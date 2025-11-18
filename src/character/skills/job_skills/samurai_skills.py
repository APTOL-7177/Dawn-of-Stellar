"""Samurai Skills - 사무라이 스킬 (의지 게이지 시스템)"""
from src.character.skills.skill import Skill
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
        GimmickEffect(GimmickOperation.ADD, "will_gauge", 1, max_value=5)
    ]
    iaido.costs = []  # 기본 공격은 MP 소모 없음
    iaido.sfx = "338"
    iaido.metadata = {"will_gain": 1}
    skills.append(iaido)

    # 2. 기본 HP: 참월
    moonlight_slash = Skill("samurai_moonlight_slash", "참월", "의지 소비 공격")
    moonlight_slash.effects = [
        DamageEffect(DamageType.HP, 1.2, gimmick_bonus={"field": "will_gauge", "multiplier": 0.35}),
        GimmickEffect(GimmickOperation.CONSUME, "will_gauge", 1)
    ]
    moonlight_slash.costs = []  # 기본 공격은 MP 소모 없음
    moonlight_slash.sfx = "345"
    moonlight_slash.metadata = {"will_cost": 1, "will_scaling": True}
    skills.append(moonlight_slash)

    # 3. 명경지수
    clear_mind = Skill("samurai_clear_mind", "명경지수", "의지 2게이지 획득")
    clear_mind.effects = [
        GimmickEffect(GimmickOperation.ADD, "will_gauge", 2, max_value=5),
        BuffEffect(BuffType.ACCURACY_UP, 0.5, duration=3)
    ]
    clear_mind.costs = []
    clear_mind.target_type = "self"
    # clear_mind.cooldown = 2  # 쿨다운 시스템 제거됨
    clear_mind.sfx = "352"
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
    battojutsu.sfx = "359"
    battojutsu.metadata = {"will_cost": 2, "will_scaling": True, "quick_draw": True}
    skills.append(battojutsu)

    # 5. 무사의 명예
    samurai_honor = Skill("samurai_samurai_honor", "무사의 명예", "의지 최대 회복")
    samurai_honor.effects = [
        GimmickEffect(GimmickOperation.SET, "will_gauge", 5),
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=4),
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=4)
    ]
    samurai_honor.costs = [MPCost(6)]
    samurai_honor.target_type = "self"
    # samurai_honor.cooldown = 4  # 쿨다운 시스템 제거됨
    samurai_honor.sfx = "366"
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
    musou_ken.sfx = "373"
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
    flying_swallow.sfx = "380"
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
    true_battojutsu.sfx = "387"
    true_battojutsu.metadata = {"will_cost": 5, "will_scaling": True, "true_strike": True}
    skills.append(true_battojutsu)

    # 9. 무한 베기 (NEW - 10번째 스킬)
    infinite_slash = Skill("samurai_infinite_slash", "무한 베기", "의지 소비 없는 연속 공격")
    infinite_slash.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0),
        BuffEffect(BuffType.SPEED_UP, 0.3, duration=3),
        GimmickEffect(GimmickOperation.ADD, "will_gauge", 1, max_value=5)
    ]
    infinite_slash.costs = [MPCost(12)]
    # infinite_slash.cooldown = 5  # 쿨다운 시스템 제거됨
    infinite_slash.sfx = "394"
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
    # ultimate.cooldown = 8  # 쿨다운 시스템 제거됨
    ultimate.sfx = "401"
    ultimate.metadata = {"ultimate": True, "will_dump": True, "supreme_strike": True}
    skills.append(ultimate)

    return skills

def register_samurai_skills(skill_manager):
    """사무라이 스킬 등록"""
    skills = create_samurai_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
