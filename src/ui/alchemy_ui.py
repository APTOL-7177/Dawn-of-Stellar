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
from src.cooking.potion_brewing import PotionDatabase, PotionRecipe, PotionBrewer, PotionType
from src.cooking.bomb_crafting import BombDatabase, BombRecipe, BombCrafter, BombType
from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler, unified_input_handler
from src.equipment.item_system import ItemGenerator
from src.core.logger import get_logger
from src.audio import play_sfx


logger = get_logger("alchemy_ui")


class AlchemyMode(Enum):
    """연금술 모드"""
    SELECT_TAB = "select_tab"  # 탭 선택 (포션/폭탄/연금술 변환)
    SELECT_RECIPE = "select_recipe"  # 레시피 선택
    CONFIRM_CRAFT = "confirm_craft"  # 제작 확인
    SHOW_RESULT = "show_result"  # 결과 표시
    TRANSMUTATION_SELECT_ITEM = "transmutation_select_item"  # 변환할 아이템 선택
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
        """인벤토리를 {item_id: count} 딕셔너리로 변환"""
        items_dict = {}
        for slot in self.inventory.slots:
            if slot and slot.item:
                item_id = getattr(slot.item, 'item_id', '')
                if item_id:
                    items_dict[item_id] = items_dict.get(item_id, 0) + slot.quantity
        return items_dict
    
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
            # 아이템 선택
            if transmutable_items and 0 <= self.transmutation_item_cursor < len(transmutable_items):
                slot_idx, slot = transmutable_items[self.transmutation_item_cursor]
                self.selected_transmutation_item = (slot_idx, slot)
                self.mode = AlchemyMode.TRANSMUTATION_CONFIRM
                play_sfx("ui", "confirm")
        
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 탭 선택 모드로 복귀
            self.mode = AlchemyMode.SELECT_TAB
            play_sfx("ui", "cursor_cancel")
        
        return False

    def _handle_transmutation_confirm(self, action: GameAction) -> bool:
        """연금술 변환 확인 모드"""
        if action == GameAction.CONFIRM:
            # 변환 실행
            self._transmute_item()
            self.mode = AlchemyMode.SHOW_RESULT
        
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 아이템 선택 모드로 복귀
            self.selected_transmutation_item = None
            self.mode = AlchemyMode.TRANSMUTATION_SELECT_ITEM
            play_sfx("ui", "cursor_cancel")
        
        return False

    def _transmute_item(self):
        """아이템 변환 실행"""
        if not self.selected_transmutation_item:
            logger.warning("선택된 아이템이 없습니다.")
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
        item_category = item.category
        
        # 같은 카테고리의 다른 재료로 변환 (랜덤)
        available_ingredients = []
        for ingredient_id, ingredient_data in IngredientDatabase.INGREDIENTS.items():
            ingredient = IngredientDatabase.get_ingredient(ingredient_id)
            if ingredient and ingredient.category == item_category and ingredient.item_id != item.item_id:
                available_ingredients.append(ingredient)
        
        if not available_ingredients:
            logger.warning("변환할 수 있는 아이템이 없습니다.")
            self.mode = AlchemyMode.TRANSMUTATION_SELECT_ITEM
            return
        
        # 랜덤 선택
        import random
        target_ingredient = random.choice(available_ingredients)
        
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
            # 변환 실패 시 원래 아이템 복구하지 않음 (이미 소모됨)
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
        
        # 재료 소모 (인벤토리에서 제거)
        for ingredient_id, required_count in self.selected_recipe.ingredients.items():
            remaining = required_count
            
            # 인벤토리에서 해당 재료 찾아서 제거 (역순으로 순회하여 인덱스 변경 문제 방지)
            slots_to_remove = []
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
        
        # 인벤토리에 추가
        if self.crafted_item:
            if self.inventory.add_item(self.crafted_item, 1):
                logger.info(f"제작 완료: {self.crafted_item.name}")
            else:
                logger.warning("인벤토리 공간 부족")
                # 인벤토리에 추가 실패 시 재료 반환은 하지 않음 (이미 소모됨)
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
            if self.mode == AlchemyMode.SELECT_RECIPE or self.mode == AlchemyMode.CONFIRM_CRAFT or self.mode == AlchemyMode.SHOW_RESULT:
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
                        
                        # 레시피 이름
                        can_craft = self._can_craft_recipe(recipe)
                        color = (255, 255, 255) if (cursor_index == self.recipe_cursor and can_craft) else ((150, 150, 150) if not can_craft else (200, 200, 200))
                        console.print(5, y, recipe.name, fg=color)
                        
                        # 난이도 표시
                        difficulty_stars = "★" * recipe.difficulty
                        console.print(self.screen_width - 25, y, difficulty_stars, fg=(255, 215, 0))
                        
                        # 제작 불가능 표시
                        if not can_craft:
                            console.print(self.screen_width - 10, y, "[재료부족]", fg=(255, 100, 100))
                
                # 선택된 레시피 상세 정보
                if self.selected_recipe or (current_recipes and 0 <= self.recipe_cursor < len(current_recipes)):
                    recipe = self.selected_recipe if self.selected_recipe else current_recipes[self.recipe_cursor]
                    detail_y = list_y + self.max_visible_recipes + 2
                    
                    console.print(3, detail_y, "─" * (self.screen_width - 6), fg=Colors.UI_BORDER)
                    detail_y += 1
                    
                    # 설명
                    console.print(5, detail_y, recipe.description, fg=Colors.UI_TEXT)
                    detail_y += 2
                    
                    # 재료 목록
                    console.print(5, detail_y, "필요 재료:", fg=(255, 200, 100))
                    detail_y += 1
                    
                    inventory_dict = self._get_inventory_items_dict()
                    
                    for ingredient_id, required_count in recipe.ingredients.items():
                        ingredient = IngredientDatabase.get_ingredient(ingredient_id)
                        ingredient_name = ingredient.name if ingredient else ingredient_id
                        current_count = inventory_dict.get(ingredient_id, 0)
                        
                        # 색상: 충분하면 녹색, 부족하면 빨간색
                        color = (100, 255, 100) if current_count >= required_count else (255, 100, 100)
                        
                        status = "✓" if current_count >= required_count else "✗"
                        console.print(7, detail_y, f"{status} {ingredient_name} x{required_count} (보유: {current_count})", fg=color)
                        detail_y += 1
                    
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
                        console.print(5, result_y, f"✓ {self.crafted_item.name} 제작 완료!", fg=(100, 255, 100))
                    elif self.transmutation_result_item:
                        console.print(5, result_y, f"✓ {self.transmutation_result_item.name} 변환 완료!", fg=(100, 255, 100))
                    
                    result_y += 1
                    console.print(5, result_y, "Z 키를 누르면 계속합니다.", fg=Colors.UI_TEXT)
        
        # 연금술 변환 탭 UI
        if self.current_tab == 2 and self.has_alchemist:
            if self.mode == AlchemyMode.TRANSMUTATION_SELECT_ITEM or self.mode == AlchemyMode.TRANSMUTATION_CONFIRM:
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
                    console.print(5, detail_y, "같은 카테고리의 다른 재료로 랜덤 변환됩니다.", fg=(200, 200, 100))
                    detail_y += 1
                    
                    # 확인 메시지
                    if self.mode == AlchemyMode.TRANSMUTATION_CONFIRM:
                        console.print(5, detail_y, "변환하시겠습니까? (Z: 변환, X: 취소)", fg=(255, 255, 100))
        
        # 안내 메시지
        help_y = self.screen_height - 2
        if self.mode == AlchemyMode.SELECT_TAB:
            help_text = "←→: 탭 변경  ↓: 선택  X: 닫기"
        elif self.mode == AlchemyMode.SELECT_RECIPE:
            help_text = "↑↓: 선택  ←→: 탭 변경  Z: 제작  X: 취소"
        elif self.mode == AlchemyMode.CONFIRM_CRAFT:
            help_text = "Z: 제작  X: 취소"
        elif self.mode == AlchemyMode.TRANSMUTATION_SELECT_ITEM:
            help_text = "↑↓: 선택  ←→: 탭 변경  Z: 변환  X: 취소"
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
    
    while not ui.closed:
        ui.render(console)
        context.present(console)
        
        for event in tcod.event.wait():
            action = unified_input_handler.process_tcod_event(event)
            
            if action:
                ui.handle_input(action)
            
            if isinstance(event, tcod.event.Quit):
                ui.closed = True
                break
