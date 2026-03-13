@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo ===================================================
echo      Dawn of Stellar - RL Bot Auto Update Pipeline
echo      Auto-Tuned: GPU/CPU/RAM auto detection
echo ===================================================
echo.

echo [0/6] GPU check...
python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only')"
echo.

echo [1/6] Auto-tuning parameters...
python training/auto_tune.py --verbose
echo.

REM auto_tune result to env vars
for /f "tokens=1,* delims==" %%a in ('python training/auto_tune.py --shell') do set "%%a=%%b"

echo.
echo  n_envs=!N_ENVS!, batch_size=!BATCH_SIZE!, n_steps=!N_STEPS!, lr=!LR!
echo.
echo Starting in 3 seconds... Press Ctrl+C to cancel.
timeout /t 3 >nul

echo.
echo [2/6] Collecting play logs...
python training/collect_play_logs.py --episodes 500 --policy heuristic
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Log collection failed!
    pause
    exit /b 1
)

echo.
echo [3/6] Behavioral Cloning pre-training...
python training/train.py --phase bc
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] BC training failed!
    pause
    exit /b 1
)

echo.
echo [4/6] PPO Training - 5M steps, GPU accelerated
echo Check GPU: open new terminal, run 'nvidia-smi -l 2'
python training/train_ppo.py --timesteps 5000000 --n-envs !N_ENVS! --batch-size !BATCH_SIZE! --n-steps !N_STEPS! --lr !LR! --n-epochs 10
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PPO training failed!
    pause
    exit /b 1
)

echo.
echo [5/6] Evaluating model...
python training/train.py --phase eval --model-path data/models/ppo_final.zip
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Evaluation failed!
    pause
    exit /b 1
)

echo.
echo [6/6] Exporting game model...
python training/train.py --phase export --model-path data/models/ppo_final.zip
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Export failed!
    pause
    exit /b 1
)

echo.
echo ===================================================
echo  SUCCESS! data/models/combat_agent.pt updated.
echo  GPU: !GPU_NAME! / Envs: !N_ENVS!
echo ===================================================
pause
