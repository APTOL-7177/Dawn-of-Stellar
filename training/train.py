"""Dawn of Stellar RL 훈련 엔트리포인트

사용법:
    python training/train.py --phase bc
    python training/train.py --phase ppo --n-envs 8 --timesteps 5000000
    python training/train.py --phase eval --model-path data/models/ppo_final.zip --episodes 1000
    python training/train.py --phase export --model-path data/models/ppo_final.zip
"""

import argparse
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dawn of Stellar RL Training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
훈련 단계:
  bc     - 행동 복제 (LLM 플레이 로그로 사전 학습)
  ppo    - PPO 강화학습 (BC 가중치로 웜스타트 가능)
  eval   - 학습된 모델 평가 (1000판)
  export - SB3 모델을 TorchScript로 변환
        """,
    )
    parser.add_argument(
        "--phase",
        choices=["bc", "ppo", "eval", "export"],
        required=True,
        help="훈련 단계 선택",
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="모델 경로 (ppo: BC 가중치 경로, eval/export: 평가할 모델 경로)",
    )
    parser.add_argument(
        "--timesteps",
        type=int,
        default=5_000_000,
        help="PPO 총 학습 스텝 수 (기본: 5,000,000)",
    )
    parser.add_argument(
        "--n-envs",
        type=int,
        default=8,
        help="병렬 환경 수 (기본: 8)",
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=1000,
        help="평가 에피소드 수 (기본: 1000)",
    )
    args = parser.parse_args()

    if args.phase == "bc":
        # --- 행동 복제 학습 ---
        from src.rl.behavioral_cloning import BehavioralCloning

        print("=== 행동 복제 (Behavioral Cloning) 학습 시작 ===")
        bc = BehavioralCloning()
        result = bc.train()
        print(f"BC 학습 완료: {result}")
        bc.save()
        print("가중치 저장: data/models/bc_weights.pt")

    elif args.phase == "ppo":
        # --- PPO 강화학습 ---
        from src.rl.ppo_trainer import PPOTrainer

        bc_path = args.model_path or "data/models/bc_weights.pt"
        if not os.path.exists(bc_path):
            bc_path = None
            print("BC 가중치 없음 - 랜덤 초기화로 PPO 훈련")

        print(f"=== PPO 훈련 시작 (스텝={args.timesteps:,}, 환경={args.n_envs}) ===")
        trainer = PPOTrainer(
            n_envs=args.n_envs,
            total_timesteps=args.timesteps,
            bc_weights_path=bc_path,
        )
        trainer.setup()
        model_path = trainer.train()
        print(f"PPO 훈련 완료: {model_path}")

    elif args.phase == "eval":
        # --- 모델 평가 ---
        from src.rl.evaluation import Evaluator

        model_path = args.model_path or "data/models/ppo_final.zip"
        print(f"=== 모델 평가 시작 ({args.episodes}판): {model_path} ===")
        evaluator = Evaluator(model_path=model_path, n_episodes=args.episodes)
        results = evaluator.evaluate()
        print(evaluator.report(results))

    elif args.phase == "export":
        # --- TorchScript 내보내기 ---
        from src.rl.model_export import ModelExporter

        model_path = args.model_path or "data/models/ppo_final.zip"
        print(f"=== TorchScript 변환: {model_path} ===")
        output_path = ModelExporter.export_torchscript(model_path)
        print(f"모델 내보내기 완료: {output_path}")


if __name__ == "__main__":
    main()
