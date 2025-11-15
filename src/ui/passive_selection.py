"""
패시브 선택 UI

4명의 파티원이 공유하는 패시브 풀에서
총 10 코스트 이내, 최대 3개의 패시브를 선택
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml
import tcod

from src.ui.input_handler import InputHandler, GameAction
from src.core.logger import get_logger, Loggers
from src.core.config import get_config


logger = get_logger(Loggers.UI)


@dataclass
class Passive:
    """패시브 데이터 클래스"""
    id: str
    name: str
    description: str
    cost: int
    unlocked: bool
    unlock_cost: int = 0
    effects: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.effects is None:
            self.effects = []


@dataclass
class PassiveSelection:
    """선택된 패시브 정보"""
    passives: List[Passive]
    total_cost: int


class PassiveSelectionUI:
    """패시브 선택 UI"""

    MAX_PASSIVES = 3
    MAX_COST = 10

    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # 패시브 목록 로드
        self.all_passives: List[Passive] = self._load_passives()

        # 선택된 패시브
        self.selected_passives: List[Passive] = []
        self.total_cost = 0

        # UI 상태
        self.cursor_index = 0
        self.scroll_offset = 0
        self.max_visible_items = 15
        self.cancelled = False
        self.confirmed = False

        logger.info(f"패시브 선택 UI 초기화: {len(self.all_passives)}개 패시브")

    def _load_passives(self) -> List[Passive]:
        """패시브 데이터 로드"""
        yaml_path = Path("data/passives.yaml")

        if not yaml_path.exists():
            logger.error(f"패시브 파일 없음: {yaml_path}")
            return []

        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            # 개발 모드 확인
            config = get_config()
            dev_mode = config.get("development.unlock_all_classes", False)

            passives = []
            for passive_data in data.get('passives', []):
                # 개발 모드이면 모든 패시브 해금
                is_unlocked = dev_mode or passive_data.get('unlocked', False)

                passive = Passive(
                    id=passive_data['id'],
                    name=passive_data['name'],
                    description=passive_data['description'],
                    cost=passive_data['cost'],
                    unlocked=is_unlocked,
                    unlock_cost=passive_data.get('unlock_cost', 0),
                    effects=passive_data.get('effects', [])
                )
                passives.append(passive)

            unlocked_count = sum(1 for p in passives if p.unlocked)
            logger.info(f"패시브 {len(passives)}개 로드 완료 (해금: {unlocked_count}개)")
            return passives

        except Exception as e:
            logger.error(f"패시브 로드 실패: {e}")
            return []

    def _can_select_passive(self, passive: Passive) -> tuple[bool, str]:
        """
        패시브 선택 가능 여부 확인

        Returns:
            (선택가능여부, 이유)
        """
        # 이미 선택됨
        if passive in self.selected_passives:
            return False, "이미 선택됨"

        # 잠김
        if not passive.unlocked:
            return False, f"잠김 (해금 비용: {passive.unlock_cost} 별빛의 파편)"

        # 최대 개수 초과
        if len(self.selected_passives) >= self.MAX_PASSIVES:
            return False, f"최대 {self.MAX_PASSIVES}개까지만 선택 가능"

        # 코스트 초과
        if self.total_cost + passive.cost > self.MAX_COST:
            remaining = self.MAX_COST - self.total_cost
            return False, f"코스트 초과 (남은 코스트: {remaining})"

        return True, ""

    def handle_input(self, action: GameAction) -> bool:
        """
        입력 처리

        Returns:
            True면 선택 완료/취소
        """
        if action == GameAction.CANCEL:
            self.cancelled = True
            return True

        elif action == GameAction.CONFIRM:
            passive = self.all_passives[self.cursor_index]

            # 이미 선택된 경우 -> 선택 해제
            if passive in self.selected_passives:
                self.selected_passives.remove(passive)
                self.total_cost -= passive.cost
                logger.info(f"패시브 해제: {passive.name} (코스트: {passive.cost})")
                return False

            # 선택 가능 여부 확인
            can_select, reason = self._can_select_passive(passive)
            if can_select:
                self.selected_passives.append(passive)
                self.total_cost += passive.cost
                logger.info(
                    f"패시브 선택: {passive.name} "
                    f"(코스트: {passive.cost}, 총: {self.total_cost}/{self.MAX_COST})"
                )
            else:
                logger.debug(f"패시브 선택 불가: {passive.name} - {reason}")

            return False

        elif action == GameAction.MENU:
            # Enter 키로 선택 확정
            if len(self.selected_passives) > 0:
                self.confirmed = True
                return True
            return False

        elif action == GameAction.MOVE_UP:
            self._move_cursor_up()
            return False

        elif action == GameAction.MOVE_DOWN:
            self._move_cursor_down()
            return False

        return False

    def _move_cursor_up(self):
        """커서 위로"""
        if self.cursor_index > 0:
            self.cursor_index -= 1

            # 스크롤 조정
            if self.cursor_index < self.scroll_offset:
                self.scroll_offset = self.cursor_index

    def _move_cursor_down(self):
        """커서 아래로"""
        if self.cursor_index < len(self.all_passives) - 1:
            self.cursor_index += 1

            # 스크롤 조정
            if self.cursor_index >= self.scroll_offset + self.max_visible_items:
                self.scroll_offset = self.cursor_index - self.max_visible_items + 1

    def render(self, console: tcod.console.Console):
        """UI 렌더링"""
        console.clear()

        # 제목
        title = "패시브 선택"
        console.print(
            self.screen_width // 2 - len(title) // 2,
            2,
            title,
            fg=(255, 255, 100)
        )

        # 설명
        info = f"최대 3개, 총 10 코스트 이내 선택 가능 | Z: 선택/해제  X: 취소  Enter: 확정"
        console.print(
            self.screen_width // 2 - len(info) // 2,
            3,
            info,
            fg=(180, 180, 180)
        )

        # 현재 상태
        status_text = f"선택: {len(self.selected_passives)}/{self.MAX_PASSIVES}  코스트: {self.total_cost}/{self.MAX_COST}"
        console.print(
            self.screen_width // 2 - len(status_text) // 2,
            4,
            status_text,
            fg=(100, 255, 100) if self.total_cost <= self.MAX_COST else (255, 100, 100)
        )

        # 구분선
        console.print(0, 5, "─" * self.screen_width, fg=(100, 100, 100))

        # 패시브 목록 영역
        list_x = 5
        list_y = 7
        list_width = 50
        list_height = self.max_visible_items

        # 선택된 패시브 패널
        selected_x = list_x + list_width + 3
        selected_y = 7

        # 패시브 목록 렌더링
        visible_passives = self.all_passives[
            self.scroll_offset:self.scroll_offset + self.max_visible_items
        ]

        for i, passive in enumerate(visible_passives):
            actual_index = self.scroll_offset + i
            y = list_y + i

            # 커서
            cursor = "▶" if actual_index == self.cursor_index else " "

            # 선택 상태
            is_selected = passive in self.selected_passives
            check = "[✓]" if is_selected else "[ ]"

            # 색상 결정
            can_select, reason = self._can_select_passive(passive)
            if is_selected:
                color = (100, 255, 100)
            elif not passive.unlocked:
                color = (100, 100, 100)
            elif not can_select:
                color = (150, 150, 150)
            else:
                color = (255, 255, 255)

            # 패시브 이름 + 코스트
            passive_text = f"{cursor} {check} [{passive.cost}] {passive.name}"
            console.print(list_x, y, passive_text, fg=color)

        # 현재 선택된 패시브의 상세 정보
        if 0 <= self.cursor_index < len(self.all_passives):
            current = self.all_passives[self.cursor_index]

            detail_y = list_y + list_height + 2
            console.print(list_x, detail_y, "─" * list_width, fg=(100, 100, 100))
            console.print(list_x, detail_y + 1, "[상세 정보]", fg=(255, 255, 100))
            console.print(list_x, detail_y + 2, f"이름: {current.name}", fg=(200, 200, 200))
            console.print(list_x, detail_y + 3, f"코스트: {current.cost}", fg=(200, 200, 200))
            console.print(list_x, detail_y + 4, f"설명:", fg=(200, 200, 200))

            # 설명 줄바꿈
            desc_lines = self._wrap_text(current.description, list_width - 2)
            for i, line in enumerate(desc_lines):
                console.print(list_x + 2, detail_y + 5 + i, line, fg=(180, 180, 180))

            # 잠금 상태
            if not current.unlocked:
                lock_y = detail_y + 6 + len(desc_lines)
                console.print(
                    list_x,
                    lock_y,
                    f"🔒 잠김 - 해금 비용: {current.unlock_cost} 별빛의 파편",
                    fg=(255, 100, 100)
                )

            # 선택 불가 이유
            can_select, reason = self._can_select_passive(current)
            if not can_select and current not in self.selected_passives:
                reason_y = detail_y + 7 + len(desc_lines)
                console.print(list_x, reason_y, f"❌ {reason}", fg=(255, 150, 100))

        # 선택된 패시브 패널
        console.print(selected_x, selected_y - 1, "[선택된 패시브]", fg=(255, 255, 100))
        console.print(selected_x, selected_y, "─" * 25, fg=(100, 100, 100))

        if self.selected_passives:
            for i, passive in enumerate(self.selected_passives):
                console.print(
                    selected_x,
                    selected_y + 1 + i,
                    f"[{passive.cost}] {passive.name}",
                    fg=(100, 255, 100)
                )
        else:
            console.print(
                selected_x,
                selected_y + 1,
                "(선택된 패시브 없음)",
                fg=(100, 100, 100)
            )

        # 스크롤 인디케이터
        if self.scroll_offset > 0:
            console.print(list_x + list_width - 5, list_y - 1, "▲ 더보기", fg=(150, 150, 150))

        if self.scroll_offset + self.max_visible_items < len(self.all_passives):
            console.print(
                list_x + list_width - 5,
                list_y + list_height,
                "▼ 더보기",
                fg=(150, 150, 150)
            )

    def _wrap_text(self, text: str, width: int) -> List[str]:
        """텍스트 줄바꿈"""
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            if len(test_line) <= width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word

        if current_line:
            lines.append(current_line)

        return lines

    def get_result(self) -> Optional[PassiveSelection]:
        """
        선택 결과 반환

        Returns:
            PassiveSelection 또는 None (취소 시)
        """
        if self.cancelled:
            return None

        return PassiveSelection(
            passives=self.selected_passives.copy(),
            total_cost=self.total_cost
        )


def run_passive_selection(
    console: tcod.console.Console,
    context: tcod.context.Context
) -> Optional[PassiveSelection]:
    """
    패시브 선택 실행

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트

    Returns:
        선택된 패시브 또는 None (취소 시)
    """
    selection = PassiveSelectionUI(console.width, console.height)
    handler = InputHandler()

    logger.info("패시브 선택 시작")

    while True:
        # 렌더링
        selection.render(console)
        context.present(console)

        # 입력 처리
        for event in tcod.event.wait():
            action = handler.dispatch(event)

            if action:
                if selection.handle_input(action):
                    # 완료 또는 취소
                    result = selection.get_result()
                    if result:
                        logger.info(
                            f"패시브 선택 완료: {len(result.passives)}개, "
                            f"총 코스트 {result.total_cost}"
                        )
                    else:
                        logger.info("패시브 선택 취소")
                    return result

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return None
