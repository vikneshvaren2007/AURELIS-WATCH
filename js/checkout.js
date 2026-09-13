/* ==========================================================================
   AURELIS — Checkout Orchestrator Engine
   ========================================================================== */

const Checkout = {
  cart: null,
  savedAddresses: [],
  selectedPaymentMethod: "UPI", // 'UPI' or 'COD'

  async init() {
    await this.loadCart();
    await this.checkAuthAndAddresses();
    this.bindEvents();
  },

  async loadCart() {
    this.cart = await Cart.fetchCart();
    if (!this.cart.items || this.cart.items.length === 0) {
      showToast("Your commission cart is empty. Redirecting to shop...", "error");
      setTimeout(() => window.location.href = "shop.html", 1500);
      return;
    }
    this.renderSummary();
  },

  async checkAuthAndAddresses() {
    // Only check saved addresses if explicitly logged in as a customer
    if (Auth.isLoggedIn()) {
      const user = Auth.getUser();
      if (user && user.role === "customer") {
        const nameInput = document.getElementById("checkoutName");
        const emailInput = document.getElementById("checkoutEmail");
        const phoneInput = document.getElementById("checkoutPhone");
        if (nameInput && !nameInput.value) nameInput.value = user.name || "";
        if (emailInput && !emailInput.value) emailInput.value = user.email || "";
        if (phoneInput && !phoneInput.value) phoneInput.value = user.phone || "";

        try {
          const res = await apiRequest("/api/auth/addresses");
          this.savedAddresses = res.addresses || [];
          this.renderSavedAddresses();
        } catch (e) {}
      }
    }
  },

  renderSavedAddresses() {
    const container = document.getElementById("savedAddressesContainer");
    if (!container || this.savedAddresses.length === 0) return;

    container.style.display = "block";
    const listEl = document.getElementById("savedAddressesList");
    listEl.innerHTML = this.savedAddresses.map((addr) => `
      <div class="luxury-card" style="padding: 16px; margin-bottom: 12px; cursor: pointer; border-color: var(--border-subtle);" onclick="Checkout.selectSavedAddress(${addr.id})">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <strong style="font-size: 13px;">${addr.name} (${addr.phone})</strong>
          ${addr.is_default ? '<span class="badge-gold">Default</span>' : ''}
        </div>
        <p style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">
          ${addr.address_line || ''}, ${addr.city || ''}, ${addr.state || ''} - ${addr.pincode || ''}
        </p>
        <span style="font-size: 11px; color: var(--gold-light); text-decoration: underline; margin-top: 4px; display: inline-block;">Click to use this address &rarr;</span>
      </div>
    `).join("");
  },

  selectSavedAddress(id) {
    const addr = this.savedAddresses.find(a => a.id === id);
    if (addr) this.populateAddressForm(addr);
  },

  populateAddressForm(addr) {
    const flatInput = document.getElementById("checkoutFlatNo");
    const streetInput = document.getElementById("checkoutStreet");
    const areaInput = document.getElementById("checkoutArea");
    const cityInput = document.getElementById("checkoutCity");
    const stateInput = document.getElementById("checkoutState");
    const pincodeInput = document.getElementById("checkoutPincode");

    if (flatInput) flatInput.value = addr.flat_no || addr.address_line || "";
    if (streetInput) streetInput.value = addr.street || "";
    if (areaInput) areaInput.value = addr.area || "";
    if (cityInput) cityInput.value = addr.city || "";
    if (stateInput && addr.state) stateInput.value = addr.state;
    if (pincodeInput) pincodeInput.value = addr.pincode || "";
    showToast("Address populated from saved profile", "success");
  },

  validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  },

  validatePhone(phone) {
    const cleaned = phone.replace(/[\s\-\+\(\)]/g, "");
    return /^[6-9]\d{9}$/.test(cleaned) || (/^91[6-9]\d{9}$/.test(cleaned) && cleaned.length === 12);
  },

  async placeOrder() {
    const nameEl = document.getElementById("checkoutName");
    const emailEl = document.getElementById("checkoutEmail");
    const phoneEl = document.getElementById("checkoutPhone");
    const flatEl = document.getElementById("checkoutFlatNo");
    const streetEl = document.getElementById("checkoutStreet");
    const areaEl = document.getElementById("checkoutArea");
    const cityEl = document.getElementById("checkoutCity");
    const districtEl = document.getElementById("checkoutDistrict");
    const stateEl = document.getElementById("checkoutState");
    const pincodeEl = document.getElementById("checkoutPincode");
    const noteEl = document.getElementById("checkoutNote");

    const name = nameEl?.value.trim() || "";
    const email = emailEl?.value.trim() || "";
    const rawPhone = phoneEl?.value.trim() || "";
    const flatNo = flatEl?.value.trim() || "";
    const street = streetEl?.value.trim() || "";
    const area = areaEl?.value.trim() || "";
    const city = cityEl?.value.trim() || "";
    const district = districtEl?.value.trim() || city;
    const state = stateEl?.value.trim() || "Tamil Nadu";
    const pincode = pincodeEl?.value.trim() || "";
    const orderNote = noteEl?.value.trim() || "";

    // Clear previous error styles
    [nameEl, emailEl, phoneEl, flatEl, streetEl, areaEl, cityEl, pincodeEl].forEach(el => {
      if (el) el.style.borderColor = "";
    });

    // 1. Mandatory Name Validation
    if (!name || name.length < 2) {
      if (nameEl) { nameEl.style.borderColor = "#e74c3c"; nameEl.focus(); }
      showToast("Please provide your full legal name for insured transit.", "error");
      return;
    }

    // 2. Mandatory Email Validation
    if (!email || !this.validateEmail(email)) {
      if (emailEl) { emailEl.style.borderColor = "#e74c3c"; emailEl.focus(); }
      showToast("Please provide a valid email address (e.g. name@gmail.com).", "error");
      return;
    }

    // 3. Mandatory 10-digit Phone Validation
    if (!rawPhone || !this.validatePhone(rawPhone)) {
      if (phoneEl) { phoneEl.style.borderColor = "#e74c3c"; phoneEl.focus(); }
      showToast("Please enter a valid 10-digit Indian mobile number (e.g. 9876543210).", "error");
      return;
    }
    const cleanPhone = rawPhone.replace(/[\s\-\+\(\)]/g, "").slice(-10);

    // 4. Mandatory Address Validation
    if (!flatNo) {
      if (flatEl) { flatEl.style.borderColor = "#e74c3c"; flatEl.focus(); }
      showToast("Please enter your flat, house, or door number.", "error");
      return;
    }
    if (!street) {
      if (streetEl) { streetEl.style.borderColor = "#e74c3c"; streetEl.focus(); }
      showToast("Please enter your street name or road.", "error");
      return;
    }
    if (!area) {
      if (areaEl) { areaEl.style.borderColor = "#e74c3c"; areaEl.focus(); }
      showToast("Please enter your locality, landmark or area name.", "error");
      return;
    }
    if (!city) {
      if (cityEl) { cityEl.style.borderColor = "#e74c3c"; cityEl.focus(); }
      showToast("Please enter your city or town.", "error");
      return;
    }

    // 5. Mandatory PIN Code Validation (6 digits)
    if (!pincode || !/^\d{6}$/.test(pincode)) {
      if (pincodeEl) { pincodeEl.style.borderColor = "#e74c3c"; pincodeEl.focus(); }
      showToast("Please enter a valid 6-digit Indian PIN code.", "error");
      return;
    }

    // 6. Cart verification
    if (!this.cart || !this.cart.items || this.cart.items.length === 0) {
      showToast("Your cart is empty. Please add a timepiece from the collection.", "error");
      setTimeout(() => window.location.href = "shop.html", 1200);
      return;
    }

    const fullAddressLine = `${flatNo}, ${street}, ${area}`;
    const shippingAddress = {
      name,
      phone: cleanPhone,
      flat_no: flatNo,
      street: street,
      area: area,
      address_line: fullAddressLine,
      city,
      district,
      state,
      pincode,
      country: "India"
    };

    const submitBtn = document.getElementById("placeOrderBtn");
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "COMMISSIONING TIMEPIECE...";
    }

    try {
      const orderPayload = {
        customer_name: name,
        customer_email: email,
        customer_phone: cleanPhone,
        shipping_address: shippingAddress,
        items: this.cart.items,
        payment_method: this.selectedPaymentMethod,
        coupon_code: Cart.appliedCoupon ? Cart.appliedCoupon.code : null,
        order_note: orderNote
      };

      const res = await apiRequest("/api/orders", {
        method: "POST",
        body: JSON.stringify(orderPayload)
      });

      if (!res || !res.order_number) {
        throw new Error("Something went wrong while placing your order. Please try again.");
      }

      // Reset client cart cache now that backend has cleared it in DB
      if (window.Cart) {
        Cart.cart = { items: [], subtotal: 0, tax: 0, shipping: 0, total: 0, count: 0 };
        Cart.updateBadges(0);
      }

      showToast("Order placed successfully! Redirecting to confirmation...", "success");
      setTimeout(() => {
        window.location.href = `order-success.html?order_id=${encodeURIComponent(res.order_number)}`;
      }, 500);

    } catch (e) {
      const friendlyMsg = (e.message && !e.message.includes("status 500") && !e.message.includes("Failed to fetch"))
        ? e.message
        : "Something went wrong while placing your order. Please try again.";
      showToast(friendlyMsg, "error");
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = this.selectedPaymentMethod === "COD" ? "Place Order (Cash on Delivery)" : "Place Order (UPI / Demo Payment)";
      }
    }
  },

  selectPaymentMethod(method) {
    this.selectedPaymentMethod = method;
    document.querySelectorAll(".payment-method-card").forEach(c => {
      const isCurrent = c.dataset.method === method;
      c.classList.toggle("active", isCurrent);
      const radio = c.querySelector("input[type='radio']");
      if (radio) radio.checked = isCurrent;
    });

    const submitBtn = document.getElementById("placeOrderBtn");
    if (submitBtn) {
      if (method === "COD") {
        submitBtn.textContent = "Place Order (Cash on Delivery)";
      } else {
        submitBtn.textContent = "Place Order (UPI / Demo Payment)";
      }
    }
  },


  bindEvents() {
    const placeBtn = document.getElementById("placeOrderBtn");
    if (placeBtn) placeBtn.addEventListener("click", () => this.placeOrder());

    document.querySelectorAll(".payment-method-card").forEach(card => {
      card.addEventListener("click", () => {
        this.selectPaymentMethod(card.dataset.method);
      });
    });
  }
};

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("checkoutItemsList")) {
    Checkout.init();
  }
});
