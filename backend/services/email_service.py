import os
import smtplib
import json
import datetime
import email.utils
from email.header import Header
import threading
from zoneinfo import ZoneInfo
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from backend.config import Config
from backend.database import get_db

IST = ZoneInfo("Asia/Kolkata")

def _safe_log(msg: str):
    """Safely log messages to stdout without UnicodeEncodeError on Windows cmd/powershell."""
    try:
        clean = msg.replace("₹", "INR ").replace("—", "-").replace("•", "*")
        print(clean, flush=True)
    except Exception:
        try:
            print(msg.encode("ascii", errors="replace").decode("ascii"), flush=True)
        except Exception:
            pass

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

    @classmethod
    def get_base_url(cls):
        """
        Returns the absolute base URL for email links so they can be clicked
        both on mobile devices (via Wi-Fi IP) and on the desktop machine.
        """
        site_url = os.getenv("SITE_URL", "").strip().rstrip("/")
        if site_url:
            return site_url

        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            lan_ip = s.getsockname()[0]
            s.close()
            if lan_ip and lan_ip != "127.0.0.1":
                port = os.getenv("PORT", "5000")
                return f"http://{lan_ip}:{port}"
        except Exception:
            pass

        return "http://192.168.43.34:5000"

    @staticmethod
    def get_ist_now():
        return datetime.datetime.now(IST).strftime("%d %B %Y, %I:%M %p IST")

    @classmethod
    def _render_luxury_template(cls, title, headline, message_body, order_details=None, cta_text=None, cta_link=None, is_admin=False):
        base_url = cls.get_base_url()
        if cta_link and not cta_link.startswith("http"):
            cta_link = f"{base_url.rstrip('/')}/{cta_link.lstrip('/')}"

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

        admin_footer_btn = f"""
        <div style="margin-top: 15px; padding-top: 12px; border-top: 1px dashed #23201b;">
          <a href="{base_url}/admin/orders.html" style="color: #d9ae55; text-decoration: none; font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; font-weight: 600; padding: 6px 14px; border: 1px solid rgba(217, 174, 85, 0.4); border-radius: 3px; display: inline-block;">
            🔐 Atelier Executive Console
          </a>
        </div>
        """ if is_admin else ""

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
      {admin_footer_btn}
      <p style="margin: 12px 0 0 0; font-size: 10px; color: #4a4742;">&copy; 2026 AURELIS Timepieces. Indian Rupees (₹) Only &bull; 6-Month Warranty.</p>
    </div>
  </div>
</body>
</html>"""

    @classmethod
    def send_email(cls, to_email, subject, title, headline, message_body, order_details=None, cta_text=None, cta_link=None, is_admin=False, async_send=False):
        """
        Dispatches an email via SMTP with full logging and graceful failure handling.
        Returns True on success, False on failure. Never raises an uncaught exception.
        """
        if async_send:
            t = threading.Thread(
                target=cls._send_email_sync,
                args=(to_email, subject, title, headline, message_body, order_details, cta_text, cta_link, is_admin),
                daemon=True
            )
            t.start()
            return True
        return cls._send_email_sync(to_email, subject, title, headline, message_body, order_details, cta_text, cta_link, is_admin)

    @classmethod
    def _send_email_sync(cls, to_email, subject, title, headline, message_body, order_details=None, cta_text=None, cta_link=None, is_admin=False):
        try:
            html_content = cls._render_luxury_template(title, headline, message_body, order_details, cta_text, cta_link, is_admin)
            raw_recipient = to_email or cls.get_admin_email()
            
            # Clean envelope addresses
            clean_recipient = raw_recipient.split("<")[-1].split(">")[0].strip() if ("<" in raw_recipient and ">" in raw_recipient) else raw_recipient.strip()
            raw_sender = Config.EMAIL_FROM or Config.EMAIL_USERNAME or "concierge@aurelistime.com"
            clean_sender = raw_sender.split("<")[-1].split(">")[0].strip() if ("<" in raw_sender and ">" in raw_sender) else raw_sender.strip()

            _safe_log(f"[EMAIL ATTEMPT] Destination: {clean_recipient} | Subject: {subject} | Title: {title}")

            if not Config.EMAIL_USERNAME or not Config.EMAIL_PASSWORD:
                _safe_log(f"[EMAIL NOT CONFIGURED] EMAIL_USERNAME or EMAIL_PASSWORD is unset in environment. Email logged to console.")
                return True

            msg = MIMEMultipart("alternative")
            msg["Subject"] = Header(str(subject), "utf-8")
            from_display = str(Header("AURELIS Concierge", "utf-8"))
            msg["From"] = f"{from_display} <{clean_sender}>"
            msg["To"] = clean_recipient
            msg["Reply-To"] = clean_sender
            msg["Date"] = email.utils.formatdate(localtime=True)
            domain_part = clean_sender.split("@")[-1] if "@" in clean_sender else "gmail.com"
            msg["Message-ID"] = email.utils.make_msgid(domain=domain_part)
            msg["X-Mailer"] = "AURELIS Haute Horlogerie Engine"

            # Plain-text fallback for optimal email client parsing & anti-spam delivery
            plain_lines = [f"AURELIS HAUTE HORLOGERIE", f"{title} - {headline}", ""]
            if order_details:
                for k, v in order_details.items():
                    plain_lines.append(f"{k}: {v}")
            plain_lines.append("")
            plain_lines.append("AURELIS Luxury Timepieces • Official Atelier Concierge")
            plain_content = "\n".join(plain_lines)

            msg.attach(MIMEText(plain_content, "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            # Send email via SMTP
            clean_pwd = Config.EMAIL_PASSWORD.replace(" ", "") if Config.EMAIL_PASSWORD else ""
            try:
                with smtplib.SMTP(Config.EMAIL_HOST, Config.EMAIL_PORT, timeout=12) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(Config.EMAIL_USERNAME, clean_pwd)
                    server.sendmail(clean_sender, [clean_recipient], msg.as_string())
                _safe_log(f"[EMAIL SENT SUCCESSFULLY] Destination: {clean_recipient} | Subject: {subject}")
                return True
            except Exception as smtp_err:
                _safe_log(f"[EMAIL SENDING EXCEPTION to {clean_recipient}] Error {type(smtp_err).__name__}: {smtp_err}")
                return False

        except Exception as e:
            _safe_log(f"[EMAIL SERVICE ERROR to {to_email}] {type(e).__name__}: {e}")
            return False

    # =========================================================================
    # ADMIN ORDER NOTIFICATION (SENT DIRECTLY TO CONFIGURED ADMIN EMAIL)
    # =========================================================================
    @classmethod
    def notify_admin_new_order(cls, order, items):
        """
        Notifies Admin with complete order and customer details per requirement:
        - Customer full name, email, mobile number, delivery address
        - Order ID, date/time, product name, SKU, quantity, price, subtotal, GST, total
        - Payment method/status, order status
        """
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
                full_addr_str = addr.get("address_line", "Address on verified record")

            items_desc = "<br>".join([
                f"• <strong>{i.get('product_name')}</strong> (SKU: {i.get('sku', 'N/A')}, {i.get('color_name', 'Standard')}) &times; {i.get('quantity')} @ ₹{float(i.get('price') or i.get('unit_price') or 0):,.2f} = <strong>₹{float(i.get('total_price', 0)):,.2f}</strong>"
                for i in items
            ])

            subtotal_val = float(order.get("subtotal") or order.get("total_amount") or 0)
            gst_val = round((subtotal_val * 0.18), 2)
            total_val = float(order.get("total_amount", 0))

            details = {
                "ORDER ID": f"#{order.get('order_number')}",
                "ORDER DATE & TIME (IST)": cls.get_ist_now(),
                "CUSTOMER FULL NAME": order.get("customer_name"),
                "CUSTOMER EMAIL": order.get("customer_email"),
                "CUSTOMER MOBILE NUMBER": f"+91 {order.get('customer_phone')}",
                "COMPLETE DELIVERY ADDRESS": full_addr_str,
                "PIN CODE": pincode or "Verified",
                "ORDER NOTE": order.get("order_note") or "None specified",
                "COMMISSION SUBTOTAL": f"₹{subtotal_val:,.2f}",
                "APPLICABLE GST": f"₹{gst_val:,.2f} (18% Included in MRP)",
                "SHIPPING / TRANSIT": "₹0.00 (Complimentary Insured Courier)",
                "TOTAL COMMISSION AMOUNT": f"₹{total_val:,.2f}",
                "PAYMENT METHOD": order.get("payment_method"),
                "PAYMENT STATUS": order.get("payment_status"),
                "ORDER STATUS": order.get("order_status"),
                "WARRANTY STATUS": "6-Month Manufacturer Warranty Active"
            }

            base_url = cls.get_base_url()

            admin_links_box = f"""
            <div style="background: #12100d; border: 1.5px solid #d9ae55; border-radius: 6px; padding: 20px 16px; margin: 22px 0; text-align: center;">
                <p style="color: #d9ae55; font-size: 11px; letter-spacing: 0.15em; text-transform: uppercase; font-weight: 700; margin: 0 0 12px 0;">
                    ⚡ Direct Mobile &amp; Desktop Executive Access
                </p>
                <div style="margin-bottom: 12px;">
                    <a href="{base_url}/admin/orders.html" style="background: #d9ae55; color: #060605; font-size: 11.5px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; padding: 12px 20px; border-radius: 3px; display: inline-block; text-decoration: none; margin: 4px;">
                        Manage Orders (Mobile Wi-Fi)
                    </a>
                    <a href="http://127.0.0.1:5000/admin/orders.html" style="background: #1f1b14; color: #d9ae55; border: 1px solid #d9ae55; font-size: 11.5px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; padding: 12px 18px; border-radius: 3px; display: inline-block; text-decoration: none; margin: 4px;">
                        Manage on Desktop (Local)
                    </a>
                </div>
                <p style="font-size: 10px; color: #8c877e; margin: 8px 0 0 0; line-height: 1.6;">
                    📱 Mobile Link: <a href="{base_url}/admin/orders.html" style="color: #d9ae55; text-decoration: underline;">{base_url}/admin/orders.html</a><br>
                    💻 Desktop Link: <a href="http://127.0.0.1:5000/admin/orders.html" style="color: #d9ae55; text-decoration: underline;">http://127.0.0.1:5000/admin/orders.html</a>
                </p>
            </div>
            """

            body = f"""
            A new timepiece commission has been confirmed and registered in the atelier database.<br><br>
            <strong>Commissioned Timepieces:</strong><br>
            {items_desc}
            <br>
            {admin_links_box}
            <br>
            <em>Please inspect the complete customer details below and proceed with packaging and serialized transit dispatch.</em>
            """

            subject_line = f"NEW AURELIS ORDER - ORDER #{order.get('order_number')}"

            return cls.send_email(
                to_email=admin_email,
                subject=subject_line,
                title="Atelier Order Notification",
                headline=f"New Order #{order.get('order_number')} Confirmed",
                message_body=body,
                order_details=details,
                cta_text="Manage in Admin Console",
                cta_link=f"{base_url}/admin/orders.html",
                is_admin=True
            )
        except Exception as err:
            _safe_log(f"[Email notify_admin_new_order Error] {err}")
            return False

    # =========================================================================
    # CUSTOMER ORDER CONFIRMATION EMAIL
    # =========================================================================
    @classmethod
    def notify_customer_order_confirmation(cls, order, items):
        """
        Sends complete order confirmation email to the customer with:
        - Customer name, Order ID, Date/Time
        - Ordered watch(es), product name, qty, price, subtotal, GST info, total
        - Delivery address, expected delivery info, payment status
        """
        try:
            base_url = cls.get_base_url()
            order_number = order.get("order_number")
            track_url = f"{base_url}/track-order.html?order_id={order_number}"

            addr = order.get("shipping_address", {})
            if isinstance(addr, str):
                try:
                    addr = json.loads(addr)
                except Exception:
                    addr = {"address_line": addr}

            flat = addr.get("flat_no") or addr.get("flat") or addr.get("house", "")
            street = addr.get("street", "")
            area = addr.get("area", "")
            city = addr.get("city", "")
            state = addr.get("state", "")
            pincode = addr.get("pincode", "")

            full_addr_str = f"{flat}, {street}, {area}".strip(", ")
            if city or state:
                full_addr_str += f", {city}, {state} - {pincode}".strip(", ")
            if not full_addr_str or full_addr_str.replace("-", "").strip() == "":
                full_addr_str = addr.get("address_line", "Address on file")

            items_summary = "<br>".join([
                f"• <strong>{i.get('product_name')}</strong> ({i.get('color_name', 'Standard')}) &times; {i.get('quantity')} @ ₹{float(i.get('price') or i.get('unit_price') or 0):,.2f} — <strong>₹{float(i.get('total_price', 0)):,.2f}</strong>"
                for i in items
            ])

            subtotal_val = float(order.get("subtotal") or order.get("total_amount") or 0)
            gst_val = round((subtotal_val * 0.18), 2)
            total_val = float(order.get("total_amount", 0))

            body = f"""
            Dear {order.get('customer_name') or 'Valued Collector'},<br><br>
            Thank you for commissioning an authentic AURELIS timepiece. Your order has been successfully recorded in our atelier ledger and assigned to our master watchmakers for serialized preparation and insured door delivery.<br><br>
            <strong>Timepiece Summary:</strong><br>
            {items_summary}
            <br><br>
            Your order includes complimentary insured transit across India and our official <strong>6-Month Atelier Manufacturer Movement Warranty</strong>.
            """

            details = {
                "CUSTOMER NAME": order.get("customer_name"),
                "ORDER ID": f"#{order_number}",
                "ORDER DATE & TIME (IST)": cls.get_ist_now(),
                "DELIVERY ADDRESS": full_addr_str,
                "CONTACT PHONE": f"+91 {order.get('customer_phone')}",
                "EXPECTED DELIVERY": order.get("estimated_delivery") or "3 - 5 Business Days (Insured)",
                "COMMISSION SUBTOTAL": f"₹{subtotal_val:,.2f}",
                "GST INFORMATION": f"₹{gst_val:,.2f} (18% Included in MRP)",
                "INSURED COURIER": "₹0.00 (Complimentary Across India)",
                "TOTAL COMMISSION": f"₹{total_val:,.2f}",
                "PAYMENT METHOD": order.get("payment_method"),
                "PAYMENT STATUS": order.get("payment_status"),
                "WARRANTY": "6-Month Official Atelier Movement Warranty"
            }

            return cls.send_email(
                to_email=order.get("customer_email"),
                subject=f"AURELIS WATCH - ORDER #{order_number} CONFIRMATION",
                title="AURELIS WATCH",
                headline="ORDER CONFIRMATION",
                message_body=body,
                order_details=details,
                cta_text="Track Order Status",
                cta_link=track_url
            )
        except Exception as err:
            _safe_log(f"[Email notify_customer_order_confirmation Error] {err}")
            return False

    # =========================================================================
    # PASSWORD RESET 6-DIGIT OTP VERIFICATION EMAIL
    # =========================================================================
    @classmethod
    def send_otp_email(cls, to_email, customer_name, otp_code):
        """
        Dispatches the 6-digit OTP verification code for password reset:
        AURELIS WATCH • PASSWORD RESET VERIFICATION
        """
        try:
            base_url = cls.get_base_url()
            details = {
                "ACCOUNT EMAIL": to_email,
                "SECURITY CODE": f"{otp_code}",
                "VALIDITY": "15 Minutes (One-Time Code)",
                "TIMESTAMP (IST)": cls.get_ist_now(),
                "SECURITY NOTICE": "Do not disclose this verification code to anyone."
            }
            body = f"""
            Dear {customer_name or 'Collector'},<br><br>
            A request was received to reset the password for your AURELIS collector account.<br><br>
            Please use the 6-digit verification code below to authorize your password update:
            <br><br>
            <div style="background: #0f0e0c; border: 1.5px solid #d9ae55; padding: 24px; margin: 20px 0; border-radius: 4px; text-align: center;">
                <p style="color: #d9ae55; font-size: 11px; letter-spacing: 0.25em; text-transform: uppercase; margin: 0 0 10px 0;">YOUR VERIFICATION CODE</p>
                <div style="font-family: 'Courier New', monospace; font-size: 34px; letter-spacing: 0.35em; color: #f5f0e7; font-weight: 700;">
                    {otp_code}
                </div>
            </div>
            <p style="font-size: 12.5px; color: #8c877e; line-height: 1.6;">
                This code is valid for strictly <strong>15 minutes</strong> and will expire immediately after use. If you did not initiate this request, your account remains fully secure and no further action is required.
            </p>
            """

            return cls.send_email(
                to_email=to_email,
                subject="AURELIS WATCH — PASSWORD RESET VERIFICATION",
                title="AURELIS WATCH",
                headline="PASSWORD RESET VERIFICATION",
                message_body=body,
                order_details=details,
                cta_text="Verify & Reset Password",
                cta_link=f"{base_url}/forgot-password.html"
            )
        except Exception as err:
            _safe_log(f"[Email send_otp_email Error] {err}")
            return False

    @classmethod
    def notify_admin_payment_event(cls, order, status, txn_id=None):
        try:
            admin_email = cls.get_admin_email()
            details = {
                "ORDER ID": f"#{order.get('order_number')}",
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
            _safe_log(f"[Email notify_admin_payment_event Error] {err}")
            return False

    @classmethod
    def notify_admin_cancellation(cls, order, reason):
        try:
            admin_email = cls.get_admin_email()
            details = {
                "ORDER ID": f"#{order.get('order_number')}",
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
            _safe_log(f"[Email notify_admin_cancellation Error] {err}")
            return False

    @classmethod
    def notify_admin_return_request(cls, order, reason, description):
        try:
            admin_email = cls.get_admin_email()
            details = {
                "ORDER ID": f"#{order.get('order_number')}",
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
            _safe_log(f"[Email notify_admin_return_request Error] {err}")
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
                subject=f"[SUPPORT INQUIRY] {subject} - From {name}",
                title="Concierge Client Inquiry",
                headline=f"Inquiry from {name}",
                message_body=f"<strong>Message:</strong><br><blockquote style='border-left: 2px solid #d9ae55; padding-left: 12px; margin: 10px 0; color: #dfdad1;'>{message}</blockquote>",
                order_details=details,
                cta_text="Reply in Admin Console",
                cta_link="/admin/messages.html",
                is_admin=True
            )
        except Exception as err:
            _safe_log(f"[Email notify_admin_customer_message Error] {err}")
            return False

    @classmethod
    def notify_customer_status_change(cls, order, new_status, notes=""):
        """
        Notifies customer of status updates (e.g. PROCESSING, PACKED, SHIPPED, OUT_FOR_DELIVERY, DELIVERED, CANCELLED, RETURN_REQUESTED).
        """
        try:
            base_url = cls.get_base_url()
            order_number = order.get("order_number")
            track_url = f"{base_url}/track-order.html?order_id={order_number}"
            status_clean = str(new_status).replace("_", " ")

            details = {
                "ORDER ID": f"#{order_number}",
                "NEW STATUS": status_clean,
                "UPDATE TIME (IST)": cls.get_ist_now(),
                "NOTES": notes or "Status updated in atelier records."
            }

            body = f"""
            Dear {order.get('customer_name') or 'Valued Collector'},<br><br>
            The status of your AURELIS timepiece commission <strong>#{order_number}</strong> has been updated to: <strong>{status_clean}</strong>.<br><br>
            <em>Atelier Notes:</em> {notes or 'Your order is progressing with serialized precision.'}<br><br>
            You can track real-time courier and delivery status anytime using the button below.
            """

            return cls.send_email(
                to_email=order.get("customer_email"),
                subject=f"AURELIS WATCH - ORDER #{order_number} STATUS: {status_clean}",
                title="AURELIS WATCH",
                headline=f"ORDER STATUS: {status_clean}",
                message_body=body,
                order_details=details,
                cta_text="Track Order Status",
                cta_link=track_url
            )
        except Exception as err:
            _safe_log(f"[Email notify_customer_status_change Error] {err}")
            return False

    @classmethod
    def notify_customer_support_reply(cls, customer_name, customer_email, inquiry_subject, reply_text):
        """
        Dispatches concierge response to customer inquiry from the admin console.
        """
        try:
            base_url = cls.get_base_url()
            details = {
                "RECIPIENT": f"{customer_name} ({customer_email})",
                "ORIGINAL INQUIRY": inquiry_subject,
                "RESPONSE TIME (IST)": cls.get_ist_now(),
                "CONCIERGE DESK": f"+91 {Config.ADMIN_PHONE}"
            }

            body = f"""
            Dear {customer_name or 'Valued Collector'},<br><br>
            Thank you for contacting the AURELIS Private Client Concierge.<br><br>
            In response to your inquiry regarding <em>"{inquiry_subject}"</em>, our master watchmaker concierge team has provided the following response:<br><br>
            <div style="background: #0d0c0a; border-left: 3px solid #d9ae55; padding: 18px 20px; margin: 20px 0; color: #f5f0e7; font-size: 13.5px; line-height: 1.8;">
                {reply_text}
            </div>
            If you have any further inquiries, please feel free to reply directly to this dispatch or reach out to our client concierge desk.
            """

            return cls.send_email(
                to_email=customer_email,
                subject=f"Re: {inquiry_subject} - AURELIS Client Concierge",
                title="AURELIS CONCIERGE",
                headline="ATELIER RESPONSE",
                message_body=body,
                order_details=details,
                cta_text="Visit AURELIS Atelier",
                cta_link=f"{base_url}/shop.html"
            )
        except Exception as err:
            _safe_log(f"[Email notify_customer_support_reply Error] {err}")
            return False

    @classmethod
    def send_otp_email(cls, to_email, name, otp_code):
        """
        Dispatches a 6-digit OTP security verification code email to customer.
        Returns True if sent, False on failure. Never raises an uncaught exception.
        """
        try:
            base_url = cls.get_base_url()
            clean_name = (name or "Valued Collector").strip()
            details = {
                "RECIPIENT": f"{clean_name} ({to_email})",
                "SECURITY CODE": f"{otp_code}",
                "CODE VALIDITY": "15 Minutes",
                "REQUEST TIME (IST)": cls.get_ist_now()
            }

            body = f"""
            Dear {clean_name},<br><br>
            A request was initiated to verify or recover access to your <strong>AURELIS Private Collector Registry</strong> account.<br><br>
            Please enter the authentic 6-digit security code below into the verification page to proceed:
            <div style="text-align: center; margin: 28px 0; padding: 22px; background: #0c0b09; border: 1.5px solid #d9ae55; border-radius: 6px; box-shadow: 0 0 20px rgba(217, 174, 85, 0.15);">
                <div style="font-size: 10px; letter-spacing: 0.24em; text-transform: uppercase; color: #d9ae55; margin-bottom: 8px;">6-DIGIT VERIFICATION CODE</div>
                <div style="font-family: 'Courier New', monospace; font-size: 36px; font-weight: 700; letter-spacing: 10px; color: #f5f0e7; text-shadow: 0 0 15px rgba(217, 174, 85, 0.35);">
                    {otp_code}
                </div>
                <div style="font-size: 11px; color: #8c877e; margin-top: 8px;">Valid for 15 minutes &bull; Single-use security token</div>
            </div>
            If you did not initiate this request, your account remains secure and no further action is required.<br><br>
            <em>Security Advisory:</em> AURELIS horology concierges will never ask for your verification code or password via phone or message.
            """

            _safe_log(f"[OTP DISPATCH] 6-digit code {otp_code} generated for {to_email}")

            return cls.send_email(
                to_email=to_email,
                subject=f"AURELIS — Your Security Verification Code: {otp_code}",
                title="ACCOUNT SECURITY",
                headline="6-DIGIT VERIFICATION CODE",
                message_body=body,
                order_details=details,
                cta_text="Complete Verification",
                cta_link="forgot-password.html"
            )
        except Exception as err:
            _safe_log(f"[Email send_otp_email Error to {to_email}] {err}")
            return False

