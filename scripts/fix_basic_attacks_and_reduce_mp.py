"""모든 기본 공격의 MP 소모량 제거 및 모든 직업 MP 소모량 40% 감소"""
import re
from pathlib import Path

def fix_basic_attacks_and_reduce_mp():
    """모든 스킬 파일 수정"""
    skills_dir = Path("src/character/skills/job_skills")
    modified_files = []
    
    for skill_file in skills_dir.glob("*_skills.py"):
        with open(skill_file, "r", encoding="utf-8") as f:
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
                
                # 이전 몇 줄을 확인하여 기본 공격 여부 판단
                context = "".join(lines[max(0, i-15):i+1]).lower()
                is_basic_attack = (
                    "basic_attack" in context or
                    "기본 공격" in context or
                    "기본 brv" in context or
                    "기본 hp" in context or
                    ("costs = []" in context and "metadata" in context and "basic" in context)
                )
                
                # 궁극기 여부 판단
                is_ultimate = "is_ultimate" in context or "ultimate" in context or "궁극기" in context
                
                if is_basic_attack:
                    # 기본 공격은 MP 소모량 제거
                    line = line.replace(f"MPCost({cost})", "")
                    # costs = [] 로 변경
                    if "costs = [" in line:
                        line = re.sub(r'costs = \[.*?\]', 'costs = []', line)
                    modified = True
                elif not is_ultimate:
                    # 일반 스킬은 40% 감소 (0.6배)
                    new_cost = max(1, int(cost * 0.6))
                    line = line.replace(f"MPCost({cost})", f"MPCost({new_cost})")
                    modified = True
                else:
                    # 궁극기는 40% 감소 (0.6배)
                    new_cost = max(1, int(cost * 0.6))
                    line = line.replace(f"MPCost({cost})", f"MPCost({new_cost})")
                    modified = True
            
            new_lines.append(line)
            i += 1
        
        if modified:
            with open(skill_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            modified_files.append(skill_file.stem.replace("_skills", ""))
            print(f"[OK] {skill_file.stem} fixed")
    
    print(f"\nTotal {len(modified_files)} files modified.")
    return modified_files

if __name__ == "__main__":
    fix_basic_attacks_and_reduce_mp()

