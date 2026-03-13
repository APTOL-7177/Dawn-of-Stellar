#!/bin/bash
# Dawn of Stellar - Auto-Tuned Cloud Training Script
# GPU/CPU/RAM을 자동 감지하여 최대 성능으로 학습합니다.

set -e
cd /root/Dawn-of-Stellar

# 학습 중 WARNING 이하 로그 억제 (ERROR 이상만 출력)
# RL 탐색 중 MP부족/BRV 0 등 WARNING이 대량 발생하므로 ERROR만 표시
export LOG_LEVEL=ERROR

# 헤드리스 서버: 사운드/디스플레이 비활성화 (ALSA 오류 방지)
export SDL_AUDIODRIVER=dummy
export SDL_VIDEODRIVER=dummy

# Python 경고 억제 (pygame pkg_resources 등)
export PYTHONWARNINGS=ignore

# SubprocVecEnv: 각 서브프로세스가 1스레드만 사용하도록 제한
# 382환경 × 64스레드 = 스레드 폭발 방지
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OMP_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

# SubprocVecEnv는 환경당 소켓 페어 2개가 필요하므로 FD 한도를 충분히 올림
ulimit -n 65536 2>/dev/null || ulimit -n 8192 2>/dev/null || true
echo "[Cloud] File descriptor limit: $(ulimit -n)"

echo "==================================================="
echo "[Cloud] GPU Diagnostics..."
echo "==================================================="
nvidia-smi 2>/dev/null && echo "[OK] nvidia-smi works" || echo "[WARN] nvidia-smi not found"
CUDA_VER=$(nvidia-smi 2>/dev/null | grep -oP 'CUDA Version: \K[0-9]+\.[0-9]+' || echo "none")
echo "[Cloud] CUDA Driver Version: $CUDA_VER"

echo ""
echo "==================================================="
echo "[Cloud] Installing Dependencies..."
echo "==================================================="
apt-get update -qq && apt-get install -y python3-pip -qq 2>/dev/null || true
pip3 install -r requirements.txt

# CUDA 버전에 맞는 PyTorch 설치 (5060 Ti 등 최신 GPU는 CUDA 12.8+ 필요)
if echo "$CUDA_VER" | grep -qE '^12\.[8-9]|^1[3-9]'; then
    echo "[Cloud] CUDA $CUDA_VER -> Installing PyTorch with cu128"
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
elif echo "$CUDA_VER" | grep -qE '^12\.[4-7]'; then
    echo "[Cloud] CUDA $CUDA_VER -> Installing PyTorch with cu124"
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
elif echo "$CUDA_VER" | grep -qE '^12\.'; then
    echo "[Cloud] CUDA $CUDA_VER -> Installing PyTorch with cu121"
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
elif echo "$CUDA_VER" | grep -qE '^11\.'; then
    echo "[Cloud] CUDA $CUDA_VER -> Installing PyTorch with cu118"
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
else
    echo "[Cloud] No CUDA detected -> CPU-only PyTorch"
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
fi
pip3 install stable-baselines3 sb3-contrib tensorboard gymnasium psutil

echo ""
echo "==================================================="
echo "[Cloud] Auto-Tuning: Detecting Hardware..."
echo "==================================================="
# auto_tune.py로 하드웨어 감지 및 최적 파라미터 결정
TUNE_OUTPUT=$(python3 training/auto_tune.py --shell 2>/dev/null) && eval "$TUNE_OUTPUT"

# auto_tune 실패 시 안전한 기본값
N_ENVS=${N_ENVS:-32}
BATCH_SIZE=${BATCH_SIZE:-256}
N_STEPS=${N_STEPS:-2048}
N_EPOCHS=${N_EPOCHS:-10}
LR=${LR:-3e-4}
GPU_NAME=${GPU_NAME:-unknown}
GPU_VRAM=${GPU_VRAM:-0}
CPU_CORES=${CPU_CORES:-8}
RAM_GB=${RAM_GB:-16}

echo "  GPU:        $GPU_NAME ($GPU_VRAM GB VRAM)"
echo "  CPU:        $CPU_CORES cores"
echo "  RAM:        $RAM_GB GB"
echo "  ---"
echo "  n_envs:     $N_ENVS"
echo "  batch_size: $BATCH_SIZE"
echo "  n_steps:    $N_STEPS"
echo "  n_epochs:   $N_EPOCHS"
echo "  lr:         $LR"

# 수동 오버라이드 지원: 인자로 N_ENVS를 넘기면 auto-tune 결과를 덮어씀
if [ -n "$1" ]; then
    N_ENVS=$1
    echo "  [Override] n_envs -> $N_ENVS"
fi

echo ""
echo "==================================================="
echo "[Cloud] Phase 1: Log Collection"
echo "==================================================="
LOG_FILES=$(ls data/play_logs/*.jsonl 2>/dev/null | wc -l)
if [ "$LOG_FILES" -gt 0 ]; then
    echo "-> Play logs already exist ($LOG_FILES files found). Skipping."
else
    echo "-> No play logs found. Collecting 500 episodes..."
    python3 training/collect_play_logs.py --episodes 500 --policy heuristic
fi

echo ""
echo "==================================================="
echo "[Cloud] Phase 2: Behavioral Cloning (BC)"
echo "==================================================="
if [ -f "data/models/bc_weights.pt" ]; then
    echo "-> bc_weights.pt already exists. Skipping."
else
    echo "-> Running BC Pre-training..."
    python3 training/train.py --phase bc
fi

echo ""
echo "==================================================="
echo "[Cloud] Phase 3: PPO Training (75M steps, GPU accelerated)"
echo "==================================================="
if [ -f "data/models/ppo_final.zip" ]; then
    echo "-> ppo_final.zip already exists. Skipping."
else
    echo "-> PPO Training: ${N_ENVS} envs, batch=${BATCH_SIZE}, n_steps=${N_STEPS}, lr=${LR}"
    python3 training/train_ppo.py \
        --timesteps 75000000 \
        --n-envs $N_ENVS \
        --batch-size $BATCH_SIZE \
        --n-steps $N_STEPS \
        --lr $LR \
        --n-epochs $N_EPOCHS
fi

echo ""
echo "==================================================="
echo "[Cloud] Phase 4: Evaluating Model"
echo "==================================================="
python3 training/train.py --phase eval --model-path data/models/ppo_final.zip

echo ""
echo "==================================================="
echo "[Cloud] Phase 5: Exporting Final Model"
echo "==================================================="
python3 training/train.py --phase export --model-path data/models/ppo_final.zip

echo ""
echo "==================================================="
echo "[Cloud] All Phases Completed!"
echo "==================================================="
