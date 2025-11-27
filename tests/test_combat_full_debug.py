"""
전투 시스템 디버깅 테스트

EventBus unhashable dict 오류를 재현하고 분석합니다.
"""

import sys
from pathlib import Path
import traceback

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 설정 초기화
from src.core.config import initialize_config
initialize_config("config.yaml")

from src.core.logger import get_logger
from src.core.event_bus import event_bus, Events

logger = get_logger("test")

# EventBus 콜백 오류를 더 자세히 로깅하도록 패치
original_publish = event_bus.publish

def patched_publish(event_name: str, data=None):
    """이벤트 발행 (오류 추적 개선)"""
    # 이벤트 히스토리 기록
    event_bus._event_history.append((event_name, data))
    if len(event_bus._event_history) > event_bus._max_history:
        event_bus._event_history.pop(0)

    # 구독자들에게 이벤트 전달
    for callback in event_bus._subscribers[event_name]:
        try:
            callback(data)
        except TypeError as e:
            if "unhashable type" in str(e):
                # unhashable dict 오류 상세 분석
                logger.error(f"\n[EventBus] UNHASHABLE TYPE 오류 감지: {event_name}")
                logger.error(f"  콜백: {callback.__name__ if hasattr(callback, '__name__') else callback}")
                logger.error(f"  오류: {type(e).__name__}: {str(e)}")
                logger.error(f"  이벤트 데이터 타입: {type(data)}")
                if isinstance(data, dict):
                    logger.error(f"  이벤트 데이터 키: {list(data.keys())}")
                    logger.error(f"  이벤트 데이터 값 타입:")
                    for k, v in data.items():
                        logger.error(f"    - {k}: {type(v).__name__}")
                logger.error(f"  스택 트레이스:")
                for line in traceback.format_exc().split('\n'):
                    if line:
                        logger.error(f"    {line}")
                print(f"\n!!! UNHASHABLE TYPE 오류 감지: {event_name} !!!")
                raise
            else:
                raise
        except Exception as e:
            # 다른 오류 정보 로깅
            logger.error(f"[EventBus] 이벤트 콜백 실행 실패: {event_name}")
            logger.error(f"  콜백: {callback.__name__ if hasattr(callback, '__name__') else callback}")
            logger.error(f"  오류: {type(e).__name__}: {str(e)}")

event_bus.publish = patched_publish

print("\n" + "=" * 70)
print("전투 시스템 디버깅 테스트")
print("=" * 70)

try:
    # 필요한 모듈 임포트
    print("\n[1] 모듈 임포트 중...")
    from src.combat.combat_manager import CombatManager, ActionType
    from src.character.party import Party
    print("    [OK] 임포트 완료")

    # Mock 캐릭터 생성
    print("\n[2] Mock 캐릭터 생성 중...")

    # StatusManager mock
    class MockStatusManager:
        def can_act(self):
            return True
        def has_status(self, status_type):
            return False

    class MockCharacter:
        def __init__(self, name):
            self.name = name
            self.id = name
            self.current_hp = 100
            self.max_hp = 100
            self.current_mp = 50
            self.max_mp = 50
            self.atb_gauge = 0
            self.is_alive = True
            self.skills = []
            self.active_buffs = {}
            self.status_manager = MockStatusManager()
            self.active_traits = []
            self.equipment = {}
            self.current_brv = 0
            self.max_brv = 100
            self.speed = 10

        def heal(self, amount):
            self.current_hp = min(self.max_hp, self.current_hp + amount)
            return amount

        def take_damage(self, damage):
            self.current_hp = max(1, self.current_hp - damage)
            return damage

    allies = [MockCharacter(f"아군{i+1}") for i in range(2)]
    enemies = [MockCharacter(f"적{i+1}") for i in range(2)]
    print(f"    [OK] 완료 (아군 {len(allies)}명, 적 {len(enemies)}명)")

    # CombatManager 생성
    print("\n[3] CombatManager 생성 중...")
    manager = CombatManager()
    print("    [OK] 완료")

    # 전투 시작
    print("\n[4] 전투 시작 (CombatManager.start_combat) 중...")
    manager.start_combat(allies, enemies)
    print("    [OK] 전투 시작 완료")

    # 간단한 BRV 공격 실행
    print("\n[5] 첫 번째 공격 실행 (아군1 → 적1 BRV 공격) 중...")
    result1 = manager.execute_action(
        allies[0],
        ActionType.BRV_ATTACK,
        enemies[0]
    )
    print(f"    [OK] 공격 완료: {result1}")

    # 적의 공격
    print("\n[6] 두 번째 공격 실행 (적1 → 아군1 BRV 공격) 중...")
    result2 = manager.execute_action(
        enemies[0],
        ActionType.BRV_ATTACK,
        allies[0]
    )
    print(f"    [OK] 공격 완료: {result2}")

    # HP 공격
    print("\n[7] 세 번째 공격 실행 (아군1 → 적1 HP 공격) 중...")
    if enemies[0].current_brv > 0:
        result3 = manager.execute_action(
            allies[0],
            ActionType.HP_ATTACK,
            enemies[0]
        )
        print(f"    [OK] HP 공격 완료: {result3}")
    else:
        print("    [SKIP] BRV가 충분하지 않아서 스킵")

    print("\n" + "=" * 70)
    print("[SUCCESS] 전투 디버깅 테스트 완료!")
    print("=" * 70)

except Exception as e:
    print(f"\n[FAIL] 오류 발생: {str(e)}")
    print(traceback.format_exc())
    logger.error(f"전투 디버깅 테스트 실패: {e}", exc_info=True)
    sys.exit(1)
