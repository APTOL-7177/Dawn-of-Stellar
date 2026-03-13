@echo off
chcp 65001 >nul
echo ========================================
echo Dawn of Stellar - itch.io 배포 (4채널)
echo ========================================
echo.
echo 채널: windows, windows-dev, linux, linux-dev
echo.

REM butler 설치 확인
butler version >nul 2>&1
if errorlevel 1 (
    echo [오류] butler가 설치되어 있지 않습니다.
    echo https://itch.io/docs/butler/installing.html 에서 설치해주세요.
    echo.
    echo 빠른 설치:
    echo   1. https://broth.itch.ovh/butler/windows-amd64/LATEST/archive/default 다운로드
    echo   2. 압축 해제 후 PATH에 추가
    echo   3. butler login 실행
    pause
    exit /b 1
)

REM 버전 자동 증가
echo [1/8] 버전 자동 증가 중...
set BUMP_TYPE=patch
if "%1"=="minor" set BUMP_TYPE=minor
if "%1"=="major" set BUMP_TYPE=major

python bump_version.py %BUMP_TYPE%
if errorlevel 1 (
    echo [오류] 버전 증가에 실패했습니다.
    pause
    exit /b 1
)

REM 새 버전 읽기
for /f "tokens=2 delims=: " %%a in ('findstr /c:"version:" config.yaml') do set GAME_VERSION=%%a

echo.
echo 배포 버전: %GAME_VERSION%
echo 배포 대상: aptol/dawn-of-stellar
echo.

REM ============ Windows 빌드 ============
echo [2/8] Windows 빌드 중... (몇 분 소요)
echo.

REM 이전 빌드 정리
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

python -m PyInstaller build_folder.spec --clean --noconfirm
if errorlevel 1 (
    echo [오류] Windows 빌드에 실패했습니다.
    pause
    exit /b 1
)

REM Windows 순정 리소스 복사
cd dist\DawnOfStellar
copy ..\..\config.yaml config.yaml >nul
if not exist user_data mkdir user_data
copy ..\..\config\meta_progress.json user_data\meta_progress.json >nul
copy ..\..\*.ttf . >nul 2>&1
copy ..\..\*.ttc . >nul 2>&1
copy ..\..\*.bdf . >nul 2>&1
if exist ..\..\data xcopy ..\..\data data /E /I /H /Y >nul
if exist ..\..\assets xcopy ..\..\assets assets /E /I /H /Y >nul
cd ..\..

echo %GAME_VERSION%> dist\DawnOfStellar\version.txt

echo.
echo Windows 순정 빌드 완료!

REM ============ Windows 개발 모드 (복사 + config 패치) ============
echo [3/8] Windows 개발 모드 빌드 생성 중...

xcopy dist\DawnOfStellar dist\DawnOfStellar_Dev /E /I /H /Y >nul

REM 개발 모드 config 패치
python -c "p='dist/DawnOfStellar_Dev/config.yaml'; t=open(p,encoding='utf-8').read(); t=t.replace('debug_mode: false','debug_mode: true').replace('  enabled: false','  enabled: true').replace('unlock_all_classes: false','unlock_all_classes: true'); open(p,'w',encoding='utf-8').write(t)"

echo Windows 개발 모드 빌드 완료!
echo.

REM ============ Linux 빌드 (WSL) ============
echo [4/8] Linux 빌드 중 (WSL)...
echo.

wsl -d Ubuntu -- bash -c "echo WSL_OK" >nul 2>&1
if errorlevel 1 (
    echo [경고] WSL Ubuntu를 찾을 수 없습니다. Linux 빌드를 건너뜁니다.
    echo WSL 설치: wsl --install -d Ubuntu
    set LINUX_BUILD=0
    goto :push_all
)

REM WSL에서 Linux 빌드 실행
set WSL_PROJECT_PATH=/mnt/x/develop/Dos-retro/Dawn-of-Stellar
wsl -d Ubuntu -- bash -c "cd '%WSL_PROJECT_PATH%' && sed -i 's/\r$//' build_linux.sh && bash build_linux.sh"
if errorlevel 1 (
    echo [경고] Linux 빌드에 실패했습니다. Windows만 배포합니다.
    set LINUX_BUILD=0
    goto :push_all
)
set LINUX_BUILD=1

echo %GAME_VERSION%> dist_linux\DawnOfStellar\version.txt

echo.
echo Linux 순정 빌드 완료!

REM ============ Linux 개발 모드 (복사 + config 패치) ============
echo [5/8] Linux 개발 모드 빌드 생성 중...

xcopy dist_linux\DawnOfStellar dist_linux\DawnOfStellar_Dev /E /I /H /Y >nul

REM 개발 모드 config 패치
python -c "p='dist_linux/DawnOfStellar_Dev/config.yaml'; t=open(p,encoding='utf-8').read(); t=t.replace('debug_mode: false','debug_mode: true').replace('  enabled: false','  enabled: true').replace('unlock_all_classes: false','unlock_all_classes: true'); open(p,'w',encoding='utf-8').write(t)"

echo Linux 개발 모드 빌드 완료!
echo.

REM ============ Push 4채널 ============
:push_all
echo [6/8] Windows 순정 푸시 중...
butler push dist\DawnOfStellar aptol/dawn-of-stellar:windows --userversion %GAME_VERSION%
if errorlevel 1 (
    echo [오류] Windows 순정 푸시 실패.
    pause
    exit /b 1
)

echo [7/8] Windows 개발 모드 푸시 중...
butler push dist\DawnOfStellar_Dev aptol/dawn-of-stellar:windows-dev --userversion %GAME_VERSION%
if errorlevel 1 (
    echo [경고] Windows 개발 모드 푸시 실패.
)

if "%LINUX_BUILD%"=="0" goto :done

echo [8/8] Linux 푸시 중 (순정 + 개발 모드)...
butler push dist_linux\DawnOfStellar aptol/dawn-of-stellar:linux --userversion %GAME_VERSION%
if errorlevel 1 (
    echo [경고] Linux 순정 푸시 실패.
)

butler push dist_linux\DawnOfStellar_Dev aptol/dawn-of-stellar:linux-dev --userversion %GAME_VERSION%
if errorlevel 1 (
    echo [경고] Linux 개발 모드 푸시 실패.
)

:done
echo.
echo ========================================
echo 배포 완료! v%GAME_VERSION%
echo ========================================
echo.
echo itch.io: https://aptol.itch.io/dawn-of-stellar
echo.
if "%LINUX_BUILD%"=="1" (
    echo 채널 4개 배포 완료:
    echo   - windows      : 순정 빌드
    echo   - windows-dev  : 개발 모드 (모든 요소 해금)
    echo   - linux        : 순정 빌드
    echo   - linux-dev    : 개발 모드 (모든 요소 해금)
) else (
    echo 채널 2개 배포 완료:
    echo   - windows      : 순정 빌드
    echo   - windows-dev  : 개발 모드 (모든 요소 해금)
    echo   [참고] Linux 빌드가 건너뛰어졌습니다.
)
echo.
echo 버전: %GAME_VERSION%
echo.
echo 사용법:
echo   push_itch.bat         패치 버전 +1 (1.0.0 -^> 1.0.1)
echo   push_itch.bat minor   마이너 버전 +1 (1.0.1 -^> 1.1.0)
echo   push_itch.bat major   메이저 버전 +1 (1.1.0 -^> 2.0.0)
echo.
pause
