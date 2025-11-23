"""
환경 효과 시스템 (Environmental Effects)

던전의 특정 구역에 적용되는 환경 효과
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Set
import random

from src.core.logger import get_logger

logger = get_logger("dungeon_events")


class EnvironmentalEffectType(Enum):
    """환경 효과 타입"""
    POISON_SWAMP = "poison_swamp"      # 독 늪
    DENSE_FOG = "dense_fog"            # 짙은 안개
    DARKNESS = "darkness"              # 어둠
    HOLY_GROUND = "holy_ground"        # 신성한 땅
    BURNING_FLOOR = "burning_floor"    # 불타는 바닥
    ICY_TERRAIN = "icy_terrain"        # 얼음 지형
    CURSED_ZONE = "cursed_zone"        # 저주받은 구역
    BLESSED_SANCTUARY = "blessed_sanctuary"  # 축복받은 성역


@dataclass
class EnvironmentalEffect:
    """환경 효과"""
    effect_type: EnvironmentalEffectType
    intensity: float = 1.0  # 강도 (0.5 ~ 2.0)
    affected_tiles: Set[tuple] = None  # (x, y) 좌표 집합
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.affected_tiles is None:
            self.affected_tiles = set()
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def name(self) -> str:
        """효과 이름"""
        names = {
            EnvironmentalEffectType.POISON_SWAMP: "독 늪",
            EnvironmentalEffectType.DENSE_FOG: "짙은 안개",
            EnvironmentalEffectType.DARKNESS: "어둠",
            EnvironmentalEffectType.HOLY_GROUND: "신성한 땅",
            EnvironmentalEffectType.BURNING_FLOOR: "불타는 바닥",
            EnvironmentalEffectType.ICY_TERRAIN: "얼음 지형",
            EnvironmentalEffectType.CURSED_ZONE: "저주받은 구역",
            EnvironmentalEffectType.BLESSED_SANCTUARY: "축복받은 성역"
        }
        return names.get(self.effect_type, "알 수 없는 효과")
    
    @property
    def description(self) -> str:
        """효과 설명"""
        descriptions = {
            EnvironmentalEffectType.POISON_SWAMP: "걸을 때마다 HP가 서서히 감소합니다.",
            EnvironmentalEffectType.DENSE_FOG: "시야가 크게 감소합니다.",
            EnvironmentalEffectType.DARKNESS: "시야가 1칸으로 제한됩니다.",
            EnvironmentalEffectType.HOLY_GROUND: "HP 재생이 증가하지만 공격력이 감소합니다.",
            EnvironmentalEffectType.BURNING_FLOOR: "매 턴 화상 데미지를 입습니다.",
            EnvironmentalEffectType.ICY_TERRAIN: "이동 속도가 감소합니다.",
            EnvironmentalEffectType.CURSED_ZONE: "모든 능력치가 감소합니다.",
            EnvironmentalEffectType.BLESSED_SANCTUARY: "모든 능력치가 증가합니다.",
            EnvironmentalEffectType.ELECTRIC_FIELD: "매 턴 감전 데미지. 공격 속도 증가.",
            EnvironmentalEffectType.GRAVITY_ANOMALY: "이동력 감소, 방어력 증가.",
            EnvironmentalEffectType.WINDSTORM: "강풍으로 회피율 증가, 명중률 감소.",
            EnvironmentalEffectType.RADIATION_ZONE: "매 턴 데미지 + 최대 HP 감소.",
            EnvironmentalEffectType.MANA_VORTEX: "마력 및 MP 회복량 증가.",
            EnvironmentalEffectType.BLOOD_MOON: "공격력 증가, 피해 증가.",
            EnvironmentalEffectType.HALLOWED_LIGHT: "언데드 약화, 모든 스탯 증가."
        }
        return descriptions.get(self.effect_type, "")


class EnvironmentalEffectManager:
    """환경 효과 관리자"""
    
    def __init__(self):
        self.active_effects: Dict[EnvironmentalEffectType, EnvironmentalEffect] = {}
    
    def add_effect(self, effect: EnvironmentalEffect):
        """효과 추가"""
        self.active_effects[effect.effect_type] = effect
        logger.info(f"환경 효과 추가: {effect.name}")
    
    def remove_effect(self, effect_type: EnvironmentalEffectType):
        """효과 제거"""
        if effect_type in self.active_effects:
            del self.active_effects[effect_type]
            logger.info(f"환경 효과 제거: {effect_type.value}")
    
    def is_tile_affected(self, x: int, y: int, effect_type: EnvironmentalEffectType) -> bool:
        """특정 타일이 효과 영향을 받는지 확인"""
        effect = self.active_effects.get(effect_type)
        if not effect:
            return False
        return (x, y) in effect.affected_tiles
    
    def get_effects_at_tile(self, x: int, y: int) -> list:
        """특정 타일의 모든 효과 가져오기"""
        effects = []
        for effect in self.active_effects.values():
            if (x, y) in effect.affected_tiles:
                effects.append(effect)
        return effects
    
    def apply_tile_effects(self, player: Any, x: int, y: int) -> list:
        """
        타일의 모든 효과 적용
        
        Args:
            player: 플레이어 객체
            x, y: 타일 좌표
            
        Returns:
            적용된 효과 메시지 리스트
        """
        effects = self.get_effects_at_tile(x, y)
        messages = []
        
        for effect in effects:
            message = self._apply_effect(effect, player)
            if message:
                messages.append(message)
        
        return messages
    
    def _apply_effect(self, effect: EnvironmentalEffect, player: Any) -> str:
        """개별 효과 적용"""
        if effect.effect_type == EnvironmentalEffectType.POISON_SWAMP:
            damage = int(player.max_hp * 0.02 * effect.intensity)  # 2% HP 감소
            player.current_hp = max(1, player.current_hp - damage)
            return f"독 늪이 당신을 침식합니다! ({damage} 데미지)"
        
        elif effect.effect_type == EnvironmentalEffectType.BURNING_FLOOR:
            damage = int(15 * effect.intensity)
            player.current_hp = max(1, player.current_hp - damage)
            return f"불타는 바닥! ({damage} 화상 데미지)"
        
        elif effect.effect_type == EnvironmentalEffectType.HOLY_GROUND:
            heal = int(player.max_hp * 0.03 * effect.intensity)  # 3% HP 회복
            player.heal(heal)
            return f"신성한 땅이 당신을 치유합니다. (+{heal} HP)"
        
        elif effect.effect_type == EnvironmentalEffectType.CURSED_ZONE:
            return "저주받은 기운이 당신을 약화시킵니다..."
        
        elif effect.effect_type == EnvironmentalEffectType.BLESSED_SANCTUARY:
            return "축복받은 성역이 당신을 강화합니다!"
        
        return None
    
    def get_vision_modifier(self, player: Any, x: int, y: int) -> float:
        """
        시야 수정치 계산
        
        Returns:
            시야 배율 (0.5 = 50% 감소, 1.0 = 정상, 2.0 = 2배)
        """
        effects = self.get_effects_at_tile(x, y)
        modifier = 1.0
        
        for effect in effects:
            if effect.effect_type == EnvironmentalEffectType.DENSE_FOG:
                modifier *= 0.5  # 50% 감소
            elif effect.effect_type == EnvironmentalEffectType.DARKNESS:
                modifier *= 0.1  # 90% 감소 (거의 안 보임)
        
        return modifier
    
    def get_stat_modifiers(self, player: Any, x: int, y: int) -> Dict[str, float]:
        """
        스탯 수정치 계산 (퍼센트 기반)
        
        Returns:
            {stat_name: percent_modifier} (e.g., 0.1 = +10%, -0.15 = -15%)
        """
        effects = self.get_effects_at_tile(x, y)
        modifiers = {}
        
        for effect in effects:
            if effect.effect_type == EnvironmentalEffectType.HOLY_GROUND:
                modifiers["strength"] = modifiers.get("strength", 0.0) - 0.15  # -15%
                modifiers["defense"] = modifiers.get("defense", 0.0) + 0.10   # +10%
            
            elif effect.effect_type == EnvironmentalEffectType.ICY_TERRAIN:
                modifiers["speed"] = modifiers.get("speed", 0.0) - 0.25  # -25%
            
            elif effect.effect_type == EnvironmentalEffectType.CURSED_ZONE:
                for stat in ["strength", "defense", "magic", "speed"]:
                    modifiers[stat] = modifiers.get(stat, 0.0) - 0.20  # -20%
            
            elif effect.effect_type == EnvironmentalEffectType.BLESSED_SANCTUARY:
                for stat in ["strength", "defense", "magic", "speed"]:
                    modifiers[stat] = modifiers.get(stat, 0.0) + 0.15  # +15%
            
            elif effect.effect_type == EnvironmentalEffectType.ELECTRIC_FIELD:
                modifiers["speed"] = modifiers.get("speed", 0.0) + 0.20  # +20%
            
            elif effect.effect_type == EnvironmentalEffectType.GRAVITY_ANOMALY:
                modifiers["speed"] = modifiers.get("speed", 0.0) - 0.30  # -30%
                modifiers["defense"] = modifiers.get("defense", 0.0) + 0.20  # +20%
            
            elif effect.effect_type == EnvironmentalEffectType.WINDSTORM:
                modifiers["accuracy"] = modifiers.get("accuracy", 0.0) - 0.25  # -25%
                modifiers["evasion"] = modifiers.get("evasion", 0.0) + 0.15  # +15%
            
            elif effect.effect_type == EnvironmentalEffectType.MANA_VORTEX:
                modifiers["magic"] = modifiers.get("magic", 0.0) + 0.30  # +30%
            
            elif effect.effect_type == EnvironmentalEffectType.BLOOD_MOON:
                modifiers["strength"] = modifiers.get("strength", 0.0) + 0.25  # +25%
                modifiers["defense"] = modifiers.get("defense", 0.0) - 0.10  # -10%
            
            elif effect.effect_type == EnvironmentalEffectType.HALLOWED_LIGHT:
                for stat in ["strength", "defense", "magic", "speed"]:
                    modifiers[stat] = modifiers.get(stat, 0.0) + 0.10  # +10%
        
        return modifiers


class EnvironmentalEffectGenerator:
    """환경 효과 생성기"""
    
    @staticmethod
    def generate_for_floor(floor_number: int, map_width: int, map_height: int) -> list:
        """
        층별 환경 효과 생성
        
        Args:
            floor_number: 던전 층
            map_width: 맵 너비
            map_height: 맵 높이
            
        Returns:
            환경 효과 리스트
        """
        effects = []
        
        # 50% 확률로 환경 효과 없음
        if random.random() < 0.5:
            return effects
        
        # 층에 따른 효과 타입 선택
        if floor_number <= 3:
            effect_types = [
                EnvironmentalEffectType.DENSE_FOG,
                EnvironmentalEffectType.HOLY_GROUND,
            ]
        elif floor_number <= 7:
            effect_types = [
                EnvironmentalEffectType.POISON_SWAMP,
                EnvironmentalEffectType.DENSE_FOG,
                EnvironmentalEffectType.ICY_TERRAIN,
                EnvironmentalEffectType.BURNING_FLOOR,
            ]
        else:
            effect_types = [
                EnvironmentalEffectType.DARKNESS,
                EnvironmentalEffectType.CURSED_ZONE,
                EnvironmentalEffectType.BURNING_FLOOR,
                EnvironmentalEffectType.POISON_SWAMP,
            ]
        
        # 랜덤 효과 선택
        effect_type = random.choice(effect_types)
        
        # 효과가 적용될 타일 생성 (맵의 일부 영역)
        effect = EnvironmentalEffect(
            effect_type=effect_type,
            intensity=random.uniform(0.8, 1.5)
        )
        
        # 랜덤 영역에 효과 적용 (맵의 20-40%)
        num_tiles = int(map_width * map_height * random.uniform(0.2, 0.4))
        
        for _ in range(num_tiles):
            x = random.randint(1, map_width - 2)
            y = random.randint(1, map_height - 2)
            effect.affected_tiles.add((x, y))
        
        effects.append(effect)
        logger.info(f"환경 효과 생성: {effect.name} (영향 타일: {len(effect.affected_tiles)})")
        
        return effects
