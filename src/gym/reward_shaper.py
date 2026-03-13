"""
보상 함수 - RL 학습을 위한 보상 계산

모든 피해/회복 보상은 대상의 max_hp/max_brv/max_mp 대비 비율로 계산되어
레벨이나 스탯 스케일링에 무관하게 일관된 보상 신호를 제공합니다.

상태 효과(버프/디버프/DoT/CC) 변화도 추적하여 전략적 행동을 보상합니다.
"""

from typing import Dict, Any, Set

from src.core.logger import get_logger

logger = get_logger("gym.reward_shaper")

# ── StatusType 카테고리 분류 (문자열 기반, import 없이 가볍게) ──
# status_effects.py의 StatusType.value 문자열과 매칭

_BUFF_VALUES: Set[str] = {
    "공격력증가", "방어력증가", "속도증가", "명중률증가", "치명타증가",
    "행운증가", "회피율증가", "모든능력치증가", "마법공격증가", "마법방어증가",
    "축복", "재생", "MP재생", "무적", "반사", "가속", "집중", "분노",
    "영감", "수호", "강화", "회피증가", "예지", "깨달음", "지혜",
    "마나재생", "무한마나", "성스러운축복", "오버클럭",
    # 보호막
    "보호막", "마법보호막", "마나실드", "화염방패", "빙결방패",
    "성스러운방패", "그림자방패",
}

_DEBUFF_VALUES: Set[str] = {
    # 순수 디버프
    "공격력감소", "방어력감소", "속도감소", "명중률감소", "회피율감소",
    "전능력감소", "마법공격감소", "마법방어감소", "취약", "노출",
    "허약", "약화", "혼란", "공포", "두려움", "절망", "MP소모",
    "냉기", "감전", "자연저주", "방어파쇄", "상처",
    # DoT (지속 피해)
    "독", "화상", "출혈", "부식", "질병", "괴사", "작열",
    # CC (군중 제어)
    "기절", "수면", "침묵", "실명", "마비", "빙결", "석화",
    "매혹", "지배", "속박", "둔화", "속박술", "광기", "도발",
    "동결", "자세무너짐",
}


class RewardShaper:
    """
    보상 함수 (비율 기반 — 레벨 무관)

    모든 수치 보상은 대상 max_hp/max_brv/max_mp 대비 비율로 정규화됩니다.
    버프/디버프 변화도 상태 비교로 추적합니다.

    보상 구성:
        게임 결과:
            - 승리: +10.0
            - 패배: -10.0
            - 적 처치: +2.0 (처치당)
            - 아군 사망: -2.0 (사망당)
        피해/회복 (비율 기반):
            - HP 피해: damage/target_max_hp * 2.0
            - BRV 피해: damage/target_max_brv * 1.0
            - 아군 HP 손실: loss/ally_max_hp * -0.5
            - 아군 HP 회복: healed/ally_max_hp * 0.8
            - BRV 축적: gained/self_max_brv * 0.3
        MP (비율 기반):
            - 아군 MP 회복: recovered/max_mp * 0.4
        상태 효과:
            - 아군 새 버프: +0.4 (버프당)
            - 적 새 디버프/DoT/CC: +0.5 (디버프당)
            - 아군 새 디버프 피격: -0.3 (디버프당)
        전투 이벤트:
            - 브레이크 유발: +2.0
            - 스킬 사용: +0.3
        패널티:
            - 유효하지 않은 행동: -0.5
            - 매 스텝: -0.01
    """

    # === 게임 결과 (고정) ===
    VICTORY = 10.0
    DEFEAT = -10.0
    ENEMY_KILL = 2.0
    ALLY_DEATH = -2.0

    # === 전투 이벤트 (고정) ===
    BREAK_CAUSED = 2.0
    SKILL_USE_BONUS = 0.3

    # === 피해/회복 비율 보상 (대상 max 대비 %) ===
    HP_DAMAGE_PCT = 2.0         # 적 max_hp 100% 피해 시 +2.0
    BRV_DAMAGE_PCT = 1.0        # 적 max_brv 100% 피해 시 +1.0
    ALLY_HP_LOSS_PCT = -0.5     # 아군 max_hp 100% 손실 시 -0.5
    ALLY_HEAL_PCT = 0.8         # 아군 max_hp 100% 회복 시 +0.8
    BRV_GAIN_PCT = 0.3          # 자신 max_brv 100% 축적 시 +0.3

    # === MP 비율 보상 ===
    ALLY_MP_RECOVERY_PCT = 0.4  # 아군 max_mp 100% 회복 시 +0.4

    # === 상태 효과 보상 (개수 기반, 고정) ===
    ALLY_BUFF_GAINED = 0.4      # 아군에게 새 버프 1개당 +0.4
    ENEMY_DEBUFF_APPLIED = 0.5  # 적에게 새 디버프/DoT/CC 1개당 +0.5
    ALLY_DEBUFF_RECEIVED = -0.3 # 아군이 새 디버프 1개 받을 때 -0.3

    # === 패널티 ===
    INVALID_ACTION = -0.5
    STEP_PENALTY = -0.01

    @staticmethod
    def calculate(
        prev_state: Dict,
        new_state: Dict,
        action_result: Dict,
        done: bool,
        result: str = "in_progress",
        invalid_action: bool = False,
    ) -> float:
        """
        보상 계산

        Args:
            prev_state: 행동 전 상태 스냅샷 (snapshot() 결과)
            new_state: 행동 후 상태 스냅샷
            action_result: execute_action() 반환값
            done: 에피소드 종료 여부
            result: 전투 결과 ('victory', 'defeat', 'in_progress', 'fled')
            invalid_action: 유효하지 않은 행동 여부

        Returns:
            float 보상값
        """
        reward = 0.0

        # 유효하지 않은 행동 패널티
        if invalid_action:
            return RewardShaper.INVALID_ACTION

        # 매 스텝 패널티
        reward += RewardShaper.STEP_PENALTY

        # ========== 행동 결과 보상 (비율 기반) ==========
        if action_result:
            alive_enemies = [e for e in new_state.get("enemies", [])
                            if e.get("is_alive", True)]
            avg_enemy_max_hp = (
                sum(e.get("max_hp", 1) for e in alive_enemies) / len(alive_enemies)
                if alive_enemies else 500
            )
            avg_enemy_max_brv = (
                sum(e.get("max_brv", 1) for e in alive_enemies) / len(alive_enemies)
                if alive_enemies else 1000
            )
            avg_enemy_max_hp = max(1.0, avg_enemy_max_hp)
            avg_enemy_max_brv = max(1.0, avg_enemy_max_brv)

            # 적에게 가한 HP 피해 (비율 기반)
            hp_damage = float(action_result.get("hp_damage", 0) or 0)
            reward += hp_damage / avg_enemy_max_hp * RewardShaper.HP_DAMAGE_PCT

            # 적에게 가한 BRV 피해 (비율 기반)
            brv_damage = float(action_result.get("brv_damage", 0) or 0)
            if not brv_damage:
                brv_result = action_result.get("brv_result", {})
                if isinstance(brv_result, dict):
                    brv_damage = float(brv_result.get("damage", 0) or 0)
            reward += brv_damage / avg_enemy_max_brv * RewardShaper.BRV_DAMAGE_PCT

            # 브레이크 유발
            if (action_result.get("is_break", False) or
                    action_result.get("brv_result", {}).get("is_break", False)):
                reward += RewardShaper.BREAK_CAUSED

            # 스킬 사용 보너스
            action_type = action_result.get("action_type", "")
            if action_type == "skill":
                reward += RewardShaper.SKILL_USE_BONUS

        # ========== 상태 변화 보상 (prev vs new 비교) ==========

        # --- 아군 HP 변화 (피해 패널티 + 회복 보상) ---
        prev_allies = {a["name"]: a for a in prev_state.get("allies", [])}
        new_allies = {a["name"]: a for a in new_state.get("allies", [])}

        for name, prev_a in prev_allies.items():
            new_a = new_allies.get(name)
            if new_a is None:
                continue

            max_hp = max(1.0, float(new_a.get("max_hp", 1)))
            prev_hp = float(prev_a.get("current_hp", 0))
            new_hp = float(new_a.get("current_hp", 0))
            hp_delta = new_hp - prev_hp

            if hp_delta < 0:
                # 아군 HP 감소 → 패널티 (비율 기반)
                reward += abs(hp_delta) / max_hp * RewardShaper.ALLY_HP_LOSS_PCT
            elif hp_delta > 0:
                # 아군 HP 회복 → 보상 (비율 기반)
                reward += hp_delta / max_hp * RewardShaper.ALLY_HEAL_PCT

            # 아군 사망 감지
            if prev_a.get("is_alive", True) and not new_a.get("is_alive", False):
                reward += RewardShaper.ALLY_DEATH
                logger.debug(f"아군 사망 패널티: {name} {RewardShaper.ALLY_DEATH}")

        # --- 아군 BRV 축적 보상 ---
        for name, prev_a in prev_allies.items():
            new_a = new_allies.get(name)
            if new_a is None:
                continue
            max_brv = max(1.0, float(new_a.get("max_brv", 1)))
            brv_delta = float(new_a.get("current_brv", 0)) - float(prev_a.get("current_brv", 0))
            if brv_delta > 0:
                reward += brv_delta / max_brv * RewardShaper.BRV_GAIN_PCT

        # --- 아군 MP 회복 보상 (비율 기반) ---
        for name, prev_a in prev_allies.items():
            new_a = new_allies.get(name)
            if new_a is None:
                continue
            max_mp = max(1.0, float(new_a.get("max_mp", 1)))
            mp_delta = float(new_a.get("current_mp", 0)) - float(prev_a.get("current_mp", 0))
            if mp_delta > 0:
                reward += mp_delta / max_mp * RewardShaper.ALLY_MP_RECOVERY_PCT

        # --- 아군 버프 획득 보상 ---
        for name, prev_a in prev_allies.items():
            new_a = new_allies.get(name)
            if new_a is None:
                continue
            prev_buffs = prev_a.get("buff_count", 0)
            new_buffs = new_a.get("buff_count", 0)
            buff_delta = new_buffs - prev_buffs
            if buff_delta > 0:
                reward += buff_delta * RewardShaper.ALLY_BUFF_GAINED

            # 아군이 디버프를 새로 받으면 패널티
            prev_debuffs = prev_a.get("debuff_count", 0)
            new_debuffs = new_a.get("debuff_count", 0)
            debuff_delta = new_debuffs - prev_debuffs
            if debuff_delta > 0:
                reward += debuff_delta * RewardShaper.ALLY_DEBUFF_RECEIVED

        # --- 적에게 디버프/DoT/CC 부여 보상 ---
        prev_enemies = {e["name"]: e for e in prev_state.get("enemies", [])}
        new_enemies = {e["name"]: e for e in new_state.get("enemies", [])}

        for name, prev_e in prev_enemies.items():
            new_e = new_enemies.get(name)
            if new_e is None:
                continue
            prev_debuffs = prev_e.get("debuff_count", 0)
            new_debuffs = new_e.get("debuff_count", 0)
            debuff_delta = new_debuffs - prev_debuffs
            if debuff_delta > 0:
                reward += debuff_delta * RewardShaper.ENEMY_DEBUFF_APPLIED

        # --- 적 처치 감지 ---
        for name, prev_e in prev_enemies.items():
            new_e = new_enemies.get(name)
            if new_e is None:
                continue
            if prev_e.get("is_alive", True) and not new_e.get("is_alive", True):
                reward += RewardShaper.ENEMY_KILL
                logger.debug(f"적 처치 보상: {name} +{RewardShaper.ENEMY_KILL}")

        # ========== 종료 보상 ==========
        if done:
            if result == "victory":
                reward += RewardShaper.VICTORY
            elif result in ("defeat", "fled"):
                reward += RewardShaper.DEFEAT

        return float(reward)

    @staticmethod
    def get_efficiency_bonus(turn_count: int, max_turns: int = 200) -> float:
        """
        승리 시 효율 보너스 계산 (빠를수록 높음)

        Args:
            turn_count: 소요 턴 수
            max_turns: 최대 허용 턴 수

        Returns:
            0.0 ~ 5.0 범위의 효율 보너스
        """
        if turn_count <= 0:
            return 5.0
        ratio = max(0.0, 1.0 - turn_count / max_turns)
        return float(ratio * 5.0)

    @staticmethod
    def _count_status_effects(character: Any) -> tuple:
        """캐릭터의 버프/디버프 개수를 반환합니다.

        Returns:
            (buff_count, debuff_count) 튜플
        """
        buff_count = 0
        debuff_count = 0
        sm = getattr(character, "status_manager", None)
        if sm is None:
            return 0, 0
        for effect in getattr(sm, "status_effects", []):
            st = getattr(effect, "status_type", None)
            value = getattr(st, "value", "") if st else ""
            if value in _BUFF_VALUES:
                buff_count += 1
            elif value in _DEBUFF_VALUES:
                debuff_count += 1
        return buff_count, debuff_count

    @staticmethod
    def snapshot(combat_manager: Any) -> Dict:
        """
        보상 계산용 상태 스냅샷 생성

        HP, BRV, MP, 버프/디버프 카운트를 포함하여
        비율 기반 보상 및 상태 효과 변화 추적을 지원합니다.

        Args:
            combat_manager: CombatManager 인스턴스

        Returns:
            allies/enemies의 HP, BRV, MP, max값, 버프/디버프 수, alive 상태
        """
        allies = []
        for a in (combat_manager.allies or []):
            buff_c, debuff_c = RewardShaper._count_status_effects(a)
            allies.append({
                "name": getattr(a, "name", "?"),
                "current_hp": getattr(a, "current_hp", 0),
                "max_hp": getattr(a, "max_hp", 1),
                "current_brv": getattr(a, "current_brv", 0),
                "max_brv": getattr(a, "max_brv", 1),
                "current_mp": getattr(a, "current_mp", 0),
                "max_mp": getattr(a, "max_mp", 1),
                "buff_count": buff_c,
                "debuff_count": debuff_c,
                "is_alive": getattr(a, "is_alive", False),
            })

        enemies = []
        for e in (combat_manager.enemies or []):
            buff_c, debuff_c = RewardShaper._count_status_effects(e)
            enemies.append({
                "name": getattr(e, "name", "?"),
                "current_hp": getattr(e, "current_hp", 0),
                "max_hp": getattr(e, "max_hp", 1),
                "current_brv": getattr(e, "current_brv", 0),
                "max_brv": getattr(e, "max_brv", 1),
                "buff_count": buff_c,
                "debuff_count": debuff_c,
                "is_alive": getattr(e, "is_alive", True),
            })

        return {"allies": allies, "enemies": enemies}
