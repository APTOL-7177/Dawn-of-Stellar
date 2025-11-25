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
    CRITICAL_RATE = "critical_rate"            # 크리티컬 확률 +X% (CRITICAL_CHANCE와 동일, 호환성)
    DODGE_CHANCE = "dodge_chance"              # 회피 확률 +X%
    BLOCK_CHANCE = "block_chance"              # 블록 확률 +X%
    COUNTER_ATTACK = "counter_attack"          # 반격 확률 X%
    FIRST_STRIKE = "first_strike"              # 선제공격 보너스
    EXECUTE = "execute"                        # 처형 (체력 낮은 적 추가 데미지)

    # === 회복 효과 ===
    HP_REGEN = "hp_regen"                      # HP 재생 (턴당 X%)
    MP_REGEN = "mp_regen"                      # MP 재생 (턴당 X)
    HEAL_BOOST = "heal_boost"                  # 받는 회복량 +X%
    HEALING_BONUS = "healing_bonus"            # 회복량 보너스 (HEAL_BOOST와 동일, 호환성)
    OVERHEAL = "overheal"                      # 과다 회복 → 실드
    OVERHEAL_SHIELD = "overheal_shield"        # 과다 회복 → 실드 (OVERHEAL과 동일, 호환성)

    # === 상태 효과 ===
    STATUS_IMMUNITY = "status_immunity"        # 상태이상 면역
    STATUS_RESISTANCE = "status_resistance"    # 상태이상 저항 X%
    STATUS_DURATION = "status_duration"        # 버프 지속시간 +X턴
    DEBUFF_REFLECT = "debuff_reflect"          # 디버프 반사 X%
    POISON_IMMUNITY = "poison_immunity"        # 독 면역
    STUN_IMMUNITY = "stun_immunity"            # 기절 면역
    SILENCE_IMMUNITY = "silence_immunity"      # 침묵 면역
    BURN_IMMUNITY = "burn_immunity"            # 화상 면역
    FREEZE_IMMUNITY = "freeze_immunity"        # 빙결 면역

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
    SKILL_POWER = "skill_power"                # 스킬 위력 +X%
    SPELL_POWER = "spell_power"                # 주문 위력 +X%
    SPELL_ECHO = "spell_echo"                  # 주문 반향 (확률로 재시전)
    HACK_DAMAGE_BONUS = "hack_damage_bonus"    # 해킹 데미지 보너스
    STANCE_POWER = "stance_power"              # 스탠스 위력 +X%
    ELEMENTAL_POWER = "elemental_power"         # 속성 위력 +X%

    # === 추가 효과 (아이템 시스템에서 사용) ===
    ON_KILL_HEAL = "on_kill_heal"              # 처치 시 회복
    ELEMENT = "element"                        # 속성 부여
    STATUS_BURN = "status_burn"                # 화상 상태 부여
    DEBUFF_SLOW = "debuff_slow"                # 슬로우 디버프
    STATUS_SHOCK = "status_shock"              # 감전 상태
    DEBUFF_SILENCE = "debuff_silence"          # 침묵 디버프
    CHAIN_LIGHTNING = "chain_lightning"        # 체인 라이트닝
    ARMOR_PENETRATION = "armor_penetration"    # 방어 관통
    MP_STEAL = "mp_steal"                      # MP 흡수
    BONUS_VS_UNDEAD = "bonus_vs_undead"        # 언데드 상대 보너스
    HEAL_ON_HIT = "heal_on_hit"                # 공격 시 회복
    ACCURACY_BONUS = "accuracy_bonus"          # 명중률 보너스
    DOUBLE_STRIKE = "double_strike"            # 더블 스트라이크
    STRIKE_COUNT = "strike_count"              # 공격 횟수
    STUN_CHANCE = "stun_chance"                # 스턴 확률
    DAMAGE_FROM_DEFENSE = "damage_from_defense" # 방어력 기반 데미지


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
        logger.info("[EquipmentEffectManager] 초기화 시작")
        self.active_effects: Dict[str, List[EquipmentEffect]] = {}  # character_id -> effects
        self.effect_handlers: Dict[EffectType, Callable] = {}
        self._register_handlers()
        self._subscribe_events()
        logger.info(f"[EquipmentEffectManager] 초기화 완료 (핸들러 {len(self.effect_handlers)}개 등록)")

    def _subscribe_events(self):
        """이벤트 구독"""
        logger.info("[EquipmentEffectManager] 이벤트 구독 시작")
        event_bus.subscribe(Events.EQUIPMENT_EQUIPPED, self._on_equipment_equipped)
        event_bus.subscribe(Events.EQUIPMENT_UNEQUIPPED, self._on_equipment_unequipped)
        event_bus.subscribe(Events.COMBAT_DAMAGE_DEALT, self._on_damage_dealt)
        event_bus.subscribe(Events.COMBAT_DAMAGE_TAKEN, self._on_damage_taken)
        event_bus.subscribe(Events.COMBAT_TURN_START, self._on_turn_start)
        event_bus.subscribe(Events.COMBAT_TURN_END, self._on_turn_end)
        logger.info("[EquipmentEffectManager] 이벤트 구독 완료")

    def _register_handlers(self):
        """효과 핸들러 등록"""
        logger.debug(f"[_register_handlers] 핸들러 등록 시작")
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
            # CRITICAL_RATE는 CRITICAL_CHANCE와 동일하게 처리 (호환성)
            EffectType.CRITICAL_CHANCE: self._handle_critical_chance,
            EffectType.CRITICAL_RATE: self._handle_critical_chance,
            EffectType.DODGE_CHANCE: self._handle_dodge_chance,
            EffectType.BLOCK_CHANCE: self._handle_block_chance,
            EffectType.MULTI_STRIKE: self._handle_multi_strike,
            # HEALING_BONUS는 HEAL_BOOST와 동일하게 처리
            EffectType.HEAL_BOOST: self._handle_heal_boost,
            EffectType.HEALING_BONUS: self._handle_heal_boost,
            # OVERHEAL_SHIELD는 OVERHEAL과 동일하게 처리
            EffectType.OVERHEAL: self._handle_overheal,
            EffectType.OVERHEAL_SHIELD: self._handle_overheal,
            # 상태 면역 효과 (핸들러 없으면 로그만)
            EffectType.STATUS_IMMUNITY: self._handle_status_immunity,
            EffectType.POISON_IMMUNITY: self._handle_status_immunity,
            EffectType.STUN_IMMUNITY: self._handle_status_immunity,
            EffectType.SILENCE_IMMUNITY: self._handle_status_immunity,
            EffectType.BURN_IMMUNITY: self._handle_status_immunity,
            EffectType.FREEZE_IMMUNITY: self._handle_status_immunity,
            # 더 많은 핸들러...
            # 추가 효과 핸들러 (기본적으로 로그만)
            EffectType.ON_KILL_HEAL: self._handle_on_kill_heal,
            EffectType.ELEMENT: self._handle_element,
            EffectType.STATUS_BURN: self._handle_status_effect,
            EffectType.DEBUFF_SLOW: self._handle_status_effect,
            EffectType.STATUS_SHOCK: self._handle_status_effect,
            EffectType.DEBUFF_SILENCE: self._handle_status_effect,
            EffectType.CHAIN_LIGHTNING: self._handle_chain_lightning,
            EffectType.ARMOR_PENETRATION: self._handle_armor_penetration,
            EffectType.MP_STEAL: self._handle_mp_steal,
            EffectType.BONUS_VS_UNDEAD: self._handle_bonus_vs_undead,
            EffectType.HEAL_ON_HIT: self._handle_heal_on_hit,
            EffectType.ACCURACY_BONUS: self._handle_accuracy_bonus,
            EffectType.DOUBLE_STRIKE: self._handle_double_strike,
            EffectType.STRIKE_COUNT: self._handle_strike_count,
            EffectType.STUN_CHANCE: self._handle_stun_chance,
            EffectType.DAMAGE_FROM_DEFENSE: self._handle_damage_from_defense,
        }
        logger.info(f"[_register_handlers] 핸들러 등록 완료: {len(self.effect_handlers)}개 (VISION_BONUS 포함: {EffectType.VISION_BONUS in self.effect_handlers})")
        if EffectType.VISION_BONUS in self.effect_handlers:
            logger.info(f"[_register_handlers] VISION_BONUS 핸들러: {self.effect_handlers[EffectType.VISION_BONUS]}")

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

        logger.debug(f"[장비 착용 이벤트] character={character.name if character else None}, item={getattr(item, 'name', None) if item else None}")

        if not character or not item:
            logger.warning(f"[장비 착용 이벤트] character 또는 item이 None입니다")
            return

        # 캐릭터 ID (name 사용)
        character_id = character.name
        item_name = getattr(item, 'name', '알 수 없는 아이템')
        unique_effect = getattr(item, 'unique_effect', None)

        logger.debug(f"[장비 착용] {character.name} - {item_name} (unique_effect: {unique_effect})")

        # vision_bonus 재계산: 먼저 초기화하고 현재 장착된 모든 장비의 vision_bonus를 다시 계산
        if hasattr(character, "vision_bonus"):
            character.vision_bonus = 0

        # 현재 장착된 모든 장비의 vision_bonus 효과 재계산
        if hasattr(character, "equipment"):
            total_vision_bonus = 0
            for slot, equipped_item in character.equipment.items():
                if equipped_item:
                    # 장착된 장비의 vision_bonus 효과 찾기
                    item_effects = []
                    if hasattr(equipped_item, "special_effects") and equipped_item.special_effects:
                        item_effects = equipped_item.special_effects
                    elif hasattr(equipped_item, "unique_effect") and equipped_item.unique_effect:
                        item_effects = parse_unique_effects(equipped_item.unique_effect)

                    for eff in item_effects:
                        if eff.effect_type == EffectType.VISION_BONUS and eff.trigger == EffectTrigger.ON_EQUIP:
                            total_vision_bonus += int(eff.value)

            character.vision_bonus = total_vision_bonus
            if total_vision_bonus > 0:
                logger.debug(f"{character.name} vision_bonus 재계산 완료: 총 +{total_vision_bonus}")

        # 아이템의 특수 효과 파싱 및 적용
        effects = []

        # 1. special_effects 리스트가 있으면 그것을 사용
        if hasattr(item, "special_effects") and item.special_effects:
            effects = item.special_effects
            logger.debug(f"[장비 착용] special_effects 사용: {len(effects)}개")
        # 2. unique_effect 문자열이 있으면 파싱
        elif hasattr(item, "unique_effect") and item.unique_effect:
            logger.debug(f"[장비 착용] unique_effect 파싱 시작: '{item.unique_effect}'")
            effects = parse_unique_effects(item.unique_effect)
            logger.debug(f"[장비 착용] unique_effect 파싱 완료: {len(effects)}개 효과")
            for i, eff in enumerate(effects):
                logger.debug(f"  효과 {i+1}: {eff.effect_type.value if hasattr(eff.effect_type, 'value') else eff.effect_type} (트리거: {eff.trigger.value if hasattr(eff.trigger, 'value') else eff.trigger}, 값: {eff.value})")

        # 효과 적용
        for effect in effects:
            # 효과에 source_id 추가 (제거용)
            effect.source_id = getattr(item, 'item_id', item.name)
            self.add_effect(character_id, effect)

            # ON_EQUIP 트리거 효과 즉시 실행 (vision_bonus는 이미 재계산했으므로 스킵)
            if effect.trigger == EffectTrigger.ON_EQUIP:
                if effect.effect_type == EffectType.VISION_BONUS:
                    # vision_bonus는 이미 재계산했으므로 스킵
                    pass
                else:
                    logger.debug(f"ON_EQUIP 효과 실행: {character.name} - {effect.effect_type.value} (값: {effect.value})")
                    try:
                        self._execute_effect(character, effect, {})
                    except Exception as e:
                        logger.error(f"ON_EQUIP 효과 실행 중 에러: {e}", exc_info=True)

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
        
        # vision_bonus 재계산: 장비 해제 후 현재 장착된 모든 장비의 vision_bonus를 다시 계산
        if hasattr(character, "vision_bonus"):
            character.vision_bonus = 0

        # 현재 장착된 모든 장비의 vision_bonus 효과 재계산
        if hasattr(character, "equipment"):
            total_vision_bonus = 0
            for slot, equipped_item in character.equipment.items():
                if equipped_item:
                    # 장착된 장비의 vision_bonus 효과 찾기
                    item_effects = []
                    if hasattr(equipped_item, "special_effects") and equipped_item.special_effects:
                        item_effects = equipped_item.special_effects
                    elif hasattr(equipped_item, "unique_effect") and equipped_item.unique_effect:
                        item_effects = parse_unique_effects(equipped_item.unique_effect)

                    for eff in item_effects:
                        if eff.effect_type == EffectType.VISION_BONUS and eff.trigger == EffectTrigger.ON_EQUIP:
                            total_vision_bonus += int(eff.value)

            character.vision_bonus = total_vision_bonus
            if total_vision_bonus > 0:
                logger.debug(f"{character.name} vision_bonus 재계산 완료 (장비 해제 후): 총 +{total_vision_bonus}")

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
        try:
            # effect_type이 EffectType enum인지 확인
            if not isinstance(effect.effect_type, EffectType):
                logger.error(f"잘못된 effect_type 타입: {type(effect.effect_type)}, 값: {effect.effect_type}")
                return
            
            handler = self.effect_handlers.get(effect.effect_type)
            if handler:
                logger.debug(f"효과 핸들러 실행: {character.name} - {effect.effect_type.value} (값: {effect.value})")
                handler(character, effect, context)
            else:
                logger.warning(f"핸들러 없음: {effect.effect_type} (타입: {type(effect.effect_type)}, 등록된 핸들러: {list(self.effect_handlers.keys())[:5]}...)")
        except AttributeError as e:
            logger.error(f"효과 실행 중 에러: {e}, effect_type: {effect.effect_type}, 타입: {type(effect.effect_type)}")
            # effect_type이 문자열인 경우 EffectType enum으로 변환 시도
            if isinstance(effect.effect_type, str):
                try:
                    effect.effect_type = EffectType(effect.effect_type)
                    handler = self.effect_handlers.get(effect.effect_type)
                    if handler:
                        logger.info(f"효과 핸들러 실행 (변환 후): {character.name} - {effect.effect_type.value} (값: {effect.value})")
                        handler(character, effect, context)
                except (ValueError, AttributeError) as e2:
                    logger.error(f"EffectType 변환 실패: {e2}, 문자열: {effect.effect_type}")
        except Exception as e:
            logger.error(f"효과 실행 중 예상치 못한 에러: {e}, effect_type: {effect.effect_type}")

    # === 개별 효과 핸들러 ===

    def _handle_vision_bonus(self, character: Any, effect: EquipmentEffect, context: Dict):
        """시야 증가"""
        if not hasattr(character, "vision_bonus"):
            character.vision_bonus = 0
        character.vision_bonus += int(effect.value)
        logger.info(f"{character.name} 시야 +{effect.value} (현재: {character.vision_bonus})")
        
    def _handle_critical_chance(self, character: Any, effect: EquipmentEffect, context: Dict):
        """크리티컬 확률 증가 (CRITICAL_RATE와 CRITICAL_CHANCE 모두 처리)"""
        # 크리티컬 확률은 StatManager나 다른 시스템에서 처리될 수 있음
        # 여기서는 로그만 남김
        logger.debug(f"{character.name} 크리티컬 확률 +{effect.value * 100:.1f}%")

    def _handle_dodge_chance(self, character: Any, effect: EquipmentEffect, context: Dict):
        """회피 확률 증가"""
        # 캐릭터에 회피 확률 보너스 저장
        if not hasattr(character, "dodge_chance_bonus"):
            character.dodge_chance_bonus = 0
        character.dodge_chance_bonus += effect.value
        logger.debug(f"{character.name} 회피 확률 +{effect.value * 100:.1f}% (총: {character.dodge_chance_bonus * 100:.1f}%)")

    def _handle_block_chance(self, character: Any, effect: EquipmentEffect, context: Dict):
        """블록 확률 증가"""
        # 캐릭터에 블록 확률 보너스 저장
        if not hasattr(character, "block_chance_bonus"):
            character.block_chance_bonus = 0
        character.block_chance_bonus += effect.value
        logger.debug(f"{character.name} 블록 확률 +{effect.value * 100:.1f}% (총: {character.block_chance_bonus * 100:.1f}%)")

    def _handle_multi_strike(self, character: Any, effect: EquipmentEffect, context: Dict):
        """연속 공격 확률"""
        # 캐릭터에 연속 공격 확률 저장
        if not hasattr(character, "multi_strike_chance"):
            character.multi_strike_chance = 0
        character.multi_strike_chance += effect.value
        logger.debug(f"{character.name} 연속 공격 확률 +{effect.value * 100:.1f}% (총: {character.multi_strike_chance * 100:.1f}%)")
        
    def _handle_heal_boost(self, character: Any, effect: EquipmentEffect, context: Dict):
        """회복량 보너스 (HEAL_BOOST와 HEALING_BONUS 모두 처리)"""
        # 회복량 보너스는 전투 시스템에서 처리될 수 있음
        # 여기서는 로그만 남김
        logger.debug(f"{character.name} 회복량 보너스 +{effect.value * 100:.1f}%")
        
    def _handle_overheal(self, character: Any, effect: EquipmentEffect, context: Dict):
        """과다 회복 → 실드 (OVERHEAL과 OVERHEAL_SHIELD 모두 처리)"""
        # 과다 회복 효과는 전투 시스템에서 처리될 수 있음
        # 여기서는 로그만 남김
        logger.debug(f"{character.name} 과다 회복 → 실드 효과 활성화")
        
    def _handle_status_immunity(self, character: Any, effect: EquipmentEffect, context: Dict):
        """상태 면역 (POISON_IMMUNITY, STUN_IMMUNITY 등)"""
        # 상태 면역 효과는 전투 시스템에서 처리될 수 있음
        # 여기서는 로그만 남김
        logger.debug(f"{character.name} {effect.effect_type.value} 효과 활성화")

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

    # === 추가 효과 핸들러 ===

    def _handle_on_kill_heal(self, character: Any, effect: EquipmentEffect, context: Dict):
        """처치 시 회복"""
        heal_amount = int(effect.value)
        if hasattr(character, "hp") and hasattr(character, "max_hp"):
            character.hp = min(character.max_hp, character.hp + heal_amount)
            logger.info(f"{character.name} 처치 회복: +{heal_amount} HP")

    def _handle_element(self, character: Any, effect: EquipmentEffect, context: Dict):
        """속성 부여"""
        if not hasattr(character, "element"):
            character.element = effect.value
        else:
            character.element = effect.value  # 덮어쓰기
        logger.debug(f"{character.name} 속성 부여: {effect.value}")

    def _handle_status_effect(self, character: Any, effect: EquipmentEffect, context: Dict):
        """상태 효과 부여"""
        from src.combat.status_effects import StatusType, StatusEffect

        # 확률 계산 (effect.value는 0-1 사이의 확률)
        if effect.value < 1.0:  # 1.0 미만이면 확률 적용
            import random
            if random.random() > effect.value:
                return  # 확률 실패

        # 효과 타입 매핑
        status_mapping = {
            EffectType.STATUS_BURN: StatusType.BURN,
            EffectType.DEBUFF_SLOW: StatusType.SLOW,
            EffectType.STATUS_SHOCK: StatusType.SHOCK,
            EffectType.DEBUFF_SILENCE: StatusType.SILENCE,
        }

        target = context.get("target")
        if not target or not hasattr(target, "status_manager"):
            return

        if effect.effect_type in status_mapping:
            status_type = status_mapping[effect.effect_type]

            # 이미 같은 상태 효과가 있는지 확인
            if not target.status_manager.has_status(status_type):
                # 기본 지속시간 설정
                duration = 3  # 3턴 기본
                intensity = 1.0

                # StatusEffect 생성 및 적용
                status_effect = StatusEffect(
                    name=f"{status_type.value}",
                    status_type=status_type,
                    duration=duration,
                    intensity=intensity
                )

                target.status_manager.add_status(status_effect)
                logger.info(f"{character.name} → {target.name}: {status_type.value} 상태 효과 적용 ({duration}턴)")

    def _handle_chain_lightning(self, character: Any, effect: EquipmentEffect, context: Dict):
        """체인 라이트닝"""
        # 캐릭터에 체인 라이트닝 속성 저장 (데미지 계산 시 사용)
        if not hasattr(character, "chain_lightning_chance"):
            character.chain_lightning_chance = 0
        character.chain_lightning_chance += effect.value

        logger.debug(f"{character.name} 체인 라이트닝 확률: {effect.value * 100:.1f}% (총: {character.chain_lightning_chance * 100:.1f}%)")

    def _handle_armor_penetration(self, character: Any, effect: EquipmentEffect, context: Dict):
        """방어 관통"""
        # 캐릭터에 방어 관통 속성 저장 (데미지 계산 시 사용)
        if not hasattr(character, "armor_penetration"):
            character.armor_penetration = 0
        character.armor_penetration += effect.value

        logger.debug(f"{character.name} 방어 관통: {effect.value * 100:.1f}% (총: {character.armor_penetration * 100:.1f}%)")

    def _handle_mp_steal(self, character: Any, effect: EquipmentEffect, context: Dict):
        """MP 흡수"""
        target = context.get("target")
        if not target or not hasattr(target, "mp"):
            return

        # 백분율 기반 MP 흡수
        steal_amount = int(target.max_mp * effect.value)
        if steal_amount > 0 and target.mp > 0:
            actual_steal = min(steal_amount, target.mp)
            target.mp -= actual_steal
            character.mp = min(character.max_mp, character.mp + actual_steal)
            logger.info(f"{character.name} MP 흡수: {target.name}의 MP {actual_steal} 흡수")

    def _handle_bonus_vs_undead(self, character: Any, effect: EquipmentEffect, context: Dict):
        """언데드 상대 보너스 (데미지 계산 시 적용)"""
        # 이 효과는 실제 데미지 계산 시 적용되어야 함
        # 캐릭터에 언데드 보너스 저장
        if not hasattr(character, "bonus_vs_undead"):
            character.bonus_vs_undead = 0
        character.bonus_vs_undead += effect.value

        logger.debug(f"{character.name} 언데드 보너스: +{effect.value * 100:.1f}% (총: {character.bonus_vs_undead * 100:.1f}%)")

    def _handle_heal_on_hit(self, character: Any, effect: EquipmentEffect, context: Dict):
        """공격 시 회복"""
        heal_amount = int(effect.value)
        if hasattr(character, "hp") and hasattr(character, "max_hp"):
            character.hp = min(character.max_hp, character.hp + heal_amount)
            logger.info(f"{character.name} 공격 회복: +{heal_amount} HP")

    def _handle_accuracy_bonus(self, character: Any, effect: EquipmentEffect, context: Dict):
        """명중률 보너스"""
        # StatManager를 통해 명중률 보너스 적용
        if hasattr(character, "stat_manager"):
            from src.character.stats import Stats
            character.stat_manager.add_bonus(Stats.ACCURACY, f"equipment_accuracy_{id(effect)}", int(effect.value))
            logger.debug(f"{character.name} 명중률 보너스: +{effect.value}")
        else:
            # StatManager가 없는 경우 직접 속성 설정
            if not hasattr(character, "accuracy_bonus"):
                character.accuracy_bonus = 0
            character.accuracy_bonus += int(effect.value)
            logger.debug(f"{character.name} 명중률 보너스: +{effect.value} (총: {character.accuracy_bonus})")

    def _handle_double_strike(self, character: Any, effect: EquipmentEffect, context: Dict):
        """더블 스트라이크"""
        # 캐릭터에 더블 스트라이크 속성 저장
        character.double_strike = True
        logger.debug(f"{character.name} 더블 스트라이크 활성화")

    def _handle_strike_count(self, character: Any, effect: EquipmentEffect, context: Dict):
        """공격 횟수"""
        # 캐릭터에 공격 횟수 속성 저장 (예: "3-5" 형태의 문자열이면 파싱)
        if isinstance(effect.value, str) and "-" in effect.value:
            # 범위 형태 (예: "3-5")
            min_count, max_count = map(int, effect.value.split("-"))
            character.strike_count_range = (min_count, max_count)
            logger.debug(f"{character.name} 공격 횟수 범위: {min_count}-{max_count}")
        else:
            # 고정 값
            character.strike_count = int(effect.value)
            logger.debug(f"{character.name} 공격 횟수: {effect.value}")

    def _handle_stun_chance(self, character: Any, effect: EquipmentEffect, context: Dict):
        """스턴 확률"""
        from src.combat.status_effects import StatusType, StatusEffect

        # 확률 계산 (effect.value는 0-1 사이의 확률)
        if effect.value < 1.0:  # 1.0 미만이면 확률 적용
            import random
            if random.random() > effect.value:
                return  # 확률 실패

        target = context.get("target")
        if not target or not hasattr(target, "status_manager"):
            return

        # 스턴 상태 효과가 이미 있는지 확인
        if not target.status_manager.has_status(StatusType.STUN):
            # 기본 지속시간 설정
            duration = 2  # 스턴은 2턴으로 설정 (다른 상태보다 짧게)
            intensity = 1.0

            # StatusEffect 생성 및 적용
            status_effect = StatusEffect(
                name="스턴",
                status_type=StatusType.STUN,
                duration=duration,
                intensity=intensity
            )

            target.status_manager.add_status(status_effect)
            logger.info(f"{character.name} → {target.name}: 스턴 상태 효과 적용 ({duration}턴)")

    def _handle_damage_from_defense(self, character: Any, effect: EquipmentEffect, context: Dict):
        """방어력 기반 데미지"""
        # 캐릭터에 방어력 기반 데미지 속성 저장 (데미지 계산 시 사용)
        if not hasattr(character, "damage_from_defense"):
            character.damage_from_defense = 0
        character.damage_from_defense += effect.value

        logger.debug(f"{character.name} 방어력 기반 데미지: {effect.value * 100:.1f}% (총: {character.damage_from_defense * 100:.1f}%)")


# 전역 인스턴스
_equipment_effect_manager: Optional[EquipmentEffectManager] = None


def get_equipment_effect_manager() -> EquipmentEffectManager:
    """전역 장비 효과 관리자"""
    global _equipment_effect_manager
    if _equipment_effect_manager is None:
        logger.info("[get_equipment_effect_manager] EquipmentEffectManager 생성")
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
        logger.debug(f"[parse_unique_effects] 빈 문자열")
        return []

    effects = []
    logger.debug(f"[parse_unique_effects] 파싱 시작: '{unique_effect_string}'")

    # | 로 분리
    for effect_str in unique_effect_string.split("|"):
        effect_str = effect_str.strip()
        if not effect_str:
            continue
        if ":" not in effect_str:
            logger.warning(f"[parse_unique_effects] ':' 구분자가 없음: '{effect_str}'")
            # 값이 없는 효과는 기본값 1.0으로 설정 (토글형 효과)
            effect_name = effect_str.strip()
            value = 1.0
            logger.debug(f"[parse_unique_effects] 값 없는 효과 처리: '{effect_name}' = {value} (기본값)")
        else:
            effect_name, value_str = effect_str.split(":", 1)
            effect_name = effect_name.strip()
            value_str = value_str.strip()
            logger.debug(f"[parse_unique_effects] 효과 파싱: '{effect_name}' = '{value_str}'")

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
            "block_chance": (EffectType.BLOCK_CHANCE, EffectTrigger.PASSIVE),
            "multi_strike": (EffectType.MULTI_STRIKE, EffectTrigger.PASSIVE),
            "counter_attack": (EffectType.COUNTER_ATTACK, EffectTrigger.ON_DAMAGED),
            "first_strike": (EffectType.FIRST_STRIKE, EffectTrigger.PASSIVE),

            # Healing
            "hp_regen": (EffectType.HP_REGEN, EffectTrigger.ON_TURN_END),
            "mp_regen": (EffectType.MP_REGEN, EffectTrigger.ON_TURN_END),
            "heal_boost": (EffectType.HEAL_BOOST, EffectTrigger.PASSIVE),
            "healing_bonus": (EffectType.HEALING_BONUS, EffectTrigger.PASSIVE),
            "overheal": (EffectType.OVERHEAL, EffectTrigger.PASSIVE),
            "overheal_shield": (EffectType.OVERHEAL_SHIELD, EffectTrigger.PASSIVE),

            # Status
            "status_immunity": (EffectType.STATUS_IMMUNITY, EffectTrigger.PASSIVE),
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

            # === 추가 효과 (아이템 시스템에서 사용) ===
            "on_kill_heal": (EffectType.ON_KILL_HEAL, EffectTrigger.ON_KILL),
            "element": (EffectType.ELEMENT, EffectTrigger.PASSIVE),
            "status_burn": (EffectType.STATUS_BURN, EffectTrigger.ON_HIT),
            "debuff_slow": (EffectType.DEBUFF_SLOW, EffectTrigger.ON_HIT),
            "status_shock": (EffectType.STATUS_SHOCK, EffectTrigger.ON_HIT),
            "debuff_silence": (EffectType.DEBUFF_SILENCE, EffectTrigger.ON_HIT),
            "chain_lightning": (EffectType.CHAIN_LIGHTNING, EffectTrigger.ON_HIT),
            "armor_penetration": (EffectType.ARMOR_PENETRATION, EffectTrigger.PASSIVE),
            "mp_steal": (EffectType.MP_STEAL, EffectTrigger.ON_HIT),
            "bonus_vs_undead": (EffectType.BONUS_VS_UNDEAD, EffectTrigger.PASSIVE),
            "heal_on_hit": (EffectType.HEAL_ON_HIT, EffectTrigger.ON_HIT),
            "accuracy_bonus": (EffectType.ACCURACY_BONUS, EffectTrigger.PASSIVE),
            "double_strike": (EffectType.DOUBLE_STRIKE, EffectTrigger.ON_EQUIP),
            "strike_count": (EffectType.STRIKE_COUNT, EffectTrigger.PASSIVE),
            "stun_chance": (EffectType.STUN_CHANCE, EffectTrigger.ON_HIT),
            "damage_from_defense": (EffectType.DAMAGE_FROM_DEFENSE, EffectTrigger.PASSIVE),
        }

        if effect_name in effect_mapping:
            effect_type, trigger = effect_mapping[effect_name]
            effect = EquipmentEffect(
                effect_type=effect_type,
                trigger=trigger,
                value=value,
                description=f"{effect_name}: {value}"
            )
            effects.append(effect)
            logger.debug(f"[parse_unique_effects] 효과 생성: {effect_type.value} (트리거: {trigger.value}, 값: {value})")
        else:
            logger.warning(f"[parse_unique_effects] 알 수 없는 효과 이름: '{effect_name}'")

    logger.debug(f"[parse_unique_effects] 파싱 완료: {len(effects)}개 효과 생성")
    return effects
