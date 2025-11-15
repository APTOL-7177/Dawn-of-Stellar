@echo off
chcp 65001 > nul
setlocal

:: ====================================================================
:: Dawn of Stellar - 실행 파일 빌드 스크립트
:: Python이 필요 없는 독립 실행 파일(EXE)을 생성합니다
:: ====================================================================

title Dawn of Stellar 빌드

color 0E
cls

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║                                                               ║
echo ║        ⭐ Dawn of Stellar - EXE 빌드 스크립트 ⭐            ║
echo ║                                                               ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo    독립 실행 파일(EXE)을 생성합니다
echo    Python 설치 없이 게임을 실행할 수 있습니다!
echo.
echo ═══════════════════════════════════════════════════════════════
echo.

:: Python 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python이 설치되어 있지 않습니다!
    echo.
    echo 📌 setup-auto.bat을 실행하여 Python을 설치하세요.
    echo.
    pause
    exit /b 1
)

echo ✅ Python 확인 완료
echo.

:: build.py 실행
echo 🔨 빌드를 시작합니다...
echo.
echo    시간이 다소 걸릴 수 있습니다 (5-10분)
echo    잠시만 기다려주세요...
echo.

python build.py

if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ═══════════════════════════════════════════════════════════════
    echo  ❌ 빌드 실패!
    echo ═══════════════════════════════════════════════════════════════
    echo.
    echo 📌 가능한 원인:
    echo    1. PyInstaller 미설치
    echo    2. 필수 파일 누락
    echo    3. 디스크 공간 부족
    echo.
    echo 해결 방법:
    echo    python -m pip install pyinstaller
    echo.
    pause
    exit /b 1
)

echo.
echo ═══════════════════════════════════════════════════════════════
echo  🎉 빌드 완료!
echo ═══════════════════════════════════════════════════════════════
echo.
echo 📦 빌드 결과:
echo    - dist\DawnOfStellar.exe (단일 실행 파일)
echo    - dist\DawnOfStellar\ (배포용 패키지)
echo.
echo 🚀 사용 방법:
echo    1. dist\DawnOfStellar.exe를 더블클릭
echo    2. 또는 dist\DawnOfStellar\ 폴더를 압축하여 배포
echo.

:: 폴더 열기
set /p OPEN_FOLDER="빌드 결과 폴더를 여시겠습니까? (Y/N): "
if /i "%OPEN_FOLDER%"=="Y" (
    explorer dist
)

echo.
pause
