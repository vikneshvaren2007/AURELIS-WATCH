/* ==========================================================================
   AURELIS — Unified API Client & Toast Notification System
   ========================================================================== */

function getApiBase() {
  if (window.AURELIS_API_BASE) return window.AURELIS_API_BASE;
  const origin = window.location.origin || "";
  const port = window.location.port || "";
  // If running via Live Server (typically port 5500 or any non-5000 local port)
  if (origin.includes("localhost") || origin.includes("127.0.0.1")) {
    if (port && port !== "5000") {
      return "http://127.0.0.1:5000";
    }
    return origin;
  }
  return "";
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

async function apiRequest(endpoint, options = {}) {
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
