import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import re
import unicodedata
from pathlib import Path
from datetime import datetime
import openpyxl

from app.config import DEFAULT_TIMEZONE
from app.database import get_db, init_db
from app.security import hash_password

def remove_vietnamese_accents(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = re.sub(r"[\u0300-\u036f]", "", text)
    text = text.replace("đ", "d").replace("Đ", "D")
    return text.lower()

def generate_simple_username(full_name: str, stt: int) -> str:
    clean_name = remove_vietnamese_accents(full_name)
    parts = clean_name.split()
    last_name = parts[-1] if parts else "hs"
    return f"hs{stt:02d}_{last_name}"

def process_11a1(excel_path: str):
    init_db()
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    sheet = wb["Danh sách đăng ký"] if "Danh sách đăng ký" in wb.sheetnames else wb.active

    students = []
    for row_idx in range(2, sheet.max_row + 1):
        cells = sheet[row_idx]
        vals = [str(c.value).strip() if c.value is not None else "" for c in cells]
        if len(vals) < 2:
            continue
        stt_str = vals[0]
        name = vals[1]
        if not name or name.lower() == "none" or name.startswith("Họ và tên"):
            continue

        stt = int(stt_str) if stt_str.isdigit() else len(students) + 1
        username = generate_simple_username(name, stt)
        password = "123456"

        students.append({
            "stt": stt,
            "full_name": name,
            "username": username,
            "password": password
        })

    now = datetime.now(DEFAULT_TIMEZONE)
    class_name = "11A1"

    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Tạo lớp 11A1
        cursor.execute("SELECT id FROM classes WHERE name = ?", (class_name,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("INSERT INTO classes (name, created_at) VALUES (?, ?)", (class_name, now.isoformat()))
            class_id = cursor.lastrowid
        else:
            class_id = row["id"]

        # 2. Thêm hoặc cập nhật tài khoản học sinh 11A1
        pwd_hash = hash_password("123456")
        for s in students:
            cursor.execute("SELECT id FROM users WHERE username = ?", (s["username"],))
            existing = cursor.fetchone()
            if existing:
                cursor.execute(
                    "UPDATE users SET full_name = ?, password_hash = ?, class_id = ?, status = 'active' WHERE id = ?",
                    (s["full_name"], pwd_hash, class_id, existing["id"])
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO users (username, password_hash, full_name, role, class_id, status, created_at)
                    VALUES (?, ?, ?, 'student', ?, 'active', ?)
                    """,
                    (s["username"], pwd_hash, s["full_name"], class_id, now.isoformat())
                )

    print(f"Hệ thống: Đã cập nhật 44 tài khoản học sinh Lớp {class_name}.")

if __name__ == "__main__":
    p = r"c:\Users\quanp\Documents\web\Danh_sach_hoc_sinh_dang_ky_mon.xlsx"
    process_11a1(p)
