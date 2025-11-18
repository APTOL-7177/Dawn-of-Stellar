"""
스킬 효과 테스트
배틀메이지의 룬 새기기와 기계공학자의 부품 조립이 제대로 작동하는지 확인
"""

from src.character.character import Character
from src.character.skills.skill_manager import get_skill_manager
from src.character.skills.job_skills.battle_mage_skills import register_battle_mage_skills
from src.character.skills.job_skills.engineer_skills import register_engineer_skills
from src.core.config import initialize_config

def test_battle_mage_rune():
    """배틀메이지 룬 새기기 테스트"""
    initialize_config()

    # 스킬 등록
    skill_manager = get_skill_manager()
    register_battle_mage_skills(skill_manager)

    print("=" * 70)
    print("배틀메이지 룬 새기기 테스트")
    print("=" * 70)

    # 배틀메이지 생성
    bmage = Character("테스트 배틀메이지", "battle_mage")
    bmage.stat_manager.set_base_value("magic", 50)

    # 적 생성
    enemy = Character("테스트 적", "warrior")
    enemy.stat_manager.set_base_value("defense", 25)

    print(f"\n[전] 배틀메이지 룬 스택: {getattr(bmage, 'rune_stacks', 'N/A')}")
    print(f"[전] 적 status_effects: {getattr(enemy, 'status_effects', 'N/A')}")

    # 룬 새기기 스킬 실행
    if bmage.skills and len(bmage.skills) > 0:
        skill = bmage.skills[0]  # 첫 번째 스킬 (룬 새기기)
        print(f"\n스킬 사용: {skill.name}")
        print(f"스킬 effects: {len(skill.effects)}개")

        for i, effect in enumerate(skill.effects):
            print(f"  Effect {i+1}: {type(effect).__name__}")

        # 스킬 실행
        result = skill.execute(bmage, enemy, {})
        print(f"\n스킬 실행 결과: {result.success}")
        print(f"메시지: {result.message}")
    else:
        print("\n스킬 없음!")

    print(f"\n[후] 배틀메이지 룬 스택: {getattr(bmage, 'rune_stacks', 'N/A')}")
    print(f"[후] 적 status_effects: {getattr(enemy, 'status_effects', 'N/A')}")

    # 적의 status_effects 상세 확인
    if hasattr(enemy, 'status_effects'):
        if isinstance(enemy.status_effects, list):
            print(f"\n적 상태 효과 (리스트): {len(enemy.status_effects)}개")
            for i, effect in enumerate(enemy.status_effects):
                if hasattr(effect, 'name'):
                    print(f"  {i+1}. {effect.name} (duration: {getattr(effect, 'duration', 'N/A')})")
        elif isinstance(enemy.status_effects, dict):
            print(f"\n적 상태 효과 (dict): {enemy.status_effects}")

def test_engineer_parts():
    """기계공학자 부품 조립 테스트"""
    initialize_config()

    # 스킬 등록
    skill_manager = get_skill_manager()
    register_engineer_skills(skill_manager)

    print("\n" + "=" * 70)
    print("기계공학자 부품 조립 테스트")
    print("=" * 70)

    # 기계공학자 생성
    engineer = Character("테스트 기계공학자", "engineer")
    engineer.stat_manager.set_base_value("strength", 50)

    # 적 생성
    enemy = Character("테스트 적", "warrior")
    enemy.stat_manager.set_base_value("defense", 25)

    print(f"\n[전] 기계공학자 부품: {getattr(engineer, 'machine_parts', 'N/A')} / {getattr(engineer, 'max_machine_parts', 'N/A')}")
    print(f"[전] 기계공학자 gimmick_type: {getattr(engineer, 'gimmick_type', 'N/A')}")

    # 부품 조립 스킬 실행
    if engineer.skills and len(engineer.skills) > 0:
        skill = engineer.skills[0]  # 첫 번째 스킬 (부품 조립)
        print(f"\n스킬 사용: {skill.name}")
        print(f"스킬 effects: {len(skill.effects)}개")

        for i, effect in enumerate(skill.effects):
            print(f"  Effect {i+1}: {type(effect).__name__}")
            if hasattr(effect, 'field'):
                print(f"    field: {effect.field}, value: {effect.value}")

        # 스킬 실행
        result = skill.execute(engineer, enemy, {})
        print(f"\n스킬 실행 결과: {result.success}")
        print(f"메시지: {result.message}")
    else:
        print("\n스킬 없음!")

    print(f"\n[후] 기계공학자 부품: {getattr(engineer, 'machine_parts', 'N/A')} / {getattr(engineer, 'max_machine_parts', 'N/A')}")

if __name__ == "__main__":
    test_battle_mage_rune()
    test_engineer_parts()
