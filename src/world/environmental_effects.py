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
    ELECTRIC_FIELD = "electric_field"  # 전기장
    GRAVITY_ANOMALY = "gravity_anomaly"  # 중력 이상
    WINDSTORM = "windstorm"            # 강풍
    RADIATION_ZONE = "radiation_zone"  # 방사능 구역
    MANA_VORTEX = "mana_vortex"        # 마나 소용돌이
    BLOOD_MOON = "blood_moon"          # 피의 달
    HALLOWED_LIGHT = "hallowed_light"  # 신성한 빛


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
            EnvironmentalEffectType.BLESSED_SANCTUARY: "축복받은 성역",
            EnvironmentalEffectType.ELECTRIC_FIELD: "전기장",
            EnvironmentalEffectType.GRAVITY_ANOMALY: "중력 이상",
            EnvironmentalEffectType.WINDSTORM: "강풍",
            EnvironmentalEffectType.RADIATION_ZONE: "방사능 구역",
            EnvironmentalEffectType.MANA_VORTEX: "마나 소용돌이",
            EnvironmentalEffectType.BLOOD_MOON: "피의 달",
            EnvironmentalEffectType.HALLOWED_LIGHT: "신성한 빛"
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
    
    @property
    def color_overlay(self) -> tuple:
        """색상 오버레이 (RGB 튜플, 투명도 적용용)"""
        colors = {
            EnvironmentalEffectType.POISON_SWAMP: (50, 150, 50),      # 초록색
            EnvironmentalEffectType.DENSE_FOG: (100, 100, 100),       # 회색
            EnvironmentalEffectType.DARKNESS: (20, 20, 20),           # 거의 검은색
            EnvironmentalEffectType.HOLY_GROUND: (255, 255, 100),     # 황금색
            EnvironmentalEffectType.BURNING_FLOOR: (255, 100, 50),    # 주황빨강
            EnvironmentalEffectType.ICY_TERRAIN: (150, 200, 255),     # 하늘색
            EnvironmentalEffectType.CURSED_ZONE: (150, 50, 150),      # 보라색
            EnvironmentalEffectType.BLESSED_SANCTUARY: (200, 255, 200),  # 연한 초록
            EnvironmentalEffectType.ELECTRIC_FIELD: (200, 200, 255),  # 전기 파란색
            EnvironmentalEffectType.GRAVITY_ANOMALY: (100, 100, 150), # 진한 보라
            EnvironmentalEffectType.WINDSTORM: (200, 200, 150),       # 회황색
            EnvironmentalEffectType.RADIATION_ZONE: (150, 255, 100),  # 독성 초록
            EnvironmentalEffectType.MANA_VORTEX: (100, 150, 255),     # 마나 파란색
            EnvironmentalEffectType.BLOOD_MOON: (150, 0, 0),          # 진한 빨강
            EnvironmentalEffectType.HALLOWED_LIGHT: (255, 255, 200)   # 밝은 황금
        }
        return colors.get(self.effect_type, (128, 128, 128))


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
    
    def apply_tile_effects(self, player: Any, x: int, y: int, is_movement: bool = False) -> list:
        """
        타일의 모든 효과 적용
        
        Args:
            player: 플레이어 객체
            x, y: 타일 좌표
            is_movement: 이동 시 적용 여부 (True면 이동 시 데미지, False면 시간당/턴당 데미지)
            
        Returns:
            적용된 효과 메시지 리스트
        """
        effects = self.get_effects_at_tile(x, y)
        messages = []
        
        for effect in effects:
            message = self._apply_effect(effect, player, is_movement=is_movement)
            if message:
                messages.append(message)
        
        return messages
    
    def _apply_effect(self, effect: EnvironmentalEffect, player: Any, is_movement: bool = False) -> str:
        """
        개별 효과 적용
        
        Args:
            effect: 환경 효과
            player: 플레이어 객체
            is_movement: 이동 시 적용 여부 (True면 이동 시 데미지, False면 시간당 데미지/회복)
        """
        # === 시간당 지속 피해 효과 ===
        if effect.effect_type == EnvironmentalEffectType.POISON_SWAMP:
            # 독 늪: 시간당 피해
            if not is_movement:
                damage = int(player.max_hp * 0.02 * effect.intensity)  # 2% HP 감소
                player.current_hp = max(1, player.current_hp - damage)
                return f"독 늪이 당신을 침식합니다! ({damage} 데미지)"
            return None
        
        elif effect.effect_type == EnvironmentalEffectType.RADIATION_ZONE:
            # 방사능 구역: 시간당 피해
            if not is_movement:
                damage = int(12 * effect.intensity)
                player.current_hp = max(1, player.current_hp - damage)
                return f"방사능이 당신을 해칩니다! ({damage} 데미지)"
            return None
        
        elif effect.effect_type == EnvironmentalEffectType.CURSED_ZONE:
            # 저주받은 구역: 시간당 피해
            if not is_movement:
                damage = int(player.max_hp * 0.015 * effect.intensity)  # 1.5% HP 감소
                player.current_hp = max(1, player.current_hp - damage)
                return f"저주의 기운이 당신을 갉아먹습니다! ({damage} 데미지)"
            return "저주받은 기운이 당신을 약화시킵니다..."
        
        elif effect.effect_type == EnvironmentalEffectType.BLOOD_MOON:
            # 피의 달: 시간당 피해 (피의 저주)
            if not is_movement:
                damage = int(player.max_hp * 0.025 * effect.intensity)  # 2.5% HP 감소
                player.current_hp = max(1, player.current_hp - damage)
                return f"피의 달의 저주가 당신을 괴롭힙니다! ({damage} 데미지)"
            return "피의 달이 전투 본능을 자극합니다..."
        
        # === 이동 시 즉시 피해 효과 ===
        elif effect.effect_type == EnvironmentalEffectType.BURNING_FLOOR:
            # 불타는 바닥: 이동 시마다 데미지
            if is_movement:
                damage = int(15 * effect.intensity)
                player.current_hp = max(1, player.current_hp - damage)
                return f"불타는 바닥! ({damage} 화상 데미지)"
            return None
        
        elif effect.effect_type == EnvironmentalEffectType.ELECTRIC_FIELD:
            # 전기장: 이동 시마다 감전 데미지
            if is_movement:
                damage = int(10 * effect.intensity)
                player.current_hp = max(1, player.current_hp - damage)
                return f"전기장이 당신을 감전시킵니다! ({damage} 데미지)"
            return None
        
        # === 시간당 지속 회복 효과 ===
        elif effect.effect_type == EnvironmentalEffectType.HOLY_GROUND:
            # 신성한 땅: 시간당 회복
            if not is_movement:
                heal = int(player.max_hp * 0.03 * effect.intensity)  # 3% HP 회복
                if hasattr(player, 'heal'):
                    player.heal(heal)
                else:
                    player.current_hp = min(player.max_hp, player.current_hp + heal)
                return f"신성한 땅이 당신을 치유합니다. (+{heal} HP)"
            return None
        
        elif effect.effect_type == EnvironmentalEffectType.BLESSED_SANCTUARY:
            # 축복받은 성역: 시간당 회복
            if not is_movement:
                heal = int(player.max_hp * 0.04 * effect.intensity)  # 4% HP 회복
                if hasattr(player, 'heal'):
                    player.heal(heal)
                else:
                    player.current_hp = min(player.max_hp, player.current_hp + heal)
                return f"축복받은 성역이 당신을 회복시킵니다! (+{heal} HP)"
            return "축복받은 성역이 당신을 강화합니다!"
        
        elif effect.effect_type == EnvironmentalEffectType.HALLOWED_LIGHT:
            # 신성한 빛: 시간당 회복
            if not is_movement:
                heal = int(player.max_hp * 0.025 * effect.intensity)  # 2.5% HP 회복
                if hasattr(player, 'heal'):
                    player.heal(heal)
                else:
                    player.current_hp = min(player.max_hp, player.current_hp + heal)
                return f"신성한 빛이 당신을 치유합니다! (+{heal} HP)"
            return "신성한 빛이 당신을 보호합니다."
        
        elif effect.effect_type == EnvironmentalEffectType.MANA_VORTEX:
            # 마나 소용돌이: 시간당 MP 회복
            if not is_movement:
                if hasattr(player, 'current_mp') and hasattr(player, 'max_mp'):
                    mp_restore = int(player.max_mp * 0.05 * effect.intensity)  # 5% MP 회복
                    if hasattr(player, 'restore_mp'):
                        player.restore_mp(mp_restore)
                    else:
                        player.current_mp = min(player.max_mp, player.current_mp + mp_restore)
                    return f"마나 소용돌이가 마력을 회복시킵니다! (+{mp_restore} MP)"
            return "마나 소용돌이가 마력을 증폭시킵니다."
        
        # === 스탯 수정만 있는 효과 (피해/회복 없음) ===
        # DENSE_FOG, DARKNESS, ICY_TERRAIN, GRAVITY_ANOMALY, WINDSTORM 등은
        # 스탯 수정만 하므로 여기서는 None 반환
        
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
        층별 환경 효과 생성 (겹치지 않도록)
        
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
                EnvironmentalEffectType.BLESSED_SANCTUARY,
                EnvironmentalEffectType.MANA_VORTEX,
            ]
        elif floor_number <= 7:
            effect_types = [
                EnvironmentalEffectType.POISON_SWAMP,
                EnvironmentalEffectType.DENSE_FOG,
                EnvironmentalEffectType.ICY_TERRAIN,
                EnvironmentalEffectType.BURNING_FLOOR,
                EnvironmentalEffectType.ELECTRIC_FIELD,
                EnvironmentalEffectType.WINDSTORM,
            ]
        else:
            effect_types = [
                EnvironmentalEffectType.DARKNESS,
                EnvironmentalEffectType.CURSED_ZONE,
                EnvironmentalEffectType.BURNING_FLOOR,
                EnvironmentalEffectType.POISON_SWAMP,
                EnvironmentalEffectType.RADIATION_ZONE,
                EnvironmentalEffectType.GRAVITY_ANOMALY,
                EnvironmentalEffectType.BLOOD_MOON,
                EnvironmentalEffectType.HALLOWED_LIGHT,
            ]
        
        # 랜덤 효과 선택
        effect_type = random.choice(effect_types)
        
        # 효과가 적용될 타일 생성 (맵의 일부 영역)
        effect = EnvironmentalEffect(
            effect_type=effect_type,
            intensity=random.uniform(0.8, 1.5)
        )
        
        # 이미 사용된 타일 추적 (겹치지 않도록)
        used_tiles = set()
        num_tiles = int(map_width * map_height * random.uniform(0.2, 0.4))
        max_attempts = num_tiles * 10  # 최대 시도 횟수
        
        attempts = 0
        while len(effect.affected_tiles) < num_tiles and attempts < max_attempts:
            x = random.randint(1, map_width - 2)
            y = random.randint(1, map_height - 2)
            
            # 이미 다른 효과에 사용된 타일이면 건너뜀
            if (x, y) not in used_tiles:
                effect.affected_tiles.add((x, y))
                used_tiles.add((x, y))
            
            attempts += 1
        
        if len(effect.affected_tiles) > 0:
            effects.append(effect)
            logger.info(f"환경 효과 생성: {effect.name} (영향 타일: {len(effect.affected_tiles)})")
        
        return effects
