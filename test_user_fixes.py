import unittest
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from backend.app import app
from backend.models import init_db
from backend.database import get_db, dict_from_row
from werkzeug.security import check_password_hash

IST = ZoneInfo("Asia/Kolkata")

class AurelisUserFixesTests(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        init_db()

    def test_01_order_id_format_and_sequential(self):
        """Verify order ID strictly follows WT-2026-XXXXXX sequential collision-free format."""
        session_token = "test_session_order_id_check"
        headers = {"X-Session-Token": session_token, "Content-Type": "application/json"}
        
        # Add item to cart
        self.app.post("/api/cart", headers=headers, json={"product_id": 1, "quantity": 1})

        payload = {
            "customer_name": "Arjun Sharma",
            "customer_email": "arjun.sharma@example.com",
            "customer_phone": "9876543210",
            "shipping_address": {
                "flat": "Suite 101",
                "street": "MG Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001"
            },
            "payment_method": "COD"
        }
        res = self.app.post("/api/orders", headers=headers, json=payload)
        self.assertEqual(res.status_code, 201)
        order = res.get_json()["order"]
        order_num = order["order_number"]
        
        self.assertTrue(order_num.startswith("WT-2026-"), f"Expected WT-2026-XXXXXX, got {order_num}")
        self.assertEqual(len(order_num), 14, f"Expected 14 chars (WT-2026-000001), got {len(order_num)}: {order_num}")
        seq_part = order_num.split("-")[2]
        self.assertTrue(seq_part.isdigit() and len(seq_part) == 6)

    def test_02_cart_cleared_after_order(self):
        """Verify cart items in database are deleted upon successful order placement."""
        session_token = "test_session_cart_clear_check"
        headers = {"X-Session-Token": session_token, "Content-Type": "application/json"}
        
        # Add 2 items
        self.app.post("/api/cart", headers=headers, json={"product_id": 1, "quantity": 1})
        self.app.post("/api/cart", headers=headers, json={"product_id": 2, "quantity": 1})

        # Check cart before order
        res_before = self.app.get("/api/cart", headers=headers)
        self.assertEqual(len(res_before.get_json()["items"]), 2)

        payload = {
            "customer_name": "Priya Nair",
            "customer_email": "priya@example.com",
            "customer_phone": "9812345678",
            "shipping_address": {
                "flat": "Villa 12",
                "street": "Koramangala",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560034"
            },
            "payment_method": "COD"
        }
        res_order = self.app.post("/api/orders", headers=headers, json=payload)
        self.assertEqual(res_order.status_code, 201)

        # Cart should now be completely empty in database
        res_after = self.app.get("/api/cart", headers=headers)
        self.assertEqual(len(res_after.get_json()["items"]), 0)
        self.assertEqual(res_after.get_json()["subtotal"], 0)

    def test_03_order_tracking_and_ist_timestamps(self):
        """Verify tracking returns IST formatted dates, customer details, address, and items."""
        session_token = "test_session_track_check"
        headers = {"X-Session-Token": session_token, "Content-Type": "application/json"}
        self.app.post("/api/cart", headers=headers, json={"product_id": 3, "quantity": 1})

        payload = {
            "customer_name": "Dev Patel",
            "customer_email": "dev.patel@example.com",
            "customer_phone": "9988776655",
            "shipping_address": {
                "flat": "Flat 302",
                "street": "Park Street",
                "city": "Kolkata",
                "state": "West Bengal",
                "pincode": "700016"
            },
            "payment_method": "COD"
        }
        res = self.app.post("/api/orders", headers=headers, json=payload)
        order_num = res.get_json()["order"]["order_number"]

        # Track order
        res_track = self.app.get(f"/api/orders/track?order_number={order_num}")
        self.assertEqual(res_track.status_code, 200)
        tracked = res_track.get_json()["order"]

        self.assertEqual(tracked["order_number"], order_num)
        self.assertIn("order_date", tracked)
        self.assertIn("order_time", tracked)
        self.assertTrue(tracked["order_time"].endswith("IST"))
        self.assertEqual(tracked["customer_name"], "Dev Patel")
        self.assertEqual(tracked["customer_email"], "dev.patel@example.com")
        self.assertEqual(len(tracked["items"]), 1)
        self.assertIn("image_url", tracked["items"][0])

    def test_04_order_cancellation_restores_stock_and_leaves_record(self):
        """Verify cancellation updates order_status to CANCELLED and restores product stock."""
        session_token = "test_session_cancel_check"
        headers = {"X-Session-Token": session_token, "Content-Type": "application/json"}
        
        # Check stock of product 4 before order
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT stock_quantity FROM products WHERE id = 4")
            stock_before = cursor.fetchone()["stock_quantity"]

        self.app.post("/api/cart", headers=headers, json={"product_id": 4, "quantity": 2})

        payload = {
            "customer_name": "Karan Mehra",
            "customer_email": "karan@example.com",
            "customer_phone": "9876501234",
            "shipping_address": {
                "flat": "B-44",
                "street": "Bandra West",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400050"
            },
            "payment_method": "COD"
        }
        res = self.app.post("/api/orders", headers=headers, json=payload)
        order_num = res.get_json()["order"]["order_number"]

        # Verify stock decreased by 2
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT stock_quantity FROM products WHERE id = 4")
            stock_after_order = cursor.fetchone()["stock_quantity"]
            self.assertEqual(stock_after_order, stock_before - 2)

        # Cancel the order
        res_cancel = self.app.post(f"/api/orders/{order_num}/cancel", json={"reason": "Test cancellation"})
        self.assertEqual(res_cancel.status_code, 200)

        # Verify status is CANCELLED in DB, not deleted
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT order_status, stock_quantity FROM orders o JOIN products p ON p.id = 4 WHERE o.order_number = ?", (order_num,))
            row = cursor.fetchone()
            self.assertEqual(row["order_status"], "CANCELLED")
            # Stock must be restored
            self.assertEqual(row["stock_quantity"], stock_before)

    def test_05_forgot_password_and_reset_flow(self):
        """Verify full forgot password -> verify token -> reset password -> login with new password flow."""
        test_email = "test.reset.user@example.com"
        orig_pass = "SecurePass123!"
        new_pass = "BrandNewPass456#"

        # 1. Register test user
        reg_res = self.app.post("/api/auth/register", json={
            "name": "Reset Test User",
            "email": test_email,
            "phone": "9876543299",
            "password": orig_pass
        })
        # If already registered, proceed
        self.assertIn(reg_res.status_code, [200, 201, 400, 409])

        # 2. Request forgot password
        forgot_res = self.app.post("/api/auth/forgot-password", json={"email": test_email})
        self.assertEqual(forgot_res.status_code, 200)
        forgot_data = forgot_res.get_json()
        self.assertTrue(forgot_data["success"])
        reset_token = forgot_data["token"]
        self.assertTrue(reset_token)

        # 3. Verify token
        verify_res = self.app.get(f"/api/auth/verify-reset-token?token={reset_token}")
        self.assertEqual(verify_res.status_code, 200)
        self.assertTrue(verify_res.get_json()["valid"])
        self.assertEqual(verify_res.get_json()["email"], test_email)

        # 4. Reset password
        reset_res = self.app.post("/api/auth/reset-password", json={
            "token": reset_token,
            "password": new_pass
        })
        self.assertEqual(reset_res.status_code, 200)
        self.assertTrue(reset_res.get_json()["success"])

        # 5. Token reuse must fail
        reuse_res = self.app.post("/api/auth/reset-password", json={
            "token": reset_token,
            "password": "AnotherPassword789$"
        })
        self.assertEqual(reuse_res.status_code, 400)

        # 6. Login with old password must fail
        bad_login = self.app.post("/api/auth/login", json={
            "email": test_email,
            "password": orig_pass
        })
        self.assertEqual(bad_login.status_code, 401)

        # 7. Login with new password must succeed
        good_login = self.app.post("/api/auth/login", json={
            "email": test_email,
            "password": new_pass
        })
        self.assertEqual(good_login.status_code, 200)
        self.assertIn("token", good_login.get_json())

if __name__ == "__main__":
    unittest.main()
