<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# docs/balance/

## Purpose
게임 수치 밸런스 분석 문서 디렉토리. 데미지, MP 비용 등의 밸런스 데이터를 정리한다.

## Key Files
| File | Description |
|------|-------------|
| `damage_balance.md` | 직업별/스킬별 데미지 밸런스 분석표 |

## For AI Agents
### Working In This Directory
- 밸런스 분석은 `scripts/balance_analyzer.py`, `scripts/analyze_and_balance_mp_costs.py` 로 생성
- 신규 밸런스 리포트 추가 시 이 디렉토리에 MD 파일로 저장
- 데미지 공식 참조: `src/combat/damage_calculator.py`

## Dependencies
### Internal
- `scripts/balance_analyzer.py` — 분석 데이터 생성
- `src/combat/damage_calculator.py` — 데미지 공식

<!-- MANUAL: -->
