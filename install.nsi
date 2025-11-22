; Dawn of Stellar Installer
; NSIS Script
; Version: 1.0.0

;--------------------------------
; General Settings

!define PRODUCT_NAME "Dawn of Stellar"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "APTOL-7177"
!define PRODUCT_WEB_SITE "https://github.com/APTOL-7177/Dawn-of-Stellar"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\DawnOfStellar.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

;--------------------------------
; Compression Settings

SetCompressor /SOLID lzma
SetCompressorDictSize 32

;--------------------------------
; MUI 1.67 Compatible Settings

!include "MUI2.nsh"

;--------------------------------
; MUI Settings

!define MUI_ABORTWARNING
!define MUI_ICON "assets\logo.png"
!define MUI_UNICON "assets\logo.png"

; Installer Pages
!insertmacro MUI_PAGE_WELCOME
!ifdef LICENSE
!insertmacro MUI_PAGE_LICENSE "${LICENSE}"
!endif
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstaller Pages
!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

;--------------------------------
; Language Files

!insertmacro MUI_LANGUAGE "English"

;--------------------------------
; MUI Reserved Files

!insertmacro MUI_RESERVEFILE_LANGDLL

;--------------------------------
; Installer Information

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "DawnOfStellar_Setup.exe"
InstallDir "$PROGRAMFILES\${PRODUCT_NAME}"
InstallDirRegKey HKCU "${PRODUCT_DIR_REGKEY}" ""
RequestExecutionLevel admin
ShowInstDetails show
ShowUnInstDetails show

;--------------------------------
; Variables

Var PythonPath
Var GitPath

;--------------------------------
; Install Types

InstType "Full Installation (Recommended)"
InstType "Minimal Installation"

;--------------------------------
; Sections

Section "Game Files" SEC01
    SectionIn RO 1 2
    
    SetOutPath "$INSTDIR"
    
    ; Essential Files
    File "main.py"
    File "config.yaml"
    File "requirements.txt"
    File "README.md"
    IfFileExists "LICENSE" 0 NoLicense
    File "LICENSE"
    NoLicense:
    
    ; Source Code
    SetOutPath "$INSTDIR\src"
    File /r "src\*.*"
    
    ; Data Files
    SetOutPath "$INSTDIR\data"
    File /r "data\*.*"
    
    ; Config Files
    SetOutPath "$INSTDIR\config"
    File /r "config\*.*"
    
    ; Font Files
    SetOutPath "$INSTDIR"
    IfFileExists "D2Coding.ttc" 0 NoD2CodingTTC
    File "D2Coding.ttc"
    NoD2CodingTTC:
    IfFileExists "D2Coding.ttf" 0 NoD2CodingTTF
    File "D2Coding.ttf"
    NoD2CodingTTF:
    IfFileExists "dalmoori.ttf" 0 NoDalmoori
    File "dalmoori.ttf"
    NoDalmoori:
    IfFileExists "DOSMyungjo.ttf" 0 NoDOSMyungjo
    File "DOSMyungjo.ttf"
    NoDOSMyungjo:
    IfFileExists "GalmuriMono9.ttf" 0 NoGalmuriMono9
    File "GalmuriMono9.ttf"
    NoGalmuriMono9:
    
    ; Logo/Icon File
    IfFileExists "assets\logo.png" 0 NoLogo
    File "assets\logo.png"
    NoLogo:
    
    ; Documentation
    SetOutPath "$INSTDIR\docs"
    File /r "docs\*.*"
    
    ; Launcher Files
    SetOutPath "$INSTDIR"
    IfFileExists "launcher.py" 0 NoLauncher
    File "launcher.py"
    NoLauncher:
    IfFileExists "launcher.bat" 0 NoLauncherBat
    File "launcher.bat"
    NoLauncherBat:
    
    ; Update Scripts
    IfFileExists "update.ps1" 0 NoUpdatePS1
    File "update.ps1"
    NoUpdatePS1:
    IfFileExists "update.bat" 0 NoUpdateBat
    File "update.bat"
    NoUpdateBat:
    
    ; Start Scripts
    SetOutPath "$INSTDIR"
    FileOpen $0 "$INSTDIR\start_game.bat" w
    FileWrite $0 "@echo off$\r$\n"
    FileWrite $0 "chcp 65001 >nul$\r$\n"
    FileWrite $0 'cd /d "$INSTDIR"$\r$\n'
    FileWrite $0 "python launcher.py$\r$\n"
    FileWrite $0 "if errorlevel 1 ($\r$\n"
    FileWrite $0 "    echo.$\r$\n"
    FileWrite $0 "    echo Error occurred.$\r$\n"
    FileWrite $0 "    pause$\r$\n"
    FileWrite $0 ")$\r$\n"
    FileClose $0
    
    ; Direct Run Script
    FileOpen $0 "$INSTDIR\start_game_direct.bat" w
    FileWrite $0 "@echo off$\r$\n"
    FileWrite $0 "chcp 65001 >nul$\r$\n"
    FileWrite $0 'cd /d "$INSTDIR"$\r$\n'
    FileWrite $0 "python main.py$\r$\n"
    FileWrite $0 "pause$\r$\n"
    FileClose $0
    
    ; Dev Mode Script
    FileOpen $0 "$INSTDIR\start_game_dev.bat" w
    FileWrite $0 "@echo off$\r$\n"
    FileWrite $0 "chcp 65001 >nul$\r$\n"
    FileWrite $0 'cd /d "$INSTDIR"$\r$\n'
    FileWrite $0 "python main.py --dev$\r$\n"
    FileWrite $0 "pause$\r$\n"
    FileClose $0
    
    ; Registry Keys
    WriteRegStr HKCR "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\main.py"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\main.py"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_ROOT_KEY}\${PRODUCT_NAME}" "Path" "$INSTDIR"
    
    ; Create Uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    ; Uninstaller Registry Keys
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\logo.png"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
SectionEnd

Section "Shortcuts" SEC02
    SectionIn 1
    
    ; Start Menu Shortcuts
    CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\start_game.bat" "" "$INSTDIR\logo.png" 0
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME} (Launcher).lnk" "$INSTDIR\launcher.bat" "" "$INSTDIR\logo.png" 0
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME} (Direct Run).lnk" "$INSTDIR\start_game_direct.bat" "" "$INSTDIR\logo.png" 0
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME} (Dev Mode).lnk" "$INSTDIR\start_game_dev.bat" "" "$INSTDIR\logo.png" 0
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Update Game.lnk" "$INSTDIR\update.bat" "" "$INSTDIR\logo.png" 0
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\logo.png" 0
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Website.lnk" "${PRODUCT_WEB_SITE}" "" "$INSTDIR\logo.png" 0
    
    ; Desktop Shortcut
    CreateShortCut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\start_game.bat" "" "$INSTDIR\logo.png" 0
SectionEnd

Section "Python Environment Setup" SEC03
    SectionIn 1 2
    
    DetailPrint "Checking Python installation..."
    
    ; Find Python Path
    ClearErrors
    ReadEnvStr $PythonPath "PYTHON"
    IfErrors 0 PythonFound
    
    ; Find Python in PATH
    ClearErrors
    ExecWait 'python --version' $0
    IfErrors 0 PythonFound
    
    ; Check Common Python Installation Paths
    IfFileExists "$PROGRAMFILES\Python*\python.exe" 0 PythonNotFound
    FindFirst $0 $1 "$PROGRAMFILES\Python*"
    StrCpy $PythonPath "$PROGRAMFILES\$1\python.exe"
    FindClose $0
    Goto PythonFound
    
PythonNotFound:
    DetailPrint "Python is not installed."
    MessageBox MB_YESNO|MB_ICONQUESTION "Python 3.10 or higher is required.$\n$\nOpen Python download page?" IDYES OpenPythonDownload IDNO SkipPython
    OpenPythonDownload:
        ExecShell "open" "https://www.python.org/downloads/"
        MessageBox MB_OK "Please check 'Add Python to PATH' during installation!$\n$\nRun this installer again after installing Python."
    SkipPython:
    Goto PythonCheckDone
    
PythonFound:
    DetailPrint "Python found: $PythonPath"
    
    ; Check Python Version
    ClearErrors
    ExecWait 'python --version' $0
    IfErrors PythonVersionError 0
    
    ; Upgrade pip
    DetailPrint "Upgrading pip..."
    ExecWait 'python -m pip install --upgrade pip' $0
    IfErrors 0 PipUpgraded
    DetailPrint "pip upgrade failed (continuing)"
    PipUpgraded:
    
    ; Install requirements.txt
    DetailPrint "Installing Python packages..."
    DetailPrint "This may take several minutes..."
    
    ; Create Temporary Batch File
    FileOpen $0 "$TEMP\install_packages.bat" w
    FileWrite $0 "@echo off$\r$\n"
    FileWrite $0 'cd /d "$INSTDIR"$\r$\n'
    FileWrite $0 "python -m pip install -r requirements.txt --disable-pip-version-check$\r$\n"
    FileWrite $0 "if %ERRORLEVEL% NEQ 0 ($\r$\n"
    FileWrite $0 "    echo Package installation failed$\r$\n"
    FileWrite $0 "    pause$\r$\n"
    FileWrite $0 "    exit /b %ERRORLEVEL%$\r$\n"
    FileWrite $0 ")$\r$\n"
    FileWrite $0 "echo Package installation complete$\r$\n"
    FileClose $0
    
    ; Execute Package Installation
    ExecWait '"$TEMP\install_packages.bat"' $0
    IfErrors 0 PackagesInstalled
    DetailPrint "Error occurred during package installation."
    MessageBox MB_YESNO|MB_ICONQUESTION "Package installation failed.$\n$\nInstall manually?$\n(pip install -r requirements.txt)" IDYES ManualInstall IDNO SkipPackages
    ManualInstall:
        ExecShell "open" "$INSTDIR"
        MessageBox MB_OK "Run the following command in Command Prompt:$\n$\npip install -r requirements.txt"
    SkipPackages:
    Goto PythonCheckDone
    
PackagesInstalled:
    DetailPrint "All packages installed successfully!"
    
    ; Test Essential Packages
    DetailPrint "Testing essential packages..."
    FileOpen $0 "$TEMP\test_packages.py" w
    FileWrite $0 "import sys$\r$\n"
    FileWrite $0 "errors = []$\r$\n"
    FileWrite $0 "try:$\r$\n"
    FileWrite $0 "    import tcod$\r$\n"
    FileWrite $0 '    print("OK tcod")$\r$\n'
    FileWrite $0 "except ImportError as e:$\r$\n"
    FileWrite $0 '    errors.append("tcod")$\r$\n'
    FileWrite $0 '    print("FAIL tcod:", e)$\r$\n'
    FileWrite $0 "try:$\r$\n"
    FileWrite $0 "    import yaml$\r$\n"
    FileWrite $0 '    print("OK yaml")$\r$\n'
    FileWrite $0 "except ImportError as e:$\r$\n"
    FileWrite $0 '    errors.append("yaml")$\r$\n'
    FileWrite $0 '    print("FAIL yaml:", e)$\r$\n'
    FileWrite $0 "try:$\r$\n"
    FileWrite $0 "    import numpy$\r$\n"
    FileWrite $0 '    print("OK numpy")$\r$\n'
    FileWrite $0 "except ImportError as e:$\r$\n"
    FileWrite $0 '    errors.append("numpy")$\r$\n'
    FileWrite $0 '    print("FAIL numpy:", e)$\r$\n'
    FileWrite $0 "if errors:$\r$\n"
    FileWrite $0 "    sys.exit(1)$\r$\n"
    FileWrite $0 "else:$\r$\n"
    FileWrite $0 "    sys.exit(0)$\r$\n"
    FileClose $0
    
    ExecWait 'python "$TEMP\test_packages.py"' $0
    IfErrors 0 TestPassed
    DetailPrint "Some packages are missing."
    Goto PythonCheckDone
    
TestPassed:
    DetailPrint "All essential packages installed successfully!"
    
PythonVersionError:
PythonCheckDone:
SectionEnd

Section "Update Feature" SEC04
    SectionIn 1
    
    ; Copy Update Scripts
    SetOutPath "$INSTDIR"
    IfFileExists "update.ps1" 0 NoUpdatePS1
    File "update.ps1"
    NoUpdatePS1:
    IfFileExists "update.bat" 0 NoUpdateBat
    File "update.bat"
    NoUpdateBat:
    
    ; Create Update Shortcut
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Update Game.lnk" "$INSTDIR\update.bat" "" "$INSTDIR\update.ps1" 0
SectionEnd

Section "Git Repository Clone (Optional)" SEC05
    SectionIn 1
    
    DetailPrint "Checking Git installation..."
    
    ; Find Git Path
    ClearErrors
    ReadEnvStr $GitPath "GIT"
    IfErrors 0 GitFound
    
    ; Find Git in PATH
    ClearErrors
    ExecWait 'git --version' $0
    IfErrors 0 GitFound
    
    ; Check Common Git Installation Path
    IfFileExists "$PROGRAMFILES\Git\cmd\git.exe" 0 GitNotFound
    StrCpy $GitPath "$PROGRAMFILES\Git\cmd\git.exe"
    Goto GitFound
    
GitNotFound:
    DetailPrint "Git is not installed."
    MessageBox MB_YESNO|MB_ICONQUESTION "Git is useful for source code updates (optional).$\n$\nOpen Git download page?" IDYES OpenGitDownload IDNO SkipGit
    OpenGitDownload:
        ExecShell "open" "https://git-scm.com/download/win"
    SkipGit:
    Goto GitCheckDone
    
GitFound:
    DetailPrint "Git found: $GitPath"
    
    ; Ask to Clone Repository
    MessageBox MB_YESNO|MB_ICONQUESTION "Clone latest source code from GitHub?$\n$\n(You can skip if already installed)" IDYES CloneRepository IDNO SkipClone
    
CloneRepository:
    DetailPrint "Cloning repository..."
    ExecWait 'git clone https://github.com/APTOL-7177/Dawn-of-Stellar.git "$INSTDIR\source"' $0
    IfErrors 0 CloneSuccess
    DetailPrint "Repository clone failed"
    MessageBox MB_OK "Repository clone failed.$\n$\nTo clone manually:$\ngit clone https://github.com/APTOL-7177/Dawn-of-Stellar.git"
    Goto GitCheckDone
    
CloneSuccess:
    DetailPrint "Repository clone complete!"
    
SkipClone:
GitCheckDone:
SectionEnd

;--------------------------------
; Descriptions

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC01} "Install all files required to run the game. (Includes launcher)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC02} "Create launcher shortcuts in Start Menu and Desktop."
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC03} "Automatically install Python packages. (Python 3.10+ required)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC04} "Install game update scripts. (Git repository required)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC05} "Clone latest source code from GitHub. (Optional)"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

;--------------------------------
; Uninstaller

Section "Uninstall"
    ; Delete Uninstaller
    Delete "$INSTDIR\uninstall.exe"
    
    ; Delete Game Files
    RMDir /r "$INSTDIR\src"
    RMDir /r "$INSTDIR\data"
    RMDir /r "$INSTDIR\config"
    RMDir /r "$INSTDIR\docs"
    RMDir /r "$INSTDIR\source"
    Delete "$INSTDIR\main.py"
    Delete "$INSTDIR\launcher.py"
    Delete "$INSTDIR\launcher.bat"
    Delete "$INSTDIR\update.ps1"
    Delete "$INSTDIR\update.bat"
    Delete "$INSTDIR\config.yaml"
    Delete "$INSTDIR\requirements.txt"
    Delete "$INSTDIR\README.md"
    Delete "$INSTDIR\LICENSE"
    Delete "$INSTDIR\start_game.bat"
    Delete "$INSTDIR\start_game_direct.bat"
    Delete "$INSTDIR\start_game_dev.bat"
    Delete "$INSTDIR\logo.png"
    Delete "$INSTDIR\*.ttc"
    Delete "$INSTDIR\*.ttf"
    
    ; Delete Start Menu Shortcuts
    RMDir /r "$SMPROGRAMS\${PRODUCT_NAME}"
    
    ; Delete Desktop Shortcut
    Delete "$DESKTOP\${PRODUCT_NAME}.lnk"
    
    ; Delete Registry Keys
    DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
    DeleteRegKey HKCR "${PRODUCT_DIR_REGKEY}"
    
    ; Delete Install Directory
    RMDir "$INSTDIR"
    
    ; Delete Temporary Files
    Delete "$TEMP\install_packages.bat"
    Delete "$TEMP\test_packages.py"
    
    SetAutoClose true
SectionEnd

;--------------------------------
; Installer Initialization

Function .onInit
    ; Set Install Directory
    StrCpy $INSTDIR "$PROGRAMFILES\${PRODUCT_NAME}"
FunctionEnd

;--------------------------------
; After Installation

Function .onInstSuccess
    MessageBox MB_YESNO|MB_ICONQUESTION "Installation complete!$\n$\nRun game launcher now?" IDYES LaunchGame IDNO Done
    LaunchGame:
        ExecShell "open" "$INSTDIR\launcher.bat"
    Done:
FunctionEnd
