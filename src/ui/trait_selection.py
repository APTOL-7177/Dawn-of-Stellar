"""
Trait Selection - 특성 선택 시스템

각 캐릭터마다 5개 특성 중 2개를 선택하는 시스템
기본 2개 해금, 나머지 3개는 상점에서 구매 필요
"""

import tcod.console
import tcod.event
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import yaml
from pathlib import Path

from src.ui.cursor_menu import CursorMenu, MenuItem
from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, InputHandler
from src.core.logger import get_logger
from src.core.config import get_config
from src.persistence.meta_progress import get_meta_progress


@dataclass
class Trait:
    """특성 정보"""
    id: str
    name: str
    description: str
    type: str  # passive, trigger, conditional


@dataclass
class CharacterTraits:
    """캐릭터의 선택된 특성"""
    character_name: str
    job_name: str
    selected_traits: List[Trait]


class TraitSelection:
    """
    특성 선택 시스템

    각 캐릭터마다 5개 특성 중 2개를 선택
    """

    def __init__(
        self,
        party_members: List[Any],
        screen_width: int = 80,
        screen_height: int = 50
    ):
        """
        Args:
            party_members: 파티 멤버 리스트 (PartyMember)
            screen_width: 화면 너비
            screen_height: 화면 높이
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.logger = get_logger("trait_selection")

        self.party_members = party_members
        self.current_member_index = 0
        self.selected_traits: List[CharacterTraits] = []

        # 현재 멤버의 특성 목록
        self.available_traits: List[Trait] = []
        self.selected_count = 0  # 현재 멤버가 선택한 특성 수 (최대 2)
        self.temp_selected: List[Trait] = []  # 임시 선택

        # 상태
        self.completed = False
        self.cancelled = False

        # 메뉴
        self.trait_menu: Optional[CursorMenu] = None

        # 첫 번째 멤버의 특성 로드
        self._load_traits_for_current_member()
        self._create_trait_menu()

    def _load_traits_for_current_member(self):
        """현재 멤버의 특성 로드"""
        member = self.party_members[self.current_member_index]
        job_id = member.job_id

        # YAML 파일에서 특성 로드
        yaml_path = Path(f"data/characters/{job_id}.yaml")

        if not yaml_path.exists():
            self.logger.error(f"직업 YAML 파일 없음: {yaml_path}")
            self.available_traits = []
            return

        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                traits_data = data.get('traits', [])

                self.available_traits = []
                meta = get_meta_progress()

                for trait_data in traits_data[:5]:  # 최대 5개
                    trait = Trait(
                        id=trait_data.get('id', ''),
                        name=trait_data.get('name', ''),
                        description=trait_data.get('description', ''),
                        type=trait_data.get('type', 'passive')
                    )

                    # 해금 여부 확인 및 추가
                    # (메타 진행에서 해금 여부를 확인하되, 여기선 모든 특성 로드)
                    self.available_traits.append(trait)

                self.logger.info(
                    f"{member.job_name} 특성 {len(self.available_traits)}개 로드"
                )

        except Exception as e:
            self.logger.error(f"특성 로드 실패: {e}")
            self.available_traits = []

    def _create_trait_menu(self):
        """특성 선택 메뉴 생성"""
        member = self.party_members[self.current_member_index]
        job_id = member.job_id
        meta = get_meta_progress()

        # 개발 모드 확인
        config = get_config()
        dev_mode = config.get("development.unlock_all_classes", False)

        menu_items = []

        for trait in self.available_traits:
            # 해금 여부 확인 (개발 모드이면 모두 해금)
            is_unlocked = dev_mode or meta.is_trait_unlocked(job_id, trait.id)

            # 이미 선택된 특성 표시
            already_selected = trait in self.temp_selected

            # 특성 타입 표시
            type_str = {
                'passive': '패시브',
                'trigger': '발동',
                'conditional': '조건부'
            }.get(trait.type, '기타')

            # 잠금/해금/선택 상태 표시
            if not is_unlocked:
                prefix = "[🔒] "
                description = trait.description + " (상점에서 해금 필요)"
                enabled = False
            elif already_selected:
                prefix = "[✓] "
                description = trait.description
                enabled = True
            else:
                prefix = ""
                description = trait.description
                enabled = True

            menu_items.append(MenuItem(
                text=f"{prefix}{trait.name} ({type_str})",
                value=trait,
                enabled=enabled,
                description=description
            ))

        # 메뉴 생성
        menu_x = 5
        menu_y = 10
        menu_width = 55

        title = f"{member.name} ({member.job_name}) - 특성 선택 ({self.selected_count}/2)"

        self.trait_menu = CursorMenu(
            title=title,
            items=menu_items,
            x=menu_x,
            y=menu_y,
            width=menu_width,
            show_description=True
        )

    def handle_input(self, action: GameAction) -> bool:
        """
        입력 처리

        Args:
            action: 게임 액션

        Returns:
            특성 선택이 완료되었으면 True
        """
        if action == GameAction.MOVE_UP:
            self.trait_menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            self.trait_menu.move_cursor_down()
        elif action == GameAction.CONFIRM:
            # 특성 선택/해제
            selected = self.trait_menu.get_selected_item()
            if selected and selected.enabled:  # enabled 확인
                trait = selected.value
                member = self.party_members[self.current_member_index]
                job_id = member.job_id
                meta = get_meta_progress()

                # 개발 모드 확인
                config = get_config()
                dev_mode = config.get("development.unlock_all_classes", False)

                # 해금 여부 재확인 (개발 모드이면 통과)
                if not dev_mode and not meta.is_trait_unlocked(job_id, trait.id):
                    self.logger.warning(f"잠긴 특성 선택 시도: {trait.name}")
                    return False

                if trait in self.temp_selected:
                    # 선택 해제
                    self.temp_selected.remove(trait)
                    self.selected_count -= 1
                    self.logger.info(f"특성 선택 해제: {trait.name}")
                elif self.selected_count < 2:
                    # 선택
                    self.temp_selected.append(trait)
                    self.selected_count += 1
                    self.logger.info(f"특성 선택: {trait.name}")

                    # 2개 선택 완료
                    if self.selected_count == 2:
                        self._confirm_traits()
                        return self.completed

                # 메뉴 갱신
                self._create_trait_menu()

        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            if self.selected_count > 0:
                # 선택 초기화
                self.temp_selected.clear()
                self.selected_count = 0
                self._create_trait_menu()
            elif self.current_member_index > 0:
                # 이전 멤버로
                self.current_member_index -= 1
                self.selected_traits.pop()
                self.temp_selected.clear()
                self.selected_count = 0
                self._load_traits_for_current_member()
                self._create_trait_menu()
            else:
                # 특성 선택 취소
                self.cancelled = True
                return True

        return False

    def _confirm_traits(self):
        """현재 멤버의 특성 확정"""
        member = self.party_members[self.current_member_index]

        char_traits = CharacterTraits(
            character_name=member.name,
            job_name=member.job_name,
            selected_traits=self.temp_selected.copy()
        )

        self.selected_traits.append(char_traits)
        self.logger.info(
            f"{member.name} 특성 확정: "
            f"{[t.name for t in self.temp_selected]}"
        )

        # 다음 멤버로
        self.current_member_index += 1

        if self.current_member_index >= len(self.party_members):
            # 모든 멤버 완료
            self.completed = True
        else:
            # 다음 멤버 준비
            self.temp_selected.clear()
            self.selected_count = 0
            self._load_traits_for_current_member()
            self._create_trait_menu()

    def render(self, console: tcod.console.Console):
        """특성 선택 화면 렌더링"""
        console.clear()

        # 제목
        title = "특성 선택"
        console.print(
            (self.screen_width - len(title)) // 2,
            2,
            title,
            fg=Colors.UI_TEXT_SELECTED
        )

        # 진행 상황
        progress = f"파티 멤버 {self.current_member_index + 1}/4"
        console.print(
            (self.screen_width - len(progress)) // 2,
            4,
            progress,
            fg=Colors.GRAY
        )

        # 특성 메뉴
        if self.trait_menu:
            self.trait_menu.render(console)

        # 우측 패널: 완료된 멤버들
        self._render_completed_members(console)

        # 안내 메시지
        help_y = self.screen_height - 4

        if self.selected_count < 2:
            help_msg = f"특성을 {2 - self.selected_count}개 더 선택하세요"
            console.print(
                (self.screen_width - len(help_msg)) // 2,
                help_y,
                help_msg,
                fg=Colors.UI_TEXT
            )

        # 조작 안내
        controls = "↑↓: 이동  Z: 선택/해제  X: 이전/취소"
        console.print(
            2,
            self.screen_height - 2,
            controls,
            fg=Colors.GRAY
        )

    def _render_completed_members(self, console: tcod.console.Console):
        """완료된 멤버 목록 표시"""
        panel_x = self.screen_width - 22
        panel_y = 10

        # 테두리
        console.draw_frame(
            panel_x - 2,
            panel_y - 2,
            24,
            20,
            "선택 완료",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )

        y = panel_y
        for i, char_traits in enumerate(self.selected_traits):
            console.print(
                panel_x,
                y,
                f"{i + 1}. {char_traits.character_name}",
                fg=Colors.UI_TEXT_SELECTED
            )
            y += 1

            for trait in char_traits.selected_traits:
                console.print(
                    panel_x + 2,
                    y,
                    f"• {trait.name}",
                    fg=Colors.GRAY
                )
                y += 1

            y += 1  # 여백

    def get_results(self) -> Optional[List[CharacterTraits]]:
        """선택 완료된 특성 반환"""
        if self.completed:
            return self.selected_traits
        return None


def run_trait_selection(
    console: tcod.console.Console,
    context: tcod.context.Context,
    party_members: List[Any]
) -> Optional[List[CharacterTraits]]:
    """
    특성 선택 실행

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        party_members: 파티 멤버 리스트

    Returns:
        선택된 특성 리스트 또는 None (취소 시)
    """
    selection = TraitSelection(party_members, console.width, console.height)
    handler = InputHandler()

    while True:
        # 렌더링
        selection.render(console)
        context.present(console)

        # 입력 처리
        for event in tcod.event.wait():
            action = handler.dispatch(event)

            if action:
                if selection.handle_input(action):
                    # 완료 또는 취소
                    if selection.cancelled:
                        return None
                    return selection.get_results()

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return None
