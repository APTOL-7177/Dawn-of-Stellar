# 팀워크 게이지 시스템 - 구현 완료 가이드

**구현 완료일**: 2025-11-28
**버전**: 1.0 (기본 시스템 완성)

## 📋 목차

1. [구현 완료 현황](#구현-완료-현황)
2. [파일 구조](#파일-구조)
3. [주요 기능](#주요-기능)
4. [통합 방법](#통합-방법)
5. [테스트 가이드](#테스트-가이드)

---

## 구현 완료 현황

### Phase 1: 핵심 데이터 구조 ✅
- [x] Party 클래스 (`src/character/party.py`)
- [x] TeamworkSkill 클래스 (`src/character/skills/teamwork_skill.py`)

### Phase 2: 전투 시스템 통합 ✅
- [x] CombatManager 수정
  - Party 인스턴스 추가
  - 게이지 증가 로직 (update_teamwork_gauge)
  - 팀워크 스킬 실행 로직 (execute_teamwork_skill)

### Phase 3: 팀워크 스킬 구현 ✅
- [x] 모든 33개 직업 팀워크 스킬 추가
- [x] 설계 문서 참고 구현 (data/teamwork_skills.yaml)

### Phase 4: 세이브/로드 지원 ✅
- [x] SaveSystem 통합 (팀워크 게이지 저장)
- [x] CombatManager 게이지 복원 메서드

### Phase 5: UI 구현 ✅
- [x] 게이지 표시 UI (src/ui/teamwork_gauge_display.py)
- [x] 연쇄 제안 화면 포맷

---

## 파일 구조

### 새로 생성된 파일

```
src/character/
├── party.py                              # Party 클래스 (팀워크 게이지 관리)
└── skills/
    ├── teamwork_skill.py                # TeamworkSkill 클래스
    └── job_skills/
        ├── warrior_skills.py            # 전사 팀워크 스킬 추가
        ├── archer_skills.py             # 궁수 팀워크 스킬 추가
        └── (... 나머지 31개 직업)

src/ui/
└── teamwork_gauge_display.py            # 게이지 표시 UI

data/
└── teamwork_skills.yaml                 # 팀워크 스킬 정보 (33개 직업)

scripts/
├── batch_add_teamwork_skills.py         # 팀워크 스킬 자동 추가 스크립트
└── add_teamwork_skills.py               # 단일 직업 추가 스크립트
```

### 수정된 파일

```
src/combat/combat_manager.py
- __init__: Party 인스턴스 추가
- start_combat: Party 초기화
- execute_action: 게이지 업데이트 통합
- update_teamwork_gauge: 게이지 증가 로직
- execute_teamwork_skill: 팀워크 스킬 실행
- restore_teamwork_gauge: 게이지 복원 (로드)

src/persistence/save_system.py
- save_game: 팀워크 게이지 저장
- load_game: 팀워크 게이지 복원 정보 준비
```

---

## 주요 기능

### 1. 팀워크 게이지 시스템

```python
# 파티에서 공유하는 게이지
party = Party(allies)
party.teamwork_gauge          # 현재 게이지 (0-600)
party.max_teamwork_gauge      # 최대 게이지 (600)

# 게이지 증가
party.add_teamwork_gauge(10)  # 10 증가

# 게이지 소모
party.consume_teamwork_gauge(100)  # 100 소모, 성공 시 True
```

### 2. 게이지 증가 로직

행동별 증가량:
- BRV 공격: +5
- HP 공격: +8
- BRV+HP 공격: +10
- 스킬: +6
- 크리티컬: +3 (추가)
- BREAK 발동: +15 (추가)
- 회복: +8 (추가)
- 피격: +3 (추가)

```python
# CombatManager에서 자동으로 호출
combat_manager.update_teamwork_gauge(
    action_type=ActionType.BRV_HP_ATTACK,
    is_critical=True,
    caused_break=True
)
# Result: 10 + 3 + 15 = 28 게이지 증가
```

### 3. 팀워크 스킬

```python
# 스킬 생성
teamwork = TeamworkSkill(
    "warrior_teamwork",
    "전장의 돌격",
    description,
    gauge_cost=125
)

# 사용 가능 여부 확인
can_use, reason = teamwork.can_use(user, party, chain_count=1)

# 실행
combat_manager.execute_teamwork_skill(
    actor=warrior,
    skill=teamwork,
    target=enemy,
    is_chain_start=True
)
```

### 4. 연쇄 시스템

```python
# 연쇄 시작
party.start_chain(starter)      # chain_active=True, chain_count=1

# 연쇄 계속 (다음 캐릭터 턴)
mp_cost = party.continue_chain()  # chain_count 증가, MP 비용 반환
# MP 비용: 10, 20, 40, 80, 160, ... (2배씩 증가)

# 연쇄 종료
party.end_chain()               # chain_active=False
```

### 5. 세이브/로드

```python
# 저장
save_system.save_game(
    save_name="slot1",
    game_state={
        "party_members": [...],
        "teamwork_gauge": 300,      # 자동으로 저장됨
        # ... 다른 정보
    }
)

# 로드
game_state = save_system.load_game("slot1")
if "_teamwork_gauge" in game_state:
    combat_manager.restore_teamwork_gauge(
        game_state["_teamwork_gauge"],
        game_state.get("_max_teamwork_gauge", 600)
    )
```

### 6. UI 표시

```python
from src.ui.teamwork_gauge_display import TeamworkGaugeDisplay, ChainPrompt

# 기본 게이지 표시
display = TeamworkGaugeDisplay.format_gauge(300, 600)
# Output: "팀워크 게이지 300/600 (12셀)"

# 스킬 메뉴용
info = TeamworkGaugeDisplay.format_for_skill_menu(100, 450, 600)

# 연쇄 제안 화면
prompt = ChainPrompt.format_prompt(
    chain_count=2,
    chain_starter_name="전사",
    current_skill_name="일제사격",
    current_skill_cost=150,
    current_actor_name="궁수",
    teamwork_gauge=350,
    current_mp=45,
    required_mp=10
)
```

---

## 통합 방법

### 1. 기존 게임 루프에 통합

```python
# main.py 또는 game_engine.py

from src.combat.combat_manager import get_combat_manager
from src.character.party import Party

# 전투 시작 시
combat_manager = get_combat_manager()
combat_manager.start_combat(allies, enemies)  # Party 자동 생성

# 게임 상태 저장 시
game_state = {
    "party_members": [member.to_dict() for member in party_members],
    # teamwork_gauge는 save_system이 자동으로 저장
}
save_system.save_game("slot1", game_state)

# 게임 상태 로드 시
game_state = save_system.load_game("slot1")
# _teamwork_gauge가 있으면 나중에 복원
if "_teamwork_gauge" in game_state:
    # 전투 시작 후 복원
    combat_manager.restore_teamwork_gauge(
        game_state["_teamwork_gauge"],
        game_state.get("_max_teamwork_gauge", 600)
    )
```

### 2. UI에 통합

```python
# combat_ui.py 또는 battle_screen.py

from src.ui.teamwork_gauge_display import TeamworkGaugeDisplay

def display_battle_status():
    # 현재 게이지 표시
    gauge_info = TeamworkGaugeDisplay.format_compact(
        combat_manager.party.teamwork_gauge,
        combat_manager.party.max_teamwork_gauge
    )
    print(gauge_info)

def display_skill_options():
    # 스킬 메뉴에 게이지 정보 추가
    for skill in player.skills:
        if hasattr(skill, 'is_teamwork_skill') and skill.is_teamwork_skill:
            info = TeamworkGaugeDisplay.format_for_skill_menu(
                skill.teamwork_cost.gauge,
                combat_manager.party.teamwork_gauge
            )
            print(info)

def show_chain_prompt(chain_info):
    # 연쇄 제안 화면 표시
    prompt = ChainPrompt.format_prompt(
        chain_count=combat_manager.party.chain_count,
        chain_starter_name=combat_manager.party.chain_starter.name,
        current_skill_name=skill.name,
        current_skill_cost=skill.teamwork_cost.gauge,
        current_actor_name=actor.name,
        teamwork_gauge=combat_manager.party.teamwork_gauge,
        current_mp=actor.current_mp,
        required_mp=skill.calculate_mp_cost(combat_manager.party.chain_count)
    )
    print(prompt)
```

### 3. 스킬 시스템에 통합

```python
# skill_menu.py 또는 action_handler.py

def handle_teamwork_skill(actor, skill, target):
    """팀워크 스킬 실행"""
    is_chain_start = not combat_manager.party.chain_active

    # 실행
    success = combat_manager.execute_teamwork_skill(
        actor=actor,
        skill=skill,
        target=target,
        is_chain_start=is_chain_start
    )

    if success:
        # ATB 회복은 execute_teamwork_skill에서 처리됨
        # 스킬 효과도 자동으로 실행됨
        return True
    else:
        # 게이지 부족 또는 MP 부족
        return False

def offer_chain_continuation(next_actor, next_skills):
    """연쇄 계속 제안"""
    if not combat_manager.party.chain_active:
        return False

    # UI에서 선택 받음
    # [Y] 이어받기 -> execute_teamwork_skill(is_chain_start=False)
    # [N] 종료 -> party.end_chain()
    pass
```

---

## 테스트 가이드

### 단위 테스트

```python
# test_teamwork.py

def test_party_gauge():
    """Party 게이지 테스트"""
    party = Party([char1, char2])
    assert party.teamwork_gauge == 0

    party.add_teamwork_gauge(50)
    assert party.teamwork_gauge == 50

    assert party.consume_teamwork_gauge(30) == True
    assert party.teamwork_gauge == 20

def test_chain_system():
    """연쇄 시스템 테스트"""
    party = Party([char1, char2])

    party.start_chain(char1)
    assert party.chain_active == True
    assert party.chain_count == 1

    mp_cost = party.continue_chain()
    assert party.chain_count == 2
    assert mp_cost == 10

    mp_cost = party.continue_chain()
    assert party.chain_count == 3
    assert mp_cost == 20

def test_teamwork_skill():
    """팀워크 스킬 테스트"""
    skill = TeamworkSkill("test", "테스트", "테스트", gauge_cost=100)

    party = Party([char1])
    party.add_teamwork_gauge(100)

    can_use, msg = skill.can_use(char1, party, chain_count=1)
    assert can_use == True

    can_use, msg = skill.can_use(char1, party, chain_count=2)
    assert can_use == False  # MP 부족
```

### 통합 테스트

```bash
# 게임 실행 후 테스트
python main.py --debug

# 전투 진입
# 1. 여러 번 공격하여 게이지 충전 (대략 100 이상)
# 2. 팀워크 스킬 사용 (키 입력 또는 메뉴)
# 3. 다음 캐릭터 턴에서 연쇄 이어받기
# 4. 로그 확인: logs/combat_latest.log

# 세이브/로드 테스트
# 1. 전투 중 게이지를 어느 정도 채운 후 저장
# 2. 게임 재시작 후 로드
# 3. 게이지가 복원되었는지 확인
```

### 성능 테스트

```python
# 성능 테스트
import time

party = Party([char for _ in range(100)])

start = time.time()
for _ in range(10000):
    party.add_teamwork_gauge(10)
    party.consume_teamwork_gauge(5)
elapsed = time.time() - start

print(f"10000 회 작업: {elapsed:.3f}초")  # < 0.1초 예상
```

---

## 주의사항

### 1. Party는 CombatManager에서만 생성

```python
# ✅ 올바른 사용법
combat_manager.start_combat(allies, enemies)
# party는 내부적으로 생성됨

# ❌ 잘못된 사용법
party = Party(allies)
# 이 party는 CombatManager와 연동되지 않음
```

### 2. 팀워크 스킬은 반드시 TeamworkSkill 클래스 사용

```python
# ✅ 올바른 사용법
skill = TeamworkSkill("id", "name", "desc", gauge_cost=100)

# ❌ 잘못된 사용법
skill = Skill("id", "name", "desc")  # 팀워크 비용 없음
```

### 3. 게이지 업데이트는 자동

```python
# ✅ 자동으로 호출됨 (execute_action 내부)
combat_manager.execute_action(actor, ActionType.BRV_HP_ATTACK, target)

# ❌ 수동으로 호출하지 않아도 됨
# combat_manager.update_teamwork_gauge(...)  # 이미 위에서 호출됨
```

### 4. 연쇄는 수동으로 관리

```python
# ✅ execute_teamwork_skill이 자동으로 연쇄 시작/계속
combat_manager.execute_teamwork_skill(actor, skill, target, is_chain_start=True)

# 다음 캐릭터 턴에서:
combat_manager.execute_teamwork_skill(actor, skill, target, is_chain_start=False)

# 또는 수동으로 종료:
combat_manager.party.end_chain()
```

---

## 향후 개선 사항

### 미구현 기능 (선택사항)

1. **특수 효과**
   - 팀워크 스킬별 고유 효과 구현 (현재는 기본 틀만 있음)
   - 예: 시간술사의 "시간 정지" - 적 전체 스턴

2. **고급 UI**
   - 게이지 애니메이션
   - 연쇄 이펙트
   - 스킬 설명 팝업

3. **밸런싱**
   - 게이지 증가량 조정
   - 스킬 비용 미세 조정
   - 연쇄 깊이 제한

4. **통계**
   - 팀워크 스킬 사용 횟수
   - 최대 연쇄 깊이
   - 게이지 효율도

---

## 지원 및 문의

문제가 발생하면:

1. 로그 확인: `logs/combat_latest.log`
2. 디버그 모드 실행: `python main.py --debug`
3. Party, TeamworkSkill, CombatManager 간 연동 확인
4. 스킬 정의가 올바른지 확인 (effects, costs)

---

**마지막 업데이트**: 2025-11-28
**상태**: 구현 완료, 기본 기능 모두 작동
**다음 단계**: 게임 내 통합 및 UI 커스터마이징
