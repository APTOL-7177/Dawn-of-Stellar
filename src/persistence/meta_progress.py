"""
메타 진행 시스템

게임 바깥에서 영구적으로 유지되는 진행 상태
- 별의 파편 (star_fragments)
- 해금된 특성 (unlocked_traits)
- 영구 업그레이드
"""

import json
from pathlib import Path
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass, field, asdict

from src.core.logger import get_logger, Loggers


@dataclass
class MetaProgress:
    """메타 진행 상태"""
    star_fragments: int = 0  # 별의 파편 (메타 화폐)

    # 해금된 특성 {job_id: [trait_id1, trait_id2, ...]}
    unlocked_traits: Dict[str, list] = field(default_factory=dict)

    # 구매한 영구 업그레이드 (아이템 ID 목록)
    purchased_upgrades: Set[str] = field(default_factory=set)

    # 구매한 패시브 (passives.yaml의 ID)
    purchased_passives: Set[str] = field(default_factory=set)

    # 해금된 직업 (job_id 목록)
    unlocked_jobs: Set[str] = field(default_factory=set)

    def __post_init__(self):
        """초기화 후 처리"""
        # Set을 list로 변환되어 저장된 것을 다시 Set으로 복원
        if isinstance(self.purchased_upgrades, list):
            self.purchased_upgrades = set(self.purchased_upgrades)
        if isinstance(self.purchased_passives, list):
            self.purchased_passives = set(self.purchased_passives)
        if isinstance(self.unlocked_jobs, list):
            self.unlocked_jobs = set(self.unlocked_jobs)

        # 기본 해금 직업 및 특성 설정
        self._ensure_default_unlocked_jobs()
        self._ensure_default_unlocked_traits()

    def _ensure_default_unlocked_jobs(self):
        """기본 해금 직업 확인 및 설정"""
        # 초기 해금 직업 (초보자용 쉬운 직업들)
        default_jobs = {
            "warrior",    # 전사 - 기본 물리 딜러
            "archmage",   # 아크메이지 - 기본 마법 딜러
            "cleric",     # 성직자 - 기본 힐러
            "rogue",      # 도적 - 기본 빠른 딜러
            "knight",     # 기사 - 기본 탱커
            "archer"      # 궁수 - 기본 원거리 딜러
        }

        # 아직 해금되지 않았으면 기본 직업 해금
        if not self.unlocked_jobs:
            self.unlocked_jobs = default_jobs.copy()
        else:
            # 기존에 해금된 직업이 있어도 기본 직업은 항상 포함
            self.unlocked_jobs.update(default_jobs)

    def _ensure_default_unlocked_traits(self):
        """기본 해금 특성 확인 및 설정"""
        # 모든 직업 목록 (총 33개)
        all_jobs = [
            "alchemist", "archer", "archmage", "assassin", "bard",
            "battle_mage", "berserker", "breaker", "cleric", "dark_knight",
            "dimensionist", "dragon_knight", "druid", "elementalist", "engineer",
            "gladiator", "hacker", "knight", "monk",
            "necromancer", "paladin", "philosopher", "pirate", "priest",
            "rogue", "samurai", "shaman", "sniper", "spellblade",
            "sword_saint", "time_mage", "vampire", "warrior"
        ]

        # 각 직업의 특성 목록 로드 및 기본 2개 해금
        import yaml
        for job_id in all_jobs:
            if job_id not in self.unlocked_traits:
                yaml_path = Path(f"data/characters/{job_id}.yaml")

                if yaml_path.exists():
                    try:
                        with open(yaml_path, 'r', encoding='utf-8') as f:
                            data = yaml.safe_load(f)
                            traits = data.get('traits', [])

                            # 처음 2개 특성 해금
                            default_unlocked = [trait['id'] for trait in traits[:2]]
                            self.unlocked_traits[job_id] = default_unlocked
                    except:
                        # 실패 시 빈 리스트
                        self.unlocked_traits[job_id] = []

    def add_star_fragments(self, amount: int):
        """별의 파편 추가"""
        self.star_fragments += amount

    def spend_star_fragments(self, amount: int) -> bool:
        """별의 파편 소비"""
        if self.star_fragments >= amount:
            self.star_fragments -= amount
            return True
        return False

    def unlock_trait(self, job_id: str, trait_id: str):
        """특성 해금"""
        if job_id not in self.unlocked_traits:
            self.unlocked_traits[job_id] = []

        if trait_id not in self.unlocked_traits[job_id]:
            self.unlocked_traits[job_id].append(trait_id)

    def is_trait_unlocked(self, job_id: str, trait_id: str) -> bool:
        """특성 해금 여부 확인"""
        return trait_id in self.unlocked_traits.get(job_id, [])

    def purchase_upgrade(self, upgrade_id: str) -> bool:
        """영구 업그레이드 구매"""
        if upgrade_id not in self.purchased_upgrades:
            self.purchased_upgrades.add(upgrade_id)
            return True
        return False

    def is_upgrade_purchased(self, upgrade_id: str) -> bool:
        """업그레이드 구매 여부"""
        return upgrade_id in self.purchased_upgrades

    def purchase_passive(self, passive_id: str) -> bool:
        """패시브 구매"""
        if passive_id not in self.purchased_passives:
            self.purchased_passives.add(passive_id)
            return True
        return False

    def is_passive_purchased(self, passive_id: str) -> bool:
        """패시브 구매 여부"""
        return passive_id in self.purchased_passives

    def unlock_job(self, job_id: str) -> bool:
        """직업 해금"""
        if job_id not in self.unlocked_jobs:
            self.unlocked_jobs.add(job_id)
            return True
        return False

    def is_job_unlocked(self, job_id: str) -> bool:
        """직업 해금 여부 확인"""
        return job_id in self.unlocked_jobs

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (저장용)"""
        return {
            "star_fragments": self.star_fragments,
            "unlocked_traits": self.unlocked_traits,
            "purchased_upgrades": list(self.purchased_upgrades),
            "purchased_passives": list(self.purchased_passives),
            "unlocked_jobs": list(self.unlocked_jobs)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetaProgress':
        """딕셔너리에서 복원"""
        return cls(
            star_fragments=data.get("star_fragments", 0),
            unlocked_traits=data.get("unlocked_traits", {}),
            purchased_upgrades=set(data.get("purchased_upgrades", [])),
            purchased_passives=set(data.get("purchased_passives", [])),
            unlocked_jobs=set(data.get("unlocked_jobs", []))
        )


class MetaProgressManager:
    """메타 진행 관리자"""

    SAVE_FILE = Path("saves/meta_progress.json")

    def __init__(self):
        self.logger = get_logger(Loggers.SYSTEM)
        self.progress: Optional[MetaProgress] = None

        # 저장 디렉토리 생성
        self.SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)

        # 자동 로드
        self.load()

    def load(self) -> MetaProgress:
        """메타 진행 로드"""
        if self.SAVE_FILE.exists():
            try:
                with open(self.SAVE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.progress = MetaProgress.from_dict(data)
                    self.logger.info(
                        f"메타 진행 로드 완료: 별의 파편 {self.progress.star_fragments}"
                    )
            except Exception as e:
                self.logger.error(f"메타 진행 로드 실패: {e}")
                self.progress = MetaProgress()
        else:
            self.logger.info("메타 진행 파일 없음 - 새로 생성")
            self.progress = MetaProgress()

        return self.progress

    def save(self):
        """메타 진행 저장"""
        try:
            with open(self.SAVE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.progress.to_dict(), f, ensure_ascii=False, indent=2)
            self.logger.info(
                f"메타 진행 저장 완료: 별의 파편 {self.progress.star_fragments}"
            )
        except Exception as e:
            self.logger.error(f"메타 진행 저장 실패: {e}")

    def get_progress(self) -> MetaProgress:
        """현재 메타 진행 반환"""
        if self.progress is None:
            self.load()
        return self.progress


# 전역 인스턴스
_meta_progress_manager: Optional[MetaProgressManager] = None


def get_meta_progress_manager() -> MetaProgressManager:
    """전역 메타 진행 관리자"""
    global _meta_progress_manager
    if _meta_progress_manager is None:
        _meta_progress_manager = MetaProgressManager()
    return _meta_progress_manager


def get_meta_progress() -> MetaProgress:
    """현재 메타 진행 상태"""
    return get_meta_progress_manager().get_progress()


def save_meta_progress():
    """메타 진행 저장"""
    get_meta_progress_manager().save()
