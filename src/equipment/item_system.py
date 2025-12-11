"""
아이템 시스템

등급, 레벨 제한, 랜덤 부가 능력치
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import random

# Equipment effects 임포트 (순환 참조 방지를 위해 lazy import 사용)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.equipment.equipment_effects import EquipmentEffect


class ItemRarity(Enum):
    """아이템 등급"""
    COMMON = ("common", "일반", (180, 180, 180))
    UNCOMMON = ("uncommon", "고급", (100, 255, 100))
    RARE = ("rare", "희귀", (100, 150, 255))
    EPIC = ("epic", "영웅", (200, 100, 255))
    LEGENDARY = ("legendary", "전설", (255, 165, 0))
    UNIQUE = ("unique", "유니크", (255, 50, 150))

    def __init__(self, id: str, name: str, color: tuple):
        self.id = id
        self.display_name = name
        self.color = color


class ItemType(Enum):
    """아이템 타입"""
    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"
    CONSUMABLE = "consumable"
    MATERIAL = "material"
    KEY_ITEM = "key_item"
    FOOD = "food"


class EquipSlot(Enum):
    """장비 슬롯 (3가지만 사용)"""
    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"


@dataclass
class ItemAffix:
    """아이템 접사 (부가 능력치)"""
    id: str
    name: str
    stat: str  # hp, strength, defense, etc.
    value: float  # 고정값 또는 퍼센트
    is_percentage: bool = False

    def get_description(self) -> str:
        """설명 텍스트"""
        # 스탯 이름 한글 매핑
        stat_names = {
            "hp": "HP",
            "mp": "MP",
            "physical_attack": "물리 공격력",
            "physical_defense": "물리 방어력",
            "magic_attack": "마법 공격력",
            "magic_defense": "마법 방어력",
            "speed": "속도",
            "accuracy": "명중률",
            "evasion": "회피율",
            "luck": "행운",
            "strength": "힘",
            "defense": "방어력",
            "magic": "마력",
            "spirit": "정신력",
            "init_brv": "초기 BRV",
            "max_brv": "최대 BRV",
        }
        display_stat = stat_names.get(self.stat, self.stat.upper())
        
        # 등급 표시 (값의 크기에 따라)
        grade = ""
        if self.is_percentage:
            val = self.value * 100
            if val >= 20: grade = "(S)"
            elif val >= 15: grade = "(A)"
            elif val >= 10: grade = "(B)"
            else: grade = "(C)"
            return f"{display_stat} +{int(val)}% {grade}"
        else:
            # 고정값은 스탯 종류에 따라 기준이 다름 (대략적인 구분)
            grade = ""
            return f"{display_stat} +{int(self.value)}"


@dataclass
class Item:
    """아이템 기본 클래스"""
    item_id: str
    name: str
    description: str
    item_type: ItemType
    rarity: ItemRarity
    level_requirement: int = 1
    base_stats: Dict[str, float] = field(default_factory=dict)
    affixes: List[ItemAffix] = field(default_factory=list)
    unique_effect: Optional[str] = None
    stack_size: int = 1
    sell_price: int = 0
    weight: float = 1.0  # 무게 (kg)
    max_durability: int = 100  # 최대 내구도
    current_durability: int = 100  # 현재 내구도

    def __post_init__(self):
        """초기화 후 처리"""
        # 등급에 따른 최대 내구도 설정 (기본값 100에서 덮어쓰기)
        durability_map = {
            ItemRarity.COMMON: 150,
            ItemRarity.UNCOMMON: 160,
            ItemRarity.RARE: 180,
            ItemRarity.EPIC: 200,
            ItemRarity.LEGENDARY: 300,
            ItemRarity.UNIQUE: 500
        }
        # 생성 시 max_durability가 명시적으로 주어지지 않았거나 기본값인 경우 재설정
        if self.max_durability == 100:
            self.max_durability = durability_map.get(self.rarity, 100)
            self.current_durability = self.max_durability

    def get_total_stats(self) -> Dict[str, float]:
        """기본 스탯 + 접사 스탯 합계 (내구도 0일 때 50% 패널티)"""
        total = self.base_stats.copy()

        for affix in self.affixes:
            if affix.stat in total:
                if affix.is_percentage:
                    total[affix.stat] *= (1 + affix.value)
                else:
                    total[affix.stat] += affix.value
            else:
                total[affix.stat] = affix.value
        
        # 내구도가 0이면 스탯 50% 감소
        if self.current_durability <= 0:
            for stat in total:
                total[stat] *= 0.5
                
        return total

    def get_full_description(self) -> List[str]:
        """전체 설명 (여러 줄)"""
        lines = []
        lines.append(f"[{self.rarity.display_name}] {self.name}")
        lines.append(self.description)
        lines.append(f"레벨 제한: {self.level_requirement}")

        # 기본 스탯
        if self.base_stats:
            lines.append("기본 능력:")
            for stat, value in self.base_stats.items():
                lines.append(f"  {stat}: +{int(value)}")

        # 접사
        if self.affixes:
            lines.append("추가 능력:")
            for affix in self.affixes:
                lines.append(f"  {affix.get_description()}")

        # 유니크 효과
        if self.unique_effect:
            lines.append(f"특수: {self.unique_effect}")

        lines.append(f"판매가: {self.sell_price} 골드")

        return lines


@dataclass
class Equipment(Item):
    """장비 아이템"""
    equip_slot: EquipSlot = EquipSlot.WEAPON
    special_effects: List[Any] = field(default_factory=list)  # EquipmentEffect 리스트

    def __post_init__(self):
        # 부모 클래스의 __post_init__ 먼저 호출하여 내구도 설정
        super().__post_init__()

        if self.item_type not in [ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY]:
            self.item_type = ItemType.WEAPON


@dataclass
class Consumable(Item):
    """소비 아이템"""
    effect_type: str = "heal_hp"  # heal_hp, heal_mp, buff, etc.
    effect_value: float = 0

    def __post_init__(self):
        self.item_type = ItemType.CONSUMABLE


# ============= 아이템 생성 템플릿 =============

WEAPON_TEMPLATES = {
    # 검
    "iron_sword": {
        "name": "철검",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_attack": 10, "accuracy": 3},
        "sell_price": 50
    },
    "steel_sword": {
        "name": "강철검",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 20, "accuracy": 5},
        "sell_price": 150
    },
    "mithril_sword": {
        "name": "미스릴 검",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 32, "accuracy": 8, "speed": 2},
        "sell_price": 500
    },
    "dragon_slayer": {
        "name": "드래곤 슬레이어",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_attack": 55, "strength": 6},
        "sell_price": 2000
    },

    # 지팡이
    "wooden_staff": {
        "name": "나무 지팡이",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"magic_attack": 12, "mp": 6},
        "sell_price": 60
    },
    "crystal_staff": {
        "name": "수정 지팡이",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"magic_attack": 39, "mp": 20, "spirit": 3},
        "sell_price": 600
    },
    "archmagus_staff": {
        "name": "대마법사의 지팡이",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 7,
        "base_stats": {"magic_attack": 78, "mp": 39, "spirit": 10},
        "sell_price": 5000
    },

    # 활
    "hunting_bow": {
        "name": "사냥용 활",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_attack": 8, "accuracy": 6},
        "sell_price": 45
    },
    "longbow": {
        "name": "장궁",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 23, "accuracy": 10, "evasion": 2},
        "sell_price": 200
    },
    "composite_bow": {
        "name": "복합궁",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 36, "accuracy": 13, "critical_rate": 6},
        "sell_price": 550
    },

    # 단검
    "bronze_dagger": {
        "name": "청동 단검",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_attack": 6, "speed": 3, "evasion": 3},
        "sell_price": 35
    },
    "assassin_dagger": {
        "name": "암살자의 단검",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 26, "speed": 6, "critical_rate": 13},
        "sell_price": 450
    },
    "venom_fang": {
        "name": "독니",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 42, "speed": 10, "critical_rate": 16},
        "sell_price": 1800
    },

    # 둔기
    "iron_mace": {
        "name": "철 메이스",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_attack": 12, "strength": 2},
        "sell_price": 55
    },
    "war_hammer": {
        "name": "전쟁 망치",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 29, "strength": 5, "physical_defense": 3},
        "sell_price": 280
    },
    "titan_hammer": {
        "name": "티탄의 망치",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_attack": 62, "strength": 10, "hp": 32},
        "sell_price": 2200
    },

    # 창
    "short_spear": {
        "name": "짧은 창",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_attack": 9, "accuracy": 5},
        "sell_price": 48
    },
    "halberd": {
        "name": "할버드",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 31, "accuracy": 8, "physical_defense": 5},
        "sell_price": 320
    },
    "dragon_lance": {
        "name": "용의 창",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 72, "accuracy": 13, "critical_rate": 10},
        "sell_price": 6000
    },

    # 마법 지팡이 추가
    "fire_staff": {
        "name": "화염의 지팡이",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"magic_attack": 26, "mp": 13},
        "sell_price": 250
    },
    "ice_staff": {
        "name": "빙결의 지팡이",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"magic_attack": 26, "mp": 13},
        "sell_price": 250
    },
    "staff_of_cosmos": {
        "name": "우주의 지팡이",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 9,
        "base_stats": {"magic_attack": 84, "mp": 52, "spirit": 13},
        "sell_price": 7500
    },

    # === 생명력 흡수 무기 ===
    "vampiric_blade": {
        "name": "흡혈검",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 36, "speed": -1},
        "unique_effect": "lifesteal:0.15",  # 15% 생명력 흡수
        "sell_price": 800
    },
    "soul_drinker": {
        "name": "영혼 포식자",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_attack": 62, "magic_attack": 20, "hp": -32},
        "unique_effect": "lifesteal:0.25",  # 25% 생명력 흡수
        "sell_price": 2500
    },
    "crimson_reaver": {
        "name": "진홍의 수확자",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 52, "critical": 10},
        "unique_effect": "lifesteal:0.12|on_kill_heal:50",
        "sell_price": 1800
    },

    # === BRV 특화 무기 ===
    "brave_enhancer": {
        "name": "브레이브 인챈서",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 29, "speed": 2},
        "unique_effect": "brv_bonus:0.30",  # BRV +30%
        "sell_price": 600
    },
    "breaker": {
        "name": "브레이커",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 46, "luck": 6},
        "unique_effect": "brv_break_bonus:0.50",  # BREAK 데미지 +50%
        "sell_price": 1500
    },
    "soul_stealer": {
        "name": "영혼 강탈자",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 39, "accuracy": 6},
        "unique_effect": "brv_steal:0.20",  # BRV 흡수 +20%
        "sell_price": 1000
    },

    # === 크리티컬 특화 ===
    "assassins_edge": {
        "name": "암살자의 칼날",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 32, "critical": 13, "speed": 3},
        "unique_effect": "critical_damage:0.50",  # 크리티컬 데미지 +50%
        "sell_price": 700
    },
    "fatal_strike": {
        "name": "필살검",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 10,
        "base_stats": {"physical_attack": 55, "critical": 23, "luck": 10},
        "unique_effect": "critical_damage:0.75|critical_chance:0.15",
        "sell_price": 3000
    },
    "backstabber": {
        "name": "배신자의 단검",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 36, "critical": 10, "speed": 5},
        "unique_effect": "execute:0.30",  # 적 HP 30% 이하 시 +30% 데미지
        "sell_price": 900
    },

    # === 속성 무기 ===
    "flametongue": {
        "name": "화염검",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 26, "magic_attack": 10},
        "unique_effect": "element:fire|status_burn:0.25",  # 25% 화상
        "sell_price": 350
    },
    "frostbite": {
        "name": "동상의 검",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 25, "magic_attack": 12},
        "unique_effect": "element:ice|debuff_slow:0.30",
        "sell_price": 350
    },
    "thunderstrike": {
        "name": "뇌전검",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 34, "magic_attack": 16, "speed": 3},
        "unique_effect": "chain_lightning:0.25|status_shock:0.30|chain_lightning:0.20",
        "sell_price": 750
    },
    "earthshaker": {
        "name": "대지 파괴자",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 49, "strength": 8},
        "unique_effect": "element:earth|armor_penetration:0.20",
        "sell_price": 1200
    },
    "windcutter": {
        "name": "바람 절단자",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 27, "speed": 5, "accuracy": 6},
        "unique_effect": "element:wind|multi_strike:0.15",  # 15% 2회 공격
        "sell_price": 400
    },
    "voidreaver": {
        "name": "공허의 수확자",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_attack": 57, "magic_attack": 26, "mp": 32},
        "unique_effect": "element:void|mp_steal:0.30|debuff_silence:0.20",
        "sell_price": 2200
    },
    "holy_avenger": {
        "name": "성스러운 복수자",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_attack": 58, "magic_attack": 23, "spirit": 10},
        "unique_effect": "element:holy|bonus_vs_undead:0.50|heal_on_hit:5",
        "sell_price": 2500
    },

    # === 방어 관통 무기 ===
    "armor_piercer": {
        "name": "갑옷 관통자",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 38, "accuracy": 10},
        "unique_effect": "armor_penetration:0.25",
        "sell_price": 800
    },
    "true_strike_spear": {
        "name": "필중의 창",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 53, "accuracy": 32},
        "unique_effect": "accuracy_bonus:50|armor_penetration:0.15",
        "sell_price": 1800
    },

    # === 속도/연타 무기 ===
    "rapier": {
        "name": "레이피어",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 21, "speed": 8, "accuracy": 5},
        "unique_effect": "multi_strike:0.25|dodge_chance:0.10",
        "sell_price": 300
    },
    "twin_daggers": {
        "name": "쌍검",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 26, "speed": 6, "critical": 6},
        "unique_effect": "double_strike|critical_chance:0.10",
        "sell_price": 650
    },
    "flurry_blade": {
        "name": "난무의 검",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 32, "speed": 10, "critical": 10},
        "unique_effect": "multi_strike:1.0|strike_count:3-5",  # 100% 확률로 3~5회
        "sell_price": 2000
    },

    # === 방어/탱커 무기 ===
    "shield_bash_mace": {
        "name": "방패격 메이스",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 27, "defense": 5},
        "unique_effect": "stun_chance:0.20|block_chance:0.10",
        "sell_price": 400
    },
    "defenders_hammer": {
        "name": "수호자의 망치",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 39, "defense": 13, "hp": 65},
        "unique_effect": "damage_from_defense:0.50|thorns:0.15",
        "sell_price": 1100
    },
    "aegis_blade": {
        "name": "이지스 검",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_attack": 51, "defense": 20, "hp": 98},
        "unique_effect": "block_chance:0.25|counter_attack:0.30",
        "sell_price": 2300
    },

    # === 마법 무기 (특수 효과) ===
    "mana_blade": {
        "name": "마나 블레이드",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 36, "magic_attack": 20, "mp": 32},
        "unique_effect": "mp_to_damage:2.0|mp_cost_per_hit:10",  # MP 10당 20 추가 데미지
        "sell_price": 950
    },
    "arcane_staff": {
        "name": "비전 지팡이",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"magic_attack": 39, "mp": 39, "spirit": 6},
        "unique_effect": "mp_regen:5|skill_success:0.15",  # 턴당 MP+5, 스킬 성공률 +15%
        "sell_price": 750
    },
    "chaos_orb_staff": {
        "name": "혼돈의 오브 지팡이",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 9,
        "base_stats": {"magic_attack": 65, "mp": 65, "luck": 13},
        "unique_effect": "all_element_damage:0.20|all_element_affinity:0.20|wild_magic:0.30",
        "sell_price": 2800
    },
    "wisdom_tome": {
        "name": "지혜의 서",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"magic_attack": 36, "mp": 46, "spirit": 10},
        "unique_effect": "spell_power:0.15|skill_success:0.20",
        "sell_price": 700
    },
    "elemental_scepter": {
        "name": "원소 홀",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"magic_attack": 55, "mp": 58, "all_element_power": 16},
        "unique_effect": "elemental_mastery:0.25",
        "sell_price": 2100
    },
    "spell_amplifier": {
        "name": "주문 증폭기",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"magic_attack": 46, "mp": 39, "spirit": 8},
        "unique_effect": "spell_power:0.30|mp_cost_mult:1.20",
        "sell_price": 1000
    },
    "mana_channeler": {
        "name": "마나 전도체",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"magic_attack": 58, "mp": 78, "spirit": 12},
        "unique_effect": "mp_regen:10|spell_power:0.20",
        "sell_price": 2400
    },
    "mind_staff": {
        "name": "정신력 지팡이",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 7,
        "base_stats": {"magic_attack": 42, "mp": 52, "spirit": 16},
        "unique_effect": "magic_from_spirit:0.50",  # Spirit의 50%를 마법 공격력에 추가
        "sell_price": 1300
    },
    "spell_echo_staff": {
        "name": "메아리 지팡이",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"magic_attack": 62, "mp": 65, "spirit": 13},
        "unique_effect": "spell_echo:0.15",
        "sell_price": 2600
    },
    "void_wand": {
        "name": "공허의 지팡이",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 7,
        "base_stats": {"magic_attack": 49, "mp": 58, "spirit": 10},
        "unique_effect": "mp_steal:0.20|mp_regen:8",
        "sell_price": 1500
    },
    "meteor_staff": {
        "name": "유성 지팡이",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"magic_attack": 44, "mp": 46, "fire_power": 26},
        "unique_effect": "fire_mastery:0.40|fire_weakness:0.20",
        "sell_price": 950
    },
    "blizzard_wand": {
        "name": "눈보라 마법봉",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"magic_attack": 44, "mp": 46, "ice_power": 26},
        "unique_effect": "ice_mastery:0.40|ice_weakness:0.20",
        "sell_price": 950
    },
    "thunderlord_rod": {
        "name": "천둥군주의 봉",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"magic_attack": 44, "mp": 46, "lightning_power": 26},
        "unique_effect": "lightning_mastery:0.40|lightning_weakness:0.20",
        "sell_price": 950
    },

    # === 원거리 무기 ===
    "hunters_bow": {
        "name": "사냥꾼의 활",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 18, "accuracy": 8, "critical": 3},
        "unique_effect": "bonus_vs_beast:0.30|first_strike",
        "sell_price": 180
    },
    "sniper_rifle": {
        "name": "저격 활",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 47, "accuracy": 26, "critical": 16},
        "unique_effect": "critical_damage:1.0|headshot:0.20",  # 20% 확률로 즉사
        "sell_price": 1400
    },
    "repeating_crossbow": {
        "name": "연발 석궁",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 23, "accuracy": 6, "speed": 3},
        "unique_effect": "triple_shot|ammo_efficiency:0.20",
        "sell_price": 550
    },

    # === 디버프 무기 ===
    "poison_dagger": {
        "name": "독침 단검",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 23, "speed": 4},
        "unique_effect": "status_poison:0.40|poison_damage:10",  # 40% 독, 턴당 10 데미지
        "sell_price": 320
    },
    "cursed_blade": {
        "name": "저주받은 검",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 55, "magic_attack": 26, "hp": -65},
        "unique_effect": "debuff_master:0.30|curse_self:hp_max_reduction:0.10",
        "sell_price": 1300
    },
    "weakening_mace": {
        "name": "약화의 메이스",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 29, "accuracy": 3},
        "unique_effect": "debuff_defense_down:0.25|armor_break:0.30",
        "sell_price": 420
    },
    "terror_scythe": {
        "name": "공포의 낫",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 44, "magic_attack": 16, "critical": 10},
        "unique_effect": "status_fear:0.35|accuracy_debuff:0.20|harvest_soul:0.10",
        "sell_price": 1100
    },

    # === 특수 기믹 무기 ===
    "combo_master": {
        "name": "콤보 마스터",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 46, "speed": 8, "critical": 6},
        "unique_effect": "combo_bonus:0.15|max_combo:5",  # 콤보당 +15%, 최대 75%
        "sell_price": 1900
    },
    "momentum_blade": {
        "name": "역전의 검",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 39, "speed": 5},
        "unique_effect": "berserk|low_hp_bonus:1.0",  # HP 낮을수록 최대 +100%
        "sell_price": 900
    },
    "overload_staff": {
        "name": "과부하 지팡이",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"magic_attack": 72, "mp": 65, "spirit": 10},
        "unique_effect": "overload:mp_cost:2.0|damage:2.5",
        "sell_price": 2600
    },
    "gambler_dice": {
        "name": "도박사의 주사위",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 52, "luck": 20},
        "unique_effect": "random_damage:0.5-2.0|lucky_crit:0.20",
        "sell_price": 800
    },

    # === 레전더리 무기 ===
    "infinity_edge": {
        "name": "무한의 칼날",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 78, "critical": 32, "speed": 6},
        "unique_effect": "critical_chance:1.0|critical_damage:1.5|ignore_armor:0.30",
        "sell_price": 8000
    },
    "ultima_weapon": {
        "name": "얼티마 웨폰",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 13,
        "base_stats": {"physical_attack": 91, "magic_attack": 52, "hp": 130, "mp": 65},
        "unique_effect": "full_hp_bonus:all_stats:0.50|invincible_at_full_hp",
        "sell_price": 15000
    },
    "all_element_damage:0.50": {
        "name": "아포칼립스",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 9,
        "base_stats": {"physical_attack": 88, "magic_attack": 46, "all_stats": 10},
        "unique_effect": "on_kill:restore_all|stack_buff:permanent|lifesteal:0.20",
        "sell_price": 12000
    },

    # === Steampunk Weapons ===
    "steam_powered_hammer": {
        "name": "증기 동력 망치",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 42, "strength": 6, "speed": -3},
        "unique_effect": "stun_chance:0.25|status_burn:0.20",
        "sell_price": 850
    },
    "clockwork_crossbow": {
        "name": "태엽 석궁",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 26, "accuracy": 10, "speed": 3},
        "unique_effect": "multi_strike:0.20|multi_strike:0.15",
        "sell_price": 450
    },
    "tesla_coil_wand": {
        "name": "테슬라 코일 완드",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"magic_attack": 55, "mp": 39, "lightning_power": 20},
        "unique_effect": "chain_lightning:0.40|status_shock:0.30",
        "sell_price": 2200
    },

    # === Apocalypse Weapons ===
    "stop_sign_axe": {
        "name": "정지 표지판 도끼",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 25, "hp": 20},
        "unique_effect": "durability_bonus:0.50",
        "sell_price": 150
    },
    "spiked_bat": {
        "name": "못 박힌 방망이",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_attack": 13, "critical": 3},
        "unique_effect": "status_bleed:0.15",
        "sell_price": 60
    },
    "chainsaw_sword": {
        "name": "체인소드",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 49, "speed": -1},
        "unique_effect": "multi_hit:3|bleed_stack:0.20|low_durability",
        "sell_price": 1100
    },

    # === Sci-Fi/Future Weapons ===
    "laser_saber": {
        "name": "레이저 사벨",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"physical_attack": 58, "accuracy": 13, "speed": 6},
        "unique_effect": "ignore_armor:0.50|ignore_armor:0.30",
        "sell_price": 3500
    },
    "plasma_rifle": {
        "name": "플라즈마 라이플",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"physical_attack": 39, "magic_attack": 39, "accuracy": 10},
        "unique_effect": "status_burn:0.40|armor_melt:0.20",
        "sell_price": 1800
    },
    "nano_swarm_staff": {
        "name": "나노 스웜 스태프",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {"magic_attack": 72, "mp": 65, "spirit": 13},
        "unique_effect": "status_poison:0.40|status_burn:0.15",
        "sell_price": 8500
    },

    # === Fantasy/Past Weapons ===
    "obsidian_macuahuitl": {
        "name": "흑요석 마쿠아후이틀",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 42, "critical": 13},
        "unique_effect": "status_bleed:0.50|critical_damage:0.30",
        "sell_price": 700
    },
    "mjolnir_replica": {
        "name": "묠니르 레플리카",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 9,
        "base_stats": {"physical_attack": 81, "strength": 16, "lightning_power": 32},
        "unique_effect": "chain_lightning:0.25|critical_chance:0.10|stun_chance:0.40",
        "sell_price": 9000
    },

    # === Crossover/Other Weapons ===
    "portal_gun": {
        "name": "포털 건",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"magic_attack": 46, "evasion": 20, "speed": 10},
        "unique_effect": "teleport_dodge|status_confusion:0.30",
        "sell_price": 4000
    },
    "crowbar": {
        "name": "빠루",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 23, "accuracy": 6},
        "unique_effect": "bonus_vs_alien:0.50|crate_breaker",
        "sell_price": 300
    },
    
    # === More Steampunk Weapons ===
    "brass_knuckles": {
        "name": "황동 너클",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 21, "speed": 5, "critical": 6},
        "unique_effect": "lifesteal:0.10|steam_burn:0.15",
        "sell_price": 280
    },
    "gear_shield_lance": {
        "name": "기어 실드 랜스",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 46, "physical_defense": 10},
        "unique_effect": "counter_attack:0.20|armor_shred:0.15",
        "sell_price": 1200
    },
    "steam_gatling": {
        "name": "증기 개틀링",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 36, "speed": -5},
        "unique_effect": "multi_strike:0.60|status_burn:0.20",
        "sell_price": 2800
    },
    "chrono_wrench": {
        "name": "시간 렌치",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {"physical_attack": 62, "magic_attack": 42, "speed": 10},
        "unique_effect": "cooldown_reduction:0.25|cooldown_reduction:0.15",
        "sell_price": 9500
    },
    "pressure_blade": {
        "name": "압력 검",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 38, "magic_attack": 14},
        "unique_effect": "status_burn:0.30|status_burn:0.15:15",
        "sell_price": 950
    },

    # === More Apocalypse Weapons ===
    "rusty_pipe": {
        "name": "녹슨 파이프",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_attack": 12, "hp": 13},
        "unique_effect": "durability:high",
        "sell_price": 45
    },
    "molotov_launcher": {
        "name": "화염병 발사기",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 27, "fire_power": 16},
        "unique_effect": "status_burn:0.50|aoe:small",
        "sell_price": 580
    },
    "scrap_bow": {
        "name": "고철 활",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 25, "accuracy": 8, "critical": 5},
        "unique_effect": "critical_chance:0.15|scavenger_bonus:0.20",
        "sell_price": 320
    },
    "nail_gun": {
        "name": "못 총",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 34, "accuracy": 12, "speed": 4},
        "unique_effect": "status_bleed:0.40|piercing:0.25",
        "sell_price": 880
    },
    "sledgehammer": {
        "name": "대형 망치",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 44, "speed": -4, "critical_damage": 20},
        "unique_effect": "stun_chance:0.30|structure_damage:2.0",
        "sell_price": 420
    },
    "road_sign_sword": {
        "name": "도로 표지 검",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_attack": 14, "accuracy": 3},
        "unique_effect": "bonus_vs_vehicles:0.30",
        "sell_price": 90
    },

    # === More Sci-Fi Weapons ===
    "ion_cannon": {
        "name": "이온 캐논",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"magic_attack": 62, "mp": 52, "accuracy": 10},
        "unique_effect": "status_shock:0.50|shield_break|emp:0.30",
        "sell_price": 4200
    },
    "photon_blade": {
        "name": "광자 검",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 11,
        "base_stats": {"physical_attack": 75, "magic_attack": 55, "speed": 12},
        "unique_effect": "ignore_armor:0.75|light_speed_strike|holy_damage:0.40",
        "sell_price": 11000
    },
    "quantum_rifle": {
        "name": "양자 라이플",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 9,
        "base_stats": {"physical_attack": 57, "magic_attack": 36, "critical": 16},
        "unique_effect": "phase_through:0.20|quantum_crit:0.35",
        "sell_price": 5500
    },
    "cryo_gun": {
        "name": "냉동총",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"magic_attack": 47, "ice_power": 23},
        "unique_effect": "status_freeze:0.45|slow:0.30|shatter:0.20",
        "sell_price": 1900
    },
    "antimatter_blade": {
        "name": "반물질 검",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 12,
        "base_stats": {"physical_attack": 91, "magic_attack": 39},
        "unique_effect": "annihilation:0.15|ignore_defense:0.80|critical_damage:0.30",
        "sell_price": 15000
    },
    "graviton_hammer": {
        "name": "중력자 해머",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"physical_attack": 66, "strength": 12},
        "unique_effect": "gravity_crush:0.25|stun_chance:0.35|slow_field",
        "sell_price": 4800
    },

    # === Fantasy/Medieval Weapons ===
    "iron_longsword": {
        "name": "철 장검",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_attack": 16, "strength": 2},
        "unique_effect": "reliable",
        "sell_price": 100
    },
    "silver_rapier": {
        "name": "은 레이피어",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 26, "speed": 8, "accuracy": 10},
        "unique_effect": "critical_chance:0.15|riposte:0.20",
        "sell_price": 480
    },
    "flame_sword": {
        "name": "화염 검",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 42, "magic_attack": 20, "fire_power": 16},
        "unique_effect": "status_burn:0.40|fire_slash",
        "sell_price": 1400
    },
    "frost_axe": {
        "name": "서리 도끼",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 47, "ice_power": 18},
        "unique_effect": "status_freeze:0.35|slow:0.40|ice_cleave",
        "sell_price": 1350
    },
    "thunder_spear": {
        "name": "번개 창",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 51, "magic_attack": 29, "lightning_power": 26},
        "unique_effect": "chain_lightning:0.50|status_shock:0.40",
        "sell_price": 3200
    },
    "holy_mace": {
        "name": "성스러운 메이스",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_attack": 49, "magic_attack": 23, "spirit": 10},
        "unique_effect": "holy_damage:0.30|undead_slayer:0.50|heal_on_hit:0.10",
        "sell_price": 2700
    },
    "cursed_dagger": {
        "name": "저주받은 단검",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_attack": 36, "magic_attack": 31, "critical": 20},
        "unique_effect": "lifesteal:0.20|curse:0.25|critical_damage:0.40",
        "sell_price": 2400
    },
    "war_hammer": {
        "name": "전쟁 망치",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 52, "strength": 8, "speed": -3},
        "unique_effect": "stun_chance:0.40|armor_crush:0.25",
        "sell_price": 980
    },
    "elven_bow": {
        "name": "엘프 활",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 40, "accuracy": 16, "critical": 10, "speed": 3},
        "unique_effect": "piercing:0.30|wind_shot|nature_bonus:0.20",
        "sell_price": 1500
    },
    "battle_axe": {
        "name": "전투 도끼",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 38, "strength": 5, "critical_damage": 16},
        "unique_effect": "cleave|bleeding:0.25",
        "sell_price": 520
    },
    "katana": {
        "name": "카타나",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 44, "speed": 6, "critical": 13},
        "unique_effect": "critical_damage:0.50|iaido|precision_strike",
        "sell_price": 1600
    },
    "scimitar": {
        "name": "시미타",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 29, "speed": 5, "evasion": 6},
        "unique_effect": "swift_strikes|parry:0.15",
        "sell_price": 460
    },
    "scythe": {
        "name": "사신의 낫",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 55, "magic_attack": 26, "critical": 16},
        "unique_effect": "lifesteal:0.20|soul_harvest|lifesteal:0.15",
        "sell_price": 3500
    },

    # === Magical/Elemental Weapons ===
    "inferno_staff": {
        "name": "업화의 지팡이",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"magic_attack": 65, "mp": 58, "fire_power": 32},
        "unique_effect": "status_burn:0.60|fire_explosion:0.30|spell_power:0.25",
        "sell_price": 4500
    },
    "glacial_orb": {
        "name": "빙하의 구슬",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"magic_attack": 62, "mp": 55, "ice_power": 36},
        "unique_effect": "status_freeze:0.55|ice_storm|mana_freeze:0.20",
        "sell_price": 4300
    },
    "storm_wand": {
        "name": "폭풍의 완드",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"magic_attack": 51, "mp": 49, "wind_power": 23},
        "unique_effect": "chain_lightning:0.40|tornado|knockback",
        "sell_price": 2100
    },
    "earth_mace": {
        "name": "대지의 메이스",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 46, "magic_attack": 20, "hp": 32},
        "unique_effect": "earthquake:0.25|stun_chance:0.30|earth_shield",
        "sell_price": 1450
    },
    "void_blade": {
        "name": "공허의 검",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {"physical_attack": 72, "magic_attack": 52, "dark_power": 39},
        "unique_effect": "void_cut|mp_drain:0.15|existence_erasure:0.10",
        "sell_price": 10000
    },
    "light_scepter": {
        "name": "빛의 홀",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"magic_attack": 57, "mp": 65, "spirit": 13},
        "unique_effect": "holy_damage:0.40|heal_allies:0.15|dispel",
        "sell_price": 3800
    },
    "shadow_dagger": {
        "name": "그림자 단검",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 34, "magic_attack": 25, "speed": 10, "evasion": 10},
        "unique_effect": "backstab:2.0|stealth_bonus|critical_chance:0.20",
        "sell_price": 1550
    },
    "chaos_orb": {
        "name": "혼돈의 구체",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"magic_attack": 55, "mp": 52, "all_elements": 16},
        "unique_effect": "all_element_damage:0.20|critical_chance:0.20|critical_damage:0.40",
        "sell_price": 4000
    },
    "nature_staff": {
        "name": "자연의 지팡이",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"magic_attack": 49, "mp": 46, "spirit": 10, "hp": 26},
        "unique_effect": "hp_regen:0.03|status_poison:0.35|slow:0.25",
        "sell_price": 1800
    },
    "blood_whip": {
        "name": "피의 채찍",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 42, "magic_attack": 36},
        "unique_effect": "lifesteal:0.30|status_bleed:0.50|lifesteal:0.15",
        "sell_price": 3300
    },

    # === Modern Weapons ===
    "combat_knife": {
        "name": "전투 나이프",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 21, "speed": 6, "critical": 8},
        "unique_effect": "critical_chance:0.15|bleeding:0.20|speed_boost:0.10",
        "sell_price": 280
    },
    "assault_rifle": {
        "name": "돌격 소총",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 44, "accuracy": 10, "speed": 2},
        "unique_effect": "multi_strike:0.30|slow:0.20",
        "sell_price": 1650
    },
    "sniper_rifle": {
        "name": "저격 소총",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 68, "accuracy": 23, "critical": 20, "speed": -3},
        "unique_effect": "headshot:3.0|piercing:0.50|long_range",
        "sell_price": 3900
    },
    "shotgun": {
        "name": "산탄총",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 55, "speed": -2},
        "unique_effect": "aoe_damage:small|knockback|close_range_bonus:0.40",
        "sell_price": 1200
    },
    "grenade_launcher": {
        "name": "유탄 발사기",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"physical_attack": 62, "fire_power": 26},
        "unique_effect": "explosion:large|status_burn:0.40|aoe_damage",
        "sell_price": 4400
    },
    "tactical_tomahawk": {
        "name": "전술 토마호크",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 42, "critical": 12, "accuracy": 8},
        "unique_effect": "critical_chance:0.10|bleeding:0.30|armor_break:0.20",
        "sell_price": 1400
    },
    "taser_baton": {
        "name": "전기봉",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 25, "magic_attack": 16},
        "unique_effect": "status_shock:0.50|stun_chance:0.35|nonlethal",
        "sell_price": 480
    },

    # === Legendary/Unique Weapons ===
    "excalibur": {
        "name": "엑스칼리버",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 12,
        "base_stats": {"physical_attack": 98, "magic_attack": 52, "all_stats": 13},
        "unique_effect": "holy_damage:0.50|light_beam|auto_revive|all_stats_bonus:0.15",
        "sell_price": 25000
    },
    "muramasa": {
        "name": "무라마사",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 11,
        "base_stats": {"physical_attack": 94, "critical": 26, "speed": 10},
        "unique_effect": "low_hp_damage:0.50|lifesteal:0.25|critical_damage:0.80|critical_damage:0.20",
        "sell_price": 20000
    },
    "gungnir": {
        "name": "궁니르",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 11,
        "base_stats": {"physical_attack": 88, "magic_attack": 46, "accuracy": 32},
        "unique_effect": "accuracy_bonus:50|critical_chance:0.10|piercing:0.80|magic_attack_bonus:0.20",
        "sell_price": 22000
    },
    "frostmourne": {
        "name": "프로스트모른",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 12,
        "base_stats": {"physical_attack": 91, "magic_attack": 58, "ice_power": 46},
        "unique_effect": "lifesteal:0.25|status_freeze:0.70|lifesteal:0.30|summon_bonus:0.30",
        "sell_price": 28000
    },
    "infinity_blade": {
        "name": "무한의 검",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 13,
        "base_stats": {"physical_attack": 104, "magic_attack": 65, "all_stats": 16},
        "unique_effect": "all_damage:0.40|ignore_armor:0.60|cooldown_reduction:0.10",
        "sell_price": 35000
    },
    "dragons_tooth": {
        "name": "용의 이빨",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {"physical_attack": 83, "fire_power": 39, "strength": 16},
        "unique_effect": "status_burn:0.50|status_burn:0.60|physical_resist:0.25|fire_resist:1.0",
        "sell_price": 18000
    },
    "death_scythe": {
        "name": "죽음의 낫",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 11,
        "base_stats": {"physical_attack": 81, "magic_attack": 62, "dark_power": 42},
        "unique_effect": "lifesteal:0.30|soul_harvest|execute:0.30|lifesteal:0.25",
        "sell_price": 23000
    },
    "ragnarok": {
        "name": "라그나로크",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 14,
        "base_stats": {"physical_attack": 110, "magic_attack": 72, "all_stats": 20},
        "unique_effect": "all_element_damage:0.50|all_element_damage:0.60|execute:0.40|holy_damage:0.50",
        "sell_price": 50000
    },



    
    # === Additional Common Weapons ===
    "wooden_club": {"name": "나무 곤봉", "description": "", "rarity": ItemRarity.COMMON, "level_requirement": 1, "base_stats": {"physical_attack": 5}, "sell_price": 15},
    "stone_dagger": {"name": "돌 단검", "description": "", "rarity": ItemRarity.COMMON, "level_requirement": 1, "base_stats": {"physical_attack": 6, "speed": 2}, "sell_price": 18},
    "bone_club": {"name": "뼈 곤봉", "description": "", "rarity": ItemRarity.COMMON, "level_requirement": 1, "base_stats": {"physical_attack": 6, "strength": 1}, "sell_price": 20},
    "makeshift_spear": {"name": "임시 창", "description": "", "rarity": ItemRarity.COMMON, "level_requirement": 1, "base_stats": {"physical_attack": 7}, "sell_price": 22},
    "training_bow": {"name": "훈련용 활", "description": "", "rarity": ItemRarity.COMMON, "level_requirement": 1, "base_stats": {"physical_attack": 5, "accuracy": 5}, "sell_price": 25},
    "rusty_sword": {"name": "녹슨 검", "description": "", "rarity": ItemRarity.COMMON, "level_requirement": 1, "base_stats": {"physical_attack": 8}, "sell_price": 20},
    "cracked_staff": {"name": "금 간 지팡이", "description": "", "rarity": ItemRarity.COMMON, "level_requirement": 1, "base_stats": {"magic_attack": 9, "mp": 6}, "sell_price": 25},
    "chipped_axe": {"name": "이빨 빠진 도끼", "description": "", "rarity": ItemRarity.COMMON, "level_requirement": 1, "base_stats": {"physical_attack": 8}, "sell_price": 23},
    
    # === More Uncommon Weapons ===
    "bronze_mace": {"name": "청동 메이스", "description": "", "rarity": ItemRarity.UNCOMMON, "level_requirement": 2, "base_stats": {"physical_attack": 17, "strength": 3}, "sell_price": 120},
    "steel_spear": {"name": "강철 창", "description": "", "rarity": ItemRarity.UNCOMMON, "level_requirement": 3, "base_stats": {"physical_attack": 22, "accuracy": 6}, "sell_price": 180},
    "oak_staff": {"name": "참나무 지팡이", "description": "", "rarity": ItemRarity.UNCOMMON, "level_requirement": 2, "base_stats": {"magic_attack": 21, "mp": 20, "spirit": 3}, "sell_price": 150},
    "short_sword": {"name": "짧은 검", "description": "", "rarity": ItemRarity.UNCOMMON, "level_requirement": 2, "base_stats": {"physical_attack": 18, "speed": 3}, "sell_price": 130},
    "war_bow": {"name": "전쟁 활", "description": "", "rarity": ItemRarity.UNCOMMON, "level_requirement": 3, "base_stats": {"physical_attack": 23, "accuracy": 8}, "sell_price": 170},
    "battle_axe": {"name": "전투 도끼", "description": "", "rarity": ItemRarity.UNCOMMON, "level_requirement": 3, "base_stats": {"physical_attack": 26, "strength": 4, "speed": -1}, "sell_price": 200},
    "light_crossbow": {"name": "경량 석궁", "description": "", "rarity": ItemRarity.UNCOMMON, "level_requirement": 3, "base_stats": {"physical_attack": 23, "accuracy": 10}, "sell_price": 190},
    "simple_wand": {"name": "단순 완드", "description": "", "rarity": ItemRarity.UNCOMMON, "level_requirement": 2, "base_stats": {"magic_attack": 20, "mp": 16}, "sell_price": 140},

    # ============================================
    # === 오마주 무기 (다양한 시대/매체) ===
    # ============================================
    
    # === 판타지/RPG 고전작 오마주 ===
    "buster_sword": {
        "name": "버스터 소드",
        "description": "거대한 대검. 병사 1등급의 상징.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 15,
        "base_stats": {"physical_attack": 120, "strength": 18, "hp": 100},
        "unique_effect": "critical_damage:0.50|low_hp_bonus:0.40",
        "sell_price": 12000
    },
    "masamune_blade": {
        "name": "마사무네",
        "description": "전설의 명공이 제작한 긴 검.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 20,
        "base_stats": {"physical_attack": 145, "speed": 15, "critical": 25},
        "unique_effect": "critical_chance:0.30|piercing:0.40",
        "sell_price": 18000
    },
    "brotherhood_blade": {
        "name": "브라더후드",
        "description": "물의 힘이 깃든 푸른 검.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 12,
        "base_stats": {"physical_attack": 78, "magic_attack": 35, "ice_power": 25},
        "unique_effect": "ice_damage:0.30|status_freeze:0.20",
        "sell_price": 5500
    },
    "keyblade_hope": {
        "name": "키블레이드",
        "description": "빛과 어둠을 잇는 열쇠 형태의 검.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 12,
        "base_stats": {"physical_attack": 72, "magic_attack": 45, "spirit": 12},
        "unique_effect": "holy_damage:0.25|mp_regen:5",
        "sell_price": 6000
    },
    "master_sword": {
        "name": "마스터 소드",
        "description": "악을 물리치는 퇴마의 검.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 18,
        "base_stats": {"physical_attack": 130, "magic_attack": 40, "all_stats": 8},
        "unique_effect": "holy_damage:0.40|bonus_vs_undead:0.80",
        "sell_price": 15000
    },
    "soul_edge_cursed": {
        "name": "소울 엣지",
        "description": "영혼을 갈망하는 저주받은 마검.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 22,
        "base_stats": {"physical_attack": 165, "critical": 20, "hp": -50},
        "unique_effect": "lifesteal:0.30|critical_damage:0.80|curse_self:hp_max_reduction:0.10",
        "sell_price": 20000
    },
    "rebellion_sword": {
        "name": "리벨리온",
        "description": "악마 사냥꾼의 대검.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 16,
        "base_stats": {"physical_attack": 105, "speed": 8, "critical": 15},
        "unique_effect": "critical_damage:0.60|multi_strike:0.20",
        "sell_price": 8500
    },
    "monado_blade": {
        "name": "모나도",
        "description": "미래를 보는 신검.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 25,
        "base_stats": {"physical_attack": 155, "magic_attack": 60, "speed": 10},
        "unique_effect": "dodge_chance:0.25|critical_chance:0.25|all_damage:0.20",
        "sell_price": 25000
    },
    "dragonslayer_greatsword": {
        "name": "드래곤 슬레이어",
        "description": "너무 크고, 너무 무겁고, 너무 거친 철괴.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 24,
        "base_stats": {"physical_attack": 180, "strength": 25, "speed": -8},
        "unique_effect": "critical_damage:1.00|stun_chance:0.30",
        "sell_price": 22000
    },
    "zangetsu_blade": {
        "name": "참월",
        "description": "달을 베는 검.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 14,
        "base_stats": {"physical_attack": 95, "speed": 12, "spirit": 10},
        "unique_effect": "critical_chance:0.20|spell_power:0.20",
        "sell_price": 7000
    },
    "elucidator_dark": {
        "name": "엘루시데이터",
        "description": "흑의 검사가 사용하는 검은 검.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"physical_attack": 65, "speed": 10, "critical": 12},
        "unique_effect": "critical_chance:0.15|speed_boost:0.15",
        "sell_price": 3500
    },
    "dark_repulser": {
        "name": "다크 리펄서",
        "description": "청백색의 아름다운 검.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"physical_attack": 62, "magic_attack": 20, "speed": 8},
        "unique_effect": "critical_damage:0.40|piercing:0.15",
        "sell_price": 3500
    },
    
    # === 신화/역사 오마주 ===
    "durandal_holy": {
        "name": "뒤랑달",
        "description": "성인의 유물이 깃든 불멸의 성검.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 17,
        "base_stats": {"physical_attack": 110, "magic_attack": 30, "spirit": 15},
        "unique_effect": "holy_damage:0.35|unbreakable",
        "sell_price": 9000
    },
    "kusanagi_divine": {
        "name": "쿠사나기노츠루기",
        "description": "삼종신기 중 하나인 신검.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 19,
        "base_stats": {"physical_attack": 125, "wind_power": 40, "speed": 12},
        "unique_effect": "wind_damage:0.50|dodge_chance:0.20",
        "sell_price": 14000
    },
    "gae_bolg_spear": {
        "name": "게이볼그",
        "description": "심장을 관통하는 저주의 창.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 21,
        "base_stats": {"physical_attack": 140, "accuracy": 40, "critical": 30},
        "unique_effect": "execute:0.40|piercing:0.50",
        "sell_price": 17000
    },
    "vajra_thunder": {
        "name": "바즈라",
        "description": "뇌신의 금강저.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 14,
        "base_stats": {"physical_attack": 85, "magic_attack": 45, "lightning_power": 30},
        "unique_effect": "chain_lightning:0.40|status_shock:0.35",
        "sell_price": 7500
    },
    "joyeuse_blessed": {
        "name": "조와이즈",
        "description": "하루에 30번 색이 변하는 축복받은 검.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 16,
        "base_stats": {"physical_attack": 98, "luck": 20, "hp": 60},
        "unique_effect": "critical_chance:0.20|gold_find:0.50",
        "sell_price": 8000
    },
    "tizona_blade": {
        "name": "티소나",
        "description": "적에게 공포를 심는 영웅의 검.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 11,
        "base_stats": {"physical_attack": 72, "strength": 8, "spirit": 6},
        "unique_effect": "status_fear:0.30",
        "sell_price": 4000
    },
    "clarent_blood": {
        "name": "클라렌트",
        "description": "왕위를 빼앗는 반역의 검.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 15,
        "base_stats": {"physical_attack": 100, "critical": 18, "dark_power": 20},
        "unique_effect": "critical_damage:0.70|lifesteal:0.15",
        "sell_price": 7800
    },
    "rhongomyniad_lance": {
        "name": "론고미니아드",
        "description": "세계를 고정하는 성창.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 23,
        "base_stats": {"physical_attack": 150, "magic_attack": 50, "spirit": 18},
        "unique_effect": "holy_damage:0.50|all_damage:0.25",
        "sell_price": 21000
    },
    "gram_sword": {
        "name": "그람",
        "description": "용을 죽인 영웅의 마검.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 20,
        "base_stats": {"physical_attack": 138, "fire_power": 30, "strength": 15},
        "unique_effect": "bonus_vs_beast:0.80|status_burn:0.30",
        "sell_price": 16000
    },
    "naegling_heroic": {
        "name": "네글링",
        "description": "영웅이 사용한 고대의 검.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 13,
        "base_stats": {"physical_attack": 82, "strength": 12, "hp": 50},
        "unique_effect": "strength_boost:0.20",
        "sell_price": 5800
    },
    "amenonuhoko": {
        "name": "아메노누호코",
        "description": "천상의 옥으로 장식된 신창.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 26,
        "base_stats": {"physical_attack": 160, "magic_attack": 80, "all_stats": 12},
        "unique_effect": "all_element_damage:0.30|holy_damage:0.40",
        "sell_price": 28000
    },
    "harpe_divine": {
        "name": "하르페",
        "description": "신에게서 받은 낫검.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 15,
        "base_stats": {"physical_attack": 95, "speed": 10, "evasion": 12},
        "unique_effect": "execute:0.30|armor_penetration:0.30",
        "sell_price": 7200
    },
    
    # === 애니메이션/만화 오마주 ===
    "tessaiga_fang": {
        "name": "철쇄아",
        "description": "아버지의 이빨로 만든 요도.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 15,
        "base_stats": {"physical_attack": 105, "wind_power": 25, "strength": 10},
        "unique_effect": "aoe_damage:medium|wind_damage:0.30",
        "sell_price": 8000
    },
    "sakabato_reverse": {
        "name": "역날검",
        "description": "살생을 거부하는 역날의 검.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 9,
        "base_stats": {"physical_attack": 55, "speed": 15, "evasion": 10},
        "unique_effect": "nonlethal|counter_attack:0.30",
        "sell_price": 2800
    },
    "toyako_wooden": {
        "name": "토야코 목검",
        "description": "호수 이름이 새겨진 목검.",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 35, "speed": 8, "luck": 10},
        "unique_effect": "stun_chance:0.20|durability:high",
        "sell_price": 800
    },
    "scissor_blade_red": {
        "name": "시저 블레이드",
        "description": "가위 형태의 붉은 검.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 14,
        "base_stats": {"physical_attack": 88, "critical": 18, "speed": 8},
        "unique_effect": "critical_damage:0.60|armor_penetration:0.25",
        "sell_price": 6800
    },
    "ea_sword_origin": {
        "name": "에아",
        "description": "성배에 담긴 세계를 가르는 검.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 28,
        "base_stats": {"physical_attack": 175, "magic_attack": 100, "all_stats": 15},
        "unique_effect": "all_damage:0.50|ignore_armor:0.60",
        "sell_price": 35000
    },
    "caliburn_selection": {
        "name": "칼리번",
        "description": "왕을 선택하는 선정의 검.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 16,
        "base_stats": {"physical_attack": 102, "magic_attack": 35, "spirit": 12},
        "unique_effect": "holy_damage:0.35|critical_chance:0.20",
        "sell_price": 8200
    },
    "yamato_demon": {
        "name": "야마토",
        "description": "공간을 베는 마검.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 22,
        "base_stats": {"physical_attack": 148, "speed": 18, "critical": 22},
        "unique_effect": "piercing:0.60|critical_damage:0.80",
        "sell_price": 19000
    },
    "demon_dweller_sword": {
        "name": "마거주검",
        "description": "마력을 흡수하는 검.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 8,
        "base_stats": {"physical_attack": 52, "magic_attack": 30, "mp": 30},
        "unique_effect": "mp_steal:0.20|spell_power:0.15",
        "sell_price": 2500
    },
    "demon_slayer_sword": {
        "name": "마멸검",
        "description": "악마를 멸하는 검.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 13,
        "base_stats": {"physical_attack": 85, "magic_attack": 25, "spirit": 8},
        "unique_effect": "bonus_vs_undead:0.60|holy_damage:0.20",
        "sell_price": 5500
    },
    "laevatein_flame": {
        "name": "레바테인",
        "description": "세계를 불태우는 화염의 검.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 24,
        "base_stats": {"physical_attack": 140, "magic_attack": 70, "fire_power": 50},
        "unique_effect": "status_burn:0.60|fire_explosion:0.30",
        "sell_price": 23000
    },
    "nichirin_blade_sun": {
        "name": "일륜도",
        "description": "귀살대가 사용하는 햇빛을 담은 검.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 11,
        "base_stats": {"physical_attack": 70, "speed": 10, "critical": 10},
        "unique_effect": "bonus_vs_undead:0.50|holy_damage:0.15",
        "sell_price": 4200
    },
    "black_clover_grimoire_sword": {
        "name": "그리모어 검",
        "description": "마도서에서 나온 검.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 9,
        "base_stats": {"physical_attack": 55, "magic_attack": 35, "mp": 25},
        "unique_effect": "mp_regen:5|spell_power:0.15",
        "sell_price": 2900
    },
    
    # === 현대/SF 오마주 ===
    "beam_katana_red": {
        "name": "빔 카타나",
        "description": "에너지로 이루어진 광검.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"physical_attack": 115, "magic_attack": 30, "speed": 10},
        "unique_effect": "ignore_armor:0.40|status_burn:0.25",
        "sell_price": 9500
    },
    "covenant_energy_sword": {
        "name": "에너지 소드",
        "description": "플라즈마로 이루어진 검.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 12,
        "base_stats": {"physical_attack": 75, "magic_attack": 25, "speed": 6},
        "unique_effect": "ignore_armor:0.30|status_burn:0.20",
        "sell_price": 4500
    },
    "high_frequency_blade": {
        "name": "고주파 블레이드",
        "description": "분자 수준에서 절단하는 검.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 19,
        "base_stats": {"physical_attack": 125, "speed": 12, "accuracy": 20},
        "unique_effect": "armor_penetration:0.50|critical_damage:0.50",
        "sell_price": 10500
    },
    "diamond_sword_mc": {
        "name": "다이아몬드 검",
        "description": "다이아몬드로 만든 내구성 높은 검.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 8,
        "base_stats": {"physical_attack": 55, "critical": 8},
        "unique_effect": "durability:high",
        "sell_price": 2400
    },
    "netherite_sword_mc": {
        "name": "네더라이트 검",
        "description": "지옥의 광물로 강화된 검.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 15,
        "base_stats": {"physical_attack": 98, "fire_power": 15, "strength": 8},
        "unique_effect": "fire_resist:0.50|durability:high",
        "sell_price": 7500
    },
    "leviathan_axe_frost": {
        "name": "리바이어던 도끼",
        "description": "얼음의 힘이 깃든 마법 도끼.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 20,
        "base_stats": {"physical_attack": 142, "ice_power": 45, "strength": 15},
        "unique_effect": "status_freeze:0.40|ice_damage:0.40",
        "sell_price": 16500
    },
    "blades_of_chaos_fire": {
        "name": "혼돈의 칼날",
        "description": "불꽃 사슬로 연결된 쌍검.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 22,
        "base_stats": {"physical_attack": 135, "fire_power": 50, "speed": 8},
        "unique_effect": "status_burn:0.50|multi_strike:0.30|lifesteal:0.15",
        "sell_price": 18500
    },
    "moonlight_great_sword": {
        "name": "달빛 대검",
        "description": "달빛을 뿜어내는 신비로운 대검.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 24,
        "base_stats": {"physical_attack": 130, "magic_attack": 80, "spirit": 15},
        "unique_effect": "spell_power:0.30|magic_from_spirit:0.50",
        "sell_price": 21000
    },
    "ludwig_holy_blade": {
        "name": "루드비히의 성검",
        "description": "은의 검과 대검을 겸비한 무기.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 23,
        "base_stats": {"physical_attack": 145, "magic_attack": 45, "strength": 12},
        "unique_effect": "holy_damage:0.35|critical_damage:0.60",
        "sell_price": 20000
    },
    "burial_blade": {
        "name": "매장의 검",
        "description": "낫과 검을 변환할 수 있는 무기.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 17,
        "base_stats": {"physical_attack": 108, "speed": 14, "critical": 16},
        "unique_effect": "critical_chance:0.25|soul_harvest",
        "sell_price": 9000
    },
    
    # === 마법사/지팡이 계열 ===
    "elder_wand_death": {
        "name": "딱총나무 지팡이",
        "description": "죽음이 직접 만든 최강의 지팡이.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 25,
        "base_stats": {"magic_attack": 150, "mp": 120, "spirit": 25},
        "unique_effect": "spell_power:0.50|mp_cost_reduction:0.30",
        "sell_price": 27000
    },
    "staff_of_ainz": {
        "name": "아인즈의 지팡이",
        "description": "지고의 마도왕이 사용하는 지팡이.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 28,
        "base_stats": {"magic_attack": 170, "mp": 150, "spirit": 30, "all_stats": 10},
        "unique_effect": "spell_power:0.60|all_element_damage:0.40|mp_regen:15",
        "sell_price": 40000
    },
    "staff_of_magnus": {
        "name": "마그누스의 지팡이",
        "description": "마법의 신이 사용했던 지팡이.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 23,
        "base_stats": {"magic_attack": 140, "mp": 100, "spirit": 20},
        "unique_effect": "mp_steal:0.30|spell_power:0.40",
        "sell_price": 22000
    },
    "caduceus_hermes": {
        "name": "카두케우스",
        "description": "전령신의 지팡이.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 16,
        "base_stats": {"magic_attack": 95, "mp": 70, "speed": 15},
        "unique_effect": "speed_boost:0.20|heal_boost:0.30",
        "sell_price": 8500
    },
    "mace_of_molag_bal": {
        "name": "몰라그 발의 철퇴",
        "description": "데이드릭 왕자의 악의가 담긴 철퇴.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 23,
        "base_stats": {"physical_attack": 135, "magic_attack": 50, "dark_power": 40},
        "unique_effect": "lifesteal:0.25|mp_steal:0.25|curse:0.30",
        "sell_price": 21000
    },
    "thyrsus_staff": {
        "name": "티르수스",
        "description": "포도넝쿨로 감긴 축제의 지팡이.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 11,
        "base_stats": {"magic_attack": 68, "mp": 50, "luck": 15},
        "unique_effect": "status_confusion:0.30|hp_regen:0.03",
        "sell_price": 4000
    },
    "loki_scepter_chaos": {
        "name": "로키의 셉터",
        "description": "정신을 지배하는 힘이 담긴 셉터.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 17,
        "base_stats": {"magic_attack": 105, "mp": 65, "spirit": 12},
        "unique_effect": "status_confusion:0.40|spell_power:0.25",
        "sell_price": 9000
    },
    "gandalf_staff": {
        "name": "백색 마법사의 지팡이",
        "description": "빛과 불의 마법을 다루는 지팡이.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 22,
        "base_stats": {"magic_attack": 135, "mp": 90, "spirit": 18, "fire_power": 25},
        "unique_effect": "holy_damage:0.30|fire_damage:0.30|spell_power:0.25",
        "sell_price": 19000
    },
    "saruman_staff": {
        "name": "다색 마법사의 지팡이",
        "description": "모든 색을 포함한 지팡이.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"magic_attack": 115, "mp": 80, "spirit": 15},
        "unique_effect": "all_element_damage:0.25|spell_power:0.20",
        "sell_price": 10000
    },
    
    # === 추가 무기: 다양한 레벨 분포 ===
    # 레벨 1-5
    "copper_gladius": {
        "name": "청동 글라디우스",
        "description": "로마 병사의 기본 검.",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 14, "speed": 3},
        "sell_price": 80
    },
    "wooden_greatbow": {
        "name": "나무 장궁",
        "description": "기본적인 장궁.",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 16, "accuracy": 8},
        "sell_price": 100
    },
    "shaman_staff": {
        "name": "주술사의 지팡이",
        "description": "자연의 힘을 다루는 지팡이.",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 4,
        "base_stats": {"magic_attack": 28, "mp": 25, "spirit": 5},
        "unique_effect": "hp_regen:0.02",
        "sell_price": 280
    },
    "tribal_axe": {
        "name": "부족 도끼",
        "description": "원시적인 전투 도끼.",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 35, "strength": 5},
        "unique_effect": "status_bleed:0.15",
        "sell_price": 350
    },
    
    # 레벨 6-10
    "samurai_daisho": {
        "name": "사무라이 대소",
        "description": "카타나와 와키자시 세트.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 48, "speed": 8, "critical": 8},
        "unique_effect": "counter_attack:0.20",
        "sell_price": 1800
    },
    "viking_battleaxe": {
        "name": "바이킹 전투도끼",
        "description": "북해의 약탈자들이 사용하는 도끼.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 8,
        "base_stats": {"physical_attack": 58, "strength": 8, "hp": 30},
        "unique_effect": "stun_chance:0.25|status_bleed:0.20",
        "sell_price": 2200
    },
    "moorish_scimitar": {
        "name": "무어인의 시미타르",
        "description": "사막의 전사가 사용하는 곡검.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 9,
        "base_stats": {"physical_attack": 60, "speed": 10, "evasion": 8},
        "unique_effect": "dodge_chance:0.15|speed_boost:0.10",
        "sell_price": 2600
    },
    "crusader_longsword": {
        "name": "십자군 장검",
        "description": "성지를 향한 십자군의 검.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"physical_attack": 68, "spirit": 8, "hp": 35},
        "unique_effect": "holy_damage:0.20",
        "sell_price": 3200
    },
    
    # 레벨 11-15
    "zweihander_giant": {
        "name": "츠바이핸더",
        "description": "양손으로 휘두르는 거대한 검.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 11,
        "base_stats": {"physical_attack": 78, "strength": 10, "speed": -3},
        "unique_effect": "critical_damage:0.40|stun_chance:0.20",
        "sell_price": 3800
    },
    "flamberge_wavy": {
        "name": "플람베르주",
        "description": "물결 모양 날의 대검.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 12,
        "base_stats": {"physical_attack": 82, "critical": 12},
        "unique_effect": "status_bleed:0.35|armor_penetration:0.20",
        "sell_price": 4200
    },
    "estoc_thrust": {
        "name": "에스토크",
        "description": "찌르기 전용의 가느다란 검.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 13,
        "base_stats": {"physical_attack": 75, "accuracy": 20, "speed": 8},
        "unique_effect": "piercing:0.35|critical_chance:0.15",
        "sell_price": 4600
    },
    "claymore_highland": {
        "name": "하이랜드 클레이모어",
        "description": "고지대 전사의 대검.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 14,
        "base_stats": {"physical_attack": 92, "strength": 12, "hp": 50},
        "unique_effect": "critical_damage:0.50|strength_boost:0.15",
        "sell_price": 5500
    },
    "rapier_musketeer": {
        "name": "총사의 레이피어",
        "description": "명예를 위해 싸우는 검사의 검.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 15,
        "base_stats": {"physical_attack": 85, "speed": 15, "accuracy": 18},
        "unique_effect": "critical_chance:0.25|riposte:0.25",
        "sell_price": 6200
    },
    
    # 레벨 16-20
    "falchion_eastern": {
        "name": "동방의 팔시온",
        "description": "동양풍 외날 곡검.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 16,
        "base_stats": {"physical_attack": 102, "speed": 10, "critical": 14},
        "unique_effect": "critical_damage:0.55|speed_boost:0.15",
        "sell_price": 7200
    },
    "glaive_polearm": {
        "name": "글레이브",
        "description": "긴 자루에 칼날이 달린 장병기.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 17,
        "base_stats": {"physical_attack": 110, "accuracy": 15, "strength": 10},
        "unique_effect": "piercing:0.30|aoe_damage:small",
        "sell_price": 8000
    },
    "naginata_warrior": {
        "name": "나기나타",
        "description": "여성 전사가 사용하는 장병기.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"physical_attack": 115, "speed": 8, "evasion": 12},
        "unique_effect": "counter_attack:0.25|dodge_chance:0.15",
        "sell_price": 8800
    },
    "nodachi_great": {
        "name": "노다치",
        "description": "매우 긴 일본도.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 19,
        "base_stats": {"physical_attack": 125, "critical": 16, "speed": 5},
        "unique_effect": "critical_damage:0.65|critical_chance:0.20",
        "sell_price": 9600
    },
    "khopesh_egyptian": {
        "name": "코페시",
        "description": "이집트 양식의 낫 형태 검.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 20,
        "base_stats": {"physical_attack": 130, "strength": 12, "luck": 10},
        "unique_effect": "critical_chance:0.20|armor_penetration:0.25",
        "sell_price": 10500
    },
    
    # 레벨 21-25
    "odachi_demon": {
        "name": "오오다치",
        "description": "악귀를 베기 위한 대태도.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 21,
        "base_stats": {"physical_attack": 145, "critical": 20, "strength": 15},
        "unique_effect": "critical_damage:0.80|bonus_vs_undead:0.50",
        "sell_price": 15000
    },
    "zanbato_horse_slayer": {
        "name": "참마도",
        "description": "기병을 베기 위한 거대한 검.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 22,
        "base_stats": {"physical_attack": 160, "strength": 20, "speed": -5},
        "unique_effect": "stun_chance:0.35|critical_damage:0.90",
        "sell_price": 16500
    },
    "kings_ultra_greatsword": {
        "name": "왕의 대검",
        "description": "거인 왕이 휘두르던 대검.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 23,
        "base_stats": {"physical_attack": 175, "strength": 22, "hp": 80, "speed": -6},
        "unique_effect": "stun_chance:0.40|armor_penetration:0.35",
        "sell_price": 18000
    },
    "black_knight_sword": {
        "name": "흑기사의 검",
        "description": "화염에 휩싸인 흑기사의 무기.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 24,
        "base_stats": {"physical_attack": 160, "fire_power": 40, "strength": 15},
        "unique_effect": "status_burn:0.45|fire_damage:0.35",
        "sell_price": 19500
    },
    "chaos_blade_dark": {
        "name": "혼돈의 검",
        "description": "사용자의 생명을 갈망하는 마검.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 25,
        "base_stats": {"physical_attack": 170, "critical": 25, "speed": 10},
        "unique_effect": "lifesteal:0.20|critical_damage:0.90|hp_penalty:-0.10",
        "sell_price": 22000
    },
    
    # 레벨 26-30
    "dragon_king_greataxe": {
        "name": "용왕의 대도끼",
        "description": "고대 용왕의 뼈로 만든 도끼.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 26,
        "base_stats": {"physical_attack": 185, "strength": 25, "fire_power": 35},
        "unique_effect": "fire_damage:0.40|critical_damage:1.00",
        "sell_price": 26000
    },
    "demon_king_blade": {
        "name": "마왕의 검",
        "description": "마왕이 사용했던 악의가 서린 검.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 27,
        "base_stats": {"physical_attack": 180, "magic_attack": 80, "dark_power": 50},
        "unique_effect": "all_damage:0.40|lifesteal:0.25|curse:0.30",
        "sell_price": 30000
    },
    "god_slayer_blade": {
        "name": "신살검",
        "description": "신조차 쓰러뜨릴 수 있는 검.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 28,
        "base_stats": {"physical_attack": 190, "magic_attack": 60, "all_stats": 12},
        "unique_effect": "all_damage:0.45|ignore_armor:0.50",
        "sell_price": 35000
    },
    "world_ender": {
        "name": "세계종결자",
        "description": "세계를 끝낼 수 있는 힘을 가진 무기.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 29,
        "base_stats": {"physical_attack": 200, "magic_attack": 100, "all_stats": 15},
        "unique_effect": "all_damage:0.50|execute:0.50|lifesteal:0.20",
        "sell_price": 45000
    },
    "primordial_blade": {
        "name": "태초의 검",
        "description": "세계가 창조될 때 함께 태어난 검.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 30,
        "base_stats": {"physical_attack": 220, "magic_attack": 120, "all_stats": 20},
        "unique_effect": "all_damage:0.60|all_element_damage:0.50|hp_regen:0.05",
        "sell_price": 60000
    },
    
    # === 추가 마법 무기 ===
    "wand_of_woh": {
        "name": "워의 지팡이",
        "description": "폭발 마법에 특화된 지팡이.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 21,
        "base_stats": {"magic_attack": 128, "mp": 85, "fire_power": 35},
        "unique_effect": "fire_explosion:0.40|spell_power:0.35",
        "sell_price": 16000
    },
    "starfire_staff": {
        "name": "별빛 지팡이",
        "description": "별의 힘을 담은 지팡이.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 19,
        "base_stats": {"magic_attack": 118, "mp": 75, "spirit": 15},
        "unique_effect": "spell_power:0.30|holy_damage:0.25",
        "sell_price": 11000
    },
    "abyssal_scepter": {
        "name": "심연의 셉터",
        "description": "어둠의 심연에서 건져낸 셉터.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 20,
        "base_stats": {"magic_attack": 125, "mp": 80, "dark_power": 40},
        "unique_effect": "dark_damage:0.40|mp_steal:0.20",
        "sell_price": 12000
    },
    "arcane_grimoire": {
        "name": "비전의 서",
        "description": "고대 마법이 기록된 마도서.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 26,
        "base_stats": {"magic_attack": 155, "mp": 130, "spirit": 22},
        "unique_effect": "spell_power:0.45|mp_cost_reduction:0.25|mp_regen:12",
        "sell_price": 28000
    },
    "void_staff": {
        "name": "공허의 지팡이",
        "description": "마법 저항을 관통하는 지팡이.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 17,
        "base_stats": {"magic_attack": 105, "mp": 60, "void_power": 25},
        "unique_effect": "spell_power:0.25|armor_penetration:0.35",
        "sell_price": 8800
    },
    "frost_queen_claim": {
        "name": "서리 여왕의 권능",
        "description": "얼음 여왕의 힘이 담긴 지팡이.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 24,
        "base_stats": {"magic_attack": 145, "mp": 100, "ice_power": 55},
        "unique_effect": "status_freeze:0.50|ice_damage:0.45|slow:0.40",
        "sell_price": 24000
    },
}


ARMOR_TEMPLATES = {
    # 갑옷
    "leather_armor": {
        "name": "가죽 갑옷",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_defense": 6, "hp": 13},
        "sell_price": 40
    },
    "plate_armor": {
        "name": "판금 갑옷",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 32, "hp": 52, "physical_attack": -3},
        "sell_price": 600
    },
    "dragon_scale_armor": {
        "name": "용비늘 갑옷",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 58, "magic_defense": 46, "hp": 98},
        "sell_price": 8000
    },

    # 로브
    "cloth_robe": {
        "name": "천 로브",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"magic_defense": 8, "mp": 10},
        "sell_price": 50
    },
    "mage_robe": {
        "name": "마법사 로브",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"magic_defense": 26, "mp": 32, "magic_attack": 6},
        "sell_price": 500
    },
    "archmage_robe": {
        "name": "대마법사 로브",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"magic_defense": 46, "mp": 65, "magic_attack": 16},
        "sell_price": 2000
    },
    "celestial_robes": {
        "name": "천상의 로브",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 7,
        "base_stats": {"magic_defense": 65, "mp": 98, "magic_attack": 26, "spirit": 10},
        "sell_price": 7000
    },

    # 경갑
    "padded_armor": {
        "name": "누빔 갑옷",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_defense": 5, "evasion": 3},
        "sell_price": 38
    },
    "studded_leather": {
        "name": "징박이 가죽",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 14, "evasion": 5, "hp": 20},
        "sell_price": 180
    },

    # 중갑 추가
    "knight_armor": {
        "name": "기사 갑옷",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_defense": 23, "hp": 32, "strength": 3},
        "sell_price": 350
    },
    "dragon_armor": {
        "name": "드래곤 아머",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 11,
        "base_stats": {"physical_defense": 62, "magic_defense": 49, "hp": 117, "strength": 8},
        "sell_price": 9000
    },

    # === 상처 시스템 연동 방어구 ===
    "healers_robe": {
        "name": "치유사의 로브",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"magic_defense": 23, "spirit": 8, "hp": 52},
        "unique_effect": "wound_reduction:0.30|heal_boost:0.20",
        "sell_price": 650
    },
    "regenerative_armor": {
        "name": "재생의 갑옷",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 39, "hp": 98, "defense": 10},
        "unique_effect": "wound_regen:5|hp_regen:0.03",  # 턴당 상처 5, HP 3%
        "sell_price": 1800
    },
    "scarless_plate": {
        "name": "무흔의 판금",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"physical_defense": 46, "magic_defense": 26, "hp": 78},
        "unique_effect": "wound_immunity|damage_taken:0.10",
        "sell_price": 2200
    },
    "trauma_ward": {
        "name": "외상 보호복",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 29, "magic_defense": 20, "hp": 65},
        "unique_effect": "wound_reduction:0.50",
        "sell_price": 850
    },

    # === BRV 시스템 연동 방어구 ===
    "brave_guard": {
        "name": "브레이브 가드",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 26, "magic_defense": 23, "hp": 58},
        "unique_effect": "brv_shield:0.30|brv_protect",  # BREAK 1회 방지
        "sell_price": 700
    },
    "fortress_plate": {
        "name": "요새 판금",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 55, "hp": 130, "speed": -3},
        "unique_effect": "brv_shield:0.50|block_chance:0.20",
        "sell_price": 2000
    },
    "breaker_armor": {
        "name": "파괴자의 갑옷",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_defense": 23, "hp": 52},
        "unique_effect": "brv_bonus:0.25|defense_reduction:0.20",
        "sell_price": 800
    },

    # === 마법사 전용 로브 ===
    "apprentice_robe": {
        "name": "견습 마법사의 로브",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"magic_defense": 8, "mp": 26, "magic_attack": 8},
        "unique_effect": "mp_regen:3",
        "sell_price": 150
    },
    "battle_mage_robe": {
        "name": "전투 마법사의 로브",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"magic_defense": 26, "mp": 52, "magic_attack": 16, "spirit": 8},
        "unique_effect": "spell_power:0.15|mp_cost_reduction:0.10",
        "sell_price": 750
    },
    "sorcerer_vestments": {
        "name": "마도사의 예복",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"magic_defense": 42, "mp": 78, "magic_attack": 23, "spirit": 12},
        "unique_effect": "mp_regen:10|spell_power:0.10|magic_defense_boost:0.25",
        "sell_price": 2000
    },
    "wisdom_robes": {
        "name": "지혜의 로브",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"magic_defense": 31, "mp": 78, "spirit": 18, "magic_attack": 13},
        "unique_effect": "spell_success:0.20",  # 스킬 성공률 +20%
        "sell_price": 950
    },
    "elemental_master_robe": {
        "name": "원소 대가의 로브",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"magic_defense": 47, "mp": 84, "magic_attack": 26, "spirit": 13},
        "unique_effect": "all_element_resist:0.20|elemental_mastery:0.25",
        "sell_price": 2400
    },
    "mana_weave_cloak": {
        "name": "마나직 망토",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"magic_defense": 36, "mp": 65, "spirit": 10},
        "unique_effect": "mp_cost_reduction:0.25|magic_defense_boost:0.30",
        "sell_price": 1100
    },
    "spell_reflect_robe": {
        "name": "주문 반사 로브",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"magic_defense": 55, "mp": 72, "spirit": 14},
        "unique_effect": "spell_reflect:0.30",
        "sell_price": 2700
    },

    # === HP/MP 재생 방어구 ===
    "troll_hide": {
        "name": "트롤 가죽",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 25, "hp": 78},
        "unique_effect": "hp_regen:0.05|weakness_fire",
        "sell_price": 600
    },
    "phoenix_mail": {
        "name": "불사조 갑옷",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_defense": 49, "magic_defense": 39, "hp": 98},
        "unique_effect": "hp_regen:0.03|phoenix_rebirth",
        "sell_price": 2800
    },
    "mana_silk_robe": {
        "name": "마나 실크 로브",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"magic_defense": 29, "mp": 52, "magic_attack": 10},
        "unique_effect": "mp_regen:8|mp_cost_reduction:0.10",
        "sell_price": 750
    },
    "archmage_vestments": {
        "name": "대마법사의 예복",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"magic_defense": 46, "mp": 98, "magic_attack": 23, "spirit": 12},
        "unique_effect": "mp_regen:12|spell_power:0.15|spell_reflect:0.20",
        "sell_price": 2500
    },

    # === 가시/반사 방어구 ===
    "thorned_armor": {
        "name": "가시 갑옷",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_defense": 21, "hp": 39},
        "unique_effect": "thorns:0.25",
        "sell_price": 350
    },
    "reflecting_plate": {
        "name": "반사 판금",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"physical_defense": 47, "magic_defense": 36, "hp": 91},
        "unique_effect": "thorns:0.40|spell_reflect:0.50",
        "sell_price": 2200
    },
    "vengeful_mail": {
        "name": "복수의 갑옷",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_defense": 36, "hp": 72, "strength": 5},
        "unique_effect": "counter_attack:0.30|vengeance_damage:0.20",
        "sell_price": 1100
    },

    # === 방어/블록 방어구 ===
    "tower_shield_armor": {
        "name": "탑 방패 갑옷",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_defense": 42, "hp": 98, "speed": -2},
        "unique_effect": "block_chance:0.30|block_perfect",
        "sell_price": 950
    },
    "adamantine_armor": {
        "name": "아다만타이트 갑옷",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 10,
        "base_stats": {"physical_defense": 58, "magic_defense": 46, "hp": 130},
        "unique_effect": "flat_damage_reduction:15|crit_immunity",
        "sell_price": 3200
    },
    "guardian_plate": {
        "name": "수호자의 판금",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_defense": 52, "magic_defense": 39, "hp": 117},
        "unique_effect": "ally_protect:0.10|damage_redirect",
        "sell_price": 2400
    },

    # === 회피 방어구 ===
    "mirage_vestments": {
        "name": "신기루 예복",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"magic_defense": 36, "evasion": 23, "speed": 8, "luck": 6},
        "unique_effect": "dodge_chance:0.35|dodge_counter",
        "sell_price": 2000
    },
    "windwalker_armor": {
        "name": "바람걸음 갑옷",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 23, "evasion": 13, "speed": 10},
        "unique_effect": "dodge_chance:0.20|brv_steal:0.30",
        "sell_price": 800
    },

    # === 속성 저항 방어구 ===
    "fire_dragon_scale": {
        "name": "화염 드래곤 비늘",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"physical_defense": 46, "magic_defense": 42, "hp": 91},
        "unique_effect": "fire_resist:1.0|fire_absorb",
        "sell_price": 2300
    },
    "frost_plate": {
        "name": "서리 판금",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_defense": 38, "magic_defense": 32, "hp": 72},
        "unique_effect": "ice_immunity|on_hit_slow:0.30",
        "sell_price": 1200
    },
    "storm_mail": {
        "name": "폭풍 갑옷",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 42, "magic_defense": 39, "hp": 78, "speed": 5},
        "unique_effect": "lightning_immunity|lightning_reflect",
        "sell_price": 1900
    },
    "rainbow_robe": {
        "name": "무지개 로브",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"magic_defense": 49, "spirit": 13, "hp": 84, "mp": 52},
        "unique_effect": "all_element_resist:0.30",
        "sell_price": 2700
    },

    # === 상태 이상 관련 방어구 ===
    "immunity_cloak": {
        "name": "면역 망토",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"magic_defense": 31, "hp": 65, "spirit": 6},
        "unique_effect": "status_immunity:poison,burn,bleed",
        "sell_price": 950
    },
    "cleansing_armor": {
        "name": "정화의 갑옷",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"physical_defense": 47, "magic_defense": 42, "hp": 98, "spirit": 10},
        "unique_effect": "debuff_duration:-0.50|cleanse_on_turn:0.30",  # 30% 확률로 디버프 제거
        "sell_price": 2300
    },
    "stalwart_plate": {
        "name": "불굴의 판금",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_defense": 52, "hp": 117, "spirit": 8},
        "unique_effect": "cc_immunity:stun,sleep,confusion",
        "sell_price": 2500
    },

    # === 특수 기믹 방어구 ===
    "glass_armor": {
        "name": "유리 갑옷",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 13, "magic_defense": 10},
        "unique_effect": "glass_cannon:damage:0.30|taken:0.50",
        "sell_price": 1200
    },
    "bloodthirst_armor": {
        "name": "피의 갈증 갑옷",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_defense": 46, "hp": 98, "strength": 6},
        "unique_effect": "on_kill:max_hp:10|stack_max:10",
        "sell_price": 2600
    },
    "adaptive_mail": {
        "name": "적응형 갑옷",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 9,
        "base_stats": {"physical_defense": 49, "magic_defense": 49, "hp": 104},
        "unique_effect": "adaptive_resistance:0.20|duration:3",
        "sell_price": 2900
    },

    # === 레전더리 방어구 ===
    "aegis_of_eternity": {
        "name": "영원의 이지스",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 9,
        "base_stats": {"physical_defense": 78, "magic_defense": 72, "hp": 195, "all_stats": 10},
        "unique_effect": "block_chance:0.50|immortality:once|all_resist:0.30",
        "sell_price": 15000
    },
    "celestial_raiment": {
        "name": "천상의 예복",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 7,
        "base_stats": {"magic_defense": 72, "mp": 130, "spirit": 16, "magic_attack": 32},
        "unique_effect": "all_element_resist:0.50|wound_immunity|mp_regen:15|spell_power:0.30",
        "sell_price": 13000
    },

    # === Steampunk Armor ===
    "brass_plate_armor": {
        "name": "황동 판금 갑옷",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_defense": 39, "hp": 65, "fire_resist": 13, "water_resist": 13},
        "unique_effect": "fire_resist:0.30",
        "sell_price": 900
    },
    "aviator_jacket": {
        "name": "비행사 자켓",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 16, "speed": 6, "wind_resist": 10},
        "unique_effect": "speed_boost:0.10",
        "sell_price": 400
    },

    # === Apocalypse Armor ===
    "tire_tread_armor": {
        "name": "타이어 갑옷",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_defense": 29, "magic_defense": 3, "hp": 39},
        "unique_effect": "thorns:0.10",
        "sell_price": 250
    },
    "hazmat_suit": {
        "name": "방호복",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_defense": 13, "magic_defense": 13, "hp": 32},
        "unique_effect": "status_immunity:poison,acid,radiation",
        "sell_price": 800
    },

    # === Sci-Fi/Future Armor ===
    "energy_shield_suit": {
        "name": "에너지 실드 수트",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 20, "magic_defense": 20, "mp": 32},
        "unique_effect": "energy_shield:hp:200|regen_shield",
        "sell_price": 2500
    },
    "power_armor_mk1": {
        "name": "파워 아머 MK-1",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {"physical_defense": 78, "magic_defense": 52, "strength": 20, "hp": 162, "speed": -6},
        "unique_effect": "strength_boost:0.20|",
        "sell_price": 10000
    },
    
    # === More Light Armor ===
    "silk_robe": {
        "name": "실크 로브",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"magic_defense": 16, "mp": 20, "speed": 3},
        "unique_effect": "mp_regen:3",
        "sell_price": 200
    },
    "mage_vestments": {
        "name": "마법사 예복",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"magic_defense": 29, "mp": 46, "magic_attack": 16, "spirit": 6},
        "unique_effect": "spell_power:0.15|mp_cost_reduction:0.10",
        "sell_price": 1100
    },
    "archmage_robes": {
        "name": "대마법사 로브",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"magic_defense": 49, "mp": 98, "magic_attack": 29, "spirit": 13},
        "unique_effect": "spell_power:0.30|mp_regen:10|spell_echo:0.15",
        "sell_price": 3800
    },
    "shadow_cloak": {
        "name": "그림자 망토",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_defense": 20, "evasion": 16, "speed": 10},
        "unique_effect": "stealth_bonus|dodge_chance:0.20|shadow_step",
        "sell_price": 1400
    },
    "wind_dancer_garb": {
        "name": "바람춤꾼 의상",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"magic_defense": 39, "evasion": 20, "speed": 13, "wind_power": 23},
        "unique_effect": "dodge_chance:0.30|wind_evasion|tornado_shield",
        "sell_price": 3200
    },

    # === More Medium Armor ===
    "chainmail": {
        "name": "사슬 갑옷",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 2,
        "base_stats": {"physical_defense": 26, "hp": 32},
        "unique_effect": "slash_resist:0.20",
        "sell_price": 250
    },
    "reinforced_leather": {
        "name": "강화 가죽 갑옷",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 36, "magic_defense": 13, "hp": 46},
        "unique_effect": "melee_resist:0.15",
        "sell_price": 480
    },
    "scale_mail": {
        "name": "비늘 갑옷",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_defense": 49, "magic_defense": 23, "hp": 65},
        "unique_effect": "water_resist:0.30|scales_deflection:0.15",
        "sell_price": 1300
    },
    "dragon_scale_mail": {
        "name": "드래곤 비늘 갑옷",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {"physical_defense": 72, "magic_defense": 58, "hp": 162, "fire_resist": 32},
        "unique_effect": "fire_resist:1.0|physical_resist:0.30|dragon_aura",
        "sell_price": 16000
    },
    "samurai_armor": {
        "name": "사무라이 갑옷",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"physical_defense": 46, "magic_defense": 26, "hp": 72, "strength": 6},
        "unique_effect": "counter_attack:0.25|honor_buff",
        "sell_price": 1700
    },

    # === More Heavy Armor ===
    "iron_plate": {
        "name": "철 판금 갑옷",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 42, "hp": 52, "speed": -2},
        "unique_effect": "physical_resist:0.10",
        "sell_price": 400
    },
    "steel_full_plate": {
        "name": "강철 전신 갑옷",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_defense": 62, "hp": 98, "strength": 5, "speed": -3},
        "unique_effect": "physical_resist:0.25|immovable",
        "sell_price": 1500
    },
    "crusader_plate": {
        "name": "십자군 갑옷",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 72, "magic_defense": 39, "hp": 117, "spirit": 10},
        "unique_effect": "holy_protection|undead_resist:0.50|faith_shield",
        "sell_price": 3500
    },
    "obsidian_armor": {
        "name": "흑요석 갑옷",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 11,
        "base_stats": {"physical_defense": 84, "magic_defense": 72, "hp": 182, "dark_power": 32},
        "unique_effect": "magic_reflect:0.30|curse_immunity|dark_absorption",
        "sell_price": 19000
    },
    "titan_armor": {
        "name": "타이탄 갑옷",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 12,
        "base_stats": {"physical_defense": 98, "hp": 228, "strength": 23, "speed": -5},
        "unique_effect": "giant_strength|knockback_immunity|earthquake_step",
        "sell_price": 22000
    },

    # === Elemental Armor ===
    "ice_crystal_plate": {
        "name": "빙정 판금",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"physical_defense": 55, "magic_defense": 62, "hp": 104, "ice_power": 32},
        "unique_effect": "ice_immunity|freeze_aura:0.20|slow_attackers:0.30",
        "sell_price": 4200
    },
    "thunder_plate": {
        "name": "뇌전 판금",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"physical_defense": 58, "magic_defense": 52, "hp": 98, "lightning_power": 36},
        "unique_effect": "lightning_immunity|shock_counter:0.40|speed_boost:0.15",
        "sell_price": 4100
    },
    "earth_fortress_armor": {
        "name": "대지 요새 갑옷",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 78, "magic_defense": 32, "hp": 143, "earth_power": 26},
        "unique_effect": "earth_wall|hp_regen:0.02|immovable_stance",
        "sell_price": 3600
    },
    "void_armor": {
        "name": "공허의 갑옷",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 11,
        "base_stats": {"physical_defense": 65, "magic_defense": 78, "hp": 130, "dark_power": 39, "void_power": 32},
        "unique_effect": "void_phase:0.25|damage_absorption:0.20|existence_denial",
        "sell_price": 20000
    },

    # === Special/Themed Armor ===
    "berserker_hide": {
        "name": "광전사의 가죽",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_defense": 39, "hp": 84, "strength": 10},
        "unique_effect": "low_hp_damage:0.50|pain_tolerance|rage_boost",
        "sell_price": 1450
    },
    "necromancer_robes": {
        "name": "강령술사 로브",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"magic_defense": 52, "mp": 91, "magic_attack": 26, "dark_power": 29},
        "unique_effect": "undead_command|lifesteal:0.15|death_magic:0.30",
        "sell_price": 3900
    },
    "assassin_leather": {
        "name": "암살자 가죽",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"physical_defense": 32, "evasion": 20, "speed": 12, "critical": 10},
        "unique_effect": "stealth|backstab_damage:0.50|silent_movement",
        "sell_price": 1800
    },
    "paladin_holy_armor": {
        "name": "성기사 신성 갑옷",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {"physical_defense": 75, "magic_defense": 62, "hp": 156, "spirit": 20},
        "unique_effect": "holy_protection|auto_revive:once|heal_aura:0.10|faith_barrier",
        "sell_price": 17000
    },
    "ninja_garb": {
        "name": "닌자 의상",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 29, "magic_defense": 23, "evasion": 23, "speed": 14},
        "unique_effect": "invisibility:3turns|dodge_chance:0.35|ninjutsu_power:0.25",
        "sell_price": 3400
    },
    "warlock_vestments": {
        "name": "흑마술사 예복",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"magic_defense": 46, "mp": 117, "magic_attack": 32, "dark_power": 26},
        "unique_effect": "curse_power:0.40|mp_drain:0.10|forbidden_magic:0.30",
        "sell_price": 4000
    },
    "monk_robes": {
        "name": "수도승 로브",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"physical_defense": 36, "magic_defense": 46, "hp": 72, "spirit": 13},
        "unique_effect": "meditation:hp_mp_regen|counter_attack:0.30|inner_peace",
        "sell_price": 1650
    },

    # === More Steampunk Armor ===
    "gear_plated_vest": {
        "name": "기어 판금 조끼",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 32, "hp": 46},
        "unique_effect": "dodge_chance:0.10|speed_boost:0.10",
        "sell_price": 520
    },
    "steam_powered_exosuit": {
        "name": "증기 파워 외골격",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 9,
        "base_stats": {"physical_defense": 65, "strength": 16, "hp": 130, "speed": -4},
        "unique_effect": "strength_boost:0.30||status_burn:0.15_counter",
        "sell_price": 5200
    },

    # === More Apocalypse Armor ===
    "scrap_metal_vest": {
        "name": "고철 조끼",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_defense": 20, "hp": 26},
        "unique_effect": "physical_resist:0.10",
        "sell_price": 150
    },
    "gas_mask_armor": {
        "name": "방독면 갑옷",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 29, "hp": 39},
        "unique_effect": "poison_immunity|poison_immunity",
        "sell_price": 600
    },
    "raider_leather": {
        "name": "약탈자 가죽",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_defense": 42, "speed": 8, "critical": 6, "hp": 58},
        "unique_effect": "gold_find:0.20|critical_chance:0.10",
        "sell_price": 1250
    },

    # === More Sci-Fi Armor ===
    "nano_weave_suit": {
        "name": "나노섬유 슈트",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"physical_defense": 39, "magic_defense": 39, "hp": 65, "speed": 5},
        "unique_effect": "damage_reduction:0.15|hp_regen:0.02",
        "sell_price": 1900
    },
    "quantum_plate": {
        "name": "양자 판금",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 12,
        "base_stats": {"physical_defense": 81, "magic_defense": 81, "hp": 169, "evasion": 13},
        "unique_effect": "quantum_evasion:0.30|superposition|reality_shift",
        "sell_price": 24000
    },
    "plasma_shield_armor": {
        "name": "플라즈마 실드 갑옷",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 9,
        "base_stats": {"physical_defense": 46, "magic_defense": 65, "mp": 65},
        "unique_effect": "plasma_shield:250|energy_absorb|burn_counter:0.35",
        "sell_price": 5000
    },
    "cryogenic_suit": {
        "name": "극저온 슈트",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 42, "magic_defense": 46, "hp": 78, "ice_power": 23},
        "unique_effect": "ice_immunity|freeze_aura:0.25|cold_storage",
        "sell_price": 2100
    },



    
    # === Additional Common Armor ===
    "cloth_armor": {"name": "천 갑옷", "description": "", "rarity": ItemRarity.COMMON, "level_requirement": 1, "base_stats": {"physical_defense": 5, "hp": 10}, "sell_price": 30},
    "hide_armor": {"name": "가죽 갑옷", "description": "", "rarity": ItemRarity.COMMON, "level_requirement": 1, "base_stats": {"physical_defense": 8, "hp": 13}, "sell_price": 40},
    "simple_robe": {"name": "간단한 로브", "description": "", "rarity": ItemRarity.COMMON, "level_requirement": 1, "base_stats": {"magic_defense": 6, "mp": 13}, "sell_price": 35},
    
    # === More Uncommon Armor ===
    "leather_vest": {"name": "가죽 조끼", "description": "", "rarity": ItemRarity.UNCOMMON, "level_requirement": 2, "base_stats": {"physical_defense": 13, "evasion": 3, "hp": 23}, "sell_price": 100},
    "bronze_plate": {"name": "청동 판금", "description": "", "rarity": ItemRarity.UNCOMMON, "level_requirement": 3, "base_stats": {"physical_defense": 21, "hp": 39}, "sell_price": 180},
    "apprentice_robes": {"name": "견습생 로브", "description": "", "rarity": ItemRarity.UNCOMMON, "level_requirement": 2, "base_stats": {"magic_defense": 14, "mp": 32, "spirit": 3}, "sell_price": 120},
    "banded_mail": {"name": "띠갑옷", "description": "", "rarity": ItemRarity.UNCOMMON, "level_requirement": 3, "base_stats": {"physical_defense": 18, "hp": 32, "strength": 2}, "sell_price": 160},

    # ============================================
    # === 오마주 방어구 (다양한 시대/매체) ===
    # ============================================
    
    # === 판타지/RPG 고전작 오마주 ===
    "soldier_uniform": {
        "name": "병사 1등급 제복",
        "description": "영웅의 출발점이 되었던 제복.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"physical_defense": 55, "hp": 80, "strength": 8},
        "unique_effect": "strength_boost:0.15",
        "sell_price": 3500
    },
    "materia_armor": {
        "name": "마테리아 갑옷",
        "description": "마테리아를 장착할 수 있는 갑옷.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"physical_defense": 85, "magic_defense": 65, "hp": 120, "mp": 60},
        "unique_effect": "spell_power:0.20|mp_regen:8",
        "sell_price": 12000
    },
    "genji_armor_set": {
        "name": "겐지 갑옷",
        "description": "전설적인 겐지 가문의 갑옷.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 22,
        "base_stats": {"physical_defense": 110, "magic_defense": 90, "hp": 180, "all_stats": 8},
        "unique_effect": "all_resist:0.30|counter_attack:0.25",
        "sell_price": 22000
    },
    "crystal_mail": {
        "name": "크리스탈 갑옷",
        "description": "마법 수정으로 만든 갑옷.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 15,
        "base_stats": {"physical_defense": 75, "magic_defense": 85, "hp": 100, "mp": 50},
        "unique_effect": "all_element_resist:0.25",
        "sell_price": 8500
    },
    "hylian_armor": {
        "name": "하이랄 갑옷",
        "description": "하이랄 왕국의 기사 갑옷.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 17,
        "base_stats": {"physical_defense": 90, "magic_defense": 60, "hp": 130},
        "unique_effect": "holy_protection|block_chance:0.20",
        "sell_price": 10000
    },
    "sheikah_stealth_armor": {
        "name": "시커 은신 갑옷",
        "description": "그림자처럼 움직이는 닌자 갑옷.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 12,
        "base_stats": {"physical_defense": 45, "evasion": 25, "speed": 15},
        "unique_effect": "stealth_bonus|dodge_chance:0.25",
        "sell_price": 5500
    },
    "barbarian_armor_wild": {
        "name": "야만인 갑옷",
        "description": "야생의 힘이 깃든 갑옷.",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 6,
        "base_stats": {"physical_defense": 35, "strength": 10, "hp": 60},
        "unique_effect": "strength_boost:0.10|low_hp_bonus:0.30",
        "sell_price": 1200
    },
    "zora_scale_armor": {
        "name": "조라 갑옷",
        "description": "수중 활동에 최적화된 갑옷.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 11,
        "base_stats": {"physical_defense": 55, "magic_defense": 45, "speed": 10},
        "unique_effect": "water_immunity|speed_boost:0.15",
        "sell_price": 4500
    },
    
    # === 역사적 오마주 ===
    "lorica_segmentata_roman": {
        "name": "로리카 세그멘타타",
        "description": "로마 군단병의 판갑.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 9,
        "base_stats": {"physical_defense": 52, "hp": 70, "strength": 6},
        "unique_effect": "damage_reduction:0.15",
        "sell_price": 2800
    },
    "byzantine_cataphract_armor": {
        "name": "비잔틴 카타프락트",
        "description": "비잔틴 중기병의 갑옷.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 16,
        "base_stats": {"physical_defense": 95, "hp": 140, "strength": 10},
        "unique_effect": "damage_reduction:0.25|knockback_immunity",
        "sell_price": 9000
    },
    "mongol_lamellar_armor": {
        "name": "몽골 찰갑",
        "description": "대초원의 정복자들의 갑옷.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"physical_defense": 50, "evasion": 12, "speed": 8},
        "unique_effect": "speed_boost:0.15|dodge_chance:0.10",
        "sell_price": 3200
    },
    "edo_period_yoroi": {
        "name": "에도 요로이",
        "description": "전국시대 사무라이의 갑옷.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 14,
        "base_stats": {"physical_defense": 72, "magic_defense": 45, "hp": 100},
        "unique_effect": "counter_attack:0.25|honor_buff",
        "sell_price": 6500
    },
    "hwarang_armor_korea": {
        "name": "화랑 갑옷",
        "description": "신라 화랑의 갑옷.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 15,
        "base_stats": {"physical_defense": 78, "magic_defense": 55, "hp": 110, "spirit": 10},
        "unique_effect": "holy_damage:0.20|speed_boost:0.10",
        "sell_price": 7500
    },
    "qin_dynasty_armor": {
        "name": "진나라 갑옷",
        "description": "진시황 군대의 갑옷.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 11,
        "base_stats": {"physical_defense": 60, "hp": 85, "strength": 8},
        "unique_effect": "damage_reduction:0.18",
        "sell_price": 4000
    },
    "spartan_bronze_armor": {
        "name": "스파르탄 갑옷",
        "description": "스파르타 전사의 청동 갑옷.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 12,
        "base_stats": {"physical_defense": 65, "hp": 90, "strength": 12},
        "unique_effect": "block_chance:0.25|low_hp_bonus:0.40",
        "sell_price": 4800
    },
    "viking_chainmail_heavy": {
        "name": "바이킹 쇄자갑",
        "description": "북해 약탈자의 쇄자갑.",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 42, "hp": 55, "strength": 6},
        "unique_effect": "lifesteal:0.08",
        "sell_price": 1600
    },
    
    # === 애니메이션/게임 오마주 ===
    "survey_corps_jacket": {
        "name": "조사병단 재킷",
        "description": "자유의 날개가 새겨진 재킷.",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 5,
        "base_stats": {"physical_defense": 28, "evasion": 15, "speed": 12},
        "unique_effect": "speed_boost:0.20|dodge_chance:0.15",
        "sell_price": 850
    },
    "kamui_living_armor": {
        "name": "카무이 생명섬유",
        "description": "생명섬유로 만든 전투복.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 24,
        "base_stats": {"physical_defense": 95, "magic_defense": 80, "speed": 20, "all_stats": 10},
        "unique_effect": "all_damage:0.30|hp_regen:0.05|low_hp_bonus:0.50",
        "sell_price": 25000
    },
    "soul_reaper_shihakusho": {
        "name": "사신의 로브",
        "description": "영혼 세계의 전투복.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 16,
        "base_stats": {"physical_defense": 65, "magic_defense": 75, "speed": 12, "spirit": 15},
        "unique_effect": "spell_power:0.25|speed_boost:0.15",
        "sell_price": 9000
    },
    "incursio_imperial": {
        "name": "인큐르시오",
        "description": "진화하는 갑옷 티이거.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 23,
        "base_stats": {"physical_defense": 115, "magic_defense": 85, "hp": 160, "strength": 18},
        "unique_effect": "damage_reduction:0.30|hp_regen:0.03|counter_attack:0.30",
        "sell_price": 23000
    },
    "nazarick_supreme_robe": {
        "name": "나자릭 대로브",
        "description": "지고의 마도왕의 로브.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 26,
        "base_stats": {"magic_defense": 140, "mp": 180, "magic_attack": 50, "spirit": 25},
        "unique_effect": "spell_power:0.40|all_element_resist:0.40|mp_regen:15",
        "sell_price": 32000
    },
    "organization_black_coat": {
        "name": "조직의 코트",
        "description": "어둠의 회랑을 걷는 자의 코트.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 14,
        "base_stats": {"physical_defense": 55, "magic_defense": 70, "evasion": 15},
        "unique_effect": "dark_resist:1.0|stealth_bonus",
        "sell_price": 6800
    },
    
    # === SF/현대 오마주 ===
    "spartan_mjolnir_armor": {
        "name": "묠니르 파워 아머",
        "description": "초인적인 전투력을 부여하는 갑옷.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 25,
        "base_stats": {"physical_defense": 130, "magic_defense": 90, "hp": 200, "strength": 25},
        "unique_effect": "strength_boost:0.30|damage_reduction:0.25|knockback_immunity",
        "sell_price": 28000
    },
    "n7_combat_armor": {
        "name": "N7 전투 갑옷",
        "description": "은하계 최고 특수부대의 갑옷.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"physical_defense": 85, "magic_defense": 70, "hp": 130, "evasion": 10},
        "unique_effect": "damage_reduction:0.20|hp_regen:0.02",
        "sell_price": 11000
    },
    "synth_suit_fallout": {
        "name": "합성인간 슈트",
        "description": "고도의 기술로 만든 전투복.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 13,
        "base_stats": {"physical_defense": 60, "magic_defense": 55, "speed": 10},
        "unique_effect": "damage_reduction:0.15|stealth_bonus",
        "sell_price": 5200
    },
    "vault_suit": {
        "name": "격리실 슈트",
        "description": "핵전쟁 생존자의 기본 슈트.",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 4,
        "base_stats": {"physical_defense": 22, "hp": 40, "luck": 8},
        "unique_effect": "status_immunity:radiation",
        "sell_price": 450
    },
    "praetor_suit_doom": {
        "name": "프레이터 슈트",
        "description": "지옥을 정복한 전사의 갑옷.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 27,
        "base_stats": {"physical_defense": 145, "magic_defense": 100, "hp": 220, "strength": 22},
        "unique_effect": "all_damage:0.35|lifesteal:0.20|fire_resist:1.0",
        "sell_price": 35000
    },
    "eva_plugsuit": {
        "name": "에바 플러그슈트",
        "description": "거대 로봇과 동조하는 슈트.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 19,
        "base_stats": {"physical_defense": 70, "magic_defense": 90, "mp": 80, "spirit": 18},
        "unique_effect": "spell_power:0.25|mp_regen:10",
        "sell_price": 12500
    },
    "mobile_suit_pilot": {
        "name": "모빌슈트 파일럿복",
        "description": "거대 로봇 조종사의 슈트.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 28,
        "base_stats": {"physical_defense": 140, "magic_defense": 110, "hp": 190, "speed": 15},
        "unique_effect": "all_damage:0.30|dodge_chance:0.25",
        "sell_price": 38000
    },
    
    # === 다크소울 시리즈 오마주 ===
    "elite_knight_armor": {
        "name": "엘리트 기사 갑옷",
        "description": "이상적인 균형의 기사 갑옷.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 15,
        "base_stats": {"physical_defense": 80, "magic_defense": 55, "hp": 110, "strength": 8},
        "unique_effect": "damage_reduction:0.20|block_chance:0.15",
        "sell_price": 7800
    },
    "faraam_plate_armor": {
        "name": "파람 갑옷",
        "description": "전쟁의 신을 숭배하는 기사의 갑옷.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 21,
        "base_stats": {"physical_defense": 105, "magic_defense": 70, "hp": 150, "strength": 15},
        "unique_effect": "strength_boost:0.20|critical_damage:0.40",
        "sell_price": 18000
    },
    "artorias_wolf_armor": {
        "name": "아르토리아스 갑옷",
        "description": "심연을 걷는 기사의 갑옷.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 24,
        "base_stats": {"physical_defense": 115, "magic_defense": 95, "hp": 170, "speed": 12},
        "unique_effect": "all_damage:0.25|dark_resist:0.50|speed_boost:0.15",
        "sell_price": 24000
    },
    "havel_rock_armor": {
        "name": "하벨의 갑옷",
        "description": "암석처럼 단단한 갑옷.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 26,
        "base_stats": {"physical_defense": 160, "magic_defense": 120, "hp": 250, "speed": -10},
        "unique_effect": "damage_reduction:0.35|knockback_immunity|stun_immunity",
        "sell_price": 30000
    },
    "black_knight_armor_ds": {
        "name": "흑기사 갑옷",
        "description": "화염에 그을린 기사의 갑옷.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 20,
        "base_stats": {"physical_defense": 95, "magic_defense": 75, "hp": 140, "fire_power": 20},
        "unique_effect": "fire_resist:0.50|fire_damage:0.20",
        "sell_price": 14000
    },
    "ornstein_golden_armor": {
        "name": "오른스타인 갑옷",
        "description": "용 사냥꾼의 황금 갑옷.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 25,
        "base_stats": {"physical_defense": 120, "magic_defense": 85, "hp": 160, "lightning_power": 35},
        "unique_effect": "lightning_damage:0.35|speed_boost:0.20",
        "sell_price": 27000
    },
    "smough_executioner_armor": {
        "name": "스모우 갑옷",
        "description": "처형자의 거대한 갑옷.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 27,
        "base_stats": {"physical_defense": 170, "hp": 280, "strength": 30, "speed": -15},
        "unique_effect": "hp_percent:0.20|knockback_immunity|stun_chance:0.30",
        "sell_price": 33000
    },
    
    # === 추가 방어구: 다양한 레벨 분포 ===
    # 레벨 1-5
    "peasant_garb": {
        "name": "농부의 옷",
        "description": "평범한 농부의 옷.",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_defense": 3, "hp": 15},
        "sell_price": 20
    },
    "travelers_cloak": {
        "name": "여행자의 망토",
        "description": "모험의 시작에 적합한 망토.",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 2,
        "base_stats": {"physical_defense": 8, "magic_defense": 6, "speed": 3},
        "sell_price": 50
    },
    "militia_armor": {
        "name": "민병대 갑옷",
        "description": "마을 경비병의 갑옷.",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 4,
        "base_stats": {"physical_defense": 25, "hp": 40},
        "sell_price": 280
    },
    "apprentice_mage_robe": {
        "name": "견습 마법사 로브",
        "description": "마법 학교 학생의 로브.",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 5,
        "base_stats": {"magic_defense": 22, "mp": 35, "spirit": 6},
        "unique_effect": "mp_regen:3",
        "sell_price": 350
    },
    
    # 레벨 6-10
    "mercenary_armor": {
        "name": "용병 갑옷",
        "description": "전장을 누비는 용병의 갑옷.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 45, "hp": 65, "strength": 6},
        "unique_effect": "gold_find:0.20",
        "sell_price": 1800
    },
    "battle_mage_vest": {
        "name": "전투 마법사 조끼",
        "description": "마법 전사를 위한 조끼.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 8,
        "base_stats": {"physical_defense": 38, "magic_defense": 45, "mp": 45},
        "unique_effect": "spell_power:0.15",
        "sell_price": 2200
    },
    "scout_leather": {
        "name": "정찰병 가죽",
        "description": "빠른 이동을 위한 경갑.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 9,
        "base_stats": {"physical_defense": 40, "evasion": 18, "speed": 12},
        "unique_effect": "speed_boost:0.15|dodge_chance:0.15",
        "sell_price": 2600
    },
    "templar_armor": {
        "name": "템플러 갑옷",
        "description": "성전 기사의 갑옷.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"physical_defense": 58, "magic_defense": 45, "hp": 75, "spirit": 8},
        "unique_effect": "holy_protection",
        "sell_price": 3500
    },
    
    # 레벨 11-15
    "knight_commander_armor": {
        "name": "기사단장 갑옷",
        "description": "기사단을 이끄는 지휘관의 갑옷.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 13,
        "base_stats": {"physical_defense": 72, "magic_defense": 50, "hp": 100, "all_stats": 5},
        "unique_effect": "leadership:0.15|damage_reduction:0.15",
        "sell_price": 6000
    },
    "archmage_battle_robe": {
        "name": "대마법사 전투 로브",
        "description": "전장에서 싸우는 마법사의 로브.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 14,
        "base_stats": {"magic_defense": 68, "mp": 80, "magic_attack": 25, "spirit": 12},
        "unique_effect": "spell_power:0.25|mp_cost_reduction:0.15",
        "sell_price": 6800
    },
    
    # 레벨 16-20
    "warlord_plate": {
        "name": "전쟁군주 판금",
        "description": "전쟁을 이끄는 군주의 갑옷.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 17,
        "base_stats": {"physical_defense": 92, "hp": 145, "strength": 15},
        "unique_effect": "strength_boost:0.20|damage_reduction:0.20",
        "sell_price": 10500
    },
    "high_sorcerer_robe": {
        "name": "대마도사 로브",
        "description": "마법의 정점에 도달한 자의 로브.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 19,
        "base_stats": {"magic_defense": 85, "mp": 110, "magic_attack": 35, "spirit": 18},
        "unique_effect": "spell_power:0.35|all_element_damage:0.20",
        "sell_price": 13000
    },
    
    # 레벨 21-25
    "dragon_knight_armor": {
        "name": "드래곤 기사 갑옷",
        "description": "용과 계약한 기사의 갑옷.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 22,
        "base_stats": {"physical_defense": 110, "magic_defense": 85, "hp": 165, "fire_power": 30},
        "unique_effect": "fire_resist:0.60|fire_damage:0.30",
        "sell_price": 21000
    },
    "void_walker_robe": {
        "name": "공허 보행자 로브",
        "description": "차원을 넘나드는 마법사의 로브.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 23,
        "base_stats": {"magic_defense": 100, "mp": 140, "magic_attack": 45, "spirit": 22},
        "unique_effect": "spell_power:0.40|dodge_chance:0.20|mp_regen:12",
        "sell_price": 23000
    },
    
    # 레벨 26-30
    "celestial_plate": {
        "name": "천상의 판금",
        "description": "천계에서 내려온 신성한 갑옷.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 26,
        "base_stats": {"physical_defense": 135, "magic_defense": 120, "hp": 200, "spirit": 20},
        "unique_effect": "holy_protection|damage_reduction:0.30|hp_regen:0.04",
        "sell_price": 32000
    },
    "abyssal_armor": {
        "name": "심연의 갑옷",
        "description": "심연의 어둠으로 만든 갑옷.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 27,
        "base_stats": {"physical_defense": 125, "magic_defense": 140, "hp": 180, "dark_power": 45},
        "unique_effect": "dark_resist:1.0|lifesteal:0.20|curse_immunity",
        "sell_price": 35000
    },
    "emperor_regalia": {
        "name": "황제의 예복",
        "description": "세계를 다스리는 황제의 예복.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 28,
        "base_stats": {"physical_defense": 145, "magic_defense": 130, "hp": 220, "all_stats": 15},
        "unique_effect": "all_resist:0.35|leadership:0.30",
        "sell_price": 40000
    },
    "god_slayer_armor": {
        "name": "신살 갑옷",
        "description": "신을 쓰러뜨린 영웅의 갑옷.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 29,
        "base_stats": {"physical_defense": 155, "magic_defense": 145, "hp": 240, "all_stats": 18},
        "unique_effect": "all_damage:0.35|damage_reduction:0.30",
        "sell_price": 48000
    },
    "primordial_vestments": {
        "name": "태초의 예복",
        "description": "세계 창조 시 함께 태어난 예복.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 30,
        "base_stats": {"physical_defense": 170, "magic_defense": 160, "hp": 280, "all_stats": 22},
        "unique_effect": "all_resist:0.50|hp_regen:0.06|mp_regen:15",
        "sell_price": 65000
    },
}


ACCESSORY_TEMPLATES = {
    # 반지
    "health_ring": {
        "name": "생명의 반지",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"hp": 20},
        "sell_price": 60
    },
    "mana_ring": {
        "name": "마나의 반지",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"mp": 13},
        "sell_price": 60
    },
    "ring_of_strength": {
        "name": "힘의 반지",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 1,
        "base_stats": {"strength": 3, "physical_attack": 5},
        "sell_price": 100
    },
    "ring_of_wisdom": {
        "name": "지혜의 반지",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 1,
        "base_stats": {"magic_attack": 5, "mp": 13},
        "sell_price": 100
    },
    "ring_of_agility": {
        "name": "민첩의 반지",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"speed": 5, "evasion": 6},
        "sell_price": 120
    },
    "phoenix_ring": {
        "name": "불사조의 반지",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"hp": 78, "magic_defense": 13},
        "sell_price": 1800
    },
    "ring_of_gods": {
        "name": "신의 반지",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {
            "physical_attack": 13, "magic_attack": 13,
            "physical_defense": 10, "magic_defense": 10,
            "hp": 65, "mp": 32, "speed": 6
        },
        "sell_price": 5000
    },

    # 목걸이/부적
    "amulet_of_life": {
        "name": "생명의 부적",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 2,
        "base_stats": {"hp": 65, "physical_defense": 6},
        "sell_price": 400
    },
    "amulet_of_mana": {
        "name": "마나의 부적",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 2,
        "base_stats": {"mp": 52, "magic_defense": 6},
        "sell_price": 400
    },
    "dragon_pendant": {
        "name": "용의 펜던트",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 12, "magic_attack": 12, "hp": 46},
        "sell_price": 1500
    },
    "phoenix_pendant": {
        "name": "불사조 펜던트",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"hp": 98, "mp": 39, "magic_defense": 16},
        "sell_price": 1600
    },
    "lucky_charm": {
        "name": "행운의 부적",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"luck": 6, "accuracy": 6, "evasion": 6, "critical_rate": 10},
        "sell_price": 1500
    },

    # 귀걸이
    "ruby_earring": {
        "name": "루비 귀걸이",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"strength": 5, "physical_attack": 6},
        "sell_price": 180
    },
    "sapphire_earring": {
        "name": "사파이어 귀걸이",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"magic_attack": 8, "mp": 16},
        "sell_price": 180
    },
    "emerald_earring": {
        "name": "에메랄드 귀걸이",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"hp": 39, "magic_defense": 5},
        "sell_price": 170
    },

    # 벨트
    "warriors_belt": {
        "name": "전사의 벨트",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"strength": 5, "hp": 32, "physical_defense": 6},
        "sell_price": 280
    },
    "mages_sash": {
        "name": "마법사의 띠",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"magic_attack": 8, "mp": 26, "magic_defense": 6},
        "sell_price": 300
    },

    # === 시야 시스템 연동 장신구 ===
    "eagle_eye_amulet": {
        "name": "매의 눈 목걸이",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"accuracy": 10, "critical": 3},
        "unique_effect": "vision:1",
        "sell_price": 200
    },
    "far_sight_lens": {
        "name": "원시의 렌즈",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"accuracy": 13, "luck": 5},
        "unique_effect": "vision:1|detect_enemy",
        "sell_price": 600
    },
    "owls_pendant": {
        "name": "부엉이의 펜던트",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"accuracy": 20, "spirit": 8, "luck": 6},
        "unique_effect": "vision:2",
        "sell_price": 1500
    },
    "all_seeing_eye": {
        "name": "전지의 눈",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {"accuracy": 32, "luck": 13, "all_stats": 5},
        "unique_effect": "vision:2|true_sight|detect_hidden",
        "sell_price": 5000
    },
    "explorers_compass": {
        "name": "탐험가의 나침반",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 2,
        "base_stats": {"luck": 10},
        "unique_effect": "vision:1|treasure_finder",
        "sell_price": 450
    },

    # === 상처 관련 장신구 ===
    "wound_ward_ring": {
        "name": "상처 보호 반지",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"hp": 39, "spirit": 5},
        "unique_effect": "wound_reduction:0.40",
        "sell_price": 550
    },
        # === BRV 관련 장신구 ===
    "brave_ring": {
        "name": "브레이브 링",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"strength": 3, "magic_attack": 3},
        "unique_effect": "brv_bonus:0.20",
        "sell_price": 250
    },
    "break_master_badge": {
        "name": "브레이크 마스터 배지",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"strength": 6, "luck": 8},
        "unique_effect": "brv_break_bonus:0.40|brv_steal:0.15",
        "sell_price": 800
    },
    "shield_earring": {
        "name": "실드 귀걸이",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"defense": 8, "spirit": 6},
        "unique_effect": "brv_shield:0.40|brv_protect",
        "sell_price": 700
    },
    "brave_surge_belt": {
        "name": "브레이브 서지 벨트",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"strength": 8, "speed": 5},
        "unique_effect": "brv_regen:15|brv_bonus:0.15",
        "sell_price": 1600
    },

    # === 생명력 흡수 장신구 ===
    "vampire_fang": {
        "name": "흡혈귀의 송곳니",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"hp": 46, "strength": 5},
        "unique_effect": "lifesteal:0.10|hp_regen:0.02",
        "sell_price": 600
    },
    "blood_ruby": {
        "name": "피의 루비",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"hp": 98, "strength": 10},
        "unique_effect": "lifesteal:0.20",
        "sell_price": 1900
    },
    "leech_ring": {
        "name": "흡혈 반지",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"hp": 52, "mp": 26},
        "unique_effect": "lifesteal:0.08|mp_steal:0.08",
        "sell_price": 900
    },

    # === 크리티컬 장신구 ===
    "lucky_coin": {
        "name": "행운의 동전",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"luck": 13, "critical": 6},
        "unique_effect": "critical_chance:0.15",
        "sell_price": 300
    },
    "executioners_token": {
        "name": "처형인의 징표",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"critical": 10, "luck": 10, "strength": 6},
        "unique_effect": "critical_damage:0.60|execute:0.30",
        "sell_price": 1100
    },
    "precision_monocle": {
        "name": "정밀 단안경",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"critical": 13, "accuracy": 20, "luck": 12},
        "unique_effect": "critical_chance:0.25|accuracy_bonus:50_crit",  # 크리티컬은 절대 빗나가지 않음
        "sell_price": 2100
    },

    # === 회피/속도 장신구 ===
    "rabbit_foot": {
        "name": "토끼발",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"evasion": 10, "speed": 5, "luck": 6},
        "unique_effect": "dodge_chance:0.15",
        "sell_price": 250
    },
    "phantom_boots": {
        "name": "유령 장화",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"evasion": 20, "speed": 8, "luck": 8},
        "unique_effect": "dodge_chance:0.30|dodge_counter",
        "sell_price": 950
    },
    "wind_walker_anklet": {
        "name": "바람걸이 발찌",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"speed": 13, "evasion": 10},
        "unique_effect": "first_strike|brv_steal:0.40",
        "sell_price": 750
    },
    "time_stop_watch": {
        "name": "시간 정지 회중시계",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"speed": 16, "all_stats": 5},
        "unique_effect": "double_turn:0.10|first_strike",  # 10% 확률로 2회 행동, 선제공격
        "sell_price": 2400
    },

    # === 방어 장신구 ===
    "iron_skin_ring": {
        "name": "강철 피부 반지",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"defense": 10, "hp": 52},
        "unique_effect": "flat_damage_reduction:10",
        "sell_price": 800
    },
    "titan_heart": {
        "name": "타이탄의 심장",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"hp": 162, "defense": 13},
        "unique_effect": "hp_regen:0.03|overheal_shield",  # 과다 회복 → 실드 전환
        "sell_price": 2600
    },
    "barrier_crystal": {
        "name": "배리어 크리스탈",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"hp": 78, "magic_defense": 16, "spirit": 10},
        "unique_effect": "barrier_on_turn:0.20",
        "sell_price": 1900
    },

    # === MP/마법 장신구 ===
    "arcane_focus": {
        "name": "비전 초점",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"mp": 39, "magic_attack": 12},
        "unique_effect": "mp_regen:6|mp_cost_reduction:0.15",
        "sell_price": 650
    },
    "sorcerers_pendant": {
        "name": "마법사의 펜던트",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"mp": 65, "magic_attack": 20, "spirit": 10},
        "unique_effect": "mp_regen:8|spell_power:0.15|barrier_on_turn:0.15",  # 턴 시작 시 최대 HP 15% 보호막
        "sell_price": 2200
    },
    "infinite_mana_orb": {
        "name": "무한 마나 오브",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 11,
        "base_stats": {"mp": 130, "magic_attack": 39, "spirit": 16},
        "unique_effect": "mp_cost_reduction:0.50|spell_power:0.30|mana_overflow",
        "sell_price": 8000
    },

    # === 상태 이상 관련 장신구 ===
    "antidote_charm": {
        "name": "해독 부적",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 2,
        "base_stats": {"hp": 26, "spirit": 3},
        "unique_effect": "status_immunity:poison,disease",
        "sell_price": 150
    },
    "freedom_amulet": {
        "name": "자유의 목걸이",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"spirit": 12, "hp": 58},
        "unique_effect": "cc_immunity:stun,sleep,confusion,fear",
        "sell_price": 1200
    },
    "purity_ring": {
        "name": "순수의 반지",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"spirit": 16, "hp": -32, "magic_defense": 20},
        "unique_effect": "status_immunity:all",
        "sell_price": 2800
    },
    "cleansing_bell": {
        "name": "정화의 종",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"spirit": 10, "mp": 32},
        "unique_effect": "cleanse_on_turn:1|debuff_resist:0.30",
        "sell_price": 850
    },

    # === 골드/경험치/드롭 장신구 ===
    "golden_scarab": {
        "name": "황금 스카라베",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"luck": 8},
        "unique_effect": "gold_find:0.50",
        "sell_price": 300
    },
    "merchants_signet": {
        "name": "상인의 인장",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"luck": 12},
        "unique_effect": "gold_find:1.00|shop_discount:0.10",
        "sell_price": 700
    },
    "dragons_hoard_ring": {
        "name": "용의 보물 반지",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"luck": 16, "all_stats": 3},
        "unique_effect": "gold_find:1.50|item_rarity:0.30",
        "sell_price": 2500
    },
    "scholars_tome": {
        "name": "학자의 서",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 1,
        "base_stats": {"spirit": 5},
        "unique_effect": "exp_bonus:0.30",
        "sell_price": 250
    },
    "mentor_medallion": {
        "name": "스승의 메달",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"spirit": 10, "all_stats": 2},
        "unique_effect": "exp_bonus:0.50|skill_mastery:0.25",
        "sell_price": 800
    },
    "item_magnet": {
        "name": "아이템 자석",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"luck": 16},
        "unique_effect": "item_find:0.40|auto_pickup",
        "sell_price": 900
    },

    # === 특수 기믹 장신구 ===
    "phoenix_down_pendant": {
        "name": "불사조 깃털 펜던트",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 10,
        "base_stats": {"hp": 98, "mp": 52, "all_stats": 5},
        "unique_effect": "phoenix_rebirth:full",
        "sell_price": 3500
    },
    "second_chance_coin": {
        "name": "두 번째 기회 동전",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 7,
        "base_stats": {"hp": 65, "luck": 10},
        "unique_effect": "phoenix_rebirth:half|charges:2",
        "sell_price": 1600
    },
    "rage_gem": {
        "name": "분노의 보석",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"strength": 10, "hp": 52},
        "unique_effect": "berserk|low_hp_bonus:0.80",
        "sell_price": 950
    },
    "glass_cannon_gem": {
        "name": "유리 대포 보석",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"strength": 13, "magic_attack": 13},
        "unique_effect": "glass_cannon:damage:0.50|defense:-0.30",
        "sell_price": 1100
    },
    "balanced_core": {
        "name": "균형의 핵",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"all_stats": 8},
        "unique_effect": "balanced_stats:0.15",  # 모든 스탯에 15% 보너스
        "sell_price": 2700
    },
    "combo_chain_badge": {
        "name": "콤보 체인 배지",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"speed": 10, "strength": 8, "critical": 6},
        "unique_effect": "combo_bonus:0.20|max_combo:5",
        "sell_price": 2000
    },
    "overload_core": {
        "name": "과부하 코어",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 9,
        "base_stats": {"all_stats": 10},
        "unique_effect": "overload:cost:2.0|effect:2.5",
        "sell_price": 2900
    },

    # === 기믹 강화 장신구 ===
    "gimmick_booster": {
        "name": "기믹 부스터",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"all_stats": 3},
        "unique_effect": "gimmick_boost:0.30",
        "sell_price": 750
    },
    "max_stack_amplifier": {
        "name": "최대 스택 증폭기",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"all_stats": 5},
        "unique_effect": "max_gimmick_increase:2",
        "sell_price": 1800
    },
    "resource_saver": {
        "name": "자원 절약가",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"mp": 39, "spirit": 8},
        "unique_effect": "gimmick_cost_reduction:0.30|mp_cost_reduction:0.20",
        "sell_price": 1000
    },

    # === 레전더리 장신구 ===
    "ring_of_gods": {
        "name": "신들의 반지",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 9,
        "base_stats": {"all_stats": 20},
        "unique_effect": "omnipotent:0.20",  # 모든 효과 20% 증폭
        "sell_price": 15000
    },
    "infinity_stone": {
        "name": "무한석",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 13,
        "base_stats": {"hp": 130, "mp": 195, "all_stats": 13},
        "unique_effect": "infinite_resources|hp_regen:0.05|mp_cost:0",
        "sell_price": 20000
    },
    "omniscient_eye": {
        "name": "전지의 눈동자",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 7,
        "base_stats": {"critical": 32, "accuracy": 65, "luck": 20},
        "unique_effect": "vision:2|true_sight|omniscient|critical_chance:0.50",
        "sell_price": 12000
    },

    # === Steampunk Accessories ===
    "pocket_watch_of_time": {
        "name": "시간의 회중시계",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"speed": 13, "accuracy": 6},
        "unique_effect": "cooldown_reduction:0.20|haste_start",
        "sell_price": 2000
    },
    "goggles_of_insight": {
        "name": "통찰의 고글",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"accuracy": 16, "luck": 6},
        "unique_effect": "detect_hidden|critical_chance:0.10",
        "sell_price": 750
    },

    # === Apocalypse Accessories ===
    "geiger_counter": {
        "name": "가이거 계수기",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"luck": 10},
        "unique_effect": "detect_radiation|loot_bonus:0.10",
        "sell_price": 300
    },
    "survival_kit": {
        "name": "생존 키트",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"hp": 20},
        "unique_effect": "hp_regen:0.02|",
        "sell_price": 100
    },

    # === Sci-Fi/Future Accessories ===
    "holographic_visor": {
        "name": "홀로그램 바이저",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"accuracy": 20, "critical": 10},
        "unique_effect": "analyze_enemy|critical_damage:0.20",
        "sell_price": 1200
    },
    "gravity_boots": {
        "name": "중력 부츠",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"speed": 10, "evasion": 13},
        "unique_effect": "immune_ground_effects|fall_damage_immune",
        "sell_price": 2800
    },
    
    # === More Rings ===
    "ring_of_fire": {
        "name": "화염의 반지",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"magic_attack": 13, "fire_power": 20},
        "unique_effect": "fire_damage:0.40|status_burn:0.20",
        "sell_price": 1100
    },
    "frostbite_ring": {
        "name": "동상 반지",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"magic_attack": 13, "ice_power": 20},
        "unique_effect": "ice_damage:0.40|slow:0.30",
        "sell_price": 1100
    },
    "thunder_ring": {
        "name": "뇌전 반지",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"magic_attack": 13, "lightning_power": 20},
        "unique_effect": "lightning_damage:0.40|chain_lightning:0.15",
        "sell_price": 1100
    },
    "ring_of_protection": {
        "name": "수호의 반지",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"hp": 65, "physical_defense": 10, "magic_defense": 10},
        "unique_effect": "damage_reduction:0.15",
        "sell_price": 1800
    },
    "vampiric_ring": {
        "name": "흡혈 반지",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"hp": 78, "strength": 8},
        "unique_effect": "lifesteal:0.15",
        "sell_price": 2200
    },
    "ring_of_haste": {
        "name": "신속의 반지",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"speed": 16, "evasion": 6},
        "unique_effect": "first_strike|speed_boost:0.15",
        "sell_price": 980
    },
    "giant_ring": {
        "name": "거인의 반지",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"hp": 130, "strength": 13},
        "unique_effect": "hp_percent:0.15",
        "sell_price": 2400
    },
    "archmage_ring": {
        "name": "대마법사의 반지",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"mp": 65, "magic_attack": 20, "spirit": 10},
        "unique_effect": "spell_power:0.20|mp_regen:5",
        "sell_price": 2500
    },
    "assassins_band": {
        "name": "암살자의 밴드",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"critical": 13, "speed": 10},
        "unique_effect": "critical_chance:0.20|backstab:1.0",
        "sell_price": 2100
    },
    "berserker_band": {
        "name": "광전사의 밴드",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"strength": 12, "hp": 52},
        "unique_effect": "low_hp_damage:0.60|berserk",
        "sell_price": 1200
    },
    
    # === More Necklaces/Amulets ===
    "amulet_of_immortality": {
        "name": "불멸의 부적",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {"hp": 162, "spirit": 13},
        "unique_effect": "hp_regen:0.05|wound_immunity",
        "sell_price": 8000
    },
    "necklace_of_elements": {
        "name": "원소의 목걸이",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"magic_attack": 23, "all_elements": 16},
        "unique_effect": "all_element_damage:0.30",
        "sell_price": 3200
    },
    "holy_cross": {
        "name": "성스러운 십자가",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"magic_attack": 20, "spirit": 16},
        "unique_effect": "holy_damage:0.50|undead_slayer:0.80",
        "sell_price": 2800
    },
    "cursed_pendant": {
        "name": "저주받은 펜던트",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 20, "magic_attack": 20},
        "unique_effect": "all_damage:0.40|damage_taken:0.20|critical_damage:0.20",
        "sell_price": 2200
    },
    "amulet_of_souls": {
        "name": "영혼의 부적",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"hp": 58, "mp": 39, "spirit": 10},
        "unique_effect": "on_kill_heal:0.15|soul_harvest",
        "sell_price": 1550
    },
    "necklace_of_wisdom": {
        "name": "지혜의 목걸이",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"mp": 98, "magic_attack": 13, "spirit": 8},
        "unique_effect": "mp_cost_reduction:0.20",
        "sell_price": 1400
    },
    "battle_horn": {
        "name": "전투의 뿔피리",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 16, "physical_defense": 10, "strength": 6},
        "unique_effect": "battle_cry",
        "sell_price": 1300
    },
    "dragons_eye": {
        "name": "용의 눈동자",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"critical": 16, "accuracy": 13, "luck": 10},
        "unique_effect": "critical_chance:0.15|critical_damage:0.50",
        "sell_price": 2900
    },
    
    # === Belts ===
    "leather_belt": {
        "name": "가죽 벨트",
        "description": "",
                "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"hp": 32, "physical_defense": 6},
        "sell_price": 80
    },
    "champion_belt": {
        "name": "챔피언 벨트",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"hp": 65, "strength": 10, "physical_attack": 8},
        "unique_effect": "strength_boost:0.10",
        "sell_price": 1200
    },
    "mage_belt": {
        "name": "마법사 벨트",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"mp": 52, "spirit": 8, "magic_attack": 10},
        "unique_effect": "mp_regen:5",
        "sell_price": 1150
    },
    "assassins_sash": {
        "name": "암살자의 띠",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"speed": 12, "critical": 10, "evasion": 8},
        "unique_effect": "critical_chance:0.12|speed_boost:0.10",
        "sell_price": 1350
    },
    "titans_girdle": {
        "name": "타이탄의 허리띠",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"hp": 117, "strength": 12, "physical_defense": 13},
        "unique_effect": "knockback_immunity|hp_percent:0.12",
        "sell_price": 2600
    },
    "sorcerers_cord": {
        "name": "마술사의 띠",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"mp": 78, "magic_attack": 16, "spirit": 10},
        "unique_effect": "spell_power:0.18|mp_cost_reduction:0.15",
        "sell_price": 2500
    },
    
    # === Special Accessories ===
    "wings_of_icarus": {
        "name": "이카루스의 날개",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {"evasion": 23, "speed": 13},
        "unique_effect": "dodge_chance:0.25",
        "sell_price": 9500
    },
    "crown_of_kings": {
        "name": "왕의 왕관",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 12,
        "base_stats": {"all_stats": 10, "hp": 98, "mp": 65},
        "unique_effect": "leadership:0.25|all_stats_bonus:0.10",
        "sell_price": 12000
    },
    "eye_of_truth": {
        "name": "진실의 눈",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"accuracy": 23, "critical": 12, "luck": 10},
        "unique_effect": "true_sight|critical_chance:0.18",
        "sell_price": 2400
    },
    "gauntlets_of_power": {
        "name": "힘의 건틀릿",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"physical_attack": 23, "strength": 13},
        "unique_effect": "piercing:0.25|stun_chance:0.15",
        "sell_price": 2700
    },
    "demon_mask": {
        "name": "악마의 가면",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 20, "magic_attack": 20},
        "unique_effect": "all_damage:0.30|hp_penalty:-0.15|critical_damage:0.20",
        "sell_price": 2200
    },
    "angel_halo": {
        "name": "천사의 후광",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"hp": 91, "spirit": 13, "mp": 52},
        "unique_effect": "hp_regen:0.03|status_resist:0.30|holy_aura",
        "sell_price": 2800
    },
    "thiefs_glove": {
        "name": "도적의 장갑",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"luck": 16, "speed": 6},
        "unique_effect": "gold_find:0.40|item_find:0.25",
        "sell_price": 1100
    },
    "scholars_glasses": {
        "name": "학자의 안경",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"mp": 39, "spirit": 6, "luck": 8},
        "unique_effect": "exp_bonus:0.50",
        "sell_price": 900
    },
    "adventurers_compass": {
        "name": "모험가의 나침반",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"luck": 10},
        "unique_effect": "treasure_find:0.35",
        "sell_price": 400
    },
    "alchemists_stone": {
        "name": "연금술사의 돌",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"hp": 52, "mp": 52, "spirit": 8},
        "unique_effect": "potion_boost:0.30|hp_regen:0.02|mp_regen:3",
        "sell_price": 1450
    },
    "lucky_clover": {
        "name": "네잎 클로버",
        "description": "",
                "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"luck": 20, "critical": 5},
        "unique_effect": "critical_chance:0.10|rare_drop:0.15",
        "sell_price": 320
    },
    "void_crystal": {
        "name": "공허 수정",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"magic_attack": 21, "dark_power": 26, "mp": 58},
        "unique_effect": "dark_damage:0.45|mp_drain:0.10",
        "sell_price": 2950
    },
    "crystal_heart": {
        "name": "수정 심장",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"hp": 130, "spirit": 12},
        "unique_effect": "heal_boost:0.30|overheal_shield",
        "sell_price": 2450
    },
    "mana_crystal": {
        "name": "마나 수정",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"mp": 130, "magic_attack": 16, "spirit": 12},
        "unique_effect": "mp_regen:8|mp_percent:0.15",
        "sell_price": 2550
    },
    "bloodstone_amulet": {
        "name": "혈석 부적",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"hp": 72, "mp": 39},
        "unique_effect": "lifesteal:0.12|damage_to_mp:0.10",
        "sell_price": 1600
    },
    "shadow_cloak_pin": {
        "name": "그림자 망토핀",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"evasion": 13, "speed": 8, "critical": 6},
        "unique_effect": "stealth_bonus|dodge_counter",
        "sell_price": 1250
    },
    "flame_shield_emblem": {
        "name": "화염 방패 문장",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"hp": 84, "defense": 16, "fire_power": 23},
        "unique_effect": "fire_resist:1.0|fire_reflect:0.30",
        "sell_price": 2800
    },
    "storm_talisman": {
        "name": "폭풍의 부적",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"speed": 16, "lightning_power": 26, "evasion": 10},
        "unique_effect": "lightning_immunity|speed_boost:0.20",
        "sell_price": 2750
    },
    "necromancers_phylactery": {
        "name": "강령술사의 필락터리",
        "description": "",
                "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 11,
        "base_stats": {"hp": 117, "mp": 98, "dark_power": 32},
        "unique_effect": "undead_command|phylactery_rebirth:0.50",
        "sell_price": 10000
    },
    "orb_of_storms": {
        "name": "폭풍의 구슬",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"magic_attack": 18, "lightning_power": 20},
        "unique_effect": "lightning_explosion:0.15|chain_lightning:0.20",
        "sell_price": 1550
    },
    "sun_medallion": {
        "name": "태양의 메달",
        "description": "",
                "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"magic_attack": 18, "spirit": 14, "hp": 78},
        "unique_effect": "holy_damage:0.40|hp_regen:0.02|radiant_aura",
        "sell_price": 2650
    },
    "moon_charm": {
        "name": "달의 부적",
        "description": "",
                "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"magic_defense": 16, "evasion": 10, "spirit": 8},
        "unique_effect": "magic_evasion:0.20",
        "sell_price": 1350
    },

    # ============================================
    # === 오마주 악세서리 (다양한 시대/매체) ===
    # ============================================
    
    # === 판타지/RPG 고전작 오마주 ===
    "ribbon_protection": {
        "name": "리본",
        "description": "모든 상태이상을 막아주는 신비한 리본.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 20,
        "base_stats": {"hp": 100, "mp": 50, "spirit": 15},
        "unique_effect": "status_immunity:all|debuff_resist:1.0",
        "sell_price": 25000
    },
    "genji_glove": {
        "name": "겐지 장갑",
        "description": "두 개의 무기를 사용할 수 있게 해주는 장갑.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 22,
        "base_stats": {"physical_attack": 40, "strength": 18, "speed": 10},
        "unique_effect": "double_strike|critical_chance:0.20",
        "sell_price": 28000
    },
    "bracer_power": {
        "name": "파워 브레이서",
        "description": "착용자의 힘을 증폭시키는 팔찌.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 8,
        "base_stats": {"physical_attack": 15, "strength": 10},
        "unique_effect": "strength_boost:0.15",
        "sell_price": 2500
    },
    "sneak_ring_thief": {
        "name": "도적의 반지",
        "description": "적에게 들키지 않게 해주는 반지.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"evasion": 18, "speed": 10, "luck": 12},
        "unique_effect": "stealth_bonus|gold_find:0.30",
        "sell_price": 3500
    },
    "sheikah_slate": {
        "name": "시커 슬레이트",
        "description": "고대 기술의 정수가 담긴 석판.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 25,
        "base_stats": {"all_stats": 12, "accuracy": 25, "luck": 15},
        "unique_effect": "vision:2|detect_hidden|true_sight",
        "sell_price": 30000
    },
    "paraglider_freedom": {
        "name": "패러글라이더",
        "description": "자유롭게 활공할 수 있는 장비.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 14,
        "base_stats": {"evasion": 20, "speed": 15},
        "unique_effect": "dodge_chance:0.25|speed_boost:0.20",
        "sell_price": 7500
    },
    "ocarina_of_time": {
        "name": "시간의 오카리나",
        "description": "시간을 조종하는 힘이 담긴 악기.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 26,
        "base_stats": {"mp": 120, "spirit": 20, "all_stats": 10},
        "unique_effect": "cooldown_reduction:0.40|double_turn:0.15",
        "sell_price": 35000
    },
    "fierce_deity_mask": {
        "name": "귀신 가면",
        "description": "사신의 힘을 부여하는 가면.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 28,
        "base_stats": {"physical_attack": 60, "magic_attack": 60, "all_stats": 15},
        "unique_effect": "all_damage:0.50|critical_damage:0.80",
        "sell_price": 45000
    },
    
    # === 신화/전설 오마주 ===
    "ring_of_gyges": {
        "name": "기게스의 반지",
        "description": "투명해지는 힘을 가진 반지.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 22,
        "base_stats": {"evasion": 30, "speed": 15, "luck": 18},
        "unique_effect": "stealth_bonus|dodge_chance:0.40|critical_chance:0.25",
        "sell_price": 26000
    },
    "draupnir_ring": {
        "name": "드라우프니르",
        "description": "9일마다 자기 복제하는 황금 반지.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 23,
        "base_stats": {"luck": 25, "all_stats": 10},
        "unique_effect": "gold_find:2.00|item_rarity:0.50",
        "sell_price": 28000
    },
    "megingjord_belt": {
        "name": "메긴요르드",
        "description": "토르의 힘을 배가시키는 벨트.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"strength": 25, "hp": 120, "physical_attack": 25},
        "unique_effect": "strength_boost:0.30|stun_chance:0.20",
        "sell_price": 14000
    },
    "tarnhelm_disguise": {
        "name": "타른헬름",
        "description": "변신 능력이 담긴 투구.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 16,
        "base_stats": {"evasion": 22, "magic_defense": 35, "luck": 15},
        "unique_effect": "stealth_bonus|dodge_chance:0.30",
        "sell_price": 10000
    },
    "andvaranaut_cursed": {
        "name": "안드바라나우트",
        "description": "저주받은 황금 반지.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 24,
        "base_stats": {"luck": 30, "gold_bonus": 100, "hp": -50},
        "unique_effect": "gold_find:3.00|curse_self:hp_max_reduction:0.15",
        "sell_price": 30000
    },
    "jade_emperor_seal": {
        "name": "옥황상제의 인장",
        "description": "하늘의 최고 권위가 담긴 인장.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 27,
        "base_stats": {"all_stats": 18, "spirit": 25, "hp": 150},
        "unique_effect": "holy_damage:0.50|leadership:0.40",
        "sell_price": 40000
    },
    "sun_wukong_headband": {
        "name": "긴고아",
        "description": "제천대성을 제어하는 금고아.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 17,
        "base_stats": {"magic_defense": 50, "spirit": 18, "hp": 80},
        "unique_effect": "damage_reduction:0.25|cc_immunity:stun,sleep",
        "sell_price": 11000
    },
    "soma_divine": {
        "name": "소마",
        "description": "신들의 음료로 만든 부적.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 15,
        "base_stats": {"hp": 100, "mp": 70, "spirit": 15},
        "unique_effect": "hp_regen:0.04|mp_regen:8",
        "sell_price": 8500
    },
    
    # === 애니메이션/게임 오마주 ===
    "soul_gem_magical": {
        "name": "소울 젬",
        "description": "소녀의 영혼이 담긴 보석.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 13,
        "base_stats": {"magic_attack": 30, "mp": 80, "spirit": 15},
        "unique_effect": "spell_power:0.30|mp_cost_reduction:0.20",
        "sell_price": 6500
    },
    "death_note_book": {
        "name": "죽음의 노트",
        "description": "이름을 쓰면 죽는 노트.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 25,
        "base_stats": {"magic_attack": 50, "luck": 20, "dark_power": 40},
        "unique_effect": "execute:0.50|dark_damage:0.40",
        "sell_price": 32000
    },
    "dragon_ball_star": {
        "name": "드래곤볼",
        "description": "소원을 이루어주는 구슬.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 29,
        "base_stats": {"all_stats": 20, "luck": 30},
        "unique_effect": "phoenix_rebirth:full|all_damage:0.40",
        "sell_price": 50000
    },
    "millennium_puzzle": {
        "name": "천년 퍼즐",
        "description": "어둠의 힘이 담긴 고대 유물.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 24,
        "base_stats": {"magic_attack": 45, "spirit": 22, "luck": 25},
        "unique_effect": "spell_power:0.40|critical_chance:0.30",
        "sell_price": 28000
    },
    "joestar_birthmark": {
        "name": "죠스타의 반점",
        "description": "운명적인 혈통의 증거.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 14,
        "base_stats": {"strength": 15, "speed": 12, "luck": 15},
        "unique_effect": "critical_chance:0.20|low_hp_bonus:0.50",
        "sell_price": 7000
    },
    "stone_mask_vampire": {
        "name": "돌가면",
        "description": "흡혈귀의 힘을 부여하는 가면.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 12,
        "base_stats": {"physical_attack": 25, "speed": 18, "hp": -30},
        "unique_effect": "lifesteal:0.25|critical_damage:0.50",
        "sell_price": 5500
    },
    "red_stone_of_aja": {
        "name": "에이자의 적석",
        "description": "궁극 생명체를 만드는 보석.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 26,
        "base_stats": {"all_stats": 15, "hp": 150, "mp": 100},
        "unique_effect": "all_damage:0.40|hp_regen:0.05|lifesteal:0.20",
        "sell_price": 38000
    },
    "world_item_nazarick": {
        "name": "월드 아이템",
        "description": "세계 법칙을 초월하는 아이템.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 30,
        "base_stats": {"all_stats": 25, "hp": 200, "mp": 150},
        "unique_effect": "all_damage:0.60|status_immunity:all|ignore_armor:0.50",
        "sell_price": 80000
    },
    "keystone_mega": {
        "name": "키스톤",
        "description": "메가 진화를 가능하게 하는 돌.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 9,
        "base_stats": {"all_stats": 5, "luck": 10},
        "unique_effect": "all_stats_bonus:0.10",
        "sell_price": 3000
    },
    "z_ring_alola": {
        "name": "Z링",
        "description": "Z기술을 사용할 수 있게 해주는 팔찌.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 15,
        "base_stats": {"all_stats": 8, "spirit": 12},
        "unique_effect": "spell_power:0.25|all_damage:0.20",
        "sell_price": 8000
    },
    "mega_ring_kalos": {
        "name": "메가링",
        "description": "메가 진화를 일으키는 반지.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 17,
        "base_stats": {"all_stats": 10, "speed": 10},
        "unique_effect": "all_stats_bonus:0.15|speed_boost:0.15",
        "sell_price": 10000
    },
    
    # === 현대/SF 오마주 ===
    "pip_boy_wrist": {
        "name": "핍보이",
        "description": "개인 정보 장치.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 8,
        "base_stats": {"accuracy": 15, "luck": 12},
        "unique_effect": "vision:1|analyze_enemy",
        "sell_price": 2800
    },
    "omni_tool_alliance": {
        "name": "옴니툴",
        "description": "만능 도구.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 16,
        "base_stats": {"magic_attack": 25, "accuracy": 18, "speed": 8},
        "unique_effect": "spell_power:0.20|armor_penetration:0.25",
        "sell_price": 9500
    },
    "cortana_ai_chip": {
        "name": "코타나 칩",
        "description": "고급 인공지능 칩.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 11,
        "base_stats": {"accuracy": 22, "luck": 10, "speed": 8},
        "unique_effect": "critical_chance:0.15|vision:1",
        "sell_price": 4200
    },
    "glados_core": {
        "name": "글라도스 코어",
        "description": "인공지능 핵심부.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"magic_attack": 35, "mp": 80, "accuracy": 25},
        "unique_effect": "spell_power:0.30|status_poison:0.30",
        "sell_price": 12000
    },
    "companion_cube_item": {
        "name": "동반자 큐브",
        "description": "당신의 유일한 친구.",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 5,
        "base_stats": {"hp": 50, "spirit": 8},
        "unique_effect": "hp_regen:0.02",
        "sell_price": 800
    },
    "pokeball_basic": {
        "name": "포켓볼",
        "description": "몬스터를 잡는 공.",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 3,
        "base_stats": {"luck": 8},
        "unique_effect": "item_find:0.15",
        "sell_price": 200
    },
    "master_ball_ultimate": {
        "name": "마스터볼",
        "description": "무엇이든 잡을 수 있는 공.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 25,
        "base_stats": {"luck": 30, "all_stats": 8},
        "unique_effect": "item_find:0.60|item_rarity:0.50",
        "sell_price": 35000
    },
    "scouter_power": {
        "name": "스카우터",
        "description": "전투력을 측정하는 장치.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"accuracy": 18, "critical": 10},
        "unique_effect": "analyze_enemy|critical_chance:0.15",
        "sell_price": 3800
    },
    
    # === 추가 악세서리: 다양한 레벨 분포 ===
    # 레벨 1-5
    "wooden_charm": {
        "name": "나무 부적",
        "description": "행운을 주는 나무 조각.",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"luck": 5, "hp": 10},
        "sell_price": 30
    },
    "copper_ring": {
        "name": "구리 반지",
        "description": "싸구려 구리 반지.",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 3, "strength": 2},
        "sell_price": 50
    },
    "travelers_amulet": {
        "name": "여행자의 부적",
        "description": "길 찾기를 돕는 부적.",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 4,
        "base_stats": {"speed": 8, "luck": 8},
        "unique_effect": "speed_boost:0.10",
        "sell_price": 300
    },
    "apprentice_badge": {
        "name": "견습생 배지",
        "description": "마법 견습생의 증표.",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 5,
        "base_stats": {"magic_attack": 10, "mp": 25, "spirit": 5},
        "unique_effect": "exp_bonus:0.20",
        "sell_price": 400
    },
    
    # 레벨 6-10
    "warrior_medal": {
        "name": "전사의 메달",
        "description": "전투에서 용맹함을 보인 자의 훈장.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 15, "strength": 8, "hp": 40},
        "unique_effect": "strength_boost:0.10",
        "sell_price": 1600
    },
    "mage_emblem": {
        "name": "마법사 휘장",
        "description": "마법 길드의 휘장.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 8,
        "base_stats": {"magic_attack": 18, "mp": 50, "spirit": 8},
        "unique_effect": "spell_power:0.15",
        "sell_price": 2000
    },
    "scout_badge": {
        "name": "정찰병 배지",
        "description": "정찰대의 배지.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 9,
        "base_stats": {"evasion": 15, "speed": 12, "accuracy": 10},
        "unique_effect": "vision:1|speed_boost:0.10",
        "sell_price": 2400
    },
    "templar_cross": {
        "name": "성전 기사 십자가",
        "description": "성전 기사의 신앙 상징.",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"spirit": 12, "hp": 60, "magic_defense": 15},
        "unique_effect": "holy_damage:0.20",
        "sell_price": 3000
    },
    
    # 레벨 11-15
    "knight_crest": {
        "name": "기사 문장",
        "description": "명예로운 기사 가문의 문장.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 12,
        "base_stats": {"physical_attack": 20, "physical_defense": 15, "hp": 70},
        "unique_effect": "counter_attack:0.20|block_chance:0.15",
        "sell_price": 5000
    },
    "archmage_sigil": {
        "name": "대마법사 인장",
        "description": "대마법사의 권위를 나타내는 인장.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 14,
        "base_stats": {"magic_attack": 30, "mp": 75, "spirit": 15},
        "unique_effect": "spell_power:0.25|mp_cost_reduction:0.15",
        "sell_price": 6500
    },
    
    # 레벨 16-20
    "war_general_insignia": {
        "name": "전쟁 장군 휘장",
        "description": "전쟁을 이끄는 장군의 휘장.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 17,
        "base_stats": {"physical_attack": 35, "strength": 15, "hp": 100},
        "unique_effect": "strength_boost:0.25|leadership:0.20",
        "sell_price": 11000
    },
    "high_mage_orb": {
        "name": "고위 마법사 오브",
        "description": "마법의 정수가 담긴 오브.",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 19,
        "base_stats": {"magic_attack": 45, "mp": 100, "spirit": 20},
        "unique_effect": "spell_power:0.35|all_element_damage:0.25",
        "sell_price": 14000
    },
    
    # 레벨 21-25
    "dragon_heart_pendant": {
        "name": "용심 펜던트",
        "description": "용의 심장에서 추출한 보석.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 22,
        "base_stats": {"hp": 150, "physical_attack": 35, "fire_power": 30},
        "unique_effect": "fire_resist:0.60|fire_damage:0.35|hp_regen:0.03",
        "sell_price": 24000
    },
    "void_walker_amulet": {
        "name": "공허 보행자 목걸이",
        "description": "차원을 넘나드는 힘이 담긴 목걸이.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 23,
        "base_stats": {"magic_attack": 50, "mp": 120, "void_power": 35},
        "unique_effect": "spell_power:0.40|dodge_chance:0.25",
        "sell_price": 26000
    },
    
    # 레벨 26-30
    "celestial_crown": {
        "name": "천상의 왕관",
        "description": "하늘의 축복이 담긴 왕관.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 26,
        "base_stats": {"all_stats": 15, "hp": 140, "spirit": 22},
        "unique_effect": "holy_protection|all_resist:0.35",
        "sell_price": 34000
    },
    "abyssal_pendant": {
        "name": "심연의 펜던트",
        "description": "심연의 어둠이 담긴 펜던트.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 27,
        "base_stats": {"magic_attack": 55, "dark_power": 50, "mp": 130},
        "unique_effect": "dark_damage:0.50|lifesteal:0.25",
        "sell_price": 38000
    },
    "world_tree_leaf": {
        "name": "세계수의 잎",
        "description": "세계수에서 떨어진 신성한 잎.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 28,
        "base_stats": {"hp": 180, "mp": 140, "spirit": 25},
        "unique_effect": "hp_regen:0.06|mp_regen:15|phoenix_rebirth:half",
        "sell_price": 42000
    },
    "god_slayer_emblem": {
        "name": "신살 문장",
        "description": "신을 쓰러뜨린 영웅의 문장.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 29,
        "base_stats": {"all_stats": 20, "physical_attack": 50, "magic_attack": 50},
        "unique_effect": "all_damage:0.45|ignore_armor:0.40",
        "sell_price": 52000
    },
    "primordial_crystal": {
        "name": "태초의 수정",
        "description": "세계 창조 시 함께 태어난 수정.",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 30,
        "base_stats": {"all_stats": 25, "hp": 200, "mp": 180},
        "unique_effect": "all_damage:0.55|all_resist:0.45|hp_regen:0.05",
        "sell_price": 70000
    },
}


# 유니크 아이템
UNIQUE_ITEMS = {
    "excalibur": {
        "name": "엑스칼리버",
        "description": "",
                "rarity": ItemRarity.UNIQUE,
        "level_requirement": 13,
        "base_stats": {"physical_attack": 98, "magic_attack": 32, "hp": 65, "mp": 32},
        "unique_effect": "HP 50% 이상 시 모든 공격력 +30%",
        "sell_price": 99999
    },
    "mjolnir": {
        "name": "묠니르",
        "description": "",
                "rarity": ItemRarity.UNIQUE,
        "level_requirement": 9,
        "base_stats": {"physical_attack": 91, "strength": 13},
        "unique_effect": "공격 시 30% 확률로 번개 추가 데미지",
        "sell_price": 88888
    },
    "infinity_gauntlet": {
        "name": "무한의 건틀릿",
        "description": "",
                "rarity": ItemRarity.UNIQUE,
        "level_requirement": 15,
        "base_stats": {
            "physical_attack": 32, "magic_attack": 32,
            "physical_defense": 20, "magic_defense": 20,
            "hp": 130, "mp": 65
        },
        "unique_effect": "모든 스탯 +10%",
        "sell_price": 150000
    },
    "phoenix_feather": {
        "name": "불사조의 깃털",
        "description": "",
                "rarity": ItemRarity.UNIQUE,
        "level_requirement": 6,
        "base_stats": {"hp": 98, "magic_defense": 26},
        "unique_effect": "전투 중 1회 사망 시 HP 100%로 부활",
        "sell_price": 50000
    },
}

# 소비 아이템 (첫 번째 정의 제거됨 - 두 번째 정의 사용)

# 접사 풀 (랜덤 생성용)
AFFIX_POOL = {
    # 물리 공격 관련
    "of_power": ItemAffix("of_power", "힘의", "physical_attack", 0.15, True),
    "of_might": ItemAffix("of_might", "완력의", "strength", 5, False),
    "sharp": ItemAffix("sharp", "날카로운", "physical_attack", 10, False),

    # 마법 관련
    "of_magic": ItemAffix("of_magic", "마력의", "magic_attack", 0.15, True),
    "of_wisdom": ItemAffix("of_wisdom", "지혜의", "mp", 20, False),
    "arcane": ItemAffix("arcane", "비전의", "magic_attack", 8, False),

    # 방어 관련
    "of_protection": ItemAffix("of_protection", "보호의", "physical_defense", 0.12, True),
    "sturdy": ItemAffix("sturdy", "견고한", "physical_defense", 8, False),
    "of_resistance": ItemAffix("of_resistance", "저항의", "magic_defense", 0.12, True),

    # 생명력
    "of_vitality": ItemAffix("of_vitality", "생명의", "hp", 0.20, True),
    "healthy": ItemAffix("healthy", "건강한", "hp", 30, False),

    # 속도/회피
    "of_speed": ItemAffix("of_speed", "신속의", "speed", 5, False),
    "of_evasion": ItemAffix("of_evasion", "회피의", "evasion", 8, False),

    # 명중/크리
    "of_accuracy": ItemAffix("of_accuracy", "정확의", "accuracy", 10, False),
    "of_luck": ItemAffix("of_luck", "행운의", "luck", 5, False),

    # === 추가 옵션 확장 ===
    # 공격 관련
    "of_destruction": ItemAffix("of_destruction", "파괴의", "critical_damage", 0.30, True),
    # === 관통 옵션 (% 최대 25%, 고정수치는 고렌 전용) ===
    "physical_piercing": ItemAffix("physical_piercing", "물리 관통의", "physical_penetration", 0.15, True),  # 최대 25%
    "magic_piercing": ItemAffix("magic_piercing", "마법 관통의", "magic_penetration", 0.15, True),  # 최대 25%
    # 레거시 호환성 (기존 armor_penetration 옵션)
    "piercing": ItemAffix("piercing", "관통하는", "physical_penetration", 0.15, True),
    "vampiric": ItemAffix("vampiric", "흡혈의", "lifesteal", 0.05, True),
    "soul_stealing": ItemAffix("soul_stealing", "영혼 강탈의", "mana_steal", 0.05, True),
    "bloodthirsty": ItemAffix("bloodthirsty", "피에 굶주린", "heal_on_kill", 20, False),
    
    # 속성 공격
    "flaming": ItemAffix("flaming", "화염의", "fire_damage", 15, False),
    "freezing": ItemAffix("freezing", "빙결의", "ice_damage", 15, False),
    "shocking": ItemAffix("shocking", "전격의", "lightning_damage", 15, False),

    # 방어 관련
    "iron_wall": ItemAffix("iron_wall", "철벽의", "physical_damage_reduction", 0.10, True),
    "antimagic": ItemAffix("antimagic", "마법 차단의", "magic_damage_reduction", 0.10, True),
    "regenerating": ItemAffix("regenerating", "재생의", "hp_regen", 5, False),
    "meditating": ItemAffix("meditating", "명상의", "mp_regen", 3, False),
    "unyielding": ItemAffix("unyielding", "불굴의", "status_resistance", 0.20, True),

    # 유틸리티
    "enlightened": ItemAffix("enlightened", "깨달음의", "exp_bonus", 0.10, True),
    "wealthy": ItemAffix("wealthy", "부유한", "gold_bonus", 0.15, True),
    "farsight": ItemAffix("farsight", "천리안의", "vision_bonus", 1, False),
    "cautious": ItemAffix("cautious", "신중한", "trap_disarm", 0.20, True),

    # === 고정 관통 (고레벨 전용 - 레벨 5 이상에서만 출현) ===
    "physical_penetration_fixed": ItemAffix("physical_penetration_fixed", "물방 파쇄의", "physical_penetration_fixed", 15, False),
    "magic_penetration_fixed": ItemAffix("magic_penetration_fixed", "마방 파쇄의", "magic_penetration_fixed", 10, False),
}


class ItemGenerator:
    """아이템 생성기"""

    @staticmethod
    def generate_random_affixes(rarity: ItemRarity, level: int = 1) -> List[ItemAffix]:
        """
        등급과 레벨에 따라 랜덤 접사 생성
        
        Args:
            rarity: 아이템 등급
            level: 아이템 레벨 (수치 스케일링용)
        """
        # 등급별 접사 개수 (최소~최대)
        affix_counts = {
            ItemRarity.COMMON: (1, 1),      # 일반도 1개 부여
            ItemRarity.UNCOMMON: (1, 2),
            ItemRarity.RARE: (2, 3),
            ItemRarity.EPIC: (3, 4),
            ItemRarity.LEGENDARY: (4, 5),
            ItemRarity.UNIQUE: (0, 0)       # 유니크는 고정
        }

        min_cnt, max_cnt = affix_counts.get(rarity, (0, 0))
        if max_cnt == 0:
            return []
            
        count = random.randint(min_cnt, max_cnt)

        # 고정 관통은 고레벨에서만 (레벨 5 이상)
        HIGH_LEVEL_AFFIXES = {"physical_penetration_fixed", "magic_penetration_fixed"}
        
        # 랜덤 접사 선택 및 수치 조정
        available_affixes = []
        for affix in AFFIX_POOL.values():
            # 고정 관통은 레벨 5 미만에서는 제외
            if affix.stat in HIGH_LEVEL_AFFIXES and level < 5:
                continue
            available_affixes.append(affix)
        
        selected_base = random.sample(available_affixes, min(count, len(available_affixes)))
        
        final_affixes = []
        for base_affix in selected_base:
            # 레벨에 따른 수치 보정 (기본값 + 레벨 * 계수)
            # 등급에 따른 추가 보정 (등급이 높으면 더 높은 수치가 나올 확률 증가)
            
            # 변동폭: 0.8 ~ 1.5 (등급 보너스 추가)
            rarity_bonus = {
                ItemRarity.COMMON: 0.0,
                ItemRarity.UNCOMMON: 0.1,
                ItemRarity.RARE: 0.2,
                ItemRarity.EPIC: 0.3,
                ItemRarity.LEGENDARY: 0.5
            }.get(rarity, 0.0)
            
            variance = random.uniform(0.8, 1.2) + rarity_bonus
            
            # 레벨 스케일링 (레벨 10당 2배)
            level_multiplier = 1.0 + (level * 0.1)
            
            new_value = base_affix.value * variance * level_multiplier
            
            # 관통 옵션은 최대 25%로 제한 (다른 % 옵션은 50%)
            PENETRATION_STATS = {"physical_penetration", "magic_penetration", "armor_penetration"}
            if base_affix.is_percentage:
                if base_affix.stat in PENETRATION_STATS:
                    new_value = min(new_value, 0.25)  # 관통은 최대 25%
                else:
                    new_value = min(new_value, 0.50)  # 다른 옵션은 최대 50%
            
            new_affix = ItemAffix(
                id=base_affix.id,
                name=base_affix.name,
                stat=base_affix.stat,
                value=new_value,
                is_percentage=base_affix.is_percentage
            )
            final_affixes.append(new_affix)

        return final_affixes

    @staticmethod
    def reforge_item(item: Equipment, gold_cost: int = 0) -> Tuple[bool, str]:
        """
        아이템 재연마 (접사 재부여)
        
        Args:
            item: 대상 아이템
            gold_cost: 소모 골드 (외부에서 확인)
            
        Returns:
            (성공 여부, 메시지)
        """
        if item.rarity == ItemRarity.UNIQUE:
            return False, "유니크 아이템은 재연마할 수 없습니다."
            
        new_affixes = ItemGenerator.generate_random_affixes(item.rarity, item.level_requirement)
        item.affixes = new_affixes
        return True, "아이템의 옵션이 변경되었습니다."

    @staticmethod
    def create_weapon(template_id: str, add_random_affixes: bool = True) -> Equipment:
        """무기 생성"""
        template = WEAPON_TEMPLATES.get(template_id)
        if not template:
            raise ValueError(f"Unknown weapon template: {template_id}")

        affixes = []
        if add_random_affixes:
            affixes = ItemGenerator.generate_random_affixes(template["rarity"], template["level_requirement"])

        # 무게 계산: 등급에 따라 3~15kg
        rarity_weight = {
            ItemRarity.COMMON: 3.0,
            ItemRarity.UNCOMMON: 5.0,
            ItemRarity.RARE: 8.0,
            ItemRarity.EPIC: 12.0,
            ItemRarity.LEGENDARY: 15.0,
            ItemRarity.UNIQUE: 10.0
        }
        weight = rarity_weight.get(template["rarity"], 5.0)

        return Equipment(
            item_id=template_id,
            name=template["name"],
            description=template["description"],
            item_type=ItemType.WEAPON,
            rarity=template["rarity"],
            level_requirement=template["level_requirement"],
            base_stats=template["base_stats"].copy(),
            affixes=affixes,
            equip_slot=EquipSlot.WEAPON,
            sell_price=template["sell_price"],
            weight=weight
        )

    @staticmethod
    def create_armor(template_id: str, add_random_affixes: bool = True) -> Equipment:
        """방어구 생성"""
        template = ARMOR_TEMPLATES.get(template_id)
        if not template:
            raise ValueError(f"Unknown armor template: {template_id}")

        affixes = []
        if add_random_affixes:
            affixes = ItemGenerator.generate_random_affixes(template["rarity"], template["level_requirement"])

        # 무게 계산: 등급에 따라 5~25kg (방어구는 무거움)
        rarity_weight = {
            ItemRarity.COMMON: 5.0,
            ItemRarity.UNCOMMON: 8.0,
            ItemRarity.RARE: 12.0,
            ItemRarity.EPIC: 18.0,
            ItemRarity.LEGENDARY: 25.0,
            ItemRarity.UNIQUE: 15.0
        }
        weight = rarity_weight.get(template["rarity"], 8.0)

        return Equipment(
            item_id=template_id,
            name=template["name"],
            description=template["description"],
            item_type=ItemType.ARMOR,
            rarity=template["rarity"],
            level_requirement=template["level_requirement"],
            base_stats=template["base_stats"].copy(),
            affixes=affixes,
            equip_slot=EquipSlot.ARMOR,
            sell_price=template["sell_price"],
            weight=weight
        )

    @staticmethod
    def create_accessory(template_id: str, add_random_affixes: bool = True) -> Equipment:
        """악세서리 생성"""
        template = ACCESSORY_TEMPLATES.get(template_id)
        if not template:
            raise ValueError(f"Unknown accessory template: {template_id}")

        affixes = []
        if add_random_affixes:
            affixes = ItemGenerator.generate_random_affixes(template["rarity"], template["level_requirement"])

        # 무게 계산: 0.1~0.5kg (가벼움)
        rarity_weight = {
            ItemRarity.COMMON: 0.1,
            ItemRarity.UNCOMMON: 0.2,
            ItemRarity.RARE: 0.3,
            ItemRarity.EPIC: 0.4,
            ItemRarity.LEGENDARY: 0.5,
            ItemRarity.UNIQUE: 0.3
        }
        weight = rarity_weight.get(template["rarity"], 0.2)

        return Equipment(
            item_id=template_id,
            name=template["name"],
            description=template["description"],
            item_type=ItemType.ACCESSORY,
            rarity=template["rarity"],
            level_requirement=template["level_requirement"],
            base_stats=template["base_stats"].copy(),
            affixes=affixes,
            equip_slot=EquipSlot.ACCESSORY,
            unique_effect=template.get("unique_effect"),  # unique_effect 추가
            sell_price=template["sell_price"],
            weight=weight
        )

    @staticmethod
    def create_unique(template_id: str) -> Equipment:
        """유니크 아이템 생성 (고정 능력)"""
        template = UNIQUE_ITEMS.get(template_id)
        if not template:
            raise ValueError(f"Unknown unique template: {template_id}")

        return Equipment(
            item_id=template_id,
            name=template["name"],
            description=template["description"],
            item_type=ItemType.WEAPON,
            rarity=template["rarity"],
            level_requirement=template["level_requirement"],
            base_stats=template["base_stats"].copy(),
            affixes=[],
            unique_effect=template["unique_effect"],
            equip_slot=EquipSlot.WEAPON,
            sell_price=template["sell_price"],
            weight=10.0  # 유니크 아이템: 고정 10kg
        )

    @staticmethod
    def create_consumable(template_id: str) -> Consumable:
        """소비 아이템 생성"""
        template = CONSUMABLE_TEMPLATES.get(template_id)
        if not template:
            raise ValueError(f"Unknown consumable template: {template_id}")

        # 소비품 무게: 0.1~0.3kg (가벼움)
        consumable_weights = {
            "health_potion": 0.2,
            "mega_health_potion": 0.3,
            "mana_potion": 0.2,
            "elixir": 0.3
        }
        weight = consumable_weights.get(template_id, 0.2)

        return Consumable(
            item_id=template_id,
            name=template["name"],
            description=template["description"],
            item_type=ItemType.CONSUMABLE,
            rarity=template["rarity"],
            effect_type=template["effect_type"],
            effect_value=template["effect_value"],
            sell_price=template["sell_price"],
            weight=weight
        )

    @staticmethod
    def create_random_drop(level: int, boss_drop: bool = False, floor_number: int = 1) -> Item:
        """레벨에 맞는 랜덤 드롭 생성"""
        # 초반(3층까지) 등급 제한: 언커먼까지만 나옴
        early_floor_limit = floor_number <= 3
        
        # 등급 확률
        if boss_drop:
            # 보스 드롭: 높은 등급 확률 증가
            if early_floor_limit:
                # 초반 보스: 언커먼까지만
                rarity_chances = {
                    ItemRarity.COMMON: 0.30,
                    ItemRarity.UNCOMMON: 0.70,
                    ItemRarity.RARE: 0.0,
                    ItemRarity.EPIC: 0.0,
                    ItemRarity.LEGENDARY: 0.0
                }
            else:
                rarity_chances = {
                    ItemRarity.COMMON: 0.10,
                    ItemRarity.UNCOMMON: 0.25,
                    ItemRarity.RARE: 0.35,
                    ItemRarity.EPIC: 0.20,
                    ItemRarity.LEGENDARY: 0.10
                }
        else:
            # 일반 드롭
            if early_floor_limit:
                # 초반 일반: 언커먼까지만
                rarity_chances = {
                    ItemRarity.COMMON: 0.70,
                    ItemRarity.UNCOMMON: 0.30,
                    ItemRarity.RARE: 0.0,
                    ItemRarity.EPIC: 0.0,
                    ItemRarity.LEGENDARY: 0.0
                }
            else:
                rarity_chances = {
                    ItemRarity.COMMON: 0.50,
                    ItemRarity.UNCOMMON: 0.30,
                    ItemRarity.RARE: 0.15,
                    ItemRarity.EPIC: 0.04,
                    ItemRarity.LEGENDARY: 0.01
                }

        # 등급 결정
        roll = random.random()
        cumulative = 0.0
        chosen_rarity = ItemRarity.COMMON

        for rarity, chance in rarity_chances.items():
            cumulative += chance
            if roll <= cumulative:
                chosen_rarity = rarity
                break

        # 레벨에 맞는 템플릿 선택
        all_templates = {**WEAPON_TEMPLATES, **ARMOR_TEMPLATES, **ACCESSORY_TEMPLATES}
        
        # 레벨과 등급에 맞는 템플릿 필터링
        filtered_templates = []
        for template_id, template in all_templates.items():
            template_rarity = template.get("rarity", ItemRarity.COMMON)
            template_level = template.get("level_requirement", 1)
            
            # 등급이 일치하고 레벨 요구사항이 충족되는 템플릿만 선택
            if template_rarity == chosen_rarity and template_level <= level:
                filtered_templates.append((template_id, template))
        
        # 필터링된 템플릿이 없으면 등급만 맞는 템플릿 선택
        if not filtered_templates:
            for template_id, template in all_templates.items():
                template_rarity = template.get("rarity", ItemRarity.COMMON)
                if template_rarity == chosen_rarity:
                    filtered_templates.append((template_id, template))
        
        # 여전히 없으면 COMMON 등급 템플릿 선택
        if not filtered_templates:
            for template_id, template in all_templates.items():
                template_level = template.get("level_requirement", 1)
                if template_level <= level:
                    filtered_templates.append((template_id, template))
        
        # 최종적으로 없으면 첫 번째 템플릿 사용
        if not filtered_templates:
            return None
        
        # 랜덤 템플릿 선택
        template_id, template = random.choice(filtered_templates)
        
        # 아이템 타입 확인 및 생성
        if template_id in WEAPON_TEMPLATES:
            return ItemGenerator.create_weapon(template_id, add_random_affixes=True)
        elif template_id in ARMOR_TEMPLATES:
            return ItemGenerator.create_armor(template_id, add_random_affixes=True)
        elif template_id in ACCESSORY_TEMPLATES:
            return ItemGenerator.create_accessory(template_id, add_random_affixes=True)
        else:
            return None

# ============= 소모품 템플릿 =============

CONSUMABLE_TEMPLATES = {
    # === HP 포션 ===
    "minor_hp_potion": {"name": "소형 HP 물약", "description": "HP를 50 회복합니다.", "effect_type": "heal_hp", "effect_value": 50, "rarity": ItemRarity.COMMON, "stack_size": 99, "sell_price": 40},
    "hp_potion": {"name": "HP 물약", "description": "HP를 150 회복합니다.", "effect_type": "heal_hp", "effect_value": 150, "rarity": ItemRarity.COMMON, "stack_size": 99, "sell_price": 80},
    "greater_hp_potion": {"name": "상급 HP 물약", "description": "HP를 300 회복합니다.", "effect_type": "heal_hp", "effect_value": 300, "rarity": ItemRarity.UNCOMMON, "stack_size": 99, "sell_price": 150},
    "superior_hp_potion": {"name": "최상급 HP 물약", "description": "HP를 600 회복합니다.", "effect_type": "heal_hp", "effect_value": 600, "rarity": ItemRarity.RARE, "stack_size": 99, "sell_price": 280},
    "max_hp_potion": {"name": "엘리트 HP 물약", "description": "HP를 완전히 회복합니다.", "effect_type": "heal_hp_full", "effect_value": 0, "rarity": ItemRarity.EPIC, "stack_size": 20, "sell_price": 600},
    
    # === MP 포션 (HP 포션보다 비싸게 설정) ===
    "minor_mp_potion": {"name": "소형 MP 물약", "description": "MP를 30 회복합니다.", "effect_type": "heal_mp", "effect_value": 30, "rarity": ItemRarity.COMMON, "stack_size": 99, "sell_price": 60},
    "mp_potion": {"name": "MP 물약", "description": "MP를 80 회복합니다.", "effect_type": "heal_mp", "effect_value": 80, "rarity": ItemRarity.COMMON, "stack_size": 99, "sell_price": 120},
    "greater_mp_potion": {"name": "상급 MP 물약", "description": "MP를 180 회복합니다.", "effect_type": "heal_mp", "effect_value": 180, "rarity": ItemRarity.UNCOMMON, "stack_size": 99, "sell_price": 220},
    "superior_mp_potion": {"name": "최상급 MP 물약", "description": "MP를 350 회복합니다.", "effect_type": "heal_mp", "effect_value": 350, "rarity": ItemRarity.RARE, "stack_size": 99, "sell_price": 420},
    "max_mp_potion": {"name": "엘리트 MP 물약", "description": "MP를 완전히 회복합니다.", "effect_type": "heal_mp_full", "effect_value": 0, "rarity": ItemRarity.EPIC, "stack_size": 20, "sell_price": 800},
    
    # === 만능 물약 ===
    "elixir": {"name": "엘릭서", "description": "HP와 MP를 각각 200씩 회복합니다.", "effect_type": "heal_both", "effect_value": 200, "rarity": ItemRarity.RARE, "stack_size": 50, "sell_price": 300},
    "mega_elixir": {"name": "메가 엘릭서", "description": "HP와 MP를 완전히 회복합니다.", "effect_type": "heal_both_full", "effect_value": 0, "rarity": ItemRarity.EPIC, "stack_size": 10, "sell_price": 1000},
    
    # === 상처 치료 ===
    "bandage": {"name": "붕대", "description": "상처를 10 치료합니다.", "effect_type": "heal_wound", "effect_value": 10, "rarity": ItemRarity.COMMON, "stack_size": 99, "sell_price": 20},
    "ointment": {"name": "연고", "description": "상처를 30 치료합니다.", "effect_type": "heal_wound", "effect_value": 30, "rarity": ItemRarity.UNCOMMON, "stack_size": 99, "sell_price": 60},
    "healing_salve": {"name": "치유 연고", "description": "상처를 60 치료합니다.", "effect_type": "heal_wound", "effect_value": 60, "rarity": ItemRarity.RARE, "stack_size": 50, "sell_price": 150},
    
    # === 상태 이상 치료 ===
    "antidote": {"name": "해독제", "description": "독 상태를 치료합니다.", "effect_type": "cure_poison", "effect_value": 0, "rarity": ItemRarity.COMMON, "stack_size": 99, "sell_price": 25},
    "panacea": {"name": "만병통치약", "description": "모든 상태 이상을 치료합니다.", "effect_type": "cure_all_status", "effect_value": 0, "rarity": ItemRarity.RARE, "stack_size": 50, "sell_price": 200},
    "remedy": {"name": "치료제", "description": "디버프 상태를 치료합니다.", "effect_type": "cure_debuff", "effect_value": 0, "rarity": ItemRarity.UNCOMMON, "stack_size": 99, "sell_price": 80},
    
    # === 강화 물약 ===
    "strength_tonic": {"name": "힘의 강장제", "description": "공격력 +10 버프 (5턴 지속).", "effect_type": "buff_strength", "effect_value": 10, "rarity": ItemRarity.UNCOMMON, "stack_size": 50, "sell_price": 100},
    "magic_tonic": {"name": "마법의 강장제", "description": "마법력 +10 버프 (5턴 지속).", "effect_type": "buff_magic", "effect_value": 10, "rarity": ItemRarity.UNCOMMON, "stack_size": 50, "sell_price": 100},
    "speed_tonic": {"name": "속도의 강장제", "description": "속도 +10 버프 (5턴 지속).", "effect_type": "buff_speed", "effect_value": 10, "rarity": ItemRarity.UNCOMMON, "stack_size": 50, "sell_price": 100},
    "defense_tonic": {"name": "방어의 강장제", "description": "방어력 +10 버프 (5턴 지속).", "effect_type": "buff_defense", "effect_value": 10, "rarity": ItemRarity.UNCOMMON, "stack_size": 50, "sell_price": 100},
    
    # === 폭탄류 (공격 아이템) ===
    "fire_bomb": {"name": "화염 폭탄", "description": "적 전체에게 (50 + 층수 × 15) 화염 피해.", "effect_type": "attack_fire", "effect_value": 100, "rarity": ItemRarity.UNCOMMON, "stack_size": 99, "sell_price": 50},
    "ice_bomb": {"name": "냉기 폭탄", "description": "적 전체에게 (50 + 층수 × 15) 냉기 피해.", "effect_type": "attack_ice", "effect_value": 100, "rarity": ItemRarity.UNCOMMON, "stack_size": 99, "sell_price": 50},
    "thunder_bomb": {"name": "번개 폭탄", "description": "적 전체에게 (60 + 층수 × 18) 번개 피해.", "effect_type": "attack_lightning", "effect_value": 120, "rarity": ItemRarity.UNCOMMON, "stack_size": 99, "sell_price": 60},
    "poison_bomb": {"name": "독 폭탄", "description": "적 전체에게 (40 + 층수 × 12) 피해 + 독 상태 부여.", "effect_type": "attack_poison", "effect_value": 80, "rarity": ItemRarity.UNCOMMON, "stack_size": 99, "sell_price": 45},
    "explosive_bomb": {"name": "폭발 폭탄", "description": "적 전체에게 (80 + 층수 × 25) 물리 피해.", "effect_type": "attack_explosive", "effect_value": 200, "rarity": ItemRarity.RARE, "stack_size": 50, "sell_price": 150},
    
    # === 수류탄 ===
    "frag_grenade": {"name": "파편 수류탄", "description": "적 전체에게 (70 + 층수 × 20) 관통 피해.", "effect_type": "attack_aoe", "effect_value": 150, "rarity": ItemRarity.RARE, "stack_size": 50, "sell_price": 120},
    "flash_grenade": {"name": "섬광탄", "description": "적 전체에게 실명 상태 부여 (3턴).", "effect_type": "debuff_blind", "effect_value": 0, "rarity": ItemRarity.UNCOMMON, "stack_size": 99, "sell_price": 70},
    "smoke_grenade": {"name": "연막탄", "description": "아군 전체 회피율 +30% (3턴).", "effect_type": "buff_evasion", "effect_value": 30, "rarity": ItemRarity.UNCOMMON, "stack_size": 99, "sell_price": 60},
    
    # === 특수 아이템 ===
    "phoenix_down": {"name": "불사조의 깃털", "description": "쓰러진 아군을 HP 50%로 부활.", "effect_type": "revive", "effect_value": 0.5, "rarity": ItemRarity.EPIC, "stack_size": 10, "sell_price": 1000},
    "mega_phoenix": {"name": "메가 불사조의 깃털", "description": "쓰러진 아군을 HP 100%로 부활.", "effect_type": "revive_full", "effect_value": 1.0, "rarity": ItemRarity.LEGENDARY, "stack_size": 5, "sell_price": 5000},
    "warp_stone": {"name": "귀환석", "description": "마을로 즉시 귀환합니다.", "effect_type": "warp_town", "effect_value": 0, "rarity": ItemRarity.COMMON, "stack_size": 99, "sell_price": 50},
    "tent": {"name": "텐트", "description": "야영 후 전체 HP/MP 50% 회복.", "effect_type": "camp_rest", "effect_value": 0, "rarity": ItemRarity.UNCOMMON, "stack_size": 20, "sell_price": 200},
    
    # === BRV 아이템 ===
    "brv_crystal": {"name": "BRV 크리스탈", "description": "BRV를 500 회복합니다.", "effect_type": "restore_brv", "effect_value": 500, "rarity": ItemRarity.RARE, "stack_size": 50, "sell_price": 150},
    "break_guard": {"name": "브레이크 가드", "description": "다음 1회 브레이크를 방지합니다.", "effect_type": "prevent_break", "effect_value": 1, "rarity": ItemRarity.EPIC, "stack_size": 20, "sell_price": 800},
    
    # === 경험치/골드 아이템 ===
    "exp_crystal": {"name": "경험치 크리스탈", "description": "경험치 100을 즉시 획득합니다.", "effect_type": "bonus_exp", "effect_value": 100, "rarity": ItemRarity.RARE, "stack_size": 50, "sell_price": 300},
    "gold_nugget": {"name": "금 덩어리", "description": "골드 1000을 즉시 획득합니다. (판매 불가)", "effect_type": "bonus_gold", "effect_value": 1000, "rarity": ItemRarity.UNCOMMON, "stack_size": 99, "sell_price": 0},  # 판매 불가
    
    # === 전투용 공격 아이템 ===
    "thunder_grenade": {"name": "천둥 수류탄", "description": "적 전체에게 (75 + 층수 × 25) 번개 피해 + 기절 확률.", "effect_type": "thunder_grenade", "effect_value": 200, "rarity": ItemRarity.RARE, "stack_size": 50, "sell_price": 250},
    "acid_flask": {"name": "산성 플라스크", "description": "단일 적에게 (65 + 층수 × 22) 피해 + 방어력 감소.", "effect_type": "acid_flask", "effect_value": 180, "rarity": ItemRarity.UNCOMMON, "stack_size": 99, "sell_price": 160},
    "debuff_attack": {"name": "공격 약화 폭탄", "description": "적 전체 공격력 -30% (5턴).", "effect_type": "debuff_attack", "effect_value": 0.3, "rarity": ItemRarity.RARE, "stack_size": 50, "sell_price": 200},
    "debuff_defense": {"name": "방어 약화 폭탄", "description": "적 전체 방어력 -40% (5턴).", "effect_type": "debuff_defense", "effect_value": 0.4, "rarity": ItemRarity.RARE, "stack_size": 50, "sell_price": 220},
    "debuff_speed": {"name": "속도 약화 폭탄", "description": "적 전체 속도 -35% (5턴).", "effect_type": "debuff_speed", "effect_value": 0.35, "rarity": ItemRarity.RARE, "stack_size": 50, "sell_price": 210},
    "break_brv": {"name": "BRV 파괴 폭탄", "description": "적 전체 BRV 200 감소.", "effect_type": "break_brv", "effect_value": 200, "rarity": ItemRarity.EPIC, "stack_size": 20, "sell_price": 350},
    "smoke_bomb": {"name": "연막탄", "description": "적 전체 명중률 -50% (3턴).", "effect_type": "smoke_bomb", "effect_value": 0.5, "rarity": ItemRarity.UNCOMMON, "stack_size": 99, "sell_price": 120},
    
    # === 전투용 수비 아이템 ===
    "barrier_crystal": {"name": "방어 크리스탈", "description": "아군 전체 받는 피해 -30% (3턴).", "effect_type": "barrier_crystal", "effect_value": 0.3, "rarity": ItemRarity.RARE, "stack_size": 50, "sell_price": 280},
    "haste_crystal": {"name": "가속 크리스탈", "description": "아군 전체 속도 +40% (3턴).", "effect_type": "haste_crystal", "effect_value": 0.4, "rarity": ItemRarity.RARE, "stack_size": 50, "sell_price": 300},
    "power_tonic": {"name": "힘의 비약", "description": "아군 전체 공격력 +35% (5턴).", "effect_type": "power_tonic", "effect_value": 0.35, "rarity": ItemRarity.EPIC, "stack_size": 20, "sell_price": 400},
    "defense_elixir": {"name": "방어 엘릭서", "description": "아군 전체 방어력 +40% (5턴).", "effect_type": "defense_elixir", "effect_value": 0.4, "rarity": ItemRarity.EPIC, "stack_size": 20, "sell_price": 380},
    "regen_crystal": {"name": "재생 크리스탈", "description": "아군 전체 매턴 HP 50 회복 (5턴).", "effect_type": "regen_crystal", "effect_value": 50, "rarity": ItemRarity.RARE, "stack_size": 50, "sell_price": 320},
    "mp_regen_crystal": {"name": "MP 재생 크리스탈", "description": "아군 전체 매턴 MP 20 회복 (5턴).", "effect_type": "mp_regen_crystal", "effect_value": 20, "rarity": ItemRarity.RARE, "stack_size": 50, "sell_price": 300},
    "status_cleanse": {"name": "정화 물약", "description": "모든 디버프 상태를 해제합니다.", "effect_type": "status_cleanse", "effect_value": 0, "rarity": ItemRarity.UNCOMMON, "stack_size": 99, "sell_price": 180},
    "revive_crystal": {"name": "부활 크리스탈", "description": "쓰러진 아군을 HP 30%로 부활.", "effect_type": "revive_crystal", "effect_value": 0.3, "rarity": ItemRarity.EPIC, "stack_size": 10, "sell_price": 500},
}
