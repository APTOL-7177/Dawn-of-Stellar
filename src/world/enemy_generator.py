"""
적 생성 시스템

층수에 따라 적절한 난이도의 적 생성
"""

from typing import List, Dict, Any
import random
from src.core.logger import get_logger
from src.combat.status_effects import StatusManager

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
        evasion: int = 10,
        element_resistance: dict = None  # 속성 저항/약점 {element: multiplier}
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
        # 속성 저항: 1.0 미만 = 약점(데미지 증가), 1.0 초과 = 저항(데미지 감소)
        # 예: {"fire": 2.0, "ice": 0.5} = 화염 저항 2배, 빙결 약점 2배
        self.element_resistance = element_resistance or {}


# 적 템플릿 데이터베이스
# ⚠️ 모든 적은 레벨 1 기준 스탯으로 작성됨
# 다른 코드에서 층수/레벨에 따라 스탯을 스케일링하여 사용
#
# 1레벨 기준 평균: HP=200, MP=40, ATK=55, DEF=45, MATK=55, MDEF=45, SPD=55, LUK=10, ACC=65, EVA=12
ENEMY_TEMPLATES = {
    # === 약한 적 (기본 잡몹) - 총합 ~450 ===
    # 각 적마다 물방/마방/속도가 다이나믹하게 다름
    "slime": EnemyTemplate(
        "slime", "슬라임", 1,
        hp=180, mp=50,  # 마법형
        physical_attack=42, physical_defense=30,  # 물방 낮음
        magic_attack=65, magic_defense=55,  # 마방 높음
        speed=45,
        max_brv=800, init_brv=267,
        luck=8, accuracy=62, evasion=10
    ),
    "goblin": EnemyTemplate(
        "goblin", "고블린", 1,
        hp=195, mp=40,  # 균형형
        physical_attack=58, physical_defense=48,  # 균형 방어
        magic_attack=45, magic_defense=42,
        speed=55,
        max_brv=900, init_brv=300,
        luck=10, accuracy=65, evasion=12
    ),
    "wolf": EnemyTemplate(
        "wolf", "늑대", 1,
        hp=185, mp=30,  # 민첩형
        physical_attack=60, physical_defense=35,  # 양방어 낮음
        magic_attack=35, magic_defense=30,
        speed=72,  # 빠름
        max_brv=850, init_brv=283,
        luck=12, accuracy=70, evasion=18
    ),

    # === 일반 적 (중간 강도) - 총합 ~500 ===
    "orc": EnemyTemplate(
        "orc", "오크", 1,
        hp=240, mp=40,  # 물리 탱커
        physical_attack=65, physical_defense=70,  # 물방 높음
        magic_attack=30, magic_defense=35,  # 마방 낮음
        speed=38,  # 느림
        max_brv=1000, init_brv=333,
        luck=8, accuracy=62, evasion=5
    ),
    "skeleton": EnemyTemplate(
        "skeleton", "해골 전사", 1,
        hp=200, mp=45,  # 균형형
        physical_attack=62, physical_defense=50,
        magic_attack=48, magic_defense=45,
        speed=55,
        max_brv=950, init_brv=317,
        luck=10, accuracy=65, evasion=12
    ),
    "dark_mage": EnemyTemplate(
        "dark_mage", "다크 메이지", 1,
        hp=165, mp=75,  # 마법형
        physical_attack=38, physical_defense=28,  # 물방 매우 낮음
        magic_attack=82, magic_defense=68,  # 마방 높음
        speed=52,
        max_brv=1100, init_brv=367,
        luck=12, accuracy=68, evasion=14
    ),

    # === 강한 적 (정예 몬스터) - 총합 ~550 ===
    "ogre": EnemyTemplate(
        "ogre", "오우거", 1,
        hp=270, mp=40,  # 물리 탱커
        physical_attack=75, physical_defense=78,  # 물방 매우 높음
        magic_attack=28, magic_defense=35,  # 마방 낮음
        speed=32,  # 느림
        max_brv=1200, init_brv=400,
        luck=6, accuracy=60, evasion=4
    ),
    "wraith": EnemyTemplate(
        "wraith", "망령", 1,
        hp=185, mp=85,  # 마법형
        physical_attack=45, physical_defense=30,  # 물방 낮음
        magic_attack=85, magic_defense=72,  # 마방 높음
        speed=62,
        max_brv=1300, init_brv=433,
        luck=14, accuracy=70, evasion=20
    ),
    "golem": EnemyTemplate(
        "golem", "골렘", 1,
        hp=310, mp=25,  # 극단적 물리 탱커
        physical_attack=68, physical_defense=90,  # 물방 극도로 높음
        magic_attack=22, magic_defense=40,  # 마방 낮음
        speed=25,  # 매우 느림
        max_brv=1400, init_brv=467,
        luck=5, accuracy=55, evasion=2
    ),

    # === 매우 강한 적 (위험 몬스터) - 총합 ~620 ===
    "troll": EnemyTemplate(
        "troll", "트롤", 1,
        hp=290, mp=50,  # 물리형 재생 탱커
        physical_attack=80, physical_defense=75,  # 물방 높음
        magic_attack=35, magic_defense=42,  # 마방 낮음
        speed=42,
        max_brv=1350, init_brv=450,
        luck=10, accuracy=62, evasion=8
    ),
    "vampire": EnemyTemplate(
        "vampire", "흡혈귀", 1,
        hp=235, mp=90,  # 민첩 마법형
        physical_attack=68, physical_defense=45,  # 물방 중간
        magic_attack=88, magic_defense=65,  # 마방 높음
        speed=78,  # 빠름
        max_brv=1400, init_brv=467,
        luck=18, accuracy=75, evasion=24
    ),
    "wyvern": EnemyTemplate(
        "wyvern", "와이번", 1,
        hp=215, mp=45,  # 극단적 민첩형
        physical_attack=65, physical_defense=38,  # 양방어 낮음
        magic_attack=55, magic_defense=35,
        speed=85,  # 매우 빠름
        max_brv=950, init_brv=317,
        luck=16, accuracy=76, evasion=28  # 높은 회피
    ),

    # === 최상급 적 (던전 보스급) - 모두 유사한 파워 레벨 (~700) ===
    "demon": EnemyTemplate(
        "demon", "악마", 1,
        hp=280, mp=75,  # 균형 잡힌 타입
        physical_attack=72, physical_defense=60,
        magic_attack=72, magic_defense=60,  # 물리/마법 균형
        speed=62,
        max_brv=1100, init_brv=367,
        luck=14, accuracy=70, evasion=14
    ),
    "dragon": EnemyTemplate(
        "dragon", "드래곤", 1,
        hp=320, mp=90,  # 가장 강한 일반 몬스터
        physical_attack=68, physical_defense=75,
        magic_attack=55, magic_defense=70,
        speed=58,
        max_brv=1250, init_brv=417,
        luck=16, accuracy=72, evasion=10
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

    # === 최종 보스 (20층) - 물리형 (소폭 강화 +15%) ===
    # 7분 30초 제한 - 스킬 계수로 위협적
    "sephiroth": EnemyTemplate(
        "sephiroth", "세피로스", 1,
        hp=600, mp=750,
        physical_attack=99, physical_defense=140,
        magic_attack=63, magic_defense=99,
        speed=155,
        max_brv=1800, init_brv=900,
        luck=26, accuracy=120, evasion=24
    ),

    # === 진 최종 보스 (30층) - 마법형 (소폭 강화 +15%) ===
    # 4분 제한 - 시간은 짧지만 마법 계수 높은 스킬로 승부
    "abel_cain": EnemyTemplate(
        "abel_cain", "닥터 아벨 카인", 1,
        hp=404, mp=750,
        physical_attack=60, physical_defense=90,
        magic_attack=118, magic_defense=146,
        speed=138,
        max_brv=1435, init_brv=718,
        luck=30, accuracy=125, evasion=21
    ),

    # ============================================================
    # 새로운 적 타입 추가 (30종)
    # ============================================================

    # === 언데드 타입 (5종) - 약한적/일반적 등급 (~450-500) ===
    "zombie": EnemyTemplate(
        "zombie", "좀비", 1,
        hp=220, mp=20,  # 물리 탱커 - 느림
        physical_attack=52, physical_defense=55,  # 물방 높음
        magic_attack=18, magic_defense=25,  # 마방 낮음
        speed=28,  # 매우 느림
        max_brv=900, init_brv=300,
        luck=5, accuracy=52, evasion=2
    ),
    "ghoul": EnemyTemplate(
        "ghoul", "구울", 1,
        hp=195, mp=40,  # 민첩형 언데드
        physical_attack=65, physical_defense=38,  # 물방 중간
        magic_attack=32, magic_defense=35,  # 마방 낮음
        speed=70,  # 빠름
        max_brv=950, init_brv=317,
        luck=12, accuracy=68, evasion=18
    ),
    "banshee": EnemyTemplate(
        "banshee", "밴시", 1,
        hp=165, mp=85,  # 마법형 언데드 (강한 적)
        physical_attack=38, physical_defense=28,  # 물방 낮음
        magic_attack=82, magic_defense=68,  # 마방 높음
        speed=62,
        max_brv=1200, init_brv=400,
        luck=15, accuracy=72, evasion=20
    ),
    "death_knight": EnemyTemplate(
        "death_knight", "죽음의 기사", 1,
        hp=275, mp=60,  # 중장갑 물리형 (매우 강한 적)
        physical_attack=85, physical_defense=82,  # 물방 매우 높음
        magic_attack=55, magic_defense=50,  # 마방 중간
        speed=48,
        max_brv=1350, init_brv=450,
        luck=13, accuracy=68, evasion=8
    ),
    "mummy": EnemyTemplate(
        "mummy", "미라", 1,
        hp=250, mp=55,  # 균형 탱커 (강한 적)
        physical_attack=55, physical_defense=62,  # 양방어 높음
        magic_attack=62, magic_defense=70,  # 마방 특히 높음
        speed=32,  # 느림
        max_brv=1150, init_brv=383,
        luck=8, accuracy=60, evasion=4
    ),

    # === 엘리멘탈 타입 (6종) - 강한적/매우강한적 등급 (~550-620) ===
    "fire_elemental": EnemyTemplate(
        "fire_elemental", "불의 정령", 1,
        hp=175, mp=90,  # 공격형 마법
        physical_attack=42, physical_defense=32,  # 물방 낮음
        magic_attack=88, magic_defense=55,  # 마방 중간
        speed=68,  # 빠름
        max_brv=1200, init_brv=400,
        luck=12, accuracy=70, evasion=16
    ),
    "ice_elemental": EnemyTemplate(
        "ice_elemental", "얼음의 정령", 1,
        hp=185, mp=88,  # 방어형 마법
        physical_attack=40, physical_defense=50,  # 물방 높음
        magic_attack=82, magic_defense=72,  # 마방 높음
        speed=48,  # 느림
        max_brv=1150, init_brv=383,
        luck=10, accuracy=66, evasion=10
    ),
    "thunder_elemental": EnemyTemplate(
        "thunder_elemental", "번개의 정령", 1,
        hp=160, mp=95,  # 극단적 속공 마법
        physical_attack=38, physical_defense=25,  # 물방 매우 낮음
        magic_attack=92, magic_defense=48,  # 마방 낮음
        speed=88,  # 최고 속도
        max_brv=1250, init_brv=417,
        luck=18, accuracy=76, evasion=28
    ),
    "earth_elemental": EnemyTemplate(
        "earth_elemental", "대지의 정령", 1,
        hp=260, mp=70,  # 극단적 탱커
        physical_attack=58, physical_defense=85,  # 물방 극도로 높음
        magic_attack=48, magic_defense=78,  # 마방 높음
        speed=28,  # 매우 느림
        max_brv=1100, init_brv=367,
        luck=6, accuracy=58, evasion=3
    ),
    "wind_elemental": EnemyTemplate(
        "wind_elemental", "바람의 정령", 1,
        hp=155, mp=85,  # 극단적 민첩형
        physical_attack=48, physical_defense=28,  # 물방 낮음
        magic_attack=72, magic_defense=42,  # 마방 낮음
        speed=95,  # 극단적 속도
        max_brv=1000, init_brv=333,
        luck=22, accuracy=74, evasion=35  # 극단적 회피
    ),
    "dark_elemental": EnemyTemplate(
        "dark_elemental", "어둠의 정령", 1,
        hp=180, mp=100,  # 균형 마법형 (매우 강한 적)
        physical_attack=45, physical_defense=38,
        magic_attack=95, magic_defense=70,
        speed=58,
        max_brv=1350, init_brv=450,
        luck=16, accuracy=70, evasion=18
    ),

    # === 야수/몬스터 타입 (6종) - 일반적/강한적 등급 (~500-550) ===
    "bear": EnemyTemplate(
        "bear", "곰", 1,
        hp=255, mp=28,  # 물리 파워형
        physical_attack=78, physical_defense=68,  # 물방 높음
        magic_attack=22, magic_defense=30,  # 마방 낮음
        speed=38,  # 느림
        max_brv=1100, init_brv=367,
        luck=8, accuracy=62, evasion=5
    ),
    "spider": EnemyTemplate(
        "spider", "거대 거미", 1,
        hp=185, mp=45,  # 민첩 독 공격
        physical_attack=62, physical_defense=42,  # 물방 중간
        magic_attack=38, magic_defense=40,
        speed=75,  # 빠름
        max_brv=950, init_brv=317,
        luck=14, accuracy=72, evasion=22
    ),
    "scorpion": EnemyTemplate(
        "scorpion", "전갈", 1,
        hp=215, mp=38,  # 물리 방어형
        physical_attack=65, physical_defense=72,  # 물방 높음
        magic_attack=28, magic_defense=45,  # 마방 중간
        speed=52,
        max_brv=1000, init_brv=333,
        luck=11, accuracy=66, evasion=12
    ),
    "basilisk": EnemyTemplate(
        "basilisk", "바실리스크", 1,
        hp=230, mp=70,  # 균형 마법형 (강한 적)
        physical_attack=68, physical_defense=55,
        magic_attack=75, magic_defense=62,
        speed=48,
        max_brv=1200, init_brv=400,
        luck=14, accuracy=70, evasion=10
    ),
    "cerberus": EnemyTemplate(
        "cerberus", "케르베로스", 1,
        hp=265, mp=55,  # 빠른 물리 공격형 (매우 강한 적)
        physical_attack=82, physical_defense=58,  # 물방 중간
        magic_attack=50, magic_defense=48,  # 마방 낮음
        speed=72,  # 빠름
        max_brv=1300, init_brv=433,
        luck=15, accuracy=72, evasion=16
    ),
    "hydra": EnemyTemplate(
        "hydra", "히드라", 1,
        hp=300, mp=70,  # 재생 탱커 (매우 강한 적)
        physical_attack=72, physical_defense=65,  # 균형 방어
        magic_attack=55, magic_defense=60,
        speed=42,  # 느림
        max_brv=1400, init_brv=467,
        luck=11, accuracy=66, evasion=8
    ),

    # === 드래곤 타입 (4종) - 모두 유사한 파워 레벨 (~700) ===
    "fire_dragon": EnemyTemplate(
        "fire_dragon", "화염 드래곤", 1,
        hp=280, mp=80,  # 화염 특화 - 공격적
        physical_attack=72, physical_defense=55,
        magic_attack=95, magic_defense=58,  # 마법 공격 특화
        speed=62,
        max_brv=1200, init_brv=400,
        luck=14, accuracy=72, evasion=13
    ),
    "ice_dragon": EnemyTemplate(
        "ice_dragon", "빙룡", 1,
        hp=290, mp=85,  # 얼음 특화 - 방어적
        physical_attack=68, physical_defense=70,
        magic_attack=88, magic_defense=72,  # 마법 방어 특화
        speed=55,
        max_brv=1150, init_brv=383,
        luck=15, accuracy=70, evasion=10
    ),
    "poison_dragon": EnemyTemplate(
        "poison_dragon", "독 드래곤", 1,
        hp=270, mp=90,  # 독 특화 - 밸런스형
        physical_attack=70, physical_defense=58,
        magic_attack=85, magic_defense=60,
        speed=68,  # 빠른 속도
        max_brv=1180, init_brv=393,
        luck=17, accuracy=74, evasion=15
    ),
    "elder_dragon": EnemyTemplate(
        "elder_dragon", "고룡", 1,
        hp=300, mp=75,  # 방어 특화 - 탱키형
        physical_attack=65, physical_defense=80,
        magic_attack=60, magic_defense=78,  # 높은 방어력
        speed=52,
        max_brv=1100, init_brv=367,
        luck=12, accuracy=68, evasion=8
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
        hp=260, mp=95,  # 매혹과 흡혈
        physical_attack=65, physical_defense=52,
        magic_attack=90, magic_defense=68,
        speed=68,
        max_brv=1300, init_brv=433,
        luck=18, accuracy=74, evasion=20
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

    # === 기계/골렘 타입 (3종) - 보스급 등급 (~750) ===
    "iron_golem": EnemyTemplate(
        "iron_golem", "강철 골렘", 1,
        hp=320, mp=30,  # 극단적 물리 탱커
        physical_attack=75, physical_defense=98,  # 물방 극도로 높음
        magic_attack=18, magic_defense=55,  # 마방 낮음
        speed=22,  # 매우 느림
        max_brv=1500, init_brv=500,
        luck=5, accuracy=55, evasion=2
    ),
    "crystal_golem": EnemyTemplate(
        "crystal_golem", "수정 골렘", 1,
        hp=285, mp=55,  # 극단적 마법 탱커
        physical_attack=65, physical_defense=70,  # 물방 높음
        magic_attack=55, magic_defense=105,  # 마방 극도로 높음
        speed=28,  # 느림
        max_brv=1400, init_brv=467,
        luck=8, accuracy=58, evasion=4
    ),
    "ancient_automaton": EnemyTemplate(
        "ancient_automaton", "고대 자동인형", 1,
        hp=270, mp=85,  # 균형 공격형
        physical_attack=82, physical_defense=65,  # 균형 방어
        magic_attack=78, magic_defense=62,
        speed=55,  # 중간 속도
        max_brv=1450, init_brv=483,
        luck=10, accuracy=68, evasion=8
    ),

    # === 보스급/특수 타입 (2종) - 매우 강한적 등급 (~620) ===
    "mimic": EnemyTemplate(
        "mimic", "미믹", 1,
        hp=195, mp=48,  # 빠른 서프라이즈 공격
        physical_attack=78, physical_defense=52,  # 물방 중간
        magic_attack=45, magic_defense=45,  # 마방 중간
        speed=72,  # 빠름
        max_brv=1150, init_brv=383,
        luck=25, accuracy=78, evasion=22  # 높은 행운과 회피
    ),
    "nightmare": EnemyTemplate(
        "nightmare", "나이트메어", 1,
        hp=255, mp=100,  # 꿈의 악마
        physical_attack=68, physical_defense=48,
        magic_attack=95, magic_defense=72,
        speed=70,
        max_brv=1350, init_brv=450,
        luck=19, accuracy=75, evasion=22
    ),

    # === 자연/야수 타입 추가 (5종) ===
    "dire_wolf": EnemyTemplate(
        "dire_wolf", "다이어 울프", 1,
        hp=175, mp=20,  # 빠른 야수, 팩 헌터
        physical_attack=72, physical_defense=40,
        magic_attack=15, magic_defense=35,
        speed=78,
        max_brv=1000, init_brv=333,
        luck=15, accuracy=75, evasion=25
    ),
    "thunderbird": EnemyTemplate(
        "thunderbird", "썬더버드", 1,
        hp=210, mp=90,  # 전기 속성 새
        physical_attack=55, physical_defense=42,
        magic_attack=88, magic_defense=65,
        speed=85,
        max_brv=1200, init_brv=400,
        luck=18, accuracy=82, evasion=30
    ),
    "manticore": EnemyTemplate(
        "manticore", "만티코어", 1,
        hp=280, mp=60,  # 독 꼬리 환상수
        physical_attack=85, physical_defense=58,
        magic_attack=55, magic_defense=50,
        speed=62,
        max_brv=1400, init_brv=467,
        luck=14, accuracy=72, evasion=15
    ),
    "treant": EnemyTemplate(
        "treant", "트렌트", 1,
        hp=350, mp=80,  # 자연의 수호자
        physical_attack=70, physical_defense=85,
        magic_attack=60, magic_defense=70,
        speed=25,  # 매우 느림
        max_brv=1600, init_brv=533,
        luck=8, accuracy=55, evasion=2
    ),
    "chimera": EnemyTemplate(
        "chimera", "키메라", 1,
        hp=320, mp=75,  # 사자+염소+뱀 합성수
        physical_attack=90, physical_defense=62,
        magic_attack=75, magic_defense=55,
        speed=58,
        max_brv=1500, init_brv=500,
        luck=13, accuracy=70, evasion=12
    ),

    # === 수중/해양 타입 (4종) ===
    "sea_serpent": EnemyTemplate(
        "sea_serpent", "바다뱀", 1,
        hp=240, mp=65,  # 물 속성 뱀
        physical_attack=75, physical_defense=50,
        magic_attack=70, magic_defense=60,
        speed=68,
        max_brv=1250, init_brv=417,
        luck=12, accuracy=70, evasion=20
    ),
    "kraken": EnemyTemplate(
        "kraken", "크라켄", 1,
        hp=380, mp=100,  # 거대 문어
        physical_attack=95, physical_defense=70,
        magic_attack=80, magic_defense=65,
        speed=35,
        max_brv=1800, init_brv=600,
        luck=10, accuracy=68, evasion=8
    ),
    "siren": EnemyTemplate(
        "siren", "사이렌", 1,
        hp=195, mp=110,  # 매혹의 노래 사용
        physical_attack=45, physical_defense=40,
        magic_attack=95, magic_defense=75,
        speed=70,
        max_brv=1100, init_brv=367,
        luck=20, accuracy=80, evasion=22
    ),
    "merfolk_warrior": EnemyTemplate(
        "merfolk_warrior", "머포크 전사", 1,
        hp=220, mp=45,  # 수중 전사
        physical_attack=78, physical_defense=55,
        magic_attack=50, magic_defense=50,
        speed=65,
        max_brv=1150, init_brv=383,
        luck=11, accuracy=72, evasion=18
    ),

    # === 확장 언데드 타입 (4종) ===
    "bone_dragon": EnemyTemplate(
        "bone_dragon", "해골 드래곤", 1,
        hp=340, mp=80,  # 언데드 드래곤
        physical_attack=88, physical_defense=75,
        magic_attack=70, magic_defense=68,
        speed=45,
        max_brv=1700, init_brv=567,
        luck=10, accuracy=65, evasion=5
    ),
    "revenant": EnemyTemplate(
        "revenant", "레버넌트", 1,
        hp=230, mp=55,  # 복수심에 불타는 망령
        physical_attack=80, physical_defense=52,
        magic_attack=65, magic_defense=58,
        speed=60,
        max_brv=1200, init_brv=400,
        luck=15, accuracy=75, evasion=18
    ),
    "dullahan": EnemyTemplate(
        "dullahan", "듀라한", 1,
        hp=275, mp=50,  # 머리없는 기사
        physical_attack=92, physical_defense=68,
        magic_attack=45, magic_defense=55,
        speed=55,
        max_brv=1350, init_brv=450,
        luck=16, accuracy=78, evasion=12
    ),
    "lich_king": EnemyTemplate(
        "lich_king", "리치 킹", 1,
        hp=300, mp=150,  # 최상위 언데드 마법사
        physical_attack=50, physical_defense=55,
        magic_attack=110, magic_defense=95,
        speed=50,
        max_brv=1550, init_brv=517,
        luck=22, accuracy=85, evasion=15
    ),

    # === 곤충/절지류 타입 (4종) ===
    "giant_centipede": EnemyTemplate(
        "giant_centipede", "거대 지네", 1,
        hp=185, mp=30,  # 독 공격 다단히트
        physical_attack=68, physical_defense=48,
        magic_attack=35, magic_defense=40,
        speed=72,
        max_brv=1050, init_brv=350,
        luck=12, accuracy=70, evasion=22
    ),
    "queen_bee": EnemyTemplate(
        "queen_bee", "여왕벌", 1,
        hp=200, mp=60,  # 소환/버프 특화
        physical_attack=55, physical_defense=45,
        magic_attack=75, magic_defense=60,
        speed=68,
        max_brv=1100, init_brv=367,
        luck=14, accuracy=72, evasion=25
    ),
    "death_beetle": EnemyTemplate(
        "death_beetle", "죽음의 딱정벌레", 1,
        hp=250, mp=40,  # 높은 방어, 저주 속성
        physical_attack=72, physical_defense=80,
        magic_attack=55, magic_defense=65,
        speed=35,
        max_brv=1250, init_brv=417,
        luck=8, accuracy=60, evasion=5
    ),
    "plague_moth": EnemyTemplate(
        "plague_moth", "역병 나방", 1,
        hp=165, mp=70,  # 상태이상 전문
        physical_attack=40, physical_defense=35,
        magic_attack=80, magic_defense=58,
        speed=75,
        max_brv=950, init_brv=317,
        luck=18, accuracy=68, evasion=28
    ),

    # === 인간형 타입 (4종) ===
    "dark_knight": EnemyTemplate(
        "dark_knight", "암흑 기사", 1,
        hp=270, mp=55,  # HP 소모 강공격
        physical_attack=95, physical_defense=70,
        magic_attack=50, magic_defense=55,
        speed=48,
        max_brv=1400, init_brv=467,
        luck=12, accuracy=75, evasion=10
    ),
    "battle_mage": EnemyTemplate(
        "battle_mage", "배틀 메이지", 1,
        hp=215, mp=100,  # 물/마 균형
        physical_attack=65, physical_defense=50,
        magic_attack=85, magic_defense=70,
        speed=58,
        max_brv=1200, init_brv=400,
        luck=15, accuracy=78, evasion=15
    ),
    "assassin": EnemyTemplate(
        "assassin", "암살자", 1,
        hp=180, mp=45,  # 크리티컬 특화
        physical_attack=88, physical_defense=38,
        magic_attack=40, magic_defense=45,
        speed=90,
        max_brv=1000, init_brv=333,
        luck=28, accuracy=92, evasion=35
    ),
    "berserker": EnemyTemplate(
        "berserker", "광전사", 1,
        hp=295, mp=25,  # HP 떨어질수록 강해짐
        physical_attack=100, physical_defense=45,
        magic_attack=25, magic_defense=40,
        speed=55,
        max_brv=1500, init_brv=500,
        luck=10, accuracy=68, evasion=8
    ),

    # === 그림자/암흑 타입 (4종) ===
    "shadow_stalker": EnemyTemplate(
        "shadow_stalker", "그림자 추적자", 1,
        hp=190, mp=55,  # 회피 특화
        physical_attack=75, physical_defense=42,
        magic_attack=60, magic_defense=50,
        speed=82,
        max_brv=1050, init_brv=350,
        luck=22, accuracy=80, evasion=38
    ),
    "void_walker": EnemyTemplate(
        "void_walker", "공허의 보행자", 1,
        hp=225, mp=85,  # 차원 마법
        physical_attack=55, physical_defense=50,
        magic_attack=90, magic_defense=75,
        speed=65,
        max_brv=1200, init_brv=400,
        luck=18, accuracy=75, evasion=25
    ),
    "nightmare_lord": EnemyTemplate(
        "nightmare_lord", "악몽의 군주", 1,
        hp=285, mp=110,  # 공포/수면 특화
        physical_attack=65, physical_defense=55,
        magic_attack=100, magic_defense=80,
        speed=60,
        max_brv=1400, init_brv=467,
        luck=20, accuracy=78, evasion=20
    ),
    "abyss_demon": EnemyTemplate(
        "abyss_demon", "심연의 마귀", 1,
        hp=330, mp=90,  # 최상급 암흑
        physical_attack=88, physical_defense=65,
        magic_attack=95, magic_defense=72,
        speed=52,
        max_brv=1600, init_brv=533,
        luck=16, accuracy=72, evasion=15
    ),

    # === Tier 1 - 약한 적 (1-3층) ===
    "mushroom": EnemyTemplate("mushroom", "독버섯", 1, hp=210, mp=30, physical_attack=22, physical_defense=37, magic_attack=22, magic_defense=32, speed=21, max_brv=700, init_brv=233, luck=6, accuracy=55, evasion=8),
    "bat": EnemyTemplate("bat", "박쥐", 1, hp=72, mp=25, physical_attack=52, physical_defense=10, magic_attack=18, magic_defense=12, speed=97, max_brv=650, init_brv=217, luck=7, accuracy=60, evasion=25),
    "rat_swarm": EnemyTemplate("rat_swarm", "쥐떼", 1, hp=136, mp=20, physical_attack=62, physical_defense=10, magic_attack=10, magic_defense=10, speed=66, max_brv=680, init_brv=227, luck=6, accuracy=58, evasion=18),
    "fire_sprite": EnemyTemplate("fire_sprite", "화염 요정", 1, hp=75, mp=60, physical_attack=10, physical_defense=10, magic_attack=105, magic_defense=60, speed=57, max_brv=750, init_brv=250, luck=8, accuracy=65, evasion=20),
    "ice_fairy": EnemyTemplate("ice_fairy", "얼음 요정", 1, hp=75, mp=60, physical_attack=10, physical_defense=10, magic_attack=102, magic_defense=62, speed=55, max_brv=720, init_brv=240, luck=8, accuracy=63, evasion=22),

    # === Tier 2 - 일반 적 (3-6층) ===
    "lizardman": EnemyTemplate("lizardman", "리자드맨", 1, hp=364, mp=35, physical_attack=40, physical_defense=102, magic_attack=11, magic_defense=25, speed=29, max_brv=950, init_brv=317, luck=7, accuracy=60, evasion=8),
    "harpy": EnemyTemplate("harpy", "하피", 1, hp=140, mp=55, physical_attack=22, physical_defense=17, magic_attack=84, magic_defense=24, speed=68, max_brv=900, init_brv=300, luck=9, accuracy=68, evasion=22),
    "shadow_imp": EnemyTemplate("shadow_imp", "그림자 임프", 1, hp=135, mp=65, physical_attack=11, physical_defense=12, magic_attack=93, magic_defense=66, speed=55, max_brv=850, init_brv=283, luck=10, accuracy=65, evasion=20),
    "frost_wolf": EnemyTemplate("frost_wolf", "서리 늑대", 1, hp=132, mp=30, physical_attack=63, physical_defense=21, magic_attack=21, magic_defense=15, speed=90, max_brv=920, init_brv=307, luck=8, accuracy=64, evasion=15),
    "flame_hound": EnemyTemplate("flame_hound", "화염 사냥개", 1, hp=178, mp=35, physical_attack=93, physical_defense=15, magic_attack=14, magic_defense=11, speed=74, max_brv=930, init_brv=310, luck=8, accuracy=65, evasion=14),
    "sand_worm": EnemyTemplate("sand_worm", "모래벌레", 1, hp=450, mp=20, physical_attack=24, physical_defense=112, magic_attack=10, magic_defense=36, speed=15, max_brv=1050, init_brv=350, luck=5, accuracy=55, evasion=3),
    "thunder_hawk": EnemyTemplate("thunder_hawk", "번개 매", 1, hp=102, mp=45, physical_attack=57, physical_defense=15, magic_attack=33, magic_defense=20, speed=108, max_brv=880, init_brv=293, luck=10, accuracy=72, evasion=28),
    "aqua_slime": EnemyTemplate("aqua_slime", "물 슬라임", 1, hp=260, mp=55, physical_attack=19, physical_defense=26, magic_attack=42, magic_defense=90, speed=30, max_brv=850, init_brv=283, luck=7, accuracy=58, evasion=12),

    # === Tier 3 - 강한 적 (6-9층) ===
    "gargoyle": EnemyTemplate("gargoyle", "가고일", 1, hp=392, mp=40, physical_attack=40, physical_defense=120, magic_attack=18, magic_defense=44, speed=29, max_brv=1100, init_brv=367, luck=8, accuracy=60, evasion=8),
    "spectre": EnemyTemplate("spectre", "망령체", 1, hp=150, mp=80, physical_attack=10, physical_defense=11, magic_attack=112, magic_defense=84, speed=47, max_brv=1000, init_brv=333, luck=12, accuracy=68, evasion=25),
    "lava_golem": EnemyTemplate("lava_golem", "용암 골렘", 1, hp=525, mp=30, physical_attack=31, physical_defense=127, magic_attack=24, magic_defense=58, speed=15, max_brv=1200, init_brv=400, luck=6, accuracy=55, evasion=3),
    "frost_giant": EnemyTemplate("frost_giant", "서리 거인", 1, hp=510, mp=35, physical_attack=72, physical_defense=94, magic_attack=20, magic_defense=49, speed=15, max_brv=1150, init_brv=383, luck=7, accuracy=56, evasion=5),
    "storm_drake": EnemyTemplate("storm_drake", "폭풍 드레이크", 1, hp=232, mp=60, physical_attack=78, physical_defense=30, magic_attack=72, magic_defense=27, speed=60, max_brv=1100, init_brv=367, luck=10, accuracy=68, evasion=15),
    "dark_priestess": EnemyTemplate("dark_priestess", "암흑 사제", 1, hp=165, mp=90, physical_attack=10, physical_defense=13, magic_attack=117, magic_defense=86, speed=42, max_brv=1050, init_brv=350, luck=11, accuracy=70, evasion=12),
    "iron_beetle": EnemyTemplate("iron_beetle", "철 딱정벌레", 1, hp=465, mp=20, physical_attack=27, physical_defense=135, magic_attack=10, magic_defense=43, speed=17, max_brv=1080, init_brv=360, luck=6, accuracy=58, evasion=5),
    "toxic_hydra": EnemyTemplate("toxic_hydra", "독 히드라", 1, hp=495, mp=50, physical_attack=58, physical_defense=74, magic_attack=26, magic_defense=52, speed=19, max_brv=1150, init_brv=383, luck=9, accuracy=62, evasion=8),
    "phoenix_chick": EnemyTemplate("phoenix_chick", "어린 불사조", 1, hp=161, mp=70, physical_attack=20, physical_defense=17, magic_attack=104, magic_defense=35, speed=60, max_brv=1000, init_brv=333, luck=12, accuracy=70, evasion=20),

    # === Tier 4 - 매우 강한 적 (9-12층) ===
    "chaos_knight": EnemyTemplate("chaos_knight", "혼돈의 기사", 1, hp=400, mp=55, physical_attack=97, physical_defense=63, magic_attack=20, magic_defense=33, speed=44, max_brv=1200, init_brv=400, luck=12, accuracy=70, evasion=10),
    "frost_wyrm": EnemyTemplate("frost_wyrm", "서리 비룡", 1, hp=510, mp=70, physical_attack=65, physical_defense=87, magic_attack=34, magic_defense=66, speed=25, max_brv=1250, init_brv=417, luck=13, accuracy=72, evasion=12),
    "thunder_dragon": EnemyTemplate("thunder_dragon", "뇌룡", 1, hp=264, mp=75, physical_attack=74, physical_defense=31, magic_attack=86, magic_defense=30, speed=63, max_brv=1200, init_brv=400, luck=14, accuracy=74, evasion=14),
    "plague_bearer": EnemyTemplate("plague_bearer", "역병 전파자", 1, hp=210, mp=85, physical_attack=13, physical_defense=18, magic_attack=112, magic_defense=78, speed=39, max_brv=1100, init_brv=367, luck=11, accuracy=68, evasion=8),
    "crystal_guardian": EnemyTemplate("crystal_guardian", "수정 수호자", 1, hp=540, mp=60, physical_attack=24, physical_defense=127, magic_attack=27, magic_defense=116, speed=19, max_brv=1300, init_brv=433, luck=10, accuracy=62, evasion=5),
    "shadow_assassin": EnemyTemplate("shadow_assassin", "그림자 암살자", 1, hp=204, mp=50, physical_attack=120, physical_defense=16, magic_attack=12, magic_defense=14, speed=90, max_brv=1100, init_brv=367, luck=15, accuracy=78, evasion=28),
    "infernal_mage": EnemyTemplate("infernal_mage", "지옥 마법사", 1, hp=195, mp=100, physical_attack=10, physical_defense=15, magic_attack=123, magic_defense=84, speed=45, max_brv=1150, init_brv=383, luck=12, accuracy=72, evasion=12),
    "water_elemental": EnemyTemplate("water_elemental", "물의 정령", 1, hp=351, mp=80, physical_attack=20, physical_defense=37, magic_attack=49, magic_defense=112, speed=33, max_brv=1100, init_brv=367, luck=10, accuracy=65, evasion=15),
    "storm_giant": EnemyTemplate("storm_giant", "폭풍 거인", 1, hp=570, mp=50, physical_attack=75, physical_defense=97, magic_attack=27, magic_defense=55, speed=17, max_brv=1350, init_brv=450, luck=10, accuracy=60, evasion=5),

    # === Tier 5 - 최상급 적 (12-15층) ===
    "ancient_lich": EnemyTemplate("ancient_lich", "고대 리치", 1, hp=232, mp=120, physical_attack=12, physical_defense=20, magic_attack=127, magic_defense=96, speed=45, max_brv=1250, init_brv=417, luck=15, accuracy=75, evasion=15),
    "chaos_dragon": EnemyTemplate("chaos_dragon", "혼돈의 용", 1, hp=304, mp=90, physical_attack=90, physical_defense=38, magic_attack=84, magic_defense=35, speed=57, max_brv=1400, init_brv=467, luck=16, accuracy=75, evasion=12),
    "celestial_guardian": EnemyTemplate("celestial_guardian", "천상의 수호자", 1, hp=525, mp=80, physical_attack=27, physical_defense=120, magic_attack=29, magic_defense=123, speed=24, max_brv=1350, init_brv=450, luck=14, accuracy=72, evasion=8),
    "abyssal_horror": EnemyTemplate("abyssal_horror", "심연의 공포", 1, hp=289, mp=95, physical_attack=108, physical_defense=22, magic_attack=27, magic_defense=24, speed=60, max_brv=1300, init_brv=433, luck=15, accuracy=73, evasion=12),
    "volcanic_titan": EnemyTemplate("volcanic_titan", "화산 타이탄", 1, hp=600, mp=50, physical_attack=80, physical_defense=110, magic_attack=30, magic_defense=49, speed=15, max_brv=1450, init_brv=483, luck=10, accuracy=62, evasion=3),
    "frost_phoenix": EnemyTemplate("frost_phoenix", "서리 불사조", 1, hp=210, mp=90, physical_attack=22, physical_defense=22, magic_attack=116, magic_defense=42, speed=66, max_brv=1250, init_brv=417, luck=16, accuracy=76, evasion=22),
    "void_beast": EnemyTemplate("void_beast", "공허의 야수", 1, hp=297, mp=60, physical_attack=120, physical_defense=24, magic_attack=19, magic_defense=20, speed=69, max_brv=1350, init_brv=450, luck=13, accuracy=72, evasion=15),
    "tempest_serpent": EnemyTemplate("tempest_serpent", "폭풍 뱀", 1, hp=174, mp=75, physical_attack=66, physical_defense=25, magic_attack=43, magic_defense=31, speed=97, max_brv=1200, init_brv=400, luck=14, accuracy=74, evasion=18),

    # === Tier 6 - 보스급 적 (15+층) ===
    "demon_lord": EnemyTemplate("demon_lord", "마왕", 1, hp=336, mp=120, physical_attack=96, physical_defense=41, magic_attack=98, magic_defense=38, speed=57, max_brv=1500, init_brv=500, luck=18, accuracy=78, evasion=15),
    "elder_lich": EnemyTemplate("elder_lich", "상위 리치", 1, hp=262, mp=150, physical_attack=13, physical_defense=22, magic_attack=135, magic_defense=102, speed=42, max_brv=1400, init_brv=467, luck=18, accuracy=80, evasion=12),
    "storm_colossus": EnemyTemplate("storm_colossus", "폭풍의 거상", 1, hp=675, mp=80, physical_attack=82, physical_defense=108, magic_attack=32, magic_defense=66, speed=19, max_brv=1550, init_brv=517, luck=14, accuracy=65, evasion=5),
    "primordial_dragon": EnemyTemplate("primordial_dragon", "시조룡", 1, hp=384, mp=100, physical_attack=93, physical_defense=42, magic_attack=90, magic_defense=39, speed=60, max_brv=1600, init_brv=533, luck=18, accuracy=80, evasion=12),

    # === legendary 티어 (18-24층) ===
    "hell_knight": EnemyTemplate("hell_knight", "지옥 기사", 1, hp=475, mp=70, physical_attack=105, physical_defense=64, magic_attack=18, magic_defense=33, speed=44, max_brv=1400, init_brv=467, luck=15, accuracy=75, evasion=12),
    "blood_witch": EnemyTemplate("blood_witch", "피의 마녀", 1, hp=210, mp=110, physical_attack=10, physical_defense=15, magic_attack=127, magic_defense=90, speed=47, max_brv=1200, init_brv=400, luck=16, accuracy=76, evasion=15),
    "shadow_dragon": EnemyTemplate("shadow_dragon", "그림자 용", 1, hp=320, mp=85, physical_attack=86, physical_defense=37, magic_attack=84, magic_defense=35, speed=57, max_brv=1450, init_brv=483, luck=16, accuracy=76, evasion=14),
    "arcane_golem": EnemyTemplate("arcane_golem", "비전 골렘", 1, hp=630, mp=60, physical_attack=29, physical_defense=132, magic_attack=24, magic_defense=118, speed=17, max_brv=1500, init_brv=500, luck=10, accuracy=60, evasion=3),
    "death_priest": EnemyTemplate("death_priest", "죽음의 사제", 1, hp=217, mp=100, physical_attack=11, physical_defense=18, magic_attack=123, magic_defense=93, speed=45, max_brv=1250, init_brv=417, luck=14, accuracy=72, evasion=12),
    "flame_titan": EnemyTemplate("flame_titan", "화염 타이탄", 1, hp=645, mp=55, physical_attack=82, physical_defense=105, magic_attack=29, magic_defense=49, speed=16, max_brv=1500, init_brv=500, luck=11, accuracy=62, evasion=4),
    "ice_wraith": EnemyTemplate("ice_wraith", "빙결 망령", 1, hp=189, mp=90, physical_attack=18, physical_defense=17, magic_attack=116, magic_defense=41, speed=60, max_brv=1200, init_brv=400, luck=14, accuracy=72, evasion=20),
    "thunder_lord": EnemyTemplate("thunder_lord", "뇌신", 1, hp=280, mp=90, physical_attack=78, physical_defense=30, magic_attack=96, magic_defense=35, speed=65, max_brv=1350, init_brv=450, luck=15, accuracy=75, evasion=16),
    "corrupted_angel": EnemyTemplate("corrupted_angel", "타락 천사", 1, hp=306, mp=95, physical_attack=69, physical_defense=32, magic_attack=27, magic_defense=104, speed=60, max_brv=1300, init_brv=433, luck=16, accuracy=76, evasion=18),
    "venom_drake": EnemyTemplate("venom_drake", "독룡", 1, hp=450, mp=65, physical_attack=94, physical_defense=55, magic_attack=22, magic_defense=30, speed=44, max_brv=1350, init_brv=450, luck=14, accuracy=70, evasion=12),
    "storm_harpy": EnemyTemplate("storm_harpy", "폭풍 하피", 1, hp=168, mp=75, physical_attack=60, physical_defense=20, magic_attack=43, magic_defense=30, speed=105, max_brv=1200, init_brv=400, luck=16, accuracy=78, evasion=25),
    "bone_colossus": EnemyTemplate("bone_colossus", "해골 거상", 1, hp=675, mp=40, physical_attack=36, physical_defense=127, magic_attack=15, magic_defense=58, speed=15, max_brv=1550, init_brv=517, luck=10, accuracy=58, evasion=3),
    "cursed_samurai": EnemyTemplate("cursed_samurai", "저주받은 사무라이", 1, hp=240, mp=55, physical_attack=114, physical_defense=30, magic_attack=20, magic_defense=22, speed=74, max_brv=1300, init_brv=433, luck=15, accuracy=80, evasion=18),
    "magma_serpent": EnemyTemplate("magma_serpent", "용암 뱀", 1, hp=248, mp=70, physical_attack=74, physical_defense=28, magic_attack=86, magic_defense=30, speed=57, max_brv=1250, init_brv=417, luck=13, accuracy=72, evasion=14),
    "void_sentinel": EnemyTemplate("void_sentinel", "공허의 파수꾼", 1, hp=532, mp=75, physical_attack=44, physical_defense=112, magic_attack=24, magic_defense=56, speed=29, max_brv=1400, init_brv=467, luck=14, accuracy=68, evasion=8),

    # === mythic 티어 (24+층) ===
    "world_serpent": EnemyTemplate("world_serpent", "세계뱀", 1, hp=720, mp=100, physical_attack=80, physical_defense=101, magic_attack=39, magic_defense=77, speed=27, max_brv=1600, init_brv=533, luck=18, accuracy=80, evasion=14),
    "fallen_seraph": EnemyTemplate("fallen_seraph", "타락한 세라핌", 1, hp=315, mp=120, physical_attack=19, physical_defense=27, magic_attack=132, magic_defense=98, speed=57, max_brv=1550, init_brv=517, luck=18, accuracy=82, evasion=20),
    "titan_king": EnemyTemplate("titan_king", "타이탄 왕", 1, hp=780, mp=70, physical_attack=39, physical_defense=127, magic_attack=22, magic_defense=79, speed=19, max_brv=1700, init_brv=567, luck=14, accuracy=68, evasion=5),
    "lich_emperor": EnemyTemplate("lich_emperor", "리치 황제", 1, hp=285, mp=150, physical_attack=13, physical_defense=22, magic_attack=138, magic_defense=105, speed=47, max_brv=1500, init_brv=500, luck=20, accuracy=82, evasion=15),
    "nightmare_king": EnemyTemplate("nightmare_king", "악몽의 왕", 1, hp=352, mp=100, physical_attack=90, physical_defense=35, magic_attack=96, magic_defense=39, speed=57, max_brv=1550, init_brv=517, luck=18, accuracy=78, evasion=16),
    "elemental_lord": EnemyTemplate("elemental_lord", "정령왕", 1, hp=280, mp=130, physical_attack=24, physical_defense=27, magic_attack=130, magic_defense=46, speed=57, max_brv=1500, init_brv=500, luck=18, accuracy=80, evasion=14),
    "doom_bringer": EnemyTemplate("doom_bringer", "파멸의 전령", 1, hp=391, mp=80, physical_attack=131, physical_defense=28, magic_attack=22, magic_defense=24, speed=69, max_brv=1600, init_brv=533, luck=17, accuracy=78, evasion=12),
    "celestial_dragon": EnemyTemplate("celestial_dragon", "천룡", 1, hp=400, mp=110, physical_attack=98, physical_defense=42, magic_attack=96, magic_defense=41, speed=60, max_brv=1650, init_brv=550, luck=19, accuracy=82, evasion=14),
    "abyssal_king": EnemyTemplate("abyssal_king", "심연의 왕", 1, hp=587, mp=100, physical_attack=110, physical_defense=63, magic_attack=31, magic_defense=40, speed=44, max_brv=1600, init_brv=533, luck=18, accuracy=78, evasion=12),
    "chrono_guardian": EnemyTemplate("chrono_guardian", "시간의 수호자", 1, hp=342, mp=120, physical_attack=63, physical_defense=42, magic_attack=29, magic_defense=116, speed=68, max_brv=1450, init_brv=483, luck=18, accuracy=80, evasion=18),
    "infernal_dragon": EnemyTemplate("infernal_dragon", "지옥룡", 1, hp=416, mp=95, physical_attack=131, physical_defense=30, magic_attack=26, magic_defense=26, speed=66, max_brv=1650, init_brv=550, luck=17, accuracy=78, evasion=12),
    "divine_beast": EnemyTemplate("divine_beast", "신수", 1, hp=585, mp=100, physical_attack=37, physical_defense=54, magic_attack=54, magic_defense=112, speed=43, max_brv=1550, init_brv=517, luck=18, accuracy=80, evasion=15),
    "shadow_emperor": EnemyTemplate("shadow_emperor", "그림자 황제", 1, hp=322, mp=110, physical_attack=21, physical_defense=29, magic_attack=123, magic_defense=90, speed=52, max_brv=1500, init_brv=500, luck=19, accuracy=80, evasion=16),
    "runic_titan": EnemyTemplate("runic_titan", "룬 타이탄", 1, hp=750, mp=80, physical_attack=38, physical_defense=132, magic_attack=27, magic_defense=94, speed=16, max_brv=1700, init_brv=567, luck=12, accuracy=65, evasion=3),
    "eternal_phoenix": EnemyTemplate("eternal_phoenix", "영원의 불사조", 1, hp=280, mp=110, physical_attack=27, physical_defense=27, magic_attack=123, magic_defense=44, speed=68, max_brv=1500, init_brv=500, luck=19, accuracy=82, evasion=20),
}


class SimpleEnemy:
    """간단한 적 클래스 (전투용)"""

    def __init__(self, template: EnemyTemplate, level_modifier: float = 1.0, difficulty_hp_mult: float = 1.0, difficulty_dmg_mult: float = 1.0, is_boss: bool = False, is_floor_boss: bool = False):
        import uuid
        self.id = str(uuid.uuid4())[:8]  # 멀티플레이 동기화용 고유 ID
        self.enemy_id = template.enemy_id  # 적 ID 저장 (BGM 선택용)
        self.name = template.name
        self.level = max(1, int(template.level * level_modifier))
        self.is_floor_boss = is_floor_boss  # 5층마다 나오는 층 보스 여부

        # 보스 여부 확인 (enemy_id로도 확인)
        if not is_boss:
            is_boss = template.enemy_id.startswith("boss_") or template.enemy_id == "sephiroth"
        self.is_boss = is_boss  # 인스턴스 속성으로 저장
        self.is_enemy = True  # 툴팁에서 적 판별용
        
        # ±20% 랜덤 오차 (0.8 ~ 1.2배)
        stat_variance = random.uniform(0.8, 1.2)
        
        # 보스 배율: 기본 스탯 1.445배 (15% 너프), HP 3.5배
        boss_stat_mult = 1.8 if is_boss else 1.0
        boss_hp_mult = 3.5 if is_boss else 1.0

        # 플레이어와 유사한 레벨당 비율 기반 성장 (장비 차이 고려하여 약 1.25배 더 성장)
        # 플레이어: HP 11.5%, 공격 20%, 방어 20% → 적: HP 14.4%, 공격 25%, 방어 25%
        level = self.level
        enemy_growth_mult = 1.25  # 장비 차이 보정 (플레이어보다 25% 더 성장)
        
        # HP: 레벨당 기초 HP의 22.425% 성장 (새 목표 150%의 1.3배)
        hp_growth = template.hp * 0.22425 * (level - 1)
        base_hp = (template.hp + hp_growth) * boss_hp_mult * stat_variance
        self.max_hp = int(base_hp) * difficulty_hp_mult
        self.current_hp = self.max_hp
        
        # MP: 레벨당 기초 MP의 9.75% 성장
        mp_growth = template.mp * 0.0975 * (level - 1)
        base_mp = (template.mp + mp_growth) * boss_stat_mult * stat_variance
        self.max_mp = int(base_mp)
        self.current_mp = self.max_mp
        
        # 공격력: 레벨당 기초 공격력의 22.5% 성장 (기존 40%에서 감소)
        # 최종 배율 0.8 (소폭 강화)
        attack_growth = template.physical_attack * 0.225 * (level - 1)
        base_physical_attack = (template.physical_attack + attack_growth) * boss_stat_mult * stat_variance
        self.physical_attack = int(base_physical_attack * 1.0) * difficulty_dmg_mult

        magic_attack_growth = template.magic_attack * 0.225 * (level - 1)
        base_magic_attack = (template.magic_attack + magic_attack_growth) * boss_stat_mult * stat_variance
        self.magic_attack = int(base_magic_attack * 1.0) * difficulty_dmg_mult
        
        # 방어력: 레벨당 기초 방어력의 68% 성장 (기존 40%에서 대폭 증가), 최종값 2/3배
        defense_growth = template.physical_defense * 0.68 * (level - 1)
        base_physical_defense = (template.physical_defense + defense_growth) * boss_stat_mult * stat_variance
        self.physical_defense = int(base_physical_defense * 0.4)

        magic_defense_growth = template.magic_defense * 0.68 * (level - 1)
        base_magic_defense = (template.magic_defense + magic_defense_growth) * boss_stat_mult * stat_variance
        self.magic_defense = int(base_magic_defense * 0.4)
        
        # 속도: 레벨당 기초 속도의 25% 성장 (약간 낮춰 밸런스 조정)
        # 추가로 속도를 1.5배로 조정하고, 30% 감소 적용 (1.5 * 0.7 = 1.05)
        speed_growth = template.speed * 0.312 * (level - 1)
        base_speed = (template.speed + speed_growth) * boss_stat_mult * stat_variance
        self.speed = int(base_speed)
        
        # 행운, 명중, 회피는 레벨에 따라 약간 증가
        base_luck = (template.luck + (level - 1) * 0.1) * boss_stat_mult * stat_variance
        self.luck = int(base_luck)
        base_accuracy = (template.accuracy + (level - 1) * 1.0) * boss_stat_mult * stat_variance
        self.accuracy = int(base_accuracy)
        base_evasion = (template.evasion + (level - 1) * 0.5) * boss_stat_mult * stat_variance
        self.evasion = int(base_evasion)

        # BRV: 레벨당 기초 BRV의 40% 성장 (기존 28.6%에서 증가), 1/4로 감소 후 1.6배
        brv_growth = template.max_brv * 0.40 * (level - 1)
        base_max_brv = (template.max_brv + brv_growth) * boss_stat_mult * stat_variance
        # 일반 적은 max_brv x0.6, 보스는 원본 유지
        max_brv_mult = 1.0 if self.enemy_id in ["sephiroth", "abel_cain"] else 0.6
        self.max_brv = int(base_max_brv * 0.25 * 1.6 * max_brv_mult)

        init_brv_growth = template.init_brv * 0.50 * (level - 1)
        full_init_brv = (template.init_brv + init_brv_growth) * boss_stat_mult * stat_variance

        # init_brv 배율: 보스는 1.0, 일반 적은 1.2 (기존 2.0에서 하향하여 BREAK 유발 완화)
        init_brv_mult = 1.2
        if self.enemy_id in ["sephiroth", "abel_cain"]:
            init_brv_mult = 1.0

        self.init_brv = int(full_init_brv * 0.25 * init_brv_mult)
        
        # 전투 시작 시 current_brv는 init_brv 그대로 사용
        self.current_brv = self.init_brv

        # 속성 저항/약점 시스템
        # 값 < 1.0 = 약점 (데미지 증가), 값 > 1.0 = 저항 (데미지 감소)
        self.element_resistance = self._get_element_resistance(template.enemy_id)

        # 상태
        self.is_alive = True
        self.status_manager = StatusManager(owner_name=self.name, owner=self)
        self.status_effects = self.status_manager.status_effects  # 하위 호환성
        self.wound_damage = 0

        # 스킬 (간단하게)
        self.skills = []

    def _get_element_resistance(self, enemy_id: str) -> dict:
        """적 타입별 속성 저항/약점 반환"""
        # 값 설명: < 1.0 = 약점(데미지 증가), > 1.0 = 저항(데미지 감소)
        # 예: 0.5 = 2배 데미지(약점), 2.0 = 0.5배 데미지(저항)
        ELEMENT_RESISTANCES = {
            # === 기본 몬스터 ===
            "slime": {"fire": 0.7, "ice": 1.3, "lightning": 0.7, "water": 1.5},  # 물에 강함, 불/전기에 약함
            "goblin": {},  # 일반
            "wolf": {"fire": 0.8, "ice": 1.2},  # 불에 약함
            "zombie": {"fire": 0.6, "holy": 0.5, "dark": 1.5},  # 불/신성에 약함, 암흑 저항
            "imp": {"holy": 0.6, "fire": 1.3, "dark": 1.3},  # 화염/암흑 저항, 신성 약점
            
            # === 일반 적 ===
            "orc": {},  # 일반
            "skeleton": {"holy": 0.5, "dark": 1.5, "fire": 0.8},  # 신성/불에 약함, 암흑 저항
            "dark_mage": {"holy": 0.6, "dark": 1.5},  # 신성 약점, 암흑 저항
            "ghoul": {"holy": 0.5, "dark": 1.3, "fire": 0.7},  # 신성/불에 약함
            
            # === 강한 적 ===
            "ogre": {},  # 일반
            "wraith": {"holy": 0.4, "dark": 2.0, "fire": 1.3, "ice": 1.3},  # 신성 초약점, 암흑 면역
            "golem": {"lightning": 0.7, "water": 0.7, "fire": 1.3},  # 전기/물에 약함, 화염 저항
            "troll": {"fire": 0.5, "ice": 1.2},  # 화염 초약점 (재생 방해)
            "vampire": {"holy": 0.5, "fire": 0.7, "dark": 1.5},  # 신성/불에 약함, 암흑 저항
            "wyvern": {"ice": 0.7, "lightning": 0.8, "earth": 1.3},  # 빙결/전기 약점
            
            # === 언데드 ===
            "banshee": {"holy": 0.5, "dark": 1.5},  # 신성 약점, 암흑 저항
            "death_knight": {"holy": 0.6, "dark": 1.4, "fire": 0.8},  # 신성/불에 약함
            "mummy": {"fire": 0.4, "holy": 0.6, "water": 1.3},  # 화염 초약점, 물 저항
            
            # === 정령 타입 (핵심) ===
            "fire_elemental": {"fire": 2.5, "ice": 0.3, "water": 0.5},  # 화염 면역, 빙결/물 초약점
            "ice_elemental": {"ice": 2.5, "fire": 0.3, "lightning": 0.8},  # 빙결 면역, 화염 초약점
            "thunder_elemental": {"lightning": 2.5, "earth": 0.3, "water": 1.5},  # 전기 면역, 대지 초약점
            "earth_elemental": {"earth": 2.5, "wind": 0.3, "lightning": 1.5},  # 대지 면역, 바람 초약점
            "wind_elemental": {"wind": 2.5, "earth": 0.3, "ice": 0.8},  # 바람 면역, 대지 초약점
            "dark_elemental": {"dark": 2.5, "holy": 0.3, "fire": 1.2},  # 암흑 면역, 신성 초약점
            
            # === 야수 타입 ===
            "bear": {"fire": 0.8, "ice": 1.2},
            "spider": {"fire": 0.6, "ice": 1.2},  # 화염 약점
            "scorpion": {"ice": 0.7, "water": 0.8},  # 빙결/물 약점
            "basilisk": {"ice": 0.7, "holy": 0.8},
            "cerberus": {"fire": 2.0, "ice": 0.5, "holy": 0.7},  # 화염 저항, 빙결/신성 약점
            "hydra": {"fire": 0.4, "ice": 1.3},  # 화염 초약점 (재생 방해)
            
            # === 드래곤 타입 ===
            "dragon": {"fire": 1.5, "ice": 1.5, "lightning": 1.3},  # 원소 저항
            "fire_dragon": {"fire": 3.0, "ice": 0.4, "water": 0.6},  # 화염 면역, 빙결/물 초약점
            "ice_dragon": {"ice": 3.0, "fire": 0.4, "lightning": 0.8},  # 빙결 면역, 화염 초약점
            "poison_dragon": {"earth": 1.5, "holy": 0.7, "wind": 0.8},
            "elder_dragon": {"fire": 1.5, "ice": 1.5, "lightning": 1.5, "holy": 0.8},  # 원소 저항, 신성에만 약함
            
            # === 악마 타입 ===
            "demon": {"holy": 0.5, "dark": 1.8, "fire": 1.3},
            "succubus": {"holy": 0.6, "dark": 1.5},
            "balrog": {"fire": 2.5, "ice": 0.4, "holy": 0.6},  # 화염 면역, 빙결/신성 약점
            "archfiend": {"holy": 0.4, "dark": 2.0, "fire": 1.5},  # 신성 초약점, 암흑/화염 저항
            
            # === 기계/골렘 ===
            "iron_golem": {"lightning": 0.5, "water": 0.6, "fire": 1.3, "ice": 1.3},  # 전기/물 약점
            "crystal_golem": {"earth": 0.6, "dark": 1.5, "holy": 1.5},  # 대지 약점, 빛/암흑 저항
            "ancient_automaton": {"lightning": 0.6, "water": 0.7},
            
            # === 특수 ===
            "mimic": {},  # 일반
            "nightmare": {"holy": 0.5, "dark": 1.5, "fire": 0.8},
            
            # === 신규 자연/야수 ===
            "dire_wolf": {"fire": 0.7, "ice": 1.2},
            "thunderbird": {"lightning": 2.0, "earth": 0.5, "wind": 1.5},  # 전기 저항, 대지 약점
            "manticore": {"ice": 0.8, "fire": 1.2},
            "treant": {"fire": 0.3, "ice": 0.8, "water": 1.5, "earth": 1.5},  # 화염 초약점
            "chimera": {"ice": 0.8, "holy": 0.8},
            
            # === 신규 수중/해양 ===
            "sea_serpent": {"lightning": 0.5, "ice": 0.8, "water": 2.0, "fire": 1.3},  # 전기 약점, 물 저항
            "kraken": {"lightning": 0.4, "fire": 1.5, "water": 2.0},  # 전기 초약점
            "siren": {"dark": 0.7, "holy": 1.3},
            "merfolk_warrior": {"lightning": 0.6, "water": 1.5, "fire": 1.2},
            
            # === 신규 언데드 ===
            "bone_dragon": {"holy": 0.4, "dark": 1.8, "fire": 0.7},
            "revenant": {"holy": 0.5, "dark": 1.5, "fire": 0.8},
            "dullahan": {"holy": 0.5, "dark": 1.4},
            "lich_king": {"holy": 0.3, "dark": 2.0, "fire": 0.7, "ice": 1.5},  # 신성 초약점, 빙결 마법 사용
            
            # === 신규 곤충 ===
            "giant_centipede": {"fire": 0.6, "ice": 0.8},
            "queen_bee": {"fire": 0.5, "ice": 0.8, "wind": 1.3},
            "death_beetle": {"fire": 0.7, "holy": 0.8},
            "plague_moth": {"fire": 0.4, "wind": 0.7},  # 화염/바람 약점
            
            # === 신규 인간형 ===
            "dark_knight": {"holy": 0.6, "dark": 1.4},
            "battle_mage": {},  # 균형
            "assassin": {"holy": 0.8},
            "berserker": {"ice": 0.8},  # 냉정함에 약함
            
            # === 신규 그림자/암흑 ===
            "shadow_stalker": {"holy": 0.5, "dark": 1.8, "fire": 0.8},
            "void_walker": {"holy": 0.4, "dark": 2.0},
            "nightmare_lord": {"holy": 0.4, "dark": 2.0, "fire": 0.8},
            "abyss_demon": {"holy": 0.3, "dark": 2.5, "fire": 1.3},  # 신성 초약점, 암흑 면역
            
            # === 보스 ===
            "boss_chimera": {"ice": 0.8, "holy": 0.8},
            "boss_lich": {"holy": 0.4, "dark": 1.8, "fire": 0.7},
            "boss_dragon_king": {"holy": 0.7},  # 약간의 신성 약점만
            "sephiroth": {"holy": 0.8},  # 미미한 약점
            "abel_cain": {"dark": 0.8, "holy": 0.8},  # 양면성

            # === Tier 1 - 약한 적 ===
            "mushroom": {"earth": 1.5, "fire": 0.5, "ice": 0.7},
            "bat": {"dark": 1.5, "holy": 0.5, "wind": 1.2},
            "rat_swarm": {"fire": 0.6, "ice": 0.8},
            "fire_sprite": {"fire": 2.5, "ice": 0.3, "water": 0.5},
            "ice_fairy": {"ice": 2.5, "fire": 0.3, "lightning": 0.7},

            # === Tier 2 - 일반 적 ===
            "lizardman": {"earth": 1.5, "ice": 0.6, "fire": 1.2},
            "harpy": {"wind": 1.5, "lightning": 0.5, "ice": 0.7, "earth": 1.3},
            "shadow_imp": {"dark": 1.8, "holy": 0.4, "fire": 0.8},
            "frost_wolf": {"ice": 2.0, "fire": 0.4, "water": 1.3},
            "flame_hound": {"fire": 2.0, "ice": 0.4, "water": 0.5},
            "sand_worm": {"earth": 2.0, "water": 0.4, "ice": 0.6},
            "thunder_hawk": {"lightning": 1.8, "earth": 0.5, "wind": 1.5},
            "aqua_slime": {"water": 2.0, "lightning": 0.3, "fire": 0.8, "ice": 1.5},

            # === Tier 3 - 강한 적 ===
            "gargoyle": {"earth": 1.8, "holy": 0.5, "lightning": 0.6},
            "spectre": {"dark": 1.5, "holy": 0.3, "fire": 0.7},
            "lava_golem": {"fire": 2.5, "ice": 0.3, "water": 0.4, "earth": 1.5},
            "frost_giant": {"ice": 2.0, "fire": 0.4, "lightning": 0.7},
            "storm_drake": {"lightning": 1.8, "wind": 1.5, "earth": 0.5, "ice": 0.6},
            "dark_priestess": {"dark": 2.0, "holy": 0.3, "fire": 0.8},
            "iron_beetle": {"earth": 2.0, "lightning": 0.5, "fire": 0.6, "water": 1.3},
            "toxic_hydra": {"water": 1.5, "fire": 0.5, "ice": 0.6, "lightning": 0.7},
            "phoenix_chick": {"fire": 2.0, "holy": 1.5, "ice": 0.4, "water": 0.5, "dark": 0.6},

            # === Tier 4 - 매우 강한 적 ===
            "chaos_knight": {"dark": 1.8, "holy": 0.4, "lightning": 0.7},
            "frost_wyrm": {"ice": 2.0, "fire": 0.4, "water": 1.3, "lightning": 0.6},
            "thunder_dragon": {"lightning": 2.0, "earth": 0.4, "water": 0.6, "wind": 1.5},
            "plague_bearer": {"dark": 1.8, "holy": 0.4, "fire": 0.5},
            "crystal_guardian": {"holy": 1.8, "ice": 1.5, "dark": 0.4, "earth": 0.6},
            "shadow_assassin": {"dark": 1.8, "holy": 0.4, "fire": 0.7},
            "infernal_mage": {"fire": 2.0, "dark": 1.5, "ice": 0.4, "water": 0.5},
            "water_elemental": {"water": 2.5, "lightning": 0.3, "fire": 0.8, "ice": 1.5},
            "storm_giant": {"lightning": 1.5, "wind": 1.5, "earth": 0.5, "ice": 0.6},

            # === Tier 5 - 최상급 적 ===
            "ancient_lich": {"dark": 2.0, "ice": 1.5, "holy": 0.3, "fire": 0.5},
            "chaos_dragon": {"dark": 1.5, "fire": 1.5, "holy": 0.4, "ice": 0.5},
            "celestial_guardian": {"holy": 2.0, "lightning": 1.5, "dark": 0.3, "earth": 0.6},
            "abyssal_horror": {"dark": 2.0, "water": 1.5, "holy": 0.3, "lightning": 0.5},
            "volcanic_titan": {"fire": 2.0, "earth": 1.8, "ice": 0.3, "water": 0.4},
            "frost_phoenix": {"ice": 2.0, "holy": 1.5, "fire": 0.4, "dark": 0.5},
            "void_beast": {"dark": 2.0, "holy": 0.4, "fire": 0.6, "lightning": 0.6},
            "tempest_serpent": {"wind": 2.0, "lightning": 1.5, "earth": 0.4, "ice": 0.6},

            # === Tier 6 - 보스급 적 ===
            "demon_lord": {"dark": 2.0, "fire": 1.5, "holy": 0.3, "ice": 0.5},
            "elder_lich": {"dark": 2.0, "ice": 1.8, "holy": 0.3, "fire": 0.4},
            "storm_colossus": {"lightning": 2.0, "wind": 1.8, "earth": 0.4, "ice": 0.5},
            "primordial_dragon": {"fire": 1.5, "ice": 1.3, "lightning": 1.3, "holy": 0.6, "dark": 0.6},

            # === legendary 티어 ===
            "hell_knight": {"dark": 1.8, "fire": 1.5, "holy": 0.4, "ice": 0.6},
            "blood_witch": {"dark": 2.0, "holy": 0.3, "fire": 0.7},
            "shadow_dragon": {"dark": 2.0, "fire": 1.3, "holy": 0.4, "lightning": 0.6},
            "arcane_golem": {"earth": 1.8, "lightning": 0.5, "fire": 0.6, "holy": 1.3},
            "death_priest": {"dark": 2.0, "holy": 0.3, "fire": 0.6},
            "flame_titan": {"fire": 2.5, "ice": 0.3, "water": 0.4, "earth": 1.5},
            "ice_wraith": {"ice": 2.0, "fire": 0.4, "holy": 0.5, "dark": 1.3},
            "thunder_lord": {"lightning": 2.0, "earth": 0.4, "water": 0.6, "wind": 1.5},
            "corrupted_angel": {"dark": 1.5, "holy": 1.5, "lightning": 0.5, "fire": 0.6},
            "venom_drake": {"earth": 1.5, "dark": 1.3, "ice": 0.5, "holy": 0.6},
            "storm_harpy": {"wind": 2.0, "lightning": 1.5, "earth": 0.4, "ice": 0.6},
            "bone_colossus": {"dark": 1.5, "earth": 1.5, "holy": 0.4, "fire": 0.5},
            "cursed_samurai": {"dark": 1.5, "wind": 1.3, "holy": 0.5, "lightning": 0.6},
            "magma_serpent": {"fire": 2.0, "earth": 1.3, "ice": 0.4, "water": 0.5},
            "void_sentinel": {"dark": 1.8, "holy": 0.4, "lightning": 0.5, "fire": 0.6},

            # === mythic 티어 ===
            "world_serpent": {"water": 1.8, "earth": 1.5, "lightning": 0.5, "ice": 0.6},
            "fallen_seraph": {"dark": 1.8, "holy": 1.5, "lightning": 0.5, "fire": 0.5},
            "titan_king": {"earth": 2.0, "fire": 1.3, "lightning": 0.5, "ice": 0.5},
            "lich_emperor": {"dark": 2.0, "ice": 1.8, "holy": 0.3, "fire": 0.4},
            "nightmare_king": {"dark": 2.0, "holy": 0.3, "fire": 0.5, "lightning": 0.5},
            "elemental_lord": {"fire": 1.3, "ice": 1.3, "lightning": 1.3, "water": 1.3, "earth": 1.3, "wind": 1.3, "holy": 0.5, "dark": 0.5},
            "doom_bringer": {"dark": 1.8, "fire": 1.3, "holy": 0.4, "ice": 0.5},
            "celestial_dragon": {"holy": 1.8, "fire": 1.3, "dark": 0.4, "ice": 0.5},
            "abyssal_king": {"dark": 2.0, "water": 1.5, "holy": 0.3, "lightning": 0.5},
            "chrono_guardian": {"lightning": 1.5, "wind": 1.5, "earth": 0.5, "dark": 0.5},
            "infernal_dragon": {"fire": 2.0, "dark": 1.5, "ice": 0.3, "water": 0.4},
            "divine_beast": {"holy": 1.8, "wind": 1.3, "dark": 0.4, "fire": 0.5},
            "shadow_emperor": {"dark": 2.0, "holy": 0.3, "fire": 0.5, "lightning": 0.5},
            "runic_titan": {"earth": 2.0, "lightning": 1.5, "water": 0.5, "fire": 0.5},
            "eternal_phoenix": {"fire": 2.0, "holy": 1.8, "ice": 0.3, "dark": 0.4},
        }
        return ELEMENT_RESISTANCES.get(enemy_id, {})

    def take_damage(self, damage: int, is_dot: bool = False, **kwargs) -> int:
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

    @property
    def hp(self) -> int:
        """현재 HP (하위 호환성)"""
        return self.current_hp


class SimpleAlly:
    """
    원격 플레이어의 캐릭터를 나타내는 간단한 아군 클래스 (멀티플레이 전투용)

    호스트가 브로드캐스트한 직렬화 데이터로부터 클라이언트 측에서 생성됩니다.
    로컬 Character 객체가 아닌 원격 캐릭터를 전투 파티에 포함시키기 위해 사용합니다.
    """

    def __init__(self, data: dict):
        """
        직렬화된 캐릭터 데이터로부터 아군 객체 생성

        Args:
            data: 직렬화된 캐릭터 전투 데이터 딕셔너리
        """
        self.id = data.get("id", "unknown")
        self.name = data.get("name", "아군")
        self.job_id = data.get("job_id", "warrior")
        self.job_name = data.get("job_name", "전사")
        self.character_class = self.job_id
        self.level = data.get("level", 1)

        # HP/MP
        self.max_hp = data.get("max_hp", 100)
        self.current_hp = data.get("current_hp", self.max_hp)
        self.max_mp = data.get("max_mp", 50)
        self.current_mp = data.get("current_mp", self.max_mp)

        # 전투 스탯
        self.physical_attack = data.get("physical_attack", 10)
        self.physical_defense = data.get("physical_defense", 10)
        self.magic_attack = data.get("magic_attack", 10)
        self.magic_defense = data.get("magic_defense", 10)
        self.speed = data.get("speed", 50)

        # BRV
        self.max_brv = data.get("max_brv", 1000)
        self.init_brv = data.get("init_brv", 333)
        self.current_brv = data.get("current_brv", self.init_brv)

        # 상태
        self.is_alive = data.get("is_alive", True)
        self.is_enemy = False
        self.owner_player_id = data.get("owner_player_id")

        # 상태이상 관리 (전투 시스템 호환)
        self.status_manager = StatusManager(owner_name=self.name, owner=self)
        self.status_effects = self.status_manager.status_effects
        self.wound_damage = 0

        # 스킬 (원격 아군은 빈 목록 - 봇/AI가 제어)
        self.skills = []

    def take_damage(self, amount: int) -> int:
        """데미지 적용"""
        actual_damage = min(amount, self.current_hp)
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

    @property
    def hp(self) -> int:
        """현재 HP (하위 호환성)"""
        return self.current_hp


class EnemyGenerator:
    """적 생성기"""

    # 적 등급별 등장 층수 정의
    ENEMY_TIERS = {
        # 약한 적 (1-3층)
        "weak": ["slime", "goblin", "wolf", "zombie", "imp", "giant_centipede",
                 "mushroom", "bat", "rat_swarm", "fire_sprite", "ice_fairy"],
        # 일반 적 (3-6층)
        "normal": [
            "orc", "skeleton", "dark_mage", "ghoul", "spider", "scorpion", "bear",
            "dire_wolf", "merfolk_warrior", "queen_bee", "plague_moth",
            "lizardman", "harpy", "shadow_imp", "frost_wolf", "flame_hound",
            "sand_worm", "thunder_hawk", "aqua_slime"
        ],
        # 강한 적 (6-9층)
        "strong": [
            "ogre", "wraith", "golem",
            "mummy", "banshee", "fire_elemental", "ice_elemental",
            "wind_elemental", "basilisk",
            "thunderbird", "sea_serpent", "revenant", "death_beetle", "assassin",
            "gargoyle", "spectre", "lava_golem", "frost_giant", "storm_drake",
            "dark_priestess", "iron_beetle", "toxic_hydra", "phoenix_chick"
        ],
        # 매우 강한 적 (9-12층)
        "very_strong": [
            "troll", "vampire", "wyvern",
            "death_knight", "thunder_elemental", "dark_elemental",
            "earth_elemental", "cerberus", "hydra", "mimic",
            "manticore", "siren", "dullahan", "dark_knight", "battle_mage",
            "shadow_stalker", "berserker",
            "chaos_knight", "frost_wyrm", "thunder_dragon", "plague_bearer",
            "crystal_guardian", "shadow_assassin", "infernal_mage",
            "water_elemental", "storm_giant"
        ],
        # 최상급 적 (12-15층)
        "elite": [
            "demon", "dragon",
            "fire_dragon", "ice_dragon", "poison_dragon",
            "succubus", "nightmare",
            "chimera", "kraken", "bone_dragon", "lich_king",
            "void_walker", "nightmare_lord",
            "ancient_lich", "chaos_dragon", "celestial_guardian", "abyssal_horror",
            "volcanic_titan", "frost_phoenix", "void_beast", "tempest_serpent"
        ],
        # 보스급 (15층 이상 또는 특수 조우)
        "boss": [
            "balrog", "archfiend", "elder_dragon",
            "iron_golem", "crystal_golem", "ancient_automaton",
            "treant", "abyss_demon",
            "demon_lord", "elder_lich", "storm_colossus", "primordial_dragon"
        ],
        # legendary 티어 (18-24층)
        "legendary": [
            "hell_knight", "blood_witch", "shadow_dragon", "arcane_golem",
            "death_priest", "flame_titan", "ice_wraith", "thunder_lord",
            "corrupted_angel", "venom_drake", "storm_harpy", "bone_colossus",
            "cursed_samurai", "magma_serpent", "void_sentinel"
        ],
        # mythic 티어 (24+층)
        "mythic": [
            "world_serpent", "fallen_seraph", "titan_king", "lich_emperor",
            "nightmare_king", "elemental_lord", "doom_bringer", "celestial_dragon",
            "abyssal_king", "chrono_guardian", "infernal_dragon", "divine_beast",
            "shadow_emperor", "runic_titan", "eternal_phoenix"
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
        if 14 <= floor_number <= 20:
            suitable.extend(EnemyGenerator.ENEMY_TIERS["elite"])
            suitable.extend(EnemyGenerator.ENEMY_TIERS["boss"])
        if 18 <= floor_number <= 26:
            suitable.extend(EnemyGenerator.ENEMY_TIERS["boss"])
            suitable.extend(EnemyGenerator.ENEMY_TIERS["legendary"])
        if floor_number >= 24:
            suitable.extend(EnemyGenerator.ENEMY_TIERS["legendary"])
            suitable.extend(EnemyGenerator.ENEMY_TIERS["mythic"])

        # 최소 1종류는 나오도록
        if not suitable:
            suitable = EnemyGenerator.ENEMY_TIERS["weak"]

        return suitable

    @staticmethod
    def _apply_early_game_scaling(enemy: 'SimpleEnemy', floor_number: int):
        """초반 층(1~14) 적 밸런스 강화 - 15층 이후는 영향 없음"""
        if floor_number >= 15:
            return
        # t: 1층=1.0 (최대 버프) → 14층≈0.07 (거의 없음)
        t = (15 - floor_number) / 14.0
        # 공격력 강화 (아군이 받는 HP 피해 증가)
        atk_mult = 1.0 + t * 0.4
        enemy.physical_attack = int(enemy.physical_attack * atk_mult)
        enemy.magic_attack = int(enemy.magic_attack * atk_mult)
        # 방어력 강화 (아군 BRV 공격에 대한 내성 증가)
        def_mult = 1.0 + t * 1.0
        enemy.physical_defense = int(enemy.physical_defense * def_mult)
        enemy.magic_defense = int(enemy.magic_defense * def_mult)
        # HP 강화
        hp_mult = 1.0 + t * 0.5
        enemy.max_hp = int(enemy.max_hp * hp_mult)
        enemy.current_hp = enemy.max_hp
        # BRV 강화 (적 BRV 풀이 커져야 HP 공격 데미지도 증가)
        brv_mult = 1.0 + t * 0.6
        enemy.max_brv = int(enemy.max_brv * brv_mult)
        enemy.init_brv = int(enemy.init_brv * brv_mult)
        enemy.current_brv = enemy.init_brv
        logger.debug(f"[초반 밸런스] {enemy.name} 층{floor_number} 보정: ATK×{atk_mult:.2f} DEF×{def_mult:.2f} HP×{hp_mult:.2f} BRV×{brv_mult:.2f}")

    @staticmethod
    def generate_enemies(floor_number: int, num_enemies: int = None, boss_battle: bool = False) -> List[SimpleEnemy]:
        """
        층수에 맞는 적 생성

        Args:
            floor_number: 층 번호
            num_enemies: 적 수 (None이면 자동)
            boss_battle: 보스전 여부 (True면 잡몹 1.4배 강화)

        Returns:
            적 리스트
        """
        if num_enemies is None:
            # config에서 적 수 범위 가져오기
            from src.core.config import get_config
            config = get_config()
            min_enemies = config.get("world.dungeon.enemy_count.min_enemies", 1)
            max_enemies = config.get("world.dungeon.enemy_count.max_enemies", 3)  # 기본 최대 3 (보너스로 +1 됨)

            # 랜덤하게 1~3마리 생성 후 +1 추가 (총 2~4마리)
            num_enemies = random.randint(min_enemies, max_enemies) + 1
            
            # 최대 4마리로 제한
            num_enemies = min(num_enemies, 4)

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

        for i in range(num_enemies):
            enemy_id = random.choice(suitable_enemy_ids)

            template = ENEMY_TEMPLATES[enemy_id]

            # 레벨 스케일링 계수 (층수와 비슷하거나 조금 낮게)
            # 1층 = 0.8배, 2층 = 1.6배, 3층 = 2.4배, ... (층수 * 0.8)
            level_modifier = floor_number * 0.8

            # 보스전 잡몹 강화 (1.4배)
            boss_battle_mult = 1.4 if boss_battle else 1.0

            enemy = SimpleEnemy(template, level_modifier, difficulty_hp_mult * boss_battle_mult, difficulty_dmg_mult * boss_battle_mult)

            # 적 타입에 맞는 스킬 추가
            try:
                from src.combat.enemy_skills import EnemySkillDatabase
                enemy.skills = EnemySkillDatabase.get_skills_for_enemy_type(template.enemy_id)
            except ImportError as e:
                # EnemySkillDatabase가 없을 경우 기본 스킬로 작동
                logger.debug(f"적 스킬 로드 실패: {e} - 기본 스킬 사용")

            # 초반 층 밸런스 보정 (1~14층)
            EnemyGenerator._apply_early_game_scaling(enemy, floor_number)

            enemies.append(enemy)

        return enemies

    @staticmethod
    def generate_boss(floor_number: int, is_floor_boss: bool = False, boss_battle: bool = False) -> SimpleEnemy:
        """
        보스 생성

        Args:
            floor_number: 층 번호
            is_floor_boss: True면 5층마다 등장하는 강력한 층 보스, False면 일반 층의 보스
            boss_battle: True면 최종보스전 (20층, 30층)에서 추가 처리 적용

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
            # ⚠️ 30층 = 진 최종 보스 카인 (4분 타임어택)
            if floor_number == 30:
                template = ENEMY_TEMPLATES["abel_cain"]
                boss_name = "닥터 아벨 카인"
                boss_enemy_id = "abel_cain"
            # ⚠️ 20층 = 최종 보스 세피로스 (7분 30초 타임어택)
            elif floor_number == 20:
                template = ENEMY_TEMPLATES["sephiroth"]
                boss_name = "세피로스"
                boss_enemy_id = "sephiroth"
            elif floor_number >= 50:
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

            # 층 보스는 추가 강화 (HP 1.8배, 공격 1.5배, 방어 1.4배)
            boss.max_hp = int(boss.max_hp * 1.8)
            boss.current_hp = boss.max_hp
            boss.physical_attack = int(boss.physical_attack * 1.5)
            boss.magic_attack = int(boss.magic_attack * 1.5)
            boss.physical_defense = int(boss.physical_defense * 1.4)
            boss.magic_defense = int(boss.magic_defense * 1.4)
            boss.max_brv = int(boss.max_brv * 1.3)
            boss.current_brv = int(boss.current_brv * 1.3)
            
            # 5층마다 나오는 보스 20% 약화 (모든 스탯)
            weaken_multiplier = 0.8
            boss.max_hp = int(boss.max_hp * weaken_multiplier)
            boss.current_hp = int(boss.current_hp * weaken_multiplier)
            boss.physical_attack = int(boss.physical_attack * weaken_multiplier)
            boss.magic_attack = int(boss.magic_attack * weaken_multiplier)
            boss.physical_defense = int(boss.physical_defense * weaken_multiplier)
            boss.magic_defense = int(boss.magic_defense * weaken_multiplier)
            boss.max_brv = int(boss.max_brv * weaken_multiplier)
            boss.current_brv = int(boss.current_brv * weaken_multiplier)
            boss.speed = int(boss.speed * weaken_multiplier)
            boss.luck = int(boss.luck * weaken_multiplier)
            boss.accuracy = int(boss.accuracy * weaken_multiplier)
            boss.evasion = int(boss.evasion * weaken_multiplier)
            boss.max_mp = int(boss.max_mp * weaken_multiplier)
            boss.current_mp = int(boss.current_mp * weaken_multiplier)

            boss.name = boss_name
            boss.enemy_id = boss_enemy_id

            # 최종보스 특별 처리 (20층 세피로스, 30층 카인)
            if boss_battle and boss_enemy_id in ["sephiroth", "abel_cain"]:
                # 세피로스와 카인 HP 15% 상향 (강화된 난이도)
                boss.max_hp = int(boss.max_hp * 1.15)  # 15% 증가
                boss.current_hp = boss.max_hp
                logger.info(f"{boss_name} HP 15% 상향 (강화 난이도): {boss.max_hp}")

                # 세피로스와 카인의 MP를 999로 설정
                boss.max_mp = 999
                boss.current_mp = 999
                logger.info(f"{boss_name} MP를 999로 설정")

            # 스킬 추가
            try:
                # 카인은 전용 스킬 사용
                if boss_enemy_id == "abel_cain":
                    from src.combat.cain_skills import CainSkillDatabase
                    boss.skills = CainSkillDatabase.get_all_cain_skills()
                    logger.info(f"카인 전용 스킬 {len(boss.skills)}개 로드 완료")
                # 세피로스는 전용 스킬 사용
                elif boss_enemy_id == "sephiroth":
                    from src.combat.sephiroth_skills import SephirothSkillDatabase
                    boss.skills = SephirothSkillDatabase.get_all_sephiroth_skills()
                    logger.info(f"세피로스 전용 스킬 {len(boss.skills)}개 로드 완료")
                else:
                    from src.combat.enemy_skills import EnemySkillDatabase
                    boss.skills = EnemySkillDatabase.get_skills_for_enemy_type(boss_enemy_id)
            except ImportError as e:
                logger.warning(f"스킬 로드 실패: {e}")

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

        # 초반 층 밸런스 보정 (1~14층)
        EnemyGenerator._apply_early_game_scaling(boss, floor_number)

        # 일반 보스는 기본 적 스킬 사용
        try:
            from src.combat.enemy_skills import EnemySkillDatabase
            boss.skills = EnemySkillDatabase.get_skills_for_enemy_type(base_enemy_id)
        except ImportError:
            pass

        return boss
