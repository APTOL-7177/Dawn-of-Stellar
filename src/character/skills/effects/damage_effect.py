"""Damage Effect"""
from enum import Enum
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.combat.brave_system import get_brave_system
from src.combat.damage_calculator import get_damage_calculator

class DamageType(Enum):
    BRV = "brv"
    HP = "hp"
    BRV_HP = "brv_hp"

class DamageEffect(SkillEffect):
    """데미지 효과"""
    def __init__(self, damage_type=DamageType.BRV, multiplier=1.0, gimmick_bonus=None, hp_scaling=False, stat_type="physical", conditional_bonus=None):
        super().__init__(EffectType.DAMAGE)
        self.damage_type = damage_type
        self.multiplier = multiplier
        self.gimmick_bonus = gimmick_bonus or {}
        self.conditional_bonus = conditional_bonus or {}  # 조건부 보너스 (예: 은신 시 추가 피해)
        self.hp_scaling = hp_scaling
        self.stat_type = stat_type  # "physical" 또는 "magical"
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
            if not single_target.is_alive:
                continue
            
            # AOE HP 공격의 경우, 첫 번째 타겟이 아닌 경우 BRV를 초기값으로 복원
            # (첫 번째 타겟에서 BRV가 소모되므로, 나머지 타겟들에는 초기 BRV를 사용)
            if is_aoe_hp and initial_brv is not None and alive_targets_processed > 0:
                user.current_brv = initial_brv
            
            # 타겟 인덱스 업데이트
            if is_aoe_hp:
                context['_aoe_hp_target_index'] = alive_targets_processed
            
            single_result = self._execute_single(user, single_target, context)
            result.merge(single_result)
            
            # 살아있는 타겟이 처리되었음을 기록
            alive_targets_processed += 1
        
        # AOE HP 공격의 경우, 살아있는 타겟이 실제로 처리된 경우에만 BRV를 소모
        if is_aoe_hp and initial_brv is not None and alive_targets_processed > 0:
            # 첫 번째 타겟에서 이미 BRV가 소모되었으므로, BRV를 0으로 설정
            user.current_brv = 0
        
        return result
    
    def _execute_single(self, user, target, context):
        """단일 타겟 데미지"""
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)
        
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
        
        # 트리플 히트 배율 적용
        if context and context.get('_triple_hit_mult'):
            final_mult *= context['_triple_hit_mult']

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
        
        if self.damage_type == DamageType.BRV:
            # 물리/마법 구분
            # 탄환 정보를 kwargs에 전달 (관통탄 방어 관통력용)
            calc_kwargs = {}
            if context and 'defense_pierce_fixed' in context:
                calc_kwargs['defense_pierce_fixed'] = context['defense_pierce_fixed']
            if context and context.get('force_critical'):
                calc_kwargs['force_critical'] = True
            
            if self.stat_type == "magical":
                dmg_result = self.damage_calculator.calculate_magic_damage(user, target, final_mult, **calc_kwargs)
            else:
                dmg_result = self.damage_calculator.calculate_brv_damage(user, target, final_mult, **calc_kwargs)

            brv_result = self.brave_system.brv_attack(user, target, dmg_result.final_damage)
            result.brv_damage = brv_result['brv_stolen']
            result.brv_gained = brv_result['actual_gain']
            result.brv_broken = brv_result['is_break']
            result.critical = dmg_result.is_critical
            result.message = f"BRV 공격! {result.brv_damage}"
        
        elif self.damage_type == DamageType.HP:
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
            
            hp_result = self.brave_system.hp_attack(user, target, final_mult, damage_type=self.stat_type, **hp_kwargs)
            
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
            # 물리/마법 구분
            if self.stat_type == "magical":
                dmg_result = self.damage_calculator.calculate_magic_damage(user, target, final_mult)
            else:
                dmg_result = self.damage_calculator.calculate_brv_damage(user, target, final_mult)

            brv_result = self.brave_system.brv_attack(user, target, dmg_result.final_damage)
            result.brv_damage = brv_result['brv_stolen']
            result.brv_gained = brv_result['actual_gain']
            result.brv_broken = brv_result['is_break']
            # HP 공격도 물리/마법 구분 - final_mult 사용 (기믹 보너스 적용)
            hp_result = self.brave_system.hp_attack(user, target, final_mult, damage_type=self.stat_type)
            result.hp_damage = hp_result['hp_damage']
            result.damage_dealt = hp_result['hp_damage']
            result.message = f"BRV+HP 공격! BRV:{result.brv_damage} HP:{result.hp_damage}"
            if context is not None:
                context['last_damage'] = result.hp_damage
        
        # ========================================
        # 자해 피해 적용 (듀얼리티 등)
        # ========================================
        if self_damage_ratio > 0 and hasattr(result, 'hp_damage') and result.hp_damage:
            self_damage = int(result.hp_damage * self_damage_ratio)
            if self_damage > 0:
                user.current_hp = max(1, user.current_hp - self_damage)  # 최소 1 HP 유지
                result.message += f" (자해 {self_damage})"
        elif self_damage_ratio > 0 and hasattr(result, 'brv_damage') and result.brv_damage:
            # BRV 공격의 경우 BRV 데미지 기준 자해
            self_damage = int(result.brv_damage * self_damage_ratio)
            if self_damage > 0:
                user.current_hp = max(1, user.current_hp - self_damage)
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
        
        return result
