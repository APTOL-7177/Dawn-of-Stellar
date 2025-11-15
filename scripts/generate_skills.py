#!/usr/bin/env python3
"""
스킬 데이터 자동 생성 스크립트
34개 직업의 204개 스킷 YAML 파일을 생성합니다.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Any


# 프로젝트 루트 디렉토리
ROOT_DIR = Path(__file__).parent.parent
CHARACTERS_DIR = ROOT_DIR / "data" / "characters"
SKILLS_DIR = ROOT_DIR / "data" / "skills"


# 스킬 타입별 기본 템플릿
SKILL_TEMPLATES = {
    "brv_attack": {
        "type": "brv_attack",
        "costs": {"mp": 15, "cast_time": 1.0},
        "effects": [
            {
                "type": "damage",
                "element": "physical",
                "multiplier": 2.0,
                "stat_base": "strength"
            }
        ]
    },
    "hp_attack": {
        "type": "hp_attack",
        "costs": {"mp": 20, "cast_time": 1.2},
        "effects": [
            {
                "type": "hp_damage",
                "multiplier": 1.5,
                "uses_brv": True
            }
        ]
    },
    "brv_hp_attack": {
        "type": "brv_hp_attack",
        "costs": {"mp": 30, "cast_time": 1.5},
        "effects": [
            {
                "type": "damage",
                "element": "physical",
                "multiplier": 1.8,
                "stat_base": "strength"
            },
            {
                "type": "hp_damage",
                "multiplier": 1.2,
                "uses_brv": True
            }
        ]
    },
    "support": {
        "type": "support",
        "costs": {"mp": 25, "cast_time": 1.0},
        "effects": [
            {
                "type": "buff",
                "target": "self",
                "stat": "physical_attack",
                "value": 1.3,
                "duration": 3
            }
        ]
    },
    "heal": {
        "type": "heal",
        "costs": {"mp": 30, "cast_time": 1.0},
        "effects": [
            {
                "type": "heal",
                "target": "ally",
                "multiplier": 2.5,
                "stat_base": "magic"
            }
        ]
    },
    "debuff": {
        "type": "debuff",
        "costs": {"mp": 20, "cast_time": 1.0},
        "effects": [
            {
                "type": "debuff",
                "target": "enemy",
                "stat": "physical_defense",
                "value": 0.7,
                "duration": 3
            }
        ]
    },
    "ultimate": {
        "type": "ultimate",
        "costs": {"mp": 50, "cast_time": 2.0},
        "effects": [
            {
                "type": "damage",
                "element": "physical",
                "multiplier": 5.0,
                "stat_base": "strength"
            },
            {
                "type": "hp_damage",
                "multiplier": 2.0,
                "uses_brv": True
            }
        ]
    }
}


# 직업별 스킬 정의 (한국어 이름, 타입, 특성)
SKILL_DEFINITIONS = {
    # 전사
    "power_strike": {"name": "강타", "type": "brv_attack", "element": "physical", "mp": 15, "multiplier": 2.5, "description": "강력한 일격으로 적을 가격합니다"},
    "shield_bash": {"name": "방패 강타", "type": "brv_attack", "element": "physical", "mp": 20, "multiplier": 2.0, "description": "방패로 적을 강타하여 스턴시킵니다"},
    "war_cry": {"name": "전쟁의 함성", "type": "support", "mp": 25, "multiplier": 1.3, "description": "아군의 공격력을 증가시킵니다"},
    "berserker_rage": {"name": "광전사의 분노", "type": "support", "mp": 30, "multiplier": 1.5, "description": "공격력이 크게 증가하지만 방어력이 감소합니다"},
    "defensive_stance": {"name": "방어 자세", "type": "support", "mp": 20, "multiplier": 1.4, "description": "방어력을 크게 증가시킵니다"},
    "ultimate_slash": {"name": "궁극의 베기", "type": "ultimate", "element": "physical", "mp": 50, "multiplier": 5.0, "description": "강력한 참격으로 적을 베어냅니다"},

    # 마법사
    "fire_blast": {"name": "화염 폭발", "type": "brv_attack", "element": "fire", "mp": 18, "multiplier": 2.8, "stat_base": "magic", "description": "화염 마법으로 적을 불태웁니다"},
    "ice_shard": {"name": "얼음 파편", "type": "brv_attack", "element": "ice", "mp": 18, "multiplier": 2.8, "stat_base": "magic", "description": "얼음 파편으로 적을 공격합니다"},
    "thunder_bolt": {"name": "번개", "type": "brv_attack", "element": "lightning", "mp": 18, "multiplier": 2.8, "stat_base": "magic", "description": "번개로 적을 타격합니다"},
    "magic_missile": {"name": "마법 미사일", "type": "brv_attack", "element": "magical", "mp": 15, "multiplier": 2.5, "stat_base": "magic", "description": "마법 에너지를 발사합니다"},
    "mana_shield": {"name": "마나 보호막", "type": "support", "mp": 25, "multiplier": 1.3, "description": "마법 방어막을 생성합니다"},
    "arcane_explosion": {"name": "비전 폭발", "type": "ultimate", "element": "magical", "mp": 55, "multiplier": 5.5, "stat_base": "magic", "description": "강력한 마법 폭발을 일으킵니다"},

    # 신관
    "healing_prayer": {"name": "치유의 기도", "type": "heal", "mp": 25, "multiplier": 3.0, "stat_base": "magic", "description": "신성한 기도로 아군을 치유합니다"},
    "divine_light": {"name": "신성한 빛", "type": "brv_attack", "element": "holy", "mp": 20, "multiplier": 2.5, "stat_base": "magic", "description": "성스러운 빛으로 적을 공격합니다"},
    "holy_barrier": {"name": "신성한 방벽", "type": "support", "mp": 30, "multiplier": 1.5, "description": "아군을 보호하는 방벽을 생성합니다"},
    "miracle_cure": {"name": "기적의 치유", "type": "heal", "mp": 40, "multiplier": 4.0, "stat_base": "magic", "description": "기적적인 치유로 상태이상을 제거합니다"},
    "resurrection": {"name": "부활", "type": "support", "mp": 60, "multiplier": 1.0, "description": "전투불능 상태의 아군을 부활시킵니다"},
    "divine_judgment": {"name": "신의 심판", "type": "ultimate", "element": "holy", "mp": 50, "multiplier": 5.0, "stat_base": "magic", "description": "신의 심판으로 적을 응징합니다"},

    # 궁수
    "power_shot": {"name": "강력한 사격", "type": "brv_attack", "element": "physical", "mp": 15, "multiplier": 2.6, "description": "강력한 화살을 발사합니다"},
    "multi_shot": {"name": "다중 사격", "type": "brv_attack", "element": "physical", "mp": 25, "multiplier": 2.0, "description": "여러 개의 화살을 동시에 발사합니다"},
    "piercing_arrow": {"name": "관통 화살", "type": "brv_attack", "element": "physical", "mp": 20, "multiplier": 2.8, "description": "방어력을 무시하는 화살을 발사합니다"},
    "explosive_arrow": {"name": "폭발 화살", "type": "brv_hp_attack", "element": "physical", "mp": 30, "multiplier": 2.2, "description": "폭발하는 화살로 광역 피해를 입힙니다"},
    "mark_target": {"name": "표적 지정", "type": "debuff", "mp": 20, "multiplier": 0.8, "description": "적에게 표식을 남겨 피해를 증가시킵니다"},
    "arrow_rain": {"name": "화살 비", "type": "ultimate", "element": "physical", "mp": 50, "multiplier": 4.5, "description": "하늘에서 수많은 화살을 쏟아냅니다"},

    # 도적
    "backstab": {"name": "배후 습격", "type": "brv_attack", "element": "physical", "mp": 18, "multiplier": 3.0, "description": "적의 배후를 공격하여 치명타를 입힙니다"},
    "poison_blade": {"name": "독 칼날", "type": "brv_attack", "element": "physical", "mp": 20, "multiplier": 2.2, "description": "독이 묻은 칼로 적을 공격합니다"},
    "smoke_bomb": {"name": "연막탄", "type": "support", "mp": 15, "multiplier": 1.0, "description": "연막으로 회피율을 증가시킵니다"},
    "steal": {"name": "훔치기", "type": "support", "mp": 10, "multiplier": 1.0, "description": "적에게서 아이템을 훔칩니다"},
    "shadow_step": {"name": "그림자 이동", "type": "support", "mp": 25, "multiplier": 1.0, "description": "그림자처럼 빠르게 이동합니다"},
    "assassinate": {"name": "암살", "type": "ultimate", "element": "physical", "mp": 45, "multiplier": 6.0, "description": "치명적인 일격으로 적을 암살합니다"},

    # 기사
    "noble_strike": {"name": "고결한 일격", "type": "brv_attack", "element": "physical", "mp": 18, "multiplier": 2.4, "description": "기사도를 담은 정직한 일격입니다"},
    "shield_wall": {"name": "방패의 벽", "type": "support", "mp": 30, "multiplier": 1.6, "description": "강력한 방어 태세를 취합니다"},
    "challenge": {"name": "도전", "type": "debuff", "mp": 15, "multiplier": 1.0, "description": "적의 어그로를 끌어 공격을 유도합니다"},
    "guardian": {"name": "수호자", "type": "support", "mp": 25, "multiplier": 1.4, "description": "아군을 보호하는 자세를 취합니다"},
    "iron_will": {"name": "강철 의지", "type": "support", "mp": 20, "multiplier": 1.3, "description": "의지로 방어력을 강화합니다"},
    "knights_honor": {"name": "기사의 명예", "type": "ultimate", "element": "physical", "mp": 50, "multiplier": 4.8, "description": "기사의 명예를 건 강력한 공격입니다"},

    # 암살자
    "silent_kill": {"name": "무음 살해", "type": "brv_attack", "element": "physical", "mp": 20, "multiplier": 3.2, "description": "소리 없이 적을 제거합니다"},
    "shadow_strike": {"name": "그림자 공격", "type": "brv_attack", "element": "dark", "mp": 22, "multiplier": 2.8, "description": "그림자에서 나타나 공격합니다"},
    "death_mark": {"name": "죽음의 표식", "type": "debuff", "mp": 25, "multiplier": 0.6, "description": "적에게 죽음의 표식을 새깁니다"},
    "vanish": {"name": "은신", "type": "support", "mp": 20, "multiplier": 1.0, "description": "완전히 모습을 감춥니다"},
    "critical_strike": {"name": "급소 공격", "type": "brv_attack", "element": "physical", "mp": 25, "multiplier": 3.5, "description": "적의 급소를 정확히 공격합니다"},
    "execution": {"name": "처형", "type": "ultimate", "element": "physical", "mp": 55, "multiplier": 7.0, "description": "적을 즉시 처형합니다"},

    # 팔라딘
    "holy_strike": {"name": "신성한 공격", "type": "brv_attack", "element": "holy", "mp": 20, "multiplier": 2.5, "description": "성스러운 힘으로 적을 공격합니다"},
    "divine_shield": {"name": "신성한 방패", "type": "support", "mp": 30, "multiplier": 1.7, "description": "신의 축복으로 방어력을 강화합니다"},
    "blessing": {"name": "축복", "type": "support", "mp": 25, "multiplier": 1.4, "description": "아군에게 축복을 내립니다"},
    "smite_evil": {"name": "악령 퇴치", "type": "brv_attack", "element": "holy", "mp": 25, "multiplier": 3.0, "description": "악한 존재에게 강력한 피해를 입힙니다"},
    "sacred_ground": {"name": "성역", "type": "support", "mp": 35, "multiplier": 1.5, "description": "신성한 땅을 만들어 아군을 보호합니다"},
    "holy_crusade": {"name": "성전", "type": "ultimate", "element": "holy", "mp": 50, "multiplier": 5.2, "stat_base": "strength", "description": "성전의 힘으로 적을 섬멸합니다"},

    # 검성
    "iaijutsu": {"name": "거합술", "type": "brv_attack", "element": "physical", "mp": 20, "multiplier": 3.2, "description": "초고속 발도술로 적을 베어냅니다"},
    "spirit_blade": {"name": "영검", "type": "brv_attack", "element": "magical", "mp": 25, "multiplier": 2.8, "stat_base": "magic", "description": "마력이 깃든 검으로 공격합니다"},
    "sword_dance": {"name": "검무", "type": "brv_hp_attack", "element": "physical", "mp": 30, "multiplier": 2.5, "description": "화려한 검무로 연속 공격합니다"},
    "mirror_blade": {"name": "거울 검", "type": "support", "mp": 25, "multiplier": 1.0, "description": "적의 공격을 반사합니다"},
    "transcendence": {"name": "초월", "type": "support", "mp": 35, "multiplier": 1.8, "description": "검의 경지를 초월합니다"},
    "heaven_sword": {"name": "천검", "type": "ultimate", "element": "physical", "mp": 55, "multiplier": 6.5, "description": "하늘을 가르는 최강의 검격입니다"},

    # 버서커
    "wild_swing": {"name": "난폭한 공격", "type": "brv_attack", "element": "physical", "mp": 12, "multiplier": 2.8, "description": "정신없이 휘두르는 공격입니다"},
    "blood_rage": {"name": "피의 분노", "type": "support", "mp": 20, "multiplier": 1.6, "description": "HP가 낮을수록 공격력이 증가합니다"},
    "reckless_charge": {"name": "무모한 돌진", "type": "brv_attack", "element": "physical", "mp": 25, "multiplier": 3.5, "description": "방어를 무시하고 돌진합니다"},
    "intimidate": {"name": "위협", "type": "debuff", "mp": 15, "multiplier": 0.7, "description": "적을 위협하여 공격력을 감소시킵니다"},
    "rampage": {"name": "광란", "type": "support", "mp": 30, "multiplier": 2.0, "description": "이성을 잃고 광란 상태가 됩니다"},
    "final_stand": {"name": "최후의 저항", "type": "ultimate", "element": "physical", "mp": 45, "multiplier": 7.5, "description": "죽음을 무릅쓴 최후의 일격입니다"},

    # 격투가
    "straight_punch": {"name": "스트레이트", "type": "brv_attack", "element": "physical", "mp": 10, "multiplier": 2.2, "description": "빠르고 강력한 펀치입니다"},
    "uppercut": {"name": "어퍼컷", "type": "brv_attack", "element": "physical", "mp": 15, "multiplier": 2.6, "description": "강력한 상승 펀치입니다"},
    "combo_strike": {"name": "콤보 공격", "type": "brv_hp_attack", "element": "physical", "mp": 25, "multiplier": 2.0, "description": "연속 타격으로 적을 몰아칩니다"},
    "focus": {"name": "집중", "type": "support", "mp": 20, "multiplier": 1.4, "description": "정신을 집중하여 능력치를 올립니다"},
    "counter": {"name": "카운터", "type": "support", "mp": 15, "multiplier": 1.0, "description": "적의 공격을 역이용합니다"},
    "meteor_strike": {"name": "유성타", "type": "ultimate", "element": "physical", "mp": 50, "multiplier": 5.8, "description": "유성처럼 빠른 연속 공격입니다"},

    # 사무라이
    "swift_slash": {"name": "신속검", "type": "brv_attack", "element": "physical", "mp": 18, "multiplier": 2.7, "description": "빠른 검격으로 적을 베어냅니다"},
    "bushido": {"name": "무사도", "type": "support", "mp": 25, "multiplier": 1.5, "description": "무사도 정신으로 능력치를 증가시킵니다"},
    "counter_slash": {"name": "카운터 베기", "type": "brv_attack", "element": "physical", "mp": 20, "multiplier": 3.0, "description": "적의 공격에 대응하는 반격입니다"},
    "meditate": {"name": "명상", "type": "support", "mp": 15, "multiplier": 1.3, "description": "명상으로 정신력을 회복합니다"},
    "honorable_death": {"name": "명예로운 죽음", "type": "support", "mp": 30, "multiplier": 2.5, "description": "명예를 위해 모든 것을 바칩니다"},
    "ultimate_blade": {"name": "극의 일도", "type": "ultimate", "element": "physical", "mp": 55, "multiplier": 6.2, "description": "검술의 극의에 도달한 일격입니다"},

    # 대마법사
    "meteor": {"name": "메테오", "type": "brv_attack", "element": "fire", "mp": 40, "multiplier": 4.0, "stat_base": "magic", "description": "하늘에서 거대한 운석을 떨어뜨립니다"},
    "blizzard": {"name": "블리자드", "type": "brv_attack", "element": "ice", "mp": 35, "multiplier": 3.5, "stat_base": "magic", "description": "강력한 눈보라를 일으킵니다"},
    "thundaga": {"name": "선더가", "type": "brv_attack", "element": "lightning", "mp": 35, "multiplier": 3.5, "stat_base": "magic", "description": "강력한 번개를 소환합니다"},
    "gravity": {"name": "그래비티", "type": "debuff", "mp": 30, "multiplier": 0.5, "stat_base": "magic", "description": "중력으로 적을 짓누릅니다"},
    "magic_barrier": {"name": "마법 장벽", "type": "support", "mp": 35, "multiplier": 1.7, "description": "강력한 마법 방어막을 생성합니다"},
    "ultima": {"name": "알테마", "type": "ultimate", "element": "magical", "mp": 70, "multiplier": 7.0, "stat_base": "magic", "description": "최강의 마법으로 모든 것을 파괴합니다"},

    # 다크나이트
    "darkness": {"name": "암흑", "type": "brv_attack", "element": "dark", "mp": 20, "multiplier": 2.8, "description": "어둠의 힘으로 적을 공격합니다"},
    "drain": {"name": "드레인", "type": "brv_attack", "element": "dark", "mp": 25, "multiplier": 2.2, "description": "적의 생명력을 흡수합니다"},
    "dark_wave": {"name": "암흑파", "type": "brv_hp_attack", "element": "dark", "mp": 30, "multiplier": 2.5, "description": "어둠의 파동으로 광역 공격합니다"},
    "soul_eater": {"name": "영혼 포식", "type": "brv_attack", "element": "dark", "mp": 35, "multiplier": 3.5, "description": "적의 영혼을 먹어치웁니다"},
    "dark_aura": {"name": "암흑 오라", "type": "support", "mp": 30, "multiplier": 1.6, "description": "어둠의 기운으로 능력치를 증가시킵니다"},
    "apocalypse": {"name": "아포칼립스", "type": "ultimate", "element": "dark", "mp": 60, "multiplier": 6.5, "description": "종말의 어둠으로 모든 것을 삼킵니다"},

    # 드래곤 기사
    "jump": {"name": "점프", "type": "brv_attack", "element": "physical", "mp": 20, "multiplier": 3.0, "description": "높이 점프하여 적을 공격합니다"},
    "dragon_breath": {"name": "용의 숨결", "type": "brv_attack", "element": "fire", "mp": 25, "multiplier": 2.8, "description": "용의 화염을 내뿜습니다"},
    "wyvern_strike": {"name": "비룡격", "type": "brv_hp_attack", "element": "physical", "mp": 30, "multiplier": 2.6, "description": "비룡의 힘으로 강타합니다"},
    "dragon_dive": {"name": "드래곤 다이브", "type": "brv_attack", "element": "physical", "mp": 35, "multiplier": 3.8, "description": "하늘에서 급강하 공격합니다"},
    "dragon_soul": {"name": "용의 혼", "type": "support", "mp": 30, "multiplier": 1.7, "description": "용의 혼을 깨워 능력치를 강화합니다"},
    "bahamut_fury": {"name": "바하무트의 분노", "type": "ultimate", "element": "fire", "mp": 60, "multiplier": 6.8, "description": "용왕 바하무트의 힘을 빌려 공격합니다"},

    # 네크로맨서
    "death_bolt": {"name": "죽음의 화살", "type": "brv_attack", "element": "dark", "mp": 20, "multiplier": 2.6, "stat_base": "magic", "description": "죽음의 기운을 쏘아냅니다"},
    "summon_undead": {"name": "언데드 소환", "type": "support", "mp": 30, "multiplier": 1.0, "description": "언데드를 소환하여 전투를 돕습니다"},
    "life_drain": {"name": "생명력 흡수", "type": "brv_attack", "element": "dark", "mp": 25, "multiplier": 2.4, "stat_base": "magic", "description": "적의 생명력을 빼앗습니다"},
    "curse": {"name": "저주", "type": "debuff", "mp": 20, "multiplier": 0.6, "stat_base": "magic", "description": "적에게 저주를 겁니다"},
    "bone_prison": {"name": "뼈 감옥", "type": "debuff", "mp": 25, "multiplier": 0.5, "description": "뼈로 만든 감옥에 적을 가둡니다"},
    "army_of_dead": {"name": "죽음의 군단", "type": "ultimate", "element": "dark", "mp": 65, "multiplier": 5.5, "stat_base": "magic", "description": "언데드 군단을 소환합니다"},

    # 시간 마법사
    "haste": {"name": "헤이스트", "type": "support", "mp": 25, "multiplier": 1.5, "description": "아군의 속도를 증가시킵니다"},
    "slow": {"name": "슬로우", "type": "debuff", "mp": 20, "multiplier": 0.7, "description": "적의 속도를 감소시킵니다"},
    "stop": {"name": "스톱", "type": "debuff", "mp": 35, "multiplier": 0.0, "description": "적의 시간을 정지시킵니다"},
    "quick": {"name": "퀵", "type": "support", "mp": 40, "multiplier": 2.0, "description": "즉시 한 번 더 행동합니다"},
    "gravity_well": {"name": "중력장", "type": "debuff", "mp": 30, "multiplier": 0.5, "stat_base": "magic", "description": "중력장으로 적을 속박합니다"},
    "time_stop": {"name": "시간 정지", "type": "ultimate", "element": "magical", "mp": 70, "multiplier": 0.0, "stat_base": "magic", "description": "모든 적의 시간을 정지시킵니다"},

    # 소환사
    "summon_ifrit": {"name": "이프리트 소환", "type": "brv_attack", "element": "fire", "mp": 30, "multiplier": 3.2, "stat_base": "magic", "description": "화염의 정령 이프리트를 소환합니다"},
    "summon_shiva": {"name": "시바 소환", "type": "brv_attack", "element": "ice", "mp": 30, "multiplier": 3.2, "stat_base": "magic", "description": "얼음의 정령 시바를 소환합니다"},
    "summon_ramuh": {"name": "라무 소환", "type": "brv_attack", "element": "lightning", "mp": 30, "multiplier": 3.2, "stat_base": "magic", "description": "번개의 정령 라무를 소환합니다"},
    "summon_carbuncle": {"name": "카벙클 소환", "type": "support", "mp": 25, "multiplier": 1.5, "description": "보호의 정령 카벙클을 소환합니다"},
    "summon_phoenix": {"name": "피닉스 소환", "type": "support", "mp": 50, "multiplier": 3.0, "stat_base": "magic", "description": "불사조 피닉스를 소환합니다"},
    "summon_bahamut": {"name": "바하무트 소환", "type": "ultimate", "element": "fire", "mp": 80, "multiplier": 7.5, "stat_base": "magic", "description": "용왕 바하무트를 소환합니다"},

    # 음유시인
    "battle_song": {"name": "전투의 노래", "type": "support", "mp": 20, "multiplier": 1.3, "description": "노래로 아군의 공격력을 증가시킵니다"},
    "healing_song": {"name": "치유의 노래", "type": "heal", "mp": 25, "multiplier": 2.0, "stat_base": "magic", "description": "노래로 아군을 치유합니다"},
    "sleep_song": {"name": "수면의 노래", "type": "debuff", "mp": 20, "multiplier": 0.0, "description": "적을 잠들게 하는 노래입니다"},
    "speed_song": {"name": "속도의 노래", "type": "support", "mp": 25, "multiplier": 1.4, "description": "아군의 속도를 증가시킵니다"},
    "war_ballad": {"name": "전쟁 발라드", "type": "support", "mp": 30, "multiplier": 1.6, "description": "전투력을 크게 강화하는 발라드입니다"},
    "requiem": {"name": "진혼곡", "type": "ultimate", "element": "holy", "mp": 55, "multiplier": 5.0, "stat_base": "magic", "description": "적을 추모하는 강력한 진혼곡입니다"},

    # 드루이드
    "nature_wrath": {"name": "자연의 분노", "type": "brv_attack", "element": "earth", "mp": 20, "multiplier": 2.6, "stat_base": "magic", "description": "자연의 힘으로 적을 공격합니다"},
    "healing_touch": {"name": "치유의 손길", "type": "heal", "mp": 25, "multiplier": 2.8, "stat_base": "magic", "description": "자연의 치유력으로 아군을 회복시킵니다"},
    "entangle": {"name": "속박", "type": "debuff", "mp": 20, "multiplier": 0.0, "description": "덩굴로 적을 속박합니다"},
    "wild_shape": {"name": "야생 변신", "type": "support", "mp": 30, "multiplier": 1.7, "description": "야생 동물로 변신합니다"},
    "rejuvenation": {"name": "재생", "type": "support", "mp": 35, "multiplier": 1.5, "description": "지속적으로 HP를 회복합니다"},
    "natural_disaster": {"name": "천재지변", "type": "ultimate", "element": "earth", "mp": 60, "multiplier": 6.0, "stat_base": "magic", "description": "자연의 재앙을 불러옵니다"},

    # 배틀메이지
    "magic_sword": {"name": "마검", "type": "brv_attack", "element": "magical", "mp": 22, "multiplier": 2.7, "stat_base": "magic", "description": "마력이 깃든 검으로 공격합니다"},
    "spell_blade": {"name": "마법검", "type": "brv_hp_attack", "element": "magical", "mp": 28, "multiplier": 2.4, "stat_base": "magic", "description": "마법과 검술을 결합한 공격입니다"},
    "arcane_strike": {"name": "비전 공격", "type": "brv_attack", "element": "magical", "mp": 20, "multiplier": 2.5, "stat_base": "magic", "description": "비전 에너지로 강화된 공격입니다"},
    "combat_magic": {"name": "전투 마법", "type": "support", "mp": 25, "multiplier": 1.5, "description": "전투 중 마법 능력을 강화합니다"},
    "mana_blade": {"name": "마나 검", "type": "brv_attack", "element": "magical", "mp": 30, "multiplier": 3.0, "stat_base": "magic", "description": "순수한 마나로 만든 검입니다"},
    "mystic_fusion": {"name": "신비의 융합", "type": "ultimate", "element": "magical", "mp": 60, "multiplier": 6.2, "stat_base": "magic", "description": "마법과 검술의 궁극적 융합입니다"},

    # 원소술사
    "fire_storm": {"name": "화염 폭풍", "type": "brv_attack", "element": "fire", "mp": 25, "multiplier": 3.0, "stat_base": "magic", "description": "화염 폭풍을 일으킵니다"},
    "ice_lance": {"name": "얼음 창", "type": "brv_attack", "element": "ice", "mp": 25, "multiplier": 3.0, "stat_base": "magic", "description": "얼음 창으로 적을 관통합니다"},
    "lightning_chain": {"name": "연쇄 번개", "type": "brv_attack", "element": "lightning", "mp": 25, "multiplier": 2.8, "stat_base": "magic", "description": "번개가 여러 적에게 연쇄됩니다"},
    "earth_spike": {"name": "대지의 가시", "type": "brv_attack", "element": "earth", "mp": 20, "multiplier": 2.6, "stat_base": "magic", "description": "땅에서 가시를 솟아오르게 합니다"},
    "elemental_ward": {"name": "원소 보호", "type": "support", "mp": 30, "multiplier": 1.6, "description": "원소 공격에 대한 저항력을 높입니다"},
    "elemental_chaos": {"name": "원소 대혼돈", "type": "ultimate", "element": "magical", "mp": 65, "multiplier": 6.5, "stat_base": "magic", "description": "모든 원소가 폭발합니다"},

    # 연금술사
    "acid_bomb": {"name": "산성 폭탄", "type": "brv_attack", "element": "magical", "mp": 20, "multiplier": 2.6, "stat_base": "magic", "description": "산성 물질을 투척합니다"},
    "healing_potion": {"name": "치유 물약", "type": "heal", "mp": 15, "multiplier": 2.5, "stat_base": "magic", "description": "치유 물약으로 HP를 회복합니다"},
    "explosive_flask": {"name": "폭발 플라스크", "type": "brv_hp_attack", "element": "fire", "mp": 28, "multiplier": 2.3, "stat_base": "magic", "description": "폭발하는 플라스크를 던집니다"},
    "poison_gas": {"name": "독가스", "type": "debuff", "mp": 20, "multiplier": 0.8, "description": "독가스를 발생시킵니다"},
    "transmute": {"name": "연성", "type": "support", "mp": 30, "multiplier": 1.5, "description": "물질을 변환하여 능력을 강화합니다"},
    "philosophers_stone": {"name": "현자의 돌", "type": "ultimate", "element": "magical", "mp": 70, "multiplier": 6.0, "stat_base": "magic", "description": "현자의 돌의 힘을 해방합니다"},

    # 저격수
    "precision_shot": {"name": "정밀 사격", "type": "brv_attack", "element": "physical", "mp": 20, "multiplier": 3.5, "description": "정확한 사격으로 급소를 노립니다"},
    "headshot": {"name": "헤드샷", "type": "brv_attack", "element": "physical", "mp": 25, "multiplier": 4.0, "description": "머리를 정확히 노린 사격입니다"},
    "armor_pierce": {"name": "관통탄", "type": "brv_attack", "element": "physical", "mp": 22, "multiplier": 3.2, "description": "방어구를 관통하는 탄환입니다"},
    "take_aim": {"name": "조준", "type": "support", "mp": 15, "multiplier": 1.4, "description": "정밀하게 조준하여 명중률을 높입니다"},
    "camouflage": {"name": "위장", "type": "support", "mp": 20, "multiplier": 1.0, "description": "위장하여 회피율을 높입니다"},
    "deadeye": {"name": "데드아이", "type": "ultimate", "element": "physical", "mp": 55, "multiplier": 8.0, "description": "절대 빗나가지 않는 사격입니다"},

    # 해적
    "cutlass_slash": {"name": "커틀러스 베기", "type": "brv_attack", "element": "physical", "mp": 15, "multiplier": 2.4, "description": "커틀러스로 베어냅니다"},
    "pistol_shot": {"name": "권총 사격", "type": "brv_attack", "element": "physical", "mp": 18, "multiplier": 2.6, "description": "권총으로 사격합니다"},
    "grapple": {"name": "갈고리", "type": "debuff", "mp": 20, "multiplier": 0.7, "description": "갈고리로 적을 끌어당깁니다"},
    "sea_shanty": {"name": "선원의 노래", "type": "support", "mp": 25, "multiplier": 1.4, "description": "신나는 노래로 아군을 고무합니다"},
    "plunder": {"name": "약탈", "type": "support", "mp": 20, "multiplier": 1.0, "description": "적에게서 물건을 약탈합니다"},
    "cannonball": {"name": "대포 발사", "type": "ultimate", "element": "physical", "mp": 50, "multiplier": 5.5, "description": "대포를 발사하여 광역 피해를 입힙니다"},

    # 엔지니어
    "turret_deploy": {"name": "포탑 설치", "type": "support", "mp": 25, "multiplier": 1.0, "description": "자동 공격 포탑을 설치합니다"},
    "grenade": {"name": "수류탄", "type": "brv_hp_attack", "element": "physical", "mp": 20, "multiplier": 2.2, "description": "수류탄을 투척합니다"},
    "repair": {"name": "수리", "type": "heal", "mp": 20, "multiplier": 2.0, "stat_base": "magic", "description": "기계와 아군을 수리합니다"},
    "overclock": {"name": "오버클럭", "type": "support", "mp": 30, "multiplier": 1.7, "description": "능력치를 강제로 증가시킵니다"},
    "shield_generator": {"name": "방어막 생성기", "type": "support", "mp": 25, "multiplier": 1.5, "description": "에너지 방어막을 생성합니다"},
    "artillery_strike": {"name": "포격", "type": "ultimate", "element": "physical", "mp": 60, "multiplier": 6.0, "description": "강력한 포격을 가합니다"},

    # 해커
    "system_hack": {"name": "시스템 해킹", "type": "debuff", "mp": 20, "multiplier": 0.7, "description": "적의 시스템을 해킹합니다"},
    "virus_upload": {"name": "바이러스 업로드", "type": "debuff", "mp": 25, "multiplier": 0.5, "description": "치명적인 바이러스를 업로드합니다"},
    "firewall": {"name": "방화벽", "type": "support", "mp": 25, "multiplier": 1.5, "description": "방화벽으로 보호합니다"},
    "ddos_attack": {"name": "DDoS 공격", "type": "brv_attack", "element": "magical", "mp": 30, "multiplier": 2.8, "stat_base": "magic", "description": "과부하 공격으로 적을 무력화합니다"},
    "backdoor": {"name": "백도어", "type": "support", "mp": 35, "multiplier": 1.0, "description": "백도어를 설치하여 정보를 훔칩니다"},
    "zero_day": {"name": "제로데이", "type": "ultimate", "element": "magical", "mp": 70, "multiplier": 7.0, "stat_base": "magic", "description": "제로데이 익스플로잇으로 완전 장악합니다"},

    # 차원술사
    "dimension_slash": {"name": "차원 베기", "type": "brv_attack", "element": "magical", "mp": 25, "multiplier": 3.0, "stat_base": "magic", "description": "차원을 가르는 공격입니다"},
    "portal": {"name": "포탈", "type": "support", "mp": 30, "multiplier": 1.0, "description": "순간이동 포탈을 엽니다"},
    "dimensional_rift": {"name": "차원 균열", "type": "brv_hp_attack", "element": "magical", "mp": 35, "multiplier": 2.6, "stat_base": "magic", "description": "차원 균열로 적을 공격합니다"},
    "phase_shift": {"name": "위상 변이", "type": "support", "mp": 25, "multiplier": 1.6, "description": "다른 차원으로 이동하여 회피율을 높입니다"},
    "void_prison": {"name": "공허의 감옥", "type": "debuff", "mp": 30, "multiplier": 0.0, "description": "적을 공허 공간에 가둡니다"},
    "dimensional_collapse": {"name": "차원 붕괴", "type": "ultimate", "element": "magical", "mp": 75, "multiplier": 7.5, "stat_base": "magic", "description": "차원을 붕괴시켜 모든 것을 소멸시킵니다"},

    # 철학자
    "logic_strike": {"name": "논리 공격", "type": "brv_attack", "element": "magical", "mp": 20, "multiplier": 2.4, "stat_base": "magic", "description": "논리로 적의 모순을 공격합니다"},
    "enlightenment": {"name": "깨달음", "type": "support", "mp": 30, "multiplier": 1.8, "description": "깨달음으로 능력치를 대폭 강화합니다"},
    "paradox": {"name": "역설", "type": "debuff", "mp": 25, "multiplier": 0.6, "description": "역설로 적을 혼란시킵니다"},
    "meditation": {"name": "사색", "type": "heal", "mp": 20, "multiplier": 2.0, "stat_base": "magic", "description": "사색을 통해 정신력을 회복합니다"},
    "wisdom": {"name": "지혜", "type": "support", "mp": 35, "multiplier": 1.7, "description": "지혜로 모든 능력을 강화합니다"},
    "absolute_truth": {"name": "절대 진리", "type": "ultimate", "element": "holy", "mp": 80, "multiplier": 8.0, "stat_base": "magic", "description": "절대 진리의 힘을 발현합니다"},

    # 뱀파이어
    "blood_drain": {"name": "피 흡수", "type": "brv_attack", "element": "dark", "mp": 20, "multiplier": 2.4, "description": "적의 피를 빨아먹습니다"},
    "bat_swarm": {"name": "박쥐 떼", "type": "brv_attack", "element": "dark", "mp": 25, "multiplier": 2.6, "description": "박쥐 떼로 적을 공격합니다"},
    "charm": {"name": "매혹", "type": "debuff", "mp": 20, "multiplier": 0.0, "description": "적을 매혹시켜 조종합니다"},
    "mist_form": {"name": "안개 형상", "type": "support", "mp": 25, "multiplier": 1.0, "description": "안개가 되어 공격을 회피합니다"},
    "blood_rage": {"name": "피의 광란", "type": "support", "mp": 30, "multiplier": 1.8, "description": "피에 굶주려 능력이 증가합니다"},
    "crimson_apocalypse": {"name": "진홍의 종말", "type": "ultimate", "element": "dark", "mp": 65, "multiplier": 6.8, "description": "피의 종말을 불러옵니다"},

    # 샤먼
    "spirit_strike": {"name": "영혼 공격", "type": "brv_attack", "element": "magical", "mp": 18, "multiplier": 2.5, "stat_base": "magic", "description": "영혼의 힘으로 공격합니다"},
    "totem": {"name": "토템", "type": "support", "mp": 25, "multiplier": 1.5, "description": "토템을 설치하여 아군을 강화합니다"},
    "spirit_walk": {"name": "영혼 보행", "type": "support", "mp": 30, "multiplier": 1.0, "description": "영혼 상태가 되어 이동합니다"},
    "ancestral_power": {"name": "조상의 힘", "type": "support", "mp": 30, "multiplier": 1.7, "description": "조상의 힘을 빌립니다"},
    "hex": {"name": "저주", "type": "debuff", "mp": 20, "multiplier": 0.7, "description": "적에게 저주를 겁니다"},
    "spirit_fury": {"name": "영혼의 분노", "type": "ultimate", "element": "magical", "mp": 60, "multiplier": 6.2, "stat_base": "magic", "description": "모든 영혼의 분노를 발현합니다"},

    # 브레이커
    "break_strike": {"name": "브레이크 공격", "type": "brv_attack", "element": "physical", "mp": 20, "multiplier": 2.2, "description": "BRV를 크게 깎는 공격입니다"},
    "shatter": {"name": "분쇄", "type": "brv_attack", "element": "physical", "mp": 25, "multiplier": 2.8, "description": "방어구를 분쇄합니다"},
    "break_combo": {"name": "브레이크 콤보", "type": "brv_hp_attack", "element": "physical", "mp": 30, "multiplier": 2.4, "description": "연속으로 BRV를 깎습니다"},
    "defense_break": {"name": "방어 분쇄", "type": "debuff", "mp": 20, "multiplier": 0.5, "description": "적의 방어력을 크게 감소시킵니다"},
    "break_boost": {"name": "브레이크 강화", "type": "support", "mp": 25, "multiplier": 1.6, "description": "브레이크 효율을 증가시킵니다"},
    "total_break": {"name": "완전 분쇄", "type": "ultimate", "element": "physical", "mp": 55, "multiplier": 6.5, "description": "모든 것을 완전히 분쇄합니다"},

    # 검투사
    "dual_strike": {"name": "이도류 공격", "type": "brv_attack", "element": "physical", "mp": 18, "multiplier": 2.6, "description": "양손의 검으로 연속 공격합니다"},
    "gladius_thrust": {"name": "글라디우스 찌르기", "type": "brv_attack", "element": "physical", "mp": 20, "multiplier": 2.8, "description": "짧은 검으로 빠르게 찌릅니다"},
    "arena_roar": {"name": "투기장의 함성", "type": "support", "mp": 25, "multiplier": 1.4, "description": "함성으로 자신을 강화합니다"},
    "counter_stance": {"name": "반격 자세", "type": "support", "mp": 20, "multiplier": 1.3, "description": "반격 자세를 취합니다"},
    "blood_sport": {"name": "혈전", "type": "support", "mp": 30, "multiplier": 1.7, "description": "피를 흘릴수록 강해집니다"},
    "colosseum_champion": {"name": "콜로세움의 챔피언", "type": "ultimate", "element": "physical", "mp": 55, "multiplier": 6.0, "description": "챔피언의 필살기입니다"},

    # 스펠블레이드
    "frost_blade": {"name": "얼음 검", "type": "brv_attack", "element": "ice", "mp": 22, "multiplier": 2.7, "description": "얼음 마법이 깃든 검격입니다"},
    "flame_sword": {"name": "화염 검", "type": "brv_attack", "element": "fire", "mp": 22, "multiplier": 2.7, "description": "화염 마법이 깃든 검격입니다"},
    "thunder_edge": {"name": "번개 검", "type": "brv_attack", "element": "lightning", "mp": 22, "multiplier": 2.7, "description": "번개 마법이 깃든 검격입니다"},
    "spell_weaving": {"name": "마법 직조", "type": "support", "mp": 28, "multiplier": 1.6, "description": "마법을 엮어 검을 강화합니다"},
    "elemental_burst": {"name": "원소 폭발", "type": "brv_hp_attack", "element": "magical", "mp": 32, "multiplier": 2.5, "description": "원소 에너지를 폭발시킵니다"},
    "prismatic_slash": {"name": "프리즘 베기", "type": "ultimate", "element": "magical", "mp": 60, "multiplier": 6.5, "stat_base": "magic", "description": "모든 원소의 힘을 담은 일격입니다"},
}


def load_all_characters() -> Dict[str, Dict]:
    """모든 캐릭터 데이터를 로드합니다."""
    characters = {}

    for yaml_file in CHARACTERS_DIR.glob("*.yaml"):
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            class_id = yaml_file.stem
            characters[class_id] = data

    return characters


def determine_skill_type(skill_id: str, class_data: Dict) -> str:
    """스킬 타입을 추론합니다."""
    # 기본 정의가 있으면 사용
    if skill_id in SKILL_DEFINITIONS:
        return SKILL_DEFINITIONS[skill_id]["type"]

    # 스킬명 패턴으로 추론
    skill_name = skill_id.lower()

    if any(word in skill_name for word in ["heal", "cure", "prayer", "resurrection"]):
        return "heal"
    elif any(word in skill_name for word in ["ultimate", "fury", "apocalypse", "judgment", "strike", "slash"]) and skill_id.endswith(("_ultimate", "_slash", "_fury", "_strike")):
        return "ultimate"
    elif any(word in skill_name for word in ["buff", "stance", "shield", "barrier", "aura", "ward"]):
        return "support"
    elif any(word in skill_name for word in ["debuff", "slow", "curse", "mark", "hex", "break"]):
        return "debuff"
    elif any(word in skill_name for word in ["combo", "burst", "explosion"]):
        return "brv_hp_attack"
    else:
        return "brv_attack"


def determine_element(skill_id: str, class_data: Dict) -> str:
    """스킬 속성을 추론합니다."""
    # 기본 정의가 있으면 사용
    if skill_id in SKILL_DEFINITIONS and "element" in SKILL_DEFINITIONS[skill_id]:
        return SKILL_DEFINITIONS[skill_id]["element"]

    skill_name = skill_id.lower()
    archetype = class_data.get("archetype", "").lower()

    # 스킬명으로 속성 판단
    if any(word in skill_name for word in ["fire", "flame", "burn", "meteor"]):
        return "fire"
    elif any(word in skill_name for word in ["ice", "frost", "blizzard", "freeze"]):
        return "ice"
    elif any(word in skill_name for word in ["thunder", "lightning", "bolt"]):
        return "lightning"
    elif any(word in skill_name for word in ["earth", "stone", "quake"]):
        return "earth"
    elif any(word in skill_name for word in ["holy", "divine", "sacred", "light"]):
        return "holy"
    elif any(word in skill_name for word in ["dark", "shadow", "death", "curse"]):
        return "dark"
    elif any(word in skill_name for word in ["magic", "arcane", "spell"]):
        return "magical"

    # 직업 특성으로 속성 판단
    if "마법" in archetype or "magic" in archetype.lower():
        return "magical"
    else:
        return "physical"


def determine_stat_base(skill_id: str, class_data: Dict, element: str) -> str:
    """스킬이 사용하는 기본 스탯을 추론합니다."""
    # 기본 정의가 있으면 사용
    if skill_id in SKILL_DEFINITIONS and "stat_base" in SKILL_DEFINITIONS[skill_id]:
        return SKILL_DEFINITIONS[skill_id]["stat_base"]

    archetype = class_data.get("archetype", "").lower()

    # 마법 관련 직업이거나 마법 속성이면 magic 사용
    if "마법" in archetype or "magic" in archetype.lower() or element in ["fire", "ice", "lightning", "magical", "holy", "dark", "earth"]:
        return "magic"
    else:
        return "strength"


def create_skill_data(skill_id: str, class_data: Dict) -> Dict:
    """스킬 데이터를 생성합니다."""
    # 기본 정의 확인
    if skill_id in SKILL_DEFINITIONS:
        definition = SKILL_DEFINITIONS[skill_id]
        skill_name = definition["name"]
        skill_type = definition["type"]
        element = definition.get("element", "physical")
        mp_cost = definition.get("mp", 20)
        multiplier = definition.get("multiplier", 2.0)
        description = definition.get("description", "")
        stat_base = definition.get("stat_base")
    else:
        # 스킬 ID에서 이름 생성
        skill_name = skill_id.replace("_", " ").title()
        skill_type = determine_skill_type(skill_id, class_data)
        element = determine_element(skill_id, class_data)
        mp_cost = 20
        multiplier = 2.0
        description = f"{skill_name} 스킬"
        stat_base = None

    # stat_base 결정
    if stat_base is None:
        stat_base = determine_stat_base(skill_id, class_data, element)

    # 스킬 타입에 따른 기본 구조
    skill_data = {
        "id": skill_id,
        "name": skill_name,
        "type": skill_type,
        "description": description,
        "costs": {
            "mp": mp_cost,
            "cast_time": 1.0 if skill_type != "ultimate" else 2.0
        }
    }

    # 효과 추가
    if skill_type == "brv_attack":
        skill_data["effects"] = [
            {
                "type": "damage",
                "element": element,
                "multiplier": multiplier,
                "stat_base": stat_base
            }
        ]
    elif skill_type == "hp_attack":
        skill_data["effects"] = [
            {
                "type": "hp_damage",
                "multiplier": multiplier,
                "uses_brv": True
            }
        ]
    elif skill_type == "brv_hp_attack":
        skill_data["effects"] = [
            {
                "type": "damage",
                "element": element,
                "multiplier": multiplier * 0.8,
                "stat_base": stat_base
            },
            {
                "type": "hp_damage",
                "multiplier": multiplier * 0.6,
                "uses_brv": True
            }
        ]
    elif skill_type == "heal":
        skill_data["effects"] = [
            {
                "type": "heal",
                "target": "ally",
                "multiplier": multiplier,
                "stat_base": stat_base
            }
        ]
    elif skill_type == "support":
        skill_data["effects"] = [
            {
                "type": "buff",
                "target": "self",
                "stat": "physical_attack",
                "value": multiplier,
                "duration": 3
            }
        ]
    elif skill_type == "debuff":
        skill_data["effects"] = [
            {
                "type": "debuff",
                "target": "enemy",
                "stat": "physical_defense",
                "value": multiplier,
                "duration": 3
            }
        ]
    elif skill_type == "ultimate":
        skill_data["effects"] = [
            {
                "type": "damage",
                "element": element,
                "multiplier": multiplier,
                "stat_base": stat_base
            },
            {
                "type": "hp_damage",
                "multiplier": multiplier * 0.4,
                "uses_brv": True
            }
        ]

    return skill_data


def generate_all_skills():
    """모든 스킬 YAML 파일을 생성합니다."""
    # 스킬 디렉토리 생성
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    # 캐릭터 데이터 로드
    characters = load_all_characters()

    total_skills = 0
    created_skills = 0
    skipped_skills = 0

    # 각 캐릭터의 스킬 생성
    for class_id, class_data in characters.items():
        class_name = class_data.get("class_name", class_id)
        skills = class_data.get("skills", [])

        print(f"\n[{class_name}] - {len(skills)}개 스킬 생성 중...")

        for skill_id in skills:
            total_skills += 1
            skill_file = SKILLS_DIR / f"{skill_id}.yaml"

            # 이미 존재하는 파일은 건너뛰기
            if skill_file.exists():
                print(f"  [SKIP] {skill_id} (이미 존재)")
                skipped_skills += 1
                continue

            # 스킬 데이터 생성
            skill_data = create_skill_data(skill_id, class_data)

            # YAML 파일로 저장
            with open(skill_file, 'w', encoding='utf-8') as f:
                yaml.dump(skill_data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

            print(f"  [OK] {skill_id} ({skill_data['name']})")
            created_skills += 1

    # 요약 출력
    print("\n" + "="*60)
    print("스킬 생성 완료!")
    print(f"총 스킬 수: {total_skills}개")
    print(f"새로 생성: {created_skills}개")
    print(f"건너뜀: {skipped_skills}개")
    print("="*60)


if __name__ == "__main__":
    generate_all_skills()
