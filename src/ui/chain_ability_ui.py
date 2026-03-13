"""
체인어빌리티 선택 UI (불릿타임 중 표시)

체인어빌리티 발동 조건 충족 시 불릿타임을 걸고,
플레이어에게 사용 여부를 선택하게 합니다.
"""

from typing import List, Optional, Any, Tuple
from src.core.logger import get_logger
from src.character.affinity import ChainAbilityResult
from src.ui.input_handler import iter_game_input, GameAction

logger = get_logger("chain_ability_ui")


class ChainAbilityUI:
    """
    체인어빌리티 선택 UI

    불릿타임 중 발동 가능한 체인어빌리티 목록을 표시하고,
    플레이어가 사용할지 결정합니다.
    """

    def __init__(self, console: Any, context: Any):
        self.console = console
        self.context = context
        self.selected_index = 0
        self.results: List[ChainAbilityResult] = []
        self.confirmed: Optional[ChainAbilityResult] = None
        self.cancelled = False

    def show(self, results: List[ChainAbilityResult], available_gauge: int) -> Optional[ChainAbilityResult]:
        """
        체인어빌리티 선택 UI 표시

        Args:
            results: 발동 가능한 체인어빌리티 결과 리스트
            available_gauge: 현재 사용 가능한 팀워크 게이지

        Returns:
            선택된 ChainAbilityResult 또는 None (패스한 경우)
        """
        if not results:
            return None

        self.results = results
        self.selected_index = 0
        self.confirmed = None
        self.cancelled = False

        # "패스" 옵션 포함
        options = results + [None]  # None = 패스

        while not self.confirmed and not self.cancelled:
            # 화면 그리기
            self._render(options, available_gauge)
            self.context.present(self.console)

            # 입력 처리
            for action, event in iter_game_input():
                if action == GameAction.QUIT:
                    self.cancelled = True
                    break
                self._handle_action(action, options)

        return self.confirmed

    def _render(self, options: list, available_gauge: int):
        """체인어빌리티 선택 UI 렌더링"""
        width = self.console.width
        height = self.console.height

        # 패널 크기 계산
        panel_w = min(50, width - 4)
        panel_h = min(4 + len(options) * 3, height - 4)
        panel_x = (width - panel_w) // 2
        panel_y = (height - panel_h) // 2

        # 배경 패널
        for y in range(panel_y, panel_y + panel_h):
            for x in range(panel_x, panel_x + panel_w):
                if 0 <= x < width and 0 <= y < height:
                    self.console.rgb[y, x] = (
                        ord(' '),
                        (200, 200, 255),
                        (20, 20, 60)
                    )

        # 타이틀
        title = "[ 체인어빌리티 ]"
        tx = panel_x + (panel_w - len(title)) // 2
        self.console.print(tx, panel_y, title, fg=(255, 220, 100), bg=(20, 20, 60))

        # 게이지 표시
        gauge_text = f"팀워크 게이지: {available_gauge}"
        self.console.print(panel_x + 2, panel_y + 1, gauge_text, fg=(100, 200, 255), bg=(20, 20, 60))

        # 옵션 목록
        for i, option in enumerate(options):
            y_pos = panel_y + 3 + i * 3
            if y_pos >= panel_y + panel_h - 1:
                break

            is_selected = (i == self.selected_index)
            cursor = ">" if is_selected else " "
            fg = (255, 255, 100) if is_selected else (200, 200, 200)
            bg = (40, 40, 80) if is_selected else (20, 20, 60)

            if option is None:
                # 패스 옵션
                text = f"{cursor} 패스 (사용하지 않음)"
                self.console.print(panel_x + 2, y_pos, text, fg=fg, bg=bg)
            else:
                # 체인어빌리티 옵션
                ability = option.ability
                cost_color = (100, 255, 100) if available_gauge >= ability.gauge_cost else (255, 100, 100)
                name_text = f"{cursor} {ability.name}"
                self.console.print(panel_x + 2, y_pos, name_text, fg=fg, bg=bg)

                # 비용 및 설명
                cost_text = f"  게이지 -{ability.gauge_cost}"
                self.console.print(panel_x + 4, y_pos + 1, cost_text, fg=cost_color, bg=bg)

                if ability.description:
                    desc = ability.description[:panel_w - 6]
                    self.console.print(panel_x + 4, y_pos + 2, desc, fg=(180, 180, 180), bg=bg)

        # 조작 안내
        help_text = "[↑↓] 선택  [Enter/A] 확정  [ESC/B] 패스"
        hy = panel_y + panel_h - 1
        self.console.print(panel_x + 2, hy, help_text, fg=(150, 150, 150), bg=(20, 20, 60))

    def _handle_action(self, action: GameAction, options: list):
        """GameAction 입력 처리"""
        if action == GameAction.MOVE_UP:
            self.selected_index = (self.selected_index - 1) % len(options)
        elif action == GameAction.MOVE_DOWN:
            self.selected_index = (self.selected_index + 1) % len(options)
        elif action == GameAction.CONFIRM:
            selected = options[self.selected_index]
            if selected is None:
                # 패스
                self.cancelled = True
            else:
                self.confirmed = selected
        elif action == GameAction.CANCEL:
            self.cancelled = True
