"""Damage Effect"""
from enum import Enum
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.combat.brave_system import get_brave_system
from src.combat.damage_calculator import get_damage_calculator
from src.core.event_bus import event_bus, Events

class DamageType(Enum):
    BRV = "brv"
    HP = "hp"
    BRV_HP = "brv_hp"
    HEAL = "heal"
    HEAL_MP = "heal_mp"

class DamageEffect(SkillEffect):
    """데미지 효과"""
    def __init__(self, damage_type=DamageType.BRV, multiplier=1.0, gimmick_bonus=None, hp_scaling=False, stat_type="physical", conditional_bonus=None, element=None):
        super().__init__(EffectType.DAMAGE)
        self.damage_type = damage_type
        self.multiplier = multiplier
        self.gimmick_bonus = gimmick_bonus or {}
        self.conditional_bonus = conditional_bonus or {}  # 조건부 보너스 (예: 은신 시 추가 피해)
        self.hp_scaling = hp_scaling
        self.stat_type = stat_type  # "physical" 또는 "magical"
        self.element = element  # 속성 (fire, ice, lightning, water, earth, wind, holy, dark)
        self.brave_system = get_brave_system()
        self.damage_calculator = get_damage_calculator()
    
    def can_execute(self, user, target, context) -> bool:
        if self.damage_type == DamageType.HP:
            return user.current_brv > 0
        return True
    
    def execute(self, user, target, context) -> EffectResult:
        """데미지 실행 - 단일/다중 타겟 처리"""
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)
        
        # 타겟 리스트 처리
        targets = target if isinstance(target, list) else [target]
        # 전체 타겟 수를 컨텍스트에 전달 (관중 요구 등에서 사용)
        if context is None:
            context = {}
        else:
            context = dict(context)
        context.setdefault('targets_count', len(targets))
        
        # 다단히트 체크 (스킬 메타데이터에서)
        multi_hit_count = 1
        if context and 'skill' in context:
            skill = context['skill']
            if hasattr(skill, 'metadata') and skill.metadata:
                multi_hit = skill.metadata.get('multi_hit')
                if multi_hit:
                    if isinstance(multi_hit, bool):
                        # True인 경우, 환영 카운트나 다른 기믹 값 기반
                        # 기본 2히트, 환영이 있으면 추가
                        phantom_count = getattr(user, 'phantom_count', 0)
                        multi_hit_count = 2 + phantom_count  # 기본 2 + 환영 수
                    elif isinstance(multi_hit, int):
                        multi_hit_count = multi_hit
        
        # 검성: 검기 스택 기반 추가 공격 처리
        sword_aura_hits = []
        if context and 'skill' in context:
            skill = context['skill']
            if hasattr(skill, 'metadata') and skill.metadata:
                # sword_aura_bonus_hits: 검기 스택에 따른 추가 공격 (고정 계수)
                sword_aura_bonus = skill.metadata.get('sword_aura_bonus_hits')
                if sword_aura_bonus:
                    sword_aura = getattr(user, 'sword_aura', 0)
                    if sword_aura > 0:
                        bonus_multiplier = sword_aura_bonus.get('multiplier', 0.075)
                        # 각 검기마다 고정 계수로 추가 공격
                        for _ in range(sword_aura):
                            sword_aura_hits.append(bonus_multiplier)
        
        # HP 공격이 여러 타겟에 적용되는 경우, 시작 시점의 BRV를 저장
        # (첫 번째 타겟에서만 BRV를 소모하고, 나머지 타겟들에는 초기 BRV로 복원)
        is_aoe_hp = (self.damage_type == DamageType.HP and len(targets) > 1)
        initial_brv = None
        if is_aoe_hp:
            initial_brv = user.current_brv
            # context에 저장하여 _execute_single에서 사용
            if context is None:
                context = {}
            context['_aoe_hp_initial_brv'] = initial_brv
            context['_aoe_hp_target_index'] = 0  # 첫 번째 타겟 추적
        
        # 실제로 처리된 살아있는 타겟 추적
        alive_targets_processed = 0
        
        for i, single_target in enumerate(targets):
            if single_target is None or not single_target.is_alive:
                continue
            
            # AOE HP 공격의 경우, 첫 번째 타겟이 아닌 경우 BRV를 초기값으로 복원
            # (첫 번째 타겟에서 BRV가 소모되므로, 나머지 타겟들에는 초기 BRV를 사용)
            if is_aoe_hp and initial_brv is not None and alive_targets_processed > 0:
                user.current_brv = initial_brv
            
            # 타겟 인덱스 업데이트
            if is_aoe_hp:
                context['_aoe_hp_target_index'] = alive_targets_processed
            
            # 검성: 검기 스택에 따른 선행 BRV 공격 (검기가 먼저 피해를 입힘)
            if sword_aura_hits and single_target.is_alive:
                import random
                
                # 원래 배율과 데미지 타입을 저장
                original_multiplier = self.multiplier
                original_damage_type = self.damage_type
                
                for hit_idx, bonus_mult in enumerate(sword_aura_hits):
                    if not single_target.is_alive:
                        break
                    
                    # 검기는 항상 BRV 공격 (고정 계수)
                    self.multiplier = bonus_mult
                    self.damage_type = DamageType.BRV
                    context['_sword_aura_hit'] = hit_idx + 1
                    context['_sword_aura_total'] = len(sword_aura_hits)
                    # SFX 정보를 context에 추가 (hit_queue에서 딜레이 적용하여 재생)
                    context['_sfx'] = ("combat", "sword4", random.uniform(1.3, 1.5))
                    
                    bonus_result = self._execute_single(user, single_target, context)
                    result.merge(bonus_result)
                
                # 원래 배율과 데미지 타입 복원
                self.multiplier = original_multiplier
                self.damage_type = original_damage_type
                
                # 컨텍스트 정리
                context.pop('_sword_aura_hit', None)
                context.pop('_sword_aura_total', None)
            
            # 다단히트 실행 (메인 공격)
            for hit_num in range(multi_hit_count):
                # 다단히트 정보를 context에 추가
                if context is None:
                    context = {}
                context['_multi_hit_current'] = hit_num + 1
                context['_multi_hit_total'] = multi_hit_count
                
                single_result = self._execute_single(user, single_target, context)
                result.merge(single_result)
                
                # 타겟이 죽었으면 다음 히트 중단
                if not single_target.is_alive:
                    break
            
            # 살아있는 타겟이 처리되었음을 기록
            alive_targets_processed += 1
        
        # AOE HP 공격의 경우, 살아있는 타겟이 실제로 처리된 경우에만 BRV를 소모
        if is_aoe_hp and initial_brv is not None and alive_targets_processed > 0:
            # 첫 번째 타겟에서 이미 BRV가 소모되었으므로, BRV를 0으로 설정
            user.current_brv = 0
        
        # 검성: 검기 스택 소모는 StackCost를 통해서만 이루어짐
        # (sword_aura_bonus_hits는 현재 검기 수만큼 추가타를 발동하지만, 소모하지 않음)
        
        return result
    
    def _execute_single(self, user, target, context):
        """단일 타겟 데미지"""
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)
        
        # ========================================
        # 일반 보호 효과 (ProtectEffect)
        # ========================================
        if context and not context.get('_protect_in_progress'):
            if hasattr(target, 'protected_by') and target.protected_by:
                # 활성 보호자 찾기
                active_protection = None
                for info in target.protected_by:
                    protector = info['protector']
                    # 보호자가 살아있고, 자신이 자신을 보호하는 경우가 아닌지 확인
                    if getattr(protector, 'is_alive', False) and protector != target:
                        active_protection = info
                        break
                
                if active_protection:
                    protector = active_protection['protector']
                    reduction = active_protection.get('damage_reduction', 0.0)
                    
                    # 타겟을 보호자로 변경
                    protect_context = context.copy() if context else {}
                    protect_context['_protect_in_progress'] = True
                    
                    # 데미지 감소 적용 (배율 오버라이드 계산)
                    if reduction > 0:
                        current_override = protect_context.get('damage_multiplier_override', 1.0)
                        protect_context['damage_multiplier_override'] = current_override * (1.0 - reduction)
                    
                    # 보호자가 대신 피해를 받음
                    protect_result = self._execute_single(user, protector, protect_context)
                    
                    # 메시지 보강
                    protect_msg = f"{protector.name}이(가) {target.name}을(를) 보호!"
                    if reduction > 0:
                        protect_msg += f" (피해 {int(reduction*100)}% 감소)"
                    
                    protect_result.message = protect_msg + " " + (protect_result.message or "")
                    return protect_result

        # ========================================
        # 나이트 (J) - 아군 보호 효과
        # 적이 아군을 공격할 때, protect_ally 효과가 있는 다른 아군이 대신 피해를 받음
        # ========================================
        if context and not context.get('_protect_in_progress'):
            # all_enemies = 공격자(user)의 적 = 피해자(target)의 아군
            target_allies = context.get('all_enemies', [])
            
            # target이 target_allies에 있는지 확인 (아군이 공격받는 경우)
            if target in target_allies:
                for ally in target_allies:
                    if ally == target:
                        continue  # 피해자 자신은 스킵
                    if not getattr(ally, 'is_alive', False):
                        continue  # 죽은 캐릭터는 스킵
                    
                    ally_card_effects = getattr(ally, 'card_effects', {})
                    if ally_card_effects.get('protect_ally'):
                        # 보호 효과 발동!
                        ally_card_effects.pop('protect_ally')  # 1회용, 소모
                        
                        # 타겟을 보호자로 변경
                        protect_context = context.copy() if context else {}
                        protect_context['_protect_in_progress'] = True  # 재귀 방지
                        
                        # 보호자가 대신 피해를 받음
                        protect_result = self._execute_single(user, ally, protect_context)
                        protect_result.message = f"[나이트] {ally.name}이(가) {target.name} 대신 피해를 받음! " + (protect_result.message or "")
                        return protect_result
        
        # 트리플 히트 (3) - 3연타 처리
        card_effects = getattr(user, 'card_effects', {})
        triple_hit = card_effects.get("triple_hit")
        if triple_hit and not (context and context.get('_triple_hit_in_progress')):
            # 3연타 시작
            hits = triple_hit.get("hits", 3)
            hit_mult = triple_hit.get("damage_mult", 0.4)
            card_effects.pop("triple_hit")  # 효과 소모
            
            total_brv = 0
            total_hp = 0
            for i in range(hits):
                # 재귀 방지 플래그
                hit_context = context.copy() if context else {}
                hit_context['_triple_hit_in_progress'] = True
                hit_context['_triple_hit_mult'] = hit_mult
                
                hit_result = self._execute_single(user, target, hit_context)
                total_brv += getattr(hit_result, 'brv_damage', 0) or 0
                total_hp += getattr(hit_result, 'hp_damage', 0) or 0
            
            result.brv_damage = total_brv
            result.hp_damage = total_hp
            result.message = f"3연타! BRV:{total_brv} HP:{total_hp}"
            return result

        # 최종 배율 계산
        final_mult = self.multiplier

        # 스킬 메타데이터 기반 배율 (예: 은신 배수)
        skill = context.get("skill") if context else None
        skill_meta = getattr(skill, "metadata", {}) if skill else {}
        if skill_meta.get("stealth_multiplier") and getattr(user, "stealth_active", False):
            try:
                final_mult *= float(skill_meta.get("stealth_multiplier", 1.0))
            except (TypeError, ValueError):
                pass

        # 가능성 시스템 배율 적용 (power_multiplier)
        if context and 'power_multiplier' in context:
            final_mult *= context['power_multiplier']
        
        # 트리플 히트 배율 적용
        if context and context.get('_triple_hit_mult'):
            final_mult *= context['_triple_hit_mult']

        # 데미지 배율 오버라이드 (보호 효과 등에서 사용)
        if context and 'damage_multiplier_override' in context:
            final_mult *= context['damage_multiplier_override']

        # 기믹 보너스
        if self.gimmick_bonus:
            field = self.gimmick_bonus.get('field')
            bonus_mult = self.gimmick_bonus.get('multiplier', 0)
            if field:
                stacks = 0
                
                # 스냅샷 컨텍스트가 있으면 스냅샷된 값 사용 (캐스팅 스킬용)
                snapshot_context = context.get('snapshot_context') if context else None
                if snapshot_context and field in snapshot_context:
                    stacks = snapshot_context[field]
                else:
                    # 스냅샷이 없으면 현재 값 사용 (즉시 실행 스킬)
                    # 계산된 필드 처리 (character에 직접 필드가 없는 경우)
                    if field == "total_runes":
                        # 배틀메이지: 모든 룬 타입 합산
                        if hasattr(user, 'gimmick_type') and user.gimmick_type == "rune_resonance":
                            stacks = (
                                getattr(user, 'rune_fire', 0) +
                                getattr(user, 'rune_ice', 0) +
                                getattr(user, 'rune_lightning', 0) +
                                getattr(user, 'rune_earth', 0) +
                                getattr(user, 'rune_arcane', 0)
                            )
                    elif field == "total_undead":
                        # 네크로맨서: 모든 언데드 타입 합산
                        if hasattr(user, 'gimmick_type') and user.gimmick_type == "undead_legion":
                            stacks = (
                                getattr(user, 'undead_skeleton', 0) +
                                getattr(user, 'undead_zombie', 0) +
                                getattr(user, 'undead_ghost', 0)
                            )
                    elif field == "total_programs":
                        # 해커: 모든 프로그램 타입 합산
                        if hasattr(user, 'gimmick_type') and user.gimmick_type == "program_execution":
                            stacks = (
                                getattr(user, 'program_virus', 0) +
                                getattr(user, 'program_backdoor', 0) +
                                getattr(user, 'program_ddos', 0) +
                                getattr(user, 'program_ransomware', 0) +
                                getattr(user, 'program_spyware', 0)
                            )
                    elif hasattr(user, field):
                        # 일반 필드 (기존 로직)
                        stacks = getattr(user, field, 0)
                
                # count_mode: 리스트의 길이를 사용 (possibility_slots 등)
                count_mode = self.gimmick_bonus.get('count_mode', False)
                if count_mode and isinstance(stacks, list):
                    stacks = len(stacks)
                
                if stacks > 0:
                    final_mult += stacks * bonus_mult

        # 조건부 보너스 (ISSUE-005 수정)
        if self.conditional_bonus:
            condition = self.conditional_bonus.get('condition')
            bonus_mult = self.conditional_bonus.get('multiplier', 1.0)

            # 조건 체크
            condition_met = False
            if condition == "danger_zone":
                # 위험 구간 (열 >= 80)
                condition_met = getattr(user, 'heat', 0) >= 80
            elif condition == "optimal_zone":
                # 최적 구간 (열 50-79)
                heat = getattr(user, 'heat', 0)
                condition_met = 50 <= heat < 80
            elif condition == "at_present":
                # 현재 타임라인 (타임라인 == 0)
                condition_met = getattr(user, 'timeline', 0) == 0
            elif condition == "stealth" or condition == "stealth_active":
                # 은신 중
                condition_met = getattr(user, 'stealth_active', False)
            elif condition == "madness_high":
                # 광기 높음 (70+)
                condition_met = getattr(user, 'madness', 0) >= 70
            elif condition == "in_berserker_mode":
                # 버서커 모드 (광기 >= 40)
                condition_met = getattr(user, 'madness', 0) >= 40
            elif condition == "in_yin_state":
                # 몽크 음 상태 (기 게이지 <= 30)
                ki = getattr(user, 'ki_gauge', 50)
                condition_met = ki <= 30
            elif condition == "in_yang_state":
                # 몽크 양 상태 (기 게이지 >= 70)
                ki = getattr(user, 'ki_gauge', 50)
                condition_met = ki >= 70
            elif condition == "hp_below_30":
                # HP 30% 이하
                current_hp = getattr(user, 'current_hp', 0)
                max_hp = getattr(user, 'max_hp', 1)
                condition_met = (current_hp / max_hp) <= 0.30 if max_hp > 0 else False
            elif condition == "hp_below_50":
                # HP 50% 이하
                current_hp = getattr(user, 'current_hp', 0)
                max_hp = getattr(user, 'max_hp', 1)
                condition_met = (current_hp / max_hp) <= 0.50 if max_hp > 0 else False
            elif condition == "last_bullet":
                # 저격수 마지막 탄환 (탄창이 1개 남았을 때)
                magazine = getattr(user, 'magazine', [])
                condition_met = len(magazine) == 1

            if condition_met:
                final_mult *= bonus_mult

        # HP 스케일링
        if self.hp_scaling:
            hp_percent = user.current_hp / user.max_hp
            if hp_percent < 0.3:
                final_mult *= 2.0
            elif hp_percent < 0.5:
                final_mult *= 1.5
        
        # ========================================
        # 마술사 카드 효과 적용
        # ========================================
        card_effects = getattr(user, 'card_effects', {})
        self_damage_ratio = 0  # 자해 피해 비율
        
        # 듀얼리티 (2) - 피해 2배, 자해 50%
        if "double_edge" in card_effects:
            double_edge = card_effects["double_edge"]
            final_mult *= double_edge.get("damage_mult", 2.0)
            self_damage_ratio = double_edge.get("self_damage", 0.5)
        
        # 극한 (9) - 스킬 효과 +50%
        skill_power_up = card_effects.get("skill_power_up", 0)
        if skill_power_up > 0:
            final_mult *= (1 + skill_power_up)
        
        # 방어 관통 (스페이드) - defense_pierce_fixed로 변환하여 전달
        armor_pierce = card_effects.get("armor_pierce", 0)
        if armor_pierce > 0:
            if context is None:
                context = {}
            # 방어 관통 비율 (기존 defense_pierce_fixed 로직 활용)
            context['defense_pierce_fixed'] = armor_pierce
        
        # 행운 (7) - 크리티컬 확정
        if card_effects.get("lucky_drop"):
            if context is None:
                context = {}
            context['force_critical'] = True
        
        # 최종 속성 결정: 4인 해인 전속성(context 플래그) > 이펙트 자체 속성 (t_83d83e83)
        if context and context.get('_burst_all_elements'):
            effective_element = "all"
        else:
            effective_element = self.element

        if self.damage_type == DamageType.BRV:
            # 물리/마법 구분
            # 탄환 정보를 kwargs에 전달 (관통탄 방어 관통력용)
            calc_kwargs = {}
            if context and 'defense_pierce_fixed' in context:
                calc_kwargs['defense_pierce_fixed'] = context['defense_pierce_fixed']
            if context and context.get('force_critical'):
                calc_kwargs['force_critical'] = True
            
            if self.stat_type in ("magical", "hybrid"):
                # 원소 속성 전달 (적 저항/약점 적용)
                dmg_result = self.damage_calculator.calculate_magic_damage(user, target, final_mult, element=effective_element, **calc_kwargs)
            else:
                dmg_result = self.damage_calculator.calculate_brv_damage(user, target, final_mult, **calc_kwargs)

            brv_result = self.brave_system.brv_attack(user, target, dmg_result.final_damage)
            result.brv_damage = brv_result['brv_stolen']
            result.brv_gained = brv_result['actual_gain']
            result.brv_broken = brv_result['is_break']
            result.critical = dmg_result.is_critical
            result.message = f"BRV 공격! {result.brv_damage}"
        
        elif self.damage_type == DamageType.HP:
            # current_hp 기반 고정 HP 소모 (영혼 전환 등)
            if self.stat_type == "current_hp":
                hp_cost = int(target.current_hp * final_mult)
                hp_cost = max(1, hp_cost)
                # 최소 1 HP 유지
                hp_cost = min(hp_cost, target.current_hp - 1) if target.current_hp > 1 else 0
                if hp_cost > 0:
                    target.current_hp = max(1, target.current_hp - hp_cost)
                result.hp_damage = hp_cost
                result.damage_dealt = hp_cost
                result.message = f"HP 소모! {hp_cost}"
                if context is not None:
                    context['last_damage'] = hp_cost
            else:
                # 물리/마법 구분하여 HP 공격
                # 탄환 정보를 전달 (관통탄 방어 관통력용)
                hp_kwargs = {}
                if context and 'defense_pierce_fixed' in context:
                    hp_kwargs['defense_pierce_fixed'] = context['defense_pierce_fixed']

                # AOE HP 공격의 경우, 첫 번째 타겟에서만 실제로 BRV를 소모
                # 나머지 타겟들에는 초기 BRV를 사용하되, 실제 소모는 하지 않음
                is_aoe_hp = context and '_aoe_hp_initial_brv' in context
                target_index = context.get('_aoe_hp_target_index', 0) if context else 0
                is_first_target = (is_aoe_hp and target_index == 0)

                # 첫 번째 타겟이 아닌 경우, BRV를 임시로 초기값으로 설정 (데미지 계산용)
                # 하지만 실제 소모는 하지 않음 (hp_attack 후 복원)
                saved_brv = None
                if is_aoe_hp and not is_first_target:
                    saved_brv = user.current_brv
                    user.current_brv = context['_aoe_hp_initial_brv']

                hp_damage_type = "magical" if self.stat_type in ("magical", "hybrid") else self.stat_type
                hp_result = self.brave_system.hp_attack(user, target, final_mult, damage_type=hp_damage_type, **hp_kwargs)

                # 첫 번째 타겟이 아닌 경우, BRV를 복원 (실제로 소모하지 않음)
                # 첫 번째 타겟에서는 BRV가 0이 되어야 하므로 그대로 둠
                if is_aoe_hp and not is_first_target and saved_brv is not None:
                    # BRV를 복원 (실제로 소모하지 않았으므로 초기값 유지)
                    user.current_brv = context['_aoe_hp_initial_brv']

                result.hp_damage = hp_result['hp_damage']
                result.damage_dealt = hp_result['hp_damage']
                result.message = f"HP 공격! {result.hp_damage}"
                if context is not None:
                    context['last_damage'] = result.hp_damage
        
        elif self.damage_type == DamageType.BRV_HP:
            # 물리/마법 구분 (hybrid는 magical로 처리)
            if self.stat_type in ("magical", "hybrid"):
                # 원소 속성 전달 (적 저항/약점 적용)
                dmg_result = self.damage_calculator.calculate_magic_damage(user, target, final_mult, element=effective_element)
            else:
                dmg_result = self.damage_calculator.calculate_brv_damage(user, target, final_mult)

            brv_result = self.brave_system.brv_attack(user, target, dmg_result.final_damage)
            result.brv_damage = brv_result['brv_stolen']
            result.brv_gained = brv_result['actual_gain']
            result.brv_broken = brv_result['is_break']
            # HP 공격: BRV에 이미 final_mult가 적용되었으므로 HP에는 1.0 사용 (이중 적용 방지)
            hp_damage_type = "magical" if self.stat_type in ("magical", "hybrid") else self.stat_type
            hp_result = self.brave_system.hp_attack(user, target, 1.0, damage_type=hp_damage_type)
            result.hp_damage = hp_result['hp_damage']
            result.damage_dealt = hp_result['hp_damage']
            result.message = f"BRV+HP 공격! BRV:{result.brv_damage} HP:{result.hp_damage}"
            if context is not None:
                context['last_damage'] = result.hp_damage
        
        # ========================================
        # 자해 피해 적용 (듀얼리티 등) - HP 피해에만 적용, BRV는 제외
        # ========================================
        if self_damage_ratio > 0 and hasattr(result, 'hp_damage') and result.hp_damage:
            self_damage = int(result.hp_damage * self_damage_ratio)
            if self_damage > 0:
                user.current_hp = max(1, user.current_hp - self_damage)  # 최소 1 HP 유지
                result.message += f" (자해 {self_damage})"
        
        # ========================================
        # 흡혈 효과 적용 (하트)
        # ========================================
        lifesteal = card_effects.get("lifesteal", 0)
        if lifesteal > 0 and hasattr(result, 'hp_damage') and result.hp_damage:
            heal_amount = int(result.hp_damage * lifesteal)
            if heal_amount > 0:
                user.current_hp = min(user.max_hp, user.current_hp + heal_amount)
                result.message += f" (흡혈 +{heal_amount})"
        
        # ========================================
        # 독 효과 적용 (클럽)
        # ========================================
        poison_attack = card_effects.get("poison_attack")
        if poison_attack and target and hasattr(target, 'status_manager'):
            try:
                from src.character.status_effect import StatusEffect, StatusType
                poison_duration = poison_attack.get("duration", 3)
                poison_damage = poison_attack.get("damage_percent", 0.05)
                poison_effect = StatusEffect(
                    StatusType.POISON,
                    duration=poison_duration,
                    damage_per_turn=int(target.max_hp * poison_damage)
                )
                target.status_manager.add_effect(poison_effect)
                result.message += f" (독 {poison_duration}턴)"
            except Exception:
                pass
        
        # ========================================
        # 저주 효과 적용 (6)
        # ========================================
        curse_target = card_effects.get("curse_target")
        if curse_target and target and hasattr(target, 'status_manager'):
            try:
                from src.character.status_effect import StatusEffect, StatusType
                curse_duration = curse_target.get("duration", 3)
                curse_effect = StatusEffect(
                    StatusType.CURSE,
                    duration=curse_duration
                )
                target.status_manager.add_effect(curse_effect)
                result.message += f" (저주 {curse_duration}턴)"
            except Exception:
                pass
        
        # ========================================
        # 매스 스턴 적용 (K) - 적 전체 기절
        # ========================================
        mass_stun = card_effects.get("mass_stun")
        if mass_stun and context:
            enemies = context.get('all_enemies', [])
            if enemies:
                try:
                    from src.character.status_effect import StatusEffect, StatusType
                    stun_duration = mass_stun.get("duration", 1)
                    stunned_count = 0
                    for enemy in enemies:
                        if hasattr(enemy, 'status_manager') and getattr(enemy, 'is_alive', False):
                            stun_effect = StatusEffect(StatusType.STUN, duration=stun_duration)
                            enemy.status_manager.add_effect(stun_effect)
                            stunned_count += 1
                    if stunned_count > 0:
                        result.message += f" (전체 기절 {stunned_count}체)"
                except Exception:
                    pass
        
        # ========================================
        # 파티 힐 적용 (Q) - 아군 전체 회복
        # ========================================
        party_heal = card_effects.get("party_heal", 0)
        if party_heal > 0 and context:
            allies = context.get('all_allies', [])
            if allies:
                healed_total = 0
                for ally in allies:
                    if hasattr(ally, 'current_hp') and getattr(ally, 'is_alive', False):
                        heal_amount = int(ally.max_hp * party_heal)
                        ally.current_hp = min(ally.max_hp, ally.current_hp + heal_amount)
                        healed_total += heal_amount
                if healed_total > 0:
                    result.message += f" (아군 회복 +{healed_total})"
        
        # ========================================
        # 버프→디버프 전환 (5)
        # ========================================
        if card_effects.get("reverse_buff") and target:
            if hasattr(target, 'active_buffs') and target.active_buffs:
                # 버프 하나를 디버프로 전환
                buff_keys = list(target.active_buffs.keys())
                if buff_keys:
                    removed_buff = buff_keys[0]
                    target.active_buffs.pop(removed_buff)
                    if hasattr(target, 'active_debuffs'):
                        target.active_debuffs[removed_buff] = {"value": 0.2, "duration": 2}
                    result.message += f" ({removed_buff} 전환)"
        
        # ========================================
        # 카드 효과 소모 (1회용)
        # ========================================
        if card_effects:
            # 1회용 효과들 제거
            for key in ["double_edge", "triple_hit", "first_strike", "armor_pierce", 
                        "lifesteal", "poison_attack", "bonus_rewards", "mass_stun",
                        "curse_target", "party_heal", "reverse_buff", "skill_power_up",
                        "lucky_drop", "free_cast", "protect_ally"]:
                card_effects.pop(key, None)
        
        # ========================================
        # 굴절량 기반 고정 피해 (차원술사)
        # ========================================
        skill = context.get("skill") if context else None
        skill_meta = getattr(skill, "metadata", {}) if skill else {}
        refraction_fixed_rate = skill_meta.get("refraction_fixed_damage_rate", 0)

        if refraction_fixed_rate > 0 and hasattr(user, 'gimmick_type') and user.gimmick_type == "dimension_refraction":
            refraction_stacks = getattr(user, 'refraction_stacks', 0)
            if refraction_stacks > 0:
                # 고정 피해 계산 (굴절량 × 비율)
                fixed_damage = int(refraction_stacks * refraction_fixed_rate)

                # 고정 피해 증폭 특성 확인 (차원술사)
                if hasattr(user, 'active_traits'):
                    has_amplification = any(
                        (t if isinstance(t, str) else t.get('id')) == 'fixed_damage_amplification'
                        for t in user.active_traits
                    )
                    if has_amplification:
                        fixed_damage = int(fixed_damage * 1.5)  # 고정 피해 +50%
                        from src.core.logger import get_logger
                        logger = get_logger("damage")
                        logger.debug(f"[고정 피해 증폭] {user.name} 굴절 피해: {fixed_damage} (+50%)")

                if fixed_damage > 0:
                    # HP 고정 피해 적용
                    actual_damage = min(fixed_damage, target.current_hp)
                    target.current_hp = max(0, target.current_hp - fixed_damage)
                    # 사망 판정
                    if target.current_hp <= 0 and hasattr(target, 'is_alive'):
                        if not (hasattr(target, '_has_undying_existence') and target._has_undying_existence()):
                            target.is_alive = False

                    # 결과에 추가
                    if hasattr(result, 'hp_damage'):
                        result.hp_damage = getattr(result, 'hp_damage', 0) + actual_damage
                    else:
                        result.hp_damage = actual_damage

                    result.damage_dealt = getattr(result, 'damage_dealt', 0) + actual_damage

                    # 메시지 업데이트
                    if result.message:
                        result.message += f" + 굴절 피해 {actual_damage}"
                    else:
                        result.message = f"굴절 피해 {actual_damage}"

                    from src.core.logger import get_logger
                    logger = get_logger("damage")
                    logger.debug(f"[굴절 고정 피해] {user.name} → {target.name}: {actual_damage} (굴절량 {refraction_stacks} × {refraction_fixed_rate})")

        # ========================================
        # 히트 이벤트 발행 (다단히트 타격감용)
        # ========================================
        # 스킬 객체 참조 (이펙트 다양화용)
        _skill = context.get('skill') if context else None
        _skill_meta = getattr(_skill, 'metadata', None) or {} if _skill else {}

        hit_info = {
            'attacker': user,
            'target': target,
            'damage_type': self.damage_type.value,
            'brv_damage': getattr(result, 'brv_damage', 0),
            'hp_damage': getattr(result, 'hp_damage', 0),
            'is_critical': getattr(result, 'critical', False),
            'is_break': getattr(result, 'brv_broken', False),
            'sword_aura_hit': context.get('_sword_aura_hit') if context else None,
            'multi_hit_current': context.get('_multi_hit_current') if context else None,
            'sfx': context.get('_sfx') if context else None,
            'element': self.element,
            'targets_hit': context.get('targets_count', 1) if context else 1,
            'hp_percent_of_target': (getattr(result, 'hp_damage', 0) / target.max_hp * 100) if getattr(result, 'hp_damage', 0) and hasattr(target, 'max_hp') and target.max_hp > 0 else 0,
            # ── 이펙트 다양화를 위한 추가 필드 ──
            'stat_type': self.stat_type,  # "physical" / "magical"
            'skill_id': getattr(_skill, 'skill_id', None),
            'is_ultimate': getattr(_skill, 'is_ultimate', False) or _skill_meta.get('ultimate', False),
            'is_basic_attack': _skill_meta.get('basic_attack', False),
            'skill_special': _skill_meta.get('special'),  # 직업 고유 특수 효과 태그
            'gimmick_type': getattr(user, 'gimmick_type', None),  # 공격자의 기믹 타입
            'multi_hit_total': context.get('_multi_hit_total') if context else None,
            'multiplier': self.multiplier,  # 스킬 배율 (이펙트 스케일링용)
        }
        event_bus.publish(Events.COMBAT_HIT, hit_info)

        return result
