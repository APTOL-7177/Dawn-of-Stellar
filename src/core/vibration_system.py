"""
Vibration System - 게임패드 진동 관리

상황별 게임패드 진동을 처리하는 시스템
"""

import pygame
import threading
import time
import os
import yaml
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from src.core.logger import get_logger


class VibrationPattern(Enum):
    """진동 패턴 타입"""
    LIGHT_TAP = "light_tap"           # 가벼운 탭 (아이템 줍기, 메뉴 선택)
    MEDIUM_TAP = "medium_tap"         # 중간 탭 (일반 공격, 상호작용)
    HEAVY_TAP = "heavy_tap"           # 강한 탭 (크리티컬 히트, 강력한 공격)
    SUCCESS = "success"               # 성공 (레벨업, 퀘스트 완료)
    FAILURE = "failure"               # 실패 (공격 실패, 아이템 사용 실패)
    DAMAGE_LIGHT = "damage_light"     # 가벼운 피격
    DAMAGE_MEDIUM = "damage_medium"   # 중간 피격
    DAMAGE_HEAVY = "damage_heavy"     # 강한 피격
    DEATH = "death"                   # 사망
    HEALING = "healing"               # 회복 (포션 사용)
    LEVEL_UP = "level_up"             # 레벨업
    BOSS_WARNING = "boss_warning"     # 보스 등장 경고
    TRAP_TRIGGER = "trap_trigger"     # 함정 발동
    DOOR_OPEN = "door_open"           # 문 열기
    ITEM_PICKUP = "item_pickup"       # 아이템 줍기
    EQUIPMENT_BREAK = "equipment_break"  # 장비 파괴
    SKILL_CAST = "skill_cast"         # 스킬 시전
    COMBAT_START = "combat_start"     # 전투 시작
    COMBAT_END = "combat_end"         # 전투 종료


@dataclass
class VibrationConfig:
    """진동 설정"""
    left_motor: float = 0.0      # 왼쪽 모터 강도 (0.0-1.0)
    right_motor: float = 0.0     # 오른쪽 모터 강도 (0.0-1.0)
    duration: float = 0.0        # 지속시간 (초)
    fade_in: float = 0.0         # 페이드인 시간 (초)
    fade_out: float = 0.0        # 페이드아웃 시간 (초)

    def __post_init__(self):
        # 값 범위 제한
        self.left_motor = max(0.0, min(1.0, self.left_motor))
        self.right_motor = max(0.0, min(1.0, self.right_motor))
        self.duration = max(0.0, self.duration)
        self.fade_in = max(0.0, self.fade_in)
        self.fade_out = max(0.0, self.fade_out)


class VibrationManager:
    """
    진동 관리자

    게임패드 진동을 제어하고 상황별 진동 패턴을 관리
    """

    def __init__(self) -> None:
        self.logger = get_logger("vibration")

        # 설정 파일 경로
        self.config_path = os.path.join("config", "vibration.yaml")

        # 현재 실행 중인 진동들
        self.active_vibrations: Dict[str, threading.Thread] = {}

        # 진동 패턴 정의 (기본값)
        self.patterns = self._define_patterns()

        # 게임패드 참조 (input_handler에서 설정)
        self.joystick: Optional[pygame.joystick.Joystick] = None

        # 패턴 강도 조절값 (설정 파일에서 로드)
        self.pattern_intensities: Dict[str, float] = {}

        # 이벤트 활성화 상태
        self.event_enabled: Dict[str, bool] = {}

        # 설정 로드
        self._load_config()

        self.logger.info("진동 시스템 초기화됨")

    def _load_config(self) -> None:
        """설정 파일 로드"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)

                if config:
                    # 기본 설정
                    self.enabled = config.get('enabled', True)
                    self.global_intensity = config.get('global_intensity', 1.0)

                    # 패턴 강도
                    pattern_intensities = config.get('pattern_intensities', {})
                    for pattern_name, intensity in pattern_intensities.items():
                        self.pattern_intensities[pattern_name] = max(0.0, min(1.0, intensity))

                    # 이벤트 활성화 상태
                    event_vibrations = config.get('event_vibrations', {})
                    self.event_enabled.update(event_vibrations)

                    # 고급 설정
                    advanced = config.get('advanced', {})
                    self.duration_multiplier = advanced.get('duration_multiplier', 1.0)
                    self.enable_fade_effects = advanced.get('enable_fade_effects', True)
                    self.max_concurrent_vibrations = advanced.get('max_concurrent_vibrations', 3)

                self.logger.info(f"진동 설정 로드됨: 활성화={self.enabled}, 강도={self.global_intensity}")
            else:
                self.logger.info("진동 설정 파일 없음, 기본값 사용")
                # 기본값 설정
                self.enabled = True
                self.global_intensity = 1.0
                self.duration_multiplier = 1.0
                self.enable_fade_effects = True
                self.max_concurrent_vibrations = 3

        except Exception as e:
            self.logger.error(f"진동 설정 로드 실패: {e}")
            # 오류 시 기본값 사용
            self.enabled = True
            self.global_intensity = 1.0
            self.duration_multiplier = 1.0
            self.enable_fade_effects = True
            self.max_concurrent_vibrations = 3

    def _define_patterns(self) -> Dict[VibrationPattern, VibrationConfig]:
        """진동 패턴 정의"""
        return {
            # 가벼운 피드백
            VibrationPattern.LIGHT_TAP: VibrationConfig(
                left_motor=0.2, right_motor=0.2, duration=0.1
            ),
            VibrationPattern.MEDIUM_TAP: VibrationConfig(
                left_motor=0.4, right_motor=0.4, duration=0.15
            ),
            VibrationPattern.HEAVY_TAP: VibrationConfig(
                left_motor=0.7, right_motor=0.7, duration=0.2
            ),

            # 성공/실패 피드백
            VibrationPattern.SUCCESS: VibrationConfig(
                left_motor=0.3, right_motor=0.6, duration=0.3, fade_out=0.1
            ),
            VibrationPattern.FAILURE: VibrationConfig(
                left_motor=0.6, right_motor=0.2, duration=0.4, fade_out=0.2
            ),

            # 피해 피드백
            VibrationPattern.DAMAGE_LIGHT: VibrationConfig(
                left_motor=0.5, right_motor=0.3, duration=0.2
            ),
            VibrationPattern.DAMAGE_MEDIUM: VibrationConfig(
                left_motor=0.7, right_motor=0.5, duration=0.3, fade_in=0.05
            ),
            VibrationPattern.DAMAGE_HEAVY: VibrationConfig(
                left_motor=1.0, right_motor=0.8, duration=0.5, fade_in=0.1, fade_out=0.2
            ),

            # 특별 이벤트
            VibrationPattern.DEATH: VibrationConfig(
                left_motor=0.8, right_motor=0.8, duration=1.0, fade_out=0.5
            ),
            VibrationPattern.HEALING: VibrationConfig(
                left_motor=0.2, right_motor=0.4, duration=0.5, fade_in=0.1, fade_out=0.2
            ),
            VibrationPattern.LEVEL_UP: VibrationConfig(
                left_motor=0.4, right_motor=0.4, duration=0.8, fade_in=0.1, fade_out=0.3
            ),

            # 전투 이벤트
            VibrationPattern.BOSS_WARNING: VibrationConfig(
                left_motor=0.6, right_motor=0.6, duration=2.0, fade_in=0.5, fade_out=1.0
            ),
            VibrationPattern.TRAP_TRIGGER: VibrationConfig(
                left_motor=0.8, right_motor=0.4, duration=0.6, fade_in=0.1
            ),

            # 세계 이벤트
            VibrationPattern.DOOR_OPEN: VibrationConfig(
                left_motor=0.3, right_motor=0.3, duration=0.2
            ),
            VibrationPattern.ITEM_PICKUP: VibrationConfig(
                left_motor=0.2, right_motor=0.2, duration=0.1
            ),
            VibrationPattern.EQUIPMENT_BREAK: VibrationConfig(
                left_motor=0.9, right_motor=0.5, duration=0.7, fade_out=0.3
            ),

            # 스킬 이벤트
            VibrationPattern.SKILL_CAST: VibrationConfig(
                left_motor=0.4, right_motor=0.6, duration=0.3, fade_in=0.05
            ),

            # 전투 상태
            VibrationPattern.COMBAT_START: VibrationConfig(
                left_motor=0.5, right_motor=0.5, duration=0.4, fade_in=0.1
            ),
            VibrationPattern.COMBAT_END: VibrationConfig(
                left_motor=0.3, right_motor=0.3, duration=0.6, fade_out=0.3
            ),
        }

    def set_joystick(self, joystick: Optional[pygame.joystick.Joystick]) -> None:
        """게임패드 설정"""
        self.joystick = joystick
        if joystick:
            self.logger.debug(f"진동 시스템에 게임패드 연결: {joystick.get_name()}")
        else:
            self.logger.debug("진동 시스템에서 게임패드 연결 해제")

    def vibrate(self, pattern: VibrationPattern, custom_config: Optional[VibrationConfig] = None, force: bool = False) -> None:
        """
        진동 실행

        Args:
            pattern: 진동 패턴
            custom_config: 사용자 정의 설정 (없으면 기본 패턴 사용)
            force: 강제 실행 (활성화 상태 무시)
        """
        if not force and (not self.enabled or not self.joystick):
            return

        # 최대 동시 진동 수 제한
        if len(self.active_vibrations) >= self.max_concurrent_vibrations:
            self.logger.debug("최대 동시 진동 수 초과, 건너뜀")
            return

        config = custom_config or self.patterns.get(pattern)
        if not config:
            self.logger.warning(f"알 수 없는 진동 패턴: {pattern}")
            return

        # 패턴 강도 조절 적용
        pattern_intensity = self.pattern_intensities.get(pattern.value, 1.0)

        # 강도 조절 적용
        adjusted_config = VibrationConfig(
            left_motor=config.left_motor * self.global_intensity * pattern_intensity,
            right_motor=config.right_motor * self.global_intensity * pattern_intensity,
            duration=config.duration * self.duration_multiplier,
            fade_in=config.fade_in if self.enable_fade_effects else 0.0,
            fade_out=config.fade_out if self.enable_fade_effects else 0.0
        )

        # 진동 실행 (별도 스레드에서)
        vibration_id = f"{pattern.value}_{time.time()}"
        thread = threading.Thread(
            target=self._execute_vibration,
            args=(vibration_id, adjusted_config),
            daemon=True
        )
        self.active_vibrations[vibration_id] = thread
        thread.start()

        self.logger.debug(f"진동 실행: {pattern.value} (강도: L{adjusted_config.left_motor:.1f}, R{adjusted_config.right_motor:.1f})")

    def _execute_vibration(self, vibration_id: str, config: VibrationConfig) -> None:
        """진동 실행 (별도 스레드)"""
        try:
            if not self.joystick:
                return

            start_time = time.time()
            end_time = start_time + config.duration

            while time.time() < end_time:
                elapsed = time.time() - start_time
                progress = elapsed / config.duration

                # 페이드 계산
                fade_multiplier = 1.0

                # 페이드인
                if config.fade_in > 0 and elapsed < config.fade_in:
                    fade_multiplier = elapsed / config.fade_in

                # 페이드아웃
                elif config.fade_out > 0 and elapsed > (config.duration - config.fade_out):
                    remaining = config.duration - elapsed
                    fade_multiplier = remaining / config.fade_out

                # 진동 적용
                left_strength = int(config.left_motor * fade_multiplier * 65535)
                right_strength = int(config.right_motor * fade_multiplier * 65535)

                # pygame rumble 사용 (가능한 경우)
                try:
                    if hasattr(self.joystick, 'rumble'):
                        self.joystick.rumble(left_strength, right_strength, 100)  # 100ms
                    else:
                        # 대안: 일반적인 rumble 메소드 시도
                        self.joystick.rumble(left_strength, right_strength, 100)
                except (AttributeError, TypeError):
                    # rumble 미지원시 건너뜀
                    pass

                time.sleep(0.1)  # 100ms 간격으로 업데이트

            # 진동 정지
            try:
                if hasattr(self.joystick, 'rumble'):
                    self.joystick.rumble(0, 0, 0)
                else:
                    self.joystick.rumble(0, 0, 0)
            except (AttributeError, TypeError):
                pass

        except Exception as e:
            self.logger.error(f"진동 실행 실패: {e}")
        finally:
            # 완료된 진동 제거
            if vibration_id in self.active_vibrations:
                del self.active_vibrations[vibration_id]

    def stop_all_vibrations(self) -> None:
        """모든 진동 정지"""
        if self.joystick:
            try:
                if hasattr(self.joystick, 'rumble'):
                    self.joystick.rumble(0, 0, 0)
                else:
                    self.joystick.rumble(0, 0, 0)
            except (AttributeError, TypeError):
                pass

        # 활성 진동들 정리
        self.active_vibrations.clear()
        self.logger.debug("모든 진동 정지됨")

    def set_enabled(self, enabled: bool) -> None:
        """진동 활성화/비활성화"""
        self.enabled = enabled
        if not enabled:
            self.stop_all_vibrations()
        self.logger.info(f"진동 시스템 {'활성화' if enabled else '비활성화'}됨")

    def set_global_intensity(self, intensity: float) -> None:
        """전체 진동 강도 설정"""
        self.global_intensity = max(0.0, min(1.0, intensity))
        self.logger.info(f"진동 강도 설정: {self.global_intensity:.1f}")

    def get_pattern_names(self) -> list:
        """사용 가능한 진동 패턴 이름 목록"""
        return [pattern.value for pattern in VibrationPattern]


class VibrationEventListener:
    """
    진동 이벤트 리스너

    이벤트 버스로부터 이벤트를 받아 진동을 실행
    """

    def __init__(self, vibration_manager: VibrationManager):
        self.vibration_manager = vibration_manager
        self.logger = get_logger("vibration_events")

        # 이벤트 매핑: 이벤트 이름 -> 진동 패턴
        self.event_mappings = {
            # 전투 이벤트
            "combat.start": VibrationPattern.COMBAT_START,
            "combat.end": VibrationPattern.COMBAT_END,
            "combat.damage_dealt": self._handle_damage_dealt,
            "combat.damage_taken": self._handle_damage_taken,

            # 캐릭터 이벤트
            "character.hp_change": self._handle_hp_change,
            "character.death": VibrationPattern.DEATH,
            "character.level_up": VibrationPattern.LEVEL_UP,

            # 스킬 이벤트
            "skill.cast_start": VibrationPattern.SKILL_CAST,
            "skill.execute": VibrationPattern.MEDIUM_TAP,

            # 상태 효과 이벤트
            "status.applied": VibrationPattern.LIGHT_TAP,
            "status.dot_damage": VibrationPattern.DAMAGE_LIGHT,

            # 세계 이벤트
            "world.item_pickup": VibrationPattern.ITEM_PICKUP,
            "world.door_open": VibrationPattern.DOOR_OPEN,
            "world.enemy_spawn": self._handle_enemy_spawn,

            # 장비 이벤트
            "equipment.broken": VibrationPattern.EQUIPMENT_BREAK,

            # UI 이벤트
            "ui.menu_open": VibrationPattern.LIGHT_TAP,
            "ui.menu_close": VibrationPattern.LIGHT_TAP,
        }

    def handle_event(self, event_name: str, data: Any = None) -> None:
        """
        이벤트 처리

        Args:
            event_name: 이벤트 이름
            data: 이벤트 데이터
        """
        if event_name in self.event_mappings:
            # 이벤트 활성화 상태 확인
            if not self._is_event_enabled(event_name):
                return

            mapping = self.event_mappings[event_name]

            if isinstance(mapping, VibrationPattern):
                # 직접 패턴 매핑
                self.vibration_manager.vibrate(mapping)
            elif callable(mapping):
                # 커스텀 핸들러 함수
                try:
                    mapping(data)
                except Exception as e:
                    self.logger.error(f"이벤트 핸들러 실행 실패: {event_name} - {e}")
            else:
                self.logger.warning(f"알 수 없는 이벤트 매핑 타입: {event_name}")

    def _is_event_enabled(self, event_name: str) -> bool:
        """이벤트 진동 활성화 상태 확인"""
        # 이벤트 카테고리 매핑
        event_categories = {
            "combat_damage": ["combat.damage_dealt", "combat.damage_taken"],
            "character_events": ["character.hp_change", "character.death", "character.level_up"],
            "skill_casting": ["skill.cast_start", "skill.execute"],
            "world_interaction": ["world.item_pickup", "world.door_open", "world.enemy_spawn"],
            "equipment_events": ["equipment.broken"],
            "ui_feedback": ["ui.menu_open", "ui.menu_close"],
        }

        # 이벤트가 속한 카테고리 찾기
        for category, events in event_categories.items():
            if event_name in events:
                return self.vibration_manager.event_enabled.get(category, True)

        # 매핑되지 않은 이벤트는 기본적으로 활성화
        return True

    def _handle_damage_dealt(self, data: Any) -> None:
        """피해 입힘 이벤트 처리"""
        if not data:
            return

        # 데이터에서 피해 양 추출 (예: {"damage": 50, "is_critical": True})
        damage = getattr(data, 'damage', 0)
        is_critical = getattr(data, 'is_critical', False)

        if is_critical:
            self.vibration_manager.vibrate(VibrationPattern.HEAVY_TAP)
        elif damage > 50:
            self.vibration_manager.vibrate(VibrationPattern.MEDIUM_TAP)
        else:
            self.vibration_manager.vibrate(VibrationPattern.LIGHT_TAP)

    def _handle_damage_taken(self, data: Any) -> None:
        """피해 입음 이벤트 처리"""
        if not data:
            return

        # 데이터에서 피해 양 추출
        damage = getattr(data, 'damage', 0)

        if damage > 100:
            self.vibration_manager.vibrate(VibrationPattern.DAMAGE_HEAVY)
        elif damage > 30:
            self.vibration_manager.vibrate(VibrationPattern.DAMAGE_MEDIUM)
        else:
            self.vibration_manager.vibrate(VibrationPattern.DAMAGE_LIGHT)

    def _handle_hp_change(self, data: Any) -> None:
        """HP 변경 이벤트 처리"""
        if not data:
            return

        # HP 증가/감소 판별
        change_amount = getattr(data, 'change', 0)

        if change_amount > 0:
            # 회복
            self.vibration_manager.vibrate(VibrationPattern.HEALING)
        # HP 감소는 damage_taken 이벤트로 처리됨

    def _handle_enemy_spawn(self, data: Any) -> None:
        """적 생성 이벤트 처리"""
        if not data:
            return

        # 보스 여부 확인
        is_boss = getattr(data, 'is_boss', False)

        if is_boss:
            self.vibration_manager.vibrate(VibrationPattern.BOSS_WARNING)
        else:
            self.vibration_manager.vibrate(VibrationPattern.LIGHT_TAP)


# 전역 인스턴스들
vibration_manager = VibrationManager()
vibration_listener = VibrationEventListener(vibration_manager)
