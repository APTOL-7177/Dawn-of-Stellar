"""Knight Skills - 기사 스킬 (의무/수호 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.shield_effect import ShieldEffect
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.protect_effect import ProtectEffect
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_knight_skills():
    """기사 10개 스킬 (의무/수호 시스템)"""
    skills = []

    # 1. 기본 BRV: 창 돌격
    lance_charge = Skill("knight_lance", "창 돌격", "돌격 공격, 의무 생성")
    lance_charge.effects = [
        DamageEffect(DamageType.BRV, 1.4),
        GimmickEffect(GimmickOperation.ADD, "duty_stacks", 1, max_value=5)
    ]
    lance_charge.costs = []  # 기본 공격은 MP 소모 없음
    lance_charge.sfx = ("combat", "attack_physical")  # 창 돌격
    lance_charge.metadata = {"duty_gain": 1}
    skills.append(lance_charge)

    # 2. 기본 HP: 의무의 일격
    duty_strike = Skill("knight_duty_strike", "의무의 일격", "의무 소비 공격")
    duty_strike.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "duty_stacks", "multiplier": 0.3}),
        GimmickEffect(GimmickOperation.CONSUME, "duty_stacks", 1)
    ]
    duty_strike.costs = []  # 기본 공격은 MP 소모 없음
    duty_strike.sfx = ("skill", "slash")  # 의무의 일격
    duty_strike.metadata = {"duty_cost": 1, "duty_scaling": True}
    skills.append(duty_strike)

    # 3. 수호의 맹세
    guardian_oath = Skill("knight_oath", "수호의 맹세", "본인에게 보호막을 두르고 선택한 아군을 보호")
    guardian_oath.effects = [
        ShieldEffect(base_amount=0),  # 공격력 기반으로 계산 (base_amount는 0)
        ProtectEffect(),  # 선택한 아군 보호
        GimmickEffect(GimmickOperation.ADD, "duty_stacks", 1, max_value=5)
    ]
    guardian_oath.costs = []
    guardian_oath.target_type = "ally"  # 아군 선택
    # guardian_oath.cooldown = 3  # 쿨다운 시스템 제거됨
    guardian_oath.sfx = ("skill", "protect")  # 보호막
    guardian_oath.metadata = {"shield": True, "duty_gain": 1, "protect": True, "attack_multiplier": 0.4, "replace_shield": True}  # 공격력의 40%, 중첩 방지
    skills.append(guardian_oath)

    # 4. 기사도
    chivalry = Skill("knight_chivalry", "기사도", "의무로 방어력 증가")
    chivalry.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.35, duration=4),
        BuffEffect(BuffType.SPIRIT_UP, 0.35, duration=4),
        GimmickEffect(GimmickOperation.ADD, "duty_stacks", 1, max_value=5)
    ]
    chivalry.costs = [MPCost(5)]
    chivalry.target_type = "self"
    # chivalry.cooldown = 4  # 쿨다운 시스템 제거됨
    chivalry.sfx = ("character", "status_buff")  # 버프
    chivalry.metadata = {"buff": True, "duty_gain": 1, "defensive": True}
    skills.append(chivalry)

    # 5. 불굴의 의지
    iron_will = Skill("knight_iron_will", "불굴의 의지", "의무 1 소비, 강력한 보호막 + 의무 2 획득")
    iron_will.effects = [
        ShieldEffect(base_amount=0),  # 공격력 기반으로 계산
        GimmickEffect(GimmickOperation.CONSUME, "duty_stacks", 1),
        GimmickEffect(GimmickOperation.ADD, "duty_stacks", 2, max_value=5)
    ]
    iron_will.costs = [MPCost(6), StackCost("duty_stacks", 1)]
    iron_will.target_type = "self"
    # iron_will.cooldown = 5  # 쿨다운 시스템 제거됨
    iron_will.sfx = ("skill", "shell")  # 방어막
    iron_will.metadata = {"shield": True, "duty_cost": 1, "duty_gain": 2, "attack_multiplier": 0.8}  # 공격력의 80%
    skills.append(iron_will)

    # 6. 방패 강타
    shield_bash = Skill("knight_bash", "방패 강타", "의무 1 소비, 방어 + 공격 + 의무 1 획득")
    shield_bash.effects = [
        DamageEffect(DamageType.BRV, 1.8, gimmick_bonus={"field": "duty_stacks", "multiplier": 0.2}),
        ShieldEffect(base_amount=0),  # 공격력 기반으로 계산
        GimmickEffect(GimmickOperation.CONSUME, "duty_stacks", 1),
        GimmickEffect(GimmickOperation.ADD, "duty_stacks", 1, max_value=5)
    ]
    shield_bash.costs = [MPCost(4), StackCost("duty_stacks", 1)]
    # shield_bash.cooldown = 2  # 쿨다운 시스템 제거됨
    shield_bash.sfx = ("combat", "attack_physical")  # 방패 강타
    shield_bash.metadata = {"shield": True, "duty_cost": 1, "duty_gain": 1, "duty_scaling": True, "attack_multiplier": 0.6}  # 공격력의 60%
    skills.append(shield_bash)

    # 7. 최후의 보루
    last_stand = Skill("knight_last_stand", "최후의 보루", "의무 3 소비, 생존")
    last_stand.effects = [
        ShieldEffect(base_amount=0),  # 공격력 기반으로 계산
        BuffEffect(BuffType.DEFENSE_UP, 0.5, duration=3),
        GimmickEffect(GimmickOperation.CONSUME, "duty_stacks", 3)
    ]
    last_stand.costs = [MPCost(7), StackCost("duty_stacks", 3)]
    last_stand.target_type = "self"
    # last_stand.cooldown = 6  # 쿨다운 시스템 제거됨
    last_stand.sfx = ("combat", "damage_high")  # 최후의 보루
    last_stand.metadata = {"shield": True, "duty_cost": 3, "defensive": True, "attack_multiplier": 1.2}  # 공격력의 120%
    skills.append(last_stand)

    # 8. 헌신
    devotion = Skill("knight_devotion", "헌신", "의무 2 소비, 파티 전체 보호 + 의무 1 획득")
    devotion.effects = [
        ShieldEffect(base_amount=0),  # 공격력 기반으로 계산
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=4, is_party_wide=True),
        GimmickEffect(GimmickOperation.CONSUME, "duty_stacks", 2),
        GimmickEffect(GimmickOperation.ADD, "duty_stacks", 1, max_value=5)
    ]
    devotion.costs = [MPCost(7), StackCost("duty_stacks", 2)]
    devotion.target_type = "party"
    # devotion.cooldown = 6  # 쿨다운 시스템 제거됨
    devotion.sfx = ("character", "status_buff")  # 파티 보호
    devotion.metadata = {"shield": True, "party": True, "duty_cost": 2, "duty_gain": 1, "attack_multiplier": 0.9}  # 공격력의 90%
    skills.append(devotion)

    # 9. 기사의 맹세 (NEW - 10번째 스킬 전)
    knight_pledge = Skill("knight_pledge", "기사의 맹세", "의무 4 소비, 강력한 보호와 반격")
    knight_pledge.effects = [
        ShieldEffect(base_amount=0),  # 공격력 기반으로 계산
        BuffEffect(BuffType.DEFENSE_UP, 0.5, duration=4),
        BuffEffect(BuffType.COUNTER, 0.6, duration=4),
        GimmickEffect(GimmickOperation.CONSUME, "duty_stacks", 4)
    ]
    knight_pledge.costs = [MPCost(10), StackCost("duty_stacks", 4)]
    knight_pledge.target_type = "self"
    # knight_pledge.cooldown = 7  # 쿨다운 시스템 제거됨
    knight_pledge.sfx = ("combat", "break")  # 기사의 맹세
    knight_pledge.metadata = {"shield": True, "duty_cost": 4, "counter": True, "attack_multiplier": 1.4}  # 공격력의 140%
    skills.append(knight_pledge)

    # 10. 궁극기: 성스러운 돌격
    ultimate = Skill("knight_ultimate", "성스러운 돌격", "모든 의무로 최후 돌격")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "duty_stacks", "multiplier": 0.5}),
        DamageEffect(DamageType.HP, 3.0),
        ShieldEffect(base_amount=0),  # 공격력 기반으로 계산
        BuffEffect(BuffType.DEFENSE_UP, 0.6, duration=5, is_party_wide=True),
        GimmickEffect(GimmickOperation.SET, "duty_stacks", 5)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15  # 궁극기 쿨타임 15턴
    ultimate.sfx = ("skill", "limit_break")  # 궁극기
    ultimate.metadata = {"ultimate": True, "duty_scaling": True, "duty_refill": True, "shield": True, "attack_multiplier": 1.4}  # 공격력의 140%
    skills.append(ultimate)

    return skills

def register_knight_skills(skill_manager):
    skills = create_knight_skills()
    for skill in skills:
        skill_manager.register_skill(skill)

    # 팀워크 스킬: 불굴의 방패
    teamwork = TeamworkSkill(
        "knight_teamwork",
        "불굴의 방패",
        "아군 전체에 방어막 부여 (자신 공격력 × 0.5, 2턴) + 의무 +2",
        gauge_cost=125
    )
    teamwork.effects = []  # TODO: 효과 추가
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "limit_break")
    teamwork.metadata = {"teamwork": True, "chain": True}
    skills.append(teamwork)
    return [s.skill_id for s in skills, teamwork]
