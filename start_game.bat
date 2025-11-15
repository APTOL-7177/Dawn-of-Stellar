@echo off
chcp 65001 > nul
title Dawn of Stellar - 별빛의 여명

echo ====================================
echo   Dawn of Stellar - 별빛의 여명
echo ====================================
echo.
echo 게임을 시작합니다...
echo.

REM 게임 직접 실행
python main.py

REM 오류 발생 시 대기
if errorlevel 1 (
    echo.
    echo 오류가 발생했습니다.
    pause
)
