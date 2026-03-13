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

    def get_skills_for_character(self, character) -> List[Skill]:
        """캐릭터가 사용 가능한 스킬 목록 반환"""
        skills = []
        skill_ids = getattr(character, 'skill_ids', [])
        for skill_id in skill_ids:
            skill = self.get_skill(skill_id)
            if skill:
                skills.append(skill)
        return skills

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
                # 기본 공격인지 확인 (여러 방법으로 확인)
                is_basic_attack = skill.metadata.get('basic_attack', False)
                
                # 메타데이터에 없으면 다른 방법으로 확인
                if not is_basic_attack:
                    # 1. costs가 비어있고 (MP 소모 없음)
                    # 2. 스킬이 사용자의 skill_ids에서 첫 번째 또는 두 번째인 경우
                    if not skill.costs and hasattr(user, 'skill_ids') and user.skill_ids:
                        skill_index = user.skill_ids.index(skill_id) if skill_id in user.skill_ids else -1
                        if skill_index in [0, 1]:  # 첫 번째 또는 두 번째 스킬
                            is_basic_attack = True
                
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

            # divine_grace 특성: MP 50% 이상일 때 회복 스킬 시전 시간 -60%
            effective_cast_time = skill.cast_time
            if hasattr(user, 'active_traits'):
                has_divine_grace = any(
                    (t if isinstance(t, str) else t.get('id')) == 'divine_grace'
                    for t in user.active_traits
                )
                if has_divine_grace:
                    # MP 50% 이상인지 확인
                    current_mp = getattr(user, 'current_mp', 0)
                    max_mp = getattr(user, 'max_mp', 1)
                    if current_mp >= max_mp * 0.5:
                        # 회복 스킬인지 확인
                        is_healing_skill = skill.metadata.get('healing', False)
                        if is_healing_skill:
                            effective_cast_time = skill.cast_time * 0.4  # -60% = 40% of original
                            self.logger.debug(f"[divine_grace] {user.name}의 {skill.name} 시전 시간 -60% ({skill.cast_time} -> {effective_cast_time})")

            casting_system.start_cast(
                caster=user,
                skill=skill,
                target=target,
                cast_time_ratio=effective_cast_time,
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

        # context에 skill 정보 추가 (다단히트, 여러 효과 처리를 위해 필요)
        if context is None:
            context = {}
        context['skill'] = skill

        # 메타데이터 기반 사용 조건 검사 (기믹 요구 등)
        meta = getattr(skill, "metadata", {}) or {}
        # 해커 RAM 체크/버닝 준비
        ram_cost = 0
        ram_burn = 0
        if getattr(user, "gimmick_type", None) == "intrusion_system":
            ram_cost = int(meta.get("ram_cost", 0) or 0)
            # YAML costs에 ram 키가 있는 경우 함께 반영
            if ram_cost == 0 and getattr(skill, "costs", None):
                for c in skill.costs:
                    try:
                        if isinstance(c, dict) and "ram" in c:
                            ram_cost = max(ram_cost, int(c.get("ram", 0) or 0))
                        elif hasattr(c, "cost_type") and getattr(c, "cost_type") == "ram":
                            ram_cost = max(ram_cost, int(getattr(c, "amount", 0) or getattr(c, "value", 0) or 0))
                    except Exception:
                        continue

            # 오버클럭 시 RAM 소모량 할인 적용
            if getattr(user, "overclock_active", False):
                discount = int(getattr(user, "overclock_data", {}).get("ram_cost_discount", 0))
                if discount > 0:
                    ram_cost = max(0, ram_cost - discount)
            burn_per = float(meta.get("ram_burn_bonus_per", 0) or 0)
            burn_max = int(meta.get("ram_burn_max", 0) or 0)
            if ram_cost and getattr(user, "ram", 0) < ram_cost:
                return SkillResult(success=False, message=f"RAM 부족 (필요: {ram_cost}, 보유: {getattr(user, 'ram', 0)})")
            if burn_per > 0 and burn_max > 0:
                available = max(0, getattr(user, "ram", 0) - ram_cost)
                ram_burn = min(available, burn_max)
                if ram_burn > 0:
                    ctx_mult = context.get("power_multiplier", 1.0)
                    context["power_multiplier"] = ctx_mult * (1 + burn_per * ram_burn)
        # 침투 요구
        if meta.get("requires_intrusion") is not None and target is not None:
            required_intrusion = meta.get("requires_intrusion", 0)
            current_intrusion = getattr(target, "intrusion_gauge", 0)
            if current_intrusion < required_intrusion:
                return SkillResult(success=False, message=f"침투 {required_intrusion}% 이상 필요 (현재 {current_intrusion}%)")
        # 독 중첩 요구
        if meta.get("requires_venom") is not None and target is not None:
            required_venom = meta.get("requires_venom", 0)
            current_venom = getattr(target, "venom_stacks", 0)
            if current_venom < required_venom:
                return SkillResult(success=False, message=f"독 중첩 {required_venom}+ 필요 (현재 {current_venom})")
        # 정령 소환 수 요구 (정령술사)
        if meta.get("requires_spirits") is not None and getattr(user, "gimmick_type", None) == "elemental_spirits":
            from src.character.gimmick_updater import GimmickUpdater
            required_spirits = meta.get("requires_spirits", 0)
            active_spirits = GimmickUpdater.get_active_spirits_count(user)
            if active_spirits < required_spirits:
                return SkillResult(success=False, message=f"정령 {required_spirits}마리 필요 (현재 {active_spirits})")
        # 굴절 요구 (차원술사)
        if meta.get("requires_refraction_check") and getattr(user, "gimmick_type", None) == "dimension_refraction":
            refraction = getattr(user, "refraction_stacks", 0)
            if refraction <= 0:
                return SkillResult(success=False, message="굴절량 부족")
        # 정령 융합 요구
        if meta.get("fusion") and getattr(user, "gimmick_type", None) == "elemental_spirits":
            requires = meta.get("requires", [])
            missing = [sp for sp in requires if getattr(user, f"spirit_{sp}", 0) <= 0]
            if missing:
                missing_names = ", ".join(missing)
                return SkillResult(success=False, message=f"융합 실패: 정령 부족 ({missing_names})")

        event_bus.publish(Events.SKILL_CAST_START, {"skill": skill, "user": user, "target": target})

        # 데드아이 특수 처리: 모든 탄환만큼 반복 실행
        if (hasattr(user, "gimmick_type") and user.gimmick_type == "magazine_system"
            and skill.metadata.get("uses_all_bullets", False)):
            try:
                from src.character.gimmick_updater import GimmickUpdater

                # 현재 탄창에 있는 탄환 개수 확인
                bullet_count = len(getattr(user, 'magazine', []))

                if bullet_count == 0:
                    return SkillResult(success=False, message="탄창이 비어있습니다!")

                # 각 탄환마다 스킬 실행
                total_damage = 0
                total_brv_damage = 0
                messages = []

                for i in range(bullet_count):
                    single_result = skill.execute(user, target, context)
                    if single_result.success:
                        total_damage += getattr(single_result, 'damage', 0)
                        total_brv_damage += getattr(single_result, 'brv_damage', 0)
                        if hasattr(single_result, 'message') and single_result.message:
                            messages.append(single_result.message)

                # 모든 탄환 소비
                bullets_consumed = GimmickUpdater._consume_bullet(user, skill)

                # 결과 통합
                result = SkillResult(
                    success=True,
                    damage=total_damage,
                    brv_damage=total_brv_damage,
                    message=f"데드아이 {bullets_consumed}발 발사!"
                )

            except Exception as exc:
                self.logger.warning(f"[데드아이] 실행 실패: {exc}")
                result = skill.execute(user, target, context)
        else:
            # 일반 스킬 실행
            result = skill.execute(user, target, context)

            # 저격수 탄환 소모: 실행 성공 후 처리하여 마지막 탄환도 정상 발사되도록 함
            if result.success and hasattr(user, "gimmick_type") and user.gimmick_type == "magazine_system":
                try:
                    from src.character.gimmick_updater import GimmickUpdater
                    GimmickUpdater._consume_bullet(user, skill)
                except Exception as exc:
                    self.logger.warning(f"[탄환] 소모 처리 실패: {exc}")

        # 해커 RAM 소모 처리
        if result.success and getattr(user, "gimmick_type", None) == "intrusion_system":
            if hasattr(user, "ram"):
                total_ram_use = 0
                if ram_cost:
                    total_ram_use += ram_cost
                if ram_burn > 0:
                    total_ram_use += ram_burn
                
                if total_ram_use > 0:
                    old_ram = user.ram
                    user.ram = max(0, user.ram - total_ram_use)
                    self.logger.info(f"[RAM] {user.name}: {skill.name} 사용으로 RAM {total_ram_use} 소모 ({old_ram} -> {user.ram})")
                else:
                    self.logger.debug(f"[RAM] {user.name}: {skill.name} 사용 (소모량 0)")

        # === 해적 보물 시스템 처리 ===
        if result.success and hasattr(skill, 'metadata') and skill.metadata:
            # 보물 획득 스킬 (플런더)
            if skill.metadata.get('treasure_skill') and skill.metadata.get('treasure_steal_chance'):
                import random
                from src.character.skills.job_skills.pirate_skills import TREASURE_TYPES
                steal_chance = skill.metadata.get('treasure_steal_chance', 0.8)
                if random.random() < steal_chance:
                    # 보물 획득 성공
                    if not hasattr(user, 'treasure_inventory'):
                        user.treasure_inventory = []
                    
                    max_treasure = getattr(user, 'max_treasure', 3)
                    if len(user.treasure_inventory) < max_treasure:
                        # 가중치 기반 랜덤 보물 선택
                        treasure_ids = list(TREASURE_TYPES.keys())
                        weights = [TREASURE_TYPES[tid]["weight"] for tid in treasure_ids]
                        selected_treasure_id = random.choices(treasure_ids, weights=weights, k=1)[0]
                        
                        user.treasure_inventory.append(selected_treasure_id)
                        treasure_name = TREASURE_TYPES[selected_treasure_id]["name"]
                        
                        self.logger.info(f"[해적] {user.name}이(가) {treasure_name}을(를) 획득했다! (총: {len(user.treasure_inventory)}개)")
                        result.message += f" ({treasure_name} 획득! {len(user.treasure_inventory)}/{max_treasure})"
                else:
                    self.logger.debug(f"[해적] {user.name}의 보물 획득 실패")

            # 보물 소비 스킬 (보물 사용, 보물 폭탄)
            if skill.metadata.get('consume_all_treasure'):
                # 모든 보물 소비
                if hasattr(user, 'treasure_inventory') and len(user.treasure_inventory) > 0:
                    consumed = len(user.treasure_inventory)
                    user.treasure_inventory.clear()
                    self.logger.info(f"[해적] {user.name}이(가) {consumed}개의 보물을 소비했다!")
                    result.message += f" (보물 {consumed}개 소비)"

        # 쿨다운 설정 비활성화 (사용자 요청)
        # if result.success and skill.cooldown > 0:
        #     self.logger.debug(f"[CD_SET] {skill.name} 쿨다운 설정: {skill.cooldown}턴")
        #     self.set_cooldown(user, skill_id, skill.cooldown)
        # else:
        #     self.logger.debug(f"[CD_SKIP] {skill.name} 쿨다운 설정 안 함 (success={result.success}, cooldown={skill.cooldown})")

        # 메타데이터 기반 소모 처리 (성공 시)
        if result.success and meta:
            # 침투 소모
            if meta.get("consumes_intrusion") and target is not None and hasattr(target, "intrusion_gauge"):
                from src.character.gimmick_updater import GimmickUpdater
                GimmickUpdater.reset_intrusion(target)
            # 독 중첩 소모
            if meta.get("venom_consume_all") and target is not None and hasattr(target, "venom_stacks"):
                from src.character.gimmick_updater import GimmickUpdater
                GimmickUpdater.reset_venom(target)
            # 정령 소모
            if meta.get("consumes_all_spirits") and getattr(user, "gimmick_type", None) == "elemental_spirits":
                from src.character.gimmick_updater import GimmickUpdater
                GimmickUpdater.release_all_spirits(user)

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
            if isinstance(skill.sfx, tuple):
                category, sfx_name = skill.sfx
                play_sfx(category, sfx_name)
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
