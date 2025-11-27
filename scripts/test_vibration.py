#!/usr/bin/env python3
"""
진동 시스템 테스트 스크립트

진동 패턴을 테스트하고 설정을 확인할 수 있습니다.
"""

import sys
import time
from pathlib import Path

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pygame
from src.core.vibration_system import vibration_manager, VibrationPattern
from src.ui.input_handler import GamepadHandler


def test_vibration():
    """진동 시스템 테스트"""
    print("진동 시스템 테스트 시작...")

    try:
        # pygame 초기화
        pygame.init()
        pygame.joystick.init()

        # 게임패드 핸들러 생성
        gamepad_handler = GamepadHandler()
        vibration_manager.set_joystick(gamepad_handler.joystick)

        print(f"게임패드 연결 상태: {gamepad_handler.connected}")
        print(f"진동 시스템 활성화: {vibration_manager.enabled}")
        print(f"전체 진동 강도: {vibration_manager.global_intensity}")

        if not gamepad_handler.connected:
            print("게임패드가 연결되어 있지 않습니다.")
            print("게임패드를 연결한 후 다시 실행해주세요.")
            return

        # 사용 가능한 패턴 목록 출력
        print("\n사용 가능한 진동 패턴:")
        for pattern in VibrationPattern:
            print(f"  - {pattern.value}")

        print("\n진동 패턴 테스트를 시작합니다...")
        print("각 패턴은 1초 간격으로 실행됩니다.")
        print("Ctrl+C로 중단할 수 있습니다.")

        # 테스트 패턴들 (강도가 낮은 것부터 높은 순서로)
        test_patterns = [
            VibrationPattern.LIGHT_TAP,
            VibrationPattern.MEDIUM_TAP,
            VibrationPattern.HEAVY_TAP,
            VibrationPattern.SUCCESS,
            VibrationPattern.FAILURE,
            VibrationPattern.DAMAGE_LIGHT,
            VibrationPattern.DAMAGE_MEDIUM,
            VibrationPattern.DAMAGE_HEAVY,
            VibrationPattern.HEALING,
            VibrationPattern.LEVEL_UP,
            VibrationPattern.BOSS_WARNING,
            VibrationPattern.COMBAT_START,
            VibrationPattern.COMBAT_END,
            VibrationPattern.DEATH,
        ]

        try:
            for pattern in test_patterns:
                print(f"\n실행 중: {pattern.value}")
                vibration_manager.vibrate(pattern)
                time.sleep(1.5)  # 패턴 실행 시간 + 간격

        except KeyboardInterrupt:
            print("\n테스트 중단됨")

        print("\n테스트 완료!")

    except Exception as e:
        print(f"테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


def show_config():
    """현재 설정 표시"""
    print("현재 진동 설정:")
    print(f"  활성화: {vibration_manager.enabled}")
    print(f"  전체 강도: {vibration_manager.global_intensity}")
    print(f"  지속시간 배율: {vibration_manager.duration_multiplier}")
    print(f"  페이드 효과: {vibration_manager.enable_fade_effects}")
    print(f"  최대 동시 진동: {vibration_manager.max_concurrent_vibrations}")

    print("\n패턴 강도 설정:")
    for pattern_name, intensity in vibration_manager.pattern_intensities.items():
        print("12")

    print("\n이벤트 활성화 상태:")
    for event_name, enabled in vibration_manager.event_enabled.items():
        print(f"  {event_name}: {'✓' if enabled else '✗'}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--config":
        show_config()
    else:
        test_vibration()
