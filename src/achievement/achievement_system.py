"""
도전과제 시스템 (Achievement System)

오마주와 밈으로 가득한 재미있는 도전과제들
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, date
import random

from src.core.logger import get_logger

logger = get_logger("achievement")


class AchievementCategory(Enum):
    """도전과제 카테고리"""
    COMBAT = "combat"          # 전투 관련
    EXPLORATION = "exploration"  # 탐험 관련
    CRAFTING = "crafting"      # 제작 관련
    SOCIAL = "social"          # 소셜/멀티플레이
    HUMOROUS = "humorous"      # 유머러스
    MEME = "meme"              # 밈
    HOMAGE = "homage"          # 오마주


class AchievementRarity(Enum):
    """도전과제 희귀도"""
    COMMON = "common"          # 일반
    UNCOMMON = "uncommon"      # 고급
    RARE = "rare"              # 희귀
    EPIC = "epic"              # 영웅
    LEGENDARY = "legendary"    # 전설


@dataclass
class AchievementCondition:
    """도전과제 달성 조건"""
    type: str                    # 조건 타입 ("kill_count", "item_crafted", "date_check" 등)
    target: Any                  # 목표 대상
    required: int = 1            # 요구량
    current: int = 0             # 현재 진행도
    extra_data: Dict[str, Any] = field(default_factory=dict)  # 추가 데이터

    @property
    def is_complete(self) -> bool:
        """완료 여부"""
        return self.current >= self.required

    @property
    def progress_percentage(self) -> float:
        """진행률 (0.0-1.0)"""
        if self.required <= 0:
            return 1.0
        return min(self.current / self.required, 1.0)


@dataclass
class AchievementReward:
    """도전과제 보상"""
    title: str = ""              # 칭호 (옵션)
    star_fragments: int = 0      # 별의 파편
    description: str = ""        # 보상 설명

    def __str__(self):
        rewards = []
        if self.title:
            rewards.append(f"칭호: {self.title}")
        if self.star_fragments > 0:
            rewards.append(f"별의 파편 {self.star_fragments}개")
        return " | ".join(rewards) if rewards else "보상 없음"


@dataclass
class Achievement:
    """도전과제"""
    achievement_id: str
    name: str
    description: str
    category: AchievementCategory
    rarity: AchievementRarity
    conditions: List[AchievementCondition]
    reward: AchievementReward
    icon: str = "?"              # 아이콘 (이모지나 심볼)
    hint: str = ""               # 힌트
    is_hidden: bool = False      # 히든 도전과제
    is_unlocked: bool = False    # 달성 여부
    unlocked_at: Optional[datetime] = None  # 달성 시간

    @property
    def is_complete(self) -> bool:
        """모든 조건 완료 여부"""
        return all(condition.is_complete for condition in self.conditions)

    @property
    def progress_percentage(self) -> float:
        """전체 진행률 (0.0-1.0)"""
        if not self.conditions:
            return 1.0
        return sum(c.progress_percentage for c in self.conditions) / len(self.conditions)

    def update_condition(self, condition_type: str, target: Any, amount: int = 1) -> bool:
        """
        조건 진행도 업데이트

        Args:
            condition_type: 조건 타입
            target: 목표 대상
            amount: 증가량

        Returns:
            달성되었으면 True
        """
        was_complete = self.is_complete

        for condition in self.conditions:
            if condition.type == condition_type:
                # 조건 타입별 매칭 로직
                if condition_type == "kill_count":
                    if target == condition.target or condition.target == "any":
                        condition.current += amount
                elif condition_type == "item_crafted":
                    if target == condition.target or condition.target == "any":
                        condition.current += amount
                elif condition_type == "date_check":
                    # 특정 날짜 체크 (예: 사카모토 데이즈)
                    today = date.today()
                    if hasattr(condition.target, '__iter__') and today in condition.target:
                        condition.current = condition.required
                elif condition_type == "damage_dealt":
                    if isinstance(target, int):
                        condition.current = max(condition.current, target)
                elif condition_type == "turns_survived":
                    if isinstance(target, int):
                        condition.current = max(condition.current, target)
                elif condition_type == "potions_used":
                    condition.current += amount
                elif condition_type == "skill_used":
                    if target == condition.target:
                        condition.current += amount
                elif condition_type == "floor_reached":
                    if isinstance(target, int):
                        condition.current = max(condition.current, target)
                elif condition_type == "enemies_killed_with_skill":
                    if target == condition.target:
                        condition.current += amount
                elif condition_type == "no_damage_taken":
                    if target == True:
                        condition.current = condition.required
                elif condition_type == "chicken_dance":
                    # 춤 추기 카운트
                    condition.current += amount
                elif condition_type == "exploration_percentage":
                    if isinstance(target, float):
                        condition.current = int(target * condition.required)
                elif condition_type == "chased_by_enemy":
                    if isinstance(target, int):
                        condition.current = max(condition.current, target)
                elif condition_type == "damage_taken":
                    if isinstance(target, int):
                        condition.current += target
                elif condition_type == "one_hit_kill":
                    condition.current += amount
                elif condition_type == "potion_inventory":
                    if isinstance(target, int):
                        condition.current = max(condition.current, target)
                elif condition_type == "same_skill_used":
                    condition.current += amount
                elif condition_type == "dodge_count":
                    condition.current += amount
                elif condition_type == "defense_used":
                    condition.current += amount
                elif condition_type == "floors_per_hour":
                    if isinstance(target, int):
                        condition.current = max(condition.current, target)
                elif condition_type == "door_unlocked":
                    condition.current += amount
                elif condition_type == "cooking_failed":
                    condition.current += amount
                elif condition_type == "solo_playtime":
                    if isinstance(target, int):
                        condition.current = max(condition.current, target)
                elif condition_type == "fled_blocks":
                    if isinstance(target, int):
                        condition.current = max(condition.current, target)
                elif condition_type == "no_damage_streak":
                    if target == True:
                        condition.current += 1
                elif condition_type == "inventory_full":
                    if isinstance(target, int):
                        condition.current = max(condition.current, target)
                elif condition_type == "unique_food_eaten":
                    condition.current += amount
                elif condition_type == "trap_avoided":
                    condition.current += amount
                elif condition_type == "combat_moves":
                    condition.current += amount

        # 새로 달성됨
        if not was_complete and self.is_complete:
            self.is_unlocked = True
            self.unlocked_at = datetime.now()
            logger.info(f"도전과제 달성: {self.name}")
            return True

        return False


class AchievementSystem:
    """도전과제 시스템"""

    def __init__(self):
        self.achievements: Dict[str, Achievement] = {}
        self._load_achievements()

    def _load_achievements(self):
        """도전과제 데이터 로드"""
        self.achievements = self._create_funny_achievements()

    def _create_funny_achievements(self) -> Dict[str, Achievement]:
        """웃긴 도전과제들 생성"""
        achievements = {}

        # ===== 전투 관련 도전과제 =====

        # 일반 도전과제들
        achievements["first_blood"] = Achievement(
            achievement_id="first_blood",
            name="첫 번째 살인",
            description="첫 번째 적을 처치했다. 이제 살인자다!",
            category=AchievementCategory.COMBAT,
            rarity=AchievementRarity.COMMON,
            conditions=[AchievementCondition("kill_count", "any", 1)],
            reward=AchievementReward("초보 살인자", 50),
            icon="[BLOOD]"
        )

        achievements["enemy_chaser"] = Achievement(
            achievement_id="enemy_chaser",
            name="적에게 50블록 쫒기기",
            description="적에게 50블록 연속으로 쫒겼다. '왜 쫒아와!' 하며 도망쳤다.",
            category=AchievementCategory.HUMOROUS,
            rarity=AchievementRarity.UNCOMMON,
            conditions=[AchievementCondition("chased_by_enemy", "any", 50)],
            reward=AchievementReward("도망자", 75),
            icon="[RUN]"
        )

        achievements["damage_sponge"] = Achievement(
            achievement_id="damage_sponge",
            name="데미지 스폰지",
            description="한 전투에서 5000 데미지를 받았다. 스폰지처럼 데미지를 흡수했다.",
            category=AchievementCategory.MEME,
            rarity=AchievementRarity.UNCOMMON,
            conditions=[AchievementCondition("damage_taken", "any", 5000)],
            reward=AchievementReward("데미지 흡수기", 80),
            icon="[SPONGE]"
        )

        achievements["one_hit_wonder"] = Achievement(
            achievement_id="one_hit_wonder",
            name="원 힛 원더",
            description="단 한 번의 공격으로 적을 죽였다. '원 힛 원더'처럼 완벽하다!",
            category=AchievementCategory.COMBAT,
            rarity=AchievementRarity.RARE,
            conditions=[AchievementCondition("one_hit_kill", "any", 10)],
            reward=AchievementReward("원 힛 마스터", 150),
            icon="[ONEHIT]"
        )

        achievements["potion_hoarder"] = Achievement(
            achievement_id="potion_hoarder",
            name="포션 호더",
            description="인벤토리에 포션이 50개 이상 쌓였다. '포션 마니아'가 되었다.",
            category=AchievementCategory.MEME,
            rarity=AchievementRarity.RARE,
            conditions=[AchievementCondition("potion_inventory", "any", 50)],
            reward=AchievementReward("포션 마니아", 200),
            icon="[POTION]"
        )

        achievements["skill_spammer"] = Achievement(
            achievement_id="skill_spammer",
            name="스킬 스패머",
            description="한 전투에서 같은 스킬을 20번 사용했다. '스킬 버튼에 손이 붙었다!'",
            category=AchievementCategory.HUMOROUS,
            rarity=AchievementRarity.RARE,
            conditions=[AchievementCondition("same_skill_used", "any", 20)],
            reward=AchievementReward("스킬 스패머", 180),
            icon="[SPAM]"
        )

        achievements["dodge_master"] = Achievement(
            achievement_id="dodge_master",
            name="회피 마스터",
            description="한 전투에서 50번 회피했다. '나는 바람이다!'",
            category=AchievementCategory.COMBAT,
            rarity=AchievementRarity.EPIC,
            conditions=[AchievementCondition("dodge_count", "any", 50)],
            reward=AchievementReward("바람처럼", 300),
            icon="[DODGE]"
        )

        achievements["tank_mode"] = Achievement(
            achievement_id="tank_mode",
            name="탱크 모드",
            description="한 전투에서 방어만 30번 했다. '나는 벽이다!'",
            category=AchievementCategory.COMBAT,
            rarity=AchievementRarity.UNCOMMON,
            conditions=[AchievementCondition("defense_used", "any", 30)],
            reward=AchievementReward("인간 방패", 120),
            icon="[SHIELD]"
        )

        # ===== 탐험 관련 =====

        achievements["treasure_hoarder"] = Achievement(
            achievement_id="treasure_hoarder",
            name="보물 호더",
            description="보물상자를 100개 열었다. '보물 사냥꾼'이 되었다!",
            category=AchievementCategory.EXPLORATION,
            rarity=AchievementRarity.RARE,
            conditions=[AchievementCondition("chest_opened", "any", 100)],
            reward=AchievementReward("보물 사냥꾼", 250),
            icon="[CHEST]"
        )

        achievements["floor_runner"] = Achievement(
            achievement_id="floor_runner",
            name="층 러너",
            description="한 시간에 10층을 올라갔다. '층간소음 제조기'!",
            category=AchievementCategory.EXPLORATION,
            rarity=AchievementRarity.EPIC,
            conditions=[AchievementCondition("floors_per_hour", "any", 10)],
            reward=AchievementReward("층간소음 제조기", 400),
            icon="[STAIR]"
        )

        achievements["trap_expert"] = Achievement(
            achievement_id="trap_expert",
            name="함정 전문가",
            description="함정에 25번 걸렸다. '함정 디텍터'가 되었다.",
            category=AchievementCategory.HUMOROUS,
            rarity=AchievementRarity.UNCOMMON,
            conditions=[AchievementCondition("trap_triggered", "any", 25)],
            reward=AchievementReward("함정 디텍터", 100),
            icon="[TRAP]"
        )


        achievements["door_breaker"] = Achievement(
            achievement_id="door_breaker",
            name="문 부수기",
            description="잠긴 문을 50번 열었다. '문짝 따개비'가 되었다.",
            category=AchievementCategory.EXPLORATION,
            rarity=AchievementRarity.UNCOMMON,
            conditions=[AchievementCondition("door_unlocked", "any", 50)],
            reward=AchievementReward("문짝 따개비", 90),
            icon="[DOOR]"
        )

        # ===== 제작 관련 =====

        achievements["cooking_fiend"] = Achievement(
            achievement_id="cooking_fiend",
            name="요리 광인",
            description="요리를 200번 만들었다. '요리 중독자'가 되었다!",
            category=AchievementCategory.CRAFTING,
            rarity=AchievementRarity.RARE,
            conditions=[AchievementCondition("item_crafted", "food", 200)],
            reward=AchievementReward("요리 중독자", 280),
            icon="[COOK]"
        )

        achievements["alchemy_addict"] = Achievement(
            achievement_id="alchemy_addict",
            name="연금술 중독자",
            description="포션을 300번 만들었다. '연금술 광인'이 되었다!",
            category=AchievementCategory.CRAFTING,
            rarity=AchievementRarity.RARE,
            conditions=[AchievementCondition("item_crafted", "potion", 300)],
            reward=AchievementReward("연금술 광인", 320),
            icon="[ALCHEMY]"
        )

        achievements["bomb_maniac"] = Achievement(
            achievement_id="bomb_maniac",
            name="폭탄 마니아",
            description="폭탄을 100번 만들었다. '폭탄광'이 되었다!",
            category=AchievementCategory.CRAFTING,
            rarity=AchievementRarity.EPIC,
            conditions=[AchievementCondition("item_crafted", "bomb", 100)],
            reward=AchievementReward("폭탄광", 350),
            icon="[BOMB]"
        )

        achievements["failed_cook"] = Achievement(
            achievement_id="failed_cook",
            name="실패 요리사",
            description="요리가 50번 실패했다. '요리 실력은 바닥'이다.",
            category=AchievementCategory.HUMOROUS,
            rarity=AchievementRarity.UNCOMMON,
            conditions=[AchievementCondition("cooking_failed", "any", 50)],
            reward=AchievementReward("요리 실력 바닥", 85),
            icon="[FAIL]"
        )

        # ===== 소셜/멀티플레이 =====

        achievements["team_player"] = Achievement(
            achievement_id="team_player",
            name="팀 플레이어",
            description="멀티플레이에서 100번 협력했다. '진정한 팀웍'!",
            category=AchievementCategory.SOCIAL,
            rarity=AchievementRarity.RARE,
            conditions=[AchievementCondition("multiplayer_coop", "any", 100)],
            reward=AchievementReward("팀웍 마스터", 200),
            icon="[TEAM]"
        )

        achievements["lone_wolf"] = Achievement(
            achievement_id="lone_wolf",
            name="외로운 늑대",
            description="멀티플레이를 하지 않고 100시간 플레이했다. '외로운 늑대'!",
            category=AchievementCategory.SOCIAL,
            rarity=AchievementRarity.EPIC,
            conditions=[AchievementCondition("solo_playtime", "any", 100)],
            reward=AchievementReward("외로운 늑대", 450),
            icon="[WOLF]"
        )

        # ===== 오마주/레퍼런스 =====

        achievements["sakamoto_days"] = Achievement(
            achievement_id="sakamoto_days",
            name="사카모토 데이즈",
            description="7월 7일에 게임을 플레이했다. '사카모토 데이즈'의 기념일!",
            category=AchievementCategory.HOMAGE,
            rarity=AchievementRarity.RARE,
            conditions=[AchievementCondition("date_check", [date.today().replace(month=7, day=7)])],
            reward=AchievementReward("사카모토", 300),
            icon="[777]"
        )

        achievements["jenova_wrath"] = Achievement(
            achievement_id="jenova_wrath",
            name="제노바의 분노",
            description="전투에서 오직 한 가지 스킬만 사용하여 승리했다. 제노바처럼 순수한 분노!",
            category=AchievementCategory.HOMAGE,
            rarity=AchievementRarity.EPIC,
            conditions=[AchievementCondition("enemies_killed_with_skill", "single_skill_only", 1)],
            reward=AchievementReward("제노바의 후예", 400),
            icon="[JENOVA]"
        )


        # ===== 숨겨진 도전과제들 =====

        achievements["potion_addict"] = Achievement(
            achievement_id="potion_addict",
            name="포션 중독자",
            description="한 전투에서 포션을 20번 사용했다. '포션 없이는 살 수 없어!'",
            category=AchievementCategory.MEME,
            rarity=AchievementRarity.UNCOMMON,
            conditions=[AchievementCondition("potions_used", "any", 20)],
            reward=AchievementReward("포션 귀신", 125),
            icon="[ADDICT]",
            is_hidden=True,
            hint="한 전투에서 포션을 많이 사용해보세요..."
        )

        achievements["chicken_runner"] = Achievement(
            achievement_id="chicken_runner",
            name="치킨 러너",
            description="적을 피해 200블록 도망쳤다. '겁쟁이 치킨'이 되었다!",
            category=AchievementCategory.HUMOROUS,
            rarity=AchievementRarity.RARE,
            conditions=[AchievementCondition("fled_blocks", "any", 200)],
            reward=AchievementReward("겁쟁이 치킨", 275),
            icon="[CHICKEN]",
            is_hidden=True,
            hint="적을 피해 멀리 도망쳐보세요..."
        )

        achievements["no_damage_legend"] = Achievement(
            achievement_id="no_damage_legend",
            name="무적의 전설",
            description="10번 연속으로 무피해 승리를 했다. '나는 진짜 무적이다!'",
            category=AchievementCategory.COMBAT,
            rarity=AchievementRarity.LEGENDARY,
            conditions=[AchievementCondition("no_damage_streak", "any", 10)],
            reward=AchievementReward("무적의 전설", 750),
            icon="[LEGEND]",
            is_hidden=True,
            hint="데미지를 받지 않고 연속 승리해보세요..."
        )

        achievements["secret_admirer"] = Achievement(
            achievement_id="secret_admirer",
            name="비밀의 팬",
            description="게임을 100시간 플레이했다. 진정한 팬이다! 감사합니다!",
            category=AchievementCategory.HUMOROUS,
            rarity=AchievementRarity.LEGENDARY,
            conditions=[AchievementCondition("playtime_hours", "any", 100)],
            reward=AchievementReward("진정한 팬", 600),
            icon="[SECRET]",
            is_hidden=True,
            hint="오랜 시간 게임을 플레이해보세요..."
        )

        achievements["item_hoarder"] = Achievement(
            achievement_id="item_hoarder",
            name="아이템 호더",
            description="인벤토리를 99칸 가득 채웠다. '호더병'에 걸렸다!",
            category=AchievementCategory.MEME,
            rarity=AchievementRarity.EPIC,
            conditions=[AchievementCondition("inventory_full", "any", 99)],
            reward=AchievementReward("호더병 환자", 425),
            icon="[HOARD]",
            is_hidden=True,
            hint="인벤토리를 가득 채워보세요..."
        )

        achievements["speed_demon"] = Achievement(
            achievement_id="speed_demon",
            name="스피드 데몬",
            description="던전을 3턴 안에 클리어했다. '빛보다 빠르다!'",
            category=AchievementCategory.EXPLORATION,
            rarity=AchievementRarity.LEGENDARY,
            conditions=[AchievementCondition("turns_survived", "any", 3)],
            reward=AchievementReward("빛보다 빠름", 700),
            icon="[SPEED]",
            is_hidden=True,
            hint="던전을 엄청나게 빠르게 클리어해보세요..."
        )

        achievements["picky_eater"] = Achievement(
            achievement_id="picky_eater",
            name="까다로운 먹보",
            description="100가지 다른 음식을 먹었다. '요리 평론가'가 되었다!",
            category=AchievementCategory.CRAFTING,
            rarity=AchievementRarity.EPIC,
            conditions=[AchievementCondition("unique_food_eaten", "any", 100)],
            reward=AchievementReward("요리 평론가", 380),
            icon="[EATER]",
            is_hidden=True,
            hint="다양한 음식을 먹어보세요..."
        )

        achievements["trap_avoider"] = Achievement(
            achievement_id="trap_avoider",
            name="함정 회피자",
            description="함정을 50번 피했다. '함정 레이더'가 생겼다!",
            category=AchievementCategory.EXPLORATION,
            rarity=AchievementRarity.RARE,
            conditions=[AchievementCondition("trap_avoided", "any", 50)],
            reward=AchievementReward("함정 레이더", 225),
            icon="[AVOID]",
            is_hidden=True,
            hint="함정을 잘 피해보세요..."
        )


        return achievements

    def get_achievement(self, achievement_id: str) -> Optional[Achievement]:
        """특정 도전과제 조회"""
        return self.achievements.get(achievement_id)

    def get_all_achievements(self) -> List[Achievement]:
        """모든 도전과제 목록"""
        return list(self.achievements.values())

    def get_unlocked_achievements(self) -> List[Achievement]:
        """달성된 도전과제 목록"""
        return [a for a in self.achievements.values() if a.is_unlocked]

    def get_achievements_by_category(self, category: AchievementCategory) -> List[Achievement]:
        """카테고리별 도전과제 목록"""
        return [a for a in self.achievements.values() if a.category == category]

    def check_achievement(self, achievement_id: str, condition_type: str, target: Any, amount: int = 1) -> bool:
        """
        도전과제 조건 체크 및 업데이트

        Returns:
            새로 달성되었으면 True
        """
        achievement = self.get_achievement(achievement_id)
        if not achievement or achievement.is_unlocked:
            return False

        return achievement.update_condition(condition_type, target, amount)

    def check_all_achievements(self, condition_type: str, target: Any, amount: int = 1) -> List[str]:
        """
        모든 도전과제에서 조건 체크

        Returns:
            새로 달성된 도전과제 ID 목록
        """
        newly_unlocked = []

        for achievement_id, achievement in self.achievements.items():
            if not achievement.is_unlocked:
                if achievement.update_condition(condition_type, target, amount):
                    newly_unlocked.append(achievement_id)

        return newly_unlocked

    def get_completion_percentage(self) -> float:
        """전체 도전과제 달성률 (0.0-1.0)"""
        if not self.achievements:
            return 0.0

        unlocked_count = len(self.get_unlocked_achievements())
        return unlocked_count / len(self.achievements)

    def save_progress(self) -> Dict[str, Any]:
        """진행도 저장 데이터"""
        return {
            "achievements": {
                aid: {
                    "is_unlocked": a.is_unlocked,
                    "unlocked_at": a.unlocked_at.isoformat() if a.unlocked_at else None,
                    "conditions": [
                        {
                            "current": c.current,
                            "extra_data": c.extra_data
                        } for c in a.conditions
                    ]
                }
                for aid, a in self.achievements.items()
            }
        }

    def load_progress(self, data: Dict[str, Any]):
        """진행도 불러오기"""
        if "achievements" not in data:
            return

        for aid, save_data in data["achievements"].items():
            if aid in self.achievements:
                achievement = self.achievements[aid]
                achievement.is_unlocked = save_data.get("is_unlocked", False)

                if save_data.get("unlocked_at"):
                    from datetime import datetime
                    achievement.unlocked_at = datetime.fromisoformat(save_data["unlocked_at"])

                # 조건 진행도 복원
                conditions_data = save_data.get("conditions", [])
                for i, cond_data in enumerate(conditions_data):
                    if i < len(achievement.conditions):
                        achievement.conditions[i].current = cond_data.get("current", 0)
                        achievement.conditions[i].extra_data = cond_data.get("extra_data", {})
