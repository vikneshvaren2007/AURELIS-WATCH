# AURELIS — Haute Horlogerie & Luxury Watch E-Commerce Platform

A production-grade, full-stack luxury watch e-commerce application featuring a **240-frame scroll-driven scrollytelling hero animation**, two masterwork watch color variants based on the supplied assets, real relational database persistence, full shopping cart with guest-to-account auto-merging, UPI & Google Pay (Razorpay) payment gateway with cryptographic server signature verification, Cash on Delivery (COD), order tracking with status timeline, self-service cancellations and 7-day returns, and a comprehensive dark luxury Administrator suite.

---

## 1. Architectural Summary & Files

### Files Created:
- **Backend Architecture (`backend/`):**
  - `backend/app.py`: Flask entrypoint, CORS, static file router, error handling.
  - `backend/config.py`: Environment configuration and security defaults.
  - `backend/database.py`: Thread-safe database connection manager with dict row factories.
  - `backend/models.py`: Complete relational database schema with performance indexes.
  - `backend/seed.py`: Seeding engine for Vikneshvaren admin user, Two Watch Color Variants, coupons, and sample reviews.
  - `backend/requirements.txt`: Backend dependency specification.
  - `backend/routes/auth_routes.py`: Customer registration, JWT authentication, profile, address book.
  - `backend/routes/product_routes.py`: Product catalog, filtering, sorting, variant querying, specifications.
  - `backend/routes/cart_routes.py`: Database-backed cart, guest cart merging, dynamic tax/shipping calculations.
  - `backend/routes/order_routes.py`: Order placement, custom Order ID generation (`AUR-2026-XXXXXX`), order history, cancellation, and return requests.
  - `backend/routes/payment_routes.py`: Razorpay UPI order creation, cryptographic HMAC-SHA256 signature verification, and COD handling.
  - `backend/routes/coupon_routes.py`: Promotional privilege code validation.
  - `backend/routes/review_routes.py`: Customer review submission and moderation.
  - `backend/routes/admin_routes.py`: Admin login, KPI dashboard stats, live stock adjustments, order transitions, returns, cancellations, and store settings.
  - `backend/services/payment_service.py`: Razorpay payment API & server HMAC verification.
  - `backend/services/inventory_service.py`: Atomic stock reservation, deduction, and release.
  - `backend/services/email_service.py`: Luxury transactional HTML email engine.

- **Frontend Pages & Styles:**
  - `index.html`: Upgraded homepage preserving the 240-frame hero scroll animation + two color variant showcase + craftsmanship + testimonials + concierge footer.
  - `shop.html`: Catalog with live debounced search, color filters, price sliders, and sorting.
  - `product.html`: PDP with interactive dual-variant switcher (Two-Tone vs Royal Gold), gallery zoom, specs table, reviews, Add to Cart, Buy Now.
  - `cart.html`: Cart management with quantity steppers, taxes, shipping, coupon application.
  - `checkout.html`: Multi-step checkout with saved addresses and live summary.
  - `payment.html`: Google Pay / UPI Razorpay modal + COD checkout.
  - `payment-success.html`: Cryptographically verified success screen with "Copy Order ID".
  - `payment-failed.html`: Graceful retry and concierge support screen.
  - `order-confirmation.html`: Itemized commission confirmation with Copy Order ID.
  - `track-order.html`: 6-stage visual delivery timeline.
  - `account.html`: Collector profile and address management.
  - `orders.html`: Customer order history.
  - `order-details.html`: Printable official commission invoice.
  - `cancellation-request.html`: Cancellation workflow with reasons.
  - `return-request.html`: 7-day return request portal.
  - `return-status.html`: Return and refund status tracker.
  - `wishlist.html`: Saved timepieces list.
  - `about.html`, `contact.html`, `faq.html`, `shipping-policy.html`, `return-refund-policy.html`, `privacy-policy.html`, `terms.html`, `404.html`, `500.html`.

- **Admin Suite (`admin/`):**
  - `admin/login.html`: Admin login portal.
  - `admin/index.html`: Dashboard with 10 KPI cards, sales timeline, and order status management.
  - `admin/products.html`: Catalog models and color variants manager.
  - `admin/orders.html`: Search and status transitions manager.
  - `admin/inventory.html`: Live stock, reserved units, and restock adjustments.
  - `admin/cancellations.html`: Cancellation requests review and refund status.
  - `admin/returns.html`: 7-day return inspection and approval console.
  - `admin/customers.html`: Customer lifetime value directory.
  - `admin/payments.html`: Gateway transaction audit log.
  - `admin/settings.html`: Tax, shipping, return window, COD toggle, and concierge profile.

- **CSS & JavaScript Assets (`css/`, `js/`, `assets/`):**
  - `css/main.css`, `css/hero.css`, `css/shop.css`, `css/product.css`, `css/cart-checkout.css`, `css/admin.css`.
  - `js/api.js`, `js/auth.js`, `js/hero-scroll.js`, `js/cart.js`, `js/shop.js`, `js/product.js`, `js/checkout.js`, `js/payment.js`, `js/track.js`, `js/admin.js`.
  - `assets/variant_steel_gold.jpg` (Two-Tone Gold & Steel with White Dragon Dial).
  - `assets/variant_royal_gold.jpg` (Radiant Royal Gold with Midnight Blue Dragon Dial).
  - `assets/variant_hero_shot.jpg` (Full Gold Dragon Chronograph on obsidian).

- **Deployment & Config:**
  - `.env.example`, `.env`, `.gitignore`, `Dockerfile`, `docker-compose.yml`.

---

## 2. Two Watch Colour Variants (From Supplied Assets)

1. **Dragon Imperial (Two-Tone Gold & Steel)**:
   - 316L surgical stainless steel case with 18K yellow gold ion-plated central links, bezel, and pushers.
   - Hand-sculptured 3D golden dragon on white guilloché chronograph dial with triple sub-registers.
   - SKU: `AUR-IMP-TT01` &bull; Price: ₹48,500 (MSRP: ₹62,000)

2. **Dragon Sovereign (Radiant Royal Gold)**:
   - Full 18K yellow gold plated case and solid architectural link bracelet.
   - 3D sculptured golden dragon curving across deep royal midnight blue sunburst dial with carbon honeycomb polygon bezel.
   - SKU: `AUR-IMP-YG02` &bull; Price: ₹54,000 (MSRP: ₹70,000)

---

## 3. How to Run Locally

### Prerequisites:
- Python 3.10+ (Python 3.13 is pre-installed)

### Step 1: Install Dependencies
```bash
python -m pip install -r backend/requirements.txt
```

### Step 2: Initialize & Seed the Database
```bash
python -m backend.seed
```
This automatically initializes the relational schema, creates the administrator account for **Vikneshvaren**, inserts the two watch variants, initial inventory, coupons (`AURELIS10`), and verified collector reviews.

### Step 3: Run the Backend & Website
```bash
python backend/app.py
```
Open your browser and navigate to:
- **Atelier Storefront:** `http://localhost:5000`
- **Catalog:** `http://localhost:5000/shop.html`
- **Admin Console:** `http://localhost:5000/admin/index.html` (or `http://localhost:5000/admin/login.html`)

---

## 4. Admin Account & Access

- **Administrator:** Vikneshvaren
- **Location:** Tenkasi, Main Road, opposite the bus stand
- **Phone:** +91 9445437069
- **Email:** Configured in `.env` as `ADMIN_EMAIL=vikneshvaren@gmail.com`
- **Password:** Configured in `.env` as `ADMIN_PASSWORD=Admin@Aurelis2026!`

---

## 5. Payment Gateway Configuration (Google Pay / UPI)

The application uses Razorpay for native UPI intent and Google Pay processing.

1. Create an account at [Razorpay](https://razorpay.com).
2. Generate API Keys in the Razorpay Dashboard under **Settings &rarr; API Keys**.
3. Update `.env`:
   ```env
   PAYMENT_KEY_ID=rzp_live_xxxxxxxxxxxxxx
   PAYMENT_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
   ```
4. The frontend connects to Razorpay's Checkout SDK. Upon authorization, the server cryptographically validates the `HMAC-SHA256` signature before marking any order as `PAID`.

---

## 6. Cash on Delivery (COD) Configuration

Cash on Delivery is enabled by default. To adjust COD availability:
1. Log into the Admin Console at `/admin/settings.html`.
2. Toggle **Cash on Delivery (COD) Enabled** between `Enabled` and `Disabled`.
3. Click **Save Store Configuration**.

---

## 7. Transactional Email Notifications (SMTP)

Configure standard SMTP credentials in `.env`:
```env
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=your-atelier-email@gmail.com
EMAIL_PASSWORD=your-google-app-password
EMAIL_FROM=concierge@aurelistime.com
```
When credentials are configured, luxury HTML notification emails are automatically dispatched on:
- Order Placement
- Payment Confirmation
- Order Status Transitions (`SHIPPED`, `DELIVERED`, etc.)
- Order Cancellations & Refunds
- 7-Day Return Requests

*(When SMTP credentials are not set, all emails are gracefully logged to the console without interrupting customer workflows.)*

---

## 8. Deployment Guide

### Deploying Frontend + Backend on Render (Recommended)
1. Push repository to GitHub.
2. Create a **Web Service** on [Render](https://render.com).
3. Set **Build Command**: `pip install -r backend/requirements.txt && python -m backend.seed`
4. Set **Start Command**: `gunicorn --bind 0.0.0.0:$PORT backend.app:app`
5. Add environment variables in the Render dashboard from `.env.example`.

### Deploying with Docker & PostgreSQL
```bash
docker-compose up --build -d
```
Runs the containerized Flask application alongside a managed PostgreSQL 16 database.
