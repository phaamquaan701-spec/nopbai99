# EduNopBai – Web App Nộp & Quản Lý Bài Tập Học Sinh (Mobile-First)

Hệ thống web app chuyên dụng dành cho học sinh THPT và giáo viên/quản trị viên để quản lý, giao bài và nộp bài tập, được tối ưu hóa đặc biệt cho thiết bị di động (**Mobile-First** từ 360px đến 430px).

---

## 🌟 Tính Năng Nổi Bật

### 1. Học sinh (Student)
- **Giao diện chuẩn Mobile-First**: Thao tác bằng một tay, các nút cảm ứng lớn, thẻ card trực quan, thanh Bottom Navigation cố định dưới màn hình.
- **Nộp bài tập bằng ảnh từ thiết bị**:
  - Cho phép chọn nhiều ảnh từ Gallery, Photos, Thư viện hoặc ảnh chụp bài làm đã lưu trong máy.
  - Sử dụng cơ chế trình duyệt gốc (`accept="image/*"`, không bật camera capture).
  - Xem trước thumbnail ảnh, hiển thị kích thước và dung lượng từng file.
  - Xóa ảnh, đổi thứ tự ảnh (Trang 1, Trang 2...).
  - Thanh tiến trình upload trực quan (Progress bar: "Đang tải ảnh 2/4 (50%)...").
  - Nếu upload lỗi, hệ thống giữ nguyên danh sách ảnh đã chọn để không phải chọn lại.
  - Xác nhận nộp bài, ghi nhận lịch sử các lần nộp (Attempts).
- **Trạng thái bài tập tự động chuẩn xác theo giờ Server**:
  - `Chưa mở` (kèm thời gian bắt đầu nhận bài).
  - `Chưa nộp` (kèm thời gian còn lại đếm ngược).
  - `Đã nộp` (kèm thời gian nộp, lần nộp, đúng hạn).
  - `Sắp hết hạn` (cảnh báo phụ khi còn $\le$ 24h).
  - `Quá hạn – chưa nộp`.
  - `Đã nộp – nộp muộn` (ghi nhận số giờ/phút nộp muộn).
  - `Đã đóng` (khi giáo viên khóa bài tập).

### 2. Giáo viên / Quản trị viên (Admin/Teacher)
- **Dashboard tổng quan**: Thống kê số lớp, học sinh, bài tập, lượt nộp bài, bài tập sắp đến hạn trong 24h.
- **Quản lý Bài tập**: Tạo bài tập, chỉnh sửa, đóng bài, mở lại, xóa bài, cấu hình hạn nộp (deadline chi tiết ngày giờ phút), cho phép nộp muộn, cho phép nộp lại, số ảnh tối đa, dung lượng tối đa.
- **Theo dõi ai đã nộp / chưa nộp**:
  - Thống kê tiến độ trực quan: `38 / 45 đã nộp` với thanh progress bar và tỷ lệ hoàn thành %.
  - Bộ lọc tức thời: Tất cả | Đã nộp | Nộp muộn | Chưa nộp.
  - Ô tìm kiếm học sinh.
  - Danh sách dạng thẻ Card tối ưu trên điện thoại.
- **Xem ảnh bài làm học sinh (Mobile Image Viewer)**:
  - Xem toàn màn hình (Fullscreen).
  - **Pinch-to-zoom**: Dùng 2 ngón tay phóng to thu nhỏ rõ từng nét chữ viết tay.
  - **Double-tap zoom**: Chạm đúp phóng to nhanh 2.5x / thu nhỏ.
  - **Kéo ảnh (Pan)** khi zoom.
  - **Vuốt trái/phải (Swipe Gallery)** để chuyển nhanh giữa các trang bài tập.
- **Quản lý Lớp & Học sinh**: Thêm lớp, xem danh sách học sinh theo lớp, thêm học sinh, đổi mật khẩu, khóa/mở khóa tài khoản.

### 3. Tiêu Chuẩn An Toàn & Bảo Mật Khắt Khe (Server-Side)
- **Kiểm tra File Upload**:
  - Xác thực chữ ký nhị phân **Magic Bytes** (chặn đứng file `.exe`, `.zip`, mã độc đổi đuôi thành `.jpg`).
  - Bộ lọc **Blacklist tên file**: Tự động từ chối file có tên chứa `download`, `downloads`, `zalo`, `messenger` (không phân biệt hoa thường).
  - **Pipeline Xử lý ảnh an toàn (Pillow)**: Tự động xoay theo EXIF orientation $\to$ Resize ảnh lớn $\to$ Re-encode thành ảnh JPEG sạch $\to$ Lưu vào thư mục **Private Storage**.
- **Chống IDOR & Phân quyền**: Học sinh tuyệt đối không thể xem bài nộp của học sinh khác hoặc gọi API Admin. File ảnh được phục vụ qua route bảo mật có xác thực quyền.
- **Chống gian lận hạn nộp**: Thời gian được quyết định 100% bằng Server Timestamp theo múi giờ `Asia/Ho_Chi_Minh` (UTC+7), học sinh không thể chỉnh giờ điện thoại để nộp lố deadline.
- **Chống F12 cơ bản**: Chặn phím tắt `F12`, `Ctrl+Shift+I/J/U` và chuột phải trên giao diện.

---

## 🚀 Hướng Dẫn Cài Đặt & Khởi Chạy

### Cách 1: Chạy bằng 1-Click (Khuyên dùng trên Windows)
- Nhấp đúp chuột vào file **`start.bat`** trong thư mục dự án `nopbai`.
- Hệ thống sẽ tự khởi tạo dữ liệu mẫu và mở trình duyệt tại: `http://localhost:8000`.

### Cách 2: Chạy bằng dòng lệnh Terminal
```bash
cd c:\Users\quanp\Documents\web\nopbai

# Khởi tạo dữ liệu mẫu (chỉ cần chạy 1 lần đầu)
python -m app.seed

# Chạy server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Truy cập: [http://localhost:8000](http://localhost:8000)

---

## 🔑 Tài Khoản Thử Nghiệm Có Sẵn

| Vai trò | Tên đăng nhập | Mật khẩu | Ghi chú |
| :--- | :--- | :--- | :--- |
| **Quản trị / Giáo viên** | `admin` | `admin123` | Toàn quyền quản lý lớp, học sinh, bài tập, tracking |
| **Học sinh 1** | `hocsinh1` | `123456` | Lớp 10A1 (Nguyễn Văn An) |
| **Học sinh 2** | `hocsinh2` | `123456` | Lớp 10A1 (Trần Thị Bích) |
| **Học sinh 3** | `hocsinh3` | `123456` | Lớp 10A1 (Lê Hoàng Cường) |
| **Học sinh 4** | `hocsinh4` | `123456` | Lớp 10A1 (Phạm Minh Đức) |

*(Trên trang đăng nhập có sẵn các nút bấm đăng nhập nhanh bằng 1 chạm tiện lợi)*

---

## 🧪 Chạy Kiểm Thử Tự Động (Automated Security Tests)
Để chạy toàn bộ bộ kiểm thử 17 kịch bản chức năng & bảo mật:
```bash
python -m tests.test_system
```
