import urllib.request
import json
import re
import sys

BASE_URL = "http://127.0.0.1:5000"

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "TestClient"})
    with urllib.request.urlopen(req) as response:
        return response.status, response.read().decode('utf-8')

def post(url, data):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={"Content-Type": "application/json", "User-Agent": "TestClient"}
    )
    with urllib.request.urlopen(req) as response:
        return response.status, json.loads(response.read().decode('utf-8'))

def run_checks():
    print("=== AURELIS E2E AUTOMATED VERIFICATION ===")
    
    # 1. Check all HTML pages
    pages = [
        "/index.html",
        "/shop.html",
        "/product.html?id=1",
        "/cart.html",
        "/checkout.html",
        "/payment.html",
        "/payment-success.html",
        "/warranty.html",
        "/track-order.html",
        "/contact.html",
        "/about.html",
        "/faq.html"
    ]
    for p in pages:
        status, html = get(f"{BASE_URL}{p}")
        assert status == 200, f"Page {p} returned {status}"
        print(f"[OK] Page: {p} (HTTP 200, {len(html)} bytes)")

    # 2. Check all products & price floor
    status, body = get(f"{BASE_URL}/api/products")
    assert status == 200
    products = json.loads(body)["products"]
    assert len(products) == 10, f"Expected 10 products, got {len(products)}"
    print(f"[OK] Product Catalog: Exactly {len(products)} products found")
    
    for p in products:
        assert p["price"] >= 5000, f"Product {p['name']} price {p['price']} is below INR 5,000"
        assert p["image"], f"Product {p['name']} missing image"
    print(f"[OK] Price Floor: All {len(products)} products have price >= INR 5,000 (Min: INR {min(p['price'] for p in products)}, Max: INR {max(p['price'] for p in products)})")

    # 3. Check 5 categories with 2 watches each
    categories = [
        ("chronographs", "Chronographs"),
        ("minimalist", "Minimalist"),
        ("business-luxury", "Business Luxury"),
        ("modern-mesh", "Modern Mesh"),
        ("classic-luxury", "Classic Luxury")
    ]
    for slug, label in categories:
        status, body = get(f"{BASE_URL}/api/products?category={slug}")
        assert status == 200
        cat_products = json.loads(body)["products"]
        assert len(cat_products) == 2, f"Category {slug} expected 2 products, got {len(cat_products)}"
        names = [p['name'] for p in cat_products]
        print(f"[OK] Category '{label}' ({slug}): Exactly 2 watches -> {names}")

    # 4. Check Hero & Craft frames endpoints
    status, body = get(f"{BASE_URL}/api/hero-frames")
    assert status == 200
    hero_count = json.loads(body)["count"]
    print(f"[OK] Hero Frames: {hero_count} frames found")

    status, body = get(f"{BASE_URL}/api/craft-frames")
    assert status == 200
    craft_count = json.loads(body)["count"]
    print(f"[OK] Craft Frames: {craft_count} frames found")

    # 5. Check Order creation & Dummy Payment flow
    order_payload = {
        "customer_name": "Alexander Wright",
        "customer_email": "alexander.wright@luxury.co",
        "customer_phone": "+91 98765 43210",
        "shipping_address": {
            "flat_no": "Penthouse 4B",
            "street": "742 Evergreen Terrace",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400001"
        },
        "payment_method": "UPI",
        "items": [
            {
                "variant_id": 1,
                "quantity": 1
            }
        ]
    }
    status, order_res = post(f"{BASE_URL}/api/orders", order_payload)
    assert status == 201, f"Order creation failed: {order_res}"
    order_num = order_res["order"]["order_number"]
    print(f"[OK] Order Created: #{order_num}, Total: INR {order_res['order']['total_amount']}")

    payment_payload = {
        "order_number": order_num,
        "payment_method": "GPay Demo",
        "upi_id": "alexander@okhdfcbank"
    }
    status, pay_res = post(f"{BASE_URL}/api/payments/dummy-pay", payment_payload)
    assert status == 200, f"Dummy payment failed: {pay_res}"
    assert pay_res["order_status"] == "CONFIRMED"
    print(f"[OK] Dummy Payment Processed: #{order_num}, Txn: {pay_res['transaction_id']}, Status: {pay_res['order_status']}")

    # 6. Verify Navbar CSS rules for underline
    status, css_content = get(f"{BASE_URL}/css/main.css")
    assert status == 200
    assert "transform: scaleX(0)" in css_content
    assert "transform: scaleX(1)" in css_content
    assert "transform-origin: center" in css_content
    print("[OK] Navbar Underline CSS: Centered scaleX transform rules verified")

    print("\nALL E2E CHECKS PASSED PERFECTLY!")

if __name__ == "__main__":
    try:
        run_checks()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
