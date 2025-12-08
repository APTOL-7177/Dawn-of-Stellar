"""Archmage-specific Skill Effects - 아크메이지 전용 스킬 효과"""
import random
from typing import Dict, List, Any, Optional
from src.character.skills.effects.base import SkillEffect, EffectResult, EffectType
from src.combat.brave_system import get_brave_system
from src.combat.damage_calculator import get_damage_calculator
from src.core.logger import get_logger

logger = get_logger("archmage_effects")


class ChainDamageEffect(SkillEffect):
    """
    연쇄 데미지 효과 (폭뢰섬 전용)
    
    화염 원소 스택당 연쇄 확률 증가, 번개 원소 스택만큼 최대 연쇄 횟수 증가
    연쇄 데미지는 70% → 50% → 30%로 감소
    3회 이상 연쇄 시 화상 부여
    """
    def __init__(
        self,
        base_multiplier: float = 1.8,
        chain_chance_per_stack: float = 0.20,
        damage_falloff: List[float] = None,
        stat_type: str = "magical"
    ):
        super().__init__(EffectType.DAMAGE)
        self.base_multiplier = base_multiplier
        self.chain_chance_per_stack = chain_chance_per_stack
        self.damage_falloff = damage_falloff or [0.70, 0.50, 0.30, 0.20, 0.15]
        self.stat_type = stat_type
        self.brave_system = get_brave_system()
        self.damage_calculator = get_damage_calculator()
    
    def execute(self, user, target, context) -> EffectResult:
        """연쇄 폭발 데미지 실행"""
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)
        
        # 원소 스택 가져오기
        fire_stacks = getattr(user, 'fire_element', 0)
        lightning_stacks = getattr(user, 'lightning_element', 0)
        
        # 연쇄 확률: 화염 스택당 20%
        chain_chance = fire_stacks * self.chain_chance_per_stack
        # 최대 연쇄 횟수: 번개 스택 수
        max_chains = lightning_stacks
        
        # 주 대상 공격
        targets = target if isinstance(target, list) else [target]
        primary_target = targets[0] if targets else None
        
        if not primary_target or not primary_target.is_alive:
            return EffectResult(effect_type=EffectType.DAMAGE, success=False, message="대상 없음")
        
        # 1차 폭발 - 주 대상
        primary_damage = self._deal_damage(user, primary_target, self.base_multiplier)
        result.brv_damage = primary_damage.get('brv_damage', 0)
        result.hp_damage = primary_damage.get('hp_damage', 0)
        
        messages = [f"폭뢰섬! {primary_target.name}에게 BRV:{result.brv_damage} HP:{result.hp_damage}"]
        
        # 연쇄 폭발
        chain_count = 0
        chain_targets = []
        
        # context에서 적 전체 목록 가져오기
        all_enemies = context.get('all_enemies', targets) if context else targets
        available_targets = [e for e in all_enemies if e != primary_target and e.is_alive]
        
        current_chance = chain_chance
        for i in range(max_chains):
            if not available_targets:
                break
                
            # 연쇄 확률 체크
            if random.random() < current_chance:
                chain_target = random.choice(available_targets)
                falloff_idx = min(i, len(self.damage_falloff) - 1)
                chain_mult = self.base_multiplier * self.damage_falloff[falloff_idx]
                
                chain_damage = self._deal_damage(user, chain_target, chain_mult)
                result.brv_damage += chain_damage.get('brv_damage', 0)
                result.hp_damage += chain_damage.get('hp_damage', 0)
                
                chain_count += 1
                chain_targets.append(chain_target)
                available_targets.remove(chain_target)
                
                dmg_percent = int(self.damage_falloff[falloff_idx] * 100)
                messages.append(f"  → 연쇄 {chain_count}! {chain_target.name}에게 {dmg_percent}% 데미지")
        
        # 3회 이상 연쇄 시 화상 부여
        if chain_count >= 3:
            self._apply_burn_to_all([primary_target] + chain_targets, user)
            messages.append(f"  🔥 폭발 격화! 모든 피격자에게 화상 부여!")
        
        result.message = "\n".join(messages)
        return result
    
    def _deal_damage(self, user, target, multiplier: float) -> Dict[str, int]:
        """데미지 계산 및 적용"""
        if self.stat_type == "magical":
            dmg_result = self.damage_calculator.calculate_magic_damage(user, target, multiplier)
        else:
            dmg_result = self.damage_calculator.calculate_brv_damage(user, target, multiplier)
        
        brv_result = self.brave_system.brv_attack(user, target, dmg_result.final_damage)
        hp_result = self.brave_system.hp_attack(user, target, 1.0, damage_type=self.stat_type)
        
        return {
            'brv_damage': brv_result['brv_stolen'],
            'hp_damage': hp_result['hp_damage']
        }
    
    def _apply_burn_to_all(self, targets: List, user) -> None:
        """모든 대상에게 화상 부여"""
        try:
            from src.combat.status_effects import StatusEffect, StatusType
            for target in targets:
                if hasattr(target, 'status_manager') and target.is_alive:
                    burn_effect = StatusEffect(
                        name="화상",
                        status_type=StatusType.BURN,
                        duration=2,
                        intensity=0.30,  # 마법 공격력 30% DoT
                        source_id=getattr(user, 'name', None)
                    )
                    target.status_manager.add_status(burn_effect)
        except Exception as e:
            logger.error(f"화상 부여 실패: {e}")


class ElectrocutionEffect(SkillEffect):
    """
    감전 마비 효과 (극한뇌전 전용)
    
    번개 스택당 10% 마비 확률, 마비 실패 시 감전 부여
    빙결 스택당 ATB 증가 속도 -10%
    """
    def __init__(
        self,
        base_brv_multiplier: float = 2.2,
        base_hp_multiplier: float = 1.2,
        paralyze_chance_per_stack: float = 0.10,
        atb_slow_per_stack: float = 0.10,
        stat_type: str = "magical"
    ):
        super().__init__(EffectType.DAMAGE)
        self.base_brv_multiplier = base_brv_multiplier
        self.base_hp_multiplier = base_hp_multiplier
        self.paralyze_chance_per_stack = paralyze_chance_per_stack
        self.atb_slow_per_stack = atb_slow_per_stack
        self.stat_type = stat_type
        self.brave_system = get_brave_system()
        self.damage_calculator = get_damage_calculator()
    
    def execute(self, user, target, context) -> EffectResult:
        """빙결 감전 데미지 실행"""
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)
        
        # 원소 스택 가져오기
        ice_stacks = getattr(user, 'ice_element', 0)
        lightning_stacks = getattr(user, 'lightning_element', 0)
        
        # 마비 확률: 번개 스택당 10%, 완전 빙결 보너스
        base_paralyze_chance = lightning_stacks * self.paralyze_chance_per_stack
        # 완전 빙결: 빙결/번개 모두 3개 이상이면 +20%
        if ice_stacks >= 3 and lightning_stacks >= 3:
            base_paralyze_chance += 0.20
        paralyze_chance = min(base_paralyze_chance, 0.70)  # 최대 70%
        
        # 둔화 강도: 빙결 스택당 10%, 감전 상태면 2배
        slow_amount = min(ice_stacks * self.atb_slow_per_stack, 0.50)
        
        targets = target if isinstance(target, list) else [target]
        messages = []
        total_brv = 0
        total_hp = 0
        
        for t in targets:
            if not t.is_alive:
                continue
            
            # 데미지 계산
            brv_mult = self.base_brv_multiplier + (ice_stacks * 0.25)
            hp_mult = self.base_hp_multiplier + (lightning_stacks * 0.25)
            
            if self.stat_type == "magical":
                brv_result = self.damage_calculator.calculate_magic_damage(user, t, brv_mult)
            else:
                brv_result = self.damage_calculator.calculate_brv_damage(user, t, brv_mult)
            
            brv_attack = self.brave_system.brv_attack(user, t, brv_result.final_damage)
            hp_attack = self.brave_system.hp_attack(user, t, hp_mult, damage_type=self.stat_type)
            
            total_brv += brv_attack['brv_stolen']
            total_hp += hp_attack['hp_damage']
            
            messages.append(f"극한뇌전! {t.name}에게 BRV:{brv_attack['brv_stolen']} HP:{hp_attack['hp_damage']}")
            
            # 상태이상 부여
            if hasattr(t, 'status_manager'):
                self._apply_status_effects(t, user, paralyze_chance, slow_amount, messages)
        
        result.brv_damage = total_brv
        result.hp_damage = total_hp
        result.message = "\n".join(messages)
        return result
    
    def _apply_status_effects(self, target, user, paralyze_chance: float, slow_amount: float, messages: List[str]) -> None:
        """상태이상 부여"""
        try:
            from src.combat.status_effects import StatusEffect, StatusType
            
            # 마비 확률 체크
            if random.random() < paralyze_chance:
                paralyze_effect = StatusEffect(
                    name="마비",
                    status_type=StatusType.PARALYZE,
                    duration=1,
                    source_id=getattr(user, 'name', None)
                )
                target.status_manager.add_status(paralyze_effect)
                messages.append(f"  ⚡ {target.name} 마비!")
            else:
                # 마비 실패 시 감전 부여
                electro_effect = StatusEffect(
                    name="감전",
                    status_type=StatusType.ELECTROCUTED,
                    duration=3,
                    intensity=0.20,  # 마법 공격력 20% DoT
                    source_id=getattr(user, 'name', None)
                )
                target.status_manager.add_status(electro_effect)
                messages.append(f"  ⚡ {target.name} 감전! (3턴 DoT + ATB -15%)")
            
            # 둔화 부여
            if slow_amount > 0:
                # 감전 상태면 둔화 2배
                has_electro = target.status_manager.has_status(StatusType.ELECTROCUTED)
                final_slow = slow_amount * 2 if has_electro else slow_amount
                
                slow_effect = StatusEffect(
                    name="둔화",
                    status_type=StatusType.SLOWED,
                    duration=2,
                    intensity=final_slow,
                    source_id=getattr(user, 'name', None)
                )
                target.status_manager.add_status(slow_effect)
                messages.append(f"  🐌 {target.name} 둔화! (ATB -{int(final_slow*100)}%)")
                
        except Exception as e:
            logger.error(f"상태이상 부여 실패: {e}")


class ThermalShockEffect(SkillEffect):
    """
    열충격 파쇄 효과 (상반의 격류 전용)
    
    온도차 폭발: 화염/빙결 스택 차이만큼 추가 데미지
    방어 파쇄: 물리/마법 방어력 -30%
    완벽한 균형: 스택이 같을 때 크리티컬 +40%, 데미지 2.2x
    """
    def __init__(
        self,
        base_multiplier: float = 2.0,
        diff_bonus_per_stack: float = 0.15,
        balance_crit_bonus: float = 0.40,
        balance_crit_multiplier: float = 2.2,
        stat_type: str = "magical"
    ):
        super().__init__(EffectType.DAMAGE)
        self.base_multiplier = base_multiplier
        self.diff_bonus_per_stack = diff_bonus_per_stack
        self.balance_crit_bonus = balance_crit_bonus
        self.balance_crit_multiplier = balance_crit_multiplier
        self.stat_type = stat_type
        self.brave_system = get_brave_system()
        self.damage_calculator = get_damage_calculator()
    
    def execute(self, user, target, context) -> EffectResult:
        """열충격 파쇄 데미지 실행"""
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)
        
        # 원소 스택 가져오기
        fire_stacks = getattr(user, 'fire_element', 0)
        ice_stacks = getattr(user, 'ice_element', 0)
        
        # 스택 차이 및 균형 체크
        stack_diff = abs(fire_stacks - ice_stacks)
        is_balanced = (fire_stacks == ice_stacks and fire_stacks >= 3)
        
        # 데미지 배율 계산
        final_mult = self.base_multiplier
        final_mult += (fire_stacks * 0.30)  # 화염 스택 보너스
        final_mult += (ice_stacks * 0.30)   # 빙결 스택 보너스
        final_mult += (stack_diff * self.diff_bonus_per_stack)  # 온도차 보너스
        
        targets = target if isinstance(target, list) else [target]
        messages = []
        total_brv = 0
        total_hp = 0
        
        for t in targets:
            if not t.is_alive:
                continue
            
            # 크리티컬 처리
            calc_kwargs = {}
            if is_balanced:
                calc_kwargs['crit_bonus'] = self.balance_crit_bonus
                calc_kwargs['crit_damage_multiplier'] = self.balance_crit_multiplier
            
            if self.stat_type == "magical":
                dmg_result = self.damage_calculator.calculate_magic_damage(user, t, final_mult, **calc_kwargs)
            else:
                dmg_result = self.damage_calculator.calculate_brv_damage(user, t, final_mult, **calc_kwargs)
            
            brv_result = self.brave_system.brv_attack(user, t, dmg_result.final_damage)
            hp_result = self.brave_system.hp_attack(user, t, 1.0, damage_type=self.stat_type)
            
            total_brv += brv_result['brv_stolen']
            total_hp += hp_result['hp_damage']
            
            crit_msg = " 💥크리티컬!" if dmg_result.is_critical else ""
            messages.append(f"상반의 격류! {t.name}에게 BRV:{brv_result['brv_stolen']} HP:{hp_result['hp_damage']}{crit_msg}")
            
            # 방어 파쇄 부여
            if hasattr(t, 'status_manager'):
                self._apply_defense_shatter(t, user, messages)
                
                # 균형 상태일 때 상처 부여
                if is_balanced:
                    self._apply_wound(t, user, messages)
        
        # 효과 설명 추가
        if stack_diff > 0:
            messages.append(f"  🌡️ 온도차 {stack_diff} → +{int(stack_diff * self.diff_bonus_per_stack * 100)}% 데미지")
        if is_balanced:
            messages.append(f"  ⚖️ 완벽한 균형! 크리티컬 +{int(self.balance_crit_bonus*100)}%, 데미지 {self.balance_crit_multiplier}x")
        
        result.brv_damage = total_brv
        result.hp_damage = total_hp
        result.message = "\n".join(messages)
        return result
    
    def _apply_defense_shatter(self, target, user, messages: List[str]) -> None:
        """방어 파쇄 부여"""
        try:
            from src.combat.status_effects import StatusEffect, StatusType
            
            shatter_effect = StatusEffect(
                name="방어파쇄",
                status_type=StatusType.DEFENSE_SHATTER,
                duration=3,
                intensity=0.30,  # 물리/마법 방어력 -30%
                source_id=getattr(user, 'name', None),
                metadata={"brv_bonus": 0.25}  # 다음 공격 BRV +25%
            )
            target.status_manager.add_status(shatter_effect)
            messages.append(f"  💔 {target.name} 방어 파쇄! (방어력 -30%, 다음 공격 BRV +25%)")
        except Exception as e:
            logger.error(f"방어 파쇄 부여 실패: {e}")
    
    def _apply_wound(self, target, user, messages: List[str]) -> None:
        """상처 부여 (균형의 파열)"""
        try:
            from src.combat.status_effects import StatusEffect, StatusType
            
            wound_effect = StatusEffect(
                name="상처",
                status_type=StatusType.WOUND,
                duration=5,
                intensity=0.50,  # 회복 효과 -50%
                source_id=getattr(user, 'name', None)
            )
            target.status_manager.add_status(wound_effect)
            messages.append(f"  🩹 {target.name} 상처! (회복 효과 -50%, 5턴)")
        except Exception as e:
            logger.error(f"상처 부여 실패: {e}")


class ElementalTransmutationEffect(SkillEffect):
    """
    원소 변환 효과 (원소 순환 전용)
    
    원소 2개 소비 → 다른 원소 3개 생성
    완전 순환: 모든 원소 2개 이상일 때 보너스
    """
    def __init__(self, consume_amount: int = 2, generate_amount: int = 3):
        super().__init__(EffectType.GIMMICK)
        self.consume_amount = consume_amount
        self.generate_amount = generate_amount
    
    def execute(self, user, target, context) -> EffectResult:
        """원소 변환 실행"""
        result = EffectResult(effect_type=EffectType.GIMMICK, success=True)
        
        # 현재 원소 스택
        fire = getattr(user, 'fire_element', 0)
        ice = getattr(user, 'ice_element', 0)
        lightning = getattr(user, 'lightning_element', 0)
        
        # 변환 선택 (context에서 가져오거나 자동 선택)
        from_element = context.get('from_element') if context else None
        to_element = context.get('to_element') if context else None
        
        # 자동 선택: 가장 많은 원소에서 가장 적은 원소로
        if not from_element or not to_element:
            elements = {'fire': fire, 'ice': ice, 'lightning': lightning}
            sorted_elements = sorted(elements.items(), key=lambda x: x[1], reverse=True)
            from_element = sorted_elements[0][0]
            to_element = sorted_elements[2][0]
        
        # 변환 가능 여부 체크
        from_value = getattr(user, f'{from_element}_element', 0)
        if from_value < self.consume_amount:
            return EffectResult(
                effect_type=EffectType.GIMMICK,
                success=False,
                message=f"원소 부족: {from_element} {from_value}/{self.consume_amount}"
            )
        
        # 원소 변환
        setattr(user, f'{from_element}_element', from_value - self.consume_amount)
        to_value = getattr(user, f'{to_element}_element', 0)
        setattr(user, f'{to_element}_element', min(to_value + self.generate_amount, 5))
        
        messages = [f"원소 순환! {from_element} -{self.consume_amount} → {to_element} +{self.generate_amount}"]
        
        # 완전 순환 체크
        new_fire = getattr(user, 'fire_element', 0)
        new_ice = getattr(user, 'ice_element', 0)
        new_lightning = getattr(user, 'lightning_element', 0)
        
        if new_fire >= 2 and new_ice >= 2 and new_lightning >= 2:
            # 완전 순환 보너스
            setattr(user, 'fire_element', min(new_fire + 1, 5))
            setattr(user, 'ice_element', min(new_ice + 1, 5))
            setattr(user, 'lightning_element', min(new_lightning + 1, 5))
            
            # 마법 공격력 버프 (context에 저장)
            if context:
                context['transmutation_bonus'] = True
            
            messages.append("✨ 완전 순환! 모든 원소 +1, 마법 공격력 +20% (3턴)")
        
        # MP 회복
        if hasattr(user, 'current_mp'):
            user.current_mp = min(user.current_mp + 5, getattr(user, 'max_mp', 100))
            messages.append("💧 MP +5")
        
        result.message = "\n".join(messages)
        result.gimmick_changes = {
            f'{from_element}_element': -self.consume_amount,
            f'{to_element}_element': self.generate_amount
        }
        return result


class ElementalOverloadEffect(SkillEffect):
    """
    원소 과부하 효과 (원소 과부하 전용)
    
    선택한 원소 전체 소비, 원소별 고유 효과
    5스택 달성 시 특수 효과 발동
    """
    def __init__(self, min_stacks: int = 3):
        super().__init__(EffectType.DAMAGE)
        self.min_stacks = min_stacks
        self.brave_system = get_brave_system()
        self.damage_calculator = get_damage_calculator()
    
    def execute(self, user, target, context) -> EffectResult:
        """원소 과부하 실행"""
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)
        
        # 선택한 원소 (context에서 가져오거나 자동 선택)
        element = context.get('element') if context else None
        
        if not element:
            # 가장 많은 원소 자동 선택
            fire = getattr(user, 'fire_element', 0)
            ice = getattr(user, 'ice_element', 0)
            lightning = getattr(user, 'lightning_element', 0)
            
            elements = {'fire': fire, 'ice': ice, 'lightning': lightning}
            element = max(elements.items(), key=lambda x: x[1])[0]
        
        stacks = getattr(user, f'{element}_element', 0)
        
        if stacks < self.min_stacks:
            return EffectResult(
                effect_type=EffectType.DAMAGE,
                success=False,
                message=f"원소 부족: {element} {stacks}/{self.min_stacks}"
            )
        
        # 원소 전체 소비
        setattr(user, f'{element}_element', 0)
        
        # 원소별 효과 실행
        if element == 'fire':
            return self._fire_overload(user, target, stacks, context)
        elif element == 'ice':
            return self._ice_overload(user, target, stacks, context)
        else:  # lightning
            return self._lightning_overload(user, target, stacks, context)
    
    def _fire_overload(self, user, target, stacks: int, context) -> EffectResult:
        """화염 과부하: 전체 공격 + 작열"""
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)
        
        # 데미지 배율: 스택당 +0.4x
        multiplier = 1.0 + (stacks * 0.4)
        
        targets = target if isinstance(target, list) else [target]
        if context:
            targets = context.get('all_enemies', targets)
        
        messages = [f"🔥 화염 과부하! ({stacks}스택)"]
        total_brv = 0
        total_hp = 0
        
        for t in targets:
            if not t.is_alive:
                continue
            
            dmg_result = self.damage_calculator.calculate_magic_damage(user, t, multiplier)
            brv_result = self.brave_system.brv_attack(user, t, dmg_result.final_damage)
            hp_result = self.brave_system.hp_attack(user, t, 1.0, damage_type="magical")
            
            total_brv += brv_result['brv_stolen']
            total_hp += hp_result['hp_damage']
            
            # 작열 부여
            if hasattr(t, 'status_manager'):
                try:
                    from src.combat.status_effects import StatusEffect, StatusType
                    burning_effect = StatusEffect(
                        name="작열",
                        status_type=StatusType.BURNING,
                        duration=4,
                        intensity=0.40,  # 마법 공격력 40% DoT + 화염 저항 -30%
                        source_id=getattr(user, 'name', None)
                    )
                    t.status_manager.add_status(burning_effect)
                except:
                    pass
        
        # 5스택 특수 효과: 화염 폭풍
        if stacks >= 5:
            messages.append("  🌋 화염 폭풍 발동! 추가 광역 BRV 1.5x")
            for t in targets:
                if t.is_alive:
                    extra_dmg = self.damage_calculator.calculate_magic_damage(user, t, 1.5)
                    extra_brv = self.brave_system.brv_attack(user, t, extra_dmg.final_damage)
                    total_brv += extra_brv['brv_stolen']
        
        messages.append(f"총 BRV:{total_brv} HP:{total_hp}")
        result.brv_damage = total_brv
        result.hp_damage = total_hp
        result.message = "\n".join(messages)
        return result
    
    def _ice_overload(self, user, target, stacks: int, context) -> EffectResult:
        """빙결 과부하: 전체 공격 + 동결"""
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)
        
        multiplier = 1.0 + (stacks * 0.5)
        
        targets = target if isinstance(target, list) else [target]
        if context:
            targets = context.get('all_enemies', targets)
        
        messages = [f"❄️ 빙결 과부하! ({stacks}스택)"]
        total_brv = 0
        
        for t in targets:
            if not t.is_alive:
                continue
            
            dmg_result = self.damage_calculator.calculate_magic_damage(user, t, multiplier)
            brv_result = self.brave_system.brv_attack(user, t, dmg_result.final_damage)
            total_brv += brv_result['brv_stolen']
            
            # 동결 부여 (스택당 1턴)
            if hasattr(t, 'status_manager'):
                try:
                    from src.combat.status_effects import StatusEffect, StatusType
                    frozen_effect = StatusEffect(
                        name="동결",
                        status_type=StatusType.FROZEN_SOLID,
                        duration=stacks,  # 스택당 1턴
                        source_id=getattr(user, 'name', None)
                    )
                    t.status_manager.add_status(frozen_effect)
                except:
                    pass
        
        # 5스택 특수 효과: 절대영도
        if stacks >= 5:
            messages.append("  ❄️❄️❄️ 절대영도 발동! 모든 적 BRV = 0, BREAK!")
            for t in targets:
                if t.is_alive:
                    old_brv = t.current_brv
                    t.current_brv = 0
                    # BREAK 처리
                    if hasattr(t, 'is_broken'):
                        t.is_broken = True
                    total_brv += old_brv
        
        messages.append(f"총 BRV:{total_brv}")
        result.brv_damage = total_brv
        result.message = "\n".join(messages)
        return result
    
    def _lightning_overload(self, user, target, stacks: int, context) -> EffectResult:
        """번개 과부하: 단일 연타 공격"""
        result = EffectResult(effect_type=EffectType.DAMAGE, success=True)
        
        targets = target if isinstance(target, list) else [target]
        primary_target = targets[0] if targets else None
        
        if not primary_target or not primary_target.is_alive:
            return EffectResult(effect_type=EffectType.DAMAGE, success=False)
        
        # 연타 횟수: 스택 수, 5스택이면 10회
        hit_count = 10 if stacks >= 5 else stacks
        hit_mult = 0.6  # 타당 0.6x
        
        messages = [f"⚡ 번개 과부하! ({stacks}스택, {hit_count}연타)"]
        total_brv = 0
        total_hp = 0
        stun_applied = False
        
        for i in range(hit_count):
            if not primary_target.is_alive:
                break
            
            # 마지막 타격은 3배 데미지 (5스택일 때)
            current_mult = hit_mult * 3 if (stacks >= 5 and i == hit_count - 1) else hit_mult
            
            dmg_result = self.damage_calculator.calculate_magic_damage(user, primary_target, current_mult)
            brv_result = self.brave_system.brv_attack(user, primary_target, dmg_result.final_damage)
            hp_result = self.brave_system.hp_attack(user, primary_target, 0.3, damage_type="magical")
            
            total_brv += brv_result['brv_stolen']
            total_hp += hp_result['hp_damage']
            
            # 10% 확률로 기절
            if random.random() < 0.10 and hasattr(primary_target, 'status_manager'):
                try:
                    from src.combat.status_effects import StatusEffect, StatusType
                    stun_effect = StatusEffect(
                        name="기절",
                        status_type=StatusType.STUN,
                        duration=1,
                        source_id=getattr(user, 'name', None)
                    )
                    primary_target.status_manager.add_status(stun_effect)
                    stun_applied = True
                except:
                    pass
        
        if stacks >= 5:
            messages.append("  ⚡⚡⚡ 뇌신강림! 마지막 타격 3배 데미지!")
        if stun_applied:
            messages.append(f"  😵 {primary_target.name} 기절!")
        
        messages.append(f"총 BRV:{total_brv} HP:{total_hp}")
        result.brv_damage = total_brv
        result.hp_damage = total_hp
        result.message = "\n".join(messages)
        return result


class ElementalBrandEffect(SkillEffect):
    """
    원소 낙인 효과 (원소 낙인 전용)
    
    대상에게 3가지 원소 낙인 부여
    낙인된 적은 해당 원소 공격에 취약
    """
    def __init__(self, vulnerability: float = 0.40, duration: int = 5):
        super().__init__(EffectType.BUFF)
        self.vulnerability = vulnerability
        self.duration = duration
    
    def execute(self, user, target, context) -> EffectResult:
        """원소 낙인 부여"""
        result = EffectResult(effect_type=EffectType.BUFF, success=True)
        
        targets = target if isinstance(target, list) else [target]
        messages = ["원소 낙인!"]
        branded_count = 0
        
        for t in targets:
            if not t.is_alive or not hasattr(t, 'status_manager'):
                continue
            
            try:
                from src.combat.status_effects import StatusEffect, StatusType
                
                # 화염 낙인
                fire_brand = StatusEffect(
                    name="화염낙인",
                    status_type=StatusType.FIRE_BRAND,
                    duration=self.duration,
                    intensity=self.vulnerability,
                    source_id=getattr(user, 'name', None)
                )
                t.status_manager.add_status(fire_brand)
                
                # 빙결 낙인
                ice_brand = StatusEffect(
                    name="빙결낙인",
                    status_type=StatusType.ICE_BRAND,
                    duration=self.duration,
                    intensity=self.vulnerability,
                    source_id=getattr(user, 'name', None)
                )
                t.status_manager.add_status(ice_brand)
                
                # 번개 낙인
                lightning_brand = StatusEffect(
                    name="번개낙인",
                    status_type=StatusType.LIGHTNING_BRAND,
                    duration=self.duration,
                    intensity=self.vulnerability,
                    source_id=getattr(user, 'name', None)
                )
                t.status_manager.add_status(lightning_brand)
                
                branded_count += 1
                messages.append(f"  {t.name}: 🔥❄️⚡ 낙인 부여! (원소 피해 +{int(self.vulnerability*100)}%, {self.duration}턴)")
                
            except Exception as e:
                logger.error(f"원소 낙인 부여 실패: {e}")
        
        result.success = branded_count > 0
        result.message = "\n".join(messages)
        return result


class ElementalAegisEffect(SkillEffect):
    """
    원소 장막 효과 (원소 장막 전용)

    모든 원소 스택 소비하여 아군 전체 공유 보호막 생성
    HP 피해 1당 BRV 피해 4로 환산하여 보호막에서 흡수
    원소별 추가 효과 (반사, 둔화, 감전)
    """
    def __init__(self, base_multiplier: float = 4.5, duration: int = 3):
        super().__init__(EffectType.GIMMICK)
        self.base_multiplier = base_multiplier  # 마법력 기반 배율
        self.duration = duration

    def execute(self, user, target, context) -> EffectResult:
        """원소 장막 생성"""
        result = EffectResult(effect_type=EffectType.GIMMICK, success=True)

        # 원소 스택 가져오기
        fire_stacks = getattr(user, 'fire_element', 0)
        ice_stacks = getattr(user, 'ice_element', 0)
        lightning_stacks = getattr(user, 'lightning_element', 0)
        total_stacks = fire_stacks + ice_stacks + lightning_stacks

        if total_stacks < 7:
            return EffectResult(
                effect_type=EffectType.GIMMICK,
                success=False,
                message=f"원소 부족: 총 {total_stacks}/7 스택"
            )

        # 보호막 내구도 계산: 마법력 × 소모 원소 × 상수
        magic_power = getattr(user, 'magic_attack', 50)
        shield_amount = int(magic_power * total_stacks * self.base_multiplier)

        # 완전 보호 체크: 모든 원소 3개 이상
        is_perfect = fire_stacks >= 3 and ice_stacks >= 3 and lightning_stacks >= 3
        if is_perfect:
            shield_amount = int(shield_amount * 1.5)  # 내구도 1.5배
        
        # 아군 전체 공유 보호막 설정 (combat_manager 또는 party에 저장)
        combat_manager = context.get('combat_manager') if context else None
        party = context.get('party') if context else None

        # 기존 보호막이 있으면 제거 (새 보호막으로 교체)
        if combat_manager and hasattr(combat_manager, 'party_elemental_shield'):
            old_shield = combat_manager.party_elemental_shield
            if old_shield:
                logger.info(f"[원소 장막] 기존 보호막 제거 (잔여: {old_shield.get('amount', 0)})")

        # 보호막 데이터
        shield_data = {
            'amount': shield_amount,
            'max_amount': shield_amount,
            'duration': 5 if is_perfect else self.duration,
            'fire_stacks': fire_stacks,
            'ice_stacks': ice_stacks,
            'lightning_stacks': lightning_stacks,
            'is_perfect': is_perfect,
            'caster': getattr(user, 'name', 'Unknown'),
            'hp_to_brv_ratio': 4  # HP 피해 1당 BRV 피해 4로 환산
        }

        # combat_manager에 보호막 저장 (최우선)
        if combat_manager:
            combat_manager.party_elemental_shield = shield_data
        # party가 있으면 party에도 저장
        if party:
            party.elemental_shield = shield_data
        # fallback: user에 저장
        user.elemental_shield = shield_data

        # 원소 스택 소비
        user.fire_element = 0
        user.ice_element = 0
        user.lightning_element = 0

        # 아군 전체에게 원소 장막 버프 부여 (시각적 표시용)
        allies = []
        if party:
            allies = party
        elif combat_manager and hasattr(combat_manager, 'allies'):
            allies = combat_manager.allies
        else:
            allies = [user]

        try:
            from src.combat.status_effects import StatusEffect, StatusType
            for ally in allies:
                if hasattr(ally, 'status_manager') and hasattr(ally, 'is_alive') and ally.is_alive:
                    aegis_effect = StatusEffect(
                        name="원소장막",
                        status_type=StatusType.ELEMENTAL_AEGIS,
                        duration=5 if is_perfect else self.duration,
                        intensity=1.0,
                        source_id=getattr(user, 'name', None),
                        metadata={
                            'shared_shield': True,
                            'shield_amount': shield_amount,
                            'fire_reflect': fire_stacks * 0.10,
                            'ice_slow': ice_stacks * 0.15,
                            'lightning_shock': lightning_stacks * 0.15
                        }
                    )
                    ally.status_manager.add_status(aegis_effect)
        except Exception as e:
            logger.error(f"원소 장막 버프 부여 실패: {e}")
        
        messages = [
            f"원소 장막 활성화! [아군 전체 공유]",
            f"  🛡️ 보호막: {shield_amount} (HP 피해 1 = 보호막 4 소모)",
            f"  🔥 반사 확률: {fire_stacks * 10}%",
            f"  ❄️ 둔화 효과: ATB -{ice_stacks * 15}%",
            f"  ⚡ 감전 DoT: {lightning_stacks * 15}%"
        ]

        if is_perfect:
            messages.append("  ✨ 완전 보호! 내구도 1.5배, 피해 감소 +30%, 지속 5턴")

        # 모든 아군에게 알림
        messages.append(f"  👥 보호 대상: {len(allies)}명의 아군")
        
        result.message = "\n".join(messages)
        result.gimmick_changes = {
            'elemental_shield': shield_amount,
            'fire_element': -fire_stacks,
            'ice_element': -ice_stacks,
            'lightning_element': -lightning_stacks
        }
        return result


class DelayedGlyphEffect(SkillEffect):
    """
    지연 마법진 효과 (지연 마법진 전용)
    
    원소 마법진 설치 (최대 3개)
    3턴 후 자동 발동 또는 융합 스킬로 기폭
    """
    def __init__(self, delay_turns: int = 3):
        super().__init__(EffectType.GIMMICK)
        self.delay_turns = delay_turns
    
    def execute(self, user, target, context) -> EffectResult:
        """마법진 설치"""
        result = EffectResult(effect_type=EffectType.GIMMICK, success=True)
        
        # 설치할 원소 (context에서 가져오기)
        element = context.get('element') if context else None
        
        if not element:
            # 가장 많은 원소 자동 선택
            fire = getattr(user, 'fire_element', 0)
            ice = getattr(user, 'ice_element', 0)
            lightning = getattr(user, 'lightning_element', 0)
            
            elements = {'fire': fire, 'ice': ice, 'lightning': lightning}
            element = max(elements.items(), key=lambda x: x[1])[0]
        
        # 원소 스택 체크
        element_value = getattr(user, f'{element}_element', 0)
        if element_value < 1:
            return EffectResult(
                effect_type=EffectType.GIMMICK,
                success=False,
                message=f"원소 부족: {element}"
            )
        
        # 마법진 리스트 초기화
        if not hasattr(user, 'delayed_glyphs'):
            user.delayed_glyphs = []
        
        # 최대 3개 제한
        if len(user.delayed_glyphs) >= 3:
            return EffectResult(
                effect_type=EffectType.GIMMICK,
                success=False,
                message="마법진 최대 개수 도달 (3개)"
            )
        
        # 원소 소비
        setattr(user, f'{element}_element', element_value - 1)
        
        # 마법진 설치
        glyph = {
            'element': element,
            'remaining_turns': self.delay_turns,
            'owner': getattr(user, 'name', 'Unknown')
        }
        user.delayed_glyphs.append(glyph)
        
        element_icons = {'fire': '🔥', 'ice': '❄️', 'lightning': '⚡'}
        icon = element_icons.get(element, '❓')
        
        messages = [
            f"지연 마법진 설치!",
            f"  {icon} {element} 마법진 설치 ({self.delay_turns}턴 후 발동)",
            f"  현재 설치: {len(user.delayed_glyphs)}/3개"
        ]
        
        result.message = "\n".join(messages)
        result.gimmick_changes = {f'{element}_element': -1}
        return result


class GlyphDetonationHelper:
    """
    지연 마법진 발동 헬퍼 클래스
    
    마법진이 발동될 때 원소별 효과 처리
    """
    
    @staticmethod
    def detonate_glyph(glyph: dict, user, targets: list, context=None) -> dict:
        """마법진 발동 처리"""
        from src.combat.brave_system import get_brave_system
        from src.combat.damage_calculator import get_damage_calculator
        
        brave_system = get_brave_system()
        damage_calculator = get_damage_calculator()
        
        element = glyph.get('element', 'fire')
        element_icons = {'fire': '🔥', 'ice': '❄️', 'lightning': '⚡'}
        icon = element_icons.get(element, '❓')
        
        result = {
            'element': element,
            'total_brv': 0,
            'total_hp': 0,
            'status_effects': [],
            'messages': []
        }
        
        # 원소별 데미지 배율 및 효과
        element_config = {
            'fire': {'multiplier': 1.5, 'status': 'burn', 'status_duration': 3},
            'ice': {'multiplier': 1.2, 'status': 'slowed', 'status_duration': 2},
            'lightning': {'multiplier': 1.8, 'status': 'electrocuted', 'status_duration': 2}
        }
        
        config = element_config.get(element, element_config['fire'])
        
        result['messages'].append(f"{icon} {element} 마법진 발동!")
        
        for target in targets:
            if not target.is_alive:
                continue
            
            # 데미지 계산
            dmg_result = damage_calculator.calculate_magic_damage(user, target, config['multiplier'])
            brv_result = brave_system.brv_attack(user, target, dmg_result.final_damage)
            
            result['total_brv'] += brv_result['brv_stolen']
            result['messages'].append(f"  → {target.name}: BRV {brv_result['brv_stolen']}")
            
            # 상태이상 부여
            if hasattr(target, 'status_manager'):
                try:
                    from src.combat.status_effects import StatusEffect, StatusType
                    
                    status_map = {
                        'burn': StatusType.BURN,
                        'slowed': StatusType.SLOWED,
                        'electrocuted': StatusType.ELECTROCUTED
                    }
                    
                    status_type = status_map.get(config['status'])
                    if status_type:
                        effect = StatusEffect(
                            name=config['status'],
                            status_type=status_type,
                            duration=config['status_duration'],
                            intensity=0.15,
                            source_id=getattr(user, 'name', None)
                        )
                        target.status_manager.add_status(effect)
                        result['status_effects'].append({
                            'target': target.name,
                            'status': config['status']
                        })
                except Exception as e:
                    logger.error(f"마법진 상태이상 부여 실패: {e}")
        
        return result
    
    @staticmethod
    def detonate_all_glyphs(user, targets: list, context=None) -> list:
        """모든 마법진 발동"""
        if not hasattr(user, 'delayed_glyphs') or not user.delayed_glyphs:
            return []
        
        results = []
        for glyph in user.delayed_glyphs:
            result = GlyphDetonationHelper.detonate_glyph(glyph, user, targets, context)
            results.append(result)
        
        user.delayed_glyphs = []
        return results
    
    @staticmethod
    def detonate_by_elements(user, elements: list, targets: list, context=None) -> list:
        """특정 원소의 마법진만 발동 (융합 스킬 사용 시)"""
        if not hasattr(user, 'delayed_glyphs') or not user.delayed_glyphs:
            return []
        
        results = []
        remaining = []
        
        for glyph in user.delayed_glyphs:
            if glyph['element'] in elements:
                result = GlyphDetonationHelper.detonate_glyph(glyph, user, targets, context)
                results.append(result)
            else:
                remaining.append(glyph)
        
        user.delayed_glyphs = remaining
        return results
