"""
상점 시스템 UI - 별의 파편으로 구매

메타 진행 요소: 영구 업그레이드, 특성 해금 등
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
    JOB_UNLOCKS = "jobs"  # 직업 해금
    PERMANENT_UPGRADES = "permanent"  # 영구 업그레이드
    TRAIT_UNLOCKS = "traits"  # 특성 해금
    CONSUMABLES = "consumables"  # 소모품
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
        job_id: str = None,  # 특성 해금용 또는 직업 해금용
        trait_id: str = None  # 특성 해금용
    ):
        self.name = name
        self.description = description
        self.price = price
        self.category = category
        self.item_id = item_id or name.lower().replace(" ", "_").replace("(", "").replace(")", "")
        self.job_id = job_id
        self.trait_id = trait_id


def get_job_unlock_items() -> List[ShopItem]:
    """직업 해금 아이템 동적 생성"""
    meta = get_meta_progress()
    items = []

    # 모든 직업 목록 (한글 이름 포함)
    all_jobs = [
        ("alchemist", "연금술사"), ("archmage", "대마법사"), ("assassin", "암살자"),
        ("bard", "바드"), ("battle_mage", "배틀메이지"), ("berserker", "광전사"),
        ("breaker", "브레이커"), ("dark_knight", "다크나이트"),
        ("dimensionist", "차원술사"), ("dragon_knight", "드래곤 나이트"),
        ("druid", "드루이드"), ("elementalist", "정령사"), ("engineer", "기계공학자"),
        ("gladiator", "검투사"), ("hacker", "해커"), ("monk", "무승"),
        ("necromancer", "네크로맨서"), ("paladin", "성기사"),
        ("philosopher", "철학자"), ("pirate", "해적"), ("priest", "사제"),
        ("samurai", "사무라이"), ("shaman", "무당"), ("sniper", "스나이퍼"),
        ("spellblade", "마검사"), ("sword_saint", "검성"), ("time_mage", "시간술사"),
        ("vampire", "뱀파이어")
    ]

    for job_id, job_name_kr in all_jobs:
        # 이미 해금되었는지 확인
        if meta.is_job_unlocked(job_id):
            continue

        # YAML 파일에서 직업 정보 로드
        yaml_path = Path(f"data/characters/{job_id}.yaml")
        if yaml_path.exists():
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    description = data.get('description', '')
                    archetype = data.get('archetype', '')

                    items.append(ShopItem(
                        name=f"[직업] {job_name_kr}",
                        description=f"{archetype} - {description}",
                        price=1000,  # 직업 해금 가격
                        category=ShopCategory.JOB_UNLOCKS,
                        item_id=f"job_{job_id}",
                        job_id=job_id
                    ))
            except Exception as e:
                logger.error(f"직업 정보 로드 실패 ({job_id}): {e}")

    return items


def get_trait_unlock_items() -> List[ShopItem]:
    """특성 해금 아이템 동적 생성"""
    meta = get_meta_progress()
    items = []

    # 모든 직업 순회
    all_jobs = [
        ("alchemist", "연금술사"), ("archer", "궁수"), ("archmage", "대마법사"),
        ("assassin", "암살자"), ("bard", "바드"), ("battle_mage", "전투 마법사"),
        ("berserker", "광전사"), ("breaker", "브레이커"), ("cleric", "성직자"),
        ("dark_knight", "다크나이트"), ("dimensionist", "차원술사"),
        ("dragon_knight", "드래곤 나이트"), ("druid", "드루이드"),
        ("elementalist", "정령사"), ("engineer", "기술자"), ("gladiator", "검투사"),
        ("hacker", "해커"), ("knight", "기사"), ("mage", "마법사"),
        ("monk", "무승"), ("necromancer", "네크로맨서"), ("paladin", "성기사"),
        ("philosopher", "철학자"), ("pirate", "해적"), ("priest", "사제"),
        ("rogue", "도적"), ("samurai", "사무라이"), ("shaman", "주술사"),
        ("sniper", "스나이퍼"), ("spellblade", "마검사"),
        ("sword_saint", "검성"), ("time_mage", "시간 마법사"),
        ("vampire", "흡혈귀"), ("warrior", "전사")
    ]

    for job_id, job_name_kr in all_jobs:
        yaml_path = Path(f"data/characters/{job_id}.yaml")

        if yaml_path.exists():
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    traits = data.get('traits', [])

                    # 3번째, 4번째, 5번째 특성 해금 아이템 생성
                    for i, trait in enumerate(traits[2:5], start=3):  # 인덱스 2, 3, 4
                        trait_id = trait.get('id', '')
                        trait_name = trait.get('name', '')

                        # 이미 해금되었는지 확인
                        is_unlocked = meta.is_trait_unlocked(job_id, trait_id)

                        items.append(ShopItem(
                            name=f"[{job_name_kr}] {trait_name}",
                            description=trait.get('description', '') + f" (특성 {i}/5)",
                            price=100 * i,  # 3번째 300, 4번째 400, 5번째 500
                            category=ShopCategory.TRAIT_UNLOCKS,
                            item_id=f"{job_id}_{trait_id}",
                            job_id=job_id,
                            trait_id=trait_id
                        ))
            except Exception as e:
                logger.error(f"특성 로드 실패 ({job_id}): {e}")

    return items


def get_shop_items() -> List[ShopItem]:
    """상점 아이템 목록 생성"""
    items = []

    # === 직업 해금 (동적 생성) ===
    items.extend(get_job_unlock_items())

    # === 영구 업그레이드 ===
    items.extend([
        ShopItem(
            "HP 증가 I",
            "파티원 전체의 최대 HP +10% (영구)",
            500,
            ShopCategory.PERMANENT_UPGRADES
        ),
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
    ])

    # === 특성 해금 (동적 생성) ===
    items.extend(get_trait_unlock_items())

    # === 소모품 ===
    items.extend([
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
    ])

    # === 특수 아이템 ===
    items.extend([
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
    ])

    return items


class ShopUI:
    """상점 UI"""

    ITEMS_PER_PAGE = 12  # 페이지당 표시할 아이템 수

    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.selected_index = 0
        self.category_index = 0
        self.page_index = 0  # 현재 페이지
        self.categories = list(ShopCategory)

        # 메타 진행 가져오기
        self.meta = get_meta_progress()

        # 아이템 목록
        self.all_items = get_shop_items()

    def get_items_by_category(self) -> List[ShopItem]:
        """현재 카테고리의 아이템 가져오기"""
        current_category = self.categories[self.category_index]
        return [item for item in self.all_items if item.category == current_category]

    def get_paged_items(self) -> Tuple[List[ShopItem], int, int]:
        """
        현재 페이지의 아이템 가져오기

        Returns:
            (페이지 아이템 목록, 현재 페이지, 총 페이지 수)
        """
        all_items = self.get_items_by_category()
        total_pages = max(1, (len(all_items) + self.ITEMS_PER_PAGE - 1) // self.ITEMS_PER_PAGE)

        # 페이지 인덱스 범위 체크
        self.page_index = max(0, min(self.page_index, total_pages - 1))

        # 현재 페이지의 아이템만 반환
        start_idx = self.page_index * self.ITEMS_PER_PAGE
        end_idx = start_idx + self.ITEMS_PER_PAGE
        paged_items = all_items[start_idx:end_idx]

        return paged_items, self.page_index + 1, total_pages

    def handle_input(self, action: GameAction) -> Optional[str]:
        """
        입력 처리

        Returns:
            "purchase" - 구매 시도
            "close" - 상점 닫기
            None - 계속
        """
        paged_items, current_page, total_pages = self.get_paged_items()

        if action == GameAction.MOVE_UP:
            self.selected_index = max(0, self.selected_index - 1)
        elif action == GameAction.MOVE_DOWN:
            self.selected_index = min(len(paged_items) - 1, self.selected_index + 1)
        elif action == GameAction.MOVE_LEFT:
            self.category_index = max(0, self.category_index - 1)
            self.selected_index = 0  # 카테고리 변경 시 선택 초기화
            self.page_index = 0  # 페이지도 초기화
        elif action == GameAction.MOVE_RIGHT:
            self.category_index = min(len(self.categories) - 1, self.category_index + 1)
            self.selected_index = 0
            self.page_index = 0
        elif action == GameAction.PAGE_UP:  # 이전 페이지
            if self.page_index > 0:
                self.page_index -= 1
                self.selected_index = 0
        elif action == GameAction.PAGE_DOWN:  # 다음 페이지
            if self.page_index < total_pages - 1:
                self.page_index += 1
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
        # 직업 해금인지 확인
        if item.category == ShopCategory.JOB_UNLOCKS:
            # 이미 해금되었는지 확인
            if self.meta.is_job_unlocked(item.job_id):
                return False, "이미 해금된 직업입니다."

            # 별의 파편 확인
            if self.meta.star_fragments < item.price:
                return False, f"별의 파편이 부족합니다. (필요: {item.price}, 보유: {self.meta.star_fragments})"

            # 구매 처리
            self.meta.spend_star_fragments(item.price)
            self.meta.unlock_job(item.job_id)
            save_meta_progress()

            logger.info(f"직업 해금: {item.job_id} ({item.price} 별의 파편)")
            return True, f"{item.name} 해금 완료!"

        # 특성 해금인지 확인
        elif item.category == ShopCategory.TRAIT_UNLOCKS:
            # 이미 해금되었는지 확인
            if self.meta.is_trait_unlocked(item.job_id, item.trait_id):
                return False, "이미 해금된 특성입니다."

            # 별의 파편 확인
            if self.meta.star_fragments < item.price:
                return False, f"별의 파편이 부족합니다. (필요: {item.price}, 보유: {self.meta.star_fragments})"

            # 구매 처리
            self.meta.spend_star_fragments(item.price)
            self.meta.unlock_trait(item.job_id, item.trait_id)
            save_meta_progress()

            logger.info(f"특성 해금: {item.job_id} - {item.trait_id} ({item.price} 별의 파편)")
            return True, f"{item.name} 해금 완료!"

        # 영구 업그레이드
        elif item.category == ShopCategory.PERMANENT_UPGRADES:
            # 이미 구매했는지 확인
            if self.meta.is_upgrade_purchased(item.item_id):
                return False, "이미 구매한 업그레이드입니다."

            # 별의 파편 확인
            if self.meta.star_fragments < item.price:
                return False, f"별의 파편이 부족합니다. (필요: {item.price}, 보유: {self.meta.star_fragments})"

            # 구매 처리
            self.meta.spend_star_fragments(item.price)
            self.meta.purchase_upgrade(item.item_id)
            save_meta_progress()

            logger.info(f"영구 업그레이드 구매: {item.name} ({item.price} 별의 파편)")
            return True, f"{item.name} 구매 완료!"

        # 소모품 및 기타
        else:
            # 별의 파편 확인
            if self.meta.star_fragments < item.price:
                return False, f"별의 파편이 부족합니다. (필요: {item.price}, 보유: {self.meta.star_fragments})"

            # 구매 처리
            self.meta.spend_star_fragments(item.price)
            save_meta_progress()

            logger.info(f"아이템 구매: {item.name} ({item.price} 별의 파편)")
            return True, f"{item.name} 구매 완료!"

    def render(self, console: tcod.console.Console):
        """상점 렌더링"""
        console.clear()

        # 제목
        title = "=== 상점 (메타 진행) ==="
        console.print((self.screen_width - len(title)) // 2, 2, title, fg=(255, 215, 0))

        # 별의 파편 표시
        fragments_text = f"별의 파편: {self.meta.star_fragments} ★"
        console.print(self.screen_width - len(fragments_text) - 5, 2, fragments_text, fg=(150, 200, 255))

        # 카테고리 탭
        tab_y = 4
        tab_x = 5
        category_names = {
            ShopCategory.JOB_UNLOCKS: "직업 해금",
            ShopCategory.PERMANENT_UPGRADES: "영구 업그레이드",
            ShopCategory.TRAIT_UNLOCKS: "특성 해금",
            ShopCategory.CONSUMABLES: "소모품",
            ShopCategory.SPECIAL: "특수"
        }

        for i, category in enumerate(self.categories):
            name = category_names.get(category, category.value)
            if i == self.category_index:
                console.print(tab_x + i * 18, tab_y, f"[{name}]", fg=(255, 255, 100))
            else:
                console.print(tab_x + i * 18, tab_y, f" {name} ", fg=(150, 150, 150))

        # 아이템 목록 (페이징)
        paged_items, current_page, total_pages = self.get_paged_items()
        all_items = self.get_items_by_category()
        list_y = 7

        # 페이지 정보 표시
        if total_pages > 1:
            page_info = f"페이지 {current_page}/{total_pages} (총 {len(all_items)}개)"
            console.print(self.screen_width - len(page_info) - 5, 5, page_info, fg=(200, 200, 200))

        if not paged_items:
            console.print(10, list_y, "이 카테고리에는 아이템이 없습니다.", fg=(150, 150, 150))
        else:
            for i, item in enumerate(paged_items):
                y = list_y + i * 3

                # 선택 커서
                if i == self.selected_index:
                    console.print(3, y, "►", fg=(255, 255, 100))

                # 구매/해금 상태 확인
                item_color = (200, 200, 200)
                item_name = item.name

                if item.category == ShopCategory.PERMANENT_UPGRADES:
                    if self.meta.is_upgrade_purchased(item.item_id):
                        item_color = (100, 100, 100)
                        item_name = f"{item.name} [구매 완료]"
                elif item.category == ShopCategory.TRAIT_UNLOCKS:
                    if self.meta.is_trait_unlocked(item.job_id, item.trait_id):
                        item_color = (100, 100, 100)
                        item_name = f"{item.name} [해금 완료]"

                # 아이템 이름
                console.print(5, y, item_name[:55], fg=item_color)

                # 가격
                price_color = (150, 200, 255) if self.meta.star_fragments >= item.price else (150, 150, 150)
                console.print(65, y, f"{item.price} ★", fg=price_color)

                # 설명
                console.print(7, y + 1, item.description[:65], fg=(150, 150, 150))

        # 조작법
        controls = "↑↓: 선택  ←→: 카테고리  "
        if total_pages > 1:
            controls += "PgUp/PgDn: 페이지  "
        controls += "Enter: 구매/해금  ESC: 닫기"

        console.print(
            5,
            self.screen_height - 4,
            controls,
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
        inventory: 인벤토리 (사용 안 함, 호환성 유지)
    """
    shop = ShopUI(console.width, console.height)
    handler = InputHandler()

    logger.info(f"상점 열림 (별의 파편: {shop.meta.star_fragments})")

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
                    paged_items, _, _ = shop.get_paged_items()
                    if paged_items and 0 <= shop.selected_index < len(paged_items):
                        selected_item = paged_items[shop.selected_index]
                        success, msg = shop.purchase_item(selected_item)
                        message = msg
                        message_timer = 60  # 60 프레임 동안 표시

                elif result == "close":
                    logger.info("상점 닫힘")
                    return

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return
