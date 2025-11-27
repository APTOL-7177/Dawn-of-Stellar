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
from src.ui.input_handler import GameAction, InputHandler, unified_input_handler
from src.core.logger import get_logger
from src.core.config import get_config
from src.persistence.meta_progress import get_meta_progress
from src.ui.party_setup import PartyMember
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.network import HostNetworkManager, ClientNetworkManager
from src.multiplayer.protocol import MessageType, MessageBuilder
from src.audio import play_sfx
from src.ui.multiplayer_lobby import get_character_allocation


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
        self.player_left = False  # 플레이어가 나갔는지 여부
        
        # 멀티플레이: 플레이어별 완료 상태 추적 (호스트만 사용)
        self.players_completed: Set[str] = set()  # 직업 선택을 완료한 플레이어 ID 집합
        self.local_completed = False  # 로컬 플레이어가 완료했는지 여부
        
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
        
        # 순차 직업 선택 관련
        self.player_order: List[str] = []  # 플레이어 순서 (1P, 2P, 3P, 4P)
        self.current_turn_player_id: Optional[str] = None  # 현재 직업 선택 턴인 플레이어 ID
        self._initialize_player_order()  # 플레이어 순서 초기화
        
        # 네트워크 메시지 핸들러 등록
        self._register_message_handlers()
        
        # 직업 선택 메뉴 생성
        self._create_job_menu()
        
        # 에러 메시지
        self.error_message = ""
        self.error_timer = 0.0
    
    def _initialize_player_order(self):
        """플레이어 순서 초기화 (1P = 호스트, 이후 연결 순서)"""
        # 호스트를 첫 번째로
        if self.session.host_id and self.session.host_id in self.session.players:
            self.player_order = [self.session.host_id]
            # 나머지 플레이어는 연결 순서대로 (딕셔너리 순서는 Python 3.7+에서 삽입 순서 보장)
            for player_id in self.session.players.keys():
                if player_id != self.session.host_id:
                    self.player_order.append(player_id)
        else:
            # 호스트가 없으면 모든 플레이어를 순서대로
            self.player_order = list(self.session.players.keys())
        
        # 호스트는 첫 번째 플레이어를 현재 턴으로 설정하고 브로드캐스트
        if self.is_host:
            if self.player_order:
                self.current_turn_player_id = self.player_order[0]
                self._broadcast_turn_change()
                self.logger.info(f"호스트: 초기 턴 설정 = {self.current_turn_player_id}, 순서 = {self.player_order}")
        else:
            # 클라이언트는 호스트로부터 턴 변경 메시지를 받을 때까지 대기
            # 초기값은 None으로 설정 (호스트의 메시지를 받으면 업데이트됨)
            self.current_turn_player_id = None
            self.logger.info(f"클라이언트: 턴 정보 대기 중... (호스트 메시지 대기)")
    
    def _register_message_handlers(self):
        """네트워크 메시지 핸들러 등록"""
        # 다른 플레이어의 직업 선택/해제 메시지 수신
        if hasattr(self.network_manager, 'register_handler'):
            self.network_manager.register_handler(
                MessageType.JOB_SELECTED,
                self._handle_job_selected
            )
            self.network_manager.register_handler(
                MessageType.JOB_DESELECTED,
                self._handle_job_deselected
            )
            self.network_manager.register_handler(
                MessageType.JOB_SELECTION_COMPLETE,
                self._handle_job_selection_complete
            )
            self.network_manager.register_handler(
                MessageType.TURN_CHANGED,
                self._handle_turn_changed
            )
            self.network_manager.register_handler(
                MessageType.PLAYER_LEFT,
                self._handle_player_left
            )
    
    def _handle_job_selected(self, message: Any, sender_id: Optional[str] = None):
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
    
    def _handle_job_deselected(self, message: Any, sender_id: Optional[str] = None):
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
    
    def _handle_job_selection_complete(self, message: Any, sender_id: Optional[str] = None):
        """다른 플레이어가 직업 선택을 완료했을 때"""
        try:
            player_id = message.player_id
            self.logger.info(f"플레이어 {player_id}가 직업 선택 완료")
            
            # 호스트만 다음 턴으로 넘기는 로직 처리 및 완료 상태 추적
            if self.is_host:
                # 완료한 플레이어 추가
                if player_id not in self.players_completed:
                    self.players_completed.add(player_id)
                    self.logger.info(f"완료한 플레이어: {self.players_completed}, 전체 플레이어: {list(self.session.players.keys())}")
                
                # 다음 턴으로 넘기기 (현재 턴이 완료한 플레이어의 턴인 경우에만)
                if self.current_turn_player_id == player_id:
                    self.logger.info(f"플레이어 {player_id}의 턴 완료 - 다음 턴으로 넘김")
                    self._advance_to_next_turn()
                else:
                    self.logger.info(f"플레이어 {player_id} 완료했지만 현재 턴이 아님 (현재 턴: {self.current_turn_player_id})")
                
                # 모든 플레이어가 완료했는지 확인
                all_players = set(self.session.players.keys())
                if all_players.issubset(self.players_completed):
                    self.logger.info("모든 플레이어의 직업 선택 완료! 호스트도 완료 처리")
                    # 호스트 자신도 완료했고 모든 플레이어가 완료했으면 completed = True
                    if self.local_completed:
                        self.completed = True
                else:
                    # 아직 완료하지 않은 플레이어가 있으면 completed는 False로 유지
                    self.logger.info(f"다른 플레이어 대기 중... 완료: {self.players_completed}, 전체: {all_players}")
            # 클라이언트는 완료 메시지를 받아도 completed를 True로 설정하지 않음 (호스트 게임 시작 대기)
        except Exception as e:
            self.logger.error(f"직업 선택 완료 메시지 처리 실패: {e}", exc_info=True)
    
    def _handle_turn_changed(self, message: Any, sender_id: Optional[str] = None):
        """턴이 변경되었을 때"""
        try:
            current_player_id = message.data.get("current_player_id")
            player_order = message.data.get("player_order", [])
            
            if current_player_id:
                old_turn = self.current_turn_player_id
                self.current_turn_player_id = current_player_id
                if player_order:
                    self.player_order = player_order
                self.logger.info(f"턴 변경 수신: {old_turn} -> {current_player_id}, 순서 = {player_order}, 로컬 플레이어 = {self.local_player_id}")
                # 직업 선택 상태면 메뉴 갱신
                if self.state == "job_select":
                    self._create_job_menu()
            else:
                self.logger.warning("턴 변경 메시지에 current_player_id가 없습니다")
        except Exception as e:
            self.logger.error(f"턴 변경 메시지 처리 실패: {e}", exc_info=True)
    
    def _handle_job_select_internal(self, job_id: str, player_id: str):
        """직업 선택 내부 처리 (봇용)"""
        # 직업 데이터 찾기
        job_data = None
        for job in self.jobs:
            if job.get('id') == job_id:
                job_data = job
                break
        
        if not job_data:
            self.logger.error(f"직업 데이터를 찾을 수 없습니다: {job_id}")
            return
        
        # 이미 선택된 직업인지 확인
        if job_id in self.other_players_jobs:
            self.logger.warning(f"이미 선택된 직업입니다: {job_id}")
            return
        
        # 파티 멤버 생성
        job_name = job_data.get('name', job_id)
        stats = job_data.get('base_stats', {})
        
        member = PartyMember(
            job_id=job_id,
            job_name=job_name,
            character_name="",  # 이름은 다음 단계에서 입력
            stats=stats,
            player_id=player_id
        )
        
        # 파티에 추가
        self.party.append(member)
        self.current_slot = len(self.party)
        
        # 선택된 직업으로 표시
        self.other_players_jobs.add(job_id)
        self.selected_job_ids.add(job_id)
        
        # 네트워크로 직업 선택 전송
        self._send_job_selected(job_id)
        
        # 이름 입력 단계로 이동
        self.state = "name_input"
        self._create_name_input()
        
        self.logger.info(f"봇 {player_id} 직업 선택 완료: {job_id}")
    
    def _handle_name_input_internal(self, name: str):
        """이름 입력 내부 처리 (봇용)"""
        if not self.party or self.current_slot >= len(self.party):
            return
        
        member = self.party[self.current_slot]
        member.character_name = name
        
        # 특성 선택 단계로 이동
        self.state = "trait_select"
        self._create_trait_menu()
        
        self.logger.info(f"봇 이름 입력 완료: {name}")
    
    def _handle_trait_select_internal(self, trait_ids: List[str]):
        """특성 선택 내부 처리 (봇용)"""
        if not self.party or self.current_slot >= len(self.party):
            return
        
        member = self.party[self.current_slot]
        member.selected_traits = trait_ids[:2]  # 최대 2개
        
        # 다음 캐릭터로 또는 완료
        if len(self.party) < self.character_allocation:
            # 다음 캐릭터 선택
            self.current_slot = len(self.party)
            self.state = "job_select"
            self._create_job_menu()
        else:
            # 모든 캐릭터 선택 완료
            self._send_job_selection_complete()
            self.logger.info(f"봇 {member.player_id} 모든 캐릭터 선택 완료")
    
    def _handle_player_left(self, message: Any, sender_id: Optional[str] = None):
        """플레이어가 나갔을 때"""
        try:
            player_id = message.data.get("player_id") or getattr(message, 'player_id', None)
            if not player_id:
                self.logger.warning("플레이어 나감 메시지에 player_id가 없습니다")
                return
            
            self.logger.warning(f"플레이어 {player_id}가 나갔습니다!")
            
            # 호스트가 나갔는지 확인
            if player_id == self.session.host_id:
                self.logger.error("호스트가 나갔습니다! 게임을 중단합니다.")
                self.cancelled = True
                self.error_message = "호스트가 게임을 나갔습니다. 게임을 종료합니다."
                self.error_timer = 5.0
                return
            
            # 나간 플레이어가 현재 턴이었는지 확인
            if player_id == self.current_turn_player_id:
                # 호스트만 다음 턴으로 넘기기
                if self.is_host:
                    self.logger.info(f"현재 턴 플레이어 {player_id}가 나갔으므로 다음 턴으로 넘깁니다.")
                    self._advance_to_next_turn()
                else:
                    # 클라이언트는 호스트가 턴을 넘길 때까지 대기
                    self.logger.info(f"현재 턴 플레이어 {player_id}가 나갔습니다. 호스트가 턴을 넘길 때까지 대기합니다.")
            
            # 나간 플레이어의 직업 선택 해제
            if player_id in self.session.players:
                player = self.session.players[player_id]
                if hasattr(player, 'party') and player.party:
                    for member in player.party:
                        if hasattr(member, 'job_id') and member.job_id:
                            job_id = member.job_id
                            self.other_players_jobs.discard(job_id)
                            self.selected_job_ids.discard(job_id)
                            self.logger.info(f"나간 플레이어의 직업 {job_id} 해제")
            
            # 플레이어 순서에서 제거
            if player_id in self.player_order:
                self.player_order.remove(player_id)
                # 현재 턴이 유효한지 확인
                if self.current_turn_player_id not in self.player_order:
                    # 현재 턴이 유효하지 않으면 첫 번째 플레이어로 설정
                    if self.player_order:
                        self.current_turn_player_id = self.player_order[0]
                        if self.is_host:
                            self._broadcast_turn_change()
            
            # 직업 메뉴 갱신
            if self.state == "job_select":
                self._create_job_menu()
        except Exception as e:
            self.logger.error(f"플레이어 나감 메시지 처리 실패: {e}", exc_info=True)
    
    def _advance_to_next_turn(self):
        """다음 플레이어로 턴 넘기기 (호스트만 호출) - 이미 완료한 플레이어는 건너뜀"""
        if not self.is_host:
            return
        
        # 모든 플레이어가 완료했는지 확인
        all_players = set(self.session.players.keys())
        if all_players.issubset(self.players_completed):
            self.logger.info("모든 플레이어가 완료했습니다. 턴 진행 중지")
            return
        
        # 현재 턴 플레이어의 인덱스 찾기
        try:
            current_index = self.player_order.index(self.current_turn_player_id)
            
            # 다음 미완료 플레이어 찾기
            next_index = current_index + 1
            while next_index < len(self.player_order):
                next_player_id = self.player_order[next_index]
                # 이미 완료한 플레이어는 건너뛰기
                if next_player_id not in self.players_completed:
                    self.current_turn_player_id = next_player_id
                    self._broadcast_turn_change()
                    self.logger.info(f"다음 턴: {self.current_turn_player_id} (완료한 플레이어 건너뜀)")
                    return
                next_index += 1
            
            # 모든 플레이어를 순회했지만 미완료 플레이어가 없음 (이론적으로는 발생하지 않아야 함)
            # 다시 처음부터 찾기
            for i, player_id in enumerate(self.player_order):
                if player_id not in self.players_completed:
                    self.current_turn_player_id = player_id
                    self._broadcast_turn_change()
                    self.logger.info(f"다음 턴 (순환): {self.current_turn_player_id}")
                    return
            
            # 모든 플레이어가 완료했지만 아직 확인되지 않음
            self.logger.warning("모든 플레이어가 완료한 것으로 보이지만 확인되지 않았습니다. 완료 대기 중...")
        except (ValueError, IndexError) as e:
            self.logger.error(f"다음 턴으로 넘기기 실패: {e}", exc_info=True)
    
    def _broadcast_turn_change(self):
        """턴 변경 브로드캐스트 (호스트만 호출)"""
        if not self.is_host:
            return
        
        try:
            message = MessageBuilder.turn_changed(
                self.current_turn_player_id,
                self.player_order
            )
            # 비동기 브로드캐스트
            import asyncio
            server_loop = getattr(self.network_manager, '_server_event_loop', None)
            if server_loop and server_loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.network_manager.broadcast(message),
                    server_loop
                )
                self.logger.info(f"턴 변경 브로드캐스트: {self.current_turn_player_id}")
        except Exception as e:
            self.logger.error(f"턴 변경 브로드캐스트 실패: {e}", exc_info=True)
    
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
        """직업 선택 메뉴 생성 (중복 방지 및 턴 체크)"""
        available_jobs = [job for job in self.jobs if job['unlocked']]
        
        # 현재 턴이 설정되지 않았으면 처리
        if self.current_turn_player_id is None:
            if self.is_host:
                # 호스트는 첫 번째 플레이어로 초기화
                if self.player_order:
                    self.current_turn_player_id = self.player_order[0]
                    self.logger.warning("_create_job_menu: 호스트의 current_turn_player_id가 None이었습니다. 첫 번째 플레이어로 초기화합니다.")
                    self._broadcast_turn_change()
            else:
                # 클라이언트는 호스트 메시지 대기 중
                self.logger.warning("_create_job_menu: 클라이언트의 current_turn_player_id가 None입니다. 호스트 메시지 대기 중...")
        
        # 현재 턴인지 확인
        is_my_turn = (self.current_turn_player_id == self.local_player_id) if self.current_turn_player_id else False
        
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
            elif not is_my_turn:
                # 현재 턴이 아니면 모든 직업 비활성화
                current_player = self.session.players.get(self.current_turn_player_id)
                player_name = current_player.player_name if current_player else "다른 플레이어"
                menu_items.append(
                    MenuItem(
                        text=f"{job['name']} [대기 중]",
                        value=job,
                        enabled=False,
                        description=f"{player_name}의 턴입니다. 기다려주세요..."
                    )
                )
            else:
                # 선택 가능한 항목 (현재 턴이고 중복되지 않은 직업)
                menu_items.append(
                    MenuItem(
                        text=job['name'],
                        value=job,
                        enabled=True,
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
        # traits는 딕셔너리 리스트: [{'id': 'xxx', 'name': 'xxx', 'description': 'xxx'}, ...]
        available_traits = []
        for trait in traits:
            trait_id = trait.get('id') if isinstance(trait, dict) else trait
            if trait_id and (dev_mode or meta.is_trait_unlocked(job_id, trait_id)):
                available_traits.append(trait)
        
        if not available_traits:
            self.logger.warning(f"{job_id}의 특성이 없습니다")
            member.selected_traits = []
            return
        
        menu_items = []
        selected_trait_ids = set(member.selected_traits or [])
        
        for trait in available_traits:
            # trait은 딕셔너리
            trait_id = trait.get('id') if isinstance(trait, dict) else trait
            trait_name = trait.get('name', '알 수 없는 특성') if isinstance(trait, dict) else str(trait)
            trait_desc = trait.get('description', '') if isinstance(trait, dict) else ''
            
            is_selected = trait_id in selected_trait_ids
            text = f"{'* ' if is_selected else '  '}{trait_name}"
            
            menu_items.append(
                MenuItem(
                    text=text,
                    value=trait,
                    description=trait_desc,
                    is_selected=is_selected  # 선택 상태 표시 (색상 변경용)
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
            return self._handle_trait_select(action, key_event)
        
        return False
    
    def _handle_job_select(self, action: GameAction) -> bool:
        """직업 선택 상태 입력 처리"""
        # 현재 턴이 설정되지 않았으면 처리
        if self.current_turn_player_id is None:
            if self.is_host:
                # 호스트는 첫 번째 플레이어로 초기화
                if self.player_order:
                    self.current_turn_player_id = self.player_order[0]
                    self.logger.warning("_handle_job_select: 호스트의 current_turn_player_id가 None이었습니다. 첫 번째 플레이어로 초기화합니다.")
                    self._broadcast_turn_change()
                    # 메뉴 재생성 (턴 정보 반영)
                    self._create_job_menu()
            else:
                # 클라이언트는 호스트 메시지 대기 중
                if action == GameAction.CONFIRM:
                    self.error_message = "턴 정보를 기다리는 중입니다. 잠시 후 다시 시도해주세요."
                    self.error_timer = 2.0
                return False
        
        # 현재 턴인지 확인
        is_my_turn = (self.current_turn_player_id == self.local_player_id) if self.current_turn_player_id else False
        
        if not self.job_menu:
            self._create_job_menu()
        
        # 커서 이동은 항상 허용
        if action == GameAction.MOVE_UP:
            if self.job_menu:
                self.job_menu.move_cursor_up()
            return False
        elif action == GameAction.MOVE_DOWN:
            if self.job_menu:
                self.job_menu.move_cursor_down()
            return False
        
        # CONFIRM 액션은 현재 턴일 때만 허용
        if action == GameAction.CONFIRM:
            # 턴 체크 (강력한 검증)
            if not is_my_turn:
                current_player = self.session.players.get(self.current_turn_player_id)
                player_name = current_player.player_name if current_player else "다른 플레이어"
                self.error_message = f"{player_name}의 턴입니다. 기다려주세요..."
                self.error_timer = 2.0
                self.logger.warning(f"턴 체크 실패: 현재 턴={self.current_turn_player_id}, 로컬 플레이어={self.local_player_id}")
                return False
            
            selected = self.job_menu.get_selected_item()
            if selected and selected.value:
                # enabled 체크 (메뉴에서 이미 비활성화되어 있을 수 있음)
                if not selected.enabled:
                    self.error_message = "이 직업은 선택할 수 없습니다"
                    self.error_timer = 1.0
                    return False
                
                job = selected.value
                
                # 턴 체크 (다시 한 번 확인)
                if not is_my_turn:
                    self.error_message = "현재 당신의 턴이 아닙니다"
                    self.error_timer = 1.0
                    self.logger.warning(f"턴 체크 실패 (선택 시): 현재 턴={self.current_turn_player_id}, 로컬 플레이어={self.local_player_id}")
                    return False
                
                # 중복 확인 (다시 한 번 확인)
                if job['id'] in self.other_players_jobs:
                    self.error_message = f"{job['name']}은(는) 이미 다른 플레이어가 선택했습니다"
                    self.error_timer = 2.0
                    return False
                
                # 최종 턴 체크 (로그 포함)
                if self.current_turn_player_id != self.local_player_id:
                    self.error_message = "턴이 변경되었습니다. 다시 시도해주세요."
                    self.error_timer = 2.0
                    self.logger.error(f"최종 턴 체크 실패: 현재 턴={self.current_turn_player_id}, 로컬 플레이어={self.local_player_id}")
                    # 메뉴 재생성 (턴 정보 업데이트)
                    self._create_job_menu()
                    return False
                
                # 파티 멤버 추가
                member = PartyMember(
                    job_id=job['id'],
                    job_name=job['name'],
                    character_name="",
                    stats=job['stats'],
                    selected_traits=[],
                    player_id=self.local_player_id  # 로컬 플레이어의 캐릭터로 설정
                )
                self.party.append(member)
                
                # 네트워크로 직업 선택 전송
                self._send_job_selected(job['id'])
                
                self.logger.info(f"직업 선택 성공: {job['name']} ({job['id']}) - 현재 턴={self.current_turn_player_id}, 로컬 플레이어={self.local_player_id}")
                
                # 이름 입력으로 이동
                self.current_slot = len(self.party) - 1
                self.state = "name_input"
                self._create_name_input()
                
                # 모든 캐릭터 선택 완료 확인
                # (직업 선택 완료는 모든 캐릭터의 특성까지 선택 완료되었을 때 보냄)
                
                return False
        
        elif action == GameAction.CANCEL:
            # 이전 슬롯으로 돌아가기 (턴 체크 없음 - 취소는 항상 가능)
            play_sfx("ui", "cursor_cancel")
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
        
        return False
    
    def _handle_name_input(self, action: GameAction, key_event: Optional[tcod.event.KeyDown] = None) -> bool:
        """이름 입력 상태 입력 처리"""
        if not self.name_input:
            return False
        
        # 엔터 키(Return) 확인
        if key_event and key_event.sym == tcod.event.KeySym.RETURN:
            # 엔터 키로 입력 완료
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
        
        # 일반 키 입력 처리 (엔터 키가 아닐 때만)
        if key_event and key_event.sym != tcod.event.KeySym.RETURN:
            self.name_input.handle_input(action, key_event)
        
        return False
    
    def _handle_trait_select(self, action: GameAction, key_event: Optional[tcod.event.KeyDown] = None) -> bool:
        """특성 선택 상태 입력 처리"""
        if not self.trait_menu:
            self._create_trait_menu()
        
        if not self.party or self.current_slot >= len(self.party):
            return False
        
        member = self.party[self.current_slot]
        selected_traits = member.selected_traits or []
        
        # 특성 선택이 완료된 상태에서 엔터를 누르면 다음 캐릭터로 넘어가기
        if (action == GameAction.CONFIRM) or (key_event and key_event.sym == tcod.event.KeySym.RETURN):
            # 이미 2개 선택 완료된 상태에서 엔터를 누르면 다음 캐릭터로
            if len(selected_traits) >= 2:
                # 다음 캐릭터로 또는 완료
                if len(self.party) < self.character_allocation:
                    # 다음 캐릭터 선택
                    self.current_slot = len(self.party)
                    self.state = "job_select"
                    self._create_job_menu()
                    self.logger.info(f"다음 캐릭터 선택으로 이동")
                else:
                    # 모든 캐릭터 선택 완료 (직업 선택 완료 메시지 전송)
                    self._send_job_selection_complete()
                    # completed는 _send_job_selection_complete에서 설정됨 (호스트는 모든 플레이어 완료 시, 클라이언트는 호스트 게임 시작 대기)
                    self.logger.info("로컬 플레이어의 모든 캐릭터 선택 완료 (특성 선택 완료 - CANCEL)")
                    # 호스트는 다른 플레이어 대기, 클라이언트는 호스트 게임 시작 대기
                    return False
                return False
            
            # 특성 선택/해제
            selected = self.trait_menu.get_selected_item()
            if selected and selected.value:
                trait = selected.value
                # trait은 딕셔너리
                trait_id = trait.get('id') if isinstance(trait, dict) else trait
                
                if not trait_id:
                    self.logger.warning(f"특성 ID가 없습니다: {trait}")
                    return False
                
                if trait_id in selected_traits:
                    # 선택 해제
                    selected_traits.remove(trait_id)
                    self.logger.info(f"특성 선택 해제: {trait_id}")
                elif len(selected_traits) < 2:
                    # 선택
                    selected_traits.append(trait_id)
                    self.logger.info(f"특성 선택: {trait_id} ({len(selected_traits)}/2)")
                else:
                    # 이미 2개 선택됨
                    self.logger.warning(f"이미 2개의 특성을 선택했습니다")
                    return False
                
                # 선택 상태 업데이트
                member.selected_traits = list(selected_traits)  # 리스트로 저장
                
                # 메뉴 갱신 (선택 표시 업데이트)
                self._create_trait_menu()
                
                # 2개 선택 완료 시 자동으로 다음 캐릭터로 넘어가기
                if len(selected_traits) >= 2:
                    self.logger.info(f"특성 선택 완료: {member.character_name} - {', '.join(selected_traits)}")
                    # 자동으로 다음 캐릭터로 넘어가기
                    if len(self.party) < self.character_allocation:
                        # 다음 캐릭터 선택
                        self.current_slot = len(self.party)
                        self.state = "job_select"
                        self._create_job_menu()
                        self.logger.info(f"자동으로 다음 캐릭터 선택으로 이동")
                    else:
                        # 모든 캐릭터 선택 완료 (직업 선택 완료 메시지 전송)
                        self._send_job_selection_complete()
                        # completed는 _send_job_selection_complete에서 설정됨 (호스트는 모든 플레이어 완료 시, 클라이언트는 호스트 게임 시작 대기)
                        self.logger.info("로컬 플레이어의 모든 캐릭터 선택 완료")
                        # 호스트는 다른 플레이어 대기, 클라이언트는 호스트 게임 시작 대기
                        if self.is_host:
                            # 호스트는 다른 플레이어들이 완료할 때까지 대기 (completed는 _send_job_selection_complete에서 설정)
                            return False
                        else:
                            # 클라이언트는 호스트가 게임을 시작할 때까지 대기 (completed는 False로 유지)
                            return False
            
            return False
        
        elif action == GameAction.CANCEL:
            # 다음 캐릭터로 또는 완료
            if len(self.party) < self.character_allocation:
                # 다음 캐릭터 선택
                self.current_slot = len(self.party)
                self.state = "job_select"
                self._create_job_menu()
            else:
                # 모든 캐릭터 선택 완료 (직업 선택 완료 메시지 전송)
                self._send_job_selection_complete()
                # completed는 _send_job_selection_complete에서 설정됨 (호스트는 모든 플레이어 완료 시, 클라이언트는 호스트 게임 시작 대기)
                self.logger.info("로컬 플레이어의 모든 캐릭터 선택 완료 (CANCEL)")
                # 호스트는 다른 플레이어 대기, 클라이언트는 호스트 게임 시작 대기
                return False
        
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
            # 비동기 브로드캐스트
            import asyncio
            if self.is_host:
                server_loop = getattr(self.network_manager, '_server_event_loop', None)
                if server_loop and server_loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.network_manager.broadcast(message),
                        server_loop
                    )
            else:
                client_loop = getattr(self.network_manager, '_client_event_loop', None)
                if client_loop and client_loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.network_manager.send(message),
                        client_loop
                    )
        except Exception as e:
            self.logger.error(f"직업 선택 메시지 전송 실패: {e}", exc_info=True)
    
    def _send_job_deselected(self, job_id: str):
        """네트워크로 직업 해제 전송"""
        try:
            message = MessageBuilder.job_deselected(
                job_id,
                self.local_player_id
            )
            # 비동기 브로드캐스트
            import asyncio
            if self.is_host:
                server_loop = getattr(self.network_manager, '_server_event_loop', None)
                if server_loop and server_loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.network_manager.broadcast(message),
                        server_loop
                    )
            else:
                client_loop = getattr(self.network_manager, '_client_event_loop', None)
                if client_loop and client_loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.network_manager.send(message),
                        client_loop
                    )
        except Exception as e:
            self.logger.error(f"직업 해제 메시지 전송 실패: {e}", exc_info=True)
    
    def _send_job_selection_complete(self):
        """직업 선택 완료 메시지 전송 (로컬 플레이어의 모든 직업 선택 완료 시)"""
        try:
            # 로컬 플레이어 완료 표시
            self.local_completed = True
            
            message = MessageBuilder.job_selection_complete(self.local_player_id)
            # 비동기 브로드캐스트
            import asyncio
            if self.is_host:
                # 호스트 자신도 완료 목록에 추가
                self.players_completed.add(self.local_player_id)
                self.logger.info(f"호스트 완료! 완료한 플레이어: {self.players_completed}, 전체 플레이어: {list(self.session.players.keys())}")
                
                server_loop = getattr(self.network_manager, '_server_event_loop', None)
                if server_loop and server_loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.network_manager.broadcast(message),
                        server_loop
                    )
                    # 호스트는 다음 턴으로 넘김 (현재 턴이 자신의 턴인 경우에만)
                    if self.current_turn_player_id == self.local_player_id:
                        self.logger.info(f"호스트 자신의 턴 완료 - 다음 턴으로 넘김")
                        self._advance_to_next_turn()
                    else:
                        self.logger.info(f"호스트 완료했지만 현재 턴이 아님 (현재 턴: {self.current_turn_player_id})")
                    
                    # 모든 플레이어가 완료했는지 확인
                    all_players = set(self.session.players.keys())
                    if all_players.issubset(self.players_completed):
                        self.logger.info("모든 플레이어의 직업 선택 완료! 호스트도 완료 처리")
                        self.completed = True
                    else:
                        self.logger.info(f"다른 플레이어 대기 중... 완료: {self.players_completed}, 전체: {all_players}")
            else:
                client_loop = getattr(self.network_manager, '_client_event_loop', None)
                if client_loop and client_loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.network_manager.send(message),
                        client_loop
                    )
        except Exception as e:
            self.logger.error(f"직업 선택 완료 메시지 전송 실패: {e}", exc_info=True)
    
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
        
        # 현재 턴 정보 (직업 선택 중일 때만)
        if self.state == "job_select":
            if self.current_turn_player_id == self.local_player_id:
                turn_msg = "▶ 현재 당신의 턴입니다"
                turn_color = Colors.UI_TEXT_SELECTED
            else:
                current_player = self.session.players.get(self.current_turn_player_id)
                player_name = current_player.player_name if current_player else "다른 플레이어"
                turn_msg = f"⏳ {player_name}의 턴입니다... (대기 중)"
                turn_color = Colors.DARK_GRAY
            
            console.print(
                self.screen_width // 2 - len(turn_msg) // 2,
                6,
                turn_msg,
                fg=turn_color
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
        
        # 호스트가 완료했지만 다른 플레이어 대기 중인 경우
        if self.is_host and self.local_completed and not self.completed:
            wait_msg = f"다른 플레이어 대기 중... ({len(self.players_completed)}/{len(self.session.players)})"
            console.print(
                self.screen_width // 2 - len(wait_msg) // 2,
                self.screen_height - 4,
                wait_msg,
                fg=Colors.UI_TEXT
            )
            # 완료하지 않은 플레이어 목록 표시
            all_players = set(self.session.players.keys())
            waiting_players = all_players - self.players_completed
            if waiting_players:
                waiting_names = [self.session.players[pid].player_name for pid in waiting_players if pid in self.session.players]
                if waiting_names:
                    waiting_text = f"대기 중: {', '.join(waiting_names)}"
                    console.print(
                        self.screen_width // 2 - len(waiting_text) // 2,
                        self.screen_height - 3,
                        waiting_text,
                        fg=Colors.DARK_GRAY
                    )
        
        # 클라이언트가 완료했지만 호스트 게임 시작 대기 중인 경우
        if not self.is_host and self.local_completed and not self.completed:
            wait_msg = "호스트가 게임을 시작할 때까지 대기 중..."
            console.print(
                self.screen_width // 2 - len(wait_msg) // 2,
                self.screen_height - 4,
                wait_msg,
                fg=Colors.UI_TEXT
            )
        
        # 안내 메시지
        if self.completed:
            help_text = "모든 플레이어의 직업 선택 완료!" if self.is_host else "준비 완료!"
        elif self.local_completed and self.is_host:
            help_text = "다른 플레이어를 기다리는 중..."
        elif self.local_completed and not self.is_host:
            help_text = "호스트가 게임을 시작할 때까지 대기 중..."
        else:
            help_text = "ESC: 취소"
        console.print(
            self.screen_width // 2 - len(help_text) // 2,
            self.screen_height - 2 if ((self.is_host and self.local_completed and not self.completed) or (not self.is_host and self.local_completed)) else self.screen_height - 3,
            help_text,
            fg=Colors.UI_TEXT
        )
    
    def get_party(self) -> Optional[List[PartyMember]]:
        """선택된 파티 반환"""
        # 호스트는 모든 플레이어 완료 시, 클라이언트는 로컬 플레이어 완료 시 파티 반환
        if (self.completed or (not self.is_host and self.local_completed)) and len(self.party) == self.character_allocation:
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
    
    import time
    last_connection_check = time.time()
    connection_check_interval = 1.0  # 1초마다 연결 상태 확인
    last_turn_broadcast = time.time()
    turn_broadcast_interval = 2.0  # 2초마다 턴 정보 브로드캐스트 (호스트만)
    
    while True:
        current_time = time.time()
        
        # 호스트가 주기적으로 턴 정보 브로드캐스트 (클라이언트 동기화 보장)
        if is_host and current_time - last_turn_broadcast >= turn_broadcast_interval:
            last_turn_broadcast = current_time
            if setup.current_turn_player_id and setup.player_order:
                setup._broadcast_turn_change()
        
        # 연결 상태 확인 (주기적으로)
        if current_time - last_connection_check >= connection_check_interval:
            last_connection_check = current_time
            
            # 호스트 연결 상태 확인 (클라이언트만)
            if not is_host and network_manager:
                from src.multiplayer.network import ConnectionState
                if network_manager.connection_state == ConnectionState.DISCONNECTED:
                    setup.logger.error("호스트 연결이 끊어졌습니다!")
                    setup.cancelled = True
                    setup.error_message = "호스트 연결이 끊어졌습니다. 게임을 종료합니다."
                    setup.error_timer = 5.0
            
            # 세션에서 호스트가 제거되었는지 확인
            if session:
                host_id = getattr(session, 'host_id', None)
                if host_id and host_id not in session.players:
                    setup.logger.error("세션에서 호스트가 제거되었습니다!")
                    setup.cancelled = True
                    setup.error_message = "호스트가 게임을 나갔습니다. 게임을 종료합니다."
                    setup.error_timer = 5.0
                # 호스트가 나갔는지 확인 (호스트 자신인 경우)
                elif is_host and local_player_id not in session.players:
                    setup.logger.error("호스트가 세션에서 제거되었습니다!")
                    setup.cancelled = True
                    setup.error_message = "연결이 끊어졌습니다. 게임을 종료합니다."
                    setup.error_timer = 5.0
        
        # 플레이어가 나갔거나 취소되었는지 확인
        if setup.cancelled:
            return None
        
        # 호스트가 모든 플레이어 완료를 확인했는지 체크 (비동기적으로 설정될 수 있음)
        # 메시지 핸들러에서 completed가 True로 설정될 수 있으므로 매 프레임 체크
        if setup.is_host and setup.completed:
            party = setup.get_party()
            if party:
                setup.logger.info(f"모든 플레이어 완료 확인! 파티 반환: {len(party)}명")
                # 패시브는 호스트가 선택 (나중에 별도 처리)
                return (party, [])
            else:
                setup.logger.warning(f"completed=True이지만 get_party()가 None 반환. party 길이: {len(setup.party)}, allocation: {setup.character_allocation}")
        
        # 클라이언트가 완료했는지 체크 (호스트 게임 시작 대기 - main.py에서 처리)
        if not setup.is_host and setup.local_completed:
            party = setup.get_party()
            if party:
                setup.logger.info(f"클라이언트 완료! 파티 반환: {len(party)}명 (호스트 게임 시작 대기)")
                return (party, [])
        
        # 렌더링
        setup.render(console)
        context.present(console)
        
        # 입력 처리
        for event in tcod.event.wait(timeout=0.05):
            if isinstance(event, tcod.event.Quit):
                return None
            
            context.convert_event(event)
            action = unified_input_handler.process_tcod_event(event)
            
            key_event = event if isinstance(event, tcod.event.KeyDown) else None
            
            if action or key_event:
                if setup.handle_input(action, key_event):
                    if setup.cancelled:
                        return None
                    # 호스트만 completed가 True일 때 반환 (모든 플레이어 완료)
                    # 클라이언트는 local_completed가 True일 때 반환 (호스트 게임 시작 대기 - main.py에서 처리)
                    elif setup.completed and setup.is_host:
                        party = setup.get_party()
                        if party:
                            # 패시브는 호스트가 선택 (나중에 별도 처리)
                            return (party, [])
                    elif setup.local_completed and not setup.is_host:
                        # 클라이언트는 완료했으면 반환 (main.py에서 호스트 게임 시작 메시지 대기)
                        party = setup.get_party()
                        if party:
                            return (party, [])

