@echo off
title Fx Downloader - Public Online Link
echo ========================================================
echo        Starting Fx Downloader Public Internet Link...
echo ========================================================
echo.
start "" ".\cloudflared.exe" tunnel --url http://127.0.0.1:5000
echo Tunnel launched! Check the console or browser.
pause
