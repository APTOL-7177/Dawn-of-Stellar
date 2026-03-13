"""
행동 공간 인코더 - Flat Discrete(114) 행동 공간

행동 레이아웃:
    0-3:     BRV_ATTACK x 적 4슬롯
    4-7:     HP_ATTACK x 적 4슬롯
    8:       DEFEND
    9:       FLEE
    10-109:  SKILL(0~24) x 적/아군 4슬롯 (스킬 25개 * 타겟 4슬롯)
    110-113: ITEM(0~3) (자기 자신 대상)
"""

from typing import Dict, List, Optional, Any

import numpy as np

from src.core.logger import get_logger
from src.combat.combat_manager import ActionType

logger = get_logger("gym.action_space")

# 행동 공간 상수
_BRV_ATTACK_START = 0    # 0-3
_HP_ATTACK_START = 4     # 4-7
_DEFEND_ID = 8
_FLEE_ID = 9
_SKILL_START = 10        # 10-109 (스킬 0~24, 타겟 4슬롯씩)
_ITEM_START = 110        # 110-113 (아이템 0~3)
_NUM_TARGETS = 4
_NUM_SKILLS = 25
_NUM_ITEMS = 4


class ActionSpaceEncoder:
    """
    행동 공간 인코딩 (Flat Discrete 114)

    RL 에이전트의 이산 행동 인덱스를 전투 행동 딕셔너리로 변환하거나
    그 역방향 변환을 제공합니다.
    """

    NUM_ACTIONS = 114

    @staticmethod
    def decode(action_id: int, combat_manager: Any, current_char: Any) -> Dict:
        """
        action_id를 전투 행동 딕셔너리로 변환

        Args:
            action_id: 0~113 사이의 행동 인덱스
            combat_manager: CombatManager 인스턴스
            current_char: 현재 행동하는 캐릭터

        Returns:
            {"action_type": str, "target": Character|None, "skill": Skill|None, "item": Any|None}
        """
        enemies = [e for e in combat_manager.enemies if getattr(e, "is_alive", True)]
        allies = [a for a in combat_manager.allies if getattr(a, "is_alive", False)]

        # BRV_ATTACK (0-3)
        if _BRV_ATTACK_START <= action_id < _HP_ATTACK_START:
            target_idx = action_id - _BRV_ATTACK_START
            target = enemies[target_idx] if target_idx < len(enemies) else (enemies[0] if enemies else None)
            return {"action_type": ActionType.BRV_ATTACK.value, "target": target, "skill": None, "item": None}

        # HP_ATTACK (4-7)
        if _HP_ATTACK_START <= action_id < _DEFEND_ID:
            target_idx = action_id - _HP_ATTACK_START
            target = enemies[target_idx] if target_idx < len(enemies) else (enemies[0] if enemies else None)
            return {"action_type": ActionType.HP_ATTACK.value, "target": target, "skill": None, "item": None}

        # DEFEND (8)
        if action_id == _DEFEND_ID:
            return {"action_type": ActionType.DEFEND.value, "target": current_char, "skill": None, "item": None}

        # FLEE (9)
        if action_id == _FLEE_ID:
            return {"action_type": ActionType.FLEE.value, "target": None, "skill": None, "item": None}

        # SKILL (10-41)
        if _SKILL_START <= action_id < _ITEM_START:
            rel = action_id - _SKILL_START
            skill_idx = rel // _NUM_TARGETS
            target_idx = rel % _NUM_TARGETS

            skills = getattr(current_char, "skills", []) or []
            skill = skills[skill_idx] if skill_idx < len(skills) else None

            if skill is None:
                # 스킬 없으면 방어로 폴백
                return {"action_type": ActionType.DEFEND.value, "target": current_char, "skill": None, "item": None}

            # 타겟 타입에 따라 아군/적군 중 선택
            target_type = getattr(skill, "target_type", "enemy")
            if target_type in ("ally", "self", "all_allies"):
                pool = allies
            else:
                pool = enemies

            target = pool[target_idx] if target_idx < len(pool) else (pool[0] if pool else None)
            return {"action_type": ActionType.SKILL.value, "target": target, "skill": skill, "item": None}

        # ITEM (42-45)
        if _ITEM_START <= action_id < ActionSpaceEncoder.NUM_ACTIONS:
            item_idx = action_id - _ITEM_START
            item = ActionSpaceEncoder._get_item(current_char, item_idx)
            return {"action_type": ActionType.ITEM.value, "target": current_char, "skill": None, "item": item}

        # 범위 외: 방어로 폴백
        logger.warning(f"유효하지 않은 action_id={action_id}, DEFEND로 폴백")
        return {"action_type": ActionType.DEFEND.value, "target": current_char, "skill": None, "item": None}

    @staticmethod
    def get_valid_mask(combat_manager: Any, current_char: Any) -> np.ndarray:
        """
        유효 행동 마스크 반환

        Args:
            combat_manager: CombatManager 인스턴스
            current_char: 현재 행동하는 캐릭터

        Returns:
            (114,) bool numpy 배열 (True = 유효한 행동)
        """
        mask = np.zeros(ActionSpaceEncoder.NUM_ACTIONS, dtype=bool)

        alive_enemies = [e for e in combat_manager.enemies if getattr(e, "is_alive", True)]
        alive_allies = [a for a in combat_manager.allies if getattr(a, "is_alive", False)]
        num_alive_enemies = len(alive_enemies)

        # BRV_ATTACK (0-3): 살아있는 적 슬롯만 유효
        for i in range(_NUM_TARGETS):
            mask[_BRV_ATTACK_START + i] = (i < num_alive_enemies)

        # HP_ATTACK (4-7): 살아있는 적 슬롯만 유효
        for i in range(_NUM_TARGETS):
            mask[_HP_ATTACK_START + i] = (i < num_alive_enemies)

        # DEFEND (8): 항상 유효
        mask[_DEFEND_ID] = True

        # FLEE (9): can_flee 속성 확인
        can_flee = getattr(combat_manager, "can_flee", True)
        mask[_FLEE_ID] = bool(can_flee)

        # SKILL (10-41)
        skills = getattr(current_char, "skills", []) or []
        for skill_idx in range(_NUM_SKILLS):
            for target_idx in range(_NUM_TARGETS):
                action_id = _SKILL_START + skill_idx * _NUM_TARGETS + target_idx
                if skill_idx >= len(skills):
                    mask[action_id] = False
                    continue

                skill = skills[skill_idx]

                # 스킬 사용 가능 여부 확인
                try:
                    context = {"combat_manager": combat_manager}
                    usable = skill.can_use(current_char, context) if hasattr(skill, "can_use") else True
                except Exception:
                    usable = True

                if not usable:
                    mask[action_id] = False
                    continue

                # 타겟 타입에 따른 유효성
                target_type = getattr(skill, "target_type", "enemy")
                if target_type in ("ally", "all_allies"):
                    pool_size = len(alive_allies)
                elif target_type == "self":
                    pool_size = 1  # 자기 자신
                elif target_type in ("all_enemies", "all"):
                    pool_size = 1  # 전체 대상은 슬롯 0만 유효
                else:
                    pool_size = num_alive_enemies

                mask[action_id] = (target_idx < pool_size) if pool_size > 0 else False

        # ITEM (42-45)
        for i in range(_NUM_ITEMS):
            item = ActionSpaceEncoder._get_item(current_char, i)
            mask[_ITEM_START + i] = (item is not None)

        return mask

    @staticmethod
    def encode(action_dict: Dict, combat_manager: Any, current_char: Any) -> int:
        """
        행동 딕셔너리를 action_id로 역변환 (BC 학습용)

        Args:
            action_dict: {"action_type": str, "target": ..., "skill": ..., "item": ...}
            combat_manager: CombatManager 인스턴스
            current_char: 현재 행동하는 캐릭터

        Returns:
            0~113 사이의 action_id
        """
        action_type = action_dict.get("action_type", "")
        target = action_dict.get("target")
        skill = action_dict.get("skill")
        item = action_dict.get("item")

        alive_enemies = [e for e in combat_manager.enemies if getattr(e, "is_alive", True)]

        if action_type == ActionType.BRV_ATTACK.value:
            target_idx = _find_target_idx(target, alive_enemies)
            return _BRV_ATTACK_START + target_idx

        if action_type == ActionType.HP_ATTACK.value:
            target_idx = _find_target_idx(target, alive_enemies)
            return _HP_ATTACK_START + target_idx

        if action_type == ActionType.DEFEND.value:
            return _DEFEND_ID

        if action_type == ActionType.FLEE.value:
            return _FLEE_ID

        if action_type == ActionType.SKILL.value and skill is not None:
            skills = getattr(current_char, "skills", []) or []
            skill_idx = 0
            for i, s in enumerate(skills):
                if s is skill or getattr(s, "skill_id", None) == getattr(skill, "skill_id", None):
                    skill_idx = i
                    break

            target_type = getattr(skill, "target_type", "enemy")
            if target_type in ("ally", "all_allies"):
                alive_allies = [a for a in combat_manager.allies if getattr(a, "is_alive", False)]
                target_idx = _find_target_idx(target, alive_allies)
            else:
                target_idx = _find_target_idx(target, alive_enemies)

            return _SKILL_START + skill_idx * _NUM_TARGETS + target_idx

        if action_type == ActionType.ITEM.value and item is not None:
            for i in range(_NUM_ITEMS):
                candidate = ActionSpaceEncoder._get_item(current_char, i)
                if candidate is item:
                    return _ITEM_START + i

        return _DEFEND_ID  # 폴백

    @staticmethod
    def _get_item(char: Any, item_idx: int) -> Optional[Any]:
        """캐릭터 인벤토리에서 item_idx번째 소비 아이템 반환"""
        try:
            inventory = getattr(char, "inventory", None)
            if inventory is None:
                return None
            consumables = getattr(inventory, "consumables", None) or []
            if item_idx < len(consumables):
                return consumables[item_idx]
        except Exception:
            pass
        return None


def _find_target_idx(target: Any, pool: List[Any]) -> int:
    """타겟이 풀에서 몇 번째인지 반환 (없으면 0)"""
    for i, t in enumerate(pool):
        if t is target:
            return i
    return 0
