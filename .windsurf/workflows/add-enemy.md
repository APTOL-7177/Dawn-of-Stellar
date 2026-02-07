---
description: 새로운 적/보스를 추가하는 워크플로우
---

# 새 적/보스 추가

## 1. 적 생성 시스템 파악
// turbo
`src/world/enemy_generator.py`를 읽어 적 생성 로직을 파악한다.
- 스케일링 공식
- 적 타입별 스탯 범위
- 보스 생성 로직

## 2. 적 스킬 추가
`src/combat/enemy_skills.py`에 새 적의 스킬을 구현한다:
- 일반 공격 패턴
- 특수 스킬/기믹
- 보스인 경우 페이즈별 패턴

## 3. 보스 기믹 추가 (보스인 경우)
`src/combat/boss_gimmicks.py`에 보스 고유 기믹을 구현한다.
`src/combat/boss_dialogue.py`에 보스 대사를 추가한다.

## 4. AI 패턴 설정
`src/ai/enemy_ai.py`에서 새 적의 행동 패턴을 정의한다:
- 스킬 사용 우선순위
- HP 기반 행동 변화
- 타겟 선택 로직

## 5. 스케일링 확인
`src/world/enemy_generator.py`의 `_apply_early_game_scaling` 등에서
새 적이 적절한 난이도로 스케일링되는지 확인한다.

## 6. 테스트
```bash
pytest tests/ -x -q -k "enemy or boss"
python main.py --dev
```
