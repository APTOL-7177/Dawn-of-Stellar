@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

:: ====================================================================
:: Dawn of Stellar - 원클릭 설치 스크립트 (Windows)
:: ====================================================================

title Dawn of Stellar 설치기

echo.
echo ═══════════════════════════════════════════════════════════════
echo    ⭐ Dawn of Stellar (별빛의 여명) - 자동 설치 ⭐
echo ═══════════════════════════════════════════════════════════════
echo.
echo    Final Fantasy 스타일 로그라이크 RPG
echo    Python + TCOD 기반 게임 엔진
echo.
echo ═══════════════════════════════════════════════════════════════
echo.

:: ====================================================================
:: 1단계: Python 설치 확인
:: ====================================================================

echo [1/5] Python 설치 확인 중...
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python이 설치되어 있지 않습니다!
    echo.
    echo 📥 Python 3.10 이상을 설치해주세요:
    echo    https://www.python.org/downloads/
    echo.
    echo 설치 시 "Add Python to PATH" 옵션을 반드시 체크하세요!
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python %PYTHON_VERSION% 발견!
echo.

:: ====================================================================
:: 2단계: pip 업그레이드
:: ====================================================================

echo [2/5] pip 업그레이드 중...
echo.

python -m pip install --upgrade pip --quiet
if %errorlevel% neq 0 (
    echo ⚠️  pip 업그레이드 실패 (무시하고 계속...)
) else (
    echo ✅ pip 업그레이드 완료!
)
echo.

:: ====================================================================
:: 3단계: 의존성 설치 옵션 선택
:: ====================================================================

echo [3/5] 설치 모드 선택
echo.
echo    1. 최소 설치 (권장) - 게임 실행에 필요한 패키지만
echo    2. 전체 설치 - 개발 도구 포함 (테스트, 린터 등)
echo.

set /p INSTALL_MODE="선택 (1 또는 2, 기본값=1): "
if "%INSTALL_MODE%"=="" set INSTALL_MODE=1

if "%INSTALL_MODE%"=="2" (
    set REQUIREMENTS_FILE=requirements.txt
    echo.
    echo 📦 전체 설치 모드 선택됨
) else (
    set REQUIREMENTS_FILE=requirements-minimal.txt
    echo.
    echo 📦 최소 설치 모드 선택됨 (권장)
)
echo.

:: ====================================================================
:: 4단계: 패키지 설치
:: ====================================================================

echo [4/5] Python 패키지 설치 중...
echo.
echo    파일: %REQUIREMENTS_FILE%
echo    시간이 다소 걸릴 수 있습니다...
echo.

python -m pip install -r %REQUIREMENTS_FILE%
if %errorlevel% neq 0 (
    echo.
    echo ❌ 패키지 설치 실패!
    echo.
    echo 해결 방법:
    echo    1. 인터넷 연결 확인
    echo    2. 방화벽 확인
    echo    3. pip 캐시 삭제: python -m pip cache purge
    echo    4. 관리자 권한으로 재실행
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ 모든 패키지 설치 완료!
echo.

:: ====================================================================
:: 5단계: 설치 확인
:: ====================================================================

echo [5/5] 설치 확인 중...
echo.

:: TCOD 설치 확인
python -c "import tcod; print('TCOD 버전:', tcod.__version__)" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ TCOD 설치 실패
    pause
    exit /b 1
)

:: YAML 설치 확인
python -c "import yaml" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ PyYAML 설치 실패
    pause
    exit /b 1
)

echo ✅ 모든 필수 패키지 확인 완료!
echo.

:: ====================================================================
:: 설치 완료
:: ====================================================================

echo.
echo ═══════════════════════════════════════════════════════════════
echo    🎉 설치가 완료되었습니다! 🎉
echo ═══════════════════════════════════════════════════════════════
echo.
echo 게임 실행 방법:
echo.
echo    방법 1: run.bat 파일을 더블클릭
echo    방법 2: python main.py 명령어 실행
echo.
echo 개발 모드 (모든 직업 잠금 해제):
echo    python main.py --dev
echo.
echo 디버그 모드:
echo    python main.py --debug --log=DEBUG
echo.
echo ═══════════════════════════════════════════════════════════════
echo.

:: ====================================================================
:: 게임 실행 옵션
:: ====================================================================

echo 지금 바로 게임을 시작하시겠습니까? (Y/N)
set /p RUN_NOW="선택: "

if /i "%RUN_NOW%"=="Y" (
    echo.
    echo 🎮 게임을 시작합니다...
    echo.
    timeout /t 2 /nobreak >nul
    python main.py
) else (
    echo.
    echo 나중에 run.bat을 실행하여 게임을 시작하세요!
)

echo.
echo 설치 스크립트를 종료합니다.
pause
