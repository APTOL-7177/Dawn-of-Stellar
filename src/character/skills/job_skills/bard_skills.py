"""Bard Skills - 바드 스킬 (멜로디/옥타브 시스템)"""
from src.character.skills.skill import Skill
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.skills.effects.damage_effect import DamageEffect, DamageType
from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
from src.character.skills.effects.heal_effect import HealEffect, HealType
from src.character.skills.effects.buff_effect import BuffEffect, BuffType
from src.character.skills.effects.atb_effect import AtbEffect
from src.character.skills.costs.mp_cost import MPCost
from src.character.skills.costs.stack_cost import StackCost

def create_bard_skills():
    """바드 10개 스킬 생성 (멜로디/옥타브 시스템)"""

    skills = []

    # 1. 기본 BRV: 음표 공격
    note_attack = Skill("bard_note_attack", "음표 공격", "음표로 적을 공격하고 멜로디 1음 획득")
    note_attack.effects = [
        DamageEffect(DamageType.BRV, 1.3, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "melody_stacks", 1, max_value=7)
    ]
    note_attack.costs = []  # 기본 공격은 MP 소모 없음
    note_attack.sfx = ("skill", "bell")  # 음표 공격
    note_attack.metadata = {"melody_gain": 1}
    skills.append(note_attack)

    # 2. 기본 HP: 화음 타격
    chord_strike = Skill("bard_chord_strike", "화음 타격", "멜로디를 소비하여 HP 공격")
    chord_strike.effects = [
        DamageEffect(DamageType.HP, 1.0, gimmick_bonus={"field": "melody_stacks", "multiplier": 0.15}),
        GimmickEffect(GimmickOperation.CONSUME, "melody_stacks", 1)
    ]
    chord_strike.costs = []  # 기본 공격은 MP 소모 없음
    chord_strike.sfx = ("skill", "sound1")  # 화음 타격
    chord_strike.metadata = {"melody_cost": 1, "melody_scaling": True}
    skills.append(chord_strike)

    # 3. 음계 상승
    scale_up = Skill("bard_scale_up", "음계 상승", "멜로디 3음 획득")
    scale_up.effects = [
        GimmickEffect(GimmickOperation.ADD, "melody_stacks", 3, max_value=7)
    ]
    scale_up.costs = []
    scale_up.target_type = "self"
    # scale_up.cooldown = 3  # 쿨다운 시스템 제거됨
    scale_up.sfx = ("skill", "haste")  # 음계 상승
    scale_up.metadata = {"melody_gain": 3}
    skills.append(scale_up)

    # 4. 회복의 노래
    healing_song = Skill("bard_healing_song", "회복의 노래", "아군 회복 + 멜로디 획득")
    healing_song.effects = [
        HealEffect(HealType.HP, percentage=0.55, is_party_wide=True),  # 회복의 노래 (파티 힐)
        GimmickEffect(GimmickOperation.ADD, "melody_stacks", 1, max_value=7)
    ]
    healing_song.costs = [MPCost(5)]
    healing_song.target_type = "party"
    # healing_song.cooldown = 3  # 쿨다운 시스템 제거됨
    healing_song.cast_time = 0.2  # ATB 20% 캐스팅
    healing_song.sfx = ("skill", "bell")  # 회복의 노래
    healing_song.metadata = {"healing": True, "party_wide": True, "melody_gain": 1}
    skills.append(healing_song)

    # 5. 전율 (크레센도)
    crescendo = Skill("bard_crescendo", "전율", "멜로디에 비례한 BRV 공격")
    crescendo.effects = [
        DamageEffect(DamageType.BRV, 1.5, gimmick_bonus={"field": "melody_stacks", "multiplier": 0.3}, stat_type="magical"),
        GimmickEffect(GimmickOperation.ADD, "melody_stacks", 1, max_value=7)
    ]
    crescendo.costs = [MPCost(4)]
    # crescendo.cooldown = 2  # 쿨다운 시스템 제거됨
    crescendo.sfx = ("skill", "sound2")  # 전율
    crescendo.metadata = {"melody_scaling": True, "melody_gain": 1}
    skills.append(crescendo)

    # 6. 공명 (파티 버프)
    resonance = Skill("bard_resonance", "공명", "파티 전체 공격력 상승")
    resonance.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.25, duration=3, is_party_wide=True),
        GimmickEffect(GimmickOperation.ADD, "melody_stacks", 1, max_value=7)
    ]
    resonance.costs = [MPCost(6)]
    resonance.target_type = "party"
    # resonance.cooldown = 4  # 쿨다운 시스템 제거됨
    resonance.sfx = ("skill", "sound1")  # 공명
    resonance.metadata = {"buff": True, "party_wide": True, "melody_gain": 1}
    skills.append(resonance)

    # 7. 화음 완성 (옥타브 완성)
    perfect_harmony = Skill("bard_perfect_harmony", "화음 완성", "7음 소비, 파티 전체 강화")
    perfect_harmony.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.4, duration=4, is_party_wide=True),
        BuffEffect(BuffType.MAGIC_UP, 0.4, duration=4, is_party_wide=True),
        BuffEffect(BuffType.SPEED_UP, 0.3, duration=4, is_party_wide=True),
        GimmickEffect(GimmickOperation.ADD, "octave_completed", 1)
    ]
    perfect_harmony.costs = [MPCost(8), StackCost("melody_stacks", 7)]  # 멜로디 7음 필요
    perfect_harmony.target_type = "party"
    # perfect_harmony.cooldown = 5  # 쿨다운 시스템 제거됨
    perfect_harmony.cast_time = 0.4  # ATB 40% 캐스팅
    perfect_harmony.sfx = ("skill", "bell")  # 화음 완성
    perfect_harmony.metadata = {"octave": True, "melody_cost": 7, "buff": True, "party_wide": True}
    skills.append(perfect_harmony)

    # 8. 불협화음 (디버프 공격)
    discord = Skill("bard_discord", "불협화음", "멜로디 2음 소비, 적 약화 공격")
    discord.effects = [
        DamageEffect(DamageType.BRV_HP, 1.8, stat_type="magical"),
        BuffEffect(BuffType.DEFENSE_DOWN, 0.3, duration=3)
    ]
    discord.costs = [MPCost(7), StackCost("melody_stacks", 2)]  # 멜로디 2음 필요
    # discord.cooldown = 3  # 쿨다운 시스템 제거됨
    discord.sfx = ("skill", "sound3")  # 불협화음
    discord.metadata = {"melody_cost": 2, "debuff": True}
    skills.append(discord)

    # 9. 강화 협주곡 (NEW - 10번째 스킬로 만들기 위해 추가)
    fortissimo = Skill("bard_fortissimo", "강화 협주곡", "멜로디 4음 소비 대규모 버프")
    fortissimo.effects = [
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=4, is_party_wide=True),
        BuffEffect(BuffType.DEFENSE_UP, 0.4, duration=4, is_party_wide=True),
        BuffEffect(BuffType.CRITICAL_UP, 0.3, duration=4, is_party_wide=True),
        GimmickEffect(GimmickOperation.CONSUME, "melody_stacks", 4)
    ]
    fortissimo.costs = [MPCost(9), StackCost("melody_stacks", 4)]
    fortissimo.target_type = "party"
    # fortissimo.cooldown = 5  # 쿨다운 시스템 제거됨
    fortissimo.sfx = ("skill", "sound2")  # 강화 협주곡
    fortissimo.metadata = {"melody_cost": 4, "buff": True, "party_wide": True}
    skills.append(fortissimo)

    # 10. 궁극기: 교향곡
    ultimate = Skill("bard_ultimate", "교향곡", "모든 멜로디로 파티 강화 + 적 섬멸")
    ultimate.effects = [
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "melody_stacks", "multiplier": 0.5}, stat_type="magical"),
        DamageEffect(DamageType.BRV, 2.0, gimmick_bonus={"field": "octave_completed", "multiplier": 0.3}, stat_type="magical"),
        DamageEffect(DamageType.HP, 2.5),
        BuffEffect(BuffType.ATTACK_UP, 0.5, duration=5, is_party_wide=True),
        BuffEffect(BuffType.MAGIC_UP, 0.5, duration=5, is_party_wide=True),
        BuffEffect(BuffType.CRITICAL_UP, 0.3, duration=5, is_party_wide=True),
        GimmickEffect(GimmickOperation.SET, "melody_stacks", 0)
    ]
    ultimate.costs = [MPCost(30)]
    ultimate.is_ultimate = True
    ultimate.cooldown = 15  # 궁극기 쿨타임 15턴
    ultimate.target_type = "all_enemies"
    ultimate.is_aoe = True
    ultimate.cast_time = 0.8  # ATB 80% 캐스팅 (궁극기)
    ultimate.sfx = ("skill", "limit_break")  # 궁극기
    # ultimate.cooldown = 8  # 쿨다운 시스템 제거됨
    ultimate.metadata = {"ultimate": True, "melody_consume_all": True, "octave_scaling": True, "party_wide": True, "aoe": True}
    skills.append(ultimate)

    return skills

def register_bard_skills(skill_manager):
    """바드 스킬 등록"""
    skills = create_bard_skills()
    for skill in skills:
        skill_manager.register_skill(skill)

    # 팀워크 스킬: 용기의 노래
    teamwork = TeamworkSkill(
        "bard_teamwork",
        "용기의 노래",
        "아군 전체 공격력/마력 1.25배 (3턴) + ATB +250 + 선율 게이지 +30",
        gauge_cost=125
    )
    teamwork.effects = [
        # 아군 전체 공격력 1.25배 (3턴)
        BuffEffect(BuffType.ATTACK_UP, 0.25, duration=3, is_party_wide=True),
        # 아군 전체 마력 1.25배 (3턴)
        BuffEffect(BuffType.MAGIC_UP, 0.25, duration=3, is_party_wide=True),
        # ATB +250 (아군 전체)
        AtbEffect(atb_change=250, is_party_wide=True),
        # 선율 게이지 +30
        GimmickEffect(GimmickOperation.ADD, "melody_gauge", 30)
    ]
    teamwork.costs = [MPCost(0)]
    teamwork.sfx = ("skill", "limit_break")
    teamwork.metadata = {"teamwork": True, "chain": True}
    skills.append(teamwork)
    return skills
