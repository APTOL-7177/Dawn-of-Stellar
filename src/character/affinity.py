"""
호감도/유대 시스템 (Affinity/Bond System)

캐릭터 간 호감도를 관리하고, 호감도 레벨에 따라
연계스킬(자동/무료)과 체인어빌리티(선택/불릿타임/게이지소모)를 발동합니다.

- 연계스킬: 일정 확률로 자동 발동, 대가 없음, 플레이어 선택 없음
- 체인어빌리티: 발동 조건 충족 시 불릿타임 중 사용 결정 가능, 팀워크 게이지 소모
- 발동 확률은 호감도 레벨에 따라 차등 적용 (레벨이 높을수록 확률 증가)
- 연계스킬과 체인어빌리티는 직업별로 고유
"""

import random
from enum import IntEnum
from typing import Dict, Any, Optional, List, Tuple
from src.core.logger import get_logger
from src.core.event_bus import event_bus, Events

logger = get_logger("affinity")


# ─── 호감도 레벨 ──────────────────────────────────────────────

class AffinityLevel(IntEnum):
    """호감도 레벨 (6단계)"""
    STRANGER = 0       # 모르는 사이 (0~49)
    COMRADE = 1        # 동료 (50~149)
    TRUST = 2          # 신뢰 (150~299) → 연계스킬 1 해금
    INTIMATE = 3       # 친밀 (300~499) → 연계스킬 2 해금, 합체기 해금
    DEEP_BOND = 4      # 깊은 유대 (500~749) → 체인어빌리티 해금
    SOUL_PARTNER = 5   # 영혼의 동반자 (750+) → 궁극 체인어빌리티

    @staticmethod
    def from_points(points: int) -> 'AffinityLevel':
        """포인트로부터 레벨 계산"""
        if points >= 750:
            return AffinityLevel.SOUL_PARTNER
        elif points >= 500:
            return AffinityLevel.DEEP_BOND
        elif points >= 300:
            return AffinityLevel.INTIMATE
        elif points >= 150:
            return AffinityLevel.TRUST
        elif points >= 50:
            return AffinityLevel.COMRADE
        return AffinityLevel.STRANGER

    @property
    def display_name(self) -> str:
        names = {
            0: "모르는 사이",
            1: "동료",
            2: "신뢰",
            3: "친밀",
            4: "깊은 유대",
            5: "영혼의 동반자"
        }
        return names.get(self.value, "???")

    @property
    def gauge_charge_bonus(self) -> float:
        """호감도 레벨에 따른 팀워크 게이지 충전 보너스"""
        bonuses = {
            0: 0.0,
            1: 0.05,
            2: 0.10,
            3: 0.15,
            4: 0.20,
            5: 0.25
        }
        return bonuses.get(self.value, 0.0)

    @property
    def next_level_points(self) -> Optional[int]:
        """다음 레벨까지 필요한 포인트 총량"""
        thresholds = {0: 50, 1: 150, 2: 300, 3: 500, 4: 750}
        return thresholds.get(self.value)


# ─── 호감도 쌍 ────────────────────────────────────────────────

class AffinityPair:
    """두 캐릭터 간 호감도 데이터"""

    def __init__(self, job_a: str, job_b: str, points: int = 0):
        # 항상 알파벳 순으로 정렬하여 일관된 키 생성
        self.job_a, self.job_b = sorted([job_a, job_b])
        self.points = max(0, points)

    @property
    def key(self) -> str:
        return f"{self.job_a}:{self.job_b}"

    @property
    def level(self) -> AffinityLevel:
        return AffinityLevel.from_points(self.points)

    def add_points(self, amount: int) -> Tuple[int, bool]:
        """포인트 추가. (새 포인트, 레벨업 여부) 반환"""
        old_level = self.level
        self.points = max(0, self.points + amount)
        new_level = self.level
        level_up = new_level > old_level
        return self.points, level_up

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_a": self.job_a,
            "job_b": self.job_b,
            "points": self.points
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AffinityPair':
        return cls(data["job_a"], data["job_b"], data.get("points", 0))


# ─── 연계스킬 / 체인어빌리티 데이터 ──────────────────────────

class BondSkill:
    """연계스킬: 자동 발동, 무료, 플레이어 선택 없음"""

    def __init__(self, data: Dict[str, Any]):
        self.id: str = data["id"]
        self.name: str = data["name"]
        self.job_id: str = data["job_id"]
        self.skill_type: str = "bond_skill"
        self.required_affinity_level: int = data.get("required_affinity_level", 2)
        self.trigger: str = data["trigger"]
        # 호감도 레벨별 발동 확률 (핵심!)
        self.trigger_chance_by_level: Dict[int, float] = data.get("trigger_chance_by_level", {})
        self.effect: Dict[str, Any] = data.get("effect", {})
        self.description: str = data.get("description", "")
        self.animation: str = data.get("animation", "default")

    def get_trigger_chance(self, affinity_level: int) -> float:
        """호감도 레벨에 따른 발동 확률 반환"""
        if affinity_level < self.required_affinity_level:
            return 0.0
        # 정확한 레벨 매핑이 있으면 사용, 없으면 가장 가까운 낮은 레벨 사용
        if affinity_level in self.trigger_chance_by_level:
            return self.trigger_chance_by_level[affinity_level]
        # 해당 레벨 이하의 가장 높은 확률 반환
        available = [v for k, v in self.trigger_chance_by_level.items() if k <= affinity_level]
        return max(available) if available else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "job_id": self.job_id,
            "type": self.skill_type,
            "required_affinity_level": self.required_affinity_level,
            "trigger": self.trigger,
            "trigger_chance_by_level": self.trigger_chance_by_level,
            "effect": self.effect, "description": self.description
        }


class ChainAbility:
    """체인어빌리티: 불릿타임 중 선택, 팀워크 게이지 소모"""

    def __init__(self, data: Dict[str, Any]):
        self.id: str = data["id"]
        self.name: str = data["name"]
        self.job_id: str = data["job_id"]
        self.skill_type: str = "chain_ability"
        self.required_affinity_level: int = data.get("required_affinity_level", 4)
        self.trigger: str = data["trigger"]
        # 호감도 레벨별 발동 확률
        self.trigger_chance_by_level: Dict[int, float] = data.get("trigger_chance_by_level", {})
        self.gauge_cost: int = data.get("gauge_cost", 50)
        self.effect: Dict[str, Any] = data.get("effect", {})
        self.description: str = data.get("description", "")
        self.animation: str = data.get("animation", "default")
        self.bullet_time: bool = True  # 항상 불릿타임
        # 파트너 직업 제한: 이 체인어빌리티를 트리거할 수 있는 actor 직업 목록
        # 비어있으면 제한 없음 (any job with sufficient affinity)
        self.partner_jobs: List[str] = data.get("partner_jobs", [])

    def get_trigger_chance(self, affinity_level: int) -> float:
        """호감도 레벨에 따른 발동 확률 반환"""
        if affinity_level < self.required_affinity_level:
            return 0.0
        if affinity_level in self.trigger_chance_by_level:
            return self.trigger_chance_by_level[affinity_level]
        available = [v for k, v in self.trigger_chance_by_level.items() if k <= affinity_level]
        return max(available) if available else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "job_id": self.job_id,
            "type": self.skill_type,
            "required_affinity_level": self.required_affinity_level,
            "trigger": self.trigger,
            "trigger_chance_by_level": self.trigger_chance_by_level,
            "gauge_cost": self.gauge_cost,
            "effect": self.effect, "description": self.description,
            "bullet_time": True
        }


# ─── 발동 결과 ────────────────────────────────────────────────

class BondSkillResult:
    """연계스킬 발동 결과 (자동 적용)"""
    def __init__(self, skill: BondSkill, source_job: str, ally_job: str):
        self.skill = skill
        self.source_job = source_job
        self.ally_job = ally_job

    def __repr__(self):
        return f"BondSkillResult({self.skill.name}: {self.source_job} → {self.ally_job})"


class ChainAbilityResult:
    """체인어빌리티 발동 가능 결과 (플레이어 선택 대기)"""
    def __init__(self, ability: ChainAbility, source_job: str, ally_job: str, cooldown_remaining: int = 0):
        self.ability = ability
        self.source_job = source_job
        self.ally_job = ally_job
        self.gauge_cost = ability.gauge_cost
        self.cooldown_remaining = cooldown_remaining  # 0이면 사용 가능

    def __repr__(self):
        return f"ChainAbilityResult({self.ability.name}: {self.source_job} → {self.ally_job}, cost={self.gauge_cost})"


# ─── 트리거 이벤트 타입 ───────────────────────────────────────

class BondTrigger:
    """연계스킬/체인어빌리티 발동 조건 타입"""
    ALLY_ATTACK_HIT = "ally_attack_hit"         # 아군 공격 적중 시
    ALLY_SKILL_HIT = "ally_skill_hit"           # 아군 스킬 적중 시
    ALLY_DAMAGED = "ally_damaged"               # 아군이 피해를 받았을 때
    ALLY_LETHAL_HIT = "ally_lethal_hit"         # 아군이 치명적 피해를 받았을 때
    ALLY_KILLED = "ally_killed"                 # 아군이 전투불능이 되었을 때
    ALLY_HEALED = "ally_healed"                 # 아군이 회복을 받았을 때
    ALLY_BUFFED = "ally_buffed"                 # 아군이 버프를 받았을 때
    ENEMY_KILLED = "enemy_killed"               # 적을 처치했을 때
    ENEMY_BREAK = "enemy_break"                 # 적 브레이크 시
    BOTH_LOW_HP = "both_low_hp"                 # 양쪽 HP 50% 이하
    BATTLE_START = "battle_start"               # 전투 시작 시
    CRITICAL_HIT = "critical_hit"               # 크리티컬 적중 시
    COUNTER_ATTACK = "counter_attack"           # 반격 시
    DEFEND_ACTION = "defend_action"             # 방어 행동 시
    TEAMWORK_SKILL_USED = "teamwork_skill_used" # 팀워크 스킬 사용 시


# ─── 스킬 데이터 로더 ─────────────────────────────────────────

class BondSkillRegistry:
    """YAML에서 로드된 연계스킬/체인어빌리티 레지스트리"""

    _instance = None
    _loaded = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not BondSkillRegistry._loaded:
            self._bond_skills: Dict[str, List[BondSkill]] = {}  # job_id -> [BondSkill]
            self._chain_abilities: Dict[str, List[ChainAbility]] = {}  # job_id -> [ChainAbility]
            self._load_data()
            BondSkillRegistry._loaded = True

    def _load_data(self):
        """YAML 파일에서 연계스킬/체인어빌리티 데이터 로드"""
        import yaml
        from src.core.paths import get_project_root

        data_path = str(get_project_root() / "data" / "bond_skills.yaml")

        import os
        if not os.path.exists(data_path):
            logger.warning(f"bond_skills.yaml 파일을 찾을 수 없습니다: {data_path}")
            return

        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"bond_skills.yaml 로드 실패: {e}")
            return

        # 연계스킬 로드
        for skill_data in data.get("bond_skills", []):
            job_id = skill_data.get("job_id", "")
            # trigger_chance_by_level의 키를 int로 변환
            if "trigger_chance_by_level" in skill_data:
                skill_data["trigger_chance_by_level"] = {
                    int(k): float(v) for k, v in skill_data["trigger_chance_by_level"].items()
                }
            skill = BondSkill(skill_data)
            if job_id not in self._bond_skills:
                self._bond_skills[job_id] = []
            self._bond_skills[job_id].append(skill)

        # 체인어빌리티 로드
        for ability_data in data.get("chain_abilities", []):
            job_id = ability_data.get("job_id", "")
            if "trigger_chance_by_level" in ability_data:
                ability_data["trigger_chance_by_level"] = {
                    int(k): float(v) for k, v in ability_data["trigger_chance_by_level"].items()
                }
            ability = ChainAbility(ability_data)
            if job_id not in self._chain_abilities:
                self._chain_abilities[job_id] = []
            self._chain_abilities[job_id].append(ability)

        # 합체기(combo_skills) 기반 파트너 직업 매핑 자동 구축
        self._combo_partners: Dict[str, set] = {}
        synergy_path = str(get_project_root() / "data" / "job_synergy.yaml")
        if os.path.exists(synergy_path):
            try:
                with open(synergy_path, 'r', encoding='utf-8') as f:
                    synergy_data = yaml.safe_load(f) or {}
                for combo in synergy_data.get("combo_skills", []):
                    jobs = combo.get("required_jobs", [])
                    if len(jobs) >= 2:
                        for i, job in enumerate(jobs):
                            if job not in self._combo_partners:
                                self._combo_partners[job] = set()
                            for j, other in enumerate(jobs):
                                if i != j:
                                    self._combo_partners[job].add(other)
            except Exception as e:
                logger.warning(f"job_synergy.yaml 파트너 매핑 로드 실패: {e}")

        # 체인어빌리티에 파트너 직업 자동 설정 (YAML에 명시하지 않은 경우)
        for job_id, abilities in self._chain_abilities.items():
            for ability in abilities:
                if not ability.partner_jobs and job_id in self._combo_partners:
                    ability.partner_jobs = list(self._combo_partners[job_id])

        total_bonds = sum(len(v) for v in self._bond_skills.values())
        total_chains = sum(len(v) for v in self._chain_abilities.values())
        partner_count = sum(1 for a_list in self._chain_abilities.values()
                           for a in a_list if a.partner_jobs)
        logger.info(
            f"연계스킬 {total_bonds}개, 체인어빌리티 {total_chains}개 로드 완료 "
            f"(파트너 제한 {partner_count}개)"
        )

    def get_bond_skills(self, job_id: str) -> List[BondSkill]:
        """직업의 연계스킬 목록 반환"""
        return self._bond_skills.get(job_id, [])

    def get_chain_abilities(self, job_id: str) -> List[ChainAbility]:
        """직업의 체인어빌리티 목록 반환"""
        return self._chain_abilities.get(job_id, [])

    def get_all_bond_skills(self) -> Dict[str, List[BondSkill]]:
        return dict(self._bond_skills)

    def get_all_chain_abilities(self) -> Dict[str, List[ChainAbility]]:
        return dict(self._chain_abilities)

    @classmethod
    def reload(cls):
        """데이터 리로드 (핫 리로드용)"""
        cls._loaded = False
        cls._instance = None


# ─── 호감도 매니저 ────────────────────────────────────────────

class AffinityManager:
    """
    호감도 관리자

    캐릭터 쌍별 호감도 포인트/레벨을 관리하고,
    연계스킬 및 체인어빌리티 발동을 판정합니다.
    """

    def __init__(self):
        self._pairs: Dict[str, AffinityPair] = {}
        self._registry = BondSkillRegistry()
        # 발동 쿨다운 (같은 스킬이 연속 발동되지 않도록)
        self._cooldowns: Dict[str, int] = {}  # skill_id -> remaining_turns

    def _make_key(self, job_a: str, job_b: str) -> str:
        """정렬된 쌍 키 생성"""
        a, b = sorted([job_a, job_b])
        return f"{a}:{b}"

    def _get_or_create_pair(self, job_a: str, job_b: str) -> AffinityPair:
        """쌍 가져오기 (없으면 생성)"""
        key = self._make_key(job_a, job_b)
        if key not in self._pairs:
            self._pairs[key] = AffinityPair(job_a, job_b)
        return self._pairs[key]

    # ─── 호감도 포인트 관리 ────────────

    def add_points(self, job_a: str, job_b: str, amount: int) -> Tuple[int, bool]:
        """호감도 포인트 추가. (새 포인트, 레벨업 여부) 반환"""
        if job_a == job_b:
            return 0, False
        pair = self._get_or_create_pair(job_a, job_b)
        new_points, level_up = pair.add_points(amount)

        if level_up:
            logger.info(f"호감도 레벨업! {job_a} ↔ {job_b}: Lv{pair.level.value} ({pair.level.display_name})")

        # 포인트 변경 시 항상 이벤트 발행 (UI 갱신용)
        event_bus.publish(Events.AFFINITY_CHANGED, {
            "job_a": job_a, "job_b": job_b,
            "points": new_points, "level": pair.level.value,
            "level_up": level_up
        })

        return new_points, level_up

    def add_points_all(self, job_ids: List[str], amount: int):
        """파티 전원 간 호감도 증가"""
        for i in range(len(job_ids)):
            for j in range(i + 1, len(job_ids)):
                self.add_points(job_ids[i], job_ids[j], amount)

    def get_points(self, job_a: str, job_b: str) -> int:
        key = self._make_key(job_a, job_b)
        pair = self._pairs.get(key)
        return pair.points if pair else 0

    def get_level(self, job_a: str, job_b: str) -> AffinityLevel:
        key = self._make_key(job_a, job_b)
        pair = self._pairs.get(key)
        return pair.level if pair else AffinityLevel.STRANGER

    def get_gauge_bonus(self, job_a: str, job_b: str) -> float:
        """두 캐릭터 간 팀워크 게이지 충전 보너스 (0.0 ~ 0.25)"""
        return self.get_level(job_a, job_b).gauge_charge_bonus

    def get_party_avg_gauge_bonus(self, job_ids: List[str]) -> float:
        """파티 전체 평균 게이지 충전 보너스"""
        if len(job_ids) < 2:
            return 0.0
        total = 0.0
        count = 0
        for i in range(len(job_ids)):
            for j in range(i + 1, len(job_ids)):
                total += self.get_gauge_bonus(job_ids[i], job_ids[j])
                count += 1
        return total / count if count > 0 else 0.0

    # ─── 쿨다운 관리 ──────────────────

    def tick_cooldowns(self):
        """턴 종료 시 쿨다운 감소"""
        expired = []
        for skill_id, remaining in self._cooldowns.items():
            self._cooldowns[skill_id] = remaining - 1
            if self._cooldowns[skill_id] <= 0:
                expired.append(skill_id)
        for sid in expired:
            del self._cooldowns[sid]

    def _is_on_cooldown(self, skill_id: str) -> bool:
        return self._cooldowns.get(skill_id, 0) > 0

    def _set_cooldown(self, skill_id: str, turns: int = 3):
        self._cooldowns[skill_id] = turns

    # ─── 연계스킬 판정 (자동, 무료) ───

    def check_bond_skills(
        self,
        trigger_event: str,
        actor_job: str,
        party_jobs: List[str],
        rng: Optional[random.Random] = None
    ) -> List[BondSkillResult]:
        """
        연계스킬 발동 체크

        actor_job이 trigger_event를 발생시켰을 때,
        파티 내 다른 캐릭터의 연계스킬이 발동되는지 확인합니다.

        Returns: 발동된 연계스킬 결과 리스트
        """
        results = []
        _rng = rng or random.Random()

        for ally_job in party_jobs:
            if ally_job == actor_job:
                continue

            affinity_level = self.get_level(actor_job, ally_job).value

            # 아군의 연계스킬 목록 확인
            bond_skills = self._registry.get_bond_skills(ally_job)
            for skill in bond_skills:
                # 트리거 이벤트 매칭
                if skill.trigger != trigger_event:
                    continue
                # 쿨다운 체크
                if self._is_on_cooldown(skill.id):
                    continue
                # 호감도 레벨별 발동 확률
                chance = skill.get_trigger_chance(affinity_level)
                if chance <= 0:
                    continue

                roll = _rng.random()
                if roll < chance:
                    results.append(BondSkillResult(skill, ally_job, actor_job))
                    self._set_cooldown(skill.id, 3)
                    logger.info(
                        f"연계스킬 발동! {skill.name} ({ally_job}) "
                        f"[호감도 Lv{affinity_level}, 확률 {chance:.0%}, 주사위 {roll:.2f}]"
                    )

        return results

    # ─── 체인어빌리티 판정 (선택, 불릿타임) ───

    def check_chain_abilities(
        self,
        actor_job: str,
        party_jobs: List[str],
        available_gauge: int,
    ) -> List[ChainAbilityResult]:
        """
        체인어빌리티 사용 가능 목록 반환 (확률 없이, 조건만 체크)

        트리거 조건(BREAK/SCATTER/팀워크/스킬)은 호출자(combat_manager)에서 이미 확인됨.
        여기서는 호감도 레벨, 게이지 잔량, 쿨다운만 체크.

        Returns: 사용 가능한 체인어빌리티 결과 리스트
        """
        results = []

        for ally_job in party_jobs:
            if ally_job == actor_job:
                continue

            affinity_level = self.get_level(actor_job, ally_job).value

            chain_abilities = self._registry.get_chain_abilities(ally_job)
            for ability in chain_abilities:
                # 파트너 직업 제한: 합체기 조합에 없는 직업은 체인어빌리티 불가
                if ability.partner_jobs and actor_job not in ability.partner_jobs:
                    continue
                if affinity_level < ability.required_affinity_level:
                    continue

                cd = self.get_cooldown(ability.id)
                if cd > 0:
                    # 쿨다운 중: 비활성 상태로 포함 (UI에서 표시용)
                    results.append(ChainAbilityResult(ability, ally_job, actor_job, cooldown_remaining=cd))
                    continue
                if available_gauge < ability.gauge_cost:
                    continue

                results.append(ChainAbilityResult(ability, ally_job, actor_job))
                logger.info(
                    f"체인어빌리티 사용 가능: {ability.name} ({ally_job}) "
                    f"[호감도 Lv{affinity_level}, 비용 {ability.gauge_cost}]"
                )

        return results

    def confirm_chain_ability(self, result: ChainAbilityResult):
        """플레이어가 체인어빌리티 사용을 확정했을 때 호출"""
        self._set_cooldown(result.ability.id, 3)
        logger.info(f"체인어빌리티 확정: {result.ability.name} (게이지 -{result.gauge_cost}, 쿨다운 3턴)")

    def get_cooldown(self, skill_id: str) -> int:
        """스킬의 남은 쿨다운 턴 수 반환 (0이면 사용 가능)"""
        return self._cooldowns.get(skill_id, 0)

    # ─── 호감도 증가 이벤트 핸들러 ────

    def on_battle_action(self, actor_job: str, party_jobs: List[str]):
        """전투 행동 시 호감도 증가 (행동당 +3)"""
        for ally_job in party_jobs:
            if ally_job != actor_job:
                self.add_points(actor_job, ally_job, 3)

    def on_battle_victory(self, party_jobs: List[str]):
        """전투 승리 시 전원 호감도 증가 (+8)"""
        self.add_points_all(party_jobs, 8)

    def on_heal_or_buff(self, caster_job: str, target_job: str):
        """힐/버프 시전 시 호감도 증가 (+5)"""
        if caster_job != target_job:
            self.add_points(caster_job, target_job, 5)

    def on_teamwork_chain(self, participant_jobs: List[str]):
        """팀워크 스킬 연쇄 시 참여자 간 호감도 증가"""
        for i in range(len(participant_jobs)):
            for j in range(i + 1, len(participant_jobs)):
                self.add_points(participant_jobs[i], participant_jobs[j], 5)

    def on_combo_skill(self, job_a: str, job_b: str):
        """합체기 사용 시 호감도 대폭 증가"""
        self.add_points(job_a, job_b, 8)

    def on_exploration_steps(self, party_jobs: List[str], steps: int):
        """탐험 이동 시 호감도 증가 (50스텝마다)"""
        if steps > 0 and steps % 50 == 0:
            self.add_points_all(party_jobs, 1)

    def on_random_event(self, party_jobs: List[str], affinity_gain: int):
        """랜덤 이벤트 해결 시 호감도 증가"""
        if affinity_gain != 0:
            self.add_points_all(party_jobs, affinity_gain)

    def on_puzzle_solved(self, solver_job: str, party_jobs: List[str]):
        """퍼즐 해결 시 호감도 증가"""
        for ally_job in party_jobs:
            if ally_job != solver_job:
                self.add_points(solver_job, ally_job, 3)

    # ─── 직렬화 ───────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pairs": {k: v.to_dict() for k, v in self._pairs.items()},
            "cooldowns": dict(self._cooldowns)
        }

    def from_dict(self, data: Dict[str, Any]):
        """데이터로부터 복원"""
        self._pairs.clear()
        self._cooldowns.clear()

        for key, pair_data in data.get("pairs", {}).items():
            pair = AffinityPair.from_dict(pair_data)
            self._pairs[pair.key] = pair

        self._cooldowns = {k: int(v) for k, v in data.get("cooldowns", {}).items()}
        logger.info(f"호감도 데이터 복원: {len(self._pairs)}쌍")

    # ─── 유틸리티 ──────────────────────

    def get_all_pairs(self) -> List[AffinityPair]:
        """모든 호감도 쌍 반환 (포인트 내림차순)"""
        return sorted(self._pairs.values(), key=lambda p: p.points, reverse=True)

    def get_pairs_for_job(self, job_id: str) -> List[Tuple[str, AffinityPair]]:
        """특정 직업의 모든 호감도 쌍 반환"""
        result = []
        for pair in self._pairs.values():
            if pair.job_a == job_id:
                result.append((pair.job_b, pair))
            elif pair.job_b == job_id:
                result.append((pair.job_a, pair))
        return sorted(result, key=lambda x: x[1].points, reverse=True)

    def get_unlocked_bond_skills(self, job_id: str, party_jobs: List[str]) -> List[Tuple[BondSkill, str, int]]:
        """해금된 연계스킬 목록: [(스킬, 대상직업, 호감도레벨)]"""
        skills = self._registry.get_bond_skills(job_id)
        result = []
        for ally_job in party_jobs:
            if ally_job == job_id:
                continue
            level = self.get_level(job_id, ally_job).value
            for skill in skills:
                if level >= skill.required_affinity_level:
                    result.append((skill, ally_job, level))
        return result

    def get_unlocked_chain_abilities(self, job_id: str, party_jobs: List[str]) -> List[Tuple[ChainAbility, str, int]]:
        """해금된 체인어빌리티 목록: [(어빌리티, 대상직업, 호감도레벨)]"""
        abilities = self._registry.get_chain_abilities(job_id)
        result = []
        for ally_job in party_jobs:
            if ally_job == job_id:
                continue
            level = self.get_level(job_id, ally_job).value
            for ability in abilities:
                # 파트너 직업 제한 체크
                if ability.partner_jobs and ally_job not in ability.partner_jobs:
                    continue
                if level >= ability.required_affinity_level:
                    result.append((ability, ally_job, level))
        return result

    def get_summary(self) -> str:
        """호감도 요약 텍스트"""
        lines = []
        for pair in self.get_all_pairs():
            lines.append(
                f"  {pair.job_a} ↔ {pair.job_b}: "
                f"Lv{pair.level.value} ({pair.level.display_name}) [{pair.points}pt]"
            )
        return "\n".join(lines) if lines else "  (호감도 데이터 없음)"
