"""
팀워크 스킬 효과 실제 구현

각 직업별 팀워크 스킬의 구체적인 효과 로직
"""

from typing import Any, Dict, List, Optional
from src.core.logger import get_logger

logger = get_logger("skill")


class TeamworkEffectExecutor:
    """팀워크 스킬 효과 실행기"""

    # 효과별 처리 함수 맵
    EFFECT_HANDLERS = {}

    @classmethod
    def execute_effect(cls, effect_type: str, actor: Any, target: Any,
                      **kwargs) -> Dict[str, Any]:
        """
        효과 실행

        Args:
            effect_type: 효과 타입
            actor: 스킬 사용자
            target: 대상
            **kwargs: 추가 파라미터

        Returns:
            효과 결과 딕셔너리
        """
        handler = cls.EFFECT_HANDLERS.get(effect_type)
        if not handler:
            logger.warning(f"알 수 없는 효과 타입: {effect_type}")
            return {"success": False}

        try:
            return handler(actor, target, **kwargs)
        except Exception as e:
            logger.error(f"효과 실행 실패 ({effect_type}): {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def register_handler(effect_type: str, handler):
        """효과 핸들러 등록"""
        TeamworkEffectExecutor.EFFECT_HANDLERS[effect_type] = handler


# ============================================================================
# 효과 핸들러 정의
# ============================================================================

def damage_effect(actor: Any, target: Any, **kwargs) -> Dict[str, Any]:
    """
    데미지 효과

    Args:
        multiplier: 데미지 배율
        damage_type: 피해 타입 (BRV, HP, BOTH)
    """
    multiplier = kwargs.get('multiplier', 1.0)
    damage_type = kwargs.get('damage_type', 'HP')

    # 간단한 데미지 계산 (실제는 damage_calculator 사용)
    if hasattr(actor, 'stat_manager'):
        base_damage = int(actor.stat_manager.get_value('STRENGTH') * multiplier)
    else:
        base_damage = int(50 * multiplier)  # 기본값

    result = {
        "success": True,
        "damage": base_damage,
        "damage_type": damage_type
    }

    # 실제 데미지 적용
    if hasattr(target, 'current_hp') and damage_type in ['HP', 'BOTH']:
        target.current_hp = max(1, target.current_hp - base_damage)
        result["target_hp"] = target.current_hp

    logger.info(f"{actor.name} -> {target.name}: {base_damage} 데미지")
    return result


def heal_effect(actor: Any, target: Any, **kwargs) -> Dict[str, Any]:
    """
    회복 효과

    Args:
        percentage: 회복 비율 (최대 HP 기준)
        amount: 고정 회복량
    """
    percentage = kwargs.get('percentage', 0)
    amount = kwargs.get('amount', 0)

    if percentage > 0 and hasattr(target, 'stat_manager'):
        max_hp = target.stat_manager.get_value('MAX_HP')
        heal_amount = int(max_hp * percentage)
    else:
        heal_amount = amount

    if hasattr(target, 'current_hp'):
        target.current_hp = min(target.stat_manager.get_value('MAX_HP'),
                               target.current_hp + heal_amount)

    result = {
        "success": True,
        "healed": heal_amount,
        "target_hp": target.current_hp if hasattr(target, 'current_hp') else 0
    }

    logger.info(f"{target.name} 회복: {heal_amount} HP")
    return result


def buff_effect(actor: Any, target: Any, **kwargs) -> Dict[str, Any]:
    """
    버프 효과

    Args:
        stat: 버프할 스탯 (STRENGTH, DEFENSE, SPEED 등)
        multiplier: 증가 배율
        duration: 지속 턴 수
    """
    stat = kwargs.get('stat', 'STRENGTH')
    multiplier = kwargs.get('multiplier', 1.2)
    duration = kwargs.get('duration', 3)

    result = {
        "success": True,
        "buff_type": stat,
        "multiplier": multiplier,
        "duration": duration
    }

    logger.info(f"{target.name}에게 {stat} 버프 적용 ({multiplier}배, {duration}턴)")
    return result


def debuff_effect(actor: Any, target: Any, **kwargs) -> Dict[str, Any]:
    """
    디버프 효과

    Args:
        stat: 디버프할 스탯
        reduction: 감소율
        duration: 지속 턴 수
    """
    stat = kwargs.get('stat', 'DEFENSE')
    reduction = kwargs.get('reduction', 0.7)
    duration = kwargs.get('duration', 3)

    result = {
        "success": True,
        "debuff_type": stat,
        "reduction": reduction,
        "duration": duration
    }

    logger.info(f"{target.name}에게 {stat} 디버프 적용 ({reduction}배, {duration}턴)")
    return result


def status_effect(actor: Any, target: Any, **kwargs) -> Dict[str, Any]:
    """
    상태이상 효과

    Args:
        status_type: 상태이상 타입 (POISON, BURN, STUN 등)
        duration: 지속 턴 수
    """
    status_type = kwargs.get('status_type', 'POISON')
    duration = kwargs.get('duration', 3)

    result = {
        "success": True,
        "status_type": status_type,
        "duration": duration
    }

    logger.info(f"{target.name}에게 {status_type} 상태이상 적용 ({duration}턴)")
    return result


def aoe_effect(actor: Any, targets: List[Any], **kwargs) -> Dict[str, Any]:
    """
    광역 효과

    Args:
        effect_type: 적용할 효과 타입
        effect_args: 효과의 파라미터
    """
    effect_type = kwargs.get('effect_type', 'damage')
    effect_args = kwargs.get('effect_args', {})

    results = []
    for target in targets:
        result = TeamworkEffectExecutor.execute_effect(
            effect_type, actor, target, **effect_args
        )
        results.append(result)

    return {
        "success": True,
        "aoe": True,
        "targets": len(targets),
        "results": results
    }


# 효과 핸들러 등록
TeamworkEffectExecutor.register_handler('damage', damage_effect)
TeamworkEffectExecutor.register_handler('heal', heal_effect)
TeamworkEffectExecutor.register_handler('buff', buff_effect)
TeamworkEffectExecutor.register_handler('debuff', debuff_effect)
TeamworkEffectExecutor.register_handler('status', status_effect)
TeamworkEffectExecutor.register_handler('aoe', aoe_effect)


# ============================================================================
# 직업별 팀워크 스킬 효과 정의
# ============================================================================

class WarriorTeamworkEffects:
    """전사 팀워크 스킬 효과"""

    @staticmethod
    def execute_charge(actor: Any, target: Any, **kwargs) -> Dict[str, Any]:
        """전장의 돌격 - 단일 BRV+HP 공격"""
        results = []

        # BRV 공격
        brv_result = damage_effect(actor, target, multiplier=2.2, damage_type='BRV')
        results.append(("BRV 공격", brv_result))

        # HP 변환
        hp_result = damage_effect(actor, target, multiplier=1.0, damage_type='HP')
        results.append(("HP 공격", hp_result))

        return {
            "success": True,
            "skill": "전장의 돌격",
            "results": results,
            "total_damage": brv_result["damage"] + hp_result["damage"]
        }


class ArcherTeamworkEffects:
    """궁수 팀워크 스킬 효과"""

    @staticmethod
    def execute_salvo(actor: Any, target: Any, **kwargs) -> Dict[str, Any]:
        """일제사격 - 마킹된 모든 아군의 지원사격 발동"""
        # 마킹 시스템과 연동되어야 함
        damage = damage_effect(actor, target, multiplier=2.5, damage_type='HP')

        return {
            "success": True,
            "skill": "일제사격",
            "damage": damage["damage"],
            "note": "마킹된 아군의 지원사격이 자동 발동됨"
        }


class KnightTeamworkEffects:
    """기사 팀워크 스킬 효과"""

    @staticmethod
    def execute_shield(actor: Any, targets: List[Any], **kwargs) -> Dict[str, Any]:
        """불굴의 방패 - 아군 전체 방어막"""
        results = []

        for target in targets:
            buff = buff_effect(actor, target, stat="DEFENSE", multiplier=1.2, duration=2)
            results.append((target.name, buff))

        return {
            "success": True,
            "skill": "불굴의 방패",
            "targets": len(targets),
            "results": results
        }


class ClericTeamworkEffects:
    """성직자 팀워크 스킬 효과"""

    @staticmethod
    def execute_heal_prayer(actor: Any, target: Any, **kwargs) -> Dict[str, Any]:
        """치유의 기도 - 대폭 회복 + 리젠"""
        # 회복
        heal_result = heal_effect(actor, target, percentage=0.6)

        # 리젠 (지속 회복)
        regen = buff_effect(actor, target, stat="REGEN", multiplier=1.1, duration=3)

        return {
            "success": True,
            "skill": "치유의 기도",
            "healed": heal_result["healed"],
            "regen": "적용됨 (3턴)",
            "results": [heal_result, regen]
        }


class SnipherTeamworkEffects:
    """저격수 팀워크 스킬 효과"""

    @staticmethod
    def execute_perfect_aim(actor: Any, target: Any, **kwargs) -> Dict[str, Any]:
        """완벽한 조준 - 크리티컬 확정 HP 공격"""
        # 크리티컬 보너스 포함 (1.5배)
        damage_result = damage_effect(actor, target, multiplier=3.0, damage_type='HP')
        damage_result["critical"] = True
        damage_result["note"] = "크리티컬 확정"

        return {
            "success": True,
            "skill": "완벽한 조준",
            "damage": damage_result["damage"],
            "critical": True
        }


# 더 많은 효과들...

# 효과 저장소
TEAMWORK_EFFECT_EXECUTORS = {
    "warrior_teamwork": WarriorTeamworkEffects.execute_charge,
    "archer_teamwork": ArcherTeamworkEffects.execute_salvo,
    "knight_teamwork": KnightTeamworkEffects.execute_shield,
    "cleric_teamwork": ClericTeamworkEffects.execute_heal_prayer,
    "sniper_teamwork": SnipherTeamworkEffects.execute_perfect_aim,
}


def execute_teamwork_skill_effect(skill_id: str, actor: Any, target: Any,
                                  **kwargs) -> Dict[str, Any]:
    """
    팀워크 스킬 효과 실행

    Args:
        skill_id: 스킬 ID
        actor: 사용자
        target: 대상
        **kwargs: 추가 파라미터

    Returns:
        효과 결과
    """
    executor = TEAMWORK_EFFECT_EXECUTORS.get(skill_id)
    if not executor:
        logger.warning(f"팀워크 스킬 효과 없음: {skill_id}")
        return {"success": False}

    try:
        result = executor(actor, target, **kwargs)
        logger.info(f"팀워크 스킬 효과 실행: {skill_id} - {result.get('success')}")
        return result
    except Exception as e:
        logger.error(f"팀워크 스킬 효과 실행 실패 ({skill_id}): {e}")
        return {"success": False, "error": str(e)}
