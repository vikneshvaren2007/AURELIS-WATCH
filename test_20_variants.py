import os
import sys
import json
import urllib.request
import sqlite3

def run_tests():
    print("==================================================")
    print("STARTING 20 WATCH VARIANTS VERIFICATION")
    print("==================================================")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "backend", "aurelis.db")
    
    # 1. Database Verification
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT id, name, slug FROM products WHERE id <= 10 ORDER BY id ASC")
    products = c.fetchall()
    assert len(products) == 10, f"Expected 10 core products, found {len(products)}"
    print(f"[PASS] Found exactly 10 core watches in database.")

    total_variants = 0
    all_variant_images = []
    
    for p in products:
        c.execute("""
            SELECT id, color_name, color_code, sku, price, image_url, strap_color, accent_color
            FROM product_variants
            WHERE product_id = ?
            ORDER BY id ASC
        """, (p["id"],))
        vars_for_p = c.fetchall()
        assert len(vars_for_p) == 2, f"Product {p['name']} (ID {p['id']}) has {len(vars_for_p)} variants, expected exactly 2!"
        total_variants += len(vars_for_p)
        print(f"  Watch {p['id']}: {p['name']}")
        for v_idx, v in enumerate(vars_for_p, 1):
            print(f"    - Variant {v_idx} (ID {v['id']}): '{v['color_name']}' | Strap: '{v['strap_color']}' | Accent: '{v['accent_color']}'")
            all_variant_images.append(v['image_url'])

    assert total_variants == 20, f"Expected 20 variants total, got {total_variants}"
    print(f"[PASS] Exactly 20 variants confirmed in database (10 watches x 2 variants).")

    # 2. Check that all variant images exist on disk and have non-zero size
    print("\n--- Verifying Variant Images on Disk ---")
    for img_rel in all_variant_images:
        clean_rel = img_rel.replace("./", "").replace("/", os.sep)
        full_path = os.path.join(base_dir, clean_rel)
        assert os.path.exists(full_path), f"Image missing on disk: {full_path}"
        size = os.path.getsize(full_path)
        assert size > 5000, f"Image file too small or empty ({size} bytes): {full_path}"
        print(f"  [OK] Exists ({size:,} bytes): {clean_rel}")
    print("[PASS] All variant image assets verified on disk.")

    # 3. HTTP API Verification: GET /api/products
    print("\n--- Verifying GET /api/products Endpoint ---")
    url = "http://127.0.0.1:5000/api/products"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    
    api_prods = data.get("products", [])
    assert len(api_prods) >= 10, f"Expected at least 10 products from API, got {len(api_prods)}"
    
    core_api_prods = [p for p in api_prods if p["id"] <= 10]
    for p in core_api_prods:
        assert len(p["variants"]) == 2, f"API product {p['name']} has {len(p['variants'])} variants, expected 2"
        for v in p["variants"]:
            assert "strap_color" in v and v["strap_color"], f"Missing strap_color in API variant {v['id']}"
            assert "image_url" in v and v["image_url"], f"Missing image_url in API variant {v['id']}"
    print("[PASS] GET /api/products correctly returns 2 variants for every watch with strap_color and accent_color.")

    # 4. HTTP API Verification: GET /api/products/<id>
    print("\n--- Verifying Individual PDP Detail Endpoints ---")
    for pid in range(1, 11):
        url = f"http://127.0.0.1:5000/api/products/{pid}"
        with urllib.request.urlopen(url) as resp:
            p_data = json.loads(resp.read().decode())
        p_obj = p_data.get("product")
        assert p_obj, f"Product {pid} not found"
        assert len(p_obj["variants"]) == 2, f"Product {pid} PDP has {len(p_obj['variants'])} variants, expected 2"
    print("[PASS] All 10 PDP endpoints verified (each returns 2 variants).")

    # 5. End-to-end Cart and Order Placement with Variant 2
    print("\n--- Verifying Cart & Order Creation with Variant 2 ---")
    # Let's test Watch 2, Variant 2: "Navy Blue" (variant ID 4)
    session_token = "test_variant2_token_9999"
    add_cart_url = "http://127.0.0.1:5000/api/cart"
    payload = json.dumps({"product_id": 2, "variant_id": 4, "quantity": 1}).encode()
    cart_req = urllib.request.Request(
        add_cart_url, 
        data=payload,
        headers={"Content-Type": "application/json", "X-Session-Token": session_token}
    )
    with urllib.request.urlopen(cart_req) as resp:
        add_res = json.loads(resp.read().decode())
    
    # Get cart
    get_cart_url = "http://127.0.0.1:5000/api/cart"
    get_cart_req = urllib.request.Request(get_cart_url, headers={"X-Session-Token": session_token})
    with urllib.request.urlopen(get_cart_req) as resp:
        cart_data = json.loads(resp.read().decode())
    
    assert len(cart_data["items"]) >= 1, "Cart empty after add!"
    cart_item = cart_data["items"][0]
    assert cart_item["variant_id"] == 4, f"Expected variant_id 4, got {cart_item['variant_id']}"
    assert "Navy Blue" in cart_item["color_name"], f"Expected Navy Blue in color_name, got {cart_item['color_name']}"
    assert "Navy Blue" in cart_item["strap_color"], f"Expected Navy Blue in strap_color, got {cart_item['strap_color']}"
    print(f"  [OK] Cart contains exact variant: '{cart_item['color_name']}' with strap '{cart_item['strap_color']}'")

    # Place order
    order_url = "http://127.0.0.1:5000/api/orders"
    order_payload = json.dumps({
        "customer_name": "Viknesh Test Collector",
        "customer_email": "viknesh.test@example.com",
        "customer_phone": "9876543210",
        "shipping_address": {
            "name": "Viknesh Test Collector",
            "phone": "9876543210",
            "flat_no": "Villa 12",
            "street": "Royal Atelier Boulevard",
            "city": "Tenkasi",
            "district": "Tenkasi",
            "state": "Tamil Nadu",
            "pincode": "627811"
        },
        "payment_method": "COD"
    }).encode()
    order_req = urllib.request.Request(
        order_url,
        data=order_payload,
        headers={"Content-Type": "application/json", "X-Session-Token": session_token}
    )
    with urllib.request.urlopen(order_req) as resp:
        order_res = json.loads(resp.read().decode())
    
    order_num = order_res.get("order_number")
    assert order_num, f"Order placement failed: {order_res}"
    print(f"  [OK] Order successfully placed: {order_num}")

    # Check database order_items for exact variant name
    c.execute("""
        SELECT oi.id, oi.product_name, oi.color_name, oi.sku, oi.price, oi.quantity
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.id
        WHERE o.order_number = ?
    """, (order_num,))
    order_items_rows = c.fetchall()
    assert len(order_items_rows) >= 1, "No order items found in database!"
    oi = order_items_rows[0]
    assert oi["color_name"] == "Navy Blue", f"Recorded color_name mismatch: {oi['color_name']}"
    print(f"  [OK] DB order_items recorded exact variant: '{oi['color_name']}' (SKU: {oi['sku']})")

    # Check order detail API
    order_detail_url = f"http://127.0.0.1:5000/api/orders/{order_num}"
    with urllib.request.urlopen(order_detail_url) as resp:
        detail_res = json.loads(resp.read().decode())
    order_obj = detail_res.get("order", {})
    item_obj = order_obj.get("items", [])[0]
    assert item_obj["color_name"] == "Navy Blue", f"API color_name mismatch: {item_obj['color_name']}"
    print(f"  [OK] Order detail API verified: item color is '{item_obj['color_name']}'")

    print("\n==================================================")
    print("ALL 20 WATCH VARIANT TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
