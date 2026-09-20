/* ==========================================================================
   AURELIS — Dedicated 100% Simulated Dummy Payment Engine
   Provides instant demo options: GPay Demo, UPI Demo, Card Demo, Cash on Delivery
   Simulates 2-second processing animation and confirms order in SQLite database.
   ========================================================================== */

const PaymentPortal = {
  order: null,
  currentTab: "gpay",

  async init() {
    const params = new URLSearchParams(window.location.search);
    const orderNumber = params.get("order_id");
    const preMethod = params.get("method");

    if (!orderNumber) {
      showToast("No order ID specified for authorization", "error");
      setTimeout(() => window.location.href = "shop.html", 1500);
      return;
    }

    await this.loadOrder(orderNumber);

    if (preMethod) {
      if (preMethod.toLowerCase().includes("cod")) this.switchTab("cod");
      else if (preMethod.toLowerCase().includes("card")) this.switchTab("card");
      else if (preMethod.toLowerCase().includes("upi")) this.switchTab("upi");
      else this.switchTab("gpay");
    }
  },

  async loadOrder(orderNumber) {
    try {
      const res = await apiRequest(`/api/orders/${orderNumber}`);
      this.order = res.order;
      if (!this.order) throw new Error("Order not found in atelier database");
      this.render();
    } catch (e) {
      showToast("Unable to load commission details: " + e.message, "error");
    }
  },

  render() {
    if (!this.order) return;

    const orderNumEl = document.getElementById("payOrderNumber");
    const amountEl = document.getElementById("payTotalAmount");
    const customerEl = document.getElementById("payCustomerInfo");
    const itemsEl = document.getElementById("payOrderItems");
    const cardHolder = document.getElementById("cardHolderDisplay");

    if (orderNumEl) orderNumEl.textContent = this.order.order_number;
    const formattedAmount = formatINR(this.order.total_amount);
    if (amountEl) amountEl.textContent = formattedAmount;
    if (customerEl) {
      customerEl.textContent = `${this.order.customer_name} • ${this.order.customer_email} • +91 ${this.order.customer_phone}`;
    }
    if (cardHolder && this.order.customer_name) {
      cardHolder.textContent = this.order.customer_name.toUpperCase();
    }

    // Update CTA button labels with order total
    const rzpBtn = document.getElementById("razorpayLiveBtn");
    const gpayBtn = document.getElementById("gpayActionBtn");
    const upiBtn = document.getElementById("upiActionBtn");
    const cardBtn = document.getElementById("cardActionBtn");
    const codBtn = document.getElementById("codActionBtn");

    if (rzpBtn) rzpBtn.innerHTML = `PAY ${formattedAmount} VIA RAZORPAY GATEWAY &rarr;`;
    if (gpayBtn) gpayBtn.textContent = `Pay ${formattedAmount} via GPay [Demo]`;
    if (upiBtn) upiBtn.textContent = `Pay ${formattedAmount} via UPI [Demo]`;
    if (cardBtn) cardBtn.textContent = `Pay ${formattedAmount} with Card [Demo]`;
    if (codBtn) codBtn.textContent = `Confirm Cash on Delivery Order (${formattedAmount})`;

    if (itemsEl && this.order.items) {
      itemsEl.innerHTML = this.order.items.map(item => `
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 12.5px;">
          <span>${item.product_name} (${item.color_name || 'Standard'}) &times; ${item.quantity}</span>
          <span style="font-weight: 500;">${formatINR(item.total_price || (item.price * item.quantity))}</span>
        </div>
      `).join("");
    }
  },

  switchTab(tabId) {
    this.currentTab = tabId;
    document.querySelectorAll(".pay-tab-btn").forEach(btn => {
      btn.classList.toggle("active", btn.id === `tabBtn-${tabId}`);
    });
    document.querySelectorAll(".pay-tab-panel").forEach(panel => {
      panel.classList.toggle("active", panel.id === `panel-${tabId}`);
    });
  },

  async processPayment(methodName) {
    if (!this.order) return;

    const overlay = document.getElementById("procOverlay");
    const eyebrow = document.getElementById("procEyebrow");
    const title = document.getElementById("procTitle");
    const desc = document.getElementById("procDesc");

    const isCod = methodName.toLowerCase().includes("cod") || methodName.toLowerCase().includes("cash");

    if (overlay) overlay.classList.add("active");

    if (isCod) {
      if (title) title.textContent = "Confirming Cash on Delivery Order...";
      if (desc) desc.textContent = "Assigning master watchmaker dispatch with tamper-evident seal.";
    } else {
      if (title) title.textContent = "Contacting Secure Banking Gateway...";
      if (desc) desc.textContent = "Verifying cryptographic authorization tokens with financial network.";
    }

    // Step 2 progression after 800ms
    setTimeout(() => {
      if (!isCod) {
        if (eyebrow) eyebrow.textContent = "VERIFYING CRYPTOGRAPHIC LEDGER";
        if (title) title.textContent = "Verifying Transaction Credentials...";
        if (desc) desc.textContent = "Card/UPI credentials authenticated. Reserving serialized timepiece in atelier registry.";
      }
    }, 800);

    // Step 3 progression after 1600ms
    setTimeout(() => {
      if (eyebrow) eyebrow.textContent = "COMMISSION SEALED";
      if (title) title.textContent = isCod ? "COD Commission Confirmed!" : "Payment Approved & Verified!";
      if (desc) desc.textContent = "Redirecting to acquisition confirmation and warranty passport...";
    }, 1600);

    const txnId = isCod ? "COD_PENDING" : `DEMO_TXN_${Date.now()}`;

    try {
      const res = await apiRequest("/api/payments/dummy-pay", {
        method: "POST",
        body: JSON.stringify({
          order_number: this.order.order_number,
          payment_method: methodName,
          txn_id: txnId
        })
      });

      if (!res.success) {
        throw new Error(res.error || "Payment authorization failed");
      }

      // Automatically redirect to success page after simulated processing
      setTimeout(() => {
        window.location.href = `order-success.html?order_id=${encodeURIComponent(this.order.order_number)}&txn=${encodeURIComponent(txnId)}`;
      }, 1600);

    } catch (e) {
      if (overlay) overlay.classList.remove("active");
      showToast("Payment authorization error: " + e.message, "error");
    }
  },

  async payWithRazorpay() {
    if (!this.order) {
      showToast("Order details not loaded", "error");
      return;
    }

    const rzpBtn = document.getElementById("razorpayLiveBtn");
    try {
      if (rzpBtn) {
        rzpBtn.disabled = true;
        rzpBtn.textContent = "INITIALIZING GATEWAY...";
      }

      const res = await apiRequest("/api/payments/create", {
        method: "POST",
        body: JSON.stringify({ order_number: this.order.order_number })
      });

      if (!res.success) {
        throw new Error(res.error || "Failed to initialize Razorpay checkout");
      }

      if (typeof Razorpay === "undefined") {
        throw new Error("Razorpay Checkout SDK is loading or unavailable. Please use alternative payment below.");
      }

      const options = {
        key: res.key_id,
        amount: res.amount,
        currency: res.currency,
        name: "AURELIS Haute Horlogerie",
        description: res.description || `Acquisition Commission for ${this.order.order_number}`,
        order_id: res.razorpay_order_id,
        prefill: {
          name: res.customer_name || this.order.customer_name,
          email: res.customer_email || this.order.customer_email,
          contact: res.customer_phone || this.order.customer_phone
        },
        theme: {
          color: "#d9ae55"
        },
        handler: async (response) => {
          const overlay = document.getElementById("procOverlay");
          const title = document.getElementById("procTitle");
          const desc = document.getElementById("procDesc");
          if (overlay) overlay.classList.add("active");
          if (title) title.textContent = "Verifying Payment Signature...";
          if (desc) desc.textContent = "Exchanging HMAC-SHA256 authorization proof with atelier ledger.";

          try {
            const verifyRes = await apiRequest("/api/payments/verify", {
              method: "POST",
              body: JSON.stringify({
                order_number: this.order.order_number,
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature
              })
            });

            if (verifyRes.success) {
              if (title) title.textContent = "Acquisition Authorized!";
              if (desc) desc.textContent = "Redirecting to your order confirmation and warranty certificate...";
              setTimeout(() => {
                window.location.href = `order-success.html?order_id=${encodeURIComponent(this.order.order_number)}&txn=${encodeURIComponent(response.razorpay_payment_id)}`;
              }, 1200);
            } else {
              throw new Error(verifyRes.error || "Signature verification rejected");
            }
          } catch (err) {
            if (overlay) overlay.classList.remove("active");
            showToast(err.message || "Payment verification failed", "error");
          }
        },
        modal: {
          ondismiss: () => {
            showToast("Payment window was dismissed.", "info");
          }
        }
      };

      const rzpInstance = new Razorpay(options);
      rzpInstance.on("payment.failed", (resp) => {
        showToast(`Payment failed: ${resp.error ? resp.error.description : 'Transaction cancelled'}`, "error");
      });
      rzpInstance.open();

    } catch (err) {
      showToast(err.message || "Could not launch Razorpay. You may use alternative methods below.", "error");
    } finally {
      if (rzpBtn) {
        rzpBtn.disabled = false;
        const formattedAmount = formatINR(this.order.total_amount);
        rzpBtn.innerHTML = `PAY ${formattedAmount} VIA RAZORPAY GATEWAY &rarr;`;
      }
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  PaymentPortal.init();
});
