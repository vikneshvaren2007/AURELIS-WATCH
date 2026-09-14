import jwt
import datetime
import secrets
from zoneinfo import ZoneInfo
from functools import wraps
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from backend.config import Config
from backend.database import get_db, dict_from_row, dicts_from_rows
from backend.services.email_service import EmailService

IST = ZoneInfo("Asia/Kolkata")

auth_bp = Blueprint("auth", __name__)


def generate_token(user_id, role, email, name):
    payload = {
        "sub": str(user_id),
        "role": role,
        "email": email,
        "name": name,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7),
        "iat": datetime.datetime.now(datetime.timezone.utc)
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm="HS256")

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Authorization token is missing or malformed"}), 401
        
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
            request.current_user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired, please log in again"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid authentication token"}), 401
        
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Admin authorization token required"}), 401
        
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
            if payload.get("role") != "admin":
                return jsonify({"error": "Forbidden: Administrator privilege required"}), 403
            request.current_user = payload
        except Exception:
            return jsonify({"error": "Invalid or expired administrator token"}), 401
            
        return f(*args, **kwargs)
    return decorated

@auth_bp.route("/register", methods=["POST"])
def register():
    import re
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    phone = data.get("phone", "").strip()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password")

    if not name or not email or not password:
        return jsonify({"error": "Full name, email, and password are required"}), 400
    
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return jsonify({"error": "Please enter a valid email address"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long"}), 400

    if confirm_password is not None and password != confirm_password:
        return jsonify({"error": "Passwords do not match. Please re-enter your password."}), 400

    # Sanitize phone if provided
    clean_phone = ""
    if phone:
        digits = re.sub(r"[\s\-\+\(\)]", "", phone)
        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        clean_phone = digits

    password_hash = generate_password_hash(password)

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                return jsonify({"error": "An account with this email address already exists. Please sign in instead."}), 409

            now_ist = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO users (name, email, phone, password_hash, role, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'customer', ?, ?)
            """, (name, email, clean_phone, password_hash, now_ist, now_ist))
            user_id = cursor.lastrowid

            token = generate_token(user_id, "customer", email, name)
            return jsonify({
                "message": "Account created successfully",
                "token": token,
                "user": {
                    "id": user_id,
                    "name": name,
                    "email": email,
                    "phone": clean_phone,
                    "role": "customer"
                }
            }), 201
    except Exception as e:
        return jsonify({"error": f"Failed to register account: {str(e)}"}), 500

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, phone, password_hash, role, address FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid email or password"}), 401

        now_ist = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (now_ist, user["id"]))

        token = generate_token(user["id"], user["role"], user["email"], user["name"])
        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "phone": user["phone"],
                "address": user["address"] or "",
                "role": user["role"],
                "last_login": now_ist
            }
        }), 200

@auth_bp.route("/me", methods=["GET"])
@token_required
def get_current_user_profile():
    user_id = int(request.current_user["sub"])
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, phone, role, address, last_login, created_at FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"user": dict_from_row(user)})

@auth_bp.route("/profile", methods=["PUT"])
@token_required
def update_profile():
    user_id = int(request.current_user["sub"])
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    address = data.get("address", "").strip()

    if not name:
        return jsonify({"error": "Full name cannot be blank"}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        now_ist = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE users SET name = ?, phone = ?, address = ?, updated_at = ?
            WHERE id = ?
        """, (name, phone, address, now_ist, user_id))
        cursor.execute("SELECT id, name, email, phone, role, address, last_login, created_at FROM users WHERE id = ?", (user_id,))
        updated_user = cursor.fetchone()
        return jsonify({"message": "Profile updated successfully", "user": dict_from_row(updated_user)})

@auth_bp.route("/addresses", methods=["GET", "POST"])
@token_required
def manage_addresses():
    user_id = int(request.current_user["sub"])
    with get_db() as conn:
        cursor = conn.cursor()
        if request.method == "GET":
            cursor.execute("SELECT * FROM addresses WHERE user_id = ? ORDER BY is_default DESC, id DESC", (user_id,))
            rows = cursor.fetchall()
            return jsonify({"addresses": dicts_from_rows(rows)})

        data = request.get_json() or {}
        name = data.get("name", "").strip()
        phone = data.get("phone", "").strip()
        address_line = data.get("address_line", "").strip()
        city = data.get("city", "").strip()
        state = data.get("state", "").strip()
        pincode = data.get("pincode", "").strip()
        country = data.get("country", "India").strip()
        is_default = 1 if data.get("is_default") else 0

        if not name or not phone or not address_line or not city or not pincode:
            return jsonify({"error": "All address fields are required"}), 400

        if is_default:
            cursor.execute("UPDATE addresses SET is_default = 0 WHERE user_id = ?", (user_id,))

        cursor.execute("""
            INSERT INTO addresses (user_id, name, phone, address_line, city, state, pincode, country, is_default)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, name, phone, address_line, city, state, pincode, country, is_default))
        
        return jsonify({"message": "Address saved successfully", "address_id": cursor.lastrowid}), 201

@auth_bp.route("/addresses/<int:address_id>", methods=["DELETE"])
@token_required
def delete_address(address_id):
    user_id = request.current_user["sub"]
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM addresses WHERE id = ? AND user_id = ?", (address_id, user_id))
        return jsonify({"message": "Address deleted successfully"})

@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "Registered email address is required"}), 400

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email FROM users WHERE LOWER(email) = ?", (email,))
            user = cursor.fetchone()

            if user:
                # Generate a secure 6-digit numeric OTP
                otp_code = f"{secrets.randbelow(900000) + 100000}"
                # Also generate secure token for URL fallback
                token = secrets.token_urlsafe(32)
                now_utc = datetime.datetime.now(datetime.timezone.utc)
                expires_at = (now_utc + datetime.timedelta(minutes=15)).isoformat()

                cursor.execute("""
                    UPDATE users
                    SET reset_otp = ?, reset_otp_expires = ?, reset_otp_attempts = 0,
                        reset_token = ?, reset_token_expires = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (otp_code, expires_at, token, expires_at, user["id"]))

                # Send 6-digit OTP email to customer
                email_sent = EmailService.send_otp_email(user["email"], user["name"], otp_code)

                return jsonify({
                    "success": True,
                    "message": "A 6-digit verification code has been dispatched to your email address.",
                    "email": user["email"],
                    "email_dispatched": bool(email_sent),
                    "reset_token": token
                }), 200

            # If user not found, provide clear actionable feedback
            return jsonify({
                "error": f"No collector account found matching '{email}'. Please check the spelling or create an account first.",
                "success": False
            }), 404
    except Exception as e:
        return jsonify({"error": f"Failed to process password recovery request: {str(e)}"}), 500

@auth_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    otp = str(data.get("otp", "")).strip()

    if not email or not otp:
        return jsonify({"error": "Email and 6-digit verification code are required"}), 400

    if not otp.isdigit() or len(otp) != 6:
        return jsonify({"error": "Please enter a valid 6-digit verification code"}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, reset_otp, reset_otp_expires, reset_otp_attempts, reset_token
            FROM users WHERE LOWER(email) = ?
        """, (email,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "No account associated with this email address"}), 404

        attempts = user["reset_otp_attempts"] or 0
        if attempts >= 5:
            return jsonify({
                "error": "Maximum verification attempts exceeded (5/5). For your security, please request a new verification code."
            }), 429

        # Increment attempts
        cursor.execute("UPDATE users SET reset_otp_attempts = reset_otp_attempts + 1 WHERE id = ?", (user["id"],))

        expires_str = user["reset_otp_expires"]
        if not expires_str:
            return jsonify({"error": "No active verification code found. Please request a new code."}), 400

        try:
            expires_dt = datetime.datetime.fromisoformat(expires_str)
            if expires_dt.tzinfo is None:
                expires_dt = expires_dt.replace(tzinfo=datetime.timezone.utc)
            if datetime.datetime.now(datetime.timezone.utc) > expires_dt:
                return jsonify({"error": "This verification code has expired (15-minute validity). Please request a new code."}), 400
        except Exception:
            pass

        if str(user["reset_otp"]).strip() != otp:
            remaining = 5 - (attempts + 1)
            return jsonify({
                "error": f"Invalid verification code. {remaining} attempt(s) remaining." if remaining > 0 else "Invalid code. Maximum attempts reached."
            }), 400

        return jsonify({
            "success": True,
            "message": "Verification code confirmed successfully.",
            "email": user["email"],
            "reset_token": user["reset_token"]
        }), 200

@auth_bp.route("/verify-reset-token", methods=["GET"])
def verify_reset_token():
    token = request.args.get("token", "").strip()
    if not token:
        return jsonify({"error": "Reset token is required", "valid": False}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, reset_token_expires FROM users WHERE reset_token = ?", (token,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "Invalid or already used password reset token", "valid": False}), 400

        expires_str = user["reset_token_expires"]
        if expires_str:
            try:
                expires_dt = datetime.datetime.fromisoformat(expires_str)
                if expires_dt.tzinfo is None:
                    expires_dt = expires_dt.replace(tzinfo=datetime.timezone.utc)
                if datetime.datetime.now(datetime.timezone.utc) > expires_dt:
                    return jsonify({"error": "This password reset token has expired. Please request a new recovery link.", "valid": False}), 400
            except Exception:
                pass

        return jsonify({
            "valid": True,
            "message": "Token is valid and verified",
            "email": user["email"],
            "name": user["name"]
        }), 200

@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json() or {}
    token = data.get("token", "").strip()
    email = data.get("email", "").strip().lower()
    otp = str(data.get("otp", "")).strip()
    new_password = data.get("new_password") or data.get("password") or ""
    confirm_password = data.get("confirm_password") or data.get("password") or ""

    if not token and (not email or not otp):
        return jsonify({"error": "Reset authorization (token or verified OTP) is required"}), 400
    if not new_password or not confirm_password:
        return jsonify({"error": "New password and confirmation are required"}), 400
    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters long"}), 400
    if new_password != confirm_password:
        return jsonify({"error": "Passwords do not match. Please verify and re-enter."}), 400

    with get_db() as conn:
        cursor = conn.cursor()
        user = None

        if token:
            cursor.execute("""
                SELECT id, name, email, reset_token_expires
                FROM users WHERE reset_token = ?
            """, (token,))
            user = cursor.fetchone()
            if not user:
                return jsonify({"error": "Invalid or expired password reset token"}), 400

            expires_str = user["reset_token_expires"]
            if expires_str:
                try:
                    expires_dt = datetime.datetime.fromisoformat(expires_str)
                    if expires_dt.tzinfo is None:
                        expires_dt = expires_dt.replace(tzinfo=datetime.timezone.utc)
                    if datetime.datetime.now(datetime.timezone.utc) > expires_dt:
                        return jsonify({"error": "Reset authorization has expired. Please initiate a new recovery request."}), 400
                except Exception:
                    pass

        elif email and otp:
            cursor.execute("""
                SELECT id, name, email, reset_otp, reset_otp_expires, reset_otp_attempts
                FROM users WHERE LOWER(email) = ?
            """, (email,))
            user = cursor.fetchone()
            if not user or str(user["reset_otp"]).strip() != otp:
                return jsonify({"error": "Invalid or expired verification credentials"}), 400

            expires_str = user["reset_otp_expires"]
            if expires_str:
                try:
                    expires_dt = datetime.datetime.fromisoformat(expires_str)
                    if expires_dt.tzinfo is None:
                        expires_dt = expires_dt.replace(tzinfo=datetime.timezone.utc)
                    if datetime.datetime.now(datetime.timezone.utc) > expires_dt:
                        return jsonify({"error": "Reset authorization has expired. Please initiate a new recovery request."}), 400
                except Exception:
                    pass

        if not user:
            return jsonify({"error": "User account could not be identified"}), 400

        new_hash = generate_password_hash(new_password)
        now_ist = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

        # Crucial: Preserves user ID, email, orders, addresses, and history
        cursor.execute("""
            UPDATE users
            SET password_hash = ?,
                reset_token = NULL, reset_token_expires = NULL,
                reset_otp = NULL, reset_otp_expires = NULL, reset_otp_attempts = 0,
                updated_at = ?
            WHERE id = ?
        """, (new_hash, now_ist, user["id"]))

        return jsonify({
            "message": "Your password has been reset successfully. You can now sign in with your new password.",
            "success": True
        }), 200

