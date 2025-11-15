"""모든 직업 스킬에 stat_type 추가"""
import re
from pathlib import Path

# 직업 분류 (analyze_job_stats.py 결과 기반)
PHYSICAL_JOBS = [
    "archer", "assassin", "berserker", "breaker", "dark_knight",
    "dragon_knight", "gladiator", "knight", "monk", "paladin",
    "pirate", "rogue", "samurai", "sniper", "sword_saint", "warrior"
]

MAGICAL_JOBS = [
    "alchemist", "archmage", "bard", "battle_mage", "cleric",
    "dimensionist", "druid", "elementalist", "hacker", "mage",
    "necromancer", "philosopher", "priest", "shaman", "time_mage"
]

HYBRID_JOBS = [
    "engineer",  # 물리+기술
    "spellblade",  # 물리+마법
    "vampire"  # 물리+마법
]

skills_dir = Path("src/character/skills/job_skills")

def update_job_skills(job_file: Path, stat_type: str):
    """직업 스킬 파일에 stat_type 추가"""
    with open(job_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # DamageEffect 패턴 찾기
    # DamageEffect(DamageType.XXX, multiplier, ...) 형태
    pattern = r'DamageEffect\(DamageType\.(BRV|HP|BRV_HP),\s*([^)]+)\)'

    def replace_damage_effect(match):
        damage_type = match.group(1)
        params = match.group(2)

        # 이미 stat_type이 있는지 확인
        if 'stat_type=' in params:
            return match.group(0)  # 이미 있으면 그대로

        # stat_type 추가
        return f'DamageEffect(DamageType.{damage_type}, {params}, stat_type="{stat_type}")'

    updated_content = re.sub(pattern, replace_damage_effect, content)

    # 파일 쓰기
    if updated_content != content:
        with open(job_file, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        return True
    return False

# 물리 직업 처리 (stat_type="physical"은 기본값이므로 추가 안 함)
print("=" * 80)
print("물리 직업 (stat_type='physical' 기본값)")
print("=" * 80)
for job in PHYSICAL_JOBS:
    job_file = skills_dir / f"{job}_skills.py"
    if job_file.exists():
        print(f"[OK] {job:20} - 기본값 사용 (수정 불필요)")

# 마법 직업 처리 (stat_type="magical" 추가)
print("\n" + "=" * 80)
print("마법 직업 (stat_type='magical' 추가)")
print("=" * 80)
updated_count = 0
for job in MAGICAL_JOBS:
    job_file = skills_dir / f"{job}_skills.py"
    if job_file.exists():
        if job == "bard":
            print(f"[SKIP] {job:20} - 이미 수정됨 (건너뜀)")
            continue

        updated = update_job_skills(job_file, "magical")
        if updated:
            print(f"[UPDATE] {job:20} - stat_type='magical' 추가됨")
            updated_count += 1
        else:
            print(f"[OK] {job:20} - 수정 불필요 (이미 있음)")
    else:
        print(f"[ERROR] {job:20} - 파일 없음!")

# 하이브리드 직업은 수동 처리 필요
print("\n" + "=" * 80)
print("하이브리드 직업 (수동 검토 필요)")
print("=" * 80)
for job in HYBRID_JOBS:
    print(f"[WARN] {job:20} - 스킬마다 다르게 설정 필요")

print("\n" + "=" * 80)
print(f"총 {updated_count}개 파일 업데이트됨")
print("=" * 80)
