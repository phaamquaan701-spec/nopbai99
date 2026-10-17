from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from app.config import UPLOAD_DIR
from app.database import get_db
from app.security import get_current_user

router = APIRouter(prefix="/api/files", tags=["Files"])

@router.get("/{file_id}")
def get_submission_file(file_id: int, current_user: dict = Depends(get_current_user)):
    """
    Truy xuất file ảnh từ Private Storage với xác thực quyền (Bảo mật tuyệt đối chống IDOR):
    - Admin: Có quyền xem mọi bài nộp của mọi học sinh.
    - Học sinh: CHỈ được xem ảnh thuộc về submission của chính mình.
    """
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT sf.id, sf.storage_key, sf.sanitized_filename, sf.mime_type, s.student_id
            FROM submission_files sf
            JOIN submissions s ON sf.submission_id = s.id
            WHERE sf.id = ?
            """,
            (file_id,)
        ).fetchone()

        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy file ảnh yêu cầu.")

        # Kiểm tra IDOR: Nếu không phải Admin và không phải chính chủ
        if current_user["role"] != "admin" and row["student_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Truy cập bị từ chối: Bạn không có quyền xem bài làm của học sinh khác."
            )

        storage_key = row["storage_key"]
        # Ngăn ngừa Directory Traversal
        safe_path = (UPLOAD_DIR / storage_key).resolve()
        if not str(safe_path).startswith(str(UPLOAD_DIR.resolve())):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Đường dẫn file không hợp lệ.")

        if not safe_path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File vật lý không tồn tại trên hệ thống lưu trữ.")

        return FileResponse(
            path=safe_path,
            media_type=row["mime_type"],
            filename=row["sanitized_filename"]
        )
