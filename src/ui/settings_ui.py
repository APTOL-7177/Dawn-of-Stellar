"""
환경설정 UI

게임 설정 조정
"""

from enum import Enum
from pathlib import Path
from typing import Optional
import tcod

from src.ui.input_handler import InputHandler, GameAction, unified_input_handler
from src.ui.pointer import PointerButton, PointerDispatcher, PointerDispatchResult, PointerEvent, PointerEventKind, PointerRegion
from src.ui.tcod_display import render_space_background
from src.ui.visual_tokens import rgb
from src.core.logger import get_logger, Loggers
from src.core.config import get_config
from src.core.paths import get_project_root
from src.audio import get_audio_manager, play_sfx


logger = get_logger(Loggers.UI)


class SettingOption(Enum):
    """설정 옵션"""
    VOLUME_BGM = "bgm_volume"
    VOLUME_SFX = "sfx_volume"
    DISPLAY_MODE = "display_mode"
    VSYNC = "vsync"
    KEY_BINDINGS = "key_bindings"
    RESET_RPG_DATA = "reset_rpg_data"
    BACK = "back"


# 화면 모드: (config 값, 표시 이름)
DISPLAY_MODES = [
    ("borderless", "전체 창화면"),
    ("fullscreen", "전체화면"),
    ("windowed", "창모드"),
]


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
        # 화면 모드: display.display_mode 우선, 없으면 기존 설정에서 추론
        display_mode = config.get("display.display_mode", None)
        if display_mode is None:
            # 기존 설정 호환: borderless_fullscreen이면 borderless, fullscreen이면 fullscreen
            if config.get("display.borderless_fullscreen", True):
                display_mode = "borderless"
            elif config.get("display.fullscreen", False):
                display_mode = "fullscreen"
            else:
                display_mode = "windowed"
        self.display_mode = display_mode
        self.vsync = config.get("display.vsync", True)

        # RPG 데이터 초기화 확인 다이얼로그 상태
        self.confirm_reset_rpg = False
        self.confirm_cursor = 1  # 0=예, 1=아니오 (기본: 아니오)
        self.reset_rpg_done = False  # 초기화 완료 메시지 표시용

        self.options = [
            ("BGM 볼륨", SettingOption.VOLUME_BGM),
            ("효과음 볼륨", SettingOption.VOLUME_SFX),
            ("화면 모드", SettingOption.DISPLAY_MODE),
            ("수직 동기화", SettingOption.VSYNC),
            ("키 설정", SettingOption.KEY_BINDINGS),
            ("RPG 데이터 초기화", SettingOption.RESET_RPG_DATA),
            ("돌아가기", SettingOption.BACK),
        ]

    def handle_input(self, action: GameAction) -> Optional[str]:
        """
        입력 처리

        Returns:
            "close" - 설정 닫기
            None - 계속
        """
        # 초기화 완료 메시지 표시 중이면 아무 키나 누르면 닫기
        if self.reset_rpg_done:
            self.reset_rpg_done = False
            return None

        # 확인 다이얼로그가 열려있을 때
        if self.confirm_reset_rpg:
            if action == GameAction.MOVE_LEFT:
                self.confirm_cursor = 0
            elif action == GameAction.MOVE_RIGHT:
                self.confirm_cursor = 1
            elif action == GameAction.CONFIRM:
                if self.confirm_cursor == 0:
                    # "예" 선택 → 초기화 실행
                    self._reset_rpg_data()
                    self.confirm_reset_rpg = False
                    self.reset_rpg_done = True
                else:
                    # "아니오" 선택 → 다이얼로그 닫기
                    self.confirm_reset_rpg = False
            elif action == GameAction.ESCAPE or action == GameAction.MENU:
                self.confirm_reset_rpg = False
            return None

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
            elif option == SettingOption.KEY_BINDINGS:
                return "key_bindings"
            elif option == SettingOption.RESET_RPG_DATA:
                self.confirm_reset_rpg = True
                self.confirm_cursor = 1  # 기본: "아니오"
                return None
            else:
                # Z로도 값 토글/증가
                self._adjust_setting(1)
        elif action == GameAction.ESCAPE or action == GameAction.MENU:
            play_sfx("ui", "cursor_cancel")
            return "close"

        return None

    def pointer_regions(self) -> tuple[PointerRegion, ...]:
        regions = []
        for index, (label, _option) in enumerate(self.options):
            regions.append(
                PointerRegion(
                    region_id=str(index),
                    x=5,
                    y=6 + index * 2,
                    width=max(44, self.screen_width - 10),
                    height=1,
                    command=GameAction.CONFIRM,
                    tooltip=self._option_tooltip(index, label),
                    enabled=True,
                )
            )
        return tuple(regions)

    def handle_pointer_event(self, event: PointerEvent) -> PointerDispatchResult:
        dispatcher = PointerDispatcher(self.pointer_regions())
        result = dispatcher.dispatch(event)
        region = dispatcher.region_at(event.position)
        region_id = result.hovered_region_id or (region.region_id if region else None)
        if region_id is not None:
            self.selected_index = int(region_id)
        if event.kind is PointerEventKind.WHEEL and result.action is not None:
            value = self.handle_input(result.action)
            return result.with_value(value)
        if event.kind in (PointerEventKind.DRAG_START, PointerEventKind.DRAG_MOVE, PointerEventKind.DRAG_END):
            return self._handle_slider_drag(event, result)
        if event.kind is PointerEventKind.CLICK and event.button is PointerButton.RIGHT:
            value = self.handle_input(GameAction.ESCAPE)
            return result.with_value(value)
        if event.kind is PointerEventKind.CLICK and result.action is not None:
            value = self.handle_input(result.action)
            return result.with_value(value)
        return result

    def _handle_slider_drag(self, event: PointerEvent, result: PointerDispatchResult) -> PointerDispatchResult:
        if result.hovered_region_id is None:
            return result
        self.selected_index = int(result.hovered_region_id)
        option = self.options[self.selected_index][1]
        if option not in (SettingOption.VOLUME_BGM, SettingOption.VOLUME_SFX):
            return result
        region = next(region for region in self.pointer_regions() if region.region_id == result.hovered_region_id)
        relative_x = max(0, min(region.width - 1, event.position.tile[0] - region.x))
        volume = int(round((relative_x / max(1, region.width - 1)) * 10)) * 10
        if option == SettingOption.VOLUME_BGM:
            self.bgm_volume = volume
            tooltip = f"BGM 볼륨: {self.bgm_volume}%"
        else:
            self.sfx_volume = volume
            tooltip = f"효과음 볼륨: {self.sfx_volume}%"
        return PointerDispatchResult(event=event, hovered_region_id=result.hovered_region_id, tooltip=tooltip)

    def _option_tooltip(self, index: int, label: str) -> str:
        explanations = {
            0: f"{label}: {self.bgm_volume}%",
            1: f"{label}: {self.sfx_volume}%",
            2: "화면 모드를 변경합니다.",
            3: "수직 동기화를 켜거나 끕니다.",
            4: "키보드와 게임패드 키 설정을 엽니다.",
            5: "RPG 데이터 초기화 확인을 엽니다.",
            6: "설정을 저장하고 닫습니다.",
        }
        return explanations.get(index, label)

    def _reset_rpg_data(self):
        """RPG 모드 데이터 초기화 - 세이브 파일과 스토리 진행도 삭제"""
        root = get_project_root()
        targets = [
            root / "user_data" / "saves" / "save_rpg.json",
            root / "user_data" / "story_progress.json",
        ]
        deleted = []
        for path in targets:
            try:
                if path.exists():
                    path.unlink()
                    deleted.append(str(path.name))
                    logger.info(f"RPG 데이터 삭제: {path}")
            except Exception as e:
                logger.error(f"RPG 데이터 삭제 실패: {path} - {e}")

        if deleted:
            logger.info(f"RPG 모드 데이터 초기화 완료: {', '.join(deleted)}")
        else:
            logger.info("RPG 모드 데이터 초기화: 삭제할 파일 없음")

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
        elif option == SettingOption.DISPLAY_MODE:
            # 3가지 모드 순환: borderless → fullscreen → windowed
            mode_keys = [m[0] for m in DISPLAY_MODES]
            current_idx = mode_keys.index(self.display_mode) if self.display_mode in mode_keys else 0
            new_idx = (current_idx + direction) % len(mode_keys)
            self.display_mode = mode_keys[new_idx]
            logger.info(f"화면 모드 설정: {self.display_mode} (재시작 필요)")
        elif option == SettingOption.VSYNC:
            self.vsync = not self.vsync

    def save_settings(self):
        """설정 저장"""
        config = get_config()
        config.set("audio.bgm_volume", self.bgm_volume / 100.0)  # 0.0-1.0 범위로 저장
        config.set("audio.sfx_volume", self.sfx_volume / 100.0)  # 0.0-1.0 범위로 저장
        config.set("display.display_mode", self.display_mode)
        config.set("display.fullscreen", self.display_mode == "fullscreen")
        config.set("display.borderless_fullscreen", self.display_mode == "borderless")
        config.set("display.vsync", self.vsync)

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
                console.print(5, y, "►", fg=rgb("accent.amber"))

            # 설정 이름
            console.print(7, y, label, fg=rgb("text.primary") if i == self.selected_index else rgb("text.secondary"))

            # 설정 값
            value_x = 35
            value_color = rgb("accent.amber") if i == self.selected_index else rgb("text.primary")

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
            elif option == SettingOption.DISPLAY_MODE:
                mode_dict = {m[0]: m[1] for m in DISPLAY_MODES}
                value = mode_dict.get(self.display_mode, "전체 창화면")
                console.print(value_x, y, f"< {value} >", fg=value_color)
            elif option == SettingOption.VSYNC:
                value = "켜짐" if self.vsync else "꺼짐"
                console.print(value_x, y, f"[ {value} ]", fg=value_color)
            elif option == SettingOption.KEY_BINDINGS:
                # 키 설정
                console.print(value_x, y, "[ Z로 열기 ]", fg=value_color)
            elif option == SettingOption.RESET_RPG_DATA:
                # RPG 데이터 초기화
                console.print(value_x, y, "[ Z로 실행 ]", fg=(255, 100, 100) if i == self.selected_index else (200, 100, 100))
            elif option == SettingOption.BACK:
                # 돌아가기는 값 표시 없음
                console.print(value_x, y, "", fg=value_color)

            y += 2

        # 확인 다이얼로그 오버레이
        if self.confirm_reset_rpg:
            self._render_confirm_dialog(console)
        elif self.reset_rpg_done:
            self._render_reset_done_message(console)

        # 설명 텍스트
        explanations = {
            0: "배경 음악의 볼륨을 조절합니다",
            1: "효과음의 볼륨을 조절합니다",
            2: "화면 모드를 변경합니다: 전체 창화면 / 전체화면 / 창모드 (재시작 필요)",
            3: "수직 동기화로 화면 찢어짐을 방지합니다 (재시작 필요)",
            4: "키보드와 게임패드 키 설정을 변경합니다",
            5: "RPG 모드 세이브와 스토리 진행 데이터를 삭제합니다",
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

        # 조작법 (게임패드 연결 시 게임패드 버튼으로 표시)
        from src.ui.input_handler import unified_input_handler, key_binding_manager
        use_gamepad = unified_input_handler.gamepad_connected

        if use_gamepad:
            move_help = key_binding_manager.get_movement_help(True)
            confirm_key = key_binding_manager.get_action_display("confirm", True)
            cancel_key = key_binding_manager.get_action_display("escape", True)
            help_text = f"{move_help}  {confirm_key}: 확인  {cancel_key}: 저장하고 닫기"
        else:
            help_text = "↑↓: 선택  ←→: 값 조정  Z: 확인  ESC: 저장하고 닫기"

        console.print(
            5,
            self.screen_height - 4,
            help_text,
            fg=(180, 180, 180)
        )

    def _render_confirm_dialog(self, console: tcod.console.Console):
        """RPG 데이터 초기화 확인 다이얼로그 렌더링"""
        # 반투명 배경 효과 (어둡게)
        for dy in range(console.height):
            for dx in range(console.width):
                r, g, b = console.rgb["bg"][dy, dx]
                console.rgb["bg"][dy, dx] = (r // 3, g // 3, b // 3)
                r2, g2, b2 = console.rgb["fg"][dy, dx]
                console.rgb["fg"][dy, dx] = (r2 // 3, g2 // 3, b2 // 3)

        # 다이얼로그 박스
        box_w, box_h = 40, 9
        bx = (self.screen_width - box_w) // 2
        by = (self.screen_height - box_h) // 2

        # 박스 배경
        for dy in range(box_h):
            for dx in range(box_w):
                console.rgb["bg"][by + dy, bx + dx] = (30, 10, 10)
                console.rgb["fg"][by + dy, bx + dx] = (200, 200, 200)
                console.rgb["ch"][by + dy, bx + dx] = ord(' ')

        # 테두리
        border_color = (255, 80, 80)
        for dx in range(box_w):
            console.print(bx + dx, by, "─", fg=border_color)
            console.print(bx + dx, by + box_h - 1, "─", fg=border_color)
        for dy in range(box_h):
            console.print(bx, by + dy, "│", fg=border_color)
            console.print(bx + box_w - 1, by + dy, "│", fg=border_color)
        console.print(bx, by, "┌", fg=border_color)
        console.print(bx + box_w - 1, by, "┐", fg=border_color)
        console.print(bx, by + box_h - 1, "└", fg=border_color)
        console.print(bx + box_w - 1, by + box_h - 1, "┘", fg=border_color)

        # 경고 제목
        title = "!! 경고 !!"
        console.print(bx + (box_w - len(title)) // 2, by + 1, title, fg=(255, 60, 60))

        # 경고 메시지
        msg1 = "RPG 모드의 모든 데이터가"
        msg2 = "삭제됩니다. 복구할 수 없습니다!"
        console.print(bx + (box_w - len(msg1)) // 2, by + 3, msg1, fg=(255, 200, 200))
        console.print(bx + (box_w - len(msg2)) // 2, by + 4, msg2, fg=(255, 200, 200))

        # 선택지
        yes_color = (255, 255, 100) if self.confirm_cursor == 0 else (150, 150, 150)
        no_color = (255, 255, 100) if self.confirm_cursor == 1 else (150, 150, 150)
        yes_prefix = "► " if self.confirm_cursor == 0 else "  "
        no_prefix = "► " if self.confirm_cursor == 1 else "  "

        yes_text = f"{yes_prefix}예"
        no_text = f"{no_prefix}아니오"
        gap = 10
        total_w = len(yes_text) + gap + len(no_text)
        start_x = bx + (box_w - total_w) // 2
        console.print(start_x, by + 6, yes_text, fg=yes_color)
        console.print(start_x + len(yes_text) + gap, by + 6, no_text, fg=no_color)

    def _render_reset_done_message(self, console: tcod.console.Console):
        """초기화 완료 메시지 렌더링"""
        # 반투명 배경 효과
        for dy in range(console.height):
            for dx in range(console.width):
                r, g, b = console.rgb["bg"][dy, dx]
                console.rgb["bg"][dy, dx] = (r // 3, g // 3, b // 3)
                r2, g2, b2 = console.rgb["fg"][dy, dx]
                console.rgb["fg"][dy, dx] = (r2 // 3, g2 // 3, b2 // 3)

        box_w, box_h = 36, 5
        bx = (self.screen_width - box_w) // 2
        by = (self.screen_height - box_h) // 2

        # 박스 배경
        for dy in range(box_h):
            for dx in range(box_w):
                console.rgb["bg"][by + dy, bx + dx] = (10, 30, 10)
                console.rgb["ch"][by + dy, bx + dx] = ord(' ')

        # 테두리
        border_color = (80, 200, 80)
        for dx in range(box_w):
            console.print(bx + dx, by, "─", fg=border_color)
            console.print(bx + dx, by + box_h - 1, "─", fg=border_color)
        for dy in range(box_h):
            console.print(bx, by + dy, "│", fg=border_color)
            console.print(bx + box_w - 1, by + dy, "│", fg=border_color)
        console.print(bx, by, "┌", fg=border_color)
        console.print(bx + box_w - 1, by, "┐", fg=border_color)
        console.print(bx, by + box_h - 1, "└", fg=border_color)
        console.print(bx + box_w - 1, by + box_h - 1, "┘", fg=border_color)

        msg = "RPG 데이터가 초기화되었습니다"
        console.print(bx + (box_w - len(msg)) // 2, by + 1, msg, fg=(100, 255, 100))
        hint = "아무 키나 누르세요"
        console.print(bx + (box_w - len(hint)) // 2, by + 3, hint, fg=(180, 180, 180))

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
    # 이전 화면에서 남은 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    settings = SettingsUI(console.width, console.height)

    logger.info("설정 메뉴 열림")

    import time

    while True:
        # 렌더링
        settings.render(console)
        context.present(console)

        # pygame 이벤트 업데이트 (게임패드 입력을 위해)
        try:
            import pygame
            pygame.event.pump()
        except:
            pass

        # 키보드 입력 처리 (논블로킹)
        for event in tcod.event.get():
            action = unified_input_handler.process_tcod_event(event)

            if action:
                result = settings.handle_input(action)

                if result == "close":
                    # 설정 저장
                    settings.save_settings()
                    logger.info("설정 메뉴 닫힘")
                    return
                elif result == "key_bindings":
                    # 키 설정 UI 열기
                    from src.ui.key_bindings_ui import open_key_bindings
                    open_key_bindings(console, context)
                    # 키 설정에서 돌아온 후 설정 화면 계속

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                settings.save_settings()
                return

        # 게임패드 입력 처리 (키보드 입력이 없었을 때)
        gamepad_action = unified_input_handler.get_action()
        if gamepad_action:
            result = settings.handle_input(gamepad_action)

            if result == "close":
                settings.save_settings()
                logger.info("설정 메뉴 닫힘")
                return
            elif result == "key_bindings":
                from src.ui.key_bindings_ui import open_key_bindings
                open_key_bindings(console, context)

        # CPU 사용률 낮추기
        time.sleep(0.01)
