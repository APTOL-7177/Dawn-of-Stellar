"""차원술사 스킬 로드 테스트"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.character.character import Character
from src.character.skills.skill_initializer import initialize_all_skills
from src.core.config import initialize_config

def test_skill_loading():
    """차원술사 스킬 로드 테스트"""
    print("=" * 60)
    print("차원술사 스킬 로드 테스트")
    print("=" * 60)

    # 설정 초기화
    print("\n설정 시스템 초기화 중...")
    initialize_config()

    # 스킬 초기화
    print("스킬 시스템 초기화 중...")
    if not initialize_all_skills():
        print("[ERROR] 스킬 초기화 실패!")
        return False

    dimensionist = Character("차원술사", "dimensionist")

    print(f"\n캐릭터: {dimensionist.name}")
    print(f"스킬 개수: {len(dimensionist.skills)}")
    print(f"\n스킬 목록:")
    for i, skill in enumerate(dimensionist.skills, 1):
        mp_cost = skill.costs[0].amount if skill.costs else 0
        print(f"  {i}. {skill.name} (MP: {mp_cost})")
        print(f"     {skill.description}")

    if len(dimensionist.skills) == 10:
        print(f"\n[OK] 10개 스킬 모두 로드됨!")
        return True
    else:
        print(f"\n[FAIL] 스킬 개수 오류: {len(dimensionist.skills)}/10")
        return False

if __name__ == "__main__":
    success = test_skill_loading()
    sys.exit(0 if success else 1)
