"""Gimmick Cost - 기믹 수치 소모 비용"""
from typing import Any, Dict, Tuple
from src.character.skills.costs.base import SkillCost


class GimmickCost(SkillCost):
    """기믹 수치 소모 비용"""

    def __init__(self, field: str, amount: int):
        """
        Args:
            field: 기믹 필드명 (예: "combo", "ammo", "rage")
            amount: 소모량
        """
        super().__init__(f"gimmick_{field}")
        self.field = field
        self.amount = amount

    def can_afford(self, user: Any, context: Dict[str, Any]) -> Tuple[bool, str]:
        """기믹 수치가 충분한지 확인"""
        if not hasattr(user, self.field):
            return False, f"기믹 필드 '{self.field}'가 없습니다"

        current_value = getattr(user, self.field, 0)
        if current_value < self.amount:
            return False, f"{self.field} 부족 (필요: {self.amount}, 현재: {current_value})"

        return True, ""

    def consume(self, user: Any, context: Dict[str, Any]) -> bool:
        """기믹 수치 소모"""
        if not hasattr(user, self.field):
            return False

        current_value = getattr(user, self.field, 0)
        if current_value < self.amount:
            return False

        setattr(user, self.field, current_value - self.amount)
        return True

    def get_description(self, user: Any) -> str:
        """비용 설명"""
        return f"{self.field} -{self.amount}"
