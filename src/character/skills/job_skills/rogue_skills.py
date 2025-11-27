"""Rogue Skills - 도적 스킬 (아이템/훔치기 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_rogue_skills():
    """도적 10개 스킬 (아이템/훔치기 시스템)"""

    skills = []

    # 1. 기본 BRV: 기습
    ambush = Skill("rogue_ambush", "기습", "빠른 기습 공격, 아이템 획득")
    ambush.effects = [
        DamageEffect(DamageType.BRV, 1.3),
        GimmickEffect(GimmickOperation.ADD, "stolen_items", 1, max_value=10)
    ]
    ambush.costs = []  # 기본 공격은 MP 소모 없음
    ambush.sfx = ("combat", "attack_physical")  # 기습
    ambush.metadata = {"item_gain": 1}
    skills.append(ambush)

    # 2. 기본 HP: 급소 공격
    vital_strike = Skill("rogue_vital_strike", "급소 공격", "치명타 확정")
    vital_strike.effects = [
        DamageEffect(DamageType.HP, 1.2, gimmick_bonus={"field": "stolen_items", "multiplier": 0.15})
    ]
    vital_strike.costs = []  # 기본 공격은 MP 소모 없음
    vital_strike.sfx = ("combat", "critical")  # 급소 공격
    vital_strike.metadata = {"item_scaling": True, "critical": True}
    skills.append(vital_strike)

    # 3. 훔치기
    steal = Skill("rogue_steal", "훔치기", "적의 버프/자원 훔치기")
    steal.effects = [
        GimmickEffect(GimmickOperation.ADD, "stolen_items", 3, max_value=10),
        BuffEffect(BuffType.SPEED_UP, 0.2, duration=3, target="self"),  # 자신에게 속도 증가
        BuffEffect(BuffType.SPEED_DOWN, 0.2, duration=3)  # 적에게 속도 감소
    ]
    steal.costs = []
    # steal.cooldown = 3  # 쿨다운 시스템 제거됨
    steal.sfx = ("item", "get_item")  # 훔치기
    steal.metadata = {"item_gain": 3, "buff": True}
    skills.append(steal)

    # 4. 연막탄
    smoke_bomb = Skill("rogue_smoke", "연막탄", "회피 + 아이템 사용")
    smoke_bomb.effects = [
        GimmickEffect(GimmickOperation.SET, "evasion_active", 1),
        BuffEffect(BuffType.EVASION_UP, 0.4, duration=2)
    ]
    smoke_bomb.costs = [MPCost(3)]
    smoke_bomb.target_type = "self"
    # smoke_bomb.cooldown = 4  # 쿨다운 시스템 제거됨
    smoke_bomb.sfx = ("combat", "dodge")  # 연막탄
    smoke_bomb.metadata = {"evasion": True, "buff": True}
    skills.append(smoke_bomb)

    # 5. 아이템 활용
    use_item = Skill("rogue_use_item", "아이템 활용", "훔친 아이템으로 공격")
    use_item.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, gimmick_bonus={"field": "stolen_items", "multiplier": 0.25})
    ]
    use_item.costs = [MPCost(6), StackCost("stolen_items", 2)]
    # use_item.cooldown = 2  # 쿨다운 시스템 제거됨
    use_item.sfx = ("item", "grenade")  # 아이템 활용
    use_item.metadata = {"item_cost": 2, "item_scaling": True}
    skills.append(use_item)

    # 6. 독 바르기
    poison_blade = Skill("rogue_poison", "독 바르기", "지속 피해")
    poison_blade.effects = [
        DamageEffect(DamageType.BRV, 1.2),
        DamageEffect(DamageType.BRV, 0.8),
        DamageEffect(DamageType.BRV, 0.8),
        GimmickEffect(GimmickOperation.ADD, "stolen_items", 1, max_value=10)
    ]
    poison_blade.costs = [MPCost(4)]
    # poison_blade.cooldown = 3  # 쿨다운 시스템 제거됨
    poison_blade.sfx = ("character", "status_debuff")  # 독 바르기
    poison_blade.metadata = {"item_gain": 1, "dot": True, "poison": True}
    skills.append(poison_blade)

    # 7. 보물 사냥
    treasure_hunt = Skill("rogue_treasure", "보물 사냥", "골드/아이템 대량 획득")
    treasure_hunt.effects = [
        GimmickEffect(GimmickOperation.ADD, "stolen_items", 5, max_value=10),
        BuffEffect(BuffType.LUCK, 0.3, duration=4)
    ]
    treasure_hunt.costs = [MPCost(6)]
    treasure_hunt.target_type = "self"
    # treasure_hunt.cooldown = 5  # 쿨다운 시스템 제거됨
    treasure_hunt.sfx = ("item", "get_item")  # 보물 사냥
    treasure_hunt.metadata = {"item_gain": 5, "buff": True}
    skills.append(treasure_hunt)

    # 8. 배신자의 일격
    backstab = Skill("rogue_backstab", "배신자의 일격", "아이템 소비 초강타")
    backstab.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, gimmick_bonus={"field": "stolen_items", "multiplier": 0.4})
    ]
    backstab.costs = [MPCost(9), StackCost("stolen_items", 4)]
    # backstab.cooldown = 5  # 쿨다운 시스템 제거됨
    backstab.sfx = ("combat", "critical")  # 배신자의 일격
    backstab.metadata = {"item_cost": 4, "item_scaling": True, "critical": True}
    skills.append(backstab)

    # 9. 암살 (NEW - 10번째 스킬 전)
    assassinate = Skill("rogue_assassinate", "암살", "아이템 6개 소비, 즉사 위협")
    assassinate.effects = [
        DamageEffect(DamageType.BRV_HP, 3.0, gimmick_bonus={"field": "stolen_items", "multiplier": 0.5}),
        BuffEffect(BuffType.CRITICAL_UP, 0.6, duration=3),
        BuffEffect(BuffType.ATTACK_DOWN, 0.4, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "stolen_items", 6)
    ]
    assassinate.costs = [MPCost(13), StackCost("stolen_items", 6)]
    # assassinate.cooldown = 7  # 쿨다운 시스템 제거됨
    assassinate.sfx = ("combat", "damage_high")  # 암살
    assassinate.metadata = {"item_cost": 6, "item_scaling": True, "critical": True, "debuff": True}
    skills.append(assassinate)

    # 10. 궁극기: 완벽한 강탈
    ultimate = Skill("rogue_ultimate", "완벽한 강탈", "모든 것을 훔치는 궁극기")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "stolen_items", "multiplier": 0.5}),
        DamageEffect(DamageType.HP, 3.0),
        GimmickEffect(GimmickOperation.SET, "stolen_items", 10),
        BuffEffect(BuffType.SPEED_UP, 0.5, duration=5),
        BuffEffect(BuffType.CRITICAL_UP, 0.4, duration=5)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15  # 궁극기 쿨타임 15턴
    ultimate.sfx = ("skill", "limit_break")  # 궁극기
    ultimate.metadata = {"ultimate": True, "item_refill": True, "buff": True, "critical": True}
    skills.append(ultimate)

    return skills

def register_rogue_skills(skill_manager):
    skills = create_rogue_skills()
    for skill in skills:
        skill_manager.register_skill(skill)

    # 팀워크 스킬: 빠른 손놀림
    teamwork = TeamworkSkill(
        "rogue_teamwork",
        "빠른 손놀림",
        "단일 대상 BRV 공격 (1.2x) + 아이템 1개 훔침 (확률 60%) + ATB +300",
        gauge_cost=50
    )
    teamwork.effects = []  # TODO: 효과 추가
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "limit_break")
    teamwork.metadata = {"teamwork": True, "chain": True}
    skills.append(teamwork)
    return [s.skill_id for s in skills, teamwork]
