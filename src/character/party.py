"""
Party - 파티 관리 클래스

파티 전체의 팀워크 게이지를 관리하고 연쇄 시스템을 제어합니다.
"""

from typing import List, Optional, Dict, Any
from src.core.logger import get_logger

logger = get_logger("party")


class Party:
    """
    파티 클래스

    아군 파티를 관리하고 파티 전체가 공유하는 팀워크 게이지를 제어합니다.
    """

    def __init__(self, members: List[Any]) -> None:
        """
        파티 초기화

        Args:
            members: 파티 멤버 (Character 인스턴스 리스트)
        """
        self.members = members

        # 팀워크 게이지 시스템
        self.teamwork_gauge = 0
        self.max_teamwork_gauge = 600

        # 연쇄 시스템
        self.chain_active = False
        self.chain_count = 0
        self.chain_starter: Optional[Any] = None
        self.chain_starter_skill: Optional[Any] = None  # 시작자의 팀워크 스킬

    def add_teamwork_gauge(self, amount: int) -> None:
        """
        팀워크 게이지 증가

        Args:
            amount: 증가할 게이지량
        """
        old_gauge = self.teamwork_gauge
        self.teamwork_gauge = min(self.max_teamwork_gauge, self.teamwork_gauge + amount)
        logger.debug(
            f"팀워크 게이지: {old_gauge} → {self.teamwork_gauge} (+{amount}) "
            f"({self.teamwork_gauge // 25}셀)"
        )

    def consume_teamwork_gauge(self, amount: int) -> bool:
        """
        팀워크 게이지 소모

        Args:
            amount: 소모할 게이지량

        Returns:
            소모 성공 여부
        """
        if self.teamwork_gauge >= amount:
            self.teamwork_gauge -= amount
            logger.info(
                f"팀워크 게이지 소모: -{amount} "
                f"(잔여: {self.teamwork_gauge}/{self.max_teamwork_gauge}, {self.teamwork_gauge // 25}셀)"
            )
            return True
        return False

    def start_chain(self, starter: Any, skill: Optional[Any] = None) -> None:
        """
        연쇄 시작

        Args:
            starter: 연쇄를 시작한 캐릭터
            skill: 팀워크 스킬 (optional, 시작자의 스킬 정보)
        """
        self.chain_active = True
        self.chain_count = 1
        self.chain_starter = starter
        self.chain_starter_skill = skill  # 시작자 스킬 저장 (참고용)
        logger.info(f"[Chain] 연쇄 시작! ({starter.name}이(가) 팀워크 스킬 사용)")

    def continue_chain(self, skill: Optional[Any] = None) -> int:
        """
        연쇄 계속 - 필요 MP 비용을 반환하고 연쇄 단계를 증가시킵니다.

        Args:
            skill: 다음 참가자의 팀워크 스킬 (스킬의 게이지 비용으로 MP 계산)

        Returns:
            필요 MP 비용 (스킬의 게이지 비용에 따라 계산)
        """
        if not self.chain_active:
            return 0

        self.chain_count += 1

        # 스킬이 제공되면, 그 스킬의 게이지 비용에 기반하여 MP 계산
        if skill and hasattr(skill, 'calculate_mp_cost'):
            mp_cost = skill.calculate_mp_cost(self.chain_count)
            logger.info(
                f"[Chain] 연쇄 {self.chain_count}단계 "
                f"(스킬: {getattr(skill, 'name', 'Unknown')}, "
                f"게이지: {skill.teamwork_cost.gauge}, 필요 MP: {mp_cost})"
            )
            return mp_cost
        else:
            # 스킬이 없으면 기본값 반환 (호환성)
            # MP 비용: 10 × 2^(연쇄수-2)
            # 2단계: 10, 3단계: 20, 4단계: 40, 5단계: 80, 6단계: 160
            mp_cost = 10 * (2 ** (self.chain_count - 2))
            logger.info(f"[Chain] 연쇄 {self.chain_count}단계 (필요 MP: {mp_cost})")
            return mp_cost

    def end_chain(self) -> None:
        """연쇄 종료"""
        if self.chain_active:
            logger.info(f"[Chain] 연쇄 종료 (총 {self.chain_count}단계)")
        self.chain_active = False
        self.chain_count = 0
        self.chain_starter = None
        self.chain_starter_skill = None

    def get_chain_info(self) -> Dict[str, Any]:
        """
        현재 연쇄 정보 반환

        Returns:
            연쇄 정보 딕셔너리
        """
        return {
            "active": self.chain_active,
            "count": self.chain_count,
            "starter": self.chain_starter.name if self.chain_starter else None
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        세이브용 딕셔너리로 변환

        Returns:
            파티 정보 딕셔너리 (세이브 데이터용)
        """
        return {
            "members": [m.to_dict() if hasattr(m, 'to_dict') else str(m) for m in self.members],
            "teamwork_gauge": self.teamwork_gauge,
            "max_teamwork_gauge": self.max_teamwork_gauge
        }

    def __iter__(self):
        """
        Party 객체를 반복하면 members를 반복하도록 함

        Yields:
            파티 멤버들
        """
        return iter(self.members)

    def __len__(self) -> int:
        """
        Party의 길이는 members의 길이와 같음

        Returns:
            멤버 수
        """
        return len(self.members)

    def __getitem__(self, index):
        """
        인덱스로 멤버 접근 가능하도록 함

        Args:
            index: 멤버 인덱스

        Returns:
            해당 인덱스의 멤버
        """
        return self.members[index]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Party':
        """
        딕셔너리로부터 파티 복원 (로드용)

        Args:
            data: 파티 정보 딕셔너리

        Returns:
            복원된 Party 인스턴스
        """
        # 주의: members 복원은 호출자가 처리해야 함
        # 여기서는 빈 파티로 생성 후 게이지만 복원
        party = cls([])
        party.teamwork_gauge = data.get("teamwork_gauge", 0)
        party.max_teamwork_gauge = data.get("max_teamwork_gauge", 600)
        return party
