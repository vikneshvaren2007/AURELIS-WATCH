from flask import Blueprint, request, jsonify
import jwt
from backend.config import Config
from backend.database import get_db, dict_from_row, dicts_from_rows
from backend.services.inventory_service import InventoryService

cart_bp = Blueprint("cart", __name__)

def get_cart_owner(request):
    """Extracts either logged-in user_id or guest session_token."""
    auth_header = request.headers.get("Authorization")
    user_id = None
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1]
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
            user_id = int(payload.get("sub")) if payload.get("sub") else None
        except Exception as e:
            pass

    session_token = request.headers.get("X-Session-Token") or request.args.get("session_token")
    return user_id, session_token

def get_or_create_cart(cursor, user_id, session_token):
    if user_id:
        cursor.execute("SELECT id FROM carts WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return row["id"]
        cursor.execute("INSERT INTO carts (user_id) VALUES (?)", (user_id,))
        return cursor.lastrowid
    elif session_token:
        cursor.execute("SELECT id FROM carts WHERE session_token = ?", (session_token,))
        row = cursor.fetchone()
        if row:
            return row["id"]
        cursor.execute("INSERT INTO carts (session_token) VALUES (?)", (session_token,))
        return cursor.lastrowid
    return None

@cart_bp.route("", methods=["GET"])
def get_cart():
    user_id, session_token = get_cart_owner(request)
    if not user_id and not session_token:
        return jsonify({"items": [], "subtotal": 0, "tax": 0, "shipping": 0, "total": 0, "count": 0})

    with get_db() as conn:
        cursor = conn.cursor()
        cart_id = get_or_create_cart(cursor, user_id, session_token)
        if not cart_id:
            return jsonify({"items": [], "subtotal": 0, "tax": 0, "shipping": 0, "total": 0, "count": 0})

        cursor.execute("""
            SELECT ci.id as item_id, ci.id as id, ci.quantity, ci.product_id, ci.variant_id,
                   p.name as product_name, p.slug as product_slug,
                   pv.color_name, pv.sku, pv.price, pv.price as unit_price, pv.discount_price, pv.image_url,
                   pv.stock_quantity as available_stock, pv.strap_color, pv.accent_color
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.id
            JOIN product_variants pv ON ci.variant_id = pv.id
            WHERE ci.cart_id = ?
        """, (cart_id,))
        items = dicts_from_rows(cursor.fetchall())

        subtotal = sum(item["price"] * item["quantity"] for item in items)
        
        # Calculate shipping and tax based on site_settings
        cursor.execute("SELECT key, value FROM site_settings WHERE key IN ('tax_percent', 'shipping_fee')")
        settings = {r["key"]: r["value"] for r in cursor.fetchall()}
        tax_percent = float(settings.get("tax_percent", 18.0))
        shipping_fee = float(settings.get("shipping_fee", 0.0))

        tax = round((subtotal * tax_percent) / 100.0, 2)
        total = round(subtotal + tax + shipping_fee, 2)
        total_items = sum(item["quantity"] for item in items)

        return jsonify({
            "items": items,
            "subtotal": subtotal,
            "tax": tax,
            "shipping": shipping_fee,
            "total": total,
            "count": total_items
        })

@cart_bp.route("", methods=["POST"])
def add_to_cart():
    user_id, session_token = get_cart_owner(request)
    data = request.get_json() or {}
    product_id = data.get("product_id")
    variant_id = data.get("variant_id")
    quantity = int(data.get("quantity", 1))

    if not variant_id and product_id:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM product_variants WHERE product_id = ? ORDER BY id ASC LIMIT 1", (product_id,))
            v_row = cursor.fetchone()
            if v_row:
                variant_id = v_row["id"]

    if not variant_id:
        return jsonify({"error": "Product variant is required"}), 400
    if quantity <= 0:
        return jsonify({"error": "Quantity must be greater than zero"}), 400

    # Stock check
    available, stock_count, msg = InventoryService.check_availability(variant_id, quantity)
    if not available:
        return jsonify({"error": msg}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        if not user_id and not session_token:
            import uuid
            session_token = f"sess_{uuid.uuid4().hex}"

        cart_id = get_or_create_cart(cursor, user_id, session_token)
        
        # Auto lookup product_id if not supplied
        if not product_id:
            cursor.execute("SELECT product_id FROM product_variants WHERE id = ?", (variant_id,))
            v_row = cursor.fetchone()
            if not v_row:
                return jsonify({"error": "Invalid variant"}), 404
            product_id = v_row["product_id"]

        cursor.execute("SELECT id, quantity FROM cart_items WHERE cart_id = ? AND variant_id = ?", (cart_id, variant_id))
        existing = cursor.fetchone()

        if existing:
            new_qty = existing["quantity"] + quantity
            avail, _, msg = InventoryService.check_availability(variant_id, new_qty, conn=conn)
            if not avail:
                return jsonify({"error": msg}), 400
            cursor.execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (new_qty, existing["id"]))
        else:
            cursor.execute("""
                INSERT INTO cart_items (cart_id, product_id, variant_id, quantity)
                VALUES (?, ?, ?, ?)
            """, (cart_id, product_id, variant_id, quantity))

        return jsonify({"message": "Timepiece added to commission cart", "session_token": session_token}), 200

@cart_bp.route("/<int:item_id>", methods=["PUT"])
def update_cart_item(item_id):
    data = request.get_json() or {}
    quantity = int(data.get("quantity", 1))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT variant_id FROM cart_items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Cart item not found"}), 404

        if quantity <= 0:
            cursor.execute("DELETE FROM cart_items WHERE id = ?", (item_id,))
            return jsonify({"message": "Item removed from cart"})

        avail, _, msg = InventoryService.check_availability(row["variant_id"], quantity, conn=conn)
        if not avail:
            return jsonify({"error": msg}), 400

        cursor.execute("UPDATE cart_items SET quantity = ? WHERE id = ?", (quantity, item_id))
        return jsonify({"message": "Cart updated successfully"})

@cart_bp.route("/<int:item_id>", methods=["DELETE"])
def delete_cart_item(item_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart_items WHERE id = ?", (item_id,))
        return jsonify({"message": "Item removed from cart"})

@cart_bp.route("/clear", methods=["POST"])
def clear_cart():
    user_id, session_token = get_cart_owner(request)
    with get_db() as conn:
        cursor = conn.cursor()
        cart_id = get_or_create_cart(cursor, user_id, session_token)
        if cart_id:
            cursor.execute("DELETE FROM cart_items WHERE cart_id = ?", (cart_id,))
        return jsonify({"message": "Cart cleared"})

@cart_bp.route("/merge", methods=["POST"])
def merge_cart():
    """Merges guest session cart items into logged-in user cart."""
    user_id, _ = get_cart_owner(request)
    if not user_id:
        return jsonify({"error": "Authentication required to merge cart"}), 401

    data = request.get_json() or {}
    session_token = data.get("session_token")
    if not session_token:
        return jsonify({"message": "No session cart to merge"})

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM carts WHERE session_token = ?", (session_token,))
        guest_cart = cursor.fetchone()
        if not guest_cart:
            return jsonify({"message": "No guest cart found"})

        user_cart_id = get_or_create_cart(cursor, user_id, None)

        cursor.execute("SELECT product_id, variant_id, quantity FROM cart_items WHERE cart_id = ?", (guest_cart["id"],))
        guest_items = cursor.fetchall()

        for item in guest_items:
            cursor.execute("SELECT id, quantity FROM cart_items WHERE cart_id = ? AND variant_id = ?", (user_cart_id, item["variant_id"]))
            existing = cursor.fetchone()
            if existing:
                cursor.execute("UPDATE cart_items SET quantity = quantity + ? WHERE id = ?", (item["quantity"], existing["id"]))
            else:
                cursor.execute("""
                    INSERT INTO cart_items (cart_id, product_id, variant_id, quantity)
                    VALUES (?, ?, ?, ?)
                """, (user_cart_id, item["product_id"], item["variant_id"], item["quantity"]))

        # Delete guest cart
        cursor.execute("DELETE FROM carts WHERE id = ?", (guest_cart["id"],))
        return jsonify({"message": "Guest cart successfully merged into user account"})
