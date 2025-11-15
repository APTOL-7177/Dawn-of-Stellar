"""몽크 스킬 테스트"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.config import initialize_config
from src.character.character import Character
from src.character.skills.skill_manager import get_skill_manager
from src.character.skills.job_skills.monk_skills import register_monk_skills
from src.combat.brave_system import get_brave_system

def test_monk():
    print("="*60)
    print("👊 몽크 스킬 시스템 테스트")
    print("="*60)
    
    initialize_config()
    skill_manager = get_skill_manager()
    brave_system = get_brave_system()
    
    # 몽크 스킬 등록
    skill_ids = register_monk_skills(skill_manager)
    print(f"\n✅ 몽크 스킬 {len(skill_ids)}개 등록 완료")
    for skill_id in skill_ids:
        skill = skill_manager.get_skill(skill_id)
        print(f"   - {skill.name}")
    
    # 캐릭터 생성
    monk = Character("몽크", "monk", level=10)
    monk.skill_ids = skill_ids
    monk.combo_count = 0
    monk.chakra_points = 0
    monk.current_mp = 500
    monk.active_buffs = {}
    
    enemy = Character("트롤", "warrior", level=5)
    enemy.is_enemy = True
    
    brave_system.initialize_brv(monk)
    brave_system.initialize_brv(enemy)
    
    print(f"\n👊 {monk.name}")
    print(f"   HP: {monk.current_hp}/{monk.max_hp}")
    print(f"   MP: {monk.current_mp}")
    print(f"   BRV: {monk.current_brv}/{monk.max_brv}")
    print(f"   콤보: {monk.combo_count}/10")
    print(f"   차크라: {monk.chakra_points}/5")
    
    print(f"\n👹 {enemy.name}")
    print(f"   HP: {enemy.current_hp}/{enemy.max_hp}")
    print(f"   BRV: {enemy.current_brv}/{enemy.max_brv}")
    
    # 테스트 1: 연타
    print("\n" + "-"*60)
    print("테스트 1: 연타 (BRV + 콤보 획득)")
    print("-"*60)
    
    result = skill_manager.execute_skill("monk_rapid_punch", monk, enemy)
    print(f"결과: {result.message}")
    print(f"  콤보: {monk.combo_count}")
    print(f"  BRV: {monk.current_brv}")
    
    # 테스트 2: 콤보 축적
    print("\n" + "-"*60)
    print("테스트 2: 연타 x7 (콤보 축적)")
    print("-"*60)
    
    for i in range(7):
        result = skill_manager.execute_skill("monk_rapid_punch", monk, enemy)
        print(f"  {i+1}회: 콤보 {monk.combo_count}, BRV {monk.current_brv}")
    
    # 테스트 3: 장타
    print("\n" + "-"*60)
    print("테스트 3: 장타 (콤보 소비 HP 공격)")
    print("-"*60)
    
    print(f"사용 전: 콤보 {monk.combo_count}, BRV {monk.current_brv}")
    
    result = skill_manager.execute_skill("monk_palm_strike", monk, enemy)
    print(f"\n결과: {result.message}")
    print(f"  HP 데미지: {result.total_damage}")
    print(f"  콤보: {monk.combo_count}")
    print(f"  트롤 HP: {enemy.current_hp}/{enemy.max_hp}")
    
    # 테스트 4: 차크라 집중
    print("\n" + "-"*60)
    print("테스트 4: 차크라 집중 (차크라 +2)")
    print("-"*60)
    
    print(f"사용 전: 차크라 {monk.chakra_points}, 콤보 {monk.combo_count}")
    
    result = skill_manager.execute_skill("monk_chakra_focus", monk, monk)
    print(f"\n결과: {result.message}")
    print(f"  차크라: {monk.chakra_points}")
    print(f"  콤보: {monk.combo_count}")
    
    # 테스트 5: 비룡각
    print("\n" + "-"*60)
    print("테스트 5: 비룡각 (콤보 비례 공격 + 콤보 2)")
    print("-"*60)
    
    print(f"사용 전: 콤보 {monk.combo_count}")
    
    result = skill_manager.execute_skill("monk_flying_kick", monk, enemy)
    print(f"결과: {result.message}")
    print(f"  데미지: {result.total_damage}")
    print(f"  콤보: {monk.combo_count}")
    
    # 테스트 6: 내공 방출
    print("\n" + "-"*60)
    print("테스트 6: 내공 방출 (차크라 소비 버프)")
    print("-"*60)
    
    print(f"사용 전: 차크라 {monk.chakra_points}")
    
    result = skill_manager.execute_skill("monk_inner_fire", monk, monk)
    print(f"\n결과: {result.message}")
    print(f"  차크라: {monk.chakra_points}")
    print(f"  버프 수: {len(monk.active_buffs)}")
    
    # 테스트 7: 명상
    print("\n" + "-"*60)
    print("테스트 7: 명상 (HP + 차크라 회복)")
    print("-"*60)
    
    monk.take_damage(40)
    old_hp = monk.current_hp
    old_chakra = monk.chakra_points
    
    result = skill_manager.execute_skill("monk_meditation", monk, monk)
    print(f"결과: {result.message}")
    print(f"  HP: {old_hp} → {monk.current_hp}")
    print(f"  차크라: {old_chakra} → {monk.chakra_points}")
    
    # 테스트 8: 콤보 피니셔
    print("\n" + "-"*60)
    print("테스트 8: 콤보 피니셔 (모든 콤보 소비)")
    print("-"*60)
    
    print(f"사용 전: 콤보 {monk.combo_count}")
    
    result = skill_manager.execute_skill("monk_combo_finisher", monk, enemy)
    print(f"\n결과: {result.message}")
    print(f"  총 데미지: {result.total_damage}")
    print(f"  콤보: {monk.combo_count}")
    
    # 테스트 9: 용격
    print("\n" + "-"*60)
    print("테스트 9: 용격 (콤보 5+ 필요)")
    print("-"*60)
    
    # 콤보 재축적
    for _ in range(7):
        skill_manager.execute_skill("monk_rapid_punch", monk, enemy)
    
    print(f"사용 전: 콤보 {monk.combo_count}")
    
    result = skill_manager.execute_skill("monk_dragon_strike", monk, enemy)
    print(f"\n결과: {result.message}")
    print(f"  총 데미지: {result.total_damage}")
    print(f"  콤보: {monk.combo_count}")
    
    # 테스트 10: 궁극기 칠성권
    print("\n" + "-"*60)
    print("테스트 10: 칠성권 (궁극기)")
    print("-"*60)
    
    # 콤보와 차크라 최대치
    for _ in range(5):
        skill_manager.execute_skill("monk_rapid_punch", monk, enemy)
    monk.chakra_points = 5
    
    print(f"사용 전: 콤보 {monk.combo_count}, 차크라 {monk.chakra_points}, BRV {monk.current_brv}")
    
    result = skill_manager.execute_skill("monk_ultimate", monk, enemy)
    print(f"\n결과: {result.message}")
    print(f"  총 데미지: {result.total_damage}")
    print(f"  콤보: {monk.combo_count}")
    print(f"  차크라: {monk.chakra_points}")
    print(f"  트롤 HP: {enemy.current_hp}/{enemy.max_hp}, 생존: {enemy.is_alive}")
    
    # 최종 상태
    print("\n" + "="*60)
    print("최종 상태")
    print("="*60)
    print(f"👊 몽크")
    print(f"   HP: {monk.current_hp}/{monk.max_hp}")
    print(f"   MP: {monk.current_mp}")
    print(f"   콤보: {monk.combo_count}/10")
    print(f"   차크라: {monk.chakra_points}/5")
    print(f"   활성 버프: {len(monk.active_buffs)}")
    
    print(f"\n👹 트롤")
    print(f"   HP: {enemy.current_hp}/{enemy.max_hp}")
    print(f"   생존: {'❌ 사망' if not enemy.is_alive else '✅ 생존'}")
    
    print("\n" + "="*60)
    print("✅ 몽크 스킬 테스트 완료!")
    print("="*60)

if __name__ == "__main__":
    test_monk()
