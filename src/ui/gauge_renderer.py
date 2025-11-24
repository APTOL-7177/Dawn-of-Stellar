"""
게이지 렌더러

픽셀 단위 부드러운 게이지 (커스텀 타일셋 기반 32분할)
+ 애니메이션 시스템 (천천히 변화하는 효과)
+ 증가/감소 모두 트레일 애니메이션
+ 글씨 테두리 효과 (가독성 향상)
"""

from typing import Tuple, List, Optional, Dict, Any
import tcod.console
import time


def print_outlined_text(console: tcod.console.Console, x: int, y: int, text: str, 
                        fg: Tuple[int, int, int] = (255, 255, 255),
                        outline: Tuple[int, int, int] = (0, 0, 0)) -> None:
    """테두리가 있는 텍스트 출력 (가독성 향상)"""
    # 검은 테두리 (8방향)
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx == 0 and dy == 0:
                continue
            console.print(x + dx, y + dy, text, fg=outline)
    # 메인 텍스트
    console.print(x, y, text, fg=fg)

# 게이지 타일셋 임포트 (지연 임포트로 순환 참조 방지)
_gauge_tileset_loaded = False
_gauge_tile_manager = None

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
        
    def set_target(self, new_target: float):
        """새로운 목표 값 설정"""
        if new_target != self.target:
            self.previous = self.current
            self.target = new_target
            self.start_time = time.time()
            self.change_time = time.time()
    
    def update(self) -> float:
        """애니메이션 업데이트 후 현재 표시 값 반환"""
        if self.current == self.target:
            return self.current
        
        elapsed = time.time() - self.start_time
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
        self._number_speed = 50  # 초당 변화량
    
    def get_animated_value(self, key: str, actual_value: float, max_value: float, duration: float = 0.8) -> AnimatedValue:
        """애니메이션 값 가져오기 또는 생성"""
        if key not in self._values:
            self._values[key] = AnimatedValue(actual_value, duration)
        
        anim = self._values[key]
        anim.set_target(actual_value)
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
    
    def clear(self):
        """모든 애니메이션 초기화"""
        self._values.clear()
        self._display_numbers.clear()


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
        anim_mgr = get_animation_manager()
        tile_manager = _get_tile_manager()
        use_tiles = tile_manager is not None and tile_manager.is_initialized()
        divisions = GaugeRenderer.DIVISIONS
        
        # 유효 최대 HP (상처로 제한됨)
        effective_max_hp = max(1, max_hp - wound_damage)
        
        # 애니메이션 값 가져오기
        anim = anim_mgr.get_animated_value(f"{entity_id}_hp", current_hp, max_hp, duration=0.8)
        display_hp = anim.update()
        
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
        
        # 데미지 트레일 (감소) / 회복 트레일 (증가)
        damage_trail_color = (200, 100, 50)  # 주황색 (감소)
        heal_trail_color = (100, 255, 150)   # 밝은 녹색 (증가)
        wound_color = (40, 30, 30)
        
        # === 레이어 방식 렌더링 ===
        total_pixels = width * divisions
        hp_pixels = int(ratio * total_pixels)
        display_pixels = int(display_ratio * total_pixels)
        wound_pixels = max(1, int(wound_ratio * total_pixels)) if wound_damage > 0 else 0
        
        # 증가/감소 판단
        is_decreasing = display_pixels > hp_pixels
        is_increasing = display_pixels < hp_pixels
        
        # 트레일 색상 선택
        trail_color = damage_trail_color if is_decreasing else heal_trail_color
        
        # 레이어 1: 전체 배경 그리기
        console.draw_rect(x, y, width, 1, ord(" "), bg=bg_color)
        
        # 레이어 2: 상처 영역 (오른쪽에서 왼쪽으로)
        if wound_pixels > 0:
            wound_start_pixel = total_pixels - wound_pixels
            for i in range(width):
                cell_start = i * divisions
                cell_end = (i + 1) * divisions
                
                overlap_start = max(cell_start, wound_start_pixel)
                overlap_end = min(cell_end, total_pixels)
                cell_wound = max(0, overlap_end - overlap_start)
                
                if cell_wound >= divisions:
                    console.draw_rect(x + i, y, 1, 1, ord(" "), bg=wound_color)
                elif cell_wound > 0:
                    fill_ratio = cell_wound / divisions
                    if use_tiles:
                        tile_char = tile_manager.get_tile_char('wound', fill_ratio)
                        console.print(x + i, y, tile_char, fg=wound_color, bg=bg_color)
                    else:
                        partial_color = (
                            int(bg_color[0] + (wound_color[0] - bg_color[0]) * fill_ratio),
                            int(bg_color[1] + (wound_color[1] - bg_color[1]) * fill_ratio),
                            int(bg_color[2] + (wound_color[2] - bg_color[2]) * fill_ratio)
                        )
                        console.draw_rect(x + i, y, 1, 1, ord(" "), bg=partial_color)
        
        # 레이어 3: 트레일 (감소 또는 증가 애니메이션)
        if is_decreasing:
            # 감소: hp_pixels ~ display_pixels 범위에 트레일
            for i in range(width):
                cell_start = i * divisions
                cell_end = (i + 1) * divisions
                
                cell_hp = max(0, min(divisions, hp_pixels - cell_start))
                if cell_hp > 0:
                    continue
                
                trail_start = max(cell_start, hp_pixels)
                trail_end = min(cell_end, display_pixels)
                cell_trail = max(0, trail_end - trail_start)
                
                if cell_trail >= divisions:
                    console.draw_rect(x + i, y, 1, 1, ord(" "), bg=trail_color)
                elif cell_trail > 0:
                    fill_ratio = cell_trail / divisions
                    if use_tiles:
                        tile_char = tile_manager.get_tile_char('damage_trail', fill_ratio)
                        console.print(x + i, y, tile_char, fg=trail_color, bg=bg_color)
                    else:
                        partial_color = (
                            int(bg_color[0] + (trail_color[0] - bg_color[0]) * fill_ratio),
                            int(bg_color[1] + (trail_color[1] - bg_color[1]) * fill_ratio),
                            int(bg_color[2] + (trail_color[2] - bg_color[2]) * fill_ratio)
                        )
                        console.draw_rect(x + i, y, 1, 1, ord(" "), bg=partial_color)
        
        elif is_increasing:
            # 증가: display_pixels ~ hp_pixels 범위에 회복 트레일 (HP 색상으로 차오름)
            for i in range(width):
                cell_start = i * divisions
                cell_end = (i + 1) * divisions
                
                # display보다 앞이면 스킵
                cell_display = max(0, min(divisions, display_pixels - cell_start))
                if cell_display >= divisions:
                    continue
                
                # 회복 트레일 영역: display ~ hp
                trail_start = max(cell_start, display_pixels)
                trail_end = min(cell_end, hp_pixels)
                cell_trail = max(0, trail_end - trail_start)
                
                if cell_trail >= divisions:
                    console.draw_rect(x + i, y, 1, 1, ord(" "), bg=trail_color)
                elif cell_trail > 0:
                    fill_ratio = cell_trail / divisions
                    if use_tiles:
                        tile_char = tile_manager.get_tile_char('hp_high', fill_ratio)
                        console.print(x + i, y, tile_char, fg=trail_color, bg=bg_color)
                    else:
                        partial_color = (
                            int(bg_color[0] + (trail_color[0] - bg_color[0]) * fill_ratio),
                            int(bg_color[1] + (trail_color[1] - bg_color[1]) * fill_ratio),
                            int(bg_color[2] + (trail_color[2] - bg_color[2]) * fill_ratio)
                        )
                        console.draw_rect(x + i, y, 1, 1, ord(" "), bg=partial_color)
        
        # 레이어 4: 현재 HP (애니메이션 중이면 display_pixels 사용)
        render_pixels = min(hp_pixels, display_pixels) if is_increasing else hp_pixels
        
        for i in range(width):
            cell_start = i * divisions
            cell_end = (i + 1) * divisions
            
            cell_hp = max(0, min(divisions, render_pixels - cell_start))
            
            if cell_hp >= divisions:
                console.draw_rect(x + i, y, 1, 1, ord(" "), bg=fg_color)
            elif cell_hp > 0:
                fill_ratio = cell_hp / divisions
                cell_unfilled = divisions - cell_hp
                
                # 트레일 블렌딩 (감소 시에만)
                if is_decreasing and cell_unfilled > 0:
                    trail_end_in_cell = min(cell_end, display_pixels)
                    trail_in_unfilled = max(0, trail_end_in_cell - (cell_start + cell_hp))
                    trail_blend = trail_in_unfilled / cell_unfilled
                    blended_bg = (
                        int(bg_color[0] + (trail_color[0] - bg_color[0]) * trail_blend),
                        int(bg_color[1] + (trail_color[1] - bg_color[1]) * trail_blend),
                        int(bg_color[2] + (trail_color[2] - bg_color[2]) * trail_blend)
                    )
                else:
                    blended_bg = bg_color
                
                if use_tiles:
                    tile_char = tile_manager.get_tile_char(color_name, fill_ratio)
                    console.print(x + i, y, tile_char, fg=fg_color, bg=blended_bg)
                else:
                    partial_color = (
                        int(blended_bg[0] + (fg_color[0] - blended_bg[0]) * fill_ratio),
                        int(blended_bg[1] + (fg_color[1] - blended_bg[1]) * fill_ratio),
                        int(blended_bg[2] + (fg_color[2] - blended_bg[2]) * fill_ratio)
                    )
                    console.draw_rect(x + i, y, 1, 1, ord(" "), bg=partial_color)
        
        # 숫자 표시 (테두리 효과로 가독성 향상)
        if show_numbers:
            current_text = f"{display_number}"
            if wound_damage > 0:
                max_text = f"{int(effective_max_hp)}"
            else:
                max_text = f"{int(max_hp)}"
            
            min_width_needed = len(current_text) + len(max_text) + 3
            
            if width >= min_width_needed:
                print_outlined_text(console, x + 1, y, current_text, fg=(255, 255, 255), outline=(0, 0, 0))
                max_text_x = x + width - len(max_text) - 1
                print_outlined_text(console, max_text_x, y, max_text, fg=(200, 200, 200), outline=(0, 0, 0))
            elif width >= len(current_text) + 2:
                print_outlined_text(console, x + 1, y, current_text, fg=(255, 255, 255), outline=(0, 0, 0))

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
        anim = anim_mgr.get_animated_value(f"{entity_id}_mp", current_mp, max_mp, duration=0.5)
        display_mp = anim.update()
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
        
        # 트레일 색상
        damage_trail_color = (100, 130, 180)  # 감소 (연한 파랑)
        heal_trail_color = (150, 200, 255)    # 증가 (밝은 하늘색)
        
        # === 픽셀 단위 렌더링 (레이어 방식) ===
        total_pixels = width * divisions
        mp_pixels = int(ratio * total_pixels)
        display_pixels = int(display_ratio * total_pixels)
        
        is_decreasing = display_pixels > mp_pixels
        is_increasing = display_pixels < mp_pixels
        trail_color = damage_trail_color if is_decreasing else heal_trail_color
        
        # 레이어 1: 배경
        console.draw_rect(x, y, width, 1, ord(" "), bg=bg_color)
        
        # 레이어 2: 트레일
        if is_decreasing:
            for i in range(width):
                cell_start = i * divisions
                cell_end = (i + 1) * divisions
                
                cell_mp = max(0, min(divisions, mp_pixels - cell_start))
                if cell_mp > 0:
                    continue
                
                trail_start = max(cell_start, mp_pixels)
                trail_end = min(cell_end, display_pixels)
                cell_trail = max(0, trail_end - trail_start)
                
                if cell_trail >= divisions:
                    console.draw_rect(x + i, y, 1, 1, ord(" "), bg=trail_color)
                elif cell_trail > 0:
                    fill_ratio = cell_trail / divisions
                    if use_tiles:
                        tile_char = tile_manager.get_tile_char('mp_fill', fill_ratio)
                        console.print(x + i, y, tile_char, fg=trail_color, bg=bg_color)
                    else:
                        partial_color = (
                            int(bg_color[0] + (trail_color[0] - bg_color[0]) * fill_ratio),
                            int(bg_color[1] + (trail_color[1] - bg_color[1]) * fill_ratio),
                            int(bg_color[2] + (trail_color[2] - bg_color[2]) * fill_ratio)
                        )
                        console.draw_rect(x + i, y, 1, 1, ord(" "), bg=partial_color)
        
        elif is_increasing:
            for i in range(width):
                cell_start = i * divisions
                cell_end = (i + 1) * divisions
                
                cell_display = max(0, min(divisions, display_pixels - cell_start))
                if cell_display >= divisions:
                    continue
                
                trail_start = max(cell_start, display_pixels)
                trail_end = min(cell_end, mp_pixels)
                cell_trail = max(0, trail_end - trail_start)
                
                if cell_trail >= divisions:
                    console.draw_rect(x + i, y, 1, 1, ord(" "), bg=trail_color)
                elif cell_trail > 0:
                    fill_ratio = cell_trail / divisions
                    if use_tiles:
                        tile_char = tile_manager.get_tile_char('mp_fill', fill_ratio)
                        console.print(x + i, y, tile_char, fg=trail_color, bg=bg_color)
                    else:
                        partial_color = (
                            int(bg_color[0] + (trail_color[0] - bg_color[0]) * fill_ratio),
                            int(bg_color[1] + (trail_color[1] - bg_color[1]) * fill_ratio),
                            int(bg_color[2] + (trail_color[2] - bg_color[2]) * fill_ratio)
                        )
                        console.draw_rect(x + i, y, 1, 1, ord(" "), bg=partial_color)
        
        # 레이어 3: 현재 MP
        render_pixels = min(mp_pixels, display_pixels) if is_increasing else mp_pixels
        
        for i in range(width):
            cell_start = i * divisions
            cell_end = (i + 1) * divisions
            
            cell_mp = max(0, min(divisions, render_pixels - cell_start))
            
            if cell_mp >= divisions:
                console.draw_rect(x + i, y, 1, 1, ord(" "), bg=fg_color)
            elif cell_mp > 0:
                fill_ratio = cell_mp / divisions
                cell_unfilled = divisions - cell_mp
                
                if is_decreasing and cell_unfilled > 0:
                    trail_end_in_cell = min(cell_end, display_pixels)
                    trail_in_unfilled = max(0, trail_end_in_cell - (cell_start + cell_mp))
                    trail_blend = trail_in_unfilled / cell_unfilled
                    blended_bg = (
                        int(bg_color[0] + (trail_color[0] - bg_color[0]) * trail_blend),
                        int(bg_color[1] + (trail_color[1] - bg_color[1]) * trail_blend),
                        int(bg_color[2] + (trail_color[2] - bg_color[2]) * trail_blend)
                    )
                else:
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
        
        # 숫자 - 테두리 효과
        if show_numbers:
            current_text = f"{display_number}"
            max_text = f"{int(max_mp)}"
            
            min_width_needed = len(current_text) + len(max_text) + 3
            
            if width >= min_width_needed:
                print_outlined_text(console, x + 1, y, current_text, fg=(255, 255, 255), outline=(0, 0, 0))
                max_text_x = x + width - len(max_text) - 1
                print_outlined_text(console, max_text_x, y, max_text, fg=(180, 200, 255), outline=(0, 0, 0))
            elif width >= len(current_text) + 2:
                print_outlined_text(console, x + 1, y, current_text, fg=(255, 255, 255), outline=(0, 0, 0))

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
        anim = anim_mgr.get_animated_value(f"{entity_id}_brv", current_brv, max_brv, duration=0.4)
        display_brv = anim.update()
        display_number = anim_mgr.get_display_number(f"{entity_id}_brv_num", current_brv, 0.016)
        
        if max_brv <= 0:
            ratio = 0.0
            display_ratio = 0.0
        else:
            ratio = min(1.0, current_brv / max_brv)
            display_ratio = min(1.0, display_brv / max_brv)
        
        # BRV 색상 (노란색 계열, BREAK 시 빨간색)
        if is_broken:
            fg_color = (150, 50, 50)
            bg_color = (60, 20, 20)
            damage_trail_color = (100, 40, 40)
            heal_trail_color = (180, 80, 80)
        elif ratio > 0.8:
            fg_color = (255, 220, 80)
            bg_color = (100, 85, 30)
            damage_trail_color = (180, 150, 60)
            heal_trail_color = (255, 240, 150)
        elif ratio > 0.5:
            fg_color = (240, 200, 60)
            bg_color = (90, 75, 25)
            damage_trail_color = (160, 130, 50)
            heal_trail_color = (255, 230, 120)
        elif ratio > 0.2:
            fg_color = (200, 160, 50)
            bg_color = (75, 60, 20)
            damage_trail_color = (140, 110, 40)
            heal_trail_color = (230, 200, 100)
        else:
            fg_color = (150, 120, 40)
            bg_color = (55, 45, 15)
            damage_trail_color = (100, 80, 30)
            heal_trail_color = (200, 170, 80)
        
        # === 픽셀 단위 렌더링 (레이어 방식) ===
        total_pixels = width * divisions
        brv_pixels = int(ratio * total_pixels)
        display_pixels = int(display_ratio * total_pixels)
        
        is_decreasing = display_pixels > brv_pixels
        is_increasing = display_pixels < brv_pixels
        trail_color = damage_trail_color if is_decreasing else heal_trail_color
        
        # 레이어 1: 배경
        console.draw_rect(x, y, width, 1, ord(" "), bg=bg_color)
        
        # 레이어 2: 트레일
        if is_decreasing:
            for i in range(width):
                cell_start = i * divisions
                cell_end = (i + 1) * divisions
                
                cell_brv = max(0, min(divisions, brv_pixels - cell_start))
                if cell_brv > 0:
                    continue
                
                trail_start = max(cell_start, brv_pixels)
                trail_end = min(cell_end, display_pixels)
                cell_trail = max(0, trail_end - trail_start)
                
                if cell_trail >= divisions:
                    console.draw_rect(x + i, y, 1, 1, ord(" "), bg=trail_color)
                elif cell_trail > 0:
                    fill_ratio = cell_trail / divisions
                    if use_tiles:
                        tile_char = tile_manager.get_tile_char('brv_fill', fill_ratio)
                        console.print(x + i, y, tile_char, fg=trail_color, bg=bg_color)
                    else:
                        partial_color = (
                            int(bg_color[0] + (trail_color[0] - bg_color[0]) * fill_ratio),
                            int(bg_color[1] + (trail_color[1] - bg_color[1]) * fill_ratio),
                            int(bg_color[2] + (trail_color[2] - bg_color[2]) * fill_ratio)
                        )
                        console.draw_rect(x + i, y, 1, 1, ord(" "), bg=partial_color)
        
        elif is_increasing:
            for i in range(width):
                cell_start = i * divisions
                cell_end = (i + 1) * divisions
                
                cell_display = max(0, min(divisions, display_pixels - cell_start))
                if cell_display >= divisions:
                    continue
                
                trail_start = max(cell_start, display_pixels)
                trail_end = min(cell_end, brv_pixels)
                cell_trail = max(0, trail_end - trail_start)
                
                if cell_trail >= divisions:
                    console.draw_rect(x + i, y, 1, 1, ord(" "), bg=trail_color)
                elif cell_trail > 0:
                    fill_ratio = cell_trail / divisions
                    if use_tiles:
                        tile_char = tile_manager.get_tile_char('brv_fill', fill_ratio)
                        console.print(x + i, y, tile_char, fg=trail_color, bg=bg_color)
                    else:
                        partial_color = (
                            int(bg_color[0] + (trail_color[0] - bg_color[0]) * fill_ratio),
                            int(bg_color[1] + (trail_color[1] - bg_color[1]) * fill_ratio),
                            int(bg_color[2] + (trail_color[2] - bg_color[2]) * fill_ratio)
                        )
                        console.draw_rect(x + i, y, 1, 1, ord(" "), bg=partial_color)
        
        # 레이어 3: 현재 BRV
        render_pixels = min(brv_pixels, display_pixels) if is_increasing else brv_pixels
        
        for i in range(width):
            cell_start = i * divisions
            cell_end = (i + 1) * divisions
            
            cell_brv = max(0, min(divisions, render_pixels - cell_start))
            
            if cell_brv >= divisions:
                console.draw_rect(x + i, y, 1, 1, ord(" "), bg=fg_color)
            elif cell_brv > 0:
                fill_ratio = cell_brv / divisions
                cell_unfilled = divisions - cell_brv
                
                if is_decreasing and cell_unfilled > 0:
                    trail_end_in_cell = min(cell_end, display_pixels)
                    trail_in_unfilled = max(0, trail_end_in_cell - (cell_start + cell_brv))
                    trail_blend = trail_in_unfilled / cell_unfilled
                    blended_bg = (
                        int(bg_color[0] + (trail_color[0] - bg_color[0]) * trail_blend),
                        int(bg_color[1] + (trail_color[1] - bg_color[1]) * trail_blend),
                        int(bg_color[2] + (trail_color[2] - bg_color[2]) * trail_blend)
                    )
                else:
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
        
        # 숫자 - 테두리 효과로 가독성 향상
        if show_numbers:
            if is_broken:
                text = "BREAK!"
                text_x = x + (width - len(text)) // 2
                if text_x >= x:
                    print_outlined_text(console, text_x, y, text, fg=(255, 100, 100), outline=(40, 0, 0))
            else:
                current_text = f"{display_number}"
                max_text = f"{int(max_brv)}"
                
                min_width_needed = len(current_text) + len(max_text) + 3
                
                if width >= min_width_needed:
                    print_outlined_text(console, x + 1, y, current_text, fg=(255, 255, 255), outline=(0, 0, 0))
                    max_text_x = x + width - len(max_text) - 1
                    print_outlined_text(console, max_text_x, y, max_text, fg=(255, 230, 150), outline=(0, 0, 0))
                elif width >= len(current_text) + 2:
                    print_outlined_text(console, x + 1, y, current_text, fg=(255, 255, 255), outline=(0, 0, 0))

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
        ATB 게이지 렌더링 (픽셀 단위, 애니메이션 지원)

        Args:
            console: TCOD 콘솔
            x, y: 게이지 위치
            width: 게이지 너비
            current: 현재 ATB 값
            threshold: 행동 가능 임계값
            maximum: 최대 ATB 값
            entity_id: 엔티티 ID (애니메이션 추적용)
        """
        anim_mgr = get_animation_manager()
        tile_manager = _get_tile_manager()
        use_tiles = tile_manager is not None and tile_manager.is_initialized()
        divisions = GaugeRenderer.DIVISIONS
        
        # 애니메이션 (entity_id가 있으면 사용)
        if entity_id:
            anim = anim_mgr.get_animated_value(f"{entity_id}_atb", current, maximum, duration=0.15)
            display_atb = anim.update()
        else:
            display_atb = current
        
        if maximum <= 0:
            ratio = 0.0
            display_ratio = 0.0
        else:
            ratio = min(1.0, current / maximum)
            display_ratio = min(1.0, display_atb / maximum)

        # 행동 가능 여부에 따른 색상 변경
        is_ready = current >= threshold
        if is_ready:
            fg_color = (150, 220, 255)  # 밝은 하늘색 (행동 가능)
            bg_color = (60, 90, 140)
        else:
            fg_color = (100, 150, 255)  # 기본 파란색
            bg_color = (50, 75, 125)
        
        trail_color = (80, 180, 255)  # 증가 트레일 색상

        # === 픽셀 단위 렌더링 (애니메이션 지원) ===
        total_pixels = width * divisions
        atb_pixels = int(display_ratio * total_pixels)
        target_pixels = int(ratio * total_pixels)
        
        is_increasing = target_pixels > atb_pixels
        
        # 레이어 1: 배경
        console.draw_rect(x, y, width, 1, ord(" "), bg=bg_color)
        
        # 레이어 2: 증가 트레일 (ATB가 차오르는 효과)
        if is_increasing:
            for i in range(width):
                cell_start = i * divisions
                cell_end = (i + 1) * divisions
                
                cell_atb = max(0, min(divisions, atb_pixels - cell_start))
                if cell_atb >= divisions:
                    continue
                
                trail_start = max(cell_start, atb_pixels)
                trail_end = min(cell_end, target_pixels)
                cell_trail = max(0, trail_end - trail_start)
                
                if cell_trail >= divisions:
                    console.draw_rect(x + i, y, 1, 1, ord(" "), bg=trail_color)
                elif cell_trail > 0:
                    fill_ratio = cell_trail / divisions
                    if use_tiles:
                        tile_char = tile_manager.get_tile_char('atb_fill', fill_ratio)
                        console.print(x + i, y, tile_char, fg=trail_color, bg=bg_color)
                    else:
                        partial_color = (
                            int(bg_color[0] + (trail_color[0] - bg_color[0]) * fill_ratio),
                            int(bg_color[1] + (trail_color[1] - bg_color[1]) * fill_ratio),
                            int(bg_color[2] + (trail_color[2] - bg_color[2]) * fill_ratio)
                        )
                        console.draw_rect(x + i, y, 1, 1, ord(" "), bg=partial_color)
        
        # 레이어 3: 현재 ATB
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
            print_outlined_text(console, threshold_x, y, "|", fg=(255, 255, 100), outline=(0, 0, 0))

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
        entity_id: str = None
    ) -> None:
        """
        ATB 게이지와 캐스팅 진행도를 함께 렌더링 (애니메이션 지원)

        Args:
            console: TCOD 콘솔
            x, y: 게이지 위치
            width: 게이지 너비
            atb_current: 현재 ATB 값
            atb_threshold: 행동 가능 임계값
            atb_maximum: 최대 ATB 값
            cast_progress: 캐스팅 진행도 (0.0 ~ 1.0)
            is_casting: 캐스팅 중 여부
            entity_id: 엔티티 ID (애니메이션 추적용)
        """
        anim_mgr = get_animation_manager()
        
        # ATB 애니메이션
        if entity_id:
            anim = anim_mgr.get_animated_value(f"{entity_id}_atb2", atb_current, atb_threshold * 2, duration=0.15)
            display_atb = anim.update()
        else:
            display_atb = atb_current
        
        # ATB를 임계값(threshold) 기준으로 표시 (0~threshold = 0~100%)
        # threshold 이상은 오버플로우로 최대 2배까지 표시
        if atb_threshold <= 0:
            atb_ratio = 0.0
            display_ratio = 0.0
        else:
            atb_ratio = min(2.0, atb_current / atb_threshold)
            display_ratio = min(2.0, display_atb / atb_threshold)

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

        # 애니메이션에 display_ratio 사용
        # ATB 게이지 그리기 (100%까지)
        normal_ratio = min(1.0, display_ratio)
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
        if display_ratio > 1.0:
            overflow_ratio = min(1.0, display_ratio - 1.0)
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
