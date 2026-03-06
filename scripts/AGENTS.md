<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# scripts/

## Purpose
개발 유틸리티 스크립트 63개. 스킬/직업 분석, 데이터 수정, 밸런스 조정, 검증, 게임패드 테스트 등을 자동화한다. 게임 실행에는 포함되지 않는다.

## Key Files
| File | Description |
|------|-------------|
| `analyze_jobs.py` | 직업 스탯 분포 분석 |
| `analyze_skills.py` | 스킬 데이터 분석 |
| `analyze_and_balance_mp_costs.py` | MP 비용 분석 및 밸런스 제안 |
| `balance_analyzer.py` | 종합 밸런스 분석기 |
| `check_skill_ids.py` | 스킬 ID 중복 검사 |
| `check_skill_duplicates.py` | 스킬 중복 정의 검사 |
| `verify_gimmick_fields.py` | 기믹 필드 유효성 검증 |
| `verify_gimmicks.py` | 기믹 동작 검증 |
| `verify_skills.py` | 스킬 YAML 전체 검증 (SE 파일 포함) |
| `validate_jobs.py` | 직업 YAML 유효성 검증 |
| `fix_yaml_skills.py` | YAML 스킬 일괄 수정 |
| `add_sfx_to_skills.py` | 스킬에 SFX 태그 일괄 추가 |
| `generate_skills.py` | 스킬 YAML 자동 생성 |
| `generate_job_redesigns.py` | 직업 리디자인 문서 생성 |
| `archive_unused_yaml_skills.py` | 미사용 스킬 archive/로 이동 |
| `test_gamepad.py` | 게임패드 입력 테스트 |
| `check_gamepad.py` | 게임패드 연결 상태 확인 |
| `bdf_to_png.py` | BDF 폰트를 PNG로 변환 |

## For AI Agents
### Working In This Directory
- 스킬 작업 전: `python scripts/check_skill_ids.py` 로 ID 충돌 확인
- 직업 수정 후: `python scripts/validate_jobs.py` 로 유효성 검증
- 스킬 YAML 수정 후: `python scripts/verify_skills.py` 로 SE 파일 참조 확인
- 밸런스 검토: `python scripts/analyze_and_balance_mp_costs.py`
- 스크립트는 프로젝트 루트에서 실행 (`python scripts/{script}.py`)

## Dependencies
### Internal
- `data/` — 분석/수정 대상 YAML 파일들
- `src/` — 일부 스크립트가 src 모듈 임포트
### External
- PyYAML, 표준 라이브러리

<!-- MANUAL: -->
