"""
전투 UI

6가지 전투 메뉴 (BRV 공격, HP 공격, 스킬, 아이템, 방어, 도망)와
전투 상태 표시
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import tcod
import random

from src.ui.input_handler import InputHandler, GameAction
from src.ui.cursor_menu import CursorMenu, MenuItem
from src.ui.gauge_renderer import GaugeRenderer
from src.ui.tcod_display import render_space_background
from src.combat.combat_manager import CombatManager, CombatState, ActionType
from src.combat.casting_system import get_casting_system, CastingSystem
from src.core.logger import get_logger, Loggers
from src.audio import play_sfx, play_bgm


logger = get_logger(Loggers.UI)
gauge_renderer = GaugeRenderer()
casting_system = get_casting_system()


class CombatUIState(Enum):
    """전투 UI 상태"""
    WAITING_ATB = "waiting_atb"  # ATB 대기 중
    ACTION_MENU = "action_menu"  # 행동 선택
    SKILL_MENU = "skill_menu"  # 스킬 선택
    TARGET_SELECT = "target_select"  # 대상 선택
    ITEM_MENU = "item_menu"  # 아이템 선택
    GIMMICK_VIEW = "gimmick_view"  # 기믹 상세 보기
    EXECUTING = "executing"  # 행동 실행 중
    BATTLE_END = "battle_end"  # 전투 종료


@dataclass
class CombatMessage:
    """전투 메시지"""
    text: str
    color: Tuple[int, int, int] = (255, 255, 255)
    frames_remaining: int = 180  # 3초 (60 FPS 기준)


class CombatUI:
    """전투 UI"""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        combat_manager: CombatManager,
        inventory: Optional[Any] = None,
        session: Optional[Any] = None,
        network_manager: Optional[Any] = None,
        bot_manager: Optional[Any] = None,  # 봇 관리자 (자동 전투용)
        local_player_id: Optional[str] = None  # 로컬 플레이어 ID (다른 플레이어 컨트롤 방지)
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.combat_manager = combat_manager
        self.inventory = inventory  # 전투 중 아이템 사용을 위한 인벤토리
        self.session = session  # 멀티플레이 세션
        self.network_manager = network_manager  # 네트워크 관리자
        self.bot_manager = bot_manager  # 봇 관리자
        self.local_player_id = local_player_id  # 로컬 플레이어 ID

        # UI 상태
        self.state = CombatUIState.WAITING_ATB
        self.current_actor: Optional[Any] = None
        self.selected_action: Optional[ActionType] = None
        self.selected_skill: Optional[Any] = None
        self.selected_target: Optional[Any] = None
        self.selected_item: Optional[Any] = None  # 선택된 아이템
        self.selected_item_index: Optional[int] = None  # 선택된 아이템 인덱스

        # 메시지 로그 (스크롤 형식, 제한 없이 저장)
        self.messages: List[CombatMessage] = []
        self.log_scroll_offset = 0  # 스크롤 오프셋 (0이면 최신 메시지)
        self.log_visible_lines = 8  # 화면에 표시할 메시지 라인 수

        # 메뉴
        self.action_menu: Optional[CursorMenu] = None
        self.skill_menu: Optional[CursorMenu] = None
        self.item_menu: Optional[CursorMenu] = None  # 아이템 메뉴
        self.target_cursor = 0
        self.current_target_list: List[Any] = []  # 현재 타겟 선택 리스트

        # 전투 종료 플래그
        self.battle_ended = False
        self.battle_result: Optional[CombatState] = None

        # 기믹 상세 보기
        self.gimmick_view_character: Optional[Any] = None
        self.previous_state: Optional[CombatUIState] = None

        # 행동 후 대기 시간 (프레임 단위, 60 FPS 기준)
        self.action_delay_frames = 0
        self.action_delay_max = 90  # 1.5초 대기

        # 멀티플레이 전투 동기화 관리자
        self.combat_sync_manager: Optional[Any] = None
        if session and network_manager:
            from src.multiplayer.game_mode import get_game_mode_manager
            from src.multiplayer.combat_sync import CombatSyncManager
            game_mode_manager = get_game_mode_manager()
            if game_mode_manager and game_mode_manager.is_multiplayer():
                self.combat_sync_manager = CombatSyncManager(session, network_manager, combat_manager)
                logger.info("멀티플레이 전투 동기화 관리자 초기화 완료")

        logger.info("전투 UI 초기화")

    def _create_action_menu(self, actor: Any = None) -> CursorMenu:
        """행동 메뉴 생성"""
        items = []

        # 현재 행동자의 기본 공격 스킬 가져오기
        if actor:
            skills = getattr(actor, 'skills', [])

            # 첫 번째 스킬 = 기본 BRV 공격
            if len(skills) >= 1:
                brv_skill = skills[0]
                brv_name = getattr(brv_skill, 'name', 'BRV 공격')
                brv_desc = getattr(brv_skill, 'description', 'BRV를 축적')
                items.append(MenuItem(brv_name, description=brv_desc, enabled=True, value=("brv_skill", brv_skill)))
            else:
                items.append(MenuItem("BRV 공격", description="BRV를 축적", enabled=True, value=ActionType.BRV_ATTACK))

            # 두 번째 스킬 = 기본 HP 공격
            if len(skills) >= 2:
                hp_skill = skills[1]
                hp_name = getattr(hp_skill, 'name', 'HP 공격')
                hp_desc = getattr(hp_skill, 'description', 'HP 데미지')
                items.append(MenuItem(hp_name, description=hp_desc, enabled=True, value=("hp_skill", hp_skill)))
            else:
                items.append(MenuItem("HP 공격", description="HP 데미지", enabled=True, value=ActionType.HP_ATTACK))
        else:
            # actor가 없으면 기본 행동
            items.append(MenuItem("BRV 공격", description="BRV를 축적", enabled=True, value=ActionType.BRV_ATTACK))
            items.append(MenuItem("HP 공격", description="HP 데미지", enabled=True, value=ActionType.HP_ATTACK))

        # 나머지 행동들
        items.append(MenuItem("스킬", description="특수 기술 사용", enabled=True, value=ActionType.SKILL))
        items.append(MenuItem("아이템", description="아이템 사용", enabled=True, value=ActionType.ITEM))
        items.append(MenuItem("방어", description="방어 자세로 피해 감소", enabled=True, value=ActionType.DEFEND))
        items.append(MenuItem("기믹 상세", description="기믹 시스템 상세 정보 보기", enabled=True, value=("gimmick_detail", None)))
        items.append(MenuItem("도망", description="전투에서 도망", enabled=True, value=ActionType.FLEE))

        return CursorMenu(
            title="행동 선택",
            items=items,
            x=5,
            y=33,  # 2줄 위로 이동 (35 → 33)
            width=35,  # 너비 증가 (기믹 상세 텍스트 때문에)
            show_description=True
        )

    def _create_skill_menu(self, actor: Any) -> CursorMenu:
        """스킬 메뉴 생성"""
        # skills 프로퍼티가 없거나 빈 리스트인 경우 skill_ids로부터 직접 생성
        all_skills = getattr(actor, 'skills', [])
        if not all_skills and hasattr(actor, 'skill_ids') and actor.skill_ids:
            from src.character.skills.skill_manager import get_skill_manager
            skill_manager = get_skill_manager()
            all_skills = [
                skill_manager.get_skill(skill_id)
                for skill_id in actor.skill_ids
                if skill_manager.get_skill(skill_id)
            ]

        # 디버그 로그
        from src.core.logger import get_logger
        logger = get_logger("combat_ui")
        logger.warning(f"[SKILL_MENU] {actor.name}의 전체 스킬 개수: {len(all_skills)}")
        logger.warning(f"[SKILL_MENU] skill_ids: {getattr(actor, 'skill_ids', [])}")

        # 첫 두 스킬은 기본 공격이므로 제외 (행동 메뉴에 있음)
        skills = all_skills[2:] if len(all_skills) >= 2 else []
        logger.warning(f"[SKILL_MENU] 기본 공격 제외 후 스킬 개수: {len(skills)}")

        items = []

        for skill in skills:
            # 모든 비용 체크 (MP, Stack, HP 등)
            can_use, reason = skill.can_use(actor)
            
            # 빙결/기절 등 행동 불가 상태이상 체크 (스킬 목록에는 표시하되 사용 불가 표시)
            if hasattr(actor, 'status_manager') and not actor.status_manager.can_act():
                can_use = False
                reason = "행동 불가 상태"

            # 비용 정보 표시
            cost_parts = []
            for cost in skill.costs:
                if hasattr(cost, 'get_description'):
                    # 스킬 정보를 context에 추가하여 특성 효과 반영
                    context = {'skill': skill}
                    # get_description에 context 전달 (시그니처 확인)
                    if hasattr(cost, '_calculate_actual_cost'):
                        # MPCost의 경우 context를 전달
                        cost_desc = cost.get_description(actor, context)
                    else:
                        # 다른 비용 타입은 기존 방식
                        try:
                            cost_desc = cost.get_description(actor, context)
                        except TypeError:
                            cost_desc = cost.get_description(actor)
                    if cost_desc:
                        cost_parts.append(cost_desc)

            cost_text = f" ({', '.join(cost_parts)})" if cost_parts else ""

            name = getattr(skill, 'name', str(skill))
            
            # 스탠스 변경 스킬인 경우 현재 스탠스 → 예상 스탠스 표시
            skill_metadata = getattr(skill, 'metadata', {})
            if 'stance' in skill_metadata:
                # 현재 스탠스 가져오기
                current_stance = getattr(actor, 'current_stance', 0)
                if isinstance(current_stance, str):
                    stance_id_to_index = {
                        "balanced": 0,
                        "attack": 1,
                        "defense": 2,
                        "berserker": 4,
                        "guardian": 5,
                        "speed": 6
                    }
                    current_stance = stance_id_to_index.get(current_stance, 0)
                
                stance_id_to_name = {
                    0: "중립",
                    1: "공격",
                    2: "방어",
                    4: "광전사",
                    5: "수호자",
                    6: "신속"
                }
                current_stance_name = stance_id_to_name.get(current_stance, "중립")
                
                stance_id = skill_metadata['stance']
                if stance_id == "auto":
                    name = f"{current_stance_name} → 상황에 맞게"
                else:
                    stance_id_to_name_map = {
                        "balanced": "중립",
                        "attack": "공격",
                        "defense": "방어",
                        "berserker": "광전사",
                        "guardian": "수호자",
                        "speed": "신속"
                    }
                    target_stance_name = stance_id_to_name_map.get(stance_id, "")
                    if target_stance_name:
                        name = f"{current_stance_name} → {target_stance_name}"
            
            desc = getattr(skill, 'description', '')

            # 사용 불가 시 이유 추가
            full_desc = f"{desc}\n{reason}" if not can_use and reason else desc

            items.append(MenuItem(
                text=f"{name}{cost_text}",
                description=full_desc,
                enabled=can_use,
                value=skill
            ))

        # 뒤로가기
        items.append(MenuItem("← 뒤로", "행동 메뉴로 돌아가기", True, None))

        return CursorMenu(
            title=f"{actor.name}의 스킬",
            items=items,
            x=5,
            y=28,  # 2줄 위로 이동 (30 → 28)
            width=40,
            show_description=True
        )

    def _create_item_menu(self) -> CursorMenu:
        """아이템 메뉴 생성"""
        items = []
        
        if not self.inventory:
            # 인벤토리가 없으면 빈 메뉴
            items.append(MenuItem("← 뒤로", "행동 메뉴로 돌아가기", True, None))
            return CursorMenu(
                title="아이템",
                items=items,
                x=5,
                y=28,
                width=40,
                show_description=True
            )
        
        # 소비 아이템만 필터링 (요리 아이템 제외)
        from src.equipment.item_system import Consumable, ItemType
        from src.cooking.recipe import CookedFood
        from src.core.logger import get_logger, Loggers
        
        logger = get_logger(Loggers.UI)
        
        logger.info(f"[전투 아이템 메뉴] 인벤토리 슬롯 수: {len(self.inventory.slots)}")
        
        for slot_index, slot in enumerate(self.inventory.slots):
            if not slot or not slot.item:
                logger.debug(f"[전투 아이템 메뉴] 슬롯 {slot_index}: 빈 슬롯")
                continue
            
            item = slot.item
            item_name = getattr(item, 'name', '알 수 없는 아이템')
            item_type = getattr(item, 'item_type', None)
            item_class = type(item).__name__
            
            logger.debug(f"[전투 아이템 메뉴] 슬롯 {slot_index}: {item_name} (타입: {item_type}, 클래스: {item_class})")
            
            # 요리 아이템은 전투 중 사용 불가
            if isinstance(item, CookedFood):
                logger.debug(f"[전투 아이템 메뉴] {item_name}: CookedFood로 필터링됨")
                continue
            
            # Consumable 또는 item_type이 CONSUMABLE인 아이템만 표시
            is_consumable = isinstance(item, Consumable) or item_type == ItemType.CONSUMABLE
            
            if not is_consumable:
                logger.debug(f"[전투 아이템 메뉴] {item_name}: Consumable이 아님 (isinstance: {isinstance(item, Consumable)}, item_type: {item_type})")
                continue
            
            logger.info(f"[전투 아이템 메뉴] {item_name}: 메뉴에 추가됨")
            
            item_desc = getattr(item, 'description', '')
            quantity = slot.quantity
            
            # 수량 표시
            name_text = f"{item_name} x{quantity}" if quantity > 1 else item_name
            
            # 사용 가능 여부 (쿨타임 체크는 use_consumable에서 처리)
            enabled = True
            
            items.append(MenuItem(
                text=name_text,
                description=item_desc,
                enabled=enabled,
                value=(slot_index, item)  # (슬롯 인덱스, 아이템) 튜플
            ))
        
        # 아이템이 없으면 메시지 추가
        if not items:
            items.append(MenuItem(
                text="사용 가능한 아이템이 없습니다",
                description="인벤토리에 전투용 아이템이 없습니다",
                enabled=False,
                value=None
            ))
        
        # 뒤로가기
        items.append(MenuItem("← 뒤로", "행동 메뉴로 돌아가기", True, None))
        
        return CursorMenu(
            title="아이템",
            items=items,
            x=5,
            y=28,
            width=40,
            show_description=True
        )

    def handle_input(self, action: GameAction) -> bool:
        """
        입력 처리

        Returns:
            True면 전투 종료
        """
        # ESC나 창 닫기는 무시 (전투 중에는 도주 명령으로만 종료 가능)
        if action == GameAction.ESCAPE or action == GameAction.QUIT:
            return False

        if self.state == CombatUIState.BATTLE_END:
            return True

        # 멀티플레이 모드에서 다른 플레이어의 캐릭터 컨트롤 방지
        if self._should_block_input():
            logger.debug(f"다른 플레이어의 캐릭터 컨트롤 시도 차단: current_actor={getattr(self.current_actor, 'name', None) if self.current_actor else None}")
            return False

        # 행동 메뉴
        if self.state == CombatUIState.ACTION_MENU:
            return self._handle_action_menu(action)

        # 스킬 메뉴
        elif self.state == CombatUIState.SKILL_MENU:
            return self._handle_skill_menu(action)

        # 대상 선택
        elif self.state == CombatUIState.TARGET_SELECT:
            return self._handle_target_select(action)

        # 아이템 메뉴
        elif self.state == CombatUIState.ITEM_MENU:
            return self._handle_item_menu(action)

        # 기믹 상세 보기
        elif self.state == CombatUIState.GIMMICK_VIEW:
            return self._handle_gimmick_view(action)

        # G 키로 기믹 상세 보기 (전투 중 언제든지 가능)
        if action == GameAction.GIMMICK_DETAIL and self.current_actor:
            return self._open_gimmick_view()

        # 로그 스크롤 (언제든지 가능)
        if action == GameAction.PAGE_UP:
            # 위로 스크롤 (오래된 메시지 보기)
            self.log_scroll_offset = min(
                self.log_scroll_offset + 3,
                max(0, len(self.messages) - self.log_visible_lines)
            )
            return False
        elif action == GameAction.PAGE_DOWN:
            # 아래로 스크롤 (최신 메시지 보기)
            self.log_scroll_offset = max(0, self.log_scroll_offset - 3)
            return False

        return False

    def _should_block_input(self) -> bool:
        """
        멀티플레이 모드에서 다른 플레이어의 캐릭터 컨트롤을 차단할지 확인
        
        Returns:
            True면 입력 차단, False면 입력 허용
        """
        # 멀티플레이 모드 확인
        from src.multiplayer.game_mode import get_game_mode_manager
        game_mode_manager = get_game_mode_manager()
        is_multiplayer = game_mode_manager and game_mode_manager.is_multiplayer() if game_mode_manager else False
        
        if not is_multiplayer:
            # 싱글플레이 모드면 차단 안 함
            return False
        
        # current_actor가 없으면 차단 안 함 (대기 상태 등)
        if not self.current_actor:
            return False
        
        # 로컬 플레이어 ID 확인
        local_player_id = self.local_player_id
        if not local_player_id:
            # 로컬 플레이어 ID를 여러 방법으로 확인
            if self.session:
                local_player_id = getattr(self.session, 'local_player_id', None)
                if not local_player_id and hasattr(self.session, 'host_id'):
                    # 호스트인 경우 host_id를 로컬 플레이어 ID로 사용
                    if game_mode_manager:
                        game_local_id = getattr(game_mode_manager, 'local_player_id', None)
                        if game_local_id:
                            local_player_id = game_local_id
        
        if not local_player_id:
            # 로컬 플레이어 ID를 찾을 수 없으면 차단 안 함 (에러 로그만)
            logger.warning("멀티플레이 모드에서 로컬 플레이어 ID를 찾을 수 없습니다")
            return False
        
        # current_actor의 플레이어 ID 확인
        current_actor_player_id = getattr(self.current_actor, 'player_id', None)
        
        # 플레이어 ID가 없으면 (AI 캐릭터 등) 차단 안 함
        if not current_actor_player_id:
            return False
        
        # 로컬 플레이어의 캐릭터가 아니면 차단
        if current_actor_player_id != local_player_id:
            logger.warning(
                f"다른 플레이어의 캐릭터 컨트롤 시도 차단: "
                f"로컬 플레이어={local_player_id}, 현재 액터 플레이어={current_actor_player_id}, "
                f"캐릭터={getattr(self.current_actor, 'name', 'Unknown')}"
            )
            return True
        
        return False

    def _handle_action_menu(self, action: GameAction) -> bool:
        """행동 메뉴 입력 처리"""
        if not self.action_menu:
            return False

        if action == GameAction.MOVE_UP:
            self.action_menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            self.action_menu.move_cursor_down()
        elif action == GameAction.CONFIRM:
            selected_item = self.action_menu.get_selected_item()
            if selected_item:
                self.selected_action = selected_item.value
                self._on_action_selected()
        elif action == GameAction.CANCEL:
            # 취소 불가 (턴은 반드시 행동을 선택해야 넘어감)
            # 아무 작업 안 함
            logger.debug("행동 선택 취소 시도 (불가)")

        return False

    def _handle_skill_menu(self, action: GameAction) -> bool:
        """스킬 메뉴 입력 처리"""
        if not self.skill_menu:
            return False

        if action == GameAction.MOVE_UP:
            self.skill_menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            self.skill_menu.move_cursor_down()
        elif action == GameAction.CONFIRM:
            selected_item = self.skill_menu.get_selected_item()
            if selected_item:
                if selected_item.value is None:  # 뒤로가기
                    self.state = CombatUIState.ACTION_MENU
                else:
                    self.selected_skill = selected_item.value
                    self._start_target_selection()
        elif action == GameAction.CANCEL:
            self.state = CombatUIState.ACTION_MENU

        return False

    def _handle_target_select(self, action: GameAction) -> bool:
        """대상 선택 입력 처리"""
        # 저장된 타겟 리스트 사용
        targets = self.current_target_list

        alive_indices = [i for i, e in enumerate(targets) if getattr(e, 'is_alive', True)]

        if not alive_indices:
            return False

        if action == GameAction.MOVE_UP or action == GameAction.MOVE_LEFT:
            # 이전 살아있는 대상으로 이동
            current_pos = alive_indices.index(self.target_cursor) if self.target_cursor in alive_indices else 0
            new_pos = (current_pos - 1) % len(alive_indices)
            self.target_cursor = alive_indices[new_pos]
        elif action == GameAction.MOVE_DOWN or action == GameAction.MOVE_RIGHT:
            # 다음 살아있는 대상으로 이동
            current_pos = alive_indices.index(self.target_cursor) if self.target_cursor in alive_indices else 0
            new_pos = (current_pos + 1) % len(alive_indices)
            self.target_cursor = alive_indices[new_pos]
        elif action == GameAction.CONFIRM:
            self.selected_target = targets[self.target_cursor]
            # 아이템 사용인 경우 아이템 정보도 전달
            if self.selected_action == ActionType.ITEM and self.selected_item:
                self._execute_current_action()
            else:
                self._execute_current_action()
        elif action == GameAction.CANCEL:
            # 취소 - 이전 상태로
            if self.selected_action == ActionType.SKILL:
                self.state = CombatUIState.SKILL_MENU
            elif self.selected_action == ActionType.ITEM:
                self.state = CombatUIState.ITEM_MENU
            else:
                self.state = CombatUIState.ACTION_MENU
            self.selected_skill = None
            self.selected_item = None
            self.selected_item_index = None

        return False

    def _handle_item_menu(self, action: GameAction) -> bool:
        """아이템 메뉴 입력 처리"""
        if not self.item_menu:
            return False

        if action == GameAction.MOVE_UP:
            self.item_menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            self.item_menu.move_cursor_down()
        elif action == GameAction.CONFIRM:
            selected_item = self.item_menu.get_selected_item()
            if selected_item:
                if selected_item.value is None:  # 뒤로가기
                    self.state = CombatUIState.ACTION_MENU
                else:
                    # 아이템 선택
                    item_data = selected_item.value
                    if isinstance(item_data, tuple) and len(item_data) == 2:
                        self.selected_item_index, self.selected_item = item_data
                        # 아이템 사용 행동 설정
                        self.selected_action = ActionType.ITEM
                        # 아이템 효과에 따라 대상 선택 필요 여부 결정
                        from src.equipment.item_system import Consumable, ItemType
                        item_type = getattr(self.selected_item, 'item_type', None)
                        is_consumable = isinstance(self.selected_item, Consumable) or item_type == ItemType.CONSUMABLE
                        
                        if is_consumable:
                            effect_type = getattr(self.selected_item, 'effect_type', 'heal_hp')
                            # AOE 공격 아이템은 타겟 선택 없이 바로 실행
                            if effect_type in ["aoe_fire", "aoe_ice", "poison_bomb", "thunder_grenade", "debuff_attack", "debuff_defense", "debuff_speed", "smoke_bomb", "break_brv"]:
                                # AOE 아이템: 타겟 선택 없이 바로 실행 (target=None)
                                self.selected_target = None
                                self._execute_current_action()
                            elif effect_type in ["single_lightning", "acid_flask", "damage"]:
                                # 단일 타겟 공격: 적 대상 선택
                                self.current_target_list = self.combat_manager.enemies
                                self.target_cursor = 0
                                self.state = CombatUIState.TARGET_SELECT
                            else:
                                # 회복/버프 아이템: 아군 대상 선택
                                self.current_target_list = self.combat_manager.party
                                self.target_cursor = 0
                                self.state = CombatUIState.TARGET_SELECT
                        else:
                            # Consumable이 아닌 경우도 대상 선택으로 진행
                            self.current_target_list = self.combat_manager.party
                            self.target_cursor = 0
                            self.state = CombatUIState.TARGET_SELECT
        elif action == GameAction.CANCEL:
            self.state = CombatUIState.ACTION_MENU

        return False

    def _on_action_selected(self):
        """행동 선택 후 처리"""
        # 튜플 형식 체크 (기본 공격 스킬, 기믹 상세)
        if isinstance(self.selected_action, tuple):
            action_type, skill = self.selected_action
            if action_type in ("brv_skill", "hp_skill"):
                # 기본 공격 스킬 선택됨
                self.selected_skill = skill
                self._start_target_selection()
                return
            elif action_type == "gimmick_detail":
                # 기믹 상세 보기 선택됨
                self._open_gimmick_view()
                return

        # ActionType 체크
        if self.selected_action == ActionType.SKILL:
            # 스킬 메뉴 열기
            self.skill_menu = self._create_skill_menu(self.current_actor)
            self.state = CombatUIState.SKILL_MENU

        elif self.selected_action == ActionType.ITEM:
            # 아이템 메뉴 열기
            self.item_menu = self._create_item_menu()
            self.state = CombatUIState.ITEM_MENU

        elif self.selected_action == ActionType.DEFEND:
            # 방어는 대상 선택 불필요
            self._execute_current_action()

        elif self.selected_action == ActionType.FLEE:
            # 도망도 대상 선택 불필요
            self._execute_current_action()

        else:
            # BRV/HP 공격 - 대상 선택
            self._start_target_selection()

    def _start_target_selection(self):
        """대상 선택 시작"""
        from src.character.skill_types import SkillTargetType

        # 스킬의 target_type에 따라 대상 결정
        if self.selected_skill:
            target_type = getattr(self.selected_skill, 'target_type', 'single_enemy')

            # "self" 타겟은 타겟 선택 건너뛰기
            if target_type == "self":
                # 타겟 선택 없이 바로 실행
                self.selected_target = self.current_actor
                self._execute_current_action()
                return

            # 문자열 target_type을 Enum으로 매핑 (하위 호환성)
            ally_targets = (
                SkillTargetType.SINGLE_ALLY,
                SkillTargetType.SELF,
                SkillTargetType.ALL_ALLIES,
                "ally",      # 문자열 지원
                "party",     # 문자열 지원
            )

            # 아군 타겟팅 스킬 (회복 등)
            if target_type in ally_targets:
                self.current_target_list = self.combat_manager.party
            else:
                # 적 타겟팅 스킬 (공격 등)
                self.current_target_list = self.combat_manager.enemies
        else:
            # 기본 공격은 적 타겟
            self.current_target_list = self.combat_manager.enemies

        # 살아있는 대상만 필터링
        alive_targets = [e for e in self.current_target_list if getattr(e, 'is_alive', True)]
        if not alive_targets:
            # 모든 대상이 죽었으면 행동 메뉴로 돌아감
            self.state = CombatUIState.ACTION_MENU
            return

        # 첫 번째 살아있는 대상의 인덱스로 커서 설정
        for i, target in enumerate(self.current_target_list):
            if getattr(target, 'is_alive', True):
                self.target_cursor = i
                break

        self.state = CombatUIState.TARGET_SELECT

    def _open_gimmick_view(self) -> bool:
        """기믹 상세 보기 열기"""
        if self.current_actor:
            self.gimmick_view_character = self.current_actor
            self.previous_state = self.state
            self.state = CombatUIState.GIMMICK_VIEW
            logger.debug(f"기믹 상세 보기 열림: {self.current_actor.name}")
        return False

    def _handle_gimmick_view(self, action: GameAction) -> bool:
        """기믹 상세 보기 입력 처리"""
        # 아무 키나 눌러도 닫기
        if action in [GameAction.CANCEL, GameAction.CONFIRM, GameAction.GIMMICK_DETAIL]:
            self.gimmick_view_character = None
            if self.previous_state:
                self.state = self.previous_state
                self.previous_state = None
            else:
                self.state = CombatUIState.ACTION_MENU
            logger.debug("기믹 상세 보기 닫힘")
        return False

    def _execute_current_action(self):
        """현재 선택된 행동 실행"""
        self.state = CombatUIState.EXECUTING

        # 튜플 형식이면 ActionType.SKILL로 변환
        action_type = self.selected_action
        if isinstance(self.selected_action, tuple):
            action_type = ActionType.SKILL  # 기본 공격 스킬도 스킬로 실행

        # 멀티플레이 모드 확인
        from src.multiplayer.game_mode import get_game_mode_manager
        game_mode_manager = get_game_mode_manager()
        is_multiplayer = game_mode_manager and game_mode_manager.is_multiplayer() if game_mode_manager else False
        
        # 호스트 여부 확인
        is_host = False
        if self.session and game_mode_manager:
            local_player_id = getattr(game_mode_manager, 'local_player_id', None) or (
                self.session.host_id if hasattr(self.session, 'host_id') else None
            )
            if local_player_id and hasattr(self.session, 'host_id'):
                is_host = self.session.host_id == local_player_id

        # 멀티플레이 모드에서 클라이언트인 경우 호스트로 액션 전송
        if is_multiplayer and self.combat_sync_manager and self.session and not is_host:
            # 클라이언트: 호스트로 액션 요청 전송
            if not self.current_actor:
                logger.error("멀티플레이 액션 실행 실패: 현재 액터가 없습니다.")
                self.state = CombatUIState.ACTION_MENU
                return

            actor_id = getattr(self.current_actor, 'id', None)
            if not actor_id:
                logger.error("멀티플레이 액션 실행 실패: 액터 ID를 찾을 수 없습니다.")
                self.state = CombatUIState.ACTION_MENU
                return

            local_player_id = getattr(self.session, 'local_player_id', None) or (
                self.session.host_id if hasattr(self.session, 'host_id') else None
            )
            if not local_player_id:
                logger.error("멀티플레이 액션 실행 실패: 로컬 플레이어 ID를 찾을 수 없습니다.")
                self.state = CombatUIState.ACTION_MENU
                return

            action_data = {
                "action_type": action_type.value if hasattr(action_type, 'value') else str(action_type),
                "target_id": getattr(self.selected_target, 'id', None) if self.selected_target else None,
                "skill_id": getattr(self.selected_skill, 'id', None) if self.selected_skill else None,
                "item_id": getattr(self.selected_item, 'id', None) if self.selected_item else None,
                "item_index": self.selected_item_index,
            }

            # 비동기 액션 요청 전송
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.combat_sync_manager.request_action(local_player_id, actor_id, action_data))
                else:
                    asyncio.run(self.combat_sync_manager.request_action(local_player_id, actor_id, action_data))
            except RuntimeError:
                # 이벤트 루프가 없으면 동기적으로 처리
                logger.warning("비동기 이벤트 루프 없음, 동기 처리 시도")
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.combat_sync_manager.request_action(local_player_id, actor_id, action_data))
                    loop.close()
                except Exception as e:
                    logger.error(f"멀티플레이 액션 전송 실패: {e}", exc_info=True)

            logger.info(f"멀티플레이 액션 요청 전송: {local_player_id} - {actor_id} - {action_type.value if hasattr(action_type, 'value') else action_type}")

            # 클라이언트는 액션 요청 후 ATB 대기 상태로 전환
            self.state = CombatUIState.WAITING_ATB
            if hasattr(self.combat_manager.atb, 'set_player_selecting'):
                self.combat_manager.atb.set_player_selecting(local_player_id, False)
            if hasattr(self.combat_manager.atb, 'set_action_confirmed'):
                self.combat_manager.atb.set_action_confirmed(local_player_id)

        else:
            # 싱글플레이 모드 또는 멀티플레이 호스트 (직접 실행)
            # 아이템 사용인 경우 아이템 정보 전달
            kwargs = {}
            if action_type == ActionType.ITEM and self.selected_item:
                kwargs['item'] = self.selected_item
                kwargs['item_index'] = self.selected_item_index
            
            result = self.combat_manager.execute_action(
                actor=self.current_actor,
                action_type=action_type,
                target=self.selected_target,
                skill=self.selected_skill,
                **kwargs
            )

            # 결과 메시지 표시
            self._show_action_result(result)

            # 행동 후 대기 시간 설정 (1.5초)
            self.action_delay_frames = self.action_delay_max
            
            # 현재 액터의 플레이어 ID 저장 (다음 아군 확인 전에 저장)
            current_actor_player_id = getattr(self.current_actor, 'player_id', None) if self.current_actor else None
            
            # 상태 초기화 (다음 아군 확인을 위해 먼저 초기화)
            self.current_actor = None

            # 멀티플레이: 다음 행동 가능한 아군 확인
            if is_multiplayer and self.session and hasattr(self.combat_manager.atb, 'set_player_selecting'):
                # 다음 행동 가능한 아군이 있는지 확인
                ready_combatants = self.combat_manager.atb.get_action_order()
                next_ally = None
                for combatant in ready_combatants:
                    if combatant in self.combat_manager.allies:
                        next_ally = combatant
                        break
                
                if next_ally:
                    # 다음 아군이 있으면 불릿타임 유지하고 바로 다음 턴으로 전환
                    # 현재 액터의 불릿타임은 해제하지만, 다음 아군의 불릿타임을 즉시 활성화
                    if current_actor_player_id:
                        self.combat_manager.atb.set_player_selecting(current_actor_player_id, False)
                        logger.debug(f"플레이어 {current_actor_player_id} 행동 선택 완료 → 다음 아군 턴으로 전환")
                    
                    # 다음 아군의 턴 즉시 시작 (불릿타임 유지)
                    self.current_actor = next_ally
                    
                    # 봇인지 확인 (player_id가 "bot_"으로 시작)
                    next_ally_player_id = getattr(next_ally, 'player_id', None)
                    is_bot = next_ally_player_id and str(next_ally_player_id).startswith('bot_')
                    
                    if is_bot:
                        # 봇 턴: UI 표시하지 않고 WAITING_ATB 상태 유지
                        self.state = CombatUIState.WAITING_ATB
                        self.add_message(f"{next_ally.name}(봇)의 턴 - 자동 행동", (150, 150, 255))
                        logger.info(f"봇 {next_ally.name} 턴: UI 건너뛰고 자동 행동 대기")
                    else:
                        # 플레이어 턴: 일반 UI 표시
                        self.action_menu = self._create_action_menu(self.current_actor)
                        self.state = CombatUIState.ACTION_MENU
                        self.add_message(f"{next_ally.name}의 턴!", (100, 255, 255))
                        play_sfx("ui", "cursor_select")
                    
                    # 불릿타임 활성화
                    if next_ally_player_id:
                        self.combat_manager.atb.set_player_selecting(next_ally_player_id, True)
                        logger.info(f"🔫 불릿타임 유지: 다음 {'봇' if is_bot else '플레이어'} {next_ally_player_id} 행동 선택 시작")
                    
                    # 상태 초기화는 건너뛰고 바로 반환
                    return
                else:
                    # 다음 아군이 없으면 불릿타임 해제
                    if current_actor_player_id:
                        self.combat_manager.atb.set_player_selecting(current_actor_player_id, False)
                        logger.debug(f"플레이어 {current_actor_player_id} 행동 선택 완료 (마지막 아군, 1.5초 정지)")
        self.selected_action = None
        self.selected_skill = None
        self.selected_target = None
        self.selected_item = None
        self.selected_item_index = None
        # 주의: state는 update()에서 delay 후 WAITING_ATB로 전환됨

        # 전투 종료 확인
        if self.combat_manager.state in [CombatState.VICTORY, CombatState.DEFEAT, CombatState.FLED]:
            self.battle_ended = True
            self.battle_result = self.combat_manager.state
            self.state = CombatUIState.BATTLE_END
            # BGM은 main.py에서 처리 (필드 BGM으로 전환하기 위해)

    def _show_action_result(self, result: Dict[str, Any]):
        """행동 결과 메시지 표시"""
        action = result.get("action", "unknown")

        if action == "brv_attack":
            damage = result.get("damage", 0)
            is_crit = result.get("is_critical", False)
            is_break = result.get("is_break", False)
            is_miss = result.get("is_miss", False)

            # 빗나감 체크
            if is_miss:
                # 공격자/방어자 정보
                attacker = self.current_actor
                target = self.selected_target
                if attacker and target:
                    attacker_name = getattr(attacker, 'name', '알 수 없음')
                    target_name = getattr(target, 'name', '알 수 없음')

                    # 아군/적 구분
                    is_attacker_ally = attacker in self.combat_manager.allies
                    is_target_ally = target in self.combat_manager.allies

                    attacker_type = "아군" if is_attacker_ally else "적"
                    target_type = "아군" if is_target_ally else "적"

                    msg = f"[빗나감] {attacker_type} {attacker_name}의 공격이 {target_type} {target_name}에게 빗나갔다!"
                    color = (150, 150, 150)
                else:
                    msg = "[빗나감] 공격이 빗나갔다!"
                    color = (150, 150, 150)
            else:
                msg = f"BRV 공격! {damage} 데미지"
                if is_crit:
                    msg += " [크리티컬!]"
                if is_break:
                    msg += " [BREAK!]"

                color = (255, 255, 100) if is_crit else (200, 200, 200)

            self.add_message(msg, color)

        elif action == "hp_attack":
            damage = result.get("hp_damage", 0)
            is_ko = result.get("is_ko", False)

            msg = f"HP 공격! {damage} HP 데미지"
            if is_ko:
                msg += " [격파!]"

            color = (255, 100, 100)
            self.add_message(msg, color)

        elif action == "defend":
            self.add_message("방어 자세!", (100, 200, 255))

        elif action == "flee":
            success = result.get("success", False)
            if success:
                self.add_message("도망쳤다!", (255, 255, 100))
            else:
                self.add_message("도망칠 수 없다!", (255, 100, 100))

        elif action == "skill":
            skill_name = result.get("skill_name", "스킬")
            success = result.get("success", False)

            if success:
                message = result.get("message", f"{skill_name} 사용!")
                # 여러 줄 메시지에서 기믹 관련 줄 필터링
                import re
                lines = message.split("\n")
                filtered_lines = []
                for line in lines:
                    # "  → "로 시작하는 효과 메시지 체크
                    if line.strip().startswith("→"):
                        # 기믹 수치 변화 패턴 체크
                        gimmick_pattern = r'.+의\s+\w+:\s*\d+\s*->\s*\d+'
                        if re.search(gimmick_pattern, line):
                            # 기믹 관련 메시지는 제외
                            continue
                    filtered_lines.append(line)
                
                # 필터링된 메시지 조합 (빈 줄 제거)
                filtered_message = "\n".join(filtered_lines).strip()
                if filtered_message:  # 메시지가 남아있으면 추가
                    self.add_message(filtered_message, (100, 255, 255))
                else:
                    # 모든 메시지가 필터링되었으면 기본 메시지만 추가
                    self.add_message(f"{skill_name} 사용!", (100, 255, 255))
            else:
                error = result.get("error", "사용 실패")
                self.add_message(f"❌ {skill_name}: {error}", (255, 100, 100))

        elif action == "item":
            item_name = result.get("item_name", "아이템")
            success = result.get("success", False)
            effect_type = result.get("effect_type", "")

            if not success:
                error = result.get("error", "사용 실패")
                self.add_message(f"❌ {item_name}: {error}", (255, 100, 100))
            else:
                # 효과 타입별 메시지 표시
                if effect_type == "heal_hp":
                    healing = result.get("healing", 0)
                    target_name = result.get("target", "대상")
                    self.add_message(f"{item_name} 사용! {target_name} HP +{healing}", (100, 255, 100))
                elif effect_type == "heal_mp":
                    mp_healing = result.get("mp_healing", 0)
                    target_name = result.get("target", "대상")
                    self.add_message(f"{item_name} 사용! {target_name} MP +{mp_healing}", (100, 200, 255))
                elif effect_type in ["aoe_fire", "aoe_ice", "poison_bomb", "thunder_grenade"]:
                    aoe_damage = result.get("aoe_damage", 0)
                    targets_hit = result.get("targets_hit", 0)
                    effect_names = {
                        "aoe_fire": "🔥 화염",
                        "aoe_ice": "❄ 냉기",
                        "poison_bomb": "☠ 독",
                        "thunder_grenade": "⚡ 번개"
                    }
                    effect_name = effect_names.get(effect_type, "데미지")
                    if targets_hit > 0:
                        self.add_message(f"{item_name} 사용! {effect_name} 데미지 {aoe_damage} (적 {targets_hit}명)", (255, 150, 50))
                    else:
                        self.add_message(f"{item_name} 사용! 하지만 적이 없습니다.", (200, 200, 200))
                elif effect_type in ["single_lightning", "acid_flask"]:
                    damage = result.get("damage", 0)
                    target_name = result.get("target", "적")
                    effect_names = {
                        "single_lightning": "⚡ 번개",
                        "acid_flask": "💧 산성"
                    }
                    effect_name = effect_names.get(effect_type, "데미지")
                    self.add_message(f"{item_name} 사용! {target_name}에게 {effect_name} 데미지 {damage}", (255, 150, 50))
                elif effect_type in ["debuff_attack", "debuff_defense", "debuff_speed", "smoke_bomb"]:
                    targets_debuffed = result.get("targets_debuffed", 0)
                    debuff_names = {
                        "debuff_attack": "공격력 감소",
                        "debuff_defense": "방어력 감소",
                        "debuff_speed": "속도 감소",
                        "smoke_bomb": "명중률 감소"
                    }
                    debuff_name = debuff_names.get(effect_type, "디버프")
                    if targets_debuffed > 0:
                        self.add_message(f"{item_name} 사용! 적 {targets_debuffed}명에게 {debuff_name}", (255, 200, 100))
                    else:
                        self.add_message(f"{item_name} 사용! 하지만 적이 없습니다.", (200, 200, 200))
                elif effect_type == "break_brv":
                    brv_loss = result.get("brv_loss", 0)
                    if brv_loss > 0:
                        self.add_message(f"{item_name} 사용! 적 전체 BRV -{brv_loss}", (255, 150, 50))
                    else:
                        self.add_message(f"{item_name} 사용! 하지만 적이 없습니다.", (200, 200, 200))
                elif effect_type in ["barrier_crystal", "haste_crystal", "power_tonic", "defense_elixir", "regen_crystal", "mp_regen_crystal"]:
                    target_name = result.get("target", "대상")
                    buff_names = {
                        "barrier_crystal": "방어력 상승",
                        "haste_crystal": "속도 상승",
                        "power_tonic": "공격력 상승",
                        "defense_elixir": "방어력 상승",
                        "regen_crystal": "HP 재생",
                        "mp_regen_crystal": "MP 재생"
                    }
                    buff_name = buff_names.get(effect_type, "버프")
                    self.add_message(f"{item_name} 사용! {target_name}에게 {buff_name}", (100, 255, 255))
                elif effect_type == "status_cleanse" or effect_type == "cure":
                    if result.get("status_cured"):
                        target_name = result.get("target", "대상")
                        self.add_message(f"{item_name} 사용! {target_name}의 상태이상 치료", (100, 255, 255))
                else:
                    # 기본 메시지
                    self.add_message(f"{item_name} 사용!", (200, 200, 200))

    def update(self, delta_time: float = 1.0):
        """업데이트 (매 프레임)"""
        # 행동 후 대기 시간 처리
        if self.action_delay_frames > 0:
            self.action_delay_frames -= 1
            if self.action_delay_frames == 0 and self.state == CombatUIState.EXECUTING:
                # 대기 완료, WAITING_ATB로 전환
                self.state = CombatUIState.WAITING_ATB

        # 플레이어가 선택 중인지 또는 대기 중인지 확인
        is_player_selecting = self.state in [
            CombatUIState.ACTION_MENU,
            CombatUIState.SKILL_MENU,
            CombatUIState.TARGET_SELECT,
            CombatUIState.ITEM_MENU,
            CombatUIState.GIMMICK_VIEW,  # 기믹 상세 보기 중에도 시간 정지
            CombatUIState.EXECUTING  # 행동 실행 후 대기 중에도 시간 정지
        ]

        # 멀티플레이 모드 확인
        from src.multiplayer.game_mode import get_game_mode_manager
        game_mode_manager = get_game_mode_manager()
        is_multiplayer = game_mode_manager and game_mode_manager.is_multiplayer() if game_mode_manager else False

        # 멀티플레이가 아닐 때만 시간 정지 로직 적용
        # 멀티플레이에서는 불릿타임 모드로 속도 조절
        if not is_multiplayer:
            # 플레이어가 선택 중이거나 대기 중일 때는 ATB 증가를 멈춤
            if is_player_selecting:
                # ATB 업데이트 스킵 (시간 정지)
                # 플레이어 턴으로 표시하여 ATB 증가 방지
                self.combat_manager.state = CombatState.PLAYER_TURN
            else:
                # 일반 진행
                if self.combat_manager.state == CombatState.PLAYER_TURN:
                    self.combat_manager.state = CombatState.IN_PROGRESS
        else:
            # 멀티플레이: 항상 IN_PROGRESS 상태 유지 (불릿타임 모드로 속도 조절)
            if self.combat_manager.state == CombatState.PLAYER_TURN:
                self.combat_manager.state = CombatState.IN_PROGRESS

        # 전투 매니저 업데이트
        self.combat_manager.update(delta_time)

        # ATB 업데이트 직후 즉시 턴 체크
        # 행동 가능한 캐릭터 확인
        ready = self.combat_manager.atb.get_action_order()

        if ready and not self.action_delay_frames:
            # 다음 행동자
            actor = ready[0]
            
            # 캐릭터 타입 확인
            actor_player_id = getattr(actor, 'player_id', None)
            is_bot = actor_player_id and str(actor_player_id).startswith('bot_')
            
            if actor in self.combat_manager.enemies:
                # 적 턴: 기존 EnemyAI 처리
                self._execute_enemy_turn(actor)
                
            elif is_bot:
                # 봇 턴: AI가 자동으로 행동
                logger.info(f"봇 {actor.name} 턴 시작 - AI 행동 결정")
                self._process_bot_turn(actor)
                
            elif actor in self.combat_manager.allies:
                # 플레이어 턴: UI 표시 (WAITING_ATB 상태일 때만)
                if self.state == CombatUIState.WAITING_ATB:
                    self.current_actor = actor
                    self.action_menu = self._create_action_menu(actor)
                    self.state = CombatUIState.ACTION_MENU
                    self.add_message(f"{actor.name}의 턴!", (100, 255, 255))
                    play_sfx("ui", "cursor_select")

        # 전투 종료 체크
        if self.combat_manager.state in [CombatState.VICTORY, CombatState.DEFEAT, CombatState.FLED]:
            if not self.battle_ended:
                logger.debug(f"전투 종료: {self.combat_manager.state}")
                self.battle_ended = True
                self.battle_result = self.combat_manager.state
                self.state = CombatUIState.BATTLE_END
    
        # 메시지 타이머 감소 (표시용이지만, 메시지는 사라지지 않고 계속 저장됨)
        for msg in self.messages:
            msg.frames_remaining -= 1
        # 메시지는 제거하지 않음 (스크롤로 항상 볼 수 있도록)

        # 불릿타임 해제 체크: 행동 선택이 완료되면 불릿타임 해제
        if is_multiplayer and hasattr(self.combat_manager.atb, 'set_player_selecting'):
            # 행동 선택 중인 상태 (ACTION_MENU, SKILL_MENU, TARGET_SELECT, ITEM_MENU)
            is_selecting_action = self.state in [
                CombatUIState.ACTION_MENU,
                CombatUIState.SKILL_MENU,
                CombatUIState.TARGET_SELECT,
                CombatUIState.ITEM_MENU
            ]
            
            if self.current_actor:
                actor_player_id = getattr(self.current_actor, 'player_id', None)
                if actor_player_id:
                    # 행동 선택 중이 아니면 불릿타임 해제 (EXECUTING, WAITING_ATB 등)
                    if not is_selecting_action:
                        self.combat_manager.atb.set_player_selecting(actor_player_id, False)
                        logger.debug(f"불릿타임 해제: 플레이어 {actor_player_id} (상태: {self.state.value})")
            elif not is_selecting_action:
                # current_actor가 없고 행동 선택 중이 아니면 모든 플레이어의 불릿타임 해제
                if hasattr(self.combat_manager.atb, 'players_selecting_action'):
                    for player_id in list(self.combat_manager.atb.players_selecting_action):
                        self.combat_manager.atb.set_player_selecting(player_id, False)
                        logger.debug(f"불릿타임 해제: 플레이어 {player_id} (액터 없음, 상태: {self.state.value})")

    def _get_bot_instance(self, character: Any) -> Any:
        """
        캐릭터의 봇 인스턴스 찾기
        
        Args:
            character: 봇이 조종하는 캐릭터
        
        Returns:
            AdvancedAIBot 인스턴스 또는 None
        """
        if not self.session:
            return None
        
        bot_id = getattr(character, 'player_id', None)
        if not bot_id:
            return None
            
        if not str(bot_id).startswith('bot_'):
            return None
        
        # 1. Session.bot_manager에서 찾기 (AdvancedBotManager) - 최우선
        if hasattr(self.session, 'bot_manager') and self.session.bot_manager:
            if bot_id in self.session.bot_manager.bots:
                return self.session.bot_manager.bots[bot_id]
        
        # 2. Session.bots에서 찾기 (이전 호환성)
        if hasattr(self.session, 'bots'):
            return self.session.bots.get(bot_id)
        
        return None
    
    def _process_bot_turn(self, actor: Any):
        """
        봇 턴 처리 - AI가 행동 결정 및 실행
        
        Args:
            actor: 봇이 조종하는 캐릭터
        """
        # 봇 인스턴스 찾기
        bot = self._get_bot_instance(actor)
        
        if not bot:
            logger.warning(f"봇 인스턴스를 찾을 수 없음: {actor.name}")
            # Fallback: 기본 BRV 공격
            self._execute_default_bot_action(actor)
            return
        
        try:
            # 봇 AI로 행동 결정
            action = bot.decide_action(
                character=actor,
                allies=self.combat_manager.allies,
                enemies=self.combat_manager.enemies
            )
            
            # 행동 실행
            self._execute_bot_action(actor, action)
            
        except Exception as e:
            logger.error(f"봇 턴 처리 실패: {e}", exc_info=True)
            # Fallback
            self._execute_default_bot_action(actor)
    
    def _execute_bot_action(self, actor: Any, action: dict):
        """
        봇이 결정한 행동 실행
        
        Args:
            actor: 행동자
            action: 행동 정보 {type, skill, target}
        """
        action_type = action.get("type")
        target = action.get("target")
        skill = action.get("skill")
        
        logger.debug(f"봇 행동 실행: {actor.name} → {action_type}")
        
        # ActionType 변환
        if action_type == "skill" and skill:
            result = self.combat_manager.execute_action(
                actor=actor,
                action_type=ActionType.SKILL,
                target=target,
                skill=skill
            )
        elif action_type == "hp_attack":
            result = self.combat_manager.execute_action(
                actor=actor,
                action_type=ActionType.HP_ATTACK,
                target=target
            )
        elif action_type == "attack":  # BRV 공격
            result = self.combat_manager.execute_action(
                actor=actor,
                action_type=ActionType.BRV_ATTACK,
                target=target
            )
        elif action_type == "defend":
            result = self.combat_manager.execute_action(
                actor=actor,
                action_type=ActionType.DEFEND
            )
        else:
            logger.warning(f"알 수 없는 행동 타입: {action_type}")
            result = {}
        
        # 결과 메시지 표시
        self._show_action_result(result)
        
        # 행동 후 대기 시간
        self.action_delay_frames = self.action_delay_max
    
    def _execute_default_bot_action(self, actor: Any):
        """
        봇 Fallback 행동 (기본 BRV 공격)
        
        Args:
            actor: 행동자
        """
        # 살아있는 적 찾기
        alive_enemies = [e for e in self.combat_manager.enemies if getattr(e, 'is_alive', True)]
        
        if not alive_enemies:
            return
        
        # 랜덤 타겟
        import random
        target = random.choice(alive_enemies)
        
        # BRV 공격
        result = self.combat_manager.execute_action(
            actor=actor,
            action_type=ActionType.BRV_ATTACK,
            target=target
        )
        
        self._show_action_result(result)
        self.action_delay_frames = self.action_delay_max

    def _check_ready_enemies(self):
        """행동 가능한 적 확인 (항상 체크)"""
        ready = self.combat_manager.atb.get_action_order()

        if not ready:
            return

        # 적군 턴 (AI) - 아군이 행동 선택 중일 때도 실행 가능
        for combatant in ready:
            if combatant in self.combat_manager.enemies:
                self._execute_enemy_turn(combatant)
                return

    def _check_ready_allies(self):
        """행동 가능한 아군 확인 (WAITING_ATB 상태일 때만)"""
        ready = self.combat_manager.atb.get_action_order()

        if not ready:
            return

        # 아군 턴
        for combatant in ready:
            if combatant in self.combat_manager.allies:
                # 행동 불가능 상태 확인 (paralyze, stun 등)
                if hasattr(combatant, 'status_manager'):
                    if not combatant.status_manager.can_act():
                        # 행동 불가능 상태이상 확인
                        from src.combat.status_effects import StatusType
                        blocking_status = None
                        status_name = None
                        
                        for effect in combatant.status_manager.status_effects:
                            if effect.status_type in [
                                StatusType.STUN, StatusType.SLEEP, StatusType.FREEZE,
                                StatusType.PETRIFY, StatusType.PARALYZE, StatusType.TIME_STOP
                            ]:
                                blocking_status = effect.status_type
                                status_name = effect.name
                                break
                        
                        if blocking_status:
                            # 행동 불가능 상태이상: 자동으로 턴 넘기기
                            actor_name = getattr(combatant, 'name', 'Unknown')
                            logger.info(f"{actor_name}은(는) {status_name}로 인해 행동할 수 없습니다. 턴 자동 넘김.")
                            
                            # 메시지 표시
                            self.add_message(f"{actor_name}은(는) {status_name}로 인해 행동할 수 없습니다.", (200, 100, 100))
                            
                            # ATB 소비 (턴 넘기기)
                            self.combat_manager.atb.consume_atb(combatant)
                            
                            # 멀티플레이: 플레이어 선택 상태 해제
                            actor_player_id = getattr(combatant, 'player_id', None)
                            if actor_player_id and hasattr(self.combat_manager.atb, 'set_player_selecting'):
                                self.combat_manager.atb.set_player_selecting(actor_player_id, False)
                            
                            # 상태이상 지속 시간 감소 (턴 소모)
                            if hasattr(combatant, 'status_manager'):
                                expired_effects = combatant.status_manager.update_duration()
                                if expired_effects:
                                    for effect in expired_effects:
                                        logger.info(f"{actor_name}의 {effect.name} 효과가 해제되었습니다.")
                            
                            # WAITING_ATB 상태 유지 (다음 턴 대기)
                            return
                
                # 봇인지 확인 (봇 관리자가 있고, 플레이어 ID가 봇 목록에 있는지)
                actor_player_id = getattr(combatant, 'player_id', None)
                is_bot = False
                bot = None
                
                # 1. self.bot_manager 사용 (일반 봇 매니저)
                if hasattr(self, 'bot_manager') and self.bot_manager and actor_player_id:
                    # get_bot이 없으면 bots 딕셔너리 확인
                    if hasattr(self.bot_manager, 'get_bot'):
                        bot = self.bot_manager.get_bot(actor_player_id)
                    elif hasattr(self.bot_manager, 'bots'):
                        bot = self.bot_manager.bots.get(actor_player_id)
                        
                    if bot:
                        is_bot = True
                        if hasattr(bot, 'set_combat_manager'):
                            bot.set_combat_manager(self.combat_manager, self)
                
                # 2. _get_bot_instance 사용 (AdvancedBotManager 및 Session 통합 검색) - 이게 더 확실함
                if not bot:
                    bot_instance = self._get_bot_instance(combatant)
                    if bot_instance:
                        is_bot = True
                        bot = bot_instance
                        if hasattr(bot, 'set_combat_manager'):
                            bot.set_combat_manager(self.combat_manager, self)

                if is_bot and bot:
                    # 봇 자동 전투: 즉시 액션 선택 및 실행
                    logger.info(f"봇 {getattr(combatant, 'name', 'Unknown')}의 턴 - 자동 액션 선택 (ID: {actor_player_id})")
                    self.current_actor = combatant
                    
                    try:
                        # 봇 행동 결정 메서드 호출 (decide_action 우선, 없으면 auto_combat_action)
                        if hasattr(bot, 'decide_action'):
                            action_data = bot.decide_action(
                                character=combatant,
                                allies=self.combat_manager.allies,
                                enemies=self.combat_manager.enemies
                            )
                        elif hasattr(bot, 'auto_combat_action'):
                            action_data = bot.auto_combat_action(
                                actor=combatant,
                                allies=self.combat_manager.allies,
                                enemies=self.combat_manager.enemies
                            )
                        else:
                            logger.error(f"봇 {actor_player_id}에 행동 결정 메서드가 없습니다.")
                            action_data = None
                            
                        if action_data:
                            # decide_action은 {type, skill, target} 반환
                            # auto_combat_action은 {type, skill_id, target} 반환
                            
                            # 공통 처리
                            self._execute_bot_action(combatant, action_data)
                        else:
                            # 행동 결정 실패 시 기본 행동
                            logger.warning(f"봇 행동 결정 실패 (None 반환). 기본 행동 수행.")
                            self._execute_default_bot_action(combatant)
                            
                    except Exception as e:
                        logger.error(f"봇 턴 처리 중 오류 발생: {e}", exc_info=True)
                        self._execute_default_bot_action(combatant)
                    
                    return
                
                # 일반 플레이어 턴
                # 아군 턴 시작 SFX (선택 SFX와 동일)
                play_sfx("ui", "cursor_select")

                # 멀티플레이 모드에서 로컬 플레이어의 캐릭터만 current_actor로 설정
                # (다른 플레이어의 캐릭터는 컨트롤하지 않음)
                should_set_actor = True
                
                # 멀티플레이 모드 확인
                from src.multiplayer.game_mode import get_game_mode_manager
                game_mode_manager = get_game_mode_manager()
                is_multiplayer_mode = game_mode_manager and game_mode_manager.is_multiplayer() if game_mode_manager else False
                
                if is_multiplayer_mode:
                    # 로컬 플레이어 ID 확인
                    local_player_id = self.local_player_id
                    if not local_player_id:
                        if self.session:
                            local_player_id = getattr(self.session, 'local_player_id', None)
                    
                    # 현재 액터의 플레이어 ID 확인
                    actor_player_id = getattr(combatant, 'player_id', None)
                    
                    # 로컬 플레이어의 캐릭터가 아니면 current_actor 설정하지 않음
                    if actor_player_id and local_player_id and actor_player_id != local_player_id:
                        should_set_actor = False
                        logger.debug(
                            f"다른 플레이어의 캐릭터 턴: {combatant.name} (플레이어={actor_player_id}, "
                            f"로컬 플레이어={local_player_id}) - current_actor 설정 안 함"
                        )
                        # 다른 플레이어의 캐릭터는 자동으로 행동 선택 (ATB 대기 상태 유지)
                        self.state = CombatUIState.WAITING_ATB
                        self.current_actor = None
                        
                        # 다른 플레이어의 행동 선택 시작 알림 (불릿타임 모드 진입)
                        if hasattr(self.combat_manager.atb, 'set_player_selecting') and actor_player_id:
                            self.combat_manager.atb.set_player_selecting(actor_player_id, True)
                            logger.info(f"🔫 불릿타임 활성화 요청: 플레이어 {actor_player_id} 행동 선택 시작")
                        
                        return
                
                if should_set_actor:
                    self.current_actor = combatant
                    self.action_menu = self._create_action_menu(self.current_actor)  # actor 전달
                    self.state = CombatUIState.ACTION_MENU
                    self.add_message(f"{combatant.name}의 턴!", (100, 255, 255))
                    
                    # 멀티플레이: 행동 선택 시작 알림 (불릿타임 모드 진입)
                    # 현재 액터가 어떤 플레이어의 캐릭터든 불릿타임 활성화
                    if is_multiplayer_mode and hasattr(self.combat_manager.atb, 'set_player_selecting'):
                        # 현재 액터의 플레이어 ID 확인
                        if actor_player_id:
                            # 어떤 플레이어든 행동 선택 중이면 불릿타임 활성화
                            self.combat_manager.atb.set_player_selecting(actor_player_id, True)
                            logger.info(f"🔫 불릿타임 활성화 요청: 플레이어 {actor_player_id} 행동 선택 시작")
                        else:
                            # 플레이어 ID가 없으면 (AI나 싱글플레이) 로그만 출력
                            logger.warning(f"⚠️ 플레이어 ID 없음 - combatant={combatant.name}, 불릿타임 비활성화")
                    elif not is_multiplayer_mode:
                        logger.debug("싱글플레이 모드 - 불릿타임 비활성화")
                    elif not hasattr(self.combat_manager.atb, 'set_player_selecting'):
                        logger.error(f"❌ ATB 시스템에 set_player_selecting 메서드 없음: {type(self.combat_manager.atb).__name__}")
                
                return

    def _execute_enemy_turn(self, enemy: Any):
        """적 턴 실행 (AI 사용)"""
        try:
            # CombatManager의 execute_enemy_turn 사용 (새로운 AI 시스템)
            result = self.combat_manager.execute_enemy_turn(enemy)
            
            if result:
                self._show_action_result(result)
            else:
                # AI 결정 실패 시 기본 메시지
                self.add_message(f"{enemy.name}의 행동 결정 실패", (200, 200, 200))

            # 전투 종료 확인
            if self.combat_manager.state in [CombatState.VICTORY, CombatState.DEFEAT]:
                self.battle_ended = True
                self.battle_result = self.combat_manager.state
                self.state = CombatUIState.BATTLE_END
        except Exception as e:
            # AI 실행 오류 시 안전장치 (기본 공격)
            logger.error(f"적 AI 실행 오류: {e}")
            allies_alive = [a for a in self.combat_manager.allies if getattr(a, 'is_alive', True)]
            if allies_alive:
                import random
                target = random.choice(allies_alive)
                
                # 기본 BRV 공격
                result = self.combat_manager.execute_action(
                    actor=enemy,
                    action_type=ActionType.BRV_ATTACK,
                    target=target
                )
                
                if result:
                    self._show_action_result(result)
                
                # 전투 종료 확인
                if self.combat_manager.state in [CombatState.VICTORY, CombatState.DEFEAT]:
                    self.battle_ended = True
                    self.battle_result = self.combat_manager.state
                    self.state = CombatUIState.BATTLE_END

    def add_message(self, text: str, color: Tuple[int, int, int] = (255, 255, 255)):
        """메시지 추가 (스크롤 형식 - 제한 없이 계속 저장)"""
        # 기믹 관련 수치 증감 메시지 필터링 (예: "이름의 필드: 값 -> 값" 형식)
        import re
        # 기믹 수치 변화 패턴 체크: "이름의 필드명: 숫자 -> 숫자" 또는 "이름의 필드명: 숫자 -> 숫자"
        gimmick_pattern = r'.+의\s+\w+:\s*\d+\s*->\s*\d+'
        if re.match(gimmick_pattern, text):
            # 기믹 관련 메시지는 로그에 추가하지 않음
            logger.debug(f"기믹 메시지 필터링됨: {text}")
            return
        
        msg = CombatMessage(text=text, color=color)
        self.messages.append(msg)

        # 새로운 메시지가 추가되면 스크롤을 최신으로 (옵션)
        # 사용자가 스크롤 중이면 그대로 유지하는 것이 나을 수도 있음
        
        logger.debug(f"전투 메시지: {text}")

    def render(self, console: tcod.console.Console):
        """렌더링"""
        render_space_background(console, self.screen_width, self.screen_height)

        # 제목
        console.print(
            self.screen_width // 2 - 5,
            1,
            " 전투 ",
            fg=(255, 255, 100)
        )

        # 아군 상태
        self._render_allies(console)

        # 적군 상태
        self._render_enemies(console)

        # 메시지 로그
        self._render_messages(console)

        # 상태별 UI
        if self.state == CombatUIState.ACTION_MENU and self.action_menu:
            self.action_menu.render(console)

        elif self.state == CombatUIState.SKILL_MENU and self.skill_menu:
            self.skill_menu.render(console)

        elif self.state == CombatUIState.TARGET_SELECT:
            self._render_target_select(console)

        elif self.state == CombatUIState.ITEM_MENU:
            self._render_item_menu(console)

        elif self.state == CombatUIState.GIMMICK_VIEW:
            self._render_gimmick_view(console)

        elif self.state == CombatUIState.BATTLE_END:
            self._render_battle_end(console)

    def _render_allies(self, console: tcod.console.Console):
        """아군 상태 렌더링 (상세)"""
        console.print(5, 4, "[아군 파티]", fg=(100, 255, 100))

        for i, ally in enumerate(self.combat_manager.allies):
            y = 6 + i * 6  # 더 큰 간격

            # 이름 + 상태
            name_color = (255, 255, 255) if ally.is_alive else (100, 100, 100)

            # 현재 행동 중인 캐릭터 표시 또는 타겟 선택 화살표
            if ally == self.current_actor:
                # 현재 행동 중
                turn_indicator = "▶ "
                indicator_color = (255, 255, 100)
            elif self.state == CombatUIState.TARGET_SELECT:
                # 타겟 선택 중 - 아군이 타겟 리스트에 있는지 확인
                is_targeted = ally in self.current_target_list

                # 광역 스킬 확인
                is_aoe = self.selected_skill and getattr(self.selected_skill, 'is_aoe', False)

                if is_aoe and is_targeted:
                    # 광역 스킬 - 모든 타겟에 화살표
                    turn_indicator = "◆ "
                    indicator_color = (100, 255, 255)
                elif is_targeted and i == self.target_cursor:
                    # 단일 타겟 - 선택된 대상에만 화살표
                    turn_indicator = "▶ "
                    indicator_color = (100, 255, 100)
                else:
                    turn_indicator = "  "
                    indicator_color = name_color
            else:
                turn_indicator = "  "
                indicator_color = name_color

            console.print(3, y, turn_indicator, fg=indicator_color)

            # 이름 표시
            name_str = f"{i+1}. {ally.name}"
            console.print(5, y, name_str, fg=name_color)
            
            # 기계공학자: 이름 오른쪽에 열 표시
            gimmick_type = getattr(ally, 'gimmick_type', None)
            if gimmick_type == "heat_gauge" or gimmick_type == "heat_management":
                heat = getattr(ally, 'heat', 0)
                max_heat = getattr(ally, 'max_heat', 100)
                # 이름 오른쪽에 열 표시
                heat_text = f" 열:{heat}"
                name_end_x = 5 + len(name_str)
                console.print(name_end_x, y, heat_text, fg=(255, 150, 50))
            
            # 직업 및 기믹 상태 표시
            gimmick_result = self._get_gimmick_display(ally)
            if isinstance(gimmick_result, tuple):
                gimmick_text, gimmick_color = gimmick_result
            else:
                # 하위 호환성 (구버전 문자열)
                gimmick_text = gimmick_result
                gimmick_color = (150, 255, 200)
            if gimmick_text:
                # 기계공학자는 이미 열이 표시되었으므로 건너뛰기
                if gimmick_type != "heat_gauge" and gimmick_type != "heat_management":
                    console.print(5 + len(f"{i+1}. {ally.name}") + 2, y, gimmick_text, fg=gimmick_color)

            # HP 게이지 (정밀)
            console.print(8, y + 1, "HP:", fg=(200, 200, 200))
            gauge_renderer.render_bar(
                console, 12, y + 1, 15,
                ally.current_hp, ally.max_hp, show_numbers=True
            )

            # MP 게이지 (파란색)
            console.print(28, y + 2, "MP:", fg=(200, 200, 200))
            # MP 게이지: 파란색 계열
            mp_ratio = ally.current_mp / max(1, ally.max_mp)
            if mp_ratio > 0.6:
                mp_fg = (100, 150, 255)  # 밝은 파랑
                mp_bg = (50, 75, 150)
            elif mp_ratio > 0.3:
                mp_fg = (80, 120, 200)  # 중간 파랑
                mp_bg = (40, 60, 100)
            else:
                mp_fg = (60, 90, 150)  # 어두운 파랑
                mp_bg = (30, 45, 75)
            console.draw_rect(32, y + 2, 10, 1, ord(" "), bg=mp_bg)
            filled_mp = int(mp_ratio * 10)
            if filled_mp > 0:
                console.draw_rect(32, y + 2, filled_mp, 1, ord(" "), bg=mp_fg)
            mp_text = f"{ally.current_mp}/{ally.max_mp}"
            console.print(32 + (10 - len(mp_text)) // 2, y + 2, mp_text, fg=(255, 255, 255))

            # BRV 게이지 (노란색)
            max_brv = getattr(ally, 'max_brv', 999)
            console.print(8, y + 2, "BRV:", fg=(200, 200, 200))
            # BRV 게이지: 노란색 계열
            brv_ratio = ally.current_brv / max(1, max_brv)
            if brv_ratio > 0.8:
                brv_fg = (255, 220, 100)  # 황금색
                brv_bg = (150, 130, 50)
            elif brv_ratio > 0.5:
                brv_fg = (255, 200, 80)  # 밝은 노랑
                brv_bg = (120, 100, 40)
            elif brv_ratio > 0.2:
                brv_fg = (200, 160, 60)  # 중간 노랑
                brv_bg = (100, 80, 30)
            else:
                brv_fg = (150, 120, 40)  # 어두운 노랑
                brv_bg = (75, 60, 20)
            console.draw_rect(13, y + 2, 10, 1, ord(" "), bg=brv_bg)
            filled_brv = int(brv_ratio * 10)
            if filled_brv > 0:
                console.draw_rect(13, y + 2, filled_brv, 1, ord(" "), bg=brv_fg)
            brv_text = f"{int(ally.current_brv)}/{int(max_brv)}"
            console.print(13 + (10 - len(brv_text)) // 2, y + 2, brv_text, fg=(255, 255, 255))

            # ATB 게이지 (캐스팅 진행도 포함)
            gauge = self.combat_manager.atb.get_gauge(ally)
            atb_value = gauge.current if gauge else 0

            # 캐스팅 정보 확인
            cast_info = casting_system.get_cast_info(ally)
            is_casting = cast_info is not None
            cast_progress = cast_info.progress if cast_info else 0.0

            # 상태이상/버프/디버프 아이콘 (ATB 게이지 바로 위, 최대 3줄)
            status_effects = getattr(ally, 'status_effects', [])
            active_buffs = getattr(ally, 'active_buffs', {})
            # status_manager에서 상태이상 가져오기
            if hasattr(ally, 'status_manager'):
                status_effects = ally.status_manager.status_effects
            
            if status_effects or active_buffs:
                status_lines = gauge_renderer.render_status_icons(status_effects, buffs=active_buffs)
                if isinstance(status_lines, list):
                    # 여러 줄 렌더링 (최대 3줄)
                    for line_idx, (line_text, line_color) in enumerate(status_lines[:3]):
                        if line_text:
                            console.print(28, y - 1 + line_idx, line_text, fg=line_color)
                elif isinstance(status_lines, tuple):
                    # 하위 호환성 (구버전 튜플)
                    status_text, status_colors = status_lines
                    if status_text:
                        console.print(28, y, status_text, fg=status_colors[0] if status_colors else (200, 200, 255))
                else:
                    # 하위 호환성 (구버전 문자열)
                    if status_lines:
                        console.print(28, y, status_lines, fg=(200, 200, 255))
            
            console.print(28, y + 1, "ATB:", fg=(200, 200, 200))
            gauge_renderer.render_atb_with_cast(
                console, 33, y + 1, 15,
                atb_current=atb_value,
                atb_threshold=1000,
                atb_maximum=2000,
                cast_progress=cast_progress,
                is_casting=is_casting
            )

            # 상처 표시
            wound_damage = getattr(ally, 'wound_damage', 0)
            if wound_damage > 0:
                gauge_renderer.render_wound_indicator(console, 33, y + 2, wound_damage)

            # BREAK 상태 표시 (캐스팅보다 우선)
            if self.combat_manager.brave.is_broken(ally):
                console.print(8, y + 3, "💔 BREAK!", fg=(255, 50, 50))
            
            # 캐스팅 중이면 스킬 이름 표시 (BREAK가 없을 때만)
            elif cast_info:
                skill_name = getattr(cast_info.skill, 'name', 'Unknown')
                console.print(8, y + 3, f"⏳ 시전: {skill_name}", fg=(200, 100, 255))

    def _render_enemies(self, console: tcod.console.Console):
        """적군 상태 렌더링 (상세)"""
        console.print(self.screen_width - 30, 4, "[적군]", fg=(255, 100, 100))

        for i, enemy in enumerate(self.combat_manager.enemies):
            y = 6 + i * 6
            x = self.screen_width - 30

            # 이름 색상: 보스는 빨간색, 일반 적은 흰색
            is_boss = hasattr(enemy, 'enemy_id') and enemy.enemy_id.startswith("boss_") if hasattr(enemy, 'enemy_id') else False
            if not enemy.is_alive:
                name_color = (100, 100, 100)
            elif is_boss:
                name_color = (255, 0, 0)  # 보스: 선명한 빨간색
            else:
                name_color = (255, 255, 255)  # 일반 적: 흰색

            # 대상 선택 커서 또는 턴 표시
            if enemy == self.current_actor:
                # 현재 행동 중인 적
                cursor = " "
                cursor_color = (255, 100, 100)
            elif self.state == CombatUIState.TARGET_SELECT:
                # 타겟 선택 중 - 적이 타겟 리스트에 있는지 확인
                is_targeted = enemy in self.current_target_list

                # 광역 스킬 확인
                is_aoe = self.selected_skill and getattr(self.selected_skill, 'is_aoe', False)

                if is_aoe and is_targeted and enemy.is_alive:
                    # 광역 스킬 - 모든 살아있는 타겟에 화살표
                    cursor = "◆ "
                    cursor_color = (255, 100, 255)
                elif is_targeted and i == self.target_cursor:
                    # 단일 타겟 - 선택된 대상에만 화살표
                    cursor = "▶ "
                    cursor_color = (255, 255, 100)
                else:
                    cursor = "  "
                    cursor_color = name_color
            else:
                cursor = "  "
                cursor_color = name_color

            console.print(x, y, cursor, fg=cursor_color)
            console.print(x + 2, y, f"{chr(65+i)}. {enemy.name}", fg=name_color)

            # 기믹 상태 표시 (룬 스택 등)
            gimmick_result = self._get_gimmick_display(enemy)
            if isinstance(gimmick_result, tuple):
                gimmick_text, gimmick_color = gimmick_result
            else:
                # 하위 호환성 (구버전 문자열)
                gimmick_text = gimmick_result
                gimmick_color = (150, 255, 200)
            if gimmick_text:
                console.print(x + 2 + len(f"{chr(65+i)}. {enemy.name}") + 1, y, gimmick_text, fg=gimmick_color)

            # 상태이상/버프/디버프 (HP 게이지 바로 위, 최대 3줄)
            status_effects = getattr(enemy, 'status_effects', [])
            active_buffs = getattr(enemy, 'active_buffs', {})
            # status_manager에서 상태이상 가져오기
            if hasattr(enemy, 'status_manager'):
                status_effects = enemy.status_manager.status_effects
            
            if status_effects or active_buffs:
                status_lines = gauge_renderer.render_status_icons(status_effects, buffs=active_buffs)
                if isinstance(status_lines, list):
                    # 여러 줄 렌더링 (최대 2줄)
                    for line_idx, (line_text, line_color) in enumerate(status_lines[:2]):
                        if line_text:
                            console.print(x + 3, y + 1 + line_idx, line_text, fg=line_color)
                elif isinstance(status_lines, tuple):
                    # 하위 호환성 (구버전 튜플)
                    status_text, status_colors = status_lines
                    if status_text:
                        console.print(x + 3, y + 1, status_text, fg=status_colors[0] if status_colors else (200, 200, 255))
                else:
                    # 하위 호환성 (구버전 문자열)
                    if status_lines:
                        console.print(x + 3, y + 1, status_lines, fg=(200, 200, 200))
            
            # HP 게이지
            console.print(x + 3, y + 2, "HP:", fg=(200, 200, 200))
            gauge_renderer.render_bar(
                console, x + 7, y + 2, 12,
                enemy.current_hp, enemy.max_hp, show_numbers=True
            )

            # BRV 게이지
            max_brv = getattr(enemy, 'max_brv', 9999)
            console.print(x + 3, y + 3, "BRV:", fg=(200, 200, 200))
            gauge_renderer.render_bar(
                console, x + 8, y + 3, 10,
                enemy.current_brv, max_brv, show_numbers=True, color_gradient=False
            )

            # BREAK 상태 표시
            if self.combat_manager.brave.is_broken(enemy):
                console.print(x + 3, y + 4, "💔 BREAK!", fg=(255, 50, 50))

            # 캐스팅 표시
            cast_info = casting_system.get_cast_info(enemy)
            if cast_info:
                skill_name = getattr(cast_info.skill, 'name', 'Unknown')
                gauge_renderer.render_casting_bar(
                    console, x + 3, y + 5, 15,
                    cast_info.progress, skill_name=f"시전:{skill_name[:8]}"
                )

    def _render_messages(self, console: tcod.console.Console):
        """메시지 로그 렌더링 (오른쪽에 배치, 스크롤 형식)"""
        # 커맨드 창(action_menu)과 같은 높이: y=33
        msg_y = 33
        
        # 오른쪽에 배치: action_menu가 x=5, width=35이므로 x=42부터 시작
        msg_x = 42
        msg_width = self.screen_width - msg_x - 3  # 오른쪽 여백 3 (스크롤 인디케이터 공간)
        
        # 구분선과 로그 제목
        separator = "─" * (msg_width - 12)  # "[전투 로그]" 공간 확보
        console.print(msg_x, msg_y - 1, "[전투 로그]" + separator, fg=(150, 150, 150))
        
        # 메시지 목록 (오래된 것부터 정렬)
        total_messages = len(self.messages)
        
        # 스크롤 가능한 범위 계산
        max_scroll = max(0, total_messages - self.log_visible_lines)
        
        # 스크롤 오프셋이 범위를 벗어나지 않도록 조정
        if self.log_scroll_offset > max_scroll:
            self.log_scroll_offset = max_scroll
        if self.log_scroll_offset < 0:
            self.log_scroll_offset = 0
        
        # 표시할 메시지 범위 계산 (하단에서 위로 스크롤)
        # offset=0이면 최신 메시지들, offset이 커질수록 오래된 메시지들
        start_idx = max(0, total_messages - self.log_visible_lines - self.log_scroll_offset)
        end_idx = total_messages - self.log_scroll_offset
        
        # 메시지 표시 (오래된 것부터 위로)
        display_messages = self.messages[start_idx:end_idx]
        for i, msg in enumerate(display_messages):
            if i >= self.log_visible_lines:
                break
            
            # 텍스트가 너무 길면 잘라내기
            display_text = msg.text[:msg_width] if len(msg.text) > msg_width else msg.text
            console.print(msg_x, msg_y + i, display_text, fg=msg.color)
        
        # 스크롤 가능 여부 표시
        if total_messages > self.log_visible_lines:
            # 아래로 스크롤 가능 (오래된 메시지 더 보기)
            if self.log_scroll_offset < max_scroll:
                console.print(msg_x + msg_width, msg_y + self.log_visible_lines - 1, "▼", fg=(150, 150, 150))
            # 위로 스크롤 가능 (최신 메시지 보기)
            if self.log_scroll_offset > 0:
                console.print(msg_x + msg_width, msg_y, "▲", fg=(150, 150, 150))

    def _render_target_select(self, console: tcod.console.Console):
        """대상 선택 UI 렌더링"""
        console.print(
            self.screen_width // 2 - 10,
            35,
            "대상을 선택하세요 (↑↓ 또는 ←→)",
            fg=(255, 255, 100)
        )

        console.print(
            self.screen_width // 2 - 8,
            36,
            "Z: 확정  X: 취소",
            fg=(180, 180, 180)
        )

    def _get_gimmick_display(self, character: Any) -> Tuple[str, Tuple[int, int, int]]:
        """캐릭터의 기믹 상태를 (텍스트, 색상) 튜플로 반환"""
        # 적에게 새겨진 룬 표시 (배틀메이지의 룬 새기기)
        if hasattr(character, 'carved_runes') and character.carved_runes:
            rune_display = []
            rune_colors = {"fire": (255, 100, 50), "ice": (100, 200, 255), "lightning": (255, 255, 100), 
                          "earth": (139, 69, 19), "arcane": (200, 100, 255)}
            rune_names = {"fire": "화", "ice": "냉", "lightning": "번", "earth": "대", "arcane": "비"}
            colored_parts = []
            for rune_type, count in character.carved_runes.items():
                if count > 0:
                    name = rune_names.get(rune_type, rune_type[0].upper())
                    colored_parts.append((f"{name}{count}", rune_colors.get(rune_type, (255, 255, 255))))
            if colored_parts:
                # 평균 색상 계산
                avg_color = tuple(sum(c[i] for _, c in colored_parts) // len(colored_parts) for i in range(3))
                text = f"룬: {', '.join(t for t, _ in colored_parts)}"
                return (text, avg_color)
        
        gimmick_type = getattr(character, 'gimmick_type', None)
        if not gimmick_type:
            return ("", (255, 255, 255))

        # 기믹 타입별 상태 표시 (컬러풀하게, 대괄호 제거)
        if gimmick_type == "stance_system":
            # 전사 - 스탠스
            stance = getattr(character, 'current_stance', 0)
            # 문자열인 경우 정수로 변환
            if isinstance(stance, str):
                stance_id_to_index = {
                    "balanced": 0,
                    "attack": 1,
                    "defense": 2,
                    "berserker": 4,
                    "guardian": 5,
                    "speed": 6
                }
                stance = stance_id_to_index.get(stance, 0)
            # 스탠스 인덱스를 배열 인덱스로 매핑 (0,1,2,4,5,6 -> 0,1,2,3,4,5)
            stance_to_array_index = {
                0: 0,  # balanced -> 중립
                1: 1,  # attack -> 공격
                2: 2,  # defense -> 방어
                4: 3,  # berserker -> 광전사
                5: 4,  # guardian -> 수호자
                6: 5   # speed -> 신속
            }
            stance_names = ["중립", "공격", "방어", "광전사", "수호자", "신속"]
            stance_colors = [(200, 200, 200), (255, 100, 100), (100, 150, 255), (255, 50, 50), (100, 200, 255), (255, 255, 100)]
            if isinstance(stance, int):
                array_index = stance_to_array_index.get(stance, 0)
                if 0 <= array_index < len(stance_names):
                    return (stance_names[array_index], stance_colors[array_index])

        elif gimmick_type == "elemental_counter":
            # 아크메이지 - 원소 카운터
            fire = getattr(character, 'fire_element', 0)
            ice = getattr(character, 'ice_element', 0)
            lightning = getattr(character, 'lightning_element', 0)
            # 평균 색상 (화염: 빨강, 냉기: 파랑, 번개: 노랑)
            avg_color = (150, 150, 100) if (fire + ice + lightning) > 0 else (255, 255, 255)
            return (f"화염{fire} 냉기{ice} 번개{lightning}", avg_color)

        elif gimmick_type == "support_fire_system" or gimmick_type == "support_fire":
            # 궁수 - 지원사격
            combo = getattr(character, 'support_fire_combo', 0)

            # 실제로 마킹된 아군 수 계산
            marked = 0
            if hasattr(self, 'combat_manager') and hasattr(self.combat_manager, 'allies'):
                for ally in self.combat_manager.allies:
                    if ally == character:  # 자기 자신은 제외
                        continue
                    # 7가지 화살 타입 중 하나라도 마킹되어 있으면 카운트
                    has_mark = any([
                        getattr(ally, 'mark_slot_normal', 0) > 0,
                        getattr(ally, 'mark_slot_piercing', 0) > 0,
                        getattr(ally, 'mark_slot_fire', 0) > 0,
                        getattr(ally, 'mark_slot_ice', 0) > 0,
                        getattr(ally, 'mark_slot_poison', 0) > 0,
                        getattr(ally, 'mark_slot_explosive', 0) > 0,
                        getattr(ally, 'mark_slot_holy', 0) > 0,
                    ])
                    if has_mark:
                        marked += 1

            return (f"지원:{marked}/3 콤보:{combo}", (255, 200, 100))

        elif gimmick_type == "magazine_system":
            # 저격수 - 탄창
            magazine = getattr(character, 'magazine', [])
            return (f"탄창:{len(magazine)}/6", (150, 150, 200))

        elif gimmick_type == "venom_system":
            # 도적 - 베놈
            venom = getattr(character, 'venom_power', 0)
            return (f"독:{venom}", (100, 255, 100))

        elif gimmick_type == "shadow_system":
            # 암살자 - 그림자
            shadows = getattr(character, 'shadow_count', 0)
            max_shadows = getattr(character, 'max_shadow_count', 5)
            return (f"그림자:{shadows}/{max_shadows}", (100, 50, 150))

        elif gimmick_type == "sword_aura":
            # 검성 - 검기
            aura = getattr(character, 'sword_aura', 0)
            max_aura = getattr(character, 'max_sword_aura', 5)
            return (f"검기:{aura}/{max_aura}", (255, 255, 150))

        elif gimmick_type == "rage_system":
            # 광전사 - 분노
            rage = getattr(character, 'rage_stacks', 0)
            max_rage = getattr(character, 'max_rage_stacks', 10)
            return (f"분노:{rage}/{max_rage}", (255, 50, 50))

        elif gimmick_type == "ki_system":
            # 몽크 - 기
            ki = getattr(character, 'ki_energy', 0)
            max_ki = getattr(character, 'max_ki_energy', 100)
            return (f"기:{ki}/{max_ki}", (255, 215, 0))

        elif gimmick_type == "melody_system":
            # 바드 - 멜로디
            melody = getattr(character, 'melody_stacks', 0)
            max_melody = getattr(character, 'max_melody_stacks', 7)
            return (f"♪:{melody}/{max_melody}", (255, 150, 255))

        elif gimmick_type == "necro_system":
            # 네크로맨서 - 네크로 에너지
            necro = getattr(character, 'necro_energy', 0)
            max_necro = getattr(character, 'max_necro_energy', 50)
            return (f"사령:{necro}/{max_necro}", (150, 0, 150))

        elif gimmick_type == "curse_system" or gimmick_type == "totem_system":
            # 무당 - 저주 (하위 호환성을 위해 totem_system도 지원)
            curses = getattr(character, 'curse_stacks', 0)
            max_curses = getattr(character, 'max_curse_stacks', 10)
            return (f"저주:{curses}/{max_curses}", (150, 100, 0))

        elif gimmick_type == "wisdom_system":
            # 철학자 - 지혜
            knowledge = getattr(character, 'knowledge_stacks', 0)
            max_knowledge = getattr(character, 'max_knowledge_stacks', 10)
            return (f"지혜:{knowledge}/{max_knowledge}", (200, 150, 255))

        elif gimmick_type == "time_system":
            # 시간술사 - 시간 기록점
            time = getattr(character, 'time_marks', 0)
            max_time = getattr(character, 'max_time_marks', 7)
            return (f"시간:{time}/{max_time}", (200, 255, 255))

        elif gimmick_type == "alchemy_system":
            # 연금술사 - 물약
            potions = getattr(character, 'potion_stock', 0)
            max_potions = getattr(character, 'max_potion_stock', 10)
            return (f"물약:{potions}/{max_potions}", (100, 200, 100))

        elif gimmick_type == "blood_system":
            # 흡혈귀 - 혈액
            blood = getattr(character, 'blood_pool', 0)
            max_blood = getattr(character, 'max_blood_pool', 100)
            return (f"혈액:{blood}/{max_blood}", (200, 0, 0))

        elif gimmick_type == "hack_system":
            # 해커 - 해킹
            hacks = getattr(character, 'hack_stacks', 0)
            max_hacks = getattr(character, 'max_hack_stacks', 5)
            return (f"해킹:{hacks}/{max_hacks}", (0, 200, 200))

        elif gimmick_type == "darkness_system":
            # 암흑기사 - 어둠
            darkness = getattr(character, 'darkness', 0)
            return (f"어둠:{darkness}", (50, 50, 100))

        elif gimmick_type == "holy_system":
            # 성기사/신관 - 신성력
            holy = getattr(character, 'holy_power', 0)
            max_holy = getattr(character, 'max_holy_power', 100)
            return (f"신성:{holy}/{max_holy}", (255, 255, 200))

        elif gimmick_type == "rune_system":
            # 전투마법사 - 룬
            runes = getattr(character, 'rune_stacks', 0)
            max_runes = getattr(character, 'max_rune_stacks', 8)
            return (f"룬:{runes}/{max_runes}", (200, 100, 255))

        elif gimmick_type == "dimension_system":
            # 차원술사 - 차원력
            dimension = getattr(character, 'dimension_points', 0)
            max_dimension = getattr(character, 'max_dimension_points', 100)
            return (f"차원:{dimension}/{max_dimension}", (150, 150, 255))

        elif gimmick_type == "construct_system":
            # 기계공학자 - 부품
            parts = getattr(character, 'machine_parts', 0)
            max_parts = getattr(character, 'max_machine_parts', 5)
            return (f"부품:{parts}/{max_parts}", (255, 150, 50))

        elif gimmick_type == "duty_system":
            # 기사 - 의무
            duty = getattr(character, 'duty_stacks', 0)
            max_duty = getattr(character, 'max_duty_stacks', 10)
            return (f"의무:{duty}/{max_duty}", (200, 200, 255))

        elif gimmick_type == "stealth_system":
            # 암살자 - 은신
            stealth = getattr(character, 'stealth_points', 0)
            max_stealth = getattr(character, 'max_stealth_points', 5)
            return (f"은신:{stealth}/{max_stealth}", (100, 100, 150))

        elif gimmick_type == "theft_system":
            # 도적 - 절도
            stolen = getattr(character, 'stolen_items', 0)
            return (f"절도:{stolen}", (150, 200, 150))

        elif gimmick_type == "plunder_system":
            # 해적 - 약탈
            gold = getattr(character, 'gold', 0)
            return (f"골드:{gold}", (255, 215, 0))

        elif gimmick_type == "iaijutsu_system":
            # 사무라이 - 거합
            will = getattr(character, 'will_gauge', 0)
            max_will = getattr(character, 'max_will_gauge', 10)
            return (f"기합:{will}/{max_will}", (255, 100, 150))

        elif gimmick_type == "enchant_system":
            # 마검사 - 마력 부여
            mana = getattr(character, 'mana_blade', 0)
            max_mana = getattr(character, 'max_mana_blade', 100)
            return (f"마검:{mana}/{max_mana}", (100, 150, 255))

        elif gimmick_type == "divinity_system":
            # 프리스트/클레릭 - 신성력
            judgment = getattr(character, 'judgment_points', 0)
            faith = getattr(character, 'faith_points', 0)
            return (f"심판:{judgment} 신앙:{faith}", (255, 255, 150))

        elif gimmick_type == "shapeshifting_system":
            # 드루이드 - 변신
            nature = getattr(character, 'nature_points', 0)
            form = getattr(character, 'current_form', None)
            if form:
                form_names = {
                    "bear": "곰",
                    "cat": "표범",
                    "panther": "표범",
                    "eagle": "독수리",
                    "wolf": "늑대",
                    "primal": "진변신",
                    "elemental": "원소"
                }
                form_name = form_names.get(form, form)
                return (f"{form_name}형태 {nature}", (139, 69, 19))
            return (f"자연:{nature}", (139, 69, 19))

        elif gimmick_type == "spirit_bond":
            # 정령술사 - 정령 친화도
            bond = getattr(character, 'spirit_bond', 0)
            max_bond = getattr(character, 'max_spirit_bond', 25)
            spirits = getattr(character, 'spirit_count', 0)
            return (f"친화:{bond}/{max_bond} 정령:{spirits}", (150, 255, 200))

        elif gimmick_type == "dragon_marks":
            # 용기사 - 용의 표식
            marks = getattr(character, 'dragon_marks', 0)
            max_marks = getattr(character, 'max_dragon_marks', 3)
            power = getattr(character, 'dragon_power', 0)
            return (f"용표:{marks}/{max_marks} 용력:{power}", (255, 100, 100))

        elif gimmick_type == "arena_system":
            # 검투사 - 투기장
            arena = getattr(character, 'arena_points', 0)
            glory = getattr(character, 'glory_points', 0)
            kills = getattr(character, 'kill_count', 0)
            return (f"투기:{arena} 영광:{glory} 처치:{kills}", (255, 200, 100))

        elif gimmick_type == "break_system":
            # 브레이커 - 파괴력
            break_power = getattr(character, 'break_power', 0)
            max_break = getattr(character, 'max_break_power', 10)
            return (f"파괴:{break_power}/{max_break}", (200, 100, 100))

        # === 15개 신규 기믹 시스템 (간략 표시) ===

        elif gimmick_type == "yin_yang_flow":
            # 몽크 - 음양 흐름 (간략: 게이지만)
            ki = getattr(character, 'ki_gauge', 50)
            return (f"기:{ki}", (255, 215, 0))

        elif gimmick_type == "rune_resonance":
            # 배틀메이지 - 룬 공명 (간략: 총합)
            fire = getattr(character, 'rune_fire', 0)
            ice = getattr(character, 'rune_ice', 0)
            lightning = getattr(character, 'rune_lightning', 0)
            earth = getattr(character, 'rune_earth', 0)
            arcane = getattr(character, 'rune_arcane', 0)
            total = fire + ice + lightning + earth + arcane
            return (f"룬:{total}", (200, 100, 255))

        elif gimmick_type == "probability_distortion":
            # 차원술사 - 확률 왜곡 (간략: 게이지)
            gauge = getattr(character, 'distortion_gauge', 0)
            return (f"왜곡:{gauge}", (150, 150, 255))

        elif gimmick_type == "heat_gauge":
            # 엔지니어 - 열 게이지 (간략: 상태) - 이미 이름 옆에 표시됨
            heat = getattr(character, 'heat', 0)
            return ("", (255, 255, 255))  # 빈 문자열 반환 (이미 이름 옆에 표시됨)

        elif gimmick_type == "thirst_gauge":
            # 뱀파이어 - 갈증 (간략: 게이지)
            thirst = getattr(character, 'thirst', 0)
            return (f"갈증:{thirst}", (200, 0, 0))

        elif gimmick_type == "madness_gauge":
            # 버서커 - 광기 (간략: 게이지)
            madness = getattr(character, 'madness', 0)
            return (f"광기:{madness}", (200, 50, 50))

        elif gimmick_type == "madness_threshold":
            # 광전사 - 광기 임계치
            madness = getattr(character, 'madness', 0)
            max_madness = getattr(character, 'max_madness', 100)
            optimal_min = getattr(character, 'optimal_min', 30)
            optimal_max = getattr(character, 'optimal_max', 70)
            danger_min = getattr(character, 'danger_min', 71)
            
            # 위험 구간 표시
            if madness >= danger_min:
                return (f"위험광기:{madness}/{max_madness}", (255, 50, 50))
            elif madness >= optimal_min:
                return (f"최적광기:{madness}/{max_madness}", (255, 200, 100))
            else:
                return (f"광기:{madness}/{max_madness}", (200, 50, 50))

        elif gimmick_type == "spirit_resonance":
            # 정령술사 - 정령 (간략: 활성 정령 수)
            fire = getattr(character, 'spirit_fire', 0)
            water = getattr(character, 'spirit_water', 0)
            wind = getattr(character, 'spirit_wind', 0)
            earth = getattr(character, 'spirit_earth', 0)
            active = sum([1 for s in [fire, water, wind, earth] if s > 0])
            return (f"정령:{active}", (150, 255, 200))

        elif gimmick_type == "stealth_mastery":
            # 암살자 - 은신 (간략: 상태만)
            stealth_active = getattr(character, 'stealth_active', False)
            if stealth_active:
                return ("은신", (100, 100, 150))
            else:
                return ("노출", (255, 150, 150))

        elif gimmick_type == "dilemma_choice":
            # 철학자 - 선택 (간략: 총 선택 수)
            power = getattr(character, 'choice_power', 0)
            wisdom = getattr(character, 'choice_wisdom', 0)
            sacrifice = getattr(character, 'choice_sacrifice', 0)
            truth = getattr(character, 'choice_truth', 0)
            total = power + wisdom + sacrifice + truth
            return (f"선택:{total}", (200, 150, 255))

        elif gimmick_type == "support_fire":
            # 궁수 - 지원사격 (간략: 콤보)
            combo = getattr(character, 'support_fire_combo', 0)
            return (f"지원:{combo}", (255, 200, 100))

        elif gimmick_type == "hack_threading":
            # 해커 - 스레드 (간략: 스레드 수)
            threads = getattr(character, 'active_threads', 0)
            return (f"스레드:{threads}", (0, 200, 200))

        elif gimmick_type == "multithread_system":
            # 해커 - 멀티스레드 시스템
            # 실제 활성 프로그램 수 계산
            program_fields = ['program_virus', 'program_backdoor', 'program_ddos', 'program_ransomware', 'program_spyware']
            active_programs = sum(1 for field in program_fields if getattr(character, field, 0) > 0)
            virus = getattr(character, 'program_virus', 0)
            backdoor = getattr(character, 'program_backdoor', 0)
            ddos = getattr(character, 'program_ddos', 0)
            ransomware = getattr(character, 'program_ransomware', 0)
            spyware = getattr(character, 'program_spyware', 0)
            total = virus + backdoor + ddos + ransomware + spyware
            return (f"프로그램:{total}", (0, 200, 200))

        elif gimmick_type == "cheer_gauge":
            # 검투사 - 환호 (간략: 게이지)
            cheer = getattr(character, 'cheer', 0)
            if cheer > 70:
                return (f"열광:{cheer}", (255, 200, 100))
            else:
                return (f"환호:{cheer}", (255, 200, 100))

        elif gimmick_type == "crowd_cheer":
            # 검투사 - 군중의 환호
            cheer = getattr(character, 'cheer', 0)
            max_cheer = getattr(character, 'max_cheer', 100)
            return (f"환호:{cheer}/{max_cheer}", (255, 200, 100))

        elif gimmick_type == "timeline_system":
            # 시간술사 - 타임라인
            timeline = getattr(character, 'timeline', 0)
            min_timeline = getattr(character, 'min_timeline', -5)
            max_timeline = getattr(character, 'max_timeline', 5)
            if timeline < 0:
                return (f"과거:{timeline}", (200, 200, 255))
            elif timeline > 0:
                return (f"미래:{timeline}", (255, 200, 255))
            else:
                return (f"현재:{timeline}", (200, 255, 255))

        elif gimmick_type == "undead_legion":
            # 네크로맨서 - 언데드 군단
            skeleton = getattr(character, 'undead_skeleton', 0)
            zombie = getattr(character, 'undead_zombie', 0)
            ghost = getattr(character, 'undead_ghost', 0)
            total = skeleton + zombie + ghost
            max_undead = getattr(character, 'max_undead_total', 5)
            return (f"언데드:{total}/{max_undead}", (150, 0, 150))

        elif gimmick_type == "stealth_exposure":
            # 암살자 - 은신-노출
            stealth = getattr(character, 'stealth_points', 0)
            max_stealth = getattr(character, 'max_stealth_points', 5)
            exposed = getattr(character, 'exposed', False)
            if exposed:
                return (f"노출:{stealth}/{max_stealth}", (255, 150, 150))
            else:
                return (f"은신:{stealth}/{max_stealth}", (100, 100, 150))

        return ("", (255, 255, 255))

    def _render_gimmick_view(self, console: tcod.console.Console):
        """기믹 상세 보기 렌더링 (박스 스타일)"""
        if not self.gimmick_view_character:
            return

        character = self.gimmick_view_character
        gimmick_type = getattr(character, 'gimmick_type', None)

        # 박스 위치 및 크기
        box_width = 50
        # 기믹 타입에 따라 높이 조정
        if gimmick_type == "dilemma_choice":
            # 철학자 - 딜레마 선택: 더 많은 공간 필요 (제목 + 구분선 + 4가지 선택 + 구분선 + 경향 + 하단 안내)
            box_height = 28
        elif gimmick_type == "rune_resonance":
            # 배틀메이지의 경우 룬 5개 + 공명 정보를 위해 높이 증가
            box_height = 22
        else:
            box_height = 22
        box_x = (self.screen_width - box_width) // 2
        box_y = (self.screen_height - box_height) // 2

        # 배경 (어두운 반투명)
        for y in range(box_y, box_y + box_height):
            console.draw_rect(box_x, y, box_width, 1, ord(" "), bg=(20, 20, 40))

        # 박스 테두리
        # 상단
        console.print(box_x, box_y, "┌" + "─" * (box_width - 2) + "┐", fg=(200, 200, 255))
        # 하단
        console.print(box_x, box_y + box_height - 1, "└" + "─" * (box_width - 2) + "┘", fg=(200, 200, 255))
        # 좌우
        for y in range(box_y + 1, box_y + box_height - 1):
            console.print(box_x, y, "│", fg=(200, 200, 255))
            console.print(box_x + box_width - 1, y, "│", fg=(200, 200, 255))

        # 내용 시작 위치
        content_x = box_x + 2
        content_y = box_y + 1
        line = 0

        # 기믹 타입에 따라 다른 UI 표시
        if not gimmick_type:
            console.print(content_x, content_y + line, "기믹 시스템 없음", fg=(150, 150, 150))
            console.print(content_x, box_y + box_height - 2, "아무 키나 눌러 닫기...", fg=(150, 150, 150))
            return

        # === 15개 신규 기믹 시스템 상세 ===

        if gimmick_type == "heat_gauge":
            # 기계공학자 - 열 게이지
            heat = getattr(character, 'heat', 0)
            max_heat = getattr(character, 'max_heat', 100)

            # 제목
            console.print(content_x, content_y + line, "🔧 기계공학자 - 열 게이지", fg=(255, 200, 100))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 게이지 바
            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, heat, max_heat, show_numbers=True, custom_color=(255, 100, 50))
            line += 1

            # 구간 표시
            console.print(content_x, content_y + line, " 냉각   최적   위험   오버히트", fg=(150, 150, 150))
            line += 1
            # 현재 위치 표시
            if heat < 50:
                indicator_pos = int((heat / 50) * 6)
                console.print(content_x + indicator_pos, content_y + line, "↑현재", fg=(100, 255, 255))
            elif heat < 80:
                indicator_pos = 6 + int(((heat - 50) / 30) * 6)
                console.print(content_x + indicator_pos, content_y + line, "↑현재", fg=(100, 255, 100))
            elif heat < 100:
                indicator_pos = 12 + int(((heat - 80) / 20) * 6)
                console.print(content_x + indicator_pos, content_y + line, "↑현재", fg=(255, 255, 100))
            else:
                console.print(content_x + 18, content_y + line, "↑현재", fg=(255, 100, 100))
            line += 2

            # 구분선
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 상태 정보
            if heat >= 100:
                console.print(content_x, content_y + line, " 상태: 오버히트!", fg=(255, 50, 50))
                line += 1
                console.print(content_x, content_y + line, "[경고] 스턴 2턴, 열 0으로 리셋", fg=(255, 100, 100))
            elif heat >= 80:
                console.print(content_x, content_y + line, "[위험] 열 상태: 위험 구간", fg=(255, 200, 100))
                line += 1
                console.print(content_x, content_y + line, "[효과] 공격력 +50%, 크리티컬 +15%", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, "[경고] 받는 피해 +20%, 명중률 -10%", fg=(255, 150, 100))
            elif heat >= 50:
                console.print(content_x, content_y + line, "[최적] 열 상태: 최적 구간", fg=(100, 255, 100))
                line += 1
                console.print(content_x, content_y + line, "[효과] 공격력 +30%, 스킬 효과 +20%", fg=(255, 255, 100))
            else:
                console.print(content_x, content_y + line, "  열 상태: 냉각 구간", fg=(150, 150, 255))
                line += 1
                console.print(content_x, content_y + line, "[효과] 일반 공격력", fg=(200, 200, 200))
            line += 1

            # 다음 턴 예측
            next_heat = heat + (5 if heat >= 50 else 0)
            console.print(content_x, content_y + line, f" 다음 턴 자동 열 증가: +{5 if heat >= 50 else 0} (예상: {min(next_heat, 100)})", fg=(150, 200, 255))

        elif gimmick_type == "yin_yang_flow":
            # 몽크 - 음양 흐름
            ki = getattr(character, 'ki_gauge', 50)
            min_ki = getattr(character, 'min_ki', 0)
            max_ki = getattr(character, 'max_ki', 100)

            console.print(content_x, content_y + line, "🥋 몽크 - 음양 기 흐름", fg=(255, 215, 0))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 게이지 바 너비 계산
            gauge_width = box_width - 6
            gauge_start_x = content_x
            
            # 음양 게이지 위치 표시 (게이지 바 너비에 맞춰 중앙 정렬)
            yin_yang_text = "[陰]        [☯]        [陽]"
            text_start_x = gauge_start_x + (gauge_width - len(yin_yang_text)) // 2
            console.print(text_start_x, content_y + line, yin_yang_text, fg=(200, 200, 200))
            line += 1
            
            # 게이지 바 (음=파랑, 양=빨강, 균형=금색)
            if ki < 40:
                gauge_color = (100, 150, 255)  # 파랑 (음)
            elif ki <= 60:
                gauge_color = (255, 215, 0)  # 금색 (균형)
            else:
                gauge_color = (255, 100, 100)  # 빨강 (양)
            gauge_renderer.render_bar(console, gauge_start_x, content_y + line, gauge_width, ki, max_ki, show_numbers=True, custom_color=gauge_color)
            line += 1

            # 상태 정보
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if ki < 25:
                console.print(content_x, content_y + line, "🌟 상태: 음 (陰) 기운 특화", fg=(100, 150, 255))
                line += 1
                console.print(content_x, content_y + line, " 효과: 방어력 +50%, MP 회복 +100%", fg=(150, 200, 255))
                line += 1
                console.print(content_x, content_y + line, "   받는 피해 -30%", fg=(150, 200, 255))
            elif ki > 75:
                console.print(content_x, content_y + line, "🌟 상태: 양 (陽) 기운 특화", fg=(255, 100, 100))
                line += 1
                console.print(content_x, content_y + line, " 효과: 공격력 +40%, 속도 +30%", fg=(255, 200, 100))
                line += 1
                console.print(content_x, content_y + line, "   크리티컬 확률 +20%", fg=(255, 200, 100))
            else:
                console.print(content_x, content_y + line, "🌟 상태: 태극 조화 (균형)", fg=(255, 215, 0))
                line += 1
                console.print(content_x, content_y + line, " 효과: 모든 스탯 +20%", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, "   음양 스킬 강화 +30%", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, "   HP/MP 회복 매 턴 5%", fg=(255, 255, 100))

        elif gimmick_type == "rune_resonance":
            # 배틀메이지 - 룬 공명
            fire = getattr(character, 'rune_fire', 0)
            ice = getattr(character, 'rune_ice', 0)
            lightning = getattr(character, 'rune_lightning', 0)
            earth = getattr(character, 'rune_earth', 0)
            arcane = getattr(character, 'rune_arcane', 0)
            max_rune = getattr(character, 'max_rune_per_type', 3)

            console.print(content_x, content_y + line, "🔮 배틀메이지 - 룬 공명", fg=(200, 100, 255))
            line += 1
            console.print(box_x, content_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 룬 상태 (5가지 모두 표시)
            console.print(content_x, content_y + line, f" 화염 룬: {fire}/{max_rune}", fg=(255, 100, 50))
            line += 1
            console.print(content_x, content_y + line, f"  냉기 룬: {ice}/{max_rune}", fg=(100, 200, 255))
            line += 1
            console.print(content_x, content_y + line, f" 번개 룬: {lightning}/{max_rune}", fg=(255, 255, 100))
            line += 1
            console.print(content_x, content_y + line, f"🌍 대지 룬: {earth}/{max_rune}", fg=(139, 69, 19))
            line += 1
            console.print(content_x, content_y + line, f" 비전 룬: {arcane}/{max_rune}", fg=(200, 100, 255))
            line += 1

            console.print(box_x, content_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 공명 가능 패턴 체크
            resonances = []
            if fire >= 3:
                resonances.append("화염 폭발 (광역 화상)")
            if ice >= 3:
                resonances.append("빙하기 (전체 감속)")
            if lightning >= 3:
                resonances.append("연쇄 번개 (연쇄 공격)")
            if fire >= 2 and ice >= 2:
                resonances.append("증기 폭발 (화염+냉기)")
            if fire >= 1 and ice >= 1 and lightning >= 1:
                resonances.append("원소 융합 (3속성 피해)")

            if resonances:
                console.print(content_x, content_y + line, "🔍 공명 가능:", fg=(255, 255, 100))
                line += 1
                for res in resonances[:3]:  # 최대 3개만 표시
                    console.print(content_x + 2, content_y + line, f"• {res}", fg=(200, 255, 200))
                    line += 1
            else:
                console.print(content_x, content_y + line, " 룬 축적 필요", fg=(150, 150, 150))

        elif gimmick_type == "probability_distortion":
            # 차원술사 - 확률 왜곡
            gauge = getattr(character, 'distortion_gauge', 0)
            max_gauge = getattr(character, 'max_gauge', 100)

            console.print(content_x, content_y + line, "🌀 차원술사 - 확률 왜곡", fg=(200, 100, 255))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, gauge, max_gauge, show_numbers=True, custom_color=(150, 100, 255))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 사용 가능한 왜곡 표시
            console.print(content_x, content_y + line, " 사용 가능한 확률 왜곡:", fg=(255, 255, 100))
            line += 1
            if gauge >= 100:
                console.print(content_x + 2, content_y + line, "• 평행우주 (100) - 모든 상태 리셋", fg=(255, 100, 255))
                line += 1
            if gauge >= 50:
                console.print(content_x + 2, content_y + line, "• 시간 되감기 (50) - 실패 재시도", fg=(200, 200, 255))
                line += 1
            if gauge >= 30:
                console.print(content_x + 2, content_y + line, "• 회피 왜곡 (30) - 회피율 +80%", fg=(150, 255, 200))
                line += 1
            if gauge >= 20:
                console.print(content_x + 2, content_y + line, "• 크리티컬 왜곡 (20) - 크리 +50%", fg=(255, 255, 100))
                line += 1

        elif gimmick_type == "thirst_gauge":
            # 뱀파이어 - 갈증
            thirst = getattr(character, 'thirst', 0)
            max_thirst = getattr(character, 'max_thirst', 100)

            console.print(content_x, content_y + line, "🧛 흡혈귀 - 갈증 게이지", fg=(200, 50, 50))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_color = (200, 50, 50) if thirst > 70 else (150, 100, 100)
            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, thirst, max_thirst, show_numbers=True, custom_color=gauge_color)
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if thirst >= 96:
                console.print(content_x, content_y + line, "💧 상태: 혈액 광란 (극위험!)", fg=(255, 0, 0))
                line += 1
                console.print(content_x, content_y + line, " 공격력 +150%, 흡혈 5배, 속도 +100%", fg=(255, 200, 0))
                line += 1
                console.print(content_x, content_y + line, "  매 턴 HP 10% 감소, 받는 데미지 +50%", fg=(255, 50, 50))
            elif thirst >= 91:
                console.print(content_x, content_y + line, "💧 상태: 통제된 광란 (위험!)", fg=(255, 100, 50))
                line += 1
                console.print(content_x, content_y + line, " 공격력 +120%, 흡혈 4배, 속도 +80%", fg=(255, 200, 100))
                line += 1
                console.print(content_x, content_y + line, "  매 턴 HP 5% 감소, 받는 데미지 +30%", fg=(255, 150, 100))
            elif thirst > 60:
                console.print(content_x, content_y + line, "💧 상태: 극심한 갈증", fg=(255, 150, 150))
                line += 1
                console.print(content_x, content_y + line, " 공격력 +70%, 흡혈 3배, 속도 +50%", fg=(255, 200, 200))
            elif thirst > 30:
                console.print(content_x, content_y + line, "💧 상태: 갈증", fg=(200, 150, 150))
                line += 1
                console.print(content_x, content_y + line, " 공격력 +30%, 흡혈 2배", fg=(255, 255, 200))
            else:
                console.print(content_x, content_y + line, "💧 상태: 만족", fg=(150, 255, 150))
                line += 1
                console.print(content_x, content_y + line, " 정상 상태", fg=(200, 200, 200))
            line += 1
            thirst_per_turn = 5  # 기본값 (blood_control 특성에서 가져올 수 있음)
            console.print(content_x, content_y + line, f" 다음 턴 자동 증가: +{thirst_per_turn} (예상: {min(thirst + thirst_per_turn, max_thirst)})", fg=(150, 200, 255))

        elif gimmick_type == "madness_gauge":
            # 버서커 - 광기
            madness = getattr(character, 'madness', 0)
            max_madness = getattr(character, 'max_madness', 100)

            console.print(content_x, content_y + line, "😡 광전사 - 광기 게이지", fg=(255, 100, 100))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_color = (255, 50, 50) if madness > 70 else (200, 100, 100)
            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, madness, max_madness, show_numbers=True, custom_color=gauge_color)
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if madness >= 100:
                console.print(content_x, content_y + line, " 상태: 폭주!", fg=(255, 50, 50))
                line += 1
                console.print(content_x, content_y + line, "  3턴간 통제 불가, 공격력 +200%!", fg=(255, 100, 100))
            elif madness > 70:
                console.print(content_x, content_y + line, " 상태: 위험 구간", fg=(255, 150, 100))
                line += 1
                console.print(content_x, content_y + line, " 공격력 +100%, 받는 피해 +50%", fg=(255, 200, 100))
            elif madness >= 30:
                console.print(content_x, content_y + line, " 상태: 광전사 모드", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, " 공격력 +60%", fg=(255, 255, 100))
            else:
                console.print(content_x, content_y + line, " 상태: 정상", fg=(200, 200, 200))

        elif gimmick_type == "spirit_resonance":
            # 정령술사 - 정령 공명
            fire = getattr(character, 'spirit_fire', 0)
            water = getattr(character, 'spirit_water', 0)
            wind = getattr(character, 'spirit_wind', 0)
            earth = getattr(character, 'spirit_earth', 0)

            console.print(content_x, content_y + line, "🌊 정령술사 - 정령 공명", fg=(100, 200, 255))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 정령 상태
            console.print(content_x, content_y + line, f" 화염 정령: {'활성화' if fire > 0 else '비활성'}", fg=(255, 100, 50) if fire > 0 else (100, 100, 100))
            line += 1
            console.print(content_x, content_y + line, f"💧 수령 정령: {'활성화' if water > 0 else '비활성'}", fg=(100, 200, 255) if water > 0 else (100, 100, 100))
            line += 1
            console.print(content_x, content_y + line, f"💨 바람 정령: {'활성화' if wind > 0 else '비활성'}", fg=(200, 255, 200) if wind > 0 else (100, 100, 100))
            line += 1
            console.print(content_x, content_y + line, f"🌍 대지 정령: {'활성화' if earth > 0 else '비활성'}", fg=(150, 100, 50) if earth > 0 else (100, 100, 100))
            line += 1

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 융합 가능 체크
            active = sum([1 for s in [fire, water, wind, earth] if s > 0])
            if active >= 2:
                console.print(content_x, content_y + line, f"🔍 융합 가능! (활성 정령: {active})", fg=(255, 255, 100))
                line += 1
                if fire and wind:
                    console.print(content_x + 2, content_y + line, "• 화염 돌풍 (화염+바람)", fg=(255, 200, 100))
                    line += 1
                if water and earth:
                    console.print(content_x + 2, content_y + line, "• 진흙 속박 (물+대지)", fg=(100, 150, 100))
                    line += 1
            else:
                console.print(content_x, content_y + line, " 정령 소환 필요", fg=(150, 150, 150))

        elif gimmick_type == "stealth_mastery":
            # 암살자 - 은신 숙련
            stealth_active = getattr(character, 'stealth_active', False)
            shadow_strike = getattr(character, 'shadow_strike_ready', False)

            console.print(content_x, content_y + line, "🗡 암살자 - 은신 숙련", fg=(100, 100, 150))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 2

            if stealth_active:
                console.print(content_x + 10, content_y + line, " 은신 중", fg=(100, 100, 200))
                line += 2
                console.print(content_x, content_y + line, " 회피율 +80%", fg=(150, 200, 255))
                line += 1
                console.print(content_x, content_y + line, " 다음 공격 크리티컬 확정", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, "  공격 시 은신 해제", fg=(200, 150, 100))
            elif shadow_strike:
                console.print(content_x + 8, content_y + line, " 그림자 공격 준비", fg=(150, 150, 200))
                line += 2
                console.print(content_x, content_y + line, " 암살 기술 사용 가능", fg=(255, 200, 100))
            else:
                console.print(content_x + 12, content_y + line, " 노출", fg=(200, 200, 200))
                line += 2
                console.print(content_x, content_y + line, " 은신 스킬로 재진입 가능", fg=(150, 200, 255))

        elif gimmick_type == "dilemma_choice":
            # 철학자 - 딜레마 선택
            power = getattr(character, 'choice_power', 0)
            wisdom = getattr(character, 'choice_wisdom', 0)
            sacrifice = getattr(character, 'choice_sacrifice', 0)
            truth = getattr(character, 'choice_truth', 0)

            console.print(content_x, content_y + line, "📚 철학자 - 딜레마 선택", fg=(200, 150, 255))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            console.print(content_x, content_y + line, f"  힘의 선택: {power}", fg=(255, 100, 100))
            line += 1
            console.print(content_x, content_y + line, f"📖 지혜의 선택: {wisdom}", fg=(100, 200, 255))
            line += 1
            console.print(content_x, content_y + line, f"💔 희생의 선택: {sacrifice}", fg=(200, 100, 200))
            line += 1
            console.print(content_x, content_y + line, f" 진리의 선택: {truth}", fg=(255, 255, 100))
            line += 1

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 경향 분석
            dominant = max(power, wisdom, sacrifice, truth)
            if dominant == 0:
                console.print(content_x, content_y + line, " 선택 대기 중", fg=(150, 150, 150))
            else:
                if power == dominant:
                    console.print(content_x, content_y + line, " 경향: 힘 중심", fg=(255, 100, 100))
                elif wisdom == dominant:
                    console.print(content_x, content_y + line, " 경향: 지혜 중심", fg=(100, 200, 255))
                elif sacrifice == dominant:
                    console.print(content_x, content_y + line, " 경향: 희생 중심", fg=(200, 100, 200))
                else:
                    console.print(content_x, content_y + line, " 경향: 진리 중심", fg=(255, 255, 100))

        elif gimmick_type == "support_fire":
            # 궁수 - 지원사격
            combo = getattr(character, 'support_fire_combo', 0)

            # 실제로 마킹된 아군 수 계산
            marked = 0
            if hasattr(self, 'combat_manager') and hasattr(self.combat_manager, 'allies'):
                for ally in self.combat_manager.allies:
                    if ally == character:  # 자기 자신은 제외
                        continue
                    # 7가지 화살 타입 중 하나라도 마킹되어 있으면 카운트
                    has_mark = any([
                        getattr(ally, 'mark_slot_normal', 0) > 0,
                        getattr(ally, 'mark_slot_piercing', 0) > 0,
                        getattr(ally, 'mark_slot_fire', 0) > 0,
                        getattr(ally, 'mark_slot_ice', 0) > 0,
                        getattr(ally, 'mark_slot_poison', 0) > 0,
                        getattr(ally, 'mark_slot_explosive', 0) > 0,
                        getattr(ally, 'mark_slot_holy', 0) > 0,
                    ])
                    if has_mark:
                        marked += 1

            console.print(content_x, content_y + line, " 궁수 - 지원사격", fg=(150, 200, 100))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            console.print(content_x, content_y + line, f"지원 콤보: {combo}", fg=(255, 200, 100))
            line += 1
            console.print(content_x, content_y + line, f"표식된 아군: {marked}명", fg=(100, 255, 200))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if combo >= 7:
                console.print(content_x, content_y + line, " 완벽한 지원!", fg=(255, 215, 0))
                line += 1
                console.print(content_x, content_y + line, " 데미지 +100%, 확정 크리티컬", fg=(255, 255, 100))
            elif combo >= 5:
                console.print(content_x, content_y + line, " 연속 지원 보너스!", fg=(255, 200, 100))
                line += 1
                console.print(content_x, content_y + line, " 데미지 +60%, 크리티컬 +40%", fg=(255, 255, 100))
            elif combo >= 3:
                console.print(content_x, content_y + line, " 연속 지원 중", fg=(200, 255, 200))
                line += 1
                console.print(content_x, content_y + line, " 데미지 +40%, 크리티컬 +20%", fg=(255, 255, 200))
            else:
                console.print(content_x, content_y + line, " 콤보 축적 중", fg=(150, 150, 150))

        elif gimmick_type == "hack_threading":
            # 해커 - 해킹 스레드 (구버전 호환)
            threads = getattr(character, 'active_threads', 0)
            exploits = getattr(character, 'exploit_count', 0)
            max_threads = getattr(character, 'max_threads', 5)

            # 리스트 타입인 경우 길이로 변환
            if isinstance(threads, list):
                threads = len(threads)
            if isinstance(exploits, list):
                exploits = len(exploits)

            console.print(content_x, content_y + line, " 해커 - 해킹 스레드", fg=(100, 255, 100))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            console.print(content_x, content_y + line, f"활성 스레드: {threads}/{max_threads}", fg=(150, 255, 150))
            line += 1
            console.print(content_x, content_y + line, f"익스플로잇: {exploits}", fg=(255, 200, 100))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if threads >= 4:
                console.print(content_x, content_y + line, " 다중 스레드 공격 가능!", fg=(255, 255, 100))
                line += 1
            if exploits >= 3:
                console.print(content_x, content_y + line, " 시스템 장악 준비 완료", fg=(255, 100, 255))

        elif gimmick_type == "multithread_system":
            # 해커 - 멀티스레드 시스템
            # 실제 활성 프로그램 수 계산
            program_fields = ['program_virus', 'program_backdoor', 'program_ddos', 'program_ransomware', 'program_spyware']
            active_programs = sum(1 for field in program_fields if getattr(character, field, 0) > 0)
            max_threads = getattr(character, 'max_threads', 3)
            
            virus = getattr(character, 'program_virus', 0)
            backdoor = getattr(character, 'program_backdoor', 0)
            ddos = getattr(character, 'program_ddos', 0)
            ransomware = getattr(character, 'program_ransomware', 0)
            spyware = getattr(character, 'program_spyware', 0)

            console.print(content_x, content_y + line, " 해커 - 멀티스레드 시스템", fg=(100, 255, 100))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            console.print(content_x, content_y + line, f"활성 프로그램: {active_programs}/{max_threads}", fg=(150, 255, 150))
            line += 2

            # 개별 프로그램 상태
            if virus > 0:
                console.print(content_x, content_y + line, f"  - 바이러스: {virus}턴 남음", fg=(255, 100, 100))
                line += 1
            if backdoor > 0:
                console.print(content_x, content_y + line, f"  - 백도어: {backdoor}턴 남음", fg=(255, 150, 100))
                line += 1
            if ddos > 0:
                console.print(content_x, content_y + line, f"  - DDoS: {ddos}턴 남음", fg=(255, 200, 100))
                line += 1
            if ransomware > 0:
                console.print(content_x, content_y + line, f"  - 랜섬웨어: {ransomware}턴 남음", fg=(255, 100, 200))
                line += 1
            if spyware > 0:
                console.print(content_x, content_y + line, f"  - 스파이웨어: {spyware}턴 남음", fg=(200, 100, 255))
                line += 1

            if active_programs == 0:
                console.print(content_x, content_y + line, "[안내] 프로그램 실행 필요", fg=(150, 150, 150))
                line += 1
            else:
                line += 1

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if active_programs >= 3:
                console.print(content_x, content_y + line, "[효과] 다중 프로그램 공격 가능!", fg=(255, 255, 100))
                line += 1
            if active_programs >= max_threads:
                console.print(content_x, content_y + line, "[최대] 최대 프로그램 실행 중!", fg=(100, 255, 255))

        elif gimmick_type == "cheer_gauge":
            # 검투사 - 환호
            cheer = getattr(character, 'cheer', 0)
            max_cheer = getattr(character, 'max_cheer', 100)

            console.print(content_x, content_y + line, " 검투사 - 환호 게이지", fg=(255, 200, 100))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_color = (255, 215, 0) if cheer > 70 else (200, 150, 100)
            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, cheer, max_cheer, show_numbers=True, custom_color=gauge_color)
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if cheer >= 100:
                console.print(content_x, content_y + line, " 열광! 검투사의 영광!", fg=(255, 215, 0))
                line += 1
                console.print(content_x, content_y + line, " 무적 3턴!", fg=(255, 255, 100))
            elif cheer > 70:
                console.print(content_x, content_y + line, " 열광! 궁극기 강화", fg=(255, 200, 100))
                line += 1
                console.print(content_x, content_y + line, " 공격력 +60%, 크리티컬 +40%", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, " 모든 공격 광역화", fg=(255, 200, 100))
            elif cheer > 40:
                console.print(content_x, content_y + line, " 고조 - 공격력 증가", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, " 공격력 +30%, 크리티컬 +20%", fg=(255, 255, 200))
            else:
                console.print(content_x, content_y + line, " 평온 - 축적 필요", fg=(150, 150, 150))

        # === 기존 기믹 시스템들 (21개) ===

        elif gimmick_type == "stance_system":
            # 전사 - 스탠스 시스템
            stance = getattr(character, 'current_stance', 0)
            # 문자열인 경우 정수로 변환
            if isinstance(stance, str):
                stance_id_to_index = {
                    "balanced": 0,
                    "attack": 1,
                    "defense": 2,
                    "berserker": 4,
                    "guardian": 5,
                    "speed": 6
                }
                stance = stance_id_to_index.get(stance, 0)
            # 스탠스 인덱스를 배열 인덱스로 매핑 (0,1,2,4,5,6 -> 0,1,2,3,4,5)
            stance_to_array_index = {
                0: 0,  # balanced -> 중립
                1: 1,  # attack -> 공격
                2: 2,  # defense -> 방어
                4: 3,  # berserker -> 광전사
                5: 4,  # guardian -> 수호자
                6: 5   # speed -> 신속
            }
            stance_names = ["중립", "공격", "방어", "광전사", "수호자", "신속"]

            console.print(content_x, content_y + line, " 전사 - 스탠스 시스템", fg=(255, 150, 100))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 2

            # 현재 스탠스 강조 표시
            if isinstance(stance, int):
                array_index = stance_to_array_index.get(stance, 0)
                if 0 <= array_index < len(stance_names):
                    console.print(content_x + 10, content_y + line, f"【 {stance_names[array_index]} 】", fg=(255, 255, 100))
                    line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 스탠스별 효과
            stance_effects = [
                "모든 스탯 그대로",
                "공격력 +40%, 방어력/마법방어력 -25%",
                "방어력/마법방어력 +60%, 공격력 -30%, 속도 -30%",
                "속도/공격력 +55%, 방어력/마법방어력 -45%, 매턴 피해",
                "모든 스탯 -15%, HP/MP 매턴 재생",
                "속도 +80%, 방어력/마법방어력/공격력 -25%"
            ]
            if isinstance(stance, int):
                array_index = stance_to_array_index.get(stance, 0)
                if 0 <= array_index < len(stance_effects):
                    console.print(content_x, content_y + line, f"{stance_effects[array_index]}", fg=(255, 255, 200))

        elif gimmick_type == "elemental_counter":
            # 아크메이지 - 원소 카운터
            fire = getattr(character, 'fire_element', 0)
            ice = getattr(character, 'ice_element', 0)
            lightning = getattr(character, 'lightning_element', 0)
            max_elem = 5

            console.print(content_x, content_y + line, "🔮 아크메이지 - 원소 카운터", fg=(150, 100, 255))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 원소 게이지들
            console.print(content_x, content_y + line, " 화염:", fg=(255, 100, 50))
            gauge_renderer.render_bar(console, content_x + 8, content_y + line, 15, fire, max_elem, show_numbers=True, custom_color=(255, 100, 50))
            line += 1
            console.print(content_x, content_y + line, " 냉기:", fg=(100, 200, 255))
            gauge_renderer.render_bar(console, content_x + 8, content_y + line, 15, ice, max_elem, show_numbers=True, custom_color=(100, 200, 255))
            line += 1
            console.print(content_x, content_y + line, " 번개:", fg=(255, 255, 100))
            gauge_renderer.render_bar(console, content_x + 8, content_y + line, 15, lightning, max_elem, show_numbers=True, custom_color=(255, 255, 100))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 원소 조합 가능 체크
            if fire >= 3 and ice >= 3:
                console.print(content_x, content_y + line, " 화염+냉기 융합 가능!", fg=(255, 200, 255))
                line += 1
            if ice >= 3 and lightning >= 3:
                console.print(content_x, content_y + line, " 냉기+번개 융합 가능!", fg=(200, 255, 255))
                line += 1
            if fire >= 3 and lightning >= 3:
                console.print(content_x, content_y + line, " 화염+번개 융합 가능!", fg=(255, 255, 200))

        elif gimmick_type == "support_fire_system":
            # 궁수 - 지원사격 시스템 (구버전 호환)
            combo = getattr(character, 'support_fire_combo', 0)

            # 실제로 마킹된 아군 수 및 상세 정보 계산
            marked_details = []
            if hasattr(self, 'combat_manager') and hasattr(self.combat_manager, 'allies'):
                for ally in self.combat_manager.allies:
                    if ally == character:  # 자기 자신은 제외
                        continue

                    ally_marks = []
                    for arrow_type in ['normal', 'piercing', 'fire', 'ice', 'poison', 'explosive', 'holy']:
                        slot = getattr(ally, f'mark_slot_{arrow_type}', 0)
                        shots = getattr(ally, f'mark_shots_{arrow_type}', 0)
                        if slot > 0 and shots > 0:
                            ally_marks.append((arrow_type, shots))

                    if ally_marks:
                        ally_name = getattr(ally, 'name', '아군')
                        marked_details.append((ally_name, ally_marks))

            console.print(content_x, content_y + line, " 궁수 - 지원사격", fg=(100, 200, 100))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 마킹된 아군 정보
            console.print(content_x, content_y + line, f"마킹된 아군: ({len(marked_details)}/3)", fg=(200, 200, 200))
            line += 1

            if marked_details:
                console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
                line += 1

                arrow_names = {
                    'normal': '일반',
                    'piercing': '관통',
                    'fire': '화염',
                    'ice': '빙결',
                    'poison': '독',
                    'explosive': '폭발',
                    'holy': '신성'
                }

                # 각 마킹된 아군 표시
                for i, (ally_name, marks) in enumerate(marked_details):
                    console.print(content_x, content_y + line, f"[{ally_name}] ", fg=(255, 200, 100))
                    line += 1
                    for arrow_type, shots in marks:
                        arrow_name = arrow_names.get(arrow_type, arrow_type)
                        console.print(content_x + 2, content_y + line, f"• {arrow_name}: {shots}회", fg=(200, 200, 200))
                        line += 1

                    if i < len(marked_details) - 1:
                        line += 1  # 간격

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 콤보 상태
            if combo >= 7:
                console.print(content_x, content_y + line, " 완벽한 지원! (콤보 7+)", fg=(255, 255, 100))
                line += 1
                console.print(content_x + 2, content_y + line, "데미지 +100%, 크리티컬 확정", fg=(255, 255, 200))
            elif combo >= 5:
                console.print(content_x, content_y + line, f" 콤보: {combo} 연속", fg=(255, 200, 100))
                line += 1
                console.print(content_x + 2, content_y + line, "데미지 +60%, 크리티컬 +40%", fg=(255, 200, 150))
                line += 1
                remaining_for_perfect = 7 - combo
                console.print(content_x, content_y + line, f" {remaining_for_perfect}회 더 성공 시 완벽한 지원!", fg=(200, 255, 200))
            elif combo >= 3:
                console.print(content_x, content_y + line, f" 콤보: {combo} 연속", fg=(255, 150, 100))
                line += 1
                console.print(content_x + 2, content_y + line, "데미지 +40%, 크리티컬 +20%", fg=(255, 200, 150))
            elif combo >= 2:
                console.print(content_x, content_y + line, f" 콤보: {combo} 연속", fg=(200, 150, 100))
                line += 1
                console.print(content_x + 2, content_y + line, "데미지 +20%", fg=(200, 200, 150))
            else:
                console.print(content_x, content_y + line, " 지원 대기 중...", fg=(150, 150, 150))
                line += 1
                console.print(content_x, content_y + line, "아군 공격 시 자동 지원 발동", fg=(180, 180, 180))

        elif gimmick_type == "magazine_system":
            # 저격수 - 탄창 시스템
            magazine = getattr(character, 'magazine', [])
            current_bullet = getattr(character, 'current_bullet_index', 0)

            console.print(content_x, content_y + line, " 저격수 - 탄창", fg=(255, 200, 100))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 탄환 타입 심볼 매핑
            bullet_symbols = {
                'N': '■',  # 기본 탄환
                'P': 'P',  # 관통탄
                'E': 'E',  # 폭발탄
                'I': 'I',  # 빙결탄
                'F': 'F',  # 화염탄
                'T': 'T',  # 독침탄
                'S': 'S',  # 섬광탄
                'H': 'H',  # 헤드샷 탄
            }

            # 탄창 표시 (최대 6발)
            max_bullets = 6
            bullet_display = ""
            for i in range(max_bullets):
                if i < len(magazine):
                    bullet_type = magazine[i] if isinstance(magazine, list) else magazine[i] if i < len(magazine) else 'N'
                    symbol = bullet_symbols.get(bullet_type, '■')
                    bullet_display += f"[{symbol}]"
                else:
                    bullet_display += "[□]"  # 빈 슬롯

            console.print(content_x, content_y + line, f"{bullet_display} {len(magazine)}/6", fg=(255, 255, 200))
            line += 1

            # 탄환 번호
            console.print(content_x, content_y + line, " 1  2  3  4  5  6", fg=(150, 150, 150))
            line += 1

            # 라스트 불렛 표시 (마지막 탄환)
            if len(magazine) > 0:
                last_bullet_indicator = " " * (len(magazine) * 3 - 1) + "↑ 라스트 불렛"
                console.print(content_x, content_y + line, last_bullet_indicator, fg=(255, 255, 100))
                line += 1

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 범례
            console.print(content_x, content_y + line, "범례:", fg=(200, 200, 200))
            line += 1
            console.print(content_x, content_y + line, "■=기본 P=관통 E=폭발", fg=(180, 180, 180))
            line += 1
            console.print(content_x, content_y + line, "I=빙결 F=화염 T=독침 S=섬광", fg=(180, 180, 180))
            line += 1

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 상태 메시지
            if len(magazine) == 0:
                console.print(content_x, content_y + line, " 탄창 비었음! 재장전 필요!", fg=(255, 100, 100))
                line += 1
                console.print(content_x, content_y + line, "권총 모드 (데미지 -80%)", fg=(255, 150, 150))
            elif len(magazine) <= 2:
                console.print(content_x, content_y + line, " 탄약 부족! 재장전 권장", fg=(255, 200, 100))
            elif len(magazine) == 6:
                console.print(content_x, content_y + line, "✓ 탄창 만탄!", fg=(100, 255, 100))
                line += 1
                # 다음 발사할 탄환 정보
                if current_bullet < len(magazine):
                    next_bullet = magazine[current_bullet] if isinstance(magazine, list) else magazine[current_bullet]
                    bullet_names = {
                        'N': '기본 탄환',
                        'P': '관통탄 (방어 무시)',
                        'E': '폭발탄 (광역)',
                        'I': '빙결탄 (빙결)',
                        'F': '화염탄 (화상)',
                        'T': '독침탄 (독)',
                        'S': '섬광탄 (명중률↓)',
                        'H': '헤드샷 탄 (크리티컬 100%)',
                    }
                    console.print(content_x, content_y + line, f"다음 발사: {bullet_names.get(next_bullet, '기본 탄환')}", fg=(200, 255, 200))
            else:
                # 다음 발사할 탄환 정보
                if current_bullet < len(magazine):
                    next_bullet = magazine[current_bullet] if isinstance(magazine, list) else magazine[current_bullet]
                    bullet_names = {
                        'N': '기본 탄환',
                        'P': '관통탄 (방어 무시)',
                        'E': '폭발탄 (광역)',
                        'I': '빙결탄 (빙결)',
                        'F': '화염탄 (화상)',
                        'T': '독침탄 (독)',
                        'S': '섬광탄 (명중률↓)',
                        'H': '헤드샷 탄 (크리티컬 100%)',
                    }
                    console.print(content_x, content_y + line, f"다음 발사: {bullet_names.get(next_bullet, '기본 탄환')}", fg=(200, 255, 200))

        elif gimmick_type == "sword_aura":
            # 검성 - 검기
            aura = getattr(character, 'sword_aura', 0)
            max_aura = getattr(character, 'max_sword_aura', 5)

            console.print(content_x, content_y + line, " 검성 - 검기", fg=(200, 220, 255))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, aura, max_aura, show_numbers=True, custom_color=(200, 220, 255))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if aura >= 5:
                console.print(content_x, content_y + line, " 검기 최대! 궁극기 가능", fg=(255, 255, 100))
            elif aura >= 3:
                console.print(content_x, content_y + line, " 검기 충전 중", fg=(200, 220, 255))
                line += 1
                console.print(content_x, content_y + line, " 공격력 +20%", fg=(255, 255, 200))
            else:
                console.print(content_x, content_y + line, " 검기 축적 중...", fg=(150, 150, 150))

        elif gimmick_type == "melody_system":
            # 바드 - 멜로디 시스템
            melody = getattr(character, 'melody_stacks', 0)
            max_melody = getattr(character, 'max_melody_stacks', 7)

            console.print(content_x, content_y + line, " 바드 - 멜로디", fg=(255, 200, 255))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, melody, max_melody, show_numbers=True, custom_color=(255, 200, 255))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if melody >= 7:
                console.print(content_x, content_y + line, " 완벽한 하모니!", fg=(255, 215, 0))
                line += 1
                console.print(content_x, content_y + line, " 파티 전체 모든 스탯 +30%", fg=(255, 255, 100))
            elif melody >= 4:
                console.print(content_x, content_y + line, " 멜로디 진행 중", fg=(255, 200, 255))
                line += 1
                console.print(content_x, content_y + line, " 파티 공격력 +15%", fg=(255, 255, 200))
            else:
                console.print(content_x, content_y + line, " 멜로디 작곡 중...", fg=(150, 150, 150))

        elif gimmick_type == "necro_system":
            # 네크로맨서 - 네크로 에너지
            necro = getattr(character, 'necro_energy', 0)
            max_necro = getattr(character, 'max_necro_energy', 50)
            corpses = getattr(character, 'corpse_count', 0)

            console.print(content_x, content_y + line, " 네크로맨서 - 사령 에너지", fg=(150, 100, 150))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            console.print(content_x, content_y + line, "사령 에너지:", fg=(200, 200, 200))
            gauge_renderer.render_bar(console, content_x, content_y + line + 1, box_width - 6, necro, max_necro, show_numbers=True, custom_color=(150, 100, 150))
            line += 2

            console.print(content_x, content_y + line, f" 시체 수집: {corpses}/10", fg=(200, 150, 200))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if corpses >= 5:
                console.print(content_x, content_y + line, " 강력한 언데드 소환 가능!", fg=(255, 200, 255))
            elif corpses >= 2:
                console.print(content_x, content_y + line, " 언데드 소환 가능", fg=(200, 150, 200))
            else:
                console.print(content_x, content_y + line, " 시체 수집 필요", fg=(150, 150, 150))

        elif gimmick_type == "time_system":
            # 시간술사 - 시간 마크
            marks = getattr(character, 'time_marks', 0)
            max_marks = getattr(character, 'max_time_marks', 7)

            console.print(content_x, content_y + line, " 시간술사 - 시간 마크", fg=(200, 150, 255))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, marks, max_marks, show_numbers=True, custom_color=(200, 150, 255))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if marks >= 7:
                console.print(content_x, content_y + line, " 시간 역행 가능!", fg=(255, 255, 100))
            elif marks >= 4:
                console.print(content_x, content_y + line, " 시간 조작 가능", fg=(200, 150, 255))
            else:
                console.print(content_x, content_y + line, " 시간 마크 축적 중...", fg=(150, 150, 150))

        elif gimmick_type == "alchemy_system":
            # 연금술사 - 포션 재고
            potions = getattr(character, 'potion_stock', 0)
            max_potions = getattr(character, 'max_potion_stock', 10)

            console.print(content_x, content_y + line, " 연금술사 - 포션 재고", fg=(100, 255, 150))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, potions, max_potions, show_numbers=True, custom_color=(100, 255, 150))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if potions >= 8:
                console.print(content_x, content_y + line, " 포션 풍부!", fg=(100, 255, 150))
                line += 1
                console.print(content_x, content_y + line, " 고급 포션 제작 가능", fg=(255, 255, 200))
            elif potions >= 4:
                console.print(content_x, content_y + line, " 포션 충분", fg=(150, 255, 200))
            else:
                console.print(content_x, content_y + line, " 포션 부족 - 제작 필요", fg=(255, 200, 100))

        elif gimmick_type == "darkness_system":
            # 암흑기사 - 어둠
            darkness = getattr(character, 'darkness', 0)
            max_darkness = 100

            console.print(content_x, content_y + line, " 암흑기사 - 어둠", fg=(100, 100, 150))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, darkness, max_darkness, show_numbers=True, custom_color=(100, 100, 150))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if darkness >= 70:
                console.print(content_x, content_y + line, " 어둠 가득!", fg=(150, 150, 200))
                line += 1
                console.print(content_x, content_y + line, " HP 소모 스킬 +50%", fg=(255, 200, 255))
            elif darkness >= 40:
                console.print(content_x, content_y + line, " 어둠 축적 중", fg=(120, 120, 180))
            else:
                console.print(content_x, content_y + line, " 어둠 부족", fg=(150, 150, 150))

        elif gimmick_type == "holy_system":
            # 성기사/신관 - 신성력
            holy = getattr(character, 'holy_power', 0)
            max_holy = getattr(character, 'max_holy_power', 100)

            console.print(content_x, content_y + line, " 성기사 - 신성력", fg=(255, 255, 200))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, holy, max_holy, show_numbers=True, custom_color=(255, 255, 200))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if holy >= 80:
                console.print(content_x, content_y + line, " 신성력 충만!", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, " 회복 +50%, 언데드 특효", fg=(255, 255, 200))
            elif holy >= 40:
                console.print(content_x, content_y + line, " 신성력 충전 중", fg=(255, 255, 150))
            else:
                console.print(content_x, content_y + line, " 기도 필요", fg=(150, 150, 150))

        elif gimmick_type == "iaijutsu_system":
            # 사무라이 - 거합 게이지
            will = getattr(character, 'will_gauge', 0)
            max_will = getattr(character, 'max_will_gauge', 100)

            console.print(content_x, content_y + line, " 사무라이 - 거합", fg=(200, 50, 50))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, will, max_will, show_numbers=True, custom_color=(200, 50, 50))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if will >= 100:
                console.print(content_x, content_y + line, " 거합 준비 완료!", fg=(255, 100, 100))
                line += 1
                console.print(content_x, content_y + line, " 일격필살 가능!", fg=(255, 255, 100))
            elif will >= 50:
                console.print(content_x, content_y + line, " 의지 집중 중", fg=(200, 100, 100))
            else:
                console.print(content_x, content_y + line, " 집중 필요", fg=(150, 150, 150))

        elif gimmick_type == "enchant_system":
            # 마검사 - 마력 부여
            mana = getattr(character, 'mana_blade', 0)
            max_mana = getattr(character, 'max_mana_blade', 100)

            console.print(content_x, content_y + line, "🔮 마검사 - 마력 부여", fg=(150, 100, 255))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, mana, max_mana, show_numbers=True, custom_color=(150, 100, 255))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if mana >= 70:
                console.print(content_x, content_y + line, "🔮 마검 완성!", fg=(200, 150, 255))
                line += 1
                console.print(content_x, content_y + line, " 물리+마법 피해 극대화", fg=(255, 255, 200))
            elif mana >= 35:
                console.print(content_x, content_y + line, "🔮 마력 충전 중", fg=(150, 100, 255))
            else:
                console.print(content_x, content_y + line, " 마력 부여 필요", fg=(150, 150, 150))

        elif gimmick_type == "shapeshifting_system":
            # 드루이드 - 변신
            nature = getattr(character, 'nature_points', 0)
            form = getattr(character, 'current_form', None)

            console.print(content_x, content_y + line, " 드루이드 - 변신", fg=(100, 200, 100))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 2

            if form:
                form_icons = {
                    "bear": "🐻 곰",
                    "cat": "🐱 표범",
                    "panther": "🐱 표범",
                    "eagle": "🦅 독수리",
                    "wolf": "🐺 늑대",
                    "primal": "🌿 진 변신",
                    "elemental": "⚡ 원소"
                }
                form_name = form_icons.get(form, form)
                console.print(content_x + 10, content_y + line, f"【 {form_name} 】", fg=(100, 255, 100))
            else:
                console.print(content_x + 10, content_y + line, "【 👤 인간 형태 】", fg=(200, 200, 200))
            line += 2

            console.print(content_x, content_y + line, f" 자연 포인트: {nature}/100", fg=(150, 255, 150))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if nature >= 70:
                console.print(content_x, content_y + line, " 자연의 힘 충만!", fg=(100, 255, 100))
            else:
                console.print(content_x, content_y + line, " 자연과 교감 필요", fg=(150, 150, 150))

        elif gimmick_type == "dragon_marks":
            # 용기사 - 용의 표식
            marks = getattr(character, 'dragon_marks', 0)
            max_marks = getattr(character, 'max_dragon_marks', 3)
            power = getattr(character, 'dragon_power', 0)

            console.print(content_x, content_y + line, " 용기사 - 용의 표식", fg=(255, 100, 50))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            console.print(content_x, content_y + line, f" 용의 표식: {marks}/{max_marks}", fg=(255, 150, 100))
            line += 1
            console.print(content_x, content_y + line, f" 용력: {power}/100", fg=(255, 200, 100))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if marks >= 3:
                console.print(content_x, content_y + line, " 드래곤 폼 가능!", fg=(255, 100, 50))
                line += 1
                console.print(content_x, content_y + line, " 모든 스탯 +50%", fg=(255, 255, 100))
            else:
                console.print(content_x, content_y + line, " 표식 축적 필요", fg=(150, 150, 150))

        elif gimmick_type == "arena_system":
            # 검투사 - 투기장
            arena = getattr(character, 'arena_points', 0)
            glory = getattr(character, 'glory_points', 0)
            kills = getattr(character, 'kill_count', 0)

            console.print(content_x, content_y + line, " 검투사 - 투기장", fg=(255, 200, 100))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            console.print(content_x, content_y + line, f" 투기: {arena}", fg=(255, 200, 100))
            line += 1
            console.print(content_x, content_y + line, f"🏆 영광: {glory}", fg=(255, 215, 0))
            line += 1
            console.print(content_x, content_y + line, f" 처치: {kills}", fg=(255, 100, 100))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if glory >= 100:
                console.print(content_x, content_y + line, "🏆 전설적 검투사!", fg=(255, 215, 0))
            elif glory >= 50:
                console.print(content_x, content_y + line, " 명성 높은 검투사", fg=(255, 200, 100))
            else:
                console.print(content_x, content_y + line, " 명성 획득 필요", fg=(150, 150, 150))

        elif gimmick_type == "break_system":
            # 브레이커 - 파괴력
            break_power = getattr(character, 'break_power', 0)
            max_break = getattr(character, 'max_break_power', 10)

            console.print(content_x, content_y + line, " 브레이커 - 파괴력", fg=(255, 150, 50))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, break_power, max_break, show_numbers=True, custom_color=(255, 150, 50))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if break_power >= 10:
                console.print(content_x, content_y + line, " 최대 파괴력!", fg=(255, 100, 50))
                line += 1
                console.print(content_x, content_y + line, " 방어 무시 100%", fg=(255, 255, 100))
            else:
                console.print(content_x, content_y + line, " 파괴력 축적 중...", fg=(150, 150, 150))

        elif gimmick_type == "plunder_system":
            # 해적 - 약탈
            gold = getattr(character, 'gold', 0)

            console.print(content_x, content_y + line, "‍☠ 해적 - 약탈 골드", fg=(255, 215, 0))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 2

            console.print(content_x + 10, content_y + line, f" {gold} 골드", fg=(255, 215, 0))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if gold >= 1000:
                console.print(content_x, content_y + line, " 골드 풍부!", fg=(255, 215, 0))
                line += 1
                console.print(content_x, content_y + line, " 용병/함포 강화 가능", fg=(255, 255, 200))
            else:
                console.print(content_x, content_y + line, " 약탈 필요", fg=(200, 200, 200))

        elif gimmick_type == "divinity_system":
            # 프리스트/클레릭 - 신성력
            judgment = getattr(character, 'judgment_points', 0)
            faith = getattr(character, 'faith_points', 0)

            console.print(content_x, content_y + line, " 성직자 - 신성력", fg=(255, 255, 200))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            console.print(content_x, content_y + line, f" 심판: {judgment}/100", fg=(255, 200, 100))
            line += 1
            console.print(content_x, content_y + line, f" 신앙: {faith}/100", fg=(200, 220, 255))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if judgment >= 70 and faith >= 70:
                console.print(content_x, content_y + line, " 균형잡힌 신성력!", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, " 기적 스킬 가능", fg=(255, 255, 200))
            elif judgment > faith:
                console.print(content_x, content_y + line, " 심판 중심 - 공격 강화", fg=(255, 200, 100))
            else:
                console.print(content_x, content_y + line, " 신앙 중심 - 회복 강화", fg=(200, 220, 255))

        else:
            # 나머지 미구현 기믹들 (폴백)
            console.print(content_x, content_y + line, f"기믹: {gimmick_type}", fg=(200, 200, 200))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 간단한 정보 표시
            detail_text = self._get_gimmick_detail(character)
            for detail_line in detail_text.split('\n')[:10]:  # 최대 10줄
                if line >= box_height - 3:
                    break
                console.print(content_x, content_y + line, detail_line[:box_width - 6], fg=(200, 200, 200))
                line += 1

        # 하단 안내
        console.print(content_x, box_y + box_height - 2, "아무 키나 눌러 닫기...", fg=(150, 150, 150))

    def _create_gauge_bar(self, current: int, maximum: int, width: int = 10, danger_threshold: int = None, optimal_min: int = None, optimal_max: int = None) -> str:
        """게이지 바 생성

        Args:
            current: 현재 값
            maximum: 최대 값
            width: 바의 너비 (문자 수)
            danger_threshold: 위험 구간 시작값 (이상이면 위험)
            optimal_min: 최적 구간 최소값
            optimal_max: 최적 구간 최대값

        Returns:
            게이지 바 문자열
        """
        if maximum == 0:
            ratio = 0
        else:
            ratio = current / maximum

        filled = int(ratio * width)
        empty = width - filled

        # 위험/최적 구간 판별
        if danger_threshold is not None and current >= danger_threshold:
            # 위험 구간: 빨간색 표시 ( 사용)
            bar = f"[{'█' * filled}{'░' * empty}] "
        elif optimal_min is not None and optimal_max is not None and optimal_min <= current <= optimal_max:
            # 최적 구간: 녹색 표시 (✓ 사용)
            bar = f"[{'█' * filled}{'░' * empty}] ✓"
        else:
            # 일반 구간
            bar = f"[{'█' * filled}{'░' * empty}]"

        return f"{bar} {current}/{maximum}"

    def _get_gimmick_detail(self, character: Any) -> str:
        """캐릭터의 기믹 상태 상세 정보 (기믹 커맨드용)"""
        gimmick_type = getattr(character, 'gimmick_type', None)
        if not gimmick_type:
            return "기믹 시스템 없음"

        details = []

        # === 33개 직업 기믹 시스템 상세 (ISSUE-007: UI 시각화 개선) ===

        # 몽크 - 음양 흐름
        if gimmick_type == "yin_yang_flow":
            ki = getattr(character, 'ki_gauge', 50)
            details.append("=== 음양 흐름 시스템 ===")
            # 게이지 바 추가 (최적 구간: 40-60)
            gauge_bar = self._create_gauge_bar(ki, 100, width=10, optimal_min=40, optimal_max=60)
            details.append(f"기 게이지: {gauge_bar}")
            if ki < 20:
                details.append("상태: ☯ 음 (방어/회복 강화)")
            elif ki > 80:
                details.append("상태: ☯ 양 (공격/속도 강화)")
            else:
                details.append("상태: ☯ 균형 (안정적 전투)")

        elif gimmick_type == "rune_resonance":
            fire = getattr(character, 'rune_fire', 0)
            ice = getattr(character, 'rune_ice', 0)
            lightning = getattr(character, 'rune_lightning', 0)
            earth = getattr(character, 'rune_earth', 0)
            arcane = getattr(character, 'rune_arcane', 0)
            details.append("=== 룬 공명 시스템 ===")
            fire_bar = self._create_gauge_bar(fire, 3, width=10)
            ice_bar = self._create_gauge_bar(ice, 3, width=10)
            lightning_bar = self._create_gauge_bar(lightning, 3, width=10)
            earth_bar = self._create_gauge_bar(earth, 3, width=10)
            arcane_bar = self._create_gauge_bar(arcane, 3, width=10)
            details.append(f" 화염 룬: {fire_bar}")
            details.append(f"  냉기 룬: {ice_bar}")
            details.append(f" 번개 룬: {lightning_bar}")
            details.append(f"🌍 대지 룬: {earth_bar}")
            details.append(f" 비전 룬: {arcane_bar}")
            if fire >= 2 and ice >= 2:
                details.append(" 공명 가능: 화염+냉기")
            if ice >= 2 and lightning >= 2:
                details.append(" 공명 가능: 냉기+번개")
            if fire >= 2 and lightning >= 2:
                details.append(" 공명 가능: 화염+번개")

        elif gimmick_type == "probability_distortion":
            gauge = getattr(character, 'distortion_gauge', 0)
            details.append("=== 확률 왜곡 시스템 ===")
            gauge_bar = self._create_gauge_bar(gauge, 100, width=10)
            details.append(f"왜곡 게이지: {gauge_bar}")
            if gauge >= 100:
                details.append("🌀 평행우주 사용 가능!")
            elif gauge >= 50:
                details.append("⏮ 시간 되감기 사용 가능")
            elif gauge >= 30:
                details.append("💨 회피 왜곡 사용 가능")
            elif gauge >= 20:
                details.append("💫 크리티컬 왜곡 사용 가능")

        # 기계공학자 - 열 관리 (YAML: heat_management)
        elif gimmick_type == "heat_management":
            heat = getattr(character, 'heat', 0)
            details.append("=== 열 관리 시스템 ===")
            # 위험 구간 80+, 최적 구간 50-79
            gauge_bar = self._create_gauge_bar(heat, 100, width=10, danger_threshold=80, optimal_min=50, optimal_max=79)
            details.append(f"열 누적: {gauge_bar}")
            if heat >= 80:
                details.append("  위험 구간! 과열 포격 배율 증가")
            elif heat >= 50:
                details.append(" 최적 구간 - 안정적 화력")
            elif heat >= 30:
                details.append("🌡 안전 구간 - 열 축적 중")
            else:
                details.append(" 낮은 열량 - 축적 필요")

        elif gimmick_type == "thirst_gauge":
            thirst = getattr(character, 'thirst', 0)
            details.append("=== 갈증 게이지 시스템 ===")
            gauge_bar = self._create_gauge_bar(thirst, 100, width=10, danger_threshold=70)
            details.append(f"갈증: {gauge_bar}")
            if thirst > 70:
                details.append("💧 갈망 상태 - 흡혈 강화")
            elif thirst < 30:
                details.append("😌 만족 상태 - 안정적")
            else:
                details.append("😐 보통 상태")

        # 버서커 - 광기 임계값 (YAML: madness_threshold)
        elif gimmick_type == "madness_threshold":
            madness = getattr(character, 'madness', 0)
            details.append("=== 광기 임계값 시스템 ===")
            gauge_bar = self._create_gauge_bar(madness, 100, width=10, danger_threshold=70)
            details.append(f"광기: {gauge_bar}")
            if madness >= 70:
                details.append(" 광란 상태 - 초강력 공격 가능!")
            elif madness >= 40:
                details.append("😠 격앙 상태 - 공격력 증가")
            else:
                details.append("😐 안전 구간")

        # 정령술사 - 정령 소환 (YAML: elemental_spirits)
        elif gimmick_type == "elemental_spirits":
            fire = getattr(character, 'spirit_fire', 0)
            water = getattr(character, 'spirit_water', 0)
            wind = getattr(character, 'spirit_wind', 0)
            earth = getattr(character, 'spirit_earth', 0)
            details.append("=== 정령 소환 시스템 ===")
            details.append(f" 화염 정령: {'✅ 활성화' if fire > 0 else '❌ 비활성'}")
            details.append(f"💧 수령 정령: {'✅ 활성화' if water > 0 else '❌ 비활성'}")
            details.append(f"💨 바람 정령: {'✅ 활성화' if wind > 0 else '❌ 비활성'}")
            details.append(f"🌍 대지 정령: {'✅ 활성화' if earth > 0 else '❌ 비활성'}")
            active = sum([1 for s in [fire, water, wind, earth] if s > 0])
            active_bar = self._create_gauge_bar(active, 4, width=10, optimal_min=2, optimal_max=4)
            details.append(f"활성 정령: {active_bar}")
            if active >= 2:
                details.append(f" 융합 가능! (활성 정령: {active}개)")

        # 암살자 - 은신 노출 (YAML: stealth_exposure)
        elif gimmick_type == "stealth_exposure":
            stealth_active = getattr(character, 'stealth_active', False)
            exposed_turns = getattr(character, 'exposed_turns', 0)
            restealth_cooldown = getattr(character, 'restealth_cooldown', 3)
            details.append("=== 은신 노출 시스템 ===")
            if stealth_active:
                details.append("상태:  은신 중")
                details.append("✅ 다음 공격 크리티컬 확정")
            else:
                details.append("상태:  노출")
                remaining = max(0, restealth_cooldown - exposed_turns)
                if remaining > 0:
                    cooldown_bar = self._create_gauge_bar(restealth_cooldown - remaining, restealth_cooldown, width=10)
                    details.append(f"재은신 쿨다운: {cooldown_bar}")
                else:
                    details.append("✅ 재은신 가능")

        elif gimmick_type == "dilemma_choice":
            power = getattr(character, 'choice_power', 0)
            wisdom = getattr(character, 'choice_wisdom', 0)
            sacrifice = getattr(character, 'choice_sacrifice', 0)
            truth = getattr(character, 'choice_truth', 0)
            details.append("=== 딜레마 선택 시스템 ===")
            power_bar = self._create_gauge_bar(power, 10, width=10)
            wisdom_bar = self._create_gauge_bar(wisdom, 10, width=10)
            sacrifice_bar = self._create_gauge_bar(sacrifice, 10, width=10)
            truth_bar = self._create_gauge_bar(truth, 10, width=10)
            details.append(f"[힘] 힘의 선택: {power_bar}")
            details.append(f"[지혜] 지혜의 선택: {wisdom_bar}")
            details.append(f"[희생] 희생의 선택: {sacrifice_bar}")
            details.append(f"[진리] 진리의 선택: {truth_bar}")
            dominant = max(power, wisdom, sacrifice, truth)
            if power == dominant and power > 0:
                details.append("경향: [힘] 힘 중심")
            elif wisdom == dominant and wisdom > 0:
                details.append("경향: [지혜] 지혜 중심")
            elif sacrifice == dominant and sacrifice > 0:
                details.append("경향: [희생] 희생 중심")
            elif truth == dominant and truth > 0:
                details.append("경향: [진리] 진리 중심")

        elif gimmick_type == "support_fire":
            combo = getattr(character, 'support_fire_combo', 0)

            # 실제로 마킹된 아군 수 계산
            marked = 0
            if hasattr(self, 'combat_manager') and hasattr(self.combat_manager, 'allies'):
                for ally in self.combat_manager.allies:
                    if ally == character:  # 자기 자신은 제외
                        continue
                    # 7가지 화살 타입 중 하나라도 마킹되어 있으면 카운트
                    has_mark = any([
                        getattr(ally, 'mark_slot_normal', 0) > 0,
                        getattr(ally, 'mark_slot_piercing', 0) > 0,
                        getattr(ally, 'mark_slot_fire', 0) > 0,
                        getattr(ally, 'mark_slot_ice', 0) > 0,
                        getattr(ally, 'mark_slot_poison', 0) > 0,
                        getattr(ally, 'mark_slot_explosive', 0) > 0,
                        getattr(ally, 'mark_slot_holy', 0) > 0,
                    ])
                    if has_mark:
                        marked += 1

            details.append("=== 지원사격 시스템 ===")
            combo_bar = self._create_gauge_bar(combo, 5, width=10, optimal_min=3, optimal_max=5)
            details.append(f"지원 콤보: {combo_bar}")
            details.append(f" 표식된 아군: {marked}명")
            if combo >= 3:
                details.append(" 연속 지원 보너스 활성!")

        # 해커 - 멀티스레드 시스템 (YAML: multithread_system)
        elif gimmick_type == "multithread_system":
            # 실제 활성 프로그램 수 계산
            program_fields = ['program_virus', 'program_backdoor', 'program_ddos', 'program_ransomware', 'program_spyware']
            active_programs = sum(1 for field in program_fields if getattr(character, field, 0) > 0)
            max_threads = getattr(character, 'max_threads', 3)
            
            virus = getattr(character, 'program_virus', 0)
            backdoor = getattr(character, 'program_backdoor', 0)
            ddos = getattr(character, 'program_ddos', 0)
            ransomware = getattr(character, 'program_ransomware', 0)
            spyware = getattr(character, 'program_spyware', 0)

            details.append("=== 멀티스레드 시스템 ===")
            thread_bar = self._create_gauge_bar(active_programs, max_threads, width=10, optimal_min=2, optimal_max=max_threads)
            details.append(f"활성 프로그램: {thread_bar} ({active_programs}/{max_threads})")
            
            # 개별 프로그램 상태
            if virus > 0:
                details.append(f"  - 바이러스: {virus}턴 남음")
            if backdoor > 0:
                details.append(f"  - 백도어: {backdoor}턴 남음")
            if ddos > 0:
                details.append(f"  - DDoS: {ddos}턴 남음")
            if ransomware > 0:
                details.append(f"  - 랜섬웨어: {ransomware}턴 남음")
            if spyware > 0:
                details.append(f"  - 스파이웨어: {spyware}턴 남음")
            
            if active_programs >= 3:
                details.append(" 다중 프로그램 공격 가능!")
            if active_programs >= max_threads:
                details.append(" 최대 프로그램 실행 중!")

        # 검투사 - 군중 환호 (YAML: crowd_cheer)
        elif gimmick_type == "crowd_cheer":
            cheer = getattr(character, 'cheer', 0)
            details.append("=== 군중 환호 시스템 ===")
            gauge_bar = self._create_gauge_bar(cheer, 100, width=10, optimal_min=70, optimal_max=100)
            details.append(f"환호: {gauge_bar}")
            if cheer >= 70:
                details.append(" 열광! 궁극기 강화")
            elif cheer >= 40:
                details.append(" 고조 - 공격력 증가")
            else:
                details.append(" 평온 - 축적 필요")

        # 시간술사 - 타임라인 시스템 (YAML: timeline_system)
        elif gimmick_type == "timeline_system":
            timeline = getattr(character, 'timeline', 0)
            details.append("=== 타임라인 시스템 ===")
            details.append(f"타임라인 위치: {timeline}")
            if timeline > 0:
                details.append(f"⏩ 미래 +{timeline} (속도 증가)")
            elif timeline < 0:
                details.append(f"⏪ 과거 {timeline} (HP 회복)")
            else:
                details.append("⏸ 현재 (균형 상태)")

        # 검성 - 검기 (YAML: sword_aura)
        elif gimmick_type == "sword_aura":
            aura = getattr(character, 'sword_aura', 0)
            max_aura = getattr(character, 'max_sword_aura', 5)
            details.append("=== 검기 시스템 ===")
            gauge_bar = self._create_gauge_bar(aura, max_aura, width=10, optimal_min=int(max_aura*0.6), optimal_max=max_aura)
            details.append(f"검기: {gauge_bar}")
            if aura >= max_aura * 0.8:
                details.append(" 검기 방출 가능!")
            elif aura >= max_aura * 0.5:
                details.append(" 고양 상태 - 공격력 증가")
            else:
                details.append("🔄 축적 중")

        # 기사 - 의무 시스템 (YAML: duty_system)
        elif gimmick_type == "duty_system":
            duty = getattr(character, 'duty_gauge', 0)
            details.append("=== 의무 시스템 ===")
            gauge_bar = self._create_gauge_bar(duty, 100, width=10, optimal_min=80, optimal_max=100)
            details.append(f"의무 게이지: {gauge_bar}")
            if duty >= 80:
                details.append("🛡 최고 명예 - 방어 극대")
            elif duty >= 50:
                details.append(" 충실 상태")
            else:
                details.append("😐 기본 상태")

        # 네크로맨서 - 언데드 군단 (YAML: undead_legion)
        elif gimmick_type == "undead_legion":
            skeleton = getattr(character, 'undead_skeleton', 0)
            zombie = getattr(character, 'undead_zombie', 0)
            ghost = getattr(character, 'undead_ghost', 0)
            total = skeleton + zombie + ghost
            max_undead = getattr(character, 'max_undead_total', 5)

            details.append("=== 언데드 군단 시스템 ===")
            details.append(f" 스켈레톤: {skeleton}/2")
            details.append(f"🧟 좀비: {zombie}/2")
            details.append(f"👻 유령: {ghost}/2")
            minion_bar = self._create_gauge_bar(total, max_undead, width=10, optimal_min=3, optimal_max=max_undead)
            details.append(f"총 소환: {minion_bar} ({total}/{max_undead})")
            if total >= 3:
                details.append(" 군단 형성 - 대량 공격 가능")
            elif total > 0:
                details.append("⏳ 소환 진행 중")
            else:
                details.append("⏳ 소환 준비 중")

        # 도적 - 절도 시스템 (YAML: theft_system)
        elif gimmick_type == "theft_system":
            stolen = getattr(character, 'stolen_items', 0)

            # 리스트 타입인 경우 길이로 변환
            if isinstance(stolen, list):
                stolen = len(stolen)

            details.append("=== 절도 시스템 ===")
            stolen_bar = self._create_gauge_bar(stolen, 10, width=10, optimal_min=5, optimal_max=10)
            details.append(f"훔친 아이템: {stolen_bar}")
            details.append(" 다음 목표: 적 버프/아이템")

        # 드루이드 - 변신 시스템 (YAML: shapeshifting_system)
        elif gimmick_type == "shapeshifting_system":
            form = getattr(character, 'current_form', None)
            nature = getattr(character, 'nature_points', 0)
            max_nature = getattr(character, 'max_nature_points', 5)
            details.append("=== 변신 시스템 ===")
            nature_bar = self._create_gauge_bar(nature, max_nature, width=10)
            details.append(f"자연 포인트: {nature_bar} ({nature}/{max_nature})")
            
            if form == 'bear':
                details.append("현재 형태: 🐻 곰")
                details.append("효과: 방어력/HP 증가")
            elif form in ['cat', 'panther']:
                details.append("현재 형태: 🐱 표범")
                details.append("효과: 속도/회피 증가")
            elif form == 'eagle':
                details.append("현재 형태: 🦅 독수리")
                details.append("효과: 공중 공격, 속도 증가")
            elif form == 'wolf':
                details.append("현재 형태: 🐺 늑대")
                details.append("효과: 공격력 증가, 광역 공격")
            elif form == 'primal':
                details.append("현재 형태: 🌿 진 변신")
                details.append("효과: 모든 능력치 증가")
            elif form == 'elemental':
                details.append("현재 형태: ⚡ 원소")
                details.append("효과: 원소 폭발")
            else:
                details.append("현재 형태: 👤 인간")
                details.append("상태: 기본 상태")

        # 마검사 - 마법부여 (YAML: enchant_system)
        elif gimmick_type == "enchant_system":
            enchant = getattr(character, 'active_enchant', None)
            details.append("=== 마법부여 시스템 ===")
            if enchant:
                details.append(f" 활성 부여: {enchant}")
            else:
                details.append("❌ 부여 없음")

        # 무당 - 저주 시스템 (YAML: curse_system, 하위 호환: totem_system)
        elif gimmick_type == "curse_system" or gimmick_type == "totem_system":
            curses = getattr(character, 'curse_stacks', 0)
            max_curses = getattr(character, 'max_curse_stacks', 10)
            details.append("=== 저주 시스템 ===")
            curse_bar = self._create_gauge_bar(curses, max_curses, width=10)
            details.append(f"저주 스택: {curse_bar} ({curses}/{max_curses})")
            details.append(" 저주 스택을 소비하여 강력한 주술 사용 가능")

        # 바드 - 선율 시스템 (YAML: melody_system)
        elif gimmick_type == "melody_system":
            melody = getattr(character, 'active_melody', None)
            notes = getattr(character, 'melody_notes', 0)
            max_notes = getattr(character, 'max_melody_notes', 8)
            details.append("=== 선율 시스템 ===")
            gauge_bar = self._create_gauge_bar(notes, max_notes, width=10)
            details.append(f"음표: {gauge_bar}")
            if melody:
                details.append(f" 연주 중: {melody}")
            else:
                details.append(" 대기 중")

        # 브레이커 - 브레이크 시스템 (YAML: break_system)
        elif gimmick_type == "break_system":
            bonus = getattr(character, 'break_bonus', 0)
            details.append("=== 브레이크 시스템 ===")
            gauge_bar = self._create_gauge_bar(bonus, 100, width=10, optimal_min=50, optimal_max=100)
            details.append(f"브레이크 보너스: {gauge_bar}%")
            if bonus >= 50:
                details.append(" 극대 브레이크!")

        # 사무라이 - 거합 시스템 (YAML: iaijutsu_system)
        elif gimmick_type == "iaijutsu_system":
            charge = getattr(character, 'will_gauge', 0)
            max_will = getattr(character, 'max_will_gauge', 100)
            details.append("=== 거합 시스템 ===")
            gauge_bar = self._create_gauge_bar(charge, max_will, width=10, optimal_min=80, optimal_max=max_will)
            details.append(f"집중력: {gauge_bar}")
            if charge >= max_will * 0.8:
                details.append(" 일섬 가능!")

        # 성직자 - 신성 시스템 (YAML: holy_system)
        elif gimmick_type == "holy_system":
            holy = getattr(character, 'holy_gauge', 0)
            details.append("=== 신성 시스템 ===")
            gauge_bar = self._create_gauge_bar(holy, 100, width=10, optimal_min=80, optimal_max=100)
            details.append(f"신성력: {gauge_bar}")
            if holy >= 80:
                details.append(" 신의 은총 발동 가능")

        # 성기사/대마법사 - 신성력 (YAML: divinity_system)
        elif gimmick_type == "divinity_system":
            divinity = getattr(character, 'divinity', 0)
            details.append("=== 신성력 시스템 ===")
            gauge_bar = self._create_gauge_bar(divinity, 100, width=10, optimal_min=80, optimal_max=100)
            details.append(f"신성력: {gauge_bar}")
            if divinity >= 80:
                details.append("🌟 신성 강화 활성")

        # 엘리멘탈리스트 - 속성 카운터 (YAML: elemental_counter)
        elif gimmick_type == "elemental_counter":
            fire = getattr(character, 'fire_stacks', 0)
            ice = getattr(character, 'ice_stacks', 0)
            lightning = getattr(character, 'lightning_stacks', 0)
            details.append("=== 속성 카운터 시스템 ===")
            fire_bar = self._create_gauge_bar(fire, 5, width=10)
            ice_bar = self._create_gauge_bar(ice, 5, width=10)
            lightning_bar = self._create_gauge_bar(lightning, 5, width=10)
            details.append(f" 화염: {fire_bar}")
            details.append(f" 냉기: {ice_bar}")
            details.append(f" 번개: {lightning_bar}")

        # 암흑기사 - 암흑 시스템 (YAML: darkness_system)
        elif gimmick_type == "darkness_system":
            darkness = getattr(character, 'darkness_gauge', 0)
            details.append("=== 암흑 시스템 ===")
            gauge_bar = self._create_gauge_bar(darkness, 100, width=10, danger_threshold=80)
            details.append(f"암흑력: {gauge_bar}")
            if darkness >= 80:
                details.append(" 암흑 폭발 가능")

        # 연금술사 - 연금 시스템 (YAML: alchemy_system)
        elif gimmick_type == "alchemy_system":
            catalyst = getattr(character, 'catalyst_type', None)
            details.append("=== 연금 시스템 ===")
            if catalyst:
                details.append(f"⚗ 활성 촉매: {catalyst}")
            else:
                details.append("❌ 촉매 없음")

        # 용기사 - 드래곤 마크 (YAML: dragon_marks)
        elif gimmick_type == "dragon_marks":
            marks = getattr(character, 'dragon_marks', 0)
            details.append("=== 드래곤 마크 시스템 ===")
            gauge_bar = self._create_gauge_bar(marks, 5, width=10, optimal_min=5, optimal_max=5)
            details.append(f"각인: {gauge_bar}")
            if marks >= 5:
                details.append(" 드래곤 변신 가능!")

        # 저격수 - 탄창 시스템 (YAML: magazine_system)
        elif gimmick_type == "magazine_system":
            ammo = getattr(character, 'ammo', 0)
            max_ammo = getattr(character, 'max_ammo', 6)
            details.append("=== 탄창 시스템 ===")
            gauge_bar = self._create_gauge_bar(ammo, max_ammo, width=10)
            details.append(f"탄약: {gauge_bar}")
            if ammo == 0:
                details.append("🔄 재장전 필요")
            elif ammo == max_ammo:
                details.append("✅ 탄창 만료")

        # 전사 - 자세 시스템 (YAML: stance_system)
        elif gimmick_type == "stance_system":
            stance = getattr(character, 'current_stance', 0)
            # 문자열인 경우 정수로 변환
            if isinstance(stance, str):
                stance_id_to_index = {
                    "balanced": 0,
                    "attack": 1,
                    "defense": 2,
                    "berserker": 4,
                    "guardian": 5,
                    "speed": 6
                }
                stance = stance_id_to_index.get(stance, 0)
            # 스탠스 인덱스를 배열 인덱스로 매핑 (0,1,2,4,5,6 -> 0,1,2,3,4,5)
            stance_to_array_index = {
                0: 0,  # balanced -> 중립
                1: 1,  # attack -> 공격
                2: 2,  # defense -> 방어
                4: 3,  # berserker -> 광전사
                5: 4,  # guardian -> 수호자
                6: 5   # speed -> 신속
            }
            details.append("=== 자세 시스템 ===")
            stance_names = ["중립", "공격", "방어", "광전사", "수호자", "신속"]
            if isinstance(stance, int):
                array_index = stance_to_array_index.get(stance, 0)
                if 0 <= array_index < len(stance_names):
                    details.append(f"현재 자세: {stance_names[array_index]}")
                else:
                    details.append(f"현재 자세: {stance}")
            else:
                details.append(f"현재 자세: {stance}")

        # 해적 - 약탈 시스템 (YAML: plunder_system)
        elif gimmick_type == "plunder_system":
            gold = getattr(character, 'plundered_gold', 0)
            details.append("=== 약탈 시스템 ===")
            gauge_bar = self._create_gauge_bar(gold, 200, width=10, optimal_min=100, optimal_max=200)
            details.append(f"약탈한 골드: {gauge_bar}")
            if gold >= 100:
                details.append(" 대박! 강화 스킬 가능")

        else:
            return "기믹 상세 정보 없음"

        return "\n".join(details)

        return ""

    def _render_item_menu(self, console: tcod.console.Console):
        """아이템 메뉴 렌더링"""
        if self.item_menu:
            self.item_menu.render(console)

    def _render_battle_end(self, console: tcod.console.Console):
        """전투 종료 화면 렌더링"""
        if self.battle_result == CombatState.VICTORY:
            msg = "승리!"
            color = (255, 255, 100)
        elif self.battle_result == CombatState.DEFEAT:
            msg = "패배..."
            color = (255, 100, 100)
        else:
            msg = "도망쳤다"
            color = (200, 200, 200)

        console.print(
            self.screen_width // 2 - len(msg) // 2,
            self.screen_height // 2,
            msg,
            fg=color
        )

        console.print(
            self.screen_width // 2 - 10,
            self.screen_height // 2 + 2,
            "아무 키나 눌러 계속...",
            fg=(180, 180, 180)
        )


def run_combat(
    console: tcod.console.Console,
    context: tcod.context.Context,
    party: List[Any],
    enemies: List[Any],
    inventory: Optional[Any] = None,
    session: Optional[Any] = None,
    network_manager: Optional[Any] = None,
    combat_position: Optional[Tuple[int, int]] = None,
    bot_manager: Optional[Any] = None,  # 봇 관리자 (자동 전투용)
    local_player_id: Optional[str] = None  # 로컬 플레이어 ID (다른 플레이어 컨트롤 방지)
) -> CombatState:
    """
    전투 실행

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        party: 아군 파티
        enemies: 적군 리스트
        inventory: 인벤토리 (아이템 사용용)
        session: 멀티플레이 세션 (선택적)
        network_manager: 네트워크 관리자 (선택적)
        combat_position: 전투 시작 위치 (선택적, 멀티플레이용)

    Returns:
        전투 결과 (승리/패배/도주)
    """
    # 전투 시작 SFX (Battle Swirl)
    play_sfx("combat", "battle_start")

    # 적 타입에 따라 BGM 선택
    # 1. 세피로스 확인
    is_sephiroth = any(hasattr(e, 'enemy_id') and e.enemy_id == "sephiroth" for e in enemies)
    # 2. 보스 확인 (enemy_id가 "boss_"로 시작)
    is_boss = any(hasattr(e, 'enemy_id') and e.enemy_id.startswith("boss_") for e in enemies)

    if is_sephiroth:
        # 세피로스전: One-Winged Angel 고정
        selected_bgm = "battle_final_boss"
    elif is_boss:
        # 보스전: battle_boss만 재생
        selected_bgm = "battle_boss"
    else:
        # 일반 전투: 2개 중 랜덤 (battle_boss 제외)
        battle_bgm_tracks = [
            "battle_jenova_absolute",   # 85-Jenova Absolute
            "battle_normal"             # 11-Fighting
        ]
        selected_bgm = random.choice(battle_bgm_tracks)

    play_bgm(selected_bgm, loop=True, fade_in=True)

    # 멀티플레이 모드 확인
    from src.multiplayer.game_mode import get_game_mode_manager
    game_mode_manager = get_game_mode_manager()
    is_multiplayer = game_mode_manager and game_mode_manager.is_multiplayer() if game_mode_manager else False
    
    # 전투 매니저 생성
    combat_manager = CombatManager()
    
    # 멀티플레이 세션 설정 (게임오버 조건 체크용)
    if is_multiplayer and session:
        combat_manager.session = session
    
    # 전투 위치 설정 (멀티플레이용)
    if combat_position:
        combat_manager.combat_position = combat_position
        # 전투 ID 생성 (위치 기반)
        import hashlib
        position_str = f"{combat_position[0]},{combat_position[1]}"
        combat_id = hashlib.md5(position_str.encode()).hexdigest()[:8]
        combat_manager.combat_id = combat_id
    
    # 멀티플레이 모드일 때 ATB 시스템을 MultiplayerATBSystem으로 교체
    if is_multiplayer:
        from src.multiplayer.atb_multiplayer import MultiplayerATBSystem
        if not isinstance(combat_manager.atb, MultiplayerATBSystem):
            # 기존 게이지와 전투원 보존
            old_gauges = combat_manager.atb.gauges.copy()
            old_combatants = combat_manager.atb.combatants.copy()
            old_enabled = combat_manager.atb.enabled
            
            # 새 멀티플레이 ATB 시스템 생성
            new_atb = MultiplayerATBSystem()
            # 기존 설정 복원
            new_atb.enabled = old_enabled
            
            # 게이지와 전투원 복원
            new_atb.gauges = old_gauges
            new_atb.combatants = old_combatants
            # 평균 속도 재계산
            new_atb._update_average_speed()
            
            # ATB 시스템 교체
            combat_manager.atb = new_atb
            logger.info(f"🔧 멀티플레이 전투: ATB 시스템을 MultiplayerATBSystem으로 교체 (게이지 {len(old_gauges)}개 복원)")
        else:
            logger.info("멀티플레이 ATB 시스템 이미 활성화됨")
    
    combat_manager.start_combat(party, enemies)
    
    # 인벤토리 설정 (전투 매니저에도 전달)
    if inventory:
        combat_manager.inventory = inventory

    # 로컬 플레이어 ID 확인
    if not local_player_id:
        if session:
            local_player_id = getattr(session, 'local_player_id', None)
        if not local_player_id and game_mode_manager:
            local_player_id = getattr(game_mode_manager, 'local_player_id', None)
    
    # 전투 UI 생성 (멀티플레이 모드일 경우 session과 network_manager 전달)
    if is_multiplayer and session and network_manager:
        ui = CombatUI(
            console.width, 
            console.height, 
            combat_manager, 
            inventory=inventory,
            session=session,
            network_manager=network_manager,
            bot_manager=bot_manager,  # 봇 관리자 전달
            local_player_id=local_player_id  # 로컬 플레이어 ID 전달
        )
        logger.info(f"멀티플레이 전투 UI 생성: 세션={session.session_id if session else None}, 로컬 플레이어={local_player_id}")
    else:
        ui = CombatUI(
            console.width, 
            console.height, 
            combat_manager, 
            inventory=inventory,
            bot_manager=bot_manager,  # 봇 관리자 전달
            local_player_id=local_player_id  # 로컬 플레이어 ID 전달 (싱글플레이도 전달)
        )
    
    handler = InputHandler()

    logger.info(f"전투 시작: 아군 {len(party)}명 vs 적군 {len(enemies)}명 (BGM: {selected_bgm})")

    # 전투 루프
    while not ui.battle_ended:
        # 업데이트
        ui.update(delta_time=1.0)

        # 렌더링
        ui.render(console)
        context.present(console)

        # 입력 처리
        for event in tcod.event.wait(timeout=0.016):  # ~60 FPS
            action = handler.dispatch(event)

            if action:
                if ui.handle_input(action):
                    break

            # 윈도우 닫기는 무시 (전투 중에는 도주 명령으로만 종료 가능)
            # if isinstance(event, tcod.event.Quit):
            #     return CombatState.FLED

    logger.info(f"전투 종료: {ui.battle_result.value if ui.battle_result else 'unknown'}")

    # BGM은 main.py에서 처리 (필드 BGM으로 전환하기 위해)
    return ui.battle_result or CombatState.FLED
