"""Bard Skills - 바드 (악보 작곡 시스템)

스킬 사용 시 음표가 악보에 추가되고,
특정 패턴 완성 시 강력한 효과 발동!

음표: A(공격), B(버프), S(서포트)
"한 음 한 음이 전장의 운명을 바꾼다"
"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.status_effect import StatusEffect, StatusType
from src.character.skills.costs.mp_cost import MPCost
from src.core.logger import get_logger

logger = get_logger("bard_skills")


def create_bard_skills():
    """바드 11개 스킬 생성 (악보 작곡 시스템)"""
    
    skills = []
    
    # ============================================================
    # 1. 음표 타격 (기본 BRV + A 추가)
    # ============================================================
    note_strike = Skill(
        "bard_note_strike",
        "음표 타격",
        "음파로 공격! 악보에 A 음표 추가."
    )
    note_strike.effects = [
        DamageEffect(DamageType.BRV, 1.4, stat_type="magic"),
    ]
    note_strike.costs = []
    note_strike.sfx = ("combat", "attack_magic")
    note_strike.metadata = {
        "basic_attack": True,
        "note_type": "attack",
        "note_add": "A"
    }
    skills.append(note_strike)
    
    # ============================================================
    # 2. 화음파 (기본 HP + B 추가)
    # ============================================================
    chord_wave = Skill(
        "bard_chord_wave",
        "화음파",
        "화음의 파동! HP 피해 + 악보에 B 추가."
    )
    chord_wave.effects = [
        DamageEffect(DamageType.HP, 1.0, stat_type="magic"),
    ]
    chord_wave.costs = []
    chord_wave.sfx = ("skill", "magic_cast")
    chord_wave.metadata = {
        "basic_attack": True,
        "note_type": "buff",
        "note_add": "B"
    }
    skills.append(chord_wave)
    
    # ============================================================
    # 3. 전투 행진곡 (파티 버프 + B)
    # ============================================================
    battle_march = Skill(
        "bard_battle_march",
        "전투 행진곡",
        "힘찬 행진곡! 파티 공격력/속도 UP + B 추가."
    )
    battle_march.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.25, duration=4, is_party_wide=True),
        BuffEffect(BuffType.SPEED_UP, 0.2, duration=4, is_party_wide=True),
    ]
    battle_march.costs = [MPCost(10)]
    battle_march.target_type = "all_allies"
    battle_march.sfx = ("character", "status_buff")
    battle_march.metadata = {
        "party_buff": True,
        "note_type": "buff",
        "note_add": "B"
    }
    skills.append(battle_march)
    
    # ============================================================
    # 4. 치유의 선율 (파티 힐 + S)
    # ============================================================
    healing_melody = Skill(
        "bard_healing_melody",
        "치유의 선율",
        "부드러운 선율로 파티 전체 회복 + S 추가."
    )
    healing_melody.effects = [
        HealEffect(HealType.HP, percentage=0.25, is_party_wide=True),
    ]
    healing_melody.costs = [MPCost(12)]
    healing_melody.target_type = "all_allies"
    healing_melody.sfx = ("character", "hp_heal")
    healing_melody.metadata = {
        "party_heal": True,
        "note_type": "support",
        "note_add": "S"
    }
    skills.append(healing_melody)
    
    # ============================================================
    # 5. 영감의 노래 (크리티컬 버프 + B)
    # ============================================================
    inspire_song = Skill(
        "bard_inspire_song",
        "영감의 노래",
        "영감을 불어넣는 노래! 파티 크리티컬 UP + B 추가."
    )
    inspire_song.effects = [
        BuffEffect(BuffType.CRITICAL_UP, 0.3, duration=4, is_party_wide=True),
        BuffEffect(BuffType.ACCURACY_UP, 0.2, duration=4, is_party_wide=True),
    ]
    inspire_song.costs = [MPCost(8)]
    inspire_song.target_type = "all_allies"
    inspire_song.sfx = ("character", "status_buff")
    inspire_song.metadata = {
        "party_buff": True,
        "note_type": "buff",
        "note_add": "B"
    }
    skills.append(inspire_song)
    
    # ============================================================
    # 6. 진혼곡 (적 약화 + S)
    # ============================================================
    requiem = Skill(
        "bard_requiem",
        "진혼곡",
        "슬픈 진혼곡으로 적을 약화! 전체 디버프 + S 추가."
    )
    requiem.effects = [
        DamageEffect(DamageType.BRV, 1.2, stat_type="magic"),
        BuffEffect(BuffType.ATTACK_DOWN, 0.25, duration=3),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.2, duration=3),
    ]
    requiem.costs = [MPCost(10)]
    requiem.target_type = "all_enemies"
    requiem.is_aoe = True
    requiem.sfx = ("character", "status_debuff")
    requiem.metadata = {
        "debuff": True,
        "aoe": True,
        "note_type": "support",
        "note_add": "S"
    }
    skills.append(requiem)
    
    # ============================================================
    # 7. 자장가 (적 수면 + S)
    # ============================================================
    lullaby = Skill(
        "bard_lullaby",
        "자장가",
        "달콤한 자장가로 적을 재운다! 수면 + S 추가."
    )
    lullaby.effects = [
        StatusEffect(StatusType.SLEEP, 2, 1.0),  # 2턴 수면
        BuffEffect(BuffType.SPEED_DOWN, 0.4, duration=2),
    ]
    lullaby.costs = [MPCost(14)]
    lullaby.target_type = "enemy"
    lullaby.sfx = ("character", "status_debuff")
    lullaby.metadata = {
        "cc_skill": True,
        "note_type": "support",
        "note_add": "S"
    }
    skills.append(lullaby)
    
    # ============================================================
    # 8. 작곡 (현재 악보 효과 발동)
    # ============================================================
    compose = Skill(
        "bard_compose",
        "작곡",
        "완성된 악보를 연주한다! 음표 패턴에 따라 효과 발동."
    )
    compose.effects = [
        # 효과는 execute_skill에서 음표 패턴에 따라 적용
        BuffEffect(BuffType.ATTACK_UP, 0.1, duration=2),  # 기본 효과
    ]
    compose.costs = [MPCost(6)]
    compose.target_type = "all_allies"
    compose.sfx = ("skill", "magic_cast")
    compose.metadata = {
        "compose_skill": True,
        "consume_notes": True,
        "pattern_effects": {
            "AAA": {"type": "attack_surge", "value": 0.8, "duration": 3},
            "BBB": {"type": "buff_extend", "value": 2.0},
            "SSS": {"type": "mass_heal", "value": 0.4},
            "ABS": {"type": "all_stat_up", "value": 0.25, "duration": 4},
            "SBA": {"type": "enemy_debuff", "value": 0.25, "duration": 3}
        }
    }
    skills.append(compose)
    
    # ============================================================
    # 9. 즉흥 연주 (랜덤 음표 3개)
    # ============================================================
    improvise = Skill(
        "bard_improvise",
        "즉흥 연주",
        "즉흥적인 연주! 랜덤 음표 3개 추가."
    )
    improvise.effects = [
        DamageEffect(DamageType.BRV, 1.6, stat_type="magic"),
        BuffEffect(BuffType.SPEED_UP, 0.15, duration=2),
    ]
    improvise.costs = [MPCost(8)]
    improvise.sfx = ("skill", "haste")
    improvise.metadata = {
        "random_notes": 3,
        "improvise": True
    }
    skills.append(improvise)
    
    # ============================================================
    # 10. 궁극기: 그랜드 피날레
    # ============================================================
    ultimate = Skill(
        "bard_ultimate",
        "그랜드 피날레",
        "장엄한 피날레! 5음표 교향곡 확정 + 모든 효과 발동."
    )
    ultimate.effects = [
        # 강력한 전체 공격
        DamageEffect(DamageType.BRV, 2.5, stat_type="magic"),
        DamageEffect(DamageType.HP, 2.0, stat_type="magic"),
        # 파티 극강 버프
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=5, is_party_wide=True),
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=5, is_party_wide=True),
        BuffEffect(BuffType.SPEED_UP, 0.3, duration=5, is_party_wide=True),
        BuffEffect(BuffType.CRITICAL_UP, 0.4, duration=5, is_party_wide=True),
        # 파티 힐
        HealEffect(HealType.HP, percentage=0.35, is_party_wide=True),
    ]
    ultimate.costs = [MPCost(35)]
    ultimate.is_ultimate = True
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.sfx = ("skill", "limit_break")
    ultimate.metadata = {
        "ultimate": True,
        "aoe": True,
        "symphony_guaranteed": True,
        "all_effects": True
    }
    skills.append(ultimate)
    
    # ============================================================
    # 팀워크 스킬: 대합주
    # ============================================================
    teamwork = TeamworkSkill(
        "bard_teamwork",
        "대합주",
        "파티 전원이 함께하는 대합주! 전체 버프 + 적 전체 피해.",
        gauge_cost=175
    )
    teamwork.effects = [
        DamageEffect(DamageType.BRV, 2.0, stat_type="magic"),
        DamageEffect(DamageType.HP, 1.5, stat_type="magic"),
        BuffEffect(BuffType.ATTACK_UP, 0.35, duration=4, is_party_wide=True),
        BuffEffect(BuffType.SPEED_UP, 0.25, duration=4, is_party_wide=True),
    ]
    teamwork.target_type = "all_enemies"
    teamwork.is_aoe = True
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "teamwork")
    teamwork.metadata = {
        "teamwork": True,
        "chain": True,
        "full_notes": True,  # 음표 5개로 채움
        "aoe": True
    }
    skills.append(teamwork)
    
    return skills


def register_bard_skills(skill_manager):
    """바드 스킬 등록"""
    skills = create_bard_skills()
    for skill in skills:
        skill_manager.register_skill(skill)
    
    logger.info(f"바드 스킬 {len(skills)}개 등록 완료")
    return [s.skill_id for s in skills]
