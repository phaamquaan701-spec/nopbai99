from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from app.database import get_db, get_current_iso_time
from app.security import require_student
from app.deadline_engine import (
    evaluate_student_assignment_status,
    validate_submission_eligibility,
    get_server_now
)
from app.image_service import process_and_save_image

router = APIRouter(prefix="/api/student", tags=["Student"])

@router.get("/dashboard")
def get_student_dashboard(student: dict = Depends(require_student)):
    class_id = student.get("class_id")
    if not class_id:
        return {
            "success": True,
            "student_name": student["full_name"],
            "class_name": "Chưa gán lớp",
            "stats": {"total": 0, "submitted": 0, "unsubmitted": 0, "need_action": 0},
            "upcoming_assignments": []
        }

    with get_db() as conn:
        # Lấy thông tin lớp
        cls = conn.execute("SELECT name FROM classes WHERE id = ?", (class_id,)).fetchone()
        class_name = cls["name"] if cls else "Không xác định"

        # Lấy toàn bộ bài tập của lớp
        assignments = conn.execute(
            """
            SELECT id, title, description, subject, class_id, start_at, deadline,
                   allow_resubmit, allow_late_submission, resubmit_after_deadline,
                   submission_grace_period, max_images, max_file_size, status
            FROM assignments
            WHERE class_id = ?
            ORDER BY deadline ASC
            """,
            (class_id,)
        ).fetchall()

        now = get_server_now()
        total = len(assignments)
        submitted_count = 0
        unsubmitted_count = 0
        need_action_count = 0
        upcoming = []

        for row in assignments:
            assign_dict = dict(row)
            # Lấy submission mới nhất của học sinh này
            latest_sub = conn.execute(
                """
                SELECT id, submitted_at, status, attempt_number, is_late, late_seconds
                FROM submissions
                WHERE assignment_id = ? AND student_id = ?
                ORDER BY attempt_number DESC
                LIMIT 1
                """,
                (assign_dict["id"], student["id"])
            ).fetchone()

            sub_dict = dict(latest_sub) if latest_sub else None
            eval_res = evaluate_student_assignment_status(assign_dict, sub_dict, now)

            if eval_res["is_submitted"]:
                submitted_count += 1
            else:
                unsubmitted_count += 1
                if eval_res["can_submit"]:
                    need_action_count += 1

            if eval_res["can_submit"] and not eval_res["is_submitted"]:
                item = assign_dict.copy()
                item["status_info"] = eval_res
                upcoming.append(item)

        return {
            "success": True,
            "student_name": student["full_name"],
            "class_name": class_name,
            "stats": {
                "total": total,
                "submitted": submitted_count,
                "unsubmitted": unsubmitted_count,
                "need_action": need_action_count
            },
            "upcoming_assignments": upcoming[:5]
        }

@router.get("/assignments")
def get_student_assignments(filter: Optional[str] = "all", student: dict = Depends(require_student)):
    class_id = student.get("class_id")
    if not class_id:
        return {"success": True, "assignments": []}

    with get_db() as conn:
        assignments = conn.execute(
            """
            SELECT id, title, description, subject, class_id, start_at, deadline,
                   allow_resubmit, allow_late_submission, resubmit_after_deadline,
                   submission_grace_period, max_images, max_file_size, status
            FROM assignments
            WHERE class_id = ?
            ORDER BY deadline ASC
            """,
            (class_id,)
        ).fetchall()

        now = get_server_now()
        results = []

        for row in assignments:
            assign_dict = dict(row)
            latest_sub = conn.execute(
                """
                SELECT id, submitted_at, status, attempt_number, is_late, late_seconds
                FROM submissions
                WHERE assignment_id = ? AND student_id = ?
                ORDER BY attempt_number DESC
                LIMIT 1
                """,
                (assign_dict["id"], student["id"])
            ).fetchone()

            sub_dict = dict(latest_sub) if latest_sub else None
            eval_res = evaluate_student_assignment_status(assign_dict, sub_dict, now)

            # Lọc theo filter
            if filter == "unsubmitted" and eval_res["is_submitted"]:
                continue
            if filter == "submitted" and not eval_res["is_submitted"]:
                continue
            if filter == "overdue" and eval_res["status_key"] != "overdue_unsubmitted":
                continue

            assign_dict["status_info"] = eval_res
            assign_dict["latest_submission"] = sub_dict
            results.append(assign_dict)

        return {"success": True, "assignments": results}

@router.get("/assignments/{assignment_id}")
def get_assignment_detail(assignment_id: int, student: dict = Depends(require_student)):
    with get_db() as conn:
        assign = conn.execute(
            """
            SELECT id, title, description, subject, class_id, start_at, deadline,
                   allow_resubmit, allow_late_submission, resubmit_after_deadline,
                   submission_grace_period, max_images, max_file_size, status
            FROM assignments
            WHERE id = ?
            """,
            (assignment_id,)
        ).fetchone()

        if not assign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bài tập.")

        assign_dict = dict(assign)
        if assign_dict["class_id"] != student["class_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không thuộc lớp được giao bài tập này.")

        now = get_server_now()
        # Lấy lịch sử tất cả attempts của học sinh
        submissions = conn.execute(
            """
            SELECT id, submitted_at, status, attempt_number, is_late, late_seconds, created_at
            FROM submissions
            WHERE assignment_id = ? AND student_id = ?
            ORDER BY attempt_number DESC
            """,
            (assignment_id, student["id"])
        ).fetchall()

        sub_list = []
        for s in submissions:
            sub_dict = dict(s)
            # Lấy files của submission này
            files = conn.execute(
                """
                SELECT id, sanitized_filename, original_filename, mime_type, file_size, order_index
                FROM submission_files
                WHERE submission_id = ?
                ORDER BY order_index ASC, id ASC
                """,
                (sub_dict["id"],)
            ).fetchall()
            sub_dict["files"] = [dict(f) for f in files]
            sub_list.append(sub_dict)

        latest_sub = sub_list[0] if sub_list else None
        eval_res = evaluate_student_assignment_status(assign_dict, latest_sub, now)

        assign_dict["status_info"] = eval_res
        assign_dict["submissions_history"] = sub_list
        assign_dict["latest_submission"] = latest_sub

        return {"success": True, "assignment": assign_dict}

@router.post("/assignments/{assignment_id}/submit")
async def submit_assignment(
    assignment_id: int,
    files: List[UploadFile] = File(...),
    student: dict = Depends(require_student)
):
    """
    Nộp bài tập học sinh với kiểm tra bảo mật tuyệt đối:
    1. Kiểm tra quyền thuộc lớp
    2. Kiểm tra server deadline & trạng thái
    3. Kiểm tra số lượng ảnh và dung lượng
    4. Kiểm tra blacklist tên file, magic bytes, sanitize và re-encode
    5. Lưu attempt mới vào database
    """
    with get_db() as conn:
        assign = conn.execute(
            """
            SELECT id, title, description, subject, class_id, start_at, deadline,
                   allow_resubmit, allow_late_submission, resubmit_after_deadline,
                   submission_grace_period, max_images, max_file_size, status
            FROM assignments
            WHERE id = ?
            """,
            (assignment_id,)
        ).fetchone()

        if not assign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bài tập.")

        assign_dict = dict(assign)
        if assign_dict["class_id"] != student["class_id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không thuộc lớp được giao bài tập này.")

        # Lấy submission mới nhất để kiểm tra nộp lại
        latest_sub = conn.execute(
            """
            SELECT id, submitted_at, status, attempt_number, is_late, late_seconds
            FROM submissions
            WHERE assignment_id = ? AND student_id = ?
            ORDER BY attempt_number DESC
            LIMIT 1
            """,
            (assignment_id, student["id"])
        ).fetchone()

        now = get_server_now()
        is_eligible, reason, is_late, late_seconds = validate_submission_eligibility(
            assign_dict,
            dict(latest_sub) if latest_sub else None,
            now
        )

        if not is_eligible:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)

        # Kiểm tra số lượng ảnh
        max_images = assign_dict.get("max_images", 10)
        if len(files) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vui lòng chọn ít nhất 1 ảnh bài làm.")
        if len(files) > max_images:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Số lượng ảnh vượt quá giới hạn tối đa ({max_images} ảnh).")

        max_file_size = assign_dict.get("max_file_size", 10485760)

        # Xử lý an toàn từng ảnh
        processed_files = []
        for idx, file in enumerate(files):
            file_bytes = await file.read()
            processed = process_and_save_image(
                file_bytes=file_bytes,
                original_filename=file.filename or f"image_{idx+1}.jpg",
                max_file_size=max_file_size
            )
            processed["order_index"] = idx
            processed_files.append(processed)

        # Tính toán attempt_number
        current_attempt = (latest_sub["attempt_number"] + 1) if latest_sub else 1
        submitted_at_str = now.isoformat()

        # Tạo bản ghi submissions
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO submissions (
                assignment_id, student_id, submitted_at, status,
                attempt_number, is_late, late_seconds, created_at
            )
            VALUES (?, ?, ?, 'submitted', ?, ?, ?, ?)
            """,
            (
                assignment_id,
                student["id"],
                submitted_at_str,
                current_attempt,
                1 if is_late else 0,
                late_seconds,
                submitted_at_str
            )
        )
        submission_id = cursor.lastrowid

        # Lưu thông tin các file đã xử lý
        for pf in processed_files:
            cursor.execute(
                """
                INSERT INTO submission_files (
                    submission_id, storage_key, original_filename,
                    sanitized_filename, mime_type, file_size, order_index, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    submission_id,
                    pf["storage_key"],
                    pf["original_filename"],
                    pf["sanitized_filename"],
                    pf["mime_type"],
                    pf["file_size"],
                    pf["order_index"],
                    submitted_at_str
                )
            )

        return {
            "success": True,
            "message": "Nộp bài thành công!",
            "submission_id": submission_id,
            "attempt_number": current_attempt,
            "submitted_at": submitted_at_str,
            "is_late": is_late,
            "late_seconds": late_seconds,
            "total_images": len(processed_files)
        }
