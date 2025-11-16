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
        combat_manager: CombatManager
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.combat_manager = combat_manager

        # UI 상태
        self.state = CombatUIState.WAITING_ATB
        self.current_actor: Optional[Any] = None
        self.selected_action: Optional[ActionType] = None
        self.selected_skill: Optional[Any] = None
        self.selected_target: Optional[Any] = None

        # 메시지 로그
        self.messages: List[CombatMessage] = []
        self.max_messages = 5

        # 메뉴
        self.action_menu: Optional[CursorMenu] = None
        self.skill_menu: Optional[CursorMenu] = None
        self.target_cursor = 0
        self.current_target_list: List[Any] = []  # 현재 타겟 선택 리스트

        # 전투 종료 플래그
        self.battle_ended = False
        self.battle_result: Optional[CombatState] = None

        # 기믹 상세 보기
        self.gimmick_view_character: Optional[Any] = None
        self.previous_state: Optional[CombatUIState] = None

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
        all_skills = getattr(actor, 'skills', [])

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

            # 비용 정보 표시
            cost_parts = []
            for cost in skill.costs:
                if hasattr(cost, 'get_description'):
                    cost_desc = cost.get_description(actor)
                    if cost_desc:
                        cost_parts.append(cost_desc)

            cost_text = f" ({', '.join(cost_parts)})" if cost_parts else ""

            name = getattr(skill, 'name', str(skill))
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
            self._execute_current_action()
        elif action == GameAction.CANCEL:
            # 취소 - 이전 상태로
            if self.selected_action == ActionType.SKILL:
                self.state = CombatUIState.SKILL_MENU
            else:
                self.state = CombatUIState.ACTION_MENU
            self.selected_skill = None

        return False

    def _handle_item_menu(self, action: GameAction) -> bool:
        """아이템 메뉴 입력 처리"""
        if action == GameAction.CANCEL:
            self.state = CombatUIState.ACTION_MENU
        elif action == GameAction.CONFIRM:
            # 아이템 시스템 구현 (인벤토리에서 선택)
            # 현재는 간단한 메시지 표시
            self.add_message("아이템 메뉴 (인벤토리 UI 연동 필요)", (200, 200, 200))
            # 실제 구현 시: 인벤토리 UI를 표시하고 아이템 선택
            # selected_item = inventory_ui.show()
            # if selected_item:
            #     self.selected_action = ("item", selected_item)
            #     self.state = CombatUIState.TARGET_SELECTION
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
        if self.selected_skill and hasattr(self.selected_skill, 'target_type'):
            target_type = self.selected_skill.target_type

            # 문자열 target_type을 Enum으로 매핑 (하위 호환성)
            ally_targets = (
                SkillTargetType.SINGLE_ALLY,
                SkillTargetType.SELF,
                SkillTargetType.ALL_ALLIES,
                "ally",      # 문자열 지원
                "self",      # 문자열 지원
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

        result = self.combat_manager.execute_action(
            actor=self.current_actor,
            action_type=action_type,
            target=self.selected_target,
            skill=self.selected_skill
        )

        # 결과 메시지 표시
        self._show_action_result(result)

        # 상태 초기화
        self.current_actor = None
        self.selected_action = None
        self.selected_skill = None
        self.selected_target = None
        self.state = CombatUIState.WAITING_ATB

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
                self.add_message(message, (100, 255, 255))
            else:
                error = result.get("error", "사용 실패")
                self.add_message(f"❌ {skill_name}: {error}", (255, 100, 100))

    def update(self, delta_time: float = 1.0):
        """업데이트 (매 프레임)"""
        # 플레이어가 선택 중인지 확인
        is_player_selecting = self.state in [
            CombatUIState.ACTION_MENU,
            CombatUIState.SKILL_MENU,
            CombatUIState.TARGET_SELECT,
            CombatUIState.ITEM_MENU
        ]

        # 플레이어가 선택 중일 때는 ATB 증가를 멈춤
        if is_player_selecting:
            # ATB 업데이트 스킵 (시간 정지)
            # 플레이어 턴으로 표시하여 ATB 증가 방지
            self.combat_manager.state = CombatState.PLAYER_TURN
        else:
            # 일반 진행
            if self.combat_manager.state == CombatState.PLAYER_TURN:
                self.combat_manager.state = CombatState.IN_PROGRESS

        # 전투 매니저 업데이트
        self.combat_manager.update(delta_time)

        # 전투 종료 확인
        if self.combat_manager.state in [CombatState.VICTORY, CombatState.DEFEAT, CombatState.FLED]:
            if not self.battle_ended:
                self.battle_ended = True
                self.battle_result = self.combat_manager.state
                self.state = CombatUIState.BATTLE_END
                logger.info(f"전투 종료 감지: {self.battle_result.value}")

        # 메시지 타이머 감소
        for msg in self.messages:
            msg.frames_remaining -= 1

        # 만료된 메시지 제거
        self.messages = [m for m in self.messages if m.frames_remaining > 0]

        # ATB 대기 중 - 턴 체크
        if self.state == CombatUIState.WAITING_ATB:
            self._check_ready_combatants()

    def _check_ready_combatants(self):
        """행동 가능한 전투원 확인"""
        ready = self.combat_manager.atb.get_action_order()

        if not ready:
            return

        # 아군 턴
        for combatant in ready:
            if combatant in self.combat_manager.allies:
                # 아군 턴 시작 SFX
                play_sfx("combat", "turn_start")

                self.current_actor = combatant
                self.action_menu = self._create_action_menu(self.current_actor)  # actor 전달
                self.state = CombatUIState.ACTION_MENU
                self.add_message(f"{combatant.name}의 턴!", (100, 255, 255))
                return

        # 적군 턴 (AI)
        for combatant in ready:
            if combatant in self.combat_manager.enemies:
                self._execute_enemy_turn(combatant)
                return

    def _execute_enemy_turn(self, enemy: Any):
        """적 턴 실행 (간단한 AI)"""
        # 간단한 AI: 랜덤 대상에게 BRV 공격 또는 HP 공격
        import random

        allies_alive = [a for a in self.combat_manager.allies if a.is_alive]
        if not allies_alive:
            return

        target = random.choice(allies_alive)

        # BRV가 충분하면 HP 공격, 아니면 BRV 공격
        if enemy.current_brv > 500:
            action = ActionType.HP_ATTACK
        else:
            action = ActionType.BRV_ATTACK

        self.add_message(f"{enemy.name}의 공격!", (255, 150, 150))

        result = self.combat_manager.execute_action(
            actor=enemy,
            action_type=action,
            target=target
        )

        self._show_action_result(result)

        # 전투 종료 확인
        if self.combat_manager.state in [CombatState.VICTORY, CombatState.DEFEAT]:
            self.battle_ended = True
            self.battle_result = self.combat_manager.state
            self.state = CombatUIState.BATTLE_END

    def add_message(self, text: str, color: Tuple[int, int, int] = (255, 255, 255)):
        """메시지 추가"""
        msg = CombatMessage(text=text, color=color)
        self.messages.append(msg)

        # 최대 개수 초과 시 오래된 것 제거
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

        logger.debug(f"전투 메시지: {text}")

    def render(self, console: tcod.console.Console):
        """렌더링"""
        console.clear()

        # 제목
        console.print(
            self.screen_width // 2 - 5,
            1,
            "⚔ 전투 ⚔",
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

            # 현재 행동 중인 캐릭터 표시
            turn_indicator = "▶ " if ally == self.current_actor else "  "
            console.print(3, y, turn_indicator, fg=(255, 255, 100))

            console.print(5, y, f"{i+1}. {ally.name}", fg=name_color)

            # 직업 및 기믹 상태 표시
            gimmick_text = self._get_gimmick_display(ally)
            if gimmick_text:
                console.print(5 + len(f"{i+1}. {ally.name}") + 2, y, gimmick_text, fg=(150, 255, 200))

            # 상태이상 아이콘
            status_effects = getattr(ally, 'status_effects', {})
            if status_effects:
                status_text = gauge_renderer.render_status_icons(status_effects)
                console.print(5 + len(ally.name) + 4, y, status_text, fg=(200, 200, 255))

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

            # 캐스팅 중이면 스킬 이름 표시
            if cast_info:
                skill_name = getattr(cast_info.skill, 'name', 'Unknown')
                console.print(8, y + 4, f"⏳ 시전: {skill_name}", fg=(200, 100, 255))

            # BREAK 상태 표시
            if self.combat_manager.brave.is_broken(ally):
                console.print(8, y + 4, "💔 BREAK!", fg=(255, 50, 50))

    def _render_enemies(self, console: tcod.console.Console):
        """적군 상태 렌더링 (상세)"""
        console.print(self.screen_width - 30, 4, "[적군]", fg=(255, 100, 100))

        for i, enemy in enumerate(self.combat_manager.enemies):
            y = 6 + i * 6
            x = self.screen_width - 30

            # 이름
            name_color = (255, 255, 255) if enemy.is_alive else (100, 100, 100)

            # 대상 선택 커서 또는 턴 표시
            if enemy == self.current_actor:
                # 현재 행동 중인 적
                cursor = "⚔ "
                cursor_color = (255, 100, 100)
            elif self.state == CombatUIState.TARGET_SELECT and i == self.target_cursor:
                # 타겟팅 중
                cursor = "▶ "
                cursor_color = (255, 255, 100)
            else:
                cursor = "  "
                cursor_color = name_color

            console.print(x, y, cursor, fg=cursor_color)
            console.print(x + 2, y, f"{chr(65+i)}. {enemy.name}", fg=name_color)

            # 기믹 상태 표시 (룬 스택 등)
            gimmick_text = self._get_gimmick_display(enemy)
            if gimmick_text:
                console.print(x + 2 + len(f"{chr(65+i)}. {enemy.name}") + 1, y, gimmick_text, fg=(150, 255, 200))

            # 상태이상
            status_effects = getattr(enemy, 'status_effects', [])
            if status_effects:
                status_text = gauge_renderer.render_status_icons(status_effects)
                if status_text:
                    console.print(x, y + 1, status_text, fg=(200, 200, 255))

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
        """메시지 로그 렌더링"""
        msg_y = 28
        console.print(5, msg_y, "─" * (self.screen_width - 10), fg=(100, 100, 100))

        for i, msg in enumerate(self.messages[-self.max_messages:]):
            console.print(5, msg_y + 1 + i, msg.text, fg=msg.color)

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

    def _get_gimmick_display(self, character: Any) -> str:
        """캐릭터의 기믹 상태를 문자열로 반환"""
        gimmick_type = getattr(character, 'gimmick_type', None)
        if not gimmick_type:
            return ""

        # 기믹 타입별 상태 표시
        if gimmick_type == "stance_system":
            # 전사 - 스탠스
            stance = getattr(character, 'current_stance', 0)
            stance_names = ["기본", "공격", "방어", "신속", "균형", "최종"]
            if 0 <= stance < len(stance_names):
                return f"[{stance_names[stance]}]"

        elif gimmick_type == "elemental_counter":
            # 아크메이지 - 원소 카운터
            fire = getattr(character, 'fire_element', 0)
            ice = getattr(character, 'ice_element', 0)
            lightning = getattr(character, 'lightning_element', 0)
            return f"[화염{fire} 냉기{ice} 번개{lightning}]"

        elif gimmick_type == "support_fire_system":
            # 궁수 - 지원사격
            marked_allies = getattr(character, 'marked_allies', [])
            combo = getattr(character, 'combo_count', 0)
            return f"[지원:{len(marked_allies)}/3 콤보:{combo}]"

        elif gimmick_type == "magazine_system":
            # 저격수 - 탄창
            magazine = getattr(character, 'magazine', [])
            return f"[탄창:{len(magazine)}/6]"

        elif gimmick_type == "venom_system":
            # 도적 - 베놈
            venom = getattr(character, 'venom_power', 0)
            return f"[독:{venom}]"

        elif gimmick_type == "shadow_system":
            # 암살자 - 그림자
            shadows = getattr(character, 'shadow_count', 0)
            max_shadows = getattr(character, 'max_shadow_count', 5)
            return f"[그림자:{shadows}/{max_shadows}]"

        elif gimmick_type == "sword_aura":
            # 검성 - 검기
            aura = getattr(character, 'sword_aura', 0)
            max_aura = getattr(character, 'max_sword_aura', 5)
            return f"[검기:{aura}/{max_aura}]"

        elif gimmick_type == "rage_system":
            # 광전사 - 분노
            rage = getattr(character, 'rage_stacks', 0)
            max_rage = getattr(character, 'max_rage_stacks', 10)
            return f"[분노:{rage}/{max_rage}]"

        elif gimmick_type == "ki_system":
            # 몽크 - 기
            ki = getattr(character, 'ki_energy', 0)
            max_ki = getattr(character, 'max_ki_energy', 100)
            return f"[기:{ki}/{max_ki}]"

        elif gimmick_type == "melody_system":
            # 바드 - 멜로디
            melody = getattr(character, 'melody_stacks', 0)
            max_melody = getattr(character, 'max_melody_stacks', 7)
            return f"[♪:{melody}/{max_melody}]"

        elif gimmick_type == "necro_system":
            # 네크로맨서 - 네크로 에너지
            necro = getattr(character, 'necro_energy', 0)
            max_necro = getattr(character, 'max_necro_energy', 50)
            return f"[사령:{necro}/{max_necro}]"

        elif gimmick_type == "totem_system":
            # 무당 - 저주
            curses = getattr(character, 'curse_stacks', 0)
            max_curses = getattr(character, 'max_curse_stacks', 10)
            return f"[저주:{curses}/{max_curses}]"

        elif gimmick_type == "wisdom_system":
            # 철학자 - 지혜
            knowledge = getattr(character, 'knowledge_stacks', 0)
            max_knowledge = getattr(character, 'max_knowledge_stacks', 10)
            return f"[지혜:{knowledge}/{max_knowledge}]"

        elif gimmick_type == "time_system":
            # 시간술사 - 시간 기록점
            time = getattr(character, 'time_marks', 0)
            max_time = getattr(character, 'max_time_marks', 7)
            return f"[시간:{time}/{max_time}]"

        elif gimmick_type == "alchemy_system":
            # 연금술사 - 물약
            potions = getattr(character, 'potion_stock', 0)
            max_potions = getattr(character, 'max_potion_stock', 10)
            return f"[물약:{potions}/{max_potions}]"

        elif gimmick_type == "blood_system":
            # 흡혈귀 - 혈액
            blood = getattr(character, 'blood_pool', 0)
            max_blood = getattr(character, 'max_blood_pool', 100)
            return f"[혈액:{blood}/{max_blood}]"

        elif gimmick_type == "hack_system":
            # 해커 - 해킹
            hacks = getattr(character, 'hack_stacks', 0)
            max_hacks = getattr(character, 'max_hack_stacks', 5)
            return f"[해킹:{hacks}/{max_hacks}]"

        elif gimmick_type == "darkness_system":
            # 암흑기사 - 어둠
            darkness = getattr(character, 'darkness', 0)
            return f"[어둠:{darkness}]"

        elif gimmick_type == "holy_system":
            # 성기사/신관 - 신성력
            holy = getattr(character, 'holy_power', 0)
            max_holy = getattr(character, 'max_holy_power', 100)
            return f"[신성:{holy}/{max_holy}]"

        elif gimmick_type == "rune_system":
            # 전투마법사 - 룬
            runes = getattr(character, 'rune_stacks', 0)
            max_runes = getattr(character, 'max_rune_stacks', 8)
            return f"[룬:{runes}/{max_runes}]"

        elif gimmick_type == "dimension_system":
            # 차원술사 - 차원력
            dimension = getattr(character, 'dimension_points', 0)
            max_dimension = getattr(character, 'max_dimension_points', 100)
            return f"[차원:{dimension}/{max_dimension}]"

        elif gimmick_type == "construct_system":
            # 기계공학자 - 부품
            parts = getattr(character, 'machine_parts', 0)
            max_parts = getattr(character, 'max_machine_parts', 5)
            return f"[부품:{parts}/{max_parts}]"

        elif gimmick_type == "duty_system":
            # 기사 - 의무
            duty = getattr(character, 'duty_stacks', 0)
            max_duty = getattr(character, 'max_duty_stacks', 10)
            return f"[의무:{duty}/{max_duty}]"

        elif gimmick_type == "stealth_system":
            # 암살자 - 은신
            stealth = getattr(character, 'stealth_points', 0)
            max_stealth = getattr(character, 'max_stealth_points', 5)
            return f"[은신:{stealth}/{max_stealth}]"

        elif gimmick_type == "theft_system":
            # 도적 - 절도
            stolen = getattr(character, 'stolen_items', 0)
            return f"[절도:{stolen}]"

        elif gimmick_type == "plunder_system":
            # 해적 - 약탈
            gold = getattr(character, 'gold', 0)
            return f"[골드:{gold}]"

        elif gimmick_type == "iaijutsu_system":
            # 사무라이 - 거합
            will = getattr(character, 'will_gauge', 0)
            max_will = getattr(character, 'max_will_gauge', 100)
            return f"[기합:{will}/{max_will}]"

        elif gimmick_type == "enchant_system":
            # 마검사 - 마력 부여
            mana = getattr(character, 'mana_blade', 0)
            max_mana = getattr(character, 'max_mana_blade', 100)
            return f"[마검:{mana}/{max_mana}]"

        elif gimmick_type == "divinity_system":
            # 프리스트/클레릭 - 신성력
            judgment = getattr(character, 'judgment_points', 0)
            faith = getattr(character, 'faith_points', 0)
            return f"[심판:{judgment} 신앙:{faith}]"

        elif gimmick_type == "shapeshifting_system":
            # 드루이드 - 변신
            nature = getattr(character, 'nature_points', 0)
            form = getattr(character, 'current_form', None)
            if form:
                return f"[{form}형태 {nature}]"
            return f"[자연:{nature}]"

        elif gimmick_type == "spirit_bond":
            # 정령술사 - 정령 친화도
            bond = getattr(character, 'spirit_bond', 0)
            max_bond = getattr(character, 'max_spirit_bond', 25)
            spirits = getattr(character, 'spirit_count', 0)
            return f"[친화:{bond}/{max_bond} 정령:{spirits}]"

        elif gimmick_type == "dragon_marks":
            # 용기사 - 용의 표식
            marks = getattr(character, 'dragon_marks', 0)
            max_marks = getattr(character, 'max_dragon_marks', 3)
            power = getattr(character, 'dragon_power', 0)
            return f"[용표:{marks}/{max_marks} 용력:{power}]"

        elif gimmick_type == "arena_system":
            # 검투사 - 투기장
            arena = getattr(character, 'arena_points', 0)
            glory = getattr(character, 'glory_points', 0)
            kills = getattr(character, 'kill_count', 0)
            return f"[투기:{arena} 영광:{glory} 처치:{kills}]"

        elif gimmick_type == "break_system":
            # 브레이커 - 파괴력
            break_power = getattr(character, 'break_power', 0)
            max_break = getattr(character, 'max_break_power', 10)
            return f"[파괴:{break_power}/{max_break}]"

        # === 15개 신규 기믹 시스템 (간략 표시) ===

        elif gimmick_type == "yin_yang_flow":
            # 몽크 - 음양 흐름 (간략: 게이지만)
            ki = getattr(character, 'ki_gauge', 50)
            return f"[기:{ki}]"

        elif gimmick_type == "rune_resonance":
            # 배틀메이지 - 룬 공명 (간략: 총합)
            fire = getattr(character, 'rune_fire', 0)
            ice = getattr(character, 'rune_ice', 0)
            lightning = getattr(character, 'rune_lightning', 0)
            total = fire + ice + lightning
            return f"[룬:{total}]"

        elif gimmick_type == "probability_distortion":
            # 차원술사 - 확률 왜곡 (간략: 게이지)
            gauge = getattr(character, 'distortion_gauge', 0)
            return f"[왜곡:{gauge}]"

        elif gimmick_type == "heat_gauge":
            # 엔지니어 - 열 게이지 (간략: 상태)
            heat = getattr(character, 'heat', 0)
            if heat > 70:
                return f"[⚠열:{heat}]"
            else:
                return f"[열:{heat}]"

        elif gimmick_type == "thirst_gauge":
            # 뱀파이어 - 갈증 (간략: 게이지)
            thirst = getattr(character, 'thirst', 0)
            if thirst > 70:
                return f"[💧:{thirst}]"
            else:
                return f"[갈증:{thirst}]"

        elif gimmick_type == "madness_gauge":
            # 버서커 - 광기 (간략: 게이지)
            madness = getattr(character, 'madness', 0)
            if madness > 70:
                return f"[⚡광:{madness}]"
            else:
                return f"[광기:{madness}]"

        elif gimmick_type == "spirit_resonance":
            # 정령술사 - 정령 (간략: 활성 정령 수)
            fire = getattr(character, 'spirit_fire', 0)
            water = getattr(character, 'spirit_water', 0)
            wind = getattr(character, 'spirit_wind', 0)
            earth = getattr(character, 'spirit_earth', 0)
            active = sum([1 for s in [fire, water, wind, earth] if s > 0])
            return f"[정령:{active}]"

        elif gimmick_type == "stealth_mastery":
            # 암살자 - 은신 (간략: 상태만)
            stealth_active = getattr(character, 'stealth_active', False)
            return "[🌑]" if stealth_active else "[👁]"

        elif gimmick_type == "dilemma_choice":
            # 철학자 - 선택 (간략: 총 선택 수)
            power = getattr(character, 'choice_power', 0)
            wisdom = getattr(character, 'choice_wisdom', 0)
            sacrifice = getattr(character, 'choice_sacrifice', 0)
            truth = getattr(character, 'choice_truth', 0)
            total = power + wisdom + sacrifice + truth
            return f"[선택:{total}]"

        elif gimmick_type == "support_fire":
            # 궁수 - 지원사격 (간략: 콤보)
            combo = getattr(character, 'support_fire_combo', 0)
            return f"[지원:{combo}]"

        elif gimmick_type == "hack_threading":
            # 해커 - 스레드 (간략: 스레드 수)
            threads = getattr(character, 'active_threads', 0)
            return f"[스레드:{threads}]"

        elif gimmick_type == "cheer_gauge":
            # 검투사 - 환호 (간략: 게이지)
            cheer = getattr(character, 'cheer', 0)
            if cheer > 70:
                return f"[📢:{cheer}]"
            else:
                return f"[환호:{cheer}]"

        return ""

    def _render_gimmick_view(self, console: tcod.console.Console):
        """기믹 상세 보기 렌더링 (박스 스타일)"""
        if not self.gimmick_view_character:
            return

        character = self.gimmick_view_character
        gimmick_type = getattr(character, 'gimmick_type', None)

        # 박스 위치 및 크기
        box_width = 50
        box_height = 20
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
                console.print(content_x, content_y + line, "💥 상태: 오버히트!", fg=(255, 50, 50))
                line += 1
                console.print(content_x, content_y + line, "⚠️  스턴 2턴, 열 0으로 리셋", fg=(255, 100, 100))
            elif heat >= 80:
                console.print(content_x, content_y + line, "🔥 열 상태: 위험 구간", fg=(255, 200, 100))
                line += 1
                console.print(content_x, content_y + line, "⚡ 효과: 공격력 +50%, 크리티컬 +15%", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, "⚠️  받는 피해 +20%, 명중률 -10%", fg=(255, 150, 100))
            elif heat >= 50:
                console.print(content_x, content_y + line, "🔥 열 상태: 최적 구간", fg=(100, 255, 100))
                line += 1
                console.print(content_x, content_y + line, "⚡ 효과: 공격력 +30%, 스킬 효과 +20%", fg=(255, 255, 100))
            else:
                console.print(content_x, content_y + line, "❄️  열 상태: 냉각 구간", fg=(150, 150, 255))
                line += 1
                console.print(content_x, content_y + line, "⚡ 효과: 일반 공격력", fg=(200, 200, 200))
            line += 1

            # 다음 턴 예측
            next_heat = heat + (5 if heat >= 50 else 0)
            console.print(content_x, content_y + line, f"📊 다음 턴 자동 열 증가: +{5 if heat >= 50 else 0} (예상: {min(next_heat, 100)})", fg=(150, 200, 255))

        elif gimmick_type == "yin_yang_flow":
            # 몽크 - 음양 흐름
            ki = getattr(character, 'ki_gauge', 50)
            min_ki = getattr(character, 'min_ki', 0)
            max_ki = getattr(character, 'max_ki', 100)

            console.print(content_x, content_y + line, "🥋 몽크 - 음양 기 흐름", fg=(255, 215, 0))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 음양 게이지
            console.print(content_x, content_y + line, "[陰]        [☯]        [陽]", fg=(200, 200, 200))
            line += 1
            # 게이지 바 (음=파랑, 양=빨강, 균형=금색)
            if ki < 40:
                gauge_color = (100, 150, 255)  # 파랑 (음)
            elif ki <= 60:
                gauge_color = (255, 215, 0)  # 금색 (균형)
            else:
                gauge_color = (255, 100, 100)  # 빨강 (양)
            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, ki, max_ki, show_numbers=True, custom_color=gauge_color)
            line += 1

            # 상태 정보
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if ki < 25:
                console.print(content_x, content_y + line, "🌟 상태: 음 (陰) 기운 특화", fg=(100, 150, 255))
                line += 1
                console.print(content_x, content_y + line, "⚡ 효과: 방어력 +50%, MP 회복 +100%", fg=(150, 200, 255))
                line += 1
                console.print(content_x, content_y + line, "   받는 피해 -30%", fg=(150, 200, 255))
            elif ki > 75:
                console.print(content_x, content_y + line, "🌟 상태: 양 (陽) 기운 특화", fg=(255, 100, 100))
                line += 1
                console.print(content_x, content_y + line, "⚡ 효과: 공격력 +40%, 속도 +30%", fg=(255, 200, 100))
                line += 1
                console.print(content_x, content_y + line, "   크리티컬 확률 +20%", fg=(255, 200, 100))
            else:
                console.print(content_x, content_y + line, "🌟 상태: 태극 조화 (균형)", fg=(255, 215, 0))
                line += 1
                console.print(content_x, content_y + line, "⚡ 효과: 모든 스탯 +20%", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, "   음양 스킬 강화 +30%", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, "   HP/MP 회복 매 턴 5%", fg=(255, 255, 100))

        elif gimmick_type == "rune_resonance":
            # 배틀메이지 - 룬 공명
            fire = getattr(character, 'rune_fire', 0)
            ice = getattr(character, 'rune_ice', 0)
            lightning = getattr(character, 'rune_lightning', 0)
            max_rune = getattr(character, 'max_rune_per_type', 3)

            console.print(content_x, content_y + line, "⚔️🔮 배틀메이지 - 룬 공명", fg=(200, 100, 255))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 룬 상태
            console.print(content_x, content_y + line, f"🔥 화염 룬: {fire}/{max_rune}", fg=(255, 100, 50))
            line += 1
            console.print(content_x, content_y + line, f"❄️  냉기 룬: {ice}/{max_rune}", fg=(100, 200, 255))
            line += 1
            console.print(content_x, content_y + line, f"⚡ 번개 룬: {lightning}/{max_rune}", fg=(255, 255, 100))
            line += 1

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
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
                console.print(content_x, content_y + line, "💡 룬 축적 필요", fg=(150, 150, 150))

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
            console.print(content_x, content_y + line, "⚡ 사용 가능한 확률 왜곡:", fg=(255, 255, 100))
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

            if thirst > 90:
                console.print(content_x, content_y + line, "💧 상태: 혈액 광란 (위험!)", fg=(255, 50, 50))
                line += 1
                console.print(content_x, content_y + line, "⚠️  통제 불가, 아군도 공격!", fg=(255, 100, 100))
            elif thirst > 60:
                console.print(content_x, content_y + line, "💧 상태: 극심한 갈증", fg=(255, 150, 150))
                line += 1
                console.print(content_x, content_y + line, "⚡ 공격력 +70%, 흡혈 3배, 속도 +50%", fg=(255, 200, 200))
            elif thirst > 30:
                console.print(content_x, content_y + line, "💧 상태: 갈증", fg=(200, 150, 150))
                line += 1
                console.print(content_x, content_y + line, "⚡ 공격력 +30%, 흡혈 2배", fg=(255, 255, 200))
            else:
                console.print(content_x, content_y + line, "💧 상태: 만족", fg=(150, 255, 150))
                line += 1
                console.print(content_x, content_y + line, "⚡ 정상 상태", fg=(200, 200, 200))
            line += 1
            console.print(content_x, content_y + line, f"📊 다음 턴 자동 증가: +10 (예상: {min(thirst + 10, max_thirst)})", fg=(150, 200, 255))

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
                console.print(content_x, content_y + line, "⚡ 상태: 폭주!", fg=(255, 50, 50))
                line += 1
                console.print(content_x, content_y + line, "⚠️  3턴간 통제 불가, 공격력 +200%!", fg=(255, 100, 100))
            elif madness > 70:
                console.print(content_x, content_y + line, "⚡ 상태: 위험 구간", fg=(255, 150, 100))
                line += 1
                console.print(content_x, content_y + line, "⚡ 공격력 +100%, 받는 피해 +50%", fg=(255, 200, 100))
            elif madness >= 30:
                console.print(content_x, content_y + line, "⚡ 상태: 광전사 모드", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, "⚡ 공격력 +60%", fg=(255, 255, 100))
            else:
                console.print(content_x, content_y + line, "⚡ 상태: 정상", fg=(200, 200, 200))

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
            console.print(content_x, content_y + line, f"🔥 화염 정령: {'활성화' if fire > 0 else '비활성'}", fg=(255, 100, 50) if fire > 0 else (100, 100, 100))
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
                console.print(content_x, content_y + line, "💡 정령 소환 필요", fg=(150, 150, 150))

        elif gimmick_type == "stealth_mastery":
            # 암살자 - 은신 숙련
            stealth_active = getattr(character, 'stealth_active', False)
            shadow_strike = getattr(character, 'shadow_strike_ready', False)

            console.print(content_x, content_y + line, "🗡️ 암살자 - 은신 숙련", fg=(100, 100, 150))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 2

            if stealth_active:
                console.print(content_x + 10, content_y + line, "🌑 은신 중", fg=(100, 100, 200))
                line += 2
                console.print(content_x, content_y + line, "⚡ 회피율 +80%", fg=(150, 200, 255))
                line += 1
                console.print(content_x, content_y + line, "⚡ 다음 공격 크리티컬 확정", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, "⚠️  공격 시 은신 해제", fg=(200, 150, 100))
            elif shadow_strike:
                console.print(content_x + 8, content_y + line, "👁 그림자 공격 준비", fg=(150, 150, 200))
                line += 2
                console.print(content_x, content_y + line, "⚡ 암살 기술 사용 가능", fg=(255, 200, 100))
            else:
                console.print(content_x + 12, content_y + line, "👁 노출", fg=(200, 200, 200))
                line += 2
                console.print(content_x, content_y + line, "💡 은신 스킬로 재진입 가능", fg=(150, 200, 255))

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

            console.print(content_x, content_y + line, f"⚔️  힘의 선택: {power}", fg=(255, 100, 100))
            line += 1
            console.print(content_x, content_y + line, f"📖 지혜의 선택: {wisdom}", fg=(100, 200, 255))
            line += 1
            console.print(content_x, content_y + line, f"💔 희생의 선택: {sacrifice}", fg=(200, 100, 200))
            line += 1
            console.print(content_x, content_y + line, f"✨ 진리의 선택: {truth}", fg=(255, 255, 100))
            line += 1

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 경향 분석
            dominant = max(power, wisdom, sacrifice, truth)
            if dominant == 0:
                console.print(content_x, content_y + line, "💡 선택 대기 중", fg=(150, 150, 150))
            else:
                if power == dominant:
                    console.print(content_x, content_y + line, "📊 경향: 힘 중심", fg=(255, 100, 100))
                elif wisdom == dominant:
                    console.print(content_x, content_y + line, "📊 경향: 지혜 중심", fg=(100, 200, 255))
                elif sacrifice == dominant:
                    console.print(content_x, content_y + line, "📊 경향: 희생 중심", fg=(200, 100, 200))
                else:
                    console.print(content_x, content_y + line, "📊 경향: 진리 중심", fg=(255, 255, 100))

        elif gimmick_type == "support_fire":
            # 궁수 - 지원사격
            combo = getattr(character, 'support_fire_combo', 0)
            marked = getattr(character, 'marked_allies_count', 0)

            console.print(content_x, content_y + line, "🏹 궁수 - 지원사격", fg=(150, 200, 100))
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
                console.print(content_x, content_y + line, "🔥 완벽한 지원!", fg=(255, 215, 0))
                line += 1
                console.print(content_x, content_y + line, "⚡ 데미지 +100%, 확정 크리티컬", fg=(255, 255, 100))
            elif combo >= 5:
                console.print(content_x, content_y + line, "🔥 연속 지원 보너스!", fg=(255, 200, 100))
                line += 1
                console.print(content_x, content_y + line, "⚡ 데미지 +60%, 크리티컬 +40%", fg=(255, 255, 100))
            elif combo >= 3:
                console.print(content_x, content_y + line, "⚡ 연속 지원 중", fg=(200, 255, 200))
                line += 1
                console.print(content_x, content_y + line, "⚡ 데미지 +40%, 크리티컬 +20%", fg=(255, 255, 200))
            else:
                console.print(content_x, content_y + line, "💡 콤보 축적 중", fg=(150, 150, 150))

        elif gimmick_type == "hack_threading":
            # 해커 - 해킹 스레드
            threads = getattr(character, 'active_threads', 0)
            exploits = getattr(character, 'exploit_count', 0)
            max_threads = getattr(character, 'max_threads', 5)

            console.print(content_x, content_y + line, "💻 해커 - 해킹 스레드", fg=(100, 255, 100))
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
                console.print(content_x, content_y + line, "⚡ 다중 스레드 공격 가능!", fg=(255, 255, 100))
                line += 1
            if exploits >= 3:
                console.print(content_x, content_y + line, "🔓 시스템 장악 준비 완료", fg=(255, 100, 255))

        elif gimmick_type == "cheer_gauge":
            # 검투사 - 환호
            cheer = getattr(character, 'cheer', 0)
            max_cheer = getattr(character, 'max_cheer', 100)

            console.print(content_x, content_y + line, "⚔️ 검투사 - 환호 게이지", fg=(255, 200, 100))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_color = (255, 215, 0) if cheer > 70 else (200, 150, 100)
            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, cheer, max_cheer, show_numbers=True, custom_color=gauge_color)
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if cheer >= 100:
                console.print(content_x, content_y + line, "📢 열광! 검투사의 영광!", fg=(255, 215, 0))
                line += 1
                console.print(content_x, content_y + line, "⚡ 무적 3턴!", fg=(255, 255, 100))
            elif cheer > 70:
                console.print(content_x, content_y + line, "📢 열광! 궁극기 강화", fg=(255, 200, 100))
                line += 1
                console.print(content_x, content_y + line, "⚡ 공격력 +60%, 크리티컬 +40%", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, "⚡ 모든 공격 광역화", fg=(255, 200, 100))
            elif cheer > 40:
                console.print(content_x, content_y + line, "📢 고조 - 공격력 증가", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, "⚡ 공격력 +30%, 크리티컬 +20%", fg=(255, 255, 200))
            else:
                console.print(content_x, content_y + line, "📢 평온 - 축적 필요", fg=(150, 150, 150))

        # === 기존 기믹 시스템들 (21개) ===

        elif gimmick_type == "stance_system":
            # 전사 - 스탠스 시스템
            stance = getattr(character, 'current_stance', 0)
            stance_names = ["기본", "공격", "방어", "신속", "균형", "최종"]

            console.print(content_x, content_y + line, "⚔️ 전사 - 스탠스 시스템", fg=(255, 150, 100))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 2

            # 현재 스탠스 강조 표시
            if 0 <= stance < len(stance_names):
                console.print(content_x + 10, content_y + line, f"【 {stance_names[stance]} 】", fg=(255, 255, 100))
                line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 스탠스별 효과
            stance_effects = [
                "일반 능력치",
                "⚔️ 공격력 +40%, 방어력 -20%",
                "🛡️ 방어력 +50%, 공격력 -10%",
                "💨 속도 +50%, HP -10%",
                "⚖️ 모든 스탯 +15%",
                "⭐ 모든 스탯 +30%, 크리티컬 +20%"
            ]
            if 0 <= stance < len(stance_effects):
                console.print(content_x, content_y + line, f"{stance_effects[stance]}", fg=(255, 255, 200))

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
            console.print(content_x, content_y + line, "🔥 화염:", fg=(255, 100, 50))
            gauge_renderer.render_bar(console, content_x + 8, content_y + line, 15, fire, max_elem, show_numbers=True, custom_color=(255, 100, 50))
            line += 1
            console.print(content_x, content_y + line, "❄️ 냉기:", fg=(100, 200, 255))
            gauge_renderer.render_bar(console, content_x + 8, content_y + line, 15, ice, max_elem, show_numbers=True, custom_color=(100, 200, 255))
            line += 1
            console.print(content_x, content_y + line, "⚡ 번개:", fg=(255, 255, 100))
            gauge_renderer.render_bar(console, content_x + 8, content_y + line, 15, lightning, max_elem, show_numbers=True, custom_color=(255, 255, 100))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 원소 조합 가능 체크
            if fire >= 3 and ice >= 3:
                console.print(content_x, content_y + line, "💥 화염+냉기 융합 가능!", fg=(255, 200, 255))
                line += 1
            if ice >= 3 and lightning >= 3:
                console.print(content_x, content_y + line, "⚡ 냉기+번개 융합 가능!", fg=(200, 255, 255))
                line += 1
            if fire >= 3 and lightning >= 3:
                console.print(content_x, content_y + line, "🔥 화염+번개 융합 가능!", fg=(255, 255, 200))

        elif gimmick_type == "support_fire_system":
            # 궁수 - 지원사격 시스템
            marked_allies = getattr(character, 'marked_allies', [])
            combo = getattr(character, 'combo_count', 0)
            max_marks = getattr(character, 'max_marks', 3)

            console.print(content_x, content_y + line, "🏹 궁수 - 지원사격", fg=(100, 200, 100))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 마킹된 아군 정보
            console.print(content_x, content_y + line, f"마킹된 아군: ({len(marked_allies)}/{max_marks})", fg=(200, 200, 200))
            line += 1

            if len(marked_allies) > 0:
                console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
                line += 1

                # 화살 타입 이름 매핑
                arrow_names = {
                    'N': '일반 화살',
                    'P': '관통 화살 (방어 무시)',
                    'F': '화염 화살 (화상)',
                    'I': '빙결 화살 (속도↓)',
                    'T': '독 화살 (독)',
                    'E': '폭발 화살 (광역)',
                    'H': '신성 화살 (언데드 특효)',
                }

                # 각 마킹된 아군 표시
                for i, ally in enumerate(marked_allies):
                    if isinstance(ally, dict):
                        ally_name = ally.get('name', f'아군{i+1}')
                        arrow_type = ally.get('arrow_type', 'N')
                        remaining = ally.get('remaining_shots', 3)
                    else:
                        ally_name = f'아군{i+1}'
                        arrow_type = 'N'
                        remaining = 3

                    console.print(content_x, content_y + line, f"[{ally_name}] 🎯", fg=(255, 200, 100))
                    line += 1
                    console.print(content_x + 2, content_y + line, f"화살: {arrow_names.get(arrow_type, '일반 화살')}", fg=(200, 200, 200))
                    line += 1
                    console.print(content_x + 2, content_y + line, f"남은 지원: {remaining}회", fg=(180, 180, 180))
                    line += 1

                    if i < len(marked_allies) - 1:
                        line += 1  # 간격

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 콤보 상태
            if combo >= 7:
                console.print(content_x, content_y + line, "🔥 완벽한 지원! (콤보 7+)", fg=(255, 255, 100))
                line += 1
                console.print(content_x + 2, content_y + line, "데미지 +100%, 크리티컬 확정", fg=(255, 255, 200))
            elif combo >= 5:
                console.print(content_x, content_y + line, f"🔥 콤보: {combo} 연속", fg=(255, 200, 100))
                line += 1
                console.print(content_x + 2, content_y + line, "데미지 +60%, 크리티컬 +40%", fg=(255, 200, 150))
                line += 1
                remaining_for_perfect = 7 - combo
                console.print(content_x, content_y + line, f"💡 {remaining_for_perfect}회 더 성공 시 완벽한 지원!", fg=(200, 255, 200))
            elif combo >= 3:
                console.print(content_x, content_y + line, f"🔥 콤보: {combo} 연속", fg=(255, 150, 100))
                line += 1
                console.print(content_x + 2, content_y + line, "데미지 +40%, 크리티컬 +20%", fg=(255, 200, 150))
            elif combo >= 2:
                console.print(content_x, content_y + line, f"🔥 콤보: {combo} 연속", fg=(200, 150, 100))
                line += 1
                console.print(content_x + 2, content_y + line, "데미지 +20%", fg=(200, 200, 150))
            else:
                console.print(content_x, content_y + line, "💡 지원 대기 중...", fg=(150, 150, 150))
                line += 1
                console.print(content_x, content_y + line, "아군 공격 시 자동 지원 발동", fg=(180, 180, 180))

        elif gimmick_type == "magazine_system":
            # 저격수 - 탄창 시스템
            magazine = getattr(character, 'magazine', [])
            current_bullet = getattr(character, 'current_bullet_index', 0)

            console.print(content_x, content_y + line, "🎯 저격수 - 탄창", fg=(255, 200, 100))
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
                console.print(content_x, content_y + line, "⚠️ 탄창 비었음! 재장전 필요!", fg=(255, 100, 100))
                line += 1
                console.print(content_x, content_y + line, "권총 모드 (데미지 -80%)", fg=(255, 150, 150))
            elif len(magazine) <= 2:
                console.print(content_x, content_y + line, "⚠️ 탄약 부족! 재장전 권장", fg=(255, 200, 100))
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

            console.print(content_x, content_y + line, "⚔️ 검성 - 검기", fg=(200, 220, 255))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, aura, max_aura, show_numbers=True, custom_color=(200, 220, 255))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if aura >= 5:
                console.print(content_x, content_y + line, "⚡ 검기 최대! 궁극기 가능", fg=(255, 255, 100))
            elif aura >= 3:
                console.print(content_x, content_y + line, "⚔️ 검기 충전 중", fg=(200, 220, 255))
                line += 1
                console.print(content_x, content_y + line, "⚡ 공격력 +20%", fg=(255, 255, 200))
            else:
                console.print(content_x, content_y + line, "💡 검기 축적 중...", fg=(150, 150, 150))

        elif gimmick_type == "melody_system":
            # 바드 - 멜로디 시스템
            melody = getattr(character, 'melody_stacks', 0)
            max_melody = getattr(character, 'max_melody_stacks', 7)

            console.print(content_x, content_y + line, "🎵 바드 - 멜로디", fg=(255, 200, 255))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, melody, max_melody, show_numbers=True, custom_color=(255, 200, 255))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if melody >= 7:
                console.print(content_x, content_y + line, "🎼 완벽한 하모니!", fg=(255, 215, 0))
                line += 1
                console.print(content_x, content_y + line, "⚡ 파티 전체 모든 스탯 +30%", fg=(255, 255, 100))
            elif melody >= 4:
                console.print(content_x, content_y + line, "🎵 멜로디 진행 중", fg=(255, 200, 255))
                line += 1
                console.print(content_x, content_y + line, "⚡ 파티 공격력 +15%", fg=(255, 255, 200))
            else:
                console.print(content_x, content_y + line, "💡 멜로디 작곡 중...", fg=(150, 150, 150))

        elif gimmick_type == "necro_system":
            # 네크로맨서 - 네크로 에너지
            necro = getattr(character, 'necro_energy', 0)
            max_necro = getattr(character, 'max_necro_energy', 50)
            corpses = getattr(character, 'corpse_count', 0)

            console.print(content_x, content_y + line, "💀 네크로맨서 - 사령 에너지", fg=(150, 100, 150))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            console.print(content_x, content_y + line, "사령 에너지:", fg=(200, 200, 200))
            gauge_renderer.render_bar(console, content_x, content_y + line + 1, box_width - 6, necro, max_necro, show_numbers=True, custom_color=(150, 100, 150))
            line += 2

            console.print(content_x, content_y + line, f"💀 시체 수집: {corpses}/10", fg=(200, 150, 200))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if corpses >= 5:
                console.print(content_x, content_y + line, "⚡ 강력한 언데드 소환 가능!", fg=(255, 200, 255))
            elif corpses >= 2:
                console.print(content_x, content_y + line, "💡 언데드 소환 가능", fg=(200, 150, 200))
            else:
                console.print(content_x, content_y + line, "💡 시체 수집 필요", fg=(150, 150, 150))

        elif gimmick_type == "time_system":
            # 시간술사 - 시간 마크
            marks = getattr(character, 'time_marks', 0)
            max_marks = getattr(character, 'max_time_marks', 7)

            console.print(content_x, content_y + line, "⏰ 시간술사 - 시간 마크", fg=(200, 150, 255))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, marks, max_marks, show_numbers=True, custom_color=(200, 150, 255))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if marks >= 7:
                console.print(content_x, content_y + line, "⏰ 시간 역행 가능!", fg=(255, 255, 100))
            elif marks >= 4:
                console.print(content_x, content_y + line, "⏰ 시간 조작 가능", fg=(200, 150, 255))
            else:
                console.print(content_x, content_y + line, "💡 시간 마크 축적 중...", fg=(150, 150, 150))

        elif gimmick_type == "alchemy_system":
            # 연금술사 - 포션 재고
            potions = getattr(character, 'potion_stock', 0)
            max_potions = getattr(character, 'max_potion_stock', 10)

            console.print(content_x, content_y + line, "🧪 연금술사 - 포션 재고", fg=(100, 255, 150))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, potions, max_potions, show_numbers=True, custom_color=(100, 255, 150))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if potions >= 8:
                console.print(content_x, content_y + line, "🧪 포션 풍부!", fg=(100, 255, 150))
                line += 1
                console.print(content_x, content_y + line, "⚡ 고급 포션 제작 가능", fg=(255, 255, 200))
            elif potions >= 4:
                console.print(content_x, content_y + line, "🧪 포션 충분", fg=(150, 255, 200))
            else:
                console.print(content_x, content_y + line, "⚠️ 포션 부족 - 제작 필요", fg=(255, 200, 100))

        elif gimmick_type == "darkness_system":
            # 암흑기사 - 어둠
            darkness = getattr(character, 'darkness', 0)
            max_darkness = 100

            console.print(content_x, content_y + line, "⚫ 암흑기사 - 어둠", fg=(100, 100, 150))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, darkness, max_darkness, show_numbers=True, custom_color=(100, 100, 150))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if darkness >= 70:
                console.print(content_x, content_y + line, "⚫ 어둠 가득!", fg=(150, 150, 200))
                line += 1
                console.print(content_x, content_y + line, "⚡ HP 소모 스킬 +50%", fg=(255, 200, 255))
            elif darkness >= 40:
                console.print(content_x, content_y + line, "⚫ 어둠 축적 중", fg=(120, 120, 180))
            else:
                console.print(content_x, content_y + line, "💡 어둠 부족", fg=(150, 150, 150))

        elif gimmick_type == "holy_system":
            # 성기사/신관 - 신성력
            holy = getattr(character, 'holy_power', 0)
            max_holy = getattr(character, 'max_holy_power', 100)

            console.print(content_x, content_y + line, "✨ 성기사 - 신성력", fg=(255, 255, 200))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, holy, max_holy, show_numbers=True, custom_color=(255, 255, 200))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if holy >= 80:
                console.print(content_x, content_y + line, "✨ 신성력 충만!", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, "⚡ 회복 +50%, 언데드 특효", fg=(255, 255, 200))
            elif holy >= 40:
                console.print(content_x, content_y + line, "✨ 신성력 충전 중", fg=(255, 255, 150))
            else:
                console.print(content_x, content_y + line, "💡 기도 필요", fg=(150, 150, 150))

        elif gimmick_type == "iaijutsu_system":
            # 사무라이 - 거합 게이지
            will = getattr(character, 'will_gauge', 0)
            max_will = getattr(character, 'max_will_gauge', 100)

            console.print(content_x, content_y + line, "⚔️ 사무라이 - 거합", fg=(200, 50, 50))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, will, max_will, show_numbers=True, custom_color=(200, 50, 50))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if will >= 100:
                console.print(content_x, content_y + line, "⚔️ 거합 준비 완료!", fg=(255, 100, 100))
                line += 1
                console.print(content_x, content_y + line, "⚡ 일격필살 가능!", fg=(255, 255, 100))
            elif will >= 50:
                console.print(content_x, content_y + line, "⚔️ 의지 집중 중", fg=(200, 100, 100))
            else:
                console.print(content_x, content_y + line, "💡 집중 필요", fg=(150, 150, 150))

        elif gimmick_type == "enchant_system":
            # 마검사 - 마력 부여
            mana = getattr(character, 'mana_blade', 0)
            max_mana = getattr(character, 'max_mana_blade', 100)

            console.print(content_x, content_y + line, "⚔️🔮 마검사 - 마력 부여", fg=(150, 100, 255))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, mana, max_mana, show_numbers=True, custom_color=(150, 100, 255))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if mana >= 70:
                console.print(content_x, content_y + line, "⚔️🔮 마검 완성!", fg=(200, 150, 255))
                line += 1
                console.print(content_x, content_y + line, "⚡ 물리+마법 피해 극대화", fg=(255, 255, 200))
            elif mana >= 35:
                console.print(content_x, content_y + line, "⚔️🔮 마력 충전 중", fg=(150, 100, 255))
            else:
                console.print(content_x, content_y + line, "💡 마력 부여 필요", fg=(150, 150, 150))

        elif gimmick_type == "shapeshifting_system":
            # 드루이드 - 변신
            nature = getattr(character, 'nature_points', 0)
            form = getattr(character, 'current_form', None)

            console.print(content_x, content_y + line, "🌿 드루이드 - 변신", fg=(100, 200, 100))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 2

            if form:
                form_icons = {
                    "bear": "🐻 곰",
                    "cat": "🐱 고양이",
                    "bird": "🦅 독수리",
                    "human": "👤 인간"
                }
                form_name = form_icons.get(form, form)
                console.print(content_x + 10, content_y + line, f"【 {form_name} 】", fg=(100, 255, 100))
            else:
                console.print(content_x + 10, content_y + line, "【 인간 형태 】", fg=(200, 200, 200))
            line += 2

            console.print(content_x, content_y + line, f"🌿 자연 포인트: {nature}/100", fg=(150, 255, 150))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if nature >= 70:
                console.print(content_x, content_y + line, "🌿 자연의 힘 충만!", fg=(100, 255, 100))
            else:
                console.print(content_x, content_y + line, "💡 자연과 교감 필요", fg=(150, 150, 150))

        elif gimmick_type == "dragon_marks":
            # 용기사 - 용의 표식
            marks = getattr(character, 'dragon_marks', 0)
            max_marks = getattr(character, 'max_dragon_marks', 3)
            power = getattr(character, 'dragon_power', 0)

            console.print(content_x, content_y + line, "🐉 용기사 - 용의 표식", fg=(255, 100, 50))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            console.print(content_x, content_y + line, f"🐉 용의 표식: {marks}/{max_marks}", fg=(255, 150, 100))
            line += 1
            console.print(content_x, content_y + line, f"⚡ 용력: {power}/100", fg=(255, 200, 100))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if marks >= 3:
                console.print(content_x, content_y + line, "🐉 드래곤 폼 가능!", fg=(255, 100, 50))
                line += 1
                console.print(content_x, content_y + line, "⚡ 모든 스탯 +50%", fg=(255, 255, 100))
            else:
                console.print(content_x, content_y + line, "💡 표식 축적 필요", fg=(150, 150, 150))

        elif gimmick_type == "arena_system":
            # 검투사 - 투기장
            arena = getattr(character, 'arena_points', 0)
            glory = getattr(character, 'glory_points', 0)
            kills = getattr(character, 'kill_count', 0)

            console.print(content_x, content_y + line, "⚔️ 검투사 - 투기장", fg=(255, 200, 100))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            console.print(content_x, content_y + line, f"⚔️ 투기: {arena}", fg=(255, 200, 100))
            line += 1
            console.print(content_x, content_y + line, f"🏆 영광: {glory}", fg=(255, 215, 0))
            line += 1
            console.print(content_x, content_y + line, f"💀 처치: {kills}", fg=(255, 100, 100))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if glory >= 100:
                console.print(content_x, content_y + line, "🏆 전설적 검투사!", fg=(255, 215, 0))
            elif glory >= 50:
                console.print(content_x, content_y + line, "⚔️ 명성 높은 검투사", fg=(255, 200, 100))
            else:
                console.print(content_x, content_y + line, "💡 명성 획득 필요", fg=(150, 150, 150))

        elif gimmick_type == "break_system":
            # 브레이커 - 파괴력
            break_power = getattr(character, 'break_power', 0)
            max_break = getattr(character, 'max_break_power', 10)

            console.print(content_x, content_y + line, "🔨 브레이커 - 파괴력", fg=(255, 150, 50))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, break_power, max_break, show_numbers=True, custom_color=(255, 150, 50))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if break_power >= 10:
                console.print(content_x, content_y + line, "🔨 최대 파괴력!", fg=(255, 100, 50))
                line += 1
                console.print(content_x, content_y + line, "⚡ 방어 무시 100%", fg=(255, 255, 100))
            else:
                console.print(content_x, content_y + line, "💡 파괴력 축적 중...", fg=(150, 150, 150))

        elif gimmick_type == "plunder_system":
            # 해적 - 약탈
            gold = getattr(character, 'gold', 0)

            console.print(content_x, content_y + line, "🏴‍☠️ 해적 - 약탈 골드", fg=(255, 215, 0))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 2

            console.print(content_x + 10, content_y + line, f"💰 {gold} 골드", fg=(255, 215, 0))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if gold >= 1000:
                console.print(content_x, content_y + line, "💰 골드 풍부!", fg=(255, 215, 0))
                line += 1
                console.print(content_x, content_y + line, "⚡ 용병/함포 강화 가능", fg=(255, 255, 200))
            else:
                console.print(content_x, content_y + line, "💡 약탈 필요", fg=(200, 200, 200))

        elif gimmick_type == "divinity_system":
            # 프리스트/클레릭 - 신성력
            judgment = getattr(character, 'judgment_points', 0)
            faith = getattr(character, 'faith_points', 0)

            console.print(content_x, content_y + line, "⛪ 성직자 - 신성력", fg=(255, 255, 200))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            console.print(content_x, content_y + line, f"⚖️ 심판: {judgment}/100", fg=(255, 200, 100))
            line += 1
            console.print(content_x, content_y + line, f"🙏 신앙: {faith}/100", fg=(200, 220, 255))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if judgment >= 70 and faith >= 70:
                console.print(content_x, content_y + line, "✨ 균형잡힌 신성력!", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, "⚡ 기적 스킬 가능", fg=(255, 255, 200))
            elif judgment > faith:
                console.print(content_x, content_y + line, "⚖️ 심판 중심 - 공격 강화", fg=(255, 200, 100))
            else:
                console.print(content_x, content_y + line, "🙏 신앙 중심 - 회복 강화", fg=(200, 220, 255))

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

    def _get_gimmick_detail(self, character: Any) -> str:
        """캐릭터의 기믹 상태 상세 정보 (기믹 커맨드용)"""
        gimmick_type = getattr(character, 'gimmick_type', None)
        if not gimmick_type:
            return "기믹 시스템 없음"

        details = []

        # === 15개 신규 기믹 시스템 상세 ===

        if gimmick_type == "yin_yang_flow":
            ki = getattr(character, 'ki_gauge', 50)
            details.append("=== 음양 흐름 시스템 ===")
            details.append(f"기 게이지: {ki}/100")
            if ki < 20:
                details.append("상태: 음 (방어/회복 강화)")
            elif ki > 80:
                details.append("상태: 양 (공격/속도 강화)")
            else:
                details.append("상태: 균형 (안정적 전투)")

        elif gimmick_type == "rune_resonance":
            fire = getattr(character, 'rune_fire', 0)
            ice = getattr(character, 'rune_ice', 0)
            lightning = getattr(character, 'rune_lightning', 0)
            details.append("=== 룬 공명 시스템 ===")
            details.append(f"🔥 화염 룬: {fire}/3")
            details.append(f"❄️  냉기 룬: {ice}/3")
            details.append(f"⚡ 번개 룬: {lightning}/3")
            if fire >= 2 and ice >= 2:
                details.append("공명 가능: 화염+냉기")
            if ice >= 2 and lightning >= 2:
                details.append("공명 가능: 냉기+번개")
            if fire >= 2 and lightning >= 2:
                details.append("공명 가능: 화염+번개")

        elif gimmick_type == "probability_distortion":
            gauge = getattr(character, 'distortion_gauge', 0)
            details.append("=== 확률 왜곡 시스템 ===")
            details.append(f"왜곡 게이지: {gauge}/100")
            if gauge >= 100:
                details.append("평행우주 사용 가능!")
            elif gauge >= 50:
                details.append("시간 되감기 사용 가능")
            elif gauge >= 30:
                details.append("회피 왜곡 사용 가능")
            elif gauge >= 20:
                details.append("크리티컬 왜곡 사용 가능")

        elif gimmick_type == "heat_gauge":
            heat = getattr(character, 'heat', 0)
            details.append("=== 열 게이지 시스템 ===")
            details.append(f"열 누적: {heat}/100")
            if heat > 70:
                details.append("⚠️  과열 위험! 방출 권장")
            elif heat > 40:
                details.append("적정 열량 - 강화 스킬 사용 가능")
            else:
                details.append("낮은 열량 - 축적 필요")

        elif gimmick_type == "thirst_gauge":
            thirst = getattr(character, 'thirst', 0)
            details.append("=== 갈증 게이지 시스템 ===")
            details.append(f"갈증: {thirst}/100")
            if thirst > 70:
                details.append("💧 갈망 상태 - 흡혈 강화")
            elif thirst < 30:
                details.append("만족 상태 - 안정적")
            else:
                details.append("보통 상태")

        elif gimmick_type == "madness_gauge":
            madness = getattr(character, 'madness', 0)
            details.append("=== 광기 게이지 시스템 ===")
            details.append(f"광기: {madness}/100")
            if madness > 70:
                details.append("⚡ 광란 상태 - 초강력 공격 가능!")
            elif madness > 40:
                details.append("격앙 상태 - 공격력 증가")
            else:
                details.append("안전 구간")

        elif gimmick_type == "spirit_resonance":
            fire = getattr(character, 'spirit_fire', 0)
            water = getattr(character, 'spirit_water', 0)
            wind = getattr(character, 'spirit_wind', 0)
            earth = getattr(character, 'spirit_earth', 0)
            details.append("=== 정령 공명 시스템 ===")
            details.append(f"🔥 화염 정령: {'활성화' if fire > 0 else '비활성'}")
            details.append(f"💧 수령 정령: {'활성화' if water > 0 else '비활성'}")
            details.append(f"💨 바람 정령: {'활성화' if wind > 0 else '비활성'}")
            details.append(f"🌍 대지 정령: {'활성화' if earth > 0 else '비활성'}")
            active = sum([1 for s in [fire, water, wind, earth] if s > 0])
            if active >= 2:
                details.append(f"융합 가능! (활성 정령: {active})")

        elif gimmick_type == "stealth_mastery":
            stealth_active = getattr(character, 'stealth_active', False)
            shadow_strike = getattr(character, 'shadow_strike_ready', False)
            details.append("=== 은신 숙련 시스템 ===")
            if stealth_active:
                details.append("상태: 🌑 은신 중")
                details.append("다음 공격 크리티컬 확정")
            elif shadow_strike:
                details.append("상태: 그림자 공격 준비")
                details.append("암살 기술 사용 가능")
            else:
                details.append("상태: 👁 노출")
                details.append("은신 스킬로 재진입 가능")

        elif gimmick_type == "dilemma_choice":
            power = getattr(character, 'choice_power', 0)
            wisdom = getattr(character, 'choice_wisdom', 0)
            sacrifice = getattr(character, 'choice_sacrifice', 0)
            truth = getattr(character, 'choice_truth', 0)
            details.append("=== 딜레마 선택 시스템 ===")
            details.append(f"힘의 선택: {power}")
            details.append(f"지혜의 선택: {wisdom}")
            details.append(f"희생의 선택: {sacrifice}")
            details.append(f"진리의 선택: {truth}")
            dominant = max(power, wisdom, sacrifice, truth)
            if power == dominant:
                details.append("경향: 힘 중심")
            elif wisdom == dominant:
                details.append("경향: 지혜 중심")
            elif sacrifice == dominant:
                details.append("경향: 희생 중심")
            elif truth == dominant:
                details.append("경향: 진리 중심")

        elif gimmick_type == "support_fire":
            combo = getattr(character, 'support_fire_combo', 0)
            marked = getattr(character, 'marked_allies_count', 0)
            details.append("=== 지원사격 시스템 ===")
            details.append(f"지원 콤보: {combo}")
            details.append(f"표식된 아군: {marked}명")
            if combo >= 3:
                details.append("연속 지원 보너스 활성!")

        elif gimmick_type == "hack_threading":
            threads = getattr(character, 'active_threads', 0)
            exploits = getattr(character, 'exploit_count', 0)
            details.append("=== 해킹 스레드 시스템 ===")
            details.append(f"활성 스레드: {threads}/5")
            details.append(f"익스플로잇: {exploits}")
            if threads >= 4:
                details.append("⚡ 다중 스레드 공격 가능!")
            if exploits >= 3:
                details.append("시스템 장악 준비 완료")

        elif gimmick_type == "cheer_gauge":
            cheer = getattr(character, 'cheer', 0)
            details.append("=== 환호 게이지 시스템 ===")
            details.append(f"환호: {cheer}/100")
            if cheer > 70:
                details.append("📢 열광! 궁극기 강화")
            elif cheer > 40:
                details.append("고조 - 공격력 증가")
            else:
                details.append("평온 - 축적 필요")

        else:
            return "기믹 상세 정보 없음"

        return "\n".join(details)

        return ""

    def _render_item_menu(self, console: tcod.console.Console):
        """아이템 메뉴 렌더링 (인벤토리 UI 연동 필요)"""
        console.print(
            self.screen_width // 2 - 10,
            35,
            "아이템 (인벤토리 열기)",
            fg=(255, 255, 100)
        )

        console.print(
            self.screen_width // 2 - 8,
            36,
            "X: 취소",
            fg=(180, 180, 180)
        )

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
    enemies: List[Any]
) -> CombatState:
    """
    전투 실행

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        party: 아군 파티
        enemies: 적군 리스트

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
        # 보스전: 2개 중 랜덤
        boss_bgm_tracks = ["battle_jenova", "battle_birth_of_god"]
        selected_bgm = random.choice(boss_bgm_tracks)
    else:
        # 일반 전투: 3개 중 랜덤
        battle_bgm_tracks = [
            "battle_boss",              # 21-Still More Fighting
            "battle_jenova_absolute",   # 85-Jenova Absolute
            "battle_normal"             # 11-Fighting
        ]
        selected_bgm = random.choice(battle_bgm_tracks)

    play_bgm(selected_bgm, loop=True, fade_in=True)

    # 전투 매니저 생성
    combat_manager = CombatManager()
    combat_manager.start_combat(party, enemies)

    # 전투 UI 생성
    ui = CombatUI(console.width, console.height, combat_manager)
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
