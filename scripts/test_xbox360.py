#!/usr/bin/env python3
"""
Xbox 360 컨트롤러 전용 테스트
"""

import sys
import time
from pathlib import Path

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

print("🎮 Xbox 360 컨트롤러 테스트 시작...")

try:
    import pygame

    # pygame 초기화
    pygame.init()
    pygame.joystick.init()

    joystick_count = pygame.joystick.get_count()
    print(f"연결된 조이스틱 수: {joystick_count}")

    if joystick_count == 0:
        print("❌ Xbox 360 컨트롤러가 연결되어 있지 않습니다.")
        print("\n해결 방법:")
        print("1. Xbox 360 컨트롤러를 USB로 연결하세요")
        print("2. Xbox Accessories 앱이 설치되어 있는지 확인하세요")
        print("3. Windows 게임 컨트롤러 설정에서 컨트롤러를 테스트해보세요")
        sys.exit(1)

    # 첫 번째 컨트롤러 가져오기
    joystick = pygame.joystick.Joystick(0)
    joystick.init()

    name = joystick.get_name().lower()
    if 'xbox' not in name and '360' not in name:
        print(f"⚠️ 연결된 컨트롤러가 Xbox 360이 아닐 수 있습니다: {joystick.get_name()}")
        print("계속 진행합니다...")

    print(f"🎯 컨트롤러: {joystick.get_name()}")
    print(f"   버튼 수: {joystick.get_numbuttons()}")
    print(f"   축 수: {joystick.get_numaxes()}")
    print(f"   햇 수: {joystick.get_numhats()}")

    print("\n=== Xbox 360 컨트롤러 버튼 매핑 정보 ===")
    print("일반적인 Xbox 360 컨트롤러 버튼 ID:")
    print("  0: A 버튼 (녹색)")
    print("  1: B 버튼 (빨간색)")
    print("  2: X 버튼 (파란색)")
    print("  3: Y 버튼 (노란색)")
    print("  4: LB (왼쪽 shoulder)")
    print("  5: RB (오른쪽 shoulder)")
    print("  6: Back 버튼")
    print("  7: Start 버튼")
    print("  8: Left Stick 버튼")
    print("  9: Right Stick 버튼")
    print("  축 0: Left Stick X (-1 왼쪽, +1 오른쪽)")
    print("  축 1: Left Stick Y (-1 위, +1 아래)")
    print("  축 2: Right Stick X (-1 왼쪽, +1 오른쪽)")
    print("  축 3: Right Stick Y (-1 위, +1 아래)")
    print("  축 4: LT 트리거 (0=떼어짐, 1=누름)")
    print("  축 5: RT 트리거 (0=떼어짐, 1=누름)")
    print("  햇 0: D-pad ((x,y) 형식: 왼쪽=-1, 오른쪽=+1, 위=-1, 아래=+1)")

    print("\n🎮 버튼을 눌러보세요... (10초 동안 테스트)")
    print("각 버튼의 ID가 표시됩니다.")

    # 초기 상태 저장
    prev_buttons = [joystick.get_button(i) for i in range(joystick.get_numbuttons())]
    prev_hats = [joystick.get_hat(i) for i in range(joystick.get_numhats())]

    start_time = time.time()
    while time.time() - start_time < 10:
        # pygame 이벤트 처리
        pygame.event.pump()

        # 버튼 상태 변화 확인
        for i in range(joystick.get_numbuttons()):
            current = joystick.get_button(i)
            if current != prev_buttons[i]:
                if current:
                    print(f"🎯 버튼 {i} 눌림")
                else:
                    print(f"🔵 버튼 {i} 뗌")
                prev_buttons[i] = current

        # D-pad 상태 변화 확인
        for i in range(joystick.get_numhats()):
            current = joystick.get_hat(i)
            if current != prev_hats[i]:
                print(f"🔄 D-pad {i}: {prev_hats[i]} -> {current}")
                prev_hats[i] = current

        # 축 값 표시 (변화가 있을 때만)
        for i in range(joystick.get_numaxes()):
            axis_value = joystick.get_axis(i)
            # 의미 있는 값만 표시 (약간의 데드존 적용)
            if abs(axis_value) > 0.1:
                axis_name = ["LeftX", "LeftY", "RightX", "RightY", "LT", "RT"][i] if i < 6 else f"Axis{i}"
                print(f"📊 {axis_name}: {axis_value:.2f}")

        time.sleep(0.05)  # 너무 빠른 출력 방지

    print("\n✅ 테스트 완료!")
    print("\n위의 버튼 ID를 참고해서 config/gamepad_mappings.yaml을 수정하세요.")

except ImportError:
    print("❌ pygame이 설치되어 있지 않습니다.")
    print("pip install pygame")
except Exception as e:
    print(f"❌ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
