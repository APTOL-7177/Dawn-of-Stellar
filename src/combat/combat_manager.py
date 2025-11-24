"""
Combat Manager - 전투 관리자

ATB, Brave, Damage 시스템을 통합하여 전투 흐름 제어
"""

from typing import List, Dict, Any, Optional, Callable, Tuple
from enum import Enum

from src.core.config import get_config
from src.core.logger import get_logger
from src.core.event_bus import event_bus, Events
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
        
        # 요리 쿨타임 (전투 턴 기준)
        self.cooking_cooldown_turn: Optional[int] = None  # 요리 사용한 턴
        self.cooking_cooldown_duration: int = 0  # 쿨타임 지속 턴 수
        
        # 환경 효과를 위한 던전 정보
        self.dungeon: Optional[Any] = None  # DungeonMap
        self.combat_position: Optional[Tuple[int, int]] = None  # 전투 시작 위치 (x, y)

        # 콜백
        self.on_combat_end: Optional[Callable[[CombatState], None]] = None
        self.on_turn_start: Optional[Callable[[Any], None]] = None
        self.on_action_complete: Optional[Callable[[Any, Dict], None]] = None

        # 사망 이벤트 구독
        event_bus.subscribe(Events.CHARACTER_DEATH, self._on_character_death)
        event_bus.subscribe(Events.COMBAT_DAMAGE_TAKEN, self._on_damage_taken)

    def start_combat(self, allies: List[Any], enemies: List[Any], dungeon: Optional[Any] = None, combat_position: Optional[Tuple[int, int]] = None) -> None:
        """
        전투 시작

        Args:
            allies: 아군 리스트
            enemies: 적군 리스트
            dungeon: 던전 맵 (환경 효과용)
            combat_position: 전투 시작 위치 (x, y)
        """
        self.logger.info("전투 시작!")

        # 전투원 설정 (PartyMember 변환은 아래에서 처리)
        self.enemies = enemies
        self.turn_count = 0
        self.state = CombatState.IN_PROGRESS
        
        # 던전 정보 저장 (환경 효과용)
        self.dungeon = dungeon
        self.combat_position = combat_position
        
        # 요리 쿨타임 초기화 (인벤토리에서 쿨타임 정보 가져오기)
        # 전투 시작 시 현재 쿨타임 턴을 설정
        if hasattr(self, 'inventory') and self.inventory:
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
        
        # ATB 시스템에 전투원 등록
        import random
        for ally in self.allies:
            self.atb.register_combatant(ally)
            self.brave.initialize_brv(ally)
            # ATB 게이지를 0~50% 랜덤하게 채우기
            gauge = self.atb.get_gauge(ally)
            if gauge:
                random_percentage = random.uniform(0.0, 0.5)
                gauge.current = int(gauge.max_gauge * random_percentage)

        for enemy in enemies:
            self.atb.register_combatant(enemy)
            self.brave.initialize_brv(enemy)
            # ATB 게이지를 0~50% 랜덤하게 채우기
            gauge = self.atb.get_gauge(enemy)
            if gauge:
                random_percentage = random.uniform(0.0, 0.5)
                gauge.current = int(gauge.max_gauge * random_percentage)

        # 캐스팅 시스템 초기화
        from src.combat.casting_system import get_casting_system
        casting_system = get_casting_system()
        casting_system.clear()

        # 파티 버프 특성 적용 (holy_aura, chivalry 등)
        self._apply_party_wide_traits()

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
        # 죽은 캐릭터는 행동 불가
        if not getattr(actor, 'is_alive', True):
            self.logger.warning(f"{getattr(actor, 'name', 'Unknown')}은(는) 죽어서 행동할 수 없습니다.")
            return {
                "action": "error",
                "error": "actor_is_dead",
                "message": "죽은 캐릭터는 행동할 수 없습니다."
            }
        
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
        trait_manager.apply_turn_start_effects(actor)
        
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

        # 1. BREAK 상태 해제
        if self.brave.is_broken(actor):
            self.logger.debug(f"{actor.name}의 BREAK 상태 해제")
            self.brave.clear_break_state(actor)

        # 2. INT BRV 회복
        int_brv_recovered = self.brave.recover_int_brv(actor)
        if int_brv_recovered > 0:
            self.logger.debug(f"{actor.name}이(가) INT BRV {int_brv_recovered} 회복")

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
                    if hasattr(actor, 'is_alive'):
                        actor.is_alive = False
                    self.logger.warning(f"{actor.name}이(가) DoT로 사망!")
        
        # 3-1. 환경 효과 처리 (전투 위치의 환경 효과 적용)
        if self.dungeon and self.combat_position:
            self._apply_environmental_effects(actor)
        
        # 3-2. 랜섬웨어 효과 처리 (적의 턴 시작 시)
        if actor in self.enemies:
            self._process_ransomware_damage(actor)
        
        # 3-2. 사망 여부 확인 (DoT 또는 랜섬웨어로 사망한 경우)
        if hasattr(actor, 'is_alive') and not actor.is_alive:
            self.logger.warning(f"{actor.name}이(가) 턴 시작 시 피해로 사망하여 행동을 취소합니다.")
            result["success"] = False
            result["error"] = "사망"
            result["death_reason"] = "턴 시작 시 피해"
            # ATB는 소비하지만 행동하지 못함
            self.atb.consume_atb(actor)
            self._on_turn_end(actor)
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

        # ATB 소비 (행동 성공 시)
        self.atb.consume_atb(actor)

        # 턴 종료 처리
        self._on_turn_end(actor)

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
        skill_multiplier = getattr(skill, "brv_multiplier", 1.0) if skill else 1.0

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
            # 명중 SFX 재생
            play_sfx("combat", "attack_physical")
            
            # 무기 내구도 감소 (명중 시에만, skip_degrade 플래그 확인)
            if hasattr(attacker, 'degrade_equipment') and not kwargs.get('skip_degrade', False):
                attacker.degrade_equipment("weapon", 1)

        # BRV 공격 적용
        brv_result = self.brave.brv_attack(attacker, defender, damage_result.final_damage)

        # 공격 후 방어 스택 초기화
        if hasattr(attacker, 'defend_stack_count') and attacker.defend_stack_count > 0:
            attacker.defend_stack_count = 0

        # 빗나간 공격은 기믹 트리거 안 함
        if not is_miss and trigger_gimmick and attacker in self.allies:
            # 아군 공격 시 기믹 트리거 (지원사격 등)
            GimmickUpdater.on_ally_attack(attacker, self.allies, target=defender)

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

        # combo_multiplier (콤보 배율 처리)
        combo_bonus = 0
        if skill and hasattr(skill, 'metadata') and skill.metadata.get('combo_multiplier'):
            combo_mult = skill.metadata['combo_multiplier']
            combo_key = f"_combo_count_{getattr(skill, 'skill_id', 'default')}"
            current_combo = getattr(attacker, combo_key, 0) + 1
            
            # 콤보 최대치 제한
            max_combo = skill.metadata.get('combo_max', 10)
            current_combo = min(current_combo, max_combo)
            setattr(attacker, combo_key, current_combo)
            
            # 콤보 보너스 계산
            combo_bonus = (current_combo - 1) * combo_mult
            if combo_bonus > 0:
                self.logger.debug(f"[콤보] {attacker.name} 콤보 {current_combo}회 → 데미지 +{combo_bonus*100:.0f}%")
            
            # combo_reset: 다른 스킬 사용 시 콤보 리셋 여부
            if not skill.metadata.get('combo_reset', False):
                # 다른 스킬의 콤보 초기화
                for attr in dir(attacker):
                    if attr.startswith('_combo_count_') and attr != combo_key:
                        setattr(attacker, attr, 0)

        # first_strike_bonus (선제공격 보너스)
        first_strike_bonus = 0
        if self.turn_count == 0 and skill and hasattr(skill, 'metadata') and skill.metadata.get('first_strike_bonus'):
            first_strike_bonus = skill.metadata['first_strike_bonus']
            self.logger.info(f"[선제 공격] {attacker.name} 첫 턴 공격! 데미지 +{first_strike_bonus*100:.0f}%")

        # revenge_bonus (복수 보너스 - 피격 후 공격)
        revenge_bonus = 0
        if hasattr(attacker, '_recently_damaged') and attacker._recently_damaged:
            if skill and hasattr(skill, 'metadata') and skill.metadata.get('revenge_bonus'):
                revenge_bonus = skill.metadata['revenge_bonus']
                self.logger.info(f"[복수] {attacker.name} 복수 공격! 데미지 +{revenge_bonus*100:.0f}%")
            attacker._recently_damaged = False  # 복수 후 초기화

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

        # SFX 재생 (높은 데미지)
        play_sfx("combat", "damage_high")

        # 스킬 배율
        hp_multiplier = getattr(skill, "hp_multiplier", 1.0) if skill else 1.0

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

        # 어둠기사 execute 효과: 적 HP 비례 추가 데미지
        if skill and hasattr(skill, 'metadata') and skill.metadata.get('execute'):
            if hasattr(defender, 'current_hp') and hasattr(defender, 'max_hp') and defender.max_hp > 0:
                hp_ratio = defender.current_hp / defender.max_hp
                low_hp_bonus = skill.metadata.get('low_hp_bonus', 2.0)
                if hp_ratio <= 0.3:  # HP 30% 이하
                    hp_multiplier *= low_hp_bonus
                    self.logger.info(f"[처형] {defender.name} HP {hp_ratio*100:.1f}% → 데미지 x{low_hp_bonus}")

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
        if instant_kill_attempted:
            # 즉사: 현재 HP를 모두 제거
            if hasattr(defender, 'current_hp'):
                defender.current_hp = 0
            hp_result = {
                "hp_damage": 9999,
                "brv_consumed": attacker.current_brv,
                "is_break_bonus": is_break
            }
            attacker.current_brv = 0  # BRV 소비
        else:
            # HP 공격 적용 (BRV 소비 및 데미지 적용)
            # brave.hp_attack()이 take_damage()를 내부적으로 호출함
            hp_result = self.brave.hp_attack(attacker, defender, hp_multiplier)

        # 무기 내구도 감소 (skip_degrade 플래그 확인)
        # HP 공격은 빗나감이 없으므로(BRV 0이면 0데미지지만 공격 자체는 성공) 항상 내구도 감소 시도
        if hasattr(attacker, 'degrade_equipment') and not kwargs.get('skip_degrade', False):
            attacker.degrade_equipment("weapon", 1)

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

        # 공격 후 방어 스택 초기화
        if hasattr(attacker, 'defend_stack_count') and attacker.defend_stack_count > 0:
            attacker.defend_stack_count = 0

        # lifesteal (흡혈) 효과 + 뱀파이어 특성 처리
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

                    # vitality_overflow: 최대 HP일 때 초과 흡혈량 → BRV 전환
                    if attacker.current_hp >= attacker.max_hp:
                        has_vitality_overflow = any(
                            (t if isinstance(t, str) else t.get('id')) == 'vitality_overflow'
                            for t in getattr(attacker, 'active_traits', [])
                        )
                        if has_vitality_overflow:
                            overflow_amount = heal_amount - actual_heal
                            if overflow_amount > 0 and hasattr(attacker, 'current_brv') and hasattr(attacker, 'max_brv'):
                                brv_gain = min(overflow_amount, attacker.max_brv - attacker.current_brv)
                                attacker.current_brv += brv_gain
                                self.logger.info(f"[생명력 과부하] {attacker.name} 초과 흡혈 {overflow_amount} → BRV +{brv_gain}")
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
            GimmickUpdater.on_ally_attack(attacker, self.allies, target=defender)
        
        # 적 처치 확인 및 효과 적용 (battle_heal, battle_mp, bloodthirst 등)
        if hasattr(defender, 'current_hp') and defender.current_hp <= 0:
            if defender in self.enemies:
                # 적 처치 확인
                from src.character.trait_effects import get_trait_effect_manager
                trait_manager = get_trait_effect_manager()
                print(f"DEBUG: trait_manager attributes: {dir(trait_manager)}")
                
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
            GimmickUpdater.on_ally_attack(attacker, self.allies, target=defender)

        # 결과 병합
        combined_result = {
            "action": "brv_hp_attack",
            "is_combo": True
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

        result = {
            "action": "skill",
            "skill_name": getattr(skill, "name", "Unknown"),
            "targets": []
        }

        # 적 스킬인지 확인
        try:
            from src.combat.enemy_skills import EnemySkill, SkillTargetType

            if isinstance(skill, EnemySkill):
                # 적 스킬 실행
                result.update(self._execute_enemy_skill(actor, target, skill, **kwargs))
                return result
        except ImportError as e:
            # EnemySkill이 없으면 일반 스킬 시스템 사용
            self.logger.debug(f"적 스킬 시스템 미사용: {e}")

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
                # skill 객체를 직접 사용
                if hasattr(skill, 'execute'):
                    # Skill 객체를 직접 실행
                    context = {"combat_manager": self, "all_enemies": self.enemies if actor in self.allies else self.allies}
                    skill_result = skill.execute(actor, target, context)
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

            # SkillManager를 통해 스킬 실행
            skill_result = skill_manager.execute_skill(
                skill_id,
                actor,
                target,
                context={"combat_manager": self, "all_enemies": all_enemies}
            )

        if skill_result.success:
            result["success"] = True
            result["message"] = skill_result.message

            # ISSUE-003: 스킬 효과 상세 로그 출력
            self.logger.info(f"[스킬 효과] {skill_result.message}")

            # 기믹 업데이트 (스킬 사용)
            GimmickUpdater.on_skill_use(actor, skill)

            # 공격 스킬 사용 시 기믹 트리거 (지원사격 등)
            if actor in self.allies and target:
                # 스킬에 데미지 효과가 있는지 확인
                has_damage = False
                if hasattr(skill, 'effects'):
                    from src.character.skills.effects.damage_effect import DamageEffect
                    has_damage = any(isinstance(effect, DamageEffect) for effect in skill.effects)

                # 데미지 효과가 있으면 공격 스킬로 간주하고 on_ally_attack 호출
                if has_damage:
                    GimmickUpdater.on_ally_attack(actor, self.allies, target=target)

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
                                        else:
                                            self.logger.warning(f"[폭발적 힘] {splash_target.name}에 take_damage 메서드가 없어 충격파 피해를 적용할 수 없습니다.")

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
        else:
            result["success"] = False
            result["error"] = skill_result.message

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
        if hasattr(actor, 'current_mp'):
            actor.current_mp = max(0, actor.current_mp - skill.mp_cost)
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
                    # - 복합 스킬(BRV+HP): BRV는 2배, HP는 0.75배로 조정
                    effective_multiplier = skill.damage_multiplier
                    brv_multiplier = skill.damage_multiplier
                    hp_multiplier = skill.damage_multiplier
                    
                    if skill.brv_damage > 0 and not skill.hp_attack:
                        # BRV 공격만 있는 경우: 2배로 조정
                        brv_multiplier = skill.damage_multiplier * 2.0
                        effective_multiplier = brv_multiplier
                    elif skill.hp_attack and not skill.brv_damage:
                        # HP 공격만 있는 경우: 0.75배로 조정
                        effective_multiplier = skill.damage_multiplier * 0.75
                        hp_multiplier = effective_multiplier
                    elif skill.hp_attack and skill.brv_damage:
                        # 복합 스킬: BRV는 2배, HP는 0.75배로
                        brv_multiplier = skill.damage_multiplier * 2.0
                        hp_multiplier = skill.damage_multiplier * 0.75
                        effective_multiplier = brv_multiplier  # BRV 데미지 계산용
                    
                    if skill.is_magical:
                        base_damage = int(skill.damage + actor.magic_attack * effective_multiplier)
                        defense = getattr(tgt, 'magic_defense', 0)
                    else:
                        base_damage = int(skill.damage + actor.physical_attack * effective_multiplier)
                        defense = getattr(tgt, 'physical_defense', 0)

                    # 방어력 적용
                    final_damage = max(1, base_damage - defense // 2)

                    # BRV 데미지 계산 (복합 스킬의 경우 BRV 계수는 2배 적용)
                    if skill.brv_damage > 0:
                        # BRV 데미지를 계수에 맞게 계산
                        if skill.is_magical:
                            brv_base_damage = int(skill.damage + actor.magic_attack * brv_multiplier)
                            brv_defense = getattr(tgt, 'magic_defense', 0)
                        else:
                            brv_base_damage = int(skill.damage + actor.physical_attack * brv_multiplier)
                            brv_defense = getattr(tgt, 'physical_defense', 0)
                        
                        # 방어력 적용 (BRV 데미지)
                        brv_final_damage = max(1, brv_base_damage - brv_defense // 2)
                        
                        if hasattr(tgt, 'current_brv'):
                            brv_dmg = min(brv_final_damage, tgt.current_brv)
                            tgt.current_brv = max(0, tgt.current_brv - brv_dmg)
                            target_result["brv_damage"] = brv_dmg

                    # HP 데미지 (HP 공격만 있거나 둘 다 있는 경우)
                    if skill.hp_attack or not skill.brv_damage:
                        # 둘 다 있는 경우: HP 데미지는 별도 계산
                        if skill.hp_attack and skill.brv_damage:
                            if skill.is_magical:
                                hp_base_damage = int(skill.damage + actor.magic_attack * hp_multiplier)
                                hp_defense = getattr(tgt, 'magic_defense', 0)
                            else:
                                hp_base_damage = int(skill.damage + actor.physical_attack * hp_multiplier)
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
                if hasattr(tgt, 'heal'):
                    healed = tgt.heal(skill.heal_amount)
                elif hasattr(tgt, 'current_hp') and hasattr(tgt, 'max_hp'):
                    healed = min(skill.heal_amount, tgt.max_hp - tgt.current_hp)
                    tgt.current_hp += healed
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
                # 실제 상태이상 시스템 연동
                if hasattr(tgt, 'status_manager') or hasattr(tgt, 'status_effects'):
                    status_mgr = getattr(tgt, 'status_manager', None) or getattr(tgt, 'status_effects', None)
                    if isinstance(status_mgr, StatusManager):
                        # status_effects는 List[str] 타입이므로 리스트를 반복
                        for effect_name in skill.status_effects:
                            duration = skill.status_duration  # 기본 duration 사용
                            intensity = 1.0  # 기본 intensity

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

        # damage=0이고 BRV 시스템을 사용하는 스킬 처리 (damage > 0 블록 밖에서)
        if skill.damage == 0 and skill.brv_damage > 0:
            # BRV 시스템을 사용하는 적 스킬
            from src.combat.damage_calculator import get_damage_calculator
            damage_calc = get_damage_calculator()
            
            # BRV 공격 계수 조정 (BRV만: 2배, 복합: BRV 2배)
            brv_multiplier = skill.damage_multiplier
            if skill.brv_damage > 0 and not skill.hp_attack:
                # BRV 공격만 있는 경우: 2배로 조정
                brv_multiplier = skill.damage_multiplier * 2.0
            elif skill.brv_damage > 0 and skill.hp_attack:
                # 복합 스킬: BRV는 2배
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

            # 효과 타입에 따라 처리
            if effect_type == "heal_hp":
                if hasattr(tgt, 'heal'):
                    healed = tgt.heal(int(effect_value))
                elif hasattr(tgt, 'current_hp') and hasattr(tgt, 'max_hp'):
                    healed = min(int(effect_value), tgt.max_hp - tgt.current_hp)
                    tgt.current_hp += healed
                else:
                    healed = int(effect_value)
                result["healing"] = healed

            elif effect_type == "heal_mp":
                if hasattr(tgt, 'restore_mp'):
                    healed = tgt.restore_mp(int(effect_value))
                elif hasattr(tgt, 'current_mp') and hasattr(tgt, 'max_mp'):
                    healed = min(int(effect_value), tgt.max_mp - tgt.current_mp)
                    tgt.current_mp += healed
                else:
                    healed = int(effect_value)
                result["mp_healing"] = healed

            elif effect_type == "buff":
                # 버프 효과 (간단하게 처리)
                result["buff_applied"] = True

            elif effect_type == "cure" or effect_type == "status_cleanse":
                # 상태이상 치료
                if hasattr(tgt, 'status_manager'):
                    tgt.status_manager.clear_all_effects()
                    result["status_cured"] = True
                elif hasattr(tgt, 'status_effects'):
                    tgt.status_effects.clear()
                    result["status_cured"] = True
            
            # === 공격적 아이템 효과 ===
            elif effect_type in ["aoe_fire", "aoe_ice", "poison_bomb", "thunder_grenade"]:
                # 적 전체 데미지
                damage = int(effect_value)
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
                        if effect_type == "poison_bomb" and hasattr(enemy, 'status_manager'):
                            from src.combat.status_effects import StatusEffect, StatusType
                            poison = StatusEffect("독", StatusType.POISON, duration=3, intensity=1.0)
                            enemy.status_manager.add_status(poison)
                        elif effect_type == "thunder_grenade" and hasattr(enemy, 'status_manager'):
                            from src.combat.status_effects import StatusEffect, StatusType
                            shock = StatusEffect("감전", StatusType.SHOCK, duration=2, intensity=1.0)
                            enemy.status_manager.add_status(shock)
                result["aoe_damage"] = total_damage
                result["targets_hit"] = len([e for e in self.enemies if hasattr(e, 'is_alive') and e.is_alive])
            
            elif effect_type in ["single_lightning", "acid_flask"]:
                # 단일 적 데미지
                damage = int(effect_value)
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
                # 버프 적용
                duration = 3 if effect_type != "regen_crystal" and effect_type != "mp_regen_crystal" else 5
                if hasattr(tgt, 'active_buffs'):
                    if effect_type == "barrier_crystal":
                        tgt.active_buffs['damage_reduction'] = {'value': effect_value, 'duration': duration}
                    elif effect_type == "haste_crystal":
                        tgt.active_buffs['speed_up'] = {'value': effect_value, 'duration': duration}
                    elif effect_type == "power_tonic":
                        tgt.active_buffs['attack_up'] = {'value': effect_value, 'duration': duration}
                        tgt.active_buffs['magic_up'] = {'value': effect_value, 'duration': duration}
                    elif effect_type == "defense_elixir":
                        tgt.active_buffs['defense_up'] = {'value': effect_value, 'duration': duration}
                        tgt.active_buffs['magic_defense_up'] = {'value': effect_value, 'duration': duration}
                    elif effect_type == "regen_crystal":
                        tgt.active_buffs['hp_regen'] = {'value': effect_value, 'duration': duration}
                    elif effect_type == "mp_regen_crystal":
                        tgt.active_buffs['mp_regen'] = {'value': effect_value, 'duration': duration}
                result["buff_applied"] = True
            
            elif effect_type == "revive_crystal":
                # 부활
                if not getattr(tgt, 'is_alive', True):
                    tgt.is_alive = True
                    if hasattr(tgt, 'max_hp'):
                        tgt.current_hp = int(tgt.max_hp * effect_value)
                    else:
                        tgt.current_hp = int(effect_value * 100)  # 기본값
                    result["revived"] = True
                    result["hp_restored"] = tgt.current_hp

            # 인벤토리에서 아이템 제거
            item_index = kwargs.get('item_index')
            if item_index is not None:
                # 인벤토리에서 슬롯 인덱스로 제거
                if hasattr(actor, 'inventory'):
                    try:
                        actor.inventory.remove_item(item_index, 1)
                    except Exception as e:
                        self.logger.warning(f"아이템 제거 실패: {e}")
                # 또는 전역 인벤토리에서 제거
                elif hasattr(self, 'inventory') and self.inventory:
                    try:
                        self.inventory.remove_item(item_index, 1)
                    except Exception as e:
                        self.logger.warning(f"아이템 제거 실패: {e}")

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
        # 도망 확률 계산
        flee_chance = 0.5  # 기본 50%
        import random
        if random.random() < flee_chance:
            self.state = CombatState.FLED
            return {
                "action": "flee",
                "success": True
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
        
        # 해커: 모든 프로그램 종료
        if hasattr(character, 'gimmick_type') and character.gimmick_type == "multithread_system":
            self._handle_hacker_death(character)
        
        # 네크로맨서: 언데드 소환물 처리
        if hasattr(character, 'gimmick_type') and character.gimmick_type == "undead_legion":
            self._handle_necromancer_death(character)
        
        # 버서커: 광기 시스템 정리
        if hasattr(character, 'gimmick_type') and character.gimmick_type == "madness_threshold":
            self._handle_berserker_death(character)
        
        # 뱀파이어: 갈증 게이지 정리
        if hasattr(character, 'gimmick_type') and character.gimmick_type == "thirst_gauge":
            self._handle_vampire_death(character)
        
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
        뱀파이어 사망 시 처리: 갈증 게이지 정리
        
        Args:
            vampire: 사망한 뱀파이어 캐릭터
        """
        # 갈증 게이지 값은 유지하되, 더 이상 증가하지 않도록 처리
        if hasattr(vampire, 'thirst'):
            thirst_value = getattr(vampire, 'thirst', 0)
            if thirst_value > 0:
                self.logger.debug(
                    f"{vampire.name} 사망 시 갈증 게이지: {thirst_value}"
                )
    
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
                                actual_damage = attacker.take_damage(reflect_damage)
                            elif hasattr(attacker, 'current_hp'):
                                actual_damage = min(reflect_damage, attacker.current_hp)
                                attacker.current_hp = max(0, attacker.current_hp - actual_damage)
                            else:
                                actual_damage = reflect_damage
                            self.logger.info(f"[반사 피해] {defender.name}의 가시 효과로 {attacker.name}에게 {actual_damage} 반사 피해!")
        
        # 아군이 피해를 받았는지 확인
        if defender not in self.allies:
            return
        
        # 이미 피해가 적용되었는지 확인 (new_hp가 None이면 아직 적용 전)
        if data.get("new_hp") is not None:
            # 이미 피해가 적용된 경우, 수호 효과는 처리할 수 없음
            return
        
        # 스킬 효과: 수호의 맹세 - 기사가 아군을 보호
        # 보호받는 대상인지 확인
        if hasattr(defender, 'protected_by') and defender.protected_by:
            # 보호자가 있는 경우, 보호자가 대신 피해를 받음
            # 현재 전투에 참여하는 보호자만 확인 (오래된 참조 방지)
            for guardian in list(defender.protected_by):  # 리스트 복사하여 순회 중 수정 방지
                if (guardian in self.allies and
                    hasattr(guardian, 'is_alive') and guardian.is_alive and 
                    guardian != defender):
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
                    
                    # 보호자가 피해를 받음
                    if hasattr(guardian, 'take_damage'):
                        guardian_actual_damage = guardian.take_damage(protected_damage)
                        self.logger.info(
                            f"[수호의 맹세] {guardian.name}이(가) {defender.name}의 피해를 대신 받음: "
                            f"{protected_damage} → 실제 {guardian_actual_damage} (보호자 방어력 적용)"
                        )
                    
                    return  # 한 명만 수호
        
        # 특성 효과: 수호 (guardian_angel) - 아군 피해 대신 받기
        from src.character.trait_effects import get_trait_effect_manager, TraitEffectType
        trait_manager = get_trait_effect_manager()
        
        # 다른 아군 중 수호 효과가 있는 캐릭터 찾기
        for ally in self.allies:
            if ally == defender or not hasattr(ally, 'is_alive') or not ally.is_alive:
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
                            
                            # 수호자가 피해를 받음
                            if hasattr(ally, 'take_damage'):
                                guardian_actual_damage = ally.take_damage(protected_damage)
                                self.logger.info(
                                    f"[{trait_id}] {ally.name}이(가) {defender.name}의 피해를 대신 받음: "
                                    f"{protected_damage} → 실제 {guardian_actual_damage} (원래 피해: {damage}, 남은 피해: {remaining_damage}, 보호 비율: {int(protection_ratio * 100)}%)"
                                )
                            
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

                        # 충전 획득 (암흑기사)
                        if hasattr(defender, 'gimmick_type') and defender.gimmick_type == "charge_system":
                            from src.character.gimmick_updater import GimmickUpdater
                            GimmickUpdater.on_charge_gained(defender, parry_charge_gain, "패링 성공")

                        # 캐스팅 완료 처리 (패링 성공 시 스킬 시전 안 함)
                        self.casting_system.cancel_cast(defender, "패링 성공")
                        return  # 패링 성공 시 피해를 받지 않으므로 충전 획득 없음

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

        # 버프 지속시간 감소 (모든 전투원)
        all_combatants = self.party + self.enemies
        for combatant in all_combatants:
            if hasattr(combatant, 'active_buffs') and combatant.active_buffs:
                expired_buffs = []
                for buff_type, buff_data in list(combatant.active_buffs.items()):
                    # REGEN, HP_REGEN, MP_REGEN은 duration 감소하지 않음 (다른 방식으로 관리)
                    if buff_type in ['regen', 'hp_regen', 'mp_regen']:
                        continue
                    
                    duration = buff_data.get('duration', 0)
                    if duration > 0:
                        duration -= 1
                        buff_data['duration'] = duration
                        
                        if duration <= 0:
                            expired_buffs.append(buff_type)
                            self.logger.debug(f"{combatant.name}의 {buff_type} 버프 만료")
                
                # 만료된 버프 제거
                for buff_type in expired_buffs:
                    del combatant.active_buffs[buff_type]

        # 기믹 업데이트 (턴 종료)
        GimmickUpdater.on_turn_end(actor)

        # 이벤트 발행
        event_bus.publish(Events.COMBAT_TURN_END, {
            "actor": actor,
            "turn": self.turn_count
        })

        self.turn_count += 1
        
        # 요리 쿨타임 감소
        if self.cooking_cooldown_turn is not None and self.cooking_cooldown_duration > 0:
            elapsed_turns = self.turn_count - self.cooking_cooldown_turn
            if elapsed_turns >= self.cooking_cooldown_duration:
                # 쿨타임 종료
                self.cooking_cooldown_duration = 0
                self.cooking_cooldown_turn = None
                # 인벤토리에도 반영
                if hasattr(self, 'inventory') and self.inventory:
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

            # 스킬 실행
            self.logger.info(f"{getattr(caster, 'name', 'Unknown')}의 {skill.name} 발동!")

            # 스킬 실행 (SFX 포함)
            from src.character.skills.skill_manager import get_skill_manager
            skill_manager = get_skill_manager()

            # 캐스팅이 완료되었으므로 실제 스킬 효과를 적용
            result = skill.execute(caster, target, context={"combat_manager": self})

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

        # 모든 스탯에 대해 보너스 계산 및 적용
        for stat in Stats:
            base_value = character.stat_manager.get_value(stat, use_total=False)
            bonus_value = int(base_value * multiplier)
            if bonus_value > 0:
                character.stat_manager.add_bonus(stat, source, bonus_value)

    def _check_battle_end(self) -> None:
        """승리/패배 판정"""
        # 전투가 이미 종료된 상태라면 체크하지 않음
        if self.state in [CombatState.VICTORY, CombatState.DEFEAT, CombatState.FLED]:
            return
        
        # 모든 적이 죽었는가?
        if all(self._is_defeated(enemy) for enemy in self.enemies):
            self._end_combat(CombatState.VICTORY)
            return

        # 모든 아군이 죽었는가?
        if all(self._is_defeated(ally) for ally in self.allies):
            # 전투 참여한 파티원이 모두 죽었으면 패배 (맵으로 복귀)
            # 멀티플레이 모드: 모든 플레이어의 모든 캐릭터가 죽었는지 확인
            if hasattr(self, 'session') and self.session:
                all_players_dead = True
                for player_id, player in self.session.players.items():
                    if hasattr(player, 'party') and player.party:
                        # 플레이어의 파티 중 살아있는 캐릭터가 있는지 확인
                        has_alive = False
                        for char in player.party:
                            if hasattr(char, 'is_alive') and char.is_alive:
                                has_alive = True
                                break
                            elif hasattr(char, 'current_hp') and char.current_hp > 0:
                                has_alive = True
                                break
                        if has_alive:
                            all_players_dead = False
                            break
                
                if all_players_dead:
                    # 모든 플레이어의 모든 캐릭터가 죽었으면 게임오버
                    self.logger.info("모든 플레이어의 모든 캐릭터가 죽었습니다. 게임오버.")
                    # 게임오버 플래그 설정 (main.py에서 게임오버로 처리)
                    self.is_game_over = True
                else:
                    # 전투 참여 파티원만 죽었으면 패배 (맵으로 복귀)
                    self.logger.info("전투 참여 파티원이 모두 죽었습니다. 패배 (맵으로 복귀).")
                    self.is_game_over = False
                
                self._end_combat(CombatState.DEFEAT)
                return
            else:
                # 싱글플레이 모드: 전투 참여자만 체크 (패배, 맵으로 복귀)
                self.logger.info("전투 참여 파티원이 모두 죽었습니다. 패배 (맵으로 복귀).")
                self.is_game_over = False
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

    def get_action_order(self) -> List[Any]:
        """
        현재 행동 순서 가져오기

        Returns:
            행동 가능한 전투원 리스트
        """
        return self.atb.get_action_order()

    @property
    def party(self) -> List[Any]:
        """
        아군 파티 (allies의 별칭)

        Returns:
            아군 리스트
        """
        return self.allies

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
            
            # 스탯 수정 효과는 별도로 처리 (현재 턴에는 데미지/회복만)
            # 스탯 수정은 get_stat_modifiers로 별도 계산되어 데미지 계산에 반영되어야 함


# 전역 인스턴스
_combat_manager: Optional[CombatManager] = None


def get_combat_manager() -> CombatManager:
    """전역 전투 관리자 인스턴스"""
    global _combat_manager
    if _combat_manager is None:
        _combat_manager = CombatManager()
    return _combat_manager
