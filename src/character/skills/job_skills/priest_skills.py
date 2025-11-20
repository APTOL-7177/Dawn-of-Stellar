"""Priest Skills - 신관 스킬 (속죄/심판 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_priest_skills():
    """신관 10개 스킬 생성 (속죄/심판 시스템)"""

    skills = []

    # 1. 기본 BRV: 성스러운 일격
    holy_smite = Skill("priest_holy_smite", "성스러운 일격", "심판 포인트 획득")
    holy_smite.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "judgment_points", 1, max_value=6)
    ]
    holy_smite.costs = []  # 기본 공격은 MP 소모 없음
    holy_smite.sfx = ("skill", "cast_start")  # 마법 시전
    holy_smite.metadata = {"judgment_gain": 1}
    skills.append(holy_smite)

    # 2. 기본 HP: 신성한 심판
    divine_judgment = Skill("priest_divine_judgment", "신성한 심판", "심판 포인트 소비 공격")
    divine_judgment.effects = [
        DamageEffect(DamageType.HP, 1.1, gimmick_bonus={"field": "judgment_points", "multiplier": 0.3}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "judgment_points", 1)
    ]
    divine_judgment.costs = []  # 기본 공격은 MP 소모 없음
    divine_judgment.sfx = ("skill", "cast_complete")  # 마법 완료
    divine_judgment.metadata = {"judgment_cost": 1, "judgment_scaling": True}
    skills.append(divine_judgment)

    # 3. 빛의 속박
    light_bind = Skill("priest_light_bind", "빛의 속박", "심판 포인트 획득, 디버프")
    light_bind.effects = [
        DamageEffect(DamageType.BRV, 1.6, stat_type="magical"),
        BuffEffect(BuffType.SPEED_DOWN, 0.4, duration=3),
        GimmickEffect(GimmickOperation.ADD, "judgment_points", 1, max_value=6)
    ]
    light_bind.costs = []
    # light_bind.cooldown = 2  # 쿨다운 시스템 제거됨
    light_bind.sfx = ("character", "status_debuff")  # 디버프
    light_bind.metadata = {"judgment_gain": 1, "debuff": True}
    skills.append(light_bind)

    # 4. 성스러운 치유
    holy_heal = Skill("priest_holy_heal", "성스러운 치유", "심판 2포인트 소비, 회복")
    holy_heal.effects = [
        HealEffect(HealType.HP, percentage=0.45),  # 성스러운 치유 (0.32 → 0.45 증가)
        GimmickEffect(GimmickOperation.CONSUME, "judgment_points", 2)
    ]
    holy_heal.costs = [MPCost(5), StackCost("judgment_points", 2)]
    holy_heal.target_type = "ally"
    # holy_heal.cooldown = 3  # 쿨다운 시스템 제거됨
    holy_heal.sfx = ("character", "hp_heal")  # 회복
    holy_heal.metadata = {"judgment_cost": 2, "healing": True}
    skills.append(holy_heal)

    # 5. 신의 가호
    divine_protection = Skill("priest_divine_protection", "신의 가호", "심판 2포인트 소비, 버프")
    divine_protection.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.5, duration=4),
        BuffEffect(BuffType.REGEN, 0.19, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "judgment_points", 2)
    ]
    divine_protection.costs = [MPCost(5), StackCost("judgment_points", 2)]
    divine_protection.target_type = "ally"
    # divine_protection.cooldown = 4  # 쿨다운 시스템 제거됨
    divine_protection.sfx = ("character", "status_buff")  # 버프
    divine_protection.metadata = {"judgment_cost": 2, "buff": True, "regen": True}
    skills.append(divine_protection)

    # 6. 심판의 빛
    judgment_light = Skill("priest_judgment_light", "심판의 빛", "심판 최대 회복")
    judgment_light.effects = [
        GimmickEffect(GimmickOperation.SET, "judgment_points", 6),
        BuffEffect(BuffType.MAGIC_UP, 0.4, duration=3)
    ]
    judgment_light.costs = [MPCost(6)]
    judgment_light.target_type = "self"
    # judgment_light.cooldown = 5  # 쿨다운 시스템 제거됨
    judgment_light.sfx = ("skill", "haste")  # 버프/강화
    judgment_light.metadata = {"judgment_refill": True, "buff": True}
    skills.append(judgment_light)

    # 7. 신성한 광선
    holy_beam = Skill("priest_holy_beam", "신성한 광선", "심판 3포인트 소비, 광역 공격")
    holy_beam.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0, gimmick_bonus={"field": "judgment_points", "multiplier": 0.35}, stat_type="magical"),
        GimmickEffect(GimmickOperation.CONSUME, "judgment_points", 3)
    ]
    holy_beam.costs = [MPCost(7), StackCost("judgment_points", 3)]
    # holy_beam.cooldown = 4  # 쿨다운 시스템 제거됨
    holy_beam.target_type = "all_enemies"
    holy_beam.is_aoe = True
    holy_beam.sfx = ("skill", "cast_complete")  # 광역 마법
    holy_beam.metadata = {"judgment_cost": 3, "judgment_scaling": True, "aoe": True}
    skills.append(holy_beam)

    # 8. 신의 분노
    divine_wrath = Skill("priest_divine_wrath", "신의 분노", "심판 5포인트 소비, 절대 심판")
    divine_wrath.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "judgment_points", "multiplier": 0.4}, stat_type="magical"),
        DamageEffect(DamageType.HP, 2.0, stat_type="magical"),
        BuffEffect(BuffType.ATTACK_DOWN, 0.5, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "judgment_points", 5)
    ]
    divine_wrath.costs = [MPCost(10), StackCost("judgment_points", 5)]
    # divine_wrath.cooldown = 6  # 쿨다운 시스템 제거됨
    divine_wrath.sfx = ("skill", "ultima")  # 강한 마법
    divine_wrath.metadata = {"judgment_cost": 5, "judgment_scaling": True, "debuff": True}
    skills.append(divine_wrath)

    # 9. 신의 은총 (NEW - 10번째 스킬 전)
    divine_grace = Skill("priest_divine_grace", "신의 은총", "심판 4포인트 소비, 파티 치유와 버프")
    divine_grace.effects = [
        HealEffect(HealType.HP, percentage=0.28, is_party_wide=True),  # 신의 은총 (파티 힐)
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=4, is_party_wide=True),
        BuffEffect(BuffType.SPIRIT_UP, 0.4, duration=4, is_party_wide=True),
        BuffEffect(BuffType.REGEN, 0.24, duration=4, is_party_wide=True),
        GimmickEffect(GimmickOperation.CONSUME, "judgment_points", 4)
    ]
    divine_grace.costs = [MPCost(10), StackCost("judgment_points", 4)]
    divine_grace.target_type = "party"
    # divine_grace.cooldown = 6  # 쿨다운 시스템 제거됨
    divine_grace.sfx = ("character", "hp_heal")  # 회복
    divine_grace.metadata = {"judgment_cost": 4, "healing": True, "buff": True, "party": True}
    skills.append(divine_grace)

    # 10. 궁극기: 최후의 심판
    ultimate = Skill("priest_ultimate", "최후의 심판", "모든 심판을 내림")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "judgment_points", "multiplier": 0.45}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "judgment_points", "multiplier": 0.45}, stat_type="magical"),
        DamageEffect(DamageType.HP, 3.0, gimmick_bonus={"field": "judgment_points", "multiplier": 0.6}, stat_type="magical"),
        HealEffect(HealType.HP, percentage=0.55, is_party_wide=True),  # 궁극기 (파티 힐)
        GimmickEffect(GimmickOperation.SET, "judgment_points", 6)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15  # 궁극기 쿨타임 15턴
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")  # 궁극기
    ultimate.metadata = {"ultimate": True, "judgment_scaling": True, "judgment_refill": True, "healing": True, "party": True}
    skills.append(ultimate)

    return skills

def register_priest_skills(skill_manager):
    """신관 스킬 등록"""
    skills = create_priest_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
