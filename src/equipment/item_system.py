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
            ItemRarity.COMMON: 50,
            ItemRarity.UNCOMMON: 80,
            ItemRarity.RARE: 120,
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
        "description": "기본적인 철제 검",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_attack": 15, "accuracy": 5},
        "sell_price": 50
    },
    "steel_sword": {
        "name": "강철검",
        "description": "단단한 강철로 만든 검",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 30, "accuracy": 8},
        "sell_price": 150
    },
    "mithril_sword": {
        "name": "미스릴 검",
        "description": "가볍고 날카로운 미스릴 검",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 50, "accuracy": 12, "speed": 3},
        "sell_price": 500
    },
    "dragon_slayer": {
        "name": "드래곤 슬레이어",
        "description": "용을 베기 위해 만들어진 거대한 검",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_attack": 85, "strength": 10},
        "sell_price": 2000
    },

    # 지팡이
    "wooden_staff": {
        "name": "나무 지팡이",
        "description": "초보 마법사용 지팡이",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"magic_attack": 18, "mp": 10},
        "sell_price": 60
    },
    "crystal_staff": {
        "name": "수정 지팡이",
        "description": "마력이 깃든 수정 지팡이",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"magic_attack": 60, "mp": 30, "spirit": 5},
        "sell_price": 600
    },
    "archmagus_staff": {
        "name": "대마법사의 지팡이",
        "description": "전설적인 대마법사가 사용했던 지팡이",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 7,
        "base_stats": {"magic_attack": 120, "mp": 60, "spirit": 15},
        "sell_price": 5000
    },

    # 활
    "hunting_bow": {
        "name": "사냥용 활",
        "description": "기본적인 사냥용 활",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_attack": 12, "accuracy": 10},
        "sell_price": 45
    },
    "longbow": {
        "name": "장궁",
        "description": "사거리가 긴 장궁",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 35, "accuracy": 15, "evasion": 3},
        "sell_price": 200
    },
    "composite_bow": {
        "name": "복합궁",
        "description": "강력한 복합 소재 활",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 55, "accuracy": 20, "critical_rate": 10},
        "sell_price": 550
    },

    # 단검
    "bronze_dagger": {
        "name": "청동 단검",
        "description": "기본적인 단검",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_attack": 10, "speed": 5, "evasion": 5},
        "sell_price": 35
    },
    "assassin_dagger": {
        "name": "암살자의 단검",
        "description": "치명타에 특화된 단검",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 40, "speed": 10, "critical_rate": 20},
        "sell_price": 450
    },
    "venom_fang": {
        "name": "독니",
        "description": "독을 품은 단검",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 65, "speed": 15, "critical_rate": 25},
        "sell_price": 1800
    },

    # 둔기
    "iron_mace": {
        "name": "철 메이스",
        "description": "무거운 둔기",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_attack": 18, "strength": 3},
        "sell_price": 55
    },
    "war_hammer": {
        "name": "전쟁 망치",
        "description": "강력한 전쟁용 망치",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 45, "strength": 8, "physical_defense": 5},
        "sell_price": 280
    },
    "titan_hammer": {
        "name": "티탄의 망치",
        "description": "거인의 힘이 깃든 망치",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_attack": 95, "strength": 15, "hp": 50},
        "sell_price": 2200
    },

    # 창
    "short_spear": {
        "name": "짧은 창",
        "description": "기본적인 창",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_attack": 14, "accuracy": 8},
        "sell_price": 48
    },
    "halberd": {
        "name": "할버드",
        "description": "긴 리치를 가진 창",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 48, "accuracy": 12, "physical_defense": 8},
        "sell_price": 320
    },
    "dragon_lance": {
        "name": "용의 창",
        "description": "용을 베는 전설의 창",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 110, "accuracy": 20, "critical_rate": 15},
        "sell_price": 6000
    },

    # 마법 지팡이 추가
    "fire_staff": {
        "name": "화염의 지팡이",
        "description": "화염 마법 강화",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"magic_attack": 40, "mp": 20},
        "sell_price": 250
    },
    "ice_staff": {
        "name": "빙결의 지팡이",
        "description": "냉기 마법 강화",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"magic_attack": 40, "mp": 20},
        "sell_price": 250
    },
    "staff_of_cosmos": {
        "name": "우주의 지팡이",
        "description": "모든 원소를 다루는 지팡이",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 9,
        "base_stats": {"magic_attack": 130, "mp": 80, "spirit": 20},
        "sell_price": 7500
    },

    # === 생명력 흡수 무기 ===
    "vampiric_blade": {
        "name": "흡혈검",
        "description": "적의 생명력을 흡수하는 검",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 55, "speed": -2},
        "unique_effect": "lifesteal:0.15",  # 15% 생명력 흡수
        "sell_price": 800
    },
    "soul_drinker": {
        "name": "영혼 포식자",
        "description": "영혼까지 삼키는 마검",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_attack": 95, "magic_attack": 30, "hp": -50},
        "unique_effect": "lifesteal:0.25",  # 25% 생명력 흡수
        "sell_price": 2500
    },
    "crimson_reaver": {
        "name": "진홍의 수확자",
        "description": "피를 갈구하는 낫. 처치 시 HP 회복",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 80, "critical": 15},
        "unique_effect": "lifesteal:0.12|on_kill_heal:50",
        "sell_price": 1800
    },

    # === BRV 특화 무기 ===
    "brave_enhancer": {
        "name": "브레이브 인챈서",
        "description": "BRV 공격력을 크게 증폭시키는 검",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 45, "speed": 3},
        "unique_effect": "brv_bonus:0.30",  # BRV +30%
        "sell_price": 600
    },
    "breaker": {
        "name": "브레이커",
        "description": "BREAK 특화 무기. BREAK 데미지 증가",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 70, "luck": 10},
        "unique_effect": "brv_break_bonus:0.50",  # BREAK 데미지 +50%
        "sell_price": 1500
    },
    "soul_stealer": {
        "name": "영혼 강탈자",
        "description": "적의 BRV를 훔쳐온다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 60, "accuracy": 10},
        "unique_effect": "brv_steal:0.20",  # BRV 흡수 +20%
        "sell_price": 1000
    },

    # === 크리티컬 특화 ===
    "assassins_edge": {
        "name": "암살자의 칼날",
        "description": "치명타 확률과 데미지 증가",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 50, "critical": 20, "speed": 5},
        "unique_effect": "critical_damage:0.50",  # 크리티컬 데미지 +50%
        "sell_price": 700
    },
    "fatal_strike": {
        "name": "필살검",
        "description": "극한의 치명타 특화 무기",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 10,
        "base_stats": {"physical_attack": 85, "critical": 35, "luck": 15},
        "unique_effect": "critical_damage:0.75|critical_chance:0.15",
        "sell_price": 3000
    },
    "backstabber": {
        "name": "배신자의 단검",
        "description": "적 HP 30% 이하 시 추가 데미지",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 55, "critical": 15, "speed": 8},
        "unique_effect": "execute:0.30",  # 적 HP 30% 이하 시 +30% 데미지
        "sell_price": 900
    },

    # === 속성 무기 ===
    "flametongue": {
        "name": "화염검",
        "description": "불꽃을 두르는 검. 화상 부여",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 40, "magic_attack": 15},
        "unique_effect": "element:fire|status_burn:0.25",  # 25% 화상
        "sell_price": 350
    },
    "frostbite": {
        "name": "동상의 검",
        "description": "얼음 속성. 적 속도 감소",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 38, "magic_attack": 18},
        "unique_effect": "element:ice|debuff_slow:0.30",
        "sell_price": 350
    },
    "thunderstrike": {
        "name": "뇌전검",
        "description": "번개 속성. 감전 부여",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 52, "magic_attack": 25, "speed": 4},
        "unique_effect": "element:lightning|status_shock:0.30|chain_lightning:0.20",
        "sell_price": 750
    },
    "earthshaker": {
        "name": "대지 파괴자",
        "description": "대지 속성. 방어력 무시 20%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 75, "strength": 12},
        "unique_effect": "element:earth|armor_penetration:0.20",
        "sell_price": 1200
    },
    "windcutter": {
        "name": "바람 절단자",
        "description": "바람 속성. 행동 속도 증가",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 42, "speed": 8, "accuracy": 10},
        "unique_effect": "element:wind|multi_strike:0.15",  # 15% 2회 공격
        "sell_price": 400
    },
    "voidreaver": {
        "name": "공허의 수확자",
        "description": "어둠 속성. MP 흡수",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_attack": 88, "magic_attack": 40, "mp": 50},
        "unique_effect": "element:void|mp_steal:0.30|debuff_silence:0.20",
        "sell_price": 2200
    },
    "holy_avenger": {
        "name": "성스러운 복수자",
        "description": "신성 속성. 언데드에게 추가 데미지",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_attack": 90, "magic_attack": 35, "spirit": 15},
        "unique_effect": "element:holy|bonus_vs_undead:0.50|heal_on_hit:5",
        "sell_price": 2500
    },

    # === 방어 관통 무기 ===
    "armor_piercer": {
        "name": "갑옷 관통자",
        "description": "방어력을 무시하는 창",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 58, "accuracy": 15},
        "unique_effect": "armor_penetration:0.25",
        "sell_price": 800
    },
    "true_strike_spear": {
        "name": "필중의 창",
        "description": "절대 빗나가지 않는 창. 명중률 대폭 증가",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 82, "accuracy": 50},
        "unique_effect": "never_miss|armor_penetration:0.15",
        "sell_price": 1800
    },

    # === 속도/연타 무기 ===
    "rapier": {
        "name": "레이피어",
        "description": "빠른 연속 공격",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 32, "speed": 12, "accuracy": 8},
        "unique_effect": "multi_strike:0.25|dodge_chance:0.10",
        "sell_price": 300
    },
    "twin_daggers": {
        "name": "쌍검",
        "description": "2회 연속 공격",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 40, "speed": 10, "critical": 10},
        "unique_effect": "double_strike|critical_chance:0.10",
        "sell_price": 650
    },
    "flurry_blade": {
        "name": "난무의 검",
        "description": "3~5회 연속 공격 (랜덤)",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 50, "speed": 15, "critical": 15},
        "unique_effect": "multi_strike:1.0|strike_count:3-5",  # 100% 확률로 3~5회
        "sell_price": 2000
    },

    # === 방어/탱커 무기 ===
    "shield_bash_mace": {
        "name": "방패격 메이스",
        "description": "공격 시 일정 확률로 적 스턴",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 42, "defense": 8},
        "unique_effect": "stun_chance:0.20|block_chance:0.10",
        "sell_price": 400
    },
    "defenders_hammer": {
        "name": "수호자의 망치",
        "description": "방어력에 비례한 추가 데미지",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 60, "defense": 20, "hp": 100},
        "unique_effect": "damage_from_defense:0.50|thorns:0.15",
        "sell_price": 1100
    },
    "aegis_blade": {
        "name": "이지스 검",
        "description": "공격과 방어를 겸비한 검",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_attack": 78, "defense": 30, "hp": 150},
        "unique_effect": "block_chance:0.25|counter_attack:0.30",
        "sell_price": 2300
    },

    # === 마법 무기 (특수 효과) ===
    "mana_blade": {
        "name": "마나 블레이드",
        "description": "MP를 소모해 추가 데미지",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 55, "magic_attack": 30, "mp": 50},
        "unique_effect": "mp_to_damage:2.0|mp_cost_per_hit:10",  # MP 10당 20 추가 데미지
        "sell_price": 950
    },
    "arcane_staff": {
        "name": "비전 지팡이",
        "description": "MP를 지속적으로 재생시키고 마법 성공률을 향상시킨다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"magic_attack": 60, "mp": 60, "spirit": 10},
        "unique_effect": "mp_regen:5|skill_success:0.15",  # 턴당 MP+5, 스킬 성공률 +15%
        "sell_price": 750
    },
    "chaos_orb_staff": {
        "name": "혼돈의 오브 지팡이",
        "description": "랜덤 속성 공격. 모든 속성 친화력",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 9,
        "base_stats": {"magic_attack": 100, "mp": 100, "luck": 20},
        "unique_effect": "random_element|all_element_affinity:0.20|wild_magic:0.30",
        "sell_price": 2800
    },
    "wisdom_tome": {
        "name": "지혜의 서",
        "description": "마법 공격력을 크게 향상시키고 스킬 성공률을 높인다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"magic_attack": 55, "mp": 70, "spirit": 15},
        "unique_effect": "spell_power:0.15|skill_success:0.20",
        "sell_price": 700
    },
    "elemental_scepter": {
        "name": "원소 홀",
        "description": "모든 원소 마법의 위력을 크게 향상시킨다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"magic_attack": 85, "mp": 90, "all_element_power": 25},
        "unique_effect": "elemental_mastery:0.25",
        "sell_price": 2100
    },
    "spell_amplifier": {
        "name": "주문 증폭기",
        "description": "마법 위력을 대폭 증가시키지만 MP 소비도 함께 증가한다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"magic_attack": 70, "mp": 60, "spirit": 12},
        "unique_effect": "spell_power:0.30|mp_cost_mult:1.20",
        "sell_price": 1000
    },
    "mana_channeler": {
        "name": "마나 전도체",
        "description": "MP를 지속적으로 재생시키고 마법 위력을 향상시킨다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"magic_attack": 90, "mp": 120, "spirit": 18},
        "unique_effect": "mp_regen:10|spell_power:0.20",
        "sell_price": 2400
    },
    "mind_staff": {
        "name": "정신력 지팡이",
        "description": "Spirit에 비례한 마법 공격력 증가",
        "rarity": ItemRarity.RARE,
        "level_requirement": 7,
        "base_stats": {"magic_attack": 65, "mp": 80, "spirit": 25},
        "unique_effect": "magic_from_spirit:0.50",  # Spirit의 50%를 마법 공격력에 추가
        "sell_price": 1300
    },
    "spell_echo_staff": {
        "name": "메아리 지팡이",
        "description": "가끔 스킬을 두 번 발동시킨다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"magic_attack": 95, "mp": 100, "spirit": 20},
        "unique_effect": "spell_echo:0.15",
        "sell_price": 2600
    },
    "void_wand": {
        "name": "공허의 지팡이",
        "description": "적의 MP를 흡수하여 자신의 마나를 회복한다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 7,
        "base_stats": {"magic_attack": 75, "mp": 90, "spirit": 15},
        "unique_effect": "mp_steal:0.20|mp_regen:8",
        "sell_price": 1500
    },
    "meteor_staff": {
        "name": "유성 지팡이",
        "description": "화염 마법 위력을 크게 증가시키지만 화염 저항력이 약해진다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"magic_attack": 68, "mp": 70, "fire_power": 40},
        "unique_effect": "fire_mastery:0.40|fire_weakness:0.20",
        "sell_price": 950
    },
    "blizzard_wand": {
        "name": "눈보라 마법봉",
        "description": "냉기 마법 위력을 크게 증가시키지만 냉기 저항력이 약해진다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"magic_attack": 68, "mp": 70, "ice_power": 40},
        "unique_effect": "ice_mastery:0.40|ice_weakness:0.20",
        "sell_price": 950
    },
    "thunderlord_rod": {
        "name": "천둥군주의 봉",
        "description": "번개 마법 위력을 크게 증가시키지만 번개 저항력이 약해진다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"magic_attack": 68, "mp": 70, "lightning_power": 40},
        "unique_effect": "lightning_mastery:0.40|lightning_weakness:0.20",
        "sell_price": 950
    },

    # === 원거리 무기 ===
    "hunters_bow": {
        "name": "사냥꾼의 활",
        "description": "야생 동물에게 추가 데미지",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 28, "accuracy": 12, "critical": 5},
        "unique_effect": "bonus_vs_beast:0.30|first_strike",
        "sell_price": 180
    },
    "sniper_rifle": {
        "name": "저격 활",
        "description": "극한의 명중률과 크리티컬",
        "rarity": ItemRarity.RARE,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 72, "accuracy": 40, "critical": 25},
        "unique_effect": "critical_damage:1.0|headshot:0.20",  # 20% 확률로 즉사
        "sell_price": 1400
    },
    "repeating_crossbow": {
        "name": "연발 석궁",
        "description": "3회 연속 공격",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 35, "accuracy": 10, "speed": 5},
        "unique_effect": "triple_shot|ammo_efficiency:0.20",
        "sell_price": 550
    },

    # === 디버프 무기 ===
    "poison_dagger": {
        "name": "독침 단검",
        "description": "공격 시 독 부여",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 35, "speed": 6},
        "unique_effect": "status_poison:0.40|poison_damage:10",  # 40% 독, 턴당 10 데미지
        "sell_price": 320
    },
    "cursed_blade": {
        "name": "저주받은 검",
        "description": "모든 디버프 확률 증가. 사용자도 HP -10%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 85, "magic_attack": 40, "hp": -100},
        "unique_effect": "debuff_master:0.30|curse_self:hp_max_reduction:0.10",
        "sell_price": 1300
    },
    "weakening_mace": {
        "name": "약화의 메이스",
        "description": "적 방어력 감소",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 44, "accuracy": 5},
        "unique_effect": "debuff_defense_down:0.25|armor_break:0.30",
        "sell_price": 420
    },
    "terror_scythe": {
        "name": "공포의 낫",
        "description": "공격 시 공포 부여. 적 회피율 감소",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 68, "magic_attack": 25, "critical": 15},
        "unique_effect": "status_fear:0.35|accuracy_debuff:0.20|harvest_soul:0.10",
        "sell_price": 1100
    },

    # === 특수 기믹 무기 ===
    "combo_master": {
        "name": "콤보 마스터",
        "description": "연속 공격 시 데미지 증가 (최대 5회)",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 70, "speed": 12, "critical": 10},
        "unique_effect": "combo_bonus:0.15|max_combo:5",  # 콤보당 +15%, 최대 75%
        "sell_price": 1900
    },
    "momentum_blade": {
        "name": "역전의 검",
        "description": "HP가 낮을수록 강해짐",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 60, "speed": 8},
        "unique_effect": "berserk|low_hp_bonus:1.0",  # HP 낮을수록 최대 +100%
        "sell_price": 900
    },
    "overload_staff": {
        "name": "과부하 지팡이",
        "description": "MP 소모 2배, 위력 2.5배",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"magic_attack": 110, "mp": 100, "spirit": 15},
        "unique_effect": "overload:mp_cost:2.0|damage:2.5",
        "sell_price": 2600
    },
    "gambler_dice": {
        "name": "도박사의 주사위",
        "description": "데미지가 50%~200% 사이로 랜덤",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 80, "luck": 30},
        "unique_effect": "random_damage:0.5-2.0|lucky_crit:0.20",
        "sell_price": 800
    },

    # === 레전더리 무기 ===
    "infinity_edge": {
        "name": "무한의 칼날",
        "description": "크리티컬 확률을 크게 증가시키고 크리티컬 데미지를 극대화한다",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 120, "critical": 50, "speed": 10},
        "unique_effect": "critical_chance:1.0|critical_damage:1.5|ignore_armor:0.30",
        "sell_price": 8000
    },
    "ultima_weapon": {
        "name": "얼티마 웨폰",
        "description": "HP가 가득 찰 때 모든 능력치가 크게 향상된다",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 13,
        "base_stats": {"physical_attack": 140, "magic_attack": 80, "hp": 200, "mp": 100},
        "unique_effect": "full_hp_bonus:all_stats:0.50|invincible_at_full_hp",
        "sell_price": 15000
    },
    "apocalypse": {
        "name": "아포칼립스",
        "description": "적 처치 시 모든 자원 회복. 영구 버프 누적",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 9,
        "base_stats": {"physical_attack": 135, "magic_attack": 70, "all_stats": 15},
        "unique_effect": "on_kill:restore_all|stack_buff:permanent|reaper:0.30",
        "sell_price": 12000
    },

    # === Steampunk Weapons ===
    "steam_powered_hammer": {
        "name": "증기 동력 망치",
        "description": "증기 압력으로 강력한 타격을 가하는 망치",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 65, "strength": 10, "speed": -5},
        "unique_effect": "stun_chance:0.25|steam_blast:damage:20",
        "sell_price": 850
    },
    "clockwork_crossbow": {
        "name": "태엽 석궁",
        "description": "정교한 태엽 장치로 자동 재장전되는 석궁",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 40, "accuracy": 15, "speed": 5},
        "unique_effect": "multi_strike:0.20|auto_reload",
        "sell_price": 450
    },
    "tesla_coil_wand": {
        "name": "테슬라 코일 완드",
        "description": "고전압 전류를 방출하여 적들을 감전시킨다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"magic_attack": 85, "mp": 60, "lightning_power": 30},
        "unique_effect": "chain_lightning:0.40|status_shock:0.30",
        "sell_price": 2200
    },

    # === Apocalypse Weapons ===
    "stop_sign_axe": {
        "name": "정지 표지판 도끼",
        "description": "도로 표지판을 날카롭게 갈아 만든 도끼",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 38, "hp": 30},
        "unique_effect": "durability_bonus:0.50",
        "sell_price": 150
    },
    "spiked_bat": {
        "name": "못 박힌 방망이",
        "description": "녹슨 못이 박힌 야구 방망이",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_attack": 20, "critical": 5},
        "unique_effect": "status_bleed:0.15",
        "sell_price": 60
    },
    "chainsaw_sword": {
        "name": "체인소드",
        "description": "엔진이 달린 톱날 검. 무시무시한 소리를 낸다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 75, "speed": -2},
        "unique_effect": "multi_hit:3|bleed_stack:0.20|low_durability",
        "sell_price": 1100
    },

    # === Sci-Fi/Future Weapons ===
    "laser_saber": {
        "name": "레이저 사벨",
        "description": "고열의 플라즈마 검날을 가진 무기",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"physical_attack": 90, "accuracy": 20, "speed": 10},
        "unique_effect": "ignore_armor:0.50|element:energy",
        "sell_price": 3500
    },
    "plasma_rifle": {
        "name": "플라즈마 라이플",
        "description": "초고온의 플라즈마 탄환을 발사한다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"physical_attack": 60, "magic_attack": 60, "accuracy": 15},
        "unique_effect": "status_burn:0.40|armor_melt:0.20",
        "sell_price": 1800
    },
    "nano_swarm_staff": {
        "name": "나노 스웜 스태프",
        "description": "나노봇 군단을 조종하여 적을 내부에서 파괴한다",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {"magic_attack": 110, "mp": 100, "spirit": 20},
        "unique_effect": "dot_damage:nano_virus|debuff_all:0.15",
        "sell_price": 8500
    },

    # === Fantasy/Past Weapons ===
    "obsidian_macuahuitl": {
        "name": "흑요석 마쿠아후이틀",
        "description": "날카로운 흑요석 조각이 박힌 나무 검",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 65, "critical": 20},
        "unique_effect": "status_bleed:0.50|fragile",
        "sell_price": 700
    },
    "mjolnir_replica": {
        "name": "묠니르 레플리카",
        "description": "천둥의 신이 사용하던 망치의 정교한 모조품",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 9,
        "base_stats": {"physical_attack": 125, "strength": 25, "lightning_power": 50},
        "unique_effect": "element:lightning|return_to_hand|stun_chance:0.40",
        "sell_price": 9000
    },

    # === Crossover/Other Weapons ===
    "portal_gun": {
        "name": "포털 건",
        "description": "공간을 이어주는 장치. 적을 혼란시킨다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"magic_attack": 70, "evasion": 30, "speed": 15},
        "unique_effect": "teleport_dodge|status_confusion:0.30",
        "sell_price": 4000
    },
    "crowbar": {
        "name": "빠루",
        "description": "물리학자의 무기. 외계 생명체에게 효과적",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 35, "accuracy": 10},
        "unique_effect": "bonus_vs_alien:0.50|crate_breaker",
        "sell_price": 300
    },
    
    # === More Steampunk Weapons ===
    "brass_knuckles": {
        "name": "황동 너클",
        "description": "증기 기관으로 작동하는 강화 너클",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 32, "speed": 8, "critical": 10},
        "unique_effect": "lifesteal:0.10|steam_burn:0.15",
        "sell_price": 280
    },
    "gear_shield_lance": {
        "name": "기어 실드 랜스",
        "description": "회전하는 톱니바퀴가 박힌 창",
        "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 70, "physical_defense": 15},
        "unique_effect": "counter_attack:0.20|armor_shred:0.15",
        "sell_price": 1200
    },
    "steam_gatling": {
        "name": "증기 개틀링",
        "description": "증기압으로 연속 발사하는 기관총",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 55, "speed": -8},
        "unique_effect": "multi_strike:0.60|overheat_damage",
        "sell_price": 2800
    },
    "chrono_wrench": {
        "name": "시간 렌치",
        "description": "시간을 조작하는 신비한 도구",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {"physical_attack": 95, "magic_attack": 65, "speed": 15},
        "unique_effect": "cooldown_reduction:0.25|time_stop:0.10",
        "sell_price": 9500
    },
    "pressure_blade": {
        "name": "압력 검",
        "description": "고압 증기를 검날로 방출한다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 58, "magic_attack": 22},
        "unique_effect": "status_burn:0.30|steam_blast:15",
        "sell_price": 950
    },

    # === More Apocalypse Weapons ===
    "rusty_pipe": {
        "name": "녹슨 파이프",
        "description": "평범한 쇠파이프지만 나름 쓸만하다",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_attack": 18, "hp": 20},
        "unique_effect": "durability:high",
        "sell_price": 45
    },
    "molotov_launcher": {
        "name": "화염병 발사기",
        "description": "개조된 발사관으로 화염병을 쏜다",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 42, "fire_power": 25},
        "unique_effect": "status_burn:0.50|aoe:small",
        "sell_price": 580
    },
    "scrap_bow": {
        "name": "고철 활",
        "description": "자동차 부품으로 만든 활",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 38, "accuracy": 12, "critical": 8},
        "unique_effect": "silent_kill|scavenger_bonus:0.20",
        "sell_price": 320
    },
    "nail_gun": {
        "name": "못 총",
        "description": "산업용 못 총을 무기로 개조",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 52, "accuracy": 18, "speed": 6},
        "unique_effect": "status_bleed:0.40|piercing:0.25",
        "sell_price": 880
    },
    "sledgehammer": {
        "name": "대형 망치",
        "description": "건설용 대형 해머",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 68, "speed": -6, "critical_damage": 30},
        "unique_effect": "stun_chance:0.30|structure_damage:2.0",
        "sell_price": 420
    },
    "road_sign_sword": {
        "name": "도로 표지 검",
        "description": "표지판을 갈아 만든 검",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_attack": 22, "accuracy": 5},
        "unique_effect": "bonus_vs_vehicles:0.30",
        "sell_price": 90
    },

    # === More Sci-Fi Weapons ===
    "ion_cannon": {
        "name": "이온 캐논",
        "description": "전자기장을 왜곡시켜 발사한다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"magic_attack": 95, "mp": 80, "accuracy": 15},
        "unique_effect": "status_shock:0.50|shield_break|emp:0.30",
        "sell_price": 4200
    },
    "photon_blade": {
        "name": "광자 검",
        "description": "순수한 빛으로 만들어진 검날",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 11,
        "base_stats": {"physical_attack": 115, "magic_attack": 85, "speed": 18},
        "unique_effect": "ignore_armor:0.75|light_speed_strike|holy_damage:0.40",
        "sell_price": 11000
    },
    "quantum_rifle": {
        "name": "양자 라이플",
        "description": "양자 붕괴를 이용한 무기",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 9,
        "base_stats": {"physical_attack": 88, "magic_attack": 55, "critical": 25},
        "unique_effect": "phase_through:0.20|quantum_crit:0.35",
        "sell_price": 5500
    },
    "cryo_gun": {
        "name": "냉동총",
        "description": "극저온 광선을 발사한다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"magic_attack": 72, "ice_power": 35},
        "unique_effect": "status_freeze:0.45|slow:0.30|shatter:0.20",
        "sell_price": 1900
    },
    "antimatter_blade": {
        "name": "반물질 검",
        "description": "반물질로 코팅된 검",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 12,
        "base_stats": {"physical_attack": 140, "magic_attack": 60},
        "unique_effect": "annihilation:0.15|ignore_defense:0.80|unstable",
        "sell_price": 15000
    },
    "graviton_hammer": {
        "name": "중력자 해머",
        "description": "중력을 조작하는 망치",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"physical_attack": 102, "strength": 18},
        "unique_effect": "gravity_crush:0.25|stun_chance:0.35|slow_field",
        "sell_price": 4800
    },

    # === Fantasy/Medieval Weapons ===
    "iron_longsword": {
        "name": "철 장검",
        "description": "튼튼한 철제 장검",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_attack": 25, "strength": 3},
        "unique_effect": "reliable",
        "sell_price": 100
    },
    "silver_rapier": {
        "name": "은 레이피어",
        "description": "가볍고 빠른 찌르기 검",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 40, "speed": 12, "accuracy": 15},
        "unique_effect": "critical_chance:0.15|riposte:0.20",
        "sell_price": 480
    },
    "flame_sword": {
        "name": "화염 검",
        "description": "불꽃이 타오르는 검",
        "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 65, "magic_attack": 30, "fire_power": 25},
        "unique_effect": "status_burn:0.40|fire_slash",
        "sell_price": 1400
    },
    "frost_axe": {
        "name": "서리 도끼",
        "description": "얼음 기운이 깃든 도끼",
        "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 72, "ice_power": 28},
        "unique_effect": "status_freeze:0.35|slow:0.40|ice_cleave",
        "sell_price": 1350
    },
    "thunder_spear": {
        "name": "번개 창",
        "description": "번개를 부르는 마법 창",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 78, "magic_attack": 45, "lightning_power": 40},
        "unique_effect": "chain_lightning:0.50|status_shock:0.40",
        "sell_price": 3200
    },
    "holy_mace": {
        "name": "성스러운 메이스",
        "description": "신성한 힘이 깃든 철퇴",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_attack": 75, "magic_attack": 35, "spirit": 15},
        "unique_effect": "holy_damage:0.30|undead_slayer:0.50|heal_on_hit:0.10",
        "sell_price": 2700
    },
    "cursed_dagger": {
        "name": "저주받은 단검",
        "description": "어둠의 힘이 깃든 단검",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_attack": 55, "magic_attack": 48, "critical": 30},
        "unique_effect": "lifesteal:0.20|curse:0.25|critical_damage:0.40",
        "sell_price": 2400
    },
    "war_hammer": {
        "name": "전쟁 망치",
        "description": "무거운 전투용 망치",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 80, "strength": 12, "speed": -4},
        "unique_effect": "stun_chance:0.40|armor_crush:0.25",
        "sell_price": 980
    },
    "elven_bow": {
        "name": "엘프 활",
        "description": "정교하게 만들어진 엘프의 장궁",
        "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 62, "accuracy": 25, "critical": 15, "speed": 5},
        "unique_effect": "piercing:0.30|wind_shot|nature_bonus:0.20",
        "sell_price": 1500
    },
    "battle_axe": {
        "name": "전투 도끼",
        "description": "양날의 커다란 전투 도끼",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 58, "strength": 8, "critical_damage": 25},
        "unique_effect": "cleave|bleeding:0.25",
        "sell_price": 520
    },
    "katana": {
        "name": "카타나",
        "description": "예리한 동양의 검",
        "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 68, "speed": 10, "critical": 20},
        "unique_effect": "critical_damage:0.50|iaido|precision_strike",
        "sell_price": 1600
    },
    "scimitar": {
        "name": "시미타",
        "description": "휘어진 곡도",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 45, "speed": 8, "evasion": 10},
        "unique_effect": "swift_strikes|parry:0.15",
        "sell_price": 460
    },
    "halberd": {
        "name": "할버드",
        "description": "긴 자루의 다목적 무기",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 70, "physical_defense": 10, "accuracy": 5},
        "unique_effect": "reach|anti_cavalry:0.40|versatile",
        "sell_price": 1100
    },
    "scythe": {
        "name": "사신의 낫",
        "description": "죽음을 베는 낫",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 85, "magic_attack": 40, "critical": 25},
        "unique_effect": "reaper:0.30|soul_harvest|lifesteal:0.15",
        "sell_price": 3500
    },

    # === Magical/Elemental Weapons ===
    "inferno_staff": {
        "name": "업화의 지팡이",
        "description": "지옥불을 부르는 마법 지팡이",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"magic_attack": 100, "mp": 90, "fire_power": 50},
        "unique_effect": "status_burn:0.60|fire_explosion:0.30|spell_power:0.25",
        "sell_price": 4500
    },
    "glacial_orb": {
        "name": "빙하의 구슬",
        "description": "절대영도의 힘이 담긴 구슬",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"magic_attack": 95, "mp": 85, "ice_power": 55},
        "unique_effect": "status_freeze:0.55|ice_storm|mana_freeze:0.20",
        "sell_price": 4300
    },
    "storm_wand": {
        "name": "폭풍의 완드",
        "description": "태풍을 소환하는 완드",
        "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"magic_attack": 78, "mp": 75, "wind_power": 35},
        "unique_effect": "chain_lightning:0.40|tornado|knockback",
        "sell_price": 2100
    },
    "earth_mace": {
        "name": "대지의 메이스",
        "description": "땅의 힘이 깃든 철퇴",
        "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 70, "magic_attack": 30, "hp": 50},
        "unique_effect": "earthquake:0.25|stun_chance:0.30|earth_shield",
        "sell_price": 1450
    },
    "void_blade": {
        "name": "공허의 검",
        "description": "무(無)의 힘이 깃든 검",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {"physical_attack": 110, "magic_attack": 80, "dark_power": 60},
        "unique_effect": "void_cut|mp_drain:0.15|existence_erasure:0.10",
        "sell_price": 10000
    },
    "light_scepter": {
        "name": "빛의 홀",
        "description": "성스러운 빛의 권능",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"magic_attack": 88, "mp": 100, "spirit": 20},
        "unique_effect": "holy_damage:0.40|heal_allies:0.15|dispel",
        "sell_price": 3800
    },
    "shadow_dagger": {
        "name": "그림자 단검",
        "description": "어둠에 숨는 암살검",
        "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 52, "magic_attack": 38, "speed": 15, "evasion": 15},
        "unique_effect": "backstab:2.0|stealth_bonus|critical_chance:0.20",
        "sell_price": 1550
    },
    "chaos_orb": {
        "name": "혼돈의 구체",
        "description": "무작위 마법을 발동하는 구체",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"magic_attack": 85, "mp": 80, "all_elements": 25},
        "unique_effect": "random_element|chaos_surge:0.30|unpredictable",
        "sell_price": 4000
    },
    "nature_staff": {
        "name": "자연의 지팡이",
        "description": "생명의 힘이 흐르는 지팡이",
        "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"magic_attack": 75, "mp": 70, "spirit": 15, "hp": 40},
        "unique_effect": "hp_regen:0.03|poison:0.35|entangle:0.25",
        "sell_price": 1800
    },
    "blood_whip": {
        "name": "피의 채찍",
        "description": "적의 피를 빨아들이는 채찍",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 65, "magic_attack": 55},
        "unique_effect": "lifesteal:0.30|status_bleed:0.50|blood_frenzy",
        "sell_price": 3300
    },

    # === Modern Weapons ===
    "combat_knife": {
        "name": "전투 나이프",
        "description": "군용 전투 단검",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_attack": 32, "speed": 10, "critical": 12},
        "unique_effect": "silent_kill|bleeding:0.20|quick_strike",
        "sell_price": 280
    },
    "assault_rifle": {
        "name": "돌격 소총",
        "description": "현대식 자동 소총",
        "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 68, "accuracy": 15, "speed": 3},
        "unique_effect": "burst_fire:3|suppression",
        "sell_price": 1650
    },
    "sniper_rifle": {
        "name": "저격 소총",
        "description": "장거리 정밀 사격총",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 105, "accuracy": 35, "critical": 30, "speed": -5},
        "unique_effect": "headshot:3.0|piercing:0.50|long_range",
        "sell_price": 3900
    },
    "shotgun": {
        "name": "산탄총",
        "description": "근거리 강력한 산탄총",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 85, "speed": -3},
        "unique_effect": "shotgun_spread|knockback|close_range_bonus:0.40",
        "sell_price": 1200
    },
    "grenade_launcher": {
        "name": "유탄 발사기",
        "description": "폭발물을 발사하는 무기",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"physical_attack": 95, "fire_power": 40},
        "unique_effect": "explosion:large|status_burn:0.40|aoe_damage",
        "sell_price": 4400
    },
    "tactical_tomahawk": {
        "name": "전술 토마호크",
        "description": "현대식 전투 도끼",
        "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 64, "critical": 18, "accuracy": 12},
        "unique_effect": "throwable|bleeding:0.30|armor_break:0.20",
        "sell_price": 1400
    },
    "taser_baton": {
        "name": "전기봉",
        "description": "전기 충격을 가하는 봉",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_attack": 38, "magic_attack": 25},
        "unique_effect": "status_shock:0.50|stun_chance:0.35|nonlethal",
        "sell_price": 480
    },

    # === Legendary/Unique Weapons ===
    "excalibur": {
        "name": "엑스칼리버",
        "description": "전설의 성검",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 12,
        "base_stats": {"physical_attack": 150, "magic_attack": 80, "all_stats": 20},
        "unique_effect": "holy_damage:0.50|light_beam|auto_revive|chosen_one",
        "sell_price": 25000
    },
    "muramasa": {
        "name": "무라마사",
        "description": "피를 원하는 마검",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 11,
        "base_stats": {"physical_attack": 145, "critical": 40, "speed": 15},
        "unique_effect": "bloodthirst|lifesteal:0.25|critical_damage:0.80|cursed",
        "sell_price": 20000
    },
    "gungnir": {
        "name": "궁니르",
        "description": "반드시 적중하는 신창",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 11,
        "base_stats": {"physical_attack": 135, "magic_attack": 70, "accuracy": 50},
        "unique_effect": "never_miss|return_to_hand|piercing:0.80|rune_power",
        "sell_price": 22000
    },
    "frostmourne": {
        "name": "프로스트모른",
        "description": "영혼을 흡수하는 마검",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 12,
        "base_stats": {"physical_attack": 140, "magic_attack": 90, "ice_power": 70},
        "unique_effect": "soul_reaper|status_freeze:0.70|lifesteal:0.30|undead_army",
        "sell_price": 28000
    },
    "infinity_blade": {
        "name": "무한의 검",
        "description": "끝없는 힘을 가진 검",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 13,
        "base_stats": {"physical_attack": 160, "magic_attack": 100, "all_stats": 25},
        "unique_effect": "infinite_power|dimension_slash|time_stop:0.05",
        "sell_price": 35000
    },
    "dragons_tooth": {
        "name": "용의 이빨",
        "description": "고대 용의 송곳니로 만든 검",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {"physical_attack": 128, "fire_power": 60, "strength": 25},
        "unique_effect": "dragon_breath|status_burn:0.60|scale_armor|fire_immunity",
        "sell_price": 18000
    },
    "death_scythe": {
        "name": "죽음의 낫",
        "description": "영혼을 베는 사신의 무기",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 11,
        "base_stats": {"physical_attack": 125, "magic_attack": 95, "dark_power": 65},
        "unique_effect": "reaper:0.50|soul_harvest|instant_death:0.05|lifesteal:0.25",
        "sell_price": 23000
    },
    "ragnarok": {
        "name": "라그나로크",
        "description": "세계의 종말을 가져오는 검",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 14,
        "base_stats": {"physical_attack": 170, "magic_attack": 110, "all_stats": 30},
        "unique_effect": "apocalypse|all_element_damage:0.60|world_ender|divine_wrath",
        "sell_price": 50000
    },
}

ARMOR_TEMPLATES = {
    # 갑옷
    "leather_armor": {
        "name": "가죽 갑옷",
        "description": "기본적인 가죽 갑옷",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_defense": 10, "hp": 20},
        "sell_price": 40
    },
    "chainmail": {
        "name": "사슬 갑옷",
        "description": "사슬로 엮은 갑옷",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_defense": 25, "hp": 40},
        "sell_price": 120
    },
    "plate_armor": {
        "name": "판금 갑옷",
        "description": "무거운 철판 갑옷",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 50, "hp": 80, "physical_attack": -5},
        "sell_price": 600
    },
    "dragon_scale_armor": {
        "name": "용비늘 갑옷",
        "description": "드래곤의 비늘로 만든 갑옷",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 90, "magic_defense": 70, "hp": 150},
        "sell_price": 8000
    },

    # 로브
    "cloth_robe": {
        "name": "천 로브",
        "description": "마법사용 천 로브",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"magic_defense": 12, "mp": 15},
        "sell_price": 50
    },
    "mage_robe": {
        "name": "마법사 로브",
        "description": "마력이 깃든 로브",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"magic_defense": 40, "mp": 50, "magic_attack": 10},
        "sell_price": 500
    },
    "archmage_robe": {
        "name": "대마법사 로브",
        "description": "강력한 마력의 로브",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"magic_defense": 70, "mp": 100, "magic_attack": 25},
        "sell_price": 2000
    },
    "celestial_robes": {
        "name": "천상의 로브",
        "description": "별들의 힘이 담긴 로브",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 7,
        "base_stats": {"magic_defense": 100, "mp": 150, "magic_attack": 40, "spirit": 15},
        "sell_price": 7000
    },

    # 경갑
    "padded_armor": {
        "name": "누빔 갑옷",
        "description": "가벼운 갑옷",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_defense": 8, "evasion": 5},
        "sell_price": 38
    },
    "studded_leather": {
        "name": "징박이 가죽",
        "description": "가죽에 징을 박은 갑옷",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 22, "evasion": 8, "hp": 30},
        "sell_price": 180
    },
    "scale_mail": {
        "name": "비늘 갑옷",
        "description": "비늘 모양으로 만든 갑옷",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_defense": 45, "magic_defense": 25, "hp": 70},
        "sell_price": 800
    },

    # 중갑 추가
    "knight_armor": {
        "name": "기사 갑옷",
        "description": "기사단의 갑옷",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_defense": 35, "hp": 50, "strength": 5},
        "sell_price": 350
    },
    "dragon_armor": {
        "name": "드래곤 아머",
        "description": "용의 힘이 깃든 갑옷",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 11,
        "base_stats": {"physical_defense": 95, "magic_defense": 75, "hp": 180, "strength": 12},
        "sell_price": 9000
    },

    # === 상처 시스템 연동 방어구 ===
    "healers_robe": {
        "name": "치유사의 로브",
        "description": "받는 상처를 크게 줄이고 회복 효과를 향상시킨다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"magic_defense": 35, "spirit": 12, "hp": 80},
        "unique_effect": "wound_reduction:0.30|heal_boost:0.20",
        "sell_price": 650
    },
    "regenerative_armor": {
        "name": "재생의 갑옷",
        "description": "턴마다 상처 회복. HP 재생",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 60, "hp": 150, "defense": 15},
        "unique_effect": "wound_regen:5|hp_regen:0.03",  # 턴당 상처 5, HP 3%
        "sell_price": 1800
    },
    "scarless_plate": {
        "name": "무흔의 판금",
        "description": "상처에 면역이 되지만 받는 데미지가 약간 증가한다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"physical_defense": 70, "magic_defense": 40, "hp": 120},
        "unique_effect": "wound_immunity|damage_taken:0.10",
        "sell_price": 2200
    },
    "trauma_ward": {
        "name": "외상 보호복",
        "description": "받는 상처를 크게 감소시킨다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 45, "magic_defense": 30, "hp": 100},
        "unique_effect": "wound_reduction:0.50",
        "sell_price": 850
    },

    # === BRV 시스템 연동 방어구 ===
    "brave_guard": {
        "name": "브레이브 가드",
        "description": "BRV 데미지를 감소시키고 BREAK 상태이상을 저항한다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 40, "magic_defense": 35, "hp": 90},
        "unique_effect": "brv_shield:0.30|brv_protect",  # BREAK 1회 방지
        "sell_price": 700
    },
    "fortress_plate": {
        "name": "요새 판금",
        "description": "BRV 데미지를 크게 감소시키지만 행동 속도가 느려진다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 85, "hp": 200, "speed": -5},
        "unique_effect": "brv_shield:0.50|block_chance:0.20",
        "sell_price": 2000
    },
    "breaker_armor": {
        "name": "파괴자의 갑옷",
        "description": "BRV 축적량을 증가시키지만 방어력이 감소한다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_defense": 35, "hp": 80},
        "unique_effect": "brv_bonus:0.25|defense_reduction:0.20",
        "sell_price": 800
    },

    # === 마법사 전용 로브 ===
    "apprentice_robe": {
        "name": "견습 마법사의 로브",
        "description": "MP를 재생시키고 마법 공격력을 향상시킨다",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"magic_defense": 12, "mp": 40, "magic_attack": 12},
        "unique_effect": "mp_regen:3",
        "sell_price": 150
    },
    "battle_mage_robe": {
        "name": "전투 마법사의 로브",
        "description": "마법 위력을 향상시키고 MP 소비를 감소시킨다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"magic_defense": 40, "mp": 80, "magic_attack": 25, "spirit": 12},
        "unique_effect": "spell_power:0.15|mp_cost_reduction:0.10",
        "sell_price": 750
    },
    "sorcerer_vestments": {
        "name": "마도사의 예복",
        "description": "MP를 빠르게 재생시키고 마법 위력과 마법 방어력을 향상시킨다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"magic_defense": 65, "mp": 120, "magic_attack": 35, "spirit": 18},
        "unique_effect": "mp_regen:10|spell_power:0.10|magic_defense_boost:0.25",
        "sell_price": 2000
    },
    "wisdom_robes": {
        "name": "지혜의 로브",
        "description": "정신력과 MP 최대치를 크게 향상시킨다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"magic_defense": 48, "mp": 120, "spirit": 28, "magic_attack": 20},
        "unique_effect": "spell_success:0.20",  # 스킬 성공률 +20%
        "sell_price": 950
    },
    "elemental_master_robe": {
        "name": "원소 대가의 로브",
        "description": "모든 원소 저항력을 향상시키고 원소 마법 위력을 크게 증가시킨다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"magic_defense": 72, "mp": 130, "magic_attack": 40, "spirit": 20},
        "unique_effect": "all_element_resist:0.20|elemental_mastery:0.25",
        "sell_price": 2400
    },
    "mana_weave_cloak": {
        "name": "마나직 망토",
        "description": "MP 소비를 크게 감소시키고 마법 방어력을 향상시킨다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"magic_defense": 55, "mp": 100, "spirit": 15},
        "unique_effect": "mp_cost_reduction:0.25|magic_defense_boost:0.30",
        "sell_price": 1100
    },
    "spell_reflect_robe": {
        "name": "주문 반사 로브",
        "description": "마법 공격을 반사하고 마법 방어력을 크게 향상시킨다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"magic_defense": 85, "mp": 110, "spirit": 22},
        "unique_effect": "spell_reflect:0.30",
        "sell_price": 2700
    },

    # === HP/MP 재생 방어구 ===
    "troll_hide": {
        "name": "트롤 가죽",
        "description": "턴당 HP 5% 재생. 화염 약점",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 38, "hp": 120},
        "unique_effect": "hp_regen:0.05|weakness_fire",
        "sell_price": 600
    },
    "phoenix_mail": {
        "name": "불사조 갑옷",
        "description": "HP를 지속적으로 재생시키며 사망 시 한 번 부활한다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_defense": 75, "magic_defense": 60, "hp": 150},
        "unique_effect": "hp_regen:0.03|phoenix_rebirth",
        "sell_price": 2800
    },
    "mana_silk_robe": {
        "name": "마나 실크 로브",
        "description": "MP를 지속적으로 재생시키고 MP 소비를 감소시킨다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"magic_defense": 45, "mp": 80, "magic_attack": 15},
        "unique_effect": "mp_regen:8|mp_cost_reduction:0.10",
        "sell_price": 750
    },
    "archmage_vestments": {
        "name": "대마법사의 예복",
        "description": "MP를 빠르게 재생시키고 마법 위력을 크게 향상시키며 마법 공격을 부분적으로 반사한다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"magic_defense": 70, "mp": 150, "magic_attack": 35, "spirit": 18},
        "unique_effect": "mp_regen:12|spell_power:0.15|spell_reflect:0.20",
        "sell_price": 2500
    },

    # === 가시/반사 방어구 ===
    "thorned_armor": {
        "name": "가시 갑옷",
        "description": "피격 시 데미지의 25% 반사",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_defense": 32, "hp": 60},
        "unique_effect": "thorns:0.25",
        "sell_price": 350
    },
    "reflecting_plate": {
        "name": "반사 판금",
        "description": "피격 시 데미지를 반사하고 마법 공격을 크게 반사한다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"physical_defense": 72, "magic_defense": 55, "hp": 140},
        "unique_effect": "thorns:0.40|spell_reflect:0.50",
        "sell_price": 2200
    },
    "vengeful_mail": {
        "name": "복수의 갑옷",
        "description": "피격 시 반격 30% 확률",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_defense": 55, "hp": 110, "strength": 8},
        "unique_effect": "counter_attack:0.30|vengeance_damage:0.20",
        "sell_price": 1100
    },

    # === 방어/블록 방어구 ===
    "tower_shield_armor": {
        "name": "탑 방패 갑옷",
        "description": "블록 확률 30%. 블록 시 데미지 무효",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_defense": 65, "hp": 150, "speed": -3},
        "unique_effect": "block_chance:0.30|block_perfect",
        "sell_price": 950
    },
    "adamantine_armor": {
        "name": "아다만타이트 갑옷",
        "description": "모든 데미지 15 감소. 크리티컬 무효",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 10,
        "base_stats": {"physical_defense": 90, "magic_defense": 70, "hp": 200},
        "unique_effect": "flat_damage_reduction:15|crit_immunity",
        "sell_price": 3200
    },
    "guardian_plate": {
        "name": "수호자의 판금",
        "description": "아군 보호. 아군이 받는 데미지 10% 대신 받음",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_defense": 80, "magic_defense": 60, "hp": 180},
        "unique_effect": "ally_protect:0.10|damage_redirect",
        "sell_price": 2400
    },

    # === 회피 방어구 ===
    "shadow_cloak": {
        "name": "그림자 망토",
        "description": "회피율을 크게 향상시키고 어둠 속성에 저항한다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"magic_defense": 30, "evasion": 25, "speed": 8},
        "unique_effect": "dodge_chance:0.25|shadow_resistance:0.50",
        "sell_price": 700
    },
    "mirage_vestments": {
        "name": "신기루 예복",
        "description": "회피율을 대폭 증가시키고 회피 시 반격한다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"magic_defense": 55, "evasion": 35, "speed": 12, "luck": 10},
        "unique_effect": "dodge_chance:0.35|dodge_counter",
        "sell_price": 2000
    },
    "windwalker_armor": {
        "name": "바람걸음 갑옷",
        "description": "회피율과 BRV 흡수율을 크게 향상시킨다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 35, "evasion": 20, "speed": 15},
        "unique_effect": "dodge_chance:0.20|brv_steal:0.30",
        "sell_price": 800
    },

    # === 속성 저항 방어구 ===
    "fire_dragon_scale": {
        "name": "화염 드래곤 비늘",
        "description": "화염 면역. 화염 흡수로 HP 회복",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"physical_defense": 70, "magic_defense": 65, "hp": 140},
        "unique_effect": "fire_immunity|fire_absorb",
        "sell_price": 2300
    },
    "frost_plate": {
        "name": "서리 판금",
        "description": "냉기 면역. 공격받을 시 적 속도 감소",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_defense": 58, "magic_defense": 50, "hp": 110},
        "unique_effect": "ice_immunity|on_hit_slow:0.30",
        "sell_price": 1200
    },
    "storm_mail": {
        "name": "폭풍 갑옷",
        "description": "번개 면역. 전기 데미지 반사",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 65, "magic_defense": 60, "hp": 120, "speed": 8},
        "unique_effect": "lightning_immunity|lightning_reflect",
        "sell_price": 1900
    },
    "rainbow_robe": {
        "name": "무지개 로브",
        "description": "모든 속성 저항 +30%",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"magic_defense": 75, "spirit": 20, "hp": 130, "mp": 80},
        "unique_effect": "all_element_resist:0.30",
        "sell_price": 2700
    },

    # === 상태 이상 관련 방어구 ===
    "immunity_cloak": {
        "name": "면역 망토",
        "description": "독, 화상, 출혈 면역",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"magic_defense": 48, "hp": 100, "spirit": 10},
        "unique_effect": "status_immunity:poison,burn,bleed",
        "sell_price": 950
    },
    "cleansing_armor": {
        "name": "정화의 갑옷",
        "description": "모든 디버프 지속시간 -50%",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"physical_defense": 72, "magic_defense": 65, "hp": 150, "spirit": 15},
        "unique_effect": "debuff_duration:-0.50|cleanse_on_turn:0.30",  # 30% 확률로 디버프 제거
        "sell_price": 2300
    },
    "stalwart_plate": {
        "name": "불굴의 판금",
        "description": "스턴, 수면, 혼란 면역",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_defense": 80, "hp": 180, "spirit": 12},
        "unique_effect": "cc_immunity:stun,sleep,confusion",
        "sell_price": 2500
    },

    # === 특수 기믹 방어구 ===
    "berserker_hide": {
        "name": "광전사의 가죽",
        "description": "HP 50% 이하 시 공격력 +40%, 방어력 -20%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_defense": 45, "hp": 130, "strength": 12},
        "unique_effect": "berserk_mode:hp_below_50|attack:0.40|defense:-0.20",
        "sell_price": 1100
    },
    "glass_armor": {
        "name": "유리 갑옷",
        "description": "모든 데미지 +30%. 받는 데미지 +50%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 20, "magic_defense": 15},
        "unique_effect": "glass_cannon:damage:0.30|taken:0.50",
        "sell_price": 1200
    },
    "bloodthirst_armor": {
        "name": "피의 갈증 갑옷",
        "description": "적 처치 시 최대 HP +10 (영구, 최대 10회)",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"physical_defense": 70, "hp": 150, "strength": 10},
        "unique_effect": "on_kill:max_hp:10|stack_max:10",
        "sell_price": 2600
    },
    "adaptive_mail": {
        "name": "적응형 갑옷",
        "description": "받은 데미지 타입에 저항 획득 (3턴)",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 9,
        "base_stats": {"physical_defense": 75, "magic_defense": 75, "hp": 160},
        "unique_effect": "adaptive_resistance:0.20|duration:3",
        "sell_price": 2900
    },

    # === 레전더리 방어구 ===
    "aegis_of_eternity": {
        "name": "영원의 이지스",
        "description": "모든 방어 +100. 블록 확률 50%. 불사 (HP 1로 생존 1회)",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 9,
        "base_stats": {"physical_defense": 120, "magic_defense": 110, "hp": 300, "all_stats": 15},
        "unique_effect": "block_chance:0.50|immortality:once|all_resist:0.30",
        "sell_price": 15000
    },
    "celestial_raiment": {
        "name": "천상의 예복",
        "description": "모든 속성 저항 50%. 상처 면역. MP 재생 +15",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 7,
        "base_stats": {"magic_defense": 110, "mp": 200, "spirit": 25, "magic_attack": 50},
        "unique_effect": "all_element_resist:0.50|wound_immunity|mp_regen:15|spell_power:0.30",
        "sell_price": 13000
    },

    # === Steampunk Armor ===
    "brass_plate_armor": {
        "name": "황동 판금 갑옷",
        "description": "증기 기관의 열기와 압력을 견디는 황동 갑옷",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_defense": 60, "hp": 100, "fire_resist": 20, "water_resist": 20},
        "unique_effect": "steam_resistance:0.30",
        "sell_price": 900
    },
    "aviator_jacket": {
        "name": "비행사 자켓",
        "description": "하늘을 나는 비행사들의 가죽 자켓",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 25, "speed": 10, "wind_resist": 15},
        "unique_effect": "speed_boost:0.10",
        "sell_price": 400
    },

    # === Apocalypse Armor ===
    "tire_tread_armor": {
        "name": "타이어 갑옷",
        "description": "폐타이어를 엮어 만든 투박한 갑옷",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"physical_defense": 45, "magic_defense": 5, "hp": 60},
        "unique_effect": "melee_reflect:0.10",
        "sell_price": 250
    },
    "hazmat_suit": {
        "name": "방호복",
        "description": "유해 물질로부터 신체를 보호하는 수트",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"physical_defense": 20, "magic_defense": 20, "hp": 50},
        "unique_effect": "status_immunity:poison,acid,radiation",
        "sell_price": 800
    },

    # === Sci-Fi/Future Armor ===
    "energy_shield_suit": {
        "name": "에너지 실드 수트",
        "description": "피격을 감지하여 에너지 방어막을 전개한다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 30, "magic_defense": 30, "mp": 50},
        "unique_effect": "energy_shield:hp:200|regen_shield",
        "sell_price": 2500
    },
    "power_armor_mk1": {
        "name": "파워 아머 MK-1",
        "description": "근력을 증폭시키는 강화 외골격 슈트",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {"physical_defense": 120, "magic_defense": 80, "strength": 30, "hp": 250, "speed": -10},
        "unique_effect": "strength_boost:0.20|carry_weight:50",
        "sell_price": 10000
    },
    
    # === More Light Armor ===
    "silk_robe": {
        "name": "실크 로브",
        "description": "부드러운 실크 로브",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"magic_defense": 25, "mp": 30, "speed": 5},
        "unique_effect": "mp_regen:3",
        "sell_price": 200
    },
    "mage_vestments": {
        "name": "마법사 예복",
        "description": "마법사를 위한 전통 복장",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"magic_defense": 45, "mp": 70, "magic_attack": 25, "spirit": 10},
        "unique_effect": "spell_power:0.15|mp_cost_reduction:0.10",
        "sell_price": 1100
    },
    "archmage_robes": {
        "name": "대마법사 로브",
        "description": "최고위 마법사의 상징",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"magic_defense": 75, "mp": 150, "magic_attack": 45, "spirit": 20},
        "unique_effect": "spell_power:0.30|mp_regen:10|spell_echo:0.15",
        "sell_price": 3800
    },
    "shadow_cloak": {
        "name": "그림자 망토",
        "description": "어둠에 숨을 수 있는 망토",
        "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_defense": 30, "evasion": 25, "speed": 15},
        "unique_effect": "stealth_bonus|dodge_chance:0.20|shadow_step",
        "sell_price": 1400
    },
    "wind_dancer_garb": {
        "name": "바람춤꾼 의상",
        "description": "바람의 정령과 춤추는 자의 옷",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"magic_defense": 60, "evasion": 30, "speed": 20, "wind_power": 35},
        "unique_effect": "dodge_chance:0.30|wind_evasion|tornado_shield",
        "sell_price": 3200
    },

    # === More Medium Armor ===
    "chainmail": {
        "name": "사슬 갑옷",
        "description": "고리로 엮은 중형 갑옷",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 2,
        "base_stats": {"physical_defense": 40, "hp": 50},
        "unique_effect": "slash_resist:0.20",
        "sell_price": 250
    },
    "reinforced_leather": {
        "name": "강화 가죽 갑옷",
        "description": "철판을 덧댄 가죽 갑옷",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 55, "magic_defense": 20, "hp": 70},
        "unique_effect": "melee_resist:0.15",
        "sell_price": 480
    },
    "scale_mail": {
        "name": "비늘 갑옷",
        "description": "물고기 비늘 모양의 갑옷",
        "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_defense": 75, "magic_defense": 35, "hp": 100},
        "unique_effect": "water_resist:0.30|scales_deflection:0.15",
        "sell_price": 1300
    },
    "dragon_scale_mail": {
        "name": "드래곤 비늘 갑옷",
        "description": "용의 비늘로 만든 갑옷",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {"physical_defense": 110, "magic_defense": 90, "hp": 250, "fire_resist": 50},
        "unique_effect": "fire_immunity|physical_resist:0.30|dragon_aura",
        "sell_price": 16000
    },
    "samurai_armor": {
        "name": "사무라이 갑옷",
        "description": "동양의 전통 갑옷",
        "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"physical_defense": 70, "magic_defense": 40, "hp": 110, "strength": 10},
        "unique_effect": "counter_attack:0.25|honor_buff",
        "sell_price": 1700
    },

    # === More Heavy Armor ===
    "iron_plate": {
        "name": "철 판금 갑옷",
        "description": "두꺼운 철판 갑옷",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 65, "hp": 80, "speed": -3},
        "unique_effect": "physical_resist:0.10",
        "sell_price": 400
    },
    "steel_full_plate": {
        "name": "강철 전신 갑옷",
        "description": "전신을 덮는 강철 갑옷",
        "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_defense": 95, "hp": 150, "strength": 8, "speed": -5},
        "unique_effect": "physical_resist:0.25|immovable",
        "sell_price": 1500
    },
    "crusader_plate": {
        "name": "십자군 갑옷",
        "description": "성전사들이 입는 신성한 갑옷",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 110, "magic_defense": 60, "hp": 180, "spirit": 15},
        "unique_effect": "holy_protection|undead_resist:0.50|faith_shield",
        "sell_price": 3500
    },
    "obsidian_armor": {
        "name": "흑요석 갑옷",
        "description": "마력이 깃든 검은 갑옷",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 11,
        "base_stats": {"physical_defense": 130, "magic_defense": 110, "hp": 280, "dark_power": 50},
        "unique_effect": "magic_reflect:0.30|curse_immunity|dark_absorption",
        "sell_price": 19000
    },
    "titan_armor": {
        "name": "타이탄 갑옷",
        "description": "거인족의 갑옷",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 12,
        "base_stats": {"physical_defense": 150, "hp": 350, "strength": 35, "speed": -8},
        "unique_effect": "giant_strength|knockback_immunity|earthquake_step",
        "sell_price": 22000
    },

    # === Elemental Armor ===
    "ice_crystal_plate": {
        "name": "빙정 판금",
        "description": "절대영도의 얼음 갑옷",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"physical_defense": 85, "magic_defense": 95, "hp": 160, "ice_power": 50},
        "unique_effect": "ice_immunity|freeze_aura:0.20|slow_attackers:0.30",
        "sell_price": 4200
    },
    "thunder_plate": {
        "name": "뇌전 판금",
        "description": "번개의 힘이 깃든 갑옷",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"physical_defense": 90, "magic_defense": 80, "hp": 150, "lightning_power": 55},
        "unique_effect": "lightning_immunity|shock_counter:0.40|speed_boost:0.15",
        "sell_price": 4100
    },
    "earth_fortress_armor": {
        "name": "대지 요새 갑옷",
        "description": "대지의 견고함을 가진 갑옷",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 120, "magic_defense": 50, "hp": 220, "earth_power": 40},
        "unique_effect": "earth_wall|hp_regen:0.02|immovable_stance",
        "sell_price": 3600
    },
    "void_armor": {
        "name": "공허의 갑옷",
        "description": "무(無)의 영역에서 온 갑옷",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 11,
        "base_stats": {"physical_defense": 100, "magic_defense": 120, "hp": 200, "dark_power": 60, "void_power": 50},
        "unique_effect": "void_phase:0.25|damage_absorption:0.20|existence_denial",
        "sell_price": 20000
    },

    # === Special/Themed Armor ===
    "berserker_hide": {
        "name": "광전사의 가죽",
        "description": "광기를 담은 야수의 가죽",
        "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_defense": 60, "hp": 130, "strength": 15},
        "unique_effect": "low_hp_damage:0.50|pain_tolerance|rage_boost",
        "sell_price": 1450
    },
    "necromancer_robes": {
        "name": "강령술사 로브",
        "description": "죽음의 마법사가 입는 로브",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"magic_defense": 80, "mp": 140, "magic_attack": 40, "dark_power": 45},
        "unique_effect": "undead_command|lifesteal:0.15|death_magic:0.30",
        "sell_price": 3900
    },
    "assassin_leather": {
        "name": "암살자 가죽",
        "description": "어둠 속에서 움직이는 자의 갑옷",
        "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"physical_defense": 50, "evasion": 30, "speed": 18, "critical": 15},
        "unique_effect": "stealth|backstab_damage:0.50|silent_movement",
        "sell_price": 1800
    },
    "paladin_holy_armor": {
        "name": "성기사 신성 갑옷",
        "description": "신의 축복을 받은 갑옷",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {"physical_defense": 115, "magic_defense": 95, "hp": 240, "spirit": 30},
        "unique_effect": "holy_protection|auto_revive:once|heal_aura:0.10|faith_barrier",
        "sell_price": 17000
    },
    "ninja_garb": {
        "name": "닌자 의상",
        "description": "그림자처럼 움직이는 닌자복",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 45, "magic_defense": 35, "evasion": 35, "speed": 22},
        "unique_effect": "invisibility:3turns|dodge_chance:0.35|ninjutsu_power:0.25",
        "sell_price": 3400
    },
    "warlock_vestments": {
        "name": "흑마술사 예복",
        "description": "금지된 마법의 힘을 담은 옷",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"magic_defense": 70, "mp": 180, "magic_attack": 50, "dark_power": 40},
        "unique_effect": "curse_power:0.40|mp_drain:0.10|forbidden_magic:0.30",
        "sell_price": 4000
    },
    "monk_robes": {
        "name": "수도승 로브",
        "description": "정신과 육체를 단련한 자의 옷",
        "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"physical_defense": 55, "magic_defense": 70, "hp": 110, "spirit": 20},
        "unique_effect": "meditation:hp_mp_regen|counter_attack:0.30|inner_peace",
        "sell_price": 1650
    },

    # === More Steampunk Armor ===
    "gear_plated_vest": {
        "name": "기어 판금 조끼",
        "description": "회전하는 톱니바퀴로 보호하는 조끼",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 50, "hp": 70},
        "unique_effect": "gear_deflection:0.15|mechanical_boost",
        "sell_price": 520
    },
    "steam_powered_exosuit": {
        "name": "증기 파워 외골격",
        "description": "증기 기관으로 힘을 증폭시키는 슈트",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 9,
        "base_stats": {"physical_defense": 100, "strength": 25, "hp": 200, "speed": -6},
        "unique_effect": "strength_boost:0.30|carry_weight:100|steam_blast_counter",
        "sell_price": 5200
    },

    # === More Apocalypse Armor ===
    "scrap_metal_vest": {
        "name": "고철 조끼",
        "description": "고철을 용접해 만든 조끼",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"physical_defense": 30, "hp": 40},
        "unique_effect": "scrap_protection",
        "sell_price": 150
    },
    "gas_mask_armor": {
        "name": "방독면 갑옷",
        "description": "오염된 대기에서 생존하기 위한 갑옷",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 45, "hp": 60},
        "unique_effect": "poison_immunity|gas_resist:100",
        "sell_price": 600
    },
    "raider_leather": {
        "name": "약탈자 가죽",
        "description": "폐허를 떠도는 약탈자의 갑옷",
        "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"physical_defense": 65, "speed": 12, "critical": 10, "hp": 90},
        "unique_effect": "scavenger_bonus:0.30|intimidation",
        "sell_price": 1250
    },

    # === More Sci-Fi Armor ===
    "nano_weave_suit": {
        "name": "나노섬유 슈트",
        "description": "나노봇이 짜낸 방어복",
        "rarity": ItemRarity.RARE,
        "level_requirement": 6,
        "base_stats": {"physical_defense": 60, "magic_defense": 60, "hp": 100, "speed": 8},
        "unique_effect": "adaptive_armor:0.20|nano_repair:hp_regen:5",
        "sell_price": 1900
    },
    "quantum_plate": {
        "name": "양자 판금",
        "description": "양자 중첩 상태의 갑옷",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 12,
        "base_stats": {"physical_defense": 125, "magic_defense": 125, "hp": 260, "evasion": 20},
        "unique_effect": "quantum_evasion:0.30|superposition|reality_shift",
        "sell_price": 24000
    },
    "plasma_shield_armor": {
        "name": "플라즈마 실드 갑옷",
        "description": "플라즈마 방어막을 전개하는 갑옷",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 9,
        "base_stats": {"physical_defense": 70, "magic_defense": 100, "mp": 100},
        "unique_effect": "plasma_shield:250|energy_absorb|burn_counter:0.35",
        "sell_price": 5000
    },
    "cryogenic_suit": {
        "name": "극저온 슈트",
        "description": "극한의 추위를 견디는 슈트",
        "rarity": ItemRarity.RARE,
        "level_requirement": 7,
        "base_stats": {"physical_defense": 65, "magic_defense": 70, "hp": 120, "ice_power": 35},
        "unique_effect": "ice_immunity|freeze_aura:0.25|cold_storage",
        "sell_price": 2100
    },
}

ACCESSORY_TEMPLATES = {
    # 반지
    "health_ring": {
        "name": "생명의 반지",
        "description": "HP를 증가시키는 반지",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"hp": 30},
        "sell_price": 60
    },
    "mana_ring": {
        "name": "마나의 반지",
        "description": "MP를 증가시키는 반지",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"mp": 20},
        "sell_price": 60
    },
    "ring_of_strength": {
        "name": "힘의 반지",
        "description": "착용자의 힘을 증가시키는 반지",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 1,
        "base_stats": {"strength": 5, "physical_attack": 8},
        "sell_price": 100
    },
    "ring_of_wisdom": {
        "name": "지혜의 반지",
        "description": "착용자의 지혜를 증가시키는 반지",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 1,
        "base_stats": {"magic_attack": 8, "mp": 20},
        "sell_price": 100
    },
    "ring_of_agility": {
        "name": "민첩의 반지",
        "description": "착용자의 행동 속도와 회피를 증가",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"speed": 8, "evasion": 10},
        "sell_price": 120
    },
    "ring_of_protection": {
        "name": "수호의 반지",
        "description": "모든 방어력을 증가시키는 반지",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"physical_defense": 15, "magic_defense": 15, "hp": 50},
        "sell_price": 450
    },
    "phoenix_ring": {
        "name": "불사조의 반지",
        "description": "부활의 힘이 깃든 반지",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"hp": 120, "magic_defense": 20},
        "sell_price": 1800
    },
    "ring_of_gods": {
        "name": "신의 반지",
        "description": "모든 능력치를 증가시키는 반지",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {
            "physical_attack": 20, "magic_attack": 20,
            "physical_defense": 15, "magic_defense": 15,
            "hp": 100, "mp": 50, "speed": 10
        },
        "sell_price": 5000
    },

    # 목걸이/부적
    "amulet_of_life": {
        "name": "생명의 부적",
        "description": "생명력을 대폭 증가시키는 부적",
        "rarity": ItemRarity.RARE,
        "level_requirement": 2,
        "base_stats": {"hp": 100, "physical_defense": 10},
        "sell_price": 400
    },
    "amulet_of_mana": {
        "name": "마나의 부적",
        "description": "마력을 대폭 증가시키는 부적",
        "rarity": ItemRarity.RARE,
        "level_requirement": 2,
        "base_stats": {"mp": 80, "magic_defense": 10},
        "sell_price": 400
    },
    "dragon_pendant": {
        "name": "용의 펜던트",
        "description": "드래곤의 힘이 깃든 펜던트",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 4,
        "base_stats": {"physical_attack": 18, "magic_attack": 18, "hp": 70},
        "sell_price": 1500
    },
    "phoenix_pendant": {
        "name": "불사조 펜던트",
        "description": "부활의 불꽃이 담긴 펜던트",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"hp": 150, "mp": 60, "magic_defense": 25},
        "sell_price": 1600
    },
    "lucky_charm": {
        "name": "행운의 부적",
        "description": "행운을 가져다주는 신비한 부적",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"luck": 10, "accuracy": 10, "evasion": 10, "critical_rate": 15},
        "sell_price": 1500
    },

    # 귀걸이
    "ruby_earring": {
        "name": "루비 귀걸이",
        "description": "힘을 증가시키는 귀걸이",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"strength": 7, "physical_attack": 10},
        "sell_price": 180
    },
    "sapphire_earring": {
        "name": "사파이어 귀걸이",
        "description": "지성을 증가시키는 귀걸이",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"magic_attack": 12, "mp": 25},
        "sell_price": 180
    },
    "emerald_earring": {
        "name": "에메랄드 귀걸이",
        "description": "회복력을 증가시키는 귀걸이",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"hp": 60, "magic_defense": 8},
        "sell_price": 170
    },

    # 벨트
    "leather_belt": {
        "name": "가죽 벨트",
        "description": "기본적인 가죽 벨트",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"hp": 20, "physical_defense": 5},
        "sell_price": 50
    },
    "warriors_belt": {
        "name": "전사의 벨트",
        "description": "전사를 위한 튼튼한 벨트",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"strength": 8, "hp": 50, "physical_defense": 10},
        "sell_price": 280
    },
    "mages_sash": {
        "name": "마법사의 띠",
        "description": "마력을 강화하는 띠",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"magic_attack": 12, "mp": 40, "magic_defense": 10},
        "sell_price": 300
    },

    # === 시야 시스템 연동 장신구 ===
    "eagle_eye_amulet": {
        "name": "매의 눈 목걸이",
        "description": "시야 +1. 명중률 +15",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"accuracy": 15, "critical": 5},
        "unique_effect": "vision:1",
        "sell_price": 200
    },
    "far_sight_lens": {
        "name": "원시의 렌즈",
        "description": "시야 +1. 적 탐지",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"accuracy": 20, "luck": 8},
        "unique_effect": "vision:1|detect_enemy",
        "sell_price": 600
    },
    "owls_pendant": {
        "name": "부엉이의 펜던트",
        "description": "시야 +2. 야간 시야 (어둠 무시)",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"accuracy": 30, "spirit": 12, "luck": 10},
        "unique_effect": "vision:2|night_vision",
        "sell_price": 1500
    },
    "all_seeing_eye": {
        "name": "전지의 눈",
        "description": "시야 +2. 투시 (벽 너머 보기). 숨겨진 적 탐지",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 10,
        "base_stats": {"accuracy": 50, "luck": 20, "all_stats": 8},
        "unique_effect": "vision:2|true_sight|detect_hidden",
        "sell_price": 5000
    },
    "explorers_compass": {
        "name": "탐험가의 나침반",
        "description": "시야 +1. 지도에 보물 위치 표시",
        "rarity": ItemRarity.RARE,
        "level_requirement": 2,
        "base_stats": {"luck": 15},
        "unique_effect": "vision:1|treasure_finder",
        "sell_price": 450
    },

    # === 상처 관련 장신구 ===
    "wound_ward_ring": {
        "name": "상처 보호 반지",
        "description": "받는 상처 40% 감소",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"hp": 60, "spirit": 8},
        "unique_effect": "wound_reduction:0.40",
        "sell_price": 550
    },
    "scar_healer_amulet": {
        "name": "흉터 치유 목걸이",
        "unique_effect": "wound_immunity",
        "sell_price": 1800
    },

    # === BRV 관련 장신구 ===
    "brave_ring": {
        "name": "브레이브 링",
        "description": "BRV 공격력 +20%",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"strength": 5, "magic_attack": 5},
        "unique_effect": "brv_bonus:0.20",
        "sell_price": 250
    },
    "break_master_badge": {
        "name": "브레이크 마스터 배지",
        "description": "BREAK 데미지 +40%. BRV 흡수 +15%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"strength": 10, "luck": 12},
        "unique_effect": "brv_break_bonus:0.40|brv_steal:0.15",
        "sell_price": 800
    },
    "shield_earring": {
        "name": "실드 귀걸이",
        "description": "BRV 데미지 40% 감소. BREAK 1회 방지",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"defense": 12, "spirit": 10},
        "unique_effect": "brv_shield:0.40|brv_protect",
        "sell_price": 700
    },
    "brave_surge_belt": {
        "name": "브레이브 서지 벨트",
        "description": "턴당 BRV +15. BRV 공격력 +15%",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"strength": 12, "speed": 8},
        "unique_effect": "brv_regen:15|brv_bonus:0.15",
        "sell_price": 1600
    },

    # === 생명력 흡수 장신구 ===
    "vampire_fang": {
        "name": "흡혈귀의 송곳니",
        "description": "생명력 흡수 10%. HP 재생 +2%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"hp": 70, "strength": 8},
        "unique_effect": "lifesteal:0.10|hp_regen:0.02",
        "sell_price": 600
    },
    "blood_ruby": {
        "name": "피의 루비",
        "description": "생명력 흡수 20%. 최대 HP +50",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"hp": 150, "strength": 15},
        "unique_effect": "lifesteal:0.20",
        "sell_price": 1900
    },
    "leech_ring": {
        "name": "흡혈 반지",
        "description": "생명력 흡수 8%. MP 흡수 8%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"hp": 80, "mp": 40},
        "unique_effect": "lifesteal:0.08|mp_steal:0.08",
        "sell_price": 900
    },

    # === 크리티컬 장신구 ===
    "lucky_coin": {
        "name": "행운의 동전",
        "description": "크리티컬 확률 +15%. 행운 +20",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"luck": 20, "critical": 10},
        "unique_effect": "critical_chance:0.15",
        "sell_price": 300
    },
    "executioners_token": {
        "name": "처형인의 징표",
        "description": "크리티컬 데미지 +60%. 적 HP 30% 이하 시 추가 +30%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"critical": 15, "luck": 15, "strength": 10},
        "unique_effect": "critical_damage:0.60|execute:0.30",
        "sell_price": 1100
    },
    "precision_monocle": {
        "name": "정밀 단안경",
        "description": "크리티컬 확률 +25%. 명중률 +30",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"critical": 20, "accuracy": 30, "luck": 18},
        "unique_effect": "critical_chance:0.25|never_miss_crit",  # 크리티컬은 절대 빗나가지 않음
        "sell_price": 2100
    },

    # === 회피/속도 장신구 ===
    "rabbit_foot": {
        "name": "토끼발",
        "description": "회피율 +15%. 속도 +8",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"evasion": 15, "speed": 8, "luck": 10},
        "unique_effect": "dodge_chance:0.15",
        "sell_price": 250
    },
    "phantom_boots": {
        "name": "유령 장화",
        "description": "회피율 +30%. 공격 회피 시 반격",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"evasion": 30, "speed": 12, "luck": 12},
        "unique_effect": "dodge_chance:0.30|dodge_counter",
        "sell_price": 950
    },
    "wind_walker_anklet": {
        "name": "바람걸이 발찌",
        "description": "행동 속도 +20. 선제공격과 BRV 흡수 보너스",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"speed": 20, "evasion": 15},
        "unique_effect": "first_strike|brv_steal:0.40",
        "sell_price": 750
    },
    "time_stop_watch": {
        "name": "시간 정지 회중시계",
        "description": "행동 속도를 크게 향상시키고 가끔 2회 행동하며 항상 선제공격한다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"speed": 25, "all_stats": 8},
        "unique_effect": "double_turn:0.10|first_strike",  # 10% 확률로 2회 행동, 선제공격
        "sell_price": 2400
    },

    # === 방어 장신구 ===
    "iron_skin_ring": {
        "name": "강철 피부 반지",
        "description": "모든 데미지 10 감소",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"defense": 15, "hp": 80},
        "unique_effect": "flat_damage_reduction:10",
        "sell_price": 800
    },
    "titan_heart": {
        "name": "타이탄의 심장",
        "description": "최대 HP +200. HP 재생 +3%",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"hp": 250, "defense": 20},
        "unique_effect": "hp_regen:0.03|overheal_shield",  # 과다 회복 → 실드 전환
        "sell_price": 2600
    },
    "barrier_crystal": {
        "name": "배리어 크리스탈",
        "description": "턴 시작 시 최대 HP 20% 보호막 생성",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"hp": 120, "magic_defense": 25, "spirit": 15},
        "unique_effect": "barrier_on_turn:0.20",
        "sell_price": 1900
    },

    # === MP/마법 장신구 ===
    "arcane_focus": {
        "name": "비전 초점",
        "description": "MP 재생 +6. MP 소비 -15%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"mp": 60, "magic_attack": 18},
        "unique_effect": "mp_regen:6|mp_cost_reduction:0.15",
        "sell_price": 650
    },
    "sorcerers_pendant": {
        "name": "마법사의 펜던트",
        "description": "MP를 지속적으로 재생시키고 마법 위력을 향상시키며 턴 시작 시 보호막을 생성한다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"mp": 100, "magic_attack": 30, "spirit": 15},
        "unique_effect": "mp_regen:8|spell_power:0.15|barrier_on_turn:0.15",  # 턴 시작 시 최대 HP 15% 보호막
        "sell_price": 2200
    },
    "infinite_mana_orb": {
        "name": "무한 마나 오브",
        "description": "MP 소비 -50%. 마법 공격력 +40",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 11,
        "base_stats": {"mp": 200, "magic_attack": 60, "spirit": 25},
        "unique_effect": "mp_cost_reduction:0.50|spell_power:0.30|mana_overflow",
        "sell_price": 8000
    },

    # === 상태 이상 관련 장신구 ===
    "antidote_charm": {
        "name": "해독 부적",
        "description": "독, 질병 면역",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 2,
        "base_stats": {"hp": 40, "spirit": 5},
        "unique_effect": "status_immunity:poison,disease",
        "sell_price": 150
    },
    "freedom_amulet": {
        "name": "자유의 목걸이",
        "description": "스턴, 수면, 혼란, 공포 면역",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"spirit": 18, "hp": 90},
        "unique_effect": "cc_immunity:stun,sleep,confusion,fear",
        "sell_price": 1200
    },
    "purity_ring": {
        "name": "순수의 반지",
        "description": "모든 상태 이상 면역. 최대 HP -50",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"spirit": 25, "hp": -50, "magic_defense": 30},
        "unique_effect": "status_immunity:all",
        "sell_price": 2800
    },
    "cleansing_bell": {
        "name": "정화의 종",
        "description": "턴 시작 시 디버프 1개 제거",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"spirit": 15, "mp": 50},
        "unique_effect": "cleanse_on_turn:1|debuff_resist:0.30",
        "sell_price": 850
    },

    # === 골드/경험치/드롭 장신구 ===
    "golden_scarab": {
        "name": "황금 스카라베",
        "description": "골드 획득 +50%",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"luck": 12},
        "unique_effect": "gold_find:0.50",
        "sell_price": 300
    },
    "merchants_signet": {
        "name": "상인의 인장",
        "description": "골드 획득 +100%. 아이템 가격 -10%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"luck": 18},
        "unique_effect": "gold_find:1.00|shop_discount:0.10",
        "sell_price": 700
    },
    "dragons_hoard_ring": {
        "name": "용의 보물 반지",
        "description": "골드 획득 +150%. 레어 아이템 드롭률 +30%",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 5,
        "base_stats": {"luck": 25, "all_stats": 5},
        "unique_effect": "gold_find:1.50|item_rarity:0.30",
        "sell_price": 2500
    },
    "scholars_tome": {
        "name": "학자의 서",
        "description": "경험치 +30%",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 1,
        "base_stats": {"spirit": 8},
        "unique_effect": "exp_bonus:0.30",
        "sell_price": 250
    },
    "mentor_medallion": {
        "name": "스승의 메달",
        "description": "경험치 +50%. 스킬 숙련도 +25%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"spirit": 15, "all_stats": 3},
        "unique_effect": "exp_bonus:0.50|skill_mastery:0.25",
        "sell_price": 800
    },
    "item_magnet": {
        "name": "아이템 자석",
        "description": "아이템 드롭률 +40%. 행운 +20",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"luck": 25},
        "unique_effect": "item_find:0.40|auto_pickup",
        "sell_price": 900
    },

    # === 특수 기믹 장신구 ===
    "phoenix_down_pendant": {
        "name": "불사조 깃털 펜던트",
        "description": "사망 시 HP 100% 부활 (1회)",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 10,
        "base_stats": {"hp": 150, "mp": 80, "all_stats": 8},
        "unique_effect": "phoenix_rebirth:full",
        "sell_price": 3500
    },
    "second_chance_coin": {
        "name": "두 번째 기회 동전",
        "description": "사망 시 50% HP 부활 (2회)",
        "rarity": ItemRarity.RARE,
        "level_requirement": 7,
        "base_stats": {"hp": 100, "luck": 15},
        "unique_effect": "phoenix_rebirth:half|charges:2",
        "sell_price": 1600
    },
    "rage_gem": {
        "name": "분노의 보석",
        "description": "HP 낮을수록 공격력 증가 (최대 +80%)",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"strength": 15, "hp": 80},
        "unique_effect": "berserk|low_hp_bonus:0.80",
        "sell_price": 950
    },
    "glass_cannon_gem": {
        "name": "유리 대포 보석",
        "description": "공격력 +50%. 방어력 -30%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"strength": 20, "magic_attack": 20},
        "unique_effect": "glass_cannon:damage:0.50|defense:-0.30",
        "sell_price": 1100
    },
    "balanced_core": {
        "name": "균형의 핵",
        "description": "모든 스탯 +10. 모든 능력 균형 잡힘",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"all_stats": 12},
        "unique_effect": "balanced_stats:0.15",  # 모든 스탯에 15% 보너스
        "sell_price": 2700
    },
    "combo_chain_badge": {
        "name": "콤보 체인 배지",
        "description": "연속 공격 시 데미지 증가 (콤보당 +20%, 최대 5회)",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"speed": 15, "strength": 12, "critical": 10},
        "unique_effect": "combo_bonus:0.20|max_combo:5",
        "sell_price": 2000
    },
    "overload_core": {
        "name": "과부하 코어",
        "description": "모든 자원 소비 2배. 모든 효과 2.5배",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 9,
        "base_stats": {"all_stats": 15},
        "unique_effect": "overload:cost:2.0|effect:2.5",
        "sell_price": 2900
    },

    # === 기믹 강화 장신구 ===
    "gimmick_booster": {
        "name": "기믹 부스터",
        "description": "기믹 효율 +30%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"all_stats": 5},
        "unique_effect": "gimmick_boost:0.30",
        "sell_price": 750
    },
    "max_stack_amplifier": {
        "name": "최대 스택 증폭기",
        "description": "최대 기믹 스택 +2",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 7,
        "base_stats": {"all_stats": 8},
        "unique_effect": "max_gimmick_increase:2",
        "sell_price": 1800
    },
    "resource_saver": {
        "name": "자원 절약가",
        "description": "기믹 소모 -30%. MP 소비 -20%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 4,
        "base_stats": {"mp": 60, "spirit": 12},
        "unique_effect": "gimmick_cost_reduction:0.30|mp_cost_reduction:0.20",
        "sell_price": 1000
    },

    # === 레전더리 장신구 ===
    "ring_of_gods": {
        "name": "신들의 반지",
        "description": "모든 스탯 +25. 모든 효과 +20%",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 9,
        "base_stats": {"all_stats": 30},
        "unique_effect": "omnipotent:0.20",  # 모든 효과 20% 증폭
        "sell_price": 15000
    },
    "infinity_stone": {
        "name": "무한석",
        "description": "자원 무한. MP 소비 없음. HP 재생 +5%",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 13,
        "base_stats": {"hp": 200, "mp": 300, "all_stats": 20},
        "unique_effect": "infinite_resources|hp_regen:0.05|mp_cost:0",
        "sell_price": 20000
    },
    "omniscient_eye": {
        "name": "전지의 눈동자",
        "description": "시야 +2. 모든 것을 볼 수 있음. 크리티컬 +50%",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 7,
        "base_stats": {"critical": 50, "accuracy": 100, "luck": 30},
        "unique_effect": "vision:2|true_sight|omniscient|critical_chance:0.50",
        "sell_price": 12000
    },

    # === Steampunk Accessories ===
    "pocket_watch_of_time": {
        "name": "시간의 회중시계",
        "description": "시간의 흐름을 미세하게 조작한다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 6,
        "base_stats": {"speed": 20, "accuracy": 10},
        "unique_effect": "cooldown_reduction:0.20|haste_start",
        "sell_price": 2000
    },
    "goggles_of_insight": {
        "name": "통찰의 고글",
        "description": "숨겨진 장치나 약점을 찾아낸다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 3,
        "base_stats": {"accuracy": 25, "luck": 10},
        "unique_effect": "detect_hidden|critical_chance:0.10",
        "sell_price": 750
    },

    # === Apocalypse Accessories ===
    "geiger_counter": {
        "name": "가이거 계수기",
        "description": "위험 지역을 탐지한다",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 2,
        "base_stats": {"luck": 15},
        "unique_effect": "detect_radiation|loot_bonus:0.10",
        "sell_price": 300
    },
    "survival_kit": {
        "name": "생존 키트",
        "description": "응급 처치 도구와 생존 물품",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 1,
        "base_stats": {"hp": 30},
        "unique_effect": "hp_regen:0.02|inventory_space:5",
        "sell_price": 100
    },

    # === Sci-Fi/Future Accessories ===
    "holographic_visor": {
        "name": "홀로그램 바이저",
        "description": "전술 정보를 시각화하여 보여준다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 5,
        "base_stats": {"accuracy": 30, "critical": 15},
        "unique_effect": "analyze_enemy|critical_damage:0.20",
        "sell_price": 1200
    },
    "gravity_boots": {
        "name": "중력 부츠",
        "description": "중력을 제어하여 공중을 걷거나 충격을 흡수한다",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 8,
        "base_stats": {"speed": 15, "evasion": 20},
        "unique_effect": "immune_ground_effects|fall_damage_immune",
        "sell_price": 2800
    },
}

# 유니크 아이템
UNIQUE_ITEMS = {
    "excalibur": {
        "name": "엑스칼리버",
        "description": "전설의 성검",
        "rarity": ItemRarity.UNIQUE,
        "level_requirement": 13,
        "base_stats": {"physical_attack": 150, "magic_attack": 50, "hp": 100, "mp": 50},
        "unique_effect": "HP 50% 이상 시 모든 공격력 +30%",
        "sell_price": 99999
    },
    "mjolnir": {
        "name": "묠니르",
        "description": "천둥의 망치",
        "rarity": ItemRarity.UNIQUE,
        "level_requirement": 9,
        "base_stats": {"physical_attack": 140, "strength": 20},
        "unique_effect": "공격 시 30% 확률로 번개 추가 데미지",
        "sell_price": 88888
    },
    "infinity_gauntlet": {
        "name": "무한의 건틀릿",
        "description": "모든 능력을 강화하는 전설의 장갑",
        "rarity": ItemRarity.UNIQUE,
        "level_requirement": 15,
        "base_stats": {
            "physical_attack": 50, "magic_attack": 50,
            "physical_defense": 30, "magic_defense": 30,
            "hp": 200, "mp": 100
        },
        "unique_effect": "모든 스탯 +10%",
        "sell_price": 150000
    },
    "phoenix_feather": {
        "name": "불사조의 깃털",
        "description": "부활의 힘을 가진 깃털",
        "rarity": ItemRarity.UNIQUE,
        "level_requirement": 6,
        "base_stats": {"hp": 150, "magic_defense": 40},
        "unique_effect": "전투 중 1회 사망 시 HP 100%로 부활",
        "sell_price": 50000
    },
}

# 소비 아이템
CONSUMABLE_TEMPLATES = {
    # HP 회복
    "health_potion": {
        "name": "체력 물약",
        "description": "HP 50 회복",
        "rarity": ItemRarity.COMMON,
        "effect_type": "heal_hp",
        "effect_value": 50,
        "sell_price": 20
    },
    "mega_health_potion": {
        "name": "대형 체력 물약",
        "description": "HP 200 회복",
        "rarity": ItemRarity.UNCOMMON,
        "effect_type": "heal_hp",
        "effect_value": 200,
        "sell_price": 80
    },
    "super_health_potion": {
        "name": "최상급 체력 물약",
        "description": "HP 500 회복",
        "rarity": ItemRarity.RARE,
        "effect_type": "heal_hp",
        "effect_value": 500,
        "sell_price": 200
    },

    # MP 회복
    "mana_potion": {
        "name": "마나 물약",
        "description": "MP 30 회복",
        "rarity": ItemRarity.COMMON,
        "effect_type": "heal_mp",
        "effect_value": 30,
        "sell_price": 25
    },
    "mega_mana_potion": {
        "name": "대형 마나 물약",
        "description": "MP 80 회복",
        "rarity": ItemRarity.UNCOMMON,
        "effect_type": "heal_mp",
        "effect_value": 80,
        "sell_price": 90
    },
    "mana_crystal": {
        "name": "마나 크리스탈",
        "description": "MP 100 회복",
        "rarity": ItemRarity.UNCOMMON,
        "effect_type": "heal_mp",
        "effect_value": 100,
        "sell_price": 120
    },
    "super_mana_potion": {
        "name": "최상급 마나 물약",
        "description": "MP 150 회복",
        "rarity": ItemRarity.RARE,
        "effect_type": "heal_mp",
        "effect_value": 150,
        "sell_price": 180
    },

    # 완전 회복
    "elixir": {
        "name": "엘릭서",
        "description": "HP와 MP를 완전히 회복",
        "rarity": ItemRarity.RARE,
        "effect_type": "full_restore",
        "effect_value": 0,
        "sell_price": 500
    },

    # 특수 아이템
    "phoenix_down": {
        "name": "불사조의 깃털",
        "description": "전투 불능 상태를 회복 (HP 50%)",
        "rarity": ItemRarity.RARE,
        "effect_type": "revive",
        "effect_value": 0.5,
        "sell_price": 300
    },
    "town_portal": {
        "name": "마을 귀환 두루마리",
        "description": "던전에서 즉시 탈출 (보상 유지)",
        "rarity": ItemRarity.UNCOMMON,
        "effect_type": "escape",
        "effect_value": 0,
        "sell_price": 100
    },
    "dungeon_key": {
        "name": "던전 열쇠",
        "description": "잠긴 문 1개를 열 수 있음",
        "rarity": ItemRarity.COMMON,
        "effect_type": "key",
        "effect_value": 1,
        "sell_price": 75
    },

    # 버프 아이템
    "strength_tonic": {
        "name": "힘의 강장제",
        "description": "3턴 동안 물리 공격력 +20%",
        "rarity": ItemRarity.UNCOMMON,
        "effect_type": "buff_attack",
        "effect_value": 0.2,
        "sell_price": 150
    },
    "magic_tonic": {
        "name": "마법의 강장제",
        "description": "3턴 동안 마법 공격력 +20%",
        "rarity": ItemRarity.UNCOMMON,
        "effect_type": "buff_magic",
        "effect_value": 0.2,
        "sell_price": 150
    },
    "speed_tonic": {
        "name": "민첩의 강장제",
        "description": "3턴 동안 속도 +30%",
        "rarity": ItemRarity.UNCOMMON,
        "effect_type": "buff_speed",
        "effect_value": 0.3,
        "sell_price": 180
    },
    "defense_tonic": {
        "name": "방어의 강장제",
        "description": "3턴 동안 방어력 +25%",
        "rarity": ItemRarity.UNCOMMON,
        "effect_type": "buff_defense",
        "effect_value": 0.25,
        "sell_price": 160
    },

    # 공격 아이템
    "fire_bomb": {
        "name": "화염 폭탄",
        "description": "적 전체에 화염 데미지",
        "rarity": ItemRarity.UNCOMMON,
        "effect_type": "aoe_fire",
        "effect_value": 150,
        "sell_price": 120
    },
    "ice_bomb": {
        "name": "냉기 폭탄",
        "description": "적 전체에 냉기 데미지 (20% 확률 빙결)",
        "rarity": ItemRarity.UNCOMMON,
        "effect_type": "aoe_ice",
        "effect_value": 130,
        "sell_price": 140
    },
    "lightning_bolt": {
        "name": "번개 구슬",
        "description": "적 1명에게 강력한 번개 데미지",
        "rarity": ItemRarity.RARE,
        "effect_type": "single_lightning",
        "effect_value": 300,
        "sell_price": 200
    },

    # === 상처 치료 아이템 ===
    "wound_salve": {
        "name": "상처 연고",
        "description": "상처 30 회복",
        "rarity": ItemRarity.UNCOMMON,
        "effect_type": "heal_wound",
        "effect_value": 30,
        "sell_price": 60
    },
    "scar_remover": {
        "name": "흉터 제거제",
        "description": "상처 100 회복",
        "rarity": ItemRarity.RARE,
        "effect_type": "heal_wound",
        "effect_value": 100,
        "sell_price": 180
    },
    "perfect_heal": {
        "name": "완전 치유",
        "description": "모든 상처 제거 + HP 완전 회복",
        "rarity": ItemRarity.EPIC,
        "effect_type": "heal_wound_full",
        "effect_value": 0,
        "sell_price": 600
    },
    "regeneration_potion": {
        "name": "재생 물약",
        "description": "3턴 동안 턴당 상처 15 회복",
        "rarity": ItemRarity.RARE,
        "effect_type": "wound_regen_buff",
        "effect_value": 15,
        "sell_price": 250
    },

    # === BRV 관련 아이템 ===
    "brave_shard": {
        "name": "브레이브 파편",
        "description": "BRV 100 즉시 획득",
        "rarity": ItemRarity.UNCOMMON,
        "effect_type": "brv_restore",
        "effect_value": 100,
        "sell_price": 50
    },
    "brave_crystal": {
        "name": "브레이브 크리스탈",
        "description": "BRV 300 즉시 획득",
        "rarity": ItemRarity.RARE,
        "effect_type": "brv_restore",
        "effect_value": 300,
        "sell_price": 150
    },
    "break_guard": {
        "name": "브레이크 가드",
        "description": "3턴 동안 BREAK 무효 (1회)",
        "rarity": ItemRarity.RARE,
        "effect_type": "brv_protect_buff",
        "effect_value": 3,
        "sell_price": 200
    },
    "brave_boost": {
        "name": "브레이브 부스트",
        "description": "5턴 동안 BRV 공격력 +50%",
        "rarity": ItemRarity.EPIC,
        "effect_type": "brv_bonus_buff",
        "effect_value": 0.50,
        "sell_price": 400
    },

    # === 복합 회복 아이템 ===
    "panacea": {
        "name": "만병통치약",
        "description": "HP, MP 완전 회복 + 상처 50 회복",
        "rarity": ItemRarity.EPIC,
        "effect_type": "panacea",
        "effect_value": 50,
        "sell_price": 800
    },
    "megalixir": {
        "name": "메가엘릭서",
        "description": "파티 전체 HP/MP 완전 회복",
        "rarity": ItemRarity.LEGENDARY,
        "effect_type": "party_full_restore",
        "effect_value": 0,
        "sell_price": 2000
    },
    "heroes_drink": {
        "name": "영웅의 음료",
        "description": "HP 200 회복 + 5턴 동안 모든 스탯 +20%",
        "rarity": ItemRarity.EPIC,
        "effect_type": "hero_buff",
        "effect_value": 200,
        "sell_price": 500
    },

    # === 특수 상태 아이템 ===
    "invincibility_potion": {
        "name": "무적 물약",
        "description": "2턴 동안 무적",
        "rarity": ItemRarity.LEGENDARY,
        "effect_type": "invincible",
        "effect_value": 2,
        "sell_price": 3000
    },
    "haste_potion": {
        "name": "가속 물약",
        "description": "5턴 동안 속도 +50%",
        "rarity": ItemRarity.RARE,
        "effect_type": "haste",
        "effect_value": 5,
        "sell_price": 300
    },
    "berserk_potion": {
        "name": "광폭화 물약",
        "description": "5턴 동안 공격력 +80%, 방어력 -30%",
        "rarity": ItemRarity.RARE,
        "effect_type": "berserk",
        "effect_value": 5,
        "sell_price": 280
    },
    
    # === 공격적 아이템 (전투용) ===
    "poison_bomb": {
        "name": "독 폭탄",
        "description": "적 전체에 독 데미지 + 독 상태이상",
        "rarity": ItemRarity.UNCOMMON,
        "effect_type": "poison_bomb",
        "effect_value": 100,
        "sell_price": 150
    },
    "thunder_grenade": {
        "name": "천둥 수류탄",
        "description": "적 전체에 번개 데미지 + 감전",
        "rarity": ItemRarity.RARE,
        "effect_type": "thunder_grenade",
        "effect_value": 200,
        "sell_price": 250
    },
    "acid_flask": {
        "name": "산성 플라스크",
        "description": "적 1명에게 산성 데미지 + 방어력 감소",
        "rarity": ItemRarity.UNCOMMON,
        "effect_type": "acid_flask",
        "effect_value": 180,
        "sell_price": 160
    },
    "debuff_attack": {
        "name": "공격 약화 폭탄",
        "description": "적 전체 공격력 -30% (3턴)",
        "rarity": ItemRarity.RARE,
        "effect_type": "debuff_attack",
        "effect_value": 0.3,
        "sell_price": 200
    },
    "debuff_defense": {
        "name": "방어 약화 폭탄",
        "description": "적 전체 방어력 -40% (3턴)",
        "rarity": ItemRarity.RARE,
        "effect_type": "debuff_defense",
        "effect_value": 0.4,
        "sell_price": 220
    },
    "debuff_speed": {
        "name": "속도 약화 폭탄",
        "description": "적 전체 속도 -35% (3턴)",
        "rarity": ItemRarity.RARE,
        "effect_type": "debuff_speed",
        "effect_value": 0.35,
        "sell_price": 210
    },
    "break_brv": {
        "name": "BRV 파괴 폭탄",
        "description": "적 전체 BRV -200",
        "rarity": ItemRarity.EPIC,
        "effect_type": "break_brv",
        "effect_value": 200,
        "sell_price": 350
    },
    "smoke_bomb": {
        "name": "연막탄",
        "description": "적 전체 명중률 -50% (2턴)",
        "rarity": ItemRarity.UNCOMMON,
        "effect_type": "smoke_bomb",
        "effect_value": 0.5,
        "sell_price": 120
    },
    
    # === 수비적 아이템 (전투용) ===
    "barrier_crystal": {
        "name": "방어 크리스탈",
        "description": "3턴 동안 모든 피해 -30%",
        "rarity": ItemRarity.RARE,
        "effect_type": "barrier_crystal",
        "effect_value": 0.3,
        "sell_price": 280
    },
    "haste_crystal": {
        "name": "가속 크리스탈",
        "description": "3턴 동안 속도 +40%",
        "rarity": ItemRarity.RARE,
        "effect_type": "haste_crystal",
        "effect_value": 0.4,
        "sell_price": 300
    },
    "power_tonic": {
        "name": "힘의 비약",
        "description": "3턴 동안 물리/마법 공격력 +35%",
        "rarity": ItemRarity.EPIC,
        "effect_type": "power_tonic",
        "effect_value": 0.35,
        "sell_price": 400
    },
    "defense_elixir": {
        "name": "방어 엘릭서",
        "description": "3턴 동안 물리/마법 방어력 +40%",
        "rarity": ItemRarity.EPIC,
        "effect_type": "defense_elixir",
        "effect_value": 0.4,
        "sell_price": 380
    },
    "regen_crystal": {
        "name": "재생 크리스탈",
        "description": "5턴 동안 턴당 HP 50 회복",
        "rarity": ItemRarity.RARE,
        "effect_type": "regen_crystal",
        "effect_value": 50,
        "sell_price": 320
    },
    "mp_regen_crystal": {
        "name": "MP 재생 크리스탈",
        "description": "5턴 동안 턴당 MP 20 회복",
        "rarity": ItemRarity.RARE,
        "effect_type": "mp_regen_crystal",
        "effect_value": 20,
        "sell_price": 300
    },
    "status_cleanse": {
        "name": "정화 물약",
        "description": "모든 상태이상 제거",
        "rarity": ItemRarity.UNCOMMON,
        "effect_type": "status_cleanse",
        "effect_value": 0,
        "sell_price": 180
    },
    "revive_crystal": {
        "name": "부활 크리스탈",
        "description": "전투 불능 상태를 회복 (HP 30%)",
        "rarity": ItemRarity.EPIC,
        "effect_type": "revive_crystal",
        "effect_value": 0.3,
        "sell_price": 500
    },
}

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
    "piercing": ItemAffix("piercing", "관통하는", "armor_penetration", 0.15, True),
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

        # 랜덤 접사 선택 및 수치 조정
        available_affixes = list(AFFIX_POOL.values())
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
            
            # 퍼센트 옵션은 최대치 제한 (밸런스)
            if base_affix.is_percentage:
                new_value = min(new_value, 0.50)  # 최대 50%
            
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
    def create_random_drop(level: int, boss_drop: bool = False) -> Item:
        """레벨에 맞는 랜덤 드롭 생성"""
        # 등급 확률
        if boss_drop:
            # 보스 드롭: 높은 등급 확률 증가
            rarity_chances = {
                ItemRarity.COMMON: 0.10,
                ItemRarity.UNCOMMON: 0.25,
                ItemRarity.RARE: 0.35,
                ItemRarity.EPIC: 0.20,
                ItemRarity.LEGENDARY: 0.10
            }
        else:
            # 일반 드롭
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
        suitable_templates = [
            (tid, tpl) for tid, tpl in all_templates.items()
            if tpl["rarity"] == chosen_rarity and tpl["level_requirement"] <= level
        ]

        if not suitable_templates:
            # 적합한 템플릿 없으면 소비 아이템 (HP/MP 포션 또는 전투용 아이템 랜덤)
            # 전투용 아이템도 포함 (30% 확률)
            if random.random() < 0.3:
                combat_consumables = [
                    "fire_bomb", "ice_bomb", "poison_bomb", "thunder_grenade",
                    "barrier_crystal", "haste_crystal", "power_tonic", "defense_elixir",
                    "regen_crystal", "mp_regen_crystal", "status_cleanse"
                ]
                chosen_consumable = random.choice(combat_consumables)
            else:
                consumable_choices = ["health_potion", "mana_potion"]
                chosen_consumable = random.choice(consumable_choices)
            return ItemGenerator.create_consumable(chosen_consumable)

        template_id, template = random.choice(suitable_templates)

        # 타입에 따라 생성
        if template_id in WEAPON_TEMPLATES:
            return ItemGenerator.create_weapon(template_id)
        elif template_id in ARMOR_TEMPLATES:
            return ItemGenerator.create_armor(template_id)
        else:
            return ItemGenerator.create_accessory(template_id)
