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


# === 직업 전용 필드 스킬 ===

class CardFortuneSkill(SkillType):
    """마술사 전용 - 카드 포춘 (카드 점술)"""

    def __init__(self) -> None:
        super().__init__(
            type_id="card_fortune",
            name="카드 포춘",
            category=SkillCategory.FIELD,
            target_type=SkillTargetType.AREA,
            description="트럼프 카드를 뽑아 운명을 점친다. 카드에 따라 다양한 필드 효과 발동!"
        )
        
        # 카드별 효과 정의
        self.rank_effects = {
            "A": {"type": "treasure", "desc": "에이스! 숨겨진 보물 발견", "bonus": 1.5},
            "K": {"type": "buff", "desc": "왕의 가호! 다음 전투 공격력 +30%", "value": 0.3},
            "Q": {"type": "heal", "desc": "여왕의 은총! 파티 HP 20% 회복", "value": 0.2},
            "J": {"type": "preemptive", "desc": "기사의 선봉! 다음 전투 선제공격 확정", "value": 1.0},
            "10": {"type": "gold", "desc": "대박! 골드 50% 추가 획득", "value": 0.5},
            "9": {"type": "exp", "desc": "성장! 경험치 30% 추가 획득", "value": 0.3},
            "8": {"type": "detect", "desc": "무한의 눈! 숨겨진 문/함정 탐지", "radius": 10},
            "7": {"type": "lucky", "desc": "럭키 세븐! 모든 드롭률 2배", "value": 2.0},
            "6": {"type": "curse", "desc": "저주의 카드... 다음 전투 받는 피해 +20%", "value": 0.2},
            "5": {"type": "trap", "desc": "함정 발동! 파티 HP 10% 피해", "value": 0.1},
            "4": {"type": "debuff", "desc": "불안정... 다음 전투 명중률 -20%", "value": 0.2},
            "3": {"type": "encounter", "desc": "조우! 근처 적이 접근 중", "value": 1},
            "2": {"type": "bad_luck", "desc": "최악의 패... 다음 전투 크리티컬 불가", "value": 0},
        }
        
        self.suit_bonuses = {
            "heart": {"element": "light", "bonus_type": "heal", "desc": "♥ 하트: 회복 효과 +50%"},
            "diamond": {"element": "earth", "bonus_type": "gold", "desc": "♦ 다이아: 골드 보너스 +50%"},
            "spade": {"element": "dark", "bonus_type": "damage", "desc": "♠ 스페이드: 전투 피해 +20%"},
            "club": {"element": "poison", "bonus_type": "debuff", "desc": "♣ 클로버: 디버프 효과 강화"},
        }
        
        self.joker_effects = {
            "joker_black": {"type": "chaos", "desc": "🃏 블랙 조커! 모든 효과 랜덤 2배 또는 역효과!"},
            "joker_red": {"type": "miracle", "desc": "🃏 레드 조커! 기적 발동! 최고의 행운!"},
        }

    def can_use(self, user: Any, context: Dict[str, Any]) -> bool:
        # 마술사만 사용 가능
        job_name = getattr(user, "job_name", getattr(user, "class_name", ""))
        if job_name != "마술사":
            return False
        
        # 트릭 덱이 있어야 함
        deck = getattr(user, "card_deck", None)
        if deck is None or len(deck) == 0:
            return False
        
        # MP 비용 (15)
        mp_cost = context.get("mp_cost", 15)
        current_mp = getattr(user, "current_mp", getattr(user, "mp", 0))
        return current_mp >= mp_cost

    def get_cost(self, user: Any) -> Dict[str, float]:
        return {"mp": 15}

    def execute(self, user: Any, target: Any, context: Dict[str, Any]) -> Any:
        import random
        
        # MP 소모
        mp_cost = 15
        if hasattr(user, "current_mp"):
            user.current_mp = max(0, user.current_mp - mp_cost)
        
        # 덱에서 카드 뽑기
        deck = getattr(user, "card_deck", [])
        discard = getattr(user, "card_discard", [])
        
        if not deck:
            # 덱이 비었으면 버린 카드에서 셔플
            if discard:
                random.shuffle(discard)
                deck = discard
                user.card_discard = []
                user.card_deck = deck
            else:
                return {"success": False, "message": "덱에 카드가 없습니다!"}
        
        # 카드 1장 뽑기
        drawn_card = deck.pop(0)
        user.card_deck = deck
        
        # 사용한 카드는 버림 더미로
        discard.append(drawn_card)
        user.card_discard = discard
        
        # 카드 정보 추출
        is_joker = drawn_card.get("is_joker", False)
        rank = drawn_card.get("rank", "")
        suit = drawn_card.get("suit", "")
        
        result = {
            "success": True,
            "card": drawn_card,
            "effects": []
        }
        
        # 조커 처리
        if is_joker:
            joker_effect = self.joker_effects.get(rank, self.joker_effects["joker_red"])
            result["main_effect"] = joker_effect
            
            if rank == "joker_red":
                # 레드 조커: 최고의 효과들
                result["effects"] = [
                    {"type": "treasure", "desc": "숨겨진 보물 발견!", "bonus": 2.0},
                    {"type": "heal", "desc": "파티 HP 50% 회복!", "value": 0.5},
                    {"type": "preemptive", "desc": "다음 전투 선제공격!", "value": 1.0},
                ]
            else:
                # 블랙 조커: 50% 확률로 대박 또는 쪽박
                if random.random() < 0.5:
                    result["effects"] = [
                        {"type": "treasure", "desc": "혼돈 속 행운! 보물 3배!", "bonus": 3.0},
                    ]
                else:
                    result["effects"] = [
                        {"type": "trap", "desc": "혼돈의 저주! 파티 HP 30% 피해!", "value": 0.3},
                        {"type": "encounter", "desc": "강력한 적 출현!", "value": 2},
                    ]
        else:
            # 일반 카드 처리
            rank_effect = self.rank_effects.get(rank, {"type": "none", "desc": "효과 없음"})
            suit_bonus = self.suit_bonuses.get(suit, {})
            
            result["main_effect"] = rank_effect
            result["suit_bonus"] = suit_bonus
            result["effects"].append(rank_effect)
            
            # 무늬 보너스 적용
            if suit_bonus:
                bonus_type = suit_bonus.get("bonus_type", "")
                if bonus_type == rank_effect.get("type"):
                    # 무늬와 효과 타입이 일치하면 강화
                    enhanced = rank_effect.copy()
                    if "value" in enhanced:
                        enhanced["value"] = enhanced["value"] * 1.5
                    if "bonus" in enhanced:
                        enhanced["bonus"] = enhanced["bonus"] * 1.5
                    enhanced["desc"] = f"[강화!] {enhanced['desc']}"
                    result["effects"][-1] = enhanced
        
        # 카드 이름 생성
        if is_joker:
            card_name = "🃏 조커"
        else:
            suit_symbols = {"spade": "♠", "heart": "♥", "diamond": "♦", "club": "♣"}
            card_name = f"{suit_symbols.get(suit, '?')}{rank}"
        
        result["card_name"] = card_name
        result["message"] = f"[카드 포춘] {card_name} - {result['main_effect']['desc']}"
        
        return result


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
            CardFortuneSkill(),  # 마술사 전용

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
