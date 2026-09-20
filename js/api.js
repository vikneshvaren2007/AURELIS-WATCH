/* ==========================================================================
   AURELIS — Unified API Client & Toast Notification System
   ========================================================================== */

function getApiBase() {
  if (window.AURELIS_API_BASE) return window.AURELIS_API_BASE;
  const origin = window.location.origin || "";
  const port = window.location.port || "";
  const protocol = window.location.protocol || "";
  // If running via file:// protocol
  if (protocol === "file:" || !origin || origin === "null") {
    return "http://127.0.0.1:5000";
  }
  // If running via Live Server (typically port 5500 or any non-5000 local port)
  if (origin.includes("localhost") || origin.includes("127.0.0.1")) {
    if (port && port !== "5000") {
      return "http://127.0.0.1:5000";
    }
    return origin;
  }
  // If accessed by local LAN IP (e.g. 192.168.x.x on non-5000 port)
  if (/^https?:\/\/\d+\.\d+\.\d+\.\d+/.test(origin)) {
    if (port && port !== "5000") {
      return origin.replace(`:${port}`, ":5000");
    }
    return origin;
  }
  return origin || "";
}

const API_BASE = getApiBase();

function getSessionToken() {
  let token = localStorage.getItem("aurelis_session_token");
  if (!token) {
    token = "sess_" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    localStorage.setItem("aurelis_session_token", token);
  }
  return token;
}

function getAuthToken() {
  return localStorage.getItem("aurelis_auth_token") || "";
}

function getAdminToken() {
  return localStorage.getItem("aurelis_admin_token") || "";
}

async function apiRequest(endpoint, options = {}, extraBody = null) {
  // Support both apiRequest(url, { method: "POST", body: JSON.stringify(data) })
  // and apiRequest(url, "POST", data)
  if (typeof options === "string") {
    const method = options.toUpperCase();
    const opts = { method };
    if (extraBody !== null && extraBody !== undefined) {
      if (typeof extraBody === "object" && !(extraBody instanceof FormData)) {
        opts.body = JSON.stringify(extraBody);
      } else {
        opts.body = extraBody;
      }
    }
    options = opts;
  }

  const url = `${API_BASE}${endpoint}`;
  const headers = options.headers || {};

  if (!headers["Content-Type"] && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  // Inject session token for guest cart tracking
  headers["X-Session-Token"] = getSessionToken();

  // Inject user or admin token
  const token = endpoint.startsWith("/api/admin") ? getAdminToken() : getAuthToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  options.headers = headers;

  try {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const errorMsg = data.error || data.message || `Request failed with status ${response.status}`;
      throw new Error(errorMsg);
    }
    return data;
  } catch (error) {
    console.error(`[API Error: ${endpoint}]`, error.message);
    throw error;
  }
}

function showToast(message, type = "success") {
  let container = document.getElementById("toastContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "toastContainer";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${type === "success" ? "✓" : "⚠"}</span>
    <span class="toast-msg">${message}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    setTimeout(() => toast.remove(), 350);
  }, 4000);
}

// Global Currency Formatter
function formatINR(amount) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0
  }).format(amount || 0);
}

/* ==========================================================================
   AURELIS — Universal Mobile Navigation Controller
   Ensures hamburger toggle, outside-click close, ESC dismiss, and active states
   work seamlessly across all pages without duplicate event listeners.
   ========================================================================== */
function initAurelisMobileNav() {
  const nav = document.querySelector(".nav") || document.getElementById("mainNav");
  if (!nav) return;

  const navLinks = nav.querySelector(".nav-links") || document.getElementById("navLinks");
  if (!navLinks) return;

  let mobileBtn = nav.querySelector(".mobile-toggle") || document.getElementById("mobileMenuBtn");
  if (!mobileBtn) {
    mobileBtn = document.createElement("button");
    mobileBtn.className = "mobile-toggle";
    mobileBtn.id = "mobileMenuBtn";
    mobileBtn.setAttribute("aria-label", "Toggle Navigation");
    mobileBtn.setAttribute("aria-expanded", "false");
    mobileBtn.innerHTML = `
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="3" y1="6" x2="21" y2="6"></line>
        <line x1="3" y1="12" x2="21" y2="12"></line>
        <line x1="3" y1="18" x2="21" y2="18"></line>
      </svg>
    `;
    const actions = nav.querySelector(".nav-actions");
    if (actions) {
      actions.appendChild(mobileBtn);
    } else {
      nav.appendChild(mobileBtn);
    }
  }

  // Replace button with clean clone to strip any conflicting/duplicate inline listeners
  const freshBtn = mobileBtn.cloneNode(true);
  if (mobileBtn.parentNode) {
    mobileBtn.parentNode.replaceChild(freshBtn, mobileBtn);
    mobileBtn = freshBtn;
  }
  mobileBtn._hasAurelisNavListener = true;

  function openMenu() {
    navLinks.classList.add("open");
    mobileBtn.classList.add("active");
    mobileBtn.setAttribute("aria-expanded", "true");
    document.body.style.overflow = "hidden";
  }

  function closeMenu() {
    navLinks.classList.remove("open");
    mobileBtn.classList.remove("active");
    mobileBtn.setAttribute("aria-expanded", "false");
    document.body.style.overflow = "";
  }

  mobileBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (navLinks.classList.contains("open")) {
      closeMenu();
    } else {
      openMenu();
    }
  });

  navLinks.querySelectorAll("a").forEach(link => {
    link.addEventListener("click", () => {
      closeMenu();
    });
  });

  document.addEventListener("click", (e) => {
    if (navLinks.classList.contains("open") && !navLinks.contains(e.target) && !mobileBtn.contains(e.target)) {
      closeMenu();
    }
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && navLinks.classList.contains("open")) {
      closeMenu();
    }
  });

  try {
    const currentPath = window.location.pathname.split("/").pop() || "index.html";
    navLinks.querySelectorAll("a").forEach(a => {
      const href = a.getAttribute("href") || "";
      if (href === currentPath || (currentPath === "" && href === "index.html")) {
        a.classList.add("active");
      }
    });
  } catch (err) {}
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initAurelisMobileNav);
} else {
  initAurelisMobileNav();
}
