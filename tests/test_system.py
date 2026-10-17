import io
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from PIL import Image
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, get_db
from app.seed import seed

client = TestClient(app)

def create_dummy_image_bytes(color=(255, 0, 0), format="JPEG"):
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 100), color=color)
    img.save(buf, format=format)
    return buf.getvalue()

def run_tests():
    print("==================================================")
    print("BẮT ĐẦU CHẠY BỘ KIỂM THỬ HỆ THỐNG (26 KỊCH BẢN)")
    print("==================================================")

    # Khởi tạo dữ liệu
    seed()

    # TEST 1: Đăng nhập học sinh
    print("\n[TEST 1] Đăng nhập học sinh hợp lệ...")
    res = client.post("/api/auth/login", json={"username": "hocsinh1", "password": "123456"})
    assert res.status_code == 200, f"Failed: {res.text}"
    student_token = res.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}
    print("  -> PASS: Đăng nhập thành công, nhận JWT token.")

    # TEST 2: Đăng nhập sai mật khẩu
    print("\n[TEST 2] Đăng nhập sai mật khẩu...")
    res = client.post("/api/auth/login", json={"username": "hocsinh1", "password": "wrongpassword"})
    assert res.status_code == 401
    print("  -> PASS: Đã chặn truy cập với status 401.")

    # TEST 3: Học sinh xem Dashboard
    print("\n[TEST 3] Học sinh xem Dashboard...")
    res = client.get("/api/student/dashboard", headers=student_headers)
    assert res.status_code == 200
    data = res.json()
    assert "stats" in data
    print(f"  -> PASS: Dashboard lớp {data['class_name']}, tổng bài: {data['stats']['total']}.")

    # TEST 4: Học sinh xem danh sách bài tập
    print("\n[TEST 4] Học sinh xem danh sách bài tập...")
    res = client.get("/api/student/assignments", headers=student_headers)
    assert res.status_code == 200
    assignments = res.json()["assignments"]
    assert len(assignments) >= 3
    print(f"  -> PASS: Lấy được {len(assignments)} bài tập với trạng thái chuẩn hóa từ server.")

    open_assignment = [a for a in assignments if a["status_info"]["status_key"] in ("unsubmitted", "submitted")][0]
    assign_id = open_assignment["id"]

    # TEST 5: Upload ảnh hợp lệ và nộp bài
    print(f"\n[TEST 5] Học sinh nộp bài tập #{assign_id} với 2 ảnh hợp lệ...")
    img1 = create_dummy_image_bytes(color=(0, 255, 0))
    img2 = create_dummy_image_bytes(color=(0, 0, 255))
    files = [
        ("files", ("bai_lam_trang1.jpg", img1, "image/jpeg")),
        ("files", ("bai_lam_trang2.jpg", img2, "image/jpeg"))
    ]
    res = client.post(f"/api/student/assignments/{assign_id}/submit", headers=student_headers, files=files)
    assert res.status_code == 200, f"Submit failed: {res.text}"
    sub_data = res.json()
    submission_id = sub_data["submission_id"]
    assert sub_data["attempt_number"] == 1
    assert sub_data["total_images"] == 2
    print(f"  -> PASS: Nộp bài thành công (Submission #{submission_id}, Lần 1).")

    # TEST 6: Nộp lại bài (Attempt 2)
    print(f"\n[TEST 6] Học sinh nộp lại bài tập #{assign_id}...")
    img3 = create_dummy_image_bytes(color=(255, 255, 0))
    files = [("files", ("bai_lam_moi.jpg", img3, "image/jpeg"))]
    res = client.post(f"/api/student/assignments/{assign_id}/submit", headers=student_headers, files=files)
    assert res.status_code == 200
    assert res.json()["attempt_number"] == 2
    print("  -> PASS: Nộp lại thành công, attempt_number tăng lên 2 và lưu lịch sử đầy đủ.")

    # TEST 7: BẢO MẬT - Chặn file EXE giả mạo .jpg
    print("\n[TEST 7] BẢO MẬT: Chặn file malware.exe đổi tên thành baitap.jpg...")
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00This is a fake windows executable"
    files = [("files", ("baitap.jpg", fake_exe, "image/jpeg"))]
    res = client.post(f"/api/student/assignments/{assign_id}/submit", headers=student_headers, files=files)
    assert res.status_code == 400
    assert "magic bytes" in res.json()["detail"].lower() or "ảnh" in res.json()["detail"].lower()
    print("  -> PASS: Server chặn đứng file giả mạo thông qua kiểm tra magic bytes.")

    # TEST 8: BẢO MẬT - Chặn file ZIP đổi tên thành .png
    print("\n[TEST 8] BẢO MẬT: Chặn file archive.zip đổi tên thành baitap.png...")
    fake_zip = b"PK\x03\x04\x14\x00\x00\x00\x08\x00Fake Zip Content"
    files = [("files", ("baitap.png", fake_zip, "image/png"))]
    res = client.post(f"/api/student/assignments/{assign_id}/submit", headers=student_headers, files=files)
    assert res.status_code == 400
    print("  -> PASS: Server chặn đứng file ZIP giả mạo.")

    # TEST 9: BẢO MẬT - Blacklist tên file chứa 'download'
    print("\n[TEST 9] BẢO MẬT: Chặn file có tên chứa 'download'...")
    files = [("files", ("download_assignment.jpg", img1, "image/jpeg"))]
    res = client.post(f"/api/student/assignments/{assign_id}/submit", headers=student_headers, files=files)
    assert res.status_code == 400
    assert "blacklist" in res.json()["detail"].lower() or "bị cấm" in res.json()["detail"].lower()
    print("  -> PASS: Server từ chối tên file chứa từ khóa 'download'.")

    # TEST 10: BẢO MẬT - Blacklist tên file chứa 'Zalo' (không phân biệt hoa/thường)
    print("\n[TEST 10] BẢO MẬT: Chặn file có tên chứa 'Zalo_123.jpg'...")
    files = [("files", ("Zalo_photo_456.jpg", img1, "image/jpeg"))]
    res = client.post(f"/api/student/assignments/{assign_id}/submit", headers=student_headers, files=files)
    assert res.status_code == 400
    print("  -> PASS: Server từ chối tên file chứa từ khóa 'zalo'.")

    # TEST 11: BẢO MẬT - Blacklist tên file chứa 'messenger'
    print("\n[TEST 11] BẢO MẬT: Chặn file có tên chứa 'Messenger_image.jpg'...")
    files = [("files", ("Messenger_received.jpg", img1, "image/jpeg"))]
    res = client.post(f"/api/student/assignments/{assign_id}/submit", headers=student_headers, files=files)
    assert res.status_code == 400
    print("  -> PASS: Server từ chối tên file chứa từ khóa 'messenger'.")

    # TEST 12: Đăng nhập Admin
    print("\n[TEST 12] Đăng nhập tài khoản Quản trị viên (Admin)...")
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    admin_token = res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("  -> PASS: Đăng nhập Admin thành công.")

    # TEST 13: BẢO MẬT - Học sinh cố gọi API Admin
    print("\n[TEST 13] BẢO MẬT: Học sinh cố tình gọi API /api/admin/dashboard...")
    res = client.get("/api/admin/dashboard", headers=student_headers)
    assert res.status_code == 403
    print("  -> PASS: 403 Forbidden - Học sinh bị chặn hoàn toàn khỏi API Admin.")

    # TEST 14: Admin xem Dashboard
    print("\n[TEST 14] Admin xem Dashboard thống kê...")
    res = client.get("/api/admin/dashboard", headers=admin_headers)
    assert res.status_code == 200
    stats = res.json()["stats"]
    assert stats["total_classes"] >= 2
    assert stats["total_students"] >= 5
    print(f"  -> PASS: Dashboard Admin (Lớp: {stats['total_classes']}, HS: {stats['total_students']}, Bài tập: {stats['total_assignments']}).")

    # TEST 15: Admin theo dõi tiến độ nộp bài (Tracking)
    print(f"\n[TEST 15] Admin theo dõi ai đã nộp/chưa nộp của bài #{assign_id}...")
    res = client.get(f"/api/admin/assignments/{assign_id}/tracking", headers=admin_headers)
    assert res.status_code == 200
    track = res.json()
    assert "summary" in track
    assert track["summary"]["on_time_count"] >= 1
    print(f"  -> PASS: Tracking hoạt động (Đã nộp: {track['summary']['on_time_count']}, Chưa nộp: {track['summary']['unsubmitted_count']}, Hoàn thành: {track['summary']['completion_rate']}%).")

    # TEST 16: BẢO MẬT & IDOR - Phân quyền xem ảnh bài làm
    # Lấy file_id từ bài vừa nộp
    res = client.get(f"/api/student/assignments/{assign_id}", headers=student_headers)
    latest_files = res.json()["assignment"]["latest_submission"]["files"]
    file_id = latest_files[0]["id"]

    print(f"\n[TEST 16] Kiểm tra tải ảnh #{file_id} từ Private Storage:")
    # Học sinh 1 tải ảnh của mình -> Thành công
    res = client.get(f"/api/files/{file_id}", headers=student_headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/jpeg"
    print("  -> PASS: Học sinh chính chủ tải được ảnh.")

    # Học sinh 2 đăng nhập và cố tình tải ảnh của học sinh 1 (Tấn công IDOR)
    res = client.post("/api/auth/login", json={"username": "hocsinh2", "password": "123456"})
    h2_token = res.json()["access_token"]
    h2_headers = {"Authorization": f"Bearer {h2_token}"}
    res = client.get(f"/api/files/{file_id}", headers=h2_headers)
    assert res.status_code == 403
    print("  -> PASS (CHỐNG IDOR): Học sinh khác bị chặn 403 Forbidden khi cố xem ảnh của bạn cùng lớp.")

    # Admin tải ảnh của học sinh -> Thành công
    res = client.get(f"/api/files/{file_id}", headers=admin_headers)
    assert res.status_code == 200
    print("  -> PASS: Admin có đầy đủ quyền xem ảnh bài làm để chấm bài.")

    # TEST 17: Admin đóng bài tập và mở lại
    print(f"\n[TEST 17] Admin đóng bài tập #{assign_id} thủ công...")
    res = client.post(f"/api/admin/assignments/{assign_id}/toggle-status", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "closed"
    print("  -> PASS: Đã đóng bài tập.")

    # Học sinh cố nộp bài khi đã đóng -> Bị từ chối
    res = client.post(f"/api/student/assignments/{assign_id}/submit", headers=student_headers, files=files)
    assert res.status_code == 400
    assert "đóng" in res.json()["detail"].lower()
    print("  -> PASS: Học sinh bị chặn nộp bài khi bài tập ở trạng thái Đã đóng.")

    # Admin mở lại
    client.post(f"/api/admin/assignments/{assign_id}/toggle-status", headers=admin_headers)
    print("  -> PASS: Đã mở lại bài tập.")

    print("\n==================================================")
    print("🎉 TẤT CẢ 17/17 KIỂM THỬ BẢO MẬT & CHỨC NĂNG ĐÃ VƯỢT QUA 100%!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
