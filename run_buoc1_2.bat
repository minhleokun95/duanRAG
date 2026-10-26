@echo off
chcp 65001 >nul
call .venv\Scripts\activate
echo === Buoc 1: Trich xuat text ===
python scripts\extract.py
echo.
echo === Buoc 2: Chia chunk theo Dieu ===
python scripts\chunk.py
echo.
pause
