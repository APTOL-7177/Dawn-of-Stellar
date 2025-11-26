; Dawn of Stellar Installer
; NSIS Script
; Version: 1.0.0

;--------------------------------
; Logo/Icon Settings

!if /FileExists "assets\logo.ico"
!define LOGO_ICO "assets\logo.ico"
!else
!define LOGO_ICO "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!endif

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
; Unicode support
Unicode true

;--------------------------------
; MUI 1.67 Compatible Settings

!include "MUI2.nsh"

;--------------------------------
; MUI Settings

!define MUI_ABORTWARNING
!define MUI_ICON "${LOGO_ICO}"
!define MUI_UNICON "${LOGO_ICO}"

; Installer Pages
!insertmacro MUI_PAGE_WELCOME
!ifdef LICENSE
!insertmacro MUI_PAGE_LICENSE "${LICENSE}"
!endif
!define MUI_PAGE_CUSTOMFUNCTION_PRE DirectoryPre
!define MUI_PAGE_CUSTOMFUNCTION_LEAVE DirectoryLeave
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
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
Var IsUpdateMode
Var ExistingInstallDir

;--------------------------------
; Install Types

InstType "Full Installation (Recommended)"
InstType "Minimal Installation"

;--------------------------------
; Sections

Section "Git Repository Clone/Update" SEC01
    SectionIn RO 1 2
    
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
    DetailPrint "Git is not installed. Attempting automatic installation..."
    MessageBox MB_YESNO|MB_ICONQUESTION "Git is not installed.$\n$\nWould you like to automatically download and install Git?$\n$\n(This will download ~50MB and may take several minutes)" IDYES AutoInstallGit IDNO ManualInstallGit

    AutoInstallGit:
        DetailPrint "Downloading Git installer..."
        ; Create temporary directory for download
        GetTempFileName $0
        Delete $0
        CreateDirectory "$0"
        StrCpy $1 "$0\Git-Installer.exe"

        ; Download Git installer using bitsadmin (works on all Windows versions)
        DetailPrint "Starting download with bitsadmin..."
        ExecWait 'bitsadmin /transfer "GitDownload" "https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe" "$1"' $2
        IntCmp $2 0 DownloadSuccess DownloadFailed

    DownloadFailed:
        DetailPrint "Failed to download Git installer with bitsadmin, trying wget..."
        ; Try wget if available (might be installed via Chocolatey or other package managers)
        ExecWait 'wget --no-check-certificate -O "$1" "https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe"' $2
        IntCmp $2 0 DownloadSuccess WgetFailed

    WgetFailed:
        DetailPrint "Failed to download Git installer with wget, trying curl..."
        ; Try curl (built-in on Windows 10 1803+)
        ExecWait 'curl -L -o "$1" "https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe"' $2
        IntCmp $2 0 DownloadSuccess CurlFailed

    CurlFailed:
        DetailPrint "Failed to download Git installer with curl, trying PowerShell..."
        ; Try PowerShell as final fallback (Windows 7+ with PowerShell)
        ; Use a simple PowerShell one-liner with proper escaping
        ExecWait 'powershell -Command "try { Invoke-WebRequest -Uri \"https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe\" -OutFile \"$1\" } catch { exit 1 }"' $2
        IntCmp $2 0 DownloadSuccess PSDownloadFailed

    PSDownloadFailed:
        DetailPrint "Failed to download Git installer"
        RMDir /r "$0"
        MessageBox MB_OK|MB_ICONSTOP "Failed to download Git installer.$\n$\nPlease download and install Git manually from:$\nhttps://git-scm.com/download/win"
        Abort "Git download failed"

    DownloadSuccess:
        DetailPrint "Git installer downloaded successfully"

        ; Install Git silently
        DetailPrint "Installing Git..."
        ExecWait '"$1" /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /COMPONENTS="icons,ext\reg\shellhere,assoc,assoc_sh" /DIR="$PROGRAMFILES\Git"' $2

        ; Clean up installer
        Delete "$1"
        RMDir /r "$0"

        ; Check if installation was successful
        IfFileExists "$PROGRAMFILES\Git\cmd\git.exe" GitInstallSuccess GitInstallFailed

    GitInstallFailed:
        DetailPrint "Git installation failed"
        MessageBox MB_OK|MB_ICONSTOP "Git installation failed.$\n$\nPlease install Git manually from:$\nhttps://git-scm.com/download/win"
        Abort "Git installation failed"

    GitInstallSuccess:
        DetailPrint "Git installed successfully"
        StrCpy $GitPath "$PROGRAMFILES\Git\cmd\git.exe"
        Goto GitFound

    ManualInstallGit:
        ExecShell "open" "https://git-scm.com/download/win"
        MessageBox MB_OK "Please install Git and run this installer again."
        Abort "Git is required for installation"
    
GitFound:
    DetailPrint "Git found: $GitPath"
    
    ; Check if update mode
    IntCmp $IsUpdateMode 1 UpdateMode NewInstall
    
UpdateMode:
    DetailPrint "Update mode: Updating existing installation..."
    
    ; Check if .git directory exists
    IfFileExists "$INSTDIR\.git" 0 NotGitRepo
    
    ; Stash local changes if any
    DetailPrint "Checking for local changes..."
    ExecWait 'git -C "$INSTDIR" status --porcelain' $0
    IntCmp $0 0 NoLocalChanges
    DetailPrint "Local changes detected. Stashing..."
    ExecWait 'git -C "$INSTDIR" stash push -m "Auto-stash before update $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")"' $0
    
NoLocalChanges:
    ; Fetch latest changes
    DetailPrint "Fetching latest changes from GitHub..."
    ExecWait 'git -C "$INSTDIR" fetch origin' $0
    IfErrors 0 FetchSuccess
    DetailPrint "Failed to fetch updates"
    MessageBox MB_OK|MB_ICONSTOP "Failed to fetch updates.$\n$\nPlease check your internet connection."
    Abort "Update fetch failed"
    
FetchSuccess:
    ; Pull latest changes (git will use current branch)
    DetailPrint "Pulling latest changes..."
    ExecWait 'git -C "$INSTDIR" pull origin' $0
    IfErrors 0 PullSuccess
    DetailPrint "Failed to pull updates"
    MessageBox MB_OK|MB_ICONSTOP "Failed to pull updates.$\n$\nError code: $0"
    Abort "Update pull failed"
    
PullSuccess:
    DetailPrint "Update complete!"
    
    ; Verify essential files
    IfFileExists "$INSTDIR\main.py" 0 UpdateFailed
    IfFileExists "$INSTDIR\requirements.txt" 0 UpdateFailed
    IfFileExists "$INSTDIR\src" 0 UpdateFailed
    Goto UpdateVerified
    
UpdateFailed:
    DetailPrint "Updated repository is missing essential files"
    MessageBox MB_OK|MB_ICONSTOP "Updated repository is incomplete.$\n$\nPlease try again or contact support."
    Abort "Update incomplete"
    
UpdateVerified:
    DetailPrint "Update verified successfully"
    Goto GitOperationDone
    
NotGitRepo:
    DetailPrint "Existing installation is not a Git repository. Reinstalling..."
    Goto NewInstall
    
NewInstall:
    DetailPrint "Install mode: Cloning repository from GitHub..."
    DetailPrint "This may take a few minutes..."
    
    ; Create temporary directory for cloning
    GetTempFileName $0
    Delete $0
    CreateDirectory "$0\clone"
    StrCpy $1 "$0\clone"
    
    ; Clone repository to temporary directory
    DetailPrint "Cloning repository from GitHub..."
    ExecWait 'git clone https://github.com/APTOL-7177/Dawn-of-Stellar.git "$1\Dawn-of-Stellar"' $2

    ; Check exit code properly
    IntCmp $2 0 CloneSuccess 0 CloneFailedWithCode

    CloneFailedWithCode:
        DetailPrint "Repository clone failed with exit code: $2"

        ; Try alternative clone method (shallow clone for faster download)
        DetailPrint "Trying shallow clone as fallback..."
        ExecWait 'git clone --depth 1 https://github.com/APTOL-7177/Dawn-of-Stellar.git "$1\Dawn-of-Stellar"' $3
        IntCmp $3 0 CloneSuccess 0 CloneFailedShallow

    CloneFailedShallow:
        DetailPrint "Shallow clone also failed"

        ; Try with different URL format (HTTPS vs SSH)
        DetailPrint "Trying with different URL format..."
        ExecWait 'git clone https://github.com/APTOL-7177/Dawn-of-Stellar "$1\Dawn-of-Stellar"' $4
        IntCmp $4 0 CloneSuccess 0 CloneFailedAlternative

    CloneFailedAlternative:
        DetailPrint "All clone attempts failed"
        RMDir /r "$0"

        ; Provide detailed error message
        MessageBox MB_OKCANCEL|MB_ICONSTOP "Failed to clone repository from GitHub.$\n$\nPossible causes:$\n- No internet connection$\n- Firewall blocking Git$\n- Git proxy settings required$\n- Repository temporarily unavailable$\n$\nExit codes: Normal=$2, Shallow=$3, Alternative=$4$\n$\nWould you like to try manual installation?" IDOK ManualClone IDCANCEL AbortInstall

    ManualClone:
        ExecShell "open" "https://github.com/APTOL-7177/Dawn-of-Stellar/archive/main.zip"
        MessageBox MB_OK "Please download the ZIP file, extract it, and run the installer again from the extracted folder."
        Abort "Manual download required"

    AbortInstall:
        Abort "Repository clone failed"
    
CloneSuccess:
    DetailPrint "Repository clone complete!"
    
    ; Verify essential files in cloned directory
    IfFileExists "$1\Dawn-of-Stellar\main.py" 0 CloneFailed
    IfFileExists "$1\Dawn-of-Stellar\requirements.txt" 0 CloneFailed
    IfFileExists "$1\Dawn-of-Stellar\src" 0 CloneFailed
    Goto CloneVerified
    
CloneFailed:
    DetailPrint "Cloned repository is missing essential files"
    RMDir /r "$0"
    MessageBox MB_OK|MB_ICONSTOP "Cloned repository is incomplete.$\n$\nPlease try again or contact support."
    Abort "Repository clone incomplete"
    
CloneVerified:
    DetailPrint "Repository verified successfully"
    
    ; Remove existing installation directory if exists (only for new install)
    IfFileExists "$INSTDIR" 0 NoExistingDir
    DetailPrint "Removing existing installation directory..."
    RMDir /r "$INSTDIR"
    NoExistingDir:
    
    ; Move cloned files to installation directory
    DetailPrint "Moving files to installation directory..."
    CreateDirectory "$INSTDIR"
    CopyFiles /SILENT "$1\Dawn-of-Stellar\*.*" "$INSTDIR\"
    
    ; Clean up temporary directory
    RMDir /r "$0"
    
    DetailPrint "Files moved to installation directory"
    
GitOperationDone:
    
    ; Start Scripts (created after Git clone)
    SetOutPath "$INSTDIR"

    ; Determine Python command to use
    StrCpy $1 "python"  ; Default to python command
    StrCmp $PythonPath "" UsePythonCommand 0
    StrCpy $1 "$PythonPath"  ; Use full path if found
    UsePythonCommand:

    FileOpen $0 "$INSTDIR\start_game.bat" w
    FileWrite $0 "@echo off$\r$\n"
    FileWrite $0 "chcp 65001 >nul$\r$\n"
    FileWrite $0 'cd /d "$INSTDIR"$\r$\n'
    FileWrite $0 '"$1" launcher.py$\r$\n'
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
    FileWrite $0 '"$1" main.py$\r$\n'
    FileWrite $0 "pause$\r$\n"
    FileClose $0

    ; Dev Mode Script
    FileOpen $0 "$INSTDIR\start_game_dev.bat" w
    FileWrite $0 "@echo off$\r$\n"
    FileWrite $0 "chcp 65001 >nul$\r$\n"
    FileWrite $0 'cd /d "$INSTDIR"$\r$\n'
    FileWrite $0 '"$1" main.py --dev$\r$\n'
    FileWrite $0 "pause$\r$\n"
    FileClose $0
    
    ; Create Uninstaller (before moving to cloned directory)
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    ; Registry Keys
    WriteRegStr HKCR "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\main.py"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\main.py"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_ROOT_KEY}\${PRODUCT_NAME}" "Path" "$INSTDIR"
    
    ; Uninstaller Registry Keys
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninstall.exe"
    ; DisplayIcon (prefer ICO)
    IfFileExists "$INSTDIR\logo.ico" 0 UsePNGIcon
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\logo.ico"
    Goto IconDone
    UsePNGIcon:
    IfFileExists "$INSTDIR\logo.png" 0 NoIconReg
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\logo.png"
    NoIconReg:
    IconDone:
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
SectionEnd

Section "Shortcuts" SEC02
    SectionIn 1 2  ; Include in both Full and Minimal installation

    DetailPrint "Creating shortcuts..."

    ; Start Menu Shortcuts
    CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"

    ; Icon path (prefer ICO, fallback to PNG, then no icon)
    StrCpy $0 "$INSTDIR\logo.ico"
    IfFileExists "$INSTDIR\logo.ico" SetIconPath 0
    StrCpy $0 "$INSTDIR\logo.png"
    IfFileExists "$INSTDIR\logo.png" SetIconPath 0
    StrCpy $0 ""  ; No icon

    SetIconPath:
    ; Create shortcuts regardless of icon existence
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME}.lnk" "$INSTDIR\start_game.bat" "" $0 0
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME} (Launcher).lnk" "$INSTDIR\launcher.bat" "" $0 0
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME} (Direct Run).lnk" "$INSTDIR\start_game_direct.bat" "" $0 0
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${PRODUCT_NAME} (Dev Mode).lnk" "$INSTDIR\start_game_dev.bat" "" $0 0

    ; Only create update shortcut if update.bat exists
    IfFileExists "$INSTDIR\update.bat" 0 SkipUpdateShortcut
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Update Game.lnk" "$INSTDIR\update.bat" "" $0 0
    SkipUpdateShortcut:

    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall.lnk" "$INSTDIR\uninstall.exe" "" $0 0
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Website.lnk" "${PRODUCT_WEB_SITE}" "" $0 0

    ; Desktop Shortcut (always create)
    CreateShortCut "$DESKTOP\${PRODUCT_NAME}.lnk" "$INSTDIR\start_game.bat" "" $0 0

    DetailPrint "Shortcuts created successfully"
SectionEnd

Section "Python Environment Setup" SEC03
    SectionIn 1 2
    
    ; In update mode, check if requirements.txt changed
    IntCmp $IsUpdateMode 1 CheckRequirements UpdateInstall
    
CheckRequirements:
    DetailPrint "Update mode: Checking if Python packages need update..."
    ; Check if requirements.txt exists and was modified
    IfFileExists "$INSTDIR\requirements.txt" 0 UpdateInstall
    ; For now, always reinstall in update mode (can be optimized later)
    DetailPrint "Reinstalling Python packages after update..."
    Goto UpdateInstall
    
UpdateInstall:
    DetailPrint "Checking Python installation..."
    
    ; Find Python Path
    ClearErrors
    ReadEnvStr $PythonPath "PYTHON"
    IfErrors 0 PythonFound

    ; Find Python in PATH
    ClearErrors
    ExecWait 'python --version' $0
    IfErrors 0 PythonFound

    ; Check Common Python Installation Paths (try multiple versions)
    ; Python 3.11
    IfFileExists "$PROGRAMFILES\Python311\python.exe" 0 CheckPython310
    StrCpy $PythonPath "$PROGRAMFILES\Python311\python.exe"
    Goto PythonFound

    CheckPython310:
    IfFileExists "$PROGRAMFILES\Python310\python.exe" 0 CheckPython312
    StrCpy $PythonPath "$PROGRAMFILES\Python310\python.exe"
    Goto PythonFound

    CheckPython312:
    IfFileExists "$PROGRAMFILES\Python312\python.exe" 0 CheckPython39
    StrCpy $PythonPath "$PROGRAMFILES\Python312\python.exe"
    Goto PythonFound

    CheckPython39:
    IfFileExists "$PROGRAMFILES\Python39\python.exe" 0 CheckPython38
    StrCpy $PythonPath "$PROGRAMFILES\Python39\python.exe"
    Goto PythonFound

    CheckPython38:
    IfFileExists "$PROGRAMFILES\Python38\python.exe" 0 CheckPython37
    StrCpy $PythonPath "$PROGRAMFILES\Python38\python.exe"
    Goto PythonFound

    CheckPython37:
    IfFileExists "$PROGRAMFILES\Python37\python.exe" 0 CheckPython36
    StrCpy $PythonPath "$PROGRAMFILES\Python37\python.exe"
    Goto PythonFound

    CheckPython36:
    IfFileExists "$PROGRAMFILES\Python36\python.exe" 0 CheckProgramFilesx86
    StrCpy $PythonPath "$PROGRAMFILES\Python36\python.exe"
    Goto PythonFound

    CheckProgramFilesx86:
    ; Check Program Files (x86) for 32-bit installations
    IfFileExists "$PROGRAMFILES32\Python311\python.exe" 0 CheckPFx86310
    StrCpy $PythonPath "$PROGRAMFILES32\Python311\python.exe"
    Goto PythonFound

    CheckPFx86310:
    IfFileExists "$PROGRAMFILES32\Python310\python.exe" 0 PythonNotFound
    StrCpy $PythonPath "$PROGRAMFILES32\Python310\python.exe"
    Goto PythonFound
    
PythonNotFound:
    DetailPrint "Python is not installed. Attempting automatic installation..."
    MessageBox MB_YESNO|MB_ICONQUESTION "Python 3.10 or higher is required.$\n$\nWould you like to automatically download and install Python?$\n$\n(This will download ~25MB and may take several minutes)" IDYES AutoInstallPython IDNO ManualPythonInstall

    AutoInstallPython:
        DetailPrint "Downloading Python installer..."
        ; Create temporary directory for download
        GetTempFileName $0
        Delete $0
        CreateDirectory "$0"
        StrCpy $1 "$0\Python-Installer.exe"

        ; Download Python installer (3.11.x for Windows)
        DetailPrint "Starting Python download..."
        ExecWait 'bitsadmin /transfer "PythonDownload" "https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe" "$1"' $2
        IntCmp $2 0 DownloadPythonSuccess DownloadPythonFailed

    DownloadPythonFailed:
        DetailPrint "Failed to download Python installer with bitsadmin, trying PowerShell..."
        ExecWait 'powershell -Command "& {try {Invoke-WebRequest -Uri \"https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe\" -OutFile \"$1\"} catch {exit 1}}"' $2
        IntCmp $2 0 DownloadPythonSuccess DownloadPythonPowerShellFailed

    DownloadPythonPowerShellFailed:
        DetailPrint "Failed to download Python installer"
        RMDir /r "$0"
        MessageBox MB_OK|MB_ICONSTOP "Failed to download Python installer.$\n$\nPlease download and install Python manually from:$\nhttps://www.python.org/downloads/"
        Abort "Python download failed"

    DownloadPythonSuccess:
        DetailPrint "Python installer downloaded successfully"

        ; Install Python silently
        DetailPrint "Installing Python..."
        ExecWait '"$1" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_pip=1 Include_doc=0 Include_launcher=1 InstallLauncherAllUsers=1' $2

        ; Clean up installer
        Delete "$1"
        RMDir /r "$0"

        ; Check if installation was successful
        IfFileExists "$PROGRAMFILES\Python311\python.exe" PythonInstallSuccess PythonInstallFailed

    PythonInstallFailed:
        DetailPrint "Python installation failed"
        MessageBox MB_OK|MB_ICONSTOP "Python installation failed.$\n$\nPlease install Python manually from:$\nhttps://www.python.org/downloads/"
        Abort "Python installation failed"

    PythonInstallSuccess:
        DetailPrint "Python installed successfully"
        StrCpy $PythonPath "$PROGRAMFILES\Python311\python.exe"
        Goto PythonFound

    ManualPythonInstall:
        ExecShell "open" "https://www.python.org/downloads/"
        MessageBox MB_OK "Please download and install Python 3.10 or higher.$\n$\nIMPORTANT: Check 'Add Python to PATH' during installation!$\n$\nRun this installer again after installing Python."
        Abort "Python installation required"
    
PythonFound:
    DetailPrint "Python found: $PythonPath"

    ; Check Python Version
    ClearErrors
    ExecWait '"$PythonPath" --version' $0
    IfErrors PythonVersionError 0

    ; Parse version number (basic check)
    ; Python version output format: "Python 3.X.Y"
    ExecWait '"$PythonPath" -c "import sys; print(sys.version_info.major * 10 + sys.version_info.minor)"' $1
    IntCmp $1 0 PythonVersionError 0  ; Check if version parsing failed
    IntCmp $1 310 VersionOK 0  ; Check if >= 3.10
    IntCmp $1 311 VersionOK 0
    IntCmp $1 312 VersionOK 0
    IntCmp $1 313 VersionOK 0
    Goto PythonVersionTooOld

VersionOK:
    DetailPrint "Python version is OK: $1"
    
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
    
PythonVersionTooOld:
    DetailPrint "Python version is too old"
    MessageBox MB_OK|MB_ICONSTOP "Python 3.10 or higher is required.$\n$\nCurrent version is too old.$\n$\nPlease update Python from:$\nhttps://www.python.org/downloads/"
    Abort "Python version too old"

PythonVersionError:
    DetailPrint "Could not determine Python version"
    MessageBox MB_OK|MB_ICONSTOP "Could not determine Python version.$\n$\nPlease ensure Python is properly installed."
    Goto PythonCheckDone

PythonCheckDone:
SectionEnd

Section "Update Feature" SEC04
    SectionIn 1
    
    ; Update scripts are already in cloned repository
    ; Create Update Shortcut (update.bat should exist in cloned repo)
    IfFileExists "$INSTDIR\update.bat" 0 NoUpdateBat
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Update Game.lnk" "$INSTDIR\update.bat" "" "$INSTDIR\logo.ico" 0
    NoUpdateBat:
SectionEnd

;--------------------------------
; Descriptions

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC01} "Download or update game files from GitHub repository. (Git required)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC02} "Create launcher shortcuts in Start Menu and Desktop."
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC03} "Automatically install Python packages. (Python 3.10+ required)"
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC04} "Create update shortcut. (Update scripts included in repository)"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

;--------------------------------
; Uninstaller

Section "Uninstall"
    ; Delete Uninstaller
    Delete "$INSTDIR\uninstall.exe"
    
    ; Delete all files (everything was cloned from Git)
    ; Delete generated scripts first
    Delete "$INSTDIR\start_game.bat"
    Delete "$INSTDIR\start_game_direct.bat"
    Delete "$INSTDIR\start_game_dev.bat"
    
    ; Delete entire directory (contains all cloned files)
    RMDir /r "$INSTDIR"
    
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
    ; Initialize update mode flag
    StrCpy $IsUpdateMode 0
    
    ; Set default install directory first
    StrCpy $INSTDIR "$PROGRAMFILES\${PRODUCT_NAME}"
    
    ; Check for existing installation in multiple ways
    ; Method 1: Check registry
    ClearErrors
    ReadRegStr $ExistingInstallDir ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Path"
    IfErrors 0 CheckRegistryPath
    
    ; Method 2: Check default installation directory
    IfFileExists "$PROGRAMFILES\${PRODUCT_NAME}\main.py" 0 CheckGitRepo
    StrCpy $ExistingInstallDir "$PROGRAMFILES\${PRODUCT_NAME}"
    Goto FoundInstallation
    
CheckRegistryPath:
    ; If registry path exists, verify it
    StrCmp $ExistingInstallDir "" CheckGitRepo
    IfFileExists "$ExistingInstallDir\main.py" FoundInstallation CheckGitRepo
    
CheckGitRepo:
    ; Method 3: Check if default directory is a git repo
    IfFileExists "$PROGRAMFILES\${PRODUCT_NAME}\.git" 0 NewInstall
    IfFileExists "$PROGRAMFILES\${PRODUCT_NAME}\main.py" 0 NewInstall
    StrCpy $ExistingInstallDir "$PROGRAMFILES\${PRODUCT_NAME}"
    Goto FoundInstallation
    
FoundInstallation:
    ; Existing installation found - ask for update
    MessageBox MB_YESNO|MB_ICONQUESTION "Existing installation found at:$\n$ExistingInstallDir$\n$\nWould you like to UPDATE the game?$\n$\nClick 'Yes' to UPDATE (recommended)$\nClick 'No' to install to a new location" IDYES UpdateMode IDNO NewInstall
    
UpdateMode:
    ; Set update mode
    StrCpy $IsUpdateMode 1
    StrCpy $INSTDIR $ExistingInstallDir
    Goto InitDone
    
NewInstall:
    ; Set Install Directory for new installation
    StrCpy $INSTDIR "$PROGRAMFILES\${PRODUCT_NAME}"
    
InitDone:
FunctionEnd

;--------------------------------
; Directory Page Functions

Function DirectoryPre
    ; If in update mode, skip directory page
    IntCmp $IsUpdateMode 1 SkipDirectory 0
    Return
    
SkipDirectory:
    ; Skip directory selection page in update mode
    Abort
FunctionEnd

Function DirectoryLeave
    ; If in update mode, don't allow changing directory
    IntCmp $IsUpdateMode 1 UpdateModeDir 0
    Return
    
UpdateModeDir:
    ; Force directory to existing installation
    StrCpy $INSTDIR $ExistingInstallDir
    Return
FunctionEnd

;--------------------------------
; After Installation

Function .onInstSuccess
    IntCmp $IsUpdateMode 1 UpdateSuccess InstallSuccess
    
UpdateSuccess:
    MessageBox MB_YESNO|MB_ICONQUESTION "Update complete!$\n$\nRun game launcher now?" IDYES LaunchGame IDNO Done
    Goto LaunchGame
    
InstallSuccess:
    MessageBox MB_YESNO|MB_ICONQUESTION "Installation complete!$\n$\nRun game launcher now?" IDYES LaunchGame IDNO Done
    
LaunchGame:
    ExecShell "open" "$INSTDIR\launcher.bat"
    Done:
FunctionEnd
