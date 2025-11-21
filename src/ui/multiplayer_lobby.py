"""
멀티플레이 로비 UI

인원 모집 화면 - 호스트는 서버를 시작하고 클라이언트들이 연결될 때까지 대기
"""

import tcod.console
import tcod.event
from typing import Optional, Dict, Any, List
import time
import random

from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler
from src.core.logger import get_logger
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.network import HostNetworkManager, ClientNetworkManager
from src.multiplayer.player import MultiplayerPlayer
from src.audio import play_bgm, play_sfx


logger = get_logger("multiplayer.lobby")


def get_character_allocation(player_count: int, is_host: bool) -> int:
    """
    플레이어 수에 따른 캐릭터 할당 계산
    
    Args:
        player_count: 현재 플레이어 수 (1~4)
        is_host: 호스트 여부
        
    Returns:
        해당 플레이어가 선택할 수 있는 캐릭터 수
        
    할당 규칙:
        - 1인: 4명 (1인당 4명)
        - 2인: 각 2명 (2인당 2명씩 = 총 4명)
        - 3인: 호스트 2명, 나머지 1명씩 (2 + 1 + 1 = 총 4명)
        - 4인: 각 1명 (1인당 1명씩 = 총 4명)
    """
    if player_count == 1:
        return 4
    elif player_count == 2:
        return 2
    elif player_count == 3:
        return 2 if is_host else 1
    elif player_count == 4:
        return 1
    else:
        logger.warning(f"알 수 없는 플레이어 수: {player_count}")
        return 1


class MultiplayerLobby:
    """멀티플레이 로비 UI 클래스"""
    
    def __init__(
        self,
        screen_width: int,
        screen_height: int,
        session: MultiplayerSession,
        network_manager: Any,
        local_player_id: str,
        is_host: bool,
        dungeon_data_check: Optional[Dict[str, Any]] = None,
        lobby_complete_check: Optional[Dict[str, Any]] = None
    ):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.session = session
        self.network_manager = network_manager
        self.local_player_id = local_player_id
        self.is_host = is_host
        self.dungeon_data_check = dungeon_data_check
        self.lobby_complete_check = lobby_complete_check
        
        self.completed = False
        self.cancelled = False
        self.host_disconnected = False
        
        # 봇 관리자 초기화
        if not hasattr(session, 'bot_manager') or not session.bot_manager:
            from src.multiplayer.ai_bot_advanced import AdvancedBotManager
            bot_manager = AdvancedBotManager(
                network_manager=network_manager,
                session=session,
                auto_fill=False,
                min_players=1
            )
            session.bot_manager = bot_manager
    
    def handle_input(self, action: GameAction) -> bool:
        """입력 처리"""
        # 호스트만 봇 추가 가능
        if action == GameAction.ADD_BOT and self.is_host:
            if len(self.session.players) < self.session.max_players:
                # 봇 추가 로직
                from src.multiplayer.ai_bot_advanced import AdvancedBotManager, BotBehavior
                from src.multiplayer.player import MultiplayerPlayer
                from uuid import uuid4
                
                bot_manager: Optional[AdvancedBotManager] = getattr(self.session, 'bot_manager', None)
                if not bot_manager:
                    logger.warning("봇 관리자가 없습니다. 봇을 추가할 수 없습니다.")
                    return False
                
                # 봇 이름 생성 (BOT1, BOT2, ... 형식)
                bot_number = len(bot_manager.bots) + 1
                bot_name = f"BOT{bot_number}"
                
                bot_id = f"bot_{uuid4().hex[:8]}"
                
                behaviors = [
                    BotBehavior.EXPLORER,
                    BotBehavior.AGGRESSIVE,
                    BotBehavior.SUPPORT,
                    BotBehavior.RANDOM
                ]
                behavior = random.choice(behaviors)
                
                bot = bot_manager.add_bot(
                    bot_id=bot_id,
                    bot_name=bot_name,
                    behavior=behavior,
                    is_host=False
                )
                
                logger.info(f"봇 매니저에 봇 추가 완료: {bot_name} (ID: {bot_id}), 봇 매니저 봇 수: {len(bot_manager.bots)}")
                
                # 봇을 세션의 플레이어로 추가
                player = MultiplayerPlayer(
                    player_id=bot_id,
                    player_name=bot_name,
                    x=0, y=0, party=[], is_host=False, is_bot=True
                )
                self.session.add_player(player)
                logger.info(f"로비에 봇 추가: {bot_name} (ID: {bot_id}), 세션 플레이어 수: {len(self.session.players)}")
                
                # 봇 시작 (봇 매니저가 실행 중이 아니면 시작)
                if bot_manager and not bot_manager.is_running:
                    logger.info(f"봇 매니저 시작 중... (봇 수: {len(bot_manager.bots)})")
                    bot_manager.start_all()
                elif bot and not bot.is_active:
                    # 봇 매니저는 실행 중이지만 봇이 활성화되지 않은 경우
                    bot.start()
                    logger.info(f"봇 {bot_name} 활성화")
                
                # 다른 클라이언트에게 플레이어 목록 업데이트 메시지 전송
                if self.network_manager.is_host:
                    from src.multiplayer.protocol import MessageBuilder
                    import asyncio
                    # 플레이어 목록을 직렬화하여 리스트로 변환
                    players_data = [player.serialize() for player in self.session.players.values()]
                    player_list_msg = MessageBuilder.player_list(players_data)
                    asyncio.run_coroutine_threadsafe(
                        self.network_manager.broadcast(player_list_msg),
                        getattr(self.network_manager, '_server_event_loop', asyncio.get_event_loop())
                    )
                return False
        
        elif action == GameAction.CONFIRM:
            # 호스트만 게임 시작 가능
            if self.is_host:
                if len(self.session.players) >= 1:
                    self.completed = True
                    return True
            return False
        
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            self.cancelled = True
            return True
        
        return False
    
    def render(self, console: tcod.console.Console):
        """렌더링"""
        render_space_background(console, self.screen_width, self.screen_height)
        
        # 제목
        title = "멀티플레이 로비"
        console.print(
            self.screen_width // 2 - len(title) // 2,
            5,
            title,
            fg=Colors.WHITE
        )
        
        # 호스트 정보
        if self.is_host:
            host_info = f"호스트: {self.network_manager.local_ip}:{self.network_manager.port}"
            console.print(
                self.screen_width // 2 - len(host_info) // 2,
                8,
                host_info,
                fg=Colors.UI_TEXT
            )
        
        # 플레이어 목록
        y = 12
        console.print(
            self.screen_width // 2 - 15,
            y,
            "플레이어 목록",
            fg=Colors.UI_TEXT
        )
        y += 2
        
        bot_count = sum(1 for p in self.session.players.values() if getattr(p, 'is_bot', False))
        console.print(
            self.screen_width // 2 - 15,
            y,
            f"플레이어 ({len(self.session.players) - bot_count}/{self.session.max_players}) 봇: {bot_count}명",
            fg=Colors.UI_TEXT
        )
        y += 2
        
        for player_id, player in self.session.players.items():
            player_name = getattr(player, 'player_name', 'Unknown')
            is_bot = getattr(player, 'is_bot', False)
            is_host_player = getattr(player, 'is_host', False)
            
            name_text = f"{'[봇] ' if is_bot else ''}{player_name}"
            if is_host_player:
                name_text += " (호스트)"
            if player_id == self.local_player_id:
                name_text += " [나]"
            
            console.print(
                self.screen_width // 2 - 15,
                y,
                name_text,
                fg=Colors.UI_TEXT_SELECTED if player_id == self.local_player_id else Colors.UI_TEXT
            )
            y += 1
        
        # 안내 메시지
        if self.is_host:
            help_text = "Enter: 게임 시작  ESC: 취소"
            if len(self.session.players) < self.session.max_players:
                help_text += "  B: 봇 추가"
            console.print(
                self.screen_width // 2 - len(help_text) // 2,
                self.screen_height - 4,
                help_text,
                fg=Colors.UI_TEXT
            )
            
            # 호스트일 때 봇 추가 안내
            if len(self.session.players) < self.session.max_players:
                add_bot_msg = "B: 봇 추가"
                console.print(
                    self.screen_width // 2 - len(add_bot_msg) // 2,
                    self.screen_height - 3,
                    add_bot_msg,
                    fg=Colors.UI_TEXT
                )
        else:
            help_text = "호스트가 게임을 시작할 때까지 대기 중..."
            console.print(
                self.screen_width // 2 - len(help_text) // 2,
                self.screen_height - 3,
                help_text,
                fg=Colors.DARK_GRAY
            )


def show_multiplayer_lobby(
    console: tcod.console.Console,
    context: tcod.context.Context,
    session: MultiplayerSession,
    network_manager: Any,
    local_player_id: str,
    is_host: bool,
    dungeon_data_check: Optional[Dict[str, Any]] = None,
    lobby_complete_check: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    멀티플레이 로비 화면 표시
    
    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        session: 멀티플레이 세션
        network_manager: 네트워크 매니저
        local_player_id: 로컬 플레이어 ID
        is_host: 호스트 여부
        dungeon_data_check: 던전 데이터 확인용 딕셔너리 (클라이언트용)
        lobby_complete_check: 로비 완료 확인용 딕셔너리 (클라이언트용)
    
    Returns:
        로비 결과 딕셔너리
    """
    from src.ui.input_handler import GameAction, InputHandler
    from src.multiplayer.protocol import MessageType
    
    # 멀티플레이 로비 BGM 재생
    try:
        play_bgm("multiplayer_lobby", loop=True)
        logger.info("멀티플레이 로비 BGM 재생")
    except Exception as e:
        logger.warning(f"멀티플레이 로비 BGM 재생 실패: {e}")
    
    ui = MultiplayerLobby(
        screen_width=console.width,
        screen_height=console.height,
        session=session,
        network_manager=network_manager,
        local_player_id=local_player_id,
        is_host=is_host,
        dungeon_data_check=dungeon_data_check,
        lobby_complete_check=lobby_complete_check
    )
    
    handler = InputHandler()
    
    # 클라이언트: 로비 완료 메시지 핸들러 등록
    if not is_host and lobby_complete_check is not None:
        def handle_lobby_complete(message: Any, sender_id: Optional[str] = None):
            """로비 완료 메시지 처리"""
            lobby_complete_check["value"] = True
            logger.info("로비 완료 메시지 수신")
        
        network_manager.register_handler(MessageType.LOBBY_COMPLETE, handle_lobby_complete)
    
    # ADD_BOT 액션 추가
    from src.ui.input_handler import GameAction
    if not hasattr(GameAction, 'ADD_BOT'):
        # GameAction에 ADD_BOT이 없으면 동적으로 처리
        pass
    
    while not ui.completed and not ui.cancelled and not ui.host_disconnected:
        # 클라이언트: 던전 데이터 확인
        if not is_host and dungeon_data_check is not None:
            if dungeon_data_check.get("dungeon_data") is not None:
                ui.completed = True
                break
        
        # 클라이언트: 로비 완료 확인
        if not is_host and lobby_complete_check is not None:
            if lobby_complete_check.get("value", False):
                ui.completed = True
                break
        
        # 렌더링
        ui.render(console)
        context.present(console)
        
        # 입력 처리
        for event in tcod.event.wait(timeout=0.1):
            if isinstance(event, tcod.event.Quit):
                ui.cancelled = True
                break
            
            context.convert_event(event)
            action = handler.dispatch(event)
            
            # B 키 처리 (봇 추가)
            if isinstance(event, tcod.event.KeyDown) and event.sym == tcod.event.KeySym.B:
                if is_host and len(session.players) < session.max_players:
                    # 봇 추가
                    from src.multiplayer.ai_bot_advanced import AdvancedBotManager, BotBehavior
                    from src.multiplayer.player import MultiplayerPlayer
                    from uuid import uuid4
                    
                    bot_manager: Optional[AdvancedBotManager] = getattr(session, 'bot_manager', None)
                    if not bot_manager:
                        logger.warning("봇 관리자가 없습니다. 봇을 추가할 수 없습니다.")
                        continue
                    
                    # 봇 이름 생성 (BOT1, BOT2, ... 형식)
                    bot_number = len(bot_manager.bots) + 1
                    bot_name = f"BOT{bot_number}"
                    
                    bot_id = f"bot_{uuid4().hex[:8]}"
                    
                    behaviors = [
                        BotBehavior.EXPLORER,
                        BotBehavior.AGGRESSIVE,
                        BotBehavior.SUPPORT,
                        BotBehavior.RANDOM
                    ]
                    behavior = random.choice(behaviors)
                    
                    bot = bot_manager.add_bot(
                        bot_id=bot_id,
                        bot_name=bot_name,
                        behavior=behavior,
                        is_host=False
                    )
                    
                    logger.info(f"봇 매니저에 봇 추가 완료: {bot_name} (ID: {bot_id}), 봇 매니저 봇 수: {len(bot_manager.bots)}")
                    
                    # 봇을 세션의 플레이어로 추가
                    player = MultiplayerPlayer(
                        player_id=bot_id,
                        player_name=bot_name,
                        x=0, y=0, party=[], is_host=False, is_bot=True
                    )
                    session.add_player(player)
                    logger.info(f"로비에 봇 추가: {bot_name} (ID: {bot_id}), 세션 플레이어 수: {len(session.players)}")
                    
                    # 봇 시작 (봇 매니저가 실행 중이 아니면 시작)
                    if bot_manager and not bot_manager.is_running:
                        logger.info(f"봇 매니저 시작 중... (봇 수: {len(bot_manager.bots)})")
                        bot_manager.start_all()
                    elif bot and not bot.is_active:
                        # 봇 매니저는 실행 중이지만 봇이 활성화되지 않은 경우
                        bot.start()
                        logger.info(f"봇 {bot_name} 활성화")
                    
                    # 다른 클라이언트에게 플레이어 목록 업데이트 메시지 전송
                    if network_manager.is_host:
                        from src.multiplayer.protocol import MessageBuilder
                        import asyncio
                        # 플레이어 목록을 직렬화하여 리스트로 변환
                        players_data = [player.serialize() for player in session.players.values()]
                        player_list_msg = MessageBuilder.player_list(players_data)
                        server_loop = getattr(network_manager, '_server_event_loop', None)
                        if server_loop and server_loop.is_running():
                            asyncio.run_coroutine_threadsafe(
                                network_manager.broadcast(player_list_msg),
                                server_loop
                            )
                    continue
            
            if action:
                if ui.handle_input(action):
                    break
        
        # 연결 상태 확인
        if not is_host:
            from src.multiplayer.network import ConnectionState
            if network_manager.connection_state == ConnectionState.DISCONNECTED:
                ui.host_disconnected = True
                break
    
    # 결과 반환
    player_count = len(session.players)
    local_allocation = get_character_allocation(player_count, is_host)
    
    return {
        "completed": ui.completed,
        "cancelled": ui.cancelled,
        "host_disconnected": ui.host_disconnected,
        "player_count": player_count,
        "local_allocation": local_allocation
    }


def show_bot_assignment_ui(
    console: tcod.console.Console,
    context: tcod.context.Context,
    session: MultiplayerSession,
    network_manager: Any
) -> bool:
    """
    게임 로드 시 봇 할당 UI
    
    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        session: 멀티플레이 세션
        network_manager: 네트워크 매니저
        
    Returns:
        봇 할당 여부 (True: 할당됨, False: 취소)
    """
    from src.multiplayer.ai_bot_advanced import AdvancedBotManager, BotBehavior
    from uuid import uuid4
    
    handler = InputHandler()
    closed = False
    bot_assigned = False
    
    # 봇 관리자 초기화
    if not hasattr(session, 'bot_manager') or not session.bot_manager:
        bot_manager = AdvancedBotManager(
            network_manager=network_manager,
            session=session,
            auto_fill=False,
            min_players=1
        )
        session.bot_manager = bot_manager
    else:
        bot_manager = session.bot_manager
    
    while not closed:
        # 렌더링
        render_space_background(console, console.width, console.height)
        
        # 제목
        title = "봇 할당"
        console.print(
            console.width // 2 - len(title) // 2,
            5,
            title,
            fg=Colors.WHITE
        )
        
        # 설명
        desc = "게임을 불러왔습니다. 봇을 추가하시겠습니까?"
        console.print(
            console.width // 2 - len(desc) // 2,
            8,
            desc,
            fg=Colors.UI_TEXT
        )
        
        # 현재 플레이어 수
        player_count = len(session.players)
        bot_count = sum(1 for p in session.players.values() if getattr(p, 'is_bot', False))
        human_count = player_count - bot_count
        
        info_text = f"현재 플레이어: {human_count}명 (봇: {bot_count}명) / 최대: {session.max_players}명"
        console.print(
            console.width // 2 - len(info_text) // 2,
            11,
            info_text,
            fg=Colors.UI_TEXT
        )
        
        # 사용 가능한 슬롯
        available_slots = session.max_players - player_count
        if available_slots > 0:
            slot_text = f"사용 가능한 슬롯: {available_slots}개"
            console.print(
                console.width // 2 - len(slot_text) // 2,
            13,
                slot_text,
                fg=Colors.UI_TEXT
            )
        
        # 메뉴
        y = 16
        menu_items = []
        
        if available_slots > 0:
            menu_items.append(("B: 봇 추가", "add_bot"))
        menu_items.append(("Enter: 계속", "continue"))
        menu_items.append(("ESC: 취소", "cancel"))
        
        for i, (text, action) in enumerate(menu_items):
            color = Colors.UI_TEXT_SELECTED if i == 0 else Colors.UI_TEXT
            console.print(
                console.width // 2 - len(text) // 2,
                y + i * 2,
                text,
                fg=color
            )
        
        # 하단 안내
        help_text = "B: 봇 추가  Enter: 계속  ESC: 취소"
        console.print(
            console.width // 2 - len(help_text) // 2,
            console.height - 3,
            help_text,
            fg=Colors.DARK_GRAY
        )
        
        context.present(console)
        
        # 입력 처리
        for event in tcod.event.wait():
            if isinstance(event, tcod.event.Quit):
                closed = True
                bot_assigned = False
                break
            
            context.convert_event(event)
            action = handler.dispatch(event)
            
            if action == GameAction.CONFIRM:
                # 계속
                closed = True
                bot_assigned = True
                break
            elif action == GameAction.CANCEL:
                # 취소
                closed = True
                bot_assigned = False
                break
            elif isinstance(event, tcod.event.KeyDown):
                # B 키: 봇 추가
                if event.sym == tcod.event.KeySym.B and available_slots > 0:
                    # 봇 추가
                    bot_number = len(bot_manager.bots) + 1
                    bot_name = f"BOT{bot_number}"
                    bot_id = f"bot_{uuid4().hex[:8]}"
                    
                    behaviors = [
                        BotBehavior.EXPLORER,
                        BotBehavior.AGGRESSIVE,
                        BotBehavior.SUPPORT,
                        BotBehavior.RANDOM
                    ]
                    behavior = random.choice(behaviors)
                    
                    bot = bot_manager.add_bot(
                        bot_id=bot_id,
                        bot_name=bot_name,
                        behavior=behavior,
                        is_host=False
                    )
                    
                    # 봇을 세션의 플레이어로 추가
                    player = MultiplayerPlayer(
                        player_id=bot_id,
                        player_name=bot_name,
                        x=0, y=0, party=[], is_host=False, is_bot=True
                    )
                    session.add_player(player)
                    logger.info(f"봇 추가: {bot_name} (ID: {bot_id})")
                    
                    # 플레이어 수 업데이트
                    player_count = len(session.players)
                    available_slots = session.max_players - player_count
    
    return bot_assigned
