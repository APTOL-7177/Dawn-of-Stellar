"""
Party Setup - 파티 구성 시스템

4인 파티를 구성하는 시스템 (직업 선택 + 이름 입력)
"""

import tcod.console
import tcod.event
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import yaml
from pathlib import Path

from src.ui.cursor_menu import CursorMenu, MenuItem, TextInputBox
from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, InputHandler
from src.core.logger import get_logger
from src.core.config import get_config
from src.persistence.meta_progress import get_meta_progress
from src.audio import play_bgm
import random


@dataclass
class PartyMember:
    """파티 멤버 정보"""
    job_id: str
    job_name: str
    character_name: str
    stats: Dict[str, Any]


class PartySetup:
    """
    파티 구성 시스템

    1. 직업 선택 (34개 중 4개)
    2. 각 캐릭터 이름 입력
    3. 파티 확인
    """

    def __init__(self, screen_width: int = 80, screen_height: int = 50):
        """
        Args:
            screen_width: 화면 너비
            screen_height: 화면 높이
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.logger = get_logger("party_setup")

        # 파티 멤버 (최대 4명)
        self.party: List[PartyMember] = []
        self.current_slot = 0  # 현재 선택 중인 슬롯 (0~3)

        # 상태
        self.state = "job_select"  # job_select, name_input, confirm
        self.completed = False
        self.cancelled = False

        # 직업 데이터 로드
        self.jobs = self._load_jobs()

        # 랜덤 이름 풀 로드
        self.random_names = self._load_random_names()

        # 현재 메뉴/입력 박스
        self.job_menu: Optional[CursorMenu] = None
        self.name_input: Optional[TextInputBox] = None

        # 첫 번째 슬롯의 직업 선택 메뉴 생성
        self._create_job_menu()

        # 에러 메시지
        self.error_message = ""
        self.error_timer = 0  # 에러 메시지 표시 시간

    def _load_jobs(self) -> List[Dict[str, Any]]:
        """직업 데이터 로드"""
        jobs = []
        characters_dir = Path("data/characters")

        if not characters_dir.exists():
            self.logger.error("캐릭터 디렉토리 없음: data/characters")
            return jobs

        # 메타 진행 정보 가져오기
        meta = get_meta_progress()

        # 개발 모드 확인
        config = get_config()
        dev_mode = config.get("development.unlock_all_classes", False)

        for yaml_file in sorted(characters_dir.glob("*.yaml")):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    job_id = yaml_file.stem

                    # 개발 모드이거나 메타 진행에서 해금된 직업인지 확인
                    is_unlocked = dev_mode or meta.is_job_unlocked(job_id)

                    jobs.append({
                        'id': job_id,
                        'name': data.get('class_name', job_id),
                        'description': data.get('description', ''),
                        'archetype': data.get('archetype', ''),
                        'stats': data.get('base_stats', {}),
                        'unlocked': is_unlocked
                    })
            except Exception as e:
                self.logger.error(f"직업 로드 실패: {yaml_file.name}: {e}")

        self.logger.info(f"직업 {len(jobs)}개 로드 완료 (해금된 직업: {sum(1 for j in jobs if j['unlocked'])}개)")
        return jobs

    def _load_random_names(self) -> List[str]:
        """랜덤 이름 풀 로드"""
        names = []
        name_file = Path("name.txt")

        if not name_file.exists():
            self.logger.warning("name.txt 파일이 없습니다. 기본 이름을 사용합니다.")
            return ["전사", "아크메이지", "도적", "성기사"]

        try:
            with open(name_file, 'r', encoding='utf-8') as f:
                # 한 줄에 하나씩 읽기
                for line in f:
                    name = line.strip()
                    if name:  # 빈 줄 제외
                        names.append(name)

            if not names:
                self.logger.warning("name.txt에서 이름을 찾을 수 없습니다.")
                return ["전사", "아크메이지", "도적", "성기사"]

            self.logger.info(f"랜덤 이름 {len(names)}개 로드 완료")
            return names

        except Exception as e:
            self.logger.error(f"name.txt 로드 실패: {e}")
            return ["전사", "아크메이지", "도적", "성기사"]

    def _create_job_menu(self):
        """직업 선택 메뉴 생성"""
        menu_items = []

        for job in self.jobs:
            # 이미 선택된 직업은 비활성화
            already_selected = any(
                member.job_id == job['id']
                for member in self.party
            )

            desc = f"{job['archetype']} - {job['description']}"
            menu_items.append(MenuItem(
                text=job['name'],
                value=job,
                enabled=job['unlocked'] and not already_selected,
                description=desc
            ))

        # 메뉴 생성
        menu_x = 3
        menu_y = 8
        menu_width = 43

        self.job_menu = CursorMenu(
            title=f"파티 멤버 {self.current_slot + 1}/4 - 직업 선택",
            items=menu_items,
            x=menu_x,
            y=menu_y,
            width=menu_width,
            show_description=True
        )

    def _create_name_input(self):
        """이름 입력 박스 생성"""
        job = self.party[self.current_slot].job_name

        self.name_input = TextInputBox(
            title=f"파티 멤버 {self.current_slot + 1}/4",
            prompt=f"{job}의 이름을 입력하세요 (비우면 랜덤):",
            max_length=20,
            x=20,
            y=15,
            width=40
        )

    def _get_random_name(self) -> str:
        """랜덤 이름 선택 (중복 제외)"""
        # 이미 사용된 이름 제외
        used_names = set(member.character_name for member in self.party if member.character_name)
        available_names = [name for name in self.random_names if name not in used_names]

        if not available_names:
            # 모든 이름이 사용되었으면 숫자 추가
            return f"{random.choice(self.random_names)}{random.randint(1, 999)}"

        return random.choice(available_names)

    def handle_input(self, action: GameAction, event: tcod.event.KeyDown = None) -> bool:
        """
        입력 처리

        Args:
            action: 게임 액션
            event: 키보드 이벤트 (텍스트 입력용)

        Returns:
            파티 구성이 완료되었으면 True
        """
        if self.state == "job_select":
            return self._handle_job_select(action)
        elif self.state == "name_input":
            return self._handle_name_input(action, event)
        elif self.state == "confirm":
            return self._handle_confirm(action)

        return False

    def _handle_job_select(self, action: GameAction) -> bool:
        """직업 선택 입력 처리"""
        if action == GameAction.MOVE_UP:
            self.job_menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            self.job_menu.move_cursor_down()
        elif action == GameAction.CONFIRM:
            # 선택된 직업 가져오기
            selected = self.job_menu.get_selected_item()
            if selected and selected.enabled:
                job_data = selected.value

                # 임시 파티 멤버 생성 (이름은 나중에)
                member = PartyMember(
                    job_id=job_data['id'],
                    job_name=job_data['name'],
                    character_name="",  # 나중에 입력
                    stats=job_data['stats']
                )

                # 현재 슬롯에 추가
                if self.current_slot < len(self.party):
                    self.party[self.current_slot] = member
                else:
                    self.party.append(member)

                # 이름 입력 단계로
                self.state = "name_input"
                self._create_name_input()

        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 이전 슬롯으로 또는 취소
            if self.current_slot > 0:
                self.current_slot -= 1
                if self.current_slot < len(self.party):
                    # 이전 슬롯 수정
                    self.party.pop()
                self._create_job_menu()
            else:
                # 파티 구성 취소
                self.cancelled = True
                return True

        return False

    def _handle_name_input(self, action: GameAction, event: tcod.event.KeyDown = None) -> bool:
        """이름 입력 처리"""
        # Enter 키만 확인 (Z는 문자 입력으로 사용)
        # action이 CONFIRM이나 CANCEL이어도 무시 (Z, X를 문자로 입력하기 위해)
        if event and event.sym == tcod.event.KeySym.RETURN:
            self.name_input.handle_confirm()
            if self.name_input.confirmed:
                name = self.name_input.get_result()

                # 이름이 비어있으면 랜덤 선택
                if not name:
                    name = self._get_random_name()
                    self.logger.info(f"이름이 비어있어 랜덤 선택: {name}")

                # 이름 중복 확인
                if any(m.character_name == name for m in self.party[:self.current_slot]):
                    self.logger.warning(f"중복된 이름: {name}")
                    # 에러 메시지 표시
                    self.error_message = f"이름 중복: '{name}'은(는) 이미 사용 중입니다!"
                    self.error_timer = 120  # 2초 표시 (60프레임 기준)
                    self.name_input.confirmed = False
                    self.name_input.text = ""
                    return False

                # 이름 저장
                self.party[self.current_slot].character_name = name
                self.logger.info(
                    f"파티 멤버 {self.current_slot + 1} 완료: "
                    f"{name} ({self.party[self.current_slot].job_name})"
                )

                # 다음 슬롯으로
                self.current_slot += 1

                if self.current_slot >= 4:
                    # 4명 모두 선택 완료 → 확인 단계
                    self.state = "confirm"
                else:
                    # 다음 멤버 직업 선택
                    self.state = "job_select"
                    self._create_job_menu()

        elif event and event.sym == tcod.event.KeySym.ESCAPE:
            # ESC만 취소 (X는 문자 입력으로 사용)
            self.state = "job_select"
            self.party.pop()  # 현재 슬롯 제거

        elif event and event.sym == tcod.event.KeySym.BACKSPACE:
            self.name_input.handle_backspace()

        # 일반 문자 입력 (ASCII 32~126 범위의 출력 가능한 문자)
        # Z와 X도 여기서 문자로 처리됨 (action은 무시)
        elif event:
            # 특수 키 제외
            if event.sym not in [tcod.event.KeySym.RETURN, tcod.event.KeySym.BACKSPACE, tcod.event.KeySym.ESCAPE]:
                # ASCII 범위 확인 (32~126은 출력 가능한 문자)
                if 32 <= event.sym <= 126:
                    char = chr(event.sym)
                    self.name_input.handle_char_input(char)

        return False

    def _handle_confirm(self, action: GameAction) -> bool:
        """파티 확인 입력 처리"""
        if action == GameAction.CONFIRM:
            # 파티 구성 완료
            self.completed = True
            return True
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 마지막 멤버 수정
            self.current_slot = 3
            self.state = "name_input"
            self._create_name_input()

        return False

    def render(self, console: tcod.console.Console):
        """파티 구성 화면 렌더링"""
        console.clear()

        # 제목
        title = "파티 구성"
        console.print(
            (self.screen_width - len(title)) // 2,
            2,
            title,
            fg=Colors.UI_TEXT_SELECTED
        )

        # 현재 파티 상태 표시 (우측)
        self._render_party_status(console)

        # 상태별 렌더링
        if self.state == "job_select":
            self.job_menu.render(console)

            # 도움말
            help_text = "↑↓: 이동  Z: 선택  X: 이전"
            console.print(
                2,
                self.screen_height - 2,
                help_text,
                fg=Colors.GRAY
            )

        elif self.state == "name_input":
            self.name_input.render(console)

        elif self.state == "confirm":
            # 최종 확인 메시지
            confirm_msg = "파티 구성이 완료되었습니다!"
            console.print(
                (self.screen_width - len(confirm_msg)) // 2,
                20,
                confirm_msg,
                fg=Colors.UI_TEXT_SELECTED
            )

            confirm_help = "Z: 게임 시작  X: 수정"
            console.print(
                (self.screen_width - len(confirm_help)) // 2,
                22,
                confirm_help,
                fg=Colors.GRAY
            )

        # 에러 메시지 표시
        if self.error_timer > 0:
            console.print(
                (self.screen_width - len(self.error_message)) // 2,
                self.screen_height - 4,
                self.error_message,
                fg=(255, 100, 100)  # 빨간색
            )
            self.error_timer -= 1

    def _render_party_status(self, console: tcod.console.Console):
        """현재 파티 상태 표시"""
        status_x = 52
        status_y = 8

        # 테두리
        console.draw_frame(
            status_x,
            status_y - 2,
            28,
            18,
            "현재 파티",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
        )

        # 4개 슬롯 표시
        for i in range(4):
            slot_y = status_y + i * 3

            if i < len(self.party) and self.party[i].character_name:
                # 완성된 멤버
                member = self.party[i]
                console.print(
                    status_x + 2,
                    slot_y,
                    f"{i + 1}. {member.character_name}",
                    fg=Colors.UI_TEXT_SELECTED if i == self.current_slot else Colors.UI_TEXT
                )
                console.print(
                    status_x + 5,
                    slot_y + 1,
                    f"({member.job_name})",
                    fg=Colors.GRAY
                )
            elif i == self.current_slot:
                # 현재 선택 중
                console.print(
                    status_x + 2,
                    slot_y,
                    f"{i + 1}. > 선택 중...",
                    fg=Colors.UI_TEXT_SELECTED
                )
            else:
                # 빈 슬롯
                console.print(
                    status_x + 2,
                    slot_y,
                    f"{i + 1}. (비어있음)",
                    fg=Colors.DARK_GRAY
                )

    def get_party(self) -> Optional[List[PartyMember]]:
        """완성된 파티 반환"""
        if self.completed and len(self.party) == 4:
            return self.party
        return None


def run_party_setup(console: tcod.console.Console, context: tcod.context.Context) -> Optional[List[PartyMember]]:
    """
    파티 구성 실행

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트

    Returns:
        완성된 파티 또는 None (취소 시)
    """
    # 파티 구성 BGM 재생
    play_bgm("party_setup")

    setup = PartySetup(console.width, console.height)
    handler = InputHandler()

    while True:
        # 렌더링
        setup.render(console)
        context.present(console)

        # 입력 처리
        for event in tcod.event.wait():
            action = handler.dispatch(event)

            # KeyDown 이벤트 저장 (텍스트 입력용)
            key_event = event if isinstance(event, tcod.event.KeyDown) else None

            # 이름 입력 중에는 action이 없어도 event 처리 필요
            if action or (key_event and setup.state == "name_input"):
                if setup.handle_input(action, key_event):
                    # 완료 또는 취소
                    if setup.cancelled:
                        return None
                    return setup.get_party()

            # 윈도우 닫기
            if isinstance(event, tcod.event.Quit):
                return None
