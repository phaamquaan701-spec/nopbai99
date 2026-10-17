import os
from pathlib import Path
from datetime import timezone, timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = BASE_DIR / "data.db"

SECRET_KEY = os.environ.get("SECRET_KEY", "eduviet-secure-session-secret-key-2026-very-safe")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

# Múi giờ UTC+7 (Asia/Ho_Chi_Minh)
DEFAULT_TIMEZONE = timezone(timedelta(hours=7), name="Asia/Ho_Chi_Minh")

DEFAULT_MAX_FILE_SIZE_MB = 10
DEFAULT_MAX_FILE_SIZE_BYTES = DEFAULT_MAX_FILE_SIZE_MB * 1024 * 1024
DEFAULT_MAX_IMAGES = 10
DEFAULT_GRACE_PERIOD_SECONDS = 300

# Không chặn tên file để học sinh tải ảnh từ Zalo, Messenger, Download vẫn nộp được bình thường
FILENAME_BLACKLIST = []

# Hỗ trợ tất cả các định dạng ảnh phổ biến trên điện thoại (iPhone/Android) và máy tính
ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif",
    ".bmp", ".gif", ".tiff", ".tif", ".jfif", ".avif",
    ".svg", ".ico", ".raw", ".dng", ".cr2", ".nef"
}
