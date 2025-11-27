"""
게이지 렌더러

픽셀 단위 부드러운 게이지 (커스텀 타일셋 기반 32분할)
+ 애니메이션 시스템 (천천히 변화하는 효과)
+ 증가/감소 모두 트레일 애니메이션
+ 배경 밝기 기반 텍스트 색상 자동 조정
"""

from typing import Tuple, List, Optional, Dict, Any
import tcod
import tcod.console
from tcod import libtcodpy
import time
from src.core.logger import get_logger

logger = get_logger("gauge")


def get_contrast_text_color(bg_color: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """배경색 밝기에 따라 가독성 좋은 텍스트 색상 반환
    
    밝은 배경 → 검은 텍스트
    어두운 배경 → 흰색 텍스트
    """
    # 밝기 계산 (인간 눈의 색상 감도 반영)
    brightness = 0.299 * bg_color[0] + 0.587 * bg_color[1] + 0.114 * bg_color[2]
    
    if brightness > 140:
        # 밝은 배경 → 진한 색 텍스트
        return (20, 20, 20)
    else:
        # 어두운 배경 → 흰색 텍스트
        return (255, 255, 255)


def get_contrast_secondary_color(bg_color: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """배경색에 따른 보조 텍스트 색상 (최대값 표시용)"""
    brightness = 0.299 * bg_color[0] + 0.587 * bg_color[1] + 0.114 * bg_color[2]
    
    if brightness > 140:
        return (60, 60, 60)
    else:
        return (180, 180, 180)


# 게이지 타일셋 임포트 (지연 임포트로 순환 참조 방지)
_gauge_tileset_loaded = False
_gauge_tile_manager = None
_boundary_tile_fail_logged = False  # 경계 타일 실패 로깅 플래그

def _get_tile_manager():
    """게이지 타일 관리자 가져오기 (지연 로드)"""
    global _gauge_tileset_loaded, _gauge_tile_manager
    if not _gauge_tileset_loaded:
        try:
            from src.ui.gauge_tileset import get_gauge_tile_manager
            _gauge_tile_manager = get_gauge_tile_manager()
            _gauge_tileset_loaded = True
        except ImportError:
            _gauge_tile_manager = None
            _gauge_tileset_loaded = True
    return _gauge_tile_manager


class AnimatedValue:
    """애니메이션 값 - 시간에 따라 부드럽게 변화"""
    
    def __init__(self, initial_value: float = 0, duration: float = 0.5):
        """
        Args:
            initial_value: 초기 값
            duration: 변화에 걸리는 시간 (초)
        """
        self.current = initial_value  # 현재 표시 값
        self.target = initial_value   # 목표 값
        self.previous = initial_value # 이전 값 (데미지 표시용)
        self.duration = duration
        self.start_time = time.time()
        self.change_time = time.time()  # 마지막 변화 시간
        self.last_trail_change_time = time.time()  # 트레일이 마지막으로 변경된 시간 (페이드용)
        
    def set_target(self, new_target: float, delay: float = 0.0):
        """새로운 목표 값 설정
        
        Args:
            new_target: 목표 값
            delay: 애니메이션 시작 지연 시간 (초)
        """
        # delay가 제공되면 항상 업데이트 (같은 값이어도 delay 적용)
        if new_target != self.target or delay > 0.0:
            self.previous = self.current
            self.target = new_target
            self.start_time = time.time() + delay  # 지연 시간 추가
            self.change_time = time.time()
            self.delay = delay
    
    def set_trail_target(self, new_target: float):
        """트레일 목표값 설정 (즉시 설정, 애니메이션 없음)"""
        if new_target != self.target:
            self.previous = self.current
            self.target = new_target
            self.current = new_target  # 즉시 설정 (애니메이션 없음)
            self.last_trail_change_time = time.time()  # 페이드 시작 시간 기록
    
    def update(self) -> float:
        """애니메이션 업데이트 후 현재 표시 값 반환"""
        if self.current == self.target:
            return self.current
        
        current_time = time.time()
        # 지연 시간이 지나지 않았으면 이전 값 유지
        if current_time < self.start_time:
            return self.current
        
        elapsed = current_time - self.start_time
        if elapsed >= self.duration:
            self.current = self.target
        else:
            # 이징 함수 (ease-out)
            t = elapsed / self.duration
            t = 1 - (1 - t) ** 3  # cubic ease-out
            self.current = self.previous + (self.target - self.previous) * t
        
        return self.current
    
    def get_damage_trail(self) -> Tuple[float, float]:
        """데미지 트레일 범위 반환 (데미지 받은 부분 표시용)"""
        # 데미지를 받았을 때 이전 값에서 현재 값까지의 범위
        if self.target < self.previous:
            # HP 감소 (데미지)
            trail_start = self.target
            trail_end = self.current
            return (trail_start, trail_end)
        return (self.current, self.current)
    
    def is_animating(self) -> bool:
        """애니메이션 중인지 확인"""
        return abs(self.current - self.target) > 0.1


class GaugeAnimationManager:
    """게이지 애니메이션 관리자"""
    
    def __init__(self):
        self._values: Dict[str, AnimatedValue] = {}
        self._display_numbers: Dict[str, float] = {}  # 표시용 숫자 (빠르게 증감)
        self._number_text_lengths: Dict[str, int] = {}  # 이전 숫자 텍스트 길이 (남은 문자 지우기용)
        self._number_speed = 50  # 초당 변화량
        self._color_animations: Dict[str, Tuple[float, float]] = {}  # 색상 애니메이션 (key: (start_time, duration))
    
    def get_animated_value(self, key: str, actual_value: float, max_value: float, duration: float = 0.8) -> AnimatedValue:
        """애니메이션 값 가져오기 또는 생성"""
        if key not in self._values:
            anim = AnimatedValue(actual_value, duration)
            self._values[key] = anim
        else:
            anim = self._values[key]
            # duration 업데이트 (필요시)
            anim.duration = duration
        
        return anim
    
    def get_display_number(self, key: str, actual_value: float, delta_time: float = 0.016) -> int:
        """빠르게 증감하는 표시용 숫자 반환"""
        if key not in self._display_numbers:
            self._display_numbers[key] = actual_value
        
        current = self._display_numbers[key]
        diff = actual_value - current
        
        if abs(diff) < 1:
            self._display_numbers[key] = actual_value
        else:
            # 차이에 비례해서 빠르게 이동 (최소 1, 최대 diff의 30%)
            speed = max(1, min(abs(diff) * 0.3, self._number_speed * delta_time * abs(diff)))
            if diff > 0:
                self._display_numbers[key] = min(actual_value, current + speed)
            else:
                self._display_numbers[key] = max(actual_value, current - speed)
        
        return int(self._display_numbers[key])
    
    def update_all(self):
        """모든 애니메이션 업데이트"""
        for anim in self._values.values():
            anim.update()
    
    def trigger_heal_color_animation(self, key: str, duration: float = 0.6):
        """회복 시 색상 애니메이션 트리거"""
        self._color_animations[key] = (time.time(), duration)
    
    def trigger_damage_color_animation(self, key: str, duration: float = 0.3):
        """데미지 시 색상 애니메이션 트리거"""
        self._color_animations[key] = (time.time(), duration)
    
    def get_heal_color_intensity(self, key: str) -> float:
        """회복 색상 애니메이션 강도 반환 (0.0 ~ 1.0)"""
        if key not in self._color_animations:
            return 0.0
        
        start_time, duration = self._color_animations[key]
        elapsed = time.time() - start_time
        
        if elapsed >= duration:
            # 애니메이션 완료
            del self._color_animations[key]
            return 0.0
        
        # 사인파로 펄스 효과 (0 → 1 → 0)
        progress = elapsed / duration
        intensity = abs(1.0 - 2.0 * progress)  # 삼각파 형태
        return intensity
    
    def get_damage_color_intensity(self, key: str) -> float:
        """데미지 색상 애니메이션 강도 반환 (0.0 ~ 1.0) - 0.35초 동안 5번 깜빡임"""
        if key not in self._color_animations:
            return 0.0
        
        start_time, duration = self._color_animations[key]
        elapsed = time.time() - start_time
        
        if elapsed >= duration:
            # 애니메이션 완료
            del self._color_animations[key]
            return 0.0
        
        # 0.35초 동안 5번 깜빡임 (주기: 0.07초)
        blink_count = 5
        blink_period = duration / blink_count  # 0.07초
        progress = elapsed / duration
        
        # 현재 깜빡임 주기 내에서의 위치 (0.0 ~ 1.0)
        cycle_position = (elapsed % blink_period) / blink_period
        
        # 삼각파 형태로 깜빡임 (0 → 1 → 0)
        if cycle_position < 0.5:
            intensity = cycle_position * 2.0  # 0 → 1
        else:
            intensity = 2.0 - (cycle_position * 2.0)  # 1 → 0
        
        # 전체 진행도에 따라 최종 강도 감소 (선형 감소)
        overall_fade = 1.0 - progress
        intensity = intensity * overall_fade
        
        return intensity
    
    def get_low_hp_blink_intensity(self, key: str) -> float:
        """HP 낮을 때 깜빡임 강도 반환 (0.0 ~ 1.0) - 지속적으로 반복"""
        if key not in self._color_animations:
            return 0.0
        
        start_time, duration = self._color_animations[key]
        elapsed = time.time() - start_time
        
        # 깜빡임 주기: duration * 2 = 한 주기 (밝아짐 + 어두워짐)
        # 애니메이션이 계속 반복되도록 시간을 모듈로 연산
        cycle_time = elapsed % (duration * 2)
        
        if cycle_time < duration:
            # 밝아지는 구간 (0 → 1)
            progress = cycle_time / duration
            intensity = progress
        else:
            # 어두워지는 구간 (1 → 0)
            progress = (cycle_time - duration) / duration
            intensity = 1.0 - progress
        
        return intensity
    
    def clear(self):
        """모든 애니메이션 초기화"""
        self._values.clear()
        self._display_numbers.clear()
        self._color_animations.clear()


# 전역 애니메이션 관리자
_animation_manager: Optional[GaugeAnimationManager] = None

def get_animation_manager() -> GaugeAnimationManager:
    """전역 애니메이션 관리자 반환"""
    global _animation_manager
    if _animation_manager is None:
        _animation_manager = GaugeAnimationManager()
    return _animation_manager


class GaugeRenderer:
    """게이지 렌더러 - 커스텀 타일셋 기반 픽셀 단위 렌더링"""

    # 분할 수 (타일셋과 동일해야 함)
    DIVISIONS = 32
    _hp_bar_debug_logged = False  # 디버그 로깅 플래그

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

        # 타일 관리자 가져오기
        tile_manager = _get_tile_manager()
        
        # 커스텀 타일셋 사용 가능한지 확인
        use_tiles = tile_manager is not None and tile_manager.is_initialized()
        
        if use_tiles:
            # === 커스텀 타일셋 기반 픽셀 단위 렌더링 ===
            GaugeRenderer._render_pixel_bar(
                console, x, y, width, ratio, fg_color, bg_color
            )
        else:
            # === 폴백: draw_rect 기반 색상 그라디언트 ===
            # 배경 (빈 부분)
            console.draw_rect(x, y, width, 1, ord(" "), bg=bg_color)

            # 픽셀 단위 채우기
            filled_exact = ratio * width
            filled_full = int(filled_exact)
            filled_partial = filled_exact - filled_full

            # 완전히 채워진 부분
            if filled_full > 0:
                console.draw_rect(x, y, filled_full, 1, ord(" "), bg=fg_color)

            # 부분적으로 채워진 마지막 칸 (그라디언트 색상)
            if filled_partial > 0.0 and filled_full < width:
                partial_color = (
                    int(bg_color[0] + (fg_color[0] - bg_color[0]) * filled_partial),
                    int(bg_color[1] + (fg_color[1] - bg_color[1]) * filled_partial),
                    int(bg_color[2] + (fg_color[2] - bg_color[2]) * filled_partial)
                )
                console.draw_rect(x + filled_full, y, 1, 1, ord(" "), bg=partial_color)

        # 숫자 표시 - 왼쪽에 현재값, 오른쪽에 최대값
        if show_numbers:
            current_text = f"{int(current)}"
            max_text = f"{int(maximum)}"
            
            min_width_needed = len(current_text) + len(max_text) + 3
            
            if width >= min_width_needed:
                console.print(x + 1, y, current_text, fg=(255, 255, 255))
                max_text_x = x + width - len(max_text) - 1
                console.print(max_text_x, y, max_text, fg=(200, 200, 200))
            elif width >= len(current_text) + 2:
                console.print(x + 1, y, current_text, fg=(255, 255, 255))

    @staticmethod
    def _render_pixel_bar(
        console: tcod.console.Console,
        x: int, y: int, width: int,
        ratio: float,
        fg_color: Tuple[int, int, int],
        bg_color: Tuple[int, int, int]
    ) -> None:
        """픽셀 단위 게이지 렌더링 (커스텀 타일셋 기반)
        
        각 셀을 DIVISIONS 단계로 나누어 부분 채움 표현
        """
        tile_manager = _get_tile_manager()
        use_tiles = tile_manager is not None and tile_manager.is_initialized()
        divisions = GaugeRenderer.DIVISIONS
        
        # 전체 픽셀 수 (width * divisions)
        total_pixels = width * divisions
        filled_pixels = int(ratio * total_pixels)
        
        for i in range(width):
            cell_start = i * divisions
            
            # 이 셀에서 채워진 픽셀 수
            cell_filled = max(0, min(divisions, filled_pixels - cell_start))
            
            if cell_filled == 0:
                # 빈 셀 - 배경색만
                console.draw_rect(x + i, y, 1, 1, ord(" "), bg=bg_color)
            elif cell_filled >= divisions:
                # 완전히 채워진 셀 - 전경색
                console.draw_rect(x + i, y, 1, 1, ord(" "), bg=fg_color)
            else:
                # 부분 채움 - 커스텀 타일 사용
                fill_ratio = cell_filled / divisions
                
                if use_tiles:
                    color_name = GaugeRenderer._get_color_name(fg_color)
                    tile_char = tile_manager.get_tile_char(color_name, fill_ratio)
                    # fg와 bg 모두 print에 전달하여 투명 영역 처리
                    console.print(x + i, y, tile_char, fg=fg_color, bg=bg_color)
                else:
                    # 폴백: 그라디언트 색상
                    partial_color = (
                        int(bg_color[0] + (fg_color[0] - bg_color[0]) * fill_ratio),
                        int(bg_color[1] + (fg_color[1] - bg_color[1]) * fill_ratio),
                        int(bg_color[2] + (fg_color[2] - bg_color[2]) * fill_ratio)
                    )
                    console.draw_rect(x + i, y, 1, 1, ord(" "), bg=partial_color)

    @staticmethod
    def _get_color_name(color: Tuple[int, int, int]) -> str:
        """색상값으로부터 타일 색상 이름 결정"""
        r, g, b = color
        
        # 초록 계열 (HP 높음)
        if g > r and g > b:
            return 'hp_high'
        # 노랑 계열 (HP 중간)
        elif r > 150 and g > 150 and b < 100:
            return 'hp_mid'
        # 빨강 계열 (HP 낮음)
        elif r > g and r > b:
            return 'hp_low'
        # 파랑 계열 (MP)
        elif b > r and b > g:
            return 'mp_fill'
        # 금색 계열 (BRV)
        elif r > 180 and g > 140 and b < 100:
            return 'brv_fill'
        # 기본값
        return 'hp_high'

    @staticmethod
    def render_animated_hp_bar(
        console: tcod.console.Console,
        x: int,
        y: int,
        width: int,
        current_hp: float,
        max_hp: float,
        entity_id: str,
        wound_damage: float = 0,
        show_numbers: bool = True
    ) -> None:
        """
        애니메이션 HP 게이지 렌더링 (픽셀 단위 + 데미지 트레일 + 상처 표시)

        Args:
            console: TCOD 콘솔
            x, y: 게이지 위치
            width: 게이지 너비
            current_hp: 현재 HP
            max_hp: 최대 HP
            entity_id: 엔티티 고유 ID (애니메이션 추적용)
            wound_damage: 상처 데미지 (최대 HP 제한)
            show_numbers: 숫자 표시 여부
        """
        global _boundary_tile_fail_logged

        anim_mgr = get_animation_manager()
        tile_manager = _get_tile_manager()
        use_tiles = tile_manager is not None and tile_manager.is_initialized()
        divisions = GaugeRenderer.DIVISIONS

        # 디버깅: tile_manager 상태 로깅 (한 번만)
        if not GaugeRenderer._hp_bar_debug_logged:
            logger.info(f"[HP 게이지 렌더링] tile_manager={tile_manager is not None}, is_initialized={tile_manager.is_initialized() if tile_manager else False}, use_tiles={use_tiles}")
            GaugeRenderer._hp_bar_debug_logged = True
        
        # 유효 최대 HP (상처로 제한됨)
        effective_max_hp = max(1, max_hp - wound_damage)
        
        # 애니메이션 값 가져오기
        # 로거 초기화 (함수 시작 부분에서)
        from src.core.logger import get_logger
        logger_gauge = get_logger("gauge_debug")
        
        # 게이지 증감 애니메이션 제거 - 즉시 current_hp 사용
        # 이전 값 추적을 위해 anim을 사용 (트레일 페이드용)
        anim = anim_mgr.get_animated_value(f"{entity_id}_hp", current_hp, max_hp, duration=0.35)
        
        # 증가/감소 판단을 위해 목표값과 비교
        prev_target = anim.target
        is_healing = current_hp > prev_target
        is_damaging = current_hp < prev_target
        
        # 목표값 업데이트
        anim.set_target(current_hp, delay=0.0)
        
        # 게이지 애니메이션 - 부드럽게 오르내리기
        display_hp = anim.update()
        
        # 값 변경 시 반짝이는 효과 트리거
        heal_color_key = f"{entity_id}_hp_heal"
        damage_color_key = f"{entity_id}_hp_damage"
        if is_healing and heal_color_key not in anim_mgr._color_animations:
            anim_mgr.trigger_heal_color_animation(heal_color_key, duration=0.3)
        if is_damaging and damage_color_key not in anim_mgr._color_animations:
            anim_mgr.trigger_damage_color_animation(damage_color_key, duration=0.35)
        
        # 표시용 숫자 (빠르게 증감)
        display_number = anim_mgr.get_display_number(f"{entity_id}_hp_num", current_hp, 0.016)
        
        # 비율 계산
        if max_hp <= 0:
            ratio = 0.0
            display_ratio = 0.0
            wound_ratio = 0.0
        else:
            ratio = min(1.0, current_hp / max_hp)
            display_ratio = min(1.0, display_hp / max_hp)
            wound_ratio = wound_damage / max_hp
        
        # 색상 계산 (HP 비율 기준)
        if ratio > 0.6:
            fg_color = (50, 220, 50)
            bg_color = (20, 80, 20)
            color_name = 'hp_high'
        elif ratio > 0.3:
            fg_color = (220, 220, 50)
            bg_color = (80, 80, 20)
            color_name = 'hp_mid'
        else:
            fg_color = (220, 50, 50)
            bg_color = (80, 20, 20)
            color_name = 'hp_low'
        
        # === 레이어 방식 렌더링 ===
        # 레이어 순서: 1.배경 → 2.HP바 → 3.상처(HP 위에 덮어씌움)
        # 상처 제한: 최대 HP의 50%이므로 오른쪽 절반(width/2)에만 상처 렌더링
        total_pixels = width * divisions
        half_pixels = total_pixels // 2  # 게이지 중간 지점
        
        # 상처 픽셀 계산 (오른쪽 절반에만)
        wound_pixels = max(1, int(wound_ratio * total_pixels)) if wound_damage > 0 else 0
        # 상처는 최대 절반까지만 (50% 제한)
        wound_pixels = min(wound_pixels, half_pixels)
        wound_start_pixel = total_pixels - wound_pixels if wound_pixels > 0 else total_pixels
        
        # HP 픽셀 계산 (상처 시작 위치를 넘지 않도록 제한)
        hp_pixels = min(int(ratio * total_pixels), wound_start_pixel) if wound_pixels > 0 else int(ratio * total_pixels)
        display_pixels = min(int(display_ratio * total_pixels), wound_start_pixel) if wound_pixels > 0 else int(display_ratio * total_pixels)
        
        # 증가/감소 판단
        is_decreasing = display_pixels > hp_pixels
        is_increasing = display_pixels < hp_pixels
        
        # 값 변경 시 반짝이는 효과
        heal_color_key = f"{entity_id}_hp_heal"
        damage_color_key = f"{entity_id}_hp_damage"
        
        # 회복/데미지 색상 애니메이션 강도 가져오기
        heal_intensity = anim_mgr.get_heal_color_intensity(heal_color_key)
        damage_intensity = anim_mgr.get_damage_color_intensity(damage_color_key)
        
        # HP 낮을 때 깜빡임 효과 (30% 이하)
        low_hp_blink_key = f"{entity_id}_hp_low_blink"
        if ratio <= 0.3:
            # 깜빡임 애니메이션 시작 (없으면 시작, 있으면 계속 유지)
            if low_hp_blink_key not in anim_mgr._color_animations:
                anim_mgr._color_animations[low_hp_blink_key] = (time.time(), 0.5)
        else:
            # HP가 충분하면 깜빡임 중지
            if low_hp_blink_key in anim_mgr._color_animations:
                del anim_mgr._color_animations[low_hp_blink_key]
        
        # HP 낮을 때 깜빡임 강도 가져오기
        blink_intensity = anim_mgr.get_low_hp_blink_intensity(low_hp_blink_key) if ratio <= 0.3 else 0.0
        
        # 회복 시 색상 반짝임 (밝게 했다가 원래대로)
        if heal_intensity > 0:
            # 밝은 색상으로 블렌딩
            highlight_color = (
                min(255, int(fg_color[0] + (255 - fg_color[0]) * heal_intensity * 0.5)),
                min(255, int(fg_color[1] + (255 - fg_color[1]) * heal_intensity * 0.5)),
                min(255, int(fg_color[2] + (255 - fg_color[2]) * heal_intensity * 0.5))
            )
            # 원래 색상과 블렌딩
            fg_color = (
                int(fg_color[0] * (1 - heal_intensity) + highlight_color[0] * heal_intensity),
                int(fg_color[1] * (1 - heal_intensity) + highlight_color[1] * heal_intensity),
                int(fg_color[2] * (1 - heal_intensity) + highlight_color[2] * heal_intensity)
            )
        
        # 데미지 시 색상 반짝임 (주황색/빨간색 계열)
        if damage_intensity > 0:
            # 주황색 계열로 블렌딩
            damage_color = (255, 140, 0)  # 주황색
            fg_color = (
                int(fg_color[0] * (1 - damage_intensity) + damage_color[0] * damage_intensity),
                int(fg_color[1] * (1 - damage_intensity) + damage_color[1] * damage_intensity),
                int(fg_color[2] * (1 - damage_intensity) + damage_color[2] * damage_intensity)
            )
        
        # HP 낮을 때 깜빡임 효과 적용
        if blink_intensity > 0:
            # 깜빡임: 밝아졌다가 어두워짐
            blink_color = (
                int(fg_color[0] * (0.3 + 0.7 * blink_intensity)),
                int(fg_color[1] * (0.3 + 0.7 * blink_intensity)),
                int(fg_color[2] * (0.3 + 0.7 * blink_intensity))
            )
            fg_color = blink_color
        
        # 레이어 1: 전체 배경 그리기
        console.draw_rect(x, y, width, 1, ord(" "), bg=bg_color)
        
        # 중간 지점 셀 인덱스 (오른쪽 절반 시작)
        half_cell_index = width // 2
        
        # HP 렌더링용 픽셀 계산
        render_pixels = min(hp_pixels, display_pixels) if is_increasing else hp_pixels

        # 레이어 2: HP와 상처를 통합 렌더링 (픽셀 단위 정밀) - 테스트 파일 구조 따름
        # 디버그: wound_pixels 값 확인
        if wound_damage > 0 and wound_pixels == 0:
            logger_gauge.warning(f"[HP 게이지] wound_damage={wound_damage:.3f}인데 wound_pixels=0! wound_ratio={wound_ratio:.3f}, total_pixels={total_pixels}")

        # 빗금 색상 (상처가 있을 때 고정 색상, 없으면 검은색)
        if wound_pixels > 0:
            # 상처가 있을 때: 고정 검은색 (깜빡임 없음)
            wound_stripe_color = (0, 0, 0)
        else:
            # 상처가 없으면 검은색 (사용 안 함)
            wound_stripe_color = (0, 0, 0)
        
        # 각 셀의 배경 색상을 미리 계산하여 저장 (숫자 렌더링용)
        cell_bg_colors = {}
        
        for i in range(width):
            cell_start = i * divisions
            cell_end = (i + 1) * divisions
            
            # 이 셀에서 HP가 차지하는 픽셀 수 (왼쪽에서)
            cell_hp_pixels = max(0, min(divisions, render_pixels - cell_start))
            
            # 상처 픽셀 계산 (wound_start_pixel부터 오른쪽 끝까지)
            cell_wound_pixels = 0
            if wound_pixels > 0:
                # 실제 상처 영역(wound_start_pixel ~ total_pixels)과 이 셀의 겹치는 부분 계산
                wound_overlap_start = max(cell_start, wound_start_pixel)
                wound_overlap_end = min(cell_end, total_pixels)
                cell_wound_pixels = max(0, wound_overlap_end - wound_overlap_start)
            
            # 경계 셀 여부: HP와 상처가 모두 있는 경우 (둘 다 부분적이거나 하나는 전체)
            has_hp = cell_hp_pixels > 0
            has_wound = cell_wound_pixels > 0 and wound_pixels > 0  # 전체 상처가 0이 아닐 때만
            is_hp_wound_boundary = has_hp and has_wound
            
            # 디버그: 전체 상처 셀 조건 확인
            if cell_wound_pixels > 0:
                from src.core.logger import get_logger
                logger_debug = get_logger("gauge")
                logger_debug.debug(
                    f"셀 {i} 상처 정보: cell_wound_pixels={cell_wound_pixels}, "
                    f"divisions={divisions}, cell_hp_pixels={cell_hp_pixels}, "
                    f"wound_start_pixel={wound_start_pixel}, cell_start={cell_start}, cell_end={cell_end}"
                )
            
            if cell_hp_pixels >= divisions and cell_wound_pixels == 0:
                # HP가 셀 전체를 채움 (상처 없음) - draw_rect 사용 (타일 불필요)
                console.draw_rect(x + i, y, 1, 1, ord(" "), bg=fg_color)
                cell_bg_colors[i] = fg_color

            elif cell_wound_pixels >= divisions and cell_hp_pixels == 0 and wound_pixels > 0:
                # 상처가 셀 전체를 채움 (전체 상처가 있을 때만) - 동적 타일로 픽셀 단위 정밀도
                boundary_tile_char = tile_manager.create_boundary_tile(
                    hp_pixels=0,
                    wound_pixels=divisions,
                    hp_color=fg_color,
                    bg_color=bg_color,
                    wound_stripe_color=wound_stripe_color,  # 애니메이션 색상 직접 전달
                    cell_index=i,  # 셀 인덱스는 상대 인덱스 (i)
                    cell_start=cell_start,  # 셀의 시작 픽셀 위치
                    wound_start_pixel=wound_start_pixel  # 게이지 전체에서의 상처 시작점
                )
                # 경계 타일 렌더링 (fg는 사용하지 않음, 타일 내부에서 색상 직접 설정)
                console.print(x + i, y, boundary_tile_char, fg=(255, 255, 255), bg=bg_color)
                # 상처 셀은 배경 색상 사용 (빗금은 타일 내부에서 처리)
                cell_bg_colors[i] = bg_color

            elif is_hp_wound_boundary:
                # 경계 셀: HP와 상처가 모두 있는 경우 (동적 타일 생성, 색상 혼합 없음)
                # 디버그: 경계 타일 호출 확인
                if wound_pixels == 0:
                    logger_gauge.error(f"[경계 타일 호출 오류] wound_pixels=0인데 경계 타일 호출! has_hp={has_hp}, has_wound={has_wound}, cell_hp_pixels={cell_hp_pixels}, cell_wound_pixels={cell_wound_pixels}, wound_stripe_color={wound_stripe_color}")

                # 게이지 전체에서의 HP 끝점 계산: 실제 HP 끝점 사용
                # hp_pixels는 이미 wound_start_pixel을 넘지 않도록 제한되어 있음
                # cell_hp_pixels는 display_pixels 기준이므로, 실제 hp_pixels 기준으로 재계산
                actual_hp_end = min(hp_pixels, wound_start_pixel) if wound_pixels > 0 else hp_pixels
                # 셀 내에서의 실제 HP 픽셀 수 재계산
                cell_actual_hp_pixels = max(0, min(divisions, actual_hp_end - cell_start))
                hp_end_pixel = cell_start + cell_actual_hp_pixels
                
                boundary_tile_char = tile_manager.create_boundary_tile(
                    hp_pixels=cell_hp_pixels,
                    wound_pixels=cell_wound_pixels,
                    hp_color=fg_color,
                    bg_color=bg_color,
                    wound_stripe_color=wound_stripe_color,  # 애니메이션 색상 직접 전달
                    cell_index=i,  # 셀 인덱스는 상대 인덱스 (i)
                    cell_start=cell_start,  # 셀의 시작 픽셀 위치
                    wound_start_pixel=wound_start_pixel,  # 게이지 전체에서의 상처 시작점
                    hp_end_pixel=hp_end_pixel  # 게이지 전체에서의 HP 끝점
                )
                # 경계 타일 렌더링 (fg는 사용하지 않음, 타일 내부에서 색상 직접 설정)
                console.print(x + i, y, boundary_tile_char, fg=(255, 255, 255), bg=bg_color)
                # 경계 셀은 배경 색상 사용 (HP와 상처는 타일 내부에서 처리)
                cell_bg_colors[i] = bg_color
            
            elif cell_hp_pixels > 0:
                # HP가 부분적으로 있음 (상처 없음)
                fill_ratio = cell_hp_pixels / divisions
                
                if use_tiles:
                    # 빗금(상처)이 스타트 지점(wound_start_pixel)보다 왼쪽인 경우에는 빗금 타일을 보여주지 않는다.
                    # cell_end: 이 셀의 끝 픽셀 위치
                    # wound_start_pixel: 상처 시작 픽셀 위치
                    # 만약 이 셀이 전부 wound_start_pixel보다 왼쪽이면 빗금이 나오면 안됨.
                    if cell_end <= wound_start_pixel:
                        tile_char = tile_manager.get_tile_char(color_name, fill_ratio)
                        console.print(x + i, y, tile_char, fg=fg_color, bg=bg_color)
                        # 부분 HP 셀: HP 색상과 배경 색상의 혼합
                        partial_bg = (
                            int(bg_color[0] + (fg_color[0] - bg_color[0]) * fill_ratio),
                            int(bg_color[1] + (fg_color[1] - bg_color[1]) * fill_ratio),
                            int(bg_color[2] + (fg_color[2] - bg_color[2]) * fill_ratio)
                        )
                        cell_bg_colors[i] = partial_bg
                    else:
                        tile_char = tile_manager.get_tile_char(color_name, fill_ratio)
                        # fg를 wound_stripe_color로 넣으면 빗금 칠해짐, fg_color 넣으면 그냥 컬러
                        console.print(x + i, y, tile_char, fg=fg_color, bg=bg_color)
                        # 부분 HP 셀: HP 색상과 배경 색상의 혼합
                        partial_bg = (
                            int(bg_color[0] + (fg_color[0] - bg_color[0]) * fill_ratio),
                            int(bg_color[1] + (fg_color[1] - bg_color[1]) * fill_ratio),
                            int(bg_color[2] + (fg_color[2] - bg_color[2]) * fill_ratio)
                        )
                        cell_bg_colors[i] = partial_bg
                else:
                    partial_color = (
                        int(bg_color[0] + (fg_color[0] - bg_color[0]) * fill_ratio),
                        int(bg_color[1] + (fg_color[1] - bg_color[1]) * fill_ratio),
                        int(bg_color[2] + (fg_color[2] - bg_color[2]) * fill_ratio)
                    )
                    console.draw_rect(x + i, y, 1, 1, ord(" "), bg=partial_color)
            
            elif cell_wound_pixels > 0 and wound_pixels > 0:
                # 상처만 부분적으로 있음 (HP 없음, 전체 상처가 있을 때만) - 동적 타일로 픽셀 단위 정밀도
                boundary_tile_char = tile_manager.create_boundary_tile(
                    hp_pixels=0,
                    wound_pixels=cell_wound_pixels,
                    hp_color=fg_color,
                    bg_color=bg_color,
                    wound_stripe_color=wound_stripe_color,  # 애니메이션 색상 직접 전달
                    cell_index=i,  # 셀 인덱스는 상대 인덱스 (i)
                    cell_start=cell_start,  # 셀의 시작 픽셀 위치
                    wound_start_pixel=wound_start_pixel  # 게이지 전체에서의 상처 시작점
                )
                # 경계 타일 렌더링 (fg는 사용하지 않음, 타일 내부에서 색상 직접 설정)
                console.print(x + i, y, boundary_tile_char, fg=(255, 255, 255), bg=bg_color)
                # 상처만 부분적으로 있는 셀: 배경 색상 사용
                cell_bg_colors[i] = bg_color

            else:
                # 빈 셀 (HP도 상처도 없음) - 배경 색상으로 채움
                console.draw_rect(x + i, y, 1, 1, ord(" "), bg=bg_color)
                cell_bg_colors[i] = bg_color
        # 숫자 표시 (배경 밝기에 따른 가독성 좋은 색상) - 현재 HP만 표시
        # 배경을 투명하게 하여 트레일이 보이도록 함
        if show_numbers:
            current_text = f"{display_number}"
            number_key = f"{entity_id}_hp_num"
            
            # 이전 숫자 길이 확인 및 남은 문자 지우기
            prev_length = anim_mgr._number_text_lengths.get(number_key, 0)
            if len(current_text) < prev_length:
                # 이전 숫자가 더 길었으면 남은 문자를 공백으로 지움
                for i in range(len(current_text), prev_length):
                    char_x = x + 1 + i
                    if char_x < x + width:
                        console.ch[y, char_x] = ord(" ")
            
            # 현재 숫자 길이 저장
            anim_mgr._number_text_lengths[number_key] = len(current_text)
            
            # 배경색에 따른 텍스트 색상 선택
            text_color = get_contrast_text_color(fg_color)
            
            # 현재 HP 표시 (왼쪽) - 배경 투명하게 하여 트레일이 보이도록
            if width >= len(current_text) + 2:
                # 각 문자를 개별적으로 렌더링하여 배경을 유지
                for i, char in enumerate(current_text):
                    char_x = x + 1 + i
                    # 배경을 건드리지 않고 문자와 전경색만 변경 (뒤의 게이지가 보이도록)
                    console.ch[y, char_x] = ord(char)
                    console.fg[y, char_x] = text_color

    @staticmethod
    def render_animated_mp_bar(
        console: tcod.console.Console,
        x: int,
        y: int,
        width: int,
        current_mp: float,
        max_mp: float,
        entity_id: str,
        show_numbers: bool = True
    ) -> None:
        """애니메이션 MP 게이지 렌더링 (타일셋 기반)"""
        anim_mgr = get_animation_manager()
        tile_manager = _get_tile_manager()
        use_tiles = tile_manager is not None and tile_manager.is_initialized()
        divisions = GaugeRenderer.DIVISIONS
        
        # 애니메이션 값
        anim = anim_mgr.get_animated_value(f"{entity_id}_mp", current_mp, max_mp, duration=0.35)
        
        # 증가/감소 판단을 위해 목표값과 비교
        prev_target_mp = anim.target
        is_healing = current_mp > prev_target_mp
        is_damaging = current_mp < prev_target_mp
        
        # 목표값 업데이트
        anim.set_target(current_mp, delay=0.0)
        
        # 게이지 애니메이션 - 부드럽게 오르내리기
        display_mp = anim.update()
        
        # 값 변경 시 반짝이는 효과 트리거
        heal_color_key = f"{entity_id}_mp_heal"
        damage_color_key = f"{entity_id}_mp_damage"
        if is_healing and heal_color_key not in anim_mgr._color_animations:
            anim_mgr.trigger_heal_color_animation(heal_color_key, duration=0.3)
        if is_damaging and damage_color_key not in anim_mgr._color_animations:
            anim_mgr.trigger_damage_color_animation(damage_color_key, duration=0.35)
        display_number = anim_mgr.get_display_number(f"{entity_id}_mp_num", current_mp, 0.016)
        
        if max_mp <= 0:
            ratio = 0.0
            display_ratio = 0.0
        else:
            ratio = min(1.0, current_mp / max_mp)
            display_ratio = min(1.0, display_mp / max_mp)
        
        # MP 색상 (파란색 계열)
        if ratio > 0.6:
            fg_color = (80, 150, 255)
            bg_color = (30, 60, 120)
        elif ratio > 0.3:
            fg_color = (60, 120, 200)
            bg_color = (25, 50, 90)
        else:
            fg_color = (40, 90, 150)
            bg_color = (20, 40, 70)
        
        # === 픽셀 단위 렌더링 (레이어 방식) ===
        total_pixels = width * divisions
        mp_pixels = int(ratio * total_pixels)
        display_pixels = int(display_ratio * total_pixels)
        
        is_decreasing = display_pixels > mp_pixels
        is_increasing = display_pixels < mp_pixels
        
        # 값 변경 시 반짝이는 효과
        heal_color_key = f"{entity_id}_mp_heal"
        damage_color_key = f"{entity_id}_mp_damage"
        
        # 회복/데미지 색상 애니메이션 강도 가져오기
        heal_intensity = anim_mgr.get_heal_color_intensity(heal_color_key)
        damage_intensity = anim_mgr.get_damage_color_intensity(damage_color_key)
        
        # 회복 시 색상 반짝임 (밝게 했다가 원래대로)
        if heal_intensity > 0:
            # 밝은 색상으로 블렌딩
            highlight_color = (
                min(255, int(fg_color[0] + (255 - fg_color[0]) * heal_intensity * 0.5)),
                min(255, int(fg_color[1] + (255 - fg_color[1]) * heal_intensity * 0.5)),
                min(255, int(fg_color[2] + (255 - fg_color[2]) * heal_intensity * 0.5))
            )
            # 원래 색상과 블렌딩
            fg_color = (
                int(fg_color[0] * (1 - heal_intensity) + highlight_color[0] * heal_intensity),
                int(fg_color[1] * (1 - heal_intensity) + highlight_color[1] * heal_intensity),
                int(fg_color[2] * (1 - heal_intensity) + highlight_color[2] * heal_intensity)
            )
        
        # 레이어 1: 배경
        console.draw_rect(x, y, width, 1, ord(" "), bg=bg_color)

        # 레이어 2: 현재 MP
        render_pixels = min(mp_pixels, display_pixels) if is_increasing else mp_pixels
        
        # 각 셀의 배경 색상을 미리 계산하여 저장 (숫자 렌더링용)
        cell_bg_colors = {}
        
        for i in range(width):
            cell_start = i * divisions
            cell_end = (i + 1) * divisions
            
            cell_mp = max(0, min(divisions, render_pixels - cell_start))
            
            if cell_mp >= divisions:
                console.draw_rect(x + i, y, 1, 1, ord(" "), bg=fg_color)
                cell_bg_colors[i] = fg_color
            elif cell_mp > 0:
                fill_ratio = cell_mp / divisions
                cell_unfilled = divisions - cell_mp
                
                blended_bg = bg_color
                
                if use_tiles:
                    tile_char = tile_manager.get_tile_char('mp_fill', fill_ratio)
                    console.print(x + i, y, tile_char, fg=fg_color, bg=blended_bg)
                else:
                    partial_color = (
                        int(blended_bg[0] + (fg_color[0] - blended_bg[0]) * fill_ratio),
                        int(blended_bg[1] + (fg_color[1] - blended_bg[1]) * fill_ratio),
                        int(blended_bg[2] + (fg_color[2] - blended_bg[2]) * fill_ratio)
                    )
                    console.draw_rect(x + i, y, 1, 1, ord(" "), bg=partial_color)
                # 부분 MP 셀: MP 색상과 배경 색상의 혼합
                partial_bg = (
                    int(blended_bg[0] + (fg_color[0] - blended_bg[0]) * fill_ratio),
                    int(blended_bg[1] + (fg_color[1] - blended_bg[1]) * fill_ratio),
                    int(blended_bg[2] + (fg_color[2] - blended_bg[2]) * fill_ratio)
                )
                cell_bg_colors[i] = partial_bg
            else:
                # 빈 셀
                cell_bg_colors[i] = bg_color
        
        # 숫자 표시 - 현재 MP만 표시
        # 배경을 투명하게 하여 트레일이 보이도록 함
        if show_numbers:
            current_text = f"{display_number}"
            number_key = f"{entity_id}_mp_num"
            
            # 이전 숫자 길이 확인 및 남은 문자 지우기
            prev_length = anim_mgr._number_text_lengths.get(number_key, 0)
            if len(current_text) < prev_length:
                # 이전 숫자가 더 길었으면 남은 문자를 공백으로 지움
                for i in range(len(current_text), prev_length):
                    char_x = x + 1 + i
                    if char_x < x + width:
                        console.ch[y, char_x] = ord(" ")
            
            # 현재 숫자 길이 저장
            anim_mgr._number_text_lengths[number_key] = len(current_text)
            
            text_color = get_contrast_text_color(fg_color)
            
            if width >= len(current_text) + 2:
                # 각 문자를 개별적으로 렌더링하여 배경을 유지
                for i, char in enumerate(current_text):
                    char_x = x + 1 + i
                    # 배경을 건드리지 않고 문자와 전경색만 변경 (뒤의 게이지가 보이도록)
                    console.ch[y, char_x] = ord(char)
                    console.fg[y, char_x] = text_color

    @staticmethod
    def render_animated_brv_bar(
        console: tcod.console.Console,
        x: int,
        y: int,
        width: int,
        current_brv: float,
        max_brv: float,
        entity_id: str,
        is_broken: bool = False,
        show_numbers: bool = True
    ) -> None:
        """애니메이션 BRV 게이지 렌더링 (타일셋 기반)"""
        anim_mgr = get_animation_manager()
        tile_manager = _get_tile_manager()
        use_tiles = tile_manager is not None and tile_manager.is_initialized()
        divisions = GaugeRenderer.DIVISIONS
        
        # 애니메이션 값
        anim = anim_mgr.get_animated_value(f"{entity_id}_brv", current_brv, max_brv, duration=0.35)
        
        # 증가/감소 판단을 위해 목표값과 비교
        prev_target_brv = anim.target
        is_healing = current_brv > prev_target_brv
        is_damaging = current_brv < prev_target_brv
        
        # 목표값 업데이트
        anim.set_target(current_brv, delay=0.0)
        
        # 게이지 애니메이션 - 부드럽게 오르내리기
        display_brv = anim.update()
        
        # 값 변경 시 반짝이는 효과 트리거
        heal_color_key = f"{entity_id}_brv_heal"
        damage_color_key = f"{entity_id}_brv_damage"
        if is_healing and heal_color_key not in anim_mgr._color_animations:
            anim_mgr.trigger_heal_color_animation(heal_color_key, duration=0.3)
        if is_damaging and damage_color_key not in anim_mgr._color_animations:
            anim_mgr.trigger_damage_color_animation(damage_color_key, duration=0.35)
        display_number = anim_mgr.get_display_number(f"{entity_id}_brv_num", current_brv, 0.016)
        
        if max_brv <= 0:
            ratio = 0.0
            display_ratio = 0.0
        else:
            ratio = min(1.0, current_brv / max_brv)
            display_ratio = min(1.0, display_brv / max_brv)
        
        # BRV 색상 (노란색 계열 통일, 100%일 때만 핑크색, BREAK 시 빨간색)
        if is_broken:
            fg_color = (150, 50, 50)
            bg_color = (60, 20, 20)
        elif ratio >= 1.0:
            # 100%일 때 핑크색
            fg_color = (255, 192, 203)  # 핑크색
            bg_color = (120, 90, 95)
        else:
            # 그 외에는 노란 계열 통일
            fg_color = (255, 220, 80)  # 노란색
            bg_color = (100, 85, 30)
        
        # === 픽셀 단위 렌더링 (레이어 방식) ===
        total_pixels = width * divisions
        brv_pixels = int(ratio * total_pixels)
        display_pixels = int(display_ratio * total_pixels)
        
        is_decreasing = display_pixels > brv_pixels
        is_increasing = display_pixels < brv_pixels
        
        # 값 변경 시 반짝이는 효과
        heal_color_key = f"{entity_id}_brv_heal"
        damage_color_key = f"{entity_id}_brv_damage"
        
        # 회복/데미지 색상 애니메이션 강도 가져오기
        heal_intensity = anim_mgr.get_heal_color_intensity(heal_color_key)
        damage_intensity = anim_mgr.get_damage_color_intensity(damage_color_key)
        
        # 회복 시 색상 반짝임 (밝게 했다가 원래대로)
        if heal_intensity > 0:
            # 밝은 색상으로 블렌딩
            highlight_color = (
                min(255, int(fg_color[0] + (255 - fg_color[0]) * heal_intensity * 0.5)),
                min(255, int(fg_color[1] + (255 - fg_color[1]) * heal_intensity * 0.5)),
                min(255, int(fg_color[2] + (255 - fg_color[2]) * heal_intensity * 0.5))
            )
            # 원래 색상과 블렌딩
            fg_color = (
                int(fg_color[0] * (1 - heal_intensity) + highlight_color[0] * heal_intensity),
                int(fg_color[1] * (1 - heal_intensity) + highlight_color[1] * heal_intensity),
                int(fg_color[2] * (1 - heal_intensity) + highlight_color[2] * heal_intensity)
            )
        
        # 데미지 시 색상 반짝임 (주황색/빨간색 계열)
        if damage_intensity > 0:
            # 주황색 계열로 블렌딩
            damage_color = (255, 140, 0)  # 주황색
            fg_color = (
                int(fg_color[0] * (1 - damage_intensity) + damage_color[0] * damage_intensity),
                int(fg_color[1] * (1 - damage_intensity) + damage_color[1] * damage_intensity),
                int(fg_color[2] * (1 - damage_intensity) + damage_color[2] * damage_intensity)
            )
        
        # 레이어 1: 배경
        console.draw_rect(x, y, width, 1, ord(" "), bg=bg_color)

        # 레이어 2: 현재 BRV (트레일 위에 렌더링)
        render_pixels = min(brv_pixels, display_pixels) if is_increasing else brv_pixels
        
        # 각 셀의 배경 색상을 미리 계산하여 저장 (숫자 렌더링용)
        cell_bg_colors = {}
        
        for i in range(width):
            cell_start = i * divisions
            cell_end = (i + 1) * divisions
            
            cell_brv = max(0, min(divisions, render_pixels - cell_start))
            
            if cell_brv >= divisions:
                console.draw_rect(x + i, y, 1, 1, ord(" "), bg=fg_color)
                cell_bg_colors[i] = fg_color
            elif cell_brv > 0:
                fill_ratio = cell_brv / divisions
                blended_bg = bg_color
                
                if use_tiles:
                    tile_char = tile_manager.get_tile_char('brv_fill', fill_ratio)
                    console.print(x + i, y, tile_char, fg=fg_color, bg=blended_bg)
                else:
                    partial_color = (
                        int(blended_bg[0] + (fg_color[0] - blended_bg[0]) * fill_ratio),
                        int(blended_bg[1] + (fg_color[1] - blended_bg[1]) * fill_ratio),
                        int(blended_bg[2] + (fg_color[2] - blended_bg[2]) * fill_ratio)
                    )
                    console.draw_rect(x + i, y, 1, 1, ord(" "), bg=partial_color)
                # 부분 BRV 셀: BRV 색상과 배경 색상의 혼합
                partial_bg = (
                    int(blended_bg[0] + (fg_color[0] - blended_bg[0]) * fill_ratio),
                    int(blended_bg[1] + (fg_color[1] - blended_bg[1]) * fill_ratio),
                    int(blended_bg[2] + (fg_color[2] - blended_bg[2]) * fill_ratio)
                )
                cell_bg_colors[i] = partial_bg
            else:
                # 빈 셀
                cell_bg_colors[i] = bg_color
        
        # 숫자 - 테두리 효과로 가독성 향상
        # 배경을 투명하게 하여 트레일이 보이도록 함
        if show_numbers:
            if is_broken:
                text = "BREAK!"
                text_x = x + (width - len(text)) // 2
                if text_x >= x:
                    # BREAK 상태는 빨간 배경이므로 흰색 텍스트
                    # 배경을 투명하게 하여 트레일이 보이도록
                    for i, char in enumerate(text):
                        # 기존 배경을 읽어서 유지
                        ch, fg_old, bg_old = console.rgb[y, text_x + i]
                        # 문자와 전경색만 변경, 배경은 유지
                        console.rgb[y, text_x + i] = (ord(char), (255, 255, 255), bg_old)
            else:
                current_text = f"{display_number}"
                number_key = f"{entity_id}_brv_num"
                
                # 이전 숫자 길이 확인 및 남은 문자 지우기
                prev_length = anim_mgr._number_text_lengths.get(number_key, 0)
                if len(current_text) < prev_length:
                    # 이전 숫자가 더 길었으면 남은 문자를 공백으로 지움
                    for i in range(len(current_text), prev_length):
                        char_x = x + 1 + i
                        if char_x < x + width:
                            console.ch[y, char_x] = ord(" ")
                
                # 현재 숫자 길이 저장
                anim_mgr._number_text_lengths[number_key] = len(current_text)
                
                text_color = get_contrast_text_color(fg_color)
                
                if width >= len(current_text) + 2:
                    # 각 문자를 개별적으로 렌더링하여 배경을 유지
                    for i, char in enumerate(current_text):
                        char_x = x + 1 + i
                        # 배경을 건드리지 않고 문자와 전경색만 변경 (뒤의 게이지가 보이도록)
                        console.ch[y, char_x] = ord(char)
                        console.fg[y, char_x] = text_color

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
        퍼센트 게이지 렌더링 (픽셀 단위)

        Args:
            console: TCOD 콘솔
            x, y: 게이지 위치
            width: 게이지 너비
            percentage: 0.0 ~ 1.0
            show_percent: 퍼센트 표시 여부
            custom_color: 커스텀 색상
        """
        tile_manager = _get_tile_manager()
        use_tiles = tile_manager is not None and tile_manager.is_initialized()
        divisions = GaugeRenderer.DIVISIONS
        
        ratio = min(1.0, max(0.0, percentage))

        # 색상
        if custom_color:
            fg_color = custom_color
            bg_color = tuple(c // 2 for c in custom_color)
        else:
            if ratio > 0.6:
                fg_color = (0, 200, 0)
                bg_color = (0, 100, 0)
            elif ratio > 0.3:
                fg_color = (200, 200, 0)
                bg_color = (100, 100, 0)
            else:
                fg_color = (200, 0, 0)
                bg_color = (100, 0, 0)

        # === 픽셀 단위 렌더링 ===
        total_pixels = width * divisions
        filled_pixels = int(ratio * total_pixels)
        
        for i in range(width):
            cell_start = i * divisions
            cell_filled = max(0, min(divisions, filled_pixels - cell_start))
            
            if cell_filled >= divisions:
                console.draw_rect(x + i, y, 1, 1, ord(" "), bg=fg_color)
            elif cell_filled > 0:
                if use_tiles:
                    fill_ratio = cell_filled / divisions
                    color_name = GaugeRenderer._get_color_name(fg_color)
                    tile_char = tile_manager.get_tile_char(color_name, fill_ratio)
                    console.draw_rect(x + i, y, 1, 1, ord(" "), bg=bg_color)
                    console.print(x + i, y, tile_char, fg=fg_color)
                else:
                    partial_ratio = cell_filled / divisions
                    partial_color = (
                        int(bg_color[0] + (fg_color[0] - bg_color[0]) * partial_ratio),
                        int(bg_color[1] + (fg_color[1] - bg_color[1]) * partial_ratio),
                        int(bg_color[2] + (fg_color[2] - bg_color[2]) * partial_ratio)
                    )
                    console.draw_rect(x + i, y, 1, 1, ord(" "), bg=partial_color)
            else:
                console.draw_rect(x + i, y, 1, 1, ord(" "), bg=bg_color)

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
        캐스팅 게이지 렌더링 (픽셀 단위)

        Args:
            console: TCOD 콘솔
            x, y: 게이지 위치
            width: 게이지 너비
            progress: 진행도 (0.0 ~ 1.0)
            skill_name: 스킬 이름
        """
        tile_manager = _get_tile_manager()
        use_tiles = tile_manager is not None and tile_manager.is_initialized()
        divisions = GaugeRenderer.DIVISIONS
        
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

        # === 픽셀 단위 렌더링 ===
        total_pixels = bar_width * divisions
        filled_pixels = int(ratio * total_pixels)
        
        for i in range(bar_width):
            cell_start = i * divisions
            cell_filled = max(0, min(divisions, filled_pixels - cell_start))
            
            if cell_filled >= divisions:
                console.draw_rect(bar_x + i, y, 1, 1, ord(" "), bg=fg_color)
            elif cell_filled > 0:
                if use_tiles:
                    fill_ratio = cell_filled / divisions
                    tile_char = tile_manager.get_tile_char('cast_fill', fill_ratio)
                    console.draw_rect(bar_x + i, y, 1, 1, ord(" "), bg=bg_color)
                    console.print(bar_x + i, y, tile_char, fg=fg_color)
                else:
                    partial_ratio = cell_filled / divisions
                    partial_color = (
                        int(bg_color[0] + (fg_color[0] - bg_color[0]) * partial_ratio),
                        int(bg_color[1] + (fg_color[1] - bg_color[1]) * partial_ratio),
                        int(bg_color[2] + (fg_color[2] - bg_color[2]) * partial_ratio)
                    )
                    console.draw_rect(bar_x + i, y, 1, 1, ord(" "), bg=partial_color)
            else:
                console.draw_rect(bar_x + i, y, 1, 1, ord(" "), bg=bg_color)

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
        maximum: float,
        entity_id: str = None
    ) -> None:
        """
        ATB 게이지 렌더링 (픽셀 단위, 커스텀 타일 기반)
        감소할 때만 애니메이션 적용

        Args:
            console: TCOD 콘솔
            x, y: 게이지 위치
            width: 게이지 너비
            current: 현재 ATB 값
            threshold: 행동 가능 임계값
            maximum: 최대 ATB 값
            entity_id: 엔티티 ID (감소 애니메이션 추적용)
        """
        anim_mgr = get_animation_manager()
        tile_manager = _get_tile_manager()
        use_tiles = tile_manager is not None and tile_manager.is_initialized()
        divisions = GaugeRenderer.DIVISIONS
        
        # 감소할 때만 애니메이션 사용
        display_atb = current
        if entity_id:
            anim_key = f"{entity_id}_atb"
            if anim_key not in anim_mgr._values:
                anim_mgr._values[anim_key] = AnimatedValue(current, duration=0.25)
            
            anim = anim_mgr._values[anim_key]
            previous_display = anim.current
            
            # 감소 중이면 애니메이션, 증가/유지면 즉시 업데이트
            if current < previous_display:
                # 감소 중 → 애니메이션
                anim.set_target(current)
                display_atb = anim.update()
            else:
                # 증가/유지 → 즉시 표시
                anim.current = current
                anim.target = current
                anim.previous = current
                display_atb = current
        
        if maximum <= 0:
            ratio = 0.0
        else:
            ratio = min(1.0, display_atb / maximum)

        # 행동 가능 여부에 따른 색상 변경
        is_ready = current >= threshold
        if is_ready:
            fg_color = (150, 220, 255)  # 밝은 하늘색 (행동 가능)
            bg_color = (60, 90, 140)
        else:
            fg_color = (100, 150, 255)  # 기본 파란색
            bg_color = (50, 75, 125)

        # === 픽셀 단위 렌더링 (커스텀 타일 기반) ===
        total_pixels = width * divisions
        atb_pixels = int(ratio * total_pixels)
        
        # 배경
        console.draw_rect(x, y, width, 1, ord(" "), bg=bg_color)
        
        # 현재 ATB
        for i in range(width):
            cell_start = i * divisions
            cell_filled = max(0, min(divisions, atb_pixels - cell_start))
            
            if cell_filled >= divisions:
                console.draw_rect(x + i, y, 1, 1, ord(" "), bg=fg_color)
            elif cell_filled > 0:
                if use_tiles:
                    fill_ratio = cell_filled / divisions
                    tile_char = tile_manager.get_tile_char('atb_fill', fill_ratio)
                    console.print(x + i, y, tile_char, fg=fg_color, bg=bg_color)
                else:
                    partial_ratio = cell_filled / divisions
                    partial_color = (
                        int(bg_color[0] + (fg_color[0] - bg_color[0]) * partial_ratio),
                        int(bg_color[1] + (fg_color[1] - bg_color[1]) * partial_ratio),
                        int(bg_color[2] + (fg_color[2] - bg_color[2]) * partial_ratio)
                    )
                    console.draw_rect(x + i, y, 1, 1, ord(" "), bg=partial_color)

        # 행동 가능 임계값 표시 (세로선)
        threshold_ratio = threshold / maximum if maximum > 0 else 0
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
        is_casting: bool = False,
        entity_id: str = None,
        is_current_actor: bool = False
    ) -> None:
        """
        ATB 게이지와 캐스팅 진행도를 함께 렌더링 (커스텀 타일 기반)
        감소할 때만 애니메이션 적용

        Args:
            console: TCOD 콘솔
            x, y: 게이지 위치
            width: 게이지 너비
            atb_current: 현재 ATB 값
            atb_threshold: 행동 가능 임계값
            atb_maximum: 최대 ATB 값
            cast_progress: 캐스팅 진행도 (0.0 ~ 1.0)
            is_casting: 캐스팅 중 여부
            entity_id: 엔티티 ID (감소 애니메이션 추적용)
            is_current_actor: 현재 행동 중인 아군 여부 (반짝임 효과)
        """
        import math
        anim_mgr = get_animation_manager()
        
        # 감소할 때만 애니메이션 사용
        display_atb = atb_current
        if entity_id:
            anim_key = f"{entity_id}_atb2"
            if anim_key not in anim_mgr._values:
                anim_mgr._values[anim_key] = AnimatedValue(atb_current, duration=0.25)
            
            anim = anim_mgr._values[anim_key]
            previous_display = anim.current
            
            # 감소 중이면 애니메이션, 증가/유지면 즉시 업데이트
            if atb_current < previous_display:
                # 감소 중 → 애니메이션
                anim.set_target(atb_current)
                display_atb = anim.update()
            else:
                # 증가/유지 → 즉시 표시
                anim.current = atb_current
                anim.target = atb_current
                anim.previous = atb_current
                display_atb = atb_current
        
        # ATB를 임계값(threshold) 기준으로 표시 (0~threshold = 0~100%)
        # threshold 이상은 오버플로우로 최대 2배까지 표시
        if atb_threshold <= 0:
            atb_ratio = 0.0
        else:
            atb_ratio = min(2.0, display_atb / atb_threshold)

        # 반짝임 효과 계산 (현재 행동 중인 아군)
        pulse = 0.0
        if is_current_actor:
            # 사인파로 0.3 ~ 1.0 사이를 빠르게 진동 (초당 3회)
            pulse = 0.35 + 0.35 * math.sin(time.time() * 6 * math.pi)
        
        # ATB 색상 (현재 행동자면 밝은 금색으로 반짝임)
        if is_current_actor:
            # 금색 계열로 반짝임
            base_fg = (255, 215, 100)
            base_bg = (100, 85, 40)
            atb_fg = (
                int(base_fg[0] * (0.7 + pulse * 0.3)),
                int(base_fg[1] * (0.7 + pulse * 0.3)),
                int(min(255, base_fg[2] * (0.5 + pulse * 0.5)))
            )
            atb_bg = (
                int(base_bg[0] * (0.8 + pulse * 0.2)),
                int(base_bg[1] * (0.8 + pulse * 0.2)),
                int(base_bg[2] * (0.8 + pulse * 0.2))
            )
            overflow_fg = (255, 240, 150)
        else:
            # 일반 ATB 색상 (연한 하늘색)
            atb_fg = (135, 206, 235)
            atb_bg = (67, 103, 117)
            overflow_fg = (173, 216, 230)

        # 캐스팅 색상 (보라색/자홍색)
        cast_fg = (200, 100, 255)
        cast_bg = (100, 50, 125)

        # 픽셀 단위 렌더링을 위한 설정
        tile_manager = _get_tile_manager()
        use_tiles = tile_manager is not None and tile_manager.is_initialized()
        divisions = GaugeRenderer.DIVISIONS
        
        # === 픽셀 단위 렌더링 (커스텀 타일 기반) ===
        total_pixels = width * divisions
        
        # ATB 게이지 (100%까지)
        normal_ratio = min(1.0, atb_ratio)
        atb_pixels = int(normal_ratio * total_pixels)
        
        # 오버플로우 (100% 초과분)
        overflow_pixels = 0
        if atb_ratio > 1.0:
            overflow_ratio = min(1.0, atb_ratio - 1.0)
            overflow_pixels = int(overflow_ratio * total_pixels)
        
        # 캐스팅 진행도
        cast_pixels = 0
        if is_casting and cast_progress > 0.0:
            cast_pixels = int(cast_progress * total_pixels)
        
        # 레이어 1: 배경
        console.draw_rect(x, y, width, 1, ord(" "), bg=atb_bg)
        
        # 레이어 2: 오버플로우 (100% 초과분, 최상단)
        if overflow_pixels > 0:
            for i in range(width):
                cell_start = i * divisions
                cell_end = (i + 1) * divisions
                
                cell_overflow = max(0, min(divisions, overflow_pixels - cell_start))
                
                if cell_overflow >= divisions:
                    console.draw_rect(x + i, y, 1, 1, ord(" "), bg=overflow_fg)
                elif cell_overflow > 0:
                    fill_ratio = cell_overflow / divisions
                    if use_tiles:
                        tile_char = tile_manager.get_tile_char('atb_fill', fill_ratio)
                        console.print(x + i, y, tile_char, fg=overflow_fg, bg=atb_bg)
                    else:
                        partial_color = (
                            int(atb_bg[0] + (overflow_fg[0] - atb_bg[0]) * fill_ratio),
                            int(atb_bg[1] + (overflow_fg[1] - atb_bg[1]) * fill_ratio),
                            int(atb_bg[2] + (overflow_fg[2] - atb_bg[2]) * fill_ratio)
                        )
                        console.draw_rect(x + i, y, 1, 1, ord(" "), bg=partial_color)
        
        # 레이어 3: ATB 게이지 (100%까지)
        for i in range(width):
            cell_start = i * divisions
            cell_end = (i + 1) * divisions
            
            cell_atb = max(0, min(divisions, atb_pixels - cell_start))
            
            if cell_atb >= divisions:
                console.draw_rect(x + i, y, 1, 1, ord(" "), bg=atb_fg)
            elif cell_atb > 0:
                fill_ratio = cell_atb / divisions
                if use_tiles:
                    tile_char = tile_manager.get_tile_char('atb_fill', fill_ratio)
                    console.print(x + i, y, tile_char, fg=atb_fg, bg=atb_bg)
                else:
                    partial_color = (
                        int(atb_bg[0] + (atb_fg[0] - atb_bg[0]) * fill_ratio),
                        int(atb_bg[1] + (atb_fg[1] - atb_bg[1]) * fill_ratio),
                        int(atb_bg[2] + (atb_fg[2] - atb_bg[2]) * fill_ratio)
                    )
                    console.draw_rect(x + i, y, 1, 1, ord(" "), bg=partial_color)
        
        # 레이어 4: 캐스팅 진행도 (오버레이)
        if cast_pixels > 0:
            for i in range(width):
                cell_start = i * divisions
                cell_end = (i + 1) * divisions
                
                cell_cast = max(0, min(divisions, cast_pixels - cell_start))
                
                if cell_cast >= divisions:
                    console.draw_rect(x + i, y, 1, 1, ord(" "), bg=cast_fg)
                elif cell_cast > 0:
                    fill_ratio = cell_cast / divisions
                    if use_tiles:
                        tile_char = tile_manager.get_tile_char('cast_fill', fill_ratio)
                        console.print(x + i, y, tile_char, fg=cast_fg, bg=atb_bg)
                    else:
                        partial_color = (
                            int(atb_bg[0] + (cast_fg[0] - atb_bg[0]) * fill_ratio),
                            int(atb_bg[1] + (cast_fg[1] - atb_bg[1]) * fill_ratio),
                            int(atb_bg[2] + (cast_fg[2] - atb_bg[2]) * fill_ratio)
                        )
                        console.draw_rect(x + i, y, 1, 1, ord(" "), bg=partial_color)

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
        # 배경을 투명하게 하여 트레일이 보이도록 함
        for i, char in enumerate(text):
            # 기존 배경을 읽어서 유지
            ch, fg_old, bg_old = console.rgb[y, text_x + i]
            # 문자와 전경색만 변경, 배경은 유지
            console.rgb[y, text_x + i] = (ord(char), (255, 255, 255), bg_old)

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
