# Advanced Bot AI System - Complete Implementation Plan

## Overview
고급 봇 AI 시스템 구현:
1. **지능형 움직임**: 의미있는 경로 선택
2. **파밍 시스템**: 자동 자원 수집
3. **소통 네트워크**: 봇 간 정보 공유
4. **향상된 커맨드**: 멀티태스킹 명령

---

## Part 1: 봇 간 소통 시스템 (Communication Network)

### Architecture
```
SharedKnowledge (싱글톤)
  ├─ discovered_items: {position: (item_type, timestamp)}
  ├─ harvested_nodes: {position: (node_type, harvested_time)}
  ├─ dangerous_areas: {position: (threat_level, timestamp)}
  └─ unexplored_areas: Set[position]
```

### Implementation
```python
class BotCommunicationNetwork:
    """봇 간 정보 공유 네트워크"""
    
    def __init__(self):
        # 공유 지식
        self.discovered_items = {}  # {(x, y): {"item": obj, "discovered_by": bot_id, "time": timestamp}}
        self.resource_nodes = {}    # {(x, y): {"type": "ingredient", "quantity": 3, "time": timestamp}}
        self.danger_zones = {}      # {(x, y): {"threat": "enemy", "level": 5, "time": timestamp}}
        self.interest_points = {}   # {(x, y): {"type": "chest|stairs|npc", "time": timestamp}}
    
    def share_item_location(self, bot_id, position, item):
        """아이템 위치 공유"""
        self.discovered_items[position] = {
            "item": item,
            "discovered_by": bot_id,
            "time": time.time()
        }
        logger.info(f"봇 {bot_id}가 아이템 위치 공유: {item.name} at {position}")
    
    def share_resource_node(self, bot_id, position, node_type, quantity):
        """자원 노드 공유"""
        self.resource_nodes[position] = {
            "type": node_type,
            "quantity": quantity,
            "discovered_by": bot_id,
            "time": time.time()
        }
    
    def get_nearest_unclaimed_item(self, current_pos, bot_id):
        """가장 가까운 미수집 아이템 찾기"""
        # 다른 봇이 수집 중이지 않은 아이템 중 가장 가까운 것
        pass
    
    def claim_item(self, position, bot_id):
        """아이템 수집 선언 (중복 방지)"""
        if position in self.discovered_items:
            self.discovered_items[position]["claimed_by"] = bot_id
```

---

## Part 2: 지능형 파밍 시스템

### Farming Strategy
```python
class FarmingBehavior:
    """파밍 행동 모듈"""
    
    def __init__(self, bot):
        self.bot = bot
        self.farming_priority = {
            "equipment": 10,      # 장비 최우선
            "ingredient": 8,      # 재료
            "consumable": 6,      # 소비품
            "gold": 5,            # 골드
            "cooking_item": 7     # 요리 재료
        }
    
    def should_farm(self, nearby_objects):
        """파밍 여부 결정"""
        # 인벤토리 공간 확인
        if self.bot.bot_inventory.is_full():
            return False
        
        # 가치있는 아이템이 있는지 확인
        valuable_items = self._filter_valuable(nearby_objects)
        return len(valuable_items) > 0
    
    def plan_farming_route(self, start, end, dungeon):
        """파밍 경로 계획 (시작점 → 종료점, 중간에 아이템 수집)"""
        # A* 경로에 가까운 아이템 포함
        base_path = self._pathfind(start, end)
        
        # 경로 근처의 아이템 찾기
        detours = []
        for pos in self.communication.discovered_items.keys():
            if self._is_near_path(pos, base_path, max_distance=3):
                detours.append(pos)
        
        # 최적화된 파밍 경로 생성
        optimized_path = self._optimize_with_detours(base_path, detours)
        return optimized_path
```

---

## Part 3: 향상된 커맨드 시스템

### Current Commands
```python
# 5번: 플레이어 따라가기
# 6번: 전투 회피 토글
```

### Enhanced Commands
```python
class BotCommand(Enum):
    # 기존
    FOLLOW_PLAYER = 1
    COMBAT_AVOIDANCE = 2
    
    # 신규
    FARM_AND_FOLLOW = 3      # 따라가면서 파밍
    GATHER_RESOURCES = 4     # 주변 자원 수집
    GOTO_AND_FARM = 5        # 특정 위치로 이동하며 파밍
    SHARE_LOCATION = 6       # 현재 위치 공유
    GOTO_SHARED_LOCATION = 7 # 공유된 위치로 이동
    DISTRIBUTE_ITEMS = 8     # 아이템 분배
    HOLD_POSITION = 9        # 현재 위치 대기
    SCOUT_AREA = 10          # 주변 정찰
```

### Command Modes
```python
class CommandMode:
    """커맨드 실행 모드"""
    
    SIMPLE = "simple"        # 단순 실행
    WITH_FARMING = "farm"    # 파밍하면서
    WITH_COMBAT = "combat"   # 전투하면서
    STEALTH = "stealth"      # 은신하면서
```

---

## Part 4: 지능형 움직임

### Movement Intelligence
```python
class IntelligentMovement:
    """지능형 이동 모듈"""
    
    def decide_next_action(self):
        """다음 행동 결정 (우선순위 기반)"""
        
        # 1순위: 위험 회피
        if self._detect_danger():
            return self._flee_from_danger()
        
        # 2순위: 명령 수행
        if self.current_command:
            return self._execute_command_intelligently()
        
        # 3순위: 파밍 기회
        if self._farming_opportunity_nearby():
            return self._farm_nearest_item()
        
        # 4순위: 플레이어 따라가기
        if self._player_too_far():
            return self._move_to_player()
        
        # 5순위: 탐험
        return self._explore_unknown_area()
    
    def _execute_command_intelligently(self):
        """명령을 지능적으로 수행"""
        command = self.current_command
        
        if command == BotCommand.FOLLOW_PLAYER:
            # 5번 키: 플레이어로 이동
            # 기본: 단순 이동
            # 개선: 경로상의 아이템 수집
            path = self._plan_path_to_player()
            
            # 경로 근처 아이템 체크
            nearby_items = self._check_items_near_path(path)
            if nearby_items:
                # 약간 우회해서 아이템 수집
                return self._detour_for_item(nearby_items[0])
            else:
                return self._move_along_path(path)
        
        elif command == BotCommand.FARM_AND_FOLLOW:
            # 새로운 6번 키: 적극적 파밍 + 따라가기
            # 플레이어 방향으로 이동하되, 모든 아이템 적극 수집
            return self._farm_while_moving_to_player()
```

---

## Part 5: 멀티태스킹 시스템

### Task Queue
```python
class TaskQueue:
    """작업 큐 (멀티태스킹)"""
    
    def __init__(self):
        self.tasks = []  # [(priority, task)]
    
    def add_task(self, task, priority):
        heapq.heappush(self.tasks, (priority, task))
    
    def get_next_task(self):
        if self.tasks:
            return heapq.heappop(self.tasks)[1]
        return None
    
    def can_multitask(self, task1, task2):
        """두 작업을 동시에 수행 가능한지"""
        # 예: 이동 + 파밍 = 가능
        #     전투 + 파밍 = 불가능
        compatible = {
            ("move", "farm"): True,
            ("move", "harvest"): True,
            ("combat", "farm"): False,
            ("follow", "farm"): True,
        }
        return compatible.get((task1.type, task2.type), False)
```

---

## Implementation Steps

### Step 1: Communication Network
**File**: `src/multiplayer/bot_communication.py` (NEW)

```python
class BotCommunicationNetwork:
    _instance = None  # 싱글톤
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_network()
        return cls._instance
    
    def _init_network(self):
        self.discovered_items = {}
        self.resource_nodes = {}
        self.shared_locations = {}
        self.bot_states = {}  # 각 봇의 현재 상태
```

### Step 2: Farming System
**File**: `ai_bot_advanced.py`

Add methods:
- `_scan_for_farmable_items()`
- `_plan_farming_route(start, end)`
- `_should_detour_for_item(item, current_path)`
- `_execute_farming_action()`

### Step 3: Enhanced Commands
**File**: `ai_bot_advanced.py`

Update:
- `execute_command()` 메서드 확장
- 새로운 커맨드 추가
- 커맨드 모드 시스템

### Step 4: Intelligent Movement
**File**: `ai_bot_advanced.py`

Update:
- `update()` 메서드 - 우선순위 기반 의사결정
- `_decide_exploration_action()` 개선
- 멀티태스킹 로직 추가

---

## Files to Create/Modify

### New Files
1. `src/multiplayer/bot_communication.py` - 소통 네트워크
2. `src/multiplayer/bot_tasks.py` - 작업 시스템

### Modified Files
1. `ai_bot_advanced.py`:
   - Communication network 통합
   - Farming 메서드 추가
   - Command 시스템 확장
   - Movement AI 개선

2. `world_ui.py` (or input handler):
   - 키보드 5,6번 커맨드 변경
   - 새로운 커맨드 UI

---

## User Experience Examples

### Example 1: 5번 키 (개선된 Follow)
**Before**:
```
[5] 봇이 플레이어에게 직선으로 이동
```

**After**:
```
[5] 봇이 플레이어에게 이동 + 경로상 아이템 수집
로그: "봇 BOT1: 플레이어로 이동 중... 아이템 발견! (포션)"
로그: "봇 BOT1: 포션 수집 완료, 이동 재개"
```

### Example 2: 6번 키 (New: Farm & Follow)
**Before**:
```
[6] 전투 회피 토글
```

**After**:
```
[6] 적극적 파밍 모드
로그: "봇 BOT1: 파밍 모드 활성화"
로그: "봇 BOT1: 주변 검색 중... 재료 3개 발견"
로그: "봇 BOT1: 버섯 채집 중..."
```

### Example 3: Communication
```
봇 BOT1: "아이템 발견! 전설 장비 at (25, 30)"
봇 BOT2: "위치 수신, 이동 중..."
플레이어: [알림] 봇들이 귀중한 아이템을 발견했습니다!
```

---

## Testing Checklist

- [ ] 봇 간 아이템 위치 공유
- [ ] 봇이 플레이어로 이동하며 아이템 수집
- [ ] 파밍 경로 최적화
- [ ] 중복 수집 방지 (claim 시스템)
- [ ] 5번 키: 이동 + 파밍
- [ ] 6번 키: 적극적 파밍 모드
- [ ] 봇 상태 로그 출력

---

## Priority Implementation Order

1. **Communication Network** (기반)
2. **Farming System** (핵심 기능)
3. **Enhanced Commands** (사용자 인터페이스)
4. **Intelligent Movement** (통합)

---

## Next Action
Part 1부터 순차 구현 시작
