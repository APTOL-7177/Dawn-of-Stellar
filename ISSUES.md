# Dawn of Stellar - 이슈 트래킹 문서

**작성일**: 2025-01-17
**버전**: 6.0.0
**상태**: 🔴 긴급 수정 필요

---

## 📋 목차

1. [긴급 이슈 (Critical)](#긴급-이슈-critical)
2. [고우선순위 이슈 (High Priority)](#고우선순위-이슈-high-priority)
3. [중간 우선순위 이슈 (Medium Priority)](#중간-우선순위-이슈-medium-priority)
4. [낮은 우선순위 이슈 (Low Priority)](#낮은-우선순위-이슈-low-priority)
5. [해결된 이슈](#해결된-이슈)

---

## 긴급 이슈 (Critical)

### 🔴 ISSUE-001: 기믹 UI 표시 불일치 (기믹 상세정보 없음)

**분류**: UI / 기믹 시스템
**우선순위**: 🔴 Critical
**발견일**: 2025-01-17
**영향 범위**: 기계공학자, 시간술사 외 다수 직업

#### 증상
- 전투 중 기믹 상세 정보를 확인하면 "기믹 상세 정보 없음"이라고 표시됨
- 기계공학자, 시간술사 등 여러 직업에서 발생

#### 원인
`src/ui/combat_ui.py`의 `_get_gimmick_detail()` 함수에서 처리하는 기믹 타입 이름과 실제 YAML 파일의 기믹 타입 이름이 불일치함

#### 불일치 목록

| 직업 | YAML 기믹 타입 | UI에서 처리하는 이름 | 상태 |
|------|----------------|---------------------|------|
| 기계공학자 | `heat_management` | `heat_gauge` | ❌ 불일치 |
| 버서커 | `madness_threshold` | `madness_gauge` | ❌ 불일치 |
| 정령술사 | `elemental_spirits` | `spirit_resonance` | ❌ 불일치 |
| 암살자 | `stealth_exposure` | `stealth_mastery` | ❌ 불일치 |
| 해커 | `multithread_system` | `hack_threading` | ❌ 불일치 |
| 검투사 | `crowd_cheer` | `cheer_gauge` | ❌ 불일치 |
| 시간술사 | `timeline_system` | ❌ 미처리 | ❌ 누락 |
| 궁수 | `support_fire` | `support_fire` | ✅ 일치 |
| 몽크 | `yin_yang_flow` | `yin_yang_flow` | ✅ 일치 |
| 차원술사 | `probability_distortion` | `probability_distortion` | ✅ 일치 |
| 뱀파이어 | `thirst_gauge` | `thirst_gauge` | ✅ 일치 |
| 철학자 | `dilemma_choice` | `dilemma_choice` | ✅ 일치 |
| 룬마스터 | `rune_resonance` | `rune_resonance` | ✅ 일치 |

#### 추가 미처리 기믹 타입 (33개 직업 중)

다음 기믹들은 `_get_gimmick_detail()`에서 전혀 처리되지 않음:

1. `sword_aura` (검성)
2. `duty_system` (기사)
3. `undead_legion` (네크로맨서)
4. `theft_system` (도적)
5. `shapeshifting_system` (드루이드)
6. `enchant_system` (마검사)
7. `totem_system` (무당)
8. `melody_system` (바드)
9. `break_system` (브레이커)
10. `iaijutsu_system` (사무라이)
11. `holy_system` (성직자)
12. `divinity_system` (성기사, 대마법사)
13. `elemental_counter` (엘리멘탈리스트)
14. `darkness_system` (암흑기사)
15. `alchemy_system` (연금술사)
16. `dragon_marks` (용기사)
17. `magazine_system` (저격수)
18. `stance_system` (전사)
19. `plunder_system` (해적)

#### 해결 방법

**방법 1: UI 코드 수정 (권장)**
- `src/ui/combat_ui.py`의 `_get_gimmick_detail()` 함수에서 처리하는 기믹 타입 이름을 YAML과 일치시킴
- 모든 기믹 타입에 대한 UI 표시 로직 추가

**방법 2: YAML 수정 (비권장)**
- 모든 캐릭터 YAML 파일의 기믹 타입을 UI에 맞게 변경
- 하지만 gimmick_updater.py도 함께 수정해야 하므로 비효율적

#### 관련 파일
- `src/ui/combat_ui.py` (2388-2571번 줄)
- `data/characters/*.yaml` (전체 33개)
- `src/character/gimmick_updater.py`

---

### 🔴 ISSUE-002: ATB 증가 스킬 효과 미적용

**분류**: 스킬 효과 / 전투 시스템
**우선순위**: 🔴 Critical
**발견일**: 2025-01-17
**영향 범위**: 시간술사 및 ATB 조작 스킬을 가진 모든 직업

#### 증상
- 시간술사의 "헤이스트" 스킬 사용 시 아군 ATB가 증가하지 않음
- 스킬 설명: "아군 ATB +100%"
- 실제: MP만 소모되고 ATB는 그대로 유지됨

#### 원인

**스킬 구현 확인** (`src/character/skills/job_skills/time_mage_skills.py:109`)

```python
haste = Skill("time_mage_haste", "헤이스트", "아군 ATB +100%, 타임라인 +1 (미래)")
haste.effects = [
    BuffEffect(BuffType.SPEED_UP, 1.0, duration=3),  # ← 문제: 속도 스탯만 증가
    GimmickEffect(GimmickOperation.ADD, "timeline", 1, max_value=5)
]
```

**문제점**:
- `BuffEffect(BuffType.SPEED_UP, 1.0, duration=3)`은 **속도 스탯을 100% 증가**시키는 효과
- 이것은 ATB 증가 속도를 빠르게 만들지만, **ATB를 즉시 증가시키는 것은 아님**
- 사용자가 기대하는 것: ATB 게이지를 즉시 +100% (또는 +1000)
- 실제 동작: 속도 스탯이 증가하여 다음 턴부터 ATB가 빠르게 차오름

#### 영향받는 스킬 목록

| 스킬 | 직업 | 설명 | 현재 구현 | 기대 동작 |
|------|------|------|-----------|-----------|
| 헤이스트 | 시간술사 | ATB +100% | 속도 스탯 +100% | ATB 게이지 즉시 증가 |
| 시간 도약 | 시간술사 | 속도 +200% 1턴 | 속도 스탯 +200% | ATB 게이지 대폭 증가 |
| 슬로우 | 시간술사 | 적 ATB -50% | 속도 스탯 -50% | 적 ATB 게이지 감소 |

#### 해결 방법

**방법 1: 새로운 Effect 타입 추가 (권장)**

`src/character/skills/effects/atb_effect.py` 생성:

```python
class ATBEffect(SkillEffect):
    """ATB 게이지를 직접 조작하는 효과"""
    def __init__(self, atb_change: int, is_percentage: bool = False):
        super().__init__(EffectType.ATB)
        self.atb_change = atb_change  # 고정값 또는 %
        self.is_percentage = is_percentage

    def execute(self, user, target, context):
        if self.is_percentage:
            # ATB 최대치(2000)의 % 만큼 증가/감소
            change = int(2000 * self.atb_change)
        else:
            change = self.atb_change

        target.atb = max(0, min(2000, target.atb + change))
```

**헤이스트 스킬 수정**:

```python
haste.effects = [
    ATBEffect(1000),  # ATB +1000 (절반 충전)
    BuffEffect(BuffType.SPEED_UP, 1.0, duration=3),  # 속도도 증가
    GimmickEffect(GimmickOperation.ADD, "timeline", 1, max_value=5)
]
```

**방법 2: GimmickEffect로 ATB 조작 (임시 해결책)**

```python
haste.effects = [
    GimmickEffect(GimmickOperation.ADD, "atb", 1000, max_value=2000, apply_to_target=True),
    BuffEffect(BuffType.SPEED_UP, 1.0, duration=3),
    GimmickEffect(GimmickOperation.ADD, "timeline", 1, max_value=5)
]
```

#### 관련 파일
- `src/character/skills/job_skills/time_mage_skills.py`
- `src/character/skills/effects/buff_effect.py`
- `src/combat/atb_system.py`
- 필요 시 생성: `src/character/skills/effects/atb_effect.py`

---

## 고우선순위 이슈 (High Priority)

### 🟠 ISSUE-003: 스킬 효과 적용 여부 불확실

**분류**: 스킬 효과 / 전투 시스템
**우선순위**: 🟠 High
**발견일**: 2025-01-17
**영향 범위**: 전체 직업

#### 증상
- 일부 스킬 사용 시 MP만 소모되고 효과가 적용되는지 불확실함
- UI에 스킬 효과 적용 피드백이 부족함

#### 잠재적 문제 영역

1. **BuffEffect 적용 확인 부족**
   - 버프가 적용되었는지 로그나 UI에 표시 없음
   - 전투 로그에 버프 적용 메시지 미비

2. **GimmickEffect 실패 시 피드백 없음**
   - GimmickEffect가 실패해도 사용자에게 알림 없음
   - 예: 최대값 도달 시, 조건 미충족 시

3. **HealEffect 적용 확인 어려움**
   - 회복량이 UI에 즉시 표시되지 않을 수 있음

#### 해결 방법

**전투 로그 강화**:
- 모든 Effect 실행 시 결과를 전투 로그에 명확히 표시
- 버프/디버프 아이콘 UI 추가
- 스킬 효과 팝업 메시지 추가

#### 관련 파일
- `src/combat/combat_manager.py`
- `src/ui/combat_ui.py`
- `src/character/skills/effects/*.py`

---

### 🟠 ISSUE-004: 기믹 업데이트 로직 누락 가능성

**분류**: 기믹 시스템
**우선순위**: 🟠 High
**발견일**: 2025-01-17
**영향 범위**: 미구현 기믹을 가진 직업들

#### 증상
- `gimmick_updater.py`에 구현된 기믹은 9개뿐
- 나머지 24개 기믹은 업데이트 로직이 없어 제대로 작동하지 않을 수 있음

#### 구현된 기믹 (9개)

1. ✅ `heat_management` (기계공학자)
2. ✅ `timeline_system` (시간술사)
3. ✅ `yin_yang_flow` (몽크)
4. ✅ `madness_threshold` (버서커)
5. ✅ `thirst_gauge` (뱀파이어)
6. ✅ `probability_distortion` (차원술사)
7. ✅ `stealth_exposure` (암살자)
8. ✅ `magazine_system` (저격수)
9. ✅ `support_fire` (궁수)

#### 미구현 기믹 (24개)

10. ❌ `sword_aura` (검성)
11. ❌ `crowd_cheer` (검투사)
12. ❌ `duty_system` (기사)
13. ❌ `undead_legion` (네크로맨서)
14. ❌ `theft_system` (도적)
15. ❌ `shapeshifting_system` (드루이드)
16. ❌ `enchant_system` (마검사)
17. ❌ `totem_system` (무당)
18. ❌ `melody_system` (바드)
19. ❌ `rune_resonance` (룬마스터)
20. ❌ `break_system` (브레이커)
21. ❌ `iaijutsu_system` (사무라이)
22. ❌ `holy_system` (성직자)
23. ❌ `divinity_system` (성기사, 대마법사)
24. ❌ `elemental_counter` (엘리멘탈리스트)
25. ❌ `darkness_system` (암흑기사)
26. ❌ `alchemy_system` (연금술사)
27. ❌ `dragon_marks` (용기사)
28. ❌ `stance_system` (전사)
29. ❌ `elemental_spirits` (정령술사)
30. ❌ `plunder_system` (해적)
31. ❌ `multithread_system` (해커)
32. ❌ `dilemma_choice` (철학자) - 부분 구현

#### 영향
- 미구현 기믹을 가진 직업들은 기믹 시스템이 작동하지 않음
- 스킬이 기믹을 변경해도 자동 업데이트가 없음
- 특성(Trait)이 기믹 상태에 의존하는 경우 작동하지 않음

#### 해결 방법

1. 각 기믹별로 `_update_XXX()` 메서드 구현
2. `on_turn_start()`, `on_turn_end()` 등에 기믹 타입 추가
3. 기믹 상태 체커 구현 (`is_in_optimal_zone()` 등)

#### 관련 파일
- `src/character/gimmick_updater.py`
- `src/character/skills/job_skills/*_skills.py`

---

## 중간 우선순위 이슈 (Medium Priority)

### 🟡 ISSUE-005: 조건부 데미지 보너스 미작동 가능성

**분류**: 데미지 계산 / 스킬 효과
**우선순위**: 🟡 Medium
**발견일**: 2025-01-17
**영향 범위**: 조건부 보너스를 가진 스킬들

#### 증상
- 일부 스킬은 특정 조건에서 데미지 보너스를 받아야 하지만 작동하지 않을 수 있음

#### 예시 스킬

**기계공학자 - 과열 포격** (`engineer_skills.py:31-39`):

```python
overload_blast = Skill("engineer_overload_blast", "과열 포격",
                      "위험 구간(80+)에서 배율 3.5, 열 +35")
overload_blast.effects = [
    DamageEffect(DamageType.BRV, 2.5,
                conditional_bonus={"condition": "danger_zone", "multiplier": 1.4}),
    # 위험 구간(heat >= 80)에서 2.5 * 1.4 = 3.5 배율
]
```

**시간술사 - 시간의 균형** (`time_mage_skills.py:95-103`):

```python
balance = Skill("time_mage_balance", "시간의 균형",
               "현재(0) 상태에서만 발동, 배율 4.5 대량 피해")
balance.effects = [
    DamageEffect(DamageType.BRV_HP, 4.5, stat_type="magical",
                conditional_bonus={"condition": "at_present", "multiplier": 1.0})
]
```

#### 확인 필요 사항

1. `DamageCalculator`가 `conditional_bonus`를 올바르게 처리하는가?
2. `gimmick_bonus`도 올바르게 처리되는가?
3. `GimmickStateChecker`의 조건 체크 함수들이 작동하는가?

#### 관련 파일
- `src/combat/damage_calculator.py`
- `src/character/skills/effects/damage_effect.py`
- `src/character/gimmick_updater.py` (GimmickStateChecker)

---

### 🟡 ISSUE-006: 스킬 쿨다운 시스템 작동 확인 필요

**분류**: 스킬 시스템
**우선순위**: 🟡 Medium
**발견일**: 2025-01-17
**영향 범위**: 쿨다운을 가진 모든 스킬

#### 증상
- 쿨다운이 있는 스킬이 연속으로 사용 가능한지 확인 필요

#### 확인 필요 사항

1. 쿨다운 감소가 턴마다 올바르게 적용되는가?
2. 쿨다운 중인 스킬은 UI에서 비활성화되는가?
3. 궁극기(is_ultimate=True) 쿨다운이 더 긴가?

#### 관련 파일
- `src/character/skills/skill.py`
- `src/combat/combat_manager.py`
- `src/ui/combat_ui.py`

---

## 낮은 우선순위 이슈 (Low Priority)

### 🟢 ISSUE-007: 기믹 UI 시각화 개선

**분류**: UI / UX
**우선순위**: 🟢 Low
**발견일**: 2025-01-17
**영향 범위**: 전체

#### 개선 사항
- 기믹 게이지 바 그래픽 추가
- 최적/위험 구간 색상 구분
- 기믹 상태에 따른 이모지/아이콘 추가

---

### 🟢 ISSUE-008: 스킬 설명 개선

**분류**: UI / 문서화
**우선순위**: 🟢 Low
**발견일**: 2025-01-17
**영향 범위**: 전체

#### 개선 사항
- 스킬 효과 설명을 더 명확하게
- ATB 증가 vs 속도 증가 구분
- 조건부 효과 명시

---

## 해결된 이슈

### ✅ RESOLVED-001: 궁수 지원사격 데미지 미적용

**해결일**: 2025-01-17
**커밋**: `b9d42fd`

#### 문제
- 궁수의 지원사격이 로그만 출력되고 실제 데미지를 입히지 않음

#### 해결
- `gimmick_updater.py`에서 `DamageCalculator`를 사용하여 실제 BRV 데미지 계산
- 입힌 데미지만큼 궁수 BRV 회복 구현
- `combat_manager.py`에서 `on_ally_attack`에 `target` 매개변수 전달

---

### ✅ RESOLVED-002: 궁수 마킹 UI 오류

**해결일**: 2025-01-17
**커밋**: `809107c`

#### 문제
- 마킹된 아군이 0명으로 표시됨
- `marked_allies_count` 속성이 존재하지 않음

#### 해결
- `combat_ui.py`에서 동적으로 `mark_slot_*` 속성을 스캔하여 카운트

---

### ✅ RESOLVED-003: GimmickEffect apply_to_target 미작동

**해결일**: 2025-01-17
**커밋**: 이전

#### 문제
- 궁수가 아군에게 마킹 스킬 사용 시 자기 자신에게 적용됨

#### 해결
- `gimmick_effect.py`에 `apply_to_target` 매개변수 추가
- `apply_to_target=True`일 때 target에 효과 적용

---

## 📊 이슈 통계

- **총 이슈 수**: 8개
- **긴급 (Critical)**: 2개 🔴
- **고우선순위 (High)**: 2개 🟠
- **중간 (Medium)**: 2개 🟡
- **낮음 (Low)**: 2개 🟢
- **해결됨**: 3개 ✅

---

## 🔧 수정 권장 순서

1. **ISSUE-001**: 기믹 UI 표시 불일치 (1-2시간 소요 예상)
2. **ISSUE-002**: ATB 증가 스킬 효과 미적용 (2-3시간 소요 예상)
3. **ISSUE-004**: 기믹 업데이트 로직 누락 (대규모 작업, 10-15시간 소요 예상)
4. **ISSUE-003**: 스킬 효과 적용 피드백 개선 (3-4시간 소요 예상)
5. **ISSUE-005**: 조건부 데미지 보너스 확인 (1-2시간 소요 예상)
6. **ISSUE-006**: 스킬 쿨다운 시스템 확인 (1시간 소요 예상)

---

## 📝 참고 사항

### 테스트 방법

각 이슈 수정 후 다음을 테스트:

1. 해당 직업으로 전투 시작
2. 기믹 UI 확인 (G 키)
3. 문제 스킬 사용
4. 효과 적용 확인
5. 로그 확인

### 로그 확인

```bash
# 전투 로그 실시간 확인
tail -f logs/combat_latest.log

# 기믹 관련 로그만 필터링
grep "gimmick" logs/combat_latest.log
```

---

**마지막 업데이트**: 2025-01-17
**다음 리뷰 예정일**: 이슈 수정 후
