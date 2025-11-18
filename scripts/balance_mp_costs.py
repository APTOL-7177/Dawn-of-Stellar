"""모든 직업의 스킬 MP 소모량을 4~25 범위로 균형 조정"""
import re
from pathlib import Path

# 목표: 평균 12~16, 개별 스킬 4~25 (궁극기 제외, 궁극기는 25~30)
TARGET_AVG_MIN = 12
TARGET_AVG_MAX = 16
MIN_MP = 4
MAX_MP = 25
ULTIMATE_MIN = 25
ULTIMATE_MAX = 30

# 직업별 조정 계수 (현재 평균을 목표 평균으로 맞추기 위한 배율)
JOB_ADJUSTMENTS = {
    # 평균이 너무 높은 직업들 (감소 필요)
    "engineer": 0.65,      # 22.4 -> 14.6
    "necromancer": 0.65,  # 22.1 -> 14.4
    "berserker": 0.75,    # 18.5 -> 13.9
    "gladiator": 0.75,    # 18.8 -> 14.1
    "monk": 0.75,         # 19.6 -> 14.7
    "vampire": 0.75,      # 19.0 -> 14.3
    "dimensionist": 0.70, # 20.0 -> 14.0
    "assassin": 0.85,     # 15.9 -> 13.5
    "elementalist": 0.85, # 15.8 -> 13.4
    "shaman": 0.85,       # 15.1 -> 12.8
    "time_mage": 0.75,    # 17.7 -> 13.3
    "hacker": 0.75,       # 17.7 -> 13.3
    
    # 평균이 너무 낮은 직업들 (증가 필요)
    "warrior": 1.25,      # 11.2 -> 14.0
    "rogue": 1.25,        # 11.9 -> 14.9
    "bard": 1.20,         # 11.8 -> 14.2
    "sword_saint": 1.15,  # 12.6 -> 14.5
    "dark_knight": 1.15,  # 12.6 -> 14.5
    "dragon_knight": 1.15, # 12.1 -> 13.9
    "paladin": 1.15,      # 12.2 -> 14.0
    "knight": 1.15,       # 12.4 -> 14.3
    "priest": 1.15,       # 12.9 -> 14.8
    "cleric": 1.15,       # 13.6 -> 15.6
    "archer": 1.10,       # 13.6 -> 15.0
    "archmage": 1.10,     # 13.8 -> 15.2
    "breaker": 1.10,      # 13.0 -> 14.3
    "druid": 1.10,        # 13.2 -> 14.5
    "pirate": 1.10,       # 13.4 -> 14.7
    "spellblade": 1.10,   # 13.4 -> 14.7
    "alchemist": 1.10,    # 12.9 -> 14.2
    "philosopher": 1.05,  # 14.2 -> 14.9
    "samurai": 1.05,      # 14.9 -> 15.6
    "sniper": 1.05,       # 14.4 -> 15.1
    "battle_mage": 1.05,  # 14.4 -> 15.1
}

def adjust_mp_cost(cost, is_ultimate, job_name):
    """MP 소모량 조정"""
    if is_ultimate:
        # 궁극기는 25~30 범위
        adjusted = int(cost * JOB_ADJUSTMENTS.get(job_name, 1.0))
        return max(ULTIMATE_MIN, min(ULTIMATE_MAX, adjusted))
    else:
        # 일반 스킬은 4~25 범위
        adjusted = int(cost * JOB_ADJUSTMENTS.get(job_name, 1.0))
        return max(MIN_MP, min(MAX_MP, adjusted))

def balance_skill_file(file_path, job_name):
    """스킬 파일의 MP 소모량 조정"""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    modified = False
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # MPCost(숫자) 패턴 찾기
        match = re.search(r'MPCost\((\d+)\)', line)
        if match:
            cost = int(match.group(1))
            
            # 이전 몇 줄을 확인하여 궁극기 여부 판단
            context = "".join(lines[max(0, i-10):i+1]).lower()
            is_ultimate = "is_ultimate" in context or "ultimate" in context or "궁극기" in context
            
            new_cost = adjust_mp_cost(cost, is_ultimate, job_name)
            if new_cost != cost:
                line = line.replace(f"MPCost({cost})", f"MPCost({new_cost})")
                modified = True
        
        new_lines.append(line)
        i += 1
    
    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        return True
    return False

def main():
    """메인 함수"""
    skills_dir = Path("src/character/skills/job_skills")
    modified_files = []
    
    for skill_file in skills_dir.glob("*_skills.py"):
        job_name = skill_file.stem.replace("_skills", "")
        if balance_skill_file(skill_file, job_name):
            modified_files.append(job_name)
            print(f"[OK] {job_name} MP cost adjusted")
    
    print(f"\nTotal {len(modified_files)} jobs adjusted.")

if __name__ == "__main__":
    main()

