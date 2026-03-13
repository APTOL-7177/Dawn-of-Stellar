"""
상태 인코더 - 전투 상태를 RL 관측 벡터로 변환

CombatManager의 전투 상태를 517차원 float32 numpy 배열로 인코딩합니다.
모든 값은 [0, 1] 범위로 정규화됩니다.
"""

from typing import Dict, List, Any

import numpy as np

from src.core.logger import get_logger

logger = get_logger("gym.state_encoder")


class StateEncoder:
    """
    전투 상태를 RL 관측 벡터로 인코딩

    인코딩 구조:
        - 전투원 8명 (아군 4 + 적 4): 각 64차원
          - HP/MP/BRV 비율: 3
          - ATB%, is_alive, is_broken: 3
          - 직업 원-핫 (35): 35
          - 기믹 비율: 1
          - 상태이상 멀티-핫 (20): 20
          - 버프/디버프 카운트 (정규화): 2
        - 글로벌 피처: 5
          - 턴 수 정규화, 생존 아군 수, 생존 적 수, 팀워크 게이지, 보스 여부
    총 517차원
    """

    NUM_COMBATANTS = 8       # 아군 4 + 적 4
    NUM_JOBS = 35
    NUM_STATUS_EFFECTS = 20  # 상위 20개 상태이상

    FEATURES_PER_COMBATANT = 64  # 3 + 3 + 35 + 1 + 20 + 2
    GLOBAL_FEATURES = 5

    OBSERVATION_DIM = NUM_COMBATANTS * FEATURES_PER_COMBATANT + GLOBAL_FEATURES  # 517

    # 35개 직업 인덱스 매핑
    JOB_INDEX: Dict[str, int] = {
        "warrior": 0,
        "archer": 1,
        "assassin": 2,
        "berserker": 3,
        "breaker": 4,
        "gladiator": 5,
        "monk": 6,
        "rogue": 7,
        "samurai": 8,
        "sniper": 9,
        "sword_saint": 10,
        "archmage": 11,
        "battle_mage": 12,
        "spellblade": 13,
        "necromancer": 14,
        "elementalist": 15,
        "dark_knight": 16,
        "paladin": 17,
        "dimensionist": 18,
        "dragon_knight": 19,
        "priest": 20,
        "cleric": 21,
        "druid": 22,
        "bard": 23,
        "knight": 24,
        "time_mage": 25,
        "hacker": 26,
        "shaman": 27,
        "alchemist": 28,
        "engineer": 29,
        "magician": 30,
        "philosopher": 31,
        "pirate": 32,
        "vampire": 33,
        "illusionist": 34,
    }

    # 상위 20개 상태이상 인덱스 매핑 (StatusType.value 기준)
    STATUS_INDEX: Dict[str, int] = {
        "독": 0,           # POISON
        "화상": 1,         # BURN
        "출혈": 2,         # BLEED
        "기절": 3,         # STUN
        "수면": 4,         # SLEEP
        "침묵": 5,         # SILENCE
        "실명": 6,         # BLIND
        "마비": 7,         # PARALYZE
        "빙결": 8,         # FREEZE
        "둔화": 9,         # SLOW
        "공격력증가": 10,  # BOOST_ATK
        "방어력증가": 11,  # BOOST_DEF
        "속도증가": 12,    # BOOST_SPD
        "공격력감소": 13,  # REDUCE_ATK
        "방어력감소": 14,  # REDUCE_DEF
        "속도감소": 15,    # REDUCE_SPD
        "재생": 16,        # REGENERATION
        "가속": 17,        # HASTE
        "보호막": 18,      # BARRIER
        "은신": 19,        # STEALTH
    }

    @staticmethod
    def encode(combat_manager: Any) -> np.ndarray:
        """
        CombatManager 상태를 517차원 벡터로 인코딩

        Args:
            combat_manager: CombatManager 인스턴스

        Returns:
            float32 numpy 배열 (517,), 값 범위 [0, 1]
        """
        obs = np.zeros(StateEncoder.OBSERVATION_DIM, dtype=np.float32)
        offset = 0

        allies = combat_manager.allies or []
        enemies = combat_manager.enemies or []

        # 아군 4슬롯 인코딩
        for slot in range(4):
            char = allies[slot] if slot < len(allies) else None
            vec = StateEncoder._encode_combatant(char, is_ally=True)
            obs[offset:offset + StateEncoder.FEATURES_PER_COMBATANT] = vec
            offset += StateEncoder.FEATURES_PER_COMBATANT

        # 적군 4슬롯 인코딩
        for slot in range(4):
            char = enemies[slot] if slot < len(enemies) else None
            vec = StateEncoder._encode_combatant(char, is_ally=False)
            obs[offset:offset + StateEncoder.FEATURES_PER_COMBATANT] = vec
            offset += StateEncoder.FEATURES_PER_COMBATANT

        # 글로벌 피처
        max_turns = 200.0
        turn_norm = min(combat_manager.turn_count / max_turns, 1.0)
        num_alive_allies = sum(1 for a in allies if getattr(a, "is_alive", False)) / max(len(allies), 1)
        num_alive_enemies = sum(1 for e in enemies if getattr(e, "is_alive", False)) / max(len(enemies), 1)

        # 팀워크 게이지
        teamwork_ratio = 0.0
        try:
            party = combat_manager.party
            if party:
                max_tw = getattr(party, "max_teamwork_gauge", 600)
                cur_tw = getattr(party, "teamwork_gauge", 0)
                if max_tw > 0:
                    teamwork_ratio = min(cur_tw / max_tw, 1.0)
        except AttributeError:
            pass

        # 보스 여부
        is_boss = float(any(getattr(e, "is_boss", False) for e in enemies))

        obs[offset] = float(turn_norm)
        obs[offset + 1] = float(num_alive_allies)
        obs[offset + 2] = float(num_alive_enemies)
        obs[offset + 3] = float(teamwork_ratio)
        obs[offset + 4] = float(is_boss)

        return obs

    @staticmethod
    def _encode_combatant(char: Any, is_ally: bool) -> np.ndarray:
        """
        단일 전투원 인코딩 (64차원)

        빈 슬롯(char=None)이면 모두 0인 벡터 반환.

        구조:
            [0]   HP 비율
            [1]   MP 비율
            [2]   BRV 비율
            [3]   ATB 퍼센트
            [4]   is_alive (0/1)
            [5]   is_broken (0/1)
            [6:41]  직업 원-핫 (35)
            [41]  기믹 비율
            [42:62] 상태이상 멀티-핫 (20)
            [62]  버프 카운트 (정규화)
            [63]  디버프 카운트 (정규화)
        """
        vec = np.zeros(StateEncoder.FEATURES_PER_COMBATANT, dtype=np.float32)

        if char is None:
            return vec

        # HP/MP/BRV 비율
        max_hp = max(getattr(char, "max_hp", 1), 1)
        max_mp = max(getattr(char, "max_mp", 1), 1)
        max_brv = max(getattr(char, "max_brv", 1), 1)

        vec[0] = float(min(getattr(char, "current_hp", 0) / max_hp, 1.0))
        vec[1] = float(min(getattr(char, "current_mp", 0) / max_mp, 1.0))
        vec[2] = float(min(getattr(char, "current_brv", 0) / max_brv, 1.0))

        # ATB 퍼센트
        try:
            from src.combat.atb_system import get_atb_system
            atb = get_atb_system()
            gauge = atb.get_gauge(char)
            if gauge:
                vec[3] = float(min(gauge.percentage, 1.0))
        except Exception:
            vec[3] = float(min(getattr(char, "atb_gauge", 0) / 2000.0, 1.0))

        # is_alive, is_broken
        is_alive = float(getattr(char, "is_alive", False))
        vec[4] = is_alive

        current_brv = getattr(char, "current_brv", 0)
        is_broken = 1.0 if (is_alive and current_brv <= 0) else 0.0
        vec[5] = is_broken

        # 직업 원-핫 인코딩 (인덱스 6~40)
        job_id = getattr(char, "character_class", None) or getattr(char, "job_id", None) or ""
        job_idx = StateEncoder.JOB_INDEX.get(job_id, -1)
        if 0 <= job_idx < StateEncoder.NUM_JOBS:
            vec[6 + job_idx] = 1.0

        # 기믹 비율 (인덱스 41)
        gimmick_ratio = StateEncoder._get_gimmick_ratio(char)
        vec[41] = float(gimmick_ratio)

        # 상태이상 멀티-핫 (인덱스 42~61)
        status_effects = getattr(char, "status_effects", []) or []
        buff_count = 0
        debuff_count = 0

        # 버프 타입 상태이상 목록
        buff_statuses = {
            "공격력증가", "방어력증가", "속도증가", "명중률증가", "치명타증가",
            "물리보호막", "마법보호막", "축복", "재생", "MP재생", "회피증가",
            "반사", "가속", "집중", "흡혈", "광폭화완화", "방어자세",
            "지혜", "마나재생", "무한마나", "보호막", "마법보호막",
            "마나실드", "신성보호막", "원소장막", "은신",
        }

        for se in status_effects:
            status_val = None
            # StatusEffect 객체 또는 딕셔너리 처리
            if hasattr(se, "status_type"):
                st = se.status_type
                if hasattr(st, "value"):
                    status_val = st.value
                else:
                    status_val = str(st)
            elif isinstance(se, dict):
                status_val = se.get("type", "")

            if status_val:
                se_idx = StateEncoder.STATUS_INDEX.get(status_val, -1)
                if se_idx >= 0:
                    vec[42 + se_idx] = 1.0
                if status_val in buff_statuses:
                    buff_count += 1
                else:
                    debuff_count += 1

        # 버프/디버프 카운트 (최대 10으로 정규화)
        vec[62] = float(min(buff_count / 10.0, 1.0))
        vec[63] = float(min(debuff_count / 10.0, 1.0))

        return vec

    @staticmethod
    def _get_gimmick_ratio(char: Any) -> float:
        """
        캐릭터 기믹 게이지를 [0, 1]로 정규화하여 반환

        각 직업의 기믹 타입에 맞게 게이지 값을 추출합니다.
        """
        gimmick_type = getattr(char, "gimmick_type", None)
        if not gimmick_type:
            return 0.0

        try:
            if gimmick_type == "stance_system":
                stances = ["balanced", "aggressive", "defensive", "counter",
                           "berserk", "focus"]
                stance = getattr(char, "current_stance", "balanced")
                idx = stances.index(stance) if stance in stances else 0
                return idx / max(len(stances) - 1, 1)

            elif gimmick_type == "elemental_counter":
                total = (getattr(char, "fire_element", 0)
                         + getattr(char, "ice_element", 0)
                         + getattr(char, "lightning_element", 0))
                return min(total / 15.0, 1.0)

            elif gimmick_type == "magazine_system":
                max_mag = max(getattr(char, "max_magazine", 6), 1)
                cur_mag = getattr(char, "current_magazine", max_mag)
                return cur_mag / max_mag

            elif gimmick_type == "aim_system":
                return min(getattr(char, "aim_points", 0) / 5.0, 1.0)

            elif gimmick_type == "rage_system":
                return min(getattr(char, "rage_stacks", 0) / 10.0, 1.0)

            elif gimmick_type == "sword_aura":
                return min(getattr(char, "sword_aura", 0) / 10.0, 1.0)

            elif gimmick_type == "venom_system":
                return min(getattr(char, "venom_power", 0) / 10.0, 1.0)

            elif gimmick_type == "shadow_system":
                return min(getattr(char, "shadow_count", 0) / 5.0, 1.0)

            elif gimmick_type == "melody_system":
                return min(getattr(char, "melody_stacks", 0) / 5.0, 1.0)

            elif gimmick_type == "timeline_system":
                # -5 ~ +5 범위를 0~1로 정규화
                val = getattr(char, "timeline", 0)
                return (val + 5) / 10.0

            elif gimmick_type == "dragon_marks":
                return min(getattr(char, "dragon_marks", 0) / 5.0, 1.0)

            elif gimmick_type == "mp_overload_system":
                return min(getattr(char, "overload_gauge", 0) / 100.0, 1.0)

            elif gimmick_type == "rune_resonance":
                return min(getattr(char, "resonance_gauge", 0) / 100.0, 1.0)

            elif gimmick_type == "intrusion_system":
                # 해커: 침투 게이지 (대상당 0~100)
                return 0.0  # 단일 수치로 표현 어려움

        except Exception:
            pass

        return 0.0
