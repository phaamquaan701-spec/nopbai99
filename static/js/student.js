/**
 * Student Portal Logic
 */
let currentStudent = null;
let currentFilter = "all";
let activeAssignment = null;
let selectedFiles = []; // Mảng chứa File objects { file, previewUrl, id }

document.addEventListener("DOMContentLoaded", async () => {
  await loadStudentProfile();
  await loadDashboard();
  setupFileInput();
});

// Chuyển đổi tab Bottom Nav
function switchTab(tabId) {
  document.querySelectorAll(".view-section").forEach(s => s.style.display = "none");
  document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));

  const targetView = document.getElementById(`view-${tabId}`);
  if (targetView) targetView.style.display = "block";

  // Active button
  const buttons = document.querySelectorAll(".bottom-nav .nav-item");
  const tabIndexes = { home: 0, assignments: 1, submitted: 2, profile: 3 };
  if (buttons[tabIndexes[tabId]]) {
    buttons[tabIndexes[tabId]].classList.add("active");
  }

  if (tabId === "assignments") loadAssignments(currentFilter);
  if (tabId === "submitted") loadSubmittedAssignments();
  if (tabId === "home") loadDashboard();
}

async function loadStudentProfile() {
  try {
    const res = await apiCall("/api/auth/me");
    currentStudent = res.user;
    document.getElementById("welcome-student").textContent = `Xin chào, ${currentStudent.full_name}!`;
    document.getElementById("header-student-class").textContent = currentStudent.class_name || "Lớp";
    document.getElementById("profile-name").textContent = currentStudent.full_name;
    document.getElementById("profile-username").textContent = `@${currentStudent.username}`;
    document.getElementById("profile-class").textContent = currentStudent.class_name || "Chưa xếp lớp";
  } catch (err) {
    console.error(err);
  }
}

async function loadDashboard() {
  try {
    const res = await apiCall("/api/student/dashboard");
    const stats = res.stats;
    document.getElementById("stat-need-action").textContent = stats.need_action;
    document.getElementById("stat-submitted").textContent = stats.submitted;
    document.getElementById("stat-unsubmitted").textContent = stats.unsubmitted;
    document.getElementById("stat-total").textContent = stats.total;

    const listContainer = document.getElementById("home-upcoming-list");
    if (!res.upcoming_assignments || res.upcoming_assignments.length === 0) {
      listContainer.innerHTML = `
        <div class="card" style="text-align: center; padding: 24px; color: var(--gray-600);">
          🎉 Tuyệt vời! Bạn không còn bài tập nào cần hoàn thành ngay lúc này.
        </div>
      `;
      return;
    }

    listContainer.innerHTML = res.upcoming_assignments.map(a => renderAssignmentCard(a, true)).join("");
  } catch (err) {
    console.error(err);
  }
}

function setAssignmentFilter(filter, el) {
  currentFilter = filter;
  document.querySelectorAll(".filter-pill").forEach(p => p.classList.remove("active"));
  if (el) el.classList.add("active");
  loadAssignments(filter);
}

async function loadAssignments(filter = "all") {
  const container = document.getElementById("assignment-list");
  container.innerHTML = `<div style="text-align: center; padding: 20px; color: var(--gray-600);">Đang tải bài tập...</div>`;

  try {
    const res = await apiCall(`/api/student/assignments?filter=${filter}`);
    if (res.assignments.length === 0) {
      container.innerHTML = `
        <div class="card" style="text-align: center; padding: 32px; color: var(--gray-600);">
          Không có bài tập nào trong mục này.
        </div>
      `;
      return;
    }
    container.innerHTML = res.assignments.map(a => renderAssignmentCard(a)).join("");
  } catch (err) {
    showToast(err.message, true);
  }
}

async function loadSubmittedAssignments() {
  const container = document.getElementById("submitted-list");
  container.innerHTML = `<div style="text-align: center; padding: 20px; color: var(--gray-600);">Đang tải...</div>`;

  try {
    const res = await apiCall("/api/student/assignments?filter=submitted");
    if (res.assignments.length === 0) {
      container.innerHTML = `
        <div class="card" style="text-align: center; padding: 32px; color: var(--gray-600);">
          Bạn chưa nộp bài tập nào.
        </div>
      `;
      return;
    }

    container.innerHTML = res.assignments.map(a => `
      <div class="card">
        <div class="card-header">
          <div>
            <div style="font-size: 0.8rem; font-weight: 700; color: var(--primary);">${a.subject}</div>
            <h4 class="card-title">${a.title}</h4>
          </div>
          <span class="badge ${a.status_info.status_badge_class}">${a.status_info.status_label}</span>
        </div>
        <div class="card-meta">
          <div>📅 Hạn nộp: ${formatDatetimeVN(a.deadline)}</div>
          <div>ℹ️ ${a.status_info.time_info}</div>
        </div>
        <div style="display: flex; gap: 8px; margin-top: 10px;">
          <button class="btn btn-outline btn-sm" onclick="viewMySubmission(${a.id})" style="flex: 1;">
            🔍 Xem bài đã nộp
          </button>
          ${a.status_info.can_submit ? `
            <button class="btn btn-primary btn-sm" onclick="openSubmitModal(${a.id})" style="flex: 1;">
              🔄 Nộp lại bài
            </button>
          ` : ""}
        </div>
      </div>
    `).join("");
  } catch (err) {
    showToast(err.message, true);
  }
}

function renderAssignmentCard(a, isCompact = false) {
  const st = a.status_info;
  return `
    <div class="card">
      <div class="card-header">
        <div>
          <span style="font-size: 0.78rem; font-weight: 700; color: var(--primary); text-transform: uppercase;">${a.subject}</span>
          <h4 class="card-title" style="margin-top: 2px;">${a.title}</h4>
        </div>
        <span class="badge ${st.status_badge_class}">${st.status_label}</span>
      </div>
      
      <p class="card-subtitle" style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
        ${a.description || "Không có mô tả chi tiết."}
      </p>

      <div class="card-meta">
        <div>⏳ ${st.time_info}</div>
        <div>📅 Hạn: ${formatDatetimeVN(a.deadline)}</div>
      </div>

      ${st.warning_badge ? `<div class="warning-callout">${st.warning_badge}</div>` : ""}

      <div style="display: flex; gap: 8px; margin-top: 12px;">
        ${st.can_submit ? `
          <button class="btn btn-primary btn-sm" onclick="openSubmitModal(${a.id})" style="flex: 1;">
            ${st.is_submitted ? "🔄 Nộp lại bài" : "📤 Nộp bài ngay"}
          </button>
        ` : `
          <button class="btn btn-outline btn-sm" disabled style="flex: 1; opacity: 0.6;">
            ⛔ Không thể nộp
          </button>
        `}
        ${st.is_submitted ? `
          <button class="btn btn-outline btn-sm" onclick="viewMySubmission(${a.id})" style="flex: 1;">
            👁️ Xem bài đã nộp
          </button>
        ` : ""}
      </div>
    </div>
  `;
}

// Xử lý nộp bài & Chọn ảnh
async function openSubmitModal(assignmentId) {
  try {
    const res = await apiCall(`/api/student/assignments/${assignmentId}`);
    activeAssignment = res.assignment;

    document.getElementById("submit-modal-title").textContent = activeAssignment.title;
    document.getElementById("submit-subject").textContent = activeAssignment.subject;
    document.getElementById("submit-description").textContent = activeAssignment.description || "Không có mô tả";
    document.getElementById("submit-deadline-text").textContent = `Hạn nộp: ${formatDatetimeVN(activeAssignment.deadline)} • ${activeAssignment.status_info.time_info}`;

    const warningBox = document.getElementById("submit-warning-box");
    if (activeAssignment.status_info.warning_badge) {
      warningBox.innerHTML = `<div class="warning-callout">${activeAssignment.status_info.warning_badge}</div>`;
    } else {
      warningBox.innerHTML = "";
    }

    // Reset danh sách ảnh đã chọn
    selectedFiles = [];
    renderPreviews();

    // Ẩn thanh upload progress
    document.getElementById("upload-progress-box").style.display = "none";
    document.getElementById("btn-do-submit").disabled = false;
    document.getElementById("btn-do-submit").textContent = activeAssignment.status_info.is_submitted ? "Xác nhận nộp lại bài" : "Nộp bài ngay";

    document.getElementById("submit-modal").classList.add("show");
  } catch (err) {
    showToast(err.message, true);
  }
}

function closeSubmitModal() {
  document.getElementById("submit-modal").classList.remove("show");
}

function setupFileInput() {
  const fileInput = document.getElementById("file-input");
  fileInput.addEventListener("change", (e) => {
    const files = Array.from(e.target.files);
    if (!files || files.length === 0) return;

    const maxAllowed = activeAssignment ? activeAssignment.max_images : 10;
    if (selectedFiles.length + files.length > maxAllowed) {
      showToast(`Tối đa ${maxAllowed} ảnh mỗi bài tập. Vui lòng chọn lại.`, true);
      return;
    }

    files.forEach(file => {
      // Đọc preview
      const reader = new FileReader();
      reader.onload = (event) => {
        selectedFiles.push({
          id: Math.random().toString(36).substring(2, 9),
          file: file,
          name: file.name,
          size: file.size,
          previewUrl: event.target.result
        });
        renderPreviews();
      };
      reader.readAsDataURL(file);
    });

    // Reset input để có thể chọn tiếp
    fileInput.value = "";
  });
}

function renderPreviews() {
  const grid = document.getElementById("preview-grid");
  const summary = document.getElementById("selected-summary");
  const countLabel = document.getElementById("selected-count-label");
  const sizeLabel = document.getElementById("selected-size-label");

  if (selectedFiles.length === 0) {
    grid.innerHTML = "";
    summary.style.display = "none";
    return;
  }

  summary.style.display = "flex";
  countLabel.textContent = `Đã chọn: ${selectedFiles.length} ảnh`;
  const totalBytes = selectedFiles.reduce((acc, f) => acc + f.size, 0);
  sizeLabel.textContent = formatFileSize(totalBytes);

  grid.innerHTML = selectedFiles.map((item, idx) => `
    <div class="preview-item">
      <img src="${item.previewUrl}" class="preview-img" alt="Ảnh ${idx+1}" onclick="previewSingle('${item.previewUrl}')" />
      <button type="button" class="btn-icon btn-del" onclick="removeFile(${idx})">&times;</button>
      <div class="preview-info">
        <span>Trang ${idx + 1} (${formatFileSize(item.size)})</span>
        <div class="preview-actions">
          ${idx > 0 ? `<button type="button" class="btn-icon" style="background:#475569;" onclick="moveFile(${idx}, -1)">▲</button>` : ""}
          ${idx < selectedFiles.length - 1 ? `<button type="button" class="btn-icon" style="background:#475569;" onclick="moveFile(${idx}, 1)">▼</button>` : ""}
        </div>
      </div>
    </div>
  `).join("");
}

function removeFile(index) {
  selectedFiles.splice(index, 1);
  renderPreviews();
}

function moveFile(index, direction) {
  const newIndex = index + direction;
  if (newIndex < 0 || newIndex >= selectedFiles.length) return;
  const temp = selectedFiles[index];
  selectedFiles[index] = selectedFiles[newIndex];
  selectedFiles[newIndex] = temp;
  renderPreviews();
}

function previewSingle(url) {
  window.mobileImageViewer.open({
    files: [{ url }],
    studentName: currentStudent ? currentStudent.full_name : "",
    assignmentTitle: "Xem trước ảnh đã chọn"
  });
}

// Xác nhận và upload nộp bài
async function confirmAndSubmit() {
  if (selectedFiles.length === 0) {
    showToast("Vui lòng chọn ít nhất 1 ảnh bài làm!", true);
    return;
  }

  const confirmed = confirm("Bạn có chắc chắn muốn nộp bài làm này không?");
  if (!confirmed) return;

  const btn = document.getElementById("btn-do-submit");
  const progressBox = document.getElementById("upload-progress-box");
  const progressBar = document.getElementById("upload-progress-bar");
  const statusText = document.getElementById("upload-status-text");
  const percentText = document.getElementById("upload-percent-text");

  btn.disabled = true;
  progressBox.style.display = "block";
  progressBar.style.width = "0%";
  statusText.textContent = `Đang tải ${selectedFiles.length} ảnh lên...`;
  percentText.textContent = "0%";

  const formData = new FormData();
  selectedFiles.forEach((item) => {
    formData.append("files", item.file, item.name);
  });

  // Sử dụng XMLHttpRequest để lắng nghe onprogress upload chính xác
  const xhr = new XMLHttpRequest();
  xhr.open("POST", `/api/student/assignments/${activeAssignment.id}/submit`);
  
  const token = localStorage.getItem("access_token");
  if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
  xhr.withCredentials = true;

  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) {
      const pct = Math.round((e.loaded / e.total) * 100);
      progressBar.style.width = pct + "%";
      percentText.textContent = pct + "%";
      statusText.textContent = `Đang tải lên (${pct}%)...`;
    }
  };

  xhr.onload = () => {
    if (xhr.status >= 200 && xhr.status < 300) {
      const res = JSON.parse(xhr.responseText);
      showToast(res.is_late ? "⚠️ Nộp bài thành công (Ghi nhận nộp muộn)!" : "✅ Nộp bài đúng hạn thành công!");
      closeSubmitModal();
      loadDashboard();
      if (currentFilter !== "all") loadAssignments(currentFilter);
    } else {
      let errDetail = "Nộp bài thất bại.";
      try {
        const errJson = JSON.parse(xhr.responseText);
        errDetail = errJson.detail || errDetail;
      } catch (e) {}
      showToast(errDetail, true);
      btn.disabled = false;
      progressBox.style.display = "none";
      // Giữ nguyên danh sách ảnh đã chọn để học sinh không phải chọn lại từ đầu (Mục 10)
    }
  };

  xhr.onerror = () => {
    showToast("Lỗi kết nối mạng khi tải ảnh lên. Danh sách ảnh vẫn được giữ nguyên để thử lại.", true);
    btn.disabled = false;
    progressBox.style.display = "none";
  };

  xhr.send(formData);
}

// Xem lại bài nộp của học sinh
async function viewMySubmission(assignmentId) {
  try {
    const res = await apiCall(`/api/student/assignments/${assignmentId}`);
    const a = res.assignment;
    if (!a.latest_submission || !a.latest_submission.files || a.latest_submission.files.length === 0) {
      showToast("Chưa có ảnh bài làm nào được ghi nhận.", true);
      return;
    }

    const files = a.latest_submission.files.map(f => ({
      id: f.id,
      url: `/api/files/${f.id}`
    }));

    window.mobileImageViewer.open({
      files: files,
      studentName: currentStudent ? currentStudent.full_name : "",
      assignmentTitle: a.title,
      submitTime: formatDatetimeVN(a.latest_submission.submitted_at)
    });
  } catch (err) {
    showToast(err.message, true);
  }
}
