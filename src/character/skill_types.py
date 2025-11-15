"""
Skill Types - 확장 가능한 스킬 타입 시스템

모든 스킬 타입은 플러그인 방식으로 추가 가능
"""

from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from abc import ABC, abstractmethod


class SkillCategory(Enum):
    """스킬 카테고리"""
    COMBAT = "combat"
    FIELD = "field"
    CRAFTING = "crafting"
    SOCIAL = "social"
    PASSIVE = "passive"


class SkillTargetType(Enum):
    """스킬 대상 타입"""
    SELF = "self"
    SINGLE_ALLY = "single_ally"
    SINGLE_ENEMY = "single_enemy"
    ALL_ALLIES = "all_allies"
    ALL_ENEMIES = "all_enemies"
    AREA = "area"
    FIELD_OBJECT = "field_object"


class SkillType(ABC):
    """
    스킬 타입 베이스 클래스

    모든 스킬 타입은 이 클래스를 상속받습니다.
    """

    def __init__(
        self,
        type_id: str,
        name: str,
        category: SkillCategory,
        target_type: SkillTargetType,
        description: str = ""
    ) -> None:
        self.type_id = type_id
        self.name = name
        self.category = category
        self.target_type = target_type
        self.description = description

    @abstractmethod
    def can_use(self, user: Any, context: Dict[str, Any]) -> bool:
        """
        스킬 사용 가능 여부

        Args:
            user: 사용자
            context: 컨텍스트 정보

        Returns:
            사용 가능 여부
        """
        pass

    @abstractmethod
    def execute(self, user: Any, target: Any, context: Dict[str, Any]) -> Any:
        """
        스킬 실행

        Args:
            user: 사용자
            target: 대상
            context: 컨텍스트

        Returns:
            실행 결과
        """
        pass

    def get_cost(self, user: Any) -> Dict[str, float]:
        """
        스킬 비용

        Returns:
            비용 딕셔너리 (예: {"mp": 20, "stamina": 10})
        """
        return {}

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "type_id": self.type_id,
            "name": self.name,
            "category": self.category.value,
            "target_type": self.target_type.value,
            "description": self.description
        }


# === 전투 스킬 타입 ===

class BrvAttackSkill(SkillType):
    """BRV 공격 스킬"""

    def __init__(self) -> None:
        super().__init__(
            type_id="brv_attack",
            name="BRV 공격",
            category=SkillCategory.COMBAT,
            target_type=SkillTargetType.SINGLE_ENEMY,
            description="적의 BRV를 축적하여 BREAK를 노리는 공격"
        )

    def can_use(self, user: Any, context: Dict[str, Any]) -> bool:
        mp_cost = context.get("mp_cost", 0)
        return user.mp >= mp_cost

    def execute(self, user: Any, target: Any, context: Dict[str, Any]) -> Any:
        # BRV 데미지 계산 로직
        return {"type": "brv_damage", "damage": 0}


class HpAttackSkill(SkillType):
    """HP 공격 스킬"""

    def __init__(self) -> None:
        super().__init__(
            type_id="hp_attack",
            name="HP 공격",
            category=SkillCategory.COMBAT,
            target_type=SkillTargetType.SINGLE_ENEMY,
            description="축적된 BRV를 소비하여 실제 HP 데미지를 가함"
        )

    def can_use(self, user: Any, context: Dict[str, Any]) -> bool:
        mp_cost = context.get("mp_cost", 0)
        return user.mp >= mp_cost and user.brv > 0

    def execute(self, user: Any, target: Any, context: Dict[str, Any]) -> Any:
        # HP 데미지 계산 로직
        return {"type": "hp_damage", "damage": 0}


class SupportSkill(SkillType):
    """지원 스킬"""

    def __init__(self) -> None:
        super().__init__(
            type_id="support",
            name="지원",
            category=SkillCategory.COMBAT,
            target_type=SkillTargetType.SINGLE_ALLY,
            description="아군을 강화하거나 회복하는 스킬"
        )

    def can_use(self, user: Any, context: Dict[str, Any]) -> bool:
        mp_cost = context.get("mp_cost", 0)
        return user.mp >= mp_cost

    def execute(self, user: Any, target: Any, context: Dict[str, Any]) -> Any:
        return {"type": "support", "effects": []}


# === 필드 스킬 타입 ===

class LockpickingSkill(SkillType):
    """자물쇠 해제 스킬"""

    def __init__(self) -> None:
        super().__init__(
            type_id="lockpicking",
            name="자물쇠 해제",
            category=SkillCategory.FIELD,
            target_type=SkillTargetType.FIELD_OBJECT,
            description="잠긴 문이나 상자를 연다"
        )

    def can_use(self, user: Any, context: Dict[str, Any]) -> bool:
        dexterity = getattr(user, "dexterity", 0)
        difficulty = context.get("difficulty", 1)
        return dexterity >= difficulty

    def execute(self, user: Any, target: Any, context: Dict[str, Any]) -> Any:
        import random
        dexterity = getattr(user, "dexterity", 0)
        difficulty = context.get("difficulty", 1)
        success_chance = 0.5 + (dexterity - difficulty) * 0.1

        return {
            "success": random.random() < success_chance,
            "difficulty": difficulty
        }


class DetectionSkill(SkillType):
    """탐지 스킬"""

    def __init__(self) -> None:
        super().__init__(
            type_id="detection",
            name="탐지",
            category=SkillCategory.FIELD,
            target_type=SkillTargetType.AREA,
            description="숨겨진 함정이나 비밀 문을 발견한다"
        )

    def can_use(self, user: Any, context: Dict[str, Any]) -> bool:
        stamina_cost = context.get("stamina_cost", 10)
        return getattr(user, "stamina", 0) >= stamina_cost

    def execute(self, user: Any, target: Any, context: Dict[str, Any]) -> Any:
        perception = getattr(user, "perception", 0)
        radius = 5 + perception // 2

        return {
            "radius": radius,
            "detected_objects": []
        }


class StealthSkill(SkillType):
    """은신 스킬"""

    def __init__(self) -> None:
        super().__init__(
            type_id="stealth",
            name="은신",
            category=SkillCategory.FIELD,
            target_type=SkillTargetType.SELF,
            description="적의 탐지를 피해 은신한다"
        )

    def can_use(self, user: Any, context: Dict[str, Any]) -> bool:
        stamina_cost = context.get("stamina_cost", 15)
        return getattr(user, "stamina", 0) >= stamina_cost

    def execute(self, user: Any, target: Any, context: Dict[str, Any]) -> Any:
        speed = getattr(user, "speed", 0)
        duration = 3 + speed // 5

        return {
            "duration": duration,
            "detection_reduction": 0.5
        }


# === 크래프팅 스킬 타입 ===

class CookingSkill(SkillType):
    """요리 스킬"""

    def __init__(self) -> None:
        super().__init__(
            type_id="cooking",
            name="요리",
            category=SkillCategory.CRAFTING,
            target_type=SkillTargetType.SELF,
            description="재료를 사용하여 음식을 만든다"
        )

    def can_use(self, user: Any, context: Dict[str, Any]) -> bool:
        stamina_cost = context.get("stamina_cost", 15)
        has_ingredients = context.get("has_ingredients", False)
        return getattr(user, "stamina", 0) >= stamina_cost and has_ingredients

    def execute(self, user: Any, target: Any, context: Dict[str, Any]) -> Any:
        import random
        dexterity = getattr(user, "dexterity", 0)

        # 요리 품질 결정
        quality_roll = random.random() + dexterity * 0.05

        if quality_roll >= 0.9:
            quality = "excellent"
        elif quality_roll >= 0.7:
            quality = "good"
        elif quality_roll >= 0.4:
            quality = "normal"
        else:
            quality = "poor"

        return {
            "quality": quality,
            "item": context.get("recipe")
        }


class GatheringSkill(SkillType):
    """채집 스킬"""

    def __init__(self) -> None:
        super().__init__(
            type_id="gathering",
            name="채집",
            category=SkillCategory.CRAFTING,
            target_type=SkillTargetType.FIELD_OBJECT,
            description="자원을 채집한다"
        )

    def can_use(self, user: Any, context: Dict[str, Any]) -> bool:
        stamina_cost = context.get("stamina_cost", 10)
        return getattr(user, "stamina", 0) >= stamina_cost

    def execute(self, user: Any, target: Any, context: Dict[str, Any]) -> Any:
        import random
        dexterity = getattr(user, "dexterity", 0)

        success_chance = 0.7 + dexterity * 0.02
        success = random.random() < success_chance

        if success:
            yield_amount = random.randint(1, 1 + dexterity // 5)
        else:
            yield_amount = 0

        return {
            "success": success,
            "yield": yield_amount,
            "resource": context.get("resource_type")
        }


# === 스킬 타입 레지스트리 ===

class SkillTypeRegistry:
    """
    스킬 타입 레지스트리

    모든 스킬 타입을 등록하고 관리하는 싱글톤
    """

    _instance = None
    _skill_types: Dict[str, SkillType] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_default_types()
        return cls._instance

    def _initialize_default_types(self) -> None:
        """기본 스킬 타입 등록"""
        default_types = [
            # 전투
            BrvAttackSkill(),
            HpAttackSkill(),
            SupportSkill(),

            # 필드
            LockpickingSkill(),
            DetectionSkill(),
            StealthSkill(),

            # 크래프팅
            CookingSkill(),
            GatheringSkill(),
        ]

        for skill_type in default_types:
            self.register(skill_type)

    def register(self, skill_type: SkillType) -> None:
        """
        스킬 타입 등록

        Args:
            skill_type: 등록할 스킬 타입
        """
        self._skill_types[skill_type.type_id] = skill_type

    def get(self, type_id: str) -> Optional[SkillType]:
        """
        스킬 타입 가져오기

        Args:
            type_id: 스킬 타입 ID

        Returns:
            스킬 타입 (없으면 None)
        """
        return self._skill_types.get(type_id)

    def get_all(self) -> Dict[str, SkillType]:
        """모든 스킬 타입"""
        return self._skill_types.copy()

    def get_by_category(self, category: SkillCategory) -> List[SkillType]:
        """카테고리별 스킬 타입"""
        return [
            st for st in self._skill_types.values()
            if st.category == category
        ]


# 전역 레지스트리 인스턴스
skill_type_registry = SkillTypeRegistry()
