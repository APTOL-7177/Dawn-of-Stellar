"""
요리 UI

4슬롯 냄비 인터페이스 (돈스타브 스타일)
"""

import tcod.console
import tcod.event
from typing import List, Optional, Any
from enum import Enum

from src.equipment.inventory import Inventory
from src.equipment.item_system import ItemType
from src.gathering.ingredient import Ingredient, IngredientCategory
from src.cooking.recipe import RecipeDatabase, CookedFood
from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler, unified_input_handler
from src.core.logger import get_logger
from src.audio import play_sfx


logger = get_logger("cooking_ui")


class CookingMode(Enum):
    """요리 모드"""
    SELECT_SLOT = "select_slot"  # 슬롯 선택
    SELECT_INGREDIENT = "select_ingredient"  # 재료 선택
    CONFIRM_COOK = "confirm_cook"  # 요리 확인
    SHOW_RESULT = "show_result"  # 결과 표시


class CookingPotUI:
    """요리 냄비 UI"""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        inventory: Inventory,
        is_cooking_pot: bool = False
    ):
        """
        Args:
            screen_width: 화면 너비
            screen_height: 화면 높이
            inventory: 인벤토리 (재료 가져오기)
            is_cooking_pot: 요리솥에서 요리하는지 여부 (보너스 적용)
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.inventory = inventory
        self.is_cooking_pot = is_cooking_pot  # 요리솥 보너스 플래그

        self.mode = CookingMode.SELECT_SLOT

        # 냄비 슬롯 (4개) - (재료, 인벤토리 슬롯 인덱스) 튜플
        self.pot_slots: List[Optional[tuple]] = [None, None, None, None]
        self.selected_slot = 0  # 현재 선택된 슬롯

        # 재료 선택
        self.ingredient_cursor = 0
        self.ingredient_scroll = 0
        self.max_visible_ingredients = 10

        # 요리 결과
        self.cooked_food: Optional[CookedFood] = None

        self.closed = False

        # 레시피 초기화
        RecipeDatabase.initialize()

    def handle_input(self, action: GameAction) -> bool:
        """
        입력 처리

        Args:
            action: 게임 액션

        Returns:
            닫기 여부
        """
        if self.mode == CookingMode.SELECT_SLOT:
            return self._handle_slot_selection(action)
        elif self.mode == CookingMode.SELECT_INGREDIENT:
            return self._handle_ingredient_selection(action)
        elif self.mode == CookingMode.CONFIRM_COOK:
            return self._handle_confirm_cook(action)
        elif self.mode == CookingMode.SHOW_RESULT:
            return self._handle_show_result(action)

        return False

    def _handle_slot_selection(self, action: GameAction) -> bool:
        """슬롯 선택 모드"""
        if action == GameAction.MOVE_LEFT:
            self.selected_slot = max(0, self.selected_slot - 1)
        elif action == GameAction.MOVE_RIGHT:
            self.selected_slot = min(3, self.selected_slot + 1)
        elif action == GameAction.CONFIRM:
            # 슬롯에 재료 추가 or 제거
            if self.pot_slots[self.selected_slot] is None:
                # 재료 선택 모드로
                self.mode = CookingMode.SELECT_INGREDIENT
                self.ingredient_cursor = 0
                self.ingredient_scroll = 0
            else:
                # 슬롯 비우기 (재료 반환하지 않음 - 취소 시에만 반환)
                ingredient_data = self.pot_slots[self.selected_slot]
                if ingredient_data:
                    ingredient, _ = ingredient_data
                    logger.info(f"슬롯 {self.selected_slot + 1}에서 {ingredient.name} 제거")
                self.pot_slots[self.selected_slot] = None
        elif action == GameAction.MENU:
            # 요리 시작 (M 키)
            if any(slot is not None for slot in self.pot_slots):
                self.mode = CookingMode.CONFIRM_COOK
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 모든 재료 반환하고 닫기
            play_sfx("ui", "cursor_cancel")
            self._return_all_ingredients()
            self.closed = True
            return True

        return False

    def _handle_ingredient_selection(self, action: GameAction) -> bool:
        """재료 선택 모드"""
        ingredients = self._get_available_ingredients()

        if action == GameAction.MOVE_UP:
            self.ingredient_cursor = max(0, self.ingredient_cursor - 1)
            self._update_ingredient_scroll()
        elif action == GameAction.MOVE_DOWN:
            self.ingredient_cursor = min(len(ingredients) - 1, self.ingredient_cursor + 1)
            self._update_ingredient_scroll()
        elif action == GameAction.CONFIRM:
            # 재료 선택
            if 0 <= self.ingredient_cursor < len(ingredients):
                slot_idx, ingredient = ingredients[self.ingredient_cursor]

                # 슬롯에 추가 (재료와 인벤토리 슬롯 인덱스 모두 저장)
                self.pot_slots[self.selected_slot] = (ingredient, slot_idx)

                logger.info(f"슬롯 {self.selected_slot + 1}에 {ingredient.name} 추가")

                # 슬롯 선택 모드로 복귀
                self.mode = CookingMode.SELECT_SLOT
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 슬롯 선택 모드로 복귀
            play_sfx("ui", "cursor_cancel")
            self.mode = CookingMode.SELECT_SLOT

        return False

    def _handle_confirm_cook(self, action: GameAction) -> bool:
        """요리 확인 모드"""
        if action == GameAction.CONFIRM:
            # 요리 실행
            self._cook()
            self.mode = CookingMode.SHOW_RESULT
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 슬롯 선택 모드로 복귀
            play_sfx("ui", "cursor_cancel")
            self.mode = CookingMode.SELECT_SLOT

        return False

    def _handle_show_result(self, action: GameAction) -> bool:
        """결과 표시 모드"""
        if action == GameAction.CONFIRM or action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 냄비 닫기 (요리 결과는 인벤토리에 추가됨)
            if action != GameAction.CONFIRM:  # CONFIRM은 요리 완료이므로 다른 효과음
                play_sfx("ui", "cursor_cancel")
            self.closed = True
            return True

        return False

    def _cook(self):
        """요리 실행"""
        import random
        
        # 냄비에 있는 재료 수집 (재료만 추출)
        ingredient_data = [slot for slot in self.pot_slots if slot is not None]

        if not ingredient_data:
            logger.warning("재료가 없습니다!")
            return

        # 재료와 슬롯 인덱스 분리
        ingredients = [data[0] for data in ingredient_data]
        slot_indices = [data[1] for data in ingredient_data]

        # 레시피 찾기
        recipe = RecipeDatabase.find_recipe(ingredients)

        # 원본 객체 수정 방지를 위해 deepcopy 사용
        from copy import deepcopy
        self.cooked_food = deepcopy(recipe.result)

        # 요리솥 보너스 적용 (CookedFood 재료가 포함된 경우 적용하지 않음 - 효과 중복 방지)
        has_cooked_food_ingredient = any(isinstance(ing, CookedFood) for ing in ingredients)
        if self.is_cooking_pot and not has_cooked_food_ingredient:
            # 요리솥에서 요리 시 보너스 (기본 재료만으로 요리할 때):
            # 1. HP/MP 회복량 20% 증가
            # 2. 버프 지속시간 20% 증가
            # 3. 추가 아이템 생성 (10% 확률로 같은 음식 1개 추가)

            # 보너스 적용 전 원래 값 저장
            self.cooked_food.original_hp_restore = getattr(self.cooked_food, 'hp_restore', 0)
            self.cooked_food.original_mp_restore = getattr(self.cooked_food, 'mp_restore', 0)
            self.cooked_food.original_buff_duration = getattr(self.cooked_food, 'buff_duration', 0)

            # HP/MP 회복량 증가
            if hasattr(self.cooked_food, 'hp_restore') and self.cooked_food.hp_restore > 0:
                self.cooked_food.hp_restore = int(self.cooked_food.hp_restore * 1.2)
                logger.info(f"요리솥 보너스: HP 회복량 20% 증가! (현재: {self.cooked_food.hp_restore})")

            if hasattr(self.cooked_food, 'mp_restore') and self.cooked_food.mp_restore > 0:
                self.cooked_food.mp_restore = int(self.cooked_food.mp_restore * 1.2)
                logger.info(f"요리솥 보너스: MP 회복량 20% 증가! (현재: {self.cooked_food.mp_restore})")

            # 버프 지속시간 증가
            if hasattr(self.cooked_food, 'buff_duration') and self.cooked_food.buff_duration > 0:
                self.cooked_food.buff_duration = int(self.cooked_food.buff_duration * 1.2)
                logger.info(f"요리솥 보너스: 버프 지속시간 20% 증가! (현재: {self.cooked_food.buff_duration})")

            # 추가 아이템 생성
            extra_item = random.random() < 0.1  # 10% 확률
            if extra_item:
                # 같은 음식을 하나 더 추가
                from copy import deepcopy
                extra_food = deepcopy(recipe.result)
                # 추가 아이템에도 보너스 적용
                if hasattr(extra_food, 'hp_restore') and extra_food.hp_restore > 0:
                    extra_food.hp_restore = int(extra_food.hp_restore * 1.2)
                    extra_food.original_hp_restore = getattr(extra_food, 'hp_restore', 0) // 1.2
                if hasattr(extra_food, 'mp_restore') and extra_food.mp_restore > 0:
                    extra_food.mp_restore = int(extra_food.mp_restore * 1.2)
                    extra_food.original_mp_restore = getattr(extra_food, 'mp_restore', 0) // 1.2
                if hasattr(extra_food, 'buff_duration') and extra_food.buff_duration > 0:
                    extra_food.buff_duration = int(extra_food.buff_duration * 1.2)
                    extra_food.original_buff_duration = getattr(extra_food, 'buff_duration', 0) // 1.2

                success_extra = self.inventory.add_item(extra_food, quantity=1)
                if success_extra:
                    logger.info(f"요리솥 보너스: 추가 음식 생성! {extra_food.name}")
                else:
                    logger.warning("요리솥 보너스: 추가 음식 생성 실패 (인벤토리 가득 참)")

            logger.info(f"요리솥 보너스 적용 완료")

        logger.info(f"요리 완료: {self.cooked_food.name}")

        # 인벤토리에서 재료 제거 (높은 인덱스부터 제거해야 인덱스 변경 안됨)
        for slot_idx in sorted(slot_indices, reverse=True):
            removed = self.inventory.remove_item(slot_idx, quantity=1)
            if removed:
                logger.debug(f"인벤토리에서 재료 제거: 슬롯 {slot_idx}, {removed.name}")

        # 요리 결과를 인벤토리에 추가
        success = self.inventory.add_item(self.cooked_food, quantity=1)
        if success:
            logger.info(f"인벤토리에 요리 추가: {self.cooked_food.name}")
        else:
            logger.warning(f"인벤토리가 가득 차서 요리를 추가할 수 없습니다!")

    def _get_available_ingredients(self) -> List[tuple]:
        """
        인벤토리에서 사용 가능한 재료 목록

        Returns:
            [(슬롯 인덱스, Ingredient), ...]
        """
        available = []

        if not self.inventory or not hasattr(self.inventory, 'slots'):
            logger.warning("인벤토리 또는 슬롯이 없습니다!")
            return available

        # 냄비에 이미 사용된 슬롯별 개수 추적
        used_counts = {}  # {슬롯_인덱스: 사용된_개수}
        for pot_slot in self.pot_slots:
            if pot_slot is not None:
                _, slot_idx = pot_slot
                used_counts[slot_idx] = used_counts.get(slot_idx, 0) + 1

        for i, slot in enumerate(self.inventory.slots):
            # 슬롯과 아이템이 존재하는지 확인
            if slot is None:
                continue
            if not hasattr(slot, 'item') or slot.item is None:
                continue
            
            # Ingredient 타입 확인 (여러 방법 시도 - 순서 중요!)
            is_ingredient = False
            
            # 방법 1: item_type이 MATERIAL이고 category 속성이 있는지 확인 (가장 확실한 방법)
            item_type = getattr(slot.item, 'item_type', None)
            has_category = hasattr(slot.item, 'category')
            if item_type == ItemType.MATERIAL and has_category:
                is_ingredient = True
            # 방법 2: isinstance 체크
            elif isinstance(slot.item, Ingredient):
                is_ingredient = True
            # 방법 3: category 속성이 IngredientCategory 타입인지 확인 (저장/로드 후 타입 체크 실패 대비)
            elif has_category and isinstance(getattr(slot.item, 'category', None), IngredientCategory):
                is_ingredient = True
            
            if is_ingredient:
                # 슬롯의 전체 quantity와 이미 사용된 개수 확인
                total_quantity = getattr(slot, 'quantity', 1)
                used_count = used_counts.get(i, 0)
                remaining_quantity = total_quantity - used_count

                # 남은 quantity만큼만 목록에 추가
                if remaining_quantity > 0:
                    for _ in range(remaining_quantity):
                        available.append((i, slot.item))
                    logger.info(f"사용 가능한 재료 발견: 슬롯 {i}, {slot.item.name} (전체: {total_quantity}, 사용: {used_count}, 남음: {remaining_quantity})")
            else:
                # 디버그: 왜 식재료로 인식되지 않는지 확인 (로그 레벨을 info로 변경해서 항상 출력)
                item_type = getattr(slot.item, 'item_type', None)
                has_category = hasattr(slot.item, 'category')
                category_value = getattr(slot.item, 'category', None)
                logger.info(f"슬롯 {i} 아이템은 식재료가 아님: {getattr(slot.item, 'name', 'Unknown')} "
                           f"(타입: {type(slot.item).__name__}, item_type: {item_type}, "
                           f"category 속성: {has_category}, category 값: {category_value})")

        logger.info(f"사용 가능한 재료 개수: {len(available)}")
        return available

    def _update_ingredient_scroll(self):
        """재료 목록 스크롤 업데이트"""
        if self.ingredient_cursor < self.ingredient_scroll:
            self.ingredient_scroll = self.ingredient_cursor
        elif self.ingredient_cursor >= self.ingredient_scroll + self.max_visible_ingredients:
            self.ingredient_scroll = self.ingredient_cursor - self.max_visible_ingredients + 1

    def _return_all_ingredients(self):
        """모든 재료 인벤토리로 복귀 (취소 시)"""
        # 요리를 취소했으므로 재료를 반환하지 않음
        # 재료는 여전히 인벤토리에 있음 (제거하지 않았으므로)
        for i, slot_data in enumerate(self.pot_slots):
            if slot_data:
                ingredient, _ = slot_data
                logger.info(f"슬롯 {i + 1}의 {ingredient.name} 반환 (실제로는 인벤토리에 유지)")
                self.pot_slots[i] = None

    def render(self, console: tcod.console.Console):
        """요리 화면 렌더링"""
        render_space_background(console, self.screen_width, self.screen_height)

        # 제목 (요리솥 보너스 표시)
        if self.is_cooking_pot:
            title = "🍲 요리 냄비 (요리솥 보너스 적용)"
        else:
            title = "🍲 요리 냄비"
        console.print(
            (self.screen_width - len(title)) // 2,
            2,
            title,
            fg=Colors.UI_TEXT_SELECTED
        )

        if self.mode == CookingMode.SHOW_RESULT:
            self._render_cooking_result(console)
        else:
            self._render_cooking_pot(console)

        # 도움말
        self._render_help(console)

    def _render_cooking_pot(self, console: tcod.console.Console):
        """냄비 인터페이스 렌더링"""
        pot_y = 5

        # 냄비 프레임
        console.print(
            (self.screen_width - 60) // 2,
            pot_y,
            "╔════════════════════════════════════════════════════════════╗",
            fg=Colors.UI_BORDER
        )

        # 슬롯 렌더링 (4개)
        slot_y = pot_y + 2
        slot_start_x = (self.screen_width - 60) // 2 + 2

        for i in range(4):
            is_selected = (i == self.selected_slot and self.mode == CookingMode.SELECT_SLOT)
            slot_x = slot_start_x + i * 15

            # 슬롯 박스
            box_char = "■" if is_selected else "□"
            console.print(slot_x, slot_y, f"[{i + 1}] {box_char}", fg=Colors.UI_TEXT_SELECTED if is_selected else Colors.UI_TEXT)

            # 슬롯 내용
            slot_data = self.pot_slots[i]
            if slot_data:
                ingredient, _ = slot_data  # 튜플에서 재료만 추출
                # 재료 이름
                console.print(
                    slot_x + 2,
                    slot_y + 1,
                    ingredient.name[:8],  # 최대 8글자
                    fg=Colors.UI_TEXT
                )

                # 카테고리
                category_color = self._get_category_color(ingredient.category)
                console.print(
                    slot_x + 2,
                    slot_y + 2,
                    ingredient.category.display_name[:4],
                    fg=category_color
                )
            else:
                console.print(
                    slot_x + 2,
                    slot_y + 1,
                    "(비어있음)",
                    fg=Colors.DARK_GRAY
                )

        # 재료 선택 모드
        if self.mode == CookingMode.SELECT_INGREDIENT:
            self._render_ingredient_list(console)

        # 요리 확인 모드
        elif self.mode == CookingMode.CONFIRM_COOK:
            self._render_confirm_dialog(console)

        # 예상 결과 표시
        else:
            self._render_preview(console, slot_y + 6)

    def _render_ingredient_list(self, console: tcod.console.Console):
        """재료 목록 렌더링"""
        box_width = 50
        box_height = 20
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        console.draw_frame(
            box_x, box_y, box_width, box_height,
            "재료 선택",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )

        ingredients = self._get_available_ingredients()

        y = box_y + 2
        visible_ingredients = ingredients[self.ingredient_scroll:self.ingredient_scroll + self.max_visible_ingredients]

        for idx, (slot_idx, ingredient) in enumerate(visible_ingredients):
            actual_idx = self.ingredient_scroll + idx
            is_selected = (actual_idx == self.ingredient_cursor)
            prefix = "►" if is_selected else " "

            category_color = self._get_category_color(ingredient.category)

            console.print(
                box_x + 2, y,
                f"{prefix} {ingredient.name}",
                fg=Colors.UI_TEXT_SELECTED if is_selected else Colors.UI_TEXT
            )

            console.print(
                box_x + 30, y,
                f"[{ingredient.category.display_name}]",
                fg=category_color
            )

            y += 1

        # 스크롤 표시
        if len(ingredients) > self.max_visible_ingredients:
            console.print(
                box_x + 2, box_y + box_height - 3,
                f"({self.ingredient_scroll + 1}-{min(self.ingredient_scroll + self.max_visible_ingredients, len(ingredients))} / {len(ingredients)})",
                fg=Colors.DARK_GRAY
            )

    def _render_confirm_dialog(self, console: tcod.console.Console):
        """요리 확인 대화상자"""
        box_width = 40
        box_height = 10
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        console.draw_frame(
            box_x, box_y, box_width, box_height,
            "요리 확인",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )

        msg = "이 재료로 요리하시겠습니까?"
        console.print(
            box_x + (box_width - len(msg)) // 2,
            box_y + 3,
            msg,
            fg=Colors.UI_TEXT
        )

        console.print(
            box_x + (box_width - 20) // 2,
            box_y + 5,
            "Z: 요리 시작",
            fg=Colors.UI_TEXT_SELECTED
        )

        console.print(
            box_x + (box_width - 20) // 2,
            box_y + 6,
            "X: 취소",
            fg=Colors.GRAY
        )

    def _render_preview(self, console: tcod.console.Console, y: int):
        """예상 결과 미리보기"""
        ingredient_data = [slot for slot in self.pot_slots if slot is not None]

        if not ingredient_data:
            return

        # 재료만 추출
        ingredients = [data[0] for data in ingredient_data]

        # 레시피 찾기
        recipe = RecipeDatabase.find_recipe(ingredients)

        console.print(
            (self.screen_width - 40) // 2,
            y,
            "예상 결과:",
            fg=Colors.UI_TEXT
        )

        console.print(
            (self.screen_width - 40) // 2,
            y + 1,
            f"→ {recipe.result.name}",
            fg=Colors.UI_TEXT_SELECTED
        )

        console.print(
            (self.screen_width - 40) // 2,
            y + 2,
            f"   HP+{recipe.result.hp_restore}, MP+{recipe.result.mp_restore}",
            fg=Colors.GRAY
        )

    def _render_cooking_result(self, console: tcod.console.Console):
        """요리 결과 표시"""
        if not self.cooked_food:
            return

        box_width = 60
        box_height = 20
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        console.draw_frame(
            box_x, box_y, box_width, box_height,
            " 요리 완성! ",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )

        y = box_y + 3

        # 요리 이름
        console.print(
            box_x + (box_width - len(self.cooked_food.name)) // 2,
            y,
            self.cooked_food.name,
            fg=Colors.UI_TEXT_SELECTED
        )
        y += 2

        # 설명
        console.print(
            box_x + 2,
            y,
            self.cooked_food.description,
            fg=Colors.UI_TEXT
        )
        y += 2

        # 효과
        console.print(box_x + 2, y, "효과:", fg=Colors.UI_TEXT)
        y += 1

        if self.cooked_food.hp_restore > 0:
            console.print(box_x + 4, y, f"HP 회복: +{self.cooked_food.hp_restore}", fg=(100, 255, 100))
            y += 1

        if self.cooked_food.mp_restore > 0:
            console.print(box_x + 4, y, f"MP 회복: +{self.cooked_food.mp_restore}", fg=(100, 200, 255))
            y += 1

        if self.cooked_food.max_hp_bonus > 0:
            console.print(box_x + 4, y, f"최대 HP 증가: +{self.cooked_food.max_hp_bonus} ({self.cooked_food.buff_duration}턴)", fg=(255, 200, 100))
            y += 1

        if self.cooked_food.max_mp_bonus > 0:
            console.print(box_x + 4, y, f"최대 MP 증가: +{self.cooked_food.max_mp_bonus} ({self.cooked_food.buff_duration}턴)", fg=(200, 150, 255))
            y += 1

        if self.cooked_food.is_poison:
            console.print(box_x + 4, y, f"독! 피해: {self.cooked_food.poison_damage}", fg=(255, 100, 100))
            y += 1

    def _render_help(self, console: tcod.console.Console):
        """도움말 렌더링"""
        help_y = self.screen_height - 2

        if self.mode == CookingMode.SELECT_SLOT:
            help_text = "←→: 슬롯 선택  Z: 재료 추가/제거  M: 요리 시작  X: 닫기"
        elif self.mode == CookingMode.SELECT_INGREDIENT:
            help_text = "↑↓: 재료 선택  Z: 선택  X: 취소"
        elif self.mode == CookingMode.CONFIRM_COOK:
            help_text = "Z: 요리  X: 취소"
        elif self.mode == CookingMode.SHOW_RESULT:
            help_text = "Z: 확인"
        else:
            help_text = ""

        console.print(
            (self.screen_width - len(help_text)) // 2,
            help_y,
            help_text,
            fg=Colors.GRAY
        )

    def _get_category_color(self, category: IngredientCategory):
        """카테고리별 색상"""
        colors = {
            IngredientCategory.MEAT: (255, 100, 100),
            IngredientCategory.VEGETABLE: (100, 255, 100),
            IngredientCategory.FRUIT: (255, 200, 100),
            IngredientCategory.MUSHROOM: (200, 150, 255),
            IngredientCategory.FISH: (100, 200, 255),
            IngredientCategory.SPICE: (255, 255, 100),
            IngredientCategory.SWEETENER: (255, 200, 150),
            IngredientCategory.FILLER: (150, 150, 150)
        }
        return colors.get(category, Colors.UI_TEXT)


def open_cooking_pot(
    console: tcod.console.Console,
    context: tcod.context.Context,
    inventory: Inventory,
    is_cooking_pot: bool = False
) -> Optional[CookedFood]:
    """
    요리 냄비 열기

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        inventory: 인벤토리
        is_cooking_pot: 요리솥에서 요리하는지 여부 (보너스 적용)

    Returns:
        요리된 음식 (취소 시 None)
    """
    ui = CookingPotUI(console.width, console.height, inventory, is_cooking_pot=is_cooking_pot)

    logger.info(f"요리 냄비 열기 (요리솥: {is_cooking_pot})")

    # 입력 큐 비우기 (이전 입력 방지)
    import time
    for _ in tcod.event.get():
        pass
    try:
        import pygame
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
        import pygame
        pygame.event.pump()
        pygame.event.clear()
    except:
        pass
    unified_input_handler.clear_input_state()

    while not ui.closed:
        # 렌더링
        ui.render(console)
        context.present(console)

        # pygame 이벤트 업데이트 (게임패드 입력을 위해)
        try:
            import pygame
            pygame.event.pump()
        except:
            pass

        # 게임패드 입력 우선 확인
        gamepad_action = unified_input_handler.get_action()
        if gamepad_action:
            if ui.handle_input(gamepad_action):
                # 요리 완료
                if ui.cooked_food:
                    logger.info(f"요리 완성: {ui.cooked_food.name}")
                return ui.cooked_food

        # 키보드 입력 처리
        for event in tcod.event.get():
            action = unified_input_handler.process_tcod_event(event)

            if action:
                if ui.handle_input(action):
                    # 요리 완료
                    if ui.cooked_food:
                        logger.info(f"요리 완성: {ui.cooked_food.name}")
                        return ui.cooked_food
                    return None

            # 윈도우 닫기
            for quit_event in tcod.event.get():
                if isinstance(quit_event, tcod.event.Quit):
                    ui.closed = True
                    return None

        # CPU 사용률 낮추기 (논블로킹 모드에서 필요)
        import time
        time.sleep(0.01)

    return None
