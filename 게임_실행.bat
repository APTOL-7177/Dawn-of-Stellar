@echo off
chcp 65001 >nul
title Dawn of Stellar - 별빛의 여명

REM 현재 스크립트가 있는 폴더로 이동
cd /d "%~dp0"

REM 실행 파일이 있는지 확인
if exist "DawnOfStellar.exe" (
    echo 게임을 시작합니다...
    echo.
    start "" "DawnOfStellar.exe"
    exit /b 0
)

REM Python 버전이 있는지 확인 (개발 모드)
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] 실행 파일을 찾을 수 없습니다.
    echo.
    echo 게임을 실행하려면 다음 중 하나를 수행하세요:
    echo 1. 배포 버전의 DawnOfStellar.exe 파일이 이 폴더에 있는지 확인하세요.
    echo 2. 또는 Python이 설치되어 있고 main.py가 있는지 확인하세요.
    echo.
    pause
    exit /b 1
)

REM Python으로 직접 실행 (개발 모드)
if exist "main.py" (
    echo 개발 모드로 게임을 시작합니다...
    echo.
    python main.py
    exit /b 0
)

echo [오류] 게임 파일을 찾을 수 없습니다.
echo.
pause
exit /b 1

