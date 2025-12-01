"""
적 스킬에 SFX 자동 추가 스크립트
"""
import re

# 스킬 이름/ID 기반 SFX 매핑 (우선순위 순서)
sfx_mapping = [
    # 물리 공격 (특정 -> 일반 순서)
    (r'(heavy|강력|분쇄|강타)', ('combat', 'damage_high')),
    (r'(multi|연속|combo)', ('combat', 'multi_hit')),
    (r'(strike|stab|bite|claw|slash|crush|stomp|punch|kick|assault)', ('combat', 'attack_physical')),

    # 마법 공격
    (r'(ultima|궁극)', ('skill', 'ultima')),
    (r'(hellfire|지옥)', ('skill', 'fire3')),
    (r'(fire|flame|burn|화염|불꽃|fireball)', ('skill', 'fire')),
    (r'(ice|frost|빙|얼음|freeze)', ('skill', 'ice')),
    (r'(thunder|lightning|전기|번개|bolt)', ('skill', 'bolt')),
    (r'(meteor|운석|流星)', ('skill', 'fire3')),
    (r'(earth|대지|quake|지진)', ('skill', 'earth')),
    (r'(wind|바람|tornado|vortex|소용돌이)', ('skill', 'wind')),
    (r'(water|물|aqua|tsunami|해일)', ('skill', 'water')),
    (r'(dark|어둠|shadow|암흑|void|공허)', ('skill', 'dark')),
    (r'(holy|신성|light|빛|nova)', ('skill', 'holy')),
    (r'(explosion|폭발|burst)', ('skill', 'explosion')),
    (r'(magic|마법|spell|주문)', ('skill', 'magic_cast')),

    # 독/상태이상
    (r'(poison|독|venom|plague|역병|disease|질병)', ('skill', 'poison')),
    (r'(acid|산성)', ('skill', 'poison')),
    (r'(confusion|혼란)', ('skill', 'confusion')),

    # 회복
    (r'(heal|치유|regenerat|재생|recover)', ('character', 'hp_heal')),
    (r'(drain|흡수|leech|corpse|시체)', ('character', 'hp_heal')),

    # 버프
    (r'(shield|방어|barrier|장벽|protect)', ('skill', 'barrier')),
    (r'(haste|가속)', ('skill', 'haste')),
    (r'(rage|광폭|frenzy|광란|berserk)', ('character', 'status_buff')),
    (r'(buff|강화|boost|enhance)', ('character', 'status_buff')),
    (r'(cry|함성|roar|포효|intimidat|위압)', ('skill', 'roar')),

    # 디버프
    (r'(slow|감속)', ('skill', 'slow')),
    (r'(wail|비명|scream|terror|공포|fear|banshee|통곡)', ('skill', 'confusion')),
    (r'(debuff|약화|weaken|curse|저주)', ('character', 'status_debuff')),

    # 특수
    (r'(summon|소환|call)', ('skill', 'summon')),
    (r'(laser|레이저|beam)', ('skill', 'laser')),
    (r'(teleport|순간이동|blink|split|분열|transform|변신)', ('skill', 'teleport')),
    (r'(dive|급강하|charge|돌진)', ('combat', 'attack_sword')),
    (r'(breath|브레스|숨결)', ('skill', 'fire_explosion')),
    (r'(soul|영혼|spirit)', ('skill', 'dark')),
    (r'(flight|비행|fly)', ('skill', 'wind')),
    (r'(petrify|석화)', ('skill', 'earth')),
    (r'(mirror|거울|반사)', ('skill', 'reflect')),
    (r'(trap|함정)', ('skill', 'trap')),
    (r'(flee|도망|escape|회피)', ('character', 'status_buff')),
]

def get_sfx_for_skill(skill_id, skill_name, description, has_sfx):
    """스킬에 적합한 SFX 결정"""
    if has_sfx:
        return None  # 이미 SFX가 있으면 건너뛰기

    # 스킬 ID, 이름, 설명을 모두 검사
    text = f"{skill_id} {skill_name} {description}".lower()

    for pattern, sfx in sfx_mapping:
        if re.search(pattern, text, re.IGNORECASE):
            return sfx

    # 기본값: 물리 공격
    return ('combat', 'attack_physical')

def process_file(input_path, output_path):
    """파일 처리"""
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    result_lines = []
    in_skill = False
    skill_lines = []
    skill_id = ""
    skill_name = ""
    skill_desc = ""
    has_sfx = False

    for line in lines:
        # EnemySkill 시작 감지
        if 'EnemySkill(' in line:
            in_skill = True
            skill_lines = [line]
            has_sfx = False
            skill_id = ""
            skill_name = ""
            skill_desc = ""
            continue

        if in_skill:
            skill_lines.append(line)

            # 스킬 정보 추출
            if 'skill_id=' in line:
                match = re.search(r'skill_id="([^"]+)"', line)
                if match:
                    skill_id = match.group(1)
            if 'name=' in line and 'skill_name' not in line:
                match = re.search(r'name="([^"]+)"', line)
                if match:
                    skill_name = match.group(1)
            if 'description=' in line:
                match = re.search(r'description="([^"]*)"', line)
                if match:
                    skill_desc = match.group(1)
            if 'sfx=' in line:
                has_sfx = True

            # EnemySkill 종료 감지 (닫는 괄호)
            if line.strip().startswith(')'):
                # 스킬 블록 완료
                sfx = get_sfx_for_skill(skill_id, skill_name, skill_desc, has_sfx)

                if sfx and not has_sfx:
                    # SFX 추가
                    # 마지막 줄 (닫는 괄호) 제거
                    last_line = skill_lines[-1]
                    skill_lines = skill_lines[:-1]

                    # 마지막 파라미터 줄 찾기
                    if skill_lines:
                        last_param_line = skill_lines[-1]
                        # 마지막 줄에 콤마가 없으면 추가
                        if not last_param_line.rstrip().endswith(','):
                            skill_lines[-1] = last_param_line.rstrip() + ',\n'

                    # SFX 추가
                    skill_lines.append(f'                sfx=("{sfx[0]}", "{sfx[1]}")\n')
                    # 닫는 괄호 추가
                    skill_lines.append(last_line)

                result_lines.extend(skill_lines)
                in_skill = False
                skill_lines = []
                continue
        else:
            result_lines.append(line)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(result_lines)

    print(f"완료: {output_path}")

if __name__ == "__main__":
    input_file = r"X:\develop\Dawn-of-Stellar\src\combat\enemy_skills.py"
    output_file = r"X:\develop\Dawn-of-Stellar\src\combat\enemy_skills_new.py"

    process_file(input_file, output_file)
    print("SFX 추가 완료!")
