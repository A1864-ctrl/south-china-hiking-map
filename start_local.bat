@echo off
chcp 65001 >nul
title Local preview - tourism and hiking map
cd /d "%~dp0"

if not exist "venv\Scripts\streamlit.exe" (
    echo [ERROR] venv not found. Run this from the project root.
    pause
    exit /b 1
)

echo Starting local preview on http://localhost:8531
echo Keep this window open. Press Ctrl+C to stop.
echo.

rem Open the browser a few seconds later, so the server is already up.
start "" /min cmd /c "timeout /t 6 >nul & start http://localhost:8531"

"venv\Scripts\streamlit.exe" run Home.py --server.port 8531 --server.headless true --browser.gatherUsageStats false

echo.
echo Server stopped.
pause
