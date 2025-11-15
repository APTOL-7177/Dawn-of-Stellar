"""Samurai Skills - 사무라이 스킬 (의지 게이지 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_samurai_skills():
    """사무라이 9개 스킬 생성"""

    # 1. 기본 BRV: 거합 베기
    iaido = Skill("samurai_iaido", "거합 베기", "의지 게이지 획득")
    iaido.effects = [
        DamageEffect(DamageType.BRV, 1.6),
        GimmickEffect(GimmickOperation.ADD, "will_gauge", 1, max_value=5)
    ]
    iaido.costs = []  # 기본 공격은 MP 소모 없음

    # 2. 기본 HP: 참월
    moonlight_slash = Skill("samurai_moonlight_slash", "참월", "의지 소비 공격")
    moonlight_slash.effects = [
        DamageEffect(DamageType.HP, 1.2, gimmick_bonus={"field": "will_gauge", "multiplier": 0.35}),
        GimmickEffect(GimmickOperation.CONSUME, "will_gauge", 1)
    ]
    moonlight_slash.costs = []  # 기본 공격은 MP 소모 없음

    # 3. 명경지수
    clear_mind = Skill("samurai_clear_mind", "명경지수", "의지 2게이지 획득")
    clear_mind.effects = [
        GimmickEffect(GimmickOperation.ADD, "will_gauge", 2, max_value=5),
        BuffEffect(BuffType.ACCURACY_UP, 0.5, duration=3)
    ]
    clear_mind.costs = [MPCost(6)]
    clear_mind.target_type = "self"
    clear_mind.cooldown = 2

    # 4. 발도술
    battojutsu = Skill("samurai_battojutsu", "발도술", "의지 2게이지 소비, 빠른 베기")
    battojutsu.effects = [
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "will_gauge", "multiplier": 0.3}),
        GimmickEffect(GimmickOperation.CONSUME, "will_gauge", 2)
    ]
    battojutsu.costs = [MPCost(8), StackCost("will_gauge", 2)]
    battojutsu.cast_time = 0.5
    battojutsu.cooldown = 2

    # 5. 무사의 명예
    samurai_honor = Skill("samurai_samurai_honor", "무사의 명예", "의지 최대 회복")
    samurai_honor.effects = [
        GimmickEffect(GimmickOperation.SET, "will_gauge", 5),
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=4),
        BuffEffect(BuffType.DEFENSE_UP, 0.3, duration=4)
    ]
    samurai_honor.costs = [MPCost(9)]
    samurai_honor.target_type = "self"
    samurai_honor.cooldown = 5

    # 6. 무쌍검
    musou_ken = Skill("samurai_musou_ken", "무쌍검", "의지 3게이지 소비, 다연타")
    musou_ken.effects = [
        DamageEffect(DamageType.BRV, 1.5),
        DamageEffect(DamageType.BRV, 1.5),
        DamageEffect(DamageType.HP, 1.5, gimmick_bonus={"field": "will_gauge", "multiplier": 0.4}),
        GimmickEffect(GimmickOperation.CONSUME, "will_gauge", 3)
    ]
    musou_ken.costs = [MPCost(11), StackCost("will_gauge", 3)]
    musou_ken.cooldown = 4

    # 7. 비연참
    flying_swallow = Skill("samurai_flying_swallow", "비연참", "의지 4게이지 소비, 공중 공격")
    flying_swallow.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, gimmick_bonus={"field": "will_gauge", "multiplier": 0.5}),
        GimmickEffect(GimmickOperation.CONSUME, "will_gauge", 4)
    ]
    flying_swallow.costs = [MPCost(14), StackCost("will_gauge", 4)]
    flying_swallow.cooldown = 5

    # 8. 진 발도
    true_battojutsu = Skill("samurai_true_battojutsu", "진 발도", "의지 5게이지 소비, 극한의 베기")
    true_battojutsu.effects = [
        DamageEffect(DamageType.BRV, 3.0, gimmick_bonus={"field": "will_gauge", "multiplier": 0.6}),
        DamageEffect(DamageType.HP, 2.0),
        GimmickEffect(GimmickOperation.CONSUME, "will_gauge", 5)
    ]
    true_battojutsu.costs = [MPCost(16), StackCost("will_gauge", 5)]
    true_battojutsu.cooldown = 6

    # 9. 궁극기: 천상천하 유아독존
    ultimate = Skill("samurai_ultimate", "천상천하 유아독존", "궁극의 의지로 무를 베다")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "will_gauge", "multiplier": 0.5}),
        DamageEffect(DamageType.BRV, 2.5, gimmick_bonus={"field": "will_gauge", "multiplier": 0.5}),
        DamageEffect(DamageType.HP, 3.5, gimmick_bonus={"field": "will_gauge", "multiplier": 0.7}),
        BuffEffect(BuffType.ATTACK_UP, 0.8, duration=5),
        GimmickEffect(GimmickOperation.SET, "will_gauge", 0)
    ]
    ultimate.costs = [MPCost(25), StackCost("will_gauge", 1)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 10

    return [iaido, moonlight_slash, clear_mind, battojutsu, samurai_honor,
            musou_ken, flying_swallow, true_battojutsu, ultimate]

def register_samurai_skills(skill_manager):
    """사무라이 스킬 등록"""
    skills = create_samurai_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
