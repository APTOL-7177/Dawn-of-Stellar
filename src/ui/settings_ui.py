"""
환경설정 UI

게임 설정 조정
"""

from enum import Enum
from typing import Optional
import tcod

from src.ui.input_handler import InputHandler, GameAction
from src.core.logger import get_logger, Loggers
from src.core.config import get_config
from src.audio import get_audio_manager


logger = get_logger(Loggers.UI)


class SettingOption(Enum):
    """설정 옵션"""
    VOLUME_BGM = "bgm_volume"
    VOLUME_SFX = "sfx_volume"
    LANGUAGE = "language"
    DIFFICULTY = "difficulty"
    AUTO_SAVE = "auto_save"
    SHOW_DAMAGE_NUMBERS = "show_damage"
    COMBAT_SPEED = "combat_speed"
    BACK = "back"


class SettingsUI:
    """설정 UI"""

    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.selected_index = 0

        # 설정값들
        config = get_config()
        self.bgm_volume = config.get("audio.bgm_volume", 70)
        self.sfx_volume = config.get("audio.sfx_volume", 80)
        self.language = config.get("game.language", "ko")
        self.difficulty = config.get("game.difficulty", "normal")
        self.auto_save = config.get("save.auto_save", True)
        self.show_damage_numbers = config.get("ui.show_damage_numbers", True)
        self.combat_speed = config.get("combat.speed", "normal")

        self.options = [
            ("BGM 볼륨", SettingOption.VOLUME_BGM),
            ("효과음 볼륨", SettingOption.VOLUME_SFX),
            ("난이도", SettingOption.DIFFICULTY),
            ("자동 저장", SettingOption.AUTO_SAVE),
            ("데미지 숫자 표시", SettingOption.SHOW_DAMAGE_NUMBERS),
            ("전투 속도", SettingOption.COMBAT_SPEED),
            ("돌아가기", SettingOption.BACK),
        ]

        # 언어는 한국어 고정
        self.language = "ko"

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
            else:
                # Enter로도 값 토글/증가
                self._adjust_setting(1)
        elif action == GameAction.ESCAPE or action == GameAction.MENU:
            return "close"

        return None

    def _adjust_setting(self, direction: int):
        """설정 값 조정"""
        option = self.options[self.selected_index][1]

        if option == SettingOption.VOLUME_BGM:
            self.bgm_volume = max(0, min(100, self.bgm_volume + direction * 10))
            # 실제 BGM 볼륨 조정 적용
            try:
                audio_manager = get_audio_manager()
                audio_manager.set_bgm_volume(self.bgm_volume / 100.0)
                logger.debug(f"BGM 볼륨 조정: {self.bgm_volume}")
            except Exception as e:
                logger.warning(f"BGM 볼륨 조정 실패: {e}")
        elif option == SettingOption.VOLUME_SFX:
            self.sfx_volume = max(0, min(100, self.sfx_volume + direction * 10))
            # 실제 SFX 볼륨 조정 적용
            try:
                audio_manager = get_audio_manager()
                audio_manager.set_sfx_volume(self.sfx_volume / 100.0)
                logger.debug(f"SFX 볼륨 조정: {self.sfx_volume}")
            except Exception as e:
                logger.warning(f"SFX 볼륨 조정 실패: {e}")
        elif option == SettingOption.DIFFICULTY:
            difficulties = ["easy", "normal", "hard", "extreme"]
            current_idx = difficulties.index(self.difficulty) if self.difficulty in difficulties else 1
            new_idx = (current_idx + direction) % len(difficulties)
            self.difficulty = difficulties[new_idx]
        elif option == SettingOption.AUTO_SAVE:
            self.auto_save = not self.auto_save
        elif option == SettingOption.SHOW_DAMAGE_NUMBERS:
            self.show_damage_numbers = not self.show_damage_numbers
        elif option == SettingOption.COMBAT_SPEED:
            speeds = ["slow", "normal", "fast", "instant"]
            current_idx = speeds.index(self.combat_speed) if self.combat_speed in speeds else 1
            new_idx = (current_idx + direction) % len(speeds)
            self.combat_speed = speeds[new_idx]

    def save_settings(self):
        """설정 저장"""
        config = get_config()
        config.set("audio.bgm_volume", self.bgm_volume)
        config.set("audio.sfx_volume", self.sfx_volume)
        config.set("game.language", self.language)
        config.set("game.difficulty", self.difficulty)
        config.set("save.auto_save", self.auto_save)
        config.set("ui.show_damage_numbers", self.show_damage_numbers)
        config.set("combat.speed", self.combat_speed)

        logger.info("설정 저장됨")

    def render(self, console: tcod.console.Console):
        """설정 렌더링"""
        console.clear()

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
                value = f"{self.bgm_volume}%"
                bar = self._render_volume_bar(self.bgm_volume)
                console.print(value_x, y, f"{bar} {value}", fg=value_color)
            elif option == SettingOption.VOLUME_SFX:
                value = f"{self.sfx_volume}%"
                bar = self._render_volume_bar(self.sfx_volume)
                console.print(value_x, y, f"{bar} {value}", fg=value_color)
            elif option == SettingOption.DIFFICULTY:
                diff_names = {"easy": "쉬움", "normal": "보통", "hard": "어려움", "extreme": "익스트림"}
                value = diff_names.get(self.difficulty, self.difficulty)
                console.print(value_x, y, f"< {value} >", fg=value_color)
            elif option == SettingOption.AUTO_SAVE:
                value = "켜짐" if self.auto_save else "꺼짐"
                console.print(value_x, y, f"[ {value} ]", fg=value_color)
            elif option == SettingOption.SHOW_DAMAGE_NUMBERS:
                value = "켜짐" if self.show_damage_numbers else "꺼짐"
                console.print(value_x, y, f"[ {value} ]", fg=value_color)
            elif option == SettingOption.COMBAT_SPEED:
                speed_names = {"slow": "느림", "normal": "보통", "fast": "빠름", "instant": "즉시"}
                value = speed_names.get(self.combat_speed, self.combat_speed)
                console.print(value_x, y, f"< {value} >", fg=value_color)
            elif option == SettingOption.BACK:
                # 돌아가기는 값 표시 없음
                console.print(value_x, y, "", fg=value_color)

            y += 2

        # 설명 텍스트
        explanations = {
            0: "배경 음악의 볼륨을 조절합니다",
            1: "효과음의 볼륨을 조절합니다",
            2: "게임 난이도를 조절합니다",
            3: "자동 저장 기능을 켜거나 끕니다",
            4: "전투 중 데미지 숫자 표시 여부",
            5: "전투 애니메이션 속도를 조절합니다",
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

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                settings.save_settings()
                return
