@echo off
chcp 65001 >nul
echo ========================================
echo Dawn of Stellar - 개발 모드 패키징
echo ========================================
echo.

REM Python이 설치되어 있는지 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    pause
    exit /b 1
)

echo [1/7] Python 버전 확인...
python --version

echo.
echo [2/7] 필수 파일 확인...
if not exist "config.yaml" (
    echo [오류] config.yaml 파일을 찾을 수 없습니다.
    pause
    exit /b 1
)
if not exist "main.py" (
    echo [오류] main.py 파일을 찾을 수 없습니다.
    pause
    exit /b 1
)
echo 필수 파일 확인 완료.

echo.
echo [3/7] 필요한 패키지 설치 확인...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install pyinstaller >nul 2>&1

if errorlevel 1 (
    echo [오류] PyInstaller 설치에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo [4/7] 이전 빌드 파일 정리...
if exist "build" rmdir /s /q "build"
if exist "dist\DawnOfStellar_Dev" rmdir /s /q "dist\DawnOfStellar_Dev"
if exist "__pycache__" rmdir /s /q "__pycache__"

echo.
echo [5/7] 실행 파일 빌드 시작...
echo 이 작업은 몇 분 정도 걸릴 수 있습니다...
echo.

python -m PyInstaller build_folder.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo [오류] 빌드에 실패했습니다.
    pause
    exit /b 1
)

echo.
echo [6/7] 개발 모드 폴더로 복사...
if exist "dist\DawnOfStellar_Dev" rmdir /s /q "dist\DawnOfStellar_Dev"
rename "dist\DawnOfStellar" "DawnOfStellar_Dev"

echo.
echo [7/7] 게임 리소스 복사 (개발 모드)...
echo.

cd dist\DawnOfStellar_Dev

REM config.yaml 복사 후 개발 모드 활성화
copy ..\..\config.yaml config.yaml >nul

REM 개발 모드 활성화: sed 대체 (python으로 처리)
python -c "p='config.yaml'; t=open(p,encoding='utf-8').read(); t=t.replace('debug_mode: false','debug_mode: true').replace('enabled: false','enabled: true').replace('unlock_all_classes: false','unlock_all_classes: true'); open(p,'w',encoding='utf-8').write(t)"

REM 기본 메타 진행 파일 복사
if not exist user_data mkdir user_data
copy ..\..\config\meta_progress.json user_data\meta_progress.json >nul

REM 폰트 파일들 복사
copy ..\..\*.ttf . >nul 2>&1
copy ..\..\*.ttc . >nul 2>&1
copy ..\..\*.bdf . >nul 2>&1

REM data 폴더 복사
if exist ..\..\data xcopy ..\..\data data /E /I /H /Y >nul

REM assets 폴더 복사
if exist ..\..\assets xcopy ..\..\assets assets /E /I /H /Y >nul

cd ..\..

echo.
echo ========================================
echo 개발 모드 패키징 완료!
echo ========================================
echo.
echo 게임 폴더 위치: dist\DawnOfStellar_Dev
echo.
echo [주의] 이 빌드는 개발 모드입니다:
echo   - 모든 직업/특성/패시브 해금
echo   - 별의 파편 999999
echo   - 모든 시설 만렙
echo   - AI 관전 모드 사용 가능
echo.
pause
