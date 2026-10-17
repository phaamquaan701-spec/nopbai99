/**
 * Admin Portal Logic
 */
let adminInfo = null;
let allClasses = [];
let allAdminAssignments = [];
let trackingData = null;
let currentTrackingFilter = "all";
let currentAssignmentClassFilter = "all";

document.addEventListener("DOMContentLoaded", async () => {
  await loadAdminProfile();
  await loadAdminDashboard();
  await loadClasses();
  await loadAdminAssignments();
});

// Chuyển Tab Bottom Nav
function switchAdminTab(tabId) {
  document.querySelectorAll(".admin-section").forEach(s => s.style.display = "none");
  document.querySelectorAll(".bottom-nav .nav-item").forEach(b => b.classList.remove("active"));

  const targetView = document.getElementById(`admin-view-${tabId}`);
  if (targetView) targetView.style.display = "block";

  const buttons = document.querySelectorAll(".bottom-nav .nav-item");
  const tabIndexes = { dashboard: 0, assignments: 1, classes: 2, tracking: 3, settings: 4 };
  if (buttons[tabIndexes[tabId]]) {
    buttons[tabIndexes[tabId]].classList.add("active");
  }

  if (tabId === "dashboard") loadAdminDashboard();
  if (tabId === "assignments") loadAdminAssignments();
  if (tabId === "classes") { loadClasses(); loadStudents(); }
  if (tabId === "tracking") setupTrackingDropdown();
}

async function loadAdminProfile() {
  try {
    const res = await apiCall("/api/auth/me");
    adminInfo = res.user;
    if (adminInfo.role !== "admin") {
      window.location.href = "/student";
      return;
    }
    document.getElementById("admin-name-title").textContent = `Xin chào, ${adminInfo.full_name}!`;
    document.getElementById("admin-profile-name").textContent = `${adminInfo.full_name} (@${adminInfo.username})`;
  } catch (err) {
    console.error(err);
  }
}

// 1. Dashboard
async function loadAdminDashboard() {
  try {
    const res = await apiCall("/api/admin/dashboard");
    const stats = res.stats;
    document.getElementById("admin-stat-classes").textContent = stats.total_classes;
    document.getElementById("admin-stat-students").textContent = stats.total_students;
    document.getElementById("admin-stat-assignments").textContent = stats.total_assignments;
    document.getElementById("admin-stat-submissions").textContent = stats.total_submissions;

    const upcomingDiv = document.getElementById("admin-upcoming-assignments");
    if (!res.upcoming_assignments || res.upcoming_assignments.length === 0) {
      upcomingDiv.innerHTML = `<div class="card" style="text-align:center; color:var(--gray-600); padding:20px;">Không có bài tập nào sắp hết hạn trong 24 giờ tới.</div>`;
      return;
    }

    upcomingDiv.innerHTML = res.upcoming_assignments.map(a => `
      <div class="card">
        <div class="card-header">
          <div>
            <span style="font-size:0.75rem; font-weight:700; color:var(--primary);">${a.subject} • Lớp ${a.class_name}</span>
            <h4 class="card-title">${a.title}</h4>
          </div>
          <span class="badge badge-warning">Sắp hết hạn</span>
        </div>
        <div class="card-meta">
          <div>📅 Hạn nộp: ${formatDatetimeVN(a.deadline)}</div>
        </div>
        <button class="btn btn-outline btn-sm" onclick="goToTracking(${a.id})" style="margin-top:8px;">
          📊 Theo dõi nộp bài
        </button>
      </div>
    `).join("");
  } catch (err) {
    console.error(err);
  }
}

// 2. Classes & Students
async function loadClasses() {
  try {
    const res = await apiCall("/api/admin/classes");
    allClasses = res.classes;

    const chips = document.getElementById("admin-classes-chips");
    if (chips) {
      chips.innerHTML = allClasses.map(c => `
        <span class="badge badge-gray" style="font-size:0.85rem; padding:6px 12px; border-radius:20px;">
          🏫 ${c.name} (${c.student_count} học sinh)
        </span>
      `).join("");
    }

    // 1. Dropdowns
    const assignClassSelect = document.getElementById("assign-class");
    if (assignClassSelect) {
      assignClassSelect.innerHTML = allClasses.map(c => `<option value="${c.id}">Lớp ${c.name} (${c.student_count} học sinh)</option>`).join("");
    }
    const studentClassSelect = document.getElementById("new-student-class");
    if (studentClassSelect) {
      studentClassSelect.innerHTML = allClasses.map(c => `<option value="${c.id}">${c.name}</option>`).join("");
    }

    // 2. Multi-class Checkboxes cho Modal tạo bài tập
    renderAssignClassCheckboxes();

    // 3. Thanh nút lọc theo lớp cho Tab Quản lý bài tập
    renderAssignmentClassFilters();
  } catch (err) {
    console.error(err);
  }
}

function renderAssignClassCheckboxes() {
  const container = document.getElementById("assign-classes-list");
  if (!container) return;
  if (!allClasses || allClasses.length === 0) {
    container.innerHTML = `<div style="font-size:0.8rem; color:var(--gray-500); padding:4px;">Chưa có lớp học nào.</div>`;
    return;
  }
  container.innerHTML = allClasses.map(c => `
    <label style="display:flex; align-items:center; gap:8px; padding:6px 10px; background:#fff; border-radius:6px; cursor:pointer; border:1px solid #e2e8f0; font-size:0.88rem;">
      <input type="checkbox" class="assign-class-checkbox" value="${c.id}" checked style="width:17px; height:17px; accent-color:var(--primary);">
      <span style="font-weight:700; color:var(--gray-800);">🏫 Lớp ${c.name}</span>
      <span style="font-size:0.75rem; color:var(--gray-500); margin-left:auto;">(${c.student_count || 0} học sinh)</span>
    </label>
  `).join("");
}

function selectAllAssignClasses(checkAll) {
  document.querySelectorAll(".assign-class-checkbox").forEach(cb => {
    cb.checked = checkAll;
  });
}

function renderAssignmentClassFilters() {
  const container = document.getElementById("assignment-class-filters");
  if (!container) return;

  const totalCount = allAdminAssignments ? allAdminAssignments.length : 0;
  let html = `<button class="filter-pill ${currentAssignmentClassFilter === 'all' ? 'active' : ''}" onclick="setAssignmentClassFilter('all', this)">Tất cả (${totalCount})</button>`;

  if (allClasses) {
    allClasses.forEach(c => {
      const count = allAdminAssignments ? allAdminAssignments.filter(a => a.class_id === c.id).length : 0;
      const isActive = String(currentAssignmentClassFilter) === String(c.id);
      html += `<button class="filter-pill ${isActive ? 'active' : ''}" onclick="setAssignmentClassFilter(${c.id}, this)">Lớp ${c.name} (${count})</button>`;
    });
  }

  container.innerHTML = html;
}

function setAssignmentClassFilter(classId, btn) {
  currentAssignmentClassFilter = classId;
  document.querySelectorAll("#assignment-class-filters .filter-pill").forEach(p => p.classList.remove("active"));
  if (btn) btn.classList.add("active");
  renderAdminAssignmentsList();
}

async function loadStudents(search = "") {
  const container = document.getElementById("admin-students-list");
  try {
    const url = search ? `/api/admin/students?search=${encodeURIComponent(search)}` : "/api/admin/students";
    const res = await apiCall(url);
    if (res.students.length === 0) {
      container.innerHTML = `<div class="card" style="text-align:center; padding:20px; color:var(--gray-600);">Không có học sinh nào.</div>`;
      return;
    }

    container.innerHTML = res.students.map(s => `
      <div class="card">
        <div class="card-header">
          <div>
            <h4 class="card-title">${s.full_name}</h4>
            <div style="font-size:0.82rem; color:var(--gray-600);">@${s.username} • Lớp: <b>${s.class_name || "Chưa gán"}</b></div>
          </div>
          <span class="badge ${s.status === 'active' ? 'badge-success' : 'badge-danger'}">
            ${s.status === 'active' ? 'Hoạt động' : 'Bị khóa'}
          </span>
        </div>
        <div style="display:flex; gap:6px; margin-top:10px;">
          <button class="btn btn-outline btn-sm" onclick="promptChangePassword(${s.id}, '${s.full_name}')" style="flex:1;">
            🔑 Đổi MK
          </button>
          <button class="btn btn-outline btn-sm" onclick="toggleStudentLock(${s.id}, '${s.status}', '${s.full_name}', ${s.class_id})" style="flex:1;">
            ${s.status === 'active' ? '🔒 Khóa' : '🔓 Mở khóa'}
          </button>
        </div>
      </div>
    `).join("");
  } catch (err) {
    showToast(err.message, true);
  }
}

let studentSearchTimeout = null;
function onStudentSearchChange() {
  clearTimeout(studentSearchTimeout);
  studentSearchTimeout = setTimeout(() => {
    const val = document.getElementById("student-search-input").value.trim();
    loadStudents(val);
  }, 300);
}

function openAddClassModal() {
  document.getElementById("class-modal").classList.add("show");
}
function closeClassModal() {
  document.getElementById("class-modal").classList.remove("show");
}
async function handleCreateClass(e) {
  e.preventDefault();
  const name = document.getElementById("new-class-name").value.trim();
  try {
    await apiCall("/api/admin/classes", {
      method: "POST",
      body: JSON.stringify({ name })
    });
    showToast("Đã tạo lớp học thành công!");
    closeClassModal();
    document.getElementById("new-class-name").value = "";
    await loadClasses();
  } catch (err) {
    showToast(err.message, true);
  }
}

function openAddStudentModal() {
  document.getElementById("student-modal").classList.add("show");
}
function closeStudentModal() {
  document.getElementById("student-modal").classList.remove("show");
}
async function handleCreateStudent(e) {
  e.preventDefault();
  const full_name = document.getElementById("new-student-name").value.trim();
  const username = document.getElementById("new-student-username").value.trim();
  const password = document.getElementById("new-student-pwd").value;
  const class_id = parseInt(document.getElementById("new-student-class").value);

  try {
    await apiCall("/api/admin/students", {
      method: "POST",
      body: JSON.stringify({ full_name, username, password, class_id })
    });
    showToast("Đã tạo học sinh thành công!");
    closeStudentModal();
    document.getElementById("new-student-name").value = "";
    document.getElementById("new-student-username").value = "";
    loadStudents();
    loadClasses();
  } catch (err) {
    showToast(err.message, true);
  }
}

async function promptChangePassword(studentId, studentName) {
  const newPwd = prompt(`Nhập mật khẩu mới cho học sinh ${studentName}:`, "123456");
  if (!newPwd) return;
  try {
    await apiCall(`/api/admin/students/${studentId}/password`, {
      method: "PUT",
      body: JSON.stringify({ new_password: newPwd })
    });
    showToast("Đổi mật khẩu thành công!");
  } catch (err) {
    showToast(err.message, true);
  }
}

async function toggleStudentLock(studentId, currentStatus, studentName, classId) {
  const newStatus = currentStatus === "active" ? "locked" : "active";
  const actionText = newStatus === "locked" ? "khóa" : "mở khóa";
  if (!confirm(`Bạn có chắc chắn muốn ${actionText} tài khoản của ${studentName}?`)) return;

  try {
    await apiCall(`/api/admin/students/${studentId}`, {
      method: "PUT",
      body: JSON.stringify({ full_name: studentName, class_id: classId, status: newStatus })
    });
    showToast(`Đã ${actionText} tài khoản thành công!`);
    loadStudents();
  } catch (err) {
    showToast(err.message, true);
  }
}

// 3. Quản lý Bài tập (Assignments)
async function loadAdminAssignments() {
  try {
    const res = await apiCall("/api/admin/assignments");
    allAdminAssignments = res.assignments;
    renderAssignmentClassFilters();
    renderAdminAssignmentsList();
    renderDashboardZipList();
  } catch (err) {
    showToast(err.message, true);
  }
}

function renderAdminAssignmentsList() {
  const container = document.getElementById("admin-assignments-list");
  if (!container) return;

  let list = allAdminAssignments;
  if (currentAssignmentClassFilter !== "all") {
    list = list.filter(a => a.class_id === currentAssignmentClassFilter);
  }

  if (list.length === 0) {
    container.innerHTML = `<div class="card" style="text-align:center; padding:24px; color:var(--gray-600);">Không có bài tập nào trong lựa chọn này. Hãy nhấn "+ Tạo bài tập" để giao bài.</div>`;
    return;
  }

  container.innerHTML = list.map(a => `
    <div class="card">
      <div class="card-header">
        <div>
          <div style="display:flex; align-items:center; gap:6px; margin-bottom:4px; flex-wrap:wrap;">
            <span class="badge" style="background:#e0e7ff; color:#3730a3; font-weight:800; font-size:0.75rem;">🏫 Lớp ${a.class_name}</span>
            <span style="font-size:0.75rem; font-weight:700; color:var(--primary); text-transform:uppercase;">${a.subject}</span>
          </div>
          <h4 class="card-title">${a.title}</h4>
        </div>
        <span class="badge ${a.status === 'open' ? 'badge-success' : 'badge-locked'}">
          ${a.status === 'open' ? 'Đang mở' : 'Đã đóng'}
        </span>
      </div>
      <p class="card-subtitle">${a.description || "Không có mô tả"}</p>
      <div class="card-meta">
        <div>📅 Hạn: ${formatDatetimeVN(a.deadline)}</div>
        <div>📊 Đã nộp: <b>${a.submitted_count} / ${a.total_students}</b> học sinh</div>
      </div>
      <div style="margin-top:10px;">
        <button class="btn btn-sm" onclick="downloadAssignmentZipById(${a.id})" style="width:100%; background:#059669; color:#fff; font-weight:700; padding:8px 12px; border-radius:8px; border:none; display:flex; align-items:center; justify-content:center; gap:6px; cursor:pointer;" title="Xuất toàn bộ ảnh học sinh đã nộp cho bài tập này thành 1 file ZIP">
          📦 Xuất tất cả ảnh của task này (.ZIP)
        </button>
      </div>
      <div style="display:flex; gap:6px; margin-top:8px; flex-wrap:wrap;">
        <button class="btn btn-primary btn-sm" onclick="goToTracking(${a.id})" style="flex:1;">
          📊 Theo dõi
        </button>
        <button class="btn btn-outline btn-sm" onclick="openDuplicateModal(${a.id})" style="flex:1; border-color:#93c5fd; color:#1d4ed8;" title="Giao bài tập này cho lớp khác">
          📋 Giao thêm
        </button>
        <button class="btn btn-outline btn-sm" onclick="toggleAssignmentStatus(${a.id})" style="width:auto;">
          ${a.status === 'open' ? '🔒 Đóng' : '🔓 Mở'}
        </button>
        <button class="btn btn-outline btn-sm" onclick="openEditAssignmentModal(${a.id})" style="width:auto;">
          ✏️
        </button>
        <button class="btn btn-outline btn-sm" onclick="deleteAssignment(${a.id})" style="width:auto; color:var(--danger); border-color:#fca5a5;">
          🗑️
        </button>
      </div>
    </div>
  `).join("");
}

function openCreateAssignmentModal() {
  document.getElementById("assignment-modal-title").textContent = "Tạo bài tập mới";
  document.getElementById("assign-id").value = "";
  document.getElementById("assign-title").value = "";
  document.getElementById("assign-subject").value = "";
  document.getElementById("assign-desc").value = "";

  // Hiển thị chọn nhiều lớp, ẩn chọn 1 lớp
  const multiWrap = document.getElementById("assign-multi-class-wrap");
  const singleWrap = document.getElementById("assign-single-class-wrap");
  if (multiWrap) multiWrap.style.display = "block";
  if (singleWrap) singleWrap.style.display = "none";
  renderAssignClassCheckboxes();
  
  // Format thời gian ISO sang local input
  const now = new Date();
  const nextWeek = new Date(now.getTime() + 7 * 24 * 3600 * 1000);
  document.getElementById("assign-start").value = toDatetimeLocal(now);
  document.getElementById("assign-deadline").value = toDatetimeLocal(nextWeek);
  document.getElementById("assign-allow-late").checked = false;
  document.getElementById("assign-allow-resubmit").checked = true;
  document.getElementById("assign-max-images").value = 10;
  document.getElementById("assign-max-size").value = 10;

  document.getElementById("assignment-modal").classList.add("show");
}

function openEditAssignmentModal(id) {
  const a = allAdminAssignments.find(item => item.id === id);
  if (!a) return;
  document.getElementById("assignment-modal-title").textContent = "Sửa bài tập";
  document.getElementById("assign-id").value = a.id;
  document.getElementById("assign-title").value = a.title;
  document.getElementById("assign-subject").value = a.subject;

  // Hiển thị chọn 1 lớp, ẩn chọn nhiều lớp
  const multiWrap = document.getElementById("assign-multi-class-wrap");
  const singleWrap = document.getElementById("assign-single-class-wrap");
  if (multiWrap) multiWrap.style.display = "none";
  if (singleWrap) singleWrap.style.display = "block";
  document.getElementById("assign-class").value = a.class_id;

  document.getElementById("assign-desc").value = a.description || "";
  document.getElementById("assign-start").value = toDatetimeLocal(new Date(a.start_at));
  document.getElementById("assign-deadline").value = toDatetimeLocal(new Date(a.deadline));
  document.getElementById("assign-allow-late").checked = Boolean(a.allow_late_submission);
  document.getElementById("assign-allow-resubmit").checked = Boolean(a.allow_resubmit);
  document.getElementById("assign-max-images").value = a.max_images;
  document.getElementById("assign-max-size").value = Math.round(a.max_file_size / (1024 * 1024));

  document.getElementById("assignment-modal").classList.add("show");
}

function closeAssignmentModal() {
  document.getElementById("assignment-modal").classList.remove("show");
}

function toDatetimeLocal(date) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

async function handleSaveAssignment(e) {
  e.preventDefault();
  const id = document.getElementById("assign-id").value;
  const title = document.getElementById("assign-title").value.trim();
  const subject = document.getElementById("assign-subject").value.trim();
  const description = document.getElementById("assign-desc").value.trim();
  const start_at = new Date(document.getElementById("assign-start").value).toISOString();
  const deadline = new Date(document.getElementById("assign-deadline").value).toISOString();
  const allow_late_submission = document.getElementById("assign-allow-late").checked;
  const allow_resubmit = document.getElementById("assign-allow-resubmit").checked;
  const max_images = parseInt(document.getElementById("assign-max-images").value) || 10;
  const max_file_size = (parseInt(document.getElementById("assign-max-size").value) || 10) * 1024 * 1024;

  if (id) {
    // Sửa bài tập cho 1 lớp
    const class_id = parseInt(document.getElementById("assign-class").value);
    const payload = {
      title, subject, class_id, description,
      start_at, deadline, allow_late_submission, allow_resubmit,
      resubmit_after_deadline: allow_late_submission,
      submission_grace_period: 300,
      max_images, max_file_size
    };

    try {
      await apiCall(`/api/admin/assignments/${id}`, {
        method: "PUT",
        body: JSON.stringify(payload)
      });
      showToast("Đã cập nhật bài tập thành công!");
      closeAssignmentModal();
      loadAdminAssignments();
    } catch (err) {
      showToast(err.message, true);
    }
  } else {
    // Tạo bài tập mới: gom danh sách các lớp đã tick
    const checkedBoxes = Array.from(document.querySelectorAll(".assign-class-checkbox:checked"));
    const class_ids = checkedBoxes.map(cb => parseInt(cb.value));

    if (class_ids.length === 0) {
      showToast("Vui lòng chọn ít nhất một lớp học áp dụng bài tập!", true);
      return;
    }

    const payload = {
      title, subject, class_ids, description,
      start_at, deadline, allow_late_submission, allow_resubmit,
      resubmit_after_deadline: allow_late_submission,
      submission_grace_period: 300,
      max_images, max_file_size
    };

    try {
      const res = await apiCall("/api/admin/assignments", {
        method: "POST",
        body: JSON.stringify(payload)
      });
      showToast(`Đã tạo bài tập thành công cho ${res.count || class_ids.length} lớp học!`);
      closeAssignmentModal();
      loadAdminAssignments();
    } catch (err) {
      showToast(err.message, true);
    }
  }
}

// Modal Nhân bản / Giao bài tập sang lớp khác
function openDuplicateModal(assignmentId) {
  const a = allAdminAssignments.find(item => item.id === assignmentId);
  if (!a) return;

  document.getElementById("duplicate-assign-id").value = a.id;
  document.getElementById("duplicate-assign-title").textContent = `${a.subject} – ${a.title}`;
  document.getElementById("duplicate-assign-current-class").textContent = `Hiện tại đã giao cho: Lớp ${a.class_name}`;

  const listContainer = document.getElementById("duplicate-classes-list");
  const otherClasses = allClasses.filter(c => c.id !== a.class_id);

  if (otherClasses.length === 0) {
    listContainer.innerHTML = `<div style="font-size:0.85rem; color:var(--gray-500); padding:8px;">Hệ thống chưa có lớp khác để giao thêm.</div>`;
    document.getElementById("btn-confirm-duplicate").disabled = true;
  } else {
    listContainer.innerHTML = otherClasses.map(c => `
      <label style="display:flex; align-items:center; gap:8px; padding:6px 10px; background:#fff; border-radius:6px; cursor:pointer; border:1px solid #e2e8f0; font-size:0.88rem;">
        <input type="checkbox" class="duplicate-class-checkbox" value="${c.id}" checked style="width:17px; height:17px; accent-color:var(--primary);">
        <span style="font-weight:700; color:var(--gray-800);">🏫 Lớp ${c.name}</span>
        <span style="font-size:0.75rem; color:var(--gray-500); margin-left:auto;">(${c.student_count || 0} học sinh)</span>
      </label>
    `).join("");
    document.getElementById("btn-confirm-duplicate").disabled = false;
  }

  document.getElementById("duplicate-modal").classList.add("show");
}

function closeDuplicateModal() {
  document.getElementById("duplicate-modal").classList.remove("show");
}

async function handleDuplicateAssignment(e) {
  e.preventDefault();
  const id = document.getElementById("duplicate-assign-id").value;
  const checkedBoxes = Array.from(document.querySelectorAll(".duplicate-class-checkbox:checked"));
  const target_class_ids = checkedBoxes.map(cb => parseInt(cb.value));

  if (target_class_ids.length === 0) {
    showToast("Vui lòng chọn ít nhất một lớp để giao thêm!", true);
    return;
  }

  try {
    const res = await apiCall(`/api/admin/assignments/${id}/duplicate`, {
      method: "POST",
      body: JSON.stringify({ target_class_ids })
    });
    showToast(`Đã giao bài tập thành công cho ${res.count || target_class_ids.length} lớp học!`);
    closeDuplicateModal();
    loadAdminAssignments();
  } catch (err) {
    showToast(err.message, true);
  }
}

async function toggleAssignmentStatus(id) {
  try {
    const res = await apiCall(`/api/admin/assignments/${id}/toggle-status`, { method: "POST" });
    showToast(res.status === "open" ? "Đã mở lại bài tập!" : "Đã đóng bài tập!");
    loadAdminAssignments();
  } catch (err) {
    showToast(err.message, true);
  }
}

async function deleteAssignment(id) {
  if (!confirm("Bạn có chắc chắn muốn xóa bài tập này cùng toàn bộ bài nộp của học sinh?")) return;
  try {
    await apiCall(`/api/admin/assignments/${id}`, { method: "DELETE" });
    showToast("Đã xóa bài tập thành công!");
    loadAdminAssignments();
  } catch (err) {
    showToast(err.message, true);
  }
}

// 4. Theo dõi ai đã nộp / chưa nộp
function goToTracking(assignmentId) {
  switchAdminTab("tracking");
  const select = document.getElementById("tracking-assignment-select");
  select.value = assignmentId;
  onTrackingAssignmentChange();
}

async function setupTrackingDropdown() {
  const select = document.getElementById("tracking-assignment-select");
  try {
    const res = await apiCall("/api/admin/assignments");
    allAdminAssignments = res.assignments;
    select.innerHTML = `<option value="">-- Chọn bài tập cần theo dõi --</option>` +
      allAdminAssignments.map(a => `<option value="${a.id}">[Lớp ${a.class_name}] ${a.title} (${a.subject})</option>`).join("");
    
    if (allAdminAssignments.length > 0 && !select.value) {
      select.value = allAdminAssignments[0].id;
      onTrackingAssignmentChange();
    }
  } catch (err) {
    console.error(err);
  }
}

async function onTrackingAssignmentChange() {
  const assignId = document.getElementById("tracking-assignment-select").value;
  if (!assignId) {
    document.getElementById("tracking-summary-card").style.display = "none";
    document.getElementById("tracking-controls").style.display = "none";
    document.getElementById("tracking-student-cards").innerHTML = "";
    return;
  }

  try {
    const res = await apiCall(`/api/admin/assignments/${assignId}/tracking`);
    trackingData = res;
    renderTrackingSummary();
    filterTrackingStudents();
  } catch (err) {
    showToast(err.message, true);
  }
}

function renderTrackingSummary() {
  if (!trackingData) return;
  const a = trackingData.assignment;
  const s = trackingData.summary;

  document.getElementById("tracking-summary-card").style.display = "block";
  document.getElementById("tracking-controls").style.display = "block";

  document.getElementById("track-assign-title").textContent = a.title;
  document.getElementById("track-assign-deadline").textContent = `Hạn nộp: ${formatDatetimeVN(a.deadline)} • Môn ${a.subject} • Lớp ${a.class_name}`;

  const submittedTotal = s.on_time_count + s.late_count;
  document.getElementById("track-progress-bar").style.width = `${s.completion_rate}%`;
  document.getElementById("track-ratio-text").textContent = `${submittedTotal} / ${s.total_students} đã nộp`;
  document.getElementById("track-rate-text").textContent = `${s.completion_rate}%`;

  document.getElementById("track-ontime-tag").textContent = `🟢 ${s.on_time_count} đúng hạn`;
  document.getElementById("track-late-tag").textContent = `🟣 ${s.late_count} nộp muộn`;
  document.getElementById("track-unsub-tag").textContent = `🔴 ${s.unsubmitted_count} chưa nộp`;
}

function setTrackingFilter(filter, el) {
  currentTrackingFilter = filter;
  document.querySelectorAll("#tracking-controls .filter-pill").forEach(p => p.classList.remove("active"));
  if (el) el.classList.add("active");
  filterTrackingStudents();
}

function filterTrackingStudents() {
  if (!trackingData) return;
  const search = document.getElementById("track-student-search").value.toLowerCase().trim();
  const container = document.getElementById("tracking-student-cards");

  let filtered = trackingData.students;

  // Lọc theo search
  if (search) {
    filtered = filtered.filter(st => st.student_name.toLowerCase().includes(search) || st.username.toLowerCase().includes(search));
  }

  // Lọc theo filter
  if (currentTrackingFilter === "on_time") {
    filtered = filtered.filter(st => st.status_info.status_key === "submitted");
  } else if (currentTrackingFilter === "late") {
    filtered = filtered.filter(st => st.status_info.status_key === "submitted_late");
  } else if (currentTrackingFilter === "unsubmitted") {
    filtered = filtered.filter(st => st.submission === null);
  }

  if (filtered.length === 0) {
    container.innerHTML = `<div class="card" style="text-align:center; padding:20px; color:var(--gray-600);">Không có học sinh nào phù hợp bộ lọc.</div>`;
    return;
  }

  container.innerHTML = filtered.map(st => `
    <div class="card">
      <div class="card-header">
        <div>
          <h4 class="card-title">${st.student_name}</h4>
          <span style="font-size:0.8rem; color:var(--gray-600);">@${st.username}</span>
        </div>
        <span class="badge ${st.status_info.status_badge_class}">${st.status_info.status_label}</span>
      </div>

      <div class="card-meta">
        ${st.submission ? `
          <div>⏰ Thời gian nộp: <b>${formatDatetimeVN(st.submission.submitted_at)}</b></div>
          <div>🔄 Lần nộp thứ: <b>${st.submission.attempt_number}</b></div>
          ${st.submission.is_late ? `<div style="color:var(--late); font-weight:600;">⚠️ Nộp muộn: ${formatDurationJS(st.submission.late_seconds)}</div>` : `<div style="color:var(--success); font-weight:600;">✅ Nộp đúng hạn</div>`}
        ` : `
          <div style="color:var(--danger); font-weight:600;">Chưa nộp bài</div>
        `}
      </div>

      ${st.submission ? `
        <button class="btn btn-primary btn-sm" onclick="viewStudentSubmission(${st.submission.id})" style="margin-top:8px;">
          🖼️ Xem ảnh bài làm (${st.submission.attempt_number ? 'Lần ' + st.submission.attempt_number : ''})
        </button>
      ` : ""}
    </div>
  `).join("");
}

function formatDurationJS(seconds) {
  if (!seconds || seconds <= 0) return "0 phút";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) return `${hours} giờ ${minutes} phút`;
  return `${minutes} phút`;
}

// Mở Image Viewer cho Admin xem bài làm của học sinh
async function viewStudentSubmission(submissionId) {
  try {
    const res = await apiCall(`/api/admin/submissions/${submissionId}`);
    const sub = res.submission;

    if (!sub.files || sub.files.length === 0) {
      showToast("Bài nộp này không có ảnh nào.", true);
      return;
    }

    const files = sub.files.map(f => ({
      id: f.id,
      url: `/api/files/${f.id}`,
      filename: f.sanitized_filename || `${sub.student_name}_anh_${f.id}.jpg`
    }));

    window.mobileImageViewer.open({
      files: files,
      studentName: `${sub.student_name} (${sub.class_name})`,
      assignmentTitle: sub.assignment_title,
      submitTime: `Nộp lúc ${formatDatetimeVN(sub.submitted_at)} - Lần ${sub.attempt_number} ${sub.is_late ? '(Nộp muộn)' : '(Đúng hạn)'}`
    });
  } catch (err) {
    showToast(err.message, true);
  }
}

// 5. Tải file ZIP chứa toàn bộ ảnh bài làm của học sinh
async function downloadAssignmentZipById(assignId) {
  if (!assignId) return;
  try {
    showToast("⏳ Đang chuẩn bị và nén các file ảnh bài làm thành file ZIP...");
    const token = localStorage.getItem("access_token");
    const res = await fetch(`/api/admin/assignments/${assignId}/export-zip`, {
      headers: token ? { "Authorization": `Bearer ${token}` } : {}
    });

    if (!res.ok) {
      let msg = "Không thể tải file ZIP.";
      try {
        const errJson = await res.json();
        if (errJson && errJson.detail) msg = errJson.detail;
      } catch (e) {}
      showToast(msg, true);
      return;
    }

    const blob = await res.blob();
    let filename = `BaiNop_BaiTap_${assignId}.zip`;
    const disposition = res.headers.get("Content-Disposition");
    if (disposition) {
      const utf8Match = disposition.match(/filename\*=utf-8''([^;\r\n]+)/i);
      const standardMatch = disposition.match(/filename="?([^";\r\n]+)"?/i);
      if (utf8Match && utf8Match[1]) {
        filename = decodeURIComponent(utf8Match[1]);
      } else if (standardMatch && standardMatch[1]) {
        filename = decodeURIComponent(standardMatch[1]);
      }
    }

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => window.URL.revokeObjectURL(url), 1000);
    showToast("✅ Đã tải file ZIP toàn bộ bài làm về máy thành công!");
  } catch (err) {
    showToast("Lỗi tải file: " + err.message, true);
  }
}

function downloadCurrentAssignmentZip() {
  const assignId = document.getElementById("tracking-assignment-select").value;
  if (!assignId) {
    showToast("Vui lòng chọn bài tập trước.", true);
    return;
  }
  downloadAssignmentZipById(assignId);
}

// 6. Modal & Dashboard Danh sách Tải ZIP toàn bộ ảnh bài làm
function openExportZipModal() {
  renderDashboardZipList();
  const modal = document.getElementById("export-zip-modal");
  if (modal) modal.classList.add("show");
}

function closeExportZipModal() {
  const modal = document.getElementById("export-zip-modal");
  if (modal) modal.classList.remove("show");
}

function renderDashboardZipList() {
  const dashContainer = document.getElementById("dashboard-zip-assignments-list");
  const modalContainer = document.getElementById("export-zip-modal-list");

  if (!allAdminAssignments || allAdminAssignments.length === 0) {
    const emptyHtml = `<div style="text-align:center; padding:12px; color:var(--gray-500); font-size:0.85rem;">Chưa có bài tập nào trên hệ thống. Hãy nhấn "+ Tạo bài tập" để thêm bài mới.</div>`;
    if (dashContainer) dashContainer.innerHTML = emptyHtml;
    if (modalContainer) modalContainer.innerHTML = emptyHtml;
    return;
  }

  const html = allAdminAssignments.map(a => `
    <div style="display:flex; justify-content:space-between; align-items:center; background:#ffffff; border:1px solid #d1fae5; border-radius:8px; padding:10px 14px; gap:10px; flex-wrap:wrap; box-shadow:0 1px 2px rgba(0,0,0,0.04);">
      <div style="flex:1; min-width:180px;">
        <div style="display:flex; align-items:center; gap:6px; margin-bottom:2px;">
          <span style="font-size:0.75rem; font-weight:800; background:#e0e7ff; color:#3730a3; padding:2px 8px; border-radius:10px;">Lớp ${a.class_name}</span>
          <span style="font-size:0.75rem; font-weight:700; color:var(--primary); text-transform:uppercase;">${a.subject}</span>
        </div>
        <div style="font-weight:700; font-size:0.92rem; color:var(--gray-800);">${a.title}</div>
        <div style="font-size:0.78rem; color:var(--gray-500); margin-top:2px;">
          📊 Đã nộp: <b>${a.submitted_count || 0} / ${a.total_students || 0}</b> học sinh
        </div>
      </div>
      <button class="btn btn-sm" onclick="downloadAssignmentZipById(${a.id})" style="background:#059669; color:#ffffff; font-weight:700; border:none; padding:8px 14px; border-radius:6px; cursor:pointer; display:inline-flex; align-items:center; gap:6px; white-space:nowrap; box-shadow:0 1px 3px rgba(0,0,0,0.1);">
        ⬇️ Tải file ZIP (${a.submitted_count || 0})
      </button>
    </div>
  `).join("");

  if (dashContainer) dashContainer.innerHTML = html;
  if (modalContainer) modalContainer.innerHTML = html;
}
