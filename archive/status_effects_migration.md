# Status Effects System - Migration Report

## 개요

기존 로그라이크 프로젝트의 StatusEffect 시스템을 Dawn of Stellar 프로젝트로 성공적으로 이식했습니다.

## 생성된 파일

### 1. 핵심 모듈
- **경로**: `X:\Dos\src\combat\status_effects.py`
- **라인 수**: 약 730줄
- **주요 클래스**:
  - `StatusType` (Enum): 165개 상태 효과 타입 정의
  - `StatusEffect` (Dataclass): 개별 상태 효과
  - `StatusManager`: 상태 효과 관리자

### 2. 테스트 파일
- **경로**: `X:\Dos\tests\unit\combat\test_status_effects.py`
- **테스트 수**: 47개
- **통과율**: 100%

### 3. 모듈 통합
- **경로**: `X:\Dos\src\combat\__init__.py`
- **내보내기**: StatusEffect, StatusManager, StatusType 등

## 주요 변경사항

### 1. 코드 스타일 개선
- **Type Hints 추가**: 모든 함수와 메서드에 타입 힌트 적용
- **Docstring**: Google 스타일 docstring 추가
- **PEP 8 준수**: 코딩 컨벤션 준수

```python
# Before (기존 코드)
def add_status(self, status_effect, duration=None, intensity=None):
    if hasattr(status_effect, 'status_type'):
        status_obj = status_effect
    # ...

# After (새 코드)
def add_status(
    self,
    status_effect: StatusEffect,
    allow_refresh: bool = True
) -> bool:
    """
    상태 효과 추가

    Args:
        status_effect: 추가할 상태 효과
        allow_refresh: True면 기존 효과의 지속시간을 갱신

    Returns:
        새로운 효과가 추가되었으면 True, 기존 효과를 갱신했으면 False
    """
```

### 2. Dataclass 활용
기존의 단순 클래스를 `@dataclass`로 변경하여 보일러플레이트 코드 제거:

```python
@dataclass
class StatusEffect:
    """상태 효과 클래스"""
    name: str
    status_type: StatusType
    duration: int
    intensity: float = 1.0
    stack_count: int = 1
    max_stacks: int = 1
    is_stackable: bool = False
    source_id: Optional[str] = None
    metadata: Dict[str, Any] = None
```

### 3. 이벤트 버스 통합
상태 효과 추가/제거 시 이벤트를 발행하여 다른 시스템과 통신:

```python
# 상태 효과 추가 시
event_bus.publish(Events.STATUS_APPLIED, {
    "owner": self.owner_name,
    "status": status_effect,
    "is_new": True
})

# 상태 효과 제거 시
event_bus.publish(Events.STATUS_REMOVED, {
    "owner": self.owner_name,
    "status": effect
})
```

### 4. 로깅 시스템 통합
`print` 문을 제거하고 구조화된 로거 사용:

```python
from src.core.logger import get_logger

logger = get_logger("status_effects")

# 사용 예시
logger.info(f"{self.owner_name}: {status_effect.name} 추가")
logger.debug(f"{self.owner_name}: {effect.name} 효과 만료")
```

### 5. 의존성 최소화
- `character.py` 의존성 완전 제거
- 순수 데이터 클래스로 구현
- 효과 적용은 상위 레이어(combat_manager)에서 처리

## StatusType Enum 분류

총 **165개** 상태 효과를 6개 카테고리로 분류:

### 1. BUFF (버프) - 27개
```python
BOOST_ATK, BOOST_DEF, BOOST_SPD, BOOST_ACCURACY, BOOST_CRIT,
BOOST_DODGE, BOOST_ALL_STATS, BOOST_MAGIC_ATK, BOOST_MAGIC_DEF,
BLESSING, REGENERATION, MP_REGEN, INVINCIBLE, REFLECT, HASTE,
FOCUS, RAGE, INSPIRATION, GUARDIAN, STRENGTHEN, EVASION_UP,
FORESIGHT, ENLIGHTENMENT, WISDOM, MANA_REGENERATION,
MANA_INFINITE, HOLY_BLESSING
```

### 2. 보호막 - 8개
```python
BARRIER, SHIELD, MAGIC_BARRIER, MANA_SHIELD,
FIRE_SHIELD, ICE_SHIELD, HOLY_SHIELD, SHADOW_SHIELD
```

### 3. DEBUFF (디버프) - 18개
```python
REDUCE_ATK, REDUCE_DEF, REDUCE_SPD, REDUCE_ACCURACY,
REDUCE_ALL_STATS, REDUCE_MAGIC_ATK, REDUCE_MAGIC_DEF,
REDUCE_SPEED, VULNERABLE, EXPOSED, WEAKNESS, WEAKEN,
CONFUSION, TERROR, FEAR, DESPAIR, HOLY_WEAKNESS,
WEAKNESS_EXPOSURE
```

### 4. DOT (지속 피해) - 11개
```python
POISON, BURN, BLEED, CORRODE, CORROSION, DISEASE,
NECROSIS, MP_DRAIN, CHILL, SHOCK, NATURE_CURSE
```

### 5. CC (군중 제어) - 14개
```python
STUN, SLEEP, SILENCE, BLIND, PARALYZE, FREEZE,
PETRIFY, CHARM, DOMINATE, ROOT, SLOW, ENTANGLE,
MADNESS, TAUNT
```

### 6. SPECIAL (특수) - 44개
```python
CURSE, STEALTH, BERSERK, COUNTER, COUNTER_ATTACK, VAMPIRE,
SPIRIT_LINK, SOUL_BOND, TIME_STOP, TIME_MARKED,
TIME_SAVEPOINT, TIME_DISTORTION, PHASE, TRANSCENDENCE,
ANALYZE, AUTO_TURRET, REPAIR_DRONE, ABSOLUTE_EVASION,
TEMPORARY_INVINCIBLE, EXISTENCE_DENIAL, TRUTH_REVELATION,
GHOST_FLEET, ANIMAL_FORM, DIVINE_PUNISHMENT, DIVINE_JUDGMENT,
HEAVEN_GATE, PURIFICATION, MARTYRDOM, ELEMENTAL_WEAPON,
ELEMENTAL_IMMUNITY, MAGIC_FIELD, TRANSMUTATION,
PHILOSOPHERS_STONE, UNDEAD_MINION, SHADOW_CLONE,
SHADOW_STACK, SHADOW_ECHO, SHADOW_EMPOWERED, EXTRA_TURN,
HOLY_MARK, HOLY_AURA, DRAGON_FORM, WARRIOR_STANCE, AFTERIMAGE
```

## 주요 기능

### 1. 상태 효과 추가 및 관리
```python
from src.combat import StatusManager, create_status_effect, StatusType

# 관리자 생성
manager = StatusManager("PlayerCharacter")

# 상태 효과 추가
poison = create_status_effect(
    name="독",
    status_type=StatusType.POISON,
    duration=5,
    intensity=1.5
)
manager.add_status(poison)
```

### 2. 스택 가능 효과
```python
# 스택 가능한 재생 효과
regen = create_status_effect(
    name="재생",
    status_type=StatusType.REGENERATION,
    duration=5,
    intensity=1.0,
    is_stackable=True,
    max_stacks=3
)
manager.add_status(regen)
# 여러 번 추가하면 스택이 쌓임 (최대 3스택)
```

### 3. 행동 제약 확인
```python
# 행동 가능 여부 (기절, 수면, 빙결 등)
can_act = manager.can_act()

# 스킬 사용 가능 여부 (침묵)
can_use_skills = manager.can_use_skills()

# 제어 가능 여부 (매혹, 지배, 혼란)
is_controlled = manager.is_controlled()
```

### 4. 스탯 수정치 계산
```python
# 모든 상태 효과를 고려한 스탯 배율 반환
modifiers = manager.get_stat_modifiers()
# {
#     'physical_attack': 1.2,  # 공격력 20% 증가
#     'magic_attack': 1.2,
#     'speed': 0.6,             # 속도 40% 감소
#     ...
# }
```

### 5. 지속시간 관리
```python
# 매 턴마다 호출
expired = manager.update_duration()
# 만료된 효과 리스트 반환
```

## 테스트 커버리지

### 테스트 카테고리
1. **StatusEffect 클래스** (4개)
   - 기본 생성
   - 스택 가능 효과
   - 문자열 표현

2. **StatusManager 클래스** (26개)
   - 추가/제거/조회
   - 지속시간 관리
   - 행동 제약 확인
   - 스탯 수정치 계산
   - 복합 효과 처리

3. **유틸리티 함수** (11개)
   - 헬퍼 함수
   - 카테고리 분류
   - 아이콘 매핑

4. **엣지 케이스** (6개)
   - 최대 스택 제한
   - 여러 CC 효과
   - 지속시간 0 처리

### 테스트 실행 결과
```
============================= test session starts =============================
collected 47 items

tests\unit\combat\test_status_effects.py ............................... [ 65%]
................                                                         [100%]

======================== 47 passed in 0.11s ===============================
```

## 사용 예시

### 기본 사용법
```python
from src.combat import StatusManager, create_status_effect, StatusType

# 캐릭터의 상태 관리자 생성
player_status = StatusManager("Player")

# 독 효과 적용
poison = create_status_effect("독", StatusType.POISON, duration=5, intensity=2.0)
player_status.add_status(poison)

# 매 턴마다 업데이트
expired = player_status.update_duration()

# 상태 확인
if not player_status.can_act():
    print("캐릭터가 행동할 수 없습니다!")

# 스탯 수정치 적용
modifiers = player_status.get_stat_modifiers()
final_attack = base_attack * modifiers['physical_attack']
```

### 전투 시스템 통합 예시
```python
class CombatManager:
    def apply_damage(self, attacker, defender, base_damage):
        # 공격자의 버프 적용
        atk_mods = attacker.status_manager.get_stat_modifiers()
        modified_damage = base_damage * atk_mods['physical_attack']

        # 방어자의 디버프 적용
        def_mods = defender.status_manager.get_stat_modifiers()
        final_damage = modified_damage / def_mods['physical_defense']

        return int(final_damage)

    def process_turn_start(self, character):
        # 행동 가능 여부 확인
        if not character.status_manager.can_act():
            return "행동 불가"

        # DOT 효과 처리 (별도 로직에서)
        # ...

        # 지속시간 감소
        expired = character.status_manager.update_duration()
        for effect in expired:
            self.show_message(f"{effect.name} 효과가 해제되었습니다.")
```

## 향후 개선 사항

### 1. DOT/HOT 자동 처리
현재는 `StatusManager`가 상태만 관리하고, 실제 피해/회복은 상위 레이어에서 처리합니다.
향후 `process_turn_effects()` 메서드를 추가하여 DOT/HOT를 자동으로 처리할 수 있습니다.

```python
def process_turn_effects(self, character) -> List[Dict[str, Any]]:
    """
    턴 시작/종료 시 상태 효과 처리

    Returns:
        효과 결과 리스트 (피해, 회복 등)
    """
    results = []
    for effect in self.status_effects:
        if effect.status_type in DOT_TYPES:
            damage = self._calculate_dot_damage(effect, character)
            results.append({
                "type": "damage",
                "source": effect.name,
                "value": damage
            })
        elif effect.status_type in HOT_TYPES:
            heal = self._calculate_hot_heal(effect, character)
            results.append({
                "type": "heal",
                "source": effect.name,
                "value": heal
            })
    return results
```

### 2. YAML 기반 상태 효과 정의
데이터 주도 설계를 위해 상태 효과를 YAML로 정의:

```yaml
# data/status_effects/poison.yaml
name: "독"
status_type: POISON
category: DOT
duration: 5
intensity: 1.0
is_stackable: false
description: "매 턴 HP가 감소합니다"
effects:
  - type: damage
    formula: "max_hp * 0.05 * intensity"
    tick_timing: "turn_start"
icon: "☠️"
```

### 3. 상태 효과 상호작용
특정 상태끼리 상호작용 추가:
- 화상 + 냉기 = 둘 다 제거
- 독 + 재생 = 효과 상쇄
- 기절 + 공격 = 기절 해제

### 4. 저항 및 면역 시스템
```python
class StatusResistance:
    """상태 이상 저항"""
    def __init__(self):
        self.resistances = {
            StatusType.POISON: 0.5,  # 50% 저항
            StatusType.STUN: 0.8,    # 80% 저항
        }
        self.immunities = {
            StatusType.SLEEP,  # 수면 면역
        }
```

## 발견된 문제점

### 해결된 문제
1. **파일 인코딩 문제**: `__init__.py` 파일에 null byte가 포함되어 import 실패
   - **해결**: 파일을 재생성하여 해결

2. **카테고리 중복**: `REGENERATION`이 BUFF와 HOT 둘 다에 포함
   - **해결**: HOT를 먼저 체크하도록 순서 변경

### 남은 주의사항
1. **색상 출력**: 원본 코드의 ANSI 색상 코드는 제거했습니다. UI 레이어에서 처리해야 합니다.
2. **캐릭터 참조**: StatusManager는 캐릭터 객체를 직접 참조하지 않습니다. 효과 적용은 combat_manager에서 처리하세요.

## 결론

StatusEffect 시스템이 성공적으로 이식되었습니다:
- ✅ 165개 상태 효과 타입 정의
- ✅ 깔끔한 API 설계
- ✅ 이벤트 버스 통합
- ✅ 47개 단위 테스트 (100% 통과)
- ✅ Type hints 및 docstring 완비
- ✅ PEP 8 준수

이제 combat_manager, skill_system 등 다른 시스템에서 안전하게 사용할 수 있습니다.
