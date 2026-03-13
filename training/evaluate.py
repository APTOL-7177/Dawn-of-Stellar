"""모델 평가 스크립트

학습된 RL 모델을 자동 평가하고 결과를 CSV로 저장합니다.
여러 모델 간 비교를 지원합니다.

사용법:
    python training/evaluate.py --model-path data/models/ppo_final.zip
    python training/evaluate.py --model-path model_a.zip --compare model_b.zip
    python training/evaluate.py --model-path model.zip --episodes 500 --output results.csv
    python training/evaluate.py --random-baseline --episodes 200
"""

import argparse
import sys
import os
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def save_csv(results: Dict[str, Any], output_path: str, model_label: str = "model") -> None:
    """평가 결과를 CSV로 저장"""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    is_new = not Path(output_path).exists()

    # 직업별 승률을 평탄화
    flat_results = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": model_label,
        "n_episodes": results.get("n_episodes", 0),
        "n_wins": results.get("n_wins", 0),
        "win_rate": f"{results.get('win_rate', 0.0):.4f}",
        "avg_turns": f"{results.get('avg_turns', 0.0):.2f}",
        "avg_reward": f"{results.get('avg_reward', 0.0):.4f}",
        "skill_diversity": f"{results.get('skill_diversity', 0.0):.4f}",
        "brv_management_score": f"{results.get('brv_management_score', 0.0):.4f}",
    }

    # 직업별 승률 추가
    for job_id, rate in results.get("job_win_rates", {}).items():
        flat_results[f"win_rate_{job_id}"] = f"{rate:.4f}"

    with open(output_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=flat_results.keys())
        if is_new:
            writer.writeheader()
        writer.writerow(flat_results)

    print(f"CSV 저장: {output_path}")


def compare_models(
    model_paths: List[str],
    n_episodes: int,
    output_path: Optional[str],
) -> None:
    """여러 모델 비교 평가"""
    from src.rl.evaluation import Evaluator

    all_results = []
    for model_path in model_paths:
        print(f"\n평가 중: {model_path}")
        evaluator = Evaluator(model_path=model_path, n_episodes=n_episodes)
        results = evaluator.evaluate()
        results["model_path"] = model_path
        all_results.append(results)

        print(evaluator.report(results))
        if output_path:
            save_csv(results, output_path, model_label=Path(model_path).stem)

    # 비교 요약 출력
    if len(all_results) > 1:
        print("\n" + "=" * 55)
        print("모델 비교 요약")
        print("=" * 55)
        print(f"{'모델':<35} {'승률':>8} {'평균턴':>8} {'다양성':>8}")
        print("-" * 60)
        for r in all_results:
            name = Path(r["model_path"]).stem[:33]
            print(
                f"{name:<35} "
                f"{r['win_rate']:>7.1%} "
                f"{r['avg_turns']:>7.1f}턴 "
                f"{r['skill_diversity']:>7.3f}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dawn of Stellar RL 모델 평가",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="평가할 모델 경로 (.zip)",
    )
    parser.add_argument(
        "--compare",
        type=str,
        nargs="+",
        default=None,
        help="비교할 추가 모델 경로들",
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=1000,
        help="평가 에피소드 수",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="CSV 결과 저장 경로 (예: data/eval_results.csv)",
    )
    parser.add_argument(
        "--random-baseline",
        action="store_true",
        help="랜덤 행동 베이스라인 평가 (모델 없음)",
    )
    args = parser.parse_args()

    print("=" * 55)
    print("Dawn of Stellar - RL 모델 평가")
    print("=" * 55)

    # 비교 모드
    if args.compare and args.model_path:
        all_paths = [args.model_path] + args.compare
        compare_models(all_paths, args.episodes, args.output)
        return

    # 단일 모델 평가
    from src.rl.evaluation import Evaluator

    model_path = args.model_path
    if args.random_baseline:
        model_path = None
        print(f"랜덤 베이스라인 평가: {args.episodes}판")
    else:
        if model_path is None:
            model_path = "data/models/ppo_final.zip"
        print(f"모델 평가: {model_path} ({args.episodes}판)")

    evaluator = Evaluator(model_path=model_path, n_episodes=args.episodes)
    results = evaluator.evaluate()

    report = evaluator.report(results)
    print(report)

    if args.output:
        label = "random" if args.random_baseline else Path(model_path or "unknown").stem
        save_csv(results, args.output, model_label=label)


if __name__ == "__main__":
    main()
