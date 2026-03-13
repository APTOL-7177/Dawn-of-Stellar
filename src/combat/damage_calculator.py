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
        element: Optional[str] = None,
        **kwargs
    ) -> DamageResult:
        """
        BRV 데미지 계산

        공식: (공격력 - 방어력) * 배율 * 랜덤(0.9~1.1) * 크리티컬

        Args:
            attacker: 공격자
            defender: 방어자
            skill_multiplier: 스킬 배율
            element: 원소 속성 (fire, ice, lightning 등)
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

        # 물리 관통 적용 (% - 장비 효과)
        phys_pen_pct = getattr(attacker, 'physical_penetration', 0)
        if phys_pen_pct > 0:
            original_def = defender_def
            defender_def = int(defender_def * (1.0 - min(phys_pen_pct, 1.0)))
            self.logger.debug(f"[물리 관통] 방어 {phys_pen_pct*100:.1f}% 무시 → {original_def} → {defender_def}")

        # 물리 관통 적용 (고정수치 - 장비 효과)
        phys_pen_fixed = getattr(attacker, 'physical_penetration_fixed', 0)
        if phys_pen_fixed > 0:
            original_def = defender_def
            defender_def = max(0, defender_def - phys_pen_fixed)
            self.logger.debug(f"[물리 관통(고정)] 방어 -{phys_pen_fixed} → {original_def} → {defender_def}")

        # 기본 데미지 계산: 공격력 / 방어력 비율
        stat_modifier = attacker_atk / (defender_def + 1.0)
        
        # 원소 데미지 보너스 적용 (물리 원소 공격용)
        element_bonus = 1.0
        if element:
            element_bonus = self._get_element_bonus(defender, element)
            # 장비 원소 데미지 보너스
            elemental_damage_bonus = self._get_elemental_damage_stat(attacker, element)
            if elemental_damage_bonus > 0:
                attacker_atk += elemental_damage_bonus
                self.logger.debug(f"[원소 데미지] {element} 보너스: +{elemental_damage_bonus} → 공격력: {attacker_atk}")
                stat_modifier = attacker_atk / (defender_def + 1.0)
        
        base_damage = max(1, int(stat_modifier * skill_multiplier * self.brv_damage_multiplier * element_bonus))
        
        # 레벨 기반 배율: (1 + 공격자 레벨 * 0.3)
        attacker_level = getattr(attacker, 'level', 1)
        level_multiplier = 1.0 + (attacker_level * 0.3)
        base_damage = int(base_damage * level_multiplier)


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

        # 크리티컬 판정 (force_critical 지원)
        force_critical = kwargs.get('force_critical', False)
        is_critical = self._check_critical(attacker, defender, force_critical)
        critical_dmg_mult = 1.0
        if is_critical:
            # 크리티컬 데미지 배율 (critical_master 등)
            critical_dmg_mult = trait_manager.calculate_critical_damage(attacker)
            # 장비의 critical_damage 효과 추가
            equip_crit_bonus = self._get_equipment_critical_damage(attacker)
            total_crit_mult = (self.critical_multiplier * critical_dmg_mult) + equip_crit_bonus
            damage *= total_crit_mult
            self.logger.debug(f"크리티컬 히트! {attacker.name} (배율: {total_crit_mult:.2f}x)")

        final_damage = max(1, int(damage))

        # 검기 충격 특성 (sword_energy): 물리 공격 시 검기로 추가 피해 (공격력의 30%)
        sword_energy_bonus = 0
        if hasattr(attacker, 'active_traits'):
            for trait_data in attacker.active_traits:
                trait_id = trait_data if isinstance(trait_data, str) else (trait_data.get('id') if isinstance(trait_data, dict) else None)
                if trait_id == 'sword_energy':
                    sword_energy_bonus = int(attacker_atk * 0.30)
                    final_damage += sword_energy_bonus
                    self.logger.debug(f"[검기 충격] {attacker.name} 추가 피해: +{sword_energy_bonus}")
                    break
        
        # available_traits에서도 체크 (검성 기본 특성)
        if sword_energy_bonus == 0 and hasattr(attacker, 'available_traits'):
            for trait_data in attacker.available_traits:
                trait_id = trait_data if isinstance(trait_data, str) else (trait_data.get('id') if isinstance(trait_data, dict) else None)
                if trait_id == 'sword_energy':
                    sword_energy_bonus = int(attacker_atk * 0.30)
                    final_damage += sword_energy_bonus
                    self.logger.debug(f"[검기 충격] {attacker.name} 추가 피해: +{sword_energy_bonus}")
                    break

        # 특성 체크 헬퍼 함수
        def has_trait(char, trait_id_to_check):
            for attr in ['active_traits', 'available_traits']:
                if hasattr(char, attr) and getattr(char, attr):
                    for t in getattr(char, attr):
                        tid = t if isinstance(t, str) else (t.get('id') if isinstance(t, dict) else None)
                        if tid == trait_id_to_check:
                            return True
            return False

        # 집중의 일격 (focus_strike): 단일 대상 공격 시 데미지 +40%
        is_single_target = kwargs.get('is_single_target', True)  # 기본값 True
        if is_single_target and has_trait(attacker, 'focus_strike'):
            bonus = int(final_damage * 0.40)
            final_damage += bonus
            self.logger.debug(f"[집중의 일격] {attacker.name} 단일 대상 보너스: +{bonus}")

        # 필살의 일격 (final_strike): HP 30% 이하일 때 피해량 +50%
        if hasattr(attacker, 'current_hp') and hasattr(attacker, 'max_hp'):
            hp_percent = attacker.current_hp / max(1, attacker.max_hp)
            if hp_percent <= 0.30 and has_trait(attacker, 'final_strike'):
                bonus = int(final_damage * 0.50)
                final_damage += bonus
                self.logger.debug(f"[필살의 일격] {attacker.name} HP {hp_percent*100:.0f}% 보너스: +{bonus}")

        # 난이도 보정 (플레이어가 공격자인 경우)
        from src.core.difficulty import get_difficulty_system
        difficulty_system = get_difficulty_system()
        if difficulty_system and self._is_player(attacker):
            player_dmg_mult = difficulty_system.get_player_damage_multiplier()
            final_damage = int(final_damage * player_dmg_mult)

        # 아군 피해 경감 (적 → 아군 공격 시 40% 감소)
        if self._is_player(defender) and not self._is_player(attacker):
            final_damage = int(final_damage * 0.6)
            self.logger.debug(f"[아군 피해 경감] {defender.name} 받는 BRV 피해 40% 감소 → {final_damage}")

        # 아군 BRV 공격력 감소 (아군 → 적 공격 시 30% 감소)
        if self._is_player(attacker) and not self._is_player(defender):
            final_damage = int(final_damage * 0.7)
            self.logger.debug(f"[아군 BRV 감소] {attacker.name} BRV 피해 30% 감소 → {final_damage}")

        # [NEW] SCATTER 보너스 (BRV 공격에도 적용, 단 연격 게이지는 증가하지 않음)
        from src.combat.status_effects import StatusType
        
        is_scattered = getattr(defender, "is_scattered", False)
        if not is_scattered and hasattr(defender, 'status_manager'):
            is_scattered = defender.status_manager.has_status(StatusType.SCATTER)
        
        scatter_applied = False
        scatter_mult = 1.0
        if is_scattered:
            # 기본 수치
            scatter_base = 1.6
            scatter_ramp = 0.08
            
            # 원인 제공자(브레이커)의 특성 확인
            source = getattr(defender, "scatter_source", None)
            if not source and hasattr(defender, 'status_manager'):
                scatter_status = defender.status_manager.get_status(StatusType.SCATTER)
                if scatter_status:
                    source = getattr(scatter_status, 'source', None)
            
            if source:
                # 엔진 오버클럭 (engine_overclock): 150% -> 185% (기본 1.6에서 증가)
                is_overclock = False
                is_chemical = False
                
                if hasattr(source, "system_traits") and "engine_overclock" in source.system_traits: is_overclock = True
                if hasattr(source, "traits"):
                    for t in source.traits:
                        tid = t if isinstance(t, str) else t.get("id")
                        if tid == "engine_overclock": is_overclock = True
                        if tid == "chemical_resonance": is_chemical = True
                
                if is_overclock: scatter_base = 1.85
                if is_chemical: scatter_ramp = 0.12
            
            # 스택에 따른 배율 계산
            stack_count = 0
            if hasattr(defender, 'status_manager'):
                scatter_status = defender.status_manager.get_status(StatusType.SCATTER)
                if scatter_status:
                    # StatusEffect는 스택 1부터 시작하므로 -1 해줌 (초기 0스택 효과)
                    stack_count = max(0, scatter_status.stack_count - 1)
            
            # 이전 속성 fallback (호환성)
            if stack_count == 0:
                stack_count = getattr(defender, "scatter_stacks", 0)

            scatter_mult = scatter_base + (stack_count * scatter_ramp)
            final_damage = int(final_damage * scatter_mult)
            scatter_applied = True
            self.logger.info(f"[SCATTER-BRV] 데미지 배율: {scatter_mult:.2f}x (Base: {scatter_base}, Stack: {stack_count})")

        self.logger.debug(
            f"BRV 데미지 계산: {attacker.name} → {defender.name}",
            {
                "base": base_damage,
                "final": final_damage,
                "critical": is_critical,
                "scatter_applied": scatter_applied
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
                "brv_multiplier": self.brv_damage_multiplier,
                "is_scattered": scatter_applied,
                "scatter_multiplier": scatter_mult if scatter_applied else 1.0,
                # NOTE: BRV 공격은 scatter_ramp를 별도로 전달하지 않음 (연격 게이지 증가 방지)
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
        # 명중 판정 (회피 무시가 아닌 경우)
        ignore_evasion = kwargs.get("ignore_evasion", False)
        if not ignore_evasion and not self.check_hit(attacker, defender):
            # 회피 성공 - 데미지 0
            return (
                DamageResult(
                    base_damage=0,
                    final_damage=0,
                    is_critical=False,
                    multiplier=0,
                    variance=0,
                    details={"miss": True}
                ),
                0  # wound_damage = 0
            )

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

        # 장비 관통 효과 적용 (damage_type에 따라 물리/마법 관통)
        if damage_type == "magical":
            # 마법 관통 적용 (%)
            mag_pen_pct = getattr(attacker, 'magic_penetration', 0)
            if mag_pen_pct > 0:
                original_stat = defender_stat
                defender_stat = int(defender_stat * (1.0 - min(mag_pen_pct, 1.0)))
                self.logger.debug(f"[마법 관통] 마방 {mag_pen_pct*100:.1f}% 무시 → {original_stat} → {defender_stat}")

            # 마법 관통 적용 (고정수치)
            mag_pen_fixed = getattr(attacker, 'magic_penetration_fixed', 0)
            if mag_pen_fixed > 0:
                original_stat = defender_stat
                defender_stat = max(0, defender_stat - mag_pen_fixed)
                self.logger.debug(f"[마법 관통(고정)] 마방 -{mag_pen_fixed} → {original_stat} → {defender_stat}")
        else:  # physical
            # 물리 관통 적용 (%)
            phys_pen_pct = getattr(attacker, 'physical_penetration', 0)
            if phys_pen_pct > 0:
                original_stat = defender_stat
                defender_stat = int(defender_stat * (1.0 - min(phys_pen_pct, 1.0)))
                self.logger.debug(f"[물리 관통] 방어 {phys_pen_pct*100:.1f}% 무시 → {original_stat} → {defender_stat}")

            # 물리 관통 적용 (고정수치)
            phys_pen_fixed = getattr(attacker, 'physical_penetration_fixed', 0)
            if phys_pen_fixed > 0:
                original_stat = defender_stat
                defender_stat = max(0, defender_stat - phys_pen_fixed)
                self.logger.debug(f"[물리 관통(고정)] 방어 -{phys_pen_fixed} → {original_stat} → {defender_stat}")

        # 스탯 보정 계산: 공격자 스탯 / (방어자 스탯 + 1)
        stat_modifier = attacker_stat / (defender_stat + 1.0)

        # HP 데미지 계산: BRV × 스킬계수 × 스탯배율 × HP배율
        # hp_multiplier: 스킬 계수 (기본 1.0 + 기믹 보너스)
        # stat_modifier: 공격/방어 비율
        # hp_damage_multiplier: HP 데미지 조정 계수 (config에서 설정)

        base_damage = int(brv_points * hp_multiplier * stat_modifier * self.hp_damage_multiplier)

        self.logger.warning(f"[HP 데미지 계산] BRV:{brv_points} × 스킬계수:{hp_multiplier:.2f} × 스탯배율:{stat_modifier:.2f} × HP배율:{self.hp_damage_multiplier} = {base_damage}")

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

        # 크리티컬 판정 (force_critical 지원)
        force_critical = kwargs.get('force_critical', False)
        is_critical = self._check_critical(attacker, defender, force_critical)
        critical_dmg_mult = 1.0
        if is_critical:
            # 크리티컬 데미지 배율 (critical_master 등)
            critical_dmg_mult = trait_manager.calculate_critical_damage(attacker)
            # 장비의 critical_damage 효과 추가
            equip_crit_bonus = self._get_equipment_critical_damage(attacker)
            total_crit_mult = (self.critical_multiplier * critical_dmg_mult) + equip_crit_bonus
            damage = int(damage * total_crit_mult)
            self.logger.info(f"[CRITICAL] HP 공격! {attacker.name} (배율: {total_crit_mult:.2f}x)")

        # BREAK 및 SCATTER 보너스 (SCATTER 우선 적용)
        from src.combat.status_effects import StatusType
        
        details = {}  # 상세 정보 저장용
        
        # SCATTER 여부 확인
        is_scattered = getattr(defender, "is_scattered", False)
        if not is_scattered and hasattr(defender, 'status_manager'):
             is_scattered = defender.status_manager.has_status(StatusType.SCATTER)

        if is_scattered:
            # 기본 수치
            scatter_base = 1.6
            scatter_ramp = 0.08
            
            # 원인 제공자(브레이커)의 특성 확인
            source = getattr(defender, "scatter_source", None)
            if not source and hasattr(defender, 'status_manager'):
                scatter_status = defender.status_manager.get_status(StatusType.SCATTER)
                if scatter_status:
                    source = getattr(scatter_status, 'source', None)
            
            if source:
                # 엔진 오버클럭 (engine_overclock): 150% -> 185% (기본 1.6에서 증가)
                is_overclock = False
                is_chemical = False
                
                if hasattr(source, "system_traits") and "engine_overclock" in source.system_traits: is_overclock = True
                if hasattr(source, "traits"):
                        for t in source.traits:
                            tid = t if isinstance(t, str) else t.get("id")
                            if tid == "engine_overclock": is_overclock = True
                            if tid == "chemical_resonance": is_chemical = True
                
                if is_overclock: scatter_base = 1.85
                if is_chemical: scatter_ramp = 0.12
            
            # 스택에 따른 배율 계산
            stack_count = 0
            if hasattr(defender, 'status_manager'):
                 scatter_status = defender.status_manager.get_status(StatusType.SCATTER)
                 if scatter_status:
                     # StatusEffect는 스택 1부터 시작하므로 -1 해줌 (초기 0스택 효과)
                     stack_count = max(0, scatter_status.stack_count - 1)
            
            # 이전 속성 fallback (호환성)
            if stack_count == 0:
                 stack_count = getattr(defender, "scatter_stacks", 0)

            scatter_mult = scatter_base + (stack_count * scatter_ramp)
            
            damage = int(damage * scatter_mult)
            self.logger.info(f"[SCATTER] 데미지 배율: {scatter_mult:.2f}x (Base: {scatter_base}, Stack: {stack_count})")
            
            # 상세 정보에 scatter_ramp 추가 (연격 게이지 계산용)
            details["scatter_ramp"] = scatter_ramp
            
            # SCATTER 상태여도 BREAK 보너스는 중복 적용하지 않음 (SCATTER가 상위 호환)

        elif is_break:
            # 일반 BREAK 보너스
            break_bonus = trait_manager.calculate_break_bonus(attacker)
            if break_bonus > 0:
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

        # 적 HP 공격 피해 감소 (적의 모든 HP 공격 35% 감소)
        if not self._is_player(attacker):
            final_damage = int(final_damage * 0.65)
            self.logger.debug(f"[적 피해 감소] {attacker.name}의 HP 피해 35% 감소 → {final_damage}")

        # 아군 피해 경감 (적 → 아군 공격 시 추가 40% 감소, 곱적용)
        if self._is_player(defender) and not self._is_player(attacker):
            final_damage = int(final_damage * 0.6)
            self.logger.debug(f"[아군 피해 경감] {defender.name} 받는 HP 피해 40% 추가 감소 → {final_damage}")

        # 상처 데미지 (BREAK 상태면 75%, 아니면 25%)
        wound_rate = 0.75 if is_break else self.wound_damage_rate
        wound_damage = int(final_damage * wound_rate)

        self.logger.debug(
            f"HP 데미지 계산: {attacker.name} → {defender.name}",
            {
                "brv_points": brv_points,
                "skill_multiplier": hp_multiplier,
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
                "is_scattered": is_scattered,
                "scatter_source": source if 'source' in locals() and source else getattr(defender, "scatter_source", None),
                "stat_modifier": stat_modifier,
                "attacker_stat": attacker_stat,
                "defender_stat": defender_stat,
                "damage_type": damage_type,
                "is_critical": is_critical,
                "critical_multiplier": self.critical_multiplier if is_critical else 1.0,
                "is_break": is_break,
                "break_bonus": self.break_damage_bonus if is_break else 1.0,
                **details # scatter_ramp 등 병합
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

        # 마법 관통 적용 (% - 장비 효과)
        mag_pen_pct = getattr(attacker, 'magic_penetration', 0)
        if mag_pen_pct > 0:
            original_spr = defender_spr
            defender_spr = int(defender_spr * (1.0 - min(mag_pen_pct, 1.0)))
            self.logger.debug(f"[마법 관통] 마방 {mag_pen_pct*100:.1f}% 무시 → {original_spr} → {defender_spr}")

        # 마법 관통 적용 (고정수치 - 장비 효과)
        mag_pen_fixed = getattr(attacker, 'magic_penetration_fixed', 0)
        if mag_pen_fixed > 0:
            original_spr = defender_spr
            defender_spr = max(0, defender_spr - mag_pen_fixed)
            self.logger.debug(f"[마법 관통(고정)] 마방 -{mag_pen_fixed} → {original_spr} → {defender_spr}")

        # 기본 데미지 계산: 마법력 / 정신력 비율
        stat_modifier = attacker_mag / (defender_spr + 1.0)

        # 속성 보너스 (속성 저항 시스템 완전 구현됨)
        element_bonus = 1.0
        if element:
            element_bonus = self._get_element_bonus(defender, element)
            
            # 장비 원소 데미지 보너스 (fire_damage, ice_damage 등)
            # 원소 속성 스킬 사용 시 공격력/마법력에 추가
            elemental_damage_bonus = self._get_elemental_damage_stat(attacker, element)
            if elemental_damage_bonus > 0:
                attacker_mag += elemental_damage_bonus
                self.logger.debug(f"[원소 데미지] {element} 보너스: +{elemental_damage_bonus} → 마법력: {attacker_mag}")
                # stat_modifier 재계산
                stat_modifier = attacker_mag / (defender_spr + 1.0)

        # 스킬 배율 적용
        base_damage = max(1, int(stat_modifier * skill_multiplier * self.brv_damage_multiplier * element_bonus))

        # 레벨 기반 배율: 물리와 동일 (하드코딩 0.3/레벨)
        attacker_level = getattr(attacker, 'level', 1)
        level_multiplier = 1.0 + (attacker_level * 0.3)
        base_damage = int(base_damage * level_multiplier)

        # 마법 피해 계수 보정: 개별 스킬에 0.65 너프가 적용되어 있으므로
        # 0.85/0.65 = 1.3077 보정으로 실질 너프를 35% → 15%로 상향
        MAGIC_NERF_CORRECTION = 0.85 / 0.65
        base_damage = int(base_damage * MAGIC_NERF_CORRECTION)

        # 랜덤 변수
        variance = random.uniform(0.9, 1.1)
        damage = base_damage * variance

        # 크리티컬 판정 (force_critical 지원)
        force_critical = kwargs.get('force_critical', False)
        is_critical = self._check_critical(attacker, defender, force_critical)
        if is_critical:
            # 장비의 critical_damage 효과 추가
            from src.character.trait_effects import get_trait_effect_manager
            trait_manager = get_trait_effect_manager()
            critical_dmg_mult = trait_manager.calculate_critical_damage(attacker)
            equip_crit_bonus = self._get_equipment_critical_damage(attacker)
            total_crit_mult = (self.critical_multiplier * critical_dmg_mult) + equip_crit_bonus
            damage *= total_crit_mult

        final_damage = max(1, int(damage))

        # 아군 BRV 공격력 감소 (아군 → 적 공격 시 30% 감소) — 물리와 동일
        if self._is_player(attacker) and not self._is_player(defender):
            final_damage = int(final_damage * 0.7)
            self.logger.debug(f"[아군 BRV 감소] {attacker.name} 마법 BRV 피해 30% 감소 → {final_damage}")

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
        """공격력 스탯 추출 (버프/환경 효과 반영)"""
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
        
        # 환경 효과 스탯 수정치 적용
        if hasattr(character, 'env_stat_modifiers'):
            env_mult = character.env_stat_modifiers.get('strength', 1.0)
            base_stat = int(base_stat * env_mult)
        
        return base_stat

    def _get_defense_stat(self, character: Any) -> int:
        """방어력 스탯 추출 (버프/환경 효과 반영)"""
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
        
        # 환경 효과 스탯 수정치 적용
        if hasattr(character, 'env_stat_modifiers'):
            env_mult = character.env_stat_modifiers.get('defense', 1.0)
            base_stat = int(base_stat * env_mult)
        
        return base_stat

    def _get_magic_stat(self, character: Any) -> int:
        """마법력 스탯 추출 (버프/환경 효과 반영)"""
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
        
        # 환경 효과 스탯 수정치 적용
        if hasattr(character, 'env_stat_modifiers'):
            env_mult = character.env_stat_modifiers.get('magic', 1.0)
            base_stat = int(base_stat * env_mult)
        
        return base_stat

    def _get_spirit_stat(self, character: Any) -> int:
        """정신력 스탯 추출 (환경 효과 반영)"""
        base_stat = 10
        for attr in ["magic_defense", "m_def", "spirit", "resistance"]:
            if hasattr(character, attr):
                base_stat = getattr(character, attr)
                break
        
        # 환경 효과 스탯 수정치 적용
        if hasattr(character, 'env_stat_modifiers'):
            env_mult = character.env_stat_modifiers.get('magic_defense', 1.0)
            base_stat = int(base_stat * env_mult)
        
        return base_stat

    def _get_accuracy_stat(self, character: Any) -> int:
        """명중률 스탯 추출 (버프/환경 효과 반영)"""
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
        
        # 환경 효과 스탯 수정치 적용
        if hasattr(character, 'env_stat_modifiers'):
            env_mult = character.env_stat_modifiers.get('accuracy', 1.0)
            base_stat = int(base_stat * env_mult)
        
        return base_stat

    def _get_evasion_stat(self, character: Any) -> int:
        """
        회피율 스탯 추출 (버프/환경 효과 반영)

        NOTE: 확정 회피(>= 5.0)는 check_hit()에서 처리하므로 여기서는 제외
        """
        base_stat = 10
        for attr in ["evasion", "eva", "dodge"]:
            if hasattr(character, attr):
                base_stat = getattr(character, attr)
                break

        # 버프/디버프 적용 (evasion_up, evasion_down)
        # 확정 회피 제외하고는 일반 버프/디버프만 처리
        if hasattr(character, 'active_buffs') and character.active_buffs:
            if 'evasion_up' in character.active_buffs:
                buff_value = character.active_buffs['evasion_up'].get('value', 0.0)
                is_absolute = character.active_buffs['evasion_up'].get('is_absolute', False)

                # 확정 회피는 check_hit()에서 처리하므로 여기서는 무시
                if buff_value < 5.0:
                    if is_absolute or buff_value > 1.0:
                        # 고정값 증가: 1.0보다 크거나 is_absolute=true면 고정값
                        base_stat += max(1, int(buff_value))
                    else:
                        # 비율 증가: 1.0 이하면 백분율 (선호 방식)
                        base_stat = int(base_stat * (1.0 + buff_value))

            if 'evasion_down' in character.active_buffs:
                debuff_value = character.active_buffs['evasion_down'].get('value', 0.0)
                is_absolute = character.active_buffs['evasion_down'].get('is_absolute', False)

                if is_absolute or debuff_value > 1.0:
                    # 고정값 감소: 1.0보다 크거나 is_absolute=true면 고정값
                    base_stat = max(1, base_stat - int(debuff_value))
                else:
                    # 비율 감소: 1.0 이하면 백분율 (선호 방식)
                    base_stat = int(base_stat * (1.0 - debuff_value))

        # 환술사 환영 회피 보너스 적용
        if hasattr(character, 'gimmick_type') and character.gimmick_type == "phantom_legion":
            phantom_count = getattr(character, 'phantom_count', 0)
            evasion_per_phantom = getattr(character, 'phantom_evasion_bonus', 0.12)
            phantom_evasion_bonus = phantom_count * evasion_per_phantom
            if phantom_evasion_bonus > 0:
                base_stat = int(base_stat * (1.0 + phantom_evasion_bonus))

        # 환경 효과 스탯 수정치 적용
        if hasattr(character, 'env_stat_modifiers'):
            env_mult = character.env_stat_modifiers.get('evasion', 1.0)
            base_stat = int(base_stat * env_mult)

        return base_stat

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

        # 확정 회피 체크 (evasion_up >= 5.0)
        if hasattr(defender, 'active_buffs') and defender.active_buffs:
            if 'evasion_up' in defender.active_buffs:
                evasion_buff_value = defender.active_buffs['evasion_up'].get('value', 0.0)
                duration = defender.active_buffs['evasion_up'].get('duration', 0)
                if evasion_buff_value >= 5.0:
                    # 확정 회피
                    self.logger.info(
                        f"[확정 회피] {getattr(defender, 'name', 'Unknown')}가 "
                        f"{getattr(attacker, 'name', 'Unknown')}의 공격을 완벽하게 피했다! "
                        f"(회피 버프: +{evasion_buff_value*100:.0f}%, 남은 턴: {duration})"
                    )
                    return False
                else:
                    self.logger.debug(
                        f"[일반 회피] {getattr(defender, 'name', 'Unknown')} 회피 버프: +{evasion_buff_value*100:.0f}%, 남은 턴: {duration}"
                    )

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

    def _check_critical(self, attacker: Any, defender: Any = None, force_critical: bool = False) -> bool:
        """
        크리티컬 판정

        Args:
            attacker: 공격자
            defender: 방어자 (특성 조건 체크용)
            force_critical: 강제 크리티컬 (마술사 행운 카드 등)

        Returns:
            크리티컬 여부
        """
        # 강제 크리티컬 (마술사 7 카드 등)
        if force_critical:
            return True
        
        # 행운 스탯 추출
        luck = getattr(attacker, "luck", 5)

        # 크리티컬 확률 = 1 - (100 / (행운*2 + 100)) + 기본 확률
        # 행운 0: 10%, 행운 10: ~26%, 행운 30: ~48%, 행운 50: ~60%, 행운 100: ~76%
        luck_bonus = 1.0 - (100.0 / (luck * 2 + 100))
        critical_chance = luck_bonus + self.critical_base_chance
        
        # 특성에 의한 크리티컬 보너스 적용
        try:
            from src.character.trait_effects import get_trait_effect_manager
            trait_manager = get_trait_effect_manager()
            context = {"target": defender} if defender else {}
            trait_bonus = trait_manager.calculate_critical_bonus(attacker, **context)
            critical_chance += trait_bonus
            if trait_bonus > 0:
                self.logger.debug(f"[특성 크리티컬] {getattr(attacker, 'name', 'Unknown')} +{trait_bonus * 100:.0f}%")
        except Exception as e:
            self.logger.debug(f"특성 크리티컬 보너스 계산 실패: {e}")

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

    def _get_equipment_critical_damage(self, character: Any) -> float:
        """
        장비의 critical_damage 효과 합산
        
        Args:
            character: 캐릭터
            
        Returns:
            크리티컬 데미지 추가 배율 (0.5 = +50%)
        """
        bonus = 0.0
        
        if not hasattr(character, 'equipment') or not character.equipment:
            return bonus
            
        for slot, item in character.equipment.items():
            if not item:
                continue
            
            # special_effects에서 critical_damage 확인
            if hasattr(item, 'special_effects'):
                for effect in item.special_effects:
                    effect_type = getattr(effect, 'effect_type', None)
                    effect_value = getattr(effect, 'value', 0)
                    # EffectType enum의 value로 비교
                    type_value = getattr(effect_type, 'value', str(effect_type)) if effect_type else ''
                    if type_value == 'critical_damage':
                        bonus += effect_value
                        self.logger.debug(f"[장비 크리티컬] {item.name}: +{effect_value*100:.0f}%")
        
        return bonus

    def _get_elemental_damage_stat(self, character: Any, element: str) -> int:
        """
        원소별 추가 데미지 스탯 추출
        
        장비의 fire_damage, ice_damage, lightning_damage 등을 합산하여
        해당 원소 스킬 사용 시 공격력/마법력에 추가합니다.
        
        Args:
            character: 캐릭터
            element: 원소 타입 (fire, ice, lightning, holy, dark, earth, wind, water)
            
        Returns:
            원소 데미지 보너스 합계
        """
        # 원소별 속성명 매핑
        element_attr_map = {
            "fire": "fire_damage",
            "ice": "ice_damage",
            "lightning": "lightning_damage",
            "water": "water_damage",
            "earth": "earth_damage",
            "wind": "wind_damage",
            "holy": "holy_damage",
            "dark": "dark_damage",
        }
        
        bonus = 0
        attr_name = element_attr_map.get(element)
        
        if not attr_name:
            return 0
        
        # 캐릭터 속성에서 직접 가져오기 (장비 효과 합산된 값)
        if hasattr(character, attr_name):
            bonus += getattr(character, attr_name, 0)
        
        # 장비에서 원소 데미지 합산 (character.equipment가 있는 경우)
        if hasattr(character, 'equipment') and character.equipment:
            for slot, item in character.equipment.items():
                if item and hasattr(item, 'effects'):
                    for effect in item.effects:
                        if hasattr(effect, 'effect_type') and hasattr(effect, 'value'):
                            if effect.effect_type == attr_name:
                                bonus += effect.value
                        elif isinstance(effect, dict):
                            if effect.get('type') == attr_name or effect.get('effect_type') == attr_name:
                                bonus += effect.get('value', 0)
        
        # 추가 옵션 (affixes)에서도 확인
        if hasattr(character, 'equipment') and character.equipment:
            for slot, item in character.equipment.items():
                if item and hasattr(item, 'affixes'):
                    for affix in item.affixes:
                        if hasattr(affix, 'effect_type') and hasattr(affix, 'value'):
                            if affix.effect_type == attr_name:
                                bonus += affix.value
                        elif isinstance(affix, dict):
                            if affix.get('type') == attr_name or affix.get('effect_type') == attr_name:
                                bonus += affix.get('value', 0)
        
        return int(bonus)


# 전역 인스턴스
_damage_calculator: Optional[DamageCalculator] = None


def get_damage_calculator() -> DamageCalculator:
    """전역 데미지 계산기 인스턴스"""
    global _damage_calculator
    if _damage_calculator is None:
        _damage_calculator = DamageCalculator()
    return _damage_calculator
