"""
파티 강화 업그레이드 적용 시스템

메타 진행에서 구매한 영구 업그레이드를 게임에 적용합니다.
멀티플레이에서는 호스트의 메타 진행 기준으로 적용됩니다.
"""

from typing import List, Optional, Dict, Any
from src.persistence.meta_progress import MetaProgress, get_meta_progress
from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.CHARACTER)


class UpgradeApplier:
    """파티 강화 업그레이드 적용 시스템"""
    
    # 업그레이드 ID 매핑 (ShopItem의 item_id 자동 생성 규칙에 따라)
    # "HP 증가 I" -> "hp_증가_i" (ShopItem의 __init__에서 자동 생성)
    # 실제 item_id는 한글이 포함될 수 있으므로 직접 매칭
    
    @staticmethod
    def apply_to_characters(
        characters: List[Any],
        meta_progress: Optional[MetaProgress] = None,
        is_host: bool = True
    ) -> Dict[str, Any]:
        """
        캐릭터들에게 업그레이드 적용 (HP/MP 증가)
        
        Args:
            characters: 적용할 캐릭터 리스트
            meta_progress: 메타 진행 상태 (None이면 자동 로드)
            is_host: 호스트 여부 (멀티플레이에서 호스트 기준 적용)
        
        Returns:
            적용된 업그레이드 정보
        """
        if meta_progress is None:
            meta_progress = get_meta_progress()
        
        applied_upgrades = {
            "hp_multiplier": 1.0,
            "mp_multiplier": 1.0,
            "exp_multiplier": 1.0,
            "gold_multiplier": 1.0,
            "inventory_weight_bonus": 0
        }
        
        # HP 증가 업그레이드 확인 (II가 있으면 II를 사용, 그렇지 않으면 I)
        hp_boost_2_id = UpgradeApplier._find_upgrade_id("HP 증가 II", meta_progress)
        hp_boost_1_id = UpgradeApplier._find_upgrade_id("HP 증가 I", meta_progress)
        
        if hp_boost_2_id and meta_progress.is_upgrade_purchased(hp_boost_2_id):
            applied_upgrades["hp_multiplier"] = 1.2
            logger.info("업그레이드 적용: HP 증가 II (+20%)")
        elif hp_boost_1_id and meta_progress.is_upgrade_purchased(hp_boost_1_id):
            applied_upgrades["hp_multiplier"] = 1.1
            logger.info("업그레이드 적용: HP 증가 I (+10%)")
        
        # MP 증가 업그레이드 확인 (II가 있으면 II를 사용, 그렇지 않으면 I)
        mp_boost_2_id = UpgradeApplier._find_upgrade_id("MP 증가 II", meta_progress)
        mp_boost_1_id = UpgradeApplier._find_upgrade_id("MP 증가 I", meta_progress)
        
        if mp_boost_2_id and meta_progress.is_upgrade_purchased(mp_boost_2_id):
            applied_upgrades["mp_multiplier"] = 1.2
            logger.info("업그레이드 적용: MP 증가 II (+20%)")
        elif mp_boost_1_id and meta_progress.is_upgrade_purchased(mp_boost_1_id):
            applied_upgrades["mp_multiplier"] = 1.1
            logger.info("업그레이드 적용: MP 증가 I (+10%)")
        
        # 캐릭터들에게 HP/MP 증가 적용
        if applied_upgrades["hp_multiplier"] > 1.0 or applied_upgrades["mp_multiplier"] > 1.0:
            for character in characters:
                if applied_upgrades["hp_multiplier"] > 1.0:
                    old_max_hp = character.max_hp
                    character.max_hp = int(character.max_hp * applied_upgrades["hp_multiplier"])
                    character.current_hp = int(character.current_hp * applied_upgrades["hp_multiplier"])
                    logger.debug(f"{character.name} HP 증가: {old_max_hp} -> {character.max_hp}")
                
                if applied_upgrades["mp_multiplier"] > 1.0:
                    old_max_mp = character.max_mp
                    character.max_mp = int(character.max_mp * applied_upgrades["mp_multiplier"])
                    character.current_mp = int(character.current_mp * applied_upgrades["mp_multiplier"])
                    logger.debug(f"{character.name} MP 증가: {old_max_mp} -> {character.max_mp}")
        
        return applied_upgrades
    
    @staticmethod
    def get_experience_multiplier(
        meta_progress: Optional[MetaProgress] = None,
        is_host: bool = True
    ) -> float:
        """
        경험치 획득 배율 반환
        
        Args:
            meta_progress: 메타 진행 상태 (None이면 자동 로드)
            is_host: 호스트 여부 (멀티플레이에서 호스트 기준 적용)
        
        Returns:
            경험치 배율 (기본 1.0)
        """
        if meta_progress is None:
            meta_progress = get_meta_progress()
        
        multiplier = 1.0
        
        # 경험치 부스트 확인 (II가 있으면 II를 사용, 그렇지 않으면 I)
        exp_boost_2_id = UpgradeApplier._find_upgrade_id("경험치 부스트 II", meta_progress)
        exp_boost_1_id = UpgradeApplier._find_upgrade_id("경험치 부스트 I", meta_progress)
        
        if exp_boost_2_id and meta_progress.is_upgrade_purchased(exp_boost_2_id):
            multiplier = 1.25
            logger.debug("업그레이드 적용: 경험치 부스트 II (+25%)")
        elif exp_boost_1_id and meta_progress.is_upgrade_purchased(exp_boost_1_id):
            multiplier = 1.1
            logger.debug("업그레이드 적용: 경험치 부스트 I (+10%)")
        
        return multiplier
    
    @staticmethod
    def get_gold_multiplier(
        meta_progress: Optional[MetaProgress] = None,
        is_host: bool = True
    ) -> float:
        """
        골드 획득 배율 반환
        
        Args:
            meta_progress: 메타 진행 상태 (None이면 자동 로드)
            is_host: 호스트 여부 (멀티플레이에서 호스트 기준 적용)
        
        Returns:
            골드 배율 (기본 1.0)
        """
        if meta_progress is None:
            meta_progress = get_meta_progress()
        
        multiplier = 1.0
        
        # 골드 부스트 확인
        gold_boost_id = UpgradeApplier._find_upgrade_id("골드 부스트", meta_progress)
        if gold_boost_id and meta_progress.is_upgrade_purchased(gold_boost_id):
            multiplier = 1.2
            logger.debug("업그레이드 적용: 골드 부스트 (+20%)")
        
        return multiplier
    
    @staticmethod
    def get_inventory_weight_bonus(
        meta_progress: Optional[MetaProgress] = None,
        is_host: bool = True
    ) -> int:
        """
        인벤토리 무게 제한 보너스 반환
        
        Args:
            meta_progress: 메타 진행 상태 (None이면 자동 로드)
            is_host: 호스트 여부 (멀티플레이에서 호스트 기준 적용)
        
        Returns:
            무게 제한 보너스 (kg)
        """
        if meta_progress is None:
            meta_progress = get_meta_progress()
        
        bonus = 0
        
        # 인벤토리 확장 I 확인
        inventory_expand_1_id = UpgradeApplier._find_upgrade_id("인벤토리 확장 I", meta_progress)
        if inventory_expand_1_id and meta_progress.is_upgrade_purchased(inventory_expand_1_id):
            bonus = 20
            logger.debug("업그레이드 적용: 인벤토리 확장 I (+20kg)")
        
        return bonus
    
    @staticmethod
    def _find_upgrade_id(name_pattern: str, meta_progress: MetaProgress) -> Optional[str]:
        """
        업그레이드 ID 찾기 (ShopItem의 item_id 자동 생성 규칙 고려)
        
        ShopItem의 item_id는 이름에서 자동 생성됩니다:
        - "HP 증가 I" -> "hp_증가_i"
        - "경험치 부스트 I" -> "경험치_부스트_i"
        
        Args:
            name_pattern: 업그레이드 이름 패턴 (예: "HP 증가 I", "경험치 부스트 I")
            meta_progress: 메타 진행 상태
        
        Returns:
            실제 item_id (없으면 None)
        """
        # purchased_upgrades에서 직접 검색 (한글 포함 가능)
        for upgrade_id in meta_progress.purchased_upgrades:
            # 이름 패턴과 매칭되는지 확인 (대소문자 무시, 공백/괄호 무시)
            normalized_upgrade_id = upgrade_id.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("_", "")
            normalized_pattern = name_pattern.lower().replace(" ", "").replace("(", "").replace(")", "").replace("_", "").replace("i", "1").replace("ii", "2")
            
            # 패턴이 포함되어 있는지 확인
            if normalized_pattern in normalized_upgrade_id or normalized_upgrade_id in normalized_pattern:
                return upgrade_id
        
        return None
    
    @staticmethod
    def give_starting_equipment(
        characters: List[Any],
        meta_progress: Optional[MetaProgress] = None,
        is_host: bool = True
    ) -> None:
        """
        캐릭터들에게 시작 장비 지급
        
        대장간 레벨에 따라 시작 장비 등급이 결정됩니다:
        - Lv 1: 기본 장비 (COMMON)
        - Lv 2~3: 일반 장비 (COMMON)
        - Lv 4: 고급 장비 (UNCOMMON)
        
        Args:
            characters: 장비를 지급할 캐릭터 리스트
            meta_progress: 메타 진행 상태 (None이면 자동 로드)
            is_host: 호스트 여부 (멀티플레이에서 호스트 기준 적용)
        """
        if meta_progress is None:
            meta_progress = get_meta_progress()
        
        # 대장간 레벨 확인
        blacksmith_level = meta_progress.get_facility_level("blacksmith")
        
        # 대장간 레벨에 따른 장비 등급 결정
        if blacksmith_level >= 4:
            target_rarity = "uncommon"
        else:
            target_rarity = "common"
        
        from src.equipment.item_system import (
            ItemGenerator, ItemRarity, Equipment
        )
        from src.character.character_loader import load_character_data
        
        # 역할군별 시작 장비 매핑 (무기, 방어구, 악세서리)
        STARTING_EQUIPMENT_BY_ARCHETYPE = {
            # 물리 딜러
            "물리 딜러": ("iron_sword", "leather_armor", "health_ring"),
            "물리 딜러/탱커": ("iron_sword", "leather_armor", "health_ring"),
            # 마법 딜러
            "마법 딜러": ("wooden_staff", "cloth_robe", "mana_ring"),
            # 하이브리드
            "하이브리드": ("iron_sword", "leather_armor", "ring_of_strength"),
            "하이브리드 딜러": ("iron_sword", "leather_armor", "ring_of_strength"),
            # 탱커
            "탱커": ("iron_sword", "leather_armor", "ring_of_protection"),
            "탱커/방어": ("iron_sword", "leather_armor", "ring_of_protection"),
            # 힐러/서포터
            "힐러": ("wooden_staff", "cloth_robe", "mana_ring"),
            "서포터": ("wooden_staff", "cloth_robe", "mana_ring"),
            "힐러/서포터": ("wooden_staff", "cloth_robe", "mana_ring"),
            # 특수 역할 (기본적으로 물리 딜러 장비)
            "특수": ("iron_sword", "leather_armor", "health_ring"),
        }
        
        # 등급 문자열을 ItemRarity로 변환
        rarity_map = {
            "common": ItemRarity.COMMON,
            "uncommon": ItemRarity.UNCOMMON
        }
        target_rarity_enum = rarity_map.get(target_rarity, ItemRarity.COMMON)
        
        for character in characters:
            # 캐릭터가 이미 장비를 가지고 있으면 스킵
            if (character.equipment.get("weapon") or 
                character.equipment.get("armor") or 
                character.equipment.get("accessory")):
                logger.debug(f"{character.name}은(는) 이미 장비를 가지고 있어 스킵")
                continue
            
            # 캐릭터 데이터 로드하여 아키타입 확인
            try:
                char_data = load_character_data(character.character_class)
                archetype = char_data.get("archetype", "특수")
            except Exception as e:
                logger.warning(f"{character.name}의 아키타입 로드 실패: {e}, 기본값 사용")
                archetype = "특수"
            
            # 역할군별 시작 장비 템플릿 ID 가져오기
            equipment_ids = STARTING_EQUIPMENT_BY_ARCHETYPE.get(archetype)
            if not equipment_ids:
                # 매핑에 없는 경우 기본값 사용
                equipment_ids = ("iron_sword", "leather_armor", "health_ring")
                logger.debug(f"{character.name}의 아키타입 '{archetype}'에 대한 매핑 없음, 기본 장비 사용")
            
            weapon_id, armor_id, accessory_id = equipment_ids
            
            # 시작 장비 생성 및 지급
            try:
                from src.equipment.item_system import WEAPON_TEMPLATES, ARMOR_TEMPLATES, ACCESSORY_TEMPLATES
                
                # 무기 생성
                if weapon_id in WEAPON_TEMPLATES:
                    weapon = ItemGenerator.create_weapon(weapon_id, add_random_affixes=True)
                else:
                    raise ValueError(f"무기 템플릿을 찾을 수 없음: {weapon_id}")
                
                weapon.rarity = target_rarity_enum
                weapon.weight = 0.1  # 무게 0.1kg
                weapon.max_durability = 100  # 내구도 100
                weapon.current_durability = 100
                # 랜덤 옵션 재생성 (등급에 맞게)
                weapon.affixes = ItemGenerator.generate_random_affixes(target_rarity_enum, 1)
                
                # 방어구 생성
                if armor_id in ARMOR_TEMPLATES:
                    armor = ItemGenerator.create_armor(armor_id, add_random_affixes=True)
                else:
                    raise ValueError(f"방어구 템플릿을 찾을 수 없음: {armor_id}")
                
                armor.rarity = target_rarity_enum
                armor.weight = 0.1
                armor.max_durability = 100
                armor.current_durability = 100
                armor.affixes = ItemGenerator.generate_random_affixes(target_rarity_enum, 1)
                
                # 악세서리 생성
                if accessory_id in ACCESSORY_TEMPLATES:
                    accessory = ItemGenerator.create_accessory(accessory_id, add_random_affixes=True)
                else:
                    raise ValueError(f"악세서리 템플릿을 찾을 수 없음: {accessory_id}")
                
                accessory.rarity = target_rarity_enum
                accessory.weight = 0.1
                accessory.max_durability = 100
                accessory.current_durability = 100
                accessory.affixes = ItemGenerator.generate_random_affixes(target_rarity_enum, 1)
                
                # 장비 장착
                character.equipment["weapon"] = weapon
                character.equipment["armor"] = armor
                character.equipment["accessory"] = accessory
                
                # 장비 스탯 적용
                character.update_equipment_stats("weapon")
                character.update_equipment_stats("armor")
                character.update_equipment_stats("accessory")
                
                logger.info(
                    f"{character.name} 시작 장비 지급: {weapon.name}, {armor.name}, {accessory.name} "
                    f"(등급: {target_rarity_enum.display_name}, 대장간 Lv.{blacksmith_level})"
                )
                
            except Exception as e:
                logger.error(f"{character.name} 시작 장비 지급 실패: {e}", exc_info=True)

