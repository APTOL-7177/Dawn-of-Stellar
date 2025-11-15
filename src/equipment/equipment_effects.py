"""
Equipment Effects System - 장비 특수 효과 시스템

상처, BRV, 시야, 전투 등 모든 게임 시스템과 연동되는 장비 효과
"""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
from src.core.event_bus import event_bus, Events
from src.core.logger import get_logger


logger = get_logger("equipment_effects")


class EffectTrigger(Enum):
    """효과 발동 시점"""
    ON_EQUIP = "on_equip"              # 장착 시
    ON_UNEQUIP = "on_unequip"          # 해제 시
    ON_HIT = "on_hit"                  # 공격 성공 시
    ON_DAMAGED = "on_damaged"          # 피격 시
    ON_KILL = "on_kill"                # 적 처치 시
    ON_TURN_START = "on_turn_start"    # 턴 시작 시
    ON_TURN_END = "on_turn_end"        # 턴 종료 시
    ON_HEAL = "on_heal"                # 회복 시
    ON_LOW_HP = "on_low_hp"            # 체력 낮을 때 (30% 이하)
    ON_FULL_HP = "on_full_hp"          # 체력 만땅일 때
    PASSIVE = "passive"                # 상시 효과


class EffectType(Enum):
    """효과 타입"""
    # === 시야 관련 ===
    VISION_BONUS = "vision_bonus"              # 시야 증가
    NIGHT_VISION = "night_vision"              # 야간 시야 (어둠 무시)
    TRUE_SIGHT = "true_sight"                  # 투시 (벽 너머 보기)
    DETECT_ENEMY = "detect_enemy"              # 적 탐지 (미니맵)

    # === 상처 관련 ===
    WOUND_REDUCTION = "wound_reduction"        # 상처 감소 (받는 상처 -X%)
    WOUND_IMMUNITY = "wound_immunity"          # 상처 면역
    WOUND_REGEN = "wound_regen"                # 상처 회복 (턴당 X씩)
    WOUND_TRANSFER = "wound_transfer"          # 상처를 적에게 전이

    # === BRV 관련 ===
    BRV_BONUS = "brv_bonus"                    # BRV 공격력 +X%
    BRV_SHIELD = "brv_shield"                  # BRV 데미지 감소 X%
    BRV_REGEN = "brv_regen"                    # 턴당 BRV +X
    BRV_STEAL = "brv_steal"                    # BRV 흡수 +X%
    BRV_BREAK_BONUS = "brv_break_bonus"        # BREAK 데미지 +X%
    BRV_PROTECT = "brv_protect"                # BREAK 방지 (1회)

    # === 전투 효과 ===
    LIFESTEAL = "lifesteal"                    # 생명력 흡수 X%
    THORNS = "thorns"                          # 반사 데미지 X%
    CRITICAL_DAMAGE = "critical_damage"        # 크리티컬 데미지 +X%
    CRITICAL_CHANCE = "critical_chance"        # 크리티컬 확률 +X%
    DODGE_CHANCE = "dodge_chance"              # 회피 확률 +X%
    BLOCK_CHANCE = "block_chance"              # 블록 확률 +X%
    COUNTER_ATTACK = "counter_attack"          # 반격 확률 X%
    FIRST_STRIKE = "first_strike"              # 선제공격 보너스
    EXECUTE = "execute"                        # 처형 (체력 낮은 적 추가 데미지)

    # === 회복 효과 ===
    HP_REGEN = "hp_regen"                      # HP 재생 (턴당 X%)
    MP_REGEN = "mp_regen"                      # MP 재생 (턴당 X)
    HEAL_BOOST = "heal_boost"                  # 받는 회복량 +X%
    OVERHEAL = "overheal"                      # 과다 회복 → 실드

    # === 상태 효과 ===
    STATUS_IMMUNITY = "status_immunity"        # 상태이상 면역
    STATUS_RESISTANCE = "status_resistance"    # 상태이상 저항 X%
    STATUS_DURATION = "status_duration"        # 버프 지속시간 +X턴
    DEBUFF_REFLECT = "debuff_reflect"          # 디버프 반사 X%

    # === 자원 관련 ===
    MP_COST_REDUCTION = "mp_cost_reduction"    # MP 소비 -X%
    RESOURCE_GAIN = "resource_gain"            # 자원 획득 +X%
    GOLD_FIND = "gold_find"                    # 골드 획득 +X%
    ITEM_FIND = "item_find"                    # 아이템 드롭률 +X%
    EXP_BONUS = "exp_bonus"                    # 경험치 +X%

    # === 기믹 관련 ===
    GIMMICK_BOOST = "gimmick_boost"            # 기믹 효율 +X%
    GIMMICK_COST_REDUCTION = "gimmick_cost_reduction"  # 기믹 소모 -X%
    MAX_GIMMICK_INCREASE = "max_gimmick_increase"      # 최대 기믹 +X

    # === 특수 효과 ===
    PHOENIX = "phoenix"                        # 부활 (1회)
    BERSERK = "berserk"                        # 광폭화 (HP 낮을수록 강함)
    GLASS_CANNON = "glass_cannon"              # 공격력 +X%, 방어력 -Y%
    TANK = "tank"                              # 방어력 +X%, 속도 -Y%
    ELEMENTAL_AFFINITY = "elemental_affinity"  # 속성 친화력
    DAMAGE_CONVERSION = "damage_conversion"    # 데미지 속성 변환
    COOLDOWN_REDUCTION = "cooldown_reduction"  # 쿨다운 감소
    MULTI_STRIKE = "multi_strike"              # 연속 공격 확률


@dataclass
class EquipmentEffect:
    """장비 효과"""
    effect_type: EffectType
    trigger: EffectTrigger
    value: float
    condition: Optional[str] = None  # "hp_below_50", "enemy_hp_below_30" 등
    element: Optional[str] = None    # "fire", "ice" 등
    status: Optional[str] = None     # 상태 이상 이름
    description: str = ""

    def check_condition(self, context: Dict[str, Any]) -> bool:
        """조건 확인"""
        if not self.condition:
            return True

        character = context.get("character")
        target = context.get("target")

        if self.condition == "hp_below_50" and character:
            return (character.hp / character.max_hp) < 0.5
        elif self.condition == "hp_below_30" and character:
            return (character.hp / character.max_hp) < 0.3
        elif self.condition == "hp_above_50" and character:
            return (character.hp / character.max_hp) >= 0.5
        elif self.condition == "hp_full" and character:
            return character.hp == character.max_hp
        elif self.condition == "enemy_hp_below_30" and target:
            return (target.hp / target.max_hp) < 0.3
        elif self.condition == "in_combat":
            return context.get("in_combat", False)

        return True


class EquipmentEffectManager:
    """장비 효과 관리자"""

    def __init__(self):
        self.active_effects: Dict[str, List[EquipmentEffect]] = {}  # character_id -> effects
        self.effect_handlers: Dict[EffectType, Callable] = {}
        self._register_handlers()
        self._subscribe_events()

    def _subscribe_events(self):
        """이벤트 구독"""
        event_bus.subscribe(Events.EQUIPMENT_EQUIPPED, self._on_equipment_equipped)
        event_bus.subscribe(Events.EQUIPMENT_UNEQUIPPED, self._on_equipment_unequipped)
        event_bus.subscribe(Events.COMBAT_DAMAGE_DEALT, self._on_damage_dealt)
        event_bus.subscribe(Events.COMBAT_DAMAGE_TAKEN, self._on_damage_taken)
        event_bus.subscribe(Events.COMBAT_TURN_START, self._on_turn_start)
        event_bus.subscribe(Events.COMBAT_TURN_END, self._on_turn_end)

    def _register_handlers(self):
        """효과 핸들러 등록"""
        self.effect_handlers = {
            EffectType.VISION_BONUS: self._handle_vision_bonus,
            EffectType.WOUND_REDUCTION: self._handle_wound_reduction,
            EffectType.WOUND_IMMUNITY: self._handle_wound_immunity,
            EffectType.WOUND_REGEN: self._handle_wound_regen,
            EffectType.BRV_BONUS: self._handle_brv_bonus,
            EffectType.BRV_SHIELD: self._handle_brv_shield,
            EffectType.BRV_REGEN: self._handle_brv_regen,
            EffectType.LIFESTEAL: self._handle_lifesteal,
            EffectType.THORNS: self._handle_thorns,
            EffectType.HP_REGEN: self._handle_hp_regen,
            EffectType.MP_REGEN: self._handle_mp_regen,
            # 더 많은 핸들러...
        }

    def add_effect(self, character_id: str, effect: EquipmentEffect):
        """효과 추가"""
        if character_id not in self.active_effects:
            self.active_effects[character_id] = []
        self.active_effects[character_id].append(effect)
        logger.debug(f"효과 추가: {character_id} - {effect.effect_type.value}")

    def remove_effects(self, character_id: str, equipment_id: str = None):
        """효과 제거"""
        if character_id in self.active_effects:
            if equipment_id:
                # 특정 장비 효과만 제거
                self.active_effects[character_id] = [
                    e for e in self.active_effects[character_id]
                    if getattr(e, 'source_id', None) != equipment_id
                ]
            else:
                # 모든 효과 제거
                del self.active_effects[character_id]

    def get_effects_by_trigger(self, character_id: str, trigger: EffectTrigger) -> List[EquipmentEffect]:
        """특정 트리거의 효과 목록"""
        if character_id not in self.active_effects:
            return []
        return [e for e in self.active_effects[character_id] if e.trigger == trigger]

    def get_total_bonus(self, character_id: str, effect_type: EffectType, context: Dict = None) -> float:
        """특정 효과 타입의 총 보너스 계산"""
        if character_id not in self.active_effects:
            return 0.0

        context = context or {}
        total = 0.0

        for effect in self.active_effects[character_id]:
            if effect.effect_type == effect_type:
                if effect.check_condition(context):
                    total += effect.value

        return total

    # === 이벤트 핸들러 ===

    def _on_equipment_equipped(self, data: Dict[str, Any]):
        """장비 착용 이벤트"""
        character = data.get("character")
        item = data.get("item")

        if not character or not item:
            return

        # 캐릭터 ID (name 사용)
        character_id = character.name

        # 아이템의 특수 효과 파싱 및 적용
        effects = []

        # 1. special_effects 리스트가 있으면 그것을 사용
        if hasattr(item, "special_effects") and item.special_effects:
            effects = item.special_effects
        # 2. unique_effect 문자열이 있으면 파싱
        elif hasattr(item, "unique_effect") and item.unique_effect:
            effects = parse_unique_effects(item.unique_effect)

        # 효과 적용
        for effect in effects:
            # 효과에 source_id 추가 (제거용)
            effect.source_id = getattr(item, 'item_id', item.name)
            self.add_effect(character_id, effect)

            # ON_EQUIP 트리거 효과 즉시 실행
            if effect.trigger == EffectTrigger.ON_EQUIP:
                self._execute_effect(character, effect, {})

    def _on_equipment_unequipped(self, data: Dict[str, Any]):
        """장비 해제 이벤트"""
        character = data.get("character")
        item = data.get("item")

        if not character or not item:
            return

        # 캐릭터 ID (name 사용)
        character_id = character.name
        item_id = getattr(item, 'item_id', item.name)

        # ON_UNEQUIP 효과 실행
        effects = []
        if hasattr(item, "special_effects") and item.special_effects:
            effects = item.special_effects
        elif hasattr(item, "unique_effect") and item.unique_effect:
            effects = parse_unique_effects(item.unique_effect)

        for effect in effects:
            if effect.trigger == EffectTrigger.ON_UNEQUIP:
                self._execute_effect(character, effect, {})

        # 효과 제거
        self.remove_effects(character_id, item_id)

    def _on_damage_dealt(self, data: Dict[str, Any]):
        """공격 성공 이벤트"""
        attacker = data.get("attacker")
        target = data.get("target")
        damage = data.get("damage", 0)

        if not attacker:
            return

        effects = self.get_effects_by_trigger(attacker.name, EffectTrigger.ON_HIT)
        for effect in effects:
            context = {"character": attacker, "target": target, "damage": damage}
            if effect.check_condition(context):
                self._execute_effect(attacker, effect, context)

    def _on_damage_taken(self, data: Dict[str, Any]):
        """피격 이벤트"""
        defender = data.get("defender")
        attacker = data.get("attacker")
        damage = data.get("damage", 0)

        if not defender:
            return

        effects = self.get_effects_by_trigger(defender.name, EffectTrigger.ON_DAMAGED)
        for effect in effects:
            context = {"character": defender, "target": attacker, "damage": damage}
            if effect.check_condition(context):
                self._execute_effect(defender, effect, context)

    def _on_turn_start(self, data: Dict[str, Any]):
        """턴 시작 이벤트"""
        character = data.get("character")
        if not character:
            return

        effects = self.get_effects_by_trigger(character.name, EffectTrigger.ON_TURN_START)
        for effect in effects:
            self._execute_effect(character, effect, {"character": character})

    def _on_turn_end(self, data: Dict[str, Any]):
        """턴 종료 이벤트"""
        character = data.get("character")
        if not character:
            return

        effects = self.get_effects_by_trigger(character.name, EffectTrigger.ON_TURN_END)
        for effect in effects:
            self._execute_effect(character, effect, {"character": character})

    # === 효과 실행 ===

    def _execute_effect(self, character: Any, effect: EquipmentEffect, context: Dict[str, Any]):
        """효과 실행"""
        handler = self.effect_handlers.get(effect.effect_type)
        if handler:
            handler(character, effect, context)
        else:
            logger.warning(f"핸들러 없음: {effect.effect_type}")

    # === 개별 효과 핸들러 ===

    def _handle_vision_bonus(self, character: Any, effect: EquipmentEffect, context: Dict):
        """시야 증가"""
        if hasattr(character, "vision_bonus"):
            character.vision_bonus += int(effect.value)
        else:
            character.vision_bonus = int(effect.value)
        logger.debug(f"{character.name} 시야 +{effect.value}")

    def _handle_wound_reduction(self, character: Any, effect: EquipmentEffect, context: Dict):
        """상처 감소"""
        if hasattr(character, "wound_reduction"):
            character.wound_reduction += effect.value
        else:
            character.wound_reduction = effect.value

    def _handle_wound_immunity(self, character: Any, effect: EquipmentEffect, context: Dict):
        """상처 면역"""
        character.wound_immune = True

    def _handle_wound_regen(self, character: Any, effect: EquipmentEffect, context: Dict):
        """상처 회복 (턴당)"""
        if hasattr(character, "wound"):
            heal_amount = int(effect.value)
            character.wound = max(0, character.wound - heal_amount)
            logger.info(f"{character.name} 상처 회복: -{heal_amount}")

    def _handle_brv_bonus(self, character: Any, effect: EquipmentEffect, context: Dict):
        """BRV 보너스"""
        if hasattr(character, "brv_bonus_multiplier"):
            character.brv_bonus_multiplier += effect.value
        else:
            character.brv_bonus_multiplier = 1.0 + effect.value

    def _handle_brv_shield(self, character: Any, effect: EquipmentEffect, context: Dict):
        """BRV 방어"""
        if hasattr(character, "brv_shield"):
            character.brv_shield += effect.value
        else:
            character.brv_shield = effect.value

    def _handle_brv_regen(self, character: Any, effect: EquipmentEffect, context: Dict):
        """BRV 재생"""
        if hasattr(character, "brv"):
            character.brv += int(effect.value)
            logger.debug(f"{character.name} BRV +{effect.value}")

    def _handle_lifesteal(self, character: Any, effect: EquipmentEffect, context: Dict):
        """생명력 흡수"""
        damage = context.get("damage", 0)
        heal = int(damage * effect.value)
        if heal > 0:
            character.hp = min(character.max_hp, character.hp + heal)
            logger.info(f"{character.name} 생명력 흡수: +{heal} HP")

    def _handle_thorns(self, character: Any, effect: EquipmentEffect, context: Dict):
        """가시 (반사 데미지)"""
        damage = context.get("damage", 0)
        attacker = context.get("target")  # 공격자

        if attacker:
            reflect_damage = int(damage * effect.value)
            if reflect_damage > 0:
                attacker.hp -= reflect_damage
                logger.info(f"{character.name} 가시 데미지: {attacker.name}에게 {reflect_damage}")

    def _handle_hp_regen(self, character: Any, effect: EquipmentEffect, context: Dict):
        """HP 재생"""
        # 상처 시스템 고려
        from src.systems.wound_system import get_wound_system
        wound_system = get_wound_system()
        effective_max_hp = wound_system.get_effective_max_hp(character)

        heal = int(character.max_hp * effect.value)
        if character.hp < effective_max_hp:
            character.hp = min(effective_max_hp, character.hp + heal)
            logger.debug(f"{character.name} HP 재생: +{heal}")

    def _handle_mp_regen(self, character: Any, effect: EquipmentEffect, context: Dict):
        """MP 재생"""
        restore = int(effect.value)
        character.mp = min(character.max_mp, character.mp + restore)
        logger.debug(f"{character.name} MP 재생: +{restore}")


# 전역 인스턴스
_equipment_effect_manager: Optional[EquipmentEffectManager] = None


def get_equipment_effect_manager() -> EquipmentEffectManager:
    """전역 장비 효과 관리자"""
    global _equipment_effect_manager
    if _equipment_effect_manager is None:
        _equipment_effect_manager = EquipmentEffectManager()
    return _equipment_effect_manager


# === 효과 생성 헬퍼 함수 ===

def create_vision_effect(bonus: int) -> EquipmentEffect:
    """시야 증가 효과"""
    return EquipmentEffect(
        effect_type=EffectType.VISION_BONUS,
        trigger=EffectTrigger.ON_EQUIP,
        value=bonus,
        description=f"시야 +{bonus}"
    )


def create_wound_reduction_effect(reduction_percent: float) -> EquipmentEffect:
    """상처 감소 효과"""
    return EquipmentEffect(
        effect_type=EffectType.WOUND_REDUCTION,
        trigger=EffectTrigger.PASSIVE,
        value=reduction_percent,
        description=f"받는 상처 -{int(reduction_percent*100)}%"
    )


def create_brv_bonus_effect(bonus_percent: float) -> EquipmentEffect:
    """BRV 보너스 효과"""
    return EquipmentEffect(
        effect_type=EffectType.BRV_BONUS,
        trigger=EffectTrigger.PASSIVE,
        value=bonus_percent,
        description=f"BRV 공격력 +{int(bonus_percent*100)}%"
    )


def create_lifesteal_effect(percent: float) -> EquipmentEffect:
    """생명력 흡수 효과"""
    return EquipmentEffect(
        effect_type=EffectType.LIFESTEAL,
        trigger=EffectTrigger.ON_HIT,
        value=percent,
        description=f"생명력 흡수 {int(percent*100)}%"
    )


def create_hp_regen_effect(percent_per_turn: float) -> EquipmentEffect:
    """HP 재생 효과"""
    return EquipmentEffect(
        effect_type=EffectType.HP_REGEN,
        trigger=EffectTrigger.ON_TURN_END,
        value=percent_per_turn,
        description=f"턴당 HP {int(percent_per_turn*100)}% 회복"
    )


def parse_unique_effects(unique_effect_string: str) -> List[EquipmentEffect]:
    """
    unique_effect 문자열을 파싱하여 EquipmentEffect 리스트로 변환

    형식: "effect_type:value|effect_type2:value2"
    예시: "vision:2|wound_reduction:0.25|brv_bonus:0.15"

    Args:
        unique_effect_string: 효과 문자열

    Returns:
        EquipmentEffect 객체 리스트
    """
    if not unique_effect_string:
        return []

    effects = []

    # | 로 분리
    for effect_str in unique_effect_string.split("|"):
        if ":" not in effect_str:
            continue

        effect_name, value_str = effect_str.split(":", 1)
        effect_name = effect_name.strip()

        try:
            value = float(value_str)
        except ValueError:
            # 값이 숫자가 아니면 True/False일 수 있음
            value = value_str.strip().lower() == "true" if value_str.strip().lower() in ["true", "false"] else value_str.strip()

        # 효과 타입 매핑
        effect_mapping = {
            # Vision
            "vision": (EffectType.VISION_BONUS, EffectTrigger.ON_EQUIP),
            "night_vision": (EffectType.NIGHT_VISION, EffectTrigger.PASSIVE),
            "true_sight": (EffectType.TRUE_SIGHT, EffectTrigger.PASSIVE),

            # Wound
            "wound_reduction": (EffectType.WOUND_REDUCTION, EffectTrigger.PASSIVE),
            "wound_immunity": (EffectType.WOUND_IMMUNITY, EffectTrigger.PASSIVE),
            "wound_regen": (EffectType.WOUND_REGEN, EffectTrigger.ON_TURN_END),

            # BRV
            "brv_bonus": (EffectType.BRV_BONUS, EffectTrigger.PASSIVE),
            "brv_shield": (EffectType.BRV_SHIELD, EffectTrigger.ON_EQUIP),
            "brv_regen": (EffectType.BRV_REGEN, EffectTrigger.ON_TURN_START),
            "brv_steal": (EffectType.BRV_STEAL, EffectTrigger.ON_HIT),
            "brv_break_bonus": (EffectType.BRV_BREAK_BONUS, EffectTrigger.PASSIVE),

            # Combat
            "lifesteal": (EffectType.LIFESTEAL, EffectTrigger.ON_HIT),
            "thorns": (EffectType.THORNS, EffectTrigger.ON_DAMAGED),
            "critical_damage": (EffectType.CRITICAL_DAMAGE, EffectTrigger.PASSIVE),
            "critical_rate": (EffectType.CRITICAL_RATE, EffectTrigger.PASSIVE),
            "dodge_chance": (EffectType.DODGE_CHANCE, EffectTrigger.PASSIVE),
            "counter_attack": (EffectType.COUNTER_ATTACK, EffectTrigger.ON_DAMAGED),
            "first_strike": (EffectType.FIRST_STRIKE, EffectTrigger.PASSIVE),

            # Healing
            "hp_regen": (EffectType.HP_REGEN, EffectTrigger.ON_TURN_END),
            "mp_regen": (EffectType.MP_REGEN, EffectTrigger.ON_TURN_END),
            "healing_bonus": (EffectType.HEALING_BONUS, EffectTrigger.PASSIVE),
            "overheal_shield": (EffectType.OVERHEAL_SHIELD, EffectTrigger.PASSIVE),

            # Status
            "poison_immunity": (EffectType.POISON_IMMUNITY, EffectTrigger.PASSIVE),
            "stun_immunity": (EffectType.STUN_IMMUNITY, EffectTrigger.PASSIVE),
            "silence_immunity": (EffectType.SILENCE_IMMUNITY, EffectTrigger.PASSIVE),
            "burn_immunity": (EffectType.BURN_IMMUNITY, EffectTrigger.PASSIVE),
            "freeze_immunity": (EffectType.FREEZE_IMMUNITY, EffectTrigger.PASSIVE),

            # Resource
            "mp_cost_reduction": (EffectType.MP_COST_REDUCTION, EffectTrigger.PASSIVE),
            "cooldown_reduction": (EffectType.COOLDOWN_REDUCTION, EffectTrigger.PASSIVE),
            "skill_power": (EffectType.SKILL_POWER, EffectTrigger.PASSIVE),
            "spell_power": (EffectType.SPELL_POWER, EffectTrigger.PASSIVE),
            "spell_echo": (EffectType.SPELL_ECHO, EffectTrigger.PASSIVE),

            # Gimmick specific
            "hack_damage": (EffectType.HACK_DAMAGE_BONUS, EffectTrigger.PASSIVE),
            "stance_power": (EffectType.STANCE_POWER, EffectTrigger.PASSIVE),
            "element_power": (EffectType.ELEMENTAL_POWER, EffectTrigger.PASSIVE),
        }

        if effect_name in effect_mapping:
            effect_type, trigger = effect_mapping[effect_name]
            effects.append(EquipmentEffect(
                effect_type=effect_type,
                trigger=trigger,
                value=value,
                description=f"{effect_name}: {value}"
            ))

    return effects
