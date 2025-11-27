"""
TeamworkSkill - 팀워크 스킬 클래스

팀워크 게이지를 소모하는 강력한 연계 스킬 시스템
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
from src.character.skills.skill import Skill
from src.core.logger import get_logger

logger = get_logger("skill")


@dataclass
class TeamworkCost:
    """팀워크 스킬 비용"""
    gauge: int  # 25~300 (25 단위)
    base_mp: int = 10  # 연쇄 시 기본 MP (시작자는 0)


class TeamworkSkill(Skill):
    """
    팀워크 스킬 클래스

    파티 공유 게이지를 소모하는 강력한 스킬입니다.
    연쇄 시스템으로 여러 캐릭터가 연계하여 사용할 수 있습니다.
    """

    def __init__(
        self,
        skill_id: str,
        name: str,
        description: str = "",
        gauge_cost: int = 100
    ) -> None:
        """
        팀워크 스킬 초기화

        Args:
            skill_id: 스킬 ID
            name: 스킬 이름
            description: 스킬 설명
            gauge_cost: 팀워크 게이지 비용 (25~300)
        """
        super().__init__(skill_id, name, description)
        self.teamwork_cost = TeamworkCost(gauge=gauge_cost)
        self.is_teamwork_skill = True
        self.is_ultimate = False  # 팀워크 스킬은 궁극기 아님

    def calculate_mp_cost(self, chain_count: int) -> int:
        """
        연쇄 단계에 따른 MP 비용 계산

        Args:
            chain_count: 연쇄 단계 (1 = 시작자, 2 = 2번째, ...)

        Returns:
            필요 MP 비용 (시작자는 0)
        """
        if chain_count == 1:
            return 0  # 시작자는 MP 소모 없음

        # 팀워크 게이지 비용에 비례하는 MP 비용 계산
        # 게이지 비용이 25(1셀)이면: 1 × 2^(연쇄수-2)
        # 게이지 비용이 50(2셀)이면: 2 × 2^(연쇄수-2)
        # 게이지 비용이 100(4셀)이면: 4 × 2^(연쇄수-2)
        # 공식: (게이지 비용 / 25) × 2^(연쇄수-2)
        base_multiplier = self.teamwork_cost.gauge // 25
        mp_cost = base_multiplier * (2 ** (chain_count - 2))
        return mp_cost

    def can_use(
        self,
        user: Any,
        party: Optional[Any] = None,
        chain_count: int = 1,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        팀워크 스킬 사용 가능 여부 확인

        Args:
            user: 스킬 사용자 (Character)
            party: 파티 (Party 인스턴스) - 게이지 체크용
            chain_count: 연쇄 단계
            context: 추가 컨텍스트

        Returns:
            (사용 가능 여부, 이유 메시지)
        """
        # 기본 상태 체크 (부모 클래스)
        can_use_base, reason_base = super().can_use(user, context)
        if not can_use_base:
            return False, reason_base

        # 파티 없으면 사용 불가
        if party is None:
            return False, "파티 정보가 없습니다"

        # 팀워크 게이지 체크
        if party.teamwork_gauge < self.teamwork_cost.gauge:
            return False, (
                f"팀워크 게이지 부족 "
                f"(필요: {self.teamwork_cost.gauge}, 현재: {party.teamwork_gauge})"
            )

        # MP 체크 (시작자가 아니면)
        if chain_count > 1:
            mp_cost = self.calculate_mp_cost(chain_count)
            current_mp = user.current_mp if hasattr(user, 'current_mp') else user.stat_manager.current_mp
            if current_mp < mp_cost:
                return False, (
                    f"MP 부족 "
                    f"(필요: {mp_cost}, 현재: {current_mp})"
                )

        return True, "사용 가능"

    def __repr__(self) -> str:
        """스킬 정보 표현"""
        return (
            f"TeamworkSkill("
            f"id={self.skill_id}, "
            f"name={self.name}, "
            f"cost={self.teamwork_cost.gauge}"
            f")"
        )
