/* ==========================================================================
   AURELIS — Shopping Cart State & Synchronization Engine
   ========================================================================== */

const Cart = {
  data: {
    items: [],
    subtotal: 0,
    tax: 0,
    shipping: 0,
    total: 0,
    count: 0
  },
  appliedCoupon: null,

  async init() {
    await this.fetchCart();
    this.bindEvents();
  },

  async fetchCart() {
    try {
      const res = await apiRequest("/api/cart");
      this.data = res;
      this.updateUI();
      return res;
    } catch (e) {
      console.warn("Error fetching cart:", e);
      return this.data;
    }
  },

  async addItem(productId, variantId, quantity = 1) {
    try {
      const res = await apiRequest("/api/cart", {
        method: "POST",
        body: JSON.stringify({ product_id: productId, variant_id: variantId, quantity: Math.max(1, quantity) })
      });
      await this.fetchCart();
      return res;
    } catch (e) {
      throw e;
    }
  },

  async updateQty(itemId, quantity) {
    if (quantity < 1) {
      if (confirm("Remove this timepiece from your commission cart?")) {
        await this.removeItem(itemId);
      }
      return;
    }
    try {
      await apiRequest(`/api/cart/${itemId}`, {
        method: "PUT",
        body: JSON.stringify({ quantity })
      });
      await this.fetchCart();
    } catch (e) {
      showToast(e.message, "error");
    }
  },

  async removeItem(itemId) {
    try {
      await apiRequest(`/api/cart/${itemId}`, { method: "DELETE" });
      showToast("Timepiece removed from commission", "success");
      await this.fetchCart();
    } catch (e) {
      showToast(e.message, "error");
    }
  },

  async applyCoupon(code) {
    if (!code) {
      showToast("Please enter a privilege code (e.g. AURELIS10)", "error");
      return;
    }
    try {
      const res = await apiRequest("/api/coupons/apply", {
        method: "POST",
        body: JSON.stringify({ code, subtotal: this.data.subtotal })
      });
      this.appliedCoupon = res;
      showToast(res.message || "Privilege code applied successfully", "success");
      this.updateUI();
    } catch (e) {
      showToast(e.message, "error");
    }
  },

  updateUI() {
    // Update badge in navbar
    const badges = document.querySelectorAll(".cart-badge-count");
    badges.forEach(b => {
      b.textContent = this.data.count || 0;
      if (b.classList.contains("nav-badge")) {
        b.style.display = this.data.count > 0 ? "grid" : "none";
      } else {
        b.style.display = "inline";
      }
    });

    // Update cart table if on cart.html
    const cartTableBody = document.getElementById("cartItemsBody");
    const cartEmptyState = document.getElementById("cartEmptyState");
    const cartContentArea = document.getElementById("cartContentArea");

    if (cartTableBody && cartEmptyState && cartContentArea) {
      if (!this.data.items || this.data.items.length === 0) {
        cartEmptyState.style.display = "block";
        cartContentArea.style.display = "none";
      } else {
        cartEmptyState.style.display = "none";
        cartContentArea.style.display = "grid";

        cartTableBody.innerHTML = this.data.items.map(item => {
          let itemImg = item.image_url || './assets/fallback-watch.svg';
          if (itemImg.startsWith('/')) itemImg = '.' + itemImg;
          return `
          <tr>
            <td>
              <div class="cart-item-flex">
                <img src="${itemImg}" alt="${item.product_name}" class="cart-item-img" onerror="this.src='./assets/fallback-watch.svg'">
                <div>
                  <h4 class="cart-item-name">${item.product_name}</h4>
                  <p class="cart-item-variant">${item.color_name || 'Signature Finish'}</p>
                  <span style="font-size: 10px; color: var(--gold-light); display: inline-flex; align-items: center; gap: 4px; margin: 3px 0;">
                    🛡️ 6-Month Warranty
                  </span>
                  <p class="cart-item-sku">SKU: ${item.sku}</p>
                  <button class="cart-item-remove" onclick="Cart.removeItem(${item.item_id})">Remove</button>
                </div>
              </div>
            </td>
            <td>${formatINR(item.price)}</td>
            <td>
              <div class="qty-stepper" style="width: 100px;">
                <button class="qty-btn" onclick="Cart.updateQty(${item.item_id}, ${item.quantity - 1})">-</button>
                <input type="text" class="qty-input" value="${item.quantity}" readonly>
                <button class="qty-btn" onclick="Cart.updateQty(${item.item_id}, ${item.quantity + 1})">+</button>
              </div>
            </td>
            <td style="font-family: var(--font-serif); font-weight: 600; color: var(--gold-light);">
              ${formatINR(item.price * item.quantity)}
            </td>
          </tr>
        `;
        }).join("");
      }
    }

    // Update price totals
    const discount = this.appliedCoupon ? this.appliedCoupon.discount_amount : 0;
    const finalTotal = Math.max(0, this.data.total - discount);

    const subtotalEl = document.getElementById("cartSubtotal");
    const totalEl = document.getElementById("cartTotal");
    const taxEl = document.getElementById("cartTax");
    const discountRow = document.getElementById("cartDiscountRow");
    const discountEl = document.getElementById("cartDiscount");

    if (subtotalEl) subtotalEl.textContent = formatINR(this.data.subtotal);
    if (totalEl) totalEl.textContent = formatINR(finalTotal);
    if (taxEl) taxEl.textContent = this.data.tax > 0 ? formatINR(this.data.tax) : "Included in MRP";

    if (discountRow && discountEl) {
      if (discount > 0) {
        discountRow.style.display = "flex";
        discountEl.textContent = `-${formatINR(discount)}`;
      } else {
        discountRow.style.display = "none";
      }
    }
  },

  bindEvents() {}
};

document.addEventListener("DOMContentLoaded", () => {
  Cart.init();
});
