"""
카인 전용 스킬

30층 진 최종 보스 닥터 아벨 카인의 시간 조작 스킬
"""

from typing import List
from src.combat.enemy_skills import EnemySkill, SkillTargetType


class CainSkillDatabase:
    """카인 전용 스킬 데이터베이스"""

    @staticmethod
    def get_all_cain_skills() -> List[EnemySkill]:
        """
        카인의 모든 스킬

        테마: 시간 조작, 예지, 압도적인 힘
        """
        skills = []

        # === 페이즈 공통 스킬 ===

        # 1. 시간 예지 - BRV 축적 + 회피 버프
        skills.append(EnemySkill(
            skill_id="cain_time_foresight",
            name="시간 예지",
            description="미래를 보고 공격을 회피하며 BRV 축적",
            target_type=SkillTargetType.SELF,
            mp_cost=30,
            buff_stats={"evasion": 1.5},  # 회피율 50% 증가
            status_duration=2,
            use_probability=0.35,
            cooldown=1,
            sfx=("enemy", "buff")
        ))

        # 2. 시간 단축 - 빠른 BRV 공격
        skills.append(EnemySkill(
            skill_id="cain_time_acceleration",
            name="시간 단축",
            description="시간을 빠르게 하여 신속한 BRV 공격",
            target_type=SkillTargetType.SINGLE_ENEMY,
            mp_cost=40,
            damage_multiplier=2.8,
            is_magical=True,
            use_probability=0.4,
            cooldown=1,
            sfx=("enemy", "magic")
        ))

        # 3. 단절의 일격 - HP 공격
        skills.append(EnemySkill(
            skill_id="cain_temporal_blade",
            name="단절의 일격",
            description="시간의 흐름을 끊어내는 일격",
            target_type=SkillTargetType.SINGLE_ENEMY,
            mp_cost=50,
            hp_attack=True,
            use_probability=0.3,
            cooldown=1,
            sfx=("enemy", "slash")
        ))

        # === 페이즈 1: 시간 조작 (HP 100% ~ 66%) ===

        # 4. 시간 역행 - 자가 회복
        skills.append(EnemySkill(
            skill_id="cain_time_reverse",
            name="시간 역행",
            description="시간을 되돌려 HP 회복",
            target_type=SkillTargetType.SELF,
            mp_cost=100,
            heal_amount=500,
            use_probability=0.25,
            cooldown=3,
            min_hp_percent=0.66,
            max_hp_percent=1.0,
            sfx=("support", "heal")
        ))

        # 5. 시공 왜곡 - 전체 디버프
        skills.append(EnemySkill(
            skill_id="cain_spacetime_distortion",
            name="시공 왜곡",
            description="시공간을 왜곡하여 전체에게 디버프",
            target_type=SkillTargetType.ALL_ENEMIES,
            mp_cost=80,
            damage_multiplier=2.0,
            is_magical=True,
            status_effects=["slow", "accuracy_down"],
            status_duration=3,
            status_intensity=0.8,
            debuff_stats={"speed_down": 0.7, "accuracy_down": 0.8},
            use_probability=0.3,
            cooldown=3,
            min_hp_percent=0.66,
            max_hp_percent=1.0,
            sfx=("enemy", "debuff")
        ))

        # === 페이즈 2: 타임라인 분기 (HP 66% ~ 33%) ===

        # 6. 타임라인 분기 - 전체 HP 공격
        skills.append(EnemySkill(
            skill_id="cain_timeline_split",
            name="타임라인 분기",
            description="여러 타임라인에서 동시 공격",
            target_type=SkillTargetType.ALL_ENEMIES,
            mp_cost=150,
            damage_multiplier=3.0,  # 여러 타임라인 공격 시뮬레이션
            is_magical=True,
            hp_attack=True,
            use_probability=0.3,
            cooldown=4,
            min_hp_percent=0.33,
            max_hp_percent=0.66,
            sfx=("enemy", "ultimate")
        ))

        # 7. 과거의 상처 - 과거 데미지 재적용
        skills.append(EnemySkill(
            skill_id="cain_past_wounds",
            name="과거의 상처",
            description="과거에 입은 상처를 다시 받게 함",
            target_type=SkillTargetType.RANDOM_ENEMY,
            mp_cost=120,
            damage_multiplier=3.0,
            is_magical=True,
            status_effects=["wound"],  # 지속 데미지
            status_duration=4,
            status_intensity=1.0,
            use_probability=0.35,
            cooldown=2,
            min_hp_percent=0.33,
            max_hp_percent=0.66,
            sfx=("enemy", "dark_attack")
        ))

        # 8. 미래 예측 - 자가 강화
        skills.append(EnemySkill(
            skill_id="cain_future_prediction",
            name="미래 예측",
            description="미래를 보고 완벽하게 대응",
            target_type=SkillTargetType.SELF,
            mp_cost=100,
            buff_stats={
                "physical_attack": 1.4,
                "magic_attack": 1.4,
                "evasion": 1.8
            },
            status_duration=3,
            use_probability=0.25,
            cooldown=4,
            min_hp_percent=0.33,
            max_hp_percent=0.66,
            sfx=("enemy", "buff")
        ))

        # === 페이즈 3: 시간의 지배자 (HP 33% ~ 0%) ===

        # 9. 시공 붕괴 - 강력한 단일 공격
        skills.append(EnemySkill(
            skill_id="cain_spacetime_collapse",
            name="시공 붕괴",
            description="시공간 자체를 무기로 사용",
            target_type=SkillTargetType.SINGLE_ENEMY,
            mp_cost=150,
            damage_multiplier=3.0,
            is_magical=True,
            hp_attack=True,
            status_effects=["stun"],
            status_duration=1,
            use_probability=0.35,
            cooldown=2,
            min_hp_percent=0.0,
            max_hp_percent=0.33,
            sfx=("enemy", "critical_hit")
        ))

        # 10. 운명의 지배 - 전체 HP 공격 (궁극기)
        skills.append(EnemySkill(
            skill_id="cain_fate_domination",
            name="운명의 지배",
            description="모든 타임라인의 힘으로 전체를 공격",
            target_type=SkillTargetType.ALL_ENEMIES,
            mp_cost=200,
            damage_multiplier=3.0,
            is_magical=True,
            hp_attack=True,
            status_effects=["curse"],
            status_duration=5,
            status_intensity=1.2,
            use_probability=0.3,
            cooldown=4,
            min_hp_percent=0.0,
            max_hp_percent=0.33,
            sfx=("enemy", "final_attack")
        ))

        # 11. 신의 심판 - HP 10% 이하 최후의 공격
        skills.append(EnemySkill(
            skill_id="cain_divine_judgment",
            name="신의 심판",
            description="불멸의 신의 최후 심판",
            target_type=SkillTargetType.ALL_ENEMIES,
            mp_cost=250,
            damage_multiplier=3.0,
            is_magical=True,
            hp_attack=True,
            use_probability=0.8,
            cooldown=999,  # 1회만 사용
            min_hp_percent=0.0,
            max_hp_percent=0.1,
            sfx=("enemy", "ultimate")
        ))

        # 12. 시간 정지 - 전체 스턴
        skills.append(EnemySkill(
            skill_id="cain_time_stop",
            name="시간 정지",
            description="시간을 멈춰 모두를 무력화",
            target_type=SkillTargetType.ALL_ENEMIES,
            mp_cost=180,
            damage_multiplier=2.5,
            is_magical=True,
            status_effects=["stun"],
            status_duration=1,
            use_probability=0.2,
            cooldown=5,
            min_hp_percent=0.0,
            max_hp_percent=0.33,
            sfx=("enemy", "time_magic")
        ))

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
            return 1  # 페이즈 1: 시간 조작
        elif hp_percent >= 0.33:
            return 2  # 페이즈 2: 타임라인 분기
        else:
            return 3  # 페이즈 3: 시간의 지배자

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
                "미래를 봤어. 네 공격은 빗나가더군.",
                "시간은 내 편이야.",
                "모든 타임라인에서 너는 진다.",
                "재밌군. 하지만 무의미해."
            ]
        elif phase == 2:
            dialogues = [
                "타임라인이 분기한다... 몇 개나 필요할까?",
                "여러 세계에서 동시에 공격받는 기분이 어때?",
                "과거의 상처가 다시 찾아온다.",
                "미래는 이미 결정되어 있어."
            ]
        else:  # phase == 3
            if hp_percent <= 0.1:
                dialogues = [
                    "신의 심판을 받아라!",
                    "이제 진지해지지.",
                    "시간이 없어지는군...",
                    "재밌었어. 정말로."
                ]
            else:
                dialogues = [
                    "시공간이 무너진다!",
                    "내 힘의 극히 일부만 보여주지.",
                    "아직도 희망을 버리지 않는 건가?",
                    "불멸의 힘을 보여주마."
                ]

        import random
        return random.choice(dialogues)

    @staticmethod
    def get_phase_transition_message(phase: int) -> str:
        """페이즈 전환 메시지"""
        if phase == 2:
            return "\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n카인이 타임라인을 분기시킨다!\n「 페이즈 2: 타임라인 분기 」\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        elif phase == 3:
            return "\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n카인: \"이제 진지해지지.\"\n「 페이즈 3: 시간의 지배자 」\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        return ""
