"""
겹치는 윈도우/패널 관리자

Z-order 기반 겹치는 패널 시스템.
각 패널은 독립적인 PygameConsole을 가지며,
최종 렌더링 시 z-order 순서대로 메인 콘솔에 합성.
"""

from typing import Callable, Dict, List, Optional, Tuple

from src.core.logger import get_logger
from src.ui.pygame_backend.pygame_console import PygameConsole

logger = get_logger("window_manager")


class Panel:
    """겹치는 윈도우 패널"""

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        width: int,
        height: int,
        title: str = "",
        fg: Tuple[int, int, int] = (200, 200, 200),
        bg: Tuple[int, int, int] = (15, 15, 25),
        border: Tuple[int, int, int] = (100, 100, 150),
        draggable: bool = False,
        closeable: bool = True,
        z_order: int = 0,
    ) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.title = title
        self.fg = fg
        self.bg = bg
        self.border = border
        self.draggable = draggable
        self.closeable = closeable
        self.z_order = z_order
        self.visible = True

        # 내부 콘솔 (자체 렌더링 버퍼)
        self.console = PygameConsole(width, height)

        # 드래그 상태
        self._dragging = False
        self._drag_offset = (0, 0)

        # 렌더링 콜백
        self._render_callback: Optional[Callable] = None

    def set_render_callback(self, callback: Callable) -> None:
        """패널 내용 렌더링 콜백 설정

        callback(console: PygameConsole) 형태.
        매 프레임 호출되어 패널 내용을 갱신합니다.
        """
        self._render_callback = callback

    def render(self) -> None:
        """패널 내용 렌더링"""
        self.console.clear(bg=self.bg)

        # 프레임
        self.console.draw_frame(
            0, 0, self.width, self.height,
            title=self.title, fg=self.border, bg=self.bg,
        )

        # 닫기 버튼 (우상단)
        if self.closeable:
            self.console.print(
                self.width - 2, 0, 'X',
                fg=(255, 80, 80), bg=self.bg,
            )

        # 사용자 콜백
        if self._render_callback:
            # 내부 영역 (프레임 제외)을 위한 서브 뷰
            self._render_callback(self.console)

    def contains(self, cell_x: int, cell_y: int) -> bool:
        """셀 좌표가 패널 영역 내인지"""
        return (self.x <= cell_x < self.x + self.width and
                self.y <= cell_y < self.y + self.height)

    def on_click(self, cell_x: int, cell_y: int) -> bool:
        """클릭 처리. 소비했으면 True 반환.

        Args:
            cell_x, cell_y: 글로벌 셀 좌표
        """
        if not self.contains(cell_x, cell_y):
            return False

        local_x = cell_x - self.x
        local_y = cell_y - self.y

        # 닫기 버튼
        if self.closeable and local_x == self.width - 2 and local_y == 0:
            self.visible = False
            return True

        # 타이틀바 드래그 시작
        if self.draggable and local_y == 0:
            self._dragging = True
            self._drag_offset = (local_x, local_y)
            return True

        return True  # 클릭 소비

    def on_drag(self, cell_x: int, cell_y: int) -> None:
        """드래그 처리"""
        if self._dragging:
            self.x = cell_x - self._drag_offset[0]
            self.y = cell_y - self._drag_offset[1]

    def on_release(self) -> None:
        """드래그 종료"""
        self._dragging = False


class WindowManager:
    """
    겹치는 윈도우 관리자

    사용법:
        wm = WindowManager()
        panel = wm.create_panel("inventory", 10, 5, 30, 20, title="인벤토리")
        panel.set_render_callback(render_inventory)
        wm.render(main_console)
    """

    def __init__(self) -> None:
        self._panels: Dict[str, Panel] = {}
        self._z_counter = 0

    def create_panel(
        self,
        name: str,
        x: int,
        y: int,
        width: int,
        height: int,
        title: str = "",
        draggable: bool = False,
        closeable: bool = True,
        **kwargs,
    ) -> Panel:
        """패널 생성"""
        self._z_counter += 1
        panel = Panel(
            name=name, x=x, y=y, width=width, height=height,
            title=title, draggable=draggable, closeable=closeable,
            z_order=self._z_counter, **kwargs,
        )
        self._panels[name] = panel
        logger.info(f"패널 생성: {name} ({width}x{height}) at ({x},{y})")
        return panel

    def get_panel(self, name: str) -> Optional[Panel]:
        """패널 조회"""
        return self._panels.get(name)

    def remove_panel(self, name: str) -> None:
        """패널 제거"""
        if name in self._panels:
            del self._panels[name]

    def show_panel(self, name: str) -> None:
        """패널 표시"""
        panel = self._panels.get(name)
        if panel:
            panel.visible = True
            self._bring_to_front(panel)

    def hide_panel(self, name: str) -> None:
        """패널 숨기기"""
        panel = self._panels.get(name)
        if panel:
            panel.visible = False

    def toggle_panel(self, name: str) -> None:
        """패널 토글"""
        panel = self._panels.get(name)
        if panel:
            panel.visible = not panel.visible
            if panel.visible:
                self._bring_to_front(panel)

    def _bring_to_front(self, panel: Panel) -> None:
        """패널을 최상위로"""
        self._z_counter += 1
        panel.z_order = self._z_counter

    def _sorted_panels(self) -> List[Panel]:
        """z-order 순서로 정렬된 보이는 패널 목록"""
        visible = [p for p in self._panels.values() if p.visible]
        return sorted(visible, key=lambda p: p.z_order)

    def render(self, main_console: PygameConsole) -> None:
        """모든 패널을 z-order 순서로 메인 콘솔에 합성"""
        for panel in self._sorted_panels():
            panel.render()
            panel.console.blit(main_console, dest_x=panel.x, dest_y=panel.y)

    def on_click(self, cell_x: int, cell_y: int) -> bool:
        """클릭 이벤트 전달 (최상위 패널부터)

        Returns:
            True면 클릭을 소비 (하위 UI에 전달하지 않음)
        """
        # 역순 (z-order 높은 것부터)
        for panel in reversed(self._sorted_panels()):
            if panel.contains(cell_x, cell_y):
                self._bring_to_front(panel)
                panel.on_click(cell_x, cell_y)
                return True
        return False

    def on_mouse_move(self, cell_x: int, cell_y: int) -> None:
        """마우스 이동 전달 (드래그)"""
        for panel in self._sorted_panels():
            if panel._dragging:
                panel.on_drag(cell_x, cell_y)

    def on_mouse_up(self) -> None:
        """마우스 버튼 놓기"""
        for panel in self._panels.values():
            panel.on_release()

    @property
    def has_visible_panels(self) -> bool:
        return any(p.visible for p in self._panels.values())
