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

        # 비용 소비
        for cost in self.costs:
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

        # 스킬 메타데이터의 lifesteal 처리 (흡혈귀 등)
        if self.metadata and 'lifesteal' in self.metadata:
            lifesteal_rate = self.metadata.get('lifesteal')
            if lifesteal_rate and total_dmg > 0:
                # lifesteal_rate가 숫자인 경우 (비율)
                if isinstance(lifesteal_rate, (int, float)) and lifesteal_rate > 0:
                    heal_amount = int(total_dmg * lifesteal_rate)
                    if heal_amount > 0:
                        if hasattr(user, 'heal'):
                            actual_heal = user.heal(heal_amount)
                            total_heal += actual_heal
                            from src.core.logger import get_logger
                            logger = get_logger("skill")
                            logger.info(f"[생명력 흡수] {user.name} HP 회복: +{actual_heal} (피해의 {lifesteal_rate * 100:.0f}%)")
                            effect_messages.append(f"생명력 흡수 +{actual_heal}")

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
