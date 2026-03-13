<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-03-07 | Updated: 2026-03-07 -->

# docs/balance/

## Purpose
밸런스 분석 및 조정 문서. 데미지 계산, 직업 성능, 인카운터 난이도, 보상 테이블을 분석하고 조정 이력을 기록합니다.

## Key Files
| File | Description |
|------|-------------|
| damage_analysis.md | 데미지 계산 공식 및 스킬별 DPS 분석 |
| job_performance_analysis.md | 직업별 성능 메트릭 (DPS, 생존력, 유틸) |
| encounter_difficulty_analysis.md | 인카운터 난이도 곡선 |
| reward_table_analysis.md | 보상 테이블 (금화, 경험치, 아이템) 균형 |

## Structure Per File
```markdown
# 밸런스 분석명

## 분석 대상
- 버전: 날짜
- 대상 시스템

## 메트릭
### 데이터
- 메트릭 1: 값
- 메트릭 2: 값

### 발견사항
- 문제점 1
- 문제점 2

## 제안 & 조정
- 조정 1: 효과
- 조정 2: 효과

## 검증 결과
조정 후 성과
```

## For AI Agents

### Working In This Directory
- 밸런스 분석은 data/ YAML 수정 전 근거 제공
- src/combat/damage_calculator.py 의 공식 검증
- 직업별 성능 메트릭 추적

### Common Patterns
- 분석: 데이터 수집 -> 메트릭 계산 -> 이상 탐지
- 조정: 스탯/계수 변경 -> 재분석 -> 결과 검증
- 버전 추적: 날짜별 분석 이력 관리

## Dependencies
- scripts/ - 분석 스크립트 (analyze_jobs.py, analyze_skills.py 등)
- data/characters/, data/skills/ - 분석 대상
- src/combat/ - 게임 로직 검증

<!-- MANUAL: -->
