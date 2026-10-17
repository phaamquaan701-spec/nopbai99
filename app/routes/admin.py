from typing import List, Optional
import os
import re
import tempfile
import zipfile
from starlette.background import BackgroundTask
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.config import UPLOAD_DIR
from app.database import get_db, get_current_iso_time
from app.security import require_admin, hash_password
from app.deadline_engine import (
    evaluate_student_assignment_status,
    parse_iso_time,
    get_server_now,
    format_duration
)

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# Models
class CreateClassRequest(BaseModel):
    name: str

class CreateStudentRequest(BaseModel):
    username: str
    password: str
    full_name: str
    class_id: Optional[int] = None

class UpdateStudentRequest(BaseModel):
    full_name: str
    class_id: Optional[int] = None
    status: str = "active"

class ChangePasswordRequest(BaseModel):
    new_password: str

class CreateAssignmentRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    subject: str
    class_id: Optional[int] = None
    class_ids: Optional[List[int]] = None
    start_at: str
    deadline: str
    allow_resubmit: bool = True
    allow_late_submission: bool = False
    resubmit_after_deadline: bool = False
    submission_grace_period: int = 300
    max_images: int = 10
    max_file_size: int = 10485760

class DuplicateAssignmentRequest(BaseModel):
    target_class_ids: List[int]

class UpdateAssignmentRequest(BaseModel):
    title: str
    description: Optional[str] = ""
    subject: str
    class_id: int
    start_at: str
    deadline: str
    allow_resubmit: bool = True
    allow_late_submission: bool = False
    resubmit_after_deadline: bool = False
    submission_grace_period: int = 300
    max_images: int = 10
    max_file_size: int = 10485760

# 1. Admin Dashboard
@router.get("/dashboard")
def get_admin_dashboard(admin: dict = Depends(require_admin)):
    with get_db() as conn:
        total_classes = conn.execute("SELECT COUNT(*) as c FROM classes").fetchone()["c"]
        total_students = conn.execute("SELECT COUNT(*) as c FROM users WHERE role = 'student'").fetchone()["c"]
        total_assignments = conn.execute("SELECT COUNT(*) as c FROM assignments").fetchone()["c"]
        total_submissions = conn.execute("SELECT COUNT(*) as c FROM submissions").fetchone()["c"]

        # Bài tập sắp hết hạn trong 24h
        assignments = conn.execute(
            """
            SELECT a.id, a.title, a.subject, a.deadline, a.class_id, c.name as class_name, a.status
            FROM assignments a
            JOIN classes c ON a.class_id = c.id
            WHERE a.status = 'open'
            ORDER BY a.deadline ASC
            """
        ).fetchall()

        now = get_server_now()
        upcoming = []
        for a in assignments:
            dl = parse_iso_time(a["deadline"])
            if now <= dl and (dl - now).total_seconds() <= 86400:
                upcoming.append(dict(a))

        return {
            "success": True,
            "stats": {
                "total_classes": total_classes,
                "total_students": total_students,
                "total_assignments": total_assignments,
                "total_submissions": total_submissions
            },
            "upcoming_assignments": upcoming[:5]
        }

# 2. Classes
@router.get("/classes")
def list_classes(admin: dict = Depends(require_admin)):
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT c.id, c.name, c.created_at, COUNT(u.id) as student_count
            FROM classes c
            LEFT JOIN users u ON u.class_id = c.id AND u.role = 'student'
            GROUP BY c.id
            ORDER BY c.name ASC
            """
        ).fetchall()
        return {"success": True, "classes": [dict(r) for r in rows]}

@router.post("/classes")
def create_class(req: CreateClassRequest, admin: dict = Depends(require_admin)):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Tên lớp không được để trống.")
    now = get_current_iso_time()
    with get_db() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO classes (name, created_at) VALUES (?, ?)", (name, now))
            return {"success": True, "id": cursor.lastrowid, "name": name}
        except Exception:
            raise HTTPException(status_code=400, detail="Lớp học này đã tồn tại.")

@router.put("/classes/{class_id}")
def update_class(class_id: int, req: CreateClassRequest, admin: dict = Depends(require_admin)):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Tên lớp không được để trống.")
    with get_db() as conn:
        try:
            conn.execute("UPDATE classes SET name = ? WHERE id = ?", (name, class_id))
            return {"success": True, "message": "Đã cập nhật tên lớp."}
        except Exception:
            raise HTTPException(status_code=400, detail="Tên lớp bị trùng lặp.")

@router.delete("/classes/{class_id}")
def delete_class(class_id: int, admin: dict = Depends(require_admin)):
    with get_db() as conn:
        conn.execute("DELETE FROM classes WHERE id = ?", (class_id,))
        return {"success": True, "message": "Đã xóa lớp học."}

# 3. Students
@router.get("/students")
def list_students(
    class_id: Optional[int] = None,
    search: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    query = """
        SELECT u.id, u.username, u.full_name, u.role, u.class_id, u.status, u.created_at, c.name as class_name
        FROM users u
        LEFT JOIN classes c ON u.class_id = c.id
        WHERE u.role = 'student'
    """
    params = []
    if class_id:
        query += " AND u.class_id = ?"
        params.append(class_id)
    if search:
        query += " AND (u.full_name LIKE ? OR u.username LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    query += " ORDER BY u.id DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return {"success": True, "students": [dict(r) for r in rows]}

@router.post("/students")
def create_student(req: CreateStudentRequest, admin: dict = Depends(require_admin)):
    username = req.username.strip().lower()
    full_name = req.full_name.strip()
    if not username or not full_name or not req.password:
        raise HTTPException(status_code=400, detail="Vui lòng điền đầy đủ tên đăng nhập, họ tên và mật khẩu.")
    pwd_hash = hash_password(req.password)
    now = get_current_iso_time()
    with get_db() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, full_name, role, class_id, status, created_at)
                VALUES (?, ?, ?, 'student', ?, 'active', ?)
                """,
                (username, pwd_hash, full_name, req.class_id, now)
            )
            return {"success": True, "id": cursor.lastrowid, "username": username}
        except Exception:
            raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại trong hệ thống.")

@router.put("/students/{student_id}")
def update_student(student_id: int, req: UpdateStudentRequest, admin: dict = Depends(require_admin)):
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET full_name = ?, class_id = ?, status = ? WHERE id = ? AND role = 'student'",
            (req.full_name.strip(), req.class_id, req.status, student_id)
        )
        return {"success": True, "message": "Đã cập nhật thông tin học sinh."}

@router.put("/students/{student_id}/password")
def change_student_password(student_id: int, req: ChangePasswordRequest, admin: dict = Depends(require_admin)):
    if len(req.new_password) < 4:
        raise HTTPException(status_code=400, detail="Mật khẩu tối thiểu 4 ký tự.")
    pwd_hash = hash_password(req.new_password)
    with get_db() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ? AND role = 'student'", (pwd_hash, student_id))
        return {"success": True, "message": "Đã đổi mật khẩu học sinh thành công."}

@router.delete("/students/{student_id}")
def delete_student(student_id: int, admin: dict = Depends(require_admin)):
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE id = ? AND role = 'student'", (student_id,))
        return {"success": True, "message": "Đã xóa học sinh."}

# 4. Assignments CRUD
@router.get("/assignments")
def list_assignments(class_id: Optional[int] = None, admin: dict = Depends(require_admin)):
    query = """
        SELECT a.*, c.name as class_name,
               (SELECT COUNT(DISTINCT student_id) FROM submissions WHERE assignment_id = a.id) as submitted_count,
               (SELECT COUNT(*) FROM users WHERE class_id = a.class_id AND role = 'student') as total_students
        FROM assignments a
        JOIN classes c ON a.class_id = c.id
    """
    params = []
    if class_id:
        query += " WHERE a.class_id = ?"
        params.append(class_id)
    query += " ORDER BY a.id DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return {"success": True, "assignments": [dict(r) for r in rows]}

@router.post("/assignments")
def create_assignment(req: CreateAssignmentRequest, admin: dict = Depends(require_admin)):
    now = get_current_iso_time()
    target_class_ids = []
    if req.class_ids and len(req.class_ids) > 0:
        target_class_ids = req.class_ids
    elif req.class_id:
        target_class_ids = [req.class_id]
    else:
        raise HTTPException(status_code=400, detail="Vui lòng chọn ít nhất một lớp học áp dụng.")

    created_ids = []
    with get_db() as conn:
        cursor = conn.cursor()
        for cid in target_class_ids:
            cursor.execute(
                """
                INSERT INTO assignments (
                    title, description, subject, class_id, created_by,
                    start_at, deadline, allow_resubmit, allow_late_submission,
                    resubmit_after_deadline, submission_grace_period, max_images, max_file_size,
                    status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
                """,
                (
                    req.title.strip(),
                    req.description.strip(),
                    req.subject.strip(),
                    cid,
                    admin["id"],
                    req.start_at,
                    req.deadline,
                    1 if req.allow_resubmit else 0,
                    1 if req.allow_late_submission else 0,
                    1 if req.resubmit_after_deadline else 0,
                    req.submission_grace_period,
                    req.max_images,
                    req.max_file_size,
                    now,
                    now
                )
            )
            created_ids.append(cursor.lastrowid)
        return {"success": True, "ids": created_ids, "id": created_ids[0], "count": len(created_ids)}

@router.post("/assignments/{assignment_id}/duplicate")
def duplicate_assignment(assignment_id: int, req: DuplicateAssignmentRequest, admin: dict = Depends(require_admin)):
    now = get_current_iso_time()
    with get_db() as conn:
        cursor = conn.cursor()
        orig = cursor.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
        if not orig:
            raise HTTPException(status_code=404, detail="Không tìm thấy bài tập gốc.")
        
        orig_dict = dict(orig)
        created_ids = []
        for cid in req.target_class_ids:
            # Skip if this assignment title already exists for this class
            existing = cursor.execute(
                "SELECT id FROM assignments WHERE class_id = ? AND title = ?",
                (cid, orig_dict["title"])
            ).fetchone()
            if existing:
                continue
            cursor.execute(
                """
                INSERT INTO assignments (
                    title, description, subject, class_id, created_by,
                    start_at, deadline, allow_resubmit, allow_late_submission,
                    resubmit_after_deadline, submission_grace_period, max_images, max_file_size,
                    status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)
                """,
                (
                    orig_dict["title"],
                    orig_dict["description"],
                    orig_dict["subject"],
                    cid,
                    admin["id"],
                    orig_dict["start_at"],
                    orig_dict["deadline"],
                    orig_dict["allow_resubmit"],
                    orig_dict["allow_late_submission"],
                    orig_dict["resubmit_after_deadline"],
                    orig_dict["submission_grace_period"],
                    orig_dict["max_images"],
                    orig_dict["max_file_size"],
                    now,
                    now
                )
            )
            created_ids.append(cursor.lastrowid)
        return {"success": True, "created_ids": created_ids, "count": len(created_ids)}

@router.put("/assignments/{assignment_id}")
def update_assignment(assignment_id: int, req: UpdateAssignmentRequest, admin: dict = Depends(require_admin)):
    now = get_current_iso_time()
    with get_db() as conn:
        conn.execute(
            """
            UPDATE assignments SET
                title = ?, description = ?, subject = ?, class_id = ?,
                start_at = ?, deadline = ?, allow_resubmit = ?,
                allow_late_submission = ?, resubmit_after_deadline = ?,
                submission_grace_period = ?, max_images = ?, max_file_size = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                req.title.strip(),
                req.description.strip(),
                req.subject.strip(),
                req.class_id,
                req.start_at,
                req.deadline,
                1 if req.allow_resubmit else 0,
                1 if req.allow_late_submission else 0,
                1 if req.resubmit_after_deadline else 0,
                req.submission_grace_period,
                req.max_images,
                req.max_file_size,
                now,
                assignment_id
            )
        )
        return {"success": True, "message": "Đã cập nhật bài tập."}

@router.post("/assignments/{assignment_id}/toggle-status")
def toggle_assignment_status(assignment_id: int, admin: dict = Depends(require_admin)):
    with get_db() as conn:
        curr = conn.execute("SELECT status FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
        if not curr:
            raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")
        new_status = "closed" if curr["status"] == "open" else "open"
        conn.execute("UPDATE assignments SET status = ?, updated_at = ? WHERE id = ?", (new_status, get_current_iso_time(), assignment_id))
        return {"success": True, "status": new_status}

@router.delete("/assignments/{assignment_id}")
def delete_assignment(assignment_id: int, admin: dict = Depends(require_admin)):
    with get_db() as conn:
        conn.execute("DELETE FROM assignments WHERE id = ?", (assignment_id,))
        return {"success": True, "message": "Đã xóa bài tập."}

# 5. Theo dõi Nộp bài (Assignment Submissions Tracking)
@router.get("/assignments/{assignment_id}/tracking")
def get_assignment_tracking(
    assignment_id: int,
    status_filter: Optional[str] = "all",
    search: Optional[str] = None,
    admin: dict = Depends(require_admin)
):
    with get_db() as conn:
        assign = conn.execute(
            """
            SELECT a.*, c.name as class_name
            FROM assignments a
            JOIN classes c ON a.class_id = c.id
            WHERE a.id = ?
            """,
            (assignment_id,)
        ).fetchone()

        if not assign:
            raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")

        assign_dict = dict(assign)
        class_id = assign_dict["class_id"]

        # Lấy danh sách toàn bộ học sinh trong lớp
        students_query = "SELECT id, username, full_name, status FROM users WHERE class_id = ? AND role = 'student'"
        students_params = [class_id]
        if search:
            students_query += " AND (full_name LIKE ? OR username LIKE ?)"
            students_params.extend([f"%{search}%", f"%{search}%"])
        students_query += " ORDER BY full_name ASC"

        students = conn.execute(students_query, students_params).fetchall()
        now = get_server_now()

        on_time_count = 0
        late_count = 0
        unsubmitted_count = 0
        student_records = []

        for st in students:
            st_dict = dict(st)
            # Lấy submission mới nhất của học sinh này
            latest_sub = conn.execute(
                """
                SELECT id, submitted_at, status, attempt_number, is_late, late_seconds
                FROM submissions
                WHERE assignment_id = ? AND student_id = ?
                ORDER BY attempt_number DESC
                LIMIT 1
                """,
                (assignment_id, st_dict["id"])
            ).fetchone()

            sub_dict = dict(latest_sub) if latest_sub else None
            eval_res = evaluate_student_assignment_status(assign_dict, sub_dict, now)

            if sub_dict:
                if eval_res["status_key"] == "submitted_late":
                    late_count += 1
                else:
                    on_time_count += 1
            else:
                unsubmitted_count += 1

            # Lọc theo filter
            # filter options: all, on_time, late, unsubmitted, overdue_unsubmitted
            if status_filter == "on_time" and eval_res["status_key"] != "submitted":
                continue
            if status_filter == "late" and eval_res["status_key"] != "submitted_late":
                continue
            if status_filter == "unsubmitted" and sub_dict is not None:
                continue
            if status_filter == "overdue_unsubmitted" and eval_res["status_key"] != "overdue_unsubmitted":
                continue

            record = {
                "student_id": st_dict["id"],
                "student_name": st_dict["full_name"],
                "username": st_dict["username"],
                "submission": sub_dict,
                "status_info": eval_res
            }
            student_records.append(record)

        total_students = len(students)
        completion_rate = round(((on_time_count + late_count) / total_students * 100), 1) if total_students > 0 else 0

        return {
            "success": True,
            "assignment": assign_dict,
            "summary": {
                "total_students": total_students,
                "on_time_count": on_time_count,
                "late_count": late_count,
                "unsubmitted_count": unsubmitted_count,
                "completion_rate": completion_rate
            },
            "students": student_records
        }

# 6. Chi tiết bài nộp của học sinh (Xem ảnh bài làm)
@router.get("/submissions/{submission_id}")
def get_submission_detail(submission_id: int, admin: dict = Depends(require_admin)):
    with get_db() as conn:
        sub = conn.execute(
            """
            SELECT s.*, u.full_name as student_name, u.username, c.name as class_name,
                   a.title as assignment_title, a.subject, a.deadline
            FROM submissions s
            JOIN users u ON s.student_id = u.id
            JOIN assignments a ON s.assignment_id = a.id
            JOIN classes c ON u.class_id = c.id
            WHERE s.id = ?
            """,
            (submission_id,)
        ).fetchone()

        if not sub:
            raise HTTPException(status_code=404, detail="Không tìm thấy bài nộp.")

        sub_dict = dict(sub)

        # Lấy danh sách files của submission này
        files = conn.execute(
            """
            SELECT id, sanitized_filename, original_filename, mime_type, file_size, order_index
            FROM submission_files
            WHERE submission_id = ?
            ORDER BY order_index ASC, id ASC
            """,
            (submission_id,)
        ).fetchall()

        file_list = []
        for f in files:
            f_dict = dict(f)
            f_dict["url"] = f"/api/files/{f_dict['id']}"
            file_list.append(f_dict)

        sub_dict["files"] = file_list

        # Lấy các lần nộp khác (attempts) của học sinh này cho cùng bài tập
        other_attempts = conn.execute(
            """
            SELECT id, submitted_at, attempt_number, is_late, late_seconds
            FROM submissions
            WHERE assignment_id = ? AND student_id = ?
            ORDER BY attempt_number DESC
            """,
            (sub_dict["assignment_id"], sub_dict["student_id"])
        ).fetchall()

        sub_dict["all_attempts"] = [dict(oa) for oa in other_attempts]
        return {"success": True, "submission": sub_dict}


def sanitize_filename_str(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return name.strip() or "hoc_sinh"


# 7. Tải toàn bộ bài nộp của cả lớp về máy dưới dạng file ZIP
@router.get("/assignments/{assignment_id}/export-zip")
def export_assignment_submissions_zip(assignment_id: int, admin: dict = Depends(require_admin)):
    """
    Đóng gói toàn bộ ảnh bài làm của học sinh trong bài tập này thành 1 file ZIP duy nhất.
    """
    with get_db() as conn:
        assign = conn.execute(
            """
            SELECT a.id, a.title, a.subject, c.name as class_name
            FROM assignments a
            JOIN classes c ON a.class_id = c.id
            WHERE a.id = ?
            """,
            (assignment_id,)
        ).fetchone()

        if not assign:
            raise HTTPException(status_code=404, detail="Không tìm thấy bài tập.")

        # Lấy danh sách học sinh và file bài nộp mới nhất của từng học sinh
        query = """
        SELECT 
            u.id as student_id, u.full_name as student_name, u.username,
            s.id as submission_id, s.attempt_number, s.submitted_at, s.is_late, s.late_seconds,
            sf.id as file_id, sf.storage_key, sf.sanitized_filename, sf.order_index
        FROM users u
        JOIN submissions s ON s.student_id = u.id AND s.assignment_id = ?
        JOIN submission_files sf ON sf.submission_id = s.id
        WHERE s.attempt_number = (
            SELECT MAX(s2.attempt_number) 
            FROM submissions s2 
            WHERE s2.assignment_id = ? AND s2.student_id = u.id
        )
        ORDER BY u.full_name COLLATE NOCASE ASC, sf.order_index ASC
        """
        rows = conn.execute(query, (assignment_id, assignment_id)).fetchall()

    if not rows:
        raise HTTPException(
            status_code=400,
            detail="Bài tập này hiện chưa có bài nộp nào có ảnh để tải về."
        )

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp_path = tmp.name
    tmp.close()

    clean_subject = sanitize_filename_str(assign["subject"]).replace(" ", "_")
    clean_title = sanitize_filename_str(assign["title"]).replace(" ", "_")
    clean_class = sanitize_filename_str(assign["class_name"]).replace(" ", "_")
    zip_display_name = f"BaiNop_{clean_subject}_{clean_class}_{clean_title}.zip"

    manifest_lines = [
        f"BÁO CÁO BÀI NỘP: {assign['title']} ({assign['subject']})",
        f"Lớp: {assign['class_name']}",
        f"Thời gian xuất: {get_server_now().strftime('%d/%m/%Y %H:%M:%S')}",
        "=" * 60,
        f"{'STT':<4} | {'Họ và tên':<24} | {'Tài khoản':<16} | {'Trạng thái':<14} | {'Số ảnh':<6}",
        "-" * 60,
    ]

    students_data = {}
    for r in rows:
        st_id = r["student_id"]
        if st_id not in students_data:
            students_data[st_id] = {
                "name": r["student_name"],
                "username": r["username"],
                "submitted_at": r["submitted_at"],
                "is_late": r["is_late"],
                "attempt_number": r["attempt_number"],
                "files": []
            }
        students_data[st_id]["files"].append(r)

    with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
        stt = 1
        for st_id, data in students_data.items():
            status_str = "Nộp muộn" if data["is_late"] else "Đúng hạn"
            manifest_lines.append(
                f"{stt:<4} | {data['name']:<24} | {data['username']:<16} | {status_str:<14} | {len(data['files']):<6}"
            )
            safe_st_name = sanitize_filename_str(data["name"]).replace(" ", "_")
            folder_name = f"{stt:02d}_{safe_st_name}_{data['username']}"

            for idx, f in enumerate(data["files"], start=1):
                storage_key = f["storage_key"]
                physical_file = (UPLOAD_DIR / storage_key).resolve()
                if physical_file.is_file():
                    ext = physical_file.suffix or ".jpg"
                    arcname = f"{folder_name}/trang_{idx:02d}{ext}"
                    zf.write(physical_file, arcname=arcname)
            stt += 1

        manifest_lines.append("=" * 60)
        zf.writestr("danh_sach_nop_bai.txt", "\n".join(manifest_lines).encode("utf-8-sig"))

    def cleanup():
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

    return FileResponse(
        path=tmp_path,
        filename=zip_display_name,
        media_type="application/zip",
        background=BackgroundTask(cleanup)
    )

