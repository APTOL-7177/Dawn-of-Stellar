@echo off
chcp 65001 >nul
title Dawn of Stellar 설치 마법사

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║     ⭐ Dawn of Stellar 설치 마법사 ⭐                    ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

REM 현재 디렉토리로 이동
cd /d "%~dp0"

REM PowerShell 스크립트 실행 (실행 정책 우회)
echo PowerShell 스크립트를 실행합니다...
echo 실행 정책을 자동으로 우회합니다...
echo.

powershell.exe -ExecutionPolicy Bypass -NoProfile -File "%~dp0install.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 오류가 발생했습니다. 오류 코드: %ERRORLEVEL%
    echo.
    echo 문제 해결 방법:
    echo 1. PowerShell을 관리자 권한으로 열고 다음 명령어 실행:
    echo    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
    echo.
    echo 2. 또는 수동으로 실행:
    echo    powershell.exe -ExecutionPolicy Bypass -File install.ps1
    echo.
    pause
    exit /b %ERRORLEVEL%
)

pause

