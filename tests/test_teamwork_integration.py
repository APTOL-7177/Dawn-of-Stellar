"""
팀워크 게이지 시스템 통합 테스트

모든 기능이 올바르게 작동하는지 확인합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.character.party import Party
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.character import Character
from src.combat.combat_manager import CombatManager, ActionType
from src.ui.teamwork_gauge_display import TeamworkGaugeDisplay, ChainPrompt
from src.ui.teamwork_battle_ui import TeamworkBattleUI, TeamworkSkillSelector
from src.character.skills.teamwork_effects import execute_teamwork_skill_effect
from src.core.logger import get_logger

logger = get_logger("test")


class TestTeamworkSystem:
    """팀워크 게이지 시스템 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.passed = 0
        self.failed = 0
        self.tests = []

    def assert_equal(self, actual, expected, message: str = ""):
        """값 비교"""
        if actual == expected:
            self.passed += 1
            self.tests.append(("PASS", message or f"{actual} == {expected}"))
            return True
        else:
            self.failed += 1
            self.tests.append(("FAIL", f"{message}: {actual} != {expected}"))
            return False

    def assert_true(self, condition, message: str = ""):
        """참 확인"""
        if condition:
            self.passed += 1
            self.tests.append(("PASS", message or "조건 참"))
            return True
        else:
            self.failed += 1
            self.tests.append(("FAIL", message or "조건 거짓"))
            return False

    # ========================================================================
    # 테스트: Party 클래스
    # ========================================================================

    def test_party_basic(self):
        """Party 기본 기능"""
        print("\n[테스트] Party 기본 기능")
        print("=" * 60)

        # 빈 파티 생성 (실제 Character 없이)
        party = Party([])

        # 초기값 확인
        self.assert_equal(party.teamwork_gauge, 0, "초기 게이지는 0")
        self.assert_equal(party.max_teamwork_gauge, 600, "최대 게이지는 600")
        self.assert_equal(party.chain_active, False, "초기에 연쇄 미활성")

        # 게이지 증가
        party.add_teamwork_gauge(100)
        self.assert_equal(party.teamwork_gauge, 100, "게이지 +100")

        # 게이지 상한선
        party.add_teamwork_gauge(600)
        self.assert_equal(party.teamwork_gauge, 600, "최대치 초과 방지")

        # 게이지 소모
        success = party.consume_teamwork_gauge(200)
        self.assert_true(success, "게이지 소모 성공")
        self.assert_equal(party.teamwork_gauge, 400, "게이지 -200")

        # 게이지 부족
        success = party.consume_teamwork_gauge(500)
        self.assert_true(not success, "게이지 부족으로 소모 실패")
        self.assert_equal(party.teamwork_gauge, 400, "게이지 변화 없음")

    def test_party_chain(self):
        """Party 연쇄 시스템"""
        print("\n[테스트] Party 연쇄 시스템")
        print("=" * 60)

        party = Party([])

        # 연쇄 시작
        class MockCharacter:
            name = "전사"

        starter = MockCharacter()
        party.start_chain(starter)

        self.assert_true(party.chain_active, "연쇄 활성화")
        self.assert_equal(party.chain_count, 1, "1단계 시작")
        self.assert_equal(party.chain_starter, starter, "시작자 저장")

        # 연쇄 계속 - 각 참가자의 스킬 전달
        # 게이지 100인 스킬 (4셀)
        skill_100 = TeamworkSkill("test2", "test2", "", gauge_cost=100)
        mp_cost = party.continue_chain(skill_100)
        self.assert_equal(party.chain_count, 2, "2단계")
        self.assert_equal(mp_cost, 4, "2단계 MP는 4 (100/25 * 2^0)")

        # 게이지 50인 스킬 (2셀)
        skill_50 = TeamworkSkill("test3", "test3", "", gauge_cost=50)
        mp_cost = party.continue_chain(skill_50)
        self.assert_equal(party.chain_count, 3, "3단계")
        self.assert_equal(mp_cost, 4, "3단계 MP는 4 (50/25 * 2^1)")

        # 게이지 75인 스킬 (3셀)
        skill_75 = TeamworkSkill("test4", "test4", "", gauge_cost=75)
        mp_cost = party.continue_chain(skill_75)
        self.assert_equal(mp_cost, 12, "4단계 MP는 12 (75/25 * 2^2)")

        # 연쇄 종료
        party.end_chain()
        self.assert_true(not party.chain_active, "연쇄 비활성화")
        self.assert_equal(party.chain_count, 0, "단계 초기화")

    # ========================================================================
    # 테스트: TeamworkSkill 클래스
    # ========================================================================

    def test_teamwork_skill_creation(self):
        """TeamworkSkill 생성"""
        print("\n[테스트] TeamworkSkill 생성")
        print("=" * 60)

        skill = TeamworkSkill(
            "test_skill",
            "테스트 스킬",
            "테스트 설명",
            gauge_cost=100
        )

        self.assert_equal(skill.skill_id, "test_skill", "스킬 ID")
        self.assert_equal(skill.name, "테스트 스킬", "스킬 이름")
        self.assert_equal(skill.teamwork_cost.gauge, 100, "게이지 비용")
        self.assert_true(skill.is_teamwork_skill, "팀워크 스킬 플래그")

    def test_teamwork_skill_mp_cost(self):
        """TeamworkSkill MP 비용 계산"""
        print("\n[테스트] TeamworkSkill MP 비용 계산")
        print("=" * 60)

        skill = TeamworkSkill("test", "test", "", gauge_cost=100)

        # 시작자는 MP 0
        mp_cost = skill.calculate_mp_cost(1)
        self.assert_equal(mp_cost, 0, "1단계 MP는 0")

        # 2단계부터 게이지 비용에 비례하는 지수적 증가
        # 게이지 100 (4셀) -> MP: (100/25) * 2^(n-2) = 4 * 2^(n-2)
        mp_cost = skill.calculate_mp_cost(2)
        self.assert_equal(mp_cost, 4, "2단계 MP는 4 (100/25 * 2^0)")

        mp_cost = skill.calculate_mp_cost(3)
        self.assert_equal(mp_cost, 8, "3단계 MP는 8 (100/25 * 2^1)")

        mp_cost = skill.calculate_mp_cost(4)
        self.assert_equal(mp_cost, 16, "4단계 MP는 16 (100/25 * 2^2)")

        mp_cost = skill.calculate_mp_cost(5)
        self.assert_equal(mp_cost, 32, "5단계 MP는 32 (100/25 * 2^3)")

    # ========================================================================
    # 테스트: UI 표시
    # ========================================================================

    def test_gauge_display(self):
        """게이지 표시"""
        print("\n[테스트] 게이지 표시")
        print("=" * 60)

        # 게이지 표시
        display = TeamworkGaugeDisplay.format_gauge(300, 600)
        self.assert_true("300/600" in display, "게이지 숫자 표시")
        self.assert_true("12셀" in display or "12" in display, "셀 표시")

        # 간단한 형식
        compact = TeamworkGaugeDisplay.format_compact(150, 600)
        self.assert_true("150" in compact, "간단한 형식에 숫자 포함")
        self.assert_true("6셀" in compact or "6" in compact, "셀 표시")

    def test_chain_prompt_display(self):
        """연쇄 제안 화면"""
        print("\n[테스트] 연쇄 제안 화면")
        print("=" * 60)

        prompt = ChainPrompt.format_prompt(
            chain_count=2,
            chain_starter_name="전사",
            current_skill_name="일제사격",
            current_skill_description="마킹된 모든 아군의 지원사격 발동",
            current_skill_cost=150,
            current_actor_name="궁수",
            teamwork_gauge=300,
            current_mp=45,
            required_mp=10
        )

        self.assert_true("일제사격" in prompt, "스킬 이름 포함")
        self.assert_true("마킹된 모든 아군" in prompt, "스킬 설명 포함")
        self.assert_true("150" in prompt, "게이지 비용 포함")
        self.assert_true("10" in prompt, "MP 비용 포함")

    # ========================================================================
    # 테스트: 효과 시스템
    # ========================================================================

    def test_teamwork_effects(self):
        """팀워크 스킬 효과"""
        print("\n[테스트] 팀워크 스킬 효과")
        print("=" * 60)

        # 효과 실행
        from src.character.skills.teamwork_effects import (
            damage_effect, heal_effect, buff_effect
        )

        class MockActor:
            name = "전사"
            class stat_manager:
                @staticmethod
                def get_value(stat):
                    if stat == "STRENGTH":
                        return 100
                    return 50

        class MockTarget:
            name = "고블린"
            current_hp = 100
            class stat_manager:
                @staticmethod
                def get_value(stat):
                    if stat == "MAX_HP":
                        return 100
                    return 50

        actor = MockActor()
        target = MockTarget()

        # 데미지
        dmg_result = damage_effect(actor, target, multiplier=2.0, damage_type='HP')
        self.assert_true(dmg_result["success"], "데미지 효과 성공")
        self.assert_true(dmg_result["damage"] > 0, "데미지 값 > 0")

        # 회복
        heal_result = heal_effect(actor, target, percentage=0.5)
        self.assert_true(heal_result["success"], "회복 효과 성공")
        self.assert_true(heal_result["healed"] > 0, "회복 값 > 0")

        # 버프
        buff_result = buff_effect(actor, target, stat="STRENGTH", multiplier=1.5, duration=3)
        self.assert_true(buff_result["success"], "버프 효과 성공")
        self.assert_equal(buff_result["duration"], 3, "버프 지속 3턴")

    # ========================================================================
    # 테스트: 전투 UI 통합
    # ========================================================================

    def test_battle_ui(self):
        """전투 UI 통합"""
        print("\n[테스트] 전투 UI 통합")
        print("=" * 60)

        # 게이지 상태
        gauge_display = TeamworkGaugeDisplay.format_compact(450, 600)
        self.assert_true("450" in gauge_display, "게이지 표시")

        # 스킬 정보
        skill_info = TeamworkGaugeDisplay.format_for_skill_menu(100, 450, 600)
        self.assert_true("100" in skill_info, "비용 표시")
        self.assert_true("450" in skill_info, "현재 게이지 표시")

    # ========================================================================
    # 결과 출력
    # ========================================================================

    def print_results(self):
        """테스트 결과 출력"""
        print("\n" + "=" * 60)
        print("[테스트 결과]")
        print("=" * 60)

        for status, message in self.tests:
            symbol = "[OK]" if status == "PASS" else "[FAIL]"
            print(f"{symbol} {message}")

        print("\n" + "=" * 60)
        print(f"총 {self.passed + self.failed}개 테스트")
        print(f"성공: {self.passed}")
        print(f"실패: {self.failed}")
        print("=" * 60)

        if self.failed == 0:
            print("\n[SUCCESS] 모든 테스트 통과!")
            return True
        else:
            print(f"\n[FAILED] {self.failed}개 테스트 실패")
            return False


def main():
    """메인 테스트 실행"""
    print("\n" + "=" * 60)
    print("팀워크 게이지 시스템 통합 테스트")
    print("=" * 60)

    tester = TestTeamworkSystem()

    # Party 테스트
    tester.test_party_basic()
    tester.test_party_chain()

    # TeamworkSkill 테스트
    tester.test_teamwork_skill_creation()
    tester.test_teamwork_skill_mp_cost()

    # UI 테스트
    tester.test_gauge_display()
    tester.test_chain_prompt_display()

    # 효과 테스트
    tester.test_teamwork_effects()

    # 전투 UI 테스트
    tester.test_battle_ui()

    # 결과 출력
    success = tester.print_results()

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
