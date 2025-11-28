"""
스토리 튜토리얼 게임 통합
Dawn of Stellar - 시공의 여명

게임 시스템과 스토리 튜토리얼을 연결합니다.
"""

import tcod
from typing import Optional, Dict, Any

from src.core.event_bus import event_bus
from src.core.logger import get_logger, Loggers
from src.tutorial.story_tutorial_manager import (
    StoryTutorialManager,
    get_story_tutorial_manager
)
from src.tutorial.job_selection_ui import show_job_selection, JobChoiceInfo


logger = get_logger(Loggers.SYSTEM)


class StoryTutorialIntegration:
    """
    스토리 튜토리얼과 게임 시스템 통합
    
    게임 시작, 저장/로드, UI 이벤트 등을 처리합니다.
    """
    
    def __init__(self):
        self.story_manager: Optional[StoryTutorialManager] = None
        self.console: Optional[tcod.console.Console] = None
        self.context: Optional[tcod.context.Context] = None
        self._initialized = False
        
    def initialize(
        self,
        console: tcod.console.Console,
        context: tcod.context.Context
    ) -> None:
        """초기화"""
        self.console = console
        self.context = context
        self.story_manager = get_story_tutorial_manager()
        self._subscribe_to_events()
        self._initialized = True
        
        logger.info("스토리 튜토리얼 통합 초기화 완료")
    
    def _subscribe_to_events(self) -> None:
        """이벤트 구독"""
        # 게임 시작 시 튜토리얼 제안
        event_bus.subscribe("game.new_game", self._on_new_game)
        
        # 직업 선택 UI 표시
        event_bus.subscribe("story.show_job_selection", self._on_show_job_selection)
        
        # 튜토리얼 완료
        event_bus.subscribe("story.complete", self._on_story_complete)
        
        # 자동 추천 트리거
        event_bus.subscribe("combat.break_failed", self._on_break_failed)
        event_bus.subscribe("combat.brv_overflow", self._on_brv_overflow)
        event_bus.subscribe("combat.player_death", self._on_player_death)
        event_bus.subscribe("job.unlocked", self._on_job_unlocked)
    
    def _on_new_game(self, data: Dict[str, Any]) -> None:
        """새 게임 시작 시"""
        if not self._initialized:
            return
            
        # 첫 플레이인지 확인
        is_first_play = data.get("is_first_play", True)
        
        if is_first_play:
            # 스토리 모드 시작 여부 묻기
            self._show_story_mode_prompt()
    
    def _show_story_mode_prompt(self) -> None:
        """스토리 모드 시작 프롬프트"""
        if not self.console or not self.context:
            return
            
        # 간단한 확인 UI (추후 개선 가능)
        logger.info("스토리 튜토리얼 시작 여부 확인")
        
        # 기본적으로 스토리 모드 시작
        if self.story_manager:
            self.story_manager.start_story_mode()
    
    def _on_show_job_selection(self, data: Dict[str, Any]) -> None:
        """직업 선택 UI 표시"""
        if not self.console or not self.context:
            logger.warning("콘솔/컨텍스트 없음 - 직업 선택 UI 표시 불가")
            return
            
        choices_data = data.get("choices", [])
        
        # JobChoiceInfo로 변환
        choices = []
        for c in choices_data:
            choices.append(JobChoiceInfo(
                id=c.get("id", ""),
                name=c.get("name", ""),
                description=c.get("description", ""),
                story_reason=c.get("story_reason", ""),
                recommended=c.get("recommended", False),
                preview_skills=c.get("preview_skills", [])
            ))
        
        # 기본 선택지가 없으면 기본값 사용
        if not choices:
            selected_job = show_job_selection(
                self.console,
                self.context,
                on_select=self._handle_job_selection
            )
        else:
            from src.tutorial.job_selection_ui import JobSelectionUI
            ui = JobSelectionUI(self.console, self.context, choices)
            selected_job = ui.show(on_select=self._handle_job_selection)
    
    def _handle_job_selection(self, job_id: str) -> None:
        """직업 선택 처리"""
        if self.story_manager:
            self.story_manager.complete_story_mode(job_id)
            
        logger.info(f"직업 선택 완료: {job_id}")
    
    def _on_story_complete(self, data: Dict[str, Any]) -> None:
        """스토리 완료 시"""
        selected_job = data.get("selected_job")
        rewards = data.get("rewards", {})
        
        logger.info(f"스토리 튜토리얼 완료! 선택 직업: {selected_job}")
        logger.info(f"보상: {rewards}")
        
        # 게임에 보상 적용
        self._apply_rewards(rewards)
    
    def _apply_rewards(self, rewards: Dict[str, Any]) -> None:
        """보상 적용"""
        try:
            # 별의 파편 (메타 진행 해금용)
            stellar_fragments = rewards.get("stellar_fragments", 0)
            if stellar_fragments > 0:
                event_bus.publish("meta.gain_fragments", {"amount": stellar_fragments})
                
        except Exception as e:
            logger.error(f"보상 적용 중 오류: {e}")
    
    def _on_break_failed(self, data: Dict[str, Any]) -> None:
        """BREAK 실패 시 튜토리얼 추천"""
        remaining_brv = data.get("remaining_brv", 0)
        
        # 거의 성공했을 때 (BRV 1~10 남음)
        if 1 <= remaining_brv <= 10:
            event_bus.publish("tutorial.suggest", {
                "tutorial_id": "story_07_break_mastery",
                "message": "BREAK에 거의 성공했어요! 다시 연습해볼까요?"
            })
    
    def _on_brv_overflow(self, data: Dict[str, Any]) -> None:
        """BRV 오버플로우 시"""
        overflow_count = data.get("count", 0)
        
        if overflow_count >= 3:
            event_bus.publish("tutorial.suggest", {
                "tutorial_id": "story_06_brv_basics",
                "message": "BRV가 넘쳐흐르고 있어요. BRV 관리법을 복습해볼까요?"
            })
    
    def _on_player_death(self, data: Dict[str, Any]) -> None:
        """플레이어 사망 시"""
        death_count = data.get("total_deaths", 0)
        
        if death_count >= 3:
            event_bus.publish("tutorial.suggest", {
                "tutorial_id": "story_06_brv_basics",
                "message": "전투가 어려우신가요? 기본 전략을 다시 배워볼까요?"
            })
    
    def _on_job_unlocked(self, data: Dict[str, Any]) -> None:
        """새 직업 해금 시"""
        job_id = data.get("job_id")
        source = data.get("source", "")
        
        if source != "tutorial_reward":  # 튜토리얼 보상이 아닌 경우
            event_bus.publish("tutorial.suggest", {
                "tutorial_id": "story_09_job_awakening",
                "message": "새 직업이 해금됐어요! 직업 시스템을 확인해볼까요?"
            })
    
    def save_state(self) -> Dict[str, Any]:
        """상태 저장"""
        if self.story_manager:
            return self.story_manager.save_progress()
        return {}
    
    def load_state(self, data: Dict[str, Any]) -> None:
        """상태 로드"""
        if self.story_manager:
            self.story_manager.load_progress(data)


# 전역 인스턴스
_integration: Optional[StoryTutorialIntegration] = None


def get_story_integration() -> StoryTutorialIntegration:
    """스토리 튜토리얼 통합 싱글톤"""
    global _integration
    if _integration is None:
        _integration = StoryTutorialIntegration()
    return _integration


def initialize_story_tutorial(
    console: tcod.console.Console,
    context: tcod.context.Context
) -> StoryTutorialIntegration:
    """
    스토리 튜토리얼 시스템 초기화
    
    게임 시작 시 호출하세요.
    """
    integration = get_story_integration()
    integration.initialize(console, context)
    return integration


def start_story_tutorial() -> bool:
    """스토리 튜토리얼 시작"""
    integration = get_story_integration()
    if integration.story_manager:
        return integration.story_manager.start_story_mode()
    return False


def complete_story_with_job(job_id: str) -> Dict[str, Any]:
    """직업 선택으로 스토리 완료"""
    integration = get_story_integration()
    if integration.story_manager:
        return integration.story_manager.complete_story_mode(job_id)
    return {}
