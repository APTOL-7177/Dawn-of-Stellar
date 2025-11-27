"""
게이지 커스텀 타일셋 시스템

픽셀 단위 정밀 게이지 렌더링을 위한 커스텀 타일 생성 및 등록
- 16분할 또는 32분할 부분 채움 타일
- 다양한 색상 지원 (HP, MP, BRV, 데미지 트레일 등)
"""

import numpy as np
import tcod
import tcod.tileset
from typing import Dict, Tuple, Optional, List
from src.core.logger import get_logger

logger = get_logger("gauge_tileset")

# 유니코드 Private Use Area (PUA) 시작점
# E000-E0FF: 게이지 타일용 예약
GAUGE_TILE_BASE = 0xE000

# 분할 수 (16 = 1/16 단위, 32 = 1/32 단위)
GAUGE_DIVISIONS = 32

# 색상 정의 (게이지 타입별)
class GaugeColors:
    """게이지 색상 정의"""
    # HP 게이지
    HP_HIGH = (0, 220, 80)      # 초록 (HP > 50%)
    HP_MID = (220, 200, 0)      # 노랑 (HP 25-50%)
    HP_LOW = (220, 50, 50)      # 빨강 (HP < 25%)
    HP_BG = (40, 20, 20)        # 배경 (어두운 빨강)
    
    # MP 게이지
    MP_FILL = (60, 120, 220)    # 파랑
    MP_BG = (20, 30, 60)        # 배경 (어두운 파랑)
    
    # BRV 게이지
    BRV_FILL = (220, 180, 60)   # 금색
    BRV_BG = (50, 40, 20)       # 배경 (어두운 금색)
    
    # 데미지 트레일
    DAMAGE_TRAIL = (255, 140, 50)  # 주황
    
    # 상처 (wound)
    WOUND = (80, 30, 50)        # 어두운 보라빨강
    WOUND_STRIPE = (0, 0, 0)    # 상처 빗금 (검은색) - 픽셀 단위로 표시
    
    # ATB 게이지
    ATB_FILL = (100, 200, 255)  # 하늘색
    ATB_BG = (30, 50, 70)       # 배경
    
    # 캐스팅 게이지
    CAST_FILL = (200, 150, 255) # 연보라
    CAST_BG = (50, 40, 70)      # 배경


class GaugeTileManager:
    """게이지 타일 관리자"""
    
    _instance: Optional['GaugeTileManager'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if GaugeTileManager._initialized:
            return
        
        self.tileset: Optional[tcod.tileset.Tileset] = None
        self.tile_width: int = 0
        self.tile_height: int = 0
        self.divisions: int = GAUGE_DIVISIONS
        
        # 생성된 타일 캐시 (codepoint -> True)
        self._created_tiles: Dict[int, bool] = {}
        
        # 타일 코드포인트 매핑
        # 구조: base + (color_index * (divisions + 1)) + fill_level
        # color_index: 0=HP_HIGH, 1=HP_MID, 2=HP_LOW, 3=HP_BG, 4=MP_FILL, 5=MP_BG, 
        #              6=BRV_FILL, 7=BRV_BG, 8=DAMAGE_TRAIL, 9=WOUND, 10=ATB_FILL, 11=CAST_FILL
        self.color_map = {
            'hp_high': 0,
            'hp_mid': 1,
            'hp_low': 2,
            'hp_bg': 3,
            'mp_fill': 4,
            'mp_bg': 5,
            'brv_fill': 6,
            'brv_bg': 7,
            'damage_trail': 8,
            'wound': 9,
            'atb_fill': 10,
            'cast_fill': 11,
            'wound_stripe': 12,  # 상처 빗금 패턴 (오른쪽에서 채움)
            'wound_fill_right': 13,  # 상처 영역 (오른쪽에서 채움, 빗금 없음)
        }
        
        self.color_values = {
            'hp_high': GaugeColors.HP_HIGH,
            'hp_mid': GaugeColors.HP_MID,
            'hp_low': GaugeColors.HP_LOW,
            'hp_bg': GaugeColors.HP_BG,
            'mp_fill': GaugeColors.MP_FILL,
            'mp_bg': GaugeColors.MP_BG,
            'brv_fill': GaugeColors.BRV_FILL,
            'brv_bg': GaugeColors.BRV_BG,
            'damage_trail': GaugeColors.DAMAGE_TRAIL,
            'wound': GaugeColors.WOUND,
            'atb_fill': GaugeColors.ATB_FILL,
            'cast_fill': GaugeColors.CAST_FILL,
            'wound_stripe': GaugeColors.WOUND_STRIPE,
            'wound_fill_right': GaugeColors.WOUND,
        }
        
        # 특수 타일 유형 (오른쪽에서 채움, 빗금 등)
        self.special_tile_types = {'wound_stripe', 'wound_fill_right'}
        
        GaugeTileManager._initialized = True
        logger.info(f"GaugeTileManager 초기화 ({self.divisions}분할)")
    
    def initialize(self, tileset: tcod.tileset.Tileset) -> None:
        """타일셋 초기화 및 게이지 타일 생성"""
        self.tileset = tileset
        self.tile_width = tileset.tile_width
        self.tile_height = tileset.tile_height
        
        logger.info(f"게이지 타일 생성 시작 (타일 크기: {self.tile_width}x{self.tile_height})")
        
        # 모든 게이지 타일 미리 생성
        self._create_all_tiles()
        
        logger.info(f"게이지 타일 생성 완료 ({len(self._created_tiles)}개)")
    
    def _create_all_tiles(self) -> None:
        """모든 게이지 타일 생성"""
        for color_name, color_index in self.color_map.items():
            color = self.color_values[color_name]
            for fill_level in range(self.divisions + 1):
                if color_name == 'wound_stripe':
                    self._create_stripe_tile(color_index, fill_level, color)
                elif color_name == 'wound_fill_right':
                    self._create_right_fill_tile(color_index, fill_level, color)
                else:
                    self._create_tile(color_index, fill_level, color)
    
    def _create_tile(self, color_index: int, fill_level: int, color: Tuple[int, int, int]) -> None:
        """단일 타일 생성
        
        타일은 흰색(255,255,255)으로 생성하여 fg 파라미터로 색상 적용 가능하게 함
        """
        if self.tileset is None:
            return
        
        codepoint = self._get_codepoint(color_index, fill_level)
        
        if codepoint in self._created_tiles:
            return
        
        # RGBA 타일 이미지 생성
        tile = np.zeros((self.tile_height, self.tile_width, 4), dtype=np.uint8)
        
        # 채움 픽셀 수 계산
        fill_pixels = int((fill_level / self.divisions) * self.tile_width)
        
        # 채움 영역 - 흰색으로 생성 (fg 파라미터가 색상을 결정)
        if fill_pixels > 0:
            tile[:, :fill_pixels, 0] = 255  # R = 흰색
            tile[:, :fill_pixels, 1] = 255  # G = 흰색
            tile[:, :fill_pixels, 2] = 255  # B = 흰색
            tile[:, :fill_pixels, 3] = 255  # A (불투명)
        
        # 빈 영역 (투명 - bg 파라미터가 색상을 결정)
        # alpha = 0 이므로 console.print()의 bg 색상이 표시됨
        
        # 타일 등록
        try:
            self.tileset.set_tile(codepoint, tile)
            self._created_tiles[codepoint] = True
        except Exception as e:
            logger.warning(f"타일 생성 실패 (codepoint={codepoint}): {e}")
    
    def _create_stripe_tile(self, color_index: int, fill_level: int, color: Tuple[int, int, int]) -> None:
        """빗금 패턴 타일 생성 (상처 영역용)

        fill_level을 오프셋으로 사용하여 인접 셀과 빗금 패턴이 연속되도록 함
        fg = 빗금 색상, bg = 투명 (이전 배경이 보임)
        """
        if self.tileset is None:
            return

        codepoint = self._get_codepoint(color_index, fill_level)

        if codepoint in self._created_tiles:
            return

        # RGBA 타일 이미지 생성
        tile = np.zeros((self.tile_height, self.tile_width, 4), dtype=np.uint8)
        # 투명으로 초기화 (배경색은 console.print의 bg 파라미터로 지정됨)
        # 빗금 타일은 투명 배경을 사용하되, 빗금만 그리기

        # 빗금 패턴 생성 (대각선)
        stripe_width = 2  # 빗금 두께
        stripe_gap = 3    # 빗금 간격
        stripe_period = stripe_width + stripe_gap

        # fill_level을 셀 인덱스로 사용하여 x 오프셋 계산 (연속성 보장)
        # 각 셀은 tile_width 픽셀이므로, 셀 인덱스 * tile_width가 실제 x 위치
        x_offset = (fill_level * self.tile_width) % stripe_period

        for py in range(self.tile_height):
            for px in range(self.tile_width):
                # 대각선 빗금 패턴 (오프셋 적용으로 인접 셀과 연속)
                if ((x_offset + px) + py) % stripe_period < stripe_width:
                    tile[py, px, 0] = 255  # R = 흰색 (fg 색상으로 대체됨)
                    tile[py, px, 1] = 255  # G
                    tile[py, px, 2] = 255  # B
                    tile[py, px, 3] = 255  # A (불투명)
                # else: 빗금 사이는 투명 (alpha=0) -> console.print의 bg 색상이 보임

        # 타일 등록
        try:
            self.tileset.set_tile(codepoint, tile)
            self._created_tiles[codepoint] = True
        except Exception as e:
            logger.warning(f"빗금 타일 생성 실패 (codepoint={codepoint}): {e}")
    
    def _create_right_fill_tile(self, color_index: int, fill_level: int, color: Tuple[int, int, int]) -> None:
        """오른쪽에서 왼쪽으로 채워지는 타일 생성 (상처 영역용)
        
        fill_level에 따라 오른쪽에서 왼쪽으로 채워짐
        일반 타일과 반대 방향
        """
        if self.tileset is None:
            return
        
        codepoint = self._get_codepoint(color_index, fill_level)
        
        if codepoint in self._created_tiles:
            return
        
        # RGBA 타일 이미지 생성
        tile = np.zeros((self.tile_height, self.tile_width, 4), dtype=np.uint8)
        
        # 채움 픽셀 수 계산 (오른쪽에서 시작)
        fill_pixels = int((fill_level / self.divisions) * self.tile_width)
        start_x = self.tile_width - fill_pixels
        
        # 오른쪽 영역 채우기
        if fill_pixels > 0:
            tile[:, start_x:, 0] = 255  # R = 흰색
            tile[:, start_x:, 1] = 255  # G = 흰색
            tile[:, start_x:, 2] = 255  # B = 흰색
            tile[:, start_x:, 3] = 255  # A (불투명)
        
        # 타일 등록
        try:
            self.tileset.set_tile(codepoint, tile)
            self._created_tiles[codepoint] = True
        except Exception as e:
            logger.warning(f"오른쪽 채움 타일 생성 실패 (codepoint={codepoint}): {e}")
    
    def _get_codepoint(self, color_index: int, fill_level: int) -> int:
        """색상과 채움 레벨에 해당하는 유니코드 코드포인트 반환"""
        return GAUGE_TILE_BASE + (color_index * (self.divisions + 1)) + fill_level
    
    def get_tile_char(self, color_name: str, fill_ratio: float) -> str:
        """채움 비율에 해당하는 타일 문자 반환

        Args:
            color_name: 색상 이름 ('hp_high', 'mp_fill', 등)
            fill_ratio: 채움 비율 (0.0 ~ 1.0)

        Returns:
            해당 타일의 유니코드 문자
        """
        if color_name not in self.color_map:
            return ' '

        color_index = self.color_map[color_name]
        fill_level = int(fill_ratio * self.divisions)
        fill_level = max(0, min(self.divisions, fill_level))

        codepoint = self._get_codepoint(color_index, fill_level)
        return chr(codepoint)

    def get_tile_char_by_index(self, color_name: str, cell_index: int) -> str:
        """셀 인덱스로 타일 문자 반환 (빗금 패턴용)

        Args:
            color_name: 색상 이름 ('wound_stripe' 등)
            cell_index: 셀 인덱스 (연속성을 위한 오프셋)

        Returns:
            해당 타일의 유니코드 문자
        """
        if color_name not in self.color_map:
            return ' '

        color_index = self.color_map[color_name]
        # 빗금 패턴은 5개 주기로 반복 (stripe_period = 5)
        fill_level = cell_index % (self.divisions + 1)

        codepoint = self._get_codepoint(color_index, fill_level)
        return chr(codepoint)
    
    def get_fill_level(self, fill_ratio: float) -> int:
        """채움 비율을 분할 레벨로 변환"""
        level = int(fill_ratio * self.divisions)
        return max(0, min(self.divisions, level))
    
    def is_initialized(self) -> bool:
        """초기화 여부 확인"""
        return self.tileset is not None and len(self._created_tiles) > 0
    
    def create_boundary_tile(
        self,
        hp_pixels: int,
        wound_pixels: int,
        hp_color: Tuple[int, int, int],
        bg_color: Tuple[int, int, int],
        wound_stripe_color: Tuple[int, int, int],
        cell_index: int = 0,
        cell_start: int = 0,
        wound_start_pixel: int = 0,
        hp_end_pixel: int = 0
    ) -> str:
        """
        경계 셀용 동적 타일 생성 (HP, 빈 공간, 상처가 한 셀에 있는 경우)

        Args:
            hp_pixels: HP가 차지하는 픽셀 수 (왼쪽에서)
            wound_pixels: 상처가 차지하는 픽셀 수 (오른쪽에서)
            hp_color: HP 색상
            bg_color: 빈 공간 (배경) 색상
            wound_stripe_color: 상처 빗금 색상
            cell_index: 셀 인덱스 (빗금 연속성을 위한 오프셋)

        Returns:
            동적 생성된 타일의 유니코드 문자
        """
        # 상처가 없으면 오류 (이 함수는 상처가 있을 때만 호출되어야 함)
        if wound_pixels == 0:
            logger.error(f"[경계 타일] wound_pixels=0인데 호출됨! hp_pixels={hp_pixels}, hp_color={hp_color}")
            logger.error(f"[경계 타일] 호출 스택을 확인하세요 - 이 함수는 wound_pixels > 0일 때만 호출되어야 합니다")
            # 빈 문자 반환 (폴백)
            return ' '

        if self.tileset is None:
            logger.warning("경계 타일 생성 실패: tileset이 초기화되지 않음")
            return ' '

        # 입력된 hp_pixels와 wound_pixels는 이미 양자화된 divisions 값
        # divisions(32) 기준 픽셀을 실제 tile_width 기준으로 스케일링
        scale = self.tile_width / self.divisions
        actual_hp_pixels = max(0, min(self.tile_width, int(hp_pixels * scale + 0.5)))
        actual_wound_pixels = max(0, min(self.tile_width, int(wound_pixels * scale + 0.5)))
        
        # 빈 HP 영역 계산
        empty_hp_pixels = self.tile_width - actual_hp_pixels - actual_wound_pixels
        
        # HP와 상처가 맞닿아 있을 때 빈 간격 방지
        # 원본 HP + 상처 합이 divisions와 같거나 거의 같으면, 스케일링 후에도 연속되도록 조정
        total_original = hp_pixels + wound_pixels
        if total_original >= self.divisions - 1:
            # 원본이 셀 전체를 거의 채우고 있으면, 정확히 타일 너비를 채우도록 조정
            # 스케일링 반올림 오차로 인한 간격 제거
            actual_wound_pixels = self.tile_width - actual_hp_pixels
            actual_wound_pixels = max(0, min(self.tile_width, actual_wound_pixels))
        
        # HP + 상처가 타일 너비를 초과하는 경우 조정
        if actual_hp_pixels + actual_wound_pixels > self.tile_width:
            # 빈 HP 영역을 최소화하면서 조정
            # 우선순위: HP > 상처 > 빈 HP 영역
            if actual_hp_pixels > self.tile_width:
                actual_hp_pixels = self.tile_width
                actual_wound_pixels = 0
            elif actual_wound_pixels > self.tile_width - actual_hp_pixels:
                actual_wound_pixels = self.tile_width - actual_hp_pixels
        
        # 최종 빈 HP 영역 재계산
        empty_hp_pixels = max(0, self.tile_width - actual_hp_pixels - actual_wound_pixels)
        
        # 경계 타일용 고유 코드포인트 생성 (캐시 키로 사용)
        # E800 ~ EFFF 범위 사용 (기존 E000~E7FF 외)
        # 캐시 키는 양자화된 divisions 값 사용 (더 안정적, 애니메이션 중 변화 없음)
        # 색상 해시 충돌 방지: 실제 색상값 포함
        # 실제 stripe offset 계산과 동일하게 캐싱하여 시각적 연속성 보장
        # 빗금 색상은 애니메이션하므로 캐시 키에 포함하여 매 프레임마다 재생성
        stripe_offset_for_cache = (cell_index * self.tile_width) % 5  # stripe_period = 5
        # wound_stripe_color를 캐시 키에 포함하여 애니메이션 색상 반영
        cache_key = (hp_pixels, wound_pixels, hp_color, bg_color, stripe_offset_for_cache, wound_stripe_color)
        
        # 캐시된 코드포인트가 있으면 재용
        if not hasattr(self, '_boundary_tile_cache'):
            self._boundary_tile_cache: Dict[tuple, int] = {}
            # Supplementary Private Use Area-A (U+F0000 ~ U+FFFFD) 사용: 65534개 범위
            # 기존 Private Use Area (U+E000 ~ U+F8FF)가 부족할 경우 확장
            self._next_boundary_codepoint = 0xF0000
            self._boundary_tile_access_order: List[tuple] = []  # LRU를 위한 접근 순서

        if cache_key in self._boundary_tile_cache:
            cached_codepoint = self._boundary_tile_cache[cache_key]
            # LRU: 접근한 항목을 맨 뒤로 이동
            if cache_key in self._boundary_tile_access_order:
                self._boundary_tile_access_order.remove(cache_key)
            self._boundary_tile_access_order.append(cache_key)
            logger.debug(f"[경계 타일 캐시 히트] codepoint=0x{cached_codepoint:04X}, hp={hp_pixels}, wound={wound_pixels}")
            return chr(cached_codepoint)

        # 새 코드포인트 할당 (범위 체크 및 LRU 캐시 정리)
        # Supplementary Private Use Area-A (U+F0000 ~ U+FFFFD): 65534개
        # 범위가 거의 찰 때 미리 정리 (90% 이상 사용 시)
        max_codepoints = 0xFFFFD - 0xF0000 + 1  # 65534개
        if self._next_boundary_codepoint >= 0xF0000 + int(max_codepoints * 0.9):
            # 캐시 크기가 90% 이상이면 가장 오래된 항목 10% 제거
            items_to_remove = max(1, len(self._boundary_tile_cache) // 10)
            for _ in range(items_to_remove):
                if len(self._boundary_tile_access_order) > 0:
                    oldest_key = self._boundary_tile_access_order.pop(0)
                    if oldest_key in self._boundary_tile_cache:
                        old_codepoint = self._boundary_tile_cache.pop(oldest_key)
                        logger.debug(
                            f"LRU 캐시 사전 정리: 오래된 타일 제거 (key={oldest_key}, codepoint=0x{old_codepoint:04X})"
                        )
        
        if self._next_boundary_codepoint > 0xFFFFD:
            # 범위 초과시 LRU 캐시에서 가장 오래된 항목 제거
            if len(self._boundary_tile_access_order) > 0:
                oldest_key = self._boundary_tile_access_order.pop(0)
                if oldest_key in self._boundary_tile_cache:
                    # 오래된 타일의 코드포인트 재사용
                    codepoint = self._boundary_tile_cache.pop(oldest_key)
                    logger.debug(
                        f"LRU 캐시 정리: 오래된 타일 제거 (key={oldest_key}, codepoint=0x{codepoint:05X}). "
                        f"캐시 크기: {len(self._boundary_tile_cache)}"
                    )
                else:
                    # 캐시가 비어있으면 재사용 불가
                    logger.error(
                        f"경계 타일 코드포인트 범위 초과 및 캐시 정리 불가 (0xF0000~0xFFFFD). "
                        f"캐시 크기: {len(self._boundary_tile_cache)}. "
                        f"폴백 블렌딩을 사용합니다."
                    )
                    return ' '
            else:
                # 접근 순서가 없으면 재사용 불가
                logger.error(
                    f"경계 타일 코드포인트 범위 초과 (0xF0000~0xFFFFD). "
                    f"캐시 크기: {len(self._boundary_tile_cache)}. "
                    f"폴백 블렌딩을 사용합니다."
                )
                return ' '
        else:
            # 새 코드포인트 할당
            codepoint = self._next_boundary_codepoint
            self._next_boundary_codepoint += 1
        
        # RGBA 타일 이미지 생성 (초기화는 bg_color로 설정하여 검은색 방지)
        tile = np.zeros((self.tile_height, self.tile_width, 4), dtype=np.uint8)
        # 타일 전체를 bg_color로 초기화 (모든 픽셀이 명시적으로 설정되도록)
        tile[:, :, 0] = bg_color[0]
        tile[:, :, 1] = bg_color[1]
        tile[:, :, 2] = bg_color[2]
        tile[:, :, 3] = 255  # 불투명

        # 빗금 패턴 파라미터
        stripe_width = 2
        stripe_gap = 3
        stripe_period = stripe_width + stripe_gap

        # 빗금 오프셋: 셀 인덱스를 픽셀 위치로 변환하여 패턴 연속성 보장
        # 각 셀은 tile_width 픽셀을 가지므로, 셀 인덱스 * tile_width가 실제 픽셀 위치
        x_offset = (cell_index * self.tile_width) % stripe_period

        # 캐시 키 계산: 실제 stripe offset과 동일한 계산 사용
        stripe_offset_for_cache = x_offset

        # 상처 시작점: 게이지 전체에서의 상처 시작점을 셀 내 상대 위치로 변환 (tile_width 단위)
        # wound_start_pixel이 셀 내에 있으면 그 위치부터, 셀보다 왼쪽에 있으면 0부터
        if wound_start_pixel > 0:
            if wound_start_pixel < cell_start:
                # 상처 시작점이 셀보다 왼쪽에 있으면 상처는 셀 전체에 걸쳐 있음
                wound_start_in_cell = 0
            else:
                # 상처 시작점이 셀 내에 있으면 셀 내 상대 위치로 변환 (divisions 단위)
                wound_start_in_cell_divisions = wound_start_pixel - cell_start
                # 스케일링 적용 (divisions -> tile_width)
                scale = self.tile_width / self.divisions
                wound_start_in_cell = max(0, min(self.tile_width, int(wound_start_in_cell_divisions * scale + 0.5)))
        else:
            # wound_start_pixel이 0이면 상처가 없음 (이 경우는 호출되지 않아야 함)
            wound_start_in_cell = self.tile_width - actual_wound_pixels if actual_wound_pixels > 0 else self.tile_width
        
        # 상처는 wound_start_in_cell부터 셀 오른쪽 끝까지
        # HP 끝 지점: 게이지 전체에서의 HP 끝점을 셀 내 상대 위치로 변환
        # hp_end_pixel이 제공되면 그것을 사용, 아니면 actual_hp_pixels 사용
        if hp_end_pixel > 0:
            # 게이지 전체에서의 HP 끝점을 셀 내 상대 위치로 변환
            if hp_end_pixel <= cell_start:
                # HP 끝점이 셀 시작점 이하이면 HP는 셀에 없음
                hp_end_in_cell = 0
            elif hp_end_pixel >= cell_start + self.divisions:
                # HP 끝점이 셀 끝점 이상이면 HP는 셀 전체를 채움
                hp_end_in_cell = self.tile_width
            else:
                # HP 끝점이 셀 내에 있으면 셀 내 상대 위치로 변환 (divisions 단위)
                hp_end_in_cell_divisions = hp_end_pixel - cell_start
                # 스케일링 적용 (divisions -> tile_width)
                scale = self.tile_width / self.divisions
                hp_end_in_cell = max(0, min(self.tile_width, int(hp_end_in_cell_divisions * scale + 0.5)))
        else:
            # hp_end_pixel이 제공되지 않으면 actual_hp_pixels 사용
            hp_end_in_cell = actual_hp_pixels
        
        # HP 끝 지점: hp_end_in_cell 사용 (이미 hp_end_pixel에서 wound_start_pixel을 넘지 않도록 제한됨)
        hp_end = hp_end_in_cell

        # 각 영역을 명시적으로 설정
        for py in range(self.tile_height):
            for px in range(self.tile_width):
                if px < hp_end:
                    # HP 영역 (왼쪽) - hp_color로 불투명하게 설정
                    tile[py, px, 0] = hp_color[0]
                    tile[py, px, 1] = hp_color[1]
                    tile[py, px, 2] = hp_color[2]
                    tile[py, px, 3] = 255  # 불투명
                elif actual_wound_pixels > 0 and px >= wound_start_in_cell:
                    # 상처 영역 (오른쪽) - 빗금 패턴 (상처가 있을 때만)
                    # 빗금 부분은 wound_stripe_color로 직접 설정 (애니메이션 색상)
                    if ((x_offset + px) + py) % stripe_period < stripe_width:
                        # 빗금: wound_stripe_color로 생성 (애니메이션 색상 직접 적용)
                        tile[py, px, 0] = wound_stripe_color[0]
                        tile[py, px, 1] = wound_stripe_color[1]
                        tile[py, px, 2] = wound_stripe_color[2]
                        tile[py, px, 3] = 255  # 불투명
                    else:
                        # 빗금 사이: bg_color (게이지 배경색)
                        tile[py, px, 0] = bg_color[0]
                        tile[py, px, 1] = bg_color[1]
                        tile[py, px, 2] = bg_color[2]
                        tile[py, px, 3] = 255  # 불투명
                else:
                    # 빈 HP 영역 (중간, hp_end <= px < wound_start_in_cell)
                    # bg_color로 불투명하게 설정 (투명하면 배경색이 보여서 초록 검정 패턴이 나타남)
                    tile[py, px, 0] = bg_color[0]
                    tile[py, px, 1] = bg_color[1]
                    tile[py, px, 2] = bg_color[2]
                    tile[py, px, 3] = 255  # 불투명
        
        # 타일 등록
        try:
            # 디버그: 타일 내부 픽셀 샘플 확인 및 색상 검증
            center_y = self.tile_height // 2
            center_x = self.tile_width // 2
            sample_pixel = tile[center_y, center_x]
            right_x = self.tile_width - 1
            right_pixel = tile[center_y, right_x]

            # 빗금 영역 샘플 확인 (wound_start_in_cell 지점)
            if wound_start_in_cell < self.tile_width:
                wound_sample = tile[center_y, wound_start_in_cell]
                # 빗금 사이 영역 샘플 (wound_start_in_cell + 1, 빗금이 아닌 부분)
                if wound_start_in_cell + 1 < self.tile_width:
                    wound_bg_sample = tile[center_y, wound_start_in_cell + 1]
                else:
                    wound_bg_sample = None
            else:
                wound_sample = None
                wound_bg_sample = None

            logger.debug(
                f"[경계 타일 디버그] 타일 생성: hp_pixels={actual_hp_pixels}, wound_pixels={actual_wound_pixels}, "
                f"bg_color={bg_color}, hp_color={hp_color}, "
                f"wound_start_in_cell={wound_start_in_cell}, hp_end={hp_end}, tile_width={self.tile_width}, "
                f"중앙픽셀=RGBA({sample_pixel[0]},{sample_pixel[1]},{sample_pixel[2]},{sample_pixel[3]}), "
                f"HP시작픽셀=RGBA({tile[center_y, 0, 0]},{tile[center_y, 0, 1]},{tile[center_y, 0, 2]},{tile[center_y, 0, 3]})"
            )

            # 타일 복사본 생성 (참조 문제 방지 - numpy 배열이 재사용될 수 있음)
            tile_copy = tile.copy()
            logger.debug(f"[경계 타일] set_tile() 호출 직전: codepoint=0x{codepoint:04X}, tileset={self.tileset is not None}")
            self.tileset.set_tile(codepoint, tile_copy)
            logger.debug(f"[경계 타일] set_tile() 호출 성공: codepoint=0x{codepoint:04X}")
            self._boundary_tile_cache[cache_key] = codepoint
            # LRU: 새 항목을 접근 순서에 추가
            self._boundary_tile_access_order.append(cache_key)
            logger.debug(
                f"경계 타일 생성 성공: codepoint=0x{codepoint:04X}, "
                f"hp_pixels={actual_hp_pixels}/{self.tile_width}, "
                f"wound_pixels={actual_wound_pixels}/{self.tile_width}, "
                f"cell_index={cell_index}, "
                f"wound_start_in_cell={wound_start_in_cell}, hp_end={hp_end}, "
                f"bg_color={bg_color}, wound_stripe_color={wound_stripe_color}"
            )
        except Exception as e:
            import traceback
            logger.error(
                f"경계 타일 생성 실패: codepoint=0x{codepoint:04X}, "
                f"hp_pixels={actual_hp_pixels}/{self.tile_width}, "
                f"wound_pixels={actual_wound_pixels}/{self.tile_width}, "
                f"cell_index={cell_index}, "
                f"error={e}"
            )
            logger.debug(f"경계 타일 생성 실패 스택 트레이스:\n{traceback.format_exc()}")
            return ' '
        
        return chr(codepoint)


def get_gauge_tile_manager() -> GaugeTileManager:
    """싱글톤 게이지 타일 관리자 반환"""
    return GaugeTileManager()


def initialize_gauge_tiles(tileset: tcod.tileset.Tileset) -> None:
    """게이지 타일 초기화 (TCOD 초기화 후 호출)"""
    manager = get_gauge_tile_manager()
    manager.initialize(tileset)


# 편의 함수들
def get_hp_tile(fill_ratio: float, hp_percent: float) -> Tuple[str, Tuple[int, int, int]]:
    """HP 게이지용 타일과 색상 반환
    
    Args:
        fill_ratio: 현재 셀의 채움 비율 (0.0 ~ 1.0)
        hp_percent: 전체 HP 비율 (색상 결정용)
    
    Returns:
        (타일 문자, 전경색)
    """
    manager = get_gauge_tile_manager()
    
    if hp_percent > 0.5:
        color_name = 'hp_high'
        color = GaugeColors.HP_HIGH
    elif hp_percent > 0.25:
        color_name = 'hp_mid'
        color = GaugeColors.HP_MID
    else:
        color_name = 'hp_low'
        color = GaugeColors.HP_LOW
    
    return manager.get_tile_char(color_name, fill_ratio), color


def get_mp_tile(fill_ratio: float) -> Tuple[str, Tuple[int, int, int]]:
    """MP 게이지용 타일과 색상 반환"""
    manager = get_gauge_tile_manager()
    return manager.get_tile_char('mp_fill', fill_ratio), GaugeColors.MP_FILL


def get_brv_tile(fill_ratio: float) -> Tuple[str, Tuple[int, int, int]]:
    """BRV 게이지용 타일과 색상 반환"""
    manager = get_gauge_tile_manager()
    return manager.get_tile_char('brv_fill', fill_ratio), GaugeColors.BRV_FILL


def get_damage_trail_tile(fill_ratio: float) -> Tuple[str, Tuple[int, int, int]]:
    """데미지 트레일용 타일과 색상 반환"""
    manager = get_gauge_tile_manager()
    return manager.get_tile_char('damage_trail', fill_ratio), GaugeColors.DAMAGE_TRAIL


def get_wound_tile(fill_ratio: float) -> Tuple[str, Tuple[int, int, int]]:
    """상처용 타일과 색상 반환"""
    manager = get_gauge_tile_manager()
    return manager.get_tile_char('wound', fill_ratio), GaugeColors.WOUND


def get_wound_stripe_tile(fill_ratio: float) -> Tuple[str, Tuple[int, int, int]]:
    """상처 빗금 패턴 타일과 색상 반환
    
    Args:
        fill_ratio: 오른쪽에서부터 채움 비율 (0.0 ~ 1.0)
    
    Returns:
        (타일 문자, 전경색)
    """
    manager = get_gauge_tile_manager()
    return manager.get_tile_char('wound_stripe', fill_ratio), GaugeColors.WOUND_STRIPE


def get_wound_fill_right_tile(fill_ratio: float) -> Tuple[str, Tuple[int, int, int]]:
    """상처 영역 타일 (오른쪽에서 채움) 반환
    
    Args:
        fill_ratio: 오른쪽에서부터 채움 비율 (0.0 ~ 1.0)
    
    Returns:
        (타일 문자, 전경색)
    """
    manager = get_gauge_tile_manager()
    return manager.get_tile_char('wound_fill_right', fill_ratio), GaugeColors.WOUND


def get_atb_tile(fill_ratio: float) -> Tuple[str, Tuple[int, int, int]]:
    """ATB 게이지용 타일과 색상 반환"""
    manager = get_gauge_tile_manager()
    return manager.get_tile_char('atb_fill', fill_ratio), GaugeColors.ATB_FILL


def get_cast_tile(fill_ratio: float) -> Tuple[str, Tuple[int, int, int]]:
    """캐스팅 게이지용 타일과 색상 반환"""
    manager = get_gauge_tile_manager()
    return manager.get_tile_char('cast_fill', fill_ratio), GaugeColors.CAST_FILL

