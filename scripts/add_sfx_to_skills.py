"""
YAML 스킬 파일에 SFX를 자동으로 추가하는 스크립트

스킬의 타입, 직업, 효과에 따라 적절한 SFX를 지정합니다.
"""

import yaml
from pathlib import Path
from typing import Dict, Any, List, Tuple

SKILLS_DIR = Path("data/skills")

# SFX 매핑 규칙
SFX_MAPPING = {
    # 해커 직업
    "hacker": {
        "default": ("se", "Computer"),
        "keywords": {
            "ddos": ("se", "Laser1"),
            "virus": ("se", "Poison"),
            "firewall": ("se", "Barrier"),
            "rootkit": ("se", "Darkness3"),
            "zero_day": ("se", "Explosion2"),
            "ultimate": ("se", "Explosion4"),
        }
    },

    # 정령술사 (Elementalist)
    "elementalist": {
        "default": ("se", "Magic1"),
        "keywords": {
            "fire": ("se", "Fire2"),
            "ice": ("se", "Ice2"),
            "thunder": ("se", "Thunder2"),
            "earth": ("se", "Earth1"),
            "wind": ("se", "Wind1"),
            "water": ("se", "Water1"),
            "fusion": ("se", "Magic2"),
            "overload": ("se", "Explosion3"),
            "ultimate": ("se", "Explosion4"),
            "teamwork": ("se", "Summon"),
        }
    },

    # 샤먼 (Shaman)
    "shaman": {
        "default": ("se", "Magic1"),
        "keywords": {
            "spirit": ("se", "Magic2"),
            "soul": ("se", "Darkness3"),
            "curse": ("se", "Poison"),
            "plague": ("se", "Poison"),
            "nightmare": ("se", "Darkness3"),
            "purification": ("se", "Heal4"),
            "blessing": ("se", "Up1"),
            "ultimate": ("se", "Explosion4"),
            "teamwork": ("se", "Summon"),
        }
    },

    # 팔라딘 (Paladin)
    "paladin": {
        "default": ("se", "Sword2"),
        "keywords": {
            "holy": ("se", "Heal4"),
            "smite": ("se", "Damage5"),
            "hammer": ("se", "Blow10"),
            "judgment": ("se", "Thunder2"),
            "shield": ("se", "Barrier"),
            "blessing": ("se", "Up1"),
            "consecration": ("se", "Heal4"),
            "wrath": ("se", "Fire2"),
            "ultimate": ("se", "Explosion4"),
            "teamwork": ("se", "Summon"),
        }
    },

    # 프리스트 (Priest)
    "priest": {
        "default": ("se", "Heal1"),
        "keywords": {
            "heal": ("se", "Recovery"),
            "blessing": ("se", "Up1"),
            "smite": ("se", "Thunder1"),
            "judgment": ("se", "Thunder2"),
            "miracle": ("se", "Heal4"),
            "resurrection": ("se", "Raise1"),
            "grace": ("se", "Up2"),
            "ultimate": ("se", "Explosion4"),
            "teamwork": ("se", "Summon"),
        }
    },

    # 나이트 (Knight)
    "knight": {
        "default": ("se", "Sword2"),
        "keywords": {
            "bash": ("se", "Blow10"),
            "lance": ("se", "Damage3"),
            "shield": ("se", "Barrier"),
            "oath": ("se", "Up1"),
            "bulwark": ("se", "Barrier"),
            "devotion": ("se", "Up2"),
            "ultimate": ("se", "Explosion4"),
            "teamwork": ("se", "Summon"),
        }
    },

    # 글래디에이터 (Gladiator)
    "gladiator": {
        "default": ("se", "Sword2"),
        "keywords": {
            "arena": ("se", "Damage3"),
            "roar": ("se", "Blow10"),
            "glory": ("se", "Damage5"),
            "honor": ("se", "Sword4"),
            "champion": ("se", "Up2"),
            "spectacular": ("se", "Explosion2"),
            "ultimate": ("se", "Explosion4"),
            "teamwork": ("se", "Summon"),
        }
    },

    # 로그 (Rogue)
    "rogue": {
        "default": ("se", "Slash1"),
        "keywords": {
            "shadow": ("se", "Darkness3"),
            "nightfall": ("se", "Blind"),
            "backstab": ("se", "Damage5"),
            "poison": ("se", "Poison"),
            "smoke": ("se", "Blind"),
            "steal": ("se", "Item1"),
            "ultimate": ("se", "Explosion4"),
            "teamwork": ("se", "Summon"),
        }
    },

    # 워리어 (Warrior)
    "warrior": {
        "default": ("se", "Sword2"),
        "keywords": {
            "strike": ("se", "Damage3"),
            "bulwark": ("se", "Barrier"),
            "guardian": ("se", "Up1"),
            "steel": ("se", "Barrier"),
            "ultimate": ("se", "Explosion4"),
            "teamwork": ("se", "Summon"),
        }
    },

    # 차원술사 (Dimensionist)
    "dimensionist": {
        "default": ("se", "Magic1"),
        "keywords": {
            "dimension": ("se", "Move2"),
            "refraction": ("se", "Reflection"),
            "barrier": ("se", "Barrier"),
            "explosion": ("se", "Explosion2"),
            "scatter": ("se", "Wind1"),
            "temporal": ("se", "Up2"),
            "backflow": ("se", "Down2"),
            "ultimate": ("se", "Explosion4"),
            "teamwork": ("se", "Summon"),
        }
    },
}

# 일반 스킬 타입별 기본 SFX
DEFAULT_SFX = {
    # 물리 공격
    "physical_attack": ("se", "Damage3"),
    "slash": ("se", "Slash1"),
    "strike": ("se", "Damage3"),
    "stab": ("se", "Slash2"),

    # 마법 공격
    "magic_attack": ("se", "Magic1"),
    "fire": ("se", "Fire1"),
    "ice": ("se", "Ice1"),
    "thunder": ("se", "Thunder1"),
    "earth": ("se", "Earth1"),
    "wind": ("se", "Wind1"),
    "water": ("se", "Water1"),
    "dark": ("se", "Darkness3"),
    "holy": ("se", "Heal4"),

    # 힐/버프
    "heal": ("se", "Recovery"),
    "buff": ("se", "Up1"),
    "protect": ("se", "Barrier"),
    "barrier": ("se", "Barrier"),

    # 디버프
    "debuff": ("se", "Down1"),
    "poison": ("se", "Poison"),
    "curse": ("se", "Darkness3"),

    # 특수
    "ultimate": ("se", "Explosion4"),
    "teamwork": ("se", "Summon"),
    "summon": ("se", "Summon"),
}


def detect_job_from_id(skill_id: str) -> str:
    """스킬 ID에서 직업명 추출"""
    parts = skill_id.split("_")
    if len(parts) > 0:
        return parts[0].lower()
    return ""


def detect_skill_type(skill_data: Dict[str, Any]) -> List[str]:
    """스킬 데이터에서 타입 키워드 추출"""
    keywords = []

    # ID에서 키워드 추출
    skill_id = skill_data.get("id", "").lower()
    keywords.extend(skill_id.split("_"))

    # 이름에서 키워드 추출
    name = skill_data.get("name", "").lower()
    keywords.append(name)

    # 설명에서 키워드 추출
    description = skill_data.get("description", "").lower()

    # 효과 타입에서 키워드 추출
    effects = skill_data.get("effects", [])
    for effect in effects:
        if isinstance(effect, dict):
            effect_type = effect.get("type", "")
            keywords.append(effect_type)

            # 데미지 타입 확인
            if effect_type == "damage":
                stat_base = effect.get("stat_base", "")
                if stat_base == "magical":
                    keywords.append("magic")
                elif stat_base == "physical":
                    keywords.append("physical")

    return keywords


def select_sfx(skill_data: Dict[str, Any]) -> Tuple[str, str]:
    """스킬 데이터에서 적절한 SFX 선택"""

    # 메타데이터에서 직업 확인
    metadata = skill_data.get("metadata", {})
    job = metadata.get("job", "")

    # 직업이 없으면 ID에서 추출
    if not job:
        job = detect_job_from_id(skill_data.get("id", ""))

    # 스킬 타입 키워드 추출
    keywords = detect_skill_type(skill_data)

    # 직업별 매핑 확인
    if job in SFX_MAPPING:
        job_mapping = SFX_MAPPING[job]

        # 키워드 매칭
        for keyword in keywords:
            for key, sfx in job_mapping.get("keywords", {}).items():
                if key in keyword:
                    return sfx

        # 직업 기본값
        return job_mapping["default"]

    # 일반 키워드 매칭
    for keyword in keywords:
        for key, sfx in DEFAULT_SFX.items():
            if key in keyword:
                return sfx

    # 최종 기본값 - 스킬 타입에 따라
    skill_type = skill_data.get("type", "attack")
    if skill_type == "support":
        return ("se", "Up1")
    elif skill_type == "heal":
        return ("se", "Recovery")
    else:
        return ("se", "Magic1")  # 기본 마법 효과음


def add_sfx_to_skill_file(file_path: Path, dry_run: bool = False) -> bool:
    """YAML 파일에 SFX 추가"""
    try:
        # YAML 파일 읽기
        with file_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # 이미 SFX가 있으면 스킵
        if "sfx" in data:
            print(f"[SKIP] {file_path.name}: 이미 SFX 존재")
            return False

        # SFX 선택
        sfx_category, sfx_name = select_sfx(data)

        if dry_run:
            print(f"[TEST] {file_path.name}: [{sfx_category}, {sfx_name}]")
            return True

        # SFX 추가
        data["sfx"] = [sfx_category, sfx_name]

        # YAML 파일 다시 쓰기 (원본 포맷 최대한 유지)
        with file_path.open("w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

        print(f"[OK] {file_path.name}: SFX 추가 [{sfx_category}, {sfx_name}]")
        return True

    except Exception as e:
        print(f"[ERROR] {file_path.name}: 오류 - {e}")
        return False


def main():
    """메인 실행"""
    import argparse

    parser = argparse.ArgumentParser(description="YAML 스킬 파일에 SFX 추가")
    parser.add_argument("--dry-run", action="store_true", help="실제 파일 변경 없이 미리보기")
    parser.add_argument("--filter", type=str, help="특정 파일만 처리 (예: hacker)")
    args = parser.parse_args()

    if not SKILLS_DIR.exists():
        print(f"[ERROR] 스킬 디렉토리가 없습니다: {SKILLS_DIR}")
        return

    print("=" * 60)
    print("YAML 스킬 SFX 자동 추가 스크립트")
    print("=" * 60)

    if args.dry_run:
        print("[WARNING] DRY RUN 모드 - 파일을 변경하지 않습니다")

    print()

    # 파일 목록
    skill_files = sorted(SKILLS_DIR.glob("*.yaml"))

    if args.filter:
        skill_files = [f for f in skill_files if args.filter.lower() in f.name.lower()]
        print(f"[FILTER] '{args.filter}' 포함 파일만 처리")

    print(f"[INFO] 총 {len(skill_files)}개 파일 발견")
    print()

    # 처리
    success_count = 0
    skip_count = 0
    error_count = 0

    for file_path in skill_files:
        try:
            if add_sfx_to_skill_file(file_path, dry_run=args.dry_run):
                success_count += 1
            else:
                skip_count += 1
        except Exception as e:
            print(f"[ERROR] {file_path.name}: {e}")
            error_count += 1

    # 결과 요약
    print()
    print("=" * 60)
    print("처리 완료")
    print("=" * 60)
    print(f"[OK] 성공: {success_count}개")
    print(f"[SKIP] 스킵: {skip_count}개 (이미 SFX 존재)")
    print(f"[ERROR] 오류: {error_count}개")
    print()

    if args.dry_run:
        print("[INFO] 실제 적용하려면 --dry-run 옵션 없이 다시 실행하세요")


if __name__ == "__main__":
    main()
