"""
적 고유 스킬 시스템

각 적 타입별로 고유한 스킬 정의
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional, Tuple
from enum import Enum
import random

from src.core.logger import get_logger


logger = get_logger("enemy_skills")


class SkillTargetType(Enum):
    """스킬 대상 타입"""
    SINGLE_ENEMY = "single_enemy"  # 적 1명
    SINGLE_ALLY = "single_ally"    # 아군 1명 (힐링/서포트)
    ALL_ENEMIES = "all_enemies"    # 적 전체
    SELF = "self"                   # 자신
    ALL_ALLIES = "all_allies"      # 아군 전체
    RANDOM_ENEMY = "random_enemy"   # 랜덤 적 1명


@dataclass
class EnemySkill:
    """
    적 스킬

    적이 사용할 수 있는 특수 스킬
    """
    skill_id: str
    name: str
    description: str

    # 대상
    target_type: SkillTargetType = SkillTargetType.SINGLE_ENEMY

    # 코스트
    mp_cost: int = 0
    hp_cost: int = 0  # 생명력 희생 스킬

    # 데미지
    damage: int = 0
    damage_multiplier: float = 1.0  # 공격력 배율
    is_magical: bool = False  # 마법 데미지인지

    # BRV 시스템
    brv_damage: int = 0  # BRV 데미지
    hp_attack: bool = False  # HP 공격 여부


    # 상태 효과
    status_effects: List[str] = field(default_factory=list)  # "poison", "stun", "burn" 등
    status_duration: int = 3  # 턴 수
    status_intensity: float = 0.5  # 상태이상 강도 (기본값: 일반 강도)

    # 버프/디버프
    buff_stats: Dict[str, float] = field(default_factory=dict)  # {"strength": 1.2} 등
    debuff_stats: Dict[str, float] = field(default_factory=dict)

    # 특수 효과
    heal_amount: int = 0  # 회복량
    shield_amount: int = 0  # 실드량
    counter_damage: bool = False  # 반격 설정

    # 사용 확률 (AI가 이 스킬을 선택할 확률)
    use_probability: float = 0.3

    # 쿨다운
    cooldown: int = 0  # 사용 후 몇 턴 대기
    current_cooldown: int = 0  # 현재 쿨다운

    # 조건
    min_hp_percent: float = 0.0  # 최소 HP 퍼센트
    max_hp_percent: float = 1.0  # 최대 HP 퍼센트
    requires_ally_count: int = 0  # 필요한 아군 수

    # 사운드 효과
    sfx: Optional[Tuple[str, str]] = None  # (category, sfx_name) 튜플

    def can_use(self, user: Any) -> bool:
        """
        스킬 사용 가능 여부

        Args:
            user: 사용자 (적 캐릭터)

        Returns:
            사용 가능 여부
        """
        # 쿨다운 체크
        if self.current_cooldown > 0:
            return False

        # MP 체크
        if hasattr(user, 'current_mp'):
            if user.current_mp < self.mp_cost:
                return False

        # HP 체크
        if hasattr(user, 'current_hp'):
            hp_percent = user.current_hp / user.max_hp if user.max_hp > 0 else 0
            if hp_percent < self.min_hp_percent or hp_percent > self.max_hp_percent:
                return False

            # HP 코스트 체크
            if user.current_hp <= self.hp_cost:
                return False

        return True

    def reduce_cooldown(self):
        """쿨다운 감소 (매 턴마다 호출)"""
        if self.current_cooldown > 0:
            self.current_cooldown -= 1

    def activate_cooldown(self):
        """쿨다운 활성화 (스킬 사용 후 호출)"""
        self.current_cooldown = self.cooldown


class EnemySkillDatabase:
    """적 스킬 데이터베이스"""

    SKILLS = {}

    @classmethod
    def initialize(cls):
        """스킬 데이터베이스 초기화"""
        if cls.SKILLS:
            return  # 이미 초기화됨

        cls.SKILLS = {
            # === 일반 몬스터 스킬 ===

            # 고블린 - 독 공격
            "poison_stab": EnemySkill(
                skill_id="poison_stab",
                name="독침 찌르기",
                description="독이 묻은 단검으로 공격하여 중독을 일으킨다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage=0,  # BRV 시스템 사용
                damage_multiplier=1.5,  # BRV 배율
                brv_damage=1,  # BRV 공격 활성화
                status_effects=["poison"],
                status_duration=3,
                status_intensity=0.3,  # poison_stab 조정
                use_probability=0.35,
                cooldown=2,
                sfx=("skill", "poison")
            ),

            # 고블린 - 도망
            "goblin_flee": EnemySkill(
                skill_id="goblin_flee",
                name="비겁한 도망",
                description="HP가 낮을 때 도망치려 한다.",
                target_type=SkillTargetType.SELF,
                buff_stats={"speed": 1.5},
                use_probability=0.5,
                min_hp_percent=0.0,
                max_hp_percent=0.3,  # HP 30% 이하일 때만
                cooldown=99,  # 한 번만 사용
                sfx=("character", "status_buff")
            ),

            # 오크 - 강타
            "heavy_strike": EnemySkill(
                skill_id="heavy_strike",
                name="강력한 일격",
                description="묵직한 공격으로 큰 피해를 입힌다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage=0,  # BRV 시스템 사용
                damage_multiplier=2.2,  # 강력한 BRV 배율
                brv_damage=1,  # BRV 공격
                hp_attack=True,  # HP 공격도 가능
                use_probability=0.25,
                cooldown=3,
                sfx=("combat", "damage_high")
            ),

            # 오크 - 전투 함성
            "war_cry": EnemySkill(
                skill_id="war_cry",
                name="전투 함성",
                description="함성을 지르며 아군의 사기를 높인다.",
                target_type=SkillTargetType.ALL_ALLIES,
                buff_stats={"strength": 1.3, "defense": 1.2},
                use_probability=0.2,
                cooldown=5,
                sfx=("skill", "roar")
            ),

            # 트롤 - 재생
            "regeneration": EnemySkill(
                skill_id="regeneration",
                name="재생",
                description="빠른 속도로 HP를 회복한다.",
                target_type=SkillTargetType.SELF,
                heal_amount=50,
                use_probability=0.4,
                min_hp_percent=0.0,
                max_hp_percent=0.5,  # HP 50% 이하일 때
                cooldown=4,
                sfx=("character", "hp_heal")
            ),

            # 늑대 - 물어뜯기
            "savage_bite": EnemySkill(
                skill_id="savage_bite",
                name="물어뜯기",
                description="날카로운 송곳니로 물어뜯어 출혈을 일으킨다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage=0,  # BRV 시스템
                damage_multiplier=1.7,
                brv_damage=1,
                hp_attack=True,
                status_effects=["bleed"],
                status_duration=3,
                status_intensity=0.35,  # savage_bite 조정
                use_probability=0.4,
                cooldown=2,
                sfx=("combat", "attack_physical")
            ),

            # 늑대 - 무리 사냥
            "pack_tactics": EnemySkill(
                skill_id="pack_tactics",
                name="무리 사냥",
                description="무리의 힘으로 공격력과 속도를 증가시킨다.",
                target_type=SkillTargetType.ALL_ALLIES,
                buff_stats={"strength": 1.4, "speed": 1.3},
                use_probability=0.25,
                requires_ally_count=2,  # 아군 2마리 이상 필요
                cooldown=5
            ),

            # 슬라임 - 산성 분사
            "acid_spray": EnemySkill(
                skill_id="acid_spray",
                name="산성 분사",
                description="산성 액체를 뿌려 방어력을 감소시킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                damage=0,
                damage_multiplier=1.2,
                brv_damage=1,
                is_magical=True,
                debuff_stats={"defense": 0.7, "spirit": 0.7},
                use_probability=0.35,
                cooldown=3
            ),

            # 슬라임 - 분열
            "slime_split": EnemySkill(
                skill_id="slime_split",
                name="분열",
                description="자신을 분열시켜 실드를 얻는다.",
                target_type=SkillTargetType.SELF,
                shield_amount=30,
                buff_stats={"defense": 1.3},
                use_probability=0.3,
                min_hp_percent=0.0,
                max_hp_percent=0.4,
                cooldown=6
            ),

            # 오우거 - 분쇄
            "crush": EnemySkill(
                skill_id="crush",
                name="분쇄",
                description="거대한 힘으로 적을 분쇄한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage=0,
                damage_multiplier=2.5,
                brv_damage=1,
                hp_attack=True,
                status_effects=["stun"],
                status_duration=1,
                status_intensity=0.4,  # crush 조정
                use_probability=0.2,
                cooldown=4
            ),

            # 오우거 - 광폭화
            "rage": EnemySkill(
                skill_id="rage",
                name="광폭화",
                description="분노하여 공격력이 대폭 증가하지만 방어력이 감소한다.",
                target_type=SkillTargetType.SELF,
                hp_cost=20,
                buff_stats={"strength": 2.0, "defense": 0.7},
                use_probability=0.25,
                min_hp_percent=0.0,
                max_hp_percent=0.5,
                cooldown=5
            ),

            # 망령 - 공포의 외침
            "wail_of_terror": EnemySkill(
                skill_id="wail_of_terror",
                name="공포의 외침",
                description="공포스러운 비명으로 적들을 겁에 질리게 한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                debuff_stats={"strength": 0.6, "magic": 0.6, "speed": 0.8},
                status_effects=["fear"],
                status_duration=2,
                is_magical=True,
                mp_cost=25,
                use_probability=0.35,
                cooldown=4
            ),

            # 망령 - 영혼 흡수
            "soul_drain": EnemySkill(
                skill_id="soul_drain",
                name="영혼 흡수",
                description="적의 영혼을 흡수하여 MP를 회복한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage=0,
                damage_multiplier=1.6,
                brv_damage=1,
                hp_attack=True,
                is_magical=True,
                heal_amount=25,  # MP 회복 (특수 처리)
                mp_cost=15,
                use_probability=0.3,
                cooldown=3
            ),

            # 골렘 - 대지의 충격
            "earth_shock": EnemySkill(
                skill_id="earth_shock",
                name="대지의 충격",
                description="땅을 내리쳐 모든 적을 공격한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                damage=0,
                damage_multiplier=1.8,
                brv_damage=1,
                hp_attack=True,
                status_effects=["slow"],
                status_duration=2,
                status_intensity=0.4,  # soul_drain 조정
                use_probability=0.35,
                cooldown=4
            ),

            # 골렘 - 석화
            "petrify": EnemySkill(
                skill_id="petrify",
                name="석화",
                description="자신을 돌로 만들어 방어력을 극대화한다.",
                target_type=SkillTargetType.SELF,
                buff_stats={"defense": 2.5, "spirit": 2.0},
                use_probability=0.25,
                cooldown=6
            ),

            # 와이번 - 급강하
            "dive_attack": EnemySkill(
                skill_id="dive_attack",
                name="급강하 공격",
                description="하늘에서 급강하하여 강력한 일격을 날린다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage=0,
                damage_multiplier=2.3,
                brv_damage=1,
                hp_attack=True,
                use_probability=0.4,
                cooldown=3
            ),

            # 와이번 - 독 숨결
            "poison_breath": EnemySkill(
                skill_id="poison_breath",
                name="독 숨결",
                description="독성 가스를 내뿜어 적들을 중독시킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                damage=0,
                damage_multiplier=1.4,
                brv_damage=1,
                is_magical=True,
                status_effects=["poison", "weakness"],
                status_duration=3,
                status_intensity=0.25,  # poison_breath 조정
                use_probability=0.3,
                cooldown=4
            ),

            # 뱀파이어 - 흡혈
            "vampire_bite": EnemySkill(
                skill_id="vampire_bite",
                name="흡혈",
                description="적의 피를 빨아 HP를 회복한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage=0,
                damage_multiplier=1.8,
                brv_damage=1,
                hp_attack=True,
                heal_amount=40,
                use_probability=0.45,
                cooldown=2
            ),

            # 뱀파이어 - 박쥐 변신
            "bat_form": EnemySkill(
                skill_id="bat_form",
                name="박쥐 변신",
                description="박쥐로 변신하여 회피율과 속도를 대폭 증가시킨다.",
                target_type=SkillTargetType.SELF,
                buff_stats={"speed": 2.0},  # 회피율은 특수 처리
                use_probability=0.25,
                cooldown=5
            ),

            # 언데드 - 생명력 흡수
            "life_drain": EnemySkill(
                skill_id="life_drain",
                name="생명력 흡수",
                description="적의 생명력을 빨아들여 자신을 회복한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage=0,  # BRV 시스템 사용
                damage_multiplier=1.5,  # BRV+HP 배율
                brv_damage=1,
                hp_attack=True,  # BRV+HP 공격
                heal_amount=30,  # 회복량 (별도 처리)
                is_magical=True,
                use_probability=0.3,
                cooldown=2
            ),

            # === 마법 몬스터 스킬 ===

            # 마법사 - 화염구
            "fireball": EnemySkill(
                skill_id="fireball",
                name="화염구",
                description="불타는 구체를 발사한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage=0,  # BRV 시스템 사용
                damage_multiplier=1.8,  # 마법 BRV 배율
                brv_damage=1,  # BRV 공격
                hp_attack=True,  # HP 공격도 가능
                is_magical=True,
                mp_cost=15,
                status_effects=["burn"],
                status_duration=2,
                status_intensity=0.35,  # fireball 조정
                use_probability=0.4,
                cooldown=1
            ),

            # 마법사 - 얼음 폭풍
            "ice_storm": EnemySkill(
                skill_id="ice_storm",
                name="얼음 폭풍",
                description="적 전체를 얼음으로 공격한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                damage=0,  # BRV 시스템 사용
                damage_multiplier=1.5,  # 전체 공격은 낮은 배율
                brv_damage=1,  # BRV 공격
                is_magical=True,
                mp_cost=25,
                status_effects=["slow"],
                status_duration=2,
                status_intensity=0.35,  # ice_storm 조정
                use_probability=0.25,
                cooldown=3
            ),

            # 마법사 - 마나 폭발
            "mana_burst": EnemySkill(
                skill_id="mana_burst",
                name="마나 폭발",
                description="모든 MP를 소모하여 강력한 마법 공격.",
                target_type=SkillTargetType.ALL_ENEMIES,
                damage=0,  # BRV 시스템 사용
                damage_multiplier=2.5,  # 필살기 배율
                brv_damage=1,
                hp_attack=True,  # BRV+HP 공격
                is_magical=True,
                mp_cost=999,  # 모든 MP (실제로는 current_mp만큼 사용)
                use_probability=0.15,
                min_hp_percent=0.0,
                max_hp_percent=0.25,  # HP 25% 이하일 때 (필살기)
                cooldown=99
            ),

            # === 보스 스킬 ===

            # 드래곤 - 브레스
            "dragon_breath": EnemySkill(
                skill_id="dragon_breath",
                name="드래곤 브레스",
                description="불길을 뿜어 적 전체에게 막대한 피해를 입힌다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                damage=0,  # BRV 시스템 사용
                damage_multiplier=2.0,  # 강력한 전체 공격
                brv_damage=1,
                hp_attack=True,  # BRV+HP 공격
                is_magical=True,
                mp_cost=30,
                status_effects=["burn"],
                status_duration=3,
                status_intensity=0.5,  # dragon_breath 조정
                use_probability=0.35,
                cooldown=4
            ),

            # 드래곤 - 용의 위압
            "dragon_intimidation": EnemySkill(
                skill_id="dragon_intimidation",
                name="용의 위압",
                description="압도적인 위압감으로 적들을 약화시킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                debuff_stats={"strength": 0.7, "defense": 0.7, "magic": 0.7},
                use_probability=0.2,
                cooldown=6
            ),

            # 드래곤 - 비행
            "dragon_flight": EnemySkill(
                skill_id="dragon_flight",
                name="비행",
                description="하늘로 날아올라 회피율을 대폭 증가시킨다.",
                target_type=SkillTargetType.SELF,
                buff_stats={"speed": 2.0},
                use_probability=0.15,
                cooldown=5
            ),

            # 악마 - 지옥의 불꽃
            "hellfire": EnemySkill(
                skill_id="hellfire",
                name="지옥의 불꽃",
                description="지옥에서 솟아오른 불꽃이 적들을 태운다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                damage=0,  # BRV 시스템 사용
                damage_multiplier=2.2,  # 강력한 악마 마법
                brv_damage=1,
                hp_attack=True,  # BRV+HP 공격
                is_magical=True,
                mp_cost=40,
                status_effects=["burn", "curse"],
                status_duration=4,
                status_intensity=0.5,  # hellfire 조정
                use_probability=0.3,
                cooldown=3
            ),

            # 악마 - 악마의 계약
            "demon_pact": EnemySkill(
                skill_id="demon_pact",
                name="악마의 계약",
                description="HP를 희생하여 강력한 힘을 얻는다.",
                target_type=SkillTargetType.SELF,
                hp_cost=30,
                buff_stats={"strength": 1.8, "magic": 1.8},
                use_probability=0.25,
                cooldown=5
            ),

            # ============================================================
            # 새로운 적 스킬 (70개)
            # ============================================================

            # === 언데드 타입 스킬 (12개) ===

            # 좀비 스킬
            "infected_strike": EnemySkill(
                skill_id="infected_strike",
                name="감염된 일격",
                description="감염된 손톱으로 공격하여 질병을 일으킨다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=3.2,
                brv_damage=1,
                status_effects=["disease", "weakness"],
                status_duration=4,
                status_intensity=0.3,  # infected_strike 조정
                use_probability=0.4,
                cooldown=2
            ),
            "zombify": EnemySkill(
                skill_id="zombify",
                name="좀비화",
                description="적을 물어 좀비로 만들려 한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=1.4,
                brv_damage=1,
                hp_attack=True,
                status_effects=["curse", "slow"],
                status_duration=5,
                status_intensity=0.3,  # zombify 조정
                use_probability=0.3,
                cooldown=4
            ),
            "undead_resilience": EnemySkill(
                skill_id="undead_resilience",
                name="언데드 회복력",
                description="언데드의 생명력으로 HP를 천천히 회복한다.",
                target_type=SkillTargetType.SELF,
                heal_amount=30,
                use_probability=0.35,
                min_hp_percent=0.0,
                max_hp_percent=0.6,
                cooldown=3
            ),

            # 구울 스킬
            "corpse_eater": EnemySkill(
                skill_id="corpse_eater",
                name="시체 먹기",
                description="아군의 시체를 먹어 HP를 대폭 회복한다.",
                target_type=SkillTargetType.SELF,
                heal_amount=60,
                use_probability=0.5,
                min_hp_percent=0.0,
                max_hp_percent=0.4,
                cooldown=5
            ),
            "frenzy": EnemySkill(
                skill_id="frenzy",
                name="광란",
                description="광란 상태가 되어 공격력과 속도가 증가한다.",
                target_type=SkillTargetType.SELF,
                buff_stats={"strength": 1.8, "speed": 1.6},
                use_probability=0.35,
                cooldown=4
            ),
            "swift_assault": EnemySkill(
                skill_id="swift_assault",
                name="빠른 습격",
                description="빠르게 달려들어 연속 공격을 가한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.0,
                brv_damage=1,
                hp_attack=True,
                use_probability=0.4,
                cooldown=3
            ),

            # 밴시 스킬
            "wail": EnemySkill(
                skill_id="wail",
                name="통곡",
                description="슬픈 울음소리로 적들의 정신을 혼란시킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=20,
                debuff_stats={"magic": 0.6, "spirit": 0.6},
                status_effects=["confusion"],
                status_duration=2,
                status_intensity=0.4,  # wail 조정
                use_probability=0.4,
                cooldown=3
            ),
            "cursed_scream": EnemySkill(
                skill_id="cursed_scream",
                name="저주의 비명",
                description="저주받은 비명으로 적들에게 다중 저주를 건다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=25,
                damage_multiplier=1.4,
                brv_damage=1,
                status_effects=["curse", "silence", "slow"],
                status_duration=2,
                status_intensity=0.425,  # cursed_scream 조정
                use_probability=0.2,
                cooldown=4
            ),
            "soul_steal": EnemySkill(
                skill_id="soul_steal",
                name="영혼 갈취",
                description="적의 영혼을 갈취하여 자신의 MP로 만든다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                mp_cost=10,
                damage_multiplier=1.5,
                brv_damage=1,
                heal_amount=35,  # MP 회복용
                use_probability=0.3,
                cooldown=3
            ),

            # 죽음의 기사 스킬
            "dark_slash": EnemySkill(
                skill_id="dark_slash",
                name="암흑 베기",
                description="암흑 기운을 담은 강력한 참격을 날린다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.4,
                brv_damage=1,
                hp_attack=True,
                is_magical=False,
                use_probability=0.4,
                cooldown=2
            ),
            "death_sentence": EnemySkill(
                skill_id="death_sentence",
                name="죽음의 선고",
                description="대상에게 죽음을 선고하여 지속 데미지를 입힌다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                mp_cost=30,
                status_effects=["doom", "curse"],
                status_duration=5,
                status_intensity=0.45,  # death_sentence 조정
                use_probability=0.25,
                cooldown=6
            ),
            "dark_aura": EnemySkill(
                skill_id="dark_aura",
                name="암흑 오라",
                description="암흑 오라를 펼쳐 자신과 아군을 강화한다.",
                target_type=SkillTargetType.ALL_ALLIES,
                mp_cost=25,
                buff_stats={"strength": 1.4, "defense": 1.3, "magic": 1.3},
                use_probability=0.3,
                cooldown=5
            ),

            # 미라 스킬
            "ancient_curse": EnemySkill(
                skill_id="ancient_curse",
                name="고대의 저주",
                description="고대 이집트의 저주를 내려 모든 능력치를 감소시킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=20,
                debuff_stats={"strength": 0.7, "defense": 0.7, "magic": 0.7, "spirit": 0.7, "speed": 0.8},
                use_probability=0.35,
                cooldown=4
            ),
            "bandage_wrap": EnemySkill(
                skill_id="bandage_wrap",
                name="붕대 감기",
                description="붕대로 적을 감싸 속박하고 방어력을 감소시킨다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=1.3,
                brv_damage=1,
                status_effects=["bind", "weakness"],
                status_duration=3,
                status_intensity=0.35,  # bandage_wrap 조정
                use_probability=0.35,
                cooldown=3
            ),
            "resurrection": EnemySkill(
                skill_id="resurrection",
                name="부활",
                description="한 번 사망 시 부활하여 HP를 회복한다.",
                target_type=SkillTargetType.SELF,
                heal_amount=100,
                use_probability=0.9,
                min_hp_percent=0.0,
                max_hp_percent=0.01,  # 거의 죽었을 때
                cooldown=99  # 한 번만
            ),

            # === 엘리멘탈 타입 스킬 (18개) ===

            # 불의 정령 스킬
            "flame_burst": EnemySkill(
                skill_id="flame_burst",
                name="화염 폭발",
                description="주변을 화염으로 폭발시킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=25,
                damage_multiplier=1.8,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn"],
                status_duration=3,
                status_intensity=0.36,  # flame_burst 조정
                use_probability=0.4,
                cooldown=3
            ),
            "fire_shield": EnemySkill(
                skill_id="fire_shield",
                name="불꽃 방벽",
                description="불꽃 방벽을 만들어 방어력을 높이고 반격한다.",
                target_type=SkillTargetType.SELF,
                mp_cost=15,
                buff_stats={"defense": 1.5, "spirit": 1.3},
                counter_damage=True,
                use_probability=0.3,
                cooldown=4
            ),
            "lava_eruption": EnemySkill(
                skill_id="lava_eruption",
                name="용암 분출",
                description="땅에서 용암이 분출하여 적들을 공격한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=30,
                damage_multiplier=2.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn", "slow"],
                status_duration=2,
                status_intensity=0.45,  # lava_eruption 조정
                use_probability=0.35,
                cooldown=4
            ),

            # 얼음의 정령 스킬
            "absolute_zero": EnemySkill(
                skill_id="absolute_zero",
                name="절대영도",
                description="주변을 절대영도로 만들어 모든 것을 얼린다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=30,
                damage_multiplier=1.9,
                brv_damage=1,
                hp_attack=True,
                status_effects=["freeze", "slow"],
                status_duration=2,
                status_intensity=0.45,  # absolute_zero 조정
                use_probability=0.35,
                cooldown=4
            ),
            "ice_prison": EnemySkill(
                skill_id="ice_prison",
                name="얼음 감옥",
                description="얼음으로 적을 가두어 행동 불능으로 만든다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                mp_cost=20,
                status_effects=["freeze", "bind"],
                status_duration=2,
                status_intensity=0.4,  # ice_prison 맞춤 강도
                use_probability=0.25,
                cooldown=3
            ),
            "blizzard": EnemySkill(
                skill_id="blizzard",
                name="빙설 폭풍",
                description="차가운 눈보라가 적들을 덮친다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=25,
                damage_multiplier=1.7,
                brv_damage=1,
                status_effects=["slow"],
                status_duration=3,
                status_intensity=0.45,  # blizzard 조정
                use_probability=0.4,
                cooldown=3
            ),

            # 번개의 정령 스킬
            "chain_lightning": EnemySkill(
                skill_id="chain_lightning",
                name="연쇄 번개",
                description="번개가 적들 사이를 연쇄적으로 공격한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=28,
                damage_multiplier=1.9,
                brv_damage=1,
                hp_attack=True,
                status_effects=["paralyze"],
                status_duration=1,
                status_intensity=0.38,  # chain_lightning 조정
                use_probability=0.4,
                cooldown=3
            ),
            "static_field": EnemySkill(
                skill_id="static_field",
                name="정전기",
                description="정전기 장을 만들어 회피율을 높인다.",
                target_type=SkillTargetType.SELF,
                mp_cost=15,
                buff_stats={"speed": 1.8},  # 회피 증가
                use_probability=0.3,
                cooldown=4
            ),
            "thunderbolt": EnemySkill(
                skill_id="thunderbolt",
                name="뇌격",
                description="강력한 낙뢰를 내려 적을 마비시킨다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                mp_cost=25,
                damage_multiplier=2.5,
                brv_damage=1,
                hp_attack=True,
                status_effects=["paralyze", "stun"],
                status_duration=1,
                status_intensity=0.4,  # static_field 조정
                use_probability=0.2,
                cooldown=3
            ),

            # 대지의 정령 스킬
            "rock_throw": EnemySkill(
                skill_id="rock_throw",
                name="바위 투척",
                description="거대한 바위를 던져 적을 공격한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.0,
                brv_damage=1,
                hp_attack=True,
                use_probability=0.4,
                cooldown=2
            ),
            "earth_barrier": EnemySkill(
                skill_id="earth_barrier",
                name="대지 방벽",
                description="대지의 힘으로 실드를 만든다.",
                target_type=SkillTargetType.SELF,
                mp_cost=20,
                shield_amount=80,
                buff_stats={"defense": 1.6},
                use_probability=0.35,
                cooldown=4
            ),
            "earthquake": EnemySkill(
                skill_id="earthquake",
                name="지진",
                description="강력한 지진을 일으켜 적 전체를 공격한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                mp_cost=30,
                damage_multiplier=1.9,
                brv_damage=1,
                hp_attack=True,
                status_effects=["slow", "stun"],
                status_duration=1,
                status_intensity=0.5,  # earthquake 조정
                use_probability=0.2,
                cooldown=4
            ),

            # 바람의 정령 스킬
            "vacuum_wave": EnemySkill(
                skill_id="vacuum_wave",
                name="진공파",
                description="진공의 칼날로 적을 베어낸다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                mp_cost=20,
                damage_multiplier=2.2,
                brv_damage=1,
                hp_attack=True,
                use_probability=0.4,
                cooldown=2
            ),
            "gust": EnemySkill(
                skill_id="gust",
                name="돌풍",
                description="강한 바람으로 적들을 밀어낸다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=20,
                damage_multiplier=1.5,
                brv_damage=1,
                debuff_stats={"accuracy": 0.7},
                use_probability=0.35,
                cooldown=3
            ),
            "tornado": EnemySkill(
                skill_id="tornado",
                name="회오리",
                description="거대한 회오리를 만들어 적들을 공격한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=28,
                damage_multiplier=1.8,
                brv_damage=1,
                hp_attack=True,
                status_effects=["confusion"],
                status_duration=2,
                status_intensity=0.45,  # tornado 조정
                use_probability=0.35,
                cooldown=4
            ),

            # 어둠의 정령 스킬
            "dark_orb": EnemySkill(
                skill_id="dark_orb",
                name="암흑 구체",
                description="암흑 에너지 구체를 발사한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                mp_cost=22,
                damage_multiplier=2.3,
                brv_damage=1,
                hp_attack=True,
                status_effects=["darkness"],
                status_duration=3,
                status_intensity=0.42,  # dark_orb 맞춤 강도
                use_probability=0.4,
                cooldown=2
            ),
            "shadow_veil": EnemySkill(
                skill_id="shadow_veil",
                name="어둠 장막",
                description="어둠의 장막을 펼쳐 회피율을 높인다.",
                target_type=SkillTargetType.SELF,
                mp_cost=20,
                buff_stats={"speed": 1.7},  # 회피 증가
                use_probability=0.3,
                cooldown=4
            ),
            "dark_curse": EnemySkill(
                skill_id="dark_curse",
                name="암흑 저주",
                description="암흑의 저주로 적들을 약화시킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=30,
                debuff_stats={"strength": 0.6, "magic": 0.6, "defense": 0.7, "spirit": 0.7},
                status_effects=["curse"],
                status_duration=4,
                status_intensity=0.42,  # dark_curse 맞춤 강도
                use_probability=0.35,
                cooldown=5
            ),

            # === 야수/몬스터 타입 스킬 (18개) ===

            # 곰 스킬
            "bear_roar": EnemySkill(
                skill_id="bear_roar",
                name="곰의 포효",
                description="위협적인 포효로 적들을 위축시킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                debuff_stats={"strength": 0.7, "defense": 0.7},
                status_effects=["fear"],
                status_duration=2,
                status_intensity=0.4,  # bear_roar 맞춤 강도
                use_probability=0.35,
                cooldown=4
            ),
            "claw_barrage": EnemySkill(
                skill_id="claw_barrage",
                name="할퀴기 연타",
                description="발톱으로 연속 공격을 가한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.3,
                brv_damage=1,
                hp_attack=True,
                status_effects=["bleed"],
                status_duration=3,
                status_intensity=0.4,  # claw_barrage 맞춤 강도
                use_probability=0.4,
                cooldown=3
            ),
            "overwhelming_force": EnemySkill(
                skill_id="overwhelming_force",
                name="압도",
                description="거대한 몸으로 적을 압도한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.6,
                brv_damage=1,
                hp_attack=True,
                status_effects=["stun"],
                status_duration=1,
                status_intensity=0.4,  # overwhelming_force 맞춤 강도
                use_probability=0.3,
                cooldown=4
            ),

            # 거미 스킬
            "web_trap": EnemySkill(
                skill_id="web_trap",
                name="거미줄 덫",
                description="거미줄로 적을 묶어 행동을 제한한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                status_effects=["bind", "slow"],
                status_duration=3,
                status_intensity=0.35,  # web_trap 조정
                use_probability=0.4,
                cooldown=3
            ),
            "venom_spray": EnemySkill(
                skill_id="venom_spray",
                name="독액 분사",
                description="독액을 뿌려 적들을 중독시킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                damage_multiplier=2.8,
                brv_damage=1,
                status_effects=["poison", "weakness"],
                status_duration=4,
                status_intensity=0.4,  # venom_spray 맞춤 강도
                use_probability=0.4,
                cooldown=3
            ),
            "poisonous_fangs": EnemySkill(
                skill_id="poisonous_fangs",
                name="독니",
                description="맹독이 묻은 송곳니로 물어뜯는다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=1.9,
                brv_damage=1,
                hp_attack=True,
                status_effects=["poison"],
                status_duration=5,
                status_intensity=0.3,  # poisonous_fangs 맞춤 강도
                use_probability=0.4,
                cooldown=2
            ),

            # 전갈 스킬
            "scorpion_sting": EnemySkill(
                skill_id="scorpion_sting",
                name="독침 찌르기",
                description="꼬리의 독침으로 치명적인 공격을 가한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.1,
                brv_damage=1,
                hp_attack=True,
                status_effects=["poison", "paralyze"],
                status_duration=2,
                status_intensity=0.4,  # scorpion_sting 맞춤 강도
                use_probability=0.25,
                cooldown=3
            ),
            "pincer_attack": EnemySkill(
                skill_id="pincer_attack",
                name="집게 공격",
                description="강력한 집게로 적을 짓눌러 방어력을 감소시킨다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=1.8,
                brv_damage=1,
                debuff_stats={"defense": 0.6},
                use_probability=0.35,
                cooldown=2
            ),
            "deadly_venom": EnemySkill(
                skill_id="deadly_venom",
                name="맹독",
                description="치명적인 맹독을 주입한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=1.5,
                brv_damage=1,
                status_effects=["poison", "curse"],
                status_duration=6,  # 긴 지속시간
                use_probability=0.35,
                cooldown=4
            ),

            # 바실리스크 스킬
            "petrifying_gaze": EnemySkill(
                skill_id="petrifying_gaze",
                name="석화의 눈빛",
                description="눈을 맞춘 적을 돌로 만든다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                mp_cost=25,
                status_effects=["petrify", "stun"],
                status_duration=2,
                status_intensity=0.44,  # petrifying_gaze 맞춤 강도
                use_probability=0.2,
                cooldown=5
            ),
            "viper_fangs": EnemySkill(
                skill_id="viper_fangs",
                name="독사의 송곳니",
                description="맹독 송곳니로 물어뜯는다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["poison"],
                status_duration=4,
                status_intensity=0.4,  # viper_fangs 맞춤 강도
                use_probability=0.4,
                cooldown=2
            ),
            "paralyzing_stare": EnemySkill(
                skill_id="paralyzing_stare",
                name="마비 시선",
                description="적을 응시하여 마비시킨다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                mp_cost=20,
                status_effects=["paralyze", "slow"],
                status_duration=2,
                status_intensity=0.4,  # paralyzing_stare 맞춤 강도
                use_probability=0.2,
                cooldown=3
            ),

            # 케르베로스 스킬
            "triple_bite": EnemySkill(
                skill_id="triple_bite",
                name="삼중 물어뜯기",
                description="세 개의 머리로 동시에 물어뜯는다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.7,
                brv_damage=1,
                hp_attack=True,
                use_probability=0.4,
                cooldown=3
            ),
            "hellfire_breath": EnemySkill(
                skill_id="hellfire_breath",
                name="지옥의 화염",
                description="지옥의 불꽃을 뿜어낸다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=30,
                damage_multiplier=1.9,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn"],
                status_duration=3,
                status_intensity=0.36,  # hellfire_breath 맞춤 강도
                use_probability=0.35,
                cooldown=4
            ),
            "frenzied_howl": EnemySkill(
                skill_id="frenzied_howl",
                name="광란의 포효",
                description="광란의 울부짖음으로 자신을 강화한다.",
                target_type=SkillTargetType.SELF,
                buff_stats={"strength": 1.8, "speed": 1.5},
                use_probability=0.3,
                cooldown=5
            ),

            # 히드라 스킬
            "head_regeneration": EnemySkill(
                skill_id="head_regeneration",
                name="머리 재생",
                description="잘린 머리가 재생되며 HP를 회복한다.",
                target_type=SkillTargetType.SELF,
                heal_amount=50,
                use_probability=0.5,
                min_hp_percent=0.0,
                max_hp_percent=0.7,
                cooldown=3
            ),
            "multi_bite": EnemySkill(
                skill_id="multi_bite",
                name="다중 물어뜯기",
                description="여러 머리로 동시에 공격한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                damage_multiplier=1.8,
                brv_damage=1,
                hp_attack=True,
                use_probability=0.4,
                cooldown=3
            ),
            "toxic_breath": EnemySkill(
                skill_id="toxic_breath",
                name="맹독 숨결",
                description="맹독 가스를 뿜어낸다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=25,
                damage_multiplier=1.6,
                brv_damage=1,
                status_effects=["poison", "weakness"],
                status_duration=4,
                status_intensity=0.4,  # toxic_breath 맞춤 강도
                use_probability=0.35,
                cooldown=3
            ),

            # === 드래곤 타입 스킬 (12개) ===

            # 화염 드래곤 스킬
            "fire_breath": EnemySkill(
                skill_id="fire_breath",
                name="화염 브레스",
                description="강렬한 불꽃을 뿜어낸다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=35,
                damage_multiplier=2.2,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn"],
                status_duration=3,
                status_intensity=0.36,  # fire_breath 맞춤 강도
                use_probability=0.4,
                cooldown=3
            ),
            "inferno": EnemySkill(
                skill_id="inferno",
                name="용염 폭발",
                description="폭발적인 화염으로 모든 것을 불태운다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=40,
                damage_multiplier=2.5,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn", "weakness"],
                status_duration=3,
                status_intensity=0.4,  # inferno 맞춤 강도
                use_probability=0.3,
                cooldown=5
            ),
            "wing_attack": EnemySkill(
                skill_id="wing_attack",
                name="날개 공격",
                description="강력한 날개로 적들을 쓸어버린다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                damage_multiplier=1.9,
                brv_damage=1,
                hp_attack=True,
                use_probability=0.35,
                cooldown=3
            ),

            # 빙룡 스킬
            "frost_breath": EnemySkill(
                skill_id="frost_breath",
                name="빙결 브레스",
                description="모든 것을 얼리는 냉기를 뿜어낸다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=35,
                damage_multiplier=2.2,
                brv_damage=1,
                hp_attack=True,
                status_effects=["freeze", "slow"],
                status_duration=2,
                status_intensity=0.4,  # frost_breath 맞춤 강도
                use_probability=0.4,
                cooldown=3
            ),
            "snowstorm": EnemySkill(
                skill_id="snowstorm",
                name="눈보라",
                description="거대한 눈보라를 일으킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=30,
                damage_multiplier=1.9,
                brv_damage=1,
                status_effects=["slow"],
                status_duration=3,
                status_intensity=0.4,  # snowstorm 맞춤 강도
                use_probability=0.35,
                cooldown=4
            ),
            "ice_wing": EnemySkill(
                skill_id="ice_wing",
                name="얼음 날개",
                description="얼음 결정을 날개로 발사한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                mp_cost=25,
                damage_multiplier=2.4,
                brv_damage=1,
                hp_attack=True,
                use_probability=0.35,
                cooldown=2
            ),

            # 독 드래곤 스킬
            "poison_breath": EnemySkill(
                skill_id="poison_breath_dragon",
                name="독 브레스",
                description="맹독 가스를 대량으로 뿜어낸다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=35,
                damage_multiplier=2.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["poison", "weakness"],
                status_duration=5,
                status_intensity=0.25,  # poison_breath 조정
                use_probability=0.4,
                cooldown=3
            ),
            "toxic_cloud": EnemySkill(
                skill_id="toxic_cloud",
                name="독무",
                description="독성 구름을 만들어 적들을 약화시킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=30,
                damage_multiplier=1.5,
                brv_damage=1,
                debuff_stats={"strength": 0.6, "defense": 0.6, "speed": 0.7},
                status_effects=["poison"],
                status_duration=4,
                status_intensity=0.4,  # toxic_cloud 맞춤 강도
                use_probability=0.35,
                cooldown=4
            ),
            "decay_breath": EnemySkill(
                skill_id="decay_breath",
                name="부패의 숨결",
                description="부패의 기운으로 적들을 약화시킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=25,
                damage_multiplier=1.7,
                brv_damage=1,
                status_effects=["curse", "disease"],
                status_duration=4,
                status_intensity=0.4,  # decay_breath 맞춤 강도
                use_probability=0.35,
                cooldown=3
            ),

            # 고룡 스킬
            "elder_dragon_roar": EnemySkill(
                skill_id="elder_dragon_roar",
                name="고룡의 포효",
                description="고대 드래곤의 포효로 적들을 압도한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                debuff_stats={"strength": 0.5, "defense": 0.5, "magic": 0.5, "spirit": 0.5, "speed": 0.6},
                status_effects=["fear"],
                status_duration=3,
                status_intensity=0.5,  # elder_dragon_roar 맞춤 강도
                use_probability=0.3,
                cooldown=5
            ),
            "elemental_breath": EnemySkill(
                skill_id="elemental_breath",
                name="원소 브레스",
                description="모든 원소의 힘을 담은 브레스를 발사한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=45,
                damage_multiplier=2.6,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn", "freeze", "poison"],
                status_duration=2,
                status_intensity=0.45,  # elemental_breath 맞춤 강도
                use_probability=0.2,
                cooldown=4
            ),
            "dragon_dive": EnemySkill(
                skill_id="dragon_dive",
                name="드래곤 다이브",
                description="하늘에서 급강하하여 강력한 일격을 가한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=3.0,
                brv_damage=1,
                hp_attack=True,
                use_probability=0.3,
                cooldown=5
            ),

            # === 악마 타입 스킬 (12개) ===

            # 임프 스킬
            "imp_fireball": EnemySkill(
                skill_id="imp_fireball",
                name="화염구",
                description="작은 화염구를 발사한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                mp_cost=15,
                damage_multiplier=1.7,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn"],
                status_duration=2,
                status_intensity=0.36,  # imp_fireball 맞춤 강도
                use_probability=0.4,
                cooldown=1
            ),
            "blink": EnemySkill(
                skill_id="blink",
                name="순간이동",
                description="순간이동하여 회피율을 높인다.",
                target_type=SkillTargetType.SELF,
                mp_cost=10,
                buff_stats={"speed": 2.0},
                use_probability=0.3,
                cooldown=4
            ),
            "mana_steal": EnemySkill(
                skill_id="mana_steal",
                name="마법 도둑",
                description="적의 MP를 훔쳐온다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                mp_cost=10,
                damage_multiplier=1.2,
                brv_damage=1,
                heal_amount=30,  # MP 회복
                use_probability=0.35,
                cooldown=3
            ),

            # 서큐버스 스킬
            "charm": EnemySkill(
                skill_id="charm",
                name="매혹",
                description="적을 매혹하여 혼란에 빠뜨린다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                mp_cost=25,
                status_effects=["charm", "confusion"],
                status_duration=3,
                status_intensity=0.38,  # charm 맞춤 강도
                use_probability=0.4,
                cooldown=4
            ),
            "life_siphon": EnemySkill(
                skill_id="life_siphon",
                name="생명력 흡수",
                description="적의 생명력을 빨아들인다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                mp_cost=20,
                damage_multiplier=1.9,
                brv_damage=1,
                hp_attack=True,
                heal_amount=50,
                use_probability=0.45,
                cooldown=2
            ),
            "demon_kiss": EnemySkill(
                skill_id="demon_kiss",
                name="악마의 키스",
                description="악마의 키스로 적을 저주한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                mp_cost=30,
                damage_multiplier=2.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["curse", "charm", "weakness"],
                status_duration=4,
                status_intensity=0.5,  # demon_kiss 맞춤 강도
                use_probability=0.3,
                cooldown=5
            ),

            # 발록 스킬
            "balrog_flame": EnemySkill(
                skill_id="balrog_flame",
                name="발록의 화염",
                description="발록의 강력한 화염을 뿜어낸다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=40,
                damage_multiplier=2.4,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn"],
                status_duration=3,
                status_intensity=0.36,  # balrog_flame 맞춤 강도
                use_probability=0.4,
                cooldown=3
            ),
            "flame_whip": EnemySkill(
                skill_id="flame_whip",
                name="염옥의 채찍",
                description="불타는 채찍으로 적을 공격한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                mp_cost=30,
                damage_multiplier=2.6,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn", "bleed"],
                status_duration=3,
                status_intensity=0.36,  # flame_whip 맞춤 강도
                use_probability=0.35,
                cooldown=3
            ),
            "infernal_explosion": EnemySkill(
                skill_id="infernal_explosion",
                name="지옥불 폭발",
                description="지옥불을 폭발시켜 모든 적을 공격한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=50,
                damage_multiplier=2.8,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn", "curse"],
                status_duration=3,
                status_intensity=0.4,  # infernal_explosion 맞춤 강도
                use_probability=0.3,
                cooldown=5
            ),

            # 대악마 스킬
            "hand_of_doom": EnemySkill(
                skill_id="hand_of_doom",
                name="멸망의 손길",
                description="멸망의 손길로 적을 파멸시킨다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                mp_cost=45,
                damage_multiplier=3.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["doom", "curse"],
                status_duration=5,
                status_intensity=0.42,  # hand_of_doom 맞춤 강도
                use_probability=0.35,
                cooldown=4
            ),
            "corruption": EnemySkill(
                skill_id="corruption",
                name="타락",
                description="적을 타락시켜 모든 능력치를 감소시킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=40,
                debuff_stats={"strength": 0.5, "defense": 0.5, "magic": 0.5, "spirit": 0.5, "speed": 0.5},
                status_effects=["curse"],
                status_duration=5,
                status_intensity=0.4,  # corruption 맞춤 강도
                use_probability=0.3,
                cooldown=6
            ),
            "demon_lord_summon": EnemySkill(
                skill_id="demon_lord_summon",
                name="악마군주 소환",
                description="악마 군주의 힘을 빌려 압도적인 힘을 얻는다.",
                target_type=SkillTargetType.SELF,
                hp_cost=50,
                mp_cost=50,
                buff_stats={"strength": 2.5, "magic": 2.5, "speed": 1.8},
                use_probability=0.2,
                min_hp_percent=0.0,
                max_hp_percent=0.3,
                cooldown=99  # 한 번만
            ),

            # === 기계/골렘 타입 스킬 (9개) ===

            # 강철 골렘 스킬
            "steel_fist": EnemySkill(
                skill_id="steel_fist",
                name="강철 주먹",
                description="강철 주먹으로 적을 내려친다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.5,
                brv_damage=1,
                hp_attack=True,
                status_effects=["stun"],
                status_duration=1,
                status_intensity=0.4,  # steel_fist 맞춤 강도
                use_probability=0.4,
                cooldown=2
            ),
            "iron_wall": EnemySkill(
                skill_id="iron_wall",
                name="철벽 방어",
                description="철벽 같은 방어력을 얻는다.",
                target_type=SkillTargetType.SELF,
                buff_stats={"defense": 2.5, "spirit": 1.8},
                use_probability=0.35,
                cooldown=5
            ),
            "quake_slam": EnemySkill(
                skill_id="quake_slam",
                name="지진 강타",
                description="땅을 내리쳐 지진을 일으킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                damage_multiplier=2.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["slow"],
                status_duration=2,
                status_intensity=0.4,  # quake_slam 맞춤 강도
                use_probability=0.3,
                cooldown=4
            ),

            # 수정 골렘 스킬
            "magic_reflect": EnemySkill(
                skill_id="magic_reflect",
                name="마법 반사",
                description="마법 공격을 반사하는 방벽을 만든다.",
                target_type=SkillTargetType.SELF,
                mp_cost=25,
                buff_stats={"spirit": 2.0},
                counter_damage=True,  # 마법 반격
                use_probability=0.4,
                cooldown=4
            ),
            "crystal_beam": EnemySkill(
                skill_id="crystal_beam",
                name="수정 광선",
                description="수정의 빛을 발사하여 적을 공격한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                mp_cost=20,
                damage_multiplier=2.3,
                brv_damage=1,
                hp_attack=True,
                use_probability=0.4,
                cooldown=2
            ),
            "prism_barrier": EnemySkill(
                skill_id="prism_barrier",
                name="프리즘 장벽",
                description="프리즘 장벽으로 마법 방어력을 극대화한다.",
                target_type=SkillTargetType.SELF,
                mp_cost=30,
                buff_stats={"spirit": 2.5, "defense": 1.5},
                shield_amount=60,
                use_probability=0.3,
                cooldown=5
            ),

            # 고대 자동인형 스킬
            "laser_beam": EnemySkill(
                skill_id="laser_beam",
                name="레이저 빔",
                description="강력한 레이저 광선을 발사한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                mp_cost=25,
                damage_multiplier=2.6,
                brv_damage=1,
                hp_attack=True,
                use_probability=0.4,
                cooldown=2
            ),
            "overload": EnemySkill(
                skill_id="overload",
                name="과부하",
                description="시스템을 과부하시켜 강력한 공격을 가한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                hp_cost=40,
                mp_cost=30,
                damage_multiplier=2.8,
                brv_damage=1,
                hp_attack=True,
                use_probability=0.25,
                cooldown=5
            ),
            "self_destruct_mode": EnemySkill(
                skill_id="self_destruct_mode",
                name="자폭 모드",
                description="자폭하여 모든 적에게 큰 피해를 입힌다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                hp_cost=999,  # 자폭
                damage_multiplier=3.5,
                brv_damage=1,
                hp_attack=True,
                use_probability=0.1,
                min_hp_percent=0.0,
                max_hp_percent=0.2,  # HP 20% 이하
                cooldown=99
            ),

            # === 특수 타입 스킬 (3개) ===

            # 미믹 스킬
            "surprise_attack": EnemySkill(
                skill_id="surprise_attack",
                name="기습 공격",
                description="상자인 척하다가 기습 공격을 가한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.8,
                brv_damage=1,
                hp_attack=True,
                status_effects=["stun"],
                status_duration=1,
                status_intensity=0.4,  # surprise_attack 맞춤 강도
                use_probability=0.3,
                cooldown=3
            ),
            "treasure_lure": EnemySkill(
                skill_id="treasure_lure",
                name="보물 미끼",
                description="보물을 미끼로 적을 유인하여 공격한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.2,
                brv_damage=1,
                hp_attack=True,
                status_effects=["confusion"],
                status_duration=2,
                status_intensity=0.4,  # treasure_lure 맞춤 강도
                use_probability=0.35,
                cooldown=3
            ),

            # 나이트메어 스킬
            "nightmare_vision": EnemySkill(
                skill_id="nightmare_vision",
                name="악몽의 환영",
                description="악몽을 보여주어 적들을 공포에 떨게 한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                mp_cost=35,
                damage_multiplier=2.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["fear", "confusion", "curse"],
                status_duration=3,
                status_intensity=0.4,  # nightmare_vision 맞춤 강도
                use_probability=0.4,
                cooldown=4
            ),
            "dream_eater": EnemySkill(
                skill_id="dream_eater",
                name="꿈 포식",
                description="적의 꿈을 먹어치워 HP와 MP를 회복한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                mp_cost=25,
                damage_multiplier=2.3,
                brv_damage=1,
                hp_attack=True,
                heal_amount=60,  # HP + MP 회복
                use_probability=0.35,
                cooldown=3
            ),
            "sleep_eternal": EnemySkill(
                skill_id="sleep_eternal",
                name="영원한 잠",
                description="적을 영원한 잠에 빠뜨린다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                mp_cost=40,
                status_effects=["sleep", "doom"],
                status_duration=2,
                status_intensity=0.38,  # sleep_eternal 맞춤 강도
                use_probability=0.15,
                cooldown=6
            ),

            # === 세피로스 전용 스킬 (15층 보스) ===

            # 슈퍼노바
            "supernova": EnemySkill(
                skill_id="supernova",
                name="슈퍼노바",
                description="초신성 폭발로 모든 것을 집어삼킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                damage=0,  # BRV 시스템 사용
                damage_multiplier=3.0,  # 궁극기 최대 배율
                brv_damage=1,
                hp_attack=True,  # BRV+HP 공격
                is_magical=True,
                mp_cost=50,
                status_effects=["stun"],
                status_duration=1,
                status_intensity=0.4,  # supernova 맞춤 강도
                use_probability=0.2,
                cooldown=7
            ),

            # 페로 카오스
            "heartless_angel": EnemySkill(
                skill_id="heartless_angel",
                name="페로 카오스",
                description="대상의 HP를 1로 만든다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage=99999,  # 특수 처리: HP를 1로 만듦
                damage_multiplier=1.0,
                is_magical=True,
                mp_cost=40,
                use_probability=0.15,
                cooldown=6
            ),

            # 옥토 슬래시
            "octaslash": EnemySkill(
                skill_id="octaslash",
                name="옥토 슬래시",
                description="8번의 연속 베기로 적을 갈기갈기 찢는다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage=0,  # BRV 시스템 사용
                damage_multiplier=2.8,  # 8연타 궁극기
                brv_damage=1,
                hp_attack=True,  # BRV+HP 공격
                use_probability=0.25,
                cooldown=4
            ),

            # 섀도우 플레어
            "shadow_flare": EnemySkill(
                skill_id="shadow_flare",
                name="섀도우 플레어",
                description="어둠의 불꽃이 적 전체를 집어삼킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                damage=0,  # BRV 시스템 사용
                damage_multiplier=2.5,  # 강력한 전체 마법
                brv_damage=1,
                hp_attack=True,  # BRV+HP 공격
                is_magical=True,
                mp_cost=35,
                status_effects=["darkness", "silence"],
                status_duration=2,
                status_intensity=0.42,  # shadow_flare 맞춤 강도
                use_probability=0.2,
                cooldown=5
            ),

            # 디스페어
            "despair": EnemySkill(
                skill_id="despair",
                name="절망",
                description="절망감을 불러일으켜 적들의 모든 능력치를 약화시킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                debuff_stats={
                    "strength": 0.5,
                    "defense": 0.5,
                    "magic": 0.5,
                    "spirit": 0.5,
                    "speed": 0.5
                },
                use_probability=0.2,
                min_hp_percent=0.0,
                max_hp_percent=0.3,  # HP 30% 이하일 때
                cooldown=8
            ),

            # ============================================================
            # === 신규 적 스킬 (언데드 타입) ===
            # ============================================================
            
            # 좀비 스킬
            "infected_strike": EnemySkill(
                skill_id="infected_strike",
                name="감염된 일격",
                description="썩어가는 손으로 적을 감염시킨다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=1.4,
                brv_damage=1,
                hp_attack=True,
                status_effects=["disease", "poison"],
                status_duration=3,
                status_intensity=0.3,  # infected_strike 조정
                use_probability=0.4,
                cooldown=2,
                sfx=("combat", "attack_physical")
            ),
            "zombify": EnemySkill(
                skill_id="zombify",
                name="좀비화",
                description="공포스러운 좀비 독이 퍼진다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=1.0,
                brv_damage=1,
                status_effects=["slow", "reduce_def"],
                status_duration=4,
                status_intensity=0.3,  # zombify 조정
                use_probability=0.3,
                cooldown=4
            ),
            "undead_resilience": EnemySkill(
                skill_id="undead_resilience",
                name="불사의 끈기",
                description="언데드의 생명력으로 회복한다.",
                target_type=SkillTargetType.SELF,
                heal_amount=40,
                buff_stats={"defense": 1.3},
                use_probability=0.35,
                min_hp_percent=0.0,
                max_hp_percent=0.4,
                cooldown=5
            ),

            # 구울 스킬
            "corpse_eater": EnemySkill(
                skill_id="corpse_eater",
                name="시체 포식",
                description="적을 물어뜯어 HP를 회복한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=1.8,
                brv_damage=1,
                hp_attack=True,
                heal_amount=30,
                use_probability=0.4,
                cooldown=3,
                sfx=("combat", "attack_physical")
            ),
            "frenzy": EnemySkill(
                skill_id="frenzy",
                name="광란",
                description="피에 굶주려 광폭해진다.",
                target_type=SkillTargetType.SELF,
                buff_stats={"strength": 1.6, "speed": 1.4, "defense": 0.8},
                use_probability=0.3,
                cooldown=5
            ),
            "swift_assault": EnemySkill(
                skill_id="swift_assault",
                name="신속 습격",
                description="빠른 속도로 연속 공격한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.4,
                brv_damage=1,
                hp_attack=True,
                use_probability=0.35,
                cooldown=3
            ),

            # 밴시 스킬
            "wail": EnemySkill(
                skill_id="wail",
                name="비명",
                description="귀를 찢는 비명으로 적을 마비시킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=1.2,
                brv_damage=1,
                status_effects=["stun"],
                status_duration=1,
                status_intensity=0.4,  # wail 조정
                use_probability=0.2,
                cooldown=4,
                sfx=("skill", "roar")
            ),
            "cursed_scream": EnemySkill(
                skill_id="cursed_scream",
                name="저주받은 비명",
                description="저주를 담은 비명이 적을 괴롭힌다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=1.8,
                brv_damage=1,
                hp_attack=True,
                status_effects=["curse", "silence"],
                status_duration=2,
                status_intensity=0.425,  # cursed_scream 조정
                use_probability=0.2,
                cooldown=4
            ),
            "soul_steal": EnemySkill(
                skill_id="soul_steal",
                name="영혼 흡수",
                description="적의 영혼 일부를 흡수하여 자신을 강화한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                damage_multiplier=2.0,
                brv_damage=1,
                hp_attack=True,
                heal_amount=40,
                debuff_stats={"magic": 0.7, "spirit": 0.7},
                use_probability=0.35,
                cooldown=4
            ),

            # 데스나이트 스킬
            "dark_slash": EnemySkill(
                skill_id="dark_slash",
                name="암흑 베기",
                description="어둠의 힘을 담은 검격.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.2,
                brv_damage=1,
                hp_attack=True,
                status_effects=["darkness"],
                status_duration=3,
                status_intensity=0.42,  # dark_slash 조정
                use_probability=0.4,
                cooldown=2
            ),
            "death_sentence": EnemySkill(
                skill_id="death_sentence",
                name="사형 선고",
                description="죽음의 선고를 내려 시한부 상태로 만든다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                status_effects=["doom"],
                status_duration=5,
                status_intensity=0.45,  # death_sentence 조정
                use_probability=0.25,
                cooldown=6
            ),
            "dark_aura": EnemySkill(
                skill_id="dark_aura",
                name="암흑 오라",
                description="어둠의 오라가 아군을 강화한다.",
                target_type=SkillTargetType.ALL_ALLIES,
                buff_stats={"strength": 1.3, "magic": 1.3},
                use_probability=0.25,
                cooldown=5
            ),

            # 미라 스킬
            "ancient_curse": EnemySkill(
                skill_id="ancient_curse",
                name="고대의 저주",
                description="고대의 저주가 적을 옭아맨다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                damage_multiplier=1.5,
                brv_damage=1,
                status_effects=["curse", "slow", "reduce_def"],
                status_duration=4,
                status_intensity=0.425,  # ancient_curse 조정
                use_probability=0.35,
                cooldown=4
            ),
            "bandage_wrap": EnemySkill(
                skill_id="bandage_wrap",
                name="붕대 속박",
                description="붕대로 적을 휘감아 구속한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                status_effects=["root", "blind"],
                status_duration=2,
                status_intensity=0.35,  # bandage_wrap 조정
                use_probability=0.35,
                cooldown=3
            ),

            # ============================================================
            # === 신규 적 스킬 (엘리멘탈 타입) ===
            # ============================================================
            
            # 화염 정령 스킬
            "flame_burst": EnemySkill(
                skill_id="flame_burst",
                name="화염 폭발",
                description="화염이 폭발하여 적을 불태운다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                damage_multiplier=2.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn"],
                status_duration=3,
                status_intensity=0.36,  # flame_burst 조정
                use_probability=0.45,
                cooldown=2,
                sfx=("skill", "fire")
            ),
            "fire_shield": EnemySkill(
                skill_id="fire_shield",
                name="화염 방패",
                description="화염의 방패가 공격자를 불태운다.",
                target_type=SkillTargetType.SELF,
                buff_stats={"defense": 1.5},
                shield_amount=40,
                counter_damage=True,
                use_probability=0.3,
                cooldown=4
            ),
            "lava_eruption": EnemySkill(
                skill_id="lava_eruption",
                name="용암 분출",
                description="용암이 솟구쳐 전체를 공격한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=2.3,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn"],
                status_duration=2,
                status_intensity=0.45,  # lava_eruption 조정
                use_probability=0.3,
                cooldown=5
            ),

            # 빙결 정령 스킬
            "absolute_zero": EnemySkill(
                skill_id="absolute_zero",
                name="절대 영도",
                description="모든 것을 얼려버리는 극한의 추위.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=2.2,
                brv_damage=1,
                hp_attack=True,
                status_effects=["freeze"],
                status_duration=1,
                status_intensity=0.45,  # absolute_zero 조정
                use_probability=0.25,
                cooldown=5,
                sfx=("skill", "ice")
            ),
            "ice_prison": EnemySkill(
                skill_id="ice_prison",
                name="얼음 감옥",
                description="적을 얼음 감옥에 가둔다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                damage_multiplier=1.6,
                brv_damage=1,
                status_effects=["freeze", "slow"],
                status_duration=2,
                status_intensity=0.4,  # ice_prison 맞춤 강도
                use_probability=0.2,
                cooldown=4
            ),
            "blizzard": EnemySkill(
                skill_id="blizzard",
                name="블리자드",
                description="눈보라가 적을 덮친다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=1.8,
                brv_damage=1,
                status_effects=["slow", "chill"],
                status_duration=3,
                status_intensity=0.45,  # blizzard 조정
                use_probability=0.35,
                cooldown=3
            ),

            # 번개 정령 스킬
            "chain_lightning": EnemySkill(
                skill_id="chain_lightning",
                name="연쇄 번개",
                description="번개가 적들 사이를 연쇄한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=1.7,
                brv_damage=1,
                hp_attack=True,
                status_effects=["paralyze"],
                status_duration=1,
                status_intensity=0.38,  # chain_lightning 조정
                use_probability=0.4,
                cooldown=3,
                sfx=("skill", "lightning")
            ),
            "static_field": EnemySkill(
                skill_id="static_field",
                name="정전기장",
                description="정전기장이 적의 움직임을 방해한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                debuff_stats={"speed": 0.6},
                status_effects=["shock"],
                status_duration=3,
                status_intensity=0.4,  # static_field 조정
                use_probability=0.3,
                cooldown=4
            ),
            "thunderbolt": EnemySkill(
                skill_id="thunderbolt",
                name="벼락",
                description="강력한 벼락이 적을 내리친다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                damage_multiplier=2.8,
                brv_damage=1,
                hp_attack=True,
                status_effects=["stun"],
                status_duration=1,
                status_intensity=0.38,  # thunderbolt 맞춤 강도
                use_probability=0.35,
                cooldown=4
            ),

            # 대지 정령 스킬
            "rock_throw": EnemySkill(
                skill_id="rock_throw",
                name="바위 던지기",
                description="거대한 바위를 던져 공격한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.3,
                brv_damage=1,
                hp_attack=True,
                status_effects=["stun"],
                status_duration=1,
                status_intensity=0.4,  # rock_throw 맞춤 강도
                use_probability=0.4,
                cooldown=3
            ),
            "earth_barrier": EnemySkill(
                skill_id="earth_barrier",
                name="대지의 방벽",
                description="대지가 솟아올라 방벽을 형성한다.",
                target_type=SkillTargetType.SELF,
                buff_stats={"defense": 1.8},
                shield_amount=60,
                use_probability=0.35,
                cooldown=5
            ),
            "earthquake": EnemySkill(
                skill_id="earthquake",
                name="지진",
                description="대지를 흔들어 모두를 공격한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                damage_multiplier=2.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["stun"],
                status_duration=1,
                status_intensity=0.5,  # earthquake 조정
                use_probability=0.3,
                cooldown=5
            ),

            # 바람 정령 스킬
            "vacuum_wave": EnemySkill(
                skill_id="vacuum_wave",
                name="진공파",
                description="진공 상태의 충격파가 적을 덮친다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=1.6,
                brv_damage=1,
                status_effects=["silence"],
                status_duration=2,
                status_intensity=0.4,  # vacuum_wave 맞춤 강도
                use_probability=0.2,
                cooldown=3
            ),
            "gust": EnemySkill(
                skill_id="gust",
                name="돌풍",
                description="강한 돌풍이 적을 휩쓸어간다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=1.4,
                brv_damage=1,
                debuff_stats={"accuracy": 0.7},
                use_probability=0.4,
                cooldown=2
            ),
            "tornado": EnemySkill(
                skill_id="tornado",
                name="토네이도",
                description="강력한 회오리가 적들을 집어삼킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=2.2,
                brv_damage=1,
                hp_attack=True,
                status_effects=["confusion"],
                status_duration=2,
                status_intensity=0.45,  # tornado 조정
                use_probability=0.3,
                cooldown=5
            ),

            # 암흑 정령 스킬
            "dark_orb": EnemySkill(
                skill_id="dark_orb",
                name="암흑 구체",
                description="어둠의 구체가 적을 집어삼킨다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                damage_multiplier=2.2,
                brv_damage=1,
                hp_attack=True,
                status_effects=["darkness", "curse"],
                status_duration=3,
                status_intensity=0.42,  # dark_orb 맞춤 강도
                use_probability=0.4,
                cooldown=3
            ),
            "shadow_veil": EnemySkill(
                skill_id="shadow_veil",
                name="그림자 장막",
                description="그림자에 몸을 숨긴다.",
                target_type=SkillTargetType.SELF,
                buff_stats={"evasion": 1.5, "speed": 1.3},
                use_probability=0.3,
                cooldown=4
            ),
            "dark_curse": EnemySkill(
                skill_id="dark_curse",
                name="암흑 저주",
                description="강력한 저주가 적을 약화시킨다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                debuff_stats={"strength": 0.6, "magic": 0.6, "defense": 0.7},
                status_effects=["curse"],
                status_duration=4,
                status_intensity=0.42,  # dark_curse 맞춤 강도
                use_probability=0.35,
                cooldown=4
            ),

            # ============================================================
            # === 신규 적 스킬 (야수/몬스터 타입) ===
            # ============================================================
            
            # 곰 스킬
            "bear_roar": EnemySkill(
                skill_id="bear_roar",
                name="곰의 포효",
                description="강력한 포효로 적을 위축시킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                debuff_stats={"strength": 0.8, "defense": 0.8},
                status_effects=["fear"],
                status_duration=2,
                status_intensity=0.4,  # bear_roar 맞춤 강도
                use_probability=0.35,
                cooldown=4,
                sfx=("skill", "roar")
            ),
            "claw_barrage": EnemySkill(
                skill_id="claw_barrage",
                name="발톱 난무",
                description="날카로운 발톱으로 연속 공격한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.5,
                brv_damage=1,
                hp_attack=True,
                status_effects=["bleed"],
                status_duration=3,
                status_intensity=0.4,  # claw_barrage 맞춤 강도
                use_probability=0.4,
                cooldown=3
            ),
            "overwhelming_force": EnemySkill(
                skill_id="overwhelming_force",
                name="압도적인 힘",
                description="압도적인 힘으로 적을 제압한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=3.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["stun"],
                status_duration=1,
                status_intensity=0.4,  # overwhelming_force 맞춤 강도
                use_probability=0.3,
                cooldown=5
            ),

            # 거미 스킬
            "web_trap": EnemySkill(
                skill_id="web_trap",
                name="거미줄 함정",
                description="끈적한 거미줄로 적을 속박한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                status_effects=["root", "slow"],
                status_duration=3,
                status_intensity=0.35,  # web_trap 조정
                use_probability=0.4,
                cooldown=3
            ),
            "venom_spray": EnemySkill(
                skill_id="venom_spray",
                name="독 분사",
                description="독액을 분사하여 적 전체를 중독시킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=1.4,
                brv_damage=1,
                status_effects=["poison"],
                status_duration=4,
                status_intensity=0.4,  # venom_spray 맞춤 강도
                use_probability=0.35,
                cooldown=4,
                sfx=("skill", "poison")
            ),
            "poisonous_fangs": EnemySkill(
                skill_id="poisonous_fangs",
                name="독송곳니",
                description="독이 묻은 송곳니로 물어뜯는다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=1.8,
                brv_damage=1,
                hp_attack=True,
                status_effects=["poison", "paralyze"],
                status_duration=2,
                status_intensity=0.3,  # poisonous_fangs 맞춤 강도
                use_probability=0.4,
                cooldown=2
            ),

            # 전갈 스킬
            "scorpion_sting": EnemySkill(
                skill_id="scorpion_sting",
                name="전갈의 침",
                description="맹독의 침으로 공격한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["poison", "paralyze"],
                status_duration=2,
                status_intensity=0.4,  # scorpion_sting 맞춤 강도
                use_probability=0.25,
                cooldown=2
            ),
            "pincer_attack": EnemySkill(
                skill_id="pincer_attack",
                name="집게 공격",
                description="강력한 집게로 적을 조른다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.2,
                brv_damage=1,
                hp_attack=True,
                status_effects=["reduce_def"],
                status_duration=3,
                status_intensity=0.4,  # pincer_attack 맞춤 강도
                use_probability=0.4,
                cooldown=3
            ),
            "deadly_venom": EnemySkill(
                skill_id="deadly_venom",
                name="치명적인 독",
                description="강력한 독이 적을 죽음의 문턱으로 몰아간다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                status_effects=["poison", "necrosis"],
                status_duration=5,
                status_intensity=0.4,  # deadly_venom 맞춤 강도
                use_probability=0.3,
                cooldown=5
            ),

            # 바실리스크 스킬
            "petrifying_gaze": EnemySkill(
                skill_id="petrifying_gaze",
                name="석화의 눈빛",
                description="눈빛으로 적을 돌로 만든다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                status_effects=["petrify"],
                status_duration=2,
                status_intensity=0.44,  # petrifying_gaze 맞춤 강도
                use_probability=0.3,
                cooldown=5
            ),
            "viper_fangs": EnemySkill(
                skill_id="viper_fangs",
                name="뱀 송곳니",
                description="맹독을 품은 송곳니로 물어뜯는다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["poison", "slow"],
                status_duration=3,
                status_intensity=0.4,  # viper_fangs 맞춤 강도
                use_probability=0.4,
                cooldown=3
            ),
            "paralyzing_stare": EnemySkill(
                skill_id="paralyzing_stare",
                name="마비의 응시",
                description="무시무시한 응시로 적을 마비시킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                status_effects=["paralyze", "fear"],
                status_duration=2,
                status_intensity=0.4,  # paralyzing_stare 맞춤 강도
                use_probability=0.2,
                cooldown=4
            ),

            # 케르베로스 스킬
            "triple_bite": EnemySkill(
                skill_id="triple_bite",
                name="세 머리의 물기",
                description="세 개의 머리가 동시에 물어뜯는다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=3.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["bleed"],
                status_duration=3,
                status_intensity=0.4,  # triple_bite 맞춤 강도
                use_probability=0.4,
                cooldown=3
            ),
            "hellfire_breath": EnemySkill(
                skill_id="hellfire_breath",
                name="지옥불 숨결",
                description="지옥의 불꽃을 뿜어낸다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=2.2,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn"],
                status_duration=3,
                status_intensity=0.36,  # hellfire_breath 맞춤 강도
                use_probability=0.35,
                cooldown=4
            ),
            "frenzied_howl": EnemySkill(
                skill_id="frenzied_howl",
                name="광란의 울부짖음",
                description="광폭한 울부짖음이 모든 것을 압도한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                damage_multiplier=1.8,
                brv_damage=1,
                status_effects=["fear", "confusion"],
                status_duration=2,
                debuff_stats={"defense": 0.7},
                use_probability=0.3,
                cooldown=5
            ),

            # 히드라 스킬
            "head_regeneration": EnemySkill(
                skill_id="head_regeneration",
                name="머리 재생",
                description="잘린 머리가 다시 자라난다.",
                target_type=SkillTargetType.SELF,
                heal_amount=80,
                buff_stats={"strength": 1.2},
                use_probability=0.4,
                min_hp_percent=0.0,
                max_hp_percent=0.5,
                cooldown=4
            ),
            "multi_bite": EnemySkill(
                skill_id="multi_bite",
                name="다중 물기",
                description="여러 머리가 동시에 공격한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                damage_multiplier=1.8,
                brv_damage=1,
                hp_attack=True,
                use_probability=0.4,
                cooldown=3
            ),
            "toxic_breath": EnemySkill(
                skill_id="toxic_breath",
                name="독성 숨결",
                description="맹독의 숨결을 뿜어낸다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=1.6,
                brv_damage=1,
                status_effects=["poison", "corrode"],
                status_duration=4,
                status_intensity=0.4,  # toxic_breath 맞춤 강도
                use_probability=0.35,
                cooldown=4
            ),

            # ============================================================
            # === 신규 적 스킬 (드래곤 타입) ===
            # ============================================================
            
            # 화염 드래곤 스킬
            "fire_breath": EnemySkill(
                skill_id="fire_breath",
                name="화염 브레스",
                description="뜨거운 화염을 뿜어낸다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=2.4,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn"],
                status_duration=3,
                status_intensity=0.36,  # fire_breath 맞춤 강도
                use_probability=0.4,
                cooldown=3,
                sfx=("skill", "fire")
            ),
            "inferno": EnemySkill(
                skill_id="inferno",
                name="인페르노",
                description="지옥의 화염이 모든 것을 집어삼킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=2.8,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn"],
                status_duration=4,
                status_intensity=0.4,  # inferno 맞춤 강도
                use_probability=0.25,
                cooldown=6
            ),
            "wing_attack": EnemySkill(
                skill_id="wing_attack",
                name="날개 공격",
                description="거대한 날개로 적을 후려친다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                damage_multiplier=1.8,
                brv_damage=1,
                hp_attack=True,
                status_effects=["stun"],
                status_duration=1,
                status_intensity=0.4,  # wing_attack 맞춤 강도
                use_probability=0.35,
                cooldown=3
            ),

            # 빙룡 스킬
            "frost_breath": EnemySkill(
                skill_id="frost_breath",
                name="서리 브레스",
                description="차가운 서리 숨결을 뿜어낸다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=2.3,
                brv_damage=1,
                hp_attack=True,
                status_effects=["freeze", "slow"],
                status_duration=2,
                status_intensity=0.4,  # frost_breath 맞춤 강도
                use_probability=0.4,
                cooldown=3
            ),
            "snowstorm": EnemySkill(
                skill_id="snowstorm",
                name="눈보라",
                description="강력한 눈보라가 휘몰아친다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=2.0,
                brv_damage=1,
                status_effects=["slow", "blind"],
                status_duration=3,
                debuff_stats={"speed": 0.6, "accuracy": 0.7},
                use_probability=0.35,
                cooldown=4
            ),
            "ice_wing": EnemySkill(
                skill_id="ice_wing",
                name="얼음 날개",
                description="얼음으로 뒤덮인 날개로 적을 베어낸다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.6,
                brv_damage=1,
                hp_attack=True,
                status_effects=["freeze"],
                status_duration=1,
                status_intensity=0.4,  # ice_wing 맞춤 강도
                use_probability=0.4,
                cooldown=3
            ),

            # 독룡 스킬
            "poison_breath_dragon": EnemySkill(
                skill_id="poison_breath_dragon",
                name="독 브레스",
                description="맹독의 숨결을 뿜어낸다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=2.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["poison", "necrosis"],
                status_duration=4,
                status_intensity=0.5,  # poison_breath_dragon 맞춤 강도
                use_probability=0.4,
                cooldown=3
            ),
            "toxic_cloud": EnemySkill(
                skill_id="toxic_cloud",
                name="독구름",
                description="독성 구름이 전장을 뒤덮는다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=1.5,
                brv_damage=1,
                status_effects=["poison", "slow"],
                status_duration=5,
                debuff_stats={"defense": 0.8, "spirit": 0.8},
                use_probability=0.35,
                cooldown=4
            ),
            "decay_breath": EnemySkill(
                skill_id="decay_breath",
                name="부패의 숨결",
                description="모든 것을 부패시키는 숨결.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=2.2,
                brv_damage=1,
                hp_attack=True,
                status_effects=["corrode", "disease"],
                status_duration=4,
                status_intensity=0.4,  # decay_breath 맞춤 강도
                use_probability=0.3,
                cooldown=5
            ),

            # 엘더 드래곤 스킬
            "elder_dragon_roar": EnemySkill(
                skill_id="elder_dragon_roar",
                name="태고의 포효",
                description="태고의 힘이 담긴 포효.",
                target_type=SkillTargetType.ALL_ENEMIES,
                damage_multiplier=2.0,
                brv_damage=1,
                status_effects=["fear", "reduce_def"],
                status_duration=3,
                debuff_stats={"strength": 0.7, "magic": 0.7, "defense": 0.7},
                use_probability=0.35,
                cooldown=4
            ),
            "elemental_breath": EnemySkill(
                skill_id="elemental_breath",
                name="원소 브레스",
                description="모든 원소의 힘이 담긴 숨결.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=3.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn", "freeze", "shock"],
                status_duration=2,
                status_intensity=0.45,  # elemental_breath 맞춤 강도
                use_probability=0.2,
                cooldown=5
            ),
            "dragon_dive": EnemySkill(
                skill_id="dragon_dive",
                name="드래곤 다이브",
                description="하늘에서 급강하하여 내리찍는다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=3.5,
                brv_damage=1,
                hp_attack=True,
                status_effects=["stun"],
                status_duration=2,
                status_intensity=0.5,  # dragon_dive 맞춤 강도
                use_probability=0.2,
                cooldown=5
            ),

            # ============================================================
            # === 신규 적 스킬 (악마 타입) ===
            # ============================================================
            
            # 임프 스킬
            "imp_fireball": EnemySkill(
                skill_id="imp_fireball",
                name="작은 화염구",
                description="작지만 뜨거운 화염구를 던진다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                damage_multiplier=1.6,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn"],
                status_duration=2,
                status_intensity=0.36,  # imp_fireball 맞춤 강도
                use_probability=0.45,
                cooldown=2
            ),
            "blink": EnemySkill(
                skill_id="blink",
                name="순간이동",
                description="순간이동하여 회피를 높인다.",
                target_type=SkillTargetType.SELF,
                buff_stats={"evasion": 1.6, "speed": 1.3},
                use_probability=0.35,
                cooldown=3
            ),
            "mana_steal": EnemySkill(
                skill_id="mana_steal",
                name="마나 흡수",
                description="적의 마나를 빼앗는다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                damage_multiplier=1.4,
                brv_damage=1,
                status_effects=["mp_drain"],
                status_duration=3,
                status_intensity=0.4,  # mana_steal 맞춤 강도
                use_probability=0.35,
                cooldown=4
            ),

            # 서큐버스 스킬
            "charm": EnemySkill(
                skill_id="charm",
                name="매혹",
                description="적을 매혹시켜 아군을 공격하게 만든다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                status_effects=["charm"],
                status_duration=2,
                status_intensity=0.38,  # charm 맞춤 강도
                use_probability=0.3,
                cooldown=5
            ),
            "life_siphon": EnemySkill(
                skill_id="life_siphon",
                name="생명력 흡수",
                description="적의 생명력을 빨아들인다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                damage_multiplier=2.0,
                brv_damage=1,
                hp_attack=True,
                heal_amount=50,
                use_probability=0.4,
                cooldown=3
            ),
            "demon_kiss": EnemySkill(
                skill_id="demon_kiss",
                name="악마의 입맞춤",
                description="치명적인 입맞춤으로 적을 약화시킨다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                damage_multiplier=1.8,
                brv_damage=1,
                hp_attack=True,
                status_effects=["charm", "curse"],
                status_duration=3,
                debuff_stats={"strength": 0.7, "magic": 0.7},
                use_probability=0.35,
                cooldown=4
            ),

            # 발로그 스킬
            "balrog_flame": EnemySkill(
                skill_id="balrog_flame",
                name="발로그의 화염",
                description="지옥의 불꽃이 타오른다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=2.6,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn"],
                status_duration=4,
                status_intensity=0.36,  # balrog_flame 맞춤 강도
                use_probability=0.35,
                cooldown=4
            ),
            "flame_whip": EnemySkill(
                skill_id="flame_whip",
                name="화염 채찍",
                description="불꽃 채찍으로 적을 후려친다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.4,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn", "reduce_def"],
                status_duration=3,
                status_intensity=0.36,  # flame_whip 맞춤 강도
                use_probability=0.4,
                cooldown=3
            ),
            "infernal_explosion": EnemySkill(
                skill_id="infernal_explosion",
                name="지옥 폭발",
                description="지옥의 에너지가 폭발한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=3.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn", "stun"],
                status_duration=2,
                status_intensity=0.4,  # infernal_explosion 맞춤 강도
                use_probability=0.15,
                cooldown=6
            ),

            # 아크피인드 스킬
            "hand_of_doom": EnemySkill(
                skill_id="hand_of_doom",
                name="파멸의 손",
                description="파멸의 손이 적을 움켜쥔다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                damage_multiplier=3.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["doom"],
                status_duration=4,
                status_intensity=0.42,  # hand_of_doom 맞춤 강도
                use_probability=0.3,
                cooldown=6
            ),
            "corruption": EnemySkill(
                skill_id="corruption",
                name="타락",
                description="악의 기운이 모든 것을 타락시킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                is_magical=True,
                damage_multiplier=2.0,
                brv_damage=1,
                status_effects=["curse", "confusion"],
                status_duration=4,
                debuff_stats={"strength": 0.6, "magic": 0.6, "defense": 0.6, "spirit": 0.6},
                use_probability=0.3,
                cooldown=5
            ),
            "demon_lord_summon": EnemySkill(
                skill_id="demon_lord_summon",
                name="마왕 소환",
                description="자신의 힘을 극대화한다.",
                target_type=SkillTargetType.SELF,
                buff_stats={"strength": 1.5, "magic": 1.5, "defense": 1.3, "speed": 1.3},
                heal_amount=100,
                use_probability=0.2,
                min_hp_percent=0.0,
                max_hp_percent=0.3,
                cooldown=8
            ),

            # ============================================================
            # === 신규 적 스킬 (기계/골렘 타입) ===
            # ============================================================
            
            # 철 골렘 스킬
            "steel_fist": EnemySkill(
                skill_id="steel_fist",
                name="강철 주먹",
                description="강철 주먹으로 적을 분쇄한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                damage_multiplier=2.6,
                brv_damage=1,
                hp_attack=True,
                status_effects=["stun"],
                status_duration=1,
                status_intensity=0.4,  # steel_fist 맞춤 강도
                use_probability=0.25,
                cooldown=3
            ),
            "iron_wall": EnemySkill(
                skill_id="iron_wall",
                name="철벽 방어",
                description="철벽같은 방어 자세를 취한다.",
                target_type=SkillTargetType.SELF,
                buff_stats={"defense": 2.0},
                shield_amount=80,
                use_probability=0.35,
                cooldown=5
            ),
            "quake_slam": EnemySkill(
                skill_id="quake_slam",
                name="지진 강타",
                description="땅을 내리쳐 지진을 일으킨다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                damage_multiplier=2.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["stun"],
                status_duration=1,
                status_intensity=0.4,  # quake_slam 맞춤 강도
                use_probability=0.3,
                cooldown=5
            ),

            # 크리스탈 골렘 스킬
            "magic_reflect": EnemySkill(
                skill_id="magic_reflect",
                name="마법 반사",
                description="마법을 반사하는 보호막을 생성한다.",
                target_type=SkillTargetType.SELF,
                buff_stats={"spirit": 2.0},
                shield_amount=60,
                counter_damage=True,
                use_probability=0.35,
                cooldown=4
            ),
            "crystal_beam": EnemySkill(
                skill_id="crystal_beam",
                name="크리스탈 빔",
                description="빛나는 수정 광선을 발사한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                damage_multiplier=2.4,
                brv_damage=1,
                hp_attack=True,
                use_probability=0.45,
                cooldown=2
            ),
            "prism_barrier": EnemySkill(
                skill_id="prism_barrier",
                name="프리즘 장벽",
                description="빛으로 이루어진 장벽을 생성한다.",
                target_type=SkillTargetType.ALL_ALLIES,
                buff_stats={"defense": 1.4, "spirit": 1.4},
                shield_amount=40,
                use_probability=0.3,
                cooldown=5
            ),

            # 고대 자동 인형 스킬
            "laser_beam": EnemySkill(
                skill_id="laser_beam",
                name="레이저 빔",
                description="고대 기술로 만들어진 레이저를 발사한다.",
                target_type=SkillTargetType.SINGLE_ENEMY,
                is_magical=True,
                damage_multiplier=3.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn"],
                status_duration=2,
                status_intensity=0.4,  # laser_beam 맞춤 강도
                use_probability=0.4,
                cooldown=4
            ),
            "overload": EnemySkill(
                skill_id="overload",
                name="과부하",
                description="동력을 과부하시켜 폭주한다.",
                target_type=SkillTargetType.SELF,
                hp_cost=50,
                buff_stats={"strength": 2.0, "magic": 2.0, "speed": 1.5},
                use_probability=0.25,
                min_hp_percent=0.0,
                max_hp_percent=0.5,
                cooldown=6
            ),
            "self_destruct_mode": EnemySkill(
                skill_id="self_destruct_mode",
                name="자폭 모드",
                description="자폭 모드를 활성화한다.",
                target_type=SkillTargetType.ALL_ENEMIES,
                hp_cost=999,  # 자폭이므로 자신의 HP 대부분 소모
                damage_multiplier=4.0,
                brv_damage=1,
                hp_attack=True,
                status_effects=["burn", "stun"],
                status_duration=2,
                status_intensity=0.4,  # self_destruct_mode 맞춤 강도
                use_probability=0.15,
                min_hp_percent=0.0,
                max_hp_percent=0.2,  # HP 20% 이하에서만 사용
                cooldown=99  # 한 번만 사용
            ),
        }

        logger.info(f"적 스킬 데이터베이스 초기화 완료: {len(cls.SKILLS)}개 스킬")

    @classmethod
    def get_skill(cls, skill_id: str) -> Optional[EnemySkill]:
        """스킬 가져오기"""
        cls.initialize()
        skill_template = cls.SKILLS.get(skill_id)
        if skill_template:
            # 복사본 반환 (쿨다운이 개별적으로 관리되도록)
            return EnemySkill(
                skill_id=skill_template.skill_id,
                name=skill_template.name,
                description=skill_template.description,
                target_type=skill_template.target_type,
                mp_cost=skill_template.mp_cost,
                hp_cost=skill_template.hp_cost,
                damage=skill_template.damage,
                damage_multiplier=skill_template.damage_multiplier,
                is_magical=skill_template.is_magical,
                brv_damage=skill_template.brv_damage,
                hp_attack=skill_template.hp_attack,
                status_effects=skill_template.status_effects.copy(),
                status_duration=skill_template.status_duration,
                buff_stats=skill_template.buff_stats.copy(),
                debuff_stats=skill_template.debuff_stats.copy(),
                heal_amount=skill_template.heal_amount,
                shield_amount=skill_template.shield_amount,
                counter_damage=skill_template.counter_damage,
                use_probability=skill_template.use_probability,
                cooldown=skill_template.cooldown,
                current_cooldown=0,
                min_hp_percent=skill_template.min_hp_percent,
                max_hp_percent=skill_template.max_hp_percent,
                requires_ally_count=skill_template.requires_ally_count
            )
        return None

    @classmethod
    def get_skills_for_enemy_type(cls, enemy_type: str) -> List[EnemySkill]:
        """
        적 타입별 스킬 목록

        Args:
            enemy_type: 적 타입 ("goblin", "orc", "dragon" 등)

        Returns:
            스킬 리스트
        """
        cls.initialize()

        # 적 타입별 스킬 매핑 (모든 적에게 스킬 추가)
        skill_mapping = {
            # === 기존 적 ===
            # 약한 적
            "slime": ["acid_spray", "slime_split"],
            "goblin": ["poison_stab", "goblin_flee"],
            "wolf": ["savage_bite", "pack_tactics"],

            # 일반 적
            "orc": ["heavy_strike", "war_cry"],
            "skeleton": ["life_drain"],
            "dark_mage": ["fireball", "shadow_flare", "ice_storm"],

            # 강한 적
            "ogre": ["crush", "rage", "heavy_strike"],
            "wraith": ["wail_of_terror", "soul_drain", "life_drain"],
            "golem": ["earth_shock", "petrify"],

            # 매우 강한 적
            "troll": ["heavy_strike", "regeneration", "crush"],
            "vampire": ["vampire_bite", "bat_form", "life_drain"],
            "wyvern": ["dive_attack", "poison_breath"],

            # 최상급 적
            "demon": ["hellfire", "demon_pact", "shadow_flare"],
            "dragon": ["dragon_breath", "dragon_intimidation", "dragon_flight"],

            # 보스
            "boss_chimera": ["dragon_breath", "heavy_strike", "regeneration"],
            "boss_lich": ["shadow_flare", "ice_storm", "life_drain", "wail_of_terror"],
            "boss_dragon_king": ["dragon_breath", "dragon_intimidation", "dragon_flight", "hellfire"],

            # 최종 보스
            "sephiroth": [
                "supernova",
                "heartless_angel",
                "octaslash",
                "shadow_flare",
                "despair"
            ],

            # === 새로운 적 ===
            # 언데드 타입
            "zombie": ["infected_strike", "zombify", "undead_resilience"],
            "ghoul": ["corpse_eater", "frenzy", "swift_assault"],
            "banshee": ["wail", "cursed_scream", "soul_steal"],
            "death_knight": ["dark_slash", "death_sentence", "dark_aura"],
            "mummy": ["ancient_curse", "bandage_wrap", "resurrection"],

            # 엘리멘탈 타입
            "fire_elemental": ["flame_burst", "fire_shield", "lava_eruption"],
            "ice_elemental": ["absolute_zero", "ice_prison", "blizzard"],
            "thunder_elemental": ["chain_lightning", "static_field", "thunderbolt"],
            "earth_elemental": ["rock_throw", "earth_barrier", "earthquake"],
            "wind_elemental": ["vacuum_wave", "gust", "tornado"],
            "dark_elemental": ["dark_orb", "shadow_veil", "dark_curse"],

            # 야수/몬스터 타입
            "bear": ["bear_roar", "claw_barrage", "overwhelming_force"],
            "spider": ["web_trap", "venom_spray", "poisonous_fangs"],
            "scorpion": ["scorpion_sting", "pincer_attack", "deadly_venom"],
            "basilisk": ["petrifying_gaze", "viper_fangs", "paralyzing_stare"],
            "cerberus": ["triple_bite", "hellfire_breath", "frenzied_howl"],
            "hydra": ["head_regeneration", "multi_bite", "toxic_breath"],

            # 드래곤 타입
            "fire_dragon": ["fire_breath", "inferno", "wing_attack"],
            "ice_dragon": ["frost_breath", "snowstorm", "ice_wing"],
            "poison_dragon": ["poison_breath_dragon", "toxic_cloud", "decay_breath"],
            "elder_dragon": ["elder_dragon_roar", "elemental_breath", "dragon_dive"],

            # 악마 타입
            "imp": ["imp_fireball", "blink", "mana_steal"],
            "succubus": ["charm", "life_siphon", "demon_kiss"],
            "balrog": ["balrog_flame", "flame_whip", "infernal_explosion"],
            "archfiend": ["hand_of_doom", "corruption", "demon_lord_summon"],

            # 기계/골렘 타입
            "iron_golem": ["steel_fist", "iron_wall", "quake_slam"],
            "crystal_golem": ["magic_reflect", "crystal_beam", "prism_barrier"],
            "ancient_automaton": ["laser_beam", "overload", "self_destruct_mode"],

            # 특수 타입
            "mimic": ["surprise_attack", "treasure_lure"],
            "nightmare": ["nightmare_vision", "dream_eater", "sleep_eternal"],
        }

        skill_ids = skill_mapping.get(enemy_type.lower(), [])
        skills = []

        for skill_id in skill_ids:
            skill = cls.get_skill(skill_id)
            if skill:
                skills.append(skill)

        return skills
