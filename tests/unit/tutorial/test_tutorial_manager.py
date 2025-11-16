"""
튜토리얼 매니저 테스트
"""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from src.tutorial.tutorial_manager import TutorialManager
from src.tutorial.tutorial_step import TutorialStep, CompletionType


class TestTutorialManager:
    """튜토리얼 매니저 테스트"""

    @pytest.fixture
    def tutorial_manager(self, tmp_path):
        """테스트용 튜토리얼 매니저"""
        # 임시 데이터 디렉토리 사용
        manager = TutorialManager(data_dir=str(tmp_path / "tutorials"))
        return manager

    def test_tutorial_manager_initialization(self, tutorial_manager):
        """튜토리얼 매니저 초기화 테스트"""
        assert tutorial_manager is not None
        assert tutorial_manager.is_active == False
        assert tutorial_manager.current_step is None
        assert len(tutorial_manager.completed_tutorials) == 0

    def test_start_tutorial_disabled(self, tutorial_manager):
        """튜토리얼 비활성화 상태 테스트"""
        tutorial_manager.config = {"global": {"enabled": False}}
        result = tutorial_manager.start_tutorial()
        assert result == False
        assert tutorial_manager.is_active == False

    def test_game_state_tracking(self, tutorial_manager):
        """게임 상태 추적 테스트"""
        # 플레이어 이동
        tutorial_manager._on_player_move({"x": 5, "y": 10})
        assert tutorial_manager.game_state["player_position"] == (5, 10)

        # 전투 종료
        tutorial_manager._on_combat_end({"result": "victory", "defeated_count": 3})
        assert tutorial_manager.game_state["last_combat_result"] == "victory"
        assert tutorial_manager.game_state["defeated_enemies"] == 3

        # 스킬 사용
        tutorial_manager._on_skill_execute({"skill_type": "brv_attack"})
        assert "brv_attack" in tutorial_manager.game_state["used_skill_types"]

        # NPC 상호작용
        tutorial_manager._on_npc_interaction({"npc_id": "tutorial_guide"})
        assert "tutorial_guide" in tutorial_manager.game_state["interacted_npcs"]

    def test_save_and_load_progress(self, tutorial_manager):
        """진행 상태 저장/로드 테스트"""
        # 진행 상태 설정
        tutorial_manager.completed_tutorials = ["basic_movement", "combat_intro"]
        tutorial_manager.skipped = False

        # 저장
        saved_data = tutorial_manager.save_progress()
        assert "completed_steps" in saved_data
        assert len(saved_data["completed_steps"]) == 2
        assert saved_data["skipped"] == False

        # 새 매니저 생성 및 로드
        new_manager = TutorialManager()
        new_manager.load_progress(saved_data)
        assert len(new_manager.completed_tutorials) == 2
        assert "basic_movement" in new_manager.completed_tutorials

    def test_skip_all_tutorials(self, tutorial_manager):
        """전체 튜토리얼 건너뛰기 테스트"""
        tutorial_manager.config = {"global": {"can_skip_all": True}}
        result = tutorial_manager.skip_all_tutorials()
        assert result == True
        assert tutorial_manager.is_active == False
        assert tutorial_manager.skipped == True


class TestTutorialStep:
    """튜토리얼 스텝 테스트"""

    def test_position_reached_completion(self):
        """위치 도달 완료 조건 테스트"""
        from src.tutorial.tutorial_step import (
            TutorialStep, CompletionCondition, TutorialMessage,
            TutorialHint, UIHighlight, TutorialReward
        )

        step = TutorialStep(
            tutorial_id="test_movement",
            title="테스트 이동",
            order=1,
            category="test",
            description="테스트 설명",
            objective="목표 지점 도달",
            messages=[],
            completion_condition=CompletionCondition(
                type=CompletionType.POSITION_REACHED,
                params={"target_x": 10, "target_y": 10, "radius": 1},
                message="완료!"
            ),
            hints=[],
            ui_highlights=[],
            rewards=TutorialReward(exp=10)
        )

        # 시작
        step.start()
        assert step.is_active == True
        assert step.is_completed == False

        # 완료 조건 체크 - 아직 도달 안함
        game_state = {"player_position": (5, 5)}
        assert step.check_completion(game_state) == False

        # 완료 조건 체크 - 도달
        game_state = {"player_position": (10, 10)}
        assert step.check_completion(game_state) == True

    def test_combat_victory_completion(self):
        """전투 승리 완료 조건 테스트"""
        from src.tutorial.tutorial_step import (
            TutorialStep, CompletionCondition, TutorialReward
        )

        step = TutorialStep(
            tutorial_id="test_combat",
            title="테스트 전투",
            order=1,
            category="test",
            description="테스트 설명",
            objective="적 처치",
            messages=[],
            completion_condition=CompletionCondition(
                type=CompletionType.COMBAT_VICTORY,
                params={"enemy_count": 1},
                message="승리!"
            ),
            hints=[],
            ui_highlights=[],
            rewards=TutorialReward(exp=50)
        )

        step.start()

        # 전투 패배
        game_state = {"last_combat_result": "defeat"}
        assert step.check_completion(game_state) == False

        # 전투 승리
        game_state = {"last_combat_result": "victory", "defeated_enemies": 1}
        assert step.check_completion(game_state) == True

    def test_hint_triggering(self):
        """힌트 트리거 테스트"""
        from src.tutorial.tutorial_step import (
            TutorialStep, CompletionCondition, TutorialHint, TutorialReward
        )

        hint1 = TutorialHint(text="힌트 1", trigger_time=5.0)
        hint2 = TutorialHint(text="힌트 2", trigger_time=10.0)

        step = TutorialStep(
            tutorial_id="test_hints",
            title="테스트 힌트",
            order=1,
            category="test",
            description="테스트 설명",
            objective="목표",
            messages=[],
            completion_condition=CompletionCondition(
                type=CompletionType.POSITION_REACHED,
                params={"target_x": 0, "target_y": 0, "radius": 0},
                message="완료"
            ),
            hints=[hint1, hint2],
            ui_highlights=[],
            rewards=TutorialReward()
        )

        step.start()

        # 시간 경과 시뮬레이션
        step.elapsed_time = 3.0
        hints = step.get_current_hints()
        assert len(hints) == 0

        step.elapsed_time = 6.0
        hints = step.get_current_hints()
        assert len(hints) == 1
        assert hints[0].text == "힌트 1"

        step.elapsed_time = 11.0
        hints = step.get_current_hints()
        assert len(hints) == 1
        assert hints[0].text == "힌트 2"

    def test_tutorial_completion(self):
        """튜토리얼 완료 테스트"""
        from src.tutorial.tutorial_step import (
            TutorialStep, CompletionCondition, TutorialReward
        )

        reward = TutorialReward(exp=100, gold=50, message="완료!")

        step = TutorialStep(
            tutorial_id="test_complete",
            title="테스트 완료",
            order=1,
            category="test",
            description="테스트 설명",
            objective="목표",
            messages=[],
            completion_condition=CompletionCondition(
                type=CompletionType.POSITION_REACHED,
                params={},
                message="완료"
            ),
            hints=[],
            ui_highlights=[],
            rewards=reward
        )

        step.start()
        received_reward = step.complete()

        assert step.is_active == False
        assert step.is_completed == True
        assert received_reward.exp == 100
        assert received_reward.gold == 50

    def test_tutorial_skip(self):
        """튜토리얼 건너뛰기 테스트"""
        from src.tutorial.tutorial_step import (
            TutorialStep, CompletionCondition, TutorialReward
        )

        step = TutorialStep(
            tutorial_id="test_skip",
            title="테스트 건너뛰기",
            order=1,
            category="test",
            description="테스트 설명",
            objective="목표",
            messages=[],
            completion_condition=CompletionCondition(
                type=CompletionType.POSITION_REACHED,
                params={},
                message="완료"
            ),
            hints=[],
            ui_highlights=[],
            rewards=TutorialReward(),
            skippable=True
        )

        step.start()
        step.skip()

        assert step.is_active == False
        assert step.is_completed == True

    def test_tutorial_not_skippable(self):
        """건너뛰기 불가 튜토리얼 테스트"""
        from src.tutorial.tutorial_step import (
            TutorialStep, CompletionCondition, TutorialReward
        )

        step = TutorialStep(
            tutorial_id="test_no_skip",
            title="테스트 건너뛰기 불가",
            order=1,
            category="test",
            description="테스트 설명",
            objective="목표",
            messages=[],
            completion_condition=CompletionCondition(
                type=CompletionType.POSITION_REACHED,
                params={},
                message="완료"
            ),
            hints=[],
            ui_highlights=[],
            rewards=TutorialReward(),
            skippable=False
        )

        step.start()
        initial_active = step.is_active
        step.skip()

        # 건너뛰기 불가이므로 여전히 활성 상태
        assert step.is_active == initial_active
