@echo off
chcp 65001 > nul
title Dawn of Stellar - Game Launcher

REM Python 경로 확인 및 실행
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not found in PATH.
    echo Please ensure Python 3.10+ is installed and added to PATH.
    echo.
    echo Press any key to continue...
    pause >nul
    exit /b 1
)

echo Starting game launcher...
echo.

REM 게임 런처 실행
python launcher.py

REM 오류 발생 시 대기
if errorlevel 1 (
    echo.
    echo Error occurred while running the launcher.
    echo This might be due to missing dependencies or configuration issues.
    echo.
    echo Try running the following commands manually:
    echo   pip install -r requirements.txt
    echo   python main.py
    echo.
    pause
)
