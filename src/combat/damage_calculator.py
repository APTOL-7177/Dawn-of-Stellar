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

        # 기본 데미지 계산: 공격력 / 방어력 비율
        stat_modifier = attacker_atk / (defender_def + 1.0)
        base_damage = max(1, int(stat_modifier * skill_multiplier * self.brv_damage_multiplier))

        # 랜덤 변수 (90% ~ 110%)
        variance = random.uniform(0.9, 1.1)
        damage = base_damage * variance

        # 크리티컬 판정
        is_critical = self._check_critical(attacker)
        if is_critical:
            damage *= self.critical_multiplier
            self.logger.debug(f"크리티컬 히트! {attacker.name}")

        final_damage = max(1, int(damage))

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

        # 스탯 보정 계산: 공격자 스탯 / (방어자 스탯 + 1)
        stat_modifier = attacker_stat / (defender_stat + 1.0)

        # HP 데미지 계산: BRV × 스킬계수 × 스탯배율 × HP배율
        # hp_multiplier: 스킬 계수 (기본 1.0 + 기믹 보너스)
        # stat_modifier: 공격/방어 비율
        # hp_damage_multiplier: HP 데미지 조정 계수 (config에서 설정)
        base_damage = int(brv_points * hp_multiplier * stat_modifier * self.hp_damage_multiplier)

        self.logger.warning(f"[HP 데미지 계산] BRV:{brv_points} × 스킬계수:{hp_multiplier:.2f} × 스탯배율:{stat_modifier:.2f} × HP배율:{self.hp_damage_multiplier} = {base_damage}")

        damage = base_damage

        # 크리티컬 판정
        is_critical = self._check_critical(attacker)
        if is_critical:
            damage = int(damage * self.critical_multiplier)
            self.logger.info(f"⚡ 크리티컬 HP 공격! {attacker.name}")

        # BREAK 보너스
        if is_break:
            damage = int(damage * self.break_damage_bonus)
            self.logger.info(f"⚡ BREAK 보너스 데미지! {damage} ({self.break_damage_bonus}x)")

        final_damage = max(5, damage)

        # 상처 데미지 (HP 데미지의 25%)
        wound_damage = int(final_damage * self.wound_damage_rate)

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
        """공격력 스탯 추출"""
        # 여러 속성명 시도
        for attr in ["physical_attack", "p_atk", "attack", "strength"]:
            if hasattr(character, attr):
                return getattr(character, attr)
        return 10  # 기본값

    def _get_defense_stat(self, character: Any) -> int:
        """방어력 스탯 추출"""
        for attr in ["physical_defense", "p_def", "defense", "defense"]:
            if hasattr(character, attr):
                return getattr(character, attr)
        return 10  # 기본값

    def _get_magic_stat(self, character: Any) -> int:
        """마법력 스탯 추출"""
        for attr in ["magic_attack", "m_atk", "magic", "intelligence"]:
            if hasattr(character, attr):
                return getattr(character, attr)
        return 10  # 기본값

    def _get_spirit_stat(self, character: Any) -> int:
        """정신력 스탯 추출"""
        for attr in ["magic_defense", "m_def", "spirit", "resistance"]:
            if hasattr(character, attr):
                return getattr(character, attr)
        return 10  # 기본값

    def _get_accuracy_stat(self, character: Any) -> int:
        """명중률 스탯 추출"""
        for attr in ["accuracy", "acc", "hit_rate"]:
            if hasattr(character, attr):
                return getattr(character, attr)
        return 50  # 기본값

    def _get_evasion_stat(self, character: Any) -> int:
        """회피율 스탯 추출"""
        for attr in ["evasion", "eva", "dodge"]:
            if hasattr(character, attr):
                return getattr(character, attr)
        return 10  # 기본값

    def check_hit(self, attacker: Any, defender: Any) -> bool:
        """
        명중 판정

        공식: 명중률 - 회피율 = 최종 명중률 (최소 5%, 최대 95%)

        Args:
            attacker: 공격자
            defender: 방어자

        Returns:
            명중 여부
        """
        accuracy = self._get_accuracy_stat(attacker)
        evasion = self._get_evasion_stat(defender)

        # 최종 명중률 계산 (명중률 - 회피율)
        hit_chance = accuracy - evasion

        # 최소/최대 제한 (5% ~ 95%)
        hit_chance = max(5, min(95, hit_chance))

        # 확률 변환 (0.0 ~ 1.0)
        hit_chance_pct = hit_chance / 100.0

        is_hit = random.random() < hit_chance_pct

        if not is_hit:
            self.logger.debug(f"공격 회피! {defender.name}가 {attacker.name}의 공격을 피했다")

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
        # 값이 1.0보다 작으면 저항 (데미지 증가), 크면 약점 (데미지 감소)
        if hasattr(defender, "element_resistance"):
            resistance = defender.element_resistance.get(element, 1.0)
            # 저항 값이 0.5면 데미지 2배, 2.0이면 데미지 0.5배
            return 1.0 / resistance

        # 기본 스탯 기반 속성 저항 (spirit이 높으면 마법 저항)
        if element in ["fire", "ice", "lightning", "water", "earth", "wind", "holy", "dark"]:
            spirit = getattr(defender, "spirit", 10)
            # spirit 10당 2% 저항 (최대 20% at spirit 100)
            resistance_bonus = min(0.2, spirit * 0.002)
            return 1.0 + resistance_bonus

        return 1.0


# 전역 인스턴스
_damage_calculator: Optional[DamageCalculator] = None


def get_damage_calculator() -> DamageCalculator:
    """전역 데미지 계산기 인스턴스"""
    global _damage_calculator
    if _damage_calculator is None:
        _damage_calculator = DamageCalculator()
    return _damage_calculator
