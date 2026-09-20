import sqlite3
from backend.database import get_db

SCHEMA_SQL = """
-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'customer', -- 'customer' or 'admin'
    reset_token TEXT,
    reset_token_expires TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Admins Table (dedicated reference)
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL,
    location TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Addresses Table
CREATE TABLE IF NOT EXISTS addresses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    address_line TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    pincode TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'India',
    is_default INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Categories Table
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products Table
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    brand TEXT NOT NULL DEFAULT 'AURELIS',
    short_description TEXT,
    description TEXT,
    category_id INTEGER,
    featured INTEGER DEFAULT 1,
    base_price REAL NOT NULL,
    discount_price REAL,
    specifications TEXT, -- JSON string
    warranty TEXT DEFAULT '6-Month Warranty',
    return_days INTEGER DEFAULT 7,
    style TEXT,
    color TEXT,
    sku TEXT,
    stock_quantity INTEGER DEFAULT 10,
    main_image TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(category_id) REFERENCES categories(id)
);

-- Product Variants Table (Holds our Two Color Variants)
CREATE TABLE IF NOT EXISTS product_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    color_name TEXT NOT NULL,
    color_code TEXT NOT NULL,
    sku TEXT UNIQUE NOT NULL,
    price REAL NOT NULL,
    discount_price REAL,
    stock_quantity INTEGER NOT NULL DEFAULT 10,
    reserved_quantity INTEGER NOT NULL DEFAULT 0,
    low_stock_threshold INTEGER NOT NULL DEFAULT 3,
    image_url TEXT NOT NULL,
    strap_color TEXT DEFAULT '',
    accent_color TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Product Images Table
CREATE TABLE IF NOT EXISTS product_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    variant_id INTEGER,
    image_url TEXT NOT NULL,
    is_primary INTEGER DEFAULT 0,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY(variant_id) REFERENCES product_variants(id) ON DELETE CASCADE
);

-- Inventory Audit Logs
CREATE TABLE IF NOT EXISTS inventory_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    variant_id INTEGER NOT NULL,
    change_amount INTEGER NOT NULL,
    new_stock INTEGER NOT NULL,
    reason TEXT NOT NULL,
    reference_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(variant_id) REFERENCES product_variants(id)
);

-- Shopping Carts Table
CREATE TABLE IF NOT EXISTS carts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    session_token TEXT UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Cart Items Table
CREATE TABLE IF NOT EXISTS cart_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cart_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(cart_id) REFERENCES carts(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id),
    FOREIGN KEY(variant_id) REFERENCES product_variants(id),
    UNIQUE(cart_id, variant_id)
);

-- Orders Table
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_number TEXT UNIQUE NOT NULL, -- e.g. AUR-2026-000001
    user_id INTEGER,
    customer_name TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    customer_phone TEXT NOT NULL,
    shipping_address TEXT NOT NULL, -- JSON string
    subtotal REAL NOT NULL,
    shipping_fee REAL NOT NULL DEFAULT 0,
    tax_amount REAL NOT NULL DEFAULT 0,
    discount_amount REAL NOT NULL DEFAULT 0,
    total_amount REAL NOT NULL,
    coupon_code TEXT,
    order_status TEXT NOT NULL DEFAULT 'PENDING',
    payment_method TEXT NOT NULL, -- 'UPI' or 'COD'
    payment_status TEXT NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'PAID', 'FAILED', 'REFUNDED', 'COD_PENDING'
    estimated_delivery TEXT,
    order_note TEXT DEFAULT '',
    admin_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- Order Items Table
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    color_name TEXT NOT NULL,
    sku TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    total_price REAL NOT NULL,
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id),
    FOREIGN KEY(variant_id) REFERENCES product_variants(id)
);

-- Order Status History Table
CREATE TABLE IF NOT EXISTS order_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
);

-- Payments Table
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    gateway TEXT NOT NULL DEFAULT 'Razorpay',
    gateway_order_id TEXT,
    gateway_payment_id TEXT,
    gateway_signature TEXT,
    payment_method TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT NOT NULL DEFAULT 'INR',
    status TEXT NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'PAID', 'FAILED', 'REFUNDED', 'COD_PENDING'
    raw_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
);

-- Cancellations Table
CREATE TABLE IF NOT EXISTS cancellations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL UNIQUE,
    user_id INTEGER,
    reason TEXT NOT NULL,
    comments TEXT,
    status TEXT NOT NULL DEFAULT 'REQUESTED', -- 'REQUESTED', 'APPROVED', 'REJECTED'
    admin_notes TEXT,
    refund_status TEXT DEFAULT 'NOT_APPLICABLE', -- 'PENDING', 'PROCESSED', 'NOT_APPLICABLE'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
);

-- Returns Table
CREATE TABLE IF NOT EXISTS returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    user_id INTEGER,
    product_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    description TEXT,
    photo_urls TEXT, -- JSON array
    status TEXT NOT NULL DEFAULT 'REQUESTED', -- 'REQUESTED', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'PICKUP_SCHEDULED', 'PICKED_UP', 'RECEIVED', 'REFUND_PROCESSING', 'REFUNDED'
    admin_notes TEXT,
    refund_amount REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
);

-- Return Items Table
CREATE TABLE IF NOT EXISTS return_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    return_id INTEGER NOT NULL,
    order_item_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    condition TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(return_id) REFERENCES returns(id) ON DELETE CASCADE
);

-- Refunds Table
CREATE TABLE IF NOT EXISTS refunds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    payment_id INTEGER,
    amount REAL NOT NULL,
    refund_transaction_id TEXT,
    method TEXT NOT NULL, -- 'ORIGINAL_PAYMENT' or 'BANK_TRANSFER'
    status TEXT NOT NULL DEFAULT 'INITIATED', -- 'INITIATED', 'COMPLETED', 'FAILED'
    admin_notes TEXT,
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(order_id) REFERENCES orders(id)
);

-- Coupons Table
CREATE TABLE IF NOT EXISTS coupons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    discount_type TEXT NOT NULL, -- 'PERCENTAGE' or 'FIXED'
    discount_value REAL NOT NULL,
    min_order_amount REAL DEFAULT 0,
    max_discount REAL,
    usage_limit INTEGER DEFAULT 100,
    used_count INTEGER DEFAULT 0,
    per_user_limit INTEGER DEFAULT 1,
    expires_at TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Reviews Table
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    user_id INTEGER,
    user_name TEXT NOT NULL,
    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
    title TEXT NOT NULL,
    comment TEXT NOT NULL,
    is_verified_purchase INTEGER DEFAULT 1,
    is_approved INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Wishlists Table
CREATE TABLE IF NOT EXISTS wishlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    variant_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, product_id, variant_id),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id)
);

-- Site Settings Table
CREATE TABLE IF NOT EXISTS site_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit Logs Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Customer Messages Table (Concierge Inquiries & Replies)
CREATE TABLE IF NOT EXISTS customer_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    subject TEXT,
    message TEXT NOT NULL,
    order_number TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'RESOLVED'
    admin_reply TEXT,
    replied_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Webhook Events Table (Idempotency & Auditing)
CREATE TABLE IF NOT EXISTS webhook_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    payload TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- INDEXES for Maximum Performance
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_variants_product ON product_variants(product_id);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_number ON orders(order_number);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(order_status);
CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_cancellations_order ON cancellations(order_id);
CREATE INDEX IF NOT EXISTS idx_returns_order ON returns(order_id);
CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_cart_items_cart ON cart_items(cart_id);
CREATE INDEX IF NOT EXISTS idx_messages_status ON customer_messages(status);
CREATE INDEX IF NOT EXISTS idx_webhook_events_id ON webhook_events(event_id);
"""

def init_db():
    """Initializes the database tables, indexes, and applies incremental migrations."""
    with get_db() as conn:
        conn.executescript(SCHEMA_SQL)
        
        # Ensure any newly added columns exist in older tables
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(products)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        
        cols_to_add = [
            ("style", "TEXT"),
            ("color", "TEXT"),
            ("sku", "TEXT"),
            ("stock_quantity", "INTEGER DEFAULT 10"),
            ("main_image", "TEXT"),
            ("is_active", "INTEGER DEFAULT 1")
        ]
        for col_name, col_type in cols_to_add:
            if col_name not in existing_cols:
                try:
                    cursor.execute(f"ALTER TABLE products ADD COLUMN {col_name} {col_type}")
                except Exception as e:
                    print(f"Migration note: {e}")

        # Ensure order_note exists in orders table
        cursor.execute("PRAGMA table_info(orders)")
        order_cols = {row[1] for row in cursor.fetchall()}
        if "order_note" not in order_cols:
            try:
                cursor.execute("ALTER TABLE orders ADD COLUMN order_note TEXT DEFAULT ''")
            except Exception as e:
                print(f"Migration note (order_note): {e}")

        # Ensure last_login and address exist in users table
        cursor.execute("PRAGMA table_info(users)")
        user_cols = {row[1] for row in cursor.fetchall()}
        if "last_login" not in user_cols:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN last_login TEXT")
            except Exception as e:
                print(f"Migration note (last_login): {e}")
        if "address" not in user_cols:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN address TEXT")
            except Exception as e:
                print(f"Migration note (address): {e}")

        # Ensure reset_otp, reset_otp_expires, reset_otp_attempts exist in users table
        if "reset_otp" not in user_cols:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN reset_otp TEXT")
            except Exception as e:
                print(f"Migration note (reset_otp): {e}")
        if "reset_otp_expires" not in user_cols:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN reset_otp_expires TEXT")
            except Exception as e:
                print(f"Migration note (reset_otp_expires): {e}")
        if "reset_otp_attempts" not in user_cols:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN reset_otp_attempts INTEGER DEFAULT 0")
            except Exception as e:
                print(f"Migration note (reset_otp_attempts): {e}")

        # Ensure strap_color and accent_color exist in product_variants table
        cursor.execute("PRAGMA table_info(product_variants)")
        variant_cols = {row[1] for row in cursor.fetchall()}
        if "strap_color" not in variant_cols:
            try:
                cursor.execute("ALTER TABLE product_variants ADD COLUMN strap_color TEXT DEFAULT ''")
            except Exception as e:
                print(f"Migration note (strap_color): {e}")
        if "accent_color" not in variant_cols:
            try:
                cursor.execute("ALTER TABLE product_variants ADD COLUMN accent_color TEXT DEFAULT ''")
            except Exception as e:
                print(f"Migration note (accent_color): {e}")

        # Database Performance Indexes (Requirement 17)
        indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
            "CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_orders_customer_email ON orders(customer_email);",
            "CREATE INDEX IF NOT EXISTS idx_orders_order_number ON orders(order_number);",
            "CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);",
            "CREATE INDEX IF NOT EXISTS idx_product_variants_product_id ON product_variants(product_id);"
        ]
        for idx_query in indexes_sql:
            try:
                cursor.execute(idx_query)
            except Exception as e:
                print(f"Index creation note: {e}")
                    
    print("Database schema initialized successfully.")

if __name__ == "__main__":
    init_db()

