@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ===================================================
echo   Dawn of Stellar - Export and Download Model
echo ===================================================

if "%~1"=="" (
    echo [Usage] download_model.bat [SSH_PORT] [IP_ADDRESS]
    echo Example: download_model.bat 12345 192.168.1.1
    pause
    exit /b 1
)

set VAST_PORT=%1
set VAST_IP=%2
set VAST_USER=root
set PROJECT=/root/Dawn-of-Stellar
set SSH_OPT=-o StrictHostKeyChecking^=no

echo.
echo [0/4] Uploading fixed export scripts to server...
scp -P %VAST_PORT% %SSH_OPT% src/rl/model_export.py %VAST_USER%@%VAST_IP%:%PROJECT%/src/rl/model_export.py
scp -P %VAST_PORT% %SSH_OPT% src/rl/network.py %VAST_USER%@%VAST_IP%:%PROJECT%/src/rl/network.py
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Upload failed, using server's existing scripts...
)

echo.
echo [1/4] Checking available models on server...
ssh -p %VAST_PORT% %SSH_OPT% %VAST_USER%@%VAST_IP% "ls -lhS %PROJECT%/data/models/ppo_final.zip %PROJECT%/data/models/checkpoints/*.zip 2>/dev/null | head -20"

echo.
echo [2/4] Finding latest checkpoint...
ssh -p %VAST_PORT% %SSH_OPT% %VAST_USER%@%VAST_IP% "if [ -f %PROJECT%/data/models/ppo_final.zip ]; then echo %PROJECT%/data/models/ppo_final.zip; else ls -t %PROJECT%/data/models/checkpoints/*.zip 2>/dev/null | head -1; fi" > %TEMP%\dos_model_path.txt

set /p MODEL_PATH=<%TEMP%\dos_model_path.txt
del %TEMP%\dos_model_path.txt >nul 2>&1

if "!MODEL_PATH!"=="" (
    echo [ERROR] No model found on server!
    pause
    exit /b 1
)

echo    -^> Model to use: !MODEL_PATH!

echo.
echo [3/4] Exporting to TorchScript... (1-2 min)
ssh -p %VAST_PORT% %SSH_OPT% %VAST_USER%@%VAST_IP% "cd %PROJECT% && python3 training/train.py --phase export --model-path !MODEL_PATH!"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Export failed! Downloading raw checkpoint instead...
    echo.
    scp -P %VAST_PORT% %SSH_OPT% %VAST_USER%@%VAST_IP%:!MODEL_PATH! data/models/latest_checkpoint.zip
    if %ERRORLEVEL% EQU 0 (
        echo [OK] Checkpoint downloaded: data/models/latest_checkpoint.zip
        echo Run locally:
        echo   python training/train.py --phase export --model-path data/models/latest_checkpoint.zip
    )
    pause
    exit /b 1
)

echo.
echo [4/4] Downloading combat_agent.pt...
if not exist "data\models" mkdir data\models
scp -P %VAST_PORT% %SSH_OPT% %VAST_USER%@%VAST_IP%:%PROJECT%/data/models/combat_agent.pt data/models/combat_agent.pt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Download failed!
    pause
    exit /b 1
)

echo.
echo ===================================================
echo  SUCCESS! Model downloaded.
echo  Path: data/models/combat_agent.pt
echo  Source: !MODEL_PATH!
echo ===================================================
pause
