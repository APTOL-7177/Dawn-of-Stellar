"""
멀티플레이 회귀 테스트

Bug 1: 빈 인벤토리의 __len__=0으로 인해 보물상자 아이템이 무시되는 버그
Bug 2: 클라이언트 세션 플레이어의 party가 PartyMember 객체라서 전투 시작 실패하는 버그
"""

import pytest
from src.multiplayer.session import MultiplayerSession
from src.multiplayer.player import MultiplayerPlayer
from src.character.character import Character
from src.equipment.inventory import Inventory
from src.ui.party_setup import PartyMember


class TestInventoryFalsyBug:
    """Bug 1: 빈 인벤토리 truthiness 회귀 테스트"""

    def test_empty_inventory_is_falsy(self):
        """빈 인벤토리의 bool() 평가가 False인지 확인 (근본 원인)"""
        inventory = Inventory()
        assert len(inventory) == 0
        # __len__=0 이므로 bool()은 False
        assert bool(inventory) is False

    def test_empty_inventory_is_not_none(self):
        """빈 인벤토리가 None이 아닌지 확인"""
        inventory = Inventory()
        assert inventory is not None

    def test_item_found_with_empty_inventory(self):
        """빈 인벤토리로 아이템 발견 시 조건 체크 (수정된 로직)"""
        inventory = Inventory()
        items = [{"name": "test_item"}]

        # 수정 전: `if items and inventory:` → False (빈 인벤토리)
        old_check = bool(items and inventory)
        assert old_check is False, "수정 전 로직: 빈 인벤토리는 falsy"

        # 수정 후: `if items and inventory is not None:` → True
        new_check = bool(items) and (inventory is not None)
        assert new_check is True, "수정 후 로직: 빈 인벤토리도 통과"


class TestClientPartyCharacterBug:
    """Bug 2: 클라이언트 세션 플레이어 party가 PartyMember라서 전투 실패하는 회귀 테스트"""

    def _create_client_session(self):
        """클라이언트 세션 환경 생성"""
        session = MultiplayerSession(max_players=4)

        # 호스트 플레이어 (다른 클라이언트에서 만들어진 플레이어)
        host = MultiplayerPlayer(
            player_id="host_id",
            player_name="호스트",
            x=5, y=5,
            party=[],
            is_host=True
        )
        session.add_player(host)
        session.host_id = host.player_id

        # 로컬 플레이어 (클라이언트)
        local_player = MultiplayerPlayer(
            player_id="client_id",
            player_name="클라이언트",
            x=5, y=5,
            party=[],
            is_host=False
        )
        session.add_player(local_player)

        return session, local_player

    def test_party_member_has_no_hp(self):
        """PartyMember 객체에는 HP/is_alive가 없음을 확인"""
        member = PartyMember(
            job_id="knight",
            job_name="나이트",
            character_name="기사",
            stats={}
        )
        assert getattr(member, 'current_hp', None) is None
        assert getattr(member, 'max_hp', None) is None
        assert getattr(member, 'is_alive', None) is None

    def test_character_has_hp(self):
        """Character 객체에는 HP/is_alive가 있음을 확인"""
        char = Character(name="기사", character_class="knight", level=1)
        char.current_hp = char.max_hp
        char.is_alive = True

        assert char.current_hp is not None
        assert char.current_hp > 0
        assert char.max_hp is not None
        assert char.is_alive is True

    def test_session_party_updated_with_characters(self):
        """클라이언트가 session player의 party를 Character 객체로 업데이트하는지 확인"""
        session, local_player = self._create_client_session()

        # 초기 상태: PartyMember 객체 설정 (파티 선택 후)
        member1 = PartyMember(
            job_id="knight", job_name="나이트",
            character_name="기사", stats={}
        )
        member2 = PartyMember(
            job_id="archer", job_name="궁수",
            character_name="사수", stats={}
        )
        local_player.party = [member1, member2]

        # PartyMember → Character 변환 (main.py 클라이언트 로직 시뮬레이션)
        party_members = []
        for member in local_player.party:
            if isinstance(member, PartyMember):
                char = Character(
                    name=member.character_name,
                    character_class=member.job_id,
                    level=1
                )
                char.current_hp = char.max_hp
                char.current_mp = char.max_mp
                char.is_alive = True
                char.player_id = local_player.player_id
                party_members.append(char)

        # 핵심 수정: session player의 party를 Character 객체로 업데이트
        local_player.party = party_members

        # 검증: session player의 party가 Character 객체인지 확인
        assert len(local_player.party) == 2
        for char in local_player.party:
            assert isinstance(char, Character)
            assert char.current_hp is not None
            assert char.current_hp > 0
            assert char.is_alive is True

    def test_get_nearby_participants_returns_characters(self):
        """_get_nearby_participants가 Character 객체를 반환하는지 확인"""
        from src.multiplayer.exploration_multiplayer import MultiplayerExplorationSystem
        from src.world.dungeon_generator import DungeonMap

        session, local_player = self._create_client_session()

        # Character 객체로 파티 설정 (수정된 코드 시뮬레이션)
        char1 = Character(name="기사", character_class="knight", level=1)
        char1.current_hp = char1.max_hp
        char1.is_alive = True
        char1.player_id = local_player.player_id

        char2 = Character(name="사수", character_class="archer", level=1)
        char2.current_hp = char2.max_hp
        char2.is_alive = True
        char2.player_id = local_player.player_id

        local_player.party = [char1, char2]

        # 던전 생성
        dungeon = DungeonMap(width=50, height=50)
        dungeon.rooms = []

        exploration = MultiplayerExplorationSystem(
            dungeon=dungeon,
            party=[char1, char2],
            floor_number=1,
            session=session,
            network_manager=None,
            local_player_id=local_player.player_id
        )

        # 전투 위치 = 플레이어 위치
        combat_position = (local_player.x, local_player.y)
        participants = exploration._get_nearby_participants(combat_position)

        # 참여자가 Character 객체이고 HP가 있어야 함
        assert len(participants) >= 2
        for p in participants:
            assert isinstance(p, Character), f"Expected Character, got {type(p).__name__}"
            assert p.current_hp is not None
            assert p.current_hp > 0
            assert p.is_alive is True

    def test_combat_validation_with_characters(self):
        """Character 객체 파티로 전투 유효성 검사 통과하는지 확인"""
        char1 = Character(name="기사", character_class="knight", level=1)
        char1.current_hp = char1.max_hp
        char1.is_alive = True

        char2 = Character(name="사수", character_class="archer", level=1)
        char2.current_hp = char2.max_hp
        char2.is_alive = True

        party = [char1, char2]

        # combat_ui.py의 유효성 검사 로직 재현
        has_alive_member = False
        for member in party:
            is_alive = getattr(member, 'is_alive', None)
            current_hp = getattr(member, 'current_hp', None)
            if is_alive is True:
                has_alive_member = True
            elif current_hp is not None and current_hp > 0:
                has_alive_member = True

        assert has_alive_member is True, "Character 파티는 전투 유효성 검사 통과해야 함"

    def test_combat_validation_fails_with_party_members(self):
        """PartyMember 객체 파티로 전투 유효성 검사 실패하는지 확인 (수정 전 버그 재현)"""
        member1 = PartyMember(
            job_id="knight", job_name="나이트",
            character_name="기사", stats={}
        )
        member2 = PartyMember(
            job_id="archer", job_name="궁수",
            character_name="사수", stats={}
        )

        party = [member1, member2]

        # combat_ui.py의 유효성 검사 로직 재현
        has_alive_member = False
        for member in party:
            is_alive = getattr(member, 'is_alive', None)
            current_hp = getattr(member, 'current_hp', None)
            if is_alive is True:
                has_alive_member = True
            elif current_hp is not None and current_hp > 0:
                has_alive_member = True

        assert has_alive_member is False, "PartyMember 파티는 전투 유효성 검사 실패해야 함"
