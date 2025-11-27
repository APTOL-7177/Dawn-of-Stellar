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
    print("게임패드 테스트 시작...")

    try:
        # pygame 초기화
        print("pygame 초기화 중...")
        pygame.init()
        pygame.joystick.init()
        print("pygame 초기화 완료")

        # 게임패드 핸들러 생성
        print("게임패드 핸들러 생성 중...")
        handler = GamepadHandler()
        print("게임패드 핸들러 생성 완료")

        print(f"pygame.joystick.get_count(): {pygame.joystick.get_count()}")
        print(f"게임패드 연결 상태: {handler.connected}")

        if not handler.connected:
            print("게임패드가 연결되어 있지 않습니다.")
            print("게임패드를 연결하고 다시 실행해주세요.")
            print("\n연결 가능한 조이스틱 목록:")
            for i in range(pygame.joystick.get_count()):
                try:
                    joy = pygame.joystick.Joystick(i)
                    print(f"  {i}: {joy.get_name()}")
                except Exception as e:
                    print(f"  {i}: 연결 실패 - {e}")
            return

    except Exception as e:
        print(f"초기화 중 오류 발생: {e}")
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

    print("\n현재 버튼 매핑:")
    for button_id, action in handler.button_mappings.items():
        print(f"  버튼 {button_id}: {action.value}")

    print("\n테스트 시작... 버튼을 눌러보세요 (10초간)")
    print("Ctrl+C로 중단")

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

    print("테스트 완료")


if __name__ == "__main__":
    test_gamepad()
