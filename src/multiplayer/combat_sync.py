"""
전투 동기화 시스템

멀티플레이에서 전투 액션 실행과 상태 업데이트를 동기화합니다.
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Set, Tuple
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.network import NetworkManager
from src.multiplayer.protocol import MessageType, MessageBuilder, NetworkMessage
from src.multiplayer.config import MultiplayerConfig
from src.combat.combat_manager import CombatManager, ActionType, CombatState
from src.core.logger import get_logger


class CombatSyncManager:
    """전투 동기화 관리자"""
    
    def __init__(
        self,
        session: MultiplayerSession,
        network_manager: Optional[NetworkManager] = None,
        combat_manager: Optional[CombatManager] = None,
        is_host: bool = False
    ):
        """
        초기화
        
        Args:
            session: 멀티플레이 세션
            network_manager: 네트워크 관리자
            combat_manager: 전투 관리자
            is_host: 호스트 여부
        """
        self.session = session
        self.network_manager = network_manager
        self.combat_manager = combat_manager
        self.is_host = is_host
        self.logger = get_logger("multiplayer.combat_sync")

        # ATB 시스템에 호스트/클라이언트 모드 설정
        if self.combat_manager and hasattr(self.combat_manager, 'atb'):
            atb_system = self.combat_manager.atb
            if hasattr(atb_system, 'set_host_mode'):
                atb_system.set_host_mode(is_host)
                self.logger.info(f"ATB 호스트 모드 설정: {'호스트' if is_host else '클라이언트'}")

        # 주기적 상태 동기화 (호스트용)
        self._last_heartbeat_time = 0.0
        self._heartbeat_interval = 0.2  # 200ms마다 상태 브로드캐스트

        # 액션 실행 큐 (호스트용)
        self.action_queue: List[Dict[str, Any]] = []  # [{player_id, actor_id, action, timestamp}, ...]
        
        # 액션 시퀀스 번호 (순서 보장용)
        self.action_sequence = 0
        self.last_processed_sequence = -1

        # 플레이어별 행동 선택 상태 추적 (ATB 시스템용)
        self.players_selecting_action: Set[str] = set()
        
        # 타임아웃 태스크 관리 {player_id: task}
        self.timeout_tasks: Dict[str, asyncio.Task] = {}

        # CombatUI 콜백 (combat_ui.py에서 설정)
        self.on_action_selection_start_callback = None  # (actor_id, actor_name, player_id) -> None
        self.on_action_result_callback = None  # (result_data) -> None
        self.on_combat_end_callback = None  # (result, rewards) -> None
        self.on_remote_action_executed_callback = None  # (actor, result) -> None  호스트: 원격 액션 실행 완료

        # 네트워크 메시지 핸들러 등록
        if self.network_manager:
            self._register_handlers()
    
    async def send_heartbeat(self):
        """
        주기적 전투 상태 브로드캐스트 (호스트 전용, 200ms 간격)

        호스트가 매 프레임 호출하며, 200ms 간격으로 전체 전투 상태를
        모든 클라이언트에게 브로드캐스트합니다. 이를 통해:
        - ATB 게이지가 호스트와 동기화됨
        - HP/BRV/상태이상이 실시간 반영됨
        - 클라이언트 간 상태 불일치 최소화
        """
        if not self.is_host or not self.network_manager or not self.combat_manager:
            return

        current_time = time.time()
        if current_time - self._last_heartbeat_time < self._heartbeat_interval:
            return

        self._last_heartbeat_time = current_time

        try:
            state_snapshot = self._get_combat_state_snapshot()
            if state_snapshot:
                state_message = MessageBuilder.state_update({
                    "combat_state": state_snapshot,
                    "heartbeat": True,
                    "timestamp": current_time
                })
                await self.network_manager.broadcast(state_message)
        except Exception as e:
            self.logger.error(f"하트비트 브로드캐스트 실패: {e}", exc_info=True)

    def _get_network_event_loop(self):
        """네트워크 매니저의 이벤트 루프를 가져옵니다 (동기→비동기 브릿지용)"""
        if not self.network_manager:
            return None
        loop = getattr(self.network_manager, '_server_event_loop', None)
        if loop is None:
            loop = getattr(self.network_manager, '_client_event_loop', None)
        if loop and loop.is_running():
            return loop
        return None

    def _schedule_async(self, coro):
        """동기 컨텍스트에서 코루틴을 네트워크 이벤트 루프에 스케줄링"""
        import asyncio
        # 1차: 네트워크 매니저의 이벤트 루프 (별도 스레드)
        event_loop = self._get_network_event_loop()
        if event_loop:
            asyncio.run_coroutine_threadsafe(coro, event_loop)
            return True
        # 2차: 현재 실행 중인 async 루프 (async 컨텍스트에서 호출된 경우)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
            return True
        except RuntimeError:
            return False

    def send_heartbeat_sync(self):
        """
        send_heartbeat의 동기 래퍼 (combat_ui에서 호출용)

        네트워크 매니저의 이벤트 루프를 통해 비동기 하트비트를 스케줄링합니다.
        동기 전투 루프에서도 안정적으로 동작합니다.
        """
        try:
            self._schedule_async(self.send_heartbeat())
        except Exception as e:
            self.logger.error(f"하트비트 동기 래퍼 실패: {e}", exc_info=True)

    def _register_handlers(self):
        """네트워크 메시지 핸들러 등록"""
        try:
            if not self.network_manager:
                return

            # 전투 액션 메시지 핸들러
            self.network_manager.register_handler(
                MessageType.COMBAT_ACTION,
                self._handle_combat_action
            )

            # 플레이어 연결 끊김 핸들러 (호스트/클라이언트 모두)
            self.network_manager.register_handler(
                MessageType.PLAYER_LEFT,
                self._handle_player_left
            )

            # 전투 상태 업데이트 메시지 핸들러 (클라이언트만)
            if not self.is_host:
                self.network_manager.register_handler(
                    MessageType.STATE_UPDATE,
                    self._handle_combat_state_update
                )

            # 액션 선택 시작 핸들러 (클라이언트만)
            if not self.is_host:
                self.network_manager.register_handler(
                    MessageType.ACTION_SELECTION_START,
                    self._handle_action_selection_start
                )

            # 액션 결과 핸들러 (클라이언트만)
            if not self.is_host:
                self.network_manager.register_handler(
                    MessageType.ACTION_RESULT,
                    self._handle_action_result
                )

            # 전투 종료 핸들러 (클라이언트만)
            if not self.is_host:
                self.network_manager.register_handler(
                    MessageType.COMBAT_END,
                    self._handle_combat_end
                )

            # 호스트 마이그레이션 핸들러 (모든 노드)
            self.network_manager.register_handler(
                MessageType.HOST_MIGRATED,
                self._handle_host_migrated
            )

            # 전체 상태 동기화 응답 핸들러 (클라이언트 - 재연결 시)
            if not self.is_host:
                self.network_manager.register_handler(
                    MessageType.FULL_STATE_SYNC,
                    self._handle_combat_state_update
                )

            # 전투 상태 요청 핸들러 (호스트용 - 재연결 클라이언트 지원)
            self.network_manager.register_handler(
                MessageType.REQUEST_STATE_SYNC,
                self._handle_request_state_sync
            )
        except Exception as e:
            self.logger.error(f"네트워크 핸들러 등록 실패: {e}", exc_info=True)

    async def _handle_host_migrated(self, message: NetworkMessage, sender_id: Optional[str] = None):
        """호스트 마이그레이션 처리 (정책상 비활성화, t_7846bbe3 §5.1)

        P2P 토폴로지에서 진짜 host migration은 불가능하므로(설계 §1), 수신 시
        no-op으로 강등한다. 로컬 플래그 전환은 수행하지 않는다.
        """
        new_host_id = message.data.get("new_host_id")
        self.logger.warning(
            f"HOST_MIGRATED 수신 (비활성화 정책 — 무시): new_host_id={new_host_id}. "
            "P2P 토폴로지에서는 host migration이 지원되지 않습니다."
        )

    async def _handle_request_state_sync(self, message: NetworkMessage, sender_id: Optional[str] = None):
        """
        전투 상태 동기화 요청 처리 (호스트용 - 재연결 클라이언트 지원)
        """
        if not self.is_host or not self.combat_manager or not self.network_manager:
            return

        self.logger.info(f"전투 상태 동기화 요청 수신: {sender_id}")
        try:
            state_snapshot = self._get_combat_state_snapshot()
            if state_snapshot:
                sync_message = NetworkMessage(
                    type=MessageType.FULL_STATE_SYNC,
                    data={
                        "combat_state": state_snapshot,
                        "timestamp": time.time()
                    }
                )
                if sender_id and sender_id in self.network_manager.clients:
                    data = sync_message.to_json().encode('utf-8')
                    await self.network_manager._send_raw(data, self.network_manager.clients[sender_id])
                    self.logger.info(f"전체 전투 상태 전송 완료: {sender_id}")
        except Exception as e:
            self.logger.error(f"전투 상태 동기화 응답 실패: {e}", exc_info=True)
    
    async def send_action_request(
        self,
        player_id: str,
        actor: Any,
        action_type: ActionType,
        target: Optional[Any] = None,
        skill: Optional[Any] = None,
        **kwargs
    ) -> bool:
        """
        액션 요청 전송 (클라이언트 → 호스트)
        
        Args:
            player_id: 플레이어 ID
            actor: 행동자 캐릭터
            action_type: 행동 타입
            target: 대상 캐릭터
            skill: 스킬 (있는 경우)
            **kwargs: 추가 옵션
            
        Returns:
            전송 성공 여부
        """
        try:
            if self.is_host:
                # 호스트는 직접 처리
                return await self._process_action_locally(player_id, actor, action_type, target, skill, **kwargs)
            
            if not self.network_manager:
                self.logger.warning("네트워크 관리자가 없어 액션 요청을 보낼 수 없습니다")
                return False
            
            # 액션 정보 직렬화
            action_data = self._serialize_action(action_type, target, skill, **kwargs)
            
            # 액터 ID 추출
            actor_id = self._get_character_id(actor)
            if not actor_id:
                self.logger.warning(f"액터 ID를 찾을 수 없음: {actor}")
                return False
            
            # 액션 요청 메시지 생성
            message = MessageBuilder.combat_action(
                player_id=player_id,
                actor_id=actor_id,
                action=action_data
            )
            
            # 호스트에게 전송
            await self.network_manager.send(message)
            
            # 행동 선택 시작 (ATB 감소용) 및 타임아웃 설정
            self._set_player_selecting(player_id, True)
            self._start_timeout_task(player_id)
            
            self.logger.debug(f"액션 요청 전송: {player_id} -> {actor_id} ({action_type.value})")
            return True
        except Exception as e:
            self.logger.error(f"액션 요청 전송 실패: {e}", exc_info=True)
            self._set_player_selecting(player_id, False)  # 실패 시 UI 잠금 해제
            return False

    async def request_action(self, player_id: str, actor_id: str, action_data: Dict[str, Any]) -> bool:
        """
        레거시 UI 호환용 액션 요청 래퍼.

        Args:
            player_id: 플레이어 ID
            actor_id: 행동자 ID
            action_data: 직렬화된 액션 데이터

        Returns:
            처리 성공 여부
        """
        try:
            actor = self._find_character_by_id(actor_id)
            if not actor:
                self.logger.warning(f"액션 요청 실패: 액터를 찾을 수 없음 ({actor_id})")
                return False

            action_type, target, skill, kwargs = self._deserialize_action(action_data)
            if not action_type:
                self.logger.warning(f"액션 요청 실패: 액션 역직렬화 실패 ({action_data})")
                return False

            return await self.send_action_request(
                player_id=player_id,
                actor=actor,
                action_type=action_type,
                target=target,
                skill=skill,
                **kwargs
            )
        except Exception as e:
            self.logger.error(f"레거시 액션 요청 처리 실패: {e}", exc_info=True)
            return False
            
    def _start_timeout_task(self, player_id: str, timeout: float = 10.0):
        """액션 응답 타임아웃 태스크 시작"""
        # 기존 태스크 취소
        if player_id in self.timeout_tasks:
            self.timeout_tasks[player_id].cancel()
            
        async def timeout_coro():
            try:
                await asyncio.sleep(timeout)
                # 타임아웃 발생 시 처리
                self.logger.warning(f"액션 요청 타임아웃: {player_id}")
                self._set_player_selecting(player_id, False)
                
                # 에러 메시지 표시 (UI가 있다면)
                # event_bus.publish(Events.ERROR_MESSAGE, {"message": "서버 응답 시간 초과"})
                
            except asyncio.CancelledError:
                pass # 정상 취소
            finally:
                if player_id in self.timeout_tasks:
                    del self.timeout_tasks[player_id]

        # 루프 확인 및 태스크 생성
        try:
            loop = asyncio.get_running_loop()
            self.timeout_tasks[player_id] = loop.create_task(timeout_coro())
        except RuntimeError:
            self.logger.warning("이벤트 루프가 없어 타임아웃 태스크를 시작할 수 없습니다.")

    def _cancel_timeout_task(self, player_id: str):
        """액션 응답 타임아웃 태스크 취소"""
        if player_id in self.timeout_tasks:
            self.timeout_tasks[player_id].cancel()
            del self.timeout_tasks[player_id]
    
    async def _handle_combat_action(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """
        전투 액션 메시지 처리 (호스트)
        
        Args:
            message: 전투 액션 메시지
            sender_id: 발신자 ID
        """
        try:
            if not self.is_host:
                return
            
            if not self.combat_manager:
                self.logger.warning("전투 관리자가 없어 액션을 처리할 수 없습니다")
                return
            
            # sender-bound 인가: WS 연결에서 파생된 sender_id가 진짜 원천.
            # payload player_id가 sender와 불일치하면 스푸핑 시도이므로 거부.
            player_id = message.resolve_sender_player_id(sender_id)
            if not player_id:
                self.logger.warning(
                    f"COMBAT_ACTION 스푸핑 의심 거부: sender={sender_id}, "
                    f"payload player_id={message.player_id}"
                )
                return
            
            # 액션 데이터 추출
            action_data = message.data.get("action", {})
            actor_id = message.data.get("actor_id")
            
            if not actor_id:
                self.logger.warning("액션 메시지에 액터 ID가 없습니다")
                return
            
            # 액터 찾기
            actor = self._find_character_by_id(actor_id)
            if not actor:
                self.logger.warning(f"액터를 찾을 수 없음: {actor_id}")
                return
            
            # 플레이어 소유 확인
            actor_player_id = self._get_player_id_from_character(actor)
            if actor_player_id != player_id:
                self.logger.warning(
                    f"플레이어 {player_id}가 소유하지 않은 캐릭터 {actor_id} 액션 시도"
                )
                return
            
            # 액션 역직렬화
            action_type, target, skill, kwargs = self._deserialize_action(action_data)
            
            # 액션 실행 및 브로드캐스트
            result = await self._execute_and_broadcast_action(
                player_id, actor, action_type, target, skill, **kwargs
            )

            # 행동 선택 완료 (ATB 감소 해제)
            self._set_player_selecting(player_id, False)

            # 호스트 UI에 원격 액션 실행 완료 콜백 (WAITING_REMOTE_ACTION 해제)
            if self.on_remote_action_executed_callback:
                try:
                    self.on_remote_action_executed_callback(actor, result)
                except Exception as cb_e:
                    self.logger.error(f"원격 액션 실행 콜백 실패: {cb_e}", exc_info=True)

        except Exception as e:
            self.logger.error(f"전투 액션 처리 실패: {e}", exc_info=True)

    async def _handle_player_left(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """
        플레이어 연결 끊김 처리 (전투 중)

        연결이 끊긴 플레이어의 캐릭터를 전투에서 제거하고
        해당 플레이어의 행동 대기 상태를 해제합니다.

        Args:
            message: PLAYER_LEFT 메시지
            sender_id: 발신자 ID
        """
        try:
            left_player_id = message.resolve_sender_player_id(sender_id)
            if not left_player_id:
                self.logger.warning(
                    f"PLAYER_LEFT 스푸핑 의심 거부: sender={sender_id}, "
                    f"payload player_id={message.player_id}"
                )
                return

            self.logger.info(f"전투 중 플레이어 연결 끊김: {left_player_id}")

            # 1. 해당 플레이어의 행동 선택 상태 해제 (무한 대기 방지)
            self._set_player_selecting(left_player_id, False)

            # 2. 타임아웃 태스크 취소
            self._cancel_timeout_task(left_player_id)

            # 3. 호스트인 경우: 해당 플레이어의 캐릭터를 전투에서 제거
            if self.is_host and self.combat_manager:
                allies_to_remove = []

                if hasattr(self.combat_manager, 'allies'):
                    for ally in self.combat_manager.allies:
                        ally_player_id = self._get_player_id_from_character(ally)
                        if ally_player_id == left_player_id:
                            allies_to_remove.append(ally)

                for ally in allies_to_remove:
                    try:
                        self.combat_manager.allies.remove(ally)
                        ally_name = getattr(ally, 'name', 'Unknown')
                        self.logger.info(
                            f"연결 끊긴 플레이어의 캐릭터 전투에서 제거: {ally_name}"
                        )

                        # ATB 게이지 제거
                        if hasattr(self.combat_manager, 'atb'):
                            atb = self.combat_manager.atb
                            if hasattr(atb, 'remove_gauge'):
                                atb.remove_gauge(ally)
                            elif hasattr(atb, 'gauges'):
                                atb.gauges.pop(ally, None)
                    except Exception as e:
                        self.logger.error(f"캐릭터 제거 실패: {e}", exc_info=True)

                # Party 객체 갱신 (남은 아군으로 재생성)
                if allies_to_remove and hasattr(self.combat_manager, 'party'):
                    try:
                        from src.character.party import Party
                        self.combat_manager.party = Party(list(self.combat_manager.allies))
                    except Exception as e:
                        self.logger.error(f"Party 객체 갱신 실패: {e}", exc_info=True)

                # 변경사항 브로드캐스트
                if allies_to_remove and self.network_manager:
                    try:
                        state_message = MessageBuilder.state_update({
                            "combat_state": self._get_combat_state_snapshot(),
                            "player_left": left_player_id,
                            "timestamp": time.time()
                        })
                        await self.network_manager.broadcast(state_message)
                    except Exception as e:
                        self.logger.error(f"플레이어 퇴장 브로드캐스트 실패: {e}", exc_info=True)

        except Exception as e:
            self.logger.error(f"플레이어 연결 끊김 처리 실패: {e}", exc_info=True)

    async def _process_action_locally(
        self,
        player_id: str,
        actor: Any,
        action_type: ActionType,
        target: Optional[Any] = None,
        skill: Optional[Any] = None,
        **kwargs
    ) -> bool:
        """
        액션 로컬 처리 (호스트)
        
        Args:
            player_id: 플레이어 ID
            actor: 행동자
            action_type: 행동 타입
            target: 대상
            skill: 스킬
            **kwargs: 추가 옵션
            
        Returns:
            처리 성공 여부
        """
        try:
            if not self.combat_manager:
                return False
            
            # 행동 선택 시작
            self._set_player_selecting(player_id, True)
            
            # 액션 실행 및 브로드캐스트
            success = await self._execute_and_broadcast_action(
                player_id, actor, action_type, target, skill, **kwargs
            )
            
            # 행동 선택 완료
            self._set_player_selecting(player_id, False)
            
            return success
        except Exception as e:
            self.logger.error(f"로컬 액션 처리 실패: {e}", exc_info=True)
            self._set_player_selecting(player_id, False)
            return False
    
    async def _execute_and_broadcast_action(
        self,
        player_id: str,
        actor: Any,
        action_type: ActionType,
        target: Optional[Any] = None,
        skill: Optional[Any] = None,
        **kwargs
    ) -> bool:
        """
        액션 실행 및 브로드캐스트 (호스트)
        
        Args:
            player_id: 플레이어 ID
            actor: 행동자
            action_type: 행동 타입
            target: 대상
            skill: 스킬
            **kwargs: 추가 옵션
            
        Returns:
            실행 성공 여부
        """
        try:
            if not self.combat_manager:
                return False

            # 액션 실행
            result = self.combat_manager.execute_action(
                actor=actor,
                action_type=action_type,
                target=target,
                skill=skill,
                **kwargs
            )

            # ATB 소비 보장: execute_action 내부에서 소비되지 않은 경우 명시적으로 소비
            if hasattr(self.combat_manager, 'atb'):
                gauge = self.combat_manager.atb.get_gauge(actor)
                if gauge and gauge.can_act:
                    # ATB가 아직 가득 차 있다면 소비되지 않은 것
                    self.combat_manager.atb.consume_atb(actor)
                    self.logger.debug(f"ATB 명시적 소비 (멀티플레이 보장): {getattr(actor, 'name', 'Unknown')}")

            # 도망 성공 시 전체 도망 브로드캐스트
            if (isinstance(result, dict) and result.get("action") == "flee"
                    and result.get("success") and self.network_manager):
                flee_message = MessageBuilder.state_update({
                    "flee_result": {
                        "success": True,
                        "player_id": player_id,
                        "all_allies_fled": result.get("all_allies_fled", False)
                    },
                    "combat_state": self._get_combat_state_snapshot(),
                    "timestamp": time.time()
                })
                await self.network_manager.broadcast(flee_message)
                self.logger.info(f"도망 성공 브로드캐스트: {player_id}")

            # 모든 클라이언트에게 액션 결과 브로드캐스트
            if self.network_manager:
                # 시퀀스 증가 (호스트 authoritative 순서)
                self.action_sequence += 1
                sequence = self.action_sequence

                # 액션 결과 직렬화
                action_result = self._serialize_action_result(
                    player_id, actor, action_type, target, skill, result, sequence=sequence, **kwargs
                )
                
                # 상태 업데이트 메시지 생성 및 브로드캐스트
                from src.multiplayer.protocol import MessageBuilder
                state_message = MessageBuilder.state_update({
                    "combat_action": action_result,
                    "combat_state": self._get_combat_state_snapshot(),
                    "timestamp": time.time()
                })
                
                await self.network_manager.broadcast(state_message)
            
            self.logger.debug(
                f"액션 실행 및 브로드캐스트: {player_id} -> {getattr(actor, 'name', 'Unknown')} "
                f"({action_type.value})"
            )
            
            return result.get("success", False) if isinstance(result, dict) else True
        except Exception as e:
            self.logger.error(f"액션 실행 및 브로드캐스트 실패: {e}", exc_info=True)
            return False
    
    async def _handle_combat_state_update(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """
        전투 상태 업데이트 메시지 처리 (클라이언트)
        
        Args:
            message: 상태 업데이트 메시지
            sender_id: 발신자 ID (호스트)
        """
        try:
            if self.is_host:
                return
            
            if not self.combat_manager:
                return
            
            data = message.data.get("data", {})

            # 도망 결과 처리 (모든 클라이언트)
            flee_result = data.get("flee_result")
            if flee_result and flee_result.get("success"):
                self.logger.info(
                    f"도망 결과 수신: 플레이어 {flee_result.get('player_id')} 도망 성공"
                )
                if self.combat_manager:
                    self.combat_manager.state = CombatState.FLED
                    self.logger.info("전체 아군 도망 처리 완료 (클라이언트)")

            combat_action = data.get("combat_action")

            if combat_action:
                sequence = combat_action.get("sequence")
                if isinstance(sequence, int):
                    if sequence <= self.last_processed_sequence:
                        self.logger.debug(f"이미 처리한 액션 시퀀스 스킵: {sequence}")
                        return
                    self.last_processed_sequence = sequence

                # 액션 동기화 실행
                await self._sync_remote_action(combat_action)

                # 액션 결과를 UI 콜백으로 전달 (데미지/힐 메시지, 애니메이션 표시)
                result_data = combat_action.get("result", {})
                if result_data and self.on_action_result_callback:
                    try:
                        self.on_action_result_callback(result_data)
                    except Exception as cb_e:
                        self.logger.error(f"액션 결과 UI 콜백 실패: {cb_e}", exc_info=True)

                # 내 액션에 대한 응답이라면 타임아웃 취소 및 UI 잠금 해제
                action_player_id = combat_action.get("player_id")
                from src.multiplayer.game_mode import get_game_mode_manager
                game_mode_manager = get_game_mode_manager()
                local_player_id = getattr(game_mode_manager, 'local_player_id', None)

                if action_player_id == local_player_id:
                    self._cancel_timeout_task(local_player_id)
                    self._set_player_selecting(local_player_id, False)

                    # 로컬 플레이어 ATB 소비 보장 (호스트에서 처리됐지만 클라이언트에서 미반영될 수 있음)
                    actor_id = combat_action.get("actor_id")
                    if actor_id and self.combat_manager and hasattr(self.combat_manager, 'atb'):
                        actor = self._find_character_by_id(actor_id)
                        if actor:
                            gauge = self.combat_manager.atb.get_gauge(actor)
                            if gauge and gauge.can_act:
                                self.combat_manager.atb.consume_atb(actor)
                                self.logger.debug(
                                    f"로컬 플레이어 ATB 소비 보장: "
                                    f"{getattr(actor, 'name', 'Unknown')}"
                                )

            # 전투 상태 스냅샷 동기화
            combat_state = data.get("combat_state")
            if combat_state:
                self._sync_combat_state(combat_state)
            
        except Exception as e:
            self.logger.error(f"전투 상태 업데이트 처리 실패: {e}", exc_info=True)
    
    async def _sync_remote_action(self, action_data: Dict[str, Any]):
        """
        원격 액션 동기화 실행 (클라이언트)
        
        Args:
            action_data: 액션 데이터
        """
        try:
            if not self.combat_manager:
                return
            
            # 액션 데이터에서 정보 추출
            player_id = action_data.get("player_id")
            actor_id = action_data.get("actor_id")
            action_type_str = action_data.get("action_type")
            result = action_data.get("result", {})
            
            # 액터 찾기
            actor = self._find_character_by_id(actor_id)
            if not actor:
                self.logger.warning(f"동기화할 액터를 찾을 수 없음: {actor_id}")
                return
            
            # 플레이어가 로컬 플레이어인지 확인 (로컬 플레이어의 액션은 이미 실행됨)
            from src.multiplayer.game_mode import get_game_mode_manager
            game_mode_manager = get_game_mode_manager()
            local_player_id = getattr(game_mode_manager, 'local_player_id', None)
            
            # 로컬 플레이어의 액션도 호스트 결과로 상태를 덮어써서 authoritative 동기화
            # (클라이언트는 로컬에서 액션을 실행하지 않으므로 호스트 결과 적용 필수)
            
            # 액션 타입 변환
            action_type = ActionType(action_type_str) if action_type_str else None

            if not action_type:
                self.logger.warning(f"알 수 없는 액션 타입: {action_type_str}")
                return

            # 원격 액션 결과를 로컬 상태에 반영
            # 호스트가 실행한 결과(HP/BRV 변동 등)를 클라이언트 측 캐릭터에 적용

            # 타겟 찾기
            target_id = action_data.get("target_id")
            target = self._find_character_by_id(target_id) if target_id else None

            # result에 포함된 상태 변화 적용
            if isinstance(result, dict):
                # HP 변동 적용
                damage = result.get("damage") or result.get("hp_damage")
                if damage and target:
                    target.current_hp = max(0, target.current_hp - damage)
                    if target.current_hp <= 0:
                        target.is_alive = False

                # BRV 변동 적용
                brv_damage = result.get("brv_damage")
                if brv_damage and target:
                    target.current_brv = max(0, getattr(target, 'current_brv', 0) - brv_damage)

                brv_stolen = result.get("brv_stolen") or result.get("brv_gain")
                if brv_stolen and actor:
                    actor.current_brv = getattr(actor, 'current_brv', 0) + brv_stolen

                # 힐링 적용
                heal_amount = result.get("heal_amount") or result.get("healing")
                if heal_amount and target:
                    max_hp = getattr(target, 'max_hp', target.current_hp + heal_amount)
                    target.current_hp = min(max_hp, target.current_hp + heal_amount)

                # MP 소비 적용
                mp_cost = result.get("mp_cost")
                if mp_cost and actor:
                    actor.current_mp = max(0, getattr(actor, 'current_mp', 0) - mp_cost)

                # BREAK 상태 적용
                is_break = result.get("is_break") or result.get("break")
                if is_break and target:
                    was_broken = getattr(target, 'is_broken', False)
                    target.is_broken = True
                    target.current_brv = 0
                    # BREAK 이벤트 로컬 발행 (ATB 게이지 리셋 등)
                    if not was_broken:
                        from src.core.event_bus import event_bus
                        event_bus.publish("brave.break", {
                            "attacker": actor,
                            "defender": target,
                            "brv_stolen": result.get("brv_stolen", 0),
                            "_synced": True
                        })

                # 사망 처리
                if result.get("target_killed") and target:
                    target.is_alive = False
                    target.current_hp = 0

                # 부활 적용 (t_ceed55de): revive_crystal/부활 스킬 결과의 hp_restored 반영.
                # 호스트가 부활시킨 대상을 클라이언트에서도 생존 상태로 복원한다.
                if result.get("revived") and target:
                    hp_restored = result.get("hp_restored")
                    if hp_restored:
                        target.current_hp = hp_restored
                    elif not getattr(target, "current_hp", 0):
                        target.current_hp = int(getattr(target, "max_hp", 100) * 0.5)
                    target.is_alive = True
                    if hasattr(target, "is_ghost"):
                        target.is_ghost = False
                    if hasattr(target, "status_effects") and hasattr(target.status_effects, "clear"):
                        target.status_effects.clear()
                    self.logger.info(
                        f"원격 부활 동기화: {getattr(target, 'name', target_id)} 부활 "
                        f"(HP: {target.current_hp})"
                    )

            # ATB 소비 (원격 액터의 ATB 리셋)
            if self.combat_manager and hasattr(self.combat_manager, 'atb'):
                self.combat_manager.atb.consume_atb(actor)

            self.logger.debug(
                f"원격 액션 동기화 완료: {player_id} -> {getattr(actor, 'name', 'Unknown')} "
                f"({action_type.value}), 결과: {list(result.keys()) if isinstance(result, dict) else result}"
            )

        except Exception as e:
            self.logger.error(f"원격 액션 동기화 실패: {e}", exc_info=True)
    
    def _sync_combat_state(self, state_data: Dict[str, Any]):
        """
        전투 상태 동기화 (클라이언트)
        
        Args:
            state_data: 상태 데이터
        """
        try:
            if not self.combat_manager:
                return
            
            # 전투원 상태 동기화
            allies_state = state_data.get("allies", [])
            enemies_state = state_data.get("enemies", [])
            
            # 적 수 동기화: 호스트에 있지만 클라이언트에 없는 적 수 맞추기
            if enemies_state and self.combat_manager:
                local_enemy_count = len(self.combat_manager.enemies)
                remote_enemy_count = len(enemies_state)
                if remote_enemy_count != local_enemy_count:
                    self.logger.warning(
                        f"적 수 불일치: 로컬={local_enemy_count}, 호스트={remote_enemy_count}"
                    )

            # 캐릭터 상태 업데이트 (HP, MP, BRV, 상태이상 등)
            for char_data in allies_state + enemies_state:
                char_id = char_data.get("id")
                if not char_id:
                    continue

                character = self._find_character_by_id(char_id)
                if not character:
                    # 인덱스 기반 ID인 경우 해당 인덱스의 캐릭터에 직접 매핑 시도
                    if char_id.startswith("enemy_") and self.combat_manager:
                        try:
                            idx = int(char_id.split("_")[1])
                            if 0 <= idx < len(self.combat_manager.enemies):
                                character = self.combat_manager.enemies[idx]
                        except (ValueError, IndexError):
                            pass
                    elif char_id.startswith("ally_") and self.combat_manager:
                        try:
                            idx = int(char_id.split("_")[1])
                            if 0 <= idx < len(self.combat_manager.allies):
                                character = self.combat_manager.allies[idx]
                        except (ValueError, IndexError):
                            pass
                if not character:
                    self.logger.debug(f"동기화 대상 캐릭터 찾기 실패: {char_id}")
                    continue
                
                # 상태 동기화
                if "current_hp" in char_data:
                    character.current_hp = char_data["current_hp"]
                if "current_mp" in char_data:
                    character.current_mp = char_data["current_mp"]
                if "current_brv" in char_data:
                    character.current_brv = char_data.get("current_brv", 0)
                if "is_alive" in char_data:
                    character.is_alive = char_data["is_alive"]
                if "is_ghost" in char_data:
                    character.is_ghost = char_data["is_ghost"]

                # BREAK 상태 동기화 (상태 변경 시 로컬 이벤트 발행하여 ATB 리셋 등 연동)
                if "is_broken" in char_data:
                    was_broken = getattr(character, 'is_broken', False)
                    character.is_broken = char_data["is_broken"]
                    # BREAK 상태로 새로 전환된 경우 로컬 이벤트 발행 (ATB 게이지 리셋 등)
                    if char_data["is_broken"] and not was_broken:
                        from src.core.event_bus import event_bus
                        event_bus.publish("brave.break", {
                            "defender": character,
                            "attacker": None,
                            "brv_stolen": 0,
                            "_synced": True  # 네트워크 동기화에 의한 이벤트 표시
                        })

                # 상태이상 동기화 (증분 방식: 기존 객체 재사용으로 콜백 보존)
                if "status_effects" in char_data and hasattr(character, 'status_manager'):
                    try:
                        from src.combat.status_effects import StatusEffect, StatusType
                        existing_effects = list(character.status_manager.status_effects)
                        remote_effects = char_data["status_effects"]

                        # 원격 상태이상을 (name, status_type) 키로 인덱싱
                        remote_map = {}
                        for eff_data in remote_effects:
                            key = (eff_data.get("name", ""), eff_data.get("status_type", ""))
                            remote_map[key] = eff_data

                        # 기존 효과 중 원격에도 있는 것은 유지하며 값만 갱신
                        new_effects = []
                        matched_keys = set()
                        for effect in existing_effects:
                            key = (effect.name, effect.status_type.value if hasattr(effect.status_type, 'value') else str(effect.status_type))
                            if key in remote_map:
                                eff_data = remote_map[key]
                                effect.duration = eff_data.get("duration", effect.duration)
                                effect.intensity = eff_data.get("intensity", effect.intensity)
                                effect.stack_count = eff_data.get("stack_count", 1)
                                new_effects.append(effect)
                                matched_keys.add(key)
                            # 원격에 없는 효과는 제거 (new_effects에 추가하지 않음)

                        # 원격에만 있는 새 효과 추가
                        for key, eff_data in remote_map.items():
                            if key not in matched_keys:
                                try:
                                    status_type = StatusType(eff_data.get("status_type", ""))
                                    effect = StatusEffect(
                                        name=eff_data.get("name", ""),
                                        status_type=status_type,
                                        duration=eff_data.get("duration", 0),
                                        intensity=eff_data.get("intensity", 1.0),
                                    )
                                    effect.stack_count = eff_data.get("stack_count", 1)
                                    new_effects.append(effect)
                                except (ValueError, TypeError):
                                    self.logger.debug(f"상태이상 동기화 스킵: {eff_data}")

                        character.status_manager.status_effects = new_effects
                    except ImportError:
                        self.logger.debug("상태이상 모듈 임포트 실패, 동기화 스킵")

                # 활성 버프 동기화
                if "active_buffs" in char_data:
                    if not hasattr(character, 'active_buffs'):
                        character.active_buffs = {}
                    character.active_buffs = char_data["active_buffs"].copy() if char_data["active_buffs"] else {}

                # ATB 게이지 동기화
                if self.combat_manager and hasattr(self.combat_manager, 'atb'):
                    gauge = self.combat_manager.atb.get_gauge(character)
                    if gauge:
                        # atb_max를 먼저 갱신한 후 current를 클램핑해야 올바른 범위가 적용됨
                        atb_max = char_data.get("atb_max")
                        if atb_max is not None:
                            try:
                                gauge.max_gauge = max(1, int(atb_max))
                            except (TypeError, ValueError):
                                self.logger.debug(f"ATB 최대치 동기화 값 무시: {atb_max}")

                        atb_current = char_data.get("atb_current")
                        if atb_current is not None:
                            try:
                                gauge.current = max(0, min(float(atb_current), gauge.max_gauge))
                            except (TypeError, ValueError):
                                self.logger.debug(f"ATB 동기화 값 무시: {atb_current}")
            
            # 전투 상태 동기화
            combat_state_str = state_data.get("combat_state")
            if combat_state_str:
                try:
                    self.combat_manager.state = CombatState(combat_state_str)
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"전투 상태 변환 실패: {combat_state_str} - {e}")
            
            # 턴 카운트 동기화
            turn_count = state_data.get("turn_count")
            if turn_count is not None:
                self.combat_manager.turn_count = turn_count
            
        except Exception as e:
            self.logger.error(f"전투 상태 동기화 실패: {e}", exc_info=True)
    
    def _set_player_selecting(self, player_id: str, is_selecting: bool):
        """
        플레이어 행동 선택 상태 설정 (ATB 시스템용)
        
        Args:
            player_id: 플레이어 ID
            is_selecting: 행동 선택 중 여부
        """
        try:
            if not player_id or not isinstance(player_id, str):
                return
            
            if is_selecting:
                self.players_selecting_action.add(player_id)
            else:
                self.players_selecting_action.discard(player_id)
            
            # ATB 시스템에 반영 (멀티플레이 ATB 시스템인 경우)
            if self.combat_manager and hasattr(self.combat_manager, 'atb'):
                atb_system = self.combat_manager.atb
                if hasattr(atb_system, 'set_player_selecting'):
                    atb_system.set_player_selecting(player_id, is_selecting)
        except Exception as e:
            self.logger.error(f"플레이어 선택 상태 설정 실패: {e}", exc_info=True)
    
    def _serialize_action(
        self,
        action_type: ActionType,
        target: Optional[Any] = None,
        skill: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        액션 직렬화
        
        Args:
            action_type: 행동 타입
            target: 대상
            skill: 스킬
            **kwargs: 추가 옵션
            
        Returns:
            직렬화된 액션 데이터
        """
        try:
            action_data = {
                "action_type": action_type.value if hasattr(action_type, 'value') else str(action_type),
                "timestamp": time.time()
            }
            
            # 타겟 ID
            if target:
                target_id = self._get_character_id(target)
                if target_id:
                    action_data["target_id"] = target_id
            
            # 스킬 ID
            if skill:
                skill_id = getattr(skill, 'id', None) or getattr(skill, 'skill_id', None)
                if skill_id:
                    action_data["skill_id"] = skill_id
                skill_name = getattr(skill, 'name', None)
                if skill_name:
                    action_data["skill_name"] = skill_name
            
            # 아이템 정보
            if "item" in kwargs:
                item = kwargs["item"]
                item_id = getattr(item, 'id', None)
                if item_id:
                    action_data["item_id"] = item_id
                item_name = getattr(item, 'name', None)
                if item_name:
                    action_data["item_name"] = item_name
            
            if "item_index" in kwargs:
                action_data["item_index"] = kwargs["item_index"]
            
            return action_data
        except Exception as e:
            self.logger.error(f"액션 직렬화 실패: {e}", exc_info=True)
            return {}
    
    def _deserialize_action(self, action_data: Dict[str, Any]) -> Tuple[ActionType, Optional[Any], Optional[Any], Dict[str, Any]]:
        """
        액션 역직렬화
        
        Args:
            action_data: 직렬화된 액션 데이터
            
        Returns:
            (action_type, target, skill, kwargs)
        """
        try:
            # 액션 타입
            action_type_str = action_data.get("action_type")
            action_type = ActionType(action_type_str) if action_type_str else None
            
            if not action_type:
                raise ValueError(f"알 수 없는 액션 타입: {action_type_str}")
            
            # 타겟 찾기
            target = None
            target_id = action_data.get("target_id")
            if target_id:
                target = self._find_character_by_id(target_id)

            # 스킬 찾기
            skill = None
            skill_id = action_data.get("skill_id")
            if skill_id:
                # 스킬 시스템에서 스킬 찾기
                from src.character.skills.skill_manager import get_skill_manager
                skill_manager = get_skill_manager()
                skill = skill_manager.get_skill(skill_id)
            
            # 추가 옵션
            kwargs = {}
            if "item_id" in action_data:
                # 아이템은 전투 관리자의 인벤토리에서 찾기
                if self.combat_manager and hasattr(self.combat_manager, 'inventory') and self.combat_manager.inventory:
                    inventory = self.combat_manager.inventory
                    item_id = action_data["item_id"]
                    
                    # 인벤토리에서 아이템 슬롯 인덱스 찾기
                    slot_index = inventory.find_item_by_id(item_id)
                    if slot_index is not None:
                        item = inventory.get_item(slot_index)
                        if item:
                            kwargs["item"] = item
                            self.logger.debug(f"아이템 찾기 성공: {item_id} (슬롯 {slot_index})")
                        else:
                            self.logger.warning(f"아이템 슬롯 {slot_index}에서 아이템을 찾을 수 없음: {item_id}")
                    else:
                        self.logger.warning(f"인벤토리에서 아이템을 찾을 수 없음: {item_id}")
            
            if "item_index" in action_data:
                kwargs["item_index"] = action_data["item_index"]
            
            return action_type, target, skill, kwargs
        except Exception as e:
            self.logger.error(f"액션 역직렬화 실패: {e}", exc_info=True)
            return None, None, None, {}
    
    def _serialize_action_result(
        self,
        player_id: str,
        actor: Any,
        action_type: ActionType,
        target: Optional[Any],
        skill: Optional[Any],
        result: Dict[str, Any],
        sequence: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        액션 결과 직렬화
        
        Args:
            player_id: 플레이어 ID
            actor: 행동자
            action_type: 행동 타입
            target: 대상
            skill: 스킬
            result: 액션 결과
            **kwargs: 추가 옵션
            
        Returns:
            직렬화된 액션 결과
        """
        try:
            actor_id = self._get_character_id(actor)
            
            action_result = {
                "player_id": player_id,
                "actor_id": actor_id,
                "action_type": action_type.value if hasattr(action_type, 'value') else str(action_type),
                "result": result,
                "timestamp": time.time()
            }

            if sequence is not None:
                action_result["sequence"] = sequence
            
            if target:
                target_id = self._get_character_id(target)
                if target_id:
                    action_result["target_id"] = target_id
            
            if skill:
                skill_id = getattr(skill, 'id', None) or getattr(skill, 'skill_id', None)
                if skill_id:
                    action_result["skill_id"] = skill_id
            
            return action_result
        except Exception as e:
            self.logger.error(f"액션 결과 직렬화 실패: {e}", exc_info=True)
            return {}
    
    # ── Phase 3-5: 액션 선택/결과/전투 종료 핸들러 ──────────────────────

    async def send_action_selection_start(self, actor: Any, target_player_id: str):
        """
        액션 선택 시작 메시지 전송 (호스트 -> 특정 클라이언트)

        원격 플레이어의 캐릭터 턴이 되었을 때 해당 플레이어에게 행동 선택을 요청합니다.

        Args:
            actor: 행동할 캐릭터
            target_player_id: 대상 플레이어 ID
        """
        if not self.is_host or not self.network_manager:
            return

        actor_id = self._get_character_id(actor)
        actor_name = getattr(actor, 'name', '아군')
        if not actor_id:
            self.logger.warning(f"액션 선택 시작 전송 실패: 액터 ID를 찾을 수 없음")
            return

        try:
            message = MessageBuilder.action_selection_start(
                actor_id=actor_id,
                actor_name=actor_name,
                player_id=target_player_id
            )
            await self.network_manager.broadcast(message)
            self.logger.info(f"액션 선택 시작 전송: {actor_name} -> 플레이어 {target_player_id}")
        except Exception as e:
            self.logger.error(f"액션 선택 시작 전송 실패: {e}", exc_info=True)

    def send_action_selection_start_sync(self, actor: Any, target_player_id: str):
        """send_action_selection_start의 동기 래퍼 (combat_ui에서 호출용)"""
        try:
            self._schedule_async(self.send_action_selection_start(actor, target_player_id))
        except Exception as e:
            self.logger.error(f"액션 선택 시작 동기 래퍼 실패: {e}", exc_info=True)

    async def broadcast_action_result(self, actor: Any, result_data: Dict[str, Any]):
        """
        액션 실행 결과 브로드캐스트 (호스트 -> 모든 클라이언트)

        Args:
            actor: 행동한 캐릭터
            result_data: 액션 실행 결과 데이터
        """
        if not self.is_host or not self.network_manager:
            return

        actor_id = self._get_character_id(actor)
        if not actor_id:
            return

        try:
            state_snapshot = self._get_combat_state_snapshot()
            message = MessageBuilder.action_result(
                actor_id=actor_id,
                result_data=result_data,
                combat_state=state_snapshot
            )
            await self.network_manager.broadcast(message)
            self.logger.debug(f"액션 결과 브로드캐스트: {getattr(actor, 'name', 'Unknown')}")
        except Exception as e:
            self.logger.error(f"액션 결과 브로드캐스트 실패: {e}", exc_info=True)

    def broadcast_action_result_sync(self, actor: Any, result_data: Dict[str, Any]):
        """broadcast_action_result의 동기 래퍼 (combat_ui에서 호출용)"""
        try:
            self._schedule_async(self.broadcast_action_result(actor, result_data))
        except Exception as e:
            self.logger.error(f"액션 결과 브로드캐스트 동기 래퍼 실패: {e}", exc_info=True)

    async def broadcast_combat_end(self, result: str, rewards: Optional[Dict[str, Any]] = None):
        """
        전투 종료 브로드캐스트 (호스트 -> 모든 클라이언트)

        Args:
            result: 전투 결과 ("victory", "defeat", "fled")
            rewards: 보상 데이터 (승리 시)
        """
        if not self.is_host or not self.network_manager:
            return

        try:
            message = MessageBuilder.combat_end(result=result, rewards=rewards)
            await self.network_manager.broadcast(message)
            self.logger.info(f"전투 종료 브로드캐스트: {result}")
        except Exception as e:
            self.logger.error(f"전투 종료 브로드캐스트 실패: {e}", exc_info=True)

    def broadcast_combat_end_sync(self, result: str, rewards: Optional[Dict[str, Any]] = None):
        """broadcast_combat_end의 동기 래퍼 (combat_ui에서 호출용)"""
        try:
            self._schedule_async(self.broadcast_combat_end(result, rewards))
        except Exception as e:
            self.logger.error(f"전투 종료 브로드캐스트 동기 래퍼 실패: {e}", exc_info=True)

    async def _handle_action_selection_start(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """
        액션 선택 시작 메시지 처리 (클라이언트)

        호스트로부터 자신의 캐릭터 턴이 되었다는 알림을 수신합니다.

        Args:
            message: ACTION_SELECTION_START 메시지
            sender_id: 발신자 ID (호스트)
        """
        try:
            if self.is_host:
                return

            data = message.data or {}
            actor_id = data.get("actor_id")
            actor_name = data.get("actor_name", "아군")
            player_id = data.get("player_id")

            self.logger.info(f"액션 선택 시작 수신: {actor_name} (ID: {actor_id}, 플레이어: {player_id})")

            # 콜백으로 CombatUI에 알림
            if self.on_action_selection_start_callback:
                self.on_action_selection_start_callback(actor_id, actor_name, player_id)
        except Exception as e:
            self.logger.error(f"액션 선택 시작 처리 실패: {e}", exc_info=True)

    async def _handle_action_result(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """
        액션 실행 결과 메시지 처리 (클라이언트)

        호스트에서 실행된 액션 결과를 수신하여 로컬 상태에 반영합니다.

        Args:
            message: ACTION_RESULT 메시지
            sender_id: 발신자 ID (호스트)
        """
        try:
            if self.is_host:
                return

            data = message.data or {}
            result_data = data.get("result", {})
            combat_state = data.get("combat_state")

            # 전투 상태 스냅샷 동기화
            if combat_state:
                self._sync_combat_state(combat_state)

            # 콜백으로 CombatUI에 알림 (데미지/힐 메시지 표시, 애니메이션 트리거)
            if self.on_action_result_callback:
                self.on_action_result_callback(result_data)

            self.logger.debug(f"액션 결과 수신 완료: actor={data.get('actor_id')}")
        except Exception as e:
            self.logger.error(f"액션 결과 처리 실패: {e}", exc_info=True)

    async def _handle_combat_end(
        self,
        message: NetworkMessage,
        sender_id: Optional[str] = None
    ):
        """
        전투 종료 메시지 처리 (클라이언트)

        호스트에서 전투 종료를 수신하여 전투 루프를 종료합니다.

        Args:
            message: COMBAT_END 메시지
            sender_id: 발신자 ID (호스트)
        """
        try:
            if self.is_host:
                return

            data = message.data or {}
            result = data.get("result", "defeat")
            rewards = data.get("rewards")

            self.logger.info(f"전투 종료 수신: 결과={result}")

            # CombatManager 상태 갱신
            if self.combat_manager:
                try:
                    self.combat_manager.state = CombatState(result)
                except (ValueError, TypeError):
                    self.logger.warning(f"전투 상태 변환 실패: {result}, DEFEAT로 처리")
                    self.combat_manager.state = CombatState.DEFEAT

            # 콜백으로 CombatUI에 알림
            if self.on_combat_end_callback:
                self.on_combat_end_callback(result, rewards)
        except Exception as e:
            self.logger.error(f"전투 종료 처리 실패: {e}", exc_info=True)

    def apply_state_update(self, state_data: Dict[str, Any]):
        """
        클라이언트가 STATE_UPDATE 수신 시 로컬 CombatManager 상태를 동기화합니다.

        호스트의 하트비트(200ms) 또는 직접 호출을 통해 전투 상태를 갱신합니다.

        Args:
            state_data: 호스트로부터 수신한 상태 데이터
        """
        if self.is_host:
            return

        try:
            self._sync_combat_state(state_data)
        except Exception as e:
            self.logger.error(f"상태 업데이트 적용 실패: {e}", exc_info=True)

    def _get_combat_state_snapshot(self) -> Dict[str, Any]:
        """
        전투 상태 스냅샷 생성 (동기화용)

        Returns:
            전투 상태 데이터
        """
        try:
            if not self.combat_manager:
                return {}
            
            snapshot = {
                "combat_state": self.combat_manager.state.value if hasattr(self.combat_manager.state, 'value') else str(self.combat_manager.state),
                "turn_count": self.combat_manager.turn_count,
                "allies": [],
                "enemies": []
            }
            
            # 아군 상태
            for ally in self.combat_manager.allies:
                char_data = self._get_character_state(ally)
                if char_data:
                    snapshot["allies"].append(char_data)
            
            # 적군 상태
            for enemy in self.combat_manager.enemies:
                char_data = self._get_character_state(enemy)
                if char_data:
                    snapshot["enemies"].append(char_data)
            
            return snapshot
        except Exception as e:
            self.logger.error(f"전투 상태 스냅샷 생성 실패: {e}", exc_info=True)
            return {}
    
    def _get_character_state(self, character: Any) -> Optional[Dict[str, Any]]:
        """
        캐릭터 상태 추출 (동기화용)
        
        Args:
            character: 캐릭터 객체
            
        Returns:
            캐릭터 상태 데이터
        """
        try:
            if not character:
                return None
            
            char_id = self._get_character_id(character)
            if not char_id:
                return None
            
            char_data = {
                "id": char_id,
                "current_hp": getattr(character, 'current_hp', 0),
                "max_hp": getattr(character, 'max_hp', 0),
                "current_mp": getattr(character, 'current_mp', 0),
                "max_mp": getattr(character, 'max_mp', 0),
                "current_brv": getattr(character, 'current_brv', 0),
                "is_alive": getattr(character, 'is_alive', True),
                "is_ghost": getattr(character, 'is_ghost', False),
                "is_broken": getattr(character, 'is_broken', False),
            }

            # 상태이상 직렬화 (status_manager 우선, 없으면 status_effects 직접 참조)
            status_effects_data = []
            if hasattr(character, 'status_manager') and hasattr(character.status_manager, 'status_effects'):
                for effect in character.status_manager.status_effects:
                    status_effects_data.append({
                        "name": getattr(effect, 'name', ''),
                        "status_type": effect.status_type.value if hasattr(effect, 'status_type') and hasattr(effect.status_type, 'value') else str(getattr(effect, 'status_type', '')),
                        "duration": getattr(effect, 'duration', 0),
                        "intensity": getattr(effect, 'intensity', 1.0),
                        "stack_count": getattr(effect, 'stack_count', 1),
                    })
            char_data["status_effects"] = status_effects_data

            # 활성 버프 직렬화
            active_buffs_data = {}
            if hasattr(character, 'active_buffs') and character.active_buffs:
                active_buffs_data = character.active_buffs.copy()
            char_data["active_buffs"] = active_buffs_data

            # ATB 게이지 상태
            if self.combat_manager and hasattr(self.combat_manager, 'atb'):
                gauge = self.combat_manager.atb.get_gauge(character)
                if gauge:
                    char_data["atb_current"] = gauge.current
                    char_data["atb_max"] = gauge.max_gauge
                    char_data["atb_can_act"] = gauge.can_act

            return char_data
        except Exception as e:
            self.logger.error(f"캐릭터 상태 추출 실패: {e}", exc_info=True)
            return None
    
    def _find_character_by_id(self, character_id: str) -> Optional[Any]:
        """
        ID로 캐릭터 찾기
        
        Args:
            character_id: 캐릭터 ID
            
        Returns:
            캐릭터 객체 (없으면 None)
        """
        try:
            if not self.combat_manager:
                return None
            
            # 아군에서 찾기
            for ally in self.combat_manager.allies:
                if self._get_character_id(ally) == character_id:
                    return ally
            
            # 적군에서 찾기
            for enemy in self.combat_manager.enemies:
                if self._get_character_id(enemy) == character_id:
                    return enemy
            
            return None
        except Exception as e:
            self.logger.error(f"캐릭터 찾기 실패: {character_id}: {e}", exc_info=True)
            return None
    
    def _get_character_id(self, character: Any) -> Optional[str]:
        """
        캐릭터 ID 추출

        Args:
            character: 캐릭터 객체

        Returns:
            캐릭터 ID (없으면 None)
        """
        try:
            if not character:
                return None

            # ID 속성 확인
            if hasattr(character, 'id') and getattr(character, 'id', None) is not None:
                return str(character.id)

            if hasattr(character, 'character_id') and getattr(character, 'character_id', None) is not None:
                return str(character.character_id)

            # 이름 기반 ID 생성 (Character 객체용)
            # player_id가 있으면 포함하여 고유성 보장 (멀티플레이 시 같은 직업 선택 가능)
            name = getattr(character, 'name', None)
            if name:
                player_id = getattr(character, 'player_id', None)
                if player_id:
                    return f"{player_id}_{name}"
                return f"name_{name}"

            # 인덱스 기반 안정 ID (전투 중 위치 변경에 무관)
            if self.combat_manager:
                for i, enemy in enumerate(self.combat_manager.enemies):
                    if enemy is character:
                        return f"enemy_{i}"
                for i, ally in enumerate(self.combat_manager.allies):
                    if ally is character:
                        return f"ally_{i}"

            # 위치 기반 ID (최후 폴백)
            if hasattr(character, 'x') and hasattr(character, 'y'):
                x = getattr(character, 'x', 0)
                y = getattr(character, 'y', 0)
                return f"char_{x}_{y}"

            return None
        except Exception as e:
            self.logger.error(f"캐릭터 ID 추출 실패: {e}", exc_info=True)
            return None
    
    def _get_player_id_from_character(self, character: Any) -> Optional[str]:
        """
        캐릭터에서 플레이어 ID 추출
        
        Args:
            character: 캐릭터 객체
            
        Returns:
            플레이어 ID (없으면 None)
        """
        try:
            if not character:
                return None
            
            # 직접 player_id 속성이 있는지 확인
            if hasattr(character, 'player_id'):
                return getattr(character, 'player_id', None)
            
            # owner를 통한 확인
            if hasattr(character, 'owner') and hasattr(character.owner, 'player_id'):
                return getattr(character.owner, 'player_id', None)
            
            return None
        except Exception as e:
            self.logger.error(f"플레이어 ID 추출 실패: {e}", exc_info=True)
            return None

