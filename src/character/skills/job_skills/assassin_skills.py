"""Assassin Skills - 암살자 스킬 (은신-노출 딜레마)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost

def create_assassin_skills():
    """암살자 10개 스킬 생성 (은신-노출 딜레마)"""

    # 1. 기본 BRV: 그림자 베기 (은신 중이면 크리티컬, 은신 해제)
    shadow_slash = Skill("assassin_shadow_slash", "그림자 베기", "은신 중이면 크리티컬 (은신 해제)")
    shadow_slash.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="physical",
                    conditional_bonus={"condition": "stealth_active", "multiplier": 1.8}),
        # 공격 시 은신 해제
        GimmickEffect(GimmickOperation.SET, "stealth_active", 0)
    ]
    shadow_slash.costs = []  # 기본 공격은 MP 소모 없음
    shadow_slash.sfx = "025"  # FFVII slash sound
    shadow_slash.metadata = {"breaks_stealth": True}

    # 2. 기본 HP: 암살 (은신 중 극대 피해, 은신 해제)
    assassinate = Skill("assassin_assassinate", "암살", "은신 중 극대 피해 (은신 해제)")
    assassinate.effects = [
        DamageEffect(DamageType.HP, 1.3, stat_type="physical",
                    conditional_bonus={"condition": "stealth_active", "multiplier": 2.5}),  # 은신 중 +250%
        GimmickEffect(GimmickOperation.SET, "stealth_active", 0)  # 은신 해제
    ]
    assassinate.costs = []  # 기본 공격은 MP 소모 없음
    assassinate.sfx = "013"  # FFVII assassinate sound
    assassinate.metadata = {"breaks_stealth": True, "stealth_bonus_high": True}

    # 3. 은신 (다시 은신 상태로 전환)
    vanish = Skill("assassin_vanish", "은신", "은신 상태로 전환 (회피 +80%, 크리티컬 확정)")
    vanish.effects = [
        GimmickEffect(GimmickOperation.SET, "stealth_active", 1),  # 은신 활성화
        GimmickEffect(GimmickOperation.SET, "exposed_turns", 0),  # 노출 턴 리셋
        BuffEffect(BuffType.EVASION_UP, 0.8, duration=99)  # 은신 중 지속
    ]
    vanish.costs = [MPCost(8)]
    vanish.target_type = "self"
    vanish.sfx = "010"  # FFVII vanish sound
    # vanish.cooldown = 3  # 쿨다운 시스템 제거됨
    vanish.metadata = {"enter_stealth": True}

    # 4. 배후 일격 (은신 중 방어 무시)
    backstab = Skill("assassin_backstab", "배후 일격", "은신 중 방어력 무시 공격 (은신 해제)")
    backstab.effects = [
        DamageEffect(DamageType.BRV_HP, 2.5, stat_type="physical",
                    conditional_bonus={"condition": "stealth_active", "multiplier": 2.0, "defense_ignore": True}),
        GimmickEffect(GimmickOperation.SET, "stealth_active", 0)  # 은신 해제
    ]
    backstab.costs = [MPCost(12)]
    backstab.sfx = "016"  # FFVII backstab sound
    # backstab.cooldown = 2  # 쿨다운 시스템 제거됨
    backstab.metadata = {"breaks_stealth": True, "defense_ignore_stealth": True}

    # 5. 목 베기 (노출 상태에서 사용 가능, 즉시 은신 진입)
    throat_slit = Skill("assassin_throat_slit", "목 베기", "강력한 공격 후 즉시 은신 (노출→은신)")
    throat_slit.effects = [
        DamageEffect(DamageType.HP, 2.8, stat_type="physical"),
        GimmickEffect(GimmickOperation.SET, "stealth_active", 1),  # 즉시 은신
        GimmickEffect(GimmickOperation.SET, "exposed_turns", 0)
    ]
    throat_slit.costs = [MPCost(15)]
    throat_slit.sfx = "069"  # FFVII slit sound
    # throat_slit.cooldown = 4  # 쿨다운 시스템 제거됨
    throat_slit.metadata = {"enter_stealth_after_attack": True}

    # 6. 그림자 질주 (은신 유지하면서 이동)
    shadow_step = Skill("assassin_shadow_step", "그림자 질주", "은신 유지, 속도 +60% (3턴)")
    shadow_step.effects = [
        BuffEffect(BuffType.SPEED_UP, 0.6, duration=3),
        BuffEffect(BuffType.EVASION_UP, 0.5, duration=3),
        # 은신 상태 유지 (변경하지 않음)
    ]
    shadow_step.costs = [MPCost(10)]
    shadow_step.target_type = "self"
    shadow_step.sfx = "077"  # FFVII step sound
    # shadow_step.cooldown = 5  # 쿨다운 시스템 제거됨
    shadow_step.metadata = {"maintain_stealth": True}

    # 7. 죽음의 표식 (은신 해제하지 않는 디버프)
    death_mark = Skill("assassin_death_mark", "죽음의 표식", "적에게 표식 (은신 유지)")
    death_mark.effects = [
        BuffEffect(BuffType.DEFENSE_DOWN, 0.4, duration=4),
        BuffEffect(BuffType.EVASION_DOWN, 0.3, duration=4),
        # 은신 유지 (공격 아님)
    ]
    death_mark.costs = [MPCost(12)]
    death_mark.target_type = "single"
    death_mark.sfx = "127"  # FFVII mark sound
    # death_mark.cooldown = 4  # 쿨다운 시스템 제거됨
    death_mark.metadata = {"non_attack_skill": True, "maintain_stealth": True}

    # 8. 그림자 분신 (은신 중 회피 극대화)
    shadow_clone = Skill("assassin_shadow_clone", "그림자 분신", "은신 강화 (회피 +100%, 3턴)")
    shadow_clone.effects = [
        BuffEffect(BuffType.EVASION_UP, 1.0, duration=3),  # 회피 +100%
        BuffEffect(BuffType.CRITICAL_UP, 0.5, duration=3),
        GimmickEffect(GimmickOperation.SET, "stealth_active", 1)  # 은신 강제 활성화
    ]
    shadow_clone.costs = [MPCost(18)]
    shadow_clone.target_type = "self"
    shadow_clone.sfx = "143"  # FFVII clone sound
    # shadow_clone.cooldown = 6  # 쿨다운 시스템 제거됨
    shadow_clone.metadata = {"enhance_stealth": True}

    # 9. 침묵의 처형 (은신 중 최대 피해)
    silent_execution = Skill("assassin_silent_execution", "침묵의 처형", "은신 중 극한의 피해 (은신 해제)")
    silent_execution.effects = [
        DamageEffect(DamageType.BRV_HP, 3.5, stat_type="physical",
                    conditional_bonus={"condition": "stealth_active", "multiplier": 3.0}),  # 은신 중 +300%
        GimmickEffect(GimmickOperation.SET, "stealth_active", 0)  # 은신 해제
    ]
    silent_execution.costs = [MPCost(22)]
    silent_execution.sfx = "159"  # FFVII execution sound
    # silent_execution.cooldown = 5  # 쿨다운 시스템 제거됨
    silent_execution.metadata = {"breaks_stealth": True, "ultimate_stealth_attack": True}

    # 10. 궁극기: 그림자의 화신 (완벽한 은신 + 극대 공격)
    ultimate = Skill("assassin_ultimate", "그림자의 화신", "완벽한 은신 + 연속 암살")
    ultimate.effects = [
        # 완벽한 은신 진입
        GimmickEffect(GimmickOperation.SET, "stealth_active", 1),
        # 연속 공격 (3회)
        DamageEffect(DamageType.BRV, 3.0, stat_type="physical"),
        DamageEffect(DamageType.BRV, 2.5, stat_type="physical"),
        DamageEffect(DamageType.HP, 5.0, stat_type="physical"),
        # 버프
        BuffEffect(BuffType.EVASION_UP, 1.5, duration=5),  # 회피 +150%
        BuffEffect(BuffType.CRITICAL_UP, 1.0, duration=5),  # 크리티컬 +100%
        BuffEffect(BuffType.ATTACK_UP, 0.8, duration=5),
        # 궁극기는 예외적으로 은신 유지
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.sfx = "186"  # FFVII ultimate shadow sound
    # ultimate.cooldown = 8  # 쿨다운 시스템 제거됨
    ultimate.metadata = {"ultimate": True, "perfect_stealth": True}

    return [shadow_slash, assassinate, vanish, backstab, throat_slit,
            shadow_step, death_mark, shadow_clone, silent_execution, ultimate]

def register_assassin_skills(skill_manager):
    """암살자 스킬 등록"""
    skills = create_assassin_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
