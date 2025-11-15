@echo off
chcp 65001 > nul
title Dawn of Stellar - 개발 모드

echo ====================================
echo   Dawn of Stellar - 개발 모드
echo   (모든 직업 잠금 해제)
echo ====================================
echo.
echo 개발 모드로 게임을 시작합니다...
echo.

REM 개발 모드로 게임 실행
python main.py --dev

REM 오류 발생 시 대기
if errorlevel 1 (
    echo.
    echo 오류가 발생했습니다.
    pause
)
