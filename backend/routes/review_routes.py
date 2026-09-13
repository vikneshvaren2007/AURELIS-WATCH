from flask import Blueprint, request, jsonify
from backend.database import get_db, dicts_from_rows
from backend.routes.auth_routes import token_required

review_bp = Blueprint("reviews", __name__)

@review_bp.route("", methods=["POST"])
def submit_review():
    data = request.get_json() or {}
    product_id = data.get("product_id")
    user_name = data.get("user_name", "Anonymous Collector").strip()
    rating = int(data.get("rating", 5))
    title = data.get("title", "").strip()
    comment = data.get("comment", "").strip()

    if not product_id or not title or not comment:
        return jsonify({"error": "Product, title, and comments are required"}), 400

    rating = max(1, min(5, rating))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reviews (product_id, user_name, rating, title, comment, is_verified_purchase, is_approved)
            VALUES (?, ?, ?, ?, ?, 1, 1)
        """, (product_id, user_name, rating, title, comment))

        return jsonify({"message": "Review submitted successfully", "review_id": cursor.lastrowid}), 201

@review_bp.route("/product/<int:product_id>", methods=["GET"])
def get_product_reviews(product_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM reviews
            WHERE product_id = ? AND is_approved = 1
            ORDER BY created_at DESC
        """, (product_id,))
        return jsonify({"reviews": dicts_from_rows(cursor.fetchall())})
