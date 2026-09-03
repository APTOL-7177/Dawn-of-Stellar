"""
인벤토리 UI

아이템 확인, 사용, 장비 착용
"""

import tcod.console
import tcod.event
from typing import List, Optional, Any
from enum import Enum

from src.equipment.inventory import Inventory
from src.equipment.item_system import Item, Equipment, Consumable, ItemType
from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler, unified_input_handler
from src.ui.cursor_menu import CursorMenu, MenuItem
from src.ui.pointer import PointerButton, PointerDispatcher, PointerDispatchResult, PointerEvent, PointerEventKind, PointerRegion
from src.ui.ui_renderer import draw_styled_box, SelectionHighlight
from src.core.logger import get_logger
from src.audio import play_sfx


logger = get_logger("inventory_ui")


class InventoryMode(Enum):
    """인벤토리 모드"""
    BROWSE = "browse"  # 둘러보기
    USE_ITEM = "use_item"  # 아이템 사용
    EQUIP = "equip"  # 장비 착용
    SELECT_TARGET = "select_target"  # 대상 선택
    CHARACTER_EQUIPMENT = "character_equipment"  # 캐릭터 장비 보기
    UNEQUIP = "unequip"  # 장비 해제
    CONFIRM_DESTROY = "confirm_destroy"  # 파괴 확인
    DROP_ITEM = "drop_item"  # 아이템 드롭
    DROP_GOLD = "drop_gold"  # 골드 드롭


class InventoryUI:
    """인벤토리 UI"""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        inventory: Inventory,
        party: List[Any],
        exploration: Optional[Any] = None
    ):
        """
        Args:
            screen_width: 화면 너비
            screen_height: 화면 높이
            inventory: 인벤토리
            party: 파티 멤버 리스트
            exploration: 탐험 시스템 (드롭 위치를 알기 위해)
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.inventory = inventory
        self.party = party
        self.exploration = exploration

        self.mode = InventoryMode.BROWSE
        self.cursor = 0  # 아이템 커서
        self.scroll_offset = 0
        self.max_visible = 15  # 한 번에 표시할 아이템 수

        # 필터
        self.filter_type: Optional[ItemType] = None

        # 선택된 아이템/대상
        self.selected_item_index: Optional[int] = None
        self.target_cursor = 0
        self.all_allies_mode = False  # 아군 전체 대상 모드 (텐트 등)

        # 정렬 메뉴
        self.sort_menu: Optional[CursorMenu] = None

        # 캐릭터 장비 관리
        self.selected_character_index: Optional[int] = None
        self.equipment_cursor = 0  # weapon, armor, accessory 선택
        self.equipment_slots = ["weapon", "armor", "accessory"]

        # 파괴 확인
        self.confirm_destroy_item: Optional[int] = None
        self.confirm_yes = False
        self.destroy_quantity: int = 1  # 파괴할 개수
        self.destroy_quantity_input_mode: bool = False  # 개수 입력 모드

        # 드롭 관련
        self.drop_item_index: Optional[int] = None
        self.drop_quantity: int = 1
        self.drop_quantity_input_mode: bool = False
        self.drop_gold_amount: int = 0
        self.drop_gold_input_mode: bool = False

        # 장비 비교 모드
        self.show_comparison = False
        self.selected_character_for_comparison = 0  # 비교할 캐릭터 인덱스

        self.closed = False
        self._pending_gauges = []  # pixel overlay 게이지 큐

    def _queue_gauge(self, console, cell_x: int, cell_y: int, cell_w: int,
                     ratio: float, kind: str = "", custom_color: tuple = None,
                     wound_ratio: float = 0.0) -> None:
        """pixel overlay 스무스 게이지 큐에 추가 + 콘솔 폴백 렌더링

        kind: "hp", "mp", "exp" 등 — combat_ui 와 동일 색상 테이블 사용
        custom_color: kind 대신 직접 색상 지정 (내구도 등)
        """
        # 콘솔 폴백 색상 결정 (전투 UI와 동일한 임계값)
        r = max(0.0, min(1.0, ratio))
        if kind == "hp":
            if r > 0.6:
                fg = (50, 220, 50)
            elif r > 0.3:
                fg = (220, 220, 50)
            else:
                fg = (220, 50, 50)
        elif kind == "mp":
            fg = (100, 150, 255)
        elif kind == "exp":
            fg = (100, 255, 100)
        elif custom_color:
            fg = custom_color
        else:
            fg = (200, 200, 200)
        bg = tuple(max(0, c // 4) for c in fg)
        console.draw_rect(cell_x, cell_y, cell_w, 1, ord(" "), bg=bg)
        filled = max(0, int(cell_w * r))
        if filled > 0:
            console.draw_rect(cell_x, cell_y, filled, 1, ord(" "), bg=fg)
        # kind 또는 custom_color 를 그대로 저장
        color_info = kind if kind else custom_color
        self._pending_gauges.append((cell_x, cell_y, cell_w, ratio, color_info, wound_ratio))

    def _translate_unique_effect(self, effect_str: str) -> str:
        """유니크 효과를 한글로 번역"""
        if not effect_str:
            return ""

        effect_names = {
            # Vision 관련
            "vision": "시야",
            "night_vision": "야간 시야",
            "true_sight": "투시",

            # Wound 관련
            "wound_reduction": "상처 감소",
            "wound_immunity": "상처 면역",
            "wound_regen": "상처 회복",

            # BRV 관련
            "brv_bonus": "BRV 보너스",
            "brv_shield": "BRV 방어",
            "brv_regen": "BRV 재생",
            "brv_steal": "BRV 흡수",
            "brv_break_bonus": "BREAK 데미지",

            # Combat 관련
            "lifesteal": "생명력 흡수",
            "thorns": "가시 (반사)",
            "critical_damage": "크리티컬 데미지",
            "critical_rate": "크리티컬 확률",
            "critical_chance": "크리티컬 확률",
            "dodge_chance": "회피 확률",
            "block_chance": "블록 확률",
            "counter_attack": "반격",
            "first_strike": "선제공격",
            "execute": "처형",
            "multi_strike": "연속 공격",

            # Healing 관련
            "hp_regen": "HP 재생",
            "mp_regen": "MP 재생",
            "heal_boost": "회복량 증가",
            "healing_bonus": "회복량 증가",
            "overheal": "과다 회복 → 실드",
            "overheal_shield": "과다 회복 → 실드",

            # Status 관련
            "status_immunity": "상태이상 면역",
            "poison_immunity": "독 면역",
            "stun_immunity": "기절 면역",
            "silence_immunity": "침묵 면역",
            "burn_immunity": "화상 면역",
            "freeze_immunity": "빙결 면역",
            "status_burn": "화상 부여",
            "status_poison": "독 부여",
            "status_shock": "감전 부여",
            "debuff_slow": "감속 디버프",
            "debuff_silence": "침묵 디버프",
            "debuff_weaken": "약화 디버프",

            # Resource 관련
            "mp_cost_reduction": "MP 소비 감소",
            "cooldown_reduction": "쿨다운 감소",
            "skill_power": "스킬 위력",
            "spell_power": "주문 위력",
            "spell_echo": "주문 반향",
            "rare_drop": "희귀 아이템 드롭",
            "item_find": "아이템 드롭",
            "gold_find": "골드 획득",
            "exp_bonus": "경험치 보너스",

            # 기타 특수 효과
            "on_kill_heal": "처치 시 회복",
            "element": "원소 속성",
            "chain_lightning": "체인 라이트닝",
            "armor_penetration": "방어 관통",
            "mp_steal": "MP 흡수",
            "bonus_vs_undead": "대 언데드",
            "heal_on_hit": "공격 시 회복",
            "accuracy_bonus": "명중률",
            "double_strike": "더블 스트라이크",
            "strike_count": "공격 횟수",
            "stun_chance": "기절 확률",
            "damage_from_defense": "방어력 기반 데미지",
            "hack_damage": "해킹 데미지",
            "stance_power": "스탠스 위력",
            "element_power": "속성 위력",
            "resistance": "저항",
        }

        element_names = {
            "fire": "불",
            "ice": "얼음",
            "thunder": "번개",
            "water": "물",
            "wind": "바람",
            "earth": "대지",
            "light": "빛",
            "dark": "어둠",
        }

        results = []
        parts = effect_str.split("|")

        for part in parts:
            if ":" in part:
                effect_name, value = part.split(":", 1)
                effect_name = effect_name.strip()
                value = value.strip()

                # 원소 처리
                if effect_name == "element":
                    element_kr = element_names.get(value, value)
                    results.append(f"{element_kr} 속성")
                else:
                    # 숫자값 처리
                    try:
                        num_value = float(value)
                        # 백분율 값 처리 (0.15 = 15%)
                        if 0 < num_value < 1:
                            display_value = f"{int(num_value * 100)}%"
                        else:
                            display_value = str(int(num_value)) if num_value == int(num_value) else str(num_value)

                        effect_kr = effect_names.get(effect_name, effect_name)
                        results.append(f"{effect_kr} +{display_value}")
                    except ValueError:
                        effect_kr = effect_names.get(effect_name, effect_name)
                        results.append(f"{effect_kr}: {value}")
            else:
                # 값이 없는 경우
                effect_kr = effect_names.get(part, part)
                results.append(effect_kr)

        return " / ".join(results)

    def _get_durability_info(self, item: Item) -> tuple[str, tuple[int, int, int]]:
        """
        아이템 내구도 정보 및 색상 반환
        Returns:
            (text, color)
        """
        if not hasattr(item, 'current_durability') or not hasattr(item, 'max_durability'):
            return "", Colors.UI_TEXT
        
        # 장비 아이템이 아니면 내구도 표시 안 함 (선택 사항)
        if not isinstance(item, Equipment):
             return "", Colors.UI_TEXT

        current = item.current_durability
        maximum = item.max_durability
        
        if maximum <= 0:
            return "", Colors.UI_TEXT
            
        percent = current / maximum
        
        text = f"[{current}/{maximum}]"
        
        if percent > 0.5:
            color = (100, 255, 100)  # 녹색
        elif percent > 0.2:
            color = (255, 255, 100)  # 노란색
        else:
            color = (255, 100, 100)  # 빨간색
            
        return text, color

    def handle_input(self, action: GameAction) -> bool:
        """
        입력 처리

        Args:
            action: 게임 액션

        Returns:
            닫기 여부
        """
        # 정렬 메뉴가 열려있으면 우선 처리
        if self.sort_menu:
            return self._handle_sort_menu(action)

        if self.mode == InventoryMode.BROWSE:
            return self._handle_browse(action)
        elif self.mode == InventoryMode.USE_ITEM or self.mode == InventoryMode.EQUIP:
            return self._handle_use_or_equip(action)
        elif self.mode == InventoryMode.SELECT_TARGET:
            return self._handle_target_select(action)
        elif self.mode == InventoryMode.CHARACTER_EQUIPMENT:
            return self._handle_character_equipment(action)
        elif self.mode == InventoryMode.UNEQUIP:
            return self._handle_unequip(action)
        elif self.mode == InventoryMode.CONFIRM_DESTROY:
            return self._handle_confirm_destroy(action)
        elif self.mode == InventoryMode.DROP_ITEM:
            return self._handle_drop_item(action)
        elif self.mode == InventoryMode.DROP_GOLD:
            return self._handle_drop_gold(action)

        return False

    def pointer_regions(self) -> tuple[PointerRegion, ...]:
        if self.sort_menu:
            return self.sort_menu.pointer_regions()
        if self.mode != InventoryMode.BROWSE:
            return ()
        regions = []
        for filtered_index in range(self.scroll_offset, min(self.scroll_offset + self.max_visible, self._get_filtered_item_count())):
            actual_index = self._get_actual_slot_index(filtered_index)
            item = self.inventory.get_item(actual_index)
            tooltip = getattr(item, "description", "") if item else "빈 슬롯입니다."
            regions.append(
                PointerRegion(
                    region_id=str(filtered_index),
                    x=5,
                    y=6 + (filtered_index - self.scroll_offset),
                    width=max(50, self.screen_width - 10),
                    height=1,
                    command=GameAction.CONFIRM,
                    tooltip=tooltip,
                    enabled=item is not None,
                )
            )
        return tuple(regions)

    def handle_pointer_event(self, event: PointerEvent) -> PointerDispatchResult:
        if self.sort_menu:
            result = self.sort_menu.handle_pointer_event(event)
            if result.value is not None:
                self._handle_sort_menu(GameAction.CONFIRM)
            return result
        dispatcher = PointerDispatcher(self.pointer_regions())
        result = dispatcher.dispatch(event)
        region = dispatcher.region_at(event.position)
        region_id = result.hovered_region_id or (region.region_id if region else None)
        if region_id is not None:
            self.cursor = int(region_id)
            self._update_scroll()
        if event.kind is PointerEventKind.WHEEL:
            action = GameAction.MOVE_UP if event.wheel_delta > 0 else GameAction.MOVE_DOWN
            value = self.handle_input(action)
            return result.with_value(value)
        if event.kind in (PointerEventKind.DRAG_START, PointerEventKind.DRAG_MOVE, PointerEventKind.DRAG_END):
            if region_id is not None:
                self.cursor = int(region_id)
            return PointerDispatchResult(event=event, hovered_region_id=region_id, tooltip=region.tooltip if region else result.tooltip)
        if event.kind is PointerEventKind.CLICK and event.button is PointerButton.RIGHT:
            value = self.handle_input(GameAction.CANCEL)
            return result.with_value(value)
        if event.kind is PointerEventKind.CLICK and result.action is not None:
            value = self.handle_input(result.action)
            return PointerDispatchResult(event=event, action=result.action, value=value, tooltip=region.tooltip if region else result.tooltip)
        return result

    def _handle_browse(self, action: GameAction) -> bool:
        """둘러보기 모드 입력"""
        if action == GameAction.MOVE_UP:
            # 장비 비교 모드 활성화 시 캐릭터 변경
            if self.show_comparison and len(self.party) > 1:
                self.selected_character_for_comparison = max(0, self.selected_character_for_comparison - 1)
            else:
                self.cursor = max(0, self.cursor - 1)
                self._update_scroll()
                self.show_comparison = False
        elif action == GameAction.MOVE_DOWN:
            # 장비 비교 모드 활성화 시 캐릭터 변경
            if self.show_comparison and len(self.party) > 1:
                self.selected_character_for_comparison = min(len(self.party) - 1, self.selected_character_for_comparison + 1)
            else:
                # 필터링된 아이템 수 기준으로 커서 이동
                filtered_count = self._get_filtered_item_count()
                self.cursor = min(filtered_count - 1, self.cursor + 1)
                self._update_scroll()
                self.show_comparison = False
        elif action == GameAction.USE_CONSUMABLE or action == GameAction.INTERACT:
            # F 키: 음식/소비품 직접 사용 (첫 번째 캐릭터에게 바로 사용)
            if len(self.inventory) > 0:
                # 필터링된 인덱스를 원래 인덱스로 변환
                actual_index = self._get_actual_slot_index(self.cursor)
                item = self.inventory.get_item(actual_index)
                if item:
                    # CookedFood 타입 확인
                    from src.cooking.recipe import CookedFood

                    if isinstance(item, (Consumable, CookedFood)):
                        # 첫 번째 캐릭터에게 바로 사용
                        target = self.party[0] if self.party else None
                        if target:
                            success = self.inventory.use_consumable(actual_index, target, user=self.party[0] if self.party else None)
                            if success:
                                item_name = getattr(item, 'name', '알 수 없는 아이템')
                                logger.info(f"{item_name} 사용 완료 (대상: {target.name})")
                                # 인덱스 조정
                                if self.cursor >= len(self.inventory):
                                    self.cursor = max(0, len(self.inventory) - 1)
                        else:
                            logger.warning("사용할 대상이 없습니다")
        elif action == GameAction.CONFIRM:
            # 아이템 사용/장착
            if len(self.inventory) > 0:
                # 필터링된 인덱스를 원래 인덱스로 변환
                actual_index = self._get_actual_slot_index(self.cursor)
                item = self.inventory.get_item(actual_index)
                if item:
                    # CookedFood 타입 확인
                    from src.cooking.recipe import CookedFood

                    self.selected_item_index = actual_index

                    if isinstance(item, Equipment):
                        # 장비 비교창이 이미 켜져 있으면 장착 실행
                        if self.show_comparison:
                            # 선택된 캐릭터에게 장비 장착
                            target_character = self.party[self.selected_character_for_comparison]
                            self._equip_item(target_character, item)
                            self.show_comparison = False
                        else:
                            # 장비 아이템: 비교 UI 토글
                            self.show_comparison = True
                            # 비교 UI를 켤 때 캐릭터 선택 초기화
                            self.selected_character_for_comparison = 0
                    elif isinstance(item, (Consumable, CookedFood)):
                        # CookedFood는 바로 사용 (아군 전체에 효과)
                        from src.cooking.recipe import CookedFood
                        if isinstance(item, CookedFood):
                            # 음식은 타겟 선택 없이 바로 사용
                            target = self.party[0] if self.party else None  # 더미 타겟
                            success = self.inventory.use_consumable(actual_index, target, user=self.party[0] if self.party else None)
                            if success:
                                item_name = getattr(item, 'name', '알 수 없는 아이템')
                                logger.info(f"{item_name} 사용 완료 (아군 전체)")
                                # 인덱스 조정
                                if self.cursor >= len(self.inventory):
                                    self.cursor = max(0, len(self.inventory) - 1)
                        elif isinstance(item, Consumable):
                            effect_type = getattr(item, 'effect_type', '')
                            if effect_type == 'revive_crystal':
                                # 부활 크리스탈: 죽은 아군만 대상으로 선택
                                dead_party_members = []
                                for member in self.party:
                                    is_alive = getattr(member, 'is_alive', True)
                                    current_hp = getattr(member, 'current_hp', 1)
                                    if not is_alive or current_hp <= 0:
                                        dead_party_members.append(member)

                                if dead_party_members:
                                    # 죽은 아군이 있으면 타겟 선택 모드로
                                    self.mode = InventoryMode.USE_ITEM
                                    logger.info(f"부활 크리스탈 사용: 죽은 파티원 {len(dead_party_members)}명 대상 선택 가능")
                                else:
                                    # 죽은 아군이 없음
                                    logger.warning("부활 크리스탈 사용 실패: 죽은 파티원이 없습니다")
                                    # 메시지 표시 로직이 필요하지만 일단 로그만 출력
                            elif effect_type == "camp_rest":
                                # 텐트 등 아군 전체 대상 아이템: 전체 모드로 전환
                                self.all_allies_mode = True
                                self.mode = InventoryMode.USE_ITEM
                            elif effect_type == "bonus_gold":
                                # 금덩어리: 바로 사용 (타겟 필요 없음)
                                target = self.party[0] if self.party else None
                                success = self.inventory.use_consumable(actual_index, target, user=self.party[0] if self.party else None)
                                if success:
                                    logger.info(f"{item.name} 사용 완료 (골드 획득)")
                                    # 인덱스 조정
                                    if self.cursor >= len(self.inventory):
                                        self.cursor = max(0, len(self.inventory) - 1)
                            else:
                                # 일반 소비품: 사용 모드로 전환
                                self.all_allies_mode = False
                                self.mode = InventoryMode.USE_ITEM
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            play_sfx("ui", "cursor_cancel")
            self.closed = True
            return True
        elif action == GameAction.MOVE_LEFT:
            # 필터 변경
            self._change_filter(-1)
            self.show_comparison = False
        elif action == GameAction.MOVE_RIGHT:
            # 필터 변경
            self._change_filter(1)
            self.show_comparison = False
        elif action == GameAction.MENU:
            # 정렬 메뉴 ('M' 키)
            self._open_sort_menu()
            self.show_comparison = False
        elif action == GameAction.OPEN_CHARACTER:
            # 캐릭터 장비 보기 ('C' 키)
            self.mode = InventoryMode.CHARACTER_EQUIPMENT
            self.target_cursor = 0
            self.show_comparison = False
        elif action == GameAction.INVENTORY_DESTROY or action == GameAction.ATTACK:
            # 아이템 파괴 ('V' 키 또는 게임패드 Y 버튼)
            if len(self.inventory) > 0:
                self.confirm_destroy_item = self.cursor
                self.mode = InventoryMode.CONFIRM_DESTROY
                self.confirm_yes = False
                self.show_comparison = False
        elif action == GameAction.INVENTORY_DROP or action == GameAction.OPEN_INVENTORY:
            # 아이템 드롭 ('D' 키 또는 게임패드 LB 버튼)
            if len(self.inventory) > 0 and self.exploration:
                actual_index = self._get_actual_slot_index(self.cursor)
                self.drop_item_index = actual_index
                self.drop_quantity = 1
                self.drop_quantity_input_mode = False
                self.mode = InventoryMode.DROP_ITEM
                self.show_comparison = False
        elif action == GameAction.INVENTORY_DROP_GOLD:
            # 골드 드롭 ('G' 키)
            if self.exploration and self.inventory.gold > 0:
                self.drop_gold_amount = 0
                self.drop_gold_input_mode = True
                self.mode = InventoryMode.DROP_GOLD

        return False

    def _handle_general_consumable_use(self, action: GameAction, item: Any) -> bool:
        """일반 소비 아이템 사용 모드 입력 (포션 등)"""
        # 아군 전체 대상 모드 (텐트 등)
        if self.all_allies_mode:
            if action == GameAction.CONFIRM:
                # 아군 전체에게 사용 (더미 타겟으로 첫 번째 파티원 전달)
                target = self.party[0] if self.party else None
                success = self.inventory.use_consumable(self.selected_item_index, target, user=self.party[0] if self.party else None)
                if success:
                    item_name = getattr(item, 'name', '알 수 없는 아이템')
                    logger.info(f"{item_name} 사용 완료 (아군 전체)")
                    if self.cursor >= len(self.inventory):
                        self.cursor = max(0, len(self.inventory) - 1)
                self.all_allies_mode = False
                self.mode = InventoryMode.BROWSE
                self.selected_item_index = None
            elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                self.all_allies_mode = False
                self.mode = InventoryMode.BROWSE
                self.selected_item_index = None
            # 커서 이동 무시 (전체 대상이므로)
            return False

        # 살아있는 파티원만 대상으로 선택
        alive_party_members = []
        for member in self.party:
            is_alive = getattr(member, 'is_alive', True)
            current_hp = getattr(member, 'current_hp', 1)
            if is_alive and current_hp > 0:
                alive_party_members.append(member)

        if not alive_party_members:
            # 살아있는 파티원이 없음
            logger.warning("일반 소비 아이템 사용 실패: 살아있는 파티원이 없습니다")
            self.mode = InventoryMode.BROWSE
            self.selected_item_index = None
            return False

        # 타겟 선택
        if action == GameAction.MOVE_UP:
            self.target_cursor = max(0, self.target_cursor - 1)
        elif action == GameAction.MOVE_DOWN:
            self.target_cursor = min(len(alive_party_members) - 1, self.target_cursor + 1)
        elif action == GameAction.CONFIRM:
            # 선택된 살아있는 파티원에게 사용
            target = alive_party_members[self.target_cursor]
            success = self.inventory.use_consumable(self.selected_item_index, target, user=self.party[0] if self.party else None)
            if success:
                item_name = getattr(item, 'name', '알 수 없는 아이템')
                target_name = getattr(target, 'name', '알 수 없는 대상')
                logger.info(f"{item_name} 사용 완료 (대상: {target_name})")
                # 인덱스 조정
                if self.cursor >= len(self.inventory):
                    self.cursor = max(0, len(self.inventory) - 1)

            # 모드 복귀
            self.mode = InventoryMode.BROWSE
            self.selected_item_index = None
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 취소: 모드 복귀
            self.mode = InventoryMode.BROWSE
            self.selected_item_index = None

        return False

    def _handle_revive_crystal_use(self, action: GameAction, item: Any) -> bool:
        """부활 크리스탈 사용 모드 입력"""
        # 죽은 파티원만 대상으로 선택
        dead_party_members = []
        for member in self.party:
            is_alive = getattr(member, 'is_alive', True)
            current_hp = getattr(member, 'current_hp', 1)
            if not is_alive or current_hp <= 0:
                dead_party_members.append(member)

        if not dead_party_members:
            # 죽은 파티원이 없음
            logger.warning("부활 크리스탈 사용 실패: 죽은 파티원이 없습니다")
            self.mode = InventoryMode.BROWSE
            self.selected_item_index = None
            return False

        # 타겟 선택
        if action == GameAction.MOVE_UP:
            self.target_cursor = max(0, self.target_cursor - 1)
        elif action == GameAction.MOVE_DOWN:
            self.target_cursor = min(len(dead_party_members) - 1, self.target_cursor + 1)
        elif action == GameAction.CONFIRM:
            # 선택된 죽은 파티원에게 사용
            target = dead_party_members[self.target_cursor]
            success = self.inventory.use_consumable(self.selected_item_index, target, user=self.party[0] if self.party else None)
            if success:
                item_name = getattr(item, 'name', '알 수 없는 아이템')
                target_name = getattr(target, 'name', '알 수 없는 대상')
                logger.info(f"{item_name} 사용 완료 (대상: {target_name})")
                # 인덱스 조정
                if self.cursor >= len(self.inventory):
                    self.cursor = max(0, len(self.inventory) - 1)

            # 모드 복귀
            self.mode = InventoryMode.BROWSE
            self.selected_item_index = None
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 취소: 모드 복귀
            self.mode = InventoryMode.BROWSE
            self.selected_item_index = None

        return False

    def _handle_use_or_equip(self, action: GameAction) -> bool:
        """아이템 사용/장착 모드 입력"""
        from src.cooking.recipe import CookedFood
        item = self.inventory.get_item(self.selected_item_index)

        # revive_crystal인 경우 죽은 파티원만 대상으로 선택
        if isinstance(item, Consumable) and getattr(item, 'effect_type', '') == 'revive_crystal':
            return self._handle_revive_crystal_use(action, item)

        # 일반 Consumable인 경우 살아있는 파티원만 대상으로 선택
        if isinstance(item, Consumable):
            return self._handle_general_consumable_use(action, item)

        # CookedFood인 경우 타겟 선택 없이 바로 사용 (아군 전체에 효과)
        if isinstance(item, CookedFood):
            if action == GameAction.CONFIRM:
                # 음식은 아군 전체에게 효과 적용 (target은 무시됨)
                target = self.party[0] if self.party else None  # 더미 타겟
                success = self.inventory.use_consumable(self.selected_item_index, target, user=self.party[0] if self.party else None)
                if success:
                    item_name = getattr(item, 'name', '알 수 없는 아이템')
                    logger.info(f"{item_name} 사용 완료 (아군 전체)")
                    # 인덱스 조정
                    if self.cursor >= len(self.inventory):
                        self.cursor = max(0, len(self.inventory) - 1)
                
                # 모드 복귀
                self.mode = InventoryMode.BROWSE
                self.selected_item_index = None
            elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                # 취소: 모드 복귀
                self.mode = InventoryMode.BROWSE
                self.selected_item_index = None
            return False
        
        # 일반 소비품/장비는 기존처럼 타겟 선택
        if action == GameAction.MOVE_UP:
            self.target_cursor = max(0, self.target_cursor - 1)
        elif action == GameAction.MOVE_DOWN:
            self.target_cursor = min(len(self.party) - 1, self.target_cursor + 1)
        elif action == GameAction.CONFIRM:
            # 대상에게 사용/장착
            target = self.party[self.target_cursor]
            item = self.inventory.get_item(self.selected_item_index)

            # CookedFood 타입 확인
            from src.cooking.recipe import CookedFood

            if isinstance(item, (Consumable, CookedFood)):
                # 소비 아이템 또는 요리 사용
                success = self.inventory.use_consumable(self.selected_item_index, target, user=self.party[0] if self.party else None)
                if success:
                    item_name = getattr(item, 'name', '알 수 없는 아이템')
                    logger.info(f"{item_name} 사용 완료")
                    # 인덱스 조정
                    if self.cursor >= len(self.inventory):
                        self.cursor = max(0, len(self.inventory) - 1)
            elif isinstance(item, Equipment):
                # 장비 착용
                self._equip_item(target, item)

            # 모드 복귀
            self.mode = InventoryMode.BROWSE
            self.selected_item_index = None

        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 취소
            self.mode = InventoryMode.BROWSE
            self.selected_item_index = None

        return False

    def _handle_target_select(self, action: GameAction) -> bool:
        """대상 선택 모드 입력"""
        # USE_ITEM과 동일
        return self._handle_use_or_equip(action)

    def _handle_character_equipment(self, action: GameAction) -> bool:
        """캐릭터 장비 보기 모드"""
        if action == GameAction.MOVE_UP:
            self.target_cursor = max(0, self.target_cursor - 1)
        elif action == GameAction.MOVE_DOWN:
            self.target_cursor = min(len(self.party) - 1, self.target_cursor + 1)
        elif action == GameAction.CONFIRM:
            # 캐릭터 선택 → 장비 해제 모드로
            self.selected_character_index = self.target_cursor
            self.mode = InventoryMode.UNEQUIP
            self.equipment_cursor = 0
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            self.mode = InventoryMode.BROWSE
            self.selected_character_index = None

        return False

    def _handle_unequip(self, action: GameAction) -> bool:
        """장비 해제 모드"""
        if action == GameAction.MOVE_UP:
            self.equipment_cursor = max(0, self.equipment_cursor - 1)
        elif action == GameAction.MOVE_DOWN:
            self.equipment_cursor = min(len(self.equipment_slots) - 1, self.equipment_cursor + 1)
        elif action == GameAction.CONFIRM:
            # 장비 해제
            character = self.party[self.selected_character_index]
            slot = self.equipment_slots[self.equipment_cursor]

            # 장비가 있는지 확인
            if character.equipment.get(slot):
                item = character.unequip_item(slot)
                if item:
                    # 인벤토리에 추가
                    item_name = getattr(item, 'name', '알 수 없는 아이템')
                    char_name = getattr(character, 'name', '알 수 없는 캐릭터')
                    if self.inventory.add_item(item):
                        logger.info(f"{char_name}: {item_name} 해제 → 인벤토리")
                    else:
                        # 인벤토리 가득 참 - 다시 장착
                        character.equip_item(slot, item)
                        logger.warning(f"인벤토리 가득 참! {item_name} 해제 실패")
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 캐릭터 선택 모드로 복귀
            self.mode = InventoryMode.CHARACTER_EQUIPMENT
            self.selected_character_index = None

        return False

    def _handle_confirm_destroy(self, action: GameAction) -> bool:
        """아이템 파괴 확인"""
        item = self.inventory.get_item(self.confirm_destroy_item) if self.confirm_destroy_item is not None else None
        if not item:
            self.mode = InventoryMode.BROWSE
            return False
        
        # 스택 가능 여부 확인
        from src.gathering.ingredient import Ingredient
        from src.cooking.recipe import CookedFood
        is_stackable = not isinstance(item, Equipment)
        slot = self.inventory.slots[self.confirm_destroy_item] if self.confirm_destroy_item < len(self.inventory.slots) else None
        max_quantity = slot.quantity if slot else 1
        
        # 개수 입력 모드
        if self.destroy_quantity_input_mode and is_stackable:
            if action == GameAction.MOVE_UP:
                self.destroy_quantity = min(max_quantity, self.destroy_quantity + 1)
            elif action == GameAction.MOVE_DOWN:
                self.destroy_quantity = max(1, self.destroy_quantity - 1)
            elif action == GameAction.MOVE_LEFT:
                self.destroy_quantity = max(1, self.destroy_quantity - 10)
            elif action == GameAction.MOVE_RIGHT:
                self.destroy_quantity = min(max_quantity, self.destroy_quantity + 10)
            elif action == GameAction.CONFIRM:
                # 개수 입력 완료 - 파괴 실행
                destroy_qty = self.destroy_quantity
                self.inventory.remove_item(self.confirm_destroy_item, destroy_qty)
                item_name = getattr(item, 'name', '알 수 없는 아이템')
                logger.info(f"{item_name} {destroy_qty}개 파괴됨")

                # 커서 조정
                if self.cursor >= len(self.inventory) and len(self.inventory) > 0:
                    self.cursor = max(0, len(self.inventory) - 1)
                elif len(self.inventory) == 0:
                    self.cursor = 0

                # 모드 복귀
                self.mode = InventoryMode.BROWSE
                self.confirm_destroy_item = None
                self.destroy_quantity = 1
                self.destroy_quantity_input_mode = False
            elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                # 개수 입력 취소
                self.destroy_quantity_input_mode = False
                self.destroy_quantity = 1
            return False
        
        # 일반 확인 모드
        if action == GameAction.MOVE_LEFT:
            self.confirm_yes = True
        elif action == GameAction.MOVE_RIGHT:
            self.confirm_yes = False
        elif action == GameAction.CONFIRM:
            if self.confirm_yes:
                # 스택형 아이템이고 개수 입력이 필요하면 개수 입력 모드로
                if is_stackable and max_quantity > 1:
                    self.destroy_quantity_input_mode = True
                    self.destroy_quantity = min(max_quantity, self.destroy_quantity)
                    return False
                
                # 파괴 실행 (비스택형이거나 1개만 있는 경우)
                destroy_qty = 1
                self.inventory.remove_item(self.confirm_destroy_item, destroy_qty)
                item_name = getattr(item, 'name', '알 수 없는 아이템')
                logger.info(f"{item_name} 파괴됨")

                # 커서 조정
                if self.cursor >= len(self.inventory) and len(self.inventory) > 0:
                    self.cursor = max(0, len(self.inventory) - 1)
                elif len(self.inventory) == 0:
                    self.cursor = 0

                # 모드 복귀
                self.mode = InventoryMode.BROWSE
                self.confirm_destroy_item = None
                self.destroy_quantity = 1
                self.destroy_quantity_input_mode = False
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 취소
            self.mode = InventoryMode.BROWSE
            self.confirm_destroy_item = None
            self.destroy_quantity = 1
            self.destroy_quantity_input_mode = False

        return False

    def _handle_drop_item(self, action: GameAction) -> bool:
        """아이템 드롭 모드 입력"""
        if self.drop_item_index is None or not self.exploration:
            self.mode = InventoryMode.BROWSE
            return False
        
        item = self.inventory.get_item(self.drop_item_index)
        if not item:
            self.mode = InventoryMode.BROWSE
            return False
        
        # 스택 가능 여부 확인
        slot = self.inventory.slots[self.drop_item_index]
        is_stackable = slot.quantity > 1
        max_quantity = slot.quantity
        
        # 개수 입력 모드
        if self.drop_quantity_input_mode:
            if action == GameAction.MOVE_UP:
                self.drop_quantity = min(max_quantity, self.drop_quantity + 1)
            elif action == GameAction.MOVE_DOWN:
                self.drop_quantity = max(1, self.drop_quantity - 1)
            elif action == GameAction.MOVE_LEFT:
                self.drop_quantity = max(1, self.drop_quantity - 10)
            elif action == GameAction.MOVE_RIGHT:
                self.drop_quantity = min(max_quantity, self.drop_quantity + 10)
            elif action == GameAction.CONFIRM:
                # 드롭 실행
                drop_qty = self.drop_quantity
                dropped_item = self.inventory.remove_item(self.drop_item_index, drop_qty)
                if dropped_item:
                    # 플레이어 위치에 아이템 드롭
                    player_x = self.exploration.player.x
                    player_y = self.exploration.player.y
                    tile = self.exploration.dungeon.get_tile(player_x, player_y)
                    if tile:
                        from src.world.tile import TileType
                    tile.tile_type = TileType.DROPPED_ITEM
                    tile.dropped_item = dropped_item
                    item_name = getattr(dropped_item, 'name', '알 수 없는 아이템')
                    
                    # 멀티플레이어: 드롭한 플레이어 ID 설정
                    dropped_by_player_id = None
                    if hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer:
                        if hasattr(self.exploration, 'local_player_id'):
                            dropped_by_player_id = self.exploration.local_player_id
                        elif hasattr(self.exploration, 'session') and self.exploration.session:
                            dropped_by_player_id = getattr(self.exploration.session, 'local_player_id', None)
                    tile.dropped_by_player_id = dropped_by_player_id
                    
                    logger.info(f"{item_name} {drop_qty}개 드롭됨 ({player_x}, {player_y}) by {dropped_by_player_id}")
                    
                    # 멀티플레이어: 드롭 동기화
                    if hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer:
                        if hasattr(self.exploration, 'network_manager') and self.exploration.network_manager:
                            from src.multiplayer.protocol import MessageBuilder
                            import asyncio
                            try:
                                # 아이템 데이터 직렬화
                                item_data = {
                                    "name": item_name,
                                    "item_id": getattr(dropped_item, 'item_id', None),
                                    "item_type": getattr(dropped_item, 'item_type', None).value if hasattr(getattr(dropped_item, 'item_type', None), 'value') else str(getattr(dropped_item, 'item_type', None)),
                                }
                                drop_msg = MessageBuilder.item_dropped(player_x, player_y, item_data, dropped_by_player_id)
                                loop = asyncio.get_event_loop()
                                if loop.is_running():
                                    asyncio.create_task(self.exploration.network_manager.broadcast(drop_msg))
                                else:
                                    loop.run_until_complete(self.exploration.network_manager.broadcast(drop_msg))
                                logger.debug(f"아이템 드롭 동기화 메시지 전송: ({player_x}, {player_y})")
                            except Exception as e:
                                logger.error(f"아이템 드롭 동기화 메시지 전송 실패: {e}", exc_info=True)
                
                # 모드 복귀
                self.mode = InventoryMode.BROWSE
                self.drop_item_index = None
                self.drop_quantity = 1
                self.drop_quantity_input_mode = False
            elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                # 취소
                self.drop_quantity_input_mode = False
                self.drop_quantity = 1
            return False
        
        # 일반 확인 모드 - Z로 확인, X로 취소
        if action == GameAction.CONFIRM:
            if is_stackable and max_quantity > 1:
                # 개수 입력 모드로 전환
                self.drop_quantity_input_mode = True
                self.drop_quantity = 1
            else:
                # 바로 드롭
                dropped_item = self.inventory.remove_item(self.drop_item_index, 1)
                if dropped_item:
                    player_x = self.exploration.player.x
                    player_y = self.exploration.player.y
                    tile = self.exploration.dungeon.get_tile(player_x, player_y)
                    if tile:
                        from src.world.tile import TileType
                        tile.tile_type = TileType.DROPPED_ITEM
                        tile.dropped_item = dropped_item
                        item_name = getattr(dropped_item, 'name', '알 수 없는 아이템')
                        logger.info(f"{item_name} 드롭됨 ({player_x}, {player_y})")

                        # 멀티플레이어: 드롭 동기화
                        if hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer:
                            if hasattr(self.exploration, 'network_manager') and self.exploration.network_manager:
                                from src.multiplayer.protocol import MessageBuilder
                                import asyncio
                                try:
                                    # 아이템 데이터 직렬화
                                    item_data = {
                                        "name": item_name,
                                        "item_id": getattr(dropped_item, 'item_id', None),
                                        "item_type": getattr(dropped_item, 'item_type', None).value if hasattr(getattr(dropped_item, 'item_type', None), 'value') else str(getattr(dropped_item, 'item_type', None)),
                                    }
                                    drop_msg = MessageBuilder.item_dropped(player_x, player_y, item_data)
                                    loop = asyncio.get_event_loop()
                                    if loop.is_running():
                                        asyncio.create_task(self.exploration.network_manager.broadcast(drop_msg))
                                    else:
                                        loop.run_until_complete(self.exploration.network_manager.broadcast(drop_msg))
                                    logger.debug(f"아이템 드롭 동기화 메시지 전송: ({player_x}, {player_y})")
                                except Exception as e:
                                    logger.error(f"아이템 드롭 동기화 메시지 전송 실패: {e}", exc_info=True)

                # 모드 복귀
                self.mode = InventoryMode.BROWSE
                self.drop_item_index = None
                self.drop_quantity = 1
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 취소
            self.mode = InventoryMode.BROWSE
            self.drop_item_index = None
            self.drop_quantity = 1
            self.drop_quantity_input_mode = False
        
        return False

    def _handle_drop_gold(self, action: GameAction) -> bool:
        """골드 드롭 모드 입력"""
        if not self.exploration:
            self.mode = InventoryMode.BROWSE
            return False
        
        max_gold = self.inventory.gold
        
        # 골드 입력 모드
        if self.drop_gold_input_mode:
            if action == GameAction.MOVE_UP:
                self.drop_gold_amount = min(max_gold, self.drop_gold_amount + 1)
            elif action == GameAction.MOVE_DOWN:
                self.drop_gold_amount = max(0, self.drop_gold_amount - 1)
            elif action == GameAction.MOVE_LEFT:
                self.drop_gold_amount = max(0, self.drop_gold_amount - 10)
            elif action == GameAction.MOVE_RIGHT:
                self.drop_gold_amount = min(max_gold, self.drop_gold_amount + 10)
            elif action == GameAction.CONFIRM:
                # 골드 드롭 실행
                if self.drop_gold_amount > 0 and self.drop_gold_amount <= max_gold:
                    self.inventory.gold -= self.drop_gold_amount
                    # 플레이어 위치에 골드 드롭
                    player_x = self.exploration.player.x
                    player_y = self.exploration.player.y
                    tile = self.exploration.dungeon.get_tile(player_x, player_y)
                    if tile:
                        from src.world.tile import TileType
                        tile.tile_type = TileType.GOLD
                        tile.gold_amount = self.drop_gold_amount
                        
                        # 멀티플레이어: 드롭한 플레이어 ID 설정
                        dropped_by_player_id = None
                        if hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer:
                            if hasattr(self.exploration, 'local_player_id'):
                                dropped_by_player_id = self.exploration.local_player_id
                            elif hasattr(self.exploration, 'session') and self.exploration.session:
                                dropped_by_player_id = getattr(self.exploration.session, 'local_player_id', None)
                        tile.dropped_by_player_id = dropped_by_player_id
                        
                        logger.info(f"골드 {self.drop_gold_amount}G 드롭됨 ({player_x}, {player_y}) by {dropped_by_player_id}")
                        
                        # 멀티플레이어: 골드 드롭 동기화
                        if hasattr(self.exploration, 'is_multiplayer') and self.exploration.is_multiplayer:
                            if hasattr(self.exploration, 'network_manager') and self.exploration.network_manager:
                                from src.multiplayer.protocol import MessageBuilder
                                import asyncio
                                try:
                                    gold_msg = MessageBuilder.gold_dropped(player_x, player_y, self.drop_gold_amount, dropped_by_player_id)
                                    loop = asyncio.get_event_loop()
                                    if loop.is_running():
                                        asyncio.create_task(self.exploration.network_manager.broadcast(gold_msg))
                                    else:
                                        loop.run_until_complete(self.exploration.network_manager.broadcast(gold_msg))
                                    logger.debug(f"골드 드롭 동기화 메시지 전송: ({player_x}, {player_y}) {self.drop_gold_amount}G")
                                except Exception as e:
                                    logger.error(f"골드 드롭 동기화 메시지 전송 실패: {e}", exc_info=True)
                
                # 모드 복귀
                self.mode = InventoryMode.BROWSE
                self.drop_gold_amount = 0
                self.drop_gold_input_mode = False
            elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                # 취소
                self.mode = InventoryMode.BROWSE
                self.drop_gold_amount = 0
                self.drop_gold_input_mode = False
            return False
        
        return False

    def _handle_sort_menu(self, action: GameAction) -> bool:
        """정렬 메뉴 처리"""
        if action == GameAction.MOVE_UP:
            if self.sort_menu:
                self.sort_menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            if self.sort_menu:
                self.sort_menu.move_cursor_down()
        elif action == GameAction.CONFIRM:
            if self.sort_menu:
                selected = self.sort_menu.get_selected_item()
                if selected:
                    sort_type = selected.data
                    if sort_type == "rarity":
                        self.inventory.sort_by_rarity()
                        logger.info("인벤토리 정렬: 등급순")
                    elif sort_type == "type":
                        self.inventory.sort_by_type()
                        logger.info("인벤토리 정렬: 타입순")
                    elif sort_type == "name":
                        self.inventory.sort_by_name()
                        logger.info("인벤토리 정렬: 이름순")

                    # 커서 초기화
                    self.cursor = 0
                    self.scroll_offset = 0

                self.sort_menu = None
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            self.sort_menu = None

        return False

    def _update_scroll(self):
        """스크롤 업데이트"""
        if self.cursor < self.scroll_offset:
            self.scroll_offset = self.cursor
        elif self.cursor >= self.scroll_offset + self.max_visible:
            self.scroll_offset = self.cursor - self.max_visible + 1

    def _get_filtered_item_count(self) -> int:
        """필터링된 아이템 수 반환"""
        count = 0
        from src.cooking.recipe import CookedFood
        for slot in self.inventory.slots:
            # CookedFood는 소비품으로 취급
            if isinstance(slot.item, CookedFood):
                current_type = ItemType.CONSUMABLE
            else:
                current_type = getattr(slot.item, 'item_type', ItemType.CONSUMABLE)

            if self.filter_type is None or current_type == self.filter_type:
                count += 1
        return count

    def _get_actual_slot_index(self, filtered_index: int) -> int:
        """필터링된 인덱스를 원래 인벤토리 인덱스로 변환"""
        visible_items = []
        from src.cooking.recipe import CookedFood
        for i, slot in enumerate(self.inventory.slots):
            # CookedFood는 소비품으로 취급
            if isinstance(slot.item, CookedFood):
                current_type = ItemType.CONSUMABLE
            else:
                current_type = getattr(slot.item, 'item_type', ItemType.CONSUMABLE)

            if self.filter_type is None or current_type == self.filter_type:
                visible_items.append(i)

        if 0 <= filtered_index < len(visible_items):
            return visible_items[filtered_index]
        return filtered_index  # 범위 밖이면 그대로 반환

    def _change_filter(self, direction: int):
        """필터 변경"""
        filters = [None, ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY, ItemType.CONSUMABLE]

        if self.filter_type is None:
            current_idx = 0
        else:
            current_idx = filters.index(self.filter_type)

        new_idx = (current_idx + direction) % len(filters)
        self.filter_type = filters[new_idx]

        # 커서 초기화 및 스크롤 업데이트
        self.cursor = 0
        self.scroll_offset = 0
        self._update_scroll()  # 화면 스크롤 업데이트

        logger.debug(f"필터 변경: {self.filter_type}")

    def _open_sort_menu(self):
        """정렬 메뉴 열기"""
        items = [
            MenuItem(text="등급순", description="전설 → 일반", enabled=True, value="rarity"),
            MenuItem(text="타입순", description="무기 → 소비품", enabled=True, value="type"),
            MenuItem(text="이름순", description="가나다순", enabled=True, value="name"),
        ]

        self.sort_menu = CursorMenu(
            title="정렬",
            items=items,
            x=30,
            y=15,
            width=25
        )

    def _equip_item(self, character: Any, item: Equipment):
        """장비 착용"""
        # 레벨 제한 체크
        char_level = getattr(character, 'level', 1)
        item_level_req = getattr(item, 'level_requirement', 1)
        
        if item_level_req > char_level:
            char_name = getattr(character, 'name', '알 수 없는 캐릭터')
            item_name = getattr(item, 'name', '알 수 없는 아이템')
            logger.warning(f"{char_name}은(는) 레벨 {item_level_req} 이상이어야 {item_name}을(를) 장착할 수 있습니다. (현재 레벨: {char_level})")
            return  # 레벨 부족으로 장착 실패

        # 장비 슬롯 결정 (안전하게 처리)
        equip_slot = getattr(item, 'equip_slot', None)
        if equip_slot and hasattr(equip_slot, 'value'):
            slot_name = equip_slot.value  # "weapon", "armor", "accessory"
        else:
            # equip_slot이 없으면 item_type에 따라 결정
            from src.equipment.item_system import ItemType
            item_type = getattr(item, 'item_type', None)
            if item_type == ItemType.WEAPON:
                slot_name = "weapon"
            elif item_type == ItemType.ARMOR:
                slot_name = "armor"
            elif item_type == ItemType.ACCESSORY:
                slot_name = "accessory"
            else:
                # 기본값으로 weapon 사용
                slot_name = "weapon"
                logger.warning(f"아이템 {getattr(item, 'name', '알 수 없는 아이템')}의 equip_slot을 확인할 수 없어 weapon 슬롯으로 설정합니다.")
        
        # 슬롯 이름 검증
        if slot_name not in ["weapon", "armor", "accessory"]:
            logger.error(f"잘못된 장비 슬롯: {slot_name} (아이템: {getattr(item, 'name', '알 수 없는 아이템')})")
            return

        # 캐릭터 이름 미리 가져오기
        char_name = getattr(character, 'name', '알 수 없는 캐릭터')

        # 기존 장비 해제
        old_item = character.equipment.get(slot_name)
        if old_item:
            # 인벤토리에 되돌림
            self.inventory.add_item(old_item)
            old_item_name = getattr(old_item, 'name', '알 수 없는 아이템')
            logger.info(f"{char_name}: {old_item_name} 해제")

        # 새 장비 착용
        character.equip_item(slot_name, item)
        item_name = getattr(item, 'name', '알 수 없는 아이템')
        logger.info(f"{char_name}: {item_name} 착용")

        # 인벤토리에서 제거
        self.inventory.remove_item(self.selected_item_index)

    def render(self, console: tcod.console.Console):
        """인벤토리 화면 렌더링"""
        render_space_background(console, self.screen_width, self.screen_height)

        # 제목
        title = "인벤토리"
        console.print(
            (self.screen_width - len(title)) // 2,
            1,
            title,
            fg=Colors.UI_TEXT_SELECTED
        )

        # 골드
        gold_text = f"골드: {self.inventory.gold}G"
        console.print(
            self.screen_width - len(gold_text) - 2,
            1,
            gold_text,
            fg=(255, 215, 0)
        )

        # 필터 표시
        filter_text = "전체"
        if self.filter_type == ItemType.WEAPON:
            filter_text = "무기"
        elif self.filter_type == ItemType.ARMOR:
            filter_text = "방어구"
        elif self.filter_type == ItemType.ACCESSORY:
            filter_text = "악세서리"
        elif self.filter_type == ItemType.CONSUMABLE:
            filter_text = "소비품"

        console.print(
            5,
            3,
            f"필터: {filter_text} (← →)",
            fg=Colors.GRAY
        )

        # 무게 정보
        current = self.inventory.current_weight
        maximum = self.inventory.max_weight
        weight_percent = (current / maximum * 100) if maximum > 0 else 0

        weight_color = Colors.UI_TEXT
        if weight_percent >= 90:
            weight_color = (255, 100, 100)  # 빨강 (거의 가득)
        elif weight_percent >= 70:
            weight_color = (255, 255, 100)  # 노랑 (많이 참)

        console.print(
            self.screen_width - 30,
            3,
            f"무게: {current}kg/{maximum}kg ({int(weight_percent)}%)",
            fg=weight_color
        )

        # 무게 제한 세부 내역 (작게 표시)
        if hasattr(self.inventory, 'weight_breakdown'):
            breakdown = self.inventory.weight_breakdown
            detail_text = (
                f"기본{int(breakdown['base'])} "
                f"+파티{int(breakdown['party_count'])} "
                f"+힘{int(breakdown['strength_bonus'])} "
                f"+Lv{int(breakdown['level_bonus'])}"
            )
            console.print(
                self.screen_width - 30,
                4,
                detail_text,
                fg=Colors.DARK_GRAY
            )

        # 아이템 목록
        y = 5
        console.print(5, y, "─" * 70, fg=Colors.UI_BORDER)
        y += 1

        # 필터링
        visible_items = []
        from src.cooking.recipe import CookedFood
        for i, slot in enumerate(self.inventory.slots):
            # CookedFood는 소비품으로 취급
            if isinstance(slot.item, CookedFood):
                current_type = ItemType.CONSUMABLE
            else:
                # 안전하게 item_type 속성 접근 (기본값 CONSUMABLE)
                current_type = getattr(slot.item, 'item_type', ItemType.CONSUMABLE)

            if self.filter_type is None or current_type == self.filter_type:
                visible_items.append((i, slot))

        # 스크롤된 아이템 표시
        for idx, (slot_idx, slot) in enumerate(visible_items[self.scroll_offset:self.scroll_offset + self.max_visible]):
            item = slot.item
            # 필터링된 리스트의 인덱스로 선택 확인
            filtered_idx = self.scroll_offset + idx
            is_selected = (self.cursor == filtered_idx and self.mode == InventoryMode.BROWSE)

            # 선택 표시
            prefix = "►" if is_selected else " "

            # 아이템 이름 (등급 색상) - 안전하게 rarity 접근
            item_rarity = getattr(item, 'rarity', None)
            if getattr(item, 'item_type', None) == ItemType.FOOD:
                rarity_color = Colors.FOOD
            elif item_rarity:
                rarity_color = getattr(item_rarity, 'color', Colors.UI_TEXT)
            else:
                rarity_color = Colors.UI_TEXT
            item_name = getattr(item, 'name', '알 수 없는 아이템')

            # 수량 표시 (스택형 아이템은 항상 표시, 1개일 때도 표시)
            from src.gathering.ingredient import Ingredient
            from src.cooking.recipe import CookedFood
            is_stackable = not isinstance(item, Equipment)
            if is_stackable:
                item_name += f" x{slot.quantity}"

            # 레벨 요구사항
            if hasattr(item, 'level_requirement') and item.level_requirement > 1:
                item_name += f" (Lv.{item.level_requirement})"

            # 내구도 표시
            dur_text, dur_color = self._get_durability_info(item)
            
            # 아이템 이름 출력
            console.print(
                5,
                y,
                f"{prefix} {item_name}",
                fg=rarity_color if is_selected else Colors.UI_TEXT
            )
            
            # 내구도 출력 (이름 뒤에)
            if dur_text:
                name_len = len(f"{prefix} {item_name}")
                console.print(
                    5 + name_len + 1,
                    y,
                    dur_text,
                    fg=dur_color
                )

            y += 1

        # 스크롤 표시
        if len(visible_items) > self.max_visible:
            scroll_info = f"(↑↓: {self.scroll_offset + 1}-{min(self.scroll_offset + self.max_visible, len(visible_items))} / {len(visible_items)})"
            console.print(5, y, scroll_info, fg=Colors.DARK_GRAY)
            y += 1

        # 아이템 상세 정보
        y += 1
        if len(self.inventory) > 0:
            actual_index = self._get_actual_slot_index(self.cursor)
            item = self.inventory.get_item(actual_index)
            if item:
                self._render_item_details(console, item, 5, y)

        # 대상 선택 모드
        if self.mode in [InventoryMode.USE_ITEM, InventoryMode.EQUIP]:
            self._render_target_selection(console)

        # 캐릭터 장비 보기 모드
        if self.mode == InventoryMode.CHARACTER_EQUIPMENT:
            self._render_character_selection(console, "장비 보기")

        # 장비 해제 모드
        if self.mode == InventoryMode.UNEQUIP:
            self._render_equipment_unequip(console)

        # 파괴 확인 모드
        if self.mode == InventoryMode.CONFIRM_DESTROY:
            self._render_destroy_confirm(console)

        # 드롭 모드
        if self.mode == InventoryMode.DROP_ITEM:
            self._render_drop_item(console)
        elif self.mode == InventoryMode.DROP_GOLD:
            self._render_drop_gold(console)

        # 정렬 메뉴
        if self.sort_menu:
            self.sort_menu.render(console)

        # 장비 비교 (BROWSE 모드에서 confirm 시)
        if self.mode == InventoryMode.BROWSE and self.show_comparison and len(self.inventory) > 0:
            actual_index = self._get_actual_slot_index(self.cursor)
            item = self.inventory.get_item(actual_index)
            if item and isinstance(item, Equipment):
                self._render_equipment_comparison(console, item)

        # 도움말 (게임패드 연결 시 게임패드 버튼으로 표시)
        help_y = self.screen_height - 2
        is_gamepad = unified_input_handler.gamepad_connected
        
        if self.mode == InventoryMode.BROWSE:
            if is_gamepad:
                # Xbox 기준: A=확인, B=취소, X=상호작용, Y=공격, LB=인벤, RB=캐릭터, Start=메뉴
                help_text = "X: 먹기  A: 사용/비교  RB: 캐릭터장비  Y: 파괴  LB: 드롭  Start: 정렬  ←→: 필터  B: 닫기"
            else:
                help_text = "F: 먹기  Z: 사용/비교  C: 캐릭터 장비  V: 파괴  D: 드롭  G: 골드드롭  M: 정렬  ←→: 필터  X: 닫기"
            console.print(2, help_y, help_text, fg=Colors.GRAY)
        elif self.mode == InventoryMode.CHARACTER_EQUIPMENT:
            if is_gamepad:
                help_text = "↑↓: 캐릭터 선택  A: 확인  B: 취소"
            else:
                help_text = "↑↓: 캐릭터 선택  Z: 확인  X: 취소"
            console.print(2, help_y, help_text, fg=Colors.GRAY)
        elif self.mode == InventoryMode.UNEQUIP:
            if is_gamepad:
                help_text = "↑↓: 장비 슬롯 선택  A: 해제  B: 뒤로"
            else:
                help_text = "↑↓: 장비 슬롯 선택  Z: 해제  X: 뒤로"
            console.print(2, help_y, help_text, fg=Colors.GRAY)
        elif self.mode == InventoryMode.CONFIRM_DESTROY:
            # 개수 입력 모드인지 확인
            if self.destroy_quantity_input_mode:
                if is_gamepad:
                    help_text = "↑↓: ±1  ←→: ±10  A: 확인  B: 취소"
                else:
                    help_text = "↑↓: ±1  ←→: ±10  Z: 확인  X: 취소"
            else:
                if is_gamepad:
                    help_text = "←→: 선택  A: 확인/개수선택  B: 취소"
                else:
                    help_text = "←→: 선택  Z: 확인/개수선택  X: 취소"
            console.print(2, help_y, help_text, fg=Colors.GRAY)
        elif self.mode == InventoryMode.DROP_ITEM:
            if self.drop_quantity_input_mode:
                if is_gamepad:
                    help_text = "↑↓: ±1  ←→: ±10  A: 드롭  B: 취소"
                else:
                    help_text = "↑↓: ±1  ←→: ±10  Z: 드롭  X: 취소"
            else:
                if is_gamepad:
                    help_text = "A: 드롭  B: 취소"
                else:
                    help_text = "Z: 드롭  X: 취소"
            console.print(2, help_y, help_text, fg=Colors.GRAY)
        elif self.mode == InventoryMode.DROP_GOLD:
            if self.drop_gold_input_mode:
                if is_gamepad:
                    help_text = f"↑↓: ±1  ←→: ±10  A: 드롭 ({self.drop_gold_amount}G)  B: 취소"
                else:
                    help_text = f"↑↓: ±1  ←→: ±10  Z: 드롭 ({self.drop_gold_amount}G)  X: 취소"
            else:
                help_text = "골드 액수 입력 중..."
            console.print(2, help_y, help_text, fg=Colors.GRAY)
        elif self.mode in [InventoryMode.USE_ITEM, InventoryMode.EQUIP]:
            if is_gamepad:
                help_text = "↑↓: 대상 선택  A: 확인  B: 취소"
            else:
                help_text = "↑↓: 대상 선택  Z: 확인  X: 취소"
            console.print(2, help_y, help_text, fg=Colors.GRAY)

    def _render_item_details(self, console: tcod.console.Console, item: Item, x: int, y: int):
        """아이템 상세 정보 렌더링"""
        console.print(x, y, "─" * 70, fg=Colors.UI_BORDER)
        y += 1

        # 이름 + 등급 (안전하게 rarity 접근)
        item_rarity = getattr(item, 'rarity', None)
        if getattr(item, 'item_type', None) == ItemType.FOOD:
            rarity_name = '음식'
            rarity_color = Colors.FOOD
        elif item_rarity:
            rarity_name = getattr(item_rarity, 'display_name', '일반')
            rarity_color = getattr(item_rarity, 'color', Colors.UI_TEXT)
        else:
            rarity_name = '일반'
            rarity_color = Colors.UI_TEXT

        item_name = getattr(item, 'name', '알 수 없는 아이템')
        console.print(
            x,
            y,
            f"{item_name} [{rarity_name}]",
            fg=rarity_color
        )
        y += 1

        # 설명
        console.print(x, y, item.description, fg=Colors.DARK_GRAY)
        y += 1

        # 무게
        console.print(x, y, f"무게: {item.weight}kg", fg=Colors.DARK_GRAY)
        y += 1

        # 내구도 (상세 정보창)
        dur_text, dur_color = self._get_durability_info(item)
        if dur_text:
            console.print(x, y, f"내구도: {dur_text}", fg=dur_color)
            y += 1

        # 장비 정보
        if isinstance(item, Equipment):
            y += 1
            console.print(x, y, "기본 스탯:", fg=Colors.UI_TEXT)
            y += 1

            # 스탯 이름 한글 매핑
            stat_names = {
                "hp": "HP",
                "mp": "MP",
                "physical_attack": "물리 공격력",
                "physical_defense": "물리 방어력",
                "magic_attack": "마법 공격력",
                "magic_defense": "마법 방어력",
                "speed": "속도",
                "accuracy": "명중률",
                "evasion": "회피율",
                "luck": "행운",
                "strength": "힘",
                "defense": "방어력",
                "magic": "마력",
                "spirit": "정신력",
                "init_brv": "초기 BRV",
                "max_brv": "최대 BRV",
            }
            
            for stat_name, value in item.base_stats.items():
                if value != 0:
                    display_stat = stat_names.get(stat_name, stat_name.upper())
                    sign = "+" if value >= 0 else ""
                    console.print(x + 2, y, f"{display_stat}: {sign}{int(value)}", fg=rarity_color)
                    y += 1

            # unique_effect에서 재생 스탯 등 추출하여 표시
            if hasattr(item, 'unique_effect') and item.unique_effect:
                # unique_effect 파싱 (간단한 파싱)
                unique_stats = {}
                for effect_str in item.unique_effect.split("|"):
                    if ":" in effect_str:
                        effect_name, value_str = effect_str.split(":", 1)
                        effect_name = effect_name.strip()
                        try:
                            value = float(value_str.strip())
                            # 재생 스탯 등 기본 스탯 섹션에 표시할 효과들
                            if effect_name == "mp_regen":
                                unique_stats["MP 재생"] = int(value)
                            elif effect_name == "hp_regen":
                                # 퍼센트일 수 있음 (0.05 = 5%)
                                if value < 1:
                                    unique_stats["HP 재생"] = f"{int(value * 100)}%"
                                else:
                                    unique_stats["HP 재생"] = int(value)
                            elif effect_name == "wound_regen":
                                unique_stats["상처 회복"] = int(value)
                        except ValueError:
                            pass
                
                # 추출한 스탯 표시
                for stat_name, value in unique_stats.items():
                    if isinstance(value, str):
                        console.print(x + 2, y, f"{stat_name}: +{value}", fg=rarity_color)
                    else:
                        sign = "+" if value >= 0 else ""
                        console.print(x + 2, y, f"{stat_name}: {sign}{value}", fg=rarity_color)
                    y += 1

            # 접사
            if item.affixes:
                y += 1
                console.print(x, y, "추가 효과:", fg=Colors.UI_TEXT_SELECTED)
                y += 1

                for affix in item.affixes:
                    # get_description() 메서드를 사용하여 올바른 형식으로 표시
                    affix_desc = affix.get_description()
                    console.print(x + 2, y, affix_desc, fg=(150, 255, 150))
                    y += 1

            # 유니크 효과
            if hasattr(item, 'unique_effect') and item.unique_effect:
                y += 1
                translated_effect = self._translate_unique_effect(item.unique_effect)
                console.print(x, y, f"특수 효과: {translated_effect}", fg=(255, 100, 255))

        # 소비품 정보
        elif isinstance(item, Consumable):
            y += 1
            effect_desc = {
                "heal_hp": f"HP {item.effect_value} 회복",
                "heal_mp": f"MP {item.effect_value} 회복",
                "heal_both": f"HP/MP {item.effect_value} 회복",
                "revive": f"HP {item.effect_value}로 부활",
                "cure_status": "모든 상태이상 치료"
            }

            desc = effect_desc.get(item.effect_type, "효과 불명")
            console.print(x, y, f"효과: {desc}", fg=Colors.UI_TEXT)
        
        # 요리 음식 정보 (CookedFood)
        else:
            from src.cooking.recipe import CookedFood
            if isinstance(item, CookedFood):
                y += 1
                console.print(x, y, "효과 (아군 전체 적용):", fg=Colors.UI_TEXT_SELECTED)
                y += 1
                
                # HP 회복
                hp_restore = getattr(item, 'hp_restore', 0)
                if hp_restore > 0:
                    console.print(x + 2, y, f"HP +{hp_restore} 회복", fg=(100, 255, 100))
                    y += 1
                
                # MP 회복
                mp_restore = getattr(item, 'mp_restore', 0)
                if mp_restore > 0:
                    console.print(x + 2, y, f"MP +{mp_restore} 회복", fg=(100, 200, 255))
                    y += 1
                
                # 최대 HP 보너스
                max_hp_bonus = getattr(item, 'max_hp_bonus', 0)
                if max_hp_bonus > 0:
                    console.print(x + 2, y, f"최대 HP +{max_hp_bonus} (일시적)", fg=(255, 200, 100))
                    y += 1
                
                # 최대 MP 보너스
                max_mp_bonus = getattr(item, 'max_mp_bonus', 0)
                if max_mp_bonus > 0:
                    console.print(x + 2, y, f"최대 MP +{max_mp_bonus} (일시적)", fg=(200, 150, 255))
                    y += 1
                
                # 버프 정보
                buff_type = getattr(item, 'buff_type', None)
                buff_duration = getattr(item, 'buff_duration', 0)
                if buff_type and buff_duration > 0:
                    y += 1
                    console.print(x, y, "버프 효과:", fg=Colors.UI_TEXT_SELECTED)
                    y += 1
                    
                    # 버프 타입 한글 매핑
                    buff_names = {
                        "attack": "공격력",
                        "defense": "방어력",
                        "speed": "속도",
                        "magic": "마법 공격력"
                    }
                    buff_name = buff_names.get(buff_type, buff_type)
                    buff_value = 0.2  # 기본 20% (inventory.py에서 사용하는 값과 동일)
                    
                    console.print(
                        x + 2, y,
                        f"{buff_name} +{int(buff_value * 100)}% ({buff_duration}턴)",
                        fg=(255, 255, 100)
                    )
                    y += 1
                
                # 독 효과 (실패 요리)
                is_poison = getattr(item, 'is_poison', False)
                poison_damage = getattr(item, 'poison_damage', 0)
                if is_poison and poison_damage > 0:
                    y += 1
                    console.print(
                        x, y,
                        f"⚠ 독! 피해 {poison_damage}",
                        fg=(255, 100, 100)
                    )
                    y += 1

    def _render_target_selection(self, console: tcod.console.Console):
        """대상 선택 UI"""
        # 아이템 타입에 따라 대상 필터링
        item = self.inventory.get_item(self.selected_item_index) if self.selected_item_index is not None else None

        if self.all_allies_mode:
            # 아군 전체 대상 모드 (텐트 등)
            targets = self.party
            title = "아군 전체 대상"
        elif isinstance(item, Consumable) and getattr(item, 'effect_type', '') == 'revive_crystal':
            # revive_crystal: 죽은 파티원만 대상으로
            targets = []
            for member in self.party:
                is_alive = getattr(member, 'is_alive', True)
                current_hp = getattr(member, 'current_hp', 1)
                if not is_alive or current_hp <= 0:
                    targets.append(member)
            title = "부활 대상 선택"
        elif isinstance(item, Consumable):
            # 일반 Consumable: 살아있는 파티원만 대상으로
            targets = []
            for member in self.party:
                is_alive = getattr(member, 'is_alive', True)
                current_hp = getattr(member, 'current_hp', 1)
                if is_alive and current_hp > 0:
                    targets.append(member)
            title = "대상 선택"
        else:
            # 장비 등의 경우 모든 파티원 대상으로
            targets = self.party
            title = "대상 선택"

        # 각 캐릭터당 3줄 (이름+직업, HP바, MP바) + 여백
        rows_per_char = 4
        box_width = 52
        box_height = 4 + len(targets) * rows_per_char
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        # 배경 박스
        draw_styled_box(
            console, box_x, box_y, box_width, box_height,
            title=title,
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )

        # 아이템 효과 미리보기 (타이틀 아래)
        if isinstance(item, Consumable):
            effect_type = getattr(item, 'effect_type', '')
            effect_value = getattr(item, 'effect_value', 0)
            effect_text = {
                "heal_hp": f"HP +{int(effect_value)}",
                "heal_hp_full": "HP 완전 회복",
                "heal_mp": f"MP +{int(effect_value)}",
                "heal_mp_full": "MP 완전 회복",
                "heal_both": f"HP/MP +{int(effect_value)}",
                "heal_both_full": "HP/MP 완전 회복",
                "heal_wound": f"상처 -{int(effect_value)}",
                "revive_crystal": f"HP {int(effect_value)}(으)로 부활",
                "cure_poison": "독 치료",
                "cure_all_status": "모든 상태이상 치료",
                "cure_debuff": "디버프 치료",
            }.get(effect_type, getattr(item, 'name', ''))
            if effect_text:
                console.print(
                    box_x + 2, box_y + 1,
                    f"[{effect_text}]",
                    fg=(150, 255, 150)
                )

        # 아이템 효과 미리보기 (아군 전체 모드)
        if self.all_allies_mode and isinstance(item, Consumable):
            effect_type = getattr(item, 'effect_type', '')
            effect_text = {
                "camp_rest": "파티 전체 HP/MP 50% 회복",
            }.get(effect_type, getattr(item, 'name', ''))
            if effect_text:
                console.print(
                    box_x + 2, box_y + 1,
                    f"[{effect_text}]",
                    fg=(100, 255, 255)
                )

        # 대상 목록
        y = box_y + 3
        for i, character in enumerate(targets):
            if self.all_allies_mode:
                # 아군 전체 모드: 모든 멤버에 ◆ 표시
                is_selected = True
                prefix = "◆"
            else:
                is_selected = (i == self.target_cursor)
                prefix = "►" if is_selected else " "

            char_name = getattr(character, 'name', str(character))
            char_job = getattr(character, 'job_name', getattr(character, 'character_class', ''))
            char_level = getattr(character, 'level', 1)
            char_hp = getattr(character, 'current_hp', 0)
            char_max_hp = getattr(character, 'max_hp', 1)
            char_mp = getattr(character, 'current_mp', 0)
            char_max_mp = getattr(character, 'max_mp', 1)
            char_wound = getattr(character, 'wound', 0)

            if self.all_allies_mode:
                name_color = (100, 255, 255)  # 전체 대상 시안 색상
            else:
                name_color = Colors.UI_TEXT_SELECTED if is_selected else Colors.UI_TEXT

            # 1줄: 이름 + 직업 + 레벨
            header = f"{prefix} {char_name}"
            if char_job:
                header += f" (Lv.{char_level} {char_job})"
            console.print(box_x + 2, y, header, fg=name_color)

            # 2줄: HP 바 (draw_rect 게이지)
            hp_ratio = char_hp / char_max_hp if char_max_hp > 0 else 0
            hp_color = Colors.HP_FULL if hp_ratio > 0.5 else (Colors.HP_HALF if hp_ratio > 0.25 else Colors.HP_LOW)
            bar_width = 20
            console.print(box_x + 4, y + 1, "HP", fg=Colors.GRAY)
            _wr = char_wound / (char_max_hp + char_wound) if char_wound > 0 and char_max_hp > 0 else 0.0
            self._queue_gauge(console, box_x + 7, y + 1, bar_width, hp_ratio, kind="hp", wound_ratio=_wr)
            hp_text = f"{char_hp}/{char_max_hp}"
            if char_wound > 0:
                hp_text += f" (상처:{char_wound})"
            console.print(box_x + 28, y + 1, hp_text, fg=hp_color)

            # 3줄: MP 바 (draw_rect 게이지)
            mp_ratio = char_mp / char_max_mp if char_max_mp > 0 else 0
            console.print(box_x + 4, y + 2, "MP", fg=Colors.GRAY)
            self._queue_gauge(console, box_x + 7, y + 2, bar_width, mp_ratio, kind="mp")
            console.print(box_x + 28, y + 2, f"{char_mp}/{char_max_mp}", fg=Colors.MP_FULL)

            y += rows_per_char


    def _render_character_selection(self, console: tcod.console.Console, title: str):
        """캐릭터 선택 UI - 장비 미리보기 및 HP/MP 표시"""
        rows_per_char = 3
        box_width = min(78, self.screen_width - 4)
        box_height = 3 + len(self.party) * rows_per_char + 2
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        draw_styled_box(
            console, box_x, box_y, box_width, box_height,
            title=title,
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG,
            separator_y=box_y + box_height - 3
        )

        # 하단 조작 안내
        console.print(box_x + 2, box_y + box_height - 2,
                      "↑↓: 선택  Z: 확인  X: 돌아가기", fg=Colors.GRAY)

        y = box_y + 2
        for i, character in enumerate(self.party):
            is_selected = (i == self.target_cursor)
            prefix = "►" if is_selected else " "

            char_name = getattr(character, 'name', str(character))
            char_class = getattr(character, 'job_name',
                               getattr(character, 'character_class', '???'))
            char_level = getattr(character, 'level', 1)

            # 선택 항목 배경 강조
            if is_selected:
                for row in range(2):
                    for dx in range(1, box_width - 1):
                        console.print(box_x + dx, y + row, " ", bg=(30, 30, 55))

            # 1줄: 캐릭터 이름/직업
            console.print(
                box_x + 2, y,
                f"{prefix} {char_name} (Lv.{char_level} {char_class})",
                fg=Colors.UI_TEXT_SELECTED if is_selected else Colors.UI_TEXT
            )

            # HP/MP 바 (우측)
            char_hp = getattr(character, 'current_hp', 0)
            char_max_hp = getattr(character, 'max_hp', 1)
            char_mp = getattr(character, 'current_mp', 0)
            char_max_mp = getattr(character, 'max_mp', 1)

            bar_w = 8
            hp_ratio = char_hp / max(char_max_hp, 1)
            mp_ratio = char_mp / max(char_max_mp, 1)

            info_x = box_x + box_width - 26
            hp_color = Colors.HP_FULL if hp_ratio > 0.5 else (
                Colors.HP_HALF if hp_ratio > 0.2 else Colors.HP_LOW)
            console.print(info_x, y, "HP", fg=Colors.GRAY)
            _wr2 = getattr(character, 'wound', 0)
            _wr2 = _wr2 / (char_max_hp + _wr2) if _wr2 > 0 and char_max_hp > 0 else 0.0
            self._queue_gauge(console, info_x + 3, y, bar_w, hp_ratio, kind="hp", wound_ratio=_wr2)
            console.print(info_x + 12, y, f"{char_hp}/{char_max_hp}", fg=hp_color)

            console.print(info_x, y + 1, "MP", fg=Colors.GRAY)
            self._queue_gauge(console, info_x + 3, y + 1, bar_w, mp_ratio, kind="mp")
            console.print(info_x + 12, y + 1, f"{char_mp}/{char_max_mp}", fg=Colors.MP_FULL)

            # 2줄: 장비 요약
            equip = getattr(character, 'equipment', {})
            eq_x = box_x + 4
            for slot_key in ["weapon", "armor", "accessory"]:
                item = equip.get(slot_key)
                label = {"weapon": "무기", "armor": "방어구", "accessory": "장신구"}[slot_key]
                console.print(eq_x, y + 1, f"{label}:", fg=Colors.GRAY)
                eq_x += len(label) + 1
                if item:
                    item_name = getattr(item, 'name', '???')
                    rarity_color = getattr(
                        getattr(item, 'rarity', None), 'color', Colors.UI_TEXT)
                    console.print(eq_x, y + 1, item_name, fg=rarity_color)
                    eq_x += len(item_name) + 2
                else:
                    console.print(eq_x, y + 1, "-", fg=Colors.DARK_GRAY)
                    eq_x += 3

            y += rows_per_char

    def _render_equipment_unequip(self, console: tcod.console.Console):
        """장비 해제 UI - 스탯 패널 + 장비 슬롯 상세"""
        if self.selected_character_index is None:
            return

        character = self.party[self.selected_character_index]
        char_name = getattr(character, 'name', str(character))
        job_name = getattr(character, 'job_name', '')
        char_level = getattr(character, 'level', 1)
        gimmick_type = getattr(character, 'gimmick_type', None)

        stat_names = {
            "hp": "HP", "mp": "MP",
            "physical_attack": "물리 공격력", "physical_defense": "물리 방어력",
            "magic_attack": "마법 공격력", "magic_defense": "마법 방어력",
            "speed": "속도", "accuracy": "명중률", "evasion": "회피율",
            "luck": "행운", "strength": "힘", "defense": "방어력",
            "magic": "마력", "spirit": "정신력",
            "init_brv": "초기 BRV", "max_brv": "최대 BRV",
        }

        total_width = min(84, self.screen_width - 4)
        total_height = min(32, self.screen_height - 6)
        box_x = (self.screen_width - total_width) // 2
        box_y = (self.screen_height - total_height) // 2
        left_w = 28
        divider_x = box_x + left_w

        title = f"{char_name}의 장비"
        if job_name:
            title += f" ({job_name})"

        # 메인 박스
        draw_styled_box(
            console, box_x, box_y, total_width, total_height,
            title=title,
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG,
            separator_y=box_y + total_height - 3
        )

        # 세로 구분선
        for dy in range(1, total_height - 3):
            console.print(divider_x, box_y + dy, "║",
                          fg=Colors.UI_BORDER, bg=Colors.UI_BG)
        console.print(divider_x, box_y, "╦", fg=Colors.UI_BORDER, bg=Colors.UI_BG)
        console.print(divider_x, box_y + total_height - 3, "╩",
                      fg=Colors.UI_BORDER, bg=Colors.UI_BG)

        # ══ 좌측 패널: 캐릭터 스탯 ══
        ly = box_y + 2
        console.print(box_x + 2, ly, f"◈ Lv.{char_level}", fg=Colors.UI_TEXT_SELECTED)
        ly += 2

        # HP 바
        char_hp = getattr(character, 'current_hp', 0)
        char_max_hp = getattr(character, 'max_hp', 1)
        hp_ratio = char_hp / max(char_max_hp, 1)
        bar_w = left_w - 8
        hp_color = Colors.HP_FULL if hp_ratio > 0.5 else (
            Colors.HP_HALF if hp_ratio > 0.2 else Colors.HP_LOW)
        console.print(box_x + 2, ly, "HP", fg=Colors.GRAY)
        _wr3 = getattr(character, 'wound', 0)
        _wr3 = _wr3 / (char_max_hp + _wr3) if _wr3 > 0 and char_max_hp > 0 else 0.0
        self._queue_gauge(console, box_x + 5, ly, bar_w, hp_ratio, kind="hp", wound_ratio=_wr3)
        ly += 1
        console.print(box_x + 5, ly, f"{char_hp}/{char_max_hp}", fg=hp_color)
        ly += 1

        # MP 바
        char_mp = getattr(character, 'current_mp', 0)
        char_max_mp = getattr(character, 'max_mp', 1)
        mp_ratio = char_mp / max(char_max_mp, 1)
        console.print(box_x + 2, ly, "MP", fg=Colors.GRAY)
        self._queue_gauge(console, box_x + 5, ly, bar_w, mp_ratio, kind="mp")
        ly += 1
        console.print(box_x + 5, ly, f"{char_mp}/{char_max_mp}", fg=Colors.MP_FULL)
        ly += 2

        # 전투 스탯
        stats_list = [
            ("물리 공격", getattr(character, 'strength', 0)),
            ("물리 방어", getattr(character, 'defense', 0)),
            ("마법 공격", getattr(character, 'magic', 0)),
            ("마법 방어", getattr(character, 'spirit', 0)),
            ("속도", getattr(character, 'speed', 0)),
            ("행운", getattr(character, 'luck', 0)),
        ]
        for label, value in stats_list:
            console.print(box_x + 3, ly, f"{label}:", fg=Colors.GRAY)
            val_str = str(value)
            console.print(box_x + left_w - 2 - len(val_str), ly,
                          val_str, fg=Colors.UI_TEXT)
            ly += 1

        ly += 1

        # BRV
        init_brv = getattr(character, 'init_brv', 0)
        max_brv = getattr(character, 'max_brv', 0)
        console.print(box_x + 3, ly, f"BRV {init_brv}/{max_brv}",
                      fg=(150, 200, 255))
        ly += 2

        # 기믹
        if gimmick_type:
            gimmick_data = getattr(character, 'gimmick_data', {})
            gimmick_name = gimmick_data.get('name', gimmick_type)
            console.print(box_x + 2, ly, "기믹:", fg=Colors.GRAY)
            console.print(box_x + 7, ly, gimmick_name, fg=(200, 200, 100))

        # ══ 우측 패널: 장비 슬롯 ══
        slot_labels = {"weapon": "무기", "armor": "방어구", "accessory": "악세서리"}
        ry = box_y + 2
        rx = divider_x + 2

        for si, slot in enumerate(self.equipment_slots):
            is_selected = (si == self.equipment_cursor)
            item = character.equipment.get(slot)
            prefix = "►" if is_selected else " "
            label = slot_labels.get(slot, slot)

            # 슬롯 헤더
            console.print(rx, ry, f"{prefix} [{label}]",
                          fg=Colors.UI_TEXT_SELECTED if is_selected else Colors.UI_TEXT)
            ry += 1

            if item:
                item_name = getattr(item, 'name', '???')
                rarity = getattr(item, 'rarity', None)
                rarity_color = getattr(rarity, 'color', Colors.UI_TEXT)
                rarity_name = getattr(rarity, 'display_name', '일반')

                # 이름 + 등급
                console.print(rx + 2, ry, item_name, fg=rarity_color)
                console.print(rx + 2 + len(item_name) + 1, ry,
                              f"[{rarity_name}]", fg=rarity_color)
                ry += 1

                # 내구도 바
                if isinstance(item, Equipment):
                    current_dur = getattr(item, 'current_durability', 100)
                    max_dur = getattr(item, 'max_durability', 100)
                    if max_dur > 0:
                        dur_ratio = current_dur / max_dur
                        dur_color = (100, 255, 100) if dur_ratio > 0.5 else (
                            (255, 255, 100) if dur_ratio > 0.2 else (255, 100, 100))
                        console.print(rx + 2, ry, "내구도", fg=Colors.GRAY)
                        self._queue_gauge(console, rx + 6, ry, 10, dur_ratio, custom_color=dur_color)
                        console.print(rx + 17, ry,
                                      f"[{current_dur}/{max_dur}]", fg=dur_color)
                        ry += 1

                # 스탯
                if hasattr(item, 'base_stats'):
                    stat_parts = []
                    for sn, sv in item.base_stats.items():
                        if sv != 0:
                            display = stat_names.get(sn, sn)
                            sign = "+" if sv > 0 else ""
                            stat_parts.append(f"{display}{sign}{int(sv)}")
                    if stat_parts:
                        line = "  ".join(stat_parts[:3])
                        console.print(rx + 2, ry, line, fg=(150, 200, 150))
                        ry += 1
                        if len(stat_parts) > 3:
                            line2 = "  ".join(stat_parts[3:6])
                            console.print(rx + 2, ry, line2, fg=(150, 200, 150))
                            ry += 1

                # 접사
                if hasattr(item, 'affixes') and item.affixes:
                    for affix in item.affixes[:2]:
                        affix_desc = affix.get_description() if hasattr(
                            affix, 'get_description') else str(affix)
                        console.print(rx + 2, ry, f"+ {affix_desc}",
                                      fg=(200, 180, 100))
                        ry += 1
            else:
                console.print(rx + 2, ry, "(장착 없음)", fg=Colors.DARK_GRAY)
                ry += 1

            ry += 1  # 슬롯 간 간격

        # 하단 안내
        console.print(box_x + 2, box_y + total_height - 2,
                      "↑↓: 슬롯 선택  Z: 장비 해제  X: 돌아가기", fg=Colors.GRAY)

    def _render_drop_item(self, console: tcod.console.Console):
        """아이템 드롭 대화상자"""
        if self.drop_item_index is None:
            return
        
        item = self.inventory.get_item(self.drop_item_index)
        if not item:
            return
        
        slot = self.inventory.slots[self.drop_item_index]
        max_quantity = slot.quantity
        
        box_width = 50
        box_height = 9 if self.drop_quantity_input_mode else 6
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2
        
        draw_styled_box(
            console, box_x, box_y, box_width, box_height,
            title="아이템 드롭",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )
        
        y = box_y + 2
        item_name = getattr(item, 'name', '알 수 없는 아이템')
        console.print(box_x + 2, y, f"{item_name}을(를) 드롭하시겠습니까?", fg=Colors.UI_TEXT)
        y += 1
        
        if self.drop_quantity_input_mode:
            console.print(box_x + 2, y, f"개수: {self.drop_quantity}/{max_quantity}", fg=Colors.UI_TEXT_SELECTED)
            y += 1
            console.print(box_x + 2, y, "↑↓: ±1  ←→: ±10", fg=Colors.GRAY)
            y += 1
            console.print(box_x + 2, y, "Z: 드롭  X: 취소", fg=Colors.GRAY)
        else:
            if max_quantity > 1:
                console.print(box_x + 2, y, "Z: 개수 선택  X: 취소", fg=Colors.GRAY)
            else:
                console.print(box_x + 2, y, "Z: 드롭  X: 취소", fg=Colors.GRAY)
    
    def _render_drop_gold(self, console: tcod.console.Console):
        """골드 드롭 대화상자"""
        max_gold = self.inventory.gold
        
        box_width = 50
        box_height = 8
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2
        
        draw_styled_box(
            console, box_x, box_y, box_width, box_height,
            title="골드 드롭",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )
        
        y = box_y + 2
        console.print(box_x + 2, y, f"보유 골드: {max_gold}G", fg=Colors.UI_TEXT)
        y += 1
        console.print(box_x + 2, y, f"드롭할 골드: {self.drop_gold_amount}G", fg=Colors.UI_TEXT_SELECTED)
        y += 1
        console.print(box_x + 2, y, "↑↓: ±1  ←→: ±10", fg=Colors.GRAY)
        y += 1
        console.print(box_x + 2, y, "Z: 드롭  X: 취소", fg=Colors.GRAY)

    def _render_destroy_confirm(self, console: tcod.console.Console):
        """파괴 확인 대화상자"""
        if self.confirm_destroy_item is None:
            return

        item = self.inventory.get_item(self.confirm_destroy_item)
        if not item:
            return

        # 스택 가능 여부 확인
        from src.gathering.ingredient import Ingredient
        from src.cooking.recipe import CookedFood
        is_stackable = not isinstance(item, Equipment)
        slot = self.inventory.slots[self.confirm_destroy_item] if self.confirm_destroy_item < len(self.inventory.slots) else None
        max_quantity = slot.quantity if slot else 1

        # 박스 크기 조정 (개수 입력 모드면 더 크게)
        if self.destroy_quantity_input_mode and is_stackable:
            box_height = 12
        else:
            box_height = 10

        box_width = 55
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        draw_styled_box(
            console, box_x, box_y, box_width, box_height,
            title="아이템 파괴",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )

        # 경고 메시지
        item_name = getattr(item, 'name', '알 수 없는 아이템')
        
        # 개수 입력 모드
        if self.destroy_quantity_input_mode and is_stackable:
            msg = f"'{item_name}'을(를) 몇 개 파괴하시겠습니까?"
            console.print(
                box_x + (box_width - len(msg)) // 2,
                box_y + 3,
                msg,
                fg=(255, 100, 100)
            )
            
            # 개수 표시
            qty_msg = f"개수: {self.destroy_quantity} / {max_quantity}"
            console.print(
                box_x + (box_width - len(qty_msg)) // 2,
                box_y + 5,
                qty_msg,
                fg=Colors.UI_TEXT_SELECTED
            )
            
            # 조작법
            controls = "↑↓: ±1  ←→: ±10  Z: 확인  X: 취소"
            console.print(
                box_x + (box_width - len(controls)) // 2,
                box_y + 7,
                controls,
                fg=Colors.GRAY
            )
        else:
            if is_stackable and max_quantity > 1:
                msg = f"'{item_name}' (보유: {max_quantity}개)을(를) 파괴하시겠습니까?"
            else:
                msg = f"'{item_name}'을(를) 파괴하시겠습니까?"
            console.print(
                box_x + (box_width - len(msg)) // 2,
                box_y + 3,
                msg,
                fg=(255, 100, 100)
            )

            console.print(
                box_x + (box_width - 30) // 2,
                box_y + 4,
                "이 작업은 되돌릴 수 없습니다!",
                fg=Colors.GRAY
            )

            # 스택형 아이템이면 개수 선택 안내
            if is_stackable and max_quantity > 1:
                console.print(
                    box_x + (box_width - 25) // 2,
                    box_y + 5,
                    "Z: 개수 선택",
                    fg=Colors.GRAY
                )

            # YES / NO 버튼
            y = box_y + 7
            yes_color = Colors.UI_TEXT_SELECTED if self.confirm_yes else Colors.UI_TEXT
            no_color = Colors.UI_TEXT_SELECTED if not self.confirm_yes else Colors.UI_TEXT

            console.print(
                box_x + 15, y,
                "[ 예 ]" if self.confirm_yes else "  예  ",
                fg=yes_color
            )

            console.print(
                box_x + 30, y,
                "[아니오]" if not self.confirm_yes else " 아니오 ",
                fg=no_color
            )

    def _render_equipment_comparison(self, console: tcod.console.Console, new_item: Equipment):
        """장비 비교 UI - 좌우 분할 패널로 새 장비 vs 현재 장비 비교"""
        stat_names = {
            "hp": "HP", "mp": "MP",
            "physical_attack": "물리 공격력", "physical_defense": "물리 방어력",
            "magic_attack": "마법 공격력", "magic_defense": "마법 방어력",
            "speed": "속도", "accuracy": "명중률", "evasion": "회피율",
            "luck": "행운", "strength": "힘", "defense": "방어력",
            "magic": "마력", "spirit": "정신력",
            "init_brv": "초기 BRV", "max_brv": "최대 BRV",
        }

        if not self.party:
            return

        total_width = min(80, self.screen_width - 4)
        total_height = min(34, self.screen_height - 6)
        box_x = (self.screen_width - total_width) // 2
        box_y = (self.screen_height - total_height) // 2
        left_w = total_width // 2
        divider_x = box_x + left_w

        draw_styled_box(
            console, box_x, box_y, total_width, total_height,
            title="장비 비교",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG,
            separator_y=box_y + total_height - 3
        )

        # 세로 구분선
        for dy in range(1, total_height - 3):
            console.print(divider_x, box_y + dy, "║",
                          fg=Colors.UI_BORDER, bg=Colors.UI_BG)
        console.print(divider_x, box_y, "╦", fg=Colors.UI_BORDER, bg=Colors.UI_BG)
        console.print(divider_x, box_y + total_height - 3, "╩",
                      fg=Colors.UI_BORDER, bg=Colors.UI_BG)

        # 캐릭터 및 슬롯 정보
        char_idx = min(self.selected_character_for_comparison, len(self.party) - 1)
        character = self.party[char_idx]
        char_name = getattr(character, 'name', '???')
        slot = new_item.equip_slot.value
        current_item = character.equipment.get(slot)

        # 새 아이템 rarity
        new_rarity = getattr(new_item, 'rarity', None)
        new_rarity_display = getattr(new_rarity, 'display_name', '일반') if new_rarity else '일반'
        new_rarity_color = getattr(new_rarity, 'color', Colors.UI_TEXT) if new_rarity else Colors.UI_TEXT
        new_item_name = getattr(new_item, 'name', '???')

        # ══ 좌측 패널: 새 장비 ══
        lx = box_x + 2
        ly = box_y + 1
        panel_w = left_w - 3  # 패널 내 유효 너비

        console.print(lx, ly, "◈ 새 장비", fg=Colors.UI_TEXT_SELECTED)
        ly += 1

        # 아이템 이름 (rarity 색상)
        name_line = f"{new_item_name} [{new_rarity_display}]"
        console.print(lx, ly, name_line[:panel_w], fg=new_rarity_color)
        ly += 1

        # 내구도 바
        new_dur = getattr(new_item, 'durability', None)
        new_max_dur = getattr(new_item, 'max_durability', None)
        if new_dur is not None and new_max_dur and new_max_dur > 0:
            dur_ratio = new_dur / new_max_dur
            bar_w = panel_w - 8
            dur_color = (100, 255, 100) if dur_ratio > 0.5 else (
                (255, 200, 0) if dur_ratio > 0.2 else (255, 100, 100))
            console.print(lx, ly, "내구:", fg=Colors.GRAY)
            self._queue_gauge(console, lx + 5, ly, bar_w, dur_ratio, custom_color=dur_color)
            ly += 1
            console.print(lx + 5, ly, f"{new_dur}/{new_max_dur}", fg=dur_color)
            ly += 1
        ly += 1

        # 스탯
        if hasattr(new_item, 'base_stats'):
            for stat_key, val in new_item.base_stats.items():
                if val == 0:
                    continue
                label = stat_names.get(stat_key, stat_key.upper())
                is_brv = stat_key in ("init_brv", "max_brv")
                val_color = (150, 200, 255) if is_brv else (150, 200, 150)
                line = f"{label}: +{val}"
                console.print(lx, ly, line[:panel_w], fg=val_color)
                ly += 1

        # 어픽스
        new_affixes = getattr(new_item, 'affixes', [])
        if new_affixes:
            ly += 1
            for afx in new_affixes:
                afx_str = afx.get_description() if hasattr(afx, 'get_description') else str(afx)
                console.print(lx, ly, f"+ {afx_str}"[:panel_w], fg=(200, 180, 100))
                ly += 1

        # 유니크 효과
        new_effect = getattr(new_item, 'unique_effect', None)
        if new_effect:
            ly += 1
            translated = self._translate_unique_effect(new_effect)
            console.print(lx, ly, "특수:", fg=Colors.GRAY)
            ly += 1
            # 긴 텍스트는 잘라서 출력
            for chunk_start in range(0, len(translated), panel_w):
                console.print(lx, ly, translated[chunk_start:chunk_start + panel_w],
                              fg=(100, 255, 100))
                ly += 1

        # ══ 우측 패널: 현재 장비 ══
        rx = divider_x + 2
        ry = box_y + 1
        rpanel_w = total_width - left_w - 3

        cur_label = f"◈ 현재 장비 ({char_name})"
        console.print(rx, ry, cur_label[:rpanel_w], fg=Colors.UI_TEXT_SELECTED)
        ry += 1

        if current_item is None:
            # 장착 없음
            console.print(rx, ry, "장착 없음", fg=Colors.DARK_GRAY)
            ry += 2

            # 내구도 바 자리 (빈 줄)
            ry += 2

            # 새 아이템 스탯을 모두 녹색으로 표시 (전부 증가)
            if hasattr(new_item, 'base_stats'):
                for stat_key, val in new_item.base_stats.items():
                    if val == 0:
                        continue
                    label = stat_names.get(stat_key, stat_key.upper())
                    diff_line = f"{label}: 0 → {val} ↑+{val}"
                    console.print(rx, ry, diff_line[:rpanel_w], fg=(100, 255, 100))
                    ry += 1

            # 새 장비 유니크 효과 (비교 대상 없으므로 녹색)
            if new_effect:
                ry += 1
                translated = self._translate_unique_effect(new_effect)
                console.print(rx, ry, "특수:", fg=Colors.GRAY)
                ry += 1
                for chunk_start in range(0, len(translated), rpanel_w):
                    console.print(rx, ry, translated[chunk_start:chunk_start + rpanel_w],
                                  fg=(100, 255, 100))
                    ry += 1

        else:
            # 현재 장착 아이템 표시
            cur_rarity = getattr(current_item, 'rarity', None)
            cur_rarity_display = getattr(cur_rarity, 'display_name', '일반') if cur_rarity else '일반'
            cur_rarity_color = getattr(cur_rarity, 'color', Colors.UI_TEXT) if cur_rarity else Colors.UI_TEXT
            cur_item_name = getattr(current_item, 'name', '???')

            cur_name_line = f"{cur_item_name} [{cur_rarity_display}]"
            console.print(rx, ry, cur_name_line[:rpanel_w], fg=cur_rarity_color)
            ry += 1

            # 현재 장비 내구도 바
            cur_dur = getattr(current_item, 'durability', None)
            cur_max_dur = getattr(current_item, 'max_durability', None)
            if cur_dur is not None and cur_max_dur and cur_max_dur > 0:
                dur_ratio = cur_dur / cur_max_dur
                bar_w = rpanel_w - 8
                dur_color = (100, 255, 100) if dur_ratio > 0.5 else (
                    (255, 200, 0) if dur_ratio > 0.2 else (255, 100, 100))
                console.print(rx, ry, "내구:", fg=Colors.GRAY)
                self._queue_gauge(console, rx + 5, ry, bar_w, dur_ratio, custom_color=dur_color)
                ry += 1
                console.print(rx + 5, ry, f"{cur_dur}/{cur_max_dur}", fg=dur_color)
                ry += 1
            ry += 1

            # 스탯 비교 (diff 화살표)
            new_stats = getattr(new_item, 'base_stats', {})
            cur_stats = getattr(current_item, 'base_stats', {})
            all_stat_keys = set(list(new_stats.keys()) + list(cur_stats.keys()))

            for stat_key in all_stat_keys:
                new_val = new_stats.get(stat_key, 0)
                cur_val = cur_stats.get(stat_key, 0)
                if new_val == 0 and cur_val == 0:
                    continue
                diff = new_val - cur_val
                label = stat_names.get(stat_key, stat_key.upper())
                if diff > 0:
                    diff_color = (100, 255, 100)
                    arrow_str = f"→ ↑+{diff}"
                elif diff < 0:
                    diff_color = (255, 100, 100)
                    arrow_str = f"→ ↓{diff}"
                else:
                    diff_color = Colors.DARK_GRAY
                    arrow_str = f"→ ={diff}"
                diff_line = f"{label}: {cur_val} {arrow_str}"
                console.print(rx, ry, diff_line[:rpanel_w], fg=diff_color)
                ry += 1

            # 어픽스 비교
            cur_affixes = getattr(current_item, 'affixes', [])
            if cur_affixes:
                ry += 1
                for afx in cur_affixes:
                    afx_str = afx.get_description() if hasattr(afx, 'get_description') else str(afx)
                    console.print(rx, ry, f"+ {afx_str}"[:rpanel_w], fg=(200, 180, 100))
                    ry += 1

            # 유니크 효과 비교
            current_effect = getattr(current_item, 'unique_effect', None)
            if new_effect or current_effect:
                ry += 1
                if new_effect == current_effect and new_effect:
                    # 동일한 효과
                    translated = self._translate_unique_effect(new_effect)
                    console.print(rx, ry, "특수:", fg=Colors.GRAY)
                    ry += 1
                    for chunk_start in range(0, len(translated), rpanel_w):
                        console.print(rx, ry, translated[chunk_start:chunk_start + rpanel_w],
                                      fg=Colors.GRAY)
                        ry += 1
                else:
                    if new_effect:
                        translated_new = self._translate_unique_effect(new_effect)
                        console.print(rx, ry, "새 특수:", fg=Colors.GRAY)
                        ry += 1
                        for chunk_start in range(0, len(translated_new), rpanel_w):
                            console.print(rx, ry, translated_new[chunk_start:chunk_start + rpanel_w],
                                          fg=(100, 255, 100))
                            ry += 1
                    if current_effect:
                        translated_cur = self._translate_unique_effect(current_effect)
                        console.print(rx, ry, "현 특수:", fg=Colors.GRAY)
                        ry += 1
                        for chunk_start in range(0, len(translated_cur), rpanel_w):
                            console.print(rx, ry, translated_cur[chunk_start:chunk_start + rpanel_w],
                                          fg=(255, 100, 100))
                            ry += 1

        # ══ 하단 조작 안내 ══
        hint_y = box_y + total_height - 2
        hint = f"({char_idx + 1}/{len(self.party)}) ↑↓: 캐릭터 선택  Z: 장착  X: 취소"
        hint_x = box_x + (total_width - len(hint)) // 2
        console.print(hint_x, hint_y, hint, fg=Colors.DARK_GRAY)


def open_inventory(
    console: tcod.console.Console,
    context: tcod.context.Context,
    inventory: Inventory,
    party: List[Any],
    exploration: Optional[Any] = None,
    on_update: Optional[Any] = None
) -> None:
    """
    인벤토리 열기

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        inventory: 인벤토리
        party: 파티 멤버
        exploration: 탐험 시스템 (드롭 기능용)
        on_update: 매 프레임 호출할 업데이트 함수 (봇 등 백그라운드 로직용)
    """
    ui = InventoryUI(console.width, console.height, inventory, party, exploration)

    logger.info("인벤토리 열기")

    import time
    import pygame
    
    while not ui.closed:
        # 백그라운드 업데이트 실행
        if on_update:
            on_update()

        # 렌더링
        ui.render(console)
        # pixel overlay 스무스 게이지 등록
        if hasattr(context, 'add_pixel_overlay') and ui._pending_gauges:
            gauges = list(ui._pending_gauges)
            ui._pending_gauges.clear()
            tw = getattr(context, 'tile_width', 10)
            th = getattr(context, 'tile_height', 13)
            def _gauge_overlay(dt, _g=gauges, _tw=tw, _th=th):
                from src.ui.raylib_backend.smooth_gauge import draw_smooth_gauge
                for gx, gy, gw, ratio, ci, wound in _g:
                    if isinstance(ci, str):
                        draw_smooth_gauge(gx * _tw, gy * _th, gw * _tw, _th, ratio, kind=ci, wound_ratio=wound)
                    else:
                        draw_smooth_gauge(gx * _tw, gy * _th, gw * _tw, _th, ratio, custom_color=ci, wound_ratio=wound)
            context.add_pixel_overlay(_gauge_overlay)
        context.present(console)

        # pygame 이벤트 업데이트 (게임패드 입력을 위해)
        try:
            pygame.event.pump()
        except:
            pass

        # 키보드 입력 처리
        keyboard_processed = False
        for event in tcod.event.get():
            action = unified_input_handler.process_tcod_event(event)

            if action:
                keyboard_processed = True
                if ui.handle_input(action):
                    return

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                ui.closed = True
                return

        # 게임패드 입력 처리
        if not keyboard_processed:
            gamepad_action = unified_input_handler.get_action()
            if gamepad_action:
                if ui.handle_input(gamepad_action):
                    return

        # CPU 사용률 낮추기
        time.sleep(0.01)

    logger.info("인벤토리 닫기")
