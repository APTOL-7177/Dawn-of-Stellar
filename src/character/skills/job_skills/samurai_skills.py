"""Samurai Skills - 사무라이 스킬 (의지 게이지 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_samurai_skills():
    """사무라이 10개 스킬 생성 (의지 게이지 시스템)"""

    skills = []

    # 1. 기본 BRV: 거합 베기
    iaido = Skill("samurai_iaido", "거합 베기", "의지 게이지 획득")
    iaido.effects = [
        DamageEffect(DamageType.BRV, 1.6),
        GimmickEffect(GimmickOperation.ADD, "will_gauge", 1, max_value=10)
    ]
    iaido.costs = []  # 기본 공격은 MP 소모 없음
    iaido.sfx = ("combat", "attack_physical")  # 거합 베기
    iaido.metadata = {"will_gain": 1}
    skills.append(iaido)

    # 2. 기본 HP: 참월
    moonlight_slash = Skill("samurai_moonlight_slash", "참월", "의지 소비 공격")
    moonlight_slash.effects = [
        DamageEffect(DamageType.HP, 1.2, gimmick_bonus={"field": "will_gauge", "multiplier": 0.35}),
        GimmickEffect(GimmickOperation.CONSUME, "will_gauge", 1)
    ]
    moonlight_slash.costs = []  # 기본 공격은 MP 소모 없음
    moonlight_slash.sfx = ("combat", "critical")  # 참월
    moonlight_slash.metadata = {"will_cost": 1, "will_scaling": True}
    skills.append(moonlight_slash)

    # 3. 명경지수
    clear_mind = Skill("samurai_clear_mind", "명경지수", "의지 2게이지 획득")
    clear_mind.effects = [
        GimmickEffect(GimmickOperation.ADD, "will_gauge", 2, max_value=10),
        BuffEffect(BuffType.ACCURACY_UP, 0.5, duration=3)
    ]
    clear_mind.costs = []
    clear_mind.target_type = "self"
    # clear_mind.cooldown = 2  # 쿨다운 시스템 제거됨
    clear_mind.sfx = ("character", "status_buff")  # 명경지수
    clear_mind.metadata = {"will_gain": 2, "buff": True}
    skills.append(clear_mind)

    # 4. 발도술
    battojutsu = Skill("samurai_battojutsu", "발도술", "의지 2게이지 소비, 빠른 베기")
    battojutsu.effects = [
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "will_gauge", "multiplier": 0.3}),
        GimmickEffect(GimmickOperation.CONSUME, "will_gauge", 2)
    ]
    battojutsu.costs = [MPCost(4), StackCost("will_gauge", 2)]
    battojutsu.cast_time = 0.5
    # battojutsu.cooldown = 2  # 쿨다운 시스템 제거됨
    battojutsu.sfx = ("combat", "attack_physical")  # 발도술
    battojutsu.metadata = {"will_cost": 2, "will_scaling": True, "quick_draw": True}
    skills.append(battojutsu)

    # 5. 무사의 명예
    samurai_honor = Skill("samurai_samurai_honor", "무사의 명예", "의지 최대 회복")
    samurai_honor.effects = [
        GimmickEffect(GimmickOperation.SET, "will_gauge", 10, max_value=10),  # 최대치로 설정
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=4),
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=4)
    ]
    samurai_honor.costs = [MPCost(6)]
    samurai_honor.target_type = "self"
    # samurai_honor.cooldown = 4  # 쿨다운 시스템 제거됨
    samurai_honor.sfx = ("skill", "haste")  # 무사의 명예
    samurai_honor.metadata = {"will_refill": True, "buff": True}
    skills.append(samurai_honor)

    # 6. 무쌍검
    musou_ken = Skill("samurai_musou_ken", "무쌍검", "의지 3게이지 소비, 다연타")
    musou_ken.effects = [
        DamageEffect(DamageType.BRV, 1.5),
        DamageEffect(DamageType.BRV, 1.5),
        DamageEffect(DamageType.HP, 1.5, gimmick_bonus={"field": "will_gauge", "multiplier": 0.4}),
        GimmickEffect(GimmickOperation.CONSUME, "will_gauge", 3)
    ]
    musou_ken.costs = [MPCost(7), StackCost("will_gauge", 3)]
    # musou_ken.cooldown = 4  # 쿨다운 시스템 제거됨
    musou_ken.sfx = ("combat", "attack_physical")  # 무쌍검
    musou_ken.metadata = {"will_cost": 3, "will_scaling": True, "multi_hit": True}
    skills.append(musou_ken)

    # 7. 비연참
    flying_swallow = Skill("samurai_flying_swallow", "비연참", "의지 4게이지 소비, 공중 공격")
    flying_swallow.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, gimmick_bonus={"field": "will_gauge", "multiplier": 0.5}),
        GimmickEffect(GimmickOperation.CONSUME, "will_gauge", 4)
    ]
    flying_swallow.costs = [MPCost(9), StackCost("will_gauge", 4)]
    # flying_swallow.cooldown = 5  # 쿨다운 시스템 제거됨
    flying_swallow.sfx = ("world", "jump")  # 비연참
    flying_swallow.metadata = {"will_cost": 4, "will_scaling": True, "aerial": True}
    skills.append(flying_swallow)

    # 8. 진 발도
    true_battojutsu = Skill("samurai_true_battojutsu", "진 발도", "의지 5게이지 소비, 극한의 베기")
    true_battojutsu.effects = [
        DamageEffect(DamageType.BRV, 3.0, gimmick_bonus={"field": "will_gauge", "multiplier": 0.6}),
        DamageEffect(DamageType.HP, 2.0),
        GimmickEffect(GimmickOperation.CONSUME, "will_gauge", 5)
    ]
    true_battojutsu.costs = [MPCost(10), StackCost("will_gauge", 5)]
    # true_battojutsu.cooldown = 6  # 쿨다운 시스템 제거됨
    true_battojutsu.sfx = ("combat", "damage_high")  # 진 발도
    true_battojutsu.metadata = {"will_cost": 5, "will_scaling": True, "true_strike": True}
    skills.append(true_battojutsu)

    # 9. 무한 베기 (NEW - 10번째 스킬)
    infinite_slash = Skill("samurai_infinite_slash", "무한 베기", "의지 소비 없는 연속 공격")
    infinite_slash.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0),
        BuffEffect(BuffType.SPEED_UP, 0.3, duration=3),
        GimmickEffect(GimmickOperation.ADD, "will_gauge", 1, max_value=10)
    ]
    infinite_slash.costs = [MPCost(12)]
    # infinite_slash.cooldown = 5  # 쿨다운 시스템 제거됨
    infinite_slash.target_type = "all_enemies"
    infinite_slash.sfx = ("skill", "cast_complete")  # 무한 베기
    infinite_slash.metadata = {"will_gain": 1, "high_damage": True}
    infinite_slash.is_aoe = True
    skills.append(infinite_slash)

    # 10. 궁극기: 천상천하 유아독존
    ultimate = Skill("samurai_ultimate", "천상천하 유아독존", "궁극의 의지로 무를 베다")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "will_gauge", "multiplier": 0.5}),
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "will_gauge", "multiplier": 0.5}),
        DamageEffect(DamageType.HP, 3.5, gimmick_bonus={"field": "will_gauge", "multiplier": 0.7}),
        BuffEffect(BuffType.ATTACK_UP, 0.8, duration=5),
        GimmickEffect(GimmickOperation.SET, "will_gauge", 0)
    ]
    ultimate.costs = [MPCost(30), StackCost("will_gauge", 1)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15  # 궁극기 쿨타임 15턴
    ultimate.sfx = ("skill", "limit_break")  # 궁극기
    ultimate.metadata = {"ultimate": True, "will_dump": True, "supreme_strike": True}
    skills.append(ultimate)

    # 팀워크 스킬: 사무라이의 정신
    teamwork = TeamworkSkill(
        "samurai_teamwork",
        "거합: 섬광",
        "단일 대상 HP 공격 (3.5x) + BREAK 시 wound damage 3배 + 거합 게이지 초기화",
        gauge_cost=200)
    teamwork.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=3, is_party_wide=True),  # 공격력 +50%
        BuffEffect(BuffType.DEFENSE_DOWN, 0.3, duration=2, is_party_wide=True),  # 적 전체 방어력 -30%
        GimmickEffect(GimmickOperation.SET, "resolve", 100),  # 의지(거합) 게이지 완전 회복
    ]
    teamwork.target_type = "party"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {"teamwork": True, "chain": True, "buff": True, "will": True}
    skills.append(teamwork)

    return skills

def register_samurai_skills(skill_manager):
    """사무라이 스킬 등록"""
    skills = create_samurai_skills()
    for skill in skills:
        skill_manager.register_skill(skill)

    # 팀워크 스킬: 거합: 섬광
    return [s.skill_id for s in skills]