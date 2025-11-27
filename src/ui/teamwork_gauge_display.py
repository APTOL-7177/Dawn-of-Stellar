"""
팀워크 게이지 표시 UI

24셀 시스템 (25 게이지 = 1셀)
"""

from typing import Optional

try:
    from src.core.logger import get_logger
    logger = get_logger("ui")
except ImportError:
    # 테스트용
    logger = None


class TeamworkGaugeDisplay:
    """팀워크 게이지 표시"""

    CELL_SIZE = 25  # 1셀 = 25 게이지
    MAX_CELLS = 24  # 총 24셀 (600 게이지)

    @staticmethod
    def format_gauge(teamwork_gauge: int, max_gauge: int = 600) -> str:
        """
        팀워크 게이지를 형식화된 문자열로 반환

        Args:
            teamwork_gauge: 현재 팀워크 게이지
            max_gauge: 최대 팀워크 게이지

        Returns:
            형식화된 게이지 문자열
        """
        # 셀 계산
        current_cells = teamwork_gauge // TeamworkGaugeDisplay.CELL_SIZE
        percentage = (teamwork_gauge / max_gauge) * 100

        # 상태에 따른 색상과 아이콘 결정
        if percentage >= 80:
            status_icon = "!"  # 화끈한 상태
            status_text = "[MAX CHARGE!]"
        elif percentage >= 50:
            status_icon = "*"  # 좋은 상태
            status_text = "[READY]"
        elif percentage >= 25:
            status_icon = "+"  # 보통 상태
            status_text = "[CHARGING]"
        else:
            status_icon = "~"  # 낮은 상태
            status_text = "[BUILDING]"

        # 게이지 바 생성 (더 화려한 디자인)
        filled_chars = ["█", "▓", "▒", "░"]  # 그라데이션 효과
        filled = ""
        for i in range(current_cells):
            # 셀마다 다른 패턴으로 다양성 추가
            pattern_index = i % len(filled_chars)
            filled += filled_chars[pattern_index]

        empty = "░" * (TeamworkGaugeDisplay.MAX_CELLS - current_cells)

        # 게이지 바에 테두리 추가
        gauge_bar = f"┌{'─' * (TeamworkGaugeDisplay.MAX_CELLS + 2)}┐\n"
        gauge_bar += f"│ {filled}{empty} │ {status_icon}\n"
        gauge_bar += f"└{'─' * (TeamworkGaugeDisplay.MAX_CELLS + 2)}┘"

        return f"{status_text} 팀워크 게이지 {teamwork_gauge}/{max_gauge} ({current_cells}/{TeamworkGaugeDisplay.MAX_CELLS}셀)\n{gauge_bar}\n{status_icon} {percentage:.1f}% 충전됨"

    @staticmethod
    def get_gauge_bar(teamwork_gauge: int, max_gauge: int = 600, width: int = 24) -> str:
        """
        팀워크 게이지 바 반환 (간단한 버전)

        Args:
            teamwork_gauge: 현재 팀워크 게이지
            max_gauge: 최대 팀워크 게이지
            width: 게이지 바 너비

        Returns:
            게이지 바 문자열
        """
        filled = int((teamwork_gauge / max_gauge) * width)
        percentage = (teamwork_gauge / max_gauge) * 100

        # 상태에 따른 채우기 문자 선택
        if percentage >= 80:
            fill_char = "█"
        elif percentage >= 50:
            fill_char = "▓"
        elif percentage >= 25:
            fill_char = "▒"
        else:
            fill_char = "░"

        # 화살표로 현재 위치 표시
        bar = fill_char * filled + "░" * (width - filled)
        if filled > 0 and filled < width:
            # 현재 위치에 화살표 표시
            bar = bar[:filled-1] + "▲" + bar[filled:]

        return f"[{bar}]"

    @staticmethod
    def format_compact(teamwork_gauge: int, max_gauge: int = 600) -> str:
        """
        간단한 형식의 게이지 표시

        Args:
            teamwork_gauge: 현재 팀워크 게이지
            max_gauge: 최대 팀워크 게이지

        Returns:
            간단한 형식의 문자열
        """
        current_cells = teamwork_gauge // TeamworkGaugeDisplay.CELL_SIZE
        percentage = (teamwork_gauge / max_gauge) * 100
        gauge_bar = TeamworkGaugeDisplay.get_gauge_bar(teamwork_gauge, max_gauge, width=16)

        # 상태에 따른 아이콘
        if percentage >= 80:
            icon = "!"
        elif percentage >= 50:
            icon = "*"
        elif percentage >= 25:
            icon = "+"
        else:
            icon = "~"

        return f"{icon} TW: {teamwork_gauge:3d}/{max_gauge:3d} ({current_cells:2d}/{TeamworkGaugeDisplay.MAX_CELLS}셀) {percentage:5.1f}% {gauge_bar}"

    @staticmethod
    def format_animated_gauge(teamwork_gauge: int, max_gauge: int = 600, frame: int = 0) -> str:
        """
        애니메이션 효과가 있는 게이지 표시

        Args:
            teamwork_gauge: 현재 팀워크 게이지
            max_gauge: 최대 팀워크 게이지
            frame: 애니메이션 프레임 (0-3)

        Returns:
            애니메이션 효과가 적용된 게이지 문자열
        """
        current_cells = teamwork_gauge // TeamworkGaugeDisplay.CELL_SIZE
        percentage = (teamwork_gauge / max_gauge) * 100

        # 상태에 따른 기본 설정
        if percentage >= 80:
            base_icon = "!"
            pulse_chars = ["!", "*", "!", "~"]
        elif percentage >= 50:
            base_icon = "*"
            pulse_chars = ["*", "*", "*", "+"]
        elif percentage >= 25:
            base_icon = "+"
            pulse_chars = ["+", "~", "+", "#"]
        else:
            base_icon = "~"
            pulse_chars = ["~", "#", "~", "+"]

        # 프레임에 따른 펄스 효과
        pulse_icon = pulse_chars[frame % len(pulse_chars)]

        # 게이지 바 생성 (애니메이션 효과)
        filled_chars = ["█", "▓", "▒", "░"]
        filled = ""
        for i in range(current_cells):
            # 마지막 셀에 펄스 효과 적용
            if i == current_cells - 1 and percentage >= 25:
                filled += "█"  # Use block character for animation
            else:
                filled += filled_chars[i % len(filled_chars)]

        empty = "░" * (TeamworkGaugeDisplay.MAX_CELLS - current_cells)

        gauge_bar = f"┌{'─' * (TeamworkGaugeDisplay.MAX_CELLS + 2)}┐\n"
        gauge_bar += f"│ {filled}{empty} │\n"
        gauge_bar += f"└{'─' * (TeamworkGaugeDisplay.MAX_CELLS + 2)}┘"

        return f"{pulse_icon} 팀워크 게이지 {teamwork_gauge}/{max_gauge} ({current_cells}/{TeamworkGaugeDisplay.MAX_CELLS}셀)\n{gauge_bar}\n{pulse_icon} {percentage:.1f}% 충전됨"

    @staticmethod
    def format_for_skill_menu(skill_cost: int, teamwork_gauge: int, max_gauge: int = 600) -> str:
        """
        스킬 선택 메뉴용 게이지 정보

        Args:
            skill_cost: 스킬의 팀워크 게이지 비용
            teamwork_gauge: 현재 팀워크 게이지
            max_gauge: 최대 팀워크 게이지

        Returns:
            스킬 선택 메뉴용 문자열
        """
        can_use = teamwork_gauge >= skill_cost
        status = "[OK]" if can_use else "[NO]"

        current_cells = teamwork_gauge // TeamworkGaugeDisplay.CELL_SIZE
        cost_cells = skill_cost // TeamworkGaugeDisplay.CELL_SIZE
        after_cells = (teamwork_gauge - skill_cost) // TeamworkGaugeDisplay.CELL_SIZE

        lines = [
            f"{status} 팀워크 게이지 {skill_cost}",
            f"   현재: {teamwork_gauge}/{max_gauge} ({current_cells}셀)",
            f"   비용: {cost_cells}셀",
        ]

        if can_use:
            lines.append(f"   사용 후: {teamwork_gauge - skill_cost}/{max_gauge} ({after_cells}셀)")

        return "\n".join(lines)

    @staticmethod
    def format_chain_info(chain_count: int, chain_starter_name: str, mp_cost: int) -> str:
        """
        연쇄 진행 정보 표시

        Args:
            chain_count: 현재 연쇄 단계
            chain_starter_name: 연쇄 시작자 이름
            mp_cost: 필요 MP

        Returns:
            연쇄 정보 문자열
        """
        if chain_count == 1:
            return f"[연쇄 시작] {chain_starter_name}의 팀워크 스킬 발동!\n"

        return f"[연쇄 {chain_count}단계] 다음 캐릭터 턴 (필요 MP: {mp_cost})\n"


class ChainPrompt:
    """연쇄 제안 화면"""

    @staticmethod
    def format_skill_description(skill_description: str) -> str:
        """스킬 설명을 포맷팅"""
        if not skill_description:
            return ""

        # 긴 설명은 줄바꿈 처리
        lines = []
        for line in skill_description.split("\n"):
            if line:
                lines.append(f"    {line}")
        return "\n".join(lines)

    @staticmethod
    def format_skill_info(skill_name: str, skill_description: str,
                         skill_cost: int, mp_cost: int) -> str:
        """스킬 정보 포맷팅"""
        lines = [
            f"[팀워크 스킬] {skill_name}",
            f"  - 설명: {skill_description}",
            f"  - 게이지 비용: {skill_cost} (= {skill_cost // 25}셀)",
            f"  - MP 비용: {mp_cost}",
        ]
        return "\n".join(lines)

    @staticmethod
    def format_prompt(
        chain_count: int,
        chain_starter_name: str,
        current_skill_name: str,
        current_skill_description: str,
        current_skill_cost: int,
        current_actor_name: str,
        teamwork_gauge: int,
        current_mp: int,
        required_mp: int,
    ) -> str:
        """
        연쇄 제안 화면 형식화 (스킬 효과 포함)

        Args:
            chain_count: 현재 연쇄 단계
            chain_starter_name: 연쇄 시작자 이름
            current_skill_name: 현재 스킬 이름
            current_skill_description: 현재 스킬 설명
            current_skill_cost: 현재 스킬의 팀워크 게이지 비용
            current_actor_name: 현재 캐릭터 이름
            teamwork_gauge: 현재 팀워크 게이지
            current_mp: 현재 MP
            required_mp: 필요 MP

        Returns:
            연쇄 제안 화면 문자열
        """
        can_use = teamwork_gauge >= current_skill_cost and current_mp >= required_mp
        if can_use:
            status = "[연쇄 가능!]"
            status_icon = ">"
        else:
            status = "[연쇄 불가]"
            status_icon = "X"

        # 게이지 상태 표시
        gauge_percentage = (teamwork_gauge / 600) * 100
        if gauge_percentage >= 80:
            gauge_status = "! MAX!"
        elif gauge_percentage >= 50:
            gauge_status = "* GOOD"
        else:
            gauge_status = "~ LOW"

        lines = [
            "+" + "-" * 58 + "+",
            f"|{status_icon} [연쇄 발동 중!] {chain_starter_name}의 팀워크 스킬 발동! {status_icon}|",
            "+" + "-" * 58 + "+",
            "",
            f"|  [{chain_count}단계] {current_actor_name}의 턴 {status}  |",
            "",
            "|  ================= 다음 스킬 =================  |",
            "",
            f"|  > 스킬명: {current_skill_name}",
            f"|  ? 설명: {current_skill_description}",
            "",
            "|  =============== 필요 자원 ===============  |",
            f"|  * 게이지: {current_skill_cost}/600 (현재: {teamwork_gauge}/600) {gauge_status}",
            f"|  @ MP: {required_mp} (현재: {current_mp})",
            f"|  # 사용 후: 게이지 {max(0, teamwork_gauge - current_skill_cost)}/600",
            "",
            "|  ================= 선택 =================  |",
            "|  [Y] > 이어받기  /  [N] X 종료              |",
            "+" + "-" * 58 + "+",
        ]

        return "\n".join(lines)

    @staticmethod
    def format_prompt_simple(
        chain_count: int,
        chain_starter_name: str,
        next_actor_name: str,
    ) -> str:
        """간단한 연쇄 제안 화면"""
        chain_icons = ["~", "*", "+", "!", "#"]
        icon = chain_icons[min(chain_count - 1, len(chain_icons) - 1)]

        lines = [
            "",
            f"{icon} [{chain_count}단계 연쇄] {next_actor_name}의 턴입니다!",
            f"   {chain_starter_name}의 팀워크 스킬을 이어받으시겠습니까?",
            "",
            "   [Y] > 이어받기 / [N] X 종료",
            "",
        ]
        return "\n".join(lines)

# 테스트용 함수
if __name__ == "__main__":
    print("🎮 팀워크 게이지 표시 테스트 🎮")
    print("=" * 50)

    # 다양한 게이지 레벨 테스트
    test_levels = [50, 150, 300, 450, 550]

    for gauge in test_levels:
        print(f"\n--- 게이지: {gauge}/600 ---")
        print(TeamworkGaugeDisplay.format_gauge(gauge, 600))
        print()
        print(TeamworkGaugeDisplay.format_compact(gauge, 600))
        print()

    print("--- 스킬 메뉴용 표시 ---")
    print(TeamworkGaugeDisplay.format_for_skill_menu(100, 450, 600))
    print()

    print("--- 연쇄 제안 화면 ---")
    print(ChainPrompt.format_prompt(
        chain_count=2,
        chain_starter_name="전사",
        current_skill_name="일제사격",
        current_skill_description="마킹된 모든 아군의 지원사격을 한꺼번에 발사",
        current_skill_cost=150,
        current_actor_name="궁수",
        teamwork_gauge=350,
        current_mp=45,
        required_mp=10,
    ))
    print()

    print("--- 간단한 연쇄 제안 ---")
    print(ChainPrompt.format_prompt_simple(3, "전사", "마법사"))
    print()

    print("--- 애니메이션 효과 ---")
    for frame in range(4):
        print(f"프레임 {frame}:")
        print(TeamworkGaugeDisplay.format_animated_gauge(450, 600, frame))
        print()
