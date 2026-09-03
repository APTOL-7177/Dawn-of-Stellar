"""
챕터 실행 엔진
Dawn of Stellar - 별빛의 여명

개별 챕터를 Phase 단위로 순서 실행합니다.
Phase 타입: cutscene, dialogue, exploration, combat, ui_tutorial, job_select, shop, alchemy, anvil, inventory, save_load, party_setup, guild_hall, bomb_craft, boss_combat, difficulty_select
"""

import yaml
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum

import tcod.console
import tcod.event
from src.ui.input_handler import iter_game_input, poll_game_input, GameAction
from src.ui.pointer import PointerButton, PointerEventKind
from src.ui.visual_tokens import rgb

from src.core.logger import get_logger
from src.audio import play_bgm, play_sfx
from src.story_mode.story_mode_manager import (
    StoryModeProgress,
    CHAPTER_META,
    CHAPTER_ORDER,
)
from src.story_mode.inline_tutorial_overlay import (
    InlineTutorialOverlay,
    NPC_NAMES,
    NPC_COLORS,
)

logger = get_logger("story_mode")

DATA_DIR = Path("data/story_mode/chapters")


def _pointer_screen_action(event) -> GameAction | None:
    pointer_event = None
    try:
        from src.ui.input_handler import unified_input_handler
        pointer_event = unified_input_handler.process_pointer_event(event)
    except AttributeError:
        pointer_event = None
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


class PhaseType(Enum):
    """챕터 Phase 타입"""
    CUTSCENE = "cutscene"
    DIALOGUE = "dialogue"
    EXPLORATION = "exploration"
    COMBAT = "combat"
    UI_TUTORIAL = "ui_tutorial"
    JOB_SELECT = "job_select"
    SHOP = "shop"
    ALCHEMY = "alchemy"
    COOKING = "cooking"
    ANVIL = "anvil"
    INVENTORY = "inventory"
    SAVE_LOAD = "save_load"
    PARTY_SETUP = "party_setup"
    GUILD_HALL = "guild_hall"
    BOMB_CRAFT = "bomb_craft"
    BOSS_COMBAT = "boss_combat"
    DIFFICULTY_SELECT = "difficulty_select"


class ChapterRunner:
    """
    개별 챕터 실행 엔진

    YAML에서 챕터 데이터를 로드하고 Phase 순서대로 실행
    """

    def __init__(self, console: tcod.console.Console, context: tcod.context.Context):
        self.console = console
        self.context = context
        self.overlay = InlineTutorialOverlay()
        self._current_chapter_id: Optional[str] = None
        # StoryModeManager가 챕터 실행 직전 주입하는 진행 상태 스냅샷
        # (재클리어 시 챕터 보상 exactly-once 판단에 사용)
        self._last_progress: Optional[StoryModeProgress] = None

    def run_chapter(self, chapter_id: str, progress: StoryModeProgress) -> str:
        """
        챕터 실행

        Args:
            chapter_id: 챕터 ID (prologue, chapter_1, ...)
            progress: 현재 진행 상태

        Returns:
            "completed", "skipped", "quit"
        """
        # 챕터 데이터 로드
        self._current_chapter_id = chapter_id
        chapter_data = self._load_chapter_data(chapter_id)
        if not chapter_data:
            logger.warning(f"챕터 데이터 없음: {chapter_id}, 인라인 실행")
            chapter_data = self._generate_default_chapter(chapter_id)

        meta = CHAPTER_META.get(chapter_id, {})
        title = meta.get("title", chapter_id)
        subtitle = meta.get("subtitle", "")

        # BGM
        bgm = chapter_data.get("bgm", "main_menu")
        play_bgm(bgm)

        # 챕터 시작 화면
        result = self._show_chapter_title(title, subtitle)
        if result == "skip":
            return "skipped"
        elif result == "quit":
            return "quit"

        # Phase 순서 실행
        phases = chapter_data.get("phases", [])
        for i, phase in enumerate(phases):
            phase_type = phase.get("type", "dialogue")

            logger.info(f"[{chapter_id}] Phase {i+1}/{len(phases)}: {phase_type}")

            if phase_type == "cutscene":
                result = self._run_cutscene(phase)
            elif phase_type == "dialogue":
                result = self._run_dialogue(phase)
            elif phase_type == "combat":
                result = self._run_combat(phase, chapter_id)
            elif phase_type == "exploration":
                result = self._run_exploration(phase, chapter_id)
            elif phase_type == "ui_tutorial":
                result = self._run_ui_tutorial(phase)
            elif phase_type == "job_select":
                result = self._run_job_select(phase, progress)
            elif phase_type == "shop":
                result = self._run_shop(phase)
            elif phase_type == "alchemy":
                result = self._run_alchemy(phase)
            elif phase_type == "cooking":
                result = self._run_cooking(phase)
            elif phase_type == "anvil":
                result = self._run_anvil(phase)
            elif phase_type == "inventory":
                result = self._run_inventory(phase)
            elif phase_type == "save_load":
                result = self._run_save_load(phase)
            elif phase_type == "party_setup":
                result = self._run_party_setup_phase(phase)
            elif phase_type == "guild_hall":
                result = self._run_guild_hall(phase)
            elif phase_type == "bomb_craft":
                result = self._run_bomb_craft(phase)
            elif phase_type == "boss_combat":
                result = self._run_boss_combat(phase, chapter_id)
            elif phase_type == "difficulty_select":
                result = self._run_difficulty_select(phase)
            else:
                result = "continue"

            if result == "quit":
                return "quit"
            if result == "skip":
                return "skipped"

        # 챕터 완료 보상 표시 + 메타 진행 적용
        rewards = chapter_data.get("rewards", {})
        if rewards:
            self._show_rewards(rewards, meta)
            self._apply_chapter_rewards(chapter_id, rewards)

        # 챕터 완료 화면
        self._show_chapter_complete(title, subtitle)

        return "completed"

    def _load_chapter_data(self, chapter_id: str) -> Optional[Dict[str, Any]]:
        """YAML에서 챕터 데이터 로드"""
        path = DATA_DIR / f"{chapter_id}.yaml"
        try:
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"챕터 데이터 로드 실패 ({chapter_id}): {e}")
        return None

    def _generate_default_chapter(self, chapter_id: str) -> Dict[str, Any]:
        """30개 챕터 각각에 대한 풍부한 콘텐츠 자동 생성 (YAML 없을 때)"""
        meta = CHAPTER_META.get(chapter_id, {})
        npc = meta.get("npc_guide", "selena")
        act = meta.get("act", "act1")
        learning = meta.get("learning", "")
        title = meta.get("title", chapter_id)
        subtitle = meta.get("subtitle", "")

        # 챕터별 전용 콘텐츠 생성
        generator = CHAPTER_GENERATORS.get(chapter_id)
        if generator:
            return generator(meta)

        # 알 수 없는 챕터 → 범용
        return _gen_generic(meta, chapter_id)

    # =========================================================================
    # Phase 실행기들
    # =========================================================================

    def _run_cutscene(self, phase: dict) -> str:
        """컷신 Phase - StorySegment 기반 타이핑 효과"""
        from src.story.story_system import StorySegment
        from src.ui.npc_dialog_ui import render_story_sequence

        segments = []
        for seg_data in phase.get("segments", []):
            text = seg_data.get("text", "")
            pause = seg_data.get("pause", 1.0)
            color = seg_data.get("color", "white")
            segments.append(StorySegment(text=text, pause=pause, color=color))

        if segments:
            render_story_sequence(self.console, self.context, segments, logger)

        return "continue"

    def _run_dialogue(self, phase: dict) -> str:
        """대화 Phase - show_npc_dialog 활용 (타이핑 효과 + 연출)"""
        from src.ui.npc_dialog_ui import show_npc_dialog

        npc_id = phase.get("npc", "selena")
        npc_name = NPC_NAMES.get(npc_id, npc_id)
        lines = phase.get("lines", [])
        effects = phase.get("effects")
        choices_data = phase.get("choices")

        for i, line in enumerate(lines):
            effect = effects[i] if effects and i < len(effects) else None

            # 마지막 대사에 선택지가 있으면
            if i == len(lines) - 1 and choices_data:
                from src.ui.npc_dialog_ui import NPCChoice
                npc_choices = [NPCChoice(text=c["text"]) for c in choices_data]
                result = show_npc_dialog(
                    self.console, self.context,
                    npc_name, line, choices=npc_choices,
                    effect=effect, npc_id=npc_id
                )
                if result is None:
                    return "quit"
            else:
                result = show_npc_dialog(
                    self.console, self.context,
                    npc_name, line,
                    effect=effect, npc_id=npc_id
                )
                if result is None and i < len(lines) - 1:
                    # 중간에 취소 → 건너뛰기
                    pass

        return "continue"

    def _run_combat(self, phase: dict, chapter_id: str) -> str:
        """전투 Phase - 실제 게임 전투 시스템 사용"""
        try:
            from src.character.character import Character
            from src.world.enemy_generator import EnemyGenerator
            from src.ui.combat_ui import run_combat
            from src.combat.combat_manager import CombatState
            from src.equipment.inventory import Inventory

            # 1. 파티 생성 (실제 Character 객체)
            party = self._create_real_party(chapter_id)
            inventory = Inventory(base_weight=50.0, party=party)

            # 2. 적 생성 - 미리 정의된 적 데이터 우선 사용 (난이도 정규화 적용)
            enemies_data = phase.get("enemies", [])
            if enemies_data:
                is_boss = "boss" in chapter_id or "finale" in chapter_id
                enemies = self._create_story_enemies(enemies_data, is_boss_chapter=is_boss)
            else:
                floor = self._get_floor_for_chapter(chapter_id)
                boss_battle = "boss" in chapter_id
                enemies = EnemyGenerator.generate_enemies(floor, boss_battle=boss_battle)
                if boss_battle:
                    boss = EnemyGenerator.generate_boss(floor, is_floor_boss=True, boss_battle=True)
                    enemies.append(boss)

            # 3. 인벤토리 아이템 추가 (폭탄 전투 등)
            inventory_type = phase.get("inventory_type")
            if inventory_type:
                self._create_tutorial_inventory(inventory_type, inventory)

            # 4. 실제 전투 실행
            combat_result, is_game_over = run_combat(
                self.console, self.context,
                party=party, enemies=enemies,
                inventory=inventory,
            )

            # 5. 전투 후 대화
            victory_dialogue = phase.get("victory_dialogue")
            if victory_dialogue and combat_result == CombatState.VICTORY:
                self._run_dialogue(victory_dialogue)

            # 6. 패배 시 자동 부활 (스토리 모드 특성)
            if combat_result == CombatState.DEFEAT:
                for char in party:
                    char.current_hp = char.max_hp
                return "continue"

            return "continue" if combat_result == CombatState.VICTORY else "quit"

        except Exception as e:
            logger.warning(f"실제 전투 시스템 로드 실패, 폴백 사용: {e}")
            from src.story_mode.story_combat_controller import StoryCombatController
            controller = StoryCombatController(self.console, self.context, self.overlay)
            enemies_data = phase.get("enemies", [])
            combat_hints = phase.get("combat_hints", [])
            result = controller.run_scripted_combat(
                chapter_id=chapter_id,
                enemies_data=enemies_data,
                combat_hints=combat_hints,
            )
            victory_dialogue = phase.get("victory_dialogue")
            if victory_dialogue and result == "victory":
                self._run_dialogue(victory_dialogue)
            return "continue" if result != "quit" else "quit"

    def _run_exploration(self, phase: dict, chapter_id: str) -> str:
        """탐험 Phase - 커스텀 맵 또는 실제 탐험"""
        dungeon_type = phase.get("dungeon")

        # 커스텀 맵이 지정된 경우 StoryExplorationController 사용
        if dungeon_type:
            from src.story_mode.story_exploration_controller import StoryExplorationController
            controller = StoryExplorationController(
                self.console, self.context, self.overlay
            )
            result = controller.run_scripted_exploration(
                chapter_id=chapter_id, dungeon_type=dungeon_type
            )
            return "continue" if result != "quit" else "quit"

        # dungeon 미지정: 랜덤 맵 사용
        try:
            from src.world.dungeon_generator import DungeonGenerator
            from src.world.exploration import ExplorationSystem
            from src.ui.world_ui import run_exploration
            from src.equipment.inventory import Inventory

            party = self._create_real_party(chapter_id)
            inventory = Inventory(base_weight=5.0, party=party)

            floor = self._get_floor_for_chapter(chapter_id)
            generator = DungeonGenerator(width=60, height=30)
            dungeon = generator.generate(floor_number=floor)

            exploration = ExplorationSystem(dungeon, party, floor, inventory)
            result, data = run_exploration(
                self.console, self.context, exploration,
                inventory=inventory, party=party,
            )

            if result == "combat":
                from src.world.enemy_generator import EnemyGenerator
                from src.ui.combat_ui import run_combat
                from src.combat.combat_manager import CombatState

                num_enemies = data.get("num_enemies") if data else None
                combat_position = data.get("position") if data else None
                enemies = EnemyGenerator.generate_enemies(floor, num_enemies=num_enemies)

                combat_result, _ = run_combat(
                    self.console, self.context,
                    party=party, enemies=enemies,
                    inventory=inventory, dungeon=dungeon,
                    combat_position=combat_position,
                )

                if combat_result == CombatState.DEFEAT:
                    for char in party:
                        char.current_hp = char.max_hp

                return "continue"

            if result == "story_boss_combat":
                from src.world.enemy_generator import EnemyGenerator
                from src.ui.combat_ui import run_combat
                from src.combat.combat_manager import CombatState

                boss = EnemyGenerator.generate_boss(floor, is_floor_boss=True)
                enemies = EnemyGenerator.generate_enemies(floor, num_enemies=2)
                enemies.append(boss)

                combat_result, _ = run_combat(
                    self.console, self.context,
                    party=party, enemies=enemies,
                    inventory=inventory, dungeon=dungeon,
                )

                if combat_result == CombatState.DEFEAT:
                    for char in party:
                        char.current_hp = char.max_hp

                return "continue"

            return "continue" if result in ("floor_down", "floor_up", "main_menu") else "quit"

        except Exception as e:
            logger.warning(f"탐험 시스템 로드 실패: {e}")
            return "continue"

    def _run_ui_tutorial(self, phase: dict) -> str:
        """UI 튜토리얼 Phase - 장비/요리 등 UI 안내"""
        # 대화 형식으로 UI 설명
        npc_id = phase.get("npc", "selena")
        lines = phase.get("lines", ["이 기능을 살펴보겠습니다."])
        for line in lines:
            from src.ui.npc_dialog_ui import show_npc_dialog
            npc_name = NPC_NAMES.get(npc_id, npc_id)
            result = show_npc_dialog(self.console, self.context, npc_name, line)
            if result is None:
                pass  # 스킵해도 진행

        return "continue"

    def _run_job_select(self, phase: dict, progress: StoryModeProgress) -> str:
        """직업 선택 Phase"""
        # 기존 job_selection_ui 활용 시도
        try:
            from src.tutorial.job_selection_ui import show_job_selection
            selected = show_job_selection(self.console, self.context)
            if selected:
                progress.selected_job = selected
                logger.info(f"직업 선택: {selected}")
        except (ImportError, Exception) as e:
            logger.warning(f"직업 선택 UI 불러오기 실패, 기본 대화로 대체: {e}")
            from src.ui.npc_dialog_ui import show_npc_dialog, NPCChoice
            choices = [
                NPCChoice(text="전사 (근접 딜러)"),
                NPCChoice(text="기사 (탱커)"),
                NPCChoice(text="궁수 (만능형)"),
                NPCChoice(text="도적 (속도형)"),
                NPCChoice(text="마법사 (원거리 딜러)"),
                NPCChoice(text="원소술사 (속성 전문)"),
                NPCChoice(text="성직자 (힐러)"),
                NPCChoice(text="음유시인 (버퍼)"),
            ]
            job_map = {
                0: "warrior", 1: "knight", 2: "archer", 3: "rogue",
                4: "magician", 5: "elementalist", 6: "cleric", 7: "bard",
            }
            result = show_npc_dialog(
                self.console, self.context,
                "셀레나",
                "이제 당신의 직업을 선택할 시간입니다.\n어떤 길을 걷겠습니까?",
                choices=choices,
            )
            if result is not None:
                progress.selected_job = job_map.get(result, "warrior")

        return "continue"

    # =========================================================================
    # 신규 Phase 실행기들 (42챕터 확장)
    # =========================================================================

    def _run_shop(self, phase: dict) -> str:
        """상점 Phase - 골드/별조각 상점 체험"""
        npc_id = phase.get("npc", "tord")
        shop_type = phase.get("shop_type", "gold")  # "gold" or "star"

        # NPC 설명 대화
        intro_lines = phase.get("intro_lines", [])
        if intro_lines:
            self._run_dialogue({"npc": npc_id, "lines": intro_lines})

        try:
            if shop_type == "star":
                from src.ui.shop_ui import open_shop
                open_shop(self.console, self.context)
            else:
                from src.ui.gold_shop_ui import open_gold_shop
                from src.equipment.inventory import Inventory
                from src.character.character import Character
                lvl = self._get_level_for_chapter(self._current_chapter_id)
                party = [Character(name="크리스", character_class="warrior", level=lvl)]
                inventory = Inventory(base_weight=50.0, party=party)
                tutorial_gold = phase.get("gold", 500)
                open_gold_shop(self.console, self.context, inventory, tutorial_gold)
        except Exception as e:
            logger.warning(f"상점 UI 로드 실패, 대화 폴백: {e}")
            from src.ui.npc_dialog_ui import show_npc_dialog
            from src.story_mode.inline_tutorial_overlay import NPC_NAMES
            npc_name = NPC_NAMES.get(npc_id, npc_id)
            show_npc_dialog(self.console, self.context, npc_name,
                "상점에서는 골드로 아이템을 사고팔 수 있어요.\n"
                "좋은 장비와 소모품을 미리 준비해두세요!")
        return "continue"

    def _run_alchemy(self, phase: dict) -> str:
        """연금술 Phase - 연금술 UI 체험"""
        npc_id = phase.get("npc", "mira")
        intro_lines = phase.get("intro_lines", [])
        if intro_lines:
            self._run_dialogue({"npc": npc_id, "lines": intro_lines})

        try:
            from src.ui.alchemy_ui import open_alchemy_lab
            from src.equipment.inventory import Inventory
            from src.character.character import Character
            lvl = self._get_level_for_chapter(self._current_chapter_id)
            party = [Character(name="크리스", character_class="warrior", level=lvl)]
            inventory = Inventory(base_weight=50.0, party=party)
            # 튜토리얼용 재료 추가
            self._create_tutorial_inventory("alchemy", inventory)
            open_alchemy_lab(self.console, self.context, inventory)
        except Exception as e:
            logger.warning(f"연금술 UI 로드 실패, 대화 폴백: {e}")
            from src.ui.npc_dialog_ui import show_npc_dialog
            from src.story_mode.inline_tutorial_overlay import NPC_NAMES
            npc_name = NPC_NAMES.get(npc_id, npc_id)
            show_npc_dialog(self.console, self.context, npc_name,
                "연금술에서는 레시피에 맞는 재료를 조합해 포션을 제조할 수 있어요.\n"
                "운이 좋으면 걸작이 나와서 효과가 30% 증가해요!")
        return "continue"

    def _run_cooking(self, phase: dict) -> str:
        """요리 Phase - 요리 UI 체험"""
        npc_id = phase.get("npc", "lina")
        intro_lines = phase.get("intro_lines", [])
        if intro_lines:
            self._run_dialogue({"npc": npc_id, "lines": intro_lines})

        try:
            from src.ui.cooking_ui import open_cooking_pot
            from src.equipment.inventory import Inventory
            from src.character.character import Character
            lvl = self._get_level_for_chapter(self._current_chapter_id)
            party = [Character(name="크리스", character_class="warrior", level=lvl)]
            inventory = Inventory(base_weight=50.0, party=party)
            self._create_tutorial_inventory("cooking", inventory)
            open_cooking_pot(self.console, self.context, inventory, is_cooking_pot=True)
        except Exception as e:
            logger.warning(f"요리 UI 로드 실패, 대화 폴백: {e}")
            from src.ui.npc_dialog_ui import show_npc_dialog
            from src.story_mode.inline_tutorial_overlay import NPC_NAMES
            npc_name = NPC_NAMES.get(npc_id, npc_id)
            show_npc_dialog(self.console, self.context, npc_name,
                "요리는 4슬롯 냄비에 재료를 넣어서 만들어!\n"
                "요리솥을 사용하면 HP/MP 회복 +20%, 버프 지속시간 +20% 보너스!")
        return "continue"

    def _run_anvil(self, phase: dict) -> str:
        """대장간 Phase - 장비 강화 UI 체험"""
        npc_id = phase.get("npc", "tord")
        intro_lines = phase.get("intro_lines", [])
        if intro_lines:
            self._run_dialogue({"npc": npc_id, "lines": intro_lines})

        try:
            from src.ui.anvil_ui import open_anvil_ui
            from src.equipment.inventory import Inventory
            from src.character.character import Character
            lvl = self._get_level_for_chapter(self._current_chapter_id)
            party = [Character(name="크리스", character_class="warrior", level=lvl)]
            inventory = Inventory(base_weight=50.0, party=party)
            self._create_tutorial_inventory("anvil", inventory)
            open_anvil_ui(self.console, self.context, inventory, target_tile=None)
        except Exception as e:
            logger.warning(f"대장간 UI 로드 실패, 대화 폴백: {e}")
            from src.ui.npc_dialog_ui import show_npc_dialog
            from src.story_mode.inline_tutorial_overlay import NPC_NAMES
            npc_name = NPC_NAMES.get(npc_id, npc_id)
            show_npc_dialog(self.console, self.context, npc_name,
                "대장간에서는 장비를 강화하고 재연마할 수 있소.\n"
                "재연마하면 장비의 접사가 바뀌니 좋은 효과를 노려보시오.")
        return "continue"

    def _run_inventory(self, phase: dict) -> str:
        """인벤토리 Phase - 인벤토리 UI 체험"""
        npc_id = phase.get("npc", "tord")
        intro_lines = phase.get("intro_lines", [])
        if intro_lines:
            self._run_dialogue({"npc": npc_id, "lines": intro_lines})

        try:
            from src.ui.inventory_ui import open_inventory
            from src.equipment.inventory import Inventory
            from src.character.character import Character
            lvl = self._get_level_for_chapter(self._current_chapter_id)
            party = [Character(name="크리스", character_class="warrior", level=lvl)]
            inventory = Inventory(base_weight=50.0, party=party)
            self._create_tutorial_inventory("inventory", inventory)
            open_inventory(self.console, self.context, inventory, party)
        except Exception as e:
            logger.warning(f"인벤토리 UI 로드 실패, 대화 폴백: {e}")
            from src.ui.npc_dialog_ui import show_npc_dialog
            from src.story_mode.inline_tutorial_overlay import NPC_NAMES
            npc_name = NPC_NAMES.get(npc_id, npc_id)
            show_npc_dialog(self.console, self.context, npc_name,
                "인벤토리에서는 아이템을 관리할 수 있소.\n"
                "무게 제한이 있으니 필요한 것만 가지고 다니시오.")
        return "continue"

    def _run_save_load(self, phase: dict) -> str:
        """저장/로드 Phase - 저장 화면 체험"""
        npc_id = phase.get("npc", "selena")
        intro_lines = phase.get("intro_lines", [])
        if intro_lines:
            self._run_dialogue({"npc": npc_id, "lines": intro_lines})

        try:
            from src.ui.save_load_ui import show_save_screen
            show_save_screen(self.console, self.context, game_state=None)
        except Exception as e:
            logger.warning(f"저장/로드 UI 로드 실패, 대화 폴백: {e}")
            from src.ui.npc_dialog_ui import show_npc_dialog
            from src.story_mode.inline_tutorial_overlay import NPC_NAMES
            npc_name = NPC_NAMES.get(npc_id, npc_id)
            show_npc_dialog(self.console, self.context, npc_name,
                "본 게임에서는 저장 포인트에서 게임을 저장할 수 있어요.\n"
                "스토리 모드는 자동 저장되니 걱정하지 마세요!")
        return "continue"

    def _run_party_setup_phase(self, phase: dict) -> str:
        """파티 구성 Phase - 파티 편성 UI 체험"""
        npc_id = phase.get("npc", "karnos")
        intro_lines = phase.get("intro_lines", [])
        if intro_lines:
            self._run_dialogue({"npc": npc_id, "lines": intro_lines})

        try:
            from src.ui.party_setup import run_party_setup
            run_party_setup(self.console, self.context)
        except Exception as e:
            logger.warning(f"파티 구성 UI 로드 실패, 대화 폴백: {e}")
            from src.ui.npc_dialog_ui import show_npc_dialog
            from src.story_mode.inline_tutorial_overlay import NPC_NAMES
            npc_name = NPC_NAMES.get(npc_id, npc_id)
            show_npc_dialog(self.console, self.context, npc_name,
                "파티를 구성할 때는 역할 분담이 중요하다.\n"
                "탱커, 딜러, 힐러의 균형을 맞추는 게 핵심이지.")
        return "continue"

    def _run_guild_hall(self, phase: dict) -> str:
        """길드 홀 Phase - 길드 UI 체험"""
        npc_id = phase.get("npc", "selena")
        intro_lines = phase.get("intro_lines", [])
        if intro_lines:
            self._run_dialogue({"npc": npc_id, "lines": intro_lines})

        try:
            from src.ui.guild_hall_ui import GuildHallUI
            guild_ui = GuildHallUI(self.console.width, self.console.height)
            guild_ui.run(self.console, self.context)
        except Exception as e:
            logger.warning(f"길드 홀 UI 로드 실패, 대화 폴백: {e}")
            from src.ui.npc_dialog_ui import show_npc_dialog
            from src.story_mode.inline_tutorial_overlay import NPC_NAMES
            npc_name = NPC_NAMES.get(npc_id, npc_id)
            show_npc_dialog(self.console, self.context, npc_name,
                "길드 홀에서는 도전과제를 확인하고 보상을 받을 수 있어요.\n"
                "마일스톤을 달성하면 특별한 보상이 있답니다!")
        return "continue"

    def _run_bomb_craft(self, phase: dict) -> str:
        """폭탄 제작 Phase - 폭탄 제작 대화 체험"""
        npc_id = phase.get("npc", "lina")
        intro_lines = phase.get("intro_lines", [])
        if intro_lines:
            self._run_dialogue({"npc": npc_id, "lines": intro_lines})

        try:
            from src.cooking.bomb_crafting import BombCrafter
            from src.equipment.inventory import Inventory
            from src.character.character import Character
            lvl = self._get_level_for_chapter(self._current_chapter_id)
            party = [Character(name="크리스", character_class="warrior", level=lvl)]
            inventory = Inventory(base_weight=50.0, party=party)
            self._create_tutorial_inventory("bomb", inventory)
            crafter = BombCrafter(inventory)
            # 폭탄 제작은 대화 기반으로 안내
            from src.ui.npc_dialog_ui import show_npc_dialog, NPCChoice
            from src.story_mode.inline_tutorial_overlay import NPC_NAMES
            npc_name = NPC_NAMES.get(npc_id, npc_id)
            bomb_types = crafter.get_available_bombs() if hasattr(crafter, 'get_available_bombs') else []
            if bomb_types:
                choices = [NPCChoice(text=f"{b}") for b in bomb_types[:4]]
                show_npc_dialog(self.console, self.context, npc_name,
                    "어떤 폭탄을 만들어볼까?", choices=choices)
            else:
                show_npc_dialog(self.console, self.context, npc_name,
                    "폭탄은 재료를 모아서 만들 수 있어!\n"
                    "화염 폭탄, 얼음 폭탄, 번개 폭탄 등 다양한 종류가 있지.")
        except Exception as e:
            logger.warning(f"폭탄 제작 시스템 로드 실패, 대화 폴백: {e}")
            from src.ui.npc_dialog_ui import show_npc_dialog
            from src.story_mode.inline_tutorial_overlay import NPC_NAMES
            npc_name = NPC_NAMES.get(npc_id, npc_id)
            show_npc_dialog(self.console, self.context, npc_name,
                "폭탄은 범위 공격이 가능한 소모품이야!\n"
                "보스전에서 잡몹을 한꺼번에 처리할 때 유용해!")
        return "continue"

    def _run_boss_combat(self, phase: dict, chapter_id: str) -> str:
        """보스 전투 Phase - 기믹/타이머 힌트 포함 보스전"""
        # 보스 기믹 설명
        gimmick_lines = phase.get("gimmick_lines", [])
        if gimmick_lines:
            npc_id = phase.get("npc", "selena")
            self._run_dialogue({"npc": npc_id, "lines": gimmick_lines})

        # 타이머 힌트
        timer_hint = phase.get("timer_hint")
        if timer_hint:
            from src.ui.npc_dialog_ui import show_npc_dialog
            from src.story_mode.inline_tutorial_overlay import NPC_NAMES
            npc_id = phase.get("npc", "selena")
            npc_name = NPC_NAMES.get(npc_id, npc_id)
            show_npc_dialog(self.console, self.context, npc_name,
                f"제한 시간: {timer_hint}분!\n시간 내에 보스를 쓰러뜨려야 해요!")

        # 실제 전투 (보스 플래그 포함)
        boss_phase = dict(phase)
        boss_phase["type"] = "combat"
        return self._run_combat(boss_phase, chapter_id)

    def _run_difficulty_select(self, phase: dict) -> str:
        """난이도 선택 Phase - 5단계 난이도 설명"""
        npc_id = phase.get("npc", "selena")
        from src.ui.npc_dialog_ui import show_npc_dialog, NPCChoice
        from src.story_mode.inline_tutorial_overlay import NPC_NAMES
        npc_name = NPC_NAMES.get(npc_id, npc_id)

        difficulties = [
            NPCChoice(text="이야기 (Story) - 전투 매우 쉬움, 스토리 집중"),
            NPCChoice(text="쉬움 (Easy) - 편안한 난이도, 초보자용"),
            NPCChoice(text="보통 (Normal) - 균형 잡힌 도전 [기본]"),
            NPCChoice(text="어려움 (Hard) - 높은 전략 요구, 보상 증가"),
            NPCChoice(text="지옥 (Hell) - 극한의 도전, 최고 보상"),
        ]

        show_npc_dialog(self.console, self.context, npc_name,
            "본 게임에서는 5가지 난이도를 선택할 수 있어요.\n"
            "난이도가 높을수록 보상도 좋아져요!\n"
            "어떤 난이도를 체험해볼까요?",
            choices=difficulties)

        return "continue"

    def _create_tutorial_inventory(self, chapter_type: str, inventory) -> None:
        """튜토리얼용 아이템/장비/재료 인벤토리 생성

        IngredientDatabase/ItemGenerator에서 실제 객체를 가져와 add_item에 넘긴다.
        """
        from copy import deepcopy
        try:
            from src.gathering.ingredient import IngredientDatabase
            from src.equipment.item_system import ItemGenerator
            idb = IngredientDatabase.INGREDIENTS

            def _add_ingredient(inv, ing_id: str, qty: int):
                """IngredientDatabase에서 복제한 Ingredient를 qty개 추가"""
                template = idb.get(ing_id)
                if template is None:
                    logger.warning(f"재료 ID를 찾을 수 없음: {ing_id}")
                    return
                for _ in range(qty):
                    inv.add_item(deepcopy(template), 1)

            if chapter_type == "alchemy":
                # 소형 체력 포션: glass_vial 1, pure_water 1, magic_herb 1
                # 소형 마나 포션: glass_vial 1, pure_water 1, blue_mushroom 1
                _add_ingredient(inventory, "glass_vial", 3)
                _add_ingredient(inventory, "pure_water", 3)
                _add_ingredient(inventory, "magic_herb", 3)
                _add_ingredient(inventory, "blue_mushroom", 2)

            elif chapter_type == "anvil":
                # 대장간: 강화/재연마할 장비 제공 (골드로 강화)
                weapon = ItemGenerator.create_weapon("iron_sword", add_random_affixes=False)
                armor = ItemGenerator.create_armor("leather_armor", add_random_affixes=False)
                inventory.add_item(weapon, 1)
                inventory.add_item(armor, 1)
                inventory.gold = max(getattr(inventory, 'gold', 0), 500)

            elif chapter_type == "inventory":
                # 다양한 아이템 종류 체험
                hp_pot = ItemGenerator.create_consumable("minor_hp_potion")
                mp_pot = ItemGenerator.create_consumable("minor_mp_potion")
                weapon = ItemGenerator.create_weapon("iron_sword", add_random_affixes=False)
                armor = ItemGenerator.create_armor("leather_armor", add_random_affixes=False)
                accessory = ItemGenerator.create_accessory("health_ring", add_random_affixes=False)
                inventory.add_item(hp_pot, 3)
                inventory.add_item(mp_pot, 2)
                inventory.add_item(weapon, 1)
                inventory.add_item(armor, 1)
                inventory.add_item(accessory, 1)

            elif chapter_type == "cooking":
                # 요리 레시피에 맞는 실제 재료 (허브 수프, 버섯 스튜 등 제작 가능)
                _add_ingredient(inventory, "monster_meat", 3)
                _add_ingredient(inventory, "magic_herb", 3)
                _add_ingredient(inventory, "red_mushroom", 2)
                _add_ingredient(inventory, "blue_mushroom", 2)
                _add_ingredient(inventory, "carrot", 2)
                _add_ingredient(inventory, "potato", 2)

            elif chapter_type == "bomb":
                # 화염 폭탄: bomb_casing 1, gunpowder 2, fuse 1, fire_essence 1
                _add_ingredient(inventory, "bomb_casing", 3)
                _add_ingredient(inventory, "gunpowder", 6)
                _add_ingredient(inventory, "fuse", 3)
                _add_ingredient(inventory, "fire_essence", 2)
                _add_ingredient(inventory, "metal_scrap", 3)

            elif chapter_type == "bomb_combat":
                # 폭탄 전투용: 제작 완료된 폭탄을 바로 제공
                fire_bomb = ItemGenerator.create_consumable("fire_bomb")
                ice_bomb = ItemGenerator.create_consumable("ice_bomb")
                inventory.add_item(fire_bomb, 3)
                inventory.add_item(ice_bomb, 2)

            elif chapter_type == "act3_boss":
                # 3막 보스: 시스템 학습 확인용 (포션, 폭탄 등)
                greater_hp = ItemGenerator.create_consumable("greater_hp_potion")
                greater_mp = ItemGenerator.create_consumable("greater_mp_potion")
                fire_bomb = ItemGenerator.create_consumable("fire_bomb")
                bandage = ItemGenerator.create_consumable("bandage")
                if greater_hp: inventory.add_item(greater_hp, 3)
                if greater_mp: inventory.add_item(greater_mp, 2)
                if fire_bomb: inventory.add_item(fire_bomb, 2)
                if bandage: inventory.add_item(bandage, 3) # 상처 치료용

        except Exception as e:
            logger.warning(f"튜토리얼 인벤토리 생성 실패: {e}")

    def _create_story_enemies(self, enemies_data: list, is_boss_chapter: bool = False) -> list:
        """_enemy() 딕셔너리를 SimpleEnemy 객체로 변환 (스토리 모드 난이도 정규화)

        랜덤 층수 생성 대신 미리 정의된 스탯을 정확히 사용하되,
        튜토리얼 특성에 맞게 스탯을 적정 범위로 클램프한다.
        """
        from src.world.enemy_generator import EnemyTemplate, SimpleEnemy

        result = []
        for i, ed in enumerate(enemies_data):
            name = ed.get("name", f"적 {i+1}")
            hp = int(ed.get("hp", 100) * 1.7)
            brv = int(ed.get("brv", 50) * 2.0)
            atk = int(ed.get("attack", 10) * 2.0)
            dfs = int(ed.get("defense", 5) * 2.0)
            spd = ed.get("speed", 30)

            # 스토리 모드 난이도 정규화 - 모든 챕터에서 비슷한 난이도 유지 (상한선 해제)
            if is_boss_chapter:
                hp = max(120, hp)
                brv = max(100, brv)
                atk = max(10, atk)
                dfs = max(5, dfs)
                spd = max(25, spd)
            else:
                hp = max(60, hp)
                brv = max(50, brv)
                atk = max(5, atk)
                dfs = max(2, dfs)
                spd = max(20, spd)

            # EnemyTemplate 생성 (level=1로 성장 공식 무효화)
            template = EnemyTemplate(
                enemy_id=f"story_{i}",
                name=name,
                level=1,
                hp=hp, mp=50,
                physical_attack=atk, physical_defense=dfs,
                magic_attack=atk, magic_defense=dfs,
                speed=spd,
                max_brv=brv, init_brv=brv // 2,
            )

            # SimpleEnemy 생성 후 정확한 스탯으로 오버라이드
            # (SimpleEnemy 생성자가 ±20% 분산 + 배율을 적용하므로 덮어씀)
            enemy = SimpleEnemy(template, level_modifier=1.0)
            enemy.max_hp = hp
            enemy.current_hp = hp
            enemy.physical_attack = atk
            enemy.physical_defense = dfs
            enemy.magic_attack = atk
            enemy.magic_defense = dfs
            enemy.speed = spd
            enemy.max_brv = brv
            enemy.init_brv = brv // 2
            enemy.current_brv = enemy.init_brv

            result.append(enemy)

        return result

    def _create_tutorial_gold(self, chapter_id: str) -> int:
        """챕터별 적절한 튜토리얼 골드 반환"""
        gold_map = {
            "act3_ch8": 500,   # 상인의 길
        }
        return gold_map.get(chapter_id, 300)

    # =========================================================================
    # 실제 게임 시스템 헬퍼
    # =========================================================================

    def _create_real_party(self, chapter_id: str) -> list:
        """실제 Character 객체로 파티 생성 (챕터에 맞는 레벨 적용)"""
        from src.character.character import Character

        level = self._get_level_for_chapter(chapter_id)

        # 주인공
        player = Character(name="크리스", character_class="warrior", level=level)
        party = [player]

        # 챕터별 NPC 합류 (실제 직업)
        _ACT_NPC_THRESHOLDS = [
            ("act2_ch3", "카르노스", "knight"),
            ("act3_ch1", "미라", "magician"),
            ("act5_ch1", "셀레나", "cleric"),
        ]

        for threshold_id, npc_name, npc_class in _ACT_NPC_THRESHOLDS:
            if self._chapter_reached(chapter_id, threshold_id):
                npc = Character(name=npc_name, character_class=npc_class, level=level)
                party.append(npc)

        return party

    @staticmethod
    def _chapter_reached(current_id: str, threshold_id: str) -> bool:
        """현재 챕터가 threshold 챕터 이후(포함)인지 확인"""
        if current_id not in CHAPTER_ORDER or threshold_id not in CHAPTER_ORDER:
            return False
        return CHAPTER_ORDER.index(current_id) >= CHAPTER_ORDER.index(threshold_id)

    @staticmethod
    def _get_floor_for_chapter(chapter_id: str) -> int:
        """챕터에 대응하는 던전 층수 (CHAPTER_ORDER 내 위치 기반 점진 증가)"""
        if chapter_id not in CHAPTER_ORDER:
            return 1

        idx = CHAPTER_ORDER.index(chapter_id)
        total = len(CHAPTER_ORDER)  # 42

        # 층수 1~15 범위로 점진적 증가
        base_floor = max(1, 1 + int(idx * 14 / max(1, total - 1)))

        # 보스/피날레 챕터는 +2
        if "boss" in chapter_id or "finale" in chapter_id:
            base_floor += 2

        return base_floor

    @staticmethod
    def _get_level_for_chapter(chapter_id: str) -> int:
        """챕터에 대응하는 파티 레벨 (CHAPTER_ORDER 내 위치 기반 점진 성장)"""
        if chapter_id not in CHAPTER_ORDER:
            return 1

        idx = CHAPTER_ORDER.index(chapter_id)
        total = len(CHAPTER_ORDER)  # 42

        # 레벨 1~18 범위로 점진적 증가 (42챕터 기준)
        # 프롤로그=1, 피날레=18, 보스/피날레 +2
        base_level = max(1, 1 + int(idx * 17 / max(1, total - 1)))

        # 보스/피날레 챕터는 +2
        if "boss" in chapter_id or "finale" in chapter_id:
            base_level += 2

        return base_level

    # =========================================================================
    # UI 헬퍼
    # =========================================================================

    def _show_chapter_title(self, title: str, subtitle: str) -> str:
        """챕터 시작 타이틀 화면 - 파티클 효과 + NPC 가이드 + Act 색상"""
        import math
        import random

        start_time = time.time()
        fade_duration = 2.0
        w, h = self.console.width, self.console.height
        cx, cy = w // 2, h // 2

        # Act 색상 결정
        meta = CHAPTER_META.get(self._current_chapter_id, {})
        act_id = meta.get("act", "act1")
        npc_id = meta.get("npc_guide", "selena")
        from src.story_mode.story_mode_manager import ACT_INFO
        act_info = ACT_INFO.get(act_id, {})
        act_color = act_info.get("color", (100, 200, 255))
        act_title = act_info.get("title", "")

        npc_name = NPC_NAMES.get(npc_id, npc_id)
        npc_color = NPC_COLORS.get(npc_id, (200, 200, 200))

        # 배경 파티클 생성
        particles = []
        for _ in range(30):
            particles.append({
                "x": random.uniform(0, w),
                "y": random.uniform(0, h),
                "vx": random.uniform(-0.3, 0.3),
                "vy": random.uniform(-0.5, -0.1),
                "char": random.choice([".", "*", "+", "·"]),
                "phase": random.uniform(0, math.pi * 2),
                "speed": random.uniform(0.5, 1.5),
            })

        # 입력 큐 비우기
        for _ in tcod.event.get():
            pass

        while True:
            elapsed = time.time() - start_time
            alpha = min(1.0, elapsed / fade_duration)

            self.console.clear()

            # 배경: Act별 미묘한 색조 그라데이션
            for y in range(h):
                t = y / max(1, h - 1)
                r = int(3 + t * act_color[0] * 0.04)
                g = int(3 + t * act_color[1] * 0.03)
                b = int(8 + t * act_color[2] * 0.06)
                for x in range(w):
                    self.console.rgb[y, x] = (ord(" "), (r, g, b), (r, g, b))

            # 배경 파티클 렌더링
            frame_t = elapsed * 60
            for p in particles:
                px = int(p["x"] + p["vx"] * elapsed * 10) % w
                py = int(p["y"] + p["vy"] * elapsed * 10) % h
                bright = 0.3 + 0.7 * abs(math.sin(frame_t * 0.03 * p["speed"] + p["phase"]))
                bright *= alpha
                pc = (min(255, int(act_color[0] * bright * 0.5)),
                      min(255, int(act_color[1] * bright * 0.5)),
                      min(255, int(act_color[2] * bright * 0.5)))
                if 0 <= px < w and 0 <= py < h and sum(pc) > 20:
                    self.console.print(px, py, p["char"], fg=pc)

            # 타이틀 페이드인
            brightness = alpha

            # Act 표시 (상단)
            act_label = f"─ {act_title} ─"
            ab = brightness * 0.6
            self.console.print(
                (w - len(act_label)) // 2, cy - 5,
                act_label,
                fg=(int(act_color[0] * ab), int(act_color[1] * ab), int(act_color[2] * ab)),
            )

            # 상단 장식선 (Act 색상)
            deco_chars = "═══════════════════════════════"
            dc = brightness * 0.35
            deco_color = (int(act_color[0] * dc), int(act_color[1] * dc), int(act_color[2] * dc))
            self.console.print(cx - 15, cy - 3, deco_chars[:30], fg=deco_color)

            # 코너 장식
            corner_b = brightness * 0.5
            cc = (int(act_color[0] * corner_b), int(act_color[1] * corner_b), int(act_color[2] * corner_b))
            self.console.print(cx - 16, cy - 3, "╔", fg=cc)
            self.console.print(cx + 15, cy - 3, "╗", fg=cc)
            self.console.print(cx - 16, cy + 5, "╚", fg=cc)
            self.console.print(cx + 15, cy + 5, "╝", fg=cc)
            # 세로선
            for dy in range(cy - 2, cy + 5):
                if 0 <= dy < h:
                    self.console.print(cx - 16, dy, "║", fg=cc)
                    self.console.print(cx + 15, dy, "║", fg=cc)

            # 챕터 타이틀 (밝은 흰색 + 약간의 Act 색조)
            tb = brightness
            title_color = (
                min(255, int(200 * tb + act_color[0] * 0.2 * tb)),
                min(255, int(200 * tb + act_color[1] * 0.2 * tb)),
                min(255, int(220 * tb + act_color[2] * 0.15 * tb)),
            )
            self.console.print(
                (w - len(title)) // 2, cy - 1, title, fg=title_color
            )

            # 서브타이틀 (Act 색상 기반)
            if subtitle:
                sb = brightness * 0.85
                sub_color = (
                    min(255, int(act_color[0] * sb)),
                    min(255, int(act_color[1] * sb)),
                    min(255, int(act_color[2] * sb)),
                )
                self.console.print(
                    (w - len(subtitle)) // 2, cy + 1,
                    subtitle, fg=sub_color,
                )

            # 하단 장식선
            self.console.print(cx - 15, cy + 3, deco_chars[:30], fg=deco_color)

            # NPC 가이드 표시 (페이드인 후 등장)
            if elapsed > 1.0:
                npc_alpha = min(1.0, (elapsed - 1.0) / 0.8)
                npc_text = f"가이드: {npc_name}"
                nc = (int(npc_color[0] * npc_alpha),
                      int(npc_color[1] * npc_alpha),
                      int(npc_color[2] * npc_alpha))
                self.console.print(
                    (w - len(npc_text)) // 2, cy + 5, npc_text, fg=nc
                )

            # 안내 (1.5초 후 등장, 깜빡임)
            if elapsed > 1.5:
                help_alpha = min(1.0, (elapsed - 1.5) / 0.5)
                blink = 0.6 + 0.4 * math.sin(elapsed * 3.0)
                hb = help_alpha * blink
                help_text = "Z: 시작  Tab: 스킵  X: 돌아가기"
                self.console.print(
                    (w - len(help_text)) // 2, h - 3,
                    help_text,
                    fg=(int(150 * hb), int(150 * hb), int(180 * hb)),
                )

            self.context.present(self.console)

            # 입력 처리
            for action, event in poll_game_input():
                action = action or _pointer_screen_action(event)
                if action == GameAction.CONFIRM:
                    play_sfx("ui", "cursor_select")
                    return "start"
                elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                    play_sfx("ui", "cursor_cancel")
                    return "quit"
                elif action == GameAction.QUIT:
                    return "quit"
                elif event and isinstance(event, tcod.event.KeyDown):
                    if event.sym == tcod.event.KeySym.TAB:
                        return "skip"
                elif event and isinstance(event, tcod.event.Quit):
                    return "quit"

            # 자동 시작 (5초 후)
            if elapsed > 5.0:
                return "start"

            time.sleep(0.016)

    def _apply_chapter_rewards(self, chapter_id: str, rewards: dict):
        """챕터 보상을 메타 진행에 실제 적용 (exactly-once)

        - star_fragments를 별의 파편에 지급하고 저장한다.
        - 이미 완료된 챕터를 다시 클리어한 경우 중복 지급하지 않는다.
        - 실제 지급액은 화면 표시값과 다를 수 있으므로 로그로 남긴다.
        """
        star_fragments = int(rewards.get("star_fragments", 0) or 0)
        if star_fragments <= 0:
            return

        try:
            from src.story_mode.story_mode_manager import (
                StoryModeProgress as _Progress,
            )
            # 호출 시점에는 run_chapter의 progress가 아직 complete_chapter 되기 전이므로
            # 재플레이 여부는 이미 완료 목록으로 판단한다.
            from src.persistence.meta_progress import (
                get_meta_progress,
                save_meta_progress,
            )

            meta = get_meta_progress()
            already_done = getattr(self, "_last_progress", None)
            if (
                isinstance(already_done, _Progress)
                and already_done.is_chapter_completed(chapter_id)
            ):
                logger.info(
                    f"챕터 '{chapter_id}' 재클리어 - 보상 중복 지급 생략"
                )
                return

            meta.add_star_fragments(star_fragments)
            save_meta_progress()
            logger.info(
                f"챕터 보상 적용: '{chapter_id}' 별의 파편 +{star_fragments}"
            )
        except Exception as e:
            logger.error(f"챕터 보상 적용 실패 ({chapter_id}): {e}")

    def _show_rewards(self, rewards: dict, meta: dict):
        """보상 표시 - 별의 파편 수집 연출"""
        import math
        import random

        message = rewards.get("message", "챕터 완료!")
        star_fragments = rewards.get("star_fragments", 0)

        w, h = self.console.width, self.console.height
        cx, cy = w // 2, h // 2

        # 보상이 없으면 간단 대화만
        if star_fragments <= 0:
            from src.ui.npc_dialog_ui import show_npc_dialog
            npc = meta.get("npc_guide", "selena")
            npc_name = NPC_NAMES.get(npc, npc)
            show_npc_dialog(self.console, self.context, npc_name, message)
            return

        # 별 파편 수집 연출
        start = time.time()
        duration = 3.0
        # 별 파편 파티클들 (바깥에서 중앙으로 수렴)
        frag_particles = []
        for i in range(star_fragments * 3):
            angle = random.uniform(0, math.pi * 2)
            dist = random.uniform(15, 25)
            frag_particles.append({
                "start_x": cx + math.cos(angle) * dist,
                "start_y": cy + math.sin(angle) * dist * 0.5,
                "delay": random.uniform(0, 1.0),
                "char": random.choice(["★", "✦", "*", "+"]),
            })

        while True:
            elapsed = time.time() - start
            if elapsed > duration:
                break

            self.console.clear()

            # 어두운 배경
            for y in range(h):
                for x in range(w):
                    self.console.rgb[y, x] = (ord(" "), (3, 3, 10), (3, 3, 10))

            # 메시지 (상단)
            msg_alpha = min(1.0, elapsed / 0.8)
            mc = (int(200 * msg_alpha), int(200 * msg_alpha), int(255 * msg_alpha))
            self.console.print((w - len(message)) // 2, cy - 5, message, fg=mc)

            # 별 파편 파티클 (수렴 애니메이션)
            for p in frag_particles:
                t = max(0, elapsed - p["delay"])
                if t <= 0:
                    continue
                progress = min(1.0, t / 1.5)
                # 이징: 가속하며 중앙으로
                ease = progress * progress
                px = int(p["start_x"] + (cx - p["start_x"]) * ease)
                py = int(p["start_y"] + (cy - p["start_y"]) * ease)

                if 0 <= px < w and 0 <= py < h:
                    bright = 1.0 - progress * 0.3
                    fc = (min(255, int(255 * bright)),
                          min(255, int(215 * bright)),
                          min(255, int(50 * bright)))
                    self.console.print(px, py, p["char"], fg=fc)

            # 중앙 카운터 (파편 수 표시)
            counter_alpha = min(1.0, max(0, (elapsed - 0.5) / 0.5))
            if counter_alpha > 0:
                # 펄스 효과
                pulse = 0.8 + 0.2 * math.sin(elapsed * 6)
                frag_text = f"★ 별의 파편 +{star_fragments}"
                fc = (min(255, int(255 * counter_alpha * pulse)),
                      min(255, int(215 * counter_alpha * pulse)),
                      min(255, int(0 * counter_alpha)))
                self.console.print((w - len(frag_text)) // 2, cy, frag_text, fg=fc)

                # 장식 스파클
                if elapsed > 1.5:
                    sparkle_chars = ["✦", "★", "+", "·"]
                    for i in range(6):
                        angle = elapsed * 2 + i * (math.pi / 3)
                        r = 3 + math.sin(elapsed * 4 + i) * 2
                        sx = int(cx + math.cos(angle) * r)
                        sy = int(cy + math.sin(angle) * r * 0.5)
                        if 0 <= sx < w and 0 <= sy < h:
                            sc = (int(255 * pulse * 0.5), int(215 * pulse * 0.5), int(100 * pulse * 0.3))
                            self.console.print(sx, sy, sparkle_chars[i % len(sparkle_chars)], fg=sc)

            # 안내
            if elapsed > 2.0:
                help_text = "아무 키나 누르세요"
                self.console.print(
                    (w - len(help_text)) // 2, h - 3,
                    help_text, fg=(100, 100, 130),
                )

            self.context.present(self.console)

            # 입력 처리
            for action, event in poll_game_input():
                action = action or _pointer_screen_action(event)
                if action is not None and elapsed > 0.5:
                    return
                elif event and isinstance(event, tcod.event.Quit) and elapsed > 0.5:
                    return

            time.sleep(0.016)

    def _show_chapter_complete(self, title: str, subtitle: str):
        """챕터 완료 화면 - 축하 파티클 효과 + 진행률 표시"""
        import math
        import random

        w, h = self.console.width, self.console.height
        cx, cy = w // 2, h // 2

        # Act 색상
        meta = CHAPTER_META.get(self._current_chapter_id, {})
        act_id = meta.get("act", "act1")
        from src.story_mode.story_mode_manager import ACT_INFO, CHAPTER_ORDER as CH_ORDER
        act_color = ACT_INFO.get(act_id, {}).get("color", (100, 200, 255))

        # 진행률 계산
        completed_count = 0
        total_count = len(CH_ORDER)
        for ch in CH_ORDER:
            # 현재 챕터 포함
            if ch == self._current_chapter_id or (
                hasattr(self, '_progress') and ch in getattr(self, '_progress', {})
            ):
                completed_count += 1

        # 축하 파티클 생성
        confetti = []
        confetti_chars = ["✦", "★", "☆", "◆", "◇", "+", "*", "·"]
        confetti_colors = [
            (255, 215, 0), (0, 255, 150), (100, 200, 255),
            (255, 150, 200), (200, 150, 255), (255, 255, 100),
        ]
        for _ in range(40):
            confetti.append({
                "x": random.uniform(0, w),
                "y": random.uniform(-10, -1),
                "vy": random.uniform(0.3, 1.0),
                "vx": random.uniform(-0.3, 0.3),
                "char": random.choice(confetti_chars),
                "color": random.choice(confetti_colors),
                "phase": random.uniform(0, math.pi * 2),
            })

        play_sfx("character", "level_up")

        start = time.time()
        while True:
            elapsed = time.time() - start

            self.console.clear()

            # 배경: 어두운 우주 + 미묘한 Act 색조
            for y in range(h):
                t = y / max(1, h - 1)
                r = int(3 + act_color[0] * 0.02 * t)
                g = int(3 + act_color[1] * 0.015 * t)
                b = int(8 + act_color[2] * 0.04 * t)
                for x in range(w):
                    self.console.rgb[y, x] = (ord(" "), (r, g, b), (r, g, b))

            # 축하 파티클 (위에서 떨어지는 컨페티)
            for p in confetti:
                px = int(p["x"] + p["vx"] * elapsed * 20 + math.sin(elapsed * 2 + p["phase"]) * 2)
                py = int(p["y"] + p["vy"] * elapsed * 15)
                px = px % w
                if 0 <= py < h:
                    bright = max(0.3, 1.0 - (py / h) * 0.5)
                    pc = (min(255, int(p["color"][0] * bright)),
                          min(255, int(p["color"][1] * bright)),
                          min(255, int(p["color"][2] * bright)))
                    self.console.print(px, py, p["char"], fg=pc)

            # 페이드인
            alpha = min(1.0, elapsed / 0.8)

            # 상단 장식
            deco = "═" * 30
            dc = alpha * 0.4
            self.console.print(
                cx - 15, cy - 4, deco,
                fg=(int(act_color[0] * dc), int(act_color[1] * dc), int(act_color[2] * dc))
            )

            # 완료 텍스트 (펄스)
            pulse = 0.8 + 0.2 * math.sin(elapsed * 4)
            complete_text = "★ 챕터 완료 ★"
            cc = (min(255, int(255 * alpha * pulse)),
                  min(255, int(215 * alpha * pulse)),
                  min(255, int(0 * alpha)))
            self.console.print(
                (w - len(complete_text)) // 2, cy - 2, complete_text, fg=cc
            )

            # 챕터 정보
            info = f"{title}: {subtitle}"
            ic = (int(act_color[0] * alpha * 0.9),
                  int(act_color[1] * alpha * 0.9),
                  int(act_color[2] * alpha * 0.9))
            self.console.print((w - len(info)) // 2, cy, info, fg=ic)

            # 하단 장식
            self.console.print(
                cx - 15, cy + 2, deco,
                fg=(int(act_color[0] * dc), int(act_color[1] * dc), int(act_color[2] * dc))
            )

            # 다음 챕터 미리보기 (2초 후)
            if elapsed > 1.5:
                na = min(1.0, (elapsed - 1.5) / 0.5)
                # 현재 챕터의 다음 챕터 확인
                if self._current_chapter_id in CH_ORDER:
                    idx = CH_ORDER.index(self._current_chapter_id)
                    if idx + 1 < len(CH_ORDER):
                        next_ch = CH_ORDER[idx + 1]
                        next_meta = CHAPTER_META.get(next_ch, {})
                        next_text = f"다음: {next_meta.get('title', '')} - {next_meta.get('subtitle', '')}"
                        nc = (int(150 * na), int(150 * na), int(200 * na))
                        self.console.print((w - len(next_text)) // 2, cy + 4, next_text, fg=nc)
                    else:
                        final_text = "모든 챕터를 완료했습니다!"
                        nc = (int(255 * na), int(215 * na), int(0 * na))
                        self.console.print((w - len(final_text)) // 2, cy + 4, final_text, fg=nc)

            # 안내
            if elapsed > 2.0:
                blink = 0.5 + 0.5 * math.sin(elapsed * 3)
                help_text = "아무 키나 누르세요"
                self.console.print(
                    (w - len(help_text)) // 2, h - 3,
                    help_text, fg=(int(120 * blink), int(120 * blink), int(150 * blink)),
                )

            self.context.present(self.console)

            # 입력 처리 (최소 1초는 보여줌)
            for action, event in poll_game_input():
                action = action or _pointer_screen_action(event)
                if action is not None and elapsed > 1.0:
                    return
                elif event and isinstance(event, tcod.event.Quit) and elapsed > 1.0:
                    return

            if elapsed > 8.0:
                return
            time.sleep(0.016)


# =============================================================================
# 30개 챕터 콘텐츠 생성기 (10시간+ 분량, 높은 난이도)
# =============================================================================

def _enemy(name, hp, brv, atk=35, dfs=30, spd=50, elem="none"):
    """적 생성 (전사 Lv1: HP210, ATK68, DEF68, SPD68 기준 밸런싱)"""
    return {"name": name, "hp": hp, "brv": brv, "attack": atk, "defense": dfs, "speed": spd, "element": elem}

def _seg(text, color="white", pause=1.5):
    return {"text": text, "color": color, "pause": pause}

def _dlg(npc, lines, effects=None):
    d = {"type": "dialogue", "npc": npc, "lines": lines}
    if effects:
        d["effects"] = effects
    return d

def _cut(segments):
    return {"type": "cutscene", "segments": segments}

def _combat(enemies, hints=None, victory_npc=None, victory_lines=None, inventory_type=None):
    c = {"type": "combat", "enemies": enemies, "combat_hints": hints or []}
    if victory_npc and victory_lines:
        c["victory_dialogue"] = {"npc": victory_npc, "lines": victory_lines}
    if inventory_type:
        c["inventory_type"] = inventory_type
    return c

def _explore(dungeon="movement_tutorial"):
    return {"type": "exploration", "dungeon": dungeon}

def _ch(chapter_id, bgm, phases, rewards, meta):
    return {"id": chapter_id, "bgm": bgm, "phases": phases, "rewards": rewards}


# ═══════════════════════════════════════════════════════════════
# 제1막: 시공의 각성
# ═══════════════════════════════════════════════════════════════

def _gen_act1_prologue(m):
    return _ch("act1_prologue", "main_menu", [
        _cut([
            _seg("서기 2157년, 지구...", "white", 2.5),
            _seg("인류는 마침내 수백 년의 꿈을 이루어냈다.", "white", 2.0),
            _seg("전쟁은 역사책 속 이야기가 되었고,", "white", 1.5),
            _seg("기아와 질병도 먼 과거의 흔적만 남았다.", "white", 1.5),
            _seg("인류는 별들 사이를 여행하며,", "white", 1.5),
            _seg("우주 곳곳에 문명의 씨앗을 퍼뜨리기 시작했다.", "white", 2.0),
            _seg("이것이... 황금시대의 시작이었다.", "yellow", 3.0),
            _seg("그러나, 어떤 빛이 강렬할수록", "white", 1.5),
            _seg("그 그림자 또한 짙어지는 법...", "dark", 2.5),
            _seg("그 날 밤, 인류 최초의 차원 도약 실험이 시작되었다.", "white", 2.0),
            _seg("하지만...", "white", 1.5),
            _seg("하늘이 갈라졌다.", "red", 1.5),
            _seg("대지가 진동했다.", "red", 1.5),
            _seg("세계는 산산조각 났다.", "red", 2.0),
            _seg("『 시공교란 감지 』", "red", 2.0),
            _seg("『 원인 불명 』", "red", 1.5),
            _seg("『 타임라인 붕괴 진행 중... 』", "red", 2.5),
            _seg("과거와 미래가 뒤섞였다.", "white", 1.5),
            _seg("죽은 자가 살아 걸어다녔다.", "white", 1.5),
            _seg("태어나지 않은 자가 이미 늙어갔다.", "white", 2.0),
            _seg("모든 것이 무너졌다.", "dark", 2.5),
            _seg("...", "dark", 2.0),
            _seg("당신은 시공의 틈새에서 깨어난다.", "cyan", 2.0),
            _seg("기억은 흐릿하고, 현실은 불안정하다.", "cyan", 1.5),
            _seg("단 하나만이 확실하다—", "white", 1.5),
            _seg("이 세계를 구하려면, 시간의 흐름을 되돌려야 한다.", "yellow", 3.0),
            _seg("─── Dawn of Stellar ───", "cyan", 4.0),
        ]),
        _dlg("selena", [
            "...눈을 떠요. 들리나요?",
            "저는 셀레나. 시공의 안내자예요.",
            "시공 교란이 일어났어요. 모든 것이 뒤섞여버렸죠.",
            "과거의 전사가 미래의 땅을 걷고,",
            "미래의 과학자가 고대의 유적을 헤매고 있어요.",
            "당신이 여기에 온 것도 그 때문이에요.",
            "하지만 아직 희망이 있어요.",
            "당신에게서 특별한 힘을 느껴요.",
            "시간의 흐름을 되돌릴 수 있는 힘...",
            "먼저, 이 세계에서 움직이는 법을 알아야 해요.",
        ], effects=[None, None, "shake", None, None, None, None, None, "flash", None]),
        _dlg("selena", [
            "방향키(↑↓←→)로 이동할 수 있어요.",
            "Z키로 확인, X키로 취소할 수 있어요.",
            "화면에 보이는 기호들을 설명해드릴게요.",
            "'.' 은 바닥이에요. 걸어다닐 수 있죠.",
            "'#' 은 벽이에요. 통과할 수 없어요.",
            "'>' 은 아래로 향하는 계단이에요.",
            "계단을 찾아서 이동해보세요.",
        ]),
        _explore("prologue_awakening"),
        _dlg("selena", [
            "잘 해냈어요!",
            "이동의 기본을 마스터했네요.",
            "하지만 이 세계에는 위험한 존재들이 있어요.",
            "시공의 왜곡이 만들어낸 괴물들...",
            "곧 전투를 배워야 할 거예요.",
            "카르노스라는 전사가 도와줄 거예요.",
            "그는 3천 년 전의 전사인데, 시공 교란으로 이곳에 왔죠.",
            "거친 사람이지만 마음은 따뜻해요.",
            "준비가 되면 앞으로 나아가세요.",
        ], effects=[None, None, None, "slow", None, None, None, None, None]),
    ], {"star_fragments": 3, "message": "시공의 각성 — 이동의 기초를 마스터!"}, m)


def _gen_act1_ch1(m):
    return _ch("act1_ch1", "battle_normal", [
        _cut([
            _seg("시공의 틈새에서 무언가 다가온다...", "red", 2.0),
            _seg("왜곡된 에너지가 형체를 갖추기 시작한다.", "red", 1.5),
            _seg("─── 고대의 전사 ───", "yellow", 2.5),
        ]),
        _dlg("karnos", [
            "멈춰라.",
            "...",
            "적의 기운이 느껴진다.",
            "나는 카르노스. 3천 년 전의 전사다.",
            "시공 교란으로 이곳에 왔다.",
            "네가 시간을 되돌리려는 자인가.",
            "...셀레나에게 들었다.",
            "좋다. 전투의 기본을 알려주겠다.",
        ], effects=["slow", None, "shake", None, None, None, None, None]),
        _dlg("karnos", [
            "이 세계의 전투는 ATB(Active Time Battle)로 진행된다.",
            "화면 아래에 ATB 게이지가 보일 거다.",
            "게이지는 0에서 시작해서 천천히 차오른다.",
            "1000까지 차면 행동할 수 있다.",
            "2000까지 완전히 차면 행동력이 최대가 되지.",
            "속도(Speed)가 높을수록 게이지가 빨리 찬다.",
            "전투에서 가장 중요한 것은 타이밍이다.",
            "게이지가 차면 망설이지 말고 행동해라.",
        ]),
        _dlg("karnos", [
            "좋다. 첫 번째 적이 온다.",
            "일단 아무 공격이나 해서 감을 잡아봐라.",
            "BRV 공격부터 시작하는 것을 추천한다.",
        ], effects=["flash", None, None]),
        _explore("combat_training_arena"),
        _combat(
            [_enemy("시간 파편", 60, 40, 6, 3, 25)],
            [{"trigger": "first_turn", "text": "ATB 게이지가 찼습니다! 행동을 선택하세요.", "speaker": "karnos"}],
            "karnos", ["나쁘지 않군. 첫 전투치고는 괜찮았다.", "하지만 아직 갈 길이 멀다."],
        ),
        _dlg("karnos", [
            "전투의 기본을 느꼈나?",
            "ATB 게이지가 차면 행동하고, 다시 기다린다.",
            "이것이 전투의 리듬이다.",
            "하지만 아직 중요한 것을 안 알려줬다.",
            "BRV와 HP에 대해서 말이지.",
            "다음에 자세히 알려주겠다.",
            "일단 한 번 더 싸워보자. 이번엔 좀 더 강한 놈이다.",
        ]),
        _combat(
            [_enemy("왜곡된 그림자", 80, 50, 8, 4, 28)],
            [],
            "karnos", ["좋다. 전투의 감을 잡아가고 있군.", "다음 수업이 기대된다."],
        ),
    ], {"star_fragments": 5, "message": "ATB 전투 시스템의 기초를 습득!"}, m)


def _gen_act1_ch2(m):
    return _ch("act1_ch2", "battle_normal", [
        _dlg("karnos", [
            "왔군. 오늘은 공격에 대해 알려주겠다.",
            "이 세계의 공격은 두 종류가 있다.",
            "BRV(브레이브) 공격과 HP 공격이다.",
        ], effects=["slow", None, "flash"]),
        _dlg("karnos", [
            "BRV 공격은 적의 BRV를 깎고, 네 BRV를 올린다.",
            "BRV는 '용기'라고 생각하면 된다.",
            "BRV가 높을수록 강한 일격을 날릴 수 있지.",
        ]),
        _dlg("karnos", [
            "HP 공격은 네가 쌓은 BRV만큼 적에게 HP 데미지를 준다.",
            "BRV가 100이면 HP 공격으로 100 데미지를 주는 거다.",
            "HP 공격 후에는 BRV가 초기값으로 돌아간다.",
            "그러니까 순서가 중요해.",
        ]),
        _dlg("karnos", [
            "전략은 이렇다:",
            "1. BRV 공격으로 BRV를 최대한 쌓는다.",
            "2. BRV가 충분히 높으면 HP 공격으로 마무리한다.",
            "3. HP 공격 후에는 BRV가 리셋되니 다시 쌓아야 한다.",
            "이 사이클을 반복하는 거다.",
            "단순하지만 이것이 전투의 핵심이다.",
        ], effects=[None, None, None, None, None, "slow"]),
        _dlg("karnos", [
            "자, 직접 해봐라.",
            "먼저 BRV 공격을 2~3번 해서 BRV를 쌓고,",
            "그 다음 HP 공격으로 마무리하는 거다.",
        ]),
        _combat(
            [_enemy("시간의 잔영", 90, 50, 7, 3, 26)],
            [
                {"trigger": "first_turn", "text": "BRV 공격으로 BRV를 쌓으세요!", "forced_action": "brv_attack", "speaker": "karnos"},
                {"trigger": "after_brv_attack", "text": "좋아! 이제 HP 공격으로 데미지를 줘라!", "forced_action": "hp_attack", "speaker": "karnos"},
            ],
            "karnos", ["좋았다! BRV를 쌓고 HP 공격. 이 리듬을 기억해라."],
        ),
        _dlg("karnos", [
            "감을 잡았군.",
            "이번엔 자유롭게 싸워봐라. 두 마리다.",
            "BRV를 쌓고 HP 공격하는 사이클을 반복해라.",
        ]),
        _combat(
            [_enemy("왜곡된 눈", 70, 45, 8, 3, 30), _enemy("시간의 파편", 60, 40, 6, 2, 28)],
            [],
            "karnos", ["둘을 동시에 상대하는 것도 해냈군.", "다음엔 더 강력한 전투 기술을 알려주겠다."],
        ),
    ], {"star_fragments": 7, "message": "BRV와 HP 공격의 사이클을 마스터!"}, m)


def _gen_act1_ch3(m):
    return _ch("act1_ch3", "battle_normal", [
        _dlg("karnos", [
            "오늘 배울 것은 BREAK다.",
            "BREAK야말로 전투의 꽃이지.",
        ], effects=["slow", "flash"]),
        _dlg("karnos", [
            "적의 BRV를 0으로 만들면 'BREAK' 상태가 된다.",
            "BREAK되면 두 가지 일이 벌어진다.",
            "첫째, 네가 보너스 BRV를 얻는다.",
            "적의 초기 BRV만큼 추가로 받게 되지.",
            "둘째, BREAK된 적은 1턴 동안 행동할 수 없다.",
            "이 기회를 놓치면 안 된다.",
        ]),
        _dlg("karnos", [
            "BREAK 상태에서 HP 공격을 날리면",
            "보너스 BRV까지 합쳐진 막대한 데미지를 줄 수 있다.",
            "이것이 콤보의 핵심이다.",
            "BRV 공격 → BREAK → 보너스 BRV → HP 공격!",
            "이 연계를 기억해라.",
        ], effects=[None, None, None, "flash", None]),
        _dlg("karnos", [
            "반대로 네가 BREAK당할 수도 있다.",
            "네 BRV가 0이 되면 네가 BREAK된다.",
            "1턴 동안 행동 불능이 되니 절대 주의해라.",
            "BRV가 낮아지면 미리 방어로 버텨라.",
        ], effects=[None, None, "shake", None]),
        _combat(
            [_enemy("균열의 기사", 100, 60, 9, 5, 28)],
            [
                {"trigger": "first_turn", "text": "BRV 공격을 반복해서 적의 BRV를 0으로 만들어라!", "speaker": "karnos"},
                {"trigger": "enemy_brv_zero", "text": "★ BREAK! 지금이다! HP 공격으로 큰 데미지를 줘!", "speaker": "karnos"},
            ],
            "karnos", ["완벽하다! BREAK 연계를 성공시켰군!", "이제 네 실력이 올라가고 있다."],
        ),
        _dlg("karnos", [
            "좋았다. 하지만 실전은 이렇게 쉽지 않다.",
            "적도 BRV 공격을 해올 테니까.",
            "네 BRV를 관리하면서 적의 BREAK를 노려야 한다.",
            "이번엔 더 강한 적과 싸워보자.",
        ]),
        _combat(
            [_enemy("왜곡된 수호병", 120, 70, 10, 6, 30)],
            [],
            "karnos", ["적의 공격을 버티면서 BREAK를 노리는 것.", "이것이 진정한 전투의 기술이다."],
        ),
        _combat(
            [_enemy("시간의 사냥꾼", 100, 55, 12, 4, 35), _enemy("시간의 추적자", 80, 45, 9, 3, 32)],
            [],
            "karnos", ["두 마리를 상대하면서 BREAK까지 성공시키다니.", "네 재능이 보이기 시작한다."],
        ),
    ], {"star_fragments": 9, "message": "BREAK 시스템과 연계 공격을 마스터!"}, m)


def _gen_act1_ch5(m):
    return _ch("act1_ch5", "main_menu", [
        _cut([
            _seg("어두운 복도가 앞에 펼쳐진다...", "dark", 2.0),
            _seg("시공의 왜곡이 만들어낸 미로...", "white", 1.5),
        ]),
        _dlg("selena", [
            "이번에는 던전 탐험을 연습할 거예요.",
            "던전은 방과 복도로 이루어져 있어요.",
            "시야(FOV) 시스템이 있어서 주변만 볼 수 있어요.",
            "어둠 속에서는 뭐가 있는지 모르니 조심하세요.",
        ], effects=["slow", None, None, "shake"]),
        _dlg("selena", [
            "던전에는 다양한 것들이 있어요.",
            "'>' 계단: 다음 층으로 이동",
            "'+' 문: 열 수 있는 문",
            "'^' 함정: 밟으면 데미지!",
            "'*' 치유의 샘: HP를 회복해줘요",
            "'$' 보물상자: 아이템을 얻을 수 있어요",
        ]),
        _dlg("selena", [
            "바닥에 반짝이는 아이템이 있으면 Z키로 주울 수 있어요.",
            "준비됐나요? 던전에 들어가볼게요.",
        ]),
        _explore("dungeon_basics"),
        _dlg("selena", [
            "잘 했어요! 던전 탐험의 기본을 익혔네요.",
            "실전 던전에서는 적도 돌아다니고 있어요.",
            "적과 마주치면 자동으로 전투가 시작돼요.",
            "앞으로의 여정에서 많은 던전을 탐험하게 될 거예요.",
        ]),
        _combat(
            [_enemy("던전의 파수꾼", 90, 50, 8, 5, 27)],
            [],
            "selena", ["적을 처치했어요! 이제 다음으로 나아갈 수 있어요."],
        ),
    ], {"star_fragments": 8, "message": "던전 탐험의 기초를 마스터!"}, m)


def _gen_act1_boss(m):
    return _ch("act1_boss", "boss", [
        _cut([
            _seg("시공의 에너지가 집중된다...", "red", 2.0),
            _seg("거대한 존재의 기운이 느껴진다!", "red", 1.5),
            _seg("【 제1막 보스: 시간의 파수꾼 】", "red", 3.0),
        ]),
        _dlg("selena", [
            "앞에 강력한 적이 있어요!",
            "시간의 파수꾼... 시공 교란의 산물이에요.",
            "지금까지 배운 모든 것을 활용해야 해요!",
        ], effects=[None, None, "shake"]),
        _dlg("karnos", [
            "이건 장난이 아니다. 진짜 전투다.",
            "BRV를 쌓고, BREAK를 노리고, HP 공격으로 마무리.",
            "기본에 충실해라. 그게 답이다.",
            "적의 공격이 강하니 HP를 잘 관리해야 한다.",
            "위험하면 아이템을 쓰는 것도 전략이다.",
        ], effects=["slow", None, "flash", None, None]),
        _combat(
            [_enemy("시간의 파수꾼", 150, 150, 14, 7, 32)],
            [
                {"trigger": "first_turn", "text": "적의 BRV가 매우 높습니다! BRV 공격으로 BREAK를 꼭 노리세요!", "speaker": "selena"},
            ],
            "selena", [
                "해냈어요! 시간의 파수꾼을 쓰러뜨렸어요!",
                "정말 대단해요!",
            ],
        ),
        _dlg("selena", [
            "제1막의 시련을 넘었어요.",
            "당신은 ATB, BRV, HP 공격, BREAK를 모두 마스터했어요.",
            "하지만 이것은 시작에 불과해요.",
            "아직 배울 것이 많이 남아있어요.",
            "스킬, 파티, 장비, 요리...",
            "그리고... 세피로스와 카인의 비밀도.",
        ], effects=["flash", None, None, None, None, "slow"]),
        _cut([
            _seg("제1막 완료", "cyan", 1.5),
            _seg("시공의 각성 — 전투의 기초를 마스터하다", "yellow", 3.0),
        ]),
    ], {"star_fragments": 15, "message": "★ 제1막 완료! 전투의 기초를 완전히 마스터! ★"}, m)


# ═══════════════════════════════════════════════════════════════
# 제2막: 전사의 길
# ═══════════════════════════════════════════════════════════════

def _gen_act2_ch1(m):
    return _ch("act2_ch1", "battle_normal", [
        _cut([_seg("─── 제2막: 전사의 길 ───", "red", 3.0)]),
        _dlg("mira", [
            "안녕! 나는 미라, 시간의 마법사야.",
            "카르노스에게 전투의 기본을 배웠지?",
            "이제 내가 스킬에 대해 알려줄게.",
            "스킬은 MP(마나 포인트)를 소모해서 사용하는 특수 능력이야.",
        ], effects=["slow", None, None, "flash"]),
        _dlg("mira", [
            "스킬에는 여러 종류가 있어.",
            "공격 스킬: 강력한 데미지를 준다.",
            "지원 스킬: 아군을 강화한다.",
            "디버프 스킬: 적을 약화시킨다.",
            "회복 스킬: HP나 MP를 회복한다.",
        ]),
        _dlg("mira", [
            "MP는 한정되어 있으니 잘 관리해야 해.",
            "에테르로 회복할 수 있지만 아끼는 게 좋아.",
            "보스전을 위해 MP를 남겨둬야 하거든.",
        ]),
        _dlg("mira", [
            "그리고 캐스팅 시간이라는 게 있어.",
            "강력한 스킬일수록 시전하는 데 시간이 걸려.",
            "캐스팅 중에는 ATB가 멈추니까 타이밍이 중요해!",
            "자, 스킬을 사용해서 적을 물리쳐봐!",
        ], effects=[None, None, "flash", None]),
        _dlg("mira", [
            "참, 캐스팅 시스템에 대해 더 알려줄게.",
            "스킬마다 캐스팅 시간이 다르다는 것 알지?",
            "캐스팅 중에는 ATB가 멈추고 주문을 준비해.",
            "강력한 스킬일수록 캐스팅 시간이 길어.",
            "적이 캐스팅 중인 스킬은 방해할 수도 있어!",
            "타이밍을 잘 맞추는 게 정말 중요해.",
        ]),
        _combat(
            [_enemy("얼음 정령", 100, 45, 9, 5, 28, "ice")],
            [{"trigger": "first_turn", "text": "스킬 메뉴에서 공격 스킬을 사용해보세요!", "speaker": "mira"}],
            "mira", ["좋아! 스킬의 위력을 느꼈지?", "MP 관리만 잘 하면 정말 강력한 무기야."],
        ),
        _combat(
            [_enemy("번개 정령", 90, 50, 10, 4, 33, "lightning")],
            [],
            "mira", ["두 번째 적도 처치! 스킬 사용에 익숙해지고 있어."],
        ),
        _combat(
            [_enemy("화염 정령", 110, 55, 11, 5, 30, "fire")],
            [],
            "mira", ["세 마리의 정령을 모두 쓰러뜨렸어!", "이제 속성에 대해 알려줄게."],
        ),
    ], {"star_fragments": 10, "message": "스킬과 MP 관리를 습득!"}, m)


def _gen_act2_ch2(m):
    return _ch("act2_ch2", "battle_normal", [
        _dlg("mira", [
            "오늘은 속성에 대해 알려줄게.",
            "이 세계에는 8가지 속성이 있어.",
            "화, 빙, 뢰의 기본 3속성과 수, 지, 풍, 성, 암 속성이지.",
        ], effects=["slow", None, None]),
        _dlg("mira", [
            "적마다 속성에 대한 약점과 저항이 달라.",
            "약점 속성으로 공격하면 데미지가 크게 올라가!",
            "반대로 저항이 높은 속성은 데미지가 줄어들어.",
            "적의 색이나 이름으로 약점을 추측할 수 있어.",
        ], effects=[None, "flash", None, None, None]),
        _dlg("mira", [
            "적의 속성을 파악하고 맞는 스킬을 쓰는 게 핵심이야.",
            "빙결, 얼음 같은 이름은 빙속성 적이겠지?",
            "빙속성 적은 화속성에 약할 가능성이 높아.",
            "전투 중 다양한 속성 스킬로 약점을 찾아봐!",
        ]),
        _combat(
            [_enemy("빙결 기사", 120, 55, 10, 6, 29, "ice")],
            [{"trigger": "first_turn", "text": "적의 약점 속성을 찾아서 공격해보세요!", "speaker": "mira"}],
            "mira", ["완벽해! 약점 속성을 잘 찾아냈어!"],
        ),
        _combat(
            [_enemy("화염 마수", 130, 60, 11, 5, 31, "fire")],
            [{"trigger": "first_turn", "text": "화속성 적이야! 약점 속성을 찾아봐!", "speaker": "mira"}],
            "mira", ["맞아! 적의 약점을 찾아서 공격하는 거야!"],
        ),
        _combat(
            [_enemy("뇌전 용사", 140, 65, 12, 5, 34, "lightning"), _enemy("빙결 궁수", 100, 45, 9, 3, 30, "ice")],
            [],
            "mira", ["다른 속성의 적 두 마리를 동시에 상대하다니!", "상황에 맞게 스킬을 바꿔쓰는 게 중요해."],
        ),
    ], {"star_fragments": 12, "message": "속성과 약점 시스템을 마스터!"}, m)


def _gen_act2_ch3(m):
    return _ch("act2_ch3", "battle_normal", [
        _cut([_seg("시공의 틈새에서 새로운 동료가 나타난다...", "cyan", 2.0)]),
        _dlg("karnos", [
            "좋은 소식이다. 동료가 합류한다.",
            "이제부터 파티를 이뤄 싸우게 될 거다.",
            "파티원은 각자 ATB 게이지가 있다.",
            "게이지가 찬 캐릭터부터 순서대로 행동한다.",
        ], effects=["slow", None, None, None]),
        _dlg("karnos", [
            "파티 전투에서 중요한 것은 역할 분담이다.",
            "한 명은 BRV를 쌓고, 한 명은 HP 공격을 담당하면",
            "효율적인 연계가 가능하다.",
            "서로의 턴을 잘 활용하는 게 핵심이야.",
        ], effects=[None, None, None, "flash"]),
        _dlg("karnos", [
            "자, 둘이 함께 싸워보자!",
        ]),
        _combat(
            [_enemy("시간의 감시자", 150, 65, 12, 6, 30)],
            [{"trigger": "first_turn", "text": "파티원이 함께 싸웁니다! 각자의 턴을 활용하세요.", "speaker": "karnos"}],
            "karnos", ["둘이 합하면 전투가 훨씬 수월해지지.", "이것이 파티의 힘이다."],
        ),
        _combat(
            [_enemy("왜곡된 전사", 130, 55, 13, 5, 32), _enemy("왜곡된 궁수", 100, 45, 11, 3, 35)],
            [],
            "karnos", ["적이 여럿이어도 파티가 있으면 두렵지 않다."],
        ),
    ], {"star_fragments": 13, "message": "파티 전투 시스템을 습득!"}, m)


def _gen_act2_ch5(m):
    return _ch("act2_ch5", "battle_normal", [
        _dlg("karnos", [
            "오늘은 방어와 도주에 대해 알려주겠다.",
            "전투가 항상 유리하지는 않다.",
            "적의 공격이 너무 강하거나 HP가 위험할 때,",
            "방어를 선택하면 받는 데미지를 절반으로 줄일 수 있다.",
        ], effects=["slow", None, None, None]),
        _dlg("karnos", [
            "도주는 전투에서 도망치는 거다.",
            "하지만 보스전에서는 도주할 수 없으니 주의해라.",
            "체력 관리가 안 될 때는 차라리 도주하는 게 나을 수도 있다.",
            "무모한 용기는 어리석음일 뿐이다.",
        ]),
        _dlg("karnos", [
            "이번 적은 강하다. 적절히 방어와 공격을 섞어라.",
            "아이템도 쓸 줄 알아야 한다.",
        ]),
        _combat(
            [_enemy("시간의 집행자", 180, 70, 16, 8, 30)],
            [{"trigger": "turn_3", "text": "HP가 위험하면 방어나 아이템을 사용하세요!", "speaker": "karnos"}],
            "karnos", ["잘 버텼다! 살아남는 것이 이기는 것의 첫걸음이다."],
        ),
        _combat(
            [_enemy("어둠의 기사", 160, 60, 15, 7, 33), _enemy("어둠의 마법사", 120, 50, 12, 4, 36)],
            [],
            "karnos", ["둘 다 강했지만 네가 이겼다. 훌륭하다."],
        ),
    ], {"star_fragments": 14, "message": "방어와 위기 관리 전략을 마스터!"}, m)


def _gen_act2_ch6(m):
    return _ch("act2_ch6", "battle_normal", [
        _dlg("selena", [
            "이번에는 팀워크 게이지에 대해 알려드릴게요.",
            "전투 중 공격을 할 때마다 팀워크 게이지가 조금씩 차요.",
            "게이지가 가득 차면 강력한 합체기를 사용할 수 있어요!",
            "팀워크 궁극기는 파티 전원이 함께 공격하는 최강의 기술이에요.",
        ], effects=[None, None, None, "flash"]),
        _dlg("selena", [
            "팀워크 게이지를 빨리 채우려면",
            "BREAK를 성공시키거나 약점 공격을 하면 돼요.",
            "연계 공격이 잘 되면 게이지가 빨리 차죠.",
            "보스전에서 팀워크 궁극기를 아껴두는 것도 전략이에요.",
        ]),
        _combat(
            [_enemy("시간의 거인", 200, 80, 14, 8, 28)],
            [],
            "selena", ["팀워크의 힘을 느꼈나요?", "함께 싸우면 어떤 적도 이길 수 있어요!"],
        ),
        _combat(
            [_enemy("왜곡된 기사단장", 180, 70, 15, 7, 32), _enemy("왜곡된 기사", 130, 55, 12, 5, 30)],
            [],
            "selena", ["완벽한 팀워크였어요!"],
        ),
    ], {"star_fragments": 15, "message": "팀워크 게이지와 합체기를 마스터!"}, m)


def _gen_act2_boss(m):
    return _ch("act2_boss", "boss", [
        _cut([
            _seg("시공의 왜곡이 거대한 형상을 취한다...", "red", 2.0),
            _seg("과거의 전장에서 온 것인가...", "white", 1.5),
            _seg("【 제2막 보스: 왜곡된 장군 】", "red", 3.0),
        ]),
        _dlg("karnos", [
            "이건... 내가 아는 녀석이다.",
            "3천 년 전, 나와 싸웠던 장군이지.",
            "시공 교란이 그를 되살린 거다.",
            "하지만 완전체는 아니야. 왜곡되어 있지.",
            "스킬, 파티, BREAK, 아이템. 모든 것을 활용해라!",
        ], effects=["shake", "slow", "shake", None, None]),
        _combat(
            [_enemy("왜곡된 장군", 350, 100, 20, 10, 35, "fire")],
            [
                {"trigger": "first_turn", "text": "적은 화염 속성입니다! 약점 속성 스킬과 파티 팀워크를 활용하세요!", "speaker": "karnos"},
            ],
            "karnos", [
                "...해냈군.",
                "3천 년 전에 내가 그를 쓰러뜨릴 때도 이렇게 힘들었지.",
                "네가 해냈다. 대단하다.",
                "제2막의 시련을 넘었다.",
            ],
        ),
        _dlg("selena", [
            "정말 대단해요!",
            "이제 전투에 관해서는 웬만큼 알게 됐어요.",
            "다음은 이 세계의 다른 비밀들을 배울 거예요.",
            "장비, 요리, 아이템... 모두 중요한 것들이에요.",
        ]),
        _cut([
            _seg("제2막 완료", "cyan", 1.5),
            _seg("전사의 길 — 전투의 모든 것을 마스터하다", "yellow", 3.0),
        ]),
    ], {"star_fragments": 25, "message": "★ 제2막 완료! 전투 시스템을 완전히 마스터! ★"}, m)


# ═══════════════════════════════════════════════════════════════
# 제3막~5막: 간결하게 생성 (동일 패턴)
# ═══════════════════════════════════════════════════════════════

def _gen_standard_chapter(m, chapter_id, enemies_list, story_lines_before, story_lines_after):
    """범용 챕터 생성기 (대화 → 다중 전투 → 대화)"""
    npc = m.get("npc_guide", "selena")
    subtitle = m.get("subtitle", "")
    phases = [
        _cut([_seg(f"─── {m.get('title', '')} ───", "cyan", 2.0), _seg(subtitle, "yellow", 2.0)]),
    ]
    for idx, lines_block in enumerate(story_lines_before):
        if idx == 0 and lines_block:
            effects = ["slow"] + [None] * (len(lines_block) - 1)
            phases.append(_dlg(npc, lines_block, effects=effects))
        else:
            phases.append(_dlg(npc, lines_block))
    for i, enemies in enumerate(enemies_list):
        phases.append(_combat(enemies, [], npc,
            [f"{'전투 승리!' if i < len(enemies_list)-1 else '모든 적을 쓰러뜨렸습니다!'}"]))
    for lines_block in story_lines_after:
        phases.append(_dlg(npc, lines_block))
    return _ch(chapter_id, "battle_normal", phases,
        {"star_fragments": 12 + len(enemies_list) * 3,
         "message": f"{subtitle} 완료!"}, m)


def _gen_act3_ch1(m):
    return _gen_standard_chapter(m, "act3_ch1",
        [[_enemy("던전 가디언", 120, 55, 10, 6, 28)],
         [_enemy("장비 수호자", 140, 60, 12, 7, 30)]],
        [["안녕하시오. 나는 토르드, 대장장이다.", "장비에 대해 알려주겠소.",
          "장비는 무기, 방어구, 장신구 세 종류가 있소.", "무기는 공격력을, 방어구는 방어력을, 장신구는 특수 효과를 주지.",
          "좋은 장비는 전투를 완전히 바꿔놓소.", "같은 레벨이라도 장비에 따라 전투력이 두 배까지 차이나지.",
          "마을의 상점에서 구매하거나, 던전에서 발견할 수 있소.", "보물상자를 열심히 찾으시오."],
         ["장비의 스탯을 잘 봐야 하오.", "공격력, 방어력뿐만 아니라 속도, 마력 등도 중요하지.",
          "직업에 따라 필요한 스탯이 다르니 잘 판단하시오.", "자, 장비의 위력을 직접 체험해보시오."]],
        [["장비의 중요성을 알겠소?", "좋은 장비를 갖추면 훨씬 수월해질 것이오."]])

def _gen_act3_ch3(m):
    return _gen_standard_chapter(m, "act3_ch3",
        [[_enemy("슬라임 킹", 130, 50, 9, 8, 25)],
         [_enemy("독 식물", 100, 40, 11, 3, 30, "poison")]],
        [["아이템에 대해 알려주겠소.", "포션은 HP를 회복하고, 에테르는 MP를 회복하오.",
          "전투 중에도 아이템을 사용할 수 있소.", "아이템 턴을 쓰면 공격은 못 하지만 생존할 수 있지.",
          "특히 보스전에서 아이템은 생명줄이오.", "만반의 준비를 하고 전투에 임하시오.",
          "해독제, 각성제 같은 상태이상 회복 아이템도 중요하오.", "항상 여러 종류의 아이템을 챙기시오."]],
        [["아이템의 중요성을 느꼈소?", "전투 전에 인벤토리를 확인하는 습관을 들이시오."]])

def _gen_act3_ch5(m):
    """리나의 주방 - 요리"""
    return _ch("act3_ch5", "main_menu", [
        _dlg("lina", [
            "안녕~! 나는 리나, 요리사야!",
            "이 세계에서는 요리가 정말 중요해!",
            "전투 전에 맛있는 요리를 먹으면 강력한 버프를 받을 수 있거든.",
            "공격력 증가, 방어력 증가, 속도 증가... 다양한 효과가 있어!",
        ], effects=["slow", None, None, None]),
        _dlg("lina", [
            "요리는 4슬롯 냄비에 재료를 넣어 만들어!",
            "재료 조합에 따라 다른 요리가 완성돼!",
            "요리솥을 사용하면 HP/MP 회복량 +20%, 버프 지속시간 +20% 보너스!",
            "추가로 10% 확률로 같은 요리가 하나 더 나오기도 해~",
            "각 요리마다 다른 버프를 주니까 상황에 맞게 골라먹어야 해.",
            "보스전 전에 좋은 요리를 먹으면 정말 큰 차이가 나!",
        ]),
        {"type": "cooking", "npc": "lina",
         "intro_lines": ["자, 요리를 직접 만들어볼까~?"]},
        _dlg("lina", [
            "어때? 요리의 매력을 느꼈지?",
            "던전 탐험 중에 재료를 모아서 요리를 만들어봐~",
            "보스전 전에 좋은 요리를 먹으면 정말 큰 차이가 나!",
        ]),
    ], {"star_fragments": 15, "message": "요리 시스템을 습득!"}, m)

def _gen_act3_ch7(m):
    return _gen_standard_chapter(m, "act3_ch7",
        [[_enemy("채집 방해꾼", 100, 50, 9, 4, 30)],
         [_enemy("숲의 수호자", 150, 60, 13, 6, 28)],
         [_enemy("거대 버섯", 120, 45, 8, 10, 22)]],
        [["던전에서 재료를 채집할 수 있어!", "바닥에 반짝이는 식재료가 보이면 주워!",
          "채집 스킬이 높으면 더 좋은 재료를 얻을 수 있어.",
          "필드 스킬이라는 게 있는데, 직업마다 다른 필드 스킬을 가지고 있어.",
          "탐지(Detection) 스킬이 있으면 숨겨진 아이템을 찾을 수 있고,",
          "은밀(Stealth) 스킬이 있으면 적을 피해 이동할 수 있어.",
          "자, 재료를 모으러 가면서 적도 상대해보자!"]],
        [["재료를 잔뜩 모았네! 이걸로 맛있는 요리를 만들 수 있어!", "전투 전에 꼭 요리를 챙기는 습관을 들여~"]])

def _gen_act3_ch9(m):
    return _gen_standard_chapter(m, "act3_ch9",
        [[_enemy("독 전사", 140, 55, 14, 5, 32)],
         [_enemy("상처의 기사", 180, 70, 16, 8, 30)]],
        [["이번에 알려드릴 건 상처 시스템이에요.", "전투에서 큰 데미지를 받으면 '상처'가 생겨요.",
          "상처는 최대 HP를 영구적으로 줄여요.", "HP 데미지의 25%가 상처로 전환돼요.",
          "최대 HP의 50%까지 줄어들 수 있어요!", "상처는 치유의 샘이나 전용 아이템으로 낫게 할 수도 있지만,",
          "일반 포션을 사용했을 때, 최대 체력을 초과한 힐량의 일부가 상처 회복으로 전환되기도 해요!",
          "물론 가장 좋은 건 강한 공격을 방어로 피해를 최소화하는 거죠."]],
        [["장비 내구도에 대해서도 알려드릴게요.",
          "장비는 사용할수록 내구도가 줄어요.",
          "내구도가 낮아지면 장비 성능이 떨어져요.",
          "0이 되면 장비가 파손돼요!",
          "대장간에서 수리할 수 있으니 정기적으로 확인하세요."],
         ["상처의 위험성을 느꼈나요?", "앞으로는 데미지 관리가 정말 중요해질 거예요."]])

def _gen_act3_boss(m):
    return _ch("act3_boss", "boss", [
        _cut([
            _seg("시공의 맛이 뒤틀린다...", "yellow", 2.0),
            _seg("【 제3막 보스: 차원의 미식가 】", "red", 3.0),
        ]),
        _dlg("lina", [
            "어머! 이 녀석은 차원의 미식가야!",
            "시공 교란으로 만들어진 괴물인데...",
            "공격력이 엄청나서 금방 상처 입고 쓰러질 수 있어!",
            "장비를 잘 갖추고, 체력이 떨어지면 바로 아이템을 사용해!",
            "폭탄 같은 공격 아이템도 잊지 말고!",
        ], effects=["shake", None, "flash", None, None]),
        _combat(
            [_enemy("차원의 미식가", 450, 100, 25, 12, 33)],
            [{"trigger": "first_turn", "text": "위험하면 즉시 인벤토리(I)에서 포션을 사용하세요!", "speaker": "lina"}],
            "lina", ["해냈어! 정말 대단해!", "이 녀석을 이길 수 있다니!"],
            inventory_type="act3_boss"
        ),
        _cut([
            _seg("제3막 완료", "cyan", 1.5),
            _seg("세계의 비밀 — 장비, 요리, 아이템을 마스터하다", "yellow", 3.0),
        ]),
    ], {"star_fragments": 30, "message": "★ 제3막 완료! 세계의 시스템을 마스터! ★"}, m)


# 제4막
def _gen_act4_ch1(m):
    return _gen_standard_chapter(m, "act4_ch1",
        [[_enemy("함정 골렘", 130, 55, 11, 8, 26)],
         [_enemy("문지기", 150, 60, 13, 7, 29)]],
        [["이번에는 던전의 다양한 요소들을 배울 거예요.",
          "함정은 밟으면 데미지를 받아요. '^' 표시를 주의하세요!",
          "잠긴 문은 열쇠를 찾아야 열 수 있어요.", "열쇠는 같은 층 어딘가에 있을 거예요.",
          "비밀 문도 있어요. 벽을 자세히 살펴보면 발견할 수 있죠.",
          "비밀 통로 뒤에는 보물이 숨겨져 있을 수도 있어요!"]],
        [["던전의 다양한 요소를 배웠네요!", "앞으로는 더 복잡한 던전을 만나게 될 거예요."]])

def _gen_act4_ch2(m):
    return _gen_standard_chapter(m, "act4_ch2",
        [[_enemy("추적자", 140, 55, 14, 5, 38)],
         [_enemy("포위 기사 A", 110, 45, 12, 6, 32), _enemy("포위 기사 B", 110, 45, 12, 6, 32)]],
        [["던전의 적은 그냥 서 있는 게 아니에요.", "적에게는 AI가 있어요.",
          "추적(Chase): 플레이어를 발견하면 쫓아와요.", "포위(Flank): 여러 적이 포위하려 해요.",
          "신호(Signal): 한 적이 다른 적에게 알려요!", "시야 밖으로 벗어나면 적이 놓칠 수도 있어요.",
          "은밀하게 이동하거나 한 마리씩 유인하는 것도 전략이에요."]],
        [["적 AI를 이해하면 던전이 훨씬 수월해져요!"]])

def _gen_act4_ch3(m):
    return _gen_standard_chapter(m, "act4_ch3",
        [[_enemy("현상금 대상", 160, 65, 14, 6, 31)]],
        [["퀘스트 시스템에 대해 알려줄게!", "마을에서 퀘스트를 받을 수 있어.",
          "현상금 사냥: 특정 적을 처치하는 퀘스트", "수집: 재료를 모아오는 퀘스트",
          "탐험: 특정 층에 도달하는 퀘스트", "보스 토벌: 보스를 처치하는 퀘스트",
          "퀘스트를 완료하면 골드, 경험치, 별의 파편을 받아!",
          "별의 파편은 메타 진행에 사용되는 중요한 자원이야."]],
        [["퀘스트를 잘 활용하면 빠르게 성장할 수 있어!"]])

def _gen_act4_ch5(m):
    return _gen_standard_chapter(m, "act4_ch5",
        [[_enemy("전사 인형", 120, 50, 11, 7, 30)],
         [_enemy("마법사 인형", 100, 40, 14, 3, 35)],
         [_enemy("궁수 인형", 110, 45, 13, 4, 38)]],
        [["이 세계에는 35개의 직업이 있다.", "기사, 전사, 마법사, 궁수, 성직자, 암살자...",
          "각 직업마다 고유한 스킬과 스탯 성장이 다르다.",
          "전사는 HP와 공격력이 높고, 마법사는 마력이 높지.",
          "성직자는 회복에 특화되어 있고, 궁수는 속도가 빠르다.",
          "파티를 구성할 때 다양한 직업을 섞는 게 좋다.",
          "탱커, 딜러, 힐러의 밸런스가 중요하다."]],
        [["직업의 다양성을 느꼈나?", "에필로그에서 네 직업을 선택하게 될 거다."]])

def _gen_act4_ch6(m):
    return _gen_standard_chapter(m, "act4_ch6",
        [[_enemy("기믹 수련체", 150, 60, 13, 6, 31)],
         [_enemy("스탠스 전환자", 170, 70, 15, 7, 33)]],
        [["각 직업에는 '기믹'이라는 고유 시스템이 있어.",
          "전사: 6단계 스탠스를 전환하며 싸운다.", "검사: 검기를 모아서 폭발시킨다.",
          "기사: 의무 게이지를 채워 파티를 강화한다.", "마법사: 트릭 덱으로 카드를 조합해 효과를 발동한다.",
          "흡혈귀: 갈증 게이지를 관리하며 강해진다.", "차원술사: 차원 굴절로 피해를 지연시킨다!",
          "기믹을 잘 활용하면 전투력이 비약적으로 올라가!"]],
        [["기믹의 깊이를 느꼈지?", "각 직업의 기믹을 마스터하면 정말 강해질 수 있어."]])

def _gen_act4_boss(m):
    return _ch("act4_boss", "boss", [
        _cut([
            _seg("미궁의 깊은 곳에서 거대한 존재가 깨어난다...", "red", 2.0),
            _seg("【 제4막 보스: 미궁의 수호자 】", "red", 3.0),
        ]),
        _dlg("selena", [
            "이건 미궁의 최심부에 있는 수호자예요!",
            "지금까지 배운 모든 것을 총동원해야 해요!",
            "직업 기믹, 퀘스트 보상 아이템, 속성 약점...",
            "모든 지식이 필요해요!",
        ], effects=["shake", "flash", None, None]),
        _dlg("selena", [
            "이 보스에게는 기믹이 있어요!",
            "주기적으로 강화 모드에 들어가는데,",
            "그때는 방어가 크게 올라가요.",
            "강화 모드가 끝날 때까지 방어에 집중하고,",
            "해제되면 집중 공격하세요!",
        ], effects=["slow", None, None, None, "flash"]),
        _combat(
            [_enemy("미궁의 수호자", 600, 150, 20, 25, 34)],
            [
                {"trigger": "first_turn", "text": "적의 방어력이 엄청납니다! 직업 고유 기믹과 패시브를 최대한 활용하세요!", "speaker": "selena"}
            ],
            "selena", ["해냈어요! 미궁의 수호자를 쓰러뜨렸어요!", "이제 마지막 막만 남았어요..."],
        ),
        _cut([
            _seg("제4막 완료", "cyan", 1.5),
            _seg("시간의 미궁 — 던전과 직업의 비밀을 마스터하다", "yellow", 3.0),
        ]),
    ], {"star_fragments": 40, "message": "★ 제4막 완료! 던전과 직업 시스템을 마스터! ★"}, m)


# 제5막
def _gen_act5_ch1(m):
    return _gen_standard_chapter(m, "act5_ch1",
        [[_enemy("독 마법사", 140, 50, 12, 5, 32)],
         [_enemy("빙결 기사", 160, 60, 14, 8, 28, "ice")],
         [_enemy("혼란의 마녀", 130, 45, 15, 4, 36)]],
        [["이번에는 상태이상에 대해 알려줄게.",
          "이 세계에는 110종 이상의 상태이상이 있어!", "주요 버프: 헤이스트(속도 증가), 프로텍트(물방 증가), 쉘(마방 증가)",
          "주요 디버프: 슬로우(속도 감소), 포이즌(지속 데미지), 블라인드(명중 감소)",
          "치명적인 것들: 스턴(1턴 행동 불능), 수면(깨어날 때까지), 석화(영구 행동 불능!)",
          "상태이상은 전투의 판도를 바꿀 수 있어.", "적에게 디버프를 거는 것도 전략이고,",
          "아군에게 버프를 거는 것도 전략이야."]],
        [["상태이상의 세계는 정말 깊어.", "적절한 때에 적절한 상태이상을 활용하면 전투가 훨씬 쉬워져."]])

def _gen_act5_ch2(m):
    npc = m.get("npc_guide", "selena")
    subtitle = m.get("subtitle", "")
    return _ch("act5_ch2", "battle_normal", [
        _cut([_seg(f"─── {m.get('title', '')} ───", "cyan", 2.0), _seg(subtitle, "yellow", 2.0)]),
        _dlg(npc, ["이번에는 메타 진행에 대해 알려드릴게요.",
          "전투에서 승리하면 '별의 파편'을 얻을 수 있어요.",
          "별의 파편으로 할 수 있는 것들이에요:",
          "1. 새로운 직업 해금 (100~1000 조각)",
          "2. 영구 패시브 스킬 구매", "3. 특수 아이템 구매",
          "메타 진행은 게임을 반복할수록 강해지는 시스템이에요.",
          "처음에 30층을 클리어하지 못해도 괜찮아요.",
          "별의 파편을 모아서 점점 강해지면 되니까요."], effects=["slow", None, None, None, None, None, None, None, "flash"]),
        {"type": "shop", "npc": "selena", "shop_type": "star",
         "intro_lines": ["별조각 상점을 직접 체험해볼까요?"]},
        _combat([_enemy("별의 수호자", 170, 65, 14, 7, 31)], [], npc,
            ["모든 적을 쓰러뜨렸습니다!"]),
        _dlg(npc, ["메타 진행이 있어서 포기할 필요가 없어요!", "매번 조금씩 강해질 수 있으니까요."]),
    ], {"star_fragments": 15, "message": f"{subtitle} 완료!"}, m)

def _gen_act5_ch3(m):
    return _gen_standard_chapter(m, "act5_ch3",
        [[_enemy("시공의 기사", 180, 70, 16, 8, 33), _enemy("시공의 마법사", 140, 55, 18, 4, 36)],
         [_enemy("시공의 궁수", 150, 60, 17, 5, 40), _enemy("시공의 전사", 170, 65, 15, 9, 30), _enemy("시공의 암살자", 120, 50, 20, 3, 45)]],
        [["이제 고급 파티 전투를 연습할 거다.",
          "3~4인 파티로 다수의 적을 상대하는 거지.",
          "역할 분담이 핵심이다. 탱커가 적의 공격을 받고,",
          "딜러가 데미지를 넣고, 힐러가 회복한다.",
          "타겟팅도 중요해. 약한 적부터 처치하는 게 기본이지만,",
          "때로는 위협적인 적부터 처치하는 게 나을 때도 있다."]],
        [["다수 전투를 해냈군! 이제 어떤 상황이든 대처할 수 있다."]])

def _gen_act5_ch5(m):
    return _ch("act5_ch5", "danger", [
        _cut([
            _seg("시공의 깊은 곳에서 목소리가 들린다...", "red", 2.0),
            _seg("\"10만 번... 10만 번이나 봤다...\"", "red", 2.5),
            _seg("\"인류의 멸망을...\"", "red", 2.0),
        ]),
        _dlg("selena", [
            "...이 목소리는...",
            "세피로스... 시간 속에 갇힌 영혼이에요.",
            "닥터 아벨 카인이 만든 실험체...",
            "카인은 세피로스를 이용해서 10만 번의 타임라인을 반복했어요.",
            "모든 비극의 설계자예요.",
        ], effects=["slow", "shake", None, None, "flash"]),
        _dlg("selena", [
            "카인의 목적은 불멸이었어요.",
            "세피로스에게 시공간을 조작하게 하고,",
            "그 데이터를 모아서 자신의 의식을 시간에 고정시켰죠.",
            "이제 카인은 시간의 왕이에요.",
            "과거도, 현재도, 미래도 그의 손 안에 있어요.",
        ], effects=["slow", None, None, "shake", None]),
        _dlg("selena", [
            "세피로스는 자유를 원하고 있어요.",
            "\"날 막아줘... 날 멈춰줘...\"",
            "10만 번의 반복 끝에 그가 바라는 건 단 하나.",
            "해방이에요.",
            "당신이 그를 해방시킬 수 있어요.",
            "하지만 먼저... 당신은 더 강해져야 해요.",
        ], effects=[None, "shake", None, "flash", None, "slow"]),
        {"type": "boss_combat", "npc": "selena",
         "gimmick_lines": [
             "세피로스의 환영이에요!",
             "이 환영은 시간 조작 기믹을 사용해요.",
             "BREAK로 시간 조작을 중단시킬 수 있어요!",
         ],
         "timer_hint": 2,
         "enemies": [_enemy("세피로스의 환영", 250, 90, 18, 8, 36)],
         "combat_hints": [{"trigger": "first_turn", "text": "세피로스의 환영입니다! 전력을 다하세요!", "speaker": "selena"}],
         "victory_dialogue": {"npc": "selena", "lines": [
             "환영을 물리쳤어요...",
             "실제 세피로스는 이것보다 훨씬 강해요.",
             "20층에서 그를 만나게 될 거예요.",
             "그리고 30층에는 카인이...",
         ]},
        },
        _cut([
            _seg("\"별빛의 여명은, 가장 긴 밤 끝에서 찾아온다.\"", "yellow", 3.0),
            _seg("\"시간은 매정하지만 공평하다.\"", "cyan", 3.0),
        ]),
    ], {"star_fragments": 35, "message": "시공 교란의 진실을 알게 되었습니다."}, m)


def _gen_act5_ch7(m):
    return _ch("act5_ch7", "boss", [
        _cut([
            _seg("최후의 시련이 시작된다.", "red", 2.0),
            _seg("지금까지 배운 모든 것을 증명하라.", "yellow", 2.0),
        ]),
        _dlg("karnos", [
            "이것이 마지막 시련이다.",
            "연속 보스전. 쉬는 시간 없이 계속 싸운다.",
            "모든 것을 쏟아부어라!",
        ], effects=["slow", "shake", "flash"]),
        _combat([_enemy("시련의 기사", 200, 80, 16, 9, 32)], [], "karnos", ["첫 번째 통과!"]),
        _combat([_enemy("시련의 마법사", 180, 70, 20, 5, 38)], [], "mira", ["두 번째도 통과!"]),
        _combat([_enemy("시련의 장군", 280, 95, 18, 10, 34), _enemy("시련의 근위병", 150, 60, 14, 7, 30)], [],
            "selena", ["세 번째도 해냈어요!"]),
        _combat([_enemy("시련의 왕", 400, 120, 22, 12, 36)],
            [{"trigger": "first_turn", "text": "최종 시련! 모든 것을 걸으세요!", "speaker": "selena"}],
            "selena", [
                "해냈어요! 모든 시련을 통과했어요!",
                "당신은 이 세계에서 가장 강한 전사가 되었어요!",
            ]),
    ], {"star_fragments": 50, "message": "★ 최후의 시련을 돌파! ★"}, m)


def _gen_act5_finale(m):
    return _ch("act5_finale", "main_menu", [
        _cut([
            _seg("모든 시련을 극복한 당신 앞에", "white", 2.0),
            _seg("새로운 길이 펼쳐진다.", "white", 2.0),
            _seg("─── 별빛의 여명 ───", "cyan", 3.0),
        ]),
        _dlg("selena", [
            "정말 대단해요.",
            "모든 기본기와 고급 전략을 마스터했어요.",
            "이제 마지막으로 한 가지만 더.",
            "당신의 직업을 선택할 시간이에요.",
        ], effects=["slow", None, None, "flash"]),
        _dlg("selena", [
            "35개의 직업 중 하나를 선택하게 됩니다.",
            "전사, 마법사, 궁수, 성직자 같은 기본 직업부터",
            "암살자, 차원술사, 해커 같은 특수 직업까지.",
            "각 직업의 기믹과 특성을 잘 생각해서 선택하세요.",
        ], effects=[None, None, None, "slow"]),
        {"type": "job_select"},
        _dlg("selena", [
            "좋은 선택이에요!",
            "별의 파편도 드릴게요. 메타 진행에 사용하세요.",
        ]),
        _cut([
            _seg("시공의 균열이 점점 커지고 있다...", "red", 2.0),
            _seg("세피로스... 10만 번의 고통에서 해방시켜줘야 한다.", "red", 2.0),
            _seg("그리고 카인... 신이 되려 한 자를 쓰러뜨려야 한다.", "dark", 2.0),
            _seg("20층에서 세피로스와 마주한다.", "white", 2.0),
            _seg("30층에서 카인과 결전을 벌인다.", "white", 2.0),
            _seg("제한 시간 안에 쓰러뜨려야 한다!", "yellow", 2.0),
            _seg("", "white", 1.0),
            _seg("열 만 번째 밤이 시작된다.", "white", 2.0),
            _seg("하지만 이번엔 다를 것이다.", "white", 2.0),
            _seg("별빛의 여명은, 포기하지 않는 자에게 찾아온다.", "yellow", 3.0),
            _seg("", "white", 1.0),
            _seg("이제, 진짜 모험이 시작됩니다.", "cyan", 3.0),
            _seg("─── Dawn of Stellar ───", "cyan", 4.0),
        ]),
        _dlg("selena", [
            "모든 준비가 끝났어요.",
            "메인 메뉴에서 '새 게임'을 시작하면",
            "본격적인 모험이 펼쳐질 거예요.",
            "행운을 빌어요, 영웅이여.",
            "별빛의 여명이 당신과 함께하길...",
        ], effects=["slow", None, None, "flash", "slow"]),
    ], {"star_fragments": 100, "message": "★★★ 스토리 모드 완료! ★★★"}, m)


def _gen_generic(m, chapter_id):
    """알 수 없는 챕터용 범용 생성"""
    npc = m.get("npc_guide", "selena")
    subtitle = m.get("subtitle", chapter_id)
    learning = m.get("learning", "")
    return _ch(chapter_id, "battle_normal", [
        _cut([_seg(f"─── {m.get('title', '')} ───", "cyan", 2.0), _seg(subtitle, "yellow", 2.0)]),
        _dlg(npc, [f"이번 장에서는 {learning}에 대해 배웁니다.", "준비가 되면 시작하죠!"]),
        _combat([_enemy("시간의 왜곡체", 150, 60, 12, 6, 30)], [], npc, ["전투를 잘 해냈습니다!"]),
        _combat([_enemy("시공의 파편", 130, 50, 11, 5, 32), _enemy("시간의 잔영", 110, 45, 10, 4, 28)],
            [], npc, ["두 번째 전투도 승리!"]),
        _dlg(npc, ["이번 장의 내용을 잘 익혔습니다.", "다음 장에서 또 만나요!"]),
    ], {"star_fragments": 12, "message": f"{subtitle} 완료!"}, m)


# ── 신규 제1막 챕터 ──

def _gen_act1_ch4(m):
    """경험의 보상 - 경험치/레벨업 시스템"""
    return _ch("act1_ch4", "battle_normal", [
        _dlg("karnos", [
            "오늘은 경험치에 대해 알려주겠다.",
            "전투에서 승리하면 경험치(EXP)를 얻는다.",
            "경험치가 일정량 쌓이면 레벨이 오른다.",
            "레벨이 오르면 모든 스탯이 상승하지.",
            "HP, MP, 공격력, 방어력, 속도... 전부 다.",
        ]),
        _dlg("karnos", [
            "레벨업은 전투력을 높이는 가장 기본적인 방법이다.",
            "강한 적일수록 더 많은 경험치를 주지.",
            "보스를 쓰러뜨리면 대량의 경험치를 얻을 수 있다.",
            "자, 적을 쓰러뜨리고 레벨업을 체험해봐라!",
        ]),
        _explore("dungeon_basics"),
        _combat(
            [_enemy("연습 인형 A", 70, 40, 7, 3, 25), _enemy("연습 인형 B", 70, 40, 7, 3, 25)],
            [{"trigger": "first_turn", "text": "적을 쓰러뜨려서 경험치를 얻으세요!", "speaker": "karnos"}],
            "karnos", ["좋다! 경험치를 얻었군.", "레벨업 시 스탯 변화를 확인해봐라."],
        ),
        _dlg("karnos", [
            "레벨이 오르면 새로운 스킬도 배울 수 있다.",
            "직업마다 배우는 스킬이 다르니 잘 확인해라.",
            "경험치를 많이 모을수록 강해진다. 기억해둬라.",
        ]),
    ], {"star_fragments": 7, "message": "경험치와 레벨업 시스템을 습득!"}, m)


def _gen_act1_ch6(m):
    """기억의 보존 - 저장/로드 시스템"""
    return _ch("act1_ch6", "main_menu", [
        _dlg("selena", [
            "이번에는 저장과 로드에 대해 알려드릴게요.",
            "본 게임은 로그라이크 요소가 있어요.",
            "던전에서 쓰러지면 일부 진행을 잃을 수 있죠.",
            "그래서 저장이 정말 중요해요!",
        ], effects=["slow", None, None, "flash"]),
        _dlg("selena", [
            "저장 포인트는 던전 곳곳에 있어요.",
            "'S' 표시가 저장 포인트예요.",
            "저장 포인트에서 Z키를 누르면 저장할 수 있어요.",
            "여러 슬롯에 저장할 수 있으니 자주 저장하세요!",
        ]),
        {"type": "save_load", "npc": "selena",
         "intro_lines": ["한번 저장 화면을 체험해볼까요?"]},
        _dlg("selena", [
            "스토리 모드에서는 챕터 완료 시 자동 저장돼요.",
            "하지만 본 게임에서는 직접 저장해야 해요.",
            "저장을 깜빡하면 진행을 잃을 수 있으니 주의하세요!",
            "치유의 샘이나 계단을 발견하면 저장하는 습관을 들이세요.",
        ]),
    ], {"star_fragments": 6, "message": "저장/로드 시스템을 습득!"}, m)


# ── 신규 제2막 챕터 ──

def _gen_act2_ch4(m):
    """소지품 정리 - 인벤토리/무게 시스템"""
    return _ch("act2_ch4", "main_menu", [
        _dlg("tord", [
            "소지품 관리에 대해 알려주겠소.",
            "인벤토리에는 무게 제한이 있소.",
            "너무 많은 아이템을 들고 다니면 이동이 느려지지.",
            "필요한 것만 챙기고 나머지는 정리하는 게 좋소.",
        ], effects=["slow", None, None, None]),
        _dlg("tord", [
            "아이템은 여러 종류가 있소.",
            "소모품: 포션, 에테르, 해독제 등",
            "장비: 무기, 방어구, 장신구",
            "재료: 요리나 강화에 쓰이는 것들",
            "각각 무게가 다르니 잘 관리하시오.",
        ]),
        {"type": "inventory", "npc": "tord",
         "intro_lines": ["인벤토리를 직접 살펴보시오."]},
        _dlg("tord", [
            "전투에서 얻은 전리품도 인벤토리에 들어가오.",
            "무게를 잘 관리하시오.",
            "필요 없는 건 버리거나 창고에 맡기면 되오.",
        ]),
    ], {"star_fragments": 10, "message": "인벤토리와 무게 시스템을 습득!"}, m)


def _gen_act2_ch7(m):
    """도전의 강도 - 난이도 설정"""
    return _ch("act2_ch7", "main_menu", [
        _dlg("selena", [
            "본 게임에는 5가지 난이도가 있어요.",
            "평온: 차원의 흐름이 안정된 여유로운 탐험. 스토리만 즐기고 싶을 때.",
            "보통: 균형 잡힌 도전과 보상. 기본 난이도예요.",
            "도전: 차원의 흐름이 불안정! 더 강한 적과 더 많은 보상.",
            "악몽: 차원이 크게 왜곡! 전략이 필수예요.",
            "지옥: 붕괴 직전의 차원! 극한의 도전과 최고의 보상!",
        ], effects=["slow", None, None, None, None, "flash"]),
        _dlg("selena", [
            "난이도가 높을수록 적이 강해지지만",
            "경험치와 골드 보상이 더 많아져요.",
            "희귀 아이템 드롭률도 올라가고요!",
            "자신의 실력에 맞는 난이도를 선택하세요.",
        ]),
        {"type": "difficulty_select", "npc": "selena"},
        _combat(
            [_enemy("난이도 시험관", 140, 55, 12, 6, 30)],
            [],
            "selena", ["이 전투의 난이도가 체감이 되나요?", "본 게임에서 자유롭게 조절할 수 있어요!"],
        ),
    ], {"star_fragments": 11, "message": "난이도 시스템을 습득!"}, m)


# ── 신규 제3막 챕터 ──

def _gen_act3_ch2(m):
    """강화의 기술 - 대장간/재연마"""
    return _ch("act3_ch2", "main_menu", [
        _dlg("tord", [
            "장비 강화에 대해 알려주겠소.",
            "대장간에서 장비를 강화하면 능력치가 올라가오.",
            "강화에는 강화석이 필요하지.",
            "+1, +2, +3... 강화할수록 더 강해지오.",
            "하지만 높은 강화 단계에서는 실패할 수도 있소!",
        ], effects=["slow", None, None, None, "flash"]),
        _dlg("tord", [
            "재연마는 장비의 접사를 무작위로 바꾸는 거오.",
            "좋은 접사가 붙으면 전투를 완전히 바꿔놓지.",
            "250골드면 재연마할 수 있으니 좋은 효과가 나올 때까지 도전해보시오.",
        ]),
        {"type": "anvil", "npc": "tord",
         "intro_lines": ["자, 대장간에서 직접 강화해보시오."]},
        _dlg("tord", [
            "장비에는 내구도가 있소.",
            "전투를 할수록 내구도가 줄어들지.",
            "내구도가 0이 되면 장비가 망가지니 주의하시오.",
            "대장간에서 수리할 수 있으니 정기적으로 오시오.",
        ], effects=[None, None, "shake", None]),
        _dlg("tord", [
            "강화된 장비의 위력은 전투에서 직접 느낄 수 있을 거오.",
            "좋은 장비를 강화하면 보스도 두렵지 않소.",
        ]),
    ], {"star_fragments": 14, "message": "대장간 강화와 재연마를 습득!"}, m)


def _gen_act3_ch4(m):
    """연금술의 세계 - 연금술"""
    return _ch("act3_ch4", "main_menu", [
        _dlg("mira", [
            "연금술에 대해 알려줄게!",
            "연금술은 레시피에 맞는 재료를 조합해 포션을 만드는 거야.",
            "50가지가 넘는 포션 레시피가 있어!",
            "제조할 때 10% 확률로 걸작이 나오면 효과가 30% 증가해!",
            "연금술사 직업이면 걸작 확률이 더 올라가지.",
        ], effects=["slow", None, None, None, None]),
        _dlg("mira", [
            "포션도 연금술로 만들 수 있어!",
            "HP 포션, MP 포션, 해독제, 각성제...",
            "상점에서 사는 것보다 직접 만드는 게 경제적이지.",
            "레시피를 모을수록 만들 수 있는 것들이 늘어나!",
        ]),
        {"type": "alchemy", "npc": "mira",
         "intro_lines": ["자, 연금술을 직접 체험해볼까?"]},
        _dlg("mira", [
            "잘했어! 이제 연금술의 기본을 배웠네.",
            "재료를 잘 모아서 다양한 것들을 만들어봐!",
            "전투 전에 포션을 준비해두면 큰 도움이 될 거야.",
        ]),
    ], {"star_fragments": 15, "message": "연금술 시스템을 습득!"}, m)


def _gen_act3_ch6(m):
    """폭발의 기술 - 폭탄 제작"""
    return _ch("act3_ch6", "battle_normal", [
        _dlg("lina", [
            "폭탄에 대해 알려줄게!",
            "폭탄은 범위 공격이 가능한 소모품이야.",
            "화염 폭탄: 넓은 범위에 화염 데미지!",
            "얼음 폭탄: 적을 얼려서 행동을 늦춰!",
            "번개 폭탄: 연쇄 데미지로 다수 처치!",
            "독 폭탄: 지속 데미지로 강적 상대!",
        ], effects=["slow", None, None, None, None, "flash"]),
        _dlg("lina", [
            "폭탄 제작에는 재료가 필요해.",
            "화약, 도화선은 기본이고,",
            "속성 재료에 따라 폭탄 종류가 달라져.",
            "던전에서 재료를 잘 모아둬!",
        ]),
        {"type": "bomb_craft", "npc": "lina",
         "intro_lines": ["자, 폭탄을 한번 만들어볼까?"]},
        _combat(
            [_enemy("폭탄 연습용 허수아비 A", 80, 30, 5, 3, 20),
             _enemy("폭탄 연습용 허수아비 B", 80, 30, 5, 3, 20),
             _enemy("폭탄 연습용 허수아비 C", 80, 30, 5, 3, 20)],
            [{"trigger": "first_turn", "text": "폭탄으로 한꺼번에 쓸어버려!", "speaker": "lina"}],
            "lina", ["범위 공격의 위력을 느꼈지?", "잡몹이 많을 때 폭탄이 정말 유용해!"],
            inventory_type="bomb_combat",
        ),
    ], {"star_fragments": 14, "message": "폭탄 제작과 범위 공격을 습득!"}, m)


def _gen_act3_ch8(m):
    """상인의 길 - 골드/별조각 상점"""
    return _ch("act3_ch8", "main_menu", [
        _dlg("tord", [
            "상점에 대해 알려주겠소.",
            "골드 상점에서는 골드로 장비와 아이템을 살 수 있소.",
            "골드는 전투 승리, 보물상자, 퀘스트로 얻지.",
            "좋은 장비는 비싸지만 그만한 가치가 있소.",
        ], effects=["slow", None, None, None]),
        {"type": "shop", "npc": "tord", "shop_type": "gold", "gold": 500,
         "intro_lines": ["자, 골드 상점을 둘러보시오."]},
        _dlg("selena", [
            "별조각 상점도 있어요!",
            "별의 파편으로 특별한 아이템을 살 수 있어요.",
            "직업 해금, 영구 패시브, 희귀 장비...",
            "별의 파편은 스토리 모드와 던전 클리어로 얻을 수 있어요.",
        ], effects=[None, None, None, "flash"]),
        {"type": "shop", "npc": "selena", "shop_type": "star",
         "intro_lines": ["별조각 상점도 살펴볼까요?"]},
    ], {"star_fragments": 16, "message": "골드 상점과 별조각 상점을 습득!"}, m)


# ── 신규 제4막 챕터 ──

def _gen_act4_ch4(m):
    """모험가의 전당 - 길드 홀/도전과제"""
    return _ch("act4_ch4", "main_menu", [
        _dlg("selena", [
            "길드 홀에 대해 알려드릴게요.",
            "길드 홀에서는 다양한 도전과제를 확인할 수 있어요.",
            "도전과제를 달성하면 특별한 보상을 받을 수 있죠!",
        ], effects=["slow", None, None]),
        _dlg("selena", [
            "마일스톤이라는 큰 목표도 있어요.",
            "예: '100마리 처치', '10층 도달', '5개 직업 해금' 등",
            "마일스톤을 달성하면 영구적인 보상을 받아요!",
            "별의 파편, 새로운 스킬, 특수 장비 등이 있죠.",
        ], effects=[None, None, None, "flash"]),
        {"type": "guild_hall", "npc": "selena",
         "intro_lines": ["길드 홀을 직접 둘러볼까요?"]},
        _dlg("selena", [
            "도전과제는 자연스럽게 달성되는 것도 있고,",
            "의식적으로 노력해야 하는 것도 있어요.",
            "길드 홀을 자주 방문해서 진행도를 확인하세요!",
        ]),
    ], {"star_fragments": 18, "message": "길드 홀과 도전과제 시스템을 습득!"}, m)


def _gen_act4_ch7(m):
    """전사들의 편대 - 파티 구성 UI"""
    return _ch("act4_ch7", "main_menu", [
        _dlg("karnos", [
            "파티 편성에 대해 알려주겠다.",
            "본 게임에서는 최대 4명의 파티를 구성할 수 있다.",
            "파티 구성의 핵심은 역할 분담이다.",
        ], effects=["slow", None, None]),
        _dlg("karnos", [
            "탱커: 기사, 성기사, 전사 등. 적의 공격을 받아낸다.",
            "딜러: 검사, 마법사, 궁수 등. 주력 데미지를 넣는다.",
            "힐러: 성직자, 드루이드 등. 아군을 회복한다.",
            "버퍼: 음유시인, 주술사 등. 아군을 강화한다.",
            "이 4가지 역할의 균형이 중요하다.",
        ], effects=[None, None, None, None, "flash"]),
        {"type": "party_setup", "npc": "karnos",
         "intro_lines": ["자, 파티를 직접 편성해봐라."]},
        _combat(
            [_enemy("편대 시험 전사", 160, 60, 13, 7, 30),
             _enemy("편대 시험 마법사", 120, 45, 16, 3, 35)],
            [],
            "karnos", ["편성한 파티로 전투를 해봤다.", "역할 분담이 잘 되면 어떤 적이든 이길 수 있다."],
        ),
    ], {"star_fragments": 20, "message": "파티 구성과 역할 분담을 습득!"}, m)


# ── 신규 제5막 챕터 ──

def _gen_act5_ch4(m):
    """시간의 심판 - 보스 기믹/타이머"""
    return _ch("act5_ch4", "boss", [
        _dlg("selena", [
            "보스 기믹에 대해 알려드릴게요.",
            "강력한 보스에게는 특별한 기믹이 있어요.",
            "약점 노출: 특정 조건에서만 데미지가 들어가요.",
            "패턴 공격: 규칙적인 강력 공격을 피해야 해요.",
            "부위 파괴: 보스의 특정 부위를 파괴하면 약화돼요.",
        ], effects=["slow", None, None, None, None]),
        _dlg("selena", [
            "그리고 타이머 보스도 있어요!",
            "제한 시간 내에 쓰러뜨려야 하는 보스죠.",
            "세피로스와 카인이 바로 타이머 보스예요.",
            "DPS(초당 데미지)를 최대화하는 전략이 필요해요.",
            "버프, 디버프, BREAK 연계를 모두 활용해야 해요!",
        ], effects=["flash", None, None, None, "shake"]),
        {"type": "boss_combat", "npc": "selena",
         "gimmick_lines": [
             "이 보스는 약점 노출 기믹이 있어요!",
             "BRV를 0으로 만들면(BREAK) 약점이 노출돼요.",
             "약점 노출 중에 HP 공격을 집중하세요!",
         ],
         "timer_hint": 3,
         "enemies": [_enemy("기믹 연습 보스", 300, 90, 16, 8, 32)],
         "combat_hints": [
             {"trigger": "first_turn", "text": "BREAK로 약점을 노출시키세요!", "speaker": "selena"},
         ],
        },
        _dlg("selena", [
            "잘 해냈어요! 기믹을 공략하는 감을 잡았네요.",
            "실전 보스는 더 복잡한 기믹을 가지고 있어요.",
            "패턴을 관찰하고, 타이밍을 맞추는 게 중요해요.",
            "세피로스전에서는 7분 30초, 카인전에서는 4분 4초의 시간 제한이 있어요!",
        ], effects=[None, None, None, "flash"]),
    ], {"star_fragments": 30, "message": "보스 기믹과 타이머 전략을 습득!"}, m)


def _gen_act5_ch6(m):
    """함께하는 모험 - 멀티플레이 소개"""
    return _ch("act5_ch6", "main_menu", [
        _dlg("selena", [
            "마지막으로 멀티플레이에 대해 알려드릴게요!",
            "Dawn of Stellar에는 2~4인 협동 멀티플레이가 있어요.",
            "WebSocket 기반으로 친구들과 함께 던전을 탐험할 수 있죠!",
        ], effects=["slow", None, None]),
        _dlg("selena", [
            "멀티플레이에서는 한 명이 호스트가 되어 세션을 만들어요.",
            "다른 플레이어들이 세션에 접속하면 함께 모험을 시작하죠.",
            "최대 4명까지 동시에 플레이할 수 있어요!",
        ]),
        _dlg("selena", [
            "같은 던전을 함께 탐험하고,",
            "누군가 적과 마주치면 근처 플레이어가 전투에 합류할 수 있어요!",
            "각자 자기 캐릭터의 턴을 조작해요.",
            "역할 분담이 확실해져서 더 깊은 전략이 가능하죠.",
        ]),
        _dlg("selena", [
            "전리품은 선점 방식이에요.",
            "먼저 줍는 사람이 가져가지만, 창고는 공유할 수 있어요.",
            "인벤토리 무게도 멀티플레이에서는 70% 늘어나서",
            "여러 명이 나눠 들 수 있도록 배려되어 있어요.",
        ]),
        _dlg("selena", [
            "멀티플레이는 메인 메뉴에서 접근할 수 있어요.",
            "'멀티플레이어' 메뉴를 선택하면 돼요.",
            "혼자서도 충분히 즐길 수 있지만,",
            "친구와 함께하면 더 재미있을 거예요!",
        ]),
    ], {"star_fragments": 20, "message": "멀티플레이 시스템을 배웠습니다!"}, m)


# 챕터 ID → 생성기 맵핑
CHAPTER_GENERATORS = {
    # 제1막 (8챕터)
    "act1_prologue": _gen_act1_prologue,
    "act1_ch1": _gen_act1_ch1,
    "act1_ch2": _gen_act1_ch2,
    "act1_ch3": _gen_act1_ch3,
    "act1_ch4": _gen_act1_ch4,      # NEW: 경험의 보상
    "act1_ch5": _gen_act1_ch5,      # was act1_ch4: 어둠의 복도
    "act1_ch6": _gen_act1_ch6,      # NEW: 기억의 보존
    "act1_boss": _gen_act1_boss,
    # 제2막 (8챕터)
    "act2_ch1": _gen_act2_ch1,
    "act2_ch2": _gen_act2_ch2,
    "act2_ch3": _gen_act2_ch3,
    "act2_ch4": _gen_act2_ch4,      # NEW: 소지품 정리
    "act2_ch5": _gen_act2_ch5,      # was act2_ch4: 방어의 기술
    "act2_ch6": _gen_act2_ch6,      # was act2_ch5: 팀워크의 힘
    "act2_ch7": _gen_act2_ch7,      # NEW: 도전의 강도
    "act2_boss": _gen_act2_boss,
    # 제3막 (10챕터)
    "act3_ch1": _gen_act3_ch1,
    "act3_ch2": _gen_act3_ch2,      # NEW: 강화의 기술
    "act3_ch3": _gen_act3_ch3,      # was act3_ch2: 아이템의 지혜
    "act3_ch4": _gen_act3_ch4,      # NEW: 연금술의 세계
    "act3_ch5": _gen_act3_ch5,      # was act3_ch3: 리나의 주방
    "act3_ch6": _gen_act3_ch6,      # NEW: 폭발의 기술
    "act3_ch7": _gen_act3_ch7,      # was act3_ch4: 재료 사냥꾼
    "act3_ch8": _gen_act3_ch8,      # NEW: 상인의 길
    "act3_ch9": _gen_act3_ch9,      # was act3_ch5: 상처와 치유
    "act3_boss": _gen_act3_boss,
    # 제4막 (8챕터)
    "act4_ch1": _gen_act4_ch1,
    "act4_ch2": _gen_act4_ch2,
    "act4_ch3": _gen_act4_ch3,
    "act4_ch4": _gen_act4_ch4,      # NEW: 모험가의 전당
    "act4_ch5": _gen_act4_ch5,      # was act4_ch4: 직업의 각성
    "act4_ch6": _gen_act4_ch6,      # was act4_ch5: 기믹의 진수
    "act4_ch7": _gen_act4_ch7,      # NEW: 전사들의 편대
    "act4_boss": _gen_act4_boss,
    # 제5막 (8챕터)
    "act5_ch1": _gen_act5_ch1,
    "act5_ch2": _gen_act5_ch2,
    "act5_ch3": _gen_act5_ch3,
    "act5_ch4": _gen_act5_ch4,      # NEW: 시간의 심판
    "act5_ch5": _gen_act5_ch5,      # was act5_ch4: 10만 번째 밤
    "act5_ch6": _gen_act5_ch6,      # NEW: 함께하는 모험
    "act5_ch7": _gen_act5_ch7,      # was act5_ch5: 최후의 시련
    "act5_finale": _gen_act5_finale,
}
