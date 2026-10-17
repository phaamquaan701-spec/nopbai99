@echo off
chcp 65001 > nul
title EduNopBai - Kh?i Ch?y Web N?p B?i Online (Internet)
echo =========================================================
echo       EduNopBai - Kh?i Ch?y Online Ra To?n C?u
echo =========================================================
echo.
cd /d "%~dp0\nopbai" 2>nul || cd /d "%~dp0"

python run_online.py
pause
