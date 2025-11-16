"""
튜토리얼 뷰어 - 튜토리얼 내용을 단계별로 표시
"""

import tcod
import tcod.console
import tcod.event
import time

from src.tutorial.tutorial_manager import get_tutorial_manager
from src.tutorial.tutorial_ui import TutorialUI
from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.SYSTEM)


def run_tutorial_viewer(console: tcod.console.Console, context: tcod.context.Context) -> None:
    """
    튜토리얼 뷰어 실행

    각 튜토리얼 단계를 순서대로 보여줍니다.

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
    """
    tutorial_manager = get_tutorial_manager()
    tutorial_ui = TutorialUI(console)

    if not tutorial_manager.tutorial_order:
        logger.error("튜토리얼이 로드되지 않았습니다!")
        return

    current_tutorial_index = 0

    while current_tutorial_index < len(tutorial_manager.tutorial_order):
        tutorial_id = tutorial_manager.tutorial_order[current_tutorial_index]
        tutorial = tutorial_manager.tutorials.get(tutorial_id)

        if not tutorial:
            logger.warning(f"튜토리얼을 찾을 수 없습니다: {tutorial_id}")
            current_tutorial_index += 1
            continue

        # 화면 클리어
        console.clear()

        # 튜토리얼 제목
        title = f"[ {tutorial.title} ]"
        console.print(
            (console.width - len(title)) // 2,
            2,
            title,
            fg=(255, 215, 0)
        )

        # 진행률 표시
        progress = f"{current_tutorial_index + 1}/{len(tutorial_manager.tutorial_order)}"
        console.print(
            console.width - len(progress) - 2,
            2,
            progress,
            fg=(150, 150, 150)
        )

        # 구분선
        console.print(2, 4, "─" * (console.width - 4), fg=(100, 100, 100))

        # 튜토리얼 설명
        y = 6
        console.print(2, y, "설명:", fg=(255, 255, 0))
        y += 1

        # 설명을 여러 줄로 나누기
        description_lines = tutorial.description.split('\n')
        for line in description_lines:
            if line.strip():
                console.print(4, y, line.strip(), fg=(200, 200, 200))
                y += 1

        y += 1

        # 목표
        console.print(2, y, "목표:", fg=(0, 255, 255))
        y += 1
        console.print(4, y, tutorial.objective, fg=(255, 255, 255))
        y += 2

        # 주요 내용 (메시지들)
        console.print(2, y, "주요 내용:", fg=(0, 255, 0))
        y += 1

        for i, message in enumerate(tutorial.messages[:5], 1):  # 처음 5개만 표시
            # 메시지를 여러 줄로 나누기
            max_width = console.width - 8
            words = message.text.split()
            lines = []
            current_line = ""

            for word in words:
                if len(current_line) + len(word) + 1 <= max_width:
                    current_line += word + " "
                else:
                    if current_line:
                        lines.append(current_line.strip())
                    current_line = word + " "
            if current_line:
                lines.append(current_line.strip())

            for line in lines:
                if y < console.height - 8:
                    console.print(4, y, f"• {line}", fg=message.color)
                    y += 1

        if len(tutorial.messages) > 5:
            console.print(4, y, f"... 외 {len(tutorial.messages) - 5}개 메시지", fg=(150, 150, 150))
            y += 1

        # 힌트
        y = console.height - 6
        if tutorial.hints:
            console.print(2, y, "힌트:", fg=(255, 255, 0))
            y += 1
            for hint in tutorial.hints[:2]:  # 처음 2개만 표시
                console.print(4, y, f"💡 {hint.text}", fg=(200, 200, 100))
                y += 1

        # 보상
        y = console.height - 4
        rewards_text = []
        if tutorial.rewards.exp > 0:
            rewards_text.append(f"경험치 +{tutorial.rewards.exp}")
        if tutorial.rewards.gold > 0:
            rewards_text.append(f"골드 +{tutorial.rewards.gold}")

        if rewards_text:
            console.print(2, y, f"보상: {' | '.join(rewards_text)}", fg=(255, 215, 0))

        # 컨트롤 안내
        y = console.height - 2
        console.print(2, y, "[→] 다음  [←] 이전  [ESC] 메인 메뉴로", fg=(150, 150, 150))

        # 화면 업데이트
        context.present(console)

        # 입력 대기
        waiting = True
        while waiting:
            for event in tcod.event.wait():
                if isinstance(event, tcod.event.Quit):
                    return
                elif isinstance(event, tcod.event.KeyDown):
                    if event.sym == tcod.event.KeySym.ESCAPE:
                        # 메인 메뉴로
                        return
                    elif event.sym == tcod.event.KeySym.RIGHT or event.sym == tcod.event.KeySym.RETURN:
                        # 다음 튜토리얼
                        current_tutorial_index += 1
                        waiting = False
                    elif event.sym == tcod.event.KeySym.LEFT:
                        # 이전 튜토리얼
                        if current_tutorial_index > 0:
                            current_tutorial_index -= 1
                        waiting = False

    # 모든 튜토리얼 완료
    console.clear()

    completion_msg = "✓ 모든 튜토리얼을 확인했습니다!"
    console.print(
        (console.width - len(completion_msg)) // 2,
        console.height // 2 - 2,
        completion_msg,
        fg=(0, 255, 0)
    )

    msg2 = "게임을 시작할 준비가 되었습니다."
    console.print(
        (console.width - len(msg2)) // 2,
        console.height // 2,
        msg2,
        fg=(255, 255, 255)
    )

    msg3 = "Press any key to continue..."
    console.print(
        (console.width - len(msg3)) // 2,
        console.height // 2 + 2,
        msg3,
        fg=(200, 200, 200)
    )

    context.present(console)

    # 아무 키나 누를 때까지 대기
    for event in tcod.event.wait():
        if isinstance(event, (tcod.event.KeyDown, tcod.event.Quit)):
            break

    logger.info("튜토리얼 뷰어 종료")
