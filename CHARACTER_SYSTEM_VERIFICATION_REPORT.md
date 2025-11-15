# 캐릭터 시스템 검증 보고서

**생성일**: 2025-11-14
**대상**: 34개 직업 시스템 (스킬, 기본공격, 기믹)

---

## 📊 검증 요약

| 항목 | 상태 | 세부 내용 |
|------|------|-----------|
| **직업 수** | ✅ 34개 | 모든 직업 YAML 존재 |
| **스킬 시스템** | ✅ 정상 | 204개 스킬, 195개 파일 (일부 공유) |
| **기본 공격** | ✅ 정상 | 34개 직업 모두 BRV/HP 공격 정의됨 |
| **기믹 시스템** | ⚠️ 수정 필요 | 31개 문제 발견 |

---

## ✅ 정상 항목

### 1. 스킬 시스템
- **총 스킬 수**: 204개 (직업당 6개)
- **스킬 파일**: 195개 YAML 파일 존재
- **공유 스킬**: 9개 스킬이 여러 직업에서 공유
  - backstab, shadow_strike, vanish, death_mark, blood_frenzy 등

### 2. 기본 공격 시스템 (basic_attacks.py)
34개 직업 모두에 대해 다음이 정의됨:
- **BRV 공격**: 브레이브 축적 공격
- **HP 공격**: HP 데미지 공격

각 직업별 고유한 특성:
- 물리/마법/하이브리드 타입
- 크리티컬 특성
- 특수 효과 (흡혈, 방어 무시, 상태이상 등)

---

## ⚠️ 수정 필요 항목

### 1. 기믹 YAML 정의 누락 (29개 직업)

다음 직업들이 스킬에서 기믹을 사용하지만 YAML에 정의가 없습니다:

#### 물리 딜러 계열
1. **berserker** (광전사)
   - 사용 중인 필드: `rage_stacks`, `shield_amount`
   - 필요 기믹: `rage_system`

2. **gladiator** (검투사)
   - 사용 중인 필드: `glory_points`, `kill_count`, `parry_active`
   - 필요 기믹: `arena_system`

3. **dark_knight** (다크나이트)
   - 사용 중인 필드: `darkness`
   - 필요 기믹: `darkness_system`

4. **knight** (기사)
   - 사용 중인 필드: `duty_stacks`
   - 필요 기믹: `duty_system`

5. **paladin** (팔라딘)
   - 사용 중인 필드: `holy_power`
   - 필요 기믹: `holy_system`

#### 속도형 물리 딜러
6. **assassin** (암살자)
   - 사용 중인 필드: `stealth_points`
   - 필요 기믹: `stealth_system`

7. **rogue** (도적)
   - 사용 중인 필드: `evasion_active`, `stolen_items`
   - 필요 기믹: `theft_system`

8. **pirate** (해적)
   - 사용 중인 필드: `gold`
   - 필요 기믹: `plunder_system`

#### 원거리 물리 딜러
9. **archer** (궁수)
   - 사용 중인 필드: `aim_points`
   - 필요 기믹: `aim_system`

10. **sniper** (저격수)
    - 사용 중인 필드: `focus_stacks`
    - 필요 기믹: `aim_system`

11. **engineer** (엔지니어)
    - 사용 중인 필드: `machine_parts`
    - 필요 기믹: `construct_system`

#### 격투가 계열
12. **monk** (몽크)
    - 사용 중인 필드: `chakra_points`, `combo_count`
    - 필요 기믹: `ki_system`

13. **samurai** (사무라이)
    - 사용 중인 필드: `will_gauge`
    - 필요 기믹: `iaijutsu_system`

14. **sword_saint** (검성)
    - 사용 중인 필드: `sword_aura`
    - 필요 기믹: `sword_aura`

15. **dragon_knight** (용기사)
    - 사용 중인 필드: `dragon_power`
    - 필요 기믹: `dragon_marks`

#### 마법 딜러 계열
16. **battle_mage** (배틀메이지)
    - 사용 중인 필드: `rune_stacks`
    - 필요 기믹: `rune_system`

17. **spellblade** (마검사)
    - 사용 중인 필드: `mana_blade`
    - 필요 기믹: `enchant_system`

18. **necromancer** (네크로맨서)
    - 사용 중인 필드: `corpse_count`, `minion_count`
    - 필요 기믹: `necro_system`

19. **time_mage** (시간마법사)
    - 사용 중인 필드: `time_points`
    - 필요 기믹: `time_system`

20. **dimensionist** (차원술사)
    - 사용 중인 필드: `dimension_points`
    - 필요 기믹: `dimension_system`

#### 지원 계열
21. **priest** (프리스트)
    - 사용 중인 필드: `judgment_points`
    - 필요 기믹: `divinity_system`

22. **cleric** (클레릭)
    - 사용 중인 필드: `faith_points`
    - 필요 기믹: `divinity_system`

23. **bard** (바드)
    - 사용 중인 필드: `melody_notes`, `octave_completed`
    - 필요 기믹: `melody_system`

24. **druid** (드루이드)
    - 사용 중인 필드: `nature_points`
    - 필요 기믹: `shapeshifting_system`

25. **shaman** (샤먼)
    - 사용 중인 필드: `curse_stacks`
    - 필요 기믹: `totem_system`

#### 특수 계열
26. **vampire** (뱀파이어)
    - 사용 중인 필드: `blood_pool`, `lifesteal_boost`
    - 필요 기믹: `blood_system`

27. **alchemist** (연금술사)
    - 사용 중인 필드: `potion_stock`
    - 필요 기믹: `alchemy_system`

28. **philosopher** (철학자)
    - 사용 중인 필드: `knowledge_stacks`
    - 필요 기믹: `wisdom_system`

29. **hacker** (해커)
    - 사용 중인 필드: `debuff_count`, `hack_stacks`
    - 필요 기믹: `hack_system`

### 2. character.py 초기화 코드 누락 (1개)

**breaker** (브레이커)
- YAML에 정의된 타입: `break_system`
- 문제: `character.py`의 `_initialize_gimmick()` 함수에 초기화 코드 없음
- 필요 필드: `break_power`, `max_break_power`

### 3. 필드 불일치 (1개)

**elementalist** (정령술사)
- YAML에 정의: `spirit_bond` 타입
- character.py 초기화: `spirit_bond`, `max_spirit_bond`
- 스킬에서 사용: `spirit_count` ❌
- **문제**: 스킬이 `spirit_count`를 사용하지만 초기화되지 않음
- **해결**: `spirit_bond` 타입 초기화에 `spirit_count` 필드 추가 필요

---

## 📝 수정 계획

### 1단계: breaker 초기화 코드 추가
`src/character/character.py`의 `_initialize_gimmick()` 함수에 추가:

```python
elif gimmick_type == "break_system":
    self.break_power = 0
    self.max_break_power = gimmick_data.get('max_break_power', 10)
```

### 2단계: elementalist 필드 추가
`spirit_bond` 타입 초기화에 `spirit_count` 필드 추가:

```python
elif gimmick_type == "spirit_bond":
    self.spirit_bond = 0
    self.max_spirit_bond = gimmick_data.get('max_spirit_bond', 100)
    self.spirit_count = 0  # ← 추가
```

### 3단계: 29개 직업 YAML에 기믹 정의 추가
각 직업 YAML 파일에 `gimmick` 섹션 추가

예시 (berserker.yaml):
```yaml
gimmick:
  type: rage_system
  name: 광전사의 분노
  description: 전투 중 분노를 축적하여 강력한 공격 수행
  max_rage_stacks: 10
```

---

## 🎯 기대 효과

수정 후:
- ✅ 모든 직업의 기믹이 YAML에 명확히 정의됨
- ✅ character.py에서 모든 기믹 타입 초기화 가능
- ✅ 스킬에서 사용하는 모든 필드가 올바르게 초기화됨
- ✅ 기믹 시스템의 일관성 확보

---

## 📚 참고 정보

### 현재 character.py에 지원되는 기믹 타입 (14개)
1. `aim_system` - 조준 시스템 (궁수, 저격수)
2. `arena_system` - 투기장 시스템 (검투사)
3. `dragon_marks` - 용의 각인 (용기사)
4. `elemental_counter` - 원소 카운터 (메이지, 대마법사)
5. `ki_system` - 기 시스템 (몽크)
6. `melody_system` - 멜로디 시스템 (바드)
7. `necro_system` - 네크로 시스템 (네크로맨서)
8. `rage_system` - 분노 시스템 (광전사)
9. `shadow_system` - 그림자 시스템 (암살자)
10. `spirit_bond` - 정령 유대 (정령술사)
11. `stance_system` - 스탠스 시스템 (전사)
12. `sword_aura` - 검기 (검성)
13. `time_system` - 시간 시스템 (시간마법사)
14. `venom_system` - 맹독 시스템 (도적)

### 추가 필요한 기믹 타입 (15개)
1. `alchemy_system` - 연금술
2. `blood_system` - 흡혈
3. `construct_system` - 구조물
4. `darkness_system` - 어둠
5. `dimension_system` - 차원
6. `divinity_system` - 신성력
7. `duty_system` - 의무
8. `enchant_system` - 마력 부여
9. `hack_system` - 해킹
10. `holy_system` - 성력
11. `iaijutsu_system` - 거합
12. `plunder_system` - 약탈
13. `shapeshifting_system` - 변신
14. `theft_system` - 절도
15. `totem_system` - 토템
16. `wisdom_system` - 지혜

---

**보고서 끝**
