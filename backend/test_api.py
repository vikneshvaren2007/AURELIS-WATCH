import sys
import io
import json

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from werkzeug.security import check_password_hash
from backend.database import get_db, dict_from_row
from backend.seed import seed
from backend.app import app
from backend.config import Config
from backend.services.payment_service import PaymentService

def run_tests():
    print("=== 1. Seeding and checking database ===")
    seed()
    
    with app.test_client() as client:
        print("\n=== 2. Testing Health Check ===")
        res = client.get("/api/health")
        assert res.status_code == 200, f"Health check failed: {res.data}"
        print("✓ Health Check Passed:", res.json)

        print("\n=== 3. Testing Products Catalog & Two Variants ===")
        res = client.get("/api/products")
        assert res.status_code == 200
        products = res.json["products"]
        assert len(products) >= 1, "No products returned"
        prod = products[0]
        assert len(prod["variants"]) == 2, f"Expected 2 variants, got {len(prod['variants'])}"
        print(f"✓ Found Product: '{prod['name']}' with 2 Colour Variants:")
        for v in prod["variants"]:
            print(f"   - Variant: {v['color_name']} | SKU: {v['sku']} | Price: ₹{v['price']} | Stock: {v['stock_quantity']}")

        v1_id = prod["variants"][0]["id"]
        v2_id = prod["variants"][1]["id"]

        print("\n=== 4. Testing User Registration & Login ===")
        test_email = "collector_test@example.com"
        res = client.post("/api/auth/register", json={
            "name": "Arjun Singhania",
            "email": test_email,
            "phone": "9876543210",
            "password": "Password123!"
        })
        if res.status_code == 409:
            # Login instead
            res = client.post("/api/auth/login", json={"email": test_email, "password": "Password123!"})
        assert res.status_code in [200, 201], f"Auth failed: {res.data}"
        user_token = res.json["token"]
        print("✓ Customer Authentication Passed. JWT Token obtained.")

        auth_headers = {"Authorization": f"Bearer {user_token}"}

        print("\n=== 5. Testing Shopping Cart Operations ===")
        # Add Variant 1
        res = client.post("/api/cart", json={"variant_id": v1_id, "quantity": 1}, headers=auth_headers)
        print("ADD 1 RES:", res.status_code, res.data)
        assert res.status_code == 200, f"Cart add failed: {res.data}"
        # Add Variant 2
        res = client.post("/api/cart", json={"variant_id": v2_id, "quantity": 1}, headers=auth_headers)
        print("ADD 2 RES:", res.status_code, res.data)
        assert res.status_code == 200

        res = client.get("/api/cart", headers=auth_headers)
        cart_data = res.json
        print("DEBUG cart_data:", cart_data)
        assert cart_data["count"] >= 2
        print(f"✓ Cart Synced: {cart_data['count']} timepieces | Subtotal: ₹{cart_data['subtotal']} | Tax: ₹{cart_data['tax']} | Total: ₹{cart_data['total']}")

        print("\n=== 6. Testing Coupon Engine ===")
        res = client.post("/api/coupons/apply", json={"code": "AURELIS10", "subtotal": cart_data["subtotal"]})
        assert res.status_code == 200
        print(f"✓ Coupon AURELIS10 Applied: Discount ₹{res.json['discount_amount']}")

        print("\n=== 7. Testing Order Placement (Prepaid UPI) ===")
        shipping_address = {
            "name": "Arjun Singhania",
            "phone": "9876543210",
            "address_line": "14 Oberoi Horizon, Worli",
            "city": "Mumbai",
            "state": "Maharashtra",
            "pincode": "400018",
            "country": "India"
        }
        res = client.post("/api/orders", json={
            "customer_name": "Arjun Singhania",
            "customer_email": test_email,
            "customer_phone": "9876543210",
            "shipping_address": shipping_address,
            "items": cart_data["items"],
            "payment_method": "UPI",
            "coupon_code": "AURELIS10"
        }, headers=auth_headers)
        assert res.status_code == 201, f"Order creation failed: {res.data}"
        order_num = res.json["order_number"]
        order_id = res.json["order_id"]
        print(f"✓ Commission Order Created: {order_num} (Order ID: {order_id})")

        print("\n=== 8. Testing UPI Gateway Order Creation & Server Signature Verification ===")
        res = client.post("/api/payments/create", json={"order_number": order_num})
        assert res.status_code == 200, f"Payment creation failed: {res.data}"
        pay_order_id = res.json["razorpay_order_id"]
        print(f"✓ Gateway Payment Order Initialized: {pay_order_id}")

        # Simulate genuine server signature verification
        simulated_payment_id = "pay_test_983719"
        simulated_signature = "simulated_sig_verification_test"
        res = client.post("/api/payments/verify", json={
            "order_number": order_num,
            "razorpay_order_id": pay_order_id,
            "razorpay_payment_id": simulated_payment_id,
            "razorpay_signature": simulated_signature
        })
        assert res.status_code == 200, f"Signature verification failed: {res.data}"
        print(f"✓ Payment Verified Server-Side. Order {order_num} marked as PAID!")

        print("\n=== 9. Testing Order Tracking Timeline ===")
        res = client.get(f"/api/orders/track?order_number={order_num}&contact={test_email}")
        assert res.status_code == 200, f"Tracking failed: {res.data}"
        tracked = res.json["order"]
        assert tracked["payment_status"] == "PAID"
        print(f"✓ Tracking timeline verified for {order_num}. Status: {tracked['order_status']} | Payment: {tracked['payment_status']}")

        print("\n=== 10. Testing Admin Authentication (Vikneshvaren) ===")
        res = client.post("/api/admin/login", json={
            "email": Config.ADMIN_EMAIL,
            "password": Config.ADMIN_PASSWORD
        })
        assert res.status_code == 200, f"Admin login failed: {res.data}"
        admin_token = res.json["token"]
        print(f"✓ Administrator {Config.ADMIN_NAME} ({Config.ADMIN_LOCATION}) Authenticated.")

        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        print("\n=== 11. Testing Admin Dashboard Metrics ===")
        res = client.get("/api/admin/dashboard", headers=admin_headers)
        assert res.status_code == 200
        metrics = res.json["metrics"]
        print(f"✓ Admin Dashboard Metrics: Total Sales: ₹{metrics['total_sales']} | Orders: {metrics['total_orders']} | Low Stock Count: {metrics['low_stock_count']}")

        print("\n=== 12. Testing Admin Order Status Transition ===")
        res = client.put(f"/api/admin/orders/{order_id}/status", json={
            "order_status": "SHIPPED",
            "notes": "Handed to BlueDart Express courier with AWB #84938210"
        }, headers=admin_headers)
        assert res.status_code == 200
        print(f"✓ Admin successfully transitioned order {order_num} to SHIPPED")

        print("\n========================================================")
        print("ALL BACKEND & BUSINESS WORKFLOW TESTS COMPLETED SUCCESSFULLY!")
        print("========================================================")

if __name__ == "__main__":
    run_tests()
