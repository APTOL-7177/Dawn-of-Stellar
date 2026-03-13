"""
트레이닝 모드

캐릭터 연습을 위한 허수아비 전투 모드
"""

import tcod
from typing import Any, TYPE_CHECKING, Optional
from src.ui.input_handler import unified_input_handler, GameAction
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType

if TYPE_CHECKING:
    from src.character.character import Character


class TrainingDummy:
    """
    트레이닝 허수아비 - 행동하지 않고 막대한 HP/BRV를 가진 연습용 적
    """

    def __init__(self, level: int):
        """
        Args:
            level: 아군 레벨에 따라 방어력 설정
        """
        self.enemy_id = "training_dummy"
        self.name = "트레이닝 허수아비"
        self.level = level

        # 고정 스탯
        self.max_hp = 1000000
        self._current_hp = 1000000  # 내부 변수로 변경
        self.max_mp = 0
        self.current_mp = 0
        self.max_brv = 1000000  # 무한대 BRV
        self._current_brv = 1000000  # 무한대 초기 BRV

        # 레벨에 따른 방어력 (레벨 * 10)
        self.physical_defense = level * 10
        self.magic_defense = level * 10

        # 기타 스탯 (공격하지 않음)
        self.physical_attack = level * 8
        self.magic_attack = level * 8
        # 속도: 트레이닝용으로 턴이 오지 않도록 낮게 유지
        self.speed = 1
        self.luck = 0
        self.accuracy = 100  # 명중률 확보 (0이면 로그 에러)
        self.evasion = 0

        # 상태
        self.is_alive = True
        self.is_enemy = True

        # ATB
        self.atb_gauge = 0

        # 상태 효과 매니저
        from src.combat.status_effects import StatusManager
        self.status_manager = StatusManager(owner_name=self.name, owner=self)
        self.status_effects = self.status_manager.status_effects  # 하위 호환성

        # 상처 데미지 (BREAK 시스템용)
        self.wound_damage = 0

        # AI 설정 (행동하지 않음)
        self.ai_enabled = False

        # 기본 공격 스킬 (BRV/HP)
        self.skills = self._build_skills()

        # 피해량 통계
        self.total_brv_damage = 0
        self.total_hp_damage = 0
        self.turn_count = 0

    @property
    def current_hp(self) -> int:
        """현재 HP getter"""
        return self._current_hp

    @current_hp.setter
    def current_hp(self, value: int):
        """현재 HP setter"""
        self._current_hp = max(0, min(value, self.max_hp))

        # 사망 체크
        if self._current_hp <= 0:
            self.is_alive = False

    @property
    def current_brv(self) -> int:
        """현재 BRV getter"""
        return self._current_brv

    @current_brv.setter
    def current_brv(self, value: int):
        """현재 BRV setter"""
        self._current_brv = max(0, min(value, self.max_brv))

    def take_damage(self, damage: int, damage_type: str = None, is_dot: bool = False, **kwargs) -> int:
        """
        HP 데미지를 받습니다 (HP 공격용)

        Args:
            damage: 데미지량
            damage_type: "hp" 또는 "brv" 힌트
            is_dot: 지속피해 여부

        Returns:
            실제 받은 데미지
        """
        actual_damage = 0
        # BRV 피해 처리 (필요 시)
        if damage_type and "brv" in str(damage_type).lower():
            old_brv = self.current_brv
            self.current_brv = max(0, self.current_brv - damage)
            actual_damage = old_brv - self.current_brv
        else:
            # HP 데미지 처리
            old_hp = self.current_hp
            self.current_hp = max(0, self.current_hp - damage)
            actual_damage = old_hp - self.current_hp

            # HP 감소량 기록
            if actual_damage > 0:
                self.total_hp_damage += actual_damage
                
                # 수면 상태에서 데미지를 받으면 깨어남
                if hasattr(self, 'status_manager') and self.status_manager:
                    from src.combat.status_effects import StatusType
                    if self.status_manager.has_status(StatusType.SLEEP):
                        self.status_manager.remove_status(StatusType.SLEEP)
                        print(f"{self.name}이(가) 데미지를 받아 수면 상태에서 깨어났습니다!")

        return actual_damage

    def increment_turn(self):
        """턴 카운트 증가"""
        self.turn_count += 1

    def get_statistics(self) -> dict:
        """피해량 통계 반환"""
        avg_hp = self.total_hp_damage / self.turn_count if self.turn_count > 0 else 0

        return {
            "total_hp_damage": self.total_hp_damage,
            "turn_count": self.turn_count,
            "avg_hp_per_turn": avg_hp
        }

    def heal(self, amount: int) -> int:
        """
        회복 (필요 없음, 구현만)

        Args:
            amount: 회복량

        Returns:
            실제 회복량
        """
        return 0

    def _build_skills(self):
        """허수아비 기본 BRV/HP 공격 스킬"""
        brv = Skill("training_dummy_brv", "허수아비 브레이크", "기본 BRV 공격")
        brv.effects = [DamageEffect(DamageType.BRV, 1.0, stat_type="physical")]
        brv.metadata = {"basic_attack": True}

        hp = Skill("training_dummy_hp", "허수아비 타격", "기본 HP 공격")
        hp.effects = [DamageEffect(DamageType.HP, 1.0, stat_type="magical")]
        hp.metadata = {"basic_attack": True}

        return [brv, hp]

    def update_atb(self, delta: float) -> None:
        """
        ATB 업데이트 (거의 증가하지 않음)

        Args:
            delta: 시간 델타
        """
        # 매우 느리게 증가 (사실상 행동 안 함)
        self.atb_gauge += delta * 0.01


def run_training_mode(
    console: tcod.console.Console,
    context: Any,
    logger: Any,
    selected_job: Optional[str] = None,
    selected_level: int = 1,
    variant: Optional[str] = None,
) -> str:
    """
    트레이닝 모드 실행

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        logger: 로거
        selected_job: 선택한 직업 (None이면 선택 UI 표시)
        selected_level: 선택한 레벨

    Returns:
        결과 문자열
    """
    from src.character.character import Character
    from src.character.party import Party
    from src.combat.combat_manager import CombatManager, CombatState
    from src.ui.combat_ui import CombatUI

    logger.info(f"트레이닝 모드 시작: 레벨 {selected_level}")

    # === 0. 트레이닝 종류 선택 ===
    if variant is None:
        variant = _select_training_variant(console, context, logger)
        if variant is None:
            return "cancel"

    # === 1. 직업 선택 (선택되지 않았을 경우) ===
    party_jobs: list[str] = []
    if selected_job is None:
        if variant == "party":
            picked_jobs: list[str] = []
            for i in range(4):
                job_pick = _select_job(
                    console,
                    context,
                    logger,
                    title=f"파티 {i+1}번 직업 선택",
                    excluded_jobs=set(picked_jobs)
                )
                if job_pick is None:
                    return "cancel"
                party_jobs.append(job_pick)
                picked_jobs.append(job_pick)
        else:
            selected_job = _select_job(console, context, logger)
            if selected_job is None:
                return "cancel"
            party_jobs.append(selected_job)
    else:
        party_jobs.append(selected_job)

    # === 2. 레벨 선택 (선택되지 않았을 경우 기본값 1) ===
    if selected_level == 1:
        level_input = _input_level(console, context, logger)
        if level_input is None:
            return "cancel"
        selected_level = level_input

    # === 3. 캐릭터 생성 및 레벨 설정 ===
    from src.character.character_loader import get_all_job_names
    job_names = get_all_job_names()

    party_members = []
    for idx, job_id in enumerate(party_jobs):
        display_name = job_names.get(job_id, job_id)
        member = Character(display_name, job_id)
        for _ in range(selected_level - 1):
            member.level_up()
        party_members.append(member)

    logger.info(f"캐릭터 생성: {len(party_members)}명 (Lv.{selected_level})")

    # === 4. 특성 선택 ===
    from src.ui.trait_selection import run_trait_selection

    trait_results = run_trait_selection(console, context, party_members)
    if trait_results is None:
        logger.info("특성 선택 취소됨")
        return "cancel"

    # 특성 적용
    if trait_results and len(trait_results) > 0:
        for member, traits in zip(party_members, trait_results):
            member.selected_traits = traits.selected_traits
            logger.info(f"{member.name} 특성 적용: {len(member.selected_traits)}개")

    # === 5. 패시브 선택 ===
    from src.ui.passive_selection import run_passive_selection

    passive_result = run_passive_selection(console, context)
    if passive_result is None:
        logger.info("패시브 선택 취소됨")
        return "cancel"

    # 패시브 적용
    if passive_result and passive_result.passives:
        selected_passives = passive_result.passives
        for passive in selected_passives:
            for member in party_members:
                member.activate_trait(passive.id)
        logger.info(f"패시브 선택 및 적용: {len(selected_passives)}개")
    else:
        selected_passives = []

    # === 6. 장비 지급 및 회복 ===
    for member in party_members:
        _equip_training_gear(member, selected_level, logger)
        member.current_hp = member.max_hp
        member.current_mp = member.max_mp

    party = Party(party_members)

    # === 7. 허수아비 생성 ===
    dummy_count = 4 if variant == "party" else 1
    enemies = [TrainingDummy(selected_level) for _ in range(dummy_count)]

    logger.info(f"허수아비 생성: {dummy_count}기")

    # === 8. 전투 시작 ===
    from src.combat.combat_manager import set_combat_manager
    combat_manager = CombatManager()
    set_combat_manager(combat_manager)

    screen_width = console.width
    screen_height = console.height

    combat_ui = CombatUI(screen_width, screen_height, combat_manager)

    # 트레이닝 모드임을 CombatUI에 알림
    combat_ui.training_mode = True
    combat_ui.training_dummy = enemies[0] if enemies else None
    combat_ui.training_variant = variant

    combat_manager.party = party

    # 호감도 MAX 설정 (체인어빌리티 테스트용)
    from src.character.affinity import AffinityManager
    affinity_mgr = AffinityManager()
    party_jobs = [m.job_id for m in party_members if hasattr(m, 'job_id')]
    affinity_mgr.add_points_all(party_jobs, 1000)  # 750+ = 영혼의 동반자 (Lv5)
    combat_manager.affinity_manager = affinity_mgr

    combat_manager.start_combat(party_members, enemies)

    # 팀워크 게이지 600 (체인어빌리티 테스트용) — start_combat 이후에 설정해야 덮어써지지 않음
    combat_manager.party.teamwork_gauge = 600

    # 이펙트 매니저 주입 (전투 애니메이션 효과용)
    if hasattr(context, 'effect_manager'):
        combat_ui.effect_manager = context.effect_manager
    # 셀→콘솔 픽셀 변환 함수 주입 (파티클 위치용)
    if hasattr(context, 'cell_to_console_pixel'):
        combat_ui._cell_to_pixel_fn = context.cell_to_console_pixel

    # 트레이닝 허수아비의 ATB를 0으로 리셋 (턴이 안오는 버그 방지)
    for dummy in enemies:
        gauge = combat_manager.atb.get_gauge(dummy)
        if gauge:
            gauge.current = 0
            logger.debug(f"허수아비 ATB 게이지 초기화: {gauge.current}/{gauge.max_gauge}")

    # 패시브 적용
    if selected_passives:
        for passive in selected_passives:
            # 전투 시작 시 패시브 효과 적용
            if hasattr(passive, 'apply_to_character'):
                for member in party_members:
                    passive.apply_to_character(member)
            logger.debug(f"패시브 적용: {passive.name}")

    # === 9. 전투 루프 ===
    from src.ui.input_handler import unified_input_handler
    from src.audio import play_bgm
    import pygame
    import time

    # 트레이닝 BGM 재생
    play_bgm("training")
    logger.info("트레이닝 BGM 재생: Timewalker")

    logger.info("트레이닝 전투 시작!")
    logger.info(f"초기 전투 상태: {combat_manager.state}")

    # 60fps 프레임 제한 설정
    TARGET_FPS = 60
    FRAME_TIME = 1.0 / TARGET_FPS
    GAME_SPEED = 2.0  # 실전과 동일한 전투 속도

    loop_count = 0
    last_frame_time = time.perf_counter()

    while combat_manager.state not in [CombatState.VICTORY, CombatState.DEFEAT, CombatState.FLED]:
        loop_count += 1
        if loop_count % 100 == 0:
            logger.debug(f"전투 루프 {loop_count}회, 상태: {combat_manager.state}")

        frame_start = time.perf_counter()

        # pygame 이벤트 처리
        try:
            pygame.event.pump()
        except:
            pass

        # 마우스 셀 좌표 업데이트 (호버 툴팁용)
        try:
            mx, my = pygame.mouse.get_pos()
            if hasattr(context, 'pixel_to_cell'):
                cell_x, cell_y = context.pixel_to_cell(mx, my)
            else:
                tile_w = getattr(context, 'tile_width', 10)
                tile_h = getattr(context, 'tile_height', 13)
                cell_x, cell_y = mx // tile_w, my // tile_h
            combat_ui.update_mouse_cell(cell_x, cell_y)
        except Exception:
            pass

        # 전투 관리자 업데이트 (ATB 시스템 포함)
        combat_manager.update(delta_time=GAME_SPEED)

        # UI 업데이트
        combat_ui.update(delta_time=GAME_SPEED)

        # 렌더링
        combat_ui.render(console)
        context.present(console)

        # 입력 처리
        action = None

        # 게임패드 입력 확인
        action = unified_input_handler.get_action()

        # tcod 이벤트 처리
        if not action:
            events = tcod.event.get()
            for event in events:
                if isinstance(event, tcod.event.Quit):
                    logger.info("트레이닝 중단 (윈도우 닫기)")
                    return "quit"

                action = unified_input_handler.process_tcod_event(event)
                if action:
                    break

        if action:
            if combat_ui.handle_input(action):
                break

        # 60fps 유지
        frame_end = time.perf_counter()
        frame_duration = frame_end - frame_start
        sleep_time = FRAME_TIME - frame_duration

        if sleep_time > 0:
            time.sleep(sleep_time)

        last_frame_time = time.perf_counter()

    # === 10. 전투 종료 ===
    logger.info(f"트레이닝 종료! 총 루프 횟수: {loop_count}, 최종 상태: {combat_manager.state}")

    # 턴 카운트 설정 (전투 매니저의 턴 카운트 사용)
    if hasattr(combat_manager, 'turn_count'):
        dummy.turn_count = combat_manager.turn_count
    else:
        # 전투 매니저에 턴 카운트가 없으면 적어도 1턴으로 설정
        dummy.turn_count = max(1, dummy.turn_count)

    # === 11. 통계 표시 ===
    if combat_manager.state == CombatState.FLED:
        _show_training_statistics(console, context, dummy, logger)

    return "completed"


def _show_training_statistics(
    console: tcod.console.Console,
    context: Any,
    dummy: TrainingDummy,
    logger: Any
) -> None:
    """
    트레이닝 통계 표시

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        dummy: 허수아비
        logger: 로거
    """
    stats = dummy.get_statistics()

    logger.info(f"트레이닝 통계: HP 총합 {stats['total_hp_damage']}, 턴 {stats['turn_count']}")

    # 이전 화면에서 남은 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    while True:
        console.clear()

        # 타이틀
        title = "=== 트레이닝 결과 ==="
        console.print(
            (console.width - len(title)) // 2,
            console.height // 2 - 8,
            title,
            fg=(255, 255, 0)
        )

        # 통계 표시
        y = console.height // 2 - 4

        # 총 HP 피해량
        total_hp_text = f"총 HP 피해량: {stats['total_hp_damage']:,}"
        console.print(
            (console.width - len(total_hp_text)) // 2,
            y,
            total_hp_text,
            fg=(255, 100, 100)
        )
        y += 3

        # 턴당 평균 HP 피해량
        avg_hp_text = f"턴당 평균 HP 피해량: {stats['avg_hp_per_turn']:,.1f}"
        console.print(
            (console.width - len(avg_hp_text)) // 2,
            y,
            avg_hp_text,
            fg=(255, 150, 150)
        )
        y += 3

        # 총 턴 수
        turn_text = f"총 턴 수: {stats['turn_count']}"
        console.print(
            (console.width - len(turn_text)) // 2,
            y,
            turn_text,
            fg=(200, 200, 200)
        )
        y += 3

        # 안내 메시지
        help_text = "[Enter] 계속"
        console.print(
            (console.width - len(help_text)) // 2,
            console.height // 2 + 10,
            help_text,
            fg=(150, 150, 150)
        )

        context.present(console)

        # 입력 대기
        for event in tcod.event.wait():
            if isinstance(event, tcod.event.KeyDown):
                if event.sym == tcod.event.KeySym.RETURN or event.sym == tcod.event.KeySym.KP_ENTER:
                    return
                elif event.sym == tcod.event.KeySym.ESCAPE:
                    return
            elif isinstance(event, tcod.event.Quit):
                return


def _select_job(
    console: tcod.console.Console,
    context: Any,
    logger: Any,
    title: Optional[str] = None,
    excluded_jobs: Optional[set] = None
) -> Optional[str]:
    """
    직업 선택 UI

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        logger: 로거

    Returns:
        선택한 직업 ID (취소 시 None)
    """
    from src.ui.cursor_menu import CursorMenu, MenuItem
    from src.character.character_loader import get_all_job_names, load_character_data

    # 모든 직업 가져오기
    all_jobs = get_all_job_names()

    # 메뉴 아이템 생성
    menu_items = []
    excluded_jobs = excluded_jobs or set()
    for job_id, display_name in all_jobs.items():
        if job_id in excluded_jobs:
            continue
        job_data = load_character_data(display_name) or {}
        desc = job_data.get("description", "")
        slogan = job_data.get("slogan", "")
        full_desc = f"{desc} {(' - ' + slogan) if slogan else ''}".strip()
        menu_items.append(
            MenuItem(
                text=display_name,
                action=lambda j=job_id: j,
                description=full_desc or f"{display_name} 직업으로 트레이닝"
            )
        )

    # 메뉴 생성
    menu = CursorMenu(
        title=title or "트레이닝할 직업 선택",
        items=menu_items,
        x=console.width // 2 - 20,
        y=console.height // 2 - 15,
        width=40,
        show_description=True
    )

    selected_job = None

    # 이전 화면에서 남은 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    while True:
        console.clear()

        # 타이틀
        title_text = title or "=== 트레이닝 모드 - 직업 선택 ==="
        console.print(
            (console.width - len(title_text)) // 2,
            5,
            title_text,
            fg=(255, 255, 0)
        )

        # 메뉴 렌더링
        menu.render(console)

        context.present(console)

        # 입력 처리 (게임패드 지원 추가)
        import time
        last_gamepad_check = 0
        gamepad_check_interval = 0.016  # 약 60 FPS
        
        while True:
            # 게임패드 입력 체크 (주기적으로)
            current_time = time.time()
            if current_time - last_gamepad_check >= gamepad_check_interval:
                gamepad_action = unified_input_handler.gamepad_handler.get_action()
                if gamepad_action:
                    action = gamepad_action
                else:
                    # 키보드 이벤트 대기 (없으면 None 반환)
                    events = list(tcod.event.get())
                    if events:
                        action = unified_input_handler.process_tcod_event(events[0])
                    else:
                        action = None
                last_gamepad_check = current_time
            else:
                # 키보드 이벤트 대기 (없으면 None 반환)
                events = list(tcod.event.get())
                if events:
                    action = unified_input_handler.process_tcod_event(events[0])
                else:
                    action = None

            if action == GameAction.MOVE_UP:
                menu.move_cursor_up()
            elif action == GameAction.MOVE_DOWN:
                menu.move_cursor_down()
            elif action == GameAction.CONFIRM:
                selected_job = menu.execute_selected()
                if selected_job:
                    logger.info(f"직업 선택: {selected_job}")
                    return selected_job
            elif action == GameAction.ESCAPE or action == GameAction.CANCEL:
                return None
            
            # 화면 다시 그리기
            console.clear()
            title = "=== 트레이닝 모드 - 직업 선택 ==="
            console.print(
                (console.width - len(title)) // 2,
                5,
                title,
                fg=(255, 255, 0)
            )
            menu.render(console)
            context.present(console)
            
            # 짧은 대기로 CPU 사용량 줄이기
            time.sleep(0.001)


def _select_training_variant(console: tcod.console.Console, context: Any, logger: Any) -> Optional[str]:
    """트레이닝 종류 선택 (솔로 / 파티+다중 허수아비)"""
    from src.ui.cursor_menu import CursorMenu, MenuItem
    import tcod.event
    import time

    menu = CursorMenu(
        title="트레이닝 모드 선택",
        items=[
            MenuItem("솔로 트레이닝 (1인 / 허수아비 1)", action=lambda: "solo"),
            MenuItem("파티 트레이닝 (4인 / 허수아비 4)", action=lambda: "party"),
        ],
        x=console.width // 2 - 22,
        y=console.height // 2 - 6,
        width=45,
        show_description=False
    )

    last_gamepad_check = 0
    gamepad_check_interval = 0.016

    # 이전 화면에서 남은 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    while True:
        console.clear()
        menu.render(console)
        context.present(console)

        current_time = time.time()
        if current_time - last_gamepad_check >= gamepad_check_interval:
            gamepad_action = unified_input_handler.gamepad_handler.get_action()
            if gamepad_action == GameAction.ESCAPE:
                return None
            elif gamepad_action == GameAction.MOVE_UP:
                menu.move_cursor_up()
            elif gamepad_action == GameAction.MOVE_DOWN:
                menu.move_cursor_down()
            elif gamepad_action == GameAction.CONFIRM:
                return menu.execute_selected()
            last_gamepad_check = current_time

        for event in tcod.event.get():
            if isinstance(event, tcod.event.KeyDown):
                if event.sym == tcod.event.KeySym.UP:
                    menu.move_cursor_up()
                elif event.sym == tcod.event.KeySym.DOWN:
                    menu.move_cursor_down()
                elif event.sym in (tcod.event.KeySym.RETURN, tcod.event.KeySym.KP_ENTER):
                    return menu.execute_selected()
                elif event.sym == tcod.event.KeySym.ESCAPE:
                    return None
            elif isinstance(event, tcod.event.Quit):
                return None


def _input_level(console: tcod.console.Console, context: Any, logger: Any) -> Optional[int]:
    """
    레벨 입력 UI

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        logger: 로거

    Returns:
        입력한 레벨 (취소 시 None)
    """
    import tcod.event

    level_str = ""

    # 입력 처리 (게임패드 Esc 지원)
    import time
    last_gamepad_check = 0
    gamepad_check_interval = 0.016  # 약 60 FPS

    # 이전 화면에서 남은 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    while True:
        # 게임패드 입력 체크
        current_time = time.time()
        if current_time - last_gamepad_check >= gamepad_check_interval:
            gamepad_action = unified_input_handler.gamepad_handler.get_action()

            if gamepad_action == GameAction.ESCAPE or gamepad_action == GameAction.CANCEL:
                return None
            elif gamepad_action == GameAction.CONFIRM:
                # 확인 (A버튼)
                if level_str:
                    try:
                        level = int(level_str)
                        if 1 <= level <= 30:
                            logger.info(f"레벨 입력: {level}")
                            return level
                        else:
                            logger.warning("레벨은 1-30 사이여야 합니다")
                    except ValueError:
                        logger.warning("올바른 숫자를 입력하세요")
            
            last_gamepad_check = current_time
        
        # 키보드 이벤트 처리
        events = list(tcod.event.get())
        for event in events:
            if isinstance(event, tcod.event.KeyDown):
                if event.sym == tcod.event.KeySym.RETURN or event.sym == tcod.event.KeySym.KP_ENTER:
                    # 확인
                    if level_str:
                        try:
                            level = int(level_str)
                            if 1 <= level <= 30:
                                logger.info(f"레벨 입력: {level}")
                                return level
                            else:
                                logger.warning("레벨은 1-30 사이여야 합니다")
                        except ValueError:
                            logger.warning("올바른 숫자를 입력하세요")

                elif event.sym == tcod.event.KeySym.BACKSPACE:
                    # 지우기
                    if level_str:
                        level_str = level_str[:-1]

                elif event.sym == tcod.event.KeySym.ESCAPE:
                    # 취소
                    return None

                else:
                    # 숫자 입력 (0-9)
                    digit_map = {
                        tcod.event.KeySym.N0: '0', tcod.event.KeySym.N1: '1',
                        tcod.event.KeySym.N2: '2', tcod.event.KeySym.N3: '3',
                        tcod.event.KeySym.N4: '4', tcod.event.KeySym.N5: '5',
                        tcod.event.KeySym.N6: '6', tcod.event.KeySym.N7: '7',
                        tcod.event.KeySym.N8: '8', tcod.event.KeySym.N9: '9',
                        # 키패드 숫자
                        tcod.event.KeySym.KP_0: '0', tcod.event.KeySym.KP_1: '1',
                        tcod.event.KeySym.KP_2: '2', tcod.event.KeySym.KP_3: '3',
                        tcod.event.KeySym.KP_4: '4', tcod.event.KeySym.KP_5: '5',
                        tcod.event.KeySym.KP_6: '6', tcod.event.KeySym.KP_7: '7',
                        tcod.event.KeySym.KP_8: '8', tcod.event.KeySym.KP_9: '9',
                    }
                    if event.sym in digit_map and len(level_str) < 2:
                        level_str += digit_map[event.sym]
            elif isinstance(event, tcod.event.Quit):
                return None
        
        # 화면 다시 그리기
        console.clear()
        title = "=== 트레이닝 모드 - 레벨 입력 ==="
        console.print(
            (console.width - len(title)) // 2,
            console.height // 2 - 5,
            title,
            fg=(255, 255, 0)
        )
        desc = "캐릭터 레벨을 입력하세요 (1-30)"
        console.print(
            (console.width - len(desc)) // 2,
            console.height // 2 - 2,
            desc,
            fg=(200, 200, 200)
        )
        input_text = f"레벨: {level_str}_"
        console.print(
            (console.width - len(input_text)) // 2,
            console.height // 2,
            input_text,
            fg=(255, 255, 255)
        )
        controls = "[Enter] 확인  [Backspace] 지우기  [Esc] 취소"
        console.print(
            (console.width - len(controls)) // 2,
            console.height // 2 + 3,
            controls,
            fg=(150, 150, 150)
        )
        context.present(console)
        
        # 짧은 대기로 CPU 사용량 줄이기
        time.sleep(0.001)


def _equip_training_gear(character: "Character", level: int, logger: Any) -> None:
    """
    캐릭터에게 레벨별 기본 장비 지급

    Args:
        character: 캐릭터
        level: 레벨
        logger: 로거
    """
    from src.equipment.item_system import Equipment, EquipSlot, ItemRarity, ItemType

    # 레벨에 따른 장비 등급 결정
    if level <= 5:
        rarity = ItemRarity.COMMON
        stat_multiplier = 2
    elif level <= 10:
        rarity = ItemRarity.UNCOMMON
        stat_multiplier = 3
    elif level <= 15:
        rarity = ItemRarity.RARE
        stat_multiplier = 4
    elif level <= 20:
        rarity = ItemRarity.EPIC
        stat_multiplier = 5
    else:
        rarity = ItemRarity.LEGENDARY
        stat_multiplier = 6

    # 무기
    weapon = Equipment(
        item_id=f"training_weapon_{level}",
        name=f"{character.name} 훈련용 무기 Lv.{level}",
        description="트레이닝용 무기",
        item_type=ItemType.WEAPON,
        equip_slot=EquipSlot.WEAPON,
        rarity=rarity,
        base_stats={
            "strength": level * stat_multiplier,
            "magic": level * stat_multiplier,
            "speed": level,
            "luck": level // 2
        },
        level_requirement=level,
        sell_price=level * 100
    )
    character.equip_item("weapon", weapon)

    # 방어구
    armor = Equipment(
        item_id=f"training_armor_{level}",
        name=f"{character.name} 훈련용 갑옷 Lv.{level}",
        description="트레이닝용 방어구",
        item_type=ItemType.ARMOR,
        equip_slot=EquipSlot.ARMOR,
        rarity=rarity,
        base_stats={
            "defense": level * stat_multiplier,
            "spirit": level * stat_multiplier,
            "hp": level * (stat_multiplier * 5),
            "mp": level * (stat_multiplier * 2)
        },
        level_requirement=level,
        sell_price=level * 100
    )
    character.equip_item("armor", armor)

    # 장신구
    accessory = Equipment(
        item_id=f"training_accessory_{level}",
        name=f"{character.name} 훈련용 장신구 Lv.{level}",
        description="트레이닝용 장신구",
        item_type=ItemType.ACCESSORY,
        equip_slot=EquipSlot.ACCESSORY,
        rarity=rarity,
        base_stats={
            "strength": level * (stat_multiplier // 2),
            "magic": level * (stat_multiplier // 2),
            "defense": level * (stat_multiplier // 2),
            "spirit": level * (stat_multiplier // 2),
            "speed": level,
            "luck": level
        },
        level_requirement=level,
        sell_price=level * 100
    )
    character.equip_item("accessory", accessory)

    logger.debug(f"{character.name} 장비 완료: 무기+방어구+장신구 (Lv.{level}, {rarity.name})")
