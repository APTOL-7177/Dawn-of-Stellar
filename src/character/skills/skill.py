"""Skill - 스킬 클래스"""
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import random

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
        self.triggers_chain: bool = False  # True면 사용 후 체인어빌리티 트리거

    def can_use(self, user: Any, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """스킬 사용 가능 여부"""
        context = context or {}
        # 스킬 정보를 context에 추가 (특성 효과 적용을 위해)
        context['skill'] = self
        
        # 직접 스턴 상태 체크
        if hasattr(user, 'is_stunned') and user.is_stunned:
            return False, "스턴 상태로 스킬을 사용할 수 없습니다"
        
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
        
        # 정령 중복 소환 선차단 (t_98b95a46 D3): 비용 차감 전에 거절한다.
        # execute가 _apply_variant_selection 이후 can_use를 호출하므로
        # 변형 병합된 metadata.spirit_type을 안전하게 읽을 수 있다.
        if self.metadata.get("requires_unsummoned_spirit"):
            spirit = str(self.metadata.get("spirit_type") or "")
            if spirit not in ("fire", "water", "wind", "earth"):
                return False, "정령 변형 정보 오류"
            if getattr(user, f"spirit_{spirit}", 0) > 0:
                return False, "이미 소환된 정령입니다"

        # 비용 체크 (가능성 소환 등에서 skip_cost가 설정되면 건너뛰기)
        if not (context and context.get('skip_cost')):
            for cost in self.costs:
                can_afford, reason = cost.can_afford(user, context)
                if not can_afford:
                    return False, reason
        
        # 메타데이터 기반 조건 체크
        if self.metadata:
            # 수호자 자세 필수 스킬 체크 (전사)
            if self.metadata.get("requires_guardian_stance"):
                current_stance = getattr(user, "current_stance", 0)
                # 문자열/정수 모두 지원
                is_guardian = current_stance == 5 or current_stance == "guardian"
                if not is_guardian:
                    return False, "수호자 자세에서만 사용 가능합니다"

            # 은신 필수 스킬 체크 (도적/암살자 등)
            if self.metadata.get("requires_stealth"):
                in_stealth = getattr(user, "stealth_active", False)
                if hasattr(user, "status_manager") and hasattr(user.status_manager, "has_stealth"):
                    try:
                        in_stealth = in_stealth or user.status_manager.has_stealth()
                    except Exception:
                        # 상태 매니저 예외 시 속성 기반만 사용
                        pass
                if not in_stealth:
                    return False, "은신 상태가 필요합니다"

            # 차원술사: 굴절량 필요
            if self.metadata.get("requires_refraction_check"):
                current_refraction = getattr(user, "refraction_stacks", 0)
                if current_refraction <= 0:
                    return False, "굴절이 필요합니다"

            # 정령술사: 활성 정령 수량 체크
            if self.metadata.get("requires_spirits"):
                required_spirits = int(self.metadata.get("requires_spirits", 1))
                current_spirits = 0
                for spirit_attr in ("spirit_fire", "spirit_water", "spirit_wind", "spirit_earth"):
                    current_spirits += getattr(user, spirit_attr, 0)
                if current_spirits < required_spirits:
                    return False, f"정령 {required_spirits}마리 이상 필요 (현재: {current_spirits})"

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
            
            # 해커: RAM 부족 체크
            if hasattr(user, 'gimmick_type') and user.gimmick_type == "intrusion_system":
                ram_cost = int(self.metadata.get('ram_cost', 0) or 0)
                if ram_cost > 0:
                    # 오버클럭 할인 적용
                    if getattr(user, 'overclock_active', False):
                        discount = int(getattr(user, 'overclock_data', {}).get('ram_cost_discount', 0))
                        ram_cost = max(0, ram_cost - discount)
                    current_ram = getattr(user, 'ram', 0)
                    if current_ram < ram_cost:
                        return False, f"RAM 부족 (필요: {ram_cost}, 보유: {current_ram})"

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
                # 새 형식: fusion=True, requires=["fire", "wind"]
                if self.metadata.get("fusion", False) and self.metadata.get("requires"):
                    requires = self.metadata.get("requires", [])
                    spirit_map = {
                        "fire": ("spirit_fire", "화염 정령"),
                        "water": ("spirit_water", "물 정령"),
                        "wind": ("spirit_wind", "바람 정령"),
                        "earth": ("spirit_earth", "대지 정령")
                    }
                    
                    missing_spirits = []
                    for spirit_type in requires:
                        if spirit_type in spirit_map:
                            attr_name, display_name = spirit_map[spirit_type]
                            if getattr(user, attr_name, 0) == 0:
                                missing_spirits.append(display_name)
                    
                    if missing_spirits:
                        return False, f"융합 스킬 사용 불가: {', '.join(missing_spirits)} 소환 필요"
                
                # 구 형식 호환: requires_both_spirits + fusion="fire_wind"
                elif self.metadata.get("requires_both_spirits", False):
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

                    # 소환 핸들러에서 교체를 처리하므로, 최대치라도 다른 종류 소환을 막지 않음

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
            
            # 차원술사: 굴절 소모 스킬 조건 체크
            if hasattr(user, 'gimmick_type') and user.gimmick_type == "dimension_refraction":
                refraction_stacks = getattr(user, 'refraction_stacks', 0)
                
                # 굴절량 비율 소모 (refraction_consumption) - 현재 굴절량의 비율만큼 소모
                if "refraction_consumption" in self.metadata:
                    consumption_rate = self.metadata.get("refraction_consumption", 0)
                    # 굴절량이 0이면 사용 불가
                    if refraction_stacks <= 0:
                        return False, f"굴절량 부족 (현재: {refraction_stacks})"
                    # 비율만큼 소모 가능한지 확인 (최소 1 이상 필요)
                    required_refraction = max(1, int(refraction_stacks * consumption_rate))
                    if refraction_stacks < required_refraction:
                        return False, f"굴절량 부족 (필요: {required_refraction}, 현재: {refraction_stacks})"
                
                # 최대 HP 비율만큼 굴절량 소모 (refraction_cost_hp_percent)
                if "refraction_cost_hp_percent" in self.metadata:
                    max_hp = getattr(user, 'max_hp', 100)
                    required_refraction = int(max_hp * self.metadata.get("refraction_cost_hp_percent", 0))
                    if refraction_stacks < required_refraction:
                        return False, f"굴절량 부족 (필요: {required_refraction}, 현재: {refraction_stacks})"
                
                # 굴절량 비율 자해 (self_damage_refraction_percent) - 현재 굴절량의 비율만큼 자해
                if "self_damage_refraction_percent" in self.metadata:
                    damage_rate = self.metadata.get("self_damage_refraction_percent", 0)
                    # 굴절량이 0이면 사용 불가
                    if refraction_stacks <= 0:
                        return False, f"굴절량 부족 (현재: {refraction_stacks})"
                    # 비율만큼 소모 가능한지 확인 (최소 1 이상 필요)
                    required_refraction = max(1, int(refraction_stacks * damage_rate))
                    if refraction_stacks < required_refraction:
                        return False, f"굴절량 부족 (필요: {required_refraction}, 현재: {refraction_stacks})"
                
                # 모든 굴절량 소모 (consume_all_refraction)
                if self.metadata.get("consume_all_refraction", False):
                    if refraction_stacks <= 0:
                        return False, f"굴절량 부족 (현재: {refraction_stacks})"
            
            # 닌자 해인: 인(印) 요구 체크 (D2, t_082c6a99)
            if self.metadata.get("ninpo_burst") or self.metadata.get("requires_seals"):
                total_seals = sum(
                    int(getattr(user, f"seal_{e}", 0) or 0) for e in ("fire", "ice", "thunder", "wind")
                )
                required_seals = int(self.metadata.get("requires_seals", 0) or 0)
                if total_seals < required_seals:
                    return False, f"인(印) {required_seals}개 이상 필요 (현재: {total_seals})"

            # 시간술사: 타임라인 조건 체크
            if hasattr(user, 'gimmick_type') and user.gimmick_type == "timeline_system":
                if "requires_timeline" in self.metadata:
                    required_timeline = self.metadata.get("requires_timeline")
                    current_timeline = getattr(user, 'timeline', 0)
                    if current_timeline != required_timeline:
                        return False, f"타임라인 {required_timeline}에서만 사용 가능합니다 (현재: {current_timeline})"
            
            # 아크메이지: 원소 스택 최소값 조건 체크 (원소 장막 등)
            if hasattr(user, 'gimmick_type') and user.gimmick_type == "elemental_fusion":
                if "min_total_stacks" in self.metadata:
                    required_stacks = self.metadata.get("min_total_stacks", 0)
                    fire_stacks = getattr(user, 'fire_element', 0)
                    ice_stacks = getattr(user, 'ice_element', 0)
                    lightning_stacks = getattr(user, 'lightning_element', 0)
                    total_stacks = fire_stacks + ice_stacks + lightning_stacks

                    if total_stacks < required_stacks:
                        return False, f"원소 스택 부족 (필요: {required_stacks}, 현재: {total_stacks})"

            # 마술사: 트릭 덱 조건 체크
            if hasattr(user, 'gimmick_type') and user.gimmick_type == "trick_deck":
                hand = getattr(user, 'card_hand', [])

                # 포커 조합 필요 스킬
                if "required_combination" in self.metadata:
                    required_combo = self.metadata.get("required_combination")
                    from src.character.skills.job_skills.magician_skills import check_poker_combination
                    current_combo, combo_cards, score = check_poker_combination(hand)
                    
                    # 조합 순위 (높을수록 좋음)
                    combo_ranks = {
                        "pair": 1,
                        "two_pair": 2,
                        "triple": 3,
                        "straight": 4,
                        "flush": 5,
                        "full_house": 6,
                        "four_of_kind": 7,
                        "straight_flush": 8,
                        "royal_straight_flush": 9
                    }
                    required_rank = combo_ranks.get(required_combo, 0)
                    current_rank = combo_ranks.get(current_combo, 0)
                    
                    # 현재 조합이 필요 조합보다 낮으면 사용 불가
                    if current_rank < required_rank:
                        combo_names = {
                            "pair": "원페어",
                            "two_pair": "투페어",
                            "triple": "트리플",
                            "straight": "스트레이트",
                            "flush": "플러시",
                            "full_house": "풀하우스",
                            "four_of_kind": "포카드",
                            "straight_flush": "스트레이트 플러시",
                            "royal_straight_flush": "로얄 스트레이트 플러시"
                        }
                        required_name = combo_names.get(required_combo, required_combo)
                        current_name = combo_names.get(current_combo, "없음") if current_combo else "없음"
                        return False, f"{required_name} 조합이 필요합니다 (현재: {current_name})"
                
                # 같은 무늬 카드 필요 스킬
                if "required_same_suit" in self.metadata:
                    required_count = self.metadata.get("required_same_suit")
                    suit_groups = {}
                    for card in hand:
                        if not card.get('is_joker'):
                            suit = card.get('suit')
                            if suit not in suit_groups:
                                suit_groups[suit] = 0
                            suit_groups[suit] += 1
                    
                    max_same_suit = max(suit_groups.values()) if suit_groups else 0
                    joker_count = sum(1 for c in hand if c.get('is_joker'))
                    
                    if max_same_suit + joker_count < required_count:
                        return False, f"같은 무늬 카드 {required_count}장이 필요합니다 (현재 최대: {max_same_suit}장)"
                
                # 특정 숫자 카드 필요 스킬
                if "required_rank" in self.metadata:
                    required_rank = self.metadata.get("required_rank")
                    has_required = any(c.get('rank') == required_rank for c in hand if not c.get('is_joker'))
                    has_joker = any(c.get('is_joker') for c in hand)
                    
                    if not has_required and not has_joker:
                        return False, f"{required_rank} 카드가 필요합니다"
                
                # 조커 필요 스킬
                if self.metadata.get("required_joker"):
                    has_joker = any(c.get('is_joker') for c in hand)
                    if not has_joker:
                        return False, "조커 카드가 필요합니다"
                
                # 손패에서 카드 선택이 필요한 스킬 (에이스 인 더 홀 등)
                # _card_processed가 True면 이미 gimmick_updater에서 처리됨
                if self.metadata.get("select_card_from_hand") and not self.metadata.get("_card_processed"):
                    if not hand:
                        return False, "손패가 비어있습니다"
        
        return True, ""

    # 실행 시점에만 임시 주입하고 실행 후 반드시 복원할 메타데이터 오버라이드 키
    # (싱글톤 공유 Skill 인스턴스의 상태 오염 방지, t_83d83e83)
    _VARIANT_OVERRIDE_KEYS = ("atb_boost", "party_atb_boost", "seal_type", "element", "spirit_type")

    def _apply_variant_selection(self, context: Optional[Dict[str, Any]]) -> None:
        """variants 파생 프리미티브 실행 시점 병합 (t_082c6a99).

        - metadata['_selected_variant'] (또는 variant_default)를 읽어
          variant_options[key]['metadata_override']를 self.metadata에 병합하고,
          base damage effect에 element 주입, 변형 전용 효과만 활성화한다.
        - metadata와 effects는 스킬 단일 인스턴스가 전투 참가자 간 공유되므로
          변경은 context['_variant_snapshot']에 스냅샷으로 기록하고,
          execute 종료 시 _restore_variant_state()에서 복원한다(비-mutating, t_83d83e83).
        """
        meta = getattr(self, "metadata", None)
        if not meta or not meta.get("variant_capable"):
            return
        options = meta.get("variant_options") or {}
        if not options:
            return

        key = meta.get("_selected_variant") or meta.get("variant_default")
        meta.pop("_selected_variant", None)  # 1회성 선택값 정리
        if key not in options:
            key = meta.get("variant_default")
        if key not in options:
            return

        entry = options[key]

        # 스냅샷: 실행 후 복원할 이전 값 기록 (오염 방지, t_83d83e83)
        if context is not None:
            snapshot = context.setdefault("_variant_snapshot", {})
            snapshot["_active_variant"] = meta.get("_active_variant")
            snapshot["_effects"] = [
                (effect, getattr(effect, "element", None)) for effect in self.effects
            ]

        meta["_active_variant"] = key

        # 1) metadata_override 병합 (seal_type/element/atb_boost 등) — 스냅샷에 이전값 기록
        override = entry.get("metadata_override") or {}
        if context is not None:
            snapshot = context.setdefault("_variant_snapshot", {})
            for k in self._VARIANT_OVERRIDE_KEYS:
                if k in override:
                    snapshot[k] = meta.get(k)  # 복원용 이전 값 (없으면 None)

        for k, v in override.items():
            meta[k] = v

        # 1b) 변형별 비용 오버라이드 (t_98b95a46 엔지니어 터렛): 실행/검증 시
        # MPCost가 읽도록 metadata에 기록하고 복원 대상에 포함한다.
        costs_override = entry.get("costs_override")
        if costs_override:
            if context is not None:
                snapshot = context.setdefault("_variant_snapshot", {})
                snapshot["_variant_cost_override"] = meta.get("_variant_cost_override")
            meta["_variant_cost_override"] = dict(costs_override)

        # 2) base damage effect에 element 주입 — 실행 시점에만, 종료 시 복원
        element = override.get("element")
        variant_filter = meta.get("_variant_filter") or {}
        variant_effect_idx = set(variant_filter.get(key, []))
        if element:
            for idx, effect in enumerate(self.effects):
                if idx in variant_effect_idx:
                    continue  # 변형 전용 효과는 필터 대상
                if hasattr(effect, "element"):
                    try:
                        effect.element = element
                    except Exception:
                        pass

        # 3) 실행 허용 인덱스 = base 효과(변형 전용 제외) + 선택 변형 전용 효과
        if context is not None and variant_filter:
            all_variant_idx = {i for idxs in variant_filter.values() for i in idxs}
            allowed = {i for i in range(len(self.effects)) if i not in all_variant_idx}
            allowed |= variant_effect_idx
            context["_variant_active_effect_idx"] = allowed
            context["_variant_label"] = entry.get("label", key)

    def _restore_variant_state(self, context: Optional[Dict[str, Any]]) -> None:
        """execute 종료(성공/실패 무관) 시 변형 실행 상태를 복원한다 (t_83d83e83).

        - metadata_override 키(atb_boost/seal_type/element 등)를 스냅샷 값으로 복원
        - damage effect에 주입했던 element를 원래 값으로 복원
        - _active_variant 제거
        """
        if not context:
            return
        snapshot = context.pop("_variant_snapshot", None)
        context.pop("_variant_active_effect_idx", None)
        context.pop("_variant_label", None)
        if not snapshot:
            return

        meta = getattr(self, "metadata", None) or {}
        # 실행 시점 effective 오버라이드를 context에 남긴다 —
        # SKILL_EXECUTE 등 execute 종료 후 소비자는 여기서 읽는다 (t_83d83e83)
        effective = {}
        for k in self._VARIANT_OVERRIDE_KEYS:
            if k in meta and k in snapshot:
                effective[k] = meta[k]
        if effective and context is not None:
            context["_variant_meta"] = effective

        for k in self._VARIANT_OVERRIDE_KEYS:
            if k in snapshot:
                if snapshot[k] is None:
                    meta.pop(k, None)
                else:
                    meta[k] = snapshot[k]
        if "_variant_cost_override" in snapshot:
            if snapshot["_variant_cost_override"] is None:
                meta.pop("_variant_cost_override", None)
            else:
                meta["_variant_cost_override"] = snapshot["_variant_cost_override"]
        meta.pop("_active_variant", None)

        for effect, original_element in snapshot.get("_effects", []):
            if hasattr(effect, "element"):
                try:
                    effect.element = original_element
                except Exception:
                    pass

    def execute(self, user: Any, target: Any, context: Optional[Dict[str, Any]] = None) -> SkillResult:
        """스킬 실행"""
        context = context or {}
        # 스킬 정보를 context에 추가 (특성 효과 적용을 위해)
        context['skill'] = self
        if hasattr(self, "metadata") and self.metadata:
            if "_selected_choice" in self.metadata and "selected_choice" not in context:
                context["selected_choice"] = self.metadata.get("_selected_choice")
                if "_selected_choice_name" in self.metadata:
                    context["selected_choice_name"] = self.metadata.get("_selected_choice_name")

            # variants 파생 프리미티브 (t_082c6a99): 선택 변형 적용
            self._apply_variant_selection(context)

            # 부활 스킬인 경우 컨텍스트에 표시 (죽은 대상 타겟팅 허용)
            if self.metadata.get("revival"):
                context["revival"] = True

        # 과부하 활성 시 컨텍스트 배율 전달 (피해 강화)
        overload_active = False
        if self.metadata.get("overload_capable") and self.metadata.get("_use_overload"):
            overload_active = True
            context['overload_active'] = True
            ov_mult = self.metadata.get("overload_damage_multiplier", 1.2)
            # 기존 power_multiplier와 곱연산
            if 'power_multiplier' in context:
                context['power_multiplier'] *= ov_mult
            else:
                context['power_multiplier'] = ov_mult

        # 기적 스킬 신앙 요구/소모 처리 (YAML: requires_faith, consumes_faith)
        meta = getattr(self, "metadata", {}) or {}
        if meta.get("miracle"):
            from src.character.gimmick_updater import GimmickUpdater
            required_faith = meta.get("requires_faith", 0)
            consumes_faith = meta.get("consumes_faith", 0)

            # 신앙 자원 필드 결정 (paladin: faith, priest: faith_points)
            faith_field = "faith"
            if hasattr(user, "faith_points"):
                faith_field = "faith_points"

            current_faith = getattr(user, faith_field, 0)

            # 요구치 미달 시 실패 처리
            if required_faith and current_faith < required_faith:
                return SkillResult(success=False, message=f"신앙 {required_faith} 이상 필요")

            # 성공 시 신앙 소모 (effects 실행 후에도 유지)
            context.setdefault("_consume_faith_after", 0)
            if consumes_faith:
                context["_consume_faith_after"] = (consumes_faith, faith_field)

        can_use, reason = self.can_use(user, context)
        # 변형 적용 후 모든 경로(성공/실패)에서 상태 복원 보장 (t_83d83e83)
        try:
            result = self._execute_variant_scoped(user, target, context, can_use, reason)
            return result
        finally:
            self._restore_variant_state(context)

    def _execute_variant_scoped(self, user, target, context, can_use, reason) -> SkillResult:
        """execute 본문 (변형 스코프) — _restore_variant_state 보장 하에 실행."""
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

        # target_type이 "party"인 경우 (팀워크 스킬 등), 아군 전체 가져오기
        if hasattr(self, 'target_type') and self.target_type == "party":
            combat_manager = context.get('combat_manager')
            party = context.get('party')
            if combat_manager:
                # 아군 전체를 타겟으로 설정
                if hasattr(combat_manager, 'allies') and user in getattr(combat_manager, 'allies', []):
                    target = [ally for ally in getattr(combat_manager, 'allies', []) if getattr(ally, 'is_alive', True)]
                else:
                    target = getattr(combat_manager, 'allies', [])
            elif party:
                # party 객체에서 멤버 가져오기
                if hasattr(party, 'members'):
                    target = [m for m in party.members if getattr(m, 'is_alive', True)]
                elif hasattr(party, '__iter__'):
                    target = [m for m in party if getattr(m, 'is_alive', True)]
                else:
                    target = [target] if target else []
            elif isinstance(target, list):
                pass
            else:
                target = [target] if target else []

        # 비용 소비 (가능성 소환 등에서 skip_cost가 설정되면 건너뛰기)
        stack_costs = []
        if not context.get('skip_cost'):
            # 스냅샷 컨텍스트가 있으면 캐스팅 완료 후이므로 StackCost 건너뛰기
            # (스택은 effects의 GimmickEffect.CONSUME에서 처리)
            has_snapshot = 'snapshot_context' in context
            is_dark_knight_for_cost = (hasattr(user, 'gimmick_type') and user.gimmick_type == "charge_system") or \
                                      (hasattr(user, 'character_class') and 'dark_knight' in str(user.character_class).lower()) or \
                                      (hasattr(user, 'job_id') and 'dark_knight' in str(user.job_id).lower())
            is_sword_saint_for_cost = (hasattr(user, 'gimmick_type') and user.gimmick_type == "sword_aura") or \
                                      (hasattr(user, 'character_class') and 'sword_saint' in str(user.character_class).lower()) or \
                                      (hasattr(user, 'job_id') and 'sword_saint' in str(user.job_id).lower())

            # StackCost를 제외한 다른 비용들 먼저 소비
            non_stack_costs = []

            for cost in self.costs:
                from src.character.skills.costs.stack_cost import StackCost
                if isinstance(cost, StackCost):
                    stack_costs.append(cost)
                else:
                    non_stack_costs.append(cost)

            # StackCost가 아닌 비용들 먼저 소비
            for cost in non_stack_costs:
                if not cost.consume(user, context):
                    return SkillResult(success=False, message="비용 소비 실패")
        
        # StackCost는 스킬 효과 실행 후에 소모할 예정 (검성, 암흑기사 제외)
        # 검성과 암흑기사는 효과 실행 후에 StackCost를 소모함

        # 마술사 카드 소모는 execute_magician_skill()에서 일괄 처리
        # (여기서 소모하면 execute_magician_skill에서 조합 재검증 시 이미 소모된 카드로 인해 실패)

        # 배틀메이지 랜덤 룬 처리
        if hasattr(user, 'gimmick_type') and user.gimmick_type == "rune_resonance":
            if self.metadata and self.metadata.get('random_rune_gain'):
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

        # 커스텀 데미지 처리 (차원 폭발 등) - effects 실행 전에 굴절량 저장
        custom_damage_refraction = None
        if self.metadata.get("custom_damage", False) and "refraction_consumption" in self.metadata:
            # 굴절량 소모 전 값을 저장 (고정 피해 계산용)
            if hasattr(user, 'gimmick_type') and user.gimmick_type == "dimension_refraction":
                custom_damage_refraction = getattr(user, 'refraction_stacks', 0)

        # 기믹 선처리 (룬 각인 등)
        pre_hook = {}
        try:
            if hasattr(user, "gimmick_type"):
                from src.character.gimmick_updater import GimmickUpdater
                pre_hook = GimmickUpdater.pre_skill_execution(user, self, target, context)
        except Exception:
            logger = get_logger("skill")
            logger.warning(f"[기믹 선처리 실패] {getattr(user, 'name', '?')} / {self.name}", exc_info=True)

        # 효과 실행 준비 (ISSUE-003: 효과 메시지 수집)
        total_dmg = 0
        total_heal = 0
        effect_messages = []  # 각 효과의 메시지 수집

        # 마술사 특수 스킬 처리
        if hasattr(user, 'gimmick_type') and user.gimmick_type == "trick_deck":
            from src.character.skills.job_skills.magician_skills import execute_magician_skill
            magician_result = execute_magician_skill(user, self, target, context)
            if not magician_result.get('success', True):
                return SkillResult(success=False, message="마술사 스킬 실행 실패")

            # 마술사 스킬 결과 처리
            for msg in magician_result.get('results', []):
                effect_messages.append(msg)

            # 보너스 배율 적용
            bonus_multiplier = magician_result.get('bonus_multiplier', 1.0)
            if bonus_multiplier != 1.0:
                context['bonus_multiplier'] = bonus_multiplier

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
                        total_dmg += result.damage_dealt if isinstance(result.damage_dealt, (int, float)) else 0
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
            variant_active_idx = context.get('_variant_active_effect_idx') if context else None
            for effect_idx, effect in enumerate(self.effects):
                # variants 프리미티브: 선택 변형의 전용 효과만 실행 (t_082c6a99)
                if variant_active_idx is not None and effect_idx not in variant_active_idx:
                    continue
                if hasattr(effect, 'execute'):
                    result = effect.execute(user, target, context)
                    if hasattr(result, 'damage_dealt'):
                        total_dmg += result.damage_dealt if isinstance(result.damage_dealt, (int, float)) else 0
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
                        total_dmg += aoe_result.damage_dealt if isinstance(aoe_result.damage_dealt, (int, float)) else 0
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

        # 커스텀 데미지 처리 (차원 폭발 등)
        if self.metadata.get("custom_damage", False) and custom_damage_refraction is not None:
            # 굴절량 소모량 계산
            consumption_rate = self.metadata.get("refraction_consumption", 0)
            consumed_refraction = int(custom_damage_refraction * consumption_rate)
            
            # 고정 피해 배율 적용
            fixed_damage_multiplier = self.metadata.get("fixed_damage_multiplier", 1.0)
            fixed_damage = int(consumed_refraction * fixed_damage_multiplier)

            # 고정 피해 증폭 특성 확인 (차원술사)
            if hasattr(user, 'active_traits'):
                has_amplification = any(
                    (t if isinstance(t, str) else t.get('id')) == 'fixed_damage_amplification'
                    for t in user.active_traits
                )
                if has_amplification:
                    fixed_damage = int(fixed_damage * 1.5)  # 고정 피해 +50%
                    from src.core.logger import get_logger
                    logger_temp = get_logger("skill")
                    logger_temp.debug(f"[고정 피해 증폭] {user.name} 차원 폭발 피해: {fixed_damage} (+50%)")

            # 적 전체에게 고정 피해 적용
            from src.character.skills.effects.fixed_damage_effect import FixedDamageEffect
            targets_list = target if isinstance(target, list) else [target]
            alive_targets = [t for t in targets_list if hasattr(t, 'is_alive') and t.is_alive]
            
            if alive_targets and fixed_damage > 0:
                from src.core.logger import get_logger
                logger = get_logger("skill")
                
                for enemy in alive_targets:
                    # 고정 피해 적용
                    if hasattr(enemy, 'take_fixed_damage'):
                        actual_damage = enemy.take_fixed_damage(fixed_damage)
                    else:
                        actual_damage = min(fixed_damage, enemy.current_hp)
                        enemy.current_hp = max(0, enemy.current_hp - fixed_damage)
                    
                    logger.info(f"[차원 폭발] {user.name} → {enemy.name} 고정 피해: {actual_damage} (굴절량 {consumed_refraction} × {fixed_damage_multiplier})")
                    total_dmg += actual_damage
                
                if len(alive_targets) > 1:
                    effect_messages.append(f"적 전체 고정 피해 {fixed_damage} × {len(alive_targets)}명")
                else:
                    effect_messages.append(f"고정 피해 {fixed_damage}")

        # 커스텀 효과 처리 (차원술사 굴절 전환 등)
        if self.metadata.get("custom_effect", False):
            # 자해 피해 처리 (self_damage_hp_percent)
            if "self_damage_hp_percent" in self.metadata:
                damage_percent = self.metadata.get("self_damage_hp_percent", 0)
                max_hp = getattr(user, 'max_hp', 100)
                current_hp_before = getattr(user, 'current_hp', max_hp)
                self_damage = int(max_hp * damage_percent)

                # 굴절 전환: HP 소모 **전**에 HP 퍼센트 계산 (low_hp_efficiency_bonus)
                multiplier = 1.0
                if "refraction_gain_multiplier" in self.metadata:
                    base_multiplier = self.metadata.get("refraction_gain_multiplier", 1.0)
                    multiplier = base_multiplier

                    # HP가 낮을수록 효율 증가 (low_hp_efficiency_bonus)
                    if self.metadata.get("low_hp_efficiency_bonus", False):
                        hp_percent = current_hp_before / max_hp if max_hp > 0 else 1.0

                        max_efficiency_hp = self.metadata.get("max_efficiency_at_hp_percent", 0.5)  # 50%
                        max_efficiency_mult = self.metadata.get("max_efficiency_multiplier", 1.5)

                        # HP 100% ~ 50%: 1.0배 ~ max_efficiency_mult배 (선형 보간)
                        # HP 50% 이하: 최대 max_efficiency_mult배
                        if hp_percent <= max_efficiency_hp:
                            efficiency_bonus = max_efficiency_mult
                        else:
                            # 100% HP에서 1.0배, 50% HP에서 max_efficiency_mult배
                            t = (hp_percent - max_efficiency_hp) / (1.0 - max_efficiency_hp)
                            efficiency_bonus = max_efficiency_mult - t * (max_efficiency_mult - 1.0)

                        multiplier = base_multiplier * efficiency_bonus

                        from src.core.logger import get_logger
                        logger = get_logger("skill")
                        logger.info(f"[굴절 전환] HP {hp_percent*100:.0f}% → base {base_multiplier}배 × 효율 {efficiency_bonus:.2f}배 = {multiplier:.2f}배")

                # 고정 피해로 적용 (방어력 무시)
                if hasattr(user, 'take_fixed_damage'):
                    actual_damage = user.take_fixed_damage(self_damage)
                else:
                    # take_fixed_damage가 없으면 직접 HP 감소
                    actual_damage = min(self_damage, current_hp_before - 1)  # 최소 1 HP 보장
                    user.current_hp = max(1, current_hp_before - actual_damage)

                from src.core.logger import get_logger
                logger = get_logger("skill")
                logger.info(f"[자해] {user.name} 고정 피해: {actual_damage} (최대 HP의 {damage_percent * 100:.0f}%)")
                effect_messages.append(f"자해 피해 {actual_damage}")
                total_dmg += actual_damage  # 자해 피해도 total_damage에 포함

                # 굴절량 획득 (actual_damage 기반)
                if "refraction_gain_multiplier" in self.metadata:
                    refraction_gain = int(actual_damage * multiplier)
                    if not hasattr(user, 'refraction_stacks'):
                        user.refraction_stacks = 0
                    user.refraction_stacks += refraction_gain
                    logger.info(f"[굴절 전환] {user.name} 굴절량 획득: +{refraction_gain} (자해 {actual_damage} × {multiplier:.2f}배, 총: {user.refraction_stacks})")
                    effect_messages.append(f"굴절량 +{refraction_gain}")

        # ===== 탱크 방어 스킬: damage_reduction 메타데이터를 버프로 적용 =====
        if self.metadata.get("tank_skill") and self.metadata.get("damage_reduction"):
            reduction_value = self.metadata["damage_reduction"]
            duration = 3  # 기본 3턴
            skill_id = self.skill_id
            
            # target이 "self"면 user에게, 아니면 target에게 적용
            buff_target = user if self.target_type == "self" else target
            if isinstance(buff_target, list):
                buff_target = buff_target[0] if buff_target else user
            
            if buff_target and getattr(buff_target, 'is_alive', True):
                if not hasattr(buff_target, 'active_buffs'):
                    buff_target.active_buffs = {}
                
                # 스킬 ID를 키로 사용하여 피해 경감 버프 적용
                buff_target.active_buffs[skill_id] = {
                    'value': reduction_value,
                    'duration': duration,
                    'damage_reduction': reduction_value,  # take_damage에서 사용
                    'remove_on_stance_change': self.metadata.get('remove_on_stance_change', False)
                }
                
                from src.core.logger import get_logger
                logger = get_logger("skill")
                logger.info(f"[탱크 스킬] {buff_target.name}에게 피해 경감 {int(reduction_value*100)}% 적용 ({duration}턴)")
                effect_messages.append(f"피해 경감 {int(reduction_value*100)}% ({duration}턴)")

        # 차원 보호막 버프 적용 (damage_reduction 메타데이터)
        if self.metadata.get("damage_reduction") and self.metadata.get("redirect_reduced_to_refraction"):
            reduction_value = self.metadata.get("damage_reduction", 0.40)
            duration = 2  # 기본 2턴
            
            # 타겟에게 dimension_barrier 버프 적용 (시전자 정보 포함)
            targets_list = target if isinstance(target, list) else [target]
            # AOE 스킬인 경우 아군 전체
            if self.is_aoe and self.target_type == "all_allies":
                targets_list = context.get('all_allies', targets_list) if context else targets_list
            
            for t in targets_list:
                if not getattr(t, 'is_alive', True):
                    continue
                if not hasattr(t, 'active_buffs'):
                    t.active_buffs = {}
                t.active_buffs['dimension_barrier'] = {
                    'value': reduction_value,
                    'duration': duration,
                    'source': user,  # 차원술사 정보 저장
                    'redirect_to_refraction': True
                }
            
            from src.core.logger import get_logger
            logger = get_logger("skill")
            logger.info(f"[차원 보호막] {user.name}이(가) 아군에게 피해 경감 {int(reduction_value*100)}% 부여 ({duration}턴)")
            effect_messages.append(f"피해 경감 {int(reduction_value*100)}% ({duration}턴)")

        # 기믹 후처리 (Arc Spark, 룬 폭발 등)
        try:
            if hasattr(user, "gimmick_type"):
                from src.character.gimmick_updater import GimmickUpdater
                post_result = GimmickUpdater.post_skill_execution(user, self, target, context, pre_hook, total_damage=total_dmg)
                if post_result:
                    total_dmg += post_result.get("extra_damage", 0)
                    total_heal += post_result.get("extra_heal", 0)
                    effect_messages.extend(post_result.get("messages", []))
        except Exception:
            logger = get_logger("skill")
            logger.warning(f"[기믹 후처리 실패] {getattr(user, 'name', '?')} / {self.name}", exc_info=True)

        # StackCost 소모 (스킬 효과 실행 후)
        # 검성과 암흑기사는 StackCost를 효과 실행 후에 소모함
        if stack_costs:
            # 기본: 효과 실행 후 소비
            # 검성/암흑기사도 동일 처리(스킬별 오버라이드 없음)
            for cost in stack_costs:
                if not cost.consume(user, context):
                    from src.core.logger import get_logger
                    logger = get_logger("skill")
                    logger.warning(f"StackCost 소모 실패: {user.name} {self.name}")

        # 최종 메시지 구성 (ISSUE-003: 상세 피드백)
        base_message = f"{user.name}이(가) {self.name} 사용!"
        if effect_messages:
            full_message = base_message + "\n  → " + "\n  → ".join(effect_messages)
        else:
            full_message = base_message

        # 신관 신탁 충족 체크 (oracle_action 메타데이터 처리)
        if hasattr(user, 'gimmick_type') and user.gimmick_type == "oracle_system":
            if self.metadata and 'oracle_action' in self.metadata:
                from src.character.gimmick_updater import GimmickUpdater
                oracle_action = self.metadata['oracle_action']
                GimmickUpdater.check_oracle_fulfillment(user, oracle_action, context)

        # 마술사 카드 처리 플래그 정리
        if self.metadata:
            self.metadata.pop('_card_processed', None)
            # 과부하 사용 플래그 정리 (다음 스킬에 영향 없도록)
            if self.metadata.get("_use_overload"):
                self.metadata.pop("_use_overload", None)

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
