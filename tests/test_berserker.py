"""광전사 스킬 테스트"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.config import initialize_config
from src.character.character import Character
from src.character.skills.skill_manager import get_skill_manager
from src.character.skills.job_skills.berserker_skills import register_berserker_skills
from src.combat.brave_system import get_brave_system

def test_berserker():
    print("="*60)
    print("🔥 광전사 스킬 시스템 테스트")
    print("="*60)
    
    # Config 초기화
    initialize_config()
    
    # 초기화
    skill_manager = get_skill_manager()
    brave_system = get_brave_system()
    
    # 광전사 스킬 등록
    skill_ids = register_berserker_skills(skill_manager)
    print(f"\n✅ 광전사 스킬 {len(skill_ids)}개 등록 완료")
    for skill_id in skill_ids:
        skill = skill_manager.get_skill(skill_id)
        print(f"   - {skill.name}")
    
    # 캐릭터 생성
    berserker = Character("광전사", "berserker", level=10)
    berserker.skill_ids = skill_ids
    # 기믹 초기화
    berserker.rage_stacks = 0
    berserker.max_rage_stacks = 10
    berserker.shield_amount = 0
    # 테스트용 MP 증가
    berserker.current_mp = 300
    
    enemy = Character("오크", "warrior", level=5)
    enemy.is_enemy = True
    
    # BRV 초기화
    brave_system.initialize_brv(berserker)
    brave_system.initialize_brv(enemy)
    
    print(f"\n🔥 {berserker.name}")
    print(f"   HP: {berserker.current_hp}/{berserker.max_hp}")
    print(f"   MP: {berserker.current_mp}")
    print(f"   BRV: {berserker.current_brv}/{berserker.max_brv}")
    print(f"   분노 스택: {berserker.rage_stacks}/{berserker.max_rage_stacks}")
    print(f"   보호막: {berserker.shield_amount}")
    
    print(f"\n👹 {enemy.name}")
    print(f"   HP: {enemy.current_hp}/{enemy.max_hp}")
    print(f"   BRV: {enemy.current_brv}/{enemy.max_brv}")
    
    # 테스트 1: 광란의 일격
    print("\n" + "-"*60)
    print("테스트 1: 광란의 일격 (HP 소비 BRV 공격)")
    print("-"*60)
    
    old_hp = berserker.current_hp
    result = skill_manager.execute_skill("berserker_frenzy_strike", berserker, enemy)
    print(f"결과: {result.message}")
    print(f"  HP: {old_hp} → {berserker.current_hp} (소비: {old_hp - berserker.current_hp})")
    print(f"  분노 스택: {berserker.rage_stacks}")
    print(f"  사용자 BRV: {berserker.current_brv}")
    
    # 테스트 2: 피의 갑옷 (HP → 보호막)
    print("\n" + "-"*60)
    print("테스트 2: 피의 갑옷 (HP 20% 소비, 보호막 150% 생성)")
    print("-"*60)
    
    old_hp = berserker.current_hp
    result = skill_manager.execute_skill("berserker_blood_armor", berserker, berserker)
    hp_consumed = old_hp - berserker.current_hp
    print(f"결과: {result.message}")
    print(f"  HP 소비: {hp_consumed}")
    print(f"  보호막 생성: {berserker.shield_amount}")
    print(f"  분노 스택: {berserker.rage_stacks}")
    print(f"  비율: {berserker.shield_amount / hp_consumed if hp_consumed > 0 else 0:.1f}x")
    
    # 테스트 3: 광폭화 (분노 축적)
    print("\n" + "-"*60)
    print("테스트 3: 광폭화 (분노 대량 축적)")
    print("-"*60)
    
    old_rage = berserker.rage_stacks
    result = skill_manager.execute_skill("berserker_rampage", berserker, enemy)
    print(f"결과: {result.message}")
    print(f"  분노 스택: {old_rage} → {berserker.rage_stacks}")
    
    # 테스트 4: 전쟁의 함성 (분노 소비, HP 스케일링)
    print("\n" + "-"*60)
    print("테스트 4: 전쟁의 함성 (HP 낮을수록 강력)")
    print("-"*60)
    
    # HP 낮추기
    berserker.current_hp = int(berserker.max_hp * 0.25)
    print(f"HP를 25%로 낮춤: {berserker.current_hp}/{berserker.max_hp}")
    print(f"분노 스택: {berserker.rage_stacks}")
    
    # BRV 축적
    for _ in range(5):
        skill_manager.execute_skill("berserker_frenzy_strike", berserker, enemy)
    
    result = skill_manager.execute_skill("berserker_war_cry", berserker, [enemy])
    print(f"\n결과: {result.message}")
    print(f"  분노 스택: {berserker.rage_stacks}")
    print(f"  사용자 BRV: {berserker.current_brv}")
    
    # 테스트 5: 피의 섬광 (흡혈)
    print("\n" + "-"*60)
    print("테스트 5: 피의 섬광 (HP 소비 + 흡혈 회복)")
    print("-"*60)
    
    old_hp = berserker.current_hp
    result = skill_manager.execute_skill("berserker_blood_flash", berserker, enemy)
    print(f"결과: {result.message}")
    print(f"  HP: {old_hp} → {berserker.current_hp}")
    print(f"  HP 변화: {berserker.current_hp - old_hp} (소비 후 흡혈)")
    print(f"  오크 HP: {enemy.current_hp}/{enemy.max_hp}")
    
    # 테스트 6: 피의 광란 (궁극기)
    print("\n" + "-"*60)
    print("테스트 6: 피의 광란 (궁극기, HP 99% 소비)")
    print("-"*60)
    
    berserker.current_hp = berserker.max_hp  # HP 회복
    berserker.rage_stacks = 10  # 분노 최대
    
    # BRV 축적
    for _ in range(10):
        result = skill_manager.execute_skill("berserker_frenzy_strike", berserker, enemy)
        if not result.success:
            break
    
    print(f"사용 전:")
    print(f"  HP: {berserker.current_hp}/{berserker.max_hp}")
    print(f"  분노 스택: {berserker.rage_stacks}")
    print(f"  BRV: {berserker.current_brv}")
    
    result = skill_manager.execute_skill("berserker_ultimate", berserker, enemy)
    print(f"\n결과: {result.message}")
    print(f"  HP: {berserker.current_hp}/{berserker.max_hp}")
    print(f"  총 데미지: {result.total_damage}")
    print(f"  총 회복: {result.total_heal}")
    print(f"  분노 스택: {berserker.rage_stacks}")
    print(f"  오크 HP: {enemy.current_hp}/{enemy.max_hp}, 생존: {enemy.is_alive}")
    
    # 최종 상태
    print("\n" + "="*60)
    print("최종 상태")
    print("="*60)
    print(f"🔥 광전사")
    print(f"   HP: {berserker.current_hp}/{berserker.max_hp}")
    print(f"   MP: {berserker.current_mp}")
    print(f"   분노 스택: {berserker.rage_stacks}")
    print(f"   보호막: {berserker.shield_amount}")
    
    print(f"\n👹 오크")
    print(f"   HP: {enemy.current_hp}/{enemy.max_hp}")
    print(f"   생존: {'❌ 사망' if not enemy.is_alive else '✅ 생존'}")
    
    print("\n" + "="*60)
    print("✅ 광전사 스킬 테스트 완료!")
    print("="*60)

if __name__ == "__main__":
    test_berserker()
