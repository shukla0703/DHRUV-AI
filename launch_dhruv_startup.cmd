@echo off
cd /d "C:\Users\shamb\OneDrive\Documents\Codes\Aether AI"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py --startup
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py -3.11 main.py --startup
    ) else (
        python main.py --startup
    )
)
