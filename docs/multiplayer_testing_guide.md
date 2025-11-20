# 멀티플레이 테스트 가이드

## 혼자서 멀티플레이 테스트하기

친구가 없어도 걱정하지 마세요! **모의 클라이언트(봇) 시스템**을 사용하면 혼자서도 멀티플레이를 완전히 테스트할 수 있습니다.

## 사용 방법

### 1. 테스트 도우미 사용

```python
from src.multiplayer.test_helper import create_test_session

# 2인 세션 생성 (호스트 1명 + 봇 1명)
session, helper = create_test_session(player_count=2)

# 또는 4인 세션 (호스트 1명 + 봇 3명)
session, helper = create_test_session(player_count=4)
```

### 2. 자동 시뮬레이션 실행

```python
import asyncio

async def test_multiplayer():
    # 세션 생성
    session, helper = create_test_session(player_count=2)
    
    # 자동 시뮬레이션 시작 (봇이 자동으로 움직임)
    await helper.start_auto_simulation(interval=2.0)  # 2초마다 행동
    
    # 테스트 실행...
    
    # 시뮬레이션 중지
    await helper.stop_auto_simulation()

# 실행
asyncio.run(test_multiplayer())
```

### 3. 수동으로 봇 추가/제거

```python
from src.multiplayer.test_helper import MultiplayerTestHelper

helper = MultiplayerTestHelper(session)

# 봇 추가
bot1 = helper.add_mock_client("봇1")
bot2 = helper.add_mock_client("봇2")

# 여러 봇 한 번에 추가
helper.add_bots(count=3, prefix="봇")

# 모든 봇 제거
helper.remove_all_bots()
```

### 4. 플레이어 위치 확인

```python
# 모든 플레이어의 위치 가져오기
positions = helper.get_player_positions()

for player_id, (x, y) in positions.items():
    player = session.players[player_id]
    print(f"{player.player_name}: ({x}, {y})")
```

## 테스트 시나리오

### 시나리오 1: 기본 2인 플레이

```python
# 2인 세션 생성
session, helper = create_test_session(player_count=2)

# 호스트와 봇 1명이 자동으로 추가됨
assert len(session.players) == 2
assert session.host_id is not None
```

### 시나리오 2: 봇이 자동으로 움직이는 테스트

```python
import asyncio

async def test_bot_movement():
    session, helper = create_test_session(player_count=2)
    
    # 초기 위치
    initial_positions = helper.get_player_positions()
    
    # 자동 시뮬레이션 시작
    await helper.start_auto_simulation(interval=1.0)
    
    # 3초 대기 (봇이 움직임)
    await asyncio.sleep(3.0)
    
    # 최종 위치 확인
    final_positions = helper.get_player_positions()
    
    # 위치가 변경되었는지 확인
    # (봇은 자동으로 이동하지만, 호스트는 수동 이동 필요)
    
    await helper.stop_auto_simulation()

asyncio.run(test_bot_movement())
```

### 시나리오 3: 네트워크 시뮬레이션

```python
# 네트워크 없이도 멀티플레이 로직 테스트
session, helper = create_test_session(player_count=4)

# 모든 플레이어가 세션에 있는지 확인
assert len(session.players) == 4

# 호스트 확인
host = session.players[session.host_id]
assert host.is_host is True
```

## 테스트 예제

자세한 테스트 예제는 `tests/test_multiplayer_exploration.py`를 참고하세요.

## 주의사항

1. **봇은 자동으로 움직입니다**: `start_auto_simulation()`을 호출하면 봇이 주기적으로 랜덤하게 이동합니다.
2. **호스트는 수동 제어**: 호스트 플레이어는 여전히 수동으로 조작해야 합니다.
3. **네트워크 없이 테스트 가능**: 실제 네트워크 연결 없이도 모든 멀티플레이 로직을 테스트할 수 있습니다.

## 실제 게임에서 테스트

실제로 2개의 게임 인스턴스를 실행하는 것도 가능합니다:

```bash
# 터미널 1: 호스트
python main.py --mode multiplayer --host

# 터미널 2: 클라이언트
python main.py --mode multiplayer --join localhost:5000
```

하지만 대부분의 테스트는 **봇 시스템**으로 충분합니다!

