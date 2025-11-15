"""
게이지 렌더러

픽셀 단위 부드러운 게이지 (그라디언트 색상 활용)
"""

from typing import Tuple
import tcod.console


class GaugeRenderer:
    """게이지 렌더러 - draw_rect() 기반"""

    @staticmethod
    def render_bar(
        console: tcod.console.Console,
        x: int,
        y: int,
        width: int,
        current: float,
        maximum: float,
        show_numbers: bool = True,
        color_gradient: bool = True,
        custom_color: Tuple[int, int, int] = None
    ) -> None:
        """
        게이지 바 렌더링 (픽셀 단위 부드러운 효과)

        Args:
            console: TCOD 콘솔
            x, y: 게이지 위치
            width: 게이지 너비 (셀 수)
            current: 현재 값
            maximum: 최대 값
            show_numbers: 숫자 표시 여부
            color_gradient: 색상 그라디언트 (빨강~노랑~초록)
            custom_color: 커스텀 색상 (RGB 튜플)
        """
        if maximum <= 0:
            ratio = 0.0
        else:
            ratio = min(1.0, current / maximum)

        # 색상 계산
        if custom_color:
            # 커스텀 색상 사용
            fg_color = custom_color
            bg_color = tuple(c // 2 for c in custom_color)
        elif color_gradient:
            if ratio > 0.6:
                fg_color = (0, 200, 0)  # 초록
                bg_color = (0, 100, 0)
            elif ratio > 0.3:
                fg_color = (200, 200, 0)  # 노랑
                bg_color = (100, 100, 0)
            else:
                fg_color = (200, 0, 0)  # 빨강
                bg_color = (100, 0, 0)
        else:
            fg_color = (150, 150, 150)
            bg_color = (50, 50, 50)

        # 배경 (빈 부분)
        console.draw_rect(x, y, width, 1, ord(" "), bg=bg_color)

        # 픽셀 단위 채우기
        filled_exact = ratio * width  # 정확한 픽셀 위치
        filled_full = int(filled_exact)  # 완전히 채워진 칸 수
        filled_partial = filled_exact - filled_full  # 부분 채움 비율 (0.0~1.0)

        # 완전히 채워진 부분
        if filled_full > 0:
            console.draw_rect(x, y, filled_full, 1, ord(" "), bg=fg_color)

        # 부분적으로 채워진 마지막 칸 (그라디언트 색상)
        if filled_partial > 0.0 and filled_full < width:
            # fg_color와 bg_color 사이의 중간 색상 계산
            partial_color = (
                int(bg_color[0] + (fg_color[0] - bg_color[0]) * filled_partial),
                int(bg_color[1] + (fg_color[1] - bg_color[1]) * filled_partial),
                int(bg_color[2] + (fg_color[2] - bg_color[2]) * filled_partial)
            )
            console.draw_rect(x + filled_full, y, 1, 1, ord(" "), bg=partial_color)

        # 숫자 표시
        if show_numbers:
            text = f"{int(current)}/{int(maximum)}"
            text_x = x + (width - len(text)) // 2
            console.print(text_x, y, text, fg=(255, 255, 255))

    @staticmethod
    def render_percentage_bar(
        console: tcod.console.Console,
        x: int,
        y: int,
        width: int,
        percentage: float,
        show_percent: bool = True,
        custom_color: Tuple[int, int, int] = None
    ) -> None:
        """
        퍼센트 게이지 렌더링 (픽셀 단위 부드러운 효과)

        Args:
            console: TCOD 콘솔
            x, y: 게이지 위치
            width: 게이지 너비
            percentage: 0.0 ~ 1.0
            show_percent: 퍼센트 표시 여부
            custom_color: 커스텀 색상
        """
        ratio = min(1.0, max(0.0, percentage))

        # 색상
        if custom_color:
            fg_color = custom_color
            bg_color = tuple(c // 2 for c in custom_color)
        else:
            # 기본 그라디언트
            if ratio > 0.6:
                fg_color = (0, 200, 0)
                bg_color = (0, 100, 0)
            elif ratio > 0.3:
                fg_color = (200, 200, 0)
                bg_color = (100, 100, 0)
            else:
                fg_color = (200, 0, 0)
                bg_color = (100, 0, 0)

        # 배경
        console.draw_rect(x, y, width, 1, ord(" "), bg=bg_color)

        # 픽셀 단위 채우기
        filled_exact = ratio * width
        filled_full = int(filled_exact)
        filled_partial = filled_exact - filled_full

        # 완전히 채워진 부분
        if filled_full > 0:
            console.draw_rect(x, y, filled_full, 1, ord(" "), bg=fg_color)

        # 부분적으로 채워진 마지막 칸
        if filled_partial > 0.0 and filled_full < width:
            partial_color = (
                int(bg_color[0] + (fg_color[0] - bg_color[0]) * filled_partial),
                int(bg_color[1] + (fg_color[1] - bg_color[1]) * filled_partial),
                int(bg_color[2] + (fg_color[2] - bg_color[2]) * filled_partial)
            )
            console.draw_rect(x + filled_full, y, 1, 1, ord(" "), bg=partial_color)

        # 퍼센트 표시
        if show_percent:
            text = f"{int(ratio * 100)}%"
            text_x = x + (width - len(text)) // 2
            console.print(text_x, y, text, fg=(255, 255, 255))

    @staticmethod
    def render_casting_bar(
        console: tcod.console.Console,
        x: int,
        y: int,
        width: int,
        progress: float,
        skill_name: str = ""
    ) -> None:
        """
        캐스팅 게이지 렌더링 (픽셀 단위 부드러운 효과)

        Args:
            console: TCOD 콘솔
            x, y: 게이지 위치
            width: 게이지 너비
            progress: 진행도 (0.0 ~ 1.0)
            skill_name: 스킬 이름
        """
        ratio = min(1.0, max(0.0, progress))

        # 캐스팅은 보라색
        fg_color = (150, 100, 255)
        bg_color = (75, 50, 125)

        # 스킬 이름 표시
        if skill_name:
            console.print(x, y, f"{skill_name}:", fg=(200, 200, 200))
            bar_x = x + len(skill_name) + 2
            bar_width = width - len(skill_name) - 2
        else:
            bar_x = x
            bar_width = width

        # 배경
        console.draw_rect(bar_x, y, bar_width, 1, ord(" "), bg=bg_color)

        # 픽셀 단위 채우기
        filled_exact = ratio * bar_width
        filled_full = int(filled_exact)
        filled_partial = filled_exact - filled_full

        # 완전히 채워진 부분
        if filled_full > 0:
            console.draw_rect(bar_x, y, filled_full, 1, ord(" "), bg=fg_color)

        # 부분적으로 채워진 마지막 칸
        if filled_partial > 0.0 and filled_full < bar_width:
            partial_color = (
                int(bg_color[0] + (fg_color[0] - bg_color[0]) * filled_partial),
                int(bg_color[1] + (fg_color[1] - bg_color[1]) * filled_partial),
                int(bg_color[2] + (fg_color[2] - bg_color[2]) * filled_partial)
            )
            console.draw_rect(bar_x + filled_full, y, 1, 1, ord(" "), bg=partial_color)

        # 진행도 표시
        percent_text = f"{int(ratio * 100)}%"
        text_x = bar_x + (bar_width - len(percent_text)) // 2
        console.print(text_x, y, percent_text, fg=(255, 255, 255))

    @staticmethod
    def render_atb_gauge(
        console: tcod.console.Console,
        x: int,
        y: int,
        width: int,
        current: float,
        threshold: float,
        maximum: float
    ) -> None:
        """
        ATB 게이지 렌더링 (픽셀 단위 부드러운 효과)

        Args:
            console: TCOD 콘솔
            x, y: 게이지 위치
            width: 게이지 너비
            current: 현재 ATB 값
            threshold: 행동 가능 임계값
            maximum: 최대 ATB 값
        """
        if maximum <= 0:
            ratio = 0.0
        else:
            ratio = min(1.0, current / maximum)

        # ATB 색상 (파란색)
        fg_color = (100, 150, 255)
        bg_color = (50, 75, 125)

        # 배경
        console.draw_rect(x, y, width, 1, ord(" "), bg=bg_color)

        # 픽셀 단위 채우기
        filled_exact = ratio * width
        filled_full = int(filled_exact)
        filled_partial = filled_exact - filled_full

        # 완전히 채워진 부분
        if filled_full > 0:
            console.draw_rect(x, y, filled_full, 1, ord(" "), bg=fg_color)

        # 부분적으로 채워진 마지막 칸
        if filled_partial > 0.0 and filled_full < width:
            partial_color = (
                int(bg_color[0] + (fg_color[0] - bg_color[0]) * filled_partial),
                int(bg_color[1] + (fg_color[1] - bg_color[1]) * filled_partial),
                int(bg_color[2] + (fg_color[2] - bg_color[2]) * filled_partial)
            )
            console.draw_rect(x + filled_full, y, 1, 1, ord(" "), bg=partial_color)

        # 행동 가능 임계값 표시 (세로선)
        threshold_ratio = threshold / maximum
        threshold_x = x + int(threshold_ratio * width)
        if 0 <= threshold_x < x + width:
            console.print(threshold_x, y, "|", fg=(255, 255, 100))

    @staticmethod
    def render_atb_with_cast(
        console: tcod.console.Console,
        x: int,
        y: int,
        width: int,
        atb_current: float,
        atb_threshold: float,
        atb_maximum: float,
        cast_progress: float = 0.0,
        is_casting: bool = False
    ) -> None:
        """
        ATB 게이지와 캐스팅 진행도를 함께 렌더링

        Args:
            console: TCOD 콘솔
            x, y: 게이지 위치
            width: 게이지 너비
            atb_current: 현재 ATB 값
            atb_threshold: 행동 가능 임계값
            atb_maximum: 최대 ATB 값
            cast_progress: 캐스팅 진행도 (0.0 ~ 1.0)
            is_casting: 캐스팅 중 여부
        """
        # ATB를 임계값(threshold) 기준으로 표시 (0~threshold = 0~100%)
        # threshold 이상은 오버플로우로 최대 2배까지 표시
        if atb_threshold <= 0:
            atb_ratio = 0.0
        else:
            atb_ratio = min(2.0, atb_current / atb_threshold)

        # ATB 색상 (연한 하늘색)
        atb_fg = (135, 206, 235)
        atb_bg = (67, 103, 117)

        # 오버플로우 색상 (밝은 하늘색)
        overflow_fg = (173, 216, 230)

        # 캐스팅 색상 (보라색/자홍색)
        cast_fg = (200, 100, 255)
        cast_bg = (100, 50, 125)

        # 배경
        console.draw_rect(x, y, width, 1, ord(" "), bg=atb_bg)

        # ATB 게이지 그리기 (100%까지)
        normal_ratio = min(1.0, atb_ratio)
        atb_filled_exact = normal_ratio * width
        atb_filled_full = int(atb_filled_exact)
        atb_filled_partial = atb_filled_exact - atb_filled_full

        # ATB 완전히 채워진 부분
        if atb_filled_full > 0:
            console.draw_rect(x, y, atb_filled_full, 1, ord(" "), bg=atb_fg)

        # ATB 부분적으로 채워진 마지막 칸
        if atb_filled_partial > 0.0 and atb_filled_full < width:
            partial_color = (
                int(atb_bg[0] + (atb_fg[0] - atb_bg[0]) * atb_filled_partial),
                int(atb_bg[1] + (atb_fg[1] - atb_bg[1]) * atb_filled_partial),
                int(atb_bg[2] + (atb_fg[2] - atb_bg[2]) * atb_filled_partial)
            )
            console.draw_rect(x + atb_filled_full, y, 1, 1, ord(" "), bg=partial_color)

        # 오버플로우 게이지 (100% 초과분, 최대 200%까지)
        if atb_ratio > 1.0:
            overflow_ratio = min(1.0, atb_ratio - 1.0)
            overflow_filled_exact = overflow_ratio * width
            overflow_filled_full = int(overflow_filled_exact)
            overflow_filled_partial = overflow_filled_exact - overflow_filled_full

            if overflow_filled_full > 0:
                console.draw_rect(x, y, overflow_filled_full, 1, ord(" "), bg=overflow_fg)

            if overflow_filled_partial > 0.0 and overflow_filled_full < width:
                partial_color = (
                    int(atb_fg[0] + (overflow_fg[0] - atb_fg[0]) * overflow_filled_partial),
                    int(atb_fg[1] + (overflow_fg[1] - atb_fg[1]) * overflow_filled_partial),
                    int(atb_fg[2] + (overflow_fg[2] - atb_fg[2]) * overflow_filled_partial)
                )
                console.draw_rect(x + overflow_filled_full, y, 1, 1, ord(" "), bg=partial_color)

        # 캐스팅 중이면 캐스팅 진행도를 오버레이
        if is_casting and cast_progress > 0.0:
            cast_filled_exact = cast_progress * width
            cast_filled_full = int(cast_filled_exact)
            cast_filled_partial = cast_filled_exact - cast_filled_full

            # 캐스팅 완전히 채워진 부분 (오버레이)
            if cast_filled_full > 0:
                console.draw_rect(x, y, cast_filled_full, 1, ord(" "), bg=cast_fg)

            # 캐스팅 부분적으로 채워진 마지막 칸
            if cast_filled_partial > 0.0 and cast_filled_full < width:
                partial_color = (
                    int(cast_bg[0] + (cast_fg[0] - cast_bg[0]) * cast_filled_partial),
                    int(cast_bg[1] + (cast_fg[1] - cast_bg[1]) * cast_filled_partial),
                    int(cast_bg[2] + (cast_fg[2] - cast_bg[2]) * cast_filled_partial)
                )
                console.draw_rect(x + cast_filled_full, y, 1, 1, ord(" "), bg=partial_color)

        # 텍스트 표시 (threshold 기준, 100% = 행동 가능)
        if is_casting:
            text = f"캐스팅 {int(cast_progress * 100)}%"
        else:
            # atb_ratio는 threshold 기준 (1.0 = 100% = 행동 가능)
            percentage = int(atb_ratio * 100)
            if percentage > 100:
                # 오버플로우는 밝게 표시
                text = f"{percentage}%"
            else:
                text = f"{percentage}%"
        text_x = x + (width - len(text)) // 2
        console.print(text_x, y, text, fg=(255, 255, 255))

    @staticmethod
    def render_status_icons(status_effects) -> str:
        """
        상태이상 아이콘 렌더링

        Args:
            status_effects: 딕셔너리 {status_name: turns_remaining} 또는 리스트

        Returns:
            아이콘 문자열
        """
        icon_map = {
            "poison": "[독]",
            "burn": "[화상]",
            "freeze": "[빙결]",
            "stun": "[기절]",
            "sleep": "[수면]",
            "silence": "[침묵]",
            "blind": "[암흑]",
            "berserk": "[광폭]",
            "haste": "[가속]",
            "slow": "[감속]",
            "regen": "[재생]",
            "reflect": "[반사]",
            "barrier": "[방벽]",
            "break": "[브레이크]",
            "doom": "[죽음]",
            "rune": "[룬]",
            "curse": "[저주]",
            "blessing": "[축복]",
            "mark": "[표식]",
            "weaken": "[약화]",
            "strengthen": "[강화]",
            "defense_down": "[방↓]",
            "defense_up": "[방↑]",
            "attack_down": "[공↓]",
            "attack_up": "[공↑]",
        }

        icons = []

        # 딕셔너리인 경우
        if isinstance(status_effects, dict):
            for status, turns in status_effects.items():
                icon = icon_map.get(status.lower(), f"[{status[:2]}]")
                icons.append(f"{icon}{turns}")
        # 리스트인 경우
        elif isinstance(status_effects, list):
            for effect in status_effects:
                if hasattr(effect, 'name'):
                    status_name = effect.name.lower()
                    turns = getattr(effect, 'duration', '')
                    icon = icon_map.get(status_name, f"[{effect.name[:2]}]")
                    if turns:
                        icons.append(f"{icon}{turns}")
                    else:
                        icons.append(icon)
                else:
                    # 문자열인 경우
                    status_name = str(effect).lower()
                    icon = icon_map.get(status_name, f"[{str(effect)[:2]}]")
                    icons.append(icon)

        return " ".join(icons) if icons else ""

    @staticmethod
    def render_wound_indicator(
        console: tcod.console.Console,
        x: int,
        y: int,
        wound_damage: int
    ) -> None:
        """
        상처 데미지 표시

        Args:
            console: TCOD 콘솔
            x, y: 표시 위치
            wound_damage: 상처 누적 데미지
        """
        if wound_damage <= 0:
            return

        # 상처 레벨에 따른 색상
        if wound_damage < 50:
            text = f"[상처:{wound_damage}]"
            color = (255, 200, 150)
        elif wound_damage < 150:
            text = f"[중상:{wound_damage}]"
            color = (255, 150, 100)
        else:
            text = f"[치명상:{wound_damage}]"
            color = (255, 50, 50)

        console.print(x, y, text, fg=color)
