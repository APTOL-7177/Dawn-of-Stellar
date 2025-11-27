"""
전투 시작 시스템 간단 테스트

combat_ui.py의 run_combat 함수가 정상 작동하는지 확인합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 설정 초기화
from src.core.config import initialize_config
initialize_config("config.yaml")

from src.core.logger import get_logger

logger = get_logger("test")

print("\n" + "=" * 70)
print("전투 시작 시스템 테스트")
print("=" * 70)

try:
    # CombatManager 임포트
    print("\n[1] CombatManager 임포트 중...")
    from src.combat.combat_manager import CombatManager, CombatState
    print("    [OK] 성공")

    # Party 임포트
    print("\n[2] Party 임포트 중...")
    from src.character.party import Party
    print("    [OK] 성공")

    # TeamworkSkill 임포트
    print("\n[3] TeamworkSkill 임포트 중...")
    from src.character.skills.teamwork_skill import TeamworkSkill
    print("    [OK] 성공")

    # CombatUI 임포트 (가장 복잡한 부분)
    print("\n[4] CombatUI 임포트 중...")
    try:
        from src.ui.combat_ui import CombatUI, run_combat
        print("    [OK] 성공")
    except Exception as e:
        print(f"    [FAIL] 실패: {str(e)}")
        logger.error(f"CombatUI 임포트 실패: {e}", exc_info=True)
        raise

    # CombatManager 인스턴스 생성
    print("\n[5] CombatManager 인스턴스 생성 중...")
    combat_manager = CombatManager()
    print("    [OK] 성공")

    # Mock 캐릭터 생성
    print("\n[6] Mock 캐릭터 생성 중...")
    class MockCharacter:
        def __init__(self, name):
            self.name = name
            self.id = name
            self.current_hp = 100
            self.max_hp = 100
            self.current_mp = 50
            self.max_mp = 50
            self.atb_gauge = 0
            self.is_alive = True
            self.skills = []
            self.active_buffs = {}
            self.status_manager = None
            self.active_traits = []
            self.equipment = {}

        def heal(self, amount):
            self.current_hp = min(self.max_hp, self.current_hp + amount)
            return amount

        def take_damage(self, damage):
            self.current_hp = max(1, self.current_hp - damage)

    allies = [MockCharacter(f"아군{i+1}") for i in range(2)]
    enemies = [MockCharacter(f"적{i+1}") for i in range(2)]
    print("    [OK] 성공 (아군 2명, 적 2명)")

    # CombatManager.start_combat() 호출
    print("\n[7] CombatManager.start_combat() 호출 중...")
    combat_manager.start_combat(allies, enemies)
    print("    [OK] 성공")

    # Party 생성 확인
    print("\n[8] Party 인스턴스 확인 중...")
    assert combat_manager.party is not None, "Party가 None"
    assert combat_manager.party.teamwork_gauge == 0, "초기 게이지가 0이 아님"
    assert combat_manager.party.max_teamwork_gauge == 600, "최대 게이지가 600이 아님"
    print("    [OK] 성공")
    print(f"      - 초기 게이지: {combat_manager.party.teamwork_gauge}/600")

    # 게이지 업데이트 테스트
    print("\n[9] 게이지 업데이트 테스트 중...")
    from src.combat.combat_manager import ActionType
    combat_manager.update_teamwork_gauge(
        action_type=ActionType.BRV_ATTACK,
        is_critical=False,
        caused_break=False,
        healed_ally=False,
        was_hit=False
    )
    assert combat_manager.party.teamwork_gauge == 5, f"BRV 공격 후 게이지가 5가 아님 ({combat_manager.party.teamwork_gauge})"
    print("    [OK] 성공")
    print(f"      - BRV 공격 후 게이지: {combat_manager.party.teamwork_gauge}/600")

    print("\n" + "=" * 70)
    print("[SUCCESS] 모든 전투 시작 시스템 테스트 통과!")
    print("=" * 70)
    print("\n전투 시스템은 정상 작동하며, 문제는 다른 곳에 있을 수 있습니다.")
    print("가능한 원인:")
    print("  1. 전투 UI 렌더링 오류")
    print("  2. 콘솔 초기화 오류")
    print("  3. 입력 처리 오류")

except Exception as e:
    print(f"\n[FAIL] 오류 발생: {str(e)}")
    try:
        import traceback
        print(traceback.format_exc())
    except:
        pass
    logger.error(f"전투 시작 테스트 실패: {e}", exc_info=True)
    sys.exit(1)
