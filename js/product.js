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
    const variantId = params.get("variant");
    await this.loadProduct(id, variantId);
    this.bindEvents();
  },

  async loadProduct(identifier, initialVariantId = null) {
    try {
      const res = await apiRequest(`/api/products/${identifier}`);
      this.product = res.product;
      if (this.product.variants && this.product.variants.length > 0) {
        // Preload all variant images immediately to ensure zero flicker when switching
        this.product.variants.forEach(v => {
          if (v.image_url) {
            const pre = new Image();
            let pSrc = v.image_url.startsWith('/') ? '.' + v.image_url : v.image_url;
            pre.src = pSrc;
          }
        });
        if (initialVariantId) {
          const matched = this.product.variants.find(v => v.id === parseInt(initialVariantId));
          this.selectedVariant = matched || this.product.variants[0];
        } else {
          this.selectedVariant = this.product.variants[0];
        }
      } else {
        this.selectedVariant = null;
      }
      this.render();
      if (this.selectedVariant) {
        this.updateVariantDisplay();
      }
      this.loadReviews(this.product.id);
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

    // Update Main Image smoothly and immediately
    const mainImg = document.getElementById("pdpMainImage");
    if (mainImg) {
      let src = this.selectedVariant.image_url || this.product.main_image || './assets/fallback-watch.svg';
      if (src.startsWith('/')) src = '.' + src;
      mainImg.src = src;
    }

    // Update Variant Cards Active Class (border highlight)
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
    if (nameLabel) nameLabel.textContent = this.selectedVariant ? this.selectedVariant.color_name : (this.product.color || 'Artisan Finish');

    if (variantGrid && this.product.variants && this.product.variants.length > 0) {
      variantGrid.innerHTML = this.product.variants.map((v, idx) => {
        let vSrc = v.image_url || this.product.main_image || './assets/fallback-watch.svg';
        if (vSrc.startsWith('/')) vSrc = '.' + vSrc;
        const isSelected = this.selectedVariant ? this.selectedVariant.id === v.id : idx === 0;
        const vPrice = v.price || this.product.base_price;
        const vOrigPrice = v.discount_price || this.product.discount_price;
        return `
        <div class="variant-option-card ${isSelected ? 'active' : ''}" 
             data-variant-id="${v.id}" 
             onclick="ProductPage.selectVariant(${v.id})" 
             role="button" 
             tabindex="0"
             title="${v.color_name}">
          <img src="${vSrc}" alt="${v.color_name}" class="variant-card-thumb" onerror="this.src='./assets/fallback-watch.svg'">
          <div class="variant-card-title">${v.color_name}</div>
          <div class="variant-card-price-row">
            <span class="variant-card-price">${formatINR(vPrice)}</span>
            ${vOrigPrice ? `<span class="variant-card-orig-price">${formatINR(vOrigPrice)}</span>` : ''}
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
          <div class="variant-card-title">${this.product.color || 'Signature Finish'}</div>
          <div class="variant-card-price-row">
            <span class="variant-card-price">${formatINR(this.product.base_price)}</span>
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
        const variantId = this.selectedVariant 
          ? this.selectedVariant.id 
          : (this.product.variants && this.product.variants.length > 0 ? this.product.variants[0].id : null);
        if (!variantId) {
          showToast("Please select an atelier edition variant", "error");
          return;
        }
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
        const variantId = this.selectedVariant 
          ? this.selectedVariant.id 
          : (this.product.variants && this.product.variants.length > 0 ? this.product.variants[0].id : null);
        if (!variantId) {
          showToast("Please select an atelier edition variant", "error");
          return;
        }
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

    // Reviews Form Toggle & Submission
    const openReviewBtn = document.getElementById("openReviewModalBtn");
    const cancelReviewBtn = document.getElementById("cancelReviewBtn");
    const reviewFormModal = document.getElementById("reviewFormModal");
    const reviewForm = document.getElementById("pdpReviewForm");

    if (openReviewBtn && reviewFormModal) {
      openReviewBtn.addEventListener("click", () => {
        reviewFormModal.style.display = reviewFormModal.style.display === "none" ? "block" : "none";
      });
    }

    if (cancelReviewBtn && reviewFormModal) {
      cancelReviewBtn.addEventListener("click", () => {
        reviewFormModal.style.display = "none";
      });
    }

    if (reviewForm) {
      reviewForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!this.product) return;

        const userName = document.getElementById("reviewAuthor")?.value.trim();
        const rating = parseInt(document.getElementById("reviewRating")?.value || "5");
        const title = document.getElementById("reviewTitle")?.value.trim();
        const comment = document.getElementById("reviewComment")?.value.trim();

        if (!title || !comment) {
          showToast("Please provide both title and assessment", "error");
          return;
        }

        try {
          const submitBtn = reviewForm.querySelector("button[type='submit']");
          if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = "TRANSMITTING...";
          }

          await apiRequest("/api/reviews", {
            method: "POST",
            body: JSON.stringify({
              product_id: this.product.id,
              user_name: userName || "Anonymous Collector",
              rating,
              title,
              comment
            })
          });

          showToast("Patron appraisal submitted successfully", "success");
          reviewForm.reset();
          if (reviewFormModal) reviewFormModal.style.display = "none";
          await this.loadReviews(this.product.id);
        } catch (err) {
          showToast(err.message || "Failed to submit appraisal", "error");
        } finally {
          const submitBtn = reviewForm.querySelector("button[type='submit']");
          if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = "TRANSMIT APPRAISAL";
          }
        }
      });
    }
  },

  async loadReviews(productId) {
    const listEl = document.getElementById("pdpReviewsList");
    if (!listEl) return;
    try {
      const res = await apiRequest(`/api/reviews/product/${productId}`);
      const reviews = res.reviews || [];
      if (reviews.length === 0) {
        listEl.innerHTML = `
          <div style="grid-column: 1 / -1; padding: 25px; border: 1px dashed var(--border-gold); text-align: center; border-radius: 4px;">
            <p style="color: var(--gold-primary); font-family: 'Playfair Display', serif; font-size: 16px; margin-bottom: 5px;">Be the inaugural patron to appraise this edition.</p>
            <p style="color: var(--text-muted); font-size: 12px;">Share your discerning assessment of its chronometry, finishing, and wrist presence.</p>
          </div>
        `;
        return;
      }

      listEl.innerHTML = reviews.map(rev => {
        const starGold = '★'.repeat(rev.rating || 5);
        const starMuted = '☆'.repeat(5 - (rev.rating || 5));
        const author = this.escapeHtml(rev.user_name || "Collector");
        const title = this.escapeHtml(rev.title || "Collector Appraisal");
        const comment = this.escapeHtml(rev.comment || "");
        const dateStr = rev.created_at ? rev.created_at.split(" ")[0] : "Verified Patron";

        return `
          <div style="background: rgba(18, 16, 13, 0.6); border: 1px solid rgba(217, 174, 85, 0.2); padding: 20px; border-radius: 4px; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <div style="color: var(--gold-primary); font-size: 14px; letter-spacing: 2px;">
                  ${starGold}${starMuted}
                </div>
                <span style="font-size: 10.5px; color: var(--text-muted); letter-spacing: 0.05em;">${dateStr}</span>
              </div>
              <h4 style="font-size: 15px; font-weight: 600; color: #fff; margin-bottom: 8px;">${title}</h4>
              <p style="color: var(--text-secondary); font-size: 13px; line-height: 1.6;">${comment}</p>
            </div>
            <div style="margin-top: 15px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.06); display: flex; align-items: center; gap: 8px;">
              <span style="font-size: 11px; font-weight: 500; color: var(--gold-primary); letter-spacing: 0.08em; text-transform: uppercase;">${author}</span>
              <span style="font-size: 10px; color: #4ade80; background: rgba(74, 222, 128, 0.1); padding: 2px 6px; border-radius: 2px;">✓ Verified Patron</span>
            </div>
          </div>
        `;
      }).join("");
    } catch (e) {
      listEl.innerHTML = `<p style="color: var(--text-muted); font-size: 13px;">Unable to load appraisals at this moment.</p>`;
    }
  },

  escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
};

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("pdpTitle")) {
    ProductPage.init();
  }
});
