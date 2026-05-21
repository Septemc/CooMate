@echo off
chcp 65001 >nul 2>&1
title CooMate - Dev Mode

echo.
echo  ██████╗ ██████╗  ██████╗ ███╗   ███╗ █████╗ ████████╗███████╗
echo ██╔════╝██╔═══██╗██╔═══██╗████╗ ████║██╔══██╗╚══██╔══╝██╔════╝
echo ██║     ██║   ██║██║   ██║██╔████╔██║███████║   ██║   █████╗
echo ██║     ██║   ██║██║   ██║██║╚██╔╝██║██╔══██║   ██║   ██╔══╝
echo ╚██████╗╚██████╔╝╚██████╔╝██║ ╚═╝ ██║██║  ██║   ██║   ███████╗
echo  ╚═════╝ ╚═════╝  ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝
echo.
echo  Starting backend and frontend in dev mode...
echo.

:: Check if ports are available
netstat -ano | findstr ":8266" >nul 2>&1
if %errorlevel%==0 (
    echo [ERROR] Port 8266 is already in use!
    pause
    exit /b 1
)

netstat -ano | findstr ":5066" >nul 2>&1
if %errorlevel%==0 (
    echo [ERROR] Port 5066 is already in use!
    pause
    exit /b 1
)

:: Start backend
echo [1/2] Starting backend (FastAPI) on port 8266...
start "CooMate-Backend" cmd /k "cd /d %~dp0apps\backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8266"

:: Wait for backend to be ready
echo Waiting for backend to initialize...
:wait_loop
timeout /t 1 /nobreak >nul
curl -s http://localhost:8266/health >nul 2>&1
if %errorlevel% neq 0 goto wait_loop
echo Backend is ready!

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

:: Kill both windows
taskkill /FI "WindowTitle eq CooMate-Backend*" /F >nul 2>&1
taskkill /FI "WindowTitle eq CooMate-Frontend*" /F >nul 2>&1
echo  All services stopped.
timeout /t 2 /nobreak >nul
