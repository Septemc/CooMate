@echo off
setlocal enabledelayedexpansion
title CooMate Dev

set PYTHON=C:\Users\lenovo\anaconda3\envs\pytorch2.2.2\python.exe
set NODE_DIR=E:\nodejs

set PATH=%NODE_DIR%;%PATH%

echo.
echo   CooMate - AI Cognitive Assistant
echo   Starting dev server...
echo.

:: Check Python
if not exist "!PYTHON!" (
    echo [ERROR] Python not found at !PYTHON!
    pause
    exit /b 1
)

:: Check Node
where node >nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] Node.js not found at !NODE_DIR!
    pause
    exit /b 1
)

:: Check and kill port 8266
netstat -ano | findstr ":8266" | findstr "LISTENING" >nul 2>&1
if !errorlevel!==0 (
    echo [WARN] Port 8266 is in use. Killing existing process...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8266" ^| findstr "LISTENING"') do (
        taskkill /PID %%a /F >nul 2>&1
    )
    timeout /t 1 /nobreak >nul
)

:: Check and kill port 5066
netstat -ano | findstr ":5066" | findstr "LISTENING" >nul 2>&1
if !errorlevel!==0 (
    echo [WARN] Port 5066 is in use. Killing existing process...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5066" ^| findstr "LISTENING"') do (
        taskkill /PID %%a /F >nul 2>&1
    )
    timeout /t 1 /nobreak >nul
)

:: Install frontend deps if needed
if not exist "%~dp0apps\frontend\node_modules" (
    echo [0/2] Installing frontend dependencies...
    cd /d %~dp0apps\frontend && npm install
    if !errorlevel! neq 0 (
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
    echo Frontend dependencies installed.
    echo.
)

:: Start backend
echo [1/2] Starting backend (FastAPI) on port 8266...
start "CooMate-Backend" cmd /k "set PATH=!NODE_DIR!;%PATH% && cd /d %~dp0apps\backend && "!PYTHON!" -m uvicorn main:app --reload --host 0.0.0.0 --port 8266"

:: Start frontend (parallel, no waiting)
echo [2/2] Starting frontend (Vite) on port 5066...
start "CooMate-Frontend" cmd /k "set PATH=!NODE_DIR!;%PATH% && cd /d %~dp0apps\frontend && npm run dev"

echo.
echo  ==============================
echo   Backend:  http://localhost:8266
echo   Frontend: http://localhost:5066
echo  ==============================
echo.
echo  Press any key to stop all services...
pause >nul

:: Cleanup
taskkill /FI "WindowTitle eq CooMate-Backend*" /F >nul 2>&1
taskkill /FI "WindowTitle eq CooMate-Frontend*" /F >nul 2>&1
echo  All services stopped.
timeout /t 2 /nobreak >nul
