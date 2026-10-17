"""
image_service.py — Xử lý ảnh và lưu trữ.

Khi chạy trên Vercel (có BLOB_READ_WRITE_TOKEN):
  - Ảnh được upload lên Vercel Blob Storage.
  - storage_key = URL đầy đủ của blob (ví dụ: https://xxx.vercel-storage.com/abc.jpg).

Khi chạy local (không có BLOB_READ_WRITE_TOKEN):
  - Ảnh được lưu vào thư mục storage/uploads/ như cũ.
  - storage_key = tên file ngắn (ví dụ: abc123.jpg).
"""

import io
import os
import uuid
import re
import urllib.request
from pathlib import Path
from typing import List, Tuple
from fastapi import UploadFile, HTTPException, status
from PIL import Image, ImageOps

# Tự động kích hoạt hỗ trợ ảnh HEIC/HEIF (chụp từ iPhone)
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass

from app.config import (
    UPLOAD_DIR,
    FILENAME_BLACKLIST,
    ALLOWED_EXTENSIONS
)

BLOB_TOKEN = os.environ.get("BLOB_READ_WRITE_TOKEN", "")
USE_BLOB = bool(BLOB_TOKEN)


def check_filename_blacklist(filename: str) -> None:
    """
    Không chặn tên file để học sinh nộp ảnh tải từ Zalo/Messenger/Download thuận tiện.
    """
    pass


def check_magic_bytes(content: bytes) -> str:
    """
    Kiểm tra chữ ký nhị phân để xác định file ảnh hợp lệ.
    Hỗ trợ mọi định dạng: JPEG, PNG, WEBP, HEIC, HEIF, BMP, GIF, TIFF, AVIF,...
    """
    if len(content) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File quá ngắn hoặc bị lỗi, không thể xác định định dạng ảnh."
        )

    # Thử nhận diện bằng Pillow
    try:
        with Image.open(io.BytesIO(content)) as img:
            if img.format:
                return img.format
    except Exception:
        pass

    # Chữ ký nhị phân các định dạng ảnh phổ biến
    if content.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if content.startswith(b"RIFF") and len(content) >= 12 and content[8:12] == b"WEBP":
        return "WEBP"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "GIF"
    if content.startswith(b"BM"):
        return "BMP"
    if content.startswith((b"II*\x00", b"MM\x00*")):
        return "TIFF"
    if len(content) >= 12 and content[4:8] == b"ftyp":
        return "HEIF"

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Nội dung file không phải là ảnh hợp lệ hoặc file bị lỗi. Vui lòng chọn file ảnh (JPG, PNG, HEIC, WEBP, GIF, BMP...)."
    )


def _upload_to_blob(image_bytes: bytes, filename: str) -> str:
    """Upload ảnh lên Vercel Blob, trả về public URL."""
    import urllib.request
    import json

    url = f"https://blob.vercel-storage.com/{filename}"
    req = urllib.request.Request(
        url,
        data=image_bytes,
        method="PUT",
        headers={
            "Authorization": f"Bearer {BLOB_TOKEN}",
            "Content-Type": "image/jpeg",
            "x-content-type": "image/jpeg",
        }
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode())
        return result["url"]


def _save_to_local(image_bytes: bytes, filename: str) -> str:
    """Lưu ảnh vào local storage, trả về tên file ngắn."""
    target_path = UPLOAD_DIR / filename
    target_path.write_bytes(image_bytes)
    return filename


def process_and_save_image(
    file_bytes: bytes,
    original_filename: str,
    max_file_size: int = 10485760
) -> dict:
    """
    Pipeline kiểm duyệt, decode, xoay EXIF, resize, sanitize và re-encode ảnh an toàn:
    1. Kiểm tra blacklist tên file
    2. Kiểm tra dung lượng
    3. Kiểm tra magic bytes
    4. Decode bằng Pillow
    5. Tự động xoay theo EXIF orientation
    6. Resize nếu kích thước > 2560px
    7. Re-encode thành JPEG sạch chất lượng cao
    8. Lưu vào Vercel Blob (production) hoặc local (dev)
    """
    # 1. Kiểm tra tên file blacklist
    check_filename_blacklist(original_filename)

    # 2. Kiểm tra dung lượng file
    if len(file_bytes) > max_file_size:
        max_mb = max_file_size / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ảnh '{original_filename}' vượt quá dung lượng cho phép ({max_mb:.1f} MB)."
        )

    # 3. Kiểm tra extension (nếu có)
    ext = Path(original_filename).suffix.lower()
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng đuôi file '{ext}' không được hỗ trợ. Hệ thống hỗ trợ tất cả các loại ảnh: JPG, PNG, HEIC, WEBP, GIF, BMP, TIFF, JFIF..."
        )

    # 4. Kiểm tra magic bytes / chữ ký ảnh
    detected_format = check_magic_bytes(file_bytes)

    # 5. Decode bằng Pillow để kiểm tra ảnh thực
    try:
        image_stream = io.BytesIO(file_bytes)
        with Image.open(image_stream) as img:
            img.verify()  # Kiểm tra tính toàn vẹn của file ảnh
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể giải mã file ảnh '{original_filename}'. File có thể bị hỏng hoặc không phải là ảnh hợp lệ."
        )

    # 6. Mở lại để xử lý (sau khi verify stream bị đóng)
    try:
        image_stream = io.BytesIO(file_bytes)
        with Image.open(image_stream) as img:
            # Chọn frame đầu tiên nếu là ảnh nhiều frame (GIF, TIFF)
            try:
                img.seek(0)
            except Exception:
                pass

            # Tự động xoay theo EXIF orientation (tránh ảnh bị chụp ngược/nghiêng trên điện thoại)
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            # Chuyển đổi sang mode RGB nếu cần (tránh lỗi khi lưu CMYK, P, RGBA sang JPEG)
            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img_rgba = img.convert("RGBA")
                    background.paste(img_rgba, mask=img_rgba.split()[-1])
                else:
                    background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Resize nếu kích thước quá lớn (> 2560px ở cạnh dài nhất) để tối ưu lưu trữ
            max_dimension = 2560
            width, height = img.size
            if width > max_dimension or height > max_dimension:
                if width > height:
                    new_width = max_dimension
                    new_height = int(height * (max_dimension / width))
                else:
                    new_height = max_dimension
                    new_width = int(width * (max_dimension / height))
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Re-encode sạch sang JPEG với chất lượng 85 (giữ chữ viết tay cực kỳ rõ nét)
            # Lưu ý: Không copy metadata/EXIF ban đầu để triệt tiêu mã độc ẩn trong metadata
            unique_filename = f"{uuid.uuid4().hex}.jpg"
            output_stream = io.BytesIO()
            img.save(
                output_stream,
                format="JPEG",
                quality=85,
                optimize=True,
                progressive=True
            )
            saved_bytes = output_stream.getvalue()
            img_width, img_height = img.size

        # Lưu vào Blob hoặc local
        if USE_BLOB:
            storage_key = _upload_to_blob(saved_bytes, unique_filename)
        else:
            storage_key = _save_to_local(saved_bytes, unique_filename)

        # Tên file hiển thị sạch cho người dùng
        safe_basename = re.sub(r"[^\w\.\-]", "_", original_filename)

        return {
            "storage_key": storage_key,
            "original_filename": original_filename,
            "sanitized_filename": safe_basename,
            "mime_type": "image/jpeg",
            "file_size": len(saved_bytes),
            "width": img_width,
            "height": img_height
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi trong quá trình xử lý và lưu trữ ảnh: {str(e)}"
        )


def get_image_bytes(storage_key: str) -> bytes:
    """
    Tải nội dung ảnh từ storage_key.
    - Nếu storage_key là URL (Vercel Blob): tải về qua HTTP.
    - Nếu là tên file ngắn: đọc từ local filesystem.
    """
    if storage_key.startswith("http://") or storage_key.startswith("https://"):
        with urllib.request.urlopen(storage_key) as resp:
            return resp.read()
    else:
        physical_path = (UPLOAD_DIR / storage_key).resolve()
        if not str(physical_path).startswith(str(UPLOAD_DIR.resolve())):
            raise ValueError("Đường dẫn file không hợp lệ.")
        return physical_path.read_bytes()
