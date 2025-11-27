"""
적 생성 시스템

층수에 따라 적절한 난이도의 적 생성
"""

from typing import List, Dict, Any
import random
from src.core.logger import get_logger

# 로거 설정
logger = get_logger("enemy")


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
        hp=210, mp=40,  # 속도 특화 - 낮은 HP
        physical_attack=64, physical_defense=45,
        magic_attack=56, magic_defense=42,
        speed=68,  # 높은 속도
        max_brv=840, init_brv=280,  # 속도형 BRV
        luck=15, accuracy=74, evasion=16  # 높은 회피
    ),

    # === 최상급 적 (던전 보스급) ===
    # BRV: 극도로 높은 max_brv, 매우 높은 init_brv (30-35%)
    "demon": EnemyTemplate(
        "demon", "악마", 1,
        hp=225, mp=46,  # 균형 잡힌 타입
        physical_attack=66, physical_defense=52,
        magic_attack=66, magic_defense=52,  # 물리/마법 균형
        speed=57,
        max_brv=890, init_brv=297,  # 균형 BRV
        luck=13, accuracy=69, evasion=13
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

    # === 강력 보스 (일반 몹 수준 스탯) ===
    # BRV: 일반 몹 수준으로 조정
    "boss_chimera": EnemyTemplate(
        "boss_chimera", "키메라", 1,
        hp=240, mp=45,  # 균형형 - 약간 높은 HP
        physical_attack=68, physical_defense=55,
        magic_attack=62, magic_defense=48,
        speed=58,
        max_brv=950, init_brv=317,  # 균형 BRV
        luck=13, accuracy=70, evasion=13
    ),
    "boss_lich": EnemyTemplate(
        "boss_lich", "리치", 1,
        hp=190, mp=60,  # 마법 특화 - 낮은 HP, 높은 MP
        physical_attack=50, physical_defense=42,
        magic_attack=78, magic_defense=65,  # 마법 공격/방어 특화
        speed=48,
        max_brv=800, init_brv=267,  # 마법형 BRV
        luck=15, accuracy=72, evasion=10
    ),
    "boss_dragon_king": EnemyTemplate(
        "boss_dragon_king", "드래곤 킹", 1,
        hp=250, mp=38,  # 물리 특화 - 높은 HP
        physical_attack=72, physical_defense=58,  # 물리 공격/방어 특화
        magic_attack=52, magic_defense=45,
        speed=55,
        max_brv=1000, init_brv=333,  # 물리형 BRV
        luck=12, accuracy=68, evasion=12
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

    # ============================================================
    # 새로운 적 타입 추가 (30종)
    # ============================================================

    # === 언데드 타입 (5종) ===
    "zombie": EnemyTemplate(
        "zombie", "좀비", 1,
        hp=230, mp=20,  # 높은 HP, 낮은 MP
        physical_attack=55, physical_defense=40,
        magic_attack=20, magic_defense=30,
        speed=30,  # 매우 느림
        max_brv=1040, init_brv=347,
        luck=5, accuracy=55, evasion=3
    ),
    "ghoul": EnemyTemplate(
        "ghoul", "구울", 1,
        hp=210, mp=40,  # 빠른 언데드
        physical_attack=70, physical_defense=45,
        magic_attack=35, magic_defense=40,
        speed=65,  # 빠름
        max_brv=1120, init_brv=373,
        luck=12, accuracy=68, evasion=16
    ),
    "banshee": EnemyTemplate(
        "banshee", "밴시", 1,
        hp=170, mp=90,  # 마법형 언데드
        physical_attack=40, physical_defense=35,
        magic_attack=88, magic_defense=70,
        speed=68,
        max_brv=1440, init_brv=480,
        luck=15, accuracy=72, evasion=20
    ),
    "death_knight": EnemyTemplate(
        "death_knight", "죽음의 기사", 1,
        hp=290, mp=70,  # 강력한 언데드 전사
        physical_attack=95, physical_defense=80,
        magic_attack=65, magic_defense=60,
        speed=55,
        max_brv=1680, init_brv=560,
        luck=14, accuracy=70, evasion=10
    ),
    "mummy": EnemyTemplate(
        "mummy", "미라", 1,
        hp=260, mp=60,  # 저주와 재생
        physical_attack=60, physical_defense=65,
        magic_attack=70, magic_defense=75,
        speed=35,
        max_brv=1360, init_brv=453,
        luck=8, accuracy=62, evasion=5
    ),

    # === 엘리멘탈 타입 (6종) ===
    "fire_elemental": EnemyTemplate(
        "fire_elemental", "불의 정령", 1,
        hp=180, mp=100,  # 마법 특화
        physical_attack=45, physical_defense=40,
        magic_attack=95, magic_defense=70,
        speed=60,
        max_brv=1520, init_brv=507,
        luck=12, accuracy=70, evasion=15
    ),
    "ice_elemental": EnemyTemplate(
        "ice_elemental", "얼음의 정령", 1,
        hp=175, mp=100,
        physical_attack=42, physical_defense=45,
        magic_attack=92, magic_defense=75,
        speed=55,
        max_brv=1480, init_brv=493,
        luck=10, accuracy=68, evasion=12
    ),
    "thunder_elemental": EnemyTemplate(
        "thunder_elemental", "번개의 정령", 1,
        hp=170, mp=110,
        physical_attack=40, physical_defense=38,
        magic_attack=100, magic_defense=65,
        speed=75,  # 매우 빠름
        max_brv=1600, init_brv=533,
        luck=18, accuracy=75, evasion=22
    ),
    "earth_elemental": EnemyTemplate(
        "earth_elemental", "대지의 정령", 1,
        hp=250, mp=80,  # 방어 특화
        physical_attack=65, physical_defense=90,
        magic_attack=55, magic_defense=85,
        speed=35,
        max_brv=1200, init_brv=400,
        luck=8, accuracy=62, evasion=4
    ),
    "wind_elemental": EnemyTemplate(
        "wind_elemental", "바람의 정령", 1,
        hp=160, mp=95,  # 회피 특화
        physical_attack=50, physical_defense=35,
        magic_attack=75, magic_defense=50,
        speed=85,  # 최고 속도
        max_brv=1280, init_brv=427,
        luck=20, accuracy=72, evasion=30
    ),
    "dark_elemental": EnemyTemplate(
        "dark_elemental", "어둠의 정령", 1,
        hp=190, mp=120,  # 암흑 마법
        physical_attack=50, physical_defense=45,
        magic_attack=105, magic_defense=80,
        speed=58,
        max_brv=1680, init_brv=560,
        luck=16, accuracy=70, evasion=18
    ),

    # === 야수/몬스터 타입 (6종) ===
    "bear": EnemyTemplate(
        "bear", "곰", 1,
        hp=270, mp=30,  # 강력한 물리 공격
        physical_attack=85, physical_defense=65,
        magic_attack=25, magic_defense=35,
        speed=45,
        max_brv=1360, init_brv=453,
        luck=10, accuracy=65, evasion=8
    ),
    "spider": EnemyTemplate(
        "spider", "거대 거미", 1,
        hp=190, mp=45,  # 독과 거미줄
        physical_attack=65, physical_defense=50,
        magic_attack=40, magic_defense=45,
        speed=70,
        max_brv=1040, init_brv=347,
        luck=14, accuracy=70, evasion=18
    ),
    "scorpion": EnemyTemplate(
        "scorpion", "전갈", 1,
        hp=220, mp=40,  # 독침과 방어
        physical_attack=70, physical_defense=70,
        magic_attack=30, magic_defense=50,
        speed=55,
        max_brv=1200, init_brv=400,
        luck=12, accuracy=68, evasion=14
    ),
    "basilisk": EnemyTemplate(
        "basilisk", "바실리스크", 1,
        hp=240, mp=75,  # 석화 시선
        physical_attack=72, physical_defense=60,
        magic_attack=80, magic_defense=65,
        speed=50,
        max_brv=1440, init_brv=480,
        luck=15, accuracy=72, evasion=12
    ),
    "cerberus": EnemyTemplate(
        "cerberus", "케르베로스", 1,
        hp=280, mp=60,  # 3연속 공격
        physical_attack=88, physical_defense=65,
        magic_attack=55, magic_defense=55,
        speed=68,
        max_brv=1600, init_brv=533,
        luck=16, accuracy=72, evasion=15
    ),
    "hydra": EnemyTemplate(
        "hydra", "히드라", 1,
        hp=320, mp=80,  # 재생 능력
        physical_attack=80, physical_defense=60,
        magic_attack=60, magic_defense=65,
        speed=48,
        max_brv=1760, init_brv=587,
        luck=12, accuracy=68, evasion=10
    ),

    # === 드래곤 타입 (4종) ===
    "fire_dragon": EnemyTemplate(
        "fire_dragon", "화염 드래곤", 1,
        hp=235, mp=48,  # 화염 특화 - 약간 높은 HP
        physical_attack=63, physical_defense=50,
        magic_attack=76, magic_defense=52,  # 마법 공격 특화
        speed=56,
        max_brv=930, init_brv=310,  # 화염형 BRV
        luck=14, accuracy=72, evasion=13
    ),
    "ice_dragon": EnemyTemplate(
        "ice_dragon", "빙룡", 1,
        hp=350, mp=135,  # 얼음 특화 드래곤
        physical_attack=92, physical_defense=78,
        magic_attack=108, magic_defense=75,
        speed=60,
        max_brv=2280, init_brv=760,
        luck=17, accuracy=74, evasion=12
    ),
    "poison_dragon": EnemyTemplate(
        "poison_dragon", "독 드래곤", 1,
        hp=330, mp=125,  # 독 특화 드래곤
        physical_attack=88, physical_defense=72,
        magic_attack=100, magic_defense=68,
        speed=65,
        max_brv=2160, init_brv=720,
        luck=19, accuracy=76, evasion=16
    ),
    "elder_dragon": EnemyTemplate(
        "elder_dragon", "고룡", 1,
        hp=230, mp=42,  # 방어 특화 - 약간 높은 HP/MP
        physical_attack=65, physical_defense=62,  # 높은 물리 방어
        magic_attack=58, magic_defense=58,  # 높은 마법 방어
        speed=50,
        max_brv=920, init_brv=307,  # 방어형 BRV
        luck=11, accuracy=66, evasion=11
    ),

    # === 악마/언홀리 타입 (4종) ===
    "imp": EnemyTemplate(
        "imp", "임프", 1,
        hp=150, mp=80,  # 약한 악마, 마법
        physical_attack=45, physical_defense=35,
        magic_attack=75, magic_defense=55,
        speed=72,
        max_brv=960, init_brv=320,
        luck=14, accuracy=68, evasion=20
    ),
    "succubus": EnemyTemplate(
        "succubus", "서큐버스", 1,
        hp=230, mp=110,  # 매혹과 흡혈
        physical_attack=68, physical_defense=55,
        magic_attack=98, magic_defense=75,
        speed=70,
        max_brv=1840, init_brv=613,
        luck=20, accuracy=76, evasion=22
    ),
    "balrog": EnemyTemplate(
        "balrog", "발록", 1,
        hp=220, mp=50,  # 공격 특화 - 약간 높은 MP
        physical_attack=75, physical_defense=48,  # 높은 물리 공격
        magic_attack=68, magic_defense=50,
        speed=52,
        max_brv=880, init_brv=293,  # 공격형 BRV
        luck=13, accuracy=71, evasion=12
    ),
    "archfiend": EnemyTemplate(
        "archfiend", "대악마", 1,
        hp=200, mp=55,  # 마법 공격 특화 - 높은 MP
        physical_attack=52, physical_defense=45,
        magic_attack=80, magic_defense=55,  # 높은 마법 공격
        speed=58,
        max_brv=850, init_brv=283,  # 마법 공격형 BRV
        luck=14, accuracy=73, evasion=14
    ),

    # === 기계/골렘 타입 (3종) ===
    "iron_golem": EnemyTemplate(
        "iron_golem", "강철 골렘", 1,
        hp=350, mp=30,  # 극도의 방어
        physical_attack=80, physical_defense=110,
        magic_attack=20, magic_defense=70,
        speed=25,
        max_brv=1920, init_brv=640,
        luck=5, accuracy=60, evasion=2
    ),
    "crystal_golem": EnemyTemplate(
        "crystal_golem", "수정 골렘", 1,
        hp=300, mp=50,  # 마법 반사
        physical_attack=70, physical_defense=85,
        magic_attack=60, magic_defense=120,
        speed=30,
        max_brv=1760, init_brv=587,
        luck=8, accuracy=62, evasion=5
    ),
    "ancient_automaton": EnemyTemplate(
        "ancient_automaton", "고대 자동인형", 1,
        hp=280, mp=100,  # 기계 공격
        physical_attack=90, physical_defense=75,
        magic_attack=85, magic_defense=70,
        speed=52,
        max_brv=1840, init_brv=613,
        luck=10, accuracy=70, evasion=8
    ),

    # === 보스급/특수 타입 (2종) ===
    "mimic": EnemyTemplate(
        "mimic", "미믹", 1,
        hp=200, mp=50,  # 보물상자 위장
        physical_attack=85, physical_defense=60,
        magic_attack=50, magic_defense=50,
        speed=65,
        max_brv=1440, init_brv=480,
        luck=25, accuracy=80, evasion=20  # 높은 행운과 회피
    ),
    "nightmare": EnemyTemplate(
        "nightmare", "나이트메어", 1,
        hp=270, mp=140,  # 꿈의 악마
        physical_attack=75, physical_defense=50,
        magic_attack=115, magic_defense=85,
        speed=72,
        max_brv=2080, init_brv=693,
        luck=22, accuracy=78, evasion=25
    ),
}


class SimpleEnemy:
    """간단한 적 클래스 (전투용)"""

    def __init__(self, template: EnemyTemplate, level_modifier: float = 1.0, difficulty_hp_mult: float = 1.0, difficulty_dmg_mult: float = 1.0, is_boss: bool = False, is_floor_boss: bool = False):
        self.enemy_id = template.enemy_id  # 적 ID 저장 (BGM 선택용)
        self.name = template.name
        self.level = max(1, int(template.level * level_modifier))
        self.is_floor_boss = is_floor_boss  # 5층마다 나오는 층 보스 여부
        
        # 보스 여부 확인 (enemy_id로도 확인)
        if not is_boss:
            is_boss = template.enemy_id.startswith("boss_") or template.enemy_id == "sephiroth"
        
        # ±20% 랜덤 오차 (0.8 ~ 1.2배)
        stat_variance = random.uniform(0.8, 1.2)
        
        # 보스 배율: 기본 스탯 1.7배, HP 3.5배
        boss_stat_mult = 1.7 if is_boss else 1.0
        boss_hp_mult = 3.5 if is_boss else 1.0

        # 플레이어와 유사한 레벨당 비율 기반 성장 (장비 차이 고려하여 약 1.25배 더 성장)
        # 플레이어: HP 11.5%, 공격 20%, 방어 20% → 적: HP 14.4%, 공격 25%, 방어 25%
        level = self.level
        enemy_growth_mult = 1.25  # 장비 차이 보정 (플레이어보다 25% 더 성장)
        
        # HP: 레벨당 기초 HP의 18.72% 성장 (플레이어 11.5% * 1.25 * 1.3)
        hp_growth = template.hp * 0.1872 * (level - 1)
        base_hp = (template.hp + hp_growth) * boss_hp_mult * stat_variance
        self.max_hp = int(base_hp) * difficulty_hp_mult
        self.current_hp = self.max_hp
        
        # MP: 레벨당 기초 MP의 8.125% 성장 (플레이어 5% * 1.25 * 1.3)
        mp_growth = template.mp * 0.08125 * (level - 1)
        base_mp = (template.mp + mp_growth) * boss_stat_mult * stat_variance
        self.max_mp = int(base_mp)
        self.current_mp = self.max_mp
        
        # 공격력: 레벨당 기초 공격력의 40% 성장 (더 공격적으로 강화)
        # 최종적으로 공격력을 21%로 조정 (밸런스 재조정 - 30% 추가 감소)
        attack_growth = template.physical_attack * 0.40 * (level - 1)
        base_physical_attack = (template.physical_attack + attack_growth) * boss_stat_mult * stat_variance
        self.physical_attack = int(base_physical_attack * 0.21) * difficulty_dmg_mult

        magic_attack_growth = template.magic_attack * 0.40 * (level - 1)
        base_magic_attack = (template.magic_attack + magic_attack_growth) * boss_stat_mult * stat_variance
        self.magic_attack = int(base_magic_attack * 0.21) * difficulty_dmg_mult
        
        # 방어력: 레벨당 기초 방어력의 40% 성장, 최종값 15% 증가 (플레이어 20% * 1.25 * 1.3, 최종 0.75 * 1.15 = 0.8625배)
        defense_growth = template.physical_defense * 0.40 * (level - 1)
        base_physical_defense = (template.physical_defense + defense_growth) * 0.75 * 1.15 * boss_stat_mult * stat_variance
        self.physical_defense = int(base_physical_defense)
        
        magic_defense_growth = template.magic_defense * 0.40 * (level - 1)
        base_magic_defense = (template.magic_defense + magic_defense_growth) * 0.75 * 1.15 * boss_stat_mult * stat_variance
        self.magic_defense = int(base_magic_defense)
        
        # 속도: 레벨당 기초 속도의 25% 성장 (약간 낮춰 밸런스 조정)
        # 추가로 속도를 1.5배로 조정하고, 30% 감소 적용 (1.5 * 0.7 = 1.05)
        speed_growth = template.speed * 0.25 * (level - 1)
        base_speed = (template.speed + speed_growth) * boss_stat_mult * stat_variance
        self.speed = int(base_speed * 1.5 * 0.7)
        
        # 행운, 명중, 회피는 레벨에 따라 약간 증가
        base_luck = (template.luck + (level - 1) * 0.5) * boss_stat_mult * stat_variance
        self.luck = int(base_luck)
        base_accuracy = (template.accuracy + (level - 1) * 1.0) * boss_stat_mult * stat_variance
        self.accuracy = int(base_accuracy)
        base_evasion = (template.evasion + (level - 1) * 0.5) * boss_stat_mult * stat_variance
        self.evasion = int(base_evasion)

        # BRV: 레벨당 기초 BRV의 25% 성장 (플레이어 20% * 1.25)
        # 적의 BRV는 모두 1/2로 조정
        brv_growth = template.max_brv * 0.25 * (level - 1)
        base_max_brv = (template.max_brv + brv_growth) * boss_stat_mult * stat_variance * 0.5
        self.max_brv = int(base_max_brv)
        init_brv_growth = template.init_brv * 0.25 * (level - 1)
        base_init_brv = (template.init_brv + init_brv_growth) * boss_stat_mult * stat_variance * 0.5
        self.current_brv = int(base_init_brv)

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
        "weak": ["slime", "goblin", "wolf", "zombie", "imp"],
        # 일반 적 (3-6층)
        "normal": ["orc", "skeleton", "dark_mage", "ghoul", "spider", "scorpion", "bear"],
        # 강한 적 (6-9층)
        "strong": [
            "ogre", "wraith", "golem",
            "mummy", "banshee", "fire_elemental", "ice_elemental",
            "wind_elemental", "basilisk"
        ],
        # 매우 강한 적 (9-12층)
        "very_strong": [
            "troll", "vampire", "wyvern",
            "death_knight", "thunder_elemental", "dark_elemental",
            "earth_elemental", "cerberus", "hydra", "mimic"
        ],
        # 최상급 적 (12-15층)
        "elite": [
            "demon", "dragon",
            "fire_dragon", "ice_dragon", "poison_dragon",
            "succubus", "nightmare"
        ],
        # 보스급 (15층 이상 또는 특수 조우)
        "boss": [
            "balrog", "archfiend", "elder_dragon",
            "iron_golem", "crystal_golem", "ancient_automaton"
        ],
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
        if 11 <= floor_number <= 15:
            suitable.extend(EnemyGenerator.ENEMY_TIERS["elite"])
        if floor_number >= 15:
            # 15층 이상: 보스급 적도 일반 조우로 등장 (낮은 확률)
            suitable.extend(EnemyGenerator.ENEMY_TIERS["boss"])

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

        # 난이도 시스템에서 배율 가져오기
        from src.core.difficulty import get_difficulty_system
        difficulty_system = get_difficulty_system()

        difficulty_hp_mult = 1.0
        difficulty_dmg_mult = 1.0
        if difficulty_system:
            difficulty_hp_mult = difficulty_system.get_enemy_hp_multiplier()
            difficulty_dmg_mult = difficulty_system.get_enemy_damage_multiplier()

        # 층수에 맞는 적 ID 가져오기
        suitable_enemy_ids = EnemyGenerator.get_suitable_enemies_for_floor(floor_number)

        # 랜덤 선택
        enemies = []
        for _ in range(num_enemies):
            enemy_id = random.choice(suitable_enemy_ids)
            template = ENEMY_TEMPLATES[enemy_id]

            # 레벨 스케일링 계수 (층수와 비슷하거나 조금 낮게)
            # 1층 = 0.8배, 2층 = 1.6배, 3층 = 2.4배, ... (층수 * 0.8)
            level_modifier = floor_number * 0.8

            enemy = SimpleEnemy(template, level_modifier, difficulty_hp_mult, difficulty_dmg_mult)

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
    def generate_boss(floor_number: int, is_floor_boss: bool = False) -> SimpleEnemy:
        """
        보스 생성

        Args:
            floor_number: 층 번호
            is_floor_boss: True면 5층마다 등장하는 강력한 층 보스, False면 일반 층의 보스

        Returns:
            보스 적
        """
        # 난이도 시스템에서 배율 가져오기
        from src.core.difficulty import get_difficulty_system
        difficulty_system = get_difficulty_system()

        difficulty_hp_mult = 1.0
        difficulty_dmg_mult = 1.0
        if difficulty_system:
            difficulty_hp_mult = difficulty_system.get_enemy_hp_multiplier()
            difficulty_dmg_mult = difficulty_system.get_enemy_damage_multiplier()

        # 5층마다 등장하는 특별한 층 보스 (더 강력함)
        if is_floor_boss or floor_number % 5 == 0:
            # 층수에 따라 특별한 보스 템플릿 선택
            if floor_number >= 50:
                template = ENEMY_TEMPLATES["sephiroth"]
                boss_name = "세피로스"
                boss_enemy_id = "sephiroth"
            elif floor_number >= 45:
                template = ENEMY_TEMPLATES["boss_dragon_king"]
                boss_name = "드래곤 킹"
                boss_enemy_id = "boss_dragon_king"
            elif floor_number >= 40:
                template = ENEMY_TEMPLATES["elder_dragon"]
                boss_name = "고룡"
                boss_enemy_id = "elder_dragon"
            elif floor_number >= 35:
                template = ENEMY_TEMPLATES["archfiend"]
                boss_name = "대악마"
                boss_enemy_id = "archfiend"
            elif floor_number >= 30:
                template = ENEMY_TEMPLATES["balrog"]
                boss_name = "발록"
                boss_enemy_id = "balrog"
            elif floor_number >= 25:
                template = ENEMY_TEMPLATES["boss_lich"]
                boss_name = "리치"
                boss_enemy_id = "boss_lich"
            elif floor_number >= 20:
                template = ENEMY_TEMPLATES["fire_dragon"]
                boss_name = "화염 드래곤"
                boss_enemy_id = "fire_dragon"
            elif floor_number >= 15:
                template = ENEMY_TEMPLATES["demon"]
                boss_name = "악마"
                boss_enemy_id = "demon"
            elif floor_number >= 10:
                template = ENEMY_TEMPLATES["boss_chimera"]
                boss_name = "키메라"
                boss_enemy_id = "boss_chimera"
            else:  # 5층
                template = ENEMY_TEMPLATES["wyvern"]
                boss_name = "와이번"
                boss_enemy_id = "wyvern"

            # 층 보스는 일반 보스보다 더 강력함 (2.5배 스탯, 5배 HP)
            level_modifier = floor_number * 0.8
            boss = SimpleEnemy(template, level_modifier, difficulty_hp_mult, difficulty_dmg_mult, is_boss=True, is_floor_boss=is_floor_boss)

            # 층 보스는 추가 강화 (HP 1.5배, 스탯 1.3배 추가)
            boss.max_hp = int(boss.max_hp * 1.5)
            boss.current_hp = boss.max_hp
            boss.physical_attack = int(boss.physical_attack * 1.3)
            boss.magic_attack = int(boss.magic_attack * 1.3)
            boss.physical_defense = int(boss.physical_defense * 1.2)
            boss.magic_defense = int(boss.magic_defense * 1.2)
            boss.max_brv = int(boss.max_brv * 1.3)
            boss.current_brv = int(boss.current_brv * 1.3)

            boss.name = boss_name
            boss.enemy_id = boss_enemy_id

            # 스킬 추가
            try:
                from src.combat.enemy_skills import EnemySkillDatabase
                boss.skills = EnemySkillDatabase.get_skills_for_enemy_type(boss_enemy_id)
            except ImportError:
                pass

            return boss

        # 일반 층의 보스 (일반 몹의 강화 버전)
        # 일반 보스로는 현재 층 티어보다 한 단계 낮은 티어를 사용 (너무 강한 보스 방지)
        boss_tier_map = {
            "elite": "very_strong",      # elite 티어 층에서는 very_strong 티어 보스
            "very_strong": "strong",    # very_strong 티어 층에서는 strong 티어 보스
            "strong": "normal",         # strong 티어 층에서는 normal 티어 보스
            "normal": "weak",          # normal 티어 층에서는 weak 티어 보스
            "weak": "weak"             # weak 티어 층에서는 weak 티어 보스
        }

        # 현재 층의 티어 결정
        current_tier = None
        if floor_number <= 3:
            current_tier = "weak"
        elif 2 <= floor_number <= 6:
            current_tier = "normal"
        elif 5 <= floor_number <= 9:
            current_tier = "strong"
        elif 8 <= floor_number <= 12:
            current_tier = "very_strong"
        elif 11 <= floor_number <= 15:
            current_tier = "elite"
        else:
            current_tier = "elite"  # 15층 이상

        # 일반 보스용 티어 선택 (한 단계 낮춤)
        boss_tier = boss_tier_map.get(current_tier, "weak")

        # 해당 티어의 적들 가져오기
        suitable_enemy_ids = EnemyGenerator.ENEMY_TIERS.get(boss_tier, ["slime"])
        # 보스 템플릿 제외 (boss_로 시작하거나 sephiroth 제외)
        normal_enemy_ids = [eid for eid in suitable_enemy_ids if not eid.startswith("boss_") and eid != "sephiroth"]

        # 일반 몹이 없으면 전체에서 선택 (보스 템플릿 제외)
        if not normal_enemy_ids:
            normal_enemy_ids = [eid for eid in ENEMY_TEMPLATES.keys() if not eid.startswith("boss_") and eid != "sephiroth"]

        # 랜덤으로 일반 몹 템플릿 선택
        base_enemy_id = random.choice(normal_enemy_ids)
        template = ENEMY_TEMPLATES[base_enemy_id]

        # 보스 이름 설정
        boss_name = f"{template.name} (보스)"
        boss_enemy_id = f"boss_{base_enemy_id}"

        # 레벨 스케일링 계수 (층수와 비슷하거나 조금 낮게)
        level_modifier = floor_number * 0.8

        # 보스 생성 (is_boss=True로 설정하여 1.7배 스탯, 3.5배 HP 적용)
        boss = SimpleEnemy(template, level_modifier, difficulty_hp_mult, difficulty_dmg_mult, is_boss=True)
        boss.name = boss_name
        boss.enemy_id = boss_enemy_id

        # 일반 보스는 기본 적 스킬 사용
        try:
            from src.combat.enemy_skills import EnemySkillDatabase
            boss.skills = EnemySkillDatabase.get_skills_for_enemy_type(base_enemy_id)
        except ImportError:
            pass

        return boss