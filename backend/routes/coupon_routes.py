from flask import Blueprint, request, jsonify
from backend.database import get_db, dict_from_row

coupon_bp = Blueprint("coupons", __name__)

@coupon_bp.route("/apply", methods=["POST"])
def apply_coupon():
    data = request.get_json() or {}
    code = data.get("code", "").strip().upper()
    subtotal = float(data.get("subtotal", 0.0))

    if not code:
        return jsonify({"error": "Coupon code is required"}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM coupons WHERE code = ? AND is_active = 1", (code,))
        coupon = dict_from_row(cursor.fetchone())

        if not coupon:
            return jsonify({"error": "Invalid or expired privilege code"}), 404

        if subtotal < coupon["min_order_amount"]:
            return jsonify({"error": f"Minimum order amount of ₹{coupon['min_order_amount']:,.2f} required for this code"}), 400

        if coupon["usage_limit"] and coupon["used_count"] >= coupon["usage_limit"]:
            return jsonify({"error": "Privilege code usage limit reached"}), 400

        discount = 0.0
        if coupon["discount_type"] == "PERCENTAGE":
            discount = (subtotal * coupon["discount_value"]) / 100.0
            if coupon["max_discount"] and discount > coupon["max_discount"]:
                discount = coupon["max_discount"]
        else: # FIXED
            discount = coupon["discount_value"]

        discount = min(discount, subtotal)
        return jsonify({
            "success": True,
            "code": coupon["code"],
            "discount_amount": round(discount, 2),
            "discount_type": coupon["discount_type"],
            "message": f"Privilege code applied! Saved ₹{discount:,.2f}"
        })
