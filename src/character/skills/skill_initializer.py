"""
Skill Initializer - 스킬 초기화 시스템

게임 시작 시 모든 직업의 스킬을 SkillManager에 등록합니다.
"""
import os
from src.core.logger import get_logger

logger = get_logger("skill_initializer")

# YAML로 완전 전환된 직업 (Python job_skills 등록을 건너뛰는 기본 목록)
DEFAULT_SKIP_JOBS = {"paladin", "gladiator", "knight", "dimensionist", "hacker", "elementalist", "shaman"}


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
            skill_ids = register_func(skill_manager)
            total_skills += len(skill_ids)
            logger.debug(f"{register_func.__name__}: {len(skill_ids)}개 스킬 등록")

        logger.info(f"[OK] 스킬 초기화 완료: 총 {total_skills}개 스킬 등록됨")
        return True

    except Exception as e:
        logger.error(f"[FAIL] 스킬 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
