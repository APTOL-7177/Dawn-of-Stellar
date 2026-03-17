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
import pygame

from src.ui.input_handler import InputHandler, GameAction, unified_input_handler
from src.ui.cursor_menu import CursorMenu, MenuItem
from src.ui.gauge_renderer import GaugeRenderer, get_animation_manager
from src.ui.tcod_display import render_space_background
from src.ui.teamwork_gauge_display import TeamworkGaugeDisplay
from src.combat.combat_manager import CombatManager, CombatState, ActionType
from src.combat.casting_system import get_casting_system, CastingSystem
from src.combat.status_effects import StatusEffect, StatusType
from src.core.logger import get_logger, Loggers
from src.core.vibration_system import vibration_manager, VibrationPattern
from src.audio import play_sfx, play_bgm
from src.ui.combat_tooltip import render_tooltip
from src.ui.effects import trigger_skill_effect, trigger_status_effect, trigger_item_effect
from src.ui.ui_renderer import draw_styled_box, SelectionHighlight


logger = get_logger(Loggers.UI)
gauge_renderer = GaugeRenderer()
casting_system = get_casting_system()


class CombatUIState(Enum):
    """전투 UI 상태"""
    WAITING_ATB = "waiting_atb"  # ATB 대기 중
    ACTION_MENU = "action_menu"  # 행동 선택
    SKILL_MENU = "skill_menu"  # 스킬 선택
    CHOICE_SELECT = "choice_select"  # 선택형 스킬(서약/피날레 등) 선택
    TARGET_SELECT = "target_select"  # 대상 선택
    ITEM_MENU = "item_menu"  # 아이템 선택
    CARD_SELECT = "card_select"  # 카드 선택 (마술사)
    POSSIBILITY_SELECT = "possibility_select"  # 가능성 선택 (시간술사)
    GIMMICK_VIEW = "gimmick_view"  # 기믹 상세 보기
    CHAIN_ABILITY_SELECT = "chain_ability_select"  # 체인어빌리티 선택 (불릿타임)
    EXECUTING = "executing"  # 행동 실행 중
    WAITING_REMOTE_ACTION = "waiting_remote_action"  # 원격 플레이어 행동 대기 중 (멀티플레이)
    BATTLE_END = "battle_end"  # 전투 종료


@dataclass
class CombatMessage:
    """전투 메시지"""
    text: str
    color: Tuple[int, int, int] = (255, 255, 255)
    frames_remaining: int = 180  # 3초 (60 FPS 기준)


@dataclass
class FloatingDialogue:
    """화면에 떠다니는 대사 (림버스 컴퍼니 스타일 - 글리치/공포 효과)"""
    text: str
    x: int
    y: int
    color: Tuple[int, int, int] = (255, 100, 100)  # 기본 붉은색
    total_frames: int = 900  # 15초 (60 FPS 기준) - 오래 남아서 방해
    frames_remaining: int = 900
    typing_speed: float = 0.1  # 프레임당 0.1글자 (10프레임당 1글자 = 초당 6글자)
    current_char_index: float = 0.0  # 현재 타이핑 중인 글자 인덱스 (float로 변경)
    fade_start_frames: int = 300  # 마지막 5초부터 페이드 아웃 (매우 느리게)


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
        local_player_id: Optional[str] = None,  # 로컬 플레이어 ID (다른 플레이어 컨트롤 방지)
        lily_dialogue: Optional[Any] = None,  # RPG 모드 릴리 대사 매니저
        rpg_chapter: int = 0,
        rpg_affinity: int = 0,
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.combat_manager = combat_manager
        self.inventory = inventory  # 전투 중 아이템 사용을 위한 인벤토리
        self.session = session  # 멀티플레이 세션
        self.network_manager = network_manager  # 네트워크 관리자
        self.bot_manager = bot_manager  # 봇 관리자
        self.local_player_id = local_player_id  # 로컬 플레이어 ID
        self.logger = logger  # 로거 인스턴스

        # UI 상태
        self.state = CombatUIState.WAITING_ATB
        self.current_actor: Optional[Any] = None
        self.selected_action: Optional[ActionType] = None
        self.selected_skill: Optional[Any] = None
        self.selected_target: Optional[Any] = None
        self.selected_item: Optional[Any] = None  # 선택된 아이템
        self.selected_item_index: Optional[int] = None  # 선택된 아이템 인덱스
        self.choice_menu: Optional[CursorMenu] = None  # 선택형 스킬 메뉴
        self.chain_ability_menu: Optional[CursorMenu] = None  # 체인어빌리티 선택 메뉴
        self.chain_ability_results: list = []  # 체인어빌리티 결과 목록

        # 메시지 로그 (스크롤 형식, 제한 없이 저장)
        self.messages: List[CombatMessage] = []
        self.log_scroll_offset = 0  # 스크롤 오프셋 (0이면 최신 메시지)
        self.log_visible_lines = 12  # 화면에 표시할 메시지 라인 수 (8 -> 12로 증가)

        # 떠다니는 대사 목록 (림버스 컴퍼니 스타일)
        self.floating_dialogues: List[FloatingDialogue] = []

        # CombatManager에 자신을 등록 (보스 대사 시스템용)
        if combat_manager:
            combat_manager.combat_ui = self

        # 트레이닝 모드
        self.training_mode = False
        self.training_dummy = None
        self.training_variant: Optional[str] = None
        self.training_damage_log: Dict[str, int] = {}

        # 메뉴
        self.action_menu: Optional[CursorMenu] = None
        self.skill_menu: Optional[CursorMenu] = None
        # 과부하 사용 여부 선택 (스킬 ID별)
        self.overload_selection: Dict[str, bool] = {}
        self.item_menu: Optional[CursorMenu] = None  # 아이템 메뉴
        self.target_cursor = 0
        self.current_target_list: List[Any] = []  # 현재 타겟 선택 리스트
        self.all_allies_mode = False  # ALL_ALLIES 타겟 선택 모드
        
        # RPG 모드 릴리 대사
        self.lily_dialogue = lily_dialogue
        self._rpg_chapter = rpg_chapter
        self._rpg_affinity = rpg_affinity
        self._lily_low_hp_shown = False
        self._lily_ally_down_shown: set = set()
        self._lily_ally_critical_shown = False
        self._lily_long_battle_shown = False
        self._lily_party_danger_shown = False
        self._lily_turn_count = 0
        self._lily_last_turn_count = 0

        # 카드 선택 (마술사)
        self.card_cursor = 0
        self.card_hand: List[Any] = []  # 현재 손패
        self.selected_card: Optional[Any] = None  # 선택된 카드

        # 가능성 선택 (시간술사)
        self.possibility_cursor = 0
        self.possibility_slots: List[Dict] = []  # 가능성 슬롯 목록
        self.possibility_selected: List[int] = []  # 선택된 인덱스
        self.possibility_action: str = "summon_single"  # 액션 타입
        self.possibility_max_select: int = 1  # 최대 선택 개수

        # 전투 종료 플래그
        self.battle_ended = False
        self.battle_result: Optional[CombatState] = None

        # 기믹 상세 보기
        self.gimmick_view_character: Optional[Any] = None
        self.previous_state: Optional[CombatUIState] = None

        # 행동 후 대기 시간 (프레임 단위, 60 FPS 기준)
        self.action_delay_frames = 0
        self.action_delay_max = 90  # 1.5초 대기
        # 멀티플레이에서 대기 지연의 소유 플레이어 추적 (None이면 전역 지연)
        self.action_delay_owner_player_id: Optional[str] = None

        # 페이즈 메시지 타이머 (프레임 단위)
        self.phase_message_timer = 0
        self.phase_message_duration = 180  # 3초 (60 FPS 기준)
        self.revival_message_timer = 0
        self.revival_message_duration = 180  # 3초

        # 다단히트 타격 큐 시스템 (타격감용)
        self.hit_queue: List[Dict[str, Any]] = []  # 히트 정보 큐
        self.hit_display_delay = 4  # 히트 간 딜레이 (절반으로 단축해 타격음/로그 템포 업)
        self.hit_delay_counter = 0  # 현재 딜레이 카운터
        
        # 히트 이벤트 구독
        from src.core.event_bus import event_bus, Events
        event_bus.subscribe(Events.COMBAT_HIT, self._on_combat_hit)
        event_bus.subscribe(Events.STATUS_APPLIED, self._on_status_applied)

        # 마우스 호버 툴팁 시스템
        self._ally_rects: Dict[int, Any] = {}  # {ally_index: (x, y, w, h)} 셀 좌표
        self._enemy_rects: Dict[int, Any] = {}  # {enemy_index: (x, y, w, h)} 셀 좌표
        self._mouse_cell: Optional[Tuple[int, int]] = None  # 마우스 셀 좌표 (x, y)
        self._hover_character: Optional[Any] = None  # 마우스 호버 중인 캐릭터
        self._hover_cell: Optional[Tuple[int, int]] = None  # 호버 캐릭터의 기준 셀 좌표

        # 이펙트 매니저 참조 (PygameDisplay에서 주입)
        self.effect_manager: Optional[Any] = None

        # 디스플레이 컨텍스트 참조 (raylib 백엔드용)
        self.display_context: Optional[Any] = None

        # 멀티플레이 전투 동기화
        self.local_party_ids: set = set()  # 로컬 플레이어가 조종하는 캐릭터 ID 셋
        self.is_mp_host: bool = False  # 멀티플레이 호스트 여부
        self._remote_action_timeout: float = 0.0  # 원격 플레이어 행동 타임아웃 타이머 (미사용, 호환성 유지)
        self._remote_action_actor: Optional[Any] = None  # 원격 행동 대기 중인 액터 (미사용, 호환성 유지)
        self._pending_remote_actors: dict = {}  # {remote_key: (actor, timeout_remaining)} 비차단 원격 대기 추적
        self._mp_combat_end_received: bool = False  # 클라이언트: COMBAT_END 수신 플래그
        self._mp_combat_end_result: Optional[str] = None  # 클라이언트: 수신된 전투 결과
        self.combat_sync_manager: Optional[Any] = None
        if session and network_manager:
            from src.multiplayer.game_mode import get_game_mode_manager
            from src.multiplayer.combat_sync import CombatSyncManager
            game_mode_manager = get_game_mode_manager()
            if game_mode_manager and game_mode_manager.is_multiplayer():
                resolved_local_player_id = (
                    local_player_id
                    or getattr(session, 'local_player_id', None)
                    or getattr(game_mode_manager, 'local_player_id', None)
                )
                # 호스트 판정: network_manager.is_host를 최우선 사용 (가장 신뢰성 높음)
                if network_manager and hasattr(network_manager, 'is_host'):
                    is_host = bool(network_manager.is_host)
                elif resolved_local_player_id and hasattr(session, 'host_id'):
                    is_host = session.host_id == resolved_local_player_id
                else:
                    is_host = bool(getattr(game_mode_manager, 'is_host', False))
                self.is_mp_host = is_host
                self.combat_sync_manager = CombatSyncManager(
                    session,
                    network_manager,
                    combat_manager,
                    is_host=is_host
                )
                # local_party_ids 설정: 로컬 플레이어가 조종하는 캐릭터 ID 수집
                if resolved_local_player_id and combat_manager:
                    for ally in combat_manager.allies:
                        ally_owner = getattr(ally, 'owner_player_id', None) or getattr(ally, 'player_id', None)
                        if ally_owner == resolved_local_player_id or not ally_owner:
                            ally_id = getattr(ally, 'id', None) or getattr(ally, 'name', None)
                            if ally_id:
                                self.local_party_ids.add(str(ally_id))
                # 콜백 등록
                if is_host:
                    # 호스트: 원격 플레이어 액션 실행 완료 시 UI 상태 리셋
                    self.combat_sync_manager.on_remote_action_executed_callback = self._on_mp_remote_action_executed
                else:
                    # 클라이언트: 호스트로부터 수신한 메시지 처리
                    self.combat_sync_manager.on_action_selection_start_callback = self._on_mp_action_selection_start
                    self.combat_sync_manager.on_action_result_callback = self._on_mp_action_result
                    self.combat_sync_manager.on_combat_end_callback = self._on_mp_combat_end
                logger.info(f"멀티플레이 전투 동기화 관리자 초기화 완료 (호스트={is_host}, 로컬파티={len(self.local_party_ids)}명)")

        # ── Raylib 전투 렌더러 (백엔드가 raylib일 때만) ──
        self._combat_renderer = None
        self._raylib_context = None
        try:
            from src.core.config import get_config
            if get_config().get("display.backend", "pygame") == "raylib":
                from src.ui.raylib_backend.combat_renderer import CombatRenderer
                from src.ui.tcod_display import get_display
                display = get_display()
                ctx = getattr(display, 'context', None) or getattr(display, '_context', None)
                if ctx is not None:
                    cw = getattr(ctx, 'tile_width', 14)
                    ch = getattr(ctx, 'tile_height', 16)
                    sw = cw * self.screen_width
                    sh = ch * self.screen_height
                    self._combat_renderer = CombatRenderer(
                        screen_w=sw, screen_h=sh, cell_w=cw, cell_h=ch
                    )
                    self._raylib_context = ctx
                    self.display_context = ctx
                    # 전투 참가자 슬롯 초기화
                    self._combat_renderer.setup(
                        list(combat_manager.allies),
                        list(combat_manager.enemies),
                    )
                    logger.info("Raylib CombatRenderer 초기화 완료")
        except Exception as e:
            logger.debug(f"Raylib CombatRenderer 초기화 스킵: {e}")

        # 독립 팝업 매니저 (CombatRenderer 의존 없이 직접 관리)
        self._standalone_popup = None
        try:
            from src.ui.raylib_backend.effects.damage_popup import DamagePopupManager
            self._standalone_popup = DamagePopupManager()
        except Exception:
            pass

        # 게이지 애니메이션 상태 (카운팅 이펙트 + 데미지 트레일)
        self._gauge_anim_values: dict = {}   # key -> 표시 수치 (카운팅)
        self._gauge_trail_ratios: dict = {}  # key -> 잔상 비율
        self._gauge_prev_values: dict = {}   # key -> 이전 프레임 실제 수치 (팝업용)
        self._gauge_display_ratios: dict = {}  # key -> 표시 비율 (증가 시 서서히 채움)

        logger.info("전투 UI 초기화")

    def _create_action_menu(self, actor: Any = None) -> CursorMenu:
        """행동 메뉴 생성"""
        items = []

        # 현재 행동자의 기본 공격 스킬 가져오기
        if actor:
            skills = getattr(actor, 'skills', [])
            
            # basic_attack: True 메타데이터가 있는 스킬만 필터링
            basic_attack_skills = [
                s for s in skills 
                if getattr(s, 'metadata', None) and s.metadata.get('basic_attack', False)
            ]
            
            # 기본 공격 스킬이 없으면 팀워크 제외 처음 2개 사용 (fallback)
            if len(basic_attack_skills) < 2:
                basic_attack_skills = [s for s in skills if not getattr(s, 'is_teamwork_skill', False)][:2]

            # 첫 번째 스킬 = 기본 BRV 공격
            if len(basic_attack_skills) >= 1:
                brv_skill = basic_attack_skills[0]
                brv_name = getattr(brv_skill, 'name', 'BRV 공격')
                brv_desc = getattr(brv_skill, 'description', 'BRV를 축적')
                items.append(MenuItem(brv_name, description=brv_desc, enabled=True, value=("brv_skill", brv_skill)))
            else:
                items.append(MenuItem("BRV 공격", description="BRV를 축적", enabled=True, value=ActionType.BRV_ATTACK))

            # 두 번째 스킬 = 기본 HP 공격
            if len(basic_attack_skills) >= 2:
                hp_skill = basic_attack_skills[1]
                hp_name = getattr(hp_skill, 'name', 'HP 공격')
                hp_desc = getattr(hp_skill, 'description', 'HP 데미지')
                items.append(MenuItem(hp_name, description=hp_desc, enabled=True, value=("hp_skill", hp_skill)))
            else:
                items.append(MenuItem("HP 공격", description="HP 데미지", enabled=True, value=ActionType.HP_ATTACK))
        else:
            # actor가 없으면 기본 행동
            items.append(MenuItem("BRV 공격", description="BRV를 축적", enabled=True, value=ActionType.BRV_ATTACK))
            items.append(MenuItem("HP 공격", description="HP 데미지", enabled=True, value=ActionType.HP_ATTACK))

        # 보스전 확인 (세피로스, 카인)
        is_boss_battle = False
        if hasattr(self.combat_manager, 'enemies'):
            for enemy in self.combat_manager.enemies:
                enemy_id = getattr(enemy, 'enemy_id', None)
                if enemy_id in ['sephiroth', 'abel_cain']:
                    is_boss_battle = True
                    break

        # 나머지 행동들
        items.append(MenuItem("스킬", description="특수 기술 사용", enabled=True, value=ActionType.SKILL))
        items.append(MenuItem("아이템", description="아이템 사용", enabled=True, value=ActionType.ITEM))
        items.append(MenuItem("방어", description="방어 자세로 피해 감소", enabled=True, value=ActionType.DEFEND))
        items.append(MenuItem("기믹 상세", description="기믹 시스템 상세 정보 보기", enabled=True, value=("gimmick_detail", None)))

        # 보스전이 아니면 도망 메뉴 추가
        if not is_boss_battle:
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

        # 보스전 확인 (층보스와 세피로스/카인에서만 궁극기 제한)
        restrict_ultimate = False
        major_bosses = ['sephiroth', 'abel_cain']

        if hasattr(self.combat_manager, 'enemies'):
            for enemy in self.combat_manager.enemies:
                enemy_id = getattr(enemy, 'enemy_id', None)
                if enemy_id:
                    # 층보스: 5층마다 나오는 특정 보스들
                    floor_boss_names = ['wyvern', 'boss_chimera', 'demon', 'boss_lich', 'balrog',
                                       'archfiend', 'elder_dragon', 'boss_dragon_king']
                    is_floor_boss = enemy_id in floor_boss_names
                    # 세피로스나 카인 확인
                    is_major_boss = enemy_id in major_bosses

                    if is_floor_boss or is_major_boss:
                        restrict_ultimate = True
                        break

        # 궁극기 제한 여부 로깅
        if restrict_ultimate:
            logger.warning("[SKILL_MENU] 주요 보스전: 궁극기 사용 제한 (5층보스/세피로스/카인)")
        else:
            logger.info("[SKILL_MENU] 일반 전투: 궁극기 사용 허용 (일반몹/일반보스)")
        major_bosses = ['sephiroth', 'abel_cain']

        if hasattr(self.combat_manager, 'enemies'):
            for enemy in self.combat_manager.enemies:
                enemy_id = getattr(enemy, 'enemy_id', None)
                if enemy_id:
                    # 층보스: 5층마다 나오는 특정 보스들
                    floor_boss_names = ['wyvern', 'boss_chimera', 'demon', 'boss_lich', 'balrog',
                                       'archfiend', 'elder_dragon', 'boss_dragon_king']
                    is_floor_boss = enemy_id in floor_boss_names
                    # 세피로스나 카인 확인
                    is_major_boss = enemy_id in major_bosses

                    if is_floor_boss or is_major_boss:
                        restrict_ultimate = True
                        break

        # 스킬 분류
        teamwork_skills = []
        basic_attack_skills = []  # 기본 공격 스킬
        gimmick_skills = []  # 기믹 스킬 (가능성 소모 등)
        normal_skills = []

        for skill in all_skills:
            metadata = getattr(skill, 'metadata', None) or {}

            # 주요 보스전에서만 궁극기 제외 (층보스, 세피로스, 카인)
            is_ultimate = getattr(skill, 'is_ultimate', False) or metadata.get('ultimate', False)
            if restrict_ultimate and is_ultimate:
                logger.info(f"[SKILL_MENU] 주요 보스전: 궁극기 '{skill.name}' 제외됨")
                continue

            # 팀워크 스킬
            if hasattr(skill, 'is_teamwork_skill') and skill.is_teamwork_skill:
                teamwork_skills.append(skill)
            # 기본 공격 스킬 (metadata로 표시된 경우)
            elif metadata.get('basic_attack', False):
                basic_attack_skills.append(skill)
            # 기믹/가능성 시스템 스킬
            elif metadata.get('gimmick_skill', False) or metadata.get('possibility_system', False):
                gimmick_skills.append(skill)
            else:
                normal_skills.append(skill)
        
        # basic_attack 메타데이터가 없는 직업은 첫 2개 스킬을 기본 공격으로 취급
        if len(basic_attack_skills) == 0 and len(normal_skills) >= 2:
            # 처음 2개를 기본 공격으로 간주하고 제외
            normal_skills = normal_skills[2:]

        logger.warning(f"[SKILL_MENU] 기본 공격 제외 후 일반 스킬: {len(normal_skills)}개, 기믹 스킬: {len(gimmick_skills)}개")

        # 합체기 스킬 (시너지 시스템)
        combo_skills = []
        try:
            if hasattr(self.combat_manager, 'get_available_combo_skills'):
                available_combos = self.combat_manager.get_available_combo_skills()
                # 현재 행동 캐릭터의 직업이 합체기에 포함된 경우만 표시
                actor_job = getattr(actor, 'character_class', None)
                combo_skills = [
                    c for c in available_combos
                    if actor_job and actor_job in c.required_jobs
                ]
                if combo_skills:
                    logger.warning(f"[SKILL_MENU] 발동 가능 합체기: {len(combo_skills)}개")
        except Exception as e:
            logger.debug(f"합체기 목록 조회 실패: {e}")

        # 스킬 순서: 기믹 스킬 맨 위 -> 일반 스킬 -> 팀워크 스킬 -> 합체기 맨 뒤
        skills = gimmick_skills + normal_skills + teamwork_skills

        logger.warning(f"[SKILL_MENU] 메뉴에 표시할 팀워크 스킬: {len(teamwork_skills)}개")
        for skill in teamwork_skills:
            logger.warning(f"[SKILL_MENU] 팀워크 스킬: {skill.name} ({skill.teamwork_cost.gauge}게이지)")

        items = []

        for skill in skills:
            overload_choice = self._get_overload_choice(skill)
            base_context = {}
            if overload_choice is not None:
                base_context['force_overload'] = overload_choice

            # 모든 비용 체크 (MP, Stack, HP 등)
            # 팀워크 스킬은 party 정보도 필요함
            if hasattr(skill, 'is_teamwork_skill') and skill.is_teamwork_skill:
                ctx = {'party': self.combat_manager.party}
                ctx.update(base_context)
                can_use, reason = skill.can_use(actor, ctx)
            else:
                can_use, reason = skill.can_use(actor, base_context if base_context else None)

            # 빙결/기절 등 행동 불가 상태이상 체크 (스킬 목록에는 표시하되 사용 불가 표시)
            if hasattr(actor, 'status_manager') and not actor.status_manager.can_act():
                can_use = False
                reason = "행동 불가 상태"

            skill_metadata = getattr(skill, 'metadata', {}) or {}

            # 가능성 스킬 사용 조건 체크
            if can_use and skill_metadata.get('possibility_system'):
                action = skill_metadata.get('action', 'summon_single')
                if action in ['summon_single', 'summon_dual', 'overwrite_slot']:
                    slots = getattr(actor, 'possibility_slots', [])
                    min_required = 2 if action == "summon_dual" else 1
                    if len(slots) < min_required:
                        can_use = False
                        reason = f"가능성 {min_required}개 필요"

            # 비용 정보 표시
            cost_parts = []
            for cost in skill.costs:
                if hasattr(cost, 'get_description'):
                    # 스킬 정보를 context에 추가하여 특성 효과 반영
                    context = {'skill': skill}
                    if base_context:
                        context.update(base_context)
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

            # 해커 RAM 비용 표시
            skill_meta = getattr(skill, 'metadata', {}) or {}
            if getattr(actor, 'gimmick_type', None) == "intrusion_system":
                ram_cost_val = int(skill_meta.get('ram_cost', 0) or 0)
                if ram_cost_val == 0:
                    # costs에서 ram 키 확인
                    raw_costs = getattr(skill, '_raw_costs', None)
                    if raw_costs and isinstance(raw_costs, dict):
                        ram_cost_val = int(raw_costs.get('ram', 0) or 0)
                if ram_cost_val > 0:
                    # 오버클럭 할인 적용
                    if getattr(actor, 'overclock_active', False):
                        discount = int(getattr(actor, 'overclock_data', {}).get('ram_cost_discount', 0))
                        ram_cost_val = max(0, ram_cost_val - discount)
                    cost_parts.append(f"RAM {ram_cost_val}")

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

            # 과부하 사용 여부 표기
            name = self._decorate_overload_name(skill, name)

            desc = getattr(skill, 'description', '')

            # 사용 불가 시 이유 추가
            full_desc = f"{desc}\n{reason}" if not can_use and reason else desc

            items.append(MenuItem(
                text=f"{name}{cost_text}",
                description=full_desc,
                enabled=can_use,
                value=skill
            ))

        # 합체기 메뉴 아이템 추가
        if combo_skills:
            for combo in combo_skills:
                gauge = self.combat_manager.party.teamwork_gauge if self.combat_manager.party else 0
                can_use_combo = gauge >= combo.gauge_cost
                jobs_text = " + ".join(combo.required_jobs)
                cost_text = f" (게이지 {combo.gauge_cost})"
                desc = f"{combo.description}\n필요: {jobs_text}"
                if not can_use_combo:
                    desc += f"\n게이지 부족 ({gauge}/{combo.gauge_cost})"
                items.append(MenuItem(
                    text=f"★ {combo.name}{cost_text}",
                    description=desc,
                    enabled=can_use_combo,
                    value=("combo", combo)
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

    def _get_overload_choice(self, skill: Any) -> Optional[bool]:
        """과부하 사용 여부 (스킬 ID별 저장, 기본값 True)"""
        metadata = getattr(skill, "metadata", {}) or {}
        if not metadata.get("overload_capable"):
            return None
        if skill.skill_id not in self.overload_selection:
            # 기본값: 안전하게 비과부하(좌측) 시작
            self.overload_selection[skill.skill_id] = metadata.get("overload_default", False)
        return self.overload_selection.get(skill.skill_id)

    def _set_overload_choice(self, skill: Any, enabled: bool) -> bool:
        """과부하 사용 여부를 설정하고 변경 여부 반환"""
        current = self._get_overload_choice(skill)
        if current is None:
            return False
        new_value = bool(enabled)
        changed = current != new_value
        self.overload_selection[skill.skill_id] = new_value
        return changed

    def _decorate_overload_name(self, skill: Any, base_name: str) -> str:
        """스킬 이름에 과부하 선택 상태를 덧붙여 표기"""
        choice = self._get_overload_choice(skill)
        if choice is None:
            return base_name
        state_label = "과부하" if choice else "일반"
        return f"{base_name} · {state_label}"

    def _apply_overload_choice(self, skill: Any) -> None:
        """선택된 과부하 여부를 스킬 메타데이터에 반영 (한 번 실행용)"""
        choice = self._get_overload_choice(skill)
        if choice is None:
            return
        if not hasattr(skill, "metadata") or skill.metadata is None:
            skill.metadata = {}
        skill.metadata["_use_overload"] = bool(choice)

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

        # 디버깅: revive_crystal이 없으면 강제로 추가
        has_revive_crystal = False
        revive_crystal_count = 0
        for slot in self.inventory.slots:
            if slot and slot.item:
                item_id = getattr(slot.item, 'item_id', None)
                item_name = getattr(slot.item, 'name', 'Unknown')
                logger.debug(f"[인벤토리 확인] {item_name} (ID: {item_id})")
                if item_id == 'revive_crystal':
                    has_revive_crystal = True
                    revive_crystal_count += slot.quantity

        logger.info(f"[디버깅] revive_crystal 보유 개수: {revive_crystal_count}")

        if not has_revive_crystal or revive_crystal_count < 1:
            logger.info("[디버깅] revive_crystal이 없어서 강제로 추가합니다")
            try:
                from src.equipment.item_system import ItemGenerator
                revive_crystal = ItemGenerator.create_consumable("revive_crystal")
                success = self.inventory.add_item(revive_crystal)
                if success:
                    logger.info("[디버깅] revive_crystal 추가 성공")
                else:
                    logger.error("[디버깅] revive_crystal 추가 실패: 인벤토리 가득 참")
            except Exception as e:
                logger.error(f"[디버깅] revive_crystal 생성/추가 실패: {e}")

        for slot_index, slot in enumerate(self.inventory.slots):
            if not slot or not slot.item:
                logger.debug(f"[전투 아이템 메뉴] 슬롯 {slot_index}: 빈 슬롯")
                continue

            item = slot.item
            item_name = getattr(item, 'name', '알 수 없는 아이템')
            item_type = getattr(item, 'item_type', None)
            item_class = type(item).__name__
            effect_type = getattr(item, 'effect_type', 'unknown')

            logger.info(f"[전투 아이템 메뉴] 슬롯 {slot_index}: {item_name} (타입: {item_type}, 클래스: {item_class}, effect_type: {effect_type})")

            # 요리 아이템은 전투 중 사용 불가
            if isinstance(item, CookedFood):
                logger.debug(f"[전투 아이템 메뉴] {item_name}: CookedFood로 필터링됨")
                continue

            # Consumable 또는 item_type이 CONSUMABLE인 아이템만 표시
            is_consumable = isinstance(item, Consumable) or item_type == ItemType.CONSUMABLE

            if not is_consumable:
                logger.warning(f"[전투 아이템 메뉴] {item_name}: Consumable이 아님 - 필터링됨 (isinstance: {isinstance(item, Consumable)}, item_type: {item_type})")
                continue

            logger.info(f"[전투 아이템 메뉴] {item_name}: 메뉴에 추가됨 (effect_type: {effect_type})")
            
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
        # 가능성 선택 상태 디버그
        if self.state == CombatUIState.POSSIBILITY_SELECT:
            print(f"[가능성UI] handle_input() 호출됨! action={action}, slots={len(self.possibility_slots) if self.possibility_slots else 0}")
        
        # ESC나 창 닫기는 무시 (전투 중에는 도주 명령으로만 종료 가능)
        if action == GameAction.ESCAPE or action == GameAction.QUIT:
            return False

        if self.state == CombatUIState.BATTLE_END:
            return True

        # 멀티플레이: WAITING_REMOTE_ACTION 상태 (레거시, 현재는 비차단 방식 사용)
        # 이 상태는 더 이상 진입하지 않으므로 입력을 차단하지 않음

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

        # 카드 선택 (마술사)
        elif self.state == CombatUIState.CARD_SELECT:
            return self._handle_card_select(action)

        # 선택형 스킬 (서약/피날레 등)
        elif self.state == CombatUIState.CHOICE_SELECT:
            return self._handle_choice_select(action)

        # 가능성 선택 (시간술사)
        elif self.state == CombatUIState.POSSIBILITY_SELECT:
            return self._handle_possibility_select(action)

        # 기믹 상세 보기
        elif self.state == CombatUIState.GIMMICK_VIEW:
            return self._handle_gimmick_view(action)

        # 체인어빌리티 선택
        elif self.state == CombatUIState.CHAIN_ABILITY_SELECT:
            return self._handle_chain_ability_select(action)

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

    def _get_local_player_id(self) -> Optional[str]:
        """멀티플레이 로컬 플레이어 ID를 안정적으로 가져옵니다."""
        local_player_id = self.local_player_id
        if local_player_id:
            return local_player_id

        if self.session:
            local_player_id = getattr(self.session, 'local_player_id', None)
            if local_player_id:
                return local_player_id

        try:
            from src.multiplayer.game_mode import get_game_mode_manager
            game_mode_manager = get_game_mode_manager()
            return getattr(game_mode_manager, 'local_player_id', None) if game_mode_manager else None
        except Exception:
            return None

    # ── Phase 4: 멀티플레이 콜백 핸들러 ──────────────────────────────

    def _on_mp_remote_action_executed(self, actor: Any, result: Any):
        """
        호스트: 원격 플레이어의 액션이 실행 완료되었을 때 콜백

        WAITING_REMOTE_ACTION 상태를 해제하고 결과를 UI에 표시합니다.

        Args:
            actor: 행동한 캐릭터
            result: 액션 실행 결과
        """
        # _pending_remote_actors에서 제거 (비차단 방식)
        actor_pid = getattr(actor, 'player_id', None)
        actor_id = getattr(actor, 'id', None)
        if actor_pid and actor_id:
            remote_key = f"{actor_pid}:{actor_id}"
            self._pending_remote_actors.pop(remote_key, None)

        # 액션 결과 표시
        if isinstance(result, dict):
            self._show_action_result(result)

        # 행동 후 대기 시간 설정
        self._set_action_delay(self.action_delay_max, actor)

        actor_name = getattr(actor, 'name', 'Unknown')
        logger.info(f"[호스트] 원격 플레이어 액션 실행 완료: {actor_name}")

        # WAITING_REMOTE_ACTION 상태였다면 해제 (레거시 호환)
        if self.state == CombatUIState.WAITING_REMOTE_ACTION:
            self.current_actor = None
            self.state = CombatUIState.WAITING_ATB

            # 전투 종료 확인
            from src.combat.combat_manager import CombatState as CS
            if self.combat_manager.state in [CS.VICTORY, CS.DEFEAT, CS.FLED]:
                if not self.battle_ended:
                    self.battle_ended = True
                    self.battle_result = self.combat_manager.state
                    self.state = CombatUIState.BATTLE_END

    def _on_mp_action_selection_start(self, actor_id: str, actor_name: str, player_id: str):
        """
        클라이언트: 호스트로부터 ACTION_SELECTION_START 수신 시 콜백

        자신의 캐릭터 턴이 도래했음을 수신하여 행동 메뉴를 활성화합니다.

        Args:
            actor_id: 행동할 캐릭터 ID
            actor_name: 행동할 캐릭터 이름
            player_id: 대상 플레이어 ID
        """
        # 자신에게 해당하는 메시지인지 확인
        local_player_id = self._get_local_player_id()
        if local_player_id and player_id != local_player_id:
            return

        # 해당 캐릭터를 current_actor로 설정
        if self.combat_sync_manager:
            actor = self.combat_sync_manager._find_character_by_id(actor_id)
            if actor:
                self.current_actor = actor
                self.action_menu = self._create_action_menu(actor)
                self.state = CombatUIState.ACTION_MENU
                self.add_message(f"{actor_name}의 턴!", (100, 255, 255))
                from src.audio import play_sfx
                play_sfx("ui", "turn_ready")
                logger.info(f"[클라이언트] 액션 선택 시작: {actor_name} (ID: {actor_id})")
            else:
                logger.warning(f"[클라이언트] 액션 선택 시작 실패: 액터를 찾을 수 없음 ({actor_id})")

    def _on_mp_action_result(self, result_data: Dict[str, Any]):
        """
        클라이언트: 호스트로부터 ACTION_RESULT 수신 시 콜백

        호스트에서 실행된 액션 결과를 수신하여 UI에 표시합니다.

        Args:
            result_data: 액션 실행 결과 데이터
        """
        # 결과를 메시지로 표시
        if isinstance(result_data, dict):
            self._show_action_result(result_data)
        logger.debug(f"[클라이언트] 액션 결과 수신: {list(result_data.keys()) if isinstance(result_data, dict) else result_data}")

    def _on_mp_combat_end(self, result: str, rewards: Optional[Dict[str, Any]]):
        """
        클라이언트: 호스트로부터 COMBAT_END 수신 시 콜백

        전투 루프를 종료하고 결과 화면을 표시합니다.

        Args:
            result: 전투 결과 ("victory", "defeat", "fled")
            rewards: 보상 데이터
        """
        self._mp_combat_end_received = True
        self._mp_combat_end_result = result
        logger.info(f"[클라이언트] 전투 종료 수신: {result}")

        # CombatManager 상태도 갱신
        try:
            from src.combat.combat_manager import CombatState as CS
            self.combat_manager.state = CS(result)
        except (ValueError, TypeError):
            pass

        # 전투 종료 처리
        if not self.battle_ended:
            self.battle_ended = True
            self.battle_result = self.combat_manager.state
            self.state = CombatUIState.BATTLE_END

    def _select_next_ready_actor(self, ready: List[Any], is_multiplayer: bool) -> Optional[Any]:
        """
        다음 처리할 행동자를 선택합니다.

        멀티플레이에서는 원격 플레이어 캐릭터가 맨 앞에 있더라도 로컬 입력을 막지 않도록
        원격 아군을 건너뛰고, 적/봇/로컬 아군 순서로 가능한 첫 전투원을 선택합니다.
        """
        if not ready:
            return None

        if not is_multiplayer:
            player_input_states = [
                CombatUIState.ACTION_MENU, CombatUIState.SKILL_MENU, CombatUIState.ITEM_MENU,
                CombatUIState.TARGET_SELECT, CombatUIState.CARD_SELECT, CombatUIState.CHOICE_SELECT,
                CombatUIState.POSSIBILITY_SELECT, CombatUIState.GIMMICK_VIEW
            ]
            if getattr(self, 'state', None) in player_input_states and getattr(self, 'current_actor', None) is not None:
                for combatant in ready:
                    if combatant == self.current_actor:
                        continue
                    # 적이거나 자동 봇 캐릭터인 경우에만 불릿타임 도중 새치기(인터럽트) 허용
                    if combatant in self.combat_manager.enemies:
                        return combatant
                    combatant_player_id = getattr(combatant, 'player_id', None)
                    if combatant_player_id and str(combatant_player_id).startswith('bot_'):
                        return combatant
            return ready[0]

        # 호스트는 모든 캐릭터의 턴을 처리해야 함 (원격 아군 포함)
        # 원격 아군 턴 시 WAITING_REMOTE_ACTION + ACTION_SELECTION_START 전송
        if getattr(self, 'is_mp_host', False):
            return ready[0] if ready else None

        # 클라이언트: 원격 아군 건너뛰기 (호스트의 ACTION_SELECTION_START 콜백으로만 턴 활성화)
        local_player_id = self._get_local_player_id()
        if not local_player_id:
            return ready[0]

        for combatant in ready:
            if combatant in self.combat_manager.enemies:
                return combatant

            combatant_player_id = getattr(combatant, 'player_id', None)
            if not combatant_player_id:
                return combatant

            if str(combatant_player_id).startswith('bot_'):
                return combatant

            if combatant_player_id == local_player_id:
                return combatant

        return None

    def _is_local_controllable_actor(self, actor: Any, is_multiplayer: bool) -> bool:
        """
        현재 UI 인스턴스에서 직접 조작 가능한 전투원인지 확인합니다.
        """
        if not is_multiplayer:
            return True

        actor_player_id = getattr(actor, 'player_id', None)
        if not actor_player_id:
            return True

        if str(actor_player_id).startswith('bot_'):
            return True

        local_player_id = self._get_local_player_id()
        if not local_player_id:
            return True

        return str(actor_player_id) == str(local_player_id)

    def _select_next_auto_advance_ally(self, ready: List[Any], is_multiplayer: bool) -> Optional[Any]:
        """
        행동 직후 즉시 UI를 넘길 다음 아군을 선택합니다.

        멀티플레이에서는 다른 플레이어의 캐릭터로 호스트 UI가 자동 전환되지 않도록
        로컬 조작 가능한 아군만 선택합니다.
        """
        if not ready:
            return None

        for combatant in ready:
            if combatant not in self.combat_manager.allies:
                continue
            if self._is_local_controllable_actor(combatant, is_multiplayer):
                return combatant

        return None

    def _set_action_delay(self, frames: int, actor: Optional[Any] = None) -> None:
        """
        행동 지연 타이머를 설정합니다.

        멀티플레이에서는 지연 소유 플레이어를 함께 기록해
        다른 플레이어의 준비된 입력이 전역 지연에 막히지 않도록 합니다.
        """
        self.action_delay_frames = max(0, int(frames))
        if self.action_delay_frames <= 0:
            self.action_delay_owner_player_id = None
            return

        actor_player_id = getattr(actor, 'player_id', None) if actor is not None else None
        self.action_delay_owner_player_id = str(actor_player_id) if actor_player_id else None

    def _is_action_delay_blocking_actor(self, actor: Any, is_multiplayer: bool) -> bool:
        """
        현재 행동 지연이 해당 전투원의 턴 처리를 막는지 확인합니다.

        싱글플레이는 기존처럼 전역 지연을 유지하고,
        멀티플레이는 같은 플레이어 소유 액터만 지연 영향을 받습니다.
        """
        if self.action_delay_frames <= 0:
            return False

        if not is_multiplayer:
            return True

        delay_owner = self.action_delay_owner_player_id
        if not delay_owner:
            # 소유자 정보가 없으면 기존처럼 전역 지연으로 처리
            return True

        actor_player_id = getattr(actor, 'player_id', None)
        if not actor_player_id:
            return True

        return str(actor_player_id) == delay_owner

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
            if selected_item and selected_item.enabled:
                play_sfx("ui", "cursor_select")  # 선택 효과음
                self.selected_action = selected_item.value
                self._on_action_selected()
            elif selected_item:
                logger.warning(f"[COMBAT_UI] 비활성화된 항목 선택 시도: {selected_item.text}")
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
        elif action == GameAction.MOVE_LEFT or action == GameAction.MOVE_RIGHT:
            selected_item = self.skill_menu.get_selected_item()
            if selected_item and selected_item.value:
                skill = selected_item.value
                metadata = getattr(skill, "metadata", {}) or {}
                if metadata.get("overload_capable"):
                    desired = action == GameAction.MOVE_RIGHT
                    changed = self._set_overload_choice(skill, desired)
                    if changed:
                        # 현재 커서 위치를 기억하고 메뉴를 새로 생성해 표기 업데이트
                        prev_index = self.skill_menu.cursor_index
                        prev_scroll = self.skill_menu.scroll_offset
                        self.skill_menu = self._create_skill_menu(self.current_actor)
                        # 기존 위치 복원 (가능한 경우)
                        if 0 <= prev_index < len(self.skill_menu.items):
                            self.skill_menu.cursor_index = prev_index
                            # 스크롤 보정
                            if self.skill_menu.cursor_index < self.skill_menu.scroll_offset:
                                self.skill_menu.scroll_offset = self.skill_menu.cursor_index
                            elif self.skill_menu.cursor_index >= self.skill_menu.scroll_offset + self.skill_menu.max_visible_items:
                                self.skill_menu.scroll_offset = self.skill_menu.cursor_index - self.skill_menu.max_visible_items + 1
                        else:
                            self.skill_menu.scroll_offset = prev_scroll
                        self.add_message(f"과부하 {'사용' if desired else '해제'}: {skill.name}", (180, 200, 255))
                        play_sfx("ui", "cursor_move")
        elif action == GameAction.CONFIRM:
            selected_item = self.skill_menu.get_selected_item()
            if selected_item:
                if selected_item.value is None:  # 뒤로가기
                    play_sfx("ui", "cursor_select")  # 선택 효과음
                    self.state = CombatUIState.ACTION_MENU
                elif not selected_item.enabled:
                    # 비활성화된 스킬은 선택 불가 - 경고음 또는 메시지
                    play_sfx("ui", "cursor_error")  # 에러 효과음
                    self.add_message("사용할 수 없는 스킬입니다!", (255, 100, 100))
                else:
                    play_sfx("ui", "cursor_select")  # 선택 효과음
                    # 합체기 처리
                    if isinstance(selected_item.value, tuple) and selected_item.value[0] == "combo":
                        combo_skill = selected_item.value[1]
                        self._execute_combo_skill(combo_skill)
                    else:
                        self.selected_skill = selected_item.value
                        # 과부하 선택 상태를 메타데이터에 반영
                        self._apply_overload_choice(self.selected_skill)
                        self._start_target_selection()
        elif action == GameAction.CANCEL:
            self.state = CombatUIState.ACTION_MENU

        return False

    def _execute_combo_skill(self, combo_skill):
        """합체기 실행"""
        # 타겟 결정: single이면 첫 번째 살아있는 적
        target = None
        for effect in combo_skill.effects:
            if effect.get("target") == "single":
                alive_enemies = [e for e in self.combat_manager.enemies if getattr(e, 'is_alive', True)]
                if alive_enemies:
                    target = alive_enemies[0]
                break

        result = self.combat_manager.execute_combo_skill(combo_skill, target)
        if result.get("success"):
            # 합체기 연출 메시지
            self.add_message(f"★ {combo_skill.name} 발동! ★", (255, 215, 0))
            for effect_info in result.get("effects", []):
                if effect_info["type"] == "damage":
                    self.add_message(
                        f"  {effect_info['target']}에게 {effect_info['damage']} 데미지!",
                        (255, 100, 100)
                    )
                elif effect_info["type"] == "heal":
                    self.add_message(
                        f"  {effect_info['target']} HP +{effect_info['amount']}",
                        (100, 255, 100)
                    )

            # 턴 종료: 체인어빌리티 체크 후 행동 딜레이 설정
            self.state = CombatUIState.EXECUTING
            if self.combat_manager.pending_chain_abilities:
                self._enter_chain_ability_select()
                return
            self._set_action_delay(self.action_delay_max, self.current_actor)
            self.current_actor = None
        else:
            self.add_message(f"합체기 실패: {result.get('message', '')}", (255, 100, 100))

    def _handle_target_select(self, action: GameAction) -> bool:
        """대상 선택 입력 처리"""
        # ALL_ALLIES 모드: 전체 아군 선택 (커서 이동 무시)
        if self.all_allies_mode:
            if action == GameAction.CONFIRM:
                play_sfx("ui", "cursor_select")
                # 전체 아군을 타겟으로 설정
                self.selected_target = self.combat_manager.party
                self.all_allies_mode = False
                self._execute_current_action()
            elif action == GameAction.CANCEL:
                # 취소 - 이전 상태로
                self.all_allies_mode = False
                if self.selected_action == ActionType.SKILL:
                    self.state = CombatUIState.SKILL_MENU
                elif self.selected_action == ActionType.ITEM:
                    self.state = CombatUIState.ITEM_MENU
                else:
                    self.state = CombatUIState.ACTION_MENU
                self.selected_skill = None
                self.selected_item = None
                self.selected_item_index = None
            # 커서 이동 무시 (MOVE_UP, MOVE_DOWN 등)
            return False

        # 저장된 타겟 리스트 사용
        targets = self.current_target_list

        # 부활 크리스탈 사용 시에는 죽은 파티원도 선택 가능
        is_revive_crystal = False
        if self.selected_action == ActionType.ITEM and self.selected_item:
            effect_type = getattr(self.selected_item, 'effect_type', '')
            if effect_type == 'revive_crystal':
                is_revive_crystal = True

        # 부활 스킬 여부 확인
        from src.multiplayer.skill_revival_handler import SkillRevivalHandler
        revival_handler = SkillRevivalHandler(None)
        is_revival_skill = self.selected_skill and revival_handler.is_revival_skill(self.selected_skill)

        # 부활 크리스탈이나 저주/부활 스킬인 경우에만 살아있는 대상 필터링 건너뛰기
        if is_revive_crystal or is_revival_skill:
            # 부활 관련: 모든 타겟 선택 가능 (죽은 파티원 포함)
            valid_indices = list(range(len(targets)))
        else:
            # 일반 아이템/스킬: 살아있는 대상만 선택 가능
            valid_indices = [i for i, e in enumerate(targets) if getattr(e, 'is_alive', True)]

        if not valid_indices:
            return False

        if self.target_cursor not in valid_indices:
            self.target_cursor = valid_indices[0]

        if action == GameAction.MOVE_UP or action == GameAction.MOVE_LEFT:
            # 이전 대상으로 이동
            current_pos = valid_indices.index(self.target_cursor) if self.target_cursor in valid_indices else 0
            new_pos = (current_pos - 1) % len(valid_indices)
            self.target_cursor = valid_indices[new_pos]
        elif action == GameAction.MOVE_DOWN or action == GameAction.MOVE_RIGHT:
            # 다음 대상으로 이동
            current_pos = valid_indices.index(self.target_cursor) if self.target_cursor in valid_indices else 0
            new_pos = (current_pos + 1) % len(valid_indices)
            self.target_cursor = valid_indices[new_pos]
        elif action == GameAction.CONFIRM:
            play_sfx("ui", "cursor_select")  # 선택 효과음
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
                    play_sfx("ui", "cursor_select")  # 선택 효과음
                    self.state = CombatUIState.ACTION_MENU
                else:
                    play_sfx("ui", "cursor_select")  # 선택 효과음
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
                            item_name = getattr(self.selected_item, 'name', 'Unknown')
                            item_class = type(self.selected_item).__name__
                            self.logger.info(f"아이템 사용: {item_name} (클래스: {item_class}), effect_type={effect_type}, is_consumable={is_consumable}")
                            # AOE 공격 아이템은 타겟 선택 없이 바로 실행
                            if effect_type in ["aoe_fire", "aoe_ice", "poison_bomb", "thunder_grenade", 
                                               "attack_fire", "attack_ice", "attack_lightning", "attack_poison", 
                                               "attack_explosive", "attack_aoe",
                                               "debuff_attack", "debuff_defense", "debuff_speed", "smoke_bomb", "break_brv"]:
                                # AOE 아이템: 타겟 선택 없이 바로 실행 (target=None)
                                self.selected_target = None
                                self._execute_current_action()
                            elif effect_type in ["single_lightning", "acid_flask", "damage"]:
                                # 단일 타겟 공격: 적 대상 선택
                                self.current_target_list = self.combat_manager.enemies
                                self.target_cursor = 0
                                self.state = CombatUIState.TARGET_SELECT
                            elif effect_type == "revive_crystal":
                                # 부활 크리스탈: 죽은 아군만 대상으로 선택
                                self.logger.info(f"=== 부활 크리스탈 타겟 선택 시작: {item_name} ===")
                                dead_party_members = []
                                for member in self.combat_manager.party:
                                    is_alive = getattr(member, 'is_alive', True)
                                    current_hp = getattr(member, 'current_hp', 1)
                                    name = getattr(member, 'name', str(member))
                                    self.logger.info(f"파티원 체크: {name}, is_alive={is_alive}, current_hp={current_hp}")
                                    if not is_alive or current_hp <= 0:
                                        dead_party_members.append(member)
                                        self.logger.info(f"  -> 죽은 파티원으로 추가: {name}")
                                self.logger.info(f"부활 크리스탈 사용: 죽은 파티원 {len(dead_party_members)}명 발견")
                                if dead_party_members:
                                    self.current_target_list = dead_party_members
                                    self.target_cursor = 0
                                    self.state = CombatUIState.TARGET_SELECT
                                    self.logger.info(f"타겟 선택 모드로 전환: {len(dead_party_members)}명의 죽은 파티원")
                                else:
                                    # 죽은 아군이 없음
                                    self.add_message("부활시킬 아군이 없습니다!")
                                    self.state = CombatUIState.ACTION_MENU
                                    self.logger.info("죽은 파티원이 없어 액션 메뉴로 복귀")
                            elif effect_type == "camp_rest":
                                # 텐트 등 아군 전체 대상 아이템
                                self.logger.info(f"아군 전체 대상 아이템: {effect_type}")
                                self.current_target_list = self.combat_manager.party
                                self.all_allies_mode = True
                                self.target_cursor = 0
                                self.state = CombatUIState.TARGET_SELECT
                            else:
                                # revive_crystal이 아닌 다른 effect_type: 회복/버프 아이템으로 처리
                                self.logger.info(f"부활 크리스탈이 아닌 다른 effect_type: {effect_type} - 회복 아이템으로 처리")
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
                # 과부하 사용 여부 반영
                self._apply_overload_choice(self.selected_skill)
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
            # 사무라이는 방어 대신 미키리 카마에(패링) 사용
            if hasattr(self.current_actor, 'gimmick_type') and self.current_actor.gimmick_type == "kenshin_system":
                from src.character.skills.skill_manager import get_skill_manager
                skill_manager = get_skill_manager()
                parry_skill = skill_manager.get_skill("samurai_mikiri_kamae")
                if parry_skill:
                    self.selected_action = ActionType.SKILL
                    self.selected_skill = parry_skill
                    self._start_target_selection()
                    return
            # 일반 방어
            self._execute_current_action()

        elif self.selected_action == ActionType.FLEE:
            # 도망도 대상 선택 불필요
            self._execute_current_action()

        else:
            # BRV/HP 공격 - 대상 선택
            self._start_target_selection()

    def _start_target_selection(self, skip_choice: bool = False):
        """대상 선택 시작"""
        from src.character.skill_types import SkillTargetType

        # 스킬의 target_type에 따라 대상 결정
        if self.selected_skill:
            # 카드 선택이 필요한 스킬인지 확인 (마술사)
            metadata = getattr(self.selected_skill, 'metadata', {}) or {}
            logger.debug(f"[카드선택] 스킬: {self.selected_skill.name}, metadata: {metadata}")

            # 선택형 스킬(서약/피날레 등) 처리
            if not skip_choice and metadata.get('choice_skill'):
                # AI/적은 자동으로 첫 선택지를 사용
                if self.current_actor not in getattr(self.combat_manager, 'allies', []):
                    self._apply_default_choice(metadata)
                else:
                    if self._start_choice_selection(metadata):
                        return
                    # 선택 메뉴 생성 실패 시 자동 선택
                    self._apply_default_choice(metadata)

            if metadata.get('select_card_from_hand'):
                logger.info(f"[카드선택] 카드 선택 UI 시작: {self.selected_skill.name}")
                self._start_card_selection()
                return
            
            # 가능성 시스템 스킬인지 확인 (시간술사)
            if metadata.get('possibility_system'):
                action = metadata.get('action', 'summon_single')
                if action in ['summon_single', 'summon_dual', 'overwrite_slot']:
                    logger.info(f"[가능성 선택] 가능성 선택 UI 시작: {self.selected_skill.name}")
                    if not self._start_possibility_selection(action):
                        # 실패 - 스킬 메뉴로 복귀
                        self.state = CombatUIState.SKILL_MENU
                        self.selected_skill = None
                    return
            
            target_type = getattr(self.selected_skill, 'target_type', 'single_enemy')

            # "self" 타겟은 타겟 선택 건너뛰기
            if target_type == "self":
                # 타겟 선택 없이 바로 실행
                self.selected_target = self.current_actor
                self._execute_current_action()
                return

            # \"ALL_ALLIES\" 또는 \"party\" 타겟은 아군 전체를 시각적으로 선택하는 UI 표시
            if target_type == SkillTargetType.ALL_ALLIES or target_type in ("all_allies", "party"):
                # 아군 전체를 타겟으로 설정하고 TARGET_SELECT 상태로 전환
                self.current_target_list = self.combat_manager.party
                self.all_allies_mode = True
                self.target_cursor = 0
                self.state = CombatUIState.TARGET_SELECT
                return

            # 문자열 target_type을 Enum으로 매핑 (하위 호환성)
            ally_targets = (
                SkillTargetType.SINGLE_ALLY,
                SkillTargetType.SELF,
                "single_ally",
                "ally",      # 문자열 지원
            )

            # 아군 타겟팅 스킬 (회복 등)
            if target_type in ally_targets:
                # 부활 스킬인 경우 죽은 아군만 대상으로
                from src.multiplayer.skill_revival_handler import SkillRevivalHandler
                revival_handler = SkillRevivalHandler(None)  # revival_system은 None으로도 동작
                if revival_handler.is_revival_skill(self.selected_skill):
                    # 죽은 아군만 대상으로
                    dead_party_members = []
                    for member in self.combat_manager.party:
                        is_alive = getattr(member, 'is_alive', True)
                        current_hp = getattr(member, 'current_hp', 1)
                        if not is_alive or current_hp <= 0:
                            dead_party_members.append(member)
                    self.current_target_list = dead_party_members
                    self.logger.info(f"부활 스킬 사용: 죽은 파티원 {len(dead_party_members)}명 대상")
                else:
                    self.current_target_list = self.combat_manager.party
            else:
                # 적 타겟팅 스킬 (공격 등)
                self.current_target_list = self.combat_manager.enemies
        else:
            # 기본 공격은 적 타겟
            self.current_target_list = self.combat_manager.enemies

        # 부활 스킬 여부 확인
        from src.multiplayer.skill_revival_handler import SkillRevivalHandler
        revival_handler = SkillRevivalHandler(None)
        is_revival = self.selected_skill and revival_handler.is_revival_skill(self.selected_skill)

        # 살아있는 대상만 필터링 (부활 스킬 제외)
        if is_revival:
            valid_targets = self.current_target_list
        else:
            valid_targets = [e for e in self.current_target_list if getattr(e, 'is_alive', True)]

        if not valid_targets:
            # 모든 대상이 죽었으면 행동 메뉴로 돌아감
            self.state = CombatUIState.ACTION_MENU
            return

        # 첫 번째 유효한 대상의 인덱스로 커서 설정
        self.target_cursor = 0
        for i, target in enumerate(self.current_target_list):
            if target in valid_targets:
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

    def _start_possibility_selection(self, action: str) -> bool:
        """가능성 슬롯 선택 시작 (시간술사)"""
        from src.character.skills.skill_manager import get_skill_manager
        
        if not self.current_actor:
            return False
        
        slots = getattr(self.current_actor, 'possibility_slots', [])
        if not slots:
            self.add_message("저장된 가능성이 없습니다!", (255, 100, 100))
            return False
        
        # 최소 필요 개수 확인
        min_required = 2 if action == "summon_dual" else 1
        if len(slots) < min_required:
            self.add_message(f"가능성 {min_required}개 이상 필요! (현재: {len(slots)}개)", (255, 100, 100))
            return False
        
        # 스킬 이름 추가
        skill_manager = get_skill_manager()
        enriched_slots = []
        for slot in slots:
            skill = skill_manager.get_skill(slot.get('skill_id', ''))
            enriched_slot = slot.copy()
            enriched_slot['skill_name'] = skill.name if skill else slot.get('skill_id', '???')
            enriched_slots.append(enriched_slot)
        
        # 상태 설정
        self.possibility_slots = enriched_slots
        self.possibility_cursor = 0
        self.possibility_selected = []
        self.possibility_action = action
        self.possibility_max_select = 2 if action == "summon_dual" else 1
        self.state = CombatUIState.POSSIBILITY_SELECT
        
        logger.info(f"[가능성 선택] 시작: {action}, 슬롯 {len(slots)}개, state={self.state}")
        logger.info(f"[가능성 선택] possibility_slots={len(self.possibility_slots)}개, enriched: {[s.get('skill_name') for s in self.possibility_slots]}")
        return True

    def _handle_possibility_select(self, action: GameAction) -> bool:
        """가능성 선택 입력 처리"""
        from src.audio.audio_manager import play_sfx
        
        if not self.possibility_slots:
            self.state = CombatUIState.SKILL_MENU
            return False
        
        if action == GameAction.MOVE_UP:
            self.possibility_cursor = max(0, self.possibility_cursor - 1)
            play_sfx("ui", "cursor_move")
        elif action == GameAction.MOVE_DOWN:
            self.possibility_cursor = min(len(self.possibility_slots) - 1, self.possibility_cursor + 1)
            play_sfx("ui", "cursor_move")
        elif action == GameAction.CONFIRM:
            if self.possibility_action == "summon_dual":
                # 다중 선택 모드 - 토글
                if self.possibility_cursor in self.possibility_selected:
                    self.possibility_selected.remove(self.possibility_cursor)
                    play_sfx("ui", "cursor_cancel")
                elif len(self.possibility_selected) < self.possibility_max_select:
                    self.possibility_selected.append(self.possibility_cursor)
                    play_sfx("ui", "cursor_select")
                    # 2개 선택 완료 시 자동 확정
                    if len(self.possibility_selected) >= 2:
                        self._confirm_possibility_selection()
                        return False
            else:
                # 단일 선택 모드 - 즉시 확정
                self.possibility_selected = [self.possibility_cursor]
                self._confirm_possibility_selection()
                play_sfx("ui", "cursor_select")
                return False
        elif action == GameAction.CANCEL:
            # 취소 - 스킬 메뉴로 복귀
            self.state = CombatUIState.SKILL_MENU
            self.selected_skill = None
            self.possibility_slots = []
            self.possibility_selected = []
            play_sfx("ui", "cursor_cancel")
            return False
        
        return False

    def _confirm_possibility_selection(self):
        """가능성 선택 확정"""
        if self.selected_skill and self.possibility_selected:
            if not hasattr(self.selected_skill, 'metadata') or self.selected_skill.metadata is None:
                self.selected_skill.metadata = {}
            self.selected_skill.metadata['_selected_indices'] = self.possibility_selected.copy()
            
            # 선택된 가능성 스킬의 타겟 타입 확인하여 타겟 선택 UI로 전환
            from src.character.skills.skill_manager import get_skill_manager
            skill_manager = get_skill_manager()
            
            # 첫 번째 선택된 스킬의 타겟 타입 확인
            first_slot_idx = self.possibility_selected[0]
            if first_slot_idx < len(self.possibility_slots):
                slot = self.possibility_slots[first_slot_idx]
                stored_skill_id = slot.get('skill_id')
                stored_skill = skill_manager.get_skill(stored_skill_id)
                
                if stored_skill:
                    target_type = getattr(stored_skill, 'target_type', 'single_enemy')
                    
                    # 아군 타겟
                    if target_type in ['ally', 'single_ally']:
                        self.current_target_list = self.combat_manager.party
                        
                        # 살아있는 대상만 필터링
                        alive_targets = [e for e in self.current_target_list if getattr(e, 'is_alive', True)]
                        if alive_targets:
                            self.target_cursor = 0
                            self.state = CombatUIState.TARGET_SELECT
                            
                            # 상태 초기화
                            self.possibility_slots = []
                            self.possibility_selected = []
                            return
                    
                    # 적 타겟 (single_enemy)
                    elif target_type == 'single_enemy':
                        self.current_target_list = self.combat_manager.enemies
                        
                        # 살아있는 대상만 필터링
                        alive_targets = [e for e in self.current_target_list if getattr(e, 'is_alive', True)]
                        if alive_targets:
                            self.target_cursor = 0
                            self.state = CombatUIState.TARGET_SELECT
                            
                            # 상태 초기화
                            self.possibility_slots = []
                            self.possibility_selected = []
                            return

            # 타겟 선택이 불필요하거나 실패한 경우 (기본값 실행)
            self.selected_target = self.combat_manager.enemies[0] if self.combat_manager.enemies else None
            self._execute_current_action()
        
        # 상태 초기화
        self.possibility_slots = []
        self.possibility_selected = []

    def _start_card_selection(self):
        """카드 선택 시작 (마술사)"""
        logger.info(f"[카드선택] _start_card_selection 호출됨, actor: {getattr(self.current_actor, 'name', None)}")
        if not self.current_actor:
            logger.warning("[카드선택] current_actor가 없음!")
            return
        
        # 손패 가져오기
        self.card_hand = getattr(self.current_actor, 'card_hand', [])
        logger.info(f"[카드선택] 손패: {len(self.card_hand)}장")
        
        if not self.card_hand:
            # 손패가 없으면 메시지 표시 후 스킬 메뉴로 복귀
            self.add_message("손패가 비어있습니다!", (255, 100, 100))
            self.state = CombatUIState.SKILL_MENU
            return
        
        self.card_cursor = 0
        self.selected_card = None
        self.state = CombatUIState.CARD_SELECT
        logger.info(f"[카드선택] 상태 변경: CARD_SELECT, {len(self.card_hand)}장")
        print(f"[카드UI] 상태 설정 완료! self.state = {self.state}")

    def _handle_card_select(self, action: GameAction) -> bool:
        """카드 선택 입력 처리"""
        if not self.card_hand:
            self.state = CombatUIState.SKILL_MENU
            return False
        
        if action == GameAction.MOVE_LEFT:
            self.card_cursor = max(0, self.card_cursor - 1)
        elif action == GameAction.MOVE_RIGHT:
            self.card_cursor = min(len(self.card_hand) - 1, self.card_cursor + 1)
        elif action == GameAction.CONFIRM:
            # 카드 선택 완료
            self.selected_card = self.card_hand[self.card_cursor]
            from src.character.skills.job_skills.magician_skills import get_card_name
            card_name = get_card_name(self.selected_card)
            self.add_message(f"[{card_name}] 선택!", (255, 200, 100))
            
            # 선택된 카드를 스킬 메타데이터에 저장
            if self.selected_skill:
                if not hasattr(self.selected_skill, 'metadata'):
                    self.selected_skill.metadata = {}
                self.selected_skill.metadata['_selected_card'] = self.selected_card
            
            # 타겟 선택으로 진행
            self._continue_target_selection_after_card()
        elif action == GameAction.CANCEL:
            # 취소 - 스킬 메뉴로 복귀
            self.state = CombatUIState.SKILL_MENU
            self.selected_card = None
            # 메타데이터 정리
            if self.selected_skill and hasattr(self.selected_skill, 'metadata'):
                self.selected_skill.metadata.pop('_selected_card', None)
        
        return False

    def _continue_target_selection_after_card(self):
        """카드 선택 후 타겟 선택 계속"""
        from src.character.skill_types import SkillTargetType
        
        if not self.selected_skill:
            self.state = CombatUIState.SKILL_MENU
            return
        
        target_type = getattr(self.selected_skill, 'target_type', 'single_enemy')
        
        # 적 타겟팅
        self.current_target_list = [e for e in self.combat_manager.enemies if getattr(e, 'is_alive', True)]
        if self.current_target_list:
            self.target_cursor = 0
            self.state = CombatUIState.TARGET_SELECT
        else:
            # 살아있는 적이 없으면 스킬 메뉴로
            self.state = CombatUIState.SKILL_MENU

    def _start_choice_selection(self, metadata: Dict[str, Any]) -> bool:
        """선택형 스킬(서약/피날레 등) 선택 UI 시작"""
        choices = metadata.get("choices") or []

        # 팔라딘 서약 등 gimmick 기반 선택지 보강
        if not choices and getattr(self.current_actor, "gimmick_type", None) == "oath_system":
            oaths = getattr(self.current_actor, "oaths", {})
            for oid, data in oaths.items():
                choices.append({
                    "id": oid,
                    "name": data.get("name", oid)
                })

        if not choices:
            return False

        items = []
        for ch in choices:
            label = ch.get("name") if isinstance(ch, dict) else str(ch)
            desc = ""
            if isinstance(ch, dict):
                desc = ch.get("description", "") or ""
                # 서약 선택인 경우 gimmick 데이터 기반 설명 생성
                if not desc and getattr(self.current_actor, "gimmick_type", None) == "oath_system":
                    choice_id = ch.get("id")
                    oath_desc = self._build_oath_description(choice_id)
                    if oath_desc:
                        desc = oath_desc
            items.append(MenuItem(text=label, value=ch, description=desc))

        title = metadata.get("choice_title") or "선택"
        self.choice_menu = CursorMenu(
            title=title,
            items=items,
            x=5,
            y=28,
            width=48,
            show_description=True
        )
        self.state = CombatUIState.CHOICE_SELECT
        return True

    def _apply_default_choice(self, metadata: Dict[str, Any]) -> None:
        """선택 메뉴 없이 기본 선택지 적용 (AI/적용 실패 시)"""
        choices = metadata.get("choices") or []
        if not choices and getattr(self.current_actor, "gimmick_type", None) == "oath_system":
            oaths = getattr(self.current_actor, "oaths", {})
            for oid, data in oaths.items():
                choices.append({"id": oid, "name": data.get("name", oid)})
        if not choices:
            return
        default_choice = choices[0]
        self._set_choice_metadata(default_choice)

    def _set_choice_metadata(self, choice: Any) -> None:
        """선택 결과를 스킬 메타데이터에 기록"""
        if not self.selected_skill:
            return
        if not hasattr(self.selected_skill, "metadata") or self.selected_skill.metadata is None:
            self.selected_skill.metadata = {}

        if isinstance(choice, dict):
            choice_id = choice.get("id")
            choice_name = choice.get("name", choice_id)
        else:
            choice_id = choice
            choice_name = str(choice)

        self.selected_skill.metadata["_selected_choice"] = choice_id
        self.selected_skill.metadata["_selected_choice_name"] = choice_name

    def _build_oath_description(self, oath_id: Optional[str]) -> str:
        """서약 선택 UI용 설명 생성"""
        if not oath_id or getattr(self.current_actor, "gimmick_type", None) != "oath_system":
            return ""
        oaths = getattr(self.current_actor, "oaths", {})
        data = oaths.get(oath_id, {})
        if not data:
            return ""
        concept = data.get("concept", "")
        reward_actions = data.get("reward_actions", [])
        reward_action = data.get("reward_action", "")
        faith_per_action = data.get("faith_per_action") or data.get("faith_per_purify") or data.get("faith_per_kill") or 0
        forbidden = data.get("forbidden_action", "")
        parts = []
        if concept:
            parts.append(f"역할: {concept}")
        # 보상 행동 요약
        reward_list = []
        if reward_action:
            reward_list.append(reward_action)
        reward_list.extend([a for a in reward_actions if a not in reward_list])
        if reward_list:
            action_map = {
                "take_damage": "피격",
                "heal": "치유",
                "purify": "정화",
                "kill": "처치",
                "buff": "버프",
                "attack": "공격"
            }
            mapped = [action_map.get(a, a) for a in reward_list]
            gain_str = f"신앙 +{faith_per_action}" if faith_per_action else "신앙 획득"
            parts.append(f"{gain_str}: {', '.join(mapped)}")
        if forbidden:
            forbid_map = {"attack": "공격 금지", "buff_heal": "버프/힐 금지"}
            parts.append(forbid_map.get(forbidden, forbidden))
        bonus = data.get("bonus_effects", {})
        bonus_parts = []
        if bonus.get("defense_multiplier"):
            bonus_parts.append(f"방어 +{int((bonus['defense_multiplier']-1)*100)}%")
        if bonus.get("attack_multiplier"):
            bonus_parts.append(f"공격 +{int((bonus['attack_multiplier']-1)*100)}%")
        if bonus.get("holy_damage_bonus"):
            bonus_parts.append(f"신성 피해 +{int(bonus['holy_damage_bonus']*100)}%")
        if bonus.get("heal_multiplier"):
            bonus_parts.append(f"치유 +{int((bonus['heal_multiplier']-1)*100)}%")
        if bonus.get("mp_regen_per_turn"):
            bonus_parts.append(f"턴당 MP +{bonus['mp_regen_per_turn']}")
        if bonus.get("can_intercept"):
            bonus_parts.append("대신 맞기 가능")
        if bonus_parts:
            parts.append("보너스: " + ", ".join(bonus_parts))
        penalty = data.get("violation_penalty", {})
        pen_parts = []
        if penalty.get("faith_loss"):
            pen_parts.append(f"신앙 -{penalty['faith_loss']}")
        if penalty.get("debuff_duration"):
            pen_parts.append(f"디버프 {penalty['debuff_duration']}턴")
        if penalty.get("attack_reduction"):
            pen_parts.append(f"공격 -{int(penalty['attack_reduction']*100)}%")
        if penalty.get("damage_reduction"):
            pen_parts.append(f"피해량 -{int(penalty['damage_reduction']*100)}%")
        if penalty.get("heal_reduction"):
            pen_parts.append(f"치유 -{int(penalty['heal_reduction']*100)}%")
        if pen_parts:
            parts.append("위반: " + ", ".join(pen_parts))
        return " | ".join(parts)

    def _handle_choice_select(self, action: GameAction) -> bool:
        """선택형 스킬 입력 처리"""
        if not self.choice_menu:
            self.state = CombatUIState.SKILL_MENU
            return False

        if action == GameAction.MOVE_UP:
            self.choice_menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            self.choice_menu.move_cursor_down()
        elif action == GameAction.CONFIRM:
            selected_item = self.choice_menu.get_selected_item()
            if selected_item:
                play_sfx("ui", "cursor_select")
                self._set_choice_metadata(selected_item.value)
                # 선택 완료 후 대상 선택 계속
                self.state = CombatUIState.SKILL_MENU  # 임시로 되돌렸다가
                self.choice_menu = None
                self._start_target_selection(skip_choice=True)
        elif action == GameAction.CANCEL:
            play_sfx("ui", "cursor_error")
            self.choice_menu = None
            self.state = CombatUIState.SKILL_MENU
        return False

    # ── 체인어빌리티 선택 UI ──

    def _enter_chain_ability_select(self):
        """체인어빌리티 선택 모드 진입"""
        results = self.combat_manager.pending_chain_abilities
        if not results:
            return

        self.chain_ability_results = results
        items = []
        for r in results:
            # 아군 이름 찾기
            ally_char = next(
                (c for c in self.combat_manager.allies
                 if hasattr(c, 'character_class') and c.character_class == r.ally_job),
                None
            )
            ally_name = getattr(ally_char, 'name', r.ally_job) if ally_char else r.ally_job
            cd = getattr(r, 'cooldown_remaining', 0)
            if cd > 0:
                label = f"[{ally_name}] {r.ability.name} (쿨다운 {cd}턴)"
                desc = f"재사용까지 {cd}턴 남음"
                items.append(MenuItem(text=label, value=r, description=desc, enabled=False))
            else:
                label = f"[{ally_name}] {r.ability.name}"
                desc = getattr(r.ability, 'description', '') or ''
                desc += f" (게이지 -{r.gauge_cost})"
                items.append(MenuItem(text=label, value=r, description=desc, enabled=True))

        self.chain_ability_menu = CursorMenu(
            title="체인어빌리티",
            items=items,
            x=5,
            y=33,
            width=50,
            show_description=True
        )
        self.state = CombatUIState.CHAIN_ABILITY_SELECT
        self.add_message("체인어빌리티 발동 가능!", (255, 220, 100))
        play_sfx("ui", "cursor_select")

    def _handle_chain_ability_select(self, action: GameAction) -> bool:
        """체인어빌리티 선택 입력 처리"""
        if not self.chain_ability_menu:
            self._exit_chain_ability_select()
            return False

        if action == GameAction.MOVE_UP:
            self.chain_ability_menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            self.chain_ability_menu.move_cursor_down()
        elif action == GameAction.CONFIRM:
            selected = self.chain_ability_menu.get_selected_item()
            if selected and selected.value:
                play_sfx("ui", "cursor_select")
                result = self.combat_manager.execute_chain_ability(selected.value)
                # 결과 메시지 표시
                ability_name = result.get("ability_name", "???")
                effects = result.get("effects", [])
                gauge_used = result.get("gauge_used", 0)
                msg = f"체인어빌리티 [{ability_name}] 발동! (게이지 -{gauge_used})"
                self.add_message(msg, (255, 200, 100))
                for eff in effects:
                    eff_type = eff.get("type", "")
                    if eff_type == "damage":
                        self.add_message(
                            f"  {eff['target']}에게 {eff['amount']} 데미지!",
                            (255, 100, 100)
                        )
                    elif eff_type == "heal":
                        self.add_message(
                            f"  {eff['target']} HP +{eff['amount']} 회복!",
                            (100, 255, 100)
                        )
                        # ── 회복 팝업 ──
                        heal_name = eff.get('target', '')
                        for ch in list(self.combat_manager.allies):
                            if getattr(ch, 'name', '') == heal_name:
                                self._trigger_damage_popup(ch, eff['amount'], "heal")
                                break
                    elif eff_type == "revive":
                        self.add_message(
                            f"  {eff['target']} 부활! (HP {eff['hp']})",
                            (255, 255, 100)
                        )
                    elif eff_type == "buff":
                        self.add_message(
                            f"  {eff.get('target', '아군')} {eff.get('buff_desc', '버프')} 적용!",
                            (100, 200, 255)
                        )
                    elif eff_type == "debuff":
                        self.add_message(
                            f"  적에게 {eff.get('desc', '디버프')} 적용!",
                            (200, 100, 255)
                        )
                    elif eff_type == "shield":
                        self.add_message(
                            f"  {eff['target']} BRV +{eff['amount']} 보호막!",
                            (100, 200, 200)
                        )
                    elif eff_type == "mp_restore":
                        self.add_message(
                            f"  {eff['target']} MP +{eff['amount']} 회복!",
                            (100, 150, 255)
                        )
                    elif eff_type == "brv_damage":
                        self.add_message(
                            f"  {eff['target']}의 BRV -{eff['amount']}!",
                            (255, 150, 50)
                        )
                        # ── 스킬 BRV 데미지 팝업 ──
                        eff_target_name = eff.get('target', '')
                        for ch in list(self.combat_manager.enemies) + list(self.combat_manager.allies):
                            if getattr(ch, 'name', '') == eff_target_name:
                                self._trigger_damage_popup(ch, eff['amount'], "brv")
                                break
                    elif eff_type == "status":
                        self.add_message(
                            f"  적 {eff.get('targets', 0)}명에게 {eff.get('status', '')} 부여!",
                            (200, 100, 200)
                        )
                    elif eff_type == "redirect":
                        self.add_message(
                            f"  피해 전환 활성! (경감 {int(eff.get('reduction', 0)*100)}%)",
                            (200, 200, 100)
                        )
                self._exit_chain_ability_select()
        elif action == GameAction.CANCEL:
            play_sfx("ui", "cursor_error")
            self.add_message("체인어빌리티를 사용하지 않았다.", (150, 150, 150))
            self._exit_chain_ability_select()
        return False

    def _exit_chain_ability_select(self):
        """체인어빌리티 선택 모드 종료"""
        self.combat_manager.pending_chain_abilities = []
        self.chain_ability_menu = None
        self.chain_ability_results = []
        # 행동 후 대기로 복귀
        self._set_action_delay(self.action_delay_max, self.current_actor)
        self.current_actor = None
        self.state = CombatUIState.EXECUTING

    def _render_chain_ability_select(self, console):
        """체인어빌리티 선택 패널 렌더링"""
        if self.chain_ability_menu:
            self.chain_ability_menu.render(console)
            # 하단 안내
            help_y = console.height - 2
            console.print(5, help_y, "[Z] 사용  [X] 패스", fg=(180, 180, 180))

    def _execute_current_action(self):
        """현재 선택된 행동 실행"""
        self.state = CombatUIState.EXECUTING

        # 튜플 형식이면 ActionType.SKILL로 변환
        action_type = self.selected_action
        if isinstance(self.selected_action, tuple):
            action_type = ActionType.SKILL  # 기본 공격 스킬도 스킬로 실행

        # 멀티플레이 모드 확인 (combat_sync_manager 존재 여부로 판별)
        is_multiplayer = self.combat_sync_manager is not None

        # 호스트 여부 확인
        is_host = self.is_mp_host
        if not is_host and self.session:
            local_player_id = self._get_local_player_id()
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

            kwargs = {}
            if action_type == ActionType.ITEM and self.selected_item:
                kwargs['item'] = self.selected_item
                kwargs['item_index'] = self.selected_item_index

            # 비동기 액션 요청 전송 - combat_sync_manager의 _schedule_async 사용
            # (전투 루프는 별도 스레드에서 동작하므로 run_coroutine_threadsafe 패턴 필요)
            scheduled = self.combat_sync_manager._schedule_async(
                self.combat_sync_manager.send_action_request(
                    player_id=local_player_id,
                    actor=self.current_actor,
                    action_type=action_type,
                    target=self.selected_target,
                    skill=self.selected_skill,
                    **kwargs
                )
            )
            if not scheduled:
                logger.error(f"멀티플레이 액션 전송 실패: 네트워크 이벤트 루프를 찾을 수 없음")

            logger.info(f"멀티플레이 액션 요청 전송: {local_player_id} - {actor_id} - {action_type.value if hasattr(action_type, 'value') else action_type}")

            # 클라이언트는 액션 요청 후 ATB 대기 상태로 전환
            self.state = CombatUIState.WAITING_ATB

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

            # 아이템 사용 시 파티클 이펙트
            if action_type == ActionType.ITEM and self.selected_item and self.effect_manager:
                item_target = self.selected_target or self.current_actor
                target_idx = None
                is_enemy = hasattr(item_target, 'enemy_id')
                if is_enemy:
                    for idx, e in enumerate(self.combat_manager.enemies):
                        if e is item_target:
                            target_idx = idx
                            break
                    if target_idx is not None and target_idx in self._enemy_rects:
                        rx, ry, rw, rh = self._enemy_rects[target_idx]
                        converter = getattr(self, '_cell_to_pixel_fn', None)
                        px, py = converter(rx + rw // 2, ry + rh // 2) if converter else (rx * 10 + 5, ry * 13 + 6)
                        trigger_item_effect(getattr(self.selected_item, 'name', ''), self.effect_manager, px, py)
                else:
                    for idx, a in enumerate(self.combat_manager.allies):
                        if a is item_target:
                            target_idx = idx
                            break
                    if target_idx is not None and target_idx in self._ally_rects:
                        rx, ry, rw, rh = self._ally_rects[target_idx]
                        converter = getattr(self, '_cell_to_pixel_fn', None)
                        px, py = converter(rx + rw // 2, ry + rh // 2) if converter else (rx * 10 + 5, ry * 13 + 6)
                        trigger_item_effect(getattr(self.selected_item, 'name', ''), self.effect_manager, px, py)

            # 멀티플레이 호스트: ACTION_RESULT 브로드캐스트
            if self.is_mp_host and self.combat_sync_manager and self.session and self.network_manager:
                if isinstance(result, dict) and self.current_actor:
                    self.combat_sync_manager.broadcast_action_result_sync(self.current_actor, result)

            # 결과 메시지 표시
            self._show_action_result(result)

            # 체인어빌리티 트리거 체크
            if self.combat_manager.pending_chain_abilities:
                self._enter_chain_ability_select()
                return

            # 행동 후 대기 시간 설정 (1.5초)
            self._set_action_delay(self.action_delay_max, self.current_actor)

            # 현재 액터의 플레이어 ID 저장 (다음 아군 확인 전에 저장)
            current_actor_player_id = getattr(self.current_actor, 'player_id', None) if self.current_actor else None
            
            # 상태 초기화 (다음 아군 확인을 위해 먼저 초기화)
            self.current_actor = None

            # 멀티플레이: 다음 행동 가능한 아군 확인
            if is_multiplayer and self.session and hasattr(self.combat_manager.atb, 'set_player_selecting'):
                # 다음 행동 가능한 아군이 있는지 확인
                ready_combatants = self.combat_manager.atb.get_action_order()
                next_ally = self._select_next_auto_advance_ally(ready_combatants, is_multiplayer=True)
                
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
                        play_sfx("ui", "turn_ready")
                    
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
        # 카드 선택 관련 초기화
        self.selected_card = None
        self.card_hand = []
        self.card_cursor = 0
        # 주의: state는 update()에서 delay 후 WAITING_ATB로 전환됨

        # 전투 종료 확인
        if self.combat_manager.state in [CombatState.VICTORY, CombatState.DEFEAT, CombatState.FLED]:
            self.battle_ended = True
            self.battle_result = self.combat_manager.state
            self.state = CombatUIState.BATTLE_END
            # BGM은 main.py에서 처리 (필드 BGM으로 전환하기 위해)
            # 멀티플레이 호스트: COMBAT_END 브로드캐스트
            if self.is_mp_host and self.combat_sync_manager and self.session and self.network_manager:
                result_str = self.combat_manager.state.value if hasattr(self.combat_manager.state, 'value') else str(self.combat_manager.state)
                self.combat_sync_manager.broadcast_combat_end_sync(result_str)

    def _resolve_popup_target(self, result: Dict[str, Any] = None):
        """팝업 대상 캐릭터 해석 (selected_target 우선, result dict 폴백)

        Args:
            result: 행동 결과 dict (None이면 selected_target만 시도)
        Returns:
            Character 객체 또는 None
        """
        # 1순위: UI에서 선택된 대상
        target = getattr(self, 'selected_target', None)
        if target is not None:
            return target

        if result is None:
            return None

        # 2순위: result dict에 target_obj가 있으면
        target = result.get('target_obj', None)
        if target is not None:
            return target

        # 3순위: result dict의 target (Character 객체 또는 이름 문자열)
        target_val = result.get('target', None)
        if target_val is not None:
            # Character 객체이면 직접 반환
            if not isinstance(target_val, str):
                return target_val
            # 문자열이면 이름으로 캐릭터 검색
            all_chars = list(self.combat_manager.allies) + list(self.combat_manager.enemies)
            for char in all_chars:
                if getattr(char, 'name', '') == target_val:
                    return char

        return None

    def _trigger_damage_popup(self, target, value, damage_type: str = "brv") -> None:
        """Raylib 데미지 팝업 생성 (독립 팝업 매니저 사용)

        Args:
            target: 대상 캐릭터
            value: 데미지/힐 수치
            damage_type: "hp", "brv", "heal", "critical", "break", "miss"
        """
        if target is None:
            return
        pm = self._standalone_popup
        if pm is None:
            return
        allies = list(self.combat_manager.allies)
        enemies = list(self.combat_manager.enemies)
        is_ally = target in allies
        idx = -1
        try:
            idx = allies.index(target) if is_ally else enemies.index(target)
        except ValueError:
            logger.debug(f"팝업 대상 '{getattr(target, 'name', '?')}' 을 아군/적군 목록에서 찾지 못함")
            return

        # 콘솔 셀 좌표 기반 팝업 위치 계산 (게이지 바 중앙)
        ctx = self._raylib_context
        tw = getattr(ctx, '_render_tw', 18) if ctx else 18
        th = getattr(ctx, '_render_th', 17) if ctx else 17
        y_base = 6 + idx * 6
        if is_ally:
            # 아군 HP 게이지: cell(12, y_base+1) → 게이지 중앙
            px = 12 * tw + (15 * tw) // 2
            py = (y_base + 1) * th
        else:
            # 적군 HP 게이지: cell(ex+7, y_base+2)
            ex = self.screen_width - 30
            px = (ex + 7) * tw + (15 * tw) // 2
            py = (y_base + 2) * th
        pm.add(value, px, py, damage_type)

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
                # ── MISS 팝업 ──
                miss_target = self._resolve_popup_target(result)
                self._trigger_damage_popup(miss_target, 0, "miss")
            else:
                msg = f"BRV 공격! {damage} 데미지"
                if is_crit:
                    msg += " [크리티컬!]"
                if is_break:
                    msg += " [BREAK!]"

                color = (255, 255, 100) if is_crit else (200, 200, 200)

                # ── 데미지 팝업 ──
                target = self._resolve_popup_target(result)
                popup_type = "critical" if is_crit else "brv"
                self._trigger_damage_popup(target, damage, popup_type)
                if is_break:
                    self._trigger_damage_popup(target, 0, "break")

            self.add_message(msg, color)

        elif action == "hp_attack":
            damage = result.get("hp_damage", 0)
            is_ko = result.get("is_ko", False)

            msg = f"HP 공격! {damage} HP 데미지"
            if is_ko:
                msg += " [격파!]"

            color = (255, 100, 100)
            self.add_message(msg, color)

            # ── 데미지 팝업 ──
            target = self._resolve_popup_target(result)
            is_hp_crit = result.get("is_critical", False)
            hp_popup_type = "critical" if is_hp_crit else "hp"
            self._trigger_damage_popup(target, damage, hp_popup_type)

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
                # SFX 재생
                if self.selected_skill and hasattr(self.selected_skill, 'sfx') and self.selected_skill.sfx:
                    try:
                        category, sound = self.selected_skill.sfx
                        play_sfx(category, sound)
                    except Exception as e:
                        logger.warning(f"스킬 SFX 재생 실패: {self.selected_skill.sfx} - {e}")

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
                elif effect_type == "heal_wound":
                    wound_healed = result.get("wound_healed", 0)
                    remaining_wound = result.get("remaining_wound", 0)
                    target_name = result.get("target", "대상")
                    if wound_healed > 0:
                        self.add_message(f"{item_name} 사용! {target_name} 상처 {wound_healed} 치료 (남은 상처: {remaining_wound})", (150, 200, 255))
                    else:
                        self.add_message(f"{item_name} 사용! {target_name} 치료할 상처가 없습니다.", (200, 200, 200))
                elif effect_type in ["aoe_fire", "aoe_ice", "poison_bomb", "thunder_grenade",
                                     "attack_fire", "attack_ice", "attack_lightning", "attack_poison", 
                                     "attack_explosive", "attack_aoe"]:
                    aoe_damage = result.get("aoe_damage", 0)
                    targets_hit = result.get("targets_hit", 0)
                    effect_names = {
                        "aoe_fire": "🔥 화염",
                        "aoe_ice": "❄ 냉기",
                        "poison_bomb": "☠ 독",
                        "thunder_grenade": "⚡ 번개",
                        "attack_fire": "🔥 화염",
                        "attack_ice": "❄ 냉기",
                        "attack_lightning": "⚡ 번개",
                        "attack_poison": "☠ 독",
                        "attack_explosive": "💥 폭발",
                        "attack_aoe": "💥 관통"
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

        # ── 연계스킬 발동 표시 ──
        bond_results = result.get("bond_skill_results", [])
        for br in bond_results:
            skill_name = br.get("skill_name", "연계스킬")
            source = br.get("source", "")
            self.add_message(f"★ 연계스킬 [{source}] {skill_name} 발동!", (255, 220, 100))
            for eff in br.get("effects", []):
                eff_type = eff.get("type", "")
                if eff_type == "damage":
                    self.add_message(
                        f"  → {eff['target']}에게 {eff['amount']} 데미지!",
                        (255, 150, 100)
                    )
                elif eff_type == "heal":
                    self.add_message(
                        f"  → {eff['target']} HP {eff['amount']} 회복!",
                        (100, 255, 150)
                    )
                    # ── 회복 팝업 ──
                    heal_name = eff.get('target', '')
                    for ch in list(self.combat_manager.allies) + list(self.combat_manager.enemies):
                        if getattr(ch, 'name', '') == heal_name:
                            self._trigger_damage_popup(ch, eff['amount'], "heal")
                            break
                elif eff_type == "mp_restore":
                    self.add_message(
                        f"  → {eff['target']} MP {eff['amount']} 회복!",
                        (100, 200, 255)
                    )
                    # ── MP 회복 팝업 ──
                    mp_name = eff.get('target', '')
                    for ch in list(self.combat_manager.allies) + list(self.combat_manager.enemies):
                        if getattr(ch, 'name', '') == mp_name:
                            self._trigger_damage_popup(ch, eff['amount'], "mp")
                            break
                elif eff_type == "shield":
                    shield_target = eff.get('target', '')
                    shield_amt = eff.get('amount', 0)
                    self.add_message(f"  → {shield_target} 보호막 +{shield_amt}!", (200, 200, 255))
                elif eff_type == "buff":
                    buff_target = eff.get('target', '')
                    buff_desc = eff.get('buff_desc', '버프')
                    self.add_message(f"  → {buff_target} {buff_desc}!", (200, 255, 200))
                elif eff_type == "redirect":
                    self.add_message(f"  → 피해 전환!", (255, 200, 200))

    def update(self, delta_time: float = 1.0):
        """업데이트 (매 프레임)"""
        if self.state == CombatUIState.CARD_SELECT:
            print(f"[카드UI] update() 시작 - state={self.state}")
        
        # 다단히트 타격 큐 처리 (타격감용 - 히트 간 간격)
        self.process_hit_queue()
        
        # 행동 후 대기 시간 처리
        if self.action_delay_frames > 0:
            self.action_delay_frames -= 1
            if self.action_delay_frames == 0:
                self.action_delay_owner_player_id = None
                # 대기 완료, WAITING_ATB로 전환 (EXECUTING 상태가 아니어도 전환)
                if self.state == CombatUIState.EXECUTING:
                    self.state = CombatUIState.WAITING_ATB
                elif self.state not in [CombatUIState.ACTION_MENU, CombatUIState.SKILL_MENU,
                                        CombatUIState.TARGET_SELECT, CombatUIState.ITEM_MENU,
                                        CombatUIState.CARD_SELECT, CombatUIState.CHOICE_SELECT,
                                        CombatUIState.POSSIBILITY_SELECT, CombatUIState.GIMMICK_VIEW,
                                        CombatUIState.CHAIN_ABILITY_SELECT]:
                    # 다른 상태에서도 WAITING_ATB로 전환 (기절 스킵 후 다음 턴 대기)
                    self.state = CombatUIState.WAITING_ATB

        # 페이즈 메시지 타이머 처리
        if hasattr(self.combat_manager, 'phase_transition_message') and self.combat_manager.phase_transition_message:
            if self.phase_message_timer == 0:
                # 새 메시지 감지, 타이머 시작
                self.phase_message_timer = self.phase_message_duration
            else:
                # 타이머 감소
                self.phase_message_timer -= 1
                if self.phase_message_timer <= 0:
                    # 시간 종료, 메시지 제거
                    self.combat_manager.phase_transition_message = None
                    self.phase_message_timer = 0

        # 부활 메시지 타이머 처리
        if hasattr(self.combat_manager, 'revival_message') and self.combat_manager.revival_message:
            if self.revival_message_timer == 0:
                # 새 메시지 감지, 타이머 시작
                self.revival_message_timer = self.revival_message_duration
            else:
                # 타이머 감소
                self.revival_message_timer -= 1
                if self.revival_message_timer <= 0:
                    # 시간 종료, 메시지 제거
                    self.combat_manager.revival_message = None
                    self.revival_message_timer = 0

        # 멀티플레이 클라이언트: COMBAT_END 수신 확인
        if getattr(self, '_mp_combat_end_received', False) and not self.battle_ended:
            self.battle_ended = True
            self.battle_result = self.combat_manager.state
            self.state = CombatUIState.BATTLE_END

        # 멀티플레이 호스트: 비차단 원격 대기 타임아웃 처리
        if self._pending_remote_actors:
            timed_out_keys = []
            for remote_key, (actor, timeout) in list(self._pending_remote_actors.items()):
                timeout -= 1
                if timeout <= 0:
                    timed_out_keys.append(remote_key)
                    if actor and getattr(actor, 'is_alive', True):
                        actor_name = getattr(actor, 'name', 'Unknown')
                        self.add_message(f"{actor_name} 행동 타임아웃 - AI 자동 행동", (255, 200, 100))
                        logger.warning(f"[호스트] 원격 플레이어 행동 타임아웃(비차단): {actor_name}")
                        self._execute_default_bot_action(actor)
                else:
                    self._pending_remote_actors[remote_key] = (actor, timeout)
            for key in timed_out_keys:
                self._pending_remote_actors.pop(key, None)

        # 행동 실행 중인지 확인 (ATB 완전 정지) - WAITING_REMOTE_ACTION 제거됨
        is_time_frozen = self.state in [CombatUIState.EXECUTING]

        # 플레이어가 메뉴에서 선택 중인지 확인 (불릿타임 적용)
        is_player_selecting = self.state in [
            CombatUIState.ACTION_MENU,
            CombatUIState.SKILL_MENU,
            CombatUIState.TARGET_SELECT,
            CombatUIState.ITEM_MENU,
            CombatUIState.CARD_SELECT,  # 카드 선택 중에도 불릿타임
            CombatUIState.CHOICE_SELECT,  # 선택형 스킬 선택 중에도 불릿타임
            CombatUIState.POSSIBILITY_SELECT,  # 가능성 선택 중에도 불릿타임
            CombatUIState.GIMMICK_VIEW,  # 기믹 상세 보기 중에도 불릿타임
            CombatUIState.CHAIN_ABILITY_SELECT,  # 체인어빌리티 선택 중에도 불릿타임
        ]

        # 멀티플레이 모드 확인 (combat_sync_manager 존재 여부로 판별 - get_game_mode_manager보다 안정적)
        is_multiplayer = self.combat_sync_manager is not None

        # 행동 실행 중: ATB 완전 정지 (update 호출 안 함)
        # 메뉴 선택 중: 불릿타임 (ATB 매우 느리게 증가)
        # 그 외(WAITING_ATB 등): ATB 정상 속도 증가
        if is_time_frozen:
            # 행동 실행 중에는 ATB 완전 정지 - combat_manager.update() 호출하지 않음
            pass
        elif is_multiplayer and not self.is_mp_host:
            # 멀티플레이 클라이언트: combat_manager.update() 건너뛰기
            # ATB, 캐스팅, 보스 타이머, 승리/패배 판정 모두 호스트에서 처리
            # 클라이언트는 200ms 하트비트로 전체 상태를 동기화 수신
            pass
        else:
            if is_player_selecting:
                self.combat_manager.state = CombatState.PLAYER_TURN
            else:
                if self.combat_manager.state == CombatState.PLAYER_TURN:
                    self.combat_manager.state = CombatState.IN_PROGRESS

            # 전투 매니저 업데이트
            self.combat_manager.update(delta_time)

        # 멀티플레이 호스트: 주기적 전투 상태 하트비트 (200ms 간격)
        if is_multiplayer and self.combat_sync_manager and self.combat_sync_manager.is_host:
            self.combat_sync_manager.send_heartbeat_sync()

        # ── 멀티플레이 클라이언트: 적 AI/상태이상 등은 호스트만 처리 ──
        # 단, 로컬 캐릭터의 ATB 100% 체크 → 행동 선택 UI 표시는 클라이언트에서 직접 수행
        # (하트비트로 동기화된 ATB 값 기반, ACTION_SELECTION_START 대기 불필요)
        if is_multiplayer and not self.is_mp_host:
            # 클라이언트: 로컬 캐릭터 중 ATB 100%인 캐릭터가 있으면 행동 메뉴 표시
            if self.state == CombatUIState.WAITING_ATB and self.current_actor is None:
                local_pid = self._get_local_player_id()
                if local_pid:
                    for ally in self.combat_manager.allies:
                        ally_pid = getattr(ally, 'player_id', None) or getattr(ally, 'owner_player_id', None)
                        if str(ally_pid) != str(local_pid):
                            continue
                        if not getattr(ally, 'is_alive', True):
                            continue
                        gauge = self.combat_manager.atb.get_gauge(ally)
                        if gauge and gauge.can_act:
                            self.current_actor = ally
                            self.action_menu = self._create_action_menu(ally)
                            self.state = CombatUIState.ACTION_MENU
                            self.add_message(f"{ally.name}의 턴!", (100, 255, 255))
                            play_sfx("ui", "turn_ready")
                            break
            return

        # ATB 업데이트 직후 즉시 턴 체크
        # 행동 가능한 캐릭터 확인
        ready = self.combat_manager.atb.get_action_order()
        
        # 행동 불가능하지만 ATB 100%인 캐릭터도 확인 (마비, 기절 등)
        all_combatants = self.combat_manager.allies + self.combat_manager.enemies
        blocked_ready = []
        for combatant in all_combatants:
            gauge = self.combat_manager.atb.get_gauge(combatant)
            if gauge and gauge.current >= gauge.threshold:
                # ATB 100% 이상이지만 행동 불가능한 경우
                if hasattr(combatant, 'status_manager') and not combatant.status_manager.can_act():
                    blocked_ready.append((combatant, gauge.current))
        
        # 행동 불가능한 캐릭터를 우선 처리 (ATB 높은 순)
        blocked_ready.sort(key=lambda x: x[1], reverse=True)
        processable_blocked_ready = [
            (combatant, gauge_value)
            for combatant, gauge_value in blocked_ready
            if not self._is_action_delay_blocking_actor(combatant, is_multiplayer)
        ]
        processable_ready = [
            combatant
            for combatant in ready
            if not self._is_action_delay_blocking_actor(combatant, is_multiplayer)
        ]

        if processable_blocked_ready:
            # 행동 불가능한 캐릭터 처리
            actor, _ = processable_blocked_ready[0]
            
            # 상태이상 지속시간 감소
            if hasattr(actor, 'status_manager'):
                from src.combat.status_effects import StatusType as StatusTypeEnum
                
                blocking_status = None
                for effect in actor.status_manager.status_effects:
                    if effect.status_type in [StatusTypeEnum.STUN, StatusTypeEnum.SLEEP, StatusTypeEnum.FREEZE,
                                             StatusTypeEnum.PETRIFY, StatusTypeEnum.PARALYZE, StatusTypeEnum.TIME_STOP]:
                        blocking_status = effect.name
                        break
                
                status_name = blocking_status or "행동 불가 상태"
                self.add_message(f"{actor.name}(은)는 {status_name}로 인해 행동할 수 없습니다...", (200, 100, 100))
                logger.info(f"{actor.name} 턴 자동 스킵: {status_name}")
                
                # 상태이상 지속시간 감소
                expired = actor.status_manager.update_duration()
                if expired:
                    logger.debug(f"{actor.name}: {len(expired)}개 상태 효과 만료 (행동 불가 중)")
            
            # ATB 소비 및 턴 스킵
            # 기절 상태일 때는 ATB를 완전히 소비하여 무한 루프 방지
            gauge = self.combat_manager.atb.get_gauge(actor)
            if gauge:
                # ATB를 threshold 아래로 강제로 내림 (무한 루프 방지)
                gauge.current = max(0, gauge.current - gauge.threshold)
                # threshold보다 높으면 threshold만큼만 남기고 나머지 소비
                if gauge.current >= gauge.threshold:
                    gauge.current = gauge.threshold - 1
            
            self.combat_manager.atb.consume_atb(actor)
            self.combat_manager._on_turn_end(actor)
            
            # 상태를 WAITING_ATB로 명확히 설정 (무한 대기 방지)
            # 단, 체인어빌리티 선택 중에는 덮어쓰지 않음
            if self.state != CombatUIState.CHAIN_ABILITY_SELECT:
                self.state = CombatUIState.WAITING_ATB
            
            # 행동 지연 타이머 설정 (0.5초 대기)
            self._set_action_delay(15, actor)  # 0.5초 (30 FPS 기준)
        elif processable_ready:
            # 행동자 처리 전 상태 정상화 (플레이어 입력 대기 상태는 유지)
            player_input_states = [
                CombatUIState.ACTION_MENU,
                CombatUIState.SKILL_MENU,
                CombatUIState.ITEM_MENU,
                CombatUIState.TARGET_SELECT,
                CombatUIState.CARD_SELECT,  # 마술사 카드 선택
                CombatUIState.CHOICE_SELECT,  # 선택형 스킬
                CombatUIState.POSSIBILITY_SELECT,  # 시간술사 가능성 선택
                CombatUIState.GIMMICK_VIEW,  # 기믹 상세 보기
                CombatUIState.CHAIN_ABILITY_SELECT  # 체인어빌리티 선택
            ]
            if self.state != CombatUIState.WAITING_ATB and self.state not in player_input_states:
                logger.debug(f"상태 강제 정상화: {self.state.value} -> WAITING_ATB")
                self.state = CombatUIState.WAITING_ATB

            # 다음 행동자 (멀티플레이에서는 원격 아군으로 인한 입력 블로킹 방지)
            actor = self._select_next_ready_actor(processable_ready, is_multiplayer)
            if actor is not None:
                # 캐릭터 타입 확인
                actor_player_id = getattr(actor, 'player_id', None)
                is_bot = actor_player_id and str(actor_player_id).startswith('bot_')
                
                if actor in self.combat_manager.enemies:
                    # 적 턴: 기존 EnemyAI 처리
                    logger.debug(f"적 {actor.name} 턴 처리")
                    # 플레이어 선택 중이면 현재 상태/액터 보존 (불릿타임 중 커서 초기화 방지)
                    prev_state = self.state
                    prev_actor = self.current_actor
                    self._execute_enemy_turn(actor)
                    # 적 행동 후 상태 복구
                    if self.state != CombatUIState.BATTLE_END:
                        if prev_state in player_input_states and prev_actor:
                            # BREAK 등으로 이전 액터의 ATB가 리셋되었는지 확인
                            prev_gauge = self.combat_manager.atb.get_gauge(prev_actor)
                            prev_alive = getattr(prev_actor, 'is_alive', True)
                            if prev_alive and prev_gauge and prev_gauge.can_act:
                                # 이전 액터가 여전히 행동 가능 → 선택 상태 유지
                                self.state = prev_state
                                self.current_actor = prev_actor
                            else:
                                # BREAK/사망 등으로 행동 불가 → WAITING_ATB로 전환
                                logger.info(f"적 행동 후 {prev_actor.name} ATB 부족/사망 → 선택 상태 해제")
                                self.state = CombatUIState.WAITING_ATB
                                self.current_actor = None
                        else:
                            self.state = CombatUIState.WAITING_ATB
                    logger.debug(f"적 {actor.name} 행동 완료 - 상태: {self.state.value}")

                elif is_bot:
                    # 봇 턴: AI가 자동으로 행동
                    logger.info(f"봇 {actor.name} 턴 시작 - player_id: {actor_player_id}")
                    self._process_bot_turn(actor)
                    # 봇 행동 후 상태 확인
                    logger.debug(f"봇 {actor.name} 행동 완료 - action_delay_frames: {self.action_delay_frames}")
                    
                elif actor in self.combat_manager.allies:
                    # 플레이어 턴: UI 표시
                    logger.debug(f"플레이어 {actor.name} 턴 처리 - 상태: {self.state.value}")
                    if self.state == CombatUIState.WAITING_ATB:
                        # 기절/마비/수면 등 행동 불가 상태 확인 (이중 체크)
                        if hasattr(actor, 'status_manager') and not actor.status_manager.can_act():
                            # 행동 불가 상태: 턴 자동 스킵
                            from src.combat.status_effects import StatusType as StatusTypeEnum
                            
                            blocking_status = None
                            for effect in actor.status_manager.status_effects:
                                if effect.status_type in [StatusTypeEnum.STUN, StatusTypeEnum.SLEEP, StatusTypeEnum.FREEZE,
                                                         StatusTypeEnum.PETRIFY, StatusTypeEnum.PARALYZE, StatusTypeEnum.TIME_STOP]:
                                    blocking_status = effect.name
                                    break
                            
                            status_name = blocking_status or "행동 불가 상태"
                            self.add_message(f"{actor.name}(은)는 {status_name}로 인해 행동할 수 없습니다...", (200, 100, 100))
                            logger.info(f"{actor.name} 턴 자동 스킵: {status_name}")
                            
                            # 상태이상 지속시간 감소
                            expired = actor.status_manager.update_duration()
                            if expired:
                                logger.debug(f"{actor.name}: {len(expired)}개 상태 효과 만료 (행동 불가 중)")
                            
                            # ATB 소비 및 턴 스킵
                            # 기절 상태일 때는 ATB를 완전히 소비하여 무한 루프 방지
                            gauge = self.combat_manager.atb.get_gauge(actor)
                            if gauge:
                                # ATB를 threshold 아래로 강제로 내림 (무한 루프 방지)
                                gauge.current = max(0, gauge.current - gauge.threshold)
                                # threshold보다 높으면 threshold만큼만 남기고 나머지 소비
                                if gauge.current >= gauge.threshold:
                                    gauge.current = gauge.threshold - 1
                            
                            self.combat_manager.atb.consume_atb(actor)
                            self.combat_manager._on_turn_end(actor)
                            
                            # 상태는 WAITING_ATB로 명확히 설정 (무한 대기 방지)
                            self.state = CombatUIState.WAITING_ATB
                            
                            # 행동 지연 타이머 설정 (0.5초 대기)
                            self._set_action_delay(15, actor)  # 0.5초 (30 FPS 기준)
                        else:
                            # 행동 가능: 멀티플레이 호스트/클라이언트 분기
                            from src.multiplayer.game_mode import get_game_mode_manager
                            gm = get_game_mode_manager()
                            is_mp = gm and gm.is_multiplayer() if gm else False

                            actor_pid = getattr(actor, 'player_id', None)
                            local_pid = self.local_player_id
                            if not local_pid and self.session:
                                local_pid = getattr(self.session, 'local_player_id', None)

                            is_remote = is_mp and actor_pid and local_pid and actor_pid != local_pid

                            if is_remote and self.is_mp_host and self.combat_sync_manager:
                                # 호스트: 원격 플레이어에게 ACTION_SELECTION_START 전송 (비차단)
                                actor_id = getattr(actor, 'id', None)
                                remote_key = f"{actor_pid}:{actor_id}"
                                if remote_key not in self._pending_remote_actors:
                                    self._pending_remote_actors[remote_key] = (actor, 10.0 * 60)  # 10초 타임아웃
                                    self.combat_sync_manager.send_action_selection_start_sync(actor, actor_pid)
                                    self.add_message(f"{actor.name} 행동 선택 중...", (200, 200, 100))
                                    logger.info(f"[호스트] ACTION_SELECTION_START 전송 (비차단): {actor.name} -> {actor_pid}")
                                    # 불릿타임 활성화
                                    if hasattr(self.combat_manager.atb, 'set_player_selecting') and actor_pid:
                                        self.combat_manager.atb.set_player_selecting(actor_pid, True)
                                # 차단하지 않음 - 계속 진행
                            else:
                                # 싱글플레이 또는 로컬 캐릭터: 정상적으로 UI 표시
                                self.current_actor = actor
                                self.action_menu = self._create_action_menu(actor)
                                self.state = CombatUIState.ACTION_MENU
                                self.add_message(f"{actor.name}의 턴!", (100, 255, 255))
                                play_sfx("ui", "turn_ready")
                                # 멀티플레이: 행동 선택 시작 (불릿타임)
                                if is_mp and hasattr(self.combat_manager.atb, 'set_player_selecting') and actor_pid:
                                    self.combat_manager.atb.set_player_selecting(actor_pid, True)

        # 전투 종료 체크
        if self.combat_manager.state in [CombatState.VICTORY, CombatState.DEFEAT, CombatState.FLED]:
            if not self.battle_ended:
                logger.debug(f"전투 종료: {self.combat_manager.state}")
                self.battle_ended = True
                self.battle_result = self.combat_manager.state
                self.state = CombatUIState.BATTLE_END
                # 멀티플레이 호스트: COMBAT_END 브로드캐스트
                if self.is_mp_host and self.combat_sync_manager and self.session and self.network_manager:
                    result_str = self.combat_manager.state.value if hasattr(self.combat_manager.state, 'value') else str(self.combat_manager.state)
                    self.combat_sync_manager.broadcast_combat_end_sync(result_str)
                    logger.info(f"[호스트] 전투 종료 브로드캐스트: {result_str}")

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
                CombatUIState.ITEM_MENU,
                CombatUIState.CARD_SELECT
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
                    local_player_id = self._get_local_player_id()
                    if local_player_id and local_player_id in self.combat_manager.atb.players_selecting_action:
                        self.combat_manager.atb.set_player_selecting(local_player_id, False)
                        logger.debug(f"불릿타임 해제: 플레이어 {local_player_id} (액터 없음, 상태: {self.state.value})")

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
        logger.info(f"=== 봇 턴 시작: {actor.name} (HP: {getattr(actor, 'hp', '?')}/{getattr(actor, 'max_hp', '?')}, BRV: {getattr(actor, 'brv', 0)}) ===")

        # 봇 인스턴스 찾기
        bot = self._get_bot_instance(actor)

        if not bot:
            logger.warning(f"봇 인스턴스를 찾을 수 없음: {actor.name}")
            # Fallback: 기본 BRV 공격
            self._execute_default_bot_action(actor)
            return
        
        try:
            # LLM 봇용 전투 상태 생성
            from src.multiplayer.llm_player_bot import (
                CombatState, CombatantState, SkillInfo, ItemInfo
            )

            # 캐릭터를 CombatantState로 변환
            def char_to_combatant_state(char: Any) -> CombatantState:
                """Character를 CombatantState로 변환"""
                return CombatantState(
                    name=char.name,
                    job=getattr(char, 'job_name', getattr(char, 'job', 'Unknown')),
                    hp=getattr(char, 'hp', 100),
                    max_hp=getattr(char, 'max_hp', 100),
                    mp=getattr(char, 'mp', 50),
                    max_mp=getattr(char, 'max_mp', 50),
                    brv=getattr(char, 'brv', 0),
                    max_brv=getattr(char, 'max_brv', 100),
                    is_alive=getattr(char, 'is_alive', True),
                    status_effects=[
                        status.name if hasattr(status, 'name') else str(status)
                        for status in getattr(char, 'status_manager', {}).status_effects
                        if hasattr(getattr(char, 'status_manager', {}), 'status_effects')
                    ] if hasattr(char, 'status_manager') else []
                )

            # 사용 가능한 스킬 정보
            available_skills = []
            if hasattr(actor, 'skills'):
                for skill in actor.skills:
                    try:
                        skill_info = SkillInfo(
                            id=getattr(skill, 'id', getattr(skill, 'skill_id', 'unknown')),
                            name=getattr(skill, 'name', 'Unknown'),
                            description=getattr(skill, 'description', ''),
                            mp_cost=getattr(skill, 'mp_cost', 0),
                            available=True  # 스킬 사용 가능 여부 (간단히 판단)
                        )
                        available_skills.append(skill_info)
                    except:
                        pass

            # CombatState 생성
            combat_state = CombatState(
                turn_count=getattr(self.combat_manager, 'turn_count', 1),
                current_actor=actor.name,
                allies=[char_to_combatant_state(ally) for ally in self.combat_manager.allies],
                enemies=[char_to_combatant_state(enemy) for enemy in self.combat_manager.enemies],
                available_skills=available_skills,
                available_items=[],  # 아이템은 나중에 구현
                can_flee=True,
                boss_name=getattr(self.combat_manager, 'boss_name', None)
            )

            logger.debug(f"LLM 봇 상태 생성: {actor.name}, 아군: {len(combat_state.allies)}, 적: {len(combat_state.enemies)}")

            # 봇 AI로 행동 결정 (decide_combat_action 직접 호출)
            logger.info(f"LLM 봇 {actor.name}에게 행동 결정 요청 중...")
            action = bot.decide_combat_action(combat_state)

            if not action:
                logger.error(f"LLM 봇 {actor.name}이 None을 반환함!")
                self._execute_default_bot_action(actor)
                return

            logger.info(f"LLM 봇 {actor.name} 행동 결정 완료: {action.action_type.value if hasattr(action, 'action_type') else action}")

            # 행동 실행
            self._execute_bot_action(actor, action)
            
        except Exception as e:
            logger.error(f"봇 턴 처리 실패: {e}", exc_info=True)
            # Fallback
            self._execute_default_bot_action(actor)
    
    def _execute_bot_action(self, actor: Any, action):
        """
        봇이 결정한 행동 실행

        Args:
            actor: 행동자
            action: 행동 정보 (딕셔너리 또는 BotAction 객체)
                   - 딕셔너리: {type, skill, target}
                   - BotAction: action_type, skill_id, target_name 속성
        """
        # 상태를 EXECUTING으로 설정 (플레이어 행동과 동일)
        self.state = CombatUIState.EXECUTING

        # BotAction 객체 또는 딕셔너리 지원
        if hasattr(action, 'action_type'):
            # BotAction 객체 (LLMPlayerBot에서 반환)
            from src.multiplayer.llm_player_bot import ActionType as LLMActionType
            action_type_enum = action.action_type
            # Enum의 value 추출 (예: ActionType.SKILL → "skill")
            if hasattr(action_type_enum, 'value'):
                action_type = action_type_enum.value
            else:
                action_type = str(action_type_enum)
            target_name = action.target_name
            skill_id = action.skill_id
        else:
            # 딕셔너리 형식 (EnemyAI에서 반환)
            action_type = action.get("type")
            target_name = action.get("target")
            skill_id = None
            # 호환성을 위해 skill 키도 확인 (EnemySkill 객체)
            skill = action.get("skill")

        logger.info(f"봇 {actor.name} 행동 실행: {action_type}, 타겟: {target_name}")

        # 타겟 객체 찾기
        target = target_name
        if isinstance(target_name, str):
            # 타겟 이름으로 캐릭터 찾기
            target = None
            for ally in self.combat_manager.allies:
                if getattr(ally, 'name', '') == target_name:
                    target = ally
                    break
            if not target:
                for enemy in self.combat_manager.enemies:
                    if getattr(enemy, 'name', '') == target_name:
                        target = enemy
                        break

        # 타겟이 없으면 기본값 설정
        if not target:
            if action_type in ["hp_attack", "HP_ATTACK", "brv_attack", "BRV_ATTACK", "attack"]:
                # 공격 행동: 가장 높은 HP를 가진 적을 기본 타겟
                alive_enemies = [e for e in self.combat_manager.enemies if getattr(e, 'is_alive', True)]
                if alive_enemies:
                    target = max(alive_enemies, key=lambda e: getattr(e, 'hp', 0))
                    logger.debug(f"기본 적 타겟 선택: {getattr(target, 'name', 'Unknown')}")
            elif action_type in ["skill", "SKILL"]:
                # 스킬 행동: 스킬 종류에 따라 판단 (일단 자신으로)
                target = actor
                logger.debug(f"기본 아군 타겟 선택: {getattr(target, 'name', 'Unknown')}")

        # ActionType 변환 및 실행
        if action_type == "skill" or action_type == "SKILL" or (hasattr(action, 'action_type') and action.action_type.value == "skill"):
            # skill_id에서 실제 skill 객체 찾기
            skill_obj = None
            if skill_id and hasattr(actor, 'skills'):
                for s in actor.skills:
                    if getattr(s, 'id', getattr(s, 'skill_id', '')) == skill_id:
                        skill_obj = s
                        break
                if not skill_obj:
                    logger.warning(f"스킬을 찾을 수 없음: {skill_id}")

            if skill_obj:
                logger.debug(f"스킬 실행: {actor.name} → {getattr(skill_obj, 'name', skill_id)}")
                result = self.combat_manager.execute_action(
                    actor=actor,
                    action_type=ActionType.SKILL,
                    target=target,
                    skill=skill_obj
                )
            elif 'skill' in locals() and skill:
                # EnemyAI 호환성
                logger.debug(f"스킬 실행 (EnemyAI 호환): {actor.name} → {getattr(skill, 'name', 'Unknown')}")
                result = self.combat_manager.execute_action(
                    actor=actor,
                    action_type=ActionType.SKILL,
                    target=target,
                    skill=skill
                )
            else:
                logger.warning(f"스킬 정보가 없음: {actor.name}, skill_id={skill_id}")
                result = {}
        elif action_type == "hp_attack" or action_type == "HP_ATTACK":
            result = self.combat_manager.execute_action(
                actor=actor,
                action_type=ActionType.HP_ATTACK,
                target=target
            )
        elif action_type == "brv_attack" or action_type == "attack" or action_type == "BRV_ATTACK":
            logger.debug(f"BRV 공격 실행: {actor.name} → {getattr(target, 'name', 'Unknown') if target else 'None'}")
            result = self.combat_manager.execute_action(
                actor=actor,
                action_type=ActionType.BRV_ATTACK,
                target=target
            )
            logger.debug(f"BRV 공격 결과: {result}")
        elif action_type == "defend" or action_type == "DEFEND":
            result = self.combat_manager.execute_action(
                actor=actor,
                action_type=ActionType.DEFEND
            )
        elif action_type == "item" or action_type == "ITEM":
            item_id = getattr(action, 'item_id', None)
            result = self.combat_manager.execute_action(
                actor=actor,
                action_type=ActionType.ITEM,
                item_id=item_id
            )
        else:
            logger.warning(f"알 수 없는 행동 타입: {action_type}, 행동: {action}")
            result = {}
        
        # 결과 메시지 표시
        self._show_action_result(result)

        # 행동 후 대기 시간
        self._set_action_delay(self.action_delay_max, actor)

        # 현재 액터 초기화 (_execute_current_action과 동일하게)
        self.current_actor = None

        logger.info(f"봇 {actor.name} 행동 완료: 상태={self.state.value}, 대기시간={self.action_delay_frames}프레임, current_actor={self.current_actor}")
    
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
        self._set_action_delay(self.action_delay_max, actor)

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
                            # 기절 상태일 때는 ATB를 완전히 소비하여 무한 루프 방지
                            gauge = self.combat_manager.atb.get_gauge(combatant)
                            if gauge:
                                # ATB를 threshold 아래로 강제로 내림 (무한 루프 방지)
                                gauge.current = max(0, gauge.current - gauge.threshold)
                                # threshold보다 높으면 threshold만큼만 남기고 나머지 소비
                                if gauge.current >= gauge.threshold:
                                    gauge.current = gauge.threshold - 1
                            
                            self.combat_manager.atb.consume_atb(combatant)
                            self.combat_manager._on_turn_end(combatant)
                            
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
                # 아군 턴 시작 SFX
                play_sfx("ui", "turn_ready")

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

                        # 호스트: 원격 플레이어에게 ACTION_SELECTION_START 전송 (비차단)
                        if self.is_mp_host and self.combat_sync_manager:
                            combatant_id = getattr(combatant, 'id', None)
                            remote_key = f"{actor_player_id}:{combatant_id}"
                            if remote_key not in self._pending_remote_actors:
                                self._pending_remote_actors[remote_key] = (combatant, 10.0 * 60)
                                self.add_message(f"{combatant.name} 행동 선택 중...", (200, 200, 100))
                                self.combat_sync_manager.send_action_selection_start_sync(combatant, actor_player_id)
                                logger.info(f"[호스트] ACTION_SELECTION_START 전송 (비차단): {combatant.name} -> {actor_player_id}")
                            # 차단하지 않음 - ATB 대기 상태 유지
                            self.state = CombatUIState.WAITING_ATB
                            self.current_actor = None
                        else:
                            # 클라이언트: ATB 대기 상태 유지 (ACTION_SELECTION_START 콜백으로 활성화)
                            self.state = CombatUIState.WAITING_ATB
                            self.current_actor = None

                        # 다른 플레이어의 행동 선택 시작 알림 (불릿타임 모드 진입)
                        if hasattr(self.combat_manager.atb, 'set_player_selecting') and actor_player_id:
                            self.combat_manager.atb.set_player_selecting(actor_player_id, True)
                            logger.info(f"불릿타임 활성화 요청: 플레이어 {actor_player_id} 행동 선택 시작")

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
                            logger.info(f"[BULLETTIME] 불릿타임 활성화 요청: 플레이어 {actor_player_id} 행동 선택 시작")
                        else:
                            # 플레이어 ID가 없으면 (AI나 싱글플레이) 로그만 출력
                            logger.warning(f"[WARNING] 플레이어 ID 없음 - combatant={combatant.name}, 불릿타임 비활성화")
                    elif not is_multiplayer_mode:
                        logger.debug("싱글플레이 모드 - 불릿타임 비활성화")
                    elif not hasattr(self.combat_manager.atb, 'set_player_selecting'):
                        logger.error(f"[ERROR] ATB 시스템에 set_player_selecting 메서드 없음: {type(self.combat_manager.atb).__name__}")
                
                return

    def _execute_enemy_turn(self, enemy: Any):
        """적 턴 실행 (AI 사용)"""
        try:
            # CombatManager의 execute_enemy_turn 사용 (새로운 AI 시스템)
            result = self.combat_manager.execute_enemy_turn(enemy)

            if result:
                self._show_action_result(result)
                # 멀티플레이 호스트: 적 행동 결과 브로드캐스트
                if self.is_mp_host and self.combat_sync_manager and self.session and self.network_manager:
                    if isinstance(result, dict):
                        self.combat_sync_manager.broadcast_action_result_sync(enemy, result)
            else:
                # AI 결정 실패 시 기본 메시지
                self.add_message(f"{enemy.name}의 행동 결정 실패", (200, 200, 200))

            # 전투 종료 확인
            if self.combat_manager.state in [CombatState.VICTORY, CombatState.DEFEAT]:
                self.battle_ended = True
                self.battle_result = self.combat_manager.state
                self.state = CombatUIState.BATTLE_END
                # 멀티플레이 호스트: COMBAT_END 브로드캐스트
                if self.is_mp_host and self.combat_sync_manager and self.session and self.network_manager:
                    result_str = self.combat_manager.state.value if hasattr(self.combat_manager.state, 'value') else str(self.combat_manager.state)
                    self.combat_sync_manager.broadcast_combat_end_sync(result_str)
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
                    # 멀티플레이 호스트: 적 행동 결과 브로드캐스트
                    if self.is_mp_host and self.combat_sync_manager and self.session and self.network_manager:
                        if isinstance(result, dict):
                            self.combat_sync_manager.broadcast_action_result_sync(enemy, result)

                # 전투 종료 확인
                if self.combat_manager.state in [CombatState.VICTORY, CombatState.DEFEAT]:
                    self.battle_ended = True
                    self.battle_result = self.combat_manager.state
                    self.state = CombatUIState.BATTLE_END
                    # 멀티플레이 호스트: COMBAT_END 브로드캐스트
                    if self.is_mp_host and self.combat_sync_manager and self.session and self.network_manager:
                        result_str = self.combat_manager.state.value if hasattr(self.combat_manager.state, 'value') else str(self.combat_manager.state)
                        self.combat_sync_manager.broadcast_combat_end_sync(result_str)

    def _on_combat_hit(self, hit_info: Dict[str, Any]):
        """히트 이벤트 핸들러 - 다단히트 타격감용"""
        # 트레이닝 파티 모드: 허수아비 피해량 집계
        if self.training_mode and getattr(self, "training_variant", None) == "party":
            tgt = hit_info.get("target")
            attacker = hit_info.get("attacker")
            hp_damage = hit_info.get("hp_damage", 0)
            if hp_damage and tgt and getattr(tgt, "enemy_id", "") == "training_dummy" and attacker:
                name = getattr(attacker, "name", "Unknown")
                self.training_damage_log[name] = self.training_damage_log.get(name, 0) + hp_damage

        self.hit_queue.append(hit_info)

    def _on_status_applied(self, status_data: Dict[str, Any]):
        """상태이상 적용 이벤트 핸들러 - 디버프/버프 파티클 이펙트"""
        if not self.effect_manager:
            return

        owner_obj = status_data.get("owner_object")
        if owner_obj is None:
            return

        def _cell_to_pixel(cx, cy):
            converter = getattr(self, '_cell_to_pixel_fn', None)
            if converter:
                return converter(cx, cy)
            return (cx * 10 + 5, cy * 13 + 6)

        # 대상이 적인지 아군인지 판별하여 위치 결정
        target_idx = None
        is_enemy = hasattr(owner_obj, 'enemy_id')
        if is_enemy:
            for idx, e in enumerate(self.combat_manager.enemies):
                if e is owner_obj:
                    target_idx = idx
                    break
            if target_idx is not None and target_idx in self._enemy_rects:
                rx, ry, rw, rh = self._enemy_rects[target_idx]
                px, py = _cell_to_pixel(rx + rw // 2, ry + rh // 2)
                trigger_status_effect(status_data, self.effect_manager, px, py)
        else:
            for idx, a in enumerate(self.combat_manager.allies):
                if a is owner_obj:
                    target_idx = idx
                    break
            if target_idx is not None and target_idx in self._ally_rects:
                rx, ry, rw, rh = self._ally_rects[target_idx]
                px, py = _cell_to_pixel(rx + rw // 2, ry + rh // 2)
                trigger_status_effect(status_data, self.effect_manager, px, py)

    def process_hit_queue(self):
        """히트 큐 처리 - 프레임마다 호출하여 다단히트 표시"""
        if not self.hit_queue:
            return
        
        # 딜레이 카운터 감소
        if self.hit_delay_counter > 0:
            self.hit_delay_counter -= 1
            return
        
        # 다음 히트 표시
        hit_info = self.hit_queue.pop(0)
        self._display_hit(hit_info)
        
        # 다음 히트를 위한 딜레이 설정
        if self.hit_queue:
            self.hit_delay_counter = self.hit_display_delay
    
    def _display_hit(self, hit_info: Dict[str, Any]):
        """개별 히트 표시 - 타격 효과 및 메시지"""
        attacker = hit_info.get('attacker')
        target = hit_info.get('target')
        damage_type = hit_info.get('damage_type', 'brv')
        brv_damage = hit_info.get('brv_damage', 0)
        hp_damage = hit_info.get('hp_damage', 0)
        is_critical = hit_info.get('is_critical', False)
        is_break = hit_info.get('is_break', False)
        sword_aura_hit = hit_info.get('sword_aura_hit')
        multi_hit_current = hit_info.get('multi_hit_current')
        
        attacker_name = getattr(attacker, 'name', '???') if attacker else '???'
        target_name = getattr(target, 'name', '???') if target else '???'
        
        # 히트별 SFX 정보 가져오기
        sfx_info = hit_info.get('sfx')  # (category, name, pitch) 또는 None
        
        # 히트 효과음 재생 (딜레이 적용됨)
        if sfx_info:
            # 커스텀 SFX (검기, 포탑 등)
            category, sfx_name = sfx_info[0], sfx_info[1]
            pitch = sfx_info[2] if len(sfx_info) > 2 else None
            play_sfx(category, sfx_name, pitch=pitch)
        elif brv_damage > 0 or hp_damage > 0:
            # 기본 SFX
            play_sfx("combat", "attack_physical")
        
        # 진동 효과 (게임패드)
        if hp_damage > 0:
            vibration_manager.vibrate(VibrationPattern.DAMAGE_MEDIUM)
        elif brv_damage > 0:
            vibration_manager.vibrate(VibrationPattern.DAMAGE_LIGHT)
        
        # 히트 메시지 생성
        if sword_aura_hit:
            # 검기 추가 공격
            if brv_damage > 0:
                msg = f"  ⚔ 검기 {sword_aura_hit}타! BRV {brv_damage}"
                color = (200, 180, 255)  # 연보라
                if is_break:
                    msg += " [BREAK!]"
                    color = (255, 100, 100)
                self.add_message(msg, color)
        elif multi_hit_current:
            # 일반 다단히트
            if damage_type == 'hp' and hp_damage > 0:
                msg = f"  💥 {multi_hit_current}타! HP {hp_damage}"
                color = (255, 150, 150)
                self.add_message(msg, color)
            elif brv_damage > 0:
                msg = f"  ✨ {multi_hit_current}타! BRV {brv_damage}"
                color = (150, 200, 255)
                if is_break:
                    msg += " [BREAK!]"
                self.add_message(msg, color)
        # 단일 히트는 메시지 표시하지 않음 (스킬 결과 메시지에서 이미 표시됨)

        # 스킬 이펙트 트리거 (원소별 파티클 + 셰이크 + 플래시)
        if self.effect_manager and target:
            # 셀→콘솔 픽셀 변환 함수 (context에 pixel converter가 있으면 사용)
            def _cell_to_pixel(cx, cy):
                converter = getattr(self, '_cell_to_pixel_fn', None)
                if converter:
                    return converter(cx, cy)
                # 폴백: 기본 타일 크기
                return (cx * 10 + 5, cy * 13 + 6)

            target_idx = None
            is_enemy_target = hasattr(target, 'enemy_id')
            if is_enemy_target:
                for idx, e in enumerate(self.combat_manager.enemies):
                    if e is target:
                        target_idx = idx
                        break
                if target_idx is not None and target_idx in self._enemy_rects:
                    rx, ry, rw, rh = self._enemy_rects[target_idx]
                    px, py = _cell_to_pixel(rx + rw // 2, ry + rh // 2)
                    trigger_skill_effect(hit_info, self.effect_manager, px, py)
            else:
                for idx, a in enumerate(self.combat_manager.allies):
                    if a is target:
                        target_idx = idx
                        break
                if target_idx is not None and target_idx in self._ally_rects:
                    rx, ry, rw, rh = self._ally_rects[target_idx]
                    px, py = _cell_to_pixel(rx + rw // 2, ry + rh // 2)
                    trigger_skill_effect(hit_info, self.effect_manager, px, py)

            # ── Cogmind 스타일 글리치 이펙트 (큰 피해/크리티컬/BREAK 시) ──
            try:
                hp_pct = hit_info.get("hp_percent_of_target", 0)
                is_critical = hit_info.get("is_critical", False)
                is_break = hit_info.get("is_break", False)
                is_ultimate = hit_info.get("is_ultimate", False)
                targets_hit = hit_info.get("targets_hit", 1)

                glitch_intensity = 0.0
                glitch_duration = 0.0

                if is_break:
                    glitch_intensity = max(glitch_intensity, 0.6)
                    glitch_duration = max(glitch_duration, 0.3)
                if is_critical and hp_pct > 15:
                    glitch_intensity = max(glitch_intensity, 0.6)
                    glitch_duration = max(glitch_duration, 0.25)
                elif hp_pct > 30:
                    glitch_intensity = max(glitch_intensity, 0.5)
                    glitch_duration = max(glitch_duration, 0.2)
                if is_ultimate:
                    glitch_intensity = min(1.0, glitch_intensity + 0.3)
                    glitch_duration = max(glitch_duration, 0.35)

                # AoE 다단히트: 이펙트 강도 감소 (과도한 화면 떨림 방지)
                if targets_hit > 1:
                    glitch_intensity *= 0.4
                    glitch_duration *= 0.5

                if glitch_intensity > 0 and hasattr(self.effect_manager, 'trigger_glitch'):
                    self.effect_manager.trigger_glitch(glitch_intensity, glitch_duration)
            except Exception:
                pass  # 글리치 이펙트 실패는 무시

    def add_message(self, text: str, color: Tuple[int, int, int] = (255, 255, 255)):
        """메시지 추가 (스크롤 형식 - 제한 없이 계속 저장, 다중 줄 지원)"""
        import re
        
        # 다중 줄 처리: \n으로 분할하여 각 줄을 별도 메시지로 추가
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue  # 빈 줄 스킵
            
            # 기믹 관련 수치 증감 메시지 필터링 (예: "이름의 필드: 값 -> 값" 형식)
            gimmick_pattern = r'.+의\s+\w+:\s*\d+\s*->\s*\d+'
            if re.match(gimmick_pattern, line):
                logger.debug(f"기믹 메시지 필터링됨: {line}")
                continue
            
            msg = CombatMessage(text=line, color=color)
            self.messages.append(msg)
            logger.debug(f"전투 메시지: {line}")

        # 새로운 메시지가 추가되면 스크롤을 최신으로 리셋
        self.log_scroll_offset = 0
    
    def add_messages(self, messages: List[Tuple[str, Tuple[int, int, int]]]):
        """
        여러 메시지를 한 번에 추가 (각 메시지별 색상 지정 가능)
        
        Args:
            messages: [(텍스트, 색상), ...] 형태의 리스트
        """
        for text, color in messages:
            self.add_message(text, color)

    def check_lily_combat_conditions(self):
        """RPG 모드 릴리 전투 중 대사 조건 체크"""
        if not self.lily_dialogue:
            return
        cm = self.combat_manager
        if not cm:
            return
        ch = self._rpg_chapter
        aff = self._rpg_affinity
        lily_color = (255, 200, 255)

        # 현재 턴 수 추적
        turn = getattr(cm, 'turn_count', 0)
        if turn != self._lily_last_turn_count:
            self._lily_turn_count = turn
            self._lily_last_turn_count = turn

        party = getattr(cm, 'party', []) or []
        alive = [m for m in party if getattr(m, 'is_alive', True)]
        dead = [m for m in party if not getattr(m, 'is_alive', True)]

        # 1) 아군 HP 위험 (<25%) - 한번만
        if not self._lily_low_hp_shown:
            for m in alive:
                hp = getattr(m, 'hp', 1)
                max_hp = getattr(m, 'max_hp', 1)
                if max_hp > 0 and hp / max_hp < 0.25:
                    line = self.lily_dialogue.get_low_hp_line(ch, aff)
                    if line:
                        self.add_message(f'릴리: "{line}"', lily_color)
                    self._lily_low_hp_shown = True
                    break

        # 2) 아군 전투불능
        for m in dead:
            name = getattr(m, 'name', '???')
            if name not in self._lily_ally_down_shown:
                line = self.lily_dialogue.get_ally_down_line(ch, aff)
                if line:
                    self.add_message(f'릴리: "{line}"', lily_color)
                self._lily_ally_down_shown.add(name)

        # 3) 주인공(파티 첫번째) HP 위험
        if not self._lily_ally_critical_shown and party:
            main_char = party[0]
            hp = getattr(main_char, 'hp', 1)
            max_hp = getattr(main_char, 'max_hp', 1)
            if getattr(main_char, 'is_alive', True) and max_hp > 0 and hp / max_hp < 0.25:
                line = self.lily_dialogue.get_ally_critical_line(ch, aff)
                if line:
                    self.add_message(f'릴리: "{line}"', lily_color)
                self._lily_ally_critical_shown = True

        # 4) 장기전 (15턴 이상)
        if not self._lily_long_battle_shown and self._lily_turn_count >= 15:
            line = self.lily_dialogue.get_long_battle_line(ch, aff)
            if line:
                self.add_message(f'릴리: "{line}"', lily_color)
            self._lily_long_battle_shown = True

        # 5) 파티 전멸 위기 (2명 이상 전투불능)
        if not self._lily_party_danger_shown and len(dead) >= 2:
            line = self.lily_dialogue.get_party_danger_line(ch, aff)
            if line:
                self.add_message(f'릴리: "{line}"', lily_color)
            self._lily_party_danger_shown = True

    def add_floating_dialogue(self, text: str, color: Tuple[int, int, int] = (255, 100, 100)):
        """
        화면의 랜덤한 빈 공간에 떠다니는 대사 추가 (림버스 컴퍼니 스타일)
        타이핑 효과로 나타나고 페이드 아웃으로 사라짐

        Args:
            text: 대사 내용
            color: 텍스트 색상 (기본: 붉은색)
        """
        # 화면 전체 영역에 랜덤 위치 선정 (UI 방해 효과 증가)
        min_x = 5  # 좌측 여백 최소화
        max_x = max(5, self.screen_width - len(text) - 5)
        min_y = 3  # 상단 UI도 가릴 수 있게 (글리치 효과)
        max_y = max(3, self.screen_height - 5)  # 하단 UI도 가릴 수 있게 (방해 효과)

        # 기존 대사와 겹치지 않는 위치 찾기 (최대 15번 시도)
        x, y = min_x, min_y
        for attempt in range(15):
            x = random.randint(min_x, max_x)
            y = random.randint(min_y, max_y)

            # 기존 대사와 너무 가까운지 체크 (약간 겹쳐도 OK - 글리치 효과)
            too_close = False
            for existing in self.floating_dialogues:
                # 거리 기준을 줄여서 더 밀집되게 배치 (20 -> 15)
                if abs(existing.x - x) < 15 and abs(existing.y - y) < 2:
                    too_close = True
                    break

            if not too_close:
                break

        # 대사 추가 (글리치/공포 효과 - 느린 타이핑, 오래 지속)
        dialogue = FloatingDialogue(
            text=text,
            x=x,
            y=y,
            color=color,
            total_frames=900,  # 15초 - 오래 남아서 화면 방해
            frames_remaining=900,
            typing_speed=0.1,  # 초당 6글자 (10프레임당 1글자) - 매우 느림
            current_char_index=0.0,
            fade_start_frames=300  # 마지막 5초부터 페이드 아웃 (매우 느리게)
        )
        self.floating_dialogues.append(dialogue)
        logger.debug(f"떠다니는 대사 추가 (글리치): {text} at ({x}, {y})")

    def render(self, console: tcod.console.Console):
        """렌더링"""
        # 가능성 선택 상태 디버그
        if self.state == CombatUIState.POSSIBILITY_SELECT:
            print(f"[가능성UI] render() 호출됨! state={self.state}, slots={len(self.possibility_slots) if self.possibility_slots else 0}")

        # 기믹 상세보기 상태에서는 다른 UI를 그리지 않고 전용 화면만 표시
        if self.state == CombatUIState.GIMMICK_VIEW:
            try:
                console.clear(ch=ord(" "), fg=(0, 0, 0), bg=(0, 0, 0))
            except Exception:
                pass
            self._render_gimmick_view(console)
            return
        
        # 카드 선택 상태면 로그 (render 진입 확인)
        if self.state == CombatUIState.CARD_SELECT:
            print(f"[카드UI] render() 호출됨! state={self.state}, card_hand={len(self.card_hand) if self.card_hand else 0}")
        
        # 필드 효과에 따른 배경 색상 변경
        dungeon = None
        combat_position = None
        if hasattr(self.combat_manager, 'dungeon') and self.combat_manager.dungeon:
            dungeon = self.combat_manager.dungeon
        if hasattr(self.combat_manager, 'combat_position') and self.combat_manager.combat_position:
            combat_position = self.combat_manager.combat_position
        
        render_space_background(
            console, 
            self.screen_width, 
            self.screen_height, 
            context="combat",
            dungeon=dungeon,
            combat_position=combat_position
        )

        # 제목
        console.print(
            self.screen_width // 2 - 5,
            1,
            " 전투 ",
            fg=(255, 255, 100)
        )

        # 보스 타이머 표시
        from src.combat.boss_timer_system import get_boss_timer_system
        boss_timer = get_boss_timer_system()
        if boss_timer.is_active:
            remaining = boss_timer.get_remaining_time()
            time_str = boss_timer.format_time(remaining)

            # 색상: 1분 이하면 빨간색, 2분 이하면 노란색, 그 외 흰색
            if remaining <= 60:
                timer_color = (255, 50, 50)  # 빨강
            elif remaining <= 120:
                timer_color = (255, 255, 0)  # 노랑
            else:
                timer_color = (255, 255, 255)  # 흰색

            timer_text = f"⏱ {time_str}"
            timer_x = self.screen_width // 2 - len(timer_text) // 2
            console.print(timer_x, 2, timer_text, fg=timer_color)

            # 타이머 경고 메시지 표시
            if hasattr(self.combat_manager, 'timer_warning_message') and self.combat_manager.timer_warning_message:
                warning_msg = self.combat_manager.timer_warning_message
                warning_x = self.screen_width // 2 - len(warning_msg) // 2
                console.print(warning_x, 3, warning_msg, fg=(255, 100, 100))

        # 부활 메시지 표시 (카인 불멸 능력)
        if hasattr(self.combat_manager, 'revival_message') and self.combat_manager.revival_message:
            revival_lines = self.combat_manager.revival_message.split('\n')
            start_y = self.screen_height // 2 - len(revival_lines) // 2
            for i, line in enumerate(revival_lines):
                if line.strip():
                    line_x = self.screen_width // 2 - len(line) // 2
                    console.print(line_x, start_y + i, line, fg=(255, 215, 0))  # 황금색

        # 페이즈 전환 메시지 표시 (보스 페이즈 변경)
        if hasattr(self.combat_manager, 'phase_transition_message') and self.combat_manager.phase_transition_message:
            phase_lines = self.combat_manager.phase_transition_message.split('\n')
            start_y = self.screen_height // 2 - len(phase_lines) // 2
            for i, line in enumerate(phase_lines):
                if line.strip():
                    line_x = self.screen_width // 2 - len(line) // 2
                    console.print(line_x, start_y + i, line, fg=(255, 50, 50))  # 빨간색

        # 아군 상태
        self._render_allies(console)

        # 적군 상태
        self._render_enemies(console)

        # ── 통합 픽셀 오버레이 (게이지 + 팝업 + 툴팁 재렌더) ──
        # 가능성 선택/기믹 상세보기 중에는 게이지 오버레이 숨김 (UI 가림 방지)
        _skip_gauge_overlay = self.state in (
            CombatUIState.POSSIBILITY_SELECT,
        )
        self._update_hover_character()
        _console_ref = console  # 클로저 캡처 (툴팁 재렌더용)

        if self._raylib_context:
            _skip = _skip_gauge_overlay  # 클로저 캡처
            def _combined_overlay(dt):
                # 1) 게이지 (가능성 선택 등 전체화면 UI 시 숨김)
                if not _skip:
                    self._draw_pixel_gauge_overlay(dt)
                # 2) 팝업 (게이지 위에)
                pm = getattr(self, '_standalone_popup', None)
                if pm:
                    try:
                        pm.update(dt)
                        pm.draw()
                    except Exception:
                        pass
                # 3) 툴팁 재렌더 (게이지 위에 다시 그림)
                if not _skip and self._hover_character and self._hover_cell:
                    self._redraw_tooltip_area(_console_ref)

            self._raylib_context.add_pixel_overlay(_combined_overlay)

        # 트레이닝 모드 통계 표시
        if self.training_mode and self.training_dummy:
            self._render_training_stats(console)

        # 메시지 로그
        self._render_messages(console)

        # 팀워크 게이지 (행동 메뉴 위에 표시)
        self._render_teamwork_gauge(console)

        # 상태별 UI
        # CARD_SELECT 디버깅
        if self.state == CombatUIState.CARD_SELECT:
            logger.info(f"[카드선택] render() 진입, state={self.state}, card_hand={len(self.card_hand) if hasattr(self, 'card_hand') and self.card_hand else 0}장")
        
        if self.state == CombatUIState.ACTION_MENU and self.action_menu:
            self.action_menu.render(console)

        elif self.state == CombatUIState.SKILL_MENU and self.skill_menu:
            self.skill_menu.render(console)

        elif self.state == CombatUIState.CHOICE_SELECT and self.choice_menu:
            self.choice_menu.render(console)

        elif self.state == CombatUIState.TARGET_SELECT:
            self._render_target_select(console)

        elif self.state == CombatUIState.ITEM_MENU:
            self._render_item_menu(console)

        elif self.state == CombatUIState.CARD_SELECT:
            logger.info(f"[카드선택] render에서 CARD_SELECT 분기 진입!")
            try:
                self._render_card_select(console)
            except Exception as e:
                logger.error(f"[카드선택] 렌더링 오류: {e}", exc_info=True)

        elif self.state == CombatUIState.POSSIBILITY_SELECT:
            logger.info(f"[가능성 선택] render() POSSIBILITY_SELECT 분기 진입, slots={len(self.possibility_slots) if self.possibility_slots else 0}개")
            self._render_possibility_select(console)

        elif self.state == CombatUIState.CHAIN_ABILITY_SELECT:
            self._render_chain_ability_select(console)

        elif self.state == CombatUIState.WAITING_REMOTE_ACTION:
            # 레거시 상태 - 비차단 방식 전환 후 더 이상 진입하지 않음
            # 혹시 진입 시 일반 전투 화면 표시 (전체 차단 없음)
            pass

        elif self.state == CombatUIState.BATTLE_END:
            self._render_battle_end(console)

        # 떠다니는 대사 렌더링 (최상위 레이어 - 림버스 컴퍼니 스타일)
        self._render_floating_dialogues(console)

        # 기믹 상세 보기 (최상위 레이어 - 모든 UI 위에 표시)
        if self.state == CombatUIState.GIMMICK_VIEW:
            self._render_gimmick_view(console)

        # 멀티플레이: 비차단 원격 대기 오버레이 (상단 소형 표시)
        if self._pending_remote_actors:
            self._render_pending_remote_overlay(console)

        # 마우스 호버 툴팁 (최상위 레이어)
        self._update_hover_character()
        if self._hover_character and self._hover_cell:
            render_tooltip(
                console,
                self._hover_character,
                self._hover_cell[0],
                self._hover_cell[1],
                self.screen_width,
                self.screen_height,
                combat_manager=self.combat_manager,
            )

    def update_mouse_cell(self, cell_x: int, cell_y: int) -> None:
        """마우스 셀 좌표 업데이트 (외부에서 호출)"""
        self._mouse_cell = (cell_x, cell_y)

    def _update_hover_character(self) -> None:
        """마우스 위치에 따라 호버 캐릭터 갱신"""
        if self._mouse_cell is None:
            self._hover_character = None
            self._hover_cell = None
            return

        mx, my = self._mouse_cell

        # 아군 영역 체크
        for i, rect in self._ally_rects.items():
            rx, ry, rw, rh = rect
            if rx <= mx < rx + rw and ry <= my < ry + rh:
                if i < len(self.combat_manager.allies):
                    self._hover_character = self.combat_manager.allies[i]
                    self._hover_cell = (rx + rw, ry)
                    return

        # 적군 영역 체크
        for i, rect in self._enemy_rects.items():
            rx, ry, rw, rh = rect
            if rx <= mx < rx + rw and ry <= my < ry + rh:
                if i < len(self.combat_manager.enemies):
                    self._hover_character = self.combat_manager.enemies[i]
                    self._hover_cell = (rx, ry)
                    return

        self._hover_character = None
        self._hover_cell = None

    def _render_allies(self, console: tcod.console.Console):
        """아군 상태 렌더링 (상세)"""
        console.print(5, 4, "[아군 파티]", fg=(100, 255, 100))
        self._ally_rects.clear()

        for i, ally in enumerate(self.combat_manager.allies):
            y = 6 + i * 6  # 더 큰 간격

            # 아군 영역 저장 (툴팁용: x, y, width, height 셀 좌표)
            self._ally_rects[i] = (3, y, 46, 5)

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

                # 현재 커서가 가리키는 실제 타겟 객체
                selected_target = (self.current_target_list[self.target_cursor]
                                   if self.current_target_list and 0 <= self.target_cursor < len(self.current_target_list)
                                   else None)

                # 광역 스킬 확인 또는 ALL_ALLIES 모드
                is_aoe = self.selected_skill and getattr(self.selected_skill, 'is_aoe', False)
                is_all_allies = getattr(self, 'all_allies_mode', False)

                if (is_aoe or is_all_allies) and is_targeted:
                    # 광역 스킬 또는 전체 아군 타겟 - 모든 타겟에 화살표
                    turn_indicator = "◆ "
                    indicator_color = (100, 255, 255)
                elif is_targeted and ally is selected_target:
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

            # 이름 표시 (표식/낙인 시 글리치 효과 - 살아있는 경우만)
            display_name = ally.name
            is_alive = getattr(ally, 'is_alive', True)
            if is_alive and (hasattr(ally, '_sephiroth_mark') or hasattr(ally, '_cain_mark')):
                # 보스 기믹 표식 - 글리치 이름 + 빨간색
                from src.combat.boss_gimmicks import BossGimmickSystem
                display_name = BossGimmickSystem.glitch_name(ally.name, 
                    intensity=3 if hasattr(ally, '_sephiroth_mark') else 2, 
                    use_color=False)
                name_color = (255, 50, 50)  # 빨간색
            
            # 무당 과부하 상태를 이름 오른쪽에 표시
            overload_state = ""
            if getattr(ally, "gimmick_type", None) == "mp_overload_system":
                state = getattr(ally, "last_mp_state", None)
                gauge = getattr(ally, "overload_gauge", 0)
                max_gauge = getattr(ally, "max_overload_gauge", 5)
                if state:
                    state_kor = {"stable": "안정", "danger": "위험", "depleted": "고갈"}.get(state, state)
                    overload_state = f" 과부하 {state_kor} {gauge}/{max_gauge}"
            # 해커 RAM 상태 표시
            ram_state = ""
            if getattr(ally, "gimmick_type", None) == "intrusion_system":
                ram = getattr(ally, "ram", 0)
                max_ram = getattr(ally, "max_ram", 0)
                if max_ram:
                    ram_state = f" RAM: {ram}GB/{max_ram}GB"
            # 성기사 서약 상태 간단 표기
            oath_state = ""
            if getattr(ally, "gimmick_type", None) == "oath_system":
                current_oath = getattr(ally, "current_oath", None)
                faith = getattr(ally, "faith", 0)
                if current_oath:
                    oath_name = getattr(ally, "oaths", {}).get(current_oath, {}).get("name", current_oath)
                    oath_state = f" {oath_name}, 신앙: {faith}"
            name_str = f"{i+1}. {display_name}{overload_state}{ram_state}{oath_state}"
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

            # HP 게이지 (애니메이션 + 상처 표시 + 숫자는 게이지 안에)
            console.print(8, y + 1, "HP:", fg=(200, 200, 200))
            wound_damage = getattr(ally, 'wound', 0)  # Character 클래스의 wound 속성
            # 보호막 수치 (current_shield: 광전사, shield_amount: 기타)
            total_shield = getattr(ally, 'current_shield', 0) + getattr(ally, 'shield_amount', 0)
            # status_manager에서 SHIELD 타입의 상태 효과도 합산 (Refraction Shield 등)
            if hasattr(ally, 'status_manager'):
                for eff in ally.status_manager.status_effects:
                    if hasattr(eff, 'status_type') and eff.status_type == StatusType.SHIELD:
                        shield_hp = eff.metadata.get('shield_hp', 0) if eff.metadata else 0
                        total_shield += shield_hp
            entity_id = f"ally_{i}_{getattr(ally, 'name', i)}"
            gauge_renderer.render_animated_hp_bar(
                console, 12, y + 1, 15,
                ally.current_hp, ally.max_hp, entity_id,
                wound_damage=wound_damage, show_numbers=True, shield_amount=total_shield
            )

            # MP 게이지 (애니메이션 + 숫자는 게이지 안에)
            console.print(29, y + 2, "MP:", fg=(200, 200, 200))
            gauge_renderer.render_animated_mp_bar(
                console, 33, y + 2, 15,
                ally.current_mp, ally.max_mp, entity_id,
                show_numbers=True,
                reserved_mp=getattr(ally, "reserved_max_mp", 0)
            )

            # BRV 게이지 (애니메이션 + 숫자는 게이지 안에)
            max_brv = getattr(ally, 'max_brv', 999)
            is_broken = self.combat_manager.brave.is_broken(ally) if hasattr(self.combat_manager, 'brave') else False
            console.print(7, y + 2, "BRV:", fg=(200, 200, 200))
            gauge_renderer.render_animated_brv_bar(
                console, 12, y + 2, 15,
                ally.current_brv, max_brv, entity_id,
                is_broken=is_broken, show_numbers=True
            )

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
            status_list = list(status_effects) if isinstance(status_effects, list) else []
            # 침투 게이지 표시
            intrusion_val = getattr(ally, "intrusion_gauge", 0)
            if intrusion_val:
                status_list.append(StatusEffect(name=f"침투 {intrusion_val}%", status_type="intrusion", duration=intrusion_val))

            if status_list or active_buffs:
                status_lines = gauge_renderer.render_status_icons(status_list, buffs=active_buffs)
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
            ally_id = getattr(ally, 'id', None) or getattr(ally, 'name', f'ally_{i}')
            # 현재 행동 중인 아군인지 확인
            is_current = (self.current_actor is not None and 
                         self.current_actor is ally and
                         self.state in [CombatUIState.ACTION_MENU, CombatUIState.SKILL_MENU, 
                                       CombatUIState.ITEM_MENU, CombatUIState.TARGET_SELECT])
            gauge_renderer.render_atb_with_cast(
                console, 33, y + 1, 15,
                atb_current=atb_value,
                atb_threshold=1000,
                atb_maximum=2000,
                cast_progress=cast_progress,
                is_casting=is_casting,
                entity_id=f"ally_{ally_id}",
                is_current_actor=is_current
            )

            # 상처 표시
            wound_damage = getattr(ally, 'wound_damage', 0)
            if wound_damage > 0:
                gauge_renderer.render_wound_indicator(console, 33, y + 2, wound_damage)

            # 캐스팅 중이면 스킬 이름 표시 (BREAK는 게이지 안에만 표시)
            if cast_info:
                skill_name = getattr(cast_info.skill, 'name', 'Unknown')
                console.print(8, y + 3, f"⏳ 시전: {skill_name}", fg=(200, 100, 255))

    def _render_enemies(self, console: tcod.console.Console):
        """적군 상태 렌더링 (상세)"""
        console.print(self.screen_width - 30, 4, "[적군]", fg=(255, 100, 100))
        self._enemy_rects.clear()

        for i, enemy in enumerate(self.combat_manager.enemies):
            y = 6 + i * 6
            x = self.screen_width - 30

            # 적군 영역 저장 (툴팁용)
            self._enemy_rects[i] = (x, y, 28, 5)

            # 이름 색상: 보스는 빨간색, 일반 적은 흰색
            is_boss = hasattr(enemy, 'enemy_id') and enemy.enemy_id.startswith("boss_") if hasattr(enemy, 'enemy_id') else False
            is_floor_boss = hasattr(enemy, 'is_floor_boss') and enemy.is_floor_boss
            if not enemy.is_alive:
                name_color = (100, 100, 100)
            elif is_boss or is_floor_boss:
                name_color = (255, 0, 0)  # 보스 또는 5층 층 보스: 선명한 빨간색
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

                # 현재 커서가 가리키는 실제 타겟 객체
                selected_target = (self.current_target_list[self.target_cursor]
                                   if self.current_target_list and 0 <= self.target_cursor < len(self.current_target_list)
                                   else None)

                # 광역 스킬 확인
                is_aoe = self.selected_skill and getattr(self.selected_skill, 'is_aoe', False)

                if is_aoe and is_targeted and enemy.is_alive:
                    # 광역 스킬 - 모든 살아있는 타겟에 화살표
                    cursor = "◆ "
                    cursor_color = (255, 100, 255)
                elif is_targeted and enemy is selected_target:
                    # 단일 타겟 - 선택된 대상에만 화살표
                    cursor = "▶ "
                    cursor_color = (255, 255, 100)
                else:
                    cursor = "  "
                    cursor_color = name_color
            else:
                cursor = "  "
                cursor_color = name_color

            # === 보스 전용 기믹 상태 표시 (이름 위에) ===
            enemy_id = getattr(enemy, 'enemy_id', None)
            
            if enemy_id == 'sephiroth' and hasattr(self.combat_manager, 'boss_gimmick_system'):
                gimmick = self.combat_manager.boss_gimmick_system
                stack = gimmick.sephiroth_counter_stack
                marked = gimmick.sephiroth_marked_target
                marked_name = marked.name[:4] if marked else "-"
                
                if gimmick.sephiroth_rage_mode:
                    gimmick_text = f"🔥광기모드 | 표식:{marked_name}"
                    gimmick_color = (255, 50, 50)
                else:
                    gimmick_text = f"광기:{stack}/3 | 표식:{marked_name}"
                    gimmick_color = (255, 150, 100)
                console.print(x + 2, y - 1, gimmick_text, fg=gimmick_color)
            
            elif enemy_id == 'abel_cain' and hasattr(self.combat_manager, 'boss_gimmick_system'):
                gimmick = self.combat_manager.boss_gimmick_system
                cd = gimmick.cain_judgment_cooldown
                marked = gimmick.cain_marked_target
                marked_name = marked.name[:4] if marked else "-"
                
                if cd > 0:
                    gimmick_text = f"심판:{cd}턴 | 낙인:{marked_name}"
                    gimmick_color = (150, 150, 200)
                else:
                    gimmick_text = f"심판:준비! | 낙인:{marked_name}"
                    gimmick_color = (255, 200, 100)
                console.print(x + 2, y - 1, gimmick_text, fg=gimmick_color)

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
            status_list = list(status_effects) if isinstance(status_effects, list) else []
            # 독 중첩 표시 (적에게 쌓인 독)
            venom_val = getattr(enemy, "venom_stacks", 0)
            if venom_val:
                max_venom = getattr(enemy, "max_venom", 5)
                status_list.append(StatusEffect(name=f"독 {venom_val}/{max_venom}", status_type="venom", duration=venom_val))
            intrusion_val = getattr(enemy, "intrusion_gauge", 0)
            if intrusion_val:
                status_list.append(StatusEffect(name=f"침투 {intrusion_val}%", status_type="intrusion", duration=intrusion_val))
            
            if status_list or active_buffs:
                status_lines = gauge_renderer.render_status_icons(status_list, buffs=active_buffs)
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
            
            # HP 게이지 (애니메이션, 적군은 상처 시스템 없음)
            console.print(x + 3, y + 2, "HP:", fg=(200, 200, 200))
            # 적군도 보호막이 있을 수 있음
            enemy_shield = getattr(enemy, 'current_shield', 0) + getattr(enemy, 'shield_amount', 0)
            # status_manager에서 SHIELD 타입의 상태 효과도 합산
            if hasattr(enemy, 'status_manager'):
                for eff in enemy.status_manager.status_effects:
                    if hasattr(eff, 'status_type') and eff.status_type == StatusType.SHIELD:
                        shield_hp = eff.metadata.get('shield_hp', 0) if eff.metadata else 0
                        enemy_shield += shield_hp
            enemy_id = f"enemy_{i}_{getattr(enemy, 'name', i)}"
            gauge_renderer.render_animated_hp_bar(
                console, x + 7, y + 2, 15,
                enemy.current_hp, enemy.max_hp, enemy_id,
                wound_damage=0, show_numbers=True, shield_amount=enemy_shield
            )

            # BRV 게이지 (애니메이션) - 플레이어와 동일 (15칸)
            max_brv = getattr(enemy, 'max_brv', 9999)
            is_broken = self.combat_manager.brave.is_broken(enemy) if hasattr(self.combat_manager, 'brave') else False
            
            # SCATTER 상태 확인 (Breaker Gimmick)
            is_scattered = False
            if hasattr(enemy, 'status_manager'):
                if enemy.status_manager.has_status(StatusType.SCATTER):
                    is_scattered = True

            # SCATTER 시 파란색 게이지 및 텍스트 변경
            custom_brv_color = (0, 100, 255) if is_scattered else None
            break_text = "SCATTER!" if is_scattered else "BREAK!"

            console.print(x + 2, y + 3, "BRV:", fg=(200, 200, 200))
            gauge_renderer.render_animated_brv_bar(
                console, x + 7, y + 3, 15,
                enemy.current_brv, max_brv, enemy_id,
                is_broken=is_broken, show_numbers=True,
                custom_color=custom_brv_color,
                break_text=break_text
            )

            # 캐스팅 표시 (BREAK는 게이지 안에만 표시)
            cast_info = casting_system.get_cast_info(enemy)
            if cast_info:
                skill_name = getattr(cast_info.skill, 'name', 'Unknown')
                gauge_renderer.render_casting_bar(
                    console, x + 3, y + 5, 15,
                    cast_info.progress, skill_name=f"시전:{skill_name[:8]}"
                )

    # ------------------------------------------------------------------
    # 픽셀 단위 정밀 게이지 오버레이
    # ------------------------------------------------------------------

    _pixel_gauge_debug_logged: bool = False

    def _lerp_gauge(self, key: str, actual: float, dt: float, speed: float = 12.0) -> float:
        """게이지 카운팅 애니메이션용 보간"""
        prev = self._gauge_anim_values.get(key, actual)
        if abs(prev - actual) < 0.5:
            self._gauge_anim_values[key] = actual
            return actual
        lerped = prev + (actual - prev) * min(1.0, dt * speed)
        self._gauge_anim_values[key] = lerped
        return lerped

    def _update_trail(self, key: str, actual_ratio: float, dt: float, decay: float = 0.6) -> float:
        """데미지/게인 트레일 비율 계산

        감소 시: 잔상이 이전 위치에서 천천히 줄어듦 (양수 반환)
        증가 시: 이전 위치에서 현재 위치까지 밝은 트레일 (음수 반환으로 구분)
        """
        prev = self._gauge_trail_ratios.get(key, actual_ratio)
        if abs(actual_ratio - prev) < 0.001:
            self._gauge_trail_ratios[key] = actual_ratio
            return 0.0
        if actual_ratio < prev:
            # 감소 — 이전 위치에서 서서히 줄어듦
            new_trail = max(actual_ratio, prev - dt * decay)
            self._gauge_trail_ratios[key] = new_trail
            return new_trail  # 양수 = 감소 트레일
        else:
            # 증가 — 이전 위치에서 서서히 늘어남
            new_trail = min(actual_ratio, prev + dt * decay)
            self._gauge_trail_ratios[key] = new_trail
            return -new_trail  # 음수 = 증가 트레일 (절대값이 이전 위치)

    def _get_display_ratio(self, key: str, actual_ratio: float, dt: float, speed: float = 1.2) -> float:
        """증가 시 서서히 채워지는 표시 비율

        감소: 즉시 반영 (잔상이 위에 남으므로)
        증가: 서서히 올라감 (밝은 목표 마커가 먼저 보임)
        """
        prev = self._gauge_display_ratios.get(key, actual_ratio)
        if actual_ratio <= prev:
            # 감소 — 즉시 반영
            self._gauge_display_ratios[key] = actual_ratio
            return actual_ratio
        # 증가 — 서서히 올라감
        new_disp = min(actual_ratio, prev + dt * speed)
        self._gauge_display_ratios[key] = new_disp
        return new_disp

    def _auto_popup(self, key: str, actual: float, px: int, py: int) -> None:
        """게이지 값 변동 감지 → 자동 팝업 생성"""
        pm = self._standalone_popup
        if pm is None:
            return
        prev = self._gauge_prev_values.get(key)
        self._gauge_prev_values[key] = actual
        if prev is None:
            return  # 첫 프레임
        delta = actual - prev
        if abs(delta) < 1:
            return  # 무시할 만한 변동
        if delta < 0:
            # 감소 = 데미지
            dtype = "hp" if "_hp" in key else "brv"
            pm.add(int(abs(delta)), px, py, dtype)
        else:
            # 증가 = 회복
            dtype = "heal" if "_hp" in key else ("mp" if "_mp" in key else "brv")
            pm.add(int(delta), px, py, dtype)

    def _draw_pixel_gauge_overlay(self, dt: float) -> None:
        """
        PUA 타일 게이지를 덮어쓰는 픽셀 정밀 게이지 오버레이

        콘솔 렌더링 후 실행되어 블록 형태의 PUA 타일 게이지 위에
        부드러운 직사각형 기반 게이지를 그립니다.
        """
        try:
            import pyray as rl
        except ImportError:
            return

        ctx = self._raylib_context
        if not ctx:
            return

        tw = getattr(ctx, '_render_tw', 18)
        th = getattr(ctx, '_render_th', 17)

        if not CombatUI._pixel_gauge_debug_logged:
            logger.info(f"[픽셀게이지] 오버레이 실행 중! tw={tw}, th={th}")
            CombatUI._pixel_gauge_debug_logged = True

        try:
            allies = list(self.combat_manager.allies)
            enemies = list(self.combat_manager.enemies)
        except Exception as e:
            logger.error(f"[픽셀게이지] 캐릭터 목록 접근 오류: {e}")
            return

        # ── 아군 게이지 ──
        for i, ally in enumerate(allies):
            y_base = 6 + i * 6

            # HP: cell(12, y_base+1), width=15
            max_hp = max(1, ally.max_hp)
            hp_ratio = max(0.0, min(1.0, ally.current_hp / max_hp))
            wound = getattr(ally, 'wound', 0)
            wound_ratio = wound / max_hp if wound > 0 else 0.0
            total_shield = getattr(ally, 'current_shield', 0) + getattr(ally, 'shield_amount', 0)
            if hasattr(ally, 'status_manager'):
                for eff in ally.status_manager.status_effects:
                    if hasattr(eff, 'status_type') and eff.status_type == StatusType.SHIELD:
                        total_shield += (eff.metadata.get('shield_hp', 0) if eff.metadata else 0)
            # 카운팅 + 트레일 + 자동 팝업 + 증가 딜레이
            hp_key = f"a{i}_hp"
            hp_actual = ally.current_hp
            hp_anim = self._lerp_gauge(hp_key, hp_actual + total_shield if total_shield > 0 else hp_actual, dt)
            hp_disp_ratio = self._get_display_ratio(hp_key + "_d", hp_ratio, dt)
            hp_trail = self._update_trail(hp_key + "_t", hp_ratio, dt)
            hp_display = f"{int(hp_anim)}"
            hp_cx = 12 * tw + (15 * tw) // 2
            hp_cy = (y_base + 1) * th
            self._auto_popup(hp_key, hp_actual, hp_cx, hp_cy)
            self._draw_smooth_gauge(
                12 * tw, hp_cy, 15 * tw, th,
                hp_disp_ratio, "hp",
                text=hp_display,
                wound_ratio=wound_ratio,
                shield_amount=total_shield, max_val=max_hp,
                trail_ratio=hp_trail,
            )

            # BRV: cell(12, y_base+2), width=15
            max_brv = max(1, getattr(ally, 'max_brv', 999))
            is_broken = (self.combat_manager.brave.is_broken(ally)
                         if hasattr(self.combat_manager, 'brave') else False)
            brv_ratio = max(0.0, min(1.0, ally.current_brv / max_brv))
            brv_key = f"a{i}_brv"
            brv_actual = ally.current_brv
            brv_anim = self._lerp_gauge(brv_key, brv_actual, dt)
            brv_disp_ratio = self._get_display_ratio(brv_key + "_d", brv_ratio, dt)
            brv_trail = self._update_trail(brv_key + "_t", brv_ratio, dt)
            brv_text = "BREAK!" if is_broken else f"{int(brv_anim)}"
            brv_cx = 12 * tw + (15 * tw) // 2
            brv_cy = (y_base + 2) * th
            self._auto_popup(brv_key, brv_actual, brv_cx, brv_cy)
            self._draw_smooth_gauge(
                12 * tw, brv_cy, 15 * tw, th,
                brv_disp_ratio, "brv",
                text=brv_text, is_broken=is_broken,
                trail_ratio=brv_trail,
            )

            # ATB: cell(33, y_base+1), width=15
            gauge = self.combat_manager.atb.get_gauge(ally)
            atb_value = gauge.current if gauge else 0
            atb_ratio = min(1.0, atb_value / 1000.0)
            is_current = (self.current_actor is not None and self.current_actor is ally
                          and self.state in [CombatUIState.ACTION_MENU, CombatUIState.SKILL_MENU,
                                             CombatUIState.ITEM_MENU, CombatUIState.TARGET_SELECT])
            cast_info = casting_system.get_cast_info(ally)
            cast_prog = cast_info.progress if cast_info else 0.0
            is_cast = cast_info is not None
            if is_cast and cast_prog > 0:
                atb_text = f"CAST {int(cast_prog * 100)}%"
            else:
                atb_text = f"{min(100, int(atb_value / 10))}%"
            self._draw_smooth_gauge(
                33 * tw, (y_base + 1) * th, 15 * tw, th,
                atb_ratio, "atb",
                text=atb_text,
                is_current_actor=is_current,
                cast_progress=cast_prog, is_casting=is_cast,
            )

            # MP: cell(33, y_base+2), width=15
            max_mp = max(1, ally.max_mp)
            reserved_mp = getattr(ally, 'reserved_max_mp', 0)
            mp_reserve_ratio = reserved_mp / max_mp if reserved_mp > 0 else 0.0
            mp_ratio = max(0.0, min(1.0, ally.current_mp / max_mp))
            mp_key = f"a{i}_mp"
            mp_anim = self._lerp_gauge(mp_key, ally.current_mp, dt)
            self._draw_smooth_gauge(
                33 * tw, (y_base + 2) * th, 15 * tw, th,
                mp_ratio, "mp",
                text=f"{int(mp_anim)}",
                wound_ratio=mp_reserve_ratio,
            )

        # ── 적군 게이지 ──
        ex = self.screen_width - 30  # 콘솔 셀 X 좌표

        for i, enemy in enumerate(enemies):
            y_base = 6 + i * 6

            # HP: cell(ex+7, y_base+2), width=15
            max_hp = max(1, enemy.max_hp)
            hp_ratio = max(0.0, min(1.0, enemy.current_hp / max_hp))
            enemy_shield = getattr(enemy, 'current_shield', 0) + getattr(enemy, 'shield_amount', 0)
            if hasattr(enemy, 'status_manager'):
                for eff in enemy.status_manager.status_effects:
                    if hasattr(eff, 'status_type') and eff.status_type == StatusType.SHIELD:
                        enemy_shield += (eff.metadata.get('shield_hp', 0) if eff.metadata else 0)
            ehp_key = f"e{i}_hp"
            ehp_raw = enemy.current_hp
            ehp_actual = ehp_raw + enemy_shield if enemy_shield > 0 else ehp_raw
            ehp_anim = self._lerp_gauge(ehp_key, ehp_actual, dt)
            ehp_disp_ratio = self._get_display_ratio(ehp_key + "_d", hp_ratio, dt)
            ehp_trail = self._update_trail(ehp_key + "_t", hp_ratio, dt)
            ehp_display = f"{int(ehp_anim)}"
            ehp_cx = (ex + 7) * tw + (15 * tw) // 2
            ehp_cy = (y_base + 2) * th
            self._auto_popup(ehp_key, ehp_raw, ehp_cx, ehp_cy)
            self._draw_smooth_gauge(
                (ex + 7) * tw, ehp_cy, 15 * tw, th,
                ehp_disp_ratio, "hp",
                text=ehp_display,
                shield_amount=enemy_shield, max_val=max_hp,
                trail_ratio=ehp_trail,
            )

            # BRV: cell(ex+7, y_base+3), width=15
            max_brv = max(1, getattr(enemy, 'max_brv', 9999))
            is_broken = (self.combat_manager.brave.is_broken(enemy)
                         if hasattr(self.combat_manager, 'brave') else False)
            is_scattered = False
            if hasattr(enemy, 'status_manager'):
                if enemy.status_manager.has_status(StatusType.SCATTER):
                    is_scattered = True
            brv_ratio = max(0.0, min(1.0, enemy.current_brv / max_brv))
            ebrv_key = f"e{i}_brv"
            ebrv_actual = enemy.current_brv
            ebrv_anim = self._lerp_gauge(ebrv_key, ebrv_actual, dt)
            ebrv_disp_ratio = self._get_display_ratio(ebrv_key + "_d", brv_ratio, dt)
            ebrv_trail = self._update_trail(ebrv_key + "_t", brv_ratio, dt)
            ebrv_cx = (ex + 7) * tw + (15 * tw) // 2
            ebrv_cy = (y_base + 3) * th
            self._auto_popup(ebrv_key, ebrv_actual, ebrv_cx, ebrv_cy)
            if is_broken:
                brv_text = "SCATTER!" if is_scattered else "BREAK!"
            else:
                brv_text = f"{int(ebrv_anim)}"
            custom_brv = (0, 100, 255) if is_scattered else None
            self._draw_smooth_gauge(
                (ex + 7) * tw, (y_base + 3) * th, 15 * tw, th,
                ebrv_disp_ratio, "brv",
                text=brv_text, is_broken=is_broken,
                custom_color=custom_brv,
                trail_ratio=ebrv_trail,
            )

        # ── 팀워크 게이지 ──
        # 위치: cell(6, 28), width=15 (라벨 "TW:"는 콘솔에서 cell(2,28)에 출력됨)
        party = getattr(self.combat_manager, 'party', None)
        if party:
            tw_gauge = getattr(party, 'teamwork_gauge', 0)
            max_tw = max(1, getattr(party, 'max_teamwork_gauge', 600))
            tw_ratio = max(0.0, min(1.0, tw_gauge / max_tw))
            tw_anim = self._lerp_gauge("tw", tw_gauge, dt)
            self._draw_smooth_gauge(
                6 * tw, 28 * th, 15 * tw, th,
                tw_ratio, "tw",
                text=f"{int(tw_anim)}",
            )

    def _draw_smooth_gauge(
        self,
        px: int, py: int, pw: int, ph: int,
        ratio: float,
        kind: str,
        text: str = "",
        wound_ratio: float = 0.0,
        shield_amount: float = 0.0,
        max_val: float = 0.0,
        is_broken: bool = False,
        overflow_ratio: float = 0.0,
        is_current_actor: bool = False,
        cast_progress: float = 0.0,
        is_casting: bool = False,
        custom_color: tuple = None,
        trail_ratio: float = 0.0,
    ) -> None:
        """
        단일 픽셀 단위 정밀 게이지 바 렌더링

        Args:
            px, py: 좌상단 픽셀 좌표 (렌더 텍스처 내)
            pw, ph: 게이지 픽셀 크기
            ratio: 채움 비율 (0.0 ~ 1.0)
            kind: 게이지 종류 ("hp", "brv", "mp", "atb")
            text: 게이지 내부 텍스트 (숫자 등)
            wound_ratio: 상처 비율 (HP 전용)
            shield_amount: 보호막 수치 (HP 전용)
            max_val: 최대값 (보호막 비율 계산용)
            is_broken: BRV 브레이크 여부
            overflow_ratio: ATB 오버플로우 비율
            is_current_actor: 현재 행동 중인 아군 여부 (ATB 반짝임)
            cast_progress: 캐스팅 진행도 (ATB 전용)
            is_casting: 캐스팅 중 여부 (ATB 전용)
            custom_color: 커스텀 채움 색상 (BRV SCATTER 등)
        """
        import pyray as rl
        import math
        import time as _time

        ratio = max(0.0, min(1.0, ratio))

        # ── 색상 결정 ──
        if custom_color:
            fg = custom_color
            bg = (max(0, fg[0] // 3), max(0, fg[1] // 3), max(0, fg[2] // 3))
        elif kind == "hp":
            if ratio > 0.6:
                fg, bg = (50, 220, 50), (15, 55, 15)
            elif ratio > 0.3:
                fg, bg = (220, 220, 50), (55, 55, 15)
            else:
                fg, bg = (220, 50, 50), (55, 15, 15)
        elif kind == "brv":
            if is_broken:
                fg, bg = (180, 50, 50), (50, 15, 15)
            elif ratio >= 0.95:
                # BRV 최대치 — 다홍색 불타는 효과
                pulse = 0.5 + 0.5 * math.sin(_time.time() * 4 * math.pi)
                fg = (int(220 + 35 * pulse), int(80 + 40 * pulse), int(30 + 30 * pulse))
                bg = (70, 25, 10)
            else:
                fg, bg = (230, 200, 50), (60, 50, 15)
        elif kind == "mp":
            fg, bg = (100, 150, 255), (25, 38, 65)
        elif kind == "tw":
            if ratio >= 0.8:
                fg, bg = (100, 255, 220), (30, 100, 80)
            elif ratio >= 0.5:
                fg, bg = (80, 220, 200), (25, 80, 70)
            elif ratio >= 0.25:
                fg, bg = (60, 180, 160), (20, 60, 55)
            else:
                fg, bg = (40, 140, 120), (15, 45, 40)
        elif kind == "atb":
            if is_current_actor:
                pulse = 0.35 + 0.35 * math.sin(_time.time() * 6 * math.pi)
                fg = (int(255 * (0.7 + pulse * 0.3)),
                      int(215 * (0.7 + pulse * 0.3)),
                      int(min(255, 100 * (0.5 + pulse * 0.5))))
                bg = (70, 60, 25)
            elif is_casting:
                fg, bg = (200, 100, 255), (55, 28, 70)
            else:
                fg, bg = (135, 206, 235), (35, 55, 65)
        else:
            fg, bg = (200, 200, 200), (50, 50, 50)

        # 1) 배경
        rl.draw_rectangle(px, py, pw, ph, rl.Color(bg[0], bg[1], bg[2], 255))

        # 2) 예약/상처 영역 — 오른쪽 끝에 사용 불가 표시
        wound_w = 0
        if wound_ratio > 0 and kind in ("hp", "mp"):
            wound_w = max(1, int(wound_ratio * pw))
            wound_w = min(wound_w, pw // 2)  # 최대 50%
            if kind == "hp":
                # HP 상처: 검은색 + 붉은 경계선
                rl.draw_rectangle(
                    px + pw - wound_w, py, wound_w, ph,
                    rl.Color(10, 8, 12, 255),
                )
                rl.draw_rectangle(
                    px + pw - wound_w, py, 1, ph,
                    rl.Color(120, 30, 30, 200),
                )
            else:
                # MP 예약: 어두운 보라색 + 파란 경계선
                rl.draw_rectangle(
                    px + pw - wound_w, py, wound_w, ph,
                    rl.Color(15, 8, 25, 255),
                )
                rl.draw_rectangle(
                    px + pw - wound_w, py, 1, ph,
                    rl.Color(60, 40, 120, 200),
                )

        # 3) 트레일 (잔상) — 메인 채움 전에 그려서 그 아래에 보임
        fill_w = int(ratio * pw)
        if wound_w > 0:
            fill_w = min(fill_w, pw - wound_w)
        # 감소 트레일 — fill 오른쪽에 주황/금 잔상 (메인 채움 아래에 그려도 OK)
        if trail_ratio > 0 and kind in ("hp", "brv"):
            trail_w = int(trail_ratio * pw)
            if wound_w > 0:
                trail_w = min(trail_w, pw - wound_w)
            if trail_w > fill_w:
                tc = rl.Color(220, 120, 40, 180) if kind == "hp" else rl.Color(200, 180, 80, 160)
                rl.draw_rectangle(px + fill_w, py, trail_w - fill_w, ph, tc)

        # 3b) 메인 채움
        if fill_w > 0:
            rl.draw_rectangle(px, py, fill_w, ph, rl.Color(fg[0], fg[1], fg[2], 255))

        # 3c) 증가 트레일 — 메인 채움 위에 밝은 오버레이
        if trail_ratio < 0 and kind in ("hp", "brv"):
            old_w = int(abs(trail_ratio) * pw)
            if wound_w > 0:
                old_w = min(old_w, pw - wound_w)
            if fill_w > old_w:
                tc = rl.Color(200, 255, 200, 160) if kind == "hp" else rl.Color(255, 255, 180, 160)
                rl.draw_rectangle(px + old_w, py, fill_w - old_w, ph, tc)

        # 4) 보호막 (HP only) — 채움 바 오른쪽에 파란색
        if shield_amount > 0 and max_val > 0 and kind == "hp":
            shield_ratio = shield_amount / max_val
            shield_w = max(1, int(shield_ratio * pw))
            shield_x = px + fill_w
            if shield_x + shield_w <= px + pw - wound_w:
                rl.draw_rectangle(shield_x, py, shield_w, ph, rl.Color(80, 140, 255, 200))

        # 5) ATB 오버플로우 — 흰색 게이지가 처음부터 다시 채워짐
        if overflow_ratio > 0 and kind == "atb":
            ov_w = max(1, int(overflow_ratio * pw))
            rl.draw_rectangle(px, py, ov_w, ph, rl.Color(240, 240, 255, 230))

        # 6) 캐스팅 진행도 (ATB only) — 보라색 오버레이
        if is_casting and cast_progress > 0 and kind == "atb":
            cast_w = max(1, int(cast_progress * pw))
            rl.draw_rectangle(px, py, cast_w, ph, rl.Color(200, 100, 255, 220))

        # 7) 상단 하이라이트 (반투명 흰색, 높이 1/4)
        hl_h = max(1, ph // 4)
        rl.draw_rectangle(px, py, pw, hl_h, rl.Color(255, 255, 255, 18))

        # 8) 테두리
        rl.draw_rectangle_lines(px, py, pw, ph, rl.Color(70, 70, 70, 180))

        # 9) 텍스트 (BDF 폰트, 게이지 내부 왼쪽 정렬, 원본 UI 일치)
        if text:
            try:
                tx = px + 8
                ty = py  # BDF 폰트 셀 높이 = 게이지 높이이므로 추가 정렬 불필요
                # 보호막 있으면 파란색, BREAK이면 빨간색, 기본 흰색
                if kind == "hp" and shield_amount > 0:
                    text_fg = (80, 180, 255)
                elif is_broken and kind == "brv":
                    text_fg = (255, 80, 80)
                else:
                    text_fg = (255, 255, 255)
                self._draw_bdf_text(text, tx, ty, text_fg, outline=(0, 0, 0))
            except Exception:
                pass

    def _draw_bdf_text(
        self,
        text: str,
        x: int,
        y: int,
        fg: tuple,
        outline: tuple = None,
    ) -> None:
        """BDF 폰트로 텍스트 렌더링 (배경 없음, 게이지 오버레이용)

        FontRenderer.render_cell()과 동일한 BDF 아틀라스를 사용하되
        배경을 그리지 않아 게이지 바 위에 글리프만 표시합니다.
        """
        import pyray as rl

        ctx = self._raylib_context
        if not ctx:
            return
        fr = getattr(ctx, 'font_renderer', None)
        if not fr or not getattr(fr, 'is_loaded', False):
            # 폴백: raylib 기본 폰트
            fs = getattr(fr, 'tile_height', 17) if fr else 17
            fg_c = rl.Color(fg[0], fg[1], fg[2], 255)
            if outline:
                ol_c = rl.Color(outline[0], outline[1], outline[2], 220)
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    rl.draw_text(text, x + dx, y + dy, fs, ol_c)
            rl.draw_text(text, x, y, fs, fg_c)
            return

        tw = fr.tile_width
        fg_color = rl.Color(fg[0], fg[1], fg[2], 255)

        # BDF 아틀라스 모드
        if fr._bdf_mode and fr._atlas_tex is not None:
            cur_x = x
            for char in text:
                cp = ord(char)
                if cp <= 0x20:
                    cur_x += tw
                    continue
                rect_data = fr._glyph_rects.get(cp)
                if rect_data is None:
                    cur_x += tw
                    continue
                src = rl.Rectangle(*rect_data)
                # 외곽선 (4방향)
                if outline:
                    ol_c = rl.Color(outline[0], outline[1], outline[2], 220)
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        rl.draw_texture_rec(
                            fr._atlas_tex, src,
                            rl.Vector2(float(cur_x + dx), float(y + dy)),
                            ol_c,
                        )
                # 본 글리프
                rl.draw_texture_rec(
                    fr._atlas_tex, src,
                    rl.Vector2(float(cur_x), float(y)),
                    fg_color,
                )
                cur_x += tw
        elif fr.font is not None:
            # TTF 모드 폴백
            cur_x = x
            for char in text:
                cp = ord(char)
                if cp <= 0x20:
                    cur_x += tw
                    continue
                if outline:
                    ol_c = rl.Color(outline[0], outline[1], outline[2], 220)
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        rl.draw_text_codepoint(
                            fr.font, cp,
                            rl.Vector2(float(cur_x + dx), float(y + dy)),
                            float(fr.font_size), ol_c,
                        )
                rl.draw_text_codepoint(
                    fr.font, cp,
                    rl.Vector2(float(cur_x), float(y)),
                    float(fr.font_size), fg_color,
                )
                cur_x += tw
        else:
            # 최종 폴백
            rl.draw_text(text, x, y, 17, fg_color)

    def _redraw_tooltip_area(self, console) -> None:
        """게이지 위에 툴팁 영역을 콘솔 버퍼에서 다시 렌더링

        픽셀 오버레이로 그려진 게이지가 콘솔 툴팁을 가리므로,
        툴팁이 차지하는 셀 영역을 font_renderer.render_cell()로
        다시 그려 게이지 위에 표시합니다.
        """
        ctx = self._raylib_context
        if not ctx or not console:
            return
        fr = getattr(ctx, 'font_renderer', None)
        if not fr or not getattr(fr, 'is_loaded', False):
            return

        tw_px = getattr(ctx, '_render_tw', 18)
        th_px = getattr(ctx, '_render_th', 17)

        sw = min(self.screen_width, getattr(console, 'width', 80))
        sh = min(self.screen_height, getattr(console, 'height', 50))

        # 툴팁 BG 색 = (12, 12, 25) — combat_tooltip.py BG_COLOR
        # 콘솔 버퍼에서 해당 BG 색을 가진 모든 셀을 재렌더링
        try:
            import numpy as np
            bg_arr = console.bg  # shape: (H, W, 3)
            # 툴팁 BG 매칭 마스크
            mask = (bg_arr[:, :, 0] == 12) & (bg_arr[:, :, 1] == 12) & (bg_arr[:, :, 2] == 25)
            ys, xs = np.where(mask)
            if len(ys) == 0:
                return
            # 바운딩 박스로 최적화
            y_min, y_max = int(ys.min()), int(ys.max())
            x_min, x_max = int(xs.min()), int(xs.max())
            for cy in range(y_min, y_max + 1):
                for cx in range(x_min, x_max + 1):
                    if mask[cy, cx]:
                        ch = int(console.ch[cy, cx])
                        fg = (int(console.fg[cy, cx, 0]), int(console.fg[cy, cx, 1]), int(console.fg[cy, cx, 2]))
                        bg = (12, 12, 25)
                        fr.render_cell(cx * tw_px, cy * th_px, ch, fg, bg)
        except Exception:
            pass

    def _render_training_stats(self, console: tcod.console.Console):
        """트레이닝 모드 통계 렌더링"""
        if not self.training_dummy:
            return

        stats = self.training_dummy.get_statistics()

        # 통계 표시 위치
        training_variant = getattr(self, "training_variant", None)
        if training_variant == "party":
            # 4인 트레이닝: 통계 대신 피해량 순위 (우상단)
            if not self.training_damage_log:
                return
            x = self.screen_width - 28
            y = 0
            console.print(x, y, "[피해 순위]", fg=(255, 220, 120))
            y += 1
            ranked = sorted(self.training_damage_log.items(), key=lambda kv: kv[1], reverse=True)
            for idx, (name, dmg) in enumerate(ranked[:4], start=1):
                console.print(x, y, f"{idx}. {name}: {dmg:,}", fg=(255, 180, 150))
                y += 1
            return
        else:
            # 기본: 화면 오른쪽, 적군 영역 아래
            x = self.screen_width - 35
            y = 15

        # 제목
        console.print(x, y, "[트레이닝 통계]", fg=(255, 255, 100))

        # 총 HP 데미지
        console.print(x, y + 1, f"총 HP: {stats['total_hp_damage']:,}", fg=(255, 150, 150))

        # 평균 HP 데미지 (소수점 1자리)
        avg_hp = stats['avg_hp_per_turn']
        console.print(x, y + 2, f"평균 HP: {avg_hp:,.1f}/턴", fg=(255, 100, 100))

        # 턴 수
        console.print(x, y + 3, f"총 턴: {stats['turn_count']}", fg=(200, 200, 200))

    def _render_messages(self, console: tcod.console.Console):
        """메시지 로그 렌더링 (오른쪽에 배치, 스크롤 형식)"""
        # 커맨드 창(action_menu)과 같은 높이: y=30으로 위로 이동 (33 -> 30)
        msg_y = 30
        
        # 오른쪽에 배치: x=40으로 왼쪽으로 이동하여 너비 증가 (42 -> 40)
        msg_x = 40
        msg_width = self.screen_width - msg_x - 2  # 오른쪽 여백 2 (스크롤 인디케이터 공간, 3 -> 2로 감소)
        
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

    def _render_floating_dialogues(self, console: tcod.console.Console):
        """떠다니는 대사 렌더링 (림버스 컴퍼니 스타일 - 글리치/공포 효과)"""
        to_remove = []

        for dialogue in self.floating_dialogues:
            # 프레임 감소
            dialogue.frames_remaining -= 1

            if dialogue.frames_remaining <= 0:
                to_remove.append(dialogue)
                continue

            # 타이핑 효과 (글자 수 증가 - 매우 느리게)
            if dialogue.current_char_index < len(dialogue.text):
                dialogue.current_char_index += dialogue.typing_speed
                dialogue.current_char_index = min(dialogue.current_char_index, float(len(dialogue.text)))

            # 현재까지 출력할 텍스트 (float를 int로 변환)
            visible_char_count = int(dialogue.current_char_index)
            visible_text = dialogue.text[:visible_char_count]

            # 페이드 아웃 효과 (매우 느리게)
            color = dialogue.color
            if dialogue.frames_remaining <= dialogue.fade_start_frames:
                # 알파값 감소 효과 (색상 어둡게) - 5초에 걸쳐 서서히
                fade_ratio = dialogue.frames_remaining / dialogue.fade_start_frames
                color = (
                    int(dialogue.color[0] * fade_ratio),
                    int(dialogue.color[1] * fade_ratio),
                    int(dialogue.color[2] * fade_ratio)
                )

            # 대사 출력 (따옴표 추가)
            if visible_text:
                try:
                    console.print(
                        dialogue.x,
                        dialogue.y,
                        f'"{visible_text}"',
                        fg=color
                    )
                except Exception as e:
                    # 화면 밖으로 나가는 경우 무시
                    logger.debug(f"떠다니는 대사 렌더링 오류: {e}")

        # 만료된 대사 제거
        for dialogue in to_remove:
            self.floating_dialogues.remove(dialogue)

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
        
        # 기믹 타입 별칭 통합 (중복 기믹 타입 처리)
        gimmick_aliases = {
            # 암살자 기믹 통합
            "shadow_system": "stealth_exposure",
            "stealth_system": "stealth_exposure",
            "stealth_mastery": "stealth_exposure",
            # 해커 기믹 통합
            "hack_system": "multithread_system",
            "hack_threading": "multithread_system",
            # 검투사 기믹 통합
            "arena_system": "crowd_cheer",
            "cheer_gauge": "crowd_cheer",
            # 몽크 기믹 통합
            "ki_system": "yin_yang_flow",
            # 궁수 기믹 통합
            "support_fire_system": "support_fire",
            # 광전사 기믹 통합
            "rage_system": "madness_threshold",
            "madness_gauge": "madness_threshold",
            # 흡혈귀 기믹 통합
            "blood_system": "thirst_gauge",
        }
        gimmick_type = gimmick_aliases.get(gimmick_type, gimmick_type)

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

        elif gimmick_type == "break_system":
            # 브레이커 - 연격 기믹
            combo = getattr(character, 'combo_gauge', 0)
            return (f"연격:{combo}", (255, 150, 50))

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
            # 도적 - 훔친 아이템 (독은 적에게 적용되므로 아이템 표시)
            items = getattr(character, 'stolen_items', 0)
            return (f"아이템:{items}", (255, 220, 100))

        elif gimmick_type == "shadow_system":
            # 암살자 - 그림자
            shadows = getattr(character, 'shadow_count', 0)
            max_shadows = getattr(character, 'max_shadow_count', 5)
            return (f"그림자:{shadows}/{max_shadows}", (100, 50, 150))
        elif gimmick_type == "mp_overload_system":
            # MP 게이지에서 시각화하므로 별도 텍스트 없음
            return ("", (255, 255, 255))

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

        elif gimmick_type == "charge_system":
            # 암흑기사 - 충전 시스템
            charge = getattr(character, 'charge_gauge', 0)
            max_charge = getattr(character, 'max_charge', 100)
            return (f"충전:{charge}/{max_charge}", (100, 50, 150))

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

        elif gimmick_type == "dimension_refraction":
            # 차원술사 - 차원 굴절
            refraction = getattr(character, 'refraction_stacks', 0)
            return (f"굴절: {refraction}", (200, 150, 255))

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

        elif gimmick_type == "kenshin_system":
            # 사무라이 - 검심 시스템
            observation = getattr(character, 'observation', 0)
            kenatsu = getattr(character, 'kenatsu', 0)

            # 관찰 단계 색상
            if observation >= 10:
                stage_color = (255, 100, 100)  # 검성 - 빨강
                stage = "검성"
            elif observation >= 5:
                stage_color = (255, 200, 100)  # 무심 - 주황
                stage = "무심"
            else:
                stage_color = (200, 200, 200)  # 초심 - 회색
                stage = "초심"

            return (f"{stage} 관찰{observation} 검압{kenatsu}", stage_color)

        elif gimmick_type == "blade_circuit":
            # 마검사 - 블레이드 서킷
            steel = getattr(character, 'steel_line', 0)
            mana = getattr(character, 'mana_line', 0)
            sigil = getattr(character, 'resonance_sigil', 0)
            return (f"스틸 {steel} 마나 {mana} 시그넷 {sigil}", (120, 200, 255))
        elif gimmick_type == "enchant_system":
            # 구버전 마검사 - 마나 블레이드
            mana = getattr(character, 'mana_blade', 0)
            max_mana = getattr(character, 'max_mana_blade', 100)
            return (f"마검:{mana}/{max_mana}", (100, 150, 255))

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
            # 배틀메이지 - 룬 공명 (간략: 게이지 + 완전 공명만 표시)
            gauge = getattr(character, 'resonance_gauge', 0)
            perfect = getattr(character, 'perfect_resonance', False)
            if perfect:
                return (f"공명 {gauge} 완전", (255, 215, 0))
            return (f"공명 {gauge}", (200, 100, 255))

        elif gimmick_type == "probability_distortion":
            # 차원술사 - 확률 왜곡 (간략: 게이지)
            gauge = getattr(character, 'distortion_gauge', 0)
            return (f"왜곡:{gauge}", (150, 150, 255))

        elif gimmick_type == "heat_gauge":
            # 엔지니어 - 열 게이지 (간략: 상태) - 이미 이름 옆에 표시됨
            heat = getattr(character, 'heat', 0)
            return ("", (255, 255, 255))  # 빈 문자열 반환 (이미 이름 옆에 표시됨)

        elif gimmick_type == "heat_management":
            # 기계공학자 - 열 관리 + 포탑 시스템
            heat = getattr(character, 'heat', 0)
            turrets = getattr(character, 'turret_count', 0)
            # 열 상태에 따른 색상
            if heat >= 80:
                color = (255, 50, 50)  # 위험 (빨강)
            elif heat >= 50:
                color = (100, 255, 100)  # 최적 (초록)
            else:
                color = (255, 150, 50)  # 준비 (주황)
            return (f"열:{heat} 포탑:{turrets}", color)

        elif gimmick_type == "thirst_gauge":
            # 흡혈귀 - 갈증 (간략: 게이지)
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
            # 철학자 - 딜레마 (가장 진행된 선택 + 발동 상태 표시)
            threshold = getattr(character, 'accumulation_threshold', 3)
            choices = {
                '힘': getattr(character, 'choice_power', 0),
                '지혜': getattr(character, 'choice_wisdom', 0),
                '희생': getattr(character, 'choice_sacrifice', 0),
                '생존': getattr(character, 'choice_survival', 0),
                '진실': getattr(character, 'choice_truth', 0),
                '거짓': getattr(character, 'choice_lie', 0),
            }
            # 발동된 딜레마 수
            activated = [name for name, count in choices.items() if count >= threshold]
            if len(activated) >= 2:
                return (f"{'·'.join(activated[:2])}발동!", (255, 200, 100))
            elif len(activated) == 1:
                # 발동 1개 + 가장 높은 미발동 표시
                rest = {n: c for n, c in choices.items() if c < threshold}
                if rest:
                    next_name = max(rest, key=rest.get)
                    next_val = rest[next_name]
                    return (f"{activated[0]}✓ {next_name}:{next_val}/{threshold}", (200, 150, 255))
                return (f"{activated[0]} 발동!", (255, 200, 100))
            else:
                # 미발동: 가장 높은 선택 표시
                if any(choices.values()):
                    lead_name = max(choices, key=choices.get)
                    lead_val = choices[lead_name]
                    return (f"{lead_name}:{lead_val}/{threshold}", (200, 150, 255))
                return ("딜레마 대기", (150, 150, 200))

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
            # 검투사 - 군중의 환호 + 현재 요구
            cheer = getattr(character, 'cheer', 0)
            max_cheer = getattr(character, 'max_cheer', 100)
            current_demand = getattr(character, 'current_demand', None)
            demand_name = current_demand.get("name", "") if current_demand else ""
            if demand_name:
                return (f"환호:{cheer} [{demand_name}]", (255, 200, 100))
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
            stealth_active = getattr(character, 'stealth_active', False)
            exposed_turns = getattr(character, 'exposed_turns', 0)
            restealth_cooldown = getattr(character, 'restealth_cooldown', 3)
            
            if stealth_active:
                return ("은신", (100, 100, 255))
            else:
                remaining = max(0, restealth_cooldown - exposed_turns)
                return (f"노출:{exposed_turns}/{restealth_cooldown}", (255, 150, 150))

        # ============================================================
        # === 12개 리워크 직업 기믹 간략 표시 ===
        # ============================================================
        
        elif gimmick_type == "rum_treasure_system":
            # 해적 - 럼주 & 보물
            treasures = getattr(character, 'treasure_inventory', [])
            rum_effect = getattr(character, 'current_rum_effect', None)
            rum_text = "럼+" if rum_effect else ""
            return (f"{rum_text}보물:{len(treasures)}", (255, 200, 100))
        
        elif gimmick_type == "score_composition":
            # 바드 - 악보 작곡: 음표 순서 표시
            notes = getattr(character, 'music_notes', [])
            notes_str = ''.join(notes) if notes else "---"
            return (f"음표: {notes_str}", (200, 150, 255))
        
        elif gimmick_type == "alchemy_system":
            # 연금술사 - 포션 조합
            stock = getattr(character, 'potion_stock', 0)
            max_stock = getattr(character, 'max_potion_stock', 10)
            return (f"재료:{stock}/{max_stock}", (100, 255, 150))
        
        elif gimmick_type == "duty_system":
            # 기사 - 의무
            duty = getattr(character, 'duty_stacks', 0)
            max_duty = getattr(character, 'max_duty_stacks', 10)
            if duty >= max_duty:
                return (f"의무:MAX", (255, 215, 0))
            return (f"의무:{duty}/{max_duty}", (100, 150, 255))
        
        elif gimmick_type == "divinity_system":
            # 성기사 - 신앙/심판 (구버전)
            faith = getattr(character, 'faith_points', 0)
            judgment = getattr(character, 'judgment_points', 0)
            return (f"신:{faith} 심:{judgment}", (255, 255, 150))

        elif gimmick_type == "oracle_system":
            # 신관 - 신탁 시스템
            faith = getattr(character, 'faith', 0)
            combo = getattr(character, 'oracle_combo', 0)
            turn_count = getattr(character, 'oracle_turn_count', 0)
            current_oracle = getattr(character, 'current_oracle', None)
            if current_oracle and not current_oracle.get('fulfilled', False):
                oracle_name = current_oracle.get('name', '신탁')
                # 신탁 이름 약칭
                oracle_short = oracle_name.replace('의 신탁', '').replace('신탁', '')[:2]
                return (f"신앙:{faith} {oracle_short}[{turn_count}/4]", (255, 220, 150))
            return (f"신앙:{faith} [{turn_count}/4]", (255, 215, 100))

        elif gimmick_type == "theft_system":
            # 도적 - 절도
            stolen = getattr(character, 'stolen_items', 0)
            max_stolen = getattr(character, 'max_stolen_items', 10)
            evasion = getattr(character, 'evasion_active', False)
            ev_text = " 회피" if evasion else ""
            return (f"절도:{stolen}{ev_text}", (150, 100, 200))
        
        elif gimmick_type == "blade_circuit":
            steel = getattr(character, 'steel_line', 0)
            mana = getattr(character, 'mana_line', 0)
            sigil = getattr(character, 'resonance_sigil', 0)
            return (f"스틸 {steel} 마나 {mana} 시그넷 {sigil}", (120, 200, 255))
        elif gimmick_type == "enchant_system":
            # 구버전 마검사 - 마나 블레이드
            mana = getattr(character, 'mana_blade', 0)
            max_mana = getattr(character, 'max_mana_blade', 100)
            if mana >= max_mana:
                return (f"마나:MAX", (100, 200, 255))
            return (f"마나:{mana}", (100, 200, 255))
        
        elif gimmick_type == "curse_system" or gimmick_type == "totem_system":
            # 무당 - 저주
            curse = getattr(character, 'curse_stacks', 0)
            max_curse = getattr(character, 'max_curse_stacks', 10)
            if curse >= max_curse:
                return (f"저주:MAX", (150, 0, 150))
            return (f"저주:{curse}/{max_curse}", (150, 50, 150))
        
        elif gimmick_type == "shapeshifting_system":
            # 드루이드 - 변신
            nature = getattr(character, 'nature_points', 0)
            form = getattr(character, 'current_form', None)
            form_names = {"bear": "곰", "panther": "표범", "eagle": "독수리", "wolf": "늑대"}
            if form:
                return (f"{form_names.get(form, form)} NP:{nature}", (100, 200, 100))
            return (f"NP:{nature}", (100, 200, 100))
        
        elif gimmick_type == "elemental_spirits":
            # 정령술사 - 4대 정령
            spirits = []
            if getattr(character, 'spirit_fire', 0): spirits.append("화")
            if getattr(character, 'spirit_water', 0): spirits.append("수")
            if getattr(character, 'spirit_wind', 0): spirits.append("풍")
            if getattr(character, 'spirit_earth', 0): spirits.append("지")
            if spirits:
                return (f"정령:{','.join(spirits)}", (150, 255, 200))
            return ("정령:없음", (100, 100, 100))
        
        elif gimmick_type == "trick_deck":
            # 마술사 - 트릭 덱
            hand = getattr(character, 'card_hand', [])
            deck = getattr(character, 'card_deck', [])
            max_hand = getattr(character, 'max_hand_size', 8)
            # 현재 조합 표시
            combo_type = getattr(character, 'current_combo', None)
            if combo_type:
                combo_names = {"pair": "원페어", "two_pair": "투페어", "triple": "트리플", 
                              "straight": "스트레이트", "flush": "플러시", "full_house": "풀하우스",
                              "four_of_kind": "포카드", "straight_flush": "스트레이트 플러시"}
                return (f"{combo_names.get(combo_type, combo_type)} 패:{len(hand)}", (255, 200, 100))
            return (f"패:{len(hand)}/{max_hand} 덱:{len(deck)}", (255, 200, 100))
        
        elif gimmick_type == "possibility_slots":
            # 시간술사 - 가능성 슬롯
            slots = getattr(character, 'possibility_slots', [])
            max_slots = getattr(character, 'max_possibility_slots', 4)
            slot_count = len(slots)
            # 슬롯 상태 아이콘 표시 (채워진 슬롯: ◆, 빈 슬롯: ◇)
            slot_icons = "◆" * slot_count + "◇" * (max_slots - slot_count)
            if slot_count >= max_slots:
                return (f"가능성:{slot_icons} MAX", (200, 255, 255))
            return (f"가능성:{slot_icons}", (150, 200, 255))

        elif gimmick_type == "phantom_legion":
            # 환술사 - 환영 군단
            phantom_count = getattr(character, 'phantom_count', 0)
            max_phantoms = getattr(character, 'max_phantoms', 4)
            afterimage = getattr(character, 'afterimage_gauge', 0)
            # 환영 아이콘 (활성: ◆, 빈 슬롯: ◇)
            phantom_icons = "◆" * phantom_count + "◇" * (max_phantoms - phantom_count)

            # 확정 회피 상태 확인 (버프 우선, 그 다음 준비 상태)
            has_guaranteed_evasion = False
            if hasattr(character, 'active_buffs') and character.active_buffs:
                evasion_buff = character.active_buffs.get('evasion_up')
                if evasion_buff and evasion_buff.get('value', 0.0) >= 5.0:
                    has_guaranteed_evasion = True

            # 확정 회피 준비 상태 계산 (플래그가 아니라 실시간으로 계산)
            mirror_shift_cooldown = getattr(character, 'mirror_shift_cooldown', 0)
            mirror_ready = phantom_count >= 2 and mirror_shift_cooldown == 0

            if has_guaranteed_evasion:
                return (f"환영:{phantom_icons} 확정회피중", (255, 255, 100))
            elif mirror_ready:
                return (f"환영:{phantom_icons} 확정회피", (200, 150, 255))
            if phantom_count >= max_phantoms:
                return (f"환영:{phantom_icons} 잔상:{afterimage}", (180, 120, 255))
            return (f"환영:{phantom_icons} 잔상:{afterimage}", (150, 100, 200))

        elif gimmick_type == "oath_system":
            # 성기사 - 서약 시스템
            current_oath = getattr(character, 'current_oath', None)
            faith = getattr(character, 'faith', 0)
            max_faith = getattr(character, 'max_faith', 100)
            oaths = getattr(character, 'oaths', {})
            if current_oath:
                oath_info = oaths.get(current_oath, {})
                oath_name = oath_info.get('name', current_oath)
                short_name = oath_name.replace('의 서약', '')
                return (f"[{short_name}] 신앙:{faith}/{max_faith}", (255, 255, 150))
            else:
                return (f"서약없음 신앙:{faith}/{max_faith}", (200, 200, 100))

        elif gimmick_type == "ninpo_chain":
            # 닌자 - 인법 연쇄
            fire = getattr(character, 'seal_fire', 0)
            ice = getattr(character, 'seal_ice', 0)
            thunder = getattr(character, 'seal_thunder', 0)
            wind = getattr(character, 'seal_wind', 0)
            total = fire + ice + thunder + wind
            seals = []
            if fire: seals.append(f"火{fire}")
            if ice: seals.append(f"氷{ice}")
            if thunder: seals.append(f"雷{thunder}")
            if wind: seals.append(f"風{wind}")
            seal_text = "/".join(seals) if seals else "0"
            # 마지막 사용 속성에 따른 기본 색상
            last_elem = getattr(character, 'last_seal_element', None)
            element_colors = {
                "fire": (255, 100, 50),
                "ice": (100, 200, 255),
                "thunder": (255, 255, 100),
                "wind": (100, 255, 150),
            }
            base_color = element_colors.get(last_elem, (200, 200, 200))
            # 은신 상태 표시
            stealth = getattr(character, 'ninja_stealth', False)
            if stealth:
                return (f"은신 인:{seal_text}", (100, 200, 150))
            # 연쇄 단계별 색상 (높은 단계는 고유 색상 우선)
            if total >= 4:
                return (f"인:{seal_text} 만화경!", (255, 100, 255))
            elif total >= 3:
                return (f"인:{seal_text} 폭주", (255, 200, 50))
            elif total >= 2:
                return (f"인:{seal_text} 강화", (255, 150, 0))
            return (f"인:{seal_text}", base_color)

        return ("", (255, 255, 255))

    def _render_gimmick_view(self, console: tcod.console.Console):
        """기믹 상세 보기 렌더링 (박스 스타일)"""
        if not self.gimmick_view_character:
            return

        character = self.gimmick_view_character
        gimmick_type = getattr(character, 'gimmick_type', None)

        # 전체 화면을 완전히 검게 덮어 기존 UI(트레이닝 통계/아군파티/턴 화살표 등) 가림
        try:
            console.clear(ch=ord(" "), fg=(0, 0, 0), bg=(0, 0, 0))
        except Exception:
            try:
                console.draw_rect(0, 0, self.screen_width, self.screen_height, ord(" "), bg=(0, 0, 0))
            except Exception:
                pass

        # 박스 위치 및 크기
        box_width = 50
        box_height = 18  # 기본값
        # 기본 위치/오프셋
        box_x = 2
        box_y = 2
        content_x = box_x + 2
        content_y = box_y + 1

        line = 0
        # 기믹 타입에 따라 높이 조정
        if gimmick_type == "dilemma_choice":
            # 철학자 - 딜레마 선택: 더 많은 공간 필요 (제목 + 구분선 + 4가지 선택 + 구분선 + 경향 + 하단 안내)
            box_height = 28
        elif gimmick_type == "rune_resonance":
            box_height = 24  # 완전 공명 상태 표시 추가로 높이 증가
            # 배틀메이지 - 룬 공명
            fire = getattr(character, 'rune_fire', 0)
            ice = getattr(character, 'rune_ice', 0)
            lightning = getattr(character, 'rune_lightning', 0)
            earth = getattr(character, 'rune_earth', 0)
            arcane = getattr(character, 'rune_arcane', 0)
            max_rune = getattr(character, 'max_rune_per_type', 3)
            resonance_gauge = getattr(character, 'resonance_gauge', 0)
            max_resonance_gauge = getattr(character, 'max_resonance_gauge', 100)
            gauge_bar = self._create_gauge_bar(resonance_gauge, max_resonance_gauge, width=10)
            resonances = []

            console.print(content_x, content_y + line, "배틀메이지 - 룬 공명", fg=(200, 100, 255))
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
            console.print(content_x, content_y + line, f" 대지 룬: {earth}/{max_rune}", fg=(139, 69, 19))
            line += 1
            console.print(content_x, content_y + line, f" 비전 룬: {arcane}/{max_rune}", fg=(200, 100, 255))
            line += 1
            console.print(content_x, content_y + line, f" 공명 게이지: {gauge_bar} ({resonance_gauge}/{max_resonance_gauge})", fg=(200, 180, 255))
            line += 1

            # 완전 공명 상태 표시
            perfect_resonance = getattr(character, 'perfect_resonance', False)
            if perfect_resonance:
                console.print(content_x, content_y + line, "완전 공명 활성!", fg=(255, 215, 0))
                line += 1
                console.print(content_x, content_y + line, " 다음 룬 폭발: 피해 +150%, 연쇄 +50%", fg=(255, 255, 100))
                line += 1

            console.print(box_x, content_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 공명 가능 패턴 체크

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
            # 흡혈귀 - 갈증
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

        elif gimmick_type == "heat_management":
            # 기계공학자 - 열 관리 + 포탑 시스템
            heat = getattr(character, 'heat', 0)
            max_heat = getattr(character, 'max_heat', 100)
            optimal_min = getattr(character, 'optimal_min', 50)
            optimal_max = getattr(character, 'optimal_max', 79)
            danger_min = getattr(character, 'danger_min', 80)
            turrets = getattr(character, 'turret_count', 0)
            fire_turrets = getattr(character, 'fire_turret_count', 0)
            ice_turrets = getattr(character, 'ice_turret_count', 0)
            thunder_turrets = getattr(character, 'thunder_turret_count', 0)
            explosive_turrets = getattr(character, 'explosive_turret_count', 0)
            heal_turrets = getattr(character, 'heal_turret_count', 0)
            normal_turrets = turrets - fire_turrets - ice_turrets - thunder_turrets - explosive_turrets - heal_turrets

            console.print(content_x, content_y + line, " 기계공학자 - 열 관리 & 포탑", fg=(255, 150, 50))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 열 게이지 (색상으로 구간 표시)
            if heat >= danger_min:
                heat_color = (255, 50, 50)
                heat_status = "위험!"
            elif heat >= optimal_min:
                heat_color = (100, 255, 100)
                heat_status = "최적"
            else:
                heat_color = (255, 150, 50)
                heat_status = "준비"
            
            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, heat, max_heat, show_numbers=True, custom_color=heat_color)
            line += 1
            console.print(content_x, content_y + line, f"열 상태: {heat_status}", fg=heat_color)
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 포탑 정보
            console.print(content_x, content_y + line, f" 총 포탑: {turrets}개", fg=(255, 200, 100))
            line += 1
            
            if turrets > 0:
                if normal_turrets > 0:
                    console.print(content_x, content_y + line, f"  - 일반: {normal_turrets}개 (0.5배)", fg=(200, 200, 200))
                    line += 1
                if fire_turrets > 0:
                    console.print(content_x, content_y + line, f"  - 화염: {fire_turrets}개 (0.6배+화상20%)", fg=(255, 100, 50))
                    line += 1
                if ice_turrets > 0:
                    console.print(content_x, content_y + line, f"  - 빙결: {ice_turrets}개 (0.4배+둔화25%)", fg=(100, 200, 255))
                    line += 1
                if thunder_turrets > 0:
                    console.print(content_x, content_y + line, f"  - 전기: {thunder_turrets}개 (0.5배+마비15%)", fg=(255, 255, 100))
                    line += 1
                if explosive_turrets > 0:
                    console.print(content_x, content_y + line, f"  - 폭발: {explosive_turrets}개 (0.7배AOE)", fg=(255, 150, 100))
                    line += 1
                if heal_turrets > 0:
                    console.print(content_x, content_y + line, f"  - 치유: {heal_turrets}개 (공격력30%)", fg=(100, 255, 100))
                    line += 1
                line += 1

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 효과 설명
            console.print(content_x, content_y + line, "=== 포탑 효과 ===", fg=(150, 150, 150))
            line += 1
            net_heat = -5 + turrets * 2
            if net_heat >= 0:
                console.print(content_x, content_y + line, f"턴당 열 {net_heat:+d} (-5 + 포탑당 +2)", fg=(255, 150, 50))
            else:
                console.print(content_x, content_y + line, f"턴당 열 {net_heat:+d} (-5 + 포탑당 +2)", fg=(100, 200, 255))
            line += 1
            console.print(content_x, content_y + line, "피격 시: 포탑 1개 파괴, 피해 -40%", fg=(100, 200, 255))
            line += 1

            # 구간별 보너스
            if heat >= optimal_min and heat < danger_min:
                console.print(content_x, content_y + line, "[최적 구간] 모든 스탯 +15%", fg=(100, 255, 100))
            elif heat >= danger_min:
                console.print(content_x, content_y + line, "[위험 구간] 크리티컬 +20%", fg=(255, 100, 100))
                line += 1
                console.print(content_x, content_y + line, "⚠ 열 100 도달 시 오버히트!", fg=(255, 50, 50))

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
            # 시간술사 - 시간 마크 (레거시)
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

        elif gimmick_type == "possibility_slots":
            # 시간술사 - 가능성 슬롯 (평행시간선 소환사)
            slots = getattr(character, 'possibility_slots', [])
            max_slots = getattr(character, 'max_possibility_slots', 4)
            slot_count = len(slots)

            console.print(content_x, content_y + line, "⌛ 시간술사 - 가능성 슬롯", fg=(150, 200, 255))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 슬롯 상태 표시
            slot_icons = ""
            for i in range(max_slots):
                if i < slot_count:
                    slot_icons += "◆ "
                else:
                    slot_icons += "◇ "
            console.print(content_x, content_y + line, f" 슬롯: {slot_icons}({slot_count}/{max_slots})", fg=(200, 255, 255))
            line += 2

            # 저장된 가능성 스킬 목록
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1
            console.print(content_x, content_y + line, " 저장된 가능성:", fg=(200, 200, 200))
            line += 1

            skill_names = {
                'time_bolt': '타임 볼트', 'time_shock': '타임 쇼크',
                'chrono_blast': '크로노 블라스트', 'time_wave': '타임 웨이브',
                'haste': '헤이스트', 'slow': '슬로우',
                'time_stop': '시간 정지', 'time_accel': '시간 가속',
                'future_sight': '미래 예지', 'past_regression': '과거 회귀',
                'rewind': '리와인드', 'paradox_guard': '역설 방어'
            }

            if slots:
                for i, slot in enumerate(slots):
                    skill_id = slot.get('skill_id', '???')
                    power = slot.get('power_ratio', 0.85)
                    reuse = slot.get('reuse_count', 0)
                    skill_name = skill_names.get(skill_id, skill_id)
                    reuse_text = f" (재사용:{reuse})" if reuse > 0 else ""
                    console.print(content_x + 2, content_y + line, f"{i+1}. {skill_name} ({int(power*100)}%){reuse_text}", fg=(150, 255, 200))
                    line += 1
            else:
                console.print(content_x + 2, content_y + line, "(없음)", fg=(100, 100, 100))
                line += 1

            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 평행 공명 효과
            damage_reduction = getattr(character, '_parallel_resonance_damage_reduction', 0)
            atb_bonus = getattr(character, '_parallel_resonance_atb_bonus', 0)
            console.print(content_x, content_y + line, " 평행 공명 효과:", fg=(200, 200, 200))
            line += 1
            console.print(content_x + 2, content_y + line, f"마법 공격력: +{slot_count * 8}%", fg=(255, 200, 255))
            line += 1
            console.print(content_x + 2, content_y + line, f"받는 피해: -{int(damage_reduction * 100)}%", fg=(100, 255, 150))
            line += 1
            if slot_count >= max_slots:
                console.print(content_x + 2, content_y + line, f"ATB 보너스: +{int(atb_bonus * 100)}% (MAX)", fg=(255, 255, 100))

        elif gimmick_type == "phantom_legion":
            # 환술사 - 환영 군단
            phantom_count = getattr(character, 'phantom_count', 0)
            max_phantoms = getattr(character, 'max_phantoms', 4)
            phantom_hits = getattr(character, 'phantom_hits', [])
            afterimage = getattr(character, 'afterimage_gauge', 0)
            max_afterimage = getattr(character, 'afterimage_max', 100)
            mirror_shift_cooldown = getattr(character, 'mirror_shift_cooldown', 0)
            # 확정 회피 준비 상태 실시간 계산 (환영 2개 이상 + 쿨다운 0)
            mirror_shift_ready = phantom_count >= 2 and mirror_shift_cooldown == 0

            console.print(content_x, content_y + line, "🌙 환술사 - 환영 군단", fg=(180, 120, 255))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 환영 상태 표시
            phantom_icons = ""
            for i in range(max_phantoms):
                if i < phantom_count:
                    hits = phantom_hits[i] if i < len(phantom_hits) else 0
                    phantom_icons += f"◆({hits}) "
                else:
                    phantom_icons += "◇ "
            console.print(content_x, content_y + line, f" 환영: {phantom_icons}", fg=(200, 150, 255))
            line += 1
            
            # 환영 보너스
            evasion_bonus = phantom_count * 12
            redirect_chance = int((1 - (0.70 ** phantom_count)) * 100) if phantom_count > 0 else 0
            console.print(content_x + 2, content_y + line, f"회피 +{evasion_bonus}% | 대신 맞을 확률: {redirect_chance}%", fg=(150, 200, 255))
            line += 2

            # 잔상 게이지
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1
            console.print(content_x, content_y + line, " 잔상 게이지:", fg=(200, 200, 200))
            line += 1
            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, afterimage, max_afterimage, show_numbers=True, custom_color=(180, 100, 220))
            line += 2

            # 확정 회피 상태
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1
            console.print(content_x, content_y + line, " 확정 회피 (Mirror Shift):", fg=(200, 200, 200))
            line += 1
            if mirror_shift_ready:
                console.print(content_x + 2, content_y + line, "★ 준비 완료! (환영 2개 이상 필요)", fg=(255, 255, 100))
            elif mirror_shift_cooldown > 0:
                console.print(content_x + 2, content_y + line, f"쿨다운: {mirror_shift_cooldown}턴 남음", fg=(150, 150, 150))
            else:
                console.print(content_x + 2, content_y + line, "환영 2개 이상 필요", fg=(150, 150, 150))
            line += 1

            # 스킬 조건 안내
            if afterimage >= 80:
                console.print(content_x + 2, content_y + line, "💫 무한 반사 사용 가능!", fg=(255, 200, 255))
            elif afterimage >= 50:
                console.print(content_x + 2, content_y + line, "✨ 잔상 폭발 사용 가능", fg=(200, 150, 255))

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

        elif gimmick_type == "charge_system":
            # 암흑기사 - 충전 시스템
            charge = getattr(character, 'charge_gauge', 0)
            max_charge = getattr(character, 'max_charge', 100)

            console.print(content_x, content_y + line, " 암흑기사 - 충전 시스템", fg=(100, 50, 150))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, charge, max_charge, show_numbers=True, custom_color=(100, 50, 150))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 충전 단계별 정보 표시
            if charge >= 100:
                console.print(content_x, content_y + line, " 완전충전!", fg=(255, 200, 100))
                line += 1
                console.print(content_x, content_y + line, " 물공 +60%, 치명타 확정", fg=(255, 255, 200))
            elif charge >= 75:
                console.print(content_x, content_y + line, " 결정타 단계", fg=(255, 150, 100))
                line += 1
                console.print(content_x, content_y + line, " 물공 +35%, 치명타율 +20%", fg=(255, 200, 150))
            elif charge >= 50:
                console.print(content_x, content_y + line, " 강화 단계", fg=(200, 150, 255))
                line += 1
                console.print(content_x, content_y + line, " 물공 +20%, 치명타율 +10%", fg=(200, 180, 255))
            elif charge >= 25:
                console.print(content_x, content_y + line, " 집중 단계", fg=(150, 100, 200))
                line += 1
                console.print(content_x, content_y + line, " 물공 +10%, 치명타율 +5%", fg=(180, 150, 220))
            else:
                console.print(content_x, content_y + line, " 준비 단계", fg=(120, 120, 180))

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

        elif gimmick_type == "blade_circuit":
            # 마검사 - 블레이드 서킷
            steel = getattr(character, 'steel_line', 0)
            mana = getattr(character, 'mana_line', 0)
            max_steel = getattr(character, 'max_steel_line', 100)
            max_mana = getattr(character, 'max_mana_line', 100)
            sigil = getattr(character, 'resonance_sigil', 0)
            max_sigil = getattr(character, 'max_resonance_sigil', 3)

            console.print(content_x, content_y + line, " 마검사 - 블레이드 서킷", fg=(120, 200, 255))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            console.print(content_x, content_y + line, f"스틸: {steel}/{max_steel}", fg=(120, 180, 255))
            line += 1
            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, steel, max_steel, custom_color=(120, 180, 255))
            line += 1
            console.print(content_x, content_y + line, f"마나: {mana}/{max_mana}", fg=(150, 120, 255))
            line += 1
            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, mana, max_mana, custom_color=(150, 120, 255))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1
            console.print(content_x, content_y + line, f" 시그넷: {sigil}", fg=(200, 220, 255))
            line += 1

        elif gimmick_type == "enchant_system":
            # 구버전 마검사 - 마력 부여
            mana = getattr(character, 'mana_blade', 0)
            max_mana = getattr(character, 'max_mana_blade', 100)
            console.print(content_x, content_y + line, " 마검사 - 마력 부여", fg=(150, 100, 255))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1
            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, mana, max_mana, show_numbers=True, custom_color=(150, 100, 255))
            line += 2

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
            # 브레이커 - 연격 기믹 (Combo Gauge)
            combo = getattr(character, 'combo_gauge', 0)
            max_combo = getattr(character, 'max_combo_gauge', 100)
            atk_power = 0
            if hasattr(character, "stat_manager"):
               from src.character.stats import Stats
               atk_power = character.stat_manager.get_value(Stats.STRENGTH)
            else:
               atk_power = getattr(character, "physical_attack", 100)
            
            thresh = int(atk_power * 0.5)

            console.print(content_x, content_y + line, " 브레이커 - 연격 기믹", fg=(255, 100, 50))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 게이지 바 (Custom Color: Red/Orange)
            gauge_bar = self._create_gauge_bar(combo, max_combo, width=10, danger_threshold=None, optimal_min=thresh, optimal_max=max_combo)
            console.print(content_x, content_y + line, f"기믹 게이지: {combo}/{max_combo}", fg=(255, 150, 100))
            line += 1
            console.print(content_x, content_y + line, f"            {gauge_bar}", fg=(255, 150, 100))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            if combo >= thresh:
                console.print(content_x, content_y + line, "⚡ 연격 준비 완료!", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, " SCATTER 시 추가 행동 발동", fg=(255, 200, 100))
            else:
                remaining = thresh - combo
                console.print(content_x, content_y + line, f" 연격 충전 중... ({remaining} 필요)", fg=(150, 150, 150))

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

        elif gimmick_type == "oracle_system":
            # 신관 - 신탁 시스템
            faith = getattr(character, 'faith', 0)
            max_faith = getattr(character, 'max_faith', 100)
            current_oracle = getattr(character, 'current_oracle', None)
            oracle_combo = getattr(character, 'oracle_combo', 0)

            box_height = 20

            console.print(content_x, content_y + line, "✝ 신관 - 신탁 시스템", fg=(255, 220, 150))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 신앙 게이지
            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, faith, max_faith, show_numbers=True, custom_color=(255, 215, 0))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 현재 신탁
            oracle_turn_count = getattr(character, 'oracle_turn_count', 0)
            if current_oracle:
                oracle_name = current_oracle.get('name', '???')
                oracle_condition = current_oracle.get('condition', '???')
                console.print(content_x, content_y + line, f"현재 신탁: {oracle_name} [{oracle_turn_count}/4턴]", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, f"조건: {oracle_condition}", fg=(200, 200, 200))
                line += 1
            else:
                console.print(content_x, content_y + line, f"현재 신탁: 없음 [{oracle_turn_count}/4턴]", fg=(150, 150, 150))
                line += 1

            console.print(content_x, content_y + line, f"연속 충족: {oracle_combo}회", fg=(200, 255, 200))
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 연속 충족 보너스
            if oracle_combo >= 5:
                console.print(content_x, content_y + line, "⚡ 기적의 은총 활성!", fg=(255, 215, 0))
            elif oracle_combo >= 4:
                console.print(content_x, content_y + line, "  4연속: 신앙 +30 추가", fg=(255, 255, 100))
            elif oracle_combo >= 3:
                console.print(content_x, content_y + line, "  3연속: 모든 효과 +20%", fg=(200, 255, 200))
            elif oracle_combo >= 2:
                console.print(content_x, content_y + line, "  2연속: 보상 +10", fg=(200, 220, 255))
            else:
                console.print(content_x, content_y + line, "  신탁 충족 필요", fg=(150, 150, 150))

        elif gimmick_type == "crowd_cheer":
            # 검투사 - 관중 요구
            cheer = getattr(character, 'cheer', 0)
            max_cheer = getattr(character, 'max_cheer', 100)
            current_demand = getattr(character, 'current_demand', None)
            demand_progress = getattr(character, 'demand_progress', 0)
            consecutive_boos = getattr(character, 'consecutive_boos', 0)

            box_height = 22

            console.print(content_x, content_y + line, "⚔ 검투사 - 콜로세움의 영광", fg=(255, 100, 100))
            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 환호 게이지
            if cheer >= 100:
                cheer_color = (255, 215, 0)
                cheer_tier = "전설"
            elif cheer >= 80:
                cheer_color = (255, 100, 255)
                cheer_tier = "챔피언"
            elif cheer >= 60:
                cheer_color = (255, 150, 100)
                cheer_tier = "인기검투사"
            elif cheer >= 30:
                cheer_color = (200, 255, 200)
                cheer_tier = "신인"
            else:
                cheer_color = (150, 150, 150)
                cheer_tier = "무명"

            gauge_renderer.render_bar(console, content_x, content_y + line, box_width - 6, cheer, max_cheer, show_numbers=True, custom_color=cheer_color)
            line += 1
            console.print(content_x, content_y + line, f"단계: {cheer_tier}", fg=cheer_color)
            line += 2

            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 현재 관중 요구
            if current_demand:
                demand_name = current_demand.get('name', '???')
                console.print(content_x, content_y + line, f"관중 요구: {demand_name}", fg=(255, 255, 100))
                line += 1
                console.print(content_x, content_y + line, f"진행도: {demand_progress}", fg=(200, 200, 200))
                line += 1
            else:
                console.print(content_x, content_y + line, "관중 요구: 없음", fg=(150, 150, 150))
                line += 1

            if consecutive_boos > 0:
                console.print(content_x, content_y + line, f"연속 야유: {consecutive_boos}회", fg=(255, 100, 100))
                line += 1

            line += 1
            console.print(box_x, box_y + line, "├" + "─" * (box_width - 2) + "┤", fg=(200, 200, 255))
            line += 1

            # 단계별 효과
            if cheer >= 100:
                console.print(content_x, content_y + line, "⚡ 그랜드 피날레 가능!", fg=(255, 215, 0))
            elif cheer >= 80:
                console.print(content_x, content_y + line, "  공격 +50%, 크리 +25%", fg=(255, 150, 255))
                line += 1
                console.print(content_x, content_y + line, "  반격률 +30%, 회피 +15%", fg=(255, 150, 255))
            elif cheer >= 60:
                console.print(content_x, content_y + line, "  공격 +30%, 크리 +15%", fg=(255, 200, 150))
                line += 1
                console.print(content_x, content_y + line, "  반격률 +20%", fg=(255, 200, 150))
            elif cheer >= 30:
                console.print(content_x, content_y + line, "  공격 +15%, 속도 +10%", fg=(200, 255, 200))
            else:
                console.print(content_x, content_y + line, "  환호 축적 필요", fg=(150, 150, 150))

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

        # 실제 사용된 높이에 맞춰 테두리와 안내 문구를 렌더링
        final_height = max(box_height, line + 3)
        final_height = min(final_height, self.screen_height - box_y - 1)  # 화면 범위 초과 방지

        # 박스 영역 배경(블랙) 적용 - 글자는 유지, 배경만 덮기
        try:
            bg_slice = console.rgb["bg"]
            bg_slice[box_y:box_y + final_height, box_x:box_x + box_width] = (0, 0, 0)
        except Exception:
            pass

        try:
            # 박스 테두리
            console.print(box_x, box_y, "┌" + "─" * (box_width - 2) + "┐", fg=(200, 200, 200), bg=(0, 0, 0))
            for i in range(1, final_height - 1):
                console.print(box_x, box_y + i, "│", fg=(120, 120, 120), bg=(0, 0, 0))
                console.print(box_x + box_width - 1, box_y + i, "│", fg=(120, 120, 120), bg=(0, 0, 0))
            console.print(box_x, box_y + final_height - 1, "└" + "─" * (box_width - 2) + "┘", fg=(200, 200, 200), bg=(0, 0, 0))
        except Exception:
            pass

        # 하단 안내
        console.print(content_x, box_y + final_height - 2, "아무 키나 눌러 닫기...", fg=(150, 150, 150))

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

        # === 35개 직업 기믹 시스템 상세 (ISSUE-007: UI 시각화 개선) ===

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

        # 마검사 - 블레이드 서킷 (YAML: blade_circuit)
        elif gimmick_type == "blade_circuit":
            steel = getattr(character, 'steel_line', 0)
            mana = getattr(character, 'mana_line', 0)
            max_steel = getattr(character, 'max_steel_line', 100)
            max_mana = getattr(character, 'max_mana_line', 100)
            sigil = getattr(character, 'resonance_sigil', 0)
            max_sigil = getattr(character, 'max_resonance_sigil', 3)
            details.append("=== 블레이드 서킷 ===")
            steel_bar = self._create_gauge_bar(steel, max_steel, width=10)
            mana_bar = self._create_gauge_bar(mana, max_mana, width=10)
            details.append(f"스틸 라인 : {steel_bar} ({steel})")
            details.append(f"마나 라인  : {mana_bar} ({mana})")
            details.append(f"공명 시그넷: {sigil}")
            if steel > 0 or mana > 0:
                details.append(" 채널을 번갈아 사용해 Arc Spark/시그넷 축적")
            else:
                details.append(" 물리→마법→물리 순환으로 시그넷 생성")
        elif gimmick_type == "enchant_system":
            mana = getattr(character, 'mana_blade', 0)
            max_mana = getattr(character, 'max_mana_blade', 100)
            details.append("=== 마나 블레이드 시스템 ===")
            mana_bar = self._create_gauge_bar(mana, max_mana, width=10)
            details.append(f"마나 블레이드: {mana_bar} ({mana}/{max_mana})")
            if mana >= max_mana:
                details.append(" 마나 MAX - 다음 스킬 무료 + 2배!")
            else:
                details.append(" 원소 공격으로 마나 축적")

        # 무당 - 저주 축적 시스템 (YAML: curse_system, 하위 호환: totem_system)
        elif gimmick_type == "curse_system" or gimmick_type == "totem_system":
            curses = getattr(character, 'curse_stacks', 0)
            max_curses = getattr(character, 'max_curse_stacks', 10)
            details.append("=== 저주 축적 시스템 ===")
            curse_bar = self._create_gauge_bar(curses, max_curses, width=10, optimal_min=5, optimal_max=max_curses)
            details.append(f"저주 스택: {curse_bar} ({curses}/{max_curses})")
            details.append(f" 저주 비례 피해: +{curses * 8}%")
            if curses >= 5:
                details.append(" 저주 5+ - 피해 +60%, 디버프 면역")
            if curses >= max_curses:
                details.append(" 저주 MAX - 저주 폭발 자동 발동!")

        # 바드 - 악보 작곡 시스템 (YAML: score_composition)
        elif gimmick_type == "score_composition":
            notes = getattr(character, 'music_notes', [])
            max_notes = getattr(character, 'max_notes', 5)
            harmony = getattr(character, 'harmony_bonus', 1.0)
            details.append("=== 악보 작곡 시스템 ===")
            notes_bar = self._create_gauge_bar(len(notes), max_notes, width=10)
            details.append(f"음표: {notes_bar} ({len(notes)}/{max_notes})")
            if harmony > 1.0:
                details.append(f" 화음 보너스: x{harmony:.1f}")
            if len(notes) >= 3:
                details.append(" 음표 3+ - 피해 +25%")
            if len(notes) >= max_notes:
                details.append(" 악보 완성 - 앙코르 가능!")
            details.append(" 스킬로 음표를 쌓아 악보 완성")

        # 바드 - 선율 시스템 (구버전 호환, YAML: melody_system)
        elif gimmick_type == "melody_system":
            melody = getattr(character, 'active_melody', None)
            notes = getattr(character, 'melody_notes', 0)
            max_notes = getattr(character, 'max_melody_notes', 8)
            details.append("=== 선율 시스템 ===")
            gauge_bar = self._create_gauge_bar(notes, max_notes, width=10)
            details.append(f"음표: {gauge_bar}")
            if melody:
                details.append(f" 연주 중: {melody}")
            details.append(" 적 처치 시 보물 획득")
        
        # 정령술사 - 4대 정령 소환 시스템 (YAML: elemental_spirits)
        elif gimmick_type == "elemental_spirits":
            fire = getattr(character, 'spirit_fire', 0)
            water = getattr(character, 'spirit_water', 0)
            wind = getattr(character, 'spirit_wind', 0)
            earth = getattr(character, 'spirit_earth', 0)
            max_spirits = getattr(character, 'max_spirits', 2)
            active = sum([1 for s in [fire, water, wind, earth] if s > 0])
            details.append("=== 4대 정령 소환 시스템 ===")
            spirit_bar = self._create_gauge_bar(active, max_spirits, width=10)
            details.append(f"활성 정령: {spirit_bar} ({active}/{max_spirits})")
            details.append(f" 화염: {'소환됨' if fire else '대기'} - 공격력 +20%")
            details.append(f" 물: {'소환됨' if water else '대기'} - MP 회복, 힐 +30%")
            details.append(f" 바람: {'소환됨' if wind else '대기'} - 속도 +30%")
            details.append(f" 대지: {'소환됨' if earth else '대기'} - 방어력 +30%")
            if active >= 2:
                details.append(" 정령 2마리 - 융합 스킬 해금!")
        
        # 마술사 - 트릭 덱 시스템 (YAML: trick_deck)
        elif gimmick_type == "trick_deck":
            hand = getattr(character, 'card_hand', [])
            deck = getattr(character, 'card_deck', [])
            discard = getattr(character, 'card_discard', [])
            max_hand = getattr(character, 'max_hand_size', 8)
            details.append("=== 트릭 덱 시스템 ===")
            hand_bar = self._create_gauge_bar(len(hand), max_hand, width=10)
            details.append(f"손패: {hand_bar} ({len(hand)}/{max_hand})")
            details.append(f" 덱: {len(deck)}장 | 버린패: {len(discard)}장")
            
            # 현재 손패 표시
            if hand:
                suit_symbols = {"spade": "♠", "heart": "♥", "diamond": "◆", "club": "♣", "joker": "★"}
                hand_str = " ".join([f"{suit_symbols.get(c.get('suit', '?'), '?')}{c.get('rank', '?')}" for c in hand[:6]])
                details.append(f" 현재 패: {hand_str}")
            
            # 현재 조합 체크
            try:
                from src.character.gimmick_updater import GimmickUpdater
                combo_type, combo_cards, bonus = GimmickUpdater.get_trick_deck_combination(character)
                if combo_type:
                    combo_names = {"pair": "원페어", "two_pair": "투페어", "triple": "트리플", 
                                  "straight": "스트레이트", "flush": "플러시", "full_house": "풀하우스",
                                  "four_of_kind": "포카드", "straight_flush": "스트레이트 플러시"}
                    details.append(f" 현재 조합: {combo_names.get(combo_type, combo_type)}")
                    details.append(f" 조합 보너스: +{int(bonus * 100)}%")
                else:
                    details.append(" 현재 조합: 없음")
            except:
                details.append(" 조합 정보 로드 실패")
            
            details.append(" 카드 드로우로 조합 완성!")

        # 브레이커 - 파괴력 축적 시스템 (YAML: break_system)
        elif gimmick_type == "break_system":
            break_power = getattr(character, 'break_power', 0)
            max_break = getattr(character, 'max_break_power', 10)
            details.append("=== 파괴력 축적 시스템 ===")
            gauge_bar = self._create_gauge_bar(break_power, max_break, width=10, optimal_min=5, optimal_max=max_break)
            details.append(f"파괴력: {gauge_bar} ({break_power}/{max_break})")
            details.append(f" 방어 관통: {min(break_power * 3, 30)}%")
            if break_power >= 5:
                details.append(" 파괴력 공명 - 피해 +50%!")
            if break_power >= max_break:
                details.append(" 파괴력 MAX - 방어 완전 관통!")

        # 사무라이 - 검심 시스템 (YAML: kenshin_system)
        elif gimmick_type == "kenshin_system":
            observation = getattr(character, 'observation', 0)
            kenatsu = getattr(character, 'kenatsu', 0)
            max_observation = getattr(character, 'max_observation', 15)
            max_kenatsu = getattr(character, 'max_kenatsu', 100)

            details.append("=== 검심(剣心) 시스템 ===")

            # 관찰 스택 게이지
            observation_bar = self._create_gauge_bar(observation, max_observation, width=10,
                                                     optimal_min=5, optimal_max=9)
            details.append(f"관찰: {observation_bar} ({observation}/{max_observation})")

            # 관찰 단계 표시
            if observation >= 10:
                details.append("⚔ 검성(剣聖) - 피해 35%↓, BRV 80% 반사")
            elif observation >= 5:
                details.append("⚔ 무심(無心) - 피해 20%↓, BRV 50% 반사")
            else:
                details.append("⚔ 초심(初心) - 피해 10%↓, BRV 30% 반사")

            # 검압 게이지
            kenatsu_bar = self._create_gauge_bar(kenatsu, max_kenatsu, width=10,
                                                optimal_min=60, optimal_max=100)
            details.append(f"검압: {kenatsu_bar} ({kenatsu}/{max_kenatsu})")

            # 사용 가능한 기술 표시
            if kenatsu >= 100:
                details.append("✅ 무료타이가(검압 100) 사용 가능!")
            elif kenatsu >= 60:
                details.append("✅ 텐치쥬잔(검압 60) 사용 가능")
            elif kenatsu >= 50:
                details.append("✅ 켄아츠잔(검압 50) 사용 가능")
            elif kenatsu >= 30:
                details.append("✅ 미키리(검압 30) 사용 가능")

            # 요미 예측 정보 표시 (예측 활성 시에만 표시)
            prediction_active = getattr(character, "prediction_active", False)
            has_prediction = hasattr(character, 'predicted_actions') and bool(character.predicted_actions)
            if prediction_active and has_prediction:
                details.append("")
                details.append("=== 요미 예측 정보 ===")
                for enemy_name, pred_info in character.predicted_actions.items():
                    action_type = pred_info.get('action', '알 수 없음')
                    target = pred_info.get('target', '')
                    details.append(f"{enemy_name}:")
                    details.append(f"  행동: {action_type}")
                    if target:
                        details.append(f"  대상: {target}")
            elif yomi_on and prediction_active and not has_prediction:
                details.append("")
                details.append("=== 요미 예측 정보 ===")
                details.append(" 예측 데이터 없음 (적 정보 또는 컨텍스트 확인 필요)")
            else:
                # 토글 OFF이거나 예측 비활성일 때는 예측 정보 섹션 자체를 숨김
                pass


        # 성직자 - 신성 시스템 (YAML: holy_system)
        elif gimmick_type == "holy_system":
            holy = getattr(character, 'holy_gauge', 0)
            details.append("=== 신성 시스템 ===")
            gauge_bar = self._create_gauge_bar(holy, 100, width=10, optimal_min=80, optimal_max=100)
            details.append(f"신성력: {gauge_bar}")
            if holy >= 80:
                details.append(" 신의 은총 발동 가능")

        # 신관 - 신앙/심판 시스템 (YAML: divinity_system)
        elif gimmick_type == "divinity_system":
            faith = getattr(character, 'faith_points', 0)
            judgment = getattr(character, 'judgment_points', 0)
            max_faith = getattr(character, 'max_faith_points', 100)
            max_judgment = getattr(character, 'max_judgment_points', 100)
            details.append("=== 신앙/심판 시스템 ===")
            faith_bar = self._create_gauge_bar(faith, max_faith, width=10)
            judgment_bar = self._create_gauge_bar(judgment, max_judgment, width=10)
            details.append(f"신앙: {faith_bar} ({faith}/{max_faith})")
            details.append(f"심판: {judgment_bar} ({judgment}/{max_judgment})")
            if faith == judgment and faith > 0:
                details.append(" 균형 달성! 모든 스킬 +40%")
            if faith >= max_faith:
                details.append(" 신앙 MAX - 자동 부활 가능")
            if judgment >= max_judgment:
                details.append(" 심판 MAX - 파티 무적 + 정화")

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

        # 암흑기사 - 충전 시스템 (YAML: charge_system)
        elif gimmick_type == "charge_system":
            charge = getattr(character, 'charge_gauge', 0)
            max_charge = getattr(character, 'max_charge', 100)
            details.append("=== 충전 시스템 ===")
            gauge_bar = self._create_gauge_bar(charge, max_charge, width=10)
            details.append(f"충전량: {gauge_bar}")
            
            # 충전 단계별 정보 표시
            if charge >= 100:
                details.append(" 완전충전: 물공 +60%, 치명타 확정")
            elif charge >= 75:
                details.append(" 결정타: 물공 +35%, 치명타율 +20%")
            elif charge >= 50:
                details.append(" 강화: 물공 +20%, 치명타율 +10%")
            elif charge >= 25:
                details.append(" 집중: 물공 +10%, 치명타율 +5%")
            else:
                details.append(" 준비: 효과 없음")

        # 연금술사 - 포션 조합 시스템 (YAML: alchemy_system)
        elif gimmick_type == "alchemy_system":
            stock = getattr(character, 'potion_stock', 0)
            max_stock = getattr(character, 'max_potion_stock', 10)
            details.append("=== 포션 조합 시스템 ===")
            stock_bar = self._create_gauge_bar(stock, max_stock, width=10)
            details.append(f"재료 보유량: {stock_bar} ({stock}/{max_stock})")
            details.append(" 재료 조합으로 다양한 포션 제작")
            if stock >= 5:
                details.append(" 고급 포션 제작 가능!")
            if stock >= max_stock:
                details.append(" 재료 MAX - 철학자의 돌 가능!")

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

        # 기계공학자 - 열 관리 + 포탑 시스템 (YAML: heat_management)
        elif gimmick_type == "heat_management":
            heat = getattr(character, 'heat', 0)
            max_heat = getattr(character, 'max_heat', 100)
            turrets = getattr(character, 'turret_count', 0)
            fire_turrets = getattr(character, 'fire_turret_count', 0)
            ice_turrets = getattr(character, 'ice_turret_count', 0)
            thunder_turrets = getattr(character, 'thunder_turret_count', 0)
            explosive_turrets = getattr(character, 'explosive_turret_count', 0)
            heal_turrets = getattr(character, 'heal_turret_count', 0)
            
            details.append("=== 열 관리 & 포탑 시스템 ===")
            heat_bar = self._create_gauge_bar(heat, max_heat, width=10, optimal_min=50, optimal_max=79, danger_threshold=80)
            details.append(f"열: {heat_bar} ({heat}/{max_heat})")
            details.append(f"총 포탑: {turrets}개")
            if fire_turrets > 0:
                details.append(f"  화염: {fire_turrets}개")
            if ice_turrets > 0:
                details.append(f"  빙결: {ice_turrets}개")
            if thunder_turrets > 0:
                details.append(f"  전기: {thunder_turrets}개")
            if explosive_turrets > 0:
                details.append(f"  폭발: {explosive_turrets}개")
            if heal_turrets > 0:
                details.append(f"  치유: {heal_turrets}개")
            net_heat = -5 + turrets * 2
            details.append(f"턴당 열 {net_heat:+d} (-5 + 포탑당 +2)")
            if heat >= 80:
                details.append(" [위험] 오버히트 주의!")
            elif heat >= 50:
                details.append(" [최적] 포탑 피해 +30%")

        else:
            return "기믹 상세 정보 없음"

        return "\n".join(details)

        return ""

    def _render_item_menu(self, console: tcod.console.Console):
        """아이템 메뉴 렌더링"""
        if self.item_menu:
            self.item_menu.render(console)

    def _render_possibility_select(self, console: tcod.console.Console):
        """가능성 선택 UI 렌더링 (시간술사)"""
        if not self.possibility_slots:
            return
        
        # 박스 크기/위치
        width = 36
        height = min(len(self.possibility_slots) + 5, 12)
        x = (console.width - width) // 2
        y = (console.height - height) // 2
        
        # 배경 박스
        draw_styled_box(console, x, y, width, height, title="가능성 선택",
                          fg=(255, 255, 255), bg=(20, 20, 50))
        
        # 설명
        action_desc = {
            "summon_single": "발동할 가능성 선택",
            "summon_dual": f"2개 선택 ({len(self.possibility_selected)}/2)",
            "overwrite_slot": "덮어쓸 슬롯 선택"
        }
        desc = action_desc.get(self.possibility_action, "선택")
        console.print(x + 2, y + 1, desc, fg=(200, 200, 200))
        
        # 슬롯 목록
        for i, slot in enumerate(self.possibility_slots):
            y_pos = y + 3 + i
            
            if i in self.possibility_selected:
                prefix = "◆ "
                fg_color = (100, 255, 100)
            elif i == self.possibility_cursor:
                prefix = "▶ "
                fg_color = (255, 255, 100)
            else:
                prefix = "  "
                fg_color = (200, 200, 200)
            
            skill_name = slot.get('skill_name', '???')
            power = int(slot.get('power_ratio', 0.85) * 100)
            text = f"{prefix}{i+1}. {skill_name} ({power}%)"
            console.print(x + 2, y_pos, text[:width-4], fg=fg_color)
        
        # 하단 안내
        help_y = y + height - 2
        if self.possibility_action == "summon_dual":
            help_text = "Z:선택/해제 X:취소"
        else:
            help_text = "Z:선택 X:취소"
        console.print(x + 2, help_y, help_text, fg=(150, 150, 150))

    def _render_card_select(self, console: tcod.console.Console):
        """카드 선택 UI 렌더링 (마술사)"""
        logger.info(f"[카드선택] _render_card_select 호출, card_hand: {len(self.card_hand) if self.card_hand else 0}장, 내용: {self.card_hand[:2] if self.card_hand else 'empty'}")
        if not self.card_hand:
            logger.warning("[카드선택] card_hand가 비어있어 렌더링 스킵!")
            return
        
        # 박스 크기 계산
        card_width = 6  # 카드 하나의 폭
        spacing = 1     # 카드 간격
        total_cards = len(self.card_hand)
        
        # 최대 표시 가능 카드 수 (화면 폭 기준)
        max_visible_cards = min(total_cards, (self.screen_width - 10) // (card_width + spacing))
        
        # 스크롤 계산 (커서가 보이도록)
        scroll_offset = 0
        if total_cards > max_visible_cards:
            # 커서가 화면 중앙에 오도록 스크롤
            scroll_offset = max(0, min(self.card_cursor - max_visible_cards // 2, 
                                       total_cards - max_visible_cards))
        
        visible_cards = total_cards if total_cards <= max_visible_cards else max_visible_cards
        box_width = (card_width + spacing) * visible_cards + 4
        box_height = 10
        
        # 박스 위치 (화면 중앙 하단)
        box_x = max(1, (self.screen_width - box_width) // 2)
        box_y = self.screen_height - box_height - 2
        
        # 배경 박스
        draw_styled_box(console, box_x, box_y, box_width, box_height,
                          title="카드 선택",
                          fg=(255, 200, 100), bg=(20, 20, 40))
        
        # 안내 텍스트 + 카드 번호
        info_text = f"◀ ▶: 선택  Z: 확정  X: 취소  ({self.card_cursor + 1}/{total_cards})"
        console.print(box_x + 2, box_y + 1, info_text, fg=(180, 180, 180))
        
        # 카드 표시
        suit_symbols = {"spade": "♠", "heart": "♥", "diamond": "◆", "club": "♣", "joker": "★"}
        suit_colors = {
            "spade": (100, 100, 255),   # 파랑
            "heart": (255, 100, 100),   # 빨강
            "diamond": (255, 200, 100), # 노랑
            "club": (100, 255, 100),    # 초록
            "joker": (255, 100, 255)    # 보라
        }
        
        # 스크롤 표시
        if scroll_offset > 0:
            console.print(box_x + 1, box_y + 5, "◀", fg=(255, 255, 100))
        if scroll_offset + visible_cards < total_cards:
            console.print(box_x + box_width - 2, box_y + 5, "▶", fg=(255, 255, 100))
        
        for display_i in range(visible_cards):
            i = display_i + scroll_offset
            if i >= total_cards:
                break
            card = self.card_hand[i]
            card_x = box_x + 2 + display_i * (card_width + spacing)
            card_y = box_y + 3
            
            suit = card.get("suit", "?")
            rank = card.get("rank", "?")
            symbol = suit_symbols.get(suit, "?")
            color = suit_colors.get(suit, (255, 255, 255))
            
            # 선택된 카드 강조
            is_selected = (i == self.card_cursor)
            if is_selected:
                # 선택 표시 (위에 화살표)
                console.print(card_x + 2, card_y - 1, "▼", fg=(255, 255, 100))
                # 선택된 카드는 더 밝게
                color = (min(255, color[0] + 80), min(255, color[1] + 80), min(255, color[2] + 80))
                bg_color = (40, 40, 60)
            else:
                bg_color = (20, 20, 30)
            
            # 카드 박스
            draw_styled_box(console, card_x, card_y, card_width, 5, fg=color, bg=bg_color)
            
            # 카드 내용
            console.print(card_x + 1, card_y + 1, f"{symbol}", fg=color)
            console.print(card_x + 1, card_y + 2, f" {rank}", fg=color)
            console.print(card_x + card_width - 2, card_y + 3, f"{symbol}", fg=color)
        
        # 선택된 카드 효과 설명
        if 0 <= self.card_cursor < len(self.card_hand):
            selected = self.card_hand[self.card_cursor]
            rank = selected.get("rank", "")
            suit = selected.get("suit", "")
            
            # 효과 설명 (예외 처리)
            try:
                from src.character.skills.job_skills.magician_skills import RANK_EFFECTS, SUIT_EFFECTS
                rank_effect = RANK_EFFECTS.get(rank, {})
                suit_effect = SUIT_EFFECTS.get(suit, {})
            except ImportError:
                rank_effect = {}
                suit_effect = {}
            
            desc_y = box_y + box_height - 2
            if rank_effect:
                desc_text = f"숫자: {rank_effect.get('name', '')} - {rank_effect.get('desc', '')[:35]}"
                console.print(box_x + 2, desc_y, desc_text[:box_width - 4], fg=(200, 200, 255))
            if suit_effect:
                desc_text = f"무늬: {suit_effect.get('name', '')} - {suit_effect.get('desc', '')[:35]}"
                console.print(box_x + 2, desc_y + 1, desc_text[:box_width - 4], fg=(200, 255, 200))

    def _render_waiting_remote_action(self, console: tcod.console.Console):
        """원격 플레이어 행동 대기 중 오버레이 렌더링 (비차단, 상단 소형 표시)"""
        # 비차단 방식: _pending_remote_actors의 각 항목을 상단에 소형 표시
        if not self._pending_remote_actors:
            return
        y = 1
        for remote_key, (actor, timeout) in self._pending_remote_actors.items():
            actor_name = getattr(actor, 'name', '???') if actor else '???'
            remaining_sec = max(0, timeout / 60.0)
            msg = f"[{actor_name} 행동 선택 중... {remaining_sec:.0f}s]"
            console.print(1, y, msg, fg=(200, 200, 100))
            y += 1

    def _render_pending_remote_overlay(self, console: tcod.console.Console):
        """전투 화면 위에 원격 대기 상태를 소형 오버레이로 표시"""
        self._render_waiting_remote_action(console)

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

    def _render_teamwork_gauge(self, console: tcod.console.Console):
        """팀워크 게이지 렌더링 (화면 하단 - 행동 메뉴 위)"""
        if not self.combat_manager or not self.combat_manager.party:
            return

        # 게이지 정보 추출
        party = self.combat_manager.party
        teamwork_gauge = getattr(party, 'teamwork_gauge', 0)
        max_teamwork_gauge = getattr(party, 'max_teamwork_gauge', 600)

        # 표시 위치: 화면 하단, 메시지 로그 왼쪽 (y=30 또는 31)
        # 행동 메뉴는 y=33이므로, 그 위에 배치
        gauge_y = 28  # 메시지 로그 상단(y=29) 위에 배치
        gauge_x = 2   # 왼쪽 여백

        # 라벨 출력
        console.print(gauge_x, gauge_y, "TW:", fg=(200, 200, 200))
        
        # 게이지 바 렌더링 (MP/BRV와 동일한 스타일)
        gauge_renderer.render_animated_teamwork_bar(
            console, gauge_x + 4, gauge_y, 15,
            teamwork_gauge, max_teamwork_gauge, "party_teamwork",
            show_numbers=True
        )


def _play_combat_transition(
    console: tcod.console.Console,
    context: tcod.context.Context,
    direction: str = "out",
    duration: float = 0.5,
) -> None:
    """전투 진입/퇴장 트랜지션 효과

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        direction: "out"=화면을 가림, "in"=가림을 해제
        duration: 전환 시간 (초)
    """
    import time as _time
    import random as _rand
    try:
        from src.ui.effects import TransitionMode
        em = getattr(context, 'effect_manager', None)
        if em is None or not hasattr(em, 'trigger_transition'):
            return

        if direction == "out":
            # 전투 진입: SHATTER 효과 + 임팩트 플래시/셰이크
            mode = TransitionMode.SHATTER
            if hasattr(em, 'trigger_flash'):
                em.trigger_flash((255, 255, 255), 0.15, max_alpha=200)
            if hasattr(em, 'trigger_shake'):
                em.trigger_shake(8.0, 0.4)
        else:
            # 전투 퇴장: 기존 FADE/WIPE 랜덤
            modes = [
                TransitionMode.FADE,
                TransitionMode.WIPE_LEFT,
            ]
            mode = _rand.choice(modes)
        em.trigger_transition(mode, duration, direction=direction, color=(0, 0, 0))

        # dt 폭주 방지
        if hasattr(context, '_last_frame_time'):
            context._last_frame_time = _time.time()

        start = _time.time()
        timeout = duration + 0.2
        while em.is_transitioning and (_time.time() - start) < timeout:
            context.present(console)
            try:
                import pygame
                pygame.event.pump()
            except Exception:
                pass
            _time.sleep(0.016)
    except Exception:
        pass


def run_combat(
    console: tcod.console.Console,
    context: tcod.context.Context,
    party: List[Any],
    enemies: List[Any],
    inventory: Optional[Any] = None,
    session: Optional[Any] = None,
    network_manager: Optional[Any] = None,
    combat_position: Optional[Tuple[int, int]] = None,
    dungeon: Optional[Any] = None,  # 던전 맵 (환경 효과용)
    bot_manager: Optional[Any] = None,  # 봇 관리자 (자동 전투용)
    local_player_id: Optional[str] = None,  # 로컬 플레이어 ID (다른 플레이어 컨트롤 방지)
    lily_start_message: Optional[str] = None,  # RPG 모드 전투 시작 릴리 대사
    lily_dialogue: Optional[Any] = None,  # RPG 모드 릴리 대사 매니저
    rpg_chapter: int = 0,
    rpg_affinity: int = 0,
    preemptive_bonus: float = 0.0,  # 선제공격 보너스 (0.0~1.0)
) -> Tuple[CombatState, bool]:
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
        (전투 결과 (승리/패배/도주), 게임오버 여부)
    """
    # 전투 시작 SFX (Battle Swirl)
    play_sfx("combat", "battle_start")

    # ── 전투 진입 트랜지션 (탐험 화면 → 검은 화면) ────────────────────
    _play_combat_transition(console, context, direction="out", duration=0.5)

    # 트랜지션 중 누적된 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    # 적 타입에 따라 BGM 선택
    # 1. 세피로스 확인
    is_sephiroth = any(hasattr(e, 'enemy_id') and e.enemy_id == "sephiroth" for e in enemies)
    # 2. 5층마다 나오는 층 보스 확인
    is_floor_boss = any(hasattr(e, 'is_floor_boss') and e.is_floor_boss for e in enemies)
    # 3. 일반 보스 확인 (enemy_id가 "boss_"로 시작)
    is_boss = any(hasattr(e, 'enemy_id') and e.enemy_id.startswith("boss_") for e in enemies)

    # 디버깅 로그
    logger.info(f"BGM 선택 - 세피로스: {is_sephiroth}, 층보스: {is_floor_boss}, 일반보스: {is_boss}")
    for i, enemy in enumerate(enemies):
        enemy_id = getattr(enemy, 'enemy_id', 'unknown')
        floor_boss_flag = getattr(enemy, 'is_floor_boss', False)
        logger.info(f"적 {i}: {enemy.name} (ID: {enemy_id}, 층보스: {floor_boss_flag})")

    if is_sephiroth or is_floor_boss:
        # 세피로스전 또는 5층 층 보스전: One-Winged Angel 고정
        selected_bgm = "battle_final_boss"
    elif is_boss:
        # 일반 보스전: battle_boss만 재생
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
    from src.combat.combat_manager import set_combat_manager
    combat_manager = CombatManager()
    set_combat_manager(combat_manager)  # 전역 참조 설정
    
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
    
    # 던전 정보 설정 (환경 효과용)
    if dungeon:
        combat_manager.dungeon = dungeon
    
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
            logger.info(f"멀티플레이 전투: ATB 시스템을 MultiplayerATBSystem으로 교체 (게이지 {len(old_gauges)}개 복원)")
        else:
            logger.info("멀티플레이 ATB 시스템 이미 활성화됨")

        # 호스트/클라이언트 모드 설정
        is_host = (network_manager and hasattr(network_manager, 'is_host') and network_manager.is_host)
        if hasattr(combat_manager.atb, 'set_host_mode'):
            combat_manager.atb.set_host_mode(is_host)
            logger.info(f"멀티플레이 ATB 호스트 모드: {is_host}")
    
    # 파티 유효성 검사 - 최소 1명의 살아있는 캐릭터 필요
    logger.info(f"전투 파티 검사 시작: 파티 크기 {len(party) if party else 0}")

    if not party or len(party) == 0:
        logger.warning("전투 시작 실패: 유효한 파티가 없습니다 (빈 리스트)")
        return (CombatState.FLED, False)

    # 살아있는 캐릭터가 있는지 확인
    has_alive_member = False
    alive_members = []
    invalid_members = []

    for i, member in enumerate(party):
        member_name = getattr(member, 'name', f'멤버{i+1}')
        member_type = type(member).__name__

        # 다양한 생존 상태 확인
        is_alive = getattr(member, 'is_alive', None)
        current_hp = getattr(member, 'current_hp', None)
        max_hp = getattr(member, 'max_hp', None)

        # Player 객체인 경우 (싱글플레이어에서 exploration.player)
        if member_type == 'Player':
            logger.info(f"파티 멤버 {i+1}: Player 객체 - {member_name} (위치: {member.x}, {member.y})")
            # Player 객체는 전투에 참여할 수 없으므로 무시
            invalid_members.append(f"{member_name}(Player)")
            continue

        logger.info(f"파티 멤버 {i+1}: {member_name} ({member_type}) - HP: {current_hp}/{max_hp}, is_alive: {is_alive}")

        # 생존 판정
        if is_alive is True:
            has_alive_member = True
            alive_members.append(member_name)
        elif current_hp is not None and current_hp > 0:
            has_alive_member = True
            alive_members.append(member_name)
        elif hasattr(member, 'hp') and getattr(member, 'hp', 0) > 0:
            # 다른 HP 속성명도 확인
            has_alive_member = True
            alive_members.append(member_name)
        else:
            invalid_members.append(member_name)

    logger.info(f"유효한 멤버: {len(alive_members)}명 - {', '.join(alive_members) if alive_members else '없음'}")
    if invalid_members:
        logger.info(f"무효한 멤버: {len(invalid_members)}명 - {', '.join(invalid_members)}")

    if not has_alive_member:
        logger.warning("전투 시작 실패: 파티에 살아있는 유효한 멤버가 없습니다")
        logger.warning("Player 객체가 파티에 포함되어 있다면 Character 객체가 필요합니다")
        return (CombatState.FLED, False)

    combat_manager.start_combat(party, enemies, dungeon=dungeon, combat_position=combat_position, preemptive_bonus=preemptive_bonus)

    # AffinityManager 설정 (연계스킬/체인어빌리티용)
    if not combat_manager.affinity_manager:
        try:
            from src.character.affinity import AffinityManager
            affinity_mgr = AffinityManager()
            # 세이브 데이터에서 호감도 복원 시도
            import src.persistence.save_system as save_module
            saved_affinity = getattr(save_module, '_last_loaded_affinity_data', None)
            if saved_affinity:
                affinity_mgr.from_dict(saved_affinity)
            combat_manager.affinity_manager = affinity_mgr
            logger.info("전투 매니저에 AffinityManager 설정 완료")
        except Exception as e:
            logger.warning(f"AffinityManager 설정 실패: {e}")

    # 인벤토리 설정 (전투 매니저에도 전달)
    if inventory is not None:
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
            local_player_id=local_player_id,  # 로컬 플레이어 ID 전달 (싱글플레이도 전달)
            lily_dialogue=lily_dialogue,
            rpg_chapter=rpg_chapter,
            rpg_affinity=rpg_affinity,
        )

    # 선제공격 발동 시 전투 로그 메시지 표시
    if getattr(combat_manager, 'is_preemptive', False):
        ui.add_message("선제공격! 아군이 먼저 행동합니다!", (255, 255, 100))

    # RPG 모드 전투 시작 릴리 대사 표시
    if lily_start_message:
        ui.add_message(lily_start_message, (255, 200, 255))

    handler = InputHandler()

    # 이펙트 매니저 주입 (PygameContext에서 가져옴)
    if hasattr(context, 'effect_manager'):
        ui.effect_manager = context.effect_manager
    # 셀→콘솔 픽셀 변환 함수 주입 (파티클 위치용)
    if hasattr(context, 'cell_to_console_pixel'):
        ui._cell_to_pixel_fn = context.cell_to_console_pixel

    logger.info(f"전투 시작: 아군 {len(party)}명 vs 적군 {len(enemies)}명 (BGM: {selected_bgm})")

    # 60fps 고정 및 전투 속도 2배 설정
    TARGET_FPS = 60
    FRAME_TIME = 1.0 / TARGET_FPS  # 0.01666... 초
    GAME_SPEED = 2.0  # 전투 속도 2배

    # 전투 루프
    while not ui.battle_ended:
        # 프레임 시작 시간
        import time
        frame_start = time.perf_counter()

        # pygame 이벤트 처리 (게임패드 입력을 위해) - 더 자주 호출
        pygame.event.pump()  # pygame 이벤트 큐 업데이트

        # 마우스 셀 좌표 업데이트 (호버 툴팁용)
        try:
            mx, my = pygame.mouse.get_pos()
            # 윈도우 픽셀 → 콘솔 셀 좌표 변환 (스케일링/레터박싱 보정)
            if hasattr(context, 'pixel_to_cell'):
                cell_x, cell_y = context.pixel_to_cell(mx, my)
            else:
                tile_w = getattr(context, 'tile_width', 10)
                tile_h = getattr(context, 'tile_height', 13)
                cell_x, cell_y = mx // tile_w, my // tile_h
            ui.update_mouse_cell(cell_x, cell_y)
        except Exception:
            pass

        # 업데이트 (게임 속도 2배)
        ui.update(delta_time=GAME_SPEED)

        # RPG 모드 릴리 전투 중 대사 체크
        if ui.lily_dialogue and not ui.battle_ended:
            ui.check_lily_combat_conditions()

        # 렌더링
        ui.render(console)
        context.present(console)

        # 입력 처리
        action = None

        # 게임패드 입력 우선 확인
        action = unified_input_handler.get_action()

        # tcod 이벤트 처리 (키보드/마우스) - 게임패드 입력이 없을 때만
        if not action:
            # tcod 이벤트는 non-blocking으로 변경
            events = tcod.event.get()  # wait 대신 get 사용
            for event in events:
                action = unified_input_handler.process_tcod_event(event)
                if action:
                    break

                # 윈도우 닫기는 무시 (전투 중에는 도주 명령으로만 종료 가능)
                # if isinstance(event, tcod.event.Quit):
                #     return CombatState.FLED

        if action:
            if ui.handle_input(action):
                break

        # 60fps 유지를 위한 프레임 제한
        frame_end = time.perf_counter()
        frame_duration = frame_end - frame_start
        sleep_time = FRAME_TIME - frame_duration

        if sleep_time > 0:
            time.sleep(sleep_time)

    logger.info(f"전투 종료: {ui.battle_result.value if ui.battle_result else 'unknown'}")

    # Combat BGM fade out before field BGM starts
    from src.audio import stop_bgm
    stop_bgm(fade_out=True)

    # ── 전투 퇴장 트랜지션 (전투 화면 → 검은 화면) ────────────────────
    _play_combat_transition(console, context, direction="out", duration=0.4)

    # BGM은 main.py에서 처리 (필드 BGM으로 전환하기 위해)
    # combat_manager의 is_game_over 플래그도 함께 반환
    is_game_over = getattr(combat_manager, 'is_game_over', False)
    return (ui.battle_result or CombatState.FLED, is_game_over)
