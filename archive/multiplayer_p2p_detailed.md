# Dawn of Stellar - P2P 멀티플레이 상세 설계

## 목차

1. [개요](#개요)
2. [멀티플레이 전용 규칙](#멀티플레이-전용-규칙)
3. [플레이어 수별 모드](#플레이어-수별-모드)
4. [아키텍처 설계](#아키텍처-설계)
5. [실시간 전투 시스템](#실시간-전투-시스템)
6. [전투 도중 합류 시스템](#전투-도중-합류-시스템)
7. [맵 탐험 시스템](#맵-탐험-시스템)
8. [던전 생성 동기화](#던전-생성-동기화)
9. [상태 동기화](#상태-동기화)
10. [인벤토리 시스템](#인벤토리-시스템)
11. [설계 결정 필요 요소](#설계-결정-필요-요소)
12. [추가 고려사항](#추가-고려사항)
13. [구현 순서](#구현-순서)

---

## 개요

이 문서는 P2P 멀티플레이 모드의 구체적인 구현 설계를 담고 있습니다. 싱글플레이와는 다른 별개의 게임 룰을 가진 멀티플레이 모드를 정의합니다.

### 핵심 설계 원칙

1. **싱글플레이와 독립적**: 멀티플레이 전용 게임 모드
2. **실시간성 우선**: 전투 중에도 게임이 진행됨
3. **개별 자유도**: 각 플레이어가 독립적으로 탐험
4. **공정성 보장**: 모든 플레이어에게 동일한 규칙 적용

### 핵심 결정 사항 요약

**전투 합류**: ATB 0부터 시작, 제한 없음, 위협 재계산  
**밸런스**: 싱글플레이와 동일 (적 수/HP/데미지/인벤토리)  
**경험치**: 전투 참여 전투원 수로 분배  
**전투 시스템**: 1.5초 고정 대기, 1/50 ATB 감소, 5타일 반경  
**인벤토리**: 자유 사용, 공유 저장, 골드 완전 공유  
**던전**: 호스트 생성 시드, 고정 크기  
**네트워크**: 압축 사용, 0.5초 일반 지연 허용  
**UI**: 토글 표시, 텍스트 채팅, 색상 핑  
**저장**: 호스트만 저장/재개  
**보안**: 엄격한 검증, 호스트 권위  

상세 내용은 [최종 설계 결정 사항](#최종-설계-결정-사항) 섹션 참고

---

## 멀티플레이 전용 규칙

### 싱글플레이 vs 멀티플레이 비교

| 요소 | 싱글플레이 | 멀티플레이 |
|------|-----------|-----------|
| 전투 모드 | 턴제 (플레이어 턴 시 시간 정지) | 실시간 (항상 진행) |
| 행동 선택 시 ATB | 증가 안 함 | 적의 ATB 증가 (1.5초 대기 제외) |
| 행동 선택 중 ATB 증가 | 증가 안 함 | **1/50로 감소** (아군/적군 모두) |
| 캐스팅 중 ATB | 정지 | **1/50로 감소** (아군/적군 모두) |
| 맵 탐험 | 단일 플레이어 | **개별 캐릭터 독립 이동** |
| 적의 움직임 | 즉시 반응 | **2초 간격** |
| 전투 참여 | 파티 전체 (항상 4명) | **주변 아군만 참여** |
| 전투 도중 합류 | 불가능 | **가능** |
| 플레이어 수 | 1명 (고정) | **2명/3명/4명 (선택)** |
| 인벤토리 | 개인 | **파티 공유** |
| 던전 생성 | 랜덤 | **시드 기반 동기화** |

---

## 플레이어 수별 모드

### 모드 구분

멀티플레이 모드는 플레이어 수에 따라 명확히 구분됩니다:

| 모드 | 플레이어 수 | 설명 |
|------|------------|------|
| 2인 플레이 | 2명 | 두 명의 플레이어가 협동 |
| 3인 플레이 | 3명 | 세 명의 플레이어가 협동 |
| 4인 플레이 | 4명 | 네 명의 플레이어가 협동 (최대) |

### 모드별 차이점

#### 1. 밸런스 조정

각 모드에 따라 게임 밸런스를 조정할 수 있습니다:

```python
class PlayerCountBalance:
    """플레이어 수별 밸런스 설정"""
    
    BALANCE_SETTINGS = {
        2: {
            "enemy_count_multiplier": 0.8,  # 적 수 80%
            "enemy_hp_multiplier": 0.9,     # 적 HP 90%
            "enemy_damage_multiplier": 0.9, # 적 데미지 90%
            "exp_multiplier": 1.1,          # 경험치 110%
            "drop_rate_multiplier": 1.0     # 드롭률 100%
        },
        3: {
            "enemy_count_multiplier": 1.0,  # 적 수 100%
            "enemy_hp_multiplier": 1.0,     # 적 HP 100%
            "enemy_damage_multiplier": 1.0, # 적 데미지 100%
            "exp_multiplier": 1.0,          # 경험치 100%
            "drop_rate_multiplier": 1.0     # 드롭률 100%
        },
        4: {
            "enemy_count_multiplier": 1.2,  # 적 수 120%
            "enemy_hp_multiplier": 1.1,     # 적 HP 110%
            "enemy_damage_multiplier": 1.1, # 적 데미지 110%
            "exp_multiplier": 0.9,          # 경험치 90% (분배)
            "drop_rate_multiplier": 1.2     # 드롭률 120%
        }
    }
```

#### 2. 인벤토리 용량

플레이어 수에 따라 인벤토리 용량이 달라질 수 있습니다:

```python
def calculate_inventory_weight(player_count: int, base_weight: float = 5.0) -> float:
    """플레이어 수에 따른 인벤토리 무게 계산"""
    # 각 플레이어당 추가 용량
    weight_per_player = 2.0
    
    return base_weight + (player_count * weight_per_player)
```

#### 3. 세션 시작 시 모드 설정

```python
class MultiplayerSession:
    """멀티플레이 세션"""
    
    def __init__(self, max_players: int = 4):
        self.max_players = max_players  # 2, 3, 또는 4
        self.player_count = 0
        self.players: Dict[str, Player] = {}
        self.balance_settings = PlayerCountBalance.BALANCE_SETTINGS[max_players]
    
    def add_player(self, player_id: str) -> bool:
        """플레이어 추가"""
        if self.player_count >= self.max_players:
            return False
        
        if player_id in self.players:
            return False
        
        self.players[player_id] = Player(player_id)
        self.player_count += 1
        return True
    
    def get_balance_multiplier(self, key: str) -> float:
        """밸런스 배율 조회"""
        return self.balance_settings.get(key, 1.0)
```

---

## 아키텍처 설계

### 전체 구조

```
[호스트 (Host)]
    ↓ (게임 상태 권위자)
[네트워크 레이어]
    ↓ (WebSocket/AsyncIO)
[클라이언트 1] [클라이언트 2] [클라이언트 3] [클라이언트 4]
```

### 호스트 역할

1. **게임 상태 권위자 (Authority)**
   - 모든 게임 로직 실행
   - 결정적인 결과 생성
   - 상태 변경 검증

2. **동기화 관리**
   - 모든 클라이언트에게 상태 브로드캐스트
   - 입력 검증 및 처리
   - 충돌 해결

3. **던전 생성 담당**
   - 시드 기반 던전 생성
   - 모든 클라이언트에 던전 데이터 전송

### 클라이언트 역할

1. **입력 전송**
   - 플레이어 입력을 호스트로 전송
   - 예측 시뮬레이션 (클라이언트 예측)

2. **상태 수신 및 렌더링**
   - 호스트로부터 상태 업데이트 수신
   - 로컬 상태를 호스트 상태로 보간 (Interpolation)

3. **UI 렌더링**
   - 현재 상태에 따른 UI 업데이트

---

## 실시간 전투 시스템

### ATB 게이지 처리 규칙

#### 기본 규칙

1. **항상 증가**: 싱글플레이와 달리 전투 중 ATB가 항상 증가
2. **1.5초 대기 예외**: 액션 선택 후 1.5초 대기 중에는 ATB 증가하지 않음
3. **행동 선택 중 감소**: 1명이라도 행동을 고르고 있으면 모든 ATB가 1/50로 감소

#### 구현 예시

```python
class MultiplayerATBSystem(ATBSystem):
    """멀티플레이 전용 ATB 시스템"""
    
    def __init__(self):
        super().__init__()
        self.players_selecting_action = set()  # 행동 선택 중인 플레이어
        self.action_confirmed_time = {}  # 액션 확인 시간 {player_id: timestamp}
        self.ACTION_WAIT_TIME = 1.5  # 액션 확인 후 대기 시간 (초)
    
    def set_player_selecting(self, player_id: str, is_selecting: bool):
        """플레이어가 행동 선택 중인지 설정"""
        if is_selecting:
            self.players_selecting_action.add(player_id)
        else:
            self.players_selecting_action.discard(player_id)
            # 액션 확인 시간 기록
            self.action_confirmed_time[player_id] = time.time()
    
    def is_in_action_wait(self, player_id: str) -> bool:
        """액션 확인 후 대기 시간 중인지 확인"""
        if player_id not in self.action_confirmed_time:
            return False
        
        elapsed = time.time() - self.action_confirmed_time[player_id]
        return elapsed < self.ACTION_WAIT_TIME
    
    def calculate_atb_increase(self, combatant: Any, delta_time: float) -> float:
        """ATB 증가량 계산 (멀티플레이 규칙 적용)"""
        # 기본 증가량 계산
        base_increase = super().calculate_atb_increase(combatant, delta_time)
        
        # 1. 행동 선택 중인 플레이어가 있으면 1/50로 감소
        if self.players_selecting_action:
            base_increase *= 0.02  # 1/50
        
        # 2. 캐스팅 중인 경우도 1/50로 감소
        gauge = self.get_gauge(combatant)
        if gauge and gauge.is_casting:
            base_increase *= 0.02  # 1/50
        
        # 3. 액션 확인 후 1.5초 대기 중이면 증가하지 않음
        # (이것은 호스트에서 처리 - 특정 플레이어의 캐릭터만 적용)
        if hasattr(combatant, 'player_id'):
            if self.is_in_action_wait(combatant.player_id):
                return 0.0
        
        return base_increase
    
    def update(self, delta_time: float = 1.0) -> None:
        """ATB 업데이트 (멀티플레이 - 항상 진행)"""
        if not self.enabled:
            return
        
        # 멀티플레이에서는 항상 ATB 증가 (싱글플레이와 달리)
        for combatant, gauge in self.gauges.items():
            if not getattr(combatant, 'is_alive', True):
                gauge.current = 0
                continue
            
            # ATB 증가량 계산 (멀티플레이 규칙 적용)
            increase = self.calculate_atb_increase(combatant, delta_time)
            gauge.increase(increase)
```

### 전투 시작 조건

#### 근처 아군만 참여

```python
class MultiplayerCombatManager(CombatManager):
    """멀티플레이 전투 관리자"""
    
    def check_nearby_allies(self, trigger_position: tuple, all_players: List[Player]) -> List[Character]:
        """
        전투 트리거 위치 주변의 아군만 선택
        
        Args:
            trigger_position: (x, y) 전투가 시작된 위치
            all_players: 모든 플레이어 리스트
            
        Returns:
            전투에 참여할 아군 리스트
        """
        PARTICIPATION_RADIUS = 5  # 참여 반경 (타일 단위)
        participating_allies = []
        
        for player in all_players:
            # 플레이어 위치와 전투 위치 거리 계산
            distance = self.calculate_distance(
                (player.x, player.y),
                trigger_position
            )
            
            # 반경 내에 있으면 참여
            if distance <= PARTICIPATION_RADIUS:
                # 플레이어의 파티 멤버 추가
                if hasattr(player, 'party') and player.party:
                    participating_allies.extend(player.party)
        
        return participating_allies
    
    def start_combat(self, trigger_position: tuple, enemies: List[Enemy], all_players: List[Player]):
        """전투 시작 (근처 아군만 참여)"""
        # 근처 아군만 선택
        nearby_allies = self.check_nearby_allies(trigger_position, all_players)
        
        if not nearby_allies:
            # 참여할 아군이 없으면 전투 시작 안 함
            return
        
        # 전투 시작 (부모 클래스 메서드 재사용)
        super().start_combat(nearby_allies, enemies)
        
        # 네트워크: 전투 시작 브로드캐스트
        self.network_manager.broadcast({
            "type": "combat_start",
            "participants": [a.id for a in nearby_allies],
            "enemies": [e.id for e in enemies],
            "position": trigger_position
        })
```

### 전투 UI (멀티플레이)

```python
class MultiplayerCombatUI(CombatUI):
    """멀티플레이 전투 UI"""
    
    def __init__(self, ...):
        super().__init__(...)
        self.network_manager = None
        self.is_local_player_turn = False
        self.action_selection_start_time = None
    
    def start_action_selection(self, actor: Any):
        """행동 선택 시작"""
        # ATB 시스템에 행동 선택 중임을 알림
        if self.atb_system and hasattr(actor, 'player_id'):
            self.atb_system.set_player_selecting(actor.player_id, True)
        
        self.action_selection_start_time = time.time()
        self.is_local_player_turn = True
        
        # 네트워크: 행동 선택 시작 알림
        self.network_manager.send({
            "type": "action_selection_start",
            "player_id": actor.player_id,
            "actor_id": actor.id
        })
    
    def confirm_action(self, actor: Any, action: dict):
        """액션 확인"""
        # ATB 시스템에 행동 선택 종료 알림
        if self.atb_system and hasattr(actor, 'player_id'):
            self.atb_system.set_player_selecting(actor.player_id, False)
        
        # 네트워크: 액션 전송 (호스트로)
        self.network_manager.send({
            "type": "combat_action",
            "player_id": actor.player_id,
            "actor_id": actor.id,
            "action": action,
            "timestamp": time.time()
        })
        
        self.is_local_player_turn = False
        self.action_selection_start_time = None
```

---

## 전투 도중 합류 시스템

### 개요

전투가 진행 중일 때도 새로운 플레이어가 합류할 수 있습니다. 이는 멀티플레이 모드의 중요한 특징입니다.

### 합류 조건

#### 1. 거리 조건

```python
class CombatJoinHandler:
    """전투 도중 합류 처리"""
    
    PARTICIPATION_RADIUS = 5  # 참여 가능 반경 (타일)
    JOIN_CHECK_INTERVAL = 0.5  # 합류 체크 주기 (초)
    
    def can_join_combat(self, player: Player, combat_position: tuple) -> bool:
        """전투 합류 가능 여부 확인"""
        # 거리 계산
        distance = self.calculate_distance(
            (player.x, player.y),
            combat_position
        )
        
        # 반경 내에 있는지 확인
        return distance <= self.PARTICIPATION_RADIUS
```

#### 2. 전투 상태 확인

```python
    def is_combat_in_progress(self, combat_manager: CombatManager) -> bool:
        """전투 진행 중인지 확인"""
        return combat_manager.state in [
            CombatState.IN_PROGRESS,
            CombatState.PLAYER_TURN,
            CombatState.ENEMY_TURN
        ]
```

### 합류 처리 로직

```python
class MultiplayerCombatManager(CombatManager):
    """멀티플레이 전투 관리자 (합류 지원)"""
    
    def __init__(self):
        super().__init__()
        self.join_handler = CombatJoinHandler()
        self.last_join_check_time = 0.0
    
    def check_and_add_joiners(self, all_players: List[Player], combat_position: tuple):
        """전투 도중 합류 가능한 플레이어 확인 및 추가"""
        current_time = time.time()
        
        # 주기적으로 체크 (0.5초마다)
        if current_time - self.last_join_check_time < self.join_handler.JOIN_CHECK_INTERVAL:
            return
        
        self.last_join_check_time = current_time
        
        # 현재 전투 참여자 ID 목록
        current_participant_ids = {getattr(a, 'player_id', None) for a in self.allies if hasattr(a, 'player_id')}
        
        # 모든 플레이어 중에서 전투에 참여하지 않은 플레이어 확인
        for player in all_players:
            player_id = getattr(player, 'id', None)
            
            # 이미 참여 중이면 스킵
            if player_id in current_participant_ids:
                continue
            
            # 합류 가능한지 확인
            if self.join_handler.can_join_combat(player, combat_position):
                # 전투에 합류
                self.add_combatant_mid_combat(player)
    
    def add_combatant_mid_combat(self, player: Player):
        """전투 도중 전투원 추가"""
        if not player.party:
            return
        
        new_allies = []
        
        # 플레이어의 파티 멤버 추가
        for character in player.party:
            if character.is_alive:
                # ATB 시스템에 등록
                self.atb.register_combatant(character)
                
                # ATB 게이지 초기화 (0부터 시작)
                gauge = self.atb.get_gauge(character)
                if gauge:
                    gauge.current = 0  # 합류자는 0에서 시작
                
                # BRV 초기화
                self.brave.initialize_brv(character)
                
                # 아군 리스트에 추가
                self.allies.append(character)
                new_allies.append(character)
        
        if new_allies:
            # 모든 클라이언트에게 합류 브로드캐스트
            self.network_manager.broadcast({
                "type": "combat_join",
                "player_id": getattr(player, 'id', None),
                "characters": [c.id for c in new_allies],
                "combat_state": self.get_state_snapshot()
            })
            
            self.logger.info(f"전투 합류: {player.id} ({len(new_allies)}명)")
```

### 합류 시 ATB 초기화 옵션

합류 시 ATB 게이지를 어떻게 설정할지 결정해야 합니다:

#### 옵션 1: 0부터 시작 (기본값)

```python
gauge.current = 0  # 합류자는 처음부터 시작
```

**장점**: 합류자가 즉시 액션을 취할 수 없음 (공정함)
**단점**: 합류 시 즉시 도움이 안 됨

#### 옵션 2: 랜덤 초기화

```python
random_percentage = random.uniform(0.0, 0.5)
gauge.current = int(gauge.max_gauge * random_percentage)
```

**장점**: 합류 시 다양한 상태로 시작
**단점**: 운에 의존

#### 옵션 3: 평균 ATB에 맞춤

```python
# 현재 전투원들의 평균 ATB 계산
avg_atb = sum(self.atb.get_gauge(c).current for c in self.allies) / len(self.allies)
gauge.current = int(avg_atb * 0.8)  # 평균의 80%
```

**장점**: 공정함 (기존 플레이어와 비슷한 시작점)
**단점**: 계산 복잡도

#### 옵션 4: 설정 가능

```python
class CombatJoinSettings:
    """전투 합류 설정"""
    ATB_INITIALIZATION = "zero"  # "zero", "random", "average", "percentage"
    ATB_PERCENTAGE = 0.3  # percentage 모드일 때 사용
```

**권장**: **옵션 1 (0부터 시작)** 또는 **옵션 3 (평균 맞춤)**

### 합류 시 처리 사항

```python
class CombatJoinProcessor:
    """전투 합류 처리 담당"""
    
    def process_join(self, player: Player, combat_manager: CombatManager):
        """합류 처리 전체 프로세스"""
        # 1. 합류 가능 여부 확인
        if not self.validate_join(player, combat_manager):
            return False
        
        # 2. 전투원 추가
        characters = combat_manager.add_combatant_mid_combat(player)
        
        # 3. 상태 효과 초기화 (선택 사항)
        # - 합류자는 현재 전투의 상태 효과를 받지 않음
        # - 또는 전투 중인 아군의 평균 버프/디버프 적용
        
        # 4. 전투 UI 업데이트 (모든 클라이언트)
        combat_manager.network_manager.broadcast({
            "type": "combat_ui_update",
            "participants": [c.id for c in combat_manager.allies]
        })
        
        # 5. 로그/알림
        combat_manager.logger.info(f"✅ {player.id} 전투에 합류했습니다!")
        
        return True
    
    def validate_join(self, player: Player, combat_manager: CombatManager) -> bool:
        """합류 가능 여부 검증"""
        # 1. 플레이어가 살아있는지 확인
        if not any(c.is_alive for c in player.party):
            return False
        
        # 2. 전투 진행 중인지 확인
        if not combat_manager.is_combat_in_progress():
            return False
        
        # 3. 최대 참여 인원 확인 (선택 사항)
        # 예: 4인 모드에서는 최대 4명까지만 참여
        # max_participants = combat_manager.session.max_players * 4  # 플레이어당 4명
        # if len(combat_manager.allies) >= max_participants:
        #     return False
        
        return True
```

### 합류 제한 옵션

전투 도중 합류를 제한할지 결정해야 합니다:

#### 옵션 A: 제한 없음
- 언제든지 합류 가능

#### 옵션 B: 시간 제한
```python
COMBAT_JOIN_TIME_LIMIT = 10.0  # 전투 시작 후 10초까지만 합류 가능
```

#### 옵션 C: 턴 제한
```python
COMBAT_JOIN_TURN_LIMIT = 3  # 3턴까지만 합류 가능
```

#### 옵션 D: HP 제한
```python
# 아군의 평균 HP가 50% 이하로 떨어지면 합류 불가
min_hp_percentage = 0.5
```

**권장**: **옵션 A (제한 없음)** 또는 **옵션 B (시간 제한)**

### 합류 시 적의 반응

합류 시 적의 행동을 변경할지 결정:

```python
def on_player_join_combat(self, enemies: List[Enemy], joined_player: Player):
    """플레이어 합류 시 적의 반응"""
    # 옵션 1: 반응 없음 (기본)
    pass
    
    # 옵션 2: 적이 새로운 위협을 인식
    for enemy in enemies:
        # 타겟 우선순위 재계산
        enemy.recalculate_threat()
    
    # 옵션 3: 적이 공격 대상 추가 (특수 스킬 등)
    # 보스가 합류자를 즉시 공격하는 스킬 사용 등
```

---

## 최종 설계 결정 사항

다음은 모든 설계 결정 요소에 대한 최종 결정 사항입니다. 이 결정 사항에 따라 구현을 진행합니다.

### 1. 전투 합류 관련

#### 1.1 ATB 초기화 방식
**결정**: **0부터 시작**
- 합류자는 ATB 게이지가 0에서 시작
- 즉시 액션을 취할 수 없지만 공정함
- 구현: `gauge.current = 0`

#### 1.2 합류 시간 제한
**결정**: **제한 없음**
- 전투 도중 언제든지 합류 가능
- 시간, 턴, HP 제한 없음
- 거리 조건만 확인 (5 타일 이내)

#### 1.3 합류 시 적의 반응
**결정**: **위협 재계산**
- 합류 시 적이 새로운 위협을 인식
- 타겟 우선순위 재계산
- 특수 행동은 없음

### 2. 플레이어 수별 밸런스

#### 2.1 적 수 조정
**결정**: **싱글플레이와 동일**
- 2인/3인/4인 모드 모두 싱글플레이와 동일한 적 수
- 밸런스 배율: 1.0 (변경 없음)

#### 2.2 적 체력/데미지 조정
**결정**: **싱글플레이와 동일**
- 적의 HP와 데미지는 플레이어 수와 관계없이 동일
- 밸런스 배율: 1.0 (변경 없음)

#### 2.3 경험치/보상 분배
**결정**: **보상/경험치 ÷ 전투에 참여한 전투원**
- 경험치와 보상은 전투에 참여한 전투원 수로 나눔
- 예: 경험치 1000, 참여 전투원 3명 → 각 333 경험치
- 개인당 경험치는 감소하지만 합계는 동일
- 구현: `total_reward / len(participating_combatants)`

#### 2.4 인벤토리 용량
**결정**: **싱글플레이와 동일**
- 플레이어 수와 관계없이 인벤토리 용량 동일
- 파티 공유이므로 용량 조정 불필요

### 3. 전투 시스템

#### 3.1 행동 선택 대기 시간
**결정**: **1.5초 고정**
- 액션 확인 후 1.5초 동안 ATB 증가하지 않음
- 설정 변경 불가
- 구현: `ACTION_WAIT_TIME = 1.5`

#### 3.2 ATB 감소 배율
**결정**: **1/50 고정**
- 행동 선택 중 또는 캐스팅 중 ATB 증가량이 1/50로 감소
- 설정 변경 불가
- 구현: `base_increase *= 0.02` (1/50)

#### 3.3 근처 아군 판정 반경
**결정**: **5 타일 고정**
- 전투 시작 또는 합류 가능 반경: 5 타일
- 설정 변경 불가
- 구현: `PARTICIPATION_RADIUS = 5`

### 4. 인벤토리 시스템

#### 4.1 아이템 사용 권한
**결정**: **자유 사용**
- 누구나 인벤토리의 아이템 사용 가능
- 획득자나 소유권 개념 없음
- 공유 인벤토리 특성상 자유롭게 사용

#### 4.2 아이템 분배
**결정**: **공유 저장**
- 획득한 아이템은 인벤토리에 저장
- 자동 분배나 수동 분배 없음
- 필요 시 누구나 사용 가능

#### 4.3 골드 관리
**결정**: **완전 공유**
- 모든 골드가 파티 전체가 공유
- 개인 골드 개념 없음
- 누구나 사용 가능

### 5. 던전 생성

#### 5.1 시드 생성 방식
**결정**: **호스트 생성**
- 호스트가 세션 시작 시 시드 생성
- 생성된 시드를 모든 클라이언트에 전송
- 모든 클라이언트에서 동일한 던전 생성

#### 5.2 던전 크기 조정
**결정**: **고정 크기**
- 플레이어 수와 관계없이 던전 크기 동일
- 싱글플레이와 동일한 크기

### 6. 네트워크 및 성능

#### 6.1 동기화 주기
**결정**: **자동 결정 (알아서)**
- 시스템이 상황에 맞게 동기화 주기 자동 조정
- 기본값:
  - 캐릭터 위치: 0.1초 (10 FPS)
  - 캐릭터 상태: 0.1초 (10 FPS)
  - 적 위치: 0.5초 (2 FPS)

#### 6.2 메시지 압축
**결정**: **압축 사용**
- 큰 메시지는 gzip 또는 zlib로 압축
- 네트워크 대역폭 절약
- 작은 메시지는 압축 없이 전송

#### 6.3 최대 지연 시간 허용
**결정**: **일반적 (0.5초 이하)**
- 허용 가능한 지연 시간: 0.5초 이하
- 0.5초 초과 시 경고 표시
- 1초 초과 시 재연결 제안

### 7. UI/UX

#### 7.1 플레이어 정보 표시
**결정**: **토글 표시**
- 기본적으로 숨김
- 특정 키(예: Tab)로 토글 가능
- 필요 시에만 표시하여 화면 깔끔하게 유지

#### 7.2 채팅 시스템
**결정**: **텍스트 채팅**
- 일반적인 텍스트 채팅 구현
- 음성 채팅은 향후 확장 사항
- 빠른 명령(미리 정의된 메시지)도 지원

#### 7.3 핑 표시
**결정**: **색상 표시**
- 숫자 표시 대신 색상으로 표시
- 녹색: 좋음 (< 100ms)
- 노란색: 보통 (100-300ms)
- 빨간색: 나쁨 (> 300ms)

### 8. 저장 및 재개

#### 8.1 세션 저장
**결정**: **호스트만 저장**
- 호스트만 게임 상태를 저장
- 저장 파일은 호스트의 로컬에 저장
- 클라이언트는 저장 불가

#### 8.2 세션 재개
**결정**: **호스트만 재개 가능**
- 호스트만 저장 파일을 불러올 수 있음
- 저장 파일 공유 필요 없음
- 호스트가 불러오면 클라이언트들이 자동으로 동기화

### 9. 보안 및 치트 방지

#### 9.1 입력 검증 레벨
**결정**: **엄격한 검증**
- 모든 입력을 서버(호스트)에서 엄격히 검증
- 범위 체크, 가능한 액션 확인, 리소스 확인 모두 수행
- 비정상적인 입력은 즉시 거부

#### 9.2 상태 동기화 방식
**결정**: **호스트 권위**
- 호스트가 게임 상태의 유일한 권위자
- 모든 중요한 결정은 호스트에서 수행
- 클라이언트는 입력만 전송하고 결과를 수신

### 10. 모드별 특수 규칙

#### 10.1~10.3 특수 규칙
**결정**: **특수 규칙 없음**
- 2인/3인/4인 모드 모두 동일한 규칙
- 밸런스 조정 없음 (싱글플레이와 동일)
- 단순히 플레이어 수만 다름

---

## 구현 설정 값

다음은 구현 시 사용할 상수 값들입니다:

```python
# 전투 합류 관련
COMBAT_JOIN_ATB_INITIAL = 0  # 0부터 시작
COMBAT_JOIN_TIME_LIMIT = None  # 제한 없음
COMBAT_JOIN_ENEMY_REACTION = "recalculate_threat"  # 위협 재계산

# 플레이어 수별 밸런스
ENEMY_COUNT_MULTIPLIER = 1.0  # 싱글과 동일
ENEMY_HP_MULTIPLIER = 1.0  # 싱글과 동일
ENEMY_DAMAGE_MULTIPLIER = 1.0  # 싱글과 동일
EXP_DIVIDE_BY_PARTICIPANTS = True  # 참여 전투원 수로 나눔
INVENTORY_WEIGHT_MULTIPLIER = 1.0  # 싱글과 동일

# 전투 시스템
ACTION_WAIT_TIME = 1.5  # 1.5초 고정
ATB_REDUCTION_MULTIPLIER = 0.02  # 1/50 고정
PARTICIPATION_RADIUS = 5  # 5 타일 고정

# 인벤토리 시스템
ITEM_USE_PERMISSION = "free"  # 자유 사용
ITEM_DISTRIBUTION = "shared_storage"  # 공유 저장
GOLD_MANAGEMENT = "fully_shared"  # 완전 공유

# 던전 생성
DUNGEON_SEED_SOURCE = "host"  # 호스트 생성
DUNGEON_SIZE_MODE = "fixed"  # 고정 크기

# 네트워크 및 성능
SYNC_INTERVAL_POSITION = 0.1  # 0.1초 (10 FPS)
SYNC_INTERVAL_STATE = 0.1  # 0.1초 (10 FPS)
SYNC_INTERVAL_ENEMY = 0.5  # 0.5초 (2 FPS)
MESSAGE_COMPRESSION = True  # 압축 사용
MAX_LATENCY_ALLOWED = 0.5  # 0.5초 (일반적)

# UI/UX
PLAYER_INFO_DISPLAY = "toggle"  # 토글 표시
CHAT_SYSTEM_TYPE = "text"  # 텍스트 채팅
PING_DISPLAY_TYPE = "color"  # 색상 표시

# 저장 및 재개
SESSION_SAVE_HOST_ONLY = True  # 호스트만 저장
SESSION_RESUME_HOST_ONLY = True  # 호스트만 재개

# 보안 및 치트 방지
INPUT_VALIDATION_LEVEL = "strict"  # 엄격한 검증
STATE_SYNC_MODE = "host_authority"  # 호스트 권위

# 모드별 특수 규칙
SPECIAL_RULES_2P = False  # 특수 규칙 없음
SPECIAL_RULES_3P = False  # 특수 규칙 없음
SPECIAL_RULES_4P = False  # 특수 규칙 없음
```

---

## 설계 결정 필요 요소 (참고용 - 결정 완료)

다음 요소들은 게임 디자인 결정이 필요하며, 각 옵션의 장단점을 비교하여 선택해야 합니다.

### 1. 전투 합류 관련

#### 1.1 ATB 초기화 방식
- **옵션**: 0부터 시작 / 랜덤 초기화 / 평균 맞춤 / 설정 가능한 퍼센트
- **고려사항**: 공정성, 게임플레이 영향
- **권장**: 0부터 시작 또는 평균 맞춤

#### 1.2 합류 시간 제한
- **옵션**: 제한 없음 / 시간 제한 (예: 10초) / 턴 제한 (예: 3턴) / HP 제한
- **고려사항**: 게임 밸런스, 전략성
- **권장**: 제한 없음 또는 시간 제한

#### 1.3 합류 시 적의 반응
- **옵션**: 반응 없음 / 위협 재계산 / 특수 행동
- **고려사항**: 게임플레이 다양성
- **권장**: 위협 재계산

### 2. 플레이어 수별 밸런스

#### 2.1 적 수 조정
- **2인**: 적 수 80% / 90% / 100% 중 선택
- **3인**: 적 수 100% (기준)
- **4인**: 적 수 120% / 130% / 150% 중 선택

#### 2.2 적 체력/데미지 조정
- 각 모드별로 적의 HP와 데미지를 조정할지 결정
- 플레이어 수가 많을수록 적이 강해져야 하는지

#### 2.3 경험치/보상 분배
- **고정 보상**: 모드와 관계없이 동일
- **비례 보상**: 플레이어 수에 비례
- **감소 보상**: 플레이어 수가 많을수록 개인당 경험치 감소

#### 2.4 인벤토리 용량
- **고정**: 모든 모드에서 동일
- **비례**: 플레이어 수에 비례 증가
- **공식**: `base_weight + (player_count * weight_per_player)`

### 3. 전투 시스템

#### 3.1 행동 선택 대기 시간
- **1.5초 고정** (현재 설계)
- 또는 **설정 가능** (0.5초 ~ 3초)

#### 3.2 ATB 감소 배율
- **1/50 고정** (현재 설계)
- 또는 **설정 가능** (1/30, 1/50, 1/100 등)

#### 3.3 근처 아군 판정 반경
- **5 타일 고정**
- 또는 **설정 가능** (3, 5, 7, 10 타일)

### 4. 인벤토리 시스템

#### 4.1 아이템 사용 권한
- **자유 사용**: 누구나 아이템 사용 가능
- **획득자 우선**: 획득한 플레이어만 사용 가능
- **권한 시스템**: 특정 아이템은 특정 플레이어만 사용

#### 4.2 아이템 분배
- **자동 분배**: 획득 시 자동으로 분배 (예: 포션 4개 → 각 1개씩)
- **수동 분배**: 플레이어가 직접 결정
- **공유 저장**: 인벤토리에만 저장, 필요 시 사용

#### 4.3 골드 관리
- **완전 공유**: 모든 골드 공유
- **개인 골드**: 플레이어별 골드 + 공유 골드
- **분배**: 획득 시 자동 분배

### 5. 던전 생성

#### 5.1 시드 생성 방식
- **호스트 생성**: 호스트가 시드 생성 후 전송
- **협의 생성**: 모든 플레이어가 합의한 시드 사용
- **날짜 기반**: 오늘 날짜를 시드로 사용 (같은 날에는 같은 던전)

#### 5.2 던전 크기 조정
- **고정 크기**: 모드와 관계없이 동일
- **비례 크기**: 플레이어 수에 비례 증가

### 6. 네트워크 및 성능

#### 6.1 동기화 주기
- **캐릭터 위치**: 0.1초 (10 FPS) / 0.2초 (5 FPS) / 0.5초 (2 FPS)
- **캐릭터 상태**: 0.1초 (10 FPS) / 이벤트 기반
- **적 위치**: 0.5초 (2 FPS) / 2초 (이미 설정됨)

#### 6.2 메시지 압축
- **압축 사용**: gzip, zlib 등
- **압축 안 함**: 원본 전송
- **선택적 압축**: 큰 메시지만 압축

#### 6.3 최대 지연 시간 허용
- **0.1초 이하**: 매우 엄격
- **0.5초 이하**: 일반적
- **1초 이하**: 느슨함

### 7. UI/UX

#### 7.1 플레이어 정보 표시
- **항상 표시**: 화면에 모든 플레이어 정보 표시
- **토글 표시**: 키로 토글
- **미니맵**: 미니맵에서만 확인

#### 7.2 채팅 시스템
- **텍스트 채팅**: 일반적인 채팅
- **음성 채팅**: 음성 통신 (별도 구현 필요)
- **빠른 명령**: 미리 정의된 메시지 (예: "도와줘!", "따라와!")

#### 7.3 핑 표시
- **숫자 표시**: ms 단위로 표시
- **색상 표시**: 녹색/노란색/빨간색으로 표시
- **숨김**: 표시하지 않음

### 8. 저장 및 재개

#### 8.1 세션 저장
- **호스트만 저장**: 호스트의 저장 파일 사용
- **모든 플레이어 저장**: 각자 저장 파일 생성
- **공유 저장**: 중앙 서버에 저장 (P2P에서는 어려움)

#### 8.2 세션 재개
- **호스트만 재개 가능**: 호스트가 저장 파일 불러오기
- **어느 플레이어나 재개**: 저장 파일 공유 후 재개

### 9. 보안 및 치트 방지

#### 9.1 입력 검증 레벨
- **기본 검증**: 범위 체크만
- **중간 검증**: 가능한 액션인지 확인
- **엄격한 검증**: 모든 입력을 서버에서 재검증

#### 9.2 상태 동기화 방식
- **호스트 권위**: 호스트가 모든 것을 결정
- **합의 방식**: 모든 클라이언트의 합의 필요 (P2P에는 부적합)
- **하이브리드**: 중요 액션만 호스트 권위

### 10. 모드별 특수 규칙

#### 10.1 2인 모드 특수 규칙
- 추가 보상 / 특수 던전 / 챌린지 모드 등

#### 10.2 3인 모드 특수 규칙
- 밸런스 조정 / 특수 메커니즘 등

#### 10.3 4인 모드 특수 규칙
- 레이드 모드 / 대형 보스 등

---

## 결정 체크리스트

다음 사항들을 결정해야 합니다:

### 필수 결정 사항

- [ ] 전투 합류 시 ATB 초기화 방식
- [ ] 전투 합류 시간 제한 유무
- [ ] 플레이어 수별 적 수 조정 비율
- [ ] 플레이어 수별 경험치/보상 분배 방식
- [ ] 인벤토리 아이템 사용 권한
- [ ] 골드 관리 방식
- [ ] 동기화 주기 (캐릭터 위치, 상태 등)
- [ ] 메시지 압축 사용 여부

### 선택 결정 사항

- [ ] 행동 선택 대기 시간 (1.5초 고정 또는 설정 가능)
- [ ] ATB 감소 배율 (1/50 고정 또는 설정 가능)
- [ ] 근처 아군 판정 반경
- [ ] 던전 크기 조정
- [ ] 채팅 시스템 타입
- [ ] 핑 표시 방식
- [ ] 세션 저장 방식

### 향후 확장 사항

- [ ] 모드별 특수 규칙
- [ ] 음성 채팅
- [ ] 리플레이 시스템
- [ ] 리더보드/랭킹

---

## 맵 탐험 시스템

### 개별 캐릭터 이동

#### 플레이어 객체 구조

```python
@dataclass
class MultiplayerPlayer:
    """멀티플레이 플레이어"""
    player_id: str  # 고유 ID
    player_name: str  # 플레이어 이름
    x: int
    y: int
    party: List[Character]  # 플레이어의 파티 (최대 4명)
    character_id: str  # 현재 조작 중인 캐릭터 ID
    
    # 네트워크 동기화용
    last_update_time: float = 0.0
    velocity_x: float = 0.0  # 예측용 속도
    velocity_y: float = 0.0
```

#### 이동 동기화

```python
class MultiplayerExplorationSystem(ExplorationSystem):
    """멀티플레이 탐험 시스템"""
    
    def __init__(self, ...):
        super().__init__(...)
        self.players: Dict[str, MultiplayerPlayer] = {}  # {player_id: Player}
        self.is_host = False
        self.network_manager = None
    
    def update_player_movement(self, player_id: str, dx: int, dy: int):
        """플레이어 이동 업데이트"""
        if player_id not in self.players:
            return
        
        player = self.players[player_id]
        
        # 이동 검증 (호스트만)
        if self.is_host:
            new_x = player.x + dx
            new_y = player.y + dy
            
            # 맵 경계 및 이동 가능 여부 확인
            if self.dungeon.is_walkable(new_x, new_y):
                player.x = new_x
                player.y = new_y
                
                # 모든 클라이언트에게 이동 브로드캐스트
                self.network_manager.broadcast({
                    "type": "player_move",
                    "player_id": player_id,
                    "x": new_x,
                    "y": new_y,
                    "timestamp": time.time()
                })
        else:
            # 클라이언트: 호스트에게 이동 요청만 전송
            self.network_manager.send({
                "type": "move_request",
                "player_id": player_id,
                "dx": dx,
                "dy": dy
            })
    
    def handle_player_move(self, message: dict):
        """플레이어 이동 메시지 처리"""
        player_id = message["player_id"]
        new_x = message["x"]
        new_y = message["y"]
        
        if player_id in self.players:
            player = self.players[player_id]
            
            # 보간을 위한 정보 저장
            player.velocity_x = new_x - player.x
            player.velocity_y = new_y - player.y
            player.last_update_time = time.time()
            
            # 위치 업데이트 (보간 적용)
            player.x = new_x
            player.y = new_y
```

### 적의 움직임 (2초 간격)

```python
class MultiplayerEnemyAI:
    """멀티플레이 적 AI (2초 간격 이동)"""
    
    def __init__(self):
        self.last_move_time: Dict[str, float] = {}  # {enemy_id: timestamp}
        self.MOVE_INTERVAL = 2.0  # 2초 간격
    
    def update(self, delta_time: float, enemies: List[Enemy], dungeon: DungeonMap, is_host: bool):
        """적 AI 업데이트"""
        current_time = time.time()
        
        for enemy in enemies:
            enemy_id = enemy.id
            
            # 마지막 이동 시간 확인
            last_move = self.last_move_time.get(enemy_id, 0)
            elapsed = current_time - last_move
            
            # 2초가 지났으면 이동
            if elapsed >= self.MOVE_INTERVAL:
                if is_host:
                    # 호스트만 실제 AI 로직 실행
                    self.move_enemy(enemy, dungeon)
                    
                    # 모든 클라이언트에게 적 이동 브로드캐스트
                    self.network_manager.broadcast({
                        "type": "enemy_move",
                        "enemy_id": enemy_id,
                        "x": enemy.x,
                        "y": enemy.y,
                        "timestamp": current_time
                    })
                
                self.last_move_time[enemy_id] = current_time
    
    def move_enemy(self, enemy: Enemy, dungeon: DungeonMap):
        """적 이동 로직 실행"""
        # 기존 AI 로직 사용 (enemy_ai.py)
        from src.ai.enemy_ai import EnemyAI
        ai = EnemyAI()
        
        # 플레이어 위치 찾기 (가장 가까운 플레이어)
        nearest_player = self.find_nearest_player(enemy)
        
        if nearest_player:
            ai.act(enemy, nearest_player, dungeon)
```

---

## 던전 생성 동기화

### 시드 기반 던전 생성

```python
class MultiplayerDungeonGenerator(DungeonGenerator):
    """멀티플레이 던전 생성기 (시드 기반)"""
    
    def __init__(self, seed: Optional[int] = None, ...):
        super().__init__(...)
        self.seed = seed
        if seed is not None:
            random.seed(seed)
            import numpy as np
            np.random.seed(seed)
    
    def generate(self, floor_number: int = 1, seed: Optional[int] = None) -> DungeonMap:
        """던전 생성 (시드 기반)"""
        # 시드 설정
        if seed is not None:
            self.seed = seed
            random.seed(seed)
            import numpy as np
            np.random.seed(seed)
        
        # 부모 클래스 메서드 호출 (시드가 이미 설정됨)
        dungeon = super().generate(floor_number)
        
        # 시드 정보 저장 (재현 가능성)
        dungeon.seed = self.seed
        dungeon.floor_number = floor_number
        
        return dungeon


class MultiplayerSession:
    """멀티플레이 세션 관리"""
    
    def __init__(self):
        self.session_seed = random.randint(0, 2**31 - 1)  # 세션 시드 생성
        self.floors: Dict[int, DungeonMap] = {}  # {floor: dungeon}
    
    def generate_dungeon_for_floor(self, floor_number: int) -> DungeonMap:
        """층별 던전 생성 (시드 기반)"""
        # 층별로 고유한 시드 생성
        floor_seed = hash((self.session_seed, floor_number))
        
        generator = MultiplayerDungeonGenerator(seed=floor_seed)
        dungeon = generator.generate(floor_number)
        
        # 캐싱
        self.floors[floor_number] = dungeon
        
        return dungeon
    
    def get_dungeon(self, floor_number: int) -> DungeonMap:
        """던전 가져오기 (생성되지 않았으면 생성)"""
        if floor_number not in self.floors:
            return self.generate_dungeon_for_floor(floor_number)
        return self.floors[floor_number]
```

### 시드 초기화

```python
class MultiplayerNetworkManager:
    """멀티플레이 네트워크 관리자"""
    
    def on_session_start(self):
        """세션 시작 시 시드 생성 및 전송"""
        if self.is_host:
            # 호스트가 시드 생성
            session_seed = random.randint(0, 2**31 - 1)
            self.session.session_seed = session_seed
            
            # 모든 클라이언트에게 시드 전송
            self.broadcast({
                "type": "session_seed",
                "seed": session_seed
            })
    
    def handle_session_seed(self, message: dict):
        """세션 시드 수신"""
        if not self.is_host:
            seed = message["seed"]
            self.session.session_seed = seed
            
            # 동일한 던전 생성 가능
            dungeon = self.session.get_dungeon(1)
```

---

## 상태 동기화

### 상시 캐릭터 상태 동기화

```python
class CharacterStateSync:
    """캐릭터 상태 동기화 관리"""
    
    def __init__(self):
        self.sync_interval = 0.1  # 0.1초마다 동기화 (10 FPS)
        self.last_sync_time = 0.0
    
    def should_sync(self, current_time: float) -> bool:
        """동기화 필요 여부 확인"""
        return current_time - self.last_sync_time >= self.sync_interval
    
    def create_state_snapshot(self, character: Character) -> dict:
        """캐릭터 상태 스냅샷 생성"""
        return {
            "id": character.id,
            "hp": character.current_hp,
            "max_hp": character.max_hp,
            "mp": character.current_mp,
            "max_mp": character.max_mp,
            "brv": getattr(character, 'current_brv', 0),
            "max_brv": getattr(character, 'max_brv', 0),
            "status_effects": [
                {
                    "type": se.type.value,
                    "stacks": se.stacks,
                    "duration": se.duration
                }
                for se in getattr(character, 'status_effects', [])
            ],
            "position": {
                "x": getattr(character, 'x', None),
                "y": getattr(character, 'y', None)
            }
        }
    
    def apply_state_update(self, character: Character, state: dict):
        """상태 업데이트 적용"""
        # HP/MP/BRV 동기화
        character.current_hp = state["hp"]
        character.current_mp = state["mp"]
        if hasattr(character, 'current_brv'):
            character.current_brv = state["brv"]
        
        # 상태 효과 동기화
        # (상태 효과는 호스트에서 결정하고 브로드캐스트)
        
        # 위치 동기화 (있으면)
        if "position" in state and state["position"]:
            if hasattr(character, 'x'):
                character.x = state["position"]["x"]
            if hasattr(character, 'y'):
                character.y = state["position"]["y"]
    
    def broadcast_all_characters(self, characters: List[Character], network_manager):
        """모든 캐릭터 상태 브로드캐스트"""
        current_time = time.time()
        
        if not self.should_sync(current_time):
            return
        
        states = [self.create_state_snapshot(c) for c in characters]
        
        network_manager.broadcast({
            "type": "character_states_update",
            "characters": states,
            "timestamp": current_time
        })
        
        self.last_sync_time = current_time
```

### 동기화 주기 설정

| 상태 종류 | 동기화 주기 | 이유 |
|----------|------------|------|
| 캐릭터 위치 (맵) | 0.1초 (10 FPS) | 빠른 이동 추적 필요 |
| 캐릭터 HP/MP/BRV | 0.1초 (10 FPS) | 전투 중 중요 |
| 상태 효과 | 이벤트 기반 | 변화 시에만 |
| 적 위치 | 0.5초 (2 FPS) | 2초 간격 이동이므로 |
| 인벤토리 | 이벤트 기반 | 변경 시에만 |
| 전투 상태 | 실시간 (프레임마다) | ATB 게이지 등 중요 |

---

## 인벤토리 시스템

### 파티 공유 인벤토리

```python
class SharedInventory(Inventory):
    """파티 공유 인벤토리 (멀티플레이)"""
    
    def __init__(self, ...):
        super().__init__(...)
        self.lock = asyncio.Lock()  # 동시 접근 방지
        self.network_manager = None
    
    async def add_item(self, item: Item, player_id: str) -> bool:
        """아이템 추가 (멀티플레이)"""
        async with self.lock:
            # 인벤토리에 추가
            success = super().add_item(item)
            
            if success and self.network_manager:
                # 모든 플레이어에게 인벤토리 업데이트 브로드캐스트
                await self.network_manager.broadcast({
                    "type": "inventory_update",
                    "action": "add",
                    "item": item.serialize(),
                    "added_by": player_id,
                    "inventory_state": self.serialize()
                })
            
            return success
    
    async def remove_item(self, item_id: str, player_id: str) -> Optional[Item]:
        """아이템 제거 (멀티플레이)"""
        async with self.lock:
            item = super().remove_item(item_id)
            
            if item and self.network_manager:
                # 모든 플레이어에게 인벤토리 업데이트 브로드캐스트
                await self.network_manager.broadcast({
                    "type": "inventory_update",
                    "action": "remove",
                    "item_id": item_id,
                    "removed_by": player_id,
                    "inventory_state": self.serialize()
                })
            
            return item
    
    async def use_item(self, item_id: str, target: Any, player_id: str) -> bool:
        """아이템 사용 (멀티플레이)"""
        async with self.lock:
            # 아이템 사용 (호스트에서 검증)
            success = super().use_item(item_id, target)
            
            if success and self.network_manager:
                # 사용 결과 브로드캐스트
                await self.network_manager.broadcast({
                    "type": "item_used",
                    "item_id": item_id,
                    "target_id": getattr(target, 'id', None),
                    "used_by": player_id,
                    "result": self.get_item_result(item_id, target)
                })
            
            return success
```

### 동시 접근 제어

```python
class InventoryLockManager:
    """인벤토리 잠금 관리 (트랜잭션)"""
    
    def __init__(self):
        self.active_transactions: Dict[str, Transaction] = {}  # {transaction_id: Transaction}
        self.transaction_timeout = 5.0  # 5초 타임아웃
    
    async def begin_transaction(self, player_id: str) -> str:
        """트랜잭션 시작"""
        transaction_id = f"{player_id}_{time.time()}"
        
        transaction = Transaction(
            id=transaction_id,
            player_id=player_id,
            start_time=time.time()
        )
        
        self.active_transactions[transaction_id] = transaction
        
        # 타임아웃 체크 (백그라운드 태스크)
        asyncio.create_task(self.check_timeout(transaction_id))
        
        return transaction_id
    
    async def commit_transaction(self, transaction_id: str):
        """트랜잭션 커밋"""
        if transaction_id in self.active_transactions:
            del self.active_transactions[transaction_id]
    
    async def check_timeout(self, transaction_id: str):
        """트랜잭션 타임아웃 체크"""
        await asyncio.sleep(self.transaction_timeout)
        
        if transaction_id in self.active_transactions:
            transaction = self.active_transactions[transaction_id]
            if time.time() - transaction.start_time > self.transaction_timeout:
                # 타임아웃: 트랜잭션 제거
                del self.active_transactions[transaction_id]
                # 플레이어에게 알림
                await self.notify_timeout(transaction.player_id)
```

---

## 추가 고려사항

### 1. 네트워크 지연 보정 (Lag Compensation)

```python
class LagCompensation:
    """네트워크 지연 보정"""
    
    def __init__(self):
        self.ping_history: Dict[str, List[float]] = {}  # {player_id: [ping, ...]}
        self.client_timestamps: Dict[str, float] = {}  # {action_id: timestamp}
    
    def calculate_ping(self, player_id: str) -> float:
        """평균 핑 계산"""
        if player_id not in self.ping_history:
            return 0.0
        
        pings = self.ping_history[player_id]
        if not pings:
            return 0.0
        
        # 최근 10개의 평균
        recent_pings = pings[-10:]
        return sum(recent_pings) / len(recent_pings)
    
    def apply_lag_compensation(self, action: dict, player_id: str):
        """지연 보정 적용"""
        ping = self.calculate_ping(player_id)
        action_timestamp = action.get("timestamp", 0)
        current_time = time.time()
        
        # 지연 시간 계산
        lag = current_time - action_timestamp
        
        # 서버 시간으로 보정
        compensated_time = action_timestamp + (lag / 2)  # 왕복 시간의 절반
        
        action["compensated_timestamp"] = compensated_time
        return action
```

### 2. 입력 큐잉 및 순서 보장

```python
class InputQueue:
    """입력 큐 (순서 보장)"""
    
    def __init__(self):
        self.queue: List[InputMessage] = []
        self.last_processed_sequence = -1
    
    def add_input(self, input_msg: InputMessage):
        """입력 추가"""
        # 시퀀스 번호 확인
        if input_msg.sequence <= self.last_processed_sequence:
            # 이미 처리된 입력 (무시)
            return
        
        # 큐에 추가 (정렬)
        self.queue.append(input_msg)
        self.queue.sort(key=lambda x: x.sequence)
    
    def process_next(self) -> Optional[InputMessage]:
        """다음 입력 처리"""
        if not self.queue:
            return None
        
        # 다음 시퀀스 번호 확인
        next_sequence = self.last_processed_sequence + 1
        
        # 큐에서 찾기
        for i, msg in enumerate(self.queue):
            if msg.sequence == next_sequence:
                # 처리
                self.queue.pop(i)
                self.last_processed_sequence = next_sequence
                return msg
            elif msg.sequence > next_sequence:
                # 순서가 맞지 않음 (이전 입력 누락)
                # 누락된 입력 요청
                self.request_missing_input(next_sequence)
                break
        
        return None
```

### 3. 플레이어 연결 끊김 처리

```python
class DisconnectionHandler:
    """연결 끊김 처리"""
    
    def __init__(self):
        self.disconnected_players: Dict[str, float] = {}  # {player_id: disconnect_time}
        self.reconnect_timeout = 30.0  # 30초 재연결 대기
    
    async def handle_disconnect(self, player_id: str):
        """플레이어 연결 끊김 처리"""
        disconnect_time = time.time()
        self.disconnected_players[player_id] = disconnect_time
        
        # 일시적으로 AI로 전환 (재연결 대기)
        await self.switch_to_ai(player_id)
        
        # 재연결 대기 (타임아웃 체크)
        asyncio.create_task(self.wait_for_reconnect(player_id))
    
    async def wait_for_reconnect(self, player_id: str):
        """재연결 대기"""
        await asyncio.sleep(self.reconnect_timeout)
        
        # 재연결 안 되면 영구 처리
        if player_id in self.disconnected_players:
            await self.handle_permanent_disconnect(player_id)
    
    async def handle_reconnect(self, player_id: str):
        """재연결 처리"""
        if player_id in self.disconnected_players:
            del self.disconnected_players[player_id]
            
            # AI에서 플레이어로 복귀
            await self.switch_to_player(player_id)
            
            # 상태 동기화
            await self.sync_player_state(player_id)
```

### 4. 전투 중 이탈 처리

```python
class CombatDisconnectHandler:
    """전투 중 이탈 처리"""
    
    async def handle_combat_disconnect(self, player_id: str, combat_manager: CombatManager):
        """전투 중 플레이어 이탈"""
        # 해당 플레이어의 캐릭터 찾기
        player_characters = [
            c for c in combat_manager.allies
            if getattr(c, 'player_id', None) == player_id
        ]
        
        for character in player_characters:
            # 옵션 1: AI로 전환
            # character.is_ai_controlled = True
            
            # 옵션 2: 전투에서 제거
            # combat_manager.allies.remove(character)
            
            # 옵션 3: 그대로 두고 다른 플레이어가 제어 가능하게
            character.player_id = None  # 소유권 해제
        
        # 다른 플레이어들에게 알림
        await self.notify_combat_disconnect(player_id, player_characters)
```

### 5. 동시 아이템 획득 처리

```python
class ItemPickupHandler:
    """아이템 획득 처리 (중복 방지)"""
    
    def __init__(self):
        self.picked_up_items: Set[str] = set()  # 획득된 아이템 ID
    
    async def handle_item_pickup(self, item_id: str, player_id: str, position: tuple):
        """아이템 획득 처리"""
        # 이미 획득된 아이템인지 확인
        if item_id in self.picked_up_items:
            # 거부 (다른 플레이어가 먼저 획득)
            return {
                "success": False,
                "reason": "already_picked_up"
            }
        
        # 획득 처리
        self.picked_up_items.add(item_id)
        
        # 모든 플레이어에게 아이템 제거 브로드캐스트
        await self.network_manager.broadcast({
            "type": "item_picked_up",
            "item_id": item_id,
            "player_id": player_id,
            "position": position
        })
        
        return {
            "success": True,
            "item_id": item_id
        }
```

### 6. 채팅/소통 시스템

```python
class ChatSystem:
    """채팅 시스템"""
    
    def __init__(self):
        self.message_history: List[ChatMessage] = []
        self.max_history = 100
    
    async def send_message(self, player_id: str, message: str):
        """채팅 메시지 전송"""
        chat_msg = ChatMessage(
            player_id=player_id,
            message=message,
            timestamp=time.time()
        )
        
        # 히스토리 추가
        self.message_history.append(chat_msg)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)
        
        # 모든 플레이어에게 브로드캐스트
        await self.network_manager.broadcast({
            "type": "chat_message",
            "player_id": player_id,
            "message": message,
            "timestamp": chat_msg.timestamp
        })
```

### 7. 핑/지연 시간 표시

```python
class PingDisplay:
    """핑 표시 시스템"""
    
    def __init__(self):
        self.ping_measurements: Dict[str, float] = {}  # {player_id: ping}
        self.update_interval = 1.0  # 1초마다 업데이트
    
    async def measure_ping(self, player_id: str):
        """핑 측정"""
        send_time = time.time()
        
        # 핑 메시지 전송
        await self.network_manager.send_to(player_id, {
            "type": "ping_request",
            "timestamp": send_time
        })
    
    def handle_pong(self, message: dict, player_id: str):
        """퐁 메시지 처리"""
        receive_time = time.time()
        send_time = message["timestamp"]
        
        ping = (receive_time - send_time) * 1000  # 밀리초
        
        self.ping_measurements[player_id] = ping
```

### 8. 리플레이/로깅

```python
class GameReplayLogger:
    """게임 리플레이 로거"""
    
    def __init__(self):
        self.actions: List[GameAction] = []
        self.session_start_time = time.time()
    
    def log_action(self, action: GameAction):
        """액션 로깅"""
        # 타임스탬프 추가
        action.timestamp = time.time() - self.session_start_time
        
        self.actions.append(action)
    
    def save_replay(self, filepath: str):
        """리플레이 저장"""
        replay_data = {
            "session_info": {
                "start_time": self.session_start_time,
                "seed": self.session_seed,
                "players": [p.id for p in self.players]
            },
            "actions": [a.serialize() for a in self.actions]
        }
        
        with open(filepath, 'w') as f:
            json.dump(replay_data, f, indent=2)
    
    def load_replay(self, filepath: str) -> List[GameAction]:
        """리플레이 로드"""
        with open(filepath, 'r') as f:
            replay_data = json.load(f)
        
        return [
            GameAction.deserialize(a) for a in replay_data["actions"]
        ]
```

### 9. 버전 호환성

```python
class VersionChecker:
    """버전 호환성 체크"""
    
    REQUIRED_VERSION = "5.0.0"
    MIN_SUPPORTED_VERSION = "5.0.0"
    
    def check_version(self, client_version: str) -> bool:
        """버전 호환성 확인"""
        # 간단한 버전 비교
        try:
            required_parts = [int(x) for x in self.REQUIRED_VERSION.split('.')]
            client_parts = [int(x) for x in client_version.split('.')]
            
            # 메이저 버전이 다르면 호환 안 됨
            if client_parts[0] != required_parts[0]:
                return False
            
            # 마이너 버전은 같거나 높아야 함
            if client_parts[1] < required_parts[1]:
                return False
            
            return True
        except:
            return False
```

### 10. 방 목록 및 매치메이킹 (향후 확장)

```python
class LobbySystem:
    """로비 시스템 (향후 확장)"""
    
    def __init__(self):
        self.active_sessions: List[GameSession] = []
    
    async def create_session(self, host_id: str, settings: dict) -> str:
        """세션 생성"""
        session_id = self.generate_session_id()
        
        session = GameSession(
            id=session_id,
            host_id=host_id,
            settings=settings
        )
        
        self.active_sessions.append(session)
        return session_id
    
    async def list_sessions(self) -> List[dict]:
        """세션 목록 조회"""
        return [
            {
                "id": s.id,
                "host": s.host_id,
                "players": len(s.players),
                "max_players": s.max_players,
                "settings": s.settings
            }
            for s in self.active_sessions
            if not s.is_full()
        ]
    
    async def join_session(self, session_id: str, player_id: str) -> bool:
        """세션 참여"""
        session = self.find_session(session_id)
        if not session:
            return False
        
        if session.is_full():
            return False
        
        session.add_player(player_id)
        return True
```

### 11. 보안 및 치트 방지

```python
class AntiCheat:
    """치트 방지 시스템"""
    
    def validate_action(self, action: dict, player_id: str) -> bool:
        """액션 검증"""
        # 1. 입력 범위 검증
        if not self.validate_input_range(action):
            return False
        
        # 2. 가능한 액션인지 확인
        if not self.validate_action_possibility(action, player_id):
            return False
        
        # 3. 쿨타임 확인
        if not self.validate_cooldown(action, player_id):
            return False
        
        # 4. 리소스 확인 (MP, HP 등)
        if not self.validate_resources(action, player_id):
            return False
        
        return True
    
    def detect_unusual_pattern(self, player_id: str) -> bool:
        """이상 패턴 감지"""
        # 너무 빠른 액션 실행
        # 불가능한 위치 이동
        # 비정상적인 데미지
        # 등등...
        pass
```

### 12. 네트워크 최적화

```python
class NetworkOptimizer:
    """네트워크 최적화"""
    
    def compress_message(self, message: dict) -> bytes:
        """메시지 압축"""
        json_str = json.dumps(message)
        compressed = gzip.compress(json_str.encode())
        return compressed
    
    def batch_updates(self, updates: List[dict]) -> dict:
        """업데이트 배치 처리"""
        return {
            "type": "batch_update",
            "updates": updates,
            "timestamp": time.time()
        }
    
    def delta_encoding(self, old_state: dict, new_state: dict) -> dict:
        """델타 인코딩 (변경된 부분만 전송)"""
        delta = {}
        
        for key, value in new_state.items():
            if key not in old_state or old_state[key] != value:
                delta[key] = value
        
        return delta
```

---

## 구현 순서

### Phase 1: 기반 구조 (2주)

1. 네트워크 레이어
   - P2P 연결 시스템 (WebSocket/AsyncIO)
   - 호스트/클라이언트 역할 구분
   - 기본 메시지 프로토콜

2. 게임 모드 분리
   - 싱글플레이/멀티플레이 모드 구분
   - 멀티플레이 전용 게임 상태 관리

### Phase 2: 맵 탐험 (2주)

1. 개별 캐릭터 이동
   - 플레이어별 위치 관리
   - 이동 동기화
   - 적의 2초 간격 움직임

2. 던전 생성 동기화
   - 시드 기반 던전 생성
   - 모든 클라이언트에서 동일 던전

### Phase 3: 실시간 전투 (3주)

1. ATB 시스템 개조
   - 실시간 ATB 증가
   - 행동 선택 중 1/50 감소 규칙
   - 1.5초 대기 예외 처리

2. 근처 아군만 참여
   - 전투 시작 조건
   - 참여 반경 계산

3. 전투 동기화
   - 액션 실행 동기화
   - 상태 업데이트

### Phase 4: 상태 동기화 (2주)

1. 캐릭터 상태 상시 동기화
   - HP/MP/BRV 동기화
   - 상태 효과 동기화
   - 주기적 업데이트

2. 인벤토리 공유
   - 파티 공유 인벤토리
   - 동시 접근 제어
   - 트랜잭션 처리

### Phase 5: 안정화 및 추가 기능 (2주)

1. 연결 끊김 처리
   - 재연결 로직
   - 전투 중 이탈 처리

2. 네트워크 최적화
   - 메시지 압축
   - 배치 업데이트
   - 지연 보정

3. UI 개선
   - 핑 표시
   - 채팅 시스템
   - 플레이어 상태 표시

---

## 결론

P2P 멀티플레이 구현은 싱글플레이와는 다른 독립적인 게임 모드로 설계됩니다. 실시간 전투, 개별 탐험, 파티 공유 인벤토리 등의 특징을 가지고 있으며, 추가 고려사항들을 통해 안정적이고 재미있는 멀티플레이 경험을 제공할 수 있습니다.

