@echo off
chcp 65001 >nul
call .venv\Scripts\activate
echo ========================================================
echo  HỆ THỐNG TRỢ LÝ RAG QUY ĐỊNH HỌC VỤ (AI ASSISTANT)
echo ========================================================
echo.
echo [*] Đang khởi động máy chủ tại: http://127.0.0.1:8000
echo [*] Trình duyệt web sẽ tự động mở...
echo [*] Nhấn Ctrl+C để dừng máy chủ.
echo.
start http://127.0.0.1:8000
uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
