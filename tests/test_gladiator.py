"""검투사 스킬 테스트"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.config import initialize_config
from src.character.character import Character
from src.character.skills.skill_manager import get_skill_manager
from src.character.skills.job_skills.gladiator_skills import register_gladiator_skills
from src.combat.brave_system import get_brave_system

def test_gladiator():
    print("="*60)
    print("⚔️ 검투사 스킬 시스템 테스트")
    print("="*60)
    
    initialize_config()
    skill_manager = get_skill_manager()
    brave_system = get_brave_system()
    
    # 검투사 스킬 등록
    skill_ids = register_gladiator_skills(skill_manager)
    print(f"\n✅ 검투사 스킬 {len(skill_ids)}개 등록 완료")
    for skill_id in skill_ids:
        skill = skill_manager.get_skill(skill_id)
        print(f"   - {skill.name}")
    
    # 캐릭터 생성
    gladiator = Character("검투사", "gladiator", level=10)
    gladiator.skill_ids = skill_ids
    gladiator.glory_points = 0
    gladiator.kill_count = 0
    gladiator.parry_active = 0
    gladiator.current_mp = 500
    gladiator.active_buffs = {}
    
    ally = Character("전사", "warrior", level=10)
    ally.active_buffs = {}
    
    enemy = Character("고블린", "warrior", level=5)
    enemy.is_enemy = True
    
    brave_system.initialize_brv(gladiator)
    brave_system.initialize_brv(ally)
    brave_system.initialize_brv(enemy)
    
    print(f"\n⚔️ {gladiator.name}")
    print(f"   HP: {gladiator.current_hp}/{gladiator.max_hp}")
    print(f"   MP: {gladiator.current_mp}")
    print(f"   영광: {gladiator.glory_points}/10")
    print(f"   처치: {gladiator.kill_count}")
    
    # 테스트 1-5: 영광 포인트 축적
    print("\n" + "-"*60)
    print("테스트 1: 투기장 기술 x5 (영광 축적)")
    print("-"*60)
    
    for i in range(5):
        result = skill_manager.execute_skill("gladiator_arena_strike", gladiator, enemy)
        print(f"  {i+1}회: 영광 {gladiator.glory_points}, BRV {gladiator.current_brv}")
    
    # 테스트 2: 명예의 일격
    print("\n" + "-"*60)
    print("테스트 2: 명예의 일격 (영광 소비 HP 공격)")
    print("-"*60)
    
    result = skill_manager.execute_skill("gladiator_honor_strike", gladiator, enemy)
    print(f"결과: {result.message}")
    print(f"  HP 데미지: {result.total_damage}")
    print(f"  영광: {gladiator.glory_points}")
    
    # 테스트 3: 패링
    print("\n" + "-"*60)
    print("테스트 3: 패링 (반격 준비)")
    print("-"*60)
    
    result = skill_manager.execute_skill("gladiator_parry", gladiator, gladiator)
    print(f"결과: 패링 활성 {gladiator.parry_active}")
    
    # 테스트 4: 투사의 기백
    print("\n" + "-"*60)
    print("테스트 4: 투사의 기백 (버프 + 영광)")
    print("-"*60)
    
    result = skill_manager.execute_skill("gladiator_spirit", gladiator, gladiator)
    print(f"결과: 영광 {gladiator.glory_points}, 버프 {len(gladiator.active_buffs)}")
    
    # 테스트 5: 처형 (가상 처치)
    print("\n" + "-"*60)
    print("테스트 5: 처형 (영광 소비 + 처치 카운트)")
    print("-"*60)
    
    print(f"사용 전: 처치 {gladiator.kill_count}, 영광 {gladiator.glory_points}")
    result = skill_manager.execute_skill("gladiator_execute", gladiator, enemy)
    print(f"결과: 처치 {gladiator.kill_count}, 영광 {gladiator.glory_points}")
    
    # 테스트 6: 챔피언의 함성
    print("\n" + "-"*60)
    print("테스트 6: 챔피언의 함성 (파티 버프)")
    print("-"*60)
    
    context = {'party_members': [gladiator, ally]}
    result = skill_manager.execute_skill("gladiator_roar", gladiator, gladiator, context)
    print(f"결과: 검투사 버프 {len(gladiator.active_buffs)}, 전사 버프 {len(ally.active_buffs)}")
    
    # 테스트 7: 궁극기
    print("\n" + "-"*60)
    print("테스트 7: 콜로세움의 왕 (궁극기)")
    print("-"*60)
    
    # 영광 최대
    for _ in range(5):
        skill_manager.execute_skill("gladiator_arena_strike", gladiator, enemy)
    
    # 처치 카운트 증가
    gladiator.kill_count = 3
    
    print(f"사용 전: 처치 {gladiator.kill_count}, 영광 {gladiator.glory_points}, BRV {gladiator.current_brv}")
    
    result = skill_manager.execute_skill("gladiator_ultimate", gladiator, enemy)
    print(f"\n결과: {result.message}")
    print(f"  총 데미지: {result.total_damage}")
    print(f"  영광: {gladiator.glory_points}")
    print(f"  고블린 HP: {enemy.current_hp}/{enemy.max_hp}")
    
    print("\n" + "="*60)
    print("✅ 검투사 스킬 테스트 완료!")
    print("="*60)

if __name__ == "__main__":
    test_gladiator()
