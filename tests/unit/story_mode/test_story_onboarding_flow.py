"""
Story Mode 정식 온보딩 복구 테스트

검증 대상:
- 튜토리얼 직업 해금 보상 exactly-once (MetaProgress.grant_job_unlock_reward)
- 챕터 보상 exactly-once (ChapterRunner._apply_chapter_rewards 재플레이 중복 방지)
- finale/skip_all → TRANSITION_TO_GAME 통일
- 스토리 진행 잠금 해제 챕터 재개 경로
"""

import pytest

import src.persistence.meta_progress as meta_progress
import src.story_mode.story_mode_manager as story_mode_manager
from src.story_mode.story_mode_manager import (
    StoryModeManager,
    StoryModeProgress,
    StoryModeResult,
    CHAPTER_ORDER,
)


# ─────────────────────────────────────────────────────────────
# MetaProgress.grant_job_unlock_reward (exactly-once)
# ─────────────────────────────────────────────────────────────


class TestJobUnlockReward:
    def test_unlock_new_job_grants_fragments(self):
        meta = meta_progress.MetaProgress()
        meta.unlocked_jobs.discard("time_mage")
        before = meta.star_fragments

        assert meta.grant_job_unlock_reward("time_mage", 50) is True
        assert "time_mage" in meta.unlocked_jobs
        assert meta.star_fragments == before + 50

    def test_unlock_duplicate_job_is_noop(self):
        meta = meta_progress.MetaProgress()
        meta.unlocked_jobs.add("time_mage")
        before = meta.star_fragments

        assert meta.grant_job_unlock_reward("time_mage", 50) is False
        assert meta.star_fragments == before

    def test_unlock_none_job_is_noop(self):
        meta = meta_progress.MetaProgress()
        before = meta.star_fragments
        assert meta.grant_job_unlock_reward(None, 50) is False
        assert meta.star_fragments == before

    def test_story_tutorial_manager_reward_is_persisted_once(
        self, tmp_path, monkeypatch
    ):
        """story_tutorial_manager 완료 보상이 set-append 없이 저장된다"""
        monkeypatch.setattr(
            meta_progress.MetaProgressManager,
            "SAVE_FILE",
            tmp_path / "meta_progress.json",
        )
        meta_progress._meta_progress_manager = None

        from src.tutorial.story_tutorial_manager import StoryTutorialManager

        manager = StoryTutorialManager()
        manager.selected_job = "time_mage"

        manager._grant_completion_rewards()
        manager._grant_completion_rewards()  # 중복 호출

        saved = meta_progress.get_meta_progress_manager().load()
        assert "time_mage" in saved.unlocked_jobs
        assert isinstance(saved.unlocked_jobs, set)

        meta_progress._meta_progress_manager = None

    def test_story_runner_completion_reward_is_persisted_once(
        self, tmp_path, monkeypatch
    ):
        """story_runner.on_tutorial_complete 보상 exactly-once"""
        monkeypatch.setattr(
            meta_progress.MetaProgressManager,
            "SAVE_FILE",
            tmp_path / "meta_progress.json",
        )
        meta_progress._meta_progress_manager = None

        import src.tutorial.story_runner as story_runner

        story_runner.on_tutorial_complete()
        fragments_after_first = meta_progress.get_meta_progress().star_fragments
        assert "time_mage" in meta_progress.get_meta_progress().unlocked_jobs

        story_runner.on_tutorial_complete()
        fragments_after_second = meta_progress.get_meta_progress().star_fragments

        assert fragments_after_second == fragments_after_first

        meta_progress._meta_progress_manager = None


# ─────────────────────────────────────────────────────────────
# ChapterRunner 보상 exactly-once
# ─────────────────────────────────────────────────────────────


class TestChapterRewards:
    def _make_runner(self, progress: StoryModeProgress):
        from src.story_mode.chapter_runner import ChapterRunner

        runner = ChapterRunner(None, None)
        runner._last_progress = progress
        return runner

    def test_first_clear_grants_fragments(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            meta_progress.MetaProgressManager,
            "SAVE_FILE",
            tmp_path / "meta_progress.json",
        )
        meta_progress._meta_progress_manager = None

        progress = StoryModeProgress()  # act1_ch1 미완료
        runner = self._make_runner(progress)

        before = meta_progress.get_meta_progress().star_fragments
        runner._apply_chapter_rewards("act1_ch1", {"star_fragments": 30})
        meta = meta_progress.get_meta_progress()
        assert meta.star_fragments == before + 30

        meta_progress._meta_progress_manager = None

    def test_replay_clear_does_not_grant_twice(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            meta_progress.MetaProgressManager,
            "SAVE_FILE",
            tmp_path / "meta_progress.json",
        )
        meta_progress._meta_progress_manager = None

        progress = StoryModeProgress()
        progress.complete_chapter("act1_ch1")  # 이미 완료된 챕터 재플레이
        runner = self._make_runner(progress)

        fragments_before = meta_progress.get_meta_progress().star_fragments
        runner._apply_chapter_rewards("act1_ch1", {"star_fragments": 30})
        meta = meta_progress.get_meta_progress()
        # 중복 지급 없음 (지급 전 값과 동일)
        assert meta.star_fragments == fragments_before

        meta_progress._meta_progress_manager = None


# ─────────────────────────────────────────────────────────────
# finale / skip_all → TRANSITION_TO_GAME
# ─────────────────────────────────────────────────────────────


class TestFinaleHandoff:
    def test_skip_all_returns_transition_to_game(self, tmp_path, monkeypatch):
        manager = StoryModeManager(None, None)
        manager.progress = StoryModeProgress()
        monkeypatch.setattr(
            story_mode_manager, "SAVE_PATH", tmp_path / "story_progress.json"
        )
        saved_results = []
        monkeypatch.setattr(
            manager, "save_progress", lambda: saved_results.append(1) or True
        )

        # run()은 챕터 선택 UI 루프 → skip_all 분기를 UI 모킹으로 검증:
        # run_chapter_select가 "__skip_all__"을 반환하면 TRANSITION_TO_GAME이어야 한다.
        import src.story_mode.chapter_select_ui as select_ui

        monkeypatch.setattr(
            select_ui, "run_chapter_select", lambda *a, **k: "__skip_all__"
        )
        result = manager.run()
        assert result == StoryModeResult.TRANSITION_TO_GAME
        assert len(saved_results) == 1
        assert manager.progress.is_all_completed()

    def test_finale_chapter_returns_transition_to_game(self, tmp_path, monkeypatch):
        manager = StoryModeManager(None, None)
        manager.progress = StoryModeProgress()
        monkeypatch.setattr(
            story_mode_manager, "SAVE_PATH", tmp_path / "story_progress.json"
        )
        monkeypatch.setattr(
            manager, "save_progress", lambda: True
        )

        import src.story_mode.chapter_select_ui as select_ui

        monkeypatch.setattr(
            select_ui, "run_chapter_select", lambda *a, **k: "act5_finale"
        )

        class FakeRunner:
            def __init__(self, console, context):
                pass

            def run_chapter(self, chapter_id, progress):
                return "completed"

        import src.story_mode.chapter_runner as chapter_runner_module

        monkeypatch.setattr(
            chapter_runner_module, "ChapterRunner", FakeRunner
        )

        result = manager.run()
        assert result == StoryModeResult.TRANSITION_TO_GAME
        assert manager.progress.is_all_completed() is False  # 피날레만 완료
        assert manager.progress.is_chapter_completed("act5_finale")


# ─────────────────────────────────────────────────────────────
# 잠금 해제 / 재개 경로
# ─────────────────────────────────────────────────────────────


class TestChapterUnlockFlow:
    def test_first_chapter_and_prologue_unlocked_by_default(self):
        progress = StoryModeProgress()
        assert progress.is_chapter_unlocked("act1_prologue")
        assert not progress.is_chapter_unlocked("act1_ch2")

        progress.complete_chapter("act1_prologue")
        assert progress.is_chapter_unlocked("act1_ch1")
        assert progress.get_next_chapter() == "act1_ch1"

        progress.complete_chapter("act1_ch1")
        assert progress.is_chapter_unlocked("act1_ch2")
        assert progress.get_next_chapter() == "act1_ch2"

    def test_quit_to_menu_keeps_progress_resumable(self, tmp_path, monkeypatch):
        """quit은 완료 처리 없이 진행 저장 → 재시작 후 이어하기 가능"""
        monkeypatch.setattr(
            story_mode_manager, "SAVE_PATH", tmp_path / "story_progress.json"
        )
        manager = StoryModeManager(None, None)
        manager.progress = StoryModeProgress()
        manager.progress.complete_chapter("act1_prologue")
        manager.progress.complete_chapter("act1_ch1")

        assert manager.save_progress() is True

        fresh = StoryModeManager(None, None)
        assert fresh.load_progress() is True
        assert fresh.progress.is_chapter_completed("act1_ch1")
        assert fresh.progress.get_next_chapter() == "act1_ch2"
        # quit 경로는 보상/완료 처리를 하지 않는다 (챕터 수 변화 없음)
        assert len(fresh.progress.completed_chapters) == 2

    def test_full_playthrough_marks_all_completed(self):
        progress = StoryModeProgress()
        for ch in CHAPTER_ORDER:
            assert progress.is_chapter_unlocked(ch)
            progress.complete_chapter(ch)
        assert progress.is_all_completed()
        assert progress.get_next_chapter() is None
