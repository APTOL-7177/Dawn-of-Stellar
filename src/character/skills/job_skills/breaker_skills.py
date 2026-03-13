"""Breaker Skills - 브레이커 (리메이크)

"부서진 것들이 나의 무기가 된다"

SCATTER 시스템과 연격 기믹을 활용한 연속 공격 딜러.
"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.status_effect import StatusEffect, StatusType
from src.character.skills.effects.cleanse_effect import CleanseEffect
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.gimmick_cost import GimmickCost
from src.core.logger import get_logger

logger = get_logger("breaker_skills")


def create_breaker_skills():
    """브레이커 스킬 생성"""
    
    skills = []
    
    # ============================================================
    # 1. 트리플 스매시 (기본 3연타)
    # ============================================================
    triple_smash = Skill(
        "breaker_triple_smash",
        "트리플 스매시",
        "건틀릿으로 3회 연속 타격. BREAK 유발에 특화."
    )
    triple_smash.effects = [
        DamageEffect(DamageType.BRV, 0.4, stat_type="physical"),
        DamageEffect(DamageType.BRV, 0.8, stat_type="physical"),
        DamageEffect(DamageType.BRV, 1.2, stat_type="physical")
    ]
    triple_smash.costs = []
    triple_smash.sfx = ("combat", "attack_physical_multi")
    triple_smash.metadata = {
        "basic_attack": True,
        "brv_break_focused": True
    }
    skills.append(triple_smash)
    
    # ============================================================
    # 2. 증기 분출 (HP 공격)
    # ============================================================
    steam_erupt = Skill(
        "breaker_steam_erupt",
        "증기 분출",
        "[화염 속성] 뜨거운 증기와 함께 강력한 일격. 연격 기믹 게이지 획득."
    )
    steam_erupt.effects = [
        DamageEffect(DamageType.HP, 1.0, stat_type="physical", element="fire",
                    gimmick_bonus={"field": "combo_gauge", "multiplier": 0.0, "scaling": "none"})
        # 기믹 보너스는 메커니즘적으로 처리됨
    ]
    steam_erupt.costs = []
    steam_erupt.sfx = ("combat", "damage_heavy")
    steam_erupt.metadata = {
        "basic_attack": True
    }
    skills.append(steam_erupt)
    
    # ============================================================
    # 3. 오버드라이브 시동 (자가 버프)
    # ============================================================
    overdrive_start = Skill(
        "breaker_overdrive_start",
        "오버드라이브 시동",
        "엔진 가동! 공격력 +40% 및 기믹 게이지 충전."
    )
    overdrive_start.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.40, duration=4, target="self"),
        GimmickEffect(GimmickOperation.ADD, "combo_gauge", 150) # 수치는 임의, 밸런싱 필요
    ]
    overdrive_start.costs = [MPCost(5)]
    overdrive_start.target_type = "self"
    overdrive_start.sfx = ("character", "charge_power")
    skills.append(overdrive_start)
    
    # ============================================================
    # 4. 래피드 피스톤 (다단 히트)
    # ============================================================
    rapid_piston = Skill(
        "breaker_rapid_piston",
        "래피드 피스톤",
        "고속 피스톤 연타. 4회 BRV 공격."
    )
    rapid_piston.effects = [
        DamageEffect(DamageType.BRV, 0.5, stat_type="physical"),
        DamageEffect(DamageType.BRV, 0.5, stat_type="physical"),
        DamageEffect(DamageType.BRV, 0.5, stat_type="physical"),
        DamageEffect(DamageType.BRV, 0.8, stat_type="physical")
    ]
    rapid_piston.costs = [MPCost(8)]
    rapid_piston.sfx = ("combat", "attack_rapid")
    rapid_piston.metadata = {}
    skills.append(rapid_piston)
    
    # ============================================================
    # 5. 케미컬 리크 (디버프)
    # ============================================================
    chemical_leak = Skill(
        "breaker_chemical_leak",
        "케미컬 리크",
        "[대지 속성] 부식성 화학물질 살포. 방어력 -30% (3턴)."
    )
    chemical_leak.effects = [
        DamageEffect(DamageType.BRV, 1.2, stat_type="physical", element="earth"),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.30, duration=3)
    ]
    chemical_leak.costs = [MPCost(10)]
    chemical_leak.sfx = ("skill", "poison_cloud")
    skills.append(chemical_leak)
    
    # ============================================================
    # 6. 엔진 로어 (도발/방어)
    # ============================================================
    engine_roar = Skill(
        "breaker_engine_roar",
        "엔진 로어",
        "거대한 엔진 소음으로 적 도발 + 받는 피해 감소."
    )
    engine_roar.effects = [
        StatusEffect(StatusType.PROVOKE, duration=3),
        BuffEffect(BuffType.DEFENSE_UP, 0.50, duration=3, target="self")
    ]
    engine_roar.costs = [MPCost(8)]
    engine_roar.target_type = "self" # 도발은 self status로 구현
    engine_roar.sfx = ("skill", "roar")
    skills.append(engine_roar)
    
    # ============================================================
    # 7. 스캐터 밤 (광역 BRV)
    # ============================================================
    scatter_bomb = Skill(
        "breaker_scatter_bomb",
        "스캐터 밤",
        "[화염 속성] 광역 폭탄 투척. 전체 적 BRV 피해."
    )
    scatter_bomb.effects = [
        DamageEffect(DamageType.BRV, 1.8, stat_type="physical", element="fire")
    ]
    scatter_bomb.costs = [MPCost(12)]
    scatter_bomb.target_type = "all_enemies"
    scatter_bomb.is_aoe = True
    scatter_bomb.sfx = ("combat", "explosion_small")
    skills.append(scatter_bomb)
    
    # ============================================================
    # 8. 풀 스로틀 (게이지 소모 극딜)
    # ============================================================
    full_throttle = Skill(
        "breaker_full_throttle",
        "풀 스로틀",
        "[화염 속성] 모든 출력 개방! 엔진 한계를 시험하는 막대한 HP 피해."
    )
    full_throttle.effects = [
        DamageEffect(DamageType.HP, 3.0, stat_type="physical", element="fire")
    ]
    full_throttle.costs = [MPCost(25)]
    full_throttle.sfx = ("skill", "limit_break")
    full_throttle.metadata = {}
    skills.append(full_throttle)
    
    # ============================================================
    # 9. 리미트 브레이크 (강력한 한방)
    # ============================================================
    limit_break = Skill(
        "breaker_limit_break",
        "리미트 브레이크",
        "[번개 속성] 한계를 넘는 일격. 높은 확율로 BREAK 유발."
    )
    limit_break.effects = [
        DamageEffect(DamageType.BRV_HP, 3.5, stat_type="physical", element="lightning")
    ]
    limit_break.costs = [MPCost(35)]
    limit_break.cooldown = 5
    limit_break.sfx = ("combat", "crit_hit")
    skills.append(limit_break)

    # ============================================================
    # 10. 궁극기: 파이널 임팩트 (Ultimate)
    # ============================================================
    ultimate = Skill(
        "breaker_ultimate",
        "파이널 임팩트",
        "[화염 속성] 건틀릿의 모든 기능을 과부하시켜 전장을 초토화. 적 전체 SCATTER 유발 시도."
    )
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 3.0, stat_type="physical", element="fire"),
        DamageEffect(DamageType.HP, 4.0, stat_type="physical", element="fire"),
        # SCATTER 강제 유발 로직은 별도 처리 안해도 BRV 데미지가 높아서 자연 발생 유도
    ]
    ultimate.costs = [MPCost(70)]
    ultimate.is_ultimate = True
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.cooldown = 99
    ultimate.sfx = ("skill", "ultimate_explosion")
    skills.append(ultimate)
    
    # ============================================================
    # 11. 안전 밸브 (회복/정화) [NEW]
    # ============================================================
    safety_valve = Skill(
        "breaker_safety_valve",
        "안전 밸브",
        "압력을 낮춰 상태이상 제거 및 HP 회복."
    )
    safety_valve.effects = [
        CleanseEffect(count=2),
        HealEffect(HealType.HP, stat_scaling="max_hp", multiplier=0.4, target_self=True)
    ]
    safety_valve.costs = [MPCost(8)]
    safety_valve.target_type = "self"
    safety_valve.sfx = ("skill", "heal_01")
    skills.append(safety_valve)

    # ============================================================
    # 12. 압력 밥솥 (지연 폭발) [NEW]
    # ============================================================
    pressure_cooker = Skill(
        "breaker_pressure_cooker",
        "압력 밥솥",
        "적에게 압력을 주입. 2턴 후 폭발하여 큰 BRV 피해."
    )
    pressure_cooker.effects = [
        StatusEffect(StatusType.DOOM, duration=2, value=3.0) # DOOM is equivalent to Timed Bomb logic here
    ]
    pressure_cooker.costs = [MPCost(12)]
    pressure_cooker.sfx = ("combat", "bomb_fuse")
    skills.append(pressure_cooker)

    # ============================================================
    # 13. 증기 연막 (회피 버프) [NEW]
    # ============================================================
    steam_screen = Skill(
        "breaker_steam_screen",
        "증기 연막",
        "자욱한 증기로 몸을 숨김. 회피율 대폭 상승."
    )
    steam_screen.effects = [
        BuffEffect(BuffType.EVASION_UP, 0.50, duration=2, target="self")
    ]
    steam_screen.costs = [MPCost(8)]
    steam_screen.target_type = "self"
    steam_screen.sfx = ("skill", "smoke_puff")
    skills.append(steam_screen)

    # ============================================================
    # 14. 열기 재순환 (MP 회복/쿨감) [NEW]
    # ============================================================
    recycle = Skill(
        "breaker_recycle",
        "열기 재순환",
        "낭비되는 열기를 에너지로 전환. MP 회복."
    )
    recycle.effects = [
        HealEffect(HealType.MP, fixed_amount=40, target_self=True),
        GimmickEffect(GimmickOperation.ADD, "combo_gauge", 50)
    ]
    recycle.costs = []
    recycle.cooldown = 4
    recycle.target_type = "self"
    recycle.sfx = ("skill", "recharge")
    skills.append(recycle)

    # ============================================================
    # 15. 연쇄 반응 (SCATTER 추뎀) [NEW]
    # ============================================================
    chain_reaction = Skill(
        "breaker_chain_reaction",
        "연쇄 반응",
        "[화염 속성] SCATTER 상태인 적에게 2배 피해."
    )
    chain_reaction.effects = [
        DamageEffect(DamageType.BRV_HP, 1.2, stat_type="physical", element="fire")
    ]
    chain_reaction.costs = [MPCost(15)]
    chain_reaction.metadata = {
        "scatter_bonus": True,
        "bonus_multiplier": 2.0
    }
    chain_reaction.sfx = ("combat", "combo_hit")
    skills.append(chain_reaction)
    
    # ============================================================
    # 팀워크: 엔진 쉐어
    # ============================================================
    teamwork = TeamworkSkill(
        "breaker_teamwork",
        "엔진 쉐어",
        "동료에게 엔진 출력 전달. 아군 전체 공격력/속도 +30%.",
        gauge_cost=150
    )
    teamwork.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.30, duration=3, target="all_allies"),
        BuffEffect(BuffType.SPEED_UP, 0.30, duration=3, target="all_allies")
    ]
    teamwork.target_type = "all_allies"
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork_buff")
    skills.append(teamwork)
    
    return skills


def register_breaker_skills(skill_manager):
    """브레이커 스킬 등록"""
    skills = create_breaker_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    
    logger.info(f"브레이커(리메이크) 스킬 {len(skills)}개 등록 완료")
    return [s.skill_id for s in skills]
