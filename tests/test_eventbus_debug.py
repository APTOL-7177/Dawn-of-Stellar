"""
EventBus unhashable dict 오류 디버깅

실제 전투 시스템을 실행하면서 unhashable dict 오류를 추적합니다.
"""

import sys
from pathlib import Path
import traceback

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 설정 초기화
try:
    from src.core.config import initialize_config, get_config
    initialize_config("config.yaml")
except Exception as e:
    print(f"설정 초기화 오류: {e}")
    pass

from src.core.logger import get_logger
from src.core.event_bus import event_bus

logger = get_logger("eventbus_debug")

# EventBus.publish() 메서드를 패치하여 더 자세히 로깅
print("[DEBUG] EventBus publish 메서드 패치 중...")
original_publish = event_bus.publish

unhashable_errors = []

def patched_publish(event_name: str, data=None):
    """이벤트 발행 (오류 추적 개선)"""
    # 이벤트 히스토리 기록
    event_bus._event_history.append((event_name, data))
    if len(event_bus._event_history) > event_bus._max_history:
        event_bus._event_history.pop(0)

    # 구독자들에게 이벤트 전달
    for callback in event_bus._subscribers[event_name]:
        callback_name = callback.__name__ if hasattr(callback, '__name__') else str(callback)
        try:
            callback(data)
        except TypeError as e:
            error_msg = str(e)
            if "unhashable type" in error_msg:
                # unhashable dict 오류 상세 분석
                error_info = {
                    "event_name": event_name,
                    "callback": callback_name,
                    "error": error_msg,
                    "data_type": type(data).__name__ if data else "None",
                    "traceback": traceback.format_exc()
                }
                unhashable_errors.append(error_info)

                logger.error(f"\n{'='*70}")
                logger.error(f"[UNHASHABLE TYPE ERROR] {event_name}")
                logger.error(f"{'='*70}")
                logger.error(f"콜백: {callback_name}")
                logger.error(f"오류: {error_msg}")
                logger.error(f"이벤트 데이터 타입: {type(data).__name__ if data else 'None'}")

                if isinstance(data, dict):
                    logger.error(f"이벤트 데이터 키: {list(data.keys())}")
                    logger.error(f"데이터 값 타입:")
                    for k, v in data.items():
                        logger.error(f"  {k}: {type(v).__name__}")

                logger.error(f"스택 트레이스:\n{error_msg}")
                logger.error(f"{'='*70}")

                # 재발생시키지 않고 계속 진행 (다른 콜백도 실행되도록)
            else:
                raise
        except Exception as e:
            logger.error(f"[EventBus] 이벤트 콜백 실행 실패: {event_name}")
            logger.error(f"  콜백: {callback_name}")
            logger.error(f"  오류: {type(e).__name__}: {str(e)}")
            # 다른 예외는 재발생
            raise

event_bus.publish = patched_publish

from src.character.party import Party
from src.combat.combat_manager import CombatManager, ActionType

print("[DEBUG] EventBus 패치 완료\n")

class TestEventBusDebug:
    """EventBus 디버깅 테스트"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def test_gauge_update_with_events(self):
        """이벤트 발행을 포함한 게이지 업데이트 테스트"""
        print("\n[테스트] 게이지 업데이트 (이벤트 포함)")
        print("=" * 60)

        try:
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
                    self.status_manager = None
                    self.active_traits = []
                    self.equipment = {}

            allies = [MockCharacter("아군1")]
            enemies = [MockCharacter("적1")]

            print("[1] CombatManager 생성 및 전투 시작...")
            combat_manager = CombatManager()
            combat_manager.start_combat(allies, enemies)
            print("    [OK] 전투 시작")

            print("[2] 게이지 업데이트 (이벤트 발행 트리거)...")
            combat_manager.update_teamwork_gauge(
                action_type=ActionType.BRV_ATTACK,
                is_critical=False,
                caused_break=False,
                healed_ally=False,
                was_hit=False
            )
            print("    [OK] 게이지 업데이트 완료")

            print("[3] 게이지 값 확인...")
            assert combat_manager.party.teamwork_gauge == 5
            print(f"    [OK] 게이지: {combat_manager.party.teamwork_gauge}/600")

            self.passed += 1
            self.results.append((
                "PASS",
                "게이지 업데이트 (이벤트 포함) 성공"
            ))
            return True

        except Exception as e:
            self.failed += 1
            self.results.append((
                "FAIL",
                f"게이지 업데이트 실패: {str(e)}"
            ))
            print(f"[FAIL] {str(e)}")
            traceback.print_exc()
            return False

    def print_results(self):
        """결과 출력"""
        print("\n" + "=" * 60)
        print("[테스트 결과]")
        print("=" * 60)

        for status, message in self.results:
            symbol = "[OK]" if status == "PASS" else "[FAIL]"
            print(f"{symbol} {message}")

        print("\n" + "=" * 60)
        print(f"총 {self.passed + self.failed}개 테스트")
        print(f"성공: {self.passed}")
        print(f"실패: {self.failed}")
        print("=" * 60)

        if unhashable_errors:
            print("\n" + "=" * 70)
            print("[UNHASHABLE DICT ERRORS FOUND]")
            print("=" * 70)
            for i, error in enumerate(unhashable_errors, 1):
                print(f"\n에러 #{i}")
                print(f"  이벤트: {error['event_name']}")
                print(f"  콜백: {error['callback']}")
                print(f"  오류: {error['error']}")
                print(f"  데이터 타입: {error['data_type']}")
            print("=" * 70)

        if self.failed == 0 and not unhashable_errors:
            print("\n[SUCCESS] 모든 테스트 통과!")
            return 0
        else:
            print(f"\n[FAILED] 문제 발생")
            return 1


def main():
    """메인 테스트 실행"""
    tester = TestEventBusDebug()

    tester.test_gauge_update_with_events()

    result = tester.print_results()
    return result


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
