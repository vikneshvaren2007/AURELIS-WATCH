/* ==========================================================================
   AURELIS — Admin Suite Operations Engine
   ========================================================================== */

const Admin = {
  token: localStorage.getItem("aurelis_admin_token") || "",
  catalogProducts: [],
  customerMessages: [],

  isAuth() {
    return !!this.token;
  },

  checkProtection() {
    if (!this.isAuth() && !window.location.pathname.includes("login.html")) {
      const page = window.location.pathname.split("/").pop() || "orders.html";
      window.location.href = `login.html?redirect=${encodeURIComponent(page)}`;
    }
  },

  logout() {
    localStorage.removeItem("aurelis_admin_token");
    window.location.href = "login.html";
  },

  async loadDashboard() {
    try {
      const res = await apiRequest("/api/admin/dashboard");
      const m = res.metrics;

      // Update KPI metrics
      this.setText("kpiTotalSales", formatINR(m.total_sales));
      this.setText("kpiTodaySales", formatINR(m.today_sales));
      this.setText("kpiTotalOrders", m.total_orders);
      this.setText("kpiPendingOrders", m.pending_orders);
      this.setText("kpiDeliveredOrders", m.delivered_orders);
      this.setText("kpiCancelledOrders", m.cancelled_orders);
      this.setText("kpiReturnRequests", m.return_requests);
      this.setText("kpiCustomers", m.customers);
      this.setText("kpiProducts", m.products);
      this.setText("kpiLowStock", m.low_stock_count);

      // Render Recent Orders
      const recentOrdersTable = document.getElementById("adminRecentOrdersTable");
      if (recentOrdersTable && res.recent_orders) {
        recentOrdersTable.innerHTML = res.recent_orders.map(o => `
          <tr>
            <td><strong>${o.order_number}</strong></td>
            <td>${o.customer_name}</td>
            <td>${formatINR(o.total_amount)}</td>
            <td><span class="status-pill status-${o.order_status}">${o.order_status}</span></td>
            <td>${o.payment_method} &bull; <span style="font-size: 11px;">${o.payment_status}</span></td>
            <td>${o.created_at || '-'}</td>
            <td>
              <button class="gold-btn-outline" style="padding: 6px 12px; font-size: 10px;" onclick="Admin.openOrderStatusModal(${o.id}, '${o.order_status}', '${o.order_number}')">
                Manage
              </button>
            </td>
          </tr>
        `).join("");
      }

      // Render Variant Distribution
      const variantTable = document.getElementById("adminVariantDistTable");
      if (variantTable && res.variant_distribution) {
        variantTable.innerHTML = res.variant_distribution.map(v => `
          <tr>
            <td><strong>${v.color_name}</strong></td>
            <td style="color: #2ecc71;">${v.in_stock} Units</td>
            <td style="color: #e67e22;">${v.reserved} Units</td>
          </tr>
        `).join("");
      }
    } catch (e) {
      showToast("Error fetching metrics: " + e.message, "error");
    }
  },

  ordersCache: [],

  async loadOrders() {
    const table = document.getElementById("adminOrdersTable");
    if (!table) return;

    const search = document.getElementById("adminOrderSearch")?.value || "";
    const status = document.getElementById("adminOrderStatusFilter")?.value || "";

    try {
      const res = await apiRequest(`/api/admin/orders?search=${encodeURIComponent(search)}&status=${encodeURIComponent(status)}`);
      this.ordersCache = res.orders || [];
      table.innerHTML = this.ordersCache.map(o => {
        const itemsHtml = (o.items && o.items.length > 0)
          ? o.items.map(it => `
              <div style="font-size: 11.5px; line-height: 1.4; margin-bottom: 2px;">
                <strong style="color: #fff;">${it.product_name}</strong>
                <span style="color: var(--text-muted);">&bull; ${it.variant_color || 'Standard'}</span>
                <span style="color: var(--gold-light); font-weight: 600;">(×${it.quantity})</span>
              </div>
            `).join("")
          : `<span style="font-size: 11px; color: var(--text-muted);">Standard Timepiece</span>`;

        const paymentColor = o.payment_status === 'PAID' ? '#2ecc71' : (o.payment_method === 'Cash on Delivery' ? '#e67e22' : '#f39c12');

        return `
          <tr>
            <td>
              <strong style="color: var(--gold-light); font-family: monospace; font-size: 12.5px;">${o.order_number}</strong>
            </td>
            <td>
              <strong style="color: #fff; font-size: 13px;">${o.customer_name}</strong><br>
              <span style="font-size: 11px; color: var(--text-muted);">${o.customer_email}</span><br>
              <span style="font-size: 11px; color: var(--text-secondary);">${o.customer_phone || ''}</span>
            </td>
            <td>
              ${itemsHtml}
            </td>
            <td>
              <strong style="color: var(--gold-primary); font-size: 13.5px;">${formatINR(o.total_amount)}</strong>
            </td>
            <td>
              <span style="font-size: 12px; font-weight: 500;">${o.payment_method}</span><br>
              <span style="font-size: 10.5px; font-weight: 600; color: ${paymentColor}; letter-spacing: 0.5px;">${o.payment_status}</span>
            </td>
            <td>
              <span class="status-pill status-${o.order_status}">${o.order_status}</span>
            </td>
            <td>
              <span style="font-size: 11.5px; color: var(--text-muted);">${o.created_at || '-'}</span>
            </td>
            <td>
              <div style="display: flex; flex-direction: column; gap: 5px;">
                <button class="gold-btn" style="padding: 5px 10px; font-size: 10px;" onclick="Admin.openOrderDetailsModal(${o.id})">
                  Inspect
                </button>
                <button class="gold-btn-outline" style="padding: 5px 10px; font-size: 10px;" onclick="Admin.openOrderStatusModal(${o.id}, '${o.order_status}', '${o.order_number}')">
                  Update Status
                </button>
              </div>
            </td>
          </tr>
        `;
      }).join("");
    } catch (e) {
      showToast(e.message, "error");
    }
  },

  openOrderDetailsModal(orderId) {
    const o = this.ordersCache.find(x => x.id === orderId);
    if (!o) return;

    const modal = document.getElementById("adminOrderDetailsModal");
    if (!modal) return;

    document.getElementById("inspOrderNumber").textContent = o.order_number;
    const badge = document.getElementById("inspOrderStatusBadge");
    badge.className = `status-pill status-${o.order_status}`;
    badge.textContent = o.order_status;

    document.getElementById("inspCustomerName").textContent = o.customer_name || 'N/A';
    document.getElementById("inspCustomerEmail").textContent = o.customer_email || 'N/A';
    document.getElementById("inspCustomerPhone").textContent = o.customer_phone || 'N/A';
    document.getElementById("inspUserId").textContent = o.user_id ? `Account User ID: #${o.user_id}` : 'Guest Commission';

    const addr = o.shipping_address || {};
    document.getElementById("inspShippingAddress").innerHTML = `
      ${addr.address_line1 || addr.street || ''}${addr.address_line2 ? `<br>${addr.address_line2}` : ''}<br>
      ${addr.city || ''}, ${addr.state || ''} ${addr.postal_code || addr.pincode || ''}<br>
      ${addr.country || 'India'}
    `;

    const itemsContainer = document.getElementById("inspOrderItemsList");
    if (o.items && o.items.length > 0) {
      itemsContainer.innerHTML = o.items.map(it => `
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; border-bottom: 1px solid var(--border-subtle); background: rgba(0,0,0,0.2);">
          <div>
            <div style="font-weight: 600; color: #fff; font-size: 13px;">${it.product_name}</div>
            <div style="font-size: 11px; color: var(--gold-primary);">Variant: ${it.variant_color || 'Standard Edition'}</div>
          </div>
          <div style="text-align: right;">
            <div style="font-size: 13px; font-weight: 600; color: #fff;">${formatINR(it.total_price || (it.unit_price * it.quantity))}</div>
            <div style="font-size: 11px; color: var(--text-muted);">${formatINR(it.unit_price)} × ${it.quantity}</div>
          </div>
        </div>
      `).join("");
    } else {
      itemsContainer.innerHTML = '<div style="padding: 12px; font-size: 12px; color: var(--text-muted);">Standard Timepiece Specification</div>';
    }

    document.getElementById("inspPaymentMethod").textContent = o.payment_method || 'Online';
    const payStatusEl = document.getElementById("inspPaymentStatus");
    payStatusEl.textContent = o.payment_status || 'PENDING';
    payStatusEl.style.color = o.payment_status === 'PAID' ? '#2ecc71' : '#f39c12';
    document.getElementById("inspTransactionId").textContent = o.transaction_id || 'N/A';

    document.getElementById("inspSubtotal").textContent = formatINR(o.subtotal || o.total_amount);
    document.getElementById("inspTotal").textContent = formatINR(o.total_amount);

    const quickUpdateBtn = document.getElementById("inspQuickUpdateBtn");
    if (quickUpdateBtn) {
      quickUpdateBtn.onclick = () => {
        modal.classList.remove("active");
        this.openOrderStatusModal(o.id, o.order_status, o.order_number);
      };
    }

    modal.classList.add("active");
  },

  openOrderStatusModal(orderId, currentStatus, orderNumber) {
    const modal = document.getElementById("orderStatusModal");
    if (!modal) return;

    document.getElementById("modalOrderId").value = orderId;
    document.getElementById("modalOrderNumberDisplay").textContent = orderNumber;
    document.getElementById("modalOrderStatusSelect").value = currentStatus;
    modal.classList.add("active");
  },

  async saveOrderStatus() {
    const orderId = document.getElementById("modalOrderId").value;
    const newStatus = document.getElementById("modalOrderStatusSelect").value;
    const notes = document.getElementById("modalOrderNotes").value;

    try {
      await apiRequest(`/api/admin/orders/${orderId}/status`, {
        method: "PUT",
        body: JSON.stringify({ order_status: newStatus, notes })
      });
      showToast("Order status updated successfully", "success");
      document.getElementById("orderStatusModal").classList.remove("active");
      if (window.location.pathname.includes("orders.html")) {
        this.loadOrders();
      } else {
        this.loadDashboard();
      }
    } catch (e) {
      showToast(e.message, "error");
    }
  },

  /* ==========================================================================
     PRODUCT CATALOG MANAGEMENT (ALL 10 WATCHES)
     ========================================================================== */
  async loadProductsCatalog() {
    const tbody = document.getElementById("adminProductsList");
    if (!tbody) return;

    try {
      const res = await apiRequest("/api/admin/products");
      this.catalogProducts = res.products || [];
      tbody.innerHTML = this.catalogProducts.map(p => {
        const imgSrc = p.main_image || p.primary_image || (p.variants && p.variants[0] ? p.variants[0].image_url : '/assets/fallback-watch.svg');
        const stock = p.stock_quantity !== undefined ? p.stock_quantity : (p.variants && p.variants[0] ? p.variants[0].stock_quantity : 0);
        return `
          <tr>
            <td>
              <img src="${imgSrc}" style="width: 52px; height: 52px; object-fit: contain; background: #080807; border: 1px solid var(--border-subtle); border-radius: 4px;" onerror="this.src='/assets/fallback-watch.svg'">
            </td>
            <td>
              <strong style="font-size: 13.5px;">${p.name}</strong><br>
              <span style="font-size: 11px; color: var(--text-muted);">${p.short_description || ''}</span>
            </td>
            <td>
              <span class="badge-gold">${p.style || 'Classic Luxury'}</span><br>
              <span style="font-size: 11px; color: var(--text-secondary);">${p.color || ''}</span>
            </td>
            <td><code>${p.sku || 'AUR-TIMEPIECE'}</code></td>
            <td>
              <strong style="color: var(--gold-light);">${formatINR(p.base_price)}</strong>
              ${p.discount_price ? `<br><span style="font-size: 11px; color: var(--text-muted); text-decoration: line-through;">${formatINR(p.discount_price)}</span>` : ''}
            </td>
            <td>
              <strong style="color: ${stock <= 3 ? '#e67e22' : '#2ecc71'};">${stock} Units</strong>
            </td>
            <td>
              <span style="font-size: 11px; color: var(--gold-primary); font-weight: 600;">6-Month Warranty</span>
            </td>
            <td>
              <span class="status-pill status-${p.is_active ? 'CONFIRMED' : 'CANCELLED'}">
                ${p.is_active ? 'ACTIVE' : 'INACTIVE'}
              </span>
            </td>
            <td>
              <div style="display: flex; gap: 6px;">
                <button class="gold-btn" style="padding: 6px 12px; font-size: 10px;" onclick="Admin.openEditProductModal(${p.id})">
                  Edit
                </button>
                <button class="gold-btn-outline" style="padding: 6px 10px; font-size: 10px; color: #e74c3c; border-color: #e74c3c;" onclick="Admin.deleteProduct(${p.id}, '${p.name.replace(/'/g, "\\'")}')">
                  Delete
                </button>
              </div>
            </td>
          </tr>
        `;
      }).join("");
    } catch (e) {
      showToast("Error loading catalog: " + e.message, "error");
    }
  },

  openAddProductModal() {
    const modal = document.getElementById("productModal");
    if (!modal) return;

    document.getElementById("prodEditId").value = "";
    document.getElementById("productModalTitle").textContent = "Add New Timepiece";
    document.getElementById("prodName").value = "";
    document.getElementById("prodStyle").value = "Classic Luxury";
    document.getElementById("prodColor").value = "";
    document.getElementById("prodSku").value = `AUR-${Date.now().toString().slice(-4)}`;
    document.getElementById("prodStock").value = "15";
    document.getElementById("prodPrice").value = "2199";
    document.getElementById("prodDiscountPrice").value = "2899";
    document.getElementById("prodImage").value = "/assets/watches/watch_1.jpg";
    document.getElementById("prodShortDesc").value = "";
    document.getElementById("prodDesc").value = "";

    modal.classList.add("active");
  },

  openEditProductModal(productId) {
    const modal = document.getElementById("productModal");
    if (!modal) return;

    const p = this.catalogProducts.find(item => item.id === productId);
    if (!p) return;

    document.getElementById("prodEditId").value = p.id;
    document.getElementById("productModalTitle").textContent = `Edit ${p.name}`;
    document.getElementById("prodName").value = p.name || "";
    document.getElementById("prodStyle").value = p.style || "";
    document.getElementById("prodColor").value = p.color || "";
    document.getElementById("prodSku").value = p.sku || "";
    document.getElementById("prodStock").value = p.stock_quantity !== undefined ? p.stock_quantity : 15;
    document.getElementById("prodPrice").value = p.base_price || 2199;
    document.getElementById("prodDiscountPrice").value = p.discount_price || 2899;
    document.getElementById("prodImage").value = p.main_image || p.primary_image || "/assets/watches/watch_1.jpg";
    document.getElementById("prodShortDesc").value = p.short_description || "";
    document.getElementById("prodDesc").value = p.description || "";

    modal.classList.add("active");
  },

  async saveProduct() {
    const editId = document.getElementById("prodEditId")?.value;
    const name = document.getElementById("prodName")?.value.trim();
    const style = document.getElementById("prodStyle")?.value.trim();
    const color = document.getElementById("prodColor")?.value.trim();
    const sku = document.getElementById("prodSku")?.value.trim();
    const stock = parseInt(document.getElementById("prodStock")?.value || "10");
    const price = parseFloat(document.getElementById("prodPrice")?.value || "2199");
    const discountPrice = parseFloat(document.getElementById("prodDiscountPrice")?.value || "2899");
    const image = document.getElementById("prodImage")?.value.trim() || "/assets/watches/watch_1.jpg";
    const shortDesc = document.getElementById("prodShortDesc")?.value.trim();
    const desc = document.getElementById("prodDesc")?.value.trim();

    if (!name || !price) {
      showToast("Timepiece name and selling price are mandatory", "error");
      return;
    }

    if (price <= 0) {
      showToast("Selling price must be greater than zero", "error");
      return;
    }

    const payload = {
      name,
      style,
      color,
      sku,
      stock_quantity: stock,
      base_price: price,
      discount_price: discountPrice,
      main_image: image,
      short_description: shortDesc,
      description: desc,
      warranty: "6-Month Warranty",
      is_active: 1
    };

    try {
      if (editId) {
        await apiRequest(`/api/admin/products/${editId}`, {
          method: "PUT",
          body: JSON.stringify(payload)
        });
        showToast("Timepiece updated successfully", "success");
      } else {
        await apiRequest("/api/admin/products", {
          method: "POST",
          body: JSON.stringify(payload)
        });
        showToast("New timepiece added to catalog", "success");
      }

      document.getElementById("productModal")?.classList.remove("active");
      this.loadProductsCatalog();
    } catch (e) {
      showToast(e.message, "error");
    }
  },

  async deleteProduct(productId, name) {
    if (!confirm(`Are you sure you want to deactivate or remove ${name} from the catalog?`)) {
      return;
    }
    try {
      await apiRequest(`/api/admin/products/${productId}`, { method: "DELETE" });
      showToast("Timepiece removed from catalog", "success");
      this.loadProductsCatalog();
    } catch (e) {
      showToast(e.message, "error");
    }
  },

  /* ==========================================================================
     CUSTOMER CONCIERGE INQUIRIES & REPLIES
     ========================================================================== */
  async loadMessages() {
    const table = document.getElementById("adminMessagesTable");
    if (!table) return;

    try {
      const res = await apiRequest("/api/admin/messages");
      this.customerMessages = res.messages || [];

      if (this.customerMessages.length === 0) {
        table.innerHTML = `
          <tr>
            <td colspan="7" style="text-align: center; padding: 40px; color: var(--text-muted);">
              No customer inquiries logged yet. All incoming messages will appear here.
            </td>
          </tr>
        `;
        return;
      }

      table.innerHTML = this.customerMessages.map(m => `
        <tr>
          <td>#${m.id}</td>
          <td>${m.created_at || '-'}</td>
          <td>
            <strong>${m.name}</strong><br>
            <span style="font-size: 11px; color: var(--gold-light);">${m.email}</span><br>
            <span style="font-size: 11px; color: var(--text-muted);">${m.phone}</span>
          </td>
          <td><span class="badge-gold">${m.subject || 'General'}</span></td>
          <td style="max-width: 300px; font-size: 12.5px; line-height: 1.5; color: var(--text-secondary);">
            ${m.message}
            ${(m.admin_reply || m.reply) ? `<div style="margin-top: 6px; padding: 6px 10px; background: rgba(217, 174, 85, 0.08); border-left: 2px solid var(--gold-primary); font-size: 11px; color: var(--gold-light);"><strong>Atelier Reply:</strong> ${m.admin_reply || m.reply}</div>` : ''}
          </td>
          <td>
            <span class="status-pill status-${m.status === 'RESOLVED' ? 'CONFIRMED' : 'PROCESSING'}">
              ${m.status || 'PENDING'}
            </span>
          </td>
          <td>
            <button class="gold-btn" style="padding: 6px 12px; font-size: 10px;" onclick="Admin.openReplyModal(${m.id}, '${m.email}', '${(m.subject || '').replace(/'/g, "\\'")}', '${(m.message || '').replace(/'/g, "\\'")}')">
              ${m.status === 'RESOLVED' ? 'Reply Again' : 'Reply'}
            </button>
          </td>
        </tr>
      `).join("");
    } catch (e) {
      showToast("Error loading messages: " + e.message, "error");
    }
  },

  openReplyModal(msgId, email, subject, originalMsg) {
    const modal = document.getElementById("replyModal");
    if (!modal) return;

    document.getElementById("replyMsgId").value = msgId;
    document.getElementById("replyToEmail").value = email;
    document.getElementById("replySubject").value = `Re: ${subject}`;
    document.getElementById("replyOriginalMsg").textContent = originalMsg;
    document.getElementById("replyContent").value = "";

    modal.classList.add("active");
  },

  async sendCustomerReply() {
    const msgId = document.getElementById("replyMsgId")?.value;
    const reply = document.getElementById("replyContent")?.value.trim();
    const btn = document.getElementById("sendReplyBtn");

    if (!reply) {
      showToast("Please enter your response message", "error");
      return;
    }

    if (btn) {
      btn.disabled = true;
      btn.textContent = "SENDING RESPONSE EMAIL...";
    }

    try {
      await apiRequest(`/api/admin/messages/${msgId}/reply`, {
        method: "POST",
        body: JSON.stringify({ reply })
      });
      showToast("Response transmitted to customer and logged in archive", "success");
      document.getElementById("replyModal")?.classList.remove("active");
      this.loadMessages();
    } catch (e) {
      showToast(e.message, "error");
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = "Send Response Email & Mark Resolved";
      }
    }
  },

  /* ==========================================================================
     INVENTORY & SETTINGS
     ========================================================================== */
  async loadInventory() {
    const table = document.getElementById("adminInventoryTable");
    if (!table) return;

    try {
      const res = await apiRequest("/api/admin/inventory");
      table.innerHTML = res.inventory.map(v => `
        <tr>
          <td><img src="${v.image_url || '/assets/fallback-watch.svg'}" style="width: 44px; height: 44px; object-fit: contain; background: #080807; border: 1px solid var(--border-subtle); border-radius: 3px;" onerror="this.src='/assets/fallback-watch.svg'"></td>
          <td><strong>${v.color_name}</strong><br><span style="font-size: 10px; color: var(--text-muted);">${v.sku}</span></td>
          <td>${formatINR(v.price)}</td>
          <td><strong>${v.stock_quantity}</strong></td>
          <td>${v.reserved_quantity}</td>
          <td><span style="color: ${v.available_quantity <= v.low_stock_threshold ? '#e67e22' : '#2ecc71'}; font-weight: 600;">${v.available_quantity}</span></td>
          <td>
            <button class="gold-btn-outline" style="padding: 5px 10px; font-size: 10px;" onclick="Admin.promptStockAdjust(${v.id}, ${v.stock_quantity}, '${v.color_name.replace(/'/g, "\\'")}')">
              Adjust Stock
            </button>
          </td>
        </tr>
      `).join("");
    } catch (e) {
      showToast(e.message, "error");
    }
  },

  async promptStockAdjust(variantId, currentStock, name) {
    const newStock = prompt(`Update stock count for ${name}:`, currentStock);
    if (newStock !== null && !isNaN(parseInt(newStock))) {
      try {
        await apiRequest("/api/admin/inventory", {
          method: "PUT",
          body: JSON.stringify({ variant_id: variantId, stock_quantity: parseInt(newStock) })
        });
        showToast("Stock quantity updated", "success");
        this.loadInventory();
      } catch (e) {
        showToast(e.message, "error");
      }
    }
  },

  async loadSettings() {
    try {
      const res = await apiRequest("/api/admin/settings");
      const s = res.settings;

      const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.value = val !== undefined ? val : "";
      };

      setVal("settingTaxPercent", s.tax_percent);
      setVal("settingShippingFee", s.shipping_fee);
      setVal("settingReturnDays", s.return_days);
      setVal("settingCodEnabled", s.cod_enabled);
      setVal("settingAdminName", s.admin_name);
      setVal("settingAdminPhone", s.admin_phone);
      setVal("settingAdminLocation", s.admin_location);
      setVal("settingAdminEmail", s.admin_email);
    } catch (e) {
      showToast(e.message, "error");
    }
  },

  async saveSettings() {
    const payload = {
      tax_percent: document.getElementById("settingTaxPercent")?.value,
      shipping_fee: document.getElementById("settingShippingFee")?.value,
      return_days: document.getElementById("settingReturnDays")?.value,
      cod_enabled: document.getElementById("settingCodEnabled")?.value,
      admin_name: document.getElementById("settingAdminName")?.value,
      admin_phone: document.getElementById("settingAdminPhone")?.value,
      admin_location: document.getElementById("settingAdminLocation")?.value,
      admin_email: document.getElementById("settingAdminEmail")?.value
    };

    try {
      await apiRequest("/api/admin/settings", {
        method: "PUT",
        body: JSON.stringify(payload)
      });
      showToast("Store settings saved successfully", "success");
    } catch (e) {
      showToast(e.message, "error");
    }
  },

  closeMobileSidebar() {
    const sidebar = document.querySelector(".admin-sidebar");
    const backdrop = document.querySelector(".admin-sidebar-backdrop");
    if (sidebar) sidebar.classList.remove("mobile-open");
    if (backdrop) backdrop.classList.remove("active");
  },

  toggleMobileSidebar() {
    const sidebar = document.querySelector(".admin-sidebar");
    const backdrop = document.querySelector(".admin-sidebar-backdrop");
    if (sidebar) {
      const isOpen = sidebar.classList.toggle("mobile-open");
      if (backdrop) backdrop.classList.toggle("active", isOpen);
    }
  },

  initMobileNavigation() {
    const sidebar = document.querySelector(".admin-sidebar");
    if (!sidebar) return;

    // Create backdrop if not already existing
    let backdrop = document.querySelector(".admin-sidebar-backdrop");
    if (!backdrop) {
      backdrop = document.createElement("div");
      backdrop.className = "admin-sidebar-backdrop";
      document.body.appendChild(backdrop);
    }

    const toggleSidebar = () => this.toggleMobileSidebar();
    const closeSidebar = () => this.closeMobileSidebar();

    backdrop.removeEventListener("click", closeSidebar);
    backdrop.addEventListener("click", closeSidebar);

    // Bind existing or inject hamburger button into admin header
    const header = document.querySelector(".admin-header");
    let toggleBtn = document.getElementById("adminMobileToggle");
    if (header && !toggleBtn) {
      toggleBtn = document.createElement("button");
      toggleBtn.type = "button";
      toggleBtn.id = "adminMobileToggle";
      toggleBtn.className = "admin-mobile-toggle";
      toggleBtn.setAttribute("aria-label", "Toggle Menu");
      toggleBtn.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
          <line x1="3" y1="6" x2="21" y2="6"></line>
          <line x1="3" y1="12" x2="21" y2="12"></line>
          <line x1="3" y1="18" x2="21" y2="18"></line>
        </svg>
      `;
      header.insertBefore(toggleBtn, header.firstChild);
    }

    if (toggleBtn) {
      toggleBtn.removeEventListener("click", toggleSidebar);
      toggleBtn.addEventListener("click", toggleSidebar);
    }

    // Close on escape key
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeSidebar();
    });

    // Close on nav link click
    document.querySelectorAll(".admin-nav-item").forEach(link => {
      link.addEventListener("click", () => {
        if (window.innerWidth <= 992) closeSidebar();
      });
    });
  },

  setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }
};

document.addEventListener("DOMContentLoaded", () => {
  if (window.location.pathname.includes("/admin/")) {
    Admin.checkProtection();
    Admin.initMobileNavigation();
    if (document.getElementById("kpiTotalSales")) Admin.loadDashboard();
    if (document.getElementById("adminOrdersTable")) Admin.loadOrders();
    if (document.getElementById("adminInventoryTable")) Admin.loadInventory();
    if (document.getElementById("settingTaxPercent")) Admin.loadSettings();
    if (document.getElementById("adminProductsList")) Admin.loadProductsCatalog();
    if (document.getElementById("adminMessagesTable")) Admin.loadMessages();
  }
});
