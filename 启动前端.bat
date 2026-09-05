@echo off
REM YiCode frontend launcher (port 5173)
cd /d "%~dp0frontend"
set "PATH=D:\kimiwork\resources\resources\runtime;%PATH%"
echo Starting YiCode frontend on http://localhost:5173 ...
call npm run dev
pause
