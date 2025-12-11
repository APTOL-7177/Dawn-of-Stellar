"""
스킬 원소 추가 스크립트
모든 직업 스킬 파일에 적절한 원소 속성 추가
"""
import os
import re

JOB_SKILLS_DIR = "x:/develop/Dawn-of-Stellar/src/character/skills/job_skills"

# 직업별 원소 매핑 (스킬명 패턴 -> 원소)
# 각 직업의 마법 공격 스킬에 적절한 원소 추가
JOB_ELEMENT_MAPPING = {
    # 이미 처리된 직업
    # "elementalist": {"default": None, "patterns": {...}},  # fire/water/wind/earth
    # "dark_knight": {"default": "dark"},
    # "paladin": {"default": "holy"},
    # "necromancer": {"default": "dark"},
    
    # 마법 기반 직업
    "magician": {"default": "fire", "patterns": {
        "fire": ["fire", "blaze", "burn", "flame"],
        "ice": ["ice", "freeze", "cold", "blizzard"],
        "lightning": ["thunder", "lightning", "shock", "bolt"],
    }},
    "archmage": {"default": None, "patterns": {
        "fire": ["fire", "flame"],
        "ice": ["ice", "freeze"],
        "lightning": ["thunder"],
    }},  # 아크메이지는 복합 원소 시스템
    
    # 힐러/서포터
    "cleric": {"default": "holy"},
    "priest": {"default": "holy"},
    
    # 물리 기반 (원소 없음)
    "warrior": {"default": None},
    "knight": {"default": None},
    "gladiator": {"default": None},
    "berserker": {"default": None},
    "samurai": {"default": None},
    "sword_saint": {"default": None},
    "monk": {"default": None},
    "archer": {"default": None},
    "sniper": {"default": None},
    "rogue": {"default": None},
    "assassin": {"default": None},
    "pirate": {"default": None},
    
    # 마법/특수 직업
    "vampire": {"default": "dark"},
    "shaman": {"default": None, "patterns": {
        "fire": ["fire", "flame"],
        "lightning": ["lightning", "thunder"],
        "dark": ["curse", "hex", "shadow", "death"],
    }},
    "druid": {"default": None, "patterns": {
        "earth": ["earth", "nature", "root"],
        "wind": ["wind", "storm"],
    }},
    "time_mage": {"default": None},  # 시간 마법은 원소 없음
    "dimensionist": {"default": None},  # 차원 마법
    "illusionist": {"default": None},  # 환영
    "bard": {"default": None},  # 음악
    "philosopher": {"default": None},  # 철학자
    
    # 하이브리드/특수
    "battle_mage": {"default": None, "patterns": {
        "fire": ["fire", "rune_fire"],
        "ice": ["ice", "rune_ice"],
        "lightning": ["lightning", "rune_lightning"],
        "earth": ["earth", "rune_earth"],
    }},
    "spellblade": {"default": None, "patterns": {
        "fire": ["fire", "flame"],
        "ice": ["ice", "frost"],
        "lightning": ["thunder", "lightning"],
    }},
    "dragon_knight": {"default": "fire", "patterns": {
        "fire": ["fire", "flame", "dragon_breath"],
    }},
    
    # 기술/기계
    "alchemist": {"default": None, "patterns": {
        "fire": ["fire", "bomb", "explosion"],
        "poison": ["poison", "acid", "venom"],
    }},
    "engineer": {"default": None},
    "hacker": {"default": None},
    "breaker": {"default": None},
}

def add_element_to_file(filepath, element_config):
    """파일에 원소 속성 추가"""
    if not os.path.exists(filepath):
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 이모지 제거
    content = re.sub(r'[🔥💧💨🌍🌑✨⚡☠️🌊]', '', content)
    
    default_element = element_config.get("default")
    patterns = element_config.get("patterns", {})
    
    if default_element:
        # stat_type="magical" 뒤에 element 추가 (이미 element가 없는 경우만)
        # DamageEffect(...stat_type="magical") -> DamageEffect(...stat_type="magical", element="<element>")
        pattern = r'(DamageEffect\([^)]*stat_type="magical")(\))'
        if 'element=' not in content:
            replacement = rf'\1, element="{default_element}"\2'
            content = re.sub(pattern, replacement, content)
    
    # 패턴별 원소 처리
    for element, keywords in patterns.items():
        for keyword in keywords:
            # 스킬 이름에 키워드가 포함된 경우 해당 원소 적용
            pattern = rf'(Skill\("[^"]*{keyword}[^"]*"[^)]*\)[\s\S]*?DamageEffect\([^)]*stat_type="magical")(\))'
            if 'element=' not in content:
                replacement = rf'\1, element="{element}"\2'
                content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def main():
    print("Starting element addition to all job skills...")
    
    for job_name, element_config in JOB_ELEMENT_MAPPING.items():
        filename = f"{job_name}_skills.py"
        filepath = os.path.join(JOB_SKILLS_DIR, filename)
        
        if os.path.exists(filepath):
            success = add_element_to_file(filepath, element_config)
            status = "✓" if success else "✗"
            print(f"{status} {job_name}: {element_config.get('default', 'patterns')}")
        else:
            print(f"? {job_name}: file not found")
    
    print("Done!")

if __name__ == "__main__":
    main()
