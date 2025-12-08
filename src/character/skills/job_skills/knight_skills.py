"""Knight Skills - 기사 (의무 시스템)

파티를 보호하며 의무 스택 축적!
의무로 강력한 수호 기술 발동

"맹세는 지키되, 대가를 치른다"
"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost
from src.core.logger import get_logger

logger = get_logger("knight_skills")


def create_knight_skills():
    """기사 스킬 생성 (의무 시스템)"""
    
    skills = []
    
    # ============================================================
    # 1. 랜스 돌격 (기본 BRV + 의무)
    # ============================================================
    lance = Skill(
        "knight_lance",
        "랜스 돌격",
        "기사의 돌격. 의무 +1."
    )
    lance.effects = [
        DamageEffect(DamageType.BRV, 1.6, stat_type="physical"),
        GimmickEffect(GimmickOperation.ADD, "duty_stacks", 1, max_value=10)
    ]
    lance.costs = []
    lance.sfx = ("combat", "attack_physical")
    lance.metadata = {
        "basic_attack": True,
        "duty_gain": 1
    }
    skills.append(lance)
    
    # ============================================================
    # 2. 의무의 일격 (기본 HP + 의무 비례)
    # ============================================================
    duty_strike = Skill(
        "knight_duty_strike",
        "의무의 일격",
        "의무 비례 HP 피해. 의무 -1."
    )
    duty_strike.effects = [
        DamageEffect(DamageType.HP, 1.0, stat_type="physical",
                    gimmick_bonus={"field": "duty_stacks", "multiplier": 0.15}),
        GimmickEffect(GimmickOperation.CONSUME, "duty_stacks", 1)
    ]
    duty_strike.costs = []
    duty_strike.sfx = ("combat", "damage_high")
    duty_strike.metadata = {
        "basic_attack": True,
        "duty_cost": 1,
        "scaling": "의무당 +15%"
    }
    skills.append(duty_strike)
    
    # ============================================================
    # 3. 기사도 맹세 (파티 버프) - 의무 필수 소비
    # ============================================================
    oath = Skill(
        "knight_oath",
        "기사도 맹세",
        "맹세로 파티 강화. 의무 2 소비 → 공/방/마공/마방 +20% (4턴)."
    )
    oath.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.20, duration=4, is_party_wide=True),
        BuffEffect(BuffType.MAGIC_UP, 0.20, duration=4, is_party_wide=True),
        BuffEffect(BuffType.DEFENSE_UP, 0.20, duration=4, is_party_wide=True),
        BuffEffect(BuffType.MAGIC_DEFENSE_UP, 0.20, duration=4, is_party_wide=True),
        GimmickEffect(GimmickOperation.CONSUME, "duty_stacks", 2)
    ]
    oath.costs = [MPCost(13), StackCost("duty_stacks", 2)]
    oath.target_type = "party"
    oath.is_aoe = True
    oath.sfx = ("character", "status_buff")
    oath.metadata = {
        "party_buff": True,
        "duty_cost": 2
    }
    skills.append(oath)
    
    # ============================================================
    # 4. 기사의 수호 (아군 보호)
    # ============================================================
    chivalry = Skill(
        "knight_chivalry",
        "기사의 수호",
        "아군 1명 보호. 대신 피해 받음 + 의무 +3."
    )
    chivalry.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.40, duration=3),
        GimmickEffect(GimmickOperation.ADD, "duty_stacks", 3, max_value=10)
    ]
    chivalry.costs = [MPCost(12)]
    chivalry.target_type = "ally"
    chivalry.sfx = ("character", "status_buff")
    chivalry.metadata = {
        "protect": True,
        "duty_gain": 3,
        "cover_ally": True
    }
    skills.append(chivalry)
    
    # ============================================================
    # 5. 철벽 방어 (자가 방어)
    # ============================================================
    iron_will = Skill(
        "knight_iron_will",
        "철벽 방어",
        "철벽 수비. 방어 +50% (3턴) + 의무 +2."
    )
    iron_will.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.50, duration=3),
        BuffEffect(BuffType.MAGIC_DEFENSE_UP, 0.40, duration=3),
        GimmickEffect(GimmickOperation.ADD, "duty_stacks", 2, max_value=10)
    ]
    iron_will.costs = [MPCost(10)]
    iron_will.target_type = "self"
    iron_will.sfx = ("character", "status_buff")
    iron_will.metadata = {
        "defense_mode": True,
        "duty_gain": 2
    }
    skills.append(iron_will)
    
    # ============================================================
    # 6. 방패 강타 (스턴 + 의무)
    # ============================================================
    bash = Skill(
        "knight_bash",
        "방패 강타",
        "방패로 강타. 속도 감소 + 의무 +2."
    )
    bash.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, stat_type="physical"),
        BuffEffect(BuffType.SPEED_DOWN, 0.30, duration=2),
        GimmickEffect(GimmickOperation.ADD, "duty_stacks", 2, max_value=10)
    ]
    bash.costs = [MPCost(12)]
    bash.sfx = ("combat", "attack_physical")
    bash.metadata = {
        "cc": True,
        "duty_gain": 2
    }
    skills.append(bash)
    
    # ============================================================
    # 7. 최후의 저항 (의무 소비 무적)
    # ============================================================
    last_stand = Skill(
        "knight_last_stand",
        "최후의 저항",
        "의무 5 소비. 무적 2턴 + HP 회복."
    )
    last_stand.effects = [
        BuffEffect(BuffType.INVINCIBLE, 1.0, duration=2),
        HealEffect(HealType.HP, percentage=0.25),
        GimmickEffect(GimmickOperation.CONSUME, "duty_stacks", 5)
    ]
    last_stand.costs = [MPCost(16), StackCost("duty_stacks", 5)]
    last_stand.target_type = "self"
    last_stand.sfx = ("character", "status_buff")
    last_stand.metadata = {
        "duty_cost": 5,
        "invincible": 2
    }
    skills.append(last_stand)
    
    # ============================================================
    # 8. 헌신 (파티 힐) - 의무 필수 소비
    # ============================================================
    devotion = Skill(
        "knight_devotion",
        "헌신",
        "의무 3 소비. 파티에게 공격력의 0.9배 HP 회복."
    )
    devotion.effects = [
        HealEffect(HealType.HP, stat_scaling='physical_attack', multiplier=0.9, is_party_wide=True),
        GimmickEffect(GimmickOperation.CONSUME, "duty_stacks", 3)
    ]
    devotion.costs = [MPCost(14), StackCost("duty_stacks", 3)]
    devotion.target_type = "party"
    devotion.is_aoe = True
    devotion.sfx = ("character", "hp_heal")
    devotion.metadata = {
        "party_heal": "공격력 x0.5",
        "duty_cost": 3
    }
    skills.append(devotion)
    
    # ============================================================
    # 9. 결전의 맹세 (의무 소비)
    # ============================================================
    pledge = Skill(
        "knight_pledge",
        "결전의 맹세",
        "결전 각오. 의무 5 소비 → 자신 공/마공/방/마방 +50% (5턴) + 파티 공/마공/방/마방 +15%."
    )
    pledge.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.50, duration=5),
        BuffEffect(BuffType.MAGIC_UP, 0.50, duration=5),
        BuffEffect(BuffType.DEFENSE_UP, 0.50, duration=5),
        BuffEffect(BuffType.MAGIC_DEFENSE_UP, 0.50, duration=5),
        BuffEffect(BuffType.ATTACK_UP, 0.15, duration=5, is_party_wide=True),
        BuffEffect(BuffType.MAGIC_UP, 0.15, duration=5, is_party_wide=True),
        BuffEffect(BuffType.DEFENSE_UP, 0.15, duration=5, is_party_wide=True),
        BuffEffect(BuffType.MAGIC_DEFENSE_UP, 0.15, duration=5, is_party_wide=True),
        GimmickEffect(GimmickOperation.CONSUME, "duty_stacks", 5)
    ]
    pledge.costs = [MPCost(18), StackCost("duty_stacks", 5)]
    pledge.target_type = "party"
    pledge.is_aoe = True
    pledge.sfx = ("character", "status_buff")
    pledge.metadata = {
        "duty_cost": 5,
        "buff": True,
        "party_buff": True
    }
    skills.append(pledge)
    
    # ============================================================
    # 10. 궁극기: 성기사의 심판
    # ============================================================
    ultimate = Skill(
        "knight_ultimate",
        "성기사의 심판",
        "성스러운 심판! 전체 피해 + 파티 보호막 + 의무 전소비."
    )
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.5, stat_type="physical",
                    gimmick_bonus={"field": "duty_stacks", "multiplier": 0.2}),
        DamageEffect(DamageType.HP, 3.2, stat_type="physical"),
        BuffEffect(BuffType.DEFENSE_UP, 0.5, duration=5, is_party_wide=True),
        BuffEffect(BuffType.INVINCIBLE, 1.0, duration=1, is_party_wide=True),
        GimmickEffect(GimmickOperation.SET, "duty_stacks", 0)
    ]
    ultimate.costs = [MPCost(25)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {
        "ultimate": True,
        "party_invincible": 1,
        "duty_consume_all": True
    }
    skills.append(ultimate)
    
    # ============================================================
    # 11. 의무 방벽 (Duty Bulwark) - 방어형 스킬
    # ============================================================
    duty_bulwark = Skill(
        "knight_duty_bulwark",
        "의무 방벽",
        "의무 3 소비 → 방어력/마법방어력 +45%, 의무 스택당 피해 경감 5%"
    )
    duty_bulwark.effects = [
        GimmickEffect(GimmickOperation.CONSUME, "duty_stacks", 3),
        BuffEffect(BuffType.DEFENSE_UP, 0.45, duration=3),
        BuffEffect(BuffType.MAGIC_DEFENSE_UP, 0.45, duration=3)
    ]
    duty_bulwark.costs = [MPCost(14), StackCost("duty_stacks", 3)]
    duty_bulwark.target_type = "self"
    duty_bulwark.sfx = ("skill", "protect")
    duty_bulwark.metadata = {
        "tank_skill": True,
        "duty_cost": 3,
        "duty_damage_reduction_per_stack": 0.05,
        "max_duty_reduction_stacks": 7,
        "skill_category": "defense"
    }
    skills.append(duty_bulwark)

    # ============================================================
    # 12. 실드 라인 (Shield Line) - 방어형 스킬
    # ============================================================
    shield_line = Skill(
        "knight_shield_line",
        "실드 라인",
        "아군 1명에게 방어력/마법방어력 +50%, 대상 피해 40%를 자신이 대신 받음"
    )
    shield_line.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.50, duration=3),
        BuffEffect(BuffType.MAGIC_DEFENSE_UP, 0.50, duration=3),
        GimmickEffect(GimmickOperation.ADD, "duty_stacks", 1, max_value=10)
    ]
    shield_line.costs = [MPCost(15)]
    shield_line.target_type = "ally"
    shield_line.sfx = ("skill", "shell")
    shield_line.metadata = {
        "tank_skill": True,
        "party_buff": True,
        "cover_skill": True,
        "damage_share_percent": 0.40,
        "duty_gain": 1,
        "skill_category": "defense"
    }
    skills.append(shield_line)

    # ============================================================
    # 13. 정의의 심판 (Knight's Judgment) - 캐스트 타임 카운터
    # ============================================================
    counter_ready = Skill(
        "knight_counter_ready",
        "정의의 심판",
        "의무 2 소비. 심판의 일격을 준비. 캐스트 중 피격 시 반격 (2.0배), 캐스트 완료 시 약한 공격 (1.0배)."
    )
    counter_ready.effects = [
        DamageEffect(DamageType.BRV_HP, 1.0, stat_type="physical"),  # 캐스트 완료 시 약한 공격
        GimmickEffect(GimmickOperation.CONSUME, "duty_stacks", 2),
        GimmickEffect(GimmickOperation.ADD, "duty_stacks", 1, max_value=10)  # 캐스트 완료 시 의무 +1
    ]
    counter_ready.costs = [MPCost(8), StackCost("duty_stacks", 2)]
    counter_ready.requirements = {"min_duty": 2}
    counter_ready.target_type = "single_enemy"
    counter_ready.cast_time = 0.6  # ATB 60% 캐스트 타임 (중간 정도)
    counter_ready.sfx = ("combat", "attack_physical")
    counter_ready.metadata = {
        "parry": True,  # 패링 기술
        "duty_cost": 2,
        "parry_damage_multiplier": 2.0,  # 캐스트 중 피격 시 반격 2배
        "parry_duty_gain": 2,  # 캐스트 중 피격 시 의무 +2
        "cast_time": 0.6,
        "interruptible": True,  # 중단 가능
        "counter_on_interrupt": True,  # 캐스트 중 피격 시 반격
        "no_damage_on_parry": True  # 패링 성공 시 피해 무효
    }
    skills.append(counter_ready)

    # ============================================================
    # 팀워크: 기사단의 맹세
    # ============================================================
    teamwork = TeamworkSkill(
        "knight_teamwork",
        "기사단의 맹세",
        "기사단의 가호! 파티 방어 +30% + 의무 +5.",
        gauge_cost=150
    )
    teamwork.effects = [
        BuffEffect(BuffType.DEFENSE_UP, 0.30, duration=4, is_party_wide=True),
        BuffEffect(BuffType.MAGIC_DEFENSE_UP, 0.25, duration=4, is_party_wide=True),
        GimmickEffect(GimmickOperation.ADD, "duty_stacks", 5, max_value=10)
    ]
    teamwork.target_type = "party"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "chain": True,
        "party_defense": True
    }
    skills.append(teamwork)
    
    return skills


def register_knight_skills(skill_manager):
    """기사 스킬 등록"""
    skills = create_knight_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    
    logger.info(f"기사 스킬 {len(skills)}개 등록 완료")
    return [s.skill_id for s in skills]
