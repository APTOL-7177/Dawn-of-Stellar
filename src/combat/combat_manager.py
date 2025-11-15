"""
Combat Manager - 전투 관리자

ATB, Brave, Damage 시스템을 통합하여 전투 흐름 제어
"""

from typing import List, Dict, Any, Optional, Callable
from enum import Enum

from src.core.config import get_config
from src.core.logger import get_logger
from src.core.event_bus import event_bus, Events
from src.combat.atb_system import get_atb_system, ATBSystem
from src.combat.brave_system import get_brave_system, BraveSystem
from src.combat.damage_calculator import get_damage_calculator, DamageCalculator
from src.combat.status_effects import StatusManager, StatusEffect, StatusType
from src.audio import play_sfx


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

        # 콜백
        self.on_combat_end: Optional[Callable[[CombatState], None]] = None
        self.on_turn_start: Optional[Callable[[Any], None]] = None
        self.on_action_complete: Optional[Callable[[Any, Dict], None]] = None

    def start_combat(self, allies: List[Any], enemies: List[Any]) -> None:
        """
        전투 시작

        Args:
            allies: 아군 리스트
            enemies: 적군 리스트
        """
        self.logger.info("전투 시작!")

        # 전투원 설정
        self.allies = allies
        self.enemies = enemies
        self.turn_count = 0
        self.state = CombatState.IN_PROGRESS

        # ATB 시스템에 전투원 등록
        for ally in allies:
            self.atb.register_combatant(ally)
            self.brave.initialize_brv(ally)

        for enemy in enemies:
            self.atb.register_combatant(enemy)
            self.brave.initialize_brv(enemy)

        # 캐스팅 시스템 초기화
        from src.combat.casting_system import get_casting_system
        casting_system = get_casting_system()
        casting_system.clear()

        # 이벤트 발행
        event_bus.publish(Events.COMBAT_START, {
            "allies": allies,
            "enemies": enemies
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
        self.current_actor = actor
        result = {}

        # 턴 시작 처리
        # 1. BREAK 상태 해제
        if self.brave.is_broken(actor):
            self.logger.debug(f"{actor.name}의 BREAK 상태 해제")
            self.brave.clear_break_state(actor)

        # 2. INT BRV 회복
        int_brv_recovered = self.brave.recover_int_brv(actor)
        if int_brv_recovered > 0:
            self.logger.debug(f"{actor.name}이(가) INT BRV {int_brv_recovered} 회복")

        self.logger.debug(
            f"행동 실행: {actor.name} → {action_type.value}",
            {"target": getattr(target, "name", None) if target else None}
        )

        # 행동 타입별 처리
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

        # ATB 소비
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
        **kwargs
    ) -> Dict[str, Any]:
        """BRV 공격 실행"""
        # SFX 재생
        play_sfx("combat", "attack_physical")

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

        # BRV 공격 적용
        brv_result = self.brave.brv_attack(attacker, defender, damage_result.final_damage)

        # 공격 후 방어 스택 초기화
        if hasattr(attacker, 'defend_stack_count') and attacker.defend_stack_count > 0:
            attacker.defend_stack_count = 0

        return {
            "action": "brv_attack",
            "damage": damage_result.final_damage,
            "is_critical": damage_result.is_critical,
            "brv_stolen": brv_result["brv_stolen"],
            "actual_gain": brv_result["actual_gain"],
            "is_break": brv_result["is_break"],
            "defend_stack_bonus": defend_stack_bonus
        }

    def _execute_hp_attack(
        self,
        attacker: Any,
        defender: Any,
        skill: Optional[Any] = None,
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

        # BREAK 상태 확인
        is_break = self.brave.is_broken(defender)

        # HP 공격 적용 (BRV 소비 및 데미지 적용)
        # brave.hp_attack()이 take_damage()를 내부적으로 호출함
        hp_result = self.brave.hp_attack(attacker, defender, hp_multiplier)

        # HP 공격 후 BRV 확실히 0으로 리셋 (이중 체크)
        self.logger.warning(f"[combat_manager] HP 공격 후 {attacker.name} BRV: {attacker.current_brv}")
        if attacker.current_brv != 0:
            self.logger.error(f"[combat_manager] BRV가 0이 아님! 강제 리셋 실행")
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
        # 1. BRV 공격
        brv_attack_result = self._execute_brv_attack(attacker, defender, skill, **kwargs)

        # 2. HP 공격 (BRV가 있으면)
        if attacker.current_brv > 0:
            hp_attack_result = self._execute_hp_attack(attacker, defender, skill, **kwargs)
        else:
            hp_attack_result = {"hp_damage": 0, "wound_damage": 0, "brv_consumed": 0}

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

        # context에 모든 적 정보 추가 (AOE 효과를 위해)
        all_enemies = self.enemies if actor in getattr(self, 'party', []) else getattr(self, 'party', [])

        # SkillManager를 통해 스킬 실행
        skill_result = skill_manager.execute_skill(
            skill.skill_id,
            actor,
            target,
            context={"combat_manager": self, "all_enemies": all_enemies}
        )

        if skill_result.success:
            result["success"] = True
            result["message"] = skill_result.message
        else:
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
            "targets": [],
            "effects": []
        }

        # MP/HP 코스트 지불
        if hasattr(actor, 'current_mp'):
            actor.current_mp = max(0, actor.current_mp - skill.mp_cost)
        if hasattr(actor, 'current_hp'):
            actor.current_hp = max(1, actor.current_hp - skill.hp_cost)

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
        elif target:
            # 단일 대상
            if isinstance(target, list):
                targets = target
            else:
                targets = [target]

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
                    if skill.is_magical:
                        base_damage = int(skill.damage + actor.magic_attack * skill.damage_multiplier)
                        defense = getattr(tgt, 'magic_defense', 0)
                    else:
                        base_damage = int(skill.damage + actor.physical_attack * skill.damage_multiplier)
                        defense = getattr(tgt, 'physical_defense', 0)

                    # 방어력 적용
                    final_damage = max(1, base_damage - defense // 2)

                    # BRV 데미지
                    if skill.brv_damage > 0:
                        if hasattr(tgt, 'current_brv'):
                            brv_dmg = min(skill.brv_damage, tgt.current_brv)
                            tgt.current_brv = max(0, tgt.current_brv - brv_dmg)
                            target_result["brv_damage"] = brv_dmg

                    # HP 데미지
                    if skill.hp_attack or not skill.brv_damage:
                        if hasattr(tgt, 'take_damage'):
                            actual_damage = tgt.take_damage(final_damage)
                        elif hasattr(tgt, 'current_hp'):
                            actual_damage = min(final_damage, tgt.current_hp)
                            tgt.current_hp -= actual_damage
                        else:
                            actual_damage = final_damage
                        target_result["hp_damage"] = actual_damage

            # 힐링 적용
            if skill.heal_amount > 0:
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
                        for effect_name, effect_data in skill.status_effects.items():
                            if isinstance(effect_data, dict):
                                duration = effect_data.get('duration', 3)
                                intensity = effect_data.get('intensity', 1.0)
                            else:
                                duration = 3
                                intensity = 1.0

                            status_type = self._map_status_to_status_type(effect_name)
                            if status_type:
                                status_effect = StatusEffect(
                                    name=effect_name,
                                    status_type=status_type,
                                    duration=duration,
                                    intensity=intensity,
                                    source_id=getattr(actor, 'id', None)
                                )
                                status_mgr.add_status(status_effect)

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

        if isinstance(item, Consumable) or (hasattr(item, 'item_type') and item.item_type == ItemType.CONSUMABLE):
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
                if hasattr(tgt, 'current_mp') and hasattr(tgt, 'max_mp'):
                    healed = min(int(effect_value), tgt.max_mp - tgt.current_mp)
                    tgt.current_mp += healed
                    result["mp_healing"] = healed

            elif effect_type == "buff":
                # 버프 효과 (간단하게 처리)
                result["buff_applied"] = True

            elif effect_type == "cure":
                # 상태이상 치료
                if hasattr(tgt, 'status_manager'):
                    # 디버프 및 상태이상 제거 (예시)
                    result["status_cured"] = True

            # 인벤토리에서 아이템 제거
            if hasattr(actor, 'inventory'):
                try:
                    actor.inventory.remove_item(item, 1)
                except Exception as e:
                    # 인벤토리 제거 실패 (아이템 없음 등)
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

    def _on_turn_end(self, actor: Any) -> None:
        """
        턴 종료 처리

        Args:
            actor: 행동한 캐릭터
        """
        # 턴 종료 시에는 BRV 회복하지 않음 (HP 공격 후 BRV가 0인 상태 유지)
        # BRV 회복은 다음 턴 시작 시에 처리됨

        # 이벤트 발행
        event_bus.publish(Events.COMBAT_TURN_END, {
            "actor": actor,
            "turn": self.turn_count
        })

        self.turn_count += 1

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

                # 쿨다운 설정
                if skill.cooldown > 0:
                    skill_manager.set_cooldown(caster, skill.skill_id, skill.cooldown)

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

    def _check_battle_end(self) -> None:
        """승리/패배 판정"""
        # 모든 적이 죽었는가?
        if all(self._is_defeated(enemy) for enemy in self.enemies):
            self._end_combat(CombatState.VICTORY)
            return

        # 모든 아군이 죽었는가?
        if all(self._is_defeated(ally) for ally in self.allies):
            self._end_combat(CombatState.DEFEAT)
            return

    def _is_defeated(self, character: Any) -> bool:
        """캐릭터가 전투 불능 상태인지 확인"""
        if hasattr(character, "is_alive"):
            return not character.is_alive
        if hasattr(character, "current_hp"):
            return character.current_hp <= 0
        return False

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

        # 시스템 정리
        self.atb.clear()

    def get_action_order(self) -> List[Any]:
        """
        현재 행동 순서 가져오기

        Returns:
            행동 가능한 전투원 리스트
        """
        return self.atb.get_action_order()

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
            elif action_type_str == "defend":
                # 방어
                return self.execute_action(
                    enemy,
                    ActionType.DEFEND
                )
            else:
                # 일반 공격
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

    def _map_status_to_status_type(self, status_name: str) -> Optional[StatusType]:
        """상태이상 이름을 StatusType으로 매핑"""
        status_mapping = {
            "poison": StatusType.POISON,
            "burn": StatusType.BURN,
            "bleed": StatusType.BLEED,
            "stun": StatusType.STUN,
            "sleep": StatusType.SLEEP,
            "silence": StatusType.SILENCE,
            "blind": StatusType.BLIND,
            "paralyze": StatusType.PARALYZE,
            "freeze": StatusType.FREEZE,
            "petrify": StatusType.PETRIFY,
            "curse": StatusType.CURSE,
            "slow": StatusType.SLOW,
            "corrosion": StatusType.CORROSION,
            "disease": StatusType.DISEASE,
            "charm": StatusType.CHARM,
            "dominate": StatusType.DOMINATE,
            "root": StatusType.ROOT,
            "chill": StatusType.CHILL,
            "shock": StatusType.SHOCK,
            "madness": StatusType.MADNESS,
            "taunt": StatusType.TAUNT,
        }

        return status_mapping.get(status_name.lower())


# 전역 인스턴스
_combat_manager: Optional[CombatManager] = None


def get_combat_manager() -> CombatManager:
    """전역 전투 관리자 인스턴스"""
    global _combat_manager
    if _combat_manager is None:
        _combat_manager = CombatManager()
    return _combat_manager
