"""
Combat Manager - 전투 관리자

ATB, Brave, Damage 시스템을 통합하여 전투 흐름 제어
"""

from typing import List, Dict, Any, Optional, Callable, Tuple
from enum import Enum

from src.core.config import get_config
from src.core.logger import get_logger
from src.core.event_bus import event_bus, Events
from src.core.vibration_system import vibration_manager, VibrationPattern
from src.combat.atb_system import get_atb_system, ATBSystem
from src.combat.brave_system import get_brave_system, BraveSystem
from src.combat.damage_calculator import get_damage_calculator, DamageCalculator
from src.combat.status_effects import StatusManager, StatusEffect, StatusType
from src.audio import play_sfx
from src.character.gimmick_updater import GimmickUpdater


class CombatState(Enum):
    """전투 상태"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PLAYER_TURN = "player_turn"
    ENEMY_TURN = "enemy_turn"
    VICTORY = "victory"
    DEFEAT = "defeat"
    FLED = "fled"


class ActionType(Enum):
    """행동 타입"""
    BRV_ATTACK = "brv_attack"
    HP_ATTACK = "hp_attack"
    BRV_HP_ATTACK = "brv_hp_attack"
    SKILL = "skill"
    ITEM = "item"
    DEFEND = "defend"
    FLEE = "flee"


class CombatManager:
    """
    전투 관리자

    전투 흐름 제어 및 시스템 통합
    """

    def __init__(self) -> None:
        self.logger = get_logger("combat")
        self.config = get_config()

        # 서브시스템
        self.atb: ATBSystem = get_atb_system()
        self.brave: BraveSystem = get_brave_system()
        self.damage_calc: DamageCalculator = get_damage_calculator()

        # 전투 상태
        self.state: CombatState = CombatState.NOT_STARTED
        self.turn_count = 0
        self.current_actor: Optional[Any] = None

        # 전투원
        self.allies: List[Any] = []
        self.enemies: List[Any] = []

        # 팀워크 게이지 시스템
        self._party: Optional[Any] = None  # Party 인스턴스

        # 원소 장막 (아군 전체 공유 보호막)
        self.party_elemental_shield: Optional[Dict[str, Any]] = None

        # 요리 쿨타임 (전투 턴 기준)
        self.cooking_cooldown_turn: Optional[int] = None  # 요리 사용한 턴
        self.cooking_cooldown_duration: int = 0  # 쿨타임 지속 턴 수

        # 환경 효과를 위한 던전 정보
        self.dungeon: Optional[Any] = None  # DungeonMap
        self.combat_position: Optional[Tuple[int, int]] = None  # 전투 시작 위치 (x, y)

        # 헤드리스 모드 (UI/오디오/진동 비활성화 - RL 학습 환경용)
        self.headless: bool = False

        # 호감도/유대 시스템
        self._affinity_manager: Optional[Any] = None  # AffinityManager
        # 체인어빌리티 대기열 (불릿타임 중 플레이어 선택 대기)
        self.pending_chain_abilities: List[Any] = []
        self.chain_trigger_reason: str = ""  # 트리거 사유

        # 직업 시너지 시스템
        self._synergy_manager: Optional[Any] = None  # SynergyManager

        # 콜백
        self.on_combat_end: Optional[Callable[[CombatState], None]] = None
        self.on_turn_start: Optional[Callable[[Any], None]] = None
        self.on_action_complete: Optional[Callable[[Any, Dict], None]] = None

        # 사망 이벤트 구독
        event_bus.subscribe(Events.CHARACTER_DEATH, self._on_character_death)
        event_bus.subscribe(Events.COMBAT_DAMAGE_TAKEN, self._on_damage_taken)

    def start_combat(self, allies: List[Any], enemies: List[Any], dungeon: Optional[Any] = None, combat_position: Optional[Tuple[int, int]] = None, preemptive_bonus: float = 0.0) -> None:
        """
        전투 시작

        Args:
            allies: 아군 리스트
            enemies: 적군 리스트
            dungeon: 던전 맵 (환경 효과용)
            combat_position: 전투 시작 위치 (x, y)
        """
        self.logger.info("전투 시작!")

        # ATB 초기화 (이전 세션/전투의 데이터 제거)
        self.atb.clear()

        if not self.headless:
            # 전투 시작 진동
            vibration_manager.vibrate(VibrationPattern.COMBAT_START)

        # 전투원 설정 (PartyMember 변환은 아래에서 처리)
        self.enemies = enemies
        self.turn_count = 0
        self.state = CombatState.IN_PROGRESS
        
        # 던전 정보 저장 (환경 효과용)
        self.dungeon = dungeon
        self.combat_position = combat_position
        
        # 적 침투 게이지 초기화 (이전 전투 데이터 제거)
        for enemy in enemies:
            if hasattr(enemy, 'intrusion_gauge'):
                enemy.intrusion_gauge = 0

        # 요리 쿨타임 초기화 (인벤토리에서 쿨타임 정보 가져오기)
        # 전투 시작 시 현재 쿨타임 턴을 설정
        if hasattr(self, 'inventory') and self.inventory is not None:
            if self.inventory.cooking_cooldown_duration > 0:
                self.cooking_cooldown_turn = 0  # 전투 시작 턴
                self.cooking_cooldown_duration = self.inventory.cooking_cooldown_duration
            else:
                self.cooking_cooldown_turn = None
                self.cooking_cooldown_duration = 0
        else:
            self.cooking_cooldown_turn = None
            self.cooking_cooldown_duration = 0

        # PartyMember를 Character로 변환 (unhashable 타입 문제 해결)
        from src.ui.party_setup import PartyMember
        from src.character.character import Character
        converted_allies = []
        for ally in allies:
            if isinstance(ally, PartyMember):
                # PartyMember를 Character로 변환
                char = Character(
                    name=ally.character_name,
                    character_class=ally.job_id,
                    level=getattr(ally, 'level', 1)
                )
                # PartyMember의 속성을 Character에 복사
                if hasattr(ally, 'player_id'):
                    char.player_id = ally.player_id
                if hasattr(ally, 'selected_traits') and ally.selected_traits:
                    for trait_id in ally.selected_traits:
                        char.activate_trait(trait_id)
                # 스탯 복사 (stats가 StatManager인 경우)
                if hasattr(ally, 'stats') and ally.stats:
                    from src.character.stats import Stats
                    # stats가 딕셔너리인 경우 StatManager에 적용
                    if isinstance(ally.stats, dict):
                        for stat_name, value in ally.stats.items():
                            try:
                                # Stats는 클래스이므로 getattr 사용
                                stat_enum = getattr(Stats, stat_name.upper(), None)
                                if stat_enum:
                                    char.stat_manager.set_value(stat_enum, value)
                            except (KeyError, AttributeError):
                                pass
                    elif hasattr(ally.stats, 'get_value'):
                        # StatManager 객체인 경우 복사
                        for stat in Stats:
                            try:
                                value = ally.stats.get_value(stat)
                                char.stat_manager.set_value(stat, value)
                            except:
                                pass
                converted_allies.append(char)
            else:
                converted_allies.append(ally)
        
        self.allies = converted_allies
        
        # 보호 관계 초기화 (이전 전투의 오래된 참조 제거)
        self._clear_protection_relationships(self.allies)
        
        # 배틀메이지 룬 카운터 초기화 (전투 시작 시 0으로 리셋)
        for ally in self.allies:
            if getattr(ally, 'gimmick_type', None) == 'rune_resonance':
                ally.rune_fire = 0
                ally.rune_ice = 0
                ally.rune_lightning = 0
                ally.rune_earth = 0
                ally.rune_arcane = 0
                ally.resonance_gauge = 0
                self.logger.info(f"{ally.name} 룬 시스템 초기화")
        
        # ATB 시스템에 전투원 등록
        import random

        # 선제공격 판정: preemptive_bonus 확률로 선제공격 발동
        is_preemptive = preemptive_bonus > 0 and random.random() < preemptive_bonus
        self.is_preemptive = is_preemptive  # UI 메시지용 플래그
        if is_preemptive:
            self.logger.info(f"선제공격 발동! (보너스: {preemptive_bonus:.0%})")

        for ally in self.allies:
            self.atb.register_combatant(ally)
            self.brave.initialize_brv(ally)
            # combat_manager 참조 설정 (원소 장막 등을 위해)
            ally._combat_manager_ref = self
            gauge = self.atb.get_gauge(ally)
            if gauge:
                if is_preemptive:
                    # 선제공격: 아군 ATB 70~100% 시작
                    random_percentage = random.uniform(0.7, 1.0)
                else:
                    # 일반: 0~50% 랜덤
                    random_percentage = random.uniform(0.0, 0.5)
                gauge.current = int(gauge.max_gauge * random_percentage)

        for enemy in enemies:
            self.atb.register_combatant(enemy)
            self.brave.initialize_brv(enemy)
            gauge = self.atb.get_gauge(enemy)
            if gauge:
                if is_preemptive:
                    # 선제공격: 적 ATB 0~15% 시작 (거의 빈 상태)
                    random_percentage = random.uniform(0.0, 0.15)
                else:
                    # 일반: 0~50% 랜덤
                    random_percentage = random.uniform(0.0, 0.5)
                gauge.current = int(gauge.max_gauge * random_percentage)

        # 해커 특성: 제로데이 헌터 - 전투 시작 시 무작위 적 침투 +30
        try:
            hack_targets = [e for e in enemies if getattr(e, "is_enemy", True)]
            if hack_targets:
                for ally in self.allies:
                    if getattr(ally, "gimmick_type", None) != "intrusion_system":
                        continue
                    active_traits = getattr(ally, "active_traits", []) or []
                    has_zero_day = any(
                        (t if isinstance(t, str) else t.get("id")) == "zero_day_hunter"
                        for t in active_traits
                    )
                    if has_zero_day:
                        target = random.choice(hack_targets)
                        GimmickUpdater.add_intrusion(ally, target, 30)
        except Exception as exc:
            self.logger.warning(f"[해커 특성] 제로데이 헌터 적용 실패: {exc}")

        # 캐스팅 시스템 초기화
        from src.combat.casting_system import get_casting_system
        casting_system = get_casting_system()
        casting_system.clear()

        # 파티 버프 특성 적용 (holy_aura, chivalry 등)
        self._apply_party_wide_traits()

        # 팀워크 게이지 시스템 초기화
        from src.character.party import Party
        self.party = Party(self.allies)

        # 저장된 팀워크 게이지 정보 복원 (게임 로드 시)
        try:
            from src.persistence.save_system import SaveSystem
            save_system = SaveSystem()
            # 최근에 로드된 게임 상태에서 팀워크 게이지 정보 확인
            # (간단하게 모듈 레벨 변수에 저장된 정보를 사용)
            import src.persistence.save_system as save_module
            if hasattr(save_module, '_last_loaded_teamwork_gauge'):
                saved_gauge = getattr(save_module, '_last_loaded_teamwork_gauge', 0)
                saved_max_gauge = getattr(save_module, '_last_loaded_max_teamwork_gauge', 600)
                self.party.teamwork_gauge = saved_gauge
                self.party.max_teamwork_gauge = saved_max_gauge
                self.logger.info(f"팀워크 게이지 복원됨: {saved_gauge}/{saved_max_gauge}")
                # 캐시는 유지 (게임 저장 시 사용)
        except Exception as e:
            self.logger.debug(f"팀워크 게이지 복원 실패 (무시): {e}")

        self.logger.debug(f"팀워크 게이지 시스템 초기화: {self.party.teamwork_gauge}/{self.party.max_teamwork_gauge}")

        # 호감도/유대 시스템 초기화 (체인어빌리티, 연계스킬, 합체기에 필요)
        if not self._affinity_manager:
            try:
                from src.character.affinity import AffinityManager
                self._affinity_manager = AffinityManager()
                party_jobs = [c.character_class for c in self.allies if hasattr(c, 'character_class')]

                # 세이브 파일에서 호감도 복원 시도 (전투 간 영속성)
                loaded_from_save = False
                try:
                    import src.persistence.save_system as save_module
                    cached_affinity = getattr(save_module, '_last_loaded_affinity_data', None)
                    if cached_affinity and isinstance(cached_affinity, dict):
                        self._affinity_manager.from_dict(cached_affinity)
                        loaded_from_save = True
                        self.logger.info(f"호감도 세이브에서 복원 완료")
                except Exception as e:
                    self.logger.debug(f"호감도 세이브 복원 실패 (무시): {e}")

                if not loaded_from_save:
                    # 세이브 데이터 없으면 0에서 시작
                    # → 연계스킬/합체기는 전투 중 호감도 축적으로 해금
                    self.logger.info(f"호감도 시스템 초기화 (0 시작): {len(party_jobs)}명 파티")
            except Exception as e:
                self.logger.debug(f"호감도 시스템 초기화 실패 (무시): {e}")

        # 직업 시너지: 파티 보너스 계산
        try:
            from src.combat.job_synergy import get_synergy_manager
            self._synergy_manager = get_synergy_manager()
            party_jobs = [c.character_class for c in self.allies if hasattr(c, 'character_class')]
            active_bonuses = self._synergy_manager.calculate_party_bonuses(party_jobs)
            if active_bonuses:
                bonus_names = [b.name for b in active_bonuses]
                self.logger.info(f"파티 시너지 보너스 활성: {', '.join(bonus_names)}")
        except Exception as e:
            self.logger.debug(f"시너지 시스템 초기화 실패 (무시): {e}")

        # === 보스 타이머 시스템 ===
        # 세피로스 또는 카인 전투인지 확인
        enemy_ids = [getattr(e, 'enemy_id', None) for e in self.enemies]
        self.logger.debug(f"[전투 시작] 적 enemy_id 목록: {enemy_ids}")
        
        is_sephiroth_battle = any(
            getattr(enemy, 'enemy_id', None) == "sephiroth" for enemy in self.enemies
        )
        is_cain_battle = any(
            getattr(enemy, 'enemy_id', None) == "abel_cain" for enemy in self.enemies
        )
        self.logger.debug(f"[전투 시작] 세피로스 전투: {is_sephiroth_battle}, 카인 전투: {is_cain_battle}")

        if (is_sephiroth_battle or is_cain_battle) and not self.headless:
            from src.combat.boss_timer_system import get_boss_timer_system
            boss_timer = get_boss_timer_system()

            if is_cain_battle:
                # 카인: 4분 4초 타이머
                boss_timer.start_timer(
                    time_limit=244.0,  # 4분 4초
                    on_timeout=self._on_boss_timeout
                )
                boss_timer.on_warning = self._on_timer_warning
                self.logger.info("카인 전투 타이머 시작: 4분 4초")
            else:
                # 세피로스: 7분 30초 타이머
                boss_timer.start_timer(
                    time_limit=450.0,  # 7분 30초
                    on_timeout=self._on_boss_timeout
                )
                boss_timer.on_warning = self._on_timer_warning
                self.logger.info("세피로스 전투 타이머 시작: 7분 30초")

            # === 보스 BGM 재생 ===
            from src.audio import play_bgm
            if is_cain_battle:
                play_bgm("battle_cain", loop=False, fade_in=False)
                self.logger.info("카인 테마곡 재생: 시간의_왕좌.wav (4분 4초)")
            elif is_sephiroth_battle:
                play_bgm("battle_sephiroth", loop=False, fade_in=False)
                self.logger.info("세피로스 테마곡 재생: 광기의_춤.wav (7분 30초)")

        # === 보스 전투 시작 대사 ===
        if (is_sephiroth_battle or is_cain_battle) and not self.headless:
            from src.combat.boss_dialogue import get_boss_dialogue
            boss_dialogue = get_boss_dialogue()

            for enemy in self.enemies:
                boss_id = getattr(enemy, 'enemy_id', None)
                if boss_id in ['sephiroth', 'abel_cain']:
                    # 페이즈 추적을 위한 속성 초기화
                    enemy._current_phase = 1
                    enemy._low_hp_dialogue_shown = False

                    dialogue = boss_dialogue.get_dialogue(boss_id, "combat_start")
                    if dialogue:
                        boss_dialogue.print_dialogue(self.logger, dialogue, combat_ui=getattr(self, 'combat_ui', None))

        # === 보스 기믹 시스템 초기화 ===
        if is_sephiroth_battle or is_cain_battle:
            from src.combat.boss_gimmicks import reset_boss_gimmicks, get_boss_gimmick_system
            reset_boss_gimmicks()
            self.boss_gimmick_system = get_boss_gimmick_system()
            # 기존 표식 모두 제거 (이전 전투 잔여물)
            for ally in self.allies:
                if hasattr(ally, '_sephiroth_mark'):
                    delattr(ally, '_sephiroth_mark')
                if hasattr(ally, '_cain_mark'):
                    delattr(ally, '_cain_mark')
            self.logger.debug("[보스 기믹] 시스템 초기화 완료")

        # === 카인 시간의 심판 (전투 시작) ===
        if is_cain_battle:
            cain = next((e for e in self.enemies if getattr(e, 'enemy_id', None) == "abel_cain"), None)
            if cain:
                # 시간의 심판 첫 발동 (전투 시작)
                self._try_cain_judgment(cain, {"turn_count": 0})
        
        # === 세피로스 표식 (전투 시작 시 첫 부여) ===
        if is_sephiroth_battle:
            sephiroth = next((e for e in self.enemies if getattr(e, 'enemy_id', None) == "sephiroth"), None)
            self.logger.debug(f"[세피로스 전투] sephiroth 찾음: {sephiroth is not None}")
            if sephiroth:
                mark_result = self.boss_gimmick_system.update_sephiroth_mark(sephiroth, self.allies)
                self.logger.debug(f"[세피로스 표식] 초기 부여 결과: {mark_result}")
                if mark_result:
                    self.logger.info(f"\033[95m{mark_result['message']}\033[0m")
                    marked = self.boss_gimmick_system.sephiroth_marked_target
                    self.logger.debug(f"[세피로스 표식] 표식 대상: {marked.name if marked else 'None'}")
                    self.logger.debug(f"[세피로스 표식] _sephiroth_mark 속성: {hasattr(marked, '_sephiroth_mark') if marked else False}")

        # 이벤트 발행
        event_bus.publish(Events.COMBAT_START, {
            "allies": [a.id for a in allies if hasattr(a, 'id')],
            "enemies": [e.id for e in enemies if hasattr(e, 'id')],
            "turn_count": self.turn_count,
            "combat_manager": self,  # 멀티플레이 합류 시스템용
            "combat_id": getattr(self, 'combat_id', None),  # 전투 ID
            "position": getattr(self, 'combat_position', None)  # 전투 위치
        })

        self.logger.debug(
            f"전투 참여자: 아군 {len(allies)}명, 적군 {len(enemies)}명"
        )

    def update(self, delta_time: float = 1.0) -> None:
        """
        전투 업데이트 (매 프레임 호출)

        Args:
            delta_time: 경과 시간
        """
        if self.state not in [CombatState.IN_PROGRESS, CombatState.PLAYER_TURN, CombatState.ENEMY_TURN]:
            return

        # ATB 시스템 업데이트
        is_player_turn = self.state == CombatState.PLAYER_TURN
        self.atb.update(delta_time, is_player_turn)

        # 완료된 캐스팅 처리
        self._process_completed_casts()

        # 보스 타이머 체크
        from src.combat.boss_timer_system import get_boss_timer_system
        boss_timer = get_boss_timer_system()
        if boss_timer.is_active:
            boss_timer.check_timeout()

        # 승리/패배 판정
        self._check_battle_end()

    def execute_action(
        self,
        actor: Any,
        action_type: ActionType,
        target: Optional[Any] = None,
        skill: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        행동 실행

        Args:
            actor: 행동자
            action_type: 행동 타입
            target: 대상
            skill: 스킬 (있는 경우)
            **kwargs: 추가 옵션

        Returns:
            행동 결과
        """
        # 전투 종료 상태 체크 - 이미 종료된 전투에서는 행동 불가
        if self.state in [CombatState.VICTORY, CombatState.DEFEAT, CombatState.FLED]:
            self.logger.debug(f"전투 이미 종료됨 ({self.state.value}) - 행동 무시")
            return {
                "action": "skip",
                "error": "combat_ended",
                "message": "전투가 이미 종료되었습니다."
            }
        
        # 죽은 캐릭터는 행동 불가 (is_alive와 current_hp 둘 다 확인, 단 불멸의 존재는 예외)
        is_dead = not getattr(actor, 'is_alive', True)
        if not is_dead and hasattr(actor, 'current_hp') and actor.current_hp <= 0:
            # 불멸의 존재 특성이 있으면 예외 처리
            if hasattr(actor, '_has_undying_existence') and actor._has_undying_existence():
                is_dead = False
            else:
                is_dead = True
                
        if is_dead:
            # is_alive 동기화
            actor.is_alive = False
            self.logger.warning(f"{getattr(actor, 'name', 'Unknown')}은(는) 죽어서 행동할 수 없습니다.")
            # 전투 종료 체크
            self._check_battle_end()
            return {
                "action": "error",
                "error": "actor_is_dead",
                "message": "죽은 캐릭터는 행동할 수 없습니다."
            }
        
        # === 카인 시간의 역설 체크 (낙인 대상 행동 시) ===
        if hasattr(self, 'boss_gimmick_system') and actor in self.allies:
            paradox = self.boss_gimmick_system.check_cain_paradox(actor)
            if paradox:
                self.logger.info(f"━━━━━━ 시간의 역설 ━━━━━━")
                self.logger.info(f"\033[96m{paradox['message']}\033[0m")
                self.logger.info(f"[시간의 역설] {paradox['glitched_name']}에게 {paradox['damage']} 피해!")
                
                # UI에 표시
                ui = getattr(self, 'combat_ui', None)
                if ui and hasattr(ui, 'add_message'):
                    ui.add_message(paradox['message'], (100, 200, 255))
                    ui.add_message(f"[시간의 역설] {actor.name}에게 {paradox['damage']} 피해!", (255, 100, 100))
                
                if paradox.get('time_frozen'):
                    self.logger.info(f"\033[96m{paradox['freeze_message']}\033[0m")
                    self.logger.info(f"[시간 정지] {paradox['glitched_name']}의 행동이 취소됨!")
                    self.logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━")
                    
                    # UI에 시간 정지 표시
                    if ui and hasattr(ui, 'add_message'):
                        ui.add_message(paradox['freeze_message'], (100, 200, 255))
                        ui.add_message(f"[시간 정지] {actor.name}의 행동이 취소됨!", (255, 150, 50))
                    
                    # 행동 취소 (턴 스킵)
                    self.atb.consume_atb(actor)
                    self._on_turn_end(actor)
                    
                    return {
                        "action": "skip",
                        "success": False,
                        "error": "time_frozen",
                        "message": "시간 정지로 인해 행동이 취소되었습니다."
                    }
                
                self.logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━")
        
        # 행동 불가 상태이상 체크 (빙결, 기절 등)
        if hasattr(actor, 'status_manager'):
            if not actor.status_manager.can_act():
                # StatusType을 명시적으로 import하여 사용
                from src.combat.status_effects import StatusType as StatusTypeEnum
                
                blocking_status = None
                for effect in actor.status_manager.status_effects:
                    if effect.status_type in [StatusTypeEnum.STUN, StatusTypeEnum.SLEEP, StatusTypeEnum.FREEZE, 
                                             StatusTypeEnum.PETRIFY, StatusTypeEnum.PARALYZE, StatusTypeEnum.TIME_STOP]:
                        blocking_status = effect.name
                        break
                
                status_name = blocking_status or "행동 불가 상태"
                self.logger.warning(f"{getattr(actor, 'name', 'Unknown')}은(는) {status_name}로 인해 행동할 수 없습니다. (턴 스킵)")
                
                # 행동 불가 상태에서도 상태이상 지속시간은 감소해야 함
                expired = actor.status_manager.update_duration()
                if expired:
                    self.logger.debug(f"{getattr(actor, 'name', 'Unknown')}: {len(expired)}개 상태 효과 만료 (행동 불가 중)")

                # 턴 스킵 처리 (ATB 소비 및 턴 종료)
                self.atb.consume_atb(actor)
                self._on_turn_end(actor)
                
                return {
                    "action": "skip",
                    "success": False,
                    "error": "actor_cannot_act",
                    "message": f"{status_name}로 인해 행동할 수 없습니다."
                }
        
        self.current_actor = actor
        result = {}

        # 행동 타입별 처리 (먼저 실행하여 실패 여부 확인)
        if action_type == ActionType.BRV_ATTACK:
            result = self._execute_brv_attack(actor, target, skill, **kwargs)
        elif action_type == ActionType.HP_ATTACK:
            result = self._execute_hp_attack(actor, target, skill, **kwargs)
        elif action_type == ActionType.BRV_HP_ATTACK:
            result = self._execute_brv_hp_attack(actor, target, skill, **kwargs)
        elif action_type == ActionType.SKILL:
            result = self._execute_skill(actor, target, skill, **kwargs)
        elif action_type == ActionType.ITEM:
            result = self._execute_item(actor, target, **kwargs)
        elif action_type == ActionType.DEFEND:
            result = self._execute_defend(actor, **kwargs)
        elif action_type == ActionType.FLEE:
            result = self._execute_flee(actor, **kwargs)

        # 행동 성공 여부 확인 (스킬 실패 시 ATB 소비 안 함)
        action_failed = False
        if action_type == ActionType.SKILL:
            # 스킬 실행 실패 시 (MP 부족 등)
            if not result.get("success", False):
                action_failed = True
                self.logger.warning(f"{actor.name}의 스킬 실행 실패: {result.get('error', 'unknown')}")
        
        # 행동이 실패하면 턴 시작 처리(재생 효과 포함)를 하지 않음
        if action_failed:
            self.logger.info(f"{actor.name}의 행동 실패 - ATB 소비 안 함, 재생 효과 없음")
            return result

        # 턴 시작 처리 (행동 성공 시에만)
        # 0. 특성 효과: 턴 시작 효과 적용
        from src.character.trait_effects import get_trait_effect_manager
        trait_manager = get_trait_effect_manager()

        # 턴 시작 시 특성 플래그 초기화 (berserker_rush 등)
        trait_manager.reset_turn_flags(actor)

        trait_manager.apply_turn_start_effects(actor)

        # 턴 시작 시 장비 내구도 소량 감소 (장기전 페널티)
        if hasattr(actor, 'degrade_equipment'):
            # 무기 소량 감소
            if actor.equipment.get("weapon"):
                actor.degrade_equipment("weapon", 1)
            # 방어구 소량 감소
            if actor.equipment.get("armor"):
                actor.degrade_equipment("armor", 1)
        
        # 0-1. 특성 효과: 주기적 버프 (tactical_genius 등)
        if hasattr(actor, 'active_traits'):
            from src.character.trait_effects import TraitEffectType
            for trait_data in actor.active_traits:
                trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                effects = trait_manager.get_trait_effects(trait_id)
                for effect in effects:
                    if effect.effect_type == TraitEffectType.PERIODIC_BUFF:
                        # 턴 카운트 확인
                        interval = effect.metadata.get("interval", 5) if effect.metadata else 5
                        duration = effect.metadata.get("duration", 2) if effect.metadata else 2
                        if self.turn_count > 0 and self.turn_count % interval == 0:
                            # 랜덤 버프 적용
                            import random
                            buff_types = ["atk", "def", "spd"]
                            buff_type = random.choice(buff_types)
                            buff_power = effect.value  # 0.30 = 30%
                            
                            if buff_type == "atk":
                                from src.combat.status_effects import StatusType, StatusEffect
                                buff = StatusEffect(
                                    status_type=StatusType.BOOST_ATK,
                                    duration=duration,
                                    intensity=int(buff_power * 100),
                                    name=f"공격력 증가 ({int(buff_power * 100)}%)"
                                )
                                if hasattr(actor, 'status_manager'):
                                    actor.status_manager.add_status(buff)
                                    self.logger.info(f"[{trait_id}] {actor.name} 랜덤 버프: 공격력 +{int(buff_power * 100)}% ({duration}턴)")
                            elif buff_type == "def":
                                from src.combat.status_effects import StatusType, StatusEffect
                                buff = StatusEffect(
                                    status_type=StatusType.BOOST_DEF,
                                    duration=duration,
                                    intensity=int(buff_power * 100),
                                    name=f"방어력 증가 ({int(buff_power * 100)}%)"
                                )
                                if hasattr(actor, 'status_manager'):
                                    actor.status_manager.add_status(buff)
                                    self.logger.info(f"[{trait_id}] {actor.name} 랜덤 버프: 방어력 +{int(buff_power * 100)}% ({duration}턴)")
                            elif buff_type == "spd":
                                from src.combat.status_effects import StatusType, StatusEffect
                                buff = StatusEffect(
                                    status_type=StatusType.BOOST_SPD,
                                    duration=duration,
                                    intensity=int(buff_power * 100),
                                    name=f"속도 증가 ({int(buff_power * 100)}%)"
                                )
                                if hasattr(actor, 'status_manager'):
                                    actor.status_manager.add_status(buff)
                                    self.logger.info(f"[{trait_id}] {actor.name} 랜덤 버프: 속도 +{int(buff_power * 100)}% ({duration}턴)")
        
        # 0-2. active_buffs의 REGEN, HP_REGEN, MP_REGEN 처리
        if hasattr(actor, 'active_buffs') and actor.active_buffs:
            # REGEN 처리 (시전자 스탯 기반 HP 재생)
            if 'regen' in actor.active_buffs:
                regen_buff = actor.active_buffs['regen']
                regen_percent = float(regen_buff.get('value', 0))
                # 시전자 스탯 기반 계산
                stat_base = regen_buff.get('stat_base', 0)
                if stat_base > 0:
                    hp_amount = int(stat_base * regen_percent)
                else:
                    # stat_base가 없으면 기존 방식 (하위 호환성, 최대 HP 기반)
                    if hasattr(actor, 'max_hp'):
                        hp_amount = int(actor.max_hp * regen_percent)
                    else:
                        hp_amount = 0
                
                if hp_amount > 0 and hasattr(actor, 'current_hp') and hasattr(actor, 'max_hp'):
                    old_hp = actor.current_hp
                    if hasattr(actor, 'heal'):
                        actual_heal = actor.heal(hp_amount)
                    else:
                        actor.current_hp = min(actor.max_hp, actor.current_hp + hp_amount)
                        actual_heal = actor.current_hp - old_hp
                    if actual_heal > 0:
                        self.logger.info(f"{actor.name} HP 재생: +{actual_heal} ({int(regen_percent*100)}% 스탯 기반, 버프)")
            
            # HP_REGEN 처리 (시전자 스탯 기반 HP 재생, 약 8%)
            if 'hp_regen' in actor.active_buffs:
                hp_regen_buff = actor.active_buffs['hp_regen']
                # 시전자 스탯 기반 계산 (약 8%)
                stat_base = hp_regen_buff.get('stat_base', 0)
                if stat_base > 0:
                    hp_amount = int(stat_base * 0.16)  # 2배 증가 (8% → 16%)
                else:
                    # stat_base가 없으면 기존 value 사용 (하위 호환성)
                    hp_amount = int(hp_regen_buff.get('value', 0))
                
                if hp_amount > 0 and hasattr(actor, 'current_hp') and hasattr(actor, 'max_hp'):
                    old_hp = actor.current_hp
                    if hasattr(actor, 'heal'):
                        actual_heal = actor.heal(hp_amount)
                    else:
                        actor.current_hp = min(actor.max_hp, actor.current_hp + hp_amount)
                        actual_heal = actor.current_hp - old_hp
                    if actual_heal > 0:
                        self.logger.info(f"{actor.name} HP 재생: +{actual_heal} (버프, 스탯 기반)")
            
            # MP 재생 처리 (고정값 기반)
            if 'mp_regen' in actor.active_buffs:
                mp_regen_buff = actor.active_buffs['mp_regen']
                mp_amount = int(mp_regen_buff.get('value', 0))
                
                if mp_amount > 0 and hasattr(actor, 'current_mp') and hasattr(actor, 'max_mp'):
                    old_mp = actor.current_mp
                    if hasattr(actor, 'restore_mp'):
                        actual_restore = actor.restore_mp(mp_amount)
                    else:
                        actor.current_mp = min(actor.max_mp, actor.current_mp + mp_amount)
                        actual_restore = actor.current_mp - old_mp
                    if actual_restore > 0:
                        self.logger.info(f"{actor.name} MP 재생: +{actual_restore} (버프)")
        # 기믹 업데이트에 context 전달 (언데드 자동 공격 등)
        context = {
            'enemies': self.enemies,
            'combat_manager': self,
            'damage_calculator': self.damage_calc
        }
        GimmickUpdater.on_turn_start(actor, context)

        # === 보스 랜덤 절망 대사 (림버스 컴퍼니 스타일) ===
        # 턴마다 일정 확률로 랜덤 대사 출력 (동시에 여러 개 가능)
        import random
        from src.combat.boss_dialogue import get_boss_dialogue
        boss_dialogue = get_boss_dialogue()

        # 보스 찾기
        boss = None
        boss_id = None
        for enemy in self.enemies:
            if hasattr(enemy, 'enemy_id') and enemy.enemy_id in ['sephiroth', 'abel_cain']:
                if getattr(enemy, 'is_alive', True):
                    boss = enemy
                    boss_id = enemy.enemy_id
                    break

        if boss and boss_id:
            # 보스의 턴: 높은 확률로 대사 출력 (글리치/공포 효과 - 방해 증가)
            if actor == boss:
                # 60% 확률로 대사 1개 출력
                if random.random() < 0.6:
                    dialogue = boss_dialogue.get_random_dialogue(boss_id)
                    if dialogue:
                        boss_dialogue.print_dialogue(self.logger, dialogue, combat_ui=getattr(self, 'combat_ui', None))

                # 추가로 40% 확률로 대사 1개 더 출력 (동시에 2개)
                if random.random() < 0.4:
                    dialogue = boss_dialogue.get_random_dialogue(boss_id)
                    if dialogue:
                        boss_dialogue.print_dialogue(self.logger, dialogue, combat_ui=getattr(self, 'combat_ui', None))

                # 추가로 20% 확률로 대사 1개 더 출력 (동시에 3개)
                if random.random() < 0.2:
                    dialogue = boss_dialogue.get_random_dialogue(boss_id)
                    if dialogue:
                        boss_dialogue.print_dialogue(self.logger, dialogue, combat_ui=getattr(self, 'combat_ui', None))

                # 아주 낮은 확률(5%)로 대사 1개 더 출력 (동시에 4개 - 화면 뒤덮기)
                if random.random() < 0.05:
                    dialogue = boss_dialogue.get_random_dialogue(boss_id)
                    if dialogue:
                        boss_dialogue.print_dialogue(self.logger, dialogue, combat_ui=getattr(self, 'combat_ui', None))

            # 아군의 턴: 중간 확률로 대사 출력 (플레이어도 괴롭히기)
            elif actor in self.allies:
                # 25% 확률로 대사 1개 출력
                if random.random() < 0.25:
                    dialogue = boss_dialogue.get_random_dialogue(boss_id)
                    if dialogue:
                        boss_dialogue.print_dialogue(self.logger, dialogue, combat_ui=getattr(self, 'combat_ui', None))

                # 추가로 15% 확률로 대사 1개 더 출력
                if random.random() < 0.15:
                    dialogue = boss_dialogue.get_random_dialogue(boss_id)
                    if dialogue:
                        boss_dialogue.print_dialogue(self.logger, dialogue, combat_ui=getattr(self, 'combat_ui', None))

                # 추가로 5% 확률로 대사 1개 더 출력 (동시에 3개)
                if random.random() < 0.05:
                    dialogue = boss_dialogue.get_random_dialogue(boss_id)
                    if dialogue:
                        boss_dialogue.print_dialogue(self.logger, dialogue, combat_ui=getattr(self, 'combat_ui', None))

        # 1. INT BRV 회복 (BREAK 상태 해제 포함)
        # recover_int_brv가 BREAK 상태를 자동으로 해제하고 BRV를 회복합니다
        was_broken = self.brave.is_broken(actor)
        int_brv_recovered = self.brave.recover_int_brv(actor)

        # 세피로스/카인 BREAK 해제 즉시 반격 (일반 행동 대체)
        break_counterattack_executed = False
        if int_brv_recovered > 0:
            self.logger.debug(f"{actor.name}이(가) INT BRV {int_brv_recovered} 회복")

            if was_broken and hasattr(actor, 'enemy_id') and actor.enemy_id in ['sephiroth', 'abel_cain']:
                self._execute_break_counterattack(actor)
                break_counterattack_executed = True
                # BREAK 반격으로 턴을 소모하므로 일반 행동은 스킵
                self.logger.debug(f"{actor.name}의 BREAK 반격으로 일반 행동 스킵")
                self.atb.consume_atb(actor)
                self._on_turn_end(actor)
                result["success"] = True
                result["action"] = "break_counterattack"
                return result

        # 3. DoT (지속 피해) 처리
        if hasattr(actor, 'status_manager'):
            dot_result = actor.status_manager.process_dot_effects(actor)
            if dot_result["total_damage"] > 0 or dot_result["total_mp_drain"] > 0:
                self.logger.info(
                    f"{actor.name}: DoT 피해 {dot_result['total_damage']}"
                    + (f", MP 소모 {dot_result['total_mp_drain']}" if dot_result["total_mp_drain"] > 0 else "")
                )
                # DoT로 사망 여부 확인
                if hasattr(actor, 'current_hp') and actor.current_hp <= 0:
                    if not (hasattr(actor, '_has_undying_existence') and actor._has_undying_existence()):
                        actor.is_alive = False  # is_alive 속성이 없으면 생성
                        self.logger.warning(f"{actor.name}이(가) DoT로 사망!")
        
        # 3-0.5. 도적 독(Venom) DoT 처리
        # 아군 중 도적(venom_system)이 있으면, 살아있는 적 전원에게 독 DoT 적용
        for ally in self.allies:
            if getattr(ally, 'gimmick_type', None) == 'venom_system' and getattr(ally, 'is_alive', True):
                for enemy in self.enemies:
                    if getattr(enemy, 'is_alive', True) and getattr(enemy, 'venom_stacks', 0) > 0:
                        dot_dmg = GimmickUpdater.apply_venom_dot(ally, enemy)
                        if dot_dmg and dot_dmg > 0:
                            # 독 DoT로 사망 여부 확인
                            if hasattr(enemy, 'current_hp') and enemy.current_hp <= 0:
                                if not (hasattr(enemy, '_has_undying_existence') and enemy._has_undying_existence()):
                                    enemy.is_alive = False
                                    self.logger.warning(f"{enemy.name}이(가) 독 DoT로 사망!")

        # 3-1. 환경 효과 처리 (아군에게만 적용 - 적은 제외)
        if self.dungeon and self.combat_position:
            # 아군인 경우에만 환경 효과 피해/회복 적용
            if actor not in self.enemies:
                self._apply_environmental_effects(actor)
                # 환경 효과로 사망 여부 확인
                if hasattr(actor, 'current_hp') and actor.current_hp <= 0:
                    if not (hasattr(actor, '_has_undying_existence') and actor._has_undying_existence()):
                        actor.is_alive = False
                        self.logger.warning(f"{actor.name}이(가) 환경 효과로 사망!")
            
            # 환경 효과 스탯 수정치 적용 (아군에게만 - ATB 속도, 데미지 계산 등에 영향)
            for ally in self.allies:
                if getattr(ally, 'is_alive', True):
                    ally.env_stat_modifiers = self.get_environmental_stat_modifiers(ally)
        
        # 3-2. 랜섬웨어 효과 처리 (적의 턴 시작 시)
        if actor in self.enemies:
            self._process_ransomware_damage(actor)
            # 랜섬웨어로 사망 여부 확인
            if hasattr(actor, 'current_hp') and actor.current_hp <= 0:
                if not (hasattr(actor, '_has_undying_existence') and actor._has_undying_existence()):
                    actor.is_alive = False
                    self.logger.warning(f"{actor.name}이(가) 랜섬웨어로 사망!")
        
        # 3-3. 사망 여부 확인 (DoT, 환경 효과, 랜섬웨어로 사망한 경우)
        is_dead_from_start_effects = False
        if not getattr(actor, 'is_alive', True):
            is_dead_from_start_effects = True
        elif hasattr(actor, 'current_hp') and actor.current_hp <= 0:
            if not (hasattr(actor, '_has_undying_existence') and actor._has_undying_existence()):
                is_dead_from_start_effects = True

        if is_dead_from_start_effects:
            self.logger.warning(f"{actor.name}이(가) 턴 시작 시 피해로 사망하여 행동을 취소합니다.")
            result["success"] = False
            result["error"] = "사망"
            result["death_reason"] = "턴 시작 시 피해"
            # ATB는 소비하지만 행동하지 못함
            self.atb.consume_atb(actor)
            self._on_turn_end(actor)
            # 전투 종료 체크 (DoT 사망으로 인한 승패 결정)
            self._check_battle_end()
            return result

        # 4. 상태 효과 지속시간 감소
        if hasattr(actor, 'status_manager'):
            expired = actor.status_manager.update_duration()
            if expired:
                self.logger.debug(f"{actor.name}: {len(expired)}개 상태 효과 만료")

        # 5. 행동 불가능 상태 확인 (스턴, 마비, 수면 등)
        if hasattr(actor, 'status_manager'):
            can_act = actor.status_manager.can_act()
            if not can_act:
                self.logger.info(f"{actor.name}은(는) 행동 불가능 상태!")
                result["success"] = False
                result["error"] = "행동 불가능 상태"
                # ATB는 소비하지만 행동하지 못함
                self.atb.consume_atb(actor)
                self._on_turn_end(actor)
                return result

        # 추가 행동 확인 (berserker_rush 특성 등)
        extra_action_available, extra_action_cost = trait_manager.check_extra_action(actor)
        is_extra_action = getattr(actor, '_is_extra_action', False)
        
        if extra_action_available and not is_extra_action:
            # 추가 행동 가능! - ATB를 소비하지 않고 추가 턴 부여
            # NOTE: 의도적으로 _on_turn_end()를 호출하지 않음
            # - berserker_rush는 같은 턴에 두 번 행동하는 것이므로 버프/디버프 지속시간이 한 번만 감소해야 함
            # - 기믹 업데이트(광기 감소 등)도 추가 행동 후에 한 번만 실행됨
            # - 턴 카운트도 한 번만 증가함
            trait_manager.activate_extra_action(actor, extra_action_cost)
            actor._is_extra_action = True  # 다음 행동은 추가 행동임을 표시
            result["extra_action_granted"] = True
            self.logger.info(f"[추가 행동] {actor.name}이(가) 추가 행동을 획득했습니다!")
            
            # 콜백 호출
            if self.on_action_complete:
                self.on_action_complete(actor, result)
            
            # 이벤트 발행 (턴 종료 없이)
            event_bus.publish(Events.COMBAT_ACTION, {
                "actor": actor,
                "action_type": action_type.value,
                "target": target,
                "result": result
            })
            
            return result  # 턴 종료 없이 반환 (추가 행동 대기)
        
        # 추가 행동 플래그 초기화
        if is_extra_action:
            actor._is_extra_action = False

        # ATB 소비 (행동 성공 시)
        # 스킬의 self_atb_cost 메타데이터 확인 (시간술사 "시간 가속" 등)
        if action_type == ActionType.SKILL and skill and hasattr(skill, 'metadata'):
            self_atb_cost = skill.metadata.get('self_atb_cost', None)
            if self_atb_cost is not None:
                # 커스텀 ATB 소모 비율 적용
                max_atb = getattr(actor, 'max_atb', 2000)  # 기본값 2000
                atb_cost = int(max_atb * self_atb_cost)
                old_atb = actor.atb_gauge
                actor.atb_gauge = max(0, actor.atb_gauge - atb_cost)
                actual_consumed = old_atb - actor.atb_gauge
                self.logger.info(f"[시간 가속] {actor.name}의 ATB {self_atb_cost*100}% 소모 (감소: {actual_consumed})")
            else:
                # 일반 ATB 소비
                self.atb.consume_atb(actor)
        else:
            # 일반 ATB 소비
            self.atb.consume_atb(actor)

        # 연속 베기 특성 (rapid_slash): 공격 시 25% 확률로 즉시 추가 공격
        rapid_slash_triggered = False
        if action_type == ActionType.SKILL and result.get("success") and target:
            # 특성 체크
            has_rapid_slash = False
            for attr in ['active_traits', 'available_traits']:
                if hasattr(actor, attr) and getattr(actor, attr):
                    for t in getattr(actor, attr):
                        trait_id = t if isinstance(t, str) else (t.get('id') if isinstance(t, dict) else None)
                        if trait_id == 'rapid_slash':
                            has_rapid_slash = True
                            break
                if has_rapid_slash:
                    break
            
            # 25% 확률로 추가 공격 (무한 루프 방지: 한 턴에 한 번만)
            if has_rapid_slash and not kwargs.get('_rapid_slash_triggered'):
                import random
                if random.random() < 0.25:
                    rapid_slash_triggered = True
                    self.logger.info(f"[연속 베기] {actor.name} 추가 공격 발동!")
                    
                    # 추가 공격 실행 (기본 공격)
                    from src.character.skills.skill_manager import SkillManager
                    skill_manager = SkillManager()
                    basic_skills = skill_manager.get_skills_for_character(actor)
                    if basic_skills:
                        basic_skill = basic_skills[0]  # 첫 번째 스킬 (기본 공격)
                        extra_result = self.execute_action(
                            actor, ActionType.SKILL, target, basic_skill,
                            _rapid_slash_triggered=True, is_extra_action=True
                        )
                        self.logger.info(f"[연속 베기] 추가 공격 결과: {extra_result.get('message', 'OK')}")

        # 턴 종료 처리
        self._on_turn_end(actor)

        # 팀워크 게이지 업데이트 (행동 성공 시에만)
        if result.get("success", True) and self.party:
            self.update_teamwork_gauge(
                action_type=action_type,
                is_critical=result.get("is_critical", False),
                caused_break=result.get("caused_break", False),
                healed_ally=result.get("healed", False),
                was_hit=result.get("was_hit", False)
            )

        # 콜백 호출
        if self.on_action_complete:
            self.on_action_complete(actor, result)

        # 이벤트 발행
        event_bus.publish(Events.COMBAT_ACTION, {
            "actor": actor,
            "action_type": action_type.value,
            "target": target,
            "result": result
        })

        # === 보스 페이즈 전환 체크 ===
        if target and hasattr(target, 'enemy_id'):
            enemy_id = target.enemy_id
            if enemy_id in ["abel_cain", "sephiroth"]:
                # 이전 페이즈 저장 (없으면 1)
                old_phase = getattr(target, '_current_phase', 1)

                # 현재 페이즈 계산
                current_phase = 1
                if enemy_id == "abel_cain":
                    from src.combat.cain_skills import CainSkillDatabase
                    current_phase = CainSkillDatabase.get_current_phase(
                        target.current_hp, target.max_hp
                    )
                elif enemy_id == "sephiroth":
                    from src.combat.sephiroth_skills import SephirothSkillDatabase
                    current_phase = SephirothSkillDatabase.get_current_phase(
                        target.current_hp, target.max_hp
                    )

                # 페이즈 전환 감지
                if current_phase != old_phase:
                    transition_msg = ""
                    if enemy_id == "abel_cain":
                        from src.combat.cain_skills import CainSkillDatabase
                        transition_msg = CainSkillDatabase.get_phase_transition_message(current_phase)
                    elif enemy_id == "sephiroth":
                        from src.combat.sephiroth_skills import SephirothSkillDatabase
                        transition_msg = SephirothSkillDatabase.get_phase_transition_message(current_phase)

                    # UI에 메시지 표시
                    self.phase_transition_message = transition_msg
                    target._current_phase = current_phase
                    self.logger.info(f"{target.name} 페이즈 전환: {old_phase} → {current_phase}")

        # ── 체인어빌리티 트리거 체크 ──
        if result.get("success", True) and actor in self.allies:
            chain_triggered = False
            # 1. BREAK/SCATTER 트리거 (SCATTER는 항상 BREAK와 동시 발생)
            # is_break: BRV 공격 결과, brv_is_break: BRV+HP 복합 공격 결과
            if result.get("is_break") or result.get("brv_is_break"):
                reason = "scatter" if target and getattr(target, 'is_scattered', False) else "break"
                self.trigger_chain_ability_check(actor, reason)
                chain_triggered = True
            # 2. triggers_chain 플래그 스킬
            if not chain_triggered and skill and getattr(skill, 'triggers_chain', False):
                self.trigger_chain_ability_check(actor, "skill")
            # 3. 팀워크 스킬 트리거 (execute_teamwork_skill에서 별도 처리)

        # ── 호감도 증가: 전투 행동 시 ──
        if result.get("success", True) and self._affinity_manager:
            party_jobs = [
                c.character_class for c in self.allies
                if hasattr(c, 'character_class')
            ]
            # 아군 행동 시 호감도 소폭 증가 (+1)
            if actor in self.allies and hasattr(actor, 'character_class'):
                self._affinity_manager.on_battle_action(actor.character_class, party_jobs)
            # 힐/버프 시전 시 호감도 증가 (+3)
            if (actor in self.allies and target and target in self.allies
                    and hasattr(actor, 'character_class') and hasattr(target, 'character_class')
                    and action_type == ActionType.SKILL
                    and (result.get("healed") or result.get("buffed"))):
                self._affinity_manager.on_heal_or_buff(
                    actor.character_class, target.character_class)

        # ── 연계스킬 트리거 체크 (자동, 무료, 확률 기반) ──
        bond_skill_results = []
        if result.get("success", True):
            # 1. 아군 공격 적중 시 (ally_attack_hit)
            if actor in self.allies and action_type in (
                ActionType.BRV_ATTACK, ActionType.HP_ATTACK,
                ActionType.BRV_HP_ATTACK, ActionType.SKILL
            ):
                bond_checks = self.check_bond_skills("ally_attack_hit", actor)
                for br in bond_checks:
                    bond_exec = self.execute_bond_skill(br, actor)
                    bond_skill_results.append(bond_exec)

            # 2. 아군이 피해를 받았을 때 (ally_damaged)
            if actor in self.enemies and target and target in self.allies:
                bond_checks = self.check_bond_skills("ally_damaged", target)
                for br in bond_checks:
                    bond_exec = self.execute_bond_skill(br, target)
                    bond_skill_results.append(bond_exec)

            # 3. 아군이 회복받았을 때 (ally_healed)
            if (actor in self.allies and target and target in self.allies
                    and action_type == ActionType.SKILL
                    and result.get("healed")):
                bond_checks = self.check_bond_skills("ally_healed", actor)
                for br in bond_checks:
                    bond_exec = self.execute_bond_skill(br, actor)
                    bond_skill_results.append(bond_exec)

            # 4. 크리티컬 히트 시 (critical_hit)
            if actor in self.allies and result.get("is_critical"):
                bond_checks = self.check_bond_skills("critical_hit", actor)
                for br in bond_checks:
                    bond_exec = self.execute_bond_skill(br, actor)
                    bond_skill_results.append(bond_exec)

            # 5. 적 처치 시 (enemy_killed) / 치명타 (ally_lethal_hit)
            if actor in self.allies and target and target in self.enemies:
                target_dead = (
                    (hasattr(target, 'is_alive') and not target.is_alive)
                    or (hasattr(target, 'current_hp') and target.current_hp <= 0)
                )
                if target_dead:
                    bond_checks = self.check_bond_skills("enemy_killed", actor)
                    for br in bond_checks:
                        bond_exec = self.execute_bond_skill(br, actor)
                        bond_skill_results.append(bond_exec)
                    # ally_lethal_hit: 마무리 일격 (enemy_killed과 동일 조건)
                    bond_checks = self.check_bond_skills("ally_lethal_hit", actor)
                    for br in bond_checks:
                        bond_exec = self.execute_bond_skill(br, actor)
                        bond_skill_results.append(bond_exec)

            # 6. 아군 사망 시 (ally_killed)
            if actor in self.enemies and target and target in self.allies:
                target_dead = (
                    (hasattr(target, 'is_alive') and not target.is_alive)
                    or (hasattr(target, 'current_hp') and target.current_hp <= 0)
                )
                if target_dead:
                    bond_checks = self.check_bond_skills("ally_killed", target)
                    for br in bond_checks:
                        bond_exec = self.execute_bond_skill(br, target)
                        bond_skill_results.append(bond_exec)

            # 7. 아군 스킬 적중 시 (ally_skill_hit)
            if actor in self.allies and action_type == ActionType.SKILL:
                bond_checks = self.check_bond_skills("ally_skill_hit", actor)
                for br in bond_checks:
                    bond_exec = self.execute_bond_skill(br, actor)
                    bond_skill_results.append(bond_exec)

            # 8. 방어 행동 시 (defend_action)
            if actor in self.allies and action_type == ActionType.DEFEND:
                bond_checks = self.check_bond_skills("defend_action", actor)
                for br in bond_checks:
                    bond_exec = self.execute_bond_skill(br, actor)
                    bond_skill_results.append(bond_exec)

            # 9. 아군 버프 시 (ally_buffed)
            if (actor in self.allies and target and target in self.allies
                    and result.get("buffed")):
                bond_checks = self.check_bond_skills("ally_buffed", actor)
                for br in bond_checks:
                    bond_exec = self.execute_bond_skill(br, actor)
                    bond_skill_results.append(bond_exec)

            # 10. 적 BRV 브레이크 시 (enemy_break)
            if actor in self.allies and (
                result.get("is_break") or result.get("brv_is_break")
            ):
                bond_checks = self.check_bond_skills("enemy_break", actor)
                for br in bond_checks:
                    bond_exec = self.execute_bond_skill(br, actor)
                    bond_skill_results.append(bond_exec)

            # 11. 팀워크 스킬 사용 시 (teamwork_skill_used)
            if (actor in self.allies and skill
                    and hasattr(skill, 'is_teamwork_skill') and skill.is_teamwork_skill):
                bond_checks = self.check_bond_skills("teamwork_skill_used", actor)
                for br in bond_checks:
                    bond_exec = self.execute_bond_skill(br, actor)
                    bond_skill_results.append(bond_exec)

            # 12. 양측 모두 HP가 낮을 때 (both_low_hp)
            if actor in self.allies:
                actor_low = (
                    hasattr(actor, 'current_hp') and hasattr(actor, 'max_hp')
                    and actor.current_hp <= actor.max_hp * 0.3
                )
                any_ally_low = any(
                    hasattr(a, 'current_hp') and hasattr(a, 'max_hp')
                    and a.current_hp <= a.max_hp * 0.3
                    for a in self.allies if a != actor and getattr(a, 'is_alive', True)
                )
                if actor_low and any_ally_low:
                    bond_checks = self.check_bond_skills("both_low_hp", actor)
                    for br in bond_checks:
                        bond_exec = self.execute_bond_skill(br, actor)
                        bond_skill_results.append(bond_exec)

        if bond_skill_results:
            result["bond_skill_results"] = bond_skill_results

        self.current_actor = None
        return result

    def _execute_brv_attack(
        self,
        attacker: Any,
        defender: Any,
        skill: Optional[Any] = None,
        trigger_gimmick: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """BRV 공격 실행"""
        # 스킬 배율
        # 기본 공격(스킬 없음) 시: 플레이어는 1.0, 적은 2.25배 (밸런스 조정)
        if skill:
            skill_multiplier = getattr(skill, "brv_multiplier", 1.0)
        else:
            # 기본 공격: 적은 2.25배, 플레이어는 1.0배
            skill_multiplier = 2.25 if attacker in self.enemies else 1.0

        # 방어 스택 보너스 적용 (집중의 힘 특성)
        defend_stack_bonus = 0
        if hasattr(attacker, 'defend_stack_count') and attacker.defend_stack_count > 0:
            has_focus_power = any(
                (t if isinstance(t, str) else t.get('id')) == 'focus_power'
                for t in getattr(attacker, 'active_traits', [])
            )

            if has_focus_power:
                defend_stack_bonus = attacker.defend_stack_count * 0.50  # 스택당 50%
                skill_multiplier *= (1.0 + defend_stack_bonus)
                self.logger.info(
                    f"[집중의 힘] {attacker.name} 스택 {attacker.defend_stack_count}개 소비 → 데미지 +{defend_stack_bonus * 100:.0f}%"
                )

        # combo_multiplier (콤보 배율 처리) - 데미지 계산 전에 적용
        combo_bonus = 0
        if skill and hasattr(skill, 'metadata') and skill.metadata.get('combo_multiplier'):
            combo_mult = skill.metadata['combo_multiplier']
            combo_key = f"_combo_count_{getattr(skill, 'skill_id', 'default')}"
            current_combo = getattr(attacker, combo_key, 0) + 1
            
            # 콤보 최대치 제한
            max_combo = skill.metadata.get('combo_max', 10)
            current_combo = min(current_combo, max_combo)
            setattr(attacker, combo_key, current_combo)
            
            # 콤보 보너스 계산 및 적용
            combo_bonus = (current_combo - 1) * combo_mult
            if combo_bonus > 0:
                skill_multiplier *= (1.0 + combo_bonus)
                self.logger.debug(f"[콤보] {attacker.name} 콤보 {current_combo}회 → 데미지 +{combo_bonus*100:.0f}%")
            
            # combo_reset: 다른 스킬 사용 시 콤보 리셋 여부
            # True(기본값): 다른 스킬 콤보 초기화 / False: 다른 스킬 콤보 유지
            if skill.metadata.get('combo_reset', True):
                # 다른 스킬의 콤보 초기화 (vars 사용으로 성능 개선)
                try:
                    attacker_vars = vars(attacker)
                except TypeError:
                    attacker_vars = getattr(attacker, '__dict__', {})
                for attr in list(attacker_vars.keys()):
                    if attr.startswith('_combo_count_') and attr != combo_key:
                        setattr(attacker, attr, 0)

        # first_strike_bonus (선제공격 보너스) - 데미지 계산 전에 적용
        first_strike_bonus = 0
        if self.turn_count == 0 and skill and hasattr(skill, 'metadata') and skill.metadata.get('first_strike_bonus'):
            first_strike_bonus = skill.metadata['first_strike_bonus']
            skill_multiplier *= (1.0 + first_strike_bonus)
            self.logger.info(f"[선제 공격] {attacker.name} 첫 턴 공격! 데미지 +{first_strike_bonus*100:.0f}%")

        # revenge_bonus (복수 보너스 - 피격 후 공격) - 데미지 계산 전에 적용
        revenge_bonus = 0
        if hasattr(attacker, '_recently_damaged') and attacker._recently_damaged:
            if skill and hasattr(skill, 'metadata') and skill.metadata.get('revenge_bonus'):
                revenge_bonus = skill.metadata['revenge_bonus']
                skill_multiplier *= (1.0 + revenge_bonus)
                self.logger.info(f"[복수] {attacker.name} 복수 공격! 데미지 +{revenge_bonus*100:.0f}%")
            attacker._recently_damaged = False  # 복수 후 초기화

        # 데미지 계산
        damage_result = self.damage_calc.calculate_brv_damage(
            attacker, defender, skill_multiplier, **kwargs
        )

        # 공격 빗나감 체크
        is_miss = damage_result.details.get("miss", False)
        if is_miss:
            # 공격 빗나감 로그
            attacker_type = "아군" if attacker in self.allies else "적"
            defender_type = "아군" if defender in self.allies else "적"
            self.logger.info(f"[빗나감] {attacker_type} {attacker.name}의 공격이 {defender_type} {defender.name}에게 빗나갔다!")
            # SFX 재생 (회피 사운드)
            play_sfx("combat", "miss")

            # 회피 후 특성 처리
            self._process_evade_traits(defender, attacker)
        else:
            # 명중 SFX 재생 (스킬 SFX 우선 사용)
            if skill and hasattr(skill, 'sfx') and skill.sfx:
                if isinstance(skill.sfx, tuple):
                    play_sfx(skill.sfx[0], skill.sfx[1])
                else:
                    play_sfx("combat", "attack_physical")
            else:
                play_sfx("combat", "attack_physical")
            
            # 무기 내구도 감소 (명중 시에만, skip_degrade 플래그 확인)
            if hasattr(attacker, 'degrade_equipment') and not kwargs.get('skip_degrade', False):
                attacker.degrade_equipment("weapon", 3)  # 3배 증가

                # 크리티컬 공격 시 무기 추가 내구도 감소 (부담)
                if damage_result.is_critical:
                    attacker.degrade_equipment("weapon", 2)  # 크리티컬 시 +2 추가 감소

        # BRV 공격 적용
        brv_result = self.brave.brv_attack(attacker, defender, damage_result.final_damage)

        # 공격 후 방어 스택 초기화
        if hasattr(attacker, 'defend_stack_count') and attacker.defend_stack_count > 0:
            attacker.defend_stack_count = 0

        # 빗나간 공격은 기믹 트리거 안 함
        if not is_miss and trigger_gimmick and attacker in self.allies:
            # 아군 공격 시 기믹 트리거 (지원사격 등)
            context = {"all_enemies": self.enemies}
            GimmickUpdater.on_ally_attack(attacker, self.allies, target=defender, context=context)

        # BRV 공격 상태이상 효과 (스킬 메타데이터 기반)
        if not is_miss and skill and hasattr(skill, 'metadata'):
            # stun_chance (기절 확률)
            if skill.metadata.get('stun_chance'):
                import random
                stun_chance = skill.metadata['stun_chance']
                if random.random() < stun_chance:
                    from src.combat.status_effects import StatusEffect, StatusType
                    stun = StatusEffect("기절", StatusType.STUN, duration=1, intensity=1.0)
                    if hasattr(defender, 'status_manager'):
                        defender.status_manager.add_status(stun)
                        self.logger.info(f"[기절] {defender.name} 기절! ({stun_chance*100:.0f}% 확률)")

            # freeze_chance (빙결 확률)
            if skill.metadata.get('freeze_chance'):
                import random
                freeze_chance = skill.metadata['freeze_chance']
                freeze_duration = skill.metadata.get('freeze_duration', 1)
                if random.random() < freeze_chance:
                    from src.combat.status_effects import StatusEffect, StatusType
                    freeze = StatusEffect("빙결", StatusType.FREEZE, duration=min(freeze_duration, 2), intensity=1.0)
                    if hasattr(defender, 'status_manager'):
                        defender.status_manager.add_status(freeze)
                        self.logger.info(f"[빙결] {defender.name} 빙결! ({freeze_chance*100:.0f}% 확률)")

            # blind_chance (실명 확률)
            if skill.metadata.get('blind_chance'):
                import random
                blind_chance = skill.metadata['blind_chance']
                blind_duration = skill.metadata.get('blind_duration', 2)
                if random.random() < blind_chance:
                    from src.combat.status_effects import StatusEffect, StatusType
                    blind = StatusEffect("실명", StatusType.BLIND, duration=blind_duration, intensity=1.0)
                    if hasattr(defender, 'status_manager'):
                        defender.status_manager.add_status(blind)
                        self.logger.info(f"[실명] {defender.name} 실명! ({blind_chance*100:.0f}% 확률)")

            # silence_chance (침묵 확률)
            if skill.metadata.get('silence_chance'):
                import random
                silence_chance = skill.metadata['silence_chance']
                silence_duration = skill.metadata.get('silence_duration', 2)
                if random.random() < silence_chance:
                    from src.combat.status_effects import StatusEffect, StatusType
                    silence = StatusEffect("침묵", StatusType.SILENCE, duration=min(silence_duration, 2), intensity=1.0)
                    if hasattr(defender, 'status_manager'):
                        defender.status_manager.add_status(silence)
                        self.logger.info(f"[침묵] {defender.name} 침묵! ({silence_chance*100:.0f}% 확률)")

        # 공격 진동 (크리티컬이면 강한 진동)
        if not is_miss:
            if damage_result.is_critical:
                vibration_manager.vibrate(VibrationPattern.HEAVY_TAP)
            elif brv_result["is_break"]:
                vibration_manager.vibrate(VibrationPattern.MEDIUM_TAP)
            else:
                vibration_manager.vibrate(VibrationPattern.LIGHT_TAP)
        
        return {
            "action": "brv_attack",
            "damage": damage_result.final_damage,
            "is_critical": damage_result.is_critical,
            "brv_stolen": brv_result["brv_stolen"],
            "actual_gain": brv_result["actual_gain"],
            "is_break": brv_result["is_break"],
            "defend_stack_bonus": defend_stack_bonus,
            "combo_bonus": combo_bonus,
            "first_strike_bonus": first_strike_bonus,
            "revenge_bonus": revenge_bonus,
            "is_miss": is_miss
        }

    def _execute_hp_attack(
        self,
        attacker: Any,
        defender: Any,
        skill: Optional[Any] = None,
        trigger_gimmick: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """HP 공격 실행"""
        if attacker.current_brv <= 0:
            self.logger.warning(f"{attacker.name}: BRV가 0이라 HP 공격 불가")
            return {"action": "hp_attack", "error": "no_brv"}

        # SFX 재생 (스킬 SFX 우선 사용, 없으면 기본 SFX)
        if skill and hasattr(skill, 'sfx') and skill.sfx:
            if isinstance(skill.sfx, tuple):
                play_sfx(skill.sfx[0], skill.sfx[1])
            else:
                play_sfx("combat", "damage_high")
        else:
            play_sfx("combat", "damage_high")

        # 스킬 배율
        # 기본 공격(스킬 없음) 시: 플레이어는 1.0, 적은 1.5배 (밸런스 조정)
        if skill:
            hp_multiplier = getattr(skill, "hp_multiplier", 1.0)
        else:
            # 기본 공격: 적은 1.5배, 플레이어는 1.0배
            hp_multiplier = 2.25 if attacker in self.enemies else 1.0

        # 방어 스택 보너스 적용 (집중의 힘 특성)
        defend_stack_bonus = 0
        if hasattr(attacker, 'defend_stack_count') and attacker.defend_stack_count > 0:
            has_focus_power = any(
                (t if isinstance(t, str) else t.get('id')) == 'focus_power'
                for t in getattr(attacker, 'active_traits', [])
            )

            if has_focus_power:
                defend_stack_bonus = attacker.defend_stack_count * 0.50  # 스택당 50%
                hp_multiplier *= (1.0 + defend_stack_bonus)
                self.logger.info(
                    f"[집중의 힘] {attacker.name} 스택 {attacker.defend_stack_count}개 소비 → 데미지 +{defend_stack_bonus * 100:.0f}%"
                )

        # 어둠기사 execute 효과: 적 HP 비례 추가 데미지 (3단계)
        if skill and hasattr(skill, 'metadata') and skill.metadata.get('execute'):
            if hasattr(defender, 'current_hp') and hasattr(defender, 'max_hp') and defender.max_hp > 0:
                hp_ratio = defender.current_hp / defender.max_hp
                low_hp_bonus = 1.0
                bonus_label = ""

                # HP 15% 이하: 3.0배
                if hp_ratio <= 0.15:
                    low_hp_bonus = skill.metadata.get('low_hp_15', 3.0)
                    bonus_label = "극한 처형"
                # HP 30% 이하: 2.5배
                elif hp_ratio <= 0.30:
                    low_hp_bonus = skill.metadata.get('low_hp_30', 2.5)
                    bonus_label = "치명 처형"
                # HP 50% 이하: 1.5배
                elif hp_ratio <= 0.50:
                    low_hp_bonus = skill.metadata.get('low_hp_50', 1.5)
                    bonus_label = "약화 처형"

                if low_hp_bonus > 1.0:
                    hp_multiplier *= low_hp_bonus
                    self.logger.info(f"[{bonus_label}] {defender.name} HP {hp_ratio*100:.1f}% → 데미지 x{low_hp_bonus}")

        # 어둠기사 perfect_strike 효과: 완전충전 시 즉사/보스 추가 피해
        instant_kill_attempted = False
        if hasattr(attacker, 'gimmick_type') and attacker.gimmick_type == "charge_system":
            if hasattr(attacker, 'charge_gauge') and attacker.charge_gauge >= 100:
                # perfect_strike 특성 확인
                has_perfect_strike = any(
                    (t if isinstance(t, str) else t.get('id')) == 'perfect_strike'
                    for t in getattr(attacker, 'active_traits', [])
                )

                if has_perfect_strike:
                    is_boss = getattr(defender, 'is_boss', False)
                    if is_boss:
                        # 보스에게 50% 추가 피해
                        hp_multiplier *= 1.50
                        self.logger.info(f"[완벽한 일격] {attacker.name} 완전충전 → 보스에게 데미지 +50%")
                    else:
                        # 일반 몬스터 15% 즉사 확률
                        import random
                        if random.random() < 0.15:
                            instant_kill_attempted = True
                            self.logger.info(f"[완벽한 일격] {attacker.name} 완전충전 → {defender.name} 즉사!")

        # BREAK 상태 확인
        is_break = self.brave.is_broken(defender)

        # 즉사 효과 적용
        # 즉사 효과 적용
        if instant_kill_attempted:
            # 즉사: 현재 HP를 모두 제거
            if hasattr(defender, 'current_hp'):
                defender.current_hp = 0
            hp_result = {
                "hp_damage": 9999,
                "brv_consumed": attacker.current_brv,
                "is_break_bonus": is_break,
                "is_critical": False,
                "actual_gain": 0
            }
            attacker.current_brv = 0  # BRV 소비
        else:
            # HP 공격 적용 (BRV 소비 및 데미지 적용)
            # brave.hp_attack()이 take_damage()를 내부적으로 호출함
            hp_result = self.brave.hp_attack(attacker, defender, hp_multiplier)
            
            # [NEW] 데미지 이벤트 발행 (Life Steal 등 On-Hit 효과용)
            # brave.hp_attack 결과에 실제 입힌 데미지(hp_damage)가 포함됨
            if hp_result.get("hp_damage", 0) > 0:
                event_bus.publish(Events.COMBAT_DAMAGE_DEALT, {
                    "attacker": attacker,
                    "target": defender,
                    "damage": hp_result["hp_damage"],
                    "is_critical": hp_result.get("is_critical", False),
                    "damage_type": "physical"  # HP 공격은 기본적으로 물리로 취급
                })

        # HP 공격은 빗나감이 없으므로(BRV 0이면 0데미지지만 공격 자체는 성공) 항상 내구도 감소 시도
        if hasattr(attacker, 'degrade_equipment') and not kwargs.get('skip_degrade', False):
            attacker.degrade_equipment("weapon", 3)  # 3배 증가

        # HP 공격 후 BRV 0 확인 (안전장치)
        if attacker.current_brv != 0:
            self.logger.warning(f"[combat_manager] HP 공격 후 {attacker.name} BRV가 0이 아님 ({attacker.current_brv}), 강제 리셋")
            attacker.current_brv = 0

        # wound damage 계산 (BREAK 보너스)
        wound_damage = 0
        if is_break and hp_result["hp_damage"] > 0:
            wound_damage = int(hp_result["hp_damage"] * 0.2)  # 20% wound damage
            if hasattr(defender, "wound_damage"):
                defender.wound_damage += wound_damage

            # BREAK 당할 때 방어구/장신구 추가 내구도 감소 (심각한 피해)
            if hasattr(defender, 'degrade_equipment'):
                if defender.equipment.get("armor"):
                    defender.degrade_equipment("armor", 3)  # BREAK 시 방어구 +3 추가 감소
                if defender.equipment.get("accessory"):
                    defender.degrade_equipment("accessory", 2)  # BREAK 시 장신구 +2 추가 감소

        # 공격 후 방어 스택 초기화
        if hasattr(attacker, 'defend_stack_count') and attacker.defend_stack_count > 0:
            attacker.defend_stack_count = 0

        # lifesteal (흡혈) 효과 + 흡혈귀 특성 처리
        lifesteal_ratio = 0
        if skill and hasattr(skill, 'metadata') and skill.metadata.get('lifesteal'):
            lifesteal_ratio = skill.metadata['lifesteal']  # 0.3 = 30% 흡혈

        # sanguine_arts: 마법 공격 시 추가 흡혈 20%
        if hasattr(attacker, 'active_traits'):
            has_sanguine_arts = any(
                (t if isinstance(t, str) else t.get('id')) == 'sanguine_arts'
                for t in attacker.active_traits
            )
            if has_sanguine_arts and skill and hasattr(skill, 'metadata'):
                # 마법 스킬인지 확인 (damage_type이 magical이거나 magic 관련)
                is_magic_skill = skill.metadata.get('damage_type') == 'magical' or skill.metadata.get('magic_based', False)
                if is_magic_skill:
                    lifesteal_ratio += 0.20  # 추가 20% 흡혈
                    self.logger.debug(f"[혈기술] {attacker.name} 마법 공격 → 흡혈 +20%")

        if lifesteal_ratio > 0:
            heal_amount = int(hp_result["hp_damage"] * lifesteal_ratio)
            if heal_amount > 0:
                overflow_amount = 0  # 초과 흡혈량

                if hasattr(attacker, 'heal'):
                    actual_heal = attacker.heal(heal_amount)
                elif hasattr(attacker, 'current_hp') and hasattr(attacker, 'max_hp'):
                    actual_heal = min(heal_amount, attacker.max_hp - attacker.current_hp)
                    attacker.current_hp += actual_heal

                    # vitality_overflow: 흡혈 시 init_brv 복귀 + 초과 흡혈 → BRV 전환
                    has_vitality_overflow = any(
                        (t if isinstance(t, str) else t.get('id')) == 'vitality_overflow'
                        for t in getattr(attacker, 'active_traits', [])
                    )
                    if has_vitality_overflow and hasattr(attacker, 'current_brv') and hasattr(attacker, 'max_brv'):
                        # 1단계: HP 공격 후 init_brv로 먼저 복귀 (항상)
                        init_brv_val = getattr(attacker, 'init_brv', 0)
                        if attacker.current_brv < init_brv_val:
                            attacker.current_brv = init_brv_val
                        # 2단계: 초과 흡혈량(오버힐)을 BRV로 추가 전환
                        overflow_amount = heal_amount - actual_heal
                        if overflow_amount > 0:
                            brv_gain = min(overflow_amount, attacker.max_brv - attacker.current_brv)
                            if brv_gain > 0:
                                attacker.current_brv += brv_gain
                            self.logger.info(f"[생명력 과부하] {attacker.name} BRV→init({init_brv_val}) + 초과 흡혈 {overflow_amount} → BRV +{brv_gain}")
                        else:
                            self.logger.info(f"[생명력 과부하] {attacker.name} BRV→init({init_brv_val}) 복귀")
                else:
                    actual_heal = heal_amount

                if actual_heal > 0:
                    self.logger.info(f"[흡혈] {attacker.name} HP 회복: {actual_heal} (피해의 {lifesteal_ratio*100:.0f}%)")

                # blood_empowerment: 흡혈 성공 시 30% 확률로 버프
                if actual_heal > 0:
                    has_blood_empowerment = any(
                        (t if isinstance(t, str) else t.get('id')) == 'blood_empowerment'
                        for t in getattr(attacker, 'active_traits', [])
                    )
                    if has_blood_empowerment:
                        import random
                        if random.random() < 0.30:  # 30% 확률
                            # 공격력 +20%, 속도 +15% 버프 (3턴)
                            from src.combat.status_effects import StatusEffect, StatusType
                            attack_buff = StatusEffect(StatusType.ATTACK_UP, duration=3, value=0.20, source=attacker)
                            speed_buff = StatusEffect(StatusType.SPEED_UP, duration=3, value=0.15, source=attacker)
                            if hasattr(attacker, 'add_status_effect'):
                                attacker.add_status_effect(attack_buff)
                                attacker.add_status_effect(speed_buff)
                            self.logger.info(f"[혈액 강화] {attacker.name} 공격력 +20%, 속도 +15% (3턴)!")

        # heal_on_hit (타격 시 HP 회복)
        if skill and hasattr(skill, 'metadata') and skill.metadata.get('heal_on_hit'):
            heal_amount = skill.metadata['heal_on_hit']
            if hasattr(attacker, 'heal'):
                actual_heal = attacker.heal(heal_amount)
            elif hasattr(attacker, 'current_hp') and hasattr(attacker, 'max_hp'):
                actual_heal = min(heal_amount, attacker.max_hp - attacker.current_hp)
                attacker.current_hp += actual_heal
            else:
                actual_heal = heal_amount
            self.logger.info(f"[타격 회복] {attacker.name} HP +{actual_heal}")

        # mp_on_hit (타격 시 MP 회복)
        if skill and hasattr(skill, 'metadata') and skill.metadata.get('mp_on_hit'):
            mp_amount = skill.metadata['mp_on_hit']
            if hasattr(attacker, 'restore_mp'):
                actual_mp = attacker.restore_mp(mp_amount)
            elif hasattr(attacker, 'current_mp') and hasattr(attacker, 'max_mp'):
                actual_mp = min(mp_amount, attacker.max_mp - attacker.current_mp)
                attacker.current_mp += actual_mp
            else:
                actual_mp = mp_amount
            self.logger.info(f"[타격 회복] {attacker.name} MP +{actual_mp}")

        # brv_on_hit (타격 시 BRV 회복)
        if skill and hasattr(skill, 'metadata') and skill.metadata.get('brv_on_hit'):
            brv_amount = skill.metadata['brv_on_hit']
            if hasattr(attacker, 'current_brv') and hasattr(attacker, 'max_brv'):
                actual_brv = min(brv_amount, attacker.max_brv - attacker.current_brv)
                attacker.current_brv += actual_brv
                self.logger.info(f"[타격 회복] {attacker.name} BRV +{actual_brv}")

        # splash_damage (범위 피해) - 주변 적들에게 추가 피해
        if skill and hasattr(skill, 'metadata') and skill.metadata.get('splash_damage'):
            splash_ratio = skill.metadata.get('splash_damage', 0.5)  # 기본 50%
            splash_radius = skill.metadata.get('splash_radius', 999)  # 기본 전체

            all_enemies = self.enemies if attacker in self.allies else self.allies
            splash_targets = [e for e in all_enemies if e != defender and hasattr(e, 'is_alive') and e.is_alive]

            if splash_targets:
                splash_damage = int(hp_result["hp_damage"] * splash_ratio)
                for splash_target in splash_targets[:splash_radius]:  # 반경 제한
                    if hasattr(splash_target, 'take_damage'):
                        actual_damage = splash_target.take_damage(splash_damage)
                    elif hasattr(splash_target, 'current_hp'):
                        actual_damage = min(splash_damage, splash_target.current_hp)
                        splash_target.current_hp = max(0, splash_target.current_hp - actual_damage)
                    else:
                        actual_damage = splash_damage
                    self.logger.info(f"[범위 피해] {splash_target.name}에게 {actual_damage} 피해! (본 피해의 {splash_ratio*100:.0f}%)")

        # cleave (광역 베기) - 전방 적들에게 피해
        if skill and hasattr(skill, 'metadata') and skill.metadata.get('cleave'):
            cleave_ratio = skill.metadata.get('cleave', 0.6)  # 기본 60%
            cleave_targets = skill.metadata.get('cleave_targets', 2)  # 기본 2명

            all_enemies = self.enemies if attacker in self.allies else self.allies
            cleave_target_list = [e for e in all_enemies if e != defender and hasattr(e, 'is_alive') and e.is_alive]

            if cleave_target_list:
                cleave_damage = int(hp_result["hp_damage"] * cleave_ratio)
                for cleave_target in cleave_target_list[:cleave_targets]:
                    if hasattr(cleave_target, 'take_damage'):
                        actual_damage = cleave_target.take_damage(cleave_damage)
                    elif hasattr(cleave_target, 'current_hp'):
                        actual_damage = min(cleave_damage, cleave_target.current_hp)
                        cleave_target.current_hp = max(0, cleave_target.current_hp - actual_damage)
                    else:
                        actual_damage = cleave_damage
                    self.logger.info(f"[광역 베기] {cleave_target.name}에게 {actual_damage} 피해! (본 피해의 {cleave_ratio*100:.0f}%)")

        # chain_lightning (연쇄 공격) - 다음 대상으로 전파
        if skill and hasattr(skill, 'metadata') and skill.metadata.get('chain_lightning'):
            chain_ratio = skill.metadata.get('chain_lightning', 0.7)  # 기본 70%
            bounce_count = skill.metadata.get('bounce_count', 3)  # 기본 3회 연쇄

            all_enemies = self.enemies if attacker in self.allies else self.allies
            chain_targets = [e for e in all_enemies if e != defender and hasattr(e, 'is_alive') and e.is_alive]

            current_damage = hp_result["hp_damage"]
            hit_targets = [defender]  # 이미 맞은 대상

            for i in range(min(bounce_count, len(chain_targets))):
                # 아직 맞지 않은 대상 중 랜덤 선택
                available_targets = [t for t in chain_targets if t not in hit_targets]
                if not available_targets:
                    break

                import random
                chain_target = random.choice(available_targets)
                chain_damage = int(current_damage * chain_ratio)

                if chain_damage > 0:
                    if hasattr(chain_target, 'take_damage'):
                        actual_damage = chain_target.take_damage(chain_damage)
                    elif hasattr(chain_target, 'current_hp'):
                        actual_damage = min(chain_damage, chain_target.current_hp)
                        chain_target.current_hp = max(0, chain_target.current_hp - actual_damage)
                    else:
                        actual_damage = chain_damage
                    self.logger.info(f"[연쇄 번개] {chain_target.name}에게 {actual_damage} 피해! (연쇄 {i+1}회)")
                    hit_targets.append(chain_target)
                    current_damage = chain_damage  # 다음 연쇄는 더 약해짐

        # on_crit_effect (크리티컬 시 추가 효과)
        if skill and hasattr(skill, 'metadata') and skill.metadata.get('on_crit_effect') and hp_result.get('is_critical', False):
            crit_effect = skill.metadata.get('on_crit_effect')
            if isinstance(crit_effect, dict):
                effect_type = crit_effect.get('type', 'damage')
                effect_value = crit_effect.get('value', 1.0)
                
                if effect_type == 'damage':
                    # 추가 데미지
                    bonus_damage = int(hp_result["hp_damage"] * effect_value)
                    if hasattr(defender, 'take_damage'):
                        actual_damage = defender.take_damage(bonus_damage)
                    elif hasattr(defender, 'current_hp'):
                        actual_damage = min(bonus_damage, defender.current_hp)
                        defender.current_hp = max(0, defender.current_hp - actual_damage)
                    else:
                        actual_damage = bonus_damage
                    self.logger.info(f"[크리티컬 추가 효과] {defender.name}에게 {actual_damage} 추가 피해!")
                elif effect_type == 'stun':
                    # 기절 확률
                    import random
                    if random.random() < effect_value:
                        from src.combat.status_effects import StatusEffect, StatusType
                        stun = StatusEffect("기절", StatusType.STUN, duration=1, intensity=1.0)
                        if hasattr(defender, 'status_manager'):
                            defender.status_manager.add_status(stun)
                            self.logger.info(f"[크리티컬 기절] {defender.name} 기절!")
                elif effect_type == 'heal':
                    # HP 회복
                    heal_amount = int(hp_result["hp_damage"] * effect_value)
                    if hasattr(attacker, 'heal'):
                        actual_heal = attacker.heal(heal_amount)
                    else:
                        actual_heal = min(heal_amount, attacker.max_hp - attacker.current_hp) if hasattr(attacker, 'max_hp') else heal_amount
                        attacker.current_hp = min(attacker.max_hp, attacker.current_hp + actual_heal) if hasattr(attacker, 'max_hp') else attacker.current_hp + actual_heal
                    self.logger.info(f"[크리티컬 흡혈] {attacker.name} HP +{actual_heal}")

        # on_break_effect (브레이크 시 추가 효과)
        if skill and hasattr(skill, 'metadata') and skill.metadata.get('on_break_effect') and is_break:
            break_effect = skill.metadata.get('on_break_effect')
            if isinstance(break_effect, dict):
                effect_type = break_effect.get('type', 'damage')
                effect_value = break_effect.get('value', 0.5)
                
                if effect_type == 'damage':
                    # 추가 데미지
                    bonus_damage = int(hp_result["hp_damage"] * effect_value)
                    if hasattr(defender, 'take_damage'):
                        actual_damage = defender.take_damage(bonus_damage)
                    else:
                        actual_damage = min(bonus_damage, defender.current_hp) if hasattr(defender, 'current_hp') else bonus_damage
                        if hasattr(defender, 'current_hp'):
                            defender.current_hp = max(0, defender.current_hp - actual_damage)
                    self.logger.info(f"[브레이크 추가 효과] {defender.name}에게 {actual_damage} 추가 피해!")
                elif effect_type == 'brv_bonus':
                    # BRV 보너스 획득
                    brv_bonus = int(effect_value)
                    if hasattr(attacker, 'current_brv') and hasattr(attacker, 'max_brv'):
                        actual_brv = min(brv_bonus, attacker.max_brv - attacker.current_brv)
                        attacker.current_brv += actual_brv
                        self.logger.info(f"[브레이크 BRV 보너스] {attacker.name} BRV +{actual_brv}")

        # freeze_chance (빙결 확률)
        if skill and hasattr(skill, 'metadata') and skill.metadata.get('freeze_chance'):
            import random
            freeze_chance = skill.metadata['freeze_chance']
            freeze_duration = skill.metadata.get('freeze_duration', 1)
            if random.random() < freeze_chance:
                from src.combat.status_effects import StatusEffect, StatusType
                freeze = StatusEffect("빙결", StatusType.FREEZE, duration=min(freeze_duration, 2), intensity=1.0)
                if hasattr(defender, 'status_manager'):
                    defender.status_manager.add_status(freeze)
                    self.logger.info(f"[빙결] {defender.name} 빙결! ({freeze_chance*100:.0f}% 확률)")

        # blind_chance (실명 확률)
        if skill and hasattr(skill, 'metadata') and skill.metadata.get('blind_chance'):
            import random
            blind_chance = skill.metadata['blind_chance']
            blind_duration = skill.metadata.get('blind_duration', 2)
            if random.random() < blind_chance:
                from src.combat.status_effects import StatusEffect, StatusType
                blind = StatusEffect("실명", StatusType.BLIND, duration=blind_duration, intensity=1.0)
                if hasattr(defender, 'status_manager'):
                    defender.status_manager.add_status(blind)
                    self.logger.info(f"[실명] {defender.name} 실명! ({blind_chance*100:.0f}% 확률)")

        # silence_chance (침묵 확률)
        if skill and hasattr(skill, 'metadata') and skill.metadata.get('silence_chance'):
            import random
            silence_chance = skill.metadata['silence_chance']
            silence_duration = skill.metadata.get('silence_duration', 2)
            if random.random() < silence_chance:
                from src.combat.status_effects import StatusEffect, StatusType
                silence = StatusEffect("침묵", StatusType.SILENCE, duration=min(silence_duration, 2), intensity=1.0)
                if hasattr(defender, 'status_manager'):
                    defender.status_manager.add_status(silence)
                    self.logger.info(f"[침묵] {defender.name} 침묵! ({silence_chance*100:.0f}% 확률)")

        # slow_percent / slow_duration (둔화)
        if skill and hasattr(skill, 'metadata') and skill.metadata.get('slow_percent'):
            import random
            slow_chance = skill.metadata.get('slow_chance', 1.0)  # 기본 100%
            if random.random() < slow_chance:
                slow_percent = skill.metadata['slow_percent']
                slow_duration = skill.metadata.get('slow_duration', 2)
                from src.combat.status_effects import StatusEffect, StatusType
                slow = StatusEffect("둔화", StatusType.SLOW, duration=slow_duration, intensity=slow_percent)
                if hasattr(defender, 'status_manager'):
                    defender.status_manager.add_status(slow)
                    self.logger.info(f"[둔화] {defender.name} 속도 -{slow_percent*100:.0f}%! ({slow_duration}턴)")

        # 아군 공격 시 기믹 트리거 (지원사격 등) - trigger_gimmick이 True일 때만
        if trigger_gimmick and attacker in self.allies:
            from src.character.gimmick_updater import GimmickUpdater
            context = {"all_enemies": self.enemies, "is_hp_attack": True}
            GimmickUpdater.on_ally_attack(attacker, self.allies, target=defender, context=context)

        # 적 처치 확인 및 효과 적용 (battle_heal, battle_mp, bloodthirst 등)
        if hasattr(defender, 'current_hp') and defender.current_hp <= 0:
            if defender in self.enemies:
                # 적 처치 확인
                from src.character.trait_effects import get_trait_effect_manager
                trait_manager = get_trait_effect_manager()
                # 모든 아군에게 처치 효과 적용
                for ally in self.allies:
                    if hasattr(ally, 'is_alive') and ally.is_alive:
                        trait_manager.apply_on_kill_effects(ally, defender)
                        
                        # 용기사: 적 처치 시 용표 획득 (30% 확률)
                        if (hasattr(ally, 'gimmick_type') and ally.gimmick_type == "dragon_marks"):
                            import random
                            if random.random() < 0.3:  # 30% 확률
                                current_marks = getattr(ally, 'dragon_marks', 0)
                                max_marks = getattr(ally, 'max_dragon_marks', 3)
                                if current_marks < max_marks:
                                    ally.dragon_marks = min(current_marks + 1, max_marks)
                                    self.logger.info(f"{ally.name} 적 처치로 용표 획득! (현재: {ally.dragon_marks}/{max_marks})")

                        # 암흑기사: 적 처치 시 충전 획득
                        if (hasattr(ally, 'gimmick_type') and ally.gimmick_type == "charge_system"):
                            from src.character.gimmick_updater import GimmickUpdater
                            GimmickUpdater.on_kill_charge(ally)

                        # 처치 보너스 (bloodthirst) - 스택 누적
                        if hasattr(ally, 'active_traits'):
                            from src.character.trait_effects import TraitEffectType
                            for trait_data in ally.active_traits:
                                trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                                effects = trait_manager.get_trait_effects(trait_id)
                                for effect in effects:
                                    if effect.effect_type == TraitEffectType.KILL_BONUS:
                                        # 스택 누적
                                        stack_key = f"_kill_bonus_stacks_{trait_id}"
                                        current_stacks = getattr(ally, stack_key, 0)
                                        max_stacks = effect.metadata.get("max_stacks", 3) if effect.metadata else 3
                                        new_stacks = min(current_stacks + 1, max_stacks)
                                        setattr(ally, stack_key, new_stacks)
                                        
                                        # 공격력 증가 적용
                                        bonus_per_stack = effect.value  # 0.10 = 10% per stack
                                        total_bonus = bonus_per_stack * new_stacks
                                        from src.character.stats import Stats
                                        if hasattr(ally, 'stat_manager'):
                                            # 기존 보너스 제거 후 새 보너스 추가
                                            ally.stat_manager.remove_bonus(Stats.STRENGTH, f"kill_bonus_{trait_id}")
                                            ally.stat_manager.remove_bonus(Stats.MAGIC, f"kill_bonus_{trait_id}")
                                            bonus_atk = int(ally.stat_manager.get_value(Stats.STRENGTH, use_total=False) * total_bonus)
                                            bonus_mag = int(ally.stat_manager.get_value(Stats.MAGIC, use_total=False) * total_bonus)
                                            if bonus_atk > 0:
                                                ally.stat_manager.add_bonus(Stats.STRENGTH, f"kill_bonus_{trait_id}", bonus_atk)
                                            if bonus_mag > 0:
                                                ally.stat_manager.add_bonus(Stats.MAGIC, f"kill_bonus_{trait_id}", bonus_mag)
                                            
                                            self.logger.info(f"[{trait_id}] {ally.name} 처치 보너스: 스택 {new_stacks}/{max_stacks} → 공격력 +{int(total_bonus * 100)}%")

        return {
            "action": "hp_attack",
            "hp_damage": hp_result["hp_damage"],
            "wound_damage": wound_damage,
            "brv_consumed": hp_result["brv_consumed"],
            "is_break_bonus": is_break,
            "defend_stack_bonus": defend_stack_bonus
        }

    def _execute_brv_hp_attack(
        self,
        attacker: Any,
        defender: Any,
        skill: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """BRV + HP 복합 공격 실행"""
        # 1. BRV 공격 (기믹 트리거 안 함)
        brv_attack_result = self._execute_brv_attack(attacker, defender, skill, trigger_gimmick=False, **kwargs)

        # 2. HP 공격 (BRV가 있으면, 기믹 트리거 안 함, 내구도 중복 감소 방지)
        if attacker.current_brv > 0:
            hp_kwargs = kwargs.copy()
            hp_kwargs['skip_degrade'] = True
            hp_attack_result = self._execute_hp_attack(attacker, defender, skill, trigger_gimmick=False, **hp_kwargs)
        else:
            hp_attack_result = {"hp_damage": 0, "wound_damage": 0, "brv_consumed": 0}

        # 아군 공격 시 기믹 트리거 (지원사격 등) - 복합 공격 전체에 대해 한 번만
        if attacker in self.allies:
            context = {"all_enemies": self.enemies, "is_hp_attack": True}
            GimmickUpdater.on_ally_attack(attacker, self.allies, target=defender, context=context)

        # 결과 병합
        combined_result = {
            "action": "brv_hp_attack",
            "is_combo": True,
            "is_break": brv_attack_result.get("is_break", False),  # 체인어빌리티 트리거용 (top-level)
        }

        # BRV 결과 추가
        for key in ["damage", "is_critical", "brv_stolen", "actual_gain", "is_break", "defend_stack_bonus"]:
            if key in brv_attack_result:
                combined_result[f"brv_{key}"] = brv_attack_result[key]

        # HP 결과 추가
        for key in ["hp_damage", "wound_damage", "brv_consumed", "is_break_bonus"]:
            if key in hp_attack_result:
                combined_result[key] = hp_attack_result[key]

        return combined_result

    def _execute_break_counterattack(self, actor: Any) -> None:
        """
        세피로스/카인 BREAK 해제 즉시 반격

        Args:
            actor: BREAK에서 회복된 세피로스 또는 카인
        """
        if not hasattr(actor, 'enemy_id') or actor.enemy_id not in ['sephiroth', 'abel_cain']:
            return

        # BREAK 반격 시 MP 회복 (반격용)
        if hasattr(actor, 'current_mp') and hasattr(actor, 'max_mp'):
            mp_restore = int(actor.max_mp * 0.5)  # 최대 MP의 50% 회복
            actor.current_mp = min(actor.current_mp + mp_restore, actor.max_mp)
            self.logger.info(f"[BREAK 반격] {actor.name} MP 회복: +{mp_restore} (현재: {actor.current_mp})")

        # 사용할 스킬 선택 (순수 BRV 광역 공격 최우선)
        counterattack_skill = None
        if actor.enemy_id == 'sephiroth':
            # 세피로스의 현재 페이즈 스킬 가져오기
            from src.combat.sephiroth_skills import SephirothSkillDatabase
            from src.combat.enemy_skills import SkillTargetType

            # 현재 페이즈 판단
            hp_percent = actor.current_hp / actor.max_hp if actor.max_hp > 0 else 0
            if hp_percent >= 0.66:
                phase_skills = SephirothSkillDatabase.get_phase_1_skills()
                phase_name = "페이즈 1"
            elif hp_percent >= 0.33:
                phase_skills = SephirothSkillDatabase.get_phase_2_skills()
                phase_name = "페이즈 2"
            else:
                phase_skills = SephirothSkillDatabase.get_phase_3_skills()
                phase_name = "페이즈 3"

            self.logger.debug(f"[BREAK 반격] 세피로스 {phase_name} (HP: {hp_percent*100:.1f}%)")

            # 1순위: 순수 BRV 광역 공격 (hp_attack=False)
            for skill in phase_skills:
                if hasattr(skill, 'target_type') and skill.target_type == SkillTargetType.ALL_ENEMIES and \
                   (not hasattr(skill, 'hp_attack') or not skill.hp_attack):
                    counterattack_skill = skill
                    self.logger.debug(f"[BREAK 반격] 순수 BRV 광역 공격 선택: {skill.name}")
                    break

            # 2순위: 광역 + HP 공격
            if not counterattack_skill:
                for skill in phase_skills:
                    if hasattr(skill, 'hp_attack') and skill.hp_attack and \
                       hasattr(skill, 'target_type') and skill.target_type == SkillTargetType.ALL_ENEMIES:
                        counterattack_skill = skill
                        self.logger.debug(f"[BREAK 반격] 광역 HP 공격 선택: {skill.name}")
                        break

            # 3순위: 일반 HP 공격
            if not counterattack_skill:
                for skill in phase_skills:
                    if hasattr(skill, 'hp_attack') and skill.hp_attack:
                        counterattack_skill = skill
                        self.logger.debug(f"[BREAK 반격] 단일 HP 공격 선택: {skill.name}")
                        break
        elif actor.enemy_id == 'abel_cain':
            # 카인의 강력한 공격 스킬 선택
            from src.combat.cain_skills import CainSkillDatabase
            from src.combat.enemy_skills import SkillTargetType
            all_skills = CainSkillDatabase.get_all_cain_skills()

            # 1순위: 순수 BRV 광역 공격 (hp_attack=False)
            for skill in all_skills:
                if hasattr(skill, 'target_type') and skill.target_type == SkillTargetType.ALL_ENEMIES and \
                   (not hasattr(skill, 'hp_attack') or not skill.hp_attack):
                    counterattack_skill = skill
                    self.logger.debug(f"[BREAK 반격] 순수 BRV 광역 공격 선택: {skill.name}")
                    break

            # 2순위: 광역 + HP 공격
            if not counterattack_skill:
                for skill in all_skills:
                    if hasattr(skill, 'hp_attack') and skill.hp_attack and \
                       hasattr(skill, 'target_type') and skill.target_type == SkillTargetType.ALL_ENEMIES:
                        counterattack_skill = skill
                        self.logger.debug(f"[BREAK 반격] 광역 HP 공격 선택: {skill.name}")
                        break

            # 3순위: 일반 HP 공격
            if not counterattack_skill:
                for skill in all_skills:
                    if hasattr(skill, 'hp_attack') and skill.hp_attack:
                        counterattack_skill = skill
                        self.logger.debug(f"[BREAK 반격] 단일 HP 공격 선택: {skill.name}")
                        break

        if not counterattack_skill:
            self.logger.warning(f"{actor.name}: BREAK 반격용 스킬을 찾을 수 없음")
            return

        # 타겟 선택 (광역이면 전체, 단일이면 랜덤)
        alive_players = [p for p in self.allies if hasattr(p, 'is_alive') and p.is_alive]
        if not alive_players:
            return

        import random
        from src.combat.enemy_skills import SkillTargetType

        if hasattr(counterattack_skill, 'target_type') and counterattack_skill.target_type == SkillTargetType.ALL_ENEMIES:
            target = alive_players  # 광역 공격: 전체 타겟
        else:
            target = random.choice(alive_players)  # 단일 공격: 랜덤 타겟

        # BREAK 반격 대사
        from src.combat.boss_dialogue import get_boss_dialogue
        boss_dialogue = get_boss_dialogue()
        dialogue = boss_dialogue.get_dialogue(actor.enemy_id, "break_counterattack")
        if dialogue:
            boss_dialogue.print_dialogue(self.logger, dialogue, combat_ui=getattr(self, 'combat_ui', None))

        self.logger.info(f"[BREAK 반격] {actor.name}이(가) {counterattack_skill.name}으로 반격!")

        # 스킬 즉시 실행
        try:
            skill_result = self._execute_skill(actor, target, counterattack_skill)
            if skill_result:
                self.logger.info(f"BREAK 반격 성공: {skill_result}")
        except Exception as e:
            self.logger.error(f"BREAK 반격 실행 실패: {e}")

    def _execute_cain_preemptive_strike(self, cain: Any) -> None:
        """
        카인 전투 시작 시 선제공격

        가장 방어력이 높은 아군을 BREAK시키고 강한 일격을 가합니다.

        Args:
            cain: 카인 객체
        """
        # 살아있는 아군 중 방어력 + 마법방어력이 가장 높은 대상 선택
        alive_allies = [a for a in self.allies if getattr(a, 'is_alive', True)]
        if not alive_allies:
            return

        # 방어력 + 마법방어력 합산으로 정렬
        def get_total_defense(character):
            defense = getattr(character, 'defense', 0)
            spirit = getattr(character, 'spirit', 0)
            return defense + spirit

        target = max(alive_allies, key=get_total_defense)

        self.logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        self.logger.info(f"\033[91m\"과거, 현재, 미래... 모든 시간의 끝에서, 네가 나의 종착점이 되어라.\"\033[0m")
        self.logger.info(f"카인이 전투 시작과 동시에 선제공격을 가한다!")
        self.logger.info(f"대상: {target.name} (방어력: {target.defense}, 마법방어력: {target.spirit})")
        self.logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # 1. 대상의 BRV를 0으로 (강제 BREAK)
        old_brv = target.current_brv
        target.current_brv = 0
        target.is_broken = True
        target.break_turn_count = 0

        self.logger.info(f"[카인 선제공격] {target.name}의 BRV 0으로! (이전: {old_brv}) - BREAK!")

        # BREAK 효과음
        from src.audio import play_sfx
        play_sfx("combat", "break")

        # 2. 강한 일격 (BRV 100% + HP 공격)
        # 카인의 현재 BRV를 매우 높게 설정 (강력한 일격용)
        preemptive_brv = int(cain.max_brv * 1.5)  # MAX BRV의 150%
        cain.current_brv = preemptive_brv

        self.logger.info(f"[카인 선제공격] 카인 BRV 충전: {preemptive_brv}")

        # HP 공격 (BREAK 보너스 포함)
        hp_result = self.brave.hp_attack(
            attacker=cain,
            defender=target,
            brv_multiplier=2.0,  # 2배 배율로 강력하게
            damage_type="physical"
        )

        hp_damage = hp_result.get('hp_damage', 0)

        # HP를 1 밑으로 떨어뜨리지 않음 (선제공격은 즉사시키지 않음)
        if target.current_hp <= 0:
            target.current_hp = 1
            self.logger.info(f"[카인 선제공격] {target.name}에게 {hp_damage} HP 데미지!")
            self.logger.info(f"\033[91m\"죽음은 아직 아니다... 더 고통스러운 선택이 너를 기다린다.\"\033[0m")
            self.logger.info(f"{target.name} 남은 HP: {target.current_hp}/{target.max_hp} (최소 HP 1로 생존)")
        else:
            self.logger.info(f"[카인 선제공격] {target.name}에게 {hp_damage} HP 데미지!")
            self.logger.info(f"{target.name} 남은 HP: {target.current_hp}/{target.max_hp}")

        self.logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # 진동 효과
        from src.core.vibration_system import vibration_manager, VibrationPattern
        vibration_manager.vibrate(VibrationPattern.HEAVY_TAP)

    def _try_cain_judgment(self, cain: Any, context: Dict) -> bool:
        """
        카인의 '시간의 심판' 발동 시도
        
        조건 충족 시 랜덤 아군에게 강력한 일격
        """
        if not hasattr(self, 'boss_gimmick_system'):
            return False
        
        judgment = self.boss_gimmick_system.check_cain_judgment_trigger(
            cain, self.allies, context
        )
        
        if judgment:
            self.logger.info(f"━━━━━━ 시간의 심판 ━━━━━━")
            self.logger.info(f"\033[95m{judgment['message']}\033[0m")
            
            # SFX 재생
            from src.audio.audio_manager import play_sfx
            play_sfx("se", "Bell1")
            
            # UI에 표시
            ui = getattr(self, 'combat_ui', None)
            if ui and hasattr(ui, 'add_message'):
                ui.add_message(judgment['message'], (255, 200, 100))
            
            # 대상 선택 (랜덤 아군)
            alive_allies = [a for a in self.allies if getattr(a, 'is_alive', True)]
            if not alive_allies:
                return False
            
            import random
            target = random.choice(alive_allies)
            
            self.logger.info(f"[시간의 심판] 발동 이유: {judgment['trigger_reason']}")
            self.logger.info(f"[시간의 심판] 대상: {target.name}")
            
            # UI에 대상 표시
            if ui and hasattr(ui, 'add_message'):
                ui.add_message(f"[시간의 심판] 대상: {target.name}", (255, 150, 50))
            
            # BRV 축적 후 HP 공격
            cain.current_brv = int(cain.max_brv * judgment['damage_multiplier'])
            
            # HP 공격 실행
            hp_result = self.brave.hp_attack(
                attacker=cain,
                defender=target,
                brv_multiplier=1.0,
                damage_type="magical"
            )
            
            hp_damage = hp_result.get('hp_damage', 0)
            
            # 시간의 심판은 HP를 1 밑으로 내리지 않음 (죽지 않음)
            if target.current_hp <= 0:
                target.current_hp = 1
                target.is_alive = True  # 생존 보장
                self.logger.info(f"[시간의 심판] {target.name}에게 {hp_damage} 피해! (HP 1로 생존)")
                self.logger.info(f"「아직... 심판은 끝나지 않았다.」")
                if ui and hasattr(ui, 'add_message'):
                    ui.add_message(f"[시간의 심판] {target.name}에게 {hp_damage} 피해! (HP 1로 생존)", (255, 100, 100))
                    ui.add_message(f"「아직... 심판은 끝나지 않았다.」", (255, 200, 100))
            else:
                self.logger.info(f"[시간의 심판] {target.name}에게 {hp_damage} 피해!")
                if ui and hasattr(ui, 'add_message'):
                    ui.add_message(f"[시간의 심판] {target.name}에게 {hp_damage} 피해!", (255, 100, 100))
            
            # 추가 효과: ATB 감소
            if 'atb_reduce' in judgment.get('effects', {}):
                if hasattr(target, 'atb'):
                    reduce = judgment['effects']['atb_reduce']
                    target.atb *= (1 - reduce)
                    self.logger.info(f"[시간의 심판] {target.name} ATB {reduce*100:.0f}% 감소!")
            
            # 추가 효과: 둔화
            if 'slow_duration' in judgment.get('effects', {}):
                from src.combat.status_effects import StatusEffect, StatusType
                slow = StatusEffect("시간 속박", StatusType.SLOW, 
                                   duration=judgment['effects']['slow_duration'], 
                                   intensity=0.3)
                if hasattr(target, 'status_manager'):
                    target.status_manager.add_status(slow)
                    self.logger.info(f"[시간의 심판] {target.name} 둔화 {judgment['effects']['slow_duration']}턴!")
            
            self.logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━")
            
            # === 심판 후 낙인 대상 강제 변경 ===
            mark_result = self.boss_gimmick_system.update_cain_mark(cain, self.allies, force_change=True)
            if mark_result:
                self.logger.info(f"\033[94m{mark_result['message']}\033[0m")
                if ui and hasattr(ui, 'add_message'):
                    ui.add_message(mark_result['message'], (100, 200, 255))
                    ui.add_message(f"[시간의 낙인] 행동 시 HP 15% 피해, 30% 시간 정지", (150, 200, 255))
            
            # 진동
            from src.core.vibration_system import vibration_manager, VibrationPattern
            vibration_manager.vibrate(VibrationPattern.HEAVY_TAP)
            
            return True
        
        return False
    
    def _try_sephiroth_counter(self, sephiroth: Any, damage: int, attacker: Any) -> bool:
        """
        세피로스의 광기 카운터 발동 시도
        
        피해를 받을 때 스택 증가, 조건 충족 시 반격
        """
        if not hasattr(self, 'boss_gimmick_system'):
            return False
        
        # 광기 스택 증가 전 값 저장
        prev_stack = self.boss_gimmick_system.sephiroth_counter_stack
        
        counter = self.boss_gimmick_system.on_sephiroth_damaged(sephiroth, damage, attacker)
        
        # UI에 스택 표시
        ui = getattr(self, 'combat_ui', None)
        current_stack = self.boss_gimmick_system.sephiroth_counter_stack
        if ui and hasattr(ui, 'add_message') and current_stack > 0:
            ui.add_message(f"[광기] 스택 {current_stack}/3", (255, 150, 100))
        
        if counter:
            self.logger.info(f"━━━━━━ {counter['skill_name']} ━━━━━━")
            self.logger.info(f"\033[91m{counter['message']}\033[0m")
            
            # UI에 반격 표시
            if ui and hasattr(ui, 'add_message'):
                ui.add_message(counter['message'], (255, 50, 50))
                ui.add_message(f"[{counter['skill_name']}] 반격!", (255, 100, 100))
            
            target = counter['target']
            
            # BRV 축적
            sephiroth.current_brv = int(sephiroth.max_brv * counter['damage_multiplier'])
            
            if counter['is_hp_attack']:
                # HP 공격
                hp_result = self.brave.hp_attack(
                    attacker=sephiroth,
                    defender=target,
                    brv_multiplier=1.0,
                    damage_type="physical"
                )
                hp_damage = hp_result.get('hp_damage', 0)
                self.logger.info(f"[{counter['skill_name']}] {target.name}에게 {hp_damage} HP 피해!")
            else:
                # BRV 공격
                brv_result = self.brave.brv_attack(
                    attacker=sephiroth,
                    defender=target,
                    brv_damage=sephiroth.current_brv
                )
                self.logger.info(f"[{counter['skill_name']}] {target.name}에게 {brv_result.get('brv_stolen', 0)} BRV 피해!")
            
            # 추가 효과: 방어력 감소
            if 'defense_down' in counter.get('effects', {}):
                from src.combat.status_effects import StatusEffect, StatusType
                debuff = StatusEffect("어둠의 침식", StatusType.DEFENSE_DOWN,
                                     duration=counter['effects'].get('duration', 2),
                                     intensity=counter['effects']['defense_down'])
                if hasattr(target, 'status_manager'):
                    target.status_manager.add_status(debuff)
                    self.logger.info(f"[{counter['skill_name']}] {target.name} 방어력 감소!")
            
            self.logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━")
            
            # 진동
            from src.core.vibration_system import vibration_manager, VibrationPattern
            vibration_manager.vibrate(VibrationPattern.MEDIUM_TAP)
            
            return True
        
        return False
    
    def _check_sephiroth_gimmick(self, target: Any, damage: int, attacker: Any):
        """
        세피로스에게 피해를 입힐 때 기믹 체크
        - 광기 스택 증가
        - 공유 고통 발동
        """
        if not hasattr(self, 'boss_gimmick_system'):
            return
        
        target_id = getattr(target, 'enemy_id', None)
        if target_id != 'sephiroth' or damage <= 0:
            return
        
        self.logger.debug(f"[세피로스 기믹] 피격! 피해량: {damage}, 공격자: {attacker.name}")
        
        # 광기 카운터 (스택 증가 + 반격)
        self._try_sephiroth_counter(target, damage, attacker)
        
        # 공유 고통 체크
        gimmick = self.boss_gimmick_system
        marked_target = gimmick.sephiroth_marked_target
        is_marked = gimmick.is_marked(attacker)
        self.logger.debug(f"[공유 고통 체크] 공격자: {attacker.name}, 표식 대상: {marked_target.name if marked_target else 'None'}, 표식 여부: {is_marked}")
        
        if is_marked:
            shared_result = gimmick.check_shared_pain(attacker, damage, self.allies)
            if shared_result:
                self.logger.info(f"\033[91m{shared_result['message']}\033[0m")
                ui = getattr(self, 'combat_ui', None)
                if ui and hasattr(ui, 'add_message'):
                    ui.add_message(shared_result['message'], (255, 100, 100))
                    total_shared = sum(d['damage'] for d in shared_result['damaged_allies'])
                    ui.add_message(f"[공유 고통] 아군 전체 {total_shared} 피해!", (255, 50, 50))
    
    def on_ally_healed(self, healer: Any, target: Any, heal_amount: int):
        """아군 회복 시 호출 (카인 기믹 트리거용)"""
        # 카인 전투 중인지 확인
        cain = next((e for e in self.enemies if getattr(e, 'enemy_id', None) == "abel_cain"), None)
        if cain and getattr(cain, 'is_alive', False):
            # HP 70% 이상 회복 체크
            hp_ratio = target.current_hp / max(1, target.max_hp)
            context = {
                'ally_healed': True,
                'ally_hp_recovered_above_70': hp_ratio >= 0.7,
                'turn_count': self.turn_count
            }
            self._try_cain_judgment(cain, context)

    def _execute_skill(
        self,
        actor: Any,
        target: Optional[Any] = None,
        skill: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """스킬 실행"""
        if not skill:
            return {"action": "skill", "error": "no_skill"}

        # 스킬 사용 시 장비 내구도 감소 (강력한 스킬일수록 더 많이 소모)
        if hasattr(actor, 'degrade_equipment'):
            # 무기 내구도 감소 (공격/마법 스킬)
            if hasattr(skill, 'effects') and skill.effects:
                # 데미지 스킬이면 무기 내구도 감소
                from src.character.skills.effects.damage_effect import DamageEffect
                has_damage = any(isinstance(effect, DamageEffect) for effect in skill.effects)
                if has_damage:
                    actor.degrade_equipment("weapon", 1)  # 스킬 사용 시 기본 1 감소

            # 장신구 내구도 감소 (모든 스킬 사용 시 소량)
            if actor.equipment.get("accessory"):
                actor.degrade_equipment("accessory", 1)  # 마나 소모 시 장신구도 소모

        result = {
            "action": "skill",
            "skill_name": getattr(skill, "name", "Unknown"),
            "targets": []
        }

        # 스킬 실행 전 대상의 BREAK 상태 저장 (체인어빌리티 트리거 감지용)
        target_was_broken_before = self.brave.is_broken(target) if target else True

        # 적 스킬인지 확인
        try:
            from src.combat.enemy_skills import EnemySkill, SkillTargetType

            if isinstance(skill, EnemySkill):
                # 적 스킬 실행
                result.update(self._execute_enemy_skill(actor, target, skill, **kwargs))
                # 적 스킬로 아군 피해 시 연계스킬 트리거
                if result.get("success", True) and target and target in self.allies:
                    bond_checks = self.check_bond_skills("ally_damaged", target)
                    if bond_checks:
                        bond_results = []
                        for br in bond_checks:
                            bond_results.append(self.execute_bond_skill(br, target))
                        result["bond_skill_results"] = bond_results
                return result
        except ImportError as e:
            # EnemySkill이 없으면 일반 스킬 시스템 사용
            self.logger.debug(f"적 스킬 시스템 미사용: {e}")

        # 팀워크 스킬인지 확인
        if hasattr(skill, 'is_teamwork_skill') and skill.is_teamwork_skill:
            # 연쇄 시작 여부 확인
            is_chain_start = not (self.party and self.party.chain_active)
            success, extra_msg = self.execute_teamwork_skill(actor, skill, target, is_chain_start)
            if success:
                result["success"] = True
                result["message"] = f"{actor.name}이(가) {skill.name} 사용! {extra_msg}"
            else:
                result["success"] = False
                result["error"] = "팀워크 스킬 실행 실패"
            return result

        # 가능성 시스템 스킬 처리 (시간술사)
        if hasattr(skill, 'metadata') and skill.metadata.get('possibility_system'):
            return self._execute_possibility_skill(actor, target, skill, **kwargs)

        # 일반 스킬 실행 (플레이어 스킬)
        from src.character.skills.skill_manager import get_skill_manager
        skill_manager = get_skill_manager()

        # 스킬 ID 확인
        skill_id = getattr(skill, 'skill_id', None)
        if not skill_id:
            self.logger.error(f"스킬 ID가 없습니다: {skill}, actor={actor.name}")
            return {
                "action": "skill",
                "success": False,
                "error": "스킬 ID가 없습니다",
                "skill_name": getattr(skill, "name", "Unknown")
            }

        # 스킬이 등록되어 있는지 확인
        registered_skill = skill_manager.get_skill(skill_id)
        if not registered_skill:
            self.logger.error(f"스킬이 등록되지 않았습니다: {skill_id}, actor={actor.name}")
            # 스킬을 다시 찾아보기 (skill_ids에서 직접 가져오기)
            if hasattr(actor, 'skill_ids') and skill_id in actor.skill_ids:
                # 스킬이 actor의 skill_ids에 있지만 등록되지 않은 경우
                # fallback: 스킬 객체를 직접 실행 (방어 로직)
                self.logger.warning(f"스킬 {skill_id}가 등록되지 않았지만 actor의 skill_ids에 있습니다. 스킬을 직접 실행합니다.")
                # skill 객체를 직접 실행
                if hasattr(skill, 'execute'):
                    # Skill 객체를 직접 실행
                    all_enemies = self.enemies if actor in self.allies else self.allies
                    all_allies = self.allies if actor in self.allies else self.enemies
                    context = {
                        "combat_manager": self,
                        "all_enemies": all_enemies,
                        "all_allies": all_allies,
                        "party": self.party,
                        "target": target,
                        "skill_id": skill_id,  # 스킬 ID 추가
                    }
                    if hasattr(skill, "metadata") and "_selected_choice" in skill.metadata:
                        context["selected_choice"] = skill.metadata.get("_selected_choice")
                        context["selected_choice_name"] = skill.metadata.get("_selected_choice_name")
                    skill_result = skill.execute(actor, target, context)
                    if hasattr(skill, "metadata"):
                        skill.metadata.pop("_selected_choice", None)
                        skill.metadata.pop("_selected_choice_name", None)
                else:
                    return {
                        "action": "skill",
                        "success": False,
                        "error": f"스킬 없음: {skill_id}",
                        "skill_name": getattr(skill, "name", "Unknown")
                    }
            else:
                return {
                    "action": "skill",
                    "success": False,
                    "error": f"스킬 없음: {skill_id}",
                    "skill_name": getattr(skill, "name", "Unknown")
                }
        else:
            # context에 모든 적 정보 추가 (AOE 효과를 위해)
            all_enemies = self.enemies if actor in self.allies else self.allies

            # revival 스킬인지 확인
            from src.multiplayer.skill_revival_handler import SkillRevivalHandler
            revival_handler = SkillRevivalHandler(None)  # revival_system은 None으로도 동작
            is_reviving = revival_handler.is_revival_skill(skill)

            # SkillManager를 통해 스킬 실행
            all_allies = self.allies if actor in self.allies else self.enemies
            context = {
                "combat_manager": self,
                "all_enemies": all_enemies,
                "all_allies": all_allies,
                "party": self.party,
                "target": target,
            }
            if is_reviving:
                context["revival"] = True

            # 선택형 스킬 선택 결과 전달
            if hasattr(skill, "metadata"):
                selected_choice = skill.metadata.get("_selected_choice")
                if selected_choice is not None:
                    context["selected_choice"] = selected_choice
                    if "_selected_choice_name" in skill.metadata:
                        context["selected_choice_name"] = skill.metadata.get("_selected_choice_name")

            # 기믹 업데이트 (스킬 사용) - 스킬 실행 전에 호출하여 카드 효과 등이 데미지에 적용되도록 함
            GimmickUpdater.on_skill_use(actor, skill, context)

            skill_result = skill_manager.execute_skill(
                skill_id,
                actor,
                target,
                context=context
            )

            # 선택형 스킬 상태 정리 (글로벌 객체 오염 방지)
            if hasattr(skill, "metadata"):
                skill.metadata.pop("_selected_choice", None)
                skill.metadata.pop("_selected_choice_name", None)

        if skill_result.success:
            result["success"] = True
            result["message"] = skill_result.message

            # ISSUE-003: 스킬 효과 상세 로그 출력
            self.logger.info(f"[스킬 효과] {skill_result.message}")

            # 아군이 스킬을 사용했을 때 마지막 사용 스킬 저장 (시간술사 운명 복제용)
            if actor in self.allies:
                actor._last_used_skill = skill
                self.logger.debug(f"[운명 복제] {actor.name}의 마지막 스킬 저장: {skill.name}")

            # 캐스팅이 시작된 경우 (시전 시작 메시지인 경우) 추가 처리를 하지 않음
            # 실제 스킬 효과는 캐스팅 완료 후 _process_completed_casts에서 처리됨
            is_casting_started = "시전 시작" in skill_result.message or "cast" in skill_result.message.lower()

            if is_casting_started:
                # 캐스팅 시작만 처리하고 스킬 효과는 나중에 처리
                return result

            # 기믹 업데이트는 스킬 실행 전에 이미 호출됨 (카드 효과 등)

            # 공격 스킬 사용 시 기믹 트리거 (지원사격 등) - 캐스팅이 아닌 즉시 실행 스킬만
            if actor in self.allies and target:
                # 스킬에 데미지 효과가 있는지 확인
                has_damage = False
                if hasattr(skill, 'effects'):
                    from src.character.skills.effects.damage_effect import DamageEffect
                    has_damage = any(isinstance(effect, DamageEffect) for effect in skill.effects)

                # 데미지 효과가 있으면 공격 스킬로 간주하고 on_ally_attack 호출
                if has_damage:
                    GimmickUpdater.on_ally_attack(actor, self.allies, target=target, context=context)

            # 해적: 보물 획득 스킬 처리
            if hasattr(skill, 'metadata') and skill.metadata.get('treasure_skill'):
                treasure_chance = skill.metadata.get('treasure_steal_chance', 0)
                if treasure_chance > 0:
                    import random
                    from src.character.skills.job_skills.pirate_skills import TREASURE_TYPES
                    if random.random() < treasure_chance:
                        # 보물 획득
                        if not hasattr(actor, 'treasure_inventory'):
                            actor.treasure_inventory = []

                        max_treasure = getattr(actor, 'max_treasure', 3)
                        if len(actor.treasure_inventory) < max_treasure:
                            # 가중치 기반 랜덤 보물 선택
                            treasure_ids = list(TREASURE_TYPES.keys())
                            weights = [TREASURE_TYPES[tid]["weight"] for tid in treasure_ids]
                            selected_treasure_id = random.choices(treasure_ids, weights=weights, k=1)[0]
                            
                            actor.treasure_inventory.append(selected_treasure_id)
                            treasure_name = TREASURE_TYPES[selected_treasure_id]["name"]
                            
                            self.logger.info(f"[해적] {actor.name}이(가) {treasure_name}을(를) 훔쳤다! (총: {len(actor.treasure_inventory)}개)")
                            if hasattr(self, 'add_message'):
                                self.add_message(f"{actor.name}이(가) {treasure_name}을(를) 획득! ({len(actor.treasure_inventory)}/{max_treasure})")

            # 어둠기사 explosive_power 특성: 충전 75% 이상에서 스킬 사용 시 충격파
            if hasattr(actor, 'gimmick_type') and actor.gimmick_type == "charge_system":
                if hasattr(skill, 'metadata') and skill.metadata.get('charge_cost', 0) > 0:
                    # 충전을 소모하는 스킬인지 확인
                    charge_cost = skill.metadata.get('charge_cost', 0)
                    if charge_cost > 0:
                        # 특성 확인
                        has_explosive_power = any(
                            (t if isinstance(t, str) else t.get('id')) == 'explosive_power'
                            for t in getattr(actor, 'active_traits', [])
                        )

                        if has_explosive_power:
                            # 스킬 사용 전 충전량 확인 (75% 이상이었는지)
                            # 충전은 이미 소모되었으므로, charge_cost + 현재 충전량으로 계산
                            charge_before_use = getattr(actor, 'charge_gauge', 0) + charge_cost
                            if charge_before_use >= 75:
                                # 주변 적들에게 충격파 피해 (소모한 충전량 비례)
                                # 공격력의 50~100% (충전 75%: 50%, 100%: 100%)
                                damage_ratio = 0.5 + (charge_before_use - 75) / 25 * 0.5
                                damage_ratio = min(1.0, damage_ratio)

                                all_enemies = self.enemies if actor in self.allies else self.allies
                                splash_targets = [e for e in all_enemies if e != target and hasattr(e, 'is_alive') and e.is_alive]

                                if splash_targets:
                                    from src.character.stats import Stats
                                    base_attack = actor.stat_manager.get_value(Stats.STRENGTH) if hasattr(actor, 'stat_manager') else getattr(actor, 'physical_attack', 50)
                                    splash_damage = int(base_attack * damage_ratio)

                                    for splash_target in splash_targets:
                                        # 방어력 적용
                                        defense = splash_target.stat_manager.get_value(Stats.DEFENSE) if hasattr(splash_target, 'stat_manager') else getattr(splash_target, 'physical_defense', 30)
                                        final_damage = max(1, splash_damage - defense // 2)

                                        # 데미지 적용 (take_damage 메서드 사용하여 이벤트 핸들러 등 시스템 통합)
                                        if hasattr(splash_target, 'take_damage'):
                                            actual_damage = splash_target.take_damage(final_damage)
                                            self.logger.info(f"[폭발적 힘] {actor.name}의 충격파 → {splash_target.name}에게 {actual_damage} 피해!")
                                        elif hasattr(splash_target, 'current_hp'):
                                            # fallback: take_damage가 없는 경우 직접 HP 수정
                                            actual_damage = min(final_damage, splash_target.current_hp)
                                            splash_target.current_hp = max(0, splash_target.current_hp - actual_damage)
                                            self.logger.info(f"[폭발적 힘] {actor.name}의 충격파 → {splash_target.name}에게 {actual_damage} 피해!")
                                        else:
                                            # 피해를 적용할 수 없는 대상 - 경고만 출력
                                            self.logger.warning(f"[폭발적 힘] {splash_target.name}에게 피해를 적용할 수 없습니다 (take_damage/current_hp 없음)")

            # 스킬 메타데이터: stun_chance (기절 확률)
            if target and hasattr(skill, 'metadata') and skill.metadata.get('stun_chance'):
                import random
                stun_chance = skill.metadata['stun_chance']
                if random.random() < stun_chance:
                    # 기절 상태 적용 (1턴)
                    from src.combat.status_effects import StatusEffect, StatusType
                    stun_effect = StatusEffect(StatusType.STUN, duration=1, source=actor)
                    if hasattr(target, 'add_status_effect'):
                        target.add_status_effect(stun_effect)
                        self.logger.info(f"[{skill.name}] {target.name} 기절! (확률 {stun_chance*100:.0f}%)")
            
            # 궁수 궁극기: 모든 아군에게 마킹 적용 (mark_all 메타데이터)
            if hasattr(skill, 'metadata') and skill.metadata.get('mark_all') and actor in self.allies:
                # 스킬 효과 실행 후 actor에서 설정된 값 가져오기
                arrow_type = getattr(actor, 'ultimate_arrow_type', 'explosive')
                shots = getattr(actor, 'mark_shots_ultimate', 5)
                
                # 모든 아군에게 폭발 화살 마킹 적용
                for ally in self.allies:
                    if hasattr(ally, 'is_alive') and ally.is_alive and ally != actor:
                        # 폭발 화살 마킹 슬롯 추가
                        mark_slot_field = f"mark_slot_{arrow_type}"
                        current_slots = getattr(ally, mark_slot_field, 0)
                        setattr(ally, mark_slot_field, min(3, current_slots + 1))
                        
                        # 지원 횟수 설정
                        mark_shots_field = f"mark_shots_{arrow_type}"
                        setattr(ally, mark_shots_field, shots)
                        
                        self.logger.info(f"[{skill.name}] {ally.name}에게 {arrow_type} 화살 마킹 적용 ({shots}회 지원)")
        else:
            result["success"] = False
            result["error"] = skill_result.message

        # 스킬로 인한 BREAK 감지 (체인어빌리티 트리거용)
        if target and result.get("success") and not target_was_broken_before and self.brave.is_broken(target):
            result["is_break"] = True
            self.logger.info(f"[스킬 BREAK] {skill.name}으로 {target.name} BREAK 발생!")

        return result

    def _execute_possibility_skill(
        self,
        actor: Any,
        target: Optional[Any] = None,
        skill: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """시간술사 가능성 시스템 스킬 실행"""
        from src.character.gimmick_updater import GimmickUpdater
        from src.character.skills.skill_manager import get_skill_manager
        
        result = {
            "action": "skill",
            "skill_name": getattr(skill, "name", "Unknown"),
            "success": False,
            "targets": []
        }
        
        action = skill.metadata.get('action', '')
        power_ratio = skill.metadata.get('power_ratio', 1.0)
        slots = GimmickUpdater.get_possibility_slots(actor)
        
        # 최소 가능성 개수 확인
        min_required = skill.metadata.get('min_possibilities', 0)
        if min_required > 0 and len(slots) < min_required:
            result["error"] = f"가능성 {min_required}개 이상 필요 (현재: {len(slots)}개)"
            return result
            
        skill_manager = get_skill_manager()
        all_enemies = self.enemies if actor in self.allies else self.allies
        all_allies = self.allies if actor in self.allies else self.enemies
        context = {"combat_manager": self, "all_enemies": all_enemies, "all_allies": all_allies, "party": self.party}

        def _resolve_possibility_target(stored_skill, default_target):
            """해방된 가능성 스킬의 target_type에 따라 적절한 타깃을 결정"""
            st_type = getattr(stored_skill, 'target_type', 'single_enemy')
            if st_type in ("ally", "single_ally"):
                # 아군 대상 스킬: HP가 가장 낮은 아군 자동 선택
                alive_allies = [a for a in all_allies if getattr(a, 'is_alive', True) and getattr(a, 'current_hp', 0) > 0]
                if alive_allies:
                    return min(alive_allies, key=lambda a: getattr(a, 'current_hp', 0) / max(getattr(a, 'max_hp', 1), 1))
                return actor
            elif st_type == "self":
                return actor
            elif st_type in ("all_allies", "party"):
                return all_allies
            elif st_type == "all_enemies":
                return all_enemies
            else:
                # single_enemy 또는 기타: 기존 타깃 사용
                return default_target or (all_enemies[0] if all_enemies else None)

        # 비용 체크 및 소모 (MP 등)
        # 일반 스킬 실행(execute_skill)을 거치지 않으므로 여기서 직접 처리해야 함
        can_use, reason = skill.can_use(actor, context)
        if not can_use:
            result["error"] = reason
            return result
            
        # 비용 소비
        if hasattr(skill, 'costs'):
            for cost in skill.costs:
                if not cost.consume(actor, context):
                    result["error"] = "비용 소비 실패"
                    return result
        
        executed_skills = []
        
        if action == "summon_single":
            # 가능성 소환: UI에서 선택한 슬롯 사용
            if not slots:
                result["error"] = "저장된 가능성이 없습니다"
                return result

            # UI에서 선택된 인덱스 가져오기
            selected_indices = skill.metadata.get('_selected_indices', [0])
            slot_index = selected_indices[0] if selected_indices else 0

            summon_result = GimmickUpdater.summon_possibility(actor, slot_index, context)
            if summon_result['success']:
                stored_skill_id = summon_result['skill_id']
                stored_power = summon_result['power_ratio']
                original_character = summon_result.get('original_character', None)

                # 원본 캐릭터가 있으면 그 캐릭터의 스탯/기믹 사용, 없으면 시간술사 사용
                skill_actor = original_character if original_character else actor

                # 저장된 스킬 실행
                stored_skill = skill_manager.get_skill(stored_skill_id)
                if stored_skill:
                    # 배율 적용하여 스킬 실행
                    context['power_multiplier'] = stored_power
                    context['time_mage_summoner'] = actor  # 시간술사 정보 (ATB용)
                    context['skip_cost'] = True  # 가능성 소환은 MP 무료 (저장된 스킬의 비용 건너뛰기)

                    # 스킬의 target_type에 따라 적절한 타깃 결정
                    resolved_target = _resolve_possibility_target(stored_skill, target)
                    skill_result = skill_manager.execute_skill(
                        stored_skill_id, skill_actor, resolved_target,
                        context=context
                    )
                    executed_skills.append({
                        "skill_name": stored_skill.name,
                        "power_ratio": stored_power,
                        "consumed": summon_result['consumed']
                    })

                    actor_display = f"{skill_actor.name}의 " if original_character else ""
                    result["success"] = True
                    result["message"] = f"{actor.name}이(가) 가능성 소환! → {actor_display}{stored_skill.name} ({int(stored_power*100)}% 위력)"
                else:
                    result["error"] = f"스킬을 찾을 수 없음: {stored_skill_id}"
            else:
                result["error"] = summon_result.get('error', '가능성 소환 실패')
                
        elif action == "summon_dual":
            # 시간선 교차: UI에서 선택한 2개 슬롯 발동
            if len(slots) < 2:
                result["error"] = "가능성 2개 이상 필요"
                return result

            # UI에서 선택된 인덱스 가져오기
            selected_indices = skill.metadata.get('_selected_indices', [0, 1])
            if len(selected_indices) < 2:
                selected_indices = [0, 1]

            crossing_result = GimmickUpdater.time_crossing(actor, selected_indices, context)
            messages = []
            for sr in crossing_result:
                if sr['success']:
                    stored_skill = skill_manager.get_skill(sr['skill_id'])
                    original_character = sr.get('original_character', None)
                    skill_actor = original_character if original_character else actor

                    if stored_skill:
                        context['power_multiplier'] = sr['power_ratio']
                        context['time_mage_summoner'] = actor  # 시간술사 정보
                        context['skip_cost'] = True  # 가능성 소환은 MP 무료

                        # 스킬의 target_type에 따라 적절한 타깃 결정
                        resolved_target = _resolve_possibility_target(stored_skill, target)
                        skill_manager.execute_skill(
                            sr['skill_id'], skill_actor, resolved_target,
                            context=context
                        )
                        actor_display = f"{skill_actor.name}의 " if original_character else ""
                        messages.append(f"{actor_display}{stored_skill.name} ({int(sr['power_ratio']*100)}%)")

            result["success"] = True
            result["message"] = f"{actor.name}이(가) 시간선 교차! → " + ", ".join(messages)
            
        elif action == "release_all":
            # 시간 폭풍: 모든 가능성 해방
            storm_result = GimmickUpdater.time_storm(actor, context)
            if storm_result['success']:
                messages = []
                for released in storm_result['released']:
                    stored_skill = skill_manager.get_skill(released['skill_id'])
                    original_character = released.get('original_character', None)
                    skill_actor = original_character if original_character else actor

                    if stored_skill:
                        context['power_multiplier'] = released['power_ratio']
                        context['time_mage_summoner'] = actor  # 시간술사 정보
                        context['skip_cost'] = True  # 가능성 소환은 MP 무료

                        # 스킬의 target_type에 따라 적절한 타깃 결정
                        resolved_target = _resolve_possibility_target(stored_skill, target)
                        skill_manager.execute_skill(
                            released['skill_id'], skill_actor, resolved_target,
                            context=context
                        )
                        actor_display = f"{skill_actor.name}의 " if original_character else ""
                        messages.append(f"{actor_display}{stored_skill.name}")

                bonus_msg = ""
                if storm_result['convergence_bonus']:
                    bonus_msg = f" (수렴 보너스 +{int(storm_result['total_damage_bonus']*100)}%!)"

                result["success"] = True
                result["message"] = f"{actor.name}이(가) 시간 폭풍! → " + ", ".join(messages) + bonus_msg
            else:
                result["error"] = storm_result.get('error', '시간 폭풍 실패')
                
        elif action == "copy_ally_skill":
            # 운명 복제
            if not target:
                result["error"] = "복제할 대상을 선택하세요"
                return result
            
            copy_result = GimmickUpdater.fate_copy(actor, target, context)
            if copy_result['success']:
                result["success"] = True
                result["message"] = f"{actor.name}이(가) {target.name}의 스킬을 복제! → {copy_result['copied_skill']}"
            else:
                result["error"] = copy_result.get('error', '운명 복제 실패')
                
        elif action == "overwrite_slot":
            # 운명 덮어쓰기: UI에서 선택한 슬롯 교체
            if not slots:
                result["error"] = "덮어쓸 슬롯이 없습니다"
                return result
            
            # UI에서 선택된 인덱스 가져오기
            selected_indices = skill.metadata.get('_selected_indices', [0])
            slot_index = selected_indices[0] if selected_indices else 0
            
            # 기본값: 타임 볼트로 덮어쓰기 (향후 UI에서 스킬 선택 추가 가능)
            new_skill_id = "time_mage_time_bolt"
            overwrite_result = GimmickUpdater.overwrite_fate(actor, slot_index, new_skill_id)
            if overwrite_result['success']:
                result["success"] = True
                result["message"] = f"{actor.name}이(가) 운명 덮어쓰기! {overwrite_result['old_skill']} → {overwrite_result['new_skill']}"
            else:
                result["error"] = overwrite_result.get('error', '운명 덮어쓰기 실패')
                
        elif action == "infinite_convergence":
            # 무한 수렴 (궁극기)
            storm_result = GimmickUpdater.time_storm(actor, context)
            messages = []
            
            # 1. 저장된 가능성 모두 발동
            if storm_result['success']:
                for released in storm_result['released']:
                    stored_skill = skill_manager.get_skill(released['skill_id'])
                    if stored_skill:
                        context['power_multiplier'] = power_ratio
                        context['skip_cost'] = True  # 가능성 소환은 MP 무료
                        # 스킬의 target_type에 따라 적절한 타깃 결정
                        resolved_target = _resolve_possibility_target(stored_skill, target)
                        skill_manager.execute_skill(
                            released['skill_id'], actor, resolved_target,
                            context=context
                        )
                        messages.append(stored_skill.name)

            # 2. 고정 스킬 연속 발동
            chain_skills = skill.metadata.get('chain_cast', [])
            for chain_skill_id in chain_skills:
                full_id = f"time_mage_{chain_skill_id}" if not chain_skill_id.startswith("time_mage_") else chain_skill_id
                chain_skill = skill_manager.get_skill(full_id)
                if chain_skill:
                    # 스킬의 target_type에 따라 적절한 타깃 결정
                    resolved_target = _resolve_possibility_target(chain_skill, target)

                    context['power_multiplier'] = power_ratio
                    context['skip_cost'] = True  # 무한 수렴 연쇄 발동은 MP 무료
                    skill_manager.execute_skill(
                        full_id, actor, resolved_target,
                        context=context
                    )
                    messages.append(chain_skill.name)
            
            # 3. 피니시 피해 (스킬 자체 효과 실행)
            if skill.effects:
                for effect in skill.effects:
                    effect.apply(actor, target or (all_enemies[0] if all_enemies else None), context)
            
            result["success"] = True
            result["message"] = f"{actor.name}이(가) 무한 수렴! → " + ", ".join(messages) + " → 피니시!"
        else:
            result["error"] = f"알 수 없는 가능성 액션: {action}"
        
        result["executed_skills"] = executed_skills
        return result

    def _execute_enemy_skill(
        self,
        actor: Any,
        target: Any,
        skill: 'EnemySkill',
        **kwargs
    ) -> Dict[str, Any]:
        """
        적 스킬 실행

        Args:
            actor: 스킬 사용자 (적)
            target: 대상 (단일 또는 리스트)
            skill: 적 스킬
            **kwargs: 추가 옵션

        Returns:
            실행 결과
        """
        from src.combat.enemy_skills import SkillTargetType

        result = {
            "action": "skill",
            "skill_name": getattr(skill, "name", "Unknown"),
            "success": True,
            "targets": [],
            "effects": []
        }

        # 스킬 사용 가능 여부 확인
        if not skill.can_use(actor):
            result["success"] = False
            # 실패 원인 파악
            if hasattr(actor, 'current_mp') and actor.current_mp < skill.mp_cost:
                result["error"] = f"MP 부족 (필요: {skill.mp_cost}, 현재: {actor.current_mp})"
            elif skill.current_cooldown > 0:
                result["error"] = f"쿨다운 중 ({skill.current_cooldown}턴 남음)"
            elif hasattr(actor, 'current_hp'):
                hp_percent = actor.current_hp / actor.max_hp if actor.max_hp > 0 else 0
                if hp_percent < skill.min_hp_percent:
                    result["error"] = f"HP 부족 (필요: {int(skill.min_hp_percent * 100)}% 이상)"
                elif hp_percent > skill.max_hp_percent:
                    result["error"] = f"HP 초과 (최대: {int(skill.max_hp_percent * 100)}% 이하)"
                elif actor.current_hp <= skill.hp_cost:
                    result["error"] = f"HP 코스트 부족 (필요: {skill.hp_cost})"
            else:
                result["error"] = "사용 불가"
            return result

        # MP/HP 코스트 지불
        # 마술사 '무한(8)' 카드 효과: MP 무료
        card_effects = getattr(actor, 'card_effects', {})
        free_cast = card_effects.pop('free_cast', False)  # 1회용, 소모
        
        if hasattr(actor, 'current_mp') and not free_cast:
            # 기본 1.5배 + 난이도별 추가 배율 적용
            base_mp_cost = skill.mp_cost * 1.5
            from src.core.difficulty import get_difficulty_system
            difficulty_system = get_difficulty_system()
            if difficulty_system:
                difficulty_mp_mult = difficulty_system.get_mp_cost_multiplier()
                final_mp_cost = int(base_mp_cost * difficulty_mp_mult)
            else:
                final_mp_cost = int(base_mp_cost)

            actor.current_mp = max(0, actor.current_mp - final_mp_cost)
        elif free_cast:
            self.logger.info(f"[마술사] {actor.name} 무한 효과! MP 소모 없음")
        if hasattr(actor, 'current_hp'):
            actor.current_hp = max(1, actor.current_hp - skill.hp_cost)
        
        # 쿨다운 활성화
        skill.activate_cooldown()

        # SFX 재생
        if hasattr(skill, 'sfx') and skill.sfx:
            play_sfx(skill.sfx[0], skill.sfx[1])
        else:
            # 기본 SFX (물리/마법 구분)
            if skill.is_magical:
                play_sfx("skill", "magic_cast")
            else:
                play_sfx("combat", "attack_physical")

        # 대상 결정
        targets = []
        if skill.target_type == SkillTargetType.SELF:
            targets = [actor]
        elif skill.target_type == SkillTargetType.ALL_ALLIES:
            # 아군 전체
            targets = [e for e in self.enemies if getattr(e, 'is_alive', True)]
        elif skill.target_type == SkillTargetType.ALL_ENEMIES:
            # 적 전체
            targets = [a for a in self.allies if getattr(a, 'is_alive', True)]
        elif skill.target_type == SkillTargetType.SINGLE_ALLY:
            # 아군 1명 (힐링/서포트 스킬)
            if target:
                if isinstance(target, list):
                    targets = target
                else:
                    targets = [target]
            else:
                # 타겟이 없으면 아군 중 랜덤 선택
                alive_allies = [e for e in self.enemies if getattr(e, 'is_alive', True)]
                if alive_allies:
                    import random
                    targets = [random.choice(alive_allies)]
        elif skill.target_type == SkillTargetType.RANDOM_ENEMY:
            # 랜덤 적 (타겟이 없으면 랜덤 선택)
            if target:
                if isinstance(target, list):
                    targets = target
                else:
                    targets = [target]
            else:
                alive_enemies = [a for a in self.allies if getattr(a, 'is_alive', True)]
                if alive_enemies:
                    import random
                    targets = [random.choice(alive_enemies)]
        elif target:
            # 단일 대상
            if isinstance(target, list):
                targets = target
            else:
                targets = [target]
        else:
            # 타겟이 필요한데 없으면 실패
            result["success"] = False
            result["error"] = "대상이 없습니다"
            return result

        # 대상이 없으면 실패
        if not targets:
            result["success"] = False
            result["error"] = "대상이 없습니다"
            return result
        
        # 각 대상에게 스킬 효과 적용
        for tgt in targets:
            target_result = {"target": getattr(tgt, 'name', 'Unknown')}

            # 데미지 적용
            if skill.damage > 0:
                # 스킬 특수 처리: 페로 카오스 (HP를 1로)
                if skill.skill_id == "heartless_angel":
                    if hasattr(tgt, 'current_hp'):
                        damage = tgt.current_hp - 1
                        tgt.current_hp = 1
                        target_result["hp_damage"] = damage
                        target_result["special"] = "hp_to_1"
                else:
                    # 일반 데미지 계산
                    # 계수 조정 (실행 시점에서 통일):
                    # - BRV 공격만 있는 경우: 2배로 조정
                    # - HP 공격만 있는 경우: 0.75배로 조정
                    # 보스 스킬 데미지 계산 (공격력/마법력 비례)
                    effective_multiplier = skill.damage_multiplier
                    brv_multiplier = skill.damage_multiplier
                    hp_multiplier = skill.damage_multiplier

                    if skill.hp_attack:
                        # HP 공격: 기본 배율 사용
                        effective_multiplier = skill.damage_multiplier
                        hp_multiplier = skill.damage_multiplier
                    else:
                        # BRV 공격: 2배 배율 적용 (BRV 시스템 강화)
                        brv_multiplier = skill.damage_multiplier * 2.0
                        effective_multiplier = brv_multiplier
                    
                    if skill.is_magical:
                        base_damage = int(skill.damage + actor.magic_attack * effective_multiplier)
                        defense = getattr(tgt, 'magic_defense', 0)
                    else:
                        base_damage = int(skill.damage + actor.physical_attack * effective_multiplier)
                        defense = getattr(tgt, 'physical_defense', 0)

                    # 방어력 적용
                    final_damage = max(1, base_damage - defense // 2)

                    # BRV 데미지 계산 (복합 스킬의 경우 BRV 계수는 2배 적용)
                    if not skill.hp_attack:
                        # BRV 데미지 계산 (공격력/마법력 비례)
                        if skill.is_magical:
                            brv_base_damage = int(actor.magic_attack * brv_multiplier)
                            brv_defense = getattr(tgt, 'magic_defense', 0)
                        else:
                            brv_base_damage = int(actor.physical_attack * brv_multiplier)
                            brv_defense = getattr(tgt, 'physical_defense', 0)

                        # 방어력 적용 (BRV 데미지)
                        brv_final_damage = max(1, brv_base_damage - brv_defense // 2)

                        if hasattr(tgt, 'current_brv'):
                            brv_dmg = min(brv_final_damage, tgt.current_brv)
                            tgt.current_brv = max(0, tgt.current_brv - brv_dmg)
                            target_result["brv_damage"] = brv_dmg

                    # HP 데미지 (HP 공격인 경우)
                    if skill.hp_attack:
                        if skill.is_magical:
                            hp_base_damage = int(actor.magic_attack * hp_multiplier)
                            hp_defense = getattr(tgt, 'magic_defense', 0)
                        else:
                            hp_base_damage = int(actor.physical_attack * hp_multiplier)
                            hp_defense = getattr(tgt, 'physical_defense', 0)
                        hp_final_damage = max(1, hp_base_damage - hp_defense // 2)
                        final_damage = hp_final_damage
                        if hasattr(tgt, 'take_damage'):
                            actual_damage = tgt.take_damage(final_damage)
                        elif hasattr(tgt, 'current_hp'):
                            actual_damage = min(final_damage, tgt.current_hp)
                            tgt.current_hp -= actual_damage
                        else:
                            actual_damage = final_damage
                        target_result["hp_damage"] = actual_damage
                        
                        # === 세피로스 기믹 체크 (스킬로 피해 입힐 때) ===
                        self._check_sephiroth_gimmick(tgt, actual_damage, actor)

            # 마법도둑 특수 처리: 타겟의 MP를 훔쳐서 사용자의 MP를 회복
            if skill.skill_id == "mana_steal":
                # 타겟의 MP를 소모
                mp_stolen = min(skill.heal_amount, getattr(tgt, 'current_mp', 0))
                if mp_stolen > 0 and hasattr(tgt, 'consume_mp'):
                    # 무한 루프 방지를 위해 이벤트 발행 없이 직접 소모
                    tgt.current_mp = max(0, tgt.current_mp - mp_stolen)
                    target_result["mp_stolen"] = mp_stolen
                    self.logger.info(f"[마법 도둑] {actor.name}이(가) {tgt.name}의 MP {mp_stolen}을(를) 훔쳤습니다!")
                
                # 사용자의 MP를 회복
                if hasattr(actor, 'restore_mp'):
                    actor.restore_mp(mp_stolen)
                elif hasattr(actor, 'current_mp') and hasattr(actor, 'max_mp'):
                    actor.current_mp = min(actor.current_mp + mp_stolen, actor.max_mp)
                target_result["mp_restored"] = mp_stolen
            
            # 힐링 적용 (마법도둑이 아닌 경우)
            elif skill.heal_amount > 0:
                # 데미지가 있는 스킬의 힐은 흡혈(drain) → 시전자(actor) 회복
                # 데미지가 없는 스킬의 힐은 순수 회복 → 대상(tgt) 회복
                heal_target = actor if skill.damage > 0 else tgt
                if hasattr(heal_target, 'heal'):
                    healed = heal_target.heal(skill.heal_amount)
                elif hasattr(heal_target, 'current_hp') and hasattr(heal_target, 'max_hp'):
                    healed = min(skill.heal_amount, heal_target.max_hp - heal_target.current_hp)
                    heal_target.current_hp += healed
                else:
                    healed = skill.heal_amount
                target_result["healing"] = healed

            # 버프 적용
            if skill.buff_stats:
                target_result["buffs"] = skill.buff_stats
                # 실제 버프 시스템 연동
                if hasattr(tgt, 'status_manager') or hasattr(tgt, 'status_effects'):
                    status_mgr = getattr(tgt, 'status_manager', None) or getattr(tgt, 'status_effects', None)
                    if isinstance(status_mgr, StatusManager):
                        for buff_name, buff_data in skill.buff_stats.items():
                            # buff_data는 딕셔너리 또는 값일 수 있음
                            if isinstance(buff_data, dict):
                                duration = buff_data.get('duration', 3)
                                intensity = buff_data.get('intensity', 1.0)
                            else:
                                duration = 3
                                intensity = float(buff_data) if isinstance(buff_data, (int, float)) else 1.0

                            # StatusType에서 찾기 (이름 매핑)
                            status_type = self._map_buff_to_status_type(buff_name)
                            if status_type:
                                buff_effect = StatusEffect(
                                    name=buff_name,
                                    status_type=status_type,
                                    duration=duration,
                                    intensity=intensity,
                                    source_id=getattr(actor, 'id', None)
                                )
                                status_mgr.add_status(buff_effect)

            # 디버프 적용
            if skill.debuff_stats:
                target_result["debuffs"] = skill.debuff_stats
                # 실제 디버프 시스템 연동
                if hasattr(tgt, 'status_manager') or hasattr(tgt, 'status_effects'):
                    status_mgr = getattr(tgt, 'status_manager', None) or getattr(tgt, 'status_effects', None)
                    if isinstance(status_mgr, StatusManager):
                        for debuff_name, debuff_data in skill.debuff_stats.items():
                            if isinstance(debuff_data, dict):
                                duration = debuff_data.get('duration', 3)
                                intensity = debuff_data.get('intensity', 1.0)
                            else:
                                duration = 3
                                intensity = float(debuff_data) if isinstance(debuff_data, (int, float)) else 1.0

                            status_type = self._map_debuff_to_status_type(debuff_name)
                            if status_type:
                                debuff_effect = StatusEffect(
                                    name=debuff_name,
                                    status_type=status_type,
                                    duration=duration,
                                    intensity=intensity,
                                    source_id=getattr(actor, 'id', None)
                                )
                                status_mgr.add_status(debuff_effect)

            # 상태이상 적용
            if skill.status_effects:
                target_result["status_effects"] = skill.status_effects
                # 실제 상태이상 시스템 연동 (status_manager 우선)
                status_mgr = getattr(tgt, 'status_manager', None)
                if isinstance(status_mgr, StatusManager):
                        # status_effects는 List[str] 타입이므로 리스트를 반복
                        for effect_name in skill.status_effects:
                            duration = skill.status_duration  # 기본 duration 사용
                            # 스킬별 intensity 사용 (기본값: 0.5)
                            intensity = getattr(skill, 'status_intensity', 0.5)

                            # 강력한 상태이상은 최대 2턴으로 제한
                            from src.combat.status_effects import StatusType as StatusTypeEnum
                            status_type = self._map_status_to_status_type(effect_name)
                            if status_type:
                                # 강력한 상태이상 체크 (기절, 침묵, 빙결, 마비, 석화, 시간정지)
                                if status_type in [StatusTypeEnum.STUN, StatusTypeEnum.SLEEP, StatusTypeEnum.FREEZE,
                                                   StatusTypeEnum.PARALYZE, StatusTypeEnum.PETRIFY, StatusTypeEnum.TIME_STOP,
                                                   StatusTypeEnum.SILENCE]:
                                    duration = min(duration, 2)  # 최대 2턴
                                
                                status_effect = StatusEffect(
                                    name=effect_name,
                                    status_type=status_type,
                                    duration=duration,
                                    intensity=intensity,
                                    source_id=getattr(actor, 'id', None)
                                )
                                status_mgr.add_status(status_effect)

            result["targets"].append(target_result)

        # damage=0이고 BRV 공격 스킬 처리 (damage > 0 블록 밖에서)
        if skill.damage == 0 and not skill.hp_attack and getattr(skill, 'brv_damage', 0) > 0:
            # BRV 시스템을 사용하는 적 스킬
            from src.combat.damage_calculator import get_damage_calculator
            damage_calc = get_damage_calculator()
            
            # BRV 공격 계수 조정
            brv_multiplier = skill.damage_multiplier
            if not skill.hp_attack:
                # BRV 공격: 2배 배율 적용
                brv_multiplier = skill.damage_multiplier * 2.0
            
            # 대상이 리스트인 경우 처리
            targets_list = targets if isinstance(targets, list) else [targets]
            
            for tgt in targets_list:
                if not getattr(tgt, 'is_alive', True):
                    continue
                
                target_result = {"target": getattr(tgt, 'name', 'Unknown')}
                
                # BRV 데미지 계산
                if skill.is_magical:
                    dmg_result = damage_calc.calculate_magic_damage(actor, tgt, brv_multiplier)
                else:
                    dmg_result = damage_calc.calculate_brv_damage(actor, tgt, brv_multiplier)
                
                # BRV 공격 실행
                brv_result = self.brave.brv_attack(actor, tgt, dmg_result.final_damage)
                target_result["brv_damage"] = brv_result['brv_stolen']
                
                # HP 공격이 있는 경우
                if skill.hp_attack:
                    # HP 공격 계수는 0.75배로 조정
                    hp_multiplier = skill.damage_multiplier * 0.75
                    hp_result = self.brave.hp_attack(actor, tgt, hp_multiplier, 
                                                     damage_type="magical" if skill.is_magical else "physical")
                    target_result["hp_damage"] = hp_result['hp_damage']
                
                result["targets"].append(target_result)

        return result

    def _execute_item(self, actor: Any, target: Optional[Any] = None, **kwargs) -> Dict[str, Any]:
        """아이템 사용"""
        # 아이템 시스템 연동
        item = kwargs.get('item')

        if not item:
            self.logger.warning(f"{getattr(actor, 'name', 'Unknown')}: 아이템이 지정되지 않음")
            return {"action": "item", "success": False}

        # Consumable 아이템 처리
        from src.equipment.item_system import Consumable, ItemType

        # 안전하게 item_type 확인
        item_type = getattr(item, 'item_type', None)
        if isinstance(item, Consumable) or item_type == ItemType.CONSUMABLE:
            effect_type = getattr(item, 'effect_type', 'heal_hp')
            effect_value = getattr(item, 'effect_value', 0)

            result = {
                "action": "item",
                "success": True,
                "item_name": getattr(item, 'name', 'Unknown Item'),
                "effect_type": effect_type,
                "effect_value": effect_value,
                "target": getattr(target, 'name', 'Unknown') if target else None
            }

            tgt = target if target else actor

            # 현재 층수 가져오기 (dungeon 정보 또는 적 정보에서) - 포션/폭탄 공용
            current_floor = 1
            if hasattr(self, 'dungeon') and self.dungeon and hasattr(self.dungeon, 'floor_number'):
                current_floor = getattr(self.dungeon, 'floor_number', 1)
            elif self.enemies:
                for enemy in self.enemies:
                    if hasattr(enemy, 'floor_level'):
                        current_floor = max(current_floor, getattr(enemy, 'floor_level', 1))
                        break
                    elif hasattr(enemy, 'level'):
                        current_floor = max(current_floor, getattr(enemy, 'level', 1))
                        break

            # 층수 스케일링 계수 (회복 계열 / 버프 계열 / 보호막 계열)
            heal_scale = 1.0 + current_floor * 0.08   # 10층 +80%, 20층 +160%
            buff_scale = 1.0 + current_floor * 0.05   # 10층 +50%, 20층 +100%
            shield_scale = 1.0 + current_floor * 0.1  # 10층 +100%, 20층 +200%
            dot_scale = 1.0 + current_floor * 0.1     # 폭탄 DoT 스케일링

            # 효과 타입에 따라 처리
            # 스탯 스케일링 헬퍼 함수
            def get_stat_bonus(item_obj, user):
                """연금술 포션 스탯 스케일링 보너스 계산"""
                bonus = 0
                try:
                    from src.cooking.potion_brewing import PotionDatabase
                    item_id = getattr(item_obj, 'item_id', None)
                    if item_id:
                        recipe = PotionDatabase.get_recipe(item_id)
                        if recipe and recipe.stat_scaling:
                            stat_type = recipe.stat_scaling.get("stat", "magic")
                            ratio = recipe.stat_scaling.get("ratio", 0)
                            
                            if stat_type == "magic" and hasattr(user, 'magic'):
                                bonus = int(user.magic * ratio)
                            elif stat_type == "attack" and hasattr(user, 'strength'):
                                bonus = int(user.strength * ratio)
                            self.logger.info(f"[연금술 스케일링] {item_id}: {stat_type} x{ratio} = +{bonus}")
                except Exception as e:
                    self.logger.debug(f"스탯 스케일링 실패: {e}")
                return bonus
            
            if effect_type == "heal_hp":
                # 층수 스케일링 + 스탯 스케일링 적용
                scaled_value = int(effect_value * heal_scale)
                bonus_heal = get_stat_bonus(item, actor)
                total_heal = scaled_value + bonus_heal

                if hasattr(tgt, 'heal'):
                    healed = tgt.heal(total_heal)
                elif hasattr(tgt, 'current_hp') and hasattr(tgt, 'max_hp'):
                    healed = min(total_heal, tgt.max_hp - tgt.current_hp)
                    tgt.current_hp += healed
                else:
                    healed = total_heal
                result["healing"] = healed
                if current_floor > 1 or bonus_heal > 0:
                    self.logger.info(f"[전투 아이템] {getattr(tgt, 'name', '?')} HP +{healed} (기본 {effect_value} x{heal_scale:.2f} + 스탯 {bonus_heal}, {current_floor}층)")

            elif effect_type == "heal_mp":
                # 층수 스케일링 + 스탯 스케일링 적용
                scaled_value = int(effect_value * heal_scale)
                bonus_restore = get_stat_bonus(item, actor)
                total_restore = scaled_value + bonus_restore

                if hasattr(tgt, 'restore_mp'):
                    healed = tgt.restore_mp(total_restore)
                elif hasattr(tgt, 'current_mp') and hasattr(tgt, 'max_mp'):
                    healed = min(total_restore, tgt.max_mp - tgt.current_mp)
                    tgt.current_mp += healed
                else:
                    healed = total_restore
                result["mp_healing"] = healed
                if current_floor > 1 or bonus_restore > 0:
                    self.logger.info(f"[전투 아이템] {getattr(tgt, 'name', '?')} MP +{healed} (기본 {effect_value} x{heal_scale:.2f} + 스탯 {bonus_restore}, {current_floor}층)")
            
            elif effect_type == "heal_both":
                # HP+MP 동시 회복 (층수 + 스탯 스케일링 적용)
                scaled_value = int(effect_value * heal_scale)
                bonus = get_stat_bonus(item, actor)
                total_heal = scaled_value + bonus

                hp_healed = 0
                mp_healed = 0
                if hasattr(tgt, 'heal'):
                    hp_healed = tgt.heal(total_heal)
                if hasattr(tgt, 'restore_mp'):
                    mp_healed = tgt.restore_mp(total_heal)
                result["healing"] = hp_healed
                result["mp_healing"] = mp_healed
                if current_floor > 1:
                    self.logger.info(f"[전투 아이템] {getattr(tgt, 'name', '?')} HP+{hp_healed} MP+{mp_healed} (x{heal_scale:.2f}, {current_floor}층)")
            
            elif effect_type == "shield":
                # 연금술 보호막 포션 (철의 요새 등) - 층수 스케일링 적용
                scaled_value = int(effect_value * shield_scale)
                bonus_shield = get_stat_bonus(item, actor)
                shield_amount = scaled_value + bonus_shield
                duration = getattr(item, 'duration', 10)
                
                if hasattr(tgt, 'status_manager'):
                    from src.combat.status_effects import StatusEffect as CombatStatusEffect, StatusType
                    shield_effect = CombatStatusEffect(
                        name="Potion Shield",
                        status_type=StatusType.SHIELD,
                        duration=duration,
                        intensity=shield_amount,
                        source_id=getattr(actor, "name", "Potion"),
                        metadata={"shield_hp": shield_amount},
                    )
                    tgt.status_manager.add_status(shield_effect, allow_refresh=True)
                    result["shield_applied"] = shield_amount
                    self.logger.info(f"[전투 아이템] {getattr(tgt, 'name', '?')} 보호막 +{shield_amount} ({duration}턴)")
            
            elif effect_type == "damage_reduction":
                # 연금술 피해 감소 포션 (차원 장벽 등) - 퍼센트 기반이므로 스케일링 불필요
                reduction_percent = effect_value / 100.0 if effect_value > 1 else effect_value
                duration = getattr(item, 'duration', 10)
                
                if hasattr(tgt, 'status_manager'):
                    from src.combat.status_effects import StatusEffect as CombatStatusEffect, StatusType
                    barrier_effect = CombatStatusEffect(
                        name="Damage Reduction",
                        status_type=StatusType.BARRIER,
                        duration=duration,
                        intensity=reduction_percent,
                        source_id=getattr(actor, "name", "Potion"),
                        metadata={"damage_reduction": reduction_percent},
                    )
                    tgt.status_manager.add_status(barrier_effect, allow_refresh=True)
                    result["barrier_applied"] = reduction_percent
                    self.logger.info(f"[전투 아이템] {getattr(tgt, 'name', '?')} 피해감소 {int(reduction_percent*100)}% ({duration}턴)")

            elif effect_type == "buff":
                # 기본 버프 (하위 호환)
                result["buff_applied"] = True

            elif effect_type == "buff_strength":
                # 공격력 버프 - 층수 스케일링 적용
                scaled_buff = int(effect_value * buff_scale) if effect_value > 1 else effect_value * buff_scale
                duration = getattr(item, 'duration', 25) or 25
                if not hasattr(tgt, 'active_buffs'):
                    tgt.active_buffs = {}
                tgt.active_buffs['attack_up'] = {'value': scaled_buff, 'duration': duration}
                result["buff_applied"] = "strength"
                self.logger.info(f"[버프 포션] {getattr(tgt, 'name', '?')} 공격력 +{scaled_buff} (기본 {effect_value} x{buff_scale:.2f}, {duration}턴, {current_floor}층)")

            elif effect_type == "buff_defense":
                # 방어력 버프 - 층수 스케일링 적용
                scaled_buff = int(effect_value * buff_scale) if effect_value > 1 else effect_value * buff_scale
                duration = getattr(item, 'duration', 25) or 25
                if not hasattr(tgt, 'active_buffs'):
                    tgt.active_buffs = {}
                tgt.active_buffs['defense_up'] = {'value': scaled_buff, 'duration': duration}
                result["buff_applied"] = "defense"
                self.logger.info(f"[버프 포션] {getattr(tgt, 'name', '?')} 방어력 +{scaled_buff} (기본 {effect_value} x{buff_scale:.2f}, {duration}턴, {current_floor}층)")

            elif effect_type == "buff_speed":
                scaled_buff = effect_value * buff_scale
                duration = getattr(item, 'duration', 20) or 20
                if not hasattr(tgt, 'active_buffs'):
                    tgt.active_buffs = {}
                tgt.active_buffs['speed_up'] = {'value': scaled_buff / 100.0, 'duration': duration}
                result["buff_applied"] = "speed"
                self.logger.info(f"[버프 포션] {getattr(tgt, 'name', '?')} 속도 +{scaled_buff:.0f}% ({duration}턴, {current_floor}층)")

            elif effect_type == "buff_berserk":
                # 광폭화: 공격+, 방어- - 공격 보너스만 층수 스케일링 (방어 감소는 고정)
                berserk_atk = 0.3 * (1.0 + current_floor * 0.02)
                duration = getattr(item, 'duration', 15) or 15
                if not hasattr(tgt, 'active_buffs'):
                    tgt.active_buffs = {}
                tgt.active_buffs['attack_up'] = {'value': berserk_atk, 'duration': duration}
                tgt.active_buffs['defense_down'] = {'value': 0.2, 'duration': duration}
                result["buff_applied"] = "berserk"
                self.logger.info(f"[버프 포션] {getattr(tgt, 'name', '?')} 광폭화 공+{berserk_atk:.0%} 방-20% ({duration}턴, {current_floor}층)")

            elif effect_type == "buff_resistance":
                scaled_buff = effect_value * buff_scale
                duration = getattr(item, 'duration', 20) or 20
                if not hasattr(tgt, 'active_buffs'):
                    tgt.active_buffs = {}
                tgt.active_buffs['status_resistance'] = {'value': scaled_buff / 100.0, 'duration': duration}
                result["buff_applied"] = "resistance"
                self.logger.info(f"[버프 포션] {getattr(tgt, 'name', '?')} 상태이상 저항 +{scaled_buff:.0f}% ({duration}턴, {current_floor}층)")

            elif effect_type == "buff_luck":
                scaled_buff = effect_value * buff_scale
                duration = getattr(item, 'duration', 30) or 30
                if not hasattr(tgt, 'active_buffs'):
                    tgt.active_buffs = {}
                tgt.active_buffs['crit_up'] = {'value': scaled_buff / 100.0, 'duration': duration}
                result["buff_applied"] = "luck"
                self.logger.info(f"[버프 포션] {getattr(tgt, 'name', '?')} 크리티컬 +{scaled_buff:.0f}% ({duration}턴, {current_floor}층)")

            elif effect_type == "buff_invisibility":
                scaled_buff = effect_value * buff_scale
                duration = getattr(item, 'duration', 5) or 5
                if not hasattr(tgt, 'active_buffs'):
                    tgt.active_buffs = {}
                tgt.active_buffs['evasion_up'] = {'value': scaled_buff / 100.0, 'duration': duration}
                result["buff_applied"] = "invisibility"
                self.logger.info(f"[버프 포션] {getattr(tgt, 'name', '?')} 회피율 +{effect_value}% ({duration}턴)")

            elif effect_type == "buff_regen":
                # 재생 - 층수 스케일링 적용 (intensity)
                scaled_regen = int(effect_value * heal_scale) if effect_value > 1 else effect_value * heal_scale
                duration = getattr(item, 'duration', 12) or 12
                if hasattr(tgt, 'status_manager'):
                    from src.combat.status_effects import StatusEffect as CombatStatusEffect, StatusType
                    regen = CombatStatusEffect("재생", StatusType.REGENERATION, duration=duration, intensity=scaled_regen)
                    tgt.status_manager.add_status(regen, allow_refresh=True)
                result["buff_applied"] = "regen"
                self.logger.info(f"[버프 포션] {getattr(tgt, 'name', '?')} 재생 {scaled_regen}/턴 (기본 {effect_value} x{heal_scale:.2f}, {duration}턴, {current_floor}층)")

            elif effect_type == "buff_lifesteal":
                scaled_buff = effect_value * buff_scale
                duration = getattr(item, 'duration', 20) or 20
                if not hasattr(tgt, 'active_buffs'):
                    tgt.active_buffs = {}
                tgt.active_buffs['lifesteal'] = {'value': scaled_buff / 100.0, 'duration': duration}
                result["buff_applied"] = "lifesteal"
                self.logger.info(f"[버프 포션] {getattr(tgt, 'name', '?')} 흡혈 {scaled_buff:.0f}% ({duration}턴, {current_floor}층)")

            elif effect_type == "buff_mana_shield":
                scaled_buff = effect_value * buff_scale
                duration = getattr(item, 'duration', 15) or 15
                if not hasattr(tgt, 'active_buffs'):
                    tgt.active_buffs = {}
                tgt.active_buffs['mana_shield'] = {'value': scaled_buff / 100.0, 'duration': duration}
                result["buff_applied"] = "mana_shield"
                self.logger.info(f"[버프 포션] {getattr(tgt, 'name', '?')} 마나 보호막 {scaled_buff:.0f}% ({duration}턴, {current_floor}층)")

            elif effect_type == "buff_crit_boost":
                duration = getattr(item, 'duration', 20) or 20
                if not hasattr(tgt, 'active_buffs'):
                    tgt.active_buffs = {}
                tgt.active_buffs['crit_up'] = {'value': 0.25, 'duration': duration}
                tgt.active_buffs['crit_damage_up'] = {'value': 0.5, 'duration': duration}
                result["buff_applied"] = "crit_boost"
                self.logger.info(f"[버프 포션] {getattr(tgt, 'name', '?')} 크리 확률/데미지 강화 ({duration}턴)")

            elif effect_type == "buff_battle_trance":
                duration = getattr(item, 'duration', 12) or 12
                if not hasattr(tgt, 'active_buffs'):
                    tgt.active_buffs = {}
                tgt.active_buffs['attack_up'] = {'value': 0.4, 'duration': duration}
                tgt.active_buffs['speed_up'] = {'value': 0.3, 'duration': duration}
                tgt.active_buffs['damage_taken_increase'] = {'value': 0.25, 'duration': duration}
                result["buff_applied"] = "battle_trance"
                self.logger.info(f"[버프 포션] {getattr(tgt, 'name', '?')} 전투 무아경 ({duration}턴)")

            elif effect_type == "buff_bonus_damage":
                scaled_buff = effect_value * buff_scale
                duration = getattr(item, 'duration', 10) or 10
                if not hasattr(tgt, 'active_buffs'):
                    tgt.active_buffs = {}
                tgt.active_buffs['bonus_hp_damage'] = {'value': scaled_buff / 100.0, 'duration': duration}
                result["buff_applied"] = "bonus_damage"
                self.logger.info(f"[버프 포션] {getattr(tgt, 'name', '?')} 추가 피해 {scaled_buff:.0f}% ({duration}턴, {current_floor}층)")

            elif effect_type == "cure" or effect_type == "status_cleanse" or effect_type == "cure_all_status":
                # 상태이상 치료 (모든 상태이상)
                if hasattr(tgt, 'status_manager'):
                    tgt.status_manager.clear_all_effects()
                    result["status_cured"] = True
                elif hasattr(tgt, 'status_effects'):
                    tgt.status_effects.clear()
                    result["status_cured"] = True
            
            elif effect_type == "cure_poison":
                # 독 치료
                if hasattr(tgt, 'status_manager'):
                    from src.combat.status_effects import StatusType
                    tgt.status_manager.remove_status(StatusType.POISON)
                    result["status_cured"] = True
                    self.logger.info(f"[{item_name}] {getattr(tgt, 'name', 'Unknown')} 독 치료")
                elif hasattr(tgt, 'status_effects'):
                    tgt.status_effects = {k: v for k, v in tgt.status_effects.items() if 'poison' not in k.lower()}
                    result["status_cured"] = True
                    self.logger.info(f"[{item_name}] {getattr(tgt, 'name', 'Unknown')} 독 치료")
            
            elif effect_type == "cure_debuff":
                # 디버프 치료
                if hasattr(tgt, 'status_manager'):
                    from src.combat.status_effects import StatusType
                    # 모든 디버프 타입 제거
                    debuff_types = [StatusType.WEAK, StatusType.SLOW, StatusType.BLIND, StatusType.SILENCE, StatusType.STUN, StatusType.POISON]
                    for debuff_type in debuff_types:
                        tgt.status_manager.remove_status(debuff_type)
                    result["status_cured"] = True
                    self.logger.info(f"[{item_name}] {getattr(tgt, 'name', 'Unknown')} 디버프 치료")
                elif hasattr(tgt, 'status_effects'):
                    # 디버프 관련 상태이상 제거
                    debuff_names = ['weak', 'slow', 'blind', 'silence', 'stun', 'poison']
                    tgt.status_effects = {k: v for k, v in tgt.status_effects.items() if not any(db in k.lower() for db in debuff_names)}
                    result["status_cured"] = True
                    self.logger.info(f"[{item_name}] {getattr(tgt, 'name', 'Unknown')} 디버프 치료")
            
            elif effect_type == "heal_wound":
                # 상처 치료
                if tgt is None:
                    self.logger.warning(f"[{item_name}] 타겟이 없습니다")
                    result["wound_healed"] = 0
                    result["success"] = False
                else:
                    from src.systems.wound_system import get_wound_system
                    wound_system = get_wound_system()
                    wound_healed = wound_system.heal_wound_item(tgt, int(effect_value))
                    result["wound_healed"] = wound_healed
                    result["remaining_wound"] = getattr(tgt, 'wound', 0)
                    if wound_healed > 0:
                        self.logger.info(f"[{item_name}] {getattr(tgt, 'name', 'Unknown')} 상처 {wound_healed} 치료 (남은 상처: {getattr(tgt, 'wound', 0)})")
                    else:
                        self.logger.info(f"[{item_name}] {getattr(tgt, 'name', 'Unknown')} 치료할 상처가 없습니다")
            
            # === 공격적 아이템 효과 ===
            elif effect_type in ["aoe_fire", "aoe_ice", "poison_bomb", "thunder_grenade",
                                 "attack_fire", "attack_ice", "attack_lightning", "attack_poison",
                                 "attack_explosive", "attack_aoe"]:
                # 적 전체 데미지 (아이템별 차등 공식 + 스탯 스케일링)
                # current_floor는 상단에서 이미 추출됨

                # 아이템별 차등 피해량 (기본값 + 층수 × 배율)
                damage_formulas = {
                    "attack_fire": (50, 15),       # 화염 폭탄: 50 + 층수 × 15
                    "attack_ice": (50, 15),        # 냉기 폭탄: 50 + 층수 × 15
                    "attack_lightning": (60, 18),  # 번개 폭탄: 60 + 층수 × 18
                    "attack_poison": (40, 12),     # 독 폭탄: 40 + 층수 × 12 (독 DoT 추가)
                    "attack_explosive": (80, 25),  # 폭발 폭탄: 80 + 층수 × 25
                    "attack_aoe": (70, 20),        # 파편 수류탄: 70 + 층수 × 20
                    "thunder_grenade": (75, 25),   # 천둥 수류탄: 75 + 층수 × 25 (기절 추가)
                    "poison_bomb": (40, 12),       # 독 폭탄 (별칭)
                    "aoe_fire": (50, 15),          # 범위 화염
                    "aoe_ice": (50, 15),           # 범위 냉기
                }
                base, mult = damage_formulas.get(effect_type, (75, 25))
                
                # 스탯 스케일링: 사용자 strength의 50%를 보너스 데미지로 추가
                stat_bonus = 0
                if hasattr(actor, 'strength'):
                    stat_bonus = int(actor.strength * 0.5)
                    self.logger.info(f"[폭탄 스케일링] strength {actor.strength} × 0.5 = +{stat_bonus}")
                
                damage = base + current_floor * mult + stat_bonus
                total_damage = 0
                for enemy in self.enemies:
                    if hasattr(enemy, 'is_alive') and enemy.is_alive:
                        if hasattr(enemy, 'take_damage'):
                            dmg = enemy.take_damage(damage)
                        else:
                            dmg = min(damage, getattr(enemy, 'current_hp', 0))
                            enemy.current_hp = max(0, enemy.current_hp - dmg)
                        total_damage += dmg
                        
                        # 상태이상 부여
                        if effect_type in ["poison_bomb", "attack_poison"] and hasattr(enemy, 'status_manager'):
                            from src.combat.status_effects import StatusEffect, StatusType
                            poison = StatusEffect("독", StatusType.POISON, duration=3, intensity=1.0)
                            enemy.status_manager.add_status(poison)
                        elif effect_type == "thunder_grenade" and hasattr(enemy, 'status_manager'):
                            from src.combat.status_effects import StatusEffect, StatusType
                            shock = StatusEffect("감전", StatusType.SHOCK, duration=2, intensity=1.0)
                            enemy.status_manager.add_status(shock)
                result["aoe_damage"] = total_damage
                result["targets_hit"] = len([e for e in self.enemies if hasattr(e, 'is_alive') and e.is_alive])

                # === 폭탄 레시피 특수효과 적용 ===
                try:
                    from src.cooking.bomb_crafting import BombDatabase
                    item_id = getattr(item, 'item_id', '')
                    bomb_recipe = BombDatabase.get_recipe(item_id)
                    if bomb_recipe and bomb_recipe.special_effect:
                        import random as _rand
                        se = bomb_recipe.special_effect
                        from src.combat.status_effects import StatusEffect as _SE, StatusType as _ST
                        for enemy in self.enemies:
                            if not (hasattr(enemy, 'is_alive') and enemy.is_alive):
                                continue
                            if not hasattr(enemy, 'status_manager'):
                                continue
                            # 화상 (층수 스케일링 적용)
                            if "burn_damage" in se:
                                scaled_burn = int(se["burn_damage"] * dot_scale)
                                burn = _SE("화상", _ST.BURN, duration=se.get("burn_duration", 3), intensity=scaled_burn)
                                enemy.status_manager.add_status(burn)
                            # 동결
                            if "freeze_chance" in se:
                                if _rand.randint(1, 100) <= se["freeze_chance"]:
                                    freeze = _SE("동결", _ST.FREEZE, duration=se.get("freeze_duration", 2))
                                    enemy.status_manager.add_status(freeze)
                            # 둔화
                            if "slow_percent" in se:
                                slow = _SE("둔화", _ST.SLOW, duration=se.get("slow_duration", 3), intensity=se["slow_percent"] / 100.0)
                                enemy.status_manager.add_status(slow)
                            # 기절
                            if "stun_chance" in se:
                                if _rand.randint(1, 100) <= se["stun_chance"]:
                                    stun = _SE("기절", _ST.STUN, duration=se.get("stun_duration", 1))
                                    enemy.status_manager.add_status(stun)
                            # MP 흡수 (층수 스케일링 적용)
                            if "mp_drain" in se:
                                if hasattr(enemy, 'current_mp'):
                                    scaled_drain = int(se["mp_drain"] * dot_scale)
                                    drain = min(scaled_drain, enemy.current_mp)
                                    enemy.current_mp -= drain
                            # 버프 제거
                            if se.get("dispel_buffs"):
                                if hasattr(enemy, 'active_buffs'):
                                    enemy.active_buffs.clear()
                            # 방어력 감소
                            if "defense_reduction" in se:
                                weak = _SE("방어감소", _ST.REDUCE_DEF, duration=se.get("duration", 3), intensity=se["defense_reduction"] / 100.0)
                                enemy.status_manager.add_status(weak)
                            # 명중률 감소
                            if "accuracy_reduction" in se:
                                blind = _SE("실명", _ST.BLIND, duration=se.get("duration", 3), intensity=se["accuracy_reduction"] / 100.0)
                                enemy.status_manager.add_status(blind)
                            # 약화 (weakness)
                            if "weakness" in se:
                                weak2 = _SE("약화", _ST.WEAKNESS, duration=se.get("duration", 3), intensity=se["weakness"] / 100.0)
                                enemy.status_manager.add_status(weak2)
                        if current_floor > 1:
                            self.logger.info(f"[폭탄 특수효과] {item_id}: {list(se.keys())} (DoT x{dot_scale:.2f}, {current_floor}층)")
                        else:
                            self.logger.info(f"[폭탄 특수효과] {item_id}: {list(se.keys())}")
                except Exception as e:
                    self.logger.debug(f"[폭탄 특수효과] 레시피 조회 실패: {e}")

            elif effect_type in ["single_lightning", "acid_flask"]:
                # 단일 적 데미지 (아이템별 차등 공식 + 스탯 스케일링)
                # current_floor는 상단에서 이미 추출됨

                # 스탯 스케일링: 사용자 strength의 50%를 보너스 데미지로 추가
                stat_bonus = 0
                if hasattr(actor, 'strength'):
                    stat_bonus = int(actor.strength * 0.5)
                    self.logger.info(f"[단일폭탄 스케일링] strength {actor.strength} × 0.5 = +{stat_bonus}")
                
                # 산성 플라스크: 65 + 층수 × 22 (단일 대상이므로 약간 더 강력)
                if effect_type == "acid_flask":
                    damage = 65 + current_floor * 22 + stat_bonus
                else:
                    damage = 60 + current_floor * 18 + stat_bonus
                if hasattr(tgt, 'take_damage'):
                    dmg = tgt.take_damage(damage)
                else:
                    dmg = min(damage, getattr(tgt, 'current_hp', 0))
                    tgt.current_hp = max(0, tgt.current_hp - dmg)
                result["damage"] = dmg
                
                # 추가 효과
                if effect_type == "acid_flask" and hasattr(tgt, 'stat_manager'):
                    # 방어력 감소 (간단하게 처리)
                    result["defense_debuffed"] = True
            
            elif effect_type in ["debuff_attack", "debuff_defense", "debuff_speed", "smoke_bomb"]:
                # 적 전체 디버프
                debuff_value = effect_value
                duration = 3 if effect_type != "smoke_bomb" else 2
                targets_debuffed = 0
                for enemy in self.enemies:
                    if hasattr(enemy, 'is_alive') and enemy.is_alive:
                        if hasattr(enemy, 'active_buffs'):
                            if effect_type == "debuff_attack":
                                enemy.active_buffs['attack_down'] = {'value': debuff_value, 'duration': duration}
                            elif effect_type == "debuff_defense":
                                enemy.active_buffs['defense_down'] = {'value': debuff_value, 'duration': duration}
                            elif effect_type == "debuff_speed":
                                enemy.active_buffs['speed_down'] = {'value': debuff_value, 'duration': duration}
                            elif effect_type == "smoke_bomb":
                                enemy.active_buffs['accuracy_down'] = {'value': debuff_value, 'duration': duration}
                        targets_debuffed += 1
                result["debuff_applied"] = True
                result["targets_debuffed"] = targets_debuffed
            
            elif effect_type == "break_brv":
                # 적 전체 BRV 감소
                brv_loss = int(effect_value)
                total_brv_loss = 0
                for enemy in self.enemies:
                    if hasattr(enemy, 'is_alive') and enemy.is_alive:
                        if hasattr(enemy, 'current_brv'):
                            loss = min(brv_loss, enemy.current_brv)
                            enemy.current_brv = max(0, enemy.current_brv - loss)
                            total_brv_loss += loss
                result["brv_loss"] = total_brv_loss
            
            # === 수비적 아이템 효과 ===
            elif effect_type in ["barrier_crystal", "haste_crystal", "power_tonic", "defense_elixir", "regen_crystal", "mp_regen_crystal"]:
                # 아군 전체 버프 적용 (광역 효과)
                duration = 3 if effect_type not in ["regen_crystal", "mp_regen_crystal"] else 5
                
                # 아군 전체에 버프 적용
                allies_buffed = 0
                all_allies = self.allies if actor in self.allies else self.enemies
                for ally in all_allies:
                    if hasattr(ally, 'is_alive') and ally.is_alive:
                        if not hasattr(ally, 'active_buffs'):
                            ally.active_buffs = {}
                        
                        if effect_type == "barrier_crystal":
                            ally.active_buffs['damage_reduction'] = {'value': effect_value, 'duration': duration}
                        elif effect_type == "haste_crystal":
                            ally.active_buffs['speed_up'] = {'value': effect_value, 'duration': duration}
                        elif effect_type == "power_tonic":
                            ally.active_buffs['attack_up'] = {'value': effect_value, 'duration': duration}
                            ally.active_buffs['magic_up'] = {'value': effect_value, 'duration': duration}
                        elif effect_type == "defense_elixir":
                            ally.active_buffs['defense_up'] = {'value': effect_value, 'duration': duration}
                            ally.active_buffs['magic_defense_up'] = {'value': effect_value, 'duration': duration}
                        elif effect_type == "regen_crystal":
                            ally.active_buffs['hp_regen'] = {'value': effect_value, 'duration': duration}
                        elif effect_type == "mp_regen_crystal":
                            ally.active_buffs['mp_regen'] = {'value': effect_value, 'duration': duration}
                        allies_buffed += 1
                
                result["buff_applied"] = True
                result["allies_buffed"] = allies_buffed
                self.logger.info(f"[광역 버프] {effect_type}: 아군 {allies_buffed}명에게 적용")
            
            elif effect_type == "revive_crystal":
                # 부활
                self.logger.info(f"=== 부활 크리스탈 효과 처리 시작 ===")
                target_name = getattr(tgt, 'name', str(tgt))
                is_alive = getattr(tgt, 'is_alive', True)
                current_hp = getattr(tgt, 'current_hp', 1)
                max_hp = getattr(tgt, 'max_hp', 100)
                self.logger.info(f"부활 크리스탈 사용: 대상={target_name}, is_alive={is_alive}, current_hp={current_hp}/{max_hp}, effect_value={effect_value}")

                if not is_alive or current_hp <= 0:
                    self.logger.info(f"부활 조건 만족: 대상 사망 또는 HP 0 이하")
                    tgt.is_alive = True
                    if hasattr(tgt, 'max_hp'):
                        tgt.current_hp = int(tgt.max_hp * effect_value)
                    else:
                        tgt.current_hp = int(effect_value * 100)  # 기본값
                    result["revived"] = True
                    result["hp_restored"] = tgt.current_hp
                    result["message"] = f"🌀 {target_name} 부활! HP {tgt.current_hp} 회복"
                    self.logger.info(f"부활 성공: {target_name} HP {tgt.current_hp}로 부활 (max_hp: {max_hp}, effect_value: {effect_value})")
                else:
                    self.logger.info(f"부활 조건 불만족: 대상 살아있고 HP {current_hp} > 0")
                    result["error"] = "대상이 이미 살아있습니다"
                    result["message"] = "대상이 이미 살아있어 부활할 수 없습니다"
                    self.logger.info(f"부활 실패: 대상이 이미 살아있음")

            elif effect_type == "heal_hp_full":
                # 엘리트 HP 포션 - HP 전체 회복
                if hasattr(tgt, 'heal'):
                    healed = tgt.heal(getattr(tgt, 'max_hp', 9999))
                elif hasattr(tgt, 'current_hp') and hasattr(tgt, 'max_hp'):
                    healed = tgt.max_hp - tgt.current_hp
                    tgt.current_hp = tgt.max_hp
                else:
                    healed = 0
                result["healing"] = healed
                self.logger.info(f"[전투 아이템] {getattr(tgt, 'name', '?')} HP 전체 회복 +{healed}")

            elif effect_type == "heal_mp_full":
                # 엘리트 MP 포션 - MP 전체 회복
                if hasattr(tgt, 'restore_mp'):
                    healed = tgt.restore_mp(getattr(tgt, 'max_mp', 9999))
                elif hasattr(tgt, 'current_mp') and hasattr(tgt, 'max_mp'):
                    healed = tgt.max_mp - tgt.current_mp
                    tgt.current_mp = tgt.max_mp
                else:
                    healed = 0
                result["mp_healing"] = healed
                self.logger.info(f"[전투 아이템] {getattr(tgt, 'name', '?')} MP 전체 회복 +{healed}")

            elif effect_type == "heal_both_full":
                # 메가 엘릭서 / 철학자의 엘릭서 - HP+MP 전체 회복
                hp_healed = 0
                mp_healed = 0
                if hasattr(tgt, 'heal'):
                    hp_healed = tgt.heal(getattr(tgt, 'max_hp', 9999))
                elif hasattr(tgt, 'current_hp') and hasattr(tgt, 'max_hp'):
                    hp_healed = tgt.max_hp - tgt.current_hp
                    tgt.current_hp = tgt.max_hp
                if hasattr(tgt, 'restore_mp'):
                    mp_healed = tgt.restore_mp(getattr(tgt, 'max_mp', 9999))
                elif hasattr(tgt, 'current_mp') and hasattr(tgt, 'max_mp'):
                    mp_healed = tgt.max_mp - tgt.current_mp
                    tgt.current_mp = tgt.max_mp
                result["healing"] = hp_healed
                result["mp_healing"] = mp_healed
                self.logger.info(f"[전투 아이템] {getattr(tgt, 'name', '?')} HP+{hp_healed} MP+{mp_healed} 전체 회복")

            elif effect_type == "restore_brv":
                # BRV 크리스탈 - BRV 전체 회복
                if hasattr(tgt, 'current_brv'):
                    max_brv = getattr(tgt, 'max_brv', getattr(tgt, 'base_brv', 0))
                    old_brv = tgt.current_brv
                    tgt.current_brv = max_brv
                    result["brv_restored"] = max_brv - old_brv
                    self.logger.info(f"[전투 아이템] {getattr(tgt, 'name', '?')} BRV {old_brv} -> {max_brv} 회복")
                else:
                    result["brv_restored"] = 0

            elif effect_type == "prevent_break":
                # 브레이크 가드 - BREAK 방지 버프 1회
                duration = getattr(item, 'duration', 5) or 5
                if not hasattr(tgt, 'active_buffs'):
                    tgt.active_buffs = {}
                tgt.active_buffs['brv_protect'] = {'value': 1, 'duration': duration, 'once': True}
                result["buff_applied"] = "prevent_break"
                self.logger.info(f"[버프 포션] {getattr(tgt, 'name', '?')} BREAK 방지 버프 ({duration}턴)")

            elif effect_type == "buff_evasion":
                # 스모크 그레네이드 - 회피율 버프
                scaled_buff = effect_value * buff_scale
                duration = getattr(item, 'duration', 5) or 5
                if not hasattr(tgt, 'active_buffs'):
                    tgt.active_buffs = {}
                tgt.active_buffs['evasion_up'] = {'value': scaled_buff / 100.0, 'duration': duration}
                result["buff_applied"] = "evasion"
                self.logger.info(f"[버프 포션] {getattr(tgt, 'name', '?')} 회피율 +{scaled_buff:.0f}% ({duration}턴, {current_floor}층)")

            elif effect_type == "debuff_blind":
                # 플래시 그레네이드 - 적 전체 실명
                from src.combat.status_effects import StatusEffect as _SE_blind, StatusType as _ST_blind
                duration = getattr(item, 'duration', 3) or 3
                targets_blinded = 0
                for enemy in self.enemies:
                    if hasattr(enemy, 'is_alive') and enemy.is_alive:
                        if hasattr(enemy, 'status_manager'):
                            blind_effect = _SE_blind(
                                name="실명",
                                status_type=_ST_blind.BLIND,
                                duration=duration,
                                intensity=effect_value / 100.0 if effect_value > 1 else effect_value,
                                source_id=getattr(actor, "name", "Item"),
                            )
                            enemy.status_manager.add_status(blind_effect, allow_refresh=True)
                        elif hasattr(enemy, 'active_buffs'):
                            if not hasattr(enemy, 'active_buffs'):
                                enemy.active_buffs = {}
                            enemy.active_buffs['accuracy_down'] = {'value': effect_value / 100.0 if effect_value > 1 else effect_value, 'duration': duration}
                        targets_blinded += 1
                result["debuff_applied"] = "blind"
                result["targets_debuffed"] = targets_blinded
                self.logger.info(f"[전투 아이템] 적 {targets_blinded}명 실명 ({duration}턴)")

            elif effect_type == "revive":
                # 피닉스의 깃털 - 50% HP로 부활
                target_name = getattr(tgt, 'name', str(tgt))
                is_alive = getattr(tgt, 'is_alive', True)
                current_hp = getattr(tgt, 'current_hp', 1)
                if not is_alive or current_hp <= 0:
                    tgt.is_alive = True
                    if hasattr(tgt, 'max_hp'):
                        tgt.current_hp = int(tgt.max_hp * 0.5)
                    else:
                        tgt.current_hp = 50
                    result["revived"] = True
                    result["hp_restored"] = tgt.current_hp
                    result["message"] = f"{target_name} 부활! HP {tgt.current_hp} 회복"
                    self.logger.info(f"[전투 아이템] {target_name} 50% HP로 부활 ({tgt.current_hp})")
                else:
                    result["error"] = "대상이 이미 살아있습니다"
                    result["message"] = "대상이 이미 살아있어 부활할 수 없습니다"

            elif effect_type == "revive_full":
                # 메가 피닉스 - 100% HP로 부활 (전체 아군)
                allies_revived = 0
                all_allies = self.allies if actor in self.allies else self.enemies
                for ally in all_allies:
                    is_alive = getattr(ally, 'is_alive', True)
                    current_hp = getattr(ally, 'current_hp', 1)
                    if not is_alive or current_hp <= 0:
                        ally.is_alive = True
                        if hasattr(ally, 'max_hp'):
                            ally.current_hp = ally.max_hp
                        else:
                            ally.current_hp = 100
                        allies_revived += 1
                result["revived"] = True
                result["allies_revived"] = allies_revived
                result["message"] = f"아군 {allies_revived}명 완전 부활"
                self.logger.info(f"[전투 아이템] 메가 피닉스: 아군 {allies_revived}명 100% 부활")

            elif effect_type == "buff_magic":
                # 매직 토닉 - 마법 공격력 버프
                scaled_buff = int(effect_value * buff_scale) if effect_value > 1 else effect_value * buff_scale
                duration = getattr(item, 'duration', 25) or 25
                if not hasattr(tgt, 'active_buffs'):
                    tgt.active_buffs = {}
                tgt.active_buffs['magic_up'] = {'value': scaled_buff, 'duration': duration}
                result["buff_applied"] = "magic"
                self.logger.info(f"[버프 포션] {getattr(tgt, 'name', '?')} 마법 +{scaled_buff} (기본 {effect_value} x{buff_scale:.2f}, {duration}턴, {current_floor}층)")

            elif effect_type == "bonus_exp":
                # 경험치 크리스탈 - 경험치 보너스 버프
                duration = getattr(item, 'duration', 5) or 5
                if not hasattr(tgt, 'active_buffs'):
                    tgt.active_buffs = {}
                tgt.active_buffs['exp_bonus'] = {'value': effect_value, 'duration': duration}
                result["buff_applied"] = "exp_bonus"
                self.logger.info(f"[버프 포션] {getattr(tgt, 'name', '?')} 경험치 보너스 +{effect_value} ({duration}턴)")

            elif effect_type in ("bonus_gold", "camp_rest"):
                # 전투 중 사용 불가 아이템
                result["success"] = False
                result["message"] = "전투 중에는 사용할 수 없는 아이템입니다."
                return result

            # 인벤토리에서 아이템 제거
            item_index = kwargs.get('item_index')
            if item_index is not None:
                self.logger.info(f"아이템 제거 시도: item_index={item_index}")
                # 인벤토리에서 슬롯 인덱스로 제거
                if hasattr(actor, 'inventory'):
                    try:
                        actor.inventory.remove_item(item_index, 1)
                        self.logger.info(f"액터 인벤토리에서 아이템 제거 성공: 슬롯 {item_index}")
                    except Exception as e:
                        self.logger.warning(f"액터 인벤토리에서 아이템 제거 실패: {e}")
                # 또는 전역 인벤토리에서 제거
                elif hasattr(self, 'inventory') and self.inventory is not None:
                    try:
                        self.inventory.remove_item(item_index, 1)
                        self.logger.info(f"전역 인벤토리에서 아이템 제거 성공: 슬롯 {item_index}")
                    except Exception as e:
                        self.logger.warning(f"전역 인벤토리에서 아이템 제거 실패: {e}")
                else:
                    self.logger.warning(f"인벤토리를 찾을 수 없음: actor.hasattr(inventory)={hasattr(actor, 'inventory')}, self.hasattr(inventory)={hasattr(self, 'inventory')}")

            # === 아이템 사용 팀워크 게이지 기여 ===
            gauge_amount = 0
            if result.get("healing") and result["healing"] > 0:
                gauge_amount = 15  # 회복 아이템
            elif result.get("aoe_damage"):
                gauge_amount = 20  # 폭탄
            elif result.get("buff_applied"):
                gauge_amount = 10  # 버프 포션
            elif result.get("status_cured"):
                gauge_amount = 12  # 상태이상 치료
            elif result.get("shield_applied") or result.get("barrier_applied"):
                gauge_amount = 18  # 보호막

            if gauge_amount > 0:
                self.update_teamwork_gauge(action_type=ActionType.ITEM, item_gauge=gauge_amount)

            return result
        else:
            # 소비 아이템이 아닌 경우
            return {
                "action": "item",
                "success": False,
                "error": "소비 아이템이 아닙니다"
            }

    def _execute_defend(self, actor: Any, **kwargs) -> Dict[str, Any]:
        """방어 태세"""
        # 방어 스택 증가 (저격수 특성: 집중의 힘)
        if hasattr(actor, 'defend_stack_count'):
            # focus_power 특성이 활성화되어 있는지 확인
            has_focus_power = any(
                (t if isinstance(t, str) else t.get('id')) == 'focus_power'
                for t in getattr(actor, 'active_traits', [])
            )

            if has_focus_power:
                max_stacks = 3
                if actor.defend_stack_count < max_stacks:
                    actor.defend_stack_count += 1
                    self.logger.info(
                        f"[집중의 힘] {actor.name} 방어 스택 증가: {actor.defend_stack_count}/{max_stacks}"
                    )

        # 기계공학자: 방어 시 열 -10 냉각
        if hasattr(actor, 'gimmick_type') and actor.gimmick_type == "heat_management":
            old_heat = getattr(actor, 'heat', 0)
            actor.heat = max(0, old_heat - 10)
            heat_reduced = old_heat - actor.heat
            if heat_reduced > 0:
                self.logger.info(f"[방어 냉각] {actor.name} 열 -{heat_reduced} (현재: {actor.heat})")

        # 방어 버프 적용 (StatusManager를 통해 방어력 증가 버프 부여)
        if hasattr(actor, 'status_manager'):
            try:
                defense_buff = StatusEffect(
                    name="방어 태세",
                    status_type=StatusType.BOOST_DEF,
                    duration=1,  # 1턴 동안 유지
                    intensity=1.5,  # 방어력 50% 증가
                    source_id=getattr(actor, 'id', None)
                )
                actor.status_manager.add_status(defense_buff)
            except Exception as e:
                # StatusEffect를 import하지 못한 경우 무시
                self.logger.debug(f"방어 버프 적용 실패: {e}")

        return {
            "action": "defend",
            "defend_stack": getattr(actor, 'defend_stack_count', 0)
        }

    def _execute_flee(self, actor: Any, **kwargs) -> Dict[str, Any]:
        """도망"""
        # 세피로스, 카인 전투에서는 도망 불가
        is_boss_battle = False
        for enemy in self.enemies:
            enemy_id = getattr(enemy, 'enemy_id', None)
            if enemy_id in ['sephiroth', 'abel_cain']:
                is_boss_battle = True
                break

        if is_boss_battle:
            return {
                "action": "flee",
                "success": False,
                "error": "보스전에서는 도망칠 수 없다!"
            }

        # 트레이닝 모드 확인 (허수아비 전투는 100% 도망 성공)
        is_training_mode = any(
            getattr(enemy, 'enemy_id', None) == 'training_dummy' for enemy in self.enemies
        )

        # 도망 확률 계산
        flee_chance = 1.0 if is_training_mode else 0.5  # 트레이닝 모드: 100%, 일반: 50%
        import random
        if random.random() < flee_chance:
            self.state = CombatState.FLED
            # 멀티플레이: 한 플레이어가 도망치면 아군 전체가 도망 처리
            is_multiplayer = hasattr(self, 'session') and self.session
            return {
                "action": "flee",
                "success": True,
                "all_allies_fled": is_multiplayer  # 멀티플레이 시 전체 도망 플래그
            }
        else:
            return {
                "action": "flee",
                "success": False
            }

    def _process_ransomware_damage(self, enemy: Any) -> None:
        """
        랜섬웨어 효과 처리 (적의 턴 시작 시)
        
        해커의 랜섬웨어가 활성화되어 있으면 적에게 해커의 마법력의 35%만큼 HP 피해를 적용
        
        Args:
            enemy: 적 캐릭터
        """
        # 아군 중 해커 찾기
        for ally in self.allies:
            # 해커가 살아있는지 확인
            if hasattr(ally, 'is_alive') and not ally.is_alive:
                continue
            
            if not hasattr(ally, 'gimmick_type'):
                continue
            
            # 해커인지 확인
            if ally.gimmick_type != "multithread_system":
                continue
            
            # 랜섬웨어가 활성화되어 있는지 확인
            if getattr(ally, 'program_ransomware', 0) <= 0:
                continue
            
            # 해커의 마법력 계산 (stat_manager 사용)
            if hasattr(ally, 'stat_manager'):
                from src.character.stats import Stats
                magic_attack = int(ally.stat_manager.get_value(Stats.MAGIC))
            else:
                magic_attack = getattr(ally, 'magic_attack', getattr(ally, 'magic', 0))
            
            if magic_attack <= 0:
                continue
            
            # 마법력의 35%만큼 HP 피해 계산
            damage = int(magic_attack * 0.35)
            if damage <= 0:
                continue
            
            # 적이 살아있는지 확인
            if hasattr(enemy, 'is_alive') and not enemy.is_alive:
                continue
            if hasattr(enemy, 'current_hp') and enemy.current_hp <= 0:
                continue
            
            # HP 피해 적용
            if hasattr(enemy, 'take_damage'):
                actual_damage = enemy.take_damage(damage)
            elif hasattr(enemy, 'current_hp'):
                actual_damage = min(damage, enemy.current_hp)
                enemy.current_hp = max(0, enemy.current_hp - actual_damage)
            else:
                actual_damage = damage
            
            if actual_damage > 0:
                self.logger.info(
                    f"[랜섬웨어] {ally.name}의 프로그램이 {enemy.name}에게 "
                    f"{actual_damage} HP 피해! (마법력 {magic_attack}의 35%)"
                )
                
                # 사망 여부 확인
                if hasattr(enemy, 'current_hp') and enemy.current_hp <= 0:
                    if hasattr(enemy, 'is_alive'):
                        enemy.is_alive = False
                    self.logger.warning(f"{enemy.name}이(가) 랜섬웨어로 사망!")
            
            # 한 해커만 처리 (여러 해커가 있어도 한 번만)
            break

    def _cleanup_protection_relations(self, character: Any) -> None:
        """
        죽은 캐릭터의 보호 관계를 정리합니다.

        Args:
            character: 죽은 캐릭터
        """
        character_name = getattr(character, 'name', 'Unknown')

        # 1. 이 캐릭터가 보호하고 있던 아군들 정리
        if hasattr(character, 'protected_allies') and character.protected_allies:
            for protected_ally in list(character.protected_allies):  # 복사본으로 순회
                if hasattr(protected_ally, 'protected_by') and character in protected_ally.protected_by:
                    protected_ally.protected_by.remove(character)
                    self.logger.debug(f"보호 관계 정리: {character_name} → {protected_ally.name} (보호자 사망)")
            character.protected_allies.clear()

        # 2. 이 캐릭터를 보호하고 있던 캐릭터들 정리
        if hasattr(character, 'protected_by') and character.protected_by:
            for protector in list(character.protected_by):  # 복사본으로 순회
                if hasattr(protector, 'protected_allies') and character in protector.protected_allies:
                    protector.protected_allies.remove(character)
                    self.logger.debug(f"보호 관계 정리: {protector.name} → {character_name} (보호 대상 사망)")
            character.protected_by.clear()

        self.logger.info(f"{character_name}의 보호 관계 모두 정리됨")

    def _on_character_death(self, data: Dict[str, Any]) -> None:
        """
        캐릭터 사망 이벤트 처리
        
        직업별 사망 후 처리 로직을 수행합니다.
        
        Args:
            data: 이벤트 데이터 (character, name 포함)
        """
        character = data.get("character")
        if not character:
            return
        
        # 전투가 이미 종료된 상태라면 처리하지 않음 (무한 루프 방지)
        if self.state in [CombatState.VICTORY, CombatState.DEFEAT, CombatState.FLED]:
            return
        
        # 이미 사망 처리된 캐릭터는 중복 처리하지 않음
        if not hasattr(character, '_death_processed'):
            character._death_processed = True
        else:
            return
        
        character_name = data.get("name", getattr(character, "name", "Unknown"))
        self.logger.info(f"{character_name} 사망 처리 시작")

        # 보호 관계 정리 (죽은 캐릭터가 보호하거나 보호받는 관계 모두 정리)
        self._cleanup_protection_relations(character)

        # 해커: 모든 프로그램 종료
        if hasattr(character, 'gimmick_type') and character.gimmick_type == "multithread_system":
            self._handle_hacker_death(character)
        
        # 네크로맨서: 언데드 소환물 처리
        if hasattr(character, 'gimmick_type') and character.gimmick_type == "undead_legion":
            self._handle_necromancer_death(character)
        
        # 버서커: 광기 시스템 정리
        if hasattr(character, 'gimmick_type') and character.gimmick_type == "madness_threshold":
            self._handle_berserker_death(character)
        
        # 흡혈귀: 갈증 게이지 정리
        if hasattr(character, 'gimmick_type') and character.gimmick_type == "thirst_gauge":
            self._handle_vampire_death(character)
        
        # 도적: 독 걸린 적 사망 시 광역 독 전파 (plague_burst 특성)
        if character in self.enemies:
            for ally in self.allies:
                if getattr(ally, 'gimmick_type', None) == 'venom_system' and getattr(ally, 'is_alive', True):
                    living_enemies = [e for e in self.enemies if getattr(e, 'is_alive', True) and e != character]
                    GimmickUpdater.on_venom_target_death(ally, character, living_enemies)
                    break  # 도적 1명만 처리

        # 해적: 적 처치 시 보물 획득 체크
        if character in self.enemies:
            # 적이 죽었을 때
            self._handle_pirate_treasure_drop(character)

        # 일반적인 사망 후 처리
        self._handle_general_death(character)

        # 전투 종료 체크 (전투가 아직 진행 중일 때만)
        if self.state not in [CombatState.VICTORY, CombatState.DEFEAT, CombatState.FLED]:
            self._check_battle_end()
    
    def _handle_hacker_death(self, hacker: Any) -> None:
        """
        해커 사망 시 처리: 모든 프로그램 종료
        
        Args:
            hacker: 사망한 해커 캐릭터
        """
        program_fields = ['program_virus', 'program_backdoor', 'program_ddos', 'program_ransomware', 'program_spyware']
        active_programs = []
        
        for field in program_fields:
            if getattr(hacker, field, 0) > 0:
                active_programs.append(field.replace('program_', ''))
                setattr(hacker, field, 0)
        
        if active_programs:
            self.logger.warning(
                f"{hacker.name} 사망으로 인해 실행 중이던 프로그램들이 종료되었습니다: {', '.join(active_programs)}"
            )
    
    def _handle_necromancer_death(self, necromancer: Any) -> None:
        """
        네크로맨서 사망 시 처리: 언데드 소환물 정리
        
        Args:
            necromancer: 사망한 네크로맨서 캐릭터
        """
        # 언데드 소환물이 있다면 정리
        if hasattr(necromancer, 'undead_list'):
            undead_count = len(getattr(necromancer, 'undead_list', []))
            if undead_count > 0:
                self.logger.warning(
                    f"{necromancer.name} 사망으로 인해 소환된 언데드 {undead_count}마리가 소멸했습니다."
                )
                necromancer.undead_list = []
    
    def _handle_berserker_death(self, berserker: Any) -> None:
        """
        버서커 사망 시 처리: 광기 시스템 정리
        
        Args:
            berserker: 사망한 버서커 캐릭터
        """
        # 광기 값은 유지하되, 더 이상 증가하지 않도록 처리
        if hasattr(berserker, 'madness'):
            madness_value = getattr(berserker, 'madness', 0)
            if madness_value > 0:
                self.logger.debug(
                    f"{berserker.name} 사망 시 광기 값: {madness_value}"
                )
    
    def _handle_vampire_death(self, vampire: Any) -> None:
        """
        흡혈귀 사망 시 처리: 갈증 게이지 정리

        Args:
            vampire: 사망한 흡혈귀 캐릭터
        """
        # 갈증 게이지 값은 유지하되, 더 이상 증가하지 않도록 처리
        if hasattr(vampire, 'thirst'):
            thirst_value = getattr(vampire, 'thirst', 0)
            if thirst_value > 0:
                self.logger.debug(
                    f"{vampire.name} 사망 시 갈증 게이지: {thirst_value}"
                )
    
    def _handle_pirate_treasure_drop(self, enemy: Any) -> None:
        """
        해적: 적 처치 시 보물 드랍 처리

        Args:
            enemy: 죽은 적 캐릭터
        """
        import random
        from src.character.skills.job_skills.pirate_skills import TREASURE_TYPES

        # 아군 파티에 해적이 있는지 확인
        for ally in self.allies:
            if not hasattr(ally, 'character_class'):
                continue

            if ally.character_class == "pirate":
                # 기본 보물 획득 확률 (60%)
                base_drop_chance = 0.6

                # treasure_drop 버프 확인 (럼주 효과 등)
                drop_bonus = 0.0
                if hasattr(ally, 'status_manager'):
                    # 럼주 "황금 러시" 효과 확인 (treasure_drop: 1.0 = 100% 확정 드랍)
                    for status in ally.status_manager.active_statuses:
                        if hasattr(status, 'metadata') and 'treasure_drop' in status.metadata:
                            drop_bonus = status.metadata['treasure_drop']
                            break

                # 최종 확률
                final_chance = min(1.0, base_drop_chance + drop_bonus)

                # 보물 획득 체크
                if random.random() < final_chance:
                    if not hasattr(ally, 'treasure_inventory'):
                        ally.treasure_inventory = []

                    # 최대 보물 개수 체크
                    max_treasure = 3  # 기본 최대치
                    if hasattr(ally, 'max_treasure'):
                        max_treasure = ally.max_treasure

                    if len(ally.treasure_inventory) < max_treasure:
                        # 가중치 기반 랜덤 보물 선택
                        treasure_ids = list(TREASURE_TYPES.keys())
                        weights = [TREASURE_TYPES[tid]["weight"] for tid in treasure_ids]
                        selected_treasure_id = random.choices(treasure_ids, weights=weights, k=1)[0]
                        
                        ally.treasure_inventory.append(selected_treasure_id)
                        treasure_name = TREASURE_TYPES[selected_treasure_id]["name"]
                        
                        self.logger.info(f"[해적] {ally.name}이(가) {treasure_name}을(를) 획득했다! (총: {len(ally.treasure_inventory)}개)")

                        # 전투 UI에 메시지 표시
                        if hasattr(self, 'add_message'):
                            self.add_message(f"{ally.name}이(가) {treasure_name}을(를) 획득했습니다! ({len(ally.treasure_inventory)}/{max_treasure})")
                    else:
                        self.logger.debug(f"[해적] {ally.name}의 보물 최대치 도달 ({len(ally.treasure_inventory)}/{max_treasure})")
                else:
                    self.logger.debug(f"[해적] {ally.name}의 보물 획득 실패 (확률: {final_chance:.1%})")

                # 한 명의 해적만 체크
                break

    def _handle_general_death(self, character: Any) -> None:
        """
        일반적인 사망 후 처리

        Args:
            character: 사망한 캐릭터
        """
        # 상태 효과 정리 (선택적 - 일부 버프는 사망 후에도 유지될 수 있음)
        if hasattr(character, 'status_manager'):
            # 사망 시 특정 상태 효과만 제거할 수도 있음
            pass

        # BRV 초기화
        if hasattr(character, 'current_brv'):
            character.current_brv = 0
    
    def _on_damage_taken(self, data: Dict[str, Any]) -> None:
        """
        피해 받은 이벤트 처리 (수호 효과, 복수 보너스 등)
        
        Args:
            data: 이벤트 데이터 (character, damage 등)
        """
        defender = data.get("character")
        damage = data.get("damage", 0)
        
        if not defender or damage <= 0:
            return
            
        # 반사 피해로 인한 무한 루프 방지
        if data.get("is_reflect", False):
            return
        
        # 아군 피격 시 진동 (피해량에 따라 강도 조절)
        if defender in self.allies:
            if damage > 100:
                vibration_manager.vibrate(VibrationPattern.DAMAGE_HEAVY)
            elif damage > 30:
                vibration_manager.vibrate(VibrationPattern.DAMAGE_MEDIUM)
            else:
                vibration_manager.vibrate(VibrationPattern.DAMAGE_LIGHT)
        
        # 복수 보너스 플래그 설정 (아군/적 모두)
        defender._recently_damaged = True
        
        # thorns (가시 효과) - 피격 시 반격 데미지
        attacker = data.get("attacker")
        if attacker and hasattr(defender, 'active_traits'):
            from src.character.trait_effects import get_trait_effect_manager, TraitEffectType
            trait_manager = get_trait_effect_manager()
            for trait_data in defender.active_traits:
                trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                if trait_id == 'thorns' or trait_id == 'retaliation':
                    effects = trait_manager.get_trait_effects(trait_id)
                    for effect in effects:
                        # 반격/반사 데미지 계산
                        reflect_ratio = effect.value
                        reflect_damage = int(damage * reflect_ratio)
                        if reflect_damage > 0:
                            if hasattr(attacker, 'take_damage'):
                                try:
                                    actual_damage = attacker.take_damage(reflect_damage, is_reflect=True)
                                except TypeError:
                                    actual_damage = attacker.take_damage(reflect_damage)
                            elif hasattr(attacker, 'current_hp'):
                                actual_damage = min(reflect_damage, attacker.current_hp)
                                attacker.current_hp = max(0, attacker.current_hp - actual_damage)
                            else:
                                actual_damage = reflect_damage
                            self.logger.info(f"[반사 피해] {defender.name}의 가시 효과로 {attacker.name}에게 {actual_damage} 반사 피해!")

        # COUNTER 버프 반사 (미러 포스, 거울 함정 등)
        if attacker and hasattr(defender, 'active_buffs') and 'counter' in defender.active_buffs:
            counter_buff = defender.active_buffs['counter']
            reflect_ratio = float(counter_buff.get('value', 0))
            if reflect_ratio > 0:
                reflect_damage = int(damage * reflect_ratio)
                if reflect_damage > 0:
                    if hasattr(attacker, 'take_damage'):
                        try:
                            actual_damage = attacker.take_damage(reflect_damage, is_reflect=True)
                        except TypeError:
                            actual_damage = attacker.take_damage(reflect_damage)
                    elif hasattr(attacker, 'current_hp'):
                        actual_damage = min(reflect_damage, attacker.current_hp)
                        attacker.current_hp = max(0, attacker.current_hp - actual_damage)
                    else:
                        actual_damage = reflect_damage
                    self.logger.info(f"[반사 피해] {defender.name}의 반격 버프로 {attacker.name}에게 {actual_damage} 반사 피해! ({int(reflect_ratio * 100)}%)")

                    # 전투 UI에 메시지 표시
                    ui = getattr(self, 'combat_ui', None)
                    if ui and hasattr(ui, 'add_message'):
                        ui.add_message(f"[반사] {defender.name} → {attacker.name} {actual_damage} 피해!", (255, 200, 100))

        # 아군이 피해를 받았는지 확인
        if defender not in self.allies:
            return
        
        # 이미 피해가 적용되었는지 확인 (new_hp가 None이면 아직 적용 전)
        if data.get("new_hp") is not None:
            # 이미 피해가 적용된 경우, 수호 효과는 처리할 수 없음
            return
        
        # 스킬 효과: 수호의 맹세 - 기사가 아군을 보호
        # 보호받는 대상인지 확인
        # 수호 효과 재귀 방지: 수호 중인 캐릭터는 다시 수호 효과를 받지 않음
        if hasattr(defender, '_is_guarding') and defender._is_guarding:
            return  # 수호 중인 캐릭터는 수호 효과를 받지 않음
        
        if hasattr(defender, 'protected_by') and defender.protected_by:
            # 보호자가 있는 경우, 보호자가 대신 피해를 받음
            # 현재 전투에 참여하는 보호자만 확인 (오래된 참조 방지)
            for guardian in list(defender.protected_by):  # 리스트 복사하여 순회 중 수정 방지
                if (guardian in self.allies and
                    hasattr(guardian, 'is_alive') and guardian.is_alive and
                    guardian != defender and
                    not getattr(guardian, '_is_guarding', False) and  # 수호 중이 아닌 경우만
                    (not hasattr(guardian, 'status_manager') or guardian.status_manager.can_act())):  # 행동 가능한 경우만
                    # 보호자가 피해를 대신 받음 (보호자의 방어력으로 재계산)
                    data["damage"] = 0  # 원래 대상은 피해를 받지 않음
                    
                    # 원본 공격 정보를 사용하여 보호자의 방어력으로 재계산
                    attacker = data.get("attacker")
                    original_damage = data.get("original_damage")
                    damage_type = data.get("damage_type", "physical")
                    brv_points = data.get("brv_points", 0)
                    hp_multiplier = data.get("hp_multiplier", 1.0)
                    is_break = data.get("is_break", False)
                    damage_kwargs = data.get("damage_kwargs", {})
                    
                    if attacker and original_damage is not None:
                        # 보호자의 방어력으로 데미지 재계산
                        from src.combat.damage_calculator import get_damage_calculator
                        damage_calc = get_damage_calculator()
                        
                        damage_result, wound_damage = damage_calc.calculate_hp_damage(
                            attacker=attacker,
                            defender=guardian,  # 보호자가 방어자
                            brv_points=brv_points,
                            hp_multiplier=hp_multiplier,
                            is_break=is_break,
                            damage_type=damage_type,
                            **damage_kwargs
                        )
                        protected_damage = damage_result.final_damage
                    else:
                        # 원본 정보가 없으면 기존 데미지 사용 (하위 호환성)
                        protected_damage = damage
                    
                    # 보호자가 피해를 받음 (수호 효과 재귀 방지 플래그 설정)
                    if hasattr(guardian, 'take_damage'):
                        # 수호 효과가 다시 트리거되지 않도록 플래그 설정
                        guardian._is_guarding = True
                        try:
                            guardian_was_alive = getattr(guardian, 'is_alive', True)
                            guardian_actual_damage = guardian.take_damage(protected_damage)
                            self.logger.info(
                                f"[수호의 맹세] {guardian.name}이(가) {defender.name}의 피해를 대신 받음: "
                                f"{protected_damage} → 실제 {guardian_actual_damage} (보호자 방어력 적용)"
                            )

                            # 보호자가 죽었으면 보호 관계 정리
                            guardian_is_alive = getattr(guardian, 'is_alive', True)
                            if guardian_was_alive and not guardian_is_alive:
                                self.logger.info(f"[수호의 맹세] {guardian.name}이(가) 사망하여 보호 관계 정리")
                                # 보호자의 보호 목록에서 죽은 대상 제거
                                if hasattr(guardian, 'protected_allies') and defender in guardian.protected_allies:
                                    guardian.protected_allies.remove(defender)
                                # 보호받는 대상의 보호자 목록에서 제거
                                if hasattr(defender, 'protected_by') and guardian in defender.protected_by:
                                    defender.protected_by.remove(guardian)
                        finally:
                            # 플래그 제거
                            guardian._is_guarding = False

                    return  # 한 명만 수호

        # 전사 수호자 스탠스: 50% 확률로 아군 피해 대신 받기
        for ally in self.allies:
            if (ally == defender or
                not hasattr(ally, 'is_alive') or not ally.is_alive or
                getattr(ally, '_is_guarding', False)):  # 수호 중이 아닌 경우만
                continue

            # 전사이고 수호자 스탠스인지 확인
            if (hasattr(ally, 'gimmick_type') and ally.gimmick_type == 'stance_system' and
                hasattr(ally, 'current_stance') and ally.current_stance == 5):  # 5 = guardian

                # 행동 불가능한 경우 스킷
                if hasattr(ally, 'status_manager') and not ally.status_manager.can_act():
                    continue

                # 50% 확률로 피해 대신 받기
                import random
                if random.random() < 0.50:
                    # 원본 공격 정보를 사용하여 보호자의 방어력으로 재계산
                    attacker = data.get("attacker")
                    original_damage = data.get("original_damage")
                    damage_type = data.get("damage_type", "physical")
                    brv_points = data.get("brv_points", 0)
                    hp_multiplier = data.get("hp_multiplier", 1.0)
                    is_break = data.get("is_break", False)
                    damage_kwargs = data.get("damage_kwargs", {})

                    if attacker and original_damage is not None:
                        # 보호자의 방어력으로 데미지 재계산
                        from src.combat.damage_calculator import get_damage_calculator
                        damage_calc = get_damage_calculator()

                        damage_result, wound_damage = damage_calc.calculate_hp_damage(
                            attacker=attacker,
                            defender=ally,  # 전사가 방어자
                            brv_points=brv_points,
                            hp_multiplier=hp_multiplier,
                            is_break=is_break,
                            damage_type=damage_type,
                            **damage_kwargs
                        )
                        protected_damage = damage_result.final_damage
                    else:
                        # 원본 정보가 없으면 기존 데미지 사용
                        protected_damage = damage

                    # 원래 대상은 피해를 받지 않음
                    data["damage"] = 0

                    # 전사가 피해를 받음 (수호 효과 재귀 방지 플래그 설정)
                    if hasattr(ally, 'take_damage'):
                        ally._is_guarding = True
                        try:
                            guardian_actual_damage = ally.take_damage(protected_damage)
                            self.logger.info(
                                f"[수호자 자세] {ally.name}이(가) {defender.name}의 피해를 대신 받음: "
                                f"{protected_damage} → 실제 {guardian_actual_damage} (원래 피해: {damage})"
                            )
                        finally:
                            ally._is_guarding = False

                    return  # 한 명만 수호

        # 특성 효과: 수호 (guardian_angel) - 아군 피해 대신 받기
        from src.character.trait_effects import get_trait_effect_manager, TraitEffectType
        trait_manager = get_trait_effect_manager()
        
        # 다른 아군 중 수호 효과가 있는 캐릭터 찾기
        for ally in self.allies:
            if (ally == defender or 
                not hasattr(ally, 'is_alive') or not ally.is_alive or
                getattr(ally, '_is_guarding', False)):  # 수호 중이 아닌 경우만
                continue
            
            if not hasattr(ally, 'active_traits'):
                continue
            
            for trait_data in ally.active_traits:
                trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                effects = trait_manager.get_trait_effects(trait_id)
                for effect in effects:
                    if effect.effect_type == TraitEffectType.GUARDIAN:
                        # 확률적으로 피해 대신 받기
                        import random
                        if random.random() < effect.value:  # value = 발동 확률 (0.20 = 20%)
                            # 보호받을 피해 비율 (metadata에서 가져오거나 기본값 100%)
                            protection_ratio = effect.metadata.get("protection_ratio", 1.0) if effect.metadata else 1.0
                            
                            # 수호자가 받을 피해 계산 (원래 피해의 protection_ratio만큼)
                            protected_damage = int(damage * protection_ratio)
                            
                            # 원래 피해를 받을 캐릭터가 받을 피해를 줄임
                            remaining_damage = damage - protected_damage
                            
                            # 데이터에 수정된 피해를 반영
                            data["damage"] = remaining_damage
                            
                            # 수호자가 피해를 받음 (수호 효과 재귀 방지 플래그 설정)
                            if hasattr(ally, 'take_damage'):
                                ally._is_guarding = True
                                try:
                                    guardian_actual_damage = ally.take_damage(protected_damage)
                                    self.logger.info(
                                        f"[{trait_id}] {ally.name}이(가) {defender.name}의 피해를 대신 받음: "
                                        f"{protected_damage} → 실제 {guardian_actual_damage} (원래 피해: {damage}, 남은 피해: {remaining_damage}, 보호 비율: {int(protection_ratio * 100)}%)"
                                    )
                                finally:
                                    # 플래그 제거
                                    ally._is_guarding = False
                            
                            return  # 한 명만 수호

        # 패링 메커니즘: 캐스팅 중 피격 시 카운터 (충전 획득 전에 처리)
        if hasattr(self, 'casting_system'):
            cast_info = self.casting_system.get_cast_info(defender)
            if cast_info and cast_info.state.value == "casting":
                skill = cast_info.skill
                attacker = data.get("attacker")

                # 패링 스킬인지 확인
                if skill and hasattr(skill, 'metadata') and skill.metadata.get('parry'):
                    # 피해 무효화
                    data["damage"] = 0
                    if hasattr(defender, 'take_damage'):
                        # 실제 HP 감소 방지
                        pass

                    # 카운터 데미지 발동
                    if attacker:
                        parry_multiplier = skill.metadata.get('parry_damage_multiplier', 3.0)
                        parry_charge_gain = skill.metadata.get('parry_charge_gain', 30)

                        # 카운터 데미지 계산 (기본 스킬 데미지 × 패링 배율)
                        from src.combat.damage_calculator import get_damage_calculator
                        damage_calc = get_damage_calculator()

                        # 패링 데미지 (BRV+HP)
                        counter_result = damage_calc.calculate_physical_damage(
                            attacker=defender,
                            defender=attacker,
                            multiplier=parry_multiplier
                        )

                        # BRV 데미지
                        self.brave.brv_attack(defender, attacker, counter_result.final_damage)

                        # HP 데미지
                        if hasattr(defender, 'current_brv') and defender.current_brv > 0:
                            hp_result = self.brave.hp_attack(defender, attacker)

                            self.logger.info(
                                f"[패링!] {defender.name}이(가) {attacker.name}의 공격을 막고 카운터! "
                                f"BRV: {counter_result.final_damage}, HP: {hp_result.get('hp_damage', 0)}"
                            )

                        # 기믹별 패링 보상
                        if hasattr(defender, 'gimmick_type'):
                            from src.character.gimmick_updater import GimmickUpdater

                            # 암흑기사: 충전 획득
                            if defender.gimmick_type == "charge_system":
                                GimmickUpdater.on_charge_gained(defender, parry_charge_gain, "패링 성공")

                            # 사무라이: 관찰 + 검압 획득
                            elif defender.gimmick_type == "kenshin_system":
                                observation_gain = skill.metadata.get('parry_observation_gain', 3)
                                kenatsu_gain = skill.metadata.get('parry_kenatsu_gain', 40)

                                # 관찰 스택 증가
                                current_obs = getattr(defender, 'observation', 0)
                                max_obs = getattr(defender, 'max_observation', 15)
                                defender.observation = min(max_obs, current_obs + observation_gain)

                                # 검압 게이지 증가
                                current_kenatsu = getattr(defender, 'kenatsu', 0)
                                max_kenatsu = getattr(defender, 'max_kenatsu', 100)
                                defender.kenatsu = min(max_kenatsu, current_kenatsu + kenatsu_gain)

                                stage = GimmickUpdater._get_kenshin_stage(defender)
                                self.logger.info(
                                    f"[검심 패링] {defender.name} [{stage}] 관찰 +{observation_gain} ({defender.observation}/{max_obs}), "
                                    f"검압 +{kenatsu_gain} ({defender.kenatsu}/{max_kenatsu})"
                                )

                        # 패링 성공 플래그 설정 (캐스팅 완료 시 스킬 효과 발동 방지용)
                        cast_info.parry_success = True
                        
                        # 캐스팅은 계속 진행 (취소하지 않음)
                        # 패링 성공 시 피해를 받지 않으므로 충전 획득 없음
                        return

        # 암흑기사: 피격 시 충전 획득 (패링으로 막히지 않은 경우에만)
        # 패링이 성공하면 위에서 return되므로 여기 도달하지 않음
        final_damage = data.get("damage", damage)
        if final_damage > 0 and hasattr(defender, 'gimmick_type') and defender.gimmick_type == "charge_system":
            from src.character.gimmick_updater import GimmickUpdater
            GimmickUpdater.on_take_damage_charge(defender, final_damage)

    def _on_turn_end(self, actor: Any) -> None:
        """
        턴 종료 처리

        Args:
            actor: 행동한 캐릭터
        """
        # 턴 종료 시에는 BRV 회복하지 않음 (HP 공격 후 BRV가 0인 상태 유지)
        # BRV 회복은 다음 턴 시작 시에 처리됨

        # 버프 지속시간 감소 (행동한 캐릭터만)
        # 각 캐릭터가 행동할 때 해당 캐릭터의 버프/디버프만 턴 감소
        if hasattr(actor, 'active_buffs') and actor.active_buffs:
            expired_buffs = []
            for buff_type, buff_data in list(actor.active_buffs.items()):
                # 모든 버프의 duration 감소 (regen/mp_regen 포함)

                duration = buff_data.get('duration', 0)
                if duration > 0:
                    duration -= 1
                    buff_data['duration'] = duration

                    if duration <= 0:
                        expired_buffs.append(buff_type)
                        self.logger.debug(f"{actor.name}의 {buff_type} 버프 만료")

            # 만료된 버프 제거
            for buff_type in expired_buffs:
                del actor.active_buffs[buff_type]

        # 스탯 스왑 효과 처리 (턴 종료) - 모든 캐릭터 대상
        all_combatants = self.allies + self.enemies
        for combatant in all_combatants:
            if hasattr(combatant, 'stat_swap_effects') and combatant.stat_swap_effects:
                expired_effects = []
                for effect in combatant.stat_swap_effects[:]:  # 복사본으로 순회
                    effect['duration'] -= 1
                    if effect['duration'] <= 0:
                        # 효과 만료: 원래 스탯으로 복원
                        stat = effect['stat']
                        original_value = effect['original_value']
                        if hasattr(combatant, 'stat_manager') and combatant.stat_manager:
                            # Character: stat_manager 사용 (Stats 상수는 문자열)
                            combatant.stat_manager.set_base_value(stat, original_value)
                            self.logger.info(f"{combatant.name}의 스탯 스왑 효과 만료: {stat} → {original_value}")
                        elif isinstance(stat, str):
                            # SimpleEnemy: 직접 속성 복원
                            setattr(combatant, stat, int(original_value))
                            self.logger.info(f"{combatant.name}의 스탯 스왑 효과 만료: {stat} → {original_value}")
                        expired_effects.append(effect)

                # 만료된 효과 제거
                for effect in expired_effects:
                    combatant.stat_swap_effects.remove(effect)

        # 기믹 업데이트 (턴 종료)
        GimmickUpdater.on_turn_end(actor)

        # 호감도 연계스킬/체인어빌리티 쿨다운 감소 (아군 턴 종료 시에만)
        if actor in self.allies:
            self.on_affinity_turn_end()

        # 모든 아군의 포탑 자동 공격 (기계공학자가 파티에 있으면 매 턴 발사)
        turret_context = {'combat_manager': self}
        for ally in self.allies:
            if getattr(ally, 'gimmick_type', None) == "heat_management" and getattr(ally, 'is_alive', False):
                turret_count = getattr(ally, 'turret_count', 0)
                if turret_count > 0:
                    GimmickUpdater._turret_auto_attack(ally, turret_context)

        # === 세피로스 표식 시스템 업데이트 ===
        sephiroth = next((e for e in self.enemies if getattr(e, 'enemy_id', None) == "sephiroth"), None)
        if sephiroth and getattr(sephiroth, 'is_alive', False) and hasattr(self, 'boss_gimmick_system'):
            # 표식 대상 변경 체크 (2턴마다)
            mark_result = self.boss_gimmick_system.update_sephiroth_mark(sephiroth, self.allies)
            if mark_result:
                self.logger.info(f"\033[95m{mark_result['message']}\033[0m")
                # UI에 표시
                ui = getattr(self, 'combat_ui', None)
                if ui and hasattr(ui, 'add_message'):
                    ui.add_message(mark_result['message'], (255, 100, 255))
                    ui.add_message(f"[광기의 표식] 피해 +50%, 매턴 HP 2% 피해", (255, 150, 150))
            
            # 표식 대상 DoT 피해
            marked = self.boss_gimmick_system.sephiroth_marked_target
            if marked and getattr(marked, 'is_alive', True):
                dot_result = self.boss_gimmick_system.process_mark_dot_damage(marked)
                if dot_result:
                    ui = getattr(self, 'combat_ui', None)
                    if ui and hasattr(ui, 'add_message'):
                        ui.add_message(f"[광기의 표식] {marked.name}에게 {dot_result['damage']} 피해!", (255, 100, 100))
        
        # === 카인 낙인 시스템 업데이트 ===
        cain = next((e for e in self.enemies if getattr(e, 'enemy_id', None) == "abel_cain"), None)
        if cain and getattr(cain, 'is_alive', False) and hasattr(self, 'boss_gimmick_system'):
            self.boss_gimmick_system.on_cain_turn_end()
            
            # 낙인 대상 변경 체크 (2턴마다)
            mark_result = self.boss_gimmick_system.update_cain_mark(cain, self.allies)
            if mark_result:
                from src.combat.boss_gimmicks import BossGimmickSystem
                self.logger.info(f"\033[96m{mark_result['message']}\033[0m")
                self.logger.info(f"[시간의 낙인] 대상: {mark_result['glitched_name']}")
                # UI에 표시
                ui = getattr(self, 'combat_ui', None)
                if ui and hasattr(ui, 'add_message'):
                    ui.add_message(mark_result['message'], (100, 200, 255))
                    ui.add_message(f"[시간의 낙인] 행동 시 HP 15% 피해, 30% 시간 정지", (150, 200, 255))

        # 이벤트 발행
        event_bus.publish(Events.COMBAT_TURN_END, {
            "actor": actor,
            "turn": self.turn_count
        })

        self.turn_count += 1

        # 트레이닝 모드: 턴 카운트 증가 (아군 턴만)
        ui = getattr(self, 'combat_ui', None)
        if ui and hasattr(ui, 'training_mode') and ui.training_mode:
            if hasattr(ui, 'training_dummy') and ui.training_dummy:
                if actor in self.allies:
                    ui.training_dummy.increment_turn()

        # 원소 장막 지속시간 감소 (아군 턴 종료 시)
        if actor in self.allies and hasattr(self, 'party_elemental_shield'):
            shield = self.party_elemental_shield
            if shield:
                shield['duration'] -= 1
                if shield['duration'] <= 0:
                    self.logger.info(f"[원소 장막] 지속시간 종료로 소멸")
                    self.party_elemental_shield = None
                    # 모든 아군의 원소장막 버프 제거
                    for ally in self.allies:
                        if hasattr(ally, 'status_manager'):
                            from src.combat.status_effects import StatusType
                            ally.status_manager.remove_status(StatusType.ELEMENTAL_AEGIS)
        
        # === 카인 시간의 심판 체크 (15턴마다) ===
        cain = next((e for e in self.enemies if getattr(e, 'enemy_id', None) == "abel_cain"), None)
        if cain and getattr(cain, 'is_alive', False) and hasattr(self, 'boss_gimmick_system'):
            # 쿨다운 감소
            self.boss_gimmick_system.on_cain_turn_end()
            # 15턴마다 심판 체크
            if self.turn_count > 0 and self.turn_count % 15 == 0:
                context = {
                    'turn_count': self.turn_count,
                    'is_turn_start': True
                }
                self._try_cain_judgment(cain, context)
        
        # 요리 쿨타임 감소
        if self.cooking_cooldown_turn is not None and self.cooking_cooldown_duration > 0:
            elapsed_turns = self.turn_count - self.cooking_cooldown_turn
            if elapsed_turns >= self.cooking_cooldown_duration:
                # 쿨타임 종료
                self.cooking_cooldown_duration = 0
                self.cooking_cooldown_turn = None
                # 인벤토리에도 반영
                if hasattr(self, 'inventory') and self.inventory is not None:
                    self.inventory.cooking_cooldown_duration = 0
                    self.inventory.cooking_cooldown_turn = None

    def _process_completed_casts(self) -> None:
        """완료된 캐스팅 처리"""
        from src.combat.casting_system import get_casting_system
        casting_system = get_casting_system()

        # 완료된 캐스팅 가져오기
        completed_casts = casting_system.get_completed_casts()

        for cast_info in completed_casts:
            caster = cast_info.caster
            skill = cast_info.skill
            target = cast_info.target

            # 시전자가 여전히 살아있고 행동 가능한지 확인
            if self._is_defeated(caster):
                self.logger.info(f"{getattr(caster, 'name', 'Unknown')} 전투 불능으로 시전 취소")
                continue

            # 패링 성공 시 스킬 효과는 발동 (패링은 즉시 카운터, 캐스팅 완료 시 스킬 효과 발동)
            # 패링 성공 플래그가 있어도 스킬 효과는 정상적으로 발동
            self.logger.info(f"{getattr(caster, 'name', 'Unknown')}의 {skill.name} 발동!")

            # 스킬 실행 (SFX 포함)
            from src.character.skills.skill_manager import get_skill_manager
            skill_manager = get_skill_manager()

            # 캐스팅이 완료되었으므로 실제 스킬 효과를 적용
            # context에 모든 적/아군 정보 추가 (AOE 효과를 위해)
            all_enemies = self.enemies if caster in self.allies else self.allies
            all_allies = self.allies if caster in self.allies else self.enemies
            
            # 스냅샷 컨텍스트를 context에 추가 (기믹 보너스 계산용)
            context = {
                "combat_manager": self, 
                "all_enemies": all_enemies,
                "all_allies": all_allies
            }
            if cast_info.snapshot_context:
                context["snapshot_context"] = cast_info.snapshot_context
            
            result = skill.execute(caster, target, context=context)

            if result.success:
                # SFX 재생
                skill_manager._play_skill_sfx(skill)

                # 쿨다운 시스템 제거됨
                # if skill.cooldown > 0:
                #     skill_manager.set_cooldown(caster, skill.skill_id, skill.cooldown)

                # ATB 소비
                self.atb.consume_atb(caster, self.atb.threshold)

                # 이벤트 발행
                from src.core.event_bus import event_bus, Events
                event_bus.publish(Events.SKILL_EXECUTE, {
                    "skill": skill,
                    "user": caster,
                    "target": target,
                    "result": result
                })

    def _process_evade_traits(self, evader: Any, attacker: Any) -> None:
        """
        회피 성공 후 특성 처리

        Args:
            evader: 회피한 캐릭터
            attacker: 공격한 캐릭터
        """
        if not hasattr(evader, 'active_traits'):
            return

        import random
        from src.combat.status_effects import StatusEffect, StatusType

        # shadow_step (Rogue): 회피 후 다음 공격 크리티컬 확률 +50%
        has_shadow_step = any(
            (t if isinstance(t, str) else t.get('id')) == 'shadow_step'
            for t in evader.active_traits
        )
        if has_shadow_step:
            crit_buff = StatusEffect(
                status_type=StatusType.BOOST_CRIT,
                duration=1,  # 다음 턴까지
                value=0.50,
                source=evader
            )
            if hasattr(evader, 'add_status_effect'):
                evader.add_status_effect(crit_buff)
                self.logger.info(f"[그림자 이동] {evader.name} 회피 후 크리티컬 확률 +50%!")

        # counter_blade (Sword Saint): 회피 시 30% 확률로 반격
        has_counter_blade = any(
            (t if isinstance(t, str) else t.get('id')) == 'counter_blade'
            for t in evader.active_traits
        )
        if has_counter_blade and random.random() < 0.30:
            # 반격 실행 (BRV 공격)
            self.logger.info(f"[반격 검술] {evader.name}이(가) 반격합니다!")
            counter_result = self.brv_attack(evader, attacker, trigger_gimmick=False)
            # 반격 데미지 로그는 brv_attack에서 처리

        # 도적(venom_system): 회피 성공 시 독 연계
        if getattr(evader, 'gimmick_type', None) == 'venom_system':
            GimmickUpdater.on_rogue_evade(evader, attacker)

    def _apply_party_wide_traits(self) -> None:
        """
        전투 시작 시 파티 전체 버프 특성 적용 (holy_aura, chivalry 등)
        """
        from src.character.stats import Stats

        # 각 아군의 파티 버프 특성 확인
        for ally in self.allies:
            if not hasattr(ally, 'active_traits') or not hasattr(ally, 'stat_manager'):
                continue

            # holy_aura (Paladin): 파티 전체 모든 스탯 +15%
            has_holy_aura = any(
                (t if isinstance(t, str) else t.get('id')) == 'holy_aura'
                for t in ally.active_traits
            )
            if has_holy_aura:
                # 모든 아군에게 스탯 보너스 적용
                for target in self.allies:
                    if not hasattr(target, 'stat_manager'):
                        continue
                    self._apply_all_stats_bonus(target, 'holy_aura', 0.15)
                self.logger.info(f"[신성한 기운] {ally.name}의 파티 버프: 모든 스탯 +15%")

            # chivalry (Knight): 파티 전체 모든 스탯 +10%
            has_chivalry = any(
                (t if isinstance(t, str) else t.get('id')) == 'chivalry'
                for t in ally.active_traits
            )
            if has_chivalry:
                # 모든 아군에게 스탯 보너스 적용
                for target in self.allies:
                    if not hasattr(target, 'stat_manager'):
                        continue
                    self._apply_all_stats_bonus(target, 'chivalry', 0.10)
                self.logger.info(f"[기사도] {ally.name}의 파티 버프: 모든 스탯 +10%")

            # leadership (Knight): 파티 리더일 때 전체 스탯 +15%
            has_leadership = any(
                (t if isinstance(t, str) else t.get('id')) == 'leadership'
                for t in ally.active_traits
            )
            if has_leadership:
                # 파티 리더 확인 (첫 번째 아군을 리더로 간주)
                is_leader = ally == self.allies[0]
                if is_leader:
                    self._apply_all_stats_bonus(ally, 'leadership', 0.15)
                    self.logger.info(f"[지휘] {ally.name} 파티 리더 버프: 모든 스탯 +15%")

    def _apply_all_stats_bonus(self, character: Any, source: str, multiplier: float) -> None:
        """
        모든 스탯에 비율 보너스 적용

        Args:
            character: 대상 캐릭터
            source: 보너스 출처 (특성 ID)
            multiplier: 배율 (0.15 = 15%)
        """
        if not hasattr(character, 'stat_manager'):
            return

        from src.character.stats import Stats

        # 모든 주요 스탯에 대해 보너스 계산 및 적용
        all_stats = [
            Stats.STRENGTH, Stats.DEFENSE, Stats.MAGIC, Stats.SPIRIT,
            Stats.SPEED, Stats.LUCK, Stats.ACCURACY, Stats.EVASION,
            Stats.HP, Stats.MP, Stats.MAX_BRV
        ]
        for stat in all_stats:
            base_value = character.stat_manager.get_value(stat, use_total=False)
            bonus_value = int(base_value * multiplier)
            if bonus_value > 0:
                character.stat_manager.add_bonus(stat, source, bonus_value)

    def _check_battle_end(self) -> None:
        """승리/패배 판정"""
        # 전투가 이미 종료된 상태라면 체크하지 않음
        if self.state in [CombatState.VICTORY, CombatState.DEFEAT, CombatState.FLED]:
            return

        # === 카인 불멸 능력: HP 0 도달 시 1회 부활 ===
        for enemy in self.enemies:
            if getattr(enemy, 'enemy_id', None) == "abel_cain":
                if enemy.current_hp <= 0 and not getattr(enemy, '_has_revived', False):
                    # 1회 부활
                    enemy.current_hp = enemy.max_hp // 2
                    enemy.is_alive = True
                    enemy._has_revived = True

                    # UI 메시지 설정
                    revival_msg = "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    revival_msg += "카인: \"하하, 내가 죽을 거라 생각했나?\"\n"
                    revival_msg += "「 불멸의 신 」\n"
                    revival_msg += f"카인이 부활했습니다! HP: {enemy.current_hp}/{enemy.max_hp}\n"
                    revival_msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━"

                    # combat_ui에서 표시하기 위해 임시 메시지 저장
                    self.revival_message = revival_msg
                    self.logger.info(f"카인 부활! (불멸 능력) HP: {enemy.current_hp}/{enemy.max_hp}")

        # 모든 적이 죽었는가? (적이 있어야만 체크)
        if self.enemies and all(self._is_defeated(enemy) for enemy in self.enemies):
            self._end_combat(CombatState.VICTORY)
            return

        # 불멸의 존재 해제 조건 체크 (HP 0인데 다른 아군이 모두 사망한 경우)
        if self.allies:
            for ally in self.allies:
                if getattr(ally, 'current_hp', 1) <= 0 and getattr(ally, 'is_alive', False):
                    if hasattr(ally, '_has_undying_existence') and not ally._has_undying_existence():
                        ally.is_alive = False
                        self.logger.warning(f"{getattr(ally, 'name', 'Unknown')}의 '불멸의 존재' 효과가 다른 아군의 전멸로 인해 해제되어 사망합니다.")

        # 모든 아군이 죽었는가? (아군이 있어야만 체크)
        if self.allies and all(self._is_defeated(ally) for ally in self.allies):
            # 멀티플레이 모드: 플레이어별로 전멸 여부를 개별 확인
            if hasattr(self, 'session') and self.session:
                # 전멸된 플레이어의 캐릭터를 유령 상태로 전환
                # 플레이어별 생존 여부 추적
                all_players_dead = True
                for player_id, player in self.session.players.items():
                    if hasattr(player, 'party') and player.party:
                        player_has_alive = False
                        for char in player.party:
                            if hasattr(char, 'is_alive') and char.is_alive:
                                player_has_alive = True
                                break
                            elif hasattr(char, 'current_hp') and char.current_hp > 0:
                                player_has_alive = True
                                break

                        if not player_has_alive:
                            # 이 플레이어의 캐릭터가 전멸 → 유령 상태로 전환
                            for char in player.party:
                                if hasattr(char, 'is_ghost'):
                                    char.is_ghost = True
                                    self.logger.info(
                                        f"[유령 전환] {getattr(char, 'name', 'Unknown')} "
                                        f"(플레이어: {player_id})"
                                    )
                        else:
                            all_players_dead = False

                if all_players_dead:
                    # 모든 플레이어의 모든 캐릭터가 죽었으면 게임오버
                    self.logger.info("모든 플레이어의 모든 캐릭터가 죽었습니다. 게임오버.")
                    self.is_game_over = True
                    self._end_combat(CombatState.DEFEAT)
                else:
                    # 일부 플레이어만 전멸 → 유령 전환, 전투 계속
                    # 전투 참여 allies에서 유령 제거 (전투에서 제외)
                    living_allies = [
                        a for a in self.allies
                        if getattr(a, 'is_alive', False) or
                        (hasattr(a, 'current_hp') and a.current_hp > 0)
                    ]
                    if living_allies:
                        self.logger.info(
                            f"일부 플레이어 전멸 → 유령 전환. "
                            f"생존 아군: {len(living_allies)}명, 전투 계속."
                        )
                        # 전투 계속 - DEFEAT 호출하지 않음
                    else:
                        # 생존 아군이 없으면 패배
                        self.logger.info("전투 참여 파티원이 모두 죽었습니다. 패배 (맵으로 복귀).")
                        self.is_game_over = False
                        self._end_combat(CombatState.DEFEAT)
                return
            else:
                # 싱글플레이 모드: 전투 참여자만 체크 (게임 오버)
                self.logger.info("전투 참여 파티원이 모두 죽었습니다. 게임오버.")
                self.is_game_over = True
                self._end_combat(CombatState.DEFEAT)
                return

    def _is_defeated(self, character: Any) -> bool:
        """캐릭터가 전투 불능 상태인지 확인"""
        if hasattr(character, "is_alive"):
            return not character.is_alive
        if hasattr(character, "current_hp"):
            return character.current_hp <= 0
        return False

    def _clear_protection_relationships(self, characters: List[Any]) -> None:
        """
        보호 관계 초기화 (오래된 참조 제거)
        
        전투 간 보호 관계가 유지되지 않도록, 현재 전투에 참여하는 캐릭터만
        보호 관계를 유지하고 나머지는 제거합니다.
        
        Args:
            characters: 현재 전투에 참여하는 캐릭터 리스트
        """
        # PartyMember는 hashable하지 않으므로 리스트로 비교
        character_list = list(characters)
        
        for character in characters:
            # protected_allies: 이 캐릭터가 보호하는 아군 목록
            # 현재 전투에 참여하지 않는 캐릭터 제거
            if hasattr(character, 'protected_allies'):
                if not isinstance(character.protected_allies, list):
                    character.protected_allies = []
                else:
                    # 현재 전투에 참여하는 캐릭터만 유지 (리스트로 비교)
                    character.protected_allies = [
                        ally for ally in character.protected_allies
                        if ally in character_list
                    ]
            
            # protected_by: 이 캐릭터를 보호하는 캐릭터 목록
            # 현재 전투에 참여하지 않는 캐릭터 제거
            if hasattr(character, 'protected_by'):
                if not isinstance(character.protected_by, list):
                    character.protected_by = []
                else:
                    # 현재 전투에 참여하는 캐릭터만 유지 (리스트로 비교)
                    character.protected_by = [
                        guardian for guardian in character.protected_by
                        if guardian in character_list
                    ]

    def _end_combat(self, state: CombatState) -> None:
        """
        전투 종료

        Args:
            state: 종료 상태
        """
        self.state = state

        self.logger.info(f"전투 종료: {state.value}")

        # 전투 종료 진동 (헤드리스 모드에서는 스킵)
        if not self.headless:
            if state == CombatState.VICTORY:
                vibration_manager.vibrate(VibrationPattern.SUCCESS)
            elif state == CombatState.DEFEAT:
                vibration_manager.vibrate(VibrationPattern.DEATH)
            else:
                vibration_manager.vibrate(VibrationPattern.COMBAT_END)
        
        # 마술사 다이아 효과 (bonus_rewards) - 승리 시 추가 보상
        if state == CombatState.VICTORY:
            # 멀티플레이: 유령 상태 플레이어 부활 (HP 1)
            if hasattr(self, 'session') and self.session:
                for player_id, player in self.session.players.items():
                    if hasattr(player, 'party') and player.party:
                        for char in player.party:
                            if getattr(char, 'is_ghost', False):
                                char.is_ghost = False
                                char.is_alive = True
                                char.current_hp = 1
                                self.logger.info(
                                    f"[유령 부활] {getattr(char, 'name', 'Unknown')} "
                                    f"(플레이어: {player_id}) HP 1로 부활"
                                )

            # === 보스 승리 스토리 ===
            is_sephiroth = any(getattr(enemy, 'enemy_id', None) == "sephiroth" for enemy in self.enemies)
            is_cain = any(getattr(enemy, 'enemy_id', None) == "abel_cain" for enemy in self.enemies)

            if is_cain:
                from src.story.story_system import get_story_system
                story_system = get_story_system()
                victory_story = story_system.get_cain_defeat_story()
                self.victory_story = victory_story
                self.logger.info("카인 격파! 퍼펙트 엔딩 달성!")
            elif is_sephiroth:
                from src.story.story_system import get_story_system
                story_system = get_story_system()
                victory_story = story_system.get_sephiroth_defeat_story()
                self.victory_story = victory_story
                story_system.set_sephiroth_defeated(True)
                self.logger.info("세피로스 격파! 30층 해금!")

            total_bonus = 0
            for ally in self.allies:
                card_effects = getattr(ally, 'card_effects', {})
                bonus = card_effects.pop('bonus_rewards', 0)
                if bonus > 0:
                    total_bonus += bonus
                    self.logger.info(f"[마술사] {ally.name} 다이아 효과! 추가 보상 +{int(bonus * 100)}%")
            if total_bonus > 0:
                # 보너스 정보 저장 (main.py에서 사용)
                self.bonus_rewards_multiplier = 1.0 + total_bonus

        # 퀘스트 진행도 업데이트 (적 처치 + 생존 턴)
        if state == CombatState.VICTORY:
            try:
                from src.quest.quest_manager import get_quest_manager
                qm = get_quest_manager()
                # 처치한 적 카운트
                for enemy in self.enemies:
                    if hasattr(enemy, 'current_hp') and enemy.current_hp <= 0:
                        # enemy_id > character_class > name 순으로 매칭
                        enemy_target = (
                            getattr(enemy, 'enemy_id', None)
                            or getattr(enemy, 'character_class', None)
                            or getattr(enemy, 'name', '')
                        )
                        if enemy_target:
                            qm.update_progress("enemy_killed", str(enemy_target).lower(), 1)
                # 생존 턴 카운트 (SURVIVAL 퀘스트용)
                if hasattr(self, 'turn_count') and self.turn_count > 0:
                    qm.update_progress("survival", "survival_turns", self.turn_count)
            except Exception as e:
                self.logger.debug(f"퀘스트 진행도 업데이트 실패: {e}")

        # 팀워크 게이지 저장 (다음 전투에서 복원용)
        if self.party:
            try:
                import src.persistence.save_system as save_module
                save_module._last_loaded_teamwork_gauge = self.party.teamwork_gauge
                save_module._last_loaded_max_teamwork_gauge = self.party.max_teamwork_gauge
                self.logger.info(f"팀워크 게이지 저장됨: {self.party.teamwork_gauge}/{self.party.max_teamwork_gauge}")
            except Exception as e:
                self.logger.debug(f"팀워크 게이지 저장 실패: {e}")

        # 호감도 데이터 저장 (다음 전투에서 복원용)
        if self._affinity_manager:
            try:
                import src.persistence.save_system as save_module
                save_module._last_loaded_affinity_data = self._affinity_manager.to_dict()
                self.logger.info("호감도 데이터 저장됨 (전투 종료 캐싱)")
            except Exception as e:
                self.logger.debug(f"호감도 데이터 저장 실패: {e}")

        # 이벤트 발행
        event_bus.publish(Events.COMBAT_END, {
            "state": state.value,
            "turn_count": self.turn_count
        })

        # 콜백 호출
        if self.on_combat_end:
            self.on_combat_end(state)

        # 보호 관계 정리 (오래된 참조 제거)
        self._clear_protection_relationships(self.allies)
        
        # 시스템 정리
        self.atb.clear()

        # 캐스팅 시스템 정리
        from src.combat.casting_system import get_casting_system
        casting_system = get_casting_system()
        casting_system.clear()
        
        # 보스 표식/낙인 정리 (전투 간 지속 방지)
        from src.combat.boss_gimmicks import BossGimmickSystem
        for ally in self.allies:
            if hasattr(ally, '_sephiroth_mark'):
                delattr(ally, '_sephiroth_mark')
                self.logger.debug(f"{ally.name} 세피로스 표식 제거")
            if hasattr(ally, '_cain_mark'):
                delattr(ally, '_cain_mark')
                self.logger.debug(f"{ally.name} 카인 낙인 제거")
        BossGimmickSystem.clear_glitch_cache()  # 글리치 캐시 전체 초기화

        # 배틀메이지 룬 카운터 리셋 (전투 간 누적 방지)
        for ally in self.allies:
            if getattr(ally, 'gimmick_type', None) == 'rune_resonance':
                ally.rune_fire = 0
                ally.rune_ice = 0
                ally.rune_lightning = 0
                ally.rune_earth = 0
                ally.rune_arcane = 0
                self.logger.debug(f"{ally.name} 룬 카운터 리셋")

    def get_action_order(self) -> List[Any]:
        """
        현재 행동 순서 가져오기

        Returns:
            행동 가능한 전투원 리스트
        """
        return self.atb.get_action_order()

    @property
    def party(self) -> Optional[Any]:
        """
        Party 객체 (팀워크 게이지 시스템용)

        Returns:
            Party 인스턴스 또는 None
        """
        return self._party

    @party.setter
    def party(self, value: Optional[Any]):
        """Party 객체 설정"""
        self._party = value

    def is_player_turn(self, character: Any) -> bool:
        """플레이어 턴 여부"""
        return character in self.allies

    def get_valid_targets(self, actor: Any, action_type: ActionType) -> List[Any]:
        """
        유효한 대상 리스트

        Args:
            actor: 행동자
            action_type: 행동 타입

        Returns:
            대상 리스트
        """
        if action_type in [ActionType.BRV_ATTACK, ActionType.HP_ATTACK, ActionType.BRV_HP_ATTACK]:
            # 공격: 상대편 대상
            if actor in self.allies:
                return [e for e in self.enemies if not self._is_defeated(e)]
            else:
                return [a for a in self.allies if not self._is_defeated(a)]
        else:
            # 아이템, 스킬 등: 아군 대상
            if actor in self.allies:
                return self.allies
            else:
                return self.enemies

    def execute_enemy_turn(self, enemy: Any) -> Optional[Dict[str, Any]]:
        """
        적 턴 실행 (AI 사용)

        Args:
            enemy: 적 캐릭터

        Returns:
            행동 결과
        """
        try:
            # 적 턴 시작 시 DoT (독, 화상 등) 처리
            if hasattr(enemy, 'status_manager'):
                dot_result = enemy.status_manager.process_dot_effects(enemy)
                if dot_result["total_damage"] > 0:
                    self.logger.info(
                        f"{enemy.name}: DoT 피해 {dot_result['total_damage']}"
                        f" (HP: {enemy.current_hp}/{enemy.max_hp})"
                    )
                    # 적이 DoT로 죽으면 처리
                    if hasattr(enemy, 'is_alive') and not enemy.is_alive:
                        self.logger.info(f"{enemy.name}이(가) DoT로 쓰러졌습니다!")
                        return {
                            "action": "defeated",
                            "actor": enemy,
                            "success": True,
                            "message": f"{enemy.name}이(가) 지속 피해로 쓰러졌습니다!"
                        }
            
            # 적이 행동할 수 있는지 확인 (기절, 수면 등 상태이상 체크)
            if hasattr(enemy, 'status_manager'):
                if not enemy.status_manager.can_act():
                    # 행동 불가능 상태 - 상태이상 지속시간만 감소
                    expired = enemy.status_manager.update_duration()
                    if expired:
                        self.logger.debug(f"{enemy.name}: {len(expired)}개 상태 효과 만료")
                    
                    # 턴 종료 처리 (재생 효과 등)
                    self._on_turn_end(enemy)
                    
                    # ATB 소비 (행동은 하지 못함)
                    self.atb.consume_atb(enemy)
                    
                    return {
                        "action": "skip",
                        "actor": enemy,
                        "success": False,
                        "error": "행동 불가능 상태",
                        "message": f"{enemy.name}은(는) 행동 불가능 상태!"
                    }

            from src.ai.enemy_ai import create_ai_for_enemy

            # 적 AI 생성
            ai = create_ai_for_enemy(enemy)

            # AI가 None이면 (허수아비 등) 턴 건너뛰기
            if ai is None:
                self.logger.debug(f"{enemy.name}: AI 비활성화 - 턴 건너뛰기")
                
                # 턴 종료 처리
                self._on_turn_end(enemy)
                
                # ATB 소비
                self.atb.consume_atb(enemy)
                
                return {
                    "action": "skip",
                    "actor": enemy,
                    "success": False,
                    "message": f"{enemy.name}은(는) 행동하지 않습니다"
                }

            # AI가 행동 결정
            allies = self.enemies  # 적 입장에서 아군
            enemies = self.allies  # 적 입장에서 적군

            action_decision = ai.decide_action(allies, enemies)

            if not action_decision:
                # 결정 실패 시 기본 공격
                target = self.get_valid_targets(enemy, ActionType.BRV_ATTACK)
                if target:
                    return self.execute_action(
                        enemy,
                        ActionType.BRV_ATTACK,
                        target=target[0]
                    )
                return None

            # AI 결정에 따라 행동 실행
            action_type_str = action_decision.get("type", "attack")
            target = action_decision.get("target")
            skill = action_decision.get("skill")

            if action_type_str == "skill":
                # 스킬 사용
                return self.execute_action(
                    enemy,
                    ActionType.SKILL,
                    target=target,
                    skill=skill
                )
            elif action_type_str == "hp_attack":
                # HP 공격
                return self.execute_action(
                    enemy,
                    ActionType.HP_ATTACK,
                    target=target
                )
            elif action_type_str == "defend":
                # 방어
                return self.execute_action(
                    enemy,
                    ActionType.DEFEND
                )
            elif action_type_str == "skip":
                # 턴 건너뛰기
                self.logger.debug(f"{enemy.name}: 턴 건너뛰기")
                
                # 턴 종료 처리
                self._on_turn_end(enemy)
                
                # ATB 소비
                self.atb.consume_atb(enemy)
                
                return {
                    "action": "skip",
                    "actor": enemy,
                    "success": False,
                    "message": action_decision.get("message", f"{enemy.name}은(는) 행동하지 않습니다")
                }
            else:
                # 일반 BRV 공격
                return self.execute_action(
                    enemy,
                    ActionType.BRV_ATTACK,
                    target=target
                )

        except ImportError as e:
            self.logger.warning(f"AI 시스템 로드 실패: {e}, 기본 공격 사용")
            # AI 없으면 기본 공격
            target = self.get_valid_targets(enemy, ActionType.BRV_ATTACK)
            if target:
                return self.execute_action(
                    enemy,
                    ActionType.BRV_ATTACK,
                    target=target[0]
                )
            return None

    def _map_buff_to_status_type(self, buff_name: str) -> Optional[StatusType]:
        """버프 이름을 StatusType으로 매핑"""
        # 일반적인 버프 매핑
        buff_mapping = {
            "strength_up": StatusType.BOOST_ATK,
            "attack_up": StatusType.BOOST_ATK,
            "defense_up": StatusType.BOOST_DEF,
            "speed_up": StatusType.BOOST_SPD,
            "magic_up": StatusType.BOOST_MAGIC_ATK,
            "magic_defense_up": StatusType.BOOST_MAGIC_DEF,
            "accuracy_up": StatusType.BOOST_ACCURACY,
            "crit_up": StatusType.BOOST_CRIT,
            "dodge_up": StatusType.BOOST_DODGE,
            "all_stats_up": StatusType.BOOST_ALL_STATS,
            "vitality_up": StatusType.REGENERATION,
            "regen": StatusType.REGENERATION,
            "mp_regen": StatusType.MP_REGEN,
            "haste": StatusType.HASTE,
            "blessing": StatusType.BLESSING,
            "invincible": StatusType.INVINCIBLE,
            "barrier": StatusType.BARRIER,
            "shield": StatusType.SHIELD,
            "royal_blessing": StatusType.BLESSING,
            "luck_up": StatusType.BOOST_CRIT,
            "divine_blessing": StatusType.HOLY_BLESSING,
            "full_recovery": StatusType.REGENERATION,
            "magic_boost": StatusType.BOOST_MAGIC_ATK,
        }

        return buff_mapping.get(buff_name.lower())

    def _map_debuff_to_status_type(self, debuff_name: str) -> Optional[StatusType]:
        """디버프 이름을 StatusType으로 매핑"""
        debuff_mapping = {
            "strength_down": StatusType.REDUCE_ATK,
            "attack_down": StatusType.REDUCE_ATK,
            "defense_down": StatusType.REDUCE_DEF,
            "speed_down": StatusType.REDUCE_SPD,
            "magic_down": StatusType.REDUCE_MAGIC_ATK,
            "magic_defense_down": StatusType.REDUCE_MAGIC_DEF,
            "accuracy_down": StatusType.REDUCE_ACCURACY,
            "evasion_down": StatusType.REDUCE_EVASION,
            "all_stats_down": StatusType.REDUCE_ALL_STATS,
            "slow": StatusType.SLOW,
            "weakness": StatusType.WEAKNESS,
            "vulnerable": StatusType.VULNERABLE,
            "weaken": StatusType.WEAKEN,
            "confusion": StatusType.CONFUSION,
            "terror": StatusType.TERROR,
            "fear": StatusType.FEAR,
        }

        return debuff_mapping.get(debuff_name.lower())

    def _map_status_to_status_type(self, status_name: str):
        """상태이상 이름을 StatusType으로 매핑"""
        # StatusType을 명시적으로 import하여 사용
        from src.combat.status_effects import StatusType as StatusTypeEnum
        
        status_mapping = {
            "poison": StatusTypeEnum.POISON,
            "burn": StatusTypeEnum.BURN,
            "bleed": StatusTypeEnum.BLEED,
            "stun": StatusTypeEnum.STUN,
            "sleep": StatusTypeEnum.SLEEP,
            "silence": StatusTypeEnum.SILENCE,
            "blind": StatusTypeEnum.BLIND,
            "paralyze": StatusTypeEnum.PARALYZE,
            "freeze": StatusTypeEnum.FREEZE,
            "petrify": StatusTypeEnum.PETRIFY,
            "curse": StatusTypeEnum.CURSE,
            "slow": StatusTypeEnum.SLOW,
            "corrosion": StatusTypeEnum.CORROSION,
            "disease": StatusTypeEnum.DISEASE,
            "charm": StatusTypeEnum.CHARM,
            "dominate": StatusTypeEnum.DOMINATE,
            "root": StatusTypeEnum.ROOT,
            "chill": StatusTypeEnum.CHILL,
            "shock": StatusTypeEnum.SHOCK,
            "madness": StatusTypeEnum.MADNESS,
            "taunt": StatusTypeEnum.TAUNT,
        }

        return status_mapping.get(status_name.lower())
    
    def _apply_environmental_effects(self, actor: Any) -> None:
        """
        전투 위치의 환경 효과를 캐릭터에게 적용
        
        Args:
            actor: 효과를 받을 캐릭터 (아군 또는 적)
        """
        if not self.dungeon or not self.combat_position:
            return
        
        # 던전의 환경 효과 관리자 확인 (두 가지 속성명 모두 지원)
        effect_manager = None
        if hasattr(self.dungeon, 'environmental_effect_manager'):
            effect_manager = self.dungeon.environmental_effect_manager
        elif hasattr(self.dungeon, 'environment_effect_manager'):
            effect_manager = self.dungeon.environment_effect_manager
        
        if not effect_manager:
            return
        
        # 전투 위치에서 환경 효과 확인
        combat_x, combat_y = self.combat_position
        effects = effect_manager.get_effects_at_tile(combat_x, combat_y)
        
        if not effects:
            return
        
        # 각 효과 적용 (전투 중에는 턴당으로 적용)
        for effect in effects:
            from src.world.environmental_effects import EnvironmentalEffectType
            
            # === 턴당 지속 피해 효과 ===
            if effect.effect_type == EnvironmentalEffectType.POISON_SWAMP:
                damage = int(actor.max_hp * 0.02 * effect.intensity)
                if hasattr(actor, 'take_damage'):
                    actor.take_damage(damage)
                else:
                    actor.current_hp = max(1, actor.current_hp - damage)
                self.logger.info(f"{actor.name} 독 늪 피해: {damage}")
            
            elif effect.effect_type == EnvironmentalEffectType.RADIATION_ZONE:
                damage = int(12 * effect.intensity)
                if hasattr(actor, 'take_damage'):
                    actor.take_damage(damage)
                else:
                    actor.current_hp = max(1, actor.current_hp - damage)
                self.logger.info(f"{actor.name} 방사능 피해: {damage}")
            
            elif effect.effect_type == EnvironmentalEffectType.CURSED_ZONE:
                damage = int(actor.max_hp * 0.015 * effect.intensity)
                if hasattr(actor, 'take_damage'):
                    actor.take_damage(damage)
                else:
                    actor.current_hp = max(1, actor.current_hp - damage)
                self.logger.info(f"{actor.name} 저주 구역 피해: {damage}")
            
            elif effect.effect_type == EnvironmentalEffectType.BLOOD_MOON:
                damage = int(actor.max_hp * 0.025 * effect.intensity)
                if hasattr(actor, 'take_damage'):
                    actor.take_damage(damage)
                else:
                    actor.current_hp = max(1, actor.current_hp - damage)
                self.logger.info(f"{actor.name} 피의 달 저주 피해: {damage}")
            
            # === 이동 시 데미지 효과 (전투 중에는 턴 시작 시에도 적용) ===
            elif effect.effect_type == EnvironmentalEffectType.BURNING_FLOOR:
                damage = int(15 * effect.intensity)
                if hasattr(actor, 'take_damage'):
                    actor.take_damage(damage)
                else:
                    actor.current_hp = max(1, actor.current_hp - damage)
                self.logger.info(f"{actor.name} 불타는 바닥 피해: {damage}")
            
            elif effect.effect_type == EnvironmentalEffectType.ELECTRIC_FIELD:
                damage = int(10 * effect.intensity)
                if hasattr(actor, 'take_damage'):
                    actor.take_damage(damage)
                else:
                    actor.current_hp = max(1, actor.current_hp - damage)
                self.logger.info(f"{actor.name} 전기장 피해: {damage}")
            
            # === 턴당 지속 회복 효과 ===
            elif effect.effect_type == EnvironmentalEffectType.HOLY_GROUND:
                heal = int(actor.max_hp * 0.03 * effect.intensity)
                if hasattr(actor, 'heal'):
                    actor.heal(heal)
                else:
                    actor.current_hp = min(actor.max_hp, actor.current_hp + heal)
                self.logger.info(f"{actor.name} 신성한 땅 회복: {heal}")
            
            elif effect.effect_type == EnvironmentalEffectType.BLESSED_SANCTUARY:
                heal = int(actor.max_hp * 0.04 * effect.intensity)
                if hasattr(actor, 'heal'):
                    actor.heal(heal)
                else:
                    actor.current_hp = min(actor.max_hp, actor.current_hp + heal)
                self.logger.info(f"{actor.name} 축복받은 성역 회복: {heal}")
            
            elif effect.effect_type == EnvironmentalEffectType.HALLOWED_LIGHT:
                heal = int(actor.max_hp * 0.025 * effect.intensity)
                if hasattr(actor, 'heal'):
                    actor.heal(heal)
                else:
                    actor.current_hp = min(actor.max_hp, actor.current_hp + heal)
                self.logger.info(f"{actor.name} 신성한 빛 회복: {heal}")
            
            elif effect.effect_type == EnvironmentalEffectType.MANA_VORTEX:
                if hasattr(actor, 'current_mp') and hasattr(actor, 'max_mp'):
                    mp_restore = int(actor.max_mp * 0.05 * effect.intensity)
                    if hasattr(actor, 'restore_mp'):
                        actor.restore_mp(mp_restore)
                    else:
                        actor.current_mp = min(actor.max_mp, actor.current_mp + mp_restore)
                    self.logger.info(f"{actor.name} 마나 소용돌이 MP 회복: {mp_restore}")
            
            # 스탯 수정 효과는 get_environmental_stat_modifiers()로 별도 계산
    
    def get_environmental_stat_modifiers(self, actor: Any) -> Dict[str, float]:
        """
        환경 효과로 인한 스탯 수정치 반환
        
        Args:
            actor: 스탯 수정을 받을 캐릭터
            
        Returns:
            스탯별 배율 딕셔너리 (예: {"strength": 1.3, "defense": 0.8})
            기본값 1.0, 값이 1.3이면 +30%, 0.8이면 -20%
        """
        modifiers = {
            "strength": 1.0,
            "magic": 1.0,
            "defense": 1.0,
            "magic_defense": 1.0,
            "speed": 1.0,
            "accuracy": 1.0,
            "evasion": 1.0
        }
        
        if not self.dungeon or not self.combat_position:
            return modifiers
        
        # 던전의 환경 효과 관리자 확인
        effect_manager = None
        if hasattr(self.dungeon, 'environmental_effect_manager'):
            effect_manager = self.dungeon.environmental_effect_manager
        elif hasattr(self.dungeon, 'environment_effect_manager'):
            effect_manager = self.dungeon.environment_effect_manager
        
        if not effect_manager:
            return modifiers
        
        # 전투 위치의 환경 효과 스탯 수정치 가져오기
        combat_x, combat_y = self.combat_position
        env_modifiers = effect_manager.get_stat_modifiers(actor, combat_x, combat_y)
        
        # 퍼센트 수정치를 배율로 변환 (0.3 = +30% → 1.3)
        for stat, percent in env_modifiers.items():
            if stat in modifiers:
                modifiers[stat] = 1.0 + percent
        
        return modifiers

    def update_teamwork_gauge(
        self,
        action_type: ActionType,
        **kwargs
    ) -> None:
        """
        팀워크 게이지 업데이트

        Args:
            action_type: 행동 타입
            **kwargs: 추가 옵션 (is_critical, caused_break, healed_ally, was_hit)
        """
        if not self.party:
            return

        gain = 0

        # 기본 게이지 증가량 (행동 타입에 따라)
        if action_type == ActionType.BRV_ATTACK:
            gain = 5
        elif action_type == ActionType.HP_ATTACK:
            gain = 8
        elif action_type == ActionType.BRV_HP_ATTACK:
            gain = 10
        elif action_type == ActionType.SKILL:
            # 스킬 타입에 따라 다름 (일단 기본값)
            gain = 6
        elif action_type == ActionType.ITEM:
            gain = kwargs.get('item_gauge', 0)  # 아이템 유형별 차등 게이지
        elif action_type == ActionType.DEFEND:
            gain = 0  # 방어는 게이지 증가 없음

        # 보너스 게이지 증가
        if kwargs.get('is_critical'):
            gain += 3
        if kwargs.get('caused_break'):
            gain += 15
        if kwargs.get('healed_ally'):
            gain += 8
        if kwargs.get('was_hit'):
            gain += 3

        # 호감도 보너스 적용
        if gain > 0 and self._affinity_manager:
            party_jobs = [c.character_class for c in self.allies if hasattr(c, 'character_class') and getattr(c, 'is_alive', True)]
            avg_bonus = self._affinity_manager.get_party_avg_gauge_bonus(party_jobs)
            if avg_bonus > 0:
                gain = int(gain * (1.0 + avg_bonus))

        # 시너지 충전 보너스 적용
        if gain > 0 and self._synergy_manager:
            synergy_bonus = self._synergy_manager.get_teamwork_charge_bonus()
            if synergy_bonus > 0:
                gain = int(gain * (1.0 + synergy_bonus))

        # 게이지 추가
        if gain > 0:
            self.party.add_teamwork_gauge(gain)

    def restore_teamwork_gauge(self, teamwork_gauge: int = 0, max_teamwork_gauge: int = 600) -> None:
        """
        팀워크 게이지 복원 (로드 시 호출)

        Args:
            teamwork_gauge: 복원할 팀워크 게이지
            max_teamwork_gauge: 최대 팀워크 게이지
        """
        if not self.party:
            self.logger.warning("Party 인스턴스가 없습니다")
            return

        self.party.teamwork_gauge = teamwork_gauge
        self.party.max_teamwork_gauge = max_teamwork_gauge
        self.logger.info(f"팀워크 게이지 복원: {teamwork_gauge}/{max_teamwork_gauge}")

    # ─── 호감도/유대 시스템 ───────────────────────────────────

    @property
    def affinity_manager(self):
        """AffinityManager 접근 (없으면 None)"""
        return self._affinity_manager

    @affinity_manager.setter
    def affinity_manager(self, manager):
        self._affinity_manager = manager

    def check_bond_skills(self, trigger_event: str, actor: Any) -> list:
        """
        연계스킬 발동 체크 (자동, 무료)

        공격 적중/피해/브레이크 등의 이벤트 발생 시 호출.
        발동된 연계스킬 목록을 반환합니다.
        """
        if not self._affinity_manager:
            return []
        if not hasattr(actor, 'character_class'):
            return []

        party_jobs = [
            c.character_class for c in self.allies
            if hasattr(c, 'character_class') and getattr(c, 'is_alive', True)
        ]

        results = self._affinity_manager.check_bond_skills(
            trigger_event=trigger_event,
            actor_job=actor.character_class,
            party_jobs=party_jobs
        )

        # 발동된 연계스킬 이벤트 발행
        for result in results:
            event_bus.publish(Events.BOND_SKILL_TRIGGERED, {
                "skill": result.skill,
                "source_job": result.source_job,
                "ally_job": result.ally_job,
                "actor": actor
            })
            self.logger.info(f"연계스킬 발동: {result.skill.name} ({result.source_job})")

        return results

    def trigger_chain_ability_check(self, actor: Any, trigger_reason: str) -> list:
        """
        체인어빌리티 트리거 공통 메서드

        BREAK/SCATTER/팀워크스킬/특정스킬 사용 후 호출.
        사용 가능한 체인어빌리티 목록을 반환하고 pending에 저장합니다.

        Args:
            actor: 트리거를 발생시킨 캐릭터
            trigger_reason: 트리거 사유 ("break", "scatter", "teamwork", "skill")
        """
        if not self._affinity_manager or not self.party:
            return []
        if not hasattr(actor, 'character_class'):
            return []

        party_jobs = [
            c.character_class for c in self.allies
            if hasattr(c, 'character_class') and getattr(c, 'is_alive', True)
        ]

        results = self._affinity_manager.check_chain_abilities(
            actor_job=actor.character_class,
            party_jobs=party_jobs,
            available_gauge=self.party.teamwork_gauge
        )

        if results:
            self.pending_chain_abilities = results
            self.chain_trigger_reason = trigger_reason
            for result in results:
                event_bus.publish(Events.CHAIN_ABILITY_TRIGGERED, {
                    "ability": result.ability,
                    "source_job": result.source_job,
                    "ally_job": result.ally_job,
                    "gauge_cost": result.gauge_cost,
                    "trigger_reason": trigger_reason
                })
            self.logger.info(
                f"체인어빌리티 트리거 ({trigger_reason}): "
                f"{len(results)}개 사용 가능"
            )

        return results

    def execute_bond_skill(self, result: Any, actor: Any) -> Dict[str, Any]:
        """
        연계스킬 효과 적용 (자동)

        Returns:
            실행 결과 딕셔너리
        """
        skill = result.skill
        effect = skill.effect
        effect_type = effect.get("type", "")
        exec_result = {"skill_name": skill.name, "source": result.source_job, "effects": []}

        # 연계스킬 효과 적용 — 아군 캐릭터 참조
        source_char = next(
            (c for c in self.allies if hasattr(c, 'character_class') and c.character_class == result.source_job),
            None
        )
        target_char = next(
            (c for c in self.allies if hasattr(c, 'character_class') and c.character_class == result.ally_job),
            None
        )

        if effect_type == "additional_attack":
            # 추가 공격 (strength/magic 프로퍼티 사용 + 레벨 스케일링)
            multiplier = effect.get("multiplier", 0.5)
            damage_type = effect.get("damage_type", "physical")
            if source_char and self.enemies:
                import random
                alive_enemies = [e for e in self.enemies if getattr(e, 'is_alive', True)]
                target = random.choice(alive_enemies) if alive_enemies else self.enemies[0]
                if damage_type == "physical":
                    base_dmg = getattr(source_char, 'strength', 50)
                else:
                    base_dmg = getattr(source_char, 'magic', 50)
                # 적 방어력 고려
                if damage_type == "physical":
                    target_def = getattr(target, 'defense', 0) if hasattr(target, 'defense') else 0
                else:
                    target_def = getattr(target, 'spirit', 0) if hasattr(target, 'spirit') else 0
                # 레벨 스케일링 (일반 BRV 공격과 동일)
                attacker_level = getattr(source_char, 'level', 1)
                from src.core.config import get_config
                config = get_config()
                level_scaling_per_level = config.get("combat.damage.level_scaling_per_level", 0.3)
                level_scaling = 1.0 + (attacker_level - 1) * level_scaling_per_level
                raw_dmg = int(base_dmg * multiplier * level_scaling)
                # 방어력 비례 경감 (flat 차감 대신 비율 경감)
                def_factor = 200.0 / (200.0 + target_def) if target_def > 0 else 1.0
                dmg = max(1, int(raw_dmg * def_factor))
                target.current_hp = max(0, getattr(target, 'current_hp', 0) - dmg)
                exec_result["effects"].append({"type": "damage", "target": getattr(target, 'name', ''), "amount": dmg})

        elif effect_type == "redirect_damage":
            # 피해 전환 — 대상에게 리다이렉트 마커 부여
            reduction = effect.get("damage_reduction", 0.5)
            if target_char:
                target_char._bond_redirect_active = True
                target_char._bond_redirect_reduction = reduction
                exec_result["effects"].append({"type": "redirect", "reduction": reduction})

        elif effect_type == "heal":
            amount_pct = effect.get("amount_percent", 0.1)
            if target_char:
                heal_amt = int(getattr(target_char, 'max_hp', 100) * amount_pct)
                target_char.current_hp = min(getattr(target_char, 'max_hp', 100), target_char.current_hp + heal_amt)
                exec_result["effects"].append({"type": "heal", "target": target_char.name, "amount": heal_amt})

        elif effect_type == "buff":
            # 버프 실제 적용 — YAML의 mult/add 키를 StatusType으로 매핑
            from src.combat.status_effects import StatusType, StatusEffect as CombatStatusEffect

            # YAML 키 → (StatusType, 한글명, intensity 제수)
            buff_stat_map = {
                "physical_attack_mult": (StatusType.BOOST_ATK, "공격력", 0.2),
                "magic_attack_mult": (StatusType.BOOST_MAGIC_ATK, "마법공격력", 0.2),
                "defense_mult": (StatusType.BOOST_DEF, "방어력", 0.2),
                "magic_defense_mult": (StatusType.BOOST_MAGIC_DEF, "마법방어력", 0.2),
                "speed_mult": (StatusType.BOOST_SPD, "속도", 0.3),
                "critical_rate_add": (StatusType.BOOST_CRIT, "치명타율", 0.25),
                "critical_damage_mult": (StatusType.BOOST_CRIT, "치명타 위력", 0.25),
                "all_stats_mult": (StatusType.BOOST_ALL_STATS, "모든 능력치", 0.15),
            }

            buff_duration = effect.get("duration", 3)
            buff_target_type = effect.get("target", "self")

            # 버프 대상 결정
            if buff_target_type == "all_allies":
                buff_targets = [c for c in self.allies if getattr(c, 'is_alive', True)]
            elif buff_target_type == "self":
                buff_targets = [source_char] if source_char else []
            else:
                # healed_ally, attacking_ally, buffed_ally → target_char
                buff_targets = [target_char] if target_char else ([actor] if actor else [])

            buff_descs = []
            for stat_key, (status_type, stat_name, divisor) in buff_stat_map.items():
                stat_value = effect.get(stat_key)
                if stat_value is None:
                    continue

                # intensity 계산: 각 StatusType의 공식에 맞게 역산
                if "_add" in stat_key:
                    intensity = stat_value / divisor
                    pct = int(stat_value * 100)
                else:
                    intensity = (stat_value - 1.0) / divisor
                    pct = int((stat_value - 1.0) * 100)
                buff_descs.append(f"{stat_name}+{pct}%")

                for bt in buff_targets:
                    if bt and hasattr(bt, 'status_manager'):
                        try:
                            se = CombatStatusEffect(
                                name=f"연계:{skill.name}({stat_name})",
                                status_type=status_type,
                                duration=buff_duration,
                                intensity=intensity,
                            )
                            bt.status_manager.add_status(se)
                        except Exception as e:
                            self.logger.warning(f"연계스킬 버프 적용 실패: {e}")

            buff_desc = ", ".join(buff_descs) if buff_descs else skill.name
            target_names = ", ".join(getattr(bt, 'name', '?') for bt in buff_targets if bt) if buff_targets else "대상"
            exec_result["effects"].append({"type": "buff", "target": target_names, "buff_desc": buff_desc})

        elif effect_type == "shield":
            # 실제 보호막 적용 (StatusType.SHIELD)
            from src.combat.status_effects import StatusEffect as CombatStatusEffect, StatusType
            amount_pct = effect.get("amount_percent", 0.1)
            shield_duration = effect.get("duration", 5)
            shield_target = target_char or actor
            if shield_target and hasattr(shield_target, 'status_manager'):
                shield_amt = int(getattr(shield_target, 'max_hp', 100) * amount_pct)
                shield_effect = CombatStatusEffect(
                    name=skill.name,
                    status_type=StatusType.SHIELD,
                    duration=shield_duration,
                    intensity=shield_amt,
                    source_id=getattr(actor, 'name', 'Bond'),
                    metadata={"shield_hp": shield_amt},
                )
                shield_target.status_manager.add_status(shield_effect, allow_refresh=True)
                exec_result["effects"].append({"type": "shield", "target": getattr(shield_target, 'name', ''), "amount": shield_amt})

        elif effect_type == "mp_restore":
            amount_pct = effect.get("amount_percent", 0.05)
            if target_char:
                restore = int(getattr(target_char, 'max_mp', 50) * amount_pct)
                target_char.current_mp = min(getattr(target_char, 'max_mp', 50), target_char.current_mp + restore)
                exec_result["effects"].append({"type": "mp_restore", "target": target_char.name, "amount": restore})

        elif effect_type == "hp_drain":
            # HP 흡수 공격 (뱀파이어 등)
            multiplier = effect.get("multiplier", 1.0)
            drain_percent = effect.get("drain_percent", 0.3)
            if source_char and self.enemies:
                import random
                alive_enemies = [e for e in self.enemies if getattr(e, 'is_alive', True)]
                if alive_enemies:
                    target_enemy = random.choice(alive_enemies)
                    base_dmg = getattr(source_char, 'strength', 50)
                    attacker_level = getattr(source_char, 'level', 1)
                    from src.core.config import get_config
                    config = get_config()
                    level_scaling_per_level = config.get("combat.damage.level_scaling_per_level", 0.3)
                    level_scaling = 1.0 + (attacker_level - 1) * level_scaling_per_level
                    raw_dmg = int(base_dmg * multiplier * level_scaling)
                    target_def = getattr(target_enemy, 'defense', 0)
                    def_factor = 200.0 / (200.0 + target_def) if target_def > 0 else 1.0
                    dmg = max(1, int(raw_dmg * def_factor))
                    target_enemy.current_hp = max(0, getattr(target_enemy, 'current_hp', 0) - dmg)
                    # 흡혈
                    heal_amount = int(dmg * drain_percent)
                    max_hp = getattr(source_char, 'max_hp', 100)
                    actual_heal = min(heal_amount, max_hp - getattr(source_char, 'current_hp', 0))
                    actual_heal = max(0, actual_heal)
                    source_char.current_hp = min(max_hp, source_char.current_hp + actual_heal)
                    exec_result["effects"].append({
                        "type": "hp_drain", "target": getattr(target_enemy, 'name', ''),
                        "damage": dmg, "heal": actual_heal
                    })

        elif effect_type == "status_apply":
            # 상태이상 부여 (매혹, 재생 등)
            from src.combat.status_effects import StatusType, StatusEffect as CombatStatusEffect
            status_id = effect.get("status", "")
            duration = effect.get("duration", 2)
            chance = effect.get("chance", 1.0)

            import random
            if random.random() > chance:
                exec_result["effects"].append({"type": "status_apply", "success": False, "status": status_id})
            else:
                target_type = effect.get("target", "enemy")
                status_targets = []
                if target_type in ("enemy", "same_target"):
                    alive_enemies = [e for e in self.enemies if getattr(e, 'is_alive', True)]
                    if alive_enemies:
                        status_targets = [random.choice(alive_enemies)]
                elif target_type in ("healed_ally", "damaged_ally", "attacking_ally", "buffed_ally"):
                    if target_char:
                        status_targets = [target_char]
                elif target_type == "self":
                    if source_char:
                        status_targets = [source_char]

                status_map = {
                    "poison": StatusType.POISON,
                    "blind": StatusType.BLIND,
                    "silence": StatusType.SILENCE,
                    "slow": StatusType.SLOW,
                    "stun": StatusType.STUN,
                    "charm": StatusType.CHARM,
                    "sleep": StatusType.SLEEP,
                    "regen": StatusType.REGENERATION,
                    "haste": StatusType.HASTE,
                    "burn": StatusType.POISON,
                    "paralyze": StatusType.STUN,
                }
                st = status_map.get(status_id)
                if st and status_targets:
                    for st_target in status_targets:
                        if hasattr(st_target, 'status_manager'):
                            try:
                                se = CombatStatusEffect(
                                    name=f"연계:{skill.name}",
                                    status_type=st,
                                    duration=duration,
                                    intensity=1.0,
                                )
                                st_target.status_manager.add_status(se)
                            except Exception as e:
                                self.logger.warning(f"연계스킬 상태이상 적용 실패: {e}")
                    exec_result["effects"].append({
                        "type": "status_apply", "success": True, "status": status_id,
                        "target": ", ".join(getattr(t, 'name', '?') for t in status_targets)
                    })

        elif effect_type == "debuff":
            # 디버프 부여 (방어력 감소 등) — buff 핸들러와 동일 패턴, 역방향
            from src.combat.status_effects import StatusType, StatusEffect as CombatStatusEffect
            debuff_duration = effect.get("duration", 2)
            target_type = effect.get("target", "enemy")
            debuff_targets = []
            if target_type in ("enemy", "same_target"):
                alive_enemies = [e for e in self.enemies if getattr(e, 'is_alive', True)]
                if alive_enemies:
                    import random
                    debuff_targets = [random.choice(alive_enemies)]
            elif target_type == "all_enemies":
                debuff_targets = [e for e in self.enemies if getattr(e, 'is_alive', True)]

            debuff_stat_map = {
                "defense_mult": (StatusType.BOOST_DEF, "방어력", 0.2),
                "magic_defense_mult": (StatusType.BOOST_MAGIC_DEF, "마법방어력", 0.2),
                "physical_attack_mult": (StatusType.BOOST_ATK, "공격력", 0.2),
                "magic_attack_mult": (StatusType.BOOST_MAGIC_ATK, "마법공격력", 0.2),
                "speed_mult": (StatusType.BOOST_SPD, "속도", 0.3),
            }

            debuff_descs = []
            for stat_key, (status_type, stat_name, divisor) in debuff_stat_map.items():
                stat_value = effect.get(stat_key)
                if stat_value is None:
                    continue
                intensity = (stat_value - 1.0) / divisor
                pct = int((1.0 - stat_value) * 100)
                debuff_descs.append(f"{stat_name}-{pct}%")

                for dt in debuff_targets:
                    if dt and hasattr(dt, 'status_manager'):
                        try:
                            se = CombatStatusEffect(
                                name=f"연계:{skill.name}({stat_name})",
                                status_type=status_type,
                                duration=debuff_duration,
                                intensity=intensity,
                            )
                            dt.status_manager.add_status(se)
                        except Exception as e:
                            self.logger.warning(f"연계스킬 디버프 적용 실패: {e}")

            target_names = ", ".join(getattr(dt, 'name', '?') for dt in debuff_targets) if debuff_targets else "대상"
            exec_result["effects"].append({
                "type": "debuff", "target": target_names,
                "debuff_desc": ", ".join(debuff_descs) if debuff_descs else skill.name
            })

        elif effect_type == "revive":
            # 부활 (사망 아군 부활)
            hp_percent = effect.get("hp_percent", 0.15)
            dead_allies = [a for a in self.allies
                           if not getattr(a, 'is_alive', True) or getattr(a, 'current_hp', 0) <= 0]
            if dead_allies:
                revive_target = dead_allies[0]
                max_hp = getattr(revive_target, 'max_hp', 100)
                revive_hp = max(1, int(max_hp * hp_percent))
                revive_target.current_hp = revive_hp
                if hasattr(revive_target, 'is_alive'):
                    revive_target.is_alive = True
                exec_result["effects"].append({
                    "type": "revive", "target": getattr(revive_target, 'name', ''),
                    "hp": revive_hp
                })

        elif effect_type == "brv_damage":
            # BRV 데미지 (브레이크 용)
            multiplier = effect.get("multiplier", 1.5)
            if source_char and self.enemies:
                import random
                alive_enemies = [e for e in self.enemies if getattr(e, 'is_alive', True)]
                if alive_enemies:
                    target_enemy = random.choice(alive_enemies)
                    base_dmg = getattr(source_char, 'strength', 50)
                    attacker_level = getattr(source_char, 'level', 1)
                    from src.core.config import get_config
                    config = get_config()
                    level_scaling_per_level = config.get("combat.damage.level_scaling_per_level", 0.3)
                    level_scaling = 1.0 + (attacker_level - 1) * level_scaling_per_level
                    brv_dmg = max(1, int(base_dmg * multiplier * level_scaling))
                    old_brv = getattr(target_enemy, 'current_brv', 0)
                    target_enemy.current_brv = max(0, old_brv - brv_dmg)
                    is_break = old_brv > 0 and target_enemy.current_brv <= 0
                    exec_result["effects"].append({
                        "type": "brv_damage", "target": getattr(target_enemy, 'name', ''),
                        "amount": brv_dmg, "is_break": is_break
                    })

        # 호감도 증가
        self._affinity_manager.on_battle_action(result.source_job, [result.ally_job])

        return exec_result

    def execute_chain_ability(self, result: Any) -> Dict[str, Any]:
        """
        체인어빌리티 실행 (플레이어가 확정한 후 호출)

        팀워크 게이지를 소모하고 효과를 적용합니다.
        execute_bond_skill과 동일한 패턴으로 모든 효과 타입을 지원합니다.
        """
        ability = result.ability
        gauge_cost = result.gauge_cost

        # 게이지 소모
        if self.party:
            self.party.consume_teamwork_gauge(gauge_cost)

        # 쿨다운 설정
        if self._affinity_manager:
            self._affinity_manager.confirm_chain_ability(result)
            # 합체기 사용 시 호감도 대폭 증가
            self._affinity_manager.on_combo_skill(result.source_job, result.ally_job)

        # 효과 적용 — execute_bond_skill과 동일 패턴
        effect = ability.effect
        effect_type = effect.get("type", "")
        exec_result = {"ability_name": ability.name, "source": result.source_job, "gauge_used": gauge_cost, "effects": []}

        # 아군 캐릭터 참조
        source_char = next(
            (c for c in self.allies if hasattr(c, 'character_class') and c.character_class == result.source_job),
            None
        )
        ally_char = next(
            (c for c in self.allies if hasattr(c, 'character_class') and c.character_class == result.ally_job),
            None
        )

        if effect_type == "additional_attack" or effect_type == "counter_attack":
            # 추가 공격 — 메인 데미지 계산기 사용 (BRV 데미지 → 직접 HP 적용)
            multiplier = effect.get("multiplier", 1.2)
            damage_type = effect.get("damage_type", "physical")
            element = effect.get("element", None)
            if source_char and self.enemies:
                import random
                alive_enemies = [e for e in self.enemies if getattr(e, 'is_alive', True)]
                target = random.choice(alive_enemies) if alive_enemies else self.enemies[0]
                # 메인 데미지 계산기로 BRV 데미지 산출
                if damage_type in ("magical",):
                    dmg_result = self.damage_calc.calculate_magic_damage(
                        source_char, target, multiplier, element=element,
                        ignore_evasion=True
                    )
                else:
                    dmg_result = self.damage_calc.calculate_brv_damage(
                        source_char, target, multiplier, element=element,
                        ignore_evasion=True
                    )
                # BRV 데미지를 직접 HP 피해로 적용 (체인 어빌리티는 보너스 공격)
                hp_damage = max(1, dmg_result.final_damage)
                target.current_hp = max(0, getattr(target, 'current_hp', 0) - hp_damage)
                is_crit = dmg_result.is_critical
                exec_result["effects"].append({
                    "type": "damage", "target": getattr(target, 'name', ''),
                    "amount": hp_damage, "critical": is_crit
                })

        elif effect_type == "buff":
            # 버프 실제 적용 — YAML의 mult/add 키를 StatusType으로 매핑
            from src.combat.status_effects import StatusType, StatusEffect as CombatStatusEffect

            buff_stat_map = {
                "physical_attack_mult": (StatusType.BOOST_ATK, "공격력", 0.2),
                "magic_attack_mult": (StatusType.BOOST_MAGIC_ATK, "마법공격력", 0.2),
                "defense_mult": (StatusType.BOOST_DEF, "방어력", 0.2),
                "magic_defense_mult": (StatusType.BOOST_MAGIC_DEF, "마법방어력", 0.2),
                "speed_mult": (StatusType.BOOST_SPD, "속도", 0.3),
                "critical_rate_add": (StatusType.BOOST_CRIT, "치명타율", 0.25),
                "critical_damage_mult": (StatusType.BOOST_CRIT, "치명타 위력", 0.25),
                "all_stats_mult": (StatusType.BOOST_ALL_STATS, "모든 능력치", 0.15),
            }

            buff_duration = effect.get("duration", 3)
            buff_target_type = effect.get("target", "all_allies")

            if buff_target_type == "all_allies":
                buff_targets = [c for c in self.allies if getattr(c, 'is_alive', True)]
            elif buff_target_type == "self":
                buff_targets = [source_char] if source_char else []
            else:
                buff_targets = [ally_char] if ally_char else []

            buff_descs = []
            for stat_key, (status_type, stat_name, divisor) in buff_stat_map.items():
                stat_value = effect.get(stat_key)
                if stat_value is None:
                    continue
                if "_add" in stat_key:
                    intensity = stat_value / divisor
                    pct = int(stat_value * 100)
                else:
                    intensity = (stat_value - 1.0) / divisor
                    pct = int((stat_value - 1.0) * 100)
                buff_descs.append(f"{stat_name}+{pct}%")

                for bt in buff_targets:
                    if bt and hasattr(bt, 'status_manager'):
                        try:
                            se = CombatStatusEffect(
                                name=f"체인:{ability.name}({stat_name})",
                                status_type=status_type,
                                duration=buff_duration,
                                intensity=intensity,
                            )
                            bt.status_manager.add_status(se)
                        except Exception as e:
                            self.logger.warning(f"체인어빌리티 버프 적용 실패: {e}")

            buff_desc = ", ".join(buff_descs) if buff_descs else ability.name
            target_names = ", ".join(getattr(bt, 'name', '?') for bt in buff_targets if bt)
            exec_result["effects"].append({"type": "buff", "target": target_names, "buff_desc": buff_desc})

        elif effect_type == "debuff":
            # 디버프 — 적에게 약화 적용
            from src.combat.status_effects import StatusType, StatusEffect as CombatStatusEffect

            debuff_stat_map = {
                "physical_attack_mult": (StatusType.REDUCE_ATK, "공격력", 0.2),
                "magic_attack_mult": (StatusType.REDUCE_MAGIC_ATK, "마법공격력", 0.2),
                "defense_mult": (StatusType.REDUCE_DEF, "방어력", 0.2),
                "magic_defense_mult": (StatusType.REDUCE_MAGIC_DEF, "마법방어력", 0.2),
                "speed_mult": (StatusType.REDUCE_SPD, "속도", 0.3),
            }

            debuff_duration = effect.get("duration", 3)
            if self.enemies:
                alive_enemies = [e for e in self.enemies if getattr(e, 'is_alive', True)]
                debuff_targets = alive_enemies if alive_enemies else self.enemies[:1]
                debuff_descs = []
                for stat_key, (status_type, stat_name, divisor) in debuff_stat_map.items():
                    stat_value = effect.get(stat_key)
                    if stat_value is None:
                        continue
                    intensity = (1.0 - stat_value) / divisor if stat_value < 1.0 else 0.5
                    pct = int((1.0 - stat_value) * 100) if stat_value < 1.0 else 10
                    debuff_descs.append(f"{stat_name}-{pct}%")
                    for dt in debuff_targets:
                        if dt and hasattr(dt, 'status_manager'):
                            try:
                                se = CombatStatusEffect(
                                    name=f"체인:{ability.name}({stat_name})",
                                    status_type=status_type,
                                    duration=debuff_duration,
                                    intensity=intensity,
                                )
                                dt.status_manager.add_status(se)
                            except Exception as e:
                                self.logger.warning(f"체인어빌리티 디버프 적용 실패: {e}")
                debuff_desc = ", ".join(debuff_descs) if debuff_descs else ability.name
                exec_result["effects"].append({"type": "debuff", "desc": debuff_desc})

        elif effect_type == "heal":
            amount_pct = effect.get("amount_percent", 0.3)
            heal_target_type = effect.get("target", "all_allies")
            if heal_target_type == "all_allies":
                targets = [c for c in self.allies if getattr(c, 'is_alive', True)]
            else:
                targets = [ally_char] if ally_char else []
            for ally in targets:
                heal = int(getattr(ally, 'max_hp', 100) * amount_pct)
                ally.current_hp = min(getattr(ally, 'max_hp', 100), ally.current_hp + heal)
                exec_result["effects"].append({"type": "heal", "target": getattr(ally, 'name', ''), "amount": heal})

        elif effect_type == "revive":
            hp_pct = effect.get("hp_percent", 0.3)
            for ally in self.allies:
                if not getattr(ally, 'is_alive', True):
                    ally.is_alive = True
                    ally.current_hp = int(getattr(ally, 'max_hp', 100) * hp_pct)
                    exec_result["effects"].append({"type": "revive", "target": getattr(ally, 'name', ''), "hp": ally.current_hp})

        elif effect_type == "shield":
            # 실제 보호막 적용 (StatusType.SHIELD)
            from src.combat.status_effects import StatusEffect as CombatStatusEffect, StatusType
            amount_pct = effect.get("amount_percent", 0.15)
            shield_duration = effect.get("duration", 5)
            shield_target_type = effect.get("target", "all_allies")
            if shield_target_type == "all_allies":
                targets = [c for c in self.allies if getattr(c, 'is_alive', True)]
            else:
                targets = [ally_char] if ally_char else []
            for st in targets:
                if st and hasattr(st, 'status_manager'):
                    shield_amt = int(getattr(st, 'max_hp', 100) * amount_pct)
                    shield_effect = CombatStatusEffect(
                        name=ability.name,
                        status_type=StatusType.SHIELD,
                        duration=shield_duration,
                        intensity=shield_amt,
                        source_id=getattr(source_char, 'name', 'Chain'),
                        metadata={"shield_hp": shield_amt},
                    )
                    st.status_manager.add_status(shield_effect, allow_refresh=True)
                    exec_result["effects"].append({"type": "shield", "target": getattr(st, 'name', ''), "amount": shield_amt})

        elif effect_type == "mp_restore":
            amount_pct = effect.get("amount_percent", 0.1)
            mp_target_type = effect.get("target", "all_allies")
            if mp_target_type == "all_allies":
                targets = [c for c in self.allies if getattr(c, 'is_alive', True)]
            else:
                targets = [ally_char] if ally_char else []
            for mt in targets:
                if mt and hasattr(mt, 'current_mp'):
                    restore = int(getattr(mt, 'max_mp', 50) * amount_pct)
                    mt.current_mp = min(getattr(mt, 'max_mp', 50), mt.current_mp + restore)
                    exec_result["effects"].append({"type": "mp_restore", "target": getattr(mt, 'name', ''), "amount": restore})

        elif effect_type == "hp_drain":
            # HP 흡수 — 적에게 데미지 + 자신 회복
            multiplier = effect.get("multiplier", 1.0)
            drain_pct = effect.get("drain_percent", 0.5)
            if source_char and self.enemies:
                import random
                alive_enemies = [e for e in self.enemies if getattr(e, 'is_alive', True)]
                target = random.choice(alive_enemies) if alive_enemies else self.enemies[0]
                base_dmg = getattr(source_char, 'magic', 50)
                attacker_level = getattr(source_char, 'level', 1)
                from src.core.config import get_config
                config = get_config()
                level_scaling = 1.0 + (attacker_level - 1) * config.get("combat.damage.level_scaling_per_level", 0.3)
                target_def = getattr(target, 'spirit', 0)
                def_factor = 200.0 / (200.0 + target_def) if target_def > 0 else 1.0
                dmg = max(1, int(base_dmg * multiplier * level_scaling * def_factor))
                target.current_hp = max(0, getattr(target, 'current_hp', 0) - dmg)
                heal = int(dmg * drain_pct)
                source_char.current_hp = min(getattr(source_char, 'max_hp', 100), source_char.current_hp + heal)
                exec_result["effects"].append({"type": "damage", "target": getattr(target, 'name', ''), "amount": dmg})
                exec_result["effects"].append({"type": "heal", "target": getattr(source_char, 'name', ''), "amount": heal})

        elif effect_type == "brv_damage":
            # BRV 데미지 — 적의 BRV를 깎음
            multiplier = effect.get("multiplier", 1.5)
            if source_char and self.enemies:
                import random
                alive_enemies = [e for e in self.enemies if getattr(e, 'is_alive', True)]
                target = random.choice(alive_enemies) if alive_enemies else self.enemies[0]
                base_dmg = getattr(source_char, 'strength', 50)
                attacker_level = getattr(source_char, 'level', 1)
                from src.core.config import get_config
                config = get_config()
                level_scaling = 1.0 + (attacker_level - 1) * config.get("combat.damage.level_scaling_per_level", 0.3)
                target_def = getattr(target, 'defense', 0)
                def_factor = 200.0 / (200.0 + target_def) if target_def > 0 else 1.0
                brv_dmg = max(1, int(base_dmg * multiplier * level_scaling * def_factor))
                old_brv = getattr(target, 'current_brv', 0)
                target.current_brv = max(0, old_brv - brv_dmg)
                exec_result["effects"].append({"type": "brv_damage", "target": getattr(target, 'name', ''), "amount": brv_dmg})

        elif effect_type == "status_apply":
            # 상태이상 부여
            from src.combat.status_effects import StatusType, StatusEffect as CombatStatusEffect
            status_name = effect.get("status", "")
            duration = effect.get("duration", 3)
            status_map = {
                "stun": StatusType.STUN, "poison": StatusType.POISON,
                "burn": StatusType.BURN, "freeze": StatusType.FREEZE,
                "bleed": StatusType.BLEED, "blind": StatusType.BLIND,
                "silence": StatusType.SILENCE, "slow": StatusType.SLOW,
            }
            st = status_map.get(status_name)
            if st and self.enemies:
                alive_enemies = [e for e in self.enemies if getattr(e, 'is_alive', True)]
                for enemy in alive_enemies:
                    if hasattr(enemy, 'status_manager'):
                        try:
                            se = CombatStatusEffect(
                                name=f"체인:{ability.name}",
                                status_type=st,
                                duration=duration,
                                intensity=1.0,
                            )
                            enemy.status_manager.add_status(se)
                        except Exception as e:
                            self.logger.warning(f"체인어빌리티 상태이상 적용 실패: {e}")
                exec_result["effects"].append({"type": "status", "status": status_name, "targets": len(alive_enemies)})

        elif effect_type == "redirect_damage":
            # 피해 전환
            reduction = effect.get("damage_reduction", 0.5)
            redirect_target = source_char or ally_char
            if redirect_target:
                redirect_target._bond_redirect_active = True
                redirect_target._bond_redirect_reduction = reduction
                exec_result["effects"].append({"type": "redirect", "reduction": reduction})

        event_bus.publish(Events.CHAIN_ABILITY_CONFIRMED, {
            "ability": ability, "result": exec_result
        })

        self.logger.info(f"체인어빌리티 실행: {ability.name} (게이지 -{gauge_cost})")
        return exec_result

    def on_affinity_turn_end(self):
        """턴 종료 시 호감도 쿨다운 틱"""
        if self._affinity_manager:
            self._affinity_manager.tick_cooldowns()

    def on_affinity_battle_end(self):
        """전투 종료 시 호감도 증가"""
        if not self._affinity_manager:
            return
        party_jobs = [
            c.character_class for c in self.allies
            if hasattr(c, 'character_class')
        ]
        self._affinity_manager.on_battle_victory(party_jobs)

    # ─── 직업 시너지/합체기 ─────────────────────────────────

    @property
    def synergy_manager(self):
        return self._synergy_manager

    def get_available_combo_skills(self) -> list:
        """현재 발동 가능한 합체기 목록"""
        if not self._synergy_manager or not self.party:
            return []
        party_jobs = [
            c.character_class for c in self.allies
            if hasattr(c, 'character_class') and getattr(c, 'is_alive', True)
        ]
        return self._synergy_manager.get_available_combos(
            party_jobs, self._affinity_manager, self.party.teamwork_gauge
        )

    def execute_combo_skill(self, combo_skill, target=None):
        """
        합체기 실행

        Args:
            combo_skill: ComboSkill 객체
            target: 대상 (single 타겟인 경우)

        Returns:
            dict: 실행 결과
        """
        if not self.party:
            return {"success": False, "message": "파티 없음"}

        # 게이지 소모
        if not self.party.consume_teamwork_gauge(combo_skill.gauge_cost):
            return {"success": False, "message": "게이지 부족"}

        result = {"success": True, "effects": [], "message": ""}
        all_enemies = [e for e in self.enemies if getattr(e, 'is_alive', True)]
        all_allies = [a for a in self.allies if getattr(a, 'is_alive', True)]

        # 참여 캐릭터 찾기
        participants = []
        for ally in self.allies:
            if hasattr(ally, 'character_class') and ally.character_class in combo_skill.required_jobs:
                participants.append(ally)

        for effect in combo_skill.effects:
            effect_type = effect.get("type", "damage")
            target_type = effect.get("target", "all_enemies")

            if effect_type == "damage":
                multiplier = effect.get("multiplier", 3.0)
                damage_type = effect.get("damage_type", "physical")

                targets = []
                if target_type == "all_enemies":
                    targets = all_enemies
                elif target_type == "single" and target:
                    targets = [target]
                elif target_type == "single" and all_enemies:
                    targets = [all_enemies[0]]

                # ── 합체기 협동 패턴 시스템 ──
                # 모든 합체기는 "P1(셋업) → P2(피니시)" 구조의 BRV→HP 공격이지만,
                # combo_pattern에 따라 셋업 단계가 달라진다.
                pattern = getattr(combo_skill, 'combo_pattern', 'brv_hp')
                brv_attacker = participants[0]
                hp_attacker = participants[1] if len(participants) >= 2 else participants[0]

                # BRV 공격자의 스탯 결정 (damage_calculator와 동일한 멀티 속성명 패턴)
                def _resolve_stat(char, attr_names, default=10):
                    for a in attr_names:
                        if hasattr(char, a):
                            return getattr(char, a)
                    return default

                _phys_atk_keys = ['physical_attack', 'p_atk', 'attack', 'strength']
                _mag_atk_keys = ['magic_attack', 'm_atk', 'magic', 'intelligence']
                _phys_def_keys = ['physical_defense', 'p_def', 'defense']
                _mag_def_keys = ['magic_defense', 'm_def']

                if damage_type == "physical":
                    brv_atk_stat = _resolve_stat(brv_attacker, _phys_atk_keys)
                    def_keys = _phys_def_keys
                elif damage_type in ("magic", "holy", "dark", "tech"):
                    brv_atk_stat = _resolve_stat(brv_attacker, _mag_atk_keys)
                    def_keys = _mag_def_keys
                else:
                    from src.combat.job_synergy import get_job_category
                    brv_cat = get_job_category(brv_attacker.character_class)
                    if brv_cat in ("magic", "support"):
                        brv_atk_stat = _resolve_stat(brv_attacker, _mag_atk_keys)
                        def_keys = _mag_def_keys
                    else:
                        brv_atk_stat = _resolve_stat(brv_attacker, _phys_atk_keys)
                        def_keys = _phys_def_keys

                # ── 패턴별 셋업 보정 ──
                empower_mult = 1.0
                def_reduction = 1.0
                sacrifice_bonus = 0

                if pattern == "empower_strike":
                    # 강화→일격: P1이 P2를 강화 (1.5배 피해)
                    empower_mult = 1.5
                    result["effects"].append({
                        "type": "empower", "caster": brv_attacker.name,
                        "target": hp_attacker.name,
                        "message": f"{brv_attacker.name}이(가) {hp_attacker.name}에게 힘을 불어넣는다!"
                    })
                    self.logger.info(f"[합체기 강화] {brv_attacker.name} → {hp_attacker.name} 강화 (x1.5)")

                elif pattern == "weaken_execute":
                    # 약화→처형: P1이 적 방어력 절반 감소
                    def_reduction = 0.5
                    for t in targets:
                        result["effects"].append({
                            "type": "weaken", "caster": brv_attacker.name,
                            "target": t.name,
                            "message": f"{brv_attacker.name}이(가) {t.name}의 약점을 간파한다!"
                        })
                    self.logger.info(f"[합체기 약화] {brv_attacker.name}이 적 방어력 50% 감소")

                elif pattern == "sacrifice_burst":
                    # 희생→폭발: P1이 HP 15%를 희생하여 추가 피해
                    sacrifice_hp = int(getattr(brv_attacker, 'max_hp', 100) * 0.15)
                    brv_attacker.current_hp = max(1, getattr(brv_attacker, 'current_hp', 0) - sacrifice_hp)
                    sacrifice_bonus = sacrifice_hp
                    result["effects"].append({
                        "type": "sacrifice", "caster": brv_attacker.name,
                        "hp_lost": sacrifice_hp,
                        "message": f"{brv_attacker.name}이(가) 자신의 생명력을 바쳐 힘을 끌어올린다!"
                    })
                    self.logger.info(f"[합체기 희생] {brv_attacker.name} HP -{sacrifice_hp} → 추가 피해 +{sacrifice_bonus}")

                brv_base = int(brv_atk_stat * multiplier * empower_mult) + sacrifice_bonus

                for t in targets:
                    # [1단계] BRV 공격: 적의 BRV 탈취
                    defense = int(_resolve_stat(t, def_keys, 0) * def_reduction)
                    if effect.get("ignore_defense"):
                        defense = 0
                    actual_brv_dmg = max(1, brv_base - defense // 2)

                    old_target_brv = getattr(t, 'current_brv', 0)
                    t.current_brv = max(0, old_target_brv - actual_brv_dmg)
                    brv_stolen = min(actual_brv_dmg, max(0, old_target_brv))

                    result["effects"].append({
                        "type": "brv_attack", "attacker": brv_attacker.name,
                        "target": t.name, "brv_damage": actual_brv_dmg,
                        "brv_stolen": brv_stolen
                    })

                    # [2단계] BRV 전달 → HP 공격자
                    result["effects"].append({
                        "type": "brv_transfer",
                        "from": brv_attacker.name, "to": hp_attacker.name,
                        "amount": brv_stolen
                    })

                    # [3단계] HP 공격: 계산된 BRV 데미지를 직접 HP 피해로 변환
                    # (합체기는 필살기이므로 타겟 BRV 잔량에 무관하게 전체 피해 적용)
                    hp_damage = actual_brv_dmg
                    if effect.get("critical_guaranteed"):
                        hp_damage = int(hp_damage * 1.5)

                    t.current_hp = max(0, getattr(t, 'current_hp', 0) - hp_damage)
                    result["effects"].append({
                        "type": "hp_attack", "attacker": hp_attacker.name,
                        "target": t.name, "hp_damage": hp_damage,
                        "damage_type": damage_type
                    })

                    self.logger.info(
                        f"[합체기 {pattern}] {brv_attacker.name} BRV {actual_brv_dmg}"
                        f" → {t.name} 탈취 {brv_stolen}"
                        f" → {hp_attacker.name} HP {hp_damage}"
                    )

                    # HP 흡수
                    drain_pct = effect.get("hp_drain_percent", 0)
                    if drain_pct > 0:
                        drain_amount = int(hp_damage * drain_pct / 100)
                        for p in participants:
                            heal = drain_amount // len(participants)
                            p.current_hp = min(getattr(p, 'max_hp', 999), getattr(p, 'current_hp', 0) + heal)

                    # 상태이상 부여
                    status = effect.get("status")
                    if status and hasattr(t, 'status_manager'):
                        duration = effect.get("status_duration", 2)
                        try:
                            t.status_manager.apply_status(status, duration=duration)
                        except Exception:
                            pass

                    # 사망 체크
                    if getattr(t, 'current_hp', 0) <= 0:
                        t.is_alive = False

            elif effect_type == "heal":
                heal_pct = effect.get("heal_percent", 30)
                cleanse = effect.get("cleanse", False)
                targets = all_allies if target_type == "all_allies" else [target] if target else all_allies

                for t in targets:
                    max_hp = getattr(t, 'max_hp', 100)
                    heal_amount = int(max_hp * heal_pct / 100)
                    t.current_hp = min(max_hp, getattr(t, 'current_hp', 0) + heal_amount)
                    result["effects"].append({"type": "heal", "target": t.name, "amount": heal_amount})
                    if cleanse and hasattr(t, 'status_manager'):
                        t.status_manager.clear_debuffs()

            elif effect_type == "buff":
                from src.combat.status_effects import StatusType, StatusEffect as CombatStatusEffect
                duration = effect.get("duration", 3)
                buff_targets = all_allies if target_type == "all_allies" else participants if target_type == "self_pair" else participants

                buff_stat_map = {
                    "physical_attack_mult": (StatusType.BOOST_ATK, "공격력", 0.2),
                    "magic_attack_mult": (StatusType.BOOST_MAGIC_ATK, "마법공격력", 0.2),
                    "defense_mult": (StatusType.BOOST_DEF, "방어력", 0.2),
                    "magic_defense_mult": (StatusType.BOOST_MAGIC_DEF, "마법방어력", 0.2),
                    "speed_mult": (StatusType.BOOST_SPD, "속도", 0.3),
                    "critical_rate_bonus": (StatusType.BOOST_CRIT, "치명타율", 0.25),
                    "all_stats_mult": (StatusType.BOOST_ALL_STATS, "모든 능력치", 0.15),
                }

                buff_descs = []
                for stat_key, (status_type, stat_name, divisor) in buff_stat_map.items():
                    stat_value = effect.get(stat_key)
                    if stat_value is None:
                        continue
                    intensity = (stat_value - 1.0) / divisor if stat_value <= 2.0 else 1.0
                    pct = int((stat_value - 1.0) * 100) if stat_value <= 2.0 else int(stat_value * 100)
                    buff_descs.append(f"{stat_name}+{pct}%")
                    for t in buff_targets:
                        if t and hasattr(t, 'status_manager'):
                            try:
                                se = CombatStatusEffect(
                                    name=f"합체기:{combo_skill.name}({stat_name})",
                                    status_type=status_type,
                                    duration=duration,
                                    intensity=intensity,
                                )
                                t.status_manager.add_status(se)
                            except Exception as e:
                                self.logger.warning(f"합체기 버프 적용 실패: {e}")

                # counter_rate / counter_multiplier 등 특수 버프 처리
                counter_rate = effect.get("counter_rate", 0)
                counter_mult = effect.get("counter_multiplier", 0)
                if counter_rate > 0 or counter_mult > 0:
                    for t in buff_targets:
                        t._combo_counter_rate = counter_rate
                        t._combo_counter_mult = counter_mult
                        t._combo_counter_duration = duration
                    buff_descs.append(f"반격률 {int(counter_rate*100)}%")

                buff_desc = ", ".join(buff_descs) if buff_descs else combo_skill.name
                target_names = ", ".join(getattr(t, 'name', '?') for t in buff_targets if t)
                result["effects"].append({"type": "buff", "target": target_names, "buff_desc": buff_desc, "duration": duration})

            elif effect_type == "debuff":
                from src.combat.status_effects import StatusType, StatusEffect as CombatStatusEffect
                duration = effect.get("duration", 3)
                debuff_targets = all_enemies if target_type == "all_enemies" else [target] if target else all_enemies

                debuff_stat_map = {
                    "physical_defense_mult": (StatusType.REDUCE_DEF, "방어력", 0.2),
                    "magic_defense_mult": (StatusType.REDUCE_MAGIC_DEF, "마법방어력", 0.2),
                    "physical_attack_mult": (StatusType.REDUCE_ATK, "공격력", 0.2),
                    "magic_attack_mult": (StatusType.REDUCE_MAGIC_ATK, "마법공격력", 0.2),
                    "speed_mult": (StatusType.REDUCE_SPD, "속도", 0.3),
                }

                debuff_descs = []
                for stat_key, (status_type, stat_name, divisor) in debuff_stat_map.items():
                    stat_value = effect.get(stat_key)
                    if stat_value is None:
                        continue
                    intensity = (1.0 - stat_value) / divisor if stat_value < 1.0 else 0.5
                    pct = int((1.0 - stat_value) * 100) if stat_value < 1.0 else 10
                    debuff_descs.append(f"{stat_name}-{pct}%")
                    for t in debuff_targets:
                        if t and hasattr(t, 'status_manager'):
                            try:
                                se = CombatStatusEffect(
                                    name=f"합체기:{combo_skill.name}({stat_name})",
                                    status_type=status_type,
                                    duration=duration,
                                    intensity=intensity,
                                )
                                t.status_manager.add_status(se)
                            except Exception as e:
                                self.logger.warning(f"합체기 디버프 적용 실패: {e}")

                debuff_desc = ", ".join(debuff_descs) if debuff_descs else combo_skill.name
                result["effects"].append({"type": "debuff", "desc": debuff_desc, "duration": duration})

        # 자해 데미지 (berserker_dragon_rage 등)
        for effect in combo_skill.effects:
            self_dmg_pct = effect.get("self_damage_percent", 0)
            if self_dmg_pct > 0:
                for p in participants:
                    dmg = int(getattr(p, 'max_hp', 100) * self_dmg_pct / 100)
                    p.current_hp = max(1, getattr(p, 'current_hp', 0) - dmg)

        # 호감도 증가
        if self._affinity_manager and len(participants) >= 2:
            for i in range(len(participants)):
                for j in range(i + 1, len(participants)):
                    self._affinity_manager.on_combo_skill(
                        participants[i].character_class,
                        participants[j].character_class
                    )

        # 이벤트 발행
        event_bus.publish(Events.COMBO_SKILL_EXECUTED, {
            "combo_id": combo_skill.id,
            "combo_name": combo_skill.name,
            "participants": [p.name for p in participants],
            "effects": result["effects"]
        })

        result["message"] = f"{combo_skill.name} 발동!"
        self.logger.info(f"합체기 실행: {combo_skill.name} (게이지 -{combo_skill.gauge_cost})")
        return result

    def get_synergy_bonus_effects(self) -> dict:
        """현재 활성 시너지 보너스 효과 조회"""
        if not self._synergy_manager:
            return {}
        return self._synergy_manager.get_total_bonus_effects()

    def execute_teamwork_skill(
        self,
        actor: Any,
        skill: Any,
        target: Optional[Any] = None,
        is_chain_start: bool = True
    ) -> Tuple[bool, str]:
        """
        팀워크 스킬 실행

        Args:
            actor: 스킬 사용자
            skill: 팀워크 스킬
            target: 대상
            is_chain_start: 연쇄 시작 여부 (True=시작자, False=연쇄 이어받기)

        Returns:
            실행 성공 여부
        """
        if not self.party:
            self.logger.warning("팀워크 게이지 시스템이 활성화되지 않았습니다")
            return False, ""

        if not hasattr(skill, 'teamwork_cost'):
            self.logger.warning(f"{skill.name}은(는) 팀워크 스킬이 아닙니다")
            return False, ""

        extra_message = ""  # 추가 메시지 초기화

        if is_chain_start:
            # ===== 연쇄 시작 =====
            # 팀워크 게이지 소모
            if not self.party.consume_teamwork_gauge(skill.teamwork_cost.gauge):
                self.logger.warning(
                    f"팀워크 게이지 부족! "
                    f"(필요: {skill.teamwork_cost.gauge}, 현재: {self.party.teamwork_gauge})"
                )
                return False, ""

            # 연쇄 시작
            self.party.start_chain(actor, skill)
            mp_cost = 0

            # 팀워크 스킬 SFX 재생 (체인 1단계)
            from src.audio import play_teamwork_sfx
            play_teamwork_sfx("skill", "teamwork", chain_count=1)
        else:
            # ===== 연쇄 이어받기 =====
            if not self.party.chain_active:
                self.logger.warning("활성화된 연쇄가 없습니다!")
                return False, ""

            # 팀워크 게이지 소모
            if not self.party.consume_teamwork_gauge(skill.teamwork_cost.gauge):
                self.logger.warning(
                    f"팀워크 게이지 부족으로 연쇄 종료! "
                    f"(필요: {skill.teamwork_cost.gauge}, 현재: {self.party.teamwork_gauge})"
                )
                self.party.end_chain()
                return False, ""

            # MP 비용 계산 및 소모 (스킬을 전달하여 게이지 기반 MP 계산)
            mp_cost = self.party.continue_chain(skill)
            current_mp = actor.current_mp if hasattr(actor, 'current_mp') else 0
            if current_mp < mp_cost:
                self.logger.warning(
                    f"MP 부족으로 연쇄 종료! "
                    f"(필요: {mp_cost}, 현재: {current_mp})"
                )
                self.party.end_chain()
                return False, ""

            actor.current_mp -= mp_cost
            self.logger.info(f"{actor.name} MP 소모: -{mp_cost} (잔여: {actor.current_mp})")

            # 팀워크 스킬 SFX 재생 (체인 2단계 이상, pitch/volume 증가)
            from src.audio import play_teamwork_sfx
            play_teamwork_sfx("skill", "teamwork", chain_count=self.party.chain_count)

        # 스킬 효과 직접 실행 (skill_manager 사용)
        from src.character.skills.skill_manager import get_skill_manager
        skill_manager = get_skill_manager()
        
        skill_id = getattr(skill, 'skill_id', None)
        all_enemies = self.enemies if actor in self.allies else self.allies
        all_allies = self.allies if actor in self.allies else self.enemies
        
        # 팀워크 스킬 실행 시 비용 체크 스킵 (이미 위에서 소모함)
        context = {
            "combat_manager": self, 
            "all_enemies": all_enemies, 
            "all_allies": all_allies, 
            "party": self.party,
            "skip_cost_check": True
        }
        
        # 기믹 업데이트 (스킬 사용) - 스킬 실행 전에 호출
        GimmickUpdater.on_skill_use(actor, skill, context)
        
        if skill_id:
            skill_result = skill_manager.execute_skill(skill_id, actor, target, context=context)
        else:
            # 스킬 객체 직접 실행
            skill_result = skill.execute(actor, target, context)
        
        if skill_result.success:
            self.logger.info(f"[스킬 효과] {skill_result.message}")

        # 팀워크 스킬 메타데이터 처리
        # 0. self_gimmick_add: 사용자 본인의 기믹 카운터 증가 (target_type과 무관하게 self에 적용)
        if hasattr(skill, 'metadata') and skill.metadata.get('self_gimmick_add'):
            gimmick_info = skill.metadata['self_gimmick_add']
            field = gimmick_info.get('field', '')
            amount = gimmick_info.get('amount', 0)
            max_val = gimmick_info.get('max_value', 999)
            if field and hasattr(actor, field):
                current = getattr(actor, field, 0)
                new_val = min(current + amount, max_val)
                setattr(actor, field, new_val)
                self.logger.info(f"[메타데이터] {actor.name}의 {field}: {current} → {new_val}")

        # 1. fill_possibility_slots: 시간술사 가능성 슬롯 채우기
        if hasattr(skill, 'metadata') and skill.metadata.get('fill_possibility_slots'):
            for ally in all_allies:
                if hasattr(ally, 'gimmick_type') and ally.gimmick_type == "possibility_system":
                    # 모든 가능성 슬롯 채우기 (최대 5개)
                    max_slots = 5
                    for i in range(max_slots):
                        if not hasattr(ally, 'possibility_slots'):
                            ally.possibility_slots = []
                        if len(ally.possibility_slots) < max_slots:
                            # 임의의 스킬 ID 추가 (메타데이터에서 기본값 제공)
                            default_skill = skill.metadata.get('default_fill_skill', 'time_mage_time_bolt')
                            ally.possibility_slots.append({
                                'skill_id': default_skill,
                                'power_ratio': 1.0,
                                'reuse_count': 0
                            })
                    self.logger.info(f"[시공 붕괴] {ally.name}의 가능성 슬롯 모두 충전!")

        # 2. atb_reset_enemies: 적 ATB 초기화
        if hasattr(skill, 'metadata') and skill.metadata.get('atb_reset_enemies'):
            for enemy in all_enemies:
                if hasattr(enemy, 'is_alive') and enemy.is_alive:
                    if enemy in self.atb.gauges:
                        self.atb.gauges[enemy].current = 0
                        self.logger.info(f"[시공 붕괴] {enemy.name}의 ATB 초기화!")

        # 3. atb_boost_allies: 아군 ATB 부스트
        if hasattr(skill, 'metadata') and skill.metadata.get('atb_boost_allies'):
            boost_amount = skill.metadata.get('atb_boost_allies', 500)
            for ally in all_allies:
                if hasattr(ally, 'is_alive') and ally.is_alive:
                    if ally in self.atb.gauges:
                        self.atb.gauges[ally].increase(boost_amount, force=True)
                        self.logger.info(f"[시공 붕괴] {ally.name}의 ATB +{boost_amount}!")

        # 4. guaranteed_treasure: 해적 보물 확정 획득
        if hasattr(skill, 'metadata') and skill.metadata.get('guaranteed_treasure'):
            treasure_amount = skill.metadata.get('guaranteed_treasure', 1)
            # 해적 직업 찾기 (gimmick_type == "rum_treasure_system")
            for ally in all_allies:
                if hasattr(ally, 'gimmick_type') and ally.gimmick_type in ["treasure_system", "rum_treasure_system"]:
                    if not hasattr(ally, 'treasure_inventory'):
                        ally.treasure_inventory = []
                    max_treasure = getattr(ally, 'max_treasure', 5)

                    # 보물 추가 (최대치 제한)
                    added = 0
                    from src.character.skills.job_skills.pirate_skills import get_random_treasure
                    
                    for _ in range(treasure_amount):
                        if len(ally.treasure_inventory) < max_treasure:
                            tid, _ = get_random_treasure()
                            ally.treasure_inventory.append(tid)
                            added += 1

                    if added > 0:
                        self.logger.info(f"[약탈 함대] 보물 {added}개 획득! (현재: {len(ally.treasure_inventory)}/{max_treasure})")
                        extra_message = f"💰 보물 {added}개 획득!"

        # ATB 25% 회복 (ATBSystem 통해)
        atb_recovery = 500  # ATB 최대치 2000의 25%
        if actor in self.atb.gauges:
            self.atb.gauges[actor].increase(atb_recovery, force=True)
        self.logger.info(
            f"[Teamwork] {actor.name}의 팀워크 스킬 '{skill.name}' "
            f"(연쇄 {self.party.chain_count}단계, MP: {mp_cost}, ATB +500)"
        )

        # ── 호감도 증가: 팀워크 스킬 연쇄 시 참여자 간 (+5) ──
        if self._affinity_manager and self.party:
            participant_jobs = []
            # 연쇄 시작자
            starter = getattr(self.party, 'chain_starter', None)
            if starter and hasattr(starter, 'character_class'):
                participant_jobs.append(starter.character_class)
            # 현재 사용자 (시작자와 다를 경우)
            if hasattr(actor, 'character_class') and actor != starter:
                participant_jobs.append(actor.character_class)
            if len(participant_jobs) >= 2:
                self._affinity_manager.on_teamwork_chain(participant_jobs)

        # ── 체인어빌리티 트리거: 팀워크 스킬 사용 후 ──
        if actor in self.allies:
            self.trigger_chain_ability_check(actor, "teamwork")

        return True, extra_message

    def _on_boss_timeout(self):
        """보스 전투 타임아웃 처리"""
        self.logger.warning("보스 전투 타임아웃!")

        # 타임오버 스토리 재생 (세피로스 또는 카인)
        is_sephiroth = any(
            getattr(enemy, 'enemy_id', None) == "sephiroth" for enemy in self.enemies
        )
        is_cain = any(
            getattr(enemy, 'enemy_id', None) == "abel_cain" for enemy in self.enemies
        )

        from src.story.story_system import get_story_system
        story_system = get_story_system()

        if is_cain:
            timeout_story = story_system.get_cain_timeout_story()
            self.logger.info("카인 타임오버 - 시공 소멸")
        else:
            timeout_story = story_system.get_sephiroth_timeout_story()
            self.logger.info("세피로스 타임오버 - 타임라인 붕괴")

        # 스토리 재생은 UI에서 처리
        # 여기서는 플래그만 설정
        self.timeout_story = timeout_story

        # 전투 패배 처리
        self.state = CombatState.DEFEAT

        # 게임오버
        if self.on_combat_end:
            self.on_combat_end(CombatState.DEFEAT)

    def _on_timer_warning(self, remaining_seconds: int):
        """타이머 경고 (1분, 30초, 10초)"""
        self.logger.warning(f"보스 타이머 경고: {remaining_seconds}초 남음!")

        # UI에 경고 메시지 표시 (플래그 설정)
        warning_msg = f"⚠️ 경고: {remaining_seconds}초 남음! ⚠️"
        self.timer_warning_message = warning_msg


# 전역 인스턴스
_combat_manager: Optional[CombatManager] = None


def get_combat_manager() -> CombatManager:
    """전역 전투 관리자 인스턴스"""
    global _combat_manager
    if _combat_manager is None:
        _combat_manager = CombatManager()
    return _combat_manager


def set_combat_manager(cm: CombatManager) -> None:
    """전역 전투 관리자 설정 (전투 시작 시 호출)"""
    global _combat_manager
    _combat_manager = cm
