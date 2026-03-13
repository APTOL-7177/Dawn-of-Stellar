# 콤보 스킬 시스템 설계 (ZZZ 지원 시스템 참고)

## 개요

Zenless Zone Zero의 지원 시스템을 참고하여 **Dawn of Stellar**에 역할군별 차별화된 콤보 스킬 시스템을 구현합니다.
턴제 ATB 전투에 맞게 재해석하여, 아군 간 연계를 통한 전술적 깊이를 추가합니다.

---

## 1. 핵심 컨셉

### ZZZ 지원 시스템 vs Dawn of Stellar 콤보 시스템

| 요소 | ZZZ | Dawn of Stellar (제안) |
|------|-----|------------------------|
| **전투 방식** | 실시간 액션 | 턴제 ATB |
| **트리거** | 회피/패리/특수 공격 | 특정 스킬/상태 태그 |
| **역할군** | 공격/방어/지원/이상 | Attacker/Defender/Support/Specialist |
| **효과** | 즉시 교체 + 연계 공격 | ATB 게이지 소모 + 추가 행동 |
| **자원 소비** | 없음 (쿨다운) | ATB 게이지 부분 소비 |

### 핵심 메커니즘: **연계 태그(Chain Tag) 시스템**

1. **스킬에 태그 부여**: 각 스킬은 `setup_tag`(셋업 태그) 또는 `trigger_tag`(트리거 태그) 보유
2. **연계 조건**: 이전 턴에 특정 `setup_tag`가 적용된 대상에게 대응하는 `trigger_tag` 스킬 사용 시 콤보 발동
3. **역할군별 차별화**: 역할군에 따라 다른 연계 효과 제공

---

## 2. 역할군별 콤보 스킬 설계

### 2.1 Attacker (공격형)
**컨셉**: 연쇄 공격으로 대미지 극대화

#### 콤보 타입
1. **체인 어택 (Chain Attack)**
   - **조건**: 아군이 `[STAGGER]` 태그 적용 → Attacker가 `[ASSAULT]` 태그 스킬 사용
   - **효과**:
     - 추가 BRV 공격 (원래 데미지의 50%)
     - ATB 소모 -30%
     - 크리티컬률 +20%
   - **예시**: 전사의 "강타"로 적 경직 → 궁수의 "관통 사격"으로 추가 데미지

2. **익스플로잇 (Exploit)**
   - **조건**: 적이 디버프/BREAK 상태 → `[EXPLOIT]` 태그 스킬 사용
   - **효과**:
     - 디버프당 데미지 +15% (최대 +45%)
     - BREAK 중이면 wound damage 2배
   - **예시**: 암살자의 "독 적용" → 저격수의 "치명타"로 극딜

### 2.2 Defender (방어형)
**컨셉**: 위기 상황 대응 및 아군 보호

#### 콤보 타입
1. **카운터 어시스트 (Counter Assist)**
   - **조건**: 아군이 피격당함 → Defender의 ATB >= 500 → 자동 개입
   - **효과**:
     - 아군 대신 데미지 50% 감소하여 받음
     - 즉시 반격 (ATB 500 소모)
     - 반격 시 적에게 `[TAUNT]` 태그 부여 (다음 턴 강제 타겟)
   - **예시**: 마법사가 공격받음 → 기사가 막고 반격

2. **프로텍트 체인 (Protect Chain)**
   - **조건**: Defender가 `[GUARD]` 태그 스킬 사용 → 아군이 그 대상 공격
   - **효과**:
     - 아군 공격 시 추가 방어막 부여 (BRV 데미지 흡수)
     - 적 공격력 -20% (1턴)
   - **예시**: 기사의 "방패 타격"으로 적 방어 저하 → 전사가 안전하게 공격

### 2.3 Support (지원형)
**컨셉**: 아군 강화 및 연계 촉진

#### 콤보 타입
1. **버프 릴레이 (Buff Relay)**
   - **조건**: Support가 `[EMPOWER]` 태그로 아군 버프 → 그 아군이 행동
   - **효과**:
     - 버프받은 아군의 스킬 효과 1.3배
     - 버프 지속시간 +1턴
     - Support의 ATB +200 (빠른 재행동)
   - **예시**: 백마법사의 "힘의 축복" → 전사의 "필살기"가 강화

2. **힐 체인 (Heal Chain)**
   - **조건**: Support가 `[RECOVERY]` 태그로 힐 → 그 아군이 `[REVENGE]` 태그 스킬 사용
   - **효과**:
     - 회복받은 HP의 50%만큼 추가 BRV 획득
     - 다음 공격 데미지 +30%
   - **예시**: 성직자의 "치유의 기도" → 몽크의 "반격의 일격"

### 2.4 Specialist (특수형)
**컨셉**: 상황 반전 및 독특한 연계

#### 콤보 타입
1. **엘리멘탈 체인 (Elemental Chain)**
   - **조건**: Specialist가 `[ELEMENT:X]` 태그 공격 → 다른 아군이 같은 속성 공격
   - **효과**:
     - 속성 데미지 +50%
     - 적에게 `[WEAKNESS:X]` 디버프 부여 (해당 속성 취약)
     - 3연쇄 이상 시 속성 폭발 (광역 BRV 데미지)
   - **예시**: 흑마법사의 "파이어" → 기계공학자의 "화염 방사"

2. **기믹 싱크로 (Gimmick Synchro)**
   - **조건**: 두 Specialist가 서로 보완적 기믹 보유 → `[SYNCHRO]` 태그 동시 발동
   - **효과**:
     - 두 캐릭터의 기믹 게이지 공유
     - 합동 스킬 사용 가능 (ATB 합산)
     - 예: 시간술사(타임라인) + 차원술사(확률 왜곡) = "시공 왜곡"
   - **예시**: 연금술사 + 마공학자 = "초월 변환"

---

## 3. 시스템 구조 설계

### 3.1 데이터 구조

#### 스킬에 태그 추가
```yaml
# data/skills/warrior_heavy_strike.yaml
skill_id: warrior_heavy_strike
name: "강타"
description: "강력한 일격으로 적을 경직시킨다"
type: BRV_ATTACK
mp_cost: 15
multiplier: 2.5

# 연계 태그
chain_tags:
  setup: "STAGGER"      # 이 스킬은 STAGGER 태그 부여
  duration: 1           # 1턴 지속

# 콤보 조건
combo_conditions:
  trigger_tags: []      # 이 스킬은 트리거 아님
```

```yaml
# data/skills/archer_piercing_shot.yaml
skill_id: archer_piercing_shot
name: "관통 사격"
type: BRV_ATTACK
mp_cost: 20
multiplier: 3.0

chain_tags:
  trigger: "ASSAULT"    # STAGGER 상태에 사용 가능

combo_conditions:
  required_setup: "STAGGER"
  combo_bonus:
    damage_multiplier: 1.5
    atb_reduction: 300    # ATB 30% 감소
    crit_rate_bonus: 0.2
```

### 3.2 코드 구조

#### 새 모듈: `src/combat/combo_system.py`
```python
from typing import List, Optional, Dict
from src.character.character import Character
from src.character.skills.skill import Skill
from src.core.logger import get_logger

logger = get_logger("combo_system")

class ChainTag:
    """연계 태그 클래스"""
    def __init__(self, tag_type: str, duration: int, source: Character):
        self.tag_type = tag_type
        self.duration = duration
        self.source = source

class ComboSystem:
    """콤보 스킬 시스템 관리"""

    def __init__(self):
        self.active_tags: Dict[Character, List[ChainTag]] = {}
        self.combo_history: List[Dict] = []

    def apply_setup_tag(self, target: Character, tag_type: str,
                       duration: int, source: Character):
        """셋업 태그 적용"""
        if target not in self.active_tags:
            self.active_tags[target] = []

        tag = ChainTag(tag_type, duration, source)
        self.active_tags[target].append(tag)
        logger.info(f"{source.name}이(가) {target.name}에게 [{tag_type}] 태그 부여")

    def check_combo(self, actor: Character, target: Character,
                    skill: Skill) -> Optional[Dict]:
        """콤보 조건 체크"""
        if not hasattr(skill, 'combo_conditions'):
            return None

        required_setup = skill.combo_conditions.get('required_setup')
        if not required_setup:
            return None

        # 대상에게 필요한 태그가 있는지 확인
        if target in self.active_tags:
            for tag in self.active_tags[target]:
                if tag.tag_type == required_setup:
                    combo_data = skill.combo_conditions.get('combo_bonus', {})
                    combo_data['chain_source'] = tag.source
                    logger.info(f"🔗 콤보 발동! {tag.source.name}의 [{tag.tag_type}] → {actor.name}의 {skill.name}")
                    self.combo_history.append({
                        'setup': tag.source,
                        'finisher': actor,
                        'target': target,
                        'tag': tag.tag_type,
                        'skill': skill.name
                    })
                    return combo_data

        return None

    def update_tags(self):
        """턴 종료 시 태그 지속시간 감소"""
        for target, tags in list(self.active_tags.items()):
            remaining_tags = []
            for tag in tags:
                tag.duration -= 1
                if tag.duration > 0:
                    remaining_tags.append(tag)
                else:
                    logger.debug(f"{target.name}의 [{tag.tag_type}] 태그 만료")

            if remaining_tags:
                self.active_tags[target] = remaining_tags
            else:
                del self.active_tags[target]

    def get_active_tags(self, character: Character) -> List[str]:
        """캐릭터의 활성 태그 목록 반환"""
        if character not in self.active_tags:
            return []
        return [tag.tag_type for tag in self.active_tags[character]]
```

### 3.3 CombatManager 통합
```python
# src/combat/combat_manager.py에 추가

from src.combat.combo_system import ComboSystem

class CombatManager:
    def __init__(self):
        # 기존 코드...
        self.combo_system = ComboSystem()

    def execute_action(self, actor, action_type, target, skill=None):
        # 1. 콤보 체크
        combo_bonus = None
        if skill and target:
            combo_bonus = self.combo_system.check_combo(actor, target, skill)

        # 2. 스킬 실행 (콤보 보너스 적용)
        if combo_bonus:
            original_multiplier = skill.multiplier
            skill.multiplier *= combo_bonus.get('damage_multiplier', 1.0)

            # ATB 감소
            atb_reduction = combo_bonus.get('atb_reduction', 0)
            # ... 실행 로직

            skill.multiplier = original_multiplier  # 복원

        # 3. 셋업 태그 적용
        if hasattr(skill, 'chain_tags') and 'setup' in skill.chain_tags:
            setup_tag = skill.chain_tags['setup']
            duration = skill.chain_tags.get('duration', 1)
            self.combo_system.apply_setup_tag(target, setup_tag, duration, actor)

        # 기존 실행 로직...

    def end_turn(self):
        """턴 종료"""
        self.combo_system.update_tags()
        # 기존 턴 종료 로직...
```

---

## 4. 역할군별 예시 스킬

### Attacker: 전사 + 궁수 콤보
```yaml
# 전사의 셋업 스킬
warrior_heavy_strike:
  name: "강타"
  chain_tags:
    setup: "STAGGER"
    duration: 1

# 궁수의 피니셔
archer_piercing_shot:
  name: "관통 사격"
  combo_conditions:
    required_setup: "STAGGER"
    combo_bonus:
      damage_multiplier: 1.5
      atb_reduction: 300
      crit_rate_bonus: 0.2
```

### Defender: 기사의 카운터 어시스트
```yaml
knight_shield_bash:
  name: "방패 강타"
  chain_tags:
    setup: "GUARD"
    duration: 2

  # 방어형 특수: 자동 개입
  defensive_assist:
    enabled: true
    atb_cost: 500
    trigger_condition: "ally_attacked"
    effect:
      damage_reduction: 0.5
      counter_damage_multiplier: 1.2
      apply_tag: "TAUNT"
```

### Support: 백마법사 + 전사 콤보
```yaml
white_mage_power_blessing:
  name: "힘의 축복"
  chain_tags:
    setup: "EMPOWER"
    duration: 2

warrior_ultimate_strike:
  combo_conditions:
    required_setup: "EMPOWER"
    combo_bonus:
      damage_multiplier: 1.3
      buff_duration_bonus: 1
      source_atb_gain: 200  # Support의 ATB 회복
```

### Specialist: 속성 연계
```yaml
black_mage_fire:
  name: "파이어"
  chain_tags:
    setup: "ELEMENT:FIRE"
    duration: 1

machinist_flame_thrower:
  combo_conditions:
    required_setup: "ELEMENT:FIRE"
    combo_bonus:
      damage_multiplier: 1.5
      apply_debuff:
        type: "WEAKNESS:FIRE"
        duration: 2
        effect: -0.3  # 화염 저항 -30%
```

---

## 5. UI/UX 설계

### 5.1 태그 표시
```
[전투 화면]
┌─────────────────────────────────┐
│ 적: 고블린 킹                   │
│ HP: ████████░░ 800/1000         │
│ BRV: 450                        │
│ 태그: [STAGGER] ⏱1턴            │  ← 활성 태그 표시
│      [ELEMENT:FIRE] ⏱2턴       │
└─────────────────────────────────┘

아군: 궁수
스킬: 관통 사격
      └─ 🔗 콤보 가능! (전사의 강타)  ← 콤보 가능 표시
```

### 5.2 콤보 발동 애니메이션
```
[전사] 강타! → 적 경직 ([STAGGER] 부여)
         ↓
[궁수] 관통 사격!
         ↓
🔗 체인 어택 발동!
   - 데미지 +50%
   - 크리티컬 확정!
   - ATB 회복 +30%
```

### 5.3 콤보 히스토리 로그
```
[전투 로그]
턴 3: 전사의 강타 → 고블린 킹에 [STAGGER] 부여
턴 4: 🔗 궁수의 관통 사격 (콤보!) → 1,850 BRV 데미지 (크리티컬!)
턴 5: 백마법사의 힘의 축복 → 전사에 [EMPOWER] 부여
턴 6: 🔗 전사의 필살기 (콤보!) → 3,200 HP 데미지
```

---

## 6. 구현 우선순위

### Phase 1: 기본 시스템 (2주)
- [x] ComboSystem 클래스 구현
- [ ] ChainTag 적용/관리 로직
- [ ] CombatManager 통합
- [ ] 기본 태그 5개 (STAGGER, ASSAULT, GUARD, EMPOWER, ELEMENT)

### Phase 2: 역할군별 콤보 (3주)
- [ ] Attacker 콤보 (체인 어택, 익스플로잇)
- [ ] Defender 콤보 (카운터 어시스트, 프로텍트 체인)
- [ ] Support 콤보 (버프 릴레이, 힐 체인)
- [ ] Specialist 콤보 (엘리멘탈 체인)

### Phase 3: UI 및 밸런스 (2주)
- [ ] 태그 표시 UI
- [ ] 콤보 발동 애니메이션/사운드
- [ ] 밸런스 조정 (데미지 배율, ATB 소모)
- [ ] AI가 콤보 활용하도록 개선

### Phase 4: 고급 기능 (3주)
- [ ] 기믹 싱크로 시스템
- [ ] 3인 이상 연계 콤보
- [ ] 콤보 카운터 및 통계
- [ ] 튜토리얼 추가

---

## 7. 기술적 고려사항

### 7.1 성능 최적화
- 태그 검색을 O(1)로: `Dict[Character, List[ChainTag]]` 사용
- 턴마다 모든 태그 순회 필요 → 캐릭터 수 제한 (최대 8명)

### 7.2 기존 시스템과 충돌 방지
- 궁수의 `support_fire` 기믹과 차별화:
  - 기믹: 자동 발동, 마킹 기반
  - 콤보: 수동 트리거, 태그 기반
- GimmickUpdater와 통합:
  - 기믹 업데이트 후 콤보 체크
  - 콤보 발동 시 기믹 게이지 보너스

### 7.3 밸런스 리스크
- 콤보 남용으로 난이도 하락 가능성:
  - 콤보당 ATB 소모 증가 (총 ATB 1200~1500)
  - 콤보 쿨다운 (같은 조합 3턴 대기)
  - 적도 콤보 사용 (고난이도)

---

## 8. 다음 단계

1. **프로토타입 구현**: 전사+궁수 1개 콤보만 먼저 구현하여 검증
2. **데이터 구조 확정**: YAML 스키마 확정
3. **AI 개선**: 콤보를 고려한 의사결정 트리 추가
4. **피드백 수집**: 테스트 플레이 후 밸런스 조정

---

## 참고 자료

- **ZZZ 지원 시스템 분석**: [YouTube - ZZZ Combat Guide]
- **기존 기믹 시스템**: `src/character/gimmick_updater.py`
- **전투 시스템**: `src/combat/combat_manager.py`
- **스킬 시스템**: `src/character/skills/`

---

**작성일**: 2025-11-28
**작성자**: Claude Code
**버전**: 1.0 (초안)
