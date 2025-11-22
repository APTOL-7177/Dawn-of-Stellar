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
    echo [오류] NSIS가 설치되어 있지 않습니다.
    echo.
    echo NSIS를 설치해야 합니다:
    echo 1. https://nsis.sourceforge.io/Download 에서 NSIS 다운로드
    echo 2. NSIS 설치 후 PATH에 추가하거나
    echo 3. makensis.exe의 전체 경로를 사용하세요
    echo.
    echo 예: "C:\Program Files (x86)\NSIS\makensis.exe" install.nsi
    echo.
    pause
    exit /b 1
)

echo NSIS를 찾았습니다.
echo.

REM LICENSE 파일 확인
if not exist "LICENSE" (
    echo [경고] LICENSE 파일이 없습니다. 빈 파일을 생성합니다.
    echo. > LICENSE
)

echo 설치 프로그램을 빌드합니다...
echo.

REM NSIS 컴파일
makensis install.nsi

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
    pause
    exit /b %ERRORLEVEL%
)

pause

