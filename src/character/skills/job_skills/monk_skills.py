"""Monk Skills - 몽크 스킬 (콤보/차크라 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_monk_skills():
    """몽크 9개 스킬 생성"""
    
    # 1. 기본 BRV: 연타
    rapid_punch = Skill("monk_rapid_punch", "연타", "빠른 주먹 공격, 콤보 획득")
    rapid_punch.effects = [
        DamageEffect(DamageType.BRV, 1.2, gimmick_bonus={"field": "combo_count", "multiplier": 0.1}),
        GimmickEffect(GimmickOperation.ADD, "combo_count", 1, max_value=10)
    ]
    rapid_punch.costs = []  # 기본 공격은 MP 소모 없음
    
    # 2. 기본 HP: 장타
    palm_strike = Skill("monk_palm_strike", "장타", "콤보 소비 강력한 장타")
    palm_strike.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "combo_count", "multiplier": 0.25}),
        GimmickEffect(GimmickOperation.CONSUME, "combo_count", 1)
    ]
    palm_strike.costs = []  # 기본 공격은 MP 소모 없음
    
    # 3. 차크라 집중
    chakra_focus = Skill("monk_chakra_focus", "차크라 집중", "내공 집중, 차크라 획득")
    chakra_focus.effects = [
        GimmickEffect(GimmickOperation.ADD, "chakra_points", 2, max_value=5),
        GimmickEffect(GimmickOperation.ADD, "combo_count", 1, max_value=10)
    ]
    chakra_focus.costs = [MPCost(5)]
    chakra_focus.target_type = "self"
    chakra_focus.cooldown = 3
    
    # 4. 비룡각
    flying_kick = Skill("monk_flying_kick", "비룡각", "공중 회전 발차기")
    flying_kick.effects = [
        DamageEffect(DamageType.BRV, 1.8, gimmick_bonus={"field": "combo_count", "multiplier": 0.15}),
        GimmickEffect(GimmickOperation.ADD, "combo_count", 2, max_value=10)
    ]
    flying_kick.costs = [MPCost(6)]
    flying_kick.cooldown = 2
    
    # 5. 내공 방출
    inner_fire = Skill("monk_inner_fire", "내공 방출", "차크라로 전투력 강화")
    inner_fire.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=4),
        BuffEffect(BuffType.SPEED_UP, 0.3, duration=4),
        BuffEffect(BuffType.CRITICAL_UP, 0.2, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "chakra_points", 1)
    ]
    inner_fire.costs = [MPCost(8), StackCost("chakra_points", 1)]
    inner_fire.target_type = "self"
    inner_fire.cooldown = 4
    
    # 6. 콤보 피니셔
    combo_finisher = Skill("monk_combo_finisher", "콤보 피니셔", "모든 콤보 소비, 최종타")
    combo_finisher.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0, gimmick_bonus={"field": "combo_count", "multiplier": 0.4}),
        GimmickEffect(GimmickOperation.SET, "combo_count", 0)
    ]
    combo_finisher.costs = [MPCost(10), StackCost("combo_count", 3)]
    combo_finisher.cooldown = 4
    
    # 7. 명상
    meditation = Skill("monk_meditation", "명상", "차크라 회복 + HP 회복")
    meditation.effects = [
        HealEffect(HealType.HP, percentage=0.3),
        GimmickEffect(GimmickOperation.ADD, "chakra_points", 3, max_value=5)
    ]
    meditation.costs = [MPCost(6)]
    meditation.target_type = "self"
    meditation.cooldown = 5
    
    # 8. 용격
    dragon_strike = Skill("monk_dragon_strike", "용격", "콤보 5+ 필요, 용의 일격")
    dragon_strike.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, gimmick_bonus={"field": "combo_count", "multiplier": 0.3}),
        GimmickEffect(GimmickOperation.CONSUME, "combo_count", 3)
    ]
    dragon_strike.costs = [MPCost(12), StackCost("combo_count", 5)]
    dragon_strike.cooldown = 5
    
    # 9. 궁극기: 칠성권
    ultimate = Skill("monk_ultimate", "칠성권", "7연타 극의, 콤보와 차크라의 극치")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 1.0, gimmick_bonus={"field": "combo_count", "multiplier": 0.2}),
        DamageEffect(DamageType.BRV, 1.0, gimmick_bonus={"field": "combo_count", "multiplier": 0.2}),
        DamageEffect(DamageType.BRV, 1.0, gimmick_bonus={"field": "combo_count", "multiplier": 0.2}),
        DamageEffect(DamageType.BRV, 1.0, gimmick_bonus={"field": "chakra_points", "multiplier": 0.3}),
        DamageEffect(DamageType.BRV, 1.0, gimmick_bonus={"field": "chakra_points", "multiplier": 0.3}),
        DamageEffect(DamageType.BRV, 1.0, gimmick_bonus={"field": "chakra_points", "multiplier": 0.3}),
        DamageEffect(DamageType.HP, 3.0),
        GimmickEffect(GimmickOperation.SET, "combo_count", 0),
        GimmickEffect(GimmickOperation.SET, "chakra_points", 0)
    ]
    ultimate.costs = [MPCost(25)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 10
    
    return [rapid_punch, palm_strike, chakra_focus, flying_kick, inner_fire,
            combo_finisher, meditation, dragon_strike, ultimate]

def register_monk_skills(skill_manager):
    """몽크 스킬 등록"""
    skills = create_monk_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
