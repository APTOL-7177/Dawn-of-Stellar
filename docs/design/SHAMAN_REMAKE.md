# 무당 리메이크안 - MP 과부하 시스템

## 📋 개요

**직업명**: 무당 (Shaman)
**기존 기믹**: 저주 축적 시스템 (Curse System)
**신규 기믹**: MP 과부하 시스템 (MP Overload System)
**컨셉**: "영력을 극한까지 끌어올려 폭발적인 힘을 발휘하는 영매"

### 핵심 변경사항
- ❌ **제거**: 저주 스택 시스템 (너무 평범함)
- ✅ **추가**: MP 과부하 메커니즘 (고위험-고보상)
- ✅ **추가**: 토글형 버프 스킬 (최대 MP 예약)
- ✅ **개선**: 모든 스킬에 "과부하 버전" 선택지

---

## 🎯 설계 철학

### 1. MP 과부하 시스템
스킬 사용 시 **추가 MP를 투입**하여 효과를 극대화할 수 있는 시스템

**메커니즘**:
- 모든 공격/디버프 스킬은 **기본 비용**과 **과부하 비용** 존재
- 과부하 사용 시: **MP 2~3배 소모**, 효과 **50~100%** 증가
- 과부하 게이지 축적: 과부하 스킬 사용 시 게이지 +1 (최대 5)
- 게이지 5 도달 시: **영력 폭주** 자동 발동 → 전체 극대 피해 + 게이지 초기화

### 2. 토글 버프 시스템
특정 버프는 **활성화/비활성화** 가능하며, 활성 중 **최대 MP 예약**

**메커니즘**:
- 토글 버프 활성화 시: 최대 MP의 20~30% **예약** (사용 불가)
- 예약된 MP는 회복되지만 사용할 수 없음
- 토글 해제 시: 예약 해제 + 남은 지속시간 비례 MP 환불
- 동시 활성 토글: 최대 2개

### 3. 영력 소모 패턴
무당의 MP 관리는 **3가지 상태**로 구분

| 상태 | MP 범위 | 효과 |
|------|---------|------|
| **안정** | 50~100% | 평범한 성능 |
| **위험** | 20~49% | 과부하 효과 +30%, 크리티컬 +15% |
| **고갈** | 0~19% | 과부하 불가, 모든 스킬 약화 |

---

## 🔧 기믹 상세 설계

### Gimmick: `mp_overload_system`

```yaml
gimmick:
  type: mp_overload_system
  name: 영력 과부하
  description: |
    [MP 과부하 시스템] 영력을 극한까지 끌어올려 폭발적 힘 발휘!

    과부하 메커니즘:
    - 스킬 사용 시 추가 MP 투입으로 강화
    - 과부하 게이지 축적 (최대 5)
    - 게이지 5 도달 시 '영력 폭주' 자동 발동

    토글 버프:
    - 특정 버프는 ON/OFF 가능
    - 활성 시 최대 MP 20~30% 예약
    - 동시 활성: 최대 2개

    MP 상태별 효과:
    - 안정(50%+): 평범
    - 위험(20~49%): 과부하 +30%, 크리티컬 +15%
    - 고갈(0~19%): 과부하 불가, 스킬 약화

  # 과부하 게이지
  max_overload_gauge: 5
  gauge_effects:
    5:
      auto_trigger: "spirit_rampage"  # 영력 폭주

  # 토글 슬롯
  max_active_toggles: 2
  toggle_skills:
    - spirit_protection    # 영혼의 보호 (최대 MP -25%)
    - ancestral_blessing   # 조상의 축복 (최대 MP -30%)

  # MP 상태 효과
  mp_state_effects:
    danger:  # 20~49%
      threshold: 0.2
      overload_bonus: 0.3
      critical_bonus: 0.15
    depleted:  # 0~19%
      threshold: 0.0
      skill_penalty: 0.5
      overload_disabled: true
```

### 저장/불러오기 대응

**저장 데이터 구조**:
```python
{
    "gimmick_type": "mp_overload_system",
    "overload_gauge": 3,                    # 현재 과부하 게이지
    "active_toggles": [                     # 활성 토글 목록
        {
            "skill_id": "spirit_protection",
            "mp_reservation": 25,           # 예약 MP량
            "remaining_duration": 5         # 남은 지속시간
        }
    ],
    "reserved_max_mp": 25,                  # 총 예약된 최대 MP
    "last_mp_state": "danger"               # 마지막 MP 상태
}
```

**불러오기 시 처리**:
1. `overload_gauge` 복원
2. `active_toggles` 순회하며 토글 재활성화
3. `reserved_max_mp` 적용하여 최대 MP 감소
4. MP 상태 재계산

---

## 💫 스킬 목록 (10개)

### 1. 영혼의 화살 (Spirit Arrow) - 기본 공격
**타입**: BRV 공격
**과부하**: 가능

```yaml
skill_id: shaman_spirit_arrow
name: 영혼의 화살
description: 영혼의 힘으로 공격. 과부하 시 피해 2배.
effects:
  - type: damage_brv
    multiplier: 1.4
    stat: magic
costs:
  - type: mp
    value: 0
overload:
  enabled: true
  costs:
    - type: mp
      value: 8
  effects:
    - type: damage_brv
      multiplier: 2.8  # 2배
      stat: magic
    - type: gimmick
      operation: ADD
      field: overload_gauge
      value: 1
```

### 2. 영력 폭발 (Spirit Burst) - 기본 HP 공격
**타입**: HP 공격
**과부하**: 가능

```yaml
skill_id: shaman_spirit_burst
name: 영력 폭발
description: 영력을 폭발시켜 HP 피해. 과부하 시 전체 공격.
effects:
  - type: damage_hp
    multiplier: 1.2
    stat: magic
costs:
  - type: mp
    value: 0
overload:
  enabled: true
  costs:
    - type: mp
      value: 15
  effects:
    - type: damage_hp
      multiplier: 2.5
      stat: magic
    - type: gimmick
      operation: ADD
      field: overload_gauge
      value: 1
  target_type: all_enemies
  is_aoe: true
```

### 3. 역병 소환 (Plague) - 광역 DoT
**타입**: BRV + 독
**과부화**: 가능

```yaml
skill_id: shaman_plague
name: 역병 소환
description: 역병을 퍼뜨린다. 과부하 시 독 2배 + 저주 추가.
effects:
  - type: damage_brv
    multiplier: 1.5
    stat: magic
  - type: status
    status: poison
    duration: 4
    damage_multiplier: 0.12
    damage_stat: magic
costs:
  - type: mp
    value: 10
target_type: all_enemies
is_aoe: true
overload:
  enabled: true
  costs:
    - type: mp
      value: 25  # 2.5배 소모
  effects:
    - type: damage_brv
      multiplier: 2.2
      stat: magic
    - type: status
      status: poison
      duration: 6
      damage_multiplier: 0.24  # 2배
      damage_stat: magic
    - type: status
      status: curse
      duration: 4
      value: 0.15  # 공/방 -15%
    - type: gimmick
      operation: ADD
      field: overload_gauge
      value: 1
```

### 4. 영혼의 보호 (Spirit Protection) - 토글 버프
**타입**: 토글형 방어 버프
**과부하**: 불가

```yaml
skill_id: shaman_spirit_protection
name: 영혼의 보호
description: |
  [토글] 영혼의 보호막. 활성 시 방어 +30%, 최대 MP -25%.
  재사용 시 해제.
effects:
  - type: toggle_buff
    buff: defense_up
    value: 0.30
    mp_reservation: 25  # 최대 MP 25% 예약
    duration: 999  # 토글 해제 시까지
costs:
  - type: mp
    value: 15  # 활성화 초기 비용
target_type: self
metadata:
  toggle: true
  max_mp_penalty: 0.25
  toggle_slot: 1
```

### 5. 조상의 축복 (Ancestral Blessing) - 토글 버프
**타입**: 토글형 마법 버프
**과부하**: 불가

```yaml
skill_id: shaman_ancestral_blessing
name: 조상의 축복
description: |
  [토글] 조상의 힘. 활성 시 마공 +40%, 속도 +20%, 최대 MP -30%.
  재사용 시 해제.
effects:
  - type: toggle_buff
    buff: magic_up
    value: 0.40
    mp_reservation: 30
    duration: 999
  - type: toggle_buff
    buff: speed_up
    value: 0.20
    mp_reservation: 0  # MP는 한 번만 차감
    duration: 999
costs:
  - type: mp
    value: 20
target_type: self
metadata:
  toggle: true
  max_mp_penalty: 0.30
  toggle_slot: 2
```

### 6. 영혼 흡수 (Soul Drain) - 흡혈
**타입**: BRV+HP + 흡혈
**과부하**: 가능

```yaml
skill_id: shaman_soul_drain
name: 영혼 흡수
description: 영혼을 빨아들인다. 과부하 시 흡혈량 2배 + MP 회복.
effects:
  - type: damage_brv_hp
    multiplier: 2.0
    stat: magic
  - type: lifesteal
    percentage: 0.30
costs:
  - type: mp
    value: 12
overload:
  enabled: true
  costs:
    - type: mp
      value: 30
  effects:
    - type: damage_brv_hp
      multiplier: 3.2
      stat: magic
    - type: lifesteal
      percentage: 0.60
    - type: heal_mp
      value: 15  # MP 15 회복
    - type: gimmick
      operation: ADD
      field: overload_gauge
      value: 1
```

### 7. 어둠의 저주 (Dark Curse) - 강력 디버프
**타입**: BRV+HP + 디버프
**과부하**: 가능

```yaml
skill_id: shaman_dark_curse
name: 어둠의 저주
description: 강력한 저주. 과부하 시 디버프 3배 + 전체 공격.
effects:
  - type: damage_brv_hp
    multiplier: 2.2
    stat: magic
  - type: buff
    buff: attack_down
    value: 0.20
    duration: 3
  - type: buff
    buff: defense_down
    value: 0.20
    duration: 3
costs:
  - type: mp
    value: 14
overload:
  enabled: true
  costs:
    - type: mp
      value: 35
  effects:
    - type: damage_brv_hp
      multiplier: 3.5
      stat: magic
    - type: buff
      buff: attack_down
      value: 0.60  # 3배
      duration: 5
    - type: buff
      buff: defense_down
      value: 0.60
      duration: 5
    - type: buff
      buff: speed_down
      value: 0.40
      duration: 5
    - type: gimmick
      operation: ADD
      field: overload_gauge
      value: 1
  target_type: all_enemies
  is_aoe: true
```

### 8. 영력 충전 (Spirit Charge) - MP 회복
**타입**: 자가 버프 + MP 회복
**과부하**: 불가

```yaml
skill_id: shaman_spirit_charge
name: 영력 충전
description: 영력을 모은다. MP 30% 회복 + 마공 버프.
effects:
  - type: heal_mp
    percentage: 0.30
  - type: buff
    buff: magic_up
    value: 0.25
    duration: 3
costs:
  - type: mp
    value: 0  # 비용 없음
target_type: self
metadata:
  mp_recovery: true
  cooldown: 3  # 3턴 쿨다운
```

### 9. 악몽 투영 (Nightmare Projection) - CC
**타입**: BRV+HP + 수면
**과부하**: 가능

```yaml
skill_id: shaman_nightmare
name: 악몽 투영
description: 악몽을 심는다. 과부하 시 수면 3턴 + 전체 공격.
effects:
  - type: damage_brv_hp
    multiplier: 1.8
    stat: magic
  - type: status
    status: sleep
    duration: 2
    value: 1.0
costs:
  - type: mp
    value: 12
overload:
  enabled: true
  costs:
    - type: mp
      value: 28
  effects:
    - type: damage_brv_hp
      multiplier: 2.8
      stat: magic
    - type: status
      status: sleep
      duration: 3
      value: 1.0
    - type: gimmick
      operation: ADD
      field: overload_gauge
      value: 1
  target_type: all_enemies
  is_aoe: true
```

### 10. 궁극기: 영력 폭주 (Spirit Rampage)
**타입**: 궁극기
**과부하**: 불가 (이미 최대 효과)
**특징**: 수동/자동 발동 시 효과 차이

```yaml
skill_id: shaman_ultimate
name: 영력 폭주
description: |
  모든 영력 해방! 전체 광역 피해 + 디버프 + 토글 해제.

  [수동 발동] MP 40, 강력한 효과
  [자동 발동] 게이지 5 시, MP 10, 약화된 효과

# 수동 발동 (직접 사용)
effects:
  - type: damage_brv
    multiplier: 2.8
    stat: magic
  - type: damage_hp
    multiplier: 3.0
    stat: magic
  - type: status
    status: poison
    duration: 4
    damage_multiplier: 0.15
    damage_stat: magic
  - type: buff
    buff: attack_down
    value: 0.30
    duration: 4
  - type: buff
    buff: defense_down
    value: 0.25
    duration: 4
  - type: buff
    buff: magic_defense_down
    value: 0.20
    duration: 4
  - type: gimmick
    operation: SET
    field: overload_gauge
    value: 0
  - type: toggle_release_all
costs:
  - type: mp
    value: 40

# 자동 발동 버전 (게이지 5 시)
auto_trigger:
  trigger_condition:
    overload_gauge: 5
  effects:
    - type: damage_brv
      multiplier: 1.8  # 2.8 → 1.8 (약 35% 감소)
      stat: magic
    - type: damage_hp
      multiplier: 2.0  # 3.0 → 2.0 (약 33% 감소)
      stat: magic
    - type: status
      status: poison
      duration: 3  # 4턴 → 3턴
      damage_multiplier: 0.10  # 0.15 → 0.10
      damage_stat: magic
    - type: buff
      buff: attack_down
      value: 0.20  # 0.30 → 0.20
      duration: 3  # 4턴 → 3턴
    - type: buff
      buff: defense_down
      value: 0.15  # 0.25 → 0.15
      duration: 3
    - type: gimmick
      operation: SET
      field: overload_gauge
      value: 0
    - type: toggle_release_all
  costs:
    - type: mp
      value: 10  # 40 → 10 (75% 감소)

is_ultimate: true
cooldown: 15
target_type: all_enemies
is_aoe: true
metadata:
  dual_mode: true
  auto_trigger_at_gauge_5: true
  auto_reduced_version: true
```

### 팀워크: 조상령 강림 (Ancestral Wrath)

```yaml
skill_id: shaman_teamwork
name: 조상령 강림
description: 조상령이 강림하여 적 전체 공격 + 과부하 게이지 MAX.
effects:
  - type: damage_brv
    multiplier: 2.5
    stat: magic
  - type: damage_hp
    multiplier: 2.0
    stat: magic
  - type: gimmick
    operation: SET
    field: overload_gauge
    value: 5
  - type: buff
    buff: defense_down
    value: 0.30
    duration: 4
costs:
  - type: teamwork_gauge
    value: 175
target_type: all_enemies
is_aoe: true
metadata:
  teamwork: true
  chain: true
```

---

## 🎨 캐릭터 데이터 (shaman.yaml)

```yaml
class_name: 무당
description: 영력을 극한까지 끌어올려 폭발적인 힘을 발휘하는 영매
slogan: "조상의 영력이 한계를 넘어선다"
archetype: MP 과부하 / 고위험 고보상

base_stats:
  hp: 110
  mp: 95  # MP 특화 (높은 기본 MP)
  init_brv: 100
  speed: 62
  physical_attack: 45
  physical_defense: 40
  magic_attack: 92  # 마법 공격 특화
  magic_defense: 75
  max_brv: 420

stat_growth:
  hp: 8
  mp: 8  # MP 성장 높음
  init_brv: 20
  strength: 2.0
  defense: 2.0
  magic: 5.0  # 마법 성장 높음
  spirit: 4.5
  speed: 3.2
  luck: 4.5
  accuracy: 2.0
  evasion: 1.8
  max_brv: 84

traits:
  - id: spirit_vision
    name: 영혼의 시야
    description: 시야 거리 +50%, 함정/보물 탐지 확률 +100%
    type: passive
    effects:
      vision_range: 1.5
      treasure_find: 1.2
      trap_detection: 1.0
      critical_resistance: 0.2

  - id: overload_master
    name: 과부하의 달인
    description: 과부하 스킬 효과 +20%, MP 소모 -10%
    type: passive
    effects:
      overload_bonus: 0.2
      overload_mp_reduction: 0.1

  - id: desperate_power
    name: 위험한 힘
    description: MP 20~49% 시 과부하 효과 +30%, 크리티컬 +15%
    type: conditional
    conditions:
      mp_percentage_min: 0.2
      mp_percentage_max: 0.49
    effects:
      overload_bonus: 0.3
      critical_rate: 0.15

  - id: spirit_resonance
    name: 영력 공명
    description: 과부하 게이지 3+ 시 마공 +40%, 속도 +25%
    type: conditional
    conditions:
      overload_gauge_min: 3
    effects:
      magic_bonus: 0.4
      speed_bonus: 0.25

  - id: toggle_efficiency
    name: 토글 효율
    description: 토글 버프 활성 시 MP 회복량 +50%
    type: conditional
    conditions:
      has_active_toggle: true
    effects:
      mp_regen_bonus: 0.5

gimmick:
  type: mp_overload_system
  name: 영력 과부하
  description: |
    [MP 과부하 시스템] 영력을 극한까지 끌어올려 폭발적 힘 발휘!

    과부하 메커니즘:
    - 스킬 사용 시 추가 MP 투입으로 강화 (2~3배 소모, 50~100% 효과)
    - 과부하 게이지 축적 (최대 5)
    - 게이지 5 도달 시 '영력 폭주' 자동 발동

    토글 버프:
    - 특정 버프는 ON/OFF 가능
    - 활성 시 최대 MP 20~30% 예약
    - 동시 활성: 최대 2개

    MP 상태별 효과:
    - 안정(50%+): 평범
    - 위험(20~49%): 과부하 +30%, 크리티컬 +15%
    - 고갈(0~19%): 과부하 불가, 스킬 약화

  max_overload_gauge: 5
  gauge_effects:
    5:
      auto_trigger: spirit_rampage

  max_active_toggles: 2
  toggle_skills:
    - shaman_spirit_protection
    - shaman_ancestral_blessing

  mp_state_effects:
    danger:
      threshold: 0.2
      max_threshold: 0.49
      overload_bonus: 0.3
      critical_bonus: 0.15
    depleted:
      threshold: 0.0
      max_threshold: 0.19
      skill_penalty: 0.5
      overload_disabled: true

skills:
  - shaman_spirit_arrow
  - shaman_spirit_burst
  - shaman_plague
  - shaman_spirit_protection
  - shaman_ancestral_blessing
  - shaman_soul_drain
  - shaman_dark_curse
  - shaman_spirit_charge
  - shaman_nightmare
  - shaman_ultimate
  - shaman_teamwork

bonuses:
  mp_regen: 1.3  # MP 회복 30% 증가
  magic_damage: 1.15  # 마법 피해 15% 증가
  vision_range: 1.5  # 시야 거리 +50%
  treasure_find: 1.2  # 보물 발견 +20%
  trap_detection: 1.0  # 함정 탐지 +100%
```

---

## 🔨 구현 체크리스트

### 1. YAML 스킬 로더 확장
- [ ] `overload` 필드 파싱 지원
- [ ] `toggle_buff` 이펙트 타입 추가
- [ ] `mp_reservation` 처리
- [ ] `toggle_release_all` 이펙트 추가

### 2. GimmickUpdater 확장
- [ ] `mp_overload_system` 기믹 추가
- [ ] `on_turn_start()`: MP 상태 체크 및 효과 적용
- [ ] `on_skill_use()`: 과부하 게이지 증가, 토글 처리
- [ ] `on_overload_gauge_max()`: 자동 궁극기 발동
- [ ] 토글 버프 활성화/해제 로직

### 3. Character 클래스 확장
- [ ] `overload_gauge` 필드 추가 (0~5)
- [ ] `active_toggles` 리스트 추가
- [ ] `reserved_max_mp` 필드 추가
- [ ] `get_effective_max_mp()` 메서드 (예약 MP 제외)
- [ ] `toggle_skill()` 메서드 (토글 활성화/해제)

### 4. Skill 클래스 확장
- [ ] `overload_version` 필드 추가
- [ ] `is_toggle` 플래그 추가
- [ ] `mp_reservation` 필드 추가
- [ ] 과부하 스킬 실행 로직
- [ ] `auto_trigger` 필드 추가 (궁극기 자동 발동 버전)
- [ ] 궁극기 이중 발동 시스템 (수동 MP 40/자동 MP 10)

### 5. 이펙트 시스템 확장
- [ ] `ToggleBuffEffect` 클래스 생성
  - `mp_reservation` 처리
  - 토글 활성화/해제
  - 최대 MP 감소/복구
- [ ] `ToggleReleaseAllEffect` 클래스 생성
  - 모든 활성 토글 해제
  - MP 예약 전체 해제

### 6. UI 표시
- [ ] 과부하 게이지 바 (0/5)
- [ ] 활성 토글 아이콘
- [ ] 예약된 MP 표시 (예: `65/100 (-35)`)
- [ ] MP 상태 색상 표시 (안정=파랑, 위험=노랑, 고갈=빨강)

### 7. 저장/불러오기
- [ ] `save_system.py`: 기믹 상태 저장
  - `overload_gauge`
  - `active_toggles` (스킬 ID, 예약 MP, 남은 시간)
  - `reserved_max_mp`
- [ ] `save_system.py`: 기믹 상태 불러오기
  - 과부하 게이지 복원
  - 토글 재활성화
  - 최대 MP 감소 적용

### 8. 테스트
- [ ] `test_shaman_overload.py`: 과부하 스킬 테스트
- [ ] `test_shaman_toggle.py`: 토글 버프 테스트
- [ ] `test_shaman_save_load.py`: 저장/불러오기 테스트
- [ ] `test_shaman_mp_states.py`: MP 상태 효과 테스트
- [ ] `test_shaman_ultimate_dual.py`: 궁극기 수동/자동 발동 테스트

---

## 📝 구현 우선순위

### Phase 1: 핵심 메커니즘 (1일)
1. Character 클래스 확장 (과부하 게이지, 토글 필드)
2. GimmickUpdater에 `mp_overload_system` 추가
3. 과부하 게이지 증가/소비 로직

### Phase 2: 스킬 시스템 (1일)
1. YAML 로더에 `overload` 파싱 추가
2. 과부하 스킬 실행 로직
3. `ToggleBuffEffect` 구현
4. 토글 활성화/해제 로직

### Phase 3: YAML 데이터 (0.5일)
1. `data/characters/shaman.yaml` 업데이트
2. `data/skills/shaman_*.yaml` 10개 스킬 생성
3. 메타데이터 검증

### Phase 4: 저장/불러오기 (0.5일)
1. 저장 로직 추가
2. 불러오기 로직 추가
3. 호환성 테스트

### Phase 5: UI & 테스트 (1일)
1. 게이지/토글 UI 표시
2. 테스트 작성 및 실행
3. 밸런스 조정

**총 예상 시간**: 4일

---

## 🎮 플레이 패턴 예시

### 패턴 1: 안정적 운영
1. 턴 1: `영혼의 화살` (MP 0)
2. 턴 2: `영력 충전` (MP 30% 회복)
3. 턴 3: `역병 소환 [과부하]` (MP 25, 게이지 +1)
4. 턴 4: `영혼의 보호 [토글 ON]` (최대 MP -25%)
5. 턴 5~: 과부하 스킬 위주로 게이지 축적

### 패턴 2: 자동 발동 활용
1. 턴 1: `조상의 축복 [토글 ON]` (최대 MP -30%, 마공 +40%)
2. 턴 2: `어둠의 저주 [과부하]` (MP 35, 게이지 +1)
3. 턴 3: `영혼 흡수 [과부하]` (MP 30, 게이지 +1, 흡혈 60%)
4. 턴 4: `악몽 투영 [과부하]` (MP 28, 게이지 +1)
5. 턴 5: `역병 소환 [과부하]` (MP 25, 게이지 +1)
6. 턴 6: 게이지 5 도달 → **영력 폭주 자동 발동!** (MP 10만 소모)
7. 자동 발동으로 MP를 절약하며 꾸준히 딜 유지

### 패턴 3: 수동 궁극기 폭딜
1. 턴 1~4: 과부하 스킬로 게이지 축적 (게이지 4)
2. 턴 5: MP를 40 이상 확보
3. 턴 6: **영력 폭주 수동 발동** (MP 40, 강력한 효과)
4. 수동 발동으로 최대 화력 (BRV 2.8, HP 3.0)
5. 게이지가 5 미만일 때 사용하여 자동 발동 방지

### 패턴 4: 위험 구간 활용
1. MP를 20~49%로 유지
2. 위험 구간 보너스 (과부하 +30%, 크리티컬 +15%)
3. 과부하 스킬 연타로 극대 피해
4. `영력 충전`으로 MP 회복 후 반복
5. 게이지 5 도달 시 자동 발동 (MP 10만 소모)

---

## 🔧 밸런스 고려사항

### 강점
- **점진적 화력 증가**: 과부하 스킬로 50~100% 효과 증가
- **유연한 운영**: 토글 버프로 상황 대응
- **위험 보상**: 낮은 MP(20~49%)에서 보너스 효과
- **이중 궁극기 시스템**: 수동(강력)/자동(MP 절약) 선택 가능
  - 자동: MP 10만 소모, 약한 효과
  - 수동: MP 40 소모, 강한 효과
- **MP 효율**: 자동 발동 시 MP 10만 소모로 장기전 유리
- **영혼의 시야**: 탐험/보물 발견에 유리

### 약점
- **MP 의존도 높음**: MP 고갈 시 전투력 급감
- **고갈 리스크**: 과부하 남발 시 MP 고갈 위험
- **토글 제약**: 최대 MP 감소로 운영 어려움
- **자동 발동 약함**: 자동 발동 시 효과 35~40% 감소
- **게이지 관리 어려움**:
  - 게이지 5 도달 시 무조건 자동 발동
  - 수동 발동 타이밍 놓치면 약한 버전만 사용
  - 게이지 4에서 멈춰야 수동 발동 가능

### 밸런스 조정 이력
- ✅ **과부하 효과**: 150~250% → **50~100%** (약화)
- ✅ **궁극기 약화**: BRV 3.5→2.8, HP 4.0→3.0, 디버프 감소
- ✅ **궁극기 이원화**: 수동(MP 40)/자동(MP 10) 발동 분리
  - 수동: BRV 2.8, HP 3.0, 디버프 -20~30%, 4턴
  - 자동: BRV 1.8, HP 2.0, 디버프 -15~20%, 3턴 (대폭 약화)
- ✅ **특성 조정**: 폭주 촉발 제거 (너무 강력함)

### 추가 조정 고려사항
1. **과부하 MP 소모 미세 조정**: 플레이테스트 후 결정
2. **토글 MP 예약 증가**: 최대 MP -40%로 상향 검토
3. **과부하 게이지 최대값 증가**: 5 → 6~7로 조정 검토
4. **위험 구간 축소**: 20~49% → 15~40% 검토

---

## 📚 참고 자료

### 유사 시스템
- **Final Fantasy XIV**: 흑마도사 (Astral Fire/Umbral Ice)
- **Granblue Fantasy**: 과부하 스킬 (Overload Skills)
- **Fate/Grand Order**: 토글형 스킬 (항시 발동 스킬)

### 파일 위치
- 캐릭터: `data/characters/shaman.yaml`
- 스킬 (개별): `data/skills/shaman_*.yaml` (10개)
- 기믹: `src/character/gimmick_updater.py`
- 로더: `src/character/skills/yaml_skill_loader.py`
- 저장: `src/persistence/save_system.py`

---

**작성일**: 2025-12-04
**작성자**: Claude Code
**버전**: 1.2 (궁극기 이원화)
**상태**: 설계 완료, 구현 대기

**변경 이력**:
- v1.2 (2025-12-04): 궁극기 수동/자동 발동 분리 (수동 MP 40/자동 MP 10)
- v1.1 (2025-12-04): 과부하 효과 약화 (50~100%), 궁극기 약화, 특성 5개로 조정
- v1.0 (2025-12-04): 초안 작성

---

## ✅ 다음 단계

1. **검토**: 리메이크안 검토 및 피드백
2. **승인**: 사용자 승인 후 구현 시작
3. **구현**: Phase 1부터 순차 진행
4. **테스트**: 각 Phase별 테스트 진행
5. **배포**: 최종 테스트 후 메인 브랜치 머지

**질문/피드백 환영합니다!** 🎮
