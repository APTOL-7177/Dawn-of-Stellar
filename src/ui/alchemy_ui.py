"""
연금술 실험실 UI

포션과 폭탄을 제작할 수 있는 전용 UI
"""

import tcod.console
import tcod.event
from typing import List, Optional, Any, Dict
from enum import Enum

from src.equipment.inventory import Inventory
from src.equipment.item_system import ItemType
from src.gathering.ingredient import Ingredient, IngredientCategory, IngredientDatabase
from src.cooking.potion_brewing import PotionDatabase, PotionRecipe, PotionBrewer, PotionType, CraftResult
from src.cooking.bomb_crafting import BombDatabase, BombRecipe, BombCrafter, BombType
from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler, unified_input_handler
from src.ui.pointer import PointerButton, PointerDispatchResult, PointerDispatcher, PointerEvent, PointerEventKind, PointerRegion
from src.equipment.item_system import ItemGenerator
from src.core.logger import get_logger
from src.audio import play_sfx


logger = get_logger("alchemy_ui")

# 희귀도별 색상
RARITY_COLORS = {}
try:
    from src.equipment.item_system import ItemRarity
    RARITY_COLORS = {
        ItemRarity.COMMON: (200, 200, 200),      # 회색
        ItemRarity.UNCOMMON: (100, 255, 100),     # 초록
        ItemRarity.RARE: (100, 150, 255),         # 파랑
        ItemRarity.EPIC: (200, 100, 255),         # 보라
        ItemRarity.LEGENDARY: (255, 200, 50),     # 금색
        ItemRarity.UNIQUE: (255, 100, 100),       # 빨강
    }
except Exception:
    pass


def _get_effect_summary(recipe) -> str:
    """레시피의 효과 요약 문자열 생성"""
    try:
        # 포션 레시피
        if hasattr(recipe, 'potion_id'):
            from src.equipment.item_system import CONSUMABLE_TEMPLATES
            tmpl = CONSUMABLE_TEMPLATES.get(recipe.potion_id, {})
            etype = tmpl.get('effect_type', '')
            evalue = tmpl.get('effect_value', 0)
            duration = tmpl.get('duration', 0)

            if etype == 'heal_hp':
                return f"HP+{evalue}"
            elif etype == 'heal_mp':
                return f"MP+{evalue}"
            elif etype == 'heal_both':
                return f"HP/MP+{evalue}"
            elif etype == 'shield':
                return f"보호막 {evalue}"
            elif etype == 'buff_strength':
                return f"공+{evalue} {duration}턴"
            elif etype == 'buff_defense':
                return f"방+{evalue} {duration}턴"
            elif etype == 'buff_speed':
                return f"속+{evalue}% {duration}턴"
            elif etype == 'buff_regen':
                return f"재생 {evalue}/턴"
            elif etype == 'buff_berserk':
                return f"광폭화 {duration}턴"
            elif etype == 'buff_resistance':
                return f"저항+{evalue}%"
            elif etype == 'buff_luck':
                return f"크리+{evalue}%"
            elif etype == 'buff_invisibility':
                return f"회피+{evalue}%"
            elif etype == 'buff_lifesteal':
                return f"흡혈 {evalue}%"
            elif etype == 'buff_mana_shield':
                return f"마나방어 {evalue}%"
            elif etype == 'buff_crit_boost':
                return f"크리강화 {duration}턴"
            elif etype == 'buff_battle_trance':
                return f"무아경 {duration}턴"
            elif etype == 'buff_bonus_damage':
                return f"추가피해 {evalue}%"
            elif 'cure' in etype or 'cleanse' in etype:
                return "상태이상 치료"
            elif etype == 'damage_reduction':
                return f"피해감소 {evalue}%"
            elif etype == 'heal_wound':
                return f"상처치료 {evalue}"
            elif evalue > 0:
                return f"효과 {evalue}"
            # 템플릿에 없으면 레시피 effects에서 추출
            effects = getattr(recipe, 'effects', {})
            if effects.get('hp_restore'):
                return f"HP+{effects['hp_restore']}"
            if effects.get('mp_restore'):
                return f"MP+{effects['mp_restore']}"
            return ""
        # 폭탄 레시피
        elif hasattr(recipe, 'bomb_id'):
            dmg = getattr(recipe, 'damage', 0)
            bomb_type = getattr(recipe, 'bomb_type', None)
            element = ""
            if bomb_type:
                type_map = {'fire': '화', 'ice': '빙', 'lightning': '뇌', 'poison': '독', 'explosive': '폭발', 'special': '특수'}
                element = type_map.get(str(bomb_type.value).lower() if hasattr(bomb_type, 'value') else str(bomb_type).lower(), '')
            if dmg:
                return f"{element} {dmg}+a"
            return element or ""
    except Exception:
        return ""
    return ""


def _get_recipe_rarity(recipe):
    """레시피 난이도 기반 희귀도 추정"""
    try:
        from src.equipment.item_system import ItemRarity, CONSUMABLE_TEMPLATES
        # 템플릿에서 rarity 가져오기
        item_id = getattr(recipe, 'potion_id', None) or getattr(recipe, 'bomb_id', None)
        if item_id:
            tmpl = CONSUMABLE_TEMPLATES.get(item_id, {})
            rarity_str = tmpl.get('rarity', 'COMMON')
            if hasattr(ItemRarity, rarity_str):
                return getattr(ItemRarity, rarity_str)
        # 없으면 난이도 기반 추정
        diff = getattr(recipe, 'difficulty', 1)
        if diff >= 5:
            return ItemRarity.LEGENDARY
        elif diff >= 4:
            return ItemRarity.EPIC
        elif diff >= 3:
            return ItemRarity.RARE
        elif diff >= 2:
            return ItemRarity.UNCOMMON
        return ItemRarity.COMMON
    except Exception:
        return None


def _get_effect_summary_from_item(effect_type: str, effect_value, duration=0) -> str:
    """아이템의 effect_type/value로 효과 요약 문자열 생성"""
    if effect_type == 'heal_hp':
        return f"HP +{effect_value}"
    elif effect_type == 'heal_mp':
        return f"MP +{effect_value}"
    elif effect_type == 'heal_both':
        return f"HP/MP +{effect_value}"
    elif effect_type == 'shield':
        return f"보호막 {effect_value}"
    elif effect_type == 'buff_strength':
        return f"공격력 +{effect_value} ({duration}턴)" if duration else f"공격력 +{effect_value}"
    elif effect_type == 'buff_defense':
        return f"방어력 +{effect_value} ({duration}턴)" if duration else f"방어력 +{effect_value}"
    elif effect_type == 'buff_speed':
        return f"속도 +{effect_value}%"
    elif effect_type == 'buff_regen':
        return f"재생 {effect_value}/턴"
    elif effect_type == 'buff_berserk':
        return f"광폭화 (공+30% 방-20%)"
    elif 'cure' in effect_type or 'cleanse' in effect_type:
        return "상태이상 치료"
    elif 'attack' in effect_type or 'aoe' in effect_type or 'bomb' in effect_type or 'grenade' in effect_type:
        return f"피해 {effect_value}+a"
    elif effect_value > 0:
        return f"효과 {effect_value}"
    return ""


class AlchemyMode(Enum):
    """연금술 모드"""
    SELECT_TAB = "select_tab"  # 탭 선택 (포션/폭탄/연금술 변환)
    SELECT_RECIPE = "select_recipe"  # 레시피 선택
    CONFIRM_CRAFT = "confirm_craft"  # 제작 확인
    SHOW_RESULT = "show_result"  # 결과 표시
    TRANSMUTATION_SELECT_ITEM = "transmutation_select_item"  # 변환할 아이템 선택
    TRANSMUTATION_SELECT_TARGET = "transmutation_select_target"  # 변환 대상 재료 선택
    TRANSMUTATION_CONFIRM = "transmutation_confirm"  # 변환 확인


class AlchemyUI:
    """연금술 실험실 UI"""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        inventory: Inventory,
        party: Optional[List[Any]] = None
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.inventory = inventory
        self.party = party or []
        
        # 연금술사가 파티에 있는지 확인
        self.has_alchemist = self._check_has_alchemist()
        
        self.mode = AlchemyMode.SELECT_TAB
        
        # 탭 (포션/폭탄/연금술 변환)
        if self.has_alchemist:
            self.tabs = ["포션 제작", "폭탄 제작", "연금술 변환"]
        else:
            self.tabs = ["포션 제작", "폭탄 제작"]
        self.current_tab = 0
        
        # 레시피 목록
        self.potion_recipes = PotionDatabase.get_all_recipes()
        self.bomb_recipes = BombDatabase.get_all_recipes()
        
        # 선택된 레시피
        self.selected_recipe: Optional[PotionRecipe | BombRecipe] = None
        
        # 커서 위치
        self.recipe_cursor = 0
        self.recipe_scroll = 0
        self.max_visible_recipes = 12
        
        # 제작 결과
        self.crafted_item: Optional[Any] = None
        
        self.closed = False
        
        # 연금술 변환 관련
        self.transmutation_item_cursor = 0
        self.transmutation_item_scroll = 0
        self.selected_transmutation_item: Optional[Any] = None
        self.transmutation_result_item: Optional[Any] = None
        # 스마트 변환: 대상 재료 선택
        self.transmutation_targets: List[Any] = []  # 변환 가능한 대상 목록
        self.transmutation_target_cursor = 0
        self.transmutation_target_scroll = 0
        self.selected_transmutation_target: Optional[Any] = None
        # 걸작 결과 추적
        self.is_masterwork_result: bool = False
        
        logger.info(f"연금술 실험실 열기 - 포션 레시피: {len(self.potion_recipes)}개, 폭탄 레시피: {len(self.bomb_recipes)}개, 연금술사: {self.has_alchemist}")

    def _check_has_alchemist(self) -> bool:
        """파티에 연금술 변환 특성을 가진 연금술사가 있는지 확인"""
        if not self.party:
            logger.warning("파티가 비어있습니다.")
            return False
            
        for member in self.party:
            is_alchemist = False
            member_name = getattr(member, 'name', 'Unknown')
            
            # 연금술사인지 확인 (여러 방법으로 확인)
            if hasattr(member, 'character_class'):
                if member.character_class == "연금술사":
                    is_alchemist = True
                    logger.debug(f"character_class로 연금술사 확인: {member_name} ({member.character_class})")
            
            if not is_alchemist and hasattr(member, 'job_name'):
                if member.job_name == "연금술사":
                    is_alchemist = True
                    logger.debug(f"job_name으로 연금술사 확인: {member_name} ({member.job_name})")
            
            if not is_alchemist and hasattr(member, 'job_id'):
                if member.job_id == "alchemist" or member.job_id == "연금술사":
                    is_alchemist = True
                    logger.debug(f"job_id로 연금술사 확인: {member_name} ({member.job_id})")
            
            if is_alchemist:
                # 연금술 변환 특성을 가지고 있는지 확인
                if hasattr(member, 'active_traits'):
                    active_traits = member.active_traits
                    logger.debug(f"연금술사 {member_name}의 active_traits: {active_traits}")
                    
                    if active_traits:
                        # active_traits는 문자열 ID 리스트 또는 딕셔너리 리스트
                        for trait in active_traits:
                            trait_id = trait if isinstance(trait, str) else trait.get('id', '') if isinstance(trait, dict) else str(trait)
                            logger.debug(f"특성 확인: {trait_id} (원본: {trait}, 타입: {type(trait)})")
                            if trait_id == 'transmutation':
                                logger.info(f"연금술 변환 특성을 가진 연금술사 발견: {member_name}")
                                return True
                    else:
                        logger.warning(f"연금술사 {member_name}의 active_traits가 비어있습니다.")
                else:
                    logger.warning(f"연금술사 {member_name}에 active_traits 속성이 없습니다.")
        
        logger.warning(f"파티에 연금술 변환 특성을 가진 연금술사가 없습니다. (파티원 수: {len(self.party)})")
        return False

    def _get_current_recipes(self) -> List[PotionRecipe | BombRecipe]:
        """현재 탭의 레시피 목록"""
        return self.potion_recipes if self.current_tab == 0 else self.bomb_recipes
    
    def _get_inventory_items_dict(self) -> Dict[str, int]:
        """인벤토리 + 창고 + 허브저장소를 {item_id: count} 딕셔너리로 변환"""
        items_dict = {}
        for slot in self.inventory.slots:
            if slot and slot.item:
                item_id = getattr(slot.item, 'item_id', '')
                if item_id:
                    items_dict[item_id] = items_dict.get(item_id, 0) + slot.quantity
        # 창고 + 허브 저장소 재료도 포함
        try:
            from src.town.town_manager import get_town_manager
            town_mgr = get_town_manager()
            if town_mgr:
                # 마을 창고 - 직렬화된 dict에서 직접 item_id 읽기 (역직렬화 불필요)
                storage_items = town_mgr.get_storage_inventory()
                for serialized in storage_items:
                    try:
                        item_id = serialized.get('item_id', '') if isinstance(serialized, dict) else ''
                        if item_id:
                            items_dict[item_id] = items_dict.get(item_id, 0) + 1
                    except Exception as e:
                        logger.warning(f"창고 아이템 조회 실패: {e}")
                # 허브 저장소 (게임오버 시 자동 보관된 재료)
                hub_items = town_mgr.get_hub_storage()
                for serialized in hub_items:
                    try:
                        item_id = serialized.get('item_id', '') if isinstance(serialized, dict) else ''
                        if item_id:
                            items_dict[item_id] = items_dict.get(item_id, 0) + 1
                    except Exception as e:
                        logger.warning(f"허브 아이템 조회 실패: {e}")
        except Exception as e:
            logger.warning(f"창고 재료 조회 실패: {e}")
        return items_dict

    def _get_inventory_and_storage_counts(self) -> tuple:
        """인벤토리와 창고+허브 재료를 각각 분리하여 반환

        Returns:
            (inv_dict, storage_dict, total_dict) - 각각 {item_id: count}
            storage_dict에는 마을 창고 + 허브 저장소 모두 포함
        """
        inv_dict: Dict[str, int] = {}
        storage_dict: Dict[str, int] = {}

        # 인벤토리 재료
        for slot in self.inventory.slots:
            if slot and slot.item:
                item_id = getattr(slot.item, 'item_id', '')
                if item_id:
                    inv_dict[item_id] = inv_dict.get(item_id, 0) + slot.quantity

        # 창고 + 허브 저장소 재료 - 직렬화된 dict에서 직접 item_id 읽기
        try:
            from src.town.town_manager import get_town_manager
            town_mgr = get_town_manager()
            if town_mgr:
                # 마을 창고
                storage_items = town_mgr.get_storage_inventory()
                for serialized in storage_items:
                    try:
                        item_id = serialized.get('item_id', '') if isinstance(serialized, dict) else ''
                        if item_id:
                            storage_dict[item_id] = storage_dict.get(item_id, 0) + 1
                    except Exception as e:
                        logger.warning(f"창고 아이템 조회 실패: {e}")
                # 허브 저장소
                hub_items = town_mgr.get_hub_storage()
                for serialized in hub_items:
                    try:
                        item_id = serialized.get('item_id', '') if isinstance(serialized, dict) else ''
                        if item_id:
                            storage_dict[item_id] = storage_dict.get(item_id, 0) + 1
                    except Exception as e:
                        logger.warning(f"허브 아이템 조회 실패: {e}")
        except Exception as e:
            logger.warning(f"창고 재료 조회 실패: {e}")

        # 합산
        total_dict: Dict[str, int] = {}
        all_ids = set(inv_dict.keys()) | set(storage_dict.keys())
        for item_id in all_ids:
            total_dict[item_id] = inv_dict.get(item_id, 0) + storage_dict.get(item_id, 0)

        return inv_dict, storage_dict, total_dict
    
    def _can_craft_recipe(self, recipe: PotionRecipe | BombRecipe) -> bool:
        """레시피 제작 가능 여부 확인"""
        inventory_dict = self._get_inventory_items_dict()
        
        if isinstance(recipe, PotionRecipe):
            return PotionBrewer.can_brew(recipe, inventory_dict)
        else:
            return BombCrafter.can_craft(recipe, inventory_dict)

    def handle_input(self, action: GameAction) -> bool:
        """입력 처리"""
        if self.mode == AlchemyMode.SELECT_TAB:
            return self._handle_tab_selection(action)
        elif self.mode == AlchemyMode.SELECT_RECIPE:
            return self._handle_recipe_selection(action)
        elif self.mode == AlchemyMode.CONFIRM_CRAFT:
            return self._handle_confirm_craft(action)
        elif self.mode == AlchemyMode.SHOW_RESULT:
            return self._handle_show_result(action)
        elif self.mode == AlchemyMode.TRANSMUTATION_SELECT_ITEM:
            return self._handle_transmutation_item_selection(action)
        elif self.mode == AlchemyMode.TRANSMUTATION_SELECT_TARGET:
            return self._handle_transmutation_target_selection(action)
        elif self.mode == AlchemyMode.TRANSMUTATION_CONFIRM:
            return self._handle_transmutation_confirm(action)
        
        return False

    def _handle_tab_selection(self, action: GameAction) -> bool:
        """탭 선택 모드"""
        if action == GameAction.MOVE_LEFT:
            self.current_tab = max(0, self.current_tab - 1)
            self.recipe_cursor = 0
            self.recipe_scroll = 0
            self.selected_recipe = None
            play_sfx("ui", "cursor_move")
        
        elif action == GameAction.MOVE_RIGHT:
            self.current_tab = min(len(self.tabs) - 1, self.current_tab + 1)
            self.recipe_cursor = 0
            self.recipe_scroll = 0
            self.selected_recipe = None
            self.selected_transmutation_item = None
            play_sfx("ui", "cursor_move")
        
        elif action == GameAction.MOVE_DOWN:
            # 현재 탭에 따라 다른 모드로
            if self.current_tab == 2 and self.has_alchemist:  # 연금술 변환 탭
                self.mode = AlchemyMode.TRANSMUTATION_SELECT_ITEM
            else:
                self.mode = AlchemyMode.SELECT_RECIPE
            play_sfx("ui", "cursor_move")
        
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            play_sfx("ui", "cursor_cancel")
            self.closed = True
            return True
        
        return False

    def _handle_recipe_selection(self, action: GameAction) -> bool:
        """레시피 선택 모드"""
        current_recipes = self._get_current_recipes()
        
        if action == GameAction.MOVE_UP:
            if current_recipes:
                self.recipe_cursor = max(0, self.recipe_cursor - 1)
                if self.recipe_cursor < self.recipe_scroll:
                    self.recipe_scroll = self.recipe_cursor
                play_sfx("ui", "cursor_move")
        
        elif action == GameAction.MOVE_DOWN:
            if current_recipes:
                self.recipe_cursor = min(len(current_recipes) - 1, self.recipe_cursor + 1)
                if self.recipe_cursor >= self.recipe_scroll + self.max_visible_recipes:
                    self.recipe_scroll = self.recipe_cursor - self.max_visible_recipes + 1
                play_sfx("ui", "cursor_move")
        
        elif action == GameAction.MOVE_LEFT or action == GameAction.MOVE_RIGHT:
            # 탭 선택 모드로 복귀
            self.mode = AlchemyMode.SELECT_TAB
            play_sfx("ui", "cursor_move")
        
        elif action == GameAction.CONFIRM:
            # 레시피 선택
            if current_recipes and 0 <= self.recipe_cursor < len(current_recipes):
                recipe = current_recipes[self.recipe_cursor]
                
                if self._can_craft_recipe(recipe):
                    self.selected_recipe = recipe
                    self.mode = AlchemyMode.CONFIRM_CRAFT
                    play_sfx("ui", "confirm")
                else:
                    play_sfx("ui", "cursor_cancel")
                    logger.warning(f"제작 불가능: {recipe.name} (재료 부족)")
        
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 탭 선택 모드로 복귀
            self.mode = AlchemyMode.SELECT_TAB
            play_sfx("ui", "cursor_cancel")
        
        return False

    def _handle_confirm_craft(self, action: GameAction) -> bool:
        """제작 확인 모드"""
        if action == GameAction.CONFIRM:
            # 제작 실행
            self._craft_item()
            self.mode = AlchemyMode.SHOW_RESULT
        
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 레시피 선택 모드로 복귀
            self.selected_recipe = None
            self.mode = AlchemyMode.SELECT_RECIPE
            play_sfx("ui", "cursor_cancel")
        
        return False

    def _handle_show_result(self, action: GameAction) -> bool:
        """결과 표시 모드"""
        if action == GameAction.CONFIRM or action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 현재 탭에 따라 다른 모드로 복귀
            self.crafted_item = None
            self.transmutation_result_item = None
            self.selected_recipe = None
            self.selected_transmutation_item = None
            self.selected_transmutation_target = None
            self.is_masterwork_result = False
            
            if self.current_tab == 2 and self.has_alchemist:
                # 연금술 변환 탭인 경우
                self.mode = AlchemyMode.TRANSMUTATION_SELECT_ITEM
            else:
                # 포션/폭탄 탭인 경우
                self.mode = AlchemyMode.SELECT_RECIPE
            
            if action != GameAction.CONFIRM:
                play_sfx("ui", "cursor_cancel")
        
        return False

    def _handle_transmutation_item_selection(self, action: GameAction) -> bool:
        """연금술 변환 아이템 선택 모드"""
        # 변환 가능한 아이템 목록 (재료 아이템만)
        transmutable_items = []
        for i, slot in enumerate(self.inventory.slots):
            if slot and slot.item:
                from src.gathering.ingredient import Ingredient
                if isinstance(slot.item, Ingredient):
                    transmutable_items.append((i, slot))
        
        if action == GameAction.MOVE_UP:
            if transmutable_items:
                self.transmutation_item_cursor = max(0, self.transmutation_item_cursor - 1)
                if self.transmutation_item_cursor < self.transmutation_item_scroll:
                    self.transmutation_item_scroll = self.transmutation_item_cursor
                play_sfx("ui", "cursor_move")
        
        elif action == GameAction.MOVE_DOWN:
            if transmutable_items:
                self.transmutation_item_cursor = min(len(transmutable_items) - 1, self.transmutation_item_cursor + 1)
                if self.transmutation_item_cursor >= self.transmutation_item_scroll + self.max_visible_recipes:
                    self.transmutation_item_scroll = self.transmutation_item_cursor - self.max_visible_recipes + 1
                play_sfx("ui", "cursor_move")
        
        elif action == GameAction.MOVE_LEFT or action == GameAction.MOVE_RIGHT:
            # 탭 선택 모드로 복귀
            self.mode = AlchemyMode.SELECT_TAB
            play_sfx("ui", "cursor_move")
        
        elif action == GameAction.CONFIRM:
            # 아이템 선택 → 대상 재료 선택 단계로
            if transmutable_items and 0 <= self.transmutation_item_cursor < len(transmutable_items):
                slot_idx, slot = transmutable_items[self.transmutation_item_cursor]
                self.selected_transmutation_item = (slot_idx, slot)
                # 같은 카테고리의 다른 재료 목록 생성
                item = slot.item
                from src.gathering.ingredient import IngredientDatabase
                self.transmutation_targets = []
                for ingredient_id, ingredient_data in IngredientDatabase.INGREDIENTS.items():
                    ingredient = IngredientDatabase.get_ingredient(ingredient_id)
                    if ingredient and ingredient.category == item.category and ingredient.item_id != item.item_id:
                        self.transmutation_targets.append(ingredient)
                if self.transmutation_targets:
                    self.transmutation_target_cursor = 0
                    self.transmutation_target_scroll = 0
                    self.mode = AlchemyMode.TRANSMUTATION_SELECT_TARGET
                    play_sfx("ui", "confirm")
                else:
                    play_sfx("ui", "cursor_cancel")
                    logger.warning("변환할 수 있는 대상 재료가 없습니다.")

        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 탭 선택 모드로 복귀
            self.mode = AlchemyMode.SELECT_TAB
            play_sfx("ui", "cursor_cancel")

        return False

    def _handle_transmutation_target_selection(self, action: GameAction) -> bool:
        """변환 대상 재료 선택 모드"""
        if action == GameAction.MOVE_UP:
            if self.transmutation_targets:
                self.transmutation_target_cursor = max(0, self.transmutation_target_cursor - 1)
                if self.transmutation_target_cursor < self.transmutation_target_scroll:
                    self.transmutation_target_scroll = self.transmutation_target_cursor
                play_sfx("ui", "cursor_move")

        elif action == GameAction.MOVE_DOWN:
            if self.transmutation_targets:
                self.transmutation_target_cursor = min(len(self.transmutation_targets) - 1, self.transmutation_target_cursor + 1)
                if self.transmutation_target_cursor >= self.transmutation_target_scroll + self.max_visible_recipes:
                    self.transmutation_target_scroll = self.transmutation_target_cursor - self.max_visible_recipes + 1
                play_sfx("ui", "cursor_move")

        elif action == GameAction.CONFIRM:
            if self.transmutation_targets and 0 <= self.transmutation_target_cursor < len(self.transmutation_targets):
                self.selected_transmutation_target = self.transmutation_targets[self.transmutation_target_cursor]
                self.mode = AlchemyMode.TRANSMUTATION_CONFIRM
                play_sfx("ui", "confirm")

        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            self.selected_transmutation_target = None
            self.mode = AlchemyMode.TRANSMUTATION_SELECT_ITEM
            play_sfx("ui", "cursor_cancel")

        return False

    def _handle_transmutation_confirm(self, action: GameAction) -> bool:
        """연금술 변환 확인 모드"""
        if action == GameAction.CONFIRM:
            # 변환 실행
            self._transmute_item()
            self.mode = AlchemyMode.SHOW_RESULT

        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 대상 선택 모드로 복귀
            self.selected_transmutation_target = None
            self.mode = AlchemyMode.TRANSMUTATION_SELECT_TARGET
            play_sfx("ui", "cursor_cancel")

        return False

    def pointer_regions(self) -> tuple[PointerRegion, ...]:
        regions: list[PointerRegion] = [
            PointerRegion(f"tab:{index}", 5 + index * 30, 4, 28, 1, GameAction.CONFIRM, f"{tab_name} 탭")
            for index, tab_name in enumerate(self.tabs)
        ]
        list_y = 7
        if self.current_tab == 2 and self.has_alchemist:
            if self.mode == AlchemyMode.TRANSMUTATION_SELECT_TARGET:
                visible_targets = self.transmutation_targets[
                    self.transmutation_target_scroll:self.transmutation_target_scroll + self.max_visible_recipes
                ]
                for index, target in enumerate(visible_targets):
                    actual_index = self.transmutation_target_scroll + index
                    regions.append(PointerRegion(f"target:{actual_index}", 5, list_y + index, self.screen_width - 10, 1, GameAction.CONFIRM, self._target_tooltip(target)))
            else:
                for index, slot_pair in enumerate(self._transmutable_slots()[self.transmutation_item_scroll:self.transmutation_item_scroll + self.max_visible_recipes]):
                    actual_index = self.transmutation_item_scroll + index
                    regions.append(PointerRegion(f"transmute:{actual_index}", 5, list_y + index, self.screen_width - 10, 1, GameAction.CONFIRM, self._item_tooltip(getattr(slot_pair[1], "item", None))))
            return tuple(regions)

        visible_recipes = self._get_current_recipes()[self.recipe_scroll:self.recipe_scroll + self.max_visible_recipes]
        for index, recipe in enumerate(visible_recipes):
            actual_index = self.recipe_scroll + index
            enabled = self._can_craft_recipe(recipe)
            regions.append(PointerRegion(f"recipe:{actual_index}", 5, list_y + index, self.screen_width - 10, 1, GameAction.CONFIRM, self._recipe_tooltip(recipe, enabled), enabled=enabled))
        return tuple(regions)

    def handle_pointer_event(self, event: PointerEvent) -> PointerDispatchResult:
        if event.kind is PointerEventKind.WHEEL:
            action = GameAction.MOVE_UP if event.wheel_delta > 0 else GameAction.MOVE_DOWN if event.wheel_delta < 0 else None
            if action is not None:
                self.handle_input(action)
            return PointerDispatchResult(event=event, action=action)
        if event.kind is PointerEventKind.CLICK and event.button is PointerButton.RIGHT:
            self.handle_input(GameAction.CANCEL)
            return PointerDispatchResult(event=event, action=GameAction.CANCEL)

        result = PointerDispatcher(self.pointer_regions()).dispatch(event)
        region_id = result.hovered_region_id or self._region_id_at(event)
        if region_id:
            self._focus_pointer_region(region_id)
        if event.kind is PointerEventKind.HOVER and region_id and result.tooltip is None:
            region = next((candidate for candidate in self.pointer_regions() if candidate.region_id == region_id), None)
            return PointerDispatchResult(event=event, hovered_region_id=region_id, tooltip=region.tooltip if region else None)
        if event.kind is PointerEventKind.CLICK and event.button is PointerButton.LEFT:
            self._focus_pointer_region(region_id)
            if region_id.startswith("recipe:"):
                recipe = self._get_current_recipes()[self.recipe_cursor]
                if not self._can_craft_recipe(recipe):
                    return PointerDispatchResult(event=event, action=GameAction.CONFIRM, value=False, hovered_region_id=region_id, tooltip=self._recipe_disabled_reason(recipe))
            closed = self.handle_input(GameAction.CONFIRM)
            return PointerDispatchResult(event=event, action=GameAction.CONFIRM, value=closed, hovered_region_id=region_id, tooltip=result.tooltip)
        return result

    def _region_id_at(self, event: PointerEvent) -> str:
        region = next((candidate for candidate in self.pointer_regions() if candidate.contains(event.position)), None)
        return region.region_id if region else ""

    def _focus_pointer_region(self, region_id: str) -> None:
        if region_id.startswith("tab:"):
            self.current_tab = int(region_id.split(":", 1)[1])
            self.mode = AlchemyMode.SELECT_TAB
            self.recipe_cursor = 0
            self.recipe_scroll = 0
        elif region_id.startswith("recipe:"):
            self.recipe_cursor = int(region_id.split(":", 1)[1])
            self.mode = AlchemyMode.SELECT_RECIPE
            if self.recipe_cursor < self.recipe_scroll:
                self.recipe_scroll = self.recipe_cursor
        elif region_id.startswith("target:"):
            self.transmutation_target_cursor = int(region_id.split(":", 1)[1])
            self.mode = AlchemyMode.TRANSMUTATION_SELECT_TARGET
        elif region_id.startswith("transmute:"):
            self.transmutation_item_cursor = int(region_id.split(":", 1)[1])
            self.mode = AlchemyMode.TRANSMUTATION_SELECT_ITEM

    def _recipe_tooltip(self, recipe: Any, enabled: bool) -> str:
        summary = _get_effect_summary(recipe)
        ingredients = ", ".join(f"{key} x{value}" for key, value in getattr(recipe, "ingredients", {}).items())
        status = "제작 가능" if enabled else self._recipe_disabled_reason(recipe)
        return " | ".join(part for part in (getattr(recipe, "name", "레시피"), summary, ingredients, status) if part)

    def _recipe_disabled_reason(self, recipe: Any) -> str:
        return f"재료 부족: {getattr(recipe, 'name', '레시피')}"

    def _target_tooltip(self, target: Any) -> str:
        category = getattr(getattr(target, "category", None), "display_name", "재료")
        return f"{getattr(target, 'name', '재료')} | {category} | 변환 대상으로 선택"

    def _item_tooltip(self, item: Any) -> str:
        return f"{getattr(item, 'name', '아이템')} | 연금술 변환 재료"

    def _transmutable_slots(self) -> list[tuple[int, Any]]:
        return [(index, slot) for index, slot in enumerate(self.inventory.slots) if slot and isinstance(getattr(slot, "item", None), Ingredient)]

    def _transmute_item(self):
        """아이템 변환 실행 (선택된 대상 재료로 변환)"""
        if not self.selected_transmutation_item:
            logger.warning("선택된 아이템이 없습니다.")
            return

        if not self.selected_transmutation_target:
            logger.warning("변환 대상이 선택되지 않았습니다.")
            return

        slot_idx, slot = self.selected_transmutation_item

        if not slot or not slot.item:
            logger.warning("유효하지 않은 아이템 슬롯")
            return

        from src.gathering.ingredient import Ingredient, IngredientCategory, IngredientDatabase
        if not isinstance(slot.item, Ingredient):
            logger.warning("재료 아이템만 변환 가능합니다.")
            return

        item = slot.item
        target_ingredient = self.selected_transmutation_target

        # 아이템 제거 (1개)
        self.inventory.remove_item(slot_idx, 1)

        # 새 아이템 생성
        from src.gathering.ingredient import Ingredient, ItemRarity
        transmuted_item = Ingredient(
            item_id=target_ingredient.item_id,
            name=target_ingredient.name,
            description=target_ingredient.description,
            item_type=ItemType.MATERIAL,
            rarity=item.rarity,  # 같은 등급 유지
            weight=target_ingredient.weight,
            sell_price=target_ingredient.sell_price,
            category=target_ingredient.category,
            food_value=target_ingredient.food_value,
            freshness=1.0,
            spoil_time=target_ingredient.spoil_time,
            edible_raw=target_ingredient.edible_raw,
            raw_hp_restore=target_ingredient.raw_hp_restore,
            raw_mp_restore=target_ingredient.raw_mp_restore
        )

        # 인벤토리에 추가
        if self.inventory.add_item(transmuted_item, 1):
            self.transmutation_result_item = transmuted_item
            logger.info(f"변환 완료: {item.name} -> {transmuted_item.name}")
        else:
            logger.warning("인벤토리 공간 부족")
            self.transmutation_result_item = None

    def _craft_item(self):
        """아이템 제작"""
        if not self.selected_recipe:
            logger.warning("선택된 레시피가 없습니다.")
            return
        
        inventory_dict = self._get_inventory_items_dict()
        
        # 재료 확인
        if isinstance(self.selected_recipe, PotionRecipe):
            can_craft = PotionBrewer.can_brew(self.selected_recipe, inventory_dict)
        else:
            can_craft = BombCrafter.can_craft(self.selected_recipe, inventory_dict)
        
        if not can_craft:
            logger.warning(f"재료 부족: {self.selected_recipe.name}")
            self.mode = AlchemyMode.SELECT_RECIPE
            return
        
        # 재료 소모 (인벤토리 우선, 부족하면 창고에서 제거)
        for ingredient_id, required_count in self.selected_recipe.ingredients.items():
            remaining = required_count

            # 1) 인벤토리에서 해당 재료 찾아서 제거 (역순으로 순회하여 인덱스 변경 문제 방지)
            for i in range(len(self.inventory.slots) - 1, -1, -1):
                slot = self.inventory.slots[i]
                if slot and slot.item and remaining > 0:
                    item_id = getattr(slot.item, 'item_id', '')
                    if item_id == ingredient_id:
                        remove_count = min(remaining, slot.quantity)
                        self.inventory.remove_item(i, remove_count)
                        remaining -= remove_count
                        if remaining <= 0:
                            break

            # 2) 인벤토리에서 부족하면 마을 창고에서 제거
            if remaining > 0:
                try:
                    from src.town.town_manager import get_town_manager
                    from src.persistence.save_system import deserialize_item
                    town_mgr = get_town_manager()
                    if town_mgr:
                        storage_items = town_mgr.get_storage_inventory()
                        indices_to_remove = []
                        for si in range(len(storage_items) - 1, -1, -1):
                            if remaining <= 0:
                                break
                            item = deserialize_item(storage_items[si])
                            if item and getattr(item, 'item_id', '') == ingredient_id:
                                indices_to_remove.append(si)
                                remaining -= 1
                        for idx in sorted(indices_to_remove, reverse=True):
                            town_mgr.retrieve_item_from_storage(idx)
                            logger.info(f"[연금술] 창고에서 재료 소모: {ingredient_id}")
                except Exception as e:
                    logger.debug(f"창고 재료 소모 실패: {e}")

            # 3) 마을 창고에서도 부족하면 허브 저장소에서 제거
            if remaining > 0:
                try:
                    from src.town.town_manager import get_town_manager
                    from src.persistence.save_system import deserialize_item
                    town_mgr = get_town_manager()
                    if town_mgr:
                        hub_items = town_mgr.get_hub_storage()
                        indices_to_remove = []
                        for si in range(len(hub_items) - 1, -1, -1):
                            if remaining <= 0:
                                break
                            item = deserialize_item(hub_items[si])
                            if item and getattr(item, 'item_id', '') == ingredient_id:
                                indices_to_remove.append(si)
                                remaining -= 1
                        for idx in sorted(indices_to_remove, reverse=True):
                            town_mgr.retrieve_item_from_hub_storage(idx)
                            logger.info(f"[연금술] 허브 저장소에서 재료 소모: {ingredient_id}")
                except Exception as e:
                    logger.debug(f"허브 저장소 재료 소모 실패: {e}")
        
        # 아이템 생성
        if isinstance(self.selected_recipe, PotionRecipe):
            try:
                self.crafted_item = ItemGenerator.create_consumable(self.selected_recipe.potion_id)
            except Exception as e:
                # 레시피 ID와 CONSUMABLE_TEMPLATES ID가 다를 수 있으므로, 직접 생성
                logger.warning(f"템플릿 없음: {self.selected_recipe.potion_id}, 직접 생성")
                from src.equipment.item_system import Consumable, ItemRarity
                
                # 효과 타입 결정
                effect_type = "heal_hp"
                effect_value = self.selected_recipe.effects.get("hp_restore", 50)
                
                if "mp_restore" in self.selected_recipe.effects:
                    effect_type = "heal_mp"
                    effect_value = self.selected_recipe.effects["mp_restore"]
                
                self.crafted_item = Consumable(
                    item_id=self.selected_recipe.potion_id,
                    name=self.selected_recipe.name,
                    description=self.selected_recipe.description,
                    item_type=ItemType.CONSUMABLE,
                    rarity=ItemRarity.COMMON,
                    effect_type=effect_type,
                    effect_value=effect_value,
                    sell_price=50,
                    weight=0.2
                )
        else:
            try:
                self.crafted_item = ItemGenerator.create_consumable(self.selected_recipe.bomb_id)
            except Exception as e:
                # 레시피 ID와 CONSUMABLE_TEMPLATES ID가 다를 수 있으므로, 직접 생성
                logger.warning(f"템플릿 없음: {self.selected_recipe.bomb_id}, 직접 생성")
                from src.equipment.item_system import Consumable, ItemRarity
                
                # 효과 타입 결정
                effect_type = "aoe_fire"
                effect_value = self.selected_recipe.damage
                
                if self.selected_recipe.bomb_type == BombType.ICE:
                    effect_type = "aoe_ice"
                elif self.selected_recipe.bomb_type == BombType.LIGHTNING:
                    effect_type = "thunder_grenade"
                elif self.selected_recipe.bomb_type == BombType.POISON:
                    effect_type = "poison_bomb"
                
                self.crafted_item = Consumable(
                    item_id=self.selected_recipe.bomb_id,
                    name=self.selected_recipe.name,
                    description=self.selected_recipe.description,
                    item_type=ItemType.CONSUMABLE,
                    rarity=ItemRarity.COMMON,
                    effect_type=effect_type,
                    effect_value=effect_value,
                    sell_price=100,
                    weight=0.3
                )
        
        # 걸작 판정
        self.is_masterwork_result = False
        if self.crafted_item:
            import random
            masterwork_chance = 10  # 기본 10%
            for member in self.party:
                job_id = getattr(member, 'job_id', '')
                if job_id == 'alchemist':
                    masterwork_chance += getattr(member, 'level', 1) * 2
                    break
            # 파티 전체 행운 평균
            luck_sum = sum(getattr(m, 'luck', 0) for m in self.party) if self.party else 0
            luck_avg = luck_sum / max(len(self.party), 1)
            masterwork_chance += luck_avg * 0.5
            masterwork_chance = min(masterwork_chance, 50)

            if random.randint(1, 100) <= masterwork_chance:
                self.is_masterwork_result = True
                self.crafted_item.name = f"걸작 {self.crafted_item.name}"
                self.crafted_item.effect_value = int(self.crafted_item.effect_value * 1.3)
                from src.equipment.item_system import ItemRarity
                rarity_upgrade = {
                    ItemRarity.COMMON: ItemRarity.UNCOMMON,
                    ItemRarity.UNCOMMON: ItemRarity.RARE,
                    ItemRarity.RARE: ItemRarity.EPIC,
                    ItemRarity.EPIC: ItemRarity.LEGENDARY,
                    ItemRarity.LEGENDARY: ItemRarity.UNIQUE,
                }
                self.crafted_item.rarity = rarity_upgrade.get(self.crafted_item.rarity, self.crafted_item.rarity)
                logger.info(f"걸작 제작! {self.crafted_item.name} (효과 +30%, 등급 상승)")

        # 인벤토리에 추가
        if self.crafted_item:
            if self.inventory.add_item(self.crafted_item, 1):
                if self.is_masterwork_result:
                    play_sfx("ui", "level_up")
                else:
                    play_sfx("ui", "confirm")
                logger.info(f"제작 완료: {self.crafted_item.name}")
            else:
                logger.warning("인벤토리 공간 부족")
                self.crafted_item = None

    def render(self, console: tcod.console.Console):
        """렌더링"""
        console.clear()
        render_space_background(console, self.screen_width, self.screen_height)
        
        # 제목
        title = "=== 연금술 실험실 ==="
        console.print((self.screen_width - len(title)) // 2, 2, title, fg=(255, 215, 0))
        
        # 탭
        tab_y = 4
        tab_x = 5
        for i, tab_name in enumerate(self.tabs):
            if i == self.current_tab:
                console.print(tab_x + i * 30, tab_y, f"[{tab_name}]", fg=(255, 255, 100))
            else:
                console.print(tab_x + i * 30, tab_y, f" {tab_name} ", fg=(150, 150, 150))
        
        # 현재 레시피 목록
        current_recipes = self._get_current_recipes()
        list_y = 7
        
        # 연금술 변환 탭이 아닌 경우
        if self.current_tab != 2 or not self.has_alchemist:
            if self.mode in (AlchemyMode.SELECT_TAB, AlchemyMode.SELECT_RECIPE, AlchemyMode.CONFIRM_CRAFT, AlchemyMode.SHOW_RESULT):
                # 레시피 목록 표시
                visible_recipes = current_recipes[self.recipe_scroll:self.recipe_scroll + self.max_visible_recipes]
                
                if not visible_recipes:
                    message = "사용 가능한 레시피가 없습니다."
                    console.print(10, list_y, message, fg=(150, 150, 150))
                else:
                    for i, recipe in enumerate(visible_recipes):
                        y = list_y + i
                        cursor_index = self.recipe_scroll + i

                        # 커서
                        if cursor_index == self.recipe_cursor and self.mode == AlchemyMode.SELECT_RECIPE:
                            console.print(3, y, "►", fg=(255, 255, 100))

                        # 희귀도 색상 적용
                        rarity = _get_recipe_rarity(recipe)
                        rarity_color = RARITY_COLORS.get(rarity, (200, 200, 200)) if rarity else (200, 200, 200)

                        # 레시피 이름 (희귀도 색상)
                        can_craft = self._can_craft_recipe(recipe)
                        if cursor_index == self.recipe_cursor and can_craft:
                            color = rarity_color
                        elif not can_craft:
                            color = (150, 150, 150)
                        else:
                            # 비선택 상태에서도 희귀도 색상 약하게 적용
                            color = tuple(min(255, c * 3 // 4 + 50) for c in rarity_color)
                        console.print(5, y, recipe.name, fg=color)

                        # 효과 요약
                        effect_summary = _get_effect_summary(recipe)
                        if effect_summary:
                            summary_x = 5 + len(recipe.name) + 2
                            # 가용 공간 내에서 표시
                            if summary_x + len(effect_summary) < self.screen_width - 28:
                                console.print(summary_x, y, effect_summary, fg=(180, 220, 255) if can_craft else (120, 120, 120))

                        # 난이도 표시
                        difficulty_stars = "★" * recipe.difficulty
                        console.print(self.screen_width - 25, y, difficulty_stars, fg=(255, 215, 0))

                        # 재료 상태 표시
                        if not can_craft:
                            console.print(self.screen_width - 10, y, "[재료부족]", fg=(255, 100, 100))
                        else:
                            console.print(self.screen_width - 10, y, "[재료OK]", fg=(100, 200, 100))
                
                # 선택된 레시피 상세 정보
                if self.selected_recipe or (current_recipes and 0 <= self.recipe_cursor < len(current_recipes)):
                    recipe = self.selected_recipe if self.selected_recipe else current_recipes[self.recipe_cursor]
                    detail_y = list_y + self.max_visible_recipes + 2

                    console.print(3, detail_y, "─" * (self.screen_width - 6), fg=Colors.UI_BORDER)
                    detail_y += 1

                    # 희귀도 배지 + 설명
                    rarity = _get_recipe_rarity(recipe)
                    rarity_color = RARITY_COLORS.get(rarity, (200, 200, 200)) if rarity else (200, 200, 200)
                    rarity_name = rarity.name if rarity and hasattr(rarity, 'name') else ""
                    if rarity_name:
                        rarity_labels = {"COMMON": "일반", "UNCOMMON": "고급", "RARE": "희귀", "EPIC": "영웅", "LEGENDARY": "전설", "UNIQUE": "유일"}
                        console.print(5, detail_y, f"[{rarity_labels.get(rarity_name, rarity_name)}]", fg=rarity_color)
                        console.print(5 + len(f"[{rarity_labels.get(rarity_name, rarity_name)}]") + 1, detail_y, recipe.description, fg=Colors.UI_TEXT)
                    else:
                        console.print(5, detail_y, recipe.description, fg=Colors.UI_TEXT)
                    detail_y += 1

                    # 효과 상세 표시
                    effect_summary = _get_effect_summary(recipe)
                    if effect_summary:
                        console.print(5, detail_y, f"효과: {effect_summary}", fg=(180, 220, 255))
                        detail_y += 1

                    detail_y += 1

                    # 재료 목록
                    console.print(5, detail_y, "필요 재료:", fg=(255, 200, 100))
                    detail_y += 1

                    inv_dict, storage_dict, total_dict = self._get_inventory_and_storage_counts()

                    for ingredient_id, required_count in recipe.ingredients.items():
                        ingredient = IngredientDatabase.get_ingredient(ingredient_id)
                        ingredient_name = ingredient.name if ingredient else ingredient_id
                        inv_count = inv_dict.get(ingredient_id, 0)
                        stg_count = storage_dict.get(ingredient_id, 0)
                        current_count = total_dict.get(ingredient_id, 0)

                        # 색상: 충분하면 녹색, 부족하면 빨간색
                        color = (100, 255, 100) if current_count >= required_count else (255, 100, 100)

                        status = "✓" if current_count >= required_count else "✗"
                        # 창고에 재료가 있으면 인벤/창고 구분 표시
                        if stg_count > 0:
                            count_text = f"인벤{inv_count}+창고{stg_count}"
                        else:
                            count_text = f"{current_count}"
                        console.print(7, detail_y, f"{status} {ingredient_name} x{required_count} (보유: {count_text})", fg=color)
                        detail_y += 1

                    # 걸작 확률 표시
                    masterwork_chance = 10
                    for member in self.party:
                        job_id = getattr(member, 'job_id', '')
                        if job_id == 'alchemist':
                            masterwork_chance += getattr(member, 'level', 1) * 2
                            break
                    luck_sum = sum(getattr(m, 'luck', 0) for m in self.party) if self.party else 0
                    luck_avg = luck_sum / max(len(self.party), 1)
                    masterwork_chance += luck_avg * 0.5
                    masterwork_chance = min(masterwork_chance, 50)
                    detail_y += 1
                    console.print(5, detail_y, f"걸작 확률: {int(masterwork_chance)}%", fg=(255, 215, 0))

                    # 제작 확인 메시지
                    if self.mode == AlchemyMode.CONFIRM_CRAFT:
                        detail_y += 1
                        console.print(5, detail_y, "제작하시겠습니까? (Z: 제작, X: 취소)", fg=(255, 255, 100))
                
                # 제작 결과 표시
                if self.mode == AlchemyMode.SHOW_RESULT and (self.crafted_item or self.transmutation_result_item):
                    result_y = list_y + self.max_visible_recipes + 2
                    console.print(3, result_y, "─" * (self.screen_width - 6), fg=Colors.UI_BORDER)
                    result_y += 1

                    if self.crafted_item:
                        # 희귀도 색상
                        item_rarity = getattr(self.crafted_item, 'rarity', None)
                        item_color = RARITY_COLORS.get(item_rarity, (200, 200, 200)) if item_rarity else (200, 200, 200)

                        if self.is_masterwork_result:
                            # 걸작 결과: 금색 프레임
                            console.print(5, result_y, "★ ★ ★  걸  작  ★ ★ ★", fg=(255, 215, 0))
                            result_y += 1
                            console.print(5, result_y, f"{self.crafted_item.name}", fg=item_color)
                            result_y += 1
                            # 효과 비교 (일반 vs 걸작)
                            base_value = int(getattr(self.crafted_item, 'effect_value', 0) / 1.3)
                            actual_value = getattr(self.crafted_item, 'effect_value', 0)
                            console.print(7, result_y, f"효과: {base_value} → {actual_value} (+30%)", fg=(255, 200, 50))
                            result_y += 1
                            console.print(7, result_y, "등급 상승!", fg=(255, 200, 50))
                        else:
                            console.print(5, result_y, f"✓ {self.crafted_item.name} 제작 완료!", fg=item_color)
                            result_y += 1
                            # 효과 상세
                            etype = getattr(self.crafted_item, 'effect_type', '')
                            evalue = getattr(self.crafted_item, 'effect_value', 0)
                            if evalue > 0:
                                effect_text = _get_effect_summary_from_item(etype, evalue, getattr(self.crafted_item, 'duration', 0))
                                if effect_text:
                                    console.print(7, result_y, f"효과: {effect_text}", fg=(180, 220, 255))

                        result_y += 1
                        console.print(5, result_y, "인벤토리에 추가됨", fg=(150, 150, 150))
                    elif self.transmutation_result_item:
                        console.print(5, result_y, f"✓ {self.transmutation_result_item.name} 변환 완료!", fg=(100, 255, 100))

                    result_y += 1
                    console.print(5, result_y, "Z 키를 누르면 계속합니다.", fg=Colors.UI_TEXT)
        
        # 연금술 변환 탭 UI
        if self.current_tab == 2 and self.has_alchemist:
            if self.mode == AlchemyMode.TRANSMUTATION_SELECT_TARGET:
                # 대상 재료 선택 UI
                console.print(5, list_y - 1, "변환 대상 재료를 선택하세요:", fg=(255, 200, 100))
                visible_targets = self.transmutation_targets[self.transmutation_target_scroll:self.transmutation_target_scroll + self.max_visible_recipes]

                if not visible_targets:
                    console.print(10, list_y, "변환 가능한 대상이 없습니다.", fg=(150, 150, 150))
                else:
                    for i, target in enumerate(visible_targets):
                        y = list_y + i
                        cursor_index = self.transmutation_target_scroll + i
                        if cursor_index == self.transmutation_target_cursor:
                            console.print(3, y, "►", fg=(255, 255, 100))
                        color = (255, 255, 255) if cursor_index == self.transmutation_target_cursor else (200, 200, 200)
                        console.print(5, y, target.name, fg=color)
                        # 카테고리 색상 표시
                        if hasattr(target, 'category'):
                            cat_name = target.category.display_name if hasattr(target.category, 'display_name') else str(target.category.value)
                            cat_colors = {
                                'herb': (100, 200, 100), 'mineral': (180, 180, 220), 'monster': (255, 120, 120),
                                'crystal': (150, 200, 255), 'reagent': (200, 150, 255), 'essence': (255, 200, 100),
                            }
                            cat_val = str(target.category.value).lower() if hasattr(target.category, 'value') else ''
                            cat_color = cat_colors.get(cat_val, (150, 200, 255))
                            console.print(self.screen_width - 20, y, f"[{cat_name}]", fg=cat_color)

                # 선택 확인 정보
                if self.transmutation_targets and 0 <= self.transmutation_target_cursor < len(self.transmutation_targets):
                    target = self.transmutation_targets[self.transmutation_target_cursor]
                    detail_y = list_y + self.max_visible_recipes + 2
                    console.print(3, detail_y, "─" * (self.screen_width - 6), fg=Colors.UI_BORDER)
                    detail_y += 1
                    if self.selected_transmutation_item:
                        _, src_slot = self.selected_transmutation_item
                        console.print(5, detail_y, f"{src_slot.item.name} → {target.name}", fg=(200, 255, 200))
                        detail_y += 1
                    console.print(5, detail_y, target.description[:self.screen_width - 10] if target.description else "", fg=Colors.UI_TEXT)

            elif self.mode == AlchemyMode.TRANSMUTATION_CONFIRM:
                # 변환 확인 UI
                detail_y = list_y
                if self.selected_transmutation_item and self.selected_transmutation_target:
                    _, src_slot = self.selected_transmutation_item
                    console.print(5, detail_y, f"{src_slot.item.name} → {self.selected_transmutation_target.name}", fg=(200, 255, 200))
                    detail_y += 2
                    console.print(5, detail_y, "변환하시겠습니까? (Z: 변환, X: 취소)", fg=(255, 255, 100))

            elif self.mode == AlchemyMode.SHOW_RESULT and self.transmutation_result_item:
                result_y = list_y
                console.print(3, result_y, "─" * (self.screen_width - 6), fg=Colors.UI_BORDER)
                result_y += 1
                console.print(5, result_y, f"✓ {self.transmutation_result_item.name} 변환 완료!", fg=(100, 255, 100))
                result_y += 1
                console.print(5, result_y, "Z 키를 누르면 계속합니다.", fg=Colors.UI_TEXT)

            elif self.mode == AlchemyMode.TRANSMUTATION_SELECT_ITEM or self.mode == AlchemyMode.SELECT_TAB:
                # 변환 가능한 아이템 목록
                transmutable_items = []
                for i, slot in enumerate(self.inventory.slots):
                    if slot and slot.item:
                        from src.gathering.ingredient import Ingredient
                        if isinstance(slot.item, Ingredient):
                            transmutable_items.append((i, slot))
                
                visible_items = transmutable_items[self.transmutation_item_scroll:self.transmutation_item_scroll + self.max_visible_recipes]
                
                if not visible_items:
                    message = "변환 가능한 재료 아이템이 없습니다."
                    console.print(10, list_y, message, fg=(150, 150, 150))
                else:
                    for i, (slot_idx, slot) in enumerate(visible_items):
                        y = list_y + i
                        cursor_index = self.transmutation_item_scroll + i
                        
                        # 커서
                        if cursor_index == self.transmutation_item_cursor and self.mode == AlchemyMode.TRANSMUTATION_SELECT_ITEM:
                            console.print(3, y, "►", fg=(255, 255, 100))
                        
                        # 아이템 이름
                        item = slot.item
                        color = (255, 255, 255) if cursor_index == self.transmutation_item_cursor else (200, 200, 200)
                        quantity_text = f" x{slot.quantity}" if slot.quantity > 1 else ""
                        console.print(5, y, f"{item.name}{quantity_text}", fg=color)
                        
                        # 카테고리 표시
                        category_name = item.category.display_name if hasattr(item.category, 'display_name') else str(item.category.value)
                        console.print(self.screen_width - 20, y, f"[{category_name}]", fg=(150, 200, 255))
                
                # 선택된 아이템 정보
                if self.selected_transmutation_item or (transmutable_items and 0 <= self.transmutation_item_cursor < len(transmutable_items)):
                    slot_idx, slot = self.selected_transmutation_item if self.selected_transmutation_item else transmutable_items[self.transmutation_item_cursor]
                    detail_y = list_y + self.max_visible_recipes + 2
                    
                    console.print(3, detail_y, "─" * (self.screen_width - 6), fg=Colors.UI_BORDER)
                    detail_y += 1
                    
                    item = slot.item
                    console.print(5, detail_y, f"{item.name} 변환", fg=Colors.UI_TEXT)
                    detail_y += 1
                    console.print(5, detail_y, f"카테고리: {item.category.display_name if hasattr(item.category, 'display_name') else item.category.value}", fg=Colors.UI_TEXT)
                    detail_y += 2
                    console.print(5, detail_y, "Z키로 변환 대상 재료를 선택하세요.", fg=(200, 200, 100))
        
        # 안내 메시지
        help_y = self.screen_height - 2
        if self.mode == AlchemyMode.SELECT_TAB:
            help_text = "←→: 탭 변경  ↓: 선택  X: 닫기"
        elif self.mode == AlchemyMode.SELECT_RECIPE:
            help_text = "↑↓: 선택  ←→: 탭 변경  Z: 제작  X: 취소"
        elif self.mode == AlchemyMode.CONFIRM_CRAFT:
            help_text = "Z: 제작  X: 취소"
        elif self.mode == AlchemyMode.TRANSMUTATION_SELECT_ITEM:
            help_text = "↑↓: 선택  ←→: 탭 변경  Z: 대상 선택  X: 취소"
        elif self.mode == AlchemyMode.TRANSMUTATION_SELECT_TARGET:
            help_text = "↑↓: 대상 선택  Z: 확인  X: 뒤로"
        elif self.mode == AlchemyMode.TRANSMUTATION_CONFIRM:
            help_text = "Z: 변환  X: 취소"
        else:
            help_text = "Z: 계속  X: 닫기"
        console.print(2, help_y, help_text, fg=Colors.GRAY)


def open_alchemy_lab(
    console: tcod.console.Console,
    context: tcod.context.Context,
    inventory: Inventory,
    floor_level: int = 1,
    party: Optional[List[Any]] = None
):
    """연금술 실험실 열기"""
    ui = AlchemyUI(console.width, console.height, inventory, party=party)
    
    logger.info(f"연금술 실험실 열기 (층수: {floor_level}, 연금술사: {ui.has_alchemist})")

    import time
    import pygame

    # 입력 큐 비우기 (이전 입력 방지)
    for _ in tcod.event.get():
        pass
    try:
        pygame.event.pump()
        pygame.event.clear()
    except:
        pass

    # 게임패드/키보드 입력 상태 초기화
    unified_input_handler.clear_input_state()

    # 딜레이 후 다시 이벤트 큐 비우기
    time.sleep(0.1)
    for _ in tcod.event.get():
        pass
    try:
        pygame.event.pump()
        pygame.event.clear()
    except:
        pass
    unified_input_handler.clear_input_state()

    # 초기 렌더링 (입력 대기 전에 화면 표시)
    ui.render(console)
    context.present(console)

    while not ui.closed:
        ui.render(console)
        context.present(console)
        
        # pygame 이벤트 업데이트 (게임패드 입력을 위해)
        try:
            pygame.event.pump()
        except:
            pass
        
        # 키보드 입력 처리
        keyboard_processed = False
        for event in tcod.event.get():
            pointer_event = unified_input_handler.process_pointer_event(event)
            if pointer_event is not None:
                ui.handle_pointer_event(pointer_event)
                keyboard_processed = True
                continue

            action = unified_input_handler.process_tcod_event(event)
            
            if action:
                keyboard_processed = True
                ui.handle_input(action)
            
            if isinstance(event, tcod.event.Quit):
                ui.closed = True
                break
        
        # 게임패드 입력 처리
        if not keyboard_processed and not ui.closed:
            gamepad_action = unified_input_handler.get_action()
            if gamepad_action:
                ui.handle_input(gamepad_action)
        
        # CPU 사용률 낮추기
        time.sleep(0.01)
