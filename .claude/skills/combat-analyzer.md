# Combat Analyzer Skill

전투 시스템 분석 및 밸런싱을 위한 스킬

## 목적
- 전투 로그 분석
- 데미지 계산 검증
- ATB 타이밍 분석
- 밸런스 이슈 파악

## 사용법
```
@combat-analyzer analyze-logs
@combat-analyzer check-balance
@combat-analyzer verify-damage
```

## 기능

### 1. 로그 분석
```bash
# 최근 전투 로그 분석
grep "전투" logs/combat_*.log | tail -100

# 데미지 통계
grep "데미지" logs/combat_*.log | awk '{sum+=$NF} END {print "평균:", sum/NR}'
```

### 2. 밸런스 체크
- HP/데미지 비율 확인
- 전투 지속 시간 분석
- 승률 통계

### 3. 데미지 검증
- 데미지 공식 계산
- 실제 vs 기대 데미지 비교
- 이상치 탐지

## 출력 예시
```
전투 분석 리포트
===============
전투 횟수: 50
평균 지속 시간: 15턴
평균 데미지: 45
승률: 92%

밸런스 이슈:
- 전사 클래스 데미지 과다 (기대치 대비 150%)
- 마법사 생존율 낮음 (40%)
```
