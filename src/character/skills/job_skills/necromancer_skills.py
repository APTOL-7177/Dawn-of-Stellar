"""Necromancer Skills - 네크로맨서 스킬 (언데드 군단 관리 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.lifesteal_effect import LifestealEffect
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.hp_cost import HPCost

def create_necromancer_skills():
    """네크로맨서 10개 스킬 생성 (언데드 군단 관리 시스템)"""

    # 1. 기본 BRV: 암흑 화살 (마법 공격)
    shadow_bolt = Skill("necromancer_shadow_bolt", "암흑 화살", "어둠의 마법 공격")
    shadow_bolt.effects = [
        DamageEffect(DamageType.BRV, 1.5, stat_type="magical")
    ]
    shadow_bolt.costs = []  # 기본 공격은 MP 소모 없음
    shadow_bolt.sfx = "012"  # 짧은 마법 공격
    shadow_bolt.metadata = {}

    # 2. 기본 HP: 생명력 흡수 (HP 드레인)
    drain_life = Skill("necromancer_drain_life", "생명력 흡수", "적의 HP를 흡수")
    drain_life.effects = [
        DamageEffect(DamageType.HP, 1.0, stat_type="magical"),
        LifestealEffect(lifesteal_percent=0.15, low_hp_bonus=False)  # 피해의 15% 회복
    ]
    drain_life.costs = []  # 기본 공격은 MP 소모 없음
    drain_life.sfx = "048"  # 짧은 드레인/흡수
    drain_life.metadata = {"drain": True}

    # 3. 스켈레톤 소환 (물리 공격력 +15%)
    summon_skeleton = Skill("necromancer_summon_skeleton", "스켈레톤 소환",
                           "HP 10 소모, 물리 공격력 +15% 증가")
    summon_skeleton.effects = [
        GimmickEffect(GimmickOperation.ADD, "undead_skeleton", 1, max_value=2),
        BuffEffect(BuffType.ATTACK_UP, 0.15, duration=99, target="self")  # 스켈레톤 보유 동안 지속
    ]
    summon_skeleton.costs = [HPCost(10)]
    summon_skeleton.target_type = "self"
    summon_skeleton.sfx = "148"  # 짧은 저주/소환
    summon_skeleton.metadata = {"undead_type": "skeleton"}

    # 4. 좀비 소환 (방어력 +20%, HP 회복)
    summon_zombie = Skill("necromancer_summon_zombie", "좀비 소환",
                         "HP 15 소모, 방어력 +20% & HP회복 +3/턴")
    summon_zombie.effects = [
        GimmickEffect(GimmickOperation.ADD, "undead_zombie", 1, max_value=2),
        BuffEffect(BuffType.DEFENSE_UP, 0.2, duration=99),
        BuffEffect(BuffType.HP_REGEN, 5, duration=99)  # 좀비 소환
    ]
    summon_zombie.costs = [MPCost(7), HPCost(15)]
    summon_zombie.target_type = "self"
    summon_zombie.sfx = "148"  # 짧은 저주/소환
    summon_zombie.metadata = {"undead_type": "zombie"}

    # 5. 유령 소환 (마법 공격력 +20%, 회피율 +10%)
    summon_ghost = Skill("necromancer_summon_ghost", "유령 소환",
                        "HP 20 소모, 마법 공격력 +20% & 회피 +10%")
    summon_ghost.effects = [
        GimmickEffect(GimmickOperation.ADD, "undead_ghost", 1, max_value=2),
        BuffEffect(BuffType.MAGIC_UP, 0.2, duration=99),
        BuffEffect(BuffType.EVASION_UP, 0.1, duration=99)
    ]
    summon_ghost.costs = [MPCost(9), HPCost(20)]
    summon_ghost.target_type = "self"
    summon_ghost.sfx = "148"  # 짧은 저주/소환
    summon_ghost.metadata = {"undead_type": "ghost"}

    # 6. 언데드 희생 (언데드 1마리 희생하여 강력한 공격)
    sacrifice_undead = Skill("necromancer_sacrifice_undead", "언데드 희생",
                            "언데드 1마리 희생, 강력한 피해 + MP 회복")
    sacrifice_undead.effects = [
        DamageEffect(DamageType.BRV_HP, 3.0, stat_type="magical",
                    gimmick_bonus={"field": "total_undead", "multiplier": 0.5}),
        GimmickEffect(GimmickOperation.CONSUME, "undead_skeleton", 1),  # 우선순위: skeleton
        HealEffect(heal_type=HealType.MP, base_amount=20)
    ]
    sacrifice_undead.costs = [MPCost(5)]
    sacrifice_undead.sfx = "146"  # 짧은 폭발
    sacrifice_undead.metadata = {"sacrifice": True}

    # 7. 군단 지휘 (언데드 강화 버프)
    legion_command = Skill("necromancer_legion_command", "군단 지휘",
                          "3턴간 모든 언데드 능력 2배")
    legion_command.effects = [
        BuffEffect(BuffType.CUSTOM, 1.0, duration=3, custom_stat="undead_power_enhanced")
    ]
    legion_command.costs = [MPCost(7)]
    legion_command.target_type = "self"
    legion_command.sfx = "093"  # 짧은 버프
    legion_command.metadata = {"undead_buff": True}

    # 8. 죽음의 파동 (언데드 수에 비례한 광역 공격)
    death_wave = Skill("necromancer_death_wave", "죽음의 파동",
                      "언데드 수에 비례한 광역 공격")
    death_wave.effects = [
        DamageEffect(DamageType.BRV_HP, 2.0, stat_type="magical",
                    gimmick_bonus={"field": "total_undead", "multiplier": 0.4})
    ]
    death_wave.costs = [MPCost(8)]
    death_wave.target_type = "all_enemies"
    death_wave.is_aoe = True
    death_wave.sfx = "146"  # 짧은 광역 마법
    death_wave.metadata = {"death_wave": True}

    # 9. 대량 소환 (모든 언데드 타입 1마리씩 즉시 소환)
    mass_summon = Skill("necromancer_mass_summon", "대량 소환",
                       "HP 50 소모, 모든 언데드 타입 소환")
    mass_summon.effects = [
        GimmickEffect(GimmickOperation.ADD, "undead_skeleton", 1, max_value=2),
        GimmickEffect(GimmickOperation.ADD, "undead_zombie", 1, max_value=2),
        GimmickEffect(GimmickOperation.ADD, "undead_ghost", 1, max_value=2),
        BuffEffect(BuffType.ATTACK_UP, 0.15, duration=99),
        BuffEffect(BuffType.DEFENSE_UP, 0.2, duration=99),
        BuffEffect(BuffType.MAGIC_UP, 0.2, duration=99)
    ]
    mass_summon.costs = [MPCost(11), HPCost(50)]
    mass_summon.target_type = "self"
    mass_summon.sfx = "148"  # 짧은 대량 소환
    mass_summon.metadata = {"mass_summon": True}

    # 10. 궁극기: 언데드 대군단 (모든 언데드 희생, 극한의 피해)
    ultimate = Skill("necromancer_ultimate", "언데드 대군단",
                    "모든 언데드 희생, 극한의 피해")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 3.0, stat_type="magical",
                    gimmick_bonus={"field": "total_undead", "multiplier": 0.8}),
        DamageEffect(DamageType.HP, 3.0, stat_type="magical",
                    gimmick_bonus={"field": "total_undead", "multiplier": 0.6}),
        GimmickEffect(GimmickOperation.SET, "undead_skeleton", 0),
        GimmickEffect(GimmickOperation.SET, "undead_zombie", 0),
        GimmickEffect(GimmickOperation.SET, "undead_ghost", 0)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = "035"  # 짧은 리미트 브레이크
    ultimate.metadata = {"ultimate": True, "legion_sacrifice": True}

    return [shadow_bolt, drain_life, summon_skeleton, summon_zombie, summon_ghost,
            sacrifice_undead, legion_command, death_wave, mass_summon, ultimate]

def register_necromancer_skills(skill_manager):
    """네크로맨서 스킬 등록"""
    skills = create_necromancer_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
