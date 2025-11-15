"""
Basic Attacks - 직업별 기본 공격 프로필

각 직업의 기본 BRV 공격과 HP 공격의 고유한 특성을 정의합니다.
"""

from typing import Dict, Any, Optional


# 직업별 기본 공격 프로필
JOB_ATTACK_PROFILES: Dict[str, Dict[str, Any]] = {
    # ===== 물리 딜러 계열 =====
    "warrior": {
        "brv_attack": {
            "name": "강타",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.3,
            "can_critical": True,
            "description": "힘을 집중한 강력한 일격"
        },
        "hp_attack": {
            "name": "방패 강타",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.1,
            "can_critical": False,
            "description": "방패로 적을 강타하여 BRV를 HP 데미지로 전환"
        }
    },

    "berserker": {
        "brv_attack": {
            "name": "광란의 일격",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.5,
            "can_critical": True,
            "critical_bonus": 0.2,  # +20% 크리티컬 확률
            "description": "광기를 담은 파괴적인 일격"
        },
        "hp_attack": {
            "name": "피의 수확",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.3,
            "can_critical": True,
            "description": "BRV를 HP 데미지로 전환하며 자신도 소량 피해"
        }
    },

    "gladiator": {
        "brv_attack": {
            "name": "검투사의 타격",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.4,
            "can_critical": True,
            "description": "투기장에서 단련된 완벽한 타격"
        },
        "hp_attack": {
            "name": "결투의 일격",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.2,
            "can_critical": True,
            "description": "일대일 전투에 특화된 결정타"
        }
    },

    "dark_knight": {
        "brv_attack": {
            "name": "암흑 베기",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.35,
            "can_critical": True,
            "element": "dark",
            "description": "어둠의 힘을 담은 베기"
        },
        "hp_attack": {
            "name": "생명 흡수",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.0,
            "can_critical": False,
            "lifesteal": 0.2,  # 20% 흡혈
            "description": "적의 생명력을 흡수하는 공격"
        }
    },

    "knight": {
        "brv_attack": {
            "name": "기사의 창",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.2,
            "can_critical": True,
            "description": "기사도를 담은 정직한 일격"
        },
        "hp_attack": {
            "name": "수호의 타격",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 0.9,
            "can_critical": False,
            "defense_bonus": 0.1,  # 방어력 10% 추가 반영
            "description": "방어력을 활용한 안정적인 공격"
        }
    },

    "paladin": {
        "brv_attack": {
            "name": "성스러운 일격",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.1,
            "can_critical": True,
            "element": "holy",
            "description": "신성한 힘이 깃든 타격"
        },
        "hp_attack": {
            "name": "응징의 빛",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 0.95,
            "can_critical": False,
            "spirit_scaling": 0.3,  # 정신력 30% 추가
            "description": "정의의 빛으로 악을 응징"
        }
    },

    # ===== 속도형 물리 딜러 =====
    "assassin": {
        "brv_attack": {
            "name": "암살",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.25,
            "can_critical": True,
            "critical_bonus": 0.25,  # +25% 크리티컬 확률
            "description": "급소를 노린 치명적인 일격"
        },
        "hp_attack": {
            "name": "그림자 일격",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.15,
            "can_critical": True,
            "speed_scaling": 0.2,  # 속도 20% 추가
            "description": "그림자처럼 빠른 공격"
        }
    },

    "rogue": {
        "brv_attack": {
            "name": "기습",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.2,
            "can_critical": True,
            "critical_bonus": 0.15,
            "description": "예상치 못한 각도의 공격"
        },
        "hp_attack": {
            "name": "독침",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.0,
            "can_critical": True,
            "poison_chance": 0.3,  # 30% 독 부여
            "description": "독을 바른 무기로 가격"
        }
    },

    "pirate": {
        "brv_attack": {
            "name": "난폭한 일격",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.35,
            "can_critical": True,
            "luck_scaling": 0.15,  # 행운 15% 추가
            "description": "거친 해적의 공격"
        },
        "hp_attack": {
            "name": "약탈의 일격",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.1,
            "can_critical": True,
            "description": "적의 재화까지 노리는 공격"
        }
    },

    # ===== 원거리 물리 딜러 =====
    "archer": {
        "brv_attack": {
            "name": "정밀 사격",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.15,
            "can_critical": True,
            "accuracy_bonus": 20,  # +20 명중
            "description": "조준된 화살 공격"
        },
        "hp_attack": {
            "name": "관통 화살",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.05,
            "can_critical": True,
            "ignore_defense": 0.2,  # 방어력 20% 무시
            "description": "적의 방어를 뚫는 화살"
        }
    },

    "sniper": {
        "brv_attack": {
            "name": "조준 사격",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.1,
            "can_critical": True,
            "critical_multiplier": 2.0,  # 크리티컬 배율 증가
            "description": "완벽히 조준한 일격"
        },
        "hp_attack": {
            "name": "저격",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.0,
            "can_critical": True,
            "critical_multiplier": 2.5,
            "description": "단 한 발로 결정짓는 저격"
        }
    },

    "engineer": {
        "brv_attack": {
            "name": "기계 타격",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.2,
            "can_critical": True,
            "magic_scaling": 0.2,  # 마법력 20% 추가
            "description": "마공학 장치를 이용한 공격"
        },
        "hp_attack": {
            "name": "폭발 공격",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.15,
            "can_critical": False,
            "splash_damage": 0.3,  # 광역 30%
            "description": "폭발물을 활용한 광역 공격"
        }
    },

    # ===== 격투가 계열 =====
    "monk": {
        "brv_attack": {
            "name": "철권",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.25,
            "can_critical": True,
            "combo_scaling": True,  # 콤보 스택에 따라 증가
            "description": "수련된 주먹 공격"
        },
        "hp_attack": {
            "name": "기공파",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.1,
            "can_critical": True,
            "ki_scaling": True,  # 기 에너지에 비례
            "description": "내공을 담은 일격"
        }
    },

    "samurai": {
        "brv_attack": {
            "name": "발도",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.4,
            "can_critical": True,
            "critical_bonus": 0.1,
            "description": "순식간의 발도 베기"
        },
        "hp_attack": {
            "name": "일섬",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.2,
            "can_critical": True,
            "description": "단 한 번의 완벽한 베기"
        }
    },

    "sword_saint": {
        "brv_attack": {
            "name": "검기 베기",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.35,
            "can_critical": True,
            "aura_scaling": True,  # 검기에 비례
            "description": "검기를 두른 일격"
        },
        "hp_attack": {
            "name": "섬공",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.15,
            "can_critical": True,
            "range_bonus": True,  # 원거리 가능
            "description": "검기를 날려 공격"
        }
    },

    "dragon_knight": {
        "brv_attack": {
            "name": "용의 발톱",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.3,
            "can_critical": True,
            "element": "dragon",
            "description": "용의 힘이 깃든 공격"
        },
        "hp_attack": {
            "name": "용의 숨결",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.2,
            "can_critical": False,
            "element": "fire",
            "splash_damage": 0.4,
            "description": "용의 브레스 공격"
        }
    },

    # ===== 마법 딜러 계열 =====
    "mage": {
        "brv_attack": {
            "name": "마법 화살",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 1.2,
            "can_critical": True,
            "description": "마력으로 만든 화살"
        },
        "hp_attack": {
            "name": "마력 폭발",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 1.0,
            "can_critical": False,
            "element": "arcane",
            "description": "마력을 폭발시켜 공격"
        }
    },

    "archmage": {
        "brv_attack": {
            "name": "대마법",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 1.3,
            "can_critical": True,
            "element_combo": True,  # 원소 조합
            "description": "강력한 마법 공격"
        },
        "hp_attack": {
            "name": "원소 융합",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 1.1,
            "can_critical": True,
            "element_combo": True,
            "description": "여러 원소를 융합한 공격"
        }
    },

    "elementalist": {
        "brv_attack": {
            "name": "정령의 축복",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 1.25,
            "can_critical": True,
            "element": "nature",
            "spirit_bond_scaling": True,
            "description": "정령의 힘을 빌린 공격"
        },
        "hp_attack": {
            "name": "정령 소환",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 1.05,
            "can_critical": False,
            "element": "nature",
            "description": "정령을 불러 공격"
        }
    },

    "battle_mage": {
        "brv_attack": {
            "name": "마검",
            "damage_type": "hybrid",  # 물리 + 마법
            "stat_base": "both",
            "base_multiplier": 1.15,
            "can_critical": True,
            "physical_ratio": 0.6,
            "magic_ratio": 0.4,
            "description": "마법과 검술의 융합"
        },
        "hp_attack": {
            "name": "마력 베기",
            "damage_type": "hybrid",
            "stat_base": "both",
            "base_multiplier": 1.0,
            "can_critical": True,
            "physical_ratio": 0.5,
            "magic_ratio": 0.5,
            "description": "물리와 마법을 동시에"
        }
    },

    "spellblade": {
        "brv_attack": {
            "name": "마력 부여",
            "damage_type": "hybrid",
            "stat_base": "both",
            "base_multiplier": 1.2,
            "can_critical": True,
            "physical_ratio": 0.7,
            "magic_ratio": 0.3,
            "element": "variable",
            "description": "검에 마법을 부여한 공격"
        },
        "hp_attack": {
            "name": "원소 베기",
            "damage_type": "hybrid",
            "stat_base": "both",
            "base_multiplier": 1.05,
            "can_critical": True,
            "physical_ratio": 0.6,
            "magic_ratio": 0.4,
            "element": "variable",
            "description": "원소를 담은 베기"
        }
    },

    "necromancer": {
        "brv_attack": {
            "name": "생명 흡수",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 1.15,
            "can_critical": False,
            "element": "dark",
            "lifesteal": 0.15,
            "description": "생명력을 빼앗는 마법"
        },
        "hp_attack": {
            "name": "네크로 폭발",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 1.0,
            "can_critical": False,
            "element": "dark",
            "necro_scaling": True,
            "description": "네크로 에너지를 폭발"
        }
    },

    "time_mage": {
        "brv_attack": {
            "name": "시간 왜곡",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 1.1,
            "can_critical": True,
            "slow_chance": 0.2,  # 20% 슬로우
            "description": "시간을 왜곡하여 공격"
        },
        "hp_attack": {
            "name": "시간 붕괴",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 0.95,
            "can_critical": False,
            "time_mark_scaling": True,
            "description": "시간의 흐름을 붕괴"
        }
    },

    "dimensionist": {
        "brv_attack": {
            "name": "차원 베기",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 1.25,
            "can_critical": True,
            "ignore_defense": 0.3,  # 방어 30% 무시
            "description": "차원을 베어 공격"
        },
        "hp_attack": {
            "name": "공간 붕괴",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 1.1,
            "can_critical": False,
            "splash_damage": 0.5,
            "description": "공간을 붕괴시켜 공격"
        }
    },

    # ===== 지원 계열 =====
    "priest": {
        "brv_attack": {
            "name": "성스러운 빛",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 0.9,
            "can_critical": False,
            "element": "holy",
            "description": "신성한 빛으로 공격"
        },
        "hp_attack": {
            "name": "심판의 빛",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 0.8,
            "can_critical": False,
            "element": "holy",
            "spirit_scaling": 0.4,
            "description": "죄를 심판하는 빛"
        }
    },

    "cleric": {
        "brv_attack": {
            "name": "치유의 빛",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 0.85,
            "can_critical": False,
            "element": "holy",
            "heal_on_hit": 0.1,  # 10% 자힐
            "description": "치유의 힘이 담긴 공격"
        },
        "hp_attack": {
            "name": "신성한 망치",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 0.75,
            "can_critical": False,
            "element": "holy",
            "description": "신의 분노를 담은 망치"
        }
    },

    "bard": {
        "brv_attack": {
            "name": "음파 공격",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 0.95,
            "can_critical": True,
            "melody_scaling": True,
            "description": "음파로 적을 공격"
        },
        "hp_attack": {
            "name": "불협화음",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 0.85,
            "can_critical": False,
            "debuff_chance": 0.3,  # 30% 약화
            "description": "불협화음으로 혼란"
        }
    },

    "druid": {
        "brv_attack": {
            "name": "자연의 분노",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 1.0,
            "can_critical": True,
            "element": "nature",
            "description": "자연의 힘으로 공격"
        },
        "hp_attack": {
            "name": "가시 덤불",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 0.9,
            "can_critical": False,
            "element": "nature",
            "dot_damage": 0.15,  # 15% 지속 데미지
            "description": "가시덤불로 공격"
        }
    },

    "shaman": {
        "brv_attack": {
            "name": "토템의 힘",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 1.05,
            "can_critical": True,
            "element": "nature",
            "description": "토템의 힘을 빌린 공격"
        },
        "hp_attack": {
            "name": "정령의 분노",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 0.95,
            "can_critical": False,
            "element": "nature",
            "description": "정령의 분노를 불러옴"
        }
    },

    # ===== 특수 계열 =====
    "vampire": {
        "brv_attack": {
            "name": "흡혈",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.2,
            "can_critical": True,
            "element": "dark",
            "lifesteal": 0.25,  # 25% 흡혈
            "description": "피를 빨아들이는 공격"
        },
        "hp_attack": {
            "name": "피의 마법",
            "damage_type": "hybrid",
            "stat_base": "both",
            "base_multiplier": 1.1,
            "can_critical": False,
            "physical_ratio": 0.5,
            "magic_ratio": 0.5,
            "lifesteal": 0.15,
            "description": "피로 만든 마법"
        }
    },

    "breaker": {
        "brv_attack": {
            "name": "브레이크 타격",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.4,
            "can_critical": True,
            "break_efficiency": 1.5,  # BRV 깎기 150%
            "description": "적의 BRV를 파괴하는 공격"
        },
        "hp_attack": {
            "name": "파쇄 일격",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.25,
            "can_critical": True,
            "break_bonus": 0.5,  # BREAK 시 보너스
            "description": "파괴에 특화된 공격"
        }
    },

    "alchemist": {
        "brv_attack": {
            "name": "연금술 타격",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 1.15,
            "can_critical": True,
            "element": "variable",
            "description": "연금술 물약을 투척"
        },
        "hp_attack": {
            "name": "폭발 물약",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 1.05,
            "can_critical": False,
            "splash_damage": 0.4,
            "description": "폭발하는 물약 공격"
        }
    },

    "philosopher": {
        "brv_attack": {
            "name": "진리의 타격",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 1.1,
            "can_critical": True,
            "wisdom_scaling": True,
            "description": "진리를 깨달은 자의 공격"
        },
        "hp_attack": {
            "name": "철학자의 돌",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 1.0,
            "can_critical": False,
            "mp_restore": 0.1,  # 10% MP 회복
            "description": "현자의 돌의 힘"
        }
    },

    "hacker": {
        "brv_attack": {
            "name": "해킹 공격",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 1.2,
            "can_critical": True,
            "debuff_chance": 0.25,  # 25% 약화
            "description": "시스템을 해킹하여 공격"
        },
        "hp_attack": {
            "name": "바이러스",
            "damage_type": "magic",
            "stat_base": "magic",
            "base_multiplier": 1.0,
            "can_critical": False,
            "dot_damage": 0.2,  # 20% 지속 데미지
            "description": "치명적인 바이러스 공격"
        }
    }
}


def get_attack_profile(job_id: str, attack_type: str) -> Dict[str, Any]:
    """
    직업의 기본 공격 프로필을 가져옵니다.

    Args:
        job_id: 직업 ID
        attack_type: 'brv_attack' 또는 'hp_attack'

    Returns:
        공격 프로필 딕셔너리
    """
    # 직업 프로필 조회
    profile = JOB_ATTACK_PROFILES.get(job_id)

    if not profile:
        # 기본 프로필 반환
        return get_default_profile(attack_type)

    # 공격 타입 프로필 조회
    attack_profile = profile.get(attack_type)

    if not attack_profile:
        return get_default_profile(attack_type)

    return attack_profile.copy()


def get_default_profile(attack_type: str) -> Dict[str, Any]:
    """
    기본 공격 프로필을 반환합니다.

    Args:
        attack_type: 'brv_attack' 또는 'hp_attack'

    Returns:
        기본 공격 프로필
    """
    if attack_type == "brv_attack":
        return {
            "name": "타격",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 1.0,
            "can_critical": True,
            "description": "기본 타격"
        }
    else:  # hp_attack
        return {
            "name": "HP 공격",
            "damage_type": "physical",
            "stat_base": "strength",
            "base_multiplier": 0.9,
            "can_critical": False,
            "description": "기본 HP 공격"
        }


def calculate_stat_value(character: Any, profile: Dict[str, Any]) -> float:
    """
    프로필에 따라 스탯 값을 계산합니다.

    Args:
        character: 캐릭터 객체
        profile: 공격 프로필

    Returns:
        계산된 스탯 값
    """
    stat_base = profile.get("stat_base", "strength")
    damage_type = profile.get("damage_type", "physical")

    # 기본 스탯
    if stat_base == "strength" or damage_type == "physical":
        base_stat = getattr(character, "strength", 50)
    elif stat_base == "magic" or damage_type == "magic":
        base_stat = getattr(character, "magic", 50)
    elif stat_base == "both" or damage_type == "hybrid":
        # 하이브리드는 물리/마법 비율 적용
        physical_ratio = profile.get("physical_ratio", 0.5)
        magic_ratio = profile.get("magic_ratio", 0.5)

        strength = getattr(character, "strength", 50)
        magic = getattr(character, "magic", 50)

        base_stat = strength * physical_ratio + magic * magic_ratio
    else:
        base_stat = 50

    # 추가 스탯 스케일링
    total_stat = base_stat

    # 방어력 추가 (기사 등)
    if profile.get("defense_bonus"):
        defense = getattr(character, "defense", 0)
        total_stat += defense * profile["defense_bonus"]

    # 정신력 추가 (팔라딘, 신관 등)
    if profile.get("spirit_scaling"):
        spirit = getattr(character, "spirit", 0)
        total_stat += spirit * profile["spirit_scaling"]

    # 속도 추가 (암살자 등)
    if profile.get("speed_scaling"):
        speed = getattr(character, "speed", 0)
        total_stat += speed * profile["speed_scaling"]

    # 행운 추가 (해적 등)
    if profile.get("luck_scaling"):
        luck = getattr(character, "luck", 0)
        total_stat += luck * profile["luck_scaling"]

    # 마법력 추가 (엔지니어 등)
    if profile.get("magic_scaling") and stat_base == "strength":
        magic = getattr(character, "magic", 0)
        total_stat += magic * profile["magic_scaling"]

    return total_stat


def get_critical_chance_modifier(character: Any, profile: Dict[str, Any]) -> float:
    """
    프로필에 따른 크리티컬 확률 보정치를 반환합니다.

    Args:
        character: 캐릭터 객체
        profile: 공격 프로필

    Returns:
        크리티컬 확률 보정치 (0.0 ~ 1.0)
    """
    if not profile.get("can_critical", False):
        return 0.0

    # 기본 크리티컬 보너스
    critical_bonus = profile.get("critical_bonus", 0.0)

    return critical_bonus


def get_critical_multiplier(profile: Dict[str, Any]) -> float:
    """
    프로필에 따른 크리티컬 배율을 반환합니다.

    Args:
        profile: 공격 프로필

    Returns:
        크리티컬 배율
    """
    if not profile.get("can_critical", False):
        return 1.0

    return profile.get("critical_multiplier", 1.5)


def get_defense_ignore(profile: Dict[str, Any]) -> float:
    """
    방어력 무시 비율을 반환합니다.

    Args:
        profile: 공격 프로필

    Returns:
        방어력 무시 비율 (0.0 ~ 1.0)
    """
    return profile.get("ignore_defense", 0.0)
