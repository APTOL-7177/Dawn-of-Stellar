@echo off
chcp 65001 >nul
echo ========================================
echo Dawn of Stellar - 최종 패키징
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

echo [1/6] Python 버전 확인...
python --version

echo.
echo [2/6] 필수 파일 확인...
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
echo 필수 파일 확인 완료.

echo.
echo [3/6] 필요한 패키지 설치 확인...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install pyinstaller >nul 2>&1

if errorlevel 1 (
    echo [오류] PyInstaller 설치에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo [4/6] 이전 빌드 파일 정리...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "__pycache__" rmdir /s /q "__pycache__"

echo.
echo [5/6] 실행 파일 빌드 시작...
echo 이 작업은 몇 분 정도 걸릴 수 있습니다...
echo.

python -m PyInstaller build_folder.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo [오류] 빌드에 실패했습니다.
    echo 오류 메시지를 확인해주세요.
    pause
    exit /b 1
)

echo.
echo [6/6] 게임 리소스 복사...
echo.

REM DawnOfStellar 폴더로 이동
cd dist\DawnOfStellar

REM config.yaml 복사
copy ..\..\config.yaml config.yaml >nul

REM 폰트 파일들 복사
copy ..\..\*.ttf . >nul 2>&1
copy ..\..\*.ttc . >nul 2>&1
copy ..\..\*.bdf . >nul 2>&1

REM assets 폴더 복사
if exist ..\..\assets xcopy ..\..\assets assets /E /I /H /Y >nul

REM 상위 디렉토리로 돌아가기
cd ..\..

echo.
echo ========================================
echo 패키징 완료!
echo ========================================
echo.
echo 게임 폴더 위치: dist\DawnOfStellar
echo.
echo 게임 실행 방법:
echo 1. dist\DawnOfStellar 폴더로 이동
echo 2. DawnOfStellar.exe 더블클릭
echo.
echo 배포 방법:
echo 1. dist\DawnOfStellar 폴더 전체를 압축
echo 2. DawnOfStellar.zip 파일로 배포
echo.
pause
