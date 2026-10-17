# -*- coding: utf-8 -*-
"""
Công cụ xuất tất cả ảnh của một bài tập (task) ra 1 file ZIP chứa ảnh.
Chạy trực tiếp trong thư mục nopbai: python xuat_anh_task.py
"""
import os
import sys
import sqlite3
import zipfile
import re
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data.db"
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"

def sanitize_name(name: str) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return name.strip() or "hoc_sinh"

def get_assignments():
    if not DB_PATH.exists():
        print(f"[!] Không tìm thấy database tại: {DB_PATH}")
        return []
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    assignments = conn.execute("""
        SELECT a.id, a.title, a.subject, c.name as class_name,
               (SELECT COUNT(DISTINCT s.student_id) FROM submissions s WHERE s.assignment_id = a.id) as sub_count
        FROM assignments a
        JOIN classes c ON a.class_id = c.id
        ORDER BY a.id DESC
    """).fetchall()
    conn.close()
    return assignments

def export_assignment(assign_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    assign = conn.execute("""
        SELECT a.id, a.title, a.subject, c.name as class_name
        FROM assignments a
        JOIN classes c ON a.class_id = c.id
        WHERE a.id = ?
    """, (assign_id,)).fetchone()

    if not assign:
        print(f"[!] Không tìm thấy bài tập có ID {assign_id}")
        conn.close()
        return

    # Lấy các file bài nộp mới nhất của từng học sinh
    query = """
    SELECT 
        u.id as student_id, u.full_name as student_name, u.username,
        s.id as submission_id, s.attempt_number, s.submitted_at, s.is_late,
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
    rows = conn.execute(query, (assign_id, assign_id)).fetchall()
    conn.close()

    if not rows:
        print(f"\n[!] Bài tập '{assign['title']}' (Lớp {assign['class_name']}) hiện CHƯA CÓ ảnh bài nộp nào.")
        return

    clean_subj = sanitize_name(assign["subject"]).replace(" ", "_")
    clean_class = sanitize_name(assign["class_name"]).replace(" ", "_")
    clean_title = sanitize_name(assign["title"]).replace(" ", "_")
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"BaiNop_{clean_subj}_{clean_class}_{clean_title}_{now_str}.zip"
    zip_path = BASE_DIR / zip_name

    # Gom nhóm theo học sinh
    students_data = {}
    for r in rows:
        st_id = r["student_id"]
        if st_id not in students_data:
            students_data[st_id] = {
                "name": r["student_name"],
                "username": r["username"],
                "is_late": r["is_late"],
                "submitted_at": r["submitted_at"],
                "files": []
            }
        students_data[st_id]["files"].append(r)

    manifest_lines = [
        f"BÁO CÁO BÀI NỘP: {assign['title']} ({assign['subject']})",
        f"Lớp: {assign['class_name']}",
        f"Thời gian xuất: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        f"Tổng số học sinh nộp ảnh: {len(students_data)}",
        "=" * 60,
        f"{'STT':<4} | {'Họ và tên':<24} | {'Tài khoản':<16} | {'Trạng thái':<12} | {'Số ảnh':<6}",
        "-" * 60,
    ]

    total_images_saved = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        stt = 1
        for st_id, data in students_data.items():
            status_str = "Nộp muộn" if data["is_late"] else "Đúng hạn"
            manifest_lines.append(
                f"{stt:<4} | {data['name']:<24} | {data['username']:<16} | {status_str:<12} | {len(data['files']):<6}"
            )
            safe_st_name = sanitize_name(data["name"]).replace(" ", "_")
            folder_name = f"{stt:02d}_{safe_st_name}_{data['username']}"

            for idx, f in enumerate(data["files"], start=1):
                storage_key = f["storage_key"]
                physical_file = (UPLOAD_DIR / storage_key).resolve()
                if physical_file.is_file():
                    ext = physical_file.suffix or ".jpg"
                    arcname = f"{folder_name}/trang_{idx:02d}{ext}"
                    zf.write(physical_file, arcname=arcname)
                    total_images_saved += 1
            stt += 1

        manifest_lines.append("=" * 60)
        zf.writestr("danh_sach_nop_bai.txt", "\n".join(manifest_lines).encode("utf-8-sig"))

    print(f"\n[✓] XUẤT THÀNH CÔNG FILE ZIP:")
    print(f"    - Tệp tin: {zip_path.name}")
    print(f"    - Đường dẫn: {zip_path}")
    print(f"    - Tổng số học sinh: {len(students_data)}")
    print(f"    - Tổng số ảnh đã đóng gói: {total_images_saved}")
    print(f"    - Dung lượng file ZIP: {zip_path.stat().st_size / 1024:.1f} KB")

def main():
    print("=" * 60)
    print("   CÔNG CỤ XUẤT TẤT CẢ ẢNH BÀI LÀM CỦA TASK RA FILE ZIP")
    print("=" * 60)
    print(f"Thư mục làm việc: {BASE_DIR}")
    print()

    assignments = get_assignments()
    if not assignments:
        print("[!] Không tìm thấy bài tập nào trong cơ sở dữ liệu.")
        return

    print("DANH SÁCH BÀI TẬP HIỆN CÓ:")
    for idx, a in enumerate(assignments, start=1):
        print(f"  [{idx}] ID {a['id']} - Lớp {a['class_name']}: {a['title']} ({a['subject']}) - Đã nộp: {a['sub_count']} HS")

    print("\nNhập số thứ tự bài tập muốn xuất ảnh (hoặc gõ 'all' để xuất tất cả, 'q' để thoát):")
    try:
        choice = input("👉 Lựa chọn: ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if choice.lower() == 'q' or not choice:
        print("Đã thoát.")
        return

    if choice.lower() == 'all':
        for a in assignments:
            export_assignment(a["id"])
    elif choice.isdigit():
        num = int(choice)
        if 1 <= num <= len(assignments):
            export_assignment(assignments[num - 1]["id"])
        else:
            print("[!] Lựa chọn không hợp lệ.")
    else:
        print("[!] Lựa chọn không hợp lệ.")

if __name__ == "__main__":
    main()
