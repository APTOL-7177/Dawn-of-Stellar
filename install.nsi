; Dawn of Stellar 설치 프로그램
; NSIS 스크립트
; 버전: 1.0.0

;--------------------------------
; 일반 설정

!define PRODUCT_NAME "Dawn of Stellar"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "APTOL-7177"
!define PRODUCT_WEB_SITE "https://github.com/APTOL-7177/Dawn-of-Stellar"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\DawnOfStellar.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

;--------------------------------
; 압축 설정

SetCompressor /SOLID lzma
SetCompressorDictSize 32

;--------------------------------
; MUI 1.67 호환 설정

!include "MUI2.nsh"

;--------------------------------
; MUI 설정

!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; 설치 마법사 페이지
!insertmacro MUI_PAGE_WELCOME
!ifdef LICENSE
!insertmacro MUI_PAGE_LICENSE "${LICENSE}"
!endif
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; 제거 마법사 페이지
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

;--------------------------------
; 언어 파일

!insertmacro MUI_LANGUAGE "Korean"

;--------------------------------
; MUI 예약 파일

!insertmacro MUI_RESERVEFILE_LANGDLL

;--------------------------------
; 설치 프로그램 정보

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "DawnOfStellar_Setup.exe"
InstallDir "$PROGRAMFILES\${PRODUCT_NAME}"
InstallDirRegKey HKCU "${PRODUCT_DIR_REGKEY}" ""
RequestExecutionLevel admin
ShowInstDetails show
ShowUnInstDetails show

;--------------------------------
; 변수

Var PythonPath
Var PythonVersion
Var GitPath
Var GitVersion
Var InstallPython
Var InstallGit
Var CloneRepo
Var InstallDir

;--------------------------------
; 설치 타입

InstType "전체 설치 (권장)"
InstType "최소 설치"

;--------------------------------
; 섹션

Section "게임 파일" SEC01
    SectionIn RO 1 2
    
    SetOutPath "$INSTDIR"
    
    ; 필수 파일 복사
    File /r "main.py"
    File /r "config.yaml"
    File /r "requirements.txt"
    File /r "README.md"
    File /r "LICENSE"
    
    ; 소스 코드 복사
    SetOutPath "$INSTDIR\src"
    File /r "src\*.*"
    
    ; 데이터 파일 복사
    SetOutPath "$INSTDIR\data"
    File /r "data\*.*"
    
    ; 설정 파일 복사
    SetOutPath "$INSTDIR\config"
    File /r "config\*.*"
    
    ; 폰트 파일 복사
    File "D2Coding.ttc"
    File "D2Coding.ttf"
    File "dalmoori.ttf"
    File "DOSMyungjo.ttf"
    File "GalmuriMono9.ttf"
    
    ; 문서 복사
    SetOutPath "$INSTDIR\docs"
    File /r "docs\*.*"
    
    ; 런처 파일 복사
    SetOutPath "$INSTDIR"
    File "launcher.py"
    File "launcher.bat"
    
    ; 시작 스크립트 생성 (런처 사용)
    SetOutPath "$INSTDIR"
    FileOpen $0 "$INSTDIR\start_game.bat" w
    FileWrite $0 "@echo off$\r$\n"
    FileWrite $0 "chcp 65001 >nul$\r$\n"
    FileWrite $0 "cd /d \"$INSTDIR\"$\r$\n"
    FileWrite $0 "python launcher.py$\r$\n"
    FileWrite $0 "if errorlevel 1 ($\r$\n"
    FileWrite $0 "    echo.$\r$\n"
    FileWrite $0 "    echo 오류가 발생했습니다.$\r$\n"
    FileWrite $0 "    pause$\r$\n"
    FileWrite $0 ")$\r$\n"
    FileClose $0
    
    ; 직접 실행 스크립트 (런처 없이)
    FileOpen $0 "$INSTDIR\start_game_direct.bat" w
    FileWrite $0 "@echo off$\r$\n"
    FileWrite $0 "chcp 65001 >nul$\r$\n"
    FileWrite $0 "cd /d \"$INSTDIR\"$\r$\n"
    FileWrite $0 "python main.py$\r$\n"
    FileWrite $0 "pause$\r$\n"
    FileClose $0
    
    ; 개발 모드 시작 스크립트 생성
    FileOpen $0 "$INSTDIR\start_game_dev.bat" w
    FileWrite $0 "@echo off$\r$\n"
    FileWrite $0 "chcp 65001 >nul$\r$\n"
    FileWrite $0 "cd /d \"$INSTDIR\"$\r$\n"
    FileWrite $0 "python main.py --dev$\r$\n"
    FileWrite $0 "pause$\r$\n"
    FileClose $0
    
    ; 레지스트리 키 생성
    WriteRegStr HKCR "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\main.py"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\main.py"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_ROOT_KEY}\${PRODUCT_NAME}" "Path" "$INSTDIR"
SectionEnd

Section "바로가기" SEC02
    SectionIn 1
    
    ; 시작 메뉴 바로가기
    CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\start_game.bat" "" "$INSTDIR\launcher.py" 0
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME} (런처).lnk" "$INSTDIR\launcher.bat" "" "$INSTDIR\launcher.py" 0
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME} (직접 실행).lnk" "$INSTDIR\start_game_direct.bat" "" "$INSTDIR\main.py" 0
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME} (개발 모드).lnk" "$INSTDIR\start_game_dev.bat" "" "$INSTDIR\main.py" 0
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\제거.lnk" "$INSTDIR\uninstall.exe"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\웹사이트.lnk" "${PRODUCT_WEB_SITE}"
    
    ; 바탕화면 바로가기 (런처 사용)
    CreateShortCut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\start_game.bat" "" "$INSTDIR\launcher.py" 0
SectionEnd

Section "Python 환경 설정" SEC03
    SectionIn 1 2
    
    DetailPrint "Python 설치 확인 중..."
    
    ; Python 경로 찾기
    ClearErrors
    ReadEnvStr $PythonPath "PYTHON"
    IfErrors 0 PythonFound
    
    ; PATH에서 Python 찾기
    ClearErrors
    ExecWait 'python --version' $0
    IfErrors 0 PythonFound
    
    ; 일반적인 Python 설치 경로 확인
    IfFileExists "$PROGRAMFILES\Python*\python.exe" 0 PythonNotFound
    FindFirst $0 $1 "$PROGRAMFILES\Python*"
    StrCpy $PythonPath "$PROGRAMFILES\$1\python.exe"
    FindClose $0
    Goto PythonFound
    
PythonNotFound:
    DetailPrint "Python이 설치되어 있지 않습니다."
    MessageBox MB_YESNO|MB_ICONQUESTION "Python 3.10 이상이 필요합니다.$\n$\nPython 다운로드 페이지를 여시겠습니까?" IDYES OpenPythonDownload IDNO SkipPython
    OpenPythonDownload:
        ExecShell "open" "https://www.python.org/downloads/"
        MessageBox MB_OK "Python 설치 시 'Add Python to PATH' 옵션을 체크하세요!$\n$\n설치 후 이 설치 프로그램을 다시 실행하세요."
    SkipPython:
    Goto PythonCheckDone
    
PythonFound:
    DetailPrint "Python을 찾았습니다: $PythonPath"
    
    ; Python 버전 확인
    ClearErrors
    ExecWait 'python --version' $0
    IfErrors PythonVersionError 0
    
    ; pip 업그레이드
    DetailPrint "pip 업그레이드 중..."
    ExecWait 'python -m pip install --upgrade pip' $0
    IfErrors 0 PipUpgraded
    DetailPrint "pip 업그레이드 실패 (계속 진행합니다)"
    PipUpgraded:
    
    ; requirements.txt 설치
    DetailPrint "Python 패키지 설치 중..."
    DetailPrint "이 작업은 몇 분 정도 걸릴 수 있습니다..."
    
    ; 임시 배치 파일 생성
    FileOpen $0 "$TEMP\install_packages.bat" w
    FileWrite $0 "@echo off$\r$\n"
    FileWrite $0 "cd /d \"$INSTDIR\"$\r$\n"
    FileWrite $0 "python -m pip install -r requirements.txt --disable-pip-version-check$\r$\n"
    FileWrite $0 "if %ERRORLEVEL% NEQ 0 ($\r$\n"
    FileWrite $0 "    echo 패키지 설치 실패$\r$\n"
    FileWrite $0 "    pause$\r$\n"
    FileWrite $0 "    exit /b %ERRORLEVEL%$\r$\n"
    FileWrite $0 ")$\r$\n"
    FileWrite $0 "echo 패키지 설치 완료$\r$\n"
    FileClose $0
    
    ; 패키지 설치 실행
    ExecWait '"$TEMP\install_packages.bat"' $0
    IfErrors 0 PackagesInstalled
    DetailPrint "패키지 설치 중 오류가 발생했습니다."
    MessageBox MB_YESNO|MB_ICONQUESTION "패키지 설치에 실패했습니다.$\n$\n수동으로 설치하시겠습니까?$\n(pip install -r requirements.txt)" IDYES ManualInstall IDNO SkipPackages
    ManualInstall:
        ExecShell "open" "$INSTDIR"
        MessageBox MB_OK "명령 프롬프트에서 다음 명령어를 실행하세요:$\n$\npip install -r requirements.txt"
    SkipPackages:
    Goto PythonCheckDone
    
PackagesInstalled:
    DetailPrint "모든 패키지 설치 완료!"
    
    ; 필수 패키지 테스트
    DetailPrint "필수 패키지 테스트 중..."
    FileOpen $0 "$TEMP\test_packages.py" w
    FileWrite $0 "import sys$\r$\n"
    FileWrite $0 "errors = []$\r$\n"
    FileWrite $0 "try:$\r$\n"
    FileWrite $0 "    import tcod$\r$\n"
    FileWrite $0 "    print('✓ tcod')$\r$\n"
    FileWrite $0 "except ImportError as e:$\r$\n"
    FileWrite $0 "    errors.append('tcod')$\r$\n"
    FileWrite $0 "    print('✗ tcod:', e)$\r$\n"
    FileWrite $0 "try:$\r$\n"
    FileWrite $0 "    import yaml$\r$\n"
    FileWrite $0 "    print('✓ yaml')$\r$\n"
    FileWrite $0 "except ImportError as e:$\r$\n"
    FileWrite $0 "    errors.append('yaml')$\r$\n"
    FileWrite $0 "    print('✗ yaml:', e)$\r$\n"
    FileWrite $0 "try:$\r$\n"
    FileWrite $0 "    import numpy$\r$\n"
    FileWrite $0 "    print('✓ numpy')$\r$\n"
    FileWrite $0 "except ImportError as e:$\r$\n"
    FileWrite $0 "    errors.append('numpy')$\r$\n"
    FileWrite $0 "    print('✗ numpy:', e)$\r$\n"
    FileWrite $0 "if errors:$\r$\n"
    FileWrite $0 "    sys.exit(1)$\r$\n"
    FileWrite $0 "else:$\r$\n"
    FileWrite $0 "    sys.exit(0)$\r$\n"
    FileClose $0
    
    ExecWait 'python "$TEMP\test_packages.py"' $0
    IfErrors 0 TestPassed
    DetailPrint "일부 패키지가 누락되었습니다."
    Goto PythonCheckDone
    
TestPassed:
    DetailPrint "모든 필수 패키지가 정상적으로 설치되었습니다!"
    
PythonVersionError:
PythonCheckDone:
SectionEnd

Section "Git 저장소 클론 (선택)" SEC04
    SectionIn 1
    
    DetailPrint "Git 설치 확인 중..."
    
    ; Git 경로 찾기
    ClearErrors
    ReadEnvStr $GitPath "GIT"
    IfErrors 0 GitFound
    
    ; PATH에서 Git 찾기
    ClearErrors
    ExecWait 'git --version' $0
    IfErrors 0 GitFound
    
    ; 일반적인 Git 설치 경로 확인
    IfFileExists "$PROGRAMFILES\Git\cmd\git.exe" 0 GitNotFound
    StrCpy $GitPath "$PROGRAMFILES\Git\cmd\git.exe"
    Goto GitFound
    
GitNotFound:
    DetailPrint "Git이 설치되어 있지 않습니다."
    MessageBox MB_YESNO|MB_ICONQUESTION "Git은 소스 코드 업데이트에 유용합니다 (선택 사항).$\n$\nGit 다운로드 페이지를 여시겠습니까?" IDYES OpenGitDownload IDNO SkipGit
    OpenGitDownload:
        ExecShell "open" "https://git-scm.com/download/win"
    SkipGit:
    Goto GitCheckDone
    
GitFound:
    DetailPrint "Git을 찾았습니다: $GitPath"
    
    ; 저장소 클론 여부 확인
    MessageBox MB_YESNO|MB_ICONQUESTION "GitHub에서 최신 소스 코드를 클론하시겠습니까?$\n$\n(이미 설치된 경우 건너뛸 수 있습니다)" IDYES CloneRepository IDNO SkipClone
    
CloneRepository:
    DetailPrint "저장소 클론 중..."
    ExecWait 'git clone https://github.com/APTOL-7177/Dawn-of-Stellar.git "$INSTDIR\source"' $0
    IfErrors 0 CloneSuccess
    DetailPrint "저장소 클론 실패"
    MessageBox MB_OK "저장소 클론에 실패했습니다.$\n$\n수동으로 클론하려면:$\ngit clone https://github.com/APTOL-7177/Dawn-of-Stellar.git"
    Goto GitCheckDone
    
CloneSuccess:
    DetailPrint "저장소 클론 완료!"
    
SkipClone:
GitCheckDone:
SectionEnd

;--------------------------------
; 설명

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC01} "게임 실행에 필요한 모든 파일을 설치합니다. (런처 포함)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC02} "시작 메뉴와 바탕화면에 런처 바로가기를 생성합니다."
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC03} "Python 패키지를 자동으로 설치합니다. (Python 3.10 이상 필요)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC04} "GitHub에서 최신 소스 코드를 클론합니다. (선택 사항)"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

;--------------------------------
; 제거 프로그램

Section "Uninstall"
    ; 제거 프로그램 파일 삭제
    Delete "$INSTDIR\uninstall.exe"
    
    ; 게임 파일 삭제
    RMDir /r "$INSTDIR\src"
    RMDir /r "$INSTDIR\data"
    RMDir /r "$INSTDIR\config"
    RMDir /r "$INSTDIR\docs"
    RMDir /r "$INSTDIR\source"
    Delete "$INSTDIR\main.py"
    Delete "$INSTDIR\launcher.py"
    Delete "$INSTDIR\launcher.bat"
    Delete "$INSTDIR\config.yaml"
    Delete "$INSTDIR\requirements.txt"
    Delete "$INSTDIR\README.md"
    Delete "$INSTDIR\LICENSE"
    Delete "$INSTDIR\start_game.bat"
    Delete "$INSTDIR\start_game_direct.bat"
    Delete "$INSTDIR\start_game_dev.bat"
    Delete "$INSTDIR\*.ttc"
    Delete "$INSTDIR\*.ttf"
    
    ; 시작 메뉴 바로가기 삭제
    RMDir /r "$SMPROGRAMS\${PRODUCT_NAME}"
    
    ; 바탕화면 바로가기 삭제
    Delete "$DESKTOP\${PRODUCT_NAME}.lnk"
    
    ; 레지스트리 키 삭제
    DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
    DeleteRegKey HKCR "${PRODUCT_DIR_REGKEY}"
    
    ; 설치 디렉토리 삭제
    RMDir "$INSTDIR"
    
    ; 임시 파일 삭제
    Delete "$TEMP\install_packages.bat"
    Delete "$TEMP\test_packages.py"
    
    SetAutoClose true
SectionEnd

;--------------------------------
; 설치 프로그램 초기화

Function .onInit
    ; 관리자 권한 확인
    UserInfo::GetAccountType
    pop $0
    ${If} $0 != "admin"
        MessageBox MB_YESNO|MB_ICONQUESTION "이 설치 프로그램은 관리자 권한이 필요합니다.$\n$\n관리자 권한으로 실행하시겠습니까?" IDYES RequestAdmin IDNO CancelInstall
        RequestAdmin:
            ExecShell "runas" "$EXEPATH"
        CancelInstall:
            Abort
    ${EndIf}
    
    ; 설치 디렉토리 설정
    StrCpy $INSTDIR "$PROGRAMFILES\${PRODUCT_NAME}"
FunctionEnd

;--------------------------------
; 설치 완료 후

Function .onInstSuccess
    MessageBox MB_YESNO|MB_ICONQUESTION "설치가 완료되었습니다!$\n$\n지금 게임 런처를 실행하시겠습니까?" IDYES LaunchGame IDNO Done
    LaunchGame:
        ExecShell "open" "$INSTDIR\launcher.bat"
    Done:
FunctionEnd

