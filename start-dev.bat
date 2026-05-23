@echo off
setlocal enabledelayedexpansion
title CooMate Dev

echo.
echo   CooMate - AI Cognitive Assistant
echo   Starting dev server...
echo.

:: Detect Python
set "PYTHON="
where python >nul 2>&1
if !errorlevel!==0 (
    for /f "delims=" %%p in ('where python') do (
        set "PYTHON=%%p"
        goto :found_python
    )
)
where python3 >nul 2>&1
if !errorlevel!==0 (
    set "PYTHON=python3"
    goto :found_python
)
echo [ERROR] Python not found. Please add Python to PATH.
pause
exit /b 1

:found_python
echo [OK] Python: !PYTHON!

:: Detect Node.js
where node >nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] Node.js not found. Please add Node.js to PATH.
    pause
    exit /b 1
)
echo [OK] Node.js found.

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
start "CooMate-Backend" cmd /k "cd /d %~dp0apps\backend && "!PYTHON!" -m uvicorn main:app --reload --host 0.0.0.0 --port 8266"

:: Start frontend
echo [2/2] Starting frontend (Vite) on port 5066...
start "CooMate-Frontend" cmd /k "cd /d %~dp0apps\frontend && npm run dev"

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
