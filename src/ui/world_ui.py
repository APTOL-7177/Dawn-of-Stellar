"""
월드 탐험 UI

플레이어가 던전을 돌아다니는 화면
"""

from typing import List, Optional
import tcod

from src.world.exploration import ExplorationSystem, ExplorationEvent, ExplorationResult
from src.world.map_renderer import MapRenderer
from src.ui.input_handler import InputHandler, GameAction
from src.ui.gauge_renderer import GaugeRenderer
from src.core.logger import get_logger, Loggers
from src.audio.audio_manager import play_bgm


logger = get_logger(Loggers.UI)


class WorldUI:
    """월드 탐험 UI"""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        exploration: ExplorationSystem,
        inventory=None,
        party=None
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.exploration = exploration
        self.inventory = inventory
        self.party = party
        self.map_renderer = MapRenderer(map_x=0, map_y=5)
        self.gauge_renderer = GaugeRenderer()

        # 초기화 로그
        logger.info(f"WorldUI 초기화 - inventory: {inventory is not None}, party: {party is not None}, party members: {len(party) if party else 0}")

        # 메시지 로그
        self.messages: List[str] = []
        self.max_messages = 5

        # 상태
        self.quit_requested = False
        self.combat_requested = False
        self.combat_enemies = None  # 전투에 참여할 적들 (맵에서 제거용)
        self.combat_num_enemies = 0  # 실제 전투 적 수
        self.floor_change_requested = None  # "up" or "down"

        # 종료 확인
        self.quit_confirm_mode = False
        self.quit_confirm_yes = False  # True: 예, False: 아니오

    def add_message(self, text: str):
        """메시지 추가"""
        self.messages.append(text)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
        logger.debug(f"메시지: {text}")

    def handle_input(self, action: GameAction, console=None, context=None) -> bool:
        """
        입력 처리

        Returns:
            True면 종료
        """
        logger.warning(f"[DEBUG] handle_input 호출됨: action={action}")

        # 종료 확인 모드
        if self.quit_confirm_mode:
            if action == GameAction.MOVE_LEFT:
                self.quit_confirm_yes = True
            elif action == GameAction.MOVE_RIGHT:
                self.quit_confirm_yes = False
            elif action == GameAction.CONFIRM:
                if self.quit_confirm_yes:
                    # 종료 확인
                    self.quit_requested = True
                    return True
                else:
                    # 취소
                    self.quit_confirm_mode = False
            elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                # 취소
                self.quit_confirm_mode = False
            return False

        if action == GameAction.QUIT or action == GameAction.ESCAPE:
            # 종료 확인 대화상자 표시
            self.quit_confirm_mode = True
            self.quit_confirm_yes = False
            return False

        # 메뉴 열기 (M키)
        if action == GameAction.MENU:
            logger.warning(f"[DEBUG] 메뉴 열기 요청")
            if self.inventory is not None and self.party is not None and console is not None and context is not None:
                from src.ui.game_menu import open_game_menu, MenuOption
                logger.warning("[DEBUG] 게임 메뉴 열기")
                result = open_game_menu(console, context, self.inventory, self.party, self.exploration)
                if result == MenuOption.QUIT:
                    self.quit_requested = True
                    return True
                elif result == MenuOption.LOAD_GAME:
                    # 게임을 불러온 경우 탐험 종료하고 main.py에서 처리하도록
                    self.quit_requested = True
                    return True
                return False
            else:
                logger.warning(f"메뉴를 열 수 없음 - inventory={self.inventory is not None}, party={self.party is not None}, console={console is not None}, context={context is not None}")

        # 인벤토리 열기 (I키)
        if action == GameAction.OPEN_INVENTORY:
            logger.warning(f"[DEBUG] 인벤토리 열기 요청")
            if self.inventory is not None and self.party is not None and console is not None and context is not None:
                from src.ui.inventory_ui import open_inventory
                logger.warning("[DEBUG] 인벤토리 열기 시도")
                open_inventory(console, context, self.inventory, self.party)
                return False
            else:
                logger.warning(f"인벤토리를 열 수 없음 - inventory={self.inventory is not None}, party={self.party is not None}, console={console is not None}, context={context is not None}")

        # 이동
        dx, dy = 0, 0

        if action == GameAction.MOVE_UP:
            dy = -1
        elif action == GameAction.MOVE_DOWN:
            dy = 1
        elif action == GameAction.MOVE_LEFT:
            dx = -1
        elif action == GameAction.MOVE_RIGHT:
            dx = 1

        if dx != 0 or dy != 0:
            result = self.exploration.move_player(dx, dy)
            logger.warning(f"[DEBUG] 이동 결과: event={result.event}")
            self._handle_exploration_result(result)
            # 전투가 트리거되면 즉시 루프 탈출
            if self.combat_requested:
                logger.warning(f"[DEBUG] 전투 요청됨! 루프 탈출")
                return True

        # 계단 이동
        elif action == GameAction.CONFIRM:
            tile = self.exploration.dungeon.get_tile(
                self.exploration.player.x,
                self.exploration.player.y
            )

            if tile:
                from src.world.tile import TileType
                if tile.tile_type == TileType.STAIRS_DOWN:
                    self.floor_change_requested = "down"
                    self.add_message("아래층으로 내려갑니다...")
                    return True
                elif tile.tile_type == TileType.STAIRS_UP:
                    self.floor_change_requested = "up"
                    self.add_message("위층으로 올라갑니다...")
                    return True

        return False

    def _handle_exploration_result(self, result: ExplorationResult):
        """탐험 결과 처리"""
        logger.warning(f"[DEBUG] 탐험 결과: event={result.event}, message={result.message}")

        if result.message:
            self.add_message(result.message)

        if result.event == ExplorationEvent.COMBAT:
            logger.warning(f"[DEBUG] 전투 이벤트 감지! combat_requested를 True로 설정")
            self.combat_requested = True
            # 전투에 참여할 적들 저장
            if result.data:
                if "num_enemies" in result.data:
                    self.combat_num_enemies = result.data["num_enemies"]
                    logger.warning(f"[DEBUG] 전투 적 수: {self.combat_num_enemies}마리")
                if "enemies" in result.data:
                    self.combat_enemies = result.data["enemies"]
                    logger.warning(f"[DEBUG] 맵 적 엔티티: {len(self.combat_enemies)}개")

        elif result.event == ExplorationEvent.TRAP_TRIGGERED:
            # 함정 데미지는 exploration 시스템에서 이미 적용됨
            # 추가 UI 처리 없음
            logger.debug("함정 발동 - 데미지 적용됨")

        elif result.event == ExplorationEvent.HEAL:
            # 회복은 exploration 시스템에서 이미 적용됨
            # 추가 UI 처리 없음
            logger.debug("회복 이벤트 - HP 회복됨")

        elif result.event == ExplorationEvent.TELEPORT:
            self.add_message(f"위치: ({self.exploration.player.x}, {self.exploration.player.y})")

    def render(self, console: tcod.console.Console):
        """렌더링"""
        console.clear()

        # 제목
        console.print(
            self.screen_width // 2 - 15,
            1,
            f"던전 탐험 - {self.exploration.floor_number}층",
            fg=(255, 255, 100)
        )

        # 맵 렌더링 (플레이어 중심)
        player = self.exploration.player
        self.map_renderer.render(
            console,
            self.exploration.dungeon,
            camera_x=max(0, player.x - 40),
            camera_y=max(0, player.y - 20),
            view_width=self.screen_width,
            view_height=35
        )

        # 적 위치 표시
        camera_x = max(0, player.x - 40)
        camera_y = max(0, player.y - 20)
        for enemy in self.exploration.enemies:
            enemy_screen_x = enemy.x - camera_x
            enemy_screen_y = 5 + (enemy.y - camera_y)
            if 0 <= enemy_screen_x < self.screen_width and 0 <= enemy_screen_y < 40:
                # 적 색상: 보스는 빨강, 일반 적은 주황색
                enemy_color = (255, 50, 50) if enemy.is_boss else (255, 150, 50)
                console.print(enemy_screen_x, enemy_screen_y, "E", fg=enemy_color)

        # 플레이어 위치 표시 (적 위에 덮어씀)
        screen_x = player.x - camera_x
        screen_y = 5 + (player.y - camera_y)
        if 0 <= screen_x < self.screen_width and 0 <= screen_y < 40:
            console.print(screen_x, screen_y, "@", fg=(255, 255, 100))

        # 파티 상태 (우측 상단)
        self._render_party_status(console)

        # 메시지 로그 (하단)
        self._render_messages(console)

        # 미니맵 (우측 하단)
        self.map_renderer.render_minimap(
            console,
            self.exploration.dungeon,
            minimap_x=self.screen_width - 22,
            minimap_y=self.screen_height - 19,  # 범례 공간 확보 (+2줄)
            player_pos=(self.exploration.player.x, self.exploration.player.y),
            enemies=self.exploration.enemies
        )

        # 조작법 (하단)
        console.print(
            5,
            self.screen_height - 2,
            "방향키: 이동  Z: 계단 이용  M: 메뉴  I: 인벤토리  ESC: 종료",
            fg=(180, 180, 180)
        )

        # 종료 확인 대화상자
        if self.quit_confirm_mode:
            self._render_quit_confirm(console)

    def _render_party_status(self, console: tcod.console.Console):
        """파티 상태 렌더링 (간단)"""
        x = self.screen_width - 30
        y = 3

        console.print(x, y, "[파티 상태]", fg=(100, 255, 100))

        for i, member in enumerate(self.exploration.player.party[:4]):
            my = y + 2 + i * 2

            # 이름과 HP 게이지를 한 줄에 표시
            console.print(x, my, f"{i+1}. {member.name[:10]}", fg=(255, 255, 255))

            # HP 게이지 (가로, 간단)
            console.print(x + 14, my, "HP:", fg=(200, 200, 200))
            self.gauge_renderer.render_bar(
                console, x + 17, my, 10,
                member.current_hp, member.max_hp, show_numbers=False
            )

        # 인벤토리 정보
        inv_y = y + 15
        console.print(x, inv_y, "[소지품]", fg=(200, 200, 255))
        console.print(x + 2, inv_y + 1, f"열쇠: {len(self.exploration.player.keys)}개", fg=(255, 215, 0))
        # 실제 인벤토리 객체의 아이템 수 표시 (slots 사용)
        item_count = len(self.inventory.slots) if self.inventory and hasattr(self.inventory, 'slots') else 0
        console.print(x + 2, inv_y + 2, f"아이템: {item_count}개", fg=(200, 200, 200))

    def _render_messages(self, console: tcod.console.Console):
        """메시지 로그"""
        msg_y = 40
        console.print(0, msg_y, "─" * self.screen_width, fg=(100, 100, 100))

        for i, msg in enumerate(self.messages[-self.max_messages:]):
            console.print(2, msg_y + 1 + i, msg, fg=(200, 200, 200))

    def _render_quit_confirm(self, console: tcod.console.Console):
        """종료 확인 대화상자"""
        box_width = 50
        box_height = 10
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        # 배경 박스
        console.draw_frame(
            box_x, box_y, box_width, box_height,
            "게임 종료",
            fg=(255, 100, 100),
            bg=(0, 0, 0)
        )

        # 메시지
        msg = "정말로 게임을 종료하시겠습니까?"
        console.print(
            box_x + (box_width - len(msg)) // 2,
            box_y + 3,
            msg,
            fg=(255, 255, 255)
        )

        msg2 = "저장하지 않은 진행 상황은 잃게 됩니다!"
        console.print(
            box_x + (box_width - len(msg2)) // 2,
            box_y + 5,
            msg2,
            fg=(255, 200, 100)
        )

        # 버튼
        y = box_y + 7
        yes_color = (255, 255, 100) if self.quit_confirm_yes else (180, 180, 180)
        no_color = (255, 255, 100) if not self.quit_confirm_yes else (180, 180, 180)

        console.print(
            box_x + 12, y,
            "[ 예 ]" if self.quit_confirm_yes else "  예  ",
            fg=yes_color
        )

        console.print(
            box_x + 28, y,
            "[아니오]" if not self.quit_confirm_yes else " 아니오 ",
            fg=no_color
        )

        # 도움말
        console.print(
            box_x + (box_width - 30) // 2,
            box_y + box_height - 1,
            "← →: 선택  Z: 확인  X: 취소",
            fg=(150, 150, 150)
        )


def run_exploration(
    console: tcod.console.Console,
    context: tcod.context.Context,
    exploration: ExplorationSystem,
    inventory=None,
    party=None,
    play_bgm_on_start: bool = True
) -> str:
    """
    탐험 실행

    Args:
        play_bgm_on_start: 탐험 시작 시 BGM 재생 여부 (기본 True, 전투 후 복귀 시 False)

    Returns:
        "quit", "combat", "floor_up", "floor_down"
    """
    ui = WorldUI(console.width, console.height, exploration, inventory, party)
    handler = InputHandler()

    logger.info(f"탐험 시작: {exploration.floor_number}층")

    # 남은 이벤트 제거 (불러오기 등에서 남은 키 입력 방지)
    tcod.event.get()

    # 층마다 다른 BGM 재생 (전투 후 복귀 시에는 재생하지 않음)
    if play_bgm_on_start:
        floor = exploration.floor_number
        if floor <= 5:
            # 초반 층: 일반 던전 BGM
            play_bgm("dungeon_normal")
        elif floor <= 10:
            # 중반 층: 탐색 던전 BGM
            play_bgm("dungeon_search")
        elif floor <= 15:
            # 중후반 층: 어두운 던전 BGM
            play_bgm("dungeon_dark")
        else:
            # 후반 층: 위험한 분위기
            play_bgm("danger")

    while True:
        # 렌더링
        ui.render(console)
        context.present(console)

        # 입력 처리
        for event in tcod.event.wait():
            action = handler.dispatch(event)

            if action:
                logger.warning(f"[DEBUG] 액션 수신: {action}")
                done = ui.handle_input(action, console, context)
                logger.warning(f"[DEBUG] handle_input 반환값: {done}")
                if done:
                    logger.warning(f"[DEBUG] 루프 탈출 - done=True")
                    break
            else:
                # action이 None인 경우 (키 입력 없음)
                # 다음 이벤트 처리로 넘어감
                continue

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return ("quit", None)

        # 상태 체크
        logger.warning(f"[DEBUG] 상태 체크: quit={ui.quit_requested}, combat={ui.combat_requested}, floor_change={ui.floor_change_requested}")
        if ui.quit_requested:
            return ("quit", None)
        elif ui.combat_requested:
            logger.warning(f"[DEBUG] 전투 반환! 적 {ui.combat_num_enemies}마리 (맵 엔티티: {len(ui.combat_enemies) if ui.combat_enemies else 0}개)")
            # 전투 데이터 반환: (적 수, 맵 적 엔티티)
            combat_data = {
                "num_enemies": ui.combat_num_enemies,
                "enemies": ui.combat_enemies
            }
            return ("combat", combat_data)
        elif ui.floor_change_requested:
            return (ui.floor_change_requested, None)
