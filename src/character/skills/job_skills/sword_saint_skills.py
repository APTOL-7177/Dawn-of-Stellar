"""Sword Saint Skills - 검성 스킬 (검기 스택 시스템)

검기 시스템:
- 검기 스택에 따라 공격 시 검기가 먼저 BRV 피해를 입힘
- 메인 스킬은 HP 공격으로 마무리
- 검기 스택이 많을수록 더 많은 BRV 피해 후 HP 공격
"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

# 검기 추가 공격 고정 계수
SWORD_AURA_MULTIPLIER = 1 / 3  # 검기 1개당 1/3 (약 0.33)

def create_sword_saint_skills():
    """검성 10개 스킬 생성 (검기 스택 시스템)
    
    검기 시스템:
    - 공격 시 현재 검기 스택 수만큼 BRV 공격이 먼저 발동
    - 그 후 메인 스킬(HP 공격)이 실행
    - 검기 스택이 많을수록 더 강력한 콤보
    """

    skills = []

    # 1. 기본 BRV: 검기 축적 (검기 획득용 - 검기 추가타 없음)
    kenkizan = Skill("sword_saint_kenkizan", "검기 축적", "적을 베어 검기 스택 획득")
    kenkizan.effects = [
        DamageEffect(DamageType.BRV, 1.8),
        GimmickEffect(GimmickOperation.ADD, "sword_aura", 1, max_value=5)
    ]
    kenkizan.costs = []  # 기본 공격은 MP 소모 없음
    kenkizan.sfx = ("combat", "attack_physical")
    kenkizan.metadata = {"aura_gain": 1}
    skills.append(kenkizan)

    # 2. 기본 HP: 일섬 (검기 추가타 + HP 공격)
    ilseom = Skill("sword_saint_ilseom", "일섬", "검기가 먼저 적을 베고, 일섬으로 마무리")
    ilseom.effects = [
        DamageEffect(DamageType.HP, 0.8),
    ]
    ilseom.costs = []  # 기본 공격은 MP 소모 없음
    ilseom.sfx = ("combat", "critical")
    ilseom.metadata = {
        "basic_attack": True,
        "sword_aura_bonus_hits": {"multiplier": SWORD_AURA_MULTIPLIER}
    }
    skills.append(ilseom)

    # 3. 검기 파동 (검기 획득 + 검기 추가타 + HP 공격)
    kenki_hadou = Skill("sword_saint_kenki_hadou", "검기 파동", "검기를 날려 적을 공격하고 검기 획득")
    kenki_hadou.effects = [
        GimmickEffect(GimmickOperation.ADD, "sword_aura", 1, max_value=5),
        DamageEffect(DamageType.HP, 1.1)
    ]
    kenki_hadou.costs = [MPCost(4)]
    kenki_hadou.sfx = ("skill", "cast_start")
    kenki_hadou.metadata = {
        "aura_gain": 1,
        "piercing": True,
        "sword_aura_bonus_hits": {"multiplier": SWORD_AURA_MULTIPLIER}
    }
    skills.append(kenki_hadou)

    # 4. 이도류 (검기 2스택 소비 + 검기 추가타 + 강력한 HP 공격)
    nitoryu = Skill("sword_saint_nitoryu", "이도류", "검기 2스택 소비, 쌍검으로 난무")
    nitoryu.effects = [
        DamageEffect(DamageType.HP, 1.8)
    ]
    nitoryu.costs = [MPCost(6), StackCost("sword_aura", 2)]
    nitoryu.sfx = ("combat", "attack_physical")
    nitoryu.metadata = {
        "aura_cost": 2,
        "dual_wield": True,
        "sword_aura_bonus_hits": {"multiplier": SWORD_AURA_MULTIPLIER}
    }
    skills.append(nitoryu)

    # 5. 검의 무덤 (모든 검기 소비 + 검기 추가타 + 폭발 HP 공격)
    kenki_bakuhatsu = Skill("sword_saint_kenki_bakuhatsu", "검의 무덤", "모든 검기를 폭발시켜 대폭발")
    kenki_bakuhatsu.effects = [
        DamageEffect(DamageType.HP, 1.6, gimmick_bonus={"field": "sword_aura", "multiplier": 0.28}),
        GimmickEffect(GimmickOperation.SET, "sword_aura", 0)
    ]
    kenki_bakuhatsu.costs = [MPCost(8), StackCost("sword_aura", 1)]
    kenki_bakuhatsu.sfx = ("skill", "ultima")
    kenki_bakuhatsu.metadata = {
        "aura_dump": True,
        "aura_scaling": True,
        "sword_aura_bonus_hits": {"multiplier": SWORD_AURA_MULTIPLIER}
    }
    skills.append(kenki_bakuhatsu)

    # 6. 초고속 베기 (검기 2스택 획득 + 검기 추가타 + HP 공격)
    rapid_slash = Skill("sword_saint_rapid_slash", "초고속 베기", "빠른 베기로 검기 대량 획득")
    rapid_slash.effects = [
        GimmickEffect(GimmickOperation.ADD, "sword_aura", 2, max_value=5),
        DamageEffect(DamageType.HP, 1.3)
    ]
    rapid_slash.costs = [MPCost(5)]
    rapid_slash.sfx = ("combat", "attack_physical")
    rapid_slash.metadata = {
        "aura_gain": 2,
        "quick": True,
        "sword_aura_bonus_hits": {"multiplier": SWORD_AURA_MULTIPLIER}
    }
    skills.append(rapid_slash)

    # 7. 검성의 의지 (검기 스택 최대 회복 - 버프 스킬)
    will = Skill("sword_saint_will", "검성의 의지", "정신 집중으로 검기 스택 최대 충전")
    will.effects = [
        GimmickEffect(GimmickOperation.SET, "sword_aura", 5),
        BuffEffect(BuffType.ATTACK_UP, 0.15, duration=3)
    ]
    will.costs = [MPCost(6)]
    will.target_type = "self"
    will.sfx = ("character", "status_buff")
    will.metadata = {"aura_refill": True}
    skills.append(will)

    # 8. 일도양단 (검기 3스택 소비 + 검기 추가타 + 강력한 HP 공격)
    bisect = Skill("sword_saint_bisect", "일도양단", "검기 3스택 소비, 한 칼에 양단")
    bisect.effects = [
        DamageEffect(DamageType.HP, 2.5)
    ]
    bisect.costs = [MPCost(10), StackCost("sword_aura", 3)]
    bisect.sfx = ("combat", "damage_high")
    bisect.metadata = {
        "aura_cost": 3,
        "cleave": True,
        "sword_aura_bonus_hits": {"multiplier": SWORD_AURA_MULTIPLIER}
    }
    skills.append(bisect)

    # 9. 검광 폭풍 (검기 4스택 소비 + 검기 추가타 + 광역 HP 공격)
    sword_storm = Skill("sword_saint_sword_storm", "검광 폭풍", "검기 4스택 소비, 전체 적을 검으로 난무")
    sword_storm.effects = [
        DamageEffect(DamageType.HP, 1.3)
    ]
    sword_storm.costs = [MPCost(14), StackCost("sword_aura", 4)]
    sword_storm.target_type = "all_enemies"
    sword_storm.is_aoe = True
    sword_storm.sfx = ("skill", "cast_complete")
    sword_storm.metadata = {
        "aura_cost": 4,
        "aoe": True,
        "sword_aura_bonus_hits": {"multiplier": SWORD_AURA_MULTIPLIER}
    }
    skills.append(sword_storm)

    # 10. 궁극기: 무한검 (검기 스택에 따른 다연타 - 검기 1개당 BRV 공격 후 HP 마무리)
    ultimate = Skill("sword_saint_ultimate", "무한검", "모든 검기로 무수한 검을 쏟아붓는다")
    ultimate.effects = [
        DamageEffect(DamageType.HP, 3.0)
    ]
    ultimate.costs = [MPCost(25), StackCost("sword_aura", 1)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 12  # 궁극기 쿨타임 12턴
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {
        "ultimate": True,
        "aura_dump": True,
        "infinite_blade": True,
        # 무한검: 검기 스택당 0.7배 BRV 공격 (다른 스킬보다 높은 계수)
        "sword_aura_bonus_hits": {"multiplier": 0.4}
    }
    skills.append(ultimate)

    return skills

def register_sword_saint_skills(skill_manager):
    """검성 스킬 등록"""
    skills = create_sword_saint_skills()
    for skill in skills:
        skill_manager.register_skill(skill)

    # 팀워크 스킬: 검성: 만상절단
    teamwork = TeamworkSkill(
        "sword_saint_teamwork",
        "검성: 만상절단",
        "전체 대상 BRV+HP (3.5x) + 검기 게이지 완전 회복 + 아군 전체 공격력 1.2배 (2턴)",
        gauge_cost=250)
    teamwork.effects = [
        # 전체 대상 BRV+HP 공격 (3.5x)
        DamageEffect(
            DamageType.BRV_HP,
            multiplier=3.5
        ),
        # 검기 게이지 완전 회복
        GimmickEffect(
            GimmickOperation.SET,
            "sword_aura",
            5,  # 최대치로 설정
            min_value=0
        ),
        # 아군 전체 공격력/마법력 1.2배 (2턴)
        BuffEffect(BuffType.ATTACK_UP, 0.2, duration=2, is_party_wide=True),
        BuffEffect(BuffType.MAGIC_UP, 0.2, duration=2, is_party_wide=True)
    ]
    teamwork.target_type = "all_enemies"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {"teamwork": True, "chain": True}
    skills.append(teamwork)
    skill_manager.register_skill(teamwork)

    return [s.skill_id for s in skills]
