"""
요리 UI

4슬롯 냄비 인터페이스 (돈스타브 스타일)
"""

import tcod.console
import tcod.event
from typing import List, Optional, Any
from enum import Enum

from src.equipment.inventory import Inventory
from src.gathering.ingredient import Ingredient, IngredientCategory
from src.cooking.recipe import RecipeDatabase, CookedFood
from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, InputHandler
from src.core.logger import get_logger


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
        inventory: Inventory
    ):
        """
        Args:
            screen_width: 화면 너비
            screen_height: 화면 높이
            inventory: 인벤토리 (재료 가져오기)
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.inventory = inventory

        self.mode = CookingMode.SELECT_SLOT

        # 냄비 슬롯 (4개)
        self.pot_slots: List[Optional[Ingredient]] = [None, None, None, None]
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
                # 슬롯 비우기
                ingredient = self.pot_slots[self.selected_slot]
                self.pot_slots[self.selected_slot] = None
                # 인벤토리에 복귀 (실제 구현 시 필요)
                logger.info(f"슬롯 {self.selected_slot + 1}에서 {ingredient.name} 제거")
        elif action == GameAction.MENU:
            # 요리 시작 (M 키)
            if any(slot is not None for slot in self.pot_slots):
                self.mode = CookingMode.CONFIRM_COOK
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 모든 재료 반환하고 닫기
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

                # 슬롯에 추가
                self.pot_slots[self.selected_slot] = ingredient

                # 인벤토리에서 제거 (임시로 냄비에 보관)
                # 실제로는 인벤토리에서 제거하지 않고, 요리 완료 시 제거
                logger.info(f"슬롯 {self.selected_slot + 1}에 {ingredient.name} 추가")

                # 슬롯 선택 모드로 복귀
                self.mode = CookingMode.SELECT_SLOT
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 슬롯 선택 모드로 복귀
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
            self.mode = CookingMode.SELECT_SLOT

        return False

    def _handle_show_result(self, action: GameAction) -> bool:
        """결과 표시 모드"""
        if action == GameAction.CONFIRM or action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 냄비 닫기 (요리 결과는 인벤토리에 추가됨)
            self.closed = True
            return True

        return False

    def _cook(self):
        """요리 실행"""
        # 냄비에 있는 재료 수집
        ingredients = [slot for slot in self.pot_slots if slot is not None]

        if not ingredients:
            logger.warning("재료가 없습니다!")
            return

        # 레시피 찾기
        recipe = RecipeDatabase.find_recipe(ingredients)

        self.cooked_food = recipe.result

        logger.info(f"요리 완료: {self.cooked_food.name}")

        # 인벤토리에서 재료 제거 (실제 구현 시)
        # 요리 결과를 인벤토리에 추가 (실제 구현 시)

    def _get_available_ingredients(self) -> List[tuple]:
        """
        인벤토리에서 사용 가능한 재료 목록

        Returns:
            [(슬롯 인덱스, Ingredient), ...]
        """
        available = []

        for i, slot in enumerate(self.inventory.slots):
            if isinstance(slot.item, Ingredient):
                # 이미 냄비에 있는 재료는 제외 (같은 인스턴스 체크)
                if slot.item not in self.pot_slots:
                    available.append((i, slot.item))

        return available

    def _update_ingredient_scroll(self):
        """재료 목록 스크롤 업데이트"""
        if self.ingredient_cursor < self.ingredient_scroll:
            self.ingredient_scroll = self.ingredient_cursor
        elif self.ingredient_cursor >= self.ingredient_scroll + self.max_visible_ingredients:
            self.ingredient_scroll = self.ingredient_cursor - self.max_visible_ingredients + 1

    def _return_all_ingredients(self):
        """모든 재료 인벤토리로 복귀"""
        for i, ingredient in enumerate(self.pot_slots):
            if ingredient:
                logger.info(f"슬롯 {i + 1}의 {ingredient.name} 반환")
                self.pot_slots[i] = None

    def render(self, console: tcod.console.Console):
        """요리 화면 렌더링"""
        console.clear()

        # 제목
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
            ingredient = self.pot_slots[i]
            if ingredient:
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
        ingredients = [slot for slot in self.pot_slots if slot is not None]

        if not ingredients:
            return

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
            "✨ 요리 완성! ✨",
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
    inventory: Inventory
) -> Optional[CookedFood]:
    """
    요리 냄비 열기

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        inventory: 인벤토리

    Returns:
        요리된 음식 (취소 시 None)
    """
    ui = CookingPotUI(console.width, console.height, inventory)
    handler = InputHandler()

    logger.info("요리 냄비 열기")

    while not ui.closed:
        # 렌더링
        ui.render(console)
        context.present(console)

        # 입력 처리
        for event in tcod.event.wait():
            action = handler.dispatch(event)

            if action:
                if ui.handle_input(action):
                    # 요리 완료
                    if ui.cooked_food:
                        logger.info(f"요리 완성: {ui.cooked_food.name}")
                        return ui.cooked_food
                    return None

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                ui.closed = True
                return None

    return None
