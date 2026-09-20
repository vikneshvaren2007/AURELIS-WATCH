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
    if (quantity < 1) return;
    const targetItem = (this.data.items || []).find(i => i.item_id === itemId);
    if (!targetItem) return;

    const prevQty = targetItem.quantity;
    if (prevQty === quantity) return;

    // Instant optimistic update for buttery-fast luxury responsiveness
    targetItem.quantity = quantity;
    targetItem.total_price = targetItem.price * quantity;

    let newSubtotal = 0;
    let newCount = 0;
    (this.data.items || []).forEach(it => {
      newSubtotal += it.price * it.quantity;
      newCount += it.quantity;
    });
    this.data.subtotal = newSubtotal;
    this.data.count = newCount;
    this.data.tax = Math.round((newSubtotal * 18.0) / 100.0);
    this.data.total = newSubtotal + this.data.tax + (this.data.shipping || 0);

    this.updateUI();

    try {
      await apiRequest(`/api/cart/${itemId}`, {
        method: "PUT",
        body: JSON.stringify({ quantity })
      });
      await this.fetchCart();
    } catch (e) {
      targetItem.quantity = prevQty;
      targetItem.total_price = targetItem.price * prevQty;
      showToast(e.message || "Failed to update quantity", "error");
      await this.fetchCart();
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
          const isMin = item.quantity <= 1;
          return `
          <tr>
            <td data-label="Timepiece">
              <div class="cart-item-flex">
                <img src="${itemImg}" alt="${item.product_name}" class="cart-item-img" onerror="this.src='./assets/fallback-watch.svg'">
                <div>
                  <h4 class="cart-item-name">${item.product_name}</h4>
                  <p class="cart-item-variant">${item.color_name || 'Signature Finish'}</p>
                  <span style="font-size: 10px; color: var(--gold-light); display: inline-flex; align-items: center; gap: 4px; margin: 3px 0;">
                    🛡️ 6-Month Warranty
                  </span>
                  <p class="cart-item-sku">SKU: ${item.sku}</p>
                  <button type="button" class="cart-item-remove-link" onclick="Cart.removeItem(${item.item_id})" title="Remove item">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: -1px; margin-right: 3px;"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    Remove Item
                  </button>
                </div>
              </div>
            </td>
            <td data-label="Price">${formatINR(item.price)}</td>
            <td data-label="Quantity" style="white-space: nowrap !important; width: 120px !important;">
              <div class="qty-stepper" style="display: inline-flex !important; flex-direction: row !important; align-items: center !important; justify-content: center !important; background: #14120f !important; border: 1px solid #d9ae55 !important; border-radius: 4px !important; padding: 2px !important; height: 32px !important; width: auto !important; min-width: 96px !important; max-width: 106px !important; white-space: nowrap !important; box-sizing: border-box !important;">
                <button type="button" class="qty-btn" onclick="Cart.updateQty(${item.item_id}, ${item.quantity - 1})" title="Decrease quantity" ${isMin ? 'disabled style="opacity:0.25;cursor:not-allowed;width:28px;height:26px;border:none;background:#14120f;color:#555;"' : 'style="width:28px !important;height:26px !important;display:inline-flex !important;align-items:center !important;justify-content:center !important;background:#1e1b15 !important;border:1px solid rgba(217,174,85,0.3) !important;border-radius:2px !important;color:#d9ae55 !important;font-size:14px !important;font-weight:700 !important;cursor:pointer !important;padding:0 !important;line-height:1 !important;user-select:none !important;flex-shrink:0 !important;"'}>&minus;</button>
                <span class="qty-val" style="min-width: 34px !important; max-width: 38px !important; height: 26px !important; line-height: 26px !important; text-align: center !important; font-family: 'DM Sans', sans-serif !important; font-size: 13px !important; font-weight: 600 !important; color: #f5f0e7 !important; background: transparent !important; display: inline-block !important; user-select: none !important; border: none !important; padding: 0 4px !important; margin: 0 !important;">${item.quantity}</span>
                <button type="button" class="qty-btn" onclick="Cart.updateQty(${item.item_id}, ${item.quantity + 1})" title="Increase quantity" style="width: 28px !important; height: 26px !important; display: inline-flex !important; align-items: center !important; justify-content: center !important; background: #1e1b15 !important; border: 1px solid rgba(217,174,85,0.3) !important; border-radius: 2px !important; color: #d9ae55 !important; font-size: 14px !important; font-weight: 700 !important; cursor: pointer !important; padding: 0 !important; line-height: 1 !important; user-select: none !important; flex-shrink: 0 !important;">&#43;</button>
              </div>
            </td>
            <td data-label="Total" style="font-family: var(--font-serif); font-weight: 600; color: var(--gold-light);">
              ${formatINR(item.price * item.quantity)}
            </td>
            <td data-label="Action" style="text-align: center;">
              <button type="button" class="cart-remove-item-btn" onclick="Cart.removeItem(${item.item_id})" title="Remove ${item.product_name} from cart">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 4px;">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                  <line x1="10" y1="11" x2="10" y2="17"></line>
                  <line x1="14" y1="11" x2="14" y2="17"></line>
                </svg>
                Remove Item
              </button>
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
