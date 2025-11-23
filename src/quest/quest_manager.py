"""
퀘스트 시스템 (Quest System)

단기/중기 목표를 제공하는 퀘스트 관리 시스템
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import random

from src.core.logger import get_logger

logger = get_logger("quest")


class QuestType(Enum):
    """퀘스트 타입"""
    BOUNTY_HUNT = "bounty_hunt"      # 현상금 사냥
    DELIVERY = "delivery"            # 운반/수집  
    EXPLORATION = "exploration"      # 탐험
    BOSS_HUNT = "boss_hunt"          # 보스 토벌
    SURVIVAL = "survival"            # 생존 (X턴 생존)
    SPEED_RUN = "speed_run"          # 속도 도전 (X턴 안에 층 도달)
    COLLECTION = "collection"        # 컬렉션 (다양한 아이템 수집)
    COOKING_QUEST = "cooking_quest"  # 요리 퀘스트
    ALCHEMY_QUEST = "alchemy_quest"  # 연금술 퀘스트
    NO_DAMAGE = "no_damage"          # 무피해 클리어


class QuestDifficulty(Enum):
    """퀘스트 난이도"""
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    LEGENDARY = "legendary"


@dataclass
class QuestObjective:
    """퀘스트 목표"""
    description: str
    target: str          # 대상 (적 ID, 아이템 ID, 층 번호 등)
    current: int = 0     # 현재 진행도
    required: int = 1    # 요구량
    
    @property
    def is_complete(self) -> bool:
        """완료 여부"""
        return self.current >= self.required
    
    @property
    def progress_text(self) -> str:
        """진행률 텍스트"""
        return f"{self.current}/{self.required}"


@dataclass
class QuestReward:
    """퀘스트 보상"""
    gold: int = 0
    experience: int = 0
    items: List[str] = field(default_factory=list)  # item_id 리스트
    star_fragments: int = 0  # 별의 파편
    reputation: int = 0
    
    def __str__(self):
        rewards = []
        if self.gold > 0:
            rewards.append(f"골드 {self.gold}")
        if self.experience > 0:
            rewards.append(f"경험치 {self.experience}")
        if self.star_fragments > 0:
            rewards.append(f"별의 파편 {self.star_fragments}")
        if self.items:
            rewards.append(f"아이템 {len(self.items)}개")
        return ", ".join(rewards) if rewards else "없음"


@dataclass
class Quest:
    """퀘스트"""
    quest_id: str
    name: str
    description: str
    quest_type: QuestType
    difficulty: QuestDifficulty
    objectives: List[QuestObjective]
    reward: QuestReward
    is_active: bool = False
    is_complete: bool = False
    
    @property
    def all_objectives_complete(self) -> bool:
        """모든 목표 완료 여부"""
        return all(obj.is_complete for obj in self.objectives)
    
    def update_progress(self, target: str, amount: int = 1) -> bool:
        """
        진행도 업데이트
        
        Args:
            target: 업데이트할 대상
            amount: 증가량
            
        Returns:
            목표 달성 여부
        """
        updated = False
        for objective in self.objectives:
            if objective.target == target and not objective.is_complete:
                objective.current = min(objective.current + amount, objective.required)
                updated = True
                logger.info(f"퀘스트 '{self.name}' 진행: {objective.description} ({objective.progress_text})")
        
        # 모든 목표 완료 확인
        if self.all_objectives_complete and not self.is_complete:
            self.is_complete = True
            logger.info(f"퀘스트 '{self.name}' 완료!")
        
        return updated


class QuestDatabase:
    """퀘스트 데이터베이스"""
    
    @staticmethod
    def generate_bounty_quest(player_level: int) -> Quest:
        """현상금 퀘스트 생성"""
        # 플레이어 레벨에 따른 적 선택
        enemy_types = {
            1: ["goblin", "slime"],
            5: ["orc", "wolf", "skeleton"],
            10: ["ogre", "wyvern", "vampire"],
            15: ["dragon", "lich", "death_knight"]
        }
        
        # 적절한 난이도 범위 선택
        for level_threshold in sorted(enemy_types.keys(), reverse=True):
            if player_level >= level_threshold:
                enemies = enemy_types[level_threshold]
                break
        else:
            enemies = enemy_types[1]
        
        enemy = random.choice(enemies)
        count = random.randint(3, 10)
        
        # 난이도 결정
        if count <= 3:
            difficulty = QuestDifficulty.EASY
        elif count <= 6:
            difficulty = QuestDifficulty.NORMAL
        else:
            difficulty = QuestDifficulty.HARD
        
        # 보상 계산
        base_reward = player_level * 10
        reward = QuestReward(
            gold=(base_reward * count) * 5,  # 5배 증가
            experience=(base_reward * 2 * count) * 5,  # 5배 증가
            star_fragments=(count // 3) * 20  # 20배 증가
        )
        
        return Quest(
            quest_id=f"bounty_{enemy}_{random.randint(1000, 9999)}",
            name=f"{enemy.title()} 토벌",
            description=f"{count}마리의 {enemy}를 처치하십시오.",
            quest_type=QuestType.BOUNTY_HUNT,
            difficulty=difficulty,
            objectives=[
                QuestObjective(
                    description=f"{enemy} 처치",
                    target=enemy,
                    required=count
                )
            ],
            reward=reward
        )
    
    @staticmethod
    def generate_delivery_quest(player_level: int) -> Quest:
        """운반 퀘스트 생성"""
        # 수집 대상 아이템
        items = [
            ("wood", "목재", 5, 10),
            ("stone", "석재", 5, 10),
            ("iron_ore", "철광석", 3, 8),
            ("magic_herb", "마법 허브", 2, 5),
            ("mana_blossom", "마력꽃", 1, 3),
        ]
        
        item_id, item_name, min_count, max_count = random.choice(items)
        count = random.randint(min_count, max_count)
        
        # 난이도
        if count <= 3:
            difficulty = QuestDifficulty.EASY
        elif count <= 6:
            difficulty = QuestDifficulty.NORMAL
        else:
            difficulty = QuestDifficulty.HARD
        
        # 보상
        base_reward = player_level * 15
        reward = QuestReward(
            gold=(base_reward * count) * 5,  # 5배 증가
            star_fragments=(count // 2) * 20,  # 20배 증가
            items=["greater_health_potion"] if difficulty == QuestDifficulty.HARD else []  # 아이템은 그대로
        )
        
        return Quest(
            quest_id=f"delivery_{item_id}_{random.randint(1000, 9999)}",
            name=f"{item_name} 수집",
            description=f"{count}개의 {item_name}를 수집하십시오.",
            quest_type=QuestType.DELIVERY,
            difficulty=difficulty,
            objectives=[
                QuestObjective(
                    description=f"{item_name} 수집",
                    target=item_id,
                    required=count
                )
            ],
            reward=reward
        )
    
    @staticmethod
    def generate_exploration_quest(player_level: int) -> Quest:
        """탐험 퀘스트 생성"""
        target_floor = (player_level // 3 + 1) * 3  # 플레이어 레벨에 맞는 층
        
        # 난이도
        if target_floor <= 3:
            difficulty = QuestDifficulty.EASY
        elif target_floor <= 7:
            difficulty = QuestDifficulty.NORMAL
        elif target_floor <= 10:
            difficulty = QuestDifficulty.HARD
        else:
            difficulty = QuestDifficulty.LEGENDARY
        
        # 보상
        base_reward = target_floor * 50
        reward = QuestReward(
            gold=base_reward * 5,  # 5배 증가
            experience=(base_reward * 3) * 5,  # 5배 증가
            star_fragments=(target_floor // 2) * 20  # 20배 증가
        )
        
        return Quest(
            quest_id=f"explore_floor_{target_floor}_{random.randint(1000, 9999)}",
            name=f"{target_floor}층 도달",
            description=f"던전 {target_floor}층에 도달하십시오.",
            quest_type=QuestType.EXPLORATION,
            difficulty=difficulty,
            objectives=[
                QuestObjective(
                    description=f"{target_floor}층 도달",
                    target=f"floor_{target_floor}",
                    required=1
                )
            ],
            reward=reward
        )
    
    @staticmethod
    def generate_boss_hunt_quest(player_level: int) -> Quest:
        """보스 토벌 퀘스트"""
        bosses = ["boss_dragon", "boss_lich", "boss_demon_lord", "boss_hydra"]
        boss = random.choice(bosses)
        
        reward = QuestReward(
            gold=(player_level * 100) * 5,  # 5배 증가
            experience=(player_level * 50) * 5,  # 5배 증가
            star_fragments=10 * 20,  # 20배 증가
            items=["stardust", "philosophers_stone_fragment"]  # 아이템은 그대로
        )
        
        return Quest(
            quest_id=f"boss_{boss}_{random.randint(1000, 9999)}",
            name=f"{boss.replace('_', ' ').title()} 토벌",
            description=f"강력한 보스 {boss}를 처치하십시오.",
            quest_type=QuestType.BOSS_HUNT,
            difficulty=QuestDifficulty.LEGENDARY,
            objectives=[QuestObjective(description=f"{boss} 처치", target=boss, required=1)],
            reward=reward
        )
    
    @staticmethod
    def generate_survival_quest(player_level: int) -> Quest:
        """생존 퀘스트"""
        turns = random.randint(50, 100)
        
        reward = QuestReward(
            gold=(turns * 10) * 5,  # 5배 증가
            experience=(turns * 5) * 5,  # 5배 증가
            star_fragments=(turns // 20) * 20  # 20배 증가
        )
        
        return Quest(
            quest_id=f"survival_{turns}_{random.randint(1000, 9999)}",
            name=f"{turns}턴 생존",
            description=f"던전에서 {turns}턴 동안 생존하십시오.",
            quest_type=QuestType.SURVIVAL,
            difficulty=QuestDifficulty.HARD,
            objectives=[QuestObjective(description=f"{turns}턴 생존", target="survival_turns", required=turns)],
            reward=reward
        )
    
    @staticmethod
    def generate_speed_run_quest(player_level: int) -> Quest:
        """속도 도전 퀘스트"""
        target_floor = player_level // 2 + 3
        time_limit = target_floor * 10
        
        reward = QuestReward(
            gold=(target_floor * 150) * 5,  # 5배 증가
            experience=(target_floor * 100) * 5,  # 5배 증가
            star_fragments=target_floor * 20  # 20배 증가
        )
        
        return Quest(
            quest_id=f"speedrun_{target_floor}_{random.randint(1000, 9999)}",
            name=f"{target_floor}층 속도 도전",
            description=f"{time_limit}턴 안에 {target_floor}층에 도달하십시오.",
            quest_type=QuestType.SPEED_RUN,
            difficulty=QuestDifficulty.HARD,
            objectives=[
                QuestObjective(description=f"{target_floor}층 도달", target=f"floor_{target_floor}", required=1)
            ],
            reward=reward
        )
    
    @staticmethod
    def generate_collection_quest(player_level: int) -> Quest:
        """컬렉션 퀘스트"""
        items = [
            ("mithril_ore", "미스릴 광석", 2),
            ("crystal_shard", "수정 파편", 3),
            ("ether", "에테르", 2),
            ("dragon_bone", "용의 뼈", 1)
        ]
        
        selected_items = random.sample(items, min(3, len(items)))
        
        objectives = [
            QuestObjective(description=f"{name} 수집", target=item_id, required=count)
            for item_id, name, count in selected_items
        ]
        
        reward = QuestReward(
            gold=(player_level * 80) * 5,  # 5배 증가
            experience=(player_level * 40) * 5,  # 5배 증가
            star_fragments=5 * 20,  # 20배 증가
            items=["greater_mana_potion"]  # 아이템은 그대로
        )
        
        return Quest(
            quest_id=f"collection_{random.randint(1000, 9999)}",
            name="희귀 자원 수집",
            description="지정된 희귀 자원들을 모두 수집하십시오.",
            quest_type=QuestType.COLLECTION,
            difficulty=QuestDifficulty.HARD,
            objectives=objectives,
            reward=reward
        )
    
    @staticmethod
    def generate_cooking_quest(player_level: int) -> Quest:
        """요리 퀘스트"""
        dishes = [
            ("apple_pie", "애플 파이", 2),
            ("monster_stew", "몬스터 스튜", 3)
        ]
        
        dish_id, dish_name, count = random.choice(dishes)
        
        reward = QuestReward(
            gold=(player_level * 50) * 5,  # 5배 증가
            star_fragments=3 * 20  # 20배 증가
        )
        
        return Quest(
            quest_id=f"cooking_{dish_id}_{random.randint(1000, 9999)}",
            name=f"{dish_name} 요리",
            description=f"{count}개의 {dish_name}를 만드십시오.",
            quest_type=QuestType.COOKING_QUEST,
            difficulty=QuestDifficulty.NORMAL,
            objectives=[QuestObjective(description=f"{dish_name} 제작", target=dish_id, required=count)],
            reward=reward
        )
    
    @staticmethod
    def generate_alchemy_quest(player_level: int) -> Quest:
        """연금술 퀘스트"""
        potions = [
            ("greater_health_potion", "대형 체력 포션", 3),
            ("fire_bomb", "화염 폭탄", 5)
        ]
        
        potion_id, potion_name, count = random.choice(potions)
        
        reward = QuestReward(
            gold=(player_level * 60) * 5,  # 5배 증가
            star_fragments=4 * 20  # 20배 증가
        )
        
        return Quest(
            quest_id=f"alchemy_{potion_id}_{random.randint(1000, 9999)}",
            name=f"{potion_name} 제작",
            description=f"{count}개의 {potion_name}를 제작하십시오.",
            quest_type=QuestType.ALCHEMY_QUEST,
            difficulty=QuestDifficulty.NORMAL,
            objectives=[QuestObjective(description=f"{potion_name} 제작", target=potion_id, required=count)],
            reward=reward
        )
    
    @staticmethod
    def generate_no_damage_quest(player_level: int) -> Quest:
        """무피해 클리어 퀘스트"""
        target_floor = player_level // 3 + 1
        
        reward = QuestReward(
            gold=(target_floor * 200) * 5,  # 5배 증가
            experience=(target_floor * 150) * 5,  # 5배 증가
            star_fragments=(target_floor * 2) * 20  # 20배 증가
        )
        
        return Quest(
            quest_id=f"nodamage_{target_floor}_{random.randint(1000, 9999)}",
            name=f"{target_floor}층 무피해 클리어",
            description=f"피해를 받지 않고 {target_floor}층에 도달하십시오.",
            quest_type=QuestType.NO_DAMAGE,
            difficulty=QuestDifficulty.LEGENDARY,
            objectives=[
                QuestObjective(description=f"{target_floor}층 도달", target=f"floor_{target_floor}", required=1)
            ],
            reward=reward
        )


class QuestManager:
    """퀘스트 관리자"""
    
    def __init__(self):
        self.available_quests: List[Quest] = []  # 수락 가능한 퀘스트
        self.active_quests: List[Quest] = []     # 진행 중인 퀘스트
        self.completed_quests: List[Quest] = []  # 완료된 퀘스트
        self.max_active_quests = 3
    
    def refresh_quests(self, player_level: int, count: int = 5):
        """
        퀘스트 목록 갱신 (기존 목록 초기화 후 재생성)
        
        Args:
            player_level: 플레이어 레벨
            count: 생성할 퀘스트 수
        """
        self.available_quests.clear()
        self.generate_quests(player_level, count)
        logger.info(f"퀘스트 목록 갱신 완료 (레벨 {player_level})")

    def generate_quests(self, player_level: int, count: int = 5):
        """
        퀘스트 생성
        
        Args:
            player_level: 플레이어 레벨
            count: 생성할 퀘스트 수
        """
        # 기존 목록 유지 (refresh_quests 사용 시만 초기화)
        # self.available_quests.clear()  <-- 제거됨 (refresh_quests로 이동)
        
        # 각 타입별로 퀘스트 생성 (가중치 기반)
        quest_generators = [
            (QuestType.BOUNTY_HUNT, QuestDatabase.generate_bounty_quest, 30),
            (QuestType.DELIVERY, QuestDatabase.generate_delivery_quest, 25),
            (QuestType.EXPLORATION, QuestDatabase.generate_exploration_quest, 20),
            (QuestType.BOSS_HUNT, QuestDatabase.generate_boss_hunt_quest, 5),
            (QuestType.SURVIVAL, QuestDatabase.generate_survival_quest, 10),
            (QuestType.SPEED_RUN, QuestDatabase.generate_speed_run_quest, 8),
            (QuestType.COLLECTION, QuestDatabase.generate_collection_quest, 12),
            (QuestType.COOKING_QUEST, QuestDatabase.generate_cooking_quest, 10),
            (QuestType.ALCHEMY_QUEST, QuestDatabase.generate_alchemy_quest, 10),
            (QuestType.NO_DAMAGE, QuestDatabase.generate_no_damage_quest, 3)
        ]
        
        for _ in range(count):
            quest_type, generator, weight = random.choices(
                quest_generators,
                weights=[w for _, _, w in quest_generators]
            )[0]
            
            quest = generator(player_level)
            
            self.available_quests.append(quest)
        
        logger.info(f"{count}개의 퀘스트 생성 완료 (플레이어 레벨: {player_level})")
    
    def accept_quest(self, quest_id: str) -> bool:
        """
        퀘스트 수락
        
        Args:
            quest_id: 퀘스트 ID
            
        Returns:
            성공 여부
        """
        if len(self.active_quests) >= self.max_active_quests:
            logger.warning("활성 퀘스트가 가득 찼습니다.")
            return False
        
        for quest in self.available_quests:
            if quest.quest_id == quest_id:
                quest.is_active = True
                self.active_quests.append(quest)
                self.available_quests.remove(quest)
                logger.info(f"퀘스트 수락: {quest.name}")
                return True
        
        return False
    
    def update_progress(self, event_type: str, target: str, amount: int = 1):
        """
        모든 활성 퀘스트의 진행도 업데이트
        
        Args:
            event_type: 이벤트 타입 ("enemy_killed", "item_collected", "floor_reached")
            target: 대상 (적 ID, 아이템 ID, 층 번호 등)
            amount: 수량
        """
        for quest in self.active_quests:
            quest.update_progress(target, amount)
    
    def complete_quest(self, quest_id: str, player: Any) -> bool:
        """
        퀘스트 완료 및 보상 지급
        
        Args:
            quest_id: 퀘스트 ID
            player: 플레이어 객체
            
        Returns:
            성공 여부
        """
        for quest in self.active_quests:
            if quest.quest_id == quest_id and quest.is_complete:
                # 보상 지급
                player.gold += quest.reward.gold
                player.experience += quest.reward.experience
                
                # 아이템 보상
                for item_id in quest.reward.items:
                    from src.gathering.ingredient import IngredientDatabase
                    item = IngredientDatabase.get_ingredient(item_id)
                    if item:
                        player.add_item(item)
                
                # 별의 파편은 별도 관리 필요 (TownManager 등)
                
                # 퀘스트 이동
                self.active_quests.remove(quest)
                self.completed_quests.append(quest)
                
                logger.info(f"퀘스트 완료: {quest.name}")
                logger.info(f"보상: {quest.reward}")
                return True
        
        return False
    
    def get_active_quests(self) -> List[Quest]:
        """활성 퀘스트 목록"""
        return self.active_quests.copy()
    
    def get_available_quests(self) -> List[Quest]:
        """수락 가능한 퀘스트 목록"""
        return self.available_quests.copy()
    
    def to_dict(self) -> Dict[str, Any]:
        """저장용 딕셔너리 변환"""
        return {
            "active_quests": [self._quest_to_dict(q) for q in self.active_quests],
            "available_quests": [self._quest_to_dict(q) for q in self.available_quests],
            "completed_quests": [self._quest_to_dict(q) for q in self.completed_quests]
        }
    
    def _quest_to_dict(self, quest: Quest) -> Dict[str, Any]:
        """퀘스트를 딕셔너리로 변환"""
        return {
            "quest_id": quest.quest_id,
            "name": quest.name,
            "description": quest.description,
            "quest_type": quest.quest_type.value,
            "difficulty": quest.difficulty.value,
            "objectives": [
                {
                    "description": obj.description,
                    "target": obj.target,
                    "current": obj.current,
                    "required": obj.required
                }
                for obj in quest.objectives
            ],
            "reward": {
                "gold": quest.reward.gold,
                "experience": quest.reward.experience,
                "items": quest.reward.items,
                "star_fragments": quest.reward.star_fragments
            },
            "is_active": quest.is_active,
            "is_complete": quest.is_complete
        }


# 전역 인스턴스
_quest_manager = QuestManager()

def get_quest_manager() -> QuestManager:
    return _quest_manager
