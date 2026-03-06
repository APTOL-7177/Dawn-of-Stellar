<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# src

## Purpose
Dawn of Stellar 게임의 전체 소스 코드. 245개 Python 파일, 21개 모듈.

## Key Files
| File | Description |
|------|-------------|
| `__init__.py` | 패키지 초기화 |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| `achievement/` | 성취/업적 시스템 - 마일스톤 추적, 업적 잠금 해제 (achievement_manager.py, achievement_system.py, milestone_system.py) |
| `ai/` | 적 AI 행동 - 적 행동 패턴 결정 (enemy_ai.py) |
| `audio/` | 오디오 관리 - BGM/SE/ME 재생 및 볼륨 제어 (audio_manager.py) |
| `bot/` | 봇/자동화 - 게임 상태 내보내기, LLM 봇 지원 (game_state_exporter.py) |
| `character/` | 캐릭터 시스템 - 35개 직업, 414개 스킬, 스탯, 특성, 파티 관리 |
| `combat/` | 전투 시스템 - ATB, Brave, 데미지 계산, 보스 기믹, 상태이상 |
| `cooking/` | 요리/제조 시스템 - 포션 양조, 폭탄 제작, 레시피 관리 |
| `core/` | 핵심 인프라 - 설정, 이벤트 버스, 로거, 난이도, 진동, 핫리로드 |
| `equipment/` | 장비 시스템 - 아이템, 인벤토리, 장비 효과 |
| `field/` | 필드 시스템 - 필드 스킬, 채집, 요리 (탐색 중 사용) |
| `gathering/` | 채집 시스템 - 수확 가능 오브젝트, 재료 정의 |
| `multiplayer/` | 멀티플레이어 - 세션, 프로토콜, 플레이어 상태, 부활, AI봇 |
| `persistence/` | 저장/불러오기 - 세이브 시스템, 메타 진행도 |
| `quest/` | 퀘스트 시스템 - 퀘스트 관리자 |
| `story/` | 스토리 시스템 - 세피로스/카인 조우 이벤트, 컷씬 |
| `systems/` | 게임 시스템 - 상처(wound) 시스템 |
| `town/` | 마을 시스템 - 마을 관리자, 층 전환, 마을 맵 |
| `tutorial/` | 튜토리얼 - 직업 선택 UI, 스토리 진행, 튜토리얼 모드, 단계 관리 |
| `ui/` | 사용자 인터페이스 - 60+ 파일 (메인메뉴, 전투UI, 인벤토리, 상점, 멀티플레이어 등) |
| `utils/` | 유틸리티 함수 모음 |
| `world/` | 월드 생성 - 던전 생성, 적 배치, FOV, 탐색, 타일, 랜덤 이벤트 |

## Module Details

### character/
- `character.py` - Character 클래스 (스탯, 스킬, 버프/디버프 관리)
- `character_loader.py` - YAML에서 캐릭터 데이터 로드
- `job_stats_loader.py` - 직업별 스탯 로드 (35개 직업)
- `party.py` - 파티 구성 및 관리
- `stats.py` - 스탯 데이터클래스
- `basic_attacks.py` - 기본 공격 정의
- `gimmick_trait_effects.py` / `gimmick_updater.py` - 직업 기믹 특성 효과
- `trait_effects.py` / `upgrade_applier.py` - 특성 효과 및 업그레이드
- `skills/skill.py` - Skill 클래스 기반 정의
- `skills/skill_manager.py` - 스킬 로드 및 실행 관리
- `skills/yaml_skill_loader.py` - YAML 스킬 데이터 로더 (414개 스킬)
- `skills/skill_initializer.py` - 스킬 초기화
- `skills/custom_handlers.py` - 커스텀 스킬 핸들러
- `skills/teamwork_skill.py` / `teamwork_effects.py` - 팀워크 스킬
- `skills/costs/` - 스킬 비용 (mp, hp, stack, gimmick)
- `skills/effects/` - 스킬 효과 25개 (damage, heal, buff, shield, status, lifesteal, taunt 등)
- `skills/job_skills/` - 직업별 스킬 파일 35개 (alchemist ~ warrior)
- `classes/` - 직업 클래스 정의

### combat/
- `atb_system.py` - Active Time Battle 시스템
- `brave_system.py` - Brave/Default 시스템
- `casting_system.py` - 스킬 시전 및 캐스팅 관리
- `combat_manager.py` - 전투 흐름 총괄 관리자
- `damage_calculator.py` - 데미지 계산 공식
- `status_effects.py` - 상태이상 효과 (독, 침묵, 스턴 등)
- `experience_system.py` - 경험치 및 레벨업
- `boss_gimmicks.py` - 보스 기믹 패턴
- `boss_dialogue.py` - 보스 대화
- `boss_timer_system.py` - 보스 타이머 기믹
- `sephiroth_skills.py` / `cain_skills.py` - 최종 보스 스킬
- `enemy_skills.py` - 일반 적 스킬

### multiplayer/
- `session.py` - 멀티플레이어 세션 관리
- `protocol.py` - 네트워크 프로토콜
- `player.py` / `player_state.py` - 플레이어 및 상태
- `party_setup.py` - 멀티 파티 구성
- `revival_system.py` / `skill_revival_handler.py` - 부활 시스템
- `ai_bot.py` / `llm_player_bot.py` - AI/LLM 플레이어 봇
- `validation.py` - 상태 검증
- `test_helper.py` - 멀티플레이어 테스트 헬퍼

### ui/
- `world_ui.py` - 던전 탐색 메인 UI
- `combat_ui.py` - 전투 화면 UI
- `main_menu.py` - 메인 메뉴
- `game_menu.py` / `pause_menu.py` - 인게임/일시정지 메뉴
- `tcod_display.py` - tcod 디스플레이 모듈
- `multiplayer_lobby.py` / `multiplayer_menu.py` 등 - 멀티플레이어 UI
- `inventory_ui.py` / `loot_ui.py` / `storage_ui.py` - 아이템/인벤토리 UI
- `shop_ui.py` / `gold_shop_ui.py` / `anvil_ui.py` - 상점 UI
- `party_setup.py` / `passive_selection.py` / `trait_selection.py` - 캐릭터 설정 UI
- `quest_board_ui.py` / `quest_list_ui.py` - 퀘스트 UI
- `npc_dialog_ui.py` - NPC 대화 및 스토리 시퀀스
- `ai_spectate_mode.py` / `ai_bug_hunter.py` - AI 관전/디버그 모드
- `training_mode.py` - 훈련 모드 UI
- `input_handler.py` - 입력 처리
- `key_bindings_ui.py` / `settings_ui.py` - 설정 UI

### world/
- `dungeon_generator.py` - 절차적 던전 생성
- `enemy_generator.py` - 적 배치 생성
- `exploration.py` - 필드 탐색 로직
- `fov.py` - 시야 계산 (FOV)
- `tile.py` - 타일 타입 정의
- `map_renderer.py` - 맵 렌더링
- `interactive_object.py` - 상호작용 오브젝트
- `environmental_effects.py` - 환경 효과
- `random_events.py` - 랜덤 이벤트
- `field_skills.py` - 필드 스킬 효과

### core/
- `config.py` - 게임 설정 로드/접근
- `event_bus.py` - 이벤트 버스 (발행/구독 패턴)
- `logger.py` - 로거 팩토리 (`get_logger`, `Loggers`)
- `difficulty.py` - 난이도 설정
- `vibration_system.py` - 진동 피드백
- `hot_reload.py` - 개발 중 핫리로드

## For AI Agents

### Working In This Directory
- 모든 코딩 규칙은 `../AGENTS.md` 참조
- 크로스 모듈 임포트는 최소화; `core` 헬퍼를 통해 의존성 주입 선호
- `character/skills/` 변경 시 YAML 스킬 데이터(`data/skills/`)와 동기화 확인
- `combat/` 변경 시 `tests/test_combat_*.py` 반드시 실행
- `multiplayer/` 변경 시 `run_multiplayer_tests.py`로 통합 테스트 실행
- 새 직업/스킬 추가: `.claude/commands/add-job.md`, `.claude/commands/add-skill.md` 참조

### Testing Requirements
- `pytest tests/test_character*.py` - 캐릭터 관련
- `pytest tests/test_combat*.py` - 전투 관련
- `pytest tests/test_skill*.py` - 스킬 관련
- `pytest tests/test_multiplayer*.py` - 멀티플레이어
- `python run_multiplayer_tests.py` - 멀티플레이어 통합

## Dependencies

### External
- tcod - 콘솔 렌더링, FOV, 경로 탐색
- pygame - 오디오 재생 (audio 모듈)
- PyYAML - 스킬/캐릭터 데이터 로드
- numpy - 맵 배열 처리 (world 모듈)

### Internal Cross-Module
- `core.logger` - 모든 모듈에서 사용
- `core.event_bus` - 이벤트 기반 통신
- `character.Character` - combat, multiplayer, ui 전반에서 참조
- `world.dungeon_generator` + `world.exploration` - ui.world_ui의 핵심 의존성

<!-- MANUAL: -->
