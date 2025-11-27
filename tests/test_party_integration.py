"""
Party 클래스와 CombatManager 통합 테스트

전투 중 팀워크 게이지가 올바르게 작동하는지 확인합니다.
"""

import sys
from pathlib import Path

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

from src.character.party import Party
from src.combat.combat_manager import CombatManager, ActionType


class TestPartyIntegration:
    """Party와 CombatManager 통합 테스트"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def test_party_creation(self):
        """Party 생성 테스트"""
        print("\n[테스트] Party 생성")
        print("=" * 60)

        try:
            # Mock 캐릭터들
            class MockCharacter:
                def __init__(self, name):
                    self.name = name
                    self.current_hp = 100
                    self.max_hp = 100

            allies = [MockCharacter(f"캐릭터{i+1}") for i in range(4)]
            party = Party(allies)

            assert party.teamwork_gauge == 0, "초기 게이지는 0이어야 함"
            assert party.max_teamwork_gauge == 600, "최대 게이지는 600이어야 함"
            assert len(party.members) == 4, "멤버 수는 4여야 함"

            self.passed += 1
            self.results.append(("PASS", "Party 생성 성공"))
            return True

        except Exception as e:
            self.failed += 1
            self.results.append(("FAIL", f"Party 생성 실패: {str(e)}"))
            return False

    def test_combat_manager_integration(self):
        """CombatManager와의 통합 테스트"""
        print("\n[테스트] CombatManager 통합")
        print("=" * 60)

        try:
            # Mock 캐릭터들
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

                def heal(self, amount):
                    self.current_hp = min(self.max_hp, self.current_hp + amount)
                    return amount

                def take_damage(self, damage):
                    self.current_hp = max(1, self.current_hp - damage)

            allies = [MockCharacter(f"아군{i+1}") for i in range(2)]
            enemies = [MockCharacter(f"적{i+1}") for i in range(2)]

            # CombatManager 생성
            combat_manager = CombatManager()

            # 전투 시작
            combat_manager.start_combat(allies, enemies)

            # Party 초기화 확인
            assert combat_manager.party is not None, "Party가 None이면 안 됨"
            assert combat_manager.party.teamwork_gauge == 0, "초기 게이지는 0이어야 함"

            self.passed += 1
            self.results.append(("PASS", "CombatManager 통합 성공"))
            return True

        except Exception as e:
            self.failed += 1
            self.results.append(("FAIL", f"CombatManager 통합 실패: {str(e)}"))
            import traceback
            print(traceback.format_exc())
            return False

    def test_gauge_update(self):
        """게이지 업데이트 테스트"""
        print("\n[테스트] 게이지 업데이트")
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

            combat_manager = CombatManager()
            combat_manager.start_combat(allies, enemies)

            # 초기 게이지
            initial_gauge = combat_manager.party.teamwork_gauge
            assert initial_gauge == 0, "초기 게이지는 0이어야 함"

            # BRV 공격으로 게이지 증가
            combat_manager.update_teamwork_gauge(
                action_type=ActionType.BRV_ATTACK,
                is_critical=False,
                caused_break=False,
                healed_ally=False,
                was_hit=False
            )

            # 게이지 확인 (BRV_ATTACK = +5)
            assert combat_manager.party.teamwork_gauge == 5, f"게이지가 5여야 하는데 {combat_manager.party.teamwork_gauge}"

            # 크리티컬 보너스 (+3)
            combat_manager.update_teamwork_gauge(
                action_type=ActionType.HP_ATTACK,  # +8
                is_critical=True,  # +3
                caused_break=False,
                healed_ally=False,
                was_hit=False
            )

            # 게이지 확인 (5 + 8 + 3 = 16)
            assert combat_manager.party.teamwork_gauge == 16, f"게이지가 16이어야 하는데 {combat_manager.party.teamwork_gauge}"

            self.passed += 1
            self.results.append(("PASS", "게이지 업데이트 성공"))
            return True

        except Exception as e:
            self.failed += 1
            self.results.append(("FAIL", f"게이지 업데이트 실패: {str(e)}"))
            import traceback
            print(traceback.format_exc())
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

        if self.failed == 0:
            print("\n[SUCCESS] 모든 통합 테스트 통과!")
        else:
            print(f"\n[FAILED] {self.failed}개 테스트 실패")


def main():
    """메인 테스트 실행"""
    tester = TestPartyIntegration()

    tester.test_party_creation()
    tester.test_combat_manager_integration()
    tester.test_gauge_update()

    tester.print_results()

    return 0 if tester.failed == 0 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
