"""네크로맨서 스킬 테스트"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.config import initialize_config
from src.character.character import Character
from src.character.skills.skill_manager import get_skill_manager
from src.character.skills.job_skills.necromancer_skills import register_necromancer_skills
from src.combat.brave_system import get_brave_system

def test_necromancer():
    print("="*60)
    print("💀 네크로맨서 스킬 시스템 테스트")
    print("="*60)
    
    initialize_config()
    skill_manager = get_skill_manager()
    brave_system = get_brave_system()
    
    # 네크로맨서 스킬 등록
    skill_ids = register_necromancer_skills(skill_manager)
    print(f"\n✅ 네크로맨서 스킬 {len(skill_ids)}개 등록 완료")
    for skill_id in skill_ids:
        skill = skill_manager.get_skill(skill_id)
        print(f"   - {skill.name}")
    
    # 캐릭터 생성
    necro = Character("네크로맨서", "necromancer", level=10)
    necro.skill_ids = skill_ids
    necro.corpse_count = 0
    necro.minion_count = 0
    necro.current_mp = 500
    necro.active_buffs = {}
    
    enemy = Character("오크", "warrior", level=5)
    enemy.is_enemy = True
    
    brave_system.initialize_brv(necro)
    brave_system.initialize_brv(enemy)
    
    print(f"\n💀 {necro.name}")
    print(f"   HP: {necro.current_hp}/{necro.max_hp}")
    print(f"   MP: {necro.current_mp}")
    print(f"   BRV: {necro.current_brv}/{necro.max_brv}")
    print(f"   시체: {necro.corpse_count}/10")
    print(f"   소환수: {necro.minion_count}/5")
    
    print(f"\n👹 {enemy.name}")
    print(f"   HP: {enemy.current_hp}/{enemy.max_hp}")
    print(f"   BRV: {enemy.current_brv}/{enemy.max_brv}")
    
    # 테스트 1: 시체의 손길
    print("\n" + "-"*60)
    print("테스트 1: 시체의 손길 (BRV + 시체 획득)")
    print("-"*60)
    
    result = skill_manager.execute_skill("necro_corpse_touch", necro, enemy)
    print(f"결과: {result.message}")
    print(f"  시체: {necro.corpse_count}")
    print(f"  BRV: {necro.current_brv}")
    
    # 테스트 2: 시체 축적
    print("\n" + "-"*60)
    print("테스트 2: 시체의 손길 x5 (시체 축적)")
    print("-"*60)
    
    for i in range(5):
        result = skill_manager.execute_skill("necro_corpse_touch", necro, enemy)
        print(f"  {i+1}회: 시체 {necro.corpse_count}, BRV {necro.current_brv}")
    
    # 테스트 3: 영혼 흡수
    print("\n" + "-"*60)
    print("테스트 3: 영혼 흡수 (시체 소비 HP 공격)")
    print("-"*60)
    
    print(f"사용 전: 시체 {necro.corpse_count}, BRV {necro.current_brv}")
    
    result = skill_manager.execute_skill("necro_soul_drain", necro, enemy)
    print(f"\n결과: {result.message}")
    print(f"  HP 데미지: {result.total_damage}")
    print(f"  시체: {necro.corpse_count}")
    print(f"  오크 HP: {enemy.current_hp}/{enemy.max_hp}")
    
    # 테스트 4: 죽음의 화살
    print("\n" + "-"*60)
    print("테스트 4: 죽음의 화살 (시체 비례 공격)")
    print("-"*60)
    
    print(f"사용 전: 시체 {necro.corpse_count}")
    
    result = skill_manager.execute_skill("necro_death_bolt", necro, enemy)
    print(f"결과: {result.message}")
    print(f"  데미지: {result.total_damage}")
    print(f"  시체: {necro.corpse_count}")
    
    # 테스트 5: 스켈레톤 소환
    print("\n" + "-"*60)
    print("테스트 5: 스켈레톤 소환 (시체 3개 → 소환수)")
    print("-"*60)
    
    print(f"사용 전: 시체 {necro.corpse_count}, 소환수 {necro.minion_count}")
    
    result = skill_manager.execute_skill("necro_summon_skeleton", necro, necro)
    print(f"\n결과: {result.message}")
    print(f"  시체: {necro.corpse_count}")
    print(f"  소환수: {necro.minion_count}")
    print(f"  버프: {necro.active_buffs}")
    
    # 테스트 6: 생명 흡수
    print("\n" + "-"*60)
    print("테스트 6: 생명 흡수 (공격 + 힐 + 시체)")
    print("-"*60)
    
    necro.take_damage(30)
    old_hp = necro.current_hp
    old_corpse = necro.corpse_count
    
    result = skill_manager.execute_skill("necro_life_tap", necro, enemy)
    print(f"결과: {result.message}")
    print(f"  HP: {old_hp} → {necro.current_hp}")
    print(f"  시체: {old_corpse} → {necro.corpse_count}")
    
    # 테스트 7: 암흑 의식
    print("\n" + "-"*60)
    print("테스트 7: 암흑 의식 (시체 2개 → 버프)")
    print("-"*60)
    
    print(f"사용 전: 시체 {necro.corpse_count}")
    
    result = skill_manager.execute_skill("necro_dark_ritual", necro, necro)
    print(f"\n결과: {result.message}")
    print(f"  시체: {necro.corpse_count}")
    print(f"  버프 수: {len(necro.active_buffs)}")
    
    # 테스트 8: 시체 폭발
    print("\n" + "-"*60)
    print("테스트 8: 시체 폭발 (모든 시체 폭발)")
    print("-"*60)
    
    # 시체 재축적
    for _ in range(5):
        skill_manager.execute_skill("necro_corpse_touch", necro, enemy)
    
    print(f"사용 전: 시체 {necro.corpse_count}")
    
    result = skill_manager.execute_skill("necro_corpse_explosion", necro, enemy)
    print(f"\n결과: {result.message}")
    print(f"  총 데미지: {result.total_damage}")
    print(f"  시체: {necro.corpse_count}")
    
    # 테스트 9: 재생
    print("\n" + "-"*60)
    print("테스트 9: 재생 (시체 5개 → 힐 + 소환수)")
    print("-"*60)
    
    # 시체 축적
    for _ in range(6):
        skill_manager.execute_skill("necro_corpse_touch", necro, enemy)
    
    necro.take_damage(40)
    old_hp = necro.current_hp
    old_minions = necro.minion_count
    
    print(f"사용 전: HP {old_hp}, 시체 {necro.corpse_count}, 소환수 {old_minions}")
    
    result = skill_manager.execute_skill("necro_reanimate", necro, necro)
    print(f"\n결과: {result.message}")
    print(f"  HP: {old_hp} → {necro.current_hp}")
    print(f"  시체: {necro.corpse_count}")
    print(f"  소환수: {necro.minion_count}")
    
    # 테스트 10: 궁극기 언데드 군단
    print("\n" + "-"*60)
    print("테스트 10: 언데드 군단 (궁극기)")
    print("-"*60)
    
    # 시체 최대치
    for _ in range(10):
        skill_manager.execute_skill("necro_corpse_touch", necro, enemy)
    
    print(f"사용 전: 시체 {necro.corpse_count}, 소환수 {necro.minion_count}, BRV {necro.current_brv}")
    
    result = skill_manager.execute_skill("necro_ultimate", necro, enemy)
    print(f"\n결과: {result.message}")
    print(f"  총 데미지: {result.total_damage}")
    print(f"  시체: {necro.corpse_count}")
    print(f"  소환수: {necro.minion_count}")
    print(f"  오크 HP: {enemy.current_hp}/{enemy.max_hp}, 생존: {enemy.is_alive}")
    print(f"  버프: {len(necro.active_buffs)} buffs")
    
    # 최종 상태
    print("\n" + "="*60)
    print("최종 상태")
    print("="*60)
    print(f"💀 네크로맨서")
    print(f"   HP: {necro.current_hp}/{necro.max_hp}")
    print(f"   MP: {necro.current_mp}")
    print(f"   시체: {necro.corpse_count}/10")
    print(f"   소환수: {necro.minion_count}/5")
    print(f"   활성 버프: {len(necro.active_buffs)}")
    
    print(f"\n👹 오크")
    print(f"   HP: {enemy.current_hp}/{enemy.max_hp}")
    print(f"   생존: {'❌ 사망' if not enemy.is_alive else '✅ 생존'}")
    
    print("\n" + "="*60)
    print("✅ 네크로맨서 스킬 테스트 완료!")
    print("="*60)

if __name__ == "__main__":
    test_necromancer()
