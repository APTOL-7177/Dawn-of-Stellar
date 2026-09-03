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
    glitch_level: int = 0  # 글리치 레벨 (세이브 삭제 후에도 유지)

    # 해금된 특성 {job_id: [trait_id1, trait_id2, ...]}
    unlocked_traits: Dict[str, list] = field(default_factory=dict)

    # 구매한 영구 업그레이드 (아이템 ID 목록)
    purchased_upgrades: Set[str] = field(default_factory=set)

    # 구매한 패시브 (passives.yaml의 ID)
    purchased_passives: Set[str] = field(default_factory=set)

    # 해금된 직업 (job_id 목록)
    unlocked_jobs: Set[str] = field(default_factory=set)
    
    # 마을 시설 레벨 (영구 보존 - 게임 오버 후에도 유지)
    facility_levels: Dict[str, int] = field(default_factory=lambda: {
        "kitchen": 1,
        "blacksmith": 1,
        "alchemy_lab": 1,
        "storage": 1
    })

    # 영구 저장소 (재료 보존)
    hub_storage: list = field(default_factory=list)  # 허브 저장소 (List[Dict])
    town_storage: list = field(default_factory=list)  # 마을 창고 (List[Dict])

    # 게임 초기 설정
    intro_shown: bool = False  # 인트로 스토리 표시 여부
    tutorial_offered: bool = False  # 튜토리얼 권장 여부
    tutorial_completed: bool = False  # 튜토리얼 던전 클리어 여부 (True면 재입장 불가)

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

        # 개발 모드: 모든 성장 요소 MAX
        try:
            from src.core.config import get_config
            if get_config().development_mode:
                self._apply_dev_mode_maxout()
        except Exception:
            pass

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
        # 모든 직업 목록 (총 35개)
        all_jobs = [
            "alchemist", "archer", "archmage", "assassin", "bard",
            "battle_mage", "berserker", "breaker", "cleric", "dark_knight",
            "dimensionist", "dragon_knight", "druid", "elementalist", "engineer",
            "gladiator", "hacker", "knight", "monk", "ninja",
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

    def _apply_dev_mode_maxout(self):
        """개발 모드: 모든 성장 요소를 MAX로 설정"""
        import yaml

        # 별의 파편 MAX
        self.star_fragments = 999999

        # 모든 직업 해금 (35개)
        all_jobs = [
            "alchemist", "archer", "archmage", "assassin", "bard",
            "battle_mage", "berserker", "breaker", "cleric", "dark_knight",
            "dimensionist", "dragon_knight", "druid", "elementalist", "engineer",
            "gladiator", "hacker", "illusionist", "knight", "magician",
            "monk", "necromancer", "ninja", "paladin", "philosopher", "pirate",
            "priest", "rogue", "samurai", "shaman", "sniper",
            "spellblade", "sword_saint", "time_mage", "vampire", "warrior"
        ]
        self.unlocked_jobs = set(all_jobs)

        # 모든 직업의 모든 특성 해금
        for job_id in all_jobs:
            yaml_path = Path(f"data/characters/{job_id}.yaml")
            if yaml_path.exists():
                try:
                    with open(yaml_path, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        traits = data.get('traits', [])
                        self.unlocked_traits[job_id] = [t['id'] for t in traits]
                except Exception:
                    pass

        # 모든 패시브 구매
        all_passives = [
            "hp_boost", "mp_boost", "speed_boost", "brv_boost",
            "accuracy_boost", "evasion_boost", "luck_boost", "quick_step",
            "physical_power", "magic_power", "physical_guard", "magic_guard",
            "critical_boost", "counter_stance", "auto_regen", "mp_recovery",
            "battle_heal", "battle_mp", "damage_reduction", "status_resist",
            "first_strike", "break_master", "skill_master", "hp_danger_boost",
            "shield_mastery", "element_mastery", "critical_master", "double_hit",
            "lifesteal", "mana_leech", "retaliation", "berserker_rage",
            "guardian_angel", "phoenix_blessing", "double_cast", "ultimate_power",
            "ultimate_defense", "brave_soul", "tactical_genius", "time_master",
            "perfect_form", "unbreakable", "master_counter", "bloodthirst",
            "eternal_flame"
        ]
        self.purchased_passives = set(all_passives)

        # 모든 영구 업그레이드 구매
        all_upgrades = [
            "hp_증가_i", "hp_증가_ii", "mp_증가_i", "mp_증가_ii",
            "경험치_부스트_i", "경험치_부스트_ii", "골드_부스트",
            "인벤토리_확장_i", "인벤토리_확장_ii", "시작_레벨_증가"
        ]
        self.purchased_upgrades = set(all_upgrades)

        # 모든 시설 만렙 (Lv.4)
        self.facility_levels = {
            "kitchen": 4,
            "blacksmith": 4,
            "alchemy_lab": 4,
            "storage": 4,
            "shop": 4
        }

        # 튜토리얼/인트로 완료 처리
        self.intro_shown = True
        self.tutorial_offered = True
        self.tutorial_completed = True

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

    def grant_job_unlock_reward(self, job_id: Optional[str], star_fragments: int = 0) -> bool:
        """직업 해금 + 별의 파편 보상 (exactly-once)

        이미 해금된 직업이면 아무것도 적용하지 않고 False를 반환한다.
        따라서 중복 호출·재시작 후 재호출에도 보상이 이중 지급되지 않는다.
        """
        if not job_id or job_id in self.unlocked_jobs:
            return False
        self.unlocked_jobs.add(job_id)
        if star_fragments > 0:
            self.star_fragments += star_fragments
        return True

    def is_job_unlocked(self, job_id: str) -> bool:
        """직업 해금 여부 확인"""
        return job_id in self.unlocked_jobs
    
    def get_facility_level(self, facility_type: str) -> int:
        """
        시설 레벨 가져오기 (메타 진행)
        
        개발 모드에서는 모든 시설이 만렙(4)으로 설정됩니다.
        
        Args:
            facility_type: 시설 타입 문자열 (예: "kitchen", "blacksmith")
            
        Returns:
            시설 레벨 (기본값 1, 개발 모드: 4)
        """
        # 개발 모드 확인
        try:
            from src.core.config import get_config
            config = get_config()
            if config.development_mode:
                # 개발 모드: 모든 시설 만렙
                return 4
        except:
            # Config가 없으면 일반 모드로 처리
            pass
        
        return self.facility_levels.get(facility_type, 1)
    
    def set_facility_level(self, facility_type: str, level: int):
        """
        시설 레벨 설정 (메타 진행 - 영구 저장)
        
        Args:
            facility_type: 시설 타입 문자열
            level: 설정할 레벨
        """
        self.facility_levels[facility_type] = level

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (저장용)"""
        return {
            "star_fragments": self.star_fragments,
            "unlocked_traits": self.unlocked_traits,
            "purchased_upgrades": list(self.purchased_upgrades),
            "purchased_passives": list(self.purchased_passives),
            "unlocked_jobs": list(self.unlocked_jobs),
            "facility_levels": self.facility_levels,  # 시설 레벨 저장
            "hub_storage": self.hub_storage,  # 허브 저장소 저장
            "town_storage": self.town_storage,  # 마을 창고 저장
            "intro_shown": self.intro_shown,
            "tutorial_offered": self.tutorial_offered,
            "tutorial_completed": self.tutorial_completed,
            "glitch_level": self.glitch_level
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetaProgress':
        """딕셔너리에서 복원"""
        return cls(
            star_fragments=data.get("star_fragments", 0),
            unlocked_traits=data.get("unlocked_traits", {}),
            purchased_upgrades=set(data.get("purchased_upgrades", [])),
            purchased_passives=set(data.get("purchased_passives", [])),
            unlocked_jobs=set(data.get("unlocked_jobs", [])),
            facility_levels=data.get("facility_levels", {
                "kitchen": 1,
                "blacksmith": 1,
                "alchemy_lab": 1,
                "alchemy_lab": 1,
                "storage": 1
            }),
            hub_storage=data.get("hub_storage", []),
            town_storage=data.get("town_storage", []),
            intro_shown=data.get("intro_shown", False),
            tutorial_offered=data.get("tutorial_offered", False),
            tutorial_completed=data.get("tutorial_completed", False),
            glitch_level=data.get("glitch_level", 0)
        )


class MetaProgressManager:
    """메타 진행 관리자"""

    # 메타 진행 파일은 게임 세이브와 별도로 관리 (config 디렉토리)
    SAVE_FILE = Path("config/meta_progress.json")

    def __init__(self):
        self.logger = get_logger(Loggers.SYSTEM)
        self.progress: Optional[MetaProgress] = None

        # 저장 디렉토리 생성
        self.SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)

        # 기존 saves/meta_progress.json 파일 마이그레이션
        self._migrate_old_file()

        # 자동 로드
        self.load()

    def _migrate_old_file(self):
        """기존 saves/meta_progress.json 파일을 config/ 디렉토리로 이동"""
        old_file = Path("saves/meta_progress.json")
        if old_file.exists() and not self.SAVE_FILE.exists():
            try:
                import shutil
                shutil.move(str(old_file), str(self.SAVE_FILE))
                self.logger.info(f"메타 진행 파일 마이그레이션: {old_file} -> {self.SAVE_FILE}")
            except Exception as e:
                self.logger.warning(f"메타 진행 파일 마이그레이션 실패: {e}")

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
