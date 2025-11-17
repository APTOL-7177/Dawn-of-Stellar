"""Sword Saint Skills - 검성 스킬 (검기 스택 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_sword_saint_skills():
    """검성 10개 스킬 생성 (검기 스택 시스템)"""

    skills = []

    # 1. 기본 BRV: 검기 베기
    kenkizan = Skill("sword_saint_kenkizan", "검기 베기", "적을 베어 검기 스택 획득")
    kenkizan.effects = [
        DamageEffect(DamageType.BRV, 1.5),
        GimmickEffect(GimmickOperation.ADD, "sword_aura", 1, max_value=5)
    ]
    kenkizan.costs = []  # 기본 공격은 MP 소모 없음
    kenkizan.sfx = "548"
    kenkizan.metadata = {"aura_gain": 1}
    skills.append(kenkizan)

    # 2. 기본 HP: 일섬
    ilseom = Skill("sword_saint_ilseom", "일섬", "검기 스택 소비하여 강력한 HP 공격")
    ilseom.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "sword_aura", "multiplier": 0.3}),
        GimmickEffect(GimmickOperation.CONSUME, "sword_aura", 1)
    ]
    ilseom.costs = []  # 기본 공격은 MP 소모 없음
    ilseom.sfx = "555"
    ilseom.metadata = {"aura_cost": 1, "aura_scaling": True}
    skills.append(ilseom)

    # 3. 검기 파동
    kenki_hadou = Skill("sword_saint_kenki_hadou", "검기 파동", "관통 공격")
    kenki_hadou.effects = [
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "sword_aura", "multiplier": 0.2}),
        GimmickEffect(GimmickOperation.ADD, "sword_aura", 1, max_value=5)
    ]
    kenki_hadou.costs = [MPCost(6)]
    # kenki_hadou.cooldown = 2  # 쿨다운 시스템 제거됨
    kenki_hadou.sfx = "562"
    kenki_hadou.metadata = {"aura_gain": 1, "piercing": True}
    skills.append(kenki_hadou)

    # 4. 이도류
    nitoryu = Skill("sword_saint_nitoryu", "이도류", "검기 2스택 소비, 2연속 공격")
    nitoryu.effects = [
        DamageEffect(DamageType.BRV, 1.8),
        DamageEffect(DamageType.HP, 1.2),
        GimmickEffect(GimmickOperation.CONSUME, "sword_aura", 2)
    ]
    nitoryu.costs = [MPCost(8), StackCost("sword_aura", 2)]
    # nitoryu.cooldown = 3  # 쿨다운 시스템 제거됨
    nitoryu.sfx = "569"
    nitoryu.metadata = {"aura_cost": 2, "dual_wield": True}
    skills.append(nitoryu)

    # 5. 검기 폭발
    kenki_bakuhatsu = Skill("sword_saint_kenki_bakuhatsu", "검기 폭발", "모든 검기 폭발")
    kenki_bakuhatsu.effects = [
        DamageEffect(DamageType.BRV_HP, 1.5, gimmick_bonus={"field": "sword_aura", "multiplier": 0.4}),
        GimmickEffect(GimmickOperation.SET, "sword_aura", 0)
    ]
    kenki_bakuhatsu.costs = [MPCost(10), StackCost("sword_aura", 1)]
    # kenki_bakuhatsu.cooldown = 4  # 쿨다운 시스템 제거됨
    kenki_bakuhatsu.sfx = "576"
    kenki_bakuhatsu.metadata = {"aura_dump": True, "aura_scaling": True}
    skills.append(kenki_bakuhatsu)

    # 6. 초고속 베기
    rapid_slash = Skill("sword_saint_rapid_slash", "초고속 베기", "빠른 베기, 검기 2스택 획득")
    rapid_slash.effects = [
        DamageEffect(DamageType.BRV, 1.2),
        GimmickEffect(GimmickOperation.ADD, "sword_aura", 2, max_value=5)
    ]
    rapid_slash.costs = [MPCost(5)]
    rapid_slash.cast_time = 0.5
    # rapid_slash.cooldown = 2  # 쿨다운 시스템 제거됨
    rapid_slash.sfx = "583"
    rapid_slash.metadata = {"aura_gain": 2, "quick": True}
    skills.append(rapid_slash)

    # 7. 검성의 의지
    will = Skill("sword_saint_will", "검성의 의지", "검기 스택 최대 회복")
    will.effects = [
        GimmickEffect(GimmickOperation.SET, "sword_aura", 5)
    ]
    will.costs = [MPCost(8)]
    will.target_type = "self"
    # will.cooldown = 4  # 쿨다운 시스템 제거됨
    will.sfx = "590"
    will.metadata = {"aura_refill": True}
    skills.append(will)

    # 8. 일도양단
    bisect = Skill("sword_saint_bisect", "일도양단", "검기 3스택 소비, 절대적 일격")
    bisect.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, gimmick_bonus={"field": "sword_aura", "multiplier": 0.5}),
        GimmickEffect(GimmickOperation.CONSUME, "sword_aura", 3)
    ]
    bisect.costs = [MPCost(14), StackCost("sword_aura", 3)]
    # bisect.cooldown = 5  # 쿨다운 시스템 제거됨
    bisect.sfx = "597"
    bisect.metadata = {"aura_cost": 3, "aura_scaling": True, "cleave": True}
    skills.append(bisect)

    # 9. 검광 폭풍 (NEW - 10번째 스킬)
    sword_storm = Skill("sword_saint_sword_storm", "검광 폭풍", "검기 4스택 소비, 광역 폭풍")
    sword_storm.effects = [
        DamageEffect(DamageType.BRV, 2.3, gimmick_bonus={"field": "sword_aura", "multiplier": 0.4}),
        DamageEffect(DamageType.HP, 1.7, gimmick_bonus={"field": "sword_aura", "multiplier": 0.3}),
        GimmickEffect(GimmickOperation.CONSUME, "sword_aura", 4)
    ]
    sword_storm.costs = [MPCost(20), StackCost("sword_aura", 4)]
    # sword_storm.cooldown = 6  # 쿨다운 시스템 제거됨
    sword_storm.is_aoe = True
    sword_storm.sfx = "604"
    sword_storm.metadata = {"aura_cost": 4, "aura_scaling": True, "aoe": True}
    skills.append(sword_storm)

    # 10. 궁극기: 무한검
    ultimate = Skill("sword_saint_ultimate", "무한검", "모든 검기로 무수한 검 다연타")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 1.0, gimmick_bonus={"field": "sword_aura", "multiplier": 0.2}),
        DamageEffect(DamageType.BRV, 1.0, gimmick_bonus={"field": "sword_aura", "multiplier": 0.2}),
        DamageEffect(DamageType.BRV, 1.0, gimmick_bonus={"field": "sword_aura", "multiplier": 0.2}),
        DamageEffect(DamageType.HP, 2.0),
        GimmickEffect(GimmickOperation.SET, "sword_aura", 0)
    ]
    ultimate.costs = [MPCost(30), StackCost("sword_aura", 1)]
    ultimate.is_ultimate = True
    # ultimate.cooldown = 8  # 쿨다운 시스템 제거됨
    ultimate.sfx = "611"
    ultimate.metadata = {"ultimate": True, "aura_dump": True, "infinite_blade": True}
    skills.append(ultimate)

    return skills

def register_sword_saint_skills(skill_manager):
    """검성 스킬 등록"""
    skills = create_sword_saint_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
