"""검성 스킬 테스트"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.config import initialize_config
from src.character.character import Character
from src.character.skills.skill_manager import get_skill_manager
from src.character.skills.job_skills.sword_saint_skills import register_sword_saint_skills
from src.combat.brave_system import get_brave_system

def test_sword_saint():
    print("="*60)
    print("🗡️  검성 스킬 시스템 테스트")
    print("="*60)
    
    # Config 초기화
    initialize_config()
    
    # 초기화
    skill_manager = get_skill_manager()
    brave_system = get_brave_system()
    
    # 검성 스킬 등록
    skills = register_sword_saint_skills(skill_manager)
    print(f"\n✅ 검성 스킬 {len(skills)}개 등록 완료")
    skill_ids = [s.skill_id for s in skills]
    for skill in skills:
        print(f"   - {skill.name}")
    
    # 캐릭터 생성
    sword_saint = Character("검성", "sword_saint", level=10)
    sword_saint.skill_ids = skill_ids
    # 검기 기믹 초기화
    sword_saint.sword_aura = 0
    sword_saint.max_sword_aura = 5
    # 테스트용 MP 증가
    sword_saint.current_mp = 200
    
    enemy = Character("고블린", "warrior", level=5)
    enemy.is_enemy = True
    
    # BRV 초기화
    brave_system.initialize_brv(sword_saint)
    brave_system.initialize_brv(enemy)
    
    print(f"\n🗡️ {sword_saint.name}")
    print(f"   HP: {sword_saint.current_hp}/{sword_saint.max_hp}")
    print(f"   MP: {sword_saint.current_mp}")
    print(f"   BRV: {sword_saint.current_brv}/{sword_saint.max_brv}")
    print(f"   검기 스택: {sword_saint.sword_aura}/{sword_saint.max_sword_aura}")
    
    print(f"\n👹 {enemy.name}")
    print(f"   HP: {enemy.current_hp}/{enemy.max_hp}")
    print(f"   BRV: {enemy.current_brv}/{enemy.max_brv}")
    
    # 테스트 1: 검기 베기
    print("\n" + "-"*60)
    print("테스트 1: 검기 베기 (BRV 공격 + 검기 스택 획득)")
    print("-"*60)
    
    result = skill_manager.execute_skill("sword_saint_kenkizan", sword_saint, enemy)
    print(f"결과: {result.message}")
    print(f"  검기 스택: {sword_saint.sword_aura}")
    print(f"  사용자 BRV: {sword_saint.current_brv}")
    print(f"  고블린 BRV: {enemy.current_brv}")
    
    # 테스트 2: 검기 4스택 축적
    print("\n" + "-"*60)
    print("테스트 2: 검기 베기 x4 (스택 축적)")
    print("-"*60)
    
    for i in range(4):
        result = skill_manager.execute_skill("sword_saint_kenkizan", sword_saint, enemy)
        print(f"  {i+1}회: 검기 {sword_saint.sword_aura}, BRV {sword_saint.current_brv}")
    
    # 테스트 3: 일섬 (HP 공격)
    print("\n" + "-"*60)
    print("테스트 3: 일섬 (검기 소비 HP 공격)")
    print("-"*60)
    
    print(f"사용 전: 검기 스택 {sword_saint.sword_aura}, BRV {sword_saint.current_brv}")
    
    result = skill_manager.execute_skill("sword_saint_ilseom", sword_saint, enemy)
    print(f"\n결과: {result.message}")
    print(f"  HP 데미지: {result.total_damage}")
    print(f"  검기 스택: {sword_saint.sword_aura}")
    print(f"  고블린 HP: {enemy.current_hp}/{enemy.max_hp}")
    
    # 테스트 4: 검성의 의지 (스택 최대 회복)
    print("\n" + "-"*60)
    print("테스트 4: 검성의 의지 (스택 최대 회복)")
    print("-"*60)
    
    print(f"사용 전: 검기 스택 {sword_saint.sword_aura}")
    result = skill_manager.execute_skill("sword_saint_will", sword_saint, sword_saint)
    print(f"사용 후: 검기 스택 {sword_saint.sword_aura}")
    
    # 테스트 5: 초고속 베기 (BRV 축적용)
    print("\n" + "-"*60)
    print("테스트 5: 초고속 베기 (검기 2스택 획득)")
    print("-"*60)
    
    sword_saint.sword_aura = 1
    result = skill_manager.execute_skill("sword_saint_rapid_slash", sword_saint, enemy)
    print(f"결과: 검기 스택 {sword_saint.sword_aura}")
    
    # 테스트 6: 무한검 (궁극기)
    print("\n" + "-"*60)
    print("테스트 6: 무한검 (궁극기)")
    print("-"*60)
    
    # 스택 5, BRV 축적
    sword_saint.sword_aura = 5
    for _ in range(5):
        skill_manager.execute_skill("sword_saint_kenkizan", sword_saint, enemy)
    
    print(f"사용 전: 검기 {sword_saint.sword_aura}, BRV {sword_saint.current_brv}")
    
    result = skill_manager.execute_skill("sword_saint_ultimate", sword_saint, enemy)
    print(f"\n결과: {result.message}")
    print(f"  총 데미지: {result.total_damage}")
    print(f"  검기 스택: {sword_saint.sword_aura}")
    print(f"  고블린 HP: {enemy.current_hp}/{enemy.max_hp}, 생존: {enemy.is_alive}")
    
    # 최종 상태
    print("\n" + "="*60)
    print("최종 상태")
    print("="*60)
    print(f"🗡️ 검성")
    print(f"   HP: {sword_saint.current_hp}/{sword_saint.max_hp}")
    print(f"   MP: {sword_saint.current_mp}")
    print(f"   검기 스택: {sword_saint.sword_aura}")
    
    print(f"\n👹 고블린")
    print(f"   HP: {enemy.current_hp}/{enemy.max_hp}")
    print(f"   생존: {'❌ 사망' if not enemy.is_alive else '✅ 생존'}")
    
    print("\n" + "="*60)
    print("✅ 검성 스킬 테스트 완료!")
    print("="*60)

if __name__ == "__main__":
    test_sword_saint()
