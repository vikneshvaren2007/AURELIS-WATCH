import requests
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://127.0.0.1:5000"

def test_all():
    print("=== STARTING COMPREHENSIVE VERIFICATION SUITE ===")

    # 1. Health Check
    res = requests.get(f"{BASE_URL}/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("✓ 1. Health check passed")

    # 2. Catalog & Variants Verification
    res = requests.get(f"{BASE_URL}/api/products")
    assert res.status_code == 200
    products = res.json().get("products", [])
    assert len(products) >= 15, f"Expected at least 15 products, got {len(products)}"
    print(f"✓ 2. Catalog verification: {len(products)} products active in database")

    # Flagship Watch (ID: 1) Variants Check
    res = requests.get(f"{BASE_URL}/api/products/1")
    assert res.status_code == 200
    prod1 = res.json().get("product", {})
    variants = prod1.get("variants", [])
    assert len(variants) == 5, f"Expected 5 variants for Product 1, got {len(variants)}"
    variant_names = [v["color_name"] for v in variants]
    print(f"✓ 3. Flagship Watch 1 has 5 color variants: {variant_names}")

    # Masterpiece Collection Check
    masterpieces = [p for p in products if p.get("base_price", 0) >= 25000 and p.get("base_price", 0) <= 50000]
    assert len(masterpieces) == 5, f"Expected 5 Masterpiece watches between ₹25,000 and ₹50,000, got {len(masterpieces)}"
    for m in masterpieces:
        print(f"   - {m['name']}: ₹{m['base_price']:,.0f} ({m.get('style', '')})")
    print("✓ 4. All 5 Masterpiece Collection timepieces verified (₹25,000 - ₹50,000)")

    # 3. Multi-Customer Isolation Test
    import time
    ts = int(time.time())
    
    # Customer A
    email_a = f"viknesh_collector_a_{ts}@example.com"
    pwd = "SecurePassword123!"
    reg_a = requests.post(f"{BASE_URL}/api/auth/register", json={
        "name": "Alexander Vance",
        "email": email_a,
        "password": pwd,
        "phone": "+91 9876543210",
        "address": "42 Oberoi Chambers, Nariman Point, Mumbai, Maharashtra 400021"
    })
    assert reg_a.status_code == 201, f"Reg A failed: {reg_a.text}"
    token_a = reg_a.json()["token"]
    user_a = reg_a.json()["user"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    print(f"✓ 5. Registered Customer A (ID: {user_a['id']}, Name: {user_a['name']})")

    # Customer B
    email_b = f"viknesh_collector_b_{ts}@example.com"
    reg_b = requests.post(f"{BASE_URL}/api/auth/register", json={
        "name": "Lady Genevieve",
        "email": email_b,
        "password": pwd,
        "phone": "+91 9123456780",
        "address": "15 Taj Palace Enclave, New Delhi, Delhi 110001"
    })
    assert reg_b.status_code == 201, f"Reg B failed: {reg_b.text}"
    token_b = reg_b.json()["token"]
    user_b = reg_b.json()["user"]
    headers_b = {"Authorization": f"Bearer {token_b}"}
    print(f"✓ 6. Registered Customer B (ID: {user_b['id']}, Name: {user_b['name']})")

    # Customer C (No orders)
    email_c = f"viknesh_collector_c_{ts}@example.com"
    reg_c = requests.post(f"{BASE_URL}/api/auth/register", json={
        "name": "Julian Thorne",
        "email": email_c,
        "password": pwd,
        "phone": "+91 9988776655"
    })
    assert reg_c.status_code == 201
    token_c = reg_c.json()["token"]
    headers_c = {"Authorization": f"Bearer {token_c}"}
    print(f"✓ 7. Registered Customer C (ID: {reg_c.json()['user']['id']}, with 0 orders)")

    # Customer A places Order 1
    order1_payload = {
        "customer_name": user_a["name"],
        "customer_email": user_a["email"],
        "customer_phone": user_a["phone"],
        "shipping_address": {
            "flat_no": "Suite 402",
            "street": "Nariman Point Boulevard",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400021"
        },
        "payment_method": "UPI",
        "items": [
            {
                "product_id": 1,
                "variant_id": variants[0]["id"],
                "product_name": "Aurelis Imperial Dragon",
                "variant_color": variants[0]["color_name"],
                "unit_price": 6499,
                "quantity": 1,
                "total_price": 6499
            }
        ]
    }
    res_o1 = requests.post(f"{BASE_URL}/api/orders", json=order1_payload, headers=headers_a)
    assert res_o1.status_code == 201, f"Order 1 creation failed: {res_o1.text}"
    order1_data = res_o1.json()
    order1_num = order1_data["order_number"]
    order1_id = order1_data["order_id"]
    print(f"✓ 8. Customer A created Order: {order1_num} (ID: {order1_id})")

    # Pay Order 1 via dummy-pay
    pay1 = requests.post(f"{BASE_URL}/api/payments/dummy-pay", json={
        "order_number": order1_num,
        "payment_method": "Google Pay Demo"
    })
    assert pay1.status_code == 200
    print(f"✓ 9. Simulated payment processed for Order {order1_num}: status={pay1.json().get('payment_status')}")

    # Customer B places Order 2 (Masterpiece Watch 11)
    order2_payload = {
        "customer_name": user_b["name"],
        "customer_email": user_b["email"],
        "customer_phone": user_b["phone"],
        "shipping_address": {
            "flat_no": "Villa 15",
            "street": "Taj Palace Enclave",
            "city": "New Delhi",
            "state": "Delhi",
            "pincode": "110001"
        },
        "payment_method": "Credit Card Demo",
        "items": [
            {
                "product_id": 11,
                "variant_id": 11,
                "product_name": "Aurelis Tourbillon Squelette",
                "variant_color": "Rose Gold & Sapphire",
                "unit_price": 49999,
                "quantity": 1,
                "total_price": 49999
            }
        ]
    }
    res_o2 = requests.post(f"{BASE_URL}/api/orders", json=order2_payload, headers=headers_b)
    assert res_o2.status_code == 201, f"Order 2 creation failed: {res_o2.text}"
    order2_data = res_o2.json()
    order2_num = order2_data["order_number"]
    order2_id = order2_data["order_id"]
    print(f"✓ 10. Customer B created Order: {order2_num} (ID: {order2_id})")

    # Pay Order 2
    pay2 = requests.post(f"{BASE_URL}/api/payments/dummy-pay", json={
        "order_number": order2_num,
        "payment_method": "Credit Card Demo"
    })
    assert pay2.status_code == 200
    print(f"✓ 11. Simulated payment processed for Order {order2_num}: status={pay2.json().get('payment_status')}")

    # VERIFY CUSTOMER ISOLATION
    # 1. Customer A's orders
    orders_a_res = requests.get(f"{BASE_URL}/api/orders/user", headers=headers_a)
    assert orders_a_res.status_code == 200
    orders_a = orders_a_res.json().get("orders", [])
    assert len(orders_a) == 1, f"Customer A should have 1 order, found {len(orders_a)}"
    assert orders_a[0]["order_number"] == order1_num, "Customer A's order number mismatch"
    assert len(orders_a[0].get("items", [])) == 1, "Order items missing in Customer A's order"
    print(f"✓ 12. Customer A order history isolated: sees only Order {order1_num} with items attached")

    # 2. Customer B's orders
    orders_b_res = requests.get(f"{BASE_URL}/api/orders/user", headers=headers_b)
    assert orders_b_res.status_code == 200
    orders_b = orders_b_res.json().get("orders", [])
    assert len(orders_b) == 1, f"Customer B should have 1 order, found {len(orders_b)}"
    assert orders_b[0]["order_number"] == order2_num, "Customer B's order number mismatch"
    print(f"✓ 13. Customer B order history isolated: sees only Order {order2_num}")

    # 3. Customer C's orders (Empty state)
    orders_c_res = requests.get(f"{BASE_URL}/api/orders/user", headers=headers_c)
    assert orders_c_res.status_code == 200
    orders_c = orders_c_res.json().get("orders", [])
    assert len(orders_c) == 0, f"Customer C should have 0 orders, found {len(orders_c)}"
    print("✓ 14. Customer C empty state verified: returns []")

    # 4. CROSS-ACCOUNT 403 FORBIDDEN TEST
    # Customer A tries to access Customer B's order
    cross_res = requests.get(f"{BASE_URL}/api/orders/{order2_num}", headers=headers_a)
    assert cross_res.status_code == 403, f"Expected 403 Forbidden for cross-account access, got {cross_res.status_code}: {cross_res.text}"
    print("✓ 15. Cross-account unauthorized order query correctly returned HTTP 403 Forbidden!")

    # 5. ADMIN VERIFICATION
    admin_login = requests.post(f"{BASE_URL}/api/admin/login", json={
        "email": "vikneshvaren2@gmail.com",
        "password": "Admin@Aurelis2026!"
    })
    assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
    admin_token = admin_login.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("✓ 16. Admin authentication successful")

    admin_orders_res = requests.get(f"{BASE_URL}/api/admin/orders", headers=admin_headers)
    assert admin_orders_res.status_code == 200
    all_orders = admin_orders_res.json().get("orders", [])
    order_nums = [o["order_number"] for o in all_orders]
    assert order1_num in order_nums and order2_num in order_nums, "Admin should see all orders"
    print(f"✓ 17. Admin orders lifecycle endpoint verified ({len(all_orders)} total commissions visible to admin)")

    print("\n=======================================================")
    print("🎉 ALL 17 COMPREHENSIVE VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=======================================================")

if __name__ == "__main__":
    test_all()
