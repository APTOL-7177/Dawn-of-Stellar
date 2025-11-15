"""궁수 스킬 테스트"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.config import initialize_config
from src.character.character import Character
from src.character.skills.skill_manager import get_skill_manager
from src.character.skills.job_skills.archer_skills import register_archer_skills
from src.combat.brave_system import get_brave_system

def test_archer():
    print("="*60)
    print("🏹 궁수 스킬 시스템 테스트")
    print("="*60)
    
    initialize_config()
    skill_manager = get_skill_manager()
    brave_system = get_brave_system()
    
    # 궁수 스킬 등록
    skill_ids = register_archer_skills(skill_manager)
    print(f"\n✅ 궁수 스킬 {len(skill_ids)}개 등록 완료")
    for skill_id in skill_ids:
        skill = skill_manager.get_skill(skill_id)
        print(f"   - {skill.name}")
    
    # 캐릭터 생성
    archer = Character("궁수", "archer", level=10)
    archer.skill_ids = skill_ids
    archer.aim_points = 0
    archer.max_aim_points = 5
    archer.support_fire_active = False
    archer.current_mp = 300
    
    enemy = Character("트롤", "warrior", level=5)
    enemy.is_enemy = True
    
    brave_system.initialize_brv(archer)
    brave_system.initialize_brv(enemy)
    
    print(f"\n🏹 {archer.name}")
    print(f"   HP: {archer.current_hp}/{archer.max_hp}")
    print(f"   MP: {archer.current_mp}")
    print(f"   BRV: {archer.current_brv}/{archer.max_brv}")
    print(f"   조준 포인트: {archer.aim_points}/{archer.max_aim_points}")
    
    print(f"\n👹 {enemy.name}")
    print(f"   HP: {enemy.current_hp}/{enemy.max_hp}")
    print(f"   BRV: {enemy.current_brv}/{enemy.max_brv}")
    
    # 테스트 1: 삼연사
    print("\n" + "-"*60)
    print("테스트 1: 삼연사 (3연속 사격 + 조준 포인트)")
    print("-"*60)
    
    result = skill_manager.execute_skill("archer_triple_shot", archer, enemy)
    print(f"결과: {result.message}")
    print(f"  조준 포인트: {archer.aim_points}")
    print(f"  사용자 BRV: {archer.current_brv}")
    
    # 테스트 2: 조준 포인트 축적
    print("\n" + "-"*60)
    print("테스트 2: 삼연사 x3 (조준 포인트 축적)")
    print("-"*60)
    
    for i in range(3):
        result = skill_manager.execute_skill("archer_triple_shot", archer, enemy)
        print(f"  {i+1}회: 조준 포인트 {archer.aim_points}, BRV {archer.current_brv}")
    
    # 테스트 3: 정밀 사격
    print("\n" + "-"*60)
    print("테스트 3: 정밀 사격 (조준 포인트 소비 HP 공격)")
    print("-"*60)
    
    print(f"사용 전: 조준 포인트 {archer.aim_points}, BRV {archer.current_brv}")
    
    result = skill_manager.execute_skill("archer_precision_shot", archer, enemy)
    print(f"\n결과: {result.message}")
    print(f"  HP 데미지: {result.total_damage}")
    print(f"  조준 포인트: {archer.aim_points}")
    print(f"  트롤 HP: {enemy.current_hp}/{enemy.max_hp}")
    
    # 테스트 4: 집중
    print("\n" + "-"*60)
    print("테스트 4: 집중 (조준 포인트 +3)")
    print("-"*60)
    
    old_points = archer.aim_points
    result = skill_manager.execute_skill("archer_focus", archer, archer)
    print(f"결과: 조준 포인트 {old_points} → {archer.aim_points}")
    
    # 테스트 5: 헤드샷
    print("\n" + "-"*60)
    print("테스트 5: 헤드샷 (조준 3포인트 소비, 크리티컬)")
    print("-"*60)
    
    # BRV 축적
    for _ in range(3):
        skill_manager.execute_skill("archer_triple_shot", archer, enemy)
    
    print(f"사용 전: 조준 포인트 {archer.aim_points}, BRV {archer.current_brv}")
    
    result = skill_manager.execute_skill("archer_headshot", archer, enemy)
    print(f"\n결과: {result.message}")
    print(f"  HP 데미지: {result.total_damage}")
    print(f"  조준 포인트: {archer.aim_points}")
    print(f"  트롤 HP: {enemy.current_hp}/{enemy.max_hp}")
    
    # 테스트 6: 지원 사격
    print("\n" + "-"*60)
    print("테스트 6: 지원 사격 (자동 사격 활성화)")
    print("-"*60)
    
    result = skill_manager.execute_skill("archer_support_fire", archer, archer)
    print(f"결과: {result.message}")
    print(f"  지원사격 활성화: {archer.support_fire_active}")
    
    # 테스트 7: 천공 사격 (궁극기)
    print("\n" + "-"*60)
    print("테스트 7: 천공 사격 (궁극기)")
    print("-"*60)
    
    # 조준 포인트 5로
    archer.aim_points = 5
    
    # BRV 축적
    for _ in range(5):
        skill_manager.execute_skill("archer_triple_shot", archer, enemy)
    
    print(f"사용 전: 조준 포인트 {archer.aim_points}, BRV {archer.current_brv}")
    
    result = skill_manager.execute_skill("archer_ultimate", archer, enemy)
    print(f"\n결과: {result.message}")
    print(f"  총 데미지: {result.total_damage}")
    print(f"  조준 포인트: {archer.aim_points}")
    print(f"  트롤 HP: {enemy.current_hp}/{enemy.max_hp}, 생존: {enemy.is_alive}")
    
    # 최종 상태
    print("\n" + "="*60)
    print("최종 상태")
    print("="*60)
    print(f"🏹 궁수")
    print(f"   HP: {archer.current_hp}/{archer.max_hp}")
    print(f"   MP: {archer.current_mp}")
    print(f"   조준 포인트: {archer.aim_points}")
    print(f"   지원사격: {archer.support_fire_active}")
    
    print(f"\n👹 트롤")
    print(f"   HP: {enemy.current_hp}/{enemy.max_hp}")
    print(f"   생존: {'❌ 사망' if not enemy.is_alive else '✅ 생존'}")
    
    print("\n" + "="*60)
    print("✅ 궁수 스킬 테스트 완료!")
    print("="*60)

if __name__ == "__main__":
    test_archer()
