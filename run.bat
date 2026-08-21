@echo off
title Fx Downloader - Ultra HD Video & Audio Downloader
cd /d "%~dp0"
echo ================================================================
echo          FX DOWNLOADER - ULTRA HD VIDEO & AUDIO SERVER
echo ================================================================
echo.
echo Starting Web Server on http://localhost:5000 ...
echo Press Ctrl+C in this terminal to stop the server.
echo.
start http://localhost:5000
python app.py
pause
