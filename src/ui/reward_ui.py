"""
전투 보상 UI

경험치, 레벨업, 골드, 아이템 보상 표시
"""

import tcod.console
import tcod.event
from typing import List, Dict, Any, Optional

from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, InputHandler
from src.core.logger import get_logger


logger = get_logger("reward_ui")


class RewardDisplay:
    """전투 보상 화면"""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        rewards: Dict[str, Any],
        level_ups: Dict[Any, List[Dict[str, Any]]]
    ):
        """
        Args:
            screen_width: 화면 너비
            screen_height: 화면 높이
            rewards: {"experience": int, "gold": int, "items": List[Item]}
            level_ups: {캐릭터: [{"level": int, "stat_gains": {...}}]}
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.rewards = rewards
        self.level_ups = level_ups

        self.completed = False

        # 스크롤 위치 (아이템이 많을 경우)
        self.scroll_offset = 0
        self.max_items_visible = 10

    def handle_input(self, action: GameAction) -> bool:
        """
        입력 처리

        Args:
            action: 게임 액션

        Returns:
            완료 여부
        """
        if action == GameAction.CONFIRM or action == GameAction.ESCAPE:
            self.completed = True
            return True
        elif action == GameAction.MOVE_UP:
            self.scroll_offset = max(0, self.scroll_offset - 1)
        elif action == GameAction.MOVE_DOWN:
            max_offset = max(0, len(self.rewards.get("items", [])) - self.max_items_visible)
            self.scroll_offset = min(max_offset, self.scroll_offset + 1)

        return False

    def render(self, console: tcod.console.Console):
        """보상 화면 렌더링"""
        console.clear()

        # 제목
        title = "⭐ 전투 승리! ⭐"
        console.print(
            (self.screen_width - len(title)) // 2,
            2,
            title,
            fg=Colors.UI_TEXT_SELECTED
        )

        y = 5

        # 경험치
        exp = self.rewards.get("experience", 0)
        console.print(
            5,
            y,
            f"획득 경험치: {exp} EXP",
            fg=Colors.UI_TEXT_SELECTED
        )
        y += 2

        # 골드
        gold = self.rewards.get("gold", 0)
        console.print(
            5,
            y,
            f"획득 골드: {gold} G",
            fg=(255, 215, 0)  # 금색
        )
        y += 2

        # 레벨업 정보
        if self.level_ups:
            console.print(
                5,
                y,
                "🎉 레벨업!",
                fg=Colors.UI_TEXT_SELECTED
            )
            y += 1

            for character, level_up_list in self.level_ups.items():
                char_name = getattr(character, 'name', str(character))

                for level_info in level_up_list:
                    new_level = level_info["level"]
                    stat_gains = level_info["stat_gains"]

                    console.print(
                        7,
                        y,
                        f"{char_name} → Lv.{new_level}",
                        fg=Colors.UI_TEXT
                    )
                    y += 1

                    # 스탯 증가량 표시
                    stat_text = []
                    for stat_name, gain in stat_gains.items():
                        if gain > 0:
                            if stat_name in ["hp", "mp"]:
                                stat_text.append(f"{stat_name.upper()}+{gain}")
                            else:
                                stat_text.append(f"{stat_name[:3]}+{gain}")

                    if stat_text:
                        console.print(
                            9,
                            y,
                            "  ".join(stat_text),
                            fg=Colors.GRAY
                        )
                        y += 1

            y += 1

        # 아이템 드롭
        items = self.rewards.get("items", [])
        if items:
            console.print(
                5,
                y,
                f"드롭 아이템 ({len(items)}개):",
                fg=Colors.UI_TEXT
            )
            y += 1

            # 아이템 목록 (스크롤 가능)
            visible_items = items[self.scroll_offset:self.scroll_offset + self.max_items_visible]

            for item in visible_items:
                # 등급별 색상
                rarity_color = getattr(item.rarity, 'color', Colors.UI_TEXT)

                # 아이템 이름 + 레벨
                item_text = f"  • {item.name}"
                if hasattr(item, 'level_requirement') and item.level_requirement > 1:
                    item_text += f" (Lv.{item.level_requirement})"

                console.print(
                    7,
                    y,
                    item_text,
                    fg=rarity_color
                )
                y += 1

                # 접사 표시
                if hasattr(item, 'affixes') and item.affixes:
                    affix_texts = []
                    for affix in item.affixes[:3]:  # 최대 3개만 표시
                        if affix.is_percentage:
                            affix_texts.append(f"{affix.name} +{affix.value}%")
                        else:
                            affix_texts.append(f"{affix.name} +{int(affix.value)}")

                    if affix_texts:
                        console.print(
                            9,
                            y,
                            " | ".join(affix_texts),
                            fg=Colors.DARK_GRAY
                        )
                        y += 1

            # 스크롤 표시
            if len(items) > self.max_items_visible:
                scroll_info = f"(↑↓로 스크롤: {self.scroll_offset + 1}-{min(self.scroll_offset + self.max_items_visible, len(items))} / {len(items)})"
                console.print(
                    7,
                    y,
                    scroll_info,
                    fg=Colors.DARK_GRAY
                )
                y += 1

        else:
            console.print(
                5,
                y,
                "드롭 아이템 없음",
                fg=Colors.DARK_GRAY
            )
            y += 1

        # 도움말
        help_text = "아무 키나 눌러 계속..."
        console.print(
            (self.screen_width - len(help_text)) // 2,
            self.screen_height - 3,
            help_text,
            fg=Colors.GRAY
        )


def show_reward_screen(
    console: tcod.console.Console,
    context: tcod.context.Context,
    rewards: Dict[str, Any],
    level_ups: Dict[Any, List[Dict[str, Any]]]
) -> None:
    """
    보상 화면 표시

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        rewards: 보상 정보
        level_ups: 레벨업 정보
    """
    # 승리 BGM 재생
    from src.audio import play_bgm
    play_bgm("victory", loop=False, fade_in=False)
    logger.info("승리 BGM 재생")

    display = RewardDisplay(
        console.width,
        console.height,
        rewards,
        level_ups
    )
    handler = InputHandler()

    logger.info("보상 화면 표시")
    logger.info(f"  경험치: {rewards.get('experience', 0)}")
    logger.info(f"  골드: {rewards.get('gold', 0)}")
    logger.info(f"  아이템: {len(rewards.get('items', []))}개")

    while not display.completed:
        # 렌더링
        display.render(console)
        context.present(console)

        # 입력 처리
        for event in tcod.event.wait():
            action = handler.dispatch(event)

            if action:
                if display.handle_input(action):
                    return

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return
