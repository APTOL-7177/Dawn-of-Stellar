"""MP Cost"""
from src.character.skills.costs.base import SkillCost

class MPCost(SkillCost):
    """MP 비용"""
    def __init__(self, amount: int):
        super().__init__("mp")
        self.amount = amount
    
    def _calculate_actual_cost(self, user, context):
        """특성 효과 + 난이도 배율 + 레벨 스케일링을 적용한 실제 MP 비용 계산"""
        from src.character.trait_effects import get_trait_effect_manager

        # context에서 스킬 정보 가져오기
        skill = context.get('skill') if context else None
        metadata = getattr(skill, "metadata", {}) if skill else {}

        # 기본 비용에 1.5배 적용
        base_cost = self.amount * 1.5

        # 변형별 비용 오버라이드 (t_98b95a46): variants costs_override.mp가 있으면
        # 기본 비용을 대체한다 (레벨/과부하/난이도/특성 배율은 동일 적용).
        variant_cost = metadata.get("_variant_cost_override") if metadata else None
        if isinstance(variant_cost, dict) and variant_cost.get("mp") is not None:
            base_cost = variant_cost["mp"] * 1.5

        # 레벨당 5% MP 비용 증가 (레벨 1 = 100%, 레벨 2 = 105%, ..., 레벨 10 = 145%)
        if hasattr(user, 'level') and user.level > 1:
            level_multiplier = 1.0 + (user.level - 1) * 0.05
            base_cost *= level_multiplier

        # 과부하 선택 시 MP 배율 적용
        use_overload = None
        if context:
            # UI에서 강제 지정한 값 우선
            if 'force_overload' in context:
                use_overload = context.get('force_overload')
        if use_overload is None:
            use_overload = metadata.get("_use_overload")
        if use_overload is None:
            use_overload = metadata.get("overload_default", False)

        if use_overload and metadata.get("overload_capable"):
            overload_mult = metadata.get("overload_mp_multiplier", 2.0)
            base_cost *= overload_mult

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
        """MP 소모 실행"""
        from src.core.logger import get_logger
        logger = get_logger("mp_cost")

        actual_cost = self._calculate_actual_cost(user, context or {})

        # MP 차감
        if hasattr(user, 'current_mp'):
            old_mp = user.current_mp
            user.current_mp = max(0, user.current_mp - actual_cost)
            logger.info(f"[MP 소모] {user.name}: {old_mp} → {user.current_mp} (-{actual_cost})")
            return True
        else:
            logger.error(f"[MP 소모 실패] {user.name}에게 current_mp 속성이 없습니다")
            return False
    
    def get_description(self, user, context=None):
        # 특성 효과를 적용한 실제 비용만 표시
        if context is None:
            context = {}
        actual_cost = self._calculate_actual_cost(user, context)
        return f"MP {actual_cost}"
