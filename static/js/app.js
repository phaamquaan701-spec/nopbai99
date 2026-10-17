/**
 * Core Application Utilities & API Client
 */
async function apiCall(url, options = {}) {
  const defaultHeaders = {};
  if (!(options.body instanceof FormData)) {
    defaultHeaders["Content-Type"] = "application/json";
  }

  const token = localStorage.getItem("access_token");
  if (token) {
    defaultHeaders["Authorization"] = `Bearer ${token}`;
  }

  options.headers = {
    ...defaultHeaders,
    ...options.headers
  };
  options.credentials = "include";

  try {
    const res = await fetch(url, options);
    if (res.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user_info");
      if (!window.location.pathname.endsWith("/") && !window.location.pathname.endsWith("index.html")) {
        window.location.href = "/";
      }
      throw new Error("Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.");
    }
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Đã xảy ra lỗi từ máy chủ.");
    }
    return data;
  } catch (err) {
    console.error("API Error:", err);
    throw err;
  }
}

function showToast(message, isError = false) {
  const existing = document.querySelector(".toast-msg");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.className = "toast-msg show";
  if (isError) {
    toast.style.background = "#dc2626";
  }
  toast.innerHTML = `<span>${isError ? "⚠️" : "✅"}</span> <span>${message}</span>`;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function formatDatetimeVN(isoStr) {
  if (!isoStr) return "";
  const d = new Date(isoStr);
  const hours = String(d.getHours()).padStart(2, "0");
  const mins = String(d.getMinutes()).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const year = d.getFullYear();
  return `${hours}:${mins} • ${day}/${month}/${year}`;
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

async function handleLogout() {
  try {
    await apiCall("/api/auth/logout", { method: "POST" });
  } catch (e) {}
  localStorage.removeItem("access_token");
  localStorage.removeItem("user_info");
  window.location.href = "/";
}
