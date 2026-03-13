<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# training/

## Purpose
강화학습(RL) 모델 학습 및 평가 코드 디렉토리입니다. PPO, Behavioral Cloning 등 AI 에이전트 학습 스크립트와 설정을 포함합니다.

## Key Files
| File | Description |
|------|-------------|
| train.py | 통합 학습 스크립트 (메인 진입점) |
| train_ppo.py | PPO(Proximal Policy Optimization) 학습 |
| train_bc.py | Behavioral Cloning (모방 학습) |
| evaluate.py | 학습된 모델 성능 평가 |
| auto_tune.py | 하이퍼파라미터 자동 튜닝 |
| collect_play_logs.py | 플레이 로그 수집 (학습 데이터) |
| requirements_training.txt | RL 학습 패키지 의존성 |
| Dockerfile | Docker 컨테이너 빌드 (클라우드 학습용) |

## Subdirectories
없음

## For AI Agents

### Working In This Directory
- 학습 스크립트 실행 시 GPU 권장 (cuda, torch 필요)
- 학습 데이터는 data/play_logs/, data/rl_logs/에서 로드
- 학습된 모델은 data/models/에 저장됨

### Common Patterns
- 환경: src/gym/ 강화학습 환경 클래스 사용
- 에이전트: src/rl/ 에이전트 구현
- 하이퍼파라미터: YAML 또는 Python dict로 설정
- 로깅: TensorFlow events 또는 W&B(Weights & Biases)

## Dependencies
- torch (PyTorch - RL 프레임워크)
- numpy, pandas (데이터 처리)
- src/gym/ (강화학습 환경)
- src/rl/ (RL 에이전트)
- data/play_logs/ (학습 데이터)
- requirements_training.txt (전체 패키지 목록)

## Notes
- 클라우드 학습: Dockerfile 사용하여 Docker 이미지 빌드
- 로컬 학습: `python train.py --config config.yaml`
- GPU 필수 (학습 속도 향상)

<!-- MANUAL: -->
