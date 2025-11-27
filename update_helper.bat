@echo off
chcp 65001 >nul
echo ========================================
echo Dawn of Stellar - 자동 업데이트 도우미
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

REM 새 버전 파일 존재 확인
set "NEW_VERSION_ZIP="
for %%f in (DawnOfStellar_v*.zip) do (
    set "NEW_VERSION_ZIP=%%f"
)

if "%NEW_VERSION_ZIP%"=="" (
    echo [안내] 새 버전 ZIP 파일을 찾을 수 없습니다.
    echo.
    echo 다음 중 하나의 새 버전 파일을 이 폴더에 다운로드해주세요:
    echo - DawnOfStellar_v6.2.0.zip
    echo - DawnOfStellar_v7.0.0.zip
    echo - 또는 최신 버전 파일
    echo.
    echo 그런 다음 이 스크립트를 다시 실행하세요.
    echo.
    pause
    exit /b 1
)

echo 찾은 새 버전 파일: %NEW_VERSION_ZIP%
echo.

REM 새 버전 폴더명 추출 (확장자 제거)
set "NEW_VERSION_NAME=%NEW_VERSION_ZIP:.zip=%"

echo [1/5] 백업 생성 중...
echo.

REM 기존 백업 스크립트 호출 (있으면)
if exist "update_backup.bat" (
    call update_backup.bat
) else (
    REM 수동 백업
    if exist "DawnOfStellar_Backup" rmdir /s /q "DawnOfStellar_Backup"
    xcopy "DawnOfStellar\user_data" "DawnOfStellar_Backup\user_data" /E /H /I /Y >nul 2>&1
    echo 기본 백업 완료
)

echo.
echo [2/5] 새 버전 압축 해제 중...
echo.

REM 새 버전 폴더가 이미 존재하면 삭제
if exist "%NEW_VERSION_NAME%" (
    echo 기존 새 버전 폴더 삭제 중...
    rmdir /s /q "%NEW_VERSION_NAME%"
)

REM 압축 해제 (PowerShell 사용)
powershell -command "Expand-Archive -Path '%NEW_VERSION_ZIP%' -DestinationPath '%NEW_VERSION_NAME%' -Force"

if errorlevel 1 (
    echo [오류] 압축 해제에 실패했습니다.
    echo 수동으로 %NEW_VERSION_ZIP% 파일을 압축 해제해주세요.
    pause
    exit /b 1
)

echo 압축 해제 완료
echo.

echo [3/5] 게임 데이터 이전 중...
echo.

REM user_data 폴더 복사
if exist "DawnOfStellar_Backup\user_data" (
    echo 사용자 데이터 복사 중...
    xcopy "DawnOfStellar_Backup\user_data" "%NEW_VERSION_NAME%\user_data" /E /H /Y >nul
    echo ✅ 사용자 데이터 이전 완료
) else (
    echo ⚠️ 백업된 사용자 데이터를 찾을 수 없습니다.
    echo 새 버전에서 게임을 처음 시작해야 할 수 있습니다.
)

echo.
echo [4/5] 폴더 정리 및 이름 변경...
echo.

REM 기존 게임 폴더 백업
set "OLD_BACKUP=DawnOfStellar_Old_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%"
if exist "DawnOfStellar_Old" rmdir /s /q "DawnOfStellar_Old"
ren "DawnOfStellar" "DawnOfStellar_Old"

REM 새 버전을 메인 폴더로
ren "%NEW_VERSION_NAME%" "DawnOfStellar"

echo ✅ 폴더 정리 완료
echo.

echo [5/5] 업데이트 검증...
echo.

REM 새 버전 실행 파일 확인
if exist "DawnOfStellar\DawnOfStellar.exe" (
    echo ✅ 새 버전 설치 성공
    echo.
    echo 🎮 업데이트 완료! 🎉
    echo.
    echo 게임 실행 방법:
    echo 1. DawnOfStellar 폴더 열기
    echo 2. DawnOfStellar.exe 더블클릭
    echo.
    echo 백업본 위치: DawnOfStellar_Old (문제가 생기면 여기서 복원)
    echo 백업본 위치: DawnOfStellar_Backup (사용자 데이터)
    echo.
) else (
    echo ❌ 새 버전 설치 실패
    echo 수동으로 업데이트를 진행해주세요.
    echo.
    pause
    exit /b 1
)

echo ========================================
echo 업데이트 프로세스 완료!
echo ========================================
echo.
echo 추가 작업:
echo - 새 버전 게임을 실행해서 정상 작동 확인
echo - 문제가 없으면 DawnOfStellar_Old 폴더 삭제 가능
echo - 백업본(DawnOfStellar_Backup)은 안전하게 보관
echo.
pause
