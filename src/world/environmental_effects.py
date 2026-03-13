from enum import Enum
from dataclasses import dataclass
from typing import Set, Dict, Any, Optional
import random

from src.core.logger import get_logger

logger = get_logger("environmental_effects")


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


# 환경 효과 설정 (간격 및 데미지)
EFFECT_CONFIGS = {
    EnvironmentalEffectType.BURNING_FLOOR: {
        "interval": 0.2,  # 0.2초마다
        "damage_type": "fixed",
        "value": 3,      # 고정 3 데미지
        "message": "불타는 바닥이 당신을 태웁니다!"
    },
    EnvironmentalEffectType.POISON_SWAMP: {
        "interval": 4.0,  # 4초마다
        "damage_type": "percent_max",
        "value": 0.1,    # 최대 체력의 10%
        "message": "독 늪이 당신을 침식합니다!"
    },
    EnvironmentalEffectType.RADIATION_ZONE: {
        "interval": 2.0,
        "damage_type": "hybrid",  # 고정 + 퍼센트
        "value": {"fixed": 10, "percent": 0.04},
        "message": "방사능이 당신을 해칩니다!"
    },
    EnvironmentalEffectType.ELECTRIC_FIELD: {
        "interval": 0.1,  # 0.1초마다 (빠름)
        "damage_type": "fixed",
        "value": 1,
        "message": "전기장이 당신을 감전시킵니다!"
    },
    EnvironmentalEffectType.CURSED_ZONE: {
        "interval": 4.0,
        "damage_type": "percent_max",
        "value": 0.15,
        "message": "저주의 기운이 당신을 갉아먹습니다!"
    },
    EnvironmentalEffectType.BLOOD_MOON: {
        "interval": 2.5,
        "damage_type": "percent_cur", # 현재 체력 비례
        "value": 0.12,
        "message": "피의 달의 저주가 당신을 괴롭힙니다!"
    },
     EnvironmentalEffectType.HOLY_GROUND: {
        "interval": 3.0,
        "damage_type": "heal_percent_max",
        "value": 0.15,
        "message": "신성한 땅이 당신을 치유합니다."
    },
    EnvironmentalEffectType.BLESSED_SANCTUARY: {
        "interval": 2.5,
        "damage_type": "heal_percent_max",
        "value": 0.1,
        "message": "축복받은 성역이 당신을 회복시킵니다!"
    },
    EnvironmentalEffectType.HALLOWED_LIGHT: {
        "interval": 0.2,
        "damage_type": "heal_percent_max",
        "value": 0.01,
        "message": "신성한 빛이 당신을 치유합니다!"
    },
    EnvironmentalEffectType.MANA_VORTEX: {
        "interval": 0.2,
        "damage_type": "heal_mp_percent_max",
        "value": 0.01,
        "message": "마나 소용돌이가 마력을 회복시킵니다!"
    }
}


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
        # affected_tiles가 None이 아니고 해당 좌표가 포함되어 있는지 확인
        if effect.affected_tiles is None:
            return False
        return (x, y) in effect.affected_tiles
    
    def get_effects_at_tile(self, x: int, y: int) -> list:
        """특정 타일의 모든 효과 가져오기"""
        effects = []
        for effect in self.active_effects.values():
            # affected_tiles가 None이 아니고 해당 좌표가 포함되어 있는지 확인
            if effect.affected_tiles is not None and (x, y) in effect.affected_tiles:
                effects.append(effect)
        return effects
    
    def get_effect_config(self, effect_type: EnvironmentalEffectType) -> dict:
        """효과 설정 가져오기"""
        return EFFECT_CONFIGS.get(effect_type, {})

    def apply_tile_effects(self, player: Any, x: int, y: int, is_movement: bool = False) -> list:
        """
        타일의 모든 효과 적용 (레거시 지원 또는 일괄 적용용)
        
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
            message = self.apply_effect(effect, player, is_movement=is_movement)
            if message:
                messages.append(message)
        
        return messages
    
    def apply_effect(self, effect: EnvironmentalEffect, player: Any, is_movement: bool = False) -> str:
        """
        개별 효과 적용
        
        Args:
            effect: 환경 효과
            player: 플레이어 객체
            is_movement: 이동 시 적용 여부 (True면 이동 시 데미지, False면 시간당 데미지/회복)
        """
        # 설정 확인
        config = EFFECT_CONFIGS.get(effect.effect_type)
        
        # 이동 시에는 기존 로직 무시 (시간 기반으로 통합됨)
        if is_movement:
            # 이동 시 즉시 발동해야 하는 예외적인 효과가 있다면 여기에 추가
            # 현재 모든 효과를 시간 기반으로 전환 요청받음
            return None

        # 설정된 효과 처리
        if config:
            import math
            damage = 0
            heal = 0
            mp_restore = 0
            
            damage_type = config["damage_type"]
            value = config["value"]
            
            # 데미지/회복량 계산
            if damage_type == "fixed":
                damage = int(value * effect.intensity)
            elif damage_type == "percent_max":
                damage = int(player.max_hp * value * effect.intensity)
            elif damage_type == "percent_cur":
                damage = int(player.current_hp * value * effect.intensity)
            elif damage_type == "hybrid":
                fixed = value.get("fixed", 0)
                percent = value.get("percent", 0.0)
                damage = int((fixed + player.max_hp * percent) * effect.intensity)
            elif damage_type == "heal_percent_max":
                heal = int(player.max_hp * value * effect.intensity)
            elif damage_type == "heal_mp_percent_max":
                if hasattr(player, 'max_mp'):
                    mp_restore = int(player.max_mp * value * effect.intensity)
            
            # 적용
            if damage > 0:
                player.current_hp = max(1, player.current_hp - damage)
                return f"{config['message']} ({damage} 데미지)"
                
            if heal > 0:
                if hasattr(player, 'heal'):
                    player.heal(heal)
                else:
                    player.current_hp = min(player.max_hp, player.current_hp + heal)
                return f"{config['message']} (+{heal} HP)"
                
            if mp_restore > 0 and hasattr(player, 'restore_mp'):
                player.restore_mp(mp_restore)
                return f"{config['message']} (+{mp_restore} MP)"
                
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
                modifiers["magic_defense"] = modifiers.get("magic_defense", 0.0) + 0.20  # +20%
            
            elif effect.effect_type == EnvironmentalEffectType.WINDSTORM:
                modifiers["accuracy"] = modifiers.get("accuracy", 0.0) - 0.25  # -25%
                modifiers["evasion"] = modifiers.get("evasion", 0.0) + 0.15  # +15%
            
            elif effect.effect_type == EnvironmentalEffectType.MANA_VORTEX:
                modifiers["magic"] = modifiers.get("magic", 0.0) + 0.30  # +30%
            
            elif effect.effect_type == EnvironmentalEffectType.BLOOD_MOON:
                modifiers["strength"] = modifiers.get("strength", 0.0) + 0.30  # +30%
                modifiers["magic"] = modifiers.get("magic", 0.0) + 0.30  # +30%
                modifiers["defense"] = modifiers.get("defense", 0.0) - 0.20  # -20%
                modifiers["magic_defense"] = modifiers.get("magic_defense", 0.0) - 0.20  # -20%
            
            elif effect.effect_type == EnvironmentalEffectType.HALLOWED_LIGHT:
                for stat in ["strength", "defense", "magic", "speed"]:
                    modifiers[stat] = modifiers.get(stat, 0.0) + 0.10  # +10%
        
        return modifiers


class EnvironmentalEffectGenerator:
    """환경 효과 생성기"""
    
    @staticmethod
    def generate_for_floor(floor_number: int, map_width: int, map_height: int, seed: Optional[int] = None) -> list:
        """
        층별 환경 효과 생성 (바이옴 방식)
        
        Args:
            floor_number: 던전 층
            map_width: 맵 너비
            map_height: 맵 높이
            seed: 랜덤 시드 (None이면 랜덤, 동일 시드 사용 시 동일한 환경 효과 생성)
            
        Returns:
            환경 효과 리스트
        """
        # 시드 설정 (던전 생성과 구분하기 위해 다른 오프셋 사용)
        if seed is not None:
            env_seed = seed + floor_number * 1000 + 50000  # 환경 효과용 오프셋
            random.seed(env_seed)
            logger.info(f"환경 효과 생성 시드: {env_seed} (floor={floor_number})")
        
        effects = []
        
        # 층에 따른 효과 타입 풀 설정
        if floor_number <= 3:
            available_types = [
                EnvironmentalEffectType.DENSE_FOG,
                EnvironmentalEffectType.HOLY_GROUND,
                EnvironmentalEffectType.BLESSED_SANCTUARY,
                EnvironmentalEffectType.MANA_VORTEX,
                EnvironmentalEffectType.ICY_TERRAIN, # 저층에도 얼음 추가
            ]
        elif floor_number <= 7:
            available_types = [
                EnvironmentalEffectType.POISON_SWAMP,
                EnvironmentalEffectType.DENSE_FOG,
                EnvironmentalEffectType.ICY_TERRAIN,
                EnvironmentalEffectType.BURNING_FLOOR,
                EnvironmentalEffectType.ELECTRIC_FIELD,
                EnvironmentalEffectType.WINDSTORM,
                EnvironmentalEffectType.GRAVITY_ANOMALY,
            ]
        else:
            available_types = [
                EnvironmentalEffectType.DARKNESS,
                EnvironmentalEffectType.CURSED_ZONE,
                EnvironmentalEffectType.BURNING_FLOOR,
                EnvironmentalEffectType.POISON_SWAMP,
                EnvironmentalEffectType.RADIATION_ZONE,
                EnvironmentalEffectType.GRAVITY_ANOMALY,
                EnvironmentalEffectType.BLOOD_MOON,
                EnvironmentalEffectType.HALLOWED_LIGHT,
            ]
        
        # 최소 3가지 이상의 효과 타입 선택
        num_biomes = random.randint(3, min(5, len(available_types)))
        selected_types = random.sample(available_types, num_biomes)
        
        # 전체 맵 크기
        total_tiles = map_width * map_height
        
        # 효과가 적용될 총 타일 수 (층에 따라 5% ~ 20%로 증가)
        # 1층: 5%, 15층 이상: 20%
        min_ratio = 0.05
        max_ratio = 0.2
        max_floor_scaling = 15
        
        current_floor_capped = min(floor_number, max_floor_scaling)
        
        if max_floor_scaling > 1:
            progress = (current_floor_capped - 1) / (max_floor_scaling - 1)
        else:
            progress = 1.0
            
        ratio = min_ratio + (max_ratio - min_ratio) * progress
        
        target_effect_tiles = int(total_tiles * ratio)
        logger.info(f"층 {floor_number} 환경 효과 비율 목표: {ratio*100:.1f}% ({target_effect_tiles} 타일)")
        
        # 각 바이옴당 할당할 타일 수 (약간의 랜덤성 부여)
        tiles_per_biome = []
        remaining_tiles = target_effect_tiles
        for i in range(num_biomes - 1):
            # 평균의 0.8 ~ 1.2배
            avg_tiles = target_effect_tiles // num_biomes
            count = int(random.uniform(0.8, 1.2) * avg_tiles)
            tiles_per_biome.append(count)
            remaining_tiles -= count
        tiles_per_biome.append(remaining_tiles) # 나머지는 마지막 바이옴에
        
        # 이미 사용된 타일 추적
        used_tiles = set()
        
        # 각 바이옴 생성
        for i, effect_type in enumerate(selected_types):
            target_count = tiles_per_biome[i]
            if target_count <= 0:
                continue
                
            effect = EnvironmentalEffect(
                effect_type=effect_type,
                intensity=random.uniform(0.8, 1.5)
            )
            
            # 시드 포인트 선택 (랜덤 위치)
            # 맵 가장자리는 피함 (맵이 충분히 클 때만)
            if map_width < 6 or map_height < 6:
                # 맵이 너무 작으면 환경 효과 생성 스킵
                continue
            seed_x = random.randint(2, max(2, map_width - 3))
            seed_y = random.randint(2, max(2, map_height - 3))
            
            # 영역 확장 (Region Growing)
            # 큐를 사용하여 덩어리감 있게 확장
            candidates = [(seed_x, seed_y)]
            current_biome_tiles = set()
            
            attempts = 0
            max_attempts = target_count * 5
            
            while len(current_biome_tiles) < target_count and candidates and attempts < max_attempts:
                attempts += 1
                
                # 랜덤하게 후보 선택 (불규칙한 모양을 위해)
                idx = random.randint(0, len(candidates) - 1)
                cx, cy = candidates[idx]
                
                # 이미 처리된 후보는 제거 (단, 확률적으로 남겨두어 뭉치게 할 수도 있음)
                if (cx, cy) in current_biome_tiles or (cx, cy) in used_tiles:
                    candidates.pop(idx)
                    continue
                
                # 타일 추가
                current_biome_tiles.add((cx, cy))
                used_tiles.add((cx, cy))
                
                # 인접 타일 후보에 추가
                # 4방향 + 대각선(확률적)으로 자연스럽게
                directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                if random.random() < 0.3: # 30% 확률로 대각선 확장
                    directions.extend([(1, 1), (1, -1), (-1, 1), (-1, -1)])
                
                for dx, dy in directions:
                    nx, ny = cx + dx, cy + dy
                    
                    # 맵 범위 체크
                    if 1 <= nx < map_width - 1 and 1 <= ny < map_height - 1:
                        if (nx, ny) not in used_tiles and (nx, ny) not in current_biome_tiles:
                            # 이미 후보에 있는지는 체크하지 않음 (확률 높이기 위해)
                            candidates.append((nx, ny))
            
            if current_biome_tiles:
                effect.affected_tiles = current_biome_tiles
                effects.append(effect)
                logger.info(f"바이옴 생성: {effect.name} (타일 {len(current_biome_tiles)}개)")
        
        return effects
