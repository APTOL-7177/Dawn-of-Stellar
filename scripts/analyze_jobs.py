"""34개 직업 분석 스크립트"""
import yaml
import os

char_dir = 'data/characters'

jobs = []
for f in sorted(os.listdir(char_dir)):
    if not f.endswith('.yaml'):
        continue
    job_id = f.replace('.yaml', '')
    path = os.path.join(char_dir, f)
    with open(path, 'r', encoding='utf-8') as file:
        data = yaml.safe_load(file)
    
    gimmick = data.get('gimmick', {})
    gimmick_type = gimmick.get('type', 'none') if gimmick else 'none'
    gimmick_name = gimmick.get('name', '-') if gimmick else '-'
    
    traits = data.get('traits', [])
    skills = data.get('skills', [])
    
    jobs.append({
        'id': job_id,
        'name': data.get('class_name', job_id),
        'archetype': data.get('archetype', '-'),
        'gimmick_type': gimmick_type,
        'gimmick_name': gimmick_name,
        'trait_count': len(traits),
        'skill_count': len(skills),
        'desc': data.get('description', '')
    })

# 기본 정보 출력
print("=" * 80)
print("34개 직업 목록")
print("=" * 80)
print(f"{'#':<3} {'영문ID':<15} {'한글명':<10} {'아키타입':<18} {'기믹':<15} {'특성':<4} {'스킬':<4}")
print("-" * 80)
for i, j in enumerate(jobs, 1):
    print(f"{i:<3} {j['id']:<15} {j['name']:<10} {j['archetype']:<18} {j['gimmick_name']:<15} {j['trait_count']:<4} {j['skill_count']:<4}")

print("\n" + "=" * 80)
print("직업별 분석 및 개선점")
print("=" * 80)

# 직업별 상세 분석
analysis = {
    'alchemist': {'rating': '🟢', 'issues': '없음 - 포션 시스템 잘 구현됨'},
    'archer': {'rating': '🟢', 'issues': '없음 - 마킹 시스템으로 다양한 효과'},
    'archmage': {'rating': '🟢', 'issues': '없음 - 원소 조합 시스템 잘 구현됨'},
    'assassin': {'rating': '🟡', 'issues': '은신 시스템이 단순함. 콤보 킬 보너스 추가 고려'},
    'bard': {'rating': '🟡', 'issues': '멜로디 시스템은 있으나 스킬 효과가 단순함. 음표 콤보 강화 필요'},
    'battle_mage': {'rating': '🟢', 'issues': '없음 - 룬 시스템 잘 구현됨'},
    'berserker': {'rating': '🟢', 'issues': '없음 - 광기 임계치 시스템 잘 구현됨'},
    'breaker': {'rating': '🟡', 'issues': 'BRV 파괴 특화이나 스킬 차별화 부족'},
    'cleric': {'rating': '🟢', 'issues': '없음 - 신성력 시스템 잘 구현됨'},
    'dark_knight': {'rating': '🟢', 'issues': '없음 - 충전 시스템 완벽 리워크됨'},
    'dimensionist': {'rating': '🟢', 'issues': '없음 - 차원 굴절 시스템 독창적'},
    'dragon_knight': {'rating': '🟢', 'issues': '없음 - 용의 표식 시스템 잘 구현됨'},
    'druid': {'rating': '🟡', 'issues': '변신 시스템이 있으나 폼별 스킬 차별화 부족'},
    'elementalist': {'rating': '🟡', 'issues': '정령 소환이 있으나 정령 조합 효과 부족'},
    'engineer': {'rating': '🟢', 'issues': '없음 - 열 관리 시스템 잘 구현됨'},
    'gladiator': {'rating': '🟡', 'issues': '군중 환호 시스템은 있으나 스킬과 연계 약함'},
    'hacker': {'rating': '🟢', 'issues': '없음 - 멀티스레드 시스템 잘 구현됨'},
    'knight': {'rating': '🟡', 'issues': '의무 스택 시스템이 단순함. 기사도 컨셉 강화 필요'},
    'magician': {'rating': '🟢', 'issues': '없음 - 트릭 덱 시스템 완벽 리워크됨'},
    'monk': {'rating': '🟢', 'issues': '없음 - 음양 흐름 시스템 잘 구현됨'},
    'necromancer': {'rating': '🟢', 'issues': '없음 - 언데드 군단 시스템 잘 구현됨'},
    'paladin': {'rating': '🟢', 'issues': '없음 - 성스러운 힘 시스템 잘 구현됨'},
    'philosopher': {'rating': '🔴', 'issues': '딜레마 선택 시스템이 너무 추상적. 전투 효과와 연계 부족'},
    'pirate': {'rating': '🔴', 'issues': '약탈 시스템이 단순함. 보물/도박 컨셉 강화 필요'},
    'priest': {'rating': '🟡', 'issues': '신성력 시스템은 있으나 클레릭과 차별화 부족'},
    'rogue': {'rating': '🟡', 'issues': '절도 시스템이 단순함. 트릭/함정 추가 고려'},
    'samurai': {'rating': '🟢', 'issues': '없음 - 거합 시스템 잘 구현됨'},
    'shaman': {'rating': '🔴', 'issues': '저주 시스템이 단순함. 정령 교감/예언 추가 필요'},
    'sniper': {'rating': '🟢', 'issues': '없음 - 탄창 시스템 잘 구현됨'},
    'spellblade': {'rating': '🟡', 'issues': '마력 부여 시스템이 단순함. 원소 콤보 강화 필요'},
    'sword_saint': {'rating': '🟢', 'issues': '없음 - 검기 시스템 잘 구현됨'},
    'time_mage': {'rating': '🟢', 'issues': '없음 - 타임라인 시스템 잘 구현됨'},
    'vampire': {'rating': '🟢', 'issues': '없음 - 갈증 게이지 시스템 잘 구현됨'},
    'warrior': {'rating': '🟢', 'issues': '없음 - 스탠스 시스템 잘 구현됨'},
}

# 등급별 분류
red = []
yellow = []
green = []

for j in jobs:
    a = analysis.get(j['id'], {'rating': '?', 'issues': '분석 필요'})
    j['rating'] = a['rating']
    j['issues'] = a['issues']
    
    if a['rating'] == '🔴':
        red.append(j)
    elif a['rating'] == '🟡':
        yellow.append(j)
    else:
        green.append(j)

print("\n🔴 리워크 필요 (3개)")
print("-" * 60)
for j in red:
    print(f"  {j['name']} ({j['id']})")
    print(f"    기믹: {j['gimmick_name']}")
    print(f"    문제: {j['issues']}")
    print()

print("\n🟡 개선 필요 (10개)")
print("-" * 60)
for j in yellow:
    print(f"  {j['name']} ({j['id']})")
    print(f"    기믹: {j['gimmick_name']}")
    print(f"    문제: {j['issues']}")
    print()

print("\n🟢 양호 (21개)")
print("-" * 60)
for j in green:
    print(f"  {j['name']} ({j['id']}) - {j['gimmick_name']}")
