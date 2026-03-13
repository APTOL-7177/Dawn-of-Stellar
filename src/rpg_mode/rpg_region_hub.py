"""
RPG 모드 지역 허브 (월드맵)

지역을 선택하여 오픈월드 탐험에 진입하는 UI
"""

import tcod.console
import tcod.context
import tcod.event
from typing import Optional, List, Set

from src.ui.cursor_menu import CursorMenu, MenuItem
from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, unified_input_handler
from src.rpg_mode.rpg_world_config import REGIONS, RegionConfig, REGION_MAP
from src.core.logger import get_logger
from src.audio import play_bgm

logger = get_logger("rpg_region_hub")


class RegionHubResult:
    """지역 허브 결과"""
    def __init__(self, action: str, region_id: Optional[str] = None,
                 sub_dungeon_id: Optional[str] = None):
        self.action = action  # "explore", "quit", "save"
        self.region_id = region_id
        self.sub_dungeon_id = sub_dungeon_id


def run_region_hub(
    console: tcod.console.Console,
    context: tcod.context.Context,
    unlocked_regions: Set[str],
    defeated_bosses: Set[str],
    current_chapter: int,
    party_info: List[dict],
) -> RegionHubResult:
    """
    지역 허브(월드맵) 실행

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        unlocked_regions: 해금된 지역 ID 집합
        defeated_bosses: 처치한 보스 지역 ID 집합
        current_chapter: 현재 챕터 번호
        party_info: 파티 정보 (표시용)

    Returns:
        RegionHubResult (선택한 지역 또는 종료)
    """
    import time

    play_bgm("main_menu")

    selected_region: Optional[str] = None

    # 메뉴 아이템 생성
    def make_menu_items():
        items = []
        for region in REGIONS:
            is_unlocked = region.region_id in unlocked_regions
            is_boss_defeated = region.region_id in defeated_bosses

            if is_unlocked:
                status = " ★" if is_boss_defeated else ""
                text = f"{region.name} (Lv.{region.level_min}~{region.level_max}){status}"
                desc = region.description
            else:
                text = f"??? [미해금]"
                desc = "이전 지역의 보스를 처치하면 해금됩니다"

            def make_action(rid=region.region_id, unlocked=is_unlocked):
                def action():
                    nonlocal selected_region
                    if unlocked:
                        selected_region = rid
                return action

            items.append(MenuItem(
                text=text,
                action=make_action(),
                enabled=is_unlocked,
                description=desc,
            ))

        # 하단 메뉴
        items.append(MenuItem(text="─" * 26, action=lambda: None, enabled=False, description=""))

        def quit_action():
            nonlocal selected_region
            selected_region = "__quit__"

        items.append(MenuItem(
            text="메인 메뉴로 돌아가기",
            action=quit_action,
            description="RPG 모드를 종료하고 메인 메뉴로 돌아갑니다",
        ))

        return items

    menu_items = make_menu_items()

    menu_width = 40
    menu_x = (console.width - menu_width) // 2
    menu_y = 12

    menu = CursorMenu(
        title="",
        items=menu_items,
        x=menu_x,
        y=menu_y,
        width=menu_width,
        show_description=False,
    )

    last_time = time.time()

    # 입력 버퍼 클리어
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    while selected_region is None:
        current_time = time.time()

        # 렌더링
        console.clear()

        # 타이틀
        title = "═══ 차원의 잔향 - 월드맵 ═══"
        title_x = (console.width - len(title)) // 2
        console.print(title_x, 2, title, fg=(200, 200, 255))

        # 파티 정보
        party_str = "파티: " + " | ".join(
            f"{p['name']}({p['job']}) Lv.{p['level']}" for p in party_info
        )
        console.print(2, 4, party_str, fg=Colors.GRAY)

        # 챕터 진행도
        console.print(2, 6, f"메인 스토리: 챕터 {current_chapter}/10", fg=(180, 200, 255))

        # 진행도 바
        unlocked_count = len(unlocked_regions)
        total_count = len(REGIONS)
        bar_width = 20
        filled = int(bar_width * unlocked_count / total_count)
        bar = "█" * filled + "░" * (bar_width - filled)
        console.print(2, 8, f"탐험 진행: [{bar}] {unlocked_count}/{total_count}", fg=(150, 255, 150))

        # 구분선
        console.print(2, 10, "─" * (console.width - 4), fg=(60, 80, 120))

        # 메뉴
        menu.render(console)

        # 선택된 지역 상세 정보
        sel_item = menu.get_selected_item()
        if sel_item and sel_item.description and sel_item.enabled:
            desc_y = menu_y + len(menu_items) + 2
            # 설명 줄바꿈 처리
            desc = sel_item.description
            max_w = console.width - 6
            if len(desc) > max_w:
                # 간단한 줄바꿈
                console.print(3, desc_y, desc[:max_w], fg=Colors.GRAY)
                if len(desc) > max_w:
                    console.print(3, desc_y + 1, desc[max_w:max_w * 2], fg=Colors.GRAY)
            else:
                console.print(3, desc_y, desc, fg=Colors.GRAY)

        # 조작 안내
        console.print(2, console.height - 2, "방향키: 이동  Z: 선택  X: 돌아가기", fg=Colors.GRAY)

        context.present(console)

        # 입력
        for event in tcod.event.get():
            action = unified_input_handler.process_tcod_event(event)
            if isinstance(event, tcod.event.Quit):
                return RegionHubResult("quit")

            if action == GameAction.MOVE_UP:
                menu.move_cursor_up()
            elif action == GameAction.MOVE_DOWN:
                menu.move_cursor_down()
            elif action == GameAction.CONFIRM:
                menu.execute_selected()
            elif action == GameAction.ESCAPE or action == GameAction.QUIT:
                return RegionHubResult("quit")

        # 게임패드
        gamepad_action = unified_input_handler.get_action()
        if gamepad_action:
            if gamepad_action == GameAction.MOVE_UP:
                menu.move_cursor_up()
            elif gamepad_action == GameAction.MOVE_DOWN:
                menu.move_cursor_down()
            elif gamepad_action == GameAction.CONFIRM:
                menu.execute_selected()
            elif gamepad_action == GameAction.ESCAPE:
                return RegionHubResult("quit")

        time.sleep(0.016)

    if selected_region == "__quit__":
        return RegionHubResult("quit")

    return RegionHubResult("explore", region_id=selected_region)
