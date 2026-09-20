import hmac
import hashlib
import json
import unittest
from backend.app import app
from backend.services.email_service import EmailService
from backend.services.payment_service import PaymentService
from backend.config import Config
from backend.database import get_db, dict_from_row

class UserAuditFixesTests(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()

    def test_01_email_service_new_methods(self):
        """Verify missing methods notify_customer_status_change and notify_customer_support_reply exist and don't throw AttributeError."""
        self.assertTrue(hasattr(EmailService, "notify_customer_status_change"), "Missing notify_customer_status_change")
        self.assertTrue(hasattr(EmailService, "notify_customer_support_reply"), "Missing notify_customer_support_reply")

        dummy_order = {
            "order_number": "WT-2026-TESTAUDIT",
            "customer_name": "Vikram Seth",
            "customer_email": "vikram@example.com",
            "order_status": "SHIPPED",
            "tracking_number": "AWB-987654321",
            "total_amount": 28000.00
        }
        
        # Test status change email dispatch (dry-run or async, checking for zero exceptions)
        try:
            status_sent = EmailService.notify_customer_status_change(dummy_order, "SHIPPED", "Handcrafted in atelier")
            # In test environment with live/mock SMTP, this should either succeed or fail gracefully without throwing AttributeError
            self.assertIsInstance(status_sent, bool)
        except AttributeError as e:
            self.fail(f"notify_customer_status_change raised AttributeError: {e}")

        # Test support reply email dispatch
        try:
            reply_sent = EmailService.notify_customer_support_reply(
                customer_name="Vikram Seth",
                customer_email="vikram@example.com",
                inquiry_subject="Bespoke Strap Inquiry",
                reply_text="Your alligator strap has been tailored to 20mm."
            )
            self.assertIsInstance(reply_sent, bool)
        except AttributeError as e:
            self.fail(f"notify_customer_support_reply raised AttributeError: {e}")

    def test_02_product_404_nonexistent(self):
        """Verify requesting a non-existent product ID or slug returns HTTP 404 instead of falling back to product 1."""
        resp_id = self.app.get("/api/products/999999")
        self.assertEqual(resp_id.status_code, 404, f"Expected 404 for invalid ID, got {resp_id.status_code}")

        resp_slug = self.app.get("/api/products/definitely-nonexistent-timepiece-slug-12345")
        self.assertEqual(resp_slug.status_code, 404, f"Expected 404 for invalid slug, got {resp_slug.status_code}")

    def test_03_cart_quantity_validation(self):
        """Verify invalid or non-positive quantities are rejected with HTTP 400."""
        session_token = "sess_audit_test_qty_validation"
        headers = {"X-Session-Token": session_token, "Content-Type": "application/json"}

        # Zero quantity
        r_zero = self.app.post("/api/cart", headers=headers, json={"product_id": 1, "quantity": 0})
        self.assertEqual(r_zero.status_code, 400)

        # Negative quantity
        r_neg = self.app.post("/api/cart", headers=headers, json={"product_id": 1, "quantity": -3})
        self.assertEqual(r_neg.status_code, 400)

        # Non-integer quantity
        r_str = self.app.post("/api/cart", headers=headers, json={"product_id": 1, "quantity": "invalid"})
        self.assertEqual(r_str.status_code, 400)

    def test_04_payment_webhook_hmac_verification_and_idempotency(self):
        """Verify POST /api/payments/webhook validates signature, updates order to PAID, and handles duplicate events idempotently."""
        import uuid
        test_order_num = f"WT-2026-WH-{uuid.uuid4().hex[:8].upper()}"
        with get_db() as conn:
            cursor = conn.cursor()
            # Create a test order
            cursor.execute("""
                INSERT INTO orders (
                    order_number, customer_name, customer_email, customer_phone,
                    shipping_address, payment_method, payment_status, order_status,
                    subtotal, tax_amount, shipping_fee, total_amount
                ) VALUES (
                    ?, 'Webhook Patron', 'webhook@example.com', '9876543210',
                    '101 Horology Lane, Tenkasi', 'UPI / Razorpay', 'PENDING', 'ORDER_PLACED',
                    25000.0, 4500.0, 0.0, 29500.0
                )
            """, (test_order_num,))
            conn.commit()

        webhook_payload = {
            "event": "payment.captured",
            "id": f"evt_{uuid.uuid4().hex[:12]}",
            "payload": {
                "payment": {
                    "entity": {
                        "id": f"pay_{uuid.uuid4().hex[:12]}",
                        "order_id": f"order_{uuid.uuid4().hex[:12]}",
                        "status": "captured",
                        "amount": 2950000,
                        "notes": {
                            "order_number": test_order_num
                        }
                    }
                }
            }
        }
        raw_body = json.dumps(webhook_payload).encode("utf-8")
        secret = Config.PAYMENT_WEBHOOK_SECRET or "aurelis_webhook_secret_2026"
        valid_signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

        # 1. Invalid signature should be rejected (400)
        resp_bad = self.app.post(
            "/api/payments/webhook",
            data=raw_body,
            headers={"X-Razorpay-Signature": "invalid_signature_hex", "Content-Type": "application/json"}
        )
        self.assertEqual(resp_bad.status_code, 400)

        # 2. Valid signature should succeed (200)
        resp_good = self.app.post(
            "/api/payments/webhook",
            data=raw_body,
            headers={"X-Razorpay-Signature": valid_signature, "Content-Type": "application/json"}
        )
        self.assertEqual(resp_good.status_code, 200)
        data = resp_good.get_json()
        self.assertEqual(data.get("status"), "processed")

        # Check DB to verify order marked PAID
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payment_status FROM orders WHERE order_number = ?", (test_order_num,))
            order = dict_from_row(cursor.fetchone())
            self.assertEqual(order["payment_status"], "PAID")

        # 3. Duplicate event should be handled idempotently (200)
        resp_dup = self.app.post(
            "/api/payments/webhook",
            data=raw_body,
            headers={"X-Razorpay-Signature": valid_signature, "Content-Type": "application/json"}
        )
        self.assertEqual(resp_dup.status_code, 200)
        self.assertEqual(resp_dup.get_json().get("status"), "already_processed")

    def test_05_reviews_api(self):
        """Verify submitting and retrieving customer reviews."""
        # Submit a review
        rev_payload = {
            "product_id": 1,
            "user_name": "Lord Horologist",
            "rating": 5,
            "title": "Unmatched horological symmetry",
            "comment": "The balance wheel pulsation and hand-finished indices are of Patek caliber."
        }
        r_post = self.app.post("/api/reviews", json=rev_payload)
        self.assertEqual(r_post.status_code, 201)

        # Get reviews for product 1
        r_get = self.app.get("/api/reviews/product/1")
        self.assertEqual(r_get.status_code, 200)
        reviews = r_get.get_json().get("reviews", [])
        self.assertTrue(any(r["title"] == "Unmatched horological symmetry" for r in reviews))

if __name__ == "__main__":
    unittest.main()
