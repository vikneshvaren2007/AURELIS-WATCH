import os
import sys
import json
import urllib.request
import sqlite3

def run_atoz_tests():
    print("==================================================")
    print("AURELIS LUXURY WATCHES — 10 WATCHES A-TO-Z VARIANT TEST")
    print("==================================================")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, "backend", "aurelis.db")
    
    EXPECTED_VARIANTS = {
        1: ("Classic Brown Leather", "Deep Brown Leather"),
        2: ("Brushed Steel & Charcoal", "Navy Blue"),
        3: ("Matte Black & Onyx", "Cognac Brown"),
        4: ("Silver Steel & Midnight Blue", "Forest Green"),
        5: ("Silver Milanese Mesh", "Burgundy / Dark Wine"),
        6: ("All-Black DLC Steel", "Dark Tan"),
        7: ("Gunmetal Steel & Graphite", "Charcoal Grey"),
        8: ("18K Gold & Cognac Leather", "Olive / Dark Green"),
        9: ("Brushed Steel & Emerald Green", "Coffee Brown"),
        10: ("Mirror Silver Links", "Deep Black"),
    }
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # 1. Verify 20 images on disk in assets/watches/variants
    print("\n[STEP 1] Verifying all 20 image assets on disk...")
    for pid in range(1, 11):
        orig_img = os.path.join(base_dir, "assets", "watches", "variants", f"watch-{pid:02d}-original.jpg")
        alt_img = os.path.join(base_dir, "assets", "watches", "variants", f"watch-{pid:02d}-alternate.jpg")
        assert os.path.exists(orig_img), f"Missing original: {orig_img}"
        assert os.path.exists(alt_img), f"Missing alternate: {alt_img}"
        assert os.path.getsize(orig_img) > 10000, f"Original image too small: {orig_img}"
        assert os.path.getsize(alt_img) > 10000, f"Alternate image too small: {alt_img}"
        print(f"  Watch {pid:02d}: Original ({os.path.getsize(orig_img):,} bytes) & Alternate ({os.path.getsize(alt_img):,} bytes) [OK]")
    print("[PASS] All 20 physical image assets verified.")

    # 2. Test each of the 10 watches from API -> Cart -> Checkout -> Order -> DB -> Admin
    print("\n[STEP 2] Testing ALL 10 watches through full e-commerce lifecycle...")
    
    for pid in range(1, 11):
        print(f"\n--- TESTING WATCH {pid:02d} ---")
        # A. Fetch Product Detail
        url = f"http://127.0.0.1:5000/api/products/{pid}"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read().decode())
        prod = data.get("product")
        assert prod, f"Product {pid} not found"
        variants = prod.get("variants", [])
        assert len(variants) == 2, f"Expected 2 variants for product {pid}, got {len(variants)}"
        
        v1 = variants[0]
        v2 = variants[1]
        
        expected_v1, expected_v2 = EXPECTED_VARIANTS[pid]
        assert v1["color_name"] == expected_v1, f"Watch {pid} V1 mismatch: expected '{expected_v1}', got '{v1['color_name']}'"
        assert v2["color_name"] == expected_v2, f"Watch {pid} V2 mismatch: expected '{expected_v2}', got '{v2['color_name']}'"
        print(f"  1. PDP loaded: '{prod['name']}'")
        print(f"     - Original variant (ID {v1['id']}): '{v1['color_name']}' (Image: {v1['image_url']})")
        print(f"     - Alternate variant (ID {v2['id']}): '{v2['color_name']}' (Image: {v2['image_url']})")
        
        # B. Add Alternate Variant to Cart
        session_token = f"session_test_watch_{pid}_{os.urandom(4).hex()}"
        add_cart_url = "http://127.0.0.1:5000/api/cart"
        payload = json.dumps({"product_id": pid, "variant_id": v2["id"], "quantity": 1}).encode()
        cart_req = urllib.request.Request(
            add_cart_url, 
            data=payload,
            headers={"Content-Type": "application/json", "X-Session-Token": session_token}
        )
        with urllib.request.urlopen(cart_req) as resp:
            add_res = json.loads(resp.read().decode())
            
        # C. Verify Cart contains Alternate Variant
        get_cart_url = "http://127.0.0.1:5000/api/cart"
        get_cart_req = urllib.request.Request(get_cart_url, headers={"X-Session-Token": session_token})
        with urllib.request.urlopen(get_cart_req) as resp:
            cart_data = json.loads(resp.read().decode())
        assert len(cart_data["items"]) == 1, f"Expected 1 item in cart, got {len(cart_data['items'])}"
        item = cart_data["items"][0]
        assert item["variant_id"] == v2["id"], f"Variant ID mismatch in cart: {item['variant_id']} vs {v2['id']}"
        assert item["color_name"] == expected_v2, f"Color name mismatch in cart: {item['color_name']}"
        assert item["image_url"] == v2["image_url"], f"Image URL mismatch in cart: {item['image_url']}"
        print(f"  2. Added alternate to cart: '{item['color_name']}' with image '{item['image_url']}' [OK]")
        
        # D. Place Order with Alternate Variant
        order_url = "http://127.0.0.1:5000/api/orders"
        order_payload = json.dumps({
            "customer_name": f"Collector {pid}",
            "customer_email": f"collector{pid}@aurelis-luxury.com",
            "customer_phone": "9876543210",
            "shipping_address": {
                "name": f"Collector {pid}",
                "phone": "9876543210",
                "flat_no": f"Penthouse {pid}",
                "street": "Timepiece Way",
                "city": "Chennai",
                "district": "Chennai",
                "state": "Tamil Nadu",
                "pincode": "600001"
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
        print(f"  3. Order placed successfully: {order_num} [OK]")
        
        # E. Verify SQLite Database order_items recorded Alternate Variant
        c.execute("""
            SELECT oi.id, oi.product_id, oi.variant_id, oi.product_name, oi.color_name, oi.sku, oi.price,
                   pv.image_url as variant_image
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            JOIN product_variants pv ON oi.variant_id = pv.id
            WHERE o.order_number = ?
        """, (order_num,))
        db_item = c.fetchone()
        assert db_item, f"Order {order_num} not found in database!"
        assert db_item["variant_id"] == v2["id"], f"DB variant_id mismatch: {db_item['variant_id']}"
        assert db_item["color_name"] == expected_v2, f"DB color_name mismatch: {db_item['color_name']}"
        assert db_item["variant_image"] == v2["image_url"], f"DB variant_image mismatch: {db_item['variant_image']}"
        print(f"  4. Database verified: order_items variant='{db_item['color_name']}' (SKU: {db_item['sku']}) [OK]")
        
        # F. Verify Order Detail API returns Alternate Variant & Image
        order_detail_url = f"http://127.0.0.1:5000/api/orders/{order_num}"
        with urllib.request.urlopen(order_detail_url) as resp:
            detail_res = json.loads(resp.read().decode())
        api_order_item = detail_res["order"]["items"][0]
        assert api_order_item["color_name"] == expected_v2
        assert api_order_item["variant_id"] == v2["id"]
        print(f"  5. Order API confirmed: returned item color='{api_order_item['color_name']}' [OK]")

    print("\n==================================================")
    print("ALL 10 WATCHES PASSED FULL E-COMMERCE TESTS WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    run_atoz_tests()
