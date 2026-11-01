@echo off
chcp 65001 > nul
echo ===================================================
echo [TEST] Chay bo kiem thu tu dong (Automated Tests)
echo ===================================================
.\.venv\Scripts\python.exe -m unittest tests/test_system.py
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [THANH CONG] Toan bo cac ca kiem thu deu PASS!
) else (
    echo.
    echo [THAT BAI] Co ca kiem thu bi loi!
)
pause

