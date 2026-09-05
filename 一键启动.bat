@echo off
REM YiCode one-click launcher: backend + frontend + browser
start "YiCode Backend" "%~dp0启动后端.bat"
timeout /t 3 /nobreak >nul
start "YiCode Frontend" "%~dp0启动前端.bat"
timeout /t 6 /nobreak >nul
start "" "http://localhost:5173/"
echo Both services starting. Close the two console windows to stop them.
pause
