/**
 * Mobile Image Viewer Component
 * Hỗ trợ cảm ứng đỉnh cao: Pinch-to-zoom, Double-tap, Pan khi zoom, Vuốt trái/phải chuyển ảnh
 */
class MobileImageViewer {
  constructor() {
    this.files = [];
    this.currentIndex = 0;
    this.scale = 1;
    this.panX = 0;
    this.panY = 0;
    this.startX = 0;
    this.startY = 0;
    this.lastTouchDist = 0;
    this.lastTapTime = 0;
    this.isDragging = false;
    this.swipeStartX = 0;
    this.swipeStartY = 0;

    this.createDOM();
    this.bindEvents();
  }

  createDOM() {
    this.modal = document.createElement("div");
    this.modal.className = "viewer-modal";
    this.modal.innerHTML = `
      <div class="viewer-header">
        <div class="viewer-meta">
          <div class="viewer-student-name" id="viewer-student">Tên học sinh</div>
          <div class="viewer-sub-info" id="viewer-info">Thông tin bài nộp</div>
        </div>
        <div class="viewer-header-actions">
          <a class="viewer-action-btn" id="viewer-download" href="#" target="_blank" download="bai_lam.jpg" title="Tải ảnh này về máy">
            ⬇️ Tải ảnh
          </a>
          <button class="viewer-close-btn" id="viewer-close" title="Đóng">&times;</button>
        </div>
      </div>
      <div class="viewer-viewport" id="viewer-viewport">
        <div class="viewer-image-container" id="viewer-container">
          <img class="viewer-image" id="viewer-img" src="" alt="Bài làm học sinh" />
        </div>
      </div>
      <div class="viewer-footer">
        <div class="viewer-counter" id="viewer-counter">Ảnh 1/1</div>
        <div class="viewer-hints">2 ngón phóng to | Chạm đúp 2x | Vuốt chuyển ảnh</div>
        <div class="viewer-nav-buttons">
          <button class="viewer-nav-btn" id="viewer-prev">&#8592;</button>
          <button class="viewer-nav-btn" id="viewer-next">&#8594;</button>
        </div>
      </div>
    `;
    document.body.appendChild(this.modal);

    this.img = this.modal.querySelector("#viewer-img");
    this.container = this.modal.querySelector("#viewer-container");
    this.viewport = this.modal.querySelector("#viewer-viewport");
    this.counter = this.modal.querySelector("#viewer-counter");
    this.studentLabel = this.modal.querySelector("#viewer-student");
    this.infoLabel = this.modal.querySelector("#viewer-info");
    this.btnPrev = this.modal.querySelector("#viewer-prev");
    this.btnNext = this.modal.querySelector("#viewer-next");
    this.btnClose = this.modal.querySelector("#viewer-close");
    this.btnDownload = this.modal.querySelector("#viewer-download");
  }

  open({ files, initialIndex = 0, studentName = "", assignmentTitle = "", submitTime = "" }) {
    if (!files || files.length === 0) return;
    this.files = files;
    this.currentIndex = Math.max(0, Math.min(initialIndex, files.length - 1));
    this.studentName = studentName;
    this.assignmentTitle = assignmentTitle;
    this.submitTime = submitTime;

    this.studentLabel.textContent = studentName || "Bài làm học sinh";
    this.infoLabel.textContent = `${assignmentTitle} • ${submitTime}`;

    this.modal.classList.add("active");
    this.showImage(this.currentIndex);
  }

  close() {
    this.modal.classList.remove("active");
    this.resetZoom();
  }

  showImage(index) {
    this.currentIndex = index;
    this.resetZoom();

    const file = this.files[this.currentIndex];
    const token = localStorage.getItem("access_token");
    let fileUrl = file.url || `/api/files/${file.id}`;
    if (token && !fileUrl.includes("token=")) {
      fileUrl += (fileUrl.includes("?") ? "&" : "?") + `token=${encodeURIComponent(token)}`;
    }
    this.img.src = fileUrl;

    if (this.btnDownload) {
      this.btnDownload.href = fileUrl;
      const safeName = (this.studentName || "bai_lam").replace(/[^a-zA-Z0-9_\u00C0-\u024F\u1E00-\u1EFF]/g, "_");
      const downloadName = file.filename || `${safeName}_anh_${this.currentIndex + 1}.jpg`;
      this.btnDownload.setAttribute("download", downloadName);
    }

    this.counter.textContent = `Ảnh ${this.currentIndex + 1}/${this.files.length}`;
    this.btnPrev.disabled = this.currentIndex === 0;
    this.btnNext.disabled = this.currentIndex === this.files.length - 1;
  }

  prev() {
    if (this.currentIndex > 0) {
      this.showImage(this.currentIndex - 1);
    }
  }

  next() {
    if (this.currentIndex < this.files.length - 1) {
      this.showImage(this.currentIndex + 1);
    }
  }

  resetZoom() {
    this.scale = 1;
    this.panX = 0;
    this.panY = 0;
    this.updateTransform();
  }

  updateTransform() {
    this.container.style.transform = `translate3d(${this.panX}px, ${this.panY}px, 0) scale(${this.scale})`;
  }

  bindEvents() {
    this.btnClose.addEventListener("click", () => this.close());
    this.btnPrev.addEventListener("click", () => this.prev());
    this.btnNext.addEventListener("click", () => this.next());

    // Chặn kéo ghost image mặc định của browser để lướt mượt mà và cho phép click/lưu ảnh
    this.img.addEventListener("dragstart", (e) => e.preventDefault());

    // Phím bấm máy tính
    window.addEventListener("keydown", (e) => {
      if (!this.modal.classList.contains("active")) return;
      if (e.key === "Escape") this.close();
      if (e.key === "ArrowLeft") this.prev();
      if (e.key === "ArrowRight") this.next();
    });

    // Cử chỉ cảm ứng Touch Mobile
    this.viewport.addEventListener("touchstart", (e) => this.handleTouchStart(e), { passive: false });
    this.viewport.addEventListener("touchmove", (e) => this.handleTouchMove(e), { passive: false });
    this.viewport.addEventListener("touchend", (e) => this.handleTouchEnd(e), { passive: false });

    // Hỗ trợ chuột kéo thả trên Desktop
    this.viewport.addEventListener("mousedown", (e) => {
      if (this.scale > 1) {
        this.isDragging = true;
        this.startX = e.clientX - this.panX;
        this.startY = e.clientY - this.panY;
      }
    });
    window.addEventListener("mousemove", (e) => {
      if (this.isDragging && this.scale > 1) {
        this.panX = e.clientX - this.startX;
        this.panY = e.clientY - this.startY;
        this.updateTransform();
      }
    });
    window.addEventListener("mouseup", () => {
      this.isDragging = false;
    });
    this.viewport.addEventListener("dblclick", (e) => {
      if (this.scale > 1) {
        this.resetZoom();
      } else {
        this.scale = 2.5;
        this.updateTransform();
      }
    });
  }

  handleTouchStart(e) {
    if (e.touches.length === 1) {
      const now = Date.now();
      // Double tap to zoom
      if (now - this.lastTapTime < 300) {
        e.preventDefault();
        if (this.scale > 1) {
          this.resetZoom();
        } else {
          this.scale = 2.5;
          this.updateTransform();
        }
        this.lastTapTime = 0;
        return;
      }
      this.lastTapTime = now;

      // 1 ngón chạm
      this.isDragging = true;
      this.swipeStartX = e.touches[0].clientX;
      this.swipeStartY = e.touches[0].clientY;
      this.startX = e.touches[0].clientX - this.panX;
      this.startY = e.touches[0].clientY - this.panY;
    } else if (e.touches.length === 2) {
      // 2 ngón bắt đầu pinch zoom
      e.preventDefault();
      this.isDragging = false;
      this.lastTouchDist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
    }
  }

  handleTouchMove(e) {
    if (e.touches.length === 1 && this.isDragging) {
      if (this.scale > 1) {
        // Pan ảnh khi đã zoom
        e.preventDefault();
        this.panX = e.touches[0].clientX - this.startX;
        this.panY = e.touches[0].clientY - this.startY;
        this.updateTransform();
      }
    } else if (e.touches.length === 2) {
      // Pinch to zoom
      e.preventDefault();
      const dist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      if (this.lastTouchDist > 0) {
        const factor = dist / this.lastTouchDist;
        this.scale = Math.min(Math.max(1, this.scale * factor), 4.5);
        this.updateTransform();
      }
      this.lastTouchDist = dist;
    }
  }

  handleTouchEnd(e) {
    if (e.touches.length === 0) {
      this.isDragging = false;
      this.lastTouchDist = 0;

      // Nếu đang ở mức zoom 1x, kiểm tra cử chỉ swipe chuyển ảnh
      if (this.scale === 1 && e.changedTouches && e.changedTouches.length > 0) {
        const endX = e.changedTouches[0].clientX;
        const endY = e.changedTouches[0].clientY;
        const diffX = endX - this.swipeStartX;
        const diffY = endY - this.swipeStartY;

        // Vuốt ngang nhiều hơn vuốt dọc và khoảng cách > 45px
        if (Math.abs(diffX) > 45 && Math.abs(diffX) > Math.abs(diffY) * 1.5) {
          if (diffX < 0) {
            // Vuốt từ phải sang trái -> Ảnh kế tiếp
            this.next();
          } else {
            // Vuốt từ trái sang phải -> Ảnh trước đó
            this.prev();
          }
        }
      }
    }
  }
}

// Khởi tạo Singleton
window.mobileImageViewer = new MobileImageViewer();
