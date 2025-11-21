@echo off
chcp 65001 >nul
title Dawn of Stellar 업데이트

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║     ⭐ Dawn of Stellar 업데이트 ⭐                      ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

REM 현재 디렉토리로 이동
cd /d "%~dp0"

REM PowerShell 스크립트 실행 (실행 정책 우회)
echo PowerShell 스크립트를 실행합니다...
echo 실행 정책을 자동으로 우회합니다...
echo.

powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0update.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 오류가 발생했습니다. 오류 코드: %ERRORLEVEL%
    echo.
    pause
    exit /b %ERRORLEVEL%
)

pause

