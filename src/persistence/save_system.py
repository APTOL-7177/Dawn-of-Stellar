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
            try:
                with open(save_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

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
    }


def serialize_equipment(member: Any) -> Dict[str, Any]:
    """장비 직렬화"""
    equipment = {}
    if hasattr(member, 'equipment'):
        for slot, item in member.equipment.items():
            if item:
                equipment[slot] = serialize_item(item)
    return equipment


def serialize_item(item: Any) -> Dict[str, Any]:
    """아이템 직렬화"""
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

    return {
        "item_id": item.item_id,
        "name": item.name,
        "description": item.description,
        "item_type": item.item_type.value if hasattr(item.item_type, 'value') else str(item.item_type),
        "rarity": item.rarity.id if hasattr(item.rarity, 'id') else str(item.rarity),
        "level_requirement": item.level_requirement,
        "base_stats": item.base_stats,
        "affixes": affixes,
        "unique_effect": getattr(item, 'unique_effect', None),
        "equip_slot": item.equip_slot.value if hasattr(item, 'equip_slot') and hasattr(item.equip_slot, 'value') else None
    }


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
                "loot_id": tile.loot_id
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
    passives: List[Any]
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
    }


def deserialize_dungeon(dungeon_data: Dict[str, Any]) -> Any:
    """던전 역직렬화"""
    from src.world.dungeon_generator import DungeonMap
    from src.world.tile import TileType

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

    return dungeon


def deserialize_item(item_data: Dict[str, Any]) -> Any:
    """아이템 역직렬화"""
    from src.equipment.item_system import (
        Item, Equipment, Consumable, ItemType, ItemRarity,
        EquipSlot, ItemAffix
    )

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
            equip_slot=equip_slot
        )
    else:
        return Item(
            item_id=item_data["item_id"],
            name=item_data["name"],
            description=item_data["description"],
            item_type=item_type,
            rarity=rarity,
            level_requirement=item_data["level_requirement"],
            base_stats=item_data["base_stats"],
            affixes=affixes,
            unique_effect=item_data.get("unique_effect")
        )


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

    # 아이템 복원
    for item_data in inventory_data.get("items", []):
        item = deserialize_item(item_data)
        inventory.add_item(item)

    logger.warning(f"[DESERIALIZE] 복원 후 인벤토리 골드: {inventory.gold}G")

    return inventory
