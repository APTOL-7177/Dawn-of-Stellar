@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ===================================================
echo      Dawn of Stellar - Vast.ai Cloud Training
echo      Auto-Tuned: GPU/CPU/RAM auto detection
echo ===================================================

if "%~1"=="" goto :USAGE
goto :START

:USAGE
echo [Usage] train_on_vast.bat [SSH_PORT] [IP_ADDRESS] [N_ENVS]
echo Example: train_on_vast.bat 12345 192.168.1.1
echo.
echo N_ENVS is optional. If omitted, auto-tuned on server.
pause
exit /b 1

:START
set VAST_PORT=%1
set VAST_IP=%2
set VAST_USER=root
set SSH_OPT=-o StrictHostKeyChecking=no

if "%~3"=="" (
    set "N_ENVS_ARG="
    echo [Info] N_ENVS: auto-tune
) else (
    set "N_ENVS_ARG=%3"
    echo [Info] N_ENVS: %3
)

echo.
echo [1/4] Compressing project...
tar -czf dos_source.tar.gz --exclude=".git" --exclude="venv" --exclude="__pycache__" --exclude=".pytest_cache" --exclude="dist" --exclude="build" --exclude="*.tar.gz" --exclude="build_linux" --exclude="dist_linux" .
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Compression failed!
    pause
    exit /b 1
)

echo.
echo [2/4] Uploading to Vast.ai server...
scp -P %VAST_PORT% %SSH_OPT% dos_source.tar.gz %VAST_USER%@%VAST_IP%:/root/
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Upload failed! Check SSH keys.
    pause
    exit /b 1
)

echo.
echo [3/4] Starting auto-tuned training pipeline on Cloud...
echo ===================================================
echo [WARNING] DO NOT close this window!
echo ===================================================
ssh -p %VAST_PORT% %SSH_OPT% %VAST_USER%@%VAST_IP% "mkdir -p /root/Dawn-of-Stellar && tar -xzf /root/dos_source.tar.gz -C /root/Dawn-of-Stellar && dos2unix /root/Dawn-of-Stellar/cloud_train.sh 2>/dev/null || true && chmod +x /root/Dawn-of-Stellar/cloud_train.sh && bash /root/Dawn-of-Stellar/cloud_train.sh !N_ENVS_ARG!"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Training failed or connection lost!
    pause
    exit /b 1
)

echo.
echo [4/4] Downloading trained model...
scp -P %VAST_PORT% %SSH_OPT% %VAST_USER%@%VAST_IP%:/root/Dawn-of-Stellar/data/models/combat_agent.pt data/models/combat_agent.pt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Download failed!
    pause
    exit /b 1
)

echo.
echo ===================================================
echo  SUCCESS! Model downloaded and applied to game.
echo  Path: data/models/combat_agent.pt
echo ===================================================
del dos_source.tar.gz
pause
