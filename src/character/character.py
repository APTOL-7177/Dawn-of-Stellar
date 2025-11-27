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
from src.combat.status_effects import StatusManager
from src.core.event_bus import event_bus, Events
from src.core.logger import get_logger

logger = get_logger("character")


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
        
        # 초기 레벨이 1이 아닌 경우 레벨업 적용 (base_value는 1레벨 기준이므로)
        if self.level > 1:
            self.stat_manager.apply_level_up(self.level)

        # 현재 HP/MP (StatManager와 별도 관리)
        self.current_hp = self.max_hp
        self.current_mp = self.max_mp
        
        # 바라보는 방향 (필드 스킬용)
        self.dx = 0
        self.dy = 1  # 기본 아래쪽

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

        # 상태 효과 관리자
        self.status_manager = StatusManager(owner_name=name, owner=self)
        # 하위 호환성을 위한 별칭
        self.status_effects = self.status_manager.status_effects

        # 직업 기믹 초기화
        self.gimmick_data = get_gimmick(character_class)
        self.gimmick_type = self.gimmick_data.get("type") if self.gimmick_data else None
        self.system_traits: List[str] = []  # 시스템/기믹에 의해 자동 적용되는 특성
        self._initialize_gimmick()

        # 특성 (Trait) - YAML에서 로드
        self.available_traits = get_traits(character_class)
        self.active_traits: List[Any] = []

        # 특성별 스택 카운터
        self.defend_stack_count = 0  # 저격수 특성: 방어 시 증가, 공격 시 소비

        # 스킬 - 직업별로 등록된 스킬 가져오기
        self.skill_ids = self._get_class_skills(character_class)
        self._cached_skills = None  # 스킬 객체 캐시

        # 시야 보너스 초기화 (장비 효과용)
        self.vision_bonus = 0

        # 보호 시스템 초기화 (수호의 맹세 등)
        self.protected_allies = []  # 이 캐릭터가 보호하는 아군 목록
        self.protected_by = []  # 이 캐릭터를 보호하는 캐릭터 목록

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

        # 궁수/저격수 - 조준 포인트 (구버전, 호환성 유지)
        elif gimmick_type == "aim_system":
            self.aim_points = 0
            self.max_aim_points = self.gimmick_data.get("max_aim", 5)
            self.focus_stacks = 0  # 집중 스택 (저격수가 사용하는 별칭)

        # 저격수 - 탄창 시스템 (신버전)
        elif gimmick_type == "magazine_system":
            self.max_magazine = self.gimmick_data.get("max_magazine", 6)
            self.magazine = ["normal"] * self.max_magazine  # 현재 탄창 (기본 탄환으로 가득 채워 시작)
            self.current_bullet_index = 0  # 다음 발사할 탄환 인덱스
            self.quick_reload_count = 2  # 빠른 재장전 남은 횟수
            # 탄환 타입 정보 저장
            self.bullet_types = {
                "normal": {"name": "기본 탄환", "multiplier": 2.0},
                "penetrating": {"name": "관통탄", "multiplier": 2.5, "defense_pierce_fixed": 0.15},  # 공격력의 15% 고정수치
                "explosive": {"name": "폭발탄", "multiplier": 1.8, "aoe": True},
                "frost": {"name": "빙결탄", "multiplier": 1.8, "status": "frozen"},
                "fire": {"name": "화염탄", "multiplier": 2.0, "status": "burn"},
                "poison": {"name": "독침탄", "multiplier": 1.5, "status": "poison"},
                "flash": {"name": "섬광탄", "multiplier": 1.0, "debuff": "blind"},
                "headshot": {"name": "헤드샷 탄", "multiplier": 5.0, "crit_guaranteed": True}
            }

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

        # 바드 - 멜로디
        elif gimmick_type == "melody_system":
            self.melody_stacks = 0
            self.max_melody_stacks = self.gimmick_data.get("max_melody", 7)
            self.melody_notes = 0
            self.current_melody = ""
            self.octave_completed = False  # 옥타브 완성 여부

        # 시간술사 - 타임라인 균형 시스템 (신버전)
        elif gimmick_type == "timeline_system":
            self.timeline = 0  # 현재 타임라인 위치 (-5 ~ +5)
            self.min_timeline = self.gimmick_data.get("min_timeline", -5)
            self.max_timeline = self.gimmick_data.get("max_timeline", 5)
            self.optimal_point = self.gimmick_data.get("optimal_point", 0)
            self.past_threshold = self.gimmick_data.get("past_threshold", -2)
            self.future_threshold = self.gimmick_data.get("future_threshold", 2)
            self.time_correction_counter = 0  # 시간 보정 카운터 (3턴마다)

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

        # 다크나이트 - 충전 시스템
        elif gimmick_type == "charge_system":
            self.charge_gauge = self.gimmick_data.get("start_charge", 0)
            self.max_charge = self.gimmick_data.get("max_charge", 100)

        # 기사 - 의무 스택
        elif gimmick_type == "duty_system":
            self.duty_stacks = 0
            self.max_duty_stacks = self.gimmick_data.get("max_duty_stacks", 10)

        # 팔라딘 - 성스러운 힘
        elif gimmick_type == "holy_system":
            self.holy_power = 0
            self.max_holy_power = self.gimmick_data.get("max_holy_power", 100)

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

        # 엔지니어 - 열 관리 시스템 (신버전)
        elif gimmick_type == "heat_management":
            self.heat = 0  # 현재 열 게이지 (0-100)
            self.max_heat = self.gimmick_data.get("max_heat", 100)
            self.optimal_min = self.gimmick_data.get("optimal_min", 50)
            self.optimal_max = self.gimmick_data.get("optimal_max", 79)
            self.danger_min = self.gimmick_data.get("danger_min", 80)
            self.danger_max = self.gimmick_data.get("danger_max", 99)
            self.overheat_threshold = self.gimmick_data.get("overheat_threshold", 100)
            self.overheat_prevention_count = 2  # 오버히트 방지 남은 횟수
            self.is_overheated = False  # 오버히트 상태
            self.overheat_stun_turns = 0  # 오버히트 스턴 남은 턴

        # 사무라이 - 거합
        elif gimmick_type == "iaijutsu_system":
            self.will_gauge = 0
            self.max_will_gauge = self.gimmick_data.get("max_will_gauge", 10)

        # 마검사 - 마력 부여
        elif gimmick_type == "enchant_system":
            self.mana_blade = 0
            self.max_mana_blade = self.gimmick_data.get("max_mana_blade", 100)

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

        # 샤먼 - 저주 (하위 호환성을 위해 totem_system도 지원)
        elif gimmick_type == "curse_system" or gimmick_type == "totem_system":
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

        # 해커 - 해킹 (구버전, 호환성 유지)
        elif gimmick_type == "hack_system":
            self.hack_stacks = 0
            self.max_hack_stacks = self.gimmick_data.get("max_hack_stacks", 5)
            self.debuff_count = 0
            self.max_debuff_count = self.gimmick_data.get("max_debuff_count", 10)

        # === 새로운 기믹 시스템들 (문서 재설계) ===

        # 몽크 - 음양 흐름 시스템 (신버전)
        elif gimmick_type == "yin_yang_flow":
            self.ki_gauge = 50  # 음양 게이지 (0-100, 50이 균형)
            self.min_ki = self.gimmick_data.get("min_ki", 0)
            self.max_ki = self.gimmick_data.get("max_ki", 100)
            self.balance_center = self.gimmick_data.get("balance_center", 50)
            self.yin_threshold = self.gimmick_data.get("yin_threshold", 20)  # 20 이하면 음 극대
            self.yang_threshold = self.gimmick_data.get("yang_threshold", 80)  # 80 이상이면 양 극대

        # 배틀메이지 - 룬 공명 시스템 (신버전)
        elif gimmick_type == "rune_resonance":
            self.rune_fire = 0  # 화염 룬 (0-3)
            self.rune_ice = 0   # 빙결 룬 (0-3)
            self.rune_lightning = 0  # 번개 룬 (0-3)
            self.rune_earth = 0  # 대지 룬 (0-3)
            self.rune_arcane = 0  # 비전 룬 (0-3)
            self.max_rune_per_type = self.gimmick_data.get("max_per_rune", 3)
            self.max_runes_total = self.gimmick_data.get("max_runes_total", 9)
            self.resonance_bonus = 0  # 공명 보너스 (3개 동일 룬 시)

        # 네크로맨서 - 언데드 군단 시스템 (신버전)
        elif gimmick_type == "undead_legion":
            self.undead_count = 0  # 현재 언데드 수 (0-5)
            self.max_undead_total = self.gimmick_data.get("max_undead_total", 5)
            self.undead_skeleton = 0  # 스켈레톤 수
            self.undead_zombie = 0  # 좀비 수
            self.undead_ghost = 0  # 유령 수
            self.undead_power = 0  # 언데드 전체 파워

        # 버서커 - 광기 임계치 시스템 (신버전)
        elif gimmick_type == "madness_threshold":
            self.madness = 0  # 광기 게이지 (0-100)
            self.max_madness = self.gimmick_data.get("max_madness", 100)
            self.optimal_min = self.gimmick_data.get("optimal_min", 30)  # 최적 구간 시작
            self.optimal_max = self.gimmick_data.get("optimal_max", 70)  # 최적 구간 끝
            self.danger_min = self.gimmick_data.get("danger_min", 71)  # 위험 구간 시작
            self.rampage_threshold = self.gimmick_data.get("rampage_threshold", 100)  # 폭주 임계값

        # 뱀파이어 - 갈증 게이지 시스템 (신버전)
        elif gimmick_type == "thirst_gauge":
            self.thirst = self.gimmick_data.get("start_thirst", 0)  # 갈증 게이지 (0-100)
            self.max_thirst = self.gimmick_data.get("max_thirst", 100)
            # YAML의 thirst_zones에서 구간 정보 읽기
            thirst_zones = self.gimmick_data.get("thirst_zones", {})
            satisfied_zone = thirst_zones.get("satisfied", {})
            thirsty_zone = thirst_zones.get("thirsty", {})
            extreme_zone = thirst_zones.get("extreme", {})
            frenzy_zone = thirst_zones.get("frenzy", {})
            # 만족 구간 (0-30)
            self.satisfied_max = satisfied_zone.get("max", 30)
            # 갈증 구간 (31-60)
            self.thirsty_min = thirsty_zone.get("min", 31)
            self.thirsty_max = thirsty_zone.get("max", 60)
            # 극심한 갈증 구간 (61-90)
            self.extreme_min = extreme_zone.get("min", 61)
            self.extreme_max = extreme_zone.get("max", 90)
            # 혈액 광란 구간 (91-100)
            self.frenzy_min = frenzy_zone.get("min", 91)
            self.frenzy_max = frenzy_zone.get("max", 100)
            # 하위 호환성을 위한 레거시 변수들 (deprecated)
            self.normal_min = self.thirsty_min
            self.normal_max = self.extreme_max
            self.starving_min = self.frenzy_min
            
            # 뱀파이어 기믹 특성 자동 추가
            if "vampire_thirst_gimmick" not in self.system_traits:
                self.system_traits.append("vampire_thirst_gimmick")

        # 해커 - 멀티스레드 시스템 (신버전)
        elif gimmick_type == "multithread_system":
            self.active_threads = []  # 활성 스레드 리스트 (최대 4개)
            self.max_threads = self.gimmick_data.get("max_threads", 4)
            self.thread_types = ["firewall", "exploit", "ddos", "rootkit"]  # 가능한 스레드 타입

        # 글래디에이터 - 군중 환호 시스템 (신버전)
        elif gimmick_type == "crowd_cheer":
            self.cheer = 0  # 환호 게이지 (0-100)
            self.max_cheer = self.gimmick_data.get("max_cheer", 100)
            self.start_cheer = self.gimmick_data.get("start_cheer", 0)
            self.cheer_zones = self.gimmick_data.get("cheer_zones", {})  # normal/popular/superstar/glory

        # 암살자 - 은신-노출 딜레마 (신버전)
        elif gimmick_type == "stealth_exposure":
            self.stealth_active = True  # 은신 상태 (True/False)
            self.exposed_turns = 0  # 노출 후 경과 턴 (3턴 후 재은신 가능)
            self.restealth_cooldown = self.gimmick_data.get("restealth_cooldown", 3)

        # 궁수 - 지원사격 시스템 (신버전)
        elif gimmick_type == "support_fire":
            self.marked_allies = {}  # 마킹된 아군 {ally_id: {"arrow_type": "normal", "shots_left": 3}}
            self.max_marks = self.gimmick_data.get("max_marks", 3)
            self.shots_per_mark = self.gimmick_data.get("shots_per_mark", 3)
            self.support_fire_combo = 0  # 연속 지원 사격 콤보
            self.arrow_types = self.gimmick_data.get("arrow_types", {})

        # 정령술사 - 4대 정령 소환 (신버전)
        elif gimmick_type == "elemental_spirits":
            self.spirit_fire = 0  # 화염 정령 (0 or 1)
            self.spirit_water = 0  # 물 정령 (0 or 1)
            self.spirit_wind = 0  # 바람 정령 (0 or 1)
            self.spirit_earth = 0  # 대지 정령 (0 or 1)
            self.max_spirits = self.gimmick_data.get("max_spirits", 2)  # 최대 2마리 동시 소환

        # 철학자 - 딜레마 선택 시스템 (신버전)
        elif gimmick_type == "dilemma_choice":
            self.choice_power = 0  # 힘 선택 카운트
            self.choice_wisdom = 0  # 지혜 선택 카운트
            self.choice_sacrifice = 0  # 희생 선택 카운트
            self.choice_survival = 0  # 생존 선택 카운트
            self.choice_truth = 0  # 진실 선택 카운트
            self.choice_lie = 0  # 거짓 선택 카운트
            self.choice_order = 0  # 질서 선택 카운트 (추가)
            self.choice_chaos = 0  # 혼돈 선택 카운트 (추가)
            self.accumulation_threshold = self.gimmick_data.get("accumulation_threshold", 5)

        # 차원술사 - 확률 왜곡 게이지 (신버전)
        elif gimmick_type == "probability_distortion":
            self.distortion_gauge = 0  # 확률 왜곡 게이지 (0-100)
            self.max_gauge = self.gimmick_data.get("max_gauge", 100)
            self.start_gauge = self.gimmick_data.get("start_gauge", 0)
            self.gauge_per_turn = self.gimmick_data.get("gauge_gain", {}).get("per_turn", 10)

        # 차원술사 - 차원 굴절 시스템
        elif gimmick_type == "dimension_refraction":
            start_refraction = self.gimmick_data.get("start_refraction", 0)
            self.refraction_stacks = start_refraction  # 차원 굴절량 초기화

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
            "네크로맨서": "necromancer_",
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
            "전투마법사": "battle_mage_",  # battle_mage
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
            "necromancer": "necromancer_",
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
            "battle_mage": "battle_mage_",
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
        # 네크로맨서: 미니언이 공격을 대신 받을 확률 체크
        if hasattr(self, 'gimmick_type') and self.gimmick_type == "undead_legion":
            skeleton = getattr(self, 'undead_skeleton', 0)
            zombie = getattr(self, 'undead_zombie', 0)
            ghost = getattr(self, 'undead_ghost', 0)
            total_undead = skeleton + zombie + ghost
            
            if total_undead > 0:
                import random
                # 미니언 1마리마다 20% 확률로 공격을 대신 받음
                minion_block_chance = min(0.8, total_undead * 0.2)  # 최대 80%
                if random.random() < minion_block_chance:
                    # 미니언이 대신 받음 - 미니언 1마리 제거
                    if ghost > 0:
                        self.undead_ghost = max(0, ghost - 1)
                        logger.info(f"[UNDEAD] 유령이 {self.name}를 대신 공격을 막았습니다! (남은 유령: {self.undead_ghost})")
                    elif zombie > 0:
                        self.undead_zombie = max(0, zombie - 1)
                        logger.info(f"[UNDEAD] 좀비가 {self.name}를 대신 공격을 막았습니다! (남은 좀비: {self.undead_zombie})")
                    elif skeleton > 0:
                        self.undead_skeleton = max(0, skeleton - 1)
                        logger.info(f"[UNDEAD] 스켈레톤이 {self.name}를 대신 공격을 막았습니다! (남은 스켈레톤: {self.undead_skeleton})")
                    
                    # 미니언이 대신 받았으므로 데미지 0
                    return 0
        
        # ===== 차원술사: 차원 굴절 시스템 (특성 효과 전에 먼저 처리) =====
        if hasattr(self, 'gimmick_type') and self.gimmick_type == "dimension_refraction":
            # 피해 경감률 계산
            reduction = getattr(self, 'damage_reduction', 0.85)

            # 차원 안정화 특성 확인
            if hasattr(self, 'active_traits'):
                if any((t if isinstance(t, str) else t.get('id')) == 'dimensional_stabilization'
                       for t in self.active_traits):
                    reduction = 0.925  # 92.5% 경감

            # 경감량 계산
            refracted_amount = int(damage * reduction)
            actual_damage_after_refraction = damage - refracted_amount

            # 이중 차원 특성 확인 (추가 50% 경감)
            if hasattr(self, 'active_traits'):
                if any((t if isinstance(t, str) else t.get('id')) == 'double_refraction'
                       for t in self.active_traits):
                    actual_damage_after_refraction = int(actual_damage_after_refraction * 0.5)
                    logger.debug(f"[이중 차원] {self.name} 추가 피해 경감 -50%")

            # 굴절량 축적
            if not hasattr(self, 'refraction_stacks'):
                self.refraction_stacks = 0
            self.refraction_stacks += refracted_amount

            logger.info(
                f"[차원 굴절] {self.name} 피해 {damage} → {actual_damage_after_refraction} "
                f"(굴절량 +{refracted_amount}, 총 {self.refraction_stacks})"
            )

            damage = actual_damage_after_refraction

        # 특성 효과: 피해 감소 (damage_reduction, brave_soul 등)
        from src.character.trait_effects import get_trait_effect_manager
        trait_manager = get_trait_effect_manager()
        
        # 방어 중인지 확인 (수호 상태)
        is_defending = False
        if hasattr(self, 'status_manager'):
            from src.combat.status_effects import StatusType
            if hasattr(self.status_manager, 'has_status'):
                is_defending = self.status_manager.has_status(StatusType.GUARDIAN) or \
                               self.status_manager.has_status(StatusType.SHIELD)
        
        damage_reduction = trait_manager.calculate_damage_reduction(self, is_defending=is_defending)
        if damage_reduction > 0:
            damage = int(damage * (1.0 - damage_reduction))
        
        # 특성 효과: 수호 (guardian_angel) - 아군 피해 대신 받기
        # 이 효과는 combat_manager에서 처리되어야 함 (아군이 피해를 받을 때)
        # 여기서는 실제 데미지만 적용
        
        # 피해 받기 전 이벤트 발행 (수호 효과를 위해 - 피해를 줄이거나 대신 받기 위함)
        old_hp = self.current_hp
        damage_event_data = {
            "character": self,
            "damage": damage,
            "old_hp": old_hp,
            "new_hp": None,  # 아직 피해가 적용되지 않았음을 나타냄
            # 보호 효과를 위해 원본 정보 저장
            "original_damage": getattr(self, "_last_original_damage", None),  # 방어력 적용 전 원본 데미지
            "attacker": getattr(self, "_last_attacker", None),  # 마지막 공격자 정보
            "damage_type": getattr(self, "_last_damage_type", "physical"),  # 마지막 데미지 타입
            "brv_points": getattr(self, "_last_brv_points", 0),  # 마지막 BRV 포인트
            "hp_multiplier": getattr(self, "_last_hp_multiplier", 1.0),  # 마지막 HP 배율
            "is_break": getattr(self, "_last_is_break", False),  # 마지막 BREAK 상태
            "damage_kwargs": getattr(self, "_last_damage_kwargs", {})  # 마지막 데미지 kwargs
        }
        event_bus.publish(Events.COMBAT_DAMAGE_TAKEN, damage_event_data)
        
        # 이벤트 핸들러에서 수정된 피해를 사용 (수호 효과가 적용되었을 수 있음)
        # 수호 효과가 적용되면 이벤트 핸들러에서 damage_event_data["damage"]를 수정함
        final_damage = damage_event_data.get("damage", damage)
        
        # 1. 상태이상: 마나 실드 (MP로 피해 흡수) - 효율: MP 1당 HP 3
        # 일반 보호막보다 먼저 적용하여 MP를 소모하게 함 (선택적)
        if self.status_manager.has_status(StatusType.MANA_SHIELD) and self.current_mp > 0:
            # 막을 수 있는 최대 피해량 (MP * 3)
            max_absorb = self.current_mp * 3
            # 실제로 막을 피해량
            absorb_damage = min(final_damage, max_absorb)
            
            # 소모될 MP (올림 처리)
            mp_cost = (absorb_damage + 2) // 3
            
            if absorb_damage > 0:
                self.consume_mp(mp_cost)
                final_damage -= absorb_damage
                logger.info(f"[SHIELD] {self.name}의 마나 실드가 {absorb_damage} 데미지를 흡수했습니다! (소모 MP: {mp_cost})")
                
                # 마나 실드가 깨졌는지(MP 소진) 확인 - 이미 consume_mp에서 처리됨

        # 2. 일반 보호막이 있으면 데미지 흡수
        shield_amount = getattr(self, 'shield_amount', 0)
        if shield_amount > 0 and final_damage > 0:
            shield_absorbed = min(shield_amount, final_damage)
            self.shield_amount -= shield_absorbed
            final_damage -= shield_absorbed
            
            if shield_absorbed > 0:
                logger.info(f"[SHIELD] {self.name}의 보호막이 {shield_absorbed} 데미지를 흡수했습니다! (남은 보호막: {self.shield_amount})")
            
            # 보호막이 모두 소진되면 0으로 설정
            if self.shield_amount <= 0:
                self.shield_amount = 0
        
        actual_damage = min(final_damage, self.current_hp)
        self.current_hp -= actual_damage

        # 내구도 감소 (피해를 입었을 때)
        if actual_damage > 0:
            # 1. 방어구 내구도 감소 (모든 피해)
            if self.equipment.get("armor"):
                self.degrade_equipment("armor", 3)  # 3배 증가

                # 크리티컬 피해를 받았을 때 방어구 추가 내구도 감소
                is_critical_hit = damage_event_data.get("is_critical", False)
                if is_critical_hit:
                    self.degrade_equipment("armor", 2)  # 크리티컬 피격 시 +2 추가 감소

            # 2. 장신구 내구도 감소 (마법 피해일 때만)
            damage_type = damage_event_data.get("damage_type", "physical")
            if damage_type == "magical" and self.equipment.get("accessory"):
                self.degrade_equipment("accessory", 3)  # 3배 증가

                # 크리티컬 마법 피해 시 장신구 추가 감소
                is_critical_hit = damage_event_data.get("is_critical", False)
                if is_critical_hit:
                    self.degrade_equipment("accessory", 2)  # 크리티컬 피격 시 +2 추가 감소

        # 특성 효과: 보복 (retaliation) - 피해 받을 때마다 공격력 증가
        if actual_damage > 0 and hasattr(self, 'active_traits'):
            from src.character.trait_effects import TraitEffectType
            for trait_data in self.active_traits:
                trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                effects = trait_manager.get_trait_effects(trait_id)
                for effect in effects:
                    if effect.effect_type == TraitEffectType.RETALIATION:
                        # 스택 누적
                        stack_key = f"_retaliation_stacks_{trait_id}"
                        current_stacks = getattr(self, stack_key, 0)
                        max_stacks = effect.metadata.get("max_stacks", 3) if effect.metadata else 3
                        new_stacks = min(current_stacks + 1, max_stacks)
                        setattr(self, stack_key, new_stacks)
                        
                        # 공격력 증가 적용 (스탯 보너스로 적용)
                        bonus_per_stack = effect.value  # 0.05 = 5% per stack
                        total_bonus = bonus_per_stack * new_stacks
                        from src.character.stats import Stats
                        if hasattr(self, 'stat_manager'):
                            # 기존 보너스 제거 후 새 보너스 추가
                            self.stat_manager.remove_bonus(Stats.STRENGTH, f"retaliation_{trait_id}")
                            self.stat_manager.remove_bonus(Stats.MAGIC, f"retaliation_{trait_id}")
                            bonus_atk = int(self.stat_manager.get_value(Stats.STRENGTH, use_total=False) * total_bonus)
                            bonus_mag = int(self.stat_manager.get_value(Stats.MAGIC, use_total=False) * total_bonus)
                            if bonus_atk > 0:
                                self.stat_manager.add_bonus(Stats.STRENGTH, f"retaliation_{trait_id}", bonus_atk)
                            if bonus_mag > 0:
                                self.stat_manager.add_bonus(Stats.MAGIC, f"retaliation_{trait_id}", bonus_mag)
                            
                            logger.info(f"[{trait_id}] {self.name} 보복: 스택 {new_stacks}/{max_stacks} → 공격력 +{int(total_bonus * 100)}%")

        if self.current_hp <= 0:
            self.current_hp = 0
            # 불멸의 존재 특성이 있으면 is_alive 유지
            if not self._has_undying_existence():
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

    def take_fixed_damage(self, damage: int) -> int:
        """
        고정 피해를 받습니다 (방어력 무시, 보호막 무시)

        Args:
            damage: 고정 피해량

        Returns:
            실제로 받은 피해
        """
        actual_damage = min(damage, self.current_hp)
        self.current_hp -= actual_damage

        # 상처 적용 (차원 굴절 지연 피해도 상처로 계산)
        from src.systems.wound_system import get_wound_system
        wound_system = get_wound_system()
        if wound_system.enabled and actual_damage > 0:
            wound_amount = int(actual_damage * wound_system.wound_threshold)
            max_wound = int(self.max_hp * wound_system.max_wound_percentage)
            current_wound = getattr(self, "wound", 0)

            if current_wound + wound_amount > max_wound:
                wound_amount = max(0, max_wound - current_wound)

            if wound_amount > 0:
                if not hasattr(self, "wound"):
                    self.wound = 0
                self.wound += wound_amount
                logger.debug(f"[고정 피해 상처] {self.name} +{wound_amount} wound (총 {self.wound}/{max_wound})")

            # 중복 적용 방지 플래그 설정
            self._wound_applied_this_turn = True

        if self.current_hp <= 0:
            self.current_hp = 0
            # 불멸의 존재 특성이 있으면 is_alive 유지
            if not self._has_undying_existence():
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

        # 플래그 해제
        if hasattr(self, "_wound_applied_this_turn"):
            self._wound_applied_this_turn = False

        return actual_damage

    def _has_undying_existence(self) -> bool:
        """불멸의 존재 특성이 있는지 확인"""
        if not hasattr(self, 'active_traits'):
            return False

        has_trait = any(
            (t if isinstance(t, str) else t.get('id')) == 'undying_existence'
            for t in self.active_traits
        )

        if not has_trait:
            return False

        # 차원 굴절 기믹이어야 함
        if getattr(self, 'gimmick_type', None) != "dimension_refraction":
            return False

        # 다른 아군이 살아있는지 확인 (combat_manager가 있는 경우)
        if hasattr(self, '_combat_manager') and self._combat_manager:
            try:
                allies = self._combat_manager.allies
                other_allies_alive = any(
                    ally != self and ally.current_hp > 0
                    for ally in allies
                )
                return other_allies_alive
            except:
                return False

        return False

    def heal(self, amount: int, can_revive: bool = False, source_character=None, is_self_skill: bool = False) -> int:
        """
        HP를 회복합니다 (상처 시스템 적용)

        Args:
            amount: 회복량
            can_revive: 죽은 캐릭터도 회복 가능한지 여부 (음식 등)
            source_character: 회복을 제공한 캐릭터 (자가 치유 특화 특성용)
            is_self_skill: 본인 스킬로 인한 회복인지 여부

        Returns:
            실제로 회복한 양
        """
        # ===== 차원술사: 자가 치유 특화 특성 =====
        if hasattr(self, 'gimmick_type') and self.gimmick_type == "dimension_refraction":
            if hasattr(self, 'active_traits'):
                has_self_healing = any(
                    (t if isinstance(t, str) else t.get('id')) == 'self_healing_mastery'
                    for t in self.active_traits
                )

                if has_self_healing:
                    # 본인 스킬인지 확인
                    is_self = (source_character == self) or is_self_skill

                    if is_self:
                        # 본인 스킬: 200% 증가 (×3.0)
                        amount = int(amount * 3.0)
                        logger.info(f"[자가 치유] {self.name} 회복량 3배: {amount}")
                    else:
                        # 외부 회복: 80% 감소 (×0.2)
                        amount = int(amount * 0.2)
                        logger.info(f"[외부 회복 저항] {self.name} 회복량 80% 감소: {amount}")

        old_hp = self.current_hp
        was_dead = not getattr(self, 'is_alive', True)
        
        # 죽은 캐릭터 회복 처리
        if was_dead:
            if can_revive and amount > 0:
                self.is_alive = True
                # 부활 시에는 상처를 고려하지 않고 일단 회복 (혹은 부활 로직에 따라 다름)
                # 여기서는 일단 1로 부활 후 일반 회복 로직을 태우거나, 
                # 단순히 amount만큼 회복하되 상처 제한을 받을지 결정해야 함.
                # 보통 부활은 상처 영향을 받음.
                self.current_hp = 0 # 0에서 시작
            else:
                return 0

        # 상처 시스템 적용
        wound = getattr(self, 'wound', 0)
        effective_max_hp = self.max_hp - wound
        
        # 1. 일반 회복 (상처 제한까지)
        healable_amount = max(0, effective_max_hp - self.current_hp)
        normal_heal = min(amount, healable_amount)
        
        self.current_hp += normal_heal
        remaining_heal = amount - normal_heal
        
        # 2. 초과 회복량으로 상처 치료 (1/4 효율)
        wound_healed = 0
        if remaining_heal > 0 and wound > 0:
            # 남은 회복량의 1/4만큼 상처가 사라짐
            wound_cure_amount = int(remaining_heal * 0.25)
            
            if wound_cure_amount > 0:
                actual_wound_cure = min(wound_cure_amount, wound)
                self.wound -= actual_wound_cure
                wound_healed = actual_wound_cure
                
                # 상처가 사라진 만큼 HP도 추가 회복 (상처가 사라져서 최대 체력이 늘어났으므로)
                # "상처가 사라지고 그만큼 회복이 되어야 해" -> 상처 치료량만큼 HP도 증가
                self.current_hp += actual_wound_cure
                
                logger.info(f"{self.name} 상처 치료: -{actual_wound_cure} (초과 회복 {remaining_heal}의 1/4)")

        # 최대 HP 보정 (혹시 모를 오버플로우 방지)
        self.current_hp = min(self.current_hp, self.max_hp - getattr(self, 'wound', 0))
        
        actual_heal = self.current_hp - old_hp

        event_bus.publish(Events.CHARACTER_HP_CHANGE, {
            "character": self,
            "change": actual_heal,
            "current": self.current_hp,
            "max": self.max_hp,
            "wound_healed": wound_healed
        })

        return actual_heal

    def consume_mp(self, amount: int, silent: bool = False) -> bool:
        """
        MP를 소비합니다

        Args:
            amount: 소비량
            silent: True이면 이벤트를 발행하지 않음 (무한 루프 방지)

        Returns:
            성공 여부
        """
        if self.current_mp < amount:
            return False

        self.current_mp -= amount

        # 무한 루프 방지: silent 플래그가 True이면 이벤트 발행 안 함
        if not silent:
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

        # 레벨 제한 체크
        item_level_req = getattr(item, 'level_requirement', 1)
        if item_level_req > self.level:
            item_name = getattr(item, 'name', '알 수 없는 아이템')
            self.logger.warning(f"{self.name}은(는) 레벨 {item_level_req} 이상이어야 {item_name}을(를) 장착할 수 있습니다. (현재 레벨: {self.level})")
            return

        # 기존 장비 해제
        if self.equipment[slot]:
            self.unequip_item(slot)

        self.equipment[slot] = item

        # 스탯 이름 매핑 (장비 스탯 이름 → StatManager 스탯 이름)
        stat_mapping = {
            "physical_attack": Stats.STRENGTH,
            "physical_defense": Stats.DEFENSE,
            "magic_attack": Stats.MAGIC,
            "magic_defense": Stats.SPIRIT,
            "hp": Stats.HP,
            "max_hp": Stats.HP,  # max_hp도 HP로 매핑
            "mp": Stats.MP,
            "max_mp": Stats.MP,  # max_mp도 MP로 매핑
            "speed": Stats.SPEED,
            "accuracy": Stats.ACCURACY,
            "evasion": Stats.EVASION,
            "luck": Stats.LUCK,
            "init_brv": Stats.INIT_BRV,
            "max_brv": Stats.MAX_BRV,
            "strength": Stats.STRENGTH,  # 직접 매핑도 지원
            "defense": Stats.DEFENSE,
            "magic": Stats.MAGIC,
            "spirit": Stats.SPIRIT,
        }

        # 장비 보너스 적용 (get_total_stats 메서드 사용)
        if hasattr(item, "get_total_stats"):
            total_stats = item.get_total_stats()
            # 현재 최대 HP/MP 값 (퍼센트 옵션 계산용)
            current_max_hp = self.max_hp
            current_max_mp = self.max_mp
            
            # 추가옵션(affixes)에서 퍼센트 옵션 확인
            if hasattr(item, "affixes"):
                for affix in item.affixes:
                    # 최대 HP % 증가 옵션 처리
                    if affix.is_percentage and affix.stat in ["max_hp", "hp", "max_hp_percent", "hp_percent"]:
                        # 캐릭터의 현재 최대 HP를 기준으로 계산
                        actual_bonus = int(current_max_hp * affix.value)
                        mapped_stat = Stats.HP
                        self.stat_manager.add_bonus(mapped_stat, f"equipment_{slot}_percent", actual_bonus)
                        self.logger.debug(f"장비 스탯 적용 (퍼센트): {self.name} - {affix.stat} ({affix.value*100}%) → {mapped_stat} +{actual_bonus} (현재 최대 HP: {current_max_hp}, {slot})")
                    # 최대 MP % 증가 옵션 처리
                    elif affix.is_percentage and affix.stat in ["max_mp", "mp", "max_mp_percent", "mp_percent"]:
                        # 캐릭터의 현재 최대 MP를 기준으로 계산
                        actual_bonus = int(current_max_mp * affix.value)
                        mapped_stat = Stats.MP
                        self.stat_manager.add_bonus(mapped_stat, f"equipment_{slot}_percent", actual_bonus)
                        self.logger.debug(f"장비 스탯 적용 (퍼센트): {self.name} - {affix.stat} ({affix.value*100}%) → {mapped_stat} +{actual_bonus} (현재 최대 MP: {current_max_mp}, {slot})")
            
            # 일반 스탯 적용 (퍼센트 옵션이 아닌 것들)
            for stat_name, bonus in total_stats.items():
                # 퍼센트 옵션은 이미 위에서 처리했으므로 스킵
                if stat_name in ["max_hp_percent", "hp_percent", "max_mp_percent", "mp_percent"]:
                    continue
                # 퍼센트 옵션이 기본 스탯에 없어서 그대로 들어간 경우도 스킵 (affixes에서 처리됨)
                if hasattr(item, "affixes"):
                    skip = False
                    for affix in item.affixes:
                        if affix.is_percentage and affix.stat == stat_name and stat_name in ["max_hp", "hp", "max_mp", "mp"]:
                            skip = True
                            break
                    if skip:
                        continue
                
                mapped_stat = stat_mapping.get(stat_name, stat_name)
                self.stat_manager.add_bonus(mapped_stat, f"equipment_{slot}", bonus)
                self.logger.debug(f"장비 스탯 적용: {self.name} - {stat_name} → {mapped_stat} +{bonus} ({slot})")
        elif hasattr(item, "stat_bonuses"):
            # 구 방식 호환성 유지
            for stat_name, bonus in item.stat_bonuses.items():
                mapped_stat = stat_mapping.get(stat_name, stat_name)
                self.stat_manager.add_bonus(mapped_stat, f"equipment_{slot}", bonus)

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

        # 스탯 이름 매핑 (장비 스탯 이름 → StatManager 스탯 이름)
        stat_mapping = {
            "physical_attack": Stats.STRENGTH,
            "physical_defense": Stats.DEFENSE,
            "magic_attack": Stats.MAGIC,
            "magic_defense": Stats.SPIRIT,
            "hp": Stats.HP,
            "max_hp": Stats.HP,  # max_hp도 HP로 매핑
            "mp": Stats.MP,
            "max_mp": Stats.MP,  # max_mp도 MP로 매핑
            "speed": Stats.SPEED,
            "accuracy": Stats.ACCURACY,
            "evasion": Stats.EVASION,
            "luck": Stats.LUCK,
            "init_brv": Stats.INIT_BRV,
            "max_brv": Stats.MAX_BRV,
            "strength": Stats.STRENGTH,  # 직접 매핑도 지원
            "defense": Stats.DEFENSE,
            "magic": Stats.MAGIC,
            "spirit": Stats.SPIRIT,
        }

        # HP/MP 증가 효과가 있는지 확인 (제거 후 현재값이 최대값을 초과할 수 있으므로)
        had_hp_bonus = False
        had_mp_bonus = False
        old_max_hp = self.max_hp
        old_max_mp = self.max_mp
        
        # 추가옵션(affixes)에서 퍼센트 옵션 제거
        if hasattr(item, "affixes"):
            for affix in item.affixes:
                # 최대 HP % 증가 옵션 제거
                if affix.is_percentage and affix.stat in ["max_hp", "hp", "max_hp_percent", "hp_percent"]:
                    self.stat_manager.remove_bonus(Stats.HP, f"equipment_{slot}_percent")
                    had_hp_bonus = True
                    self.logger.debug(f"장비 스탯 제거 (퍼센트): {self.name} - {affix.stat} ({affix.value*100}%) → HP ({slot})")
                # 최대 MP % 증가 옵션 제거
                elif affix.is_percentage and affix.stat in ["max_mp", "mp", "max_mp_percent", "mp_percent"]:
                    self.stat_manager.remove_bonus(Stats.MP, f"equipment_{slot}_percent")
                    had_mp_bonus = True
                    self.logger.debug(f"장비 스탯 제거 (퍼센트): {self.name} - {affix.stat} ({affix.value*100}%) → MP ({slot})")
        
        # 장비 보너스 제거 (get_total_stats 메서드 사용)
        if hasattr(item, "get_total_stats"):
            total_stats = item.get_total_stats()
            for stat_name in total_stats.keys():
                # 퍼센트 옵션은 이미 위에서 처리했으므로 스킵
                if stat_name in ["max_hp_percent", "hp_percent", "max_mp_percent", "mp_percent"]:
                    continue
                # 퍼센트 옵션이 기본 스탯에 없어서 그대로 들어간 경우도 스킵 (affixes에서 처리됨)
                if hasattr(item, "affixes"):
                    skip = False
                    for affix in item.affixes:
                        if affix.is_percentage and affix.stat == stat_name and stat_name in ["max_hp", "hp", "max_mp", "mp"]:
                            skip = True
                            break
                    if skip:
                        continue
                
                # 매핑된 스탯 이름 사용
                mapped_stat = stat_mapping.get(stat_name, stat_name)
                # HP/MP 보너스 확인
                if stat_name in ("hp", "HP") or mapped_stat == Stats.HP:
                    had_hp_bonus = True
                if stat_name in ("mp", "MP") or mapped_stat == Stats.MP:
                    had_mp_bonus = True
                
                self.stat_manager.remove_bonus(mapped_stat, f"equipment_{slot}")
                self.logger.debug(f"장비 스탯 제거: {self.name} - {stat_name} → {mapped_stat} ({slot})")
        elif hasattr(item, "stat_bonuses"):
            # 구 방식 호환성 유지
            for stat_name in item.stat_bonuses.keys():
                mapped_stat = stat_mapping.get(stat_name, stat_name)
                # HP/MP 보너스 확인
                if stat_name in ("hp", "HP") or mapped_stat == Stats.HP:
                    had_hp_bonus = True
                if stat_name in ("mp", "MP") or mapped_stat == Stats.MP:
                    had_mp_bonus = True
                
                self.stat_manager.remove_bonus(mapped_stat, f"equipment_{slot}")

        self.equipment[slot] = None

        # 최대 HP/MP가 줄어든 경우, 현재 HP/MP가 새로운 최대값을 초과하면 제한
        new_max_hp = self.max_hp
        new_max_mp = self.max_mp
        
        if had_hp_bonus and new_max_hp < old_max_hp:
            if self.current_hp > new_max_hp:
                self.logger.debug(f"{self.name} HP 제한: {self.current_hp} → {new_max_hp} (최대값 감소)")
                self.current_hp = new_max_hp
        
        if had_mp_bonus and new_max_mp < old_max_mp:
            if self.current_mp > new_max_mp:
                self.logger.debug(f"{self.name} MP 제한: {self.current_mp} → {new_max_mp} (최대값 감소)")
                self.current_mp = new_max_mp

        event_bus.publish(Events.EQUIPMENT_UNEQUIPPED, {
            "character": self,
            "slot": slot,
            "item": item
        })

        return item

    def update_equipment_stats(self, slot: str) -> None:
        """장비 스탯 재계산 (내구도 변경 시 호출)"""
        item = self.equipment.get(slot)
        
        # 1. 기존 보너스 제거
        # 스탯 이름 매핑
        stat_mapping = {
            "physical_attack": Stats.STRENGTH,
            "physical_defense": Stats.DEFENSE,
            "magic_attack": Stats.MAGIC,
            "magic_defense": Stats.SPIRIT,
            "hp": Stats.HP,
            "max_hp": Stats.HP,  # max_hp도 HP로 매핑
            "mp": Stats.MP,
            "max_mp": Stats.MP,  # max_mp도 MP로 매핑
            "speed": Stats.SPEED,
            "accuracy": Stats.ACCURACY,
            "evasion": Stats.EVASION,
            "luck": Stats.LUCK,
            "init_brv": Stats.INIT_BRV,
            "max_brv": Stats.MAX_BRV,
            "strength": Stats.STRENGTH,
            "defense": Stats.DEFENSE,
            "magic": Stats.MAGIC,
            "spirit": Stats.SPIRIT,
        }

        # 모든 가능한 스탯에 대해 보너스 제거 시도 (어떤 스탯이 있었는지 모르므로)
        # 또는 StatManager의 bonuses 딕셔너리를 순회하며 해당 source를 가진 보너스 제거가 이상적이나
        # 현재 StatManager 구조상 remove_bonus는 key가 필요함.
        # 따라서 일반적인 스탯들을 모두 순회하며 제거 시도.
        stat_keys = [Stats.HP, Stats.MP, Stats.INIT_BRV, Stats.MAX_BRV, Stats.STRENGTH, Stats.DEFENSE,
                     Stats.MAGIC, Stats.SPIRIT, Stats.SPEED, Stats.LUCK, Stats.ACCURACY, Stats.EVASION,
                     Stats.STAMINA, Stats.VITALITY, Stats.DEXTERITY, Stats.PERCEPTION, Stats.ENDURANCE, Stats.CHARISMA]
        for stat_key in stat_keys:
            self.stat_manager.remove_bonus(stat_key, f"equipment_{slot}")
            self.stat_manager.remove_bonus(stat_key, f"equipment_{slot}_percent")  # 퍼센트 옵션도 제거

        if not item:
            return

        # 2. 새 보너스 적용 (내구도 반영된 get_total_stats 사용)
        if hasattr(item, "get_total_stats"):
            total_stats = item.get_total_stats()
            # 현재 최대 HP/MP 값 (퍼센트 옵션 계산용)
            current_max_hp = self.max_hp
            current_max_mp = self.max_mp
            
            # 추가옵션(affixes)에서 퍼센트 옵션 확인
            if hasattr(item, "affixes"):
                for affix in item.affixes:
                    # 최대 HP % 증가 옵션 처리
                    if affix.is_percentage and affix.stat in ["max_hp", "hp", "max_hp_percent", "hp_percent"]:
                        actual_bonus = int(current_max_hp * affix.value)
                        mapped_stat = Stats.HP
                        self.stat_manager.add_bonus(mapped_stat, f"equipment_{slot}_percent", actual_bonus)
                        self.logger.debug(f"장비 스탯 재계산 (퍼센트): {self.name} - {affix.stat} ({affix.value*100}%) → {mapped_stat} +{actual_bonus} ({slot})")
                    # 최대 MP % 증가 옵션 처리
                    elif affix.is_percentage and affix.stat in ["max_mp", "mp", "max_mp_percent", "mp_percent"]:
                        actual_bonus = int(current_max_mp * affix.value)
                        mapped_stat = Stats.MP
                        self.stat_manager.add_bonus(mapped_stat, f"equipment_{slot}_percent", actual_bonus)
                        self.logger.debug(f"장비 스탯 재계산 (퍼센트): {self.name} - {affix.stat} ({affix.value*100}%) → {mapped_stat} +{actual_bonus} ({slot})")
            
            # 일반 스탯 적용 (퍼센트 옵션이 아닌 것들)
            for stat_name, bonus in total_stats.items():
                # 퍼센트 옵션은 이미 위에서 처리했으므로 스킵
                if stat_name in ["max_hp_percent", "hp_percent", "max_mp_percent", "mp_percent"]:
                    continue
                # 퍼센트 옵션이 기본 스탯에 없어서 그대로 들어간 경우도 스킵 (affixes에서 처리됨)
                if hasattr(item, "affixes"):
                    skip = False
                    for affix in item.affixes:
                        if affix.is_percentage and affix.stat == stat_name and stat_name in ["max_hp", "hp", "max_mp", "mp"]:
                            skip = True
                            break
                    if skip:
                        continue
                
                mapped_stat = stat_mapping.get(stat_name, stat_name)
                self.stat_manager.add_bonus(mapped_stat, f"equipment_{slot}", bonus)

    def degrade_equipment(self, slot: str, amount: int = 1) -> bool:
        """
        장비 내구도 감소
        
        Args:
            slot: 장비 슬롯
            amount: 감소량
            
        Returns:
            파괴 여부 (True if broken this time)
        """
        item = self.equipment.get(slot)
        if not item:
            return False
            
        if not hasattr(item, 'current_durability'):
            return False
            
        if item.current_durability <= 0:
            return False
            
        old_state = item.current_durability > 0
        item.current_durability = max(0, item.current_durability - amount)
        new_state = item.current_durability > 0
        
        # 내구도가 0이 되어 파괴된 경우 (또는 그 반대) 스탯 업데이트
        if old_state != new_state:
            if not new_state:
                # 내구도 0 -> 파괴됨
                self.logger.warning(f"{self.name}의 {item.name}이(가) 내구도가 다해 파괴되었습니다!")
                self.unequip_item(slot)  # 장착 해제 (인벤토리로 돌아가지 않고 소멸됨)
                return True
            else:
                self.update_equipment_stats(slot)
                
        return False

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
            stat_enum = self._stat_name_to_enum(stat_name)
            if stat_enum:
                # 기존 trait 보너스 제거 (중복 방지)
                self.stat_manager.remove_bonus(stat_enum, f"trait_{stat_name}")
                
                # 새로운 보너스 적용
                if bonus_value != base_value:
                    bonus_diff = bonus_value - base_value
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
