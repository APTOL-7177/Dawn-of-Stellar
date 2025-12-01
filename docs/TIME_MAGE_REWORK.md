# 시간술사 리워크: 평행시간선 소환사 (Parallel Summoner)

> **버전**: 1.0  
> **작성일**: 2025-11-30  
> **역할**: 마법 딜러 / 유틸리티 서포터

---

## 1. 컨셉 개요

### 핵심 판타지
> *"나는 수천 갈래의 가능성 중 하나일 뿐. 하지만 모든 가능성의 '나'가 함께 싸운다면?"*

매 순간 우리는 선택을 하고, 선택하지 않은 길은 사라진다. 하지만 시간술사는 **"선택하지 않은 가능성"**을 버리지 않고 저장해뒀다가, 필요할 때 현실로 불러온다.

### 플레이 스타일
- **셋업형 딜러**: 2~3턴 동안 가능성을 축적 → 한 번에 폭발
- **유연한 대응**: 저장된 가능성으로 상황에 맞는 스킬 선택
- **팀 연계**: 아군 스킬을 복제하여 시너지 극대화

---

## 2. 기본 스탯 (밸런스 비교)

### 스탯 비교표

| 스탯 | 시간술사 | 아크메이지 | 정령술사 | 바드 | 비고 |
|------|----------|------------|----------|------|------|
| **HP** | 115 | 121 | 107 | 112 | 중간 (서포터 겸업) |
| **MP** | 98 | 89 | 94 | 78 | 높음 (가능성 소환용) |
| **init_brv** | 105 | 102 | 108 | 110 | 중간 |
| **speed** | 62 | 58 | 59 | 72 | 중상 (시간 조작자) |
| **p_atk** | 42 | 43 | 49 | 45 | 낮음 |
| **p_def** | 45 | 33 | 42 | 40 | 중간 |
| **m_atk** | 82 | 78 | 85 | 70 | 높음 (메인 딜러) |
| **m_def** | 65 | 67 | 69 | 62 | 중간 |
| **max_brv** | 420 | 430 | 438 | 450 | 중간 |

### 스탯 성장률

```yaml
stat_growth:
  hp: 8.5
  mp: 7.5
  init_brv: 21.0
  strength: 2.2
  defense: 2.0
  magic: 5.2
  spirit: 4.2
  speed: 4.5
  luck: 4.0
  accuracy: 2.0
  evasion: 2.5
  max_brv: 84.0
```

---

## 3. 기믹: 가능성 슬롯 시스템 (Possibility Slots)

### 시스템 개요

```
┌──────────────────────────────────────────────────────────────┐
│                    【 가능성 슬롯 】                          │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐             │
│  │ 슬롯 1 │  │ 슬롯 2 │  │ 슬롯 3 │  │ 슬롯 4 │             │
│  │        │  │        │  │        │  │        │             │
│  │ [빈칸] │  │ [빈칸] │  │ [빈칸] │  │ [빈칸] │             │
│  └────────┘  └────────┘  └────────┘  └────────┘             │
│                                                              │
│  보유 가능성: 0/4    │    평행 공명: 비활성                   │
└──────────────────────────────────────────────────────────────┘
```

### 기믹 상세

```yaml
gimmick:
  type: possibility_slots
  name: 가능성 슬롯
  description: |
    [평행시간선 시스템] 선택하지 않은 가능성을 저장하라!
    
    ◆ 기본 규칙
    - 스킬 사용 시 70% 확률로 "대안 가능성" 저장
    - 최대 4개 슬롯 보유
    - 저장된 가능성은 원본의 85% 위력
    
    ◆ 가능성 소환
    - 슬롯의 가능성을 즉시 실현
    - MP 소모 없이 스킬 발동!
    
    ◆ 평행 공명 (슬롯 보유 보너스)
    - 1개: 마법 공격력 +8%
    - 2개: 마법 공격력 +16%, 피해 감소 5%
    - 3개: 마법 공격력 +24%, 피해 감소 10%
    - 4개: 마법 공격력 +32%, 피해 감소 15%, ATB +15%
    
  max_slots: 4
  base_generation_chance: 0.70  # 70% 기본 생성 확률
  possibility_power_ratio: 0.85  # 가능성 위력 85%
  
  resonance_bonuses:
    1:
      magic_attack_bonus: 0.08
    2:
      magic_attack_bonus: 0.16
      damage_reduction: 0.05
    3:
      magic_attack_bonus: 0.24
      damage_reduction: 0.10
    4:
      magic_attack_bonus: 0.32
      damage_reduction: 0.15
      atb_bonus: 0.15
```

### 가능성 생성 규칙

| 실제 사용 스킬 | 저장되는 가능성 | 카테고리 |
|----------------|-----------------|----------|
| 타임 볼트 | 타임 쇼크 | 공격 ↔ 공격 |
| 타임 쇼크 | 타임 볼트 | 공격 ↔ 공격 |
| 헤이스트 | 슬로우 | 버프 ↔ 디버프 |
| 슬로우 | 헤이스트 | 디버프 ↔ 버프 |
| 리와인드 | 역설 방어 | 회복 ↔ 방어 |
| 역설 방어 | 리와인드 | 방어 ↔ 회복 |
| 시간 정지 | 시간 가속 | CC ↔ 버프 |

---

## 4. 특성 (Traits) - 5개

### 특성 1: 분기점 창조자 (Branch Creator)

```yaml
- id: branch_creator
  name: 분기점 창조자
  description: |
    스킬 사용 시 "대안 가능성" 생성 확률 +15% (총 85%)
    행운 4당 추가 +1% (최대 95%)
  type: passive
  unlock_level: 1
  effects:
    generation_chance_bonus: 0.15
    luck_scaling: 0.0025  # 행운 4당 1%
    max_generation_chance: 0.95
```

### 특성 2: 평행 공명 (Parallel Resonance)

```yaml
- id: parallel_resonance
  name: 평행 공명
  description: |
    저장된 가능성 개수에 비례해 강해진다.
    - 가능성 1개당: 마법 공격력 +8%, 받는 피해 -5%
    - 슬롯 4개 모두 찼을 때: ATB 충전 속도 +15%
  type: passive
  unlock_level: 5
  effects:
    per_slot_magic_bonus: 0.08
    per_slot_damage_reduction: 0.05
    full_slot_atb_bonus: 0.15
```

### 특성 3: 시간선 간섭 (Timeline Interference)

```yaml
- id: timeline_interference
  name: 시간선 간섭
  description: |
    가능성을 소환할 때 30% 확률로 해당 가능성이 소멸하지 않음.
    같은 가능성은 최대 2회까지 재사용 가능.
  type: trigger
  unlock_level: 10
  effects:
    preserve_chance: 0.30
    max_reuse: 2
```

### 특성 4: 수렴하는 운명 (Converging Fates)

```yaml
- id: converging_fates
  name: 수렴하는 운명
  description: |
    "시간 폭풍" 스킬로 3개 이상의 가능성을 동시에 해방할 때:
    - 총 피해량 +40%
    - 대상에게 "시간 고정" 디버프 부여 (1턴 ATB 정지)
  type: conditional
  unlock_level: 15
  conditions:
    skill_used: time_storm
    possibilities_released_min: 3
  effects:
    damage_bonus: 0.40
    apply_time_lock: true
    time_lock_duration: 1
```

### 특성 5: 무한 분기 (Infinite Branches)

```yaml
- id: infinite_branches
  name: 무한 분기
  description: |
    - 전투 시작 시 랜덤 가능성 1개 자동 생성
    - HP 30% 이하일 때 가능성 생성 확률 100%
    - 가능성 소환 시 10% 확률로 같은 스킬 한 번 더 발동
  type: passive
  unlock_level: 20
  effects:
    start_with_possibility: 1
    low_hp_threshold: 0.30
    low_hp_generation_chance: 1.0
    double_cast_chance: 0.10
```

---

## 5. 기본 공격

### BRV 공격: 시간 왜곡

```yaml
brv_attack:
  name: 시간 왜곡
  damage_type: magic
  stat_base: magic
  base_multiplier: 1.15  # 마법 딜러 평균
  can_critical: true
  effects:
    - type: generate_possibility
      chance: 0.50  # 기본 공격은 50% 확률
      skill_pool: [time_bolt, slow]
    - type: debuff
      target: enemy
      stat: speed
      value: 0.10  # 10% 슬로우
      duration: 1
      chance: 0.25
  description: |
    시간을 왜곡하여 적을 공격.
    25% 확률로 적 속도 -10% (1턴).
    50% 확률로 가능성 생성.
```

### HP 공격: 시간 붕괴

```yaml
hp_attack:
  name: 시간 붕괴
  damage_type: magic
  stat_base: magic
  base_multiplier: 1.0
  can_critical: false
  effects:
    - type: bonus_per_slot
      value: 0.08  # 슬롯당 +8% 피해
    - type: generate_possibility
      chance: 0.50
      skill_pool: [time_shock, haste]
  description: |
    축적된 시간의 힘을 폭발.
    보유 가능성 1개당 피해량 +8%.
    50% 확률로 가능성 생성.
```

---

## 6. 스킬 세트 (17개)

### 기본 공격 스킬

| 스킬 ID | 이름 | MP | 타입 | 효과 |
|---------|------|-----|------|------|
| `time_bolt` | 타임 볼트 | 9 | BRV 공격 | 단일 BRV 피해 (MAG×1.8). 대안: 타임 쇼크 |
| `time_shock` | 타임 쇼크 | 14 | BRV 공격 | 전체 BRV 피해 (MAG×1.0). 대안: 타임 볼트 |
| `chrono_blast` | 크로노 블라스트 | 17 | HP 공격 | 단일 HP 피해 (MAG×2.2) + 슬롯 1개 즉시 생성. 대안: 타임 웨이브 |
| `time_wave` | 타임 웨이브 | 19 | BRV+HP | 전체 BRV 피해 (MAG×1.0) → 전체 HP 피해 (MAG×0.7). 20% 슬로우. 대안: 크로노 블라스트 |

### 버프/디버프 스킬

| 스킬 ID | 이름 | MP | 타입 | 효과 |
|---------|------|-----|------|------|
| `haste` | 헤이스트 | 11 | 버프 | 아군 1명 SPD +30% (3턴). 대안: 슬로우 |
| `slow` | 슬로우 | 9 | 디버프 | 적 1명 SPD -30% (3턴). 대안: 헤이스트 |
| `time_stop` | 시간 정지 | 19 | CC | 적 1명 1턴 행동불가. 대안: 시간 가속 |
| `time_accel` | 시간 가속 | 15 | 버프 | 아군 1명 ATB 75% 즉시 충전. 시간술사 ATB 50%만 소모. 대안: 시간 정지 |
| `future_sight` | 미래 예지 | 14 | 버프 | 아군 1명 회피율 +50% (2턴) + 다음 공격 크리티컬 확정. 대안: 과거 회귀 |
| `past_regression` | 과거 회귀 | 14 | 회복 | 아군 1명 HP를 2턴 전 상태로 복원 (최대 40% 회복). 대안: 미래 예지 |

### 회복/방어 스킬

| 스킬 ID | 이름 | MP | 타입 | 효과 |
|---------|------|-----|------|------|
| `rewind` | 리와인드 | 17 | 회복 | 아군 1명 HP 30% 회복 + 디버프 1개 해제. 대안: 역설 방어 |
| `paradox_guard` | 역설 방어 | 14 | 방어 | "피해를 받지 않았을 가능성" 실현. 이번 턴 받는 피해 60% 감소. 대안: 리와인드 |

### 가능성 시스템 스킬

| 스킬 ID | 이름 | MP | 타입 | 효과 |
|---------|------|-----|------|------|
| `summon_possibility` | 가능성 소환 | **0** | 특수 | 슬롯에서 가능성 1개 선택 → 85% 위력으로 즉시 발동 (MP 무료!) |
| `time_crossing` | 시간선 교차 | 14 | 특수 | 슬롯의 가능성 2개 동시 발동 (각 75% 위력) |
| `time_storm` | 시간 폭풍 | 26 | 특수 | 모든 슬롯 가능성 해방 (100% 위력). 3개 이상 시 수렴 보너스 |
| `fate_copy` | 운명 복제 | 15 | 특수 | 아군 1명의 마지막 사용 스킬을 가능성으로 저장 (파티 연계!) |
| `overwrite_fate` | 운명 덮어쓰기 | 11 | 특수 | 지정한 슬롯의 가능성을 원하는 보유 스킬로 교체 |

### 궁극기

| 스킬 ID | 이름 | MP | 조건 | 효과 |
|---------|------|-----|------|------|
| `infinite_convergence` | 무한 수렴 | 38 | 슬롯 3개 이상 | 저장된 모든 가능성 + "타임 볼트/타임 쇼크/리와인드" 연속 발동. 발동 후 슬롯 초기화. 모든 스킬 120% 위력 |

---

## 7. 스킬 상세

### 7.1 타임 볼트 (Time Bolt)

```yaml
id: time_bolt
name: 타임 볼트
type: brv_attack
description: 응축된 시간 에너지를 발사하여 단일 적에게 BRV 피해
costs:
  mp: 9
  cast_time: 0.8
effects:
  - type: damage
    target: single_enemy
    damage_type: magic
    multiplier: 1.8
    element: time
  - type: generate_possibility
    chance: 0.70  # 분기점 창조자로 85%
    alternative_skill: time_shock
possibility_pair: time_shock
```

### 7.2 크로노 블라스트 (Chrono Blast)

```yaml
id: chrono_blast
name: 크로노 블라스트
type: hp_attack
description: 시간의 폭발을 일으켜 강력한 단일 HP 피해 + 가능성 확정 생성
costs:
  mp: 17
  cast_time: 1.2
effects:
  - type: damage
    target: single_enemy
    damage_type: magic
    multiplier: 2.2
    element: time
  - type: generate_possibility
    chance: 1.0  # 100% 확정 생성
    alternative_skill: time_wave
possibility_pair: time_wave
```

### 7.3 미래 예지 (Future Sight)

```yaml
id: future_sight
name: 미래 예지
type: buff
description: 아군에게 미래를 보여주어 회피와 크리티컬 보장
costs:
  mp: 14
  cast_time: 0.6
target: ally
effects:
  - type: buff
    stat: evasion
    value: 0.50  # +50% 회피
    duration: 2
  - type: buff
    special: guaranteed_critical
    duration: 1  # 다음 공격만
  - type: generate_possibility
    chance: 0.70
    alternative_skill: past_regression
possibility_pair: past_regression
```

### 7.4 과거 회귀 (Past Regression)

```yaml
id: past_regression
name: 과거 회귀
type: heal
description: 대상의 HP를 2턴 전 상태로 되돌린다
costs:
  mp: 14
  cast_time: 1.0
target: ally
effects:
  - type: temporal_heal
    method: restore_past_hp
    turns_back: 2
    max_heal_percent: 0.40  # 최대 40% 회복
  - type: generate_possibility
    chance: 0.70
    alternative_skill: future_sight
possibility_pair: future_sight
```

### 7.5 운명 덮어쓰기 (Overwrite Fate)

```yaml
id: overwrite_fate
name: 운명 덮어쓰기
type: special
description: 슬롯의 가능성을 원하는 스킬로 교체한다
costs:
  mp: 11
  cast_time: 0.5
requirements:
  min_possibilities: 1
effects:
  - type: replace_possibility
    target: selected_slot
    replacement: selected_own_skill
    power_ratio: 0.85
  - type: special_note
    text: "궁극기는 선택 불가"
restrictions:
  - cannot_select_ultimate
  - cannot_select_teamwork
```

### 7.6 시간 폭풍 (Time Storm)

```yaml
id: time_storm
name: 시간 폭풍
type: special
description: 저장된 모든 가능성을 한번에 해방하여 시간의 폭풍을 일으킨다
costs:
  mp: 26
  cast_time: 1.5
requirements:
  min_possibilities: 1
effects:
  - type: release_all_possibilities
    power_ratio: 1.0  # 100% 위력
  - type: convergence_bonus
    min_possibilities: 3
    damage_bonus: 0.40
    apply_debuff:
      type: time_lock
      duration: 1
      effect: atb_stop
  - type: clear_slots
    after_cast: true
```

### 7.7 운명 복제 (Fate Copy)

```yaml
id: fate_copy
name: 운명 복제
type: special
description: 아군의 마지막 행동을 "가능성"으로 저장한다
costs:
  mp: 15
  cast_time: 0.5
target: ally
effects:
  - type: copy_last_skill
    target: selected_ally
    store_as_possibility: true
    power_ratio: 0.85
  - type: special_note
    text: "궁극기 및 아이템 사용은 복제 불가"
restrictions:
  - cannot_copy_ultimate
  - cannot_copy_items
  - cannot_copy_teamwork
```

### 7.8 무한 수렴 (Infinite Convergence) - 궁극기

```yaml
id: infinite_convergence
name: 무한 수렴
type: ultimate
description: |
  모든 시간선의 가능성을 하나로 수렴시켜
  과거, 현재, 미래의 자신이 동시에 공격한다
costs:
  mp: 38
  cast_time: 2.0
requirements:
  min_possibilities: 3
effects:
  # 1단계: 저장된 가능성 모두 발동
  - type: release_all_possibilities
    power_ratio: 1.2  # 120% 위력
    sequence: true
    delay_between: 0.3
  
  # 2단계: 고정 스킬 연속 발동
  - type: chain_cast
    skills:
      - skill_id: time_bolt
        power_ratio: 1.2
      - skill_id: time_shock  
        power_ratio: 1.2
      - skill_id: rewind
        target: lowest_hp_ally
        power_ratio: 1.2
  
  # 3단계: 마무리 효과
  - type: finale
    damage_type: magic
    multiplier: 2.5  # 피니시 피해
    target: all_enemies
    apply_debuff:
      type: time_fracture
      effect: all_stats_down
      value: 0.20
      duration: 2
  
  # 슬롯 초기화
  - type: clear_slots
    after_cast: true
```

---

## 8. 전투 흐름 예시

### 기본 콤보

```
=== 턴 1 ===
시간술사: 타임 볼트 → 적A에게 1,200 피해
  └→ [슬롯1] 타임 쇼크 저장됨 (대안 가능성)
  └→ ★ 평행 공명: MAG +8%

=== 턴 2 ===
시간술사: 헤이스트 → 광전사 SPD +30%
  └→ [슬롯2] 슬로우 저장됨
  └→ ★ 평행 공명: MAG +16%, 피해감소 5%

=== 턴 3 ===
시간술사: 운명 복제 → 광전사의 "광란의 일격" 복제!
  └→ [슬롯3] 광란의 일격 저장됨
  └→ ★ 평행 공명: MAG +24%, 피해감소 10%

=== 턴 4 ===
시간술사: 타임 볼트 → 적A에게 1,500 피해 (평행 공명 보너스)
  └→ [슬롯4] 타임 쇼크 저장됨
  └→ ★ 평행 공명 MAX: MAG +32%, 피해감소 15%, ATB +15%

=== 턴 5 (폭발!) ===
시간술사: 시간 폭풍!
  ├→ [타임 쇼크] 발동 → 전체 900 피해
  ├→ [슬로우] 발동 → 적 전체 SPD -30%
  ├→ [광란의 일격] 발동 → 적A에게 1,800 피해!
  ├→ [타임 쇼크] 발동 → 전체 900 피해
  └→ ★ 수렴 보너스: 추가 40% 피해 + 시간 고정 (1턴 ATB 정지)

총 효과: 4,500+ 피해 + 전체 속도 감소 + 전체 1턴 스턴
```

### 위기 대응

```
상황: 힐러 사망, 탱커 HP 20%

=== 긴급 턴 ===
시간술사: 가능성 소환 → [리와인드] 선택
  └→ 탱커 HP 30% 회복 + 디버프 해제
  └→ (MP 0 소모! 원래 17 필요)

다음 턴: 역설 방어 → 탱커 피해 60% 감소
  └→ [슬롯] 리와인드 저장됨 (다음 힐 준비)
```

---

## 9. UI 시각화

```
┌──────────────────────────────────────────────────────────────┐
│                      【 시간술사 】                          │
│  HP ████████████░░░░░░  MP ██████████████░░░                │
│     115/180               78/98                              │
├──────────────────────────────────────────────────────────────┤
│                    ◆ 가능성 슬롯 ◆                           │
│  ┌──────────┬──────────┬──────────┬──────────┐              │
│  │ ⚡ 타임  │ 🐢 슬로우 │ ⚔️ 광란의 │ ⚡ 타임  │              │
│  │   쇼크   │          │   일격   │   쇼크   │              │
│  │  [공격]  │ [디버프] │  [공격]  │  [공격]  │              │
│  │   85%   │   85%    │   85%   │   85%   │              │
│  └──────────┴──────────┴──────────┴──────────┘              │
│                                                              │
│  ★ 평행 공명 MAX                                             │
│    • 마법 공격력: +32%                                       │
│    • 받는 피해: -15%                                         │
│    • ATB 충전: +15%                                          │
│                                                              │
│  ◈ 수렴 준비 완료! (4/4 슬롯)                                │
└──────────────────────────────────────────────────────────────┘
```

---

## 10. 밸런스 분석

### 강점

| 항목 | 설명 |
|------|------|
| **한 턴 다중 스킬** | 가능성 소환으로 턴당 2~5개 스킬 발동 가능 |
| **상황 대응력** | 다양한 스킬을 저장해두고 필요할 때 사용 |
| **팀 시너지** | 운명 복제로 아군 강력 스킬 재사용 |
| **스탯 버프** | 가능성 보유만으로도 최대 MAG +32% |
| **MP 효율** | 가능성 소환은 **MP 0**으로 어떤 스킬이든 발동! |

### 약점

| 항목 | 설명 |
|------|------|
| **셋업 시간** | 최대 효율까지 3~4턴 필요 |
| **슬롯 소진 후 취약** | 시간 폭풍 후 일시적 화력 저하 |
| **운 의존성** | 가능성 생성이 확률 기반 (85%) |
| **복잡한 자원 관리** | 슬롯 + MP 동시 관리 필요 |
| **특정 스킬 저장 불가** | 원하는 가능성을 직접 선택 불가 |

### DPS 비교 (5턴 기준)

| 직업 | 5턴 예상 총 피해 | 특징 |
|------|------------------|------|
| **시간술사** | 8,000~12,000 | 폭발 턴에 집중 |
| 아크메이지 | 9,000~11,000 | 꾸준한 고피해 |
| 정령술사 | 7,500~10,000 | 융합 콤보 의존 |
| 바드 | 5,000~7,000 | 버프/디버프 중심 |

---

## 11. 파티 조합 추천

### 최적 조합

| 조합 | 시너지 |
|------|--------|
| **시간술사 + 광전사** | 운명 복제로 광전사 궁극기 재사용 |
| **시간술사 + 암살자** | 시간 정지 → 암살자 크리티컬 세팅 |
| **시간술사 + 클레릭** | 리와인드 복제로 이중 힐링 |
| **시간술사 + 바드** | 버프 지속시간 연장 + 가능성 저장 |

### 역할 분담

```
[메인 딜러] 광전사/암살자
    ↓ 운명 복제
[서브 딜러/유틸] 시간술사
    ↓ 시간 조작
[힐러] 클레릭/드루이드
    ↓ 리와인드 백업
[탱커] 기사/팔라딘
```

---

## 12. 구현 체크리스트

### 캐릭터 데이터
- [ ] `data/characters/time_mage.yaml` 수정
- [ ] 스탯 밸런스 조정
- [ ] 기믹 정의 추가
- [ ] 특성 5개 정의

### 스킬 데이터 (17개)
- [ ] `data/skills/time_bolt.yaml` 수정
- [ ] `data/skills/time_shock.yaml` 수정
- [ ] `data/skills/chrono_blast.yaml` 신규
- [ ] `data/skills/time_wave.yaml` 신규
- [ ] `data/skills/haste.yaml` 수정
- [ ] `data/skills/slow.yaml` 수정
- [ ] `data/skills/time_stop.yaml` 수정
- [ ] `data/skills/time_accel.yaml` 신규
- [ ] `data/skills/future_sight.yaml` 신규
- [ ] `data/skills/past_regression.yaml` 신규
- [ ] `data/skills/rewind.yaml` 수정
- [ ] `data/skills/paradox_guard.yaml` 신규
- [ ] `data/skills/summon_possibility.yaml` 신규
- [ ] `data/skills/time_crossing.yaml` 신규
- [ ] `data/skills/time_storm.yaml` 신규
- [ ] `data/skills/fate_copy.yaml` 신규
- [ ] `data/skills/overwrite_fate.yaml` 신규
- [ ] `data/skills/infinite_convergence.yaml` 신규 (궁극기)

### 시스템 구현
- [ ] `src/character/gimmick_updater.py` - 가능성 슬롯 시스템
- [ ] `src/combat/skill_executor.py` - 가능성 생성/소환 로직
- [ ] `src/character/trait_effects.py` - 특성 효과 처리
- [ ] `src/ui/gimmick_display.py` - UI 표시

### 기본 공격
- [ ] `src/character/basic_attacks.py` - time_mage 프로필 수정

---

## 13. 최종 YAML 예시

```yaml
class_name: 시간술사
description: 평행 시간선의 가능성을 소환하여 전투하는 시공의 마법사
slogan: "선택하지 않은 길도, 결국 나의 것이다"
archetype: 마법 딜러/유틸리티

base_stats:
  hp: 115
  mp: 98
  init_brv: 105
  speed: 62
  physical_attack: 42
  physical_defense: 45
  magic_attack: 82
  magic_defense: 65
  max_brv: 420

stat_growth:
  hp: 8.5
  mp: 7.5
  init_brv: 21.0
  strength: 2.2
  defense: 2.0
  magic: 5.2
  spirit: 4.2
  speed: 4.5
  luck: 4.0
  accuracy: 2.0
  evasion: 2.5
  max_brv: 84.0

gimmick:
  type: possibility_slots
  name: 가능성 슬롯
  description: |
    스킬 사용 시 "선택하지 않은 가능성"을 슬롯에 저장.
    저장된 가능성을 소환하여 추가 행동 가능!
    가능성이 많을수록 평행 공명으로 강해진다.
  max_slots: 4
  base_generation_chance: 0.70
  possibility_power_ratio: 0.85
  resonance_per_slot:
    magic_attack_bonus: 0.08
    damage_reduction: 0.05
  full_slot_bonus:
    atb_bonus: 0.15

traits:
  - id: branch_creator
    name: 분기점 창조자
    description: 가능성 생성 확률 +15%, 행운 비례 추가 증가
    type: passive
    
  - id: parallel_resonance
    name: 평행 공명
    description: 보유 가능성당 마법 공격력 +8%, 받는 피해 -5%
    type: passive
    
  - id: timeline_interference
    name: 시간선 간섭
    description: 가능성 소환 시 30% 확률로 소멸하지 않음 (최대 2회)
    type: trigger
    
  - id: converging_fates
    name: 수렴하는 운명
    description: 시간 폭풍으로 3개 이상 해방 시 피해 +40%, 시간 고정 부여
    type: conditional
    
  - id: infinite_branches
    name: 무한 분기
    description: 전투 시작 시 가능성 1개 자동 생성, HP 30% 이하 시 생성 확률 100%
    type: passive

skills:
  - teamwork
  # 공격 스킬 (4개)
  - time_bolt
  - time_shock
  - chrono_blast
  - time_wave
  # 버프/디버프 스킬 (6개)
  - haste
  - slow
  - time_stop
  - time_accel
  - future_sight
  - past_regression
  # 회복/방어 스킬 (2개)
  - rewind
  - paradox_guard
  # 가능성 시스템 스킬 (5개)
  - summon_possibility
  - time_crossing
  - time_storm
  - fate_copy
  - overwrite_fate
  # 궁극기 (1개)
  - infinite_convergence

bonuses:
  magic_multiplier: 1.1
  atb_rate: 1.08
  spell_cast_speed: 1.1
```

---

## 14. 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2025-11-30 | 초기 설계 문서 작성 |

---

*이 문서는 시간술사 리워크의 설계 명세서입니다. 실제 구현 시 밸런스 테스트를 거쳐 수치가 조정될 수 있습니다.*
