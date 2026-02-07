# Project Navigator Skill

Dawn of Stellar 프로젝트 구조 탐색 전문 스킬

## 프로젝트 아키텍처

### src/ 모듈 맵
```
src/
├── core/          — 핵심 유틸, 게임 루프, 설정
├── combat/        — 전투 시스템 (ATB, BRV, 데미지, 상태이상, 보스)
├── character/     — 캐릭터, 스킬, 기믹, 트레이트, 스탯
│   ├── skills/    — 스킬 시스템 (YAML 로더, 핸들러, 효과)
│   │   ├── effects/    — 효과별 처리기
│   │   ├── job_skills/ — 직업별 특수 스킬 (35개 파일)
│   │   └── costs/      — 비용 처리기
│   └── classes/   — 클래스 정의
├── world/         — 월드맵, 적 생성, 랜덤 이벤트, 던전
├── ui/            — 모든 UI (전투, 메뉴, 보상, 결과, HUB 등)
├── ai/            — 적 AI 로직
├── audio/         — BGM/SFX 관리
├── multiplayer/   — 멀티플레이어 (WebSocket)
├── tutorial/      — 튜토리얼 시스템
├── achievement/   — 업적 시스템
├── cooking/       — 요리 시스템
├── equipment/     — 장비 시스템
├── gathering/     — 채집 시스템
├── field/         — 필드 탐험
├── town/          — 마을
├── story/         — 스토리/대사
├── quest/         — 퀘스트
├── persistence/   — 저장/로드
├── bot/           — 자동 플레이 봇
└── utils/         — 유틸리티
```

### data/ 데이터 맵
```
data/
├── characters/          — 직업 정의 YAML (35개)
├── skills/              — 스킬 정의 YAML (414개)
├── tutorials/           — 튜토리얼 YAML (8개)
├── teamwork_skills.yaml — 팀워크 스킬 정의
├── passives.yaml        — 패시브 스킬
└── cooking_recipes.yaml — 요리 레시피
```

## 파일 크기 TOP 10 (로직 밀집도)
1. `gimmick_updater.py` ~333KB — 모든 직업 기믹
2. `combat_manager.py` ~280KB — 전투 전체 흐름
3. `trait_effects.py` ~211KB — 트레이트 효과
4. `enemy_skills.py` ~186KB — 적 전용 스킬
5. `character.py` ~110KB — 캐릭터 핵심 클래스
6. `skill.py` ~60KB — 스킬 실행 엔진
7. `damage_calculator.py` ~52KB — 데미지 공식
8. `gimmick_trait_effects.py` ~50KB — 기믹-트레이트 연동
9. `status_effects.py` ~49KB — 상태이상
10. `brave_system.py` ~40KB — BRV 시스템

## 기능별 탐색 가이드

### "이 스킬이 왜 안 되지?"
1. `data/skills/<id>.yaml` → 데이터 확인
2. `src/character/skills/yaml_skill_loader.py` → 로딩 확인
3. `src/character/skills/custom_handlers.py` → 커스텀 핸들러
4. `src/character/skills/job_skills/<job>.py` → 직업별 구현
5. `src/combat/combat_manager.py` → 실행 흐름

### "이 기믹이 왜 안 되지?"
1. `data/characters/<job>.yaml` → `gimmick:` 정의
2. `src/character/gimmick_updater.py` → 기믹 로직
3. `src/combat/combat_manager.py` → 이벤트 훅
4. `src/character/gimmick_trait_effects.py` → 트레이트 연동

### "데미지가 이상해요"
1. `src/combat/damage_calculator.py` → 데미지 공식
2. `src/combat/brave_system.py` → BRV 계산
3. `data/skills/<id>.yaml` → multiplier, stat_base
4. `data/characters/<job>.yaml` → base_stats

### "UI가 잘못 표시돼요"
1. `src/ui/combat_ui.py` → 전투 UI
2. `src/ui/reward_ui.py` → 보상 화면
3. `src/ui/game_result_ui.py` → 결과 화면

### "적이 너무 강하거나 약해요"
1. `src/world/enemy_generator.py` → 적 생성/스케일링
2. `src/ai/enemy_ai.py` → 적 행동 패턴
3. `src/combat/enemy_skills.py` → 적 스킬
4. `src/combat/boss_gimmicks.py` → 보스 기믹
