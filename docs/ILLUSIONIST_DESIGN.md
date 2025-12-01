# 환술사: 거울 속의 군단 (Mirror Legion)

> **버전**: 1.1  
> **작성일**: 2025-12-01  
> **역할**: 회피형 탱커 / 하이브리드 딜러  
> **아키타입**: 특수 / 탱커 / 하이브리드

---

## 1. 컨셉 개요

### 핵심 판타지
> *"내가 하나인가? 열인가? 백인가? 너의 칼날이 닿을 수 있는 '나'는 존재하지 않는다."*

환술사는 자신의 환영을 만들어내어 적의 공격을 헛손질로 만들고, 다수의 환영과 함께 적을 압도하는 **거울의 군주**다. 단단한 갑옷이 아닌, "존재하지 않음"으로 아군을 지킨다.

### 플레이 스타일
- **회피형 탱커**: 낮은 HP를 회피와 환영으로 보완
- **하이브리드 딜러**: 물리/마법 병행, 환영과 함께 다단히트
- **보호막 서포터**: 아군에게 환영 분신을 부여해 피해 대신 받기
- **심리전 마스터**: 적 명중률 감소, 도발 분산 등 혼란 유발

---

## 2. 기본 스탯 (밸런스 비교)

### 스탯 비교표

| 스탯 | 환술사 | 기사 | 암살자 | 무도가 | 비고 |
|------|--------|------|--------|--------|------|
| **HP** | 95 | 165 | 98 | 112 | **낮음** (회피 필수) |
| **MP** | 72 | 48 | 65 | 58 | 중상 (환영 유지) |
| **init_brv** | 115 | 95 | 125 | 120 | 중상 |
| **speed** | 70 | 52 | 75 | 70 | 높음 (회피형) |
| **p_atk** | 62 | 72 | 85 | 78 | 중간 (하이브리드) |
| **p_def** | 48 | 82 | 45 | 55 | 낮음 (회피 의존) |
| **m_atk** | 62 | 38 | 48 | 42 | 중간 (하이브리드) |
| **m_def** | 52 | 55 | 52 | 48 | 중하 |
| **max_brv** | 400 | 380 | 450 | 435 | 중간 |

### 스탯 성장률

```yaml
stat_growth:
  hp: 6.5       # 낮음
  mp: 5.5
  init_brv: 22.0
  strength: 4.0  # 하이브리드
  defense: 2.2   # 낮음
  magic: 4.0     # 하이브리드
  spirit: 3.0
  speed: 5.2
  luck: 5.5
  accuracy: 3.0
  evasion: 6.5   # 최고 수준
  max_brv: 80.0
```

---

## 3. 기믹: 환영 군단 시스템 (Phantom Legion)

### 시스템 개요

```
┌──────────────────────────────────────────────────────────────┐
│                    【 환영 군단 】                            │
│                                                              │
│        👤         👤         👤         👤         👤       │
│      [본체]     [환영1]    [환영2]    [환영3]    [환영4]     │
│        ★          ◆          ◆          ◇          ◇       │
│      (고정)     (활성)     (활성)     (대기)     (대기)     │
│                                                              │
│  활성 환영: 2/4    │    회피 보너스: +24%                    │
│  공격 배수: x3     │    대신 맞을 확률: 51%                  │
│                                                              │
│  ◈ 잔상 게이지: ████████████████░░░░░ 80/100               │
└──────────────────────────────────────────────────────────────┘
```

### 기믹 상세

```yaml
gimmick:
  type: phantom_legion
  name: 환영 군단
  description: |
    [환영 시스템] 환영을 소환하여 함께 싸우고 피해를 분산하라!
    
    ◆ 기본 규칙
    - 최대 4개의 환영 유지 가능
    - 환영은 HP가 없으며, 히트 횟수로 소멸 (환영당 2히트 흡수)
    - 환영 소멸 시 "잔상 게이지" 충전
    
    ◆ 환영 보너스 (활성 환영 개수당)
    - 회피율 +12%
    - 공격 시 환영도 함께 공격 (환영당 본체 피해의 35%)
    - 피해를 환영이 대신 받을 확률 30% (중첩 계산)
      → 환영 1개: 30% 대신 맞음
      → 환영 2개: 51% 대신 맞음 (1-0.7²)
      → 환영 3개: 66% 대신 맞음 (1-0.7³)
      → 환영 4개: 76% 대신 맞음 (1-0.7⁴)
    
    ◆ 잔상 게이지 (소멸한 환영의 잔류 에너지)
    - 환영 소멸 시 25 충전 (최대 100)
    - 100 도달 시 "잔상 폭발" 발동 가능
    - 전투 종료 시 초기화
    
    ◆ 확정 회피 (Mirror Shift)
    - 환영 2개 이상 보유 시: 5턴마다 다음 공격 1회 확정 회피
    - 환영 4개 보유 시: 4턴마다 확정 회피 (쿨다운 1턴 감소)
    
  max_phantoms: 4
  phantom_hit_absorb: 2  # 환영당 흡수 가능 히트 수
  afterimage_max: 100
  afterimage_per_destroy: 25
  
  per_phantom_bonus:
    evasion_bonus: 0.12
    attack_echo_ratio: 0.35  # 환영 공격 = 본체의 35%
    damage_redirect_chance: 0.30  # 환영당 30% 확률로 대신 맞음 (중첩)
    
  mirror_shift:
    base_cooldown: 5  # 기본 5턴 쿨다운
    full_phantom_cooldown: 4  # 환영 4개 시 4턴
    min_phantoms: 2  # 최소 환영 2개 필요
```

### 환영 상태 표시

| 환영 상태 | 표시 | 설명 |
|-----------|------|------|
| 활성 (풀) | ◆ | 2히트 흡수 가능 |
| 활성 (반) | ◇ | 1히트 흡수 가능 |
| 소멸 | ○ | 슬롯 빈 상태 |
| 재생 중 | ◈ | 다음 턴 활성화 예정 |

---

## 4. 특성 (Traits) - 5개

### 특성 1: 거울 분신술 (Mirror Image)

```yaml
- id: mirror_image
  name: 거울 분신술
  description: |
    전투 시작 시 환영 2개 자동 생성.
    환영 소환 스킬 사용 시 추가 환영 1개 보너스 생성 (25% 확률).
  type: passive
  unlock_level: 1
  effects:
    start_phantoms: 2
    bonus_phantom_chance: 0.25
```

### 특성 2: 아지랑이 걸음 (Mirage Step)

```yaml
- id: mirage_step
  name: 아지랑이 걸음
  description: |
    회피 성공 시 ATB 10% 충전.
    확정 회피 성공 시 추가로 ATB 15% 충전 + 다음 공격 피해 +20%.
  type: trigger
  unlock_level: 5
  effects:
    evasion_atb_charge: 0.10
    perfect_evasion_atb_charge: 0.15
    perfect_evasion_damage_bonus: 0.20
    damage_bonus_duration: 1
```

### 특성 3: 환영 군주 (Phantom Lord)

```yaml
- id: phantom_lord
  name: 환영 군주
  description: |
    환영 4개 보유 시 특수 효과 활성화:
    - 적 전체 명중률 -15%
    - 아군 전체에게 "환영의 가호" (받는 피해 1회 50% 감소)
    효과는 환영이 4개 미만이 되면 해제됨.
  type: conditional
  unlock_level: 10
  conditions:
    phantom_count: 4
  effects:
    enemy_accuracy_debuff: 0.15
    ally_phantom_blessing:
      damage_reduction: 0.50
      hits: 1
```

### 특성 4: 그림자 잠식 (Shadow Feast)

```yaml
- id: shadow_feast
  name: 그림자 잠식
  description: |
    환영이 피해를 대신 받아 소멸할 때:
    - 자신 HP 5% 회복
    - 다음 공격 피해 +15%
    - 30% 확률로 해당 환영 즉시 재생성
  type: trigger
  unlock_level: 15
  effects:
    on_phantom_destroy:
      hp_restore: 0.05
      damage_bonus: 0.15
      damage_bonus_duration: 1
      regen_chance: 0.30
```

### 특성 5: 무한 거울 (Infinite Mirrors)

```yaml
- id: infinite_mirrors
  name: 무한 거울
  description: |
    환영 소멸 시 20% 확률로 즉시 재생성.
    HP 30% 이하일 때 재생성 확률 50%로 증가.
    환영의 히트 흡수량 +1 (총 3히트).
  type: passive
  unlock_level: 20
  effects:
    phantom_regen_chance: 0.20
    low_hp_threshold: 0.30
    low_hp_regen_chance: 0.50
    phantom_hit_bonus: 1
```

---

## 5. 기본 공격

### BRV 공격: 환영 난무

```yaml
brv_attack:
  name: 환영 난무
  damage_type: physical
  stat_base: strength  # 물리 기반
  magic_scaling: 0.3   # 마법도 30% 반영
  base_multiplier: 0.85  # 본체 기본
  multi_hit: true
  effects:
    - type: phantom_echo
      description: 활성 환영 수만큼 추가 타격
      per_phantom_multiplier: 0.35
    - type: generate_afterimage
      value: 5  # 잔상 게이지 +5
  description: |
    환영과 함께 적을 공격.
    본체 1회 + 환영 수만큼 추가 타격.
    (환영 4개 시 총 5히트!)
```

**예시 계산 (환영 3개 보유 시)**:
- 본체: 0.85 × STR
- 환영1: 0.35 × 0.85 × STR = 0.30 × STR
- 환영2: 0.30 × STR
- 환영3: 0.30 × STR
- **총 피해**: 1.75 × STR (4히트)

### HP 공격: 거울 참격

```yaml
hp_attack:
  name: 거울 참격
  damage_type: hybrid  # 물리+마법 혼합
  stat_base: [strength, magic]  # 둘 중 높은 것
  base_multiplier: 1.0
  can_critical: true
  effects:
    - type: phantom_convergence
      description: 모든 환영이 동시에 공격, 한 점에 수렴
      per_phantom_bonus: 0.15  # 환영당 +15% 피해
    - type: phantom_damage_absorb
      chance: 0.30
      description: 30% 확률로 환영 1개 소멸 대신 피해 +50%
  description: |
    모든 환영과 함께 적에게 수렴 공격.
    환영 1개당 피해 +15%.
    (환영 4개 시 총 +60% 피해!)
```

---

## 6. 스킬 세트 (17개)

### 환영 소환 스킬

| 스킬 ID | 이름 | MP | 타입 | 효과 |
|---------|------|-----|------|------|
| `summon_phantom` | 환영 소환 | 8 | 특수 | 환영 1~2개 생성. 운에 비례해 2개 생성 확률 증가 |
| `phantom_army` | 환영 군단 소집 | 18 | 특수 | 환영 슬롯을 최대(4개)로 채움. 쿨다운 4턴 |
| `mirror_replacement` | 거울 대체 | 5 | 특수 | 환영 1개 소멸 → 자신 HP 15% 회복 + 잔상 +35 |

### 회피/방어 스킬

| 스킬 ID | 이름 | MP | 타입 | 효과 |
|---------|------|-----|------|------|
| `phantom_dodge` | 환영 회피 | 6 | 방어 | 이번 턴 회피율 +50%. 회피 성공 시 환영 1개 생성 |
| `mirror_shield` | 거울 방패 | 10 | 버프 | 아군 1명에게 "환영 보호막" 부여. 다음 피해 2회 흡수 |
| `phase_walk` | 위상 이동 | 12 | 특수 | 다음 1턴간 확정 회피 + 환영 1개 생성. 공격 불가 |
| `shared_illusion` | 공유 환상 | 14 | 버프 | 아군 전체 회피율 +25% (2턴). 환영 1개 소모 |

### 공격 스킬

| 스킬 ID | 이름 | MP | 타입 | 효과 |
|---------|------|-----|------|------|
| `phantom_strike` | 환영 일격 | 8 | BRV 공격 | 단일 BRV 피해 (**STR**×1.6) + 환영×0.4. 총 최대 5히트 |
| `mirror_storm` | 거울 폭풍 | 12 | BRV 공격 | 전체 BRV 피해 (**MAG**×0.9) + 환영×0.25. 다단 히트 |
| `convergence_blade` | 수렴의 칼날 | 14 | HP 공격 | 단일 HP 피해 (**STR**×2.0). 환영 전부 수렴하여 +환영×25% |
| `phantom_rain` | 환영우 | 18 | BRV+HP | 전체 BRV (**MAG**×0.8) → 랜덤 4회 HP 공격. 환영 많을수록 타수 증가 |

### 디버프/유틸 스킬

| 스킬 ID | 이름 | MP | 타입 | 효과 |
|---------|------|-----|------|------|
| `confusion_veil` | 혼란의 장막 | 9 | 디버프 | 적 전체 명중률 -20% (3턴). 환영 보유 시 추가 -5% |
| `taunt_split` | 분산 도발 | 7 | 탱킹 | 적의 타겟을 환영들에게 분산. 환영 우선 타격됨 |
| `mirror_trap` | 거울 함정 | 11 | 설치 | 적 공격 시 30% 확률로 반사 (**MAG** 기반, 피해의 40%). 2턴 지속 |

### 궁극기

| 스킬 ID | 이름 | MP | 조건 | 효과 |
|---------|------|-----|------|------|
| `afterimage_burst` | 잔상 폭발 | 14 | 잔상 50+ | 잔상 소모 → 전체 BRV+HP (**MAG**×1.8). 환영 1개 생성 |

### 궁극기

| 스킬 ID | 이름 | MP | 조건 | 효과 |
|---------|------|-----|------|------|
| `infinite_reflection` | 무한 반사 | 28 | 잔상 게이지 80+ | 단일 HP 공격 (환영 수+1)×**STR**×0.6, 5~10히트 (0.2초 간격). 확정 회피 1턴. 환영 전부 소멸 후 2개 재생성 |

---

## 7. 스킬 상세

### 7.1 환영 소환 (Summon Phantom)

```yaml
id: summon_phantom
name: 환영 소환
type: special
description: 거울 속에서 자신의 환영을 불러낸다
costs:
  mp: 8
  cast_time: 0.5
effects:
  - type: summon_phantom
    base_count: 1
    bonus_count: 1
    bonus_chance: 0.30  # 30% 확률로 2개
    luck_scaling: 0.01  # 행운 10당 +10% 확률
  - type: buff
    target: self
    stat: evasion
    value: 0.10
    duration: 1
    description: 소환 직후 순간 회피 보너스
```

### 7.2 거울 방패 (Mirror Shield)

```yaml
id: mirror_shield
name: 거울 방패
type: buff
description: 아군에게 환영 분신을 부여하여 피해를 대신 받게 한다
costs:
  mp: 10
  cast_time: 0.6
target: ally
effects:
  - type: apply_shield
    shield_type: phantom_absorb
    absorb_hits: 2
    absorb_ratio: 1.0  # 100% 피해 흡수
    duration: 3  # 최대 3턴 또는 2히트
  - type: visual
    description: 대상 옆에 반투명 환영 표시
```

### 7.3 환영 일격 (Phantom Strike)

```yaml
id: phantom_strike
name: 환영 일격
type: brv_attack
description: 환영들과 함께 적을 연속 공격 (물리)
costs:
  mp: 8
  damage_type: physical  # STR 기반
  cast_time: 0.8
target: single_enemy
effects:
  - type: multi_hit_damage
    base_hits: 1
    phantom_hits: true  # 환영 수만큼 추가 히트
    damage_type: physical
    base_multiplier: 1.6
    phantom_multiplier: 0.4
    element: none
  - type: generate_afterimage
    value: 3  # 히트당 잔상 +3
```

**히트 테이블**:
| 환영 수 | 총 히트 | 총 배율 |
|---------|---------|---------|
| 0개 | 1히트 | 1.6× |
| 1개 | 2히트 | 2.0× |
| 2개 | 3히트 | 2.4× |
| 3개 | 4히트 | 2.8× |
| 4개 | 5히트 | 3.2× |

### 7.4 수렴의 칼날 (Convergence Blade)

```yaml
id: convergence_blade
name: 수렴의 칼날
type: hp_attack
description: 모든 환영이 한 점으로 수렴하여 강력한 일격을 가한다 (물리)
costs:
  mp: 14
  damage_type: physical  # STR 기반
  cast_time: 1.2
target: single_enemy
effects:
  - type: damage
    damage_type: hybrid
    base_multiplier: 2.0
    phantom_bonus: 0.25  # 환영당 +25%
    max_bonus: 1.0  # 최대 +100% (4개)
  - type: consume_option
    consume_phantoms: 1
    bonus_if_consumed:
      multiplier_bonus: 0.5
      guaranteed_critical: true
  - type: generate_afterimage
    value: 15
```

### 7.5 위상 이동 (Phase Walk)

```yaml
id: phase_walk
name: 위상 이동
type: special
description: 물질계를 벗어나 완전한 회피 상태에 진입
costs:
  mp: 12
  cast_time: 0.3
target: self
effects:
  - type: buff
    stat: guaranteed_evasion
    duration: 1
  - type: debuff
    stat: cannot_attack
    duration: 1
  - type: phantom_summon
    count: 1
```

### 7.6 분산 도발 (Taunt Split)

```yaml
id: taunt_split
name: 분산 도발
type: tank
description: 적의 공격 대상을 환영들에게 분산시킨다
costs:
  mp: 11
  cast_time: 0.5
target: self
effects:
  - type: taunt
    duration: 2
    special: phantom_priority
    description: |
      적이 환술사를 노릴 때:
      - 70% 확률로 환영이 대신 맞음
      - 환영이 없으면 본체가 맞음
  - type: phantom_buff
    effect: counter
    counter_chance: 0.25
    counter_damage: 0.5
```

### 7.7 환영우 (Phantom Rain)

```yaml
id: phantom_rain
name: 환영우
type: brv_hp_attack
description: 무수한 환영들이 적진에 쏟아진다
costs:
  mp: 24
  cast_time: 1.5
target: all_enemies
effects:
  - type: brv_damage
    target: all_enemies
    damage_type: physical
    multiplier: 0.7
  - type: hp_damage
    target: random_enemies
    hits: 4  # 기본 4회
    phantom_bonus_hits: 1  # 환영당 +1회 (최대 8회)
    multiplier_per_hit: 0.3
  - type: debuff
    target: all_enemies
    stat: accuracy
    value: 0.10
    duration: 2
```

### 7.8 잔상 폭발 (Afterimage Burst) - 통상 스킬

```yaml
id: afterimage_burst
name: 잔상 폭발
type: brv_hp_attack
description: 축적된 잔상을 폭발시켜 적을 공격 (마법)
costs:
  mp: 14
  cast_time: 1.0
requirements:
  afterimage_gauge: 50
effects:
  - type: consume_afterimage
    amount: all
  - type: brv_hp_damage
    target: all_enemies
    damage_type: magic  # MAG 기반
    multiplier: 1.8
    afterimage_bonus: 0.01  # 잔상 1당 +1%
  - type: phantom_summon
    count: 1
```

### 7.9 무한 반사 (Infinite Reflection) - 궁극기

```yaml
id: infinite_reflection
name: 무한 반사
type: ultimate
description: |
  모든 환영이 한 점에 수렴하여 연속 공격 (물리).
  거울의 미로 속에서 적은 진짜를 찾을 수 없다.
costs:
  mp: 28
  cast_time: 2.0
requirements:
  afterimage_gauge: 80
effects:
  # 1단계: 환영 수렴
  - type: consume_all_phantoms
    store_count: true
  
  # 2단계: 다단 히트 HP 공격 (0.2초 간격)
  - type: multi_hit_hp_damage
    target: single_enemy
    damage_type: physical  # STR 기반
    hits_formula: "phantom_count + 1"  # 환영 4개면 5히트
    max_hits: 10
    base_multiplier: 0.6
    hit_delay: 0.2  # 0.2초 간격
    visual: "환영들이 연속으로 관통"
  
  # 3단계: 회피 및 재생
  - type: buff
    target: self
    stat: guaranteed_evasion
    duration: 1
  - type: phantom_restore
    count: 2
  
  # 4단계: 잔상 초기화
  - type: consume_afterimage
    amount: all
```

---

## 8. 다단히트 시스템

### 히트 딜레이 (Hit Delay)

환술사의 다단히트는 타격감을 위해 각 히트 사이에 **0.2초** 간격을 둡니다.

```yaml
multi_hit_system:
  hit_delay: 0.2  # 초 단위
  damage_display: individual  # 각 히트별 피해 표시
  visual_effect: phantom_slash
  sound_effect: slash_chain
```

### 예시: 환영 일격 (5히트)

```
[0.0초] 본체 공격 → 480 BRV 피해
[0.2초] 환영1 공격 → 168 BRV 피해
[0.4초] 환영2 공격 → 168 BRV 피해
[0.6초] 환영3 공격 → 168 BRV 피해
[0.8초] 환영4 공격 → 168 BRV 피해

총 시간: 0.8초
총 피해: 1,152 BRV
```

---

## 9. 전투 흐름 예시

### 기본 탱킹 패턴

```
=== 전투 시작 ===
[특성: 거울 분신술] 환영 2개 자동 생성
  └→ 현재 환영: ◆◆○○
  └→ ★ 회피 보너스: +24%

=== 턴 1 ===
환술사: 분산 도발
  └→ 적의 공격이 환영에게 분산됨
  └→ 적 공격 → 환영1이 대신 맞음 (1히트 흡수)
  └→ 현재 환영: ◇◆○○

=== 턴 2 ===
환술사: 환영 소환
  └→ 환영 2개 생성!
  └→ 현재 환영: ◇◆◆◆
  └→ ★ 회피 보너스: +48%
  └→ ★ 확정 회피 쿨다운: 4턴 (환영 4개 보너스)

=== 턴 3 (적 턴) ===
적 보스: 강타 → 환술사
  └→ [확정 회피 발동!] 미스!
  └→ ★ 아지랑이 걸음: ATB +25%, 다음 공격 +20%

=== 턴 4 ===
환술사: 수렴의 칼날 → 보스
  └→ 본체 + 환영 4개 수렴!
  └→ 기본 2.0× + 환영 보너스 100% = 4.0×
  └→ 아지랑이 걸음 보너스 +20% = 4.8×
  └→ 5,200 HP 피해! 크리티컬!
```

### 다단히트 딜러 패턴

```
=== 턴 1 ===
환술사: 환영 군단 소집
  └→ 환영 4개 즉시 생성!
  └→ 현재 환영: ◆◆◆◆
  └→ ★ 환영 군주 발동!
  └→   • 적 전체 명중률 -15%
  └→   • 아군 전체 "환영의 가호"

=== 턴 2 ===
환술사: 환영 일격 → 적A
  └→ 본체 1.6× (히트1)
  └→ 환영1 0.4× (히트2)
  └→ 환영2 0.4× (히트3)
  └→ 환영3 0.4× (히트4)
  └→ 환영4 0.4× (히트5)
  └→ 총 5히트! 3.2× = 2,800 BRV 피해
  └→ 잔상 게이지: +15

=== 턴 3 ===
환술사: 환영우 → 적 전체
  └→ 전체 BRV 0.7× (1,200 피해)
  └→ 랜덤 HP 공격 8회! (기본 4 + 환영 4)
  └→ 적A: 3히트 / 적B: 2히트 / 적C: 3히트
  └→ 잔상 게이지: +45

=== 턴 4 ===
(적들의 반격으로 환영 2개 소멸)
  └→ 현재 환영: ○○◆◆
  └→ 잔상 게이지: 45 + 50 = 95

=== 턴 5 ===
환술사: 환영 소환
  └→ 환영 2개 생성
  └→ 현재 환영: ◆◆◆◆
  └→ 잔상 게이지: 100 도달!
  └→ ★ 잔상 폭발 사용 가능!

=== 턴 6 ===
환술사: 무한 반사! (궁극기)
  └→ 환영 4개 소모
  └→ (4+1)×2 = 10히트 공격!
  └→ 히트당 0.8× = 8.0× 총 피해
  └→ 잔상 피니시: 2.0× + 100% = 4.0×
  └→ 총 12.0× = 13,000 피해!
  └→ 환영 4개 재생성
  └→ 확정 회피 3턴 획득
```

### 파티 보호 패턴

```
=== 상황: 보스 광역기 예고 ===

턴 1: 환술사: 거울 방패 → 힐러
  └→ 힐러에게 환영 보호막 (2히트 흡수)

턴 2: 환술사: 공유 환상
  └→ 환영 1개 소모
  └→ 아군 전체 회피율 +25% (2턴)

턴 3: 보스: 멸망의 일격 (전체 공격)
  └→ 환술사: 확정 회피 → 미스!
  └→ 힐러: 환영 보호막 → 피해 흡수!
  └→ 딜러1: 회피 성공 (25% 보너스)
  └→ 딜러2: 피격 → 환영의 가호로 50% 감소

결과: 파티 생존!
```

---

## 9. UI 시각화

```
┌──────────────────────────────────────────────────────────────┐
│                       【 환술사 】                            │
│  HP ██████████████░░░░  MP ████████████░░░░░░                │
│     128/160              54/72                                │
├──────────────────────────────────────────────────────────────┤
│                    ◆ 환영 군단 ◆                              │
│                                                              │
│           👤        👤        👤        👤                   │
│         [본체]    [환영1]   [환영2]   [환영3]                 │
│           ★         ◆         ◆         ◇                   │
│                   2/2히트   2/2히트   1/2히트                 │
│                                                              │
│  ┌────────────────────────────────────────────────────┐      │
│  │ 잔상 게이지: ████████████████████░░░░░ 80/100     │      │
│  └────────────────────────────────────────────────────┘      │
│                                                              │
│  ◈ 활성 보너스                                               │
│    • 회피율: +36%                                            │
│    • 공격 시: 본체 + 3히트 추가                               │
│    • 대신 맞을 확률: 66%                                      │
│                                                              │
│  ◈ 확정 회피 [Mirror Shift]                                  │
│    ▶ 쿨다운: 2턴 남음 (4턴 주기)                              │
│                                                              │
│  ◈ 환영 군주 [활성]                                          │
│    • 적 명중률: -15%                                         │
│    • 아군 보호: 환영의 가호                                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 10. 밸런스 분석

### 강점

| 항목 | 설명 |
|------|------|
| **생존력** | 확정 회피 + 환영 피해 분산으로 높은 생존율 |
| **다단히트** | 환영 4개 시 기본 공격도 5히트, 스킬은 10히트 이상 |
| **파티 보호** | 거울 방패, 공유 환상으로 아군 보호 |
| **자가 회복** | 환영 소멸/재생 사이클로 지속 탱킹 |
| **디버프** | 적 명중률 감소로 파티 전체 생존 기여 |

### 약점

| 항목 | 설명 |
|------|------|
| **환영 의존** | 환영 없으면 회피도, 피해도 급감 |
| **광역 취약** | 다수 히트 광역기에 환영 빠르게 소멸 |
| **낮은 단일 화력** | 다단히트지만 총합 DPS는 전문 딜러 대비 낮음 |
| **리소스 관리** | 환영 개수, 잔상 게이지 동시 관리 필요 |
| **진실 피해 취약** | 회피 불가 공격에는 무력 |

### 생존력 비교

| 직업 | 유효 HP | 생존 메커니즘 |
|------|---------|---------------|
| **환술사** | 중 (128) + 회피 | 회피 50%+, 확정 회피, 환영 분산 |
| 기사 | 고 (165) + 방어 | 높은 HP/방어, 물리 저항 |
| 팔라딘 | 고 (155) + 힐 | HP + 자가 회복 |
| 암살자 | 저 (98) + 회피 | 높은 회피지만 맞으면 위험 |

### DPS 비교 (5턴 기준)

| 직업 | 5턴 예상 총 피해 | 히트 수 | 특징 |
|------|------------------|---------|------|
| **환술사** | 6,000~9,000 | 20~40히트 | 다단히트, 중간 총합 |
| 암살자 | 10,000~14,000 | 5~10히트 | 고피해 소수 히트 |
| 무도가 | 8,000~11,000 | 15~25히트 | 다단히트 전문 |
| 광전사 | 9,000~12,000 | 5~8히트 | 폭발 딜링 |

---

## 11. 파티 조합 추천

### 최적 조합

| 조합 | 시너지 |
|------|--------|
| **환술사 + 힐러** | 거울 방패로 힐러 보호, 회피 탱킹으로 힐 부담 감소 |
| **환술사 + 암살자** | 환술사가 어그로 분산, 암살자는 안전하게 딜링 |
| **환술사 + 시간술사** | 헤이스트로 환술사 턴 가속, 더 많은 회피 기회 |
| **환술사 + 바드** | 회피율 버프 중첩으로 거의 무적 상태 |

### 역할 분담

```
[회피 탱커] 환술사
    ↓ 분산 도발 + 환영 분산
[메인 딜러] 암살자/광전사
    ↓ 안전한 딜링 환경
[서포터] 바드/시간술사
    ↓ 회피/속도 버프
[힐러] 클레릭/드루이드
    ↓ 거울 방패로 보호받음
```

### 주의할 조합

| 조합 | 문제점 |
|------|--------|
| 환술사 + 기사 | 탱커 중복, 딜 부족 |
| 환술사 only 탱커 | 진실 피해/광역 다히트에 취약 |

---

## 12. 구현 체크리스트

### 캐릭터 데이터
- [ ] `data/characters/illusionist.yaml` 생성
- [ ] 스탯 밸런스 검증
- [ ] 기믹 정의 추가
- [ ] 특성 5개 정의

### 스킬 데이터 (17개)
- [ ] `data/skills/summon_phantom.yaml` 신규
- [ ] `data/skills/phantom_army.yaml` 신규
- [ ] `data/skills/mirror_replacement.yaml` 신규
- [ ] `data/skills/phantom_dodge.yaml` 신규
- [ ] `data/skills/mirror_shield.yaml` 신규
- [ ] `data/skills/phase_walk.yaml` 신규
- [ ] `data/skills/shared_illusion.yaml` 신규
- [ ] `data/skills/phantom_strike.yaml` 신규
- [ ] `data/skills/mirror_storm.yaml` 신규
- [ ] `data/skills/convergence_blade.yaml` 신규
- [ ] `data/skills/phantom_rain.yaml` 신규
- [ ] `data/skills/confusion_veil.yaml` 신규
- [ ] `data/skills/taunt_split.yaml` 신규
- [ ] `data/skills/mirror_trap.yaml` 신규
- [ ] `data/skills/infinite_reflection.yaml` 신규 (궁극기)
- [ ] 기본 BRV 공격: 환영 난무
- [ ] 기본 HP 공격: 거울 참격

### 시스템 구현
- [ ] `src/character/gimmick_updater.py` - 환영 군단 시스템
- [ ] `src/combat/skill_executor.py` - 다단히트 로직, 환영 소환/소멸
- [ ] `src/character/trait_effects.py` - 특성 효과 처리
- [ ] `src/ui/gimmick_display.py` - 환영 UI 표시
- [ ] `src/combat/damage_handler.py` - 환영 피해 분산 로직

### 기본 공격
- [ ] `src/character/basic_attacks.py` - illusionist 프로필 추가

---

## 13. 최종 YAML 예시

```yaml
class_name: 환술사
description: 거울 속 환영을 부리는 회피형 탱커이자 다단히트 딜러
slogan: "네가 베는 것은 그림자, 진짜 나는 이미 네 뒤에 있다"
archetype: 특수/탱커/하이브리드

base_stats:
  hp: 95
  mp: 72
  init_brv: 115
  speed: 70
  physical_attack: 62
  physical_defense: 48
  magic_attack: 62
  magic_defense: 52
  max_brv: 400

stat_growth:
  hp: 6.5
  mp: 5.5
  init_brv: 22.0
  strength: 4.0
  defense: 2.2
  magic: 4.0
  spirit: 3.0
  speed: 5.2
  luck: 5.5
  accuracy: 3.0
  evasion: 6.5
  max_brv: 80.0

multi_hit_delay: 0.2  # 다단히트 간격 (초)

gimmick:
  type: phantom_legion
  name: 환영 군단
  description: |
    환영을 소환하여 함께 싸우고 피해를 분산.
    환영이 많을수록 회피율과 공격 히트 수 증가.
    환영 소멸 시 잔상 게이지 충전 → 잔상 폭발 발동!
  max_phantoms: 4
  phantom_hit_absorb: 2
  afterimage_max: 100
  afterimage_per_destroy: 25
  per_phantom_bonus:
    evasion: 0.12
    attack_echo: 0.35
    damage_redirect_chance: 0.30  # 중첩 계산
  mirror_shift:
    base_cooldown: 5
    full_phantom_cooldown: 4

traits:
  - id: mirror_image
    name: 거울 분신술
    description: 전투 시작 시 환영 2개 생성, 소환 시 25% 확률로 추가 생성
    type: passive
    
  - id: mirage_step
    name: 아지랑이 걸음
    description: 회피 시 ATB +10%, 확정 회피 시 ATB +25% 및 피해 +20%
    type: trigger
    
  - id: phantom_lord
    name: 환영 군주
    description: 환영 4개 시 적 명중률 -15%, 아군에게 환영의 가호
    type: conditional
    
  - id: shadow_feast
    name: 그림자 잠식
    description: 환영 소멸 시 HP 5% 회복, 피해 +15%, 30% 재생성
    type: trigger
    
  - id: infinite_mirrors
    name: 무한 거울
    description: 환영 소멸 시 20% 재생성, HP 30% 이하 시 50%로 증가
    type: passive

skills:
  - teamwork
  # 환영 소환 (3개)
  - summon_phantom
  - phantom_army
  - mirror_replacement
  # 회피/방어 (4개)
  - phantom_dodge
  - mirror_shield
  - phase_walk
  - shared_illusion
  # 공격 (4개)
  - phantom_strike
  - mirror_storm
  - convergence_blade
  - phantom_rain
  # 디버프/유틸 (3개)
  - confusion_veil
  - taunt_split
  - mirror_trap
  # 잔상 스킬 (1개)
  - afterimage_burst
  # 궁극기 (1개)
  - infinite_reflection

bonuses:
  evasion_multiplier: 1.15
  multi_hit_delay: 0.2
  atb_on_evade: 0.05

# 스킬 스케일링 분류
skill_scaling:
  physical:  # STR 기반
    - phantom_strike
    - convergence_blade
    - infinite_reflection
    - taunt_split
  magical:   # MAG 기반
    - mirror_storm
    - phantom_rain
    - afterimage_burst
    - mirror_trap
    - confusion_veil
```

---

## 14. 다른 직업과의 차별점

| 비교 대상 | 환술사의 차별점 |
|-----------|----------------|
| **기사 (정통 탱커)** | HP/방어 대신 회피로 탱킹. 피격 0이 목표 |
| **암살자 (회피형)** | 암살자는 회피+도주, 환술사는 회피+도발 |
| **무도가 (다단히트)** | 무도가는 콤보, 환술사는 환영과 동시 공격 |
| **소환사 (소환물)** | 소환수는 독립 개체, 환영은 분신/확장 |

---

## 15. 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2025-12-01 | 초기 설계 문서 작성 |

---

*이 문서는 환술사의 설계 명세서입니다. 실제 구현 시 밸런스 테스트를 거쳐 수치가 조정될 수 있습니다.*
