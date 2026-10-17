from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.config import BASE_DIR
from app.routes import auth, student, admin, files
from app.seed import seed

app = FastAPI(
    title="Hệ thống Nộp Bài Tập Học Sinh",
    description="Web app quản lý và nộp bài tập tối ưu trên điện thoại (Mobile-First)",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# No-cache middleware để đảm bảo trình duyệt luôn nhận file JS/CSS/HTML mới nhất
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/static/") or path in ["/", "/student", "/admin"]:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Startup: Tự động khởi tạo DB, tạo Admin và đầy đủ 44 học sinh Lớp 11A1
@app.on_event("startup")
def on_startup():
    init_db()
    seed()

# Mount API Routers
app.include_router(auth.router)
app.include_router(student.router)
app.include_router(admin.router)
app.include_router(files.router)

# Mount thư mục tĩnh
STATIC_DIR = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Phục vụ HTML Pages
@app.get("/")
def read_root():
    return FileResponse(str(STATIC_DIR / "index.html"))

@app.get("/student")
def read_student_page():
    return FileResponse(str(STATIC_DIR / "student.html"))

@app.get("/admin")
def read_admin_page():
    return FileResponse(str(STATIC_DIR / "admin.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
