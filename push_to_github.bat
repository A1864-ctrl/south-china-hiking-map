@echo off
chcp 65001 >nul
title 推送到 GitHub（自动重试）
cd /d "%~dp0"

echo ============================================
echo   把本地提交推送到 GitHub
echo ============================================
echo.

echo [0] 先测一下能不能连上 github.com ...
curl -s -o NUL --max-time 20 -w "    返回码 = %%{http_code}\n" https://github.com/
echo.
echo     200 = 通；000 / 502 = 当前连不上，推送一定会失败
echo.

set /a try=0

:loop
set /a try+=1
echo [第 %try% 次] 正在推送...
echo.

git push origin master
if not errorlevel 1 goto success

if %try% geq 8 goto failed

echo.
echo   失败原因通常是这两类：
echo     CONNECT tunnel failed, response 502  -^> 代理节点连不上 github
echo     schannel: failed to receive handshake -^> TLS 握手被打断
echo.
echo   25 秒后重试。期间可以试：
echo     - 代理软件里换一个节点（香港/日本节点成功率高）
echo     - 手机开热点，电脑连热点后直接重跑本脚本
echo     - 等几分钟再试，这种 502 是间歇性的
echo.
timeout /t 25 /nobreak >nul
goto loop

:success
echo.
echo ============================================
echo   推送成功
echo   打开 https://github.com/A1864-ctrl/streamlit-geospatial
echo   刷新页面，提交记录里应该能看到刚才这一条
echo ============================================
echo.
pause
exit /b 0

:failed
echo.
echo ============================================
echo   8 次都没成功，当前网络确实到不了 github.com
echo.
echo   1) 先在窗口里自查：
echo        curl -o NUL -w "%%{http_code}" https://github.com/
echo      200 才是通，000 / 502 都不通
echo.
echo   2) 换网络（手机热点最有效），再双击本脚本
echo.
echo   3) 代码其实已经推上去过了（提交 a2eeea2），
echo      只有最后的文档更新卡住，不影响 Streamlit 部署。
echo ============================================
echo.
pause
exit /b 1
