from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from app.config import DEFAULT_TIMEZONE

def get_server_now() -> datetime:
    """Lấy thời gian chuẩn hiện tại trên server múi giờ Asia/Ho_Chi_Minh (UTC+7)"""
    return datetime.now(DEFAULT_TIMEZONE)

def parse_iso_time(iso_str: str) -> datetime:
    """Parse chuỗi ISO datetime sang datetime object kèm múi giờ UTC+7"""
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=DEFAULT_TIMEZONE)
    else:
        dt = dt.astimezone(DEFAULT_TIMEZONE)
    return dt

def format_duration(seconds: int) -> str:
    """Định dạng số giây thành chuỗi giờ phút dễ đọc tiếng Việt"""
    if seconds < 0:
        seconds = 0
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days} ngày")
    if hours > 0:
        parts.append(f"{hours} giờ")
    if minutes > 0:
        parts.append(f"{minutes} phút")
    if not parts:
        parts.append(f"{secs} giây")
    return " ".join(parts)

def evaluate_student_assignment_status(
    assignment: dict,
    latest_submission: Optional[dict] = None,
    now: Optional[datetime] = None
) -> dict:
    """
    Xác định trạng thái bài tập của một học sinh theo quy tắc thứ tự ưu tiên:
    1. Chưa mở (now < start_at)
    2. Đã đóng (assignment.status == 'closed')
    3. Quá hạn - chưa nộp (now > deadline và chưa có submission)
    4. Nộp muộn (đã nộp sau deadline)
    5. Đã nộp (đã nộp trước hoặc đúng deadline)
    6. Chưa nộp (start_at <= now <= deadline và chưa nộp)

    Cảnh báo phụ: 'is_near_deadline' nếu <= 24 giờ trước deadline
    """
    if now is None:
        now = get_server_now()

    start_at = parse_iso_time(assignment["start_at"])
    deadline = parse_iso_time(assignment["deadline"])
    is_closed = assignment.get("status") == "closed"
    allow_late = bool(assignment.get("allow_late_submission", 0))
    allow_resubmit = bool(assignment.get("allow_resubmit", 1))
    resubmit_after_deadline = bool(assignment.get("resubmit_after_deadline", 0))

    has_submitted = latest_submission is not None
    is_late_submission = bool(latest_submission.get("is_late", 0)) if has_submitted else False

    main_status = ""
    status_text = ""
    status_badge_class = ""
    can_submit = False
    warning_badge = None
    time_info = ""

    # 1. Chưa mở
    if now < start_at:
        main_status = "not_started"
        status_text = "Chưa mở"
        status_badge_class = "badge-gray"
        can_submit = False
        time_info = f"Bắt đầu nhận bài: {start_at.strftime('%d/%m/%Y %H:%M')}"

    # 2. Đã đóng thủ công bởi Admin
    elif is_closed:
        main_status = "closed"
        status_text = "Đã đóng"
        status_badge_class = "badge-locked"
        can_submit = False
        time_info = "Bài tập đã bị khóa bởi Quản trị viên"

    # Đã có bài nộp
    elif has_submitted:
        submitted_at = parse_iso_time(latest_submission["submitted_at"])
        sub_time_str = submitted_at.strftime("%H:%M ngày %d/%m")
        attempt_num = latest_submission.get("attempt_number", 1)

        if is_late_submission:
            # 4. Đã nộp muộn
            main_status = "submitted_late"
            late_sec = latest_submission.get("late_seconds", 0)
            status_text = "Đã nộp muộn"
            status_badge_class = "badge-late"
            time_info = f"Nộp lúc {sub_time_str} (Muộn {format_duration(late_sec)}) - Lần {attempt_num}"
        else:
            # 5. Đã nộp đúng hạn
            main_status = "submitted"
            status_text = "Đã nộp"
            status_badge_class = "badge-success"
            time_info = f"Nộp lúc {sub_time_str} (Đúng hạn) - Lần {attempt_num}"

        # Kiểm tra xem có được nộp lại không
        if allow_resubmit:
            if now <= deadline:
                can_submit = True
            elif allow_late and (resubmit_after_deadline or allow_late):
                can_submit = True
            else:
                can_submit = False
        else:
            can_submit = False

    # Chưa nộp bài nào
    else:
        if now > deadline:
            # 3. Quá hạn – chưa nộp
            main_status = "overdue_unsubmitted"
            status_text = "Quá hạn – Chưa nộp"
            status_badge_class = "badge-danger"
            time_info = f"Hết hạn lúc {deadline.strftime('%d/%m/%Y %H:%M')}"
            # Nếu bật allow_late_submission thì vẫn cho nộp muộn
            can_submit = allow_late
        else:
            # 6. Chưa nộp (đang trong hạn)
            main_status = "unsubmitted"
            status_text = "Chưa nộp"
            status_badge_class = "badge-warning"
            remaining_seconds = int((deadline - now).total_seconds())
            time_info = f"Còn {format_duration(remaining_seconds)}"
            can_submit = True

    # Cảnh báo phụ: Sắp hết hạn (<= 24 giờ trước deadline và chưa quá hạn)
    if start_at <= now <= deadline and not is_closed:
        diff_sec = int((deadline - now).total_seconds())
        if diff_sec <= 86400:
            warning_badge = f"⚠ Sắp hết hạn – còn {format_duration(diff_sec)}"

    return {
        "status_key": main_status,
        "status_label": status_text,
        "status_badge_class": status_badge_class,
        "can_submit": can_submit,
        "warning_badge": warning_badge,
        "time_info": time_info,
        "is_submitted": has_submitted,
        "allow_resubmit": allow_resubmit,
        "allow_late_submission": allow_late
    }

def validate_submission_eligibility(
    assignment: dict,
    latest_submission: Optional[dict] = None,
    now: Optional[datetime] = None
) -> Tuple[bool, str, bool, int]:
    """
    Kiểm tra tính hợp lệ của việc nộp bài ở server.
    Trả về: (is_eligible, reason, is_late, late_seconds)
    """
    if now is None:
        now = get_server_now()

    start_at = parse_iso_time(assignment["start_at"])
    deadline = parse_iso_time(assignment["deadline"])
    is_closed = assignment.get("status") == "closed"
    allow_late = bool(assignment.get("allow_late_submission", 0))
    allow_resubmit = bool(assignment.get("allow_resubmit", 1))
    resubmit_after_deadline = bool(assignment.get("resubmit_after_deadline", 0))
    grace_period = assignment.get("submission_grace_period", 300)

    if is_closed:
        return False, "Bài tập đã bị đóng bởi Quản trị viên. Không thể nộp bài.", False, 0

    if now < start_at:
        return False, f"Bài tập chưa đến thời gian mở nhận bài ({start_at.strftime('%d/%m/%Y %H:%M')}).", False, 0

    has_submitted = latest_submission is not None
    if has_submitted and not allow_resubmit:
        return False, "Bài tập này không cho phép nộp lại.", False, 0

    # Kiểm tra thời hạn
    is_late = False
    late_seconds = 0

    if now > deadline:
        # Kiểm tra grace period
        diff_from_deadline = int((now - deadline).total_seconds())
        
        if diff_from_deadline <= grace_period:
            # Được tính trong thời gian ân hạn grace period khi upload dở
            is_late = False
            late_seconds = 0
        else:
            is_late = True
            late_seconds = diff_from_deadline

            if not allow_late:
                return False, f"Đã quá hạn nộp bài ({deadline.strftime('%d/%m/%Y %H:%M')}) và bài tập không cho phép nộp muộn.", False, 0

            if has_submitted and not resubmit_after_deadline and not allow_late:
                return False, "Không được phép nộp lại sau khi đã quá hạn.", False, 0

    return True, "Hợp lệ", is_late, late_seconds
