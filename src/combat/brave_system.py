"""
Brave System - 브레이브 시스템

Final Fantasy Dissidia/Opera Omnia 스타일의 BRV/HP 시스템

주요 기능:
- INT BRV: 초기 BRV (전투 시작 시 / 턴 시작 시 회복)
- MAX BRV: 최대 BRV 제한
- BRV 공격: 상대 BRV 감소 + 자신 BRV 증가
- HP 공격: 축적된 BRV를 소비하여 HP 데미지
- BREAK: 상대 BRV를 0으로 만들면 보너스 데미지 + 스턴
"""

from typing import Dict, Any, Optional
from src.core.config import get_config
from src.core.logger import get_logger
from src.core.event_bus import event_bus, Events
from src.combat.damage_calculator import get_damage_calculator


class BraveSystem:
    """
    브레이브 시스템 매니저

    BRV 공격, HP 공격, BREAK 메커니즘 관리
    """

    def __init__(self) -> None:
        self.logger = get_logger("brave")
        self.config = get_config()

        # 설정 로드
        self.base_brv = self.config.get("combat.brave.base_brv", 100)
        self.max_brv_multiplier = self.config.get("combat.brave.max_brv_multiplier", 3.0)
        self.break_bonus = self.config.get("combat.brave.break_bonus", 1.5)
        self.break_stun_duration = self.config.get("combat.brave.break_stun_duration", 1)

        # BRV 효율 및 저항
        self.brv_efficiency_default = 1.0
        self.brv_loss_resistance_default = 1.0

    def calculate_int_brv(self, character: Any) -> int:
        """
        INT BRV 계산 (초기 BRV)

        Args:
            character: 캐릭터 객체

        Returns:
            계산된 INT BRV
        """
        # SimpleEnemy는 이미 생성자에서 current_brv가 설정되어 있으므로 그대로 사용
        if hasattr(character, '__class__') and character.__class__.__name__ == "SimpleEnemy":
            return character.current_brv

        # Character 객체는 StatManager를 통해 init_brv 가져오기
        if hasattr(character, "stat_manager"):
            from src.character.stats import Stats
            base_int_brv = int(character.stat_manager.get_value(Stats.INIT_BRV, use_total=False))
        elif hasattr(character, "init_brv"):
            base_int_brv = character.init_brv
        else:
            base_int_brv = self.base_brv

        # 레벨 보너스
        level = getattr(character, "level", 1)
        level_bonus = (level - 1) * 10

        # 장비 보너스
        equipment_bonus = self._get_equipment_int_brv_bonus(character)

        total_int_brv = base_int_brv + level_bonus + equipment_bonus

        return max(50, total_int_brv)

    def calculate_max_brv(self, character: Any) -> int:
        """
        MAX BRV 계산 (최대 BRV)

        Args:
            character: 캐릭터 객체

        Returns:
            계산된 MAX BRV
        """
        # SimpleEnemy는 이미 생성자에서 max_brv가 설정되어 있으므로 그대로 사용
        if hasattr(character, '__class__') and character.__class__.__name__ == "SimpleEnemy":
            return character.max_brv

        # Character 객체는 StatManager를 통해 max_brv 가져오기
        if hasattr(character, "stat_manager"):
            from src.character.stats import Stats
            base_max_brv = int(character.stat_manager.get_value(Stats.MAX_BRV, use_total=False))
        elif hasattr(character, "max_brv") and not callable(getattr(type(character), "max_brv", None)):
            # max_brv가 property가 아닌 일반 속성인 경우
            base_max_brv = character.max_brv
        else:
            # INT BRV 기반으로 계산
            int_brv = self.calculate_int_brv(character)
            base_max_brv = int(int_brv * self.max_brv_multiplier)

        # 레벨 보너스
        level = getattr(character, "level", 1)
        level_bonus = (level - 1) * 50

        # 장비 보너스
        equipment_bonus = self._get_equipment_max_brv_bonus(character)

        total_max_brv = base_max_brv + level_bonus + equipment_bonus

        return max(200, total_max_brv)

    def _get_equipment_int_brv_bonus(self, character: Any) -> int:
        """장비로부터 INT BRV 보너스 계산"""
        bonus = 0
        if hasattr(character, "equipped_weapon") and character.equipped_weapon:
            bonus += getattr(character.equipped_weapon, "int_brv", 0)
        if hasattr(character, "equipped_armor") and character.equipped_armor:
            bonus += getattr(character.equipped_armor, "int_brv", 0)
        if hasattr(character, "equipped_accessory") and character.equipped_accessory:
            bonus += getattr(character.equipped_accessory, "int_brv", 0)
        return bonus

    def _get_equipment_max_brv_bonus(self, character: Any) -> int:
        """장비로부터 MAX BRV 보너스 계산"""
        bonus = 0
        if hasattr(character, "equipped_weapon") and character.equipped_weapon:
            bonus += getattr(character.equipped_weapon, "max_brv", 0)
        if hasattr(character, "equipped_armor") and character.equipped_armor:
            bonus += getattr(character.equipped_armor, "max_brv", 0)
        if hasattr(character, "equipped_accessory") and character.equipped_accessory:
            bonus += getattr(character.equipped_accessory, "max_brv", 0)
        return bonus

    def initialize_brv(self, character: Any) -> None:
        """
        전투 시작 시 BRV 초기화

        Args:
            character: 캐릭터 객체
        """
        # INT BRV와 MAX BRV 계산
        int_brv = self.calculate_int_brv(character)
        max_brv = self.calculate_max_brv(character)

        # 캐릭터에 저장
        character.current_brv = int_brv
        character.int_brv = int_brv
        character.max_brv = max_brv

        # BRV 효율 및 저항 초기화
        if not hasattr(character, "brv_efficiency"):
            character.brv_efficiency = self.brv_efficiency_default
        if not hasattr(character, "brv_loss_resistance"):
            character.brv_loss_resistance = self.brv_loss_resistance_default

        self.logger.debug(
            f"BRV 초기화: {character.name}",
            {"int_brv": int_brv, "max_brv": max_brv}
        )

        event_bus.publish(Events.CHARACTER_BRV_CHANGE, {
            "character": character,
            "change": int_brv,
            "current": int_brv,
            "max": max_brv
        })

    def brv_attack(
        self,
        attacker: Any,
        defender: Any,
        damage: int
    ) -> Dict[str, Any]:
        """
        BRV 공격

        상대방의 BRV를 감소시키고 자신의 BRV를 증가시킵니다.
        효율과 저항이 반영됩니다.

        Args:
            attacker: 공격자
            defender: 방어자
            damage: BRV 데미지

        Returns:
            공격 결과 {"brv_stolen": int, "actual_gain": int, "is_break": bool}
        """
        # 빗나간 공격 (데미지 0)은 BRV 회복 없음
        if damage == 0:
            return {
                "brv_stolen": 0,
                "actual_gain": 0,
                "is_break": False,
                "damage": 0,
                "miss": True
            }

        # 방어자의 BRV 저항 반영
        defender_resistance = getattr(defender, "brv_loss_resistance", 1.0)
        actual_damage = int(damage / defender_resistance)

        # BRV 감소 (최소 0)
        old_defender_brv = defender.current_brv
        defender.current_brv = max(0, defender.current_brv - actual_damage)

        # BREAK 상태 확인 (공격 전 BRV가 0)
        was_broken = old_defender_brv == 0

        # BRV 획득량 계산
        if was_broken:
            # BREAK 상태: 가한 데미지만큼 BRV 획득
            brv_stolen = actual_damage
        else:
            # 일반 상태: 실제로 훔친 BRV
            brv_stolen = min(actual_damage, max(0, old_defender_brv))

        # 공격자의 BRV 효율 반영
        attacker_efficiency = getattr(attacker, "brv_efficiency", 1.0)
        brv_gain = int(brv_stolen * attacker_efficiency)

        # BRV 흡수 (MAX BRV 제한)
        old_attacker_brv = attacker.current_brv
        attacker.current_brv = min(
            attacker.current_brv + brv_gain,
            attacker.max_brv
        )
        actual_gain = attacker.current_brv - old_attacker_brv

        # BREAK 판정: 이미 BRV가 0인 상태에서 추가 공격을 받으면 BREAK
        is_break = False
        if was_broken and actual_damage > 0:
            is_break = True
            self.logger.info(f"⚡ BREAK! {attacker.name} → {defender.name} (BRV 획득: {brv_gain})")

            # BREAK 상태 플래그 설정
            defender.is_broken = True

            event_bus.publish("brave.break", {
                "attacker": attacker,
                "defender": defender,
                "brv_stolen": brv_stolen
            })

        # 이벤트 발행
        event_bus.publish(Events.CHARACTER_BRV_CHANGE, {
            "character": attacker,
            "change": actual_gain,
            "current": attacker.current_brv,
            "max": attacker.max_brv
        })

        event_bus.publish(Events.CHARACTER_BRV_CHANGE, {
            "character": defender,
            "change": -brv_stolen,
            "current": defender.current_brv,
            "max": defender.max_brv
        })

        return {
            "brv_stolen": brv_stolen,
            "actual_gain": actual_gain,
            "is_break": is_break,
            "damage": actual_damage,
            "miss": False
        }

    def hp_attack(
        self,
        attacker: Any,
        defender: Any,
        brv_multiplier: float = 1.0,
        damage_type: str = "physical",
        **kwargs
    ) -> Dict[str, Any]:
        """
        HP 공격

        축적된 BRV를 소비하여 HP 데미지를 가합니다.
        공격자의 스탯(힘/마법)과 방어자의 스탯(방어/정신)을 고려합니다.

        Args:
            attacker: 공격자
            defender: 방어자
            brv_multiplier: BRV 배율 (스킬에 따라 다름)
            damage_type: 데미지 타입 ("physical" 또는 "magical")

        Returns:
            공격 결과 {"hp_damage": int, "brv_consumed": int}
        """
        if attacker.current_brv <= 0:
            self.logger.warning(f"{attacker.name}: BRV가 0이라 HP 공격 불가")
            return {"hp_damage": 0, "brv_consumed": 0}

        # 데미지 계산기 사용
        damage_calc = get_damage_calculator()

        # BREAK 상태 확인 (is_broken 플래그 사용, BRV=0만으로는 BREAK가 아님)
        is_defender_broken = self.is_broken(defender)

        # HP 데미지 계산 (스탯 기반)
        damage_result, wound_damage = damage_calc.calculate_hp_damage(
            attacker=attacker,
            defender=defender,
            brv_points=attacker.current_brv,
            hp_multiplier=brv_multiplier,
            is_break=is_defender_broken,
            damage_type=damage_type,
            **kwargs  # 관통탄 방어 관통력 등 전달
        )

        # HP 데미지 적용 전에 상처 적용 플래그 설정 (중복 방지)
        if hasattr(defender, "wound"):
            defender._wound_applied_this_turn = True
        
        # HP 데미지 적용
        # shield_mastery 등의 DEFEND_BOOST 효과는 take_damage 내부의 calculate_damage_reduction에서 처리됨
        # 여기서는 BRV 회복만 처리
        from src.character.trait_effects import get_trait_effect_manager, TraitEffectType
        trait_manager = get_trait_effect_manager()
        
        # 방어 중인지 확인
        is_defending = False
        if hasattr(defender, 'status_manager'):
            from src.combat.status_effects import StatusType
            if hasattr(defender.status_manager, 'has_status'):
                is_defending = defender.status_manager.has_status(StatusType.GUARDIAN) or \
                               defender.status_manager.has_status(StatusType.SHIELD)
        
        # 방어 보너스: BRV 회복만 여기서 처리 (피해 감소는 take_damage에서 처리)
        if is_defending and hasattr(defender, 'active_traits'):
            for trait_data in defender.active_traits:
                trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                effects = trait_manager.get_trait_effects(trait_id)
                for effect in effects:
                    if effect.effect_type == TraitEffectType.DEFEND_BOOST:
                        # BRV 회복만 처리
                        if effect.metadata and "brv_regen" in effect.metadata:
                            brv_regen = effect.metadata["brv_regen"]
                            brv_recovered = int(defender.max_brv * brv_regen)
                            old_brv = defender.current_brv
                            defender.current_brv = min(defender.current_brv + brv_recovered, defender.max_brv)
                            actual_brv_regen = defender.current_brv - old_brv
                            if actual_brv_regen > 0:
                                self.logger.info(f"[{trait_id}] {defender.name} BRV 회복: +{actual_brv_regen} ({brv_regen * 100:.0f}%)")
        
        # 보호 효과를 위해 원본 공격 정보 저장
        defender._last_attacker = attacker
        defender._last_damage_type = damage_type
        defender._last_brv_points = attacker.current_brv
        defender._last_hp_multiplier = brv_multiplier
        defender._last_is_break = is_defender_broken
        defender._last_damage_kwargs = kwargs.copy()
        defender._last_original_damage = damage_result.base_damage  # 방어력 적용 전 원본 데미지
        
        # HP 데미지 적용 (피해 감소는 take_damage 내부에서 처리)
        hp_damage = defender.take_damage(damage_result.final_damage)
        
        # 보호 효과 처리 후 원본 정보 제거
        if hasattr(defender, '_last_attacker'):
            delattr(defender, '_last_attacker')
        if hasattr(defender, '_last_damage_type'):
            delattr(defender, '_last_damage_type')
        if hasattr(defender, '_last_brv_points'):
            delattr(defender, '_last_brv_points')
        if hasattr(defender, '_last_hp_multiplier'):
            delattr(defender, '_last_hp_multiplier')
        if hasattr(defender, '_last_is_break'):
            delattr(defender, '_last_is_break')
        if hasattr(defender, '_last_damage_kwargs'):
            delattr(defender, '_last_damage_kwargs')
        if hasattr(defender, '_last_original_damage'):
            delattr(defender, '_last_original_damage')
        
        # 상처 데미지 적용 (HP 데미지의 일부가 상처로 전환)
        # WoundSystem의 이벤트 핸들러는 플래그로 인해 무시됨
        if hasattr(defender, "wound") and wound_damage > 0:
            # WoundSystem의 설정 사용
            from src.systems.wound_system import get_wound_system
            wound_system = get_wound_system()
            max_wound = int(defender.max_hp * wound_system.max_wound_percentage)
            if defender.wound + wound_damage > max_wound:
                wound_damage = max(0, max_wound - defender.wound)

            defender.wound += wound_damage
            self.logger.info(f"상처 축적: {defender.name} +{wound_damage} (총 {defender.wound}/{max_wound})")
        
        # 플래그 해제
        if hasattr(defender, "_wound_applied_this_turn"):
            defender._wound_applied_this_turn = False

        # 생명력/마력 흡수 적용 (lifesteal, mana_leech)
        from src.character.trait_effects import get_trait_effect_manager
        trait_manager = get_trait_effect_manager()
        
        lifesteal_rate = trait_manager.calculate_lifesteal(attacker)
        if lifesteal_rate > 0 and hp_damage > 0:
            heal_amount = int(hp_damage * lifesteal_rate)
            if hasattr(attacker, 'heal'):
                actual_heal = attacker.heal(heal_amount)
                if actual_heal > 0:
                    self.logger.info(f"[생명력 흡수] {attacker.name} HP 회복: +{actual_heal} ({lifesteal_rate * 100:.0f}%)")
        
        mana_leech_rate = trait_manager.calculate_mana_leech(attacker)
        if mana_leech_rate > 0 and hp_damage > 0:
            mp_amount = int(hp_damage * mana_leech_rate)
            if hasattr(attacker, 'restore_mp'):
                actual_mp = attacker.restore_mp(mp_amount)
                if actual_mp > 0:
                    self.logger.info(f"[마력 흡수] {attacker.name} MP 회복: +{actual_mp} ({mana_leech_rate * 100:.0f}%)")

        # BRV 소비
        brv_consumed = attacker.current_brv
        self.logger.debug(f"[HP 공격] {attacker.name} BRV 소비: {brv_consumed}")
        attacker.current_brv = 0

        event_bus.publish(Events.CHARACTER_BRV_CHANGE, {
            "character": attacker,
            "change": -brv_consumed,
            "current": 0,
            "max": attacker.max_brv
        })

        self.logger.info(
            f"HP 공격: {attacker.name} → {defender.name}",
            {
                "brv_consumed": brv_consumed,
                "hp_damage": hp_damage,
                "wound_damage": wound_damage,
                "total_wound": defender.wound if hasattr(defender, "wound") else 0,
                "damage_type": damage_type,
                "stat_modifier": damage_result.variance,
                "is_critical": damage_result.is_critical,
                "is_break_bonus": is_defender_broken,
                "attacker_brv_after": attacker.current_brv
            }
        )

        return {
            "hp_damage": hp_damage,
            "wound_damage": wound_damage,
            "brv_consumed": brv_consumed,
            "is_break_bonus": is_defender_broken,
            "is_critical": damage_result.is_critical,
            "damage_type": damage_type,
            "stat_modifier": damage_result.variance
        }

    def brv_hp_attack(
        self,
        attacker: Any,
        defender: Any,
        brv_damage: int,
        hp_multiplier: float = 1.0,
        damage_type: str = "physical"
    ) -> Dict[str, Any]:
        """
        BRV + HP 복합 공격

        BRV 공격 후 즉시 HP 공격을 수행합니다.

        Args:
            attacker: 공격자
            defender: 방어자
            brv_damage: BRV 데미지
            hp_multiplier: HP 배율
            damage_type: 데미지 타입 ("physical" 또는 "magical")

        Returns:
            공격 결과
        """
        # 1. BRV 공격
        brv_result = self.brv_attack(attacker, defender, brv_damage)

        # 2. HP 공격 (데미지 타입 전달)
        hp_result = self.hp_attack(attacker, defender, hp_multiplier, damage_type)

        return {
            **brv_result,
            **hp_result,
            "is_combo": True
        }

    def restore_brv(self, character: Any, amount: int) -> int:
        """
        BRV 회복

        Args:
            character: 캐릭터
            amount: 회복량

        Returns:
            실제 회복량
        """
        old_brv = character.current_brv
        character.current_brv = min(character.current_brv + amount, character.max_brv)
        actual_restore = character.current_brv - old_brv

        event_bus.publish(Events.CHARACTER_BRV_CHANGE, {
            "character": character,
            "change": actual_restore,
            "current": character.current_brv,
            "max": character.max_brv
        })

        return actual_restore

    def reset_brv(self, character: Any) -> None:
        """BRV를 초기값으로 리셋"""
        old_brv = character.current_brv
        character.current_brv = character.init_brv

        event_bus.publish(Events.CHARACTER_BRV_CHANGE, {
            "character": character,
            "change": character.current_brv - old_brv,
            "current": character.current_brv,
            "max": character.max_brv
        })

    def is_broken(self, character: Any) -> bool:
        """BREAK 상태 여부"""
        return getattr(character, "is_broken", False)

    def recover_int_brv(self, character: Any) -> int:
        """
        턴 시작 시 INT BRV 회복

        BRV가 0일 때 INT BRV로 회복합니다.

        Args:
            character: 캐릭터

        Returns:
            회복된 BRV 양
        """
        # BREAK 상태 확인
        if self.is_broken(character):
            # BREAK 턴 카운터 증가
            if not hasattr(character, "break_turn_count"):
                character.break_turn_count = 0
            character.break_turn_count += 1

            # BREAK 상태를 1턴 동안만 유지
            if character.break_turn_count >= 1:
                # BREAK 해제 및 BRV 회복
                character.is_broken = False
                character.break_turn_count = 0
                character.current_brv = character.int_brv

                self.logger.info(f"{character.name} BREAK 해제 및 BRV 회복: {character.int_brv}")

                event_bus.publish(Events.CHARACTER_BRV_CHANGE, {
                    "character": character,
                    "change": character.int_brv,
                    "current": character.current_brv,
                    "max": character.max_brv
                })

                return character.int_brv
            else:
                # 아직 BREAK 상태 유지
                self.logger.debug(f"{character.name} BREAK 상태 유지")
                return 0

        # 일반적인 경우: BRV가 0일 때만 회복
        if character.current_brv <= 0:
            character.current_brv = character.int_brv

            event_bus.publish(Events.CHARACTER_BRV_CHANGE, {
                "character": character,
                "change": character.int_brv,
                "current": character.current_brv,
                "max": character.max_brv
            })

            return character.int_brv

        return 0

    def clear_break_state(self, character: Any) -> None:
        """BREAK 상태 강제 해제"""
        if hasattr(character, "is_broken"):
            character.is_broken = False
        if hasattr(character, "break_turn_count"):
            character.break_turn_count = 0


# 전역 인스턴스
_brave_system: Optional[BraveSystem] = None


def get_brave_system() -> BraveSystem:
    """전역 Brave 시스템 인스턴스"""
    global _brave_system
    if _brave_system is None:
        _brave_system = BraveSystem()
    return _brave_system
