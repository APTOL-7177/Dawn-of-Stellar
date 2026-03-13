"""PPO 훈련 스크립트

MaskablePPO로 Dawn of Stellar 전투 AI를 훈련합니다.
TensorBoard 로깅, 체크포인트 관리, wandb 선택적 지원을 포함합니다.

사용법:
    python training/train_ppo.py
    python training/train_ppo.py --bc-weights data/models/bc_weights.pt
    python training/train_ppo.py --resume data/models/checkpoints/ppo_combat_100000_steps.zip
    python training/train_ppo.py --timesteps 10000000 --n-envs 16
    python training/train_ppo.py --wandb --wandb-project dawn-of-stellar-rl
"""

import argparse
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# wandb 선택적 임포트
try:
    import wandb
    HAS_WANDB = True
except ImportError:
    HAS_WANDB = False


def setup_tensorboard(log_dir: str) -> None:
    """TensorBoard 설정 안내"""
    print(f"\nTensorBoard 로그: {log_dir}")
    print(f"  실행: tensorboard --logdir {log_dir}")
    print(f"  접속: http://localhost:6006\n")


def setup_wandb(project: str, config: dict) -> bool:
    """wandb 초기화 (설치된 경우에만)"""
    if not HAS_WANDB:
        print("[정보] wandb 미설치. pip install wandb로 설치하면 실험 추적이 가능합니다.")
        return False
    try:
        wandb.init(project=project, config=config, sync_tensorboard=True)
        print(f"wandb 초기화 완료: {project}")
        return True
    except Exception as e:
        print(f"[경고] wandb 초기화 실패: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dawn of Stellar PPO 강화학습 훈련",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--timesteps", type=int, default=5_000_000, help="총 학습 스텝 수")
    parser.add_argument("--n-envs", type=int, default=8, help="병렬 환경 수")
    parser.add_argument("--lr", type=float, default=3e-4, help="학습률")
    parser.add_argument("--n-steps", type=int, default=2048, help="환경당 수집 스텝 수")
    parser.add_argument("--batch-size", type=int, default=256, help="미니배치 크기")
    parser.add_argument("--n-epochs", type=int, default=10, help="PPO 업데이트 에폭 수")
    parser.add_argument("--gamma", type=float, default=0.99, help="할인 계수")
    parser.add_argument("--gae-lambda", type=float, default=0.95, help="GAE 람다")
    parser.add_argument("--bc-weights", type=str, default=None, help="BC 사전 학습 가중치 경로")
    parser.add_argument("--resume", type=str, default=None, help="재개할 체크포인트 경로")
    parser.add_argument("--model-dir", type=str, default="data/models", help="모델 저장 디렉토리")
    parser.add_argument("--log-dir", type=str, default="data/rl_logs", help="TensorBoard 로그 디렉토리")
    parser.add_argument("--wandb", action="store_true", help="wandb 로깅 활성화")
    parser.add_argument("--wandb-project", type=str, default="dawn-of-stellar-rl", help="wandb 프로젝트명")
    args = parser.parse_args()

    print("=" * 55)
    print("Dawn of Stellar - PPO 강화학습 훈련")
    print("=" * 55)
    print(f"  총 스텝:    {args.timesteps:,}")
    print(f"  병렬 환경:  {args.n_envs}개")
    print(f"  학습률:     {args.lr}")
    print(f"  BC 가중치:  {args.bc_weights or '없음 (랜덤 초기화)'}")
    print(f"  재개:       {args.resume or '없음 (새로 시작)'}")
    print()

    # TensorBoard 안내
    setup_tensorboard(args.log_dir)

    # wandb 설정
    wandb_active = False
    if args.wandb:
        config = {
            "timesteps": args.timesteps,
            "n_envs": args.n_envs,
            "lr": args.lr,
            "n_steps": args.n_steps,
            "batch_size": args.batch_size,
            "n_epochs": args.n_epochs,
        }
        wandb_active = setup_wandb(args.wandb_project, config)

    from src.rl.ppo_trainer import PPOTrainer

    trainer = PPOTrainer(
        n_envs=args.n_envs,
        total_timesteps=args.timesteps,
        learning_rate=args.lr,
        n_steps=args.n_steps,
        batch_size=args.batch_size,
        n_epochs=args.n_epochs,
        gamma=args.gamma,
        gae_lambda=args.gae_lambda,
        model_dir=args.model_dir,
        log_dir=args.log_dir,
        bc_weights_path=args.bc_weights,
    )

    if args.resume:
        print(f"체크포인트에서 재개: {args.resume}")
        trainer.resume(args.resume)
    else:
        trainer.setup()

    print("PPO 훈련 시작...")
    model_path = trainer.train()

    print(f"\nPPO 훈련 완료: {model_path}")
    print("다음 단계:")
    print(f"  평가: python training/evaluate.py --model-path {model_path}")
    print(f"  변환: python training/train.py --phase export --model-path {model_path}")

    if wandb_active:
        wandb.finish()


if __name__ == "__main__":
    main()
