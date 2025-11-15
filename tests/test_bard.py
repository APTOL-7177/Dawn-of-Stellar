"""바드 스킬 테스트"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.config import initialize_config
from src.character.character import Character
from src.character.skills.skill_manager import get_skill_manager
from src.character.skills.job_skills.bard_skills import register_bard_skills
from src.combat.brave_system import get_brave_system

def test_bard():
    print("="*60)
    print("🎵 바드 스킬 시스템 테스트")
    print("="*60)
    
    initialize_config()
    skill_manager = get_skill_manager()
    brave_system = get_brave_system()
    
    # 바드 스킬 등록
    skill_ids = register_bard_skills(skill_manager)
    print(f"\n✅ 바드 스킬 {len(skill_ids)}개 등록 완료")
    for skill_id in skill_ids:
        skill = skill_manager.get_skill(skill_id)
        print(f"   - {skill.name}")
    
    # 캐릭터 생성
    bard = Character("바드", "bard", level=10)
    bard.skill_ids = skill_ids
    bard.melody_notes = 0
    bard.octave_completed = 0
    bard.current_mp = 500
    bard.active_buffs = {}
    
    ally = Character("전사", "warrior", level=10)
    ally.active_buffs = {}
    
    enemy = Character("고블린", "warrior", level=5)
    enemy.is_enemy = True
    
    brave_system.initialize_brv(bard)
    brave_system.initialize_brv(ally)
    brave_system.initialize_brv(enemy)
    
    print(f"\n🎵 {bard.name}")
    print(f"   HP: {bard.current_hp}/{bard.max_hp}")
    print(f"   MP: {bard.current_mp}")
    print(f"   BRV: {bard.current_brv}/{bard.max_brv}")
    print(f"   멜로디: {bard.melody_notes}/7")
    print(f"   옥타브 완성: {bard.octave_completed}")
    
    print(f"\n👹 {enemy.name}")
    print(f"   HP: {enemy.current_hp}/{enemy.max_hp}")
    print(f"   BRV: {enemy.current_brv}/{enemy.max_brv}")
    
    # 테스트 1: 음표 공격
    print("\n" + "-"*60)
    print("테스트 1: 음표 공격 (BRV + 멜로디 획득)")
    print("-"*60)
    
    result = skill_manager.execute_skill("bard_note_attack", bard, enemy)
    print(f"결과: {result.message}")
    print(f"  멜로디: {bard.melody_notes}")
    print(f"  BRV: {bard.current_brv}")
    
    # 테스트 2: 멜로디 축적
    print("\n" + "-"*60)
    print("테스트 2: 음표 공격 x5 (멜로디 축적)")
    print("-"*60)
    
    for i in range(5):
        result = skill_manager.execute_skill("bard_note_attack", bard, enemy)
        print(f"  {i+1}회: 멜로디 {bard.melody_notes}, BRV {bard.current_brv}")
    
    # 테스트 3: 화음 타격
    print("\n" + "-"*60)
    print("테스트 3: 화음 타격 (멜로디 소비 HP 공격)")
    print("-"*60)
    
    print(f"사용 전: 멜로디 {bard.melody_notes}, BRV {bard.current_brv}")
    
    result = skill_manager.execute_skill("bard_chord_strike", bard, enemy)
    print(f"\n결과: {result.message}")
    print(f"  HP 데미지: {result.total_damage}")
    print(f"  멜로디: {bard.melody_notes}")
    print(f"  고블린 HP: {enemy.current_hp}/{enemy.max_hp}")
    
    # 테스트 4: 음계 상승
    print("\n" + "-"*60)
    print("테스트 4: 음계 상승 (멜로디 +3)")
    print("-"*60)
    
    old_melody = bard.melody_notes
    result = skill_manager.execute_skill("bard_scale_up", bard, bard)
    print(f"결과: 멜로디 {old_melody} → {bard.melody_notes}")
    
    # 테스트 5: 회복의 노래
    print("\n" + "-"*60)
    print("테스트 5: 회복의 노래 (파티 힐 + 멜로디)")
    print("-"*60)
    
    bard.take_damage(50)
    old_hp = bard.current_hp
    old_melody = bard.melody_notes
    
    context = {'party_members': [bard, ally]}
    result = skill_manager.execute_skill("bard_healing_song", bard, bard, context)
    print(f"결과: {result.message}")
    print(f"  바드 HP: {old_hp} → {bard.current_hp}")
    print(f"  멜로디: {old_melody} → {bard.melody_notes}")
    
    # 테스트 6: 전율
    print("\n" + "-"*60)
    print("테스트 6: 전율 (멜로디 비례 BRV 공격)")
    print("-"*60)
    
    print(f"사용 전: 멜로디 {bard.melody_notes}")
    
    result = skill_manager.execute_skill("bard_crescendo", bard, enemy)
    print(f"결과: {result.message}")
    print(f"  데미지: {result.total_damage}")
    print(f"  멜로디: {bard.melody_notes}")
    
    # 테스트 7: 공명 (파티 버프)
    print("\n" + "-"*60)
    print("테스트 7: 공명 (파티 전체 공격력 상승)")
    print("-"*60)
    
    context = {'party_members': [bard, ally]}
    result = skill_manager.execute_skill("bard_resonance", bard, bard, context)
    print(f"결과: {result.message}")
    print(f"  바드 버프: {bard.active_buffs}")
    print(f"  전사 버프: {ally.active_buffs}")
    print(f"  멜로디: {bard.melody_notes}")
    
    # 테스트 8: 화음 완성 (7음 소비)
    print("\n" + "-"*60)
    print("테스트 8: 화음 완성 (7음 소비, 파티 전체 강화)")
    print("-"*60)
    
    print(f"사용 전: 멜로디 {bard.melody_notes}, 옥타브 {bard.octave_completed}")
    
    context = {'party_members': [bard, ally]}
    result = skill_manager.execute_skill("bard_perfect_harmony", bard, bard, context)
    print(f"\n결과: {result.message}")
    print(f"  멜로디: {bard.melody_notes}")
    print(f"  옥타브 완성: {bard.octave_completed}")
    print(f"  바드 버프 수: {len(bard.active_buffs)}")
    
    # 테스트 9: 불협화음
    print("\n" + "-"*60)
    print("테스트 9: 불협화음 (멜로디 2음 소비 공격)")
    print("-"*60)
    
    # 멜로디 재축적
    for _ in range(3):
        skill_manager.execute_skill("bard_note_attack", bard, enemy)
    
    print(f"사용 전: 멜로디 {bard.melody_notes}")
    
    result = skill_manager.execute_skill("bard_discord", bard, enemy)
    print(f"\n결과: {result.message}")
    print(f"  총 데미지: {result.total_damage}")
    print(f"  멜로디: {bard.melody_notes}")
    
    # 테스트 10: 궁극기 교향곡
    print("\n" + "-"*60)
    print("테스트 10: 교향곡 (궁극기)")
    print("-"*60)
    
    # 멜로디 최대치
    bard.melody_notes = 7
    
    # BRV 축적
    for _ in range(5):
        skill_manager.execute_skill("bard_note_attack", bard, enemy)
    
    print(f"사용 전: 멜로디 {bard.melody_notes}, 옥타브 {bard.octave_completed}, BRV {bard.current_brv}")
    
    context = {'party_members': [bard, ally]}
    result = skill_manager.execute_skill("bard_ultimate", bard, enemy, context)
    print(f"\n결과: {result.message}")
    print(f"  총 데미지: {result.total_damage}")
    print(f"  멜로디: {bard.melody_notes}")
    print(f"  고블린 HP: {enemy.current_hp}/{enemy.max_hp}, 생존: {enemy.is_alive}")
    print(f"  파티 버프 적용: {len(bard.active_buffs)} buffs")
    
    # 최종 상태
    print("\n" + "="*60)
    print("최종 상태")
    print("="*60)
    print(f"🎵 바드")
    print(f"   HP: {bard.current_hp}/{bard.max_hp}")
    print(f"   MP: {bard.current_mp}")
    print(f"   멜로디: {bard.melody_notes}/7")
    print(f"   옥타브 완성: {bard.octave_completed}")
    print(f"   활성 버프: {len(bard.active_buffs)}")
    
    print(f"\n👹 고블린")
    print(f"   HP: {enemy.current_hp}/{enemy.max_hp}")
    print(f"   생존: {'❌ 사망' if not enemy.is_alive else '✅ 생존'}")
    
    print("\n" + "="*60)
    print("✅ 바드 스킬 테스트 완료!")
    print("="*60)

if __name__ == "__main__":
    test_bard()
