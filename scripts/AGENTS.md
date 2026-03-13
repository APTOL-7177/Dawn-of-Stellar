<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# scripts/ (Root-level Python utility scripts)

## Purpose
게임 개발 및 유지보수 유틸리티 스크립트 모음입니다. 데이터 분석, 검증, 밸런싱, 생성, 테스트 헬퍼 등 약 17개 스크립트를 포함합니다.

## Key Files by Category

### 분석 및 검증 (Analysis & Validation)
| File | Description |
|------|-------------|
| analyze_jobs.py | 직업 통계 분석 (스탯, 스킬 분포) |
| analyze_skills.py | 스킬 데이터 분석 및 검증 |
| check_teamwork.py | 팀워크 스킬 정의 검증 |
| verify_skills.py | 모든 스킬 YAML 구문 검증 |
| validate_jobs.py | 직업 설정 검증 |
| check_skill_duplicates.py | 중복 스킬 감지 |
| show_job_profiles.py | 직업 프로필 출력 |
| find_item_issues.py | 아이템 데이터 문제 감지 |

### 밸런싱 (Balancing)
| File | Description |
|------|-------------|
| balance_analyzer.py | 게임 밸런스 분석 및 리포트 |
| balance_mp_costs.py | MP 비용 재조정 |
| rebalance_stat_growth.py | 직업별 스탯 성장 재조정 |
| increase_ultimate_mp.py | 궁극기 MP 비용 증가 |
| reduce_mp_costs.py | MP 비용 감소 |
| adjust_enemy_hp_skills.py | 적 HP/스킬 조정 |

### 생성 및 유지보수 (Generation & Maintenance)
| File | Description |
|------|-------------|
| add_descriptions.py | 스킬/아이템 설명 추가 |
| cleanup_items.py | 미사용 아이템 정리 |
| fix_syntax_errors.py | YAML 구문 오류 수정 |
| fix_remaining_teamwork.py | 팀워크 스킬 결함 수정 |
| implement_teamwork_effects.py | 팀워크 이펙트 자동 생성 |

### 버전 관리 (Versioning)
| File | Description |
|------|-------------|
| bump_version.py | 버전 번호 업데이트 |

### 기타 유틸리티 (Other Utilities)
| File | Description |
|------|-------------|
| bot_client.py | 게임 상태 봇 클라이언트 |
| convert_logo_to_ico.py | 로고 이미지 → ICO 변환 |
| launcher.py | 게임 실행 런처 (GUI) |
| launcher_cli.py | 게임 실행 런처 (CLI) |
| llm_macro.py | LLM 기반 매크로 실행 |

## Subdirectories
없음

## For AI Agents

### Working In This Directory
- 스크립트는 독립적으로 실행 가능 (서로 의존성 최소화)
- data/, src/ 디렉토리 참조하여 게임 데이터 접근
- 데이터 수정 스크립트는 백업 생성 후 원본 수정

### Common Patterns
- YAML 파일 읽기: src/ 내 로더 클래스 재사용
- 출력: 콘솔 리포트 또는 JSON/CSV 파일 생성
- 에러 처리: 파일 없음, YAML 파싱 오류 예외 처리
- 스크립트 메인 진입: `if __name__ == "__main__":`

## Dependencies
- src/character/job_stats_loader.py (직업 데이터 로드)
- src/character/character.py (캐릭터 생성)
- src/character/skills/skill.py (스킬 정의)
- data/characters/, data/skills/ (게임 데이터)
- requirements.txt (패키지 의존성)

<!-- MANUAL: -->
