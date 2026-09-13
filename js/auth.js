/* ==========================================================================
   AURELIS — User Authentication & Client Profile Management
   ========================================================================== */

const Auth = {
  getUser() {
    const raw = localStorage.getItem("aurelis_user");
    try {
      return raw ? jsonParse(raw) : null;
    } catch {
      return null;
    }
  },

  getToken() {
    return localStorage.getItem("aurelis_auth_token");
  },

  isLoggedIn() {
    return !!this.getToken();
  },

  setAuth(token, user) {
    localStorage.setItem("aurelis_auth_token", token);
    localStorage.setItem("aurelis_user", JSON.stringify(user));
    this.updateNavbar();
    this.mergeGuestCart();
  },

  logout() {
    localStorage.removeItem("aurelis_auth_token");
    localStorage.removeItem("aurelis_user");
    this.updateNavbar();
    showToast("Signed out of your collector profile", "success");
    if (window.location.pathname.includes("account.html") || window.location.pathname.includes("orders.html")) {
      window.location.href = "index.html";
    }
  },

  async mergeGuestCart() {
    const sessionToken = localStorage.getItem("aurelis_session_token");
    if (sessionToken && this.isLoggedIn()) {
      try {
        await apiRequest("/api/cart/merge", {
          method: "POST",
          body: JSON.stringify({ session_token: sessionToken })
        });
        if (window.Cart) Cart.fetchCart();
      } catch (e) {
        console.warn("Cart merge deferred:", e.message);
      }
    }
  },

  updateNavbar() {
    const accountBtn = document.getElementById("navAccountBtn");
    const accountLink = document.getElementById("navAccountLink");
    const navAuth = document.getElementById("navAuthArea");
    const user = this.getUser();

    if (user) {
      if (accountBtn) {
        accountBtn.title = `${user.name} (${user.email})`;
        accountBtn.innerHTML = `
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
        `;
      }
      if (accountLink) {
        accountLink.href = "account.html";
        accountLink.textContent = "My Account";
      }
      if (navAuth) {
        const firstName = user.name.split(" ")[0];
        navAuth.innerHTML = `
          <div style="display: flex; align-items: center; gap: 10px;">
            <a href="account.html" style="color: var(--gold-light); text-decoration: none; font-size: 12px; font-weight: 600; display: flex; align-items: center; gap: 6px;">
              <span>👤</span> <span>${firstName}</span>
            </a>
            <button class="gold-btn-outline" style="padding: 5px 10px; font-size: 9.5px;" onclick="Auth.logout()">Sign Out</button>
          </div>
        `;
      }
      // Update any "Sign In" link in nav-links
      document.querySelectorAll(".nav-links a").forEach(link => {
        if (link.textContent.trim().toLowerCase() === "sign in") {
          link.textContent = "My Account";
          link.href = "account.html";
        }
      });
    }
  }
};

function jsonParse(str) {
  try { return JSON.parse(str); } catch { return null; }
}

document.addEventListener("DOMContentLoaded", () => {
  Auth.updateNavbar();
});
