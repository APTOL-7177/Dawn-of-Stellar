"""모든 직업의 스킬 MP 소모량 분석 및 균형 조정"""
import re
import os
from pathlib import Path

def analyze_mp_costs():
    """모든 직업 스킬의 MP 소모량 분석"""
    skills_dir = Path("src/character/skills/job_skills")
    mp_costs = {}
    
    for skill_file in skills_dir.glob("*_skills.py"):
        job_name = skill_file.stem.replace("_skills", "")
        with open(skill_file, "r", encoding="utf-8") as f:
            content = f.read()
            costs = [int(m.group(1)) for m in re.finditer(r'MPCost\((\d+)\)', content)]
            if costs:
                mp_costs[job_name] = costs
    
    return mp_costs

def print_analysis(mp_costs):
    """분석 결과 출력"""
    print("=== 직업별 MP 소모량 분석 ===\n")
    for job, costs in sorted(mp_costs.items()):
        avg = sum(costs) / len(costs) if costs else 0
        min_cost = min(costs) if costs else 0
        max_cost = max(costs) if costs else 0
        print(f"{job:20s}: {costs}")
        print(f"  평균: {avg:5.1f}, 최소: {min_cost:2d}, 최대: {max_cost:2d}\n")

if __name__ == "__main__":
    mp_costs = analyze_mp_costs()
    print_analysis(mp_costs)

