@echo off
chcp 65001 > nul
setlocal

:: ====================================================================
:: Dawn of Stellar - 게임 실행 스크립트
:: ====================================================================

title Dawn of Stellar - 별빛의 여명

color 0B
cls

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║                                                               ║
echo ║         ⭐ Dawn of Stellar (별빛의 여명) ⭐                  ║
echo ║                                                               ║
echo ║          Final Fantasy Style Roguelike RPG                    ║
echo ║                                                               ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

:: Python 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python이 설치되어 있지 않습니다!
    echo.
    echo 📌 setup-auto.bat을 실행하여 자동 설치하세요.
    echo.
    pause
    exit /b 1
)

:: 게임 파일 확인
if not exist "main.py" (
    echo ❌ main.py 파일을 찾을 수 없습니다!
    echo.
    echo    현재 위치: %CD%
    echo.
    pause
    exit /b 1
)

echo 🎮 게임을 시작합니다...
echo.

:: 게임 실행
python main.py

:: 오류 체크
if %errorlevel% neq 0 (
    echo.
    echo ═══════════════════════════════════════════════════════════════
    echo  ⚠️  게임 실행 중 오류가 발생했습니다
    echo ═══════════════════════════════════════════════════════════════
    echo.
    echo 📌 해결 방법:
    echo    1. 로그 확인: logs/ 폴더
    echo    2. 패키지 재설치: python -m pip install -r requirements-minimal.txt
    echo    3. 문제 지속 시 setup-auto.bat 재실행
    echo.
) else (
    echo.
    echo ═══════════════════════════════════════════════════════════════
    echo  👋 게임을 종료합니다. 다음에 또 만나요!
    echo ═══════════════════════════════════════════════════════════════
    echo.
)

pause
