"""
멀티플레이 파티 설정 UI

각 플레이어가 자신의 캐릭터를 선택하는 시스템
- 호스트와 클라이언트 간 직업 중복 방지
- 클라이언트끼리도 직업 중복 방지
- 각 플레이어는 자신의 메타 진행 상황에 따라 직업 선택
"""

import tcod.console
import tcod.event
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass
import yaml
from pathlib import Path
import time

from src.ui.cursor_menu import CursorMenu, MenuItem, TextInputBox
from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler
from src.core.logger import get_logger
from src.core.config import get_config
from src.persistence.meta_progress import get_meta_progress
from src.ui.party_setup import PartyMember
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.network import HostNetworkManager, ClientNetworkManager
from src.multiplayer.protocol import MessageType, MessageBuilder


logger = get_logger("multiplayer.party_setup")


class MultiplayerPartySetup:
    """멀티플레이 파티 설정 시스템"""
    
    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        session: MultiplayerSession,
        network_manager: Any,
        local_player_id: str,
        character_allocation: int,
        is_host: bool
    ):
        """
        Args:
            screen_width: 화면 너비
            screen_height: 화면 높이
            session: 멀티플레이 세션
            network_manager: 네트워크 매니저
            local_player_id: 로컬 플레이어 ID
            character_allocation: 선택할 수 있는 캐릭터 수
            is_host: 호스트 여부
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.session = session
        self.network_manager = network_manager
        self.local_player_id = local_player_id
        self.character_allocation = character_allocation
        self.is_host = is_host
        
        self.logger = get_logger("multiplayer.party_setup")
        
        # 로컬 플레이어의 파티 멤버 (최대 character_allocation명)
        self.party: List[PartyMember] = []
        self.current_slot = 0
        
        # 상태
        self.state = "job_select"  # job_select, name_input, trait_select
        self.completed = False
        self.cancelled = False
        
        # 직업 데이터 로드 (로컬 플레이어의 메타 진행 기준)
        self.jobs = self._load_jobs()
        
        # 랜덤 이름 풀 로드
        self.random_names = self._load_random_names()
        
        # 현재 메뉴/입력 박스
        self.job_menu: Optional[CursorMenu] = None
        self.name_input: Optional[TextInputBox] = None
        self.trait_menu: Optional[CursorMenu] = None
        
        # 선택된 직업 ID 목록 (전체 세션 기준 - 중복 방지용)
        self.selected_job_ids: Set[str] = set()
        self.other_players_jobs: Set[str] = set()  # 다른 플레이어들이 선택한 직업
        
        # 네트워크 메시지 핸들러 등록
        self._register_message_handlers()
        
        # 직업 선택 메뉴 생성
        self._create_job_menu()
        
        # 에러 메시지
        self.error_message = ""
        self.error_timer = 0.0
    
    def _register_message_handlers(self):
        """네트워크 메시지 핸들러 등록"""
        # 다른 플레이어의 직업 선택/해제 메시지 수신
        if hasattr(self.network_manager, 'register_message_handler'):
            self.network_manager.register_message_handler(
                MessageType.JOB_SELECTED,
                self._handle_job_selected
            )
            self.network_manager.register_message_handler(
                MessageType.JOB_DESELECTED,
                self._handle_job_deselected
            )
    
    def _handle_job_selected(self, message: Any):
        """다른 플레이어가 직업을 선택했을 때"""
        try:
            player_id = message.player_id
            job_id = message.data.get("job_id")
            
            if player_id != self.local_player_id and job_id:
                self.other_players_jobs.add(job_id)
                self.selected_job_ids.add(job_id)
                self.logger.info(f"다른 플레이어 {player_id}가 직업 선택: {job_id}")
                # 직업 메뉴 갱신 (선택 불가능한 직업 표시)
                if self.state == "job_select":
                    self._create_job_menu()
        except Exception as e:
            self.logger.error(f"직업 선택 메시지 처리 실패: {e}", exc_info=True)
    
    def _handle_job_deselected(self, message: Any):
        """다른 플레이어가 직업을 해제했을 때"""
        try:
            player_id = message.player_id
            job_id = message.data.get("job_id")
            
            if player_id != self.local_player_id and job_id:
                self.other_players_jobs.discard(job_id)
                # 다른 플레이어도 선택하지 않았는지 확인
                # TODO: 세션에서 모든 플레이어의 선택된 직업을 확인
                self.selected_job_ids.discard(job_id)
                self.logger.info(f"다른 플레이어 {player_id}가 직업 해제: {job_id}")
                # 직업 메뉴 갱신
                if self.state == "job_select":
                    self._create_job_menu()
        except Exception as e:
            self.logger.error(f"직업 해제 메시지 처리 실패: {e}", exc_info=True)
    
    def _load_jobs(self) -> List[Dict[str, Any]]:
        """직업 데이터 로드 (로컬 플레이어의 메타 진행 기준)"""
        jobs = []
        characters_dir = Path("data/characters")
        
        if not characters_dir.exists():
            self.logger.error("캐릭터 디렉토리 없음: data/characters")
            return jobs
        
        # 로컬 플레이어의 메타 진행 정보 가져오기
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
        
        self.logger.info(
            f"직업 {len(jobs)}개 로드 완료 "
            f"(해금된 직업: {sum(1 for j in jobs if j['unlocked'])}개)"
        )
        return jobs
    
    def _load_random_names(self) -> List[str]:
        """랜덤 이름 풀 로드"""
        name_file = Path("name.txt")
        
        if not name_file.exists():
            return ["아리아", "카일", "엘리나", "다리우스", "루나", "제이든", "세라", "라이언",
                    "미아", "알렉스", "소피아", "마커스", "이리스", "테오", "엠마", "노아"]
        
        try:
            with open(name_file, 'r', encoding='utf-8') as f:
                names = [line.strip() for line in f if line.strip()]
            if not names:
                return ["아리아", "카일", "엘리나", "다리우스", "루나", "제이든", "세라", "라이언",
                        "미아", "알렉스", "소피아", "마커스", "이리스", "테오", "엠마", "노아"]
            return names
        except Exception as e:
            self.logger.error(f"name.txt 로드 실패: {e}")
            return ["아리아", "카일", "엘리나", "다리우스", "루나", "제이든", "세라", "라이언",
                    "미아", "알렉스", "소피아", "마커스", "이리스", "테오", "엠마", "노아"]
    
    def _create_job_menu(self):
        """직업 선택 메뉴 생성 (중복 방지)"""
        available_jobs = [job for job in self.jobs if job['unlocked']]
        
        # 이미 선택한 직업 제외
        my_selected_jobs = {member.job_id for member in self.party if hasattr(member, 'job_id') and member.job_id}
        
        # 다른 플레이어가 선택한 직업 제외
        # available_jobs에서 이미 선택된 직업이나 다른 플레이어가 선택한 직업 필터링
        menu_items = []
        for job in available_jobs:
            job_id = job['id']
            
            # 이미 내가 선택한 직업인지 확인
            if job_id in my_selected_jobs:
                continue
            
            # 다른 플레이어가 선택한 직업인지 확인
            if job_id in self.other_players_jobs:
                # 비활성화된 항목으로 추가 (선택 불가 표시)
                menu_items.append(
                    MenuItem(
                        text=f"{job['name']} [이미 선택됨]",
                        value=job,
                        enabled=False,
                        description=job.get('description', '')
                    )
                )
            else:
                # 선택 가능한 항목
                menu_items.append(
                    MenuItem(
                        text=job['name'],
                        value=job,
                        description=job.get('description', '')
                    )
                )
        
        # 직업이 없으면 오류
        if not menu_items:
            self.error_message = "선택 가능한 직업이 없습니다"
            self.error_timer = 3.0
            return
        
        self.job_menu = CursorMenu(
            title=f"직업 선택 ({len(self.party)}/{self.character_allocation})",
            items=menu_items,
            x=10,
            y=10,
            width=60
        )
    
    def _create_name_input(self):
        """이름 입력 박스 생성"""
        if not self.party or self.current_slot >= len(self.party):
            return
        
        member = self.party[self.current_slot]
        job_name = member.job_name
        
        # 랜덤 이름 추천
        import random
        random_name = random.choice(self.random_names) if self.random_names else "플레이어"
        
        self.name_input = TextInputBox(
            title=f"이름 입력 ({self.current_slot + 1}/{self.character_allocation})",
            prompt=f"{job_name}의 이름을 입력하세요 (비우면 {random_name}):",
            max_length=20,
            x=20,
            y=15,
            width=40
        )
    
    def _create_trait_menu(self):
        """특성 선택 메뉴 생성"""
        if not self.party or self.current_slot >= len(self.party):
            return
        
        member = self.party[self.current_slot]
        job_id = member.job_id
        
        from src.character.character_loader import get_traits
        meta = get_meta_progress()
        config = get_config()
        dev_mode = config.get("development.unlock_all_classes", False)
        
        # 해당 직업의 특성 가져오기
        traits = get_traits(job_id)
        
        # 해금된 특성만 필터링
        available_traits = []
        for trait in traits:
            if dev_mode or meta.is_trait_unlocked(job_id, trait.id):
                available_traits.append(trait)
        
        if not available_traits:
            self.logger.warning(f"{job_id}의 특성이 없습니다")
            member.selected_traits = []
            return
        
        menu_items = []
        selected_trait_ids = set(member.selected_traits or [])
        
        for trait in available_traits:
            is_selected = trait.id in selected_trait_ids
            text = f"{'✓ ' if is_selected else '  '}{trait.name}"
            
            menu_items.append(
                MenuItem(
                    text=text,
                    value=trait,
                    description=trait.description
                )
            )
        
        self.trait_menu = CursorMenu(
            title=f"{member.character_name} ({member.job_name}) - 특성 선택 (최대 2개)",
            items=menu_items,
            x=10,
            y=10,
            width=60
        )
    
    def handle_input(self, action: GameAction, key_event: Optional[tcod.event.KeyDown] = None) -> bool:
        """입력 처리"""
        if self.error_timer > 0:
            self.error_timer -= 0.1
            if self.error_timer <= 0:
                self.error_message = ""
        
        if self.state == "job_select":
            return self._handle_job_select(action)
        elif self.state == "name_input":
            return self._handle_name_input(action, key_event)
        elif self.state == "trait_select":
            return self._handle_trait_select(action)
        
        return False
    
    def _handle_job_select(self, action: GameAction) -> bool:
        """직업 선택 상태 입력 처리"""
        if not self.job_menu:
            self._create_job_menu()
        
        if action == GameAction.CONFIRM:
            selected = self.job_menu.get_selected_item()
            if selected and selected.enabled and selected.value:
                job = selected.value
                
                # 중복 확인 (다시 한 번 확인)
                if job['id'] in self.other_players_jobs:
                    self.error_message = f"{job['name']}은(는) 이미 다른 플레이어가 선택했습니다"
                    self.error_timer = 2.0
                    return False
                
                # 파티 멤버 추가
                member = PartyMember(
                    job_id=job['id'],
                    job_name=job['name'],
                    character_name="",
                    stats=job['stats'],
                    selected_traits=[]
                )
                self.party.append(member)
                
                # 네트워크로 직업 선택 전송
                self._send_job_selected(job['id'])
                
                self.logger.info(f"직업 선택: {job['name']} ({job['id']})")
                
                # 이름 입력으로 이동
                self.current_slot = len(self.party) - 1
                self.state = "name_input"
                self._create_name_input()
                
                # 모든 캐릭터 선택 완료 확인
                if len(self.party) >= self.character_allocation:
                    # 마지막 캐릭터 이름 입력 후 특성 선택으로
                    pass
                
                return False
        
        elif action == GameAction.CANCEL:
            # 이전 슬롯으로 돌아가기
            if len(self.party) > 0:
                # 마지막 선택한 직업 해제
                last_member = self.party.pop()
                if hasattr(last_member, 'job_id') and last_member.job_id:
                    self._send_job_deselected(last_member.job_id)
                
                self.current_slot = len(self.party)
                self._create_job_menu()
            else:
                self.cancelled = True
                return True
        
        elif action == GameAction.MOVE_UP:
            if self.job_menu:
                self.job_menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            if self.job_menu:
                self.job_menu.move_cursor_down()
        
        return False
    
    def _handle_name_input(self, action: GameAction, key_event: Optional[tcod.event.KeyDown] = None) -> bool:
        """이름 입력 상태 입력 처리"""
        if not self.name_input:
            return False
        
        if key_event:
            self.name_input.handle_input(action, key_event)
        
        if action == GameAction.CONFIRM:
            name = self.name_input.text.strip()
            
            # 빈 이름이면 랜덤 이름 사용
            if not name:
                import random
                name = random.choice(self.random_names) if self.random_names else "플레이어"
            
            # 현재 멤버에 이름 설정
            if self.party and self.current_slot < len(self.party):
                self.party[self.current_slot].character_name = name
                self.logger.info(f"이름 입력: {name}")
                
                # 특성 선택으로 이동
                self.state = "trait_select"
                self._create_trait_menu()
            
            return False
        
        elif action == GameAction.CANCEL:
            # 직업 선택으로 돌아가기
            self.state = "job_select"
            self.name_input = None
            return False
        
        return False
    
    def _handle_trait_select(self, action: GameAction) -> bool:
        """특성 선택 상태 입력 처리"""
        if not self.trait_menu:
            self._create_trait_menu()
        
        if not self.party or self.current_slot >= len(self.party):
            return False
        
        member = self.party[self.current_slot]
        selected_traits = member.selected_traits or []
        
        if action == GameAction.CONFIRM:
            selected = self.trait_menu.get_selected_item()
            if selected and selected.value:
                trait = selected.value
                
                if trait.id in selected_traits:
                    # 선택 해제
                    selected_traits.remove(trait.id)
                elif len(selected_traits) < 2:
                    # 선택
                    selected_traits.append(trait.id)
                
                member.selected_traits = selected_traits
                self._create_trait_menu()
                
                # 2개 선택 완료 또는 ESC로 넘어가기 가능
                if len(selected_traits) >= 2:
                    # 자동으로 다음 단계로
                    pass
        
        elif action == GameAction.CANCEL or (action == GameAction.CONFIRM and len(selected_traits) >= 0):
            # 다음 캐릭터로 또는 완료
            if len(self.party) < self.character_allocation:
                # 다음 캐릭터 선택
                self.current_slot = len(self.party)
                self.state = "job_select"
                self._create_job_menu()
            else:
                # 모든 캐릭터 선택 완료
                self.completed = True
                return True
        
        elif action == GameAction.MOVE_UP:
            if self.trait_menu:
                self.trait_menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            if self.trait_menu:
                self.trait_menu.move_cursor_down()
        
        return False
    
    def _send_job_selected(self, job_id: str):
        """네트워크로 직업 선택 전송"""
        try:
            message = MessageBuilder.job_selected(
                job_id,
                self.local_player_id
            )
            if self.is_host:
                # 호스트는 모든 클라이언트에게 브로드캐스트
                self.network_manager.broadcast(message)
            else:
                # 클라이언트는 호스트에게 전송
                self.network_manager.send_to_host(message)
        except Exception as e:
            self.logger.error(f"직업 선택 메시지 전송 실패: {e}", exc_info=True)
    
    def _send_job_deselected(self, job_id: str):
        """네트워크로 직업 해제 전송"""
        try:
            message = MessageBuilder.job_deselected(
                job_id,
                self.local_player_id
            )
            if self.is_host:
                self.network_manager.broadcast(message)
            else:
                self.network_manager.send_to_host(message)
        except Exception as e:
            self.logger.error(f"직업 해제 메시지 전송 실패: {e}", exc_info=True)
    
    def render(self, console: tcod.console.Console):
        """렌더링"""
        render_space_background(console, self.screen_width, self.screen_height)
        
        # 제목
        title = f"파티 설정 ({len(self.session.players)}명 플레이어)"
        console.print(
            self.screen_width // 2 - len(title) // 2,
            2,
            title,
            fg=Colors.WHITE
        )
        
        # 상태 정보
        status = f"당신: {len(self.party)}/{self.character_allocation}명 선택됨"
        console.print(
            self.screen_width // 2 - len(status) // 2,
            4,
            status,
            fg=Colors.UI_TEXT
        )
        
        # 현재 상태에 따라 렌더링
        if self.state == "job_select" and self.job_menu:
            self.job_menu.render(console)
        elif self.state == "name_input" and self.name_input:
            self.name_input.render(console)
        elif self.state == "trait_select" and self.trait_menu:
            self.trait_menu.render(console)
        
        # 에러 메시지
        if self.error_message:
            console.print(
                self.screen_width // 2 - len(self.error_message) // 2,
                self.screen_height - 5,
                self.error_message,
                fg=Colors.RED
            )
        
        # 안내 메시지
        help_text = "ESC: 취소" if not self.completed else "모든 캐릭터 선택 완료!"
        console.print(
            self.screen_width // 2 - len(help_text) // 2,
            self.screen_height - 3,
            help_text,
            fg=Colors.UI_TEXT
        )
    
    def get_party(self) -> Optional[List[PartyMember]]:
        """선택된 파티 반환"""
        if self.completed and len(self.party) == self.character_allocation:
            return self.party
        return None


def run_multiplayer_party_setup(
    console: tcod.console.Console,
    context: tcod.context.Context,
    session: MultiplayerSession,
    network_manager: Any,
    local_player_id: str,
    character_allocation: int,
    is_host: bool
) -> Optional[tuple[List[PartyMember], List[str]]]:
    """
    멀티플레이 파티 설정 실행
    
    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        session: 멀티플레이 세션
        network_manager: 네트워크 매니저
        local_player_id: 로컬 플레이어 ID
        character_allocation: 선택할 수 있는 캐릭터 수
        is_host: 호스트 여부
        
    Returns:
        (파티 멤버 리스트, 선택된 패시브 리스트) 또는 None (취소 시)
    """
    setup = MultiplayerPartySetup(
        screen_width=console.width,
        screen_height=console.height,
        session=session,
        network_manager=network_manager,
        local_player_id=local_player_id,
        character_allocation=character_allocation,
        is_host=is_host
    )
    
    handler = InputHandler()
    
    while True:
        # 렌더링
        setup.render(console)
        context.present(console)
        
        # 입력 처리
        for event in tcod.event.wait():
            if isinstance(event, tcod.event.Quit):
                return None
            
            context.convert_event(event)
            action = handler.dispatch(event)
            
            key_event = event if isinstance(event, tcod.event.KeyDown) else None
            
            if action or key_event:
                if setup.handle_input(action, key_event):
                    if setup.cancelled:
                        return None
                    elif setup.completed:
                        party = setup.get_party()
                        # 패시브는 호스트가 선택 (나중에 별도 처리)
                        return (party, [])

