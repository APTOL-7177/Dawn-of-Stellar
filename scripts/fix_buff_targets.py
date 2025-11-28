"""
BuffEffect 타겟 오류 자동 수정 스크립트
공격 스킬에서 자신에게 버프를 주는 경우 target="self" 추가
"""
import os
import re

# 수정이 필요한 스킬 목록 (직업, 스킬ID, 버프타입)
FIXES = [
    ("archer", "총력 지원", "ATTACK_UP"),
    ("assassin", "그림자 베기", "EVASION_UP"),
    ("assassin", "침묵의 처형", "EVASION_UP"),
    ("assassin", "그림자의 화신", "EVASION_UP"),
    ("bard", "즉흥 연주", "SPEED_UP"),
    ("battle_mage", "룬 새기기", "ATTACK_UP"),
    ("berserker", "전투의 함성", "SPEED_UP"),
    ("berserker", "광란의 힘", "ATTACK_UP"),
    ("breaker", "절대 파괴", "ATTACK_UP"),
    ("dark_knight", "불굴의 힘", "ATTACK_UP"),
    ("dimensionist", "차원 보호막", "DEFENSE_UP"),
    ("dragon_knight", "진 드래곤", "ATTACK_UP"),
    ("druid", "독수리 변신", "SPEED_UP"),
    ("druid", "늑대 변신", "ATTACK_UP"),
    ("druid", "진 변신", "ATTACK_UP"),
    ("elementalist", "화염 정령 소환", "ATTACK_UP"),
    ("elementalist", "4대 정령 융합", "ATTACK_UP"),
    ("gladiator", "검투사의 영광", "ATTACK_UP"),
    ("hacker", "시스템 과부하", "MAGIC_UP"),
    ("hacker", "멀티스레드 폭주", "MAGIC_UP"),
    ("philosopher", "철학자의 돌", "ATTACK_UP"),
    ("pirate", "해적왕의 유산", "ATTACK_UP"),
    ("rogue", "백스탭", "CRITICAL_UP"),
    ("rogue", "그림자 습격", "EVASION_UP"),
    ("samurai", "무한 베기", "SPEED_UP"),
    ("samurai", "천상천하 유아독존", "ATTACK_UP"),
    ("spellblade", "마검 오의", "ATTACK_UP"),
    ("vampire", "혈족의 군주", "ATTACK_UP"),
    ("warrior", "격노의 일격", "ATTACK_UP"),
    ("warrior", "완전체 각성", "ATTACK_UP"),
]

def fix_skill_file(job, skill_name, buff_type):
    """스킬 파일에서 버프 타겟 수정"""
    filepath = f"src/character/skills/job_skills/{job}_skills.py"
    
    if not os.path.exists(filepath):
        print(f"  [SKIP] 파일 없음: {filepath}")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 스킬 블록 찾기
    # 스킬 이름으로 검색
    skill_pattern = rf'["\']({re.escape(skill_name)})["\']'
    skill_match = re.search(skill_pattern, content)
    
    if not skill_match:
        print(f"  [SKIP] 스킬 못 찾음: {job}/{skill_name}")
        return False
    
    # 해당 스킬의 BuffEffect 찾기
    start_idx = skill_match.start()
    # skills.append까지의 범위
    end_match = re.search(r'skills\.append\(\w+\)', content[start_idx:])
    if end_match:
        end_idx = start_idx + end_match.end()
    else:
        end_idx = start_idx + 2000
    
    skill_block = content[start_idx:end_idx]
    
    # BuffEffect(BuffType.XXX_UP 패턴 찾기 (target="self"가 없는 것)
    buff_pattern = rf'(BuffEffect\(BuffType\.{buff_type},\s*[\d.]+,\s*duration=\d+)(\))'
    
    def replace_buff(m):
        # target="self" 추가
        return m.group(1) + ', target="self"' + m.group(2)
    
    # 이미 target="self"가 있는지 확인
    if f'BuffType.{buff_type}' in skill_block and 'target="self"' not in skill_block:
        new_block = re.sub(buff_pattern, replace_buff, skill_block)
        
        if new_block != skill_block:
            new_content = content[:start_idx] + new_block + content[end_idx:]
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"  [FIXED] {job}: {skill_name} - {buff_type}")
            return True
    
    print(f"  [SKIP] 이미 수정됨 또는 패턴 불일치: {job}/{skill_name}")
    return False

def main():
    print("=" * 60)
    print(" BuffEffect 타겟 오류 자동 수정")
    print("=" * 60)
    
    fixed_count = 0
    
    for job, skill_name, buff_type in FIXES:
        if fix_skill_file(job, skill_name, buff_type):
            fixed_count += 1
    
    print("=" * 60)
    print(f" 수정 완료: {fixed_count}/{len(FIXES)}개")
    print("=" * 60)

if __name__ == "__main__":
    main()
