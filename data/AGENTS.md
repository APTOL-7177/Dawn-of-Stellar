<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# data/

## Purpose
게임 데이터 저장소. 35개 직업 캐릭터, 414+ 스킬, 튜토리얼, 요리 레시피, 팀워크 스킬을 YAML로 정의합니다. RPG/스토리 모드 설정, 학습 모델, 플레이 로그도 관리합니다.

## Key Files
| File | Description |
|------|-------------|
| cooking_recipes.yaml | 요리 시스템: 재료 조합 -> 아이템 정의 |
| teamwork_skills.yaml | 팀워크 스킬: 35개 직업 조합별 협력 스킬 |
| passives.yaml | 패시브 스킬 (특성) 전역 정의 |

## Subdirectories
| Directory | Purpose |
|-----------|---------|
| characters/ | 35개 직업별 YAML 정의 (warrior.yaml, berserker.yaml 등) |
| skills/ | 414+ 스킬 YAML 파일 (이름순 정렬) |
| tutorials/ | 12개 튜토리얼 + 튜토리얼 설정 (tutorial_config.yaml) |
| rpg_mode/ | RPG 모드 설정 (rpg_config.yaml) |
| story_mode/ | 스토리 모드 설정 및 chapters/ 하위디렉토리 |
| models/ | 학습된 RL 모델 (PyTorch .pt 형식) |
| play_logs/ | 플레이 로그 (JSONL 형식) |
| rl_logs/ | 강화학습 학습 로그 (TensorFlow events) |

## For AI Agents

### Working In This Directory
- YAML 스키마는 src/character/character_loader.py, src/character/skills/yaml_skill_loader.py 에서 정의
- 직업별 캐릭터: 기본 스탯(HP/MP/ATK/DEF), 성장률, 고유 메커니즘(gimmick), 스킬 리스트
- 스킬 YAML: damage, cost, effects, targeting, condition 필드 포함
- 튜토리얼: step-based 진행 + UI overlay + 조건부 활성화

### Common Patterns
- 스킬 참조: `skill_id` 필드로 skills/ YAML과 연동
- 효과 체이닝: effects 배열로 순차 적용
- 조건 평가: condition 필드로 skill_points, player_level, job 확인
- 팀워크 스킬: source_job + target_job 조합으로 조건부 활성화

## Dependencies
- src/character/character_loader.py - YAML 파싱 및 캐릭터 로드
- src/character/skills/yaml_skill_loader.py - 스킬 YAML 파싱
- src/tutorial/tutorial_manager.py - 튜토리얼 로드 및 진행

<!-- MANUAL: -->
