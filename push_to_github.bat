@echo off
chcp 65001 >nul
title 推送到 GitHub（自动重试）

cd /d "%~dp0"

echo ============================================
echo   把本地提交推送到 GitHub
echo   网络不通时会自动重试，最多 10 次
echo ============================================
echo.

set /a try=0

:loop
set /a try+=1
echo [第 %try% 次] 正在推送...

git push origin master
if not errorlevel 1 goto success

if %try% geq 10 goto failed

echo.
echo   推送失败：多半是网络连不上 github.com
echo   10 秒后重试，建议同时做其中一件事：
echo     - 关掉代理软件，或用手机热点
echo     - 打开代理并换一个节点
echo.
timeout /t 10 /nobreak >nul
goto loop

:success
echo.
echo ============================================
echo   推送成功
echo   打开 https://github.com/A1864-ctrl/streamlit-geospatial 看看
echo ============================================
echo.
pause
exit /b 0

:failed
echo.
echo ============================================
echo   10 次都没成功，说明当前网络确实连不上 github.com
echo.
echo   自查命令（在窗口里粘贴）：
echo     curl -o NUL -w "%%{http_code}" https://github.com/
echo   返回 200 才代表网络通了，000 就是连不上。
echo.
echo   换网络（手机热点最有效）后，再双击本脚本。
echo ============================================
echo.
pause
exit /b 1
