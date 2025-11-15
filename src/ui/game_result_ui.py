"""
게임 정산 UI

게임 오버/클리어 시 보여지는 정산 화면
별의 파편 지급 및 세이브 파일 삭제
"""

import tcod
import tcod.console
import tcod.event
import os
from pathlib import Path
from typing import Optional

from src.ui.input_handler import InputHandler, GameAction
from src.core.logger import get_logger, Loggers
from src.persistence.meta_progress import get_meta_progress, save_meta_progress


logger = get_logger(Loggers.UI)


class GameResultUI:
    """게임 정산 UI"""

    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        is_victory: bool,
        max_floor: int,
        enemies_defeated: int,
        total_gold: int,
        total_exp: int,
        save_slot: Optional[int] = None
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.is_victory = is_victory
        self.max_floor = max_floor
        self.enemies_defeated = enemies_defeated
        self.total_gold = total_gold
        self.total_exp = total_exp
        self.save_slot = save_slot

        # 별의 파편 계산
        self.star_fragments = self._calculate_star_fragments()

    def _calculate_star_fragments(self) -> int:
        """별의 파편 계산 (20배 증가)"""
        fragments = 0

        # 층수 보너스 (층당 20, 기존 1에서 20배)
        fragments += self.max_floor * 20

        # 적 처치 보너스 (1마리당 2, 기존 10마리당 1에서 20배)
        fragments += self.enemies_defeated * 2

        # 승리 보너스 (1000, 기존 50에서 20배)
        if self.is_victory:
            fragments += 1000  # 게임 클리어 시 보너스

        # 층수 마일스톤 보너스 (20배)
        if self.max_floor >= 10:
            fragments += 200  # 기존 10
        if self.max_floor >= 20:
            fragments += 400  # 기존 20
        if self.max_floor >= 30:
            fragments += 600  # 기존 30

        return fragments

    def render(self, console: tcod.console.Console):
        """정산 화면 렌더링"""
        console.clear()

        # 제목
        if self.is_victory:
            title = "=== 게임 클리어! ==="
            title_color = (100, 255, 100)
        else:
            title = "=== 게임 오버 ==="
            title_color = (255, 100, 100)

        console.print(
            (self.screen_width - len(title)) // 2,
            5,
            title,
            fg=title_color
        )

        # 통계
        stats_y = 10
        stats = [
            f"도달 층수: {self.max_floor}층",
            f"처치한 적: {self.enemies_defeated}마리",
            f"획득 골드: {self.total_gold} G",
            f"획득 경험치: {self.total_exp} EXP",
        ]

        for i, stat in enumerate(stats):
            console.print(
                (self.screen_width - len(stat)) // 2,
                stats_y + i * 2,
                stat,
                fg=(200, 200, 200)
            )

        # 별의 파편
        fragments_y = stats_y + len(stats) * 2 + 3
        fragments_title = "=== 별의 파편 획득 ==="
        console.print(
            (self.screen_width - len(fragments_title)) // 2,
            fragments_y,
            fragments_title,
            fg=(150, 200, 255)
        )

        # 별의 파편 계산 상세
        breakdown_y = fragments_y + 2
        breakdown = []

        breakdown.append(f"층수 보너스: {self.max_floor * 20} ★")
        breakdown.append(f"처치 보너스: {self.enemies_defeated * 2} ★")

        if self.is_victory:
            breakdown.append(f"클리어 보너스: 1000 ★")

        # 마일스톤 보너스
        milestone_bonus = 0
        if self.max_floor >= 10:
            milestone_bonus += 200  # 20배
        if self.max_floor >= 20:
            milestone_bonus += 400  # 20배
        if self.max_floor >= 30:
            milestone_bonus += 600  # 20배

        if milestone_bonus > 0:
            breakdown.append(f"마일스톤 보너스: {milestone_bonus} ★")

        for i, line in enumerate(breakdown):
            console.print(
                (self.screen_width - len(line)) // 2,
                breakdown_y + i * 2,
                line,
                fg=(180, 180, 180)
            )

        # 총 획득
        total_y = breakdown_y + len(breakdown) * 2 + 2
        total_line = f"총 획득: {self.star_fragments} ★"
        console.print(
            (self.screen_width - len(total_line)) // 2,
            total_y,
            total_line,
            fg=(255, 215, 0)
        )

        # 안내 메시지
        message_y = self.screen_height - 8
        messages = [
            "별의 파편이 메타 진행에 추가되었습니다.",
            "세이브 파일이 삭제됩니다.",
            "",
            "메인 메뉴로 돌아가려면 Enter를 누르세요."
        ]

        for i, msg in enumerate(messages):
            console.print(
                (self.screen_width - len(msg)) // 2,
                message_y + i,
                msg,
                fg=(150, 150, 150)
            )

    def handle_input(self, action: GameAction) -> bool:
        """
        입력 처리

        Returns:
            True: 종료, False: 계속
        """
        if action == GameAction.CONFIRM or action == GameAction.ESCAPE:
            return True
        return False

    def finalize(self):
        """
        정산 완료 처리

        - 별의 파편 지급
        - 세이브 파일 삭제
        """
        # 별의 파편 지급
        meta = get_meta_progress()
        meta.add_star_fragments(self.star_fragments)
        save_meta_progress()

        logger.info(f"별의 파편 {self.star_fragments} 지급 (총: {meta.star_fragments})")

        # 세이브 파일 삭제
        if self.save_slot is not None:
            save_file = Path(f"saves/save_slot_{self.save_slot}.json")
            if save_file.exists():
                try:
                    os.remove(save_file)
                    logger.info(f"세이브 파일 삭제: {save_file}")
                except Exception as e:
                    logger.error(f"세이브 파일 삭제 실패: {e}")
        else:
            # 슬롯 번호가 없으면 모든 임시 세이브 파일 삭제
            saves_dir = Path("saves")
            if saves_dir.exists():
                for save_file in saves_dir.glob("save_slot_*.json"):
                    try:
                        os.remove(save_file)
                        logger.info(f"세이브 파일 삭제: {save_file}")
                    except Exception as e:
                        logger.error(f"세이브 파일 삭제 실패: {e}")


def show_game_result(
    console: tcod.console.Console,
    context: tcod.context.Context,
    is_victory: bool,
    max_floor: int,
    enemies_defeated: int,
    total_gold: int = 0,
    total_exp: int = 0,
    save_slot: Optional[int] = None
):
    """
    게임 정산 화면 표시

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        is_victory: 승리 여부
        max_floor: 최대 도달 층수
        enemies_defeated: 처치한 적 수
        total_gold: 총 골드
        total_exp: 총 경험치
        save_slot: 세이브 슬롯 번호 (None이면 모든 임시 파일 삭제)
    """
    ui = GameResultUI(
        console.width,
        console.height,
        is_victory,
        max_floor,
        enemies_defeated,
        total_gold,
        total_exp,
        save_slot
    )

    handler = InputHandler()

    logger.info("게임 정산 화면 표시")

    # 정산 완료 처리
    ui.finalize()

    # BGM 정지
    try:
        from src.audio import stop_bgm
        stop_bgm()
    except Exception as e:
        # 오디오 시스템 없으면 무시
        logger.debug(f"BGM 정지 실패 (오디오 시스템 없음): {e}")

    # 결과 화면 표시
    while True:
        ui.render(console)
        context.present(console)

        for event in tcod.event.wait():
            action = handler.dispatch(event)

            if action:
                if ui.handle_input(action):
                    logger.info("게임 정산 종료")
                    return

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return
