import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Config:
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.getenv("SECRET_KEY", "aurelis_super_secret_jwt_key_2026_luxury_chronograph")
    raw_db_url = os.getenv("DATABASE_URL", "")
    if raw_db_url.startswith("sqlite:///"):
        rel_p = raw_db_url.replace("sqlite:///", "")
        DATABASE_URL = str((BASE_DIR / rel_p).resolve())
    elif raw_db_url:
        DATABASE_URL = raw_db_url
    else:
        DATABASE_URL = str((BASE_DIR / "backend" / "aurelis.db").resolve())
    
    # Admin details requested
    ADMIN_NAME = os.getenv("ADMIN_NAME", "Vikneshvaren")
    ADMIN_PHONE = os.getenv("ADMIN_PHONE", "9445437069")
    ADMIN_LOCATION = os.getenv("ADMIN_LOCATION", "Tenkasi, Main Road, opposite the bus stand")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "vikneshvaren2@gmail.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@Aurelis2026!")

    # Payment Gateway (Razorpay for UPI / Cards / NetBanking)
    PAYMENT_KEY_ID = os.getenv("PAYMENT_KEY_ID", "rzp_test_placeholder_key")
    PAYMENT_KEY_SECRET = os.getenv("PAYMENT_KEY_SECRET", "rzp_test_placeholder_secret")
    PAYMENT_WEBHOOK_SECRET = os.getenv("PAYMENT_WEBHOOK_SECRET", "rzp_webhook_secret")

    # Email configuration
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
    EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
    EMAIL_FROM = os.getenv("EMAIL_FROM", "concierge@aurelistime.com")

    # Store Settings defaults
    DEFAULT_RETURN_DAYS = 7
    DEFAULT_SHIPPING_FEE = 0 # Luxury complimentary shipping
    DEFAULT_TAX_PERCENT = 18.0 # 18% GST standard luxury watches
    COD_ENABLED = True
    TIMEZONE = "Asia/Kolkata"

