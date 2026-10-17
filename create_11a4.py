# -*- coding: utf-8 -*-
import sys
import os
import re
import unicodedata
import sqlite3
import openpyxl
from pathlib import Path

# Đảm bảo utf-8 cho stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.config import DB_PATH, DEFAULT_TIMEZONE
from app.security import hash_password
from datetime import datetime

raw_list = [
    (1, "Đồng Duy Anh"),
    (2, "Lương Thị Ngọc Ánh"),
    (3, "Nguyễn Phương Anh"),
    (4, "Vũ Duy Anh"),
    (5, "Lại Ngọc Bảo"),
    (6, "Vũ Quang Bình"),
    (7, "Phạm Thị Thùy Chi"),
    (8, "Nguyễn Thu Cúc"),
    (9, "Bùi Trung Dũng"),
    (10, "Nguyễn Quang Dũng"),
    (11, "Nguyễn Tiến Dũng"),
    (12, "Lê Anh Đức"),
    (13, "Nguyễn Thanh Hà"),
    (14, "Nguyễn Hoàng Hải"),
    (15, "Trần Hoàng Hải"),
    (16, "Chu Thúy Hiền"),
    (17, "Nguyễn Vinh Hiển"),
    (18, "Trương Minh Hiếu"),
    (19, "Vũ Trung Hiêu"),
    (20, "Đỗ Mai Phương"),
    (21, "Ngô Hương Huyền"),
    (22, "Nguyễn Đình Hưng"),
    (23, "Nguyễn Quốc Khánh"),
    (24, "Nguyễn Trần Thảo Lâm"),
    (25, "Phạm Phương Linh"),
    (26, "Phạm Trần Lộc"),
    (27, "Nguyễn Thành Luân"),
    (28, "Nguyễn Công Minh"),
    (29, "Trần Thị Trà My"),
    (30, "Nguyễn Hồng Anh"),
    (31, "Lục Phạm Bảo Nam"),
    (32, "Ngô Lam Phương"),
    (33, "Vũ Xuân Quý"),
    (34, "Chu Hải Sơn"),
    (35, "Nguyễn Ngọc Giai Tâm"),
    (36, "Bùi Nam Thanh"),
    (37, "Lưu Vương Đức Thành"),
    (38, "Phạm Bá Thông"),
    (39, "Nguyễn Minh Thuận"),
    (40, "Trần Thị Trang"),
    (41, "Nguyễn Tuấn Tú"),
    (42, "Vũ Hùng Vương"),
    (43, "Đào Thị Xuân")
]

def vn_to_ascii(text: str) -> str:
    """Chuyển tiếng Việt sang không dấu chuẩn xác"""
    patterns = {
        '[àáảãạăằắẳẵặâầấẩẫậ]': 'a',
        '[ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬ]': 'A',
        '[èéẻẽẹêềếểễệ]': 'e',
        '[ÈÉẺẼẸÊỀẾỂỄỆ]': 'E',
        '[ìíỉĩị]': 'i',
        '[ÌÍỈĨỊ]': 'I',
        '[òóỏõọôồốổỗộơờớởỡợ]': 'o',
        '[ÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢ]': 'O',
        '[ùúủũụưừứửữự]': 'u',
        '[ÙÚỦŨỤƯỪỨỬỮỰ]': 'U',
        '[ỳýỷỹỵ]': 'y',
        '[ỲÝỶỸỴ]': 'Y',
        '[đ]': 'd',
        '[Đ]': 'D'
    }
    output = text
    for regex, replace in patterns.items():
        output = re.sub(regex, replace, output)
    # Loại bỏ các ký tự dấu tổ hợp còn sót
    output = unicodedata.normalize('NFD', output)
    output = re.sub(r'[\u0300-\u036f]', '', output)
    return output.lower().strip()

def create_username(full_name: str) -> str:
    ascii_name = vn_to_ascii(full_name)
    parts = ascii_name.split()
    if not parts:
        return "hs_11a4"
    last_name = parts[-1]
    initials = "".join([p[0] for p in parts[:-1]])
    return f"{last_name}_{initials}_11a4"

students_data = []
for stt, name in raw_list:
    u = create_username(name)
    students_data.append({
        "stt": stt,
        "full_name": name,
        "username": u,
        "password": "123456"
    })

print("Danh sách 5 username đầu tiên:")
for s in students_data[:5]:
    print(f"{s['stt']:2d}. {s['full_name']} -> {s['username']}")

# Cập nhật Database
conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()
now = datetime.now(DEFAULT_TIMEZONE).isoformat()

# Lớp 11A4
cursor.execute("SELECT id FROM classes WHERE name = '11A4'")
row_11a4 = cursor.fetchone()
if not row_11a4:
    cursor.execute("INSERT INTO classes (name, created_at) VALUES ('11A4', ?)", (now,))
    class_id_11a4 = cursor.lastrowid
else:
    class_id_11a4 = row_11a4[0]

# Xóa các học sinh 11A4 cũ (nếu có lỗi chính tả username trước đó) và nạp lại chuẩn
cursor.execute("DELETE FROM users WHERE class_id = ? AND role = 'student'", (class_id_11a4,))

pwd_hash = hash_password("123456")
for s in students_data:
    cursor.execute(
        """
        INSERT INTO users (username, password_hash, full_name, role, class_id, status, created_at)
        VALUES (?, ?, ?, 'student', ?, 'active', ?)
        """,
        (s["username"], pwd_hash, s["full_name"], class_id_11a4, now)
    )

# Thêm admin Cuong
admin_pwd = hash_password("mybeovl")
for u in ["Cuong", "cuong"]:
    cursor.execute("SELECT id FROM users WHERE username = ?", (u,))
    if not cursor.fetchone():
        cursor.execute(
            """
            INSERT INTO users (username, password_hash, full_name, role, class_id, status, created_at)
            VALUES (?, ?, ?, 'admin', NULL, 'active', ?)
            """,
            (u, admin_pwd, "Lợn My", now)
        )
    else:
        cursor.execute("UPDATE users SET password_hash = ?, full_name = ? WHERE username = ?", (admin_pwd, "Lợn My", u))

conn.commit()
conn.close()
print("Cập nhật Database thành công!")

# Xuất Excel
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "11A4"
ws.append(["STT", "Họ và tên", "Tên đăng nhập (Username)", "Mật khẩu"])
for s in students_data:
    ws.append([s["stt"], s["full_name"], s["username"], s["password"]])

ws.column_dimensions["A"].width = 8
ws.column_dimensions["B"].width = 28
ws.column_dimensions["C"].width = 24
ws.column_dimensions["D"].width = 16

excel_out = Path(r"c:\Users\quanp\Documents\web\Tai_khoan_11A4.xlsx")
wb.save(str(excel_out))
print(f"Đã xuất Excel: {excel_out}")

# Xuất file Text Zalo
txt_out = Path(r"c:\Users\quanp\Documents\web\Tai_khoan_11A4.txt")
lines = [
    "DANH SÁCH TÀI KHOẢN NỘP BÀI TẬP - LỚP 11A4",
    "Mật khẩu chung cho cả lớp: 123456",
    "=" * 60,
    f"{'STT':<4} | {'Họ và tên':<24} | {'Tên đăng nhập':<18} | Mật khẩu",
    "-" * 60
]
for s in students_data:
    lines.append(f"{s['stt']:<4} | {s['full_name']:<24} | {s['username']:<18} | {s['password']}")
lines.append("=" * 60)
lines.append("\nHướng dẫn học sinh: Truy cập vào link web, nhập Tên đăng nhập và Mật khẩu ở trên để vào nộp bài.")
txt_out.write_text("\n".join(lines), encoding="utf-8")
print(f"Đã xuất file Text: {txt_out}")
