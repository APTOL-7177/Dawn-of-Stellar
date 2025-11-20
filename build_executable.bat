@echo off
chcp 65001 >nul
echo ========================================
echo Dawn of Stellar - 실행 파일 빌드
echo ========================================
echo.

REM Python이 설치되어 있는지 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo Python 3.10 이상을 설치해주세요.
    pause
    exit /b 1
)

echo [1/5] Python 버전 확인...
python --version

echo.
echo [2/5] 필수 파일 확인...
if not exist "config.yaml" (
    echo [오류] config.yaml 파일을 찾을 수 없습니다.
    echo 현재 위치: %CD%
    echo 이 스크립트는 프로젝트 루트 폴더에서 실행해야 합니다.
    pause
    exit /b 1
)
if not exist "main.py" (
    echo [오류] main.py 파일을 찾을 수 없습니다.
    echo 현재 위치: %CD%
    echo 이 스크립트는 프로젝트 루트 폴더에서 실행해야 합니다.
    pause
    exit /b 1
)
if not exist "data" (
    echo [경고] data 폴더를 찾을 수 없습니다.
)
if not exist "assets" (
    echo [경고] assets 폴더를 찾을 수 없습니다.
)
echo 필수 파일 확인 완료.

echo.
echo [3/5] 필요한 패키지 설치 확인...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install pyinstaller >nul 2>&1

if errorlevel 1 (
    echo [오류] PyInstaller 설치에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo [4/5] 이전 빌드 파일 정리...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "__pycache__" rmdir /s /q "__pycache__"

echo.
echo [5/5] 실행 파일 빌드 시작...
echo 이 작업은 몇 분 정도 걸릴 수 있습니다...
echo.

python -m PyInstaller build.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo [오류] 빌드에 실패했습니다.
    echo 오류 메시지를 확인해주세요.
    pause
    exit /b 1
)

echo.
echo ========================================
echo 빌드 완료!
echo ========================================
echo.
echo 실행 파일 위치: dist\DawnOfStellar.exe
echo.
echo 이제 dist 폴더의 모든 내용을 다른 컴퓨터로 복사하면
echo Python 없이도 게임을 실행할 수 있습니다.
echo.
pause

