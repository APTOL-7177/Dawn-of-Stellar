"""
전리품 UI

전투 승리 후 아이템 획득 화면
- 좌/우 키로 전리품↔인벤토리 전환
- Z로 아이템 획득 (전리품 패널) / 되돌리기 (인벤토리 패널)
- ESC로 닫기 (남은 아이템 파괴)
"""

import tcod.console
import tcod.event
from typing import List, Dict, Any, Optional
import time

from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler, unified_input_handler
from src.equipment.inventory import Inventory
from src.core.logger import get_logger
from src.audio import play_sfx


logger = get_logger("loot_ui")


class LootUI:
    """전리품 획득 UI"""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        loot_items: List[Any],
        inventory: Inventory,
        player_id: Optional[str] = None,
        network_manager: Optional[Any] = None,
        is_multiplayer: bool = False
    ):
        """
        Args:
            screen_width: 화면 너비
            screen_height: 화면 높이
            loot_items: 전리품 아이템 리스트
            inventory: 플레이어 인벤토리
            player_id: 플레이어 ID (멀티플레이용)
            network_manager: 네트워크 매니저 (멀티플레이용)
            is_multiplayer: 멀티플레이 여부
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.loot_items = list(loot_items)  # 복사본 (수정 가능)
        self.inventory = inventory
        self.player_id = player_id
        self.network_manager = network_manager
        self.is_multiplayer = is_multiplayer

        # 현재 패널 (0: 전리품, 1: 인벤토리)
        self.current_panel = 0
        
        # 각 패널 선택 인덱스
        self.loot_index = 0
        self.inv_index = 0
        
        # 스크롤 오프셋
        self.loot_scroll = 0
        self.inv_scroll = 0
        self.max_visible = 8
        
        # 완료 여부
        self.completed = False

        # 교체 모드
        self.swap_mode = False
        self.swap_item = None  # 교체할 전리품

        # 닫기 확인 모드
        self.confirm_close = False

        # 획득한 아이템 추적 (이름 리스트)
        self.claimed_items = []

        # 획득 피드백 메시지
        self.feedback_msg = ""
        self.feedback_timer = 0.0
        self.feedback_color = Colors.UI_TEXT_SELECTED

    def handle_input(self, action: GameAction) -> bool:
        """
        입력 처리

        Returns:
            완료 여부
        """
        # 닫기 확인 모드
        if self.confirm_close:
            if action == GameAction.CONFIRM:
                # 확인 - 남은 아이템 버리고 닫기
                play_sfx("ui", "cursor_cancel")
                logger.info(f"전리품 {len(self.loot_items)}개 파괴됨")
                self.completed = True
                return True
            elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
                # 취소 - 돌아가기
                play_sfx("ui", "cursor_move")
                self.confirm_close = False
                return False
            return False

        if action == GameAction.ESCAPE or action == GameAction.CANCEL:
            if self.swap_mode:
                # 교체 모드 취소
                self.swap_mode = False
                self.swap_item = None
                self.current_panel = 0
                play_sfx("ui", "cursor_cancel")
                return False
            if self.loot_items:
                # 남은 아이템이 있으면 확인 요청
                play_sfx("ui", "cursor_cancel")
                self.confirm_close = True
                return False
            else:
                # 전리품이 비었으면 바로 닫기
                play_sfx("ui", "cursor_cancel")
                self.completed = True
                return True

        # P키(PICKUP) = 모두 획득
        if action == GameAction.PICKUP:
            self._claim_all_items()
            return False

        # 좌/우 키로 패널 전환
        if action == GameAction.MOVE_LEFT:
            if self.swap_mode:
                # 교체 모드 취소
                self.swap_mode = False
                self.swap_item = None
                play_sfx("ui", "cursor_cancel")
            else:
                self.current_panel = 0
                play_sfx("ui", "cursor_move")
            return False

        if action == GameAction.MOVE_RIGHT:
            if not self.swap_mode:
                self.current_panel = 1
                play_sfx("ui", "cursor_move")
            return False

        # 상/하 키로 선택 이동
        if action == GameAction.MOVE_UP:
            if self.current_panel == 0:
                self._move_selection(-1, is_loot=True)
            else:
                self._move_selection(-1, is_loot=False)
            return False

        if action == GameAction.MOVE_DOWN:
            if self.current_panel == 0:
                self._move_selection(1, is_loot=True)
            else:
                self._move_selection(1, is_loot=False)
            return False

        # Z (확인) 키로 아이템 획득/교체/파괴
        if action == GameAction.CONFIRM:
            if self.current_panel == 0:
                # 전리품 패널에서 Z
                self._try_claim_item()
            else:
                # 인벤토리 패널에서 Z
                if self.swap_mode:
                    # 교체 모드: 선택한 인벤토리 아이템과 교체
                    self._perform_swap()
                else:
                    # 인벤토리 → 전리품으로 이동
                    self._move_to_loot()
            return False

        return False

    def _move_selection(self, delta: int, is_loot: bool):
        """선택 이동"""
        if is_loot:
            if not self.loot_items:
                return
            self.loot_index = max(0, min(len(self.loot_items) - 1, self.loot_index + delta))
            # 스크롤 조정
            if self.loot_index < self.loot_scroll:
                self.loot_scroll = self.loot_index
            elif self.loot_index >= self.loot_scroll + self.max_visible:
                self.loot_scroll = self.loot_index - self.max_visible + 1
        else:
            slots = self.inventory.slots
            if not slots:
                return
            self.inv_index = max(0, min(len(slots) - 1, self.inv_index + delta))
            # 스크롤 조정
            if self.inv_index < self.inv_scroll:
                self.inv_scroll = self.inv_index
            elif self.inv_index >= self.inv_scroll + self.max_visible:
                self.inv_scroll = self.inv_index - self.max_visible + 1
        
        play_sfx("ui", "cursor_move")

    def _set_feedback(self, msg: str, color=None):
        """피드백 메시지 설정"""
        self.feedback_msg = msg
        self.feedback_timer = time.time()
        self.feedback_color = color or Colors.UI_TEXT_SELECTED

    def _try_claim_item(self):
        """전리품 획득 시도"""
        if not self.loot_items or self.loot_index >= len(self.loot_items):
            play_sfx("ui", "cursor_error")
            return

        item = self.loot_items[self.loot_index]
        item_weight = getattr(item, 'weight', 0.5)

        # 무게 체크
        if not self.inventory.can_add_item(item):
            # 무게 초과 - 교체 모드로 전환
            play_sfx("ui", "cursor_error")
            self.swap_mode = True
            self.swap_item = item
            self.current_panel = 1  # 인벤토리 패널로 전환
            self._set_feedback(f"무게 초과! 교체할 아이템을 선택하세요", (255, 100, 100))
            logger.info(f"무게 초과: {item.name} ({item_weight}kg) - 교체 모드")
            return

        # 획득 성공
        item_name = getattr(item, 'name', '아이템')
        item_id = getattr(item, 'item_id', '')
        self.inventory.add_item(item)
        self.loot_items.pop(self.loot_index)
        self.claimed_items.append(item_name)

        # 퀘스트 진행도 업데이트
        if item_id:
            try:
                from src.quest.quest_manager import get_quest_manager
                get_quest_manager().update_progress("item_collected", item_id, 1)
            except Exception:
                pass

        # 인덱스 조정
        if self.loot_index >= len(self.loot_items) and self.loot_index > 0:
            self.loot_index -= 1

        play_sfx("ui", "item_pickup")
        self._set_feedback(f"{item_name} 획득!", (100, 255, 100))
        logger.info(f"아이템 획득: {item_name}")

        # 전리품이 모두 없어지면 완료
        if not self.loot_items:
            self.completed = True

    def _claim_all_items(self):
        """전리품 모두 획득"""
        if not self.loot_items:
            play_sfx("ui", "cursor_error")
            return

        claimed = 0
        failed = 0
        claimed_ids = []
        while self.loot_items:
            item = self.loot_items[0]
            if not self.inventory.can_add_item(item):
                failed += 1
                break
            item_name = getattr(item, 'name', '아이템')
            item_id = getattr(item, 'item_id', '')
            self.inventory.add_item(item)
            self.loot_items.pop(0)
            self.claimed_items.append(item_name)
            if item_id:
                claimed_ids.append(item_id)
            claimed += 1

        # 퀘스트 진행도 일괄 업데이트
        if claimed_ids:
            try:
                from src.quest.quest_manager import get_quest_manager
                qm = get_quest_manager()
                for cid in claimed_ids:
                    qm.update_progress("item_collected", cid, 1)
            except Exception:
                pass

        if claimed > 0:
            play_sfx("ui", "item_pickup")

        if failed > 0:
            self._set_feedback(f"{claimed}개 획득 (무게 초과로 {len(self.loot_items)}개 남음)", (255, 200, 100))
            # 인덱스 조정
            self.loot_index = 0
            self.loot_scroll = 0
        elif claimed > 0:
            self._set_feedback(f"전리품 {claimed}개 모두 획득!", (100, 255, 100))
            self.completed = True

        logger.info(f"모두 획득: {claimed}개 획득, {len(self.loot_items)}개 남음")

    def _perform_swap(self):
        """아이템 교체 수행"""
        if not self.swap_item or not self.inventory.slots:
            play_sfx("ui", "cursor_error")
            return
        
        if self.inv_index >= len(self.inventory.slots):
            play_sfx("ui", "cursor_error")
            return
        
        # 인벤토리에서 아이템 제거
        removed_item = self.inventory.remove_item(self.inv_index)
        
        if removed_item:
            swap_item_name = getattr(self.swap_item, 'name', '아이템')
            removed_item_name = getattr(removed_item, 'name', '아이템')

            # 전리품 추가
            self.inventory.add_item(self.swap_item)
            self.claimed_items.append(swap_item_name)

            # 퀘스트 진행도 업데이트
            swap_item_id = getattr(self.swap_item, 'item_id', '')
            if swap_item_id:
                try:
                    from src.quest.quest_manager import get_quest_manager
                    get_quest_manager().update_progress("item_collected", swap_item_id, 1)
                except Exception:
                    pass

            # 전리품 리스트에서 제거
            if self.swap_item in self.loot_items:
                self.loot_items.remove(self.swap_item)

            # 제거된 아이템은 전리품 목록으로 이동
            self.loot_items.append(removed_item)
            logger.info(f"아이템 교체: {swap_item_name} ← {removed_item_name} (전리품으로 이동)")
            self._set_feedback(f"{swap_item_name} ← {removed_item_name}", (100, 255, 200))
            play_sfx("ui", "item_pickup")
        
        # 교체 모드 종료
        self.swap_mode = False
        self.swap_item = None
        self.current_panel = 0
        
        # 인덱스 조정
        if self.loot_index >= len(self.loot_items) and self.loot_index > 0:
            self.loot_index -= 1
        
        # 전리품이 모두 없어지면 완료
        if not self.loot_items:
            self.completed = True

    def _move_to_loot(self):
        """인벤토리 아이템을 전리품 목록으로 이동"""
        if not self.inventory.slots or self.inv_index >= len(self.inventory.slots):
            play_sfx("ui", "cursor_error")
            return

        removed_item = self.inventory.remove_item(self.inv_index)
        if removed_item:
            item_name = getattr(removed_item, 'name', '아이템')
            self.loot_items.append(removed_item)
            logger.info(f"인벤토리 → 전리품: {item_name}")
            play_sfx("ui", "item_pickup")
            self._set_feedback(f"{item_name} → 전리품으로 이동", (200, 200, 100))

            # 인덱스 조정
            if self.inv_index >= len(self.inventory.slots) and self.inv_index > 0:
                self.inv_index -= 1

    def _get_selected_item(self):
        """현재 선택된 아이템 반환"""
        if self.current_panel == 0:
            if self.loot_items and 0 <= self.loot_index < len(self.loot_items):
                return self.loot_items[self.loot_index]
        else:
            slots = self.inventory.slots
            if slots and 0 <= self.inv_index < len(slots):
                return slots[self.inv_index].item
        return None

    def render(self, console: tcod.console.Console):
        """렌더링"""
        render_space_background(console, self.screen_width, self.screen_height)

        # 제목
        if self.swap_mode:
            title = "⚠ 무게 초과! 교체할 아이템 선택 ⚠"
            title_color = (255, 100, 100)
        else:
            title = "💎 전리품 획득 💎"
            title_color = Colors.UI_TEXT_SELECTED

        console.print(
            (self.screen_width - len(title)) // 2,
            2,
            title,
            fg=title_color
        )

        # 현재 무게 표시
        weight_text = f"가방: {self.inventory.current_weight:.1f}/{self.inventory.max_weight:.1f}kg"
        weight_color = (255, 100, 100) if self.inventory.current_weight >= self.inventory.max_weight * 0.9 else (200, 200, 200)
        console.print(
            self.screen_width - len(weight_text) - 3,
            2,
            weight_text,
            fg=weight_color
        )

        # 패널 레이아웃 계산 (아이템 상세 영역 확보)
        detail_height = 5
        panel_width = (self.screen_width - 6) // 2
        left_x = 3
        right_x = left_x + panel_width + 2
        panel_top = 5
        panel_height = self.screen_height - 10 - detail_height

        # 왼쪽: 전리품 패널
        self._render_panel(
            console,
            left_x, panel_top, panel_width, panel_height,
            "전리품",
            self.loot_items,
            self.loot_index,
            self.loot_scroll,
            is_selected=(self.current_panel == 0 and not self.swap_mode)
        )

        # 오른쪽: 인벤토리 패널
        inv_items = [slot.item for slot in self.inventory.slots] if self.inventory.slots else []
        self._render_panel(
            console,
            right_x, panel_top, panel_width, panel_height,
            "인벤토리",
            inv_items,
            self.inv_index,
            self.inv_scroll,
            is_selected=(self.current_panel == 1 or self.swap_mode)
        )

        # 아이템 상세 정보 영역
        detail_y = panel_top + panel_height + 1
        self._render_item_detail(console, left_x, detail_y, self.screen_width - 6, detail_height)

        # 피드백 메시지 (2초간 표시)
        if self.feedback_msg and (time.time() - self.feedback_timer) < 2.0:
            console.print(
                (self.screen_width - len(self.feedback_msg)) // 2,
                4,
                self.feedback_msg,
                fg=self.feedback_color
            )

        # 도움말
        if self.swap_mode:
            help_text = "◀ 취소 | ▲▼ 선택 | Z 교체 | X 닫기"
        else:
            help_text = "◀▶ 패널전환 | ▲▼ 선택 | Z 획득/되돌리기 | P 모두획득 | X 닫기"

        console.print(
            (self.screen_width - len(help_text)) // 2,
            self.screen_height - 3,
            help_text,
            fg=Colors.GRAY
        )

        # 닫기 확인 오버레이
        if self.confirm_close:
            self._render_confirm_close(console)

    def _render_item_detail(self, console: tcod.console.Console, x: int, y: int, width: int, height: int):
        """선택된 아이템 상세 정보"""
        item = self._get_selected_item()
        if not item:
            return

        # 구분선
        for i in range(width):
            console.print(x + i, y, "─", fg=Colors.DARK_GRAY)

        item_name = getattr(item, 'name', '알 수 없는 아이템')
        item_rarity = getattr(item, 'rarity', None)
        item_type_val = getattr(item, 'item_type', None)
        is_food = (item_type_val is not None and getattr(item_type_val, 'value', None) == 'food')
        if is_food:
            name_color = Colors.FOOD
            rarity_name = '음식'
        elif item_rarity:
            name_color = getattr(item_rarity, 'color', Colors.UI_TEXT)
            rarity_name = getattr(item_rarity, 'display_name', '')
        else:
            name_color = Colors.UI_TEXT
            rarity_name = ''

        # 이름 + 등급
        name_text = f"{item_name}"
        if rarity_name:
            name_text += f" [{rarity_name}]"
        console.print(x + 1, y + 1, name_text, fg=name_color)

        # 스탯 정보
        detail_parts = []
        item_weight = getattr(item, 'weight', None)
        if item_weight is not None:
            detail_parts.append(f"무게:{item_weight:.1f}kg")

        item_type = getattr(item, 'item_type', None)
        if item_type:
            type_name = getattr(item_type, 'value', str(item_type))
            detail_parts.append(f"종류:{type_name}")

        level_req = getattr(item, 'level_requirement', None)
        if level_req and level_req > 1:
            detail_parts.append(f"요구Lv:{level_req}")

        # 장비 스탯
        if hasattr(item, 'attack') and item.attack:
            sign = "+" if item.attack >= 0 else ""
            detail_parts.append(f"공격:{sign}{item.attack}")
        if hasattr(item, 'defense') and item.defense:
            sign = "+" if item.defense >= 0 else ""
            detail_parts.append(f"방어:{sign}{item.defense}")
        if hasattr(item, 'magic_attack') and item.magic_attack:
            sign = "+" if item.magic_attack >= 0 else ""
            detail_parts.append(f"마공:{sign}{item.magic_attack}")

        if detail_parts:
            console.print(x + 1, y + 2, "  ".join(detail_parts), fg=Colors.GRAY)

        # 접사 표시
        if hasattr(item, 'affixes') and item.affixes:
            affix_texts = [affix.get_description() for affix in item.affixes[:4]]
            if affix_texts:
                console.print(x + 1, y + 3, " | ".join(affix_texts), fg=Colors.DARK_GRAY)

    def _render_confirm_close(self, console: tcod.console.Console):
        """닫기 확인 대화상자"""
        box_width = 44
        box_height = 6
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        # 배경 어둡게
        for dy in range(box_height):
            for dx in range(box_width):
                console.print(box_x + dx, box_y + dy, " ", bg=(20, 20, 40))

        # 테두리
        for i in range(box_width):
            console.print(box_x + i, box_y, "─", fg=(255, 100, 100))
            console.print(box_x + i, box_y + box_height - 1, "─", fg=(255, 100, 100))
        for i in range(box_height):
            console.print(box_x, box_y + i, "│", fg=(255, 100, 100))
            console.print(box_x + box_width - 1, box_y + i, "│", fg=(255, 100, 100))
        console.print(box_x, box_y, "┌", fg=(255, 100, 100))
        console.print(box_x + box_width - 1, box_y, "┐", fg=(255, 100, 100))
        console.print(box_x, box_y + box_height - 1, "└", fg=(255, 100, 100))
        console.print(box_x + box_width - 1, box_y + box_height - 1, "┘", fg=(255, 100, 100))

        msg = f"남은 전리품 {len(self.loot_items)}개를 버리시겠습니까?"
        console.print(
            box_x + (box_width - len(msg)) // 2,
            box_y + 2,
            msg,
            fg=(255, 200, 100)
        )
        hint = "Z: 확인  X: 돌아가기"
        console.print(
            box_x + (box_width - len(hint)) // 2,
            box_y + 4,
            hint,
            fg=Colors.GRAY
        )

    def _render_panel(
        self,
        console: tcod.console.Console,
        x: int, y: int, width: int, height: int,
        title: str,
        items: List[Any],
        selected_index: int,
        scroll_offset: int,
        is_selected: bool
    ):
        """패널 렌더링"""
        # 테두리 색상
        border_color = Colors.UI_TEXT_SELECTED if is_selected else Colors.GRAY
        
        # 테두리
        for i in range(width):
            console.print(x + i, y, "─", fg=border_color)
            console.print(x + i, y + height - 1, "─", fg=border_color)
        for i in range(height):
            console.print(x, y + i, "│", fg=border_color)
            console.print(x + width - 1, y + i, "│", fg=border_color)
        console.print(x, y, "┌", fg=border_color)
        console.print(x + width - 1, y, "┐", fg=border_color)
        console.print(x, y + height - 1, "└", fg=border_color)
        console.print(x + width - 1, y + height - 1, "┘", fg=border_color)
        
        # 제목
        title_text = f" {title} ({len(items)}) "
        console.print(
            x + (width - len(title_text)) // 2,
            y,
            title_text,
            fg=border_color
        )
        
        # 아이템 리스트
        if not items:
            console.print(
                x + 2, y + 2,
                "(비어있음)",
                fg=Colors.DARK_GRAY
            )
            return
        
        visible_items = items[scroll_offset:scroll_offset + self.max_visible]
        for i, item in enumerate(visible_items):
            item_y = y + 2 + i
            actual_index = scroll_offset + i
            
            # 선택 표시
            if is_selected and actual_index == selected_index:
                prefix = "▶ "
                item_color = Colors.UI_TEXT_SELECTED
            else:
                prefix = "  "
                item_type_val = getattr(item, 'item_type', None)
                is_food = (item_type_val is not None and getattr(item_type_val, 'value', None) == 'food')
                if is_food:
                    item_color = Colors.FOOD
                else:
                    item_rarity = getattr(item, 'rarity', None)
                    if item_rarity:
                        item_color = getattr(item_rarity, 'color', Colors.UI_TEXT)
                    else:
                        item_color = Colors.UI_TEXT
            
            # 아이템 이름
            item_name = getattr(item, 'name', '알 수 없는 아이템')
            item_weight = getattr(item, 'weight', 0.5)
            
            # 이름 자르기
            max_name_len = width - 12
            if len(item_name) > max_name_len:
                item_name = item_name[:max_name_len-2] + ".."
            
            item_text = f"{prefix}{item_name} ({item_weight:.1f}kg)"
            console.print(x + 1, item_y, item_text[:width-2], fg=item_color)
        
        # 스크롤 표시
        if len(items) > self.max_visible:
            scroll_text = f"({scroll_offset + 1}-{min(scroll_offset + self.max_visible, len(items))}/{len(items)})"
            console.print(
                x + (width - len(scroll_text)) // 2,
                y + height - 2,
                scroll_text,
                fg=Colors.DARK_GRAY
            )


def show_loot_screen(
    console: tcod.console.Console,
    context: tcod.context.Context,
    loot_items: List[Any],
    inventory: Inventory,
    player_id: Optional[str] = None,
    network_manager: Optional[Any] = None,
    is_multiplayer: bool = False
) -> List[Any]:
    """
    전리품 획득 화면 표시
    
    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        loot_items: 전리품 아이템 리스트
        inventory: 플레이어 인벤토리
        player_id: 플레이어 ID (멀티플레이용)
        network_manager: 네트워크 매니저 (멀티플레이용)
        is_multiplayer: 멀티플레이 여부
        
    Returns:
        획득한 아이템 리스트
    """
    if not loot_items:
        logger.info("전리품 없음 - 전리품 화면 생략")
        return []
    
    ui = LootUI(
        console.width,
        console.height,
        loot_items,
        inventory,
        player_id,
        network_manager,
        is_multiplayer
    )
    
    logger.info(f"전리품 화면 표시: {len(loot_items)}개 아이템")
    
    import pygame
    
    # 입력 큐 비우기
    for _ in tcod.event.get():
        pass
    try:
        pygame.event.pump()
        pygame.event.clear()
    except:
        pass
    unified_input_handler.clear_input_state()
    
    time.sleep(0.1)
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()
    
    initial_item_count = len(loot_items)
    
    while not ui.completed:
        # 렌더링
        ui.render(console)
        context.present(console)
        
        # pygame 이벤트 업데이트
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
                ui.handle_input(action)
            
            if isinstance(event, tcod.event.Quit):
                ui.completed = True
                break
        
        # 게임패드 입력 처리
        if not keyboard_processed:
            gamepad_action = unified_input_handler.get_action()
            if gamepad_action:
                ui.handle_input(gamepad_action)
        
        time.sleep(0.01)
    
    # 획득한 아이템 수 계산
    claimed_count = len(ui.claimed_items)
    logger.info(f"전리품 화면 종료: {claimed_count}개 획득, {len(ui.loot_items)}개 파괴")

    # 인벤토리에 대기 메시지 저장 (world_ui에서 자동 표시)
    if ui.claimed_items and hasattr(inventory, 'pending_loot_messages'):
        for item_name in ui.claimed_items:
            inventory.pending_loot_messages.append(f"아이템 획득: {item_name}")

    return ui.claimed_items  # 획득한 아이템 이름 리스트 반환

