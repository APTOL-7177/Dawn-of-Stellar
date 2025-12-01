"""
세피로스 전용 스킬

20층 최종 보스 세피로스의 3페이즈 스킬
"""

from typing import List
from src.combat.enemy_skills import EnemySkill, SkillTargetType


class SephirothSkillDatabase:
    """세피로스 전용 스킬 데이터베이스"""

    @staticmethod
    def get_phase_1_skills() -> List[EnemySkill]:
        """
        페이즈 1: 절망 (HP 100% ~ 66%)

        테마: 압도적인 절망감, 플레이어를 압박
        """
        skills = []

        # 1. 어둠의 낫 - BRV 축적 공격
        skills.append(EnemySkill(
            skill_id="sephiroth_dark_scythe",
            name="어둠의 낫",
            description="어둠 속성의 강력한 BRV 공격",
            target_type=SkillTargetType.SINGLE_ENEMY,
            mp_cost=20,
            damage_multiplier=2.5,  # 공격력의 2.5배
            is_magical=True,
            brv_damage=800,  # 기본 BRV 데미지
            use_probability=0.4,
            cooldown=1,
            min_hp_percent=0.66,  # HP 66% 이상
            max_hp_percent=1.0,
            sfx=("enemy", "dark_attack")
        ))

        # 2. 절망의 안개 - 전체 회피율 감소 디버프
        skills.append(EnemySkill(
            skill_id="sephiroth_despair_fog",
            name="절망의 안개",
            description="전체에게 절망의 안개를 퍼뜨려 회피율 감소",
            target_type=SkillTargetType.ALL_ENEMIES,
            mp_cost=30,
            damage_multiplier=0.8,
            is_magical=True,
            brv_damage=300,
            status_effects=["evasion_down", "accuracy_down"],
            status_duration=3,
            status_intensity=0.7,  # 강한 디버프
            debuff_stats={"evasion": 0.5, "accuracy": 0.8},  # 회피율 50%, 명중률 80%
            use_probability=0.25,
            cooldown=3,
            min_hp_percent=0.66,
            max_hp_percent=1.0,
            sfx=("enemy", "debuff")
        ))

        # 3. 무의 검 - HP 공격
        skills.append(EnemySkill(
            skill_id="sephiroth_void_blade",
            name="무의 검",
            description="축적한 BRV를 HP 데미지로 전환",
            target_type=SkillTargetType.SINGLE_ENEMY,
            mp_cost=25,
            hp_attack=True,  # BRV를 HP로 전환
            use_probability=0.3,
            cooldown=2,
            min_hp_percent=0.66,
            max_hp_percent=1.0,
            sfx=("enemy", "slash")
        ))

        # 4. 시공 왜곡 - ATB 감소
        skills.append(EnemySkill(
            skill_id="sephiroth_time_distortion",
            name="시공 왜곡",
            description="시공간을 왜곡하여 적의 시간을 뒤틀음",
            target_type=SkillTargetType.RANDOM_ENEMY,
            mp_cost=40,
            damage_multiplier=1.0,
            is_magical=True,
            brv_damage=200,
            status_effects=["slow"],  # 느려짐
            status_duration=2,
            status_intensity=0.8,
            use_probability=0.2,
            cooldown=4,
            min_hp_percent=0.66,
            max_hp_percent=1.0,
            sfx=("enemy", "magic")
        ))

        return skills

    @staticmethod
    def get_phase_2_skills() -> List[EnemySkill]:
        """
        페이즈 2: 광기 (HP 66% ~ 33%)

        테마: 통제를 잃은 광폭화, 강력하지만 취약
        """
        skills = []

        # 5. 광기의 불꽃 - 랜덤 속성 전체 공격
        skills.append(EnemySkill(
            skill_id="sephiroth_madness_flames",
            name="광기의 불꽃",
            description="타오르는 광기로 전체를 불태움",
            target_type=SkillTargetType.ALL_ENEMIES,
            mp_cost=50,
            damage_multiplier=2.0,
            is_magical=True,
            brv_damage=600,
            status_effects=["burn"],  # 화상
            status_duration=3,
            status_intensity=1.0,  # 강력한 화상
            use_probability=0.35,
            cooldown=2,
            min_hp_percent=0.33,
            max_hp_percent=0.66,
            sfx=("enemy", "fire_attack")
        ))

        # 6. 차원 붕괴의 검 - 전체 HP 공격
        skills.append(EnemySkill(
            skill_id="sephiroth_dimension_collapse",
            name="차원 붕괴의 검",
            description="차원을 찢는 일격으로 전체를 공격",
            target_type=SkillTargetType.ALL_ENEMIES,
            mp_cost=80,
            damage_multiplier=3.5,  # 매우 강력
            is_magical=True,
            brv_damage=1200,
            hp_attack=True,  # BRV + HP 동시 공격
            use_probability=0.25,
            cooldown=5,
            min_hp_percent=0.33,
            max_hp_percent=0.66,
            sfx=("enemy", "ultimate")
        ))

        # 7. 자기 강화 - 광기의 힘
        skills.append(EnemySkill(
            skill_id="sephiroth_berserk_power",
            name="광기의 힘",
            description="광기에 물들어 공격력 대폭 상승, 방어력 감소",
            target_type=SkillTargetType.SELF,
            mp_cost=30,
            buff_stats={
                "physical_attack": 1.5,  # 물리 공격력 +50%
                "magic_attack": 1.5,     # 마법 공격력 +50%
                "physical_defense": 0.7,  # 물리 방어력 -30%
                "magic_defense": 0.7,     # 마법 방어력 -30%
                "speed": 1.3             # 속도 +30%
            },
            status_duration=4,
            use_probability=0.3,
            cooldown=6,
            min_hp_percent=0.33,
            max_hp_percent=0.66,
            sfx=("enemy", "buff")
        ))

        # 8. 혼돈의 연격 - 3회 연속 공격 (시뮬레이션: 높은 배율)
        skills.append(EnemySkill(
            skill_id="sephiroth_chaos_barrage",
            name="혼돈의 연격",
            description="광기의 속도로 3회 연속 공격 (시뮬레이션)",
            target_type=SkillTargetType.RANDOM_ENEMY,
            mp_cost=60,
            damage_multiplier=4.0,  # 3회 연속을 시뮬레이션한 높은 배율
            is_magical=False,  # 물리 공격
            brv_damage=500,
            use_probability=0.3,
            cooldown=3,
            min_hp_percent=0.33,
            max_hp_percent=0.66,
            sfx=("enemy", "combo_attack")
        ))

        return skills

    @staticmethod
    def get_phase_3_skills() -> List[EnemySkill]:
        """
        페이즈 3: 해방 (HP 33% ~ 0%)

        테마: 죽음을 갈망, 최대 화력 + 방어 포기
        """
        skills = []

        # 9. 일격필살 - 단일 대상 초강력 공격
        skills.append(EnemySkill(
            skill_id="sephiroth_one_shot_kill",
            name="일격필살",
            description="단 한 번의 일격으로 적을 쓰러뜨림",
            target_type=SkillTargetType.SINGLE_ENEMY,
            mp_cost=100,
            damage_multiplier=6.0,  # 압도적인 데미지
            is_magical=False,
            brv_damage=2000,
            hp_attack=True,
            use_probability=0.35,
            cooldown=4,
            min_hp_percent=0.0,
            max_hp_percent=0.33,
            sfx=("enemy", "critical_hit")
        ))

        # 10. 인류의 이름으로 - 궁극기 (HP 10% 이하)
        skills.append(EnemySkill(
            skill_id="sephiroth_humanity_final",
            name="인류의 이름으로",
            description="최후의 일격. 모든 것을 태워 끝을 맞이한다",
            target_type=SkillTargetType.ALL_ENEMIES,
            hp_cost=0,  # HP 코스트 없음 (사망 직전)
            mp_cost=200,
            damage_multiplier=8.0,  # 최강 데미지
            is_magical=True,
            brv_damage=3000,
            hp_attack=True,
            status_effects=["burn", "wound"],
            status_duration=5,
            status_intensity=1.5,  # 극강 상태이상
            use_probability=0.8,  # 높은 확률
            cooldown=999,  # 1회만 사용
            min_hp_percent=0.0,
            max_hp_percent=0.1,  # HP 10% 이하일 때만
            sfx=("enemy", "final_attack")
        ))

        # 11. 희생의 빛 - 랜덤 아군 버프 (지고 싶어함)
        skills.append(EnemySkill(
            skill_id="sephiroth_sacrifice_light",
            name="희생의 빛",
            description="...부탁이야... 날 막아줘...",
            target_type=SkillTargetType.RANDOM_ENEMY,  # 아군을 버프 (적 입장에서 RANDOM_ENEMY)
            mp_cost=50,
            buff_stats={
                "physical_attack": 1.3,
                "magic_attack": 1.3,
                "physical_defense": 1.2,
                "magic_defense": 1.2,
                "speed": 1.2
            },
            heal_amount=500,  # 추가 회복
            status_duration=3,
            use_probability=0.15,  # 낮은 확률 (가끔 도움)
            cooldown=5,
            min_hp_percent=0.0,
            max_hp_percent=0.33,
            sfx=("support", "buff")
        ))

        # 12. 최후의 광기 - 자신 버프 (방어 포기, 공격 최대화)
        skills.append(EnemySkill(
            skill_id="sephiroth_final_madness",
            name="최후의 광기",
            description="더 이상 물러설 곳이 없다. 모든 것을 불태운다",
            target_type=SkillTargetType.SELF,
            mp_cost=80,
            buff_stats={
                "physical_attack": 2.0,  # 공격력 2배
                "magic_attack": 2.0,
                "physical_defense": 0.5,  # 방어력 절반
                "magic_defense": 0.5,
                "speed": 1.5
            },
            status_duration=999,  # 영구 (전투 끝까지)
            use_probability=0.25,
            cooldown=999,  # 1회만 사용
            min_hp_percent=0.0,
            max_hp_percent=0.2,  # HP 20% 이하
            sfx=("enemy", "power_up")
        ))

        # 13. 시공붕괴 - 전체 공격 (페이즈 3 일반 공격)
        skills.append(EnemySkill(
            skill_id="sephiroth_spacetime_collapse",
            name="시공붕괴",
            description="시공간이 무너진다",
            target_type=SkillTargetType.ALL_ENEMIES,
            mp_cost=70,
            damage_multiplier=3.0,
            is_magical=True,
            brv_damage=1000,
            hp_attack=True,
            use_probability=0.4,
            cooldown=2,
            min_hp_percent=0.0,
            max_hp_percent=0.33,
            sfx=("enemy", "aoe_attack")
        ))

        return skills

    @staticmethod
    def get_all_sephiroth_skills() -> List[EnemySkill]:
        """
        세피로스의 모든 스킬 (페이즈 통합)

        전투 중 HP에 따라 자동으로 사용 가능한 스킬이 결정됨
        """
        skills = []
        skills.extend(SephirothSkillDatabase.get_phase_1_skills())
        skills.extend(SephirothSkillDatabase.get_phase_2_skills())
        skills.extend(SephirothSkillDatabase.get_phase_3_skills())
        return skills

    @staticmethod
    def get_current_phase(current_hp: int, max_hp: int) -> int:
        """
        현재 HP에 따른 페이즈 반환

        Args:
            current_hp: 현재 HP
            max_hp: 최대 HP

        Returns:
            페이즈 번호 (1, 2, 3)
        """
        hp_percent = current_hp / max_hp if max_hp > 0 else 0

        if hp_percent >= 0.66:
            return 1  # 페이즈 1: 절망
        elif hp_percent >= 0.33:
            return 2  # 페이즈 2: 광기
        else:
            return 3  # 페이즈 3: 해방

    @staticmethod
    def get_phase_dialogue(phase: int, hp_percent: float) -> str:
        """
        페이즈별 대사

        Args:
            phase: 페이즈 번호
            hp_percent: HP 퍼센트

        Returns:
            대사 문자열
        """
        if phase == 1:
            dialogues = [
                "끝없는 어둠 속에 난 서 있어...",
                "희망은 없다. 모든 것은 무너진다.",
                "10만 번... 10만 번이나 봤다... 인류의 멸망을...",
                "이 세계는 이미 끝났다."
            ]
        elif phase == 2:
            dialogues = [
                "타올라! 타올라! 내 안의 불꽃!",
                "1,000개의 영혼이 울부짖는다!",
                "무엇이 진짜인지... 알 수 없어...",
                "광기가... 나를 삼킨다..."
            ]
        else:  # phase == 3
            if hp_percent <= 0.1:
                dialogues = [
                    "...부탁이야... 날 막아줘...",
                    "내가 무너져야... 세상이 살아...",
                    "인류의 이름으로... 끝을 맞아..."
                ]
            else:
                dialogues = [
                    "날 막아줘... 나를 멈춰줘...",
                    "이제... 지쳐버렸어...",
                    "네가... 희망이 될 수 있는가...?",
                    "제발... 이 손에 쥔 불꽃을 꺼줘..."
                ]

        import random
        return random.choice(dialogues)

    @staticmethod
    def get_phase_transition_message(phase: int) -> str:
        """페이즈 전환 메시지"""
        if phase == 2:
            return "\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n세피로스가 광기에 물들어간다!\n「 페이즈 2: 광기 」\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        elif phase == 3:
            return "\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n세피로스가 절규한다... \"날 막아줘...\"\n「 페이즈 3: 해방 」\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        return ""
