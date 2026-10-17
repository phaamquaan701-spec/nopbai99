from app.main import app
from app.database import init_db
from app.seed import seed

# Khởi tạo DB và seed tài khoản học sinh / admin khi serverless instance khởi động
try:
    init_db()
    seed()
except Exception as e:
    print(f"Serverless initialization note: {e}")
