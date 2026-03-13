"""
직업 시너지/콤보 시스템 (Job Synergy System)

합체기(2인 이상 직업 조합 필살기)와 파티 편성 보너스를 관리합니다.

- 합체기: 특정 직업 조합 + 호감도 조건 충족 시 발동 가능, 팀워크 게이지 소모
- 파티 보너스: 파티 편성 시 자동 적용되는 패시브 보너스
"""

from typing import Dict, Any, Optional, List, Tuple
from src.core.logger import get_logger
from src.core.event_bus import event_bus, Events

logger = get_logger("job_synergy")


# ─── 직업 카테고리 ────────────────────────────────────────────

JOB_CATEGORIES = {
    "physical": [
        "warrior", "knight", "rogue", "assassin", "berserker", "monk",
        "samurai", "pirate", "gladiator", "sniper", "archer", "breaker",
        "sword_saint", "dragon_knight", "ninja"
    ],
    "magic": [
        "magician", "archmage", "elementalist", "necromancer", "time_mage",
        "dimensionist", "illusionist", "battle_mage", "spellblade", "shaman"
    ],
    "support": [
        "cleric", "priest", "bard", "druid", "paladin", "alchemist", "philosopher"
    ],
    "tech": [
        "engineer", "hacker"
    ],
    "dark": [
        "dark_knight", "vampire", "necromancer", "assassin"
    ]
}


def get_job_category(job_id: str) -> str:
    """직업의 주 카테고리 반환"""
    for category, jobs in JOB_CATEGORIES.items():
        if job_id in jobs:
            return category
    return "physical"


# ─── 합체기 ───────────────────────────────────────────────────

class ComboSkill:
    """합체기: 2인 이상의 직업 조합 필살기"""

    def __init__(self, data: Dict[str, Any]):
        self.id: str = data["id"]
        self.name: str = data["name"]
        self.required_jobs: List[str] = data["required_jobs"]
        self.gauge_cost: int = data.get("gauge_cost", 250)
        self.min_affinity: int = data.get("min_affinity", 3)
        self.effects: List[Dict[str, Any]] = data.get("effects", [])
        self.description: str = data.get("description", "")
        self.animation: str = data.get("animation", "combo_default")
        # 협동 패턴: brv_hp(기본), empower_strike(강화→일격),
        # weaken_execute(약화→처형), sacrifice_burst(희생→폭발)
        self.combo_pattern: str = data.get("combo_pattern", "brv_hp")

    def can_execute(self, party_jobs: List[str], affinity_level: int, available_gauge: int) -> bool:
        """발동 조건 확인"""
        # 필요 직업이 파티에 모두 있는지
        for req_job in self.required_jobs:
            if req_job not in party_jobs:
                return False
        # 호감도 레벨 충족
        if affinity_level < self.min_affinity:
            return False
        # 게이지 충분
        if available_gauge < self.gauge_cost:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name,
            "required_jobs": self.required_jobs,
            "gauge_cost": self.gauge_cost,
            "min_affinity": self.min_affinity,
            "effects": self.effects,
            "description": self.description
        }


# ─── 파티 보너스 ──────────────────────────────────────────────

class PartyBonus:
    """파티 편성 보너스: 편성 조건에 따른 자동 적용 패시브"""

    def __init__(self, data: Dict[str, Any]):
        self.id: str = data["id"]
        self.name: str = data["name"]
        self.condition: Dict[str, Any] = data.get("condition", {})
        self.effects: Dict[str, Any] = data.get("effects", {})
        self.description: str = data.get("description", "")

    def check_condition(self, party_jobs: List[str]) -> bool:
        """파티 편성 조건 확인"""
        cond = self.condition

        # 카테고리 수 조건
        if "job_category" in cond:
            category = cond["job_category"]
            min_count = cond.get("min_count", 2)
            cat_jobs = JOB_CATEGORIES.get(category, [])
            count = sum(1 for j in party_jobs if j in cat_jobs)
            return count >= min_count

        # 특정 직업 조합
        if "required_jobs" in cond:
            for req in cond["required_jobs"]:
                if req not in party_jobs:
                    return False
            return True

        # 균형 편성 (물리+마법+서포트 각 1이상)
        if cond.get("balanced"):
            has_phys = any(j in JOB_CATEGORIES.get("physical", []) for j in party_jobs)
            has_magic = any(j in JOB_CATEGORIES.get("magic", []) for j in party_jobs)
            has_support = any(j in JOB_CATEGORIES.get("support", []) for j in party_jobs)
            return has_phys and has_magic and has_support

        # 모든 직업이 다른 카테고리 (다양성)
        if cond.get("all_different_categories"):
            categories = set(get_job_category(j) for j in party_jobs)
            return len(categories) >= len(party_jobs)

        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name,
            "condition": self.condition,
            "effects": self.effects,
            "description": self.description
        }


# ─── 시너지 매니저 ────────────────────────────────────────────

class SynergyManager:
    """직업 시너지 관리자"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._combo_skills: List[ComboSkill] = []
        self._party_bonuses: List[PartyBonus] = []
        self._active_bonuses: List[PartyBonus] = []
        self._load_data()
        self._initialized = True

    def _load_data(self):
        """YAML에서 시너지 데이터 로드"""
        import yaml
        from src.core.paths import get_project_root

        data_path = str(get_project_root() / "data" / "job_synergy.yaml")

        import os
        if not os.path.exists(data_path):
            logger.warning(f"job_synergy.yaml 파일을 찾을 수 없습니다: {data_path}")
            return

        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"job_synergy.yaml 로드 실패: {e}")
            return

        for combo_data in data.get("combo_skills", []):
            self._combo_skills.append(ComboSkill(combo_data))

        for bonus_data in data.get("party_bonuses", []):
            self._party_bonuses.append(PartyBonus(bonus_data))

        logger.info(f"합체기 {len(self._combo_skills)}개, 파티 보너스 {len(self._party_bonuses)}개 로드")

    # ─── 합체기 ────────────────────────

    def get_available_combos(
        self,
        party_jobs: List[str],
        affinity_manager: Any,
        available_gauge: int
    ) -> List[ComboSkill]:
        """발동 가능한 합체기 목록"""
        available = []
        for combo in self._combo_skills:
            # 호감도 조건 체크: 필요 직업 쌍의 호감도가 min_affinity 이상인지
            if affinity_manager:
                min_level = 999
                for i in range(len(combo.required_jobs)):
                    for j in range(i + 1, len(combo.required_jobs)):
                        level = affinity_manager.get_level(
                            combo.required_jobs[i], combo.required_jobs[j]
                        ).value
                        min_level = min(min_level, level)
            else:
                # affinity_manager가 없으면 호감도 조건 무시 (직업 조합 + 게이지만 확인)
                min_level = 999

            if combo.can_execute(party_jobs, min_level, available_gauge):
                available.append(combo)

        return available

    def get_all_combos(self) -> List[ComboSkill]:
        return list(self._combo_skills)

    # ─── 파티 보너스 ──────────────────

    def calculate_party_bonuses(self, party_jobs: List[str]) -> List[PartyBonus]:
        """파티 편성에 따른 활성 보너스 계산"""
        self._active_bonuses = [
            bonus for bonus in self._party_bonuses
            if bonus.check_condition(party_jobs)
        ]

        if self._active_bonuses:
            names = [b.name for b in self._active_bonuses]
            logger.info(f"파티 보너스 활성: {', '.join(names)}")
            for bonus in self._active_bonuses:
                event_bus.publish(Events.PARTY_BONUS_APPLIED, {
                    "bonus_id": bonus.id,
                    "bonus_name": bonus.name,
                    "effects": bonus.effects
                })

        return self._active_bonuses

    def get_active_bonuses(self) -> List[PartyBonus]:
        return list(self._active_bonuses)

    def get_total_bonus_effects(self) -> Dict[str, float]:
        """활성 보너스의 총합 효과"""
        total = {}
        for bonus in self._active_bonuses:
            for key, value in bonus.effects.items():
                if key in total:
                    total[key] = total[key] + value - 1.0 if isinstance(value, float) and value > 1.0 else total[key] + value
                else:
                    total[key] = value
        return total

    def get_teamwork_charge_bonus(self) -> float:
        """파티 보너스에 의한 팀워크 게이지 충전 보너스"""
        total = 0.0
        for bonus in self._active_bonuses:
            total += bonus.effects.get("teamwork_charge_bonus", 0.0)
        return total

    @classmethod
    def reload(cls):
        """데이터 리로드"""
        cls._instance = None


def get_synergy_manager() -> SynergyManager:
    return SynergyManager()
