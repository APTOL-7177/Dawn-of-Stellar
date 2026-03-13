"""
particles.py - 파티클 시스템

최대 500개의 파티클을 관리합니다.
전투 이벤트(spark, magic, heal)에 연동되는 ParticleEmitter를 포함합니다.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pygame

from src.ui.pygame_backend.effects.base import EffectLayer
from src.core.logger import get_logger

logger = get_logger("effects.particles")

# 최대 파티클 수 (이 수를 초과하면 오래된 것부터 제거)
MAX_PARTICLES: int = 500


@dataclass
class Particle:
    """
    단일 파티클 데이터

    Attributes:
        x: 화면 X 좌표 (픽셀)
        y: 화면 Y 좌표 (픽셀)
        vx: X 속도 (픽셀/초)
        vy: Y 속도 (픽셀/초)
        color: RGB 색상 튜플
        life: 남은 수명 (초)
        size: 파티클 반지름 (픽셀)
        max_life: 초기 수명 (페이드아웃 비율 계산용)
    """
    x: float
    y: float
    vx: float
    vy: float
    color: Tuple[int, int, int]
    life: float
    size: float
    gravity: float = 80.0  # 프리셋별 중력 (양수=아래, 음수=위)
    max_life: float = field(init=False)

    def __post_init__(self) -> None:
        self.max_life = self.life

    @property
    def alive(self) -> bool:
        """파티클이 아직 살아있는지 여부"""
        return self.life > 0.0

    @property
    def alpha_ratio(self) -> float:
        """수명 기반 페이드아웃 비율 (1.0 → 0.0)"""
        if self.max_life <= 0:
            return 0.0
        return max(0.0, self.life / self.max_life)


# ── 이벤트 종류별 파티클 프리셋 ──────────────────────────────────────────
_PRESETS: Dict[str, Dict] = {
    "spark": {
        # 전투 공격 스파크: 밝은 주황/노랑, 빠른 속도, 짧은 수명
        "colors": [(255, 220, 80), (255, 140, 20), (255, 80, 20)],
        "speed_min": 60.0,
        "speed_max": 180.0,
        "life_min": 0.25,
        "life_max": 0.55,
        "size_min": 1.5,
        "size_max": 3.5,
        "gravity": 120.0,
        "count": 12,
    },
    "magic": {
        # 마법 이펙트: 보라/파랑/청록, 느린 속도, 긴 수명
        "colors": [(180, 80, 255), (80, 160, 255), (60, 220, 220)],
        "speed_min": 20.0,
        "speed_max": 80.0,
        "life_min": 0.5,
        "life_max": 1.2,
        "size_min": 2.0,
        "size_max": 5.0,
        "gravity": -20.0,  # 위로 떠오르는 느낌
        "count": 16,
    },
    "heal": {
        # 회복 이펙트: 초록/연두, 천천히 위로 떠오름
        "colors": [(80, 255, 120), (160, 255, 80), (200, 255, 160)],
        "speed_min": 15.0,
        "speed_max": 50.0,
        "life_min": 0.6,
        "life_max": 1.4,
        "size_min": 2.5,
        "size_max": 6.0,
        "gravity": -60.0,  # 위로 떠오름
        "count": 10,
    },
    # ── 원소별 스킬 파티클 프리셋 ────────────────────────────────────────
    "fire": {
        "colors": [(255, 100, 20), (255, 200, 50), (255, 60, 10)],
        "speed_min": 40.0,
        "speed_max": 140.0,
        "life_min": 0.3,
        "life_max": 0.8,
        "size_min": 2.0,
        "size_max": 5.0,
        "gravity": -40.0,  # 위로 (불꽃)
        "count": 20,
    },
    "ice": {
        "colors": [(100, 200, 255), (200, 230, 255), (60, 140, 255)],
        "speed_min": 20.0,
        "speed_max": 70.0,
        "life_min": 0.5,
        "life_max": 1.2,
        "size_min": 2.0,
        "size_max": 4.5,
        "gravity": 30.0,  # 살짝 아래로 (결정 낙하)
        "count": 18,
    },
    "lightning": {
        "colors": [(255, 255, 100), (255, 255, 255), (180, 120, 255)],
        "speed_min": 100.0,
        "speed_max": 250.0,
        "life_min": 0.1,
        "life_max": 0.35,
        "size_min": 1.5,
        "size_max": 3.5,
        "gravity": 0.0,  # 무중력 (전기 방전)
        "count": 24,
    },
    "water": {
        "colors": [(50, 100, 255), (80, 200, 220), (180, 220, 255)],
        "speed_min": 25.0,
        "speed_max": 80.0,
        "life_min": 0.4,
        "life_max": 1.0,
        "size_min": 2.5,
        "size_max": 5.5,
        "gravity": 60.0,  # 아래로 (물방울)
        "count": 16,
    },
    "earth": {
        "colors": [(150, 100, 50), (200, 150, 80), (100, 140, 60)],
        "speed_min": 30.0,
        "speed_max": 100.0,
        "life_min": 0.3,
        "life_max": 0.7,
        "size_min": 3.0,
        "size_max": 6.0,
        "gravity": 150.0,  # 강한 중력 (바위 파편)
        "count": 14,
    },
    "wind": {
        "colors": [(200, 255, 200), (220, 255, 255), (180, 240, 200)],
        "speed_min": 50.0,
        "speed_max": 120.0,
        "life_min": 0.5,
        "life_max": 1.3,
        "size_min": 1.5,
        "size_max": 3.5,
        "gravity": -30.0,  # 살짝 위로 (바람)
        "count": 22,
    },
    "holy": {
        "colors": [(255, 230, 120), (255, 255, 200), (255, 200, 80)],
        "speed_min": 15.0,
        "speed_max": 60.0,
        "life_min": 0.6,
        "life_max": 1.5,
        "size_min": 2.5,
        "size_max": 5.5,
        "gravity": -50.0,  # 위로 (성스러운 빛)
        "count": 16,
    },
    "dark": {
        "colors": [(80, 0, 120), (40, 0, 60), (150, 20, 40)],
        "speed_min": 30.0,
        "speed_max": 90.0,
        "life_min": 0.4,
        "life_max": 1.0,
        "size_min": 2.5,
        "size_max": 5.0,
        "gravity": 20.0,  # 살짝 아래로 (어둠)
        "count": 18,
    },
    "poison": {
        "colors": [(100, 200, 0), (150, 255, 50), (50, 80, 0)],
        "speed_min": 10.0,
        "speed_max": 40.0,
        "life_min": 0.8,
        "life_max": 1.8,
        "size_min": 2.0,
        "size_max": 4.5,
        "gravity": -20.0,  # 살짝 위로 (독 연기)
        "count": 14,
    },
    "heal_skill": {
        "colors": [(100, 255, 150), (150, 255, 100), (200, 255, 200)],
        "speed_min": 10.0,
        "speed_max": 40.0,
        "life_min": 0.8,
        "life_max": 1.6,
        "size_min": 2.5,
        "size_max": 5.5,
        "gravity": -70.0,  # 위로 떠오름 (치유 빛)
        "count": 12,
    },
    "buff": {
        "colors": [(255, 220, 80), (255, 255, 150), (255, 200, 50)],
        "speed_min": 10.0,
        "speed_max": 35.0,
        "life_min": 0.6,
        "life_max": 1.4,
        "size_min": 2.0,
        "size_max": 4.0,
        "gravity": -50.0,  # 위로 (강화 효과)
        "count": 10,
    },
    "physical": {
        "colors": [(255, 255, 255), (200, 200, 200), (180, 180, 180)],
        "speed_min": 60.0,
        "speed_max": 160.0,
        "life_min": 0.15,
        "life_max": 0.4,
        "size_min": 1.5,
        "size_max": 3.0,
        "gravity": 100.0,
        "count": 10,
    },
    "critical_burst": {
        "colors": [(255, 255, 255), (255, 255, 200), (255, 200, 100)],
        "speed_min": 80.0,
        "speed_max": 200.0,
        "life_min": 0.2,
        "life_max": 0.5,
        "size_min": 2.0,
        "size_max": 4.5,
        "gravity": 60.0,
        "count": 8,
    },
    "break_burst": {
        "colors": [(255, 50, 50), (255, 150, 50), (255, 255, 100)],
        "speed_min": 100.0,
        "speed_max": 260.0,
        "life_min": 0.3,
        "life_max": 0.7,
        "size_min": 3.0,
        "size_max": 7.0,
        "gravity": 80.0,
        "count": 25,
    },
    # ── 물리 공격 변형 ────────────────────────────────────────
    "slash_wide": {
        "colors": [(255, 255, 255), (200, 220, 255), (180, 200, 240)],
        "speed_min": 80.0, "speed_max": 200.0,
        "life_min": 0.15, "life_max": 0.35,
        "size_min": 1.5, "size_max": 3.0,
        "gravity": 0.0, "count": 14,
        "direction": 0.0, "spread": 0.4,
    },
    "slash_precise": {
        "colors": [(255, 255, 255), (220, 240, 255), (200, 200, 255)],
        "speed_min": 120.0, "speed_max": 280.0,
        "life_min": 0.1, "life_max": 0.25,
        "size_min": 1.0, "size_max": 2.5,
        "gravity": 0.0, "count": 10,
        "direction": -0.3, "spread": 0.2,
    },
    "thrust_impact": {
        "colors": [(255, 240, 200), (255, 220, 160), (255, 200, 100)],
        "speed_min": 100.0, "speed_max": 250.0,
        "life_min": 0.1, "life_max": 0.3,
        "size_min": 1.5, "size_max": 3.5,
        "gravity": 20.0, "count": 12,
        "direction": 0.0, "spread": 0.3,
    },
    "smash_ground": {
        "colors": [(200, 180, 150), (180, 160, 120), (150, 140, 100)],
        "speed_min": 60.0, "speed_max": 160.0,
        "life_min": 0.2, "life_max": 0.5,
        "size_min": 2.5, "size_max": 5.0,
        "gravity": 200.0, "count": 16,
        "direction": 1.5708, "spread": 0.6,
    },
    # ── 마법 공격 변형 ────────────────────────────────────────
    "magic_burst": {
        "colors": [(180, 100, 255), (100, 180, 255), (255, 180, 255)],
        "speed_min": 40.0, "speed_max": 120.0,
        "life_min": 0.4, "life_max": 0.9,
        "size_min": 2.0, "size_max": 4.5,
        "gravity": -10.0, "count": 20,
    },
    "magic_beam": {
        "colors": [(200, 150, 255), (255, 200, 255), (150, 100, 255)],
        "speed_min": 150.0, "speed_max": 300.0,
        "life_min": 0.1, "life_max": 0.25,
        "size_min": 1.0, "size_max": 2.5,
        "gravity": 0.0, "count": 16,
        "direction": 0.0, "spread": 0.15,
    },
    "arcane_pulse": {
        "colors": [(120, 80, 255), (180, 120, 255), (80, 40, 200)],
        "speed_min": 15.0, "speed_max": 50.0,
        "life_min": 0.6, "life_max": 1.4,
        "size_min": 3.0, "size_max": 6.0,
        "gravity": -5.0, "count": 14,
    },
    # ── 원소 변형 (2차 프리셋) ────────────────────────────────
    "flame_pillar": {
        "colors": [(255, 200, 50), (255, 120, 20), (255, 80, 0)],
        "speed_min": 60.0, "speed_max": 180.0,
        "life_min": 0.3, "life_max": 0.7,
        "size_min": 2.5, "size_max": 5.5,
        "gravity": -80.0, "count": 22,
        "direction": -1.5708, "spread": 0.3,
    },
    "fire_explosion": {
        "colors": [(255, 60, 10), (255, 160, 40), (200, 40, 0)],
        "speed_min": 80.0, "speed_max": 220.0,
        "life_min": 0.25, "life_max": 0.6,
        "size_min": 3.0, "size_max": 6.0,
        "gravity": 60.0, "count": 28,
    },
    "ice_shatter": {
        "colors": [(200, 240, 255), (140, 200, 255), (255, 255, 255)],
        "speed_min": 80.0, "speed_max": 200.0,
        "life_min": 0.2, "life_max": 0.5,
        "size_min": 1.5, "size_max": 4.0,
        "gravity": 40.0, "count": 20,
    },
    "frost_ring": {
        "colors": [(160, 220, 255), (200, 240, 255), (100, 180, 255)],
        "speed_min": 30.0, "speed_max": 70.0,
        "life_min": 0.6, "life_max": 1.3,
        "size_min": 3.0, "size_max": 6.0,
        "gravity": -5.0, "count": 16,
    },
    "thunder_bolt": {
        "colors": [(255, 255, 200), (255, 255, 100), (200, 180, 255)],
        "speed_min": 200.0, "speed_max": 400.0,
        "life_min": 0.05, "life_max": 0.2,
        "size_min": 1.0, "size_max": 3.0,
        "gravity": 300.0, "count": 20,
        "direction": 1.5708, "spread": 0.2,
    },
    "chain_lightning": {
        "colors": [(255, 255, 150), (200, 200, 255), (255, 220, 100)],
        "speed_min": 150.0, "speed_max": 350.0,
        "life_min": 0.05, "life_max": 0.15,
        "size_min": 1.0, "size_max": 2.5,
        "gravity": 0.0, "count": 22,
        "direction": 0.0, "spread": 0.8,
    },
    "water_torrent": {
        "colors": [(30, 80, 255), (60, 160, 255), (100, 200, 255)],
        "speed_min": 60.0, "speed_max": 150.0,
        "life_min": 0.3, "life_max": 0.8,
        "size_min": 2.5, "size_max": 5.0,
        "gravity": 40.0, "count": 20,
        "direction": 0.0, "spread": 0.5,
    },
    "tidal_wave": {
        "colors": [(40, 100, 200), (80, 180, 255), (60, 140, 220)],
        "speed_min": 40.0, "speed_max": 100.0,
        "life_min": 0.5, "life_max": 1.2,
        "size_min": 3.0, "size_max": 7.0,
        "gravity": 80.0, "count": 24,
        "direction": 1.885, "spread": 0.7,
    },
    "earth_shatter": {
        "colors": [(180, 130, 60), (140, 100, 40), (220, 180, 100)],
        "speed_min": 80.0, "speed_max": 180.0,
        "life_min": 0.2, "life_max": 0.6,
        "size_min": 3.0, "size_max": 7.0,
        "gravity": 200.0, "count": 18,
        "direction": -1.5708, "spread": 0.8,
    },
    "quake_wave": {
        "colors": [(160, 120, 60), (200, 160, 80), (120, 90, 40)],
        "speed_min": 100.0, "speed_max": 200.0,
        "life_min": 0.2, "life_max": 0.5,
        "size_min": 2.0, "size_max": 4.0,
        "gravity": 50.0, "count": 16,
        "direction": 0.0, "spread": 0.3,
    },
    "wind_blade": {
        "colors": [(200, 255, 220), (180, 255, 200), (160, 240, 180)],
        "speed_min": 120.0, "speed_max": 250.0,
        "life_min": 0.1, "life_max": 0.3,
        "size_min": 1.5, "size_max": 3.0,
        "gravity": 0.0, "count": 18,
        "direction": 0.0, "spread": 0.15,
    },
    "gale_spiral": {
        "colors": [(220, 255, 220), (200, 255, 240), (180, 240, 220)],
        "speed_min": 40.0, "speed_max": 100.0,
        "life_min": 0.5, "life_max": 1.2,
        "size_min": 2.0, "size_max": 4.0,
        "gravity": -40.0, "count": 20,
    },
    "holy_pillar": {
        "colors": [(255, 240, 150), (255, 255, 200), (255, 220, 100)],
        "speed_min": 30.0, "speed_max": 80.0,
        "life_min": 0.5, "life_max": 1.2,
        "size_min": 2.5, "size_max": 5.0,
        "gravity": -60.0, "count": 18,
        "direction": -1.5708, "spread": 0.25,
    },
    "divine_radiance": {
        "colors": [(255, 255, 180), (255, 240, 120), (255, 220, 200)],
        "speed_min": 20.0, "speed_max": 60.0,
        "life_min": 0.8, "life_max": 1.8,
        "size_min": 3.0, "size_max": 7.0,
        "gravity": -20.0, "count": 16,
    },
    "dark_vortex": {
        "colors": [(60, 0, 100), (30, 0, 50), (100, 0, 60)],
        "speed_min": 20.0, "speed_max": 60.0,
        "life_min": 0.6, "life_max": 1.4,
        "size_min": 2.5, "size_max": 5.5,
        "gravity": 10.0, "count": 20,
    },
    "shadow_claw": {
        "colors": [(80, 0, 100), (120, 20, 60), (60, 0, 80)],
        "speed_min": 100.0, "speed_max": 220.0,
        "life_min": 0.1, "life_max": 0.3,
        "size_min": 1.5, "size_max": 3.5,
        "gravity": 0.0, "count": 16,
        "direction": -0.3, "spread": 0.5,
    },
    # ── 직업별 고유 파티클 ────────────────────────────────────
    "sword_aura_slash": {
        "colors": [(200, 180, 255), (255, 255, 255), (160, 120, 255)],
        "speed_min": 100.0, "speed_max": 240.0,
        "life_min": 0.12, "life_max": 0.3,
        "size_min": 1.5, "size_max": 3.0,
        "gravity": 0.0, "count": 12,
        "direction": -0.2, "spread": 0.3,
    },
    "berserker_frenzy": {
        "colors": [(255, 30, 30), (255, 80, 20), (200, 0, 0)],
        "speed_min": 80.0, "speed_max": 220.0,
        "life_min": 0.15, "life_max": 0.4,
        "size_min": 2.0, "size_max": 5.0,
        "gravity": 40.0, "count": 20,
    },
    "stealth_strike": {
        "colors": [(100, 0, 150), (60, 0, 100), (200, 100, 255)],
        "speed_min": 150.0, "speed_max": 320.0,
        "life_min": 0.08, "life_max": 0.2,
        "size_min": 1.0, "size_max": 2.5,
        "gravity": 0.0, "count": 14,
        "direction": 0.0, "spread": 0.2,
    },
    "dragon_breath": {
        "colors": [(255, 100, 0), (255, 200, 50), (255, 50, 0)],
        "speed_min": 80.0, "speed_max": 200.0,
        "life_min": 0.3, "life_max": 0.7,
        "size_min": 3.0, "size_max": 7.0,
        "gravity": -20.0, "count": 26,
        "direction": 0.0, "spread": 0.6,
    },
    "dragon_mark_burst": {
        "colors": [(255, 150, 0), (255, 200, 50), (200, 100, 0)],
        "speed_min": 50.0, "speed_max": 150.0,
        "life_min": 0.3, "life_max": 0.8,
        "size_min": 2.5, "size_max": 5.5,
        "gravity": -30.0, "count": 20,
    },
    "necro_drain": {
        "colors": [(60, 0, 40), (100, 0, 60), (40, 80, 0)],
        "speed_min": 10.0, "speed_max": 40.0,
        "life_min": 0.8, "life_max": 1.6,
        "size_min": 2.0, "size_max": 4.5,
        "gravity": -30.0, "count": 14,
    },
    "hack_glitch": {
        "colors": [(0, 255, 0), (0, 200, 100), (100, 255, 100)],
        "speed_min": 40.0, "speed_max": 120.0,
        "life_min": 0.15, "life_max": 0.4,
        "size_min": 2.0, "size_max": 4.0,
        "gravity": 0.0, "count": 16,
    },
    "music_notes": {
        "colors": [(255, 200, 100), (200, 150, 255), (100, 255, 200)],
        "speed_min": 10.0, "speed_max": 40.0,
        "life_min": 1.0, "life_max": 2.0,
        "size_min": 2.5, "size_max": 5.0,
        "gravity": -40.0, "count": 8,
    },
    "monk_ki_burst": {
        "colors": [(255, 220, 100), (255, 200, 50), (200, 180, 255)],
        "speed_min": 60.0, "speed_max": 160.0,
        "life_min": 0.2, "life_max": 0.5,
        "size_min": 2.0, "size_max": 4.5,
        "gravity": 0.0, "count": 18,
    },
    "alchemy_burst": {
        "colors": [(255, 100, 200), (100, 255, 100), (100, 200, 255)],
        "speed_min": 30.0, "speed_max": 100.0,
        "life_min": 0.4, "life_max": 1.0,
        "size_min": 2.5, "size_max": 5.5,
        "gravity": -30.0, "count": 18,
    },
    "rune_activation": {
        "colors": [(150, 100, 255), (100, 150, 255), (200, 150, 255)],
        "speed_min": 25.0, "speed_max": 70.0,
        "life_min": 0.5, "life_max": 1.0,
        "size_min": 2.0, "size_max": 4.5,
        "gravity": -15.0, "count": 14,
    },
    "time_distortion": {
        "colors": [(180, 255, 255), (200, 200, 255), (255, 255, 220)],
        "speed_min": 10.0, "speed_max": 30.0,
        "life_min": 1.0, "life_max": 2.0,
        "size_min": 2.0, "size_max": 4.0,
        "gravity": 0.0, "count": 12,
    },
    "sniper_shot": {
        "colors": [(255, 255, 200), (200, 200, 180), (255, 200, 100)],
        "speed_min": 200.0, "speed_max": 400.0,
        "life_min": 0.05, "life_max": 0.15,
        "size_min": 1.0, "size_max": 2.0,
        "gravity": 0.0, "count": 10,
        "direction": 0.0, "spread": 0.08,
    },
    "phantom_slash": {
        "colors": [(160, 100, 255), (120, 60, 200), (200, 160, 255)],
        "speed_min": 80.0, "speed_max": 200.0,
        "life_min": 0.15, "life_max": 0.4,
        "size_min": 1.5, "size_max": 3.5,
        "gravity": 0.0, "count": 14,
        "direction": -0.2, "spread": 0.4,
    },
    "dimension_rift": {
        "colors": [(80, 0, 200), (0, 80, 255), (160, 0, 255)],
        "speed_min": 30.0, "speed_max": 80.0,
        "life_min": 0.5, "life_max": 1.2,
        "size_min": 2.5, "size_max": 5.0,
        "gravity": 0.0, "count": 16,
    },
    "yin_strike": {
        "colors": [(60, 60, 200), (80, 40, 180), (100, 80, 220)],
        "speed_min": 50.0, "speed_max": 120.0,
        "life_min": 0.3, "life_max": 0.7,
        "size_min": 2.0, "size_max": 4.0,
        "gravity": -20.0, "count": 14,
    },
    "yang_strike": {
        "colors": [(255, 200, 50), (255, 150, 20), (255, 255, 100)],
        "speed_min": 70.0, "speed_max": 180.0,
        "life_min": 0.2, "life_max": 0.5,
        "size_min": 2.0, "size_max": 4.5,
        "gravity": 0.0, "count": 16,
    },
    "cannon_blast": {
        "colors": [(200, 200, 200), (150, 150, 150), (255, 200, 100)],
        "speed_min": 60.0, "speed_max": 180.0,
        "life_min": 0.3, "life_max": 0.7,
        "size_min": 2.5, "size_max": 5.0,
        "gravity": 100.0, "count": 18,
        "direction": 0.0, "spread": 0.4,
    },
    "shield_impact": {
        "colors": [(200, 200, 255), (180, 180, 220), (255, 255, 255)],
        "speed_min": 40.0, "speed_max": 120.0,
        "life_min": 0.15, "life_max": 0.35,
        "size_min": 1.5, "size_max": 3.0,
        "gravity": 60.0, "count": 14,
        "direction": 3.14159, "spread": 0.5,
    },
    "drain_life": {
        "colors": [(200, 0, 0), (150, 50, 0), (50, 150, 50)],
        "speed_min": 15.0, "speed_max": 50.0,
        "life_min": 0.6, "life_max": 1.2,
        "size_min": 2.0, "size_max": 4.0,
        "gravity": -50.0, "count": 12,
    },
    "ultimate_flash": {
        "colors": [(255, 255, 255), (255, 255, 200), (255, 240, 160)],
        "speed_min": 60.0, "speed_max": 200.0,
        "life_min": 0.3, "life_max": 0.8,
        "size_min": 3.0, "size_max": 7.0,
        "gravity": -10.0, "count": 30,
    },
    "death_burst": {
        "colors": [(255, 100, 50), (255, 200, 100), (200, 50, 0)],
        "speed_min": 60.0, "speed_max": 180.0,
        "life_min": 0.4, "life_max": 1.0,
        "size_min": 2.5, "size_max": 6.0,
        "gravity": 60.0, "count": 30,
    },
    "aoe_ring": {
        "colors": [(255, 200, 100), (255, 150, 50), (255, 255, 200)],
        "speed_min": 100.0, "speed_max": 200.0,
        "life_min": 0.2, "life_max": 0.5,
        "size_min": 1.5, "size_max": 3.0,
        "gravity": 0.0, "count": 24,
    },
    "charge_release": {
        "colors": [(200, 50, 50), (255, 100, 50), (150, 0, 30)],
        "speed_min": 70.0, "speed_max": 200.0,
        "life_min": 0.2, "life_max": 0.6,
        "size_min": 2.5, "size_max": 5.5,
        "gravity": 20.0, "count": 22,
    },
    "stance_shift": {
        "colors": [(100, 200, 255), (150, 220, 255), (200, 240, 255)],
        "speed_min": 30.0, "speed_max": 80.0,
        "life_min": 0.3, "life_max": 0.7,
        "size_min": 2.0, "size_max": 4.0,
        "gravity": -20.0, "count": 12,
    },
    "duty_shield": {
        "colors": [(220, 200, 255), (180, 160, 255), (255, 240, 200)],
        "speed_min": 20.0, "speed_max": 60.0,
        "life_min": 0.5, "life_max": 1.0,
        "size_min": 2.5, "size_max": 5.0,
        "gravity": -10.0, "count": 14,
    },
    "crowd_roar": {
        "colors": [(255, 220, 80), (255, 180, 50), (255, 255, 150)],
        "speed_min": 40.0, "speed_max": 120.0,
        "life_min": 0.4, "life_max": 0.9,
        "size_min": 2.0, "size_max": 4.5,
        "gravity": -30.0, "count": 18,
    },
    "druid_nature": {
        "colors": [(50, 200, 50), (100, 255, 100), (80, 180, 40)],
        "speed_min": 20.0, "speed_max": 60.0,
        "life_min": 0.6, "life_max": 1.4,
        "size_min": 2.0, "size_max": 5.0,
        "gravity": -25.0, "count": 14,
    },
    "vampire_bite": {
        "colors": [(180, 0, 0), (120, 0, 30), (255, 50, 50)],
        "speed_min": 40.0, "speed_max": 100.0,
        "life_min": 0.3, "life_max": 0.7,
        "size_min": 1.5, "size_max": 3.5,
        "gravity": 30.0, "count": 14,
        "direction": 0.0, "spread": 0.4,
    },
    "spirit_summon": {
        "colors": [(100, 200, 255), (200, 255, 200), (255, 200, 100)],
        "speed_min": 25.0, "speed_max": 70.0,
        "life_min": 0.6, "life_max": 1.5,
        "size_min": 2.5, "size_max": 5.5,
        "gravity": -40.0, "count": 16,
    },
    "dilemma_resolve": {
        "colors": [(200, 200, 255), (255, 200, 200), (200, 255, 200)],
        "speed_min": 30.0, "speed_max": 80.0,
        "life_min": 0.5, "life_max": 1.0,
        "size_min": 2.0, "size_max": 4.5,
        "gravity": -15.0, "count": 14,
    },
    # ── 디버프 적용 파티클 ──────────────────────────────────────
    "debuff_poison": {
        "colors": [(80, 180, 0), (120, 200, 40), (40, 100, 0)],
        "speed_min": 8.0, "speed_max": 30.0,
        "life_min": 1.0, "life_max": 2.0,
        "size_min": 2.5, "size_max": 5.0,
        "gravity": -15.0, "count": 12,
    },
    "debuff_burn": {
        "colors": [(255, 120, 30), (255, 60, 0), (200, 40, 0)],
        "speed_min": 20.0, "speed_max": 60.0,
        "life_min": 0.5, "life_max": 1.2,
        "size_min": 2.0, "size_max": 4.0,
        "gravity": -50.0, "count": 14,
    },
    "debuff_freeze": {
        "colors": [(150, 220, 255), (200, 240, 255), (100, 180, 255)],
        "speed_min": 5.0, "speed_max": 20.0,
        "life_min": 1.0, "life_max": 2.0,
        "size_min": 3.0, "size_max": 6.0,
        "gravity": 10.0, "count": 10,
    },
    "debuff_stun": {
        "colors": [(255, 255, 100), (255, 200, 50), (255, 255, 200)],
        "speed_min": 15.0, "speed_max": 50.0,
        "life_min": 0.6, "life_max": 1.2,
        "size_min": 2.0, "size_max": 3.5,
        "gravity": -20.0, "count": 8,
    },
    "debuff_silence": {
        "colors": [(150, 100, 200), (100, 60, 160), (180, 140, 220)],
        "speed_min": 10.0, "speed_max": 35.0,
        "life_min": 0.8, "life_max": 1.5,
        "size_min": 2.0, "size_max": 4.0,
        "gravity": -10.0, "count": 10,
    },
    "debuff_bleed": {
        "colors": [(200, 0, 0), (150, 0, 0), (255, 50, 30)],
        "speed_min": 20.0, "speed_max": 60.0,
        "life_min": 0.4, "life_max": 0.9,
        "size_min": 1.5, "size_max": 3.5,
        "gravity": 120.0, "count": 12,
    },
    "debuff_curse": {
        "colors": [(80, 0, 80), (60, 0, 60), (120, 0, 100)],
        "speed_min": 10.0, "speed_max": 30.0,
        "life_min": 1.0, "life_max": 2.0,
        "size_min": 2.5, "size_max": 5.0,
        "gravity": -5.0, "count": 10,
    },
    "debuff_doom": {
        "colors": [(40, 0, 40), (80, 0, 0), (20, 0, 20)],
        "speed_min": 5.0, "speed_max": 20.0,
        "life_min": 1.5, "life_max": 3.0,
        "size_min": 3.0, "size_max": 7.0,
        "gravity": -3.0, "count": 8,
    },
    "debuff_slow": {
        "colors": [(100, 100, 200), (80, 80, 160), (120, 120, 220)],
        "speed_min": 5.0, "speed_max": 15.0,
        "life_min": 1.2, "life_max": 2.0,
        "size_min": 2.5, "size_max": 5.0,
        "gravity": 20.0, "count": 8,
    },
    "debuff_blind": {
        "colors": [(40, 40, 40), (20, 20, 20), (60, 60, 60)],
        "speed_min": 10.0, "speed_max": 30.0,
        "life_min": 0.8, "life_max": 1.5,
        "size_min": 3.0, "size_max": 6.0,
        "gravity": 10.0, "count": 10,
    },
    "debuff_confuse": {
        "colors": [(255, 100, 255), (200, 50, 200), (255, 150, 100)],
        "speed_min": 15.0, "speed_max": 50.0,
        "life_min": 0.8, "life_max": 1.5,
        "size_min": 2.0, "size_max": 4.0,
        "gravity": -20.0, "count": 10,
    },
    "debuff_paralyze": {
        "colors": [(255, 255, 50), (200, 200, 0), (255, 200, 100)],
        "speed_min": 30.0, "speed_max": 80.0,
        "life_min": 0.15, "life_max": 0.4,
        "size_min": 1.5, "size_max": 3.0,
        "gravity": 0.0, "count": 14,
    },
    "debuff_scatter": {
        "colors": [(200, 150, 100), (180, 120, 80), (220, 180, 120)],
        "speed_min": 40.0, "speed_max": 120.0,
        "life_min": 0.2, "life_max": 0.5,
        "size_min": 2.0, "size_max": 4.0,
        "gravity": 150.0, "count": 14,
        "direction": 1.5708, "spread": 0.8,
    },
    # ── 힐 바리에이션 ──────────────────────────────────────────
    "heal_group": {
        "colors": [(80, 255, 150), (120, 255, 100), (160, 255, 200)],
        "speed_min": 15.0, "speed_max": 60.0,
        "life_min": 0.8, "life_max": 1.8,
        "size_min": 3.0, "size_max": 6.0,
        "gravity": -80.0, "count": 18,
    },
    "heal_resurrection": {
        "colors": [(255, 255, 200), (255, 240, 120), (255, 220, 80)],
        "speed_min": 20.0, "speed_max": 70.0,
        "life_min": 1.0, "life_max": 2.5,
        "size_min": 3.0, "size_max": 7.0,
        "gravity": -100.0, "count": 24,
    },
    "heal_cleanse": {
        "colors": [(200, 255, 255), (150, 240, 255), (255, 255, 255)],
        "speed_min": 20.0, "speed_max": 60.0,
        "life_min": 0.6, "life_max": 1.4,
        "size_min": 2.5, "size_max": 5.0,
        "gravity": -60.0, "count": 14,
    },
    "heal_mp_restore": {
        "colors": [(80, 120, 255), (100, 180, 255), (160, 200, 255)],
        "speed_min": 10.0, "speed_max": 40.0,
        "life_min": 0.8, "life_max": 1.6,
        "size_min": 2.0, "size_max": 4.5,
        "gravity": -50.0, "count": 12,
    },
    # ── 버프 세분화 ────────────────────────────────────────────
    "buff_attack": {
        "colors": [(255, 100, 50), (255, 150, 80), (255, 200, 120)],
        "speed_min": 20.0, "speed_max": 60.0,
        "life_min": 0.5, "life_max": 1.2,
        "size_min": 2.0, "size_max": 4.5,
        "gravity": -40.0, "count": 12,
    },
    "buff_defense": {
        "colors": [(100, 150, 255), (150, 200, 255), (200, 220, 255)],
        "speed_min": 15.0, "speed_max": 45.0,
        "life_min": 0.6, "life_max": 1.4,
        "size_min": 2.5, "size_max": 5.0,
        "gravity": -30.0, "count": 12,
    },
    "buff_speed": {
        "colors": [(200, 255, 200), (150, 255, 150), (255, 255, 200)],
        "speed_min": 50.0, "speed_max": 120.0,
        "life_min": 0.3, "life_max": 0.7,
        "size_min": 1.5, "size_max": 3.0,
        "gravity": -20.0, "count": 16,
    },
    "buff_barrier": {
        "colors": [(180, 220, 255), (200, 240, 255), (220, 240, 255)],
        "speed_min": 10.0, "speed_max": 30.0,
        "life_min": 1.0, "life_max": 2.0,
        "size_min": 3.0, "size_max": 6.0,
        "gravity": -10.0, "count": 10,
    },
    "buff_regen": {
        "colors": [(100, 255, 120), (80, 200, 100), (150, 255, 160)],
        "speed_min": 8.0, "speed_max": 25.0,
        "life_min": 1.0, "life_max": 2.0,
        "size_min": 2.0, "size_max": 4.0,
        "gravity": -40.0, "count": 8,
    },
    "buff_critical": {
        "colors": [(255, 200, 50), (255, 150, 30), (255, 255, 100)],
        "speed_min": 30.0, "speed_max": 80.0,
        "life_min": 0.4, "life_max": 0.9,
        "size_min": 1.5, "size_max": 3.5,
        "gravity": -30.0, "count": 12,
    },
    "buff_haste": {
        "colors": [(255, 255, 150), (220, 255, 180), (255, 255, 220)],
        "speed_min": 80.0, "speed_max": 180.0,
        "life_min": 0.15, "life_max": 0.35,
        "size_min": 1.5, "size_max": 3.0,
        "gravity": 0.0, "count": 18,
    },
    "buff_invincible": {
        "colors": [(255, 255, 255), (255, 255, 200), (255, 240, 150)],
        "speed_min": 15.0, "speed_max": 50.0,
        "life_min": 1.0, "life_max": 2.5,
        "size_min": 3.0, "size_max": 7.0,
        "gravity": -15.0, "count": 16,
    },
    # ── 전투 행동 이펙트 ───────────────────────────────────────
    "defend_guard": {
        "colors": [(180, 200, 255), (200, 220, 255), (160, 180, 240)],
        "speed_min": 10.0, "speed_max": 40.0,
        "life_min": 0.5, "life_max": 1.2,
        "size_min": 3.0, "size_max": 6.0,
        "gravity": 0.0, "count": 10,
    },
    "counter_attack": {
        "colors": [(255, 200, 50), (255, 255, 100), (255, 150, 30)],
        "speed_min": 100.0, "speed_max": 250.0,
        "life_min": 0.1, "life_max": 0.3,
        "size_min": 1.5, "size_max": 3.5,
        "gravity": 0.0, "count": 16,
        "direction": 3.14159, "spread": 0.3,
    },
    "dodge_evade": {
        "colors": [(200, 200, 255), (180, 180, 240), (220, 220, 255)],
        "speed_min": 60.0, "speed_max": 140.0,
        "life_min": 0.1, "life_max": 0.3,
        "size_min": 1.0, "size_max": 2.5,
        "gravity": 0.0, "count": 10,
        "direction": 0.0, "spread": 0.2,
    },
    # ── 아이템 사용 이펙트 ─────────────────────────────────────
    "item_potion": {
        "colors": [(100, 255, 150), (150, 255, 100), (200, 255, 180)],
        "speed_min": 10.0, "speed_max": 35.0,
        "life_min": 0.6, "life_max": 1.2,
        "size_min": 2.0, "size_max": 4.0,
        "gravity": -40.0, "count": 10,
    },
    "item_ether": {
        "colors": [(80, 140, 255), (120, 180, 255), (160, 200, 255)],
        "speed_min": 10.0, "speed_max": 35.0,
        "life_min": 0.6, "life_max": 1.2,
        "size_min": 2.0, "size_max": 4.0,
        "gravity": -40.0, "count": 10,
    },
    "item_bomb": {
        "colors": [(255, 100, 20), (255, 60, 0), (255, 200, 50)],
        "speed_min": 80.0, "speed_max": 200.0,
        "life_min": 0.25, "life_max": 0.6,
        "size_min": 2.5, "size_max": 5.5,
        "gravity": 80.0, "count": 22,
    },
    "item_antidote": {
        "colors": [(200, 255, 200), (150, 255, 150), (255, 255, 220)],
        "speed_min": 10.0, "speed_max": 30.0,
        "life_min": 0.8, "life_max": 1.5,
        "size_min": 2.0, "size_max": 4.0,
        "gravity": -50.0, "count": 10,
    },
    "item_elixir": {
        "colors": [(255, 220, 100), (255, 255, 180), (200, 180, 255)],
        "speed_min": 15.0, "speed_max": 50.0,
        "life_min": 1.0, "life_max": 2.0,
        "size_min": 3.0, "size_max": 6.0,
        "gravity": -60.0, "count": 16,
    },
    # ── 특수 상황 이펙트 ───────────────────────────────────────
    "level_up": {
        "colors": [(255, 255, 100), (255, 255, 200), (255, 220, 50)],
        "speed_min": 30.0, "speed_max": 100.0,
        "life_min": 0.8, "life_max": 2.0,
        "size_min": 2.5, "size_max": 5.5,
        "gravity": -80.0, "count": 30,
    },
    "revive_flash": {
        "colors": [(255, 255, 255), (255, 255, 200), (255, 240, 100)],
        "speed_min": 20.0, "speed_max": 80.0,
        "life_min": 0.8, "life_max": 2.0,
        "size_min": 3.0, "size_max": 7.0,
        "gravity": -70.0, "count": 24,
    },
    "absorb_drain": {
        "colors": [(150, 50, 200), (200, 0, 150), (100, 0, 100)],
        "speed_min": 20.0, "speed_max": 60.0,
        "life_min": 0.5, "life_max": 1.2,
        "size_min": 2.0, "size_max": 4.0,
        "gravity": -40.0, "count": 12,
    },
    "reflect_barrier": {
        "colors": [(200, 220, 255), (255, 255, 255), (180, 200, 240)],
        "speed_min": 40.0, "speed_max": 100.0,
        "life_min": 0.2, "life_max": 0.5,
        "size_min": 1.5, "size_max": 3.5,
        "gravity": 0.0, "count": 14,
        "direction": 3.14159, "spread": 0.6,
    },
    "provoke_taunt": {
        "colors": [(255, 50, 50), (255, 100, 50), (200, 30, 30)],
        "speed_min": 20.0, "speed_max": 50.0,
        "life_min": 0.6, "life_max": 1.2,
        "size_min": 2.0, "size_max": 4.0,
        "gravity": -20.0, "count": 10,
    },
}


class ParticleEmitter:
    """
    전투 이벤트 연동 파티클 방출기

    emit() 메서드를 호출하여 특정 위치에 파티클을 생성합니다.
    """

    def emit(
        self,
        particles: List[Particle],
        x: float,
        y: float,
        event_type: str = "spark",
        count_override: Optional[int] = None,
    ) -> None:
        """
        파티클 방출

        Args:
            particles: 파티클 목록 (ParticleEffect가 관리)
            x: 방출 위치 X (픽셀)
            y: 방출 위치 Y (픽셀)
            event_type: 이벤트 종류 ("spark", "magic", "heal")
            count_override: 생성 개수 오버라이드 (None이면 프리셋 기본값)
        """
        preset = _PRESETS.get(event_type, _PRESETS["spark"])
        count = count_override if count_override is not None else preset["count"]

        # 최대 파티클 수 초과 방지: 오래된 것부터 제거
        if len(particles) + count > MAX_PARTICLES:
            overflow = (len(particles) + count) - MAX_PARTICLES
            del particles[:overflow]

        for _ in range(count):
            # 방향성 방출 지원: direction이 설정된 경우 해당 방향 ± spread 범위
            direction = preset.get("direction")
            spread = preset.get("spread", math.pi)
            if direction is not None:
                angle = direction + random.uniform(-spread, spread)
            else:
                angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(preset["speed_min"], preset["speed_max"])
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed

            color = random.choice(preset["colors"])
            life = random.uniform(preset["life_min"], preset["life_max"])
            size = random.uniform(preset["size_min"], preset["size_max"])

            # 방출 위치에 약간의 흩어짐 추가
            px = x + random.uniform(-4, 4)
            py = y + random.uniform(-4, 4)

            p = Particle(
                x=px, y=py,
                vx=vx, vy=vy,
                color=color,
                life=life,
                size=size,
                gravity=preset.get("gravity", 80.0),
            )
            # max_life는 __post_init__에서 자동 설정
            particles.append(p)


class ParticleEffect(EffectLayer):
    """
    파티클 시스템 이펙트 레이어

    최대 MAX_PARTICLES(500)개의 파티클을 관리하며,
    ParticleEmitter를 통해 전투 이벤트와 연동됩니다.
    """

    def __init__(self, enabled: bool = True) -> None:
        super().__init__(enabled)
        # 활성 파티클 목록
        self._particles: List[Particle] = []
        # 파티클 방출기 (외부에서 접근 가능)
        self.emitter: ParticleEmitter = ParticleEmitter()
        # 파티클 렌더링용 임시 Surface (알파 지원)
        self._particle_surf: Optional[pygame.Surface] = None
        self._surf_size: Tuple[int, int] = (0, 0)

    @property
    def particles(self) -> List[Particle]:
        """활성 파티클 목록 (읽기 전용 접근용)"""
        return self._particles

    def emit(
        self,
        x: float,
        y: float,
        event_type: str = "spark",
        count: Optional[int] = None,
    ) -> None:
        """
        편의 메서드: 파티클 방출

        Args:
            x: 화면 X 좌표 (픽셀)
            y: 화면 Y 좌표 (픽셀)
            event_type: 이벤트 종류 ("spark", "magic", "heal")
            count: 생성 개수 (None이면 프리셋 기본값)
        """
        if not self.enabled:
            return
        self.emitter.emit(self._particles, x, y, event_type, count)

    def update(self, dt: float) -> None:
        """
        모든 파티클 물리 업데이트

        Args:
            dt: 경과 시간 (초)
        """
        if not self.enabled:
            return

        alive: List[Particle] = []
        for p in self._particles:
            if not p.alive:
                continue

            # 속도 업데이트 (파티클별 중력 적용)
            p.vy += p.gravity * dt
            # 위치 업데이트
            p.x += p.vx * dt
            p.y += p.vy * dt
            # 수명 감소
            p.life -= dt

            if p.alive:
                alive.append(p)

        self._particles = alive

    def render(self, surface: pygame.Surface) -> None:
        """
        파티클을 surface에 렌더링

        Args:
            surface: 렌더링 대상 Surface
        """
        if not self.enabled or not self._particles:
            return

        w, h = surface.get_size()

        # 알파 지원 임시 Surface 준비 (크기 변경 시 재생성)
        if self._surf_size != (w, h) or self._particle_surf is None:
            self._particle_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            self._surf_size = (w, h)

        self._particle_surf.fill((0, 0, 0, 0))  # 투명으로 초기화

        for p in self._particles:
            # 화면 범위 밖 파티클은 스킵
            if p.x < 0 or p.x >= w or p.y < 0 or p.y >= h:
                continue

            # 수명 기반 알파 (페이드아웃)
            alpha = int(p.alpha_ratio * 255)
            if alpha <= 0:
                continue

            r, g, b = p.color
            radius = max(1, int(p.size))

            try:
                pygame.draw.circle(
                    self._particle_surf,
                    (r, g, b, alpha),
                    (int(p.x), int(p.y)),
                    radius,
                )
            except Exception:
                pass  # 개별 파티클 렌더링 실패는 무시

        # BLEND_ADD로 합성하여 발광 효과
        surface.blit(self._particle_surf, (0, 0), special_flags=pygame.BLEND_ADD)
