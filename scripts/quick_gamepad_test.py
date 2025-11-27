#!/usr/bin/env python3
"""
빠른 게임패드 입력 테스트
"""

import sys
import pygame
from pathlib import Path

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

print("Quick gamepad test starting...")

try:
    # pygame 초기화
    pygame.init()
    pygame.joystick.init()

    joystick_count = pygame.joystick.get_count()
    print(f"Connected joysticks: {joystick_count}")

    if joystick_count == 0:
        print("No gamepad connected.")
        print("Please connect a gamepad and try again.")
        sys.exit(1)

    # 첫 번째 게임패드 가져오기
    joystick = pygame.joystick.Joystick(0)
    joystick.init()

    print(f"Testing gamepad: {joystick.get_name()}")
    print(f"   Buttons: {joystick.get_numbuttons()}")
    print(f"   Axes: {joystick.get_numaxes()}")
    print(f"   Hats: {joystick.get_numhats()}")

    print("\nPress buttons... (10 second test)")
    print("Press Ctrl+C to exit.")

    import time
    start_time = time.time()

    last_button_states = [False] * joystick.get_numbuttons()
    last_hat_states = [(0, 0)] * joystick.get_numhats()

    while time.time() - start_time < 10:
        # pygame 이벤트 처리 및 출력
        events = pygame.event.get()
        if events:
            print(f"Events detected: {len(events)}")
            for event in events:
                if event.type == pygame.JOYBUTTONDOWN:
                    print(f"JOYBUTTONDOWN: button {event.button}")
                elif event.type == pygame.JOYBUTTONUP:
                    print(f"JOYBUTTONUP: button {event.button}")
                elif event.type == pygame.JOYHATMOTION:
                    print(f"JOYHATMOTION: hat {event.hat}, value {event.value}")
                elif event.type == pygame.JOYAXISMOTION:
                    print(f"JOYAXISMOTION: axis {event.axis}, value {event.value:.2f}")
                else:
                    print(f"Other event: {event.type}")

        # pygame 이벤트 큐 업데이트 (중요!)
        pygame.event.pump()

        # 버튼 상태 변화 확인 (폴링 방식)
        for i in range(joystick.get_numbuttons()):
            current_state = joystick.get_button(i)
            if current_state != last_button_states[i]:
                if current_state:
                    print(f"Button {i} pressed (polling)")
                else:
                    print(f"Button {i} released (polling)")
                last_button_states[i] = current_state

        # D-pad 상태 변화 확인 (폴링 방식)
        for i in range(joystick.get_numhats()):
            current_hat = joystick.get_hat(i)
            if current_hat != last_hat_states[i]:
                print(f"D-pad {i} changed: {last_hat_states[i]} -> {current_hat} (polling)")
                last_hat_states[i] = current_hat

        # 잠시 대기
        time.sleep(0.05)  # 더 빠른 응답을 위해 0.05초로 줄임

    print("\nTest completed!")

except KeyboardInterrupt:
    print("\nTest interrupted")

except Exception as e:
    print(f"Error occurred: {e}")
    import traceback
    traceback.print_exc()
