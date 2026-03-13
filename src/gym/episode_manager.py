"""
에피소드 관리자 - 전투 에피소드 생성

RL 학습용 전투 에피소드를 생성합니다.
랜덤 아군 구성과 적 생성을 담당합니다.
"""

import random
from typing import List, Optional, Tuple, Any

from src.core.logger import get_logger

logger = get_logger("gym.episode_manager")


class EpisodeManager:
    """
    에피소드 (전투) 생성 관리자

    RL 학습을 위한 다양한 전투 에피소드를 생성합니다.
    아군과 적의 구성을 랜덤하게 또는 지정된 방식으로 설정합니다.
    """

    ALL_JOBS: List[str] = [
        "warrior", "archer", "assassin", "berserker", "breaker",
        "gladiator", "monk", "ninja", "rogue", "samurai", "sniper",
        "sword_saint", "archmage", "battle_mage", "spellblade", "necromancer",
        "elementalist", "dark_knight", "paladin", "dimensionist", "dragon_knight",
        "priest", "cleric", "druid", "bard", "knight",
        "time_mage", "hacker", "shaman", "alchemist", "engineer",
        "magician", "philosopher", "pirate", "vampire", "illusionist",
    ]

    # 난이도별 던전 층 범위
    DIFFICULTY_FLOOR_MAP = {
        "쉬움": (1, 3),
        "보통": (3, 7),
        "어려움": (7, 12),
        "매우 어려움": (12, 15),
    }

    def __init__(self, difficulty: str = "보통") -> None:
        """
        Args:
            difficulty: 난이도 ('쉬움', '보통', '어려움', '매우 어려움')
        """
        self.difficulty = difficulty
        floor_range = self.DIFFICULTY_FLOOR_MAP.get(difficulty, (3, 7))
        self._floor_min, self._floor_max = floor_range
        logger.debug(f"에피소드 관리자 초기화: 난이도={difficulty}, 층={floor_range}")

    def create_random_episode(self) -> Tuple[List[Any], List[Any]]:
        """
        랜덤 아군 4명과 랜덤 적 생성

        Returns:
            (allies, enemies) 튜플
        """
        # 4개의 랜덤 직업 선택 (중복 가능)
        ally_jobs = random.choices(self.ALL_JOBS, k=4)

        # 층수 랜덤 선택
        floor = random.randint(self._floor_min, self._floor_max)

        return self.create_episode(ally_jobs=ally_jobs, level=floor * 2)

    def create_episode(
        self,
        ally_jobs: List[str],
        enemy_templates: Optional[List[str]] = None,
        level: int = 10,
    ) -> Tuple[List[Any], List[Any]]:
        """
        지정된 구성으로 에피소드 생성

        Args:
            ally_jobs: 아군 직업 ID 리스트 (최대 4개)
            enemy_templates: 적 ID 리스트 (None이면 EnemyGenerator 사용)
            level: 캐릭터 레벨 (적 층수 계산에도 사용)

        Returns:
            (allies, enemies) 튜플
        """
        allies = self._create_allies(ally_jobs, level)
        enemies = self._create_enemies(enemy_templates, level)
        logger.debug(
            f"에피소드 생성: 아군 {len(allies)}명 ({[j for j in ally_jobs]}), "
            f"적 {len(enemies)}명"
        )
        return allies, enemies

    def _create_allies(self, job_ids: List[str], level: int) -> List[Any]:
        """아군 Character 인스턴스 생성"""
        # 지연 임포트 (순환 임포트 방지)
        from src.character.character import Character

        allies = []
        for job_id in job_ids[:4]:
            try:
                char = Character(
                    name=self._job_display_name(job_id),
                    character_class=job_id,
                    level=max(1, level),
                )
                allies.append(char)
            except Exception as e:
                logger.warning(f"아군 생성 실패 (job={job_id}): {e}")

        return allies

    def _create_enemies(
        self,
        enemy_templates: Optional[List[str]],
        level: int,
    ) -> List[Any]:
        """적군 생성"""
        # 레벨을 층수로 변환 (대략 레벨/2 = 층수)
        floor = max(1, level // 2)

        if enemy_templates:
            return self._create_enemies_from_templates(enemy_templates, floor)
        else:
            return self._create_enemies_from_generator(floor)

    def _create_enemies_from_generator(self, floor: int) -> List[Any]:
        """EnemyGenerator를 사용해 적 생성"""
        try:
            from src.world.enemy_generator import EnemyGenerator
            enemies = EnemyGenerator.generate_enemies(floor_number=floor)
            return enemies
        except Exception as e:
            logger.warning(f"EnemyGenerator 적 생성 실패: {e}, 폴백 사용")
            return self._create_fallback_enemies(floor)

    def _create_enemies_from_templates(
        self, templates: List[str], floor: int
    ) -> List[Any]:
        """지정된 템플릿으로 적 생성"""
        try:
            from src.world.enemy_generator import EnemyGenerator, ENEMY_TEMPLATES, SimpleEnemy

            level_modifier = floor * 0.8
            enemies = []
            for tmpl_id in templates[:4]:
                if tmpl_id not in ENEMY_TEMPLATES:
                    logger.warning(f"알 수 없는 적 템플릿: {tmpl_id}")
                    continue
                template = ENEMY_TEMPLATES[tmpl_id]
                enemy = SimpleEnemy(template, level_modifier=level_modifier)
                enemies.append(enemy)
            return enemies if enemies else self._create_fallback_enemies(floor)
        except Exception as e:
            logger.warning(f"템플릿 기반 적 생성 실패: {e}")
            return self._create_fallback_enemies(floor)

    def _create_fallback_enemies(self, floor: int) -> List[Any]:
        """최후 폴백: 기본 슬라임 적 1마리 생성"""
        try:
            from src.world.enemy_generator import ENEMY_TEMPLATES, SimpleEnemy
            level_modifier = max(0.8, floor * 0.8)
            template = ENEMY_TEMPLATES.get("slime") or list(ENEMY_TEMPLATES.values())[0]
            return [SimpleEnemy(template, level_modifier=level_modifier)]
        except Exception as e:
            logger.error(f"폴백 적 생성도 실패: {e}")
            return []

    @staticmethod
    def _job_display_name(job_id: str) -> str:
        """직업 ID를 한국어 표시명으로 변환"""
        names = {
            "warrior": "전사",
            "archer": "궁수",
            "assassin": "암살자",
            "berserker": "광전사",
            "breaker": "브레이커",
            "gladiator": "검투사",
            "monk": "무도가",
            "rogue": "도적",
            "samurai": "사무라이",
            "sniper": "저격수",
            "sword_saint": "검성",
            "archmage": "대마도사",
            "battle_mage": "배틀메이지",
            "spellblade": "마검사",
            "necromancer": "네크로맨서",
            "elementalist": "원소술사",
            "dark_knight": "암흑기사",
            "paladin": "성기사",
            "dimensionist": "차원술사",
            "dragon_knight": "용기사",
            "priest": "사제",
            "cleric": "클레릭",
            "druid": "드루이드",
            "bard": "바드",
            "knight": "기사",
            "time_mage": "시간술사",
            "hacker": "해커",
            "shaman": "무당",
            "alchemist": "연금술사",
            "engineer": "기술자",
            "magician": "마술사",
            "philosopher": "철학자",
            "pirate": "해적",
            "vampire": "뱀파이어",
            "illusionist": "환술사",
        }
        return names.get(job_id, job_id)
