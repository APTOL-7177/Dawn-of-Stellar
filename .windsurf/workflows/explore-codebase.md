---
description: 코드베이스를 탐색하고 구조를 파악하는 워크플로우
---

# 코드베이스 탐색

## 1. 프로젝트 구조 개요
주요 디렉토리:
- `src/` — 핵심 게임 코드
  - `core/` — 핵심 유틸리티
  - `combat/` — 전투 시스템 (ATB, BRV, 데미지, 상태이상)
  - `character/` — 캐릭터, 스킬, 기믹, 트레이트
  - `world/` — 월드맵, 적 생성, 랜덤 이벤트
  - `ui/` — UI 렌더링 (전투, 보상, 결과)
  - `ai/` — 적 AI
  - `multiplayer/` — 멀티플레이어
  - `tutorial/` — 튜토리얼 시스템
  - `audio/` — 오디오 관리
  - `achievement/` — 업적
  - `cooking/`, `equipment/`, `gathering/` — 서브시스템
- `data/` — YAML 게임 데이터
  - `characters/` — 직업별 캐릭터 정의 (33개+)
  - `skills/` — 스킬 정의 (400개+)
  - `tutorials/` — 튜토리얼 정의
  - `teamwork_skills.yaml`, `passives.yaml`, `cooking_recipes.yaml`
- `tests/` — pytest 테스트 스위트
- `scripts/` — 밸런싱/검증 유틸리티
- `assets/` — 폰트, 오디오 리소스
- `config/` — 입력/진동/메타 설정

## 2. 핵심 대형 파일
// turbo
크기가 큰 핵심 파일 (이 파일들이 대부분의 로직을 담당):
- `src/character/gimmick_updater.py` (~333KB) — 전 직업 기믹 로직
- `src/combat/combat_manager.py` (~280KB) — 전투 전체 흐름
- `src/character/trait_effects.py` (~211KB) — 트레이트 효과
- `src/combat/enemy_skills.py` (~186KB) — 적 스킬 로직
- `src/character/character.py` (~110KB) — 캐릭터 클래스
- `src/character/skills/skill.py` (~60KB) — 스킬 실행
- `src/combat/damage_calculator.py` (~52KB) — 데미지 계산
- `src/character/gimmick_trait_effects.py` (~50KB) — 기믹-트레이트 연동

## 3. 게임 시스템 개요
- **ATB + BRV 하이브리드**: ATB 게이지가 차면 행동, BRV 공격 → HP 공격 2단계
- **33개+ 직업**: 각 직업은 고유 기믹(gimmick)을 가짐
- **YAML 기반 데이터**: 스킬/캐릭터 정의는 YAML, 로직은 Python
- **메타 프로그레션**: 별의 파편으로 해금/강화
- **4인 파티**: 게임 시작 시 선택, 변경 불가

## 4. 특정 기능 탐색
`code_search` 또는 `grep_search`로 키워드를 검색:
```
예: "crowd_cheer", "support_fire", "yomi", "rune_signal"
```
