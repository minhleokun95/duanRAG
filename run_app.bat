@echo off
chcp 65001 >nul
call .venv\Scripts\activate
echo Mo trinh duyet tai http://127.0.0.1:8000
uvicorn app.main:app --port 8000
pause
