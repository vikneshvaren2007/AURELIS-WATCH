/* ==========================================================================
   AURELIS — Product Detail Page (PDP) Engine (10 Timepieces Collection)
   ========================================================================== */

const ProductPage = {
  product: null,
  selectedVariant: null,
  quantity: 1,

  async init() {
    const params = new URLSearchParams(window.location.search);
    const id = params.get("id") || "1";
    await this.loadProduct(id);
    this.bindEvents();
    this.loadRelatedProducts();
  },

  async loadProduct(identifier) {
    try {
      const res = await apiRequest(`/api/products/${identifier}`);
      this.product = res.product;
      this.selectedVariant = (this.product.variants && this.product.variants.length > 0)
        ? this.product.variants[0]
        : null;
      this.render();
    } catch (e) {
      showToast("Timepiece edition could not be loaded: " + e.message, "error");
    }
  },

  selectVariant(variantId) {
    if (!this.product.variants) return;
    const found = this.product.variants.find(v => v.id === variantId);
    if (found) {
      this.selectedVariant = found;
      this.updateVariantDisplay();
    }
  },

  updateVariantDisplay() {
    if (!this.selectedVariant) return;

    // Update Main Image
    const mainImg = document.getElementById("pdpMainImage");
    if (mainImg) {
      mainImg.style.opacity = "0.4";
      setTimeout(() => {
        let src = this.selectedVariant.image_url || this.product.main_image || './assets/fallback-watch.svg';
        if (src.startsWith('/')) src = '.' + src;
        mainImg.src = src;
        mainImg.style.opacity = "1";
      }, 150);
    }

    // Update Variant Cards Active Class
    document.querySelectorAll(".variant-option-card").forEach(card => {
      const cardId = parseInt(card.dataset.variantId);
      card.classList.toggle("active", cardId === this.selectedVariant.id);
    });

    // Update Variant Name Label
    const nameLabel = document.getElementById("selectedVariantName");
    if (nameLabel) nameLabel.textContent = this.selectedVariant.color_name;

    // Update SKU
    const skuEl = document.getElementById("pdpSku");
    if (skuEl) skuEl.textContent = `REFERENCE / SKU: ${this.selectedVariant.sku || this.product.sku || 'AUR-TIMEPIECE'}`;

    // Update Price
    const priceEl = document.getElementById("pdpPrice");
    const origPriceEl = document.getElementById("pdpOriginalPrice");
    const price = this.selectedVariant.price || this.product.base_price;
    const origPrice = this.selectedVariant.discount_price || this.product.discount_price;

    if (priceEl) priceEl.textContent = formatINR(price);
    if (origPriceEl) {
      if (origPrice) {
        origPriceEl.style.display = "inline";
        origPriceEl.textContent = formatINR(origPrice);
      } else {
        origPriceEl.style.display = "none";
      }
    }

    // Update Stock Availability
    const stockEl = document.getElementById("pdpStockStatus");
    if (stockEl) {
      const avail = this.selectedVariant.available_stock !== undefined ? this.selectedVariant.available_stock : (this.product.stock_quantity || 10);
      if (avail <= 0) {
        stockEl.innerHTML = `<span class="badge-low-stock" style="background: rgba(231,76,60,0.2); color:#e74c3c; border-color:#e74c3c;">Out of Stock</span>`;
      } else if (avail <= 3) {
        stockEl.innerHTML = `<span class="badge-low-stock">Only ${avail} Commission(s) Left</span>`;
      } else {
        stockEl.innerHTML = `<span class="badge-stock">In Stock &bull; Ready for Atelier Dispatch</span>`;
      }
    }
  },

  render() {
    if (!this.product) return;

    // Title, Eyebrow & Descriptions
    const titleEl = document.getElementById("pdpTitle");
    const eyebrowEl = document.getElementById("pdpEyebrow");
    const shortDescEl = document.getElementById("pdpShortDesc");
    const descEl = document.getElementById("pdpFullDesc");
    const breadcrumbEl = document.getElementById("pdpBreadcrumb");
    const mainImg = document.getElementById("pdpMainImage");

    if (titleEl) titleEl.textContent = this.product.name;
    if (eyebrowEl) eyebrowEl.textContent = `HAUTE HORLOGERIE &bull; ${this.product.style || 'LIMITED ATELIER EDITION'}`;
    if (shortDescEl) shortDescEl.textContent = this.product.short_description || "";
    if (descEl) descEl.textContent = this.product.description || "";
    if (breadcrumbEl) breadcrumbEl.textContent = this.product.name;
    if (mainImg) {
      let mainSrc = this.product.main_image || this.product.primary_image || (this.selectedVariant ? this.selectedVariant.image_url : './assets/fallback-watch.svg');
      if (mainSrc.startsWith('/')) mainSrc = '.' + mainSrc;
      mainImg.src = mainSrc;
      mainImg.onerror = () => { mainImg.src = './assets/fallback-watch.svg'; };
    }

    // Set page document title
    document.title = `${this.product.name} — AURELIS Luxury Timepieces`;

    // Render Color Variants
    const variantGrid = document.getElementById("variantCardsGrid");
    const nameLabel = document.getElementById("selectedVariantName");
    if (nameLabel) nameLabel.textContent = this.product.color || (this.selectedVariant ? this.selectedVariant.color_name : 'Artisan Finish');

    if (variantGrid && this.product.variants && this.product.variants.length > 0) {
      variantGrid.innerHTML = this.product.variants.map((v, idx) => {
        let vSrc = v.image_url || this.product.main_image || './assets/fallback-watch.svg';
        if (vSrc.startsWith('/')) vSrc = '.' + vSrc;
        return `
        <div class="variant-option-card ${idx === 0 ? 'active' : ''}" data-variant-id="${v.id}" onclick="ProductPage.selectVariant(${v.id})">
          <img src="${vSrc}" alt="${v.color_name}" class="variant-card-thumb" onerror="this.src='./assets/fallback-watch.svg'">
          <div>
            <div class="variant-card-title">${v.color_name}</div>
            <div class="variant-card-stock" style="color: ${(v.stock_quantity || 10) <= 3 ? '#e67e22' : '#2ecc71'};">
              ${(v.stock_quantity || 10) <= 3 ? `Only ${v.stock_quantity} left` : 'In Stock'}
            </div>
          </div>
        </div>
      `;
      }).join("");
    } else if (variantGrid) {
      // Single finish card
      let sSrc = this.product.main_image || './assets/fallback-watch.svg';
      if (sSrc.startsWith('/')) sSrc = '.' + sSrc;
      variantGrid.innerHTML = `
        <div class="variant-option-card active">
          <img src="${sSrc}" alt="${this.product.name}" class="variant-card-thumb" onerror="this.src='./assets/fallback-watch.svg'">
          <div>
            <div class="variant-card-title">${this.product.color || 'Signature Finish'}</div>
            <div class="variant-card-stock" style="color: #2ecc71;">In Stock &bull; Tenkasi Atelier</div>
          </div>
        </div>
      `;
    }

    // Render Thumbnails
    const thumbsContainer = document.getElementById("pdpThumbnails");
    if (thumbsContainer) {
      const images = [];
      if (this.product.main_image) images.push(this.product.main_image);
      if (this.product.images && this.product.images.length > 0) {
        this.product.images.forEach(img => {
          if (!images.includes(img.image_url)) images.push(img.image_url);
        });
      }

      thumbsContainer.innerHTML = images.map((rawUrl, i) => {
        let imgUrl = rawUrl.startsWith('/') ? '.' + rawUrl : rawUrl;
        return `
        <div class="pdp-thumb ${i === 0 ? 'active' : ''}" onclick="ProductPage.switchGalleryImage('${imgUrl}', this)">
          <img src="${imgUrl}" alt="Gallery preview ${i + 1}" onerror="this.src='./assets/fallback-watch.svg'">
        </div>
      `;
      }).join("");
    }

    // Price, SKU & Stock
    this.updateVariantDisplay();

    // Specifications Table
    const specsTable = document.getElementById("pdpSpecsTable");
    if (specsTable) {
      let specs = this.product.specifications;
      if (typeof specs === "string") {
        try { specs = JSON.parse(specs); } catch (e) { specs = null; }
      }

      const defaultSpecs = {
        "Movement": "High-Precision Japanese Caliber",
        "Case Diameter": "41 mm",
        "Case Thickness": "10.0 mm",
        "Case Material": "316L Solid Surgical Stainless Steel",
        "Dial": "Sunburst Guilloché with Applied Luminous Markers",
        "Strap": "Solid Stainless Steel / Milanese Mesh Bracelet",
        "Crystal": "Flame-Fusion Scratch-Resistant Sapphire Crystal",
        "Water Resistance": "5 ATM / 50 Meters",
        "Warranty": "6-Month Manufacturer Movement Warranty",
        "Clasp": "Concealed Butterfly Deployment Clasp"
      };

      const finalSpecs = specs || defaultSpecs;

      specsTable.innerHTML = Object.entries(finalSpecs).map(([label, val]) => `
        <tr>
          <td>${label}</td>
          <td>${label === 'Warranty' ? `<strong style="color: var(--gold-primary);">${val}</strong> &bull; <a href="warranty.html" style="text-decoration: underline; font-size: 11px;">Coverage Details</a>` : val}</td>
        </tr>
      `).join("");
    }
  },

  switchGalleryImage(imgUrl, thumbEl) {
    const mainImg = document.getElementById("pdpMainImage");
    if (mainImg) {
      mainImg.style.opacity = "0.3";
      setTimeout(() => {
        mainImg.src = imgUrl;
        mainImg.style.opacity = "1";
      }, 150);
    }
    document.querySelectorAll(".pdp-thumb").forEach(t => t.classList.remove("active"));
    if (thumbEl) thumbEl.classList.add("active");
  },

  bindEvents() {
    const minusBtn = document.getElementById("qtyMinus");
    const plusBtn = document.getElementById("qtyPlus");
    const qtyInput = document.getElementById("pdpQuantityInput");

    if (minusBtn && plusBtn && qtyInput) {
      minusBtn.addEventListener("click", () => {
        if (this.quantity > 1) {
          this.quantity--;
          qtyInput.value = this.quantity;
        }
      });

      plusBtn.addEventListener("click", () => {
        const maxStock = (this.selectedVariant ? this.selectedVariant.available_stock : (this.product ? this.product.stock_quantity : 10)) || 10;
        if (this.quantity < maxStock) {
          this.quantity++;
          qtyInput.value = this.quantity;
        } else {
          showToast(`Maximum atelier stock available is ${maxStock}`, "info");
        }
      });
    }

    const addBtn = document.getElementById("pdpAddToCartBtn");
    if (addBtn) {
      addBtn.addEventListener("click", async () => {
        if (!this.product) return;
        const variantId = this.selectedVariant ? this.selectedVariant.id : 1;
        try {
          addBtn.disabled = true;
          addBtn.textContent = "COMMISSIONING...";
          await Cart.addItem(this.product.id, variantId, this.quantity);
          showToast(`${this.quantity} × ${this.product.name} added to commission cart`, "success");
        } catch (e) {
          showToast(e.message, "error");
        } finally {
          addBtn.disabled = false;
          addBtn.textContent = "Add to Commission";
        }
      });
    }

    const buyNowBtn = document.getElementById("pdpBuyNowBtn");
    if (buyNowBtn) {
      buyNowBtn.addEventListener("click", async () => {
        if (!this.product) return;
        const variantId = this.selectedVariant ? this.selectedVariant.id : 1;
        try {
          buyNowBtn.disabled = true;
          buyNowBtn.textContent = "PREPARING CHECKOUT...";
          await Cart.addItem(this.product.id, variantId, this.quantity);
          window.location.href = "checkout.html";
        } catch (e) {
          showToast(e.message, "error");
          buyNowBtn.disabled = false;
          buyNowBtn.textContent = "Acquire Now";
        }
      });
    }
  },

  async loadRelatedProducts() {
    const grid = document.getElementById("relatedProductsGrid");
    if (!grid) return;

    try {
      const res = await apiRequest("/api/products");
      const others = (res.products || []).filter(p => !this.product || p.id !== this.product.id).slice(0, 3);
      grid.innerHTML = others.map(p => {
        let pSrc = p.primary_image || p.main_image || './assets/fallback-watch.svg';
        if (pSrc.startsWith('/')) pSrc = '.' + pSrc;
        return `
        <div class="product-card">
          <div class="product-card-badges">
            <span class="badge-gold">${p.style || 'Atelier'}</span>
            <span class="badge-stock">In Stock</span>
          </div>
          <a href="product.html?id=${p.id}" class="product-image-wrap">
            <img src="${pSrc}" alt="${p.name}" onerror="this.src='./assets/fallback-watch.svg'" loading="lazy">
          </a>
          <div class="product-info">
            <div style="font-size: 10px; color: var(--gold-light); margin-bottom: 4px;">🛡️ 6-Month Warranty</div>
            <h3 class="product-title"><a href="product.html?id=${p.id}">${p.name}</a></h3>
            <div class="product-price-row">
              <span class="product-price">${formatINR(p.base_price)}</span>
            </div>
            <div class="product-card-actions">
              <a href="product.html?id=${p.id}" class="gold-btn" style="text-align: center;">View Timepiece</a>
            </div>
          </div>
        </div>
      `;
      }).join("");
    } catch (e) {}
  }
};

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("pdpTitle")) {
    ProductPage.init();
  }
});
