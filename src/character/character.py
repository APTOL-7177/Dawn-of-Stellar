"""
Character - 캐릭터 클래스

StatManager를 통합한 확장 가능한 캐릭터 시스템
YAML 기반 직업 데이터 로딩
"""

from typing import Dict, Any, Optional, List
from src.character.stats import StatManager, Stats, GrowthType
from src.character.character_loader import (
    load_character_data,
    get_base_stats,
    get_gimmick,
    get_traits,
    get_skills,
    get_bonuses
)
from src.character.trait_effects import get_trait_effect_manager
from src.core.event_bus import event_bus, Events
from src.core.logger import get_logger


class Character:
    """
    게임 캐릭터 클래스

    StatManager를 사용하여 모든 스탯을 관리합니다.
    """

    def __init__(
        self,
        name: str,
        character_class: str,
        level: int = 1,
        stats_config: Optional[Dict[str, Any]] = None
    ) -> None:
        self.name = name
        self.character_class = character_class
        self.job_id = character_class  # job_id는 character_class의 별칭
        self.level = level

        self.logger = get_logger("character")

        # YAML에서 직업 데이터 로드
        self.class_data = load_character_data(character_class)

        # job_name 설정 (YAML의 class_name)
        self.job_name = self.class_data.get('class_name', character_class)

        # StatManager 초기화
        if stats_config is None:
            stats_config = self._get_stats_from_yaml()

        self.stat_manager = StatManager(stats_config)

        # 현재 HP/MP (StatManager와 별도 관리)
        self.current_hp = self.max_hp
        self.current_mp = self.max_mp

        # 상처 시스템 (HP 데미지의 일부가 상처로 전환)
        self.wound = 0  # 누적된 상처 (최대 HP 감소)

        # 전투 관련
        self.current_brv = 0  # 현재 BRV (전투 중에만 사용)
        self.is_alive = True
        self.is_enemy = False  # 적 여부

        # 장비 (3가지 슬롯만 사용)
        self.equipment: Dict[str, Any] = {
            "weapon": None,
            "armor": None,
            "accessory": None
        }

        # 상태 효과 (간단한 구현)
        self.status_effects: List[Any] = []

        # 직업 기믹 초기화
        self.gimmick_data = get_gimmick(character_class)
        self.gimmick_type = self.gimmick_data.get("type") if self.gimmick_data else None
        self._initialize_gimmick()

        # 특성 (Trait) - YAML에서 로드
        self.available_traits = get_traits(character_class)
        self.active_traits: List[Any] = []

        # 특성별 스택 카운터
        self.defend_stack_count = 0  # 저격수 특성: 방어 시 증가, 공격 시 소비

        # 스킬 - 직업별로 등록된 스킬 가져오기
        self.skill_ids = self._get_class_skills(character_class)
        self._cached_skills = None  # 스킬 객체 캐시

        # 로그
        self.logger.info(f"캐릭터 생성: {self.name} ({self.character_class}), 스킬: {len(self.skill_ids)}개")

        # 이벤트 발행
        event_bus.publish(Events.CHARACTER_CREATED, {
            "character": self,
            "name": self.name,
            "class": self.character_class
        })

    def _get_stats_from_yaml(self) -> Dict[str, Any]:
        """YAML에서 스탯 설정을 가져옵니다."""
        base_stats = get_base_stats(self.character_class)

        # YAML 필드명 → Stats enum 매핑
        stat_mapping = {
            "hp": Stats.HP,
            "mp": Stats.MP,
            "init_brv": Stats.INIT_BRV,
            "max_brv": Stats.MAX_BRV,
            "physical_attack": Stats.STRENGTH,
            "physical_defense": Stats.DEFENSE,
            "magic_attack": Stats.MAGIC,
            "magic_defense": Stats.SPIRIT,
            "speed": Stats.SPEED,
        }

        stats_config = {}

        for yaml_key, stat_enum in stat_mapping.items():
            base_value = base_stats.get(yaml_key, 50)

            # 성장률 설정 (linear로 기초 스탯의 일정 %만큼 성장)
            if yaml_key == "hp":
                # HP: 레벨당 기초 HP의 11.5% 성장 (8~15% 범위)
                growth_rate = base_value * 0.115
                growth_type = "linear"
            elif yaml_key == "mp":
                # MP: 레벨당 기초 MP의 5% 성장 (최대 5 정도)
                growth_rate = base_value * 0.05
                growth_type = "linear"
            elif yaml_key == "init_brv":
                # init_brv: 레벨당 기초 값의 20% 성장 (비례 성장)
                growth_rate = base_value * 0.20
                growth_type = "linear"
            elif yaml_key == "max_brv":
                # max_brv: 레벨당 기초 값의 20% 성장 (비례 성장)
                growth_rate = base_value * 0.20
                growth_type = "linear"
            elif yaml_key in ["physical_attack", "magic_attack"]:
                # 공격/마법: 레벨당 기초 스탯의 20% 성장 (15~25% 범위)
                growth_rate = base_value * 0.20
                growth_type = "linear"
            elif yaml_key in ["physical_defense", "magic_defense"]:
                # 방어: 레벨당 기초 스탯의 20% 성장 (15~25% 범위)
                growth_rate = base_value * 0.20
                growth_type = "linear"
            elif yaml_key == "speed":
                # 속도: 레벨당 기초 스탯의 20% 성장 (15~25% 범위)
                growth_rate = base_value * 0.20
                growth_type = "linear"
            else:
                growth_rate = base_value * 0.10
                growth_type = "linear"

            stats_config[stat_enum] = {
                "base_value": base_value,
                "growth_rate": growth_rate,
                "growth_type": growth_type
            }

        # 추가 스탯 (YAML에 없는 것들)
        stats_config[Stats.LUCK] = {
            "base_value": 5,
            "growth_rate": 0.5,
            "growth_type": "linear"
        }
        stats_config[Stats.ACCURACY] = {
            "base_value": 100,
            "growth_rate": 2,
            "growth_type": "logarithmic"
        }
        stats_config[Stats.EVASION] = {
            "base_value": 10,
            "growth_rate": 1,
            "growth_type": "logarithmic"
        }

        return stats_config

    def _initialize_gimmick(self) -> None:
        """직업별 기믹 시스템을 초기화합니다."""
        if not self.gimmick_data:
            return

        gimmick_type = self.gimmick_data.get("type")

        # 전사 - 6단계 스탠스 시스템
        if gimmick_type == "stance_system":
            self.current_stance = "balanced"
            self.stance_focus = 0
            self.available_stances = [s['id'] for s in self.gimmick_data.get('stances', [])]

        # 아크메이지 / 마법사 - 원소 카운터 시스템
        # 화염/빙결/번개 원소를 각각 최대 5개까지 축적하여 강력한 복합 마법 시전
        elif gimmick_type == "elemental_counter":
            self.fire_element = 0
            self.ice_element = 0
            self.lightning_element = 0

        # 궁수/저격수 - 조준 포인트
        elif gimmick_type == "aim_system":
            self.aim_points = 0
            self.max_aim_points = self.gimmick_data.get("max_aim", 5)
            self.focus_stacks = 0  # 집중 스택 (저격수가 사용하는 별칭)

        # 도적 - 베놈 파워
        elif gimmick_type == "venom_system":
            self.venom_power = 0
            self.venom_power_max = self.gimmick_data.get("max_venom", 200)
            self.poison_stacks = 0
            self.max_poison_stacks = self.gimmick_data.get("max_poison", 10)

        # 암살자 - 그림자
        elif gimmick_type == "shadow_system":
            self.shadow_count = 0
            self.max_shadow_count = self.gimmick_data.get("max_shadows", 5)

        # 검성 - 검기
        elif gimmick_type == "sword_aura":
            self.sword_aura = 0
            self.max_sword_aura = self.gimmick_data.get("max_aura", 5)

        # 광전사 - 분노
        elif gimmick_type == "rage_system":
            self.rage_stacks = 0
            self.max_rage_stacks = self.gimmick_data.get("max_rage", 10)
            self.shield_amount = 0  # 분노 방패량

        # 몽크 - 기 에너지
        elif gimmick_type == "ki_system":
            self.ki_energy = 0
            self.max_ki_energy = self.gimmick_data.get("max_ki", 100)
            self.chakra_points = 0  # 차크라 포인트 (스킬에서 사용)
            self.combo_count = 0
            self.strike_marks = 0

        # 바드 - 멜로디
        elif gimmick_type == "melody_system":
            self.melody_stacks = 0
            self.max_melody_stacks = self.gimmick_data.get("max_melody", 7)
            self.melody_notes = []
            self.current_melody = ""
            self.octave_completed = False  # 옥타브 완성 여부

        # 네크로맨서 - 네크로 에너지
        elif gimmick_type == "necro_system":
            self.necro_energy = 0
            self.max_necro_energy = self.gimmick_data.get("max_necro", 50)
            self.soul_power = 0
            self.undead_count = 0
            self.corpse_count = 0  # 시체 개수 (스킬에서 사용)
            self.minion_count = 0  # 미니언 개수 (스킬에서 사용)

        # 정령술사 - 정령 친화도
        elif gimmick_type == "spirit_bond":
            self.spirit_bond = 0
            self.max_spirit_bond = self.gimmick_data.get("max_bond", 25)
            self.spirit_count = 0  # 정령 개수 (스킬에서 사용)

        # 시간술사 - 시간 기록점
        elif gimmick_type == "time_system":
            self.time_marks = 0
            self.max_time_marks = self.gimmick_data.get("max_marks", 7)
            self.time_points = 0  # 시간 포인트 (스킬에서 사용하는 별칭)

        # 용기사 - 용의 표식
        elif gimmick_type == "dragon_marks":
            self.dragon_marks = 0
            self.max_dragon_marks = self.gimmick_data.get("max_marks", 3)
            self.dragon_power = 0  # 용의 힘 (스킬에서 사용하는 별칭)

        # 검투사 - 투기장 포인트
        elif gimmick_type == "arena_system":
            self.arena_points = 0
            self.max_arena_points = self.gimmick_data.get("max_points", 20)
            self.glory_points = 0  # 영광 포인트 (스킬에서 사용하는 별칭)
            self.kill_count = 0  # 처치 카운트
            self.parry_active = False  # 패리 활성화 여부

        # 브레이커 - 파괴력 축적
        elif gimmick_type == "break_system":
            self.break_power = 0
            self.max_break_power = self.gimmick_data.get("max_break_power", 10)

        # 다크나이트 - 어둠의 힘
        elif gimmick_type == "darkness_system":
            self.darkness = 0
            self.max_darkness = self.gimmick_data.get("max_darkness", 100)

        # 기사 - 의무 스택
        elif gimmick_type == "duty_system":
            self.duty_stacks = 0
            self.max_duty_stacks = self.gimmick_data.get("max_duty_stacks", 10)

        # 팔라딘 - 성스러운 힘
        elif gimmick_type == "holy_system":
            self.holy_power = 0
            self.max_holy_power = self.gimmick_data.get("max_holy_power", 100)

        # 암살자 - 은신
        elif gimmick_type == "stealth_system":
            self.stealth_points = 0
            self.max_stealth_points = self.gimmick_data.get("max_stealth_points", 5)

        # 도적 - 절도
        elif gimmick_type == "theft_system":
            self.stolen_items = 0
            self.max_stolen_items = self.gimmick_data.get("max_stolen_items", 10)
            self.evasion_active = False

        # 해적 - 약탈
        elif gimmick_type == "plunder_system":
            self.gold = 0
            self.max_gold = self.gimmick_data.get("max_gold", 1000)
            self.gold_per_hit = self.gimmick_data.get("gold_per_hit", 10)

        # 엔지니어 - 구조물
        elif gimmick_type == "construct_system":
            self.machine_parts = 0
            self.max_machine_parts = self.gimmick_data.get("max_machine_parts", 5)

        # 사무라이 - 거합
        elif gimmick_type == "iaijutsu_system":
            self.will_gauge = 0
            self.max_will_gauge = self.gimmick_data.get("max_will_gauge", 100)

        # 배틀메이지 - 룬
        elif gimmick_type == "rune_system":
            self.rune_stacks = 0
            self.max_rune_stacks = self.gimmick_data.get("max_rune_stacks", 5)

        # 마검사 - 마력 부여
        elif gimmick_type == "enchant_system":
            self.mana_blade = 0
            self.max_mana_blade = self.gimmick_data.get("max_mana_blade", 100)

        # 차원술사 - 차원 조작
        elif gimmick_type == "dimension_system":
            self.dimension_points = 0
            self.max_dimension_points = self.gimmick_data.get("max_dimension_points", 100)

        # 프리스트/클레릭 - 신성력
        elif gimmick_type == "divinity_system":
            self.judgment_points = 0
            self.max_judgment_points = self.gimmick_data.get("max_judgment_points", 100)
            self.faith_points = 0
            self.max_faith_points = self.gimmick_data.get("max_faith_points", 100)

        # 드루이드 - 변신
        elif gimmick_type == "shapeshifting_system":
            self.nature_points = 0
            self.max_nature_points = self.gimmick_data.get("max_nature_points", 100)
            self.current_form = None
            self.available_forms = self.gimmick_data.get("forms", ["bear", "panther", "eagle"])

        # 샤먼 - 토템
        elif gimmick_type == "totem_system":
            self.curse_stacks = 0
            self.max_curse_stacks = self.gimmick_data.get("max_curse_stacks", 10)

        # 뱀파이어 - 흡혈
        elif gimmick_type == "blood_system":
            self.blood_pool = 0
            self.max_blood_pool = self.gimmick_data.get("max_blood_pool", 100)
            self.lifesteal_boost = self.gimmick_data.get("lifesteal_base", 0.15)

        # 연금술사 - 연금술
        elif gimmick_type == "alchemy_system":
            self.potion_stock = 0
            self.max_potion_stock = self.gimmick_data.get("max_potion_stock", 10)

        # 철학자 - 지혜
        elif gimmick_type == "wisdom_system":
            self.knowledge_stacks = 0
            self.max_knowledge_stacks = self.gimmick_data.get("max_knowledge_stacks", 10)

        # 해커 - 해킹
        elif gimmick_type == "hack_system":
            self.hack_stacks = 0
            self.max_hack_stacks = self.gimmick_data.get("max_hack_stacks", 5)
            self.debuff_count = 0
            self.max_debuff_count = self.gimmick_data.get("max_debuff_count", 10)

        self.logger.debug(f"{self.character_class} 기믹 초기화: {gimmick_type}")

    def _get_class_skills(self, character_class: str) -> List[str]:
        """
        직업에 맞는 스킬 ID 목록을 가져옵니다.

        SkillManager에 등록된 스킬 중 해당 직업의 스킬만 필터링합니다.
        """
        from src.character.skills.skill_manager import get_skill_manager
        skill_manager = get_skill_manager()

        # 한글/영문 직업명 → 영문 스킬 접두사 매핑
        skill_prefix_map = {
            # 한글 직업명
            "전사": "warrior_",
            "아크메이지": "archmage_",
            "궁수": "archer_",
            "도적": "rogue_",
            "성기사": "paladin_",
            "암흑기사": "dk_",  # dark_knight 축약형
            "몽크": "monk_",
            "바드": "bard_",
            "네크로맨서": "necro_",  # necromancer 축약형
            "용기사": "dragon_knight_",
            "검성": "sword_saint_",
            "정령술사": "elementalist_",
            "암살자": "assassin_",
            "기계공학자": "engineer_",
            "무당": "shaman_",
            "해적": "pirate_",
            "사무라이": "samurai_",
            "드루이드": "druid_",
            "철학자": "philosopher_",
            "시간술사": "time_mage_",
            "연금술사": "alchemist_",
            "검투사": "gladiator_",
            "기사": "knight_",
            "신관": "priest_",
            "마검사": "spellblade_",
            "차원술사": "dimensionist_",
            "광전사": "berserker_",
            "마법사": "mage_",
            "전투마법사": "bmage_",  # battle_mage 축약형
            "클레릭": "cleric_",
            "브레이커": "breaker_",
            "해커": "hacker_",
            "저격수": "sniper_",
            "흡혈귀": "vampire_",
            # 영문 직업명 (하위호환성)
            "warrior": "warrior_",
            "archmage": "archmage_",
            "archer": "archer_",
            "rogue": "rogue_",
            "paladin": "paladin_",
            "dark_knight": "dk_",
            "monk": "monk_",
            "bard": "bard_",
            "necromancer": "necro_",
            "dragon_knight": "dragon_knight_",
            "sword_saint": "sword_saint_",
            "elementalist": "elementalist_",
            "assassin": "assassin_",
            "engineer": "engineer_",
            "shaman": "shaman_",
            "pirate": "pirate_",
            "samurai": "samurai_",
            "druid": "druid_",
            "philosopher": "philosopher_",
            "time_mage": "time_mage_",
            "alchemist": "alchemist_",
            "gladiator": "gladiator_",
            "knight": "knight_",
            "priest": "priest_",
            "spellblade": "spellblade_",
            "dimensionist": "dimensionist_",
            "berserker": "berserker_",
            "mage": "mage_",
            "battle_mage": "bmage_",
            "cleric": "cleric_",
            "breaker": "breaker_",
            "hacker": "hacker_",
            "sniper": "sniper_",
            "vampire": "vampire_",
        }

        # 스킬 접두사 가져오기
        skill_prefix = skill_prefix_map.get(character_class)
        if not skill_prefix:
            self.logger.warning(f"{character_class}의 스킬 접두사를 찾을 수 없습니다!")
            return []

        # 해당 접두사로 시작하는 스킬 ID 필터링
        skill_ids = []
        for skill_id in skill_manager._skills.keys():
            if skill_id.startswith(skill_prefix):
                skill_ids.append(skill_id)

        if not skill_ids:
            self.logger.warning(f"{character_class}({skill_prefix})의 스킬을 찾을 수 없습니다!")
        else:
            self.logger.debug(f"{character_class}({skill_prefix})의 스킬: {len(skill_ids)}개")

        return skill_ids

    # ===== 스탯 프로퍼티 =====

    @property
    def max_hp(self) -> int:
        """최대 HP"""
        return int(self.stat_manager.get_value(Stats.HP))

    @property
    def max_mp(self) -> int:
        """최대 MP"""
        return int(self.stat_manager.get_value(Stats.MP))

    @property
    def init_brv(self) -> int:
        """초기 BRV (전투 시작 시)"""
        return int(self.stat_manager.get_value(Stats.INIT_BRV))

    @property
    def max_brv(self) -> int:
        """최대 BRV"""
        return int(self.stat_manager.get_value(Stats.MAX_BRV))

    @max_brv.setter
    def max_brv(self, value: int) -> None:
        """최대 BRV 설정"""
        # 기본 값 (보너스 제외)
        base_value = int(self.stat_manager.get_value(Stats.MAX_BRV, use_total=False))
        # 이전 direct_set 보너스 제거
        self.stat_manager.remove_bonus(Stats.MAX_BRV, "direct_set")
        # 새로운 보너스 추가
        bonus = value - base_value
        if bonus != 0:
            self.stat_manager.add_bonus(Stats.MAX_BRV, "direct_set", bonus)

    @property
    def strength(self) -> int:
        """물리 공격력"""
        return int(self.stat_manager.get_value(Stats.STRENGTH))

    @property
    def defense(self) -> int:
        """물리 방어력"""
        return int(self.stat_manager.get_value(Stats.DEFENSE))

    @property
    def magic(self) -> int:
        """마법 공격력"""
        return int(self.stat_manager.get_value(Stats.MAGIC))

    @property
    def spirit(self) -> int:
        """마법 방어력"""
        return int(self.stat_manager.get_value(Stats.SPIRIT))

    @property
    def speed(self) -> int:
        """속도"""
        return int(self.stat_manager.get_value(Stats.SPEED))

    @property
    def luck(self) -> int:
        """행운"""
        return int(self.stat_manager.get_value(Stats.LUCK))

    @property
    def accuracy(self) -> int:
        """명중률"""
        return int(self.stat_manager.get_value(Stats.ACCURACY))

    @property
    def evasion(self) -> int:
        """회피율"""
        return int(self.stat_manager.get_value(Stats.EVASION))

    # ===== 스킬 관리 =====

    @property
    def skills(self) -> List[Any]:
        """스킬 객체 리스트 (skill_ids로부터 생성)"""
        if self._cached_skills is None:
            from src.character.skills.skill_manager import get_skill_manager
            skill_manager = get_skill_manager()
            self._cached_skills = [
                skill_manager.get_skill(skill_id)
                for skill_id in self.skill_ids
                if skill_manager.get_skill(skill_id)
            ]
        return self._cached_skills

    # ===== HP/MP 관리 =====

    def take_damage(self, damage: int) -> int:
        """
        데미지를 받습니다

        Args:
            damage: 데미지 양

        Returns:
            실제로 받은 데미지
        """
        actual_damage = min(damage, self.current_hp)
        self.current_hp -= actual_damage

        if self.current_hp <= 0:
            self.current_hp = 0
            self.is_alive = False

            event_bus.publish(Events.CHARACTER_DEATH, {
                "character": self,
                "name": self.name
            })

        event_bus.publish(Events.CHARACTER_HP_CHANGE, {
            "character": self,
            "change": -actual_damage,
            "current": self.current_hp,
            "max": self.max_hp
        })

        return actual_damage

    def heal(self, amount: int) -> int:
        """
        HP를 회복합니다

        Args:
            amount: 회복량

        Returns:
            실제로 회복한 양
        """
        old_hp = self.current_hp
        self.current_hp = min(self.current_hp + amount, self.max_hp)
        actual_heal = self.current_hp - old_hp

        event_bus.publish(Events.CHARACTER_HP_CHANGE, {
            "character": self,
            "change": actual_heal,
            "current": self.current_hp,
            "max": self.max_hp
        })

        return actual_heal

    def consume_mp(self, amount: int) -> bool:
        """
        MP를 소비합니다

        Args:
            amount: 소비량

        Returns:
            성공 여부
        """
        if self.current_mp < amount:
            return False

        self.current_mp -= amount

        event_bus.publish(Events.CHARACTER_MP_CHANGE, {
            "character": self,
            "change": -amount,
            "current": self.current_mp,
            "max": self.max_mp
        })

        return True

    def restore_mp(self, amount: int) -> int:
        """
        MP를 회복합니다

        Args:
            amount: 회복량

        Returns:
            실제로 회복한 양
        """
        old_mp = self.current_mp
        self.current_mp = min(self.current_mp + amount, self.max_mp)
        actual_restore = self.current_mp - old_mp

        event_bus.publish(Events.CHARACTER_MP_CHANGE, {
            "character": self,
            "change": actual_restore,
            "current": self.current_mp,
            "max": self.max_mp
        })

        return actual_restore

    # ===== 레벨업 =====

    def level_up(self) -> None:
        """레벨업"""
        old_level = self.level
        self.level += 1

        # StatManager를 통해 모든 스탯 성장
        self.stat_manager.apply_level_up(self.level)

        # HP/MP는 회복하지 않음 (전투 중 레벨업 시 밸런스)

        self.logger.info(f"{self.name} 레벨업: {old_level} → {self.level}")

        event_bus.publish(Events.CHARACTER_LEVEL_UP, {
            "character": self,
            "old_level": old_level,
            "new_level": self.level
        })

    # ===== 장비 =====

    def equip_item(self, slot: str, item: Any) -> None:
        """
        장비 장착

        Args:
            slot: 장비 슬롯 (weapon, armor, accessory)
            item: 아이템
        """
        if slot not in self.equipment:
            self.logger.warning(f"잘못된 장비 슬롯: {slot}")
            return

        # 기존 장비 해제
        if self.equipment[slot]:
            self.unequip_item(slot)

        self.equipment[slot] = item

        # 장비 보너스 적용
        if hasattr(item, "stat_bonuses"):
            for stat_name, bonus in item.stat_bonuses.items():
                self.stat_manager.add_bonus(stat_name, f"equipment_{slot}", bonus)

        event_bus.publish(Events.EQUIPMENT_EQUIPPED, {
            "character": self,
            "slot": slot,
            "item": item
        })

    def unequip_item(self, slot: str) -> Optional[Any]:
        """
        장비 해제

        Args:
            slot: 장비 슬롯

        Returns:
            해제된 아이템
        """
        item = self.equipment.get(slot)
        if not item:
            return None

        # 장비 보너스 제거
        if hasattr(item, "stat_bonuses"):
            for stat_name in item.stat_bonuses.keys():
                self.stat_manager.remove_bonus(stat_name, f"equipment_{slot}")

        self.equipment[slot] = None

        event_bus.publish(Events.EQUIPMENT_UNEQUIPPED, {
            "character": self,
            "slot": slot,
            "item": item
        })

        return item

    # ===== Trait (특성) 관련 =====

    def activate_trait(self, trait_id: str) -> bool:
        """
        특성 활성화

        Args:
            trait_id: 특성 ID

        Returns:
            성공 여부
        """
        # 이미 활성화된 특성인지 확인
        if any(
            (t if isinstance(t, str) else t.get('id')) == trait_id
            for t in self.active_traits
        ):
            self.logger.warning(f"특성 {trait_id}는 이미 활성화되어 있습니다")
            return False

        # 사용 가능한 특성인지 확인
        # available_traits는 딕셔너리 리스트: [{'id': 'xxx', 'name': 'xxx', ...}, ...]
        available_trait_ids = [
            t['id'] if isinstance(t, dict) else t
            for t in self.available_traits
        ]

        # trait_id가 available_trait_ids에 있거나, passives.yaml에 정의된 패시브 특성이면 허용
        if trait_id not in available_trait_ids:
            # 패시브 특성인지 확인 (passives.yaml의 특성들)
            from src.character.trait_effects import get_trait_effect_manager
            trait_manager = get_trait_effect_manager()
            if trait_id not in trait_manager.trait_definitions:
                self.logger.warning(f"특성 {trait_id}는 사용할 수 없습니다")
                return False

        # 특성 활성화
        self.active_traits.append(trait_id)
        self.logger.info(f"특성 활성화: {trait_id}")

        # 특성 효과 적용 (패시브 스탯 보너스 등)
        self._apply_trait_stat_bonuses()

        return True

    def deactivate_trait(self, trait_id: str) -> bool:
        """
        특성 비활성화

        Args:
            trait_id: 특성 ID

        Returns:
            성공 여부
        """
        # 활성화된 특성 찾기
        for i, trait in enumerate(self.active_traits):
            if (trait if isinstance(trait, str) else trait.get('id')) == trait_id:
                self.active_traits.pop(i)
                self.logger.info(f"특성 비활성화: {trait_id}")
                return True

        self.logger.warning(f"특성 {trait_id}는 활성화되어 있지 않습니다")
        return False

    def _apply_trait_stat_bonuses(self) -> None:
        """
        활성화된 특성의 스탯 보너스 적용
        """
        trait_manager = get_trait_effect_manager()

        # 각 스탯에 대해 trait 보너스 계산
        stat_names = [
            "hp", "mp", "init_brv", "max_brv", "physical_attack", "physical_defense",
            "magic_attack", "magic_defense", "speed", "accuracy", "evasion"
        ]

        for stat_name in stat_names:
            # 기본 스탯 값 가져오기
            if stat_name == "hp":
                base_value = self.stat_manager.get_value(Stats.HP)
            elif stat_name == "mp":
                base_value = self.stat_manager.get_value(Stats.MP)
            elif stat_name == "init_brv":
                base_value = self.stat_manager.get_value(Stats.INIT_BRV)
            elif stat_name == "max_brv":
                base_value = self.stat_manager.get_value(Stats.MAX_BRV)
            elif stat_name == "physical_attack":
                base_value = self.stat_manager.get_value(Stats.STRENGTH)
            elif stat_name == "physical_defense":
                base_value = self.stat_manager.get_value(Stats.DEFENSE)
            elif stat_name == "magic_attack":
                base_value = self.stat_manager.get_value(Stats.MAGIC)
            elif stat_name == "magic_defense":
                base_value = self.stat_manager.get_value(Stats.SPIRIT)
            elif stat_name == "speed":
                base_value = self.stat_manager.get_value(Stats.SPEED)
            elif stat_name == "accuracy":
                base_value = self.stat_manager.get_value(Stats.ACCURACY)
            elif stat_name == "evasion":
                base_value = self.stat_manager.get_value(Stats.EVASION)
            else:
                continue

            # Trait 보너스 계산
            bonus_value = trait_manager.calculate_stat_bonus(self, stat_name, base_value)

            # 보너스가 있으면 StatManager에 적용
            if bonus_value != base_value:
                bonus_diff = bonus_value - base_value
                stat_enum = self._stat_name_to_enum(stat_name)
                if stat_enum:
                    self.stat_manager.add_bonus(stat_enum, f"trait_{stat_name}", bonus_diff)

    def _stat_name_to_enum(self, stat_name: str) -> Optional[Stats]:
        """스탯 이름을 Stats enum으로 변환"""
        mapping = {
            "hp": Stats.HP,
            "mp": Stats.MP,
            "init_brv": Stats.INIT_BRV,
            "max_brv": Stats.MAX_BRV,
            "physical_attack": Stats.STRENGTH,
            "physical_defense": Stats.DEFENSE,
            "magic_attack": Stats.MAGIC,
            "magic_defense": Stats.SPIRIT,
            "speed": Stats.SPEED,
            "accuracy": Stats.ACCURACY,
            "evasion": Stats.EVASION
        }
        return mapping.get(stat_name)

    def get_trait_bonus(self, trait_type: str = "damage") -> float:
        """
        특정 타입의 trait 보너스 가져오기

        Args:
            trait_type: 보너스 타입 (damage, critical, mp_cost 등)

        Returns:
            보너스 값
        """
        trait_manager = get_trait_effect_manager()

        if trait_type == "damage":
            return trait_manager.calculate_damage_multiplier(self)
        elif trait_type == "critical":
            return trait_manager.calculate_critical_bonus(self)
        elif trait_type == "break":
            return trait_manager.calculate_break_bonus(self)
        else:
            return 0.0

    # ===== 유틸리티 =====

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (저장용)"""
        return {
            "name": self.name,
            "character_class": self.character_class,
            "level": self.level,
            "current_hp": self.current_hp,
            "current_mp": self.current_mp,
            "wound": getattr(self, "wound", 0),  # 상처 값 저장
            "stats": self.stat_manager.to_dict(),
            "equipment": {
                slot: item.to_dict() if hasattr(item, "to_dict") else None
                for slot, item in self.equipment.items()
            }
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Character":
        """딕셔너리에서 복원"""
        character = cls.__new__(cls)
        character.name = data["name"]
        character.character_class = data["character_class"]
        character.level = data["level"]
        character.current_hp = data["current_hp"]
        character.current_mp = data["current_mp"]
        character.wound = data.get("wound", 0)  # 상처 값 복원

        # StatManager 복원
        character.stat_manager = StatManager.from_dict(data["stats"])

        character.current_brv = 0
        character.is_alive = character.current_hp > 0
        character.is_enemy = False
        character.equipment = {"weapon": None, "armor": None, "accessory": None}
        character.status_effects = []
        character.traits = []

        character.logger = get_logger("character")

        return character

    def __repr__(self) -> str:
        return f"Character({self.name}, {self.character_class}, Lv.{self.level})"
