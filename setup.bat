@echo off
chcp 65001 >nul
echo === Tao moi truong ao va cai thu vien ===
python --version || (echo Chua co Python. Hay cai Python 3.12 va tick "Add to PATH" & pause & exit /b 1)
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
python -m pip install -r requirements.txt
echo.
echo Xong! Bay gio copy file quy che vao data\raw roi chay run_buoc1_2.bat
pause
