import json
import random
import datetime
from zoneinfo import ZoneInfo
from flask import Blueprint, request, jsonify
import jwt
from backend.config import Config
from backend.database import get_db, dict_from_row, dicts_from_rows
from backend.services.inventory_service import InventoryService
from backend.services.email_service import EmailService

IST = ZoneInfo("Asia/Kolkata")

order_bp = Blueprint("orders", __name__)

def generate_order_number(cursor):
    """Generates a sequential, guaranteed-unique luxury order number: WT-2026-XXXXXX"""
    cursor.execute("SELECT order_number FROM orders WHERE order_number LIKE 'WT-2026-%' ORDER BY id DESC LIMIT 1")
    last_row = cursor.fetchone()
    next_seq = 1
    if last_row and last_row["order_number"]:
        try:
            parts = last_row["order_number"].split("-")
            next_seq = int(parts[-1]) + 1
        except Exception:
            next_seq = 1
    else:
        # Check any legacy orders count as base
        cursor.execute("SELECT COUNT(id) as cnt FROM orders")
        base_cnt = cursor.fetchone()["cnt"]
        next_seq = base_cnt + 1

    while True:
        candidate = f"WT-2026-{next_seq:06d}"
        cursor.execute("SELECT id FROM orders WHERE order_number = ?", (candidate,))
        if not cursor.fetchone():
            return candidate
        next_seq += 1

def get_auth_user_id(request):
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1]
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
            return int(payload.get("sub")) if payload.get("sub") else None
        except Exception:
            pass
    return None

@order_bp.route("", methods=["POST"])
def create_order():
    data = request.get_json() or {}
    cust_data = data.get("customer") if isinstance(data.get("customer"), dict) else {}
    customer_name = (data.get("customer_name") or cust_data.get("name") or cust_data.get("customer_name") or "").strip()
    customer_email = (data.get("customer_email") or cust_data.get("email") or cust_data.get("customer_email") or "").strip().lower()
    customer_phone = (data.get("customer_phone") or cust_data.get("phone") or cust_data.get("customer_phone") or "").strip()
    shipping_address = data.get("shipping_address") or cust_data
    items = data.get("items", [])
    raw_payment = (data.get("payment_method") or "COD").upper()
    payment_method = "COD" if "COD" in raw_payment or "CASH" in raw_payment else raw_payment
    coupon_code = (data.get("coupon_code") or "").strip().upper()
    order_note = (data.get("order_note") or "").strip()

    # 1. Customer Name Validation
    if not customer_name or len(customer_name) < 2:
        return jsonify({"error": "Full customer name is required (minimum 2 characters)"}), 400

    # 2. Customer Email Validation
    import re
    if not customer_email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", customer_email):
        return jsonify({"error": "A valid customer email address is required"}), 400

    # 3. Customer Phone Validation (10 digits)
    clean_phone = re.sub(r"[\s\-\+\(\)]", "", customer_phone)
    if clean_phone.startswith("91") and len(clean_phone) == 12:
        clean_phone = clean_phone[2:]
    if not re.match(r"^[6-9]\d{9}$", clean_phone):
        return jsonify({"error": "A valid 10-digit Indian mobile number is required"}), 400

    # 4. Delivery Address Validation
    if not isinstance(shipping_address, dict):
        return jsonify({"error": "Shipping address details are required"}), 400

    flat_no = (shipping_address.get("flat_no") or shipping_address.get("flat") or shipping_address.get("house") or shipping_address.get("address_line") or shipping_address.get("address_line1") or shipping_address.get("address") or "").strip()
    street = (shipping_address.get("street") or shipping_address.get("address_line") or shipping_address.get("address_line1") or shipping_address.get("address") or "").strip()
    if not flat_no and street:
        flat_no = street
    if not street and flat_no:
        street = flat_no
    city = (shipping_address.get("city") or "").strip()
    pincode = str(shipping_address.get("pincode") or shipping_address.get("postal_code") or "").strip()

    if not flat_no or not street or not city:
        return jsonify({"error": "Complete address required: Flat/House, Street, and City cannot be blank"}), 400

    if not re.match(r"^\d{6}$", pincode):
        return jsonify({"error": "A valid 6-digit Indian PIN code is required"}), 400

    user_id = get_auth_user_id(request)
    session_token = request.headers.get("X-Session-Token")

    # If user not authenticated, check if customer email matches an existing account
    if not user_id:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE LOWER(email) = ?", (customer_email,))
            u_row = cursor.fetchone()
            if u_row:
                user_id = u_row["id"]

    # If items not explicitly passed in payload, automatically pull from active cart
    if not items:
        with get_db() as conn:
            cursor = conn.cursor()
            cart_id = None
            if user_id:
                cursor.execute("SELECT id FROM carts WHERE user_id = ?", (user_id,))
                c_row = cursor.fetchone()
                if c_row:
                    cart_id = c_row["id"]
            if not cart_id and session_token:
                cursor.execute("SELECT id FROM carts WHERE session_token = ?", (session_token,))
                c_row = cursor.fetchone()
                if c_row:
                    cart_id = c_row["id"]
            if cart_id:
                cursor.execute("""
                    SELECT ci.variant_id, ci.quantity, ci.product_id, p.name as product_name
                    FROM cart_items ci
                    JOIN products p ON ci.product_id = p.id
                    WHERE ci.cart_id = ?
                """, (cart_id,))
                items = dicts_from_rows(cursor.fetchall())

    if not items:
        return jsonify({"error": "Order must contain at least one timepiece"}), 400

    with get_db() as conn:
        cursor = conn.cursor()

        # Verify stock for every item before creating order
        for item in items:
            variant_id = item.get("variant_id")
            qty = int(item.get("quantity", 1))
            available, stock, msg = InventoryService.check_availability(variant_id, qty, conn=conn)
            if not available:
                return jsonify({"error": f"Item {item.get('product_name', 'timepiece')}: {msg}"}), 400

        # Calculate subtotal from database prices to prevent client-side tampering
        subtotal = 0.0
        verified_items = []
        for item in items:
            cursor.execute("""
                SELECT pv.id as variant_id, pv.product_id, pv.color_name, pv.sku, pv.price,
                       COALESCE(pv.image_url, p.main_image, './assets/fallback-watch.svg') as image_url,
                       p.name as product_name
                FROM product_variants pv
                JOIN products p ON pv.product_id = p.id
                WHERE pv.id = ?
            """, (item.get("variant_id"),))
            v_info = cursor.fetchone()
            if not v_info:
                return jsonify({"error": "Invalid variant in order"}), 400

            qty = int(item.get("quantity", 1))
            line_total = v_info["price"] * qty
            subtotal += line_total
            verified_items.append({
                "product_id": v_info["product_id"],
                "variant_id": v_info["variant_id"],
                "product_name": v_info["product_name"],
                "color_name": v_info["color_name"],
                "sku": v_info["sku"],
                "price": v_info["price"],
                "image_url": v_info["image_url"],
                "quantity": qty,
                "total_price": line_total
            })

        # Calculate taxes and shipping
        cursor.execute("SELECT key, value FROM site_settings WHERE key IN ('tax_percent', 'shipping_fee')")
        settings = {r["key"]: r["value"] for r in cursor.fetchall()}
        tax_percent = float(settings.get("tax_percent", 18.0))
        shipping_fee = float(settings.get("shipping_fee", 0.0))

        # Check Coupon
        discount_amount = 0.0
        if coupon_code:
            cursor.execute("SELECT * FROM coupons WHERE code = ? AND is_active = 1", (coupon_code,))
            c_row = cursor.fetchone()
            if c_row and subtotal >= c_row["min_order_amount"]:
                if c_row["discount_type"] == "PERCENTAGE":
                    discount_amount = (subtotal * c_row["discount_value"]) / 100.0
                    if c_row["max_discount"] and discount_amount > c_row["max_discount"]:
                        discount_amount = c_row["max_discount"]
                else:
                    discount_amount = c_row["discount_value"]
                discount_amount = min(discount_amount, subtotal)
                cursor.execute("UPDATE coupons SET used_count = used_count + 1 WHERE id = ?", (c_row["id"],))

        discounted_subtotal = max(0.0, subtotal - discount_amount)
        tax_amount = round((discounted_subtotal * tax_percent) / 100.0, 2)
        total_amount = round(discounted_subtotal + tax_amount + shipping_fee, 2)

        order_number = generate_order_number(cursor)

        is_cod = payment_method == "COD"
        initial_order_status = "CONFIRMED" if is_cod else "PENDING"
        initial_payment_status = "COD_PENDING" if is_cod else "PENDING"

        # Current India Standard Time (IST)
        now_ist = datetime.datetime.now(IST)
        created_at_ist = now_ist.strftime("%Y-%m-%d %H:%M:%S")
        date_formatted = now_ist.strftime("%d %B %Y, %I:%M %p IST")
        time_formatted = now_ist.strftime("%I:%M %p IST")

        # Estimated delivery: 3-5 business days
        delivery_est = (now_ist + datetime.timedelta(days=4)).strftime("%B %d, %Y")

        cursor.execute("""
            INSERT INTO orders (
                order_number, user_id, customer_name, customer_email, customer_phone,
                shipping_address, subtotal, shipping_fee, tax_amount, discount_amount,
                total_amount, coupon_code, order_status, payment_method, payment_status,
                estimated_delivery, order_note, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_number, user_id, customer_name, customer_email, clean_phone,
            json.dumps(shipping_address) if isinstance(shipping_address, dict) else str(shipping_address),
            subtotal, shipping_fee, tax_amount, discount_amount, total_amount,
            coupon_code or None, initial_order_status, payment_method, initial_payment_status,
            delivery_est, order_note, created_at_ist, created_at_ist
        ))
        order_id = cursor.lastrowid

        # Insert Order Items & Reserve Inventory
        for item in verified_items:
            cursor.execute("""
                INSERT INTO order_items (
                    order_id, product_id, variant_id, product_name, color_name, sku,
                    price, quantity, total_price
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id, item["product_id"], item["variant_id"], item["product_name"],
                item["color_name"], item["sku"], item["price"], item["quantity"], item["total_price"]
            ))
            # Reserve stock
            InventoryService.reserve_stock(item["variant_id"], item["quantity"], order_number, conn=conn)

        # Status history
        cursor.execute("""
            INSERT INTO order_status_history (order_id, status, notes, created_at)
            VALUES (?, ?, ?, ?)
        """, (order_id, initial_order_status, f"Order placed via {payment_method} - Insured Express Dispatch Assigned", created_at_ist))

        # Clear purchased items from cart in database
        target_cart_id = None
        if user_id:
            cursor.execute("SELECT id FROM carts WHERE user_id = ?", (user_id,))
            c_row = cursor.fetchone()
            if c_row:
                target_cart_id = c_row["id"]
        if not target_cart_id and session_token:
            cursor.execute("SELECT id FROM carts WHERE session_token = ?", (session_token,))
            c_row = cursor.fetchone()
            if c_row:
                target_cart_id = c_row["id"]
        if target_cart_id:
            cursor.execute("DELETE FROM cart_items WHERE cart_id = ?", (target_cart_id,))

        order_dict = {
            "id": order_id,
            "order_number": order_number,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "customer_phone": clean_phone,
            "shipping_address": shipping_address,
            "subtotal": subtotal,
            "shipping_fee": shipping_fee,
            "total_amount": total_amount,
            "payment_method": "Cash on Delivery" if is_cod else ("UPI / Online (Demo)" if payment_method in ["UPI", "GPAY", "CARD"] else payment_method),
            "payment_status": initial_payment_status,
            "order_status": initial_order_status,
            "estimated_delivery": delivery_est,
            "order_note": order_note,
            "created_at": created_at_ist,
            "order_date": date_formatted,
            "order_time": time_formatted,
            "items": verified_items
        }

        # Dispatch emails with separate error isolation and comprehensive backend logging
        admin_email_sent = False
        customer_email_sent = False

        try:
            admin_email_sent = EmailService.notify_admin_new_order(order_dict, verified_items)
            print(f"[ORDER {order_number}] Admin email dispatch status: {'SUCCESS' if admin_email_sent else 'FAILED'}")
        except Exception as e_admin:
            print(f"[ORDER {order_number}] Admin email exception: {e_admin}")

        try:
            customer_email_sent = EmailService.notify_customer_order_confirmation(order_dict, verified_items)
            print(f"[ORDER {order_number}] Customer email dispatch status: {'SUCCESS' if customer_email_sent else 'FAILED'}")
        except Exception as e_cust:
            print(f"[ORDER {order_number}] Customer email exception: {e_cust}")

        return jsonify({
            "message": "Order placed successfully",
            "order_id": order_id,
            "order_number": order_number,
            "total_amount": total_amount,
            "payment_method": order_dict["payment_method"],
            "order_status": initial_order_status,
            "payment_status": initial_payment_status,
            "order_date": date_formatted,
            "order_time": time_formatted,
            "emails": {
                "customer": customer_email_sent,
                "admin": admin_email_sent
            },
            "order": order_dict
        }), 201


@order_bp.route("", methods=["GET"])
@order_bp.route("/user", methods=["GET"])
def get_user_orders():
    user_id = get_auth_user_id(request)
    if not user_id:
        return jsonify({"error": "Authentication required to view order history"}), 401

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
        u_row = cursor.fetchone()
        user_email = u_row["email"].lower() if u_row else ""

        cursor.execute("""
            SELECT o.*, COUNT(oi.id) as item_count
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE o.user_id = ? OR (LOWER(o.customer_email) = ? AND ? != '')
            GROUP BY o.id
            ORDER BY o.id DESC
        """, (user_id, user_email, user_email))
        orders = dicts_from_rows(cursor.fetchall())
        for o in orders:
            try:
                o["shipping_address"] = json.loads(o["shipping_address"])
            except Exception:
                pass
            cursor.execute("""
                SELECT oi.*, COALESCE(pv.image_url, p.main_image, './assets/fallback-watch.svg') as image_url,
                       p.name as product_name
                FROM order_items oi
                LEFT JOIN product_variants pv ON oi.variant_id = pv.id
                LEFT JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = ?
            """, (o["id"],))
            o["items"] = dicts_from_rows(cursor.fetchall())

            if o.get("created_at"):
                try:
                    dt = datetime.datetime.fromisoformat(str(o["created_at"]).replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        o["order_date"] = dt.strftime("%d %B %Y, %I:%M %p IST")
                        o["order_time"] = dt.strftime("%I:%M %p IST")
                    else:
                        dt_ist = dt.astimezone(IST)
                        o["order_date"] = dt_ist.strftime("%d %B %Y, %I:%M %p IST")
                        o["order_time"] = dt_ist.strftime("%I:%M %p IST")
                except Exception:
                    o["order_date"] = str(o.get("created_at", ""))
                    o["order_time"] = ""
        return jsonify({"orders": orders})

@order_bp.route("/<identifier>", methods=["GET"])
def get_order_by_identifier(identifier):
    with get_db() as conn:
        cursor = conn.cursor()
        if identifier.isdigit():
            cursor.execute("SELECT * FROM orders WHERE id = ?", (int(identifier),))
        else:
            cursor.execute("SELECT * FROM orders WHERE order_number = ?", (identifier,))

        order = dict_from_row(cursor.fetchone())
        if not order:
            return jsonify({"error": "Order not found"}), 404

        # Strict Customer Ownership Check
        auth_uid = get_auth_user_id(request)
        order_uid = order.get("user_id")
        order_email = (order.get("customer_email") or "").lower()

        if order_uid:
            # Order belongs to a registered collector
            if not auth_uid:
                return jsonify({"error": "Authentication required to view this private collector commission"}), 401
            cursor.execute("SELECT email, role FROM users WHERE id = ?", (auth_uid,))
            curr_u = cursor.fetchone()
            if not curr_u:
                return jsonify({"error": "Invalid authentication credentials"}), 401
            if curr_u["role"] != "admin":
                user_email = (curr_u["email"] or "").lower()
                if order_uid != auth_uid and order_email != user_email:
                    return jsonify({"error": "Forbidden: You do not have permission to view this order"}), 403
        elif auth_uid:
            cursor.execute("SELECT role FROM users WHERE id = ?", (auth_uid,))
            curr_u = cursor.fetchone()
            # If guest order, any logged-in customer who is not admin should only view if email matches
            if curr_u and curr_u["role"] != "admin":
                cursor.execute("SELECT email FROM users WHERE id = ?", (auth_uid,))
                user_email = (cursor.fetchone()["email"] or "").lower()
                if order_email and user_email != order_email:
                    return jsonify({"error": "Forbidden: You do not have permission to view this order"}), 403

        try:
            order["shipping_address"] = json.loads(order["shipping_address"])
        except Exception:
            pass

        # Items with images and watch names
        cursor.execute("""
            SELECT oi.*, COALESCE(pv.image_url, p.main_image, './assets/fallback-watch.svg') as image_url,
                   p.name as product_name
            FROM order_items oi
            LEFT JOIN product_variants pv ON oi.variant_id = pv.id
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        """, (order["id"],))
        order["items"] = dicts_from_rows(cursor.fetchall())

        if order.get("created_at"):
            try:
                dt = datetime.datetime.fromisoformat(str(order["created_at"]).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    order["order_date"] = dt.strftime("%d %B %Y, %I:%M %p IST")
                    order["order_time"] = dt.strftime("%I:%M %p IST")
                else:
                    dt_ist = dt.astimezone(IST)
                    order["order_date"] = dt_ist.strftime("%d %B %Y, %I:%M %p IST")
                    order["order_time"] = dt_ist.strftime("%I:%M %p IST")
            except Exception:
                order["order_date"] = str(order.get("created_at", ""))
                order["order_time"] = ""

        # Status History
        cursor.execute("SELECT * FROM order_status_history WHERE order_id = ? ORDER BY id ASC", (order["id"],))
        order["history"] = dicts_from_rows(cursor.fetchall())

        return jsonify({"order": order})

@order_bp.route("/track", methods=["GET"])
def track_order():
    order_number = request.args.get("order_number", "").strip()
    contact = request.args.get("contact", "").strip().lower() # email or phone

    if not order_number:
        return jsonify({"error": "Order ID is required for tracking"}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        if contact:
            cursor.execute("""
                SELECT * FROM orders
                WHERE order_number = ? AND (LOWER(customer_email) = ? OR customer_phone = ?)
            """, (order_number, contact, contact))
        else:
            cursor.execute("SELECT * FROM orders WHERE order_number = ?", (order_number,))

        order = dict_from_row(cursor.fetchone())

        if not order:
            return jsonify({"error": "No order matched the provided Order ID"}), 404

        try:
            order["shipping_address"] = json.loads(order["shipping_address"])
        except Exception:
            pass

        cursor.execute("""
            SELECT oi.*, COALESCE(pv.image_url, p.main_image, './assets/fallback-watch.svg') as image_url,
                   p.name as product_name
            FROM order_items oi
            LEFT JOIN product_variants pv ON oi.variant_id = pv.id
            LEFT JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        """, (order["id"],))
        order["items"] = dicts_from_rows(cursor.fetchall())

        if order.get("created_at"):
            try:
                dt = datetime.datetime.fromisoformat(str(order["created_at"]).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    order["order_date"] = dt.strftime("%d %B %Y, %I:%M %p IST")
                    order["order_time"] = dt.strftime("%I:%M %p IST")
                else:
                    dt_ist = dt.astimezone(IST)
                    order["order_date"] = dt_ist.strftime("%d %B %Y, %I:%M %p IST")
                    order["order_time"] = dt_ist.strftime("%I:%M %p IST")
            except Exception:
                order["order_date"] = str(order.get("created_at", ""))
                order["order_time"] = ""

        cursor.execute("SELECT * FROM order_status_history WHERE order_id = ? ORDER BY id ASC", (order["id"],))
        order["history"] = dicts_from_rows(cursor.fetchall())

        return jsonify({"order": order})

@order_bp.route("/<identifier>/cancel", methods=["POST"])
def cancel_order(identifier):
    data = request.get_json() or {}
    reason = (data.get("reason") or "").strip()
    comments = (data.get("comments") or "").strip()

    if not reason:
        return jsonify({"error": "Cancellation reason is required"}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        if identifier.isdigit():
            cursor.execute("SELECT * FROM orders WHERE id = ?", (int(identifier),))
        else:
            cursor.execute("SELECT * FROM orders WHERE order_number = ?", (identifier,))
        order = dict_from_row(cursor.fetchone())

        if not order:
            return jsonify({"error": "Order not found"}), 404

        # Disallow cancellation if already packed/shipped/delivered
        if order["order_status"] in ["SHIPPED", "OUT_FOR_DELIVERY", "DELIVERED", "CANCELLED"]:
            return jsonify({"error": f"Cannot cancel order in '{order['order_status']}' status. Please use Return Request once delivered."}), 400

        # Check payment method & status
        refund_status = "NOT_APPLICABLE"
        new_order_status = "CANCELLED"
        if order["payment_status"] == "PAID":
            refund_status = "PENDING"

        cursor.execute("""
            INSERT INTO cancellations (order_id, user_id, reason, comments, status, refund_status)
            VALUES (?, ?, ?, ?, 'APPROVED', ?)
            ON CONFLICT(order_id) DO UPDATE SET reason = excluded.reason, comments = excluded.comments
        """, (order["id"], order["user_id"], reason, comments, refund_status))

        now_ist = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE orders
            SET order_status = 'CANCELLED',
                updated_at = ?
            WHERE id = ?
        """, (now_ist, order["id"]))

        cursor.execute("""
            INSERT INTO order_status_history (order_id, status, notes, created_at)
            VALUES (?, 'CANCELLED', ?, ?)
        """, (order["id"], f"Cancelled by customer: {reason}", now_ist))

        # Release stock back to available inventory
        cursor.execute("SELECT variant_id, quantity FROM order_items WHERE order_id = ?", (order["id"],))
        for item in cursor.fetchall():
            InventoryService.release_stock(item["variant_id"], item["quantity"], order["order_number"], conn=conn)

        # Notify Admin vikneshvaren@gmail.com of cancellation
        EmailService.notify_admin_cancellation(order, reason)

        # Notify Customer
        EmailService.notify_customer_status_change(
            order, "CANCELLED",
            f"Reason: {reason}. " + ("Prepaid amount queued for refund." if refund_status == "PENDING" else "")
        )

        return jsonify({
            "message": "Order successfully cancelled",
            "refund_status": refund_status,
            "order_status": "CANCELLED"
        })

@order_bp.route("/<identifier>/return", methods=["POST"])
def request_return(identifier):
    data = request.get_json() or {}
    product_id = data.get("product_id")
    variant_id = data.get("variant_id")
    reason = (data.get("reason") or "").strip()
    description = (data.get("description") or "").strip()
    photo_urls = data.get("photo_urls", [])

    if not reason or not description:
        return jsonify({"error": "Return reason and description are required"}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        if identifier.isdigit():
            cursor.execute("SELECT * FROM orders WHERE id = ?", (int(identifier),))
        else:
            cursor.execute("SELECT * FROM orders WHERE order_number = ?", (identifier,))
        order = dict_from_row(cursor.fetchone())

        if not order:
            return jsonify({"error": "Order not found"}), 404

        if order["order_status"] != "DELIVERED":
            return jsonify({"error": "Returns can only be requested after the timepiece has been delivered"}), 400

        # Return window check (default 7 days)
        cursor.execute("SELECT value FROM site_settings WHERE key = 'return_days'")
        row = cursor.fetchone()
        return_days = int(row["value"]) if row else 7

        # In a real app we check delivery date; if within days, allow return
        cursor.execute("""
            INSERT INTO returns (
                order_id, user_id, product_id, variant_id, reason, description, photo_urls,
                status, refund_amount
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'REQUESTED', ?)
        """, (
            order["id"], order["user_id"], product_id or 1, variant_id or 1,
            reason, description, json.dumps(photo_urls), order["total_amount"]
        ))
        return_id = cursor.lastrowid

        cursor.execute("UPDATE orders SET order_status = 'RETURN_REQUESTED' WHERE id = ?", (order["id"],))
        cursor.execute("INSERT INTO order_status_history (order_id, status, notes) VALUES (?, 'RETURN_REQUESTED', ?)", (order["id"], f"Customer submitted return: {reason}"))

        # Notify Admin vikneshvaren@gmail.com of return request
        EmailService.notify_admin_return_request(order, reason, description)

        # Notify Customer
        EmailService.notify_customer_status_change(order, "RETURN_REQUESTED", f"Return reason: {reason}. Review under process.")

        return jsonify({
            "message": "Return request submitted successfully",
            "return_id": return_id,
            "status": "REQUESTED"
        }), 201

@order_bp.route("/contact", methods=["POST"])
def submit_contact_inquiry():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    subject = (data.get("subject") or "").strip() or "General Inquiry"
    message = (data.get("message") or "").strip()
    order_number = (data.get("order_number") or "").strip()

    if not name or not email or not message:
        return jsonify({"error": "Name, email address, and message details are required"}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO customer_messages (name, email, phone, subject, message, order_number, status)
            VALUES (?, ?, ?, ?, ?, ?, 'PENDING')
        """, (name, email, phone, subject, message, order_number or None))
        msg_id = cursor.lastrowid

    # Immediate notification to Administrator vikneshvaren@gmail.com
    EmailService.notify_admin_customer_message(name, email, phone, subject, message, order_number)

    return jsonify({
        "message": "Your message has been transmitted to Administrator Vikneshvaren. We will respond promptly.",
        "message_id": msg_id
    }), 201
