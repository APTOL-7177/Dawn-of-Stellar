"""
튜토리얼 스텝 - 개별 튜토리얼 단계
"""

from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum


class CompletionType(Enum):
    """완료 조건 타입"""
    POSITION_REACHED = "position_reached"  # 특정 위치 도달
    NPC_INTERACTION = "npc_interaction"  # NPC와 상호작용
    COMBAT_VICTORY = "combat_victory"  # 전투 승리
    ACTION_COUNT = "action_count"  # 특정 횟수 행동
    SKILL_USAGE_VARIETY = "skill_usage_variety"  # 다양한 스킬 사용
    COMBAT_ACTION_SEQUENCE = "combat_action_sequence"  # 특정 행동 순서
    MENU_OPENED = "menu_opened"  # 메뉴 열기
    ITEM_USED = "item_used"  # 아이템 사용
    EQUIPMENT_CHANGED = "equipment_changed"  # 장비 변경


@dataclass
class TutorialMessage:
    """튜토리얼 메시지"""
    text: str
    color: Tuple[int, int, int] = (255, 255, 255)
    pause: float = 1.0
    effect: str = "typing"  # typing, fade_in, flash, glitch


@dataclass
class TutorialHint:
    """튜토리얼 힌트"""
    text: str
    trigger_time: float  # 초 단위


@dataclass
class UIHighlight:
    """UI 강조 요소"""
    element: str
    color: Tuple[int, int, int] = (255, 255, 0)
    pulse: bool = False
    description: str = ""
    position: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None


@dataclass
class CompletionCondition:
    """완료 조건"""
    type: CompletionType
    params: Dict[str, Any]
    message: str


@dataclass
class TutorialReward:
    """튜토리얼 보상"""
    exp: int = 0
    gold: int = 0
    items: List[str] = None
    message: str = ""

    def __post_init__(self):
        if self.items is None:
            self.items = []


class TutorialStep:
    """
    튜토리얼 단계

    각 튜토리얼 단계는 독립적으로 실행 가능하며,
    완료 조건을 만족하면 다음 단계로 진행됩니다.
    """

    def __init__(
        self,
        tutorial_id: str,
        title: str,
        order: int,
        category: str,
        description: str,
        objective: str,
        messages: List[TutorialMessage],
        completion_condition: CompletionCondition,
        hints: List[TutorialHint],
        ui_highlights: List[UIHighlight],
        rewards: TutorialReward,
        next_step: Optional[str] = None,
        enabled: bool = True,
        skippable: bool = True
    ):
        self.id = tutorial_id
        self.title = title
        self.order = order
        self.category = category
        self.description = description
        self.objective = objective
        self.messages = messages
        self.completion_condition = completion_condition
        self.hints = hints
        self.ui_highlights = ui_highlights
        self.rewards = rewards
        self.next_step = next_step
        self.enabled = enabled
        self.skippable = skippable

        # 상태
        self.is_active = False
        self.is_completed = False
        self.start_time = 0.0
        self.elapsed_time = 0.0
        self.shown_hints: List[int] = []
        self.progress_data: Dict[str, Any] = {}

    def start(self) -> None:
        """튜토리얼 시작"""
        self.is_active = True
        self.is_completed = False
        self.start_time = 0.0
        self.elapsed_time = 0.0
        self.shown_hints = []
        self.progress_data = {}

    def update(self, delta_time: float) -> None:
        """튜토리얼 업데이트"""
        if not self.is_active:
            return

        self.elapsed_time += delta_time

    def check_completion(self, game_state: Dict[str, Any]) -> bool:
        """
        완료 조건 확인

        Args:
            game_state: 현재 게임 상태

        Returns:
            완료 여부
        """
        if not self.is_active:
            return False

        condition_type = self.completion_condition.type
        params = self.completion_condition.params

        # 완료 조건 타입별 체크
        if condition_type == CompletionType.POSITION_REACHED:
            return self._check_position_reached(game_state, params)
        elif condition_type == CompletionType.NPC_INTERACTION:
            return self._check_npc_interaction(game_state, params)
        elif condition_type == CompletionType.COMBAT_VICTORY:
            return self._check_combat_victory(game_state, params)
        elif condition_type == CompletionType.ACTION_COUNT:
            return self._check_action_count(game_state, params)
        elif condition_type == CompletionType.SKILL_USAGE_VARIETY:
            return self._check_skill_usage_variety(game_state, params)
        elif condition_type == CompletionType.COMBAT_ACTION_SEQUENCE:
            return self._check_combat_action_sequence(game_state, params)

        return False

    def _check_position_reached(
        self, game_state: Dict[str, Any], params: Dict[str, Any]
    ) -> bool:
        """위치 도달 확인"""
        player_pos = game_state.get("player_position")
        if not player_pos:
            return False

        target_x = params.get("target_x", 0)
        target_y = params.get("target_y", 0)
        radius = params.get("radius", 0)

        distance = abs(player_pos[0] - target_x) + abs(player_pos[1] - target_y)
        return distance <= radius

    def _check_npc_interaction(
        self, game_state: Dict[str, Any], params: Dict[str, Any]
    ) -> bool:
        """NPC 상호작용 확인"""
        interacted_npcs = game_state.get("interacted_npcs", [])
        target_npc = params.get("npc_id")
        return target_npc in interacted_npcs

    def _check_combat_victory(
        self, game_state: Dict[str, Any], params: Dict[str, Any]
    ) -> bool:
        """전투 승리 확인"""
        combat_result = game_state.get("last_combat_result")
        if not combat_result or combat_result != "victory":
            return False

        required_count = params.get("enemy_count", 1)
        defeated_count = game_state.get("defeated_enemies", 0)
        return defeated_count >= required_count

    def _check_action_count(
        self, game_state: Dict[str, Any], params: Dict[str, Any]
    ) -> bool:
        """행동 횟수 확인"""
        required_actions = params.get("required_actions", 1)
        action_count = game_state.get("action_count", 0)
        return action_count >= required_actions

    def _check_skill_usage_variety(
        self, game_state: Dict[str, Any], params: Dict[str, Any]
    ) -> bool:
        """다양한 스킬 사용 확인"""
        required_types = set(params.get("required_skill_types", []))
        used_skill_types = set(game_state.get("used_skill_types", []))
        return required_types.issubset(used_skill_types)

    def _check_combat_action_sequence(
        self, game_state: Dict[str, Any], params: Dict[str, Any]
    ) -> bool:
        """전투 행동 순서 확인"""
        required_sequence = params.get("required_sequence", [])
        action_sequence = game_state.get("action_sequence", [])

        if len(action_sequence) < len(required_sequence):
            return False

        # 순서대로 매칭되는지 확인
        for i, required in enumerate(required_sequence):
            if i >= len(action_sequence):
                return False
            if action_sequence[i].get("action") != required.get("action"):
                return False

        return True

    def get_current_hints(self) -> List[TutorialHint]:
        """현재 표시할 힌트 목록"""
        current_hints = []
        for i, hint in enumerate(self.hints):
            if i not in self.shown_hints and self.elapsed_time >= hint.trigger_time:
                current_hints.append(hint)
                self.shown_hints.append(i)
        return current_hints

    def complete(self) -> TutorialReward:
        """튜토리얼 완료"""
        self.is_active = False
        self.is_completed = True
        return self.rewards

    def skip(self) -> None:
        """튜토리얼 건너뛰기"""
        if self.skippable:
            self.is_active = False
            self.is_completed = True

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (저장용)"""
        return {
            "id": self.id,
            "is_completed": self.is_completed,
            "progress_data": self.progress_data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], full_data: Optional[Dict[str, Any]] = None) -> "TutorialStep":
        """
        딕셔너리에서 로드 (저장된 데이터 복원용)

        Args:
            data: 저장된 진행 상태 데이터
            full_data: YAML에서 로드한 전체 튜토리얼 데이터

        Returns:
            복원된 TutorialStep 인스턴스
        """
        if full_data is None:
            # 저장된 ID만으로는 완전한 복원 불가
            # TutorialManager에서 YAML 파일을 다시 로드해야 함
            raise ValueError("full_data가 필요합니다. TutorialManager.load_tutorials()를 사용하세요.")

        # 메시지 파싱
        messages = []
        for msg_data in full_data.get("messages", []):
            messages.append(TutorialMessage(
                text=msg_data.get("text", ""),
                color=tuple(msg_data.get("color", [255, 255, 255])),
                pause=msg_data.get("pause", 1.0),
                effect=msg_data.get("effect", "typing")
            ))

        # 힌트 파싱
        hints = []
        for hint_data in full_data.get("hints", []):
            hints.append(TutorialHint(
                text=hint_data.get("text", ""),
                trigger_time=hint_data.get("trigger_time", 10.0)
            ))

        # UI 강조 파싱
        ui_highlights = []
        for ui_data in full_data.get("ui_highlights", []):
            ui_highlights.append(UIHighlight(
                element=ui_data.get("element", ""),
                color=tuple(ui_data.get("color", [255, 255, 0])),
                pulse=ui_data.get("pulse", False),
                description=ui_data.get("description", ""),
                position=ui_data.get("position"),
                x=ui_data.get("x"),
                y=ui_data.get("y")
            ))

        # 완료 조건 파싱
        cond_data = full_data.get("completion_condition", {})
        completion_condition = CompletionCondition(
            type=CompletionType(cond_data.get("type", "position_reached")),
            params=cond_data,
            message=cond_data.get("message", "완료!")
        )

        # 보상 파싱
        reward_data = full_data.get("rewards", {})
        rewards = TutorialReward(
            exp=reward_data.get("exp", 0),
            gold=reward_data.get("gold", 0),
            items=reward_data.get("items", []),
            message=reward_data.get("message", "")
        )

        # 튜토리얼 스텝 생성
        step = cls(
            tutorial_id=full_data.get("id", ""),
            title=full_data.get("title", ""),
            order=full_data.get("order", 0),
            category=full_data.get("category", ""),
            description=full_data.get("description", ""),
            objective=full_data.get("objective", ""),
            messages=messages,
            completion_condition=completion_condition,
            hints=hints,
            ui_highlights=ui_highlights,
            rewards=rewards,
            next_step=full_data.get("next_step"),
            enabled=full_data.get("enabled", True),
            skippable=full_data.get("skippable", True)
        )

        # 저장된 진행 상태 복원
        step.is_completed = data.get("is_completed", False)
        step.progress_data = data.get("progress_data", {})

        return step
