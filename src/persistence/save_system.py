"""
저장/로드 시스템

모든 게임 상태를 JSON으로 저장
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.SYSTEM)


class SaveSystem:
    """저장 시스템"""

    def __init__(self, save_directory: str = "saves"):
        self.save_dir = Path(save_directory)
        self.save_dir.mkdir(exist_ok=True)

    def save_game(self, save_name: str, game_state: Dict[str, Any]) -> bool:
        """
        게임 저장

        Args:
            save_name: 저장 파일 이름
            game_state: 전체 게임 상태 딕셔너리

        Returns:
            성공 여부
        """
        try:
            save_path = self.save_dir / f"{save_name}.json"

            # 저장 시간 추가
            game_state["save_time"] = datetime.now().isoformat()
            game_state["version"] = "5.0.0"

            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(game_state, f, indent=2, ensure_ascii=False)

            logger.info(f"게임 저장 완료: {save_path}")
            return True

        except Exception as e:
            logger.error(f"게임 저장 실패: {e}")
            return False

    def load_game(self, save_name: str) -> Optional[Dict[str, Any]]:
        """
        게임 로드

        Args:
            save_name: 저장 파일 이름

        Returns:
            게임 상태 딕셔너리 또는 None
        """
        try:
            save_path = self.save_dir / f"{save_name}.json"

            if not save_path.exists():
                logger.warning(f"저장 파일 없음: {save_path}")
                return None

            with open(save_path, 'r', encoding='utf-8') as f:
                game_state = json.load(f)

            logger.info(f"게임 로드 완료: {save_path}")
            return game_state

        except Exception as e:
            logger.error(f"게임 로드 실패: {e}")
            return None

    def list_saves(self) -> List[Dict[str, Any]]:
        """저장 파일 목록"""
        saves = []

        for save_file in self.save_dir.glob("*.json"):
            # meta_progress.json은 게임 세이브 파일이 아니므로 제외
            if save_file.stem == "meta_progress":
                continue

            try:
                with open(save_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 게임 세이브 파일인지 확인 (party 키가 있어야 함)
                if "party" not in data:
                    logger.debug(f"게임 세이브 파일이 아님: {save_file.name}")
                    continue

                saves.append({
                    "name": save_file.stem,
                    "save_time": data.get("save_time", "Unknown"),
                    "floor": data.get("floor_number", 1),
                    "party_size": len(data.get("party", []))
                })

            except Exception as e:
                logger.warning(f"저장 파일 읽기 실패: {save_file}, {e}")

        return sorted(saves, key=lambda x: x["save_time"], reverse=True)

    def delete_save(self, save_name: str) -> bool:
        """저장 파일 삭제"""
        try:
            save_path = self.save_dir / f"{save_name}.json"
            if save_path.exists():
                save_path.unlink()
                logger.info(f"저장 파일 삭제: {save_path}")
                return True
            return False

        except Exception as e:
            logger.error(f"저장 파일 삭제 실패: {e}")
            return False

    def save_exists(self, slot: int) -> bool:
        """
        저장 파일 존재 여부 확인

        Args:
            slot: 슬롯 번호

        Returns:
            저장 파일이 존재하면 True, 없으면 False
        """
        save_path = self.save_dir / f"save_slot_{slot}.json"
        return save_path.exists()


def serialize_party_member(member: Any) -> Dict[str, Any]:
    """파티원 직렬화"""
    # StatManager가 있으면 직렬화
    stats_data = None
    if hasattr(member, 'stat_manager'):
        stats_data = member.stat_manager.to_dict()

    # 기믹 상태 직렬화
    gimmick_state = serialize_gimmick_state(member)

    # active_buffs 직렬화 (요리 버프 포함)
    active_buffs_data = {}
    if hasattr(member, 'active_buffs') and member.active_buffs:
        active_buffs_data = member.active_buffs.copy()
    
    return {
        "name": member.name,
        "character_class": getattr(member, 'character_class', getattr(member, 'job_id', 'unknown')),
        "job_name": getattr(member, 'job_name', 'Unknown'),
        "level": getattr(member, 'level', 1),
        "current_hp": getattr(member, 'current_hp', 100),
        "current_mp": getattr(member, 'current_mp', 50),
        "current_brv": getattr(member, 'current_brv', 0),
        "experience": getattr(member, 'experience', 0),
        "stats": stats_data,
        "equipment": serialize_equipment(member),
        "status_effects": getattr(member, 'status_effects', []),
        "skill_ids": getattr(member, 'skill_ids', []),
        "active_traits": getattr(member, 'active_traits', []),
        "active_buffs": active_buffs_data,  # 요리 버프 포함
        "gimmick_state": gimmick_state,
    }


def serialize_gimmick_state(member: Any) -> Dict[str, Any]:
    """기믹 상태 직렬화"""
    gimmick_state = {}
    
    if not hasattr(member, 'gimmick_type') or not member.gimmick_type:
        return gimmick_state
    
    gimmick_state["gimmick_type"] = member.gimmick_type
    
    # 기믹 타입별 저장할 속성 목록
    gimmick_attributes = {
        "stance_system": ["current_stance", "stance_focus", "available_stances"],
        "elemental_counter": ["fire_element", "ice_element", "lightning_element"],
        "aim_system": ["aim_points", "max_aim_points", "focus_stacks"],
        "magazine_system": ["magazine", "current_bullet_index", "quick_reload_count"],
        "venom_system": ["venom_power", "venom_power_max", "poison_stacks", "max_poison_stacks"],
        "shadow_system": ["shadow_count", "max_shadow_count"],
        "sword_aura": ["sword_aura", "max_sword_aura"],
        "rage_system": ["rage_stacks", "max_rage_stacks", "shield_amount"],
        "melody_system": ["melody_stacks", "max_melody_stacks", "melody_notes", "current_melody", "octave_completed"],
        "timeline_system": ["timeline", "min_timeline", "max_timeline", "optimal_point", "past_threshold", "future_threshold", "time_correction_counter"],
        "dragon_marks": ["dragon_marks", "max_dragon_marks", "dragon_power"],
        "arena_system": ["arena_points", "max_arena_points", "glory_points", "kill_count", "parry_active"],
        "break_system": ["break_power", "max_break_power"],
        "darkness_system": ["darkness", "max_darkness"],
        "duty_system": ["duty_stacks", "max_duty_stacks"],
        "holy_system": ["holy_power", "max_holy_power"],
        "theft_system": ["stolen_items", "max_stolen_items", "evasion_active"],
        "plunder_system": ["gold", "max_gold", "gold_per_hit"],
        "heat_management": ["heat", "max_heat", "optimal_min", "optimal_max", "danger_min", "danger_max", "overheat_threshold", "overheat_prevention_count", "is_overheated", "overheat_stun_turns"],
        "iaijutsu_system": ["will_gauge", "max_will_gauge"],
        "enchant_system": ["mana_blade", "max_mana_blade"],
        "divinity_system": ["judgment_points", "max_judgment_points", "faith_points", "max_faith_points"],
        "shapeshifting_system": ["nature_points", "max_nature_points", "current_form", "available_forms"],
        "totem_system": ["curse_stacks", "max_curse_stacks"],
        "blood_system": ["blood_pool", "max_blood_pool", "lifesteal_boost"],
        "alchemy_system": ["potion_stock", "max_potion_stock"],
        "wisdom_system": ["knowledge_stacks", "max_knowledge_stacks"],
        "hack_system": ["hack_stacks", "max_hack_stacks", "debuff_count", "max_debuff_count"],
        "yin_yang_flow": ["ki_gauge", "min_ki", "max_ki", "balance_center", "yin_threshold", "yang_threshold"],
        "rune_resonance": ["rune_fire", "rune_ice", "rune_lightning", "rune_earth", "rune_arcane", "max_rune_per_type", "max_runes_total", "resonance_bonus"],
        "undead_legion": ["undead_count", "max_undead_total", "undead_skeleton", "undead_zombie", "undead_ghost", "undead_power"],
        "madness_threshold": ["madness", "max_madness", "optimal_min", "optimal_max", "danger_min", "rampage_threshold"],
        "thirst_gauge": ["thirst", "max_thirst", "satisfied_max", "normal_min", "normal_max", "starving_min"],
        "multithread_system": ["active_threads", "max_threads", "thread_types"],
        "crowd_cheer": ["cheer", "max_cheer", "start_cheer", "cheer_zones"],
        "stealth_exposure": ["stealth_active", "exposed_turns", "restealth_cooldown"],
        "support_fire": ["marked_allies", "max_marks", "shots_per_mark", "support_fire_combo", "arrow_types"],
        "elemental_spirits": ["spirit_fire", "spirit_water", "spirit_wind", "spirit_earth", "max_spirits"],
        "dilemma_choice": ["choice_power", "choice_wisdom", "choice_sacrifice", "choice_survival", "choice_truth", "choice_lie", "choice_order", "choice_chaos", "accumulation_threshold"],
        "probability_distortion": ["distortion_gauge", "max_gauge", "start_gauge", "gauge_per_turn"],
    }
    
    # 해당 기믹 타입의 속성들을 저장
    attributes_to_save = gimmick_attributes.get(member.gimmick_type, [])
    for attr in attributes_to_save:
        if hasattr(member, attr):
            value = getattr(member, attr)
            # 리스트나 딕셔너리는 그대로 저장 (JSON 직렬화 가능)
            gimmick_state[attr] = value
    
    return gimmick_state


def serialize_equipment(member: Any) -> Dict[str, Any]:
    """장비 직렬화"""
    equipment = {}
    if hasattr(member, 'equipment'):
        for slot, item in member.equipment.items():
            if item:
                equipment[slot] = serialize_item(item)
    return equipment


def serialize_item(item: Any) -> Dict[str, Any]:
    """아이템 직렬화 (모든 아이템 타입 지원)"""
    from src.equipment.item_system import ItemAffix

    affixes = []
    if hasattr(item, 'affixes'):
        for affix in item.affixes:
            affixes.append({
                "id": affix.id,
                "name": affix.name,
                "stat": affix.stat,
                "value": affix.value,
                "is_percentage": affix.is_percentage
            })

    # 안전하게 속성 접근
    item_id = getattr(item, 'item_id', str(id(item)))
    name = getattr(item, 'name', '알 수 없는 아이템')
    description = getattr(item, 'description', '')

    # item_type 안전 접근
    item_type = getattr(item, 'item_type', None)
    if item_type:
        item_type_value = item_type.value if hasattr(item_type, 'value') else str(item_type)
    else:
        item_type_value = 'consumable'

    # rarity 안전 접근
    rarity = getattr(item, 'rarity', None)
    if rarity:
        rarity_value = rarity.id if hasattr(rarity, 'id') else str(rarity)
    else:
        rarity_value = 'common'

    level_requirement = getattr(item, 'level_requirement', 1)
    base_stats = getattr(item, 'base_stats', {})

    # equip_slot 안전 접근
    equip_slot = getattr(item, 'equip_slot', None)
    if equip_slot and hasattr(equip_slot, 'value'):
        equip_slot_value = equip_slot.value
    else:
        equip_slot_value = None

    result = {
        "item_id": item_id,
        "name": name,
        "description": description,
        "item_type": item_type_value,
        "rarity": rarity_value,
        "level_requirement": level_requirement,
        "base_stats": base_stats,
        "affixes": affixes,
        "unique_effect": getattr(item, 'unique_effect', None),
        "equip_slot": equip_slot_value,
        "weight": getattr(item, 'weight', 1.0),
        "sell_price": getattr(item, 'sell_price', 0)
    }
    
    # Ingredient 특수 속성 저장
    from src.gathering.ingredient import Ingredient
    if isinstance(item, Ingredient):
        result["ingredient_category"] = item.category.value if hasattr(item.category, 'value') else str(item.category)
        result["food_value"] = getattr(item, 'food_value', 1.0)
        result["freshness"] = getattr(item, 'freshness', 1.0)
        result["spoil_time"] = getattr(item, 'spoil_time', 0)
        result["edible_raw"] = getattr(item, 'edible_raw', False)
        result["raw_hp_restore"] = getattr(item, 'raw_hp_restore', 0)
        result["raw_mp_restore"] = getattr(item, 'raw_mp_restore', 0)
    
    # Consumable 특수 속성 저장
    from src.equipment.item_system import Consumable
    if isinstance(item, Consumable):
        result["effect_type"] = getattr(item, 'effect_type', 'heal_hp')
        result["effect_value"] = getattr(item, 'effect_value', 0)
    
    return result


def serialize_dungeon(dungeon: Any) -> Dict[str, Any]:
    """던전 직렬화"""
    from src.world.tile import TileType

    # 타일 데이터 압축 (변경된 타일만 저장)
    tiles_data = []

    for y in range(dungeon.height):
        for x in range(dungeon.width):
            tile = dungeon.get_tile(x, y)

            # 기본 VOID 타일은 저장 안 함
            if tile.tile_type == TileType.VOID and not tile.explored:
                continue

            tiles_data.append({
                "x": x,
                "y": y,
                "type": tile.tile_type.value,
                "explored": tile.explored,
                "visible": tile.visible,
                "locked": tile.locked,
                "key_id": tile.key_id,
                "trap_damage": tile.trap_damage,
                "teleport_target": tile.teleport_target,
                "loot_id": tile.loot_id,
                "ingredient_id": tile.ingredient_id,
                "harvested": tile.harvested
            })

    # 채집 오브젝트 직렬화
    harvestables_data = []
    if hasattr(dungeon, 'harvestables'):
        for harvestable in dungeon.harvestables:
            harvestables_data.append({
                "object_type": harvestable.object_type.value,
                "x": harvestable.x,
                "y": harvestable.y,
                "harvested": harvestable.harvested
            })

    return {
        "width": dungeon.width,
        "height": dungeon.height,
        "tiles": tiles_data,
        "stairs_up": dungeon.stairs_up,
        "stairs_down": dungeon.stairs_down,
        "keys": dungeon.keys,
        "locked_doors": dungeon.locked_doors,
        "teleporters": {str(k): v for k, v in dungeon.teleporters.items()},  # Tuple key를 문자열로
        "harvestables": harvestables_data,  # 채집 오브젝트 추가
    }


def serialize_game_state(
    party: List[Any],
    floor_number: int,
    dungeon: Any,
    player_x: int,
    player_y: int,
    inventory: List[Any],
    player_keys: List[str],
    traits: List[Any],
    passives: List[Any],
    difficulty: Optional[str] = None
) -> Dict[str, Any]:
    """전체 게임 상태 직렬화"""

    # 파티
    party_data = [serialize_party_member(member) for member in party]

    # 던전
    dungeon_data = serialize_dungeon(dungeon)

    # 인벤토리
    inventory_data = [serialize_item(item) for item in inventory]

    # 특성
    traits_data = []
    for trait_selection in traits:
        traits_data.append({
            "character_name": trait_selection.character_name,
            "job_name": trait_selection.job_name,
            "selected_traits": [
                {"id": t.id, "name": t.name, "description": t.description, "type": t.type}
                for t in trait_selection.selected_traits
            ]
        })

    # 패시브
    passives_data = [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "cost": p.cost,
            "effects": p.effects
        }
        for p in passives
    ]

    return {
        "party": party_data,
        "floor_number": floor_number,
        "dungeon": dungeon_data,
        "player_position": {"x": player_x, "y": player_y},
        "inventory": inventory_data,
        "keys": player_keys,
        "traits": traits_data,
        "passives": passives_data,
        "difficulty": difficulty if difficulty else "보통",  # 난이도 추가
    }


def deserialize_dungeon(dungeon_data: Dict[str, Any]) -> Any:
    """던전 역직렬화"""
    from src.world.dungeon_generator import DungeonMap
    from src.world.tile import TileType
    from src.gathering.harvestable import HarvestableObject, HarvestableType

    dungeon = DungeonMap(dungeon_data["width"], dungeon_data["height"])

    # 타일 복원
    for tile_data in dungeon_data["tiles"]:
        x, y = tile_data["x"], tile_data["y"]
        tile_type = TileType(tile_data["type"])

        dungeon.set_tile(
            x, y, tile_type,
            locked=tile_data.get("locked", False),
            key_id=tile_data.get("key_id"),
            trap_damage=tile_data.get("trap_damage", 0),
            teleport_target=tuple(tile_data["teleport_target"]) if tile_data.get("teleport_target") else None,
            loot_id=tile_data.get("loot_id")
        )

        tile = dungeon.get_tile(x, y)
        tile.explored = tile_data.get("explored", False)
        tile.visible = tile_data.get("visible", False)
        tile.ingredient_id = tile_data.get("ingredient_id")
        tile.harvested = tile_data.get("harvested", False)

    # 계단, 열쇠, 문 복원
    dungeon.stairs_up = tuple(dungeon_data["stairs_up"]) if dungeon_data.get("stairs_up") else None
    dungeon.stairs_down = tuple(dungeon_data["stairs_down"]) if dungeon_data.get("stairs_down") else None
    dungeon.keys = [tuple(k) if isinstance(k, list) else k for k in dungeon_data.get("keys", [])]
    dungeon.locked_doors = [tuple(d) if isinstance(d, list) else d for d in dungeon_data.get("locked_doors", [])]

    # 텔레포터 (문자열 키를 튜플로 변환)
    teleporters = {}
    for k_str, v in dungeon_data.get("teleporters", {}).items():
        key = eval(k_str)  # "(x, y)" 문자열을 튜플로
        teleporters[key] = tuple(v)
    dungeon.teleporters = teleporters

    # 채집 오브젝트 복원
    harvestables = []
    for harv_data in dungeon_data.get("harvestables", []):
        harvestable = HarvestableObject(
            object_type=HarvestableType(harv_data["object_type"]),
            x=harv_data["x"],
            y=harv_data["y"],
            harvested=harv_data.get("harvested", False)
        )
        harvestables.append(harvestable)
    dungeon.harvestables = harvestables

    logger.info(f"던전 복원 완료: {len(harvestables)}개의 채집 오브젝트 복원됨")

    return dungeon


def deserialize_item(item_data: Dict[str, Any]) -> Any:
    """아이템 역직렬화"""
    from src.equipment.item_system import (
        Item, Equipment, Consumable, ItemType, ItemRarity,
        EquipSlot, ItemAffix
    )
    from src.gathering.ingredient import Ingredient, IngredientCategory

    # 접사 복원
    affixes = []
    for affix_data in item_data.get("affixes", []):
        affixes.append(ItemAffix(
            id=affix_data["id"],
            name=affix_data["name"],
            stat=affix_data["stat"],
            value=affix_data["value"],
            is_percentage=affix_data["is_percentage"]
        ))

    # 타입 복원
    item_type = ItemType(item_data["item_type"])
    rarity = None
    for r in ItemRarity:
        if r.id == item_data["rarity"]:
            rarity = r
            break
    if not rarity:
        rarity = ItemRarity.COMMON

    weight = item_data.get("weight", 1.0)
    sell_price = item_data.get("sell_price", 0)

    # Ingredient 복원 (item_type이 MATERIAL이거나 ingredient_category 필드가 있으면)
    if item_type == ItemType.MATERIAL or item_data.get("ingredient_category"):
        # IngredientDatabase에서 기본 데이터 가져오기 (item_id로)
        from src.gathering.ingredient import IngredientDatabase
        ingredient_template = IngredientDatabase.get_ingredient(item_data["item_id"])
        
        # ingredient_category 필드가 있으면 그걸 우선 사용
        if item_data.get("ingredient_category"):
            category_value = item_data.get("ingredient_category", "filler")
            # IngredientCategory 찾기
            category = None
            for cat in IngredientCategory:
                if cat.value == category_value:
                    category = cat
                    break
            if not category:
                category = IngredientCategory.FILLER
        elif ingredient_template:
            # 템플릿에서 카테고리 가져오기
            category = ingredient_template.category
        else:
            category = IngredientCategory.FILLER
        
        # food_value 등도 템플릿에서 가져오되, 저장된 값이 있으면 그것 우선
        food_value = item_data.get("food_value", ingredient_template.food_value if ingredient_template else 1.0)
        freshness = item_data.get("freshness", ingredient_template.freshness if ingredient_template else 1.0)
        spoil_time = item_data.get("spoil_time", ingredient_template.spoil_time if ingredient_template else 0)
        edible_raw = item_data.get("edible_raw", ingredient_template.edible_raw if ingredient_template else False)
        raw_hp_restore = item_data.get("raw_hp_restore", ingredient_template.raw_hp_restore if ingredient_template else 0)
        raw_mp_restore = item_data.get("raw_mp_restore", ingredient_template.raw_mp_restore if ingredient_template else 0)
        
        return Ingredient(
            item_id=item_data["item_id"],
            name=item_data["name"],
            description=item_data["description"],
            item_type=item_type,
            rarity=rarity,
            level_requirement=item_data.get("level_requirement", 1),
            base_stats=item_data.get("base_stats", {}),
            affixes=affixes,
            unique_effect=item_data.get("unique_effect"),
            weight=weight,
            sell_price=sell_price,
            category=category,
            food_value=food_value,
            freshness=freshness,
            spoil_time=spoil_time,
            edible_raw=edible_raw,
            raw_hp_restore=raw_hp_restore,
            raw_mp_restore=raw_mp_restore
        )

    # 장비 vs 소비 아이템
    if item_type in [ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY]:
        equip_slot = EquipSlot(item_data["equip_slot"]) if item_data.get("equip_slot") else EquipSlot.WEAPON

        return Equipment(
            item_id=item_data["item_id"],
            name=item_data["name"],
            description=item_data["description"],
            item_type=item_type,
            rarity=rarity,
            level_requirement=item_data["level_requirement"],
            base_stats=item_data["base_stats"],
            affixes=affixes,
            unique_effect=item_data.get("unique_effect"),
            equip_slot=equip_slot,
            weight=weight,
            sell_price=sell_price
        )
    elif item_type == ItemType.CONSUMABLE or item_data.get("effect_type"):
        # Consumable 복원
        return Consumable(
            item_id=item_data["item_id"],
            name=item_data["name"],
            description=item_data["description"],
            item_type=item_type,
            rarity=rarity,
            level_requirement=item_data.get("level_requirement", 1),
            base_stats=item_data.get("base_stats", {}),
            affixes=affixes,
            unique_effect=item_data.get("unique_effect"),
            effect_type=item_data.get("effect_type", "heal_hp"),
            effect_value=item_data.get("effect_value", 0),
            weight=weight,
            sell_price=sell_price
        )
    else:
        return Item(
            item_id=item_data["item_id"],
            name=item_data["name"],
            description=item_data["description"],
            item_type=item_type,
            rarity=rarity,
            level_requirement=item_data.get("level_requirement", 1),
            base_stats=item_data.get("base_stats", {}),
            affixes=affixes,
            unique_effect=item_data.get("unique_effect"),
            weight=weight,
            sell_price=sell_price
        )


def deserialize_gimmick_state(character: Any, gimmick_state: Dict[str, Any]) -> None:
    """기믹 상태 역직렬화"""
    if not gimmick_state or not gimmick_state.get("gimmick_type"):
        return
    
    # 기믹 타입 확인
    gimmick_type = gimmick_state.get("gimmick_type")
    if not hasattr(character, 'gimmick_type') or character.gimmick_type != gimmick_type:
        logger.warning(f"기믹 타입 불일치: 저장된 {gimmick_type} vs 현재 {getattr(character, 'gimmick_type', None)}")
        return
    
    # 저장된 속성들을 복원
    for attr, value in gimmick_state.items():
        if attr == "gimmick_type":
            continue
        if hasattr(character, attr):
            setattr(character, attr, value)
            logger.debug(f"기믹 상태 복원: {character.name} - {attr} = {value}")


def deserialize_party_member(member_data: Dict[str, Any]) -> Any:
    """파티원 역직렬화"""
    from src.character.character import Character
    from src.character.stats import StatManager

    # 데이터 유효성 검사
    if not isinstance(member_data, dict):
        raise TypeError(f"member_data는 딕셔너리여야 합니다. 받은 타입: {type(member_data)}")

    required_fields = ["name", "character_class", "level"]
    missing_fields = [field for field in required_fields if field not in member_data]
    if missing_fields:
        raise KeyError(f"필수 필드 누락: {missing_fields}. 데이터: {member_data}")

    # Character 객체 생성
    char = Character(
        name=member_data["name"],
        character_class=member_data["character_class"],
        level=member_data["level"]
    )

    # 스탯 복원
    if member_data.get("stats"):
        char.stat_manager = StatManager.from_dict(member_data["stats"])

    # HP/MP 복원
    char.current_hp = member_data["current_hp"]
    char.current_mp = member_data["current_mp"]
    char.current_brv = member_data.get("current_brv", 0)

    # 경험치 복원
    char.experience = member_data.get("experience", 0)

    # 스킬 ID 복원
    if member_data.get("skill_ids"):
        char.skill_ids = member_data["skill_ids"]
        char._cached_skills = None  # 캐시 초기화

    # 특성 복원
    if member_data.get("active_traits"):
        char.active_traits = member_data["active_traits"]

    # active_buffs 복원 (요리 버프 포함)
    if member_data.get("active_buffs"):
        if not hasattr(char, 'active_buffs'):
            char.active_buffs = {}
        char.active_buffs = member_data["active_buffs"].copy()
        logger.debug(f"버프 복원: {char.name} - {len(char.active_buffs)}개 버프")

    # 기믹 상태 복원
    if member_data.get("gimmick_state"):
        deserialize_gimmick_state(char, member_data["gimmick_state"])

    # 장비 복원
    if member_data.get("equipment"):
        # equipment 속성이 없으면 생성
        if not hasattr(char, 'equipment'):
            char.equipment = {}

        for slot, item_data in member_data["equipment"].items():
            if item_data:
                try:
                    item = deserialize_item(item_data)
                    char.equipment[slot] = item
                    logger.debug(f"장비 복원: {char.name} - {slot} = {getattr(item, 'name', 'Unknown')}")
                except Exception as e:
                    logger.warning(f"장비 복원 실패: {char.name} - {slot}: {e}")
                    char.equipment[slot] = None
            else:
                char.equipment[slot] = None

    return char


def deserialize_inventory(inventory_data: Dict[str, Any], party: List[Any] = None) -> Any:
    """인벤토리 역직렬화"""
    from src.equipment.inventory import Inventory

    # 파티 정보와 함께 인벤토리 생성 (최대 무게 계산용)
    inventory = Inventory(base_weight=50.0, party=party)

    # 디버그: 인벤토리 데이터 확인
    logger.warning(f"[DESERIALIZE] inventory_data 타입: {type(inventory_data)}")
    logger.warning(f"[DESERIALIZE] inventory_data 내용: {inventory_data}")
    logger.warning(f"[DESERIALIZE] 골드 값: {inventory_data.get('gold', 0)}")

    # 골드 복원
    inventory.gold = inventory_data.get("gold", 0)

    # 요리 쿨타임 복원
    inventory.cooking_cooldown_turn = inventory_data.get("cooking_cooldown_turn", None)
    inventory.cooking_cooldown_duration = inventory_data.get("cooking_cooldown_duration", 0)

    # 아이템 복원
    for item_entry in inventory_data.get("items", []):
        # 새 형식: {"item": {...}, "quantity": ...} 또는 구형식: {...} (직접 item_data)
        if isinstance(item_entry, dict) and "item" in item_entry:
            # 새 형식: quantity 정보 포함
            item = deserialize_item(item_entry["item"])
            quantity = item_entry.get("quantity", 1)
            # add_item은 quantity를 지원하므로 한 번에 추가 (스택 가능한 아이템은 자동으로 스택됨)
            inventory.add_item(item, quantity=quantity)
        else:
            # 구형식: 직접 item_data (하위 호환성)
            item = deserialize_item(item_entry)
            inventory.add_item(item, quantity=1)

    logger.warning(f"[DESERIALIZE] 복원 후 인벤토리 골드: {inventory.gold}G")
    if inventory.cooking_cooldown_duration > 0:
        logger.warning(f"[DESERIALIZE] 요리 쿨타임 복원: {inventory.cooking_cooldown_duration}턴")

    return inventory
