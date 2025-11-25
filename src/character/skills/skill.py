"""Skill - 스킬 클래스"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

@dataclass
class SkillResult:
    """스킬 실행 결과"""
    success: bool
    message: str = ""
    total_damage: int = 0
    total_heal: int = 0

class Skill:
    """스킬 클래스"""
    def __init__(self, skill_id: str, name: str, description: str = ""):
        self.skill_id = skill_id
        self.name = name
        self.description = description
        self.effects = []
        self.costs = []
        self.target_type = "single_enemy"
        self.cast_time = None  # 기본값: 캐스팅 없음
        # self.cooldown = 0  # 쿨다운 시스템 제거됨
        self.category = "combat"
        self.is_ultimate = False
        self.metadata = {}
        self.sfx: Optional[Tuple[str, str]] = None  # (category, sfx_name) 튜플

    def can_use(self, user: Any, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """스킬 사용 가능 여부"""
        context = context or {}
        # 스킬 정보를 context에 추가 (특성 효과 적용을 위해)
        context['skill'] = self
        
        # 행동 불가 상태이상 체크 (빙결, 기절 등 - 모든 행동 불가)
        if hasattr(user, 'status_manager'):
            if not user.status_manager.can_act():
                # 기본 공격인지 확인
                is_basic_attack = self.metadata.get('basic_attack', False)
                if not is_basic_attack:
                    return False, "행동 불가 상태로 인해 스킬을 사용할 수 없습니다"
        
        # 침묵 상태이상 체크 (기본 공격은 제외)
        if hasattr(user, 'status_manager'):
            if not user.status_manager.can_use_skills():
                # 기본 공격인지 확인 (여러 방법으로 확인)
                is_basic_attack = self.metadata.get('basic_attack', False)
                
                # 메타데이터에 없으면 다른 방법으로 확인
                if not is_basic_attack:
                    # 1. costs가 비어있고 (MP 소모 없음)
                    # 2. 스킬이 사용자의 skill_ids에서 첫 번째 또는 두 번째인 경우
                    if not self.costs and hasattr(user, 'skill_ids') and user.skill_ids:
                        skill_index = user.skill_ids.index(self.skill_id) if self.skill_id in user.skill_ids else -1
                        if skill_index in [0, 1]:  # 첫 번째 또는 두 번째 스킬
                            is_basic_attack = True
                
                if not is_basic_attack:
                    return False, "침묵 상태로 인해 스킬을 사용할 수 없습니다"
        
        # 비용 체크
        for cost in self.costs:
            can_afford, reason = cost.can_afford(user, context)
            if not can_afford:
                return False, reason
        
        # 메타데이터 기반 조건 체크
        if self.metadata:
            # 배틀메이지: 서로 다른 룬 3개 필요
            if self.metadata.get("requires_different_runes"):
                required_count = self.metadata.get("requires_different_runes", 3)
                if hasattr(user, 'gimmick_type') and user.gimmick_type == "rune_resonance":
                    rune_types = ["rune_fire", "rune_ice", "rune_lightning", "rune_earth", "rune_arcane"]
                    different_runes = 0
                    for rune_type in rune_types:
                        if getattr(user, rune_type, 0) > 0:
                            different_runes += 1
                    
                    if different_runes < required_count:
                        return False, f"서로 다른 룬 {required_count}개가 필요합니다 (현재: {different_runes}개)"
            
            # 해커: 프로그램 실행 스킬은 스레드 여유가 있어야 사용 가능
            if self.metadata.get("program_type"):
                if hasattr(user, 'gimmick_type') and user.gimmick_type == "multithread_system":
                    # 현재 활성 프로그램 수 계산
                    program_fields = ['program_virus', 'program_backdoor', 'program_ddos', 'program_ransomware', 'program_spyware']
                    active_programs = sum(1 for field in program_fields if getattr(user, field, 0) > 0)
                    max_threads = getattr(user, 'max_threads', 3)
                    
                    # 이미 최대 스레드 수만큼 프로그램이 실행 중이면 새 프로그램 실행 불가
                    if active_programs >= max_threads:
                        return False, f"스레드 부족! (활성: {active_programs}/{max_threads})"
            
            # 몽크: 기 게이지 조건 체크
            if hasattr(user, 'gimmick_type') and user.gimmick_type == "yin_yang_flow":
                ki_gauge = getattr(user, 'ki_gauge', 50)
                
                # 음 극단 상태 필요 (20 이하)
                if self.metadata.get("requires_yin"):
                    if ki_gauge > 20:
                        return False, f"음 극단 상태(20 이하)가 필요합니다 (현재: {ki_gauge})"
                
                # 양 극단 상태 필요 (80 이상)
                if self.metadata.get("requires_yang"):
                    if ki_gauge < 80:
                        return False, f"양 극단 상태(80 이상)가 필요합니다 (현재: {ki_gauge})"
                
                # 균형 상태 필요 (40-60)
                if self.metadata.get("requires_balance"):
                    if not (40 <= ki_gauge <= 60):
                        return False, f"균형 상태(40-60)가 필요합니다 (현재: {ki_gauge})"
                
                # 정확한 기 게이지 값 필요
                if "ki_exact" in self.metadata:
                    required_ki = self.metadata.get("ki_exact")
                    if ki_gauge != required_ki:
                        return False, f"기 게이지가 정확히 {required_ki}여야 합니다 (현재: {ki_gauge})"
            
            # 차원술사: 확률 왜곡 게이지 소모량 조건 체크
            if hasattr(user, 'gimmick_type') and user.gimmick_type == "probability_distortion":
                if "distortion_cost" in self.metadata:
                    required_gauge = self.metadata.get("distortion_cost", 0)
                    current_gauge = getattr(user, 'distortion_gauge', 0)
                    if current_gauge < required_gauge:
                        return False, f"확률 왜곡 게이지가 부족합니다! (필요: {required_gauge}, 현재: {current_gauge})"
            
            # 정령술사: 융합 스킬 조건 체크
            if hasattr(user, 'gimmick_type') and user.gimmick_type == "elemental_spirits":
                # 융합 스킬은 필요한 정령이 모두 소환되어 있어야 함
                if self.metadata.get("requires_both_spirits", False):
                    fusion_type = self.metadata.get("fusion", "")
                    spirit_fire = getattr(user, 'spirit_fire', 0)
                    spirit_water = getattr(user, 'spirit_water', 0)
                    spirit_wind = getattr(user, 'spirit_wind', 0)
                    spirit_earth = getattr(user, 'spirit_earth', 0)
                    
                    missing_spirits = []
                    
                    if fusion_type == "fire_wind":
                        if spirit_fire == 0:
                            missing_spirits.append("화염 정령")
                        if spirit_wind == 0:
                            missing_spirits.append("바람 정령")
                    elif fusion_type == "water_earth":
                        if spirit_water == 0:
                            missing_spirits.append("물 정령")
                        if spirit_earth == 0:
                            missing_spirits.append("대지 정령")
                    elif fusion_type == "fire_water":
                        if spirit_fire == 0:
                            missing_spirits.append("화염 정령")
                        if spirit_water == 0:
                            missing_spirits.append("물 정령")
                    
                    if missing_spirits:
                        return False, f"융합 스킬 사용 불가: {', '.join(missing_spirits)} 소환 필요"
                
                # 정령 소환 스킬: 최대 정령 수 체크 (이미 2마리 소환되어 있으면 새로 소환 불가)
                if self.metadata.get("spirit_type"):
                    current_spirits = (
                        getattr(user, 'spirit_fire', 0) +
                        getattr(user, 'spirit_water', 0) +
                        getattr(user, 'spirit_wind', 0) +
                        getattr(user, 'spirit_earth', 0)
                    )
                    max_spirits = getattr(user, 'max_spirits', 2)
                    
                    # 이미 소환된 정령이 최대치이고, 새로 소환하려는 정령이 아직 소환되지 않은 경우
                    spirit_type = self.metadata.get("spirit_type")
                    spirit_attr = f"spirit_{spirit_type}"
                    current_spirit_value = getattr(user, spirit_attr, 0)
                    
                    if current_spirits >= max_spirits and current_spirit_value == 0:
                        return False, f"최대 정령 수 도달! (현재: {current_spirits}/{max_spirits}) 기존 정령을 해제하거나 대체해야 합니다"
            
            # 암살자: 은신 스킬 조건 체크 (노출 상태에서 3턴 경과 후에만 사용 가능)
            if self.metadata.get("enter_stealth"):
                if hasattr(user, 'gimmick_type') and user.gimmick_type == "stealth_exposure":
                    stealth_active = getattr(user, 'stealth_active', False)
                    exposed_turns = getattr(user, 'exposed_turns', 0)
                    restealth_cooldown = getattr(user, 'restealth_cooldown', 3)
                    
                    # 이미 은신 상태면 은신 스킬 사용 불가
                    if stealth_active:
                        return False, "이미 은신 상태입니다"
                    
                    # 노출 상태에서 쿨다운이 지나지 않았으면 사용 불가
                    if exposed_turns < restealth_cooldown:
                        remaining = restealth_cooldown - exposed_turns
                        return False, f"재은신 쿨다운 중입니다 ({remaining}턴 남음)"
        
        return True, ""

    def execute(self, user: Any, target: Any, context: Optional[Dict[str, Any]] = None) -> SkillResult:
        """스킬 실행"""
        context = context or {}
        # 스킬 정보를 context에 추가 (특성 효과 적용을 위해)
        context['skill'] = self
        
        can_use, reason = self.can_use(user, context)
        if not can_use:
            return SkillResult(success=False, message=f"사용 불가: {reason}")

        # target_type이 "all_enemies"인 경우, context에서 all_enemies 가져오기
        if hasattr(self, 'target_type') and self.target_type == "all_enemies":
            all_enemies = context.get('all_enemies', [])
            if all_enemies:
                target = all_enemies
            else:
                # all_enemies가 없으면 combat_manager에서 가져오기
                combat_manager = context.get('combat_manager')
                if combat_manager:
                    # 아군이 사용하는 경우 적 전체, 적이 사용하는 경우 아군 전체
                    if hasattr(combat_manager, 'allies') and user in getattr(combat_manager, 'allies', []):
                        target = getattr(combat_manager, 'enemies', [])
                    elif hasattr(combat_manager, 'enemies') and user in getattr(combat_manager, 'enemies', []):
                        target = getattr(combat_manager, 'allies', [])
                    else:
                        # 기본값: 적 전체
                        target = getattr(combat_manager, 'enemies', [])
                else:
                    # combat_manager도 없으면 원래 target 유지 (하위 호환성)
                    pass

        # target_type이 "ALL_ALLIES"인 경우, context에서 아군 전체 가져오기
        from src.character.skill_types import SkillTargetType
        if hasattr(self, 'target_type') and (self.target_type == SkillTargetType.ALL_ALLIES or self.target_type == "all_allies"):
            combat_manager = context.get('combat_manager')
            if combat_manager:
                # 아군이 사용하는 경우 아군 전체, 적이 사용하는 경우 적 전체
                if hasattr(combat_manager, 'allies') and user in getattr(combat_manager, 'allies', []):
                    target = getattr(combat_manager, 'allies', [])
                elif hasattr(combat_manager, 'enemies') and user in getattr(combat_manager, 'enemies', []):
                    target = getattr(combat_manager, 'enemies', [])
                else:
                    # 기본값: 아군 전체
                    target = getattr(combat_manager, 'allies', [])
            elif isinstance(target, list):
                # 이미 리스트로 전달된 경우 그대로 사용
                pass
            else:
                # combat_manager도 없고 리스트도 아니면 단일 타겟을 리스트로 변환
                target = [target] if target else []

        # 비용 소비
        # 스냅샷 컨텍스트가 있으면 캐스팅 완료 후이므로 StackCost 건너뛰기
        # (스택은 effects의 GimmickEffect.CONSUME에서 처리)
        has_snapshot = 'snapshot_context' in context
        is_dark_knight_for_cost = (hasattr(user, 'gimmick_type') and user.gimmick_type == "charge_system") or \
                                  (hasattr(user, 'character_class') and 'dark_knight' in str(user.character_class).lower()) or \
                                  (hasattr(user, 'job_id') and 'dark_knight' in str(user.job_id).lower())
        
        for cost in self.costs:
            # 스냅샷이 있거나 암흑기사이고 StackCost인 경우 건너뛰기
            if has_snapshot or is_dark_knight_for_cost:
                from src.character.skills.costs.stack_cost import StackCost
                if isinstance(cost, StackCost):
                    continue  # StackCost는 건너뛰고 effects의 GimmickEffect.CONSUME에서 처리
            
            if not cost.consume(user, context):
                return SkillResult(success=False, message="비용 소비 실패")

        # 랜덤 룬 추가 처리 (배틀메이지)
        if self.metadata.get("random_rune") and hasattr(user, 'gimmick_type') and user.gimmick_type == "rune_resonance":
            import random
            rune_types = ["fire", "ice", "lightning", "earth", "arcane"]
            selected_rune = random.choice(rune_types)
            rune_field = f"rune_{selected_rune}"
            current_value = getattr(user, rune_field, 0)
            max_value = getattr(user, 'max_rune_per_type', 3)
            if current_value < max_value:
                setattr(user, rune_field, current_value + 1)
                from src.core.logger import get_logger
                logger = get_logger("skill")
                logger.info(f"{user.name} 랜덤 룬 획득: {selected_rune} 룬 (+1, 총: {current_value + 1}/{max_value})")
            
            # 적에게 룬 새기기 (적이 리스트인 경우 첫 번째 적에게 적용)
            target_list = target if isinstance(target, list) else [target]
            for single_target in target_list:
                if single_target and hasattr(single_target, 'is_alive') and single_target.is_alive:
                    # 적의 carved_runes 딕셔너리 초기화 (없으면)
                    if not hasattr(single_target, 'carved_runes'):
                        single_target.carved_runes = {}
                    
                    # 랜덤 룬 타입을 적에게 새기기 (최대 3개까지)
                    current_count = single_target.carved_runes.get(selected_rune, 0)
                    if current_count < 3:
                        single_target.carved_runes[selected_rune] = current_count + 1
                        rune_names = {"fire": "화염", "ice": "냉기", "lightning": "번개", "earth": "대지", "arcane": "비전"}
                        rune_name = rune_names.get(selected_rune, selected_rune)
                        logger.info(f"{single_target.name}에게 {rune_name} 룬 새김! (총: {current_count + 1}/3)")
                    break  # 첫 번째 적에게만 적용

        # 효과 실행 (ISSUE-003: 효과 메시지 수집)
        total_dmg = 0
        total_heal = 0
        effect_messages = []  # 각 효과의 메시지 수집

        # 수호의 맹세 스킬: 본인에게 보호막을 두르고 선택한 아군을 보호
        # ProtectEffect가 있으면 protect_self 플래그 설정
        has_protect_effect = any(
            effect.__class__.__name__ == 'ProtectEffect' 
            for effect in self.effects
        )
        if has_protect_effect:
            context['protect_self'] = True  # ShieldEffect는 본인에게 적용
        
        # 공격력 기반 보호막 배율 설정 (metadata에서 가져오기)
        if self.metadata and 'attack_multiplier' in self.metadata:
            context['attack_multiplier'] = self.metadata['attack_multiplier']
        
        # 보호막 중첩 방지 설정 (metadata에서 가져오기)
        if self.metadata and 'replace_shield' in self.metadata:
            context['replace_shield'] = self.metadata['replace_shield']
        
        # 저격수 탄환 정보를 context에 추가 (데미지 계산 전에)
        if hasattr(user, 'gimmick_type') and user.gimmick_type == "magazine_system":
            if hasattr(user, 'magazine') and user.magazine:
                current_bullet = user.magazine[0]  # 다음 발사할 탄환
                if hasattr(user, 'bullet_types') and current_bullet in user.bullet_types:
                    bullet_info = user.bullet_types[current_bullet]
                    context['current_bullet'] = current_bullet
                    context['bullet_info'] = bullet_info
                    # 관통탄 방어 관통력 정보 전달
                    if 'defense_pierce_fixed' in bullet_info:
                        context['defense_pierce_fixed'] = bullet_info['defense_pierce_fixed']

        # 암흑기사 한정: 효과 실행 순서 조정 (CONSUME/SET 연산은 데미지 계산 후에 실행)
        # 충전 보너스가 데미지 계산에 반영되도록 하기 위함
        is_dark_knight = (hasattr(user, 'gimmick_type') and user.gimmick_type == "charge_system") or \
                        (hasattr(user, 'character_class') and 'dark_knight' in str(user.character_class).lower()) or \
                        (hasattr(user, 'job_id') and 'dark_knight' in str(user.job_id).lower())
        
        if is_dark_knight:
            from src.character.skills.effects.gimmick_effect import GimmickEffect, GimmickOperation
            
            # 효과를 두 그룹으로 분리: 데미지/힐 효과와 기믹 소모 효과
            damage_heal_effects = []
            gimmick_consume_effects = []
            
            for effect in self.effects:
                # CONSUME 또는 SET 연산인 GimmickEffect는 나중에 실행
                if isinstance(effect, GimmickEffect) and effect.operation in [GimmickOperation.CONSUME, GimmickOperation.SET]:
                    gimmick_consume_effects.append(effect)
                else:
                    damage_heal_effects.append(effect)
            
            # 먼저 데미지/힐 효과 실행 (충전 보너스가 적용됨)
            for effect in damage_heal_effects:
                if hasattr(effect, 'execute'):
                    result = effect.execute(user, target, context)
                    if hasattr(result, 'damage_dealt'):
                        total_dmg += result.damage_dealt
                    if hasattr(result, 'heal_amount'):
                        total_heal += result.heal_amount
                    # 효과 메시지 수집
                    if hasattr(result, 'message') and result.message:
                        effect_messages.append(result.message)
            
            # 그 다음 기믹 소모 효과 실행 (데미지 계산 후)
            for effect in gimmick_consume_effects:
                if hasattr(effect, 'execute'):
                    result = effect.execute(user, target, context)
                    # 효과 메시지 수집
                    if hasattr(result, 'message') and result.message:
                        effect_messages.append(result.message)
        else:
            # 다른 직업은 기존 순서대로 실행
            for effect in self.effects:
                if hasattr(effect, 'execute'):
                    result = effect.execute(user, target, context)
                    if hasattr(result, 'damage_dealt'):
                        total_dmg += result.damage_dealt
                    if hasattr(result, 'heal_amount'):
                        total_heal += result.heal_amount
                    # 효과 메시지 수집
                    if hasattr(result, 'message') and result.message:
                        effect_messages.append(result.message)

        # AOE 효과 실행 (적 전체 대상)
        if hasattr(self, 'aoe_effect') and self.aoe_effect:
            # context에서 모든 적 가져오기
            all_enemies = context.get('all_enemies', [])
            if all_enemies:
                # AOE 대상 결정: aoe_includes_main_target 플래그에 따라
                aoe_includes_main = getattr(self, 'aoe_includes_main_target', False)

                if aoe_includes_main:
                    # 모든 적에게 AOE 피해 (메인 타겟 포함)
                    aoe_targets = [e for e in all_enemies if hasattr(e, 'is_alive') and e.is_alive]
                else:
                    # 메인 타겟을 제외한 다른 적들에게 AOE 피해
                    aoe_targets = [e for e in all_enemies if e != target and hasattr(e, 'is_alive') and e.is_alive]

                if aoe_targets and hasattr(self.aoe_effect, 'execute'):
                    from src.core.logger import get_logger
                    logger = get_logger("skill")
                    logger.debug(f"AOE 효과 실행: {len(aoe_targets)}명 대상, 메인 타겟 포함={aoe_includes_main}")

                    aoe_result = self.aoe_effect.execute(user, aoe_targets, context)
                    if hasattr(aoe_result, 'damage_dealt'):
                        total_dmg += aoe_result.damage_dealt
                        logger.debug(f"AOE 피해: {aoe_result.damage_dealt}")

        # 스킬 메타데이터 및 특성 lifesteal 처리
        trait_lifesteal_rate = 0.0
        trait_manager = None  # 초기화
        # 특성 매니저 가져오기 (순환 참조 방지)
        try:
            from src.character.trait_effects import get_trait_effect_manager
            trait_manager = get_trait_effect_manager()
            # context에 스킬 정보 포함
            lifesteal_context = {'skill': self, 'target': target}
            trait_lifesteal_rate = trait_manager.calculate_lifesteal(user, **lifesteal_context)
        except ImportError:
            pass

        metadata_lifesteal_rate = 0.0
        if self.metadata and 'lifesteal' in self.metadata:
            rate = self.metadata.get('lifesteal')
            if isinstance(rate, (int, float)) and rate > 0:
                metadata_lifesteal_rate = rate

        total_lifesteal_rate = trait_lifesteal_rate + metadata_lifesteal_rate
        
        if total_lifesteal_rate > 0 and total_dmg > 0:
            # 흡혈 배율 적용
            multiplier = 1.0
            if trait_manager:
                 multiplier = trait_manager.calculate_lifesteal_multiplier(user)
            
            lifesteal_amount = int(total_dmg * total_lifesteal_rate * multiplier)
            
            if lifesteal_amount > 0:
                if hasattr(user, 'heal'):
                    actual_heal = user.heal(lifesteal_amount)
                    total_heal += actual_heal
                    
                    msg = f"생명력 흡수 +{actual_heal}"
                    
                    # Vitality Overflow Logic (Duplicate of LifestealEffect logic, but needed here for metadata/trait lifesteal)
                    has_overflow = False
                    if hasattr(user, 'active_traits') and 'vitality_overflow' in user.active_traits:
                        has_overflow = True
                    elif hasattr(user, 'system_traits') and 'vitality_overflow' in user.system_traits:
                        has_overflow = True
                        
                    if has_overflow:
                        overheal = lifesteal_amount - actual_heal
                        if overheal > 0 and hasattr(user, 'current_brv') and hasattr(user, 'max_brv'):
                            old_brv = user.current_brv
                            user.current_brv = min(user.current_brv + overheal, user.max_brv)
                            brv_gain = user.current_brv - old_brv
                            if brv_gain > 0:
                                msg += f", BRV 전환 +{brv_gain}"

                    from src.core.logger import get_logger
                    logger = get_logger("skill")
                    logger.info(f"[생명력 흡수] {user.name} HP 회복: +{actual_heal} (피해의 {total_lifesteal_rate * multiplier * 100:.0f}%)")
                    effect_messages.append(msg)

        # 최종 메시지 구성 (ISSUE-003: 상세 피드백)
        base_message = f"{user.name}이(가) {self.name} 사용!"
        if effect_messages:
            full_message = base_message + "\n  → " + "\n  → ".join(effect_messages)
        else:
            full_message = base_message

        return SkillResult(
            success=True,
            message=full_message,
            total_damage=total_dmg,
            total_heal=total_heal
        )

    def get_description(self, user: Any) -> str:
        """스킬 설명"""
        parts = [self.description]
        if self.costs:
            cost_strs = [getattr(c, 'get_description', lambda u: "")(user) for c in self.costs]
            parts.append(f"비용: {', '.join([c for c in cost_strs if c])}")
        # 쿨다운 시스템 제거됨
        # if self.cooldown > 0:
        #     parts.append(f"쿨다운: {self.cooldown}턴")
        return " | ".join(parts)

    def __repr__(self) -> str:
        return f"Skill({self.name})"
