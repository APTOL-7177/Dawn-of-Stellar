"""
인벤토리 시스템

아이템 저장, 관리, 사용
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from src.equipment.item_system import Item, Equipment, Consumable, ItemType, ItemRarity
from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.SYSTEM)


@dataclass
class InventorySlot:
    """인벤토리 슬롯"""
    item: Item
    quantity: int = 1


class Inventory:
    """
    인벤토리 시스템

    - 아이템 저장/관리 (무게 기반)
    - 골드 관리
    - 장비/소비 아이템 사용
    - 동적 무게 제한 (파티 스탯에 따라 변동)
    """

    def __init__(self, base_weight: float = 50.0, party: List[Any] = None):
        """
        Args:
            base_weight: 기본 무게 (kg)
            party: 파티 멤버 리스트 (스탯 계산용)
        """
        self.base_weight = base_weight
        self.party = party or []
        self.slots: List[InventorySlot] = []
        self.gold = 0

        logger.info(f"인벤토리 생성: 기본 무게 {base_weight}kg")

    @property
    def max_weight(self) -> float:
        """
        최대 무게 계산 (동적)

        계산 방식:
        - 기본 무게: 50kg
        - 파티원 1명당: +10kg
        - 힘(Strength) 1당: +0.5kg
        - 레벨 1당: +1kg
        """
        total = self.base_weight

        if self.party:
            # 파티원 수 보너스
            total += len(self.party) * 10.0

            # 파티원들의 힘 스탯 합계
            total_strength = 0
            total_level = 0

            for member in self.party:
                # 힘 스탯
                strength = getattr(member, 'strength', 0)
                total_strength += strength

                # 레벨
                level = getattr(member, 'level', 1)
                total_level += level

            # 힘 보너스: 1 STR = +0.5kg
            total += total_strength * 0.5

            # 레벨 보너스: 1 Level = +1kg
            total += total_level * 1.0

        return round(total, 1)

    @property
    def current_weight(self) -> float:
        """현재 총 무게"""
        total = 0.0
        for slot in self.slots:
            total += slot.item.weight * slot.quantity
        return round(total, 2)

    @property
    def is_full(self) -> bool:
        """인벤토리가 가득 찼는지 (무게 기준)"""
        return self.current_weight >= self.max_weight

    @property
    def remaining_weight(self) -> float:
        """남은 무게"""
        return round(max(0, self.max_weight - self.current_weight), 2)

    @property
    def weight_breakdown(self) -> Dict[str, float]:
        """무게 제한 세부 내역"""
        breakdown = {
            "base": self.base_weight,
            "party_count": 0.0,
            "strength_bonus": 0.0,
            "level_bonus": 0.0
        }

        if self.party:
            breakdown["party_count"] = len(self.party) * 10.0

            total_strength = sum(getattr(m, 'strength', 0) for m in self.party)
            breakdown["strength_bonus"] = total_strength * 0.5

            total_level = sum(getattr(m, 'level', 1) for m in self.party)
            breakdown["level_bonus"] = total_level * 1.0

        return breakdown

    def add_item(self, item: Item, quantity: int = 1) -> bool:
        """
        아이템 추가

        Args:
            item: 추가할 아이템
            quantity: 수량 (소비 아이템용)

        Returns:
            성공 여부
        """
        # 무게 체크
        item_weight = item.weight * quantity
        if self.current_weight + item_weight > self.max_weight:
            logger.warning(
                f"무게 초과! {item.name} x{quantity} ({item_weight}kg) 추가 실패. "
                f"현재: {self.current_weight}kg / 최대: {self.max_weight}kg"
            )
            return False

        # 소비 아이템은 스택 가능
        if isinstance(item, Consumable):
            # 같은 아이템이 있는지 확인
            for slot in self.slots:
                if isinstance(slot.item, Consumable) and slot.item.item_id == item.item_id:
                    slot.quantity += quantity
                    logger.info(
                        f"아이템 추가: {item.name} x{quantity} (총 {slot.quantity}개). "
                        f"무게: {self.current_weight}kg/{self.max_weight}kg"
                    )
                    return True

        # 새 슬롯 추가
        self.slots.append(InventorySlot(item, quantity))
        logger.info(
            f"아이템 추가: {item.name} x{quantity}. "
            f"무게: {self.current_weight}kg/{self.max_weight}kg"
        )
        return True

    def remove_item(self, slot_index: int, quantity: int = 1) -> Optional[Item]:
        """
        아이템 제거

        Args:
            slot_index: 슬롯 인덱스
            quantity: 제거할 수량

        Returns:
            제거된 아이템 (없으면 None)
        """
        if slot_index < 0 or slot_index >= len(self.slots):
            logger.warning(f"잘못된 슬롯 인덱스: {slot_index}")
            return None

        slot = self.slots[slot_index]

        # 소비 아이템은 수량 감소
        if isinstance(slot.item, Consumable):
            slot.quantity -= quantity

            if slot.quantity <= 0:
                # 수량이 0이 되면 슬롯 제거
                removed_item = slot.item
                self.slots.pop(slot_index)
                logger.info(f"아이템 제거: {removed_item.name}")
                return removed_item
            else:
                logger.info(f"아이템 사용: {slot.item.name} (남은 수량: {slot.quantity})")
                return slot.item
        else:
            # 장비는 슬롯 제거
            removed_item = slot.item
            self.slots.pop(slot_index)
            logger.info(f"아이템 제거: {removed_item.name}")
            return removed_item

    def get_item(self, slot_index: int) -> Optional[Item]:
        """슬롯의 아이템 가져오기 (제거하지 않음)"""
        if slot_index < 0 or slot_index >= len(self.slots):
            return None
        return self.slots[slot_index].item

    def get_slot(self, slot_index: int) -> Optional[InventorySlot]:
        """슬롯 가져오기"""
        if slot_index < 0 or slot_index >= len(self.slots):
            return None
        return self.slots[slot_index]

    def find_item_by_id(self, item_id: str) -> Optional[int]:
        """
        아이템 ID로 슬롯 찾기

        Args:
            item_id: 아이템 ID

        Returns:
            슬롯 인덱스 (없으면 None)
        """
        for i, slot in enumerate(self.slots):
            if slot.item.item_id == item_id:
                return i
        return None

    def add_gold(self, amount: int):
        """골드 추가"""
        self.gold += amount
        logger.info(f"골드 획득: +{amount} (총 {self.gold}G)")

    def remove_gold(self, amount: int) -> bool:
        """
        골드 소비

        Args:
            amount: 소비할 골드

        Returns:
            성공 여부
        """
        if self.gold >= amount:
            self.gold -= amount
            logger.info(f"골드 소비: -{amount} (남은 {self.gold}G)")
            return True

        logger.warning(f"골드 부족: {amount}G 필요, {self.gold}G 보유")
        return False

    def get_items_by_type(self, item_type: ItemType) -> List[int]:
        """
        타입별 아이템 슬롯 인덱스 가져오기

        Args:
            item_type: 아이템 타입

        Returns:
            슬롯 인덱스 리스트
        """
        indices = []
        for i, slot in enumerate(self.slots):
            if slot.item.item_type == item_type:
                indices.append(i)
        return indices

    def get_items_by_rarity(self, rarity: ItemRarity) -> List[int]:
        """
        등급별 아이템 슬롯 인덱스 가져오기

        Args:
            rarity: 아이템 등급

        Returns:
            슬롯 인덱스 리스트
        """
        indices = []
        for i, slot in enumerate(self.slots):
            if slot.item.rarity == rarity:
                indices.append(i)
        return indices

    def get_equipable_items(self, character: Any) -> List[int]:
        """
        캐릭터가 장착 가능한 장비 아이템 가져오기

        Args:
            character: 캐릭터

        Returns:
            슬롯 인덱스 리스트
        """
        indices = []
        char_level = getattr(character, 'level', 1)

        for i, slot in enumerate(self.slots):
            item = slot.item

            # 장비만
            if not isinstance(item, Equipment):
                continue

            # 레벨 요구사항 확인
            if item.level_requirement > char_level:
                continue

            indices.append(i)

        return indices

    def sort_by_rarity(self):
        """등급별로 정렬 (전설 → 일반)"""
        rarity_order = {
            ItemRarity.UNIQUE: 0,
            ItemRarity.LEGENDARY: 1,
            ItemRarity.EPIC: 2,
            ItemRarity.RARE: 3,
            ItemRarity.UNCOMMON: 4,
            ItemRarity.COMMON: 5
        }

        self.slots.sort(key=lambda s: rarity_order.get(s.item.rarity, 99))
        logger.debug("인벤토리 정렬: 등급순")

    def sort_by_type(self):
        """타입별로 정렬"""
        type_order = {
            ItemType.WEAPON: 0,
            ItemType.ARMOR: 1,
            ItemType.ACCESSORY: 2,
            ItemType.CONSUMABLE: 3,
            ItemType.MATERIAL: 4,
            ItemType.KEY_ITEM: 5
        }

        self.slots.sort(key=lambda s: type_order.get(s.item.item_type, 99))
        logger.debug("인벤토리 정렬: 타입순")

    def sort_by_name(self):
        """이름별로 정렬"""
        self.slots.sort(key=lambda s: s.item.name)
        logger.debug("인벤토리 정렬: 이름순")

    def use_consumable(
        self,
        slot_index: int,
        target: Any
    ) -> bool:
        """
        소비 아이템 사용

        Args:
            slot_index: 슬롯 인덱스
            target: 대상 캐릭터

        Returns:
            성공 여부
        """
        slot = self.get_slot(slot_index)
        if not slot:
            return False

        item = slot.item
        if not isinstance(item, Consumable):
            logger.warning(f"{item.name}은(는) 소비 아이템이 아닙니다")
            return False

        # 효과 적용
        success = False
        effect_type = item.effect_type
        effect_value = item.effect_value

        if effect_type == "heal_hp":
            # HP 회복
            healed = target.heal(effect_value)
            if healed > 0:
                logger.info(f"{target.name}: {item.name} 사용 → HP +{healed}")
                success = True
        elif effect_type == "heal_mp":
            # MP 회복
            restored = target.restore_mp(effect_value)
            if restored > 0:
                logger.info(f"{target.name}: {item.name} 사용 → MP +{restored}")
                success = True
        elif effect_type == "heal_both":
            # HP/MP 모두 회복
            healed = target.heal(effect_value)
            restored = target.restore_mp(effect_value)
            if healed > 0 or restored > 0:
                logger.info(f"{target.name}: {item.name} 사용 → HP +{healed}, MP +{restored}")
                success = True
        elif effect_type == "revive":
            # 부활
            if not getattr(target, 'is_alive', True):
                target.is_alive = True
                target.current_hp = effect_value
                logger.info(f"{target.name}: {item.name} 사용 → 부활! HP {effect_value}")
                success = True
        elif effect_type == "cure_status":
            # 상태이상 치료
            if hasattr(target, 'status_effects'):
                target.status_effects.clear()
                logger.info(f"{target.name}: {item.name} 사용 → 상태이상 치료")
                success = True

        # 사용 성공 시 아이템 제거
        if success:
            self.remove_item(slot_index, 1)

        return success

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (저장용)"""
        from src.persistence.save_system import serialize_item

        slots_data = []
        for slot in self.slots:
            slots_data.append({
                "item": serialize_item(slot.item),
                "quantity": slot.quantity
            })

        return {
            "base_weight": self.base_weight,
            "slots": slots_data,
            "gold": self.gold
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], party: List[Any] = None) -> "Inventory":
        """딕셔너리에서 복원"""
        from src.persistence.save_system import deserialize_item

        # 하위 호환성: max_weight 필드가 있으면 base_weight로 변환
        base_weight = data.get("base_weight", data.get("max_weight", 50.0))

        inventory = cls(base_weight=base_weight, party=party)
        inventory.gold = data.get("gold", 0)

        for slot_data in data.get("slots", []):
            item = deserialize_item(slot_data["item"])
            quantity = slot_data.get("quantity", 1)
            inventory.slots.append(InventorySlot(item, quantity))

        logger.info(f"인벤토리 로드: {len(inventory.slots)}개 아이템, {inventory.gold}G, {inventory.current_weight}kg/{inventory.max_weight}kg")
        return inventory

    def __len__(self) -> int:
        """아이템 개수"""
        return len(self.slots)

    def __repr__(self) -> str:
        return f"Inventory({len(self.slots)} items, {self.current_weight}kg/{self.max_weight}kg, {self.gold}G)"
