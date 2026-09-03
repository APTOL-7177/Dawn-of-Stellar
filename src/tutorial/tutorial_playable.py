"""
플레이 가능한 튜토리얼 모드

실제로 캐릭터를 조작하며 배우는 인터랙티브 튜토리얼
"""

import tcod
import tcod.console
import tcod.event
import time
from typing import Optional, Tuple, List, Dict, Set

from src.tutorial.tutorial_dungeon import TutorialDungeon, StoryMapMarker
from src.tutorial.tutorial_manager import get_tutorial_manager
from src.tutorial.tutorial_ui import TutorialUI
from src.character.character import Character
from src.world.exploration import ExplorationSystem
from src.world.tile import TileType
from src.equipment.inventory import Inventory
from src.ui.input_handler import InputHandler, GameAction, iter_game_input, unified_input_handler
from src.ui.pointer import PointerButton, PointerEventKind
from src.ui.visual_tokens import rgb
from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.SYSTEM)


def flush_events():
    """이벤트 버퍼를 비웁니다 (이전 입력 제거)"""
    # 짧은 시간 대기하면서 모든 이벤트 비우기
    start_time = time.time()
    while time.time() - start_time < 0.2:  # 200ms 대기
        for _ in tcod.event.get():
            pass
        time.sleep(0.01)  # CPU 부하 방지
    unified_input_handler.clear_input_state()


def _coerce_pointer_action(action: GameAction | None, event) -> GameAction | None:
    if action is not None or event is None:
        return action
    pointer_event = unified_input_handler.process_pointer_event(event)
    if pointer_event is None:
        return None
    if pointer_event.kind is PointerEventKind.WHEEL:
        if pointer_event.wheel_delta > 0:
            return GameAction.MOVE_UP
        if pointer_event.wheel_delta < 0:
            return GameAction.MOVE_DOWN
    if pointer_event.kind is PointerEventKind.CLICK:
        if pointer_event.button is PointerButton.RIGHT:
            return GameAction.ESCAPE
        if pointer_event.button is PointerButton.LEFT:
            return GameAction.CONFIRM
    return None


def _pointer_surface_hint(event, text: str) -> str | None:
    pointer_event = unified_input_handler.process_pointer_event(event) if event is not None else None
    if pointer_event is not None and pointer_event.kind is PointerEventKind.HOVER:
        return text
    return None


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
            ("basic_interaction", self._run_interaction_tutorial),
            ("combat_intro", self._run_combat_tutorial),
            ("atb_system", self._run_atb_tutorial),
            ("brave_system", self._run_brave_tutorial),
            ("skill_system", self._run_skill_tutorial),
            ("job_system", self._run_job_tutorial),
            ("cooking", self._run_cooking_tutorial),
            ("alchemy", self._run_alchemy_tutorial),
            ("party_management", self._run_party_tutorial),
            ("equipment_inventory", self._run_equipment_tutorial),
            ("dungeon_exploration", self._run_dungeon_tutorial),
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

        # 이벤트 버퍼 비우기 (이전 입력 제거)
        flush_events()

        # 입력 대기
        for action, event in iter_game_input():
            action = _coerce_pointer_action(action, event)
            if action == GameAction.CONFIRM:
                return True
            elif action in (GameAction.ESCAPE, GameAction.CANCEL):
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
        prompt = "Press Z or Enter to continue..."
        self.console.print(
            (self.console.width - len(prompt)) // 2,
            self.console.height // 2 + 3,
            prompt,
            fg=(150, 150, 150)
        )

        self.context.present(self.console)

        # 이벤트 버퍼 비우기 (이전 입력 제거)
        flush_events()

        # 입력 대기 (Z 또는 엔터만)
        while True:
            for action, event in iter_game_input():
                action = _coerce_pointer_action(action, event)
                if action == GameAction.CONFIRM:
                    return

    # =========================================================================
    # 공통 헬퍼: 맵 탐험 루프
    # =========================================================================

    def _get_action_delta(self, action: GameAction) -> Tuple[int, int]:
        """GameAction에서 dx, dy 추출"""
        if action == GameAction.MOVE_UP:
            return 0, -1
        elif action == GameAction.MOVE_DOWN:
            return 0, 1
        elif action == GameAction.MOVE_LEFT:
            return -1, 0
        elif action == GameAction.MOVE_RIGHT:
            return 1, 0
        return 0, 0

    def _is_move_action(self, action: GameAction) -> bool:
        return action in (GameAction.MOVE_UP, GameAction.MOVE_DOWN,
                          GameAction.MOVE_LEFT, GameAction.MOVE_RIGHT)

    def _find_marker_at(self, markers: List[StoryMapMarker], x: int, y: int, marker_type: str = None) -> Optional[StoryMapMarker]:
        """특정 위치의 마커 찾기"""
        for m in markers:
            if m.x == x and m.y == y:
                if marker_type is None or m.marker_type == marker_type:
                    return m
        return None

    def _wait_confirm(self) -> bool:
        """Z/Enter 대기. ESC면 False"""
        flush_events()
        while True:
            for action, event in iter_game_input():
                action = _coerce_pointer_action(action, event)
                if action == GameAction.CONFIRM:
                    return True
                elif action in (GameAction.ESCAPE, GameAction.CANCEL):
                    return False

    def _show_message_screen(self, messages: List[str], title: str = "") -> bool:
        """메시지 화면 표시 후 확인 대기"""
        self.console.clear()

        y = 6
        if title:
            self.console.print(
                (self.console.width - len(title)) // 2, y,
                title, fg=(255, 215, 0)
            )
            y += 2

        for msg in messages:
            color = (150, 150, 150) if "Press" in msg else (255, 255, 255)
            cx = (self.console.width - len(msg)) // 2 if msg else 0
            self.console.print(cx, y, msg, fg=color)
            y += 1

        self.context.present(self.console)
        return self._wait_confirm()

    # =========================================================================
    # 01. 이동 튜토리얼
    # =========================================================================

    def _run_movement_tutorial(self, tutorial) -> bool:
        """이동 튜토리얼 실행"""
        logger.info("이동 튜토리얼 시작")

        dungeon = TutorialDungeon.create_movement_tutorial()
        exploration = ExplorationSystem(dungeon, self.party, floor_number=0, inventory=self.inventory)
        start_x, start_y = dungeon.start_pos
        exploration.player.x = start_x
        exploration.player.y = start_y

        target_x, target_y = dungeon.exit_pos

        while True:
            self.console.clear()
            self._render_simple_map(exploration, target_x, target_y)

            self.console.print(2, 2, "방향키로 ★ 출구까지 이동하세요!", fg=(255, 255, 0))
            self.console.print(2, 3, f"위치: ({exploration.player.x}, {exploration.player.y})", fg=(200, 200, 200))
            self.console.print(2, self.console.height - 2, "[ESC] 튜토리얼 중단", fg=(150, 150, 150))

            self.context.present(self.console)

            for action, event in iter_game_input():
                action = _coerce_pointer_action(action, event)
                if action == GameAction.ESCAPE:
                    return False
                elif self._is_move_action(action):
                    dx, dy = self._get_action_delta(action)
                    if exploration.can_move(dx, dy):
                        exploration.player.x += dx
                        exploration.player.y += dy
                        if exploration.player.x == target_x and exploration.player.y == target_y:
                            logger.info("이동 튜토리얼 완료")
                            return True

    # =========================================================================
    # 02. 상호작용 튜토리얼
    # =========================================================================

    def _run_interaction_tutorial(self, tutorial) -> bool:
        """상호작용 튜토리얼 - 실제로 오브젝트와 상호작용 체험"""
        logger.info("상호작용 튜토리얼 시작")

        dungeon = TutorialDungeon.create_interaction_tutorial()
        markers = getattr(dungeon, 'story_markers', [])
        exploration = ExplorationSystem(dungeon, self.party, floor_number=0, inventory=self.inventory)
        start_x, start_y = dungeon.start_pos
        exploration.player.x = start_x
        exploration.player.y = start_y
        target_x, target_y = dungeon.exit_pos

        interacted_objects: Set[Tuple[int, int]] = set()
        talked_to_npc = False
        required_interactions = 2  # NPC 대화 + 오브젝트 1개 이상

        while True:
            self.console.clear()
            self._render_simple_map(exploration, target_x, target_y, markers=markers)

            done_count = len(interacted_objects) + (1 if talked_to_npc else 0)
            can_exit = done_count >= required_interactions
            self.console.print(2, 2, "NPC(N)에게 Z키로 대화, 오브젝트에 Z키로 상호작용!", fg=(255, 255, 0))
            self.console.print(2, 3, f"상호작용: {done_count}/{required_interactions}  $=상자 ~=회복샘 +=문", fg=(200, 200, 200))
            if can_exit:
                self.console.print(2, 4, "조건 달성! ★ 출구로 이동하세요!", fg=(0, 255, 0))
            self.console.print(2, self.console.height - 2, "[Z] 상호작용  [ESC] 중단", fg=(150, 150, 150))

            self.context.present(self.console)

            for action, event in iter_game_input():
                action = _coerce_pointer_action(action, event)
                if action == GameAction.ESCAPE:
                    return False
                elif self._is_move_action(action):
                    dx, dy = self._get_action_delta(action)
                    if exploration.can_move(dx, dy):
                        exploration.player.x += dx
                        exploration.player.y += dy
                        if can_exit and exploration.player.x == target_x and exploration.player.y == target_y:
                            logger.info("상호작용 튜토리얼 완료")
                            return True
                elif action == GameAction.CONFIRM:
                    px, py = exploration.player.x, exploration.player.y
                    for ddx, ddy in [(0, 0), (0, -1), (0, 1), (-1, 0), (1, 0)]:
                        nx, ny = px + ddx, py + ddy
                        if 0 <= nx < dungeon.width and 0 <= ny < dungeon.height:
                            tile = dungeon.tiles[ny][nx]
                            # NPC 대화
                            npc = self._find_marker_at(markers, nx, ny, "npc")
                            if npc and not talked_to_npc:
                                talked_to_npc = True
                                self._show_message_screen(
                                    [npc.data.get("dialogue", "..."), "", "Press Z or Enter to continue..."],
                                    title=f"[ {npc.data.get('name', 'NPC')} ]"
                                )
                                break
                            # 오브젝트 상호작용
                            if tile.tile_type == TileType.CHEST and (nx, ny) not in interacted_objects:
                                interacted_objects.add((nx, ny))
                                self._show_message_screen(
                                    ["보물 상자를 열었습니다! 포션을 발견!", "", "Press Z or Enter..."],
                                    title="[ 보물 상자 ]"
                                )
                                break
                            if tile.tile_type == TileType.HEALING_SPRING and (nx, ny) not in interacted_objects:
                                interacted_objects.add((nx, ny))
                                self._show_message_screen(
                                    ["회복 샘에서 HP가 모두 회복되었습니다!", "", "Press Z or Enter..."],
                                    title="[ 회복의 샘 ]"
                                )
                                break
                            if tile.tile_type == TileType.DOOR and (nx, ny) not in interacted_objects:
                                interacted_objects.add((nx, ny))
                                dungeon.tiles[ny][nx] = dungeon.tiles[ny][nx].__class__(TileType.FLOOR, nx, ny)
                                break

    # =========================================================================
    # 03. 전투 튜토리얼 (맵 기반)
    # =========================================================================

    def _run_combat_tutorial(self, tutorial) -> bool:
        """전투 튜토리얼 - 맵에서 이동 후 전투 설명"""
        logger.info("전투 튜토리얼 시작")

        dungeon = TutorialDungeon.create_combat_tutorial()
        exploration = ExplorationSystem(dungeon, self.party, floor_number=0, inventory=self.inventory)
        start_x, start_y = dungeon.start_pos
        exploration.player.x = start_x
        exploration.player.y = start_y
        target_x, target_y = dungeon.exit_pos

        # 적 위치 (맵 중앙 부근)
        enemy_x, enemy_y = 14, 9
        enemy_encountered = False
        combat_actions = 0

        while True:
            self.console.clear()

            if not enemy_encountered:
                # 맵 탐험 단계
                self._render_simple_map(exploration, target_x, target_y,
                                        extra_markers=[(enemy_x, enemy_y, "E", (255, 80, 80))])

                self.console.print(2, 2, "맵을 탐험하세요! E는 적입니다.", fg=(255, 255, 0))
                self.console.print(2, self.console.height - 2, "[ESC] 중단", fg=(150, 150, 150))
                self.context.present(self.console)

                for action, event in iter_game_input():
                    action = _coerce_pointer_action(action, event)
                    if action == GameAction.ESCAPE:
                        return False
                    elif self._is_move_action(action):
                        dx, dy = self._get_action_delta(action)
                        if exploration.can_move(dx, dy):
                            exploration.player.x += dx
                            exploration.player.y += dy
                            # 적 위치에 도달하면 전투 시작
                            if abs(exploration.player.x - enemy_x) <= 1 and abs(exploration.player.y - enemy_y) <= 1:
                                enemy_encountered = True
            else:
                # 모의 전투 UI
                self.console.print(
                    (self.console.width - 20) // 2, 4,
                    "[ 모의 전투 ]", fg=(255, 80, 80)
                )

                enemy_brv = max(0, 30 - combat_actions * 15)
                enemy_hp = 20 if enemy_brv > 0 else max(0, 20 - (combat_actions - 2) * 10)
                is_broken = enemy_brv == 0

                self.console.print(10, 7, f"훈련용 인형  BRV: {enemy_brv}  HP: {enemy_hp}", fg=(255, 150, 150))
                if is_broken:
                    self.console.print(10, 8, "** BREAK! **", fg=(255, 255, 0))

                self.console.print(10, 11, f"나의 BRV: {100 + combat_actions * 15}", fg=(100, 200, 255))

                # 행동 선택
                if not is_broken:
                    self.console.print(10, 14, "▶ BRV 공격 (Z키)", fg=(255, 255, 0))
                    self.console.print(10, 15, "  적의 BRV를 깎아 BREAK를 노리세요!", fg=(200, 200, 200))
                else:
                    self.console.print(10, 14, "▶ HP 공격 (Z키)", fg=(255, 255, 0))
                    self.console.print(10, 15, "  BREAK 상태! HP 공격으로 마무리!", fg=(200, 200, 200))

                self.console.print(10, 18, f"행동 {combat_actions}/3", fg=(150, 150, 150))
                self.context.present(self.console)

                for action, event in iter_game_input():
                    action = _coerce_pointer_action(action, event)
                    if action == GameAction.CONFIRM:
                        combat_actions += 1
                        if combat_actions >= 3:
                            logger.info("combat tutorial complete")
                            return True
                    elif action in (GameAction.ESCAPE, GameAction.CANCEL):
                        return False

    # =========================================================================
    # 04. ATB 튜토리얼
    # =========================================================================

    def _run_atb_tutorial(self, tutorial) -> bool:
        """ATB 튜토리얼 - 아레나 맵에서 ATB 게이지 시뮬레이션"""
        logger.info("ATB 튜토리얼 시작")

        dungeon = TutorialDungeon.create_atb_tutorial()
        markers = getattr(dungeon, 'story_markers', [])
        exploration = ExplorationSystem(dungeon, self.party, floor_number=0, inventory=self.inventory)
        start_x, start_y = dungeon.start_pos
        exploration.player.x = start_x
        exploration.player.y = start_y
        target_x, target_y = dungeon.exit_pos

        # ATB 시뮬레이션 상태
        atb_phase = False  # 아레나 안에서 적 근처 도달 시 True
        atb_gauge = 0
        atb_actions = 0
        enemy_marker = self._find_marker_at(markers, None, None)
        # 적 위치 찾기
        enemy_pos = None
        for m in markers:
            if m.marker_type == "enemy":
                enemy_pos = (m.x, m.y)
                break

        while True:
            self.console.clear()

            if not atb_phase:
                # 맵 탐험
                extra = []
                if enemy_pos:
                    extra.append((enemy_pos[0], enemy_pos[1], "E", (255, 80, 80)))
                self._render_simple_map(exploration, target_x, target_y, markers=markers, extra_markers=extra)

                self.console.print(2, 2, "아레나에서 적(E)에게 접근하세요!", fg=(255, 255, 0))
                self.console.print(2, self.console.height - 2, "[ESC] 중단", fg=(150, 150, 150))
                self.context.present(self.console)

                for action, event in iter_game_input():
                    action = _coerce_pointer_action(action, event)
                    if action == GameAction.ESCAPE:
                        return False
                    elif self._is_move_action(action):
                        dx, dy = self._get_action_delta(action)
                        if exploration.can_move(dx, dy):
                            exploration.player.x += dx
                            exploration.player.y += dy
                            if enemy_pos and abs(exploration.player.x - enemy_pos[0]) <= 1 and abs(exploration.player.y - enemy_pos[1]) <= 1:
                                atb_phase = True
            else:
                # ATB 시뮬레이션 UI
                self.console.print(
                    (self.console.width - 20) // 2, 3,
                    "[ ATB 시스템 체험 ]", fg=(255, 215, 0)
                )

                # ATB 게이지 바
                bar_width = 30
                filled = int(bar_width * atb_gauge / 1000)
                bar = "█" * filled + "░" * (bar_width - filled)
                gauge_color = (0, 255, 0) if atb_gauge >= 1000 else (100, 200, 255)
                self.console.print(10, 7, f"ATB: [{bar}] {atb_gauge}/1000", fg=gauge_color)

                if atb_gauge >= 1000:
                    self.console.print(10, 9, "▶ 게이지 충전 완료! Z키로 행동!", fg=(255, 255, 0))
                    self.console.print(10, 10, "  (공격을 선택합니다)", fg=(200, 200, 200))
                else:
                    self.console.print(10, 9, "Z키를 눌러 게이지를 충전하세요...", fg=(200, 200, 200))

                self.console.print(10, 13, f"행동 완료: {atb_actions}/2", fg=(150, 150, 150))
                self.console.print(10, 15, "ATB 게이지가 1000에 도달하면 행동 가능!", fg=(0, 255, 255))
                self.context.present(self.console)

                for action, event in iter_game_input():
                    action = _coerce_pointer_action(action, event)
                    if action in (GameAction.ESCAPE, GameAction.CANCEL):
                        return False
                    elif action == GameAction.CONFIRM:
                            if atb_gauge < 1000:
                                atb_gauge = min(1000, atb_gauge + 350)
                            else:
                                atb_actions += 1
                                atb_gauge = 0
                                if atb_actions >= 2:
                                    logger.info("ATB 튜토리얼 완료")
                                    return True

    # =========================================================================
    # 05. BRV/HP 튜토리얼
    # =========================================================================

    def _run_brave_tutorial(self, tutorial) -> bool:
        """BRV/HP 튜토리얼 - BREAK 후 HP 공격 연습"""
        logger.info("BRV/HP 튜토리얼 시작")

        dungeon = TutorialDungeon.create_brave_tutorial()
        markers = getattr(dungeon, 'story_markers', [])
        exploration = ExplorationSystem(dungeon, self.party, floor_number=0, inventory=self.inventory)
        start_x, start_y = dungeon.start_pos
        exploration.player.x = start_x
        exploration.player.y = start_y
        target_x, target_y = dungeon.exit_pos

        # 적 위치
        enemy_pos = None
        for m in markers:
            if m.marker_type == "enemy":
                enemy_pos = (m.x, m.y)
                break

        combat_phase = False
        enemy_brv = 50
        enemy_hp = 10
        my_brv = 100
        broke_enemy = False
        hp_attacked = False

        while True:
            self.console.clear()

            if not combat_phase:
                extra = []
                if enemy_pos:
                    extra.append((enemy_pos[0], enemy_pos[1], "E", (255, 80, 80)))
                self._render_simple_map(exploration, target_x, target_y, markers=markers, extra_markers=extra)

                self.console.print(2, 2, "적(E)에게 접근해서 BRV/HP 시스템을 배우세요!", fg=(255, 255, 0))
                self.console.print(2, self.console.height - 2, "[ESC] 중단", fg=(150, 150, 150))
                self.context.present(self.console)

                for action, event in iter_game_input():
                    action = _coerce_pointer_action(action, event)
                    if action == GameAction.ESCAPE:
                        return False
                    elif self._is_move_action(action):
                        dx, dy = self._get_action_delta(action)
                        if exploration.can_move(dx, dy):
                            exploration.player.x += dx
                            exploration.player.y += dy
                            if enemy_pos and abs(exploration.player.x - enemy_pos[0]) <= 1 and abs(exploration.player.y - enemy_pos[1]) <= 1:
                                combat_phase = True
            else:
                # BRV/HP 모의 전투
                self.console.print(
                    (self.console.width - 22) // 2, 3,
                    "[ BRV/HP 시스템 체험 ]", fg=(255, 215, 0)
                )

                # 적 상태
                self.console.print(10, 6, f"BRV 허수아비", fg=(255, 150, 150))
                brv_color = (255, 0, 0) if enemy_brv == 0 else (255, 200, 100)
                self.console.print(10, 7, f"  BRV: {enemy_brv}", fg=brv_color)
                self.console.print(10, 8, f"  HP:  {enemy_hp}", fg=(255, 100, 100))
                if enemy_brv == 0:
                    self.console.print(25, 7, "BREAK!", fg=(255, 255, 0))

                # 내 상태
                self.console.print(10, 10, f"나의 BRV: {my_brv}", fg=(100, 200, 255))

                # 행동 선택
                if not broke_enemy:
                    self.console.print(10, 13, "▶ BRV 공격 (Z키) - 적 BRV를 깎으세요!", fg=(255, 255, 0))
                    self.console.print(10, 14, "  적의 BRV가 0이 되면 BREAK 발생!", fg=(200, 200, 200))
                elif not hp_attacked:
                    self.console.print(10, 13, "▶ HP 공격 (Z키) - BREAK 상태에서 HP 공격!", fg=(255, 255, 0))
                    self.console.print(10, 14, "  축적한 BRV만큼 HP 데미지!", fg=(200, 200, 200))

                self.context.present(self.console)

                for action, event in iter_game_input():
                    action = _coerce_pointer_action(action, event)
                    if action in (GameAction.ESCAPE, GameAction.CANCEL):
                        return False
                    elif action == GameAction.CONFIRM:
                            if not broke_enemy:
                                enemy_brv = max(0, enemy_brv - 30)
                                my_brv += 30
                                if enemy_brv == 0:
                                    broke_enemy = True
                            elif not hp_attacked:
                                enemy_hp = 0
                                hp_attacked = True
                                logger.info("BRV/HP 튜토리얼 완료")
                                return True

    # =========================================================================
    # 06. 스킬 튜토리얼 (맵 기반)
    # =========================================================================

    def _run_skill_tutorial(self, tutorial) -> bool:
        """스킬 튜토리얼 - 맵에서 이동 후 스킬 메뉴 체험"""
        logger.info("스킬 튜토리얼 시작")

        dungeon = TutorialDungeon.create_skill_tutorial()
        exploration = ExplorationSystem(dungeon, self.party, floor_number=0, inventory=self.inventory)
        start_x, start_y = dungeon.start_pos
        exploration.player.x = start_x
        exploration.player.y = start_y
        target_x, target_y = dungeon.exit_pos

        # 스킬 연습 타겟 (CHEST 위치)
        skill_target_x, skill_target_y = 20, 10
        skill_menu_opened = False

        skill_info = [
            ("강타", "BRV 공격", "강력한 일격으로 BRV를 축적합니다", "물리 배율 2.5x"),
            ("방패 강타", "BRV 공격", "방패로 가격하여 BRV를 축적합니다", "물리 배율 2.0x"),
            ("전력 일격", "HP 공격", "축적한 BRV로 HP 데미지를 줍니다", "BRV 소모 HP 공격"),
            ("전투 함성", "지원", "아군 전체의 공격력을 증가시킵니다", "공격력 +30% 3턴"),
            ("분노", "버프", "자신의 공격력을 크게 증가시킵니다", "공격력 +50% 2턴"),
            ("검무", "BRV+HP", "BRV 축적 후 즉시 HP 공격", "배율 1.8x + HP"),
        ]

        while True:
            self.console.clear()

            if not skill_menu_opened:
                # 맵 탐험
                self._render_simple_map(exploration, target_x, target_y)
                self.console.print(2, 2, "보물상자($) 근처에서 Z키로 스킬 메뉴를 열어보세요!", fg=(255, 255, 0))
                self.console.print(2, self.console.height - 2, "[Z] 상호작용  [ESC] 중단", fg=(150, 150, 150))
                self.context.present(self.console)

                for action, event in iter_game_input():
                    if action == GameAction.ESCAPE:
                        return False
                    elif self._is_move_action(action):
                        dx, dy = self._get_action_delta(action)
                        if exploration.can_move(dx, dy):
                            exploration.player.x += dx
                            exploration.player.y += dy
                    elif action == GameAction.CONFIRM:
                        if abs(exploration.player.x - skill_target_x) <= 1 and abs(exploration.player.y - skill_target_y) <= 1:
                            skill_menu_opened = True
            else:
                # 스킬 메뉴 UI (기존 인터랙티브 스킬 메뉴)
                selected = 0
                while True:
                    self.console.clear()
                    title = "스킬 시스템 - 전사 스킬 체험"
                    self.console.print((self.console.width - len(title)) // 2, 2, title, fg=(255, 215, 0))
                    guide = "↑↓ 스킬 선택  |  Z/Enter: 완료  |  ESC: 건너뛰기"
                    self.console.print((self.console.width - len(guide)) // 2, 4, guide, fg=(150, 150, 150))

                    y = 7
                    for i, (name, type_, desc, detail) in enumerate(skill_info):
                        prefix = "▶" if i == selected else " "
                        color = (255, 255, 0) if i == selected else (200, 200, 200)
                        self.console.print(5, y, f"{prefix} {name}", fg=color)
                        y += 1

                    y = 7 + len(skill_info) + 2
                    name, type_, desc, detail = skill_info[selected]
                    self.console.print(5, y, f"━━━ {name} ━━━", fg=(0, 255, 255))
                    self.console.print(5, y + 1, f"타입: {type_}", fg=(255, 215, 0))
                    self.console.print(5, y + 2, f"설명: {desc}", fg=(255, 255, 255))
                    self.console.print(5, y + 3, f"효과: {detail}", fg=(0, 255, 0))

                    self.context.present(self.console)

                    for action, event in iter_game_input():
                        if action == GameAction.ESCAPE:
                            return False
                        elif action == GameAction.MOVE_UP:
                            selected = (selected - 1) % len(skill_info)
                        elif action == GameAction.MOVE_DOWN:
                            selected = (selected + 1) % len(skill_info)
                        elif action == GameAction.CONFIRM:
                            logger.info("스킬 튜토리얼 완료")
                            return True

    # =========================================================================
    # 07. 직업 튜토리얼
    # =========================================================================

    def _run_job_tutorial(self, tutorial) -> bool:
        """직업 튜토리얼 - 4개 방 방문으로 직업 특성 파악 + 제단에서 비교 열람"""
        logger.info("직업 튜토리얼 시작")

        dungeon = TutorialDungeon.create_job_tutorial()
        markers = getattr(dungeon, 'story_markers', [])
        exploration = ExplorationSystem(dungeon, self.party, floor_number=0, inventory=self.inventory)
        start_x, start_y = dungeon.start_pos
        exploration.player.x = start_x
        exploration.player.y = start_y
        target_x, target_y = dungeon.exit_pos

        visited_trainers: Set[str] = set()
        trainer_positions = {}
        for m in markers:
            if m.marker_type == "npc":
                trainer_positions[m.data.get("name", "")] = (m.x, m.y)

        viewed_comparison = False  # 제단에서 직업 비교 열람 여부
        altar_x, altar_y = 15, 10

        while True:
            self.console.clear()

            extra = []
            for m in markers:
                if m.marker_type == "npc":
                    name = m.data.get("name", "")
                    color = (0, 200, 0) if name in visited_trainers else (0, 255, 255)
                    extra.append((m.x, m.y, "N", color))

            self._render_simple_map(exploration, target_x, target_y, markers=markers, extra_markers=extra)

            visited_count = len(visited_trainers)
            can_exit = visited_count >= 2 and viewed_comparison
            self.console.print(2, 2, f"훈련관 방문: {visited_count}/4  N에게 접근 후 Z키!", fg=(255, 255, 0))
            if visited_count >= 2 and not viewed_comparison:
                self.console.print(2, 3, "중앙 제단(^)에서 Z키로 직업 비교표를 확인하세요!", fg=(0, 255, 255))
            elif viewed_comparison:
                self.console.print(2, 3, "직업 학습 완료! ★ 출구로 이동하세요!", fg=(0, 255, 0))
            else:
                self.console.print(2, 3, "훈련관 2명 이상 방문 후 제단에서 직업 비교!", fg=(200, 200, 200))
            self.console.print(2, self.console.height - 2, "[Z] 대화/상호작용  [ESC] 중단", fg=(150, 150, 150))
            self.context.present(self.console)

            for action, event in iter_game_input():
                if action == GameAction.ESCAPE:
                    return False
                elif self._is_move_action(action):
                    dx, dy = self._get_action_delta(action)
                    if exploration.can_move(dx, dy):
                        exploration.player.x += dx
                        exploration.player.y += dy
                        if can_exit and exploration.player.x == target_x and exploration.player.y == target_y:
                            logger.info("직업 튜토리얼 완료")
                            return True
                elif action == GameAction.CONFIRM:
                    px, py = exploration.player.x, exploration.player.y
                    # 제단에서 직업 비교 열람
                    if not viewed_comparison and abs(px - altar_x) <= 1 and abs(py - altar_y) <= 1 and visited_count >= 2:
                        viewed_comparison = self._show_job_comparison()
                        continue
                    # NPC 대화
                    for name, (nx, ny) in trainer_positions.items():
                        if abs(px - nx) <= 1 and abs(py - ny) <= 1:
                            visited_trainers.add(name)
                            for m in markers:
                                if m.data.get("name") == name:
                                    dialogue = m.data.get("dialogue", "...")
                                    self._show_message_screen(
                                        [dialogue, "", "Press Z or Enter to continue..."],
                                        title=f"[ {name} ]"
                                    )
                                    break
                            break

    def _show_job_comparison(self) -> bool:
        """직업 비교표 열람 메뉴 (기본 해금 6직업)"""
        jobs = [
            ("전사 (Warrior)", "HP ★★★  ATK ★★★  DEF ★★★  SPD ★★",
             "근접 물리 딜러. 높은 HP와 방어력으로 전열을 지킨다."),
            ("아크메이지 (Archmage)", "HP ★★   ATK ★    DEF ★    SPD ★★",
             "원소 마법의 대가. 강력한 광역기로 적을 소멸시킨다."),
            ("성직자 (Cleric)", "HP ★★   ATK ★    DEF ★★   SPD ★★",
             "치유와 정화의 사제. 파티의 생명선이자 버프 담당."),
            ("도적 (Rogue)", "HP ★★   ATK ★★   DEF ★    SPD ★★★",
             "은신과 기습의 달인. 빠른 속도와 치명타가 강점."),
            ("기사 (Knight)", "HP ★★★  ATK ★★   DEF ★★★  SPD ★",
             "철벽 방어의 탱커. 아군을 보호하며 적의 공격을 유도."),
            ("궁수 (Archer)", "HP ★★   ATK ★★★  DEF ★    SPD ★★★",
             "원거리 정밀 사격. 높은 명중률과 치명타로 적을 처치."),
        ]
        selected = 0

        while True:
            self.console.clear()
            self.console.print(
                (self.console.width - 18) // 2, 2,
                "[ 직업 비교 안내서 ]", fg=(180, 100, 255)
            )
            self.console.print(
                (self.console.width - 40) // 2, 4,
                "↑↓ 직업 선택   Z/Enter: 확인 후 닫기", fg=(150, 150, 150)
            )
            self.console.print(6, 5, "직업은 게임 시작 시 선택하며, 모험 중에는 변경 불가!", fg=(255, 100, 100))

            y = 8
            for i, (name, stats, desc) in enumerate(jobs):
                prefix = "▶" if i == selected else " "
                color = (255, 255, 0) if i == selected else (200, 200, 200)
                self.console.print(5, y, f"{prefix} {name}", fg=color)
                if i == selected:
                    self.console.print(7, y + 1, stats, fg=(100, 200, 255))
                    self.console.print(7, y + 2, desc, fg=(0, 255, 255))
                    y += 4
                else:
                    y += 1

            self.context.present(self.console)

            for action, event in iter_game_input():
                if action == GameAction.ESCAPE:
                    return False
                elif action == GameAction.MOVE_UP:
                    selected = (selected - 1) % len(jobs)
                elif action == GameAction.MOVE_DOWN:
                    selected = (selected + 1) % len(jobs)
                elif action == GameAction.CONFIRM:
                    return True

    # =========================================================================
    # 08. 요리 튜토리얼 (핵심 실습)
    # =========================================================================

    def _run_cooking_tutorial(self, tutorial) -> bool:
        """요리 튜토리얼 - 재료 수집 후 요리솥에서 실제 요리"""
        logger.info("요리 튜토리얼 시작")

        dungeon = TutorialDungeon.create_cooking_tutorial()
        markers = getattr(dungeon, 'story_markers', [])
        exploration = ExplorationSystem(dungeon, self.party, floor_number=0, inventory=self.inventory)
        start_x, start_y = dungeon.start_pos
        exploration.player.x = start_x
        exploration.player.y = start_y
        target_x, target_y = dungeon.exit_pos

        # 기본 재료 미리 지급
        self._give_cooking_ingredients()

        # 재료 수집 추적
        collected_ingredients: Set[Tuple[int, int]] = set()
        cooked = False

        # 요리솥 위치
        cooking_pot_pos = None
        for m in markers:
            if m.marker_type == "cooking_pot":
                cooking_pot_pos = (m.x, m.y)
                break

        while True:
            self.console.clear()

            extra = []
            # 재료 위치 표시 (수집 안 된 것만)
            for m in markers:
                if m.marker_type == "ingredient" and (m.x, m.y) not in collected_ingredients:
                    extra.append((m.x, m.y, "*", (100, 255, 100)))
            # 요리솥
            if cooking_pot_pos:
                extra.append((cooking_pot_pos[0], cooking_pot_pos[1], "P", (255, 165, 0)))

            self._render_simple_map(exploration, target_x, target_y, markers=markers, extra_markers=extra)

            if not cooked:
                self.console.print(2, 2, "재료(*)를 밟아 수집! 요리솥(P) 근처에서 Z키!", fg=(255, 255, 0))
                self.console.print(2, 3, f"수집한 재료: {len(collected_ingredients)}개 (+기본 재료 보유)", fg=(200, 200, 200))
            else:
                self.console.print(2, 2, "요리 완료! ★ 출구로 이동하세요!", fg=(0, 255, 0))

            self.console.print(2, self.console.height - 2, "[Z] 상호작용  [ESC] 중단", fg=(150, 150, 150))
            self.context.present(self.console)

            for action, event in iter_game_input():
                if action == GameAction.ESCAPE:
                    return False
                elif self._is_move_action(action):
                    dx, dy = self._get_action_delta(action)
                    if exploration.can_move(dx, dy):
                        exploration.player.x += dx
                        exploration.player.y += dy

                        # 재료 자동 수집
                        px, py = exploration.player.x, exploration.player.y
                        for m in markers:
                            if m.marker_type == "ingredient" and m.x == px and m.y == py and (px, py) not in collected_ingredients:
                                collected_ingredients.add((px, py))
                                ing_id = m.data.get("ingredient_id", "")
                                self._collect_ingredient(ing_id)
                                # 바닥 타일로 변경
                                dungeon.tiles[py][px] = dungeon.tiles[py][px].__class__(TileType.FLOOR, px, py)

                        # 출구 도달 (요리 완료 후)
                        if cooked and px == target_x and py == target_y:
                            logger.info("요리 튜토리얼 완료")
                            return True

                elif action == GameAction.CONFIRM:
                    # 요리솥 근처에서 상호작용
                    if not cooked and cooking_pot_pos:
                        px, py = exploration.player.x, exploration.player.y
                        if abs(px - cooking_pot_pos[0]) <= 1 and abs(py - cooking_pot_pos[1]) <= 1:
                            # 실제 요리 UI 호출
                            try:
                                from src.ui.cooking_ui import open_cooking_pot
                                result = open_cooking_pot(self.console, self.context, self.inventory, is_cooking_pot=True)
                                if result:
                                    cooked = True
                                    logger.info("요리 제작 성공!")
                            except Exception as e:
                                logger.warning(f"요리 UI 실행 실패: {e}")
                                # 폴백: 자동 완료
                                cooked = True


    # =========================================================================
    # 09. 연금술 튜토리얼 (핵심 실습)
    # =========================================================================

    def _run_alchemy_tutorial(self, tutorial) -> bool:
        """연금술 튜토리얼 - 재료 수집 후 연금술 테이블에서 실제 제작"""
        logger.info("연금술 튜토리얼 시작")

        dungeon = TutorialDungeon.create_alchemy_tutorial()
        markers = getattr(dungeon, 'story_markers', [])
        exploration = ExplorationSystem(dungeon, self.party, floor_number=0, inventory=self.inventory)
        start_x, start_y = dungeon.start_pos
        exploration.player.x = start_x
        exploration.player.y = start_y
        target_x, target_y = dungeon.exit_pos

        # 기본 재료 지급
        self._give_alchemy_ingredients()

        collected_ingredients: Set[Tuple[int, int]] = set()
        crafted = False

        # 연금술 테이블 위치
        alchemy_pos = None
        for m in markers:
            if m.marker_type == "alchemy_table":
                alchemy_pos = (m.x, m.y)
                break

        while True:
            self.console.clear()

            extra = []
            for m in markers:
                if m.marker_type == "ingredient" and (m.x, m.y) not in collected_ingredients:
                    extra.append((m.x, m.y, "*", (100, 255, 100)))
            if alchemy_pos:
                extra.append((alchemy_pos[0], alchemy_pos[1], "A", (180, 100, 255)))

            self._render_simple_map(exploration, target_x, target_y, markers=markers, extra_markers=extra)

            if not crafted:
                self.console.print(2, 2, "재료(*)를 밟아 수집! 연금술 테이블(A) 근처에서 Z키!", fg=(255, 255, 0))
                self.console.print(2, 3, f"수집한 재료: {len(collected_ingredients)}개 (+기본 재료 보유)", fg=(200, 200, 200))
            else:
                self.console.print(2, 2, "제작 완료! ★ 출구로 이동하세요!", fg=(0, 255, 0))

            self.console.print(2, self.console.height - 2, "[Z] 상호작용  [ESC] 중단", fg=(150, 150, 150))
            self.context.present(self.console)

            for action, event in iter_game_input():
                if action == GameAction.ESCAPE:
                    return False
                elif self._is_move_action(action):
                    dx, dy = self._get_action_delta(action)
                    if exploration.can_move(dx, dy):
                        exploration.player.x += dx
                        exploration.player.y += dy

                        # 재료 자동 수집
                        px, py = exploration.player.x, exploration.player.y
                        for m in markers:
                            if m.marker_type == "ingredient" and m.x == px and m.y == py and (px, py) not in collected_ingredients:
                                collected_ingredients.add((px, py))
                                ing_id = m.data.get("ingredient_id", "")
                                self._collect_ingredient(ing_id)
                                dungeon.tiles[py][px] = dungeon.tiles[py][px].__class__(TileType.FLOOR, px, py)

                        # 출구 도달
                        if crafted and px == target_x and py == target_y:
                            logger.info("연금술 튜토리얼 완료")
                            return True

                elif action == GameAction.CONFIRM:
                    if not crafted and alchemy_pos:
                        px, py = exploration.player.x, exploration.player.y
                        if abs(px - alchemy_pos[0]) <= 1 and abs(py - alchemy_pos[1]) <= 1:
                            try:
                                from src.ui.alchemy_ui import open_alchemy_lab
                                open_alchemy_lab(self.console, self.context, self.inventory, floor_level=1, party=self.party)
                                crafted = True
                                logger.info("연금술 제작 성공!")
                            except Exception as e:
                                logger.warning(f"연금술 UI 실행 실패: {e}")
                                crafted = True


    # =========================================================================
    # 10. 파티 관리 튜토리얼
    # =========================================================================

    def _run_party_tutorial(self, tutorial) -> bool:
        """파티 관리 튜토리얼 - 파티 정보 확인 + 인벤토리 열기 체험"""
        logger.info("파티 관리 튜토리얼 시작")

        dungeon = TutorialDungeon.create_party_tutorial()
        markers = getattr(dungeon, 'story_markers', [])
        exploration = ExplorationSystem(dungeon, self.party, floor_number=0, inventory=self.inventory)
        start_x, start_y = dungeon.start_pos
        exploration.player.x = start_x
        exploration.player.y = start_y
        target_x, target_y = dungeon.exit_pos

        talked_to_npc = False
        viewed_stats = False
        opened_inventory = False

        while True:
            self.console.clear()
            self._render_simple_map(exploration, target_x, target_y, markers=markers)

            done_count = sum([talked_to_npc, viewed_stats, opened_inventory])
            can_exit = done_count >= 2
            self.console.print(2, 2, "NPC 대화 + 파티 정보/인벤토리 확인!", fg=(255, 255, 0))
            tasks = []
            tasks.append(f"{'V' if talked_to_npc else ' '} NPC 대화")
            tasks.append(f"{'V' if viewed_stats else ' '} 파티 정보 확인 (N근처 Z키)")
            tasks.append(f"{'V' if opened_inventory else ' '} 인벤토리 열기 ($근처 Z키)")
            self.console.print(2, 3, "  ".join(tasks), fg=(200, 200, 200))
            if can_exit:
                self.console.print(2, 4, "조건 달성! ★ 출구로 이동!", fg=(0, 255, 0))
            self.console.print(2, self.console.height - 2, "[Z] 상호작용  [ESC] 중단", fg=(150, 150, 150))
            self.context.present(self.console)

            for action, event in iter_game_input():
                if action == GameAction.ESCAPE:
                    return False
                elif self._is_move_action(action):
                    dx, dy = self._get_action_delta(action)
                    if exploration.can_move(dx, dy):
                        exploration.player.x += dx
                        exploration.player.y += dy
                        if can_exit and exploration.player.x == target_x and exploration.player.y == target_y:
                            logger.info("파티 관리 튜토리얼 완료")
                            return True
                elif action == GameAction.CONFIRM:
                    px, py = exploration.player.x, exploration.player.y
                    for ddx, ddy in [(0, 0), (0, -1), (0, 1), (-1, 0), (1, 0)]:
                        nx, ny = px + ddx, py + ddy
                        if 0 <= nx < dungeon.width and 0 <= ny < dungeon.height:
                            npc = self._find_marker_at(markers, nx, ny, "npc")
                            if npc and npc.data.get("name") == "party_guide" and not talked_to_npc:
                                talked_to_npc = True
                                self._show_message_screen(
                                    [npc.data.get("dialogue", "..."), "", "Press Z or Enter..."],
                                    title="[ 파티 안내원 ]"
                                )
                                break
                            if npc and npc.data.get("name") == "stats_guide" and not viewed_stats:
                                viewed_stats = True
                                # 파티 정보 표시
                                ch = self.tutorial_character
                                stats_lines = [
                                    f"이름: {ch.name}  직업: {ch.job_id}  레벨: {ch.level}",
                                    f"HP: {ch.hp}/{ch.max_hp}  BRV: {ch.brv}",
                                    f"공격력: {ch.attack}  방어력: {ch.defense}  속도: {ch.speed}",
                                    "",
                                    "실제 게임에서는 더 자세한 정보를 확인할 수 있습니다!",
                                    "", "Press Z or Enter..."
                                ]
                                self._show_message_screen(stats_lines, title="[ 파티원 정보 ]")
                                break
                            tile = dungeon.tiles[ny][nx]
                            inv_marker = self._find_marker_at(markers, nx, ny, "inventory_chest")
                            if (tile.tile_type == TileType.CHEST or inv_marker) and not opened_inventory:
                                opened_inventory = True
                                try:
                                    from src.ui.inventory_ui import open_inventory
                                    open_inventory(self.console, self.context, self.inventory, self.party)
                                except Exception as e:
                                    logger.warning(f"인벤토리 UI 실행 실패: {e}")
                                    self._show_message_screen(
                                        ["인벤토리를 열었습니다!", "아이템을 확인하고 관리할 수 있습니다.", "", "Press Z or Enter..."],
                                        title="[ 인벤토리 ]"
                                    )
                                break

    # =========================================================================
    # 11. 장비/대장간 튜토리얼
    # =========================================================================

    def _run_equipment_tutorial(self, tutorial) -> bool:
        """장비/대장간 튜토리얼 - 장비 수집 + 모루 수리 체험"""
        logger.info("장비/대장간 튜토리얼 시작")

        dungeon = TutorialDungeon.create_equipment_tutorial()
        markers = getattr(dungeon, 'story_markers', [])
        exploration = ExplorationSystem(dungeon, self.party, floor_number=0, inventory=self.inventory)
        start_x, start_y = dungeon.start_pos
        exploration.player.x = start_x
        exploration.player.y = start_y
        target_x, target_y = dungeon.exit_pos

        # 장비 아이템 미리 지급 (내구도 낮은 상태)
        self._give_damaged_equipment()

        collected_items: Set[Tuple[int, int]] = set()
        talked_to_npc = False
        used_anvil = False
        opened_inventory = False

        # 모루 위치
        anvil_pos = None
        for m in markers:
            if m.marker_type == "anvil":
                anvil_pos = (m.x, m.y)
                break

        while True:
            self.console.clear()

            extra = []
            for m in markers:
                if m.marker_type == "equipment_item" and (m.x, m.y) not in collected_items:
                    extra.append((m.x, m.y, "!", (255, 255, 255)))
                elif m.marker_type == "anvil":
                    extra.append((m.x, m.y, "M", (255, 165, 0)))
                elif m.marker_type == "inventory_chest":
                    extra.append((m.x, m.y, "$", (255, 215, 0)))

            self._render_simple_map(exploration, target_x, target_y, markers=markers, extra_markers=extra)

            done_count = sum([talked_to_npc, used_anvil, len(collected_items) > 0])
            can_exit = used_anvil or (talked_to_npc and opened_inventory)
            self.console.print(2, 2, "장비(!)를 줍고, 모루(M)에서 수리 체험!", fg=(255, 255, 0))
            tasks = []
            tasks.append(f"{'V' if talked_to_npc else ' '} 대장장이 대화")
            tasks.append(f"{'V' if len(collected_items) > 0 else ' '} 장비 수집({len(collected_items)}개)")
            tasks.append(f"{'V' if used_anvil else ' '} 모루에서 수리")
            self.console.print(2, 3, "  ".join(tasks), fg=(200, 200, 200))
            if can_exit:
                self.console.print(2, 4, "체험 완료! ★ 출구로!", fg=(0, 255, 0))
            self.console.print(2, self.console.height - 2, "[Z] 상호작용  [ESC] 중단", fg=(150, 150, 150))
            self.context.present(self.console)

            for action, event in iter_game_input():
                if action == GameAction.ESCAPE:
                    return False
                elif self._is_move_action(action):
                    dx, dy = self._get_action_delta(action)
                    if exploration.can_move(dx, dy):
                        exploration.player.x += dx
                        exploration.player.y += dy

                        # 장비 자동 수집 (밟으면)
                        px, py = exploration.player.x, exploration.player.y
                        for m in markers:
                            if m.marker_type == "equipment_item" and m.x == px and m.y == py and (px, py) not in collected_items:
                                collected_items.add((px, py))
                                item_type = m.data.get("item_type", "item")
                                item_names = {"sword": "연습용 검", "shield": "연습용 방패", "armor": "연습용 갑옷"}
                                name = item_names.get(item_type, "장비")
                                self._show_message_screen(
                                    [f"{name}을(를) 획득했습니다!", "", "Press Z or Enter..."],
                                    title="[ 장비 획득 ]"
                                )
                                dungeon.tiles[py][px] = dungeon.tiles[py][px].__class__(TileType.FLOOR, px, py)

                        if can_exit and px == target_x and py == target_y:
                            logger.info("장비/대장간 튜토리얼 완료")
                            return True

                elif action == GameAction.CONFIRM:
                    px, py = exploration.player.x, exploration.player.y
                    for ddx, ddy in [(0, 0), (0, -1), (0, 1), (-1, 0), (1, 0)]:
                        nx, ny = px + ddx, py + ddy
                        if 0 <= nx < dungeon.width and 0 <= ny < dungeon.height:
                            # 대장장이 NPC
                            npc = self._find_marker_at(markers, nx, ny, "npc")
                            if npc and not talked_to_npc:
                                talked_to_npc = True
                                self._show_message_screen(
                                    [npc.data.get("dialogue", "..."), "",
                                     "장비에는 내구도가 있으며, 전투 중 닳습니다.",
                                     "모루에서 수리하면 내구도를 회복할 수 있습니다!",
                                     "", "Press Z or Enter..."],
                                    title="[ 대장장이 ]"
                                )
                                break
                            # 모루 사용
                            if anvil_pos and abs(nx - anvil_pos[0]) <= 0 and abs(ny - anvil_pos[1]) <= 0:
                                if not used_anvil:
                                    try:
                                        from src.ui.anvil_ui import open_anvil_ui
                                        # 모루 타일 객체 생성
                                        anvil_tile = dungeon.tiles[anvil_pos[1]][anvil_pos[0]]
                                        if not hasattr(anvil_tile, 'used'):
                                            anvil_tile.used = False
                                        open_anvil_ui(self.console, self.context, self.inventory, anvil_tile)
                                        used_anvil = True
                                        logger.info("모루 수리 체험 완료!")
                                    except Exception as e:
                                        logger.warning(f"모루 UI 실행 실패: {e}")
                                        used_anvil = True
                                        self._show_message_screen(
                                            ["모루에서 장비를 수리했습니다!",
                                             "내구도가 회복되었습니다.", "", "Press Z or Enter..."],
                                            title="[ 대장간 수리 ]"
                                        )
                                    break
                            # 인벤토리 열기
                            inv_marker = self._find_marker_at(markers, nx, ny, "inventory_chest")
                            if inv_marker and not opened_inventory:
                                opened_inventory = True
                                try:
                                    from src.ui.inventory_ui import open_inventory
                                    open_inventory(self.console, self.context, self.inventory, self.party)
                                except Exception as e:
                                    logger.warning(f"인벤토리 UI 실행 실패: {e}")
                                break

    # =========================================================================
    # 12. 던전 탐험 튜토리얼 (종합 실습)
    # =========================================================================

    def _run_dungeon_tutorial(self, tutorial) -> bool:
        """던전 탐험 튜토리얼 - 미니 던전 종합 실습"""
        logger.info("던전 탐험 튜토리얼 시작")

        dungeon = TutorialDungeon.create_dungeon_exploration_tutorial()
        markers = getattr(dungeon, 'story_markers', [])
        exploration = ExplorationSystem(dungeon, self.party, floor_number=0, inventory=self.inventory)
        start_x, start_y = dungeon.start_pos
        exploration.player.x = start_x
        exploration.player.y = start_y
        target_x, target_y = dungeon.exit_pos

        interacted: Set[Tuple[int, int]] = set()
        collected: Set[Tuple[int, int]] = set()

        while True:
            self.console.clear()

            extra = []
            for m in markers:
                if m.marker_type == "ingredient" and (m.x, m.y) not in collected:
                    extra.append((m.x, m.y, "*", (100, 255, 100)))

            self._render_simple_map(exploration, target_x, target_y, markers=markers, extra_markers=extra)

            self.console.print(2, 2, "미니 던전 종합 실습! 출구(★)를 찾아가세요!", fg=(255, 255, 0))
            self.console.print(2, 3, f"$=상자 ~=회복샘 +=문 *=재료 N=NPC", fg=(200, 200, 200))
            self.console.print(2, self.console.height - 2, "[Z] 상호작용  [ESC] 중단", fg=(150, 150, 150))
            self.context.present(self.console)

            for action, event in iter_game_input():
                if action == GameAction.ESCAPE:
                    return False
                elif self._is_move_action(action):
                    dx, dy = self._get_action_delta(action)
                    if exploration.can_move(dx, dy):
                        exploration.player.x += dx
                        exploration.player.y += dy
                        px, py = exploration.player.x, exploration.player.y

                        # 재료 자동 수집
                        for m in markers:
                            if m.marker_type == "ingredient" and m.x == px and m.y == py and (px, py) not in collected:
                                collected.add((px, py))
                                self._collect_ingredient(m.data.get("ingredient_id", ""))
                                dungeon.tiles[py][px] = dungeon.tiles[py][px].__class__(TileType.FLOOR, px, py)

                        # 함정 경고
                        tile = dungeon.tiles[py][px]
                        if tile.tile_type == TileType.TRAP and (px, py) not in interacted:
                            interacted.add((px, py))
                            self._show_message_screen(
                                ["함정을 밟았습니다! 주의하세요!", "던전에는 다양한 함정이 숨어있습니다.", "", "Press Z or Enter..."],
                                title="[ 함정! ]"
                            )

                        # 출구 도달
                        if px == target_x and py == target_y:
                            logger.info("던전 탐험 튜토리얼 완료")
                            return True

                elif action == GameAction.CONFIRM:
                    px, py = exploration.player.x, exploration.player.y
                    for ddx, ddy in [(0, 0), (0, -1), (0, 1), (-1, 0), (1, 0)]:
                        nx, ny = px + ddx, py + ddy
                        if 0 <= nx < dungeon.width and 0 <= ny < dungeon.height:
                            tile = dungeon.tiles[ny][nx]
                            # NPC 대화
                            npc = self._find_marker_at(markers, nx, ny, "npc")
                            if npc and (nx, ny) not in interacted:
                                interacted.add((nx, ny))
                                self._show_message_screen(
                                    [npc.data.get("dialogue", "..."), "", "Press Z or Enter..."],
                                    title=f"[ {npc.data.get('name', 'NPC')} ]"
                                )
                                break
                            # 보물 상자
                            if tile.tile_type == TileType.CHEST and (nx, ny) not in interacted:
                                interacted.add((nx, ny))
                                self._show_message_screen(
                                    ["보물 상자를 열었습니다!", "포션을 발견!", "", "Press Z or Enter..."],
                                    title="[ 보물 상자 ]"
                                )
                                break
                            # 회복 샘
                            if tile.tile_type == TileType.HEALING_SPRING and (nx, ny) not in interacted:
                                interacted.add((nx, ny))
                                self._show_message_screen(
                                    ["치유의 샘에서 HP가 회복되었습니다!", "", "Press Z or Enter..."],
                                    title="[ 치유의 샘 ]"
                                )
                                break
                            # 크리스탈
                            if tile.tile_type == TileType.CRYSTAL and (nx, ny) not in interacted:
                                interacted.add((nx, ny))
                                self._show_message_screen(
                                    ["크리스탈에서 MP가 회복되었습니다!", "", "Press Z or Enter..."],
                                    title="[ 크리스탈 ]"
                                )
                                break
                            # 문 열기
                            if tile.tile_type == TileType.DOOR and (nx, ny) not in interacted:
                                interacted.add((nx, ny))
                                dungeon.tiles[ny][nx] = dungeon.tiles[ny][nx].__class__(TileType.FLOOR, nx, ny)
                                break

    # =========================================================================
    # 재료 관리 헬퍼
    # =========================================================================

    def _give_damaged_equipment(self):
        """장비 튜토리얼용 내구도 낮은 장비 지급"""
        try:
            from src.equipment.item_system import ItemGenerator
            # 간단한 철검 생성 (static method, 랜덤 접사 없이)
            sword = ItemGenerator.create_weapon("iron_sword", add_random_affixes=False)
            if hasattr(sword, 'current_durability') and hasattr(sword, 'max_durability'):
                sword.current_durability = max(1, sword.max_durability // 3)
            self.inventory.add_item(sword)
            logger.info("연습용 장비 지급 완료")
        except Exception as e:
            logger.warning(f"장비 지급 실패: {e}")

    def _give_cooking_ingredients(self):
        """요리 튜토리얼용 기본 재료 지급"""
        try:
            from src.gathering.ingredient import IngredientDatabase
            db = IngredientDatabase.INGREDIENTS
            for ing_id in ["monster_meat", "magic_herb", "red_mushroom"]:
                if ing_id in db:
                    self.inventory.add_item(db[ing_id], quantity=2)
        except Exception as e:
            logger.warning(f"요리 재료 지급 실패: {e}")

    def _give_alchemy_ingredients(self):
        """연금술 튜토리얼용 기본 재료 지급"""
        try:
            from src.gathering.ingredient import IngredientDatabase
            db = IngredientDatabase.INGREDIENTS
            for ing_id in ["magic_herb", "blue_mushroom", "red_mushroom"]:
                if ing_id in db:
                    self.inventory.add_item(db[ing_id], quantity=2)
        except Exception as e:
            logger.warning(f"연금술 재료 지급 실패: {e}")

    def _collect_ingredient(self, ingredient_id: str):
        """재료 수집 (인벤토리에 추가)"""
        try:
            from src.gathering.ingredient import IngredientDatabase
            db = IngredientDatabase.INGREDIENTS
            if ingredient_id in db:
                self.inventory.add_item(db[ingredient_id], quantity=1)
                logger.info(f"재료 수집: {ingredient_id}")
        except Exception as e:
            logger.warning(f"재료 수집 실패 ({ingredient_id}): {e}")

    # =========================================================================
    # 렌더링
    # =========================================================================

    def _render_simple_map(
        self,
        exploration: ExplorationSystem,
        target_x: int,
        target_y: int,
        markers: List[StoryMapMarker] = None,
        extra_markers: List[Tuple[int, int, str, Tuple[int, int, int]]] = None,
    ) -> None:
        """
        간단한 맵 렌더링 (확장판)

        Args:
            exploration: 탐험 시스템
            target_x, target_y: 출구 좌표
            markers: 스토리 마커 목록
            extra_markers: 추가 마커 [(x, y, char, color), ...]
        """
        dungeon = exploration.dungeon
        player_x, player_y = exploration.player.x, exploration.player.y

        map_start_x = 5
        map_start_y = 5

        # extra_markers를 딕셔너리로 변환
        extra_dict: Dict[Tuple[int, int], Tuple[str, Tuple[int, int, int]]] = {}
        if extra_markers:
            for mx, my, mc, mcolor in extra_markers:
                extra_dict[(mx, my)] = (mc, mcolor)

        # NPC 마커 딕셔너리
        npc_dict: Dict[Tuple[int, int], str] = {}
        if markers:
            for m in markers:
                if m.marker_type == "npc":
                    npc_dict[(m.x, m.y)] = m.data.get("name", "NPC")

        for y in range(dungeon.height):
            for x in range(dungeon.width):
                tile = dungeon.tiles[y][x]
                screen_x = map_start_x + x
                screen_y = map_start_y + y

                if screen_x >= self.console.width or screen_y >= self.console.height:
                    continue

                # 우선순위: 플레이어 > 출구 > extra_markers > NPC > 타일
                if x == player_x and y == player_y:
                    char, color = "@", (255, 255, 0)
                elif x == target_x and y == target_y:
                    char, color = "★", (0, 255, 0)
                elif (x, y) in extra_dict:
                    char, color = extra_dict[(x, y)]
                elif (x, y) in npc_dict:
                    char, color = "N", (0, 255, 255)
                elif tile.tile_type == TileType.INGREDIENT:
                    char, color = "*", (100, 255, 100)
                elif tile.tile_type == TileType.CHEST:
                    char, color = "$", (255, 215, 0)
                elif tile.tile_type == TileType.DOOR:
                    char, color = "+", (180, 120, 60)
                elif tile.tile_type == TileType.HEALING_SPRING:
                    char, color = "~", (80, 150, 255)
                elif tile.tile_type == TileType.ALTAR:
                    char, color = "^", (180, 100, 255)
                elif tile.tile_type == TileType.CRYSTAL:
                    char, color = "o", (0, 255, 255)
                elif tile.tile_type == TileType.SHOP:
                    char, color = "S", (255, 215, 0)
                elif tile.tile_type == TileType.ITEM:
                    char, color = "!", (255, 255, 255)
                elif not tile.walkable:
                    char, color = "#", (100, 100, 100)
                elif tile.walkable:
                    char, color = ".", (50, 50, 50)
                else:
                    char, color = "?", (150, 150, 150)

                self.console.print(screen_x, screen_y, char, fg=color)

    def _show_tutorial_complete(self) -> None:
        """전체 튜토리얼 완료"""
        self.console.clear()

        complete_msg = "튜토리얼 완료!"
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

        prompt = "Press Z or Enter to continue..."
        self.console.print(
            (self.console.width - len(prompt)) // 2,
            self.console.height // 2 + 4,
            prompt,
            fg=(150, 150, 150)
        )

        self.context.present(self.console)

        # 이벤트 버퍼 비우기 (이전 입력 제거)
        flush_events()

        # 입력 대기 (Z 또는 엔터만)
        while True:
            for action, event in iter_game_input():
                if action == GameAction.CONFIRM:
                    return


def run_playable_tutorial(console: tcod.console.Console, context: tcod.context.Context) -> bool:
    """
    [비활성] 레거시 플레이 가능 튜토리얼 진입점

    Story Mode가 유일한 정식 온보딩 (2026-09 설계 결정).
    세이브 호환성을 위해 TutorialPlayMode 클래스는 유지하지만,
    이 진입 함수는 더 이상 UI를 띄우지 않고 즉시 중단(False)을 반환한다.
    재진입 요청은 Story Mode Act 1 onboarding으로 리다이렉트된다.

    Args:
        console: 사용하지 않음 (호환성 유지)
        context: 사용하지 않음 (호환성 유지)

    Returns:
        False: 항상 (레거시 진입 차단)
    """
    logger.warning(
        "레거시 플레이 가능 튜토리얼 진입 차단 - Story Mode로 안내됩니다. "
        "(튜토리얼은 메인 메뉴의 스토리 모드 Act 1에서 진행하세요)"
    )
    return False
