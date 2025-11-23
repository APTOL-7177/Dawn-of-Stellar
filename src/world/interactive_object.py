"""
상호작용 오브젝트 시스템 (Interactive Objects)

던전에 배치되는 상호작용 가능한 특수 오브젝트
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional, Callable
import random

from src.core.logger import get_logger

logger = get_logger("dungeon_events")


class InteractiveObjectType(Enum):
    """상호작용 오브젝트 타입"""
    HEALING_FOUNTAIN = "healing_fountain"    # 치유의 샘
    CURSED_ALTAR = "cursed_altar"            # 저주받은 제단
    GAMBLERS_TABLE = "gamblers_table"        # 도박사의 테이블
    LOCKED_CHEST = "locked_chest"            # 잠긴 상자
    MYSTERY_STATUE = "mystery_statue"        # 신비한 석상
    MERCHANT = "merchant"                    # 상인
    SHRINE_OF_STRENGTH = "shrine_of_strength"  # 힘의 성소
    SHRINE_OF_WISDOM = "shrine_of_wisdom"      # 지혜의 성소
    ANCIENT_PORTAL = "ancient_portal"          # 고대 포탈
    WISHING_WELL = "wishing_well"              # 소원의 우물


@dataclass
class InteractiveObject:
    """상호작용 가능한 오브젝트"""
    object_type: InteractiveObjectType
    x: int
    y: int
    used: bool = False  # 사용 여부
    metadata: Dict[str, Any] = None  # 추가 데이터
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def symbol(self) -> str:
        """맵 심볼"""
        symbols = {
            InteractiveObjectType.HEALING_FOUNTAIN: "F",
            InteractiveObjectType.CURSED_ALTAR: "A",
            InteractiveObjectType.GAMBLERS_TABLE: "G",
            InteractiveObjectType.LOCKED_CHEST: "C",
            InteractiveObjectType.MYSTERY_STATUE: "S",
            InteractiveObjectType.MERCHANT: "M",
            InteractiveObjectType.SHRINE_OF_STRENGTH: "Σ",
            InteractiveObjectType.SHRINE_OF_WISDOM: "Ω",
            InteractiveObjectType.ANCIENT_PORTAL: "P",
            InteractiveObjectType.WISHING_WELL: "W"
        }
        return symbols.get(self.object_type, "?")
    
    @property
    def color(self) -> tuple:
        """오브젝트 색상 (RGB)"""
        colors = {
            InteractiveObjectType.HEALING_FOUNTAIN: (100, 200, 255),  # 파란색
            InteractiveObjectType.CURSED_ALTAR: (150, 50, 150),       # 보라색
            InteractiveObjectType.GAMBLERS_TABLE: (255, 215, 0),      # 금색
            InteractiveObjectType.LOCKED_CHEST: (139, 69, 19),        # 갈색
            InteractiveObjectType.MYSTERY_STATUE: (180, 180, 180),    # 회색
            InteractiveObjectType.MERCHANT: (255, 165, 0),            # 주황색
            InteractiveObjectType.SHRINE_OF_STRENGTH: (255, 100, 100),  # 빨강
            InteractiveObjectType.SHRINE_OF_WISDOM: (100, 100, 255),    # 파랑
            InteractiveObjectType.ANCIENT_PORTAL: (200, 50, 200),       # 보라
            InteractiveObjectType.WISHING_WELL: (100, 255, 255)         # 청록
        }
        return colors.get(self.object_type, (255, 255, 255))
    
    @property
    def name(self) -> str:
        """오브젝트 이름"""
        names = {
            InteractiveObjectType.HEALING_FOUNTAIN: "치유의 샘",
            InteractiveObjectType.CURSED_ALTAR: "저주받은 제단",
            InteractiveObjectType.GAMBLERS_TABLE: "도박사의 테이블",
            InteractiveObjectType.LOCKED_CHEST: "잠긴 상자",
            InteractiveObjectType.MYSTERY_STATUE: "신비한 석상",
            InteractiveObjectType.MERCHANT: "떠돌이 상인",
            InteractiveObjectType.SHRINE_OF_STRENGTH: "힘의 성소",
            InteractiveObjectType.SHRINE_OF_WISDOM: "지혜의 성소",
            InteractiveObjectType.ANCIENT_PORTAL: "고대 포탈",
            InteractiveObjectType.WISHING_WELL: "소원의 우물"
        }
        return names.get(self.object_type, "알 수 없는 오브젝트")


class InteractionHandler:
    """상호작용 처리기"""
    
    @staticmethod
    def interact(obj: InteractiveObject, player: Any) -> Dict[str, Any]:
        """
        오브젝트와 상호작용
        
        Args:
            obj: 상호작용할 오브젝트
            player: 플레이어 객체
            
        Returns:
            결과 딕셔너리 {success: bool, message: str, effects: dict}
        """
        if obj.used:
            return {
                "success": False,
                "message": f"{obj.name}은(는) 이미 사용되었습니다.",
                "effects": {}
            }
        
        # 타입별 처리
        handler = {
            InteractiveObjectType.HEALING_FOUNTAIN: InteractionHandler._healing_fountain,
            InteractiveObjectType.CURSED_ALTAR: InteractionHandler._cursed_altar,
            InteractiveObjectType.GAMBLERS_TABLE: InteractionHandler._gamblers_table,
            InteractiveObjectType.LOCKED_CHEST: InteractionHandler._locked_chest,
            InteractiveObjectType.MYSTERY_STATUE: InteractionHandler._mystery_statue,
            InteractiveObjectType.SHRINE_OF_STRENGTH: InteractionHandler._shrine_of_strength,
            InteractiveObjectType.SHRINE_OF_WISDOM: InteractionHandler._shrine_of_wisdom,
            InteractiveObjectType.WISHING_WELL: InteractionHandler._wishing_well,
        }.get(obj.object_type)
        
        if handler:
            result = handler(obj, player)
            if result.get("success"):
                obj.used = True
            return result
        
        return {
            "success": False,
            "message": "상호작용할 수 없습니다.",
            "effects": {}
        }
    
    @staticmethod
    def _healing_fountain(obj: InteractiveObject, player: Any) -> Dict[str, Any]:
        """치유의 샘"""
        hp_restore = int(player.max_hp * 0.5)
        mp_restore = int(player.max_mp * 0.5)
        
        player.heal(hp_restore)
        player.current_mp = min(player.current_mp + mp_restore, player.max_mp)
        
        return {
            "success": True,
            "message": f"샘물이 당신의 상처를 치유합니다. HP {hp_restore}, MP {mp_restore} 회복!",
            "effects": {"hp_restored": hp_restore, "mp_restored": mp_restore}
        }
    
    @staticmethod
    def _cursed_altar(obj: InteractiveObject, player: Any) -> Dict[str, Any]:
        """저주받은 제단 - HP 20% 희생으로 영구 스탯 부스트"""
        cost = int(player.max_hp * 0.2)
        
        if player.current_hp <= cost:
            return {
                "success": False,
                "message": "HP가 부족하여 제단을 사용할 수 없습니다.",
                "effects": {}
            }
        
        # HP 희생
        player.current_hp -= cost
        
        # 랜덤 스탯 증가
        stat_choice = random.choice(["strength", "defense", "magic", "speed"])
        bonus = random.randint(3, 8)
        
        if hasattr(player, 'stat_manager'):
            player.stat_manager.add_bonus(stat_choice, "cursed_altar", bonus)
        
        return {
            "success": True,
            "message": f"어둠의 힘이 당신을 강화합니다! {stat_choice.upper()} +{bonus} (영구)",
            "effects": {"hp_cost": cost, "stat_boost": {stat_choice: bonus}}
        }
    
    @staticmethod
    def _gamblers_table(obj: InteractiveObject, player: Any) -> Dict[str, Any]:
        """도박사의 테이블"""
        cost = 100
        
        if player.gold < cost:
            return {
                "success": False,
                "message": f"골드가 부족합니다. (필요: {cost} Gold)",
                "effects": {}
            }
        
        player.gold -= cost
        
        # 확률: 50% 꽝, 30% 소형, 15% 중형, 5% 대박
        roll = random.randint(1, 100)
        
        if roll <= 50:
            return {
                "success": True,
                "message": "꽝! 아무것도 얻지 못했습니다.",
                "effects": {"gold_spent": cost, "reward": None}
            }
        elif roll <= 80:
            # 소형 보상: 골드 100-200
            reward_gold = random.randint(100, 200)
            player.gold += reward_gold
            return {
                "success": True,
                "message": f"골드 {reward_gold}를 얻었습니다!",
                "effects": {"gold_spent": cost, "reward_gold": reward_gold}
            }
        elif roll <= 95:
            # 중형 보상: 포션
            return {
                "success": True,
                "message": "대형 체력 포션을 얻었습니다!",
                "effects": {"gold_spent": cost, "reward_item": "greater_health_potion"}
            }
        else:
            # 대박: 희귀 아이템
            return {
                "success": True,
                "message": "대박! 별가루를 얻었습니다!",
                "effects": {"gold_spent": cost, "reward_item": "stardust"}
            }
    
    @staticmethod
    def _locked_chest(obj: InteractiveObject, player: Any) -> Dict[str, Any]:
        """잠긴 상자 - 힘 체크 또는 열쇠 필요"""
        # 열쇠 확인
        if player.inventory.get("key", 0) > 0:
            player.remove_item("key", 1)
            return InteractionHandler._open_chest(obj, player, bypass=True)
        
        # 힘 체크 (힘 스탯 30 이상)
        strength = player.stat_manager.get_stat("strength").total_value if hasattr(player, 'stat_manager') else 20
        
        if strength >= 30:
            return InteractionHandler._open_chest(obj, player, bypass=False)
        else:
            return {
                "success": False,
                "message": f"상자가 너무 단단합니다. 힘이 더 필요합니다. (현재: {strength}, 필요: 30)",
                "effects": {}
            }
    
    @staticmethod
    def _open_chest(obj: InteractiveObject, player: Any, bypass: bool) -> Dict[str, Any]:
        """상자 열기"""
        # 랜덤 보상
        rewards = []
        
        # 골드
        gold = random.randint(200, 500)
        player.gold += gold
        rewards.append(f"골드 {gold}")
        
        # 희귀 재료
        rare_materials = ["mithril_ore", "crystal_shard", "ether", "stardust"]
        material = random.choice(rare_materials)
        from src.gathering.ingredient import IngredientDatabase
        item = IngredientDatabase.get_ingredient(material)
        if item:
            player.add_item(item)
            rewards.append(item.name)
        
        message = f"상자를 열었습니다! {', '.join(rewards)}를 얻었습니다!"
        if bypass:
            message = "[열쇠 사용] " + message
        
        return {
            "success": True,
            "message": message,
            "effects": {"rewards": rewards}
        }
    
    @staticmethod
    def _mystery_statue(obj: InteractiveObject, player: Any) -> Dict[str, Any]:
        """신비한 석상 - 랜덤 버프/디버프"""
        # 70% 버프, 30% 디버프
        is_buff = random.random() < 0.7
        
        if is_buff:
            buff_type = random.choice(["strength", "defense", "speed", "luck"])
            bonus = random.randint(10, 20)
            duration = 30
            
            return {
                "success": True,
                "message": f"석상이 축복을 내립니다! {buff_type.upper()} +{bonus} (30턴)",
                "effects": {"buff": buff_type, "value": bonus, "duration": duration}
            }
        else:
            debuff_type = random.choice(["strength", "defense", "speed"])
            penalty = random.randint(5, 15)
            duration = 20
            
            return {
                "success": True,
                "message": f"석상이 저주를 내립니다... {debuff_type.upper()} -{penalty} (20턴)",
                "effects": {"debuff": debuff_type, "value": -penalty, "duration": duration}
            }
    
    @staticmethod
    def _shrine_of_strength(obj: InteractiveObject, player: Any) -> Dict[str, Any]:
        """힘의 성소"""
        if hasattr(player, 'stat_manager'):
            player.stat_manager.add_bonus("strength", "shrine_strength", 15)
        
        return {
            "success": True,
            "message": "힘의 성소가 당신을 강화합니다! 힘 +15 (영구)",
            "effects": {"strength_bonus": 15}
        }
    
    @staticmethod
    def _shrine_of_wisdom(obj: InteractiveObject, player: Any) -> Dict[str, Any]:
        """지혜의 성소"""
        if hasattr(player, 'stat_manager'):
            player.stat_manager.add_bonus("magic", "shrine_wisdom", 15)
        
        return {
            "success": True,
            "message": "지혜의 성소가 당신의 지성을 깨웁니다! 마력 +15 (영구)",
            "effects": {"magic_bonus": 15}
        }
    
    @staticmethod
    def _wishing_well(obj: InteractiveObject, player: Any) -> Dict[str, Any]:
        """소원의 우물"""
        cost = 50
        
        if player.gold < cost:
            return {
                "success": False,
                "message": f"골드가 부족합니다. (필요: {cost} Gold)",
                "effects": {}
            }
        
        player.gold -= cost
        
        # 랜덤 소원 효과
        wishes = [
            ("HP/MP 완전 회복", lambda p: (p.heal(p.max_hp), setattr(p, 'current_mp', p.max_mp))),
            ("경험치 +200", lambda p: setattr(p, 'experience', p.experience + 200)),
            ("모든 스탯 +5 (30턴)", lambda p: None),  # 버프 효과
            ("희귀 아이템", lambda p: None),  # 아이템 드롭
        ]
        
        wish_name, wish_effect = random.choice(wishes)
        
        if wish_effect:
            wish_effect(player)
        
        return {
            "success": True,
            "message": f"우물이 소원을 들어줍니다! {wish_name}",
            "effects": {"wish": wish_name}
        }


class InteractiveObjectGenerator:
    """상호작용 오브젝트 생성기"""
    
    @staticmethod
    def generate_for_floor(floor_number: int, count: int = 2) -> list:
        """
        층별 오브젝트 생성
        
        Args:
            floor_number: 던전 층
            count: 생성할 개수
            
        Returns:
            오브젝트 리스트
        """
        objects = []
        
        # 층에 따른 타입 가중치
        if floor_number <= 3:
            # 초반: 치유, 상자 위주
            types_weights = [
                (InteractiveObjectType.HEALING_FOUNTAIN, 40),
                (InteractiveObjectType.LOCKED_CHEST, 30),
                (InteractiveObjectType.MYSTERY_STATUE, 20),
                (InteractiveObjectType.WISHING_WELL, 10),
            ]
        elif floor_number <= 7:
            # 중반: 다양한 타입
            types_weights = [
                (InteractiveObjectType.GAMBLERS_TABLE, 25),
                (InteractiveObjectType.LOCKED_CHEST, 25),
                (InteractiveObjectType.MYSTERY_STATUE, 20),
                (InteractiveObjectType.HEALING_FOUNTAIN, 15),
                (InteractiveObjectType.SHRINE_OF_STRENGTH, 10),
                (InteractiveObjectType.SHRINE_OF_WISDOM, 5),
            ]
        else:
            # 후반: 고급 오브젝트
            types_weights = [
                (InteractiveObjectType.CURSED_ALTAR, 30),
                (InteractiveObjectType.SHRINE_OF_STRENGTH, 20),
                (InteractiveObjectType.SHRINE_OF_WISDOM, 20),
                (InteractiveObjectType.LOCKED_CHEST, 15),
                (InteractiveObjectType.ANCIENT_PORTAL, 10),
                (InteractiveObjectType.GAMBLERS_TABLE, 5),
            ]
        
        # 가중치 기반 랜덤 선택
        types = [t for t, w in types_weights]
        weights = [w for t, w in types_weights]
        
        for _ in range(count):
            obj_type = random.choices(types, weights=weights)[0]
            obj = InteractiveObject(
                object_type=obj_type,
                x=0,
                y=0
            )
            objects.append(obj)
        
        return objects
