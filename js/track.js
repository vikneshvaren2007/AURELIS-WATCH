/* ==========================================================================
   AURELIS — Order Tracking & Status Timeline Engine
   Strict 5-Stage Tracking: Order Placed -> Processing -> Shipped -> Out for Delivery -> Delivered
   ========================================================================== */

const TRACK_STAGES = [
  { key: "ORDER_PLACED", label: "Order Placed", match: ["PENDING", "CONFIRMED"] },
  { key: "PROCESSING", label: "Processing", match: ["PROCESSING", "PACKED"] },
  { key: "SHIPPED", label: "Shipped", match: ["SHIPPED"] },
  { key: "OUT_FOR_DELIVERY", label: "Out for Delivery", match: ["OUT_FOR_DELIVERY"] },
  { key: "DELIVERED", label: "Delivered", match: ["DELIVERED"] }
];

const Track = {
  currentOrder: null,

  async init() {
    const params = new URLSearchParams(window.location.search);
    const orderId = params.get("order_id");
    const contact = params.get("contact");

    if (orderId) {
      const orderInput = document.getElementById("trackOrderId");
      const contactInput = document.getElementById("trackContact");
      if (orderInput) orderInput.value = orderId;
      if (contactInput && contact) contactInput.value = contact;
      await this.track(orderId, contact || "");
    }

    const form = document.getElementById("trackOrderForm");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const oId = document.getElementById("trackOrderId").value.trim();
        const ct = document.getElementById("trackContact") ? document.getElementById("trackContact").value.trim() : "";
        await this.track(oId, ct);
      });
    }
  },

  async track(orderNumber, contact) {
    const resultBox = document.getElementById("trackingResultBox");
    if (!resultBox) return;

    try {
      const res = await apiRequest(`/api/orders/track?order_number=${encodeURIComponent(orderNumber)}&contact=${encodeURIComponent(contact)}`);
      this.currentOrder = res.order;
      this.renderOrder(res.order);
      resultBox.style.display = "block";
      resultBox.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      showToast(e.message || "Failed to load order details", "error");
      resultBox.style.display = "none";
    }
  },

  renderOrder(order) {
    const orderNumEl = document.getElementById("trackResultOrderNum");
    const dateTimeEl = document.getElementById("trackResultDateTime");
    const statusPill = document.getElementById("trackResultStatus");
    const deliveryEst = document.getElementById("trackResultEstDelivery");
    const addressEl = document.getElementById("trackResultAddress");
    const customerEl = document.getElementById("trackResultCustomer");
    const paymentEl = document.getElementById("trackResultPayment");
    const itemsEl = document.getElementById("trackResultItems");
    const actionsEl = document.getElementById("trackResultActions");
    const cancelledBanner = document.getElementById("trackCancelledBanner");

    if (orderNumEl) orderNumEl.textContent = order.order_number;
    if (dateTimeEl) {
      dateTimeEl.textContent = order.order_date ? `${order.order_date} at ${order.order_time || ''}` : `Placed on: ${order.created_at || '-'}`;
    }

    const isCancelled = order.order_status === "CANCELLED";

    if (statusPill) {
      statusPill.textContent = order.order_status.replace(/_/g, " ");
      statusPill.className = `status-pill status-${order.order_status}`;
    }

    if (cancelledBanner) {
      cancelledBanner.style.display = isCancelled ? "block" : "none";
    }

    if (deliveryEst) {
      deliveryEst.textContent = isCancelled ? "Cancelled" : (order.estimated_delivery || "3-5 Business Days");
    }

    // Render Address
    if (addressEl) {
      const addr = order.shipping_address || {};
      const street = [addr.address_line1, addr.address_line2, addr.landmark].filter(Boolean).join(", ");
      const loc = [addr.city, addr.state, addr.postal_code].filter(Boolean).join(" - ");
      const country = addr.country || "India";
      addressEl.innerHTML = `
        <strong>${addr.recipient_name || order.customer_name || 'Valued Client'}</strong><br>
        ${street ? `${street}<br>` : ''}
        ${loc ? `${loc}<br>` : ''}
        ${country} &bull; Tel: ${addr.phone || order.customer_phone || '-'}
      `;
    }

    // Render Customer & Payment
    if (customerEl) {
      customerEl.innerHTML = `
        <strong>Client:</strong> ${order.customer_name || 'N/A'}<br>
        <strong>Email:</strong> ${order.customer_email || 'N/A'}<br>
        <strong>Phone:</strong> ${order.customer_phone || 'N/A'}
      `;
    }

    if (paymentEl) {
      const paymentDisplay = (order.payment_method || 'CARD').toUpperCase();
      const paymentStatusDisplay = (order.payment_status || 'PAID').toUpperCase();
      paymentEl.innerHTML = `
        <strong>Payment Method:</strong> ${paymentDisplay}<br>
        <strong>Payment Status:</strong> <span style="color: ${paymentStatusDisplay === 'PAID' ? 'var(--gold-primary)' : '#eab308'}; font-weight: 600;">${paymentStatusDisplay}</span><br>
        <strong>Total Amount:</strong> <span style="font-family: var(--font-serif); font-weight: 600; color: var(--gold-light);">${formatINR(order.total_amount)}</span>
      `;
    }

    // Render Items
    if (itemsEl && order.items) {
      itemsEl.innerHTML = order.items.map(item => `
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 14px 0; border-bottom: 1px solid var(--border-subtle); gap: 15px;">
          <div style="display: flex; align-items: center; gap: 16px;">
            <img src="${item.image_url || './assets/fallback-watch.svg'}" alt="${item.product_name}" 
                 style="width: 55px; height: 55px; object-fit: contain; border-radius: 6px; background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle); padding: 4px;">
            <div>
              <h5 style="font-size: 14px; margin-bottom: 3px; font-family: var(--font-serif);">${item.product_name}</h5>
              <p style="font-size: 11px; color: var(--gold-light); margin: 0;">${item.color_name || 'Edition'} &bull; Qty: ${item.quantity}</p>
            </div>
          </div>
          <div style="text-align: right;">
            <div style="font-family: var(--font-serif); font-size: 15px; font-weight: 600; color: var(--gold-light);">${formatINR(item.total_price)}</div>
            <div style="font-size: 11px; color: var(--text-muted);">${formatINR(item.unit_price)} each</div>
          </div>
        </div>
      `).join("");
    }

    // Render Timeline Steps
    this.renderTimeline(order.order_status);

    // Actions
    if (actionsEl) {
      let buttonsHtml = `
        <a href="orders.html" class="gold-btn-outline" style="font-size: 11px; padding: 10px 18px;">
          View My Orders
        </a>
        <a href="shop.html" class="gold-btn-outline" style="font-size: 11px; padding: 10px 18px;">
          Continue Shopping
        </a>
      `;

      if (["PENDING", "CONFIRMED", "PROCESSING", "PACKED"].includes(order.order_status)) {
        buttonsHtml = `
          <button onclick="Track.handleCancel('${order.order_number}')" class="gold-btn-outline" style="font-size: 11px; padding: 10px 18px; border-color: rgba(239, 68, 68, 0.5); color: #ef4444;">
            Cancel Order
          </button>
        ` + buttonsHtml;
      }

      actionsEl.innerHTML = buttonsHtml;
    }
  },

  renderTimeline(currentStatus) {
    const timelineEl = document.getElementById("trackingTimeline");
    if (!timelineEl) return;

    if (currentStatus === "CANCELLED") {
      timelineEl.innerHTML = `
        <div style="width: 100%; text-align: center; padding: 25px 0;">
          <div style="width: 52px; height: 52px; border-radius: 50%; background: rgba(239, 68, 68, 0.15); border: 2px solid #ef4444; color: #ef4444; font-size: 24px; line-height: 48px; margin: 0 auto 12px; font-weight: bold;">✕</div>
          <p style="color: #ef4444; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 4px;">Order Status: Cancelled</p>
          <p style="color: var(--text-muted); font-size: 12px; margin: 0;">This commission was cancelled and is no longer moving through transit stages.</p>
        </div>
      `;
      return;
    }

    let activeStageIndex = TRACK_STAGES.findIndex(s => s.match.includes(currentStatus));
    if (activeStageIndex === -1) activeStageIndex = 0;

    timelineEl.innerHTML = TRACK_STAGES.map((stage, idx) => {
      let stateClass = "";
      if (idx < activeStageIndex) {
        stateClass = "completed";
      } else if (idx === activeStageIndex) {
        stateClass = "current";
      }

      return `
        <div class="timeline-step ${stateClass}">
          <div class="timeline-circle">
            ${idx < activeStageIndex ? '✓' : (idx + 1)}
          </div>
          <div class="timeline-label">${stage.label}</div>
        </div>
      `;
    }).join("");
  },

  async handleCancel(orderNumber) {
    const confirmed = confirm(`Are you sure you wish to cancel order ${orderNumber}?\n\nOnce cancelled, the reserved timepiece will be returned to the boutique inventory.`);
    if (!confirmed) return;

    try {
      const reason = prompt("Please provide a reason for cancellation (optional):", "Customer requested cancellation");
      const res = await apiRequest(`/api/orders/${orderNumber}/cancel`, {
        method: "POST",
        body: JSON.stringify({ reason: reason || "Customer cancellation" })
      });
      showToast(res.message || "Order cancelled successfully", "success");
      // Reload order tracking
      await this.track(orderNumber, "");
    } catch (err) {
      showToast(err.message || "Failed to cancel order", "error");
    }
  }
};

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("trackOrderForm") || document.getElementById("trackingTimeline")) {
    Track.init();
  }
});
