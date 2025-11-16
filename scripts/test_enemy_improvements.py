"""적 개선사항 테스트 스크립트"""

import sys
sys.path.insert(0, "X:/develop/Dos")

from src.core.config import initialize_config
from src.world.enemy_generator import EnemyGenerator, ENEMY_TEMPLATES
from src.combat.enemy_skills import EnemySkillDatabase
from src.ai.enemy_ai import create_ai_for_enemy

# Config 초기화
initialize_config("config.yaml")

def test_enemy_generation():
    """적 생성 테스트"""
    print("=" * 70)
    print("적 생성 테스트")
    print("=" * 70)

    # 1층, 5층, 10층에서 적 생성
    for floor in [1, 5, 10]:
        print(f"\n[{floor}층 적 생성]")
        enemies = EnemyGenerator.generate_enemies(floor)

        print(f"생성된 적 수: {len(enemies)}마리 (기대: 2-4마리)")

        for i, enemy in enumerate(enemies, 1):
            print(f"\n  적 #{i}: {enemy.name}")
            print(f"    레벨: {enemy.level}")
            print(f"    HP: {enemy.current_hp}/{enemy.max_hp}")
            print(f"    MP: {enemy.current_mp}/{enemy.max_mp}")
            print(f"    BRV: {enemy.current_brv}/{enemy.max_brv}")
            print(f"    공격력: 물리 {enemy.physical_attack}, 마법 {enemy.magic_attack}")
            print(f"    방어력: 물리 {enemy.physical_defense}, 마법 {enemy.magic_defense}")
            print(f"    스킬 수: {len(enemy.skills)}개")

            if enemy.skills:
                print(f"    스킬 목록:")
                for skill in enemy.skills:
                    print(f"      - {skill.name} (사용확률: {skill.use_probability*100:.0f}%, 쿨다운: {skill.cooldown})")

def test_enemy_skills():
    """적 스킬 데이터베이스 테스트"""
    print("\n" + "=" * 70)
    print("적 스킬 데이터베이스 테스트")
    print("=" * 70)

    EnemySkillDatabase.initialize()

    # 모든 적 타입에 대해 스킬 확인
    enemy_types = [
        "slime", "goblin", "wolf",
        "orc", "skeleton", "dark_mage",
        "ogre", "wraith", "golem",
        "troll", "vampire", "wyvern",
        "demon", "dragon"
    ]

    print(f"\n총 스킬 수: {len(EnemySkillDatabase.SKILLS)}개")

    for enemy_type in enemy_types:
        skills = EnemySkillDatabase.get_skills_for_enemy_type(enemy_type)
        print(f"\n{enemy_type}: {len(skills)}개 스킬")
        for skill in skills:
            damage_type = "마법" if skill.is_magical else "물리"
            print(f"  - {skill.name} ({damage_type}, 배율: {skill.damage_multiplier}x)")

def test_enemy_ai():
    """적 AI 테스트"""
    print("\n" + "=" * 70)
    print("적 AI 공격성 테스트")
    print("=" * 70)

    # 여러 적 생성
    enemies = EnemyGenerator.generate_enemies(5, num_enemies=3)

    for enemy in enemies:
        ai = create_ai_for_enemy(enemy)
        print(f"\n{enemy.name}의 AI:")
        print(f"  난이도: {ai.difficulty}")
        print(f"  스킬 사용 배율: {ai.skill_use_multiplier}x")
        print(f"  스킬 수: {len(enemy.skills)}개")

def test_skill_variety():
    """스킬 다양성 테스트"""
    print("\n" + "=" * 70)
    print("스킬 다양성 및 밸런스 테스트")
    print("=" * 70)

    EnemySkillDatabase.initialize()

    # 스킬 타입별 분류
    brv_skills = []
    hp_skills = []
    buff_skills = []
    debuff_skills = []
    heal_skills = []

    for skill_id, skill in EnemySkillDatabase.SKILLS.items():
        if skill.brv_damage > 0:
            brv_skills.append(skill)
        if skill.hp_attack:
            hp_skills.append(skill)
        if skill.buff_stats:
            buff_skills.append(skill)
        if skill.debuff_stats:
            debuff_skills.append(skill)
        if skill.heal_amount > 0:
            heal_skills.append(skill)

    print(f"\n스킬 타입별 통계:")
    print(f"  BRV 공격 스킬: {len(brv_skills)}개")
    print(f"  HP 공격 스킬: {len(hp_skills)}개")
    print(f"  버프 스킬: {len(buff_skills)}개")
    print(f"  디버프 스킬: {len(debuff_skills)}개")
    print(f"  회복 스킬: {len(heal_skills)}개")

    print(f"\n가장 강력한 스킬 Top 5:")
    strong_skills = sorted(
        EnemySkillDatabase.SKILLS.values(),
        key=lambda s: s.damage_multiplier * (2 if s.hp_attack else 1),
        reverse=True
    )[:5]

    for i, skill in enumerate(strong_skills, 1):
        attack_type = "BRV+HP" if skill.hp_attack else "BRV"
        damage_type = "마법" if skill.is_magical else "물리"
        print(f"  {i}. {skill.name} ({attack_type}, {damage_type}, 배율: {skill.damage_multiplier}x)")

if __name__ == "__main__":
    print("\n적 개선사항 종합 테스트 시작!\n")

    test_enemy_generation()
    test_enemy_skills()
    test_enemy_ai()
    test_skill_variety()

    print("\n" + "=" * 70)
    print("테스트 완료!")
    print("=" * 70)
    print("\n변경사항 요약:")
    print("1. 적 AI 난이도: normal → hard (스킬 사용 확률 2배)")
    print("2. 모든 적 타입에 2-3개 스킬 추가")
    print("3. 적 조우 시 적 수: 1-4마리 → 2-4마리")
    print("4. 총 스킬 수: 기존 대비 2배 이상 증가")
    print("\n게임 난이도가 대폭 상승했습니다!")
    print("=" * 70)
