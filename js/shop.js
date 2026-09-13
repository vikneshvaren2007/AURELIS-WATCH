/* ==========================================================================
   AURELIS — Shop & Catalog Filtering Engine (10 Timepieces Collection)
   ========================================================================== */

const Shop = {
  products: [],
  filters: {
    search: "",
    style: "",
    min_price: 5000,
    max_price: 15000,
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

      return `
        <div class="product-card">
          <div class="product-card-badges">
            <span class="badge-gold">${p.style || 'Artisan Edition'}</span>
            ${stockBadge}
          </div>

          <button class="product-wishlist-btn" onclick="Shop.toggleWishlist(${p.id}, event)" title="Save to Wishlist">
            ♡
          </button>

          <a href="product.html?id=${p.id}" class="product-image-wrap">
            <img src="${imgSrc}" alt="${p.name}" onerror="this.src='./assets/fallback-watch.svg'" loading="lazy">
          </a>

          <div class="product-info">
            <div class="badge-warranty-pill">🛡️ 6-Month Warranty</div>
            <p class="product-variant-tag">${p.color || 'Signature Finish'}</p>
            <h3 class="product-title">
              <a href="product.html?id=${p.id}">${p.name}</a>
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
              <a href="product.html?id=${p.id}" class="dark-btn" style="text-align: center;">
                Discover
              </a>
            </div>
          </div>
        </div>
      `;
    }).join("");
  },

  async quickAdd(productId, variantId, event) {
    if (event) event.stopPropagation();
    try {
      await Cart.addItem(productId, variantId, 1);
      showToast("Timepiece added to your commission cart", "success");
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
      this.filters.min_price = minInput ? parseFloat(minInput.value) || 5000 : 5000;
      this.filters.max_price = maxInput ? parseFloat(maxInput.value) || 15000 : 15000;
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
      min_price: 5000,
      max_price: 15000,
      availability: "",
      sort: "featured"
    };

    const s = document.getElementById("shopSearch");
    if (s) s.value = "";

    const sortEl = document.getElementById("shopSort");
    if (sortEl) sortEl.value = "featured";

    const minInput = document.getElementById("minPrice");
    if (minInput) minInput.value = 5000;

    const maxInput = document.getElementById("maxPrice");
    if (maxInput) maxInput.value = 15000;

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
