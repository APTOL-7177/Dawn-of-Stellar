"""
멀티플레이 파티 설정 테스트
"""

import pytest
from src.multiplayer.party_setup import MultiplayerPartySetup, MultiplayerPartyValidator
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.player import MultiplayerPlayer
from src.ui.party_setup import PartyMember


class TestMultiplayerPartySetup:
    """멀티플레이 파티 설정 테스트"""
    
    def test_job_duplication_prevention(self):
        """직업 중복 방지 테스트"""
        # 호스트 세션 생성
        session = MultiplayerSession(max_players=4)
        host = MultiplayerPlayer(
            player_id="host_player",
            player_name="호스트"
        )
        session.add_player(host)
        
        # 호스트 파티 설정
        host_setup = MultiplayerPartySetup(
            session=session,
            player_id="host_player",
            is_host=True
        )
        
        # 클라이언트 파티 설정
        client = MultiplayerPlayer(
            player_id="client_player",
            player_name="클라이언트"
        )
        session.add_player(client)
        
        client_setup = MultiplayerPartySetup(
            session=session,
            player_id="client_player",
            is_host=False
        )
        
        # 호스트가 직업 선택
        host_member = PartyMember(
            job_id="knight",
            job_name="나이트",
            character_name="기사",
            stats={}
        )
        
        success = host_setup.add_party_member(host_member)
        assert success is True
        assert "knight" in host_setup.used_jobs
        
        # 클라이언트가 같은 직업 선택 시도 (실패해야 함)
        client_setup.sync_used_jobs_from_host(host_setup.used_jobs)
        
        client_member = PartyMember(
            job_id="knight",
            job_name="나이트",
            character_name="기사2",
            stats={}
        )
        
        can_select = client_setup.can_select_job("knight")
        assert can_select is False
        
        success = client_setup.add_party_member(client_member)
        assert success is False
    
    def test_passive_host_only(self):
        """패시브 호스트 전용 설정 테스트"""
        session = MultiplayerSession(max_players=4)
        host = MultiplayerPlayer(
            player_id="host_player",
            player_name="호스트"
        )
        session.add_player(host)
        
        host_setup = MultiplayerPartySetup(
            session=session,
            player_id="host_player",
            is_host=True
        )
        
        client = MultiplayerPlayer(
            player_id="client_player",
            player_name="클라이언트"
        )
        session.add_player(client)
        
        client_setup = MultiplayerPartySetup(
            session=session,
            player_id="client_player",
            is_host=False
        )
        
        # 호스트는 패시브 설정 가능
        success = host_setup.set_passives(["passive1", "passive2"])
        assert success is True
        assert host_setup.selected_passives == ["passive1", "passive2"]
        
        # 클라이언트는 패시브 설정 불가
        success = client_setup.set_passives(["passive3"])
        assert success is False


class TestPlayerStateManager:
    """플레이어 상태 관리 테스트"""
    
    def test_mark_visibility_on_all_death(self):
        """모든 캐릭터 사망 시 마크 숨김 테스트"""
        from src.multiplayer.player_state import PlayerStateManager
        
        manager = PlayerStateManager()
        
        # 플레이어 생성
        player = MultiplayerPlayer(
            player_id="test_player",
            player_name="테스트 플레이어"
        )
        
        # 더미 캐릭터 생성
        from src.character.character import Character
        
        character1 = Character(name="캐릭터1", character_class="knight", level=1)
        character2 = Character(name="캐릭터2", character_class="archer", level=1)
        
        player.party = [character1, character2]
        
        # 모든 캐릭터 죽음
        character1.current_hp = 0
        character1.is_alive = False
        character2.current_hp = 0
        character2.is_alive = False
        
        # 상태 업데이트
        manager.update_player_state(player)
        
        # 마크가 숨겨져야 함
        assert manager.is_mark_visible("test_player") is False
    
    def test_mark_visibility_on_revival(self):
        """부활 시 마크 표시 테스트"""
        from src.multiplayer.player_state import PlayerStateManager
        
        manager = PlayerStateManager()
        
        # 플레이어 생성
        player = MultiplayerPlayer(
            player_id="test_player",
            player_name="테스트 플레이어"
        )
        
        # 더미 캐릭터 생성
        from src.character.character import Character
        
        character1 = Character(name="캐릭터1", character_class="knight", level=1)
        player.party = [character1]
        
        # 모든 캐릭터 죽음
        character1.current_hp = 0
        character1.is_alive = False
        manager.update_player_state(player)
        
        assert manager.is_mark_visible("test_player") is False
        
        # 하나 부활
        character1.current_hp = 50
        character1.is_alive = True
        manager.update_player_state(player)
        
        # 마크가 다시 표시되어야 함
        assert manager.is_mark_visible("test_player") is True


class TestRevivalSystem:
    """부활 시스템 테스트"""
    
    def test_revival_spawn_near_player(self):
        """부활 시 플레이어 옆에 스폰 테스트"""
        from src.multiplayer.player_state import PlayerStateManager
        from src.multiplayer.revival_system import RevivalSystem
        
        player_state_manager = PlayerStateManager()
        revival_system = RevivalSystem(player_state_manager)
        
        # 플레이어 생성
        player = MultiplayerPlayer(
            player_id="test_player",
            player_name="테스트 플레이어",
            x=10,
            y=10
        )
        
        # 더미 캐릭터 생성 (사망 상태)
        from src.character.character import Character
        
        character = Character(name="캐릭터1", character_class="knight", level=1)
        character.current_hp = 0
        character.is_alive = False
        # max_hp는 property이므로 직접 설정 불가 (StatManager를 통해 관리됨)
        
        player.party = [character]
        
        # 부활
        success = revival_system.revive_character(player, character)
        
        assert success is True
        assert character.is_alive is True
        assert character.current_hp > 0
        
        # 부활 위치가 플레이어 옆에 결정되었는지 확인
        # (실제 위치는 맵 탐험 시스템에서 관리될 수 있으므로 여기서는 성공 여부만 확인)
        spawn_x, spawn_y = player_state_manager.handle_character_revival(player, character)
        assert spawn_x is not None and spawn_y is not None
        # 플레이어 위치 (10, 10) 근처에 스폰되었는지 확인
        assert abs(spawn_x - player.x) <= 2
        assert abs(spawn_y - player.y) <= 2

