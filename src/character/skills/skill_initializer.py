"""
Skill Initializer - 스킬 초기화 시스템

게임 시작 시 모든 직업의 스킬을 SkillManager에 등록합니다.

단일 정본 규칙: data/skills/*.yaml 이 스킬 정의의 정본(authority)이다.
Python job_skills는 YAML에 없는 레거시 전용 스킬만 추가 등록하며,
동일 ID를 재정의한 경우 YAML 정본 인스턴스로 복원된다.
"""
import os
from src.core.logger import get_logger

logger = get_logger("skill_initializer")

# YAML로 완전 전환된 직업 (Python job_skills 등록을 건너뛰는 기본 목록)
DEFAULT_SKIP_JOBS = {"paladin", "gladiator", "knight", "dimensionist", "hacker", "elementalist", "shaman", "cleric"}


def initialize_all_skills():
    """
    모든 직업의 스킬을 등록합니다.

    게임 시작 시 한 번만 호출되어야 합니다.
    """
    # 설정 미초기화 시 기본 설정 로드
    try:
        from src.core.config import get_config, initialize_config
        try:
            get_config()
        except Exception:
            initialize_config()
    except Exception:
        # 설정 초기화 실패해도 진행은 시도 (테스트/툴링 환경)
        pass
    from src.character.skills.skill_manager import get_skill_manager
    skill_manager = get_skill_manager()

    logger.info("스킬 초기화 시작...")

    try:
        # 각 직업별 스킬 등록
        from src.character.skills.job_skills.alchemist_skills import register_alchemist_skills
        from src.character.skills.job_skills.archer_skills import register_archer_skills
        from src.character.skills.job_skills.archmage_skills import register_archmage_skills
        from src.character.skills.job_skills.assassin_skills import register_assassin_skills
        from src.character.skills.job_skills.bard_skills import register_bard_skills
        from src.character.skills.job_skills.battle_mage_skills import register_battle_mage_skills
        from src.character.skills.job_skills.berserker_skills import register_berserker_skills
        from src.character.skills.job_skills.breaker_skills import register_breaker_skills
        from src.character.skills.job_skills.cleric_skills import register_cleric_skills
        from src.character.skills.job_skills.dark_knight_skills import register_dark_knight_skills
        from src.character.skills.job_skills.dimensionist_skills import register_dimensionist_skills
        from src.character.skills.job_skills.dragon_knight_skills import register_dragon_knight_skills
        from src.character.skills.job_skills.druid_skills import register_druid_skills
        from src.character.skills.job_skills.elementalist_skills import register_elementalist_skills
        from src.character.skills.job_skills.engineer_skills import register_engineer_skills
        from src.character.skills.job_skills.gladiator_skills import register_gladiator_skills
        from src.character.skills.job_skills.hacker_skills import register_hacker_skills
        from src.character.skills.job_skills.knight_skills import register_knight_skills
        from src.character.skills.job_skills.monk_skills import register_monk_skills
        from src.character.skills.job_skills.necromancer_skills import register_necromancer_skills
        from src.character.skills.job_skills.paladin_skills import register_paladin_skills
        from src.character.skills.job_skills.philosopher_skills import register_philosopher_skills
        from src.character.skills.job_skills.pirate_skills import register_pirate_skills
        from src.character.skills.job_skills.priest_skills import register_priest_skills
        from src.character.skills.job_skills.rogue_skills import register_rogue_skills
        from src.character.skills.job_skills.samurai_skills import register_samurai_skills
        from src.character.skills.job_skills.shaman_skills import register_shaman_skills
        from src.character.skills.job_skills.sniper_skills import register_sniper_skills
        from src.character.skills.job_skills.spellblade_skills import register_spellblade_skills
        from src.character.skills.job_skills.sword_saint_skills import register_sword_saint_skills
        from src.character.skills.job_skills.time_mage_skills import register_time_mage_skills
        from src.character.skills.job_skills.vampire_skills import register_vampire_skills
        from src.character.skills.job_skills.warrior_skills import register_warrior_skills
        from src.character.skills.job_skills.magician_skills import register_magician_skills
        from src.character.skills.job_skills.illusionist_skills import register_illusionist_skills
        from src.character.skills.job_skills.ninja_skills import register_ninja_skills

        from src.character.skills.yaml_skill_loader import load_yaml_skills

        yaml_ids = load_yaml_skills(skill_manager)
        logger.info("[YAML] 스킬 %d개 등록", len(yaml_ids))
        # YAML 단일 정본 스냅샷: 이후 Python job_skills 등록이 동일 ID를 덮어쓰지 않도록 한다.
        # (재초기화 시 load_yaml_skills가 중복 skip하므로 현재 매니저에 YAML 인스턴스가
        #  남아 있지 않을 수 있다 → 이 경우 파일에서 직접 다시 로드한다.)
        from src.character.skills.yaml_skill_loader import _load_yaml_file, _create_skill, SKILLS_DIR
        yaml_id_set = set(yaml_ids)
        yaml_loaded_skills = {sid: skill_manager._skills[sid] for sid in yaml_id_set}
        if SKILLS_DIR.exists():
            for file_path in sorted(SKILLS_DIR.glob("*.yaml")):
                data = _load_yaml_file(file_path)
                if not data or data.get("metadata", {}).get("state") == "deprecated":
                    continue
                try:
                    skill = _create_skill(data)
                except Exception:
                    continue
                yaml_id_set.add(skill.skill_id)
                yaml_loaded_skills[skill.skill_id] = skill

        skip_jobs_env = os.getenv("SKIP_PY_JOB_SKILLS", "")
        env_skip_jobs = {
            job.strip().lower()
            for job in skip_jobs_env.replace(";", ",").split(",")
            if job.strip()
        }
        # 기본값: YAML로 100% 이관 완료된 직업은 Python 등록을 건너뛴다.
        skip_jobs = env_skip_jobs if env_skip_jobs else DEFAULT_SKIP_JOBS

        register_functions = [
            ("alchemist", register_alchemist_skills),
            ("archer", register_archer_skills),
            ("archmage", register_archmage_skills),
            ("assassin", register_assassin_skills),
            ("bard", register_bard_skills),
            ("battle_mage", register_battle_mage_skills),
            ("berserker", register_berserker_skills),
            ("breaker", register_breaker_skills),
            ("cleric", register_cleric_skills),
            ("dark_knight", register_dark_knight_skills),
            ("dimensionist", register_dimensionist_skills),
            ("dragon_knight", register_dragon_knight_skills),
            ("druid", register_druid_skills),
            ("elementalist", register_elementalist_skills),
            ("engineer", register_engineer_skills),
            ("gladiator", register_gladiator_skills),
            ("hacker", register_hacker_skills),
            ("knight", register_knight_skills),
            ("monk", register_monk_skills),
            ("necromancer", register_necromancer_skills),
            ("paladin", register_paladin_skills),
            ("philosopher", register_philosopher_skills),
            ("pirate", register_pirate_skills),
            ("priest", register_priest_skills),
            ("rogue", register_rogue_skills),
            ("samurai", register_samurai_skills),
            ("shaman", register_shaman_skills),
            ("sniper", register_sniper_skills),
            ("spellblade", register_spellblade_skills),
            ("sword_saint", register_sword_saint_skills),
            ("time_mage", register_time_mage_skills),
            ("vampire", register_vampire_skills),
            ("warrior", register_warrior_skills),
            ("magician", register_magician_skills),
            ("illusionist", register_illusionist_skills),
            ("ninja", register_ninja_skills)
        ]

        total_skills = len(yaml_ids)
        for job_name, register_func in register_functions:
            if job_name in skip_jobs:
                logger.info("[SKIP] %s job_skills 등록 생략 (SKIP_PY_JOB_SKILLS)", job_name)
                continue
            before_ids = set(skill_manager._skills.keys())
            skill_ids = register_func(skill_manager)
            # YAML 단일 정본: Python 등록이 동일 ID의 YAML 스킬을 덮어썼다면 원래 YAML 스킬을 복원한다.
            # (YAML에 없는 레거시 전용 Python 스킬만 유지)
            # 검사 대상: 신규 추가 id + 반환된 id(기존 id를 덮어쓴 경우 포함)
            restored = 0
            for sid in (set(skill_manager._skills.keys()) - before_ids) | set(skill_ids or []):
                if sid in yaml_id_set:
                    skill_manager._skills[sid] = yaml_loaded_skills[sid]
                    restored += 1
            if restored:
                logger.info(f"[YAML 우선] {job_name}: Python 재정의 {restored}개 스킬을 YAML 정본으로 복원")
            total_skills += len(skill_ids)
            logger.debug(f"{register_func.__name__}: {len(skill_ids)}개 스킬 등록")

        logger.info(f"[OK] 스킬 초기화 완료: 총 {total_skills}개 스킬 등록됨")
        return True

    except Exception as e:
        logger.error(f"[FAIL] 스킬 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
