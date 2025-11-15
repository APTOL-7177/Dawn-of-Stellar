"""Effect Base"""
from dataclasses import dataclass, field
from typing import Any, Dict, List
from enum import Enum

class EffectType(Enum):
    DAMAGE = "damage"
    HEAL = "heal"
    GIMMICK = "gimmick"
    BUFF = "buff"

@dataclass
class EffectResult:
    """효과 결과"""
    effect_type: EffectType
    success: bool
    damage_dealt: int = 0
    brv_damage: int = 0
    hp_damage: int = 0
    heal_amount: int = 0
    brv_gained: int = 0
    brv_broken: bool = False
    critical: bool = False
    gimmick_changes: Dict[str, Any] = field(default_factory=dict)
    message: str = ""

    def merge(self, other):
        """결과 병합"""
        self.damage_dealt += other.damage_dealt
        self.brv_damage += other.brv_damage
        self.hp_damage += other.hp_damage
        self.heal_amount += other.heal_amount
        self.brv_gained += other.brv_gained
        self.brv_broken = self.brv_broken or other.brv_broken
        self.critical = self.critical or other.critical
        self.gimmick_changes.update(other.gimmick_changes)

class SkillEffect:
    """효과 베이스"""
    def __init__(self, effect_type: EffectType):
        self.effect_type = effect_type
    
    def can_execute(self, user, target, context) -> bool:
        return True
    
    def execute(self, user, target, context) -> EffectResult:
        return EffectResult(effect_type=self.effect_type, success=True)
