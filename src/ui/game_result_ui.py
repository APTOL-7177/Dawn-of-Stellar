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
from typing import Optional, Any

from src.ui.input_handler import InputHandler, GameAction, unified_input_handler
from src.ui.tcod_display import render_space_background
from src.core.logger import get_logger, Loggers
from src.persistence.meta_progress import get_meta_progress, save_meta_progress
from src.audio import play_sfx


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
        save_slot: Optional[Any] = None
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
        render_space_background(console, self.screen_width, self.screen_height)

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
        if action == GameAction.CONFIRM or action == GameAction.ESCAPE or action == GameAction.MENU:
            if action != GameAction.CONFIRM:  # CONFIRM은 확인이므로 다른 효과음
                play_sfx("ui", "cursor_cancel")
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

        # 세이브 파일 삭제 (게임 타입에 따라)
        from src.persistence.save_system import SaveSystem
        save_system = SaveSystem()
        
        # save_slot에서 게임 타입 정보 추출
        is_multiplayer = False
        if isinstance(self.save_slot, dict):
            # 딕셔너리인 경우 (게임 상태에서 전달된 경우)
            is_multiplayer = self.save_slot.get("is_multiplayer", False)
        elif isinstance(self.save_slot, str):
            # 문자열인 경우 "save_multiplayer"인지 확인
            is_multiplayer = "multiplayer" in self.save_slot.lower()
        
        # SaveSystem의 delete_save_by_type 사용
        save_system.delete_save_by_type(is_multiplayer)
        save_system.delete_save_by_type(is_multiplayer)


def show_game_result(
    console: tcod.console.Console,
    context: tcod.context.Context,
    is_victory: bool,
    max_floor: int,
    enemies_defeated: int,
    total_gold: int = 0,
    total_exp: int = 0,
    save_slot: Optional[Any] = None,
    is_multiplayer: bool = False,
    inventory: Optional[Any] = None
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
        save_slot: 세이브 슬롯 정보 (딕셔너리 또는 문자열, None 가능)
        is_multiplayer: 멀티플레이어 여부
        inventory: 인벤토리 (게임 오버 시 재료 저장용)
    """
    # save_slot이 딕셔너리가 아니면 딕셔너리로 변환
    if save_slot is not None and not isinstance(save_slot, dict):
        save_slot = {"is_multiplayer": is_multiplayer}
    elif save_slot is None:
        save_slot = {"is_multiplayer": is_multiplayer}
    else:
        # 딕셔너리인 경우 is_multiplayer 추가
        save_slot["is_multiplayer"] = save_slot.get("is_multiplayer", is_multiplayer)
    
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


    logger.info("게임 정산 화면 표시")

    # 게임 오버 시 재료 아이템 저장소로 이동 및 재료가 아닌 아이템 제거
    if not is_victory:
        from src.town.town_manager import get_town_manager
        town_mgr = get_town_manager()
        
        if town_mgr and inventory:
            try:
                # 1. 인벤토리의 재료를 허브 저장소로 이동
                stored = town_mgr.store_all_materials_from_inventory(inventory)
                if stored:
                    logger.info(f"게임 오버: {len(stored)}종류의 재료 아이템을 허브 저장소로 이동")
                
                # 2. 허브 저장소에서 재료가 아닌 아이템(요리, 장비, 소모품 등) 제거
                town_mgr.clear_runtime_storage()
            except Exception as e:
                logger.error(f"게임 오버 저장 처리 실패: {e}", exc_info=True)

    # 정산 완료 처리
    ui.finalize()

    # 게임 오버 BGM 재생
    try:
        from src.audio import play_bgm
        play_bgm("game_over")
        logger.info("게임 오버 BGM 재생")
    except Exception as e:
        # 오디오 시스템 없으면 무시
        logger.debug(f"게임 오버 BGM 재생 실패 (오디오 시스템 없음): {e}")

    # 결과 화면 표시
    while True:
        ui.render(console)
        context.present(console)

        for event in tcod.event.wait():
            action = unified_input_handler.process_tcod_event(event)

            if action:
                if ui.handle_input(action):
                    logger.info("게임 정산 종료")
                    return

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return
