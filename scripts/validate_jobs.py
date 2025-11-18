"""모든 직업 시스템 검증 스크립트"""
import sys
import os
import importlib
import inspect
from pathlib import Path

# UTF-8 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.character.skills.skill import Skill
from src.core.config import initialize_config

# 설정 초기화
try:
    config_path = project_root / "config.yaml"
    initialize_config(str(config_path))
except Exception as e:
    print(f"경고: 설정 초기화 실패 - {e}")
    print("일부 검증이 제한될 수 있습니다.")


def validate_job_skills(job_name):
    """특정 직업의 스킬 검증"""
    errors = []
    warnings = []

    try:
        # 스킬 모듈 임포트
        module_name = f"src.character.skills.job_skills.{job_name}_skills"
        module = importlib.import_module(module_name)

        # create_XXX_skills 함수 찾기
        create_func_name = f"create_{job_name}_skills"
        if not hasattr(module, create_func_name):
            errors.append(f"함수 '{create_func_name}' 없음")
            return errors, warnings

        create_func = getattr(module, create_func_name)

        # 스킬 생성 시도
        try:
            skills = create_func()
        except Exception as e:
            errors.append(f"스킬 생성 실패: {str(e)}")
            return errors, warnings

        # 스킬 개수 확인
        if not isinstance(skills, list):
            errors.append(f"스킬이 리스트가 아님: {type(skills)}")
            return errors, warnings

        if len(skills) != 10:
            warnings.append(f"스킬 개수가 10개가 아님: {len(skills)}개")

        # 각 스킬 검증
        for i, skill in enumerate(skills):
            if not isinstance(skill, Skill):
                errors.append(f"스킬[{i}]가 Skill 인스턴스가 아님: {type(skill)}")
                continue

            # 스킬 ID, 이름 체크
            if not hasattr(skill, 'skill_id') or not skill.skill_id:
                errors.append(f"스킬[{i}] ID 없음")
            if not skill.name:
                errors.append(f"스킬[{i}] 이름 없음")

            # effects 체크
            if not hasattr(skill, 'effects') or skill.effects is None:
                warnings.append(f"스킬 '{skill.name}' effects 없음")
            elif not isinstance(skill.effects, list):
                errors.append(f"스킬 '{skill.name}' effects가 리스트가 아님")

            # costs 체크
            if not hasattr(skill, 'costs'):
                warnings.append(f"스킬 '{skill.name}' costs 없음")

            # target_type 체크
            if not hasattr(skill, 'target_type'):
                warnings.append(f"스킬 '{skill.name}' target_type 없음")
            elif skill.target_type not in ['enemy', 'ally', 'self', 'all_enemies', 'all_allies', 'all']:
                warnings.append(f"스킬 '{skill.name}' 이상한 target_type: {skill.target_type}")

    except ModuleNotFoundError:
        errors.append(f"모듈 파일 없음: {job_name}_skills.py")
    except Exception as e:
        errors.append(f"예외 발생: {str(e)}")

    return errors, warnings


def main():
    """모든 직업 검증"""
    print("=" * 80)
    print("모든 직업 시스템 검증 시작")
    print("=" * 80)

    # 모든 직업 목록
    jobs = [
        "alchemist", "archer", "archmage", "assassin", "bard", "battle_mage",
        "berserker", "breaker", "cleric", "dark_knight", "dimensionist",
        "dragon_knight", "druid", "elementalist", "engineer", "gladiator",
        "hacker", "knight", "monk", "necromancer", "paladin", "philosopher",
        "pirate", "priest", "rogue", "samurai", "shaman", "sniper",
        "spellblade", "sword_saint", "time_mage", "vampire", "warrior"
    ]

    total_errors = 0
    total_warnings = 0
    jobs_with_errors = []
    jobs_with_warnings = []

    for job in jobs:
        print(f"\n[{job.upper()}]")
        errors, warnings = validate_job_skills(job)

        if errors:
            total_errors += len(errors)
            jobs_with_errors.append(job)
            print(f"  ❌ 에러 {len(errors)}개:")
            for error in errors:
                print(f"     - {error}")

        if warnings:
            total_warnings += len(warnings)
            jobs_with_warnings.append(job)
            print(f"  ⚠️  경고 {len(warnings)}개:")
            for warning in warnings:
                print(f"     - {warning}")

        if not errors and not warnings:
            print("  ✅ 정상")

    print("\n" + "=" * 80)
    print(f"검증 완료:")
    print(f"  - 총 직업: {len(jobs)}개")
    print(f"  - 정상: {len(jobs) - len(set(jobs_with_errors + jobs_with_warnings))}개")
    print(f"  - 에러 있음: {len(jobs_with_errors)}개")
    print(f"  - 경고만 있음: {len(set(jobs_with_warnings) - set(jobs_with_errors))}개")
    print(f"  - 총 에러: {total_errors}개")
    print(f"  - 총 경고: {total_warnings}개")
    print("=" * 80)

    if jobs_with_errors:
        print(f"\n에러가 있는 직업: {', '.join(jobs_with_errors)}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
