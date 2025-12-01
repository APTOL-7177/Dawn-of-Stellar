#!/usr/bin/env python3
"""궁수 지원사격 테스트"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from src.core.config import initialize_config
from src.character.character import Character
from src.combat.combat_manager import CombatManager
from src.character.skills.skill_manager import SkillManager
from src.character.skills.job_skills.archer_skills import register_archer_skills

def test_archer_support_fire():
    """궁수 지원사격 테스트"""
    print("=== 궁수 지원사격 테스트 ===")

    # 궁수와 전사 생성
    archer = Character("궁수", "archer")
    warrior = Character("전사", "warrior")
    enemy = Character("적", "warrior")

    print(f"궁수 gimmick_type: {getattr(archer, 'gimmick_type', '없음')}")
    print(f"궁수 지원 콤보: {getattr(archer, 'support_fire_combo', '없음')}")

    # 스킬 매니저 설정
    skill_manager = SkillManager()
    register_archer_skills(skill_manager)

    # 마킹 스킬 테스트
    mark_normal_skill = skill_manager.get_skill("archer_mark_normal")
    if mark_normal_skill:
        print(f"마킹 스킬 찾음: {mark_normal_skill.name}")

        # 궁수가 전사에게 마킹 시도
        result = mark_normal_skill.execute(archer, warrior, {})
        print(f"마킹 결과: {result.success}")
        if result.message:
            print(f"메시지: {result.message}")

        # 마킹 확인
        warrior_mark_slot = getattr(warrior, 'mark_slot_normal', 0)
        warrior_mark_shots = getattr(warrior, 'mark_shots_normal', 0)
        print(f"전사 마킹 슬롯: {warrior_mark_slot}")
        print(f"전사 지원 발사 횟수: {warrior_mark_shots}")
    else:
        print("마킹 스킬을 찾을 수 없음")

    # 전투 매니저 설정
    cm = CombatManager()
    cm.start_combat([warrior, archer], [enemy])

    # 전사가 공격 시도 (지원사격 트리거 테스트)
    print("\n--- 전사 공격 시도 ---")

    # 기본 공격 시도
    try:
        # 전사의 기본 공격 찾기
        warrior_basic_attack = None
        for skill in skill_manager.get_all_skills():
            if skill.skill_id.startswith("warrior") and "brv" in skill.skill_id:
                warrior_basic_attack = skill
                break

        if warrior_basic_attack:
            print(f"전사 기본 공격: {warrior_basic_attack.name}")
            result = cm.execute_skill(warrior, enemy, warrior_basic_attack, {})
            print(f"공격 결과: {result.get('success', False)}")
        else:
            print("전사 기본 공격을 찾을 수 없음")

    except Exception as e:
        print(f"공격 중 오류: {e}")
        import traceback
        traceback.print_exc()

    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    test_archer_support_fire()
