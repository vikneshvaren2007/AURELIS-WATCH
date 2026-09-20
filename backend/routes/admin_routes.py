import os
import json
import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from backend.database import get_db, dict_from_row, dicts_from_rows
from backend.routes.auth_routes import admin_required, generate_token
from backend.services.email_service import EmailService
from backend.services.inventory_service import InventoryService
from backend.config import Config

IST = ZoneInfo("Asia/Kolkata")

admin_bp = Blueprint("admin", __name__)

WATCH_ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "watches"
os.makedirs(WATCH_ASSETS_DIR, exist_ok=True)

@admin_bp.route("/login", methods=["POST"])
def admin_login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, phone, password_hash, role FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if not user or user["role"] != "admin" or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid administrator credentials"}), 401

        token = generate_token(user["id"], "admin", user["email"], user["name"])
        return jsonify({
            "message": "Admin authorization successful",
            "token": token,
            "admin": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "phone": user["phone"],
                "location": Config.ADMIN_LOCATION
            }
        })

@admin_bp.route("/profile", methods=["GET"])
@admin_required
def admin_profile():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins LIMIT 1")
        admin = dict_from_row(cursor.fetchone())
        return jsonify({
            "admin": admin or {
                "name": Config.ADMIN_NAME,
                "email": Config.ADMIN_EMAIL,
                "phone": Config.ADMIN_PHONE,
                "location": Config.ADMIN_LOCATION
            }
        })

@admin_bp.route("/password", methods=["PUT"])
@admin_required
def admin_change_password():
    data = request.get_json() or {}
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")

    if not old_password or not new_password:
        return jsonify({"error": "Both old and new passwords are required"}), 400
    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400

    user_id = request.current_user["sub"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user or not check_password_hash(user["password_hash"], old_password):
            return jsonify({"error": "Current password incorrect"}), 400

        new_hash = generate_password_hash(new_password)
        cursor.execute("UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_hash, user_id))
        return jsonify({"message": "Password updated successfully"})

@admin_bp.route("/dashboard", methods=["GET"])
@admin_required
def admin_dashboard():
    with get_db() as conn:
        cursor = conn.cursor()

        # Gross sales & today sales
        cursor.execute("SELECT COALESCE(SUM(total_amount), 0) as total_sales FROM orders WHERE order_status != 'CANCELLED'")
        total_sales = cursor.fetchone()["total_sales"]

        cursor.execute("SELECT COALESCE(SUM(total_amount), 0) as today_sales FROM orders WHERE order_status != 'CANCELLED' AND DATE(created_at) = DATE('now')")
        today_sales = cursor.fetchone()["today_sales"]

        # Counts
        cursor.execute("SELECT COUNT(id) as cnt FROM orders")
        total_orders = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(id) as cnt FROM orders WHERE order_status IN ('PENDING', 'CONFIRMED', 'PROCESSING', 'PACKED')")
        pending_orders = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(id) as cnt FROM orders WHERE order_status = 'DELIVERED'")
        delivered_orders = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(id) as cnt FROM orders WHERE order_status = 'CANCELLED'")
        cancelled_orders = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(id) as cnt FROM returns WHERE status = 'REQUESTED'")
        return_requests = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(id) as cnt FROM users WHERE role = 'customer'")
        customers = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(id) as cnt FROM products WHERE (is_active = 1 OR is_active IS NULL)")
        products_count = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(id) as cnt FROM product_variants WHERE (stock_quantity - reserved_quantity) <= low_stock_threshold")
        low_stock_count = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(id) as cnt FROM customer_messages WHERE status = 'PENDING'")
        pending_messages = cursor.fetchone()["cnt"]

        # Recent Orders
        cursor.execute("""
            SELECT id, order_number, customer_name, total_amount, order_status, payment_method, payment_status, created_at
            FROM orders
            ORDER BY id DESC
            LIMIT 5
        """)
        recent_orders = dicts_from_rows(cursor.fetchall())

        # Sales over time (last 7 days)
        cursor.execute("""
            SELECT DATE(created_at) as date, COALESCE(SUM(total_amount), 0) as sales, COUNT(id) as count
            FROM orders
            WHERE order_status != 'CANCELLED'
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            LIMIT 7
        """)
        sales_timeline = dicts_from_rows(cursor.fetchall())

        # Variant breakdown
        cursor.execute("""
            SELECT color_name, SUM(stock_quantity) as in_stock, SUM(reserved_quantity) as reserved
            FROM product_variants
            GROUP BY color_name
        """)
        variant_distribution = dicts_from_rows(cursor.fetchall())

        # Payment method distribution
        cursor.execute("""
            SELECT payment_method, COUNT(id) as count, COALESCE(SUM(total_amount), 0) as total
            FROM orders
            GROUP BY payment_method
        """)
        payment_distribution = dicts_from_rows(cursor.fetchall())

        return jsonify({
            "metrics": {
                "total_sales": total_sales,
                "today_sales": today_sales,
                "total_orders": total_orders,
                "pending_orders": pending_orders,
                "delivered_orders": delivered_orders,
                "cancelled_orders": cancelled_orders,
                "return_requests": return_requests,
                "customers": customers,
                "products": products_count,
                "low_stock_count": low_stock_count,
                "pending_messages": pending_messages
            },
            "recent_orders": recent_orders,
            "sales_timeline": sales_timeline,
            "variant_distribution": variant_distribution,
            "payment_distribution": payment_distribution
        })

@admin_bp.route("/orders", methods=["GET"])
@admin_required
def admin_get_orders():
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    payment_status = request.args.get("payment_status", "").strip()
    payment_method = request.args.get("payment_method", "").strip()

    query = "SELECT * FROM orders WHERE 1=1"
    params = []

    if search:
        query += " AND (order_number LIKE ? OR customer_name LIKE ? OR customer_email LIKE ? OR customer_phone LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])

    if status:
        query += " AND order_status = ?"
        params.append(status)

    if payment_status:
        query += " AND payment_status = ?"
        params.append(payment_status)

    if payment_method:
        query += " AND payment_method = ?"
        params.append(payment_method)

    query += " ORDER BY id DESC"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        orders = dicts_from_rows(cursor.fetchall())
        for o in orders:
            try:
                o["shipping_address"] = json.loads(o["shipping_address"])
            except Exception:
                pass
            cursor.execute("SELECT * FROM order_items WHERE order_id = ?", (o["id"],))
            o["items"] = dicts_from_rows(cursor.fetchall())
        return jsonify({"orders": orders, "count": len(orders)})

@admin_bp.route("/orders/<int:order_id>/status", methods=["PUT"])
@admin_required
def admin_update_order_status(order_id):
    data = request.get_json() or {}
    new_status = data.get("order_status", "").strip().upper()
    notes = data.get("notes", f"Status updated to {new_status} by administrator")

    valid_statuses = [
        "PENDING", "CONFIRMED", "PROCESSING", "PACKED", "SHIPPED",
        "OUT_FOR_DELIVERY", "DELIVERED", "CANCELLED", "RETURN_REQUESTED",
        "RETURN_APPROVED", "RETURN_REJECTED", "RETURNED", "REFUND_PROCESSING", "REFUNDED"
    ]

    if new_status not in valid_statuses:
        return jsonify({"error": f"Invalid order status: {new_status}"}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order = dict_from_row(cursor.fetchone())
        if not order:
            return jsonify({"error": "Order not found"}), 404

        # If transitioning to DELIVERED, finalize inventory deduction
        if new_status == "DELIVERED":
            cursor.execute("SELECT variant_id, quantity FROM order_items WHERE order_id = ?", (order_id,))
            for item in cursor.fetchall():
                InventoryService.finalize_stock(item["variant_id"], item["quantity"], order["order_number"], conn=conn)
            
            # If COD, mark payment as PAID upon delivery
            if order["payment_method"] == "COD":
                cursor.execute("UPDATE orders SET payment_status = 'PAID' WHERE id = ?", (order_id,))
                cursor.execute("UPDATE payments SET status = 'PAID' WHERE order_id = ?", (order_id,))

        now_ist = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE orders
            SET order_status = ?, updated_at = ?
            WHERE id = ?
        """, (new_status, now_ist, order_id))

        cursor.execute("""
            INSERT INTO order_status_history (order_id, status, notes, created_at)
            VALUES (?, ?, ?, ?)
        """, (order_id, new_status, notes, now_ist))

        # Notify customer
        EmailService.notify_customer_status_change(order, new_status, notes)

        # Notify Admin email of status progress
        EmailService.send_email(
            to_email=Config.ADMIN_EMAIL,
            subject=f"[STATUS UPDATE] #{order['order_number']} is now {new_status}",
            title="Order Status Updated",
            headline=f"Order #{order['order_number']} status changed to {new_status}",
            message_body=f"Note: {notes}",
            order_details={"ORDER ID": order["order_number"], "STATUS": new_status, "AMOUNT": f"₹{order['total_amount']:,.2f}"},
            is_admin=True
        )

        return jsonify({"message": f"Order status successfully updated to {new_status}"})

# =========================================================================
# PRODUCT MANAGEMENT (Add, Edit, Delete, Stock, Images for all 10 watches)
# =========================================================================
@admin_bp.route("/products", methods=["GET", "POST"])
@admin_required
def admin_manage_products():
    with get_db() as conn:
        cursor = conn.cursor()
        if request.method == "GET":
            cursor.execute("""
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                ORDER BY p.id ASC
            """)
            products = dicts_from_rows(cursor.fetchall())
            for p in products:
                cursor.execute("SELECT * FROM product_variants WHERE product_id = ?", (p["id"],))
                p["variants"] = dicts_from_rows(cursor.fetchall())
            return jsonify({"products": products, "count": len(products)})

        # POST: Create a new watch
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        slug = data.get("slug", "").strip().lower() or name.lower().replace(" ", "-")
        base_price = float(data.get("base_price", 0.0))
        discount_price = float(data.get("discount_price", 0.0)) if data.get("discount_price") else None
        short_desc = data.get("short_description", "").strip()
        desc = data.get("description", "").strip()
        style = data.get("style", "").strip() or "Classic Luxury"
        color = data.get("color", "").strip() or "Standard"
        sku = data.get("sku", "").strip() or f"AUR-{slug[:4].upper()}-{int(datetime.datetime.now().timestamp()) % 1000}"
        stock = int(data.get("stock_quantity", 10))
        warranty = data.get("warranty", "").strip() or "6-Month Warranty"
        main_image = data.get("main_image", "").strip() or "/assets/fallback-watch.svg"
        category_id = int(data.get("category_id", 1))
        featured = 1 if data.get("featured") else 0
        is_active = 1 if data.get("is_active", True) else 0

        if not name or base_price <= 0:
            return jsonify({"error": "Product name and positive base price are required"}), 400

        cursor.execute("""
            INSERT INTO products (
                name, slug, brand, short_description, description, category_id, featured,
                base_price, discount_price, style, color, sku, stock_quantity,
                warranty, main_image, is_active
            ) VALUES (?, ?, 'AURELIS', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, slug, short_desc, desc, category_id, featured,
            base_price, discount_price, style, color, sku, stock,
            warranty, main_image, is_active
        ))
        new_prod_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO product_variants (
                product_id, color_name, color_code, sku, price, discount_price,
                stock_quantity, reserved_quantity, low_stock_threshold, image_url
            ) VALUES (?, ?, '#d9ae55', ?, ?, ?, ?, 0, 3, ?)
        """, (new_prod_id, color, sku, base_price, discount_price, stock, main_image))
        v_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO product_images (product_id, variant_id, image_url, is_primary, sort_order)
            VALUES (?, ?, ?, 1, 1)
        """, (new_prod_id, v_id, main_image))

        return jsonify({"message": "Timepiece created successfully", "product_id": new_prod_id}), 201

@admin_bp.route("/products/<int:product_id>", methods=["PUT", "DELETE"])
@admin_required
def admin_single_product(product_id):
    with get_db() as conn:
        cursor = conn.cursor()
        if request.method == "DELETE":
            cursor.execute("DELETE FROM product_images WHERE product_id = ?", (product_id,))
            cursor.execute("DELETE FROM product_variants WHERE product_id = ?", (product_id,))
            cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
            return jsonify({"message": "Product deleted successfully"})

        data = request.get_json() or {}
        cursor.execute("""
            UPDATE products
            SET name = COALESCE(?, name),
                base_price = COALESCE(?, base_price),
                discount_price = COALESCE(?, discount_price),
                short_description = COALESCE(?, short_description),
                description = COALESCE(?, description),
                style = COALESCE(?, style),
                color = COALESCE(?, color),
                sku = COALESCE(?, sku),
                stock_quantity = COALESCE(?, stock_quantity),
                warranty = COALESCE(?, warranty),
                main_image = COALESCE(?, main_image),
                featured = COALESCE(?, featured),
                is_active = COALESCE(?, is_active),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            data.get("name"), data.get("base_price"), data.get("discount_price"),
            data.get("short_description"), data.get("description"),
            data.get("style"), data.get("color"), data.get("sku"),
            data.get("stock_quantity"), data.get("warranty"),
            data.get("main_image"), data.get("featured"), data.get("is_active"),
            product_id
        ))

        # Also sync primary variant and images if price/image/stock/sku updated
        cursor.execute("""
            UPDATE product_variants
            SET price = COALESCE(?, price),
                discount_price = COALESCE(?, discount_price),
                sku = COALESCE(?, sku),
                stock_quantity = COALESCE(?, stock_quantity),
                color_name = COALESCE(?, color_name),
                image_url = COALESCE(?, image_url)
            WHERE product_id = ?
        """, (
            data.get("base_price"), data.get("discount_price"),
            data.get("sku"), data.get("stock_quantity"),
            data.get("color"), data.get("main_image"),
            product_id
        ))

        if data.get("main_image"):
            cursor.execute("""
                UPDATE product_images
                SET image_url = ?
                WHERE product_id = ? AND is_primary = 1
            """, (data.get("main_image"), product_id))

        return jsonify({"message": "Product updated successfully"})

@admin_bp.route("/upload", methods=["POST"])
@admin_required
def admin_upload_image():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filename = secure_filename(file.filename)
    if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        return jsonify({"error": "Only JPG, PNG, and WebP images are permitted"}), 400

    ext = os.path.splitext(filename)[1].lower()
    clean_name = f"watch_{int(datetime.datetime.now().timestamp())}{ext}"
    save_path = WATCH_ASSETS_DIR / clean_name
    file.save(save_path)

    return jsonify({
        "message": "Image uploaded successfully",
        "image_url": f"/assets/watches/{clean_name}"
    })

# =========================================================================
# CUSTOMER INQUIRIES & REPLIES
# =========================================================================
@admin_bp.route("/messages", methods=["GET"])
@admin_required
def admin_get_messages():
    status_filter = request.args.get("status", "").strip()
    query = "SELECT * FROM customer_messages WHERE 1=1"
    params = []
    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
    query += " ORDER BY id DESC"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        messages = dicts_from_rows(cursor.fetchall())
        return jsonify({"messages": messages, "count": len(messages)})

@admin_bp.route("/messages/<int:message_id>/reply", methods=["POST"])
@admin_required
def admin_reply_message(message_id):
    data = request.get_json() or {}
    reply_text = data.get("reply", "").strip()
    if not reply_text:
        return jsonify({"error": "Reply message cannot be empty"}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customer_messages WHERE id = ?", (message_id,))
        msg = dict_from_row(cursor.fetchone())
        if not msg:
            return jsonify({"error": "Message not found"}), 404

        cursor.execute("""
            UPDATE customer_messages
            SET admin_reply = ?, replied_at = CURRENT_TIMESTAMP, status = 'RESOLVED'
            WHERE id = ?
        """, (reply_text, message_id))

    # Dispatch reply email to customer
    EmailService.notify_customer_support_reply(msg["name"], msg["email"], msg["subject"], reply_text)

    return jsonify({"message": f"Reply dispatched successfully to {msg['email']}"})

# =========================================================================
# INVENTORY
# =========================================================================
@admin_bp.route("/inventory", methods=["GET", "PUT"])
@admin_required
def admin_inventory():
    with get_db() as conn:
        cursor = conn.cursor()
        if request.method == "GET":
            cursor.execute("""
                SELECT pv.*, p.name as product_name, p.warranty,
                       (pv.stock_quantity - pv.reserved_quantity) as available_quantity
                FROM product_variants pv
                JOIN products p ON pv.product_id = p.id
                ORDER BY pv.id ASC
            """)
            return jsonify({"inventory": dicts_from_rows(cursor.fetchall())})

        data = request.get_json() or {}
        variant_id = data.get("variant_id")
        stock_quantity = int(data.get("stock_quantity", 0))

        cursor.execute("""
            UPDATE product_variants
            SET stock_quantity = ?
            WHERE id = ?
        """, (stock_quantity, variant_id))

        cursor.execute("""
            INSERT INTO inventory_logs (variant_id, change_amount, new_stock, reason)
            VALUES (?, 0, ?, 'ADMIN_MANUAL_ADJUSTMENT')
        """, (variant_id, stock_quantity))

        return jsonify({"message": "Inventory stock updated successfully"})

# =========================================================================
# CANCELLATIONS & RETURNS
# =========================================================================
@admin_bp.route("/cancellations", methods=["GET", "PUT"])
@admin_required
def admin_cancellations():
    with get_db() as conn:
        cursor = conn.cursor()
        if request.method == "GET":
            cursor.execute("""
                SELECT c.*, o.order_number, o.customer_name, o.customer_email, o.total_amount, o.payment_method, o.payment_status
                FROM cancellations c
                JOIN orders o ON c.order_id = o.id
                ORDER BY c.id DESC
            """)
            return jsonify({"cancellations": dicts_from_rows(cursor.fetchall())})

        data = request.get_json() or {}
        cancellation_id = data.get("cancellation_id")
        status = data.get("status", "APPROVED")
        admin_notes = data.get("admin_notes", "")

        cursor.execute("""
            UPDATE cancellations
            SET status = ?, admin_notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, admin_notes, cancellation_id))

        return jsonify({"message": f"Cancellation request {status.lower()}"})

@admin_bp.route("/returns", methods=["GET", "PUT"])
@admin_required
def admin_returns():
    with get_db() as conn:
        cursor = conn.cursor()
        if request.method == "GET":
            cursor.execute("""
                SELECT r.*, o.order_number, o.customer_name, o.customer_email, o.total_amount
                FROM returns r
                JOIN orders o ON r.order_id = o.id
                ORDER BY r.id DESC
            """)
            returns = dicts_from_rows(cursor.fetchall())
            for r in returns:
                try:
                    r["photo_urls"] = json.loads(r["photo_urls"])
                except Exception:
                    pass
            return jsonify({"returns": returns})

        data = request.get_json() or {}
        return_id = data.get("return_id")
        status = data.get("status", "UNDER_REVIEW")
        admin_notes = data.get("admin_notes", "")

        cursor.execute("""
            UPDATE returns
            SET status = ?, admin_notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, admin_notes, return_id))

        return jsonify({"message": f"Return status updated to {status}"})

@admin_bp.route("/customers", methods=["GET"])
@admin_required
def admin_customers():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.name, u.email, u.phone, u.created_at, u.address,
                   COUNT(DISTINCT o.id) as order_count,
                   COALESCE(SUM(CASE WHEN o.order_status != 'CANCELLED' THEN o.total_amount ELSE 0 END), 0) as total_spent
            FROM users u
            LEFT JOIN orders o ON (u.id = o.user_id OR LOWER(u.email) = LOWER(o.customer_email))
            WHERE u.role = 'customer'
            GROUP BY u.id
            ORDER BY u.id DESC
        """)
        return jsonify({"customers": dicts_from_rows(cursor.fetchall())})


@admin_bp.route("/payments", methods=["GET"])
@admin_required
def admin_payments():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, o.order_number, o.customer_name, o.customer_email
            FROM payments p
            JOIN orders o ON p.order_id = o.id
            ORDER BY p.id DESC
        """)
        return jsonify({"payments": dicts_from_rows(cursor.fetchall())})

@admin_bp.route("/settings", methods=["GET", "PUT"])
@admin_required
def admin_settings():
    with get_db() as conn:
        cursor = conn.cursor()
        if request.method == "GET":
            cursor.execute("SELECT key, value FROM site_settings")
            rows = cursor.fetchall()
            settings_dict = {r["key"]: r["value"] for r in rows}
            return jsonify({"settings": settings_dict})

        data = request.get_json() or {}
        for k, v in data.items():
            cursor.execute("""
                INSERT INTO site_settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
            """, (str(k), str(v)))

        return jsonify({"message": "Settings updated successfully"})
