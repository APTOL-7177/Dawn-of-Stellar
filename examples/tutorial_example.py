"""
튜토리얼 시스템 사용 예제

이 예제는 튜토리얼 시스템을 메인 게임에 통합하는 방법을 보여줍니다.
"""

import tcod
import tcod.console
import tcod.context
import time

from src.tutorial.tutorial_manager import get_tutorial_manager
from src.tutorial.tutorial_ui import TutorialUI
from src.tutorial.tutorial_integration import show_tutorial_intro_with_story


def main():
    """튜토리얼 예제 메인 함수"""

    # TCOD 초기화
    screen_width = 120
    screen_height = 50

    tileset = tcod.tileset.load_tilesheet(
        "assets/fonts/dejavu10x10_gs_tc.png",
        32, 8,
        tcod.tileset.CHARMAP_TCOD
    )

    console = tcod.console.Console(screen_width, screen_height, order="F")

    with tcod.context.new(
        columns=console.width,
        rows=console.height,
        tileset=tileset,
        title="Dawn of Stellar - Tutorial Example",
        vsync=True,
    ) as context:

        # 튜토리얼 통합 시스템 초기화
        print("튜토리얼 시스템 로드 중...")
        integration = show_tutorial_intro_with_story(
            console,
            context,
            skip_intro_story=False  # 인트로 스토리 표시
        )

        if not integration.tutorial_manager.is_active:
            print("튜토리얼을 건너뛰었습니다.")
            return

        print("튜토리얼 시작!")

        # 메인 게임 루프
        running = True
        last_time = time.time()

        while running:
            current_time = time.time()
            delta_time = current_time - last_time
            last_time = current_time

            # 이벤트 처리
            for event in tcod.event.wait(timeout=0.016):
                if isinstance(event, tcod.event.Quit):
                    running = False

                # 튜토리얼 입력 처리
                if integration.handle_tutorial_input(event):
                    # 튜토리얼이 입력을 처리했으면 건너뜀
                    continue

                # 게임 입력 처리
                if isinstance(event, tcod.event.KeyDown):
                    if event.sym == tcod.event.KeySym.q:
                        running = False

            # 튜토리얼 업데이트
            integration.update_tutorial(delta_time)

            # 화면 렌더링
            console.clear()

            # 게임 화면 렌더링 (여기서는 간단한 텍스트만)
            console.print(
                2, 2,
                "Dawn of Stellar - 튜토리얼 예제",
                fg=(255, 215, 0)
            )

            if integration.tutorial_manager.current_step:
                console.print(
                    2, 4,
                    f"현재 단계: {integration.tutorial_manager.current_step.title}",
                    fg=(255, 255, 255)
                )

                console.print(
                    2, 5,
                    f"목표: {integration.tutorial_manager.current_step.objective}",
                    fg=(200, 200, 200)
                )

            # 튜토리얼 UI 렌더링
            integration.render_tutorial_ui()

            # 도움말
            console.print(
                2, screen_height - 2,
                "[Q] 종료  [ESC] 튜토리얼 건너뛰기",
                fg=(150, 150, 150)
            )

            # 화면 업데이트
            context.present(console)

            # 튜토리얼 완료 체크
            if not integration.tutorial_manager.is_active:
                print("튜토리얼 완료!")
                time.sleep(2)
                running = False

        print("예제 종료")


def quick_test():
    """빠른 테스트 - 콘솔에서 튜토리얼 로드 확인"""
    print("=" * 60)
    print("Dawn of Stellar - 튜토리얼 시스템 테스트")
    print("=" * 60)

    # 튜토리얼 매니저 생성
    manager = get_tutorial_manager()

    print(f"\n총 {len(manager.tutorials)}개 튜토리얼 로드됨:")
    for tutorial_id, tutorial in manager.tutorials.items():
        print(f"  • {tutorial.title} (ID: {tutorial_id})")

    print(f"\n튜토리얼 순서:")
    for i, tutorial_id in enumerate(manager.tutorial_order, 1):
        tutorial = manager.tutorials.get(tutorial_id)
        if tutorial:
            print(f"  {i}. {tutorial.title}")

    print("\n설정:")
    print(f"  • 튜토리얼 활성화: {manager.config.get('global', {}).get('enabled', False)}")
    print(f"  • 자동 시작: {manager.config.get('global', {}).get('auto_start', False)}")
    print(f"  • 전체 스킵 가능: {manager.config.get('global', {}).get('can_skip_all', False)}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    # 빠른 테스트 실행
    quick_test()

    # 풀 예제 실행 여부 묻기
    print("\n풀 예제를 실행하시겠습니까? (y/n): ", end="")
    try:
        response = input().lower()
        if response == 'y':
            main()
        else:
            print("예제를 종료합니다.")
    except KeyboardInterrupt:
        print("\n예제를 종료합니다.")
