"""
Skill Initializer - 스킬 초기화 시스템

게임 시작 시 모든 직업의 스킬을 SkillManager에 등록합니다.
"""
from src.core.logger import get_logger

logger = get_logger("skill_initializer")


def initialize_all_skills():
    """
    모든 직업의 스킬을 등록합니다.

    게임 시작 시 한 번만 호출되어야 합니다.
    """
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

        register_functions = [
            register_alchemist_skills,
            register_archer_skills,
            register_archmage_skills,
            register_assassin_skills,
            register_bard_skills,
            register_battle_mage_skills,
            register_berserker_skills,
            register_breaker_skills,
            register_cleric_skills,
            register_dark_knight_skills,
            register_dimensionist_skills,
            register_dragon_knight_skills,
            register_druid_skills,
            register_elementalist_skills,
            register_engineer_skills,
            register_gladiator_skills,
            register_hacker_skills,
            register_knight_skills,
            register_monk_skills,
            register_necromancer_skills,
            register_paladin_skills,
            register_philosopher_skills,
            register_pirate_skills,
            register_priest_skills,
            register_rogue_skills,
            register_samurai_skills,
            register_shaman_skills,
            register_sniper_skills,
            register_spellblade_skills,
            register_sword_saint_skills,
            register_time_mage_skills,
            register_vampire_skills,
            register_warrior_skills
        ]

        total_skills = 0
        for register_func in register_functions:
            skill_ids = register_func(skill_manager)
            total_skills += len(skill_ids)
            logger.debug(f"{register_func.__name__}: {len(skill_ids)}개 스킬 등록")

        logger.info(f"✅ 스킬 초기화 완료: 총 {total_skills}개 스킬 등록됨")
        return True

    except Exception as e:
        logger.error(f"❌ 스킬 초기화 실패: {e}")
        import traceback
        traceback.print_exc()
        return False
