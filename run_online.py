import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import os
import re
import time
import subprocess
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CLOUDFLARED_EXE = BASE_DIR / "cloudflared.exe"

def run():
    print("=========================================================")
    print("     KHỞI CHẠY HỆ THỐNG NỘP BÀI TẬP ONLINE (INTERNET)")
    print("=========================================================")
    print()

    # 1. Khởi động Web Server (Uvicorn)
    print("[1/3] Đang khởi động Web Server nội bộ (port 8000)...")
    server_cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload"]
    server_proc = subprocess.Popen(
        server_cmd,
        cwd=str(BASE_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(2)

    # 2. Khởi động Cloudflare Tunnel
    if not CLOUDFLARED_EXE.exists():
        print("Lỗi: Không tìm thấy file cloudflared.exe!")
        return

    print("[2/3] Đang kết nối mạng Cloudflare Tunnel an toàn...")
    tunnel_cmd = [str(CLOUDFLARED_EXE), "tunnel", "--url", "http://127.0.0.1:8000"]
    tunnel_proc = subprocess.Popen(
        tunnel_cmd,
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )

    public_url = None
    start_time = time.time()

    # Quét log để tìm domain trycloudflare.com
    while time.time() - start_time < 30:
        line = tunnel_proc.stdout.readline()
        if not line:
            time.sleep(0.2)
            continue

        match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
        if match:
            public_url = match.group(0)
            break

    if public_url:
        print("\n" + "=" * 60)
        print("🎉 HỆ THỐNG ĐÃ SẴN SÀNG CHẠY ONLINE TRÊN TOÀN CẦU!")
        print("=" * 60)
        print(f"\n👉 ĐƯỜNG LINK ONLINE CHO HỌC SINH VÀ GIÁO VIÊN:")
        print(f"   \033[1;32m{public_url}\033[0m")
        print("\n(Học sinh có thể dùng điện thoại mở link này qua 4G/Wifi từ bất kỳ đâu)")
        print("=" * 60)

        # Lưu link vào file txt
        link_file = BASE_DIR.parent / "DUONG_DAN_ONLINE.txt"
        link_file.write_text(
            f"LINK WEB NỘP BÀI TẬP ONLINE DÀNH CHO HỌC SINH VÀ GIÁO VIÊN:\n\n{public_url}\n\n(Lưu ý: Giữ cửa sổ dòng lệnh luôn mở trong khi học sinh đang làm bài và nộp bài)\n",
            encoding="utf-8"
        )
        print(f"-> Đã lưu link vào file: {link_file.name}")

        # Tự động mở trình duyệt
        webbrowser.open(public_url)
    else:
        print("\nKhông lấy được link public tự động. Bạn vẫn có thể truy cập nội bộ tại: http://localhost:8000")

    print("\nẤn Ctrl + C để dừng hệ thống khi không sử dụng nữa...")
    try:
        tunnel_proc.wait()
    except KeyboardInterrupt:
        print("\nĐang tắt hệ thống...")
    finally:
        tunnel_proc.terminate()
        server_proc.terminate()

if __name__ == "__main__":
    run()
