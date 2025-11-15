@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion

:: ====================================================================
:: Dawn of Stellar - 완전판 원클릭 설치 스크립트
:: Git 클론 + Python 설치 + 패키지 설치 + 게임 실행까지 모두 자동!
:: ====================================================================

title Dawn of Stellar 완전 자동 설치기

color 0A
mode con: cols=80 lines=40
cls

echo.
echo ╔══════════════════════════════════════════════════════════════════════╗
echo ║                                                                      ║
echo ║          ⭐⭐⭐ Dawn of Stellar (별빛의 여명) ⭐⭐⭐              ║
echo ║                                                                      ║
echo ║                      완전 자동 설치 프로그램                        ║
echo ║                                                                      ║
echo ║    이 프로그램은 아무것도 없는 상태에서 게임을 바로 실행합니다!    ║
echo ║                                                                      ║
echo ╚══════════════════════════════════════════════════════════════════════╝
echo.
echo    🎮 Final Fantasy 스타일 로그라이크 RPG
echo    ⚔️  28개 직업 × ATB 전투 × AI 동료 × 멀티플레이어
echo    🌟 완전한 한국어 지원
echo.
echo ══════════════════════════════════════════════════════════════════════
echo.
echo    📌 자동으로 설치되는 항목:
echo       1. Git (소스 코드 다운로드용)
echo       2. Python 3.11 (게임 실행 환경)
echo       3. 게임 필수 패키지 (TCOD, PyYAML 등)
echo       4. Dawn of Stellar 게임 파일
echo.
echo ══════════════════════════════════════════════════════════════════════
echo.

timeout /t 3 /nobreak >nul

:: ====================================================================
:: 관리자 권한 확인
:: ====================================================================

echo [확인] 관리자 권한 체크...
net session >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ╔══════════════════════════════════════════════════════════════════════╗
    echo ║  ⚠️  관리자 권한이 필요합니다                                      ║
    echo ╚══════════════════════════════════════════════════════════════════════╝
    echo.
    echo 📌 해결 방법:
    echo    1. 이 파일을 우클릭
    echo    2. "관리자 권한으로 실행" 선택
    echo    3. 다시 실행
    echo.
    pause
    exit /b 1
)
echo ✅ 관리자 권한 확인됨
echo.

:: ====================================================================
:: 설치 디렉토리 설정
:: ====================================================================

echo [설정] 설치 위치 선택...
echo.
echo    현재 위치: %CD%
echo.

set "GAME_DIR=%USERPROFILE%\Desktop\Dawn-of-Stellar"

echo    권장 설치 위치: %GAME_DIR%
echo.
set /p CUSTOM_DIR="다른 위치에 설치하시겠습니까? (Y/N, 기본값=N): "

if /i "%CUSTOM_DIR%"=="Y" (
    echo.
    set /p GAME_DIR="설치 경로를 입력하세요: "
)

echo.
echo ✅ 설치 위치: %GAME_DIR%
echo.

:: ====================================================================
:: Git 설치 확인 및 자동 설치
:: ====================================================================

echo [1/7] Git 확인 중...
echo.

git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Git이 설치되어 있지 않습니다.
    echo.
    echo 📥 Git을 자동으로 설치합니다...
    echo.

    :: Git 설치 파일 다운로드
    set GIT_URL=https://github.com/git-for-windows/git/releases/download/v2.45.2.windows.1/Git-2.45.2-64-bit.exe
    set GIT_INSTALLER=git-installer.exe

    echo    다운로드 중... (약 50MB, 시간이 걸릴 수 있습니다)
    echo.

    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Write-Host 'Git 다운로드 시작...'; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%GIT_URL%' -OutFile '%GIT_INSTALLER%'; Write-Host 'Git 다운로드 완료!'}"

    if not exist %GIT_INSTALLER% (
        echo.
        echo ❌ Git 다운로드 실패!
        echo.
        echo 📌 수동 설치:
        echo    https://git-scm.com/download/win
        echo.
        pause
        exit /b 1
    )

    echo ✅ 다운로드 완료!
    echo.
    echo 📦 Git 설치 중... (2-3분 소요)
    echo.

    :: Git 자동 설치 (silent mode)
    %GIT_INSTALLER% /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /COMPONENTS="icons,ext\reg\shellhere,assoc,assoc_sh"

    timeout /t 10 /nobreak >nul

    :: 설치 파일 삭제
    del %GIT_INSTALLER% >nul 2>&1

    :: PATH 새로고침
    call :RefreshEnv

    :: Git 재확인
    git --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo ⚠️  Git이 설치되었지만 PATH 설정이 필요합니다.
        echo.
        echo 📌 컴퓨터를 재부팅하고 이 스크립트를 다시 실행하세요.
        echo.
        pause
        exit /b 1
    )

    echo ✅ Git 설치 완료!
    echo.
) else (
    for /f "tokens=3" %%i in ('git --version 2^>^&1') do set GIT_VERSION=%%i
    echo ✅ Git !GIT_VERSION! 이미 설치됨
    echo.
)

:: ====================================================================
:: 게임 소스 코드 다운로드
:: ====================================================================

echo [2/7] 게임 다운로드 중...
echo.

:: GitHub 저장소 URL (실제 저장소로 변경 필요)
set REPO_URL=https://github.com/APTOL-7177/Dawn-of-Stellar.git

echo    저장소: %REPO_URL%
echo    위치: %GAME_DIR%
echo.

:: 이미 존재하는 경우 업데이트
if exist "%GAME_DIR%" (
    echo ⚠️  설치 폴더가 이미 존재합니다.
    echo.
    set /p UPDATE_GAME="기존 게임을 업데이트하시겠습니까? (Y/N): "

    if /i "!UPDATE_GAME!"=="Y" (
        cd /d "%GAME_DIR%"
        echo.
        echo 📥 최신 버전으로 업데이트 중...
        git pull
        echo.
        echo ✅ 업데이트 완료!
        echo.
    ) else (
        echo.
        echo ⏭️  다운로드 건너뜀 (기존 파일 사용)
        echo.
    )
) else (
    echo 📥 게임 파일 다운로드 중... (약 30MB)
    echo.

    git clone %REPO_URL% "%GAME_DIR%"

    if %errorlevel% neq 0 (
        echo.
        echo ❌ 게임 다운로드 실패!
        echo.
        echo 📌 가능한 원인:
        echo    1. 인터넷 연결 끊김
        echo    2. 저장소 접근 권한 없음
        echo    3. 디스크 공간 부족
        echo.
        pause
        exit /b 1
    )

    echo.
    echo ✅ 게임 다운로드 완료!
    echo.
)

:: 게임 디렉토리로 이동
cd /d "%GAME_DIR%"

:: ====================================================================
:: Python 설치 확인 및 자동 설치
:: ====================================================================

echo [3/7] Python 확인 중...
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Python이 설치되어 있지 않습니다.
    echo.
    echo 📥 Python 3.11을 자동으로 설치합니다...
    echo.

    :: Python 설치 파일 다운로드
    set PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
    set PYTHON_INSTALLER=python-installer.exe

    echo    다운로드 중... (약 25MB)
    echo.

    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'; Write-Host 'Python 다운로드 완료!'}"

    if not exist %PYTHON_INSTALLER% (
        echo.
        echo ❌ Python 다운로드 실패!
        echo.
        pause
        exit /b 1
    )

    echo ✅ 다운로드 완료!
    echo.
    echo 📦 Python 설치 중... (2-3분 소요)
    echo.

    :: Python 자동 설치
    %PYTHON_INSTALLER% /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

    timeout /t 5 /nobreak >nul
    del %PYTHON_INSTALLER% >nul 2>&1

    call :RefreshEnv

    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo ⚠️  Python PATH 설정 필요. 재부팅 후 다시 실행하세요.
        echo.
        pause
        exit /b 1
    )

    echo ✅ Python 설치 완료!
    echo.
) else (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo ✅ Python !PYTHON_VERSION! 이미 설치됨
    echo.
)

:: ====================================================================
:: pip 업그레이드
:: ====================================================================

echo [4/7] pip 업그레이드 중...
echo.

python -m pip install --upgrade pip --quiet >nul 2>&1
echo ✅ pip 업그레이드 완료!
echo.

:: ====================================================================
:: 게임 패키지 설치
:: ====================================================================

echo [5/7] 게임 패키지 설치 중...
echo.
echo    TCOD, PyYAML, NumPy 등 필수 패키지 설치
echo    시간이 다소 걸릴 수 있습니다...
echo.

:: requirements-minimal.txt가 있으면 사용, 없으면 직접 설치
if exist "requirements-minimal.txt" (
    python -m pip install -r requirements-minimal.txt --quiet
) else (
    python -m pip install tcod pyyaml numpy --quiet
)

if %errorlevel% neq 0 (
    echo.
    echo ❌ 패키지 설치 실패!
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ 패키지 설치 완료!
echo.

:: ====================================================================
:: 설치 검증
:: ====================================================================

echo [6/7] 설치 검증 중...
echo.

python -c "import tcod, yaml; print('✅ 모든 필수 모듈 로드 성공')" 2>nul
if %errorlevel% neq 0 (
    echo ❌ 모듈 로드 실패
    pause
    exit /b 1
)

echo ✅ 설치 검증 완료!
echo.

:: ====================================================================
:: 바로가기 생성
:: ====================================================================

echo [7/7] 바로가기 생성 중...
echo.

:: 실행 스크립트 생성
if not exist "run.bat" (
    (
        echo @echo off
        echo chcp 65001 ^> nul
        echo title Dawn of Stellar
        echo python main.py
        echo pause
    ) > run.bat
    echo ✅ run.bat 생성
)

:: 데스크톱 바로가기 생성 (PowerShell 사용)
set DESKTOP=%USERPROFILE%\Desktop
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP%\Dawn of Stellar.lnk'); $Shortcut.TargetPath = '%GAME_DIR%\run.bat'; $Shortcut.WorkingDirectory = '%GAME_DIR%'; $Shortcut.Description = 'Dawn of Stellar 게임 실행'; $Shortcut.Save()" >nul 2>&1

if exist "%DESKTOP%\Dawn of Stellar.lnk" (
    echo ✅ 데스크톱 바로가기 생성 완료
) else (
    echo ⚠️  바로가기 생성 실패 (직접 run.bat 실행)
)

echo.

:: ====================================================================
:: 설치 완료!
:: ====================================================================

cls
color 0E

echo.
echo ╔══════════════════════════════════════════════════════════════════════╗
echo ║                                                                      ║
echo ║               🎉🎉🎉 설치가 완료되었습니다! 🎉🎉🎉              ║
echo ║                                                                      ║
echo ╚══════════════════════════════════════════════════════════════════════╝
echo.
echo ══════════════════════════════════════════════════════════════════════
echo.
echo    설치 완료 요약:
echo.
echo       ✅ Git 설치/확인 완료
echo       ✅ 게임 파일 다운로드 완료
echo       ✅ Python 3.11 설치 완료
echo       ✅ 필수 패키지 설치 완료
echo       ✅ 바로가기 생성 완료
echo.
echo ──────────────────────────────────────────────────────────────────────
echo.
echo    🎮 게임 실행 방법:
echo.
echo       방법 1: 데스크톱의 "Dawn of Stellar" 바로가기 클릭
echo       방법 2: %GAME_DIR%\run.bat 실행
echo       방법 3: 명령어: python main.py
echo.
echo ──────────────────────────────────────────────────────────────────────
echo.
echo    🛠️  고급 옵션:
echo.
echo       개발 모드: python main.py --dev
echo       디버그 모드: python main.py --debug
echo.
echo ══════════════════════════════════════════════════════════════════════
echo.

:: ====================================================================
:: 즉시 실행 옵션
:: ====================================================================

echo.
set /p RUN_NOW="지금 바로 게임을 시작하시겠습니까? (Y/N): "
echo.

if /i "%RUN_NOW%"=="Y" (
    color 0B
    echo ═══════════════════════════════════════════════════════════
    echo    🎮 게임을 시작합니다... 즐거운 플레이 되세요! 🎮
    echo ═══════════════════════════════════════════════════════════
    echo.
    timeout /t 2 /nobreak >nul

    python main.py

    if %errorlevel% neq 0 (
        color 0C
        echo.
        echo ⚠️  게임 실행 중 오류 발생
        echo 📌 logs/ 폴더의 로그 파일을 확인하세요.
        echo.
        pause
    )
) else (
    echo.
    echo 👋 데스크톱 바로가기를 클릭하여 게임을 즐기세요!
    echo.
)

echo.
echo 설치 프로그램을 종료합니다.
timeout /t 5
exit /b 0

:: ====================================================================
:: 함수: 환경변수 새로고침
:: ====================================================================
:RefreshEnv
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "SYS_PATH=%%b"
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "USER_PATH=%%b"
set "PATH=%SYS_PATH%;%USER_PATH%;C:\Program Files\Git\cmd;%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts"
goto :eof
