"""
적 생성 시스템

층수에 따라 적절한 난이도의 적 생성
"""

from typing import List, Dict, Any
import random


class EnemyTemplate:
    """적 템플릿"""

    def __init__(
        self,
        enemy_id: str,
        name: str,
        level: int,
        hp: int,
        mp: int,
        physical_attack: int,
        physical_defense: int,
        magic_attack: int,
        magic_defense: int,
        speed: int,
        max_brv: int,  # 최대 BRV
        init_brv: int,  # 초기 BRV
        luck: int = 5,
        accuracy: int = 50,
        evasion: int = 10
    ):
        self.enemy_id = enemy_id
        self.name = name
        self.level = level
        self.hp = hp
        self.mp = mp
        self.physical_attack = physical_attack
        self.physical_defense = physical_defense
        self.magic_attack = magic_attack
        self.magic_defense = magic_defense
        self.speed = speed
        self.max_brv = max_brv
        self.init_brv = init_brv
        self.luck = luck
        self.accuracy = accuracy
        self.evasion = evasion


# 적 템플릿 데이터베이스
# ⚠️ 모든 적은 레벨 1 기준 스탯으로 작성됨
# 다른 코드에서 층수/레벨에 따라 스탯을 스케일링하여 사용
#
# 1레벨 기준 평균: HP=200, MP=40, ATK=55, DEF=45, MATK=55, MDEF=45, SPD=55, LUK=10, ACC=65, EVA=12
ENEMY_TEMPLATES = {
    # === 약한 적 (기본 잡몹) ===
    # BRV: 낮은 max_brv, 낮은 init_brv (10-15%)
    "slime": EnemyTemplate(
        "slime", "슬라임", 1,
        hp=180, mp=35,  # 마법형 - HP 약간 낮음
        physical_attack=45, physical_defense=40,
        magic_attack=65, magic_defense=55,  # 마법 특화
        speed=50,
        max_brv=800, init_brv=267,  # 낮은 BRV (2400÷3, 800÷3)
        luck=8, accuracy=62, evasion=10
    ),
    "goblin": EnemyTemplate(
        "goblin", "고블린", 1,
        hp=200, mp=35,  # 균형형
        physical_attack=60, physical_defense=45,
        magic_attack=50, magic_defense=42,
        speed=55,
        max_brv=960, init_brv=320,  # 평균 BRV (2880÷3, 960÷3)
        luck=10, accuracy=65, evasion=12
    ),
    "wolf": EnemyTemplate(
        "wolf", "늑대", 1,
        hp=220, mp=30,  # 물리형 - HP 높음
        physical_attack=65, physical_defense=50,
        magic_attack=40, magic_defense=38,
        speed=60,
        max_brv=1067, init_brv=356,  # 약간 높은 BRV (3200÷3, 1067÷3)
        luck=12, accuracy=68, evasion=15
    ),

    # === 일반 적 (중간 강도) ===
    # BRV: 중간 max_brv, 중간 init_brv (15-20%)
    "orc": EnemyTemplate(
        "orc", "오크", 1,
        hp=240, mp=45,  # 탱커형 - 높은 HP와 방어력
        physical_attack=70, physical_defense=60,
        magic_attack=35, magic_defense=40,
        speed=45,
        max_brv=1173, init_brv=391,  # 탱커 BRV (3520÷3, 1173÷3)
        luck=8, accuracy=62, evasion=6
    ),
    "skeleton": EnemyTemplate(
        "skeleton", "해골 전사", 1,
        hp=190, mp=50,  # 균형형 언데드
        physical_attack=65, physical_defense=42,
        magic_attack=48, magic_defense=50,
        speed=58,
        max_brv=1013, init_brv=338,  # 균형 BRV (3040÷3, 1013÷3)
        luck=10, accuracy=65, evasion=12
    ),
    "dark_mage": EnemyTemplate(
        "dark_mage", "다크 메이지", 1,
        hp=160, mp=80,  # 마법 특화 - 낮은 HP, 높은 MP/마법
        physical_attack=40, physical_defense=35,
        magic_attack=85, magic_defense=65,
        speed=52,
        max_brv=1333, init_brv=444,  # 높은 BRV (마법사) (4000÷3, 1333÷3)
        luck=12, accuracy=68, evasion=14
    ),

    # === 강한 적 (정예 몬스터) ===
    # BRV: 높은 max_brv, 높은 init_brv (20-25%)
    "ogre": EnemyTemplate(
        "ogre", "오우거", 1,
        hp=280, mp=50,  # 중장갑 탱커
        physical_attack=80, physical_defense=70,
        magic_attack=30, magic_defense=45,
        speed=40,
        max_brv=1493, init_brv=498,  # 높은 탱커 BRV (4480÷3, 1493÷3)
        luck=6, accuracy=60, evasion=4
    ),
    "wraith": EnemyTemplate(
        "wraith", "망령", 1,
        hp=200, mp=90,  # 마법 특화 언데드
        physical_attack=50, physical_defense=38,
        magic_attack=90, magic_defense=75,
        speed=65,
        max_brv=1600, init_brv=533,  # 매우 높은 BRV (마법) (4800÷3, 1600÷3)
        luck=14, accuracy=70, evasion=20
    ),
    "golem": EnemyTemplate(
        "golem", "골렘", 1,
        hp=320, mp=20,  # 극단적 탱커 - 매우 높은 HP/방어, 느림
        physical_attack=75, physical_defense=85,
        magic_attack=25, magic_defense=55,
        speed=30,
        max_brv=1867, init_brv=622,  # 극단적 탱커 BRV (5600÷3, 1867÷3)
        luck=5, accuracy=58, evasion=2
    ),

    # === 매우 강한 적 (위험 몬스터) ===
    # BRV: 매우 높은 max_brv, 매우 높은 init_brv (25-30%)
    "troll": EnemyTemplate(
        "troll", "트롤", 1,
        hp=300, mp=55,  # 재생 능력 탱커
        physical_attack=85, physical_defense=72,
        magic_attack=40, magic_defense=48,
        speed=48,
        max_brv=1707, init_brv=569,  # 재생 탱커 BRV (5120÷3, 1707÷3)
        luck=10, accuracy=62, evasion=8
    ),
    "vampire": EnemyTemplate(
        "vampire", "뱀파이어", 1,
        hp=250, mp=100,  # 민첩 + 마법형
        physical_attack=75, physical_defense=55,
        magic_attack=95, magic_defense=70,
        speed=75,
        max_brv=1867, init_brv=622,  # 흡혈 특화 BRV (5600÷3, 1867÷3)
        luck=18, accuracy=75, evasion=22
    ),
    "wyvern": EnemyTemplate(
        "wyvern", "와이번", 1,
        hp=280, mp=65,  # 비행 물리형 - 높은 공격/속도
        physical_attack=90, physical_defense=62,
        magic_attack=55, magic_defense=50,
        speed=70,
        max_brv=1760, init_brv=587,  # 공격형 BRV (5280÷3, 1760÷3)
        luck=14, accuracy=70, evasion=18
    ),

    # === 최상급 적 (던전 보스급) ===
    # BRV: 극도로 높은 max_brv, 매우 높은 init_brv (30-35%)
    "demon": EnemyTemplate(
        "demon", "악마", 1,
        hp=320, mp=120,  # 균형잡힌 강력한 적
        physical_attack=95, physical_defense=75,
        magic_attack=100, magic_defense=80,
        speed=65,
        max_brv=2133, init_brv=711,  # 강력한 균형 BRV (6400÷3, 2133÷3)
        luck=16, accuracy=72, evasion=16
    ),
    "dragon": EnemyTemplate(
        "dragon", "드래곤", 1,
        hp=400, mp=150,  # 최강 일반 몬스터
        physical_attack=110, physical_defense=90,
        magic_attack=105, magic_defense=85,
        speed=60,
        max_brv=2667, init_brv=889,  # 드래곤급 BRV (8000÷3, 2667÷3)
        luck=20, accuracy=75, evasion=12
    ),

    # === 보스 몬스터 ===
    # BRV: 보스급 max_brv, 높은 init_brv (35-40%)
    "boss_chimera": EnemyTemplate(
        "boss_chimera", "키메라 (보스)", 1,
        hp=500, mp=150,  # 초반 보스
        physical_attack=100, physical_defense=80,
        magic_attack=95, magic_defense=75,
        speed=68,
        max_brv=3200, init_brv=1067,  # 초반 보스 BRV (9600÷3, 3200÷3)
        luck=18, accuracy=75, evasion=15
    ),
    "boss_lich": EnemyTemplate(
        "boss_lich", "리치 (보스)", 1,
        hp=600, mp=250,  # 중반 보스 - 마법 특화
        physical_attack=90, physical_defense=70,
        magic_attack=140, magic_defense=110,
        speed=62,
        max_brv=4000, init_brv=1333,  # 중반 보스 BRV (12000÷3, 4000÷3)
        luck=22, accuracy=78, evasion=18
    ),
    "boss_dragon_king": EnemyTemplate(
        "boss_dragon_king", "드래곤 킹 (보스)", 1,
        hp=800, mp=300,  # 후반 보스
        physical_attack=130, physical_defense=105,
        magic_attack=125, magic_defense=100,
        speed=70,
        max_brv=4800, init_brv=1600,  # 후반 보스 BRV (14400÷3, 4800÷3)
        luck=25, accuracy=80, evasion=14
    ),

    # === 최종 보스 ===
    # BRV: 압도적 max_brv, 매우 높은 init_brv (40%)
    "sephiroth": EnemyTemplate(
        "sephiroth", "세피로스", 1,
        hp=1000, mp=500,  # 압도적인 스탯 (레벨 스케일링으로 더욱 강해짐)
        physical_attack=150, physical_defense=120,
        magic_attack=160, magic_defense=130,
        speed=100,
        max_brv=6400, init_brv=2133,  # 세피로스급 BRV (19200÷3, 6400÷3)
        luck=30, accuracy=90, evasion=25
    ),
}


class SimpleEnemy:
    """간단한 적 클래스 (전투용)"""

    def __init__(self, template: EnemyTemplate, level_modifier: float = 1.0):
        self.enemy_id = template.enemy_id  # 적 ID 저장 (BGM 선택용)
        self.name = template.name
        self.level = max(1, int(template.level * level_modifier))

        # 스탯 (레벨 보정)
        self.max_hp = int(template.hp * level_modifier)
        self.current_hp = self.max_hp
        self.max_mp = int(template.mp * level_modifier)
        self.current_mp = self.max_mp

        self.physical_attack = int(template.physical_attack * level_modifier)
        self.physical_defense = int(template.physical_defense * level_modifier)
        self.magic_attack = int(template.magic_attack * level_modifier)
        self.magic_defense = int(template.magic_defense * level_modifier)
        self.speed = template.speed
        self.luck = template.luck
        self.accuracy = template.accuracy
        self.evasion = template.evasion

        # BRV (템플릿에서 정의된 값을 레벨 보정)
        self.max_brv = int(template.max_brv * level_modifier)
        self.current_brv = int(template.init_brv * level_modifier)

        # 상태
        self.is_alive = True
        self.status_effects = {}
        self.wound_damage = 0

        # 스킬 (간단하게)
        self.skills = []

    def take_damage(self, damage: int) -> int:
        """데미지 받기"""
        actual_damage = min(damage, self.current_hp)
        self.current_hp -= actual_damage

        if self.current_hp <= 0:
            self.current_hp = 0
            self.is_alive = False

        return actual_damage

    def heal(self, amount: int) -> int:
        """회복"""
        actual_heal = min(amount, self.max_hp - self.current_hp)
        self.current_hp += actual_heal
        return actual_heal


class EnemyGenerator:
    """적 생성기"""

    # 적 등급별 등장 층수 정의
    ENEMY_TIERS = {
        # 약한 적 (1-3층)
        "weak": ["slime", "goblin", "wolf"],
        # 일반 적 (3-6층)
        "normal": ["orc", "skeleton", "dark_mage"],
        # 강한 적 (6-9층)
        "strong": ["ogre", "wraith", "golem"],
        # 매우 강한 적 (9-12층)
        "very_strong": ["troll", "vampire", "wyvern"],
        # 최상급 적 (12층 이상)
        "elite": ["demon", "dragon"],
    }

    @staticmethod
    def get_suitable_enemies_for_floor(floor_number: int) -> List[str]:
        """
        층수에 맞는 적 ID 리스트 반환

        Args:
            floor_number: 층 번호

        Returns:
            적합한 적 ID 리스트
        """
        suitable = []

        # 층수에 따라 등장 가능한 적 선택
        if floor_number <= 3:
            suitable.extend(EnemyGenerator.ENEMY_TIERS["weak"])
        if 2 <= floor_number <= 6:
            suitable.extend(EnemyGenerator.ENEMY_TIERS["normal"])
        if 5 <= floor_number <= 9:
            suitable.extend(EnemyGenerator.ENEMY_TIERS["strong"])
        if 8 <= floor_number <= 12:
            suitable.extend(EnemyGenerator.ENEMY_TIERS["very_strong"])
        if floor_number >= 11:
            suitable.extend(EnemyGenerator.ENEMY_TIERS["elite"])

        # 최소 1종류는 나오도록
        if not suitable:
            suitable = EnemyGenerator.ENEMY_TIERS["weak"]

        return suitable

    @staticmethod
    def generate_enemies(floor_number: int, num_enemies: int = None) -> List[SimpleEnemy]:
        """
        층수에 맞는 적 생성

        Args:
            floor_number: 층 번호
            num_enemies: 적 수 (None이면 자동)

        Returns:
            적 리스트
        """
        if num_enemies is None:
            # config에서 적 수 범위 가져오기
            from src.core.config import get_config
            config = get_config()
            min_enemies = config.get("world.dungeon.enemy_count.min_enemies", 1)
            max_enemies = config.get("world.dungeon.enemy_count.max_enemies", 4)

            # 랜덤하게 1~4마리 생성
            num_enemies = random.randint(min_enemies, max_enemies)

        # 층수에 맞는 적 ID 가져오기
        suitable_enemy_ids = EnemyGenerator.get_suitable_enemies_for_floor(floor_number)

        # 랜덤 선택
        enemies = []
        for _ in range(num_enemies):
            enemy_id = random.choice(suitable_enemy_ids)
            template = ENEMY_TEMPLATES[enemy_id]

            # 레벨 스케일링 계수 (층수에 비례)
            # 1층 = 1.0배, 2층 = 1.5배, 3층 = 2.0배, ...
            level_modifier = 1.0 + (floor_number - 1) * 0.5

            enemy = SimpleEnemy(template, level_modifier)

            # 적 타입에 맞는 스킬 추가
            try:
                from src.combat.enemy_skills import EnemySkillDatabase
                enemy.skills = EnemySkillDatabase.get_skills_for_enemy_type(template.enemy_id)
            except ImportError as e:
                # EnemySkillDatabase가 없을 경우 기본 스킬로 작동
                logger.debug(f"적 스킬 로드 실패: {e} - 기본 스킬 사용")

            enemies.append(enemy)

        return enemies

    @staticmethod
    def generate_boss(floor_number: int) -> SimpleEnemy:
        """보스 생성"""
        # 층수에 맞는 보스 선택
        if floor_number == 15:
            # 15층: 세피로스 (최종 보스)
            template = ENEMY_TEMPLATES["sephiroth"]
        elif floor_number < 15:
            template = ENEMY_TEMPLATES["boss_chimera"]
        elif floor_number < 25:
            template = ENEMY_TEMPLATES["boss_lich"]
        else:
            template = ENEMY_TEMPLATES["boss_dragon_king"]

        level_modifier = floor_number / template.level
        level_modifier = max(1.0, level_modifier)  # 최소 1배

        boss = SimpleEnemy(template, level_modifier)

        # 세피로스일 경우 스킬 추가
        if floor_number == 15:
            try:
                from src.combat.enemy_skills import EnemySkillDatabase
                boss.skills = EnemySkillDatabase.get_skills_for_enemy_type("sephiroth")
            except ImportError as e:
                # EnemySkillDatabase가 없을 경우 기본 스킬로 작동
                logger.warning(f"세피로스 스킬 로드 실패: {e} - 기본 스킬 사용")

        return boss
