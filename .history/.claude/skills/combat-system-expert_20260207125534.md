# Combat System Expert

ATB+BRV 하이브리드 전투 시스템 전문 스킬

## 전투 흐름 개요
```
전투 시작
  → ATB 게이지 충전 (속도 기반)
  → 게이지 만충 → 행동 선택
    → BRV 공격: 적 BRV를 깎고 자신 BRV 획득
    → HP 공격: 축적된 BRV로 HP 데미지
    → 스킬 사용: 다양한 효과
  → 턴 종료 → 기믹/트레이트/상태이상 처리
  → 적 전멸 또는 아군 전멸 → 전투 종료
```

## 핵심 파일 맵

| 시스템 | 파일 |
|--------|------|
| 전투 전체 흐름 | `src/combat/combat_manager.py` (~280KB) |
| ATB 시스템 | `src/combat/atb_system.py` |
| BRV 시스템 | `src/combat/brave_system.py` |
| 데미지 계산 | `src/combat/damage_calculator.py` |
| 상태이상 | `src/combat/status_effects.py` |
| 캐스팅 | `src/combat/casting_system.py` |
| 보스 기믹 | `src/combat/boss_gimmicks.py` |
| 적 스킬 | `src/combat/enemy_skills.py` |
| 적 AI | `src/ai/enemy_ai.py` |
| 전투 UI | `src/ui/combat_ui.py` |

## ATB 시스템
- 각 캐릭터의 `speed` 스탯에 비례하여 ATB 게이지 충전
- 100% 도달 시 행동 가능
- 행동 후 ATB 초기화 (cast_time에 따라 감소량 다름)
- `src/combat/atb_system.py`에서 관리

## BRV 시스템
- **init_brv**: 전투 시작 시 초기 BRV
- **max_brv**: BRV 상한
- **BRV 공격**: 적 BRV를 깎아 자기 BRV에 추가
- **HP 공격**: 현재 BRV만큼 HP 데미지 → BRV 0으로 리셋
- **BRV Break**: BRV가 0 이하로 떨어지면 Break 상태 → 페널티
- `src/combat/brave_system.py`에서 관리

## 데미지 계산 공식
```
base_damage = stat_base × multiplier
defense_reduction = target_defense × (1 - ignore_defense)
element_modifier = 속성 상성 배율
final_brv_damage = max(0, base_damage - defense_reduction) × element_modifier
critical_bonus = 1.5x (크리티컬 시)
```
`src/combat/damage_calculator.py`에서 상세 구현.

## 전투 디버깅 포인트
1. **데미지 1 (최소값)**: 공격/방어 비율이 극히 낮음, multiplier 누락, stat_base 잘못 지정
2. **스킬 미발동**: MP 부족, 쿨다운 중, 대상 선택 실패, 효과 핸들러 미등록
3. **ATB 이상**: speed 값 오류, 버프/디버프 반영 누락
4. **BRV Break 미처리**: brave_system의 break 판정 로직 확인
5. **상태이상 미적용**: chance 확률 판정, 면역 체크, status_effects 등록 확인
6. **기믹 미트리거**: combat_manager의 이벤트 훅에서 context 전달 확인

## 일반적 디버깅 패턴
```python
# combat_manager.py에서 자주 나오는 패턴
context = {
    "action_type": "skill",
    "skill_id": skill.id,
    "target": target,
    "targets_hit": len(targets),
    "damage": damage_dealt,
    "is_critical": is_crit,
    "hp_percent": target.hp / target.max_hp,
}
self._update_gimmick(character, context)
```
context 키가 누락되면 기믹/트레이트 조건 판정이 실패한다.
