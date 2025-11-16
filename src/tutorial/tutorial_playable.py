"""
플레이 가능한 튜토리얼 모드

실제로 캐릭터를 조작하며 배우는 인터랙티브 튜토리얼
"""

import tcod
import tcod.console
import tcod.event
from typing import Optional, Tuple

from src.tutorial.tutorial_dungeon import TutorialDungeon
from src.tutorial.tutorial_manager import get_tutorial_manager
from src.tutorial.tutorial_ui import TutorialUI
from src.character.character import Character
from src.world.exploration import ExplorationSystem
from src.equipment.inventory import Inventory
from src.ui.input_handler import InputHandler, GameAction
from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.SYSTEM)


class TutorialPlayMode:
    """플레이 가능한 튜토리얼 모드"""

    def __init__(self, console: tcod.console.Console, context: tcod.context.Context):
        self.console = console
        self.context = context
        self.tutorial_manager = get_tutorial_manager()
        self.tutorial_ui = TutorialUI(console)
        self.input_handler = InputHandler()

        # 튜토리얼 전용 파티 (전사 1명)
        self.tutorial_character = Character("튜토리얼 전사", "warrior", level=1)
        self.party = [self.tutorial_character]

        # 튜토리얼 인벤토리
        self.inventory = Inventory(base_weight=100.0, party=self.party)
        self.inventory.add_gold(0)

        self.current_step_index = 0
        self.completed = False

    def run(self) -> bool:
        """
        튜토리얼 플레이 모드 실행

        Returns:
            True: 완료, False: 중단
        """
        logger.info("튜토리얼 시작")

        # 튜토리얼 BGM 재생
        from src.audio import play_bgm
        play_bgm("tutorial", loop=True, fade_in=True)

        # 튜토리얼 순서
        tutorial_steps = [
            ("basic_movement", self._run_movement_tutorial),
            ("combat_intro", self._run_combat_tutorial),
            ("skill_system", self._run_skill_tutorial),
        ]

        for step_id, step_function in tutorial_steps:
            tutorial = self.tutorial_manager.tutorials.get(step_id)
            if not tutorial:
                logger.warning(f"튜토리얼을 찾을 수 없습니다: {step_id}")
                continue

            # 단계 시작 안내
            if not self._show_step_intro(tutorial):
                logger.info("튜토리얼 중단됨")
                return False

            # 실제 플레이
            result = step_function(tutorial)
            if not result:
                logger.info("튜토리얼 중단됨")
                return False

            # 단계 완료 안내
            self._show_step_complete(tutorial)

        # 전체 완료
        self._show_tutorial_complete()
        logger.info("튜토리얼 완료")
        return True

    def _show_step_intro(self, tutorial) -> bool:
        """
        단계 시작 안내

        Returns:
            True: 계속, False: 중단
        """
        self.console.clear()

        # 제목
        title = f"[ {tutorial.title} ]"
        self.console.print(
            (self.console.width - len(title)) // 2,
            self.console.height // 2 - 5,
            title,
            fg=(255, 215, 0)
        )

        # 설명
        desc_y = self.console.height // 2 - 3
        for i, line in enumerate(tutorial.description.split('\n')[:3]):
            if line.strip():
                self.console.print(
                    (self.console.width - len(line.strip())) // 2,
                    desc_y + i,
                    line.strip(),
                    fg=(200, 200, 200)
                )

        # 목표
        objective_text = f"목표: {tutorial.objective}"
        self.console.print(
            (self.console.width - len(objective_text)) // 2,
            self.console.height // 2 + 2,
            objective_text,
            fg=(0, 255, 255)
        )

        # 안내
        prompt = "Press Enter to start... (ESC to skip)"
        self.console.print(
            (self.console.width - len(prompt)) // 2,
            self.console.height // 2 + 5,
            prompt,
            fg=(150, 150, 150)
        )

        self.context.present(self.console)

        # 입력 대기
        for event in tcod.event.wait():
            if isinstance(event, tcod.event.KeyDown):
                if event.sym == tcod.event.KeySym.RETURN:
                    return True
                elif event.sym == tcod.event.KeySym.ESCAPE:
                    return False
            elif isinstance(event, tcod.event.Quit):
                return False

        return True

    def _show_step_complete(self, tutorial) -> None:
        """단계 완료 안내"""
        self.console.clear()

        # 완료 메시지
        complete_msg = f"✓ {tutorial.title} 완료!"
        self.console.print(
            (self.console.width - len(complete_msg)) // 2,
            self.console.height // 2 - 2,
            complete_msg,
            fg=(0, 255, 0)
        )

        # 보상
        star_fragments = tutorial.rewards.exp // 10
        reward_msg = f"보상: 별의 파편 +{star_fragments}"
        self.console.print(
            (self.console.width - len(reward_msg)) // 2,
            self.console.height // 2,
            reward_msg,
            fg=(255, 215, 0)
        )

        # 안내
        prompt = "Press any key to continue..."
        self.console.print(
            (self.console.width - len(prompt)) // 2,
            self.console.height // 2 + 3,
            prompt,
            fg=(150, 150, 150)
        )

        self.context.present(self.console)

        # 입력 대기
        for event in tcod.event.wait():
            if isinstance(event, (tcod.event.KeyDown, tcod.event.Quit)):
                break

    def _run_movement_tutorial(self, tutorial) -> bool:
        """이동 튜토리얼 실행"""
        logger.info("이동 튜토리얼 시작")

        # 튜토리얼 던전 생성
        dungeon = TutorialDungeon.create_movement_tutorial()

        # 탐험 시스템 초기화
        exploration = ExplorationSystem(dungeon, self.party, floor_number=0, inventory=self.inventory)
        start_x, start_y = dungeon.start_pos
        exploration.player.x = start_x
        exploration.player.y = start_y

        # 목표: 출구까지 이동
        target_x, target_y = dungeon.exit_pos

        while True:
            # 화면 렌더링
            self.console.clear()

            # 맵 렌더링 (간단하게)
            self._render_simple_map(exploration, target_x, target_y)

            # 가이드 메시지
            guide_msg = "방향키(↑↓←→)로 ★ 표시된 출구까지 이동하세요!"
            self.console.print(
                2, 2,
                guide_msg,
                fg=(255, 255, 0)
            )

            # 현재 위치
            pos_msg = f"위치: ({exploration.player.x}, {exploration.player.y})"
            self.console.print(
                2, 3,
                pos_msg,
                fg=(200, 200, 200)
            )

            # 컨트롤 안내
            self.console.print(
                2, self.console.height - 2,
                "[ESC] 튜토리얼 중단",
                fg=(150, 150, 150)
            )

            self.context.present(self.console)

            # 입력 처리
            for event in tcod.event.wait():
                action = self.input_handler.dispatch(event)

                if action == GameAction.ESCAPE:
                    return False
                elif action in [GameAction.MOVE_UP, GameAction.MOVE_DOWN,
                               GameAction.MOVE_LEFT, GameAction.MOVE_RIGHT]:
                    # 이동 처리
                    dx, dy = 0, 0
                    if action == GameAction.MOVE_UP:
                        dy = -1
                    elif action == GameAction.MOVE_DOWN:
                        dy = 1
                    elif action == GameAction.MOVE_LEFT:
                        dx = -1
                    elif action == GameAction.MOVE_RIGHT:
                        dx = 1

                    # 이동 가능한지 확인
                    if exploration.can_move(dx, dy):
                        exploration.player.x += dx
                        exploration.player.y += dy

                        # 목표 도달 확인
                        if exploration.player.x == target_x and exploration.player.y == target_y:
                            logger.info("이동 튜토리얼 완료")
                            return True

                elif isinstance(event, tcod.event.Quit):
                    return False

    def _run_combat_tutorial(self, tutorial) -> bool:
        """전투 튜토리얼 실행"""
        logger.info("전투 튜토리얼 - 단순화 버전")

        # 간단한 설명 화면
        self.console.clear()

        messages = [
            "전투 시스템 튜토리얼",
            "",
            "실제 전투는 메인 게임에서 경험할 수 있습니다.",
            "",
            "전투의 기본:",
            "• ATB 게이지가 1000에 도달하면 행동 가능",
            "• BRV 공격으로 적의 BRV를 깎기",
            "• HP 공격으로 실제 데미지 입히기",
            "• 적의 BRV를 0으로 만들면 BREAK!",
            "",
            "Press any key to continue..."
        ]

        y = 10
        for msg in messages:
            self.console.print(
                (self.console.width - len(msg)) // 2 if msg else 0,
                y,
                msg,
                fg=(255, 255, 255) if msg and "Press" not in msg else (150, 150, 150)
            )
            y += 1

        self.context.present(self.console)

        # 입력 대기
        for event in tcod.event.wait():
            if isinstance(event, (tcod.event.KeyDown, tcod.event.Quit)):
                break

        return True

    def _run_skill_tutorial(self, tutorial) -> bool:
        """스킬 튜토리얼 실행"""
        logger.info("스킬 튜토리얼 - 단순화 버전")

        # 간단한 설명 화면
        self.console.clear()

        messages = [
            "스킬 시스템 튜토리얼",
            "",
            "각 직업은 6개의 고유 스킬을 가지고 있습니다.",
            "",
            "스킬 타입:",
            "• BRV 공격 - BRV 축적",
            "• HP 공격 - HP 데미지",
            "• BRV+HP 공격 - 둘 다!",
            "• 지원 스킬 - 아군 강화/회복",
            "• 디버프 - 적 약화",
            "",
            "메인 게임에서 다양한 스킬을 사용해보세요!",
            "",
            "Press any key to continue..."
        ]

        y = 8
        for msg in messages:
            self.console.print(
                (self.console.width - len(msg)) // 2 if msg and "•" not in msg else 10,
                y,
                msg,
                fg=(255, 255, 255) if msg and "Press" not in msg else (150, 150, 150)
            )
            y += 1

        self.context.present(self.console)

        # 입력 대기
        for event in tcod.event.wait():
            if isinstance(event, (tcod.event.KeyDown, tcod.event.Quit)):
                break

        return True

    def _render_simple_map(self, exploration: ExplorationSystem, target_x: int, target_y: int) -> None:
        """간단한 맵 렌더링"""
        dungeon = exploration.dungeon
        player_x, player_y = exploration.player.x, exploration.player.y

        # 맵 렌더링 시작 위치
        map_start_x = 5
        map_start_y = 5

        for y in range(dungeon.height):
            for x in range(dungeon.width):
                tile = dungeon.tiles[y][x]
                screen_x = map_start_x + x
                screen_y = map_start_y + y

                # 타일 렌더링
                if x == player_x and y == player_y:
                    # 플레이어
                    char = "@"
                    color = (255, 255, 0)
                elif x == target_x and y == target_y:
                    # 목표
                    char = "★"
                    color = (0, 255, 0)
                elif not tile.walkable:
                    # 벽
                    char = "#"
                    color = (100, 100, 100)
                elif tile.walkable:
                    # 바닥
                    char = "."
                    color = (50, 50, 50)
                else:
                    char = "?"
                    color = (150, 150, 150)

                if screen_x < self.console.width and screen_y < self.console.height:
                    self.console.print(screen_x, screen_y, char, fg=color)

    def _show_tutorial_complete(self) -> None:
        """전체 튜토리얼 완료"""
        self.console.clear()

        complete_msg = "🎉 튜토리얼 완료! 🎉"
        self.console.print(
            (self.console.width - len(complete_msg)) // 2,
            self.console.height // 2 - 3,
            complete_msg,
            fg=(255, 215, 0)
        )

        msg1 = "이제 본 게임을 시작할 준비가 되었습니다!"
        self.console.print(
            (self.console.width - len(msg1)) // 2,
            self.console.height // 2 - 1,
            msg1,
            fg=(255, 255, 255)
        )

        msg2 = "설정 메뉴에서 언제든 튜토리얼을 다시 볼 수 있습니다."
        self.console.print(
            (self.console.width - len(msg2)) // 2,
            self.console.height // 2 + 1,
            msg2,
            fg=(200, 200, 200)
        )

        prompt = "Press any key to continue..."
        self.console.print(
            (self.console.width - len(prompt)) // 2,
            self.console.height // 2 + 4,
            prompt,
            fg=(150, 150, 150)
        )

        self.context.present(self.console)

        # 입력 대기
        for event in tcod.event.wait():
            if isinstance(event, (tcod.event.KeyDown, tcod.event.Quit)):
                break


def run_playable_tutorial(console: tcod.console.Console, context: tcod.context.Context) -> bool:
    """
    플레이 가능한 튜토리얼 실행

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트

    Returns:
        True: 완료, False: 중단
    """
    tutorial_mode = TutorialPlayMode(console, context)
    return tutorial_mode.run()
