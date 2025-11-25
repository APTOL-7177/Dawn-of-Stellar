"""
Damage Calculator - 데미지 계산 시스템

BRV 데미지, HP 데미지, 상처 데미지 계산
밸런스 조정된 데미지 공식 적용
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import random

from src.core.config import get_config
from src.core.logger import get_logger


@dataclass
class DamageResult:
    """데미지 계산 결과"""
    base_damage: int
    final_damage: int
    is_critical: bool
    multiplier: float
    variance: float
    details: Dict[str, Any]


class DamageCalculator:
    """
    데미지 계산기

    BRV 데미지 및 HP 데미지 계산
    """

    def __init__(self) -> None:
        self.logger = get_logger("damage")
        self.config = get_config()

        # 밸런스 설정
        self.brv_damage_multiplier = self.config.get("combat.damage.brv_multiplier", 1.5)
        self.hp_damage_multiplier = self.config.get("combat.damage.hp_multiplier", 0.15)
        self.level_scaling_per_level = self.config.get("combat.damage.level_scaling_per_level", 0.3)
        self.break_damage_bonus = self.config.get("combat.damage.break_bonus", 1.5)
        self.wound_damage_rate = self.config.get("combat.damage.wound_rate", 0.25)
        self.critical_multiplier = self.config.get("combat.damage.critical_multiplier", 1.5)
        self.critical_base_chance = self.config.get("combat.damage.critical_chance", 0.1)

    def calculate_brv_damage(
        self,
        attacker: Any,
        defender: Any,
        skill_multiplier: float = 1.0,
        **kwargs
    ) -> DamageResult:
        """
        BRV 데미지 계산

        공식: (공격력 - 방어력) * 배율 * 랜덤(0.9~1.1) * 크리티컬

        Args:
            attacker: 공격자
            defender: 방어자
            skill_multiplier: 스킬 배율
            **kwargs: 추가 옵션 (ignore_evasion: 회피 무시)

        Returns:
            DamageResult
        """
        # 명중 판정 (회피 무시가 아닌 경우)
        ignore_evasion = kwargs.get("ignore_evasion", False)
        if not ignore_evasion and not self.check_hit(attacker, defender):
            # 회피 성공 - 데미지 0
            return DamageResult(
                base_damage=0,
                final_damage=0,
                is_critical=False,
                multiplier=0,
                variance=0,
                details={"miss": True}
            )

        # 스탯 추출
        attacker_atk = self._get_attack_stat(attacker)
        defender_def = self._get_defense_stat(defender)

        # pierce: 방어 무시 (%) - 방어력을 %만큼 무시
        if kwargs.get('pierce'):
            pierce_percent = kwargs['pierce']  # 0.3 = 30% 방어 무시
            defender_def = int(defender_def * (1.0 - pierce_percent))
            self.logger.debug(f"[관통] 방어 {pierce_percent*100:.0f}% 무시 → 유효 방어력: {defender_def}")

        # 관통탄 방어 관통력 적용 (공격력의 15% 고정수치)
        if kwargs.get('defense_pierce_fixed'):
            pierce_amount = int(attacker_atk * kwargs['defense_pierce_fixed'])
            # 방어력을 고정수치만큼 감소
            defender_def = max(0, defender_def - pierce_amount)
            self.logger.debug(f"[관통탄] 방어 관통: {pierce_amount} (공격력 {attacker_atk}의 {kwargs['defense_pierce_fixed']*100}%)")

        # 기본 데미지 계산: 공격력 / 방어력 비율
        stat_modifier = attacker_atk / (defender_def + 1.0)
        base_damage = max(1, int(stat_modifier * skill_multiplier * self.brv_damage_multiplier))

        # 특성 효과: HP 비례 공격력 (berserker_rage 등)
        from src.character.trait_effects import get_trait_effect_manager
        trait_manager = get_trait_effect_manager()
        hp_scaling_mult = 1.0
        if hasattr(attacker, 'active_traits'):
            for trait_data in attacker.active_traits:
                trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                effects = trait_manager.get_trait_effects(trait_id)
                for effect in effects:
                    if effect.effect_type.value == "hp_scaling_attack":
                        # HP가 낮을수록 공격력 증가
                        if hasattr(attacker, 'current_hp') and hasattr(attacker, 'max_hp'):
                            hp_percent = attacker.current_hp / attacker.max_hp if attacker.max_hp > 0 else 1.0
                            max_bonus = effect.metadata.get("max_bonus", effect.value) if effect.metadata else effect.value
                            # HP 0%일 때 최대 보너스, HP 100%일 때 보너스 없음
                            bonus_mult = 1.0 + (max_bonus * (1.0 - hp_percent))
                            hp_scaling_mult *= bonus_mult
        
        base_damage = int(base_damage * hp_scaling_mult)

        # 랜덤 변수 (90% ~ 110%)
        variance = random.uniform(0.9, 1.1)
        damage = base_damage * variance

        # 크리티컬 판정
        is_critical = self._check_critical(attacker)
        critical_dmg_mult = 1.0
        if is_critical:
            # 크리티컬 데미지 배율 (critical_master 등)
            critical_dmg_mult = trait_manager.calculate_critical_damage(attacker)
            damage *= (self.critical_multiplier * critical_dmg_mult)
            self.logger.debug(f"크리티컬 히트! {attacker.name} (배율: {self.critical_multiplier * critical_dmg_mult:.2f}x)")

        final_damage = max(1, int(damage))

        # 난이도 보정 (플레이어가 공격자인 경우)
        from src.core.difficulty import get_difficulty_system
        difficulty_system = get_difficulty_system()
        if difficulty_system and self._is_player(attacker):
            player_dmg_mult = difficulty_system.get_player_damage_multiplier()
            final_damage = int(final_damage * player_dmg_mult)

        self.logger.debug(
            f"BRV 데미지 계산: {attacker.name} → {defender.name}",
            {
                "base": base_damage,
                "final": final_damage,
                "critical": is_critical
            }
        )

        return DamageResult(
            base_damage=base_damage,
            final_damage=final_damage,
            is_critical=is_critical,
            multiplier=skill_multiplier,
            variance=variance,
            details={
                "attacker_atk": attacker_atk,
                "defender_def": defender_def,
                "brv_multiplier": self.brv_damage_multiplier
            }
        )

    def calculate_hp_damage(
        self,
        attacker: Any,
        defender: Any,
        brv_points: int,
        hp_multiplier: float = 1.0,
        is_break: bool = False,
        damage_type: str = "physical",
        **kwargs
    ) -> Tuple[DamageResult, int]:
        """
        HP 데미지 계산

        공식: BRV 포인트 * HP 배율 * 스탯 보정 * (BREAK 보너스)
        상처 데미지: HP 데미지의 25%

        Args:
            attacker: 공격자
            defender: 방어자
            brv_points: 축적된 BRV
            hp_multiplier: HP 배율
            is_break: BREAK 상태 여부
            damage_type: 데미지 타입 ("physical" 또는 "magical")
            **kwargs: 추가 옵션

        Returns:
            (DamageResult, wound_damage)
        """
        # 스탯 기반 보정 (공격자 스탯 vs 방어자 스탯)
        if damage_type == "magical":
            attacker_stat = self._get_magic_stat(attacker)
            defender_stat = self._get_spirit_stat(defender)
        else:  # physical
            attacker_stat = self._get_attack_stat(attacker)
            defender_stat = self._get_defense_stat(defender)

        # pierce: 방어 무시 (%) - 방어력을 %만큼 무시
        if kwargs.get('pierce'):
            pierce_percent = kwargs['pierce']  # 0.3 = 30% 방어 무시
            defender_stat = int(defender_stat * (1.0 - pierce_percent))
            self.logger.debug(f"[관통] HP 공격 방어 {pierce_percent*100:.0f}% 무시 → 유효 방어력: {defender_stat}")

        # 관통탄 방어 관통력 적용 (공격력의 15% 고정수치)
        if kwargs.get('defense_pierce_fixed'):
            pierce_amount = int(attacker_stat * kwargs['defense_pierce_fixed'])
            # 방어력을 고정수치만큼 감소
            defender_stat = max(0, defender_stat - pierce_amount)
            self.logger.debug(f"[관통탄] HP 공격 방어 관통: {pierce_amount} (공격력 {attacker_stat}의 {kwargs['defense_pierce_fixed']*100}%)")

        # 스탯 보정 계산: 공격자 스탯 / (방어자 스탯 + 1)
        stat_modifier = attacker_stat / (defender_stat + 1.0)

        # HP 데미지 계산: BRV × 스킬계수 × 스탯배율 × HP배율 × 레벨보정
        # hp_multiplier: 스킬 계수 (기본 1.0 + 기믹 보너스)
        # stat_modifier: 공격/방어 비율
        # hp_damage_multiplier: HP 데미지 조정 계수 (config에서 설정)
        # level_scaling: 공격자 레벨에 따른 피해량 증가 (레벨당 30%)

        # 공격자 레벨에 따른 피해량 증가
        attacker_level = getattr(attacker, 'level', 1)
        level_scaling = 1.0 + (attacker_level - 1) * self.level_scaling_per_level

        base_damage = int(brv_points * hp_multiplier * stat_modifier * self.hp_damage_multiplier * level_scaling)

        self.logger.warning(f"[HP 데미지 계산] BRV:{brv_points} × 스킬계수:{hp_multiplier:.2f} × 스탯배율:{stat_modifier:.2f} × HP배율:{self.hp_damage_multiplier} × 레벨보정:{level_scaling:.2f} = {base_damage}")

        damage = base_damage

        # 특성 효과: HP 비례 공격력 (berserker_rage 등)
        from src.character.trait_effects import get_trait_effect_manager
        trait_manager = get_trait_effect_manager()
        hp_scaling_mult = 1.0
        if hasattr(attacker, 'active_traits'):
            for trait_data in attacker.active_traits:
                trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                effects = trait_manager.get_trait_effects(trait_id)
                for effect in effects:
                    if effect.effect_type.value == "hp_scaling_attack":
                        # HP가 낮을수록 공격력 증가
                        if hasattr(attacker, 'current_hp') and hasattr(attacker, 'max_hp'):
                            hp_percent = attacker.current_hp / attacker.max_hp if attacker.max_hp > 0 else 1.0
                            max_bonus = effect.metadata.get("max_bonus", effect.value) if effect.metadata else effect.value
                            # HP 0%일 때 최대 보너스, HP 100%일 때 보너스 없음
                            bonus_mult = 1.0 + (max_bonus * (1.0 - hp_percent))
                            hp_scaling_mult *= bonus_mult
        
        damage = int(damage * hp_scaling_mult)

        # 언데드 추가 피해 (undead_bonus)
        if kwargs.get('undead_bonus'):
            is_undead = getattr(defender, 'is_undead', False) or getattr(defender, 'race', '') == 'undead'
            if is_undead:
                undead_mult = 1.0 + kwargs['undead_bonus']  # 0.5 = +50% 데미지
                damage = int(damage * undead_mult)
                self.logger.info(f"[언데드 추가 피해] {attacker.name} → {defender.name} (언데드): 데미지 +{kwargs['undead_bonus']*100:.0f}%")

        # 크리티컬 판정
        is_critical = self._check_critical(attacker)
        critical_dmg_mult = 1.0
        if is_critical:
            # 크리티컬 데미지 배율 (critical_master 등)
            critical_dmg_mult = trait_manager.calculate_critical_damage(attacker)
            damage = int(damage * self.critical_multiplier * critical_dmg_mult)
            self.logger.info(f"[CRITICAL] HP 공격! {attacker.name} (배율: {self.critical_multiplier * critical_dmg_mult:.2f}x)")

        # BREAK 보너스
        if is_break:
            # 브레이크 보너스 계산 (break_master 등)
            break_bonus = trait_manager.calculate_break_bonus(attacker)
            if break_bonus > 0:
                # break_bonus는 추가 배율 (1.5 = 150%)
                break_mult = 1.0 + (break_bonus - 1.0)
            else:
                break_mult = self.break_damage_bonus
            damage = int(damage * break_mult)
            self.logger.info(f"[BREAK BONUS] 데미지! {damage} ({break_mult:.2f}x)")

        final_damage = max(5, damage)
        
        # 피해 감소 적용 (damage_reduction, brave_soul 등)
        damage_reduction = trait_manager.calculate_damage_reduction(defender, is_defending=kwargs.get("is_defending", False))
        if damage_reduction > 0:
            final_damage = int(final_damage * (1.0 - damage_reduction))
            self.logger.debug(f"[{defender.name}] 피해 감소 적용: {damage_reduction * 100:.1f}% → 최종 피해: {final_damage}")

        # 난이도 보정 (플레이어가 공격자인 경우)
        from src.core.difficulty import get_difficulty_system
        difficulty_system = get_difficulty_system()
        if difficulty_system and self._is_player(attacker):
            player_dmg_mult = difficulty_system.get_player_damage_multiplier()
            final_damage = int(final_damage * player_dmg_mult)

        # 상처 데미지 (HP 데미지의 25%)
        wound_damage = int(final_damage * self.wound_damage_rate)

        self.logger.debug(
            f"HP 데미지 계산: {attacker.name} → {defender.name}",
            {
                "brv_points": brv_points,
                "skill_multiplier": hp_multiplier,
                "level_scaling": level_scaling,
                "base_damage": base_damage,
                "stat_modifier": f"{stat_modifier:.2f}",
                "attacker_stat": attacker_stat,
                "defender_stat": defender_stat,
                "damage_type": damage_type,
                "is_critical": is_critical,
                "final_damage": final_damage,
                "wound_damage": wound_damage,
                "is_break": is_break
            }
        )

        result = DamageResult(
            base_damage=base_damage,
            final_damage=final_damage,
            is_critical=is_critical,
            multiplier=hp_multiplier,
            variance=stat_modifier,  # 스탯 보정을 variance로 기록
            details={
                "brv_points": brv_points,
                "skill_multiplier": hp_multiplier,
                "stat_modifier": stat_modifier,
                "attacker_stat": attacker_stat,
                "defender_stat": defender_stat,
                "damage_type": damage_type,
                "is_critical": is_critical,
                "critical_multiplier": self.critical_multiplier if is_critical else 1.0,
                "is_break": is_break,
                "break_bonus": self.break_damage_bonus if is_break else 1.0
            }
        )

        return result, wound_damage

    def calculate_magic_damage(
        self,
        attacker: Any,
        defender: Any,
        skill_multiplier: float = 1.0,
        element: Optional[str] = None,
        **kwargs
    ) -> DamageResult:
        """
        마법 데미지 계산

        Args:
            attacker: 공격자
            defender: 방어자
            skill_multiplier: 스킬 배율
            element: 속성 (fire, ice, lightning 등)
            **kwargs: 추가 옵션 (ignore_evasion: 회피 무시)

        Returns:
            DamageResult
        """
        # 명중 판정 (회피 무시가 아닌 경우)
        ignore_evasion = kwargs.get("ignore_evasion", False)
        if not ignore_evasion and not self.check_hit(attacker, defender):
            # 회피 성공 - 데미지 0
            return DamageResult(
                base_damage=0,
                final_damage=0,
                is_critical=False,
                multiplier=0,
                variance=0,
                details={"miss": True}
            )

        # 마법 스탯 추출
        attacker_mag = self._get_magic_stat(attacker)
        defender_spr = self._get_spirit_stat(defender)

        # 기본 데미지 계산: 마법력 / 정신력 비율
        stat_modifier = attacker_mag / (defender_spr + 1.0)

        # 속성 보너스 (속성 저항 시스템 완전 구현됨)
        element_bonus = 1.0
        if element:
            element_bonus = self._get_element_bonus(defender, element)

        # 스킬 배율 적용
        base_damage = max(1, int(stat_modifier * skill_multiplier * self.brv_damage_multiplier * element_bonus))

        # 랜덤 변수
        variance = random.uniform(0.9, 1.1)
        damage = base_damage * variance

        # 크리티컬 판정
        is_critical = self._check_critical(attacker)
        if is_critical:
            damage *= self.critical_multiplier

        final_damage = max(1, int(damage))

        return DamageResult(
            base_damage=base_damage,
            final_damage=final_damage,
            is_critical=is_critical,
            multiplier=skill_multiplier,
            variance=variance,
            details={
                "attacker_mag": attacker_mag,
                "defender_spr": defender_spr,
                "element": element,
                "element_bonus": element_bonus
            }
        )

    def _get_attack_stat(self, character: Any) -> int:
        """공격력 스탯 추출 (버프 반영)"""
        # 여러 속성명 시도
        base_stat = 10
        for attr in ["physical_attack", "p_atk", "attack", "strength"]:
            if hasattr(character, attr):
                base_stat = getattr(character, attr)
                break
        
        # 버프/디버프 적용 (attack_up, attack_down)
        if hasattr(character, 'active_buffs') and character.active_buffs:
            if 'attack_up' in character.active_buffs:
                buff_value = character.active_buffs['attack_up'].get('value', 0.0)
                base_stat = int(base_stat * (1.0 + buff_value))
            if 'attack_down' in character.active_buffs:
                debuff_value = character.active_buffs['attack_down'].get('value', 0.0)
                base_stat = int(base_stat * (1.0 - debuff_value))
        
        return base_stat

    def _get_defense_stat(self, character: Any) -> int:
        """방어력 스탯 추출 (버프 반영)"""
        base_stat = 10
        for attr in ["physical_defense", "p_def", "defense"]:
            if hasattr(character, attr):
                base_stat = getattr(character, attr)
                break
        
        # 버프/디버프 적용 (defense_up, defense_down)
        if hasattr(character, 'active_buffs') and character.active_buffs:
            if 'defense_up' in character.active_buffs:
                buff_value = character.active_buffs['defense_up'].get('value', 0.0)
                base_stat = int(base_stat * (1.0 + buff_value))
            if 'defense_down' in character.active_buffs:
                debuff_value = character.active_buffs['defense_down'].get('value', 0.0)
                base_stat = int(base_stat * (1.0 - debuff_value))
        
        return base_stat

    def _get_magic_stat(self, character: Any) -> int:
        """마법력 스탯 추출 (버프 반영)"""
        base_stat = 10
        for attr in ["magic_attack", "m_atk", "magic", "intelligence"]:
            if hasattr(character, attr):
                base_stat = getattr(character, attr)
                break
        
        # 버프/디버프 적용 (magic_up, magic_down)
        if hasattr(character, 'active_buffs') and character.active_buffs:
            if 'magic_up' in character.active_buffs:
                buff_value = character.active_buffs['magic_up'].get('value', 0.0)
                base_stat = int(base_stat * (1.0 + buff_value))
            if 'magic_down' in character.active_buffs:
                debuff_value = character.active_buffs['magic_down'].get('value', 0.0)
                base_stat = int(base_stat * (1.0 - debuff_value))
        
        return base_stat

    def _get_spirit_stat(self, character: Any) -> int:
        """정신력 스탯 추출"""
        for attr in ["magic_defense", "m_def", "spirit", "resistance"]:
            if hasattr(character, attr):
                return getattr(character, attr)
        return 10  # 기본값

    def _get_accuracy_stat(self, character: Any) -> int:
        """명중률 스탯 추출 (버프 반영)"""
        base_stat = 50
        for attr in ["accuracy", "acc", "hit_rate"]:
            if hasattr(character, attr):
                base_stat = getattr(character, attr)
                break
        
        # 버프/디버프 적용 (accuracy_up, accuracy_down)
        if hasattr(character, 'active_buffs') and character.active_buffs:
            if 'accuracy_up' in character.active_buffs:
                buff_value = character.active_buffs['accuracy_up'].get('value', 0.0)
                base_stat = int(base_stat * (1.0 + buff_value))
            if 'accuracy_down' in character.active_buffs:
                debuff_value = character.active_buffs['accuracy_down'].get('value', 0.0)
                base_stat = int(base_stat * (1.0 - debuff_value))
        
        return base_stat

    def _get_evasion_stat(self, character: Any) -> int:
        """회피율 스탯 추출"""
        for attr in ["evasion", "eva", "dodge"]:
            if hasattr(character, attr):
                return getattr(character, attr)
        return 10  # 기본값

    def _is_player(self, character: Any) -> bool:
        """플레이어 캐릭터 여부 확인"""
        # Character 클래스의 인스턴스인지 확인 (적은 SimpleEnemy)
        from src.character.character import Character
        return isinstance(character, Character)

    def check_hit(self, attacker: Any, defender: Any) -> bool:
        """
        명중 판정

        명중/회피 비율 기반 공식 (로그 스케일):
        - 기준 명중률: 65% (base)
        - 최종 명중률 = 65% + 50 * log10(명중 / 회피)
        - 상한선: 98%, 하한선: 30%

        예시:
        - 명중 50, 회피 10: 65% + 50*log10(5) = 99.9% → 98% (상한)
        - 명중 50, 회피 20: 65% + 50*log10(2.5) = 84.9%
        - 명중 50, 회피 30: 65% + 50*log10(1.67) = 76.1%
        - 명중 50, 회피 50: 65% + 50*log10(1) = 65% (동등)
        - 명중 50, 회피 70: 65% + 50*log10(0.71) = 57.7%
        - 명중 50, 회피 100: 65% + 50*log10(0.5) = 49.9%
        - 명중 50, 회피 150: 65% + 50*log10(0.33) = 41.1%

        Args:
            attacker: 공격자
            defender: 방어자

        Returns:
            명중 여부
        """
        import math

        accuracy = self._get_accuracy_stat(attacker)
        evasion = self._get_evasion_stat(defender)

        # 회피가 0이면 최소값 1로 설정 (0으로 나누기 방지)
        evasion = max(1, evasion)

        # 명중/회피 비율 계산
        ratio = accuracy / evasion

        # 로그 스케일로 명중률 계산
        # 65% + 50 * log10(명중/회피)
        final_hit_rate = 65.0 + 50.0 * math.log10(ratio)

        # 최소/최대 제한 (30% ~ 98%)
        final_hit_rate = max(30.0, min(98.0, final_hit_rate))

        # 확률 변환 (0.0 ~ 1.0)
        hit_chance_pct = final_hit_rate / 100.0

        is_hit = random.random() < hit_chance_pct

        if not is_hit:
            self.logger.debug(
                f"공격 회피! {getattr(defender, 'name', 'Unknown')}가 "
                f"{getattr(attacker, 'name', 'Unknown')}의 공격을 피했다 "
                f"(명중률: {final_hit_rate:.1f}%, 명중: {accuracy}, 회피: {evasion}, 비율: {ratio:.2f})"
            )
        else:
            self.logger.debug(
                f"공격 명중! (명중률: {final_hit_rate:.1f}%, 명중: {accuracy}, 회피: {evasion}, 비율: {ratio:.2f})"
            )

        return is_hit

    def _check_critical(self, attacker: Any) -> bool:
        """
        크리티컬 판정

        Args:
            attacker: 공격자

        Returns:
            크리티컬 여부
        """
        # 행운 스탯 추출
        luck = getattr(attacker, "luck", 5)

        # 크리티컬 확률 = 기본 확률 + (행운 / 100)
        critical_chance = self.critical_base_chance + (luck / 100.0)

        # 크리티컬 확률 상한선 (95%)
        critical_chance = min(0.95, critical_chance)

        return random.random() < critical_chance

    def _get_element_bonus(self, defender: Any, element: str) -> float:
        """
        속성 보너스 계산

        Args:
            defender: 방어자
            element: 속성

        Returns:
            보너스 배율 (저항 반영)
        """
        # 속성 저항 시스템 구현
        # defender.element_resistance = {"fire": 0.5, "ice": 2.0, ...}
        # 값이 1.0보다 작으면 약점 (데미지 증가), 크면 저항 (데미지 감소)
        if hasattr(defender, "element_resistance"):
            resistance = defender.element_resistance.get(element, 1.0)
            # resistance = 0.5 → 1.0/0.5 = 2.0 (데미지 2배, 약점)
            # resistance = 2.0 → 1.0/2.0 = 0.5 (데미지 0.5배, 저항)
            return 1.0 / resistance

        # 기본 스탯 기반 속성 저항 (spirit이 높으면 마법 저항)
        if element in ["fire", "ice", "lightning", "water", "earth", "wind", "holy", "dark"]:
            spirit = getattr(defender, "spirit", 10)
            # spirit 10당 2% 저항 (최대 20% at spirit 100)
            resistance_bonus = min(0.2, spirit * 0.002)
            return 1.0 - resistance_bonus

        return 1.0


# 전역 인스턴스
_damage_calculator: Optional[DamageCalculator] = None


def get_damage_calculator() -> DamageCalculator:
    """전역 데미지 계산기 인스턴스"""
    global _damage_calculator
    if _damage_calculator is None:
        _damage_calculator = DamageCalculator()
    return _damage_calculator
