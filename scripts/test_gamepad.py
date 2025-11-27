#!/usr/bin/env python3
"""
게임패드 연결 및 입력 테스트 스크립트

게임패드가 제대로 연결되고 입력이 처리되는지 확인
"""

import sys
import time
from pathlib import Path

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pygame
from src.ui.input_handler import GamepadHandler, GameAction


def test_gamepad():
    """게임패드 연결 및 입력 테스트"""
    print("=== 게임패드 테스트 시작 ===")

    try:
        print("1. pygame 초기화 시도...")
        # pygame 초기화
        pygame.init()
        print("   ✓ pygame.init() 성공")

        pygame.joystick.init()
        print("   ✓ pygame.joystick.init() 성공")

        joystick_count = pygame.joystick.get_count()
        print(f"   연결된 조이스틱 수: {joystick_count}")

        if joystick_count == 0:
            print("No gamepad connected.")
            print("\nTroubleshooting:")
            print("1. Check if gamepad is properly connected to PC")
            print("2. Check if gamepad drivers are installed")
            print("3. Test USB port with another device")
            print("4. For Bluetooth gamepads, check pairing status")
            return

        print("\n2. Gamepad information:")
        for i in range(joystick_count):
            try:
                joy = pygame.joystick.Joystick(i)
                joy.init()
                print(f"   Joystick {i}: {joy.get_name()}")
                print(f"     - Buttons: {joy.get_numbuttons()}")
                print(f"     - Axes: {joy.get_numaxes()}")
                print(f"     - Hats: {joy.get_numhats()}")
            except Exception as e:
                print(f"   Joystick {i}: initialization failed - {e}")

        print("\n3. 게임패드 핸들러 생성...")
        # 게임패드 핸들러 생성
        handler = GamepadHandler()
        print("   게임패드 핸들러 생성 완료")

        print(f"   게임패드 연결 상태: {handler.connected}")
        if hasattr(handler, 'current_layout'):
            print(f"   감지된 레이아웃: {handler.current_layout.value}")

        if not handler.connected:
            print("❌ 게임패드 핸들러 연결 실패")
            return

    except ImportError as e:
        print(f"❌ pygame 임포트 실패: {e}")
        print("pygame이 설치되어 있는지 확인해주세요.")
        print("설치: pip install pygame")
        return
    except Exception as e:
        print(f"❌ 초기화 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n게임패드 정보:")
    joystick = handler.joystick
    if joystick:
        print(f"  이름: {joystick.get_name()}")
        print(f"  버튼 수: {joystick.get_numbuttons()}")
        print(f"  축 수: {joystick.get_numaxes()}")
        print(f"  햇 수: {joystick.get_numhats()}")

    print("\nCurrent button mapping:")
    for button_id, action in handler.button_mappings.items():
        print(f"  Button {button_id}: {action.value}")

    print("\nTest starting... Press buttons (10 seconds)")
    print("Ctrl+C to stop")

    try:
        start_time = time.time()
        while time.time() - start_time < 10:
            # 게임패드 업데이트
            handler.update()

            # 액션 확인
            action = handler.get_action()
            if action:
                print(f"감지된 액션: {action.value}")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n테스트 중단")

    print("Test completed")


if __name__ == "__main__":
    test_gamepad()
