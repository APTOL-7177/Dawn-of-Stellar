"""
게이지 커스텀 타일셋 시스템

픽셀 단위 정밀 게이지 렌더링을 위한 커스텀 타일 생성 및 등록
- 16분할 또는 32분할 부분 채움 타일
- 다양한 색상 지원 (HP, MP, BRV, 데미지 트레일 등)
"""

import numpy as np
import tcod
import tcod.tileset
from typing import Dict, Tuple, Optional
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
    WOUND = (80, 30, 30)        # 어두운 빨강
    
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
        }
        
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
                self._create_tile(color_index, fill_level, color)
    
    def _create_tile(self, color_index: int, fill_level: int, color: Tuple[int, int, int]) -> None:
        """단일 타일 생성"""
        if self.tileset is None:
            return
        
        codepoint = self._get_codepoint(color_index, fill_level)
        
        if codepoint in self._created_tiles:
            return
        
        # RGBA 타일 이미지 생성
        tile = np.zeros((self.tile_height, self.tile_width, 4), dtype=np.uint8)
        
        # 채움 픽셀 수 계산
        fill_pixels = int((fill_level / self.divisions) * self.tile_width)
        
        # 채움 영역 (왼쪽에서 오른쪽으로)
        if fill_pixels > 0:
            tile[:, :fill_pixels, 0] = color[0]  # R
            tile[:, :fill_pixels, 1] = color[1]  # G
            tile[:, :fill_pixels, 2] = color[2]  # B
            tile[:, :fill_pixels, 3] = 255       # A (불투명)
        
        # 빈 영역 (투명으로 처리 - 배경색 표시용)
        # 투명 영역은 콘솔의 배경색이 표시됨
        
        # 타일 등록
        try:
            self.tileset.set_tile(codepoint, tile)
            self._created_tiles[codepoint] = True
        except Exception as e:
            logger.warning(f"타일 생성 실패 (codepoint={codepoint}): {e}")
    
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
    
    def get_fill_level(self, fill_ratio: float) -> int:
        """채움 비율을 분할 레벨로 변환"""
        level = int(fill_ratio * self.divisions)
        return max(0, min(self.divisions, level))
    
    def is_initialized(self) -> bool:
        """초기화 여부 확인"""
        return self.tileset is not None and len(self._created_tiles) > 0


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


def get_atb_tile(fill_ratio: float) -> Tuple[str, Tuple[int, int, int]]:
    """ATB 게이지용 타일과 색상 반환"""
    manager = get_gauge_tile_manager()
    return manager.get_tile_char('atb_fill', fill_ratio), GaugeColors.ATB_FILL


def get_cast_tile(fill_ratio: float) -> Tuple[str, Tuple[int, int, int]]:
    """캐스팅 게이지용 타일과 색상 반환"""
    manager = get_gauge_tile_manager()
    return manager.get_tile_char('cast_fill', fill_ratio), GaugeColors.CAST_FILL

