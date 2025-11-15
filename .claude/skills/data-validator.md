# Data Validator Skill

게임 데이터 검증 및 무결성 체크

## 목적
- YAML 데이터 검증
- 밸런스 데이터 확인
- 누락된 데이터 탐지
- 데이터 일관성 체크

## 사용법
```
@data-validator check-characters
@data-validator check-skills
@data-validator check-all
```

## 검증 항목

### 1. 캐릭터 데이터
```yaml
# data/characters/*.yaml 검증
- 필수 필드 존재 여부
- 스탯 범위 체크
- 스킬 참조 유효성
- 성장률 밸런스
```

### 2. 스킬 데이터
```yaml
# data/skills/*.yaml 검증
- MP 비용 적절성
- 데미지 배율 밸런스
- 캐스팅 시간 합리성
- 쿨다운 시간
```

### 3. 아이템 데이터
```yaml
# data/items/*.yaml 검증
- 가격 밸런스
- 효과 적절성
- 희귀도 일관성
```

## 출력 예시
```
데이터 검증 리포트
=================
✓ 캐릭터: 28개 - 모두 유효
✗ 스킬: 142개 중 3개 오류
  - power_strike.yaml: MP 비용 누락
  - shadow_blade.yaml: 존재하지 않는 상태 효과 참조
  - heal.yaml: 회복량이 음수

✓ 아이템: 85개 - 모두 유효

권장사항:
- 레벨 1-10 스킬 MP 비용 평균: 15
- 레벨 1-10 스킬 데미지 평균: 2.5x
```
