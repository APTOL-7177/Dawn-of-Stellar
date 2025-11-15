"""
적 고유 스킬 시스템

각 적 타입별로 고유한 스킬 정의
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional
from enum import Enum
import random

from src.core.logger import get_logger


logger = get_logger("enemy_skills")


class SkillTargetType(Enum):
    """스킬 대상 타입"""
    SINGLE_ENEMY = "single_enemy"  # 적 1명
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
                use_probability=0.35,
                cooldown=2
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
                cooldown=99  # 한 번만 사용
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
                cooldown=3
            ),

            # 오크 - 전투 함성
            "war_cry": EnemySkill(
                skill_id="war_cry",
                name="전투 함성",
                description="함성을 지르며 아군의 사기를 높인다.",
                target_type=SkillTargetType.ALL_ALLIES,
                buff_stats={"strength": 1.3, "defense": 1.2},
                use_probability=0.2,
                cooldown=5
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
                cooldown=4
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
                status_duration=3,
                use_probability=0.3,
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

        # 적 타입별 스킬 매핑
        skill_mapping = {
            "goblin": ["poison_stab", "goblin_flee"],
            "orc": ["heavy_strike", "war_cry"],
            "troll": ["heavy_strike", "regeneration"],
            "skeleton": ["life_drain"],
            "zombie": ["life_drain", "regeneration"],
            "mage": ["fireball", "ice_storm", "mana_burst"],
            "dark_mage": ["fireball", "shadow_flare", "mana_burst"],
            "dragon": ["dragon_breath", "dragon_intimidation", "dragon_flight"],
            "demon": ["hellfire", "demon_pact"],
            "sephiroth": [
                "supernova",
                "heartless_angel",
                "octaslash",
                "shadow_flare",
                "despair"
            ],
        }

        skill_ids = skill_mapping.get(enemy_type.lower(), [])
        skills = []

        for skill_id in skill_ids:
            skill = cls.get_skill(skill_id)
            if skill:
                skills.append(skill)

        return skills
