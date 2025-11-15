"""
상점 시스템 UI

메타 진행 요소: 영구 업그레이드, 특수 아이템 구매 등
별의 파편으로 구매
"""

from enum import Enum
from typing import List, Optional, Tuple
import tcod
import yaml
from pathlib import Path

from src.ui.input_handler import InputHandler, GameAction
from src.core.logger import get_logger, Loggers
from src.persistence.meta_progress import get_meta_progress, save_meta_progress


logger = get_logger(Loggers.UI)


class ShopCategory(Enum):
    """상점 카테고리"""
    PERMANENT_UPGRADES = "permanent"  # 영구 업그레이드
    TRAIT_UNLOCKS = "traits"  # 특성 해금
    CONSUMABLES = "consumables"  # 소모품
    EQUIPMENT = "equipment"  # 장비
    SPECIAL = "special"  # 특수 아이템


class ShopItem:
    """상점 아이템"""

    def __init__(
        self,
        name: str,
        description: str,
        price: int,
        category: ShopCategory,
        item_id: str = None,
        is_purchased: bool = False,
        job_id: str = None,  # 특성 해금용
        trait_id: str = None  # 특성 해금용
    ):
        self.name = name
        self.description = description
        self.price = price
        self.category = category
        self.item_id = item_id or name.lower().replace(" ", "_")
        self.is_purchased = is_purchased
        self.job_id = job_id
        self.trait_id = trait_id


# 상점 아이템 목록 (동적으로 생성)
def get_shop_items() -> List[ShopItem]:
    """상점 아이템 목록 생성"""
    meta = get_meta_progress()
    items = []

    # === 영구 업그레이드 ===
    items.append(ShopItem(
        "HP 증가 I",
        "파티원 전체의 최대 HP +10% (영구)",
        500,
        ShopCategory.PERMANENT_UPGRADES
    ))
    ShopItem(
        "HP 증가 II",
        "파티원 전체의 최대 HP +20% (영구)",
        1500,
        ShopCategory.PERMANENT_UPGRADES
    ),
    ShopItem(
        "MP 증가 I",
        "파티원 전체의 최대 MP +10% (영구)",
        500,
        ShopCategory.PERMANENT_UPGRADES
    ),
    ShopItem(
        "MP 증가 II",
        "파티원 전체의 최대 MP +20% (영구)",
        1500,
        ShopCategory.PERMANENT_UPGRADES
    ),
    ShopItem(
        "경험치 부스트 I",
        "획득 경험치 +10% (영구)",
        800,
        ShopCategory.PERMANENT_UPGRADES
    ),
    ShopItem(
        "경험치 부스트 II",
        "획득 경험치 +25% (영구)",
        2000,
        ShopCategory.PERMANENT_UPGRADES
    ),
    ShopItem(
        "골드 부스트",
        "획득 골드 +20% (영구)",
        1000,
        ShopCategory.PERMANENT_UPGRADES
    ),
    ShopItem(
        "인벤토리 확장 I",
        "무게 제한 +20kg (영구)",
        600,
        ShopCategory.PERMANENT_UPGRADES
    ),
    ShopItem(
        "인벤토리 확장 II",
        "무게 제한 +50kg (영구)",
        1800,
        ShopCategory.PERMANENT_UPGRADES
    ),
    ShopItem(
        "시작 레벨 증가",
        "새 캐릭터 시작 레벨 +1 (영구)",
        3000,
        ShopCategory.PERMANENT_UPGRADES
    ),

    # 소모품
    ShopItem(
        "엘릭서",
        "HP와 MP를 완전히 회복",
        100,
        ShopCategory.CONSUMABLES
    ),
    ShopItem(
        "하이포션",
        "HP 500 회복",
        50,
        ShopCategory.CONSUMABLES
    ),
    ShopItem(
        "하이이더",
        "MP 100 회복",
        50,
        ShopCategory.CONSUMABLES
    ),
    ShopItem(
        "피닉스의 깃털",
        "전투 중 사망 시 자동 부활 (1회)",
        200,
        ShopCategory.CONSUMABLES
    ),

    # 특수 아이템
    ShopItem(
        "던전 스킵 티켓",
        "특정 층을 스킵하고 다음 층으로",
        300,
        ShopCategory.SPECIAL
    ),
    ShopItem(
        "보스 레이더",
        "현재 층의 보스 위치를 미니맵에 표시",
        150,
        ShopCategory.SPECIAL
    ),
    ShopItem(
        "보물 탐지기",
        "현재 층의 모든 보물 위치를 미니맵에 표시",
        100,
        ShopCategory.SPECIAL
    ),
]


class ShopUI:
    """상점 UI"""

    def __init__(self, screen_width: int, screen_height: int, gold: int = 0):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.gold = gold
        self.selected_index = 0
        self.category_index = 0
        self.categories = list(ShopCategory)

        # 구매한 아이템 추적 (영구 업그레이드용)
        self.purchased_items: set = set()

    def get_items_by_category(self) -> List[ShopItem]:
        """현재 카테고리의 아이템 가져오기"""
        current_category = self.categories[self.category_index]
        return [item for item in SHOP_ITEMS if item.category == current_category]

    def handle_input(self, action: GameAction) -> Optional[str]:
        """
        입력 처리

        Returns:
            "purchase" - 구매 시도
            "close" - 상점 닫기
            None - 계속
        """
        items = self.get_items_by_category()

        if action == GameAction.MOVE_UP:
            self.selected_index = max(0, self.selected_index - 1)
        elif action == GameAction.MOVE_DOWN:
            self.selected_index = min(len(items) - 1, self.selected_index + 1)
        elif action == GameAction.MOVE_LEFT:
            self.category_index = max(0, self.category_index - 1)
            self.selected_index = 0  # 카테고리 변경 시 선택 초기화
        elif action == GameAction.MOVE_RIGHT:
            self.category_index = min(len(self.categories) - 1, self.category_index + 1)
            self.selected_index = 0
        elif action == GameAction.CONFIRM:
            return "purchase"
        elif action == GameAction.ESCAPE or action == GameAction.MENU:
            return "close"

        return None

    def purchase_item(self, item: ShopItem) -> Tuple[bool, str]:
        """
        아이템 구매 시도

        Returns:
            (성공 여부, 메시지)
        """
        # 이미 구매한 영구 업그레이드인지 확인
        if item.category == ShopCategory.PERMANENT_UPGRADES and item.item_id in self.purchased_items:
            return False, "이미 구매한 업그레이드입니다."

        # 골드 확인
        if self.gold < item.price:
            return False, f"골드가 부족합니다. (필요: {item.price}, 보유: {self.gold})"

        # 구매 처리
        self.gold -= item.price

        # 영구 업그레이드는 구매 목록에 추가
        if item.category == ShopCategory.PERMANENT_UPGRADES:
            self.purchased_items.add(item.item_id)

        logger.info(f"상점 구매: {item.name} ({item.price} 골드)")
        return True, f"{item.name} 구매 완료!"

    def render(self, console: tcod.console.Console):
        """상점 렌더링"""
        console.clear()

        # 제목
        title = "=== 상점 (메타 진행) ==="
        console.print((self.screen_width - len(title)) // 2, 2, title, fg=(255, 215, 0))

        # 골드 표시
        gold_text = f"보유 골드: {self.gold} G"
        console.print(self.screen_width - len(gold_text) - 5, 2, gold_text, fg=(255, 215, 0))

        # 카테고리 탭
        tab_y = 4
        tab_x = 5
        category_names = {
            ShopCategory.PERMANENT_UPGRADES: "영구 업그레이드",
            ShopCategory.CONSUMABLES: "소모품",
            ShopCategory.EQUIPMENT: "장비",
            ShopCategory.SPECIAL: "특수"
        }

        for i, category in enumerate(self.categories):
            name = category_names.get(category, category.value)
            if i == self.category_index:
                console.print(tab_x + i * 18, tab_y, f"[{name}]", fg=(255, 255, 100))
            else:
                console.print(tab_x + i * 18, tab_y, f" {name} ", fg=(150, 150, 150))

        # 아이템 목록
        items = self.get_items_by_category()
        list_y = 7

        if not items:
            console.print(10, list_y, "이 카테고리에는 아이템이 없습니다.", fg=(150, 150, 150))
        else:
            for i, item in enumerate(items):
                y = list_y + i * 3

                # 선택 커서
                if i == self.selected_index:
                    console.print(3, y, "►", fg=(255, 255, 100))

                # 아이템 이름
                item_color = (200, 200, 200)
                if item.category == ShopCategory.PERMANENT_UPGRADES and item.item_id in self.purchased_items:
                    item_color = (100, 100, 100)  # 구매한 아이템은 회색
                    item_name = f"{item.name} [구매 완료]"
                else:
                    item_name = item.name

                console.print(5, y, item_name, fg=item_color)

                # 가격
                price_color = (255, 215, 0) if self.gold >= item.price else (150, 150, 150)
                console.print(50, y, f"{item.price} G", fg=price_color)

                # 설명
                console.print(7, y + 1, item.description, fg=(150, 150, 150))

        # 조작법
        console.print(
            5,
            self.screen_height - 4,
            "↑↓: 선택  ←→: 카테고리  Enter: 구매  ESC: 닫기",
            fg=(180, 180, 180)
        )


def open_shop(
    console: tcod.console.Console,
    context: tcod.context.Context,
    inventory=None
) -> None:
    """
    상점 열기

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        inventory: 인벤토리 (골드 확인용)
    """
    # 골드 가져오기
    gold = inventory.gold if inventory and hasattr(inventory, 'gold') else 0

    shop = ShopUI(console.width, console.height, gold)
    handler = InputHandler()

    logger.info(f"상점 열림 (골드: {gold})")

    message = ""
    message_timer = 0

    while True:
        # 렌더링
        shop.render(console)

        # 메시지 표시
        if message and message_timer > 0:
            msg_y = shop.screen_height - 6
            console.print(5, msg_y, message, fg=(255, 255, 100))
            message_timer -= 1

        context.present(console)

        # 입력 처리
        for event in tcod.event.wait():
            action = handler.dispatch(event)

            if action:
                result = shop.handle_input(action)

                if result == "purchase":
                    items = shop.get_items_by_category()
                    if items and 0 <= shop.selected_index < len(items):
                        selected_item = items[shop.selected_index]
                        success, msg = shop.purchase_item(selected_item)
                        message = msg
                        message_timer = 60  # 60 프레임 동안 표시

                        # 구매 성공 시 인벤토리 골드 업데이트
                        if success and inventory and hasattr(inventory, 'gold'):
                            inventory.gold = shop.gold

                elif result == "close":
                    logger.info("상점 닫힘")
                    return

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return
