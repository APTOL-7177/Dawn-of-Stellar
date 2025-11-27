@echo off
chcp 65001 >nul
echo ========================================
echo Dawn of Stellar - 업데이트 백업 도우미
echo ========================================
echo.

REM 현재 작업 디렉토리 확인
echo 현재 위치: %CD%
echo.

REM DawnOfStellar 폴더 존재 확인
if not exist "DawnOfStellar" (
    echo [오류] DawnOfStellar 폴더를 찾을 수 없습니다.
    echo.
    echo 이 스크립트는 DawnOfStellar 폴더가 있는 디렉토리에서 실행해야 합니다.
    echo 예: C:\Games\ 에 DawnOfStellar 폴더가 있다면 C:\Games\ 에서 실행
    echo.
    pause
    exit /b 1
)

echo [1/3] 기존 백업 정리 중...
if exist "DawnOfStellar_Backup" (
    echo 기존 백업 폴더를 삭제합니다...
    rmdir /s /q "DawnOfStellar_Backup"
)

echo.
echo [2/3] 게임 데이터 백업 중...
echo 이 작업은 게임 크기에 따라 몇 분 정도 걸릴 수 있습니다...
echo.

REM user_data 폴더 우선 백업 (가장 중요)
if exist "DawnOfStellar\user_data" (
    echo 사용자 데이터 백업 중...
    xcopy "DawnOfStellar\user_data" "DawnOfStellar_Backup\user_data" /E /H /I /Y >nul
) else (
    echo [경고] user_data 폴더를 찾을 수 없습니다.
)

REM 전체 게임 폴더 백업
echo 전체 게임 폴더 백업 중...
xcopy "DawnOfStellar" "DawnOfStellar_Backup" /E /H /I /Y >nul

echo.
echo [3/3] 백업 완료 확인...
if exist "DawnOfStellar_Backup\user_data" (
    echo ✅ 사용자 데이터 백업 성공
) else (
    echo ❌ 사용자 데이터 백업 실패
)

if exist "DawnOfStellar_Backup\DawnOfStellar.exe" (
    echo ✅ 게임 파일 백업 성공
) else (
    echo ❌ 게임 파일 백업 실패
)

echo.
echo ========================================
echo 백업 완료!
echo ========================================
echo.
echo 백업 위치: %CD%\DawnOfStellar_Backup
echo.
echo 백업된 내용:
echo - 게임 실행 파일 및 리소스
echo - 사용자 세이브 데이터 (meta_progress.json)
echo - 게임 설정 및 로그
echo.
echo 새 버전 업데이트 후 문제가 발생하면
echo 이 백업본에서 user_data 폴더를 복원하세요.
echo.
pause
