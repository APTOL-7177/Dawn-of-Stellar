"""Paladin Skills - 팔라딘 스킬 (성력/신성 보호 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.shield_effect import ShieldEffect
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_paladin_skills():
    """팔라딘 10개 스킬 생성 (성력/신성 보호 시스템)"""

    skills = []

    # 1. 기본 BRV: 성스러운 일격
    holy_strike = Skill("paladin_holy_strike", "성스러운 일격", "신성 속성. 신성한 힘으로 공격, 성력 획득")
    holy_strike.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magical", element="holy"),
        GimmickEffect(GimmickOperation.ADD, "holy_power", 1, max_value=5)
    ]
    holy_strike.costs = []
    holy_strike.sfx = ("combat", "attack_physical")
    holy_strike.metadata = {"basic_attack": True, "element": "holy", "holy_power_gain": 1}
    skills.append(holy_strike)

    # 2. 기본 HP: 신성한 심판
    divine_judgment = Skill("paladin_judgment", "신성한 심판", "신성 속성. 성력 소비 심판의 일격")
    divine_judgment.effects = [
        DamageEffect(DamageType.HP, 1.0, stat_type="magical", element="holy", gimmick_bonus={"field": "holy_power", "multiplier": 0.3}),
        GimmickEffect(GimmickOperation.CONSUME, "holy_power", 1)
    ]
    divine_judgment.costs = []
    divine_judgment.sfx = ("skill", "cast_complete")
    divine_judgment.metadata = {"basic_attack": True, "element": "holy", "holy_power_cost": 1, "holy_power_scaling": True}
    skills.append(divine_judgment)

    # 3. 신성한 보호막
    divine_shield = Skill("paladin_divine_shield", "신성한 보호막", "성력으로 강력한 보호막")
    divine_shield.effects = [
        ShieldEffect(base_amount=0),  # 공격력 기반으로 계산 (base_amount는 0)
        GimmickEffect(GimmickOperation.CONSUME, "holy_power", 2)
    ]
    divine_shield.costs = []
    divine_shield.target_type = "self"
    # divine_shield.cooldown = 4  # 쿨다운 시스템 제거됨
    divine_shield.sfx = ("skill", "shell")  # 신성한 보호막
    divine_shield.metadata = {"holy_power_cost": 2, "shield": True, "attack_multiplier": 0.7, "replace_shield": True}  # 공격력의 70%, 중첩 방지
    skills.append(divine_shield)

    # 4. 신성화
    consecration = Skill("paladin_consecration", "신성화", "땅을 신성화, 지속 피해")
    consecration.effects = [
        DamageEffect(DamageType.BRV, 1.3),
        DamageEffect(DamageType.BRV, 1.3),
        GimmickEffect(GimmickOperation.ADD, "holy_power", 1, max_value=5)
    ]
    consecration.costs = [MPCost(3)]
    # consecration.cooldown = 3  # 쿨다운 시스템 제거됨
    consecration.sfx = ("character", "status_buff")  # 신성화
    consecration.metadata = {"holy_power_gain": 1, "dot": True}
    skills.append(consecration)

    # 5. 성스러운 빛
    holy_light = Skill("paladin_holy_light", "성스러운 빛", "아군 치유 + 성력")
    holy_light.effects = [
        HealEffect(HealType.HP, percentage=0.45),  # 성스러운 빛 (탱커 기준 적정 회복량)
        GimmickEffect(GimmickOperation.ADD, "holy_power", 1, max_value=5)
    ]
    holy_light.costs = [MPCost(5)]
    holy_light.target_type = "ally"
    # holy_light.cooldown = 2  # 쿨다운 시스템 제거됨
    holy_light.sfx = ("character", "hp_heal")  # 성스러운 빛
    holy_light.metadata = {"holy_power_gain": 1, "healing": True}
    skills.append(holy_light)

    # 6. 정의의 망치
    hammer = Skill("paladin_hammer", "정의의 망치", "신성 속성. 성력 비례 강타")
    hammer.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0, stat_type="magical", element="holy", gimmick_bonus={"field": "holy_power", "multiplier": 0.25}),
        GimmickEffect(GimmickOperation.ADD, "holy_power", 1, max_value=5)
    ]
    hammer.costs = [MPCost(6)]
    hammer.sfx = ("combat", "damage_high")
    hammer.metadata = {"element": "holy", "holy_power_gain": 1, "holy_power_scaling": True}
    skills.append(hammer)

    # 7. 축복
    blessing = Skill("paladin_blessing", "축복", "파티 전체 방어 버프")
    blessing.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=4, is_party_wide=True),
        BuffEffect(BuffType.SPIRIT_UP, 0.3, duration=4, is_party_wide=True),
        GimmickEffect(GimmickOperation.ADD, "holy_power", 1, max_value=5)
    ]
    blessing.costs = [MPCost(6)]
    blessing.target_type = "party"
    # blessing.cooldown = 5  # 쿨다운 시스템 제거됨
    blessing.sfx = ("character", "status_buff")  # 축복
    blessing.metadata = {"holy_power_gain": 1, "party": True, "buff": True}
    skills.append(blessing)

    # 8. 복수의 격노
    avenging_wrath = Skill("paladin_wrath", "복수의 격노", "성력 3 소비, 강력한 버프")
    avenging_wrath.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=5),
        BuffEffect(BuffType.CRITICAL_UP, 0.3, duration=5),
        ShieldEffect(base_amount=80),
        GimmickEffect(GimmickOperation.CONSUME, "holy_power", 3)
    ]
    avenging_wrath.costs = [MPCost(7), StackCost("holy_power", 3)]
    avenging_wrath.target_type = "self"
    # avenging_wrath.cooldown = 6  # 쿨다운 시스템 제거됨
    avenging_wrath.sfx = ("skill", "haste")  # 복수의 격노
    avenging_wrath.metadata = {"holy_power_cost": 3, "buff": True, "shield": True}
    skills.append(avenging_wrath)

    # 9. 성스러운 징벌 (NEW - 10번째 스킬 전)
    holy_retribution = Skill("paladin_retribution", "성스러운 징벌", "신성 속성. 성력 4 소비, 신성 폭발")
    holy_retribution.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, stat_type="magical", element="holy", gimmick_bonus={"field": "holy_power", "multiplier": 0.35}),
        BuffEffect(BuffType.ATTACK_DOWN, 0.4, duration=4),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.4, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "holy_power", 4)
    ]
    holy_retribution.costs = [MPCost(10), StackCost("holy_power", 4)]
    holy_retribution.target_type = "all_enemies"
    holy_retribution.is_aoe = True
    holy_retribution.sfx = ("skill", "ultima")
    holy_retribution.metadata = {"element": "holy", "holy_power_cost": 4, "holy_power_scaling": True, "debuff": True, "aoe": True}
    skills.append(holy_retribution)

    # 10. 궁극기: 신성한 폭풍
    ultimate = Skill("paladin_ultimate", "신성한 폭풍", "신성 속성. 성력으로 신성 폭풍 + 파티 힐")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.0, stat_type="magical", element="holy", gimmick_bonus={"field": "holy_power", "multiplier": 0.4}),
        DamageEffect(DamageType.BRV, 2.0, stat_type="magical", element="holy", gimmick_bonus={"field": "holy_power", "multiplier": 0.4}),
        DamageEffect(DamageType.HP, 3.2, stat_type="magical", element="holy"),
        HealEffect(HealType.HP, percentage=0.7, is_party_wide=True),
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=5, is_party_wide=True),
        GimmickEffect(GimmickOperation.SET, "holy_power", 5)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {"ultimate": True, "element": "holy", "holy_power_refill": True, "healing": True, "party": True}
    skills.append(ultimate)

    # 11. 축복의 방패 (Aegis of Grace) - 방어형 스킬
    aegis_of_grace = Skill("paladin_aegis_of_grace", "축복의 방패",
                          "방어력/마법방어력 +30%, 피해 경감 15%, 성력 20 회복. 성력 60+ 시 파티 마방 +15%")
    aegis_of_grace.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.30, duration=3),
        BuffEffect(BuffType.MAGIC_DEFENSE_UP, 0.30, duration=3),
        GimmickEffect(GimmickOperation.ADD, "holy_power", 20, max_value=100)
    ]
    aegis_of_grace.costs = [MPCost(13)]
    aegis_of_grace.target_type = "self"
    aegis_of_grace.sfx = ("skill", "protect")
    aegis_of_grace.metadata = {
        "tank_skill": True,
        "damage_reduction": 0.15,
        "holy_restore": 20,
        "conditional_party_buff": {
            "condition": {"gimmick": "holy_power", "min_value": 60},
            "buff": {"stat": "magic_defense", "value": 0.15, "duration": 3}
        },
        "skill_category": "defense"
    }
    skills.append(aegis_of_grace)

    # 12. 빛의 벽 (Radiant Barrier) - 방어형 스킬
    radiant_barrier = Skill("paladin_radiant_barrier", "빛의 벽",
                           "파티 전체에 HP 20% 비례 보호막 + 방어력 +20%, 보호막 유지 시 마방 +10%")
    radiant_barrier.effects = [
        ShieldEffect(base_amount=0),  # HP 비례 보호막 (메타데이터로 처리)
        BuffEffect(BuffType.DEFENSE_UP, 0.20, duration=2, is_party_wide=True),
        BuffEffect(BuffType.MAGIC_DEFENSE_UP, 0.10, duration=2, is_party_wide=True)
    ]
    radiant_barrier.costs = [MPCost(15)]
    radiant_barrier.target_type = "party"
    radiant_barrier.is_aoe = True
    radiant_barrier.sfx = ("skill", "shell")
    radiant_barrier.metadata = {
        "tank_skill": True,
        "party_buff": True,
        "shield_skill": True,
        "hp_ratio_shield": 0.20,
        "requires_shield_for_magic_def": True,
        "skill_category": "defense"
    }
    skills.append(radiant_barrier)

    # 팀워크 스킬: 신성한 보호
    teamwork = TeamworkSkill(
        "paladin_teamwork",
        "성스러운 수호",
        "아군 전체 방어막 (자신 공격력 × 0.7, 3턴) + 신성 속성 버프",
        gauge_cost=175)
    teamwork.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 1.0, duration=1, is_party_wide=True),  # 방어력 +100% (임시 무효화 효과)
        HealEffect(percentage=0.4, is_party_wide=True),  # HP 40% 회복
        BuffEffect(BuffType.DEFENSE_UP, 0.5, duration=3, is_party_wide=True),  # 방어력 +50%
        BuffEffect(BuffType.MAGIC_DEFENSE_UP, 0.5, duration=3, is_party_wide=True)  # 마법 방어력 +50%
    ]
    teamwork.target_type = "party"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {"teamwork": True, "chain": True, "protection": True, "healing": True}
    skills.append(teamwork)

    return skills

def register_paladin_skills(skill_manager):
    """팔라딘 스킬 등록"""
    skills = create_paladin_skills()
    for skill in skills:
        skill_manager.register_skill(skill)

    # 팀워크 스킬: 성스러운 수호
    return [s.skill_id for s in skills]