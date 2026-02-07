"""
랜덤 이벤트 시스템

던전에서 발생하는 다양한 랜덤 이벤트
"""

import random
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


class EventType(Enum):
    """이벤트 타입"""
    MERCHANT = "merchant"  # 상인 조우
    BLESSING = "blessing"  # 축복
    CURSE = "curse"  # 저주
    TREASURE = "treasure"  # 보물
    CHALLENGE = "challenge"  # 도전
    MYSTERY = "mystery"  # 미스터리 상자
    FOUNTAIN = "fountain"  # 마법의 분수
    SHRINE = "shrine"  # 제단
    GAMBLE = "gamble"  # 도박
    RIDDLE = "riddle"  # 수수께끼


@dataclass
class RandomEvent:
    """랜덤 이벤트"""
    event_id: str
    event_type: EventType
    name: str
    description: str
    rarity: float  # 0.0 ~ 1.0 (낮을수록 희귀)

    # 이벤트 데이터
    data: Dict[str, Any] = None

    def __post_init__(self):
        if self.data is None:
            self.data = {}


class RandomEventSystem:
    """랜덤 이벤트 시스템"""

    def __init__(self):
        self.events: List[RandomEvent] = []
        self._initialize_events()

    def _initialize_events(self):
        """이벤트 초기화"""

        # === 상인 이벤트 ===
        self.events.append(RandomEvent(
            event_id="merchant_weapons",
            event_type=EventType.MERCHANT,
            name="떠돌이 무기상인",
            description="\"좋은 무기가 필요하신가요?\"",
            rarity=0.6,
            data={
                "shop_type": "weapons",
                "discount": 0.9  # 10% 할인
            }
        ))

        self.events.append(RandomEvent(
            event_id="merchant_potions",
            event_type=EventType.MERCHANT,
            name="포션 장수",
            description="\"체력 회복은 기본! 마나 포션도 있어요!\"",
            rarity=0.7,
            data={
                "shop_type": "potions",
                "discount": 0.85  # 15% 할인
            }
        ))

        self.events.append(RandomEvent(
            event_id="merchant_rare",
            event_type=EventType.MERCHANT,
            name="수상한 상인",
            description="\"특별한 물건들이 있소... 값은 비싸지만.\"",
            rarity=0.2,
            data={
                "shop_type": "rare",
                "discount": 1.5  # 50% 더 비쌈
            }
        ))

        # === 축복 이벤트 ===
        self.events.append(RandomEvent(
            event_id="blessing_hp",
            event_type=EventType.BLESSING,
            name="생명의 축복",
            description="신성한 빛이 당신을 감싸며 활력을 되찾습니다.",
            rarity=0.5,
            data={
                "effect": "heal_full",
                "bonus_hp": 20
            }
        ))

        self.events.append(RandomEvent(
            event_id="blessing_stats",
            event_type=EventType.BLESSING,
            name="전사의 축복",
            description="전투의 신이 당신에게 힘을 부여합니다.",
            rarity=0.4,
            data={
                "effect": "stat_boost",
                "stat": "strength",
                "amount": 5,
                "duration": 10  # 10층 동안
            }
        ))

        self.events.append(RandomEvent(
            event_id="blessing_exp",
            event_type=EventType.BLESSING,
            name="지혜의 축복",
            description="경험이 풍부해지는 느낌입니다.",
            rarity=0.5,
            data={
                "effect": "exp_boost",
                "multiplier": 1.5,
                "duration": 5  # 5층 동안
            }
        ))

        # === 저주 이벤트 ===
        self.events.append(RandomEvent(
            event_id="curse_weakness",
            event_type=EventType.CURSE,
            name="약화의 저주",
            description="어둠의 기운이 당신의 힘을 빼앗아갑니다...",
            rarity=0.3,
            data={
                "effect": "stat_debuff",
                "stat": "strength",
                "amount": -3,
                "duration": 5
            }
        ))

        self.events.append(RandomEvent(
            event_id="curse_hunger",
            event_type=EventType.CURSE,
            name="굶주림의 저주",
            description="갑자기 극심한 배고픔이 엄습합니다...",
            rarity=0.3,
            data={
                "effect": "damage",
                "hp_loss": 30
            }
        ))

        # === 보물 이벤트 ===
        self.events.append(RandomEvent(
            event_id="treasure_gold",
            event_type=EventType.TREASURE,
            name="숨겨진 금고",
            description="오래된 금고를 발견했습니다!",
            rarity=0.4,
            data={
                "reward": "gold",
                "amount_min": 200,
                "amount_max": 500
            }
        ))

        self.events.append(RandomEvent(
            event_id="treasure_equipment",
            event_type=EventType.TREASURE,
            name="잊혀진 무기고",
            description="고대의 무기고를 발견했습니다!",
            rarity=0.2,
            data={
                "reward": "equipment",
                "rarity": "rare",
                "count": 1
            }
        ))

        # === 도전 이벤트 ===
        self.events.append(RandomEvent(
            event_id="challenge_combat",
            event_type=EventType.CHALLENGE,
            name="전투 시험",
            description="\"용기를 증명하라!\" 강력한 적이 나타났습니다.",
            rarity=0.3,
            data={
                "challenge": "combat",
                "enemy_level_bonus": 3,
                "reward_multiplier": 2.0
            }
        ))

        self.events.append(RandomEvent(
            event_id="challenge_survival",
            event_type=EventType.CHALLENGE,
            name="생존 시험",
            description="함정이 가득한 방입니다. 조심히 통과하세요!",
            rarity=0.4,
            data={
                "challenge": "trap_room",
                "trap_count": 5,
                "reward": "gold",
                "reward_amount": 300
            }
        ))

        # === 미스터리 상자 ===
        self.events.append(RandomEvent(
            event_id="mystery_box",
            event_type=EventType.MYSTERY,
            name="미스터리 상자",
            description="이상한 상자가 있습니다. 열어볼까요?",
            rarity=0.5,
            data={
                "outcomes": [
                    {"type": "reward", "weight": 0.4, "data": {"gold": 200}},
                    {"type": "reward", "weight": 0.3, "data": {"item": "rare"}},
                    {"type": "curse", "weight": 0.2, "data": {"damage": 50}},
                    {"type": "nothing", "weight": 0.1, "data": {}}
                ]
            }
        ))

        # === 마법의 분수 ===
        self.events.append(RandomEvent(
            event_id="fountain_hp",
            event_type=EventType.FOUNTAIN,
            name="생명의 분수",
            description="맑은 물이 솟아나는 분수입니다.",
            rarity=0.6,
            data={
                "effect": "heal",
                "hp_restore": 100,
                "remove_debuffs": True
            }
        ))

        self.events.append(RandomEvent(
            event_id="fountain_mana",
            event_type=EventType.FOUNTAIN,
            name="마나의 분수",
            description="푸른 빛이 나는 분수입니다.",
            rarity=0.5,
            data={
                "effect": "restore_mp",
                "mp_restore": 100,
                "max_mp_bonus": 10
            }
        ))

        # === 제단 ===
        self.events.append(RandomEvent(
            event_id="shrine_sacrifice",
            event_type=EventType.SHRINE,
            name="희생의 제단",
            description="\"현재 HP의 30%를 바치면 힘을 얻으리라...\"",
            rarity=0.3,
            data={
                "cost": "hp_percentage",
                "cost_amount": 0.3,
                "reward": "stat_permanent",
                "stat": "strength",
                "amount": 2
            }
        ))

        # === 도박 ===
        self.events.append(RandomEvent(
            event_id="gamble_coin_flip",
            event_type=EventType.GAMBLE,
            name="동전 던지기",
            description="\"골드를 걸고 동전을 던지시겠습니까?\"",
            rarity=0.4,
            data={
                "type": "coin_flip",
                "bet_amount": 100,
                "win_multiplier": 2.0,
                "win_chance": 0.5
            }
        ))

        # === 수수께끼 ===
        self.events.append(RandomEvent(
            event_id="riddle_easy",
            event_type=EventType.RIDDLE,
            name="현자의 수수께끼",
            description="\"수수께끼를 풀면 보상을 주리다.\"",
            rarity=0.3,
            data={
                "difficulty": "easy",
                "reward": "exp",
                "reward_amount": 500
            }
        ))

    def get_random_event(self, floor: int, rarity_modifier: float = 1.0) -> Optional[RandomEvent]:
        """
        랜덤 이벤트 획득

        Args:
            floor: 현재 층수
            rarity_modifier: 희귀도 수정자 (높을수록 희귀한 이벤트 발생)

        Returns:
            랜덤 이벤트 또는 None
        """
        # 층수에 따라 이벤트 발생 확률 증가
        base_chance = min(0.15 + (floor * 0.005), 0.4)  # 15% ~ 40%

        if random.random() > base_chance:
            return None

        # 가중치 계산
        weights = []
        for event in self.events:
            # 희귀도와 수정자를 고려한 가중치
            weight = event.rarity * rarity_modifier
            weights.append(weight)

        # 가중치 기반 랜덤 선택
        if sum(weights) == 0:
            return None

        selected_event = random.choices(self.events, weights=weights, k=1)[0]
        return selected_event

    def execute_event(self, event: RandomEvent, party: List[Any], inventory: Any) -> Dict[str, Any]:
        """
        이벤트 실행

        Args:
            event: 실행할 이벤트
            party: 파티
            inventory: 인벤토리

        Returns:
            실행 결과
        """
        result = {
            "success": True,
            "message": event.description,
            "effects": []
        }

        # 이벤트 타입별 처리
        if event.event_type == EventType.BLESSING:
            result["effects"].extend(self._handle_blessing(event, party))

        elif event.event_type == EventType.CURSE:
            result["effects"].extend(self._handle_curse(event, party))

        elif event.event_type == EventType.TREASURE:
            result["effects"].extend(self._handle_treasure(event, inventory))

        elif event.event_type == EventType.FOUNTAIN:
            result["effects"].extend(self._handle_fountain(event, party))

        # 다른 이벤트는 UI에서 처리

        return result

    def _handle_blessing(self, event: RandomEvent, party: List[Any]) -> List[str]:
        """축복 처리"""
        effects = []
        effect_type = event.data.get("effect")

        if effect_type == "heal_full":
            for member in party:
                if hasattr(member, 'heal'):
                    member.heal(member.max_hp)
            effects.append("파티 전체 HP 완전 회복!")

        elif effect_type == "stat_boost":
            stat = event.data.get("stat")
            amount = event.data.get("amount")
            effects.append(f"{stat} +{amount} (일시적)")

        elif effect_type == "exp_boost":
            multiplier = event.data.get("multiplier")
            effects.append(f"경험치 획득 {int((multiplier - 1) * 100)}% 증가!")

        return effects

    def _handle_curse(self, event: RandomEvent, party: List[Any]) -> List[str]:
        """저주 처리"""
        effects = []
        effect_type = event.data.get("effect")

        if effect_type == "damage":
            hp_loss = event.data.get("hp_loss")
            for member in party:
                if hasattr(member, 'take_damage'):
                    member.take_damage(hp_loss)
            effects.append(f"파티 전체 {hp_loss} HP 손실!")

        elif effect_type == "stat_debuff":
            stat = event.data.get("stat")
            amount = event.data.get("amount")
            effects.append(f"{stat} {amount} (일시적)")

        return effects

    def _handle_treasure(self, event: RandomEvent, inventory: Any) -> List[str]:
        """보물 처리"""
        effects = []
        reward = event.data.get("reward")

        if reward == "gold":
            amount = random.randint(
                event.data.get("amount_min", 100),
                event.data.get("amount_max", 300)
            )
            if inventory:
                inventory.gold += amount
            effects.append(f"골드 {amount}G 획득!")

        elif reward == "equipment":
            effects.append("희귀 장비 획득!")

        return effects

    def _handle_fountain(self, event: RandomEvent, party: List[Any]) -> List[str]:
        """분수 처리"""
        effects = []
        effect_type = event.data.get("effect")

        if effect_type == "heal":
            hp_restore = event.data.get("hp_restore")
            for member in party:
                if hasattr(member, 'heal'):
                    member.heal(hp_restore)
            effects.append(f"파티 전체 {hp_restore} HP 회복!")

            if event.data.get("remove_debuffs"):
                effects.append("모든 디버프 제거!")

        elif effect_type == "restore_mp":
            mp_restore = event.data.get("mp_restore")
            for member in party:
                if hasattr(member, 'current_mp'):
                    member.current_mp = min(member.max_mp, member.current_mp + mp_restore)
            effects.append(f"파티 전체 {mp_restore} MP 회복!")

        return effects


# 전역 인스턴스
random_event_system = RandomEventSystem()
