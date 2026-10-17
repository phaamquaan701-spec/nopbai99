@echo off
chcp 65001 > nul
title EduViet Nop Bai - He Thong Quan Ly Bai Tap Hoc Sinh
echo =========================================================
echo       EduViet - Phan He Nop Bai Tap Hoc Sinh (Mobile)
echo =========================================================
echo.
cd /d "%~dp0"

echo [1/2] Dang kiem tra va khoi tao co so du lieu...
python -m app.seed

echo.
echo [2/2] Dang khoi chay may chu tai http://localhost:8000 ...
start http://localhost:8000

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
