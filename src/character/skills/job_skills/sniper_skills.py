"""Sniper Skills - 저격수 스킬 (탄창 재장전 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.costs.mp_cost import MPCost

def create_sniper_skills():
    """저격수 10개 스킬 생성 (탄창 재장전 시스템)"""

    # 1. 기본 BRV: 정밀 사격 (탄환 1발 소모)
    precise_shot = Skill("sniper_precise_shot", "정밀 사격", "현재 탄환 1발 사격")
    precise_shot.effects = [
        DamageEffect(DamageType.BRV, 2.0,
                    conditional_bonus={"condition": "last_bullet", "multiplier": 1.3})
    ]
    precise_shot.costs = []  # 기본 공격은 MP 소모 없음
    precise_shot.metadata = {"bullets_used": 1, "uses_magazine": True}

    # 2. 기본 HP: 헤드샷 (탄환 1발 소모, 크리티컬 확정)
    headshot = Skill("sniper_headshot", "헤드샷", "크리티컬 확정 강타, 탄환 1발")
    headshot.effects = [
        DamageEffect(DamageType.HP, 3.0,
                    conditional_bonus={"condition": "last_bullet", "multiplier": 1.3})
    ]
    headshot.costs = []  # 기본 공격은 MP 소모 없음
    headshot.metadata = {"bullets_used": 1, "uses_magazine": True, "crit_guaranteed": True}

    # 3. 더블 탭 (2발 연속 사격)
    double_tap = Skill("sniper_double_tap", "더블 탭", "2발 연속 사격")
    double_tap.effects = [
        DamageEffect(DamageType.BRV, 1.8),
        DamageEffect(DamageType.BRV, 1.8)
    ]
    double_tap.costs = [MPCost(10)]
    double_tap.metadata = {"bullets_used": 2, "uses_magazine": True}

    # 4. 재장전 (탄창 6발 충전)
    reload = Skill("sniper_reload", "재장전", "탄창 6발 충전 (기본 탄환)")
    reload.effects = [
        GimmickEffect(GimmickOperation.RELOAD_MAGAZINE, "magazine", 6,
                     bullet_type="normal")
    ]
    reload.costs = [MPCost(6)]
    reload.target_type = "self"
    reload.metadata = {"reload": True, "bullet_type": "normal", "amount": 6}

    # 5. 관통탄 장전 (2발)
    load_penetrating = Skill("sniper_load_penetrating", "관통탄 장전",
                            "관통탄 2발 장전 (방어 무시 50%)")
    load_penetrating.effects = [
        GimmickEffect(GimmickOperation.LOAD_BULLETS, "magazine", 2,
                     bullet_type="penetrating")
    ]
    load_penetrating.costs = [MPCost(12)]
    load_penetrating.target_type = "self"
    load_penetrating.metadata = {"load": True, "bullet_type": "penetrating", "amount": 2}

    # 6. 폭발탄 장전 (2발)
    load_explosive = Skill("sniper_load_explosive", "폭발탄 장전",
                          "폭발탄 2발 장전 (광역 피해 50%)")
    load_explosive.effects = [
        GimmickEffect(GimmickOperation.LOAD_BULLETS, "magazine", 2,
                     bullet_type="explosive")
    ]
    load_explosive.costs = [MPCost(16)]
    load_explosive.target_type = "self"
    load_explosive.metadata = {"load": True, "bullet_type": "explosive", "amount": 2}

    # 7. 완벽한 조준 (버프)
    perfect_aim = Skill("sniper_perfect_aim", "완벽한 조준",
                       "다음 3발 명중률 100%, 크리티컬 +30%")
    perfect_aim.effects = [
        BuffEffect(BuffType.ACCURACY_UP, 1.0, duration=3),
        BuffEffect(BuffType.CRITICAL_UP, 0.3, duration=3)
    ]
    perfect_aim.costs = [MPCost(14)]
    perfect_aim.target_type = "self"
    perfect_aim.cooldown = 4

    # 8. 연막탄 (회피 버프)
    smoke_grenade = Skill("sniper_smoke_grenade", "연막탄",
                         "3턴간 회피율 +40%, 적 명중률 -30%")
    smoke_grenade.effects = [
        BuffEffect(BuffType.EVASION_UP, 0.4, duration=3, target="self"),
        BuffEffect(BuffType.ACCURACY_DOWN, 0.3, duration=3, target="all_enemies")
    ]
    smoke_grenade.costs = [MPCost(15)]
    smoke_grenade.cooldown = 4
    smoke_grenade.metadata = {"smoke": True}

    # 9. 트랩 설치 (적 디버프)
    set_trap = Skill("sniper_set_trap", "트랩 설치",
                    "다음 턴 적 이동 시 피해 + 속도 -50%")
    set_trap.effects = [
        DamageEffect(DamageType.BRV, 2.0),
        BuffEffect(BuffType.SPEED_DOWN, 0.5, duration=2)
    ]
    set_trap.costs = [MPCost(12)]
    set_trap.target_type = "single_enemy"
    set_trap.cooldown = 3
    set_trap.metadata = {"trap": True}

    # 10. 궁극기: 데드아이 (탄창의 모든 탄환 연속 발사)
    deadeye = Skill("sniper_deadeye", "데드아이",
                   "탄창의 모든 탄환을 연속 발사")
    deadeye.effects = [
        # 실제 탄환 수만큼 반복 공격 (스킬 실행 시 동적 처리)
        DamageEffect(DamageType.BRV, 2.5),
        DamageEffect(DamageType.HP, 1.5)
    ]
    deadeye.costs = [MPCost(30)]
    deadeye.is_ultimate = True
    deadeye.cooldown = 8
    deadeye.metadata = {"uses_all_bullets": True, "deadeye": True}

    return [precise_shot, headshot, double_tap, reload,
            load_penetrating, load_explosive, perfect_aim, smoke_grenade,
            set_trap, deadeye]

def register_sniper_skills(skill_manager):
    """저격수 스킬 등록"""
    skills = create_sniper_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    return [s.skill_id for s in skills]
