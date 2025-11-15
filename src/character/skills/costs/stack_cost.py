"""Stack Cost"""
from src.character.skills.costs.base import SkillCost

class StackCost(SkillCost):
    """스택 비용"""
    def __init__(self, field: str, amount: int):
        super().__init__("stack")
        self.field = field
        self.amount = amount
    
    def can_afford(self, user, context):
        if not hasattr(user, self.field):
            return False, f"기믹 필드 없음: {self.field}"
        current = getattr(user, self.field, 0)
        if current >= self.amount:
            return True, ""
        return False, f"{self.field} 부족 ({current}/{self.amount})"
    
    def consume(self, user, context):
        if not hasattr(user, self.field):
            return False
        current = getattr(user, self.field, 0)
        if current < self.amount:
            return False
        setattr(user, self.field, current - self.amount)
        return True
    
    def get_description(self, user):
        return f"{self.field} {self.amount}"
