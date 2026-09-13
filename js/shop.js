/* ==========================================================================
   AURELIS — Shop & Catalog Filtering Engine (10 Timepieces Collection)
   ========================================================================== */

const Shop = {
  products: [],
  filters: {
    search: "",
    style: "",
    min_price: 2000,
    max_price: 60000,
    availability: "",
    sort: "featured"
  },

  async init() {
    this.bindFilters();
    await this.loadProducts();
  },

  setFilterStyle(style) {
    this.filters.style = style;
    const pills = document.querySelectorAll("#styleFilterList .filter-pill-item");
    pills.forEach(p => {
      if ((p.getAttribute("data-style") || "") === style) p.classList.add("active");
      else p.classList.remove("active");
    });
    const catCards = document.querySelectorAll(".category-card");
    catCards.forEach(c => {
      if ((c.getAttribute("data-category") || "") === style) c.classList.add("active");
      else c.classList.remove("active");
    });
    this.loadProducts();
    const el = document.getElementById("catalogSection");
    if (el) el.scrollIntoView({ behavior: "smooth" });
  },

  async loadProducts() {
    const grid = document.getElementById("productsGrid");
    if (!grid) return;

    grid.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 60px; color: var(--text-muted);">
        <p class="eyebrow">CURATING ATELIER EDITIONS</p>
        <p>Loading 10 masterwork timepieces...</p>
      </div>
    `;

    const params = new URLSearchParams();
    if (this.filters.search) params.append("search", this.filters.search);
    if (this.filters.style) params.append("style", this.filters.style);
    if (this.filters.min_price) params.append("min_price", this.filters.min_price);
    if (this.filters.max_price) params.append("max_price", this.filters.max_price);
    if (this.filters.availability) params.append("availability", this.filters.availability);
    if (this.filters.sort) params.append("sort", this.filters.sort);

    try {
      const res = await apiRequest(`/api/products?${params.toString()}`);
      this.products = res.products || [];
      this.renderGrid();
    } catch (e) {
      grid.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 60px; color: #e74c3c;">
          <p>Failed to load collection: ${e.message}</p>
        </div>
      `;
    }
  },

  renderGrid() {
    const grid = document.getElementById("productsGrid");
    const countEl = document.getElementById("catalogCount");
    if (!grid) return;

    if (countEl) countEl.textContent = `Showing ${this.products.length} Timepiece${this.products.length === 1 ? '' : 's'}`;

    if (this.products.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 80px 20px; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: 4px;">
          <p class="eyebrow">NO TIMEPIECES MATCHING FILTERS</p>
          <h3 style="margin: 10px 0 15px;">No timepieces match your current selection</h3>
          <p style="color: var(--text-secondary); margin-bottom: 25px; font-size: 14px;">Try resetting your filters to explore all 10 masterwork editions.</p>
          <button class="gold-btn-outline" onclick="Shop.resetFilters()">Reset All Filters</button>
        </div>
      `;
      return;
    }

    grid.innerHTML = this.products.map(p => {
      const primaryVariant = (p.variants && p.variants.length > 0) ? p.variants[0] : null;
      const displayPrice = p.base_price || (primaryVariant ? primaryVariant.price : 6499);
      const originalPrice = p.discount_price || (primaryVariant ? primaryVariant.discount_price : 8499);
      const stock = p.stock_quantity !== undefined ? p.stock_quantity : (primaryVariant ? primaryVariant.stock_quantity : 10);
      let imgSrc = p.primary_image || p.main_image || (primaryVariant ? primaryVariant.image_url : './assets/fallback-watch.svg');
      if (imgSrc.startsWith('/')) imgSrc = '.' + imgSrc;

      const stockBadge = (stock <= 3 && stock > 0)
        ? `<span class="badge-low-stock">Only ${stock} Left</span>`
        : `<span class="badge-stock">In Stock</span>`;

      const isMasterpiece = p.style === 'Masterpiece Collection' || p.category_name === 'Masterpiece Collection' || displayPrice >= 20000;
      const styleBadge = isMasterpiece
        ? `<span class="badge-gold" style="background: linear-gradient(135deg, #d4af37 0%, #aa7c11 100%); color: #000; font-weight: 700; border: none;">HAUTE HORLOGERIE</span>`
        : `<span class="badge-gold">${p.style || 'Artisan Edition'}</span>`;

      const variants = p.variants || [];
      const hasMultipleVariants = variants.length > 1;

      const colorSelectorHtml = hasMultipleVariants ? `
        <div class="card-color-selector">
          <div class="color-dots-group">
            ${variants.map((v, vIdx) => `
              <button type="button" class="color-dot ${vIdx === 0 ? 'active' : ''}" 
                style="background: ${v.color_code || '#d4af37'};" 
                title="${v.color_name}${v.strap_color ? ' — ' + v.strap_color : ''}"
                onclick="Shop.selectCardVariant(${p.id}, ${vIdx}, event)"
                aria-label="${v.color_name}">
              </button>
            `).join('')}
          </div>
          <span class="card-variant-label" id="cardVariantLabel-${p.id}">${variants[0].color_name}</span>
        </div>
      ` : '';

      return `
        <div class="product-card" id="productCard-${p.id}" ${isMasterpiece ? 'style="border: 1px solid rgba(212,175,55,0.4); box-shadow: 0 10px 30px rgba(212,175,55,0.06);"' : ''}>
          <div class="product-card-badges">
            ${styleBadge}
            ${stockBadge}
          </div>

          <button class="product-wishlist-btn" onclick="Shop.toggleWishlist(${p.id}, event)" title="Save to Wishlist">
            ♡
          </button>

          <a href="product.html?id=${p.id}${primaryVariant ? `&variant=${primaryVariant.id}` : ''}" class="product-image-wrap">
            <img src="${imgSrc}" alt="${p.name}" onerror="this.src='./assets/fallback-watch.svg'" loading="lazy">
          </a>

          <div class="product-info">
            <div class="badge-warranty-pill">🛡️ 6-Month Warranty</div>
            ${colorSelectorHtml}
            <p class="product-variant-tag">${primaryVariant && primaryVariant.strap_color ? `${primaryVariant.color_name} • ${primaryVariant.strap_color}` : (p.color || 'Signature Finish')}</p>
            <h3 class="product-title">
              <a href="product.html?id=${p.id}${primaryVariant ? `&variant=${primaryVariant.id}` : ''}">${p.name}</a>
            </h3>

            <div class="product-rating">
              <span>★ ${p.avg_rating || 5.0}</span>
              <span style="color: var(--text-muted);">(${p.review_count || 4} collector reviews)</span>
            </div>

            <div class="product-price-row">
              <span class="product-price">${formatINR(displayPrice)}</span>
              ${originalPrice ? `<span class="product-original-price">${formatINR(originalPrice)}</span>` : ''}
            </div>

            <div class="product-card-actions">
              <button class="gold-btn" onclick="Shop.quickAdd(${p.id}, ${primaryVariant ? primaryVariant.id : 1}, event)">
                Acquire Now
              </button>
              <a href="product.html?id=${p.id}${primaryVariant ? `&variant=${primaryVariant.id}` : ''}" class="dark-btn" style="text-align: center;">
                Discover
              </a>
            </div>
          </div>
        </div>
      `;
    }).join("");
  },

  selectedCardVariants: {},

  selectCardVariant(productId, variantIndex, event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    const product = this.products.find(p => p.id === productId);
    if (!product || !product.variants || !product.variants[variantIndex]) return;
    const variant = product.variants[variantIndex];
    this.selectedCardVariants[productId] = variant;

    const card = document.getElementById(`productCard-${productId}`);
    if (!card) return;

    // Toggle active dot
    const dots = card.querySelectorAll(".color-dot");
    dots.forEach((dot, idx) => {
      dot.classList.toggle("active", idx === variantIndex);
    });

    // Update image with smooth swap
    const img = card.querySelector(".product-image-wrap img");
    if (img) {
      img.classList.add("switching");
      setTimeout(() => {
        let src = variant.image_url || product.main_image || './assets/fallback-watch.svg';
        if (src.startsWith('/')) src = '.' + src;
        img.src = src;
        img.classList.remove("switching");
      }, 120);
    }

    // Update label & tag
    const label = card.querySelector(`#cardVariantLabel-${productId}`);
    if (label) label.textContent = variant.color_name;

    const tag = card.querySelector(".product-variant-tag");
    if (tag) {
      tag.textContent = variant.strap_color 
        ? `${variant.color_name} • ${variant.strap_color}`
        : variant.color_name;
    }

    // Update price if variant has custom pricing
    const priceEl = card.querySelector(".product-price");
    if (priceEl && variant.price) {
      priceEl.textContent = formatINR(variant.price);
    }
    const origPriceEl = card.querySelector(".product-original-price");
    if (origPriceEl) {
      if (variant.discount_price) {
        origPriceEl.textContent = formatINR(variant.discount_price);
        origPriceEl.style.display = "inline";
      } else {
        origPriceEl.style.display = "none";
      }
    }

    // Update Acquire Now button onclick handler
    const buyBtn = card.querySelector(".product-card-actions .gold-btn");
    if (buyBtn) {
      buyBtn.setAttribute("onclick", `Shop.quickAdd(${productId}, ${variant.id}, event)`);
    }

    // Update link targets
    const links = card.querySelectorAll("a[href*='product.html']");
    links.forEach(a => {
      a.href = `product.html?id=${productId}&variant=${variant.id}`;
    });
  },

  async quickAdd(productId, variantId, event) {
    if (event) event.stopPropagation();
    try {
      const targetVariantId = variantId || (this.selectedCardVariants[productId] ? this.selectedCardVariants[productId].id : 1);
      await Cart.addItem(productId, targetVariantId, 1);
      const product = this.products.find(p => p.id === productId);
      const variant = product?.variants?.find(v => v.id === targetVariantId);
      const variantDesc = variant ? ` (${variant.color_name})` : '';
      showToast(`Timepiece added to your cart${variantDesc}`, "success");
    } catch (e) {
      showToast("Could not add timepiece: " + e.message, "error");
    }
  },

  toggleWishlist(productId, event) {
    if (event) event.stopPropagation();
    showToast("Timepiece saved to your private horology wishlist", "success");
  },

  bindFilters() {
    // Search input
    const searchInput = document.getElementById("shopSearch");
    if (searchInput) {
      let timer;
      searchInput.addEventListener("input", (e) => {
        clearTimeout(timer);
        timer = setTimeout(() => {
          this.filters.search = e.target.value.trim();
          this.loadProducts();
        }, 300);
      });
    }

    // Style filter items
    const styleItems = document.querySelectorAll("#styleFilterList .filter-pill-item");
    styleItems.forEach(item => {
      item.addEventListener("click", () => {
        const style = item.dataset.style || "";
        this.setFilterStyle(style);
      });
    });

    // Min & Max Price
    const minInput = document.getElementById("minPrice");
    const maxInput = document.getElementById("maxPrice");
    const onPriceChange = () => {
      this.filters.min_price = minInput ? parseFloat(minInput.value) || 2000 : 2000;
      this.filters.max_price = maxInput ? parseFloat(maxInput.value) || 60000 : 60000;
      this.loadProducts();
    };
    if (minInput) minInput.addEventListener("change", onPriceChange);
    if (maxInput) maxInput.addEventListener("change", onPriceChange);

    // Sorting
    const sortSelect = document.getElementById("shopSort");
    if (sortSelect) {
      sortSelect.addEventListener("change", (e) => {
        this.filters.sort = e.target.value;
        this.loadProducts();
      });
    }
  },

  resetFilters() {
    this.filters = {
      search: "",
      style: "",
      min_price: 2000,
      max_price: 60000,
      availability: "",
      sort: "featured"
    };

    const s = document.getElementById("shopSearch");
    if (s) s.value = "";

    const sortEl = document.getElementById("shopSort");
    if (sortEl) sortEl.value = "featured";

    const minInput = document.getElementById("minPrice");
    if (minInput) minInput.value = 2000;

    const maxInput = document.getElementById("maxPrice");
    if (maxInput) maxInput.value = 60000;

    const availInput = document.getElementById("availFilter");
    if (availInput) availInput.checked = false;

    const styleItems = document.querySelectorAll("#styleFilterList .filter-pill-item");
    styleItems.forEach((i, idx) => i.classList.toggle("active", idx === 0));

    const catCards = document.querySelectorAll(".category-card");
    catCards.forEach((c, idx) => c.classList.toggle("active", idx === 0));

    this.loadProducts();
  }
};

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("productsGrid")) {
    Shop.init();
  }
});
