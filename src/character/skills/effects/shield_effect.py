"""Shield Effect - 보호막 효과"""
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType

class ShieldEffect(SkillEffect):
    """보호막 효과"""
    def __init__(self, base_amount=0, hp_consumed_multiplier=0.0, multiplier=0.0, stat_name=None):
        super().__init__(EffectType.GIMMICK)
        self.base_amount = base_amount
        self.hp_consumed_multiplier = hp_consumed_multiplier
        self.multiplier = multiplier
        self.stat_name = stat_name

    def execute(self, user, target, context):
        """보호막 생성"""
        from src.core.logger import get_logger
        logger = get_logger("shield_effect")
        
        amount = self.base_amount
        logger.debug(f"[ShieldEffect] 시작: base_amount={self.base_amount}, context={context}")

        # HP 소비 기반 보호막
        if self.hp_consumed_multiplier > 0 and context and 'hp_consumed' in context:
            hp_consumed = context['hp_consumed']
            amount += int(hp_consumed * self.hp_consumed_multiplier)
            logger.debug(f"[ShieldEffect] HP 소비 기반: +{int(hp_consumed * self.hp_consumed_multiplier)}")

        # 스탯/기믹 기반 보호막 (예: holy_power)
        if self.stat_name and hasattr(user, self.stat_name):
            stat_value = getattr(user, self.stat_name, 0)
            stat_based = int(stat_value * self.multiplier * 10)
            amount += stat_based
            logger.debug(f"[ShieldEffect] 스탯 기반: {self.stat_name}={stat_value}, +{stat_based}")

        # 공격력 기반 보호막 (수호의 맹세 등)
        # context에서 'attack_multiplier'가 있으면 공격력의 해당 비율만큼 보호막 추가
        if context and 'attack_multiplier' in context:
            attack_multiplier = context['attack_multiplier']
            logger.debug(f"[ShieldEffect] 공격력 기반 보호막 계산 시작: multiplier={attack_multiplier}")
            
            # physical_attack 또는 strength 속성 사용
            attack = 0
            if hasattr(user, 'physical_attack'):
                attack = user.physical_attack
                logger.debug(f"[ShieldEffect] physical_attack 속성 사용: {attack}")
            elif hasattr(user, 'strength'):
                attack = user.strength
                logger.debug(f"[ShieldEffect] strength 속성 사용: {attack}")
            elif hasattr(user, 'stat_manager'):
                # StatManager를 통해 strength 가져오기
                from src.character.stats import Stats
                attack = user.stat_manager.get_value(Stats.STRENGTH)
                logger.debug(f"[ShieldEffect] stat_manager를 통해 strength 가져옴: {attack}")
            else:
                logger.warning(f"[ShieldEffect] 공격력 값을 가져올 수 없음: user={user.name}, hasattr physical_attack={hasattr(user, 'physical_attack')}, hasattr strength={hasattr(user, 'strength')}, hasattr stat_manager={hasattr(user, 'stat_manager')}")
            
            attack_based_shield = int(attack * attack_multiplier)
            amount += attack_based_shield
            
            logger.info(f"[보호막 계산] {user.name}: 공격력={attack}, 배율={attack_multiplier}, 보호막={attack_based_shield}, 총={amount}")
        else:
            logger.warning(f"[ShieldEffect] attack_multiplier가 context에 없음: context={context}, metadata에서 확인 필요")

        # 보호막 추가 (수호의 맹세는 본인에게 보호막을 두름)
        # context에서 'protect_self'가 True이면 user에게, 아니면 target에게
        shield_target = user if context and context.get('protect_self', False) else target
        
        if not hasattr(shield_target, 'shield_amount'):
            shield_target.shield_amount = 0

        old_shield = shield_target.shield_amount
        
        # 중첩 방지: context에서 'replace_shield'가 True이면 기존 보호막을 덮어씀
        if context and context.get('replace_shield', False):
            shield_target.shield_amount = amount
            message = f"보호막 {amount} (기존 보호막 대체)"
        else:
            shield_target.shield_amount += amount
            message = f"보호막 +{amount} (총 {shield_target.shield_amount})"

        return EffectResult(
            effect_type=EffectType.GIMMICK,
            success=True,
            gimmick_changes={'shield_amount': amount},
            message=message
        )
