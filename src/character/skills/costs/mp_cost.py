"""MP Cost"""
from src.character.skills.costs.base import SkillCost

class MPCost(SkillCost):
    """MP 비용"""
    def __init__(self, amount: int):
        super().__init__("mp")
        self.amount = amount
    
    def _calculate_actual_cost(self, user, context):
        """특성 효과를 적용한 실제 MP 비용 계산"""
        from src.character.trait_effects import get_trait_effect_manager
        
        # context에서 스킬 정보 가져오기
        skill = context.get('skill') if context else None
        
        # 특성 효과 적용
        trait_manager = get_trait_effect_manager()
        actual_cost = trait_manager.calculate_mp_cost(
            user,
            self.amount,
            skill=skill
        )
        return actual_cost
    
    def can_afford(self, user, context):
        actual_cost = self._calculate_actual_cost(user, context or {})
        if user.current_mp >= actual_cost:
            return True, ""
        return False, f"MP 부족 ({user.current_mp}/{actual_cost})"
    
    def consume(self, user, context):
        actual_cost = self._calculate_actual_cost(user, context or {})
        return user.consume_mp(actual_cost)
    
    def get_description(self, user, context=None):
        # 특성 효과를 적용한 비용 표시
        if context is None:
            context = {}
        actual_cost = self._calculate_actual_cost(user, context)
        if actual_cost != self.amount:
            return f"MP {actual_cost} (기본: {self.amount})"
        return f"MP {self.amount}"
