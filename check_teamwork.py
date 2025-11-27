from src.core.config import initialize_config
from src.character.character import Character
from src.character.skills.skill_initializer import initialize_all_skills
from src.character.skills.skill_manager import get_skill_manager

initialize_config('config.yaml')
initialize_all_skills()

skill_manager = get_skill_manager()
# 모든 직업 확인
all_jobs = [
    'warrior', 'archer', 'time_mage', 'alchemist', 'paladin', 'monk', 'bard', 'cleric',
    'priest', 'necromancer', 'dragon_knight', 'elementalist', 'assassin', 'shaman',
    'pirate', 'samurai', 'druid', 'philosopher', 'gladiator', 'knight', 'spellblade',
    'dimensionist', 'berserker', 'battle_mage', 'sword_saint', 'breaker', 'hacker',
    'sniper', 'vampire', 'dark_knight', 'archmage', 'engineer', 'rogue'
]

print('🎯 최종 확인: 33개 직업 팀워크 스킬 현황')
print('=' * 60)

completed_jobs = []
incomplete_jobs = []

for job in all_jobs:
    try:
        character = Character('테스트', job)
        teamwork_skills = []
        
        for skill_id in character.skill_ids:
            skill = skill_manager.get_skill(skill_id)
            if skill and getattr(skill, 'is_teamwork_skill', False):
                teamwork_skills.append(skill)
        
        if teamwork_skills:
            completed_jobs.append(job)
            teamwork_name = teamwork_skills[0].name
            print(f'✅ {job}: "{teamwork_name}"')
        else:
            incomplete_jobs.append(job)
            print(f'❌ {job}: 팀워크 스킬 없음')
            
    except Exception as e:
        incomplete_jobs.append(job)
        print(f'⚠️ {job}: 오류 - {e}')

print(f'\n📊 최종 결과:')
print(f'   완료된 직업: {len(completed_jobs)}/33개 ({len(completed_jobs)/33*100:.1f}%)')
print(f'   미완료 직업: {len(incomplete_jobs)}개')

if incomplete_jobs:
    print(f'\n🔧 미완료 직업: {incomplete_jobs}')
else:
    print(f'\n🎉 모든 직업에 팀워크 스킬 추가 완료!')
