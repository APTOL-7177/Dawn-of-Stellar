"""
환경설정 UI

게임 설정 조정
"""

from enum import Enum
from typing import Optional
import tcod

from src.ui.input_handler import InputHandler, GameAction
from src.ui.tcod_display import render_space_background
from src.core.logger import get_logger, Loggers
from src.core.config import get_config
from src.audio import get_audio_manager, play_sfx


logger = get_logger(Loggers.UI)


class SettingOption(Enum):
    """설정 옵션"""
    VOLUME_BGM = "bgm_volume"
    VOLUME_SFX = "sfx_volume"
    FULLSCREEN = "fullscreen"
    SHOW_FPS = "show_fps"
    FPS_LIMIT = "fps_limit"
    TUTORIAL = "tutorial"
    BACK = "back"


class SettingsUI:
    """설정 UI"""

    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.selected_index = 0

        # 설정값들
        config = get_config()
        # 볼륨은 0-100 정수로 저장, config에는 float(0.0-1.0) 또는 int(0-100)가 있을 수 있음
        bgm_vol = config.get("audio.bgm_volume", 70)
        sfx_vol = config.get("audio.sfx_volume", 80)
        
        # float 값이면 정수로 변환 (0.0-1.0 -> 0-100)
        if isinstance(bgm_vol, float):
            self.bgm_volume = int(round(bgm_vol * 100))
        else:
            self.bgm_volume = int(bgm_vol)
        
        if isinstance(sfx_vol, float):
            self.sfx_volume = int(round(sfx_vol * 100))
        else:
            self.sfx_volume = int(sfx_vol)
        
        # 10의 배수로 반올림
        self.bgm_volume = round(self.bgm_volume / 10) * 10
        self.sfx_volume = round(self.sfx_volume / 10) * 10
        self.fullscreen = config.get("display.fullscreen", False)
        self.show_fps = config.get("display.show_fps", False)
        self.fps_limit = config.get("display.fps_limit", 60)

        self.options = [
            ("BGM 볼륨", SettingOption.VOLUME_BGM),
            ("효과음 볼륨", SettingOption.VOLUME_SFX),
            ("전체화면", SettingOption.FULLSCREEN),
            ("FPS 표시", SettingOption.SHOW_FPS),
            ("FPS 제한", SettingOption.FPS_LIMIT),
            ("튜토리얼 다시보기", SettingOption.TUTORIAL),
            ("돌아가기", SettingOption.BACK),
        ]

    def handle_input(self, action: GameAction) -> Optional[str]:
        """
        입력 처리

        Returns:
            "close" - 설정 닫기
            None - 계속
        """
        if action == GameAction.MOVE_UP:
            self.selected_index = max(0, self.selected_index - 1)
        elif action == GameAction.MOVE_DOWN:
            self.selected_index = min(len(self.options) - 1, self.selected_index + 1)
        elif action == GameAction.MOVE_LEFT:
            # 값 감소
            self._adjust_setting(-1)
        elif action == GameAction.MOVE_RIGHT:
            # 값 증가
            self._adjust_setting(1)
        elif action == GameAction.CONFIRM:
            option = self.options[self.selected_index][1]
            if option == SettingOption.BACK:
                return "close"
            elif option == SettingOption.TUTORIAL:
                return "tutorial"
            else:
                # Enter로도 값 토글/증가
                self._adjust_setting(1)
        elif action == GameAction.ESCAPE or action == GameAction.MENU:
            play_sfx("ui", "cursor_cancel")
            return "close"

        return None

    def _adjust_setting(self, direction: int):
        """설정 값 조정"""
        option = self.options[self.selected_index][1]

        if option == SettingOption.VOLUME_BGM:
            self.bgm_volume = max(0, min(100, self.bgm_volume + direction * 10))
            # 10의 배수로 보장
            self.bgm_volume = round(self.bgm_volume / 10) * 10
            # 실제 BGM 볼륨 조정 적용
            try:
                audio_manager = get_audio_manager()
                audio_manager.set_bgm_volume(self.bgm_volume / 100.0)
                logger.debug(f"BGM 볼륨 조정: {self.bgm_volume}")
            except Exception as e:
                logger.warning(f"BGM 볼륨 조정 실패: {e}")
        elif option == SettingOption.VOLUME_SFX:
            self.sfx_volume = max(0, min(100, self.sfx_volume + direction * 10))
            # 10의 배수로 보장
            self.sfx_volume = round(self.sfx_volume / 10) * 10
            # 실제 SFX 볼륨 조정 적용
            try:
                audio_manager = get_audio_manager()
                audio_manager.set_sfx_volume(self.sfx_volume / 100.0)
                logger.debug(f"SFX 볼륨 조정: {self.sfx_volume}")
            except Exception as e:
                logger.warning(f"SFX 볼륨 조정 실패: {e}")
        elif option == SettingOption.FULLSCREEN:
            self.fullscreen = not self.fullscreen
            # 전체화면 변경은 재시작 필요
            logger.info(f"전체화면 설정: {self.fullscreen} (재시작 필요)")
        elif option == SettingOption.SHOW_FPS:
            self.show_fps = not self.show_fps
        elif option == SettingOption.FPS_LIMIT:
            # 30, 60, 120, 144, 240, 0 (무제한)
            fps_options = [30, 60, 120, 144, 240, 0]
            current_idx = fps_options.index(self.fps_limit) if self.fps_limit in fps_options else 1
            new_idx = (current_idx + direction) % len(fps_options)
            self.fps_limit = fps_options[new_idx]

    def save_settings(self):
        """설정 저장"""
        config = get_config()
        config.set("audio.bgm_volume", self.bgm_volume / 100.0)  # 0.0-1.0 범위로 저장
        config.set("audio.sfx_volume", self.sfx_volume / 100.0)  # 0.0-1.0 범위로 저장
        config.set("display.fullscreen", self.fullscreen)
        config.set("display.show_fps", self.show_fps)
        config.set("display.fps_limit", self.fps_limit)
        
        # 설정 파일에 실제로 저장
        try:
            config.save()
            logger.info("설정이 파일에 저장되었습니다")
        except Exception as e:
            logger.error(f"설정 저장 실패: {e}", exc_info=True)

    def render(self, console: tcod.console.Console):
        """설정 렌더링"""
        render_space_background(console, console.width, console.height)

        # 제목
        title = "=== 환경 설정 ==="
        console.print((self.screen_width - len(title)) // 2, 2, title, fg=(255, 255, 100))

        # 설정 항목
        y = 6

        for i, (label, option) in enumerate(self.options):
            # 선택 커서
            if i == self.selected_index:
                console.print(5, y, "►", fg=(255, 255, 100))

            # 설정 이름
            console.print(7, y, label, fg=(200, 200, 200) if i == self.selected_index else (150, 150, 150))

            # 설정 값
            value_x = 35
            value_color = (255, 255, 100) if i == self.selected_index else (200, 200, 200)

            if option == SettingOption.VOLUME_BGM:
                # 10의 배수로 보장
                bgm_vol = round(self.bgm_volume / 10) * 10
                value = f"{int(bgm_vol)}%"
                bar = self._render_volume_bar(int(bgm_vol))
                console.print(value_x, y, f"{bar} {value}", fg=value_color)
            elif option == SettingOption.VOLUME_SFX:
                # 10의 배수로 보장
                sfx_vol = round(self.sfx_volume / 10) * 10
                value = f"{int(sfx_vol)}%"
                bar = self._render_volume_bar(int(sfx_vol))
                console.print(value_x, y, f"{bar} {value}", fg=value_color)
            elif option == SettingOption.FULLSCREEN:
                value = "켜짐" if self.fullscreen else "꺼짐"
                console.print(value_x, y, f"[ {value} ]", fg=value_color)
            elif option == SettingOption.SHOW_FPS:
                value = "켜짐" if self.show_fps else "꺼짐"
                console.print(value_x, y, f"[ {value} ]", fg=value_color)
            elif option == SettingOption.FPS_LIMIT:
                value = f"{self.fps_limit} FPS" if self.fps_limit > 0 else "무제한"
                console.print(value_x, y, f"< {value} >", fg=value_color)
            elif option == SettingOption.TUTORIAL:
                # 튜토리얼 다시보기
                console.print(value_x, y, "[ Enter로 시작 ]", fg=value_color)
            elif option == SettingOption.BACK:
                # 돌아가기는 값 표시 없음
                console.print(value_x, y, "", fg=value_color)

            y += 2

        # 설명 텍스트
        explanations = {
            0: "배경 음악의 볼륨을 조절합니다",
            1: "효과음의 볼륨을 조절합니다",
            2: "전체화면 모드로 게임을 실행합니다 (재시작 필요)",
            3: "화면에 프레임 레이트(FPS)를 표시합니다",
            4: "게임의 최대 프레임 레이트를 제한합니다 (0 = 무제한)",
            5: "튜토리얼을 다시 볼 수 있습니다 (게임 기본 조작법, 전투 시스템 등)",
            6: "메뉴로 돌아갑니다",
        }

        explanation = explanations.get(self.selected_index, "")
        if explanation:
            console.print(
                7,
                self.screen_height - 8,
                explanation,
                fg=(150, 200, 255)
            )

        # 조작법
        console.print(
            5,
            self.screen_height - 4,
            "↑↓: 선택  ←→: 값 조정  Enter: 확인  ESC: 저장하고 닫기",
            fg=(180, 180, 180)
        )

    def _render_volume_bar(self, volume: int) -> str:
        """볼륨 바 렌더링"""
        bar_length = 10
        filled = int(volume / 10)
        return "█" * filled + "░" * (bar_length - filled)


def open_settings(
    console: tcod.console.Console,
    context: tcod.context.Context
) -> None:
    """
    설정 메뉴 열기

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
    """
    settings = SettingsUI(console.width, console.height)
    handler = InputHandler()

    logger.info("설정 메뉴 열림")

    while True:
        # 렌더링
        settings.render(console)
        context.present(console)

        # 입력 처리
        for event in tcod.event.wait():
            action = handler.dispatch(event)

            if action:
                result = settings.handle_input(action)

                if result == "close":
                    # 설정 저장
                    settings.save_settings()
                    logger.info("설정 메뉴 닫힘")
                    return
                elif result == "tutorial":
                    # 튜토리얼 뷰어 실행
                    from src.tutorial.tutorial_viewer import run_tutorial_viewer
                    logger.info("튜토리얼 뷰어 시작")
                    run_tutorial_viewer(console, context)
                    logger.info("튜토리얼 뷰어 종료")
                    # 설정 화면으로 돌아옴

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                settings.save_settings()
                return
