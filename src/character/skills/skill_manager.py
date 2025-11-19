"""Skill Manager - 스킬 관리자"""
from typing import Any, Dict, List, Optional
from src.character.skills.skill import Skill, SkillResult
from src.core.event_bus import event_bus, Events
from src.core.logger import get_logger

class SkillManager:
    """스킬 관리자"""
    def __init__(self):
        self.logger = get_logger("skill_manager")
        self._skills = {}
        # self._cooldowns = {}  # 쿨다운 시스템 제거됨

    def register_skill(self, skill: Skill):
        """스킬 등록"""
        self._skills[skill.skill_id] = skill
        self.logger.debug(f"스킬 등록: {skill.name}")

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """스킬 가져오기"""
        return self._skills.get(skill_id)

    def execute_skill(self, skill_id: str, user: Any, target: Any, context: Optional[Dict[str, Any]] = None) -> SkillResult:
        """스킬 실행"""
        skill = self.get_skill(skill_id)
        if not skill:
            return SkillResult(success=False, message=f"스킬 없음: {skill_id}")
        
        # 행동 불가 상태이상 체크 (빙결, 기절 등 - 모든 행동 불가)
        if hasattr(user, 'status_manager'):
            if not user.status_manager.can_act():
                # 기본 공격인지 확인
                is_basic_attack = skill.metadata.get('basic_attack', False)
                if not is_basic_attack:
                    return SkillResult(success=False, message="행동 불가 상태로 인해 스킬을 사용할 수 없습니다")
        
        # 침묵 상태이상 체크 (기본 공격은 제외)
        if hasattr(user, 'status_manager'):
            if not user.status_manager.can_use_skills():
                # 기본 공격인지 확인
                is_basic_attack = skill.metadata.get('basic_attack', False)
                if not is_basic_attack:
                    return SkillResult(success=False, message="침묵 상태로 인해 스킬을 사용할 수 없습니다")

        # 쿨다운 체크 비활성화 (사용자 요청)
        # char_id = id(user)
        # current_cooldown = self._cooldowns.get(char_id, {}).get(skill_id, 0)
        # skill_cooldown_value = getattr(skill, 'cooldown', 0)
        # is_basic_attack = getattr(skill, 'metadata', {}).get('basic_attack', False)

        # self.logger.debug(f"[CD_CHECK] {user.name} - {skill.name} (ID: {skill_id})")
        # self.logger.debug(f"  skill.cooldown = {skill_cooldown_value}, current_cd = {current_cooldown}, basic_attack = {is_basic_attack}")

        # if self.is_on_cooldown(user, skill_id):
        #     self.logger.warning(f"[CD_BLOCK] {skill.name}이(가) 쿨다운 중 (남은: {current_cooldown}턴)")
        #     return SkillResult(success=False, message="쿨다운 중")

        # 캐스팅이 필요한 스킬인지 확인
        if hasattr(skill, 'cast_time') and skill.cast_time and skill.cast_time > 0:
            # 캐스팅 시작
            from src.combat.casting_system import get_casting_system
            casting_system = get_casting_system()

            casting_system.start_cast(
                caster=user,
                skill=skill,
                target=target,
                cast_time_ratio=skill.cast_time,
                atb_threshold=1000,  # 기본 ATB 임계값
                interruptible=True
            )

            # 캐스팅 시작 SFX 재생
            from src.audio import play_sfx
            play_sfx("skill", "cast_start")

            event_bus.publish(Events.SKILL_CAST_START, {"skill": skill, "user": user, "target": target})

            # 캐스팅 중이므로 즉시 실행하지 않음
            return SkillResult(success=True, message=f"{skill.name} 시전 시작")

        # 캐스팅이 필요 없는 스킬은 즉시 실행
        # 저격수 탄환 체크 (magazine_system 기믹)
        if hasattr(user, 'gimmick_type') and user.gimmick_type == "magazine_system":
            bullets_required = skill.metadata.get('bullets_used', 0)
            uses_magazine = skill.metadata.get('uses_magazine', False)

            if uses_magazine and bullets_required > 0:
                current_bullets = len(getattr(user, 'magazine', []))
                if current_bullets < bullets_required:
                    self.logger.warning(f"{user.name}: 탄환 부족! (필요: {bullets_required}, 보유: {current_bullets})")
                    return SkillResult(success=False, message=f"탄환 부족 (필요: {bullets_required}, 보유: {current_bullets})")

        # 스킬 타입에 따른 SFX 재생
        self._play_skill_sfx(skill)

        event_bus.publish(Events.SKILL_CAST_START, {"skill": skill, "user": user, "target": target})
        result = skill.execute(user, target, context)

        # 쿨다운 설정 비활성화 (사용자 요청)
        # if result.success and skill.cooldown > 0:
        #     self.logger.debug(f"[CD_SET] {skill.name} 쿨다운 설정: {skill.cooldown}턴")
        #     self.set_cooldown(user, skill_id, skill.cooldown)
        # else:
        #     self.logger.debug(f"[CD_SKIP] {skill.name} 쿨다운 설정 안 함 (success={result.success}, cooldown={skill.cooldown})")

        event_bus.publish(Events.SKILL_EXECUTE, {"skill": skill, "user": user, "target": target, "result": result})
        return result

    def _play_skill_sfx(self, skill: Skill):
        """스킬 타입에 따라 SFX 재생"""
        from src.audio import play_sfx
        from src.character.skills.effects.damage_effect import DamageEffect, DamageType
        from src.character.skills.effects.buff_effect import BuffEffect
        from src.character.skills.effects.heal_effect import HealEffect

        # 스킬에 직접 SFX가 지정되어 있으면 우선 사용
        if skill.sfx:
            # skill.sfx가 튜플인지 문자열인지 확인
            if isinstance(skill.sfx, tuple):
                category, sfx_name = skill.sfx
                play_sfx(category, sfx_name)
            else:
                # 문자열인 경우 FFVII 카테고리 사용 (FFVII SFX 인덱스 번호)
                play_sfx("ffvii", skill.sfx)
            return

        # 스킬 effects 분석
        has_brv_damage = False
        has_hp_damage = False
        has_buff = False
        has_heal = False
        is_magical = False

        for effect in skill.effects:
            if isinstance(effect, DamageEffect):
                if effect.damage_type == DamageType.BRV:
                    has_brv_damage = True
                elif effect.damage_type == DamageType.HP:
                    has_hp_damage = True
                # 마법 속성 체크
                if hasattr(effect, 'element') and effect.element in ['fire', 'ice', 'lightning', 'holy', 'dark']:
                    is_magical = True
            elif isinstance(effect, BuffEffect):
                has_buff = True
            elif isinstance(effect, HealEffect):
                has_heal = True

        # 우선순위에 따라 SFX 재생
        if has_heal:
            play_sfx("character", "hp_heal")
        elif has_buff:
            play_sfx("character", "status_buff")
        elif has_hp_damage:
            if is_magical:
                play_sfx("combat", "attack_magic")
            else:
                play_sfx("combat", "attack_physical")
        elif has_brv_damage:
            if is_magical:
                play_sfx("skill", "cast_complete")
            else:
                play_sfx("combat", "attack_physical")
        else:
            # 기본 SFX
            play_sfx("skill", "cast_start")

    # 쿨다운 시스템 제거됨 - 아래 메서드들은 더 이상 사용되지 않음
    # def is_on_cooldown(self, character: Any, skill_id: str) -> bool:
    #     """쿨다운 확인"""
    #     char_id = id(character)
    #     return char_id in self._cooldowns and self._cooldowns[char_id].get(skill_id, 0) > 0
    #
    # def get_cooldown(self, character: Any, skill_id: str) -> int:
    #     """남은 쿨다운"""
    #     char_id = id(character)
    #     return self._cooldowns.get(char_id, {}).get(skill_id, 0)
    #
    # def set_cooldown(self, character: Any, skill_id: str, turns: int):
    #     """쿨다운 설정"""
    #     char_id = id(character)
    #     if char_id not in self._cooldowns:
    #         self._cooldowns[char_id] = {}
    #     self._cooldowns[char_id][skill_id] = turns
    #
    # def reduce_cooldowns(self, character: Any, amount: int = 1):
    #     """쿨다운 감소"""
    #     char_id = id(character)
    #     if char_id not in self._cooldowns:
    #         return
    #     for skill_id in list(self._cooldowns[char_id].keys()):
    #         self._cooldowns[char_id][skill_id] -= amount
    #         if self._cooldowns[char_id][skill_id] <= 0:
    #             del self._cooldowns[char_id][skill_id]

_skill_manager = None

def get_skill_manager() -> SkillManager:
    """전역 스킬 관리자"""
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = SkillManager()
    return _skill_manager
