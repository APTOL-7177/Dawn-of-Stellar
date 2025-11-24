# 미구현 특성 및 스킬 효과 목록

**작성일**: 2025-11-25
**총 미구현 특성**: 92개
**총 직업**: 33개

---

## 진행 상황 요약

- ✅ **완전 구현 (14개 직업)**: 연금술사, 아크메이지, 바드, 광전사, 차원술사, 정령술사, 기계공학자, 검투사, 해커, 몽크, 저격수, 마검사, 시간술사, 전사, 암흑기사
- 🔴 **미구현 특성 있음 (19개 직업)**: 나머지 직업들

---

## 공통 스킬 메타데이터

### ✅ 구현 완료
- [x] `lifesteal` - 흡혈 효과 (피해의 %만큼 HP 회복)
- [x] `undead_bonus` - 언데드 추가 피해 (언데드 대상에게 추가 데미지)
- [x] `defense_pierce_fixed` - 방어 관통 (방어력 무시)
- [x] `execute` - 처형 (적 HP 낮을 때 추가 피해)
- [x] `low_hp_bonus` - 저체력 보너스 (execute와 연계)
- [x] `stun_chance` - 기절 확률
- [x] `parry` - 패링 메커니즘 (캐스트 중 피격 시 카운터)
- [x] `parry_damage_multiplier` - 패링 데미지 배율
- [x] `parry_charge_gain` - 패링 성공 시 충전 획득
- [x] `charge_cost` - 충전 소모량 (암흑기사)
- [x] `charge_gain` - 충전 획득량 (암흑기사)
- [x] `builder` - 충전 쌓기 스킬 표시 (암흑기사)
- [x] `spender` - 충전 소모 스킬 표시 (암흑기사)
- [x] `explosive_power` - 폭발적 힘 (충전 75%+ 시 충격파, 암흑기사 특성)
- [x] `cast_time` - 캐스트 타임 (ATB 기반)
- [x] `interruptible` - 중단 가능 여부
- [x] `counter_on_interrupt` - 중단 시 카운터

### 🔴 미구현 - 기본 효과
- [ ] `pierce` / `armor_penetration` - 방어 무시 (%) - defense_pierce_fixed와 별도
- [ ] `splash_damage` - 추가 범위 피해 (주변 적에게 피해)
- [ ] `splash_radius` - 범위 피해 반경
- [ ] `cleave` - 광역 베기 (전방 적들에게 피해)
- [ ] `chain_lightning` - 연쇄 공격 (다음 대상으로 전파)
- [ ] `bounce_count` - 연쇄 횟수
- [ ] `reflect_damage` - 피해 반사
- [ ] `thorns` - 가시 (피격 시 반격)
- [ ] `heal_on_hit` - 타격 시 회복
- [ ] `mp_on_hit` - 타격 시 MP 회복
- [ ] `brv_on_hit` - 타격 시 BRV 회복

### 🔴 미구현 - 상태이상 관련
- [ ] `burn_duration` - 화상 지속시간 (현재 고정값)
- [ ] `burn_damage` - 화상 피해량
- [ ] `poison_duration` - 독 지속시간
- [ ] `poison_damage` - 독 피해량
- [ ] `bleed_duration` - 출혈 지속시간
- [ ] `bleed_stacks` - 출혈 스택
- [ ] `slow_percent` - 둔화 정도 (속도 감소 %)
- [ ] `slow_duration` - 둔화 지속시간
- [ ] `freeze_chance` - 빙결 확률
- [ ] `freeze_duration` - 빙결 지속시간
- [ ] `silence_chance` - 침묵 확률 (마법 봉인)
- [ ] `silence_duration` - 침묵 지속시간
- [ ] `blind_chance` - 실명 확률 (명중률 감소)
- [ ] `blind_duration` - 실명 지속시간
- [ ] `curse_duration` - 저주 지속시간
- [ ] `curse_effect` - 저주 효과

### 🔴 미구현 - 직업별 기믹 메타데이터

#### 연금술사 (Alchemist) - alchemy_system
- [ ] `potion_type` - 물약 타입 (healing, mana, rage, clarity, shadow, haste)
- [ ] `flask_cost` - 플라스크 소모량
- [ ] `potion_multiplier` - 물약 효과 배율
- [ ] `transmute` - 변환 효과

#### 궁수 (Archer) - support_fire
- [x] `arrow_type` - 화살 타입 (구현됨: gimmick_updater.py에서 처리)
- [ ] `mark_all` - 전체 마킹
- [ ] `mark_duration` - 마킹 지속시간
- [ ] `support_damage_ratio` - 지원사격 데미지 비율

#### 암살자 (Assassin) - stealth_exposure
- [ ] `stealth_attack` - 은신 공격 (은신 중 사용 시 추가 효과)
- [ ] `stealth_break` - 은신 해제 여부
- [ ] `exposure_penalty` - 노출 패널티
- [ ] `restealth_cooldown` - 재은신 쿨다운

#### 바드 (Bard) - melody_system
- [ ] `melody_gain` - 멜로디 게이지 획득
- [ ] `melody_cost` - 멜로디 게이지 소모
- [ ] `octave` - 옥타브 (low, mid, high)
- [ ] `melody_effect` - 멜로디 효과
- [ ] `chord` - 코드 조합 효과

#### 배틀메이지 (Battle Mage) - rune_resonance
- [ ] `rune_type` - 룬 타입 (fire, ice, lightning, earth, wind, water)
- [ ] `consumes_runes` - 룬 소모 여부
- [ ] `rune_cost` - 룬 소모 개수
- [ ] `rune_combo` - 룬 조합 효과
- [ ] `resonance_bonus` - 공명 보너스

#### 브레이커 (Breaker) - break_system
- [ ] `break_power_gain` - 브레이크 파워 획득
- [ ] `break_scaling` - 브레이크 파워 비례 데미지
- [ ] `break_duration_extend` - 브레이크 지속시간 연장
- [ ] `wound_damage_bonus` - 상처 데미지 보너스

#### 성직자/신관 (Cleric/Priest) - divinity_system / holy_system
- [ ] `faith_gain` - 신앙 게이지 획득
- [ ] `faith_cost` - 신앙 게이지 소모
- [ ] `prayer` - 기도 효과
- [ ] `divine_blessing` - 신성한 축복
- [ ] `holy_damage` - 성스러운 피해 (언데드에 강함)
- [ ] `miracle_chance` - 기적 확률

#### 용기사 (Dragon Knight) - dragon_marks
- [x] `dragon_mark_gain` - 용표 획득 (구현됨: combat_manager.py)
- [ ] `dragon_mark_cost` - 용표 소모
- [ ] `dragon_breath_damage` - 용의 숨결 피해
- [ ] `dragon_scale` - 용의 비늘 (방어력)

#### 드루이드 (Druid) - shapeshifting_system
- [ ] `animal_form` - 동물 형태 (bear, cat, wolf, eagle)
- [ ] `transform_cost` - 변신 코스트
- [ ] `form_bonus` - 형태별 보너스
- [ ] `nature_spell` - 자연 주문

#### 정령술사 (Elementalist) - elemental_spirits
- [ ] `spirit_type` - 정령 타입 (fire, water, earth, wind)
- [ ] `spirit_summon` - 정령 소환
- [ ] `spirit_command` - 정령 명령
- [ ] `spirit_fusion` - 정령 융합

#### 기계공학자 (Engineer) - heat_management
- [x] `heat_gain` - 열 획득 (구현됨: gimmick_updater.py)
- [x] `heat_cost` - 열 소모
- [x] `overheat_risk` - 과열 위험
- [x] `cooling` - 냉각 효과

#### 해커 (Hacker) - multithread_system
- [x] `thread_cost` - 스레드 소모 (구현됨: gimmick_updater.py)
- [x] `parallel_execution` - 병렬 실행
- [x] `hack_effect` - 해킹 효과

#### 기사 (Knight) - duty_system
- [ ] `duty_gain` - 의무 게이지 획득
- [ ] `duty_cost` - 의무 게이지 소모
- [ ] `vow_effect` - 서약 효과
- [ ] `protect_ally` - 아군 보호

#### 몽크 (Monk) - yin_yang_flow
- [x] `yin_yang_shift` - 음양 이동 (구현됨: gimmick_updater.py)
- [x] `balance_bonus` - 균형 보너스
- [x] `chakra` - 차크라 효과

#### 네크로맨서 (Necromancer) - undead_legion
- [ ] `summon_undead` - 언데드 소환
- [ ] `undead_type` - 언데드 타입 (skeleton, zombie, ghost)
- [ ] `sacrifice_undead` - 언데드 희생
- [ ] `death_energy` - 죽음의 에너지
- [ ] `corpse_explosion` - 시체 폭발

#### 성기사 (Paladin) - holy_system
- [ ] `holy_power` - 성스러운 힘
- [ ] `divine_shield` - 신성한 방패
- [ ] `smite` - 응징 (언데드/악마에 강함)
- [ ] `consecrate` - 성별 (지역 정화)

#### 철학자 (Philosopher) - dilemma_choice
- [ ] `dilemma_choice` - 딜레마 선택 (power/wisdom/sacrifice/truth)
- [ ] `choice_duration` - 선택 지속시간
- [ ] `philosophy_bonus` - 철학 보너스
- [ ] `paradox` - 역설 효과

#### 해적 (Pirate) - plunder_system
- [ ] `plunder_chance` - 약탈 확률
- [ ] `plunder_gold` - 골드 약탈
- [ ] `plunder_item` - 아이템 약탈
- [ ] `fortune_stack` - 행운 스택
- [ ] `dirty_trick` - 더러운 수법

#### 사무라이 (Samurai) - iaijutsu_system
- [x] `iaijutsu_charge` - 거합 충전 (구현됨: gimmick_updater.py)
- [ ] `honor_code` - 명예 규율
- [ ] `bushido_bonus` - 무사도 보너스
- [ ] `meditation_effect` - 명상 효과

#### 무당 (Shaman) - totem_system
- [ ] `totem_type` - 토템 타입 (fire, water, earth, wind, spirit)
- [ ] `totem_summon` - 토템 소환
- [ ] `totem_buff` - 토템 버프
- [ ] `spirit_link` - 영혼 연결

#### 저격수 (Sniper) - magazine_system
- [x] `bullet_type` - 탄환 타입 (구현됨: gimmick_updater.py)
- [x] `magazine_cost` - 탄창 소모
- [x] `reload` - 재장전
- [x] `headshot` - 헤드샷

#### 마검사 (Spellblade) - enchant_system
- [x] `enchant_type` - 부여 타입 (구현됨: gimmick_updater.py)
- [x] `enchant_duration` - 부여 지속시간
- [x] `spell_blade` - 마법검 효과

#### 검성 (Sword Saint) - sword_aura
- [ ] `aura_type` - 검기 타입 (cutting, piercing, crushing)
- [ ] `aura_stack` - 검기 스택
- [ ] `aura_release` - 검기 방출
- [ ] `sword_wave` - 검기파 (원거리)

#### 시간술사 (Time Mage) - timeline_system
- [x] `timeline_shift` - 타임라인 이동 (구현됨: gimmick_updater.py)
- [x] `past_bonus` - 과거 보너스
- [x] `future_bonus` - 미래 보너스
- [x] `time_stop` - 시간 정지

#### 뱀파이어 (Vampire) - thirst_gauge
- [x] `lifesteal_ratio` - 흡혈 비율 (구현됨: thirst_gauge)
- [x] `thirst_gain` - 갈증 감소
- [x] `blood_frenzy` - 피의 광기
- [ ] `blood_pool` - 혈액 저장소
- [ ] `sanguine_gift` - 혈액 선물

#### 암흑기사 (Dark Knight) - charge_system
- [x] 모든 메타데이터 구현됨

---

## 특수 메타데이터

### 타겟팅 관련
- [ ] `target_selection` - 대상 선택 방식 (random, weakest, strongest, nearest)
- [ ] `multi_target` - 다중 대상 (2~5개)
- [ ] `target_count` - 대상 개수
- [ ] `exclude_self` - 자신 제외

### 조건부 효과
- [ ] `on_crit_effect` - 크리티컬 시 추가 효과
- [ ] `on_kill_effect` - 처치 시 추가 효과
- [ ] `on_break_effect` - 브레이크 시 추가 효과
- [ ] `combo_multiplier` - 콤보 배율
- [ ] `combo_reset` - 콤보 초기화 여부
- [ ] `first_strike_bonus` - 선제공격 보너스
- [ ] `revenge_bonus` - 복수 보너스 (피격 후 공격)

### 리소스 관련
- [ ] `hp_cost` - HP 소모 (이미 있을 수도)
- [ ] `hp_percent_cost` - HP % 소모
- [ ] `brv_cost` - BRV 소모
- [ ] `sacrifice_hp` - HP 희생 (최대 HP 감소)
- [ ] `life_for_power` - 생명을 힘으로

### 궁극기 관련
- [x] `is_ultimate` - 궁극기 여부
- [x] `cooldown` - 쿨다운
- [ ] `ultimate_gauge_cost` - 궁극기 게이지 소모
- [ ] `finisher` - 피니셔 (특수 연출)

---

---

## 직업별 미구현 특성

### 🟢 1. 연금술사 (Alchemist) - 0/5
- [x] `potion_mastery`
- [x] `transmutation`
- [x] `chemical_weapon`
- [x] `emergency_elixir`
- [x] `philosopher_stone`

### 🟢 2. 궁수 (Archer) - 0/5
- [x] `support_fire_master`
- [x] `perfect_support`
- [x] `tactical_marksman`
- [x] `combo_momentum` - 콤보 지속 시 데미지 증가
- [x] `overwatch`

### 🟢 3. 아크메이지 (Archmage) - 0/5
- [x] 모든 특성 구현됨

### 🟢 4. 암살자 (Assassin) - 0/5
- [x] `critical_strike`
- [x] `shadow_mobility` - 은신 중 이동력 증가
- [x] `quick_restealth` - 빠른 재은신
- [x] `shadow_mastery` - 은신 지속시간 증가
- [x] `lethal_strike`

### 🟢 5. 바드 (Bard) - 0/5
- [x] 모든 특성 구현됨

### 🟢 6. 배틀메이지 (Battle Mage) - 0/5
- [x] `rune_mastery`
- [x] `hybrid_strike` - 물리+마법 하이브리드 공격
- [x] `rune_combination` - 룬 조합 효과
- [x] `arcane_flow`
- [x] `elemental_harmony` - 원소 조화 보너스

### 🟢 7. 광전사 (Berserker) - 0/5
- [x] 모든 특성 구현됨

### 🟢 8. 브레이커 (Breaker) - 0/5
- [x] `brv_crusher`
- [x] `break_master`
- [x] `shield_breaker`
- [x] `ruthless_breaker` - 브레이크 시 추가 데미지
- [x] `momentum_crush` - 연속 브레이크 시 파워 증가

### 🟢 9. 성직자 (Cleric) - 0/5
- [x] `healing_power` - 회복량 증가
- [x] `faith_shield` - 신앙 기반 방어
- [x] `divine_grace`
- [x] `resurrection_master` - 부활 효과 강화
- [x] `prayer_blessing` - 기도 버프 효과

### 🟢 10. 차원술사 (Dimensionist) - 0/5
- [x] 모든 특성 구현됨

### 🟢 11. 용기사 (Dragon Knight) - 0/5
- [x] `dragon_breath`
- [x] `burning_rage`
- [x] `dragon_scales`
- [x] `flame_wings` - 화염 날개 (비행/회피)
- [x] `inferno` - 인페르노 상태 (극도 화상)

### 🟢 12. 드루이드 (Druid) - 0/5
- [x] `animal_affinity` - 야수 친화력
- [x] `natures_blessing`
- [x] `plant_control` - 식물 조종
- [x] `natural_balance` - 자연 균형 보너스
- [x] `wild_instinct` - 야생 본능

### 🟢 13. 정령술사 (Elementalist) - 0/5
- [x] 모든 특성 구현됨

### 🟢 14. 기계공학자 (Engineer) - 0/5
- [x] 모든 특성 구현됨

### 🟢 15. 검투사 (Gladiator) - 0/5
- [x] 모든 특성 구현됨

### 🟢 16. 해커 (Hacker) - 0/5
- [x] 모든 특성 구현됨

### 🟢 17. 기사 (Knight) - 0/5
- [x] `glory_vow` - 영광의 서약 (duty 게이지)
- [x] `honor_guard` - 명예의 수호 (아군 보호)
- [x] `chivalry` - 기사도 (아군 버프)
- [x] `leadership` - 리더십 (파티 보너스)
- [x] `heroic_sacrifice` - 영웅적 희생 (사망 시 효과)

### 🟢 18. 몽크 (Monk) - 0/5
- [x] 모든 특성 구현됨

### 🟢 19. 네크로맨서 (Necromancer) - 0/5
- [x] `undead_commander` - 언데드 지휘관 (군단 관리)
- [x] `death_harvest` - 죽음 수확 (처치 시 효과)
- [x] `necromantic_power` - 강령술 위력 증가
- [x] `undead_sacrifice` - 언데드 희생 (군단 소모)
- [x] `legion_master` - 군단 마스터 (최대 언데드 증가)

### 🟢 20. 성기사 (Paladin) - 0/5
- [x] `divine_protection` - 신성한 보호 (피해 감소)
- [x] `holy_aura` - 성스러운 오라 (파티 버프)
- [x] `martyr_spirit` - 순교자 정신 (대신 피해받기)
- [x] `healing_light` - 치유의 빛 (자동 회복)
- [x] `righteous_fury` - 정의의 분노 (공격력 증가)

### 🟢 21. 철학자 (Philosopher) - 0/5
- [x] `power_mastery` - 힘의 숙련 (선택: 공격력)
- [x] `wisdom_mastery` - 지혜의 숙련 (선택: 마법력)
- [x] `sacrifice_mastery` - 희생의 숙련 (선택: HP 소모)
- [x] `truth_mastery` - 진리의 숙련 (선택: 균형)
- [x] `balanced_philosophy`

### 🟢 22. 해적 (Pirate) - 0/5
- [x] `treasure_hunter` - 보물 사냥꾼 (약탈 보너스)
- [x] `lucky_strike` - 행운의 일격 (크리티컬)
- [x] `greed` - 탐욕 (골드로 스탯 증가)
- [x] `pirate_fortune` - 해적의 행운 (확률 조작)
- [x] `dirty_fighting` - 더러운 싸움 (디버프)

### 🟢 23. 신관 (Priest) - 0/5
- [x] `divine_miracle` - 신성한 기적 (극대 회복)
- [x] `healing_mastery` - 치유 숙련
- [x] `blessing`
- [x] `holy_protection` - 신성 보호
- [x] `resurrection` - 부활 효과

### 🟢 24. 도적 (Rogue) - 0/5
- [x] `shadow_step` - 그림자 이동
- [x] `assassinate`
- [x] `swift_strikes` - 신속한 타격
- [x] `evasion_master` - 회피 숙련
- [x] `critical_finesse` - 크리티컬 정교함

### 🟢 25. 사무라이 (Samurai) - 0/5
- [x] `bushido`
- [x] `honor_vow` - 명예의 서약
- [x] `meditation` - 명상 (MP/BRV 회복)
- [x] `iaijutsu`
- [x] `iron_will` - 강철 의지 (상태이상 저항)

### 🟢 26. 무당 (Shaman) - 0/5
- [x] `spirit_sight` - 영혼 시야
- [x] `ancestral_protection`
- [x] `spirit_communion` - 영혼 교감
- [x] `fortune_telling` - 점술 (확률 조작)
- [x] `spirit_guide` - 영혼 안내

### 🟢 27. 저격수 (Sniper) - 0/5
- [x] 모든 특성 구현됨

### 🟢 28. 마검사 (Spellblade) - 0/5
- [x] 모든 특성 구현됨

### 🟢 29. 검성 (Sword Saint) - 0/5
- [x] `sword_energy` - 검기 (원거리 공격)
- [x] `rapid_slash` - 신속 베기 (다단 히트)
- [x] `blade_master`
- [x] `focus_strike` - 집중 일격
- [x] `counter_blade` - 반격 검술

### 🟢 30. 시간술사 (Time Mage) - 0/5
- [x] 모든 특성 구현됨

### 🟢 31. 전사 (Warrior) - 0/5
- [x] 모든 특성 구현됨

### 🟢 32. 뱀파이어 (Vampire) - 0/5
- [x] `sanguine_arts` - 혈액 예술 (흡혈 강화)
- [x] `vitality_overflow` - 생명력 넘침 (과잉 흡혈 시)
- [x] `bleeding_heart`
- [x] `shadow_veil`
- [x] `blood_empowerment` - 피로 강화 (흡혈 시 스탯)

### 🟢 33. 암흑기사 (Dark Knight) - 0/5
- [x] 모든 특성 구현됨

---

## 우선순위 구현 계획

### Phase 1: 공통 시스템 (High Priority)
- [ ] **원소 시스템** 완성 (정령술사, 드루이드, 용기사 등)
- [ ] **상태이상** 시스템 강화 (화상, 독, 기절 지속시간 등)

### Phase 2: 핵심 직업 (5개) - 총 23개 특성
1. [ ] **네크로맨서** (5개) - undead_legion 기믹
2. [ ] **성기사** (5개) - holy_system 기믹
3. [ ] **기사** (5개) - duty_system 기믹
4. [ ] **해적** (5개) - plunder_system 기믹
5. [ ] **철학자** (4개) - dilemma_choice 기믹

### Phase 3: 중요 직업 (7개) - 총 29개 특성
6. [ ] **성직자** (4개) - 회복 강화
7. [ ] **신관** (4개) - 회복/부활
8. [ ] **도적** (4개) - 기동력/크리티컬
9. [ ] **무당** (4개) - 토템 시스템
10. [ ] **검성** (4개) - 검기 시스템
11. [ ] **드루이드** (4개) - 변신 시스템
12. [ ] **사무라이** (3개) - 거합 시스템

### Phase 4: 나머지 직업 (7개) - 총 17개 특성
13. [ ] **뱀파이어** (3개) - 흡혈 강화
14. [ ] **암살자** (3개) - 은신 시스템
15. [ ] **배틀메이지** (3개) - 룬 시스템
16. [ ] **브레이커** (2개) - 브레이크 파워
17. [ ] **용기사** (2개) - 화염 강화
18. [ ] **궁수** (1개) - 콤보 시스템
19. [ ] **기타** (3개)

---

## 구현 노트

### trait_effects.py 체크 포인트
- `_check_condition()` - 조건 체크
- `calculate_stat_bonus()` - 스탯 보너스
- `apply_on_kill_effects()` - 처치 시 효과
- `calculate_damage_reduction()` - 피해 감소
- `calculate_critical_damage()` - 크리티컬 데미지

### combat_manager.py 체크 포인트
- `_execute_brv_attack()` - BRV 공격 시
- `_execute_hp_attack()` - HP 공격 시
- `_execute_skill()` - 스킬 사용 시
- 이벤트 핸들러들

### gimmick_updater.py 체크 포인트
- `on_turn_start()` - 턴 시작
- `on_turn_end()` - 턴 종료
- `on_skill_use()` - 스킬 사용
- `on_ally_attack()` - 아군 공격 시

---

**마지막 업데이트**: 2025-11-25
