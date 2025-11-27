#!/usr/bin/env python3
"""
게임패드 연결 상태 확인 스크립트
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def check_gamepad():
    """게임패드 상태 확인"""
    results = []

    try:
        results.append("=== 게임패드 연결 상태 확인 ===")

        # Python 버전
        results.append(f"Python 버전: {sys.version}")

        # pygame 임포트 시도
        try:
            import pygame
            results.append(f"✓ pygame 임포트 성공 (버전: {pygame.version.ver})")

            # pygame 초기화
            pygame.init()
            results.append("✓ pygame.init() 성공")

            pygame.joystick.init()
            results.append("✓ pygame.joystick.init() 성공")

            # 조이스틱 수 확인
            joystick_count = pygame.joystick.get_count()
            results.append(f"연결된 조이스틱 수: {joystick_count}")

            if joystick_count > 0:
                results.append("\n--- 게임패드 상세 정보 ---")
                for i in range(joystick_count):
                    try:
                        joy = pygame.joystick.Joystick(i)
                        joy.init()
                        results.append(f"조이스틱 {i}:")
                        results.append(f"  이름: {joy.get_name()}")
                        results.append(f"  버튼 수: {joy.get_numbuttons()}")
                        results.append(f"  축 수: {joy.get_numaxes()}")
                        results.append(f"  햇 수: {joy.get_numhats()}")
                    except Exception as e:
                        results.append(f"조이스틱 {i}: 초기화 실패 - {e}")
            else:
                results.append("\n❌ 연결된 게임패드가 없습니다.")
                results.append("\n문제 해결 팁:")
                results.append("1. 게임패드가 PC에 제대로 연결되어 있는지 확인")
                results.append("2. 게임패드 배터리가 충분한지 확인")
                results.append("3. USB 포트를 바꿔서 연결해보기")
                results.append("4. Windows 게임 컨트롤러 설정에서 게임패드 확인")

        except ImportError as e:
            results.append(f"❌ pygame 임포트 실패: {e}")
            results.append("해결: pip install pygame")
        except Exception as e:
            results.append(f"❌ pygame 초기화 실패: {e}")

    except Exception as e:
        results.append(f"❌ 스크립트 실행 오류: {e}")

    # 결과 파일에 저장
    result_file = PROJECT_ROOT / "gamepad_check_result.txt"
    try:
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(results))
        results.append(f"\n✓ 결과가 파일에 저장됨: {result_file}")
    except Exception as e:
        results.append(f"\n❌ 결과 파일 저장 실패: {e}")

    # 콘솔에도 출력
    print('\n'.join(results))

if __name__ == "__main__":
    check_gamepad()
