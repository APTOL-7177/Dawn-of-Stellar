"""
튜토리얼 매니저 - 튜토리얼 시스템 총괄 관리
"""

import os
import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path

from src.tutorial.tutorial_step import (
    TutorialStep,
    TutorialMessage,
    TutorialHint,
    UIHighlight,
    CompletionCondition,
    TutorialReward,
    CompletionType
)
from src.core.event_bus import event_bus
from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.SYSTEM)


class TutorialManager:
    """
    튜토리얼 매니저

    모든 튜토리얼을 관리하고, 진행 상태를 추적하며,
    이벤트를 통해 게임과 통합됩니다.
    """

    def __init__(self, data_dir: str = "data/tutorials"):
        self.data_dir = Path(data_dir)
        self.tutorials: Dict[str, TutorialStep] = {}
        self.tutorial_order: List[str] = []
        self.config: Dict[str, Any] = {}

        # 상태
        self.is_active = False
        self.current_step: Optional[TutorialStep] = None
        self.completed_tutorials: List[str] = []
        self.skipped = False

        # 게임 상태 추적
        self.game_state: Dict[str, Any] = {
            "player_position": (0, 0),
            "interacted_npcs": [],
            "last_combat_result": None,
            "defeated_enemies": 0,
            "action_count": 0,
            "used_skill_types": [],
            "action_sequence": [],
        }

        # 이벤트 구독
        self._subscribe_to_events()

        logger.info("튜토리얼 매니저 초기화")

    def load_tutorials(self) -> None:
        """튜토리얼 데이터 로드"""
        try:
            # 설정 파일 로드
            config_path = self.data_dir / "tutorial_config.yaml"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f)
                    self.tutorial_order = self.config.get("tutorial_order", [])
                    logger.info(f"튜토리얼 설정 로드 완료: {len(self.tutorial_order)}개 단계")

            # 개별 튜토리얼 파일 로드
            for tutorial_file in sorted(self.data_dir.glob("*.yaml")):
                if tutorial_file.name == "tutorial_config.yaml":
                    continue

                try:
                    tutorial = self._load_tutorial_file(tutorial_file)
                    if tutorial:
                        self.tutorials[tutorial.id] = tutorial
                        logger.debug(f"튜토리얼 로드: {tutorial.id}")
                except Exception as e:
                    logger.error(f"튜토리얼 파일 로드 실패 ({tutorial_file}): {e}")

            logger.info(f"총 {len(self.tutorials)}개 튜토리얼 로드 완료")

        except Exception as e:
            logger.error(f"튜토리얼 로드 중 오류: {e}")

    def _load_tutorial_file(self, file_path: Path) -> Optional[TutorialStep]:
        """개별 튜토리얼 파일 로드"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            # 메시지 파싱
            messages = []
            for msg_data in data.get("messages", []):
                messages.append(TutorialMessage(
                    text=msg_data.get("text", ""),
                    color=tuple(msg_data.get("color", [255, 255, 255])),
                    pause=msg_data.get("pause", 1.0),
                    effect=msg_data.get("effect", "typing")
                ))

            # 힌트 파싱
            hints = []
            for hint_data in data.get("hints", []):
                hints.append(TutorialHint(
                    text=hint_data.get("text", ""),
                    trigger_time=hint_data.get("trigger_time", 10.0)
                ))

            # UI 강조 파싱
            ui_highlights = []
            for ui_data in data.get("ui_highlights", []):
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
            cond_data = data.get("completion_condition", {})
            completion_condition = CompletionCondition(
                type=CompletionType(cond_data.get("type", "position_reached")),
                params=cond_data,
                message=cond_data.get("message", "완료!")
            )

            # 보상 파싱
            reward_data = data.get("rewards", {})
            rewards = TutorialReward(
                exp=reward_data.get("exp", 0),
                gold=reward_data.get("gold", 0),
                items=reward_data.get("items", []),
                message=reward_data.get("message", "")
            )

            # 튜토리얼 스텝 생성
            return TutorialStep(
                tutorial_id=data.get("id", ""),
                title=data.get("title", ""),
                order=data.get("order", 0),
                category=data.get("category", ""),
                description=data.get("description", ""),
                objective=data.get("objective", ""),
                messages=messages,
                completion_condition=completion_condition,
                hints=hints,
                ui_highlights=ui_highlights,
                rewards=rewards,
                next_step=data.get("next_step"),
                enabled=data.get("enabled", True),
                skippable=data.get("skippable", True)
            )

        except Exception as e:
            logger.error(f"튜토리얼 파일 파싱 오류 ({file_path}): {e}")
            return None

    def start_tutorial(self, tutorial_id: Optional[str] = None) -> bool:
        """
        튜토리얼 시작

        Args:
            tutorial_id: 시작할 튜토리얼 ID (None이면 첫 번째 단계)

        Returns:
            시작 성공 여부
        """
        if not self.config.get("global", {}).get("enabled", True):
            logger.info("튜토리얼 시스템이 비활성화되어 있습니다.")
            return False

        # 시작할 튜토리얼 결정
        if tutorial_id is None:
            if not self.tutorial_order:
                logger.warning("튜토리얼 순서가 설정되지 않았습니다.")
                return False
            tutorial_id = self.tutorial_order[0]

        # 튜토리얼 가져오기
        tutorial = self.tutorials.get(tutorial_id)
        if not tutorial:
            logger.warning(f"튜토리얼을 찾을 수 없습니다: {tutorial_id}")
            return False

        if not tutorial.enabled:
            logger.info(f"튜토리얼이 비활성화되어 있습니다: {tutorial_id}")
            return False

        # 현재 튜토리얼 시작
        self.is_active = True
        self.current_step = tutorial
        self.current_step.start()

        # 이벤트 발행
        event_bus.publish("tutorial.started", {
            "tutorial_id": tutorial_id,
            "title": tutorial.title
        })

        logger.info(f"튜토리얼 시작: {tutorial_id} - {tutorial.title}")
        return True

    def update(self, delta_time: float) -> None:
        """튜토리얼 업데이트"""
        if not self.is_active or not self.current_step:
            return

        # 현재 단계 업데이트
        self.current_step.update(delta_time)

        # 완료 조건 확인
        if self.current_step.check_completion(self.game_state):
            self._complete_current_step()

    def _complete_current_step(self) -> None:
        """현재 단계 완료 처리"""
        if not self.current_step:
            return

        # 보상 지급
        rewards = self.current_step.complete()

        # 완료 목록에 추가
        self.completed_tutorials.append(self.current_step.id)

        # 이벤트 발행
        event_bus.publish("tutorial.step_complete", {
            "tutorial_id": self.current_step.id,
            "title": self.current_step.title,
            "rewards": {
                "exp": rewards.exp,
                "gold": rewards.gold,
                "items": rewards.items
            }
        })

        logger.info(f"튜토리얼 완료: {self.current_step.id}")

        # 다음 단계로 진행
        next_step_id = self.current_step.next_step
        self.current_step = None

        if next_step_id:
            self.start_tutorial(next_step_id)
        else:
            # 모든 튜토리얼 완료
            self._complete_all_tutorials()

    def _complete_all_tutorials(self) -> None:
        """모든 튜토리얼 완료"""
        self.is_active = False

        event_bus.publish("tutorial.all_complete", {
            "completed_count": len(self.completed_tutorials)
        })

        logger.info("모든 튜토리얼 완료!")

    def skip_current_step(self) -> bool:
        """현재 단계 건너뛰기"""
        if not self.current_step or not self.current_step.skippable:
            return False

        logger.info(f"튜토리얼 건너뛰기: {self.current_step.id}")

        next_step_id = self.current_step.next_step
        self.current_step.skip()
        self.current_step = None

        if next_step_id:
            self.start_tutorial(next_step_id)
        else:
            self.is_active = False

        return True

    def skip_all_tutorials(self) -> bool:
        """모든 튜토리얼 건너뛰기"""
        if not self.config.get("global", {}).get("can_skip_all", True):
            return False

        self.is_active = False
        self.current_step = None
        self.skipped = True

        event_bus.publish("tutorial.skipped_all", {})

        logger.info("모든 튜토리얼 건너뛰기")
        return True

    def _subscribe_to_events(self) -> None:
        """게임 이벤트 구독"""
        # 플레이어 이동
        event_bus.subscribe("player.move", self._on_player_move)

        # 전투 관련
        event_bus.subscribe("combat.start", self._on_combat_start)
        event_bus.subscribe("combat.end", self._on_combat_end)
        event_bus.subscribe("combat.action", self._on_combat_action)

        # 스킬 사용
        event_bus.subscribe("skill.execute", self._on_skill_execute)

        # 상호작용
        event_bus.subscribe("npc.interaction", self._on_npc_interaction)

    def _on_player_move(self, data: Dict[str, Any]) -> None:
        """플레이어 이동 이벤트 처리"""
        self.game_state["player_position"] = (data.get("x", 0), data.get("y", 0))

    def _on_combat_start(self, data: Dict[str, Any]) -> None:
        """전투 시작 이벤트 처리"""
        self.game_state["action_count"] = 0
        self.game_state["action_sequence"] = []

    def _on_combat_end(self, data: Dict[str, Any]) -> None:
        """전투 종료 이벤트 처리"""
        self.game_state["last_combat_result"] = data.get("result")
        self.game_state["defeated_enemies"] = data.get("defeated_count", 0)

    def _on_combat_action(self, data: Dict[str, Any]) -> None:
        """전투 행동 이벤트 처리"""
        self.game_state["action_count"] += 1
        # dict를 직접 저장하지 말고 필요한 정보만 추출
        action_info = {
            "action_type": data.get("action_type"),
            "actor_name": getattr(data.get("actor"), "name", str(data.get("actor"))),
            "target_name": getattr(data.get("target"), "name", str(data.get("target"))) if data.get("target") else None,
            "skill_name": getattr(data.get("skill"), "name", str(data.get("skill"))) if data.get("skill") else None
        }
        self.game_state["action_sequence"].append(action_info)

    def _on_skill_execute(self, data: Dict[str, Any]) -> None:
        """스킬 사용 이벤트 처리"""
        skill = data.get("skill")
        if skill:
            # 스킬 이름이나 타입을 사용 (객체가 아니라 문자열로 저장)
            skill_identifier = getattr(skill, "name", str(skill))
            if skill_identifier not in self.game_state["used_skill_types"]:
                self.game_state["used_skill_types"].append(skill_identifier)

    def _on_npc_interaction(self, data: Dict[str, Any]) -> None:
        """NPC 상호작용 이벤트 처리"""
        npc_id = data.get("npc_id")
        if npc_id and npc_id not in self.game_state["interacted_npcs"]:
            self.game_state["interacted_npcs"].append(npc_id)

    def save_progress(self) -> Dict[str, Any]:
        """튜토리얼 진행 상태 저장"""
        return {
            "tutorial_completed": not self.is_active and len(self.completed_tutorials) > 0,
            "current_step": self.current_step.id if self.current_step else None,
            "completed_steps": self.completed_tutorials,
            "skipped": self.skipped
        }

    def load_progress(self, data: Dict[str, Any]) -> None:
        """튜토리얼 진행 상태 로드"""
        self.completed_tutorials = data.get("completed_steps", [])
        self.skipped = data.get("skipped", False)

        current_step_id = data.get("current_step")
        if current_step_id and not data.get("tutorial_completed", False):
            self.start_tutorial(current_step_id)


# 전역 튜토리얼 매니저 인스턴스
_tutorial_manager: Optional[TutorialManager] = None


def get_tutorial_manager() -> TutorialManager:
    """튜토리얼 매니저 싱글톤 가져오기"""
    global _tutorial_manager
    if _tutorial_manager is None:
        _tutorial_manager = TutorialManager()
        _tutorial_manager.load_tutorials()
    return _tutorial_manager
