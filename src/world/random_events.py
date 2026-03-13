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
            if inventory is not None:
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


# ============================================================
# YAML 기반 랜덤 이벤트 매니저 (던전/지역 탐험용)
# ============================================================

@dataclass
class EventChoice:
    """이벤트 선택지"""
    text: str
    requirements: Dict[str, Any]
    outcomes: List[Dict[str, Any]]


@dataclass
class YamlRandomEvent:
    """YAML 기반 랜덤 이벤트"""
    id: str
    name: str
    category: str
    description: str
    min_floor: int
    max_floor: int
    weight: int
    cooldown_steps: int
    once_only: bool
    choices: List[EventChoice]
    region: str = ""


@dataclass
class EventOutcome:
    """이벤트 결과"""
    message: str = ""
    gold: int = 0
    exp: int = 0
    items: List[str] = None
    affinity_gain: int = 0
    damage: int = 0
    damage_percent: int = 0
    heal: int = 0
    heal_percent: int = 0
    buff_id: str = ""
    debuff_id: str = ""
    duration: int = 0
    event_type: str = "neutral"

    def __post_init__(self):
        if self.items is None:
            self.items = []


# RPG 지역 ID → 이벤트 바이옴 매핑
REGION_TO_EVENT_BIOME: Dict[str, str] = {
    "forgotten_forest": "forest",
    "twilight_desert": "desert",
    "abyss_cavern": "cave",
    "storm_plateau": "mountain",
    "eternal_glacier": "snowfield",
    "war_lands": "wasteland",
    "starlight_throne": "stellar",
}

# 던전 바이옴 → 이벤트 region 매핑
DUNGEON_BIOME_TO_EVENT_REGION: Dict[str, str] = {
    "biome_0": "forest",
    "biome_1": "desert",
    "biome_2": "cave",
    "biome_3": "coast",
    "biome_4": "mountain",
    "biome_5": "snowfield",
    "biome_6": "volcano",
    "biome_7": "wasteland",
    "biome_8": "town",
    "biome_9": "stellar",
}


class RandomEventManager:
    """YAML 기반 랜덤 이벤트 매니저"""

    _instance = None

    def __init__(self):
        import time as _time
        self._dungeon_events: List[YamlRandomEvent] = []
        self._region_events: List[YamlRandomEvent] = []
        self._steps_since_event = 0
        self._total_steps = 0
        self._event_cooldowns: Dict[str, int] = {}  # event_id -> steps remaining
        self._completed_once_only: set = set()
        self._hourly_event_times: List[float] = []  # 최근 이벤트 발생 시각 (unix timestamp)
        self._max_events_per_hour: int = 5  # 시간당 최대 이벤트 수
        self._events_per_floor: dict = {}  # 층당 이벤트 발생 횟수
        self._load_events()

    def _load_events(self):
        """YAML에서 이벤트 로드"""
        import os
        try:
            import yaml
        except ImportError:
            return

        base = os.path.join(os.path.dirname(__file__), "..", "..", "data", "random_events")

        dungeon_path = os.path.join(base, "dungeon_events.yaml")
        if os.path.exists(dungeon_path):
            with open(dungeon_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for ev in data.get("dungeon_events", []):
                self._dungeon_events.append(self._parse_event(ev))

        region_path = os.path.join(base, "region_events.yaml")
        if os.path.exists(region_path):
            with open(region_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            for ev in data.get("region_events", []):
                self._region_events.append(self._parse_event(ev))

    def _parse_event(self, data: Dict[str, Any]) -> YamlRandomEvent:
        choices = []
        for c in data.get("choices", []):
            choices.append(EventChoice(
                text=c.get("text", ""),
                requirements=c.get("requirements", {}),
                outcomes=c.get("outcomes", []),
            ))
        return YamlRandomEvent(
            id=data.get("id", ""),
            name=data.get("name", ""),
            category=data.get("category", ""),
            description=data.get("description", ""),
            min_floor=data.get("min_floor", 0),
            max_floor=data.get("max_floor", 99),
            weight=data.get("weight", 10),
            cooldown_steps=data.get("cooldown_steps", 100),
            once_only=data.get("once_only", False),
            choices=choices,
            region=data.get("region", ""),
        )

    def on_step(self, floor: int, region: Optional[str], party_jobs: List[str], biome: Optional[str] = None) -> Optional[YamlRandomEvent]:
        """한 걸음마다 호출. 이벤트 발생 시 반환, 아니면 None

        Args:
            floor: 현재 층수
            region: RPG 모드 지역 ID (forgotten_forest 등) 또는 None
            party_jobs: 파티 직업 목록
            biome: 던전 바이옴 (biome_0~9) 또는 None
        """
        self._total_steps += 1
        self._steps_since_event += 1

        # 쿨다운 감소
        expired = []
        for eid, remaining in self._event_cooldowns.items():
            self._event_cooldowns[eid] = remaining - 1
            if self._event_cooldowns[eid] <= 0:
                expired.append(eid)
        for eid in expired:
            del self._event_cooldowns[eid]

        # 시간당 최대 5회 제한 (1시간 = 3600초)
        import time as _time
        now = _time.time()
        self._hourly_event_times = [t for t in self._hourly_event_times if now - t < 3600]
        if len(self._hourly_event_times) >= self._max_events_per_hour:
            return None

        # 층당 최대 5회 제한
        floor_key = f"floor_{floor}"
        if self._events_per_floor.get(floor_key, 0) >= 5:
            return None

        # 최소 간격: RPG 모드(대형 맵)는 120스텝, 일반 던전/스토리(소형 맵)는 45스텝
        is_rpg = region is not None
        min_steps = 120 if is_rpg else 45
        if self._steps_since_event < min_steps:
            return None

        # 발생 확률 (기존 대비 1/3로 감소):
        # RPG는 0.33% 기본 + 0.033%/스텝 (최대 3.3%)
        # 일반 던전은 1% 기본 + 0.1%/스텝 (최대 5%)
        if is_rpg:
            chance = min(0.0033 + (self._steps_since_event - min_steps) * 0.00033, 0.033)
        else:
            chance = min(0.01 + (self._steps_since_event - min_steps) * 0.001, 0.05)
        if random.random() > chance:
            return None

        # 이벤트 풀 구성 - 바이옴/지역별 필터링
        event_region: Optional[str] = None
        raw_region: Optional[str] = region  # RPG 지역 ID 원본 (forgotten_forest 등)
        if region is not None:
            # RPG 오픈월드: region_id → 이벤트 바이옴 매핑
            event_region = REGION_TO_EVENT_BIOME.get(region, region)
            events = self._region_events
        elif biome is not None:
            # 던전 모드 + 바이옴: 바이옴에 맞는 지역 이벤트 사용
            event_region = DUNGEON_BIOME_TO_EVENT_REGION.get(biome)
            events = self._region_events if event_region else self._dungeon_events
        else:
            # 일반 던전 모드
            events = self._dungeon_events

        pool = []
        for ev in events:
            if ev.id in self._completed_once_only:
                continue
            if ev.id in self._event_cooldowns:
                continue
            if floor < ev.min_floor or floor > ev.max_floor:
                continue
            # 바이옴/지역 필터링: "all"이나 빈 문자열은 모든 지역에서 발생
            if ev.region and ev.region not in ("all", ""):
                # RPG 지역 ID 직접 매칭 (forgotten_forest 등) 또는 바이옴 매칭 (forest 등)
                if event_region and ev.region != event_region and ev.region != raw_region:
                    continue
            pool.append(ev)

        # 바이옴 매칭 이벤트가 없으면 던전 이벤트로 폴백
        if not pool and event_region:
            for ev in self._dungeon_events:
                if ev.id in self._completed_once_only:
                    continue
                if ev.id in self._event_cooldowns:
                    continue
                if floor < ev.min_floor or floor > ev.max_floor:
                    continue
                pool.append(ev)

        if not pool:
            return None

        weights = [ev.weight for ev in pool]
        selected = random.choices(pool, weights=weights, k=1)[0]

        # 발동 후 초기화
        self._steps_since_event = 0
        self._events_per_floor[floor_key] = self._events_per_floor.get(floor_key, 0) + 1
        self._event_cooldowns[selected.id] = selected.cooldown_steps
        self._hourly_event_times.append(now)  # 시간당 제한용 시각 기록
        if selected.once_only:
            self._completed_once_only.add(selected.id)

        return selected

    @staticmethod
    def _reward_scale_factor(floor: int = 1, level: int = 1) -> float:
        """층수/레벨 기반 보상 스케일 팩터.

        YAML의 보상 수치는 중반(floor~10 / level~10) 기준.
        초반에는 줄이고 후반에는 늘린다.
          floor/level  1 → 0.17  (gold ~50, exp ~40)
          floor/level  5 → 0.54
          floor/level 10 → 1.0
          floor/level 15 → 1.46
          floor/level 20 → 1.92
          floor/level 21+→ 2.0 (cap)
        """
        ref = max(floor, level, 1)
        return max(0.17, min(0.17 + (ref - 1) * 0.092, 2.0))

    def resolve_choice(
        self,
        event: YamlRandomEvent,
        choice_idx: int,
        party_jobs: List[str],
        inventory: Any = None,
        floor: int = 1,
        level: int = 1,
    ) -> EventOutcome:
        """선택지 결과 해결"""
        if choice_idx < 0 or choice_idx >= len(event.choices):
            return EventOutcome(message="아무 일도 일어나지 않았다.")

        choice = event.choices[choice_idx]

        # 요구사항 체크
        reqs = choice.requirements
        if reqs:
            if "has_job" in reqs:
                required_job = reqs["has_job"]
                if required_job not in party_jobs:
                    return EventOutcome(
                        message="필요한 직업이 파티에 없어 실패했다.",
                        event_type="fail",
                    )
            if "min_gold" in reqs and inventory is not None:
                min_gold = reqs["min_gold"]
                current_gold = getattr(inventory, 'gold', 0)
                if current_gold < min_gold:
                    return EventOutcome(
                        message=f"골드가 부족하다. ({current_gold}/{min_gold}G 필요)",
                        event_type="fail",
                    )
            if "has_item" in reqs and inventory is not None:
                required_item = reqs["has_item"]
                has_it = False
                if hasattr(inventory, 'items'):
                    for slot in inventory.items:
                        if slot and hasattr(slot, 'item_id') and slot.item_id == required_item:
                            has_it = True
                            break
                if not has_it:
                    return EventOutcome(
                        message=f"필요한 아이템이 없다.",
                        event_type="fail",
                    )

        # 결과 집계 (모든 outcomes 합산)
        if not choice.outcomes:
            return EventOutcome(message="아무 일도 일어나지 않았다.")

        total_message_parts = []
        total_gold = 0
        total_exp = 0
        total_items: List[str] = []
        total_affinity = 0
        total_damage = 0
        total_damage_pct = 0
        total_heal = 0
        total_heal_pct = 0
        last_buff = ""
        last_debuff = ""
        last_duration = 0
        last_type = "neutral"

        for outcome_data in choice.outcomes:
            msg = outcome_data.get("message", "")
            if msg:
                total_message_parts.append(msg)
            total_gold += outcome_data.get("gold", 0)
            total_exp += outcome_data.get("exp", 0)
            total_items.extend(outcome_data.get("items", []))
            total_affinity += outcome_data.get("affinity_gain", 0)
            total_damage += outcome_data.get("damage", 0)
            total_damage_pct += outcome_data.get("damage_percent", 0)
            total_heal += outcome_data.get("heal", 0)
            total_heal_pct += outcome_data.get("heal_percent", 0)
            otype = outcome_data.get("type", "neutral")
            if otype == "buff":
                last_buff = outcome_data.get("buff_id", "")
                last_duration = outcome_data.get("duration", 0)
            elif otype == "debuff":
                last_debuff = outcome_data.get("debuff_id", "")
                last_duration = outcome_data.get("duration", 0)
            if otype not in ("neutral",):
                last_type = otype

        # 층수/레벨 기반 보상 스케일링
        scale = self._reward_scale_factor(floor, level)
        total_gold = int(total_gold * scale)
        total_exp = int(total_exp * scale)

        return EventOutcome(
            message=" ".join(total_message_parts),
            gold=total_gold,
            exp=total_exp,
            items=total_items,
            affinity_gain=total_affinity,
            damage=total_damage,
            damage_percent=total_damage_pct,
            heal=total_heal,
            heal_percent=total_heal_pct,
            buff_id=last_buff,
            debuff_id=last_debuff,
            duration=last_duration,
            event_type=last_type,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps_since_event": self._steps_since_event,
            "total_steps": self._total_steps,
            "cooldowns": dict(self._event_cooldowns),
            "completed_once_only": list(self._completed_once_only),
            "hourly_event_times": list(self._hourly_event_times),
        }

    def from_dict(self, data: Dict[str, Any]):
        self._steps_since_event = data.get("steps_since_event", 0)
        self._total_steps = data.get("total_steps", 0)
        self._event_cooldowns = data.get("cooldowns", {})
        self._completed_once_only = set(data.get("completed_once_only", []))
        # 로드 시 1시간 이상 지난 타임스탬프 즉시 정리
        import time as _time
        now = _time.time()
        raw_times = data.get("hourly_event_times", [])
        self._hourly_event_times = [t for t in raw_times if isinstance(t, (int, float)) and now - t < 3600]


_random_event_manager: Optional[RandomEventManager] = None


def get_random_event_manager() -> RandomEventManager:
    """싱글톤 RandomEventManager 반환"""
    global _random_event_manager
    if _random_event_manager is None:
        _random_event_manager = RandomEventManager()
    return _random_event_manager
