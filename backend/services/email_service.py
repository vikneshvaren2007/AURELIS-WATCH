import smtplib
import json
import datetime
from zoneinfo import ZoneInfo
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from backend.config import Config
from backend.database import get_db

IST = ZoneInfo("Asia/Kolkata")

class EmailService:
    @staticmethod
    def get_admin_email():
        """Fetches admin email dynamically from site_settings or falls back to config."""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM site_settings WHERE key = 'admin_email'")
                row = cursor.fetchone()
                if row and row["value"]:
                    return row["value"].strip()
        except Exception:
            pass
        return Config.ADMIN_EMAIL or "vikneshvaren2@gmail.com"

    @staticmethod
    def get_ist_now():
        return datetime.datetime.now(IST).strftime("%d %B %Y, %I:%M %p IST")

    @staticmethod
    def _render_luxury_template(title, headline, message_body, order_details=None, cta_text=None, cta_link=None, is_admin=False):
        cta_html = ""
        if cta_text and cta_link:
            cta_html = f"""
            <div style="text-align: center; margin: 35px 0;">
                <a href="{cta_link}" style="background: #d9ae55; color: #080807; text-decoration: none; padding: 14px 28px; font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase; font-weight: 600; display: inline-block; border-radius: 2px;">
                    {cta_text}
                </a>
            </div>
            """

        details_html = ""
        if order_details:
            rows_html = ""
            for k, v in order_details.items():
                rows_html += f"""
                <div style="display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #1c1a16; font-size: 13px;">
                    <span style="color: #8c877e; text-transform: uppercase; font-size: 11px; letter-spacing: 0.1em;">{k}</span>
                    <strong style="color: #f5f0e7; text-align: right;">{v}</strong>
                </div>
                """
            details_html = f"""
            <div style="border: 1px solid #28241e; background: #0c0b09; padding: 22px; margin: 25px 0; border-radius: 4px;">
                <p style="color: #d9ae55; margin: 0 0 14px 0; font-size: 11px; letter-spacing: 0.15em; text-transform: uppercase;">Commission Overview</p>
                {rows_html}
            </div>
            """

        header_badge = "ADMINISTRATIVE DISPATCH &bull; STRICTLY CONFIDENTIAL" if is_admin else "HAUTE HORLOGERIE &bull; TIME / FORM / PRECISION"

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ margin:0; padding:0; background-color:#050504; font-family:'Helvetica Neue', Arial, sans-serif; color:#dfdad1; }}
</style>
</head>
<body style="background-color:#050504; padding: 40px 15px;">
  <div style="max-width: 620px; margin: 0 auto; background-color: #080807; border: 1px solid #23201b; padding: 40px 30px; border-radius: 6px;">
    <div style="text-align: center; padding-bottom: 25px; border-bottom: 1px solid #1c1a16;">
      <h1 style="color: #f5f0e7; letter-spacing: 0.25em; font-size: 22px; font-weight: 500; margin: 0;">A U R E L I S</h1>
      <p style="color: #d9ae55; font-size: 9px; letter-spacing: 0.3em; margin-top: 6px; text-transform: uppercase;">{header_badge}</p>
    </div>
    
    <div style="padding: 30px 10px;">
      <p style="color: #d9ae55; font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase; margin-bottom: 8px;">{title}</p>
      <h2 style="color: #f5f0e7; font-size: 24px; font-weight: 400; line-height: 1.3; margin: 0 0 18px 0;">{headline}</h2>
      <div style="color: #aaa59c; font-size: 14px; line-height: 1.8;">
        {message_body}
      </div>
      {details_html}
      {cta_html}
    </div>
    
    <div style="border-top: 1px solid #1c1a16; padding-top: 25px; text-align: center; font-size: 11px; color: #6a665f; line-height: 1.6;">
      <p style="margin: 0; color: #d9ae55;">AURELIS Client Concierge & Atelier</p>
      <p style="margin: 4px 0;">Administrator: {Config.ADMIN_NAME} &bull; +91 {Config.ADMIN_PHONE}</p>
      <p style="margin: 4px 0;">{Config.ADMIN_LOCATION}</p>
      <p style="margin: 12px 0 0 0; font-size: 10px; color: #4a4742;">&copy; 2026 AURELIS Timepieces. Indian Rupees (₹) Only &bull; 6-Month Warranty.</p>
    </div>
  </div>
</body>
</html>"""

    @classmethod
    def send_email(cls, to_email, subject, title, headline, message_body, order_details=None, cta_text=None, cta_link=None, is_admin=False):
        """Dispatches an email via SMTP or logs cleanly if SMTP credentials are unset."""
        try:
            html_content = cls._render_luxury_template(title, headline, message_body, order_details, cta_text, cta_link, is_admin)
            
            recipient = to_email or cls.get_admin_email()
            safe_msg = f"[Email Notification Logged] Destination: {recipient} | Subject: {subject} | Title: {title}".replace("\u20b9", "INR ")
            try:
                print(safe_msg)
            except Exception:
                try:
                    print(safe_msg.encode("ascii", errors="replace").decode("ascii"))
                except Exception:
                    pass

            if not Config.EMAIL_USERNAME or not Config.EMAIL_PASSWORD:
                return True

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"AURELIS Concierge <{Config.EMAIL_FROM or Config.EMAIL_USERNAME}>"
            msg["To"] = recipient
            msg.attach(MIMEText(html_content, "html"))

            import threading
            def _async_send():
                try:
                    with smtplib.SMTP(Config.EMAIL_HOST, Config.EMAIL_PORT, timeout=10) as server:
                        server.starttls()
                        server.login(Config.EMAIL_USERNAME, Config.EMAIL_PASSWORD)
                        server.sendmail(msg["From"], [recipient], msg.as_string())
                    print(f"[Email Sent Successfully] Destination: {recipient} | Subject: {subject}".replace("\u20b9", "INR "))
                except Exception as e:
                    try:
                        print(f"[Email Sending Exception to {recipient}] {e}".replace("\u20b9", "INR "))
                    except Exception:
                        pass

            threading.Thread(target=_async_send, daemon=True).start()
            return True
        except Exception as e:
            try:
                print(f"[Email Sending Exception to {to_email}] {e}".replace("\u20b9", "INR "))
            except Exception:
                pass
            return False

    # =========================================================================
    # ADMIN NOTIFICATIONS (Sent directly to VIKNESHVAREN2@GMAIL.COM)
    # =========================================================================
    @classmethod
    def notify_admin_new_order(cls, order, items):
        try:
            admin_email = cls.get_admin_email()
            addr = order.get("shipping_address", {})
            if isinstance(addr, str):
                try:
                    addr = json.loads(addr)
                except Exception:
                    addr = {"address_line": addr}

            flat = addr.get("flat_no") or addr.get("flat") or addr.get("house", "")
            street = addr.get("street", "")
            area = addr.get("area", "")
            landmark = addr.get("landmark", "")
            city = addr.get("city", "")
            district = addr.get("district", city)
            state = addr.get("state", "")
            pincode = addr.get("pincode", "")
            country = addr.get("country", "India")

            full_addr_str = f"{flat}, {street}, {area}".strip(", ")
            if landmark:
                full_addr_str += f" (Near {landmark})"
            if district and district != city:
                full_addr_str += f", {district}"
            full_addr_str += f", {city}, {state} - {pincode}, {country}".strip(", ")
            if not full_addr_str or full_addr_str.replace("-", "").strip() == "":
                full_addr_str = addr.get("address_line", "Address on file")

            items_desc = "<br>".join([
                f"• <strong>{i.get('product_name')}</strong> ({i.get('color_name', 'Standard')}) &times; {i.get('quantity')} @ ₹{float(i.get('price') or i.get('unit_price') or 0):,.2f} = <strong>₹{float(i.get('total_price', 0)):,.2f}</strong>"
                for i in items
            ])

            details = {
                "ORDER ID": order.get("order_number"),
                "DATE & TIME (IST)": cls.get_ist_now(),
                "CUSTOMER NAME": order.get("customer_name"),
                "CUSTOMER EMAIL": order.get("customer_email"),
                "CUSTOMER PHONE": f"+91 {order.get('customer_phone')}",
                "DELIVERY ADDRESS": full_addr_str,
                "PINCODE": pincode or "Verified",
                "ORDER NOTE": order.get("order_note") or "None specified",
                "SUBTOTAL": f"₹{float(order.get('subtotal', 0)):,.2f}",
                "DELIVERY CHARGE": "₹0.00 (Complimentary Insured)",
                "TOTAL COMMISSION": f"₹{float(order.get('total_amount', 0)):,.2f}",
                "PAYMENT METHOD": order.get("payment_method"),
                "PAYMENT STATUS": order.get("payment_status"),
                "ORDER STATUS": order.get("order_status"),
                "WARRANTY": "6-Month Manufacturer Warranty Active"
            }

            body = f"""
            A new acquisition commission has been recorded on the AURELIS atelier network.<br><br>
            <strong>Commissioned Timepieces:</strong><br>
            {items_desc}
            """

            return cls.send_email(
                to_email=admin_email,
                subject=f"[NEW ORDER] #{order.get('order_number')} ({order.get('payment_method')}) — ₹{float(order.get('total_amount', 0)):,.2f}",
                title="Immediate Atelier Commission",
                headline=f"New Order #{order.get('order_number')} Received",
                message_body=body,
                order_details=details,
                cta_text="Inspect in Admin Console",
                cta_link="/admin/orders.html",
                is_admin=True
            )
        except Exception as err:
            print(f"[Email notify_admin_new_order Error] {err}")
            return False

    @classmethod
    def notify_admin_payment_event(cls, order, status, txn_id=None):
        try:
            admin_email = cls.get_admin_email()
            details = {
                "ORDER ID": order.get("order_number"),
                "CUSTOMER": f"{order.get('customer_name')} ({order.get('customer_phone')})",
                "AMOUNT": f"₹{float(order.get('total_amount', 0)):,.2f}",
                "PAYMENT METHOD": order.get("payment_method"),
                "PAYMENT STATUS": status,
                "TRANSACTION REF": txn_id or "N/A",
                "TIMESTAMP (IST)": cls.get_ist_now()
            }
            return cls.send_email(
                to_email=admin_email,
                subject=f"[PAYMENT {status.upper()}] Order #{order.get('order_number')} — ₹{float(order.get('total_amount', 0)):,.2f}",
                title="Gateway Payment Event",
                headline=f"Payment {status.title()} for Order #{order.get('order_number')}",
                message_body=f"Payment transaction update recorded. Transaction Reference: <code>{txn_id or 'N/A'}</code>.",
                order_details=details,
                is_admin=True
            )
        except Exception as err:
            print(f"[Email notify_admin_payment_event Error] {err}")
            return False

    @classmethod
    def notify_admin_cancellation(cls, order, reason):
        try:
            admin_email = cls.get_admin_email()
            details = {
                "ORDER ID": order.get("order_number"),
                "CUSTOMER": f"{order.get('customer_name')} ({order.get('customer_phone')})",
                "AMOUNT": f"₹{float(order.get('total_amount', 0)):,.2f}",
                "PAYMENT METHOD": order.get("payment_method"),
                "CANCELLATION REASON": reason,
                "TIMESTAMP (IST)": cls.get_ist_now()
            }
            return cls.send_email(
                to_email=admin_email,
                subject=f"[CANCELLATION] Order #{order.get('order_number')} Cancelled",
                title="Commission Cancelled",
                headline=f"Order #{order.get('order_number')} Has Been Cancelled",
                message_body=f"Customer has submitted a cancellation request for order #{order.get('order_number')}. Inventory stock has been returned to available atelier reserve.",
                order_details=details,
                cta_text="Manage Cancellations",
                cta_link="/admin/cancellations.html",
                is_admin=True
            )
        except Exception as err:
            print(f"[Email notify_admin_cancellation Error] {err}")
            return False

    @classmethod
    def notify_admin_return_request(cls, order, reason, description):
        try:
            admin_email = cls.get_admin_email()
            details = {
                "ORDER ID": order.get("order_number"),
                "CUSTOMER": f"{order.get('customer_name')} ({order.get('customer_phone')})",
                "TOTAL VALUE": f"₹{float(order.get('total_amount', 0)):,.2f}",
                "RETURN REASON": reason,
                "DESCRIPTION": description,
                "TIMESTAMP (IST)": cls.get_ist_now()
            }
            return cls.send_email(
                to_email=admin_email,
                subject=f"[RETURN REQUEST] Order #{order.get('order_number')}",
                title="Return Request Initiated",
                headline=f"Return Requested for #{order.get('order_number')}",
                message_body=f"A customer has requested a return under the 6-Month / 7-Day policy. Reason: <em>{reason}</em>.",
                order_details=details,
                cta_text="Inspect Return Case",
                cta_link="/admin/returns.html",
                is_admin=True
            )
        except Exception as err:
            print(f"[Email notify_admin_return_request Error] {err}")
            return False

    @classmethod
    def notify_admin_customer_message(cls, name, email, phone, subject, message, order_number=None):
        try:
            admin_email = cls.get_admin_email()
            details = {
                "SENDER NAME": name,
                "EMAIL": email,
                "PHONE": phone or "N/A",
                "SUBJECT": subject,
                "RELATED ORDER": order_number or "N/A",
                "TIME (IST)": cls.get_ist_now()
            }
            return cls.send_email(
                to_email=admin_email,
                subject=f"[SUPPORT INQUIRY] {subject} — From {name}",
                title="Concierge Client Inquiry",
                headline=f"Inquiry from {name}",
                message_body=f"<strong>Message:</strong><br><blockquote style='border-left: 2px solid #d9ae55; padding-left: 12px; margin: 10px 0; color: #dfdad1;'>{message}</blockquote>",
                order_details=details,
                cta_text="Reply in Admin Console",
                cta_link="/admin/messages.html",
                is_admin=True
            )
        except Exception as err:
            print(f"[Email notify_admin_customer_message Error] {err}")
            return False

    # =========================================================================
    # CUSTOMER NOTIFICATIONS (2-Line Concise Format per Specification)
    # =========================================================================
    @classmethod
    def notify_customer_order_confirmation(cls, order, items):
        try:
            order_number = order.get("order_number")
            track_url = f"track-order.html?order_id={order_number}"

            items_summary = "<br>".join([
                f"• <strong>{i.get('product_name')}</strong> ({i.get('color_name', 'Standard')}) &times; {i.get('quantity')} — <strong>₹{float(i.get('total_price', 0)):,.2f}</strong>"
                for i in items
            ])

            body = f"""
            <p style="font-size: 15px; color: #f5f0e7; margin: 0 0 12px 0; line-height: 1.6;">
                Your AURELIS order <strong>{order_number}</strong> has been placed successfully.
            </p>
            <p style="font-size: 14px; color: #dfdad1; margin: 0 0 20px 0; line-height: 1.6;">
                Estimated delivery: 3-5 business days. Track your order at <a href="{track_url}" style="color: #d9ae55; text-decoration: underline;">{track_url}</a>
            </p>
            <div style="background: #0f0e0c; border: 1px solid #23201b; padding: 16px; margin: 16px 0; border-radius: 4px;">
                <p style="color: #d9ae55; margin: 0 0 8px 0; font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; font-weight: 600;">Timepieces Summary:</p>
                {items_summary}
            </div>
            """

            details = {
                "ORDER ID": order_number,
                "ORDER DATE (IST)": cls.get_ist_now(),
                "PAYMENT METHOD": order.get("payment_method"),
                "TOTAL AMOUNT": f"₹{float(order.get('total_amount', 0)):,.2f}",
                "WARRANTY": "6-Month Official Atelier Warranty"
            }

            return cls.send_email(
                to_email=order.get("customer_email"),
                subject=f"Your AURELIS Order #{order_number} Confirmation",
                title="Order Placed Successfully",
                headline=f"Order #{order_number} Confirmed",
                message_body=body,
                order_details=details,
                cta_text="Track Order Status",
                cta_link=f"/track-order.html?order_id={order_number}"
            )
        except Exception as err:
            print(f"[Email notify_customer_order_confirmation Error] {err}")
            return False

    @classmethod
    def notify_customer_status_change(cls, order, new_status, notes=""):
        status_readable = new_status.replace("_", " ").title()
        details = {
            "ORDER NUMBER": order.get("order_number"),
            "LATEST STATUS": status_readable,
            "AMOUNT": f"₹{float(order.get('total_amount', 0)):,.2f}",
            "WARRANTY": "6-Month Manufacturer Warranty Active",
            "UPDATED AT (IST)": cls.get_ist_now()
        }
        body = f"""
        The status of your timepiece commission #{order.get('order_number')} has progressed to: <strong>{status_readable}</strong>.
        <br><br>
        <strong>Atelier Notes:</strong> {notes or 'Your order is progressing smoothly through our fulfillment pipeline.'}
        """
        return cls.send_email(
            to_email=order.get("customer_email"),
            subject=f"Order #{order.get('order_number')} Update: {status_readable}",
            title="Commission Milestone",
            headline=f"Your Order is now {status_readable}",
            message_body=body,
            order_details=details,
            cta_text="View Live Tracking",
            cta_link=f"/track-order.html?order_id={order.get('order_number')}&contact={order.get('customer_email')}"
        )

    @classmethod
    def notify_customer_support_reply(cls, name, email, original_subject, reply_message):
        body = f"""
        Dear {name},
        <br><br>
        Administrator Vikneshvaren from the AURELIS atelier has responded to your inquiry regarding <strong>"{original_subject}"</strong>:
        <br><br>
        <div style="background: #0f0e0c; border-left: 3px solid #d9ae55; padding: 18px; margin: 15px 0; color: #f5f0e7; font-size: 14px; line-height: 1.8;">
          {reply_message}
        </div>
        <br>
        If you have any further questions, simply reply to this email or call our direct concierge line at +91 {Config.ADMIN_PHONE}.
        """
        return cls.send_email(
            to_email=email,
            subject=f"Re: {original_subject} — AURELIS Client Concierge",
            title="Concierge Response",
            headline=f"Message for {name}",
            message_body=body,
            cta_text="Explore Collection",
            cta_link="/shop.html"
        )

    @classmethod
    def send_password_reset_email(cls, to_email, customer_name, reset_token, reset_link):
        try:
            details = {
                "ACCOUNT EMAIL": to_email,
                "TOKEN VALIDITY": "15 Minutes (One-Time Use)",
                "TIMESTAMP (IST)": cls.get_ist_now(),
                "SECURITY": "Do not share this code with anyone"
            }
            body = f"""
            Dear {customer_name or 'Collector'},
            <br><br>
            A request was initiated to reset your AURELIS account password.
            <br><br>
            Please use the secure button below to set your new password, or copy the one-time reset token:
            <br><br>
            <div style="background: #0f0e0c; border: 1px solid #28241e; padding: 18px; margin: 15px 0; border-radius: 4px; text-align: center;">
                <p style="color: #d9ae55; font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase; margin: 0 0 8px 0;">One-Time Security Token</p>
                <code style="font-family: monospace; font-size: 15px; color: #f5f0e7; word-break: break-all;">{reset_token}</code>
            </div>
            <p style="font-size: 12px; color: #8c877e; line-height: 1.6;">
                For your security, this password reset link is valid for 15 minutes and will expire immediately after use. If you did not make this request, your account remains secure and no action is required.
            </p>
            """
            return cls.send_email(
                to_email=to_email,
                subject="Reset Your AURELIS Account Password",
                title="Account Recovery Desk",
                headline="Password Reset Authorization",
                message_body=body,
                order_details=details,
                cta_text="Reset Account Password",
                cta_link=reset_link
            )
        except Exception as err:
            print(f"[Email send_password_reset_email Error] {err}")
            return False

