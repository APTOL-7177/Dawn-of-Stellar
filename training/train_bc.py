"""행동 복제 학습 스크립트

LLM 플레이 로그(data/play_logs/*.jsonl)에서 전문가 행동을 학습합니다.
진행률 표시, 데이터 검증, 상세 로깅을 포함합니다.

사용법:
    python training/train_bc.py
    python training/train_bc.py --epochs 100 --batch-size 512 --lr 5e-4
    python training/train_bc.py --log-dir data/play_logs --save-path data/models/bc_weights.pt
"""

import argparse
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def validate_data(log_dir: str) -> int:
    """플레이 로그 데이터 검증 및 샘플 수 반환"""
    log_path = Path(log_dir)
    if not log_path.exists():
        print(f"[경고] 로그 디렉토리 없음: {log_path}")
        return 0

    import json
    total = 0
    invalid = 0
    log_files = list(log_path.glob("*.jsonl"))

    if not log_files:
        print(f"[경고] JSONL 파일 없음: {log_path}")
        return 0

    print(f"데이터 검증 중: {len(log_files)}개 파일...")
    for f in log_files:
        with open(f, "r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    state = rec.get("state", [])
                    action = rec.get("action")
                    if len(state) != 517 or action is None or not (0 <= action < 114):
                        invalid += 1
                    else:
                        total += 1
                except json.JSONDecodeError:
                    invalid += 1

    print(f"유효 샘플: {total}개, 무효: {invalid}개")
    return total


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dawn of Stellar 행동 복제 학습",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--epochs", type=int, default=50, help="학습 에폭 수")
    parser.add_argument("--batch-size", type=int, default=256, help="미니배치 크기")
    parser.add_argument("--lr", type=float, default=1e-3, help="학습률")
    parser.add_argument("--log-dir", type=str, default="data/play_logs", help="플레이 로그 디렉토리")
    parser.add_argument("--save-path", type=str, default="data/models/bc_weights.pt", help="가중치 저장 경로")
    parser.add_argument("--skip-validation", action="store_true", help="데이터 검증 건너뜀")
    args = parser.parse_args()

    print("=" * 55)
    print("Dawn of Stellar - 행동 복제 (Behavioral Cloning)")
    print("=" * 55)

    # 데이터 검증
    if not args.skip_validation:
        n_samples = validate_data(args.log_dir)
        if n_samples == 0:
            print("[오류] 유효한 학습 데이터가 없습니다.")
            print(f"  data/play_logs/*.jsonl 파일에 다음 형식의 데이터가 필요합니다:")
            print('  {"state": [517개 float], "action": int(0-113)}')
            sys.exit(1)
        print(f"\n학습 설정:")
        print(f"  샘플 수:   {n_samples:,}개")
        print(f"  에폭:      {args.epochs}")
        print(f"  배치 크기: {args.batch_size}")
        print(f"  학습률:    {args.lr}")
        print(f"  저장 경로: {args.save_path}")
        print()

    from src.rl.behavioral_cloning import BehavioralCloning

    bc = BehavioralCloning(log_dir=args.log_dir, model_dir=str(Path(args.save_path).parent))

    print("학습 시작...")
    result = bc.train(epochs=args.epochs, batch_size=args.batch_size, lr=args.lr)

    print("\n학습 결과:")
    print(f"  최종 손실:  {result['loss']:.4f}")
    print(f"  최종 정확도: {result['accuracy']:.1%}")
    print(f"  완료 에폭:  {result['epochs']}")

    bc.save(args.save_path)
    print(f"\n가중치 저장 완료: {args.save_path}")
    print("다음 단계: python training/train_ppo.py --bc-weights", args.save_path)


if __name__ == "__main__":
    main()
