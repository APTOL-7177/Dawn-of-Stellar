"""
RPG 모드 매니저

튜토리얼 완료 후 해금되는 자유 탐험 + 챕터 기반 RPG 모드.
원신 스타일의 하나의 거대한 심리스 오픈월드 맵에서 7개 지역을 탐험한다.
패배해도 세이브가 유지되며, 마을 캠프파이어에서 부활한다.
"""

import json
import time
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple, Set

import tcod.console
import tcod.context
from src.ui.input_handler import iter_game_input, GameAction
from src.ui.pointer import PointerButton, PointerEventKind

from src.core.logger import get_logger
from src.core.paths import get_project_root
from src.character.character import Character
from src.rpg_mode.party_builder import build_rpg_party
from src.rpg_mode.rpg_world_config import (
    REGIONS, REGION_MAP, RPG_WORLD_WIDTH, RPG_WORLD_HEIGHT,
    get_enemy_level_for_region,
)
from src.rpg_mode.rpg_world_generator import generate_rpg_world, _get_region_for_point
from src.rpg_mode.rpg_chapter_system import RPGChapterSystem, RPGProgress
from src.rpg_mode.lily_dialogue import LilyDialogueManager
from src.rpg_mode.objective_tracker import RPGObjectiveTracker

logger = get_logger("rpg_mode")


def _rpg_pointer_action(event) -> GameAction | None:
    if event is None:
        return None
    from src.ui.input_handler import unified_input_handler
    pointer_event = unified_input_handler.process_pointer_event(event)
    if pointer_event is None:
        return None
    if pointer_event.kind is PointerEventKind.CLICK:
        if pointer_event.button is PointerButton.RIGHT:
            return GameAction.CANCEL
        if pointer_event.button is PointerButton.LEFT:
            return GameAction.CONFIRM
    if pointer_event.kind is PointerEventKind.WHEEL:
        return GameAction.PAGE_UP if pointer_event.wheel_delta > 0 else GameAction.PAGE_DOWN
    return None

# 튜토리얼(스토리 모드) 전체 챕터 목록
_ALL_TUTORIAL_CHAPTERS = [
    "act1_prologue", "act1_ch1", "act1_ch2", "act1_ch3",
    "act1_ch4", "act1_ch5", "act1_ch6", "act1_boss",
    "act2_ch1", "act2_ch2", "act2_ch3", "act2_ch4",
    "act2_ch5", "act2_ch6", "act2_ch7", "act2_boss",
    "act3_ch1", "act3_ch2", "act3_ch3", "act3_ch4",
    "act3_ch5", "act3_ch6", "act3_ch7", "act3_ch8",
    "act3_ch9", "act3_boss",
    "act4_ch1", "act4_ch2", "act4_ch3", "act4_ch4",
    "act4_ch5", "act4_ch6", "act4_ch7", "act4_boss",
    "act5_ch1", "act5_ch2", "act5_ch3", "act5_ch4",
    "act5_ch5", "act5_ch6", "act5_ch7", "act5_finale",
]


class RPGModeResult(Enum):
    """RPG 모드 종료 결과"""
    RETURN_TO_MENU = "return_to_menu"
    COMPLETED = "completed"
    GAME_OVER = "game_over"


class RPGModeManager:
    """
    RPG 모드 총괄 매니저

    - 해금 조건 확인
    - RPG 전용 세이브 관리
    - 파티 자동 구성
    - 하나의 심리스 월드맵에서 탐험/전투 루프 실행
    - 마을 건물 상호작용 (주방, 대장간, 연금술 등)
    - 패배 시 세이브 유지 & 마을 부활
    """

    def __init__(self, console: tcod.console.Console, context: tcod.context.Context):
        self.console = console
        self.context = context
        self.party: List[Character] = []
        self.protagonist_name: str = "크리스"
        self.companion_names: List[str] = []

        # RPG 진행 상태
        self.progress = RPGProgress()
        self.chapter_system = RPGChapterSystem()

        # 월드맵 (하나의 거대한 심리스 맵)
        self.world_dungeon = None
        self.spawn_points: Dict[str, Tuple[int, int]] = {}
        self.world_seed: int = 0

        # 릴리 대사 시스템
        self.lily_dialogue = LilyDialogueManager()
        self.objective_tracker = RPGObjectiveTracker()

        # 다음 탐험 시작 시 표시할 릴리 메시지
        self._pending_lily_message: Optional[str] = None

        # 이미 표시한 챕터 이벤트 추적 (중복 방지)
        self._shown_chapter_events: set = set()

        # 플레이어 위치 (월드맵 좌표)
        self.player_x: int = 0
        self.player_y: int = 0

        # 마을 시설 (TownManager 활용, MAX 레벨)
        self.town_manager = None

        # 세이브에서 복원할 인벤토리/골드/마을 데이터
        self._saved_inventory_full: Optional[Dict] = None  # Inventory.to_dict() 결과
        self._saved_inventory_items: list = []  # 하위 호환용
        self._saved_inventory_gold: int = 0
        self._saved_town_data: Optional[Dict] = None

    def run(self) -> RPGModeResult:
        """RPG 모드 메인 루프"""
        logger.info("RPG 모드 시작")

        # 1) 해금 확인
        if not self.check_unlock():
            logger.warning("RPG 모드 미해금 상태에서 진입 시도")
            return RPGModeResult.RETURN_TO_MENU

        # 2) 세이브 로드 또는 새로 생성
        save_data = self._load_or_create_save()

        # 3) 파티 구성
        if save_data and "party" in save_data:
            self._restore_party_from_save(save_data)
        else:
            self._build_new_party()

        # 4) 월드맵 생성 (또는 세이브에서 시드 복원)
        self._setup_world(save_data)

        # 5) 마을 시설 초기화 (MAX 레벨)
        self._setup_town_facilities()

        # 6) 새 게임이면 프롤로그 표시
        is_new_game = save_data is None
        if is_new_game:
            self._show_prologue()

        # 7) 메인 게임 루프
        result = self._main_game_loop()

        return result

    @staticmethod
    def check_unlock() -> bool:
        """튜토리얼(스토리 모드) 전체 완료 여부를 확인한다."""
        progress_path = get_project_root() / "user_data" / "story_progress.json"
        if not progress_path.exists():
            return False

        try:
            with open(progress_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            completed = set(data.get("completed_chapters", []))
            required = set(_ALL_TUTORIAL_CHAPTERS)
            return required.issubset(completed)
        except Exception as e:
            logger.error(f"스토리 진행도 확인 실패: {e}")
            return False

    # ── 세이브 관리 ──────────────────────────────────────────

    def _load_or_create_save(self) -> Optional[Dict[str, Any]]:
        """RPG 세이브를 로드하거나, 없으면 None 반환"""
        from src.persistence.save_system import SaveSystem

        save_system = SaveSystem()
        save_data = save_system.load_game("save_rpg")

        if save_data and save_data.get("rpg_mode"):
            logger.info("기존 RPG 세이브 로드 성공")
            self.protagonist_name = save_data.get("protagonist_name", "크리스")
            self.companion_names = save_data.get("companion_names", [])
            self.world_seed = save_data.get("world_seed", 0)
            self.player_x = save_data.get("player_x", 0)
            self.player_y = save_data.get("player_y", 0)

            # RPG 진행 상태 복원
            rpg_progress = save_data.get("rpg_progress")
            if rpg_progress:
                self.progress = RPGProgress.from_dict(rpg_progress)

            # 인벤토리 데이터 보존 (메인 루프에서 복원용)
            self._saved_inventory_full = save_data.get("inventory_full", None)
            self._saved_inventory_items = save_data.get("inventory_items", [])
            self._saved_inventory_gold = save_data.get("inventory_gold", 0)

            # 마을 창고 데이터 보존 (메인 루프에서 복원용)
            self._saved_town_data = save_data.get("town_manager", None)

            # 랜덤 이벤트 매니저 상태 복원 (시간당 제한 타이머 포함)
            random_event_state = save_data.get("random_event_state")
            if random_event_state:
                try:
                    from src.world.random_events import get_random_event_manager
                    get_random_event_manager().from_dict(random_event_state)
                except Exception:
                    pass

            return save_data

        logger.info("RPG 세이브 없음 - 새 게임 시작")
        return None

    def _build_new_party(self):
        """새 파티를 자동 구성한다."""
        protagonist_job = "warrior"
        progress_path = get_project_root() / "user_data" / "story_progress.json"

        try:
            if progress_path.exists():
                with open(progress_path, "r", encoding="utf-8") as f:
                    progress = json.load(f)
                selected = progress.get("selected_job")
                if selected:
                    protagonist_job = selected
        except Exception as e:
            logger.warning(f"직업 선택 정보 로드 실패: {e}")

        self.party = build_rpg_party(protagonist_job, level=1)
        self.companion_names = [c.name for c in self.party[1:]]
        logger.info(f"새 파티 구성: {[c.name + '(' + c.character_class + ')' for c in self.party]}")

    def _restore_party_from_save(self, save_data: Dict[str, Any]):
        """세이브 데이터에서 파티를 복원한다 (싱글모드와 동일한 완전 복원)."""
        from src.persistence.save_system import deserialize_party_member
        party_data = save_data.get("party", [])
        self.party = []

        for char_data in party_data:
            try:
                # deserialize_party_member: 장비, 스킬, 경험치, 버프, 기믹 등 완전 복원
                char = deserialize_party_member(char_data)
                self.party.append(char)
            except Exception as e:
                logger.warning(f"파티원 완전 복원 실패, 기본 복원 시도: {e}")
                # 폴백: 기본 정보만 복원
                name = char_data.get("name", "???")
                job = char_data.get("character_class", "warrior")
                level = char_data.get("level", 1)
                char = Character(name=name, character_class=job, level=level)
                char.current_hp = char_data.get("current_hp", char.max_hp)
                char.current_mp = char_data.get("current_mp", char.max_mp)
                char.wound = char_data.get("wound", 0)
                self.party.append(char)

        self.companion_names = [c.name for c in self.party[1:]]
        logger.info(f"파티 복원 (장비/스킬 포함): {[c.name + '(Lv' + str(c.level) + ')' for c in self.party]}")

    def _setup_world(self, save_data: Optional[Dict] = None):
        """
        하나의 심리스 월드맵 생성.
        같은 시드를 사용하면 같은 맵이 생성되므로, 세이브에서 시드를 복원한다.
        로딩 애니메이션을 표시하며 백그라운드에서 생성.
        """
        import random
        import threading

        if save_data and self.world_seed:
            seed = self.world_seed
        else:
            seed = random.randint(0, 999999)
            self.world_seed = seed

        logger.info(f"월드맵 생성 시작 (seed={seed}, {RPG_WORLD_WIDTH}x{RPG_WORLD_HEIGHT})")

        # 백그라운드 스레드에서 월드 생성
        result = {}
        gen_done = threading.Event()

        def _generate():
            try:
                dungeon, spawns = generate_rpg_world(
                    width=RPG_WORLD_WIDTH,
                    height=RPG_WORLD_HEIGHT,
                    seed=seed,
                )
                result["dungeon"] = dungeon
                result["spawns"] = spawns
            except Exception as e:
                result["error"] = e
            finally:
                gen_done.set()

        thread = threading.Thread(target=_generate, daemon=True)
        thread.start()

        # 로딩 화면 애니메이션
        self._show_loading_screen(gen_done)

        thread.join(timeout=120)

        if "error" in result:
            raise result["error"]

        self.world_dungeon = result["dungeon"]
        self.spawn_points = result["spawns"]

        # 시작 위치 설정
        if not save_data:
            start = self.spawn_points.get("forgotten_forest", (RPG_WORLD_WIDTH // 6, RPG_WORLD_HEIGHT // 4))
            self.player_x, self.player_y = start

        self.world_dungeon.player_start = (self.player_x, self.player_y)
        self.world_dungeon._world_seed = self.world_seed  # 게임메뉴 저장용 시드 기록
        logger.info(f"월드맵 생성 완료. 플레이어 위치: ({self.player_x}, {self.player_y})")

    def _show_loading_screen(self, done_event):
        """차원 생성 로딩 화면 애니메이션"""
        import math

        messages = [
            "차원의 잔향을 감지하고 있습니다...",
            "잊혀진 숲의 지형을 구성합니다...",
            "황혼의 사막에 모래바람이 불어옵니다...",
            "심연의 동굴 깊은 곳에서 소리가 들립니다...",
            "폭풍의 고원에 바람이 모여듭니다...",
            "영원의 빙원에 시간이 멈춥니다...",
            "전쟁의 대지에 기억이 남아있습니다...",
            "별빛의 왕좌가 빛나기 시작합니다...",
            "마을과 도로를 연결합니다...",
            "차원의 문이 열리고 있습니다...",
        ]

        frame = 0
        msg_idx = 0
        msg_timer = 0.0
        last_time = time.time()

        spinner_chars = "◐◓◑◒"

        while not done_event.is_set():
            now = time.time()
            dt = now - last_time
            last_time = now
            frame += 1
            msg_timer += dt

            # 2초마다 메시지 변경
            if msg_timer > 2.0:
                msg_timer = 0.0
                msg_idx = (msg_idx + 1) % len(messages)

            self.console.clear()
            w = self.console.width
            h = self.console.height

            # 배경 별빛
            import random as _rng
            _rng.seed(frame // 3)
            for _ in range(30):
                sx = _rng.randint(0, w - 1)
                sy = _rng.randint(0, h - 1)
                brt = _rng.randint(30, 120)
                self.console.print(sx, sy, _rng.choice("·.+"), fg=(brt, brt, int(brt * 1.3)))

            # 타이틀
            title = "⟡ 차원을 생성하고 있습니다 ⟡"
            tx = (w - len(title)) // 2
            ty = h // 2 - 4
            pulse = int(180 + 75 * math.sin(frame * 0.1))
            self.console.print(tx, ty, title, fg=(pulse, pulse, 255))

            # 스피너
            spinner = spinner_chars[frame % len(spinner_chars)]
            self.console.print(w // 2, ty + 2, spinner, fg=(200, 200, 255))

            # 진행 메시지
            msg = messages[msg_idx]
            mx = (w - len(msg)) // 2
            self.console.print(mx, ty + 4, msg, fg=(150, 180, 220))

            # 프로그레스 바 (애니메이션)
            bar_w = 30
            bx = (w - bar_w) // 2
            by = ty + 6
            fill = int((math.sin(frame * 0.05) * 0.5 + 0.5) * bar_w)
            bar = "█" * fill + "░" * (bar_w - fill)
            self.console.print(bx, by, bar, fg=(100, 140, 200))

            # 안내
            hint = "잠시만 기다려주세요..."
            hx = (w - len(hint)) // 2
            self.console.print(hx, ty + 8, hint, fg=(100, 100, 140))

            self.context.present(self.console)
            time.sleep(0.033)  # ~30 FPS

    def _setup_town_facilities(self):
        """마을 시설을 MAX 레벨로 초기화"""
        try:
            from src.town.town_manager import TownManager, FacilityType

            self.town_manager = TownManager()

            # 모든 시설을 MAX 레벨(4)로 설정
            max_level = 4
            for facility_type in FacilityType:
                if facility_type in self.town_manager.facilities:
                    self.town_manager.facilities[facility_type].level = max_level

            logger.info("마을 시설 MAX 레벨 초기화 완료")
        except Exception as e:
            logger.warning(f"마을 시설 초기화 실패 (게임 진행에 영향 없음): {e}")

    # ── 메인 게임 루프 ──────────────────────────────────────

    def _main_game_loop(self) -> RPGModeResult:
        """
        RPG 모드 메인 게임 루프.
        탐험 → 전투/건물 상호작용 → 탐험 반복.
        """
        from src.world.exploration import ExplorationSystem, ExplorationEvent
        from src.ui.world_ui import run_exploration
        from src.equipment.inventory import Inventory

        # 인벤토리 (세이브에서 복원 - Inventory.from_dict 우선 사용)
        inventory = Inventory(party=self.party)
        if hasattr(self, '_saved_inventory_full') and self._saved_inventory_full:
            # 새 방식: Inventory.to_dict()/from_dict() (골드 포함)
            try:
                inventory = Inventory.from_dict(self._saved_inventory_full, party=self.party)
                logger.info(f"RPG 인벤토리 복원 (from_dict): {len(inventory.slots)}개 슬롯, {inventory.gold}G")
            except Exception as e:
                logger.warning(f"인벤토리 from_dict 복원 실패, 레거시 방식 시도: {e}")
                inventory = Inventory(party=self.party)
                self._saved_inventory_full = None
        if not hasattr(self, '_saved_inventory_full') or not self._saved_inventory_full:
            # 하위 호환: 이전 세이브 포맷 (inventory_items + inventory_gold)
            if hasattr(self, '_saved_inventory_items') and self._saved_inventory_items:
                from src.persistence.save_system import deserialize_item
                for item_data in self._saved_inventory_items:
                    try:
                        item = deserialize_item(item_data)
                        inventory.add_item(item)
                    except Exception as e:
                        logger.warning(f"인벤토리 아이템 복원 실패: {e}")
                logger.info(f"RPG 인벤토리 복원 (레거시): {len(inventory.slots)}개 슬롯")
            # 골드 복원 (레거시)
            if hasattr(self, '_saved_inventory_gold') and self._saved_inventory_gold:
                inventory.gold = self._saved_inventory_gold
                logger.info(f"RPG 골드 복원: {inventory.gold}G")
        # 복원 후 클리어
        self._saved_inventory_full = None
        self._saved_inventory_items = []
        self._saved_inventory_gold = 0

        # 마을 창고 복원 (기존 MAX 레벨 시설 유지하면서 창고 데이터만 복원)
        if hasattr(self, '_saved_town_data') and self._saved_town_data:
            try:
                if self.town_manager:
                    # MAX 레벨 시설을 유지하면서 창고/허브 데이터만 복원
                    hub_storage = self._saved_town_data.get("hub_storage", [])
                    storage_inv = self._saved_town_data.get("storage_inventory", [])
                    if isinstance(hub_storage, list):
                        self.town_manager.hub_storage = hub_storage.copy()
                    if isinstance(storage_inv, list):
                        self.town_manager.storage_inventory = storage_inv.copy()
                    logger.info(f"RPG 마을 창고 복원: 허브={len(self.town_manager.hub_storage)}개, 창고={len(self.town_manager.storage_inventory)}개")
                else:
                    from src.town.town_manager import TownManager
                    self.town_manager = TownManager.from_dict(self._saved_town_data)
            except Exception as e:
                logger.warning(f"마을 창고 복원 실패, 기본 초기화 사용: {e}")
            self._saved_town_data = None

        # RPG 사이드 퀘스트를 퀘스트 매니저에 주입
        self._inject_rpg_side_quests()

        # 자동 저장 (시작 시 - 복원된 인벤토리 포함)
        self._auto_save(inventory)

        # 첫 스폰 시 릴리 마을 진입 대사 (RPG 모드는 항상 마을에서 시작)
        if not self._pending_lily_message:
            lily_line = self.lily_dialogue.get_town_enter_line(
                self.progress.current_chapter, self.progress.lily_affinity
            )
            if lily_line:
                self._pending_lily_message = f'릴리: "{lily_line}"'

        # 세이브 복원 시: 이미 진행된 챕터는 다시 표시하지 않음
        for ch in self.chapter_system.chapters:
            if ch.chapter_number <= self.progress.current_chapter:
                self._shown_chapter_events.add(ch.chapter_id)

        # 첫 스폰 시 챕터 트리거 (자동 해금 챕터 이벤트 즉시 표시)
        initial_chapters = self.chapter_system.check_chapter_triggers(self.progress)
        for ch in initial_chapters:
            if ch.chapter_id in self._shown_chapter_events:
                continue
            self._shown_chapter_events.add(ch.chapter_id)
            self.progress.current_chapter = max(
                self.progress.current_chapter, ch.chapter_number
            )
            logger.info(f"초기 챕터 해금: {ch.title}")
            self._show_enhanced_chapter_event(ch)

        # RPG 모드 활성화 플래그 세팅 (경험치 계수 등 모드별 분기에 사용)
        from src.core.config import get_config
        get_config().set("rpg_mode.enabled", True)

        # ExplorationSystem 영속화: 루프 밖에서 None으로 초기화하여 지역 변경 시에만 재생성
        exploration = None
        _last_region_id = None  # 마지막으로 ExplorationSystem을 생성한 지역 ID

        try:
            while True:
                # 현재 위치의 지역 확인
                current_region_id = _get_region_for_point(
                    self.player_x, self.player_y,
                    RPG_WORLD_WIDTH, RPG_WORLD_HEIGHT
                )
                region = REGION_MAP.get(current_region_id)
                if region:
                    self.progress.current_region = current_region_id

                # 동적 레벨 스케일링: 파티 평균 레벨 기반으로 적 레벨 계산
                enemy_level = 1
                if region:
                    # 파티 평균 레벨 계산
                    avg_party_level = (
                        sum(getattr(c, 'level', 1) for c in self.party) / max(1, len(self.party))
                        if self.party else 1
                    )
                    if avg_party_level >= 1:
                        # 파티 평균 레벨 ±2 범위 내에서 스폰, 지역 level_min/level_max로 클램핑
                        import random as _random
                        min_enemy_level = max(region.level_min, int(avg_party_level) - 2)
                        max_enemy_level = min(region.level_max, int(avg_party_level) + 2)
                        # min이 max보다 클 경우 보정 (지역 범위 초과 시)
                        if min_enemy_level > max_enemy_level:
                            min_enemy_level = max_enemy_level
                        enemy_level = _random.randint(min_enemy_level, max_enemy_level)
                    else:
                        # fallback: 거리 기반 로직 (파티 레벨 정보 없을 때)
                        from src.rpg_mode.rpg_world_generator import _REGION_CENTERS
                        cx_ratio, cy_ratio = _REGION_CENTERS.get(current_region_id, (0.5, 0.5))
                        cx = int(cx_ratio * RPG_WORLD_WIDTH)
                        cy = int(cy_ratio * RPG_WORLD_HEIGHT)
                        dist = ((self.player_x - cx) ** 2 + (self.player_y - cy) ** 2) ** 0.5
                        max_dist = RPG_WORLD_WIDTH * 0.2  # 지역 반경 추정
                        progress = min(1.0, dist / max(1, max_dist))
                        enemy_level = get_enemy_level_for_region(region, progress)

                # 플레이어 시작 위치를 던전에 미리 설정 (적 스폰 시 올바른 위치 기준 사용)
                self.world_dungeon.player_start = (self.player_x, self.player_y)

                # ExplorationSystem 영속화:
                # - 최초 생성이거나 지역이 바뀌었을 때만 새로 생성
                # - 그 외에는 기존 exploration을 재사용 (explored_tiles, 남은 적 보존)
                region_changed = (current_region_id != _last_region_id)
                if exploration is None or region_changed:
                    exploration = ExplorationSystem(
                        dungeon=self.world_dungeon,
                        party=self.party,
                        floor_number=1,  # 오픈월드는 층 개념 없음
                        inventory=inventory,
                    )
                    _last_region_id = current_region_id
                    # 새로 생성한 적 엔티티에 레벨 설정
                    if hasattr(exploration, 'enemies'):
                        for enemy in exploration.enemies:
                            enemy.level = enemy_level
                else:
                    # 기존 exploration 재사용 시: 플레이어 위치와 파티 동기화
                    if hasattr(exploration, 'player'):
                        exploration.player.x = self.player_x
                        exploration.player.y = self.player_y
                        exploration.player.party = self.party

                # 랜덤 이벤트 on_step에서 region 필터링에 사용할 지역 ID 주입
                exploration._current_region_id = current_region_id

                # TownManager 연결
                if self.town_manager:
                    exploration.town_manager = self.town_manager

                # RPG 안내 메시지 설정
                exploration.initial_messages = self._get_rpg_guide_messages(region)

                # 릴리 대사 매니저 + 목표 추적기를 exploration에 전달
                exploration.lily_dialogue = self.lily_dialogue
                exploration.objective_tracker = self.objective_tracker
                exploration.rpg_progress = self.progress

                # 네비게이션 데이터 전달 (마을 좌표, 현재 지역)
                exploration.nav_spawn_points = self.spawn_points
                exploration.nav_current_region = current_region_id

                # 실제 시간 기반 밤/낮 판정 (RPG 모드 한정)
                hour = datetime.now().hour
                exploration.is_night = (hour >= 19 or hour < 6)
                if exploration.is_night:
                    time_label = "밤" if hour >= 21 or hour < 4 else ("저녁" if hour >= 19 else "새벽")
                else:
                    time_label = "아침" if hour < 10 else ("낮" if hour < 17 else "오후")
                exploration.time_label = time_label

                # 목표 HUD 업데이트
                self.objective_tracker.update(self.progress)

                # 이전 루프에서 저장된 릴리 메시지 주입
                if self._pending_lily_message:
                    exploration.initial_messages.append(self._pending_lily_message)
                    self._pending_lily_message = None

                # 대기 중인 챕터 이벤트 표시 (맵 복귀 후)
                if hasattr(self, '_pending_chapter_events') and self._pending_chapter_events:
                    pending = self._pending_chapter_events[:]
                    self._pending_chapter_events = []
                    for ch in pending:
                        self._show_enhanced_chapter_event(ch)

                # 릴리 마을 진입 대사
                is_town = hasattr(exploration, 'is_town') and exploration.is_town
                if is_town:
                    lily_line = self.lily_dialogue.get_town_enter_line(
                        self.progress.current_chapter, self.progress.lily_affinity
                    )
                    if lily_line:
                        exploration.initial_messages.append(f'릴리: "{lily_line}"')
                else:
                    # 지역 진입 대사
                    if current_region_id:
                        lily_line = self.lily_dialogue.get_region_line(
                            current_region_id, self.progress.current_chapter, self.progress.lily_affinity
                        )
                        if lily_line:
                            exploration.initial_messages.append(f'릴리: "{lily_line}"')

                # 탐험 실행
                result = run_exploration(
                    console=self.console,
                    context=self.context,
                    exploration=exploration,
                    inventory=inventory,
                    party=self.party,
                    play_bgm_on_start=True,
                )

                # 플레이어 위치 업데이트
                if hasattr(exploration, 'player'):
                    self.player_x = exploration.player.x
                    self.player_y = exploration.player.y

                # 결과 처리
                result_type = result[0] if isinstance(result, tuple) else result
                result_data = result[1] if isinstance(result, tuple) and len(result) > 1 else {}

                if result_type in ("quit", "main_menu"):
                    self._auto_save(inventory)
                    return RPGModeResult.RETURN_TO_MENU

                elif result_type == "combat":
                    # 전투 전 릴리 대사
                    ch = self.progress.current_chapter
                    aff = self.progress.lily_affinity

                    # 보스 전투인지 확인
                    is_boss = isinstance(result_data, dict) and result_data.get("is_boss", False)
                    if is_boss:
                        lily_line = self.lily_dialogue.get_boss_encounter_line(ch, aff)
                        # 보스 전 대화 씬
                        boss_region = result_data.get("region_id", current_region_id)
                        pre_scenes = self.lily_dialogue.get_boss_pre_line(boss_region)
                        if pre_scenes:
                            self._show_lily_scenes(pre_scenes)
                    else:
                        lily_line = self.lily_dialogue.get_combat_start_line(ch, aff)

                    # 전투 처리
                    combat_result = self._handle_combat(
                        result_data, inventory, enemy_level,
                        lily_start_line=lily_line,
                    )

                    # 전투 종료 직후 호감도 캐시 갱신 (combat manager 해제 전)
                    self._cache_affinity_data()

                    # ExplorationSystem 영속화: 전투에 참여한 적을 exploration에서 제거
                    # 승리/패배/도주 모두 전투에 참여한 적은 맵에서 사라져야 함
                    if exploration is not None and isinstance(result_data, dict):
                        combat_enemies = result_data.get("enemies", [])
                        if combat_enemies:
                            participated_ids = {getattr(e, 'id', None) for e in combat_enemies if e is not None}
                            # id 매칭으로 처치된 적 제거 (승리 시에만 제거, 도주 시에는 잔류)
                            if combat_result not in ("fled", "game_over"):
                                to_remove = [
                                    e for e in list(exploration.enemies)
                                    if getattr(e, 'id', None) in participated_ids
                                ]
                                for e in to_remove:
                                    exploration.remove_enemy(e)
                                if to_remove:
                                    logger.info(f"전투 후 맵 적 제거: {len(to_remove)}마리 (exploration 재사용)")
                        # 전투 후 면역 시간 설정 (즉각 재조우 방지)
                        exploration.set_post_combat_immunity(2.0)

                    if combat_result == "game_over":
                        # 패배 시 릴리 부활 대사
                        respawn_line = self.lily_dialogue.get_respawn_line(ch, aff)
                        self._respawn_at_town()
                        if respawn_line:
                            self._pending_lily_message = f'릴리: "{respawn_line}"'
                        self.lily_dialogue._victory_count = 0  # 연승 리셋
                        self._auto_save(inventory)
                        # 리스폰 후 지역이 바뀌므로 exploration 초기화
                        exploration = None
                        _last_region_id = None
                        continue
                    elif combat_result == "quit":
                        self._auto_save(inventory)
                        return RPGModeResult.RETURN_TO_MENU
                    elif combat_result == "fled":
                        flee_line = self.lily_dialogue.get_flee_line(ch, aff)
                        if flee_line:
                            self._pending_lily_message = f'릴리: "{flee_line}"'
                        self.lily_dialogue._victory_count = 0
                    else:
                        # 승리
                        self.progress.battles_won += 1
                        victory_line = self.lily_dialogue.get_combat_victory_line(ch, aff)
                        if victory_line:
                            self._pending_lily_message = f'릴리: "{victory_line}"'
                        self.lily_dialogue._victory_count += 1
                        if self.lily_dialogue._victory_count >= 3:
                            consec_line = self.lily_dialogue.get_consecutive_victory_line(ch, aff)
                            if consec_line:
                                self._pending_lily_message = f'릴리: "{consec_line}"'

                        # 보스 승리 시 후 대화 씬
                        if is_boss:
                            post_scenes = self.lily_dialogue.get_boss_post_line(
                                result_data.get("region_id", current_region_id)
                            )
                            if post_scenes:
                                self._show_lily_scenes(post_scenes)

                    self._auto_save(inventory)

                elif result_type == "building_interaction":
                    # 마을 건물 상호작용
                    self._handle_building_interaction(result_data, inventory)

                elif result_type in ("floor_up", "floor_down"):
                    # 오픈월드에서는 층 이동 없음 (무시)
                    pass

                else:
                    # 기타 (예: story_boss_combat 등)
                    self._auto_save(inventory)

                # 챕터 트리거 체크
                new_chapters = self.chapter_system.check_chapter_triggers(self.progress)
                # 챕터 이벤트를 대기열에 저장 (맵 복귀 후 표시)
                for ch in new_chapters:
                    # 이미 표시한 챕터는 건너뛰기 (중복 방지)
                    if ch.chapter_id in self._shown_chapter_events:
                        continue
                    self._shown_chapter_events.add(ch.chapter_id)

                    self.progress.current_chapter = max(
                        self.progress.current_chapter, ch.chapter_number
                    )
                    logger.info(f"새 챕터 해금: {ch.title}")

                    # 챕터 이벤트를 대기열에 추가 (맵 복귀 후 표시)
                    if not hasattr(self, '_pending_chapter_events'):
                        self._pending_chapter_events = []
                    self._pending_chapter_events.append(ch)
                    # 새 지역 해금 대사
                    region_line = self.lily_dialogue.get_new_region_line(
                        self.progress.current_chapter, self.progress.lily_affinity
                    )
                    if region_line:
                        self._pending_lily_message = f'릴리: "{region_line}"'

        except Exception as e:
            logger.error(f"RPG 모드 게임 루프 오류: {e}", exc_info=True)
            self._auto_save(inventory)
            return RPGModeResult.RETURN_TO_MENU
        finally:
            # RPG 모드 종료 시 플래그 해제
            get_config().set("rpg_mode.enabled", False)

    # ── 전투 처리 ──────────────────────────────────────────

    def _handle_combat(self, combat_data: Any, inventory, enemy_level: int,
                        lily_start_line: str = None) -> str:
        """
        전투를 실행하고 결과를 반환한다.

        Returns:
            "victory", "game_over", "fled", "quit"
        """
        from src.ui.combat_ui import run_combat
        from src.combat.combat_manager import CombatManager, CombatState
        from src.world.enemy_generator import EnemyGenerator

        try:
            # 적 생성 - 필드 조우 정보 활용
            enemy_gen = EnemyGenerator()
            num_enemies = None
            boss_battle = False
            if isinstance(combat_data, dict):
                num_enemies = combat_data.get("num_enemies", None)
                boss_battle = combat_data.get("is_boss", False)
                # 필드 적 레벨이 있으면 우선 사용
                field_enemy_level = combat_data.get("enemy_level", None)
                if field_enemy_level is not None:
                    enemy_level = field_enemy_level
            enemies = enemy_gen.generate_enemies(
                floor_number=max(1, enemy_level),
                num_enemies=num_enemies,
                boss_battle=boss_battle,
            )

            # 전투 실행 (CombatManager는 run_combat 내부에서 생성됨)
            combat_result = run_combat(
                console=self.console,
                context=self.context,
                party=self.party,
                enemies=enemies,
                inventory=inventory,
                lily_start_message=f'릴리: "{lily_start_line}"' if lily_start_line else None,
                lily_dialogue=self.lily_dialogue,
                rpg_chapter=self.progress.current_chapter,
                rpg_affinity=self.progress.lily_affinity,
            )

            # 결과 해석
            if isinstance(combat_result, tuple):
                state = combat_result[0]
            else:
                state = combat_result

            if state == CombatState.VICTORY:
                logger.info("전투 승리")
                # 보상 계산 및 전리품 UI 표시
                try:
                    from src.combat.experience_system import (
                        RewardCalculator, distribute_party_experience,
                    )
                    from src.ui.reward_ui import show_reward_screen

                    rewards = RewardCalculator.calculate_combat_rewards(
                        enemies, enemy_level, is_boss_fight=boss_battle,
                    )
                    level_up_info = distribute_party_experience(
                        self.party, rewards["experience"],
                    )
                    show_reward_screen(
                        self.console, self.context, rewards, level_up_info,
                        inventory=inventory,
                    )
                    if inventory:
                        inventory.add_gold(rewards.get("gold", 0))
                except Exception as e:
                    logger.warning(f"RPG 전투 보상 처리 오류: {e}")
                return "victory"
            elif state == CombatState.DEFEAT:
                logger.info("전투 패배 - 마을에서 부활")
                return "game_over"
            elif state == CombatState.FLED:
                logger.info("전투 도주")
                return "fled"
            else:
                return "quit"

        except Exception as e:
            logger.error(f"전투 처리 오류: {e}", exc_info=True)
            return "quit"

    def _respawn_at_town(self):
        """
        패배 시 가장 가까운 마을 캠프파이어에서 부활.
        파티 HP를 절반으로 복구하고 세이브는 유지된다.
        """
        # 현재 지역의 마을 스폰 포인트 찾기
        current_region = self.progress.current_region
        respawn_point = self.spawn_points.get(
            current_region,
            self.spawn_points.get("forgotten_forest", (RPG_WORLD_WIDTH // 6, RPG_WORLD_HEIGHT // 4))
        )
        self.player_x, self.player_y = respawn_point

        # 파티 HP/MP 절반 회복
        for member in self.party:
            member.current_hp = max(1, member.max_hp // 2)
            member.current_mp = max(0, member.max_mp // 2)
            member.wound = max(0, getattr(member, 'wound', 0) - 1)

        region = REGION_MAP.get(current_region)
        town_name = region.town_name if region else "마을"
        logger.info(f"마을 부활: {town_name} ({self.player_x}, {self.player_y})")

    # ── 마을 건물 상호작용 ──────────────────────────────────

    def _handle_building_interaction(self, data: Any, inventory):
        """마을 건물 상호작용 처리"""
        if not isinstance(data, dict):
            return

        building_type = data.get("building_type", "")
        logger.info(f"마을 건물 상호작용: {building_type}")

        try:
            ch = self.progress.current_chapter
            aff = self.progress.lily_affinity

            if building_type == "shop":
                shop_line = self.lily_dialogue.get_shop_line(ch, aff)
                if shop_line:
                    self._pending_lily_message = f'릴리: "{shop_line}"'
            elif building_type == "campfire":
                rest_line = self.lily_dialogue.get_rest_line(ch, aff)
                if rest_line:
                    self._pending_lily_message = f'릴리: "{rest_line}"'
            elif building_type == "inn":
                rest_line = self.lily_dialogue.get_rest_line(ch, aff)
                if rest_line:
                    self._pending_lily_message = f'릴리: "{rest_line}"'
            elif building_type == "kitchen":
                cook_line = self.lily_dialogue.get_cooking_line(ch, aff)
                if cook_line:
                    self._pending_lily_message = f'릴리: "{cook_line}"'
            elif building_type == "alchemy_lab":
                alch_line = self.lily_dialogue.get_alchemy_line(ch, aff)
                if alch_line:
                    self._pending_lily_message = f'릴리: "{alch_line}"'

            if building_type == "kitchen":
                self._open_kitchen(inventory)
            elif building_type == "blacksmith":
                self._open_blacksmith(inventory)
            elif building_type == "alchemy_lab":
                self._open_alchemy(inventory)
            elif building_type == "storage_building":
                self._open_storage(inventory)
            elif building_type == "quest_board":
                self._open_quest_board(inventory)
            elif building_type == "shop":
                self._open_shop(inventory)
            elif building_type == "inn":
                self._open_inn()
            elif building_type == "guild_hall":
                self._open_guild_hall()
            elif building_type == "fountain":
                self._handle_fountain()
            elif building_type == "campfire":
                self._handle_campfire(inventory)
            elif building_type == "healing_spring":
                self._handle_healing_spring()
        except Exception as e:
            logger.error(f"건물 상호작용 오류 ({building_type}): {e}", exc_info=True)

    def _open_kitchen(self, inventory):
        """주방 - 요리 UI"""
        try:
            from src.ui.cooking_ui import run_cooking_ui
            run_cooking_ui(self.console, self.context, inventory, self.party)
        except Exception as e:
            logger.error(f"주방 열기 실패: {e}")

    def _open_blacksmith(self, inventory):
        """대장간 - 장비 강화/수리"""
        try:
            from src.ui.shop_ui import run_shop
            run_shop(self.console, self.context, inventory, self.party, shop_type="blacksmith")
        except Exception as e:
            logger.error(f"대장간 열기 실패: {e}")

    def _open_alchemy(self, inventory):
        """연금술 실험실 - 포션/폭탄 제작"""
        try:
            from src.ui.alchemy_ui import run_alchemy_ui
            run_alchemy_ui(self.console, self.context, inventory, self.party)
        except Exception as e:
            logger.error(f"연금술 실험실 열기 실패: {e}")

    def _open_storage(self, inventory):
        """창고 - 아이템 보관"""
        try:
            from src.ui.storage_ui import run_storage_ui
            if self.town_manager:
                run_storage_ui(self.console, self.context, inventory, self.town_manager)
            else:
                logger.warning("TownManager 없음 - 창고 사용 불가")
        except Exception as e:
            logger.error(f"창고 열기 실패: {e}")

    def _open_quest_board(self, inventory=None):
        """퀘스트 게시판"""
        try:
            from src.ui.quest_board_ui import open_quest_board
            player_level = self.party[0].level if self.party else 1
            open_quest_board(
                self.console, self.context,
                quest_manager=None,  # 전역 매니저 자동 사용
                player_level=player_level,
                player=self.party[0] if self.party else None,
                current_floor=0,
                inventory=inventory
            )
        except Exception as e:
            logger.error(f"퀘스트 게시판 열기 실패: {e}")

    def _open_shop(self, inventory):
        """잡화점"""
        try:
            from src.ui.gold_shop_ui import run_gold_shop
            run_gold_shop(self.console, self.context, inventory, self.party)
        except Exception as e:
            logger.error(f"잡화점 열기 실패: {e}")

    def _open_inn(self):
        """여관 - 완전 회복"""
        try:
            from src.ui.rest_ui import run_rest
            run_rest(self.console, self.context, self.party)
        except Exception as e:
            logger.error(f"여관 열기 실패: {e}")

    def _open_guild_hall(self):
        """모험가 길드 - 정보/NPC 대화"""
        try:
            from src.ui.npc_dialog_ui import run_npc_dialog
            # 길드 마스터 NPC 대화
            region = REGION_MAP.get(self.progress.current_region)
            region_name = region.name if region else "알 수 없는 지역"
            run_npc_dialog(
                self.console, self.context,
                npc_name="길드 마스터",
                dialog_lines=[
                    f"여기는 {region_name}의 모험가 길드입니다.",
                    "퀘스트 게시판에서 의뢰를 확인해 보세요.",
                    f"현재 챕터: {self.progress.current_chapter}/10",
                ],
            )
        except Exception as e:
            logger.error(f"길드 열기 실패: {e}")

    def _handle_fountain(self):
        """분수대 - HP/MP 소량 회복"""
        from src.audio import play_sfx
        try:
            play_sfx("character", "hp_heal")
        except Exception:
            pass

        heal_amount = 30
        for member in self.party:
            if hasattr(member, 'heal'):
                member.heal(heal_amount)
            else:
                member.current_hp = min(member.max_hp, member.current_hp + heal_amount)
            member.current_mp = min(member.max_mp, member.current_mp + heal_amount // 2)
        logger.info(f"분수대: 파티 HP {heal_amount}, MP {heal_amount // 2} 회복")

    def _handle_campfire(self, inventory):
        """캠프파이어 - 세이브 + 소량 회복"""
        from src.audio import play_sfx
        try:
            play_sfx("character", "hp_heal")
        except Exception:
            pass

        # 소량 회복
        for member in self.party:
            heal = member.max_hp // 5
            member.current_hp = min(member.max_hp, member.current_hp + heal)
            member.current_mp = min(member.max_mp, member.current_mp + heal // 2)

        # 자동 저장
        self._auto_save(inventory)
        logger.info("캠프파이어: 회복 + 자동 저장 완료")

    def _handle_healing_spring(self):
        """치유의 샘 - 전원 HP 완전 회복"""
        from src.audio import play_sfx
        try:
            play_sfx("character", "hp_heal")
        except Exception:
            pass

        for member in self.party:
            member.current_hp = member.max_hp
        logger.info("치유의 샘: 파티 HP 완전 회복")

    # ── 감동 연출 ──────────────────────────────────────────

    def _show_prologue(self):
        """RPG 모드 첫 시작 시 프롤로그 연출"""
        import tcod.event
        try:
            self._play_emotional_bgm()
        except Exception:
            pass

        # 이전 화면에서 남은 입력 이벤트 플러시
        self._flush_input_events()

        prologue_pages = [
            [
                "[ 차원의 잔향 ]",
                "",
                "세피로스가 10만 번의 타임라인을 반복하며",
                "생겨난 또 다른 세계 ── '잔향 차원'.",
                "",
                "후회와 집념이 빚어낸 이 세계에서,",
                "시간의 잔향들이 새로운 생명으로 숨 쉬고 있다.",
            ],
            [
                "[ 각성 ]",
                "",
                "...어디지, 여기는.",
                "",
                "차원의 균열에 빨려 들어간 크리스가",
                "낯선 숲 한가운데서 눈을 뜬다.",
                "",
                "낯선 하늘, 낯선 공기.",
                "여기가 어디인지도 모른 채,",
                "크리스는 살아남기 위해 움직이기 시작한다.",
            ],
            [
                "[ 릴리와의 만남 ]",
                "",
                "의식을 잃은 크리스를 발견한 소녀 ── 릴리.",
                "",
                "\"드디어... 하늘에서 누군가가 왔어.\"",
                "",
                "그녀는 이 차원에서 태어난 존재로,",
                "'언젠가 하늘에서 누군가가 올 것'이라는",
                "예언을 기다려 왔다고 말한다.",
                "",
                "릴리는 크리스를 치료하고",
                "숲의 마을 '실바나'로 안내한다.",
            ],
            [
                "[ 여정의 시작 ]",
                "",
                f"크리스 ({self.party[0].character_class}) ── 주인공",
                f"릴리 ({self.party[1].character_class}) ── 이 차원의 소녀",
                f"{self.party[2].name} ({self.party[2].character_class}) ── 동료",
                f"{self.party[3].name} ({self.party[3].character_class}) ── 동료",
                "",
                "4명의 일행이 모였다.",
                "잔향 차원의 비밀을 밝히기 위한 여정이 시작된다.",
                "",
                "  [ 아무 키나 눌러 시작 ]",
            ],
        ]

        for page in prologue_pages:
            self.console.clear()
            start_y = max(1, (self.console.height - len(page)) // 2)
            for i, line in enumerate(page):
                x = max(0, (self.console.width - len(line)) // 2)
                fg = (255, 220, 100) if line.startswith("[") else (200, 200, 200)
                if line.startswith("\""):
                    fg = (150, 220, 255)
                elif line.startswith("  ["):
                    fg = (100, 100, 100)
                self.console.print(x, start_y + i, line, fg=fg)
            self.context.present(self.console)

            # 입력 버퍼 플러시 + 최소 대기 (페이지 스킵 방지)
            self._flush_input_events()
            time.sleep(0.4)
            self._flush_input_events()

            # 키 입력 대기
            while True:
                for action, event in iter_game_input():
                    action = action or _rpg_pointer_action(event)
                    if action is not None:
                        break
                    elif event and isinstance(event, tcod.event.KeyDown):
                        break
                else:
                    continue
                break

        # 프롤로그 완료 (current_chapter는 0으로 유지 → _main_game_loop 진입 시
        # check_chapter_triggers가 챕터 1을 자동 해금하면서 챕터 이벤트 창 표시)
        logger.info("프롤로그 완료")

    def _cache_affinity_data(self):
        """전투 종료 후 호감도 데이터를 모듈 캐시에 보존"""
        try:
            from src.combat.combat_manager import get_combat_manager
            cm = get_combat_manager()
            if cm and cm.affinity_manager:
                import src.persistence.save_system as save_module
                save_module._last_loaded_affinity_data = cm.affinity_manager.to_dict()
                logger.debug("호감도 데이터 캐시 갱신 완료")
        except Exception as e:
            logger.debug(f"호감도 캐시 갱신 실패: {e}")

    def _flush_input_events(self):
        """입력 이벤트 큐를 비운다 (페이지 스킵 방지)"""
        import tcod.event
        for _ in tcod.event.get():
            pass
        try:
            from src.ui.input_handler import unified_input_handler
            unified_input_handler.clear_input_state()
        except Exception:
            pass
        try:
            import pygame
            pygame.event.pump()
            pygame.event.clear()
        except Exception:
            pass

    def _play_emotional_bgm(self):
        """감동적인 순간에 pianosolo BGM 재생"""
        try:
            from src.audio import play_bgm
            play_bgm("emotional", loop=False, fade_in=True)
            logger.info("감동 BGM 재생: pianosolo")
        except Exception as e:
            logger.warning(f"감동 BGM 재생 실패: {e}")

    def _inject_rpg_side_quests(self):
        """RPG 사이드 퀘스트를 글로벌 QuestManager에 주입"""
        try:
            from src.quest.quest_manager import (
                get_quest_manager, Quest, QuestType, QuestDifficulty,
                QuestObjective, QuestReward,
            )

            qm = get_quest_manager()
            existing_ids = {q.quest_id for q in qm.available_quests}
            existing_ids |= {q.quest_id for q in qm.active_quests}
            existing_ids |= {q.quest_id for q in qm.completed_quests}

            # 타입 매핑
            type_map = {
                "kill": QuestType.BOUNTY_HUNT,
                "hunt": QuestType.BOSS_HUNT,
                "explore": QuestType.EXPLORATION,
                "fetch": QuestType.COLLECTION,
                "collect": QuestType.COLLECTION,
                "delivery": QuestType.DELIVERY,
                "escort": QuestType.DELIVERY,
                "investigate": QuestType.EXPLORATION,
                "craft": QuestType.ALCHEMY_QUEST,
                "cooking": QuestType.COOKING_QUEST,
                "alchemy": QuestType.ALCHEMY_QUEST,
                "defend": QuestType.SURVIVAL,
                "arena": QuestType.BOUNTY_HUNT,
                "rescue": QuestType.BOUNTY_HUNT,
                "puzzle": QuestType.EXPLORATION,
                "chain": QuestType.BOUNTY_HUNT,
            }

            injected = 0
            for region_id in self.progress.unlocked_regions:
                quests = self.chapter_system.get_quests_for_region(
                    region_id, self.progress
                )
                region_cfg = REGION_MAP.get(region_id)
                region_name = region_cfg.name if region_cfg else region_id

                for sq in quests:
                    if sq.quest_id in existing_ids:
                        continue

                    # 난이도 결정
                    if sq.level_req <= 5:
                        diff = QuestDifficulty.EASY
                    elif sq.level_req <= 15:
                        diff = QuestDifficulty.NORMAL
                    elif sq.level_req <= 30:
                        diff = QuestDifficulty.HARD
                    else:
                        diff = QuestDifficulty.LEGENDARY

                    # 목표 변환 (quest_type에 따라 의미 있는 target 생성)
                    objectives = []
                    qt = sq.quest_type
                    base_required = max(getattr(sq, 'collect_count', 0), 1)

                    if qt in ("kill", "arena", "rescue", "chain"):
                        # 전투 기반 - 각 objective를 전투 완료로 추적
                        for i, obj_text in enumerate(sq.objectives):
                            # 텍스트에서 숫자 추출 (예: "변이 늑대 8마리 처치" → 8)
                            import re
                            nums = re.findall(r'(\d+)\s*마리', obj_text)
                            req = int(nums[0]) if nums else base_required
                            objectives.append(QuestObjective(
                                description=obj_text,
                                target=f"rpg_quest:{sq.quest_id}:{i}",
                                current=0,
                                required=req,
                            ))
                    elif qt in ("fetch", "collect"):
                        # 수집 기반 - collect_count 적용
                        for i, obj_text in enumerate(sq.objectives):
                            import re
                            nums = re.findall(r'(\d+)\s*개', obj_text)
                            req = int(nums[0]) if nums else base_required
                            objectives.append(QuestObjective(
                                description=obj_text,
                                target=f"rpg_quest:{sq.quest_id}:{i}",
                                current=0,
                                required=req,
                            ))
                    else:
                        # 탐험/조사/호위/요리 등 - NPC/이벤트 기반 수동 완료
                        for i, obj_text in enumerate(sq.objectives):
                            objectives.append(QuestObjective(
                                description=obj_text,
                                target=f"rpg_quest:{sq.quest_id}:{i}",
                                current=0,
                                required=1,
                            ))

                    if not objectives:
                        objectives.append(QuestObjective(
                            description=sq.description,
                            target=f"rpg_quest:{sq.quest_id}:main",
                            current=0,
                            required=1,
                        ))

                    # 보상 파싱 (YAML rewards 문자열에서 추출, 없으면 레벨 기반 기본값)
                    reward_gold = sq.level_req * 30
                    reward_exp = sq.level_req * 50
                    reward_items = []
                    if hasattr(sq, 'rewards') and sq.rewards:
                        import re
                        gold_match = re.search(r'골드\s*(\d+)', sq.rewards)
                        exp_match = re.search(r'경험치\s*(\d+)', sq.rewards)
                        if gold_match:
                            reward_gold = int(gold_match.group(1))
                        if exp_match:
                            reward_exp = int(exp_match.group(1))
                        # 아이템 추출 (예: "회복 포션 x5" → item id)
                        item_matches = re.findall(r'([가-힣\s]+)\s*[xX×]?\s*(\d+)?', sq.rewards)
                        for item_name, _count in item_matches:
                            item_name = item_name.strip()
                            if item_name and item_name not in ('골드', '경험치'):
                                # 아이템 이름 → ID 변환은 향후 구현
                                pass

                    reward = QuestReward(
                        gold=reward_gold,
                        experience=reward_exp,
                        star_fragments=max(sq.level_req * 5, 10),
                    )

                    quest = Quest(
                        quest_id=sq.quest_id,
                        name=f"[{region_name}] {sq.title}",
                        description=sq.description,
                        quest_type=type_map.get(sq.quest_type, QuestType.BOUNTY_HUNT),
                        difficulty=diff,
                        objectives=objectives,
                        reward=reward,
                        hint=self._generate_quest_hint(sq.quest_type, sq.title, region_name),
                        quest_subtype=sq.quest_type,
                        region=region_id,
                    )
                    qm.available_quests.append(quest)
                    injected += 1

            if injected > 0:
                logger.info(f"RPG 사이드 퀘스트 {injected}개 주입 완료")

        except Exception as e:
            logger.warning(f"RPG 사이드 퀘스트 주입 실패: {e}")

    def _generate_quest_hint(self, quest_type: str, title: str, region_name: str) -> str:
        """퀘스트 타입별 힌트 텍스트 생성"""
        hints = {
            "kill": f"{region_name} 필드에서 몬스터를 처치하세요.",
            "hunt": f"{region_name} 필드에서 목표 몬스터를 사냥하세요.",
            "arena": f"{region_name} 필드에서 강적과 전투하세요.",
            "defend": f"{region_name} 필드의 적과 전투하여 방어하세요.",
            "investigate": f"{region_name} 마을 NPC에게 단서를 물어보거나, 동굴 입구·이정표를 조사하세요.",
            "explore": f"{region_name} 지역을 탐험하세요. 동굴 입구나 이정표를 확인해보세요.",
            "fetch": f"{region_name} 마을의 NPC에게 이야기를 들어보세요.",
            "collect": f"{region_name} 마을의 NPC에게 수집 의뢰를 진행하세요.",
            "delivery": f"{region_name} 마을의 NPC에게 배달 임무를 보고하세요.",
            "escort": f"{region_name} 지역의 동굴 입구 근처를 수색하거나 NPC에게 말을 걸어보세요.",
            "rescue": f"{region_name} 지역의 동굴 입구를 탐색하거나 NPC에게 정보를 얻으세요.",
            "puzzle": f"{region_name} 지역의 이정표를 살펴보거나 NPC에게 힌트를 얻으세요.",
            "cooking": f"{region_name} 마을의 주방 시설을 이용해 요리하세요.",
            "alchemy": f"{region_name} 마을의 연금술 실험실을 이용하세요.",
            "craft": f"{region_name} 마을의 대장간을 이용하세요.",
        }
        return hints.get(quest_type, f"{region_name} 지역을 탐험하며 목표를 달성하세요.")

    def _get_rpg_guide_messages(self, region) -> list:
        """현재 진행 상황에 맞는 RPG 안내 메시지 생성"""
        messages = []
        ch = self.progress.current_chapter

        if ch == 0:
            # 첫 시작 안내
            messages.append("== 차원의 여명 - RPG 모드 ==")
            messages.append("마을 시설: 상점($) 대장간(&) 연금술(%)")
            messages.append("  요리솥(K) 길드(G) 퀘스트(?)")
            messages.append("마을 밖 동굴(O)을 탐험하여 레벨을 올리세요.")
            messages.append("보스 던전을 클리어하면 다음 지역이 열립니다.")
            messages.append("Z키로 시설/동굴과 상호작용합니다.")
        else:
            # 진행 중 안내
            ch_title = self.chapter_system.get_chapter_title(ch)
            messages.append(f"현재 챕터: {ch} - {ch_title}")
            if region:
                messages.append(f"현재 지역: {region.name}")
                boss_defeated = region.region_id in self.progress.defeated_bosses
                if boss_defeated:
                    if region.next_region_id:
                        next_r = REGION_MAP.get(region.next_region_id)
                        next_name = next_r.name if next_r else region.next_region_id
                        messages.append(f"다음 지역 '{next_name}'으로 이동할 수 있습니다.")
                else:
                    messages.append("보스 던전을 찾아 클리어하세요!")

        return messages

    def _show_chapter_event(self, chapter):
        """챕터의 스토리 이벤트를 대화 UI로 표시"""
        try:
            from src.ui.npc_dialog_ui import run_npc_dialog

            # 챕터 제목 + 이벤트들을 대화로 표시
            lines = [f"[ 챕터 {chapter.chapter_number}: {chapter.title} ]", ""]
            lines.append(chapter.description.strip())
            lines.append("")

            for event in chapter.events:
                lines.append(f"-- {event.title} --")
                lines.append(event.description.strip())
                lines.append("")

            run_npc_dialog(
                self.console, self.context,
                npc_name=f"챕터 {chapter.chapter_number}",
                dialog_lines=lines,
            )
        except Exception as e:
            logger.warning(f"챕터 이벤트 표시 실패: {e}")

    def _show_enhanced_chapter_event(self, chapter):
        """강화된 챕터 이벤트 - 컷씬 YAML 지원"""
        try:
            from src.ui.npc_dialog_ui import run_npc_dialog, NPCChoice

            # 감동 BGM (핵심 챕터만)
            if chapter.chapter_number in (1, 6, 8, 10):
                self._play_emotional_bgm()

            # 컷씬 데이터 로드
            cutscene = self.lily_dialogue.get_chapter_cutscene(chapter.chapter_number)

            if cutscene:
                # BGM 전환
                bgm = cutscene.get("bgm")
                if bgm:
                    try:
                        from src.audio import play_bgm
                        play_bgm(bgm, loop=False, fade_in=True)
                    except Exception:
                        pass

                # 씬 순차 실행
                for scene in cutscene.get("scenes", []):
                    speaker = scene.get("speaker", "릴리")
                    lines = scene.get("lines", [])
                    effect = scene.get("effect")
                    choices = scene.get("choices")

                    if not lines:
                        continue

                    # 선택지 처리
                    npc_choices = None
                    if choices:
                        npc_choices = []
                        for c in choices:
                            def make_callback(aff_val):
                                def callback():
                                    self.progress.lily_affinity += aff_val
                                return callback
                            npc_choices.append(NPCChoice(
                                text=c["text"],
                                callback=make_callback(c.get("affinity", 0))
                            ))

                    run_npc_dialog(
                        self.console, self.context,
                        npc_name=speaker,
                        dialog_lines=lines,
                        choices=npc_choices,
                        effect=effect,
                    )
            else:
                # 컷씬 없으면 기존 방식
                self._show_chapter_event(chapter)

        except Exception as e:
            logger.warning(f"강화 챕터 이벤트 실패: {e}")
            self._show_chapter_event(chapter)

    def _show_lily_scenes(self, scenes: list):
        """릴리 대화 씬 리스트 표시 (보스 전후 등)"""
        try:
            from src.ui.npc_dialog_ui import run_npc_dialog

            for scene in scenes:
                speaker = scene.get("speaker", "릴리")
                lines = scene.get("lines", [])
                effect = scene.get("effect")

                if lines:
                    run_npc_dialog(
                        self.console, self.context,
                        npc_name=speaker,
                        dialog_lines=lines,
                        effect=effect,
                    )
        except Exception as e:
            logger.warning(f"릴리 씬 표시 실패: {e}")

    # ── 세이브 ──────────────────────────────────────────────

    def _auto_save(self, inventory=None):
        """RPG 모드 자동 저장 (패배해도 세이브 유지)"""
        from src.persistence.save_system import SaveSystem, serialize_party_member

        try:
            party_data = [serialize_party_member(m) for m in self.party]

            # 인벤토리 저장 (Inventory.to_dict() 사용 - 싱글모드와 동일)
            inventory_dict = {}
            inventory_data = []
            inventory_gold = 0
            if inventory:
                inventory_dict = inventory.to_dict()  # slots + gold + base_weight
                inventory_gold = getattr(inventory, 'gold', 0)
                # 하위 호환용 flat list (이전 세이브 포맷)
                from src.persistence.save_system import serialize_item
                for slot in inventory.slots:
                    if slot and slot.item:
                        inventory_data.append(serialize_item(slot.item))

            # 호감도 데이터 확보 (combat manager → 모듈 캐시 순)
            affinity_data = None
            try:
                from src.combat.combat_manager import get_combat_manager
                cm = get_combat_manager()
                if cm and cm.affinity_manager:
                    affinity_data = cm.affinity_manager.to_dict()
                else:
                    import src.persistence.save_system as save_module
                    affinity_data = getattr(save_module, '_last_loaded_affinity_data', None)
            except Exception:
                pass

            game_state = {
                "party": party_data,
                "floor_number": 1,
                "max_floor_reached": 1,
                "inventory_full": inventory_dict,  # 완전한 인벤토리 (to_dict)
                "inventory_items": inventory_data,  # 하위 호환용
                "inventory_gold": inventory_gold,
                # RPG 모드 전용
                "rpg_mode": True,
                "protagonist_name": self.protagonist_name,
                "companion_names": self.companion_names,
                "world_seed": self.world_seed,
                "player_x": self.player_x,
                "player_y": self.player_y,
                "rpg_progress": self.progress.to_dict(),
                "rpg_chapter": self.progress.current_chapter,
            }
            if affinity_data:
                game_state["affinity_data"] = affinity_data

            # 마을 창고 데이터 저장
            try:
                if hasattr(self, 'town_manager') and self.town_manager:
                    game_state["town_manager"] = self.town_manager.to_dict()
                    logger.debug(f"마을 창고 저장: {len(self.town_manager.storage_inventory)}개 아이템")
            except Exception as e:
                logger.warning(f"마을 창고 저장 실패: {e}")

            # 랜덤 이벤트 매니저 상태 저장 (시간당 제한 타이머 포함)
            try:
                from src.world.random_events import get_random_event_manager
                game_state["random_event_state"] = get_random_event_manager().to_dict()
            except Exception:
                pass

            save_system = SaveSystem()
            save_system.save_game("save_rpg", game_state, game_type="rpg")
            logger.info(f"RPG 자동 저장 (위치: {self.player_x},{self.player_y}, "
                        f"챕터: {self.progress.current_chapter})")
        except Exception as e:
            logger.error(f"RPG 자동 저장 실패: {e}")
