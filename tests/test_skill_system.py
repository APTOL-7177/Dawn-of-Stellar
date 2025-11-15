"""
Skills System Test - 스킬 시스템 테스트

검성 스킬을 중심으로 스킬 시스템 테스트
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.character.character import Character
from src.character.skills.skill_manager import get_skill_manager
from src.character.skills.job_skills.sword_saint_skills import (
    create_sword_saint_skills,
    register_sword_saint_skills
)
from src.combat.brave_system import get_brave_system


def test_sword_saint_skills():
    """검성 스킬 테스트"""
    print("=" * 60)
    print("검성 스킬 시스템 테스트")
    print("=" * 60)

    # 스킬 관리자 초기화
    skill_manager = get_skill_manager()
    brave_system = get_brave_system()

    # 검성 스킬 등록
    skill_ids = register_sword_saint_skills(skill_manager)
    print(f"\n✅ 검성 스킬 {len(skill_ids)}개 등록 완료")

    # 검성 캐릭터 생성
    sword_saint = Character(
        name="검성 테스터",
        character_class="sword_saint",
        level=10
    )
    sword_saint.skill_ids = skill_ids

    # 적 생성
    enemy = Character(
        name="고블린",
        character_class="warrior",  # 임시
        level=5
    )
    enemy.is_enemy = True

    # BRV 초기화
    brave_system.initialize_brv(sword_saint)
    brave_system.initialize_brv(enemy)

    print(f"\n🗡️ {sword_saint.name} (Lv.{sword_saint.level})")
    print(f"   HP: {sword_saint.current_hp}/{sword_saint.max_hp}")
    print(f"   MP: {sword_saint.current_mp}/{sword_saint.max_mp}")
    print(f"   BRV: {sword_saint.current_brv}/{sword_saint.max_brv}")
    print(f"   검기 스택: {sword_saint.sword_aura}/{sword_saint.max_sword_aura}")

    print(f"\n👹 {enemy.name} (Lv.{enemy.level})")
    print(f"   HP: {enemy.current_hp}/{enemy.max_hp}")
    print(f"   BRV: {enemy.current_brv}/{enemy.max_brv}")

    # ===== 테스트 1: 검기 베기 (기본 BRV 공격) =====
    print("\n" + "-" * 60)
    print("테스트 1: 검기 베기 (기본 BRV 공격)")
    print("-" * 60)

    skill = skill_manager.get_skill("sword_saint_kenkizan")
    print(f"\n스킬: {skill.name}")
    print(f"설명: {skill.get_description(sword_saint)}")

    result = skill_manager.execute_skill(
        skill_id="sword_saint_kenkizan",
        user=sword_saint,
        target=enemy
    )

    print(f"\n결과: {result.message}")
    if result.success:
        print(f"  - BRV 데미지: {result.total_damage}")
        print(f"  - 검기 스택: {sword_saint.sword_aura}")
        print(f"  - 적 BRV: {enemy.current_brv}/{enemy.max_brv}")

    # ===== 테스트 2: 검기 베기 x3 (스택 축적) =====
    print("\n" + "-" * 60)
    print("테스트 2: 검기 베기 x3 (스택 축적)")
    print("-" * 60)

    for i in range(3):
        result = skill_manager.execute_skill(
            skill_id="sword_saint_kenkizan",
            user=sword_saint,
            target=enemy
        )
        print(f"\n  {i+1}회: 검기 스택 {sword_saint.sword_aura}")

    # ===== 테스트 3: 일섬 (HP 공격) =====
    print("\n" + "-" * 60)
    print("테스트 3: 일섬 (HP 공격, 스택 소비)")
    print("-" * 60)

    skill = skill_manager.get_skill("sword_saint_ilseom")
    print(f"\n스킬: {skill.name}")
    print(f"설명: {skill.get_description(sword_saint)}")
    print(f"현재 검기 스택: {sword_saint.sword_aura}")

    result = skill_manager.execute_skill(
        skill_id="sword_saint_ilseom",
        user=sword_saint,
        target=enemy
    )

    print(f"\n결과: {result.message}")
    if result.success:
        print(f"  - HP 데미지: {result.total_damage}")
        print(f"  - 검기 스택: {sword_saint.sword_aura}")
        print(f"  - 적 HP: {enemy.current_hp}/{enemy.max_hp}")

    # ===== 테스트 4: 검기 파동 (광역 공격) =====
    print("\n" + "-" * 60)
    print("테스트 4: 검기 파동 (관통 공격)")
    print("-" * 60)

    skill = skill_manager.get_skill("sword_saint_kenki_hadou")
    print(f"\n스킬: {skill.name}")
    print(f"설명: {skill.get_description(sword_saint)}")

    can_use, reason = skill.can_use(sword_saint)
    if can_use:
        result = skill_manager.execute_skill(
            skill_id="sword_saint_kenki_hadou",
            user=sword_saint,
            target=[enemy]  # 광역이지만 테스트에서는 1명
        )

        print(f"\n결과: {result.message}")
        if result.success:
            print(f"  - BRV 데미지: {result.total_damage}")
            print(f"  - 검기 스택: {sword_saint.sword_aura}")
    else:
        print(f"❌ 사용 불가: {reason}")

    # ===== 테스트 5: 무한검 (궁극기) =====
    print("\n" + "-" * 60)
    print("테스트 5: 무한검 (궁극기)")
    print("-" * 60)

    # 스택 최대로 설정
    sword_saint.sword_aura = 5

    skill = skill_manager.get_skill("sword_saint_ultimate")
    print(f"\n스킬: {skill.name}")
    print(f"설명: {skill.get_description(sword_saint)}")
    print(f"현재 검기 스택: {sword_saint.sword_aura}")

    can_use, reason = skill.can_use(sword_saint)
    if can_use:
        result = skill_manager.execute_skill(
            skill_id="sword_saint_ultimate",
            user=sword_saint,
            target=enemy
        )

        print(f"\n결과: {result.message}")
        if result.success:
            print(f"  - 총 데미지: {result.total_damage}")
            print(f"  - 검기 스택: {sword_saint.sword_aura}")
            print(f"  - 적 HP: {enemy.current_hp}/{enemy.max_hp}")
    else:
        print(f"❌ 사용 불가: {reason}")

    # ===== 최종 상태 =====
    print("\n" + "=" * 60)
    print("최종 상태")
    print("=" * 60)

    print(f"\n🗡️ {sword_saint.name}")
    print(f"   HP: {sword_saint.current_hp}/{sword_saint.max_hp}")
    print(f"   MP: {sword_saint.current_mp}/{sword_saint.max_mp}")
    print(f"   검기 스택: {sword_saint.sword_aura}/{sword_saint.max_sword_aura}")

    print(f"\n👹 {enemy.name}")
    print(f"   HP: {enemy.current_hp}/{enemy.max_hp}")
    print(f"   생존: {'살아있음' if enemy.is_alive else '사망'}")

    print("\n✅ 검성 스킬 테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    test_sword_saint_skills()
