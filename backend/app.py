import os
import sys
from pathlib import Path

# Ensure root directory is always on python sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

from backend.config import Config
from backend.routes.auth_routes import auth_bp
from backend.routes.product_routes import product_bp
from backend.routes.cart_routes import cart_bp
from backend.routes.order_routes import order_bp
from backend.routes.payment_routes import payment_bp
from backend.routes.coupon_routes import coupon_bp
from backend.routes.review_routes import review_bp
from backend.routes.admin_routes import admin_bp
from backend.models import init_db

FRONTEND_DIR = Path(__file__).resolve().parent.parent

app = Flask(__name__, static_folder=str(FRONTEND_DIR))
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# Auto-initialize and seed database if empty (required for cloud environments like Render)
def init_application():
    try:
        init_db()
        from backend.database import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM products")
            row = cursor.fetchone()
            if not row or row["count"] == 0:
                from backend.seed import seed
                seed()
    except Exception as e:
        print(f"[AURELIS] Application startup init: {e}")

init_application()

# Register API Blueprints
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(product_bp, url_prefix="/api/products")
app.register_blueprint(cart_bp, url_prefix="/api/cart")
app.register_blueprint(order_bp, url_prefix="/api/orders")
app.register_blueprint(payment_bp, url_prefix="/api/payments")
app.register_blueprint(payment_bp, url_prefix="/api/payment", name="payment_alias")
app.register_blueprint(coupon_bp, url_prefix="/api/coupons")
app.register_blueprint(review_bp, url_prefix="/api/reviews")
app.register_blueprint(admin_bp, url_prefix="/api/admin")

from backend.routes.order_routes import submit_contact_inquiry
from backend.database import get_db

@app.route("/api/contact", methods=["POST", "OPTIONS"])
def contact_forward():
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200
    return submit_contact_inquiry()

@app.route("/api/settings", methods=["GET"])
def public_settings():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM site_settings WHERE key IN ('brand_name', 'currency', 'currency_symbol', 'warranty_period', 'warranty_terms', 'shipping_fee', 'return_days', 'admin_phone', 'admin_location')")
        rows = cursor.fetchall()
        return jsonify({"settings": {r["key"]: r["value"] for r in rows}})

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "brand": "AURELIS TIMEPIECES",
        "version": "2.0.0",
        "warranty": "6-Month Warranty",
        "database": "connected"
    })

@app.route("/api/frames", methods=["GET"])
@app.route("/api/hero-frames", methods=["GET"])
def get_hero_frames():
    import re
    # Homepage hero strictly uses original frames folder
    target_dir = FRONTEND_DIR / "frames"
    if not target_dir.is_dir():
        return jsonify({"count": 0, "folder": "", "frames": []}), 404
        
    supported_exts = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
    all_files = [f.name for f in target_dir.iterdir() if f.is_file() and f.suffix.lower() in supported_exts]
    
    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
        
    sorted_files = sorted(all_files, key=natural_sort_key)
    frame_urls = [f"/frames/{name}" for name in sorted_files]
    
    return jsonify({
        "status": "success",
        "folder": "frames",
        "count": len(frame_urls),
        "total_frames": len(frame_urls),
        "frames": frame_urls
    })

@app.route("/api/craft-frames", methods=["GET"])
@app.route("/api/shop-frames", methods=["GET"])
@app.route("/api/frames-2", methods=["GET"])
def get_shop_frames():
    import re
    # Craft section exploded horology sequence strictly uses frame 2 / frames 2 sequence
    candidates = ["frames 2", "frame 2"]
    target_dir = None
    folder_name = "frames 2"
    for c in candidates:
        d = FRONTEND_DIR / c
        if d.is_dir():
            target_dir = d
            folder_name = c
            break

    if not target_dir:
        return jsonify({"count": 0, "folder": "", "frames": []}), 404

    supported_exts = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
    all_files = [f.name for f in target_dir.iterdir() if f.is_file() and f.suffix.lower() in supported_exts]

    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

    sorted_files = sorted(all_files, key=natural_sort_key)

    import urllib.parse
    encoded_folder = urllib.parse.quote(folder_name)
    frame_urls = [f"/{encoded_folder}/{urllib.parse.quote(name)}" for name in sorted_files]


    return jsonify({
        "status": "success",
        "folder": folder_name,
        "count": len(frame_urls),
        "total_frames": len(frame_urls),
        "frames": frame_urls
    })

# Static files & Frontend routes
@app.route("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/frames/<path:filename>")
def serve_frames(filename):
    response = send_from_directory(FRONTEND_DIR / "frames", filename)
    response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response

@app.route("/frames 2/<path:filename>")
@app.route("/frame 2/<path:filename>")
def serve_frames_2(filename):
    target = FRONTEND_DIR / "frames 2"
    if not target.is_dir():
        target = FRONTEND_DIR / "frame 2"
    response = send_from_directory(target, filename)
    response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response

@app.route("/assets/<path:filename>")
def serve_assets(filename):
    response = send_from_directory(FRONTEND_DIR / "assets", filename, conditional=True)
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response

@app.route("/css/<path:filename>")
def serve_css(filename):
    response = send_from_directory(FRONTEND_DIR / "css", filename)
    response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response

@app.route("/js/<path:filename>")
def serve_js(filename):
    response = send_from_directory(FRONTEND_DIR / "js", filename)
    response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response

@app.route("/admin/assets/<path:filename>")
def serve_admin_assets(filename):
    response = send_from_directory(FRONTEND_DIR / "assets", filename, conditional=True)
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response

@app.route("/admin")
@app.route("/admin/")
@app.route("/admin/index.html")
def serve_admin_dashboard():
    return send_from_directory(FRONTEND_DIR / "admin", "index.html")

@app.route("/admin/<path:filename>")
def serve_admin_files(filename):
    return send_from_directory(FRONTEND_DIR / "admin", filename)

@app.route("/<path:path>")
def serve_static(path):
    file_path = FRONTEND_DIR / path
    if file_path.is_file():
        return send_from_directory(FRONTEND_DIR, path)
    elif (FRONTEND_DIR / f"{path}.html").is_file():
        return send_from_directory(FRONTEND_DIR, f"{path}.html")
    if (FRONTEND_DIR / "404.html").is_file():
        return send_from_directory(FRONTEND_DIR, "404.html"), 404
    return send_from_directory(FRONTEND_DIR, "index.html")

# Luxury Error Handlers
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Resource not found"}), 404
    return send_from_directory(FRONTEND_DIR, "404.html"), 404

@app.errorhandler(500)
def server_error(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "An internal atelier error occurred"}), 500
    return send_from_directory(FRONTEND_DIR, "500.html"), 500

if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", 5000))
    print(f"Starting AURELIS Luxury E-Commerce Atelier on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
