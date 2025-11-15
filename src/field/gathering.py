"""
Gathering System - 채집 시스템

필드에서 자원을 채집하는 시스템
"""

import random
from typing import Dict, Any, Optional, List
from src.core.event_bus import event_bus
from src.core.config import get_config
from src.core.logger import get_logger
from src.character.stats import Stats


class Resource:
    """채집 가능한 자원"""

    def __init__(
        self,
        resource_id: str,
        name: str,
        rarity: float = 1.0,
        required_skill_level: int = 1
    ) -> None:
        self.resource_id = resource_id
        self.name = name
        self.rarity = rarity  # 0.0 ~ 1.0 (낮을수록 희귀)
        self.required_skill_level = required_skill_level


class GatheringSystem:
    """채집 시스템"""

    def __init__(self) -> None:
        self.logger = get_logger("gathering")
        self.config = get_config()

        # 설정 로드
        self.enabled = self.config.get("field_systems.gathering.enabled", True)
        self.stamina_cost = self.config.get("field_systems.gathering.stamina_cost", 10)
        self.base_success_chance = self.config.get("field_systems.gathering.success_base_chance", 0.7)
        self.stat_bonus = self.config.get("field_systems.gathering.stat_bonus", "dexterity")
        self.yield_range = self.config.get("field_systems.gathering.yield_multiplier_range", [1, 3])

        # 자원 데이터베이스
        self.resources: Dict[str, Resource] = {}
        self._load_resources()

    def _load_resources(self) -> None:
        """자원 데이터 로드"""
        # 기본 자원 데이터 (향후 YAML로 확장 가능)
        default_resources = [
            # === 기본 식재료 (평야, 초원) - 난이도 1 ===
            Resource("herb", "약초", 0.9, 1),
            Resource("wild_berry", "야생 베리", 0.9, 1),
            Resource("mushroom", "버섯", 0.8, 1),
            Resource("vegetable", "야채", 0.8, 1),
            Resource("flower", "꽃", 0.7, 1),
            Resource("flour", "밀가루", 0.8, 1),

            # === 숲 지역 식재료 - 난이도 2 ===
            Resource("honey", "꿀", 0.6, 2),
            Resource("meat", "고기", 0.6, 2),
            Resource("spice", "향신료", 0.5, 2),
            Resource("rare_herb", "희귀 약초", 0.4, 2),
            Resource("pine_nut", "잣", 0.6, 2),
            Resource("wild_ginseng", "산삼", 0.3, 2),

            # === 수변 지역 식재료 - 난이도 2-3 ===
            Resource("fish", "생선", 0.7, 2),
            Resource("shellfish", "조개", 0.6, 2),
            Resource("seaweed", "해조류", 0.7, 2),
            Resource("lotus_root", "연근", 0.5, 3),
            Resource("crystal_water", "크리스탈 물", 0.4, 3),

            # === 산악 지역 식재료 - 난이도 3-4 ===
            Resource("mountain_herb", "산약초", 0.5, 3),
            Resource("crystal", "크리스탈", 0.3, 3),
            Resource("rare_mushroom", "희귀 버섯", 0.4, 3),
            Resource("mineral_salt", "암염", 0.6, 3),
            Resource("dragon_scale", "드래곤 비늘", 0.1, 4),

            # === 마법 숲 지역 - 난이도 4-5 ===
            Resource("moonflower", "달빛꽃", 0.3, 4),
            Resource("mana_herb", "마나 허브", 0.3, 4),
            Resource("star_fruit", "별빛 과일", 0.2, 5),
            Resource("magic_mushroom", "마법 버섯", 0.3, 4),
            Resource("elf_tears", "엘프의 눈물", 0.2, 5),

            # === 화산 지역 - 난이도 5-6 ===
            Resource("lava_pepper", "용암 고추", 0.3, 5),
            Resource("fire_crystal", "화염 크리스탈", 0.2, 5),
            Resource("phoenix_feather", "불사조 깃털", 0.1, 6),
            Resource("volcano_salt", "화산염", 0.4, 5),

            # === 극지 지역 - 난이도 5-6 ===
            Resource("ice_flower", "얼음꽃", 0.3, 5),
            Resource("frost_berry", "서리 베리", 0.4, 5),
            Resource("ice_crystal", "얼음 크리스탈", 0.2, 6),
            Resource("snow_mushroom", "설화버섯", 0.3, 5),

            # === 사막 지역 - 난이도 4-5 ===
            Resource("desert_cactus", "사막 선인장", 0.5, 4),
            Resource("sand_truffle", "사막 송로버섯", 0.2, 5),
            Resource("mirage_fruit", "신기루 과일", 0.2, 5),
            Resource("crystal_sugar", "크리스탈 설탕", 0.3, 4),

            # === 고대 유적 - 난이도 6+ ===
            Resource("ancient_grain", "고대의 곡물", 0.2, 6),
            Resource("relic_spice", "유물 향신료", 0.1, 7),
            Resource("time_flower", "시간의 꽃", 0.1, 7),
            Resource("celestial_nectar", "천상의 꿀", 0.05, 8),
        ]

        for resource in default_resources:
            self.resources[resource.resource_id] = resource

    def can_gather(self, character: Any, resource_id: str) -> bool:
        """
        채집 가능 여부

        Args:
            character: 캐릭터
            resource_id: 자원 ID

        Returns:
            채집 가능 여부
        """
        if not self.enabled:
            return False

        # 스태미나 확인
        stamina = getattr(character, Stats.STAMINA, 0)
        if stamina < self.stamina_cost:
            return False

        # 자원 존재 확인
        resource = self.resources.get(resource_id)
        if not resource:
            return False

        # 스킬 레벨 확인 (임시로 dexterity 사용)
        skill_level = getattr(character, self.stat_bonus, 0)
        if skill_level < resource.required_skill_level:
            return False

        return True

    def gather(self, character: Any, resource_id: str) -> Dict[str, Any]:
        """
        채집 실행

        Args:
            character: 캐릭터
            resource_id: 자원 ID

        Returns:
            채집 결과 {"success": bool, "yield": int, "resource": Resource}
        """
        if not self.can_gather(character, resource_id):
            return {"success": False, "yield": 0, "resource": None}

        resource = self.resources[resource_id]

        # 스태미나 소비
        character.stamina -= self.stamina_cost

        # 성공률 계산
        stat_value = getattr(character, self.stat_bonus, 0)
        success_chance = self.base_success_chance + (stat_value * 0.02)
        success_chance *= resource.rarity  # 희귀도에 따라 감소

        # 채집 시도
        success = random.random() < success_chance

        if success:
            # 획득량 계산
            yield_amount = random.randint(
                self.yield_range[0],
                self.yield_range[0] + stat_value // 5
            )
            yield_amount = min(yield_amount, self.yield_range[1])
        else:
            yield_amount = 0

        result = {
            "success": success,
            "yield": yield_amount,
            "resource": resource
        }

        self.logger.info(
            f"채집: {character.name}",
            {
                "resource": resource.name,
                "success": success,
                "yield": yield_amount
            }
        )

        event_bus.publish("gathering.completed", {
            "character": character,
            "result": result
        })

        return result

    def add_resource(self, resource: Resource) -> None:
        """자원 추가 (동적 확장)"""
        self.resources[resource.resource_id] = resource

    def get_resource(self, resource_id: str) -> Optional[Resource]:
        """자원 조회"""
        return self.resources.get(resource_id)


# 전역 인스턴스
gathering_system = GatheringSystem()
