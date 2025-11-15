"""Skill - 스킬 클래스"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

@dataclass
class SkillResult:
    """스킬 실행 결과"""
    success: bool
    message: str = ""
    total_damage: int = 0
    total_heal: int = 0

class Skill:
    """스킬 클래스"""
    def __init__(self, skill_id: str, name: str, description: str = ""):
        self.skill_id = skill_id
        self.name = name
        self.description = description
        self.effects = []
        self.costs = []
        self.target_type = "single_enemy"
        self.cast_time = None  # 기본값: 캐스팅 없음
        self.cooldown = 0
        self.category = "combat"
        self.is_ultimate = False
        self.metadata = {}
        self.sfx: Optional[Tuple[str, str]] = None  # (category, sfx_name) 튜플

    def can_use(self, user: Any, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """스킬 사용 가능 여부"""
        context = context or {}
        for cost in self.costs:
            can_afford, reason = cost.can_afford(user, context)
            if not can_afford:
                return False, reason
        return True, ""

    def execute(self, user: Any, target: Any, context: Optional[Dict[str, Any]] = None) -> SkillResult:
        """스킬 실행"""
        context = context or {}
        can_use, reason = self.can_use(user, context)
        if not can_use:
            return SkillResult(success=False, message=f"사용 불가: {reason}")

        # 비용 소비
        for cost in self.costs:
            if not cost.consume(user, context):
                return SkillResult(success=False, message="비용 소비 실패")

        # 효과 실행
        total_dmg = 0
        total_heal = 0
        for effect in self.effects:
            if hasattr(effect, 'execute'):
                result = effect.execute(user, target, context)
                if hasattr(result, 'damage_dealt'):
                    total_dmg += result.damage_dealt
                if hasattr(result, 'heal_amount'):
                    total_heal += result.heal_amount

        # AOE 효과 실행 (적 전체 대상)
        if hasattr(self, 'aoe_effect') and self.aoe_effect:
            # context에서 모든 적 가져오기
            all_enemies = context.get('all_enemies', [])
            if all_enemies and len(all_enemies) > 1:
                # 메인 타겟을 제외한 다른 적들에게 AOE 피해
                other_enemies = [e for e in all_enemies if e != target and hasattr(e, 'is_alive') and e.is_alive]
                if other_enemies and hasattr(self.aoe_effect, 'execute'):
                    aoe_result = self.aoe_effect.execute(user, other_enemies, context)
                    if hasattr(aoe_result, 'damage_dealt'):
                        total_dmg += aoe_result.damage_dealt

        return SkillResult(
            success=True,
            message=f"{user.name}이(가) {self.name} 사용!",
            total_damage=total_dmg,
            total_heal=total_heal
        )

    def get_description(self, user: Any) -> str:
        """스킬 설명"""
        parts = [self.description]
        if self.costs:
            cost_strs = [getattr(c, 'get_description', lambda u: "")(user) for c in self.costs]
            parts.append(f"비용: {', '.join([c for c in cost_strs if c])}")
        if self.cooldown > 0:
            parts.append(f"쿨다운: {self.cooldown}턴")
        return " | ".join(parts)

    def __repr__(self) -> str:
        return f"Skill({self.name})"
