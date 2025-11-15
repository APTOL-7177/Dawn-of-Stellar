@echo off
chcp 65001 > nul
title Dawn of Stellar - Game Launcher

REM 게임 런처 실행
python launcher.py

REM 오류 발생 시 대기
if errorlevel 1 (
    echo.
    echo 오류가 발생했습니다.
    pause
)
