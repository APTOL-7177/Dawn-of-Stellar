"""하드웨어 자동 감지 & 학습 하이퍼파라미터 최적화

GPU VRAM, CPU 코어, RAM을 감지하여
n_envs, batch_size, n_steps 등을 자동 결정합니다.

사용법:
    python training/auto_tune.py              # JSON 출력
    python training/auto_tune.py --shell      # shell 변수 출력 (cloud_train.sh용)
    python training/auto_tune.py --verbose    # 상세 출력
"""

import argparse
import json
import os
import sys
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def detect_gpu() -> Dict[str, Any]:
    """GPU 정보 감지"""
    try:
        import torch
        if not torch.cuda.is_available():
            return {"available": False, "name": "none", "vram_gb": 0, "count": 0}

        gpu_count = torch.cuda.device_count()
        gpu_name = torch.cuda.get_device_name(0)
        props = torch.cuda.get_device_properties(0)
        vram_bytes = getattr(props, "total_memory", None) or getattr(props, "total_mem", 0)
        vram_gb = vram_bytes / (1024 ** 3)

        return {
            "available": True,
            "name": gpu_name,
            "vram_gb": round(vram_gb, 1),
            "count": gpu_count,
        }
    except ImportError:
        return {"available": False, "name": "no_torch", "vram_gb": 0, "count": 0}


def detect_cpu() -> Dict[str, Any]:
    """CPU 정보 감지"""
    import multiprocessing
    cpu_count = multiprocessing.cpu_count()

    # 물리 코어 수 (가능한 경우)
    physical_cores = cpu_count
    try:
        physical_cores = len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        pass

    return {
        "logical_cores": cpu_count,
        "physical_cores": physical_cores,
    }


def detect_ram() -> Dict[str, Any]:
    """RAM 정보 감지"""
    try:
        import psutil
        mem = psutil.virtual_memory()
        return {
            "total_gb": round(mem.total / (1024 ** 3), 1),
            "available_gb": round(mem.available / (1024 ** 3), 1),
        }
    except ImportError:
        # psutil 없으면 /proc/meminfo 시도 (Linux)
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        total_gb = kb / (1024 ** 2)
                        return {"total_gb": round(total_gb, 1), "available_gb": round(total_gb * 0.8, 1)}
        except FileNotFoundError:
            pass
        return {"total_gb": 0, "available_gb": 0}


def calculate_optimal_params(
    gpu: Dict[str, Any],
    cpu: Dict[str, Any],
    ram: Dict[str, Any],
) -> Dict[str, Any]:
    """하드웨어 스펙에 기반한 최적 하이퍼파라미터 계산

    핵심 원리:
    - n_envs: CPU 바운드 (SubprocVecEnv는 프로세스당 1코어)
    - batch_size: GPU VRAM 바운드 (정책 업데이트 시 GPU 사용)
    - n_steps: n_envs * n_steps = 롤아웃 버퍼 크기
    """
    cores = cpu["physical_cores"]
    ram_gb = ram.get("available_gb") or ram.get("total_gb", 8) * 0.8
    vram_gb = gpu["vram_gb"]

    # === n_envs 결정 ===
    # SubprocVecEnv는 환경당 1 프로세스 = 1 코어
    # 메인 프로세스 + PyTorch 스레드용으로 2코어 여유
    env_by_cpu = max(4, cores - 2)

    # 환경당 ~80MB RAM 사용 (HeadlessCombat + Python 오버헤드)
    # RAM의 70%까지 환경에 할당
    env_by_ram = max(4, int(ram_gb * 0.7 / 0.08))

    # GPU 없으면 CPU만으로 제한적 학습
    if not gpu["available"]:
        n_envs = min(env_by_cpu, env_by_ram, 16)
    else:
        # GPU 있으면 CPU/RAM 기준으로 최대한 병렬화
        n_envs = min(env_by_cpu, env_by_ram)

    # SubprocVecEnv 상한 (FD 한도 및 IPC 오버헤드 고려)
    n_envs = min(n_envs, 512)

    # 2의 배수로 정렬 (SIMD 친화적)
    n_envs = max(4, (n_envs // 2) * 2)

    # === n_steps 결정 (batch_size보다 먼저 결정해야 함) ===
    # n_envs가 크면 n_steps를 줄여도 버퍼는 충분하지만,
    # n_steps가 너무 작으면 GPU 업데이트 대기 비율이 높아져 CPU 유휴 발생.
    if n_envs >= 128:
        n_steps = 2048
    elif n_envs >= 32:
        n_steps = 1024
    else:
        n_steps = 2048  # 소규모는 n_steps로 버퍼 보상

    # === batch_size 결정 ===
    # VRAM 기반 상한
    if vram_gb >= 20:
        max_batch = 8192
    elif vram_gb >= 10:
        max_batch = 4096
    elif vram_gb >= 6:
        max_batch = 2048
    elif vram_gb >= 3:
        max_batch = 1024
    else:
        max_batch = 512

    # 버퍼 크기에 비례하여 batch_size 결정 (목표: ~600 gradient 스텝)
    total_rollout = n_envs * n_steps
    ideal_batch = max(256, total_rollout * 3 // 600)
    batch_size = min(ideal_batch, max_batch)
    # 256의 배수로 정렬
    batch_size = max(256, (batch_size // 256) * 256)

    # batch_size는 n_envs * n_steps의 약수여야 함 (SB3 요구사항)
    while total_rollout % batch_size != 0 and batch_size > 64:
        batch_size -= 64
    if total_rollout % batch_size != 0:
        batch_size = 256  # 안전 폴백

    # === 학습률 결정 ===
    # 배치가 크면 학습률도 약간 높여도 됨
    if batch_size >= 2048:
        lr = 5e-4
    elif batch_size >= 1024:
        lr = 3e-4
    else:
        lr = 2.5e-4

    # === n_epochs 결정 ===
    # 롤아웃당 총 gradient 업데이트 = (buffer / batch_size) * n_epochs
    # 너무 많으면 clip_fraction/KL이 폭등 → 학습 불안정
    # 목표: 롤아웃당 총 gradient 스텝 300~800회
    minibatches_per_epoch = total_rollout // batch_size
    target_total_steps = 600  # 목표 gradient 스텝/롤아웃
    n_epochs = max(3, min(10, target_total_steps // max(minibatches_per_epoch, 1)))

    return {
        "n_envs": n_envs,
        "batch_size": batch_size,
        "n_steps": n_steps,
        "n_epochs": n_epochs,
        "lr": lr,
        "rollout_buffer_size": total_rollout,
        "minibatches_per_update": total_rollout // batch_size,
    }


def auto_tune(verbose: bool = False) -> Dict[str, Any]:
    """전체 자동 튜닝 실행"""
    gpu = detect_gpu()
    cpu = detect_cpu()
    ram = detect_ram()
    params = calculate_optimal_params(gpu, cpu, ram)

    result = {
        "hardware": {
            "gpu": gpu,
            "cpu": cpu,
            "ram": ram,
        },
        "params": params,
    }

    if verbose:
        print("=" * 55)
        print("Dawn of Stellar - 하드웨어 자동 감지")
        print("=" * 55)
        print(f"\n[GPU]")
        if gpu["available"]:
            print(f"  이름:     {gpu['name']}")
            print(f"  VRAM:     {gpu['vram_gb']} GB")
            print(f"  수량:     {gpu['count']}개")
        else:
            print(f"  GPU 없음 (CPU 전용 모드)")

        print(f"\n[CPU]")
        print(f"  물리 코어: {cpu['physical_cores']}개")
        print(f"  논리 코어: {cpu['logical_cores']}개")

        print(f"\n[RAM]")
        print(f"  전체:     {ram['total_gb']} GB")
        print(f"  가용:     {ram.get('available_gb', '?')} GB")

        print(f"\n[최적 파라미터]")
        print(f"  병렬 환경 (n_envs):    {params['n_envs']}")
        print(f"  배치 크기 (batch_size): {params['batch_size']}")
        print(f"  수집 스텝 (n_steps):    {params['n_steps']}")
        print(f"  학습 에폭 (n_epochs):   {params['n_epochs']}")
        print(f"  학습률 (lr):            {params['lr']}")
        print(f"  롤아웃 버퍼:            {params['rollout_buffer_size']:,} 샘플")
        print(f"  미니배치/업데이트:      {params['minibatches_per_update']}회")

    return result


def main():
    parser = argparse.ArgumentParser(description="학습 하이퍼파라미터 자동 튜닝")
    parser.add_argument("--shell", action="store_true", help="shell 변수 형식 출력")
    parser.add_argument("--verbose", action="store_true", help="상세 출력")
    parser.add_argument("--json", action="store_true", help="JSON 출력 (기본)")
    args = parser.parse_args()

    result = auto_tune(verbose=args.verbose)

    if args.shell:
        p = result["params"]
        print(f"N_ENVS={p['n_envs']}")
        print(f"BATCH_SIZE={p['batch_size']}")
        print(f"N_STEPS={p['n_steps']}")
        print(f"N_EPOCHS={p['n_epochs']}")
        print(f"LR={p['lr']}")
        hw = result["hardware"]
        print(f"GPU_NAME=\"{hw['gpu']['name']}\"")
        print(f"GPU_VRAM={hw['gpu']['vram_gb']}")
        print(f"CPU_CORES={hw['cpu']['physical_cores']}")
        print(f"RAM_GB={hw['ram']['total_gb']}")
    elif not args.verbose:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
