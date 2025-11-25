"""
저장/로드 시스템

모든 게임 상태를 JSON으로 저장
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.SYSTEM)


class SaveSystem:
    """저장 시스템"""

    def __init__(self, save_directory: str = "saves"):
        self.save_dir = Path(save_directory)
        self.save_dir.mkdir(exist_ok=True)

    def save_game(self, save_name: str, game_state: Dict[str, Any], is_multiplayer: bool = False) -> bool:
        """
        게임 저장

        Args:
            save_name: 저장 파일 이름 (사용되지 않음, 게임 타입에 따라 자동 결정)
            game_state: 전체 게임 상태 딕셔너리
            is_multiplayer: 멀티플레이어 여부

        Returns:
            성공 여부
        """
        try:
            # 게임 타입에 따라 파일명 결정
            if is_multiplayer:
                save_filename = "save_multiplayer.json"
            else:
                save_filename = "save_single.json"
            
            save_path = self.save_dir / save_filename

            # 저장 시간 추가
            game_state["save_time"] = datetime.now().isoformat()
            game_state["version"] = "5.0.0"
            game_state["is_multiplayer"] = is_multiplayer
            
            # 마을 창고 아이템 저장 로그 (game_state에 town_manager가 포함된 경우)
            if "town_manager" in game_state:
                town_manager_data = game_state["town_manager"]
                if isinstance(town_manager_data, dict) and "storage_inventory" in town_manager_data:
                    storage_inventory = town_manager_data["storage_inventory"]
                    if storage_inventory:
                        logger.info(f"마을 창고 아이템 {len(storage_inventory)}개 저장됨:")
                        for item_data in storage_inventory:
                            item_name = item_data.get("name", item_data.get("item_id", "알 수 없는 아이템"))
                            logger.info(f"  - {item_name}")
                    else:
                        logger.info("마을 창고: 저장된 아이템 없음")
            
            # QuestManager 저장
            from src.quest.quest_manager import get_quest_manager
            game_state["quest_manager"] = get_quest_manager().to_dict()

            # JSON 직렬화 전에 모든 데이터 검증 및 정리
            cleaned_state = self._clean_for_json(game_state)

            # 같은 타입의 기존 파일 삭제 (최대 2개 유지)
            if save_path.exists():
                save_path.unlink()
                logger.info(f"기존 세이브 파일 삭제: {save_path}")

            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(cleaned_state, f, indent=2, ensure_ascii=False, default=self._json_default)

            logger.info(f"게임 저장 완료: {save_path} (타입: {'멀티플레이' if is_multiplayer else '싱글플레이'})")
            return True

        except Exception as e:
            logger.error(f"게임 저장 실패: {e}", exc_info=True)
            return False

    def _json_default(self, obj: Any) -> Any:
        """JSON 직렬화 불가능한 객체를 처리하는 기본 함수"""
        # StatusEffect 객체 처리 (먼저 체크)
        from src.combat.status_effects import StatusEffect
        if isinstance(obj, StatusEffect):
            logger.warning(f"StatusEffect 객체가 _json_default에서 발견됨 (이미 _clean_for_json에서 처리되어야 함): {obj.name}")
            return {
                "name": obj.name,
                "status_type": obj.status_type.value if hasattr(obj.status_type, 'value') else str(obj.status_type),
                "duration": obj.duration,
                "intensity": obj.intensity,
                "stack_count": obj.stack_count,
                "max_stacks": obj.max_stacks,
                "is_stackable": obj.is_stackable,
                "source_id": obj.source_id,
                "metadata": obj.metadata or {},
                "max_duration": getattr(obj, 'max_duration', obj.duration)
            }
        
        # Enum 처리
        if hasattr(obj, 'value'):
            return obj.value
        if hasattr(obj, 'name'):
            return obj.name
        # 그 외의 객체는 문자열로 변환
        logger.warning(f"JSON 직렬화 불가능한 객체 발견: {type(obj)}, 값: {obj}")
        return str(obj)

    def _clean_for_json(self, data: Any) -> Any:
        """JSON 직렬화를 위해 데이터 정리 (재귀적으로 모든 객체 검사)"""
        # StatusEffect 객체 처리 (먼저 체크)
        from src.combat.status_effects import StatusEffect
        if isinstance(data, StatusEffect):
            logger.debug(f"StatusEffect 객체 발견 및 직렬화: {data.name}")
            return {
                "name": data.name,
                "status_type": data.status_type.value if hasattr(data.status_type, 'value') else str(data.status_type),
                "duration": data.duration,
                "intensity": data.intensity,
                "stack_count": data.stack_count,
                "max_stacks": data.max_stacks,
                "is_stackable": data.is_stackable,
                "source_id": data.source_id,
                "metadata": data.metadata or {},
                "max_duration": getattr(data, 'max_duration', data.duration)
            }
        
        if isinstance(data, dict):
            return {k: self._clean_for_json(v) for k, v in data.items()}
        elif isinstance(data, (list, tuple)):
            return [self._clean_for_json(item) for item in data]
        elif isinstance(data, (str, int, float, bool, type(None))):
            return data
        elif hasattr(data, 'value'):  # Enum
            return data.value
        elif hasattr(data, 'name'):  # Enum 또는 다른 객체
            return data.name
        else:
            # 예상치 못한 객체 타입
            logger.warning(f"JSON 직렬화 전 정리 중 예상치 못한 타입: {type(data)}, 값: {data}")
            return str(data)

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
            
            # TownManager 복원
            if "town_manager" in game_state:
                from src.town.town_manager import TownManager, get_town_manager
                # 싱글톤 인스턴스 가져오기
                singleton_instance = get_town_manager()
                # 싱글톤 인스턴스에 로드된 데이터 적용
                loaded_data = game_state["town_manager"]
                if isinstance(loaded_data, dict):
                    # 기존 인스턴스의 속성을 로드된 데이터로 업데이트
                    singleton_instance.hub_storage = loaded_data.get("hub_storage", [])
                    singleton_instance.storage_inventory = loaded_data.get("storage_inventory", [])
                    singleton_instance.facilities = loaded_data.get("facilities", {})
                    logger.info(f"마을 데이터 복원 완료 - hub_storage: {len(singleton_instance.hub_storage)}개, storage_inventory: {len(singleton_instance.storage_inventory)}개")

                    # 마을 창고 아이템 로드 로그
                    storage_inventory = singleton_instance.get_storage_inventory()
                    if storage_inventory:
                        logger.info(f"마을 창고에서 불러온 아이템 {len(storage_inventory)}개:")
                        for item_data in storage_inventory:
                            item_name = item_data.get("name", item_data.get("item_id", "알 수 없는 아이템"))
                            logger.info(f"  - {item_name}")
                    else:
                        logger.info("마을 창고: 불러온 아이템 없음")
            
            # QuestManager 복원
            if "quest_manager" in game_state:
                from src.quest.quest_manager import get_quest_manager, QuestManager, _quest_manager
                # 전역 인스턴스를 로드된 매니저로 교체
                loaded_quest_manager = QuestManager.from_dict(game_state["quest_manager"])
                # 전역 인스턴스 직접 업데이트 (참조 교체)
                import src.quest.quest_manager as quest_module
                quest_module._quest_manager = loaded_quest_manager
                logger.info(f"퀘스트 데이터 복원 완료: 활성 {len(loaded_quest_manager.active_quests)}개, 가능 {len(loaded_quest_manager.available_quests)}개, 완료 {len(loaded_quest_manager.completed_quests)}개")
            
            return game_state

        except Exception as e:
            logger.error(f"게임 로드 실패: {e}")
            return None

    def list_saves(self) -> List[Dict[str, Any]]:
        """저장 파일 목록 (싱글플레이와 멀티플레이 구분)"""
        saves = []

        # 고정된 파일명 확인
        single_save = self.save_dir / "save_single.json"
        multiplayer_save = self.save_dir / "save_multiplayer.json"

        for save_file in [single_save, multiplayer_save]:
            if not save_file.exists():
                continue

            try:
                with open(save_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 게임 세이브 파일인지 확인 (party 키가 있어야 함)
                if "party" not in data:
                    logger.debug(f"게임 세이브 파일이 아님: {save_file.name}")
                    continue

                is_multiplayer = data.get("is_multiplayer", False)
                save_type = "멀티플레이" if is_multiplayer else "싱글플레이"

                saves.append({
                    "name": save_file.stem,
                    "save_time": data.get("save_time", "Unknown"),
                    "floor": data.get("floor_number", 1),
                    "max_floor_reached": data.get("max_floor_reached", data.get("floor_number", 1)),
                    "party_size": len(data.get("party", [])),
                    "is_multiplayer": is_multiplayer,
                    "save_type": save_type
                })

            except Exception as e:
                logger.warning(f"저장 파일 읽기 실패: {save_file}, {e}")

        return sorted(saves, key=lambda x: x["save_time"], reverse=True)

    def delete_save(self, save_name: str) -> bool:
        """저장 파일 삭제"""
        try:
            # save_name이 "save_single" 또는 "save_multiplayer"인 경우 직접 처리
            if save_name == "save_single" or save_name == "save_multiplayer":
                save_path = self.save_dir / f"{save_name}.json"
            else:
                save_path = self.save_dir / f"{save_name}.json"
            
            if save_path.exists():
                save_path.unlink()
                logger.info(f"저장 파일 삭제: {save_path}")
                return True
            return False

        except Exception as e:
            logger.error(f"저장 파일 삭제 실패: {e}")
            return False
    
    def delete_save_by_type(self, is_multiplayer: bool) -> bool:
        """
        게임 타입에 따라 세이브 파일 삭제
        
        Args:
            is_multiplayer: 멀티플레이어 여부
            
        Returns:
            삭제 성공 여부
        """
        try:
            if is_multiplayer:
                save_path = self.save_dir / "save_multiplayer.json"
            else:
                save_path = self.save_dir / "save_single.json"
            
            if save_path.exists():
                save_path.unlink()
                logger.info(f"세이브 파일 삭제: {save_path} (타입: {'멀티플레이' if is_multiplayer else '싱글플레이'})")
                return True
            return False

        except Exception as e:
            logger.error(f"세이브 파일 삭제 실패: {e}")
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


def serialize_status_effects(status_effects: List[Any]) -> List[Dict[str, Any]]:
    """StatusEffect 리스트 직렬화"""
    from src.combat.status_effects import StatusEffect
    
    serialized = []
    for effect in status_effects:
        if isinstance(effect, StatusEffect):
            serialized.append({
                "name": effect.name,
                "status_type": effect.status_type.value if hasattr(effect.status_type, 'value') else str(effect.status_type),
                "duration": effect.duration,
                "intensity": effect.intensity,
                "stack_count": effect.stack_count,
                "max_stacks": effect.max_stacks,
                "is_stackable": effect.is_stackable,
                "source_id": effect.source_id,
                "metadata": effect.metadata or {},
                "max_duration": getattr(effect, 'max_duration', effect.duration)
            })
    return serialized


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
    
    # status_effects 직렬화
    status_effects_data = []
    # status_manager의 status_effects를 우선 확인 (실제 데이터 소스)
    if hasattr(member, 'status_manager') and hasattr(member.status_manager, 'status_effects'):
        status_effects_data = serialize_status_effects(member.status_manager.status_effects)
    elif hasattr(member, 'status_effects') and member.status_effects:
        status_effects_data = serialize_status_effects(member.status_effects)
    
    result = {
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
        "status_effects": status_effects_data,
        "skill_ids": getattr(member, 'skill_ids', []),
        "active_traits": getattr(member, 'active_traits', []),
        "active_buffs": active_buffs_data,  # 요리 버프 포함
        "gimmick_state": gimmick_state,
    }
    
    # 멀티플레이: player_id 저장
    if hasattr(member, 'player_id') and member.player_id:
        result["player_id"] = member.player_id
    
    return result


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
        "charge_system": ["charge_gauge", "max_charge"],
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
            # JSON 직렬화 가능한 타입만 저장
            if isinstance(value, (str, int, float, bool, type(None), list, dict)):
                gimmick_state[attr] = value
            else:
                # Enum 등은 문자열로 변환
                if hasattr(value, 'value'):
                    gimmick_state[attr] = value.value
                elif hasattr(value, 'name'):
                    gimmick_state[attr] = value.name
                else:
                    gimmick_state[attr] = str(value)
                    logger.warning(f"기믹 속성 {attr}를 문자열로 변환: {type(value)}")
    
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
        "sell_price": getattr(item, 'sell_price', 0),
        "max_durability": getattr(item, 'max_durability', 100),
        "current_durability": getattr(item, 'current_durability', 100)
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
    
    # CookedFood 특수 속성 저장 (Item의 서브클래스가 아니므로 먼저 체크)
    from src.cooking.recipe import CookedFood
    if isinstance(item, CookedFood):
        # CookedFood는 Item의 서브클래스가 아니므로 기본 속성도 직접 설정
        result["item_id"] = getattr(item, 'name', 'cooked_food')  # 이름을 ID로 사용
        result["name"] = getattr(item, 'name', '요리된 음식')
        result["description"] = getattr(item, 'description', '')
        result["item_type"] = 'consumable'  # 소비 아이템으로 분류
        result["rarity"] = 'common'
        result["is_cooked_food"] = True
        result["hp_restore"] = getattr(item, 'hp_restore', 0)
        result["mp_restore"] = getattr(item, 'mp_restore', 0)
        result["max_hp_bonus"] = getattr(item, 'max_hp_bonus', 0)
        result["max_mp_bonus"] = getattr(item, 'max_mp_bonus', 0)
        result["buff_duration"] = getattr(item, 'buff_duration', 0)
        result["buff_type"] = getattr(item, 'buff_type', None)
        result["is_poison"] = getattr(item, 'is_poison', False)
        result["poison_damage"] = getattr(item, 'poison_damage', 0)
        result["spoil_time"] = getattr(item, 'spoil_time', 200)
        result["weight"] = getattr(item, 'weight', 0.5)
        return result  # CookedFood는 여기서 반환
    
    return result


def serialize_dungeon(dungeon: Any, enemies: List[Any] = None) -> Dict[str, Any]:
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
            harvestable_dict = {
                "object_type": harvestable.object_type.value,
                "x": harvestable.x,
                "y": harvestable.y,
                "harvested": harvestable.harvested  # 싱글플레이 호환성
            }
            # 멀티플레이: 플레이어별 채집 상태 저장
            if hasattr(harvestable, 'harvested_by') and harvestable.harvested_by:
                harvestable_dict["harvested_by"] = list(harvestable.harvested_by)
            harvestables_data.append(harvestable_dict)

    # 적(enemies) 직렬화
    enemies_data = []
    if enemies:
        for enemy in enemies:
            enemy_data = {
                "x": enemy.x,
                "y": enemy.y,
                "level": enemy.level,
                "name": getattr(enemy, 'name', '적'),
                "is_boss": getattr(enemy, 'is_boss', False),
                "spawn_x": getattr(enemy, 'spawn_x', enemy.x),
                "spawn_y": getattr(enemy, 'spawn_y', enemy.y),
                "is_chasing": getattr(enemy, 'is_chasing', False),
                "chase_turns": getattr(enemy, 'chase_turns', 0),
                "max_chase_turns": getattr(enemy, 'max_chase_turns', 15),
                "max_chase_distance": getattr(enemy, 'max_chase_distance', 15),
                "detection_range": getattr(enemy, 'detection_range', 5)
            }
            # 적 ID 포함 (멀티플레이 동기화용)
            if hasattr(enemy, 'id') and enemy.id:
                enemy_data["id"] = enemy.id
            enemies_data.append(enemy_data)

    return {
        "width": dungeon.width,
        "height": dungeon.height,
        "tiles": tiles_data,
        "stairs_down": dungeon.stairs_down,
        "keys": dungeon.keys,
        "locked_doors": dungeon.locked_doors,
        "teleporters": {str(k): v for k, v in dungeon.teleporters.items()},  # Tuple key를 문자열로
        "harvestables": harvestables_data,  # 채집 오브젝트 추가
        "enemies": enemies_data,  # 적 추가
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
    difficulty: Optional[str] = None,
    exploration: Any = None,
    all_floors_dungeons: Dict[int, Any] = None,
    is_multiplayer: bool = False,
    session: Any = None,
    max_floor_reached: int = 1
) -> Dict[str, Any]:
    """전체 게임 상태 직렬화"""

    # 파티
    party_data = [serialize_party_member(member) for member in party]

    # 현재 층 던전 (적 포함)
    enemies = []
    if exploration and hasattr(exploration, 'enemies'):
        enemies = exploration.enemies
    
    dungeon_data = serialize_dungeon(dungeon, enemies=enemies)

    # 모든 층의 던전 상태 저장 (층별 던전 상태 유지)
    floors_data = {}
    if all_floors_dungeons:
        for floor_num, floor_dungeon_data in all_floors_dungeons.items():
            floors_data[floor_num] = floor_dungeon_data
    else:
        # 기존 방식: 현재 층만 저장
        floors_data[floor_number] = dungeon_data

    # 인벤토리 (딕셔너리 형식으로 저장)
    # inventory가 Inventory 객체인지 리스트인지 확인
    if hasattr(inventory, 'gold') and hasattr(inventory, 'slots'):
        # Inventory 객체인 경우
        items_list = []
        for slot in inventory.slots:
            # InventorySlot은 dataclass이므로 item과 quantity 속성 사용
            if slot and hasattr(slot, 'item'):
                # quantity 정보 포함하여 저장
                items_list.append({
                    "item": serialize_item(slot.item),
                    "quantity": getattr(slot, 'quantity', 1)
                })
        
        inventory_data = {
            "gold": getattr(inventory, 'gold', 0),
            "items": items_list,
            "cooking_cooldown_turn": getattr(inventory, 'cooking_cooldown_turn', None),
            "cooking_cooldown_duration": getattr(inventory, 'cooking_cooldown_duration', 0)
        }
    elif isinstance(inventory, list):
        # 리스트인 경우 (구버전 형식 - 하위 호환성)
        # 리스트의 각 항목이 아이템인지 확인
        items_list = []
        for item in inventory:
            if hasattr(item, 'item_id') or hasattr(item, 'name'):
                # 아이템 객체인 경우
                items_list.append({
                    "item": serialize_item(item),
                    "quantity": 1
                })
            elif isinstance(item, dict):
                # 이미 직렬화된 딕셔너리인 경우
                items_list.append(item)
        
        inventory_data = {
            "gold": 0,
            "items": items_list,
            "cooking_cooldown_turn": None,
            "cooking_cooldown_duration": 0
        }
    else:
        # 알 수 없는 형식
        inventory_data = {
            "gold": 0,
            "items": [],
            "cooking_cooldown_turn": None,
            "cooking_cooldown_duration": 0
        }

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

    # TownManager 저장 (exploration에서 우선 가져옴)
    town_manager_data = None
    if exploration and hasattr(exploration, 'town_manager') and exploration.town_manager:
        town_manager_data = exploration.town_manager.to_dict()
        logger.info(f"[DEBUG] 저장: exploration.town_manager 사용 (id: {id(exploration.town_manager)}, storage: {len(exploration.town_manager.get_storage_inventory())}개)")
    else:
        logger.warning("[DEBUG] 저장: exploration.town_manager 없음")
        # 폴백: 전역 town_manager
        from src.town.town_manager import get_town_manager
        global_tm = get_town_manager()
        if global_tm:
            town_manager_data = global_tm.to_dict()
            logger.info(f"[DEBUG] 저장: 전역 town_manager 사용 (id: {id(global_tm)}, storage: {len(global_tm.get_storage_inventory())}개)")
        else:
            logger.error("[DEBUG] 저장: 전역 town_manager도 없음")

    result = {
        "party": party_data,
        "floor_number": floor_number,
        "max_floor_reached": max_floor_reached,  # 최대 도달 층수
        "dungeon": dungeon_data,  # 현재 층 던전 (하위 호환성)
        "floors": floors_data,  # 모든 층의 던전 상태
        "player_position": {"x": player_x, "y": player_y},
        "inventory": inventory_data,
        "keys": player_keys,
        "traits": traits_data,
        "passives": passives_data,
        "difficulty": difficulty if difficulty else "보통",  # 난이도 추가
        "is_multiplayer": is_multiplayer,  # 멀티플레이어 여부
    }

    if town_manager_data:
        result["town_manager"] = town_manager_data
    
    # 멀티플레이: 세션 정보 저장 (플레이어 재할당용)
    if is_multiplayer and session:
        session_data = {
            "host_id": getattr(session, 'host_id', None),
            "max_players": getattr(session, 'max_players', 4),
            "players": []
        }
        
        # 각 플레이어 정보 저장 (player_id, player_name)
        if hasattr(session, 'players'):
            for player_id, player in session.players.items():
                if player:
                    session_data["players"].append({
                        "player_id": player_id,
                        "player_name": getattr(player, 'player_name', '플레이어'),
                        "x": getattr(player, 'x', 0),
                        "y": getattr(player, 'y', 0)
                    })
        
        result["session"] = session_data
        logger.debug(f"멀티플레이 세션 정보 저장: {len(session_data['players'])}명 플레이어")
    
    return result


def deserialize_dungeon(dungeon_data: Dict[str, Any]) -> Tuple[Any, List[Any]]:
    """던전 역직렬화 (던전과 적 리스트 반환)"""
    from src.world.dungeon_generator import DungeonMap
    from src.world.tile import TileType
    from src.gathering.harvestable import HarvestableObject, HarvestableType
    from src.world.exploration import Enemy

    dungeon = DungeonMap(dungeon_data["width"], dungeon_data["height"])

    # 타일 복원
    for tile_data in dungeon_data["tiles"]:
        x, y = tile_data["x"], tile_data["y"]
        tile_type = TileType(tile_data["type"])
        loot_id = tile_data.get("loot_id")

        # loot_id가 None이 아니면 아이템/상자가 있는 타일로 복원
        # (이미 주운 아이템은 loot_id가 None이므로 복원되지 않음)
        if loot_id and tile_type in [TileType.ITEM, TileType.CHEST]:
            # 아이템/상자 타일로 복원 (loot_id 포함)
            dungeon.set_tile(
                x, y, tile_type,
                locked=tile_data.get("locked", False),
                key_id=tile_data.get("key_id"),
                trap_damage=tile_data.get("trap_damage", 0),
                teleport_target=tuple(tile_data["teleport_target"]) if tile_data.get("teleport_target") else None,
                loot_id=loot_id
            )
        else:
            # 일반 타일로 복원 (아이템/상자는 이미 주운 것으로 간주)
            # 만약 원래 타입이 ITEM이나 CHEST였지만 loot_id가 None이면 FLOOR로 변경
            if tile_type in [TileType.ITEM, TileType.CHEST]:
                tile_type = TileType.FLOOR
            # BOSS_ROOM 타일은 FLOOR로 변경 (B 타일 제거 요청에 따라)
            elif tile_type == TileType.BOSS_ROOM:
                tile_type = TileType.FLOOR

            dungeon.set_tile(
                x, y, tile_type,
                locked=tile_data.get("locked", False),
                key_id=tile_data.get("key_id"),
                trap_damage=tile_data.get("trap_damage", 0),
                teleport_target=tuple(tile_data["teleport_target"]) if tile_data.get("teleport_target") else None,
                loot_id=None  # 아이템을 주웠으므로 loot_id는 None
            )

        tile = dungeon.get_tile(x, y)
        tile.explored = tile_data.get("explored", False)
        tile.visible = tile_data.get("visible", False)
        tile.ingredient_id = tile_data.get("ingredient_id")
        tile.harvested = tile_data.get("harvested", False)

    # 계단, 열쇠, 문 복원
    dungeon.stairs_down = tuple(dungeon_data["stairs_down"]) if dungeon_data.get("stairs_down") else None

    # 계단 위치에 STAIRS 타일 설정
    if dungeon.stairs_down:
        x, y = dungeon.stairs_down
        dungeon.set_tile(x, y, TileType.STAIRS_DOWN)
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
            harvested=harv_data.get("harvested", False)  # 싱글플레이 호환성
        )
        # 멀티플레이: 플레이어별 채집 상태 복원
        if "harvested_by" in harv_data:
            harvestable.harvested_by = set(harv_data["harvested_by"])
        harvestables.append(harvestable)
    dungeon.harvestables = harvestables

    # 적(enemies) 복원
    enemies = []
    for enemy_data in dungeon_data.get("enemies", []):
        enemy = Enemy(
            x=enemy_data["x"],
            y=enemy_data["y"],
            level=enemy_data.get("level", 1),
            name=enemy_data.get("name", "적"),
            is_boss=enemy_data.get("is_boss", False),
            id=enemy_data.get("id")  # 적 ID 복원 (멀티플레이 동기화용)
        )
        enemy.spawn_x = enemy_data.get("spawn_x", enemy.x)
        enemy.spawn_y = enemy_data.get("spawn_y", enemy.y)
        enemy.is_chasing = enemy_data.get("is_chasing", False)
        enemy.chase_turns = enemy_data.get("chase_turns", 0)
        enemy.max_chase_turns = enemy_data.get("max_chase_turns", 15)
        enemy.max_chase_distance = enemy_data.get("max_chase_distance", 15)
        enemy.detection_range = enemy_data.get("detection_range", 5)
        enemies.append(enemy)

    logger.info(f"던전 복원 완료: {len(harvestables)}개의 채집 오브젝트, {len(enemies)}마리의 적 복원됨")

    return dungeon, enemies


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
    max_durability = item_data.get("max_durability", 100)
    current_durability = item_data.get("current_durability", 100)

    # CookedFood 복원 (is_cooked_food 플래그가 있으면)
    if item_data.get("is_cooked_food"):
        from src.cooking.recipe import CookedFood
        return CookedFood(
            name=item_data["name"],
            description=item_data.get("description", ""),
            hp_restore=item_data.get("hp_restore", 0),
            mp_restore=item_data.get("mp_restore", 0),
            max_hp_bonus=item_data.get("max_hp_bonus", 0),
            max_mp_bonus=item_data.get("max_mp_bonus", 0),
            buff_duration=item_data.get("buff_duration", 0),
            buff_type=item_data.get("buff_type", None),
            is_poison=item_data.get("is_poison", False),
            poison_damage=item_data.get("poison_damage", 0),
            spoil_time=item_data.get("spoil_time", 200),
            weight=weight
        )

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
        
        ingredient = Ingredient(
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
        # 내구도 복원
        ingredient.max_durability = max_durability
        ingredient.current_durability = current_durability
        return ingredient

    # 장비 vs 소비 아이템
    if item_type in [ItemType.WEAPON, ItemType.ARMOR, ItemType.ACCESSORY]:
        # equip_slot 복원 (item_type에 따라 기본값 설정)
        equip_slot_value = item_data.get("equip_slot")
        if equip_slot_value:
            try:
                equip_slot = EquipSlot(equip_slot_value)
            except (ValueError, KeyError):
                # 잘못된 값이면 item_type에 따라 기본값 설정
                if item_type == ItemType.WEAPON:
                    equip_slot = EquipSlot.WEAPON
                elif item_type == ItemType.ARMOR:
                    equip_slot = EquipSlot.ARMOR
                else:  # ACCESSORY
                    equip_slot = EquipSlot.ACCESSORY
        else:
            # equip_slot이 없으면 item_type에 따라 기본값 설정
            if item_type == ItemType.WEAPON:
                equip_slot = EquipSlot.WEAPON
            elif item_type == ItemType.ARMOR:
                equip_slot = EquipSlot.ARMOR
            else:  # ACCESSORY
                equip_slot = EquipSlot.ACCESSORY

        equipment = Equipment(
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
        # 내구도 복원
        equipment.max_durability = max_durability
        equipment.current_durability = current_durability
        return equipment
    elif item_type == ItemType.CONSUMABLE or item_data.get("effect_type"):
        # Consumable 복원
        consumable = Consumable(
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
        # 내구도 복원
        consumable.max_durability = max_durability
        consumable.current_durability = current_durability
        return consumable
    else:
        item = Item(
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
        # 내구도 복원
        item.max_durability = max_durability
        item.current_durability = current_durability
        return item


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

    # status_effects 복원
    if member_data.get("status_effects"):
        deserialize_status_effects(char, member_data["status_effects"])

    # 기믹 상태 복원
    if member_data.get("gimmick_state"):
        deserialize_gimmick_state(char, member_data["gimmick_state"])
    
    # 멀티플레이: player_id 복원 (재할당 전 원래 값 저장용)
    if member_data.get("player_id"):
        char.player_id = member_data["player_id"]
        logger.debug(f"{char.name}의 원래 player_id 복원: {char.player_id}")

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

        # 장비 스탯 재적용 (equip_item 로직 사용)
        # StatManager는 이미 stats 데이터를 통해 복원되었지만, 장비 스탯은 별도로 재적용해야 함
        # 특히 퍼센트 옵션은 현재 최대 HP/MP를 기준으로 계산되므로 재적용 필요
        # 먼저 기존 장비 스탯을 제거 (중복 적용 방지)
        from src.character.stats import Stats
        # Stats는 enum이 아니라 클래스이므로 모든 스탯 속성을 리스트로 만듦
        all_stats = [
            Stats.HP, Stats.MP, Stats.INIT_BRV, Stats.MAX_BRV,
            Stats.STRENGTH, Stats.DEFENSE, Stats.MAGIC, Stats.SPIRIT,
            Stats.SPEED, Stats.LUCK, Stats.ACCURACY, Stats.EVASION,
            Stats.STAMINA, Stats.VITALITY, Stats.DEXTERITY, Stats.PERCEPTION,
            Stats.ENDURANCE, Stats.CHARISMA, Stats.CRIT_RATE, Stats.CRIT_DAMAGE
        ]
        for slot in char.equipment.keys():
            # 모든 가능한 스탯에 대해 장비 보너스 제거
            for stat_enum in all_stats:
                char.stat_manager.remove_bonus(stat_enum, f"equipment_{slot}")
                char.stat_manager.remove_bonus(stat_enum, f"equipment_{slot}_percent")
        
        # 이제 장비 스탯 재적용
        for slot, item in char.equipment.items():
            if item:
                # 장비 스탯 재적용 (equip_item의 스탯 적용 로직 사용)
                stat_mapping = {
                    "physical_attack": Stats.STRENGTH,
                    "physical_defense": Stats.DEFENSE,
                    "magic_attack": Stats.MAGIC,
                    "magic_defense": Stats.SPIRIT,
                    "hp": Stats.HP,
                    "max_hp": Stats.HP,
                    "mp": Stats.MP,
                    "max_mp": Stats.MP,
                    "speed": Stats.SPEED,
                    "accuracy": Stats.ACCURACY,
                    "evasion": Stats.EVASION,
                    "luck": Stats.LUCK,
                    "init_brv": Stats.INIT_BRV,
                    "max_brv": Stats.MAX_BRV,
                    "strength": Stats.STRENGTH,
                    "defense": Stats.DEFENSE,
                    "magic": Stats.MAGIC,
                    "spirit": Stats.SPIRIT,
                }
                
                # 장비 보너스 적용 (get_total_stats 메서드 사용)
                if hasattr(item, "get_total_stats"):
                    total_stats = item.get_total_stats()
                    # 현재 최대 HP/MP 값 (퍼센트 옵션 계산용) - 장비 스탯 제거 후 계산
                    current_max_hp = char.max_hp
                    current_max_mp = char.max_mp
                    
                    # 추가옵션(affixes)에서 퍼센트 옵션 확인
                    if hasattr(item, "affixes"):
                        for affix in item.affixes:
                            # 최대 HP % 증가 옵션 처리
                            if affix.is_percentage and affix.stat in ["max_hp", "hp", "max_hp_percent", "hp_percent"]:
                                actual_bonus = int(current_max_hp * affix.value)
                                mapped_stat = Stats.HP
                                char.stat_manager.add_bonus(mapped_stat, f"equipment_{slot}_percent", actual_bonus)
                                logger.debug(f"장비 스탯 재적용 (퍼센트): {char.name} - {affix.stat} ({affix.value*100}%) → {mapped_stat} +{actual_bonus} ({slot})")
                            # 최대 MP % 증가 옵션 처리
                            elif affix.is_percentage and affix.stat in ["max_mp", "mp", "max_mp_percent", "mp_percent"]:
                                actual_bonus = int(current_max_mp * affix.value)
                                mapped_stat = Stats.MP
                                char.stat_manager.add_bonus(mapped_stat, f"equipment_{slot}_percent", actual_bonus)
                                logger.debug(f"장비 스탯 재적용 (퍼센트): {char.name} - {affix.stat} ({affix.value*100}%) → {mapped_stat} +{actual_bonus} ({slot})")
                    
                    # 일반 스탯 적용 (퍼센트 옵션이 아닌 것들)
                    for stat_name, bonus in total_stats.items():
                        # 퍼센트 옵션은 이미 위에서 처리했으므로 스킵
                        if stat_name in ["max_hp_percent", "hp_percent", "max_mp_percent", "mp_percent"]:
                            continue
                        # 퍼센트 옵션이 기본 스탯에 없어서 그대로 들어간 경우도 스킵 (affixes에서 처리됨)
                        if hasattr(item, "affixes"):
                            skip = False
                            for affix in item.affixes:
                                if affix.is_percentage and affix.stat == stat_name and stat_name in ["max_hp", "hp", "max_mp", "mp"]:
                                    skip = True
                                    break
                            if skip:
                                continue
                        
                        mapped_stat = stat_mapping.get(stat_name, stat_name)
                        char.stat_manager.add_bonus(mapped_stat, f"equipment_{slot}", bonus)
                        logger.debug(f"장비 스탯 재적용: {char.name} - {stat_name} → {mapped_stat} +{bonus} ({slot})")
                elif hasattr(item, "stat_bonuses"):
                    # 구 방식 호환성 유지
                    for stat_name, bonus in item.stat_bonuses.items():
                        mapped_stat = stat_mapping.get(stat_name, stat_name)
                        char.stat_manager.add_bonus(mapped_stat, f"equipment_{slot}", bonus)
                
                # 장비 특수 효과 재적용 (Events.EQUIPMENT_EQUIPPED 발행)
                from src.core.event_bus import event_bus, Events
                event_bus.publish(Events.EQUIPMENT_EQUIPPED, {
                    "character": char,
                    "slot": slot,
                    "item": item
                })
                logger.debug(f"장비 특수 효과 재적용 이벤트 발행: {char.name} - {getattr(item, 'name', 'Unknown')}")

    return char


def deserialize_status_effects(character: Any, status_effects_data: List[Dict[str, Any]]) -> None:
    """StatusEffect 리스트 역직렬화"""
    from src.combat.status_effects import StatusEffect, StatusType
    
    if not hasattr(character, 'status_manager'):
        return
    
    # 기존 상태 효과 초기화
    character.status_manager.status_effects = []
    
    for effect_data in status_effects_data:
        try:
            # StatusType 찾기
            status_type_value = effect_data.get("status_type")
            status_type = None
            for st in StatusType:
                if st.value == status_type_value or str(st) == status_type_value:
                    status_type = st
                    break
            
            if status_type is None:
                logger.warning(f"알 수 없는 StatusType: {status_type_value}, 건너뜀")
                continue
            
            # StatusEffect 생성
            effect = StatusEffect(
                name=effect_data.get("name", "Unknown"),
                status_type=status_type,
                duration=effect_data.get("duration", 1),
                intensity=effect_data.get("intensity", 1.0),
                stack_count=effect_data.get("stack_count", 1),
                max_stacks=effect_data.get("max_stacks", 1),
                is_stackable=effect_data.get("is_stackable", False),
                source_id=effect_data.get("source_id"),
                metadata=effect_data.get("metadata", {})
            )
            
            # max_duration 복원
            if "max_duration" in effect_data:
                effect.max_duration = effect_data["max_duration"]
            
            character.status_manager.status_effects.append(effect)
        except Exception as e:
            logger.warning(f"StatusEffect 복원 실패: {e}, 데이터: {effect_data}")


def deserialize_inventory(inventory_data: Dict[str, Any], party: List[Any] = None) -> Any:
    """인벤토리 역직렬화"""
    from src.equipment.inventory import Inventory

    # 파티 정보와 함께 인벤토리 생성 (최대 무게 계산용)
    inventory = Inventory(base_weight=50.0, party=party)

    # 디버그: 인벤토리 데이터 확인
    logger.warning(f"[DESERIALIZE] inventory_data 타입: {type(inventory_data)}")
    logger.warning(f"[DESERIALIZE] inventory_data 내용: {inventory_data}")
    
    # inventory_data가 리스트인 경우 (구버전 형식) 새 형식으로 마이그레이션
    if isinstance(inventory_data, list):
        logger.warning(f"[DESERIALIZE] 구버전 리스트 형식 감지. 새 형식으로 마이그레이션합니다.")
        # 리스트의 각 항목을 새 형식으로 변환
        items_list = []
        for item_entry in inventory_data:
            if isinstance(item_entry, dict):
                # 이미 직렬화된 딕셔너리인 경우
                if "item" in item_entry:
                    # 새 형식 이미 ({"item": {...}, "quantity": ...})
                    items_list.append(item_entry)
                else:
                    # 구버전: 직접 item_data 딕셔너리
                    items_list.append({
                        "item": item_entry,
                        "quantity": 1
                    })
            else:
                # 아이템 객체인 경우 (역직렬화 시에는 발생하지 않아야 함, 안전장치)
                logger.warning(f"[DESERIALIZE] 리스트에 예상치 못한 타입 발견: {type(item_entry)}, 건너뜀")
        
        # 새 형식으로 마이그레이션
        inventory_data = {
            "gold": 0,
            "items": items_list,
            "cooking_cooldown_turn": None,
            "cooking_cooldown_duration": 0
        }
        logger.warning(f"[DESERIALIZE] 마이그레이션 완료: {len(items_list)}개 아이템 복원")
    
    # 딕셔너리가 아닌 경우도 처리
    if not isinstance(inventory_data, dict):
        logger.warning(f"[DESERIALIZE] inventory_data가 딕셔너리가 아닙니다 ({type(inventory_data)}). 빈 인벤토리로 초기화합니다.")
        inventory_data = {
            "gold": 0,
            "items": [],
            "cooking_cooldown_turn": None,
            "cooking_cooldown_duration": 0
        }
    
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
