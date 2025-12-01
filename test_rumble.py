"""진동 테스트"""
import pygame
import time

pygame.init()
pygame.joystick.init()

if pygame.joystick.get_count() > 0:
    j = pygame.joystick.Joystick(0)
    j.init()
    print(f"Joystick: {j.get_name()}")
    print(f"Has rumble: {hasattr(j, 'rumble')}")
    
    # 진동 테스트
    print("진동 테스트 시작...")
    result = j.rumble(0.5, 0.5, 500)
    print(f"Rumble result: {result}")
    time.sleep(1)
    print("진동 테스트 완료")
else:
    print("게임패드 없음")

pygame.quit()
