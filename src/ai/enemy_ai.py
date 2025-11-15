"""
적 AI 시스템 - 스킬 선택 및 전략

적이 전투 중 어떤 행동을 할지 결정하는 AI
"""

from typing import List, Optional, Any
import random

from src.combat.enemy_skills import EnemySkill, SkillTargetType
from src.core.logger import get_logger


logger = get_logger("enemy_ai")


class EnemyAI:
    """
    적 AI

    전투 상황을 분석하여 최적의 행동 결정
    """

    def __init__(self, enemy: Any, difficulty: str = "normal"):
        """
        Args:
            enemy: 적 캐릭터
            difficulty: 난이도 ("easy", "normal", "hard", "insane")
        """
        self.enemy = enemy
        self.difficulty = difficulty

        # 난이도별 스킬 사용 확률 조정
        self.skill_use_multiplier = {
            "easy": 0.5,     # 스킬 사용 50% 감소
            "normal": 1.0,   # 기본
            "hard": 1.5,     # 스킬 사용 50% 증가
            "insane": 2.0    # 스킬 사용 2배
        }.get(difficulty, 1.0)

    def decide_action(
        self,
        allies: List[Any],
        enemies: List[Any]
    ) -> dict:
        """
        행동 결정

        Args:
            allies: 아군 목록 (적 입장에서)
            enemies: 적군 목록 (플레이어 파티)

        Returns:
            행동 정보 딕셔너리
            {
                "type": "attack" | "skill" | "defend",
                "skill": EnemySkill (if type == "skill"),
                "target": target_character
            }
        """
        # 스킬이 없으면 일반 공격
        if not hasattr(self.enemy, 'skills') or not self.enemy.skills:
            return self._decide_basic_attack(enemies)

        # 쿨다운 감소
        for skill in self.enemy.skills:
            skill.reduce_cooldown()

        # 사용 가능한 스킬 필터링
        available_skills = [
            skill for skill in self.enemy.skills
            if skill.can_use(self.enemy)
        ]

        if not available_skills:
            # 사용 가능한 스킬 없음 → 일반 공격
            return self._decide_basic_attack(enemies)

        # 상황 분석
        context = self._analyze_situation(allies, enemies)

        # 스킬 선택 (우선순위 기반)
        selected_skill = self._select_skill(available_skills, context)

        if selected_skill:
            # 스킬 사용 확률 체크 (난이도 반영)
            adjusted_probability = selected_skill.use_probability * self.skill_use_multiplier
            if random.random() < adjusted_probability:
                # 대상 선택
                target = self._select_target(selected_skill, allies, enemies)
                if target:
                    # 쿨다운 활성화
                    selected_skill.activate_cooldown()

                    logger.info(
                        f"{self.enemy.name}이(가) {selected_skill.name} 사용! "
                        f"(대상: {getattr(target, 'name', 'Unknown')})"
                    )

                    return {
                        "type": "skill",
                        "skill": selected_skill,
                        "target": target
                    }

        # 스킬 사용하지 않음 → 일반 공격
        return self._decide_basic_attack(enemies)

    def _analyze_situation(
        self,
        allies: List[Any],
        enemies: List[Any]
    ) -> dict:
        """
        전투 상황 분석

        Returns:
            상황 정보 딕셔너리
        """
        # 자신의 HP 비율
        self_hp_percent = self.enemy.current_hp / self.enemy.max_hp if self.enemy.max_hp > 0 else 0

        # 아군 평균 HP
        ally_hp_total = sum(getattr(a, 'current_hp', 0) for a in allies if getattr(a, 'is_alive', True))
        ally_hp_avg = ally_hp_total / len(allies) if allies else 0

        # 적군 평균 HP
        enemy_hp_total = sum(getattr(e, 'current_hp', 0) for e in enemies if getattr(e, 'is_alive', True))
        enemy_hp_avg = enemy_hp_total / len(enemies) if enemies else 0

        # 생존한 아군/적군 수
        alive_allies = sum(1 for a in allies if getattr(a, 'is_alive', True))
        alive_enemies = sum(1 for e in enemies if getattr(e, 'is_alive', True))

        # 가장 약한 적 (HP 기준)
        weakest_enemy = None
        lowest_hp = float('inf')
        for enemy in enemies:
            if getattr(enemy, 'is_alive', True):
                hp = getattr(enemy, 'current_hp', 0)
                if hp < lowest_hp:
                    lowest_hp = hp
                    weakest_enemy = enemy

        # 가장 강한 적 (HP 기준)
        strongest_enemy = None
        highest_hp = 0
        for enemy in enemies:
            if getattr(enemy, 'is_alive', True):
                hp = getattr(enemy, 'current_hp', 0)
                if hp > highest_hp:
                    highest_hp = hp
                    strongest_enemy = enemy

        return {
            "self_hp_percent": self_hp_percent,
            "ally_hp_avg": ally_hp_avg,
            "enemy_hp_avg": enemy_hp_avg,
            "alive_allies": alive_allies,
            "alive_enemies": alive_enemies,
            "weakest_enemy": weakest_enemy,
            "strongest_enemy": strongest_enemy,
            "is_desperate": self_hp_percent < 0.3,  # HP 30% 이하
            "is_low_hp": self_hp_percent < 0.5,     # HP 50% 이하
            "outnumbered": alive_allies < alive_enemies,
            "winning": ally_hp_avg > enemy_hp_avg * 1.5
        }

    def _select_skill(
        self,
        available_skills: List[EnemySkill],
        context: dict
    ) -> Optional[EnemySkill]:
        """
        스킬 선택 (우선순위 기반)

        Args:
            available_skills: 사용 가능한 스킬 목록
            context: 상황 정보

        Returns:
            선택된 스킬 (또는 None)
        """
        # 우선순위 점수 계산
        skill_scores = []

        for skill in available_skills:
            score = skill.use_probability  # 기본 점수

            # 상황별 가중치 조정
            if context["is_desperate"]:
                # 절망적인 상황: 힐/버프 우선
                if skill.heal_amount > 0:
                    score *= 3.0
                if skill.buff_stats:
                    score *= 2.5
                # 필살기 우선
                if skill.damage > 100:
                    score *= 2.0

            elif context["is_low_hp"]:
                # HP 낮음: 힐 우선
                if skill.heal_amount > 0:
                    score *= 2.0

            if context["outnumbered"]:
                # 수적 열세: AoE 스킬 우선
                if skill.target_type == SkillTargetType.ALL_ENEMIES:
                    score *= 1.5

            if context["winning"]:
                # 우세: 공격적인 스킬
                if skill.damage > 0:
                    score *= 1.3

            # MP가 부족하면 낮은 코스트 스킬 우선
            if hasattr(self.enemy, 'current_mp'):
                mp_percent = self.enemy.current_mp / self.enemy.max_mp if self.enemy.max_mp > 0 else 0
                if mp_percent < 0.3:  # MP 30% 이하
                    if skill.mp_cost < 20:
                        score *= 1.5

            skill_scores.append((skill, score))

        if not skill_scores:
            return None

        # 가중치 기반 랜덤 선택
        skills, scores = zip(*skill_scores)
        selected = random.choices(skills, weights=scores, k=1)[0]

        return selected

    def _select_target(
        self,
        skill: EnemySkill,
        allies: List[Any],
        enemies: List[Any]
    ) -> Optional[Any]:
        """
        대상 선택

        Args:
            skill: 사용할 스킬
            allies: 아군 목록
            enemies: 적군 목록

        Returns:
            선택된 대상
        """
        if skill.target_type == SkillTargetType.SELF:
            return self.enemy

        elif skill.target_type == SkillTargetType.SINGLE_ALLY:
            # 단일 아군 선택 (회복 스킬 등) - 가장 HP가 낮은 아군
            alive_allies = [a for a in allies if getattr(a, 'is_alive', True)]
            if not alive_allies:
                return None
            # HP가 가장 낮은 아군 선택
            return min(alive_allies, key=lambda a: getattr(a, 'current_hp', 0))

        elif skill.target_type == SkillTargetType.ALL_ALLIES:
            return allies  # 전체 대상

        elif skill.target_type == SkillTargetType.ALL_ENEMIES:
            return enemies  # 전체 대상

        elif skill.target_type == SkillTargetType.SINGLE_ENEMY:
            # 단일 적 선택
            alive_enemies = [e for e in enemies if getattr(e, 'is_alive', True)]
            if not alive_enemies:
                return None

            # 전략에 따라 선택
            if skill.damage > 100:
                # 강력한 공격: 가장 약한 적 (마무리)
                return min(alive_enemies, key=lambda e: getattr(e, 'current_hp', 0))
            else:
                # 일반 공격: 랜덤 또는 가장 강한 적
                if random.random() < 0.7:
                    return random.choice(alive_enemies)
                else:
                    return max(alive_enemies, key=lambda e: getattr(e, 'current_hp', 0))

        elif skill.target_type == SkillTargetType.RANDOM_ENEMY:
            alive_enemies = [e for e in enemies if getattr(e, 'is_alive', True)]
            return random.choice(alive_enemies) if alive_enemies else None

        return None

    def _decide_basic_attack(self, enemies: List[Any]) -> dict:
        """
        일반 공격 결정

        Args:
            enemies: 적군 목록

        Returns:
            공격 행동 정보
        """
        alive_enemies = [e for e in enemies if getattr(e, 'is_alive', True)]

        if not alive_enemies:
            return {"type": "defend", "target": None}

        # 랜덤 대상 선택
        target = random.choice(alive_enemies)

        return {
            "type": "attack",
            "target": target
        }


class BossAI(EnemyAI):
    """
    보스 AI

    일반 적보다 더 똑똑하고 전략적
    """

    def __init__(self, enemy: Any):
        # 보스는 항상 "hard" 난이도
        super().__init__(enemy, difficulty="hard")

    def _select_skill(
        self,
        available_skills: List[EnemySkill],
        context: dict
    ) -> Optional[EnemySkill]:
        """
        보스 스킬 선택 (더 전략적)
        """
        # 페이즈별 전략
        hp_percent = context["self_hp_percent"]

        # HP 단계별 우선 스킬
        phase_skills = {
            # HP 0-30%: 필살기 우선
            "desperate": lambda s: s.damage > 100 or s.heal_amount > 50,
            # HP 30-70%: 균형잡힌 전략
            "balanced": lambda s: True,
            # HP 70-100%: 공격적 전략
            "aggressive": lambda s: s.damage > 0 or s.debuff_stats
        }

        if hp_percent < 0.3:
            phase = "desperate"
        elif hp_percent < 0.7:
            phase = "balanced"
        else:
            phase = "aggressive"

        # 페이즈에 맞는 스킬 필터링
        phase_filter = phase_skills[phase]
        filtered_skills = [s for s in available_skills if phase_filter(s)]

        if not filtered_skills:
            filtered_skills = available_skills

        # 부모 클래스의 선택 로직 사용
        return super()._select_skill(filtered_skills, context)


class SephirothAI(BossAI):
    """
    세피로스 전용 AI

    가장 강력하고 전략적인 AI
    """

    def __init__(self, enemy: Any):
        super().__init__(enemy)
        self.skill_use_multiplier = 2.5  # 스킬 사용 확률 2.5배
        self.phase = 1

    def decide_action(
        self,
        allies: List[Any],
        enemies: List[Any]
    ) -> dict:
        """
        세피로스의 행동 결정

        HP 단계별로 다른 전략 사용
        """
        hp_percent = self.enemy.current_hp / self.enemy.max_hp if self.enemy.max_hp > 0 else 0

        # 페이즈 전환
        if hp_percent < 0.3 and self.phase < 3:
            self.phase = 3
            logger.warning(f"⚠️ {self.enemy.name}의 광기가 폭발한다!")
        elif hp_percent < 0.6 and self.phase < 2:
            self.phase = 2
            logger.warning(f"⚠️ {self.enemy.name}이(가) 진지해진다...")

        # 페이즈별 강제 스킬 사용
        if self.phase == 3:
            # 페이즈 3: 절망 사용 시도
            for skill in self.enemy.skills:
                if skill.skill_id == "despair" and skill.can_use(self.enemy):
                    skill.activate_cooldown()
                    return {
                        "type": "skill",
                        "skill": skill,
                        "target": enemies
                    }

        # 일반 결정 로직
        return super().decide_action(allies, enemies)


def create_ai_for_enemy(enemy: Any) -> EnemyAI:
    """
    적에 맞는 AI 생성

    Args:
        enemy: 적 캐릭터

    Returns:
        적절한 AI 인스턴스
    """
    enemy_name = getattr(enemy, 'name', '').lower()

    # 세피로스
    if 'sephiroth' in enemy_name or '세피로스' in enemy_name:
        return SephirothAI(enemy)

    # 보스
    if 'boss' in enemy_name or '보스' in enemy_name or 'dragon' in enemy_name:
        return BossAI(enemy)

    # 일반 적
    return EnemyAI(enemy, difficulty="normal")
