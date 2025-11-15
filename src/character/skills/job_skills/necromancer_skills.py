"""Necromancer Skills - 네크로맨서 스킬 (시체/소환수 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_necromancer_skills():
    """네크로맨서 9개 스킬 생성"""
    
    # 1. 기본 BRV: 시체의 손길
    corpse_touch = Skill("necro_corpse_touch", "시체의 손길", "죽음의 에너지로 공격, 시체 획득")
    corpse_touch.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "corpse_count", 1, max_value=10)
    ]
    corpse_touch.costs = []  # 기본 공격은 MP 소모 없음
    
    # 2. 기본 HP: 영혼 흡수
    soul_drain = Skill("necro_soul_drain", "영혼 흡수", "시체를 소비하여 HP 공격")
    soul_drain.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "corpse_count", "multiplier": 0.2}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "corpse_count", 1)
    ]
    soul_drain.costs = []  # 기본 공격은 MP 소모 없음
    
    # 3. 스켈레톤 소환
    summon_skeleton = Skill("necro_summon_skeleton", "스켈레톤 소환", "시체 3개로 소환수 생성")
    summon_skeleton.effects = [
        GimmickEffect(GimmickOperation.ADD, "minion_count", 1, max_value=5),
        GimmickEffect(GimmickOperation.CONSUME, "corpse_count", 3),
        BuffEffect(BuffType.ATTACK_UP, 0.15, duration=5)
    ]
    summon_skeleton.costs = [MPCost(8), StackCost("corpse_count", 3)]
    summon_skeleton.target_type = "self"
    summon_skeleton.cooldown = 3
    
    # 4. 죽음의 화살
    death_bolt = Skill("necro_death_bolt", "죽음의 화살", "시체에 비례한 마법 공격")
    death_bolt.effects = [
        DamageEffect(DamageType.BRV, 1.8, gimmick_bonus={"field": "corpse_count", "multiplier": 0.15}, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "corpse_count", 1, max_value=10)
    ]
    death_bolt.costs = [MPCost(6)]
    death_bolt.cooldown = 2
    
    # 5. 시체 폭발
    corpse_explosion = Skill("necro_corpse_explosion", "시체 폭발", "모든 시체 폭발, 범위 공격")
    corpse_explosion.effects = [
        DamageEffect(DamageType.BRV_HP, 1.5, gimmick_bonus={"field": "corpse_count", "multiplier": 0.3}, stat_type="magical"),
        GimmickEffect(GimmickOperation.SET, "corpse_count", 0)
    ]
    corpse_explosion.costs = [MPCost(10), StackCost("corpse_count", 1)]
    corpse_explosion.cooldown = 4
    
    # 6. 생명 흡수
    life_tap = Skill("necro_life_tap", "생명 흡수", "적의 생명력을 흡수")
    life_tap.effects = [
        DamageEffect(DamageType.BRV, 1.2, stat_type="magical"),
        HealEffect(HealType.HP, percentage=0.2),
        GimmickEffect(GimmickOperation.ADD, "corpse_count", 2, max_value=10)
    ]
    life_tap.costs = [MPCost(8)]
    life_tap.cooldown = 3
    
    # 7. 암흑 의식
    dark_ritual = Skill("necro_dark_ritual", "암흑 의식", "시체로 힘 강화")
    dark_ritual.effects = [
        BuffEffect(BuffType.MAGIC_UP, 0.3, duration=4),
        BuffEffect(BuffType.SPEED_UP, 0.2, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "corpse_count", 2)
    ]
    dark_ritual.costs = [MPCost(9), StackCost("corpse_count", 2)]
    dark_ritual.target_type = "self"
    dark_ritual.cooldown = 4
    
    # 8. 재생
    reanimate = Skill("necro_reanimate", "재생", "시체 5개 소비, 대량 회복 + 소환수")
    reanimate.effects = [
        HealEffect(HealType.HP, percentage=0.5),
        GimmickEffect(GimmickOperation.ADD, "minion_count", 2, max_value=5),
        GimmickEffect(GimmickOperation.CONSUME, "corpse_count", 5)
    ]
    reanimate.costs = [MPCost(12), StackCost("corpse_count", 5)]
    reanimate.target_type = "self"
    reanimate.cooldown = 6
    
    # 9. 궁극기: 언데드 군단
    ultimate = Skill("necro_ultimate", "언데드 군단", "모든 시체로 군단 소환, 적 섬멸")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "corpse_count", "multiplier": 0.4}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 1.5, gimmick_bonus={"field": "minion_count", "multiplier": 0.5}, stat_type="magical"),
        DamageEffect(DamageType.HP, 3.0, stat_type="magical"),
        GimmickEffect(GimmickOperation.SET, "minion_count", 5),
        GimmickEffect(GimmickOperation.SET, "corpse_count", 0),
        BuffEffect(BuffType.MAGIC_UP, 0.5, duration=5),
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=5)
    ]
    ultimate.costs = [MPCost(25)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 10
    
    return [corpse_touch, soul_drain, summon_skeleton, death_bolt, corpse_explosion,
            life_tap, dark_ritual, reanimate, ultimate]

def register_necromancer_skills(skill_manager):
    """네크로맨서 스킬 등록"""
    skills = create_necromancer_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
