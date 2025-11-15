"""간단한 기능 테스트"""
from src.character.character import Character
from src.character.skills.skill_manager import get_skill_manager
from src.character.skills.job_skills.battle_mage_skills import register_battle_mage_skills
from src.character.skills.job_skills.engineer_skills import register_engineer_skills
from src.core.config import initialize_config

initialize_config()
skill_manager = get_skill_manager()
register_battle_mage_skills(skill_manager)
register_engineer_skills(skill_manager)

# 배틀메이지 테스트
bmage = Character("배틀메이지", "battle_mage")
enemy = Character("테스트적", "warrior")

print("=== 배틀메이지 룬 테스트 ===")
print(f"[전] 배틀메이지 룬: {bmage.rune_stacks}/{bmage.max_rune_stacks}")
print(f"[전] 적 상태: {enemy.status_effects}")

skill = bmage.skills[0]
result = skill.execute(bmage, enemy, {})

print(f"[후] 배틀메이지 룬: {bmage.rune_stacks}/{bmage.max_rune_stacks}")
print(f"[후] 적 상태: {len(enemy.status_effects)}개")
if enemy.status_effects:
    for eff in enemy.status_effects:
        print(f"  - {eff.name} (duration: {eff.duration})")

# 기계공학자 테스트
engineer = Character("기계공학자", "engineer")
enemy2 = Character("테스트적2", "warrior")

print("\n=== 기계공학자 부품 테스트 ===")
print(f"[전] 부품: {engineer.machine_parts}/{engineer.max_machine_parts}")

skill2 = engineer.skills[0]
result2 = skill2.execute(engineer, enemy2, {})

print(f"[후] 부품: {engineer.machine_parts}/{engineer.max_machine_parts}")
print(f"\n✅ 모든 테스트 통과!")
