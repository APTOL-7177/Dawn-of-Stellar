"""
아이템 시스템

등급, 레벨 제한, 랜덤 부가 능력치
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
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
        if self.is_percentage:
            return f"{self.name}: {self.stat} +{int(self.value * 100)}%"
        else:
            return f"{self.name}: {self.stat} +{int(self.value)}"


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

    def get_total_stats(self) -> Dict[str, float]:
        """기본 스탯 + 접사 스탯 합계"""
        total = self.base_stats.copy()

        for affix in self.affixes:
            if affix.stat in total:
                if affix.is_percentage:
                    total[affix.stat] *= (1 + affix.value)
                else:
                    total[affix.stat] += affix.value
            else:
                total[affix.stat] = affix.value

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
        "level_requirement": 5,
        "base_stats": {"physical_attack": 30, "accuracy": 8},
        "sell_price": 150
    },
    "mithril_sword": {
        "name": "미스릴 검",
        "description": "가볍고 날카로운 미스릴 검",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"physical_attack": 50, "accuracy": 12, "speed": 3},
        "sell_price": 500
    },
    "dragon_slayer": {
        "name": "드래곤 슬레이어",
        "description": "용을 베기 위해 만들어진 거대한 검",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 20,
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
        "level_requirement": 10,
        "base_stats": {"magic_attack": 60, "mp": 30, "spirit": 5},
        "sell_price": 600
    },
    "archmagus_staff": {
        "name": "대마법사의 지팡이",
        "description": "전설적인 대마법사가 사용했던 지팡이",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 25,
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
        "level_requirement": 7,
        "base_stats": {"physical_attack": 35, "accuracy": 15, "evasion": 3},
        "sell_price": 200
    },
    "composite_bow": {
        "name": "복합궁",
        "description": "강력한 복합 소재 활",
        "rarity": ItemRarity.RARE,
        "level_requirement": 12,
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
        "level_requirement": 10,
        "base_stats": {"physical_attack": 40, "speed": 10, "critical_rate": 20},
        "sell_price": 450
    },
    "venom_fang": {
        "name": "독니",
        "description": "독을 품은 단검",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
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
        "level_requirement": 8,
        "base_stats": {"physical_attack": 45, "strength": 8, "physical_defense": 5},
        "sell_price": 280
    },
    "titan_hammer": {
        "name": "티탄의 망치",
        "description": "거인의 힘이 깃든 망치",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 20,
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
        "level_requirement": 9,
        "base_stats": {"physical_attack": 48, "accuracy": 12, "physical_defense": 8},
        "sell_price": 320
    },
    "dragon_lance": {
        "name": "용의 창",
        "description": "용을 베는 전설의 창",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 25,
        "base_stats": {"physical_attack": 110, "accuracy": 20, "critical_rate": 15},
        "sell_price": 6000
    },

    # 마법 지팡이 추가
    "fire_staff": {
        "name": "화염의 지팡이",
        "description": "화염 마법 강화",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 7,
        "base_stats": {"magic_attack": 40, "mp": 20},
        "sell_price": 250
    },
    "ice_staff": {
        "name": "빙결의 지팡이",
        "description": "냉기 마법 강화",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 7,
        "base_stats": {"magic_attack": 40, "mp": 20},
        "sell_price": 250
    },
    "staff_of_cosmos": {
        "name": "우주의 지팡이",
        "description": "모든 원소를 다루는 지팡이",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 28,
        "base_stats": {"magic_attack": 130, "mp": 80, "spirit": 20},
        "sell_price": 7500
    },

    # === 생명력 흡수 무기 ===
    "vampiric_blade": {
        "name": "흡혈검",
        "description": "적의 생명력을 흡수하는 검",
        "rarity": ItemRarity.RARE,
        "level_requirement": 12,
        "base_stats": {"physical_attack": 55, "speed": -2},
        "unique_effect": "lifesteal:0.15",  # 15% 생명력 흡수
        "sell_price": 800
    },
    "soul_drinker": {
        "name": "영혼 포식자",
        "description": "영혼까지 삼키는 마검",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 20,
        "base_stats": {"physical_attack": 95, "magic_attack": 30, "hp": -50},
        "unique_effect": "lifesteal:0.25",  # 25% 생명력 흡수
        "sell_price": 2500
    },
    "crimson_reaver": {
        "name": "진홍의 수확자",
        "description": "피를 갈구하는 낫. 처치 시 HP 회복",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"physical_attack": 80, "critical": 15},
        "unique_effect": "lifesteal:0.12|on_kill_heal:50",
        "sell_price": 1800
    },

    # === BRV 특화 무기 ===
    "brave_enhancer": {
        "name": "브레이브 인챈서",
        "description": "BRV 공격력을 크게 증폭시키는 검",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"physical_attack": 45, "speed": 3},
        "unique_effect": "brv_bonus:0.30",  # BRV +30%
        "sell_price": 600
    },
    "breaker": {
        "name": "브레이커",
        "description": "BREAK 특화 무기. BREAK 데미지 증가",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 16,
        "base_stats": {"physical_attack": 70, "luck": 10},
        "unique_effect": "brv_break_bonus:0.50",  # BREAK 데미지 +50%
        "sell_price": 1500
    },
    "soul_stealer": {
        "name": "영혼 강탈자",
        "description": "적의 BRV를 훔쳐온다",
        "rarity": ItemRarity.RARE,
        "level_requirement": 14,
        "base_stats": {"physical_attack": 60, "accuracy": 10},
        "unique_effect": "brv_steal:0.20",  # BRV 흡수 +20%
        "sell_price": 1000
    },

    # === 크리티컬 특화 ===
    "assassins_edge": {
        "name": "암살자의 칼날",
        "description": "치명타 확률과 데미지 증가",
        "rarity": ItemRarity.RARE,
        "level_requirement": 11,
        "base_stats": {"physical_attack": 50, "critical": 20, "speed": 5},
        "unique_effect": "critical_damage:0.50",  # 크리티컬 데미지 +50%
        "sell_price": 700
    },
    "fatal_strike": {
        "name": "필살검",
        "description": "극한의 치명타 특화 무기",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 22,
        "base_stats": {"physical_attack": 85, "critical": 35, "luck": 15},
        "unique_effect": "critical_damage:0.75|critical_chance:0.15",
        "sell_price": 3000
    },
    "backstabber": {
        "name": "배신자의 단검",
        "description": "적 HP 30% 이하 시 추가 데미지",
        "rarity": ItemRarity.RARE,
        "level_requirement": 13,
        "base_stats": {"physical_attack": 55, "critical": 15, "speed": 8},
        "unique_effect": "execute:0.30",  # 적 HP 30% 이하 시 +30% 데미지
        "sell_price": 900
    },

    # === 속성 무기 ===
    "flametongue": {
        "name": "화염검",
        "description": "불꽃을 두르는 검. 화상 부여",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 8,
        "base_stats": {"physical_attack": 40, "magic_attack": 15},
        "unique_effect": "element:fire|status_burn:0.25",  # 25% 화상
        "sell_price": 350
    },
    "frostbite": {
        "name": "동상의 검",
        "description": "얼음 속성. 적 속도 감소",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 8,
        "base_stats": {"physical_attack": 38, "magic_attack": 18},
        "unique_effect": "element:ice|debuff_slow:0.30",
        "sell_price": 350
    },
    "thunderstrike": {
        "name": "뇌전검",
        "description": "번개 속성. 감전 부여",
        "rarity": ItemRarity.RARE,
        "level_requirement": 12,
        "base_stats": {"physical_attack": 52, "magic_attack": 25, "speed": 4},
        "unique_effect": "element:lightning|status_shock:0.30|chain_lightning:0.20",
        "sell_price": 750
    },
    "earthshaker": {
        "name": "대지 파괴자",
        "description": "대지 속성. 방어력 무시 20%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 15,
        "base_stats": {"physical_attack": 75, "strength": 12},
        "unique_effect": "element:earth|armor_penetration:0.20",
        "sell_price": 1200
    },
    "windcutter": {
        "name": "바람 절단자",
        "description": "바람 속성. 공격 속도 증가",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 9,
        "base_stats": {"physical_attack": 42, "speed": 8, "accuracy": 10},
        "unique_effect": "element:wind|multi_strike:0.15",  # 15% 2회 공격
        "sell_price": 400
    },
    "voidreaver": {
        "name": "공허의 수확자",
        "description": "어둠 속성. MP 흡수",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 19,
        "base_stats": {"physical_attack": 88, "magic_attack": 40, "mp": 50},
        "unique_effect": "element:void|mp_steal:0.30|debuff_silence:0.20",
        "sell_price": 2200
    },
    "holy_avenger": {
        "name": "성스러운 복수자",
        "description": "신성 속성. 언데드에게 추가 데미지",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 20,
        "base_stats": {"physical_attack": 90, "magic_attack": 35, "spirit": 15},
        "unique_effect": "element:holy|bonus_vs_undead:0.50|heal_on_hit:5",
        "sell_price": 2500
    },

    # === 방어 관통 무기 ===
    "armor_piercer": {
        "name": "갑옷 관통자",
        "description": "방어력을 무시하는 창",
        "rarity": ItemRarity.RARE,
        "level_requirement": 12,
        "base_stats": {"physical_attack": 58, "accuracy": 15},
        "unique_effect": "armor_penetration:0.25",
        "sell_price": 800
    },
    "true_strike_spear": {
        "name": "필중의 창",
        "description": "절대 빗나가지 않는 창. 명중률 대폭 증가",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 17,
        "base_stats": {"physical_attack": 82, "accuracy": 50},
        "unique_effect": "never_miss|armor_penetration:0.15",
        "sell_price": 1800
    },

    # === 속도/연타 무기 ===
    "rapier": {
        "name": "레이피어",
        "description": "빠른 연속 공격",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 32, "speed": 12, "accuracy": 8},
        "unique_effect": "multi_strike:0.25|dodge_chance:0.10",
        "sell_price": 300
    },
    "twin_daggers": {
        "name": "쌍검",
        "description": "2회 연속 공격",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"physical_attack": 40, "speed": 10, "critical": 10},
        "unique_effect": "double_strike|critical_chance:0.10",
        "sell_price": 650
    },
    "flurry_blade": {
        "name": "난무의 검",
        "description": "3~5회 연속 공격 (랜덤)",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"physical_attack": 50, "speed": 15, "critical": 15},
        "unique_effect": "multi_strike:1.0|strike_count:3-5",  # 100% 확률로 3~5회
        "sell_price": 2000
    },

    # === 방어/탱커 무기 ===
    "shield_bash_mace": {
        "name": "방패격 메이스",
        "description": "공격 시 일정 확률로 적 스턴",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 9,
        "base_stats": {"physical_attack": 42, "defense": 8},
        "unique_effect": "stun_chance:0.20|block_chance:0.10",
        "sell_price": 400
    },
    "defenders_hammer": {
        "name": "수호자의 망치",
        "description": "방어력에 비례한 추가 데미지",
        "rarity": ItemRarity.RARE,
        "level_requirement": 14,
        "base_stats": {"physical_attack": 60, "defense": 20, "hp": 100},
        "unique_effect": "damage_from_defense:0.50|thorns:0.15",
        "sell_price": 1100
    },
    "aegis_blade": {
        "name": "이지스 검",
        "description": "공격과 방어를 겸비한 검",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 19,
        "base_stats": {"physical_attack": 78, "defense": 30, "hp": 150},
        "unique_effect": "block_chance:0.25|counter_attack:0.30",
        "sell_price": 2300
    },

    # === 마법 무기 (특수 효과) ===
    "mana_blade": {
        "name": "마나 블레이드",
        "description": "MP를 소모해 추가 데미지",
        "rarity": ItemRarity.RARE,
        "level_requirement": 13,
        "base_stats": {"physical_attack": 55, "magic_attack": 30, "mp": 50},
        "unique_effect": "mp_to_damage:2.0|mp_cost_per_hit:10",  # MP 10당 20 추가 데미지
        "sell_price": 950
    },
    "arcane_staff": {
        "name": "비전 지팡이",
        "description": "MP 재생 증가. 스킬 쿨다운 감소",
        "rarity": ItemRarity.RARE,
        "level_requirement": 11,
        "base_stats": {"magic_attack": 60, "mp": 60, "spirit": 10},
        "unique_effect": "mp_regen:5|cooldown_reduction:0.15",  # 턴당 MP+5, 쿨다운 -15%
        "sell_price": 750
    },
    "chaos_orb_staff": {
        "name": "혼돈의 오브 지팡이",
        "description": "랜덤 속성 공격. 모든 속성 친화력",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 21,
        "base_stats": {"magic_attack": 100, "mp": 100, "luck": 20},
        "unique_effect": "random_element|all_element_affinity:0.20|wild_magic:0.30",
        "sell_price": 2800
    },
    "wisdom_tome": {
        "name": "지혜의 서",
        "description": "마법 공격력 증가. 스킬 성공률 +20%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"magic_attack": 55, "mp": 70, "spirit": 15},
        "unique_effect": "spell_power:0.15|skill_success:0.20",
        "sell_price": 700
    },
    "elemental_scepter": {
        "name": "원소 홀",
        "description": "모든 원소 마법 위력 +25%",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"magic_attack": 85, "mp": 90, "all_element_power": 25},
        "unique_effect": "elemental_mastery:0.25",
        "sell_price": 2100
    },
    "spell_amplifier": {
        "name": "주문 증폭기",
        "description": "마법 위력 +30%. MP 소비 +20%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 14,
        "base_stats": {"magic_attack": 70, "mp": 60, "spirit": 12},
        "unique_effect": "spell_power:0.30|mp_cost_mult:1.20",
        "sell_price": 1000
    },
    "mana_channeler": {
        "name": "마나 전도체",
        "description": "MP 재생 +10. 마법 위력 +20%",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 19,
        "base_stats": {"magic_attack": 90, "mp": 120, "spirit": 18},
        "unique_effect": "mp_regen:10|spell_power:0.20",
        "sell_price": 2400
    },
    "mind_staff": {
        "name": "정신력 지팡이",
        "description": "Spirit에 비례한 마법 공격력 증가",
        "rarity": ItemRarity.RARE,
        "level_requirement": 15,
        "base_stats": {"magic_attack": 65, "mp": 80, "spirit": 25},
        "unique_effect": "magic_from_spirit:0.50",  # Spirit의 50%를 마법 공격력에 추가
        "sell_price": 1300
    },
    "spell_echo_staff": {
        "name": "메아리 지팡이",
        "description": "15% 확률로 스킬 2회 발동",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 20,
        "base_stats": {"magic_attack": 95, "mp": 100, "spirit": 20},
        "unique_effect": "spell_echo:0.15",
        "sell_price": 2600
    },
    "void_wand": {
        "name": "공허의 지팡이",
        "description": "적의 MP를 흡수. MP 재생 +8",
        "rarity": ItemRarity.RARE,
        "level_requirement": 16,
        "base_stats": {"magic_attack": 75, "mp": 90, "spirit": 15},
        "unique_effect": "mp_steal:0.20|mp_regen:8",
        "sell_price": 1500
    },
    "meteor_staff": {
        "name": "유성 지팡이",
        "description": "화염 마법 위력 +40%. 화염 저항 -20%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 13,
        "base_stats": {"magic_attack": 68, "mp": 70, "fire_power": 40},
        "unique_effect": "fire_mastery:0.40|fire_weakness:0.20",
        "sell_price": 950
    },
    "blizzard_wand": {
        "name": "눈보라 마법봉",
        "description": "냉기 마법 위력 +40%. 냉기 저항 -20%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 13,
        "base_stats": {"magic_attack": 68, "mp": 70, "ice_power": 40},
        "unique_effect": "ice_mastery:0.40|ice_weakness:0.20",
        "sell_price": 950
    },
    "thunderlord_rod": {
        "name": "천둥군주의 봉",
        "description": "번개 마법 위력 +40%. 번개 저항 -20%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 13,
        "base_stats": {"magic_attack": 68, "mp": 70, "lightning_power": 40},
        "unique_effect": "lightning_mastery:0.40|lightning_weakness:0.20",
        "sell_price": 950
    },

    # === 원거리 무기 ===
    "hunters_bow": {
        "name": "사냥꾼의 활",
        "description": "야생 동물에게 추가 데미지",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 5,
        "base_stats": {"physical_attack": 28, "accuracy": 12, "critical": 5},
        "unique_effect": "bonus_vs_beast:0.30|first_strike",
        "sell_price": 180
    },
    "sniper_rifle": {
        "name": "저격 활",
        "description": "극한의 명중률과 크리티컬",
        "rarity": ItemRarity.RARE,
        "level_requirement": 15,
        "base_stats": {"physical_attack": 72, "accuracy": 40, "critical": 25},
        "unique_effect": "critical_damage:1.0|headshot:0.20",  # 20% 확률로 즉사
        "sell_price": 1400
    },
    "repeating_crossbow": {
        "name": "연발 석궁",
        "description": "3회 연속 공격",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 10,
        "base_stats": {"physical_attack": 35, "accuracy": 10, "speed": 5},
        "unique_effect": "triple_shot|ammo_efficiency:0.20",
        "sell_price": 550
    },

    # === 디버프 무기 ===
    "poison_dagger": {
        "name": "독침 단검",
        "description": "공격 시 독 부여",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 7,
        "base_stats": {"physical_attack": 35, "speed": 6},
        "unique_effect": "status_poison:0.40|poison_damage:10",  # 40% 독, 턴당 10 데미지
        "sell_price": 320
    },
    "cursed_blade": {
        "name": "저주받은 검",
        "description": "모든 디버프 확률 증가. 사용자도 HP -10%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 16,
        "base_stats": {"physical_attack": 85, "magic_attack": 40, "hp": -100},
        "unique_effect": "debuff_master:0.30|curse_self:hp_max_reduction:0.10",
        "sell_price": 1300
    },
    "weakening_mace": {
        "name": "약화의 메이스",
        "description": "적 방어력 감소",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 9,
        "base_stats": {"physical_attack": 44, "accuracy": 5},
        "unique_effect": "debuff_defense_down:0.25|armor_break:0.30",
        "sell_price": 420
    },
    "terror_scythe": {
        "name": "공포의 낫",
        "description": "공격 시 공포 부여. 적 회피율 감소",
        "rarity": ItemRarity.RARE,
        "level_requirement": 14,
        "base_stats": {"physical_attack": 68, "magic_attack": 25, "critical": 15},
        "unique_effect": "status_fear:0.35|accuracy_debuff:0.20|harvest_soul:0.10",
        "sell_price": 1100
    },

    # === 특수 기믹 무기 ===
    "combo_master": {
        "name": "콤보 마스터",
        "description": "연속 공격 시 데미지 증가 (최대 5회)",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"physical_attack": 70, "speed": 12, "critical": 10},
        "unique_effect": "combo_bonus:0.15|max_combo:5",  # 콤보당 +15%, 최대 75%
        "sell_price": 1900
    },
    "momentum_blade": {
        "name": "역전의 검",
        "description": "HP가 낮을수록 강해짐",
        "rarity": ItemRarity.RARE,
        "level_requirement": 13,
        "base_stats": {"physical_attack": 60, "speed": 8},
        "unique_effect": "berserk|low_hp_bonus:1.0",  # HP 낮을수록 최대 +100%
        "sell_price": 900
    },
    "overload_staff": {
        "name": "과부하 지팡이",
        "description": "MP 소모 2배, 위력 2.5배",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 20,
        "base_stats": {"magic_attack": 110, "mp": 100, "spirit": 15},
        "unique_effect": "overload:mp_cost:2.0|damage:2.5",
        "sell_price": 2600
    },
    "gambler_dice": {
        "name": "도박사의 주사위",
        "description": "데미지가 50%~200% 사이로 랜덤",
        "rarity": ItemRarity.RARE,
        "level_requirement": 12,
        "base_stats": {"physical_attack": 80, "luck": 30},
        "unique_effect": "random_damage:0.5-2.0|lucky_crit:0.20",
        "sell_price": 800
    },

    # === 레전더리 무기 ===
    "infinity_edge": {
        "name": "무한의 칼날",
        "description": "크리티컬 확률 2배. 크리티컬 데미지 극대화",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 25,
        "base_stats": {"physical_attack": 120, "critical": 50, "speed": 10},
        "unique_effect": "critical_chance:1.0|critical_damage:1.5|ignore_armor:0.30",
        "sell_price": 8000
    },
    "ultima_weapon": {
        "name": "얼티마 웨폰",
        "description": "HP가 만땅일 때 모든 능력치 +50%",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 30,
        "base_stats": {"physical_attack": 140, "magic_attack": 80, "hp": 200, "mp": 100},
        "unique_effect": "full_hp_bonus:all_stats:0.50|invincible_at_full_hp",
        "sell_price": 15000
    },
    "apocalypse": {
        "name": "아포칼립스",
        "description": "적 처치 시 모든 자원 회복. 영구 버프 누적",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 28,
        "base_stats": {"physical_attack": 135, "magic_attack": 70, "all_stats": 15},
        "unique_effect": "on_kill:restore_all|stack_buff:permanent|reaper:0.30",
        "sell_price": 12000
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
        "level_requirement": 5,
        "base_stats": {"physical_defense": 25, "hp": 40},
        "sell_price": 120
    },
    "plate_armor": {
        "name": "판금 갑옷",
        "description": "무거운 철판 갑옷",
        "rarity": ItemRarity.RARE,
        "level_requirement": 12,
        "base_stats": {"physical_defense": 50, "hp": 80, "physical_attack": -5},
        "sell_price": 600
    },
    "dragon_scale_armor": {
        "name": "용비늘 갑옷",
        "description": "드래곤의 비늘로 만든 갑옷",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 25,
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
        "level_requirement": 10,
        "base_stats": {"magic_defense": 40, "mp": 50, "magic_attack": 10},
        "sell_price": 500
    },
    "archmage_robe": {
        "name": "대마법사 로브",
        "description": "강력한 마력의 로브",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"magic_defense": 70, "mp": 100, "magic_attack": 25},
        "sell_price": 2000
    },
    "celestial_robes": {
        "name": "천상의 로브",
        "description": "별들의 힘이 담긴 로브",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 26,
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
        "level_requirement": 6,
        "base_stats": {"physical_defense": 22, "evasion": 8, "hp": 30},
        "sell_price": 180
    },
    "scale_mail": {
        "name": "비늘 갑옷",
        "description": "비늘 모양으로 만든 갑옷",
        "rarity": ItemRarity.RARE,
        "level_requirement": 13,
        "base_stats": {"physical_defense": 45, "magic_defense": 25, "hp": 70},
        "sell_price": 800
    },

    # 중갑 추가
    "knight_armor": {
        "name": "기사 갑옷",
        "description": "기사단의 갑옷",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 8,
        "base_stats": {"physical_defense": 35, "hp": 50, "strength": 5},
        "sell_price": 350
    },
    "dragon_armor": {
        "name": "드래곤 아머",
        "description": "용의 힘이 깃든 갑옷",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 24,
        "base_stats": {"physical_defense": 95, "magic_defense": 75, "hp": 180, "strength": 12},
        "sell_price": 9000
    },

    # === 상처 시스템 연동 방어구 ===
    "healers_robe": {
        "name": "치유사의 로브",
        "description": "받는 상처 30% 감소. 회복량 +20%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"magic_defense": 35, "spirit": 12, "hp": 80},
        "unique_effect": "wound_reduction:0.30|heal_boost:0.20",
        "sell_price": 650
    },
    "regenerative_armor": {
        "name": "재생의 갑옷",
        "description": "턴마다 상처 회복. HP 재생",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 16,
        "base_stats": {"physical_defense": 60, "hp": 150, "defense": 15},
        "unique_effect": "wound_regen:5|hp_regen:0.03",  # 턴당 상처 5, HP 3%
        "sell_price": 1800
    },
    "scarless_plate": {
        "name": "무흔의 판금",
        "description": "상처 면역. 받는 데미지 +10%",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"physical_defense": 70, "magic_defense": 40, "hp": 120},
        "unique_effect": "wound_immunity|damage_taken:0.10",
        "sell_price": 2200
    },
    "trauma_ward": {
        "name": "외상 보호복",
        "description": "받는 상처 50% 감소",
        "rarity": ItemRarity.RARE,
        "level_requirement": 12,
        "base_stats": {"physical_defense": 45, "magic_defense": 30, "hp": 100},
        "unique_effect": "wound_reduction:0.50",
        "sell_price": 850
    },

    # === BRV 시스템 연동 방어구 ===
    "brave_guard": {
        "name": "브레이브 가드",
        "description": "BRV 데미지 30% 감소. BREAK 저항",
        "rarity": ItemRarity.RARE,
        "level_requirement": 11,
        "base_stats": {"physical_defense": 40, "magic_defense": 35, "hp": 90},
        "unique_effect": "brv_shield:0.30|brv_protect",  # BREAK 1회 방지
        "sell_price": 700
    },
    "fortress_plate": {
        "name": "요새 판금",
        "description": "BRV 데미지 50% 감소. 이동 속도 -5",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 17,
        "base_stats": {"physical_defense": 85, "hp": 200, "speed": -5},
        "unique_effect": "brv_shield:0.50|block_chance:0.20",
        "sell_price": 2000
    },
    "breaker_armor": {
        "name": "파괴자의 갑옷",
        "description": "BRV 축적량 +25%. 방어력 -20%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 13,
        "base_stats": {"physical_defense": 35, "hp": 80},
        "unique_effect": "brv_bonus:0.25|defense_reduction:0.20",
        "sell_price": 800
    },

    # === 마법사 전용 로브 ===
    "apprentice_robe": {
        "name": "견습 마법사의 로브",
        "description": "MP 재생 +3. 마법 공격력 +10",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 3,
        "base_stats": {"magic_defense": 12, "mp": 40, "magic_attack": 12},
        "unique_effect": "mp_regen:3",
        "sell_price": 150
    },
    "battle_mage_robe": {
        "name": "전투 마법사의 로브",
        "description": "마법 위력 +15%. MP 소비 -10%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 11,
        "base_stats": {"magic_defense": 40, "mp": 80, "magic_attack": 25, "spirit": 12},
        "unique_effect": "spell_power:0.15|mp_cost_reduction:0.10",
        "sell_price": 750
    },
    "sorcerer_vestments": {
        "name": "마도사의 예복",
        "description": "MP 재생 +10. 스킬 쿨다운 -15%",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 17,
        "base_stats": {"magic_defense": 65, "mp": 120, "magic_attack": 35, "spirit": 18},
        "unique_effect": "mp_regen:10|cooldown_reduction:0.15|spell_power:0.10",
        "sell_price": 2000
    },
    "wisdom_robes": {
        "name": "지혜의 로브",
        "description": "Spirit +25. MP 최대치 +100",
        "rarity": ItemRarity.RARE,
        "level_requirement": 13,
        "base_stats": {"magic_defense": 48, "mp": 120, "spirit": 28, "magic_attack": 20},
        "unique_effect": "spell_success:0.20",  # 스킬 성공률 +20%
        "sell_price": 950
    },
    "elemental_master_robe": {
        "name": "원소 대가의 로브",
        "description": "모든 원소 저항 +20%. 원소 마법 위력 +25%",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 19,
        "base_stats": {"magic_defense": 72, "mp": 130, "magic_attack": 40, "spirit": 20},
        "unique_effect": "all_element_resist:0.20|elemental_mastery:0.25",
        "sell_price": 2400
    },
    "mana_weave_cloak": {
        "name": "마나직 망토",
        "description": "MP 소비 -25%. 마법 방어력 +30%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 14,
        "base_stats": {"magic_defense": 55, "mp": 100, "spirit": 15},
        "unique_effect": "mp_cost_reduction:0.25|magic_defense_boost:0.30",
        "sell_price": 1100
    },
    "spell_reflect_robe": {
        "name": "주문 반사 로브",
        "description": "마법 공격 30% 반사. 마법 방어력 +50",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 20,
        "base_stats": {"magic_defense": 85, "mp": 110, "spirit": 22},
        "unique_effect": "spell_reflect:0.30",
        "sell_price": 2700
    },

    # === HP/MP 재생 방어구 ===
    "troll_hide": {
        "name": "트롤 가죽",
        "description": "턴당 HP 5% 재생. 화염 약점",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"physical_defense": 38, "hp": 120},
        "unique_effect": "hp_regen:0.05|weakness_fire",
        "sell_price": 600
    },
    "phoenix_mail": {
        "name": "불사조 갑옷",
        "description": "HP 재생 +3%. 사망 시 50% HP로 부활 (1회)",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 20,
        "base_stats": {"physical_defense": 75, "magic_defense": 60, "hp": 150},
        "unique_effect": "hp_regen:0.03|phoenix_rebirth",
        "sell_price": 2800
    },
    "mana_silk_robe": {
        "name": "마나 실크 로브",
        "description": "턴당 MP 8 재생. MP 소비 -10%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 12,
        "base_stats": {"magic_defense": 45, "mp": 80, "magic_attack": 15},
        "unique_effect": "mp_regen:8|mp_cost_reduction:0.10",
        "sell_price": 750
    },
    "archmage_vestments": {
        "name": "대마법사의 예복",
        "description": "MP 재생 +12. 스킬 쿨다운 -20%",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 19,
        "base_stats": {"magic_defense": 70, "mp": 150, "magic_attack": 35, "spirit": 18},
        "unique_effect": "mp_regen:12|cooldown_reduction:0.20|spell_power:0.15",
        "sell_price": 2500
    },

    # === 가시/반사 방어구 ===
    "thorned_armor": {
        "name": "가시 갑옷",
        "description": "피격 시 데미지의 25% 반사",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 8,
        "base_stats": {"physical_defense": 32, "hp": 60},
        "unique_effect": "thorns:0.25",
        "sell_price": 350
    },
    "reflecting_plate": {
        "name": "반사 판금",
        "description": "피격 시 40% 반사. 마법 공격 50% 반사",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"physical_defense": 72, "magic_defense": 55, "hp": 140},
        "unique_effect": "thorns:0.40|spell_reflect:0.50",
        "sell_price": 2200
    },
    "vengeful_mail": {
        "name": "복수의 갑옷",
        "description": "피격 시 반격 30% 확률",
        "rarity": ItemRarity.RARE,
        "level_requirement": 14,
        "base_stats": {"physical_defense": 55, "hp": 110, "strength": 8},
        "unique_effect": "counter_attack:0.30|vengeance_damage:0.20",
        "sell_price": 1100
    },

    # === 방어/블록 방어구 ===
    "tower_shield_armor": {
        "name": "탑 방패 갑옷",
        "description": "블록 확률 30%. 블록 시 데미지 무효",
        "rarity": ItemRarity.RARE,
        "level_requirement": 13,
        "base_stats": {"physical_defense": 65, "hp": 150, "speed": -3},
        "unique_effect": "block_chance:0.30|block_perfect",
        "sell_price": 950
    },
    "adamantine_armor": {
        "name": "아다만타이트 갑옷",
        "description": "모든 데미지 15 감소. 크리티컬 무효",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 22,
        "base_stats": {"physical_defense": 90, "magic_defense": 70, "hp": 200},
        "unique_effect": "flat_damage_reduction:15|crit_immunity",
        "sell_price": 3200
    },
    "guardian_plate": {
        "name": "수호자의 판금",
        "description": "아군 보호. 아군이 받는 데미지 10% 대신 받음",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 19,
        "base_stats": {"physical_defense": 80, "magic_defense": 60, "hp": 180},
        "unique_effect": "ally_protect:0.10|damage_redirect",
        "sell_price": 2400
    },

    # === 회피 방어구 ===
    "shadow_cloak": {
        "name": "그림자 망토",
        "description": "회피율 +25%. 어둠 속성 저항",
        "rarity": ItemRarity.RARE,
        "level_requirement": 11,
        "base_stats": {"magic_defense": 30, "evasion": 25, "speed": 8},
        "unique_effect": "dodge_chance:0.25|shadow_resistance:0.50",
        "sell_price": 700
    },
    "mirage_vestments": {
        "name": "신기루 예복",
        "description": "회피율 +35%. 회피 시 반격",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 17,
        "base_stats": {"magic_defense": 55, "evasion": 35, "speed": 12, "luck": 10},
        "unique_effect": "dodge_chance:0.35|dodge_counter",
        "sell_price": 2000
    },
    "windwalker_armor": {
        "name": "바람걸음 갑옷",
        "description": "회피 +20%. 속도 +15",
        "rarity": ItemRarity.RARE,
        "level_requirement": 12,
        "base_stats": {"physical_defense": 35, "evasion": 20, "speed": 15},
        "unique_effect": "dodge_chance:0.20|move_speed:0.30",
        "sell_price": 800
    },

    # === 속성 저항 방어구 ===
    "fire_dragon_scale": {
        "name": "화염 드래곤 비늘",
        "description": "화염 면역. 화염 흡수로 HP 회복",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"physical_defense": 70, "magic_defense": 65, "hp": 140},
        "unique_effect": "fire_immunity|fire_absorb",
        "sell_price": 2300
    },
    "frost_plate": {
        "name": "서리 판금",
        "description": "냉기 면역. 공격받을 시 적 속도 감소",
        "rarity": ItemRarity.RARE,
        "level_requirement": 14,
        "base_stats": {"physical_defense": 58, "magic_defense": 50, "hp": 110},
        "unique_effect": "ice_immunity|on_hit_slow:0.30",
        "sell_price": 1200
    },
    "storm_mail": {
        "name": "폭풍 갑옷",
        "description": "번개 면역. 전기 데미지 반사",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 16,
        "base_stats": {"physical_defense": 65, "magic_defense": 60, "hp": 120, "speed": 8},
        "unique_effect": "lightning_immunity|lightning_reflect",
        "sell_price": 1900
    },
    "rainbow_robe": {
        "name": "무지개 로브",
        "description": "모든 속성 저항 +30%",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 20,
        "base_stats": {"magic_defense": 75, "spirit": 20, "hp": 130, "mp": 80},
        "unique_effect": "all_element_resist:0.30",
        "sell_price": 2700
    },

    # === 상태 이상 관련 방어구 ===
    "immunity_cloak": {
        "name": "면역 망토",
        "description": "독, 화상, 출혈 면역",
        "rarity": ItemRarity.RARE,
        "level_requirement": 13,
        "base_stats": {"magic_defense": 48, "hp": 100, "spirit": 10},
        "unique_effect": "status_immunity:poison,burn,bleed",
        "sell_price": 950
    },
    "cleansing_armor": {
        "name": "정화의 갑옷",
        "description": "모든 디버프 지속시간 -50%",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"physical_defense": 72, "magic_defense": 65, "hp": 150, "spirit": 15},
        "unique_effect": "debuff_duration:-0.50|cleanse_on_turn:0.30",  # 30% 확률로 디버프 제거
        "sell_price": 2300
    },
    "stalwart_plate": {
        "name": "불굴의 판금",
        "description": "스턴, 수면, 혼란 면역",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 19,
        "base_stats": {"physical_defense": 80, "hp": 180, "spirit": 12},
        "unique_effect": "cc_immunity:stun,sleep,confusion",
        "sell_price": 2500
    },

    # === 특수 기믹 방어구 ===
    "berserker_hide": {
        "name": "광전사의 가죽",
        "description": "HP 50% 이하 시 공격력 +40%, 방어력 -20%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 14,
        "base_stats": {"physical_defense": 45, "hp": 130, "strength": 12},
        "unique_effect": "berserk_mode:hp_below_50|attack:0.40|defense:-0.20",
        "sell_price": 1100
    },
    "glass_armor": {
        "name": "유리 갑옷",
        "description": "모든 데미지 +30%. 받는 데미지 +50%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 15,
        "base_stats": {"physical_defense": 20, "magic_defense": 15},
        "unique_effect": "glass_cannon:damage:0.30|taken:0.50",
        "sell_price": 1200
    },
    "bloodthirst_armor": {
        "name": "피의 갈증 갑옷",
        "description": "적 처치 시 최대 HP +10 (영구, 최대 10회)",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 20,
        "base_stats": {"physical_defense": 70, "hp": 150, "strength": 10},
        "unique_effect": "on_kill:max_hp:10|stack_max:10",
        "sell_price": 2600
    },
    "adaptive_mail": {
        "name": "적응형 갑옷",
        "description": "받은 데미지 타입에 저항 획득 (3턴)",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 21,
        "base_stats": {"physical_defense": 75, "magic_defense": 75, "hp": 160},
        "unique_effect": "adaptive_resistance:0.20|duration:3",
        "sell_price": 2900
    },

    # === 레전더리 방어구 ===
    "aegis_of_eternity": {
        "name": "영원의 이지스",
        "description": "모든 방어 +100. 블록 확률 50%. 불사 (HP 1로 생존 1회)",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 28,
        "base_stats": {"physical_defense": 120, "magic_defense": 110, "hp": 300, "all_stats": 15},
        "unique_effect": "block_chance:0.50|immortality:once|all_resist:0.30",
        "sell_price": 15000
    },
    "celestial_raiment": {
        "name": "천상의 예복",
        "description": "모든 속성 저항 50%. 상처 면역. MP 재생 +15",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 26,
        "base_stats": {"magic_defense": 110, "mp": 200, "spirit": 25, "magic_attack": 50},
        "unique_effect": "all_element_resist:0.50|wound_immunity|mp_regen:15|spell_power:0.30",
        "sell_price": 13000
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
        "level_requirement": 3,
        "base_stats": {"strength": 5, "physical_attack": 8},
        "sell_price": 100
    },
    "ring_of_wisdom": {
        "name": "지혜의 반지",
        "description": "착용자의 지혜를 증가시키는 반지",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"magic_attack": 8, "mp": 20},
        "sell_price": 100
    },
    "ring_of_agility": {
        "name": "민첩의 반지",
        "description": "착용자의 속도와 회피를 증가",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 4,
        "base_stats": {"speed": 8, "evasion": 10},
        "sell_price": 120
    },
    "ring_of_protection": {
        "name": "수호의 반지",
        "description": "모든 방어력을 증가시키는 반지",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"physical_defense": 15, "magic_defense": 15, "hp": 50},
        "sell_price": 450
    },
    "phoenix_ring": {
        "name": "불사조의 반지",
        "description": "부활의 힘이 깃든 반지",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 16,
        "base_stats": {"hp": 120, "magic_defense": 20},
        "sell_price": 1800
    },
    "ring_of_gods": {
        "name": "신의 반지",
        "description": "모든 능력치를 증가시키는 반지",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 22,
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
        "level_requirement": 8,
        "base_stats": {"hp": 100, "physical_defense": 10},
        "sell_price": 400
    },
    "amulet_of_mana": {
        "name": "마나의 부적",
        "description": "마력을 대폭 증가시키는 부적",
        "rarity": ItemRarity.RARE,
        "level_requirement": 8,
        "base_stats": {"mp": 80, "magic_defense": 10},
        "sell_price": 400
    },
    "dragon_pendant": {
        "name": "용의 펜던트",
        "description": "드래곤의 힘이 깃든 펜던트",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 14,
        "base_stats": {"physical_attack": 18, "magic_attack": 18, "hp": 70},
        "sell_price": 1500
    },
    "phoenix_pendant": {
        "name": "불사조 펜던트",
        "description": "부활의 불꽃이 담긴 펜던트",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 15,
        "base_stats": {"hp": 150, "mp": 60, "magic_defense": 25},
        "sell_price": 1600
    },
    "lucky_charm": {
        "name": "행운의 부적",
        "description": "행운을 가져다주는 신비한 부적",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 15,
        "base_stats": {"luck": 10, "accuracy": 10, "evasion": 10, "critical_rate": 15},
        "sell_price": 1500
    },

    # 귀걸이
    "ruby_earring": {
        "name": "루비 귀걸이",
        "description": "힘을 증가시키는 귀걸이",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 5,
        "base_stats": {"strength": 7, "physical_attack": 10},
        "sell_price": 180
    },
    "sapphire_earring": {
        "name": "사파이어 귀걸이",
        "description": "지성을 증가시키는 귀걸이",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 5,
        "base_stats": {"magic_attack": 12, "mp": 25},
        "sell_price": 180
    },
    "emerald_earring": {
        "name": "에메랄드 귀걸이",
        "description": "회복력을 증가시키는 귀걸이",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 5,
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
        "level_requirement": 7,
        "base_stats": {"strength": 8, "hp": 50, "physical_defense": 10},
        "sell_price": 280
    },
    "mages_sash": {
        "name": "마법사의 띠",
        "description": "마력을 강화하는 띠",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 7,
        "base_stats": {"magic_attack": 12, "mp": 40, "magic_defense": 10},
        "sell_price": 300
    },

    # === 시야 시스템 연동 장신구 ===
    "eagle_eye_amulet": {
        "name": "매의 눈 목걸이",
        "description": "시야 +1. 명중률 +15",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 5,
        "base_stats": {"accuracy": 15, "critical": 5},
        "unique_effect": "vision:1",
        "sell_price": 200
    },
    "far_sight_lens": {
        "name": "원시의 렌즈",
        "description": "시야 +1. 적 탐지",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"accuracy": 20, "luck": 8},
        "unique_effect": "vision:1|detect_enemy",
        "sell_price": 600
    },
    "owls_pendant": {
        "name": "부엉이의 펜던트",
        "description": "시야 +2. 야간 시야 (어둠 무시)",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 15,
        "base_stats": {"accuracy": 30, "spirit": 12, "luck": 10},
        "unique_effect": "vision:2|night_vision",
        "sell_price": 1500
    },
    "all_seeing_eye": {
        "name": "전지의 눈",
        "description": "시야 +2. 투시 (벽 너머 보기). 숨겨진 적 탐지",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 22,
        "base_stats": {"accuracy": 50, "luck": 20, "all_stats": 8},
        "unique_effect": "vision:2|true_sight|detect_hidden",
        "sell_price": 5000
    },
    "explorers_compass": {
        "name": "탐험가의 나침반",
        "description": "시야 +1. 지도에 보물 위치 표시",
        "rarity": ItemRarity.RARE,
        "level_requirement": 8,
        "base_stats": {"luck": 15},
        "unique_effect": "vision:1|treasure_finder",
        "sell_price": 450
    },

    # === 상처 관련 장신구 ===
    "wound_ward_ring": {
        "name": "상처 보호 반지",
        "description": "받는 상처 40% 감소",
        "rarity": ItemRarity.RARE,
        "level_requirement": 9,
        "base_stats": {"hp": 60, "spirit": 8},
        "unique_effect": "wound_reduction:0.40",
        "sell_price": 550
    },
    "scar_healer_amulet": {
        "name": "흉터 치유 목걸이",
        "description": "턴당 상처 8 회복. 회복량 +15%",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 14,
        "base_stats": {"hp": 100, "spirit": 15},
        "unique_effect": "wound_regen:8|heal_boost:0.15",
        "sell_price": 1400
    },
    "flawless_gem": {
        "name": "무결점의 보석",
        "description": "상처 면역. 최대 HP -10%",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"hp": -50, "all_stats": 5},
        "unique_effect": "wound_immunity",
        "sell_price": 1800
    },

    # === BRV 관련 장신구 ===
    "brave_ring": {
        "name": "브레이브 링",
        "description": "BRV 공격력 +20%",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 6,
        "base_stats": {"strength": 5, "magic_attack": 5},
        "unique_effect": "brv_bonus:0.20",
        "sell_price": 250
    },
    "break_master_badge": {
        "name": "브레이크 마스터 배지",
        "description": "BREAK 데미지 +40%. BRV 흡수 +15%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 12,
        "base_stats": {"strength": 10, "luck": 12},
        "unique_effect": "brv_break_bonus:0.40|brv_steal:0.15",
        "sell_price": 800
    },
    "shield_earring": {
        "name": "실드 귀걸이",
        "description": "BRV 데미지 40% 감소. BREAK 1회 방지",
        "rarity": ItemRarity.RARE,
        "level_requirement": 11,
        "base_stats": {"defense": 12, "spirit": 10},
        "unique_effect": "brv_shield:0.40|brv_protect",
        "sell_price": 700
    },
    "brave_surge_belt": {
        "name": "브레이브 서지 벨트",
        "description": "턴당 BRV +15. BRV 공격력 +15%",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 16,
        "base_stats": {"strength": 12, "speed": 8},
        "unique_effect": "brv_regen:15|brv_bonus:0.15",
        "sell_price": 1600
    },

    # === 생명력 흡수 장신구 ===
    "vampire_fang": {
        "name": "흡혈귀의 송곳니",
        "description": "생명력 흡수 10%. HP 재생 +2%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"hp": 70, "strength": 8},
        "unique_effect": "lifesteal:0.10|hp_regen:0.02",
        "sell_price": 600
    },
    "blood_ruby": {
        "name": "피의 루비",
        "description": "생명력 흡수 20%. 최대 HP +50",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 17,
        "base_stats": {"hp": 150, "strength": 15},
        "unique_effect": "lifesteal:0.20",
        "sell_price": 1900
    },
    "leech_ring": {
        "name": "흡혈 반지",
        "description": "생명력 흡수 8%. MP 흡수 8%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 13,
        "base_stats": {"hp": 80, "mp": 40},
        "unique_effect": "lifesteal:0.08|mp_steal:0.08",
        "sell_price": 900
    },

    # === 크리티컬 장신구 ===
    "lucky_coin": {
        "name": "행운의 동전",
        "description": "크리티컬 확률 +15%. 행운 +20",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 7,
        "base_stats": {"luck": 20, "critical": 10},
        "unique_effect": "critical_chance:0.15",
        "sell_price": 300
    },
    "executioners_token": {
        "name": "처형인의 징표",
        "description": "크리티컬 데미지 +60%. 적 HP 30% 이하 시 추가 +30%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 14,
        "base_stats": {"critical": 15, "luck": 15, "strength": 10},
        "unique_effect": "critical_damage:0.60|execute:0.30",
        "sell_price": 1100
    },
    "precision_monocle": {
        "name": "정밀 단안경",
        "description": "크리티컬 확률 +25%. 명중률 +30",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"critical": 20, "accuracy": 30, "luck": 18},
        "unique_effect": "critical_chance:0.25|never_miss_crit",  # 크리티컬은 절대 빗나가지 않음
        "sell_price": 2100
    },

    # === 회피/속도 장신구 ===
    "rabbit_foot": {
        "name": "토끼발",
        "description": "회피율 +15%. 속도 +8",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 6,
        "base_stats": {"evasion": 15, "speed": 8, "luck": 10},
        "unique_effect": "dodge_chance:0.15",
        "sell_price": 250
    },
    "phantom_boots": {
        "name": "유령 장화",
        "description": "회피율 +30%. 공격 회피 시 반격",
        "rarity": ItemRarity.RARE,
        "level_requirement": 13,
        "base_stats": {"evasion": 30, "speed": 12, "luck": 12},
        "unique_effect": "dodge_chance:0.30|dodge_counter",
        "sell_price": 950
    },
    "wind_walker_anklet": {
        "name": "바람걸이 발찌",
        "description": "속도 +20. 선제공격 보너스",
        "rarity": ItemRarity.RARE,
        "level_requirement": 11,
        "base_stats": {"speed": 20, "evasion": 15},
        "unique_effect": "first_strike|move_speed:0.40",
        "sell_price": 750
    },
    "time_stop_watch": {
        "name": "시간 정지 회중시계",
        "description": "속도 +25. 스킬 쿨다운 -25%",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 19,
        "base_stats": {"speed": 25, "all_stats": 8},
        "unique_effect": "cooldown_reduction:0.25|double_turn:0.10",  # 10% 확률로 2회 행동
        "sell_price": 2400
    },

    # === 방어 장신구 ===
    "iron_skin_ring": {
        "name": "강철 피부 반지",
        "description": "모든 데미지 10 감소",
        "rarity": ItemRarity.RARE,
        "level_requirement": 12,
        "base_stats": {"defense": 15, "hp": 80},
        "unique_effect": "flat_damage_reduction:10",
        "sell_price": 800
    },
    "titan_heart": {
        "name": "타이탄의 심장",
        "description": "최대 HP +200. HP 재생 +3%",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 20,
        "base_stats": {"hp": 250, "defense": 20},
        "unique_effect": "hp_regen:0.03|overheal_shield",  # 과다 회복 → 실드 전환
        "sell_price": 2600
    },
    "barrier_crystal": {
        "name": "배리어 크리스탈",
        "description": "턴 시작 시 최대 HP 20% 보호막 생성",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 17,
        "base_stats": {"hp": 120, "magic_defense": 25, "spirit": 15},
        "unique_effect": "barrier_on_turn:0.20",
        "sell_price": 1900
    },

    # === MP/마법 장신구 ===
    "arcane_focus": {
        "name": "비전 초점",
        "description": "MP 재생 +6. MP 소비 -15%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"mp": 60, "magic_attack": 18},
        "unique_effect": "mp_regen:6|mp_cost_reduction:0.15",
        "sell_price": 650
    },
    "mana_crystal": {
        "name": "마나 크리스탈",
        "description": "최대 MP +100. 마법 공격력 +20",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 8,
        "base_stats": {"mp": 120, "magic_attack": 25},
        "unique_effect": "spell_power:0.10",
        "sell_price": 400
    },
    "sorcerers_pendant": {
        "name": "마법사의 펜던트",
        "description": "스킬 쿨다운 -20%. MP 재생 +8",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"mp": 100, "magic_attack": 30, "spirit": 15},
        "unique_effect": "cooldown_reduction:0.20|mp_regen:8|spell_power:0.15",
        "sell_price": 2200
    },
    "infinite_mana_orb": {
        "name": "무한 마나 오브",
        "description": "MP 소비 -50%. 마법 공격력 +40",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 24,
        "base_stats": {"mp": 200, "magic_attack": 60, "spirit": 25},
        "unique_effect": "mp_cost_reduction:0.50|spell_power:0.30|mana_overflow",
        "sell_price": 8000
    },

    # === 상태 이상 관련 장신구 ===
    "antidote_charm": {
        "name": "해독 부적",
        "description": "독, 질병 면역",
        "rarity": ItemRarity.COMMON,
        "level_requirement": 4,
        "base_stats": {"hp": 40, "spirit": 5},
        "unique_effect": "status_immunity:poison,disease",
        "sell_price": 150
    },
    "freedom_amulet": {
        "name": "자유의 목걸이",
        "description": "스턴, 수면, 혼란, 공포 면역",
        "rarity": ItemRarity.RARE,
        "level_requirement": 14,
        "base_stats": {"spirit": 18, "hp": 90},
        "unique_effect": "cc_immunity:stun,sleep,confusion,fear",
        "sell_price": 1200
    },
    "purity_ring": {
        "name": "순수의 반지",
        "description": "모든 상태 이상 면역. 최대 HP -50",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 20,
        "base_stats": {"spirit": 25, "hp": -50, "magic_defense": 30},
        "unique_effect": "status_immunity:all",
        "sell_price": 2800
    },
    "cleansing_bell": {
        "name": "정화의 종",
        "description": "턴 시작 시 디버프 1개 제거",
        "rarity": ItemRarity.RARE,
        "level_requirement": 12,
        "base_stats": {"spirit": 15, "mp": 50},
        "unique_effect": "cleanse_on_turn:1|debuff_resist:0.30",
        "sell_price": 850
    },

    # === 골드/경험치/드롭 장신구 ===
    "golden_scarab": {
        "name": "황금 스카라베",
        "description": "골드 획득 +50%",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 5,
        "base_stats": {"luck": 12},
        "unique_effect": "gold_find:0.50",
        "sell_price": 300
    },
    "merchants_signet": {
        "name": "상인의 인장",
        "description": "골드 획득 +100%. 아이템 가격 -10%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"luck": 18},
        "unique_effect": "gold_find:1.00|shop_discount:0.10",
        "sell_price": 700
    },
    "dragons_hoard_ring": {
        "name": "용의 보물 반지",
        "description": "골드 획득 +150%. 레어 아이템 드롭률 +30%",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 18,
        "base_stats": {"luck": 25, "all_stats": 5},
        "unique_effect": "gold_find:1.50|item_rarity:0.30",
        "sell_price": 2500
    },
    "scholars_tome": {
        "name": "학자의 서",
        "description": "경험치 +30%",
        "rarity": ItemRarity.UNCOMMON,
        "level_requirement": 3,
        "base_stats": {"spirit": 8},
        "unique_effect": "exp_bonus:0.30",
        "sell_price": 250
    },
    "mentor_medallion": {
        "name": "스승의 메달",
        "description": "경험치 +50%. 스킬 숙련도 +25%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 10,
        "base_stats": {"spirit": 15, "all_stats": 3},
        "unique_effect": "exp_bonus:0.50|skill_mastery:0.25",
        "sell_price": 800
    },
    "item_magnet": {
        "name": "아이템 자석",
        "description": "아이템 드롭률 +40%. 행운 +20",
        "rarity": ItemRarity.RARE,
        "level_requirement": 12,
        "base_stats": {"luck": 25},
        "unique_effect": "item_find:0.40|auto_pickup",
        "sell_price": 900
    },

    # === 특수 기믹 장신구 ===
    "phoenix_down_pendant": {
        "name": "불사조 깃털 펜던트",
        "description": "사망 시 HP 100% 부활 (1회)",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 22,
        "base_stats": {"hp": 150, "mp": 80, "all_stats": 8},
        "unique_effect": "phoenix_rebirth:full",
        "sell_price": 3500
    },
    "second_chance_coin": {
        "name": "두 번째 기회 동전",
        "description": "사망 시 50% HP 부활 (2회)",
        "rarity": ItemRarity.RARE,
        "level_requirement": 16,
        "base_stats": {"hp": 100, "luck": 15},
        "unique_effect": "phoenix_rebirth:half|charges:2",
        "sell_price": 1600
    },
    "rage_gem": {
        "name": "분노의 보석",
        "description": "HP 낮을수록 공격력 증가 (최대 +80%)",
        "rarity": ItemRarity.RARE,
        "level_requirement": 13,
        "base_stats": {"strength": 15, "hp": 80},
        "unique_effect": "berserk|low_hp_bonus:0.80",
        "sell_price": 950
    },
    "glass_cannon_gem": {
        "name": "유리 대포 보석",
        "description": "공격력 +50%. 방어력 -30%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 14,
        "base_stats": {"strength": 20, "magic_attack": 20},
        "unique_effect": "glass_cannon:damage:0.50|defense:-0.30",
        "sell_price": 1100
    },
    "balanced_core": {
        "name": "균형의 핵",
        "description": "모든 스탯 +10. 모든 능력 균형 잡힘",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 20,
        "base_stats": {"all_stats": 12},
        "unique_effect": "balanced_stats:0.15",  # 모든 스탯에 15% 보너스
        "sell_price": 2700
    },
    "combo_chain_badge": {
        "name": "콤보 체인 배지",
        "description": "연속 공격 시 데미지 증가 (콤보당 +20%, 최대 5회)",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 17,
        "base_stats": {"speed": 15, "strength": 12, "critical": 10},
        "unique_effect": "combo_bonus:0.20|max_combo:5",
        "sell_price": 2000
    },
    "overload_core": {
        "name": "과부하 코어",
        "description": "모든 자원 소비 2배. 모든 효과 2.5배",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 21,
        "base_stats": {"all_stats": 15},
        "unique_effect": "overload:cost:2.0|effect:2.5",
        "sell_price": 2900
    },

    # === 기믹 강화 장신구 ===
    "gimmick_booster": {
        "name": "기믹 부스터",
        "description": "기믹 효율 +30%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 11,
        "base_stats": {"all_stats": 5},
        "unique_effect": "gimmick_boost:0.30",
        "sell_price": 750
    },
    "max_stack_amplifier": {
        "name": "최대 스택 증폭기",
        "description": "최대 기믹 스택 +2",
        "rarity": ItemRarity.EPIC,
        "level_requirement": 16,
        "base_stats": {"all_stats": 8},
        "unique_effect": "max_gimmick_increase:2",
        "sell_price": 1800
    },
    "resource_saver": {
        "name": "자원 절약가",
        "description": "기믹 소모 -30%. MP 소비 -20%",
        "rarity": ItemRarity.RARE,
        "level_requirement": 13,
        "base_stats": {"mp": 60, "spirit": 12},
        "unique_effect": "gimmick_cost_reduction:0.30|mp_cost_reduction:0.20",
        "sell_price": 1000
    },

    # === 레전더리 장신구 ===
    "ring_of_gods": {
        "name": "신들의 반지",
        "description": "모든 스탯 +25. 모든 효과 +20%",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 28,
        "base_stats": {"all_stats": 30},
        "unique_effect": "omnipotent:0.20",  # 모든 효과 20% 증폭
        "sell_price": 15000
    },
    "infinity_stone": {
        "name": "무한석",
        "description": "자원 무한. MP 소비 없음. HP 재생 +5%",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 30,
        "base_stats": {"hp": 200, "mp": 300, "all_stats": 20},
        "unique_effect": "infinite_resources|hp_regen:0.05|mp_cost:0",
        "sell_price": 20000
    },
    "omniscient_eye": {
        "name": "전지의 눈동자",
        "description": "시야 +2. 모든 것을 볼 수 있음. 크리티컬 +50%",
        "rarity": ItemRarity.LEGENDARY,
        "level_requirement": 26,
        "base_stats": {"critical": 50, "accuracy": 100, "luck": 30},
        "unique_effect": "vision:2|true_sight|omniscient|critical_chance:0.50",
        "sell_price": 12000
    },
}

# 유니크 아이템
UNIQUE_ITEMS = {
    "excalibur": {
        "name": "엑스칼리버",
        "description": "전설의 성검",
        "rarity": ItemRarity.UNIQUE,
        "level_requirement": 30,
        "base_stats": {"physical_attack": 150, "magic_attack": 50, "hp": 100, "mp": 50},
        "unique_effect": "HP 50% 이상 시 모든 공격력 +30%",
        "sell_price": 99999
    },
    "mjolnir": {
        "name": "묠니르",
        "description": "천둥의 망치",
        "rarity": ItemRarity.UNIQUE,
        "level_requirement": 28,
        "base_stats": {"physical_attack": 140, "strength": 20},
        "unique_effect": "공격 시 30% 확률로 번개 추가 데미지",
        "sell_price": 88888
    },
    "infinity_gauntlet": {
        "name": "무한의 건틀릿",
        "description": "모든 능력을 강화하는 전설의 장갑",
        "rarity": ItemRarity.UNIQUE,
        "level_requirement": 35,
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
        "level_requirement": 20,
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
}


class ItemGenerator:
    """아이템 생성기"""

    @staticmethod
    def generate_random_affixes(rarity: ItemRarity) -> List[ItemAffix]:
        """등급에 따라 랜덤 접사 생성"""
        num_affixes = {
            ItemRarity.COMMON: 0,
            ItemRarity.UNCOMMON: 1,
            ItemRarity.RARE: 2,
            ItemRarity.EPIC: 3,
            ItemRarity.LEGENDARY: 4,
            ItemRarity.UNIQUE: 0  # 유니크는 고정 능력
        }

        count = num_affixes.get(rarity, 0)
        if count == 0:
            return []

        # 랜덤 접사 선택
        available_affixes = list(AFFIX_POOL.values())
        selected = random.sample(available_affixes, min(count, len(available_affixes)))

        return selected

    @staticmethod
    def create_weapon(template_id: str, add_random_affixes: bool = True) -> Equipment:
        """무기 생성"""
        template = WEAPON_TEMPLATES.get(template_id)
        if not template:
            raise ValueError(f"Unknown weapon template: {template_id}")

        affixes = []
        if add_random_affixes:
            affixes = ItemGenerator.generate_random_affixes(template["rarity"])

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
            affixes = ItemGenerator.generate_random_affixes(template["rarity"])

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
            affixes = ItemGenerator.generate_random_affixes(template["rarity"])

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
            # 적합한 템플릿 없으면 소비 아이템
            return ItemGenerator.create_consumable("health_potion")

        template_id, template = random.choice(suitable_templates)

        # 타입에 따라 생성
        if template_id in WEAPON_TEMPLATES:
            return ItemGenerator.create_weapon(template_id)
        elif template_id in ARMOR_TEMPLATES:
            return ItemGenerator.create_armor(template_id)
        else:
            return ItemGenerator.create_accessory(template_id)
