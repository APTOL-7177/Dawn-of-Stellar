"""HP Cost - HP 비용 (광전사 등)"""
from src.character.skills.costs.base import SkillCost

class HPCost(SkillCost):
    """HP 비용"""
    def __init__(self, amount: int = 0, percentage: float = 0.0):
        super().__init__("hp")
        self.amount = amount
        self.percentage = percentage
    
    def can_afford(self, user, context):
        """HP 충분한지 확인 (최소 1 HP는 남겨야 함)"""
        required_hp = self._calculate_cost(user)
        if user.current_hp > required_hp:
            return True, ""
        return False, f"HP 부족 ({user.current_hp}/{required_hp})"
    
    def consume(self, user, context):
        """HP 소비"""
        cost = self._calculate_cost(user)
        if user.current_hp <= cost:
            return False
        user.take_damage(cost)
        # 소비한 HP를 context에 저장 (보호막 생성용)
        if context is not None:
            context['hp_consumed'] = cost
        return True
    
    def _calculate_cost(self, user):
        """비용 계산"""
        cost = self.amount
        if self.percentage > 0:
            cost += int(user.current_hp * self.percentage)
        return max(1, cost)
    
    def get_description(self, user):
        """비용 설명"""
        cost = self._calculate_cost(user)
        if self.percentage > 0:
            return f"HP {cost} ({int(self.percentage*100)}%)"
        return f"HP {cost}"
