# Add Job Command

새로운 직업(Job)을 프로젝트에 추가합니다.

## 사용법
```
/add-job <job_name> [gimmick_type]
```

예시:
- `/add-job ninja` - 닌자 직업 추가 (기본 템플릿)
- `/add-job elementalist elemental_spirits` - 정령술사 + 정령 기믹 추가

## 실행 내용

### 1. 캐릭터 YAML 파일 생성
`data/characters/<job_name>.yaml` 생성:

```yaml
class_name: "<직업명>"
description: "<직업 설명>"

base_stats:
  hp: 100
  mp: 50
  strength: 10
  defense: 10
  magic: 10
  spirit: 10
  speed: 10
  luck: 5
  evasion: 1.0
  max_brv: 2.0

traits:
- id: <job_name>_master
  name: <직업> 달인
  description: <조건부 효과>
  type: conditional
  conditions:
    # 조건 추가
  effects:
    damage_bonus: 0.2

- id: <job_name>_passive
  name: 패시브 특성
  type: passive
  effects:
    stat_multiplier:
      strength: 1.1

gimmick:
  type: <gimmick_type>
  name: <기믹 이름>
  description: <기믹 설명>
  # 기믹별 파라미터 추가

skills:
- <job_name>_skill_1
- <job_name>_skill_2
- <job_name>_skill_3
- <job_name>_skill_4
- <job_name>_skill_5
- <job_name>_skill_6
- <job_name>_skill_7
- <job_name>_skill_8
- <job_name>_skill_9
- <job_name>_ultimate
```

### 2. 스킬 파일 생성
`src/character/skills/job_skills/<job_name>_skills.py` 생성:

```python
"""<Job Name> Skills - <직업명> 스킬 (<기믹> 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost

def create_<job_name>_skills():
    """<직업명> 10개 스킬 생성"""

    # 1. 기본 BRV 공격
    basic_brv = Skill(f"<job_name>_basic_brv", "기본 공격", "기본 BRV 공격")
    basic_brv.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="physical")
    ]
    basic_brv.costs = []

    # 2. 기본 HP 공격
    basic_hp = Skill(f"<job_name>_basic_hp", "강타", "기본 HP 공격")
    basic_hp.effects = [
        DamageEffect(DamageType.HP, 1.3, stat_type="physical")
    ]
    basic_hp.costs = []

    # 3-9. 특수 스킬들
    # 기믹 활용 스킬 추가

    # 10. 궁극기
    ultimate = Skill(f"<job_name>_ultimate", "궁극기", "강력한 궁극기")
    ultimate.effects = [
        DamageEffect(DamageType.BRV_HP, 3.0, stat_type="physical"),
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=5)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 8

    return [basic_brv, basic_hp, ..., ultimate]

def register_<job_name>_skills(skill_manager):
    """<직업명> 스킬 등록"""
    skills = create_<job_name>_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
```

### 3. 기믹 시스템 추가 (선택)

`src/character/gimmick_updater.py`에 추가:

```python
# on_turn_start 또는 on_turn_end에 추가
elif gimmick_type == "<gimmick_type>":
    GimmickUpdater._update_<gimmick_name>(character)

# 업데이트 메서드 구현
@staticmethod
def _update_<gimmick_name>(character):
    """<기믹> 업데이트 로직"""
    # 기믹 값 업데이트
    current_value = getattr(character, 'gimmick_value', 0)
    character.gimmick_value = min(100, current_value + 10)
    logger.debug(f"{character.name} <기믹> +10 (총: {character.gimmick_value})")
```

### 4. 특성 효과 추가 (선택)

`src/character/trait_effects.py`에 추가:

```python
"<job_name>_master": [
    TraitEffect(
        trait_id="<job_name>_master",
        effect_type=TraitEffectType.DAMAGE_MULTIPLIER,
        value=1.20,
        condition="<condition_name>",
        metadata={"threshold": 2}
    )
],
```

### 5. 테스트 파일 생성

`tests/test_<job_name>.py` 생성:

```python
"""<Job Name> Test - <직업명> 테스트"""
import pytest
from src.character.character import Character

def test_<job_name>_basic():
    """<직업명> 기본 테스트"""
    character = Character("<직업명>", "<job_name>")

    assert character.class_name == "<직업명>"
    assert character.gimmick_type == "<gimmick_type>"
    assert len(character.skills) == 10

def test_<job_name>_gimmick():
    """<직업명> 기믹 테스트"""
    character = Character("<직업명>", "<job_name>")

    # 기믹 초기값 확인
    assert hasattr(character, 'gimmick_value')
    assert character.gimmick_value == 0
```

## 32가지 기믹 타입

구현됨 (9개):
- `heat_management` - 열 관리
- `timeline_system` - 타임라인
- `yin_yang_flow` - 음양 기
- `madness_threshold` - 광기 역치
- `thirst_gauge` - 갈증 게이지
- `probability_distortion` - 확률 왜곡
- `stealth_exposure` - 은신-노출
- `magazine_system` - 탄창 시스템
- `support_fire` - 지원사격

미구현 (23개):
- `alchemy_system` - 연금술
- `break_system` - BREAK 특화
- `crowd_cheer` - 관중 환호
- `darkness_system` - 어둠의 힘
- `dilemma_choice` - 딜레마 선택
- `divinity_system` - 신앙의 힘
- `dragon_marks` - 용의 각인
- `duty_system` - 의무 시스템
- `elemental_counter` - 원소 조합
- `elemental_spirits` - 정령 소환
- `enchant_system` - 마법 부여
- `holy_system` - 성스러운 힘
- `iaijutsu_system` - 발도술
- `melody_system` - 음악의 선율
- `multithread_system` - 멀티스레드
- `plunder_system` - 약탈
- `rune_resonance` - 룬 공명
- `shapeshifting_system` - 변신
- `stance_system` - 스탠스 전환
- `sword_aura` - 검기
- `theft_system` - 도둑질
- `totem_system` - 토템
- `undead_legion` - 언데드 군단

## 체크리스트

- [ ] YAML 파일 생성
- [ ] 스킬 파일 생성
- [ ] 기믹 업데이트 추가 (있다면)
- [ ] 특성 효과 추가 (있다면)
- [ ] 테스트 파일 생성
- [ ] 스킬 등록 (`src/character/skills/__init__.py`)
- [ ] 테스트 실행 (`/test`)
- [ ] Git 커밋

## 참고 자료

- 기믹 설계: `COMPLETE_JOB_SYSTEM_DESIGN.md`
- 기믹 UI: `GIMMICK_UI_DESIGN.md`
- 직업 재설계: `JOB_MECHANISM_REDESIGN.md`
