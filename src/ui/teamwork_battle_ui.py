"""
팀워크 게이지 시스템 전투 UI 통합

전투 화면에 팀워크 게이지를 표시하고 연쇄 제안을 처리합니다.
"""

from typing import Optional, List, Tuple
from src.ui.teamwork_gauge_display import TeamworkGaugeDisplay, ChainPrompt
from src.core.logger import get_logger

logger = get_logger("ui")


class TeamworkBattleUI:
    """전투 화면에서의 팀워크 게이지 UI 관리"""

    @staticmethod
    def display_gauge_status(combat_manager) -> str:
        """
        전투 화면에 표시할 게이지 상태

        Args:
            combat_manager: CombatManager 인스턴스

        Returns:
            게이지 상태 문자열
        """
        if not combat_manager.party:
            return ""

        return TeamworkGaugeDisplay.format_compact(
            combat_manager.party.teamwork_gauge,
            combat_manager.party.max_teamwork_gauge
        )

    @staticmethod
    def display_skill_menu(skills: List[object], actor: object, combat_manager) -> str:
        """
        스킬 선택 메뉴 (팀워크 스킬 정보 포함)

        Args:
            skills: 사용 가능한 스킬 리스트
            actor: 현재 캐릭터
            combat_manager: CombatManager 인스턴스

        Returns:
            스킬 메뉴 문자열
        """
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━ 스킬 선택 ━━━━━━━━━━━━━━━━━━━━━",
            ""
        ]

        party = combat_manager.party
        actor_mp = actor.current_mp if hasattr(actor, 'current_mp') else 0

        for i, skill in enumerate(skills, 1):
            is_teamwork = hasattr(skill, 'is_teamwork_skill') and skill.is_teamwork_skill

            if is_teamwork:
                # 팀워크 스킬
                mp_cost = skill.calculate_mp_cost(
                    party.chain_count if party.chain_active else 1
                )
                gauge_cost = skill.teamwork_cost.gauge
                can_use = party.teamwork_gauge >= gauge_cost and actor_mp >= mp_cost

                status = "[O]" if can_use else "[X]"
                info = f"{i}. {status} {skill.name}"
                info += f" [게이지: {gauge_cost}, MP: {mp_cost}]"

                lines.append(info)
            else:
                # 일반 스킬
                can_use = True
                if hasattr(skill, 'costs') and skill.costs:
                    for cost in skill.costs:
                        if hasattr(cost, 'can_afford'):
                            can_use, _ = cost.can_afford(actor, {})
                            if not can_use:
                                break

                status = "[O]" if can_use else "[X]"
                info = f"{i}. {status} {skill.name}"

                if hasattr(skill, 'costs') and skill.costs:
                    for cost in skill.costs:
                        if hasattr(cost, '__class__') and 'MP' in cost.__class__.__name__:
                            if hasattr(cost, 'amount'):
                                info += f" [MP: {cost.amount}]"

                lines.append(info)

        lines.append("━" * 55)
        return "\n".join(lines)

    @staticmethod
    def show_chain_prompt(
        combat_manager,
        next_actor: object,
        next_skill: object
    ) -> str:
        """
        연쇄 제안 화면 표시

        Args:
            combat_manager: CombatManager 인스턴스
            next_actor: 다음 주자
            next_skill: 사용할 팀워크 스킬

        Returns:
            연쇄 제안 화면 문자열
        """
        party = combat_manager.party
        chain_count = party.chain_count + 1  # 다음 단계
        mp_cost = next_skill.calculate_mp_cost(chain_count)
        actor_mp = next_actor.current_mp if hasattr(next_actor, 'current_mp') else 0

        return ChainPrompt.format_prompt(
            chain_count=chain_count,
            chain_starter_name=party.chain_starter.name,
            current_skill_name=next_skill.name,
            current_skill_description=next_skill.description,
            current_skill_cost=next_skill.teamwork_cost.gauge,
            current_actor_name=next_actor.name,
            teamwork_gauge=party.teamwork_gauge,
            current_mp=actor_mp,
            required_mp=mp_cost
        )

    @staticmethod
    def show_action_result(actor_name: str, skill_name: str, damage: int = 0,
                          healed: int = 0) -> str:
        """
        행동 결과 표시

        Args:
            actor_name: 행동자 이름
            skill_name: 스킬 이름
            damage: 입힌 데미지
            healed: 회복량

        Returns:
            행동 결과 문자열
        """
        lines = [f"\n{actor_name}의 '{skill_name}' 발동!"]

        if damage > 0:
            lines.append(f"데미지: {damage}")
        if healed > 0:
            lines.append(f"회복: {healed}")

        return "\n".join(lines)

    @staticmethod
    def show_gauge_update(old_gauge: int, new_gauge: int, max_gauge: int = 600) -> str:
        """
        게이지 변화 표시

        Args:
            old_gauge: 이전 게이지
            new_gauge: 새 게이지
            max_gauge: 최대 게이지

        Returns:
            게이지 변화 문자열
        """
        change = new_gauge - old_gauge
        old_cells = old_gauge // 25
        new_cells = new_gauge // 25

        if change > 0:
            symbol = "▲"
        elif change < 0:
            symbol = "▼"
        else:
            return ""

        return (
            f"팀워크 게이지 {symbol} {old_cells}셀 → {new_cells}셀 "
            f"({new_gauge}/{max_gauge})"
        )


class TeamworkSkillSelector:
    """팀워크 스킬 선택 헬퍼"""

    @staticmethod
    def find_available_teamwork_skills(skills: List[object], actor: object,
                                       combat_manager) -> List[object]:
        """
        사용 가능한 팀워크 스킬 찾기

        Args:
            skills: 전체 스킬 리스트
            actor: 현재 캐릭터
            combat_manager: CombatManager 인스턴스

        Returns:
            사용 가능한 팀워크 스킬 리스트
        """
        from src.core.logger import get_logger
        logger = get_logger("teamwork_selector")

        available = []
        teamwork_skills_found = 0

        logger.debug(f"[TEAMWORK_SELECTOR] 스킬 검색 시작: {len(skills)}개 스킬 중 팀워크 스킬 찾기")

        for skill in skills:
            if hasattr(skill, 'is_teamwork_skill') and skill.is_teamwork_skill:
                teamwork_skills_found += 1
                logger.debug(f"[TEAMWORK_SELECTOR] 팀워크 스킬 발견: {skill.name} ({skill.teamwork_cost.gauge}게이지)")

                # 파티 정보 확인
                party = getattr(combat_manager, 'party', None)
                if not party:
                    logger.warning(f"[TEAMWORK_SELECTOR] 파티 정보 없음")
                    continue

                logger.debug(f"[TEAMWORK_SELECTOR] 팀워크 게이지: {party.teamwork_gauge}/{party.max_teamwork_gauge}")

                chain_count = party.chain_count if getattr(party, 'chain_active', False) else 1
                logger.debug(f"[TEAMWORK_SELECTOR] 연쇄 단계: {chain_count}")

                can_use, reason = skill.can_use(actor, {'party': party, 'chain_count': chain_count})
                logger.debug(f"[TEAMWORK_SELECTOR] {skill.name} 사용 가능: {can_use} (이유: {reason})")

                if can_use:
                    available.append(skill)
                    logger.debug(f"[TEAMWORK_SELECTOR] {skill.name} 추가됨")

        logger.debug(f"[TEAMWORK_SELECTOR] 결과: {teamwork_skills_found}개 팀워크 스킬 발견, {len(available)}개 사용 가능")
        return available

    @staticmethod
    def can_continue_chain(actor: object, skill: object,
                          combat_manager) -> Tuple[bool, str]:
        """
        연쇄를 계속할 수 있는지 확인

        Args:
            actor: 현재 캐릭터
            skill: 사용할 팀워크 스킬
            combat_manager: CombatManager 인스턴스

        Returns:
            (가능 여부, 이유)
        """
        if not combat_manager.party.chain_active:
            return False, "활성 연쇄가 없습니다"

        party = combat_manager.party
        mp_cost = skill.calculate_mp_cost(party.chain_count + 1)
        actor_mp = actor.current_mp if hasattr(actor, 'current_mp') else 0

        # 게이지 확인
        if party.teamwork_gauge < skill.teamwork_cost.gauge:
            return False, f"게이지 부족 ({party.teamwork_gauge}/{skill.teamwork_cost.gauge})"

        # MP 확인
        if actor_mp < mp_cost:
            return False, f"MP 부족 ({actor_mp}/{mp_cost})"

        return True, "사용 가능"


class CombatLogDisplay:
    """전투 로그 표시"""

    def __init__(self):
        self.logs: List[str] = []

    def add_action_log(self, actor_name: str, action: str, details: str = "") -> None:
        """행동 로그 추가"""
        log = f"[{actor_name}] {action}"
        if details:
            log += f" - {details}"
        self.logs.append(log)

    def add_gauge_log(self, change: int, reason: str) -> None:
        """게이지 변화 로그 추가"""
        symbol = "+" if change > 0 else "-"
        self.logs.append(f"  팀워크 게이지 {symbol}{abs(change)} ({reason})")

    def add_chain_log(self, event: str) -> None:
        """연쇄 이벤트 로그 추가"""
        self.logs.append(f"🔗 {event}")

    def display(self, max_lines: int = 10) -> str:
        """로그 표시"""
        recent_logs = self.logs[-max_lines:]
        return "\n".join(recent_logs)

    def clear(self) -> None:
        """로그 초기화"""
        self.logs.clear()


# 테스트용
if __name__ == "__main__":
    from src.character.character import Character
    from src.combat.combat_manager import get_combat_manager

    # 테스트 실행
    print("[테스트] 팀워크 전투 UI")
    print("=" * 60)

    # 문자 생성 불가능 (의존성 문제)하므로 UI만 테스트
    print("\n[게이지 상태]")
    gauge_str = TeamworkGaugeDisplay.format_compact(450, 600)
    print(gauge_str)

    print("\n[스킬 메뉴 예시]")
    menu = """━━━━━━━━━━━━━━━━━━━━━ 스킬 선택 ━━━━━━━━━━━━━━━━━━━━━

1. [O] 강타 [MP: 0]
2. [O] 전장의 돌격 [게이지: 125, MP: 0]
3. [X] 궁극기 [MP: 30]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    print(menu)

    print("\n[연쇄 제안 화면 예시]")
    prompt = ChainPrompt.format_prompt(
        chain_count=2,
        chain_starter_name="전사",
        current_skill_name="일제사격",
        current_skill_description="마킹된 모든 아군의 지원사격을 한꺼번에 발사",
        current_skill_cost=150,
        current_actor_name="궁수",
        teamwork_gauge=300,
        current_mp=45,
        required_mp=10
    )
    print(prompt)

    print("\n[테스트 완료]")
