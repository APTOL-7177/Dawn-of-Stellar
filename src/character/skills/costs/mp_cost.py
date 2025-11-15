"""MP Cost"""
from src.character.skills.costs.base import SkillCost

class MPCost(SkillCost):
    """MP 비용"""
    def __init__(self, amount: int):
        super().__init__("mp")
        self.amount = amount
    
    def can_afford(self, user, context):
        if user.current_mp >= self.amount:
            return True, ""
        return False, f"MP 부족 ({user.current_mp}/{self.amount})"
    
    def consume(self, user, context):
        return user.consume_mp(self.amount)
    
    def get_description(self, user):
        return f"MP {self.amount}"
