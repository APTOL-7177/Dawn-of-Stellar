"""Cost Base"""
from typing import Any, Dict, Tuple

class SkillCost:
    """비용 베이스"""
    def __init__(self, cost_type: str):
        self.cost_type = cost_type
    
    def can_afford(self, user, context) -> Tuple[bool, str]:
        return True, ""
    
    def consume(self, user, context) -> bool:
        return True
    
    def get_description(self, user) -> str:
        return self.cost_type
