#!/usr/bin/env python3
"""
XInput 기반 게임패드 테스트 (Xbox 360 컨트롤러용)
pygame 대신 더 나은 Windows 호환성
"""

import sys
import time

print("🎮 XInput 게임패드 테스트 시작...")

try:
    # XInput 라이브러리 설치 확인
    try:
        import XInput
        print("✅ XInput 라이브러리 사용")
    except ImportError:
        print("❌ XInput 라이브러리가 설치되어 있지 않습니다.")
        print("설치 명령: pip install XInput-Python")
        print("\npygame으로 대체 테스트를 진행합니다...")

        # pygame으로 대체 테스트
        import pygame
        pygame.init()
        pygame.joystick.init()

        joystick_count = pygame.joystick.get_count()
        print(f"pygame으로 감지된 조이스틱 수: {joystick_count}")

        if joystick_count > 0:
            joystick = pygame.joystick.Joystick(0)
            joystick.init()
            print(f"컨트롤러: {joystick.get_name()}")
            print(f"버튼 수: {joystick.get_numbuttons()}")
            print(f"축 수: {joystick.get_numaxes()}")

            # 간단한 버튼 테스트
            print("\n버튼을 눌러보세요 (5초간)...")
            start_time = time.time()
            while time.time() - start_time < 5:
                pygame.event.pump()
                for i in range(min(10, joystick.get_numbuttons())):
                    if joystick.get_button(i):
                        print(f"버튼 {i} 감지됨!")
                time.sleep(0.1)
        else:
            print("❌ 연결된 게임패드가 없습니다.")
            print("\n문제 해결:")
            print("1. Xbox 360 컨트롤러를 USB로 연결")
            print("2. Windows 게임 컨트롤러 설정에서 테스트")
            print("3. Xbox Accessories 앱 설치")
            print("4. 컨트롤러 드라이버 업데이트")

        sys.exit(0)

    # XInput을 사용한 테스트
    print("\n🎯 Xbox 360 컨트롤러를 연결하고 버튼을 눌러보세요...")
    print("연결된 컨트롤러를 찾고 있습니다...")

    # 컨트롤러 연결 확인
    connected = XInput.get_connected()
    controller_ids = [i for i, state in enumerate(connected) if state]

    if not controller_ids:
        print("❌ Xbox 360 컨트롤러가 연결되어 있지 않습니다.")
        print("\n연결 방법:")
        print("1. Xbox 360 컨트롤러를 USB 케이블로 PC에 연결")
        print("2. 컨트롤러의 중앙 X 버튼을 눌러 전원 켜기")
        print("3. Windows에서 '게임 컨트롤러 설정' 실행")
        sys.exit(1)

    print(f"✅ 연결된 Xbox 컨트롤러: {len(controller_ids)}개")

    for controller_id in controller_ids:
        print(f"\n🎮 컨트롤러 {controller_id} 테스트 시작")
        print("각 버튼을 눌러보세요. 버튼 이름이 표시됩니다.")
        print("(중단하려면 Ctrl+C)")

        # 초기 상태 저장
        prev_state = XInput.get_state(controller_id)

        try:
            while True:
                # 현재 상태 가져오기
                state = XInput.get_state(controller_id)

                # 버튼 상태 비교
                buttons = [
                    ('DPAD_UP', state.Gamepad.wButtons & 0x0001),
                    ('DPAD_DOWN', state.Gamepad.wButtons & 0x0002),
                    ('DPAD_LEFT', state.Gamepad.wButtons & 0x0004),
                    ('DPAD_RIGHT', state.Gamepad.wButtons & 0x0008),
                    ('START', state.Gamepad.wButtons & 0x0010),
                    ('BACK', state.Gamepad.wButtons & 0x0020),
                    ('LEFT_THUMB', state.Gamepad.wButtons & 0x0040),
                    ('RIGHT_THUMB', state.Gamepad.wButtons & 0x0080),
                    ('LEFT_SHOULDER', state.Gamepad.wButtons & 0x0100),
                    ('RIGHT_SHOULDER', state.Gamepad.wButtons & 0x0200),
                    ('A', state.Gamepad.wButtons & 0x1000),
                    ('B', state.Gamepad.wButtons & 0x2000),
                    ('X', state.Gamepad.wButtons & 0x4000),
                    ('Y', state.Gamepad.wButtons & 0x8000),
                ]

                # 트리거 값
                left_trigger = state.Gamepad.bLeftTrigger / 255.0
                right_trigger = state.Gamepad.bRightTrigger / 255.0

                # 아날로그 스틱 값
                left_thumb_x = state.Gamepad.sThumbLX / 32767.0
                left_thumb_y = state.Gamepad.sThumbLY / 32767.0
                right_thumb_x = state.Gamepad.sThumbRX / 32767.0
                right_thumb_y = state.Gamepad.sThumbRY / 32767.0

                # 버튼 상태 출력 (눌렸을 때만)
                for button_name, pressed in buttons:
                    if pressed:
                        print(f"🎯 {button_name} 버튼 눌림")

                # 트리거 출력 (일정 값 이상일 때)
                if left_trigger > 0.1:
                    print(".2f"                if right_trigger > 0.1:
                    print(".2f"
                # 아날로그 스틱 출력 (일정 값 이상일 때)
                if abs(left_thumb_x) > 0.2 or abs(left_thumb_y) > 0.2:
                    print(".2f"                if abs(right_thumb_x) > 0.2 or abs(right_thumb_y) > 0.2:
                    print(".2f"
                time.sleep(0.05)  # 너무 빠른 출력 방지

        except KeyboardInterrupt:
            print(f"\n🛑 컨트롤러 {controller_id} 테스트 중단")

except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
