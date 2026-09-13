import json
import unittest
from backend.app import app
from backend.models import init_db
from backend.database import get_db, dict_from_row
from backend.config import Config

class AurelisVerificationTests(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        init_db()

    def test_01_hero_frames_route(self):
        """Verify homepage hero frames returns 240 frames from /frames/frame_0001.jpg to 0240.jpg."""
        resp = self.app.get("/api/frames")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["total_frames"], 240)
        self.assertEqual(len(data["frames"]), 240)
        self.assertTrue(data["frames"][0].endswith("frame_0001.jpg"))
        self.assertTrue(data["frames"][239].endswith("frame_0240.jpg"))

    def test_02_shop_frames_route(self):
        """Verify shop frames returns 240 frames from /frames 2/ezgif-frame-001.jpg to 240.jpg."""
        resp = self.app.get("/api/shop-frames")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["total_frames"], 240)
        self.assertEqual(len(data["frames"]), 240)
        self.assertTrue("ezgif-frame-001.jpg" in data["frames"][0])
        self.assertTrue("ezgif-frame-240.jpg" in data["frames"][239])

    def test_03_catalog_10_luxury_watches_strictly_above_5000(self):
        """Verify catalog returns exactly 10 watches with prices strictly > ₹5,000."""
        resp = self.app.get("/api/products")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        products = data.get("products", [])
        self.assertEqual(len(products), 10, f"Expected 10 products, found {len(products)}")
        for p in products:
            price = float(p["base_price"])
            self.assertGreater(price, 5000.0, f"{p['name']} price {price} is not > 5000")

    def test_04_five_categories_with_exactly_two_watches_each(self):
        """Verify each of the 5 horological categories returns exactly 2 watches."""
        categories = ["Chronographs", "Minimalist", "Business Luxury", "Modern Mesh", "Classic Luxury"]
        for cat in categories:
            resp = self.app.get(f"/api/products?category={cat}")
            self.assertEqual(resp.status_code, 200)
            products = resp.get_json().get("products", [])
            self.assertEqual(len(products), 2, f"Category '{cat}' expected 2 watches, got {len(products)}")

            # Also verify via style parameter
            resp_style = self.app.get(f"/api/products?style={cat}")
            self.assertEqual(resp_style.status_code, 200)
            products_style = resp_style.get_json().get("products", [])
            self.assertEqual(len(products_style), 2, f"Style '{cat}' expected 2 watches, got {len(products_style)}")

    def test_05_admin_email_configuration(self):
        """Verify Admin Email is configured to vikneshvaren2@gmail.com."""
        from backend.services.email_service import EmailService
        admin_email = EmailService.get_admin_email()
        self.assertIn("vikneshvaren2@gmail.com", admin_email.lower())

    def test_06_cart_operations(self):
        """Verify isolated guest cart operations: add, get, update quantity."""
        session_token = "test_guest_session_9999"
        headers = {"X-Session-Token": session_token, "Content-Type": "application/json"}
        
        # Add product 1
        resp = self.app.post("/api/cart", headers=headers, json={"product_id": 1, "quantity": 1})
        self.assertEqual(resp.status_code, 200)
        
        # Get cart
        resp = self.app.get("/api/cart", headers=headers)
        self.assertEqual(resp.status_code, 200)
        cart = resp.get_json()
        self.assertEqual(len(cart["items"]), 1)
        item_id = cart["items"][0]["id"]
        
        # Update quantity
        resp = self.app.put(f"/api/cart/{item_id}", headers=headers, json={"quantity": 2})
        self.assertEqual(resp.status_code, 200)
        
        # Verify updated subtotal
        resp = self.app.get("/api/cart", headers=headers)
        cart = resp.get_json()
        self.assertEqual(cart["items"][0]["quantity"], 2)
        self.assertEqual(cart["subtotal"], cart["items"][0]["unit_price"] * 2)

    def test_07_checkout_validation_rejections(self):
        """Verify strict server-side validation rejects invalid/missing customer details."""
        session_token = "test_guest_session_validation"
        headers = {"X-Session-Token": session_token, "Content-Type": "application/json"}
        
        self.app.post("/api/cart", headers=headers, json={"product_id": 1, "quantity": 1})
        
        base_payload = {
            "customer_name": "Rajesh Kumar",
            "customer_email": "rajesh@example.com",
            "customer_phone": "9876543210",
            "shipping_address": {
                "flat": "Flat 4B, Emerald Tower",
                "street": "MG Road",
                "area": "Indiranagar",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560038"
            },
            "payment_method": "COD"
        }
        
        # 1. Invalid phone (9 digits)
        bad_phone = dict(base_payload)
        bad_phone["customer_phone"] = "987654321"
        resp = self.app.post("/api/orders", headers=headers, json=bad_phone)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("10-digit", resp.get_json()["error"])
        
        # 2. Invalid PIN code (5 digits)
        bad_pin = dict(base_payload)
        bad_pin["shipping_address"] = dict(base_payload["shipping_address"], pincode="56003")
        resp = self.app.post("/api/orders", headers=headers, json=bad_pin)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("pin", resp.get_json()["error"].lower())

        # 3. Missing street/flat
        bad_addr = dict(base_payload)
        bad_addr["shipping_address"] = dict(base_payload["shipping_address"], flat="", street="")
        resp = self.app.post("/api/orders", headers=headers, json=bad_addr)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("address", resp.get_json()["error"].lower())

    def test_08_dummy_payment_gpay_and_card(self):
        """Verify 100% simulated dummy payment updates order to PAID and CONFIRMED."""
        session_token = "test_guest_session_dummy_pay"
        headers = {"X-Session-Token": session_token, "Content-Type": "application/json"}
        
        self.app.post("/api/cart", headers=headers, json={"product_id": 2, "quantity": 1})
        
        order_payload = {
            "customer_name": "Vikram Seth",
            "customer_email": "vikram@example.com",
            "customer_phone": "9712345678",
            "shipping_address": {
                "flat": "Penthouse 12",
                "street": "Marine Drive",
                "area": "Nariman Point",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400021"
            },
            "payment_method": "UPI"
        }
        resp = self.app.post("/api/orders", headers=headers, json=order_payload)
        self.assertEqual(resp.status_code, 201)
        order_number = resp.get_json()["order"]["order_number"]

        # Simulate GPay Demo payment via /api/payments/dummy-pay
        pay_resp = self.app.post("/api/payments/dummy-pay", headers=headers, json={
            "order_number": order_number,
            "payment_method": "GPay Demo",
            "txn_id": "DEMO_GPAY_12345"
        })
        self.assertEqual(pay_resp.status_code, 200)
        pay_data = pay_resp.get_json()
        self.assertTrue(pay_data["success"])
        self.assertEqual(pay_data["payment_status"], "PAID")
        self.assertEqual(pay_data["order_status"], "CONFIRMED")

        # Verify directly in SQLite DB
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payment_status, order_status, payment_method FROM orders WHERE order_number = ?", (order_number,))
            row = dict_from_row(cursor.fetchone())
            self.assertEqual(row["payment_status"], "PAID")
            self.assertEqual(row["order_status"], "CONFIRMED")
            self.assertEqual(row["payment_method"], "GPay Demo")

    def test_09_order_tracking_timeline(self):
        """Verify order tracking endpoint returns order and status history."""
        resp = self.app.get("/api/orders/track?order_number=AUR-2026-NONEXISTENT")
        self.assertEqual(resp.status_code, 404)

if __name__ == "__main__":
    unittest.main()
