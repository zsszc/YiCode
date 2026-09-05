@echo off
REM YiCode backend launcher (port 8000)
cd /d "%~dp0backend"
echo Starting YiCode backend on http://localhost:8000 ...
"D:\KimiData\daimon-share\daimon\runtime\python\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
