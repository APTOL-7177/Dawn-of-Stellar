# 직업별 기본 공격 차별화 시스템

## 개요

각 직업의 기본 BRV 공격과 HP 공격이 고유한 특성을 갖도록 구현한 시스템입니다.
34개 직업별로 차별화된 공격 프로필이 적용됩니다.

## 구현 파일

### 1. `src/character/basic_attacks.py`
직업별 기본 공격 프로필을 정의하는 새 파일입니다.

**주요 기능:**
- `JOB_ATTACK_PROFILES`: 34개 직업의 공격 프로필 딕셔너리
- `get_attack_profile()`: 직업별 프로필 조회 함수
- `calculate_stat_value()`: 프로필 기반 스탯 계산
- `get_critical_chance_modifier()`: 크리티컬 확률 보정
- `get_critical_multiplier()`: 크리티컬 배율 조회
- `get_defense_ignore()`: 방어력 무시 비율 조회

### 2. `src/combat/damage_calculator.py` (수정)
데미지 계산기에 직업 프로필 시스템을 통합했습니다.

**주요 변경사항:**
- `calculate_brv_damage()`: 직업 프로필 기반 BRV 데미지 계산
- `calculate_hp_damage()`: 직업 프로필 기반 HP 데미지 계산
- `_check_critical_with_profile()`: 프로필 기반 크리티컬 판정 (신규)

## 공격 프로필 구조

```python
{
    "brv_attack": {
        "name": "공격 이름",
        "damage_type": "physical/magic/hybrid",
        "stat_base": "strength/magic/both",
        "base_multiplier": 1.0,  # 기본 배율
        "can_critical": True,     # 크리티컬 가능 여부
        "critical_bonus": 0.0,    # 추가 크리티컬 확률 (옵션)
        "critical_multiplier": 1.5,  # 크리티컬 배율 (옵션)
        # ... 추가 특성
    },
    "hp_attack": {
        # 동일한 구조
    }
}
```

## 직업별 특성

### 물리 딜러 계열

#### 전사 (Warrior)
- **BRV 공격**: 강타 (배율 1.3x, 크리티컬 가능)
- **HP 공격**: 방패 강타 (배율 1.1x, 크리티컬 불가)
- **특징**: 균형잡힌 기본 성능

#### 광전사 (Berserker)
- **BRV 공격**: 광란의 일격 (배율 1.5x, 크리티컬 +20%)
- **HP 공격**: 피의 수확 (배율 1.3x, 크리티컬 가능)
- **특징**: 최고 데미지, 높은 크리티컬

#### 검투사 (Gladiator)
- **BRV 공격**: 검투사의 타격 (배율 1.4x)
- **HP 공격**: 결투의 일격 (배율 1.2x, 크리티컬 가능)
- **특징**: 높은 기본 배율

#### 다크 나이트 (Dark Knight)
- **BRV 공격**: 암흑 베기 (배율 1.35x, 어둠 속성)
- **HP 공격**: 생명 흡수 (배율 1.0x, 20% 흡혈)
- **특징**: 흡혈 능력

#### 기사 (Knight)
- **BRV 공격**: 기사의 창 (배율 1.2x)
- **HP 공격**: 수호의 타격 (배율 0.9x, 방어력 10% 추가)
- **특징**: 방어력 활용

#### 팔라딘 (Paladin)
- **BRV 공격**: 성스러운 일격 (배율 1.1x, 신성 속성)
- **HP 공격**: 응징의 빛 (배율 0.95x, 정신력 30% 추가)
- **특징**: 정신력 스케일링

### 속도형 물리 딜러

#### 암살자 (Assassin)
- **BRV 공격**: 암살 (배율 1.25x, 크리티컬 +25%)
- **HP 공격**: 그림자 일격 (배율 1.15x, 속도 20% 추가)
- **특징**: 최고 크리티컬, 속도 스케일링

#### 도적 (Rogue)
- **BRV 공격**: 기습 (배율 1.2x, 크리티컬 +15%)
- **HP 공격**: 독침 (배율 1.0x, 30% 독 부여)
- **특징**: 독 효과

#### 해적 (Pirate)
- **BRV 공격**: 난폭한 일격 (배율 1.35x, 행운 15% 추가)
- **HP 공격**: 약탈의 일격 (배율 1.1x)
- **특징**: 행운 스케일링

### 원거리 물리 딜러

#### 궁수 (Archer)
- **BRV 공격**: 정밀 사격 (배율 1.15x, 명중 +20)
- **HP 공격**: 관통 화살 (배율 1.05x, 방어력 20% 무시)
- **특징**: 높은 명중률, 방어 관통

#### 저격수 (Sniper)
- **BRV 공격**: 조준 사격 (배율 1.1x, 크리티컬 배율 2.0x)
- **HP 공격**: 저격 (배율 1.0x, 크리티컬 배율 2.5x)
- **특징**: 극한의 크리티컬 배율

#### 엔지니어 (Engineer)
- **BRV 공격**: 기계 타격 (배율 1.2x, 마법력 20% 추가)
- **HP 공격**: 폭발 공격 (배율 1.15x, 30% 광역)
- **특징**: 하이브리드 스케일링

### 격투가 계열

#### 몽크 (Monk)
- **BRV 공격**: 철권 (배율 1.25x, 콤보 스케일링)
- **HP 공격**: 기공파 (배율 1.1x, 기 에너지 스케일링)
- **특징**: 콤보/기 에너지 연동

#### 사무라이 (Samurai)
- **BRV 공격**: 발도 (배율 1.4x, 크리티컬 +10%)
- **HP 공격**: 일섬 (배율 1.2x)
- **특징**: 높은 순간 화력

#### 검성 (Sword Saint)
- **BRV 공격**: 검기 베기 (배율 1.35x, 검기 스케일링)
- **HP 공격**: 섬공 (배율 1.15x, 원거리 가능)
- **특징**: 검기 시스템 연동

#### 용기사 (Dragon Knight)
- **BRV 공격**: 용의 발톱 (배율 1.3x, 용 속성)
- **HP 공격**: 용의 숨결 (배율 1.2x, 화염 속성, 40% 광역)
- **특징**: 광역 공격

### 마법 딜러 계열

#### 마법사 (Mage)
- **BRV 공격**: 마법 화살 (배율 1.2x)
- **HP 공격**: 마력 폭발 (배율 1.0x, 비전 속성)
- **특징**: 기본 마법 공격

#### 아크메이지 (Archmage)
- **BRV 공격**: 대마법 (배율 1.3x, 원소 조합)
- **HP 공격**: 원소 융합 (배율 1.1x, 원소 조합)
- **특징**: 원소 시스템 활용

#### 정령술사 (Elementalist)
- **BRV 공격**: 정령의 축복 (배율 1.25x, 정령 친화도)
- **HP 공격**: 정령 소환 (배율 1.05x)
- **특징**: 정령 친화도 연동

#### 배틀 메이지 (Battle Mage)
- **BRV 공격**: 마검 (배율 1.15x, 물리 60% + 마법 40%)
- **HP 공격**: 마력 베기 (배율 1.0x, 물리 50% + 마법 50%)
- **특징**: 완전한 하이브리드

#### 스펠블레이드 (Spellblade)
- **BRV 공격**: 마력 부여 (배율 1.2x, 물리 70% + 마법 30%)
- **HP 공격**: 원소 베기 (배율 1.05x, 물리 60% + 마법 40%)
- **특징**: 물리 중심 하이브리드

#### 네크로맨서 (Necromancer)
- **BRV 공격**: 생명 흡수 (배율 1.15x, 15% 흡혈)
- **HP 공격**: 네크로 폭발 (배율 1.0x, 네크로 에너지)
- **특징**: 어둠 속성, 흡혈

#### 시간술사 (Time Mage)
- **BRV 공격**: 시간 왜곡 (배율 1.1x, 20% 슬로우)
- **HP 공격**: 시간 붕괴 (배율 0.95x, 시간 기록점)
- **특징**: 시간 조작

#### 차원술사 (Dimensionist)
- **BRV 공격**: 차원 베기 (배율 1.25x, 방어력 30% 무시)
- **HP 공격**: 공간 붕괴 (배율 1.1x, 50% 광역)
- **특징**: 강력한 방어 관통

### 지원 계열

#### 신관 (Priest)
- **BRV 공격**: 성스러운 빛 (배율 0.9x)
- **HP 공격**: 심판의 빛 (배율 0.8x, 정신력 40% 추가)
- **특징**: 낮은 공격력, 정신력 활용

#### 클레릭 (Cleric)
- **BRV 공격**: 치유의 빛 (배율 0.85x, 10% 자힐)
- **HP 공격**: 신성한 망치 (배율 0.75x)
- **특징**: 최저 공격력, 자가 치유

#### 바드 (Bard)
- **BRV 공격**: 음파 공격 (배율 0.95x, 멜로디)
- **HP 공격**: 불협화음 (배율 0.85x, 30% 약화)
- **특징**: 디버프 효과

#### 드루이드 (Druid)
- **BRV 공격**: 자연의 분노 (배율 1.0x)
- **HP 공격**: 가시 덤불 (배율 0.9x, 15% 지속 데미지)
- **특징**: 도트 데미지

#### 샤먼 (Shaman)
- **BRV 공격**: 토템의 힘 (배율 1.05x)
- **HP 공격**: 정령의 분노 (배율 0.95x)
- **특징**: 자연 속성

### 특수 계열

#### 뱀파이어 (Vampire)
- **BRV 공격**: 흡혈 (배율 1.2x, 25% 흡혈)
- **HP 공격**: 피의 마법 (배율 1.1x, 15% 흡혈, 하이브리드)
- **특징**: 강력한 생존력

#### 브레이커 (Breaker)
- **BRV 공격**: 브레이크 타격 (배율 1.4x, BRV 깎기 150%)
- **HP 공격**: 파쇄 일격 (배율 1.25x, BREAK 보너스 +50%)
- **특징**: BREAK 특화

#### 연금술사 (Alchemist)
- **BRV 공격**: 연금술 타격 (배율 1.15x)
- **HP 공격**: 폭발 물약 (배율 1.05x, 40% 광역)
- **특징**: 가변 속성

#### 철학자 (Philosopher)
- **BRV 공격**: 진리의 타격 (배율 1.1x, 지혜 스케일링)
- **HP 공격**: 철학자의 돌 (배율 1.0x, 10% MP 회복)
- **특징**: MP 회복

#### 해커 (Hacker)
- **BRV 공격**: 해킹 공격 (배율 1.2x, 25% 약화)
- **HP 공격**: 바이러스 (배율 1.0x, 20% 지속 데미지)
- **특징**: 디버프와 도트

## 추가 특성 옵션

### 스탯 스케일링
- `defense_bonus`: 방어력 추가 (기사)
- `spirit_scaling`: 정신력 추가 (팔라딘, 신관)
- `speed_scaling`: 속도 추가 (암살자)
- `luck_scaling`: 행운 추가 (해적)
- `magic_scaling`: 마법력 추가 (엔지니어)

### 크리티컬 관련
- `can_critical`: 크리티컬 가능 여부
- `critical_bonus`: 크리티컬 확률 보정 (+0.0 ~ +0.25)
- `critical_multiplier`: 크리티컬 배율 (1.5 ~ 2.5)

### 방어 관련
- `ignore_defense`: 방어력 무시 비율 (0.0 ~ 0.3)

### 추가 효과
- `lifesteal`: 흡혈 비율
- `poison_chance`: 독 부여 확률
- `slow_chance`: 슬로우 확률
- `debuff_chance`: 약화 확률
- `splash_damage`: 광역 데미지 비율
- `dot_damage`: 지속 데미지 비율
- `heal_on_hit`: 타격 시 자가 치유
- `mp_restore`: MP 회복

### 기믹 연동
- `combo_scaling`: 콤보 스택에 비례
- `ki_scaling`: 기 에너지에 비례
- `aura_scaling`: 검기에 비례
- `melody_scaling`: 멜로디 스택에 비례
- `necro_scaling`: 네크로 에너지에 비례
- `spirit_bond_scaling`: 정령 친화도에 비례
- `time_mark_scaling`: 시간 기록점에 비례
- `element_combo`: 원소 조합 활용
- `break_efficiency`: BRV 깎기 효율
- `break_bonus`: BREAK 보너스 증가

## 사용 방법

### 기본 사용 (자동 적용)
```python
from src.combat.damage_calculator import DamageCalculator

calc = DamageCalculator()

# BRV 공격 (직업 프로필 자동 적용)
brv_result = calc.calculate_brv_damage(attacker, defender)

# HP 공격 (직업 프로필 자동 적용)
hp_result, wound = calc.calculate_hp_damage(attacker, defender, brv_points=100)
```

### 직업 프로필 비활성화
```python
# 기존 방식으로 계산하려면
brv_result = calc.calculate_brv_damage(attacker, defender, use_job_profile=False)
hp_result, wound = calc.calculate_hp_damage(attacker, defender, brv_points=100, use_job_profile=False)
```

## 밸런스 가이드라인

### 데미지 배율 기준
- **순수 딜러**: 1.3 ~ 1.5
- **하이브리드**: 1.1 ~ 1.3
- **지원형**: 0.8 ~ 1.0

### 크리티컬 확률 보너스
- **일반**: 0% (기본 확률만)
- **크리티컬 특화**: +10% ~ +25%

### 크리티컬 배율
- **일반**: 1.5x (기본)
- **크리티컬 특화**: 2.0x ~ 2.5x

### HP 공격 배율
- BRV 공격 배율의 80% ~ 90% 수준
- 일부 직업은 크리티컬 가능

## 테스트

테스트 스크립트 실행:
```bash
python test_basic_attacks.py
```

테스트 항목:
1. 직업별 기본 공격 프로필 적용 확인
2. 크리티컬 특화 직업 비교
3. 물리 딜러 vs 마법 딜러 비교
4. 지원형 vs 딜러형 데미지 비교

## 확장 가능성

### 신규 직업 추가
`src/character/basic_attacks.py`의 `JOB_ATTACK_PROFILES`에 직업 추가:

```python
"new_job": {
    "brv_attack": {
        "name": "공격명",
        "damage_type": "physical/magic/hybrid",
        "stat_base": "strength/magic/both",
        "base_multiplier": 1.0,
        "can_critical": True,
        # ... 추가 특성
    },
    "hp_attack": {
        # ...
    }
}
```

### 신규 특성 추가
1. `basic_attacks.py`에 특성 정의
2. `damage_calculator.py`에서 특성 처리 로직 구현
3. 테스트 추가

## 주의사항

- 직업 ID는 YAML 파일명과 일치해야 합니다
- 배율 조정 시 전체 밸런스 고려 필요
- 크리티컬 확률은 최대 95%로 제한됩니다
- 하이브리드 직업은 `physical_ratio` + `magic_ratio` = 1.0 유지

## 버전 히스토리

- **v1.0.0** (2025-11-14): 초기 구현
  - 34개 직업 프로필 완성
  - DamageCalculator 통합
  - 테스트 스크립트 작성
