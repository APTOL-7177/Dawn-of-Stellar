"""
Job Redesign Generator - 나머지 27개 직업 자동 생성 스크립트
"""

# 27개 남은 직업의 기믹 시스템 정의
JOB_DESIGNS = {
    # Phase 2 (3 more)
    "berserker": {
        "gimmick_type": "rage_management",
        "gimmick_name": "분노 관리",
        "gimmick_desc": "피해를 받으면 분노 증가(0-100). 높을수록 공격력 증가, 방어력 감소",
        "stats": {
            "rage": 0,
            "max_rage": 100,
            "rage_decay": 5,  # 턴당 감소량
            "berserk_threshold": 70,  # 버서커 모드 진입
        },
        "skills": [
            ("berserker_slash", "격노의 일격", "BRV", "기본 물리 공격, 분노 +5"),
            ("berserker_smash", "파쇄타", "HP", "강타, 분노 +10"),
            ("berserker_rage_strike", "분노 강타", "BRV_HP", "분노에 비례한 피해, 분노 +15"),
            ("berserker_blood_frenzy", "피의 광란", "BUFF", "3턴간 공격력 +50%, 분노 +20"),
            ("berserker_berserk_mode", "버서커 모드", "BUFF", "분노 70+ 필요, 극한의 공격력"),
            ("berserker_warcry", "전쟁함성", "DEBUFF", "적 전체 위축, 분노 +10"),
            ("berserker_reckless_charge", "무모한 돌진", "BRV_HP", "HP 소모, 강력한 피해"),
            ("berserker_rage_explosion", "분노 폭발", "BRV_HP", "모든 분노 소모, 극한 피해"),
            ("berserker_calm_down", "진정", "HEAL", "분노 0으로, HP 회복"),
            ("berserker_ultimate", "광전사의 울부짖음", "ULTIMATE", "궁극기"),
        ]
    },

    "vampire": {
        "gimmick_type": "blood_reserve",
        "gimmick_name": "혈액 저장고",
        "gimmick_desc": "적 피해 시 혈액 획득(0-100). 혈액으로 강력한 흡혈 능력 사용",
        "stats": {
            "blood": 0,
            "max_blood": 100,
            "blood_per_hit": 10,
            "bloodthirst_threshold": 50,
        },
        "skills": [
            ("vampire_bite", "흡혈", "BRV", "기본 공격, 혈액 +10, HP 회복"),
            ("vampire_drain", "흡수", "HP", "HP 공격, 혈액 +15, HP 드레인"),
            ("vampire_blood_lance", "혈창", "BRV_HP", "혈액 20 소모, 관통 공격"),
            ("vampire_bat_swarm", "박쥐 떼", "AOE", "광역 공격, 혈액 획득"),
            ("vampire_blood_shield", "혈액 보호막", "BUFF", "혈액으로 방어막"),
            ("vampire_mist_form", "안개 형상", "BUFF", "회피 +50%, 혈액 소모"),
            ("vampire_blood_frenzy", "피의 광란", "BUFF", "혈액 50+ 필요, 공격력 증가"),
            ("vampire_life_tap", "생명 연결", "DRAIN", "지속 흡혈"),
            ("vampire_crimson_nova", "진홍 폭발", "BRV_HP", "혈액 전부 소모, 광역 피해"),
            ("vampire_ultimate", "혈마의 심장", "ULTIMATE", "궁극기"),
        ]
    },

    "hacker": {
        "gimmick_type": "network_access",
        "gimmick_name": "네트워크 접근",
        "gimmick_desc": "적 시스템 해킹(접근 레벨 0-5). 레벨↑→능력↑",
        "stats": {
            "access_level": 0,
            "max_access": 5,
            "firewall_break_count": 0,
        },
        "skills": [
            ("hacker_data_spike", "데이터 스파이크", "BRV", "기본 공격, 접근 +1"),
            ("hacker_exploit", "취약점 공격", "HP", "HP 공격, 접근 +1"),
            ("hacker_crack_firewall", "방화벽 해제", "GIMMICK", "접근 레벨 +2"),
            ("hacker_ddos", "DDoS 공격", "AOE", "광역 공격, 스턴"),
            ("hacker_root_access", "루트 권한", "BUFF", "접근 5 필요, 모든 능력 증가"),
            ("hacker_virus_upload", "바이러스 업로드", "DOT", "지속 피해"),
            ("hacker_system_overload", "시스템 과부하", "BRV_HP", "접근에 비례한 피해"),
            ("hacker_backdoor", "백도어", "BUFF", "접근 레벨 유지 강화"),
            ("hacker_network_collapse", "네트워크 붕괴", "BRV_HP", "접근 레벨 소모, 강력한 피해"),
            ("hacker_ultimate", "제로데이 익스플로잇", "ULTIMATE", "궁극기"),
        ]
    },

    # Phase 3 (6 jobs)
    "gladiator": {
        "gimmick_type": "crowd_favor",
        "gimmick_name": "군중 선호도",
        "gimmick_desc": "전투 행동으로 군중 환호 획득(0-100). 높을수록 보너스",
        "stats": {
            "crowd_favor": 50,  # 시작 50
            "max_favor": 100,
            "min_favor": 0,
            "combo_count": 0,
        },
        "skills": [
            ("gladiator_slash", "검격", "BRV", "기본 공격, 선호도 +5"),
            ("gladiator_thrust", "찌르기", "HP", "강타, 선호도 +7"),
            ("gladiator_showmanship", "화려한 기술", "BRV_HP", "선호도 +15, 화려한 공격"),
            ("gladiator_crowd_roar", "군중의 함성", "BUFF", "선호도 70+ 필요, 공격력 증가"),
            ("gladiator_combo_strike", "연속 공격", "MULTI", "3연타, 선호도 증가"),
            ("gladiator_finisher", "피니쉬", "BRV_HP", "선호도 소모, 강력한 공격"),
            ("gladiator_thumbs_up", "승인의 엄지", "HEAL", "선호도 80+, HP 회복"),
            ("gladiator_arena_master", "투기장 지배자", "BUFF", "선호도 100, 최대 강화"),
            ("gladiator_execution", "처형", "BRV_HP", "선호도 50 소모, 즉사 급 피해"),
            ("gladiator_ultimate", "검투사의 영광", "ULTIMATE", "궁극기"),
        ]
    },

    "assassin": {
        "gimmick_type": "shadow_gauge",
        "gimmick_name": "암영 게이지",
        "gimmick_desc": "은신(0-100). 높을수록 크리티컬/회피↑",
        "stats": {
            "shadow": 0,
            "max_shadow": 100,
            "stealth_threshold": 50,
        },
        "skills": [
            ("assassin_dagger", "단검 공격", "BRV", "기본 공격, 암영 +10"),
            ("assassin_backstab", "백스탭", "HP", "크리티컬 확정, 암영 +15"),
            ("assassin_shadow_step", "그림자 이동", "GIMMICK", "암영 +30, 회피 증가"),
            ("assassin_poison_blade", "독 단검", "DOT", "지속 독 피해"),
            ("assassin_stealth", "은신", "BUFF", "암영 50+ 필요, 투명화"),
            ("assassin_critical_strike", "치명타", "BRV_HP", "크리티컬 보장, 강력한 피해"),
            ("assassin_shadow_clone", "그림자 분신", "BUFF", "회피율 극대화"),
            ("assassin_assassination", "암살", "HP", "암영 80+ 필요, 즉사급 피해"),
            ("assassin_vanish", "소멸", "GIMMICK", "암영 100, 완전 회피"),
            ("assassin_ultimate", "암살자의 춤", "ULTIMATE", "궁극기"),
        ]
    },

    "archer": {
        "gimmick_type": "focus_system",
        "gimmick_name": "집중력",
        "gimmick_desc": "집중 상태 유지(0-100). 높을수록 명중/크리티컬↑",
        "stats": {
            "focus": 0,
            "max_focus": 100,
            "perfect_focus": 80,
        },
        "skills": [
            ("archer_quick_shot", "속사", "BRV", "기본 공격, 집중 +5"),
            ("archer_power_shot", "강력한 일격", "HP", "강타, 집중 +10"),
            ("archer_aim", "조준", "GIMMICK", "집중 +40"),
            ("archer_multi_shot", "다중 화살", "MULTI", "3발 동시 발사"),
            ("archer_snipe", "저격", "HP", "집중 80+ 필요, 크리티컬 확정"),
            ("archer_arrow_rain", "화살 비", "AOE", "광역 공격"),
            ("archer_piercing_shot", "관통 화살", "BRV_HP", "방어 무시"),
            ("archer_perfect_shot", "완벽한 조준", "BRV_HP", "집중 100, 최대 피해"),
            ("archer_focus_reset", "집중 초기화", "GIMMICK", "집중 0, MP 회복"),
            ("archer_ultimate", "궁수의 심안", "ULTIMATE", "궁극기"),
        ]
    },

    "elementalist": {
        "gimmick_type": "elemental_harmony",
        "gimmick_name": "원소 조화",
        "gimmick_desc": "4원소(불/물/바람/땅) 조화 관리. 균형 시 강력",
        "stats": {
            "fire": 0,
            "water": 0,
            "wind": 0,
            "earth": 0,
            "max_per_element": 3,
        },
        "skills": [
            ("elementalist_fire_bolt", "화염탄", "BRV", "기본 공격, 화염 +1"),
            ("elementalist_water_blast", "물줄기", "HP", "HP 공격, 물 +1"),
            ("elementalist_wind_slash", "바람 베기", "BRV", "공격, 바람 +1"),
            ("elementalist_earth_spike", "대지 가시", "BRV_HP", "공격, 땅 +1"),
            ("elementalist_fire_storm", "화염 폭풍", "AOE", "화염 2 소모, 광역"),
            ("elementalist_ice_prison", "얼음 감옥", "DEBUFF", "물 2 소모, 스턴"),
            ("elementalist_tornado", "회오리", "BRV_HP", "바람 2 소모, 강력한 공격"),
            ("elementalist_earthquake", "지진", "AOE", "땅 2 소모, 광역 공격"),
            ("elementalist_elemental_fusion", "원소 융합", "BRV_HP", "4원소 균형 필요, 강력한 공격"),
            ("elementalist_ultimate", "원소 조화의 극치", "ULTIMATE", "궁극기"),
        ]
    },

    "philosopher": {
        "gimmick_type": "wisdom_depth",
        "gimmick_name": "지혜 깊이",
        "gimmick_desc": "사색을 통한 지혜 축적(0-10). 레벨↑→능력↑",
        "stats": {
            "wisdom_level": 0,
            "max_wisdom": 10,
            "meditation_count": 0,
        },
        "skills": [
            ("philosopher_thought_strike", "사념타", "BRV", "기본 공격"),
            ("philosopher_logic_blast", "논리 폭발", "HP", "HP 공격"),
            ("philosopher_meditate", "명상", "GIMMICK", "지혜 +2, MP 회복"),
            ("philosopher_wisdom_share", "지혜 공유", "BUFF", "아군 강화"),
            ("philosopher_dialectic", "변증법", "DEBUFF", "적 약화"),
            ("philosopher_enlightenment", "깨달음", "BUFF", "지혜 7+ 필요, 모든 능력↑"),
            ("philosopher_paradox", "역설", "BRV_HP", "지혜에 비례한 피해"),
            ("philosopher_truth_reveal", "진리 계시", "BRV_HP", "지혜 10, 극한 피해"),
            ("philosopher_reset_wisdom", "무지의 자각", "GIMMICK", "지혜 0, HP/MP 회복"),
            ("philosopher_ultimate", "철학자의 돌", "ULTIMATE", "궁극기"),
        ]
    },

    "dimensionist": {
        "gimmick_type": "dimensional_anchor",
        "gimmick_name": "차원 정박",
        "gimmick_desc": "다른 차원과의 연결(0-5차원). 차원 이동으로 전투",
        "stats": {
            "current_dimension": 0,  # 현재 차원 (0-5)
            "dimension_stability": 100,  # 안정도
        },
        "skills": [
            ("dimensionist_rift_strike", "차원 균열 타격", "BRV", "기본 공격"),
            ("dimensionist_void_blast", "공허 폭발", "HP", "HP 공격"),
            ("dimensionist_shift_up", "차원 상승", "GIMMICK", "차원 +1"),
            ("dimensionist_shift_down", "차원 하강", "GIMMICK", "차원 -1"),
            ("dimensionist_dimensional_blade", "차원 검", "BRV_HP", "차원에 비례한 피해"),
            ("dimensionist_banish", "추방", "DEBUFF", "적을 다른 차원으로"),
            ("dimensionist_anchor_here", "정박", "BUFF", "현재 차원 고정, 강화"),
            ("dimensionist_rift_walk", "차원 보행", "GIMMICK", "차원 자유 이동"),
            ("dimensionist_reality_tear", "현실 파열", "BRV_HP", "차원 5, 강력한 공격"),
            ("dimensionist_ultimate", "차원 붕괴", "ULTIMATE", "궁극기"),
        ]
    },

    # 나머지 18개 직업 (간략 정의)
    "warrior": {"gimmick_type": "battle_stance", "gimmick_name": "전투 태세"},
    "knight": {"gimmick_type": "guardian_oath", "gimmick_name": "수호 서약"},
    "paladin": {"gimmick_type": "holy_light", "gimmick_name": "성스러운 빛"},
    "dark_knight": {"gimmick_type": "dark_pact", "gimmick_name": "어둠의 계약"},
    "samurai": {"gimmick_type": "iaido_stance", "gimmick_name": "거합 자세"},
    "sword_saint": {"gimmick_type": "sword_mastery", "gimmick_name": "검의 경지"},
    "rogue": {"gimmick_type": "combo_points", "gimmick_name": "연계 포인트"},
    "pirate": {"gimmick_type": "plunder_gold", "gimmick_name": "약탈 금화"},
    "dragon_knight": {"gimmick_type": "dragon_soul", "gimmick_name": "용의 혼"},
    "spellblade": {"gimmick_type": "spell_charge", "gimmick_name": "마법 충전"},
    "archmage": {"gimmick_type": "arcane_power", "gimmick_name": "비전 마력"},
    "priest": {"gimmick_type": "divine_grace", "gimmick_name": "신성한 은총"},
    "cleric": {"gimmick_type": "prayer_stack", "gimmick_name": "기도 축적"},
    "druid": {"gimmick_type": "nature_attunement", "gimmick_name": "자연 동화"},
    "shaman": {"gimmick_type": "spirit_totem", "gimmick_name": "정령 토템"},
    "bard": {"gimmick_type": "melody_rhythm", "gimmick_name": "선율 리듬"},
    "alchemist": {"gimmick_type": "potion_brew", "gimmick_name": "물약 조제"},
    "breaker": {"gimmick_type": "break_gauge", "gimmick_name": "파괴 게이지"},
}

print("Job Redesign Definitions Generated!")
print(f"Total Jobs Defined: {len(JOB_DESIGNS)}")
print("\nPhase 2-3 Jobs (Detailed):")
for job in ["berserker", "vampire", "hacker", "gladiator", "assassin", "archer", "elementalist", "philosopher", "dimensionist"]:
    if job in JOB_DESIGNS:
        design = JOB_DESIGNS[job]
        print(f"  - {job}: {design['gimmick_name']} ({len(design.get('skills', []))} skills)")

print("\nOther Jobs (Simplified):")
other_jobs = [k for k in JOB_DESIGNS.keys() if k not in ["berserker", "vampire", "hacker", "gladiator", "assassin", "archer", "elementalist", "philosopher", "dimensionist"]]
for job in other_jobs:
    design = JOB_DESIGNS[job]
    print(f"  - {job}: {design['gimmick_name']}")
