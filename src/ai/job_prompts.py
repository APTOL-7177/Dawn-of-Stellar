"""
직업별 전략 데이터 및 시스템 프롬프트 생성기

Dawn of Stellar 35개 직업의 역할, 우선 행동, 기믹 규칙을
구조화된 데이터로 관리하고, LLM 시스템 프롬프트를 동적으로 생성합니다.
"""

from dataclasses import dataclass, field
from typing import Dict, List

from src.core.logger import get_logger

logger = get_logger("ai.job_prompts")


# =============================================================================
# 데이터 클래스
# =============================================================================

@dataclass
class JobStrategy:
    """직업별 전략 데이터"""
    job_id: str                         # 직업 ID (영문 소문자)
    job_name: str                       # 직업 한글명
    role: str                           # 역할: tank / healer / dps_physical / dps_magical / buffer / debuffer / utility
    priority_actions: List[str]         # 우선 행동 유형 목록 (순서 중요)
    gimmick_rules: List[str]            # 기믹 관리 규칙 (문자열 목록)
    target_bias: str                    # 타겟 선택 편향: "lowest_hp" / "highest_brv" / "broken_enemy" / "debuffed_enemy"
    emergency_threshold: float          # 긴급 상황 HP% 임계값 (예: 0.3 = 30%)
    extra_notes: List[str] = field(default_factory=list)  # 추가 전략 메모


# =============================================================================
# 35개 직업 전략 데이터
# =============================================================================

JOB_STRATEGIES: Dict[str, JobStrategy] = {

    # =========================================================================
    # 물리 딜러 (dps_physical)
    # =========================================================================

    "warrior": JobStrategy(
        job_id="warrior",
        job_name="전사",
        role="dps_physical",
        priority_actions=["skill_stance_switch", "brv_attack", "hp_attack"],
        gimmick_rules=[
            "attack_stance 사용 시 공격력 증가, 방어력 감소 — 적 수가 많으면 defensive_stance로 전환",
            "balanced_stance는 무난한 기본값, 상황에 따라 스탠스 교체",
            "BRV 쌓은 후 HP 공격으로 마무리",
        ],
        target_bias="highest_brv",
        emergency_threshold=0.3,
    ),

    "archer": JobStrategy(
        job_id="archer",
        job_name="궁수",
        role="dps_physical",
        priority_actions=["skill_mark", "brv_attack", "hp_attack"],
        gimmick_rules=[
            "mark_fire / mark_ice / mark_poison 으로 적에게 화살 설치 (최대 3개)",
            "화살 3개 설치 후 HP 공격 — 자동 발사로 폭딜",
            "원소 화살로 약점 속성 부여 가능",
        ],
        target_bias="lowest_hp",
        emergency_threshold=0.35,
    ),

    "assassin": JobStrategy(
        job_id="assassin",
        job_name="암살자",
        role="dps_physical",
        priority_actions=["skill_vanish", "skill_backstab", "hp_attack"],
        gimmick_rules=[
            "vanish 로 은신 → 은신 중 backstab / assassinate 사용 시 치명타 보너스",
            "공격 후 노출됨 → 재은신 반복이 핵심 사이클",
            "은신 없이 쓰는 일반 공격은 효율 저하",
        ],
        target_bias="lowest_hp",
        emergency_threshold=0.25,
        extra_notes=["은신 중 스킬 우선 — 노출 상태에서는 BRV 쌓기"],
    ),

    "berserker": JobStrategy(
        job_id="버서커",
        job_name="버서커",
        role="dps_physical",
        priority_actions=["skill_blood_rage", "brv_attack", "hp_attack"],
        gimmick_rules=[
            "HP 낮을수록 광기(Madness) 스택 증가 → 데미지 상승",
            "self_harm 으로 의도적으로 HP 소모해 광기 축적 가능",
            "광기 최고점에서 blood_rage 발동 — 폭딜 타이밍",
            "HP 30% 미만이면 healing_roar 로 회복 우선",
        ],
        target_bias="broken_enemy",
        emergency_threshold=0.2,
        extra_notes=["리스크 높은 직업 — healing_roar 쿨다운 주시"],
    ),

    "breaker": JobStrategy(
        job_id="breaker",
        job_name="브레이커",
        role="dps_physical",
        priority_actions=["brv_attack", "skill_crush", "skill_mega_crush"],
        gimmick_rules=[
            "BRV 공격마다 파괴력(Destruction) 게이지 증가",
            "파괴력 높을수록 BREAK 보너스 증가",
            "crush / break_hit 으로 게이지 빠르게 축적",
            "게이지 최대 시 mega_crush 발동 — BREAK 특화 딜",
        ],
        target_bias="highest_brv",
        emergency_threshold=0.3,
    ),

    "gladiator": JobStrategy(
        job_id="gladiator",
        job_name="검투사",
        role="dps_physical",
        priority_actions=["skill_taunt", "skill_spectacular", "skill_glory_strike"],
        gimmick_rules=[
            "spectacular / risky_stunt 같은 화려한 스킬로 환호(Ovation) 게이지 축적",
            "환호 게이지 높을수록 공격/방어 버프 증가",
            "taunt 로 어그로 확보 후 glory_strike 로 마무리",
            "위험한 스킬 성공 시 환호 대폭 상승",
        ],
        target_bias="highest_brv",
        emergency_threshold=0.3,
    ),

    "monk": JobStrategy(
        job_id="monk",
        job_name="몽크",
        role="dps_physical",
        priority_actions=["skill_yin_strike", "skill_yang_strike", "skill_taichi_flow"],
        gimmick_rules=[
            "yin_strike 로 음기 증가, yang_strike 로 양기 증가",
            "음양 균형(각 50) 맞추면 버프 발동",
            "한쪽 극대화(yin_extreme / yang_extreme)도 강력",
            "균형 또는 극화 상태에서 taichi_flow 로 폭발",
        ],
        target_bias="lowest_hp",
        emergency_threshold=0.3,
    ),

    "rogue": JobStrategy(
        job_id="rogue",
        job_name="로그",
        role="dps_physical",
        priority_actions=["skill_steal", "skill_smoke", "skill_vital_strike"],
        gimmick_rules=[
            "steal 로 적 아이템 탈취 후 use_item 으로 활용",
            "smoke 로 회피율 증가 후 연타 공격",
            "ambush → vital_strike → backstab 콤보가 핵심",
        ],
        target_bias="lowest_hp",
        emergency_threshold=0.3,
    ),

    "samurai": JobStrategy(
        job_id="samurai",
        job_name="사무라이",
        role="dps_physical",
        priority_actions=["skill_clear_mind", "skill_battojutsu", "skill_true_battojutsu"],
        gimmick_rules=[
            "clear_mind 로 집중(Focus) 게이지 축적",
            "집중 높을수록 battojutsu / iaido 치명타 확률 증가",
            "true_battojutsu 는 집중 전부 소모 — 최대 집중 시 사용",
        ],
        target_bias="lowest_hp",
        emergency_threshold=0.25,
    ),

    "sniper": JobStrategy(
        job_id="sniper",
        job_name="스나이퍼",
        role="dps_physical",
        priority_actions=["skill_reload", "skill_perfect_aim", "skill_headshot"],
        gimmick_rules=[
            "reload 로 탄창 충전, load_penetrating / load_explosive 로 특수탄 장전",
            "perfect_aim 으로 정조준 후 headshot — 단발 폭딜",
            "탄창 관리가 핵심, 빈 탄창에 강력 스킬 사용 불가",
        ],
        target_bias="lowest_hp",
        emergency_threshold=0.3,
    ),

    "sword_saint": JobStrategy(
        job_id="sword_saint",
        job_name="검성",
        role="dps_physical",
        priority_actions=["skill_kenkizan", "skill_ilseom", "skill_kenki_hadou"],
        gimmick_rules=[
            "공격할수록 검기(Kenki) 게이지 증가",
            "검기 높을수록 스킬 데미지 증가",
            "kenki_hadou / bisect 로 검기 방출",
            "게이지 최대 시 sword_storm — 광역 폭딜",
        ],
        target_bias="broken_enemy",
        emergency_threshold=0.3,
    ),

    # =========================================================================
    # 마법 딜러 (dps_magical)
    # =========================================================================

    "archmage": JobStrategy(
        job_id="archmage",
        job_name="대마법사",
        role="dps_magical",
        priority_actions=["skill_fire", "skill_ice", "skill_lightning", "skill_elemental_surge"],
        gimmick_rules=[
            "불/얼음/번개 3원소를 번갈아 사용하면 조합 카운터 증가",
            "카운터 3 도달 시 elemental_surge 자동 발동 — 대폭딜",
            "같은 원소 연속 사용은 카운터 초기화로 비효율",
        ],
        target_bias="lowest_hp",
        emergency_threshold=0.3,
    ),

    "battle_mage": JobStrategy(
        job_id="battle_mage",
        job_name="배틀메이지",
        role="dps_magical",
        priority_actions=["skill_carve_rune", "skill_rune_burst", "skill_elemental_fusion"],
        gimmick_rules=[
            "carve_rune 으로 룬 새기고, 원소룬으로 속성 부여",
            "룬 다수 축적 후 rune_burst 로 폭발",
            "룬 4개 이상 시 elemental_fusion 최대 효율",
        ],
        target_bias="highest_brv",
        emergency_threshold=0.3,
    ),

    "spellblade": JobStrategy(
        job_id="spellblade",
        job_name="스펠블레이드",
        role="dps_magical",
        priority_actions=["skill_fire_infusion", "skill_magic_slash", "skill_elemental_slash"],
        gimmick_rules=[
            "fire / ice / lightning_infusion 으로 무기에 속성 부여 (지속 효과)",
            "부여 후 magic_slash / elemental_slash 로 속성 물리 공격",
            "부여 유지하면서 연타가 핵심",
        ],
        target_bias="debuffed_enemy",
        emergency_threshold=0.3,
    ),

    "necromancer": JobStrategy(
        job_id="necromancer",
        job_name="강령술사",
        role="dps_magical",
        priority_actions=["skill_summon_skeleton", "skill_summon_zombie", "skill_sacrifice_undead", "skill_legion_command"],
        gimmick_rules=[
            "summon_skeleton / zombie / ghost 로 언데드 소환 → 자동 공격",
            "언데드 3기 이상 시 sacrifice_undead 로 터뜨려 폭딜",
            "legion_command 로 전체 지휘 — 효과 극대화",
        ],
        target_bias="lowest_hp",
        emergency_threshold=0.35,
    ),

    "elementalist": JobStrategy(
        job_id="elementalist",
        job_name="정령술사",
        role="dps_magical",
        priority_actions=["skill_summon_fire", "skill_summon_water", "skill_spirit_burst", "skill_fusion_firestorm"],
        gimmick_rules=[
            "summon_fire / water / wind / earth 로 정령 소환",
            "spirit_burst 로 정령 폭발 — 단일 정령 폭딜",
            "2정령 조합 fusion_firestorm / mudtrap / steam 상황별 선택",
        ],
        target_bias="highest_brv",
        emergency_threshold=0.3,
    ),

    # =========================================================================
    # 탱커 (tank)
    # =========================================================================

    "warrior": JobStrategy(  # type: ignore[misc]  # 아래에서 재정의 (tank 전사는 별도 키 없음, 위 dps_physical 전사 사용)
        job_id="warrior",
        job_name="전사",
        role="dps_physical",
        priority_actions=["skill_stance_switch", "brv_attack", "hp_attack"],
        gimmick_rules=[
            "attack_stance: 공격력↑, 방어력↓ — 적 소수일 때",
            "defensive_stance: 방어력↑ — 적 다수 또는 HP 낮을 때",
            "BRV 충분히 쌓고 HP 공격",
        ],
        target_bias="highest_brv",
        emergency_threshold=0.3,
    ),

    "paladin": JobStrategy(
        job_id="paladin",
        job_name="팔라딘",
        role="tank",
        priority_actions=["skill_divine_shield", "skill_holy_light", "skill_blessing", "brv_attack"],
        gimmick_rules=[
            "힐/보호 스킬 사용마다 신성(Divinity) 게이지 증가",
            "신성 높을수록 holy 계열 스킬 강화",
            "divine_shield 로 파티 전체 보호막",
            "holy_light 로 자힐, blessing 으로 파티 버프",
        ],
        target_bias="highest_brv",
        emergency_threshold=0.4,
    ),

    "dimensionist": JobStrategy(
        job_id="dimensionist",
        job_name="차원술사",
        role="tank",
        priority_actions=["skill_dimension_barrier", "skill_refraction_strike", "skill_refraction_release"],
        gimmick_rules=[
            "refraction_strike 로 받은 피해를 저장",
            "저장량 최대 시 refraction_release 로 반사 — 피해 → 딜로 전환",
            "dimension_barrier 로 파티 보호",
            "맞으면서 반격하는 역발상 플레이",
        ],
        target_bias="highest_brv",
        emergency_threshold=0.4,
    ),

    "dark_knight": JobStrategy(
        job_id="dark_knight",
        job_name="암흑기사",
        role="tank",
        priority_actions=["skill_charge_strike", "skill_crushing_blow", "skill_dark_regeneration"],
        gimmick_rules=[
            "charge_strike 로 충전(Charge) 게이지 증가",
            "충전 높을수록 crushing_blow / execution 데미지 폭증",
            "HP 소모 스킬 다수 — dark_regeneration 으로 자힐 필수",
            "충전 → 방출 사이클 반복",
        ],
        target_bias="highest_brv",
        emergency_threshold=0.35,
    ),

    "dragon_knight": JobStrategy(
        job_id="dragon_knight",
        job_name="용기사",
        role="tank",
        priority_actions=["skill_dragon_mark", "skill_dragon_mark_strike", "skill_dragon_scales", "skill_dragon_storm"],
        gimmick_rules=[
            "화염 스킬로 적에게 각인(Dragon Mark) 최대 3개 설치",
            "dragon_mark_strike 로 각인 전부 폭발",
            "dragon_scales 로 자신 방어 강화",
            "dragon_storm 은 궁극기 — 각인 최대 시 사용",
        ],
        target_bias="debuffed_enemy",
        emergency_threshold=0.35,
    ),

    "knight": JobStrategy(
        job_id="knight",
        job_name="기사",
        role="tank",
        priority_actions=["skill_oath", "skill_iron_will", "skill_chivalry", "brv_attack"],
        gimmick_rules=[
            "oath 로 보호할 아군 지정 → 해당 아군에게 피해 일부 흡수",
            "chivalry / devotion 으로 파티 버프",
            "iron_will 로 도발 — 적 어그로 집중",
            "last_stand 은 위기 상황 최후 수단",
        ],
        target_bias="highest_brv",
        emergency_threshold=0.4,
    ),

    # =========================================================================
    # 힐러 (healer)
    # =========================================================================

    "priest": JobStrategy(
        job_id="priest",
        job_name="사제",
        role="healer",
        priority_actions=["skill_holy_heal", "skill_divine_protection", "skill_mass_heal"],
        gimmick_rules=[
            "신성 스킬 사용마다 권능(Power) 게이지 증가 → 힐량 증가",
            "아군 HP 70% 이하면 holy_heal 우선",
            "divine_protection 으로 보호막 선제 사용",
            "mass_heal 은 파티 전체 위기 시 사용",
        ],
        target_bias="lowest_hp",
        emergency_threshold=0.5,
    ),

    "cleric": JobStrategy(
        job_id="cleric",
        job_name="클레릭",
        role="healer",
        priority_actions=["skill_pray", "skill_heal", "skill_mass_heal", "skill_resurrect"],
        gimmick_rules=[
            "pray 로 신앙(Faith) 게이지 증가 → heal / greater_heal 강화",
            "holy_barrier 로 선제 보호막",
            "mass_heal 로 파티 광역 회복",
            "아군 사망 시 resurrect 최우선",
        ],
        target_bias="lowest_hp",
        emergency_threshold=0.5,
    ),

    "druid": JobStrategy(
        job_id="druid",
        job_name="드루이드",
        role="healer",
        priority_actions=["skill_healing_forest", "skill_bear_form", "skill_cat_form"],
        gimmick_rules=[
            "bear_form: 체력↑ — 파티 HP 낮을 때 방어적 운용",
            "cat_form: 공격력↑ — 여유 있을 때 딜링 기여",
            "wolf_form: 속도↑, eagle_form: 회피↑ — 상황별 선택",
            "healing_forest 로 파티 광역 힐",
        ],
        target_bias="lowest_hp",
        emergency_threshold=0.45,
    ),

    # =========================================================================
    # 버퍼 (buffer)
    # =========================================================================

    "bard": JobStrategy(
        job_id="bard",
        job_name="바드",
        role="buffer",
        priority_actions=["skill_attack_note", "skill_buff_note", "skill_support_note", "skill_symphony"],
        gimmick_rules=[
            "스킬마다 음표 추가: A(공격)/B(버프)/S(서포트)",
            "3음표=소나타, 4음표=협주곡, 5음표=교향곡 자동 발동",
            "특수 조합: AAA=공격↑80%, BBB=버프 2배, ABS=올스탯↑",
            "음표 조합 계획하며 스킬 선택",
        ],
        target_bias="debuffed_enemy",
        emergency_threshold=0.4,
    ),

    "time_mage": JobStrategy(
        job_id="time_mage",
        job_name="시간마법사",
        role="buffer",
        priority_actions=["skill_haste", "skill_slow", "skill_stop", "skill_balance"],
        gimmick_rules=[
            "haste 로 아군 ATB 가속",
            "slow / stop 으로 적 ATB 지연",
            "시간 조작 과다 사용 시 균형(Balance) 붕괴 → balance 로 복구",
            "rewind 으로 아군 상태 되돌리기, foresight 로 회피",
        ],
        target_bias="highest_brv",
        emergency_threshold=0.35,
    ),

    # =========================================================================
    # 디버퍼 (debuffer)
    # =========================================================================

    "hacker": JobStrategy(
        job_id="hacker",
        job_name="해커",
        role="debuffer",
        priority_actions=["skill_run_virus", "skill_run_ddos", "skill_terminate_all"],
        gimmick_rules=[
            "run_virus / run_backdoor / run_ddos / run_ransomware 로 프로세스 실행",
            "프로세스 많을수록 자신 버프 증가",
            "terminate_all 로 모든 프로세스 종료 — 폭딜 + 적 디버프",
        ],
        target_bias="debuffed_enemy",
        emergency_threshold=0.3,
    ),

    "shaman": JobStrategy(
        job_id="shaman",
        job_name="샤먼",
        role="debuffer",
        priority_actions=["skill_curse", "skill_plague", "skill_curse_burst"],
        gimmick_rules=[
            "curse 로 저주(Curse) 스택 증가 → DoT 피해 증가",
            "plague 로 저주 전염 — 다수 적에 확산",
            "스택 최대 시 curse_burst 로 폭발 딜",
            "curse_transfer 로 아군의 저주를 적으로 전이",
        ],
        target_bias="debuffed_enemy",
        emergency_threshold=0.35,
    ),

    # =========================================================================
    # 유틸리티 (utility)
    # =========================================================================

    "alchemist": JobStrategy(
        job_id="alchemist",
        job_name="연금술사",
        role="utility",
        priority_actions=["skill_gather", "skill_heal_potion", "skill_acid_flask", "skill_chain"],
        gimmick_rules=[
            "gather 로 재료 수집 → heal / buff / mana_potion 조합",
            "재료 충분 시 고급 포션 제작 가능",
            "acid_flask 로 공격, chain 으로 연계 폭발",
        ],
        target_bias="lowest_hp",
        emergency_threshold=0.35,
    ),

    "engineer": JobStrategy(
        job_id="engineer",
        job_name="엔지니어",
        role="utility",
        priority_actions=["skill_cooling_vent", "skill_overclock_mode", "skill_shield_generator", "skill_deploy_drone"],
        gimmick_rules=[
            "공격 스킬 사용마다 열(Heat) 게이지 증가",
            "열 과열 시 오버히트 — 패널티 발생",
            "cooling_vent 로 냉각, 열 적당할 때 overclock_mode 폭딜",
            "shield_generator 로 방어, deploy_drone 으로 지원",
        ],
        target_bias="highest_brv",
        emergency_threshold=0.3,
    ),

    "magician": JobStrategy(
        job_id="magician",
        job_name="마술사",
        role="utility",
        priority_actions=["skill_card_slash", "skill_ace_in_the_hole", "skill_fatal_flush"],
        gimmick_rules=[
            "card_slash 로 카드 뽑기 → 뽑힌 카드 종류에 따라 효과 결정",
            "ace_in_the_hole 으로 강패, double_or_nothing 으로 도박",
            "카드 조합 fatal_flush / full_house 노리기",
        ],
        target_bias="lowest_hp",
        emergency_threshold=0.35,
    ),

    "philosopher": JobStrategy(
        job_id="philosopher",
        job_name="철학자",
        role="utility",
        priority_actions=["skill_choose_power", "skill_choose_wisdom", "skill_choose_sacrifice"],
        gimmick_rules=[
            "choose_power: 공격↑, choose_wisdom: 마법↑",
            "choose_sacrifice: HP 소모 후 강화, choose_survival: 방어↑",
            "딜레마 선택 — 상황에 따라 최적 선택",
        ],
        target_bias="highest_brv",
        emergency_threshold=0.3,
    ),

    "pirate": JobStrategy(
        job_id="pirate",
        job_name="해적",
        role="utility",
        priority_actions=["brv_attack", "skill_drink_rum", "skill_find_treasure"],
        gimmick_rules=[
            "drink_rum 으로 버프 + 리스크 동시 발동",
            "find_treasure 로 랜덤 보상 (운 의존)",
            "도박성 스킬 다수 — 리스크 감수 플레이",
        ],
        target_bias="lowest_hp",
        emergency_threshold=0.3,
    ),

    "vampire": JobStrategy(
        job_id="vampire",
        job_name="흡혈귀",
        role="utility",
        priority_actions=["skill_vampiric_bite", "skill_blood_drain", "skill_thirst_surge", "skill_blood_satiation"],
        gimmick_rules=[
            "vampiric_bite / blood_drain 으로 흡혈 + 갈증(Thirst) 증가",
            "갈증 높을수록 공격력↑, 단 지속 피해 발생",
            "갈증 최대 시 thirst_surge 로 폭발 딜",
            "갈증 위험 시 blood_satiation 으로 안정화",
        ],
        target_bias="lowest_hp",
        emergency_threshold=0.3,
    ),

    "illusionist": JobStrategy(
        job_id="illusionist",
        job_name="환술사",
        role="utility",
        priority_actions=["skill_illusion", "brv_attack", "hp_attack"],
        gimmick_rules=[
            "환상 스킬로 적 혼란 유발",
            "혼란 상태 적에게 집중 공격",
            "파티 서포트와 딜링 혼합 운용",
        ],
        target_bias="debuffed_enemy",
        emergency_threshold=0.3,
    ),

    "ninja": JobStrategy(
        job_id="ninja",
        job_name="닌자",
        role="dps_physical",
        priority_actions=["skill_seal_stack", "skill_ninjutsu", "hp_attack"],
        gimmick_rules=[
            "인(印) 4개 축적 후 인법진 발동으로 속성 폭딜",
            "오둔-오의(ninja_elemental_ninjutsu)는 속성 변형 스킬 — 화/빙/뇌/풍 중 선택, 좌/우 방향키 또는 variant 필드로 지정",
            "변형 선택 API: {\"skill_id\": \"ninja_elemental_ninjutsu\", \"variant\": \"fire|ice|thunder|wind\"}",
            "가장 낮은 인(印) 속성을 우선 사용해 만화경 인법(4인)까지의 행동 수를 줄인다",
            "고속 이동(분신술)으로 회피율 확보 후 근접 연격",
            "아군 속성 스킬 연계 시 인(印) 자동 획득 활용",
        ],
        target_bias="lowest_hp",
        emergency_threshold=0.3,
        extra_notes=[
            "인(印) 4개 축적 완료 전에는 BRV 쌓기 우선",
            "분신술 → 연격 → 인법진 콤보가 핵심 딜 사이클",
        ],
    ),
}

# warrior 키가 두 번 선언되었으므로 마지막 값(dps_physical)이 유효함 — 의도적


# =============================================================================
# 헬퍼 함수
# =============================================================================

def get_job_strategy(job_id: str) -> JobStrategy:
    """
    직업 ID로 전략 데이터 조회

    Args:
        job_id: 직업 ID (영문 소문자, 예: "warrior")

    Returns:
        JobStrategy 인스턴스. 없으면 기본 balanced 전략 반환
    """
    strategy = JOB_STRATEGIES.get(job_id)
    if strategy is None:
        logger.warning(f"알 수 없는 직업 ID: '{job_id}', 기본 전략 사용")
        return JobStrategy(
            job_id=job_id,
            job_name=job_id,
            role="dps_physical",
            priority_actions=["brv_attack", "hp_attack"],
            gimmick_rules=["BRV 쌓고 HP 공격"],
            target_bias="lowest_hp",
            emergency_threshold=0.3,
        )
    return strategy


def get_combat_system_prompt(job_id: str, play_style: str = "balanced") -> str:
    """
    직업과 플레이 스타일에 맞는 전투 시스템 프롬프트 생성

    Args:
        job_id: 직업 ID (영문 소문자)
        play_style: 플레이 스타일 ("aggressive", "defensive", "balanced", "speedrun", "resource")

    Returns:
        LLM 시스템 프롬프트 문자열
    """
    strategy = get_job_strategy(job_id)

    # 역할별 기본 지침
    role_guidelines = {
        "tank": "파티 보호가 최우선. 도발 스킬로 적 어그로 집중, 방어/보호막 스킬 적극 사용.",
        "healer": "파티 HP 관리가 최우선. 아군 HP 70% 이하면 즉시 회복. 부활 스킬 아끼지 말 것.",
        "dps_physical": "물리 딜러. BRV 충분히 쌓고 HP 공격으로 마무리. 기믹 사이클 유지.",
        "dps_magical": "마법 딜러. 원소/기믹 콤보 활용하여 폭딜. MP 관리 필요.",
        "buffer": "버프/서포트 최우선. 팀 강화 후 여유 있을 때 공격 기여.",
        "debuffer": "적 약화 최우선. 디버프 적용 후 집중 공격. 스택/게이지 관리.",
        "utility": "상황 판단 후 유연하게 대응. 고유 기믹 최대 활용.",
    }

    # 플레이 스타일별 추가 지침
    style_guidelines = {
        "aggressive": "공격적: 강력한 공격 스킬 우선, 리스크 감수. 딜링 최대화.",
        "defensive": "방어적: HP 50% 이하면 회복 우선. 안정성 중시. 버프/보호막 적극 사용.",
        "balanced": "균형: 상황에 따라 공격/회복/버프 적절히 혼합. 전략적 판단.",
        "speedrun": "스피드: 가장 높은 데미지 스킬로 빠른 처치. 회복은 필수일 때만.",
        "resource": "절약: MP/아이템 아끼며 효율적 스킬 선택. 저비용 스킬 선호.",
    }

    gimmick_text = "\n".join(f"  - {r}" for r in strategy.gimmick_rules)
    priority_text = " → ".join(strategy.priority_actions)
    extra_text = ""
    if strategy.extra_notes:
        extra_text = "\n추가 전략:\n" + "\n".join(f"  * {n}" for n in strategy.extra_notes)

    role_guide = role_guidelines.get(strategy.role, "상황에 맞게 대응.")
    style_guide = style_guidelines.get(play_style, style_guidelines["balanced"])

    prompt = f"""당신은 Dawn of Stellar의 {strategy.job_name}({job_id}) AI입니다.
ATB+BRV 전투 시스템에서 최적의 결정을 내립니다.

## 직업 역할: {strategy.role}
{role_guide}

## 플레이 스타일
{style_guide}

## 행동 우선순위
{priority_text}

## 기믹 관리 규칙
{gimmick_text}

## 타겟 선택
기본 타겟 편향: {strategy.target_bias}
긴급 상황 기준: HP {int(strategy.emergency_threshold * 100)}% 이하 → 생존 최우선
{extra_text}

## 응답 형식 (JSON)
{{
  "action": "brv_attack|hp_attack|skill|item|defend",
  "target": "적_또는_아군_이름",
  "skill_id": "스킬ID (skill 선택 시)",
  "reasoning": "판단 이유 (한국어)"
}}
"""
    return prompt
