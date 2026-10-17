import hmac
import hashlib
import json
import base64
import time
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status, Depends
import bcrypt

from app.config import SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES
from app.database import get_db

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = data.copy()
    exp = int(time.time()) + (ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    payload["exp"] = exp
    
    def b64_encode(obj):
        dumped = json.dumps(obj, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(dumped).decode("utf-8").rstrip("=")
        
    encoded_header = b64_encode(header)
    encoded_payload = b64_encode(payload)
    signature_base = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = hmac.new(SECRET_KEY.encode("utf-8"), signature_base, hashlib.sha256).digest()
    encoded_sig = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    return f"{encoded_header}.{encoded_payload}.{encoded_sig}"

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        signature_base = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), signature_base, hashlib.sha256).digest()
        actual_sig = base64.urlsafe_b64decode(sig_b64 + "=" * (-len(sig_b64) % 4))
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload_json = base64.urlsafe_b64decode(payload_b64 + "=" * (-len(payload_b64) % 4)).decode("utf-8")
        payload = json.loads(payload_json)
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None

def get_current_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = request.cookies.get("session_token")
    if not token:
        token = request.query_params.get("token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chưa đăng nhập hoặc phiên làm việc đã hết hạn"
        )
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn"
        )
    user_id = payload["sub"]
    with get_db() as conn:
        user = conn.execute("SELECT id, username, full_name, role, class_id, status FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Người dùng không tồn tại")
        user_dict = dict(user)
        if user_dict.get("status") == "locked":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa bởi Quản trị viên")
        return user_dict

def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Quyền truy cập bị từ chối: Chỉ dành cho Admin/Giáo viên")
    return current_user

def require_student(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Quyền truy cập bị từ chối: Chỉ dành cho Học sinh")
    return current_user
