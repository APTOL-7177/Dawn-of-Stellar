"""
팀워크 게이지 시스템 종합 통합 테스트

구현 가이드의 모든 기능을 엔드투엔드로 검증합니다:
- 전투 시작 및 Party 초기화
- 게이지 축적 (행동별 증가량)
- 팀워크 스킬 실행 및 게이지 소모
- 연쇄 시스템 (MP 비용 계산)
- 저장/로드 시스템 (게이지 영속성)
- UI 표시 기능
"""

import sys
import tempfile
import os
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from src.character.party import Party
from src.character.skills.teamwork_skill import TeamworkSkill
from src.character.character import Character
from src.combat.combat_manager import CombatManager, ActionType
from src.ui.teamwork_gauge_display import TeamworkGaugeDisplay, ChainPrompt
from src.persistence.save_system import SaveSystem
from src.core.logger import get_logger

logger = get_logger("test")


class TestTeamworkComprehensive:
    """팀워크 게이지 시스템 종합 테스트"""

    @pytest.fixture
    def combat_manager(self):
        """CombatManager 설정"""
        cm = CombatManager()
        
        # 테스트용 캐릭터 생성
        warrior = Character("전사", "warrior")
        archer = Character("궁수", "archer")
        enemies = [Character("적", "warrior")]  # goblin 대신 기존 클래스 사용
        
        # 전투 시작 (Party 자동 생성)
        cm.start_combat([warrior, archer], enemies)
        
        return cm

    def test_combat_initialization_and_party_creation(self, combat_manager):
        """전투 시작 시 Party 초기화 검증"""
        assert combat_manager.party is not None
        assert combat_manager.party.teamwork_gauge == 0
        assert combat_manager.party.max_teamwork_gauge == 600
        assert len(combat_manager.party.members) == 2
        assert combat_manager.party.chain_active == False
        assert combat_manager.party.chain_count == 0

    def test_gauge_accumulation_by_action_types(self, combat_manager):
        """행동 타입별 게이지 증가량 검증"""
        initial_gauge = combat_manager.party.teamwork_gauge
        
        # BRV 공격: +5
        combat_manager.update_teamwork_gauge(ActionType.BRV_ATTACK)
        assert combat_manager.party.teamwork_gauge == initial_gauge + 5
        
        # HP 공격: +8
        combat_manager.update_teamwork_gauge(ActionType.HP_ATTACK)
        assert combat_manager.party.teamwork_gauge == initial_gauge + 5 + 8
        
        # BRV+HP 공격: +10
        combat_manager.update_teamwork_gauge(ActionType.BRV_HP_ATTACK)
        assert combat_manager.party.teamwork_gauge == initial_gauge + 5 + 8 + 10
        
        # 스킬: +6
        combat_manager.update_teamwork_gauge(ActionType.SKILL)
        assert combat_manager.party.teamwork_gauge == initial_gauge + 5 + 8 + 10 + 6

    def test_gauge_accumulation_with_bonuses(self, combat_manager):
        """크리티컬, BREAK, 회복, 피격 보너스 검증"""
        initial_gauge = combat_manager.party.teamwork_gauge
        
        # BRV+HP 공격 + 크리티컬 + BREAK: 10 + 3 + 15 = 28
        combat_manager.update_teamwork_gauge(
            ActionType.BRV_HP_ATTACK,
            is_critical=True,
            caused_break=True
        )
        assert combat_manager.party.teamwork_gauge == initial_gauge + 28

    def test_gauge_limits_and_overflow(self, combat_manager):
        """게이지 최대값 및 오버플로우 방지 검증"""
        # 게이지를 최대값으로 설정
        combat_manager.party.teamwork_gauge = 600
        
        # 추가 증가 시도
        combat_manager.update_teamwork_gauge(ActionType.BRV_HP_ATTACK)
        
        # 최대값을 초과하지 않아야 함
        assert combat_manager.party.teamwork_gauge == 600

    def test_teamwork_skill_creation_and_cost(self, combat_manager):
        """팀워크 스킬 생성 및 비용 검증"""
        skill = TeamworkSkill(
            "test_teamwork",
            "테스트 스킬",
            "테스트용 팀워크 스킬",
            gauge_cost=125
        )
        
        assert skill.skill_id == "test_teamwork"
        assert skill.name == "테스트 스킬"
        assert skill.teamwork_cost.gauge == 125
        assert skill.is_teamwork_skill == True

    def test_teamwork_skill_mp_cost_calculation(self, combat_manager):
        """연쇄 단계별 MP 비용 계산 검증"""
        skill = TeamworkSkill("test", "테스트", gauge_cost=100)
        
        # 시작자: MP 0
        assert skill.calculate_mp_cost(1) == 0
        
        # 2단계: (100/25) * 2^(0) = 4 * 1 = 4
        assert skill.calculate_mp_cost(2) == 4
        
        # 3단계: (100/25) * 2^(1) = 4 * 2 = 8
        assert skill.calculate_mp_cost(3) == 8
        
        # 4단계: (100/25) * 2^(2) = 4 * 4 = 16
        assert skill.calculate_mp_cost(4) == 16

    def test_teamwork_skill_usage_validation(self, combat_manager):
        """팀워크 스킬 사용 가능 여부 검증"""
        skill = TeamworkSkill("test", "테스트", gauge_cost=100)
        warrior = combat_manager.allies[0]
        
        # 게이지 부족 시 사용 불가
        can_use, reason = skill.can_use(warrior, combat_manager.party)
        assert can_use == False
        assert "팀워크 게이지 부족" in reason
        
        # 게이지 충분 시 사용 가능
        combat_manager.party.teamwork_gauge = 100
        can_use, reason = skill.can_use(warrior, combat_manager.party)
        assert can_use == True
        assert reason == "사용 가능"

    def test_chain_system_management(self, combat_manager):
        """연쇄 시스템 관리 검증"""
        warrior = combat_manager.allies[0]
        
        # 연쇄 시작
        combat_manager.party.start_chain(warrior)
        assert combat_manager.party.chain_active == True
        assert combat_manager.party.chain_count == 1
        assert combat_manager.party.chain_starter == warrior
        
        # 연쇄 계속
        mp_cost = combat_manager.party.continue_chain()
        assert combat_manager.party.chain_count == 2
        assert mp_cost == 10  # 기본값
        
        # 연쇄 종료
        combat_manager.party.end_chain()
        assert combat_manager.party.chain_active == False
        assert combat_manager.party.chain_count == 0

    def test_teamwork_skill_execution(self, combat_manager):
        """팀워크 스킬 실행 검증"""
        # 테스트용 팀워크 스킬 생성
        skill = TeamworkSkill("test", "테스트", gauge_cost=50)
        warrior = combat_manager.allies[0]
        enemy = combat_manager.enemies[0]
        
        # 게이지 설정
        combat_manager.party.teamwork_gauge = 50
        
        # 스킬 실행
        success = combat_manager.execute_teamwork_skill(
            actor=warrior,
            skill=skill,
            target=enemy,
            is_chain_start=True
        )
        
        assert success == True
        assert combat_manager.party.teamwork_gauge == 0  # 게이지 소모
        assert combat_manager.party.chain_active == True  # 연쇄 시작

    def test_chain_continuation_execution(self, combat_manager):
        """연쇄 계속 실행 검증"""
        # 첫 번째 스킬 실행
        skill1 = TeamworkSkill("test1", "테스트1", gauge_cost=50)
        warrior = combat_manager.allies[0]
        enemy = combat_manager.enemies[0]
        
        combat_manager.party.teamwork_gauge = 100
        combat_manager.execute_teamwork_skill(warrior, skill1, enemy, is_chain_start=True)
        
        # 두 번째 스킬로 연쇄 계속
        skill2 = TeamworkSkill("test2", "테스트2", gauge_cost=50)
        archer = combat_manager.allies[1]
        
        # MP 설정
        archer.current_mp = 20
        
        success = combat_manager.execute_teamwork_skill(
            actor=archer,
            skill=skill2,
            target=enemy,
            is_chain_start=False
        )
        
        assert success == True
        assert combat_manager.party.chain_count == 2

    def test_save_load_persistence(self, combat_manager):
        """저장/로드 시스템 게이지 영속성 검증"""
        # 게이지 설정
        combat_manager.party.teamwork_gauge = 250
        combat_manager.party.max_teamwork_gauge = 600
        
        # 저장 시스템 테스트
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            # 저장
            save_system = SaveSystem()
            game_state = {
                "party_members": [warrior.to_dict() for warrior in combat_manager.allies],
                "current_area": "test_area"
            }
            
            save_system.save_game(temp_path, game_state)
            
            # 모듈 레벨 변수 확인
            import src.persistence.save_system as save_module
            assert hasattr(save_module, '_last_loaded_teamwork_gauge')
            
            # 새 CombatManager 생성 및 게이지 복원
            new_cm = CombatManager()
            new_cm.start_combat(combat_manager.allies, combat_manager.enemies)
            
            # 복원 확인
            assert new_cm.party.teamwork_gauge == 250
            assert new_cm.party.max_teamwork_gauge == 600
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_ui_display_formatting(self, combat_manager):
        """UI 게이지 표시 형식화 검증"""
        combat_manager.party.teamwork_gauge = 300
        
        # 기본 게이지 표시
        gauge_display = TeamworkGaugeDisplay.format_gauge(300, 600)
        assert "300/600" in gauge_display
        assert "12셀" in gauge_display  # 300 // 25 = 12
        
        # 스킬 메뉴용 형식
        skill_info = TeamworkGaugeDisplay.format_for_skill_menu(100, 300, 600)
        assert "필요: 100" in skill_info
        assert "현재: 300" in skill_info

    def test_chain_prompt_formatting(self, combat_manager):
        """연쇄 제안 화면 형식화 검증"""
        combat_manager.party.start_chain(combat_manager.allies[0])
        
        prompt = ChainPrompt.format_prompt(
            chain_count=2,
            chain_starter_name="전사",
            current_skill_name="일제사격",
            current_skill_cost=150,
            current_actor_name="궁수",
            teamwork_gauge=350,
            current_mp=45,
            required_mp=10
        )
        
        assert "연쇄 2단계" in prompt
        assert "전사" in prompt
        assert "일제사격" in prompt
        assert "궁수" in prompt

    def test_complete_gameplay_cycle(self, combat_manager):
        """완전한 게임플레이 사이클 통합 테스트"""
        warrior = combat_manager.allies[0]
        archer = combat_manager.allies[1]
        enemy = combat_manager.enemies[0]
        
        # 1. 전투 시작 및 초기 상태 확인
        assert combat_manager.party.teamwork_gauge == 0
        
        # 2. 여러 행동으로 게이지 축적
        for _ in range(10):
            combat_manager.update_teamwork_gauge(ActionType.BRV_HP_ATTACK)
        
        expected_gauge = 10 * 10  # 100
        assert combat_manager.party.teamwork_gauge == expected_gauge
        
        # 3. 팀워크 스킬 생성 및 실행
        skill = TeamworkSkill("ultimate", "궁극기", gauge_cost=100)
        success = combat_manager.execute_teamwork_skill(warrior, skill, enemy, is_chain_start=True)
        
        assert success == True
        assert combat_manager.party.teamwork_gauge == 0
        assert combat_manager.party.chain_active == True
        
        # 4. 연쇄 계속
        archer.current_mp = 20
        skill2 = TeamworkSkill("followup", "후속타", gauge_cost=50)
        
        # 추가 게이지 필요
        combat_manager.party.teamwork_gauge = 50
        success = combat_manager.execute_teamwork_skill(archer, skill2, enemy, is_chain_start=False)
        
        assert success == True
        assert combat_manager.party.chain_count == 2
        
        # 5. 연쇄 종료
        combat_manager.party.end_chain()
        assert combat_manager.party.chain_active == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
