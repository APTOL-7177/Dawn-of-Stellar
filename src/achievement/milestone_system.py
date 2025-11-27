"""
마일스톤 시스템 (Milestone System)

플레이어의 장기적인 발전을 추적하는 마일스톤
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.core.logger import get_logger

logger = get_logger("milestone")


class MilestoneCategory(Enum):
    """마일스톤 카테고리"""
    COMBAT = "combat"          # 전투 발전
    EXPLORATION = "exploration"  # 탐험 발전
    CRAFTING = "crafting"      # 제작 발전
    SOCIAL = "social"          # 소셜 발전
    PROGRESSION = "progression" # 게임 진행


class MilestoneTier(Enum):
    """마일스톤 등급"""
    BRONZE = "bronze"          # 동
    SILVER = "silver"          # 은
    GOLD = "gold"              # 금
    PLATINUM = "platinum"      # 백금
    DIAMOND = "diamond"        # 다이아몬드


@dataclass
class MilestoneStage:
    """마일스톤 단계"""
    threshold: int             # 달성 임계값
    reward_star_fragments: int # 별의 파편 보상
    reward_title: str = ""     # 칭호 보상
    description: str = ""      # 단계 설명

    @property
    def reward_description(self) -> str:
        """보상 설명"""
        rewards = []
        if self.reward_star_fragments > 0:
            rewards.append(f"별의 파편 {self.reward_star_fragments}개")
        if self.reward_title:
            rewards.append(f"칭호: {self.reward_title}")
        return " | ".join(rewards) if rewards else "보상 없음"


@dataclass
class Milestone:
    """마일스톤"""
    milestone_id: str
    name: str
    description: str
    category: MilestoneCategory
    icon: str = "[MILE]"

    # 진행도
    current_value: int = 0
    max_value: int = 100     # 최대값 (달성률 계산용)

    # 단계별 보상
    stages: List[MilestoneStage] = field(default_factory=list)
    current_stage: int = 0   # 현재 달성된 단계 (0-based)

    # 달성 정보
    last_updated: Optional[datetime] = None

    @property
    def progress_percentage(self) -> float:
        """진행률 (0.0-1.0)"""
        if self.max_value <= 0:
            return 1.0
        return min(self.current_value / self.max_value, 1.0)

    @property
    def next_stage(self) -> Optional[MilestoneStage]:
        """다음 단계"""
        if self.current_stage >= len(self.stages):
            return None
        return self.stages[self.current_stage]

    @property
    def is_complete(self) -> bool:
        """완전 달성 여부"""
        return self.current_stage >= len(self.stages)

    @property
    def current_stage_info(self) -> Optional[MilestoneStage]:
        """현재 단계 정보"""
        if self.current_stage > 0 and self.current_stage <= len(self.stages):
            return self.stages[self.current_stage - 1]
        return None

    def update_progress(self, amount: int) -> bool:
        """
        진행도 업데이트

        Args:
            amount: 증가량

        Returns:
            새로운 단계에 도달했으면 True
        """
        if self.is_complete:
            return False

        old_stage = self.current_stage
        self.current_value += amount
        self.last_updated = datetime.now()

        # 단계 달성 체크
        while (self.next_stage and
               self.current_value >= self.next_stage.threshold and
               self.current_stage < len(self.stages)):
            self.current_stage += 1
            logger.info(f"마일스톤 단계 달성: {self.name} - 단계 {self.current_stage}")

        return self.current_stage > old_stage

    def get_progress_text(self) -> str:
        """진행도 텍스트"""
        if self.is_complete:
            return "완료"
        elif self.next_stage:
            return f"{self.current_value}/{self.next_stage.threshold}"
        else:
            return f"{self.current_value}/{self.max_value}"


class MilestoneSystem:
    """마일스톤 시스템"""

    def __init__(self):
        self.milestones: Dict[str, Milestone] = {}
        self._load_milestones()

    def _load_milestones(self):
        """마일스톤 데이터 로드"""
        self.milestones = self._create_milestones()

    def _create_milestones(self) -> Dict[str, Milestone]:
        """마일스톤 생성"""
        milestones = {}

        # ===== 전투 발전 마일스톤 =====

        milestones["enemy_slayer"] = Milestone(
            milestone_id="enemy_slayer",
            name="적 사냥꾼",
            description="적을 처치하여 전투 실력을 키워보세요",
            category=MilestoneCategory.COMBAT,
            icon="[SWORD]",
            max_value=10000,
            stages=[
                MilestoneStage(100, 5, "초보 사냥꾼", "100마리 처치"),
                MilestoneStage(500, 10, "숙련된 사냥꾼", "500마리 처치"),
                MilestoneStage(1000, 15, "전문 사냥꾼", "1000마리 처치"),
                MilestoneStage(2500, 25, "마스터 사냥꾼", "2500마리 처치"),
                MilestoneStage(5000, 50, "전설의 사냥꾼", "5000마리 처치"),
                MilestoneStage(10000, 100, "신화의 사냥꾼", "10000마리 처치"),
            ]
        )

        milestones["damage_dealer"] = Milestone(
            milestone_id="damage_dealer",
            name="데미지 딜러",
            description="누적 데미지를 쌓아 파괴력을 증명하세요",
            category=MilestoneCategory.COMBAT,
            icon="[DAMAGE]",
            max_value=10000000,  # 10M 데미지
            stages=[
                MilestoneStage(10000, 5, "약한 펀치", "10,000 데미지"),
                MilestoneStage(50000, 10, "강한 펀치", "50,000 데미지"),
                MilestoneStage(100000, 15, "파괴의 화신", "100,000 데미지"),
                MilestoneStage(500000, 25, "파괴신", "500,000 데미지"),
                MilestoneStage(1000000, 50, "세계파괴자", "1,000,000 데미지"),
                MilestoneStage(5000000, 100, "우주파괴자", "5,000,000 데미지"),
                MilestoneStage(10000000, 200, "차원파괴자", "10,000,000 데미지"),
            ]
        )

        # ===== 탐험 발전 마일스톤 =====

        milestones["dungeon_explorer"] = Milestone(
            milestone_id="dungeon_explorer",
            name="던전 탐험가",
            description="던전을 탐험하여 모험을 쌓아보세요",
            category=MilestoneCategory.EXPLORATION,
            icon="[MAP]",
            max_value=1000,  # 1000층
            stages=[
                MilestoneStage(10, 5, "초보 모험가", "10층 도달"),
                MilestoneStage(50, 10, "중급 모험가", "50층 도달"),
                MilestoneStage(100, 15, "상급 모험가", "100층 도달"),
                MilestoneStage(250, 25, "마스터 모험가", "250층 도달"),
                MilestoneStage(500, 50, "전설의 모험가", "500층 도달"),
                MilestoneStage(1000, 100, "신화의 모험가", "1000층 도달"),
            ]
        )

        milestones["treasure_hunter"] = Milestone(
            milestone_id="treasure_hunter",
            name="보물 사냥꾼",
            description="보물상자를 열어 부를 쌓아보세요",
            category=MilestoneCategory.EXPLORATION,
            icon="[TREASURE]",
            max_value=10000,
            stages=[
                MilestoneStage(10, 3, "보물 초보", "10개 상자 개방"),
                MilestoneStage(50, 8, "보물 중급", "50개 상자 개방"),
                MilestoneStage(100, 12, "보물 상급", "100개 상자 개방"),
                MilestoneStage(500, 20, "보물 마스터", "500개 상자 개방"),
                MilestoneStage(1000, 30, "보물 전설", "1000개 상자 개방"),
                MilestoneStage(5000, 60, "보물 신화", "5000개 상자 개방"),
                MilestoneStage(10000, 120, "보물의 신", "10000개 상자 개방"),
            ]
        )

        # ===== 제작 발전 마일스톤 =====

        milestones["master_chef"] = Milestone(
            milestone_id="master_chef",
            name="마스터 셰프",
            description="요리를 만들어 미식의 세계를 탐험하세요",
            category=MilestoneCategory.CRAFTING,
            icon="[CHEF]",
            max_value=10000,
            stages=[
                MilestoneStage(10, 3, "요리 초보", "10개 요리 제작"),
                MilestoneStage(50, 8, "요리 견습생", "50개 요리 제작"),
                MilestoneStage(100, 12, "숙련된 요리사", "100개 요리 제작"),
                MilestoneStage(500, 20, "마스터 셰프", "500개 요리 제작"),
                MilestoneStage(1000, 30, "요리 대가", "1000개 요리 제작"),
                MilestoneStage(5000, 60, "요리의 신", "5000개 요리 제작"),
                MilestoneStage(10000, 120, "미식의 신", "10000개 요리 제작"),
            ]
        )

        milestones["alchemist"] = Milestone(
            milestone_id="alchemist",
            name="연금술사",
            description="포션을 만들어 연금술의 비밀을 밝혀보세요",
            category=MilestoneCategory.CRAFTING,
            icon="[ALCHEMY]",
            max_value=5000,
            stages=[
                MilestoneStage(10, 4, "연금 초보", "10개 포션 제작"),
                MilestoneStage(50, 10, "연금 견습생", "50개 포션 제작"),
                MilestoneStage(100, 15, "숙련된 연금술사", "100개 포션 제작"),
                MilestoneStage(500, 25, "마스터 연금술사", "500개 포션 제작"),
                MilestoneStage(1000, 40, "연금술 대가", "1000개 포션 제작"),
                MilestoneStage(5000, 80, "연금술의 신", "5000개 포션 제작"),
            ]
        )

        # ===== 소셜 발전 마일스톤 =====

        milestones["team_player"] = Milestone(
            milestone_id="team_player",
            name="팀 플레이어",
            description="다른 플레이어들과 협력하여 승리를 쟁취하세요",
            category=MilestoneCategory.SOCIAL,
            icon="[TEAM]",
            max_value=1000,
            stages=[
                MilestoneStage(5, 10, "협력 초보", "5번 협력 플레이"),
                MilestoneStage(25, 20, "협력 중급", "25번 협력 플레이"),
                MilestoneStage(50, 30, "협력 상급", "50번 협력 플레이"),
                MilestoneStage(100, 50, "협력 마스터", "100번 협력 플레이"),
                MilestoneStage(250, 80, "팀 리더", "250번 협력 플레이"),
                MilestoneStage(500, 120, "전설의 파트너", "500번 협력 플레이"),
                MilestoneStage(1000, 200, "영웅의 동료", "1000번 협력 플레이"),
            ]
        )

        # ===== 게임 진행 마일스톤 =====

        milestones["playtime_warrior"] = Milestone(
            milestone_id="playtime_warrior",
            name="플레이타임 워리어",
            description="오랜 시간 게임을 플레이하여 경험을 쌓아보세요",
            category=MilestoneCategory.PROGRESSION,
            icon="[TIME]",
            max_value=1000,  # 1000시간
            stages=[
                MilestoneStage(10, 5, "게임 초보", "10시간 플레이"),
                MilestoneStage(50, 15, "게임 중급", "50시간 플레이"),
                MilestoneStage(100, 25, "게임 상급", "100시간 플레이"),
                MilestoneStage(250, 50, "게임 마스터", "250시간 플레이"),
                MilestoneStage(500, 100, "게임 전설", "500시간 플레이"),
                MilestoneStage(1000, 200, "게임의 신", "1000시간 플레이"),
            ]
        )

        milestones["completionist"] = Milestone(
            milestone_id="completionist",
            name="완벽주의자",
            description="모든 것을 수집하고 완료하여 완벽을 추구하세요",
            category=MilestoneCategory.PROGRESSION,
            icon="🏆",
            max_value=100,  # 100% 완료
            stages=[
                MilestoneStage(10, 10, "수집 초보", "10% 완료"),
                MilestoneStage(25, 20, "수집 중급", "25% 완료"),
                MilestoneStage(50, 40, "수집 상급", "50% 완료"),
                MilestoneStage(75, 60, "수집 마스터", "75% 완료"),
                MilestoneStage(90, 80, "완벽 추구자", "90% 완료"),
                MilestoneStage(100, 150, "완벽주의자", "100% 완료"),
            ]
        )

        return milestones

    def get_milestone(self, milestone_id: str) -> Optional[Milestone]:
        """특정 마일스톤 조회"""
        return self.milestones.get(milestone_id)

    def get_all_milestones(self) -> List[Milestone]:
        """모든 마일스톤 목록"""
        return list(self.milestones.values())

    def get_milestones_by_category(self, category: MilestoneCategory) -> List[Milestone]:
        """카테고리별 마일스톤 목록"""
        return [m for m in self.milestones.values() if m.category == category]

    def update_milestone(self, milestone_id: str, amount: int) -> bool:
        """
        마일스톤 진행도 업데이트

        Returns:
            새로운 단계에 도달했으면 True
        """
        milestone = self.get_milestone(milestone_id)
        if not milestone:
            return False

        return milestone.update_progress(amount)

    def update_multiple_milestones(self, updates: Dict[str, int]) -> List[str]:
        """
        여러 마일스톤 동시 업데이트

        Args:
            updates: {milestone_id: amount} 딕셔너리

        Returns:
            새로운 단계에 도달한 마일스톤 ID 목록
        """
        newly_completed = []

        for milestone_id, amount in updates.items():
            if self.update_milestone(milestone_id, amount):
                newly_completed.append(milestone_id)

        return newly_completed

    def get_completion_percentage(self) -> float:
        """전체 마일스톤 완료율 (0.0-1.0)"""
        if not self.milestones:
            return 0.0

        total_stages = sum(len(m.stages) for m in self.milestones.values())
        completed_stages = sum(m.current_stage for m in self.milestones.values())

        return completed_stages / total_stages if total_stages > 0 else 0.0

    def save_progress(self) -> Dict[str, Any]:
        """진행도 저장 데이터"""
        return {
            "milestones": {
                mid: {
                    "current_value": m.current_value,
                    "current_stage": m.current_stage,
                    "last_updated": m.last_updated.isoformat() if m.last_updated else None,
                }
                for mid, m in self.milestones.items()
            }
        }

    def load_progress(self, data: Dict[str, Any]):
        """진행도 불러오기"""
        if "milestones" not in data:
            return

        for mid, save_data in data["milestones"].items():
            if mid in self.milestones:
                milestone = self.milestones[mid]
                milestone.current_value = save_data.get("current_value", 0)
                milestone.current_stage = save_data.get("current_stage", 0)

                if save_data.get("last_updated"):
                    milestone.last_updated = datetime.fromisoformat(save_data["last_updated"])
