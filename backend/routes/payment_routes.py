import json
from flask import Blueprint, request, jsonify
from backend.database import get_db, dict_from_row
from backend.services.payment_service import PaymentService
from backend.services.email_service import EmailService
from backend.services.inventory_service import InventoryService
from backend.config import Config

payment_bp = Blueprint("payments", __name__)

@payment_bp.route("/create", methods=["POST"])
def create_payment():
    """
    Creates a gateway payment order for UPI / Cards via Razorpay.
    """
    data = request.get_json() or {}
    order_id = data.get("order_id")
    order_number = data.get("order_number")

    with get_db() as conn:
        cursor = conn.cursor()
        if order_id:
            cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        elif order_number:
            cursor.execute("SELECT * FROM orders WHERE order_number = ?", (order_number,))
        else:
            return jsonify({"error": "order_id or order_number is required"}), 400

        order = dict_from_row(cursor.fetchone())
        if not order:
            return jsonify({"error": "Order not found"}), 404

        # Disallow payment if already paid
        if order["payment_status"] == "PAID":
            return jsonify({"error": "Order has already been paid"}), 400

        res = PaymentService.create_razorpay_order(order["total_amount"], order["order_number"])
        if not res.get("success"):
            return jsonify({
                "error": res.get("error", "Failed to initiate payment gateway session"),
                "configured": res.get("configured", False)
            }), 400

        # Save initial payment record
        cursor.execute("""
            INSERT INTO payments (
                order_id, gateway, gateway_order_id, payment_method, amount, currency, status
            ) VALUES (?, 'Razorpay', ?, 'UPI', ?, 'INR', 'PENDING')
        """, (order["id"], res["razorpay_order_id"], order["total_amount"]))

        return jsonify({
            "success": True,
            "key_id": res["key_id"],
            "razorpay_order_id": res["razorpay_order_id"],
            "amount": res["amount"],
            "currency": res["currency"],
            "order_number": order["order_number"],
            "customer_name": order["customer_name"],
            "customer_email": order["customer_email"],
            "customer_phone": order["customer_phone"],
            "description": f"Acquisition commission for {order['order_number']}"
        })

@payment_bp.route("/verify", methods=["POST"])
def verify_payment():
    """
    Cryptographically verifies Razorpay / UPI payment signature on the backend.
    Only marks the order as PAID after successful HMAC-SHA256 signature verification.
    """
    data = request.get_json() or {}
    order_number = data.get("order_number")
    order_id = data.get("order_id")
    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_signature = data.get("razorpay_signature")

    if (not order_number and not order_id) or not razorpay_order_id or not razorpay_payment_id or not razorpay_signature:
        return jsonify({"error": "Missing required signature verification parameters"}), 400

    # Cryptographic signature check
    is_valid = PaymentService.verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature)
    if not is_valid:
        return jsonify({"error": "Payment verification failed: cryptographic signature mismatch"}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        if order_number:
            cursor.execute("SELECT * FROM orders WHERE order_number = ?", (order_number,))
        else:
            cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order = dict_from_row(cursor.fetchone())
        if not order:
            return jsonify({"error": "Order not found"}), 404

        # Update order status to PAID and CONFIRMED
        cursor.execute("""
            UPDATE orders
            SET payment_status = 'PAID',
                order_status = 'CONFIRMED',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (order["id"],))

        # Update payment transaction record
        cursor.execute("""
            UPDATE payments
            SET gateway_payment_id = ?,
                gateway_signature = ?,
                status = 'PAID'
            WHERE gateway_order_id = ? OR order_id = ?
        """, (razorpay_payment_id, razorpay_signature, razorpay_order_id, order["id"]))

        # Status timeline entry
        cursor.execute("""
            INSERT INTO order_status_history (order_id, status, notes)
            VALUES (?, 'CONFIRMED', ?)
        """, (order["id"], f"Prepaid via UPI/Razorpay. Txn ID: {razorpay_payment_id}"))

        # Fetch order items for email breakdown
        cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order["id"],))
        from backend.database import dicts_from_rows
        order_items = dicts_from_rows(cursor.fetchall())

        order_updated = dict(order)
        order_updated["payment_status"] = "PAID"
        order_updated["order_status"] = "CONFIRMED"

        # Notify Admin of complete order & payment completion
        EmailService.notify_admin_new_order(order_updated, order_items)
        EmailService.notify_admin_payment_event(order_updated, "PAID", razorpay_payment_id)

        # Send luxury confirmation email to customer
        EmailService.notify_customer_order_confirmation(order_updated, order_items)

        return jsonify({
            "success": True,
            "message": "Payment verified and order confirmed successfully",
            "order_number": order["order_number"],
            "transaction_id": razorpay_payment_id
        })

@payment_bp.route("/fail", methods=["POST"])
def payment_failed():
    """Handles failed, cancelled or timed out payments."""
    data = request.get_json() or {}
    order_number = data.get("order_number")
    reason = data.get("reason", "Payment failed or cancelled by user")

    if not order_number:
        return jsonify({"error": "order_number is required"}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE order_number = ?", (order_number,))
        order = dict_from_row(cursor.fetchone())
        if order:
            cursor.execute("""
                UPDATE orders SET payment_status = 'FAILED', updated_at = CURRENT_TIMESTAMP WHERE id = ?
            """, (order["id"],))
            cursor.execute("""
                INSERT INTO order_status_history (order_id, status, notes)
                VALUES (?, 'PAYMENT_FAILED', ?)
            """, (order["id"], f"Payment attempt failed: {reason}"))

            # Notify Admin of payment failure
            EmailService.notify_admin_payment_event(order, "FAILED", reason)

        return jsonify({"success": True, "message": "Failure registered"})

@payment_bp.route("/cod", methods=["POST"])
def confirm_cod():
    """Handles Cash on Delivery order finalization."""
    data = request.get_json() or {}
    order_number = data.get("order_number")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE order_number = ?", (order_number,))
        order = dict_from_row(cursor.fetchone())
        if not order:
            return jsonify({"error": "Order not found"}), 404

        # Check COD site setting
        cursor.execute("SELECT value FROM site_settings WHERE key = 'cod_enabled'")
        cod_setting = cursor.fetchone()
        if cod_setting and cod_setting["value"].lower() != "true":
            return jsonify({"error": "Cash on Delivery is currently unavailable"}), 400

        cursor.execute("""
            UPDATE orders
            SET payment_method = 'COD',
                payment_status = 'COD_PENDING',
                order_status = 'CONFIRMED',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (order["id"],))

        cursor.execute("""
            INSERT INTO payments (order_id, gateway, payment_method, amount, currency, status)
            VALUES (?, 'COD', 'COD', ?, 'INR', 'COD_PENDING')
        """, (order["id"], order["total_amount"]))

        cursor.execute("""
            INSERT INTO order_status_history (order_id, status, notes)
            VALUES (?, 'CONFIRMED', 'Order confirmed under Cash on Delivery terms')
        """, (order["id"],))

        return jsonify({
            "success": True,
            "message": "Cash on Delivery order confirmed",
            "order_number": order["order_number"]
        })

@payment_bp.route("/dummy-pay", methods=["POST"])
def dummy_pay():
    """
    Handles 100% simulated dummy payments for:
    - GPay Demo
    - UPI Demo
    - Card Demo
    - Cash on Delivery
    Saves order in SQLite with PAID or CONFIRMED (COD_PENDING for COD),
    creates a payment record, safely triggers notifications, and returns success.
    """
    import time
    data = request.get_json() or {}
    order_number = data.get("order_number") or data.get("order_id")
    payment_method = data.get("payment_method") or data.get("method") or "UPI Demo"
    txn_id = data.get("txn_id") or f"DEMO_TXN_{int(time.time())}"

    if not order_number:
        return jsonify({"error": "order_number or order_id is required"}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE order_number = ?", (order_number,))
        order = dict_from_row(cursor.fetchone())
        if not order:
            return jsonify({"error": "Order not found"}), 404

        is_cod = ("cod" in payment_method.lower() or "cash" in payment_method.lower())
        saved_method = "Cash on Delivery" if is_cod else payment_method
        new_payment_status = "COD_PENDING" if is_cod else "PAID"
        new_order_status = "ORDER PLACED" if is_cod else "CONFIRMED"

        cursor.execute("""
            UPDATE orders
            SET payment_method = ?,
                payment_status = ?,
                order_status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (saved_method, new_payment_status, new_order_status, order["id"]))

        # Insert or update payment transaction record
        cursor.execute("""
            INSERT INTO payments (
                order_id, gateway, gateway_order_id, gateway_payment_id,
                payment_method, amount, currency, status
            ) VALUES (?, 'SIMULATED_DEMO', ?, ?, ?, ?, 'INR', ?)
        """, (order["id"], f"DEMO_ORD_{order['id']}", txn_id, payment_method, order["total_amount"], new_payment_status))

        # Status timeline history
        history_note = f"Payment verified via {payment_method}. Reference: {txn_id}" if not is_cod else "Order confirmed under Cash on Delivery terms"
        cursor.execute("""
            INSERT INTO order_status_history (order_id, status, notes)
            VALUES (?, 'CONFIRMED', ?)
        """, (order["id"], history_note))

        # Fetch items for email
        cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (order["id"],))
        from backend.database import dicts_from_rows
        order_items = dicts_from_rows(cursor.fetchall())

        order_updated = dict(order)
        order_updated["payment_method"] = payment_method
        order_updated["payment_status"] = new_payment_status
        order_updated["order_status"] = new_order_status

        # Safely trigger emails
        try:
            EmailService.notify_admin_new_order(order_updated, order_items)
            if not is_cod:
                EmailService.notify_admin_payment_event(order_updated, "PAID", txn_id)
            EmailService.notify_customer_order_confirmation(order_updated, order_items)
        except Exception as e:
            print(f"[Dummy Pay Email Warning] {e}")

        return jsonify({
            "success": True,
            "message": "Payment authorized and order confirmed successfully",
            "order_number": order["order_number"],
            "transaction_id": txn_id,
            "payment_method": payment_method,
            "payment_status": new_payment_status,
            "order_status": new_order_status
        })
