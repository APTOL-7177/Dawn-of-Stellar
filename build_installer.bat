@echo off
chcp 65001 >nul
title Dawn of Stellar 설치 프로그램 빌드

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo     Dawn of Stellar 설치 프로그램 빌드
echo ╚══════════════════════════════════════════════════════════╝
echo.

REM 현재 디렉토리로 이동
cd /d "%~dp0"

REM NSIS 설치 확인
where makensis >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [오류] NSIS가 PATH에 없습니다.
    echo.
    echo NSIS를 찾는 중...
    
    REM 일반적인 NSIS 설치 경로 확인
    if exist "C:\Program Files (x86)\NSIS\makensis.exe" (
        set "NSIS_PATH=C:\Program Files (x86)\NSIS\makensis.exe"
        echo NSIS를 찾았습니다: %NSIS_PATH%
        goto Build
    )
    
    if exist "C:\Program Files\NSIS\makensis.exe" (
        set "NSIS_PATH=C:\Program Files\NSIS\makensis.exe"
        echo NSIS를 찾았습니다: %NSIS_PATH%
        goto Build
    )
    
    echo.
    echo NSIS를 찾을 수 없습니다.
    echo.
    echo NSIS를 설치해야 합니다:
    echo 1. https://nsis.sourceforge.io/Download 에서 NSIS 다운로드
    echo 2. NSIS 설치
    echo 3. 설치 후 이 스크립트를 다시 실행하세요
    echo.
    echo 또는 makensis.exe의 전체 경로를 입력하세요:
    set /p NSIS_PATH="NSIS 경로: "
    if "%NSIS_PATH%"=="" (
        pause
        exit /b 1
    )
    goto Build
)

set "NSIS_PATH=makensis"
echo NSIS를 찾았습니다.
echo.

:Build
REM LICENSE 파일 확인
if not exist "LICENSE" (
    echo [경고] LICENSE 파일이 없습니다. 빈 파일을 생성합니다.
    echo. > LICENSE
)

echo 설치 프로그램을 빌드합니다...
echo.

REM NSIS 컴파일
"%NSIS_PATH%" install.nsi

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ╔══════════════════════════════════════════════════════════╗
    echo     빌드 완료!
    echo ╚══════════════════════════════════════════════════════════╝
    echo.
    echo 설치 프로그램: DawnOfStellar_Setup.exe
    echo.
) else (
    echo.
    echo [오류] 빌드 실패
    echo.
    echo 오류 메시지를 확인하세요.
    echo.
    pause
    exit /b %ERRORLEVEL%
)

pause
