"""Archer Skills - 궁수 스킬 (지원사격 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost

def create_archer_skills():
    """궁수 10개 스킬 생성 (지원사격 시스템)"""

    # 1. 기본 BRV: 직접 사격 (콤보 단절)
    direct_shot = Skill("archer_direct_shot", "직접 사격", "직접 공격 (지원 콤보 초기화)")
    direct_shot.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="physical"),
        GimmickEffect(GimmickOperation.SET, "support_combo", 0)  # 콤보 초기화
    ]
    direct_shot.costs = []  # 기본 공격은 MP 소모 없음
    direct_shot.sfx = "193"  # FFVII shot sound
    direct_shot.metadata = {"breaks_combo": True}

    # 2. 기본 HP: 강력한 사격 (콤보 단절)
    power_shot = Skill("archer_power_shot", "강력한 사격", "HP 공격 (지원 콤보 초기화)")
    power_shot.effects = [
        DamageEffect(DamageType.HP, 1.3, stat_type="physical"),
        GimmickEffect(GimmickOperation.SET, "support_combo", 0)  # 콤보 초기화
    ]
    power_shot.costs = []  # 기본 공격은 MP 소모 없음
    power_shot.sfx = "204"  # FFVII power shot sound
    power_shot.metadata = {"breaks_combo": True}

    # 3. 일반 화살 마킹 (MP 0)
    mark_normal = Skill("archer_mark_normal", "일반 화살 지원", "아군 마킹: 일반 화살 (배율 1.5)")
    mark_normal.effects = [
        GimmickEffect(GimmickOperation.ADD, "mark_slot_normal", 1, max_value=3, apply_to_target=True),  # 대상에게 마킹 슬롯 추가
        GimmickEffect(GimmickOperation.SET, "mark_shots_normal", 3, apply_to_target=True),  # 대상에게 3회 지원 설정
    ]
    mark_normal.costs = []  # 일반 화살은 MP 소모 없음
    mark_normal.target_type = "ally"
    mark_normal.sfx = "219"  # FFVII mark sound
    # mark_normal.cooldown = 1  # 쿨다운 시스템 제거됨
    mark_normal.metadata = {"arrow_type": "normal", "multiplier": 1.5}

    # 4. 관통 화살 마킹
    mark_piercing = Skill("archer_mark_piercing", "관통 화살 지원", "아군 마킹: 관통 (배율 1.8, 방어 무시 30%)")
    mark_piercing.effects = [
        GimmickEffect(GimmickOperation.ADD, "mark_slot_piercing", 1, max_value=3, apply_to_target=True),
        GimmickEffect(GimmickOperation.SET, "mark_shots_piercing", 3, apply_to_target=True),
    ]
    mark_piercing.costs = [MPCost(6)]
    mark_piercing.target_type = "ally"
    mark_piercing.sfx = "267"  # FFVII pierce sound
    # mark_piercing.cooldown = 2  # 쿨다운 시스템 제거됨
    mark_piercing.metadata = {"arrow_type": "piercing", "multiplier": 1.8, "defense_ignore": 0.3}

    # 5. 화염 화살 마킹
    mark_fire = Skill("archer_mark_fire", "화염 화살 지원", "아군 마킹: 화염 (배율 1.6, 화상 2턴)")
    mark_fire.effects = [
        GimmickEffect(GimmickOperation.ADD, "mark_slot_fire", 1, max_value=3, apply_to_target=True),
        GimmickEffect(GimmickOperation.SET, "mark_shots_fire", 3, apply_to_target=True),
    ]
    mark_fire.costs = [MPCost(6)]
    mark_fire.target_type = "ally"
    mark_fire.sfx = "314"  # FFVII fire sound
    # mark_fire.cooldown = 2  # 쿨다운 시스템 제거됨
    mark_fire.metadata = {"arrow_type": "fire", "multiplier": 1.6, "burn_duration": 2}

    # 6. 빙결 화살 마킹
    mark_ice = Skill("archer_mark_ice", "빙결 화살 지원", "아군 마킹: 빙결 (배율 1.4, 속도 -30%)")
    mark_ice.effects = [
        GimmickEffect(GimmickOperation.ADD, "mark_slot_ice", 1, max_value=3, apply_to_target=True),
        GimmickEffect(GimmickOperation.SET, "mark_shots_ice", 3, apply_to_target=True),
    ]
    mark_ice.costs = [MPCost(6)]
    mark_ice.target_type = "ally"
    mark_ice.sfx = "644"  # FFVII ice sound
    # mark_ice.cooldown = 2  # 쿨다운 시스템 제거됨
    mark_ice.metadata = {"arrow_type": "ice", "multiplier": 1.4, "slow_percent": 0.3}

    # 7. 독 화살 마킹
    mark_poison = Skill("archer_mark_poison", "독 화살 지원", "아군 마킹: 독 (배율 1.3, 독 3턴)")
    mark_poison.effects = [
        GimmickEffect(GimmickOperation.ADD, "mark_slot_poison", 1, max_value=3, apply_to_target=True),
        GimmickEffect(GimmickOperation.SET, "mark_shots_poison", 3, apply_to_target=True),
    ]
    mark_poison.costs = [MPCost(4)]
    mark_poison.target_type = "ally"
    mark_poison.sfx = "645"  # FFVII poison sound
    # mark_poison.cooldown = 2  # 쿨다운 시스템 제거됨
    mark_poison.metadata = {"arrow_type": "poison", "multiplier": 1.3, "poison_duration": 3}

    # 8. 폭발 화살 마킹
    mark_explosive = Skill("archer_mark_explosive", "폭발 화살 지원", "아군 마킹: 폭발 (배율 2.0, 광역 50%)")
    mark_explosive.effects = [
        GimmickEffect(GimmickOperation.ADD, "mark_slot_explosive", 1, max_value=3, apply_to_target=True),
        GimmickEffect(GimmickOperation.SET, "mark_shots_explosive", 3, apply_to_target=True),
    ]
    mark_explosive.costs = [MPCost(9)]
    mark_explosive.target_type = "ally"
    mark_explosive.sfx = "678"  # FFVII explosion sound
    # mark_explosive.cooldown = 3  # 쿨다운 시스템 제거됨
    mark_explosive.metadata = {"arrow_type": "explosive", "multiplier": 2.0, "aoe_percent": 0.5}

    # 9. 신성 화살 마킹
    mark_holy = Skill("archer_mark_holy", "신성 화살 지원", "아군 마킹: 신성 (배율 1.7, 언데드 2배)")
    mark_holy.effects = [
        GimmickEffect(GimmickOperation.ADD, "mark_slot_holy", 1, max_value=3, apply_to_target=True),
        GimmickEffect(GimmickOperation.SET, "mark_shots_holy", 3, apply_to_target=True),
    ]
    mark_holy.costs = [MPCost(7)]
    mark_holy.target_type = "ally"
    mark_holy.sfx = "687"  # FFVII holy sound
    # mark_holy.cooldown = 2  # 쿨다운 시스템 제거됨
    mark_holy.metadata = {"arrow_type": "holy", "multiplier": 1.7, "undead_bonus": 2.0}

    # 10. 궁극기: 전원 마킹 (모든 아군에게 최강 화살)
    ultimate = Skill("archer_ultimate", "총력 지원", "모든 아군 마킹 + 콤보 7 시작")
    ultimate.effects = [
        # 모든 아군에게 폭발 화살 마킹 (최강 화살)
        GimmickEffect(GimmickOperation.SET, "mark_all_allies", 1),
        GimmickEffect(GimmickOperation.SET, "ultimate_arrow_type", "explosive"),
        GimmickEffect(GimmickOperation.SET, "mark_shots_ultimate", 5),  # 5회 지원
        # 콤보 즉시 7로 설정 (완벽한 지원 상태)
        GimmickEffect(GimmickOperation.SET, "support_combo", 7),
        # 버프
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=5),
        BuffEffect(BuffType.CRITICAL_UP, 0.4, duration=5),
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.target_type = "party"
    ultimate.is_aoe = True
    ultimate.sfx = "694"  # FFVII ultimate sound
    # ultimate.cooldown = 8  # 쿨다운 시스템 제거됨
    ultimate.metadata = {"ultimate": True, "mark_all": True, "perfect_support": True}

    return [direct_shot, power_shot, mark_normal, mark_piercing, mark_fire,
            mark_ice, mark_poison, mark_explosive, mark_holy, ultimate]

def register_archer_skills(skill_manager):
    """궁수 스킬 등록"""
    skills = create_archer_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
