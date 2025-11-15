"""팔라딘 스킬 테스트"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.config import initialize_config
from src.character.character import Character
from src.character.skills.skill_manager import get_skill_manager
from src.character.skills.job_skills.paladin_skills import register_paladin_skills
from src.combat.brave_system import get_brave_system

def test_paladin():
    print("="*60)
    print("⚔️ 팔라딘 스킬 시스템 테스트")
    print("="*60)
    
    initialize_config()
    skill_manager = get_skill_manager()
    brave_system = get_brave_system()
    
    # 팔라딘 스킬 등록
    skill_ids = register_paladin_skills(skill_manager)
    print(f"\n✅ 팔라딘 스킬 {len(skill_ids)}개 등록 완료")
    for skill_id in skill_ids:
        skill = skill_manager.get_skill(skill_id)
        print(f"   - {skill.name}")
    
    # 캐릭터 생성
    paladin = Character("팔라딘", "paladin", level=10)
    paladin.skill_ids = skill_ids
    paladin.holy_power = 0
    paladin.shield_amount = 0
    paladin.current_mp = 500
    paladin.active_buffs = {}
    
    ally = Character("전사", "warrior", level=10)
    ally.active_buffs = {}
    
    enemy = Character("언데드", "undead", level=5)
    enemy.is_enemy = True
    
    brave_system.initialize_brv(paladin)
    brave_system.initialize_brv(ally)
    brave_system.initialize_brv(enemy)
    
    print(f"\n⚔️ {paladin.name}")
    print(f"   HP: {paladin.current_hp}/{paladin.max_hp}")
    print(f"   MP: {paladin.current_mp}")
    print(f"   BRV: {paladin.current_brv}/{paladin.max_brv}")
    print(f"   성력: {paladin.holy_power}/5")
    print(f"   보호막: {paladin.shield_amount}")
    
    print(f"\n👹 {enemy.name}")
    print(f"   HP: {enemy.current_hp}/{enemy.max_hp}")
    
    # 테스트 1-4: 성력 축적
    print("\n" + "-"*60)
    print("테스트 1: 성력 축적 (성스러운 일격 x5)")
    print("-"*60)
    
    for i in range(5):
        result = skill_manager.execute_skill("paladin_holy_strike", paladin, enemy)
        print(f"  {i+1}회: 성력 {paladin.holy_power}, BRV {paladin.current_brv}")
    
    # 테스트 2: 신성한 심판
    print("\n" + "-"*60)
    print("테스트 2: 신성한 심판 (성력 소비 HP 공격)")
    print("-"*60)
    
    result = skill_manager.execute_skill("paladin_judgment", paladin, enemy)
    print(f"결과: {result.message}")
    print(f"  HP 데미지: {result.total_damage}")
    print(f"  성력: {paladin.holy_power}")
    
    # 테스트 3: 성스러운 빛 (힐)
    print("\n" + "-"*60)
    print("테스트 3: 성스러운 빛 (힐 + 성력)")
    print("-"*60)
    
    paladin.take_damage(30)
    old_hp = paladin.current_hp
    result = skill_manager.execute_skill("paladin_holy_light", paladin, paladin)
    print(f"결과: HP {old_hp} → {paladin.current_hp}, 성력 {paladin.holy_power}")
    
    # 테스트 4: 신성한 보호막
    print("\n" + "-"*60)
    print("테스트 4: 신성한 보호막 (성력 2 소비)")
    print("-"*60)
    
    # 성력 재충전
    for _ in range(3):
        skill_manager.execute_skill("paladin_holy_strike", paladin, enemy)
    
    print(f"사용 전: 성력 {paladin.holy_power}, 보호막 {paladin.shield_amount}")
    result = skill_manager.execute_skill("paladin_divine_shield", paladin, paladin)
    print(f"결과: {result.message}")
    print(f"  성력: {paladin.holy_power}")
    print(f"  보호막: {paladin.shield_amount}")
    
    # 테스트 5: 축복 (파티 버프)
    print("\n" + "-"*60)
    print("테스트 5: 축복 (파티 방어 버프)")
    print("-"*60)
    
    context = {'party_members': [paladin, ally]}
    result = skill_manager.execute_skill("paladin_blessing", paladin, paladin, context)
    print(f"결과: {result.message}")
    print(f"  팔라딘 버프: {len(paladin.active_buffs)}")
    print(f"  전사 버프: {len(ally.active_buffs)}")
    
    # 테스트 6: 복수의 격노
    print("\n" + "-"*60)
    print("테스트 6: 복수의 격노 (성력 3 소비, 강력 버프)")
    print("-"*60)
    
    # 성력 재충전
    for _ in range(4):
        skill_manager.execute_skill("paladin_holy_strike", paladin, enemy)
    
    print(f"사용 전: 성력 {paladin.holy_power}")
    result = skill_manager.execute_skill("paladin_wrath", paladin, paladin)
    print(f"결과: {result.message}")
    print(f"  성력: {paladin.holy_power}")
    print(f"  버프: {len(paladin.active_buffs)}")
    print(f"  보호막: {paladin.shield_amount}")
    
    # 테스트 7: 궁극기
    print("\n" + "-"*60)
    print("테스트 7: 신성한 폭풍 (궁극기)")
    print("-"*60)
    
    # 성력 최대
    for _ in range(6):
        skill_manager.execute_skill("paladin_holy_strike", paladin, enemy)
    
    print(f"사용 전: 성력 {paladin.holy_power}, BRV {paladin.current_brv}")
    
    context = {'party_members': [paladin, ally]}
    result = skill_manager.execute_skill("paladin_ultimate", paladin, enemy, context)
    print(f"\n결과: {result.message}")
    print(f"  총 데미지: {result.total_damage}")
    print(f"  성력: {paladin.holy_power}")
    print(f"  언데드 HP: {enemy.current_hp}/{enemy.max_hp}")
    
    print("\n" + "="*60)
    print("✅ 팔라딘 스킬 테스트 완료!")
    print("="*60)

if __name__ == "__main__":
    test_paladin()
