"""궁극기들의 MP 소모량 증가"""
import re
from pathlib import Path

def increase_ultimate_mp():
    """모든 궁극기 스킬의 MP 소모량 증가"""
    skills_dir = Path("src/character/skills/job_skills")
    modified_files = []
    
    for skill_file in skills_dir.glob("*_skills.py"):
        with open(skill_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        modified = False
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # is_ultimate = True 라인 찾기
            if re.search(r'is_ultimate\s*=\s*True', line):
                # 이전 15줄 내에서 가장 가까운 MPCost 찾기 (역순으로)
                found_mp_cost = False
                for j in range(i - 1, max(0, i - 15) - 1, -1):
                    if j < 0:
                        break
                    mp_cost_match = re.search(r'MPCost\((\d+)\)', lines[j])
                    if mp_cost_match:
                        current_cost = int(mp_cost_match.group(1))
                        
                        # 궁극기 MP 소모량 증가
                        # 15 이하는 25로, 16-24는 30으로, 25 이상은 35로
                        if current_cost < 15:
                            new_cost = 25
                        elif current_cost < 25:
                            new_cost = 30
                        elif current_cost < 30:
                            new_cost = 35
                        else:
                            # 이미 35 이상이면 그대로 유지
                            new_cost = current_cost
                        
                        if new_cost != current_cost:
                            lines[j] = re.sub(
                                r'MPCost\(\d+\)',
                                f'MPCost({new_cost})',
                                lines[j]
                            )
                            modified = True
                            found_mp_cost = True
                            break
                
                if not found_mp_cost:
                    # MPCost를 찾지 못한 경우 로그 출력
                    print(f"[WARN] {skill_file.stem}: 궁극기 발견했지만 MPCost를 찾지 못함")
            
            i += 1
        
        if modified:
            with open(skill_file, "w", encoding="utf-8") as f:
                f.writelines(lines)
            modified_files.append(skill_file.stem.replace("_skills", ""))
            print(f"[OK] {skill_file.stem}: 궁극기 MP 소모량 증가")
    
    print(f"\n총 {len(modified_files)}개 파일 수정 완료.")
    return modified_files

if __name__ == "__main__":
    increase_ultimate_mp()

