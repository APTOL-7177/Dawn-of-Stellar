"""모든 직업에 슬로건 추가"""
import os
import re

char_dir = 'data/characters'

# 34개 직업 슬로건
slogans = {
    'alchemist': '"완벽한 조합은 천재의 영역, 폭발은 일상"',
    'archer': '"한 발의 화살이 전장의 흐름을 바꾼다"',
    'archmage': '"세 가지 원소, 무한한 가능성"',
    'assassin': '"그림자 속에서 온 죽음, 소리 없이 사라진다"',
    'bard': '"한 음 한 음이 전장의 운명을 바꾼다"',
    'battle_mage': '"검에 새긴 룬이 마법을 부른다"',
    'berserker': '"고통이 클수록 나는 강해진다"',
    'breaker': '"부서진 것들이 나의 무기가 된다"',
    'cleric': '"신앙은 기적을 낳고, 기적은 승리를 부른다"',
    'dark_knight': '"한 번의 완벽한 일격, 그것이 전부다"',
    'dimensionist': '"시간과 공간, 그 경계를 넘어서"',
    'dragon_knight': '"용의 피가 내 안에서 불타오른다"',
    'druid': '"자연의 모든 모습이 나의 힘"',
    'elementalist': '"하나보다 둘, 둘보다 넷이 강하다"',
    'engineer': '"기계는 거짓말을 하지 않는다"',
    'gladiator': '"관중이 열광할수록 나는 강해진다"',
    'hacker': '"시스템을 지배하는 자가 전장을 지배한다"',
    'knight': '"맹세는 지키되, 대가를 치른다"',
    'magician': '"카드 한 장에 운명이 담겨있다"',
    'monk': '"음과 양의 조화 속에 진정한 힘이 있다"',
    'necromancer': '"죽음은 끝이 아니라 시작이다"',
    'paladin': '"신성한 빛이 어둠을 물리친다"',
    'philosopher': '"진실과 거짓, 그 선택이 세상을 바꾼다"',
    'pirate': '"인생은 도박이야, 럼주나 마셔"',
    'priest': '"구원할 것인가, 심판할 것인가"',
    'rogue': '"정정당당? 그건 바보들이나 하는 거지"',
    'samurai': '"일도양단, 한 번의 베기에 모든 것을 건다"',
    'shaman': '"조상의 목소리가 미래를 말해준다"',
    'sniper': '"한 발, 한 명. 그것으로 충분하다"',
    'spellblade': '"검과 마법, 그 경계를 넘어서"',
    'sword_saint': '"검기가 폭발하는 순간, 적은 이미 베였다"',
    'time_mage': '"시간을 다루는 자, 운명을 다룬다"',
    'vampire': '"피는 생명이자 힘이다"',
    'warrior': '"상황에 맞는 자세, 그것이 진정한 전사의 길"',
}

updated = 0
for yaml_file in os.listdir(char_dir):
    if not yaml_file.endswith('.yaml'):
        continue
    
    job_id = yaml_file.replace('.yaml', '')
    if job_id not in slogans:
        print(f"✗ {job_id}: 슬로건 없음")
        continue
    
    yaml_path = os.path.join(char_dir, yaml_file)
    with open(yaml_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 이미 슬로건이 있는지 확인
    if 'slogan:' in content:
        print(f"- {job_id}: 이미 있음")
        continue
    
    # description 다음에 slogan 추가
    slogan = slogans[job_id]
    pattern = r'(description: .+?\n)'
    replacement = f'\\1slogan: {slogan}\n'
    
    new_content = re.sub(pattern, replacement, content, count=1)
    
    if new_content != content:
        with open(yaml_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✓ {job_id}: 슬로건 추가됨")
        updated += 1
    else:
        print(f"? {job_id}: 변경 없음")

print(f"\n완료: {updated}개 파일 업데이트")
