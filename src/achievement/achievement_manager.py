"""
도전과제 관리자 (Achievement Manager)

도전과제와 마일스톤 시스템을 통합 관리
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import random

from src.core.logger import get_logger
from src.achievement.achievement_system import AchievementSystem, Achievement
from src.achievement.milestone_system import MilestoneSystem, Milestone

logger = get_logger("achievement_manager")


class AchievementManager:
    """도전과제 및 마일스톤 관리자"""

    def __init__(self):
        self.achievement_system = AchievementSystem()
        self.milestone_system = MilestoneSystem()

        # 통계 추적용 변수들
        self.stats = {
            "total_kills": 0,
            "total_damage_dealt": 0,
            "max_damage_in_one_hit": 0,
            "potions_used_in_battle": 0,
            "current_battle_skill_used": set(),
            "floor_reached": 0,
            "chests_opened": 0,
            "food_cooked": 0,
            "potions_brewed": 0,
            "multiplayer_sessions": 0,
            "playtime_hours": 0,
            "completion_percentage": 0.0,
        }

        # 일일/주간 도전과제 추적
        self.daily_achievements = []
        self.weekly_achievements = []
        self._generate_daily_achievements()

        logger.info("도전과제 시스템 초기화 완료")

    def _generate_daily_achievements(self):
        """일일 도전과제 생성"""
        # 간단한 일일 도전과제들
        daily_options = [
            ("daily_kills", "오늘 적 10마리 처치하기", "kill_count", "any", 10),
            ("daily_damage", "오늘 5000 데미지 입히기", "damage_dealt_total", None, 5000),
            ("daily_floor", "오늘 5층 더 올라가기", "floor_progress", None, 5),
            ("daily_cooking", "오늘 3개 요리 만들기", "item_crafted", "food", 3),
        ]

        # 3개 랜덤 선택
        selected = random.sample(daily_options, 3)

        for achievement_id, name, cond_type, target, required in selected:
            achievement = Achievement(
                achievement_id=f"daily_{achievement_id}_{datetime.now().date()}",
                name=f"[일일] {name}",
                description="오늘 안에 완료하세요!",
                category=self.achievement_system.achievements["why_wont_you_die"].category,  # 임시
                rarity=self.achievement_system.achievements["why_wont_you_die"].rarity,  # 임시
                conditions=[],  # 일일 도전과제는 별도 처리
                reward=self.achievement_system.achievements["why_wont_you_die"].reward,  # 임시
                icon="📅"
            )
            self.daily_achievements.append(achievement)

    def on_enemy_killed(self, enemy_type: str = "any", damage_dealt: int = 0):
        """적 처치 이벤트"""
        self.stats["total_kills"] += 1
        self.stats["total_damage_dealt"] += damage_dealt
        self.stats["max_damage_in_one_hit"] = max(self.stats["max_damage_in_one_hit"], damage_dealt)

        # 도전과제 체크
        newly_unlocked = []
        newly_unlocked.extend(self.achievement_system.check_all_achievements("kill_count", enemy_type))

        # 마일스톤 업데이트
        milestone_updates = {
            "enemy_slayer": 1,
            "damage_dealer": damage_dealt,
        }
        newly_completed = self.milestone_system.update_multiple_milestones(milestone_updates)

        return newly_unlocked, newly_completed

    def on_damage_dealt(self, damage: int, is_critical: bool = False):
        """데미지 입히기 이벤트"""
        self.stats["total_damage_dealt"] += damage
        self.stats["max_damage_in_one_hit"] = max(self.stats["max_damage_in_one_hit"], damage)

        newly_unlocked = []
        if damage >= 9999:
            newly_unlocked.extend(self.achievement_system.check_all_achievements("damage_dealt", damage))

        # 원 힛 킬 체크 (데미지가 적의 최대 체력보다 크면)
        if damage >= 1000:  # 임의의 기준 - 실제로는 적의 체력과 비교해야 함
            newly_unlocked.extend(self.achievement_system.check_all_achievements("one_hit_kill", 1))

        # 마일스톤 업데이트
        milestone_updates = {"damage_dealer": damage}
        newly_completed = self.milestone_system.update_multiple_milestones(milestone_updates)

        return newly_unlocked, newly_completed

    def on_skill_used(self, skill_name: str):
        """스킬 사용 이벤트"""
        self.stats["current_battle_skill_used"].add(skill_name)

        newly_unlocked = []
        newly_unlocked.extend(self.achievement_system.check_all_achievements("skill_used", skill_name))

        # 리미트 브레이크 마스터 체크
        if skill_name == "limit_break":
            newly_unlocked.extend(self.achievement_system.check_all_achievements("skill_used", "limit_break"))

        return newly_unlocked, []

    def on_potion_used(self):
        """포션 사용 이벤트"""
        self.stats["potions_used_in_battle"] += 1

        newly_unlocked = []
        if self.stats["potions_used_in_battle"] >= 10:
            newly_unlocked.extend(self.achievement_system.check_all_achievements("potions_used", "any", 1))

        return newly_unlocked, []

    def on_battle_end(self, battle_result: str, turns_survived: int):
        """전투 종료 이벤트"""
        newly_unlocked = []
        newly_completed = []

        if battle_result == "victory":
            # 무피해 승리 체크
            if self.stats.get("damage_taken_in_battle", 0) == 0:
                newly_unlocked.extend(self.achievement_system.check_all_achievements("no_damage_taken", True))

            # 하나의 스킬만 사용해서 승리 체크
            if len(self.stats["current_battle_skill_used"]) == 1:
                newly_unlocked.extend(self.achievement_system.check_all_achievements("enemies_killed_with_skill", "single_skill_only"))

        # 스피드런 체크
        if turns_survived <= 5:
            newly_unlocked.extend(self.achievement_system.check_all_achievements("turns_survived", turns_survived))

        # 전투 통계 초기화
        self.stats["potions_used_in_battle"] = 0
        self.stats["current_battle_skill_used"] = set()
        self.stats["damage_taken_in_battle"] = 0

        return newly_unlocked, newly_completed

    def on_floor_reached(self, floor: int):
        """층 도달 이벤트"""
        old_floor = self.stats["floor_reached"]
        self.stats["floor_reached"] = max(self.stats["floor_reached"], floor)

        newly_unlocked = []
        newly_completed = []

        # 층 도달 도전과제들 체크
        newly_unlocked.extend(self.achievement_system.check_all_achievements("floor_reached", floor))

        # 마일스톤 업데이트
        if floor > old_floor:
            milestone_updates = {"dungeon_explorer": floor - old_floor}
            newly_completed = self.milestone_system.update_multiple_milestones(milestone_updates)

        return newly_unlocked, newly_completed

    def on_chest_opened(self):
        """보물상자 열기 이벤트"""
        self.stats["chests_opened"] += 1

        milestone_updates = {"treasure_hunter": 1}
        newly_completed = self.milestone_system.update_multiple_milestones(milestone_updates)

        return [], newly_completed

    def on_item_crafted(self, item_type: str):
        """아이템 제작 이벤트"""
        newly_unlocked = []
        newly_completed = []

        if item_type == "food":
            self.stats["food_cooked"] += 1
            newly_unlocked.extend(self.achievement_system.check_all_achievements("item_crafted", "food"))
            newly_completed = self.milestone_system.update_multiple_milestones({"master_chef": 1})

        elif item_type in ["potion", "elixir", "grenade"]:
            self.stats["potions_brewed"] += 1
            newly_completed = self.milestone_system.update_multiple_milestones({"alchemist": 1})

        return newly_unlocked, newly_completed

    def on_multiplayer_session(self):
        """멀티플레이 세션 이벤트"""
        self.stats["multiplayer_sessions"] += 1

        milestone_updates = {"team_player": 1}
        newly_completed = self.milestone_system.update_multiple_milestones(milestone_updates)

        return [], newly_completed

    def on_playtime_update(self, hours_played: float):
        """플레이타임 업데이트 이벤트"""
        old_hours = self.stats["playtime_hours"]
        self.stats["playtime_hours"] = hours_played

        newly_unlocked = []
        newly_completed = []

        # 비밀의 팬 도전과제 체크 (100시간)
        if hours_played >= 100:
            newly_unlocked.extend(self.achievement_system.check_all_achievements("playtime_hours", int(hours_played)))

        # 마일스톤 업데이트
        if hours_played > old_hours:
            hours_gained = int(hours_played - old_hours)
            newly_completed = self.milestone_system.update_multiple_milestones({"playtime_warrior": hours_gained})

        return newly_unlocked, newly_completed

    def on_completion_update(self, completion_percentage: float):
        """완료도 업데이트 이벤트"""
        old_completion = self.stats["completion_percentage"]
        self.stats["completion_percentage"] = completion_percentage

        newly_completed = []

        # 마일스톤 업데이트
        if completion_percentage > old_completion:
            percent_gained = int((completion_percentage - old_completion) * 100)
            newly_completed = self.milestone_system.update_multiple_milestones({"completionist": percent_gained})

        return [], newly_completed

    def check_daily_achievements(self) -> List[str]:
        """일일 도전과제 달성 체크"""
        newly_unlocked = []

        # 간단한 일일 도전과제 로직 (실제로는 더 복잡한 로직 필요)
        current_date = datetime.now().date()

        for achievement in self.daily_achievements:
            if not achievement.is_unlocked and achievement.achievement_id.endswith(str(current_date)):
                # 임시: 랜덤으로 일부 달성
                if random.random() < 0.1:  # 10% 확률로 달성
                    achievement.is_unlocked = True
                    achievement.unlocked_at = datetime.now()
                    newly_unlocked.append(achievement.achievement_id)

        return newly_unlocked

    def get_all_achievements(self) -> List[Achievement]:
        """모든 도전과제 목록"""
        all_achievements = self.achievement_system.get_all_achievements()
        all_achievements.extend(self.daily_achievements)
        return all_achievements

    def get_unlocked_achievements(self) -> List[Achievement]:
        """달성된 도전과제 목록"""
        unlocked = self.achievement_system.get_unlocked_achievements()
        unlocked.extend([a for a in self.daily_achievements if a.is_unlocked])
        return unlocked

    def get_completion_stats(self) -> Dict[str, Any]:
        """완료 통계"""
        return {
            "achievement_completion": self.achievement_system.get_completion_percentage(),
            "milestone_completion": self.milestone_system.get_completion_percentage(),
            "total_star_fragments_earned": self._calculate_total_star_fragments(),
            "stats": self.stats.copy(),
        }

    def _calculate_total_star_fragments(self) -> int:
        """총 획득한 별의 파편 수 계산"""
        total = 0

        # 도전과제 보상
        for achievement in self.get_unlocked_achievements():
            if achievement.reward.star_fragments > 0:
                total += achievement.reward.star_fragments

        # 마일스톤 보상
        for milestone in self.milestone_system.get_all_milestones():
            for i in range(milestone.current_stage):
                if i < len(milestone.stages):
                    total += milestone.stages[i].reward_star_fragments

        return total

    def save_progress(self) -> Dict[str, Any]:
        """진행도 저장"""
        return {
            "achievement_system": self.achievement_system.save_progress(),
            "milestone_system": self.milestone_system.save_progress(),
            "stats": self.stats,
            "daily_achievements": [
                {
                    "achievement_id": a.achievement_id,
                    "is_unlocked": a.is_unlocked,
                    "unlocked_at": a.unlocked_at.isoformat() if a.unlocked_at else None,
                }
                for a in self.daily_achievements
            ],
        }

    def load_progress(self, data: Dict[str, Any]):
        """진행도 불러오기"""
        if "achievement_system" in data:
            self.achievement_system.load_progress(data["achievement_system"])

        if "milestone_system" in data:
            self.milestone_system.load_progress(data["milestone_system"])

        if "stats" in data:
            self.stats.update(data["stats"])

        if "daily_achievements" in data:
            for save_data in data["daily_achievements"]:
                for achievement in self.daily_achievements:
                    if achievement.achievement_id == save_data["achievement_id"]:
                        achievement.is_unlocked = save_data.get("is_unlocked", False)
                        if save_data.get("unlocked_at"):
                            achievement.unlocked_at = datetime.fromisoformat(save_data["unlocked_at"])
                        break

        logger.info("도전과제 시스템 진행도 불러오기 완료")
