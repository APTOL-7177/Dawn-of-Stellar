"""
Wound System - 상처 시스템

데미지의 일부가 영구 상처로 전환되는 시스템
"""

from typing import Dict, Any, Optional
from src.core.event_bus import event_bus, Events
from src.core.config import get_config
from src.core.logger import get_logger


class WoundSystem:
    """
    상처 시스템

    - 받은 데미지의 일부가 상처로 전환
    - 상처는 자연 회복이 느림
    - 치유 아이템으로 더 효과적으로 회복
    """

    def __init__(self) -> None:
        self.logger = get_logger("wound")
        self.config = get_config()

        # 설정 로드
        self.enabled = self.config.get("wound_system.enabled", True)
        self.wound_threshold = self.config.get("wound_system.wound_threshold", 0.25)
        self.natural_healing_rate = self.config.get("wound_system.natural_healing_rate", 0.01)
        self.max_wound_percentage = self.config.get("wound_system.max_wound_percentage", 0.5)
        self.healing_items_efficiency = self.config.get("wound_system.healing_items_efficiency", 1.5)

        # 이벤트 구독
        event_bus.subscribe(Events.CHARACTER_HP_CHANGE, self._on_hp_change)

    def apply_damage(self, character: Any, damage: int) -> Dict[str, int]:
        """
        데미지 적용 및 상처 계산

        Args:
            character: 캐릭터
            damage: 데미지 양

        Returns:
            {"hp_damage": int, "wound": int}
        """
        if not self.enabled:
            return {"hp_damage": damage, "wound": 0}

        # 상처 계산
        wound_amount = int(damage * self.wound_threshold)

        # 현재 상처 + 새 상처가 최대치를 넘지 않도록
        max_wound = int(character.max_hp * self.max_wound_percentage)
        current_wound = getattr(character, "wound", 0)

        if current_wound + wound_amount > max_wound:
            wound_amount = max(0, max_wound - current_wound)

        # 상처 적용
        if not hasattr(character, "wound"):
            character.wound = 0

        character.wound += wound_amount

        self.logger.debug(
            f"상처 적용: {character.name}",
            {
                "damage": damage,
                "wound": wound_amount,
                "total_wound": character.wound,
                "max_wound": max_wound
            }
        )

        event_bus.publish("wound.applied", {
            "character": character,
            "wound_amount": wound_amount,
            "total_wound": character.wound
        })

        return {
            "hp_damage": damage,
            "wound": wound_amount
        }

    def natural_healing(self, character: Any) -> int:
        """
        자연 회복 (턴마다)

        Args:
            character: 캐릭터

        Returns:
            회복된 HP 양
        """
        if not self.enabled or not hasattr(character, "wound"):
            return 0

        # 현재 HP가 가능한 최대 HP (max_hp - wound)보다 낮을 때만 회복
        effective_max_hp = character.max_hp - character.wound
        if character.hp >= effective_max_hp:
            return 0

        heal_amount = int(character.max_hp * self.natural_healing_rate)
        heal_amount = min(heal_amount, effective_max_hp - character.hp)

        if heal_amount > 0:
            character.hp += heal_amount
            self.logger.debug(f"자연 회복: {character.name} +{heal_amount} HP")

        return heal_amount

    def heal_with_item(self, character: Any, base_heal: int) -> Dict[str, int]:
        """
        아이템으로 회복 (상처도 일부 회복)

        Args:
            character: 캐릭터
            base_heal: 기본 회복량

        Returns:
            {"hp_healed": int, "wound_healed": int}
        """
        if not self.enabled:
            character.hp = min(character.hp + base_heal, character.max_hp)
            return {"hp_healed": base_heal, "wound_healed": 0}

        # HP 회복
        effective_max_hp = character.max_hp - getattr(character, "wound", 0)
        hp_healed = min(base_heal, effective_max_hp - character.hp)

        # 초과 회복량을 상처 회복에 사용
        excess_heal = base_heal - hp_healed
        wound_heal = int(excess_heal * self.healing_items_efficiency * 0.25)

        if hasattr(character, "wound"):
            wound_heal = min(wound_heal, character.wound)
            character.wound -= wound_heal
        else:
            wound_heal = 0

        character.hp += hp_healed

        self.logger.info(
            f"아이템 회복: {character.name}",
            {
                "hp_healed": hp_healed,
                "wound_healed": wound_heal,
                "remaining_wound": getattr(character, "wound", 0)
            }
        )

        event_bus.publish("wound.healed", {
            "character": character,
            "hp_healed": hp_healed,
            "wound_healed": wound_heal
        })

        return {
            "hp_healed": hp_healed,
            "wound_healed": wound_heal
        }

    def get_effective_max_hp(self, character: Any) -> int:
        """
        실제 최대 HP (상처 고려)

        Args:
            character: 캐릭터

        Returns:
            유효 최대 HP
        """
        wound = getattr(character, "wound", 0)
        return character.max_hp - wound

    def get_wound_percentage(self, character: Any) -> float:
        """
        상처 비율 (0.0 ~ 1.0)

        Args:
            character: 캐릭터

        Returns:
            상처 비율
        """
        wound = getattr(character, "wound", 0)
        return wound / character.max_hp if character.max_hp > 0 else 0.0

    def _on_hp_change(self, data: Dict[str, Any]) -> None:
        """HP 변화 이벤트 핸들러"""
        character = data.get("character")
        change = data.get("change", 0)

        if change < 0 and character:
            # 데미지를 받았을 때
            self.apply_damage(character, abs(change))


# 전역 인스턴스
_wound_system: Optional[WoundSystem] = None


def get_wound_system() -> WoundSystem:
    """전역 상처 시스템 인스턴스"""
    global _wound_system
    if _wound_system is None:
        _wound_system = WoundSystem()
    return _wound_system
