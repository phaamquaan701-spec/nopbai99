// Chống F12 và DevTools cơ bản trên Frontend
(function() {
  function showWarning() {
    const existing = document.getElementById("anti-inspect-toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.id = "anti-inspect-toast";
    toast.className = "toast-msg show";
    toast.style.background = "#b91c1c";
    toast.textContent = "🛡️ Thao tác này bị khóa để bảo đảm an toàn hệ thống thi/bài tập.";
    document.body.appendChild(toast);

    setTimeout(() => {
      toast.classList.remove("show");
      setTimeout(() => toast.remove(), 300);
    }, 2500);
  }

  // Chặn chuột phải (ngoại trừ trên ảnh hoặc trình xem bài làm để lưu ảnh)
  document.addEventListener("contextmenu", function(e) {
    if (e.target && (e.target.tagName === "IMG" || e.target.closest(".viewer-modal") || e.target.closest(".preview-item") || e.target.closest(".preview-card"))) {
      return true;
    }
    e.preventDefault();
    showWarning();
    return false;
  });

  // Chặn các tổ hợp phím thông dụng
  document.addEventListener("keydown", function(e) {
    // F12
    if (e.key === "F12" || e.keyCode === 123) {
      e.preventDefault();
      showWarning();
      return false;
    }
    // Ctrl + Shift + I / J / C
    if (e.ctrlKey && e.shiftKey && (e.key === "I" || e.key === "i" || e.key === "J" || e.key === "j" || e.key === "C" || e.key === "c")) {
      e.preventDefault();
      showWarning();
      return false;
    }
    // Ctrl + U (View Source)
    if (e.ctrlKey && (e.key === "U" || e.key === "u")) {
      e.preventDefault();
      showWarning();
      return false;
    }
  });
})();
