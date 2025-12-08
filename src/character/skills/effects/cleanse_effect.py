"""Cleanse Effect - 상태 이상 해제 효과"""
from typing import Dict, Any, Tuple
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.character.skills.effects.status_effect import StatusType, StatusEffect
from src.core.logger import get_logger

logger = get_logger("cleanse_effect")

class CleanseEffect(SkillEffect):
    """
    상태 이상 해제 효과
    
    지정된 개수만큼의 해로운 상태 이상을 무작위(또는 최근 순)로 제거합니다.
    """
    def __init__(self, count: int = 1, status_types: list = None):
        """
        Args:
            count: 제거할 상태 이상 개수
            status_types: 제거할 특정 상태 이상 타입 리스트 (None이면 모든 디버프 대상)
        """
        super().__init__(EffectType.UTILITY)
        self.count = count
        self.status_types = status_types

    def can_execute(self, user: Any, target: Any, context: Dict[str, Any]) -> Tuple[bool, str]:
        return True, ""

    def execute(self, user: Any, target: Any, context: Dict[str, Any]) -> EffectResult:
        """상태 이상 제거 실행"""
        removed_count = 0
        removed_names = []

        # 1. StatusManager 사용 확인 (신규 시스템)
        if hasattr(target, 'status_manager'):
            # 제거 대상 상태 찾기
            candidates = []
            for effect in target.status_manager.status_effects:
                # 특정 타입 지정된 경우 확인
                if self.status_types:
                    # TODO: StatusType 매핑 확인 필요
                    pass
                
                # 디버프인지 확인 (StatusType Enum 멤버의 값이나 이름으로 확인 어려움 -> 단순 리스트 체크)
                # 여기서는 간단히 부정적인 효과 목록을 정의해서 체크하거나,
                # StatusEffect 클래스에 is_debuff 같은 속성이 있다고 가정
                # 하지만 현재 StatusEffect 구조상 명시적인 is_debuff 속성은 없음.
                # StatusType Enum의 Categorization 주석을 참고하여 하드코딩하거나
                # 일반적으로 알려진 디버프들을 체크해야 함.
                
                # 임시: StatusType Enum을 import해서 비교
                from src.combat.status_effects import StatusType as CombatStatusType
                
                # 디버프 목록 (combat/status_effects.py 참조)
                debuff_types = [
                    CombatStatusType.REDUCE_ATK, CombatStatusType.REDUCE_DEF, CombatStatusType.REDUCE_SPD,
                    CombatStatusType.REDUCE_ACCURACY, CombatStatusType.REDUCE_EVASION, CombatStatusType.REDUCE_ALL_STATS,
                    CombatStatusType.REDUCE_MAGIC_ATK, CombatStatusType.REDUCE_MAGIC_DEF,
                    CombatStatusType.VULNERABLE, CombatStatusType.EXPOSED, CombatStatusType.WEAKNESS,
                    CombatStatusType.WEAKEN, CombatStatusType.CONFUSION, CombatStatusType.TERROR,
                    CombatStatusType.FEAR, CombatStatusType.DESPAIR,
                    CombatStatusType.POISON, CombatStatusType.BURN, CombatStatusType.BLEED,
                    CombatStatusType.CORRODE, CombatStatusType.CORROSION, CombatStatusType.DISEASE,
                    CombatStatusType.NECROSIS, CombatStatusType.MP_DRAIN, CombatStatusType.CHILL,
                    CombatStatusType.SHOCK, CombatStatusType.NATURE_CURSE,
                    CombatStatusType.STUN, CombatStatusType.SLEEP, CombatStatusType.SILENCE,
                    CombatStatusType.BLIND, CombatStatusType.PARALYZE, CombatStatusType.FREEZE,
                    CombatStatusType.PETRIFY, CombatStatusType.CHARM, CombatStatusType.DOMINATE,
                    CombatStatusType.ROOT, CombatStatusType.SLOW, CombatStatusType.ENTANGLE,
                    CombatStatusType.MADNESS, CombatStatusType.TAUNT, CombatStatusType.CURSE,
                    CombatStatusType.DOOM, CombatStatusType.HP_RECOVERY_BLOCK, CombatStatusType.CURSE_MARK
                ]
                
                if effect.status_type in debuff_types:
                    candidates.append(effect)
            
            # 제거 실행 (최근에 추가된 것부터? 랜덤? -> 뒤에서부터)
            for _ in range(self.count):
                if not candidates:
                    break
                effect_to_remove = candidates.pop() # 가장 최근
                if target.status_manager.remove_status(effect_to_remove.status_type):
                    removed_count += 1
                    removed_names.append(effect_to_remove.name)
                    
        # 2. Legacy status_effects 리스트/딕셔너리 사용
        elif hasattr(target, 'status_effects'):
            # 딕셔너리 구조 가정 (legacy)
            if isinstance(target.status_effects, dict):
                # 디버프 키워드들 (legacy status_effect.py 참조)
                legacy_debuffs = [
                    StatusType.POISON, StatusType.BURN, StatusType.FREEZE, StatusType.STUN,
                    StatusType.SLEEP, StatusType.SILENCE, StatusType.BLIND, StatusType.SLOW,
                    StatusType.SHOCK, StatusType.CURSE, StatusType.WEAKEN, StatusType.WEAKNESS,
                    StatusType.DEFENSE_DOWN, StatusType.ATTACK_DOWN
                ]
                
                candidates = [k for k in target.status_effects.keys() if k in legacy_debuffs]
                
                for _ in range(self.count):
                    if not candidates:
                        break
                    key = candidates.pop()
                    del target.status_effects[key]
                    removed_count += 1
                    removed_names.append(key)
                    
            elif isinstance(target.status_effects, list):
                # 여기서는 Legacy StatusEffectData 객체라고 가정
                # 단순 구현 생략 (대부분 dict 또는 StatusManager로 이행 중)
                pass

        if removed_count > 0:
            return EffectResult(EffectType.UTILITY, True, f"상태이상 해제: {', '.join(removed_names)}")
        return EffectResult(EffectType.UTILITY, False, "해제할 상태이상이 없습니다.")

    def get_description(self) -> str:
        return f"디버프 {self.count}개 제거"
