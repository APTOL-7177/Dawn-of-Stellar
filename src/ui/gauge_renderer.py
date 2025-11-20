"""
게이지 렌더러

픽셀 단위 부드러운 게이지 (그라디언트 색상 활용)
"""

from typing import Tuple, List, Optional
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
    def render_status_icons(status_effects, buffs=None, debuffs=None) -> List[Tuple[str, Tuple[int, int, int]]]:
        """
        상태이상/버프/디버프 아이콘 렌더링 (컬러풀하게, 대괄호 제거, 최대 3줄)

        Args:
            status_effects: 딕셔너리 {status_name: turns_remaining} 또는 리스트
            buffs: 버프 딕셔너리 {buff_name: buff_data}
            debuffs: 디버프 딕셔너리 {debuff_name: debuff_data}

        Returns:
            [(텍스트, 색상), ...] 리스트 (최대 3줄)
        """
        from src.combat.status_effects import StatusType
        
        # 한글 이름 및 컬러 매핑
        status_info = {
            # 상태이상 - DOT (녹색 계열)
            "poison": ("독", (100, 255, 100)),
            "burn": ("화상", (255, 100, 50)),
            "bleed": ("출혈", (200, 0, 0)),
            "corrode": ("부식", (100, 150, 50)),
            "corrosion": ("부식", (100, 150, 50)),
            "disease": ("질병", (150, 100, 50)),
            "necrosis": ("괴사", (100, 50, 50)),
            "mp_drain": ("MP소모", (150, 100, 255)),
            "chill": ("냉기", (100, 200, 255)),
            "shock": ("감전", (255, 255, 100)),
            "nature_curse": ("자연저주", (100, 150, 100)),
            # 행동 제약 - CC (빨강 계열)
            "stun": ("기절", (255, 50, 50)),
            "sleep": ("수면", (150, 150, 255)),
            "silence": ("침묵", (150, 100, 150)),
            "blind": ("실명", (100, 100, 100)),
            "paralyze": ("마비", (200, 200, 100)),
            "freeze": ("빙결", (100, 200, 255)),
            "petrify": ("석화", (150, 150, 150)),
            "charm": ("매혹", (255, 150, 255)),
            "dominate": ("지배", (200, 100, 200)),
            "root": ("속박", (150, 100, 50)),
            "slow": ("둔화", (100, 150, 200)),
            "entangle": ("속박술", (100, 150, 100)),
            "madness": ("광기", (200, 50, 50)),
            "taunt": ("도발", (255, 150, 100)),
            # 버프 (초록 계열)
            "boost_atk": ("공↑", (100, 255, 100)),
            "boost_def": ("방↑", (100, 255, 150)),
            "boost_spd": ("속↑", (150, 255, 150)),
            "boost_accuracy": ("명중↑", (100, 255, 100)),
            "boost_crit": ("치명↑", (150, 255, 150)),
            "boost_dodge": ("회피↑", (100, 255, 150)),
            "boost_all_stats": ("전능↑", (150, 255, 200)),
            "boost_magic_atk": ("마공↑", (100, 255, 150)),
            "boost_magic_def": ("마방↑", (100, 255, 150)),
            "blessing": ("축복", (150, 255, 200)),
            "regeneration": ("재생", (100, 255, 150)),
            "mp_regen": ("MP재생", (100, 255, 200)),
            "invincible": ("무적", (150, 255, 200)),
            "reflect": ("반사", (150, 255, 200)),
            "haste": ("가속", (100, 255, 150)),
            "focus": ("집중", (150, 255, 200)),
            "rage": ("분노", (150, 255, 100)),
            "inspiration": ("영감", (150, 255, 200)),
            "guardian": ("수호", (100, 255, 150)),
            "strengthen": ("강화", (150, 255, 200)),
            "evasion_up": ("회피↑", (100, 255, 150)),
            "foresight": ("예지", (150, 255, 200)),
            "enlightenment": ("깨달음", (150, 255, 200)),
            "wisdom": ("지혜", (150, 255, 200)),
            "mana_regeneration": ("마나재생", (100, 255, 200)),
            "mana_infinite": ("무한마나", (150, 255, 200)),
            "holy_blessing": ("성축복", (150, 255, 200)),
            "barrier": ("보호막", (100, 255, 200)),
            "shield": ("보호막", (100, 255, 200)),
            "magic_barrier": ("마법보호막", (100, 255, 200)),
            "mana_shield": ("마나실드", (100, 255, 200)),
            "fire_shield": ("화염방패", (150, 255, 150)),
            "ice_shield": ("빙결방패", (100, 255, 200)),
            "holy_shield": ("성방패", (150, 255, 200)),
            "shadow_shield": ("그림자방패", (100, 255, 150)),
            # 디버프 (보라 계열)
            "reduce_atk": ("공↓", (200, 100, 255)),
            "reduce_def": ("방↓", (200, 100, 255)),
            "reduce_spd": ("속↓", (200, 100, 255)),
            "reduce_accuracy": ("명중↓", (200, 100, 255)),
            "reduce_all_stats": ("전능↓", (200, 100, 255)),
            "reduce_magic_atk": ("마공↓", (200, 100, 255)),
            "reduce_magic_def": ("마방↓", (200, 100, 255)),
            "reduce_speed": ("속도↓", (200, 100, 255)),
            "vulnerable": ("취약", (200, 100, 255)),
            "exposed": ("노출", (200, 100, 255)),
            "weakness": ("허약", (200, 100, 255)),
            "weaken": ("약화", (200, 100, 255)),
            "confusion": ("혼란", (200, 150, 255)),
            "terror": ("공포", (200, 100, 255)),
            "fear": ("공포", (200, 100, 255)),
            "despair": ("절망", (150, 50, 200)),
            "holy_weakness": ("성약점", (200, 100, 255)),
            "weakness_exposure": ("약점노출", (200, 100, 255)),
            # 특수 상태
            "curse": ("저주", (150, 0, 150)),
            "stealth": ("은신", (100, 100, 150)),
            "berserk": ("광폭", (255, 50, 50)),
            "counter": ("반격", (255, 255, 100)),
            "counter_attack": ("반격", (255, 255, 100)),
            "vampire": ("흡혈", (200, 0, 0)),
            "spirit_link": ("정신연결", (200, 150, 255)),
            "soul_bond": ("영혼유대", (200, 150, 255)),
            "time_stop": ("시간정지", (200, 255, 255)),
            "time_marked": ("시간기록", (150, 200, 255)),
            "time_savepoint": ("시간저장", (150, 200, 255)),
            "time_distortion": ("시간왜곡", (150, 200, 255)),
            "phase": ("위상변화", (200, 150, 255)),
            "transcendence": ("초월", (255, 255, 255)),
            "analyze": ("분석", (200, 200, 200)),
            "auto_turret": ("자동포탑", (255, 200, 100)),
            "repair_drone": ("수리드론", (100, 255, 200)),
            "absolute_evasion": ("절대회피", (255, 255, 200)),
            "temporary_invincible": ("일시무적", (255, 255, 150)),
            "existence_denial": ("존재부정", (150, 150, 150)),
            "truth_revelation": ("진리계시", (255, 255, 200)),
            "ghost_fleet": ("유령함대", (150, 150, 200)),
            "animal_form": ("동물변신", (139, 69, 19)),
            "divine_punishment": ("신벌", (255, 200, 100)),
            "divine_judgment": ("신심판", (255, 255, 100)),
            "heaven_gate": ("천국문", (255, 255, 200)),
            "purification": ("정화", (255, 255, 255)),
            "martyrdom": ("순교", (255, 200, 200)),
            "elemental_weapon": ("원소무기", (255, 200, 100)),
            "elemental_immunity": ("원소면역", (200, 255, 200)),
            "magic_field": ("마법진", (200, 150, 255)),
            "transmutation": ("변환술", (200, 200, 255)),
            "philosophers_stone": ("현자의돌", (255, 215, 0)),
            "undead_minion": ("언데드", (150, 0, 150)),
            "shadow_clone": ("그림자분신", (100, 50, 150)),
            "shadow_stack": ("그림자축적", (100, 50, 150)),
            "shadow_echo": ("그림자메아리", (100, 50, 150)),
            "shadow_empowered": ("그림자강화", (150, 100, 200)),
            "extra_turn": ("추가턴", (255, 255, 100)),
            "holy_mark": ("성표식", (255, 255, 200)),
            "holy_aura": ("성기운", (255, 255, 200)),
            "dragon_form": ("용변신", (255, 100, 100)),
            "warrior_stance": ("전사자세", (255, 200, 100)),
            "afterimage": ("잔상", (200, 200, 200)),
        }

        status_items = []  # (name, color, duration)
        buff_items = []  # (name, color, duration)
        debuff_items = []  # (name, color, duration)

        # 상태이상 처리
        if status_effects:
            if isinstance(status_effects, dict):
                for status, turns in status_effects.items():
                    status_key = status.lower().replace(' ', '_').replace('-', '_')
                    name, color = status_info.get(status_key, (status[:2], (200, 200, 200)))
                    status_items.append((name, color, turns))
            elif isinstance(status_effects, list):
                for effect in status_effects:
                    if hasattr(effect, 'status_type'):
                        # StatusEffect 객체
                        status_type = effect.status_type
                        if isinstance(status_type, StatusType):
                            status_key = status_type.name.lower()
                        else:
                            status_key = str(status_type).lower().replace(' ', '_')
                        name, color = status_info.get(status_key, (effect.name[:2] if hasattr(effect, 'name') else str(effect)[:2], (200, 200, 200)))
                        turns = getattr(effect, 'duration', '')
                        status_items.append((name, color, turns))
                    elif hasattr(effect, 'name'):
                        status_name = effect.name.lower().replace(' ', '_')
                        turns = getattr(effect, 'duration', '')
                        name, color = status_info.get(status_name, (effect.name[:2], (200, 200, 200)))
                        status_items.append((name, color, turns))
                    else:
                        status_name = str(effect).lower().replace(' ', '_')
                        name, color = status_info.get(status_name, (str(effect)[:2], (200, 200, 200)))
                        status_items.append((name, color, ''))
        
        # 버프 처리 (초록 계열)
        if buffs:
            for buff_name, buff_data in buffs.items():
                if isinstance(buff_data, dict):
                    duration = buff_data.get('duration', '')
                    status_key = buff_name.lower().replace(' ', '_').replace('-', '_')
                    name, color = status_info.get(status_key, (buff_name[:2], (100, 255, 100)))
                    buff_items.append((name, color, duration))
        
        # 디버프 처리 (보라 계열)
        if debuffs:
            for debuff_name, debuff_data in debuffs.items():
                if isinstance(debuff_data, dict):
                    duration = debuff_data.get('duration', '')
                    status_key = debuff_name.lower().replace(' ', '_').replace('-', '_')
                    name, color = status_info.get(status_key, (debuff_name[:2], (200, 100, 255)))
                    debuff_items.append((name, color, duration))
        
        # 모든 아이템 합치기 (상태이상, 버프, 디버프 순서)
        all_items = status_items + buff_items + debuff_items
        
        if not all_items:
            return []
        
        # 최대 3줄로 나누기 (한 줄당 최대 6개 아이템)
        max_items_per_line = 6
        max_lines = 3
        lines = []
        
        for line_idx in range(max_lines):
            start_idx = line_idx * max_items_per_line
            end_idx = start_idx + max_items_per_line
            line_items = all_items[start_idx:end_idx]
            
            if not line_items:
                break
            
            # 한 줄의 텍스트와 색상 리스트 생성
            line_text_parts = []
            line_colors = []
            
            for name, color, duration in line_items:
                text = f"{name}{duration if duration else ''}"
                line_text_parts.append(text)
                line_colors.append(color)
            
            line_text = " ".join(line_text_parts)
            # 줄의 평균 색상 계산 (또는 첫 번째 색상 사용)
            avg_color = line_colors[0] if line_colors else (200, 200, 200)
            lines.append((line_text, avg_color))
        
        return lines

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
