from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from pydantic import BaseModel
from app.database import get_db
from app.security import verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(req: LoginRequest, response: Response):
    username = req.username.strip()
    with get_db() as conn:
        user = conn.execute(
            """
            SELECT u.id, u.username, u.password_hash, u.full_name, u.role, u.class_id, u.status, c.name as class_name
            FROM users u
            LEFT JOIN classes c ON u.class_id = c.id
            WHERE u.username = ?
            """,
            (username,)
        ).fetchone()

        if not user or not verify_password(req.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tên đăng nhập hoặc mật khẩu không chính xác."
            )

        if user["status"] == "locked":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản của bạn đã bị khóa. Vui lòng liên hệ Giáo viên/Quản trị viên."
            )

        token = create_access_token({"sub": user["id"], "role": user["role"], "username": user["username"]})
        
        # Thiết lập Cookie HttpOnly an toàn
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 7
        )

        return {
            "success": True,
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "role": user["role"],
                "class_id": user["class_id"],
                "class_name": user["class_name"]
            }
        }

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="session_token")
    return {"success": True, "message": "Đã đăng xuất thành công."}

@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        user = conn.execute(
            """
            SELECT u.id, u.username, u.full_name, u.role, u.class_id, u.status, c.name as class_name
            FROM users u
            LEFT JOIN classes c ON u.class_id = c.id
            WHERE u.id = ?
            """,
            (current_user["id"],)
        ).fetchone()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại")
        return {"success": True, "user": dict(user)}
