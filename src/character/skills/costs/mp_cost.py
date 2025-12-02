"""MP Cost"""
from src.character.skills.costs.base import SkillCost

class MPCost(SkillCost):
    """MP 비용"""
    def __init__(self, amount: int):
        super().__init__("mp")
        self.amount = amount
    
    def _calculate_actual_cost(self, user, context):
        """특성 효과 + 난이도 배율을 적용한 실제 MP 비용 계산"""
        from src.character.trait_effects import get_trait_effect_manager

        # context에서 스킬 정보 가져오기
        skill = context.get('skill') if context else None

        # 기본 비용에 1.5배 적용
        base_cost = self.amount * 1.5

        # 난이도 배율 적용
        try:
            from src.core.difficulty import get_difficulty_system
            difficulty_system = get_difficulty_system()
            if difficulty_system:
                difficulty_mp_mult = difficulty_system.get_mp_cost_multiplier()
                base_cost *= difficulty_mp_mult
        except Exception:
            # 난이도 시스템을 로드할 수 없는 경우 기본값 사용
            pass

        # 특성 효과 적용
        trait_manager = get_trait_effect_manager()
        actual_cost = trait_manager.calculate_mp_cost(
            user,
            base_cost,
            skill=skill
        )
        return int(actual_cost)
    
    def can_afford(self, user, context):
        actual_cost = self._calculate_actual_cost(user, context or {})
        if user.current_mp >= actual_cost:
            return True, ""
        return False, f"MP 부족 ({user.current_mp}/{actual_cost})"

    def consume(self, user, context):
        # 실제 MP 소모는 combat_manager에서 처리하므로 여기서는 비용만 계산
        actual_cost = self._calculate_actual_cost(user, context or {})
        # 실제 소모는 combat_manager에서 처리되므로 여기서는 True만 반환
        return True
    
    def get_description(self, user, context=None):
        # 특성 효과를 적용한 비용 표시
        if context is None:
            context = {}
        actual_cost = self._calculate_actual_cost(user, context)
        if actual_cost != self.amount:
            return f"MP {actual_cost} (기본: {self.amount})"
        return f"MP {self.amount}"
