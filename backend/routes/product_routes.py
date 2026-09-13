import json
from flask import Blueprint, request, jsonify
from backend.database import get_db, dict_from_row, dicts_from_rows

product_bp = Blueprint("products", __name__)

@product_bp.route("", methods=["GET"])
def get_products():
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    style = request.args.get("style", "").strip()
    color = request.args.get("color", "").strip()
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    availability = request.args.get("availability", "").strip()
    sort = request.args.get("sort", "featured").strip()

    query = """
        SELECT p.*, c.name as category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE (p.is_active = 1 OR p.is_active IS NULL)
    """
    params = []

    if search:
        query += " AND (p.name LIKE ? OR p.short_description LIKE ? OR p.description LIKE ? OR p.style LIKE ? OR p.color LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term, term])

    if category:
        c_clean = category.lower().replace(" ", "-").rstrip("s")
        query += " AND (LOWER(c.slug) LIKE ? OR LOWER(c.name) LIKE ?)"
        params.extend([f"%{c_clean}%", f"%{category.lower()}%"])

    if style:
        s_clean = style.lower().replace(" ", "-").rstrip("s")
        query += " AND (LOWER(p.style) LIKE ? OR LOWER(c.name) LIKE ? OR LOWER(c.slug) LIKE ?)"
        params.extend([f"%{style.lower().rstrip('s')}%", f"%{style.lower()}%", f"%{s_clean}%"])

    if color:
        query += " AND (p.color LIKE ? OR EXISTS (SELECT 1 FROM product_variants pv WHERE pv.product_id = p.id AND pv.color_name LIKE ?))"
        params.extend([f"%{color}%", f"%{color}%"])

    if min_price is not None:
        query += " AND p.base_price >= ?"
        params.append(min_price)

    if max_price is not None:
        query += " AND p.base_price <= ?"
        params.append(max_price)

    # Sorting
    if sort == "newest":
        query += " ORDER BY p.id DESC"
    elif sort == "price_asc":
        query += " ORDER BY p.base_price ASC"
    elif sort == "price_desc":
        query += " ORDER BY p.base_price DESC"
    elif sort == "name_asc":
        query += " ORDER BY p.name ASC"
    elif sort == "name_desc":
        query += " ORDER BY p.name DESC"
    elif sort == "best_selling":
        query += " ORDER BY p.featured DESC, p.id ASC"
    else: # featured default
        query += " ORDER BY p.featured DESC, p.id ASC"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        products = dicts_from_rows(cursor.fetchall())

        result = []
        for p in products:
            if p.get("specifications"):
                try:
                    p["specifications"] = json.loads(p["specifications"])
                except Exception:
                    pass

            # Fetch variants for this product
            cursor.execute("""
                SELECT id, product_id, color_name, color_code, sku, price, discount_price,
                       stock_quantity, reserved_quantity, (stock_quantity - reserved_quantity) as available_stock,
                       low_stock_threshold, image_url
                FROM product_variants
                WHERE product_id = ?
            """, (p["id"],))
            variants = dicts_from_rows(cursor.fetchall())

            # Filter by availability
            if availability == "in_stock":
                has_stock = (p.get("stock_quantity", 0) > 0) or any(v["available_stock"] > 0 for v in variants)
                if not has_stock:
                    continue

            # Fetch primary image
            cursor.execute("SELECT image_url FROM product_images WHERE product_id = ? ORDER BY is_primary DESC LIMIT 1", (p["id"],))
            img_row = cursor.fetchone()
            p["primary_image"] = p.get("main_image") or (img_row["image_url"] if img_row else (variants[0]["image_url"] if variants else "/assets/fallback-watch.svg"))
            p["image"] = p["primary_image"]
            p["price"] = p.get("base_price")
            p["variants"] = variants

            # Average rating
            cursor.execute("SELECT AVG(rating) as avg_rating, COUNT(id) as review_count FROM reviews WHERE product_id = ? AND is_approved = 1", (p["id"],))
            rating_row = cursor.fetchone()
            p["avg_rating"] = round(rating_row["avg_rating"] or 5.0, 1)
            p["review_count"] = rating_row["review_count"] or 5

            result.append(p)

        return jsonify({"products": result, "count": len(result)})

@product_bp.route("/<identifier>", methods=["GET"])
def get_product_detail(identifier):
    with get_db() as conn:
        cursor = conn.cursor()
        if identifier.isdigit():
            cursor.execute("""
                SELECT p.*, c.name as category_name 
                FROM products p 
                LEFT JOIN categories c ON p.category_id = c.id 
                WHERE p.id = ?
            """, (int(identifier),))
        else:
            cursor.execute("""
                SELECT p.*, c.name as category_name 
                FROM products p 
                LEFT JOIN categories c ON p.category_id = c.id 
                WHERE p.slug = ?
            """, (identifier,))

        product = dict_from_row(cursor.fetchone())
        if not product:
            # Fallback to first active product
            cursor.execute("""
                SELECT p.*, c.name as category_name 
                FROM products p 
                LEFT JOIN categories c ON p.category_id = c.id 
                WHERE (p.is_active = 1 OR p.is_active IS NULL)
                ORDER BY p.id ASC LIMIT 1
            """)
            product = dict_from_row(cursor.fetchone())
            if not product:
                return jsonify({"error": "Timepiece not found"}), 404

        if product.get("specifications"):
            try:
                product["specifications"] = json.loads(product["specifications"])
            except Exception:
                pass

        # Fetch variants
        cursor.execute("""
            SELECT id, product_id, color_name, color_code, sku, price, discount_price,
                   stock_quantity, reserved_quantity, (stock_quantity - reserved_quantity) as available_stock,
                   low_stock_threshold, image_url
            FROM product_variants
            WHERE product_id = ?
            ORDER BY id ASC
        """, (product["id"],))
        product["variants"] = dicts_from_rows(cursor.fetchall())

        # Fetch gallery images
        cursor.execute("""
            SELECT id, variant_id, image_url, is_primary, sort_order
            FROM product_images
            WHERE product_id = ?
            ORDER BY is_primary DESC, sort_order ASC
        """, (product["id"],))
        gallery = dicts_from_rows(cursor.fetchall())
        
        primary_img = product.get("main_image")
        if not primary_img and gallery:
            primary_img = gallery[0]["image_url"]
        elif not primary_img and product["variants"]:
            primary_img = product["variants"][0]["image_url"]
        else:
            primary_img = primary_img or "/assets/fallback-watch.svg"
            
        product["primary_image"] = primary_img
        product["image"] = primary_img
        product["price"] = product.get("base_price")
        if not gallery:
            gallery = [{"image_url": primary_img, "is_primary": 1}]
        product["gallery"] = gallery

        # Fetch reviews
        cursor.execute("""
            SELECT id, user_name, rating, title, comment, is_verified_purchase, created_at
            FROM reviews
            WHERE product_id = ? AND is_approved = 1
            ORDER BY created_at DESC
        """, (product["id"],))
        product["reviews"] = dicts_from_rows(cursor.fetchall())

        # Related products (exactly from the 10 watch catalog)
        cursor.execute("""
            SELECT id, name, slug, base_price, discount_price, main_image as primary_image, warranty
            FROM products
            WHERE id != ? AND (is_active = 1 OR is_active IS NULL)
            LIMIT 4
        """, (product["id"],))
        product["related_products"] = dicts_from_rows(cursor.fetchall())

        return jsonify({"product": product})

@product_bp.route("/categories", methods=["GET"])
def get_categories():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories ORDER BY name ASC")
        return jsonify({"categories": dicts_from_rows(cursor.fetchall())})
