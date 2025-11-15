# Debug Combat Command

전투 관련 문제를 디버깅합니다.

## 사용법
- 최근 전투 로그 확인: `/debug-combat logs`
- ATB 시스템 검증: `/debug-combat atb`
- 데미지 계산 검증: `/debug-combat damage`
- 전체 전투 분석: `/debug-combat full`

## 실행 내용

### 1. 최근 전투 로그 확인
```bash
# 최근 전투 로그 파일 찾기
find logs/ -name "combat_*.log" -type f -mtime -1 | sort -r | head -5

# 로그 내용 분석
tail -100 logs/combat_latest.log
```

주요 확인 사항:
- 전투 시작/종료 이벤트
- 턴 순서 및 ATB 게이지
- 데미지 계산 과정
- 스킬 실행 성공/실패
- 상태 효과 적용

### 2. ATB 시스템 검증
```python
# ATB 게이지 업데이트 검증
python scripts/debug_atb.py

# 확인 항목:
# - ATB 증가 속도
# - 턴 순서 정확성
# - 속도 스탯 반영
# - 액션 후 ATB 감소
```

분석 내용:
```
ATB 디버그 리포트
===================
캐릭터: 전사
- 기본 속도: 12
- ATB 증가율: 15/턴
- 예상 턴 순서: 3번째
- 실제 턴 순서: 3번째 ✓

캐릭터: 마법사
- 기본 속도: 8
- ATB 증가율: 10/턴
- 예상 턴 순서: 4번째
- 실제 턴 순서: 4번째 ✓
```

### 3. 데미지 계산 검증
```python
# 데미지 계산 시뮬레이션
python scripts/debug_damage.py

# 확인 항목:
# - 공격력 계산
# - 방어력 적용
# - 속성 배율
# - 크리티컬 판정
# - BRV/HP 전환
```

예상 vs 실제 데미지:
```
데미지 계산 분석
=================
공격자: 전사 (STR: 18)
스킬: 강타 (배율: 2.5x)
대상: 고블린 (DEF: 10)

계산 과정:
1. 기본 데미지: 18 * 2.5 = 45
2. 방어 적용: 45 - 10 = 35
3. 속성 배율: 35 * 1.0 = 35
4. 최종 BRV 데미지: 35

예상: 35 BRV
실제: 35 BRV ✓
```

### 4. 전체 전투 분석
전투 시뮬레이션 실행:
```python
python scripts/simulate_combat.py --attacker=전사 --defender=고블린 --turns=10
```

분석 리포트:
- 턴별 행동 로그
- ATB 타임라인
- 데미지 누적 그래프
- 상태 효과 타임라인
- 전투 결과 통계

### 5. 일반적인 문제 체크리스트

**전투가 시작되지 않음:**
- [ ] 적 데이터 로드 확인
- [ ] 전투 초기화 로직 확인
- [ ] 이벤트 리스너 등록 확인

**턴 순서가 이상함:**
- [ ] 속도 스탯 계산 확인
- [ ] ATB 게이지 증가 로직 확인
- [ ] 턴 순서 정렬 알고리즘 확인

**데미지가 0 또는 너무 큼:**
- [ ] 스탯 값 범위 확인
- [ ] 데미지 공식 검증
- [ ] 방어 관통/배율 확인
- [ ] 정수 오버플로우 확인

**스킬이 실행 안됨:**
- [ ] MP 소비 확인
- [ ] 스킬 사용 조건 확인
- [ ] 대상 선택 로직 확인
- [ ] 캐스팅 시간 확인

**상태 효과가 적용 안됨:**
- [ ] 확률 계산 확인
- [ ] 면역 체크 확인
- [ ] 상태 효과 등록 확인
- [ ] 지속 시간 카운터 확인

## 로그 파일 위치
- 전투 로그: `logs/combat_*.log`
- ATB 로그: `logs/atb_*.log`
- 데미지 로그: `logs/damage_*.log`
- 에러 로그: `logs/error_*.log`

## 추가 도구
```bash
# 로그 실시간 모니터링
tail -f logs/combat_latest.log

# 특정 패턴 검색
grep "CRITICAL" logs/*.log
grep "ATB" logs/combat_latest.log | tail -20

# 로그 통계
python scripts/analyze_combat_logs.py --date=today
```
