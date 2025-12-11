"""
YAML 스킬 파일 원소 추가 스크립트
스킬 이름/파일명 기반으로 적절한 원소 할당
"""
import os
import yaml
from pathlib import Path

SKILLS_DIR = Path("x:/develop/Dawn-of-Stellar/data/skills")

# 스킬 파일명 패턴 -> 원소 매핑
ELEMENT_PATTERNS = {
    # 화염 계열
    "fire": ["fire", "flame", "burn", "inferno", "blaze", "meteor", "dragon", "volcano", "lava"],
    # 빙결 계열
    "ice": ["ice", "frost", "freeze", "blizzard", "cold", "arctic", "snow", "glacial"],
    # 전기 계열
    "lightning": ["thunder", "lightning", "shock", "bolt", "storm", "electric", "volt"],
    # 신성 계열
    "holy": ["holy", "divine", "sacred", "blessing", "heal", "light", "prayer", "miracle", "grace", "purify", "resurrection", "sanctuary"],
    # 암흑 계열
    "dark": ["dark", "shadow", "curse", "death", "abyss", "nightmare", "blood", "drain", "vampire", "necro", "soul", "poison", "plague", "spirit", "ancestor"],
    # 대지 계열
    "earth": ["earth", "rock", "stone", "mud", "vine", "nature", "root", "bear"],
    # 바람 계열
    "wind": ["wind", "air", "gale", "tornado", "storm", "eagle"],
    # 물 계열
    "water": ["water", "aqua", "wave", "ocean", "rain", "stream"],
}

# 직업별 기본 원소
JOB_ELEMENTS = {
    "paladin": "holy",
    "priest": "holy",
    "cleric": "holy",
    "shaman": "dark",
    "necromancer": "dark",
    "vampire": "dark",
    "dark_knight": "dark",
    "dragon_knight": "fire",
    "elementalist": None,  # 복합
    "archmage": None,  # 복합
}

def get_element_for_skill(filepath: Path, content: dict) -> str | None:
    """스킬 파일에 적절한 원소 결정"""
    filename = filepath.stem.lower()
    skill_name = content.get("name", "").lower()
    job = content.get("metadata", {}).get("job", "").lower() if content.get("metadata") else ""
    
    # 이미 원소가 있는 effects 확인
    effects = content.get("effects", [])
    for effect in effects:
        if isinstance(effect, dict) and effect.get("element"):
            return None  # 이미 원소 있음
    
    # 파일명/스킬명으로 원소 추론
    combined = f"{filename} {skill_name}"
    
    for element, patterns in ELEMENT_PATTERNS.items():
        for pattern in patterns:
            if pattern in combined:
                return element
    
    # 직업 기반 기본 원소
    if job in JOB_ELEMENTS:
        return JOB_ELEMENTS[job]
    
    # 파일명에서 직업 추출 시도
    for job_name, default_element in JOB_ELEMENTS.items():
        if job_name in filename:
            return default_element
    
    return None

def add_element_to_effects(content: dict, element: str) -> bool:
    """effects에 element 추가"""
    effects = content.get("effects", [])
    modified = False
    
    for effect in effects:
        if isinstance(effect, dict):
            if effect.get("type") == "damage" and not effect.get("element"):
                effect["element"] = element
                modified = True
    
    return modified

def process_skill_file(filepath: Path) -> tuple[bool, str]:
    """단일 스킬 파일 처리"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = yaml.safe_load(f)
        
        if not content:
            return False, "empty"
        
        element = get_element_for_skill(filepath, content)
        if not element:
            return False, "no_element_needed"
        
        if add_element_to_effects(content, element):
            # 설명에 원소 추가
            desc = content.get("description", "")
            element_labels = {
                "fire": "[화염 속성]",
                "ice": "[빙결 속성]",
                "lightning": "[전기 속성]",
                "holy": "[신성 속성]",
                "dark": "[암흑 속성]",
                "earth": "[대지 속성]",
                "wind": "[바람 속성]",
                "water": "[물 속성]",
            }
            label = element_labels.get(element, f"[{element}]")
            if label not in desc:
                content["description"] = f"{label} {desc}"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(content, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            
            return True, element
        
        return False, "already_has_element"
        
    except Exception as e:
        return False, str(e)

def main():
    results = {"updated": [], "skipped": [], "errors": []}
    
    for filepath in SKILLS_DIR.glob("*.yaml"):
        success, info = process_skill_file(filepath)
        if success:
            results["updated"].append((filepath.name, info))
        elif info.startswith("no_element") or info == "already_has_element":
            results["skipped"].append((filepath.name, info))
        else:
            results["errors"].append((filepath.name, info))
    
    print(f"Updated: {len(results['updated'])} files")
    print(f"Skipped: {len(results['skipped'])} files")
    print(f"Errors: {len(results['errors'])} files")
    
    print("\n=== Updated Files ===")
    for name, element in results["updated"][:30]:
        print(f"  {name}: {element}")
    if len(results["updated"]) > 30:
        print(f"  ... and {len(results['updated']) - 30} more")

if __name__ == "__main__":
    main()
