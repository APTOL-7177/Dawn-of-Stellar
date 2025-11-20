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
        # (첫 번째 타겟에서 BRV가 소모되어 이후 타겟들에 영향을 주지 않도록)
        is_aoe_hp = (self.damage_type == DamageType.HP and len(targets) > 1)
        initial_brv = None
        if is_aoe_hp:
            initial_brv = user.current_brv
            # context에 저장하여 _execute_single에서 사용
            if context is None:
                context = {}
            context['_aoe_hp_initial_brv'] = initial_brv
        
        for single_target in targets:
            if not single_target.is_alive:
                continue
            
            # HP 공격이 여러 타겟에 적용되는 경우, 각 타겟에 대해 BRV를 복원
            if is_aoe_hp and initial_brv is not None:
                user.current_brv = initial_brv
            
            single_result = self._execute_single(user, single_target, context)
            result.merge(single_result)
        
        # AOE HP 공격의 경우, 마지막에 한 번만 BRV 소모 (첫 번째 타겟에서 소모된 것과 동일)
        if is_aoe_hp and initial_brv is not None and len(targets) > 0:
            # BRV를 원래 소모량만큼만 감소 (첫 번째 타겟에서 이미 소모되었으므로)
            pass  # BRV는 각 타겟에 대해 복원되었으므로, 마지막 타겟에서 소모된 상태를 유지
        
        return result
    
    def _execute_single(self, user, target, context):
        """단일 타겟 데미지"""
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)

        # 최종 배율 계산
        final_mult = self.multiplier

        # 기믹 보너스
        if self.gimmick_bonus:
            field = self.gimmick_bonus.get('field')
            bonus_mult = self.gimmick_bonus.get('multiplier', 0)
            if field:
                stacks = 0
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
            elif condition == "stealth":
                # 은신 중
                condition_met = getattr(user, 'stealth_active', False)
            elif condition == "madness_high":
                # 광기 높음 (70+)
                condition_met = getattr(user, 'madness', 0) >= 70
            elif condition == "in_berserker_mode":
                # 버서커 모드 (광기 >= 40)
                condition_met = getattr(user, 'madness', 0) >= 40
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
            # 더 많은 조건을 여기에 추가 가능

            if condition_met:
                final_mult *= bonus_mult

        # HP 스케일링
        if self.hp_scaling:
            hp_percent = user.current_hp / user.max_hp
            if hp_percent < 0.3:
                final_mult *= 2.0
            elif hp_percent < 0.5:
                final_mult *= 1.5
        
        if self.damage_type == DamageType.BRV:
            # 물리/마법 구분
            # 탄환 정보를 kwargs에 전달 (관통탄 방어 관통력용)
            calc_kwargs = {}
            if context and 'defense_pierce_fixed' in context:
                calc_kwargs['defense_pierce_fixed'] = context['defense_pierce_fixed']
            
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
            
            # AOE HP 공격의 경우, 시작 시점의 BRV를 사용하도록 설정
            # (context에 저장된 초기 BRV가 있으면 사용, 없으면 현재 BRV 사용)
            use_initial_brv = context and '_aoe_hp_initial_brv' in context
            if use_initial_brv:
                # 임시로 BRV를 초기값으로 설정
                saved_brv = user.current_brv
                user.current_brv = context['_aoe_hp_initial_brv']
            
            hp_result = self.brave_system.hp_attack(user, target, final_mult, damage_type=self.stat_type, **hp_kwargs)
            
            # AOE HP 공격의 경우, BRV를 복원 (소모는 마지막 타겟에서만)
            if use_initial_brv:
                # 소모된 BRV만 계산하고, 나머지는 복원
                brv_consumed = context['_aoe_hp_initial_brv'] - user.current_brv
                user.current_brv = saved_brv - brv_consumed  # 원래 BRV에서 소모량만 빼기
            
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
            # HP 공격도 물리/마법 구분
            hp_result = self.brave_system.hp_attack(user, target, 1.0, damage_type=self.stat_type)
            result.hp_damage = hp_result['hp_damage']
            result.damage_dealt = hp_result['hp_damage']
            result.message = f"BRV+HP 공격! BRV:{result.brv_damage} HP:{result.hp_damage}"
            if context is not None:
                context['last_damage'] = result.hp_damage
        
        return result
