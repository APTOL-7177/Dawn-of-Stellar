"""Gimmick Updater - 기믹 자동 업데이트 시스템"""
import math
from src.core.logger import get_logger
from src.core.event_bus import event_bus, Events
from src.character.stats import Stats

logger = get_logger("gimmick")

class GimmickUpdater:
    """기믹 자동 업데이트 관리자"""

    @staticmethod
    def _push_ui_log(character, message: str, color=None):
        """전투 UI 로그로 기믹 메시지를 전달 (UI가 없으면 로거로 기록)"""
        color = color or (200, 200, 200)

        combat_manager = getattr(character, "_combat_manager_ref", None)
        if combat_manager is None:
            try:
                from src.combat.combat_manager import get_combat_manager
                combat_manager = get_combat_manager()
            except Exception:
                combat_manager = None

        ui = getattr(combat_manager, "combat_ui", None) if combat_manager else None
        if ui and hasattr(ui, "add_message"):
            try:
                ui.add_message(message, color)
                return
            except Exception:
                logger.debug(f"UI 로그 전달 실패: {message}", exc_info=True)

        logger.info(message)

    @staticmethod
    def on_turn_end(character):
        """턴 종료 시 기믹 업데이트"""
        gimmick_type = getattr(character, 'gimmick_type', None)
        if not gimmick_type:
            return

        # 기존 구현된 기믹들
        if gimmick_type == "heat_management":
            GimmickUpdater._update_heat_management(character, is_own_turn=True)
            # 포탑 자동 공격은 combat_manager에서 모든 턴 종료 시 처리
        elif gimmick_type == "timeline_system":
            GimmickUpdater._update_timeline_system(character)
        elif gimmick_type == "yin_yang_flow":
            GimmickUpdater._update_yin_yang_flow(character)
        elif gimmick_type == "madness_threshold":
            GimmickUpdater._update_madness_threshold(character, is_turn_end=True)
        elif gimmick_type == "thirst_gauge":
            GimmickUpdater._update_thirst_gauge(character)
        elif gimmick_type == "probability_distortion":
            GimmickUpdater._update_probability_distortion(character)
        elif gimmick_type == "stealth_exposure":
            GimmickUpdater._update_stealth_exposure(character)
        # ISSUE-004: 신규 추가 기믹들
        elif gimmick_type == "sword_aura":
            GimmickUpdater._update_sword_aura(character)
        elif gimmick_type == "blade_circuit":
            # 채널 봉인 턴 감소
            if getattr(character, "steel_lock", 0) > 0:
                character.steel_lock = max(0, character.steel_lock - 1)
            if getattr(character, "mana_lock", 0) > 0:
                character.mana_lock = max(0, character.mana_lock - 1)
        elif gimmick_type == "crowd_cheer":
            # 관중 요구: 4턴 주기로 생성, 그 사이에 달성하면 OK
            current_demand = getattr(character, "current_demand", None)
            cooldown = getattr(character, "demand_cooldown", 0)
            turns_left = getattr(character, "demand_turns_left", 0)

            if current_demand:
                # 진행 중인 요구의 남은 턴 감소
                turns_left = max(0, turns_left - 1)
                character.demand_turns_left = turns_left

                if current_demand.get("fulfilled", False):
                    # 이미 충족된 요구: 정리 후 쿨다운 시작
                    character.current_demand = None
                    character.demand_progress = {}
                    character.demand_cooldown = 4
                    character.demand_turns_left = 0
                elif turns_left <= 0:
                    # 기간 내 미충족 → 야유
                    GimmickUpdater.fail_demand(character)
                    character.current_demand = None
                    character.demand_progress = {}
                    character.demand_cooldown = 4
                    character.demand_turns_left = 0
            else:
                # 진행 중인 요구가 없을 때 쿨다운 감소 후 생성
                cooldown = max(0, cooldown - 1)
                character.demand_cooldown = cooldown
                if cooldown <= 0:
                    new_demand = GimmickUpdater.generate_crowd_demand(character)
                    if new_demand:
                        character.demand_turns_left = 4  # 4턴 안에 달성
                        character.demand_cooldown = 0

            # 환호 자연 감소 및 기타 처리
            GimmickUpdater._update_crowd_cheer(character)
        elif gimmick_type == "rune_resonance":
            # 배틀메이지: 공명 게이지 100 도달 시 자동 룬 분배
            GimmickUpdater._update_rune_resonance(character)

    @staticmethod
    def on_hp_change(character, old_hp: int, new_hp: int):
        """HP 변화 시 기믹 업데이트 (광기 즉시 반영)"""
        gimmick_type = getattr(character, 'gimmick_type', None)
        if not gimmick_type or gimmick_type != "madness_threshold":
            return

        # 광기 HP 비율 업데이트 (즉시 반영)
        if hasattr(character, 'current_hp') and hasattr(character, 'max_hp') and character.max_hp > 0:
            hp_ratio = character.current_hp / character.max_hp
            hp_madness_increase = int((1.0 - hp_ratio) * 15)

            if hp_madness_increase > 0:
                old_madness = character.madness
                character.madness = min(character.max_madness or 100, character.madness + hp_madness_increase)
                logger.info(f"{character.name} HP 즉시 변화로 광기 증가: +{hp_madness_increase} (HP: {hp_ratio:.1%}, {old_madness}→{character.madness})")
        elif gimmick_type == "duty_system":
            GimmickUpdater._update_duty_system(character)
        elif gimmick_type == "stance_system":
            GimmickUpdater._update_stance_system(character)
        elif gimmick_type == "iaijutsu_system":
            GimmickUpdater._update_iaijutsu_system(character)
        elif gimmick_type == "dragon_marks":
            GimmickUpdater._update_dragon_marks(character)
        elif gimmick_type == "holy_system":
            GimmickUpdater._update_holy_system(character)
        elif gimmick_type == "divinity_system":
            GimmickUpdater._update_divinity_system(character)
        # charge_system은 별도로 처리됨 (on_turn_start, on_turn_end에서)
        elif gimmick_type == "undead_legion":
            GimmickUpdater._update_undead_legion(character)
        elif gimmick_type == "theft_system":
            GimmickUpdater._update_theft_system(character)
        elif gimmick_type == "shapeshifting_system":
            GimmickUpdater._update_shapeshifting_system(character)
        elif gimmick_type == "enchant_system":
            GimmickUpdater._update_enchant_system(character)
        elif gimmick_type == "curse_system" or gimmick_type == "totem_system":
            GimmickUpdater._update_curse_system(character)
        elif gimmick_type == "melody_system":
            GimmickUpdater._update_melody_system(character)
        elif gimmick_type == "break_system":
            GimmickUpdater._update_break_system(character)
        elif gimmick_type == "elemental_counter":
            GimmickUpdater._update_elemental_counter(character)
        elif gimmick_type == "alchemy_system":
            GimmickUpdater._update_alchemy_system(character)
        elif gimmick_type == "elemental_spirits":
            GimmickUpdater._update_elemental_spirits(character)
        elif gimmick_type == "plunder_system":
            GimmickUpdater._update_plunder_system(character)
        elif gimmick_type == "multithread_system":
            GimmickUpdater._update_multithread_system(character)
        elif gimmick_type == "intrusion_system":
            GimmickUpdater._update_intrusion_system(character)
        elif gimmick_type == "oath_system":
            GimmickUpdater._update_oath_system(character)
        elif gimmick_type == "oracle_system":
            GimmickUpdater._update_oracle_system(character)
        elif gimmick_type == "mockery_system":
            GimmickUpdater._update_mockery_system(character)
        elif gimmick_type == "dilemma_choice":
            GimmickUpdater._update_dilemma_choice(character)
        elif gimmick_type == "rune_resonance":
            GimmickUpdater._update_rune_resonance(character)
        elif gimmick_type == "charge_system":
            GimmickUpdater._update_charge_system_turn_end(character)
        elif gimmick_type == "dimension_refraction":
            GimmickUpdater._update_dimension_refraction(character)
        elif gimmick_type == "trick_deck":
            GimmickUpdater._update_trick_deck(character)
        elif gimmick_type == "possibility_slots":
            GimmickUpdater._update_possibility_slots(character)
        elif gimmick_type == "phantom_legion":
            GimmickUpdater._update_phantom_legion(character)
        elif gimmick_type == "mp_overload_system":
            GimmickUpdater._update_mp_overload_state(character)
        elif gimmick_type == "kenshin_system":
            # 사무라이: 관찰 스택 감소 (매 턴 종료 시 -1)
            GimmickUpdater._update_kenshin_system_turn_end(character)

    @staticmethod
    def on_turn_start(character, context=None):
        """턴 시작 시 기믹 업데이트
        
        Args:
            character: 캐릭터
            context: 컨텍스트 (enemies, combat_manager 등)
        """
        # 스턴 턴 감소 및 해제 (모든 캐릭터 공통)
        if hasattr(character, 'stunned_turns') and character.stunned_turns > 0:
            character.stunned_turns -= 1
            if character.stunned_turns <= 0:
                character.is_stunned = False
                character.stunned_turns = 0
                logger.info(f"{character.name} 스턴 해제!")
            else:
                logger.info(f"{character.name} 스턴 중... (남은 턴: {character.stunned_turns})")
        
        # 토글 스킬 유지비 MP 소모 처리 (기믹과 무관하게 공통 적용)
        GimmickUpdater._apply_toggle_mp_upkeep(character)

        gimmick_type = getattr(character, 'gimmick_type', None)
        if not gimmick_type:
            return

        # 확률 왜곡 게이지 - 턴 시작 시 +10
        if gimmick_type == "probability_distortion":
            gauge_gain = getattr(character, 'gauge_per_turn', 10)
            character.distortion_gauge = min(character.max_gauge, character.distortion_gauge + gauge_gain)
            logger.debug(f"{character.name} 확률 왜곡 게이지 +{gauge_gain} (총: {character.distortion_gauge})")
        elif gimmick_type == "intrusion_system":
            # 해커: RAM/침투 시스템 턴 시작 처리 (회복 및 오버클럭 소모)
            GimmickUpdater._update_intrusion_system(character)
        elif gimmick_type == "oracle_system":
            # 신관: 신탁 턴 카운터 증가
            oracle_turn_count = getattr(character, 'oracle_turn_count', 0) + 1
            character.oracle_turn_count = oracle_turn_count

            # 현재 신탁이 없으면 즉시 생성
            if not getattr(character, "current_oracle", None):
                GimmickUpdater.generate_oracle(character)
                character.oracle_turn_count = 0  # 턴 카운터 초기화
            # 4턴마다 강제로 신탁 변경
            elif oracle_turn_count >= 4:
                current_oracle = character.current_oracle
                oracle_name = current_oracle.get('name', '신탁') if current_oracle else '신탁'
                if current_oracle and not current_oracle.get('fulfilled', False):
                    # 미충족 신탁 - 콤보 초기화
                    character.oracle_combo = 0
                    logger.info(f"[신탁 시간 초과] {character.name}: {oracle_name} 미충족 - 새 신탁 생성")
                else:
                    logger.info(f"[신탁 갱신] {character.name}: 4턴 경과 - 새 신탁 생성")
                GimmickUpdater.generate_oracle(character)
                character.oracle_turn_count = 0  # 턴 카운터 초기화

        # 갈증 게이지 - 턴 시작 시 증가 (특성에서 설정된 값 사용, 기본값 5)
        elif gimmick_type == "thirst_gauge":
            # 특성에서 thirst_per_turn 값 확인
            thirst_per_turn = 5  # 기본값
            if hasattr(character, 'active_traits'):
                from src.character.trait_effects import get_trait_effect_manager
                trait_manager = get_trait_effect_manager()
                for trait_data in character.active_traits:
                    trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                    if trait_id == "blood_control":
                        # blood_control 특성의 thirst_per_turn 값 사용
                        thirst_per_turn = 5  # 특성에서 정의된 값
                        break
            
            character.thirst = min(character.max_thirst, character.thirst + thirst_per_turn)
            logger.debug(f"{character.name} 갈증 +{thirst_per_turn} (총: {character.thirst})")

        # ISSUE-004: 추가 턴 시작 기믹 업데이트
        # 군중 환호 - 턴 시작 시 +5
        elif gimmick_type == "crowd_cheer":
            cheer = getattr(character, 'cheer', 0)
            max_cheer = getattr(character, 'max_cheer', 100)
            character.cheer = min(max_cheer, cheer + 5)
            logger.debug(f"{character.name} 환호 증가: +5 (총: {character.cheer})")
        
        # 전사 - 스탠스 시스템 효과 적용
        elif gimmick_type == "stance_system":
            GimmickUpdater._apply_stance_effects(character)
        
        # 네크로맨서 - 언데드 자동 공격
        elif gimmick_type == "undead_legion":
            GimmickUpdater._undead_auto_attack(character, context)

        # 기계공학자 - 포탑 발사는 turn_end에서 처리

        # 암흑기사 - 충전 시스템 턴 시작
        elif gimmick_type == "charge_system":
            GimmickUpdater._update_charge_system_turn_start(character)
        
        # 마술사 - 트릭 덱 시스템 턴 시작
        elif gimmick_type == "trick_deck":
            GimmickUpdater._update_trick_deck_turn_start(character)
        
        # 시간술사 - 가능성 슬롯 시스템 턴 시작
        elif gimmick_type == "possibility_slots":
            GimmickUpdater._update_possibility_slots_turn_start(character, context)
        
        # 환술사 - 환영 군단 시스템 턴 시작
        elif gimmick_type == "phantom_legion":
            GimmickUpdater._update_phantom_legion_turn_start(character, context)
        elif gimmick_type == "mp_overload_system":
            GimmickUpdater._update_mp_overload_state(character)
        # elif gimmick_type == "dimension_refraction":
        #    # ISSUE-16: 리메이크 - 턴 시작 시가 아니라 매 행동마다 처리됨
        #    pass

        # 일반 특성 처리 (기믹과 무관한 특성들)
        GimmickUpdater._process_turn_start_traits(character, context)

    @staticmethod
    def on_death(character):
        """캐릭터 사망 시 기믹 업데이트"""
        gimmick_type = getattr(character, 'gimmick_type', None)
        if not gimmick_type:
            return

        # 차원술사: 사망 시 굴절량 0으로 초기화
        if gimmick_type == "dimension_refraction":
            if hasattr(character, "refraction_stacks") and character.refraction_stacks > 0:
                character.refraction_stacks = 0
                logger.info(f"[기믹] {character.name} 사망으로 차원 굴절량 초기화")
                GimmickUpdater._push_ui_log(character, f"{character.name}의 차원 굴절이 흩어집니다.", (150, 150, 200))

    @staticmethod
    def _apply_toggle_mp_upkeep(character):
        """토글 스킬 유지비 MP 소모"""
        if not hasattr(character, "active_toggles") or not getattr(character, "active_toggles", None):
            return
        if not hasattr(character, "current_mp"):
            return

        try:
            from src.character.skills.skill_manager import get_skill_manager
            skill_manager = get_skill_manager()
        except Exception:
            skill_manager = None

        toggles_to_remove = []
        for toggle_id in list(getattr(character, "active_toggles", [])):
            skill = skill_manager.get_skill(toggle_id) if skill_manager else None
            meta = getattr(skill, "metadata", {}) if skill else {}
            mp_per_turn = meta.get("toggle_mp_per_turn", 0)
            max_mp_penalty = meta.get("max_mp_penalty", 0.0)
            if not mp_per_turn:
                continue

            if character.current_mp >= mp_per_turn:
                character.current_mp -= mp_per_turn
                logger.info(f"[토글 유지비] {character.name} {toggle_id} MP -{mp_per_turn} (잔여 {character.current_mp})")
            else:
                # MP 부족 → 토글 자동 해제
                toggles_to_remove.append((toggle_id, max_mp_penalty))
                logger.info(f"[토글 해제/MP부족] {character.name} {toggle_id} 비활성화 (MP 부족)")

        for toggle_id, max_mp_penalty in toggles_to_remove:
            if toggle_id in character.active_toggles:
                character.active_toggles.remove(toggle_id)
            if max_mp_penalty:
                penalty = int(character.max_mp * max_mp_penalty)
                character.reserved_max_mp = max(0, getattr(character, "reserved_max_mp", 0) - penalty)
                if hasattr(character, "current_mp"):
                    character.current_mp = min(character.current_mp, character.effective_max_mp())

            # 요미 특수 처리: 토글 해제 시 예측 정보도 중단
            if toggle_id == "samurai_yomi":
                if hasattr(character, "prediction_active"):
                    character.prediction_active = False
                if hasattr(character, "prediction_turns_left"):
                    character.prediction_turns_left = 0
                if hasattr(character, "predicted_actions"):
                    character.predicted_actions = {}

    @staticmethod
    def _process_turn_start_traits(character, context):
        """턴 시작 시 특성 효과 처리"""
        if not hasattr(character, 'active_traits'):
            return

        # prayer_blessing: 매 턴 아군 전체 HP 5% 회복 (성직자)
        has_prayer_blessing = any(
            (t if isinstance(t, str) else t.get('id')) == 'prayer_blessing'
            for t in character.active_traits
        )
        if has_prayer_blessing and context and 'combat_manager' in context:
            combat_manager = context['combat_manager']
            if hasattr(combat_manager, 'allies'):
                # 모든 아군에게 최대 HP의 5% 회복
                for ally in combat_manager.allies:
                    if hasattr(ally, 'is_alive') and ally.is_alive:
                        if hasattr(ally, 'max_hp') and hasattr(ally, 'current_hp'):
                            heal_amount = int(ally.max_hp * 0.05)
                            if hasattr(ally, 'heal'):
                                actual_heal = ally.heal(heal_amount)
                            else:
                                actual_heal = min(heal_amount, ally.max_hp - ally.current_hp)
                                ally.current_hp = min(ally.max_hp, ally.current_hp + actual_heal)
                            if actual_heal > 0:
                                logger.info(f"[기도의 축복] {ally.name} HP +{actual_heal} (최대 HP의 5%)")

        # meditation: 턴 시작 시 MP 5%, BRV 10% 회복 (사무라이)
        has_meditation = any(
            (t if isinstance(t, str) else t.get('id')) == 'meditation'
            for t in character.active_traits
        )
        if has_meditation:
            if hasattr(character, 'max_mp') and hasattr(character, 'current_mp'):
                mp_restore = int(character.max_mp * 0.05)
                if hasattr(character, 'restore_mp'):
                    actual_mp = character.restore_mp(mp_restore)
                else:
                    actual_mp = min(mp_restore, character.max_mp - character.current_mp)
                    character.current_mp += actual_mp
                if actual_mp > 0:
                    logger.info(f"[명상] {character.name} MP +{actual_mp} (최대 MP의 5%)")

            if hasattr(character, 'max_brv') and hasattr(character, 'current_brv'):
                brv_restore = int(character.max_brv * 0.10)
                actual_brv = min(brv_restore, character.max_brv - character.current_brv)
                character.current_brv += actual_brv
                if actual_brv > 0:
                    logger.info(f"[명상] {character.name} BRV +{actual_brv} (최대 BRV의 10%)")

        # healing_light: 턴 시작 시 HP 3% 자동 회복 (성기사)
        has_healing_light = any(
            (t if isinstance(t, str) else t.get('id')) == 'healing_light'
            for t in character.active_traits
        )
        if has_healing_light:
            if hasattr(character, 'max_hp') and hasattr(character, 'current_hp'):
                heal_amount = int(character.max_hp * 0.03)
                if hasattr(character, 'heal'):
                    actual_heal = character.heal(heal_amount)
                else:
                    actual_heal = min(heal_amount, character.max_hp - character.current_hp)
                    character.current_hp = min(character.max_hp, character.current_hp + actual_heal)
                if actual_heal > 0:
                    logger.info(f"[치유의 빛] {character.name} HP +{actual_heal} (최대 HP의 3%)")

        # spirit_guide: 턴 시작 시 MP 10% 회복 (무당)
        has_spirit_guide = any(
            (t if isinstance(t, str) else t.get('id')) == 'spirit_guide'
            for t in character.active_traits
        )
        if has_spirit_guide:
            if hasattr(character, 'max_mp') and hasattr(character, 'current_mp'):
                mp_restore = int(character.max_mp * 0.10)
                if hasattr(character, 'restore_mp'):
                    actual_mp = character.restore_mp(mp_restore)
                else:
                    actual_mp = min(mp_restore, character.max_mp - character.current_mp)
                    character.current_mp += actual_mp
                if actual_mp > 0:
                    logger.info(f"[영혼 안내] {character.name} MP +{actual_mp} (최대 MP의 10%)")

    @staticmethod
    def on_skill_use(character, skill, context=None):
        """스킬 사용 시 기믹 업데이트"""
        gimmick_type = getattr(character, 'gimmick_type', None)
        if not gimmick_type:
            return

        # 공통 토글 스킬 처리 (직업 무관)
        if skill.metadata.get("toggle") or skill.metadata.get("toggle_release_all") or skill.metadata.get("overload_capable"):
            _mp_overload_on_skill(character, skill)
            # 중복 처리 방지 플래그 정리 (다음 스킬에서 다시 처리 가능하도록)
            skill.metadata.pop("_overload_processed", None)

        # 신관: 신앙 100 강화 시스템
        if gimmick_type == "oracle_system" and skill.metadata.get("faith_empowered"):
            current_faith = getattr(character, 'faith', 0)
            if current_faith >= 100:
                # 신앙 강화 적용
                _apply_faith_empowerment(character, skill)
                # 신앙 소모
                character.faith = 0
                logger.info(f"[신앙 강화] {character.name}의 {skill.name} 강화 발동! 신앙 소모.")

        if gimmick_type == "oracle_system":
            # 신관: 신탁 액션 충족 (on_skill_use에 추가하여 즉시 반응 보장)
            oracle_action = skill.metadata.get("oracle_action")
            if oracle_action:
                try:
                    GimmickUpdater.check_oracle_fulfillment(character, oracle_action)
                except AttributeError:
                    # check_oracle_fulfillment가 없을 경우 대비 (안전장치)
                    logger.warning(f"{character.name} 신탁 확인 실패: check_oracle_fulfillment 메서드 없음")
                except Exception as e:
                    logger.error(f"신탁 확인 중 오류: {e}")

        if gimmick_type == "stealth_exposure":
            # 공격 스킬 사용 시 은신 해제 체크
            if skill.metadata.get("breaks_stealth", False):
                was_stealthed = getattr(character, "stealth_active", False)
                character.stealth_active = False
                # 최초 은신 해제 시에만 노출 턴 초기화, 이미 노출 중이면 유지
                if was_stealthed and getattr(character, "exposed_turns", 0) <= 0:
                    character.exposed_turns = 0
                # 노출 스택은 턴마다 증가하도록 유지 (초기화하지 않음)
                logger.info(f"{character.name} 은신 해제 (공격 스킬 사용)")
        elif gimmick_type == "support_fire":
            # 직접 공격 시 콤보 초기화
            if skill.metadata.get("breaks_combo", False):
                character.support_fire_combo = 0
                logger.debug(f"{character.name} 직접 공격으로 지원 콤보 초기화")
        elif gimmick_type == "stance_system":
            # 스탠스 변경 스킬 사용 시 스탠스 효과 재적용
            if skill.metadata.get("stance"):
                GimmickUpdater._apply_stance_effects(character)
        elif gimmick_type == "shapeshifting_system":
            # 드루이드: 변신 스킬 사용 시 형태 변경
            form = skill.metadata.get("form")
            if form:
                character.current_form = form
                form_names = {
                    "bear": "곰",
                    "cat": "표범",
                    "panther": "표범",
                    "eagle": "독수리",
                    "wolf": "늑대",
                    "primal": "진 변신",
                    "elemental": "원소"
                }
                form_name = form_names.get(form, form)
                logger.info(f"{character.name} {form_name} 형태로 변신!")
        
        elif gimmick_type == "score_composition":
            # 바드: 스킬 사용 시 음표 추가
            note_add = skill.metadata.get("note_add")
            if note_add:
                if not hasattr(character, 'music_notes'):
                    character.music_notes = []
                max_notes = getattr(character, 'max_notes', 5)
                if len(character.music_notes) < max_notes:
                    character.music_notes.append(note_add)
                    logger.info(f"{character.name} 악보에 {note_add} 음표 추가! (현재: {''.join(character.music_notes)})")
                else:
                    # 가장 오래된 음표 제거 후 추가
                    character.music_notes.pop(0)
                    character.music_notes.append(note_add)
                    logger.info(f"{character.name} 악보 갱신: {''.join(character.music_notes)}")
            
            # 작곡 스킬: 패턴 효과 발동
            if skill.metadata.get("compose_skill"):
                GimmickUpdater._apply_bard_compose_effect(character, skill, context)
        
        elif gimmick_type == "trick_deck":
            # 마술사: 스킬 사용 시 카드 드로우 및 효과 적용
            card_draw = skill.metadata.get("card_draw", 0)
            if card_draw > 0:
                try:
                    from src.character.skills.job_skills.magician_skills import draw_cards, get_card_name, discard_cards, RANK_EFFECTS, SUIT_EFFECTS
                    drawn = draw_cards(character, card_draw)
                    if drawn:
                        card_names = [get_card_name(c) for c in drawn]
                        logger.info(f"{character.name} 카드 드로우: {', '.join(card_names)}")
                        
                        # 카드 효과 적용
                        cards_to_discard = []
                        for card in drawn:
                            # 숫자 효과 적용
                            if skill.metadata.get("apply_rank_effect"):
                                rank = card.get("rank", "")
                                rank_effect = RANK_EFFECTS.get(rank, {})
                                if rank_effect:
                                    GimmickUpdater._apply_card_rank_effect(character, rank_effect, card)
                                    cards_to_discard.append(card)
                            
                            # 무늬 효과 적용
                            if skill.metadata.get("apply_suit_effect"):
                                suit = card.get("suit", "")
                                suit_effect = SUIT_EFFECTS.get(suit, {})
                                if suit_effect:
                                    GimmickUpdater._apply_card_suit_effect(character, suit_effect, card, context)
                                    if card not in cards_to_discard:
                                        cards_to_discard.append(card)
                        
                        # 사용한 카드 소모 (버리기)
                        if cards_to_discard and skill.metadata.get("consume_drawn_cards", True):
                            discard_cards(character, cards_to_discard)
                            logger.info(f"{character.name} 카드 {len(cards_to_discard)}장 소모")
                except Exception as e:
                    logger.debug(f"카드 드로우 실패: {e}")
            
            # 카드 강화 발사 스킬: 손패에서 카드 선택하여 사용
            if skill.metadata.get("select_card_from_hand"):
                try:
                    from src.character.skills.job_skills.magician_skills import get_card_name, discard_cards, RANK_EFFECTS, SUIT_EFFECTS
                    hand = getattr(character, 'card_hand', [])
                    
                    # UI에서 선택한 카드가 있으면 사용, 없으면 자동 선택
                    selected_card = skill.metadata.get('_selected_card')
                    if selected_card and selected_card in hand:
                        # UI에서 선택된 카드 사용
                        pass
                    elif hand:
                        # 자동 선택 (가장 높은 랭크)
                        rank_order = {"A": 14, "K": 13, "Q": 12, "J": 11, "10": 10, "9": 9, "8": 8, "7": 7, "6": 6, "5": 5, "4": 4, "3": 3, "2": 2, "JOKER": 15}
                        selected_card = max(hand, key=lambda c: rank_order.get(c.get("rank", ""), 0))
                    
                    if selected_card and selected_card in hand:
                        
                        card_name = get_card_name(selected_card)
                        logger.info(f"[마술사] {character.name} 카드 강화 발사! 선택: {card_name}")
                        
                        # 숫자 효과 적용
                        if skill.metadata.get("apply_rank_effect"):
                            rank = selected_card.get("rank", "")
                            rank_effect = RANK_EFFECTS.get(rank, {})
                            if rank_effect:
                                GimmickUpdater._apply_card_rank_effect(character, rank_effect, selected_card)
                        
                        # 무늬 효과 적용
                        if skill.metadata.get("apply_suit_effect"):
                            suit = selected_card.get("suit", "")
                            suit_effect = SUIT_EFFECTS.get(suit, {})
                            if suit_effect:
                                GimmickUpdater._apply_card_suit_effect(character, suit_effect, selected_card, context)
                        
                        # 카드 소모:
                        if skill.metadata.get("consume_selected_card"):
                            discard_cards(character, [selected_card])
                            logger.info(f"  -> {card_name} 소모됨")
                        
                        # 카드 처리 완료 플래그 설정 (can_use 체크 건너뛰기용)
                        skill.metadata['_card_processed'] = True
                        
                        # 메타데이터 정리
                        skill.metadata.pop('_selected_card', None)
                    else:
                        logger.info(f"[마술사] {character.name} 손패가 없어 카드 강화 발사 실패!")
                except Exception as e:
                    logger.debug(f"카드 강화 발사 실패: {e}")
                finally:
                    if hasattr(skill, 'metadata'):
                        skill.metadata.pop('_selected_card', None)

            # 카드 카운터 스킬: 덱에서 원하는 숫자 카드 서치
            if skill.metadata.get("search_deck"):
                try:
                    from src.character.skills.job_skills.magician_skills import get_card_name
                    deck = getattr(character, 'card_deck', [])
                    hand = getattr(character, 'card_hand', [])
                    max_hand = getattr(character, 'max_hand_size', 8)
                    
                    if len(hand) >= max_hand:
                        logger.info(f"[카드 카운터] {character.name} 손패가 가득 차 서치 불가!")
                    elif not deck:
                        logger.info(f"[카드 카운터] {character.name} 덱이 비어 서치 불가!")
                    else:
                        # UI에서 선택한 랭크가 있으면 사용, 없으면 필요한 카드 자동 선택
                        target_rank = skill.metadata.get('_search_rank')
                        
                        if not target_rank:
                            # 자동 선택: 현재 조합 완성에 필요한 카드 탐색
                            from src.character.skills.job_skills.magician_skills import check_poker_combination
                            current_combo, _, _ = check_poker_combination(hand)
                            
                            # 손패에 있는 랭크 수 계산
                            rank_counts = {}
                            for card in hand:
                                if not card.get('is_joker'):
                                    r = card.get('rank', '')
                                    rank_counts[r] = rank_counts.get(r, 0) + 1
                            
                            # 가장 많은 랭크 찾아서 조합 완성 시도
                            if rank_counts:
                                target_rank = max(rank_counts, key=rank_counts.get)
                            else:
                                # 손패가 비었으면 A 서치
                                target_rank = "A"
                        
                        # 덱에서 해당 랭크 카드 찾기
                        found_card = None
                        for i, card in enumerate(deck):
                            if not card.get('is_joker') and card.get('rank') == target_rank:
                                found_card = deck.pop(i)
                                break
                        
                        if found_card:
                            hand.append(found_card)
                            character.card_hand = hand
                            character.card_deck = deck
                            card_name = get_card_name(found_card)
                            logger.info(f"[카드 카운터] {character.name} 덱에서 {card_name} 서치 성공!")
                        else:
                            logger.info(f"[카드 카운터] {character.name} 덱에 {target_rank} 카드가 없음!")
                except Exception as e:
                    logger.debug(f"카드 서치 실패: {e}")
                finally:
                    if hasattr(skill, 'metadata'):
                        skill.metadata.pop('_search_rank', None)
            
            # 선공 효과 (A) - 플래그 설정 (턴 종료 시 ATB 최대치로)
            # 스킬 사용 후 턴이 끝나고 ATB가 consume된 후에 적용해야 함
            card_effects = getattr(character, 'card_effects', {})
            if card_effects.get('first_strike', False):
                # 턴 종료 시 적용되도록 플래그 유지
                character._first_strike_pending = True
                logger.info(f"[마술사] {character.name} 선제공격 준비!")
        
        elif gimmick_type == "possibility_slots":
            # 시간술사: 스킬 사용 시 가능성 생성
            GimmickUpdater._process_possibility_generation(character, skill, context)

        elif gimmick_type == "kenshin_system":
            # 사무라이: 공격 스킬 사용 시 관찰 스택 감소 (-2)
            if skill.metadata.get("observation_cost", 0) > 0:
                observation = getattr(character, "observation", 0)
                cost = skill.metadata.get("observation_cost", 2)
                character.observation = max(0, observation - cost)
                logger.info(f"{character.name} 관찰 스택 -{cost} (공격) -> {character.observation}")

            # 미키리 스킬: BRV 흡수
            if skill.metadata.get("brv_steal", False):
                GimmickUpdater._apply_kenshin_brv_steal(character, skill, context)

            # 요미 스킬: 적 행동 예측
            if skill.metadata.get("prediction", False):
                GimmickUpdater._apply_kenshin_prediction(character, skill, context)

    @staticmethod
    def pre_skill_execution(user, skill, target, context=None):
        """Skill.execute 진입 전에 기믹별 선처리"""
        gimmick_type = getattr(user, "gimmick_type", None)
        context = context or {}
        if gimmick_type == "blade_circuit":
            return GimmickUpdater._pre_blade_circuit_skill(user, skill, target, context)
        if gimmick_type == "rune_resonance":
            return GimmickUpdater._pre_rune_resonance_skill(user, skill, target, context)
        return {}

    @staticmethod
    def post_skill_execution(user, skill, target, context=None, hook=None, total_damage=0):
        """Skill.execute 종료 직후 기믹별 후처리"""
        gimmick_type = getattr(user, "gimmick_type", None)
        context = context or {}
        hook = hook or {}
        if gimmick_type == "blade_circuit":
            return GimmickUpdater._post_blade_circuit_skill(user, skill, target, context, hook, total_damage)
        if gimmick_type == "rune_resonance":
            return GimmickUpdater._post_rune_resonance_skill(user, skill, target, context, hook, total_damage)
        return {"extra_damage": 0, "extra_heal": 0, "messages": []}

    @staticmethod
    def on_ally_attack(attacker, all_allies, target=None, context=None):
        """아군 공격 시 기믹 트리거 (지원사격 등)"""
        # 모든 아군 중에서 궁수 찾기
        for ally in all_allies:
            if not hasattr(ally, 'gimmick_type'):
                continue

            if ally.gimmick_type == "support_fire" and ally != attacker:
                GimmickUpdater._trigger_support_fire(ally, attacker, target, context)

        # 배틀메이지 Rune Trigger: Rune Signal 버프를 받은 아군의 공격으로 룬 기폭
        rune_owner = next((a for a in all_allies if getattr(a, "gimmick_type", None) == "rune_resonance"), None)
        attacker_buffs = getattr(attacker, "active_buffs", {}) if attacker else {}
        if rune_owner and attacker_buffs.get("rune_trigger") and target and getattr(target, "carved_runes", {}):
            rune_counts = dict(getattr(target, "carved_runes", {}))
            if rune_counts:
                import random
                from src.character.skills.effects.damage_effect import DamageEffect, DamageType
                enemies_all = context.get("all_enemies", []) if context else []
                # 가장 많이 쌓인 룬 1개 기폭 (단일 타격) - 룬 폭발과 동일한 효과
                rune_type = max(rune_counts, key=rune_counts.get)
                total_runes = sum(rune_counts.values())
                # 룬 폭발과 동일: HP 타입, 0.9 배율, 룬 개수에 따른 추가 피해
                deto = DamageEffect(DamageType.HP, 0.9, stat_type="hybrid",
                                   gimmick_bonus={"field": "total_runes", "multiplier": 0.17})
                # total_runes를 context에 추가하여 gimmick_bonus가 작동하도록 함
                trigger_context = dict(context or {})
                trigger_context["total_runes"] = total_runes
                deto.execute(rune_owner, target, trigger_context)
                # 광역 충격: 나머지 적들에게도 감쇠 피해 (0.9 * 0.7 = 0.63)
                aoe_targets = [e for e in enemies_all if e and getattr(e, "is_alive", True) and e != target]
                if aoe_targets:
                    aoe_deto = DamageEffect(DamageType.HP, 0.63, stat_type="hybrid",
                                           gimmick_bonus={"field": "total_runes", "multiplier": 0.12})  # 0.17 * 0.7
                    for aoe_t in aoe_targets:
                        aoe_deto.execute(rune_owner, aoe_t, trigger_context)

                # 룬 소모
                GimmickUpdater._consume_carved_runes(rune_owner, target, {rune_type: 1})

                # 연쇄 폭발: 룬 폭발과 동일한 30% 확률로 다른 적의 룬 폭발
                spread_chance = 0.3  # 룬 폭발과 동일
                if GimmickUpdater._has_trait(rune_owner, "chain_ignition"):
                    spread_chance += 0.15  # 체인 점화 특성

                # 다른 적으로 연쇄
                if enemies_all and spread_chance > 0 and random.random() <= spread_chance:
                    other_enemies = [e for e in enemies_all
                                    if e and getattr(e, "is_alive", True)
                                    and e != target
                                    and sum(getattr(e, "carved_runes", {}).values()) > 0]
                    if other_enemies:
                        chain_target = random.choice(other_enemies)
                        chain_runes = getattr(chain_target, "carved_runes", {})
                        available_runes = [rt for rt, cnt in chain_runes.items() if cnt > 0]
                        if available_runes:
                            # 연쇄 대상의 룬 1개 폭발 (감쇠: 0.9 * 0.7 = 0.63)
                            chain_rune_type = random.choice(available_runes)
                            chain_total = sum(chain_runes.values())
                            chain_ctx = dict(trigger_context)
                            chain_ctx["total_runes"] = chain_total
                            chain_deto = DamageEffect(DamageType.HP, 0.63, stat_type="hybrid",
                                                     gimmick_bonus={"field": "total_runes", "multiplier": 0.12})
                            chain_deto.execute(rune_owner, chain_target, chain_ctx)
                            GimmickUpdater._consume_carved_runes(rune_owner, chain_target, {chain_rune_type: 1})
                            GimmickUpdater._push_ui_log(rune_owner, f"[연쇄] {chain_target.name}의 {chain_rune_type} 룬 폭발!")

                GimmickUpdater._grant_resonance_gauge(rune_owner, 5)
                GimmickUpdater._push_ui_log(
                    rune_owner,
                    f"[Rune Trigger] {getattr(attacker, 'name', '')} → {getattr(target, 'name', '')} {rune_type} 룬 폭발",
                )

    @staticmethod
    def _trigger_support_fire(archer, attacking_ally, target=None, context=None):
        """궁수 지원사격 트리거"""
        # 디버그: 지원사격 체크 시작 (INFO 레벨로 변경)
        logger.info(f"[지원사격 체크] 궁수 {archer.name}, 공격자 {attacking_ally.name}, 타겟 {getattr(target, 'name', 'None')}")

        # 마킹된 아군인지 확인
        marked_slots = [
            getattr(attacking_ally, 'mark_slot_normal', 0),
            getattr(attacking_ally, 'mark_slot_piercing', 0),
            getattr(attacking_ally, 'mark_slot_fire', 0),
            getattr(attacking_ally, 'mark_slot_ice', 0),
            getattr(attacking_ally, 'mark_slot_poison', 0),
            getattr(attacking_ally, 'mark_slot_explosive', 0),
            getattr(attacking_ally, 'mark_slot_holy', 0)
        ]

        logger.info(f"  마킹 슬롯: {marked_slots}")

        # 마킹이 없으면 종료
        if all(slot == 0 for slot in marked_slots):
            logger.info(f"  -> 마킹 없음, 지원사격 안 함")
            return

        # 마킹된 슬롯 찾기
        arrow_types = ['normal', 'piercing', 'fire', 'ice', 'poison', 'explosive', 'holy']
        arrow_multipliers = {
            'normal': 1.5,
            'piercing': 1.8,
            'fire': 1.6,
            'ice': 1.4,
            'poison': 1.3,
            'explosive': 2.0,
            'holy': 1.7
        }

        for i, slot_count in enumerate(marked_slots):
            if slot_count > 0:
                arrow_type = arrow_types[i]
                shots_attr = f'mark_shots_{arrow_type}'
                shots_remaining = getattr(attacking_ally, shots_attr, 0)

                logger.info(f"  화살 타입: {arrow_type}, 슬롯: {slot_count}, 남은 발사 횟수: {shots_remaining}")

                if shots_remaining > 0:
                    # 지원사격 발동
                    logger.info(f"[지원사격] {archer.name} -> {attacking_ally.name}의 공격 지원 ({arrow_type} 화살)")

                    # 실제 BRV 데미지 계산 및 적용
                    if target and hasattr(target, 'current_brv'):
                        from src.combat.damage_calculator import DamageCalculator
                        damage_calc = DamageCalculator()

                        # 화살 배율 적용
                        multiplier = arrow_multipliers.get(arrow_type, 1.5)

                        # 콤보 보너스 적용
                        combo = getattr(archer, 'support_fire_combo', 0)
                        if combo >= 7:
                            multiplier *= 2.0  # 콤보 7+: 데미지 2배
                        elif combo >= 5:
                            multiplier *= 1.6  # 콤보 5+: 데미지 +60%
                        elif combo >= 3:
                            multiplier *= 1.4  # 콤보 3+: 데미지 +40%
                        elif combo >= 2:
                            multiplier *= 1.2  # 콤보 2+: 데미지 +20%

                        # 화살 타입별 특수 효과 파라미터 설정
                        damage_kwargs = {}
                        if arrow_type == 'piercing':
                            damage_kwargs['pierce'] = 0.3  # 방어 30% 무시
                        elif arrow_type == 'holy':
                            damage_kwargs['undead_bonus'] = 2.0  # 언데드에게 2배 데미지

                        # 폭발 화살: 광역 데미지 처리
                        if arrow_type == 'explosive':
                            # context에서 적 리스트 가져오기 (더 안정적)
                            enemies = []
                            if context and 'all_enemies' in context:
                                enemies = [e for e in context['all_enemies'] if hasattr(e, 'current_brv') and getattr(e, 'is_alive', True)]
                            else:
                                # fallback: combat_manager에서 가져오기
                                from src.combat.combat_manager import get_combat_manager
                                combat_manager = get_combat_manager()
                                if combat_manager and hasattr(combat_manager, 'enemies'):
                                    enemies = [e for e in combat_manager.enemies if hasattr(e, 'current_brv') and getattr(e, 'is_alive', True)]

                            aoe_percent = 0.5  # 광역 데미지 50%

                            # 메인 타겟에게 100% 데미지
                            damage_result = damage_calc.calculate_brv_damage(archer, target, skill_multiplier=multiplier, **damage_kwargs)
                            brv_damage = damage_result.final_damage

                            from src.combat.brave_system import get_brave_system
                            brave_system = get_brave_system()
                            brv_result = brave_system.brv_attack(archer, target, brv_damage)

                            logger.info(f"  → [폭발 화살] {target.name}에게 {brv_result['brv_stolen']} BRV 데미지! {archer.name} BRV +{brv_result['actual_gain']}")
                            if brv_result['is_break']:
                                logger.info(f"  → [BREAK!] {target.name} BRV 파괴!")

                            # 주변 적들에게 광역 데미지 (50%)
                            aoe_damage = int(brv_damage * aoe_percent)
                            aoe_targets = [e for e in enemies if e != target and hasattr(e, 'current_brv') and getattr(e, 'is_alive', True)]

                            if aoe_targets:
                                logger.info(f"  → [폭발 화살 광역] 주변 {len(aoe_targets)}명의 적에게 {aoe_damage} BRV 데미지!")
                                for aoe_target in aoe_targets:
                                    aoe_result = brave_system.brv_attack(archer, aoe_target, aoe_damage)
                                    logger.info(f"    → {aoe_target.name}에게 {aoe_result['brv_stolen']} BRV 데미지!")
                                    if aoe_result['is_break']:
                                        logger.info(f"    → [BREAK!] {aoe_target.name} BRV 파괴!")
                            else:
                                # combat_manager를 찾을 수 없으면 일반 처리
                                damage_result = damage_calc.calculate_brv_damage(archer, target, skill_multiplier=multiplier, **damage_kwargs)
                                brv_damage = damage_result.final_damage
                                
                                from src.combat.brave_system import get_brave_system
                                brave_system = get_brave_system()
                                brv_result = brave_system.brv_attack(archer, target, brv_damage)
                                
                                logger.info(f"  → {target.name}에게 {brv_result['brv_stolen']} BRV 데미지! {archer.name} BRV +{brv_result['actual_gain']}")
                                if brv_result['is_break']:
                                    logger.info(f"  → [BREAK!] {target.name} BRV 파괴!")
                        else:
                            # 일반 화살: 단일 타겟 데미지
                            damage_result = damage_calc.calculate_brv_damage(archer, target, skill_multiplier=multiplier, **damage_kwargs)
                            brv_damage = damage_result.final_damage

                            # brave_system을 사용하여 BRV 공격 적용 (BREAK 체크 포함)
                            from src.combat.brave_system import get_brave_system
                            brave_system = get_brave_system()
                            brv_result = brave_system.brv_attack(archer, target, brv_damage)

                            logger.info(f"  → {target.name}에게 {brv_result['brv_stolen']} BRV 데미지! {archer.name} BRV +{brv_result['actual_gain']}")
                            if brv_result['is_break']:
                                logger.info(f"  → [BREAK!] {target.name} BRV 파괴!")

                    # 화살 타입별 특수 효과 적용
                    if arrow_type == 'fire' and hasattr(target, 'status_manager'):
                        # 화염 화살: 화상 적용
                        from src.combat.status_effects import StatusEffect, StatusType
                        burn_effect = StatusEffect("화상", StatusType.BURN, duration=2, intensity=0.1)
                        target.status_manager.add_status(burn_effect)
                        logger.info(f"  → [화염 화살] {target.name}에게 화상 2턴 적용!")

                    elif arrow_type == 'ice' and hasattr(target, 'status_manager'):
                        # 빙결 화살: 둔화 적용
                        from src.combat.status_effects import StatusEffect, StatusType
                        slow_effect = StatusEffect("둔화", StatusType.SLOW, duration=3, intensity=0.3)
                        target.status_manager.add_status(slow_effect)
                        logger.info(f"  → [빙결 화살] {target.name}에게 둔화 3턴 적용 (속도 -30%!)")

                    elif arrow_type == 'poison' and hasattr(target, 'status_manager'):
                        # 독 화살: 독 적용
                        from src.combat.status_effects import StatusEffect, StatusType
                        poison_effect = StatusEffect("독", StatusType.POISON, duration=3, intensity=0.05)
                        target.status_manager.add_status(poison_effect)
                        logger.info(f"  → [독 화살] {target.name}에게 독 3턴 적용!")

                    # 신성 화살과 관통 화살은 데미지 계산 시 이미 적용됨 (calculate_brv_damage에서 처리)

                    # 남은 발사 횟수 감소
                    setattr(attacking_ally, shots_attr, shots_remaining - 1)

                    # 발사 횟수가 0이 되면 마킹 슬롯 제거
                    if shots_remaining - 1 <= 0:
                        setattr(attacking_ally, f'mark_slot_{arrow_type}', 0)
                        logger.debug(f"{attacking_ally.name}의 {arrow_type} 마킹 소진")

                    # 콤보 증가
                    current_combo = getattr(archer, 'support_fire_combo', 0)
                    archer.support_fire_combo = current_combo + 1
                    logger.debug(f"{archer.name} 지원 콤보: {archer.support_fire_combo}")

                    # 첫 번째 마킹만 처리하고 종료
                    break

    @staticmethod
    def check_overheat(character):
        """오버히트 체크 (기계공학자) - _update_heat_management에서 이미 처리됨"""
        if character.gimmick_type != "heat_management":
            return False
        
        # 오버히트는 _update_heat_management에서 처리됨
        return getattr(character, 'is_stunned', False)

    # === 기믹별 업데이트 로직 ===

    @staticmethod
    def _update_heat_management(character, is_own_turn=False):
        """기계공학자: 열 관리 시스템 업데이트
        
        Args:
            character: 기계공학자 캐릭터
            is_own_turn: 기계공학자 자신의 턴인지 여부 (열 감소는 자신의 턴에만)
        """
        from src.character.stats import Stats
        
        # 먼저 기존 열 보너스 제거
        try:
            if hasattr(character, 'stat_manager'):
                character.stat_manager.remove_bonus(Stats.STRENGTH, "heat_bonus")
                character.stat_manager.remove_bonus(Stats.MAGIC, "heat_bonus")
                character.stat_manager.remove_bonus(Stats.SPEED, "heat_bonus")
                character.stat_manager.remove_bonus(Stats.PHYSICAL_DEF, "heat_bonus")
                character.stat_manager.remove_bonus(Stats.MAGIC_DEF, "heat_bonus")
        except (AttributeError, KeyError):
            pass
        
        # 기계공학자의 턴에만 열 감소 처리
        if is_own_turn:
            # 기본 열 감소 (매 턴 -15, 기존 -5에서 200% 증가)
            base_heat_decay = 15
            old_heat = getattr(character, 'heat', 0)
            character.heat = max(0, character.heat - base_heat_decay)
            logger.debug(f"{character.name} 기본 열 감소: -{base_heat_decay} ({old_heat} → {character.heat})")
            
            # 자동 냉각 특성 (추가 -5)
            if hasattr(character, 'active_traits'):
                if any((t if isinstance(t, str) else t.get('id')) == 'auto_cooling' for t in character.active_traits):
                    character.heat = max(0, character.heat - 5)
                    logger.debug(f"{character.name} 자동 냉각: 열 -5")

        # 열 구간별 처리
        heat = getattr(character, 'heat', 0)
        optimal_min = getattr(character, 'optimal_min', 50)
        optimal_max = getattr(character, 'optimal_max', 79)
        danger_min = getattr(character, 'danger_min', 80)
        
        # 오버히트 방지 특성 체크 (80+ 도달 시 발동, 전투당 3회, -30)
        if heat >= 80 and heat < 100:
            has_prevention_trait = False
            
            # 특성 체크 헬퍼 함수
            def check_trait_list(trait_list, target_id):
                if not trait_list:
                    return False
                for t in trait_list:
                    if isinstance(t, str):
                        if t == target_id:
                            return True
                    elif isinstance(t, dict):
                        if t.get('id') == target_id:
                            return True
                return False
            
            # 모든 가능한 특성 속성 체크
            trait_attrs = ['active_traits', 'available_traits', 'selected_traits', 'traits']
            for attr in trait_attrs:
                if hasattr(character, attr) and check_trait_list(getattr(character, attr), 'overheat_prevention'):
                    has_prevention_trait = True
                    break
            
            # 기계공학자면 기본 발동
            if not has_prevention_trait and getattr(character, 'gimmick_type', '') == 'heat_management':
                # 기계공학자는 오버히트 방지가 기본 특성
                has_prevention_trait = True
            
            if has_prevention_trait:
                if not hasattr(character, 'overheat_prevention_uses'):
                    character.overheat_prevention_uses = 0
                
                if character.overheat_prevention_uses < 3:
                    old_heat = character.heat
                    character.heat = max(0, character.heat - 30)
                    character.overheat_prevention_uses += 1
                    heat = character.heat  # 업데이트
                    logger.info(f"{character.name} [오버히트 방지] 열 {old_heat} → {character.heat} (-30) (사용: {character.overheat_prevention_uses}/3)")
        
        # 오버히트 체크 (100 이상)
        if heat >= 100:
            import random
            # 오버히트 발동!
            character.is_stunned = True
            character.stunned_turns = 2
            logger.warning(f"{character.name} [오버히트] 스턴 상태! (열 {heat})")
            
            # 포탑 75% 파괴 (개별 포탑 카운트 사용)
            turret_types = ['fire_turret_count', 'ice_turret_count', 'thunder_turret_count', 
                           'explosive_turret_count', 'heal_turret_count']
            total_turrets = getattr(character, 'turret_count', 0)
            
            if total_turrets > 0:
                destroy_count = max(1, int(total_turrets * 0.75))
                destroyed = 0
                
                # 무작위로 포탑 파괴
                while destroyed < destroy_count:
                    # 파괴 가능한 포탑 종류 찾기
                    available_types = [t for t in turret_types if getattr(character, t, 0) > 0]
                    if not available_types:
                        break
                    
                    # 무작위로 포탑 종류 선택하여 파괴
                    to_destroy = random.choice(available_types)
                    current = getattr(character, to_destroy, 0)
                    setattr(character, to_destroy, current - 1)
                    destroyed += 1
                
                # 총 포탑 수 업데이트
                character.turret_count = max(0, total_turrets - destroyed)
                logger.warning(f"{character.name} [오버히트] 포탑 {destroyed}/{total_turrets}개 파괴! (남은 포탑: {character.turret_count})")
            
            # 크리티컬 보너스 제거
            if hasattr(character, 'heat_crit_bonus'):
                character.heat_crit_bonus = 0
            # 열 리셋 (오버히트 후 50으로)
            character.heat = 50
            heat = 50
        
        # 스탯 보너스 적용
        if hasattr(character, 'stat_manager'):
            if optimal_min <= heat <= optimal_max:
                # 최적 구간: 모든 스탯 +15%
                base_str = character.stat_manager.get_value(Stats.STRENGTH)
                base_mag = character.stat_manager.get_value(Stats.MAGIC)
                base_spd = character.stat_manager.get_value(Stats.SPEED)
                base_pdef = character.stat_manager.get_value(Stats.DEFENSE)
                base_mdef = character.stat_manager.get_value(Stats.SPIRIT)
                
                character.stat_manager.add_bonus(Stats.STRENGTH, "heat_bonus", int(base_str * 0.15))
                character.stat_manager.add_bonus(Stats.MAGIC, "heat_bonus", int(base_mag * 0.15))
                character.stat_manager.add_bonus(Stats.SPEED, "heat_bonus", int(base_spd * 0.15))
                character.stat_manager.add_bonus(Stats.DEFENSE, "heat_bonus", int(base_pdef * 0.15))
                character.stat_manager.add_bonus(Stats.SPIRIT, "heat_bonus", int(base_mdef * 0.15))
                logger.debug(f"{character.name} [최적 구간] 모든 스탯 +15%")
                    
            elif heat >= danger_min:
                # 위험 구간: 크리티컬 +20% (별도 속성으로 처리)
                character.heat_crit_bonus = 0.20
                logger.debug(f"{character.name} [위험 구간] 크리티컬 +20%")
            else:
                # 준비 구간: 보너스 없음
                if hasattr(character, 'heat_crit_bonus'):
                    character.heat_crit_bonus = 0

    @staticmethod
    def _update_timeline_system(character):
        """시간술사: 타임라인 균형 시스템 업데이트"""
        # 시간 보정 특성 (3턴마다 자동으로 0으로 이동)
        if hasattr(character, 'time_correction_counter'):
            character.time_correction_counter += 1
            if character.time_correction_counter >= 3:
                if hasattr(character, 'active_traits'):
                    if any((t if isinstance(t, str) else t.get('id')) == 'time_correction' for t in character.active_traits):
                        logger.info(f"{character.name} 시간 보정 발동! 타임라인 0으로")
                        character.timeline = 0
                        character.time_correction_counter = 0

    @staticmethod
    def _update_yin_yang_flow(character):
        """몽크: 음양 기 흐름 시스템 업데이트"""
        # 기 흐름 특성 (매 턴 균형(50)으로 +5 이동)
        if hasattr(character, 'active_traits'):
            if any((t if isinstance(t, str) else t.get('id')) == 'ki_flow' for t in character.active_traits):
                current_ki = getattr(character, 'ki_gauge', 50)
                if current_ki < 50:
                    character.ki_gauge = min(50, current_ki + 5)
                    logger.debug(f"{character.name} 기 흐름: +5 (균형으로)")
                elif current_ki > 50:
                    character.ki_gauge = max(50, current_ki - 5)
                    logger.debug(f"{character.name} 기 흐름: -5 (균형으로)")

        # 균형 상태에서 HP/MP 회복
        if 40 <= character.ki_gauge <= 60:
            character.current_hp = min(character.max_hp, character.current_hp + int(character.max_hp * 0.05))
            character.current_mp = min(character.max_mp, character.current_mp + int(character.max_mp * 0.05))
            logger.debug(f"{character.name} 태극 조화: HP/MP 5% 회복")

    @staticmethod
    def _update_madness_threshold(character, is_turn_end: bool = False):
        """버서커: 광기 임계치 시스템 업데이트

        기본 효과 (특성 불필요):
        - 광기 30-70 (최적): 공격력 +25%, 속도 +15%
        - 광기 71-99 (위험): 공격력 +50%, 속도 +30%, 크리티컬 +15%, 받는 피해 +30%
        - 광기 100 (폭주): 공격력 +100%, 크리티컬 +25%, 받는 피해 +50%
        """
        from src.character.stats import Stats
        
        # 먼저 기존 광기 관련 스탯 보너스 제거
        try:
            character.stat_manager.remove_bonus(Stats.STRENGTH, "madness_bonus")
            character.stat_manager.remove_bonus(Stats.SPEED, "madness_bonus")
        except (AttributeError, KeyError):
            pass
        
        # === rage_control 특성 확인 (광기 감소량 조절 + 구간 확장) ===
        decay_mult = 1.0  # 기본 감소 배율
        optimal_min_adj = 0  # 최적 구간 시작 조절
        optimal_max_adj = 0  # 최적 구간 끝 조절
        
        if hasattr(character, 'active_traits'):
            for trait_data in character.active_traits:
                trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                if trait_id == "rage_control":
                    decay_mult = 0.50  # 감소량 50%로
                    optimal_min_adj = -5  # 최적 구간 25-75로 확장
                    optimal_max_adj = 5
                    break
        
        # 특성 적용된 최적/위험 구간
        effective_optimal_min = character.optimal_min + optimal_min_adj
        effective_optimal_max = character.optimal_max + optimal_max_adj
        effective_danger_min = effective_optimal_max + 1
        
        # 광기 자연 감소/증가 계산
        base_decay = 5
        actual_decay = int(base_decay * decay_mult)

        # HP 비율에 따른 광기 증가 (HP가 낮을수록 광기 증가)
        hp_ratio = character.current_hp / character.max_hp
        hp_madness_increase = int((1.0 - hp_ratio) * 15)  # HP 0%일 때 최대 +15

        if character.madness < effective_optimal_min:
            # 최적 구간 미만: 자연 감소
            character.madness = max(0, character.madness - actual_decay)
            logger.debug(f"{character.name} 광기 자연 감소: -{actual_decay} (총: {character.madness})")
        elif character.madness >= effective_danger_min:
            # 위험 구간: 자연 증가
            old_madness = character.madness
            character.madness = min(character.max_madness or 100, character.madness + 10)
            logger.warning(f"{character.name} 광기 위험 증가: +10 ({old_madness}→{character.madness}, 최대: {character.max_madness or 100})")

        # HP 비율에 따른 광기 증가 적용
        if hp_madness_increase > 0:
            old_madness = character.madness
            character.madness = min(character.max_madness or 100, character.madness + hp_madness_increase)
            logger.info(f"{character.name} HP 낮음으로 광기 증가: +{hp_madness_increase} (HP: {hp_ratio:.1%}, {old_madness}→{character.madness}, 최대: {character.max_madness or 100})")
        
        # === 기본 효과 적용 (특성 불필요) ===
        madness = character.madness
        base_attack = character.stat_manager.get_value(Stats.STRENGTH, use_total=False)
        base_speed = character.stat_manager.get_value(Stats.SPEED, use_total=False)
        
        # 폭주 상태 (광기 100) - 통제 가능하지만 대가가 큼
        if madness >= character.rampage_threshold:
            character.stat_manager.add_bonus(Stats.STRENGTH, "madness_bonus", base_attack * 1.00)
            # 폭주 상태에서는 속도 보너스 없음 (공격력 +100%, 크리티컬 +25%만 적용)
            character._is_rampaging = True
            character._rampage_turns = getattr(character, '_rampage_turns', 0) + 1
            character._madness_zone = "rampage"
            character._madness_crit_bonus = 0.25  # 크리티컬 +25%
            character._madness_damage_taken_mult = 1.50  # 받는 피해 +50%

            # 매턴 HP 10% 감소 (폭주의 대가)
            hp_loss = int(character.max_hp * 0.10)
            old_hp = character.current_hp
            character.current_hp = max(1, character.current_hp - hp_loss)
            
            # UI 업데이트를 위한 이벤트 발행
            if old_hp != character.current_hp:
                event_bus.publish(Events.CHARACTER_HP_CHANGE, {
                    "character": character,
                    "change": -(old_hp - character.current_hp),
                    "current": character.current_hp,
                    "max": character.max_hp
                })

            logger.critical(f"{character.name} 폭주 상태! 공격력 +100%, 받는 피해 +50%, HP -{hp_loss} (잔여: {character.current_hp})")

        # 위험 구간 (effective_danger_min ~ 99)
        elif madness >= effective_danger_min:
            character.stat_manager.add_bonus(Stats.STRENGTH, "madness_bonus", base_attack * 0.50)
            character.stat_manager.add_bonus(Stats.SPEED, "madness_bonus", base_speed * 0.30)
            character._is_rampaging = False
            character._madness_zone = "danger"
            character._madness_crit_bonus = 0.15  # 크리티컬 +15%
            character._madness_damage_taken_mult = 1.30  # 받는 피해 +30%

            # 매턴 HP 5% 감소 (위험의 대가)
            hp_loss = int(character.max_hp * 0.05)
            old_hp = character.current_hp
            character.current_hp = max(1, character.current_hp - hp_loss)
            
            # UI 업데이트를 위한 이벤트 발행
            if old_hp != character.current_hp:
                event_bus.publish(Events.CHARACTER_HP_CHANGE, {
                    "character": character,
                    "change": -(old_hp - character.current_hp),
                    "current": character.current_hp,
                    "max": character.max_hp
                })

            logger.warning(f"{character.name} 위험 구간! 공격력 +50%, 받는 피해 +30%, HP -{hp_loss} (잔여: {character.current_hp})")

        # 최적 구간 (effective_optimal_min ~ effective_optimal_max)
        elif madness >= effective_optimal_min:
            character.stat_manager.add_bonus(Stats.STRENGTH, "madness_bonus", base_attack * 0.25)
            character.stat_manager.add_bonus(Stats.SPEED, "madness_bonus", base_speed * 0.15)
            character._is_rampaging = False
            character._madness_zone = "optimal"
            character._madness_crit_bonus = 0
            character._madness_damage_taken_mult = 1.0
            logger.info(f"{character.name} 최적 구간! 공격력 +25%, 속도 +15%")
            
        # 안전 구간 (0 ~ effective_optimal_min-1)
        else:
            character._is_rampaging = False
            character._madness_zone = "safe"
            character._madness_crit_bonus = 0
            character._madness_damage_taken_mult = 1.0
            logger.debug(f"{character.name} 안전 구간. 보너스 없음.")
        
        # === 피의 방패: 보호막 지속시간 감소 (턴 종료 시에만) ===
        if is_turn_end:
            shield_duration = getattr(character, 'shield_duration', 0)
            current_shield = getattr(character, 'current_shield', 0)
            if shield_duration > 0 and current_shield > 0:
                character.shield_duration -= 1
                if character.shield_duration <= 0:
                    # 보호막 만료
                    character.current_shield = 0
                    character.shield_duration = 0
                    logger.info(f"{character.name} 피의 방패 만료! 보호막 소멸")
                else:
                    logger.debug(f"{character.name} 피의 방패: {current_shield} (남은 턴: {character.shield_duration})")
        
            # === 절망의 힘: 매턴 HP 감소 + 공격력 재계산 (턴 종료 시에만) ===
            if hasattr(character, 'active_buffs') and 'desperate_strength' in character.active_buffs:
                buff_data = character.active_buffs['desperate_strength']
                hp_drain = buff_data.get('hp_drain', 0.08)
                max_bonus = buff_data.get('max_bonus', 0.5)
                
                # HP 8% 감소
                hp_loss = int(character.max_hp * hp_drain)
                character.current_hp = max(1, character.current_hp - hp_loss)
                logger.info(f"{character.name} 절망의 힘: HP -{hp_loss} ({hp_drain*100:.0f}%)")
                
                # HP 비율에 따라 공격력 보너스 재계산
                hp_ratio = character.current_hp / character.max_hp if character.max_hp > 0 else 1.0
                missing_hp_ratio = 1.0 - hp_ratio
                new_atk_bonus = max_bonus * missing_hp_ratio
                buff_data['value'] = new_atk_bonus
                
                # status_manager의 버프도 업데이트 (공격력 재계산)
                if hasattr(character, 'status_manager'):
                    from src.combat.status_effects import StatusType
                    for effect in character.status_manager.status_effects:
                        if effect.name == "절망의 힘":
                            effect.intensity = new_atk_bonus
                            if hasattr(effect, 'stat_changes'):
                                effect.stat_changes = {
                                    "physical_attack": new_atk_bonus,
                                    "magic_attack": new_atk_bonus
                                }
                            break
                
                # 지속시간 감소
                buff_data['duration'] -= 1
                if buff_data['duration'] <= 0:
                    del character.active_buffs['desperate_strength']
                    # status_manager에서도 제거
                    if hasattr(character, 'status_manager'):
                        from src.combat.status_effects import StatusType
                        for effect in character.status_manager.status_effects[:]:
                            if effect.name == "절망의 힘":
                                character.status_manager.status_effects.remove(effect)
                                break
                    logger.info(f"{character.name} 절망의 힘 만료!")
                else:
                    logger.debug(f"{character.name} 절망의 힘: 공격력 +{int(new_atk_bonus*100)}% (남은 턴: {buff_data['duration']})")

    @staticmethod
    def _update_thirst_gauge(character):
        """흡혈귀: 갈증 게이지 시스템 업데이트"""
        thirst = getattr(character, 'thirst', 0)
        
        # 갈증 100: 치명적 리스크 (HP 10% 감소, MP 20% 감소)
        if thirst >= 100:
            critical_hp_loss = int(character.max_hp * 0.10)
            character.current_hp = max(1, character.current_hp - critical_hp_loss)
            mp_loss = int(character.max_mp * 0.2)
            character.current_mp = max(0, character.current_mp - mp_loss)
            logger.critical(f"{character.name} 최대 갈증! HP -{critical_hp_loss}, MP -{mp_loss} (총 HP: {character.current_hp}, MP: {character.current_mp})")
        # 갈증 95-99: HP 지속 감소 (8%)
        elif thirst >= 95:
            hp_loss = int(character.max_hp * 0.08)
            character.current_hp = max(1, character.current_hp - hp_loss)
            logger.warning(f"{character.name} 혈액 광란: HP -{hp_loss} (총 HP: {character.current_hp})")
        # 갈증 90-94: HP 지속 감소 (5%)
        elif thirst >= 90:
            hp_loss = int(character.max_hp * 0.05)
            character.current_hp = max(1, character.current_hp - hp_loss)
            logger.warning(f"{character.name} 극심한 갈증: HP -{hp_loss} (총 HP: {character.current_hp})")

    @staticmethod
    def _update_probability_distortion(character):
        """차원술사: 확률 왜곡 게이지 시스템 업데이트"""
        # 게이지는 턴 시작 시 on_turn_start에서 증가
        # 턴 종료 시에는 특별한 업데이트 없음
        pass

    @staticmethod
    def _update_mp_overload_state(character):
        """무당: MP 상태와 과부하 게이지 처리"""
        max_gauge = getattr(character, "max_overload_gauge", 5)
        # MP 상태 재계산
        effective_max = character.effective_max_mp() if hasattr(character, "effective_max_mp") else character.max_mp
        mp_ratio = 0
        if effective_max > 0 and hasattr(character, "current_mp"):
            mp_ratio = character.current_mp / effective_max

        last_state = getattr(character, "last_mp_state", None)
        new_state = None
        danger = character.gimmick_data.get("mp_state_effects", {}).get("danger", {})
        danger_min = danger.get("threshold", 0.2)
        danger_max = danger.get("max_threshold", 0.49)
        depleted = character.gimmick_data.get("mp_state_effects", {}).get("depleted", {})
        dep_max = depleted.get("max_threshold", 0.19)

        if mp_ratio <= dep_max:
            new_state = "depleted"
        elif danger_min <= mp_ratio <= danger_max:
            new_state = "danger"
        else:
            new_state = "stable"

        if new_state != last_state:
            character.last_mp_state = new_state
            logger.info(f"[MP 과부하] {character.name} MP 상태 변경: {last_state} → {new_state} ({mp_ratio*100:.0f}%)")

        # 과부하 게이지 최대 시 자동 발동
        gauge = getattr(character, "overload_gauge", 0)
        if gauge >= max_gauge:
            auto_skill = character.gimmick_data.get("gauge_effects", {}).get(max_gauge, {}).get("auto_trigger")
            if auto_skill:
                try:
                    from src.character.skills.skill_manager import get_skill_manager
                    # 가능한 한 전투 컨텍스트를 전달하여 대상 자동 선택
                    combat_manager = None
                    try:
                        from src.combat.combat_manager import get_combat_manager
                        combat_manager = get_combat_manager()
                    except Exception:
                        combat_manager = None
                    enemies = []
                    if combat_manager:
                        if hasattr(combat_manager, "enemies"):
                            enemies = [e for e in combat_manager.enemies if getattr(e, "is_alive", True)]
                    context = {
                        "auto_overload": True,
                        "combat_manager": combat_manager,
                        "all_enemies": enemies,
                    }
                    sm = get_skill_manager()
                    result = sm.execute_skill(auto_skill, character, None, context=context)
                    logger.info(f"[MP 과부하] 자동 발동: {auto_skill} (성공={result.success})")
                except Exception as exc:
                    logger.error(f"[MP 과부하] 자동 발동 실패: {auto_skill} ({exc})")
            character.overload_gauge = 0

    @staticmethod
    def _update_stealth_exposure(character):
        """암살자: 은신-노출 딜레마 시스템 업데이트"""
        # 노출 상태에서 턴 경과 체크
        if not character.stealth_active:
            character.exposed_turns += 1
            logger.debug(f"{character.name} 노출 턴 경과: {character.exposed_turns}/{character.restealth_cooldown}")

            # 노출 스택 증가 (턴마다 +1, 최대치는 특성에 따라 3→2)
            max_stacks = getattr(character, "max_exposed_stacks", 3)
            # 특성 quick_restealth가 있으면 최대치 2로 감소
            if hasattr(character, "traits"):
                if any((t if isinstance(t, str) else t.get("id")) == "quick_restealth" for t in character.traits):
                    max_stacks = 2
            if not hasattr(character, "exposed_stacks"):
                character.exposed_stacks = 0
            if character.exposed_stacks < max_stacks:
                character.exposed_stacks += 1
                logger.info(f"[암살자 노출] {character.name} 노출 스택 {character.exposed_stacks}/{max_stacks}")

            # 3턴 경과 시 재은신 가능 (자동 전환은 하지 않음, 스킬로만 가능)
            if character.exposed_turns >= character.restealth_cooldown:
                logger.info(f"{character.name} 재은신 가능!")

    @staticmethod
    def _consume_bullet(character, skill):
        """저격수: 탄환 소비"""
        if not hasattr(character, 'magazine'):
            return 0

        bullets_used = skill.metadata.get('bullets_used', 0)
        uses_magazine = skill.metadata.get('uses_magazine', False)
        uses_all_bullets = skill.metadata.get('uses_all_bullets', False)

        # 데드아이: 모든 탄환 사용
        if uses_all_bullets:
            bullets_to_use = len(character.magazine)
            if bullets_to_use == 0:
                logger.warning(f"{character.name} 데드아이 사용 실패: 탄창 비어있음")
                return 0

            # 모든 탄환 소비
            consumed_bullets = []
            while len(character.magazine) > 0:
                consumed_bullets.append(character.magazine.pop(0))

            logger.info(f"{character.name} 데드아이: {bullets_to_use}발 전탄 발사!")
            return bullets_to_use

        if not uses_magazine or bullets_used == 0:
            return 0

        # 탄환 절약 특성 체크
        if hasattr(character, 'active_traits'):
            if any((t if isinstance(t, str) else t.get('id')) == 'bullet_conservation' for t in character.active_traits):
                import random
                if random.random() < 0.3:  # 30% 확률로 탄환 소모 안 함
                    logger.info(f"{character.name} 탄환 절약 발동!")
                    return 0

        # 탄환 소비
        consumed = 0
        for _ in range(bullets_used):
            if len(character.magazine) > 0:
                used_bullet = character.magazine.pop(0)
                logger.debug(f"{character.name} 탄환 발사: {used_bullet}")
                consumed += 1

        # 탄창이 비었으면 권총 모드로 전환
        if len(character.magazine) == 0:
            logger.warning(f"{character.name} 탄창 비움! 권총 모드")

        return consumed


    # === ISSUE-004: 신규 기믹 업데이트 로직 (1/3) ===

    @staticmethod
    def _update_sword_aura(character):
        """검성: 검기 시스템 업데이트"""
        # 검기는 공격 시 자동 획득하므로 자동 증가 없음 (YAML 기준 max=5)
        # 최대값 제한만 체크
        sword_aura = getattr(character, 'sword_aura', 0)
        
        # 기본 최대값 (YAML에서 설정된 값 또는 기본 5)
        base_max_aura = getattr(character, 'base_max_sword_aura', None)
        if base_max_aura is None:
            # 최초 호출 시 현재 max_sword_aura를 기본값으로 저장
            base_max_aura = getattr(character, 'max_sword_aura', 5)
            # 이미 특성 보너스가 적용된 경우를 대비해 기본값 5로 설정
            if base_max_aura > 5:
                base_max_aura = 5
            character.base_max_sword_aura = base_max_aura
        
        max_aura = base_max_aura
        
        # 검기 숙련 특성 (sword_aura_mastery): 검기 최대치 +2
        def has_trait(char, trait_id_to_check):
            for attr in ['active_traits', 'available_traits', 'traits', 'selected_traits']:
                if hasattr(char, attr) and getattr(char, attr):
                    for t in getattr(char, attr):
                        tid = t if isinstance(t, str) else (t.get('id') if isinstance(t, dict) else None)
                        if tid == trait_id_to_check:
                            return True
            return False
        
        if has_trait(character, 'sword_aura_mastery'):
            max_aura += 2
        
        character.max_sword_aura = max_aura
        
        if sword_aura > max_aura:
            character.sword_aura = max_aura

    @staticmethod
    def _update_crowd_cheer(character):
        """검투사: 콜로세움 쇼타임 시스템 업데이트 (리메이크)"""
        cheer = getattr(character, 'cheer', 0)
        
        # 환호 단계 계산
        GimmickUpdater._update_cheer_tier(character)
        
        # 환호 자연 감소 (매 턴 -5, 리메이크에서 완화)
        # 단, 95 이상에서는 감쇠하지 않아 100 달성이 가능하도록 함
        decay = 0 if cheer >= 95 else 5
        # 쇼스토퍼 특성: 감소량 50% 감소
        if decay > 0 and hasattr(character, 'active_traits'):
            for trait in character.active_traits:
                tid = trait if isinstance(trait, str) else trait.get('id')
                if tid == 'showstopper':
                    decay = int(decay * 0.5)
                    break
        
        if decay > 0:
            character.cheer = max(0, cheer - decay)
            logger.debug(f"{character.name} 환호 자연 감소: -{decay} (총: {character.cheer})")
    
    @staticmethod
    def _update_cheer_tier(character):
        """환호 단계 계산"""
        cheer = getattr(character, 'cheer', 0)
        cheer_tiers = getattr(character, 'cheer_tiers', {})
        
        old_tier = getattr(character, 'cheer_tier', 'nameless')
        new_tier = 'nameless'
        
        for tier_id, tier_data in cheer_tiers.items():
            tier_min = tier_data.get('min', 0)
            tier_max = tier_data.get('max', 100)
            if tier_min <= cheer <= tier_max:
                new_tier = tier_id
                break
        
        if new_tier != old_tier:
            character.cheer_tier = new_tier
            tier_name = cheer_tiers.get(new_tier, {}).get('name', new_tier)
            GimmickUpdater._push_ui_log(character, f'[환호 단계] {tier_name} 달성')
    
    @staticmethod
    def generate_crowd_demand(character):
        """라운드 시작 시 관중의 요구 생성 (상황별 가중치 적용)"""
        import random

        if not hasattr(character, 'gimmick_type') or character.gimmick_type != "crowd_cheer":
            return None

        crowd_demands = getattr(character, 'crowd_demands', {})
        if not crowd_demands:
            return None

        # 전투 상황 분석
        hp_percent = (character.current_hp / character.max_hp * 100) if character.max_hp > 0 else 100
        cheer = getattr(character, 'cheer', 0)
        consecutive_fails = getattr(character, 'consecutive_demand_fails', 0)

        # 전투 매니저에서 적 정보 가져오기
        enemy_count = 1
        is_boss = False
        if hasattr(character, '_combat_manager') and character._combat_manager:
            enemy_count = len(character._combat_manager.enemies)
            is_boss = any(getattr(e, 'is_boss', False) for e in character._combat_manager.enemies)

        # 상황별 가중치 계산
        weighted_demands = []
        for demand_id, demand_data in crowd_demands.items():
            difficulty = demand_data.get('difficulty', 'normal')
            condition = demand_data.get('condition', '')

            # 기본 난이도 가중치
            base_weight = {'easy': 3, 'normal': 2, 'hard': 1, 'very_hard': 0.5}.get(difficulty, 2)

            # 상황별 가중치 배수
            context_multiplier = 1.0

            # HP 상태에 따른 가중치
            if hp_percent < 30:
                # 저체력: 생존 관련 요구 선호
                if condition in ['survive_hit', 'low_hp_kill', 'survive_massive_damage']:
                    context_multiplier *= 2.5
                elif condition in ['no_damage_kill', 'dodge_3']:
                    context_multiplier *= 1.8
            elif hp_percent > 70:
                # 고체력: 공격적 요구 선호
                if condition in ['critical_2', 'act_twice', 'hp_30_single']:
                    context_multiplier *= 1.5

            # 환호 단계에 따른 가중치
            if cheer < 30:
                # 환호 낮음: 쉬운 요구 선호
                if difficulty == 'easy':
                    context_multiplier *= 2.0
                elif difficulty in ['hard', 'very_hard']:
                    context_multiplier *= 0.5
            elif cheer >= 60:
                # 환호 높음: 어려운 요구 선호
                if difficulty in ['hard', 'very_hard']:
                    context_multiplier *= 2.0
                elif difficulty == 'easy':
                    context_multiplier *= 0.7

            # 적 수에 따른 가중치
            if enemy_count >= 3:
                # 다수 적: 광역 관련 요구 선호
                if condition in ['damage_3_enemies', 'hit_all_enemies', 'multi_attack_4']:
                    context_multiplier *= 2.0
            elif enemy_count <= 2:
                # 소수 적: 단일 대상 요구 선호
                if condition in ['attack_same_twice', 'hp_30_single', 'execute_low_hp']:
                    context_multiplier *= 1.5

            # 보스전 가중치
            if is_boss:
                if condition in ['boss_kill', 'survive_massive_damage', 'low_hp_kill']:
                    context_multiplier *= 2.5
                # 보스전에서는 어려운 요구도 더 자주
                if difficulty in ['hard', 'very_hard']:
                    context_multiplier *= 1.3

            # 연속 실패 시 쉬운 요구 우대
            if consecutive_fails >= 2:
                if difficulty == 'easy':
                    context_multiplier *= 3.0
                elif difficulty in ['hard', 'very_hard']:
                    context_multiplier *= 0.3

            # 최종 가중치 계산
            final_weight = max(0.1, base_weight * context_multiplier)

            # 가중치에 따라 리스트에 추가 (정수로 변환)
            count = max(1, int(final_weight * 10))
            weighted_demands.extend([(demand_id, demand_data)] * count)

        if weighted_demands:
            demand_id, demand_data = random.choice(weighted_demands)
            character.current_demand = {
                'id': demand_id,
                'name': demand_data.get('name', demand_id),
                'condition': demand_data.get('condition', ''),
                'cheer_reward': demand_data.get('cheer_reward', 10),
                'bonus': demand_data.get('bonus', None),
                'fulfilled': False
            }
            character.demand_progress = {}  # 진행 상황 초기화
            GimmickUpdater._push_ui_log(character, f'[관중의 요구] {character.current_demand["name"]}')
            return character.current_demand

        return None
    
    @staticmethod
    def check_demand_fulfillment(character, action_type: str, context: dict = None):
        """관중의 요구 충족 여부 체크"""
        if not hasattr(character, 'current_demand') or not character.current_demand:
            return False

        demand = character.current_demand
        if demand.get('fulfilled'):
            return True
        
        condition = demand.get('condition', '')
        progress = getattr(character, 'demand_progress', {})
        
        # 조건별 체크
        fulfilled = False
        
        # 액션 타입 매핑 보정: combat_manager/on_ally_attack 등에서 들어오는 이벤트명을 통합
        normalized_action = action_type
        if action_type in ['attack', 'brv_attack', 'hp_attack', 'basic_attack']:
            normalized_action = 'attack'
        elif action_type in ['kill', 'enemy_killed', 'finish']:
            normalized_action = 'kill'
        elif action_type in ['critical_hit', 'crit', 'critical']:
            normalized_action = 'critical'
        elif action_type in ['hit_taken', 'damaged', 'damage_taken']:
            normalized_action = 'hit_taken'
        elif action_type in ['action', 'turn_action', 'ally_action']:
            normalized_action = 'action'

        # 조건별 체크
        if condition == 'kill_enemy' and normalized_action == 'kill':
            fulfilled = True
        elif condition == 'counter_success' and normalized_action == 'counter':
            fulfilled = True
        elif condition == 'critical_2' and normalized_action == 'critical':
            progress['critical_count'] = progress.get('critical_count', 0) + 1
            character.demand_progress = progress
            if progress['critical_count'] >= 2:
                fulfilled = True
        elif condition == 'no_damage_kill' and normalized_action == 'kill':
            # 전투 시작 이후 한 번도 HP 감소/회복 변동이 없었는지 체크 (context 플래그 우선)
            no_damage = False
            if context and context.get('no_damage_taken') is True:
                no_damage = True
            else:
                no_damage = getattr(character, 'took_damage_this_round', False) is False and \
                            getattr(character, 'healed_this_round', False) is False
            if no_damage:
                fulfilled = True
        elif condition == 'survive_hit' and normalized_action == 'hit_taken':
            # 한 번이라도 피격 시 충족
            fulfilled = True
        elif condition == 'act_twice' and normalized_action == 'action':
            progress['action_count'] = progress.get('action_count', 0) + 1
            character.demand_progress = progress
            if progress['action_count'] >= 2:
                fulfilled = True
        elif condition == 'hp_30_single' and normalized_action in ['hp_damage', 'hp_attack', 'attack']:
            # context에 피해 비율 전달 필요. 없으면 실패 방지 위해 0 처리
            hp_percent = context.get('hp_percent', 0) if context else 0
            if hp_percent >= 30:
                fulfilled = True
        elif condition == 'damage_3_enemies' and normalized_action in ['hit', 'aoe_hit', 'attack']:
            targets = context.get('targets_hit', 1) if context else 1
            if targets >= 3:
                fulfilled = True
        elif condition == 'hit_all_enemies' and normalized_action in ['hit', 'aoe_hit', 'attack']:
            # 전원 적중 여부 (context에서 all_enemies_hit True 기대)
            if context and context.get('all_enemies_hit'):
                fulfilled = True
        elif condition == 'multi_attack_4' and normalized_action in ['attack', 'multi_hit']:
            # 다단히트 카운트 (context.multi_hit_count 전달 기대)
            hit_count = context.get('multi_hit_count', 1) if context else 1
            if hit_count >= 4:
                fulfilled = True
        elif condition == 'attack_same_twice' and normalized_action == 'attack':
            target_id = context.get('target_id') if context else None
            if target_id:
                prev = progress.get('attack_target')
                if prev == target_id:
                    fulfilled = True
                progress['attack_target'] = target_id
                character.demand_progress = progress
        
        if fulfilled:
            GimmickUpdater._fulfill_demand(character)

        return fulfilled
    
    @staticmethod
    def _fulfill_demand(character):
        """관중의 요구 충족 처리"""
        demand = character.current_demand
        demand['fulfilled'] = True
        
        # 환호 보상
        reward = demand.get('cheer_reward', 10)
        
        # 군중의 총아 특성: 추가 환호 +5
        if hasattr(character, 'active_traits'):
            for trait in character.active_traits:
                tid = trait if isinstance(trait, str) else trait.get('id')
                if tid == 'crowd_favorite':
                    reward += 5
                    break
        
        character.cheer = min(character.max_cheer, character.cheer + reward)
        character.consecutive_boos = 0  # 연속 야유 초기화
        character.consecutive_demand_fails = 0  # 연속 실패 초기화

        GimmickUpdater._push_ui_log(character, f'[요구 충족] {demand["name"]} (환호 +{reward}, 총 {character.cheer})')
        
        # 단계 업데이트
        GimmickUpdater._update_cheer_tier(character)
    
    @staticmethod
    def fail_demand(character):
        """관중의 요구 실패 처리 (야유)"""
        if not hasattr(character, 'current_demand') or not character.current_demand:
            return
        
        demand = character.current_demand
        if demand.get('fulfilled'):
            return
        
        boo_effect = getattr(character, 'boo_effect', {})
        cheer_loss = boo_effect.get('cheer_loss', 15)
        
        # 쇼스토퍼 특성: 야유 감소량 50% 감소
        if hasattr(character, 'active_traits'):
            for trait in character.active_traits:
                tid = trait if isinstance(trait, str) else trait.get('id')
                if tid == 'showstopper':
                    cheer_loss = int(cheer_loss * 0.5)
                    break
        
        # 연속 야유 페널티
        character.consecutive_boos = getattr(character, 'consecutive_boos', 0) + 1
        character.consecutive_demand_fails = getattr(character, 'consecutive_demand_fails', 0) + 1
        if character.consecutive_boos >= 3:
            cheer_loss = int(character.cheer * 0.5)  # 현재 환호의 50% 감소
            logger.warning(f"[연속 야유!] {character.name}: 3연속 야유 - 환호 50% 감소!")

        character.cheer = max(0, character.cheer - cheer_loss)
        GimmickUpdater._push_ui_log(character, f'[야유] {demand["name"]} 실패 - 환호 -{cheer_loss} (총 {character.cheer})')
        
        # 단계 업데이트
        GimmickUpdater._update_cheer_tier(character)

    @staticmethod
    def _update_duty_system(character):
        """기사: 의무 시스템 업데이트"""
        # 의무 게이지는 스킬/특성으로만 변화, 자동 업데이트 없음
        pass

    @staticmethod
    def _update_stance_system(character):
        """전사: 자세 시스템 업데이트"""
        # 턴 종료 시 스탠스별 효과 처리
        stance = getattr(character, 'current_stance', 0)
        
        # 문자열인 경우 정수로 변환
        if isinstance(stance, str):
            stance_id_to_index = {
                "balanced": 0,
                "attack": 1,
                "defense": 2,
                "berserker": 4,
                "guardian": 5,
                "speed": 6
            }
            stance = stance_id_to_index.get(stance, 0)
        
        # 광전사: 매턴 피해
        if stance == 4:  # berserker
            if hasattr(character, 'max_hp'):
                damage = int(character.max_hp * 0.05)  # 최대 HP의 5%
                character.current_hp = max(1, character.current_hp - damage)
                logger.info(f"{character.name} 광전사 자세: 매턴 피해 -{damage} HP")
        
        # 수호자: HP 재생 (MP 재생 제거)
        elif stance == 5:  # guardian
            if hasattr(character, 'max_hp'):
                hp_regen = int(character.max_hp * 0.12)  # 최대 HP의 12%
                old_hp = character.current_hp
                character.current_hp = min(character.max_hp, character.current_hp + hp_regen)
                actual_hp = character.current_hp - old_hp
                if actual_hp > 0:
                    logger.info(f"{character.name} 수호자 자세: HP +{actual_hp}")
    
    @staticmethod
    def _apply_stance_effects(character):
        """전사: 스탠스 효과를 StatManager에 적용"""
        if not hasattr(character, 'stat_manager'):
            return
        
        # 스탠스 변경 시 remove_on_stance_change 플래그가 있는 버프 제거
        if hasattr(character, 'active_buffs') and character.active_buffs:
            buffs_to_remove = []
            for buff_id, buff_data in character.active_buffs.items():
                if isinstance(buff_data, dict) and buff_data.get('remove_on_stance_change'):
                    buffs_to_remove.append(buff_id)
            
            for buff_id in buffs_to_remove:
                del character.active_buffs[buff_id]
                logger.info(f"[스탠스 변경] {character.name}의 '{buff_id}' 버프가 스탠스 변경으로 제거됨")
        
        stance = getattr(character, 'current_stance', 0)
        
        # 문자열인 경우 정수로 변환
        if isinstance(stance, str):
            stance_id_to_index = {
                "balanced": 0,
                "attack": 1,
                "defense": 2,
                "berserker": 4,
                "guardian": 5,
                "speed": 6
            }
            stance = stance_id_to_index.get(stance, 0)
        
        from src.character.stats import Stats
        
        # 기존 스탠스 보너스 제거
        for stat_name in [Stats.STRENGTH, Stats.DEFENSE, Stats.SPIRIT, Stats.SPEED]:
            character.stat_manager.remove_bonus(stat_name, "stance")

        # 스탠스별 피해 경감 초기화 (수호자 전용)
        character.stance_damage_reduction = 0.0
        
        # 스탠스별 효과 적용
        if stance == 0:  # 중립 (balanced)
            # 모든 스탯 그대로 - 보너스 없음
            pass
        
        elif stance == 1:  # 공격 (attack)
            # 공격+40%, 방,마방-25%
            base_attack = character.stat_manager.get_value(Stats.STRENGTH)
            base_defense = character.stat_manager.get_value(Stats.DEFENSE)
            base_magic_def = character.stat_manager.get_value(Stats.SPIRIT)
            
            character.stat_manager.add_bonus(Stats.STRENGTH, "stance", base_attack * 0.40)
            character.stat_manager.add_bonus(Stats.DEFENSE, "stance", -base_defense * 0.25)
            character.stat_manager.add_bonus(Stats.SPIRIT, "stance", -base_magic_def * 0.25)
        
        elif stance == 2:  # 방어 (defense)
            # 방,마방+60%, 공-30%, 속도-30%
            base_attack = character.stat_manager.get_value(Stats.STRENGTH)
            base_defense = character.stat_manager.get_value(Stats.DEFENSE)
            base_magic_def = character.stat_manager.get_value(Stats.SPIRIT)
            base_speed = character.stat_manager.get_value(Stats.SPEED)
            
            character.stat_manager.add_bonus(Stats.DEFENSE, "stance", base_defense * 0.60)
            character.stat_manager.add_bonus(Stats.SPIRIT, "stance", base_magic_def * 0.60)
            character.stat_manager.add_bonus(Stats.STRENGTH, "stance", -base_attack * 0.30)
            character.stat_manager.add_bonus(Stats.SPEED, "stance", -base_speed * 0.30)
        
        elif stance == 4:  # 광전사 (berserker)
            # 속도,공격+55%, 방,마방-45%
            base_attack = character.stat_manager.get_value(Stats.STRENGTH)
            base_defense = character.stat_manager.get_value(Stats.DEFENSE)
            base_magic_def = character.stat_manager.get_value(Stats.SPIRIT)
            base_speed = character.stat_manager.get_value(Stats.SPEED)
            
            character.stat_manager.add_bonus(Stats.STRENGTH, "stance", base_attack * 0.55)
            character.stat_manager.add_bonus(Stats.SPEED, "stance", base_speed * 0.55)
            character.stat_manager.add_bonus(Stats.DEFENSE, "stance", -base_defense * 0.45)
            character.stat_manager.add_bonus(Stats.SPIRIT, "stance", -base_magic_def * 0.45)
        
        elif stance == 5:  # 수호자 (guardian)
            # 받는 피해 70% 경감, 공격력/마법공격력/속도 -60%
            base_attack = character.stat_manager.get_value(Stats.STRENGTH)
            base_magic = character.stat_manager.get_value(Stats.MAGIC)
            base_speed = character.stat_manager.get_value(Stats.SPEED)

            character.stat_manager.add_bonus(Stats.STRENGTH, "stance", -base_attack * 0.60)
            character.stat_manager.add_bonus(Stats.MAGIC, "stance", -base_magic * 0.60)
            character.stat_manager.add_bonus(Stats.SPEED, "stance", -base_speed * 0.60)
            character.stance_damage_reduction = 0.70
        
        elif stance == 6:  # 속도 (speed)
            # 속도+80%, 방,마방,공-25%
            base_attack = character.stat_manager.get_value(Stats.STRENGTH)
            base_defense = character.stat_manager.get_value(Stats.DEFENSE)
            base_magic_def = character.stat_manager.get_value(Stats.SPIRIT)
            base_speed = character.stat_manager.get_value(Stats.SPEED)
            
            character.stat_manager.add_bonus(Stats.SPEED, "stance", base_speed * 0.80)
            character.stat_manager.add_bonus(Stats.STRENGTH, "stance", -base_attack * 0.25)
            character.stat_manager.add_bonus(Stats.DEFENSE, "stance", -base_defense * 0.25)
            character.stat_manager.add_bonus(Stats.SPIRIT, "stance", -base_magic_def * 0.25)

    @staticmethod
    def _update_iaijutsu_system(character):
        """사무라이: 거합 시스템 업데이트"""
        # 의지 게이지 자연 증가 (매 턴 +1) - YAML: max_will_gauge
        will_gauge = getattr(character, 'will_gauge', 0)
        max_will = getattr(character, 'max_will_gauge', 10)
        character.will_gauge = min(max_will, will_gauge + 1)
        logger.debug(f"{character.name} 의지 게이지 증가: +1 (총: {character.will_gauge})")

    @staticmethod
    def _update_dragon_marks(character):
        """용기사: 드래곤 마크 시스템 업데이트"""
        # 용표는 용력이 최대치에 도달할 때 자동 획득 (GimmickEffect에서 처리)
        # 용표 3개 도달 시 드래곤 변신 가능 상태 표시
        marks = getattr(character, 'dragon_marks', 0)
        max_marks = getattr(character, 'max_dragon_marks', 3)
        if marks >= max_marks:
            character.dragon_transform_ready = True
            if not hasattr(character, '_dragon_transform_notified') or not character._dragon_transform_notified:
                logger.info(f"{character.name} 드래곤 변신 준비 완료! (용표 {marks}/{max_marks})")
                character._dragon_transform_notified = True
        else:
            character.dragon_transform_ready = False
            character._dragon_transform_notified = False

    @staticmethod
    def _update_holy_system(character):
        """성직자: 신성 시스템 업데이트"""
        # 신성력 자연 증가 (매 턴 +5)
        holy = getattr(character, 'holy_gauge', 0)
        max_holy = getattr(character, 'max_holy_gauge', 100)
        character.holy_gauge = min(max_holy, holy + 5)
        logger.debug(f"{character.name} 신성력 증가: +5 (총: {character.holy_gauge})")

    @staticmethod
    def _update_divinity_system(character):
        """성기사/대마법사: 신성력 시스템 업데이트"""
        # 신성력 자연 증가 (매 턴 +3, 성직자보다 느림)
        divinity = getattr(character, 'divinity', 0)
        max_divinity = getattr(character, 'max_divinity', 100)
        character.divinity = min(max_divinity, divinity + 3)
        logger.debug(f"{character.name} 신성력 증가: +3 (총: {character.divinity})")

    @staticmethod
    def _update_darkness_system(character):
        """암흑기사: 암흑 시스템 업데이트"""
        # 암흑력 자연 증가 (매 턴 +5)
        darkness = getattr(character, 'darkness_gauge', 0)
        max_darkness = getattr(character, 'max_darkness_gauge', 100)
        character.darkness_gauge = min(max_darkness, darkness + 5)
        logger.debug(f"{character.name} 암흑력 증가: +5 (총: {character.darkness_gauge})")

    # === ISSUE-004: 신규 기믹 업데이트 로직 (2/3) ===

    @staticmethod
    def _update_undead_legion(character):
        """네크로맨서: 언데드 군단 시스템 업데이트"""
        # 소환된 언데드는 스킬로만 관리, 자동 업데이트 없음
        # 최대 5개까지 유지
        skeleton = getattr(character, 'undead_skeleton', 0)
        zombie = getattr(character, 'undead_zombie', 0)
        ghost = getattr(character, 'undead_ghost', 0)
        total = skeleton + zombie + ghost
        max_undead = getattr(character, 'max_undead_total', 5)
        if total > max_undead:
            # 초과분 제거 (우선순위: ghost > zombie > skeleton)
            excess = total - max_undead
            while excess > 0 and ghost > 0:
                ghost -= 1
                excess -= 1
            while excess > 0 and zombie > 0:
                zombie -= 1
                excess -= 1
            while excess > 0 and skeleton > 0:
                skeleton -= 1
                excess -= 1
            character.undead_skeleton = skeleton
            character.undead_zombie = zombie
            character.undead_ghost = ghost
    
    @staticmethod
    def _undead_auto_attack(character, context):
        """네크로맨서: 언데드 자동 공격"""
        if not context:
            return
        
        enemies = context.get('enemies', [])
        if not enemies:
            return
        
        # 살아있는 적만 필터링
        alive_enemies = [e for e in enemies if hasattr(e, 'is_alive') and e.is_alive]
        if not alive_enemies:
            return
        
        skeleton = getattr(character, 'undead_skeleton', 0)
        zombie = getattr(character, 'undead_zombie', 0)
        ghost = getattr(character, 'undead_ghost', 0)
        
        # 네크로맨서의 스탯 가져오기
        from src.character.stats import Stats
        base_attack = 0
        base_magic = 0
        if hasattr(character, 'stat_manager'):
            base_attack = character.stat_manager.get_value(Stats.STRENGTH)
            base_magic = character.stat_manager.get_value(Stats.MAGIC)
        else:
            base_attack = getattr(character, 'physical_attack', 0)
            base_magic = getattr(character, 'magic_attack', 0)
        
        import random
        
        def select_target(enemy_list, strategy="smart"):
            """언데드가 자율적으로 적을 선택"""
            if not enemy_list:
                return None
            
            if strategy == "weakest":
                # 가장 약한 적 (HP가 가장 낮은 적)
                return min(enemy_list, key=lambda e: getattr(e, 'current_hp', 0))
            elif strategy == "strongest":
                # 가장 강한 적 (HP가 가장 높은 적)
                return max(enemy_list, key=lambda e: getattr(e, 'current_hp', 0))
            elif strategy == "random":
                # 랜덤 선택
                return random.choice(enemy_list)
            else:  # "smart" - 지능적 선택
                # HP 비율이 낮은 적 우선 (마무리), 그 외는 랜덤
                hp_ratios = []
                for enemy in enemy_list:
                    max_hp = getattr(enemy, 'max_hp', 1)
                    current_hp = getattr(enemy, 'current_hp', 0)
                    ratio = current_hp / max_hp if max_hp > 0 else 1.0
                    hp_ratios.append((enemy, ratio))
                
                # HP 비율이 30% 이하인 적이 있으면 그 중 가장 약한 적 선택
                low_hp_enemies = [e for e, ratio in hp_ratios if ratio <= 0.3]
                if low_hp_enemies:
                    return min(low_hp_enemies, key=lambda e: getattr(e, 'current_hp', 0))
                
                # 그 외는 랜덤 선택
                return random.choice(enemy_list)
        
        # 스켈레톤: 물리 공격 (네크로맨서의 물리 공격력 + 마법력의 일부 기반, HP 공격)
        # 스켈레톤은 지능적으로 적을 선택 (약한 적 우선)
        for i in range(skeleton):
            if not alive_enemies:
                break
            target = select_target(alive_enemies, strategy="smart")
            if not target:
                break
            
            # 스켈레톤 공격력: 네크로맨서 물리 공격력의 60% + 마법력의 20%
            skeleton_brv = int(base_attack * 0.6 + base_magic * 0.2)
            # 단순히 brv_points를 데미지로 사용
            damage = max(1, skeleton_brv)
            
            if damage > 0:
                target.take_damage(damage)
                logger.info(f"💀 스켈레톤이 {target.name}에게 {damage} HP 피해!")
        
        # 좀비: 방어/탱킹 (약한 물리 HP 공격)
        # 좀비는 랜덤으로 적을 선택 (탱킹 역할)
        for i in range(zombie):
            if not alive_enemies:
                break
            target = select_target(alive_enemies, strategy="random")
            if not target:
                break
            
            # 좀비 공격력: 네크로맨서 물리 공격력의 40% + 마법력의 10% (약한 공격)
            zombie_brv = int(base_attack * 0.4 + base_magic * 0.1)
            # 단순히 brv_points를 데미지로 사용
            damage = max(1, zombie_brv)
            
            if damage > 0:
                target.take_damage(damage)
                logger.info(f"🧟 좀비가 {target.name}에게 {damage} HP 피해!")
        
        # 유령: 마법 공격 (네크로맨서의 마법 공격력 기반, HP 공격)
        # 유령은 가장 강한 적을 집중 공격 (디버프 역할)
        for i in range(ghost):
            if not alive_enemies:
                break
            target = select_target(alive_enemies, strategy="strongest")
            if not target:
                break
            
            # 유령 공격력: 네크로맨서 마법 공격력의 70%
            ghost_brv = int(base_magic * 0.7)
            # 단순히 brv_points를 데미지로 사용
            damage = max(1, ghost_brv)
            
            if damage > 0:
                target.take_damage(damage)
                logger.info(f"👻 유령이 {target.name}에게 {damage} HP 피해!")

    @staticmethod
    def _update_theft_system(character):
        """도적: 절도 시스템 업데이트"""
        # 훔친 아이템/버프는 스킬로만 관리, 자동 업데이트 없음
        pass

    @staticmethod
    def _update_shapeshifting_system(character):
        """드루이드: 변신 시스템 업데이트"""
        # 변신 형태는 스킬로만 변경, 자동 업데이트 없음
        pass

    @staticmethod
    def _update_enchant_system(character):
        """마검사: 마법부여 시스템 업데이트"""
        # 부여된 속성은 스킬로만 변경, 자동 업데이트 없음
        pass

    @staticmethod
    def _update_curse_system(character):
        """무당: 저주 시스템 업데이트 (하위 호환성을 위해 기존 totem_system 지원)"""
        # 저주 스택 자동 업데이트 없음 (스킬로만 변경)
        # 최대 저주 스택 유지
        curse_stacks = getattr(character, 'curse_stacks', 0)
        max_curse_stacks = getattr(character, 'max_curse_stacks', 10)
        if curse_stacks > max_curse_stacks:
            character.curse_stacks = max_curse_stacks
        
        # 하위 호환성: 토템 시스템이 있으면 처리 (더 이상 사용되지 않음)
        totems = getattr(character, 'active_totems', [])
        if len(totems) > 3:
            character.active_totems = totems[:3]

    @staticmethod
    def _update_melody_system(character):
        """바드: 선율 시스템 업데이트"""
        # 음표 자연 증가 (매 턴 +1)
        notes = getattr(character, 'melody_notes', 0)
        max_notes = getattr(character, 'max_melody_notes', 8)
        character.melody_notes = min(max_notes, notes + 1)
        logger.debug(f"{character.name} 음표 증가: +1 (총: {character.melody_notes})")

    @staticmethod
    def _update_break_system(character):
        """브레이커: 브레이크 시스템 업데이트"""
        # 브레이크 보너스 자연 감소 (매 턴 -5%)
        bonus = getattr(character, 'break_bonus', 0)
        character.break_bonus = max(0, bonus - 5)
        logger.debug(f"{character.name} 브레이크 보너스 감소: -5% (총: {character.break_bonus}%)")

    @staticmethod
    def _update_elemental_counter(character):
        """엘리멘탈리스트: 속성 카운터 시스템 업데이트"""
        # 속성 스택은 스킬로만 축적, 자동 업데이트 없음
        # 최대 5스택까지 유지
        for element in ['fire', 'ice', 'lightning']:
            stacks = getattr(character, f'{element}_stacks', 0)
            if stacks > 5:
                setattr(character, f'{element}_stacks', 5)

    @staticmethod
    def _update_alchemy_system(character):
        """연금술사: 연금 시스템 업데이트"""
        # 촉매는 스킬로만 변경, 자동 업데이트 없음
        pass

    @staticmethod
    def _update_elemental_spirits(character):
        """정령술사: 정령 전환 시스템 업데이트 (리메이크)"""
        # 정령별 턴 종료 버프 효과 적용
        
        # 물 정령: MP +5/턴
        if getattr(character, 'spirit_water', 0) > 0:
            mp_regen = 5
            if hasattr(character, 'current_mp') and hasattr(character, 'max_mp'):
                old_mp = character.current_mp
                character.current_mp = min(character.max_mp, character.current_mp + mp_regen)
                actual_regen = character.current_mp - old_mp
                if actual_regen > 0:
                    logger.info(f"[물 정령] {character.name} MP +{actual_regen} (총: {character.current_mp})")
        
        # 대지 정령: HP +3/턴
        if getattr(character, 'spirit_earth', 0) > 0:
            hp_regen = 3
            if hasattr(character, 'current_hp') and hasattr(character, 'max_hp'):
                old_hp = character.current_hp
                character.current_hp = min(character.max_hp, character.current_hp + hp_regen)
                actual_regen = character.current_hp - old_hp
                if actual_regen > 0:
                    logger.info(f"[대지 정령] {character.name} HP +{actual_regen} (총: {character.current_hp})")
        
        # 생명 공명 (물+대지): HP/MP 동시 회복 추가
        if getattr(character, 'spirit_water', 0) > 0 and getattr(character, 'spirit_earth', 0) > 0:
            resonance_mult = getattr(character, 'resonance_multiplier', 1.0)
            bonus_regen = int(3 * resonance_mult)
            if hasattr(character, 'current_hp') and hasattr(character, 'max_hp'):
                old_hp = character.current_hp
                character.current_hp = min(character.max_hp, character.current_hp + bonus_regen)
                hp_bonus = character.current_hp - old_hp
                if hp_bonus > 0:
                    logger.info(f"[생명 공명] {character.name} 추가 HP +{hp_bonus}")
            if hasattr(character, 'current_mp') and hasattr(character, 'max_mp'):
                old_mp = character.current_mp
                character.current_mp = min(character.max_mp, character.current_mp + bonus_regen)
                mp_bonus = character.current_mp - old_mp
                if mp_bonus > 0:
                    logger.info(f"[생명 공명] {character.name} 추가 MP +{mp_bonus}")
        
        # 공명 효과 업데이트
        GimmickUpdater._update_spirit_resonance(character)
    
    @staticmethod
    def _update_spirit_resonance(character):
        """정령 공명 효과 계산 및 적용"""
        max_spirits = getattr(character, 'max_spirits', 2) or 2
        # 슬롯 정보 우선 사용해 활성 정령 정렬
        slots = list(getattr(character, 'spirit_slots', []))
        # 필드 상태와 싱크 맞추기 (잘못된 슬롯 정리)
        synced_slots = []
        for s in slots:
            if getattr(character, f"spirit_{s}", 0) > 0:
                synced_slots.append(s)
        slots = synced_slots
        # 필드에 있는데 슬롯에 없는 정령 추가 (최신 추가 순서는 중요치 않지만 채워줌)
        for s in ['fire', 'water', 'wind', 'earth']:
            if getattr(character, f"spirit_{s}", 0) > 0 and s not in slots:
                slots.append(s)
        # 초과 정령은 오래된 것부터 제거
        while len(slots) > max_spirits:
            oldest = slots.pop(0)
            setattr(character, f"spirit_{oldest}", 0)
            logger.info(f"[정령 정리] {oldest} 정령 제거 (슬롯 초과)")
        character.spirit_slots = slots

        active_spirits = slots[:max_spirits]

        # 공명 효과 결정 (2마리 소환 시만 - 슬롯 기반)
        resonance = None
        if len(active_spirits) == 2:
            combo = '_'.join(sorted(active_spirits))
            # 순서 정규화 (fire_water, fire_wind 등)
            resonance_map = {
                'fire_water': 'fire_water',
                'fire_wind': 'fire_wind', 
                'earth_fire': 'fire_earth',
                'water_wind': 'water_wind',
                'earth_water': 'water_earth',
                'earth_wind': 'wind_earth'
            }
            resonance = resonance_map.get(combo, combo)
        
        # 이전 공명과 다르면 로그 출력
        old_resonance = getattr(character, 'active_resonance', None)
        if resonance != old_resonance:
            character.active_resonance = resonance
            if resonance:
                resonance_names = {
                    'fire_water': '증기 공명 (마법 크리 +15%)',
                    'fire_wind': '열풍 공명 (화염 광역화)',
                    'fire_earth': '용암 공명 (화상 +25%, 관통 +10%)',
                    'water_wind': '한랭 공명 (속도 -30% 부여)',
                    'water_earth': '생명 공명 (HP/MP 동시 회복)',
                    'wind_earth': '반사 공명 (회피 +10%, 반사 20%)'
                }
                logger.info(f"[정령 공명] {character.name}: {resonance_names.get(resonance, resonance)}")
    
    @staticmethod
    def summon_spirit(character, spirit_type: str):
        """정령 소환 처리 (자동 교체 포함)"""
        if not hasattr(character, 'gimmick_type') or character.gimmick_type != "elemental_spirits":
            return False
        
        spirit_field = f'spirit_{spirit_type}'
        
        # 이미 소환된 정령이면 무시
        if getattr(character, spirit_field, 0) > 0:
            logger.info(f"[정령술사] {spirit_type} 정령은 이미 소환되어 있습니다.")
            return False
        
        # 현재 소환된 정령 수 확인
        spirit_slots = getattr(character, 'spirit_slots', [])
        max_spirits = getattr(character, 'max_spirits', 2)

        # 슬롯이 가득 찬 경우 가장 오래된 정령 교체
        if len(spirit_slots) >= max_spirits:
            oldest_spirit = spirit_slots.pop(0)
            oldest_field = f'spirit_{oldest_spirit}'
            setattr(character, oldest_field, 0)
            logger.info(f"[정령 교체] {oldest_spirit} 정령 소멸 → {spirit_type} 정령 소환")
        
        # 새 정령 소환
        setattr(character, spirit_field, 1)
        spirit_slots.append(spirit_type)
        character.spirit_slots = spirit_slots

        spirit_names = {'fire': '화염', 'water': '물', 'wind': '바람', 'earth': '대지'}
        logger.info(f"[정령 소환] {character.name}: {spirit_names.get(spirit_type, spirit_type)} 정령 소환!")

        # 공명 효과 업데이트
        GimmickUpdater._update_spirit_resonance(character)
        # 즉시 정령 패시브/공명 효과 적용 (턴 대기 없이)
        GimmickUpdater._update_elemental_spirits(character)

        return True
    
    @staticmethod
    def release_all_spirits(character) -> int:
        """모든 정령 해방 (정령 해방 스킬용)"""
        released_count = 0
        for spirit_type in ['fire', 'water', 'wind', 'earth']:
            spirit_field = f'spirit_{spirit_type}'
            if getattr(character, spirit_field, 0) > 0:
                setattr(character, spirit_field, 0)
                released_count += 1
        
        character.spirit_slots = []
        character.active_resonance = None
        
        if released_count > 0:
            logger.info(f"[정령 해방] {character.name}: {released_count}마리 정령 해방!")
        
        return released_count
    
    @staticmethod
    def swap_spirit_slots(character):
        """정령 슬롯 위치 교환 (정령 교대 스킬용)"""
        spirit_slots = getattr(character, 'spirit_slots', [])
        if len(spirit_slots) >= 2:
            spirit_slots[0], spirit_slots[1] = spirit_slots[1], spirit_slots[0]
            character.spirit_slots = spirit_slots
            logger.info(f"[정령 교대] {character.name}: 정령 슬롯 교환 → {spirit_slots}")

    @staticmethod
    def get_active_spirits_count(character) -> int:
        """현재 소환된 정령 수 반환"""
        return sum([
            getattr(character, 'spirit_fire', 0),
            getattr(character, 'spirit_water', 0),
            getattr(character, 'spirit_wind', 0),
            getattr(character, 'spirit_earth', 0)
        ])

    @staticmethod
    def _update_plunder_system(character):
        """해적: 약탈 시스템 업데이트"""
        # 보물은 스킬(플런더, 약탈)로만 획득
        # 턴 종료 시 자동으로 쌓이지는 않음
        treasure_count = getattr(character, 'treasure_count', 0)

        # 보물 보유 상태 로깅
        if treasure_count > 0:
            logger.info(f"[해적] {character.name}의 보물 보유: {treasure_count}개 (턴 종료)")

        # 보물 관련 처리는 skill_manager.py에서 수행됨
        # - 플런더: treasure_steal_chance로 보물 획득
        # - 보물 폭탄/사용: consume_all_treasure로 모든 보물 소비

    @staticmethod
    def _update_multithread_system(character):
        """해커: 멀티스레드 시스템 업데이트"""
        # 활성 스레드 리스트 관리
        threads = getattr(character, 'active_threads', [])

        # 리스트 타입이 아니면 정수로 처리 (하위 호환성)
        if isinstance(threads, int):
            character.active_threads = max(0, threads - 1)
            if threads > 0:
                logger.debug(f"{character.name} 활성 스레드 감소: -1 (총: {character.active_threads})")
        else:
            # 리스트 타입인 경우 (신버전) - 프로그램 기반 관리로 변경되었으므로 자동 감소 안 함
            # 프로그램들은 program_virus, program_backdoor 등으로 개별 관리됨
            thread_count = len(threads)
            if thread_count > 0:
                logger.debug(f"{character.name} 활성 스레드: {thread_count}개")
        
        # 실행 중인 프로그램 수 계산 (program_* 변수 확인)
        active_programs = 0
        program_fields = ['program_virus', 'program_backdoor', 'program_ddos', 'program_ransomware', 'program_spyware']
        for field in program_fields:
            if getattr(character, field, 0) > 0:
                active_programs += 1
        
        # 프로그램당 MP 소모 (기본값 4, 특성으로 감소 가능)
        if active_programs > 0 and hasattr(character, 'current_mp'):
            mp_per_program = getattr(character, 'mp_per_program_per_turn', 4)
            
            # CPU 최적화 특성 체크 (프로그램당 MP 소모 -2) - TraitEffectManager 사용
            from src.character.trait_effects import get_trait_effect_manager
            trait_manager = get_trait_effect_manager()
            
            if hasattr(character, 'active_traits'):
                for trait_data in character.active_traits:
                    trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                    effects = trait_manager.get_trait_effects(trait_id)
                    
                    for effect in effects:
                        # program_cost 타겟인 MP_COST_REDUCTION 효과 확인
                        from src.character.trait_effects import TraitEffectType
                        if (effect.effect_type == TraitEffectType.MP_COST_REDUCTION and 
                            hasattr(effect, 'target_stat') and 
                            effect.target_stat == "program_cost"):
                            # 고정값 감소 (value는 감소량)
                            mp_per_program = max(1, mp_per_program - int(effect.value))  # 최소 1로 제한
                            logger.debug(f"[{trait_id}] 프로그램 유지 비용 감소: -{effect.value} MP/턴")
            
            total_mp_cost = active_programs * mp_per_program
            actual_mp_cost = min(total_mp_cost, character.current_mp)
            character.current_mp -= actual_mp_cost
            
            if actual_mp_cost > 0:
                logger.info(
                    f"{character.name} 프로그램 유지 비용: {actual_mp_cost} MP "
                    f"(프로그램 {active_programs}개 × {mp_per_program} MP/턴)"
                )

    @staticmethod
    def _update_intrusion_system(character):
        """해커: 침투 시스템 업데이트 (리메이크)"""
        # RAM 회복
        ram_regen = getattr(character, 'ram_regen', None)
        if ram_regen is None:
            ram_regen = getattr(getattr(character, "gimmick_data", {}), "get", lambda k, d=None: d)("ram_regen_per_turn", 1)
        ram_regen = max(0, ram_regen or 1)
        
        # 병렬 처리 특성: RAM +1 추가 회복
        if hasattr(character, 'active_traits'):
            for trait in character.active_traits:
                tid = trait if isinstance(trait, str) else trait.get('id')
                if tid == 'parallel_processing':
                    ram_regen += 1
                    break

        # 버프/상태와 동기화: 오버클럭 버프가 있으면 플래그 강제 활성, 없으면 비활성
        if hasattr(character, "status_manager"):
            from src.combat.status_effects import StatusType
            has_buff = False
            try:
                has_buff = character.status_manager.has_status(StatusType.OVERCLOCK)
            except Exception:
                has_buff = False
            if has_buff and not getattr(character, "overclock_active", False):
                character.overclock_active = True
                logger.info(f"[오버클럭] {character.name} 오버클럭 모드 활성화!")
            if not has_buff and getattr(character, "overclock_active", False):
                character.overclock_active = False
                logger.info(f"[오버클럭] {character.name} 오버클럭 모드 비활성화!")

        # 오버클럭 모드: 고정 보너스 회복만 적용 (2배 회복 제거)
        if getattr(character, 'overclock_active', False):
            overclock_data = getattr(character, 'overclock_data', {})
            ram_regen += int(overclock_data.get('ram_regen_bonus', 1))
        
        old_ram = getattr(character, 'ram', 0)
        max_ram = getattr(character, 'max_ram', 8)
        character.ram = min(max_ram, old_ram + ram_regen)
        
        if character.ram > old_ram:
            logger.debug(f"[해커] {character.name} RAM +{character.ram - old_ram} (총: {character.ram}/{max_ram})")
        
        # 오버클럭 모드 페널티
        if getattr(character, 'overclock_active', False):
            overclock_data = getattr(character, 'overclock_data', {})
            
            # RAM 소모
            ram_cost = overclock_data.get('ram_cost_per_turn', 2)
            character.ram = max(0, character.ram - ram_cost)
            logger.debug(f"[오버클럭] {character.name} RAM -{ram_cost}")
            
            # HP 소모
            hp_cost_rate = overclock_data.get('hp_cost_per_turn', 0.03)
            # 가상화 특성: HP 페널티 50% 감소
            if hasattr(character, 'active_traits'):
                for trait in character.active_traits:
                    tid = trait if isinstance(trait, str) else trait.get('id')
                    if tid == 'virtualization':
                        hp_cost_rate *= 0.5
                        break
            
            hp_cost = int(character.max_hp * hp_cost_rate)
            character.current_hp = max(1, character.current_hp - hp_cost)
            logger.debug(f"[오버클럭] {character.name} HP -{hp_cost}")
            
            # RAM 부족 시 오버클럭 해제
            if character.ram <= 0:
                character.overclock_active = False
                logger.info(f"[오버클럭 해제] {character.name} RAM 부족으로 오버클럭 종료!")
    
    @staticmethod
    def add_intrusion(hacker, target, amount: int):
        """대상에게 침투 게이지 추가"""
        if not hasattr(target, 'intrusion_gauge'):
            target.intrusion_gauge = 0
        cap = GimmickUpdater._compute_intrusion_cap(hacker, target)
        target.intrusion_cap = cap
        
        # 침투 전문가 특성: +20%
        bonus = 1.0
        if hasattr(hacker, 'active_traits'):
            for trait in hacker.active_traits:
                tid = trait if isinstance(trait, str) else trait.get('id')
                if tid == 'intrusion_expert':
                    bonus += 0.2
                    break
        
        # 오버클럭 모드: +50%
        if getattr(hacker, 'overclock_active', False):
            overclock_data = getattr(hacker, 'overclock_data', {})
            bonus += overclock_data.get('intrusion_bonus', 0.5) - 1.0

        # 난이도 보정: 침투 최대치(50~300)에 따라 효율 스케일
        difficulty_ratio = 100 / cap  # cap이 높을수록 비율 ↓ → 더 많이 필요
        actual_gain = max(1, math.ceil(amount * bonus * difficulty_ratio)) if amount > 0 else 0
        old_intrusion = target.intrusion_gauge
        target.intrusion_gauge = min(100, target.intrusion_gauge + actual_gain)
        
        # 단계 진입 로그
        stages = getattr(hacker, 'intrusion_stages', {})
        for stage_id, stage_data in stages.items():
            threshold = stage_data.get('threshold', 0)
            if old_intrusion < threshold <= target.intrusion_gauge:
                stage_name = stage_data.get('name', stage_id)
                logger.info(f"[침투] {target.name}: {stage_name} 단계 진입! ({target.intrusion_gauge}%)")
                
                # 100% 도달 시 장악 가능 알림
                if threshold == 100:
                    logger.info(f"[완전 장악!] {target.name} 시스템 장악 가능!")
        
        if actual_gain > 0:
            logger.debug(f"[침투] {hacker.name} → {target.name}: +{actual_gain}% (총: {target.intrusion_gauge}%)")
        
        return actual_gain

    @staticmethod
    def _compute_intrusion_cap(hacker, target):
        """적 개체별 침투 최대치(50~300) 계산: HP↑ → 요구량↑, 해커 마공↑ → 요구량↓"""
        max_hp = getattr(target, "max_hp", 100)
        magic_power = getattr(hacker, "magic_attack", getattr(hacker, "magic", 0))
        base = 50 + (max_hp / 80.0) - (magic_power * 0.05)
        return int(max(50, min(300, base)))

    @staticmethod
    def get_intrusion_percent(hacker, target):
        """실제 침투%"""
        return getattr(target, "intrusion_gauge", 0)
    
    @staticmethod
    def get_intrusion_stage_effects(hacker, target) -> dict:
        """대상의 침투 단계에 따른 효과 반환"""
        intrusion = getattr(target, 'intrusion_gauge', 0)
        stages = getattr(hacker, 'intrusion_stages', {})
        
        effects = {}
        for stage_id, stage_data in stages.items():
            threshold = stage_data.get('threshold', 0)
            if intrusion >= threshold:
                stage_effects = stage_data.get('effects', {})
                effects.update(stage_effects)
        
        return effects
    
    @staticmethod
    def reset_intrusion(target):
        """대상의 침투 게이지 초기화"""
        if hasattr(target, 'intrusion_gauge'):
            old = target.intrusion_gauge
            target.intrusion_gauge = 0
            logger.info(f"[침투 초기화] {target.name}: {old}% → 0%")

    @staticmethod
    def _update_oath_system(character):
        """성기사: 서약 시스템 업데이트 (리메이크)"""
        # 서약별 능력치 보너스 적용
        GimmickUpdater._apply_oath_bonuses(character)

        # 자비 서약: 턴 종료 MP 회복
        current_oath = getattr(character, 'current_oath', None)
        if current_oath == 'mercy':
            oaths = getattr(character, 'oaths', {})
            mercy_data = oaths.get('mercy', {})
            bonus_effects = mercy_data.get('bonus_effects', {})
            mp_regen = bonus_effects.get('mp_regen_per_turn', 5)
            
            if hasattr(character, 'current_mp') and hasattr(character, 'max_mp'):
                old_mp = character.current_mp
                character.current_mp = min(character.max_mp, character.current_mp + mp_regen)
                actual_regen = character.current_mp - old_mp
                if actual_regen > 0:
                    logger.debug(f"[자비 서약] {character.name} MP +{actual_regen}")
        
        # 턴 종료 시 서약 준수 여부 초기화
        character.oath_kept = True
    
    @staticmethod
    def select_oath(character, oath_id: str):
        """서약 선택"""
        if not hasattr(character, 'gimmick_type') or character.gimmick_type != "oath_system":
            return False

        oaths = getattr(character, 'oaths', {})
        if oath_id not in oaths:
            logger.warning(f"[서약] 알 수 없는 서약: {oath_id}")
            return False

        old_oath = getattr(character, 'current_oath', None)
        # 서약 변경 시 신앙 절반으로 감소
        if old_oath and old_oath != oath_id and hasattr(character, "faith"):
            before = character.faith
            character.faith = int(character.faith * 0.5)
            logger.info(f"[서약 변경] {character.name}: 신앙 {before}->{character.faith} (기존: {old_oath})")

        character.current_oath = oath_id
        oath_name = oaths[oath_id].get('name', oath_id)
        logger.info(f"[서약 선택] {character.name}: {oath_name}")
        character.oath_kept = True
        # 선택 직후 보너스 적용
        GimmickUpdater._apply_oath_bonuses(character)
        
        return True
    
    @staticmethod
    def add_faith(character, amount: int, action_type: str = None):
        """신앙 게이지 추가"""
        if not hasattr(character, 'faith'):
            return 0
        
        current_oath = getattr(character, 'current_oath', None)
        oaths = getattr(character, 'oaths', {})
        
        # 서약에 맞는 행동인지 확인
        actual_gain = amount
        if current_oath and action_type:
            oath_data = oaths.get(current_oath, {})
            reward_action = oath_data.get('reward_action', '')
            reward_actions = oath_data.get('reward_actions', [])
            
            # 보상 행동 확인
            is_reward = (action_type == reward_action or action_type in reward_actions)
            
            if is_reward:
                # 치유의 빛 특성: 자비 서약 시 치유 신앙 +5
                if current_oath == 'mercy' and action_type == 'heal':
                    if hasattr(character, 'active_traits'):
                        for trait in character.active_traits:
                            tid = trait if isinstance(trait, str) else trait.get('id')
                            if tid == 'healing_light':
                                actual_gain += 5
                                break
        
        old_faith = character.faith
        max_faith = getattr(character, 'max_faith', 100)
        character.faith = min(max_faith, max(0, character.faith + actual_gain))
        
        if actual_gain > 0 and character.faith > old_faith:
            logger.info(f"[신앙] {character.name} +{character.faith - old_faith} (총: {character.faith}/{max_faith})")
        
        return actual_gain
    
    @staticmethod
    def check_oath_violation(character, action_type: str) -> bool:
        """서약 위반 확인"""
        current_oath = getattr(character, 'current_oath', None)
        if not current_oath:
            return False
        
        oaths = getattr(character, 'oaths', {})
        oath_data = oaths.get(current_oath, {})
        forbidden_action = oath_data.get('forbidden_action', '')
        
        # 금지 행동 체크
        is_violation = False
        if forbidden_action == 'attack' and action_type in ['attack', 'damage']:
            is_violation = True
        elif forbidden_action == 'buff_heal' and action_type in ['buff', 'heal']:
            is_violation = True
        
        if is_violation:
            GimmickUpdater._apply_oath_violation(character)
            return True
        
        return False
    
    @staticmethod
    def _apply_oath_violation(character):
        """서약 위반 페널티 적용"""
        current_oath = getattr(character, 'current_oath', None)
        oaths = getattr(character, 'oaths', {})
        oath_data = oaths.get(current_oath, {})
        penalty = oath_data.get('violation_penalty', {})
        
        # 정의의 분노 특성: 페널티 50% 감소
        penalty_mult = 1.0
        if hasattr(character, 'active_traits'):
            for trait in character.active_traits:
                tid = trait if isinstance(trait, str) else trait.get('id')
                if tid == 'righteous_fury':
                    penalty_mult = 0.5
                    break
        
        # 신앙 감소
        faith_loss = int(penalty.get('faith_loss', 20) * penalty_mult)
        character.faith = max(0, character.faith - faith_loss)
        
        character.oath_violation_count = getattr(character, 'oath_violation_count', 0) + 1
        character.oath_kept = False
        
        oath_name = oath_data.get('name', current_oath)
        logger.warning(f"[서약 위반!] {character.name}: {oath_name} - 신앙 -{faith_loss}")
        # 위반 시에도 보너스 재적용(감소된 신앙 상태 반영)
        GimmickUpdater._apply_oath_bonuses(character)

    @staticmethod
    def _apply_oath_bonuses(character):
        """서약에 따른 능력치 보너스 적용 (방어/마법방어 등)"""
        if not hasattr(character, "stat_manager"):
            return
        # 기존 보너스 제거
        character.stat_manager.remove_bonus(Stats.DEFENSE, "oath_bonus")
        character.stat_manager.remove_bonus(Stats.SPIRIT, "oath_bonus")
        character.stat_manager.remove_bonus(Stats.STRENGTH, "oath_bonus")

        current_oath = getattr(character, "current_oath", None)
        if not current_oath:
            return
        oaths = getattr(character, "oaths", {})
        oath_data = oaths.get(current_oath, {})
        bonus = oath_data.get("bonus_effects", {})

        # 방어/마법방어 배율 적용
        def_mult = bonus.get("defense_multiplier")
        mdef_mult = bonus.get("magic_defense_multiplier") or def_mult
        if def_mult and def_mult > 1.0:
            base_def = character.stat_manager.get_value(Stats.DEFENSE)
            character.stat_manager.add_bonus(Stats.DEFENSE, "oath_bonus", base_def * (def_mult - 1.0))
        if mdef_mult and mdef_mult > 1.0:
            base_mdef = character.stat_manager.get_value(Stats.SPIRIT)
            character.stat_manager.add_bonus(Stats.SPIRIT, "oath_bonus", base_mdef * (mdef_mult - 1.0))

        # 공격 배율 적용 (순결)
        atk_mult = bonus.get("attack_multiplier")
        if atk_mult and atk_mult > 1.0:
            base_atk = character.stat_manager.get_value(Stats.STRENGTH)
            character.stat_manager.add_bonus(Stats.STRENGTH, "oath_bonus", base_atk * (atk_mult - 1.0))

    @staticmethod
    def can_use_miracle(character, miracle_id: str) -> bool:
        """기적 스킬 사용 가능 여부 확인"""
        if not hasattr(character, 'faith'):
            return False
        
        thresholds = getattr(character, 'miracle_thresholds', {})
        required_faith = thresholds.get(miracle_id, 100)
        
        return character.faith >= required_faith
    
    @staticmethod
    def _update_oracle_system(character):
        """신관: 신탁 시스템 업데이트 (리메이크)"""
        # 턴 종료 시 현재 신탁 미충족 확인
        current_oracle = getattr(character, 'current_oracle', None)
        if current_oracle and not current_oracle.get('fulfilled', False):
            # 신탁 미충족 - 콤보 초기화
            character.oracle_combo = 0
            character.consecutive_oracle_fails = getattr(character, 'consecutive_oracle_fails', 0) + 1
            oracle_name = current_oracle.get('name', '신탁')
            logger.debug(f"[신탁 미충족] {character.name}: {oracle_name} (연속 실패: {character.consecutive_oracle_fails})")
    
    @staticmethod
    def generate_oracle(character):
        """라운드 시작 시 신탁 생성 (상황별 가중치 적용)"""
        import random

        if not hasattr(character, 'gimmick_type') or character.gimmick_type != "oracle_system":
            return None

        oracles = getattr(character, 'oracles', {})
        if not oracles:
            return None

        # 전투 상황 분석
        faith = getattr(character, 'faith', 0)
        consecutive_fails = getattr(character, 'consecutive_oracle_fails', 0)

        # 파티 상태 분석
        party_hp_avg = 100.0
        has_injured = False
        has_debuff = False
        has_dead = False
        is_boss = False

        if hasattr(character, '_combat_manager') and character._combat_manager:
            allies = character._combat_manager.allies
            if allies:
                total_hp_percent = sum((a.current_hp / a.max_hp * 100) for a in allies if a.max_hp > 0)
                party_hp_avg = total_hp_percent / len(allies)
                has_injured = any(a.current_hp < a.max_hp * 0.6 for a in allies)
                has_debuff = any(getattr(a, 'status_effects', []) for a in allies)
                has_dead = any(a.current_hp <= 0 for a in allies)

            is_boss = any(getattr(e, 'is_boss', False) for e in character._combat_manager.enemies)

        # 상황별 가중치 계산
        weighted_oracles = []
        for oracle_id, oracle_data in oracles.items():
            condition = oracle_data.get('condition', '')
            faith_reward = oracle_data.get('faith_reward', 20)

            # 기본 가중치 (신앙 보상이 높을수록 어려움)
            base_weight = 2.0
            if faith_reward >= 35:
                base_weight = 0.8  # 매우 어려움
            elif faith_reward >= 25:
                base_weight = 1.2  # 어려움
            elif faith_reward <= 15:
                base_weight = 3.0  # 쉬움

            # 상황별 가중치 배수
            context_multiplier = 1.0

            # 파티 HP 상태에 따른 가중치
            if has_injured or party_hp_avg < 60:
                # 부상자 있음: 치유 관련 신탁 선호
                if condition in ['heal_ally', 'party_buff_heal', 'protect_ally']:
                    context_multiplier *= 3.0
                elif condition in ['damage_evil', 'holy_damage']:
                    context_multiplier *= 0.5
            elif party_hp_avg > 80:
                # 전원 건강: 공격/버프 신탁 선호
                if condition in ['damage_evil', 'holy_damage', 'buff_ally']:
                    context_multiplier *= 1.8
                elif condition == 'heal_ally':
                    context_multiplier *= 0.6

            # 디버프 상태에 따른 가중치
            if has_debuff:
                if condition == 'cleanse_debuff':
                    context_multiplier *= 4.0  # 디버프 있으면 정화 신탁 매우 선호

            # 전투 불능자 있으면 부활 신탁 우선
            if has_dead:
                if condition == 'resurrect_ally':
                    context_multiplier *= 5.0
                # 부활이 필요한 상황에서는 다른 신탁 가중치 감소
                elif condition not in ['protect_ally', 'self_damage']:
                    context_multiplier *= 0.7

            # 신앙 수치에 따른 가중치
            if faith < 30:
                # 신앙 낮음: 쉬운 신탁 선호
                if faith_reward <= 20:
                    context_multiplier *= 2.0
                elif faith_reward >= 30:
                    context_multiplier *= 0.5
            elif faith >= 50:
                # 신앙 높음: 어려운 신탁도 가능
                if faith_reward >= 30:
                    context_multiplier *= 1.5
                # 신앙 유지 관련 신탁 우대
                if condition == 'maintain_faith_50':
                    context_multiplier *= 2.0

            # 보스전 가중치
            if is_boss:
                # 보스전에서는 중요한 신탁 우선
                if condition in ['resurrect_ally', 'protect_ally', 'party_buff_heal']:
                    context_multiplier *= 2.0
                elif condition in ['buff_ally', 'cleanse_debuff']:
                    context_multiplier *= 1.5

            # 연속 실패 시 쉬운 신탁 우대
            if consecutive_fails >= 2:
                if faith_reward <= 20:
                    context_multiplier *= 3.0
                elif faith_reward >= 30:
                    context_multiplier *= 0.3

            # 특수: 반격/응징 신탁은 기본적으로 가중치 낮음 (상황 특수)
            if condition in ['counter_success', 'self_damage']:
                context_multiplier *= 0.7

            # 최종 가중치 계산
            final_weight = max(0.1, base_weight * context_multiplier)

            # 가중치에 따라 리스트에 추가 (정수로 변환)
            count = max(1, int(final_weight * 10))
            weighted_oracles.extend([(oracle_id, oracle_data)] * count)

        if weighted_oracles:
            oracle_id, oracle_data = random.choice(weighted_oracles)

            character.current_oracle = {
                'id': oracle_id,
                'name': oracle_data.get('name', oracle_id),
                'condition': oracle_data.get('condition', ''),
                'faith_reward': oracle_data.get('faith_reward', 20),
                'bonus': oracle_data.get('bonus', None),
                'fulfilled': False
            }

            GimmickUpdater._push_ui_log(character, f'[신탁] {character.current_oracle["name"]}')
            return character.current_oracle

        return None
    
    @staticmethod
    def check_oracle_fulfillment(character, action_type: str, context: dict = None) -> bool:
        """신탁 충족 여부 체크"""
        if not hasattr(character, 'current_oracle') or not character.current_oracle:
            return False

        oracle = character.current_oracle
        if oracle.get('fulfilled'):
            return True

        condition = oracle.get('condition', '')
        fulfilled = False
        context = context or {}

        # 기본 조건들
        if condition == 'heal_ally' and action_type in ['heal', 'heal_ally']:
            fulfilled = True
        elif condition == 'buff_ally' and action_type in ['buff', 'buff_ally']:
            fulfilled = True
        elif condition == 'cleanse_debuff' and action_type in ['cleanse', 'purify']:
            fulfilled = True
        elif condition == 'damage_evil' and action_type in ['damage_undead', 'damage_demon', 'holy_damage', 'damage_evil']:
            fulfilled = True

        # 추가 조건들 (리메이크)
        elif condition == 'holy_damage' and action_type in ['holy_damage', 'damage_evil']:
            # 성속성 공격은 광휘의 신탁과 심판의 신탁 모두 충족
            fulfilled = True
        elif condition == 'resurrect_ally' and action_type == 'resurrect':
            fulfilled = True
        elif condition == 'self_damage' and action_type == 'self_damage':
            fulfilled = True
        elif condition == 'party_buff_heal' and action_type in ['party_buff_heal', 'mass_heal']:
            fulfilled = True
        elif condition == 'counter_success' and action_type == 'counter':
            fulfilled = True
        elif condition == 'protect_ally' and action_type == 'protect':
            fulfilled = True
        elif condition == 'buff_3_allies' and action_type == 'buff':
            # 3명 이상 버프 확인
            targets_buffed = context.get('targets_buffed', 0)
            if targets_buffed >= 3:
                fulfilled = True
        elif condition == 'maintain_faith_50':
            # 신앙 50 이상 유지
            faith = getattr(character, 'faith', 0)
            if faith >= 50:
                fulfilled = True

        if fulfilled:
            GimmickUpdater._fulfill_oracle(character)

        return fulfilled
    
    @staticmethod
    def _fulfill_oracle(character):
        """신탁 충족 처리"""
        oracle = character.current_oracle
        oracle['fulfilled'] = True
        
        # 연속 충족 콤보
        character.oracle_combo = getattr(character, 'oracle_combo', 0) + 1
        
        # 기본 신앙 보상
        reward = oracle.get('faith_reward', 20)
        
        # 신의 총애 특성: 신탁 충족 시 신앙 +5
        if hasattr(character, 'active_traits'):
            for trait in character.active_traits:
                tid = trait if isinstance(trait, str) else trait.get('id')
                if tid == 'divine_favor':
                    reward += 5
                    break
        
        # 연속 충족 보너스
        combo = character.oracle_combo
        combo_bonuses = getattr(character, 'combo_bonuses', {})
        
        # 신탁 숙련 특성: 임계값 -1
        combo_reduction = 0
        if hasattr(character, 'active_traits'):
            for trait in character.active_traits:
                tid = trait if isinstance(trait, str) else trait.get('id')
                if tid == 'oracle_mastery':
                    combo_reduction = 1
                    break
        
        for threshold_str, bonus_data in combo_bonuses.items():
            threshold = int(threshold_str) - combo_reduction
            if combo >= threshold:
                faith_bonus = bonus_data.get('faith_bonus', 0)
                reward += faith_bonus
                
                if bonus_data.get('trigger_grace'):
                    logger.info(f"[기적의 은총!] {character.name}: {combo}연속 충족 - 특별 보너스!")
        
        max_faith = getattr(character, 'max_faith', 100)
        character.faith = min(max_faith, character.faith + reward)
        character.consecutive_oracle_fails = 0  # 연속 실패 초기화

        GimmickUpdater._push_ui_log(character, f'[신탁 충족] {oracle["name"]} (신앙 +{reward}, {combo}연속)')

        # 신탁 충족 후 즉시 새로운 신탁 생성
        GimmickUpdater.generate_oracle(character)
        character.oracle_turn_count = 0  # 턴 카운터 초기화
    
    @staticmethod
    def add_priest_faith(character, amount: int, action_type: str = None):
        """신관 신앙 게이지 추가"""
        if not hasattr(character, 'faith'):
            return 0
        
        old_faith = character.faith
        max_faith = getattr(character, 'max_faith', 100)
        character.faith = min(max_faith, max(0, character.faith + amount))
        
        actual_gain = character.faith - old_faith
        if actual_gain > 0:
            logger.debug(f"[신앙] {character.name} +{actual_gain} (총: {character.faith}/{max_faith})")
        
        # 신탁 충족 체크
        if action_type:
            GimmickUpdater.check_oracle_fulfillment(character, action_type)
        
        return actual_gain
    
    @staticmethod
    def _update_mockery_system(character):
        """도적: 농락 시스템 업데이트 (리메이크)"""
        # 턴 종료 시 연속 회피 카운트 초기화 (행동 없이 턴 종료 시)
        # 은신 상태는 공격 시 해제됨
        pass
    
    @staticmethod
    def add_mockery(rogue, target, amount: int):
        """대상에게 농락 게이지 추가"""
        if not hasattr(target, 'mockery_gauge'):
            target.mockery_gauge = 0
        
        max_mockery = getattr(rogue, 'max_mockery', 10)
        
        # 농락의 달인 특성: +50%
        bonus = 1.0
        if hasattr(rogue, 'active_traits'):
            for trait in rogue.active_traits:
                tid = trait if isinstance(trait, str) else trait.get('id')
                if tid == 'master_mocker':
                    bonus = 1.5
                    break
        
        actual_gain = int(amount * bonus)
        old_mockery = target.mockery_gauge
        target.mockery_gauge = min(max_mockery, target.mockery_gauge + actual_gain)
        
        # 단계 진입 로그
        mockery_effects = getattr(rogue, 'mockery_effects', {})
        for threshold_str, effect_data in mockery_effects.items():
            threshold = int(threshold_str)
            if old_mockery < threshold <= target.mockery_gauge:
                effect_name = effect_data.get('name', f'농락 {threshold}')
                logger.info(f"[농락] {target.name}: {effect_name} 상태! ({target.mockery_gauge}/{max_mockery})")
                
                # 굴욕 전문가 특성: 농락 10 달성 시 HP 10% 순수 피해
                if threshold == 10:
                    if hasattr(rogue, 'active_traits'):
                        for trait in rogue.active_traits:
                            tid = trait if isinstance(trait, str) else trait.get('id')
                            if tid == 'humiliation':
                                damage = int(target.max_hp * 0.1)
                                target.current_hp = max(1, target.current_hp - damage)
                                logger.info(f"[굴욕 전문가] {target.name}에게 {damage} 순수 피해!")
                                break
        
        if actual_gain > 0:
            logger.debug(f"[농락] {rogue.name} → {target.name}: +{actual_gain} (총: {target.mockery_gauge})")
        
        return actual_gain
    
    @staticmethod
    def get_mockery_effects(rogue, target) -> dict:
        """대상의 농락 단계에 따른 효과 반환"""
        mockery = getattr(target, 'mockery_gauge', 0)
        mockery_effects = getattr(rogue, 'mockery_effects', {})
        
        effects = {}
        for threshold_str, effect_data in mockery_effects.items():
            threshold = int(threshold_str)
            if mockery >= threshold:
                effects.update(effect_data)
        
        return effects
    
    @staticmethod
    def reset_mockery(target):
        """대상의 농락 게이지 초기화"""
        if hasattr(target, 'mockery_gauge'):
            old = target.mockery_gauge
            target.mockery_gauge = 0
            logger.info(f"[농락 소모] {target.name}: {old} → 0")
    
    @staticmethod
    def on_evade_success(rogue, attacker):
        """회피 성공 시 처리"""
        if not hasattr(rogue, 'gimmick_type') or rogue.gimmick_type != "mockery_system":
            return
        
        evasion_chain = getattr(rogue, 'evasion_chain', {})
        per_evade = evasion_chain.get('per_evade', {})
        
        # 농락 +2
        mockery_gain = per_evade.get('mockery', 2)
        GimmickUpdater.add_mockery(rogue, attacker, mockery_gain)
        
        # 연속 회피 카운트
        rogue.consecutive_evades = getattr(rogue, 'consecutive_evades', 0) + 1
        
        # 그림자 춤꾼 특성: 회피 시 속도 +10%
        if hasattr(rogue, 'active_traits'):
            for trait in rogue.active_traits:
                tid = trait if isinstance(trait, str) else trait.get('id')
                if tid == 'shadow_dancer':
                    logger.debug(f"[그림자 춤꾼] {rogue.name} 속도 버프 적용")
                    break
        
        # 3연속 회피: 은신 돌입
        chain_3 = evasion_chain.get('chain_3', {})
        if rogue.consecutive_evades >= 3 and chain_3.get('stealth'):
            rogue.stealth_active = True
            bonus_mockery = chain_3.get('mockery', 5)
            GimmickUpdater.add_mockery(rogue, attacker, bonus_mockery)
            rogue.consecutive_evades = 0
            logger.info(f"[3연속 회피!] {rogue.name} 은신 돌입!")
        
        logger.debug(f"[회피 성공] {rogue.name} 연속 회피: {rogue.consecutive_evades}")
    
    @staticmethod
    def enter_stealth(rogue):
        """은신 돌입"""
        rogue.stealth_active = True
        logger.info(f"[은신] {rogue.name} 은신 상태 돌입!")
    
    @staticmethod
    def remove_stealth(rogue):
        """은신 해제"""
        rogue.stealth_active = False
        logger.info(f"[은신 해제] {rogue.name} 은신 상태 해제!")

    @staticmethod
    def _update_dilemma_choice(character):
        """철학자: 딜레마 선택 시스템 업데이트"""
        # 선택 값은 스킬로만 변경, 자동 업데이트 없음
        pass

    @staticmethod
    def _update_rune_resonance(character):
        """배틀메이지: 룬 공명 시스템 업데이트 - 게이지 100 도달 시 자동 룬 분배"""
        import random
        
        resonance_gauge = getattr(character, 'resonance_gauge', 0)
        max_gauge = getattr(character, 'max_resonance_gauge', 100)

        # 공명 게이지가 최대치에 도달하면 자동 룬 분배
        if resonance_gauge >= max_gauge:
            character.resonance_gauge = 0  # 게이지 0으로 초기화
            
            # 살아있는 적 목록 가져오기 (여러 방법 시도)
            enemies = []
            
            # 방법 1: character._combat_manager
            if hasattr(character, '_combat_manager') and character._combat_manager:
                cm = character._combat_manager
                if hasattr(cm, 'enemies'):
                    enemies = [e for e in cm.enemies if getattr(e, 'is_alive', True)]
            
            # 방법 2: 전역 get_combat_manager()
            if not enemies:
                try:
                    from src.combat.combat_manager import get_combat_manager
                    cm = get_combat_manager()
                    if cm and hasattr(cm, 'enemies'):
                        enemies = [e for e in cm.enemies if getattr(e, 'is_alive', True)]
                except Exception as e:
                    logger.warning(f"전역 combat_manager 접근 실패: {e}")
            
            if not enemies:
                # 적이 없으면 완전 공명 상태만 부여 (기존 호환성)
                character.perfect_resonance = True
                GimmickUpdater._push_ui_log(character, f"[완전 공명] 게이지 소모! 다음 룬 폭발 대폭 강화!")
                logger.info(f"{character.name} 완전 공명 상태 활성화 (적 없음, 게이지 {max_gauge} 소모)")
                return
            
            # 기본 룬 4개 + 특성 보너스
            base_runes = 4
            bonus_runes = 0
            
            # resonance_expert 특성 확인: 추가 룬 +2
            if GimmickUpdater._has_trait(character, "resonance_expert"):
                bonus_runes = 2
            
            total_runes = base_runes + bonus_runes
            rune_types = ["fire", "ice", "lightning", "earth", "arcane"]
            
            # 적 수에 따라 룬 분배 (균등 분배)
            runes_per_enemy = [0] * len(enemies)
            for i in range(total_runes):
                runes_per_enemy[i % len(enemies)] += 1
            
            # 실제 룬 각인
            for enemy, rune_count in zip(enemies, runes_per_enemy):
                for _ in range(rune_count):
                    rune_type = random.choice(rune_types)
                    GimmickUpdater._add_carved_rune(character, enemy, rune_type)
            
            # UI 로그
            distribution_msg = f"적 {len(enemies)}명에게 룬 {total_runes}개 분배"
            GimmickUpdater._push_ui_log(character, f"[공명 폭발] 게이지 100! {distribution_msg}!")
            logger.info(f"{character.name} 공명 폭발: {distribution_msg} (게이지 0으로 초기화)")

    @staticmethod
    def _update_dimension_refraction(character):
        """차원술사: 차원 굴절 시스템 업데이트 - 매 행동마다 굴절량 감소 및 피해"""
        try:
            refraction = getattr(character, 'refraction_stacks', 0)
            print(f"[DEBUG][굴절업데이트] {character.name} 굴절량={refraction}")

            if refraction <= 0:
                print(f"[DEBUG][굴절업데이트] 굴절량 0 이하, 스킵")
                return

            # 매 행동마다: 현재 굴절량의 10% 소멸 + 고정 피해
            decay_rate = 0.10

            # 차원 안정화 특성: 감소율 완화 10% -> 5%
            # active_traits와 selected_traits 모두 확인 (트레이닝 모드 호환)
            active_traits = list(getattr(character, 'active_traits', []) or [])
            selected_traits = list(getattr(character, 'selected_traits', []) or [])
            all_traits = active_traits + selected_traits
            print(f"[DEBUG][굴절업데이트] active_traits={active_traits}, selected_traits={selected_traits}")
            
            for t in all_traits:
                trait_id = t if isinstance(t, str) else t.get('id') if isinstance(t, dict) else None
                if trait_id == 'dimensional_stabilization':
                    decay_rate = 0.05
                    print(f"[DEBUG][굴절업데이트] 차원 안정화 특성 적용, decay_rate=5%")
                    break

            # 이중 차원 특성: 굴절 피해 +75%
            decay_damage_mult = 1.0
            for t in all_traits:
                trait_id = t if isinstance(t, str) else t.get('id') if isinstance(t, dict) else None
                if trait_id == 'double_refraction':
                    decay_damage_mult = 1.75
                    print(f"[DEBUG][굴절업데이트] 이중 차원 특성 적용, 피해 배율=175%")
                    break

            decay_amount = int(refraction * decay_rate)
            # 최소 1의 감소는 있도록 함 (스택이 있으면)
            if refraction > 0 and decay_amount < 1:
                decay_amount = 1
            
            print(f"[DEBUG][굴절업데이트] 감소량={decay_amount}, 감소율={int(decay_rate*100)}%")
                 
            fixed_damage = max(1, int(decay_amount * decay_damage_mult))
            print(f"[DEBUG][굴절업데이트] 고정피해={fixed_damage}")

            # 굴절 보호막(Refraction Shield)이 있으면 자해 피해만 방지 (굴절 감소는 진행)
            skip_damage = False
            if hasattr(character, 'status_manager') and character.status_manager:
                try:
                    # status_effects에서 이름으로 검색
                    refraction_shield = None
                    for effect in getattr(character.status_manager, 'status_effects', []):
                        if getattr(effect, 'name', '') == "Refraction Shield":
                            refraction_shield = effect
                            break
                    
                    if refraction_shield:
                        shield_hp = getattr(refraction_shield, 'metadata', {}).get('shield_hp', 0)
                        print(f"[DEBUG][굴절업데이트] Refraction Shield 발견, shield_hp={shield_hp}")
                        if shield_hp > 0:
                            skip_damage = True
                            print(f"[DEBUG][굴절업데이트] 보호막으로 피해 {fixed_damage} 방지됨")
                except Exception as e:
                    print(f"[DEBUG][굴절업데이트] 보호막 체크 중 오류: {e}")

            # 고정 피해 적용 (보호막이 없을 때만)
            actual_damage = 0
            if not skip_damage:
                print(f"[DEBUG][굴절업데이트] 피해 적용 시도...")
                character._processing_refraction_decay = True
                try:
                    if hasattr(character, 'take_fixed_damage'):
                        actual_damage = character.take_fixed_damage(fixed_damage)
                    else:
                        actual_damage = min(fixed_damage, getattr(character, 'current_hp', 0))
                        character.current_hp = max(1, character.current_hp - fixed_damage)
                    print(f"[DEBUG][굴절업데이트] 피해 적용 완료: {actual_damage}")
                except Exception as e:
                    print(f"[DEBUG][굴절업데이트] 피해 적용 중 오류: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    character._processing_refraction_decay = False
            else:
                print(f"[DEBUG][굴절업데이트] 피해 스킵됨 (보호막)")

            # 굴절량 감소는 항상 적용!
            old_refraction = character.refraction_stacks
            character.refraction_stacks = max(0, refraction - decay_amount)
            print(f"[DEBUG][굴절업데이트] 굴절량 변화: {old_refraction} → {character.refraction_stacks}")

            # 로그
            if actual_damage > 0 or decay_amount > 0:
                logger.info(
                    f"[차원 굴절] {character.name} 유지비: HP -{actual_damage}, 굴절량 -{decay_amount} "
                    f"(굴절량 {refraction} → {character.refraction_stacks}, 감소율 {int(decay_rate*100)}%)"
                )
        except Exception as e:
            print(f"[DEBUG][굴절업데이트] 전체 오류: {e}")
            import traceback
            traceback.print_exc()

    @staticmethod
    def check_choice_mastery(character, choice_type: str) -> bool:
        """
        딜레마틱: 선택 숙련도 확인

        Args:
            character: 캐릭터 (철학자)
            choice_type: 선택 타입 (power, wisdom, sacrifice, survival, truth, lie, order, chaos)

        Returns:
            해당 선택이 숙련(5회 이상)되었는지 여부
        """
        if character.gimmick_type != "dilemma_choice":
            return False

        choice_attr = f"choice_{choice_type}"
        choice_count = getattr(character, choice_attr, 0)
        accumulation_threshold = getattr(character, 'accumulation_threshold', 5)

        return choice_count >= accumulation_threshold

    # ============================================================
    # 암흑기사 - 충전 시스템
    # ============================================================

    @staticmethod
    def _update_charge_system_turn_start(character):
        """충전 시스템 턴 시작 업데이트"""
        # 충전량 50% 이상일 때 BRV 회복 (특성: overflowing_darkness)
        charge_gauge = getattr(character, 'charge_gauge', 0)

        if charge_gauge >= 50:
            # BRV 회복 (최대 BRV의 10%)
            if hasattr(character, 'max_brv') and hasattr(character, 'current_brv'):
                brv_restore = int(character.max_brv * 0.1)
                character.current_brv = min(character.max_brv, character.current_brv + brv_restore)
                logger.debug(f"{character.name} 충전 {charge_gauge}% - BRV +{brv_restore} (턴 시작)")

    @staticmethod
    def _update_charge_system_turn_end(character):
        """충전 시스템 턴 종료 업데이트"""
        # 자연 충전 감소 (선택적, 현재는 없음)
        # 필요 시 구현
        pass

    @staticmethod
    def on_charge_gained(character, amount: int, reason: str = ""):
        """충전 획득 처리"""
        if not hasattr(character, 'charge_gauge'):
            character.charge_gauge = 0

        # charge_acceleration 특성 확인: 모든 충전 획득량 배율 적용
        from src.character.trait_effects import get_trait_effect_manager, TraitEffectType
        trait_manager = get_trait_effect_manager()
        
        # charge_gain은 표준 스탯이 아니므로 직접 특성 효과 확인
        charge_multiplier = 1.0
        if hasattr(character, 'active_traits'):
            for trait_data in character.active_traits:
                trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                if trait_id == 'charge_acceleration':
                    effects = trait_manager.get_trait_effects(trait_id)
                    for effect in effects:
                        if effect.effect_type == TraitEffectType.STAT_MULTIPLIER and effect.target_stat == "charge_gain":
                            # 조건 확인
                            if not effect.condition or trait_manager._check_condition(character, effect.condition):
                                charge_multiplier = effect.value
                                logger.debug(f"[충전 가속] {character.name} 충전 획득량 배율: x{charge_multiplier}")
                                break
        
        if charge_multiplier > 1.0:
            amount = int(amount * charge_multiplier)
            logger.debug(f"[충전 가속] {character.name} 충전 획득량 {charge_multiplier}배 적용 → {amount}")

        max_charge = getattr(character, 'max_charge', 100)
        old_charge = character.charge_gauge
        character.charge_gauge = min(max_charge, character.charge_gauge + amount)

        actual_gain = character.charge_gauge - old_charge
        if actual_gain > 0:
            logger.info(f"{character.name} 충전 +{actual_gain} ({reason}) - 총: {character.charge_gauge}%")

    @staticmethod
    def on_take_damage_charge(character, damage: int):
        """피격 시 충전 획득 (방어 태세 배율 적용)"""
        if getattr(character, 'gimmick_type', None) != "charge_system":
            return

        # 기본 충전 획득 (YAML의 take_damage_gain)
        base_gain = getattr(character, 'take_damage_gain', 10)

        # 방어 태세 버프가 있는지 확인 (메타데이터에서)
        multiplier = 1.0
        if hasattr(character, 'active_buffs'):
            for buff in character.active_buffs:
                if hasattr(buff, 'metadata') and buff.metadata.get('on_hit_charge_multiplier'):
                    multiplier = buff.metadata['on_hit_charge_multiplier']
                    break

        charge_gain = int(base_gain * multiplier)
        GimmickUpdater.on_charge_gained(character, charge_gain, f"피격 ({damage} 데미지)")

    @staticmethod
    def on_kill_charge(character):
        """적 처치 시 충전 획득"""
        if getattr(character, 'gimmick_type', None) != "charge_system":
            return

        kill_gain = getattr(character, 'kill_gain', 20)
        GimmickUpdater.on_charge_gained(character, kill_gain, "적 처치")

    # ============================================================
    # 마술사: 트릭 덱 시스템
    # ============================================================

    @staticmethod
    def _update_trick_deck(character):
        """마술사: 트릭 덱 시스템 턴 종료 업데이트"""
        hand = getattr(character, 'card_hand', [])
        
        if hand:
            from src.character.skills.job_skills.magician_skills import check_poker_combination
            combo_type, combo_cards, score = check_poker_combination(hand)
            
            if combo_type:
                combo_names = {
                    "pair": "원페어", "two_pair": "투페어", "triple": "트리플",
                    "straight": "스트레이트", "flush": "플러시", "full_house": "풀하우스",
                    "four_of_kind": "포카드", "straight_flush": "스트레이트 플러시",
                    "royal_straight_flush": "로얄 스트레이트 플러시"
                }
                logger.debug(f"{character.name} 현재 조합: {combo_names.get(combo_type, combo_type)}")
        
        # 선제공격 효과 처리 (A카드) - 턴 종료 시 ATB를 최대치로 설정
        if getattr(character, '_first_strike_pending', False):
            # ATB 게이지를 최대치로 설정 (다음 턴에 바로 행동)
            if hasattr(character, 'atb_gauge') and hasattr(character.atb_gauge, 'current'):
                character.atb_gauge.current = 1000
            elif hasattr(character, 'atb_gauge'):
                character.atb_gauge = 1000
            
            # 플래그 및 카드 효과 제거
            character._first_strike_pending = False
            if hasattr(character, 'card_effects'):
                character.card_effects.pop('first_strike', None)
            
            logger.info(f"[마술사] {character.name} 선제공격 발동! 즉시 다음 턴!")

    @staticmethod
    def _update_trick_deck_turn_start(character):
        """마술사: 트릭 덱 시스템 턴 시작 업데이트"""
        if not hasattr(character, 'card_deck') or character.card_deck is None:
            GimmickUpdater.initialize_trick_deck(character)
        
        hand = getattr(character, 'card_hand', [])
        deck_count = len(getattr(character, 'card_deck', []))
        
        if hand:
            from src.character.skills.job_skills.magician_skills import get_hand_display
            logger.info(f"{character.name} {get_hand_display(character)} (덱: {deck_count}장)")
        else:
            logger.debug(f"{character.name} 손패 없음 (덱: {deck_count}장)")

    @staticmethod
    def initialize_trick_deck(character):
        """마술사 트릭 덱 초기화"""
        try:
            from src.character.skills.job_skills.magician_skills import create_deck, shuffle_deck
            character.card_deck = shuffle_deck(create_deck())
            character.card_hand = []
            character.card_discard = []
            character.max_hand_size = 8
            logger.info(f"{character.name} 트릭 덱 초기화 완료 (54장)")
        except Exception as e:
            logger.error(f"{character.name} 트릭 덱 초기화 실패: {e}")
            character.card_deck = []
            character.card_hand = []
            character.card_discard = []
            character.max_hand_size = 8

    @staticmethod
    def get_trick_deck_hand_size(character) -> int:
        """마술사 손패 크기 반환"""
        if getattr(character, 'gimmick_type', None) == "trick_deck":
            return len(getattr(character, 'card_hand', []))
        return 0

    @staticmethod
    def get_trick_deck_combination(character):
        """마술사 현재 손패 조합 반환"""
        if getattr(character, 'gimmick_type', None) != "trick_deck":
            return None, [], 0
        
        hand = getattr(character, 'card_hand', [])
        if not hand:
            return None, [], 0
        
        from src.character.skills.job_skills.magician_skills import check_poker_combination
        return check_poker_combination(hand)

    @staticmethod
    def has_poker_combination(character, required_combo: str) -> bool:
        """마술사가 특정 포커 조합을 가지고 있는지 확인"""
        combo_type, _, _ = GimmickUpdater.get_trick_deck_combination(character)
        
        if combo_type is None:
            return False
        
        combo_hierarchy = {
            "royal_straight_flush": 9, "straight_flush": 8, "four_of_kind": 7,
            "full_house": 6, "flush": 5, "straight": 4, "triple": 3,
            "two_pair": 2, "pair": 1
        }
        
        current_rank = combo_hierarchy.get(combo_type, 0)
        required_rank = combo_hierarchy.get(required_combo, 0)
        return current_rank >= required_rank
    
    # ============================================================
    # 마술사 카드 효과 적용
    # ============================================================
    
    @staticmethod
    def _apply_card_rank_effect(character, rank_effect, card):
        """마술사 카드 숫자 효과 적용"""
        effect_type = rank_effect.get("effect", "")
        effect_name = rank_effect.get("name", "")
        
        logger.info(f"[마술사] {effect_name} 효과 발동! ({rank_effect.get('desc', '')})")
        
        if not hasattr(character, 'active_buffs'):
            character.active_buffs = {}
        if not hasattr(character, 'card_effects'):
            character.card_effects = {}
        
        if effect_type == "first_strike":
            character.card_effects["first_strike"] = True
        elif effect_type == "double_edge":
            character.card_effects["double_edge"] = {"damage_mult": 2.0, "self_damage": 0.25}
        elif effect_type == "triple_hit":
            character.card_effects["triple_hit"] = {"hits": 3, "damage_mult": 0.4}
        elif effect_type == "stability":
            character.active_buffs["accuracy_up"] = {"value": 1.0, "duration": 1}
        elif effect_type == "change":
            character.card_effects["reverse_buff"] = True
        elif effect_type == "curse":
            character.card_effects["curse_target"] = {"duration": 3}
        elif effect_type == "lucky_seven":
            character.active_buffs["critical_up"] = {"value": 1.0, "duration": 1}
            character.card_effects["lucky_drop"] = 0.5
        elif effect_type == "infinity":
            character.card_effects["free_cast"] = True
        elif effect_type == "max_power":
            character.card_effects["skill_power_up"] = 0.5
        elif effect_type == "completion":
            from src.character.skills.job_skills.magician_skills import draw_cards
            max_hand = getattr(character, 'max_hand_size', 7)
            current_hand = len(getattr(character, 'card_hand', []))
            if current_hand < max_hand:
                draw_cards(character, max_hand - current_hand)
        elif effect_type == "knight":
            # J: 아군 1명 보호 (1회 피해 대신 받음) - 버프로 설정
            character.card_effects["protect_ally"] = True
            character.active_buffs["protect_target"] = {"value": 1, "duration": 1}
            logger.info(f"[마술사] {character.name}이(가) 아군 보호 태세!")
        elif effect_type == "queen":
            # Q: 아군 전체 HP 15% 회복 - 즉시 적용
            try:
                from src.combat.combat_manager import get_combat_manager
                cm = get_combat_manager()
                if cm and cm.party:
                    heal_percent = 0.15
                    for ally in cm.party.characters:
                        if hasattr(ally, 'is_alive') and ally.is_alive:
                            heal_amount = int(ally.max_hp * heal_percent)
                            ally.hp = min(ally.hp + heal_amount, ally.max_hp)
                            logger.info(f"[마술사] 퀸 효과: {ally.name} HP +{heal_amount} 회복!")
            except Exception as e:
                logger.warning(f"[마술사] 퀸 효과 적용 실패: {e}")
            character.card_effects["party_heal"] = 0.15
        elif effect_type == "king":
            # K: 적 전체 1턴 행동불가 - 즉시 적용
            try:
                from src.combat.combat_manager import get_combat_manager
                cm = get_combat_manager()
                if cm and cm.enemies:
                    for enemy in cm.enemies:
                        if hasattr(enemy, 'is_alive') and enemy.is_alive:
                            # 스턴 상태 적용
                            if hasattr(enemy, 'status_manager'):
                                from src.character.status_effect import StatusEffectType
                                enemy.status_manager.add_effect(StatusEffectType.STUN, duration=1)
                                logger.info(f"[마술사] 킹 효과: {enemy.name}에게 스턴 1턴!")
                            elif hasattr(enemy, 'active_debuffs'):
                                if not enemy.active_debuffs:
                                    enemy.active_debuffs = {}
                                enemy.active_debuffs["stun"] = {"duration": 1}
                                logger.info(f"[마술사] 킹 효과: {enemy.name}에게 스턴 1턴!")
            except Exception as e:
                logger.warning(f"[마술사] 킹 효과 적용 실패: {e}")
            character.card_effects["mass_stun"] = {"duration": 1}
    
    @staticmethod
    def _apply_card_suit_effect(character, suit_effect, card, context=None):
        """마술사 카드 무늬 효과 적용"""
        effect_type = suit_effect.get("effect", "")
        effect_name = suit_effect.get("name", "")
        
        logger.info(f"[마술사] {effect_name} 효과 발동! ({suit_effect.get('desc', '')})")
        
        if not hasattr(character, 'card_effects'):
            character.card_effects = {}
        
        if effect_type == "pierce":
            character.card_effects["armor_pierce"] = 0.3
        elif effect_type == "lifesteal":
            character.card_effects["lifesteal"] = 0.3
        elif effect_type == "wealth":
            character.card_effects["bonus_rewards"] = 0.3
        elif effect_type == "toxic":
            # ♣: 적에게 독 3턴 적용 - 즉시 적용
            character.card_effects["poison_attack"] = {"duration": 3, "damage_percent": 0.05}
            try:
                # context에서 적 목록 가져오기
                all_enemies = []
                if context and 'all_enemies' in context:
                    all_enemies = context['all_enemies']
                else:
                    # fallback: combat_manager에서 가져오기
                    from src.combat.combat_manager import get_combat_manager
                    cm = get_combat_manager()
                    if cm and cm.enemies:
                        all_enemies = cm.enemies
                
                # 현재 타겟이 있으면 타겟에게, 없으면 랜덤 적에게 적용
                target = getattr(character, '_current_target', None)
                if not target and all_enemies:
                    alive_enemies = [e for e in all_enemies if getattr(e, 'is_alive', True)]
                    if alive_enemies:
                        import random
                        target = random.choice(alive_enemies)
                
                if target:
                    if hasattr(target, 'status_manager'):
                        from src.combat.status_effects import StatusType, StatusEffect
                        poison_effect = StatusEffect(
                            status_type=StatusType.POISON,
                            name="독",
                            duration=3,
                            intensity=0.5  # 매턴 최대HP 5% 피해 (base 10% × 0.5)
                        )
                        target.status_manager.add_status(poison_effect, allow_refresh=True)
                        logger.info(f"[마술사] 클로버 효과: {target.name}에게 독 3턴!")
            except Exception as e:
                logger.warning(f"[마술사] 클로버 효과 적용 실패: {e}")
    
    # ============================================================
    # 바드 작곡 패턴 효과 적용
    # ============================================================
    
    @staticmethod
    def _apply_bard_compose_effect(character, skill, context=None):
        """바드 작곡 스킬 패턴 효과 적용"""
        if not hasattr(character, 'music_notes') or not character.music_notes:
            logger.info(f"{character.name} 악보가 비어있어 기본 효과만 적용됩니다.")
            return
        
        notes = ''.join(character.music_notes)
        pattern_effects = skill.metadata.get("pattern_effects", {})
        
        matched_pattern = None
        matched_effect = None
        
        for pattern, effect in pattern_effects.items():
            if pattern in notes or (len(notes) >= 3 and notes[-3:] == pattern):
                matched_pattern = pattern
                matched_effect = effect
                break
        
        if not hasattr(character, 'active_buffs'):
            character.active_buffs = {}
        
        if matched_effect:
            effect_type = matched_effect.get("type", "")
            value = matched_effect.get("value", 0)
            duration = matched_effect.get("duration", 3)
            
            logger.info(f"[바드] {matched_pattern} 패턴 완성! {effect_type} 효과 발동!")
            
            # 아군 목록 가져오기
            allies = []
            if context and 'all_allies' in context:
                allies = [a for a in context['all_allies'] if getattr(a, 'is_alive', True)]
            else:
                allies = [character]  # fallback
            
            if effect_type == "attack_surge":
                # 파티 전체 공격력 버프
                for ally in allies:
                    if not hasattr(ally, 'active_buffs'):
                        ally.active_buffs = {}
                    ally.active_buffs["attack_up"] = {"value": value, "duration": duration}
                logger.info(f"  -> 아군 전체 공격력 +{int(value*100)}% ({duration}턴)")
            elif effect_type == "attack_magic_surge":
                # 파티 전체 공격력 + 마법력 버프
                for ally in allies:
                    if not hasattr(ally, 'active_buffs'):
                        ally.active_buffs = {}
                    ally.active_buffs["attack_up"] = {"value": value, "duration": duration}
                    ally.active_buffs["magic_up"] = {"value": value, "duration": duration}
                logger.info(f"  -> 아군 전체 공격력/마법력 +{int(value*100)}% ({duration}턴)")
            elif effect_type == "buff_extend":
                # 파티 전체 버프 지속시간 연장
                for ally in allies:
                    if hasattr(ally, 'active_buffs'):
                        for buff_name, buff_data in ally.active_buffs.items():
                            if isinstance(buff_data, dict) and "duration" in buff_data:
                                buff_data["duration"] += int(value)
                logger.info(f"  -> 아군 전체 버프 지속시간 +{int(value)}턴")
            elif effect_type == "mass_heal":
                # 파티 전체 힐
                healed_count = 0
                for ally in allies:
                    if hasattr(ally, 'current_hp') and hasattr(ally, 'max_hp'):
                        heal_amount = int(ally.max_hp * value)
                        ally.current_hp = min(ally.max_hp, ally.current_hp + heal_amount)
                        logger.info(f"  -> {ally.name} HP {heal_amount} 회복!")
                        healed_count += 1
                if healed_count == 0:
                    heal_amount = int(character.max_hp * value)
                    character.current_hp = min(character.max_hp, character.current_hp + heal_amount)
                    logger.info(f"  -> HP {heal_amount} 회복!")
            elif effect_type == "all_stat_up":
                # 파티 전체 공/방/마공/마방/속 버프
                for ally in allies:
                    if not hasattr(ally, 'active_buffs'):
                        ally.active_buffs = {}
                    ally.active_buffs["attack_up"] = {"value": value, "duration": duration}
                    ally.active_buffs["defense_up"] = {"value": value, "duration": duration}
                    ally.active_buffs["magic_up"] = {"value": value, "duration": duration}
                    ally.active_buffs["spirit_up"] = {"value": value, "duration": duration}
                    ally.active_buffs["speed_up"] = {"value": value, "duration": duration}
                logger.info(f"  -> 아군 전체 공/방/마공/마방/속 +{int(value*100)}% ({duration}턴)")
            elif effect_type == "all_stat_down":
                # 적 전체 공/방/마공/마방/속 디버프
                all_enemies = []
                if context and 'all_enemies' in context:
                    all_enemies = [e for e in context['all_enemies'] if getattr(e, 'is_alive', True)]
                for enemy in all_enemies:
                    if not hasattr(enemy, 'active_buffs'):
                        enemy.active_buffs = {}
                    enemy.active_buffs["attack_down"] = {"value": value, "duration": duration}
                    enemy.active_buffs["defense_down"] = {"value": value, "duration": duration}
                    enemy.active_buffs["magic_down"] = {"value": value, "duration": duration}
                    enemy.active_buffs["spirit_down"] = {"value": value, "duration": duration}
                    enemy.active_buffs["speed_down"] = {"value": value, "duration": duration}
                logger.info(f"  -> 적 전체 공/방/마공/마방/속 -{int(value*100)}% ({duration}턴)")
            elif effect_type == "magic_heal":
                # 바드 마법력 기반 파티 전체 회복
                magic_stat = getattr(character, 'magic', getattr(character, 'magic_attack', 100))
                heal_multiplier = matched_effect.get("multiplier", 1.35)
                heal_amount = int(magic_stat * heal_multiplier)
                for ally in allies:
                    if hasattr(ally, 'current_hp') and hasattr(ally, 'max_hp'):
                        actual_heal = min(ally.max_hp - ally.current_hp, heal_amount)
                        ally.current_hp = min(ally.max_hp, ally.current_hp + heal_amount)
                        logger.info(f"  -> {ally.name} HP {actual_heal} 회복!")
                logger.info(f"  -> 마법력 {magic_stat} × {heal_multiplier} = {heal_amount} 회복")
            elif effect_type == "triple_strike":
                # 적 전체 3연타 BRV+HP 공격
                all_enemies = []
                if context and 'all_enemies' in context:
                    all_enemies = [e for e in context['all_enemies'] if getattr(e, 'is_alive', True)]
                
                brv_mult = matched_effect.get("brv_multiplier", 1.2)
                hp_mult = matched_effect.get("hp_multiplier", 1.0)
                magic_stat = getattr(character, 'magic', getattr(character, 'magic_attack', 100))
                
                for enemy in all_enemies:
                    total_damage = 0
                    # 3연타 BRV 공격
                    for i in range(3):
                        brv_damage = int(magic_stat * brv_mult * 0.8)
                        if hasattr(enemy, 'current_brv'):
                            enemy.current_brv = max(0, enemy.current_brv - brv_damage)
                        total_damage += brv_damage
                    # HP 공격 마무리
                    hp_damage = int(magic_stat * hp_mult)
                    if hasattr(enemy, 'current_hp'):
                        enemy.current_hp = max(0, enemy.current_hp - hp_damage)
                    total_damage += hp_damage
                    logger.info(f"  -> {enemy.name}에게 3연타 BRV + HP 공격! (총 {total_damage} 피해)")
                    
                    # 사망 체크
                    if hasattr(enemy, 'current_hp') and enemy.current_hp <= 0:
                        enemy.is_alive = False
            elif effect_type == "enemy_debuff":
                # 적 전체 디버프 (context에서 적 목록 가져오기)
                all_enemies = []
                if context and 'all_enemies' in context:
                    all_enemies = [e for e in context['all_enemies'] if getattr(e, 'is_alive', True)]
                for enemy in all_enemies:
                    if not hasattr(enemy, 'active_buffs'):
                        enemy.active_buffs = {}
                    enemy.active_buffs["attack_down"] = {"value": value, "duration": duration}
                    enemy.active_buffs["defense_down"] = {"value": value, "duration": duration}
                logger.info(f"  -> 적 전체 공/방 -{int(value*100)}% ({duration}턴)")
            
            if skill.metadata.get("consume_notes"):
                if len(character.music_notes) >= 3:
                    character.music_notes = character.music_notes[:-3]
                else:
                    character.music_notes = []
                logger.info(f"  -> 악보 갱신: {''.join(character.music_notes) if character.music_notes else '(비어있음)'}")
        else:
            # 패턴 미완성: 음표 개수에 비례한 공/마 버프 (아군 전체)
            note_count = len(character.music_notes)
            bonus = 0.1 * note_count  # 음표당 10%
            
            # 아군 전체에 버프 적용
            allies = []
            if context and 'all_allies' in context:
                allies = [a for a in context['all_allies'] if getattr(a, 'is_alive', True)]
            else:
                allies = [character]  # fallback
            
            for ally in allies:
                if not hasattr(ally, 'active_buffs'):
                    ally.active_buffs = {}
                ally.active_buffs["attack_up"] = {"value": bonus, "duration": 2}
                ally.active_buffs["magic_up"] = {"value": bonus, "duration": 2}
            
            logger.info(f"[바드] 패턴 미완성. 음표 {note_count}개 -> 아군 전체 공/마 +{int(bonus*100)}% (2턴)")
            
            # 패턴 미완성 시에도 음표 소모
            if skill.metadata.get("consume_notes"):
                if len(character.music_notes) >= 3:
                    character.music_notes = character.music_notes[:-3]
                else:
                    character.music_notes = []
                logger.info(f"  -> 악보 갱신: {''.join(character.music_notes) if character.music_notes else '(비어있음)'}")

    # === 시간술사: 가능성 슬롯 시스템 ===

    @staticmethod
    def _update_possibility_slots(character):
        """시간술사: 가능성 슬롯 시스템 턴 종료 시 업데이트"""
        GimmickUpdater._apply_parallel_resonance(character)

    @staticmethod
    def _update_possibility_slots_turn_start(character, context=None):
        """시간술사: 가능성 슬롯 시스템 턴 시작 시 업데이트"""
        if not hasattr(character, '_battle_started'):
            character._battle_started = True
            if hasattr(character, 'active_traits'):
                for trait_data in character.active_traits:
                    trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                    if trait_id == "infinite_branches":
                        import random
                        possible_skills = ['time_mage_time_bolt', 'time_mage_time_shock', 'time_mage_haste', 'time_mage_slow', 'time_mage_rewind']
                        random_skill = random.choice(possible_skills)
                        GimmickUpdater._add_possibility(character, random_skill)
                        logger.info(f"[무한 분기] {character.name} 전투 시작 시 '{random_skill}' 가능성 자동 생성!")
                        break
        GimmickUpdater._apply_parallel_resonance(character)

    @staticmethod
    def _process_possibility_generation(character, skill, context=None):
        """시간술사: 스킬 사용 시 가능성 생성 처리"""
        import random
        skill_id = getattr(skill, 'id', None) or skill.metadata.get('id', '')
        excluded_skills = ['summon_possibility', 'time_crossing', 'time_storm', 
                          'fate_copy', 'overwrite_fate', 'infinite_convergence', 'teamwork']
        if skill_id in excluded_skills:
            return
        possibility_pairs = getattr(character, 'possibility_pairs', {})
        alternative_skill = possibility_pairs.get(skill_id)
        if not alternative_skill:
            alternative_skill = skill.metadata.get('possibility_pair')
        if not alternative_skill:
            return
        slots = getattr(character, 'possibility_slots', [])
        max_slots = getattr(character, 'max_possibility_slots', 4)
        if len(slots) >= max_slots:
            return
        base_chance = getattr(character, 'base_generation_chance', 0.70)
        generation_bonus = 0
        luck_bonus = 0
        max_chance = 1.0
        if hasattr(character, 'active_traits'):
            for trait_data in character.active_traits:
                trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                if trait_id == "branch_creator":
                    generation_bonus = 0.15
                    luck = getattr(character, 'luck', 0)
                    if hasattr(character, 'stat_manager'):
                        from src.character.stats import Stats
                        luck = character.stat_manager.get_value(Stats.LUCK)
                    luck_bonus = luck * 0.0025
                    max_chance = 0.95
                    break
        if hasattr(character, 'active_traits'):
            for trait_data in character.active_traits:
                trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                if trait_id == "infinite_branches":
                    current_hp = getattr(character, 'current_hp', 0)
                    max_hp = getattr(character, 'max_hp', 1)
                    if current_hp / max_hp <= 0.30:
                        base_chance = 1.0
                        generation_bonus = 0
                        luck_bonus = 0
                        max_chance = 1.0
                        logger.info(f"[무한 분기] {character.name} HP 30% 이하! 가능성 생성 확률 100%")
                    break
        final_chance = min(max_chance, base_chance + generation_bonus + luck_bonus)
        if random.random() < final_chance:
            GimmickUpdater._add_possibility(character, alternative_skill)
            logger.info(f"[가능성 생성] {character.name}: '{skill_id}' 사용 → '{alternative_skill}' 저장됨 (확률: {final_chance*100:.0f}%)")

    @staticmethod
    def _add_possibility(character, skill_id: str, reuse_count: int = 0, original_character=None):
        """가능성 슬롯에 스킬 추가

        Args:
            character: 시간술사 캐릭터
            skill_id: 저장할 스킬 ID
            reuse_count: 재사용 카운트
            original_character: 원본 캐릭터 (운명 복제 시 사용)
        """
        if not hasattr(character, 'possibility_slots'):
            character.possibility_slots = []
        max_slots = getattr(character, 'max_possibility_slots', 4)
        if len(character.possibility_slots) >= max_slots:
            return False
        character.possibility_slots.append({
            'skill_id': skill_id,
            'power_ratio': getattr(character, 'possibility_power_ratio', 0.85),
            'reuse_count': reuse_count,
            'original_character': original_character  # 원본 캐릭터 정보 저장
        })
        return True

    @staticmethod
    def _apply_parallel_resonance(character):
        """평행 공명 효과 적용"""
        if not hasattr(character, 'stat_manager'):
            return
        from src.character.stats import Stats
        try:
            character.stat_manager.remove_bonus(Stats.MAGIC, "parallel_resonance")
        except:
            pass
        slots = getattr(character, 'possibility_slots', [])
        slot_count = len(slots)
        if slot_count == 0:
            character._parallel_resonance_damage_reduction = 0
            character._parallel_resonance_atb_bonus = 0
            return
        per_slot_magic_bonus = 0.08
        per_slot_damage_reduction = 0.05
        full_slot_atb_bonus = 0.15
        base_magic = character.stat_manager.get_value(Stats.MAGIC, use_total=False)
        magic_bonus = base_magic * (per_slot_magic_bonus * slot_count)
        character.stat_manager.add_bonus(Stats.MAGIC, "parallel_resonance", magic_bonus)
        character._parallel_resonance_damage_reduction = per_slot_damage_reduction * slot_count
        max_slots = getattr(character, 'max_possibility_slots', 4)
        character._parallel_resonance_atb_bonus = full_slot_atb_bonus if slot_count >= max_slots else 0

    @staticmethod
    def summon_possibility(character, slot_index: int, context=None) -> dict:
        """가능성 소환 - 저장된 스킬 발동

        Args:
            character: 시간술사 캐릭터
            slot_index: 소환할 슬롯 인덱스
            context: 전투 컨텍스트

        Returns:
            스킬 ID, 위력 배율, 원본 캐릭터 정보
        """
        import random
        slots = getattr(character, 'possibility_slots', [])
        if not slots or slot_index >= len(slots):
            return {'success': False, 'error': '슬롯이 비어있거나 잘못된 인덱스'}
        possibility = slots[slot_index]
        skill_id = possibility['skill_id']
        power_ratio = possibility['power_ratio']
        reuse_count = possibility.get('reuse_count', 0)
        original_character = possibility.get('original_character', None)  # 원본 캐릭터 정보
        preserve = False
        if hasattr(character, 'active_traits'):
            for trait_data in character.active_traits:
                trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                if trait_id == "timeline_interference":
                    effects = trait_data.get('effects', {}) if isinstance(trait_data, dict) else {}
                    if reuse_count < effects.get('max_reuse', 2) and random.random() < effects.get('preserve_chance', 0.30):
                        preserve = True
                        possibility['reuse_count'] = reuse_count + 1
                    break
        consumed = not preserve
        if consumed:
            slots.pop(slot_index)
            character.possibility_slots = slots
        return {
            'success': True,
            'skill_id': skill_id,
            'power_ratio': power_ratio,
            'consumed': consumed,
            'original_character': original_character  # 원본 캐릭터 반환
        }

    @staticmethod
    def time_crossing(character, slot_indices: list, context=None) -> list:
        """시간선 교차: 2개 가능성 동시 발동"""
        results = []
        slots = getattr(character, 'possibility_slots', [])
        if len(slot_indices) != 2 or len(slots) < 2:
            return [{'success': False, 'error': '슬롯 2개 필요'}]
        for idx in sorted(slot_indices, reverse=True):
            if idx < len(slots):
                results.append({
                    'success': True,
                    'skill_id': slots[idx]['skill_id'],
                    'power_ratio': 0.75,
                    'consumed': True,
                    'original_character': slots[idx].get('original_character', None)
                })
                slots.pop(idx)
        character.possibility_slots = slots
        return results

    @staticmethod
    def time_storm(character, context=None) -> dict:
        """시간 폭풍: 모든 가능성 해방"""
        slots = getattr(character, 'possibility_slots', [])
        if not slots:
            return {'success': False, 'error': '가능성 없음'}
        released = [
            {
                'skill_id': p['skill_id'],
                'power_ratio': 1.0,
                'original_character': p.get('original_character', None)
            }
            for p in slots
        ]
        slot_count = len(slots)
        convergence_bonus = False
        total_damage_bonus = 0
        if hasattr(character, 'active_traits'):
            for trait_data in character.active_traits:
                trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                if trait_id == "converging_fates":
                    effects = trait_data.get('effects', {}) if isinstance(trait_data, dict) else {}
                    if slot_count >= effects.get('min_possibilities', 3):
                        convergence_bonus = True
                        total_damage_bonus = effects.get('damage_bonus', 0.40)
                    break
        character.possibility_slots = []
        return {'success': True, 'released': released, 'convergence_bonus': convergence_bonus, 'total_damage_bonus': total_damage_bonus}

    @staticmethod
    def fate_copy(character, ally, context=None) -> dict:
        """운명 복제 - 아군의 스킬을 복제하여 저장

        Args:
            character: 시간술사 캐릭터
            ally: 복제 대상 아군
            context: 전투 컨텍스트

        Returns:
            성공 여부와 복제된 스킬 정보
        """
        last_skill = getattr(ally, '_last_used_skill', None)
        if not last_skill:
            return {'success': False, 'error': '복제할 스킬 없음'}

        # 스킬 ID 추출
        skill_id = getattr(last_skill, 'id', None) or getattr(last_skill, 'skill_id', None)
        if not skill_id:
            return {'success': False, 'error': '스킬 ID 없음'}

        # 제외 스킬 확인
        excluded = ['teamwork', 'infinite_convergence']
        if skill_id in excluded:
            return {'success': False, 'error': '팀워크 스킬은 복제 불가'}

        # 궁극기 확인
        is_ultimate = getattr(last_skill, 'is_ultimate', False)
        if is_ultimate:
            return {'success': False, 'error': '궁극기는 복제 불가'}

        # 원본 캐릭터 정보를 함께 저장
        if GimmickUpdater._add_possibility(character, skill_id, original_character=ally):
            return {'success': True, 'copied_skill': skill_id, 'original_character': ally.name}
        return {'success': False, 'error': '슬롯 가득 참'}

    @staticmethod
    def overwrite_fate(character, slot_index: int, new_skill_id: str) -> dict:
        """운명 덮어쓰기"""
        slots = getattr(character, 'possibility_slots', [])
        if not slots or slot_index >= len(slots):
            return {'success': False, 'error': '슬롯이 비어있거나 잘못된 인덱스'}
        excluded = ['teamwork', 'infinite_convergence']
        if new_skill_id in excluded:
            return {'success': False, 'error': '궁극기/팀워크는 선택 불가'}
        old_skill = slots[slot_index]['skill_id']
        slots[slot_index] = {'skill_id': new_skill_id, 'power_ratio': 0.85, 'reuse_count': 0}
        return {'success': True, 'old_skill': old_skill, 'new_skill': new_skill_id}

    @staticmethod
    def get_possibility_slots(character) -> list:
        """가능성 슬롯 목록 반환"""
        return getattr(character, 'possibility_slots', [])

    @staticmethod
    def get_possibility_slot_count(character) -> int:
        """가능성 슬롯 개수 반환"""
        return len(getattr(character, 'possibility_slots', []))

    # === 환술사: 환영 군단 시스템 ===
    
    @staticmethod
    def _update_phantom_legion(character):
        """환술사: 환영 군단 시스템 턴 종료 업데이트"""
        # 확정 회피 쿨다운 감소
        mirror_shift_cooldown = getattr(character, 'mirror_shift_cooldown', 0)
        if mirror_shift_cooldown > 0:
            character.mirror_shift_cooldown = mirror_shift_cooldown - 1
            if character.mirror_shift_cooldown == 0:
                logger.info(f"[환술사] {character.name} 확정 회피(Mirror Shift) 준비 완료!")
        
        # 환영 재생성 체크 (무한 거울 특성)
        GimmickUpdater._check_phantom_regeneration(character)
    
    @staticmethod
    def _update_phantom_legion_turn_start(character, context=None):
        """환술사: 환영 군단 시스템 턴 시작 업데이트"""
        # phantom_hits와 phantom_count 동기화 (0이하 히트 포인트 제거)
        phantom_hits = getattr(character, 'phantom_hits', [])
        if phantom_hits:
            # 0이하 히트 포인트 가진 환영들 제거
            original_count = len(phantom_hits)
            phantom_hits[:] = [hit for hit in phantom_hits if hit > 0]
            removed_count = original_count - len(phantom_hits)

            if removed_count > 0:
                character.phantom_count = max(0, getattr(character, 'phantom_count', 0) - removed_count)
                logger.info(f"[환술사] {character.name} 사망한 환영 정리: {removed_count}개 제거, 남은 phantom_count={character.phantom_count}")

        phantom_count = getattr(character, 'phantom_count', 0)

        # 환영 보너스 적용
        if phantom_count > 0:
            evasion_bonus = phantom_count * 0.12  # 환영당 12% 회피
            character._phantom_evasion_bonus = evasion_bonus
            logger.debug(f"[환술사] {character.name} 환영 보너스: 회피 +{evasion_bonus*100:.0f}%")
        
        # 환영 4개 보유 시 환영 군주 특성 효과
        if phantom_count >= 4:
            has_phantom_lord = GimmickUpdater._has_trait(character, 'phantom_lord')
            if has_phantom_lord and context:
                enemies = context.get('enemies', [])
                for enemy in enemies:
                    if hasattr(enemy, 'is_alive') and enemy.is_alive:
                        # 적 명중률 -15% 디버프
                        if not hasattr(enemy, '_phantom_lord_debuff'):
                            enemy._phantom_lord_debuff = True
                            logger.info(f"[환영 군주] {enemy.name} 명중률 -15%")
        
        # 확정 회피 준비 상태 체크
        min_phantoms = 2
        if phantom_count >= min_phantoms:
            mirror_shift_cooldown = getattr(character, 'mirror_shift_cooldown', 0)
            if mirror_shift_cooldown == 0:
                character.mirror_shift_ready = True
            else:
                character.mirror_shift_ready = False
    
    @staticmethod
    def _check_phantom_regeneration(character):
        """환영 재생성 체크"""
        import random
        
        pending_regen = getattr(character, '_phantom_pending_regen', 0)
        if pending_regen > 0:
            max_phantoms = getattr(character, 'max_phantoms', 4)
            current = getattr(character, 'phantom_count', 0)
            
            for _ in range(pending_regen):
                if current >= max_phantoms:
                    break
                    
                # 기본 재생성 확률 20%
                regen_chance = 0.20
                
                # 무한 거울 특성 체크
                if GimmickUpdater._has_trait(character, 'infinite_mirrors'):
                    # HP 30% 이하 시 50%로 증가
                    hp_ratio = getattr(character, 'current_hp', 1) / max(1, getattr(character, 'max_hp', 1))
                    if hp_ratio <= 0.30:
                        regen_chance = 0.50
                
                # 그림자 잠식 특성 30% 추가 재생성
                if GimmickUpdater._has_trait(character, 'shadow_feast'):
                    regen_chance = max(regen_chance, 0.30)
                
                if random.random() < regen_chance:
                    current += 1
                    character.phantom_count = current
                    logger.info(f"[환술사] {character.name} 환영 재생성! (현재: {current}/{max_phantoms})")
            
            character._phantom_pending_regen = 0
    
    @staticmethod
    def summon_phantom(character, count: int = 1, fill_to_max: bool = False) -> dict:
        """환영 소환"""
        import random
        
        max_phantoms = getattr(character, 'max_phantoms', 4)
        current = getattr(character, 'phantom_count', 0)
        
        if fill_to_max:
            added = max_phantoms - current
            character.phantom_count = max_phantoms
        else:
            # 거울 분신술 특성: 25% 확률로 추가 생성
            bonus = 0
            if GimmickUpdater._has_trait(character, 'mirror_image'):
                if random.random() < 0.25:
                    bonus = 1
                    logger.info(f"[거울 분신술] 추가 환영 생성!")
            
            total_add = min(count + bonus, max_phantoms - current)
            added = total_add
            character.phantom_count = current + total_add
        
        # 환영 히트 포인트 초기화
        hit_absorb = getattr(character, 'phantom_hit_absorb', 2)
        if GimmickUpdater._has_trait(character, 'infinite_mirrors'):
            hit_absorb += 1  # 무한 거울: 히트 흡수 +1
        
        if not hasattr(character, 'phantom_hits'):
            character.phantom_hits = []
        
        for _ in range(added):
            if len(character.phantom_hits) < max_phantoms:
                character.phantom_hits.append(hit_absorb)
        
        new_count = getattr(character, 'phantom_count', 0)
        logger.info(f"[환술사] {character.name} 환영 소환! (+{added}, 현재: {new_count}/{max_phantoms})")
        
        return {'success': True, 'added': added, 'current': new_count, 'max': max_phantoms}
    
    @staticmethod
    def consume_phantom(character, count: int = 1) -> dict:
        """환영 소모"""
        current = getattr(character, 'phantom_count', 0)
        
        if current < count:
            return {'success': False, 'error': '환영이 부족합니다', 'current': current}
        
        consumed = min(count, current)
        character.phantom_count = current - consumed
        
        # 환영 히트 배열에서도 제거
        phantom_hits = getattr(character, 'phantom_hits', [])
        for _ in range(consumed):
            if phantom_hits:
                phantom_hits.pop()
        
        # 잔상 게이지 충전
        afterimage_per_destroy = getattr(character, 'afterimage_per_destroy', 25)
        afterimage = getattr(character, 'afterimage_gauge', 0)
        max_afterimage = getattr(character, 'afterimage_max', 100)
        character.afterimage_gauge = min(max_afterimage, afterimage + (afterimage_per_destroy * consumed))
        
        logger.info(f"[환술사] {character.name} 환영 소모: {consumed}개, 잔상 +{afterimage_per_destroy * consumed}")
        
        return {'success': True, 'consumed': consumed, 'current': character.phantom_count}
    
    @staticmethod
    def phantom_take_damage(character, damage: int) -> dict:
        """환영이 피해를 대신 받음 (30% 확률 중첩)"""
        import random
        
        phantom_count = getattr(character, 'phantom_count', 0)
        if phantom_count <= 0:
            return {'absorbed': False, 'damage': damage}
        
        # 환영당 30% 확률로 대신 맞음 (중첩 계산)
        # 1개: 30%, 2개: 51%, 3개: 66%, 4개: 76%
        redirect_chance = 1 - (0.70 ** phantom_count)
        
        if random.random() < redirect_chance:
            # 환영이 대신 맞음
            phantom_hits = getattr(character, 'phantom_hits', [])
            if phantom_hits:
                logger.info(f"[환술사] 환영 피해 대신 받음 전: phantom_count={phantom_count}, phantom_hits={phantom_hits}")
                phantom_hits[-1] -= 1  # 가장 마지막 환영의 히트 감소

                absorbed_by_phantom = True
                phantom_destroyed = False

                if phantom_hits[-1] <= 0:
                    phantom_hits.pop()
                    character.phantom_count = phantom_count - 1
                    phantom_destroyed = True

                    # 잔상 게이지 충전
                    afterimage_per_destroy = getattr(character, 'afterimage_per_destroy', 25)
                    afterimage = getattr(character, 'afterimage_gauge', 0)
                    max_afterimage = getattr(character, 'afterimage_max', 100)
                    character.afterimage_gauge = min(max_afterimage, afterimage + afterimage_per_destroy)

                    # 그림자 잠식 특성 효과
                    if GimmickUpdater._has_trait(character, 'shadow_feast'):
                        # HP 5% 회복
                        max_hp = getattr(character, 'max_hp', 100)
                        heal_amount = int(max_hp * 0.05)
                        if hasattr(character, 'heal'):
                            actual_heal = character.heal(heal_amount)
                        else:
                            current_hp = getattr(character, 'current_hp', 0)
                            actual_heal = min(heal_amount, max_hp - current_hp)
                            character.current_hp = min(max_hp, current_hp + actual_heal)

                        # 다음 공격 피해 +15%
                        character._shadow_feast_bonus = 0.15

                        logger.info(f"[그림자 잠식] {character.name} HP +{actual_heal}, 다음 공격 +15%")

                    # 재생성 대기 등록
                    character._phantom_pending_regen = getattr(character, '_phantom_pending_regen', 0) + 1

                    logger.info(f"[환술사] {character.name} 환영 소멸! (피해 흡수, 잔상 +{afterimage_per_destroy})")
                    logger.info(f"[환술사] 환영 소멸 후: phantom_count={character.phantom_count}, phantom_hits={phantom_hits}")
                else:
                    logger.info(f"[환술사] {character.name} 환영이 피해를 대신 받음! (환영 HP: {phantom_hits[-1]})")
                    logger.info(f"[환술사] 피해 대신 후: phantom_count={character.phantom_count}, phantom_hits={phantom_hits}")

                return {
                    'absorbed': True,
                    'damage': 0,
                    'phantom_destroyed': phantom_destroyed,
                    'remaining_phantoms': character.phantom_count
                }
        
        return {'absorbed': False, 'damage': damage}
    
    @staticmethod
    def use_mirror_shift(character) -> dict:
        """확정 회피 (Mirror Shift) 사용"""
        phantom_count = getattr(character, 'phantom_count', 0)
        min_phantoms = 2
        
        if phantom_count < min_phantoms:
            return {'success': False, 'error': f'환영이 {min_phantoms}개 이상 필요합니다'}
        
        if not getattr(character, 'mirror_shift_ready', False):
            cooldown = getattr(character, 'mirror_shift_cooldown', 0)
            return {'success': False, 'error': f'확정 회피 쿨다운 중 ({cooldown}턴)'}
        
        # 확정 회피 사용
        character.mirror_shift_ready = False
        
        # 쿨다운 설정 (환영 4개면 4턴, 그 외 5턴)
        if phantom_count >= 4:
            character.mirror_shift_cooldown = 4
        else:
            character.mirror_shift_cooldown = 5
        
        # 아지랑이 걸음 특성: 확정 회피 시 ATB +25%, 다음 공격 +20%
        if GimmickUpdater._has_trait(character, 'mirage_step'):
            character._perfect_evasion_atb_bonus = 0.25
            character._perfect_evasion_damage_bonus = 0.20
            logger.info(f"[아지랑이 걸음] {character.name} ATB +25%, 다음 공격 +20%")
        
        logger.info(f"[환술사] {character.name} 확정 회피 발동! (쿨다운: {character.mirror_shift_cooldown}턴)")
        
        return {'success': True, 'cooldown': character.mirror_shift_cooldown}
    
    @staticmethod
    def charge_afterimage(character, amount: int) -> dict:
        """잔상 게이지 충전"""
        afterimage = getattr(character, 'afterimage_gauge', 0)
        max_afterimage = getattr(character, 'afterimage_max', 100)
        
        added = min(amount, max_afterimage - afterimage)
        character.afterimage_gauge = afterimage + added
        
        logger.debug(f"[환술사] {character.name} 잔상 게이지 +{added} (현재: {character.afterimage_gauge}/{max_afterimage})")
        
        return {'success': True, 'added': added, 'current': character.afterimage_gauge}
    
    @staticmethod
    def consume_afterimage(character, amount: int = None) -> dict:
        """잔상 게이지 소모"""
        afterimage = getattr(character, 'afterimage_gauge', 0)
        
        if amount is None:
            # 전부 소모
            consumed = afterimage
            character.afterimage_gauge = 0
        else:
            consumed = min(amount, afterimage)
            character.afterimage_gauge = afterimage - consumed
        
        return {'success': True, 'consumed': consumed, 'remaining': character.afterimage_gauge}
    
    @staticmethod
    def get_phantom_count(character) -> int:
        """환영 개수 반환"""
        return getattr(character, 'phantom_count', 0)
    
    @staticmethod
    def get_afterimage_gauge(character) -> int:
        """잔상 게이지 반환"""
        return getattr(character, 'afterimage_gauge', 0)
    
    @staticmethod
    def calculate_phantom_echo_damage(character, base_damage: int) -> list:
        """환영 에코 피해 계산 (다단히트)"""
        phantom_count = getattr(character, 'phantom_count', 0)
        echo_ratio = 0.35  # 환영당 본체의 35%
        
        hits = []
        hits.append({'damage': base_damage, 'source': 'main', 'delay': 0})
        
        for i in range(phantom_count):
            echo_damage = int(base_damage * echo_ratio)
            hits.append({
                'damage': echo_damage, 
                'source': f'phantom_{i+1}', 
                'delay': 0.2 * (i + 1)  # 0.2초 간격
            })
        
        return hits

    # ============================================================
    # 블레이드 서킷 / 룬 공명 필드 특수 처리
    # ============================================================

    @staticmethod
    def _pre_blade_circuit_skill(user, skill, target, context):
        """블레이드 서킷: 스킬 사용 전 회로 상태 업데이트"""
        meta = getattr(skill, "metadata", {}) or {}
        hook = {"messages": [], "power_multiplier": 1.0}
        channel = meta.get("circuit_channel")

        # Flux Step: 다음 스킬 채널 자동 전환
        if getattr(user, "circuit_flux_ready", 0) and channel in ("steel", "mana"):
            channel = "mana" if channel == "steel" else "steel"
            user.circuit_flux_ready = max(0, getattr(user, "circuit_flux_ready", 0) - 1)
        elif getattr(user, "circuit_flux_ready", 0) and channel == "hybrid":
            user.circuit_flux_ready = 0

        hook["channel"] = channel
        lock_turns = meta.get("lock_turns", getattr(user, "default_lock_turns", 1))
        arc_bonus = meta.get("arc_spark_bonus", 0.5)

        # 봉인 채널을 사용했을 때 Arc Spark 준비
        if channel == "steel" and getattr(user, "steel_lock", 0) > 0:
            hook["arc_spark"] = {"bonus": arc_bonus, "channel": "steel"}
            user.steel_lock = 0
        elif channel == "mana" and getattr(user, "mana_lock", 0) > 0:
            hook["arc_spark"] = {"bonus": arc_bonus, "channel": "mana"}
            user.mana_lock = 0

        # 게이지 충전
        charge = meta.get("circuit_charge", 10)
        gain_bonus = int(charge * 0.2) if GimmickUpdater._has_trait(user, "circuit_overdrive") else 0
        if channel in ("steel", "mana"):
            field = f"{channel}_line"
            max_field = f"max_{field}"
            max_val = getattr(user, max_field, 100)
            setattr(user, field, min(max_val, getattr(user, field, 0) + charge + gain_bonus))
        elif channel == "hybrid":
            # 하이브리드 스킬은 두 채널을 모두 살짝 충전
            half = max(4, int((charge + gain_bonus) / 2))
            for ch in ("steel", "mana"):
                field = f"{ch}_line"
                max_field = f"max_{field}"
                max_val = getattr(user, max_field, 100)
                setattr(user, field, min(max_val, getattr(user, field, 0) + half))

        # 봉인 적용 (반대 채널 봉인)
        if channel == "steel":
            user.mana_lock = max(getattr(user, "mana_lock", 0), lock_turns)
        elif channel == "mana":
            user.steel_lock = max(getattr(user, "steel_lock", 0), lock_turns)
        elif channel == "hybrid":
            user.steel_lock = max(getattr(user, "steel_lock", 0), lock_turns)
            user.mana_lock = max(getattr(user, "mana_lock", 0), lock_turns)

        # 공명 패턴 체크 (물리→마법→물리 또는 역순)
        if meta.get("resonance_step") and channel in ("steel", "mana"):
            history = list(getattr(user, "circuit_history", []))
            history.append(channel)
            if len(history) > 3:
                history = history[-3:]
            user.circuit_history = history
            if len(history) == 3 and history[0] == history[2] and history[0] != history[1]:
                sigil_gain = 1
                if GimmickUpdater._has_trait(user, "resonance_loop"):
                    sigil_gain += 1
                max_sig = getattr(user, "max_resonance_sigil", 3)
                before = getattr(user, "resonance_sigil", 0)
                user.resonance_sigil = min(max_sig, before + sigil_gain)
                hook["messages"].append(f"[공명 패턴] 시그넷 +{user.resonance_sigil - before}")

        # Mirror Edge 시그넷 소비 처리
        if meta.get("consumes_sigils"):
            available = getattr(user, "resonance_sigil", 0)
            use_max = meta.get("max_sigils", available)
            used = min(available, use_max)
            if used > 0:
                user.resonance_sigil = max(0, available - used)
                bonus = 1.0 + meta.get("sigil_damage_bonus", 0.3) * used
                hook["power_multiplier"] = hook.get("power_multiplier", 1.0) * bonus
                hook["sigils_used"] = used
                def_per = meta.get("def_shred_per_sigil", 0)
                if GimmickUpdater._has_trait(user, "mirror_specialist"):
                    def_per += 0.05
                hook["def_shred"] = def_per * used

        # 브랜드 적 정보 저장
        target_list = target if isinstance(target, list) else [target]
        hook["target_branded"] = any(getattr(t, "circuit_brand", 0) for t in target_list if t)

        # 균형 상태 보너스
        if GimmickUpdater._has_trait(user, "balanced_blade"):
            if getattr(user, "steel_line", 0) >= 50 and getattr(user, "mana_line", 0) >= 50:
                hook["power_multiplier"] = hook.get("power_multiplier", 1.0) * 1.15

        return hook

    @staticmethod
    def _post_blade_circuit_skill(user, skill, target, context, hook, total_damage):
        """블레이드 서킷: 스킬 사용 후 처리 (Arc Spark, 시그넷, 추가 방깎 등)"""
        from src.character.skills.effects.damage_effect import DamageEffect, DamageType
        from src.character.skills.effects.buff_effect import BuffEffect, BuffType

        result = {"extra_damage": 0, "extra_heal": 0, "messages": []}
        meta = getattr(skill, "metadata", {}) or {}

        # 시그넷 소비 보너스 배율 적용
        if hook.get("power_multiplier", 1.0) > 1.0:
            context["power_multiplier"] = context.get("power_multiplier", 1.0) * hook["power_multiplier"]

        # Arc Spark 추가타
        arc = hook.get("arc_spark")
        target_list = target if isinstance(target, list) else [target]
        if arc and target_list:
            for t in target_list:
                if not t or not getattr(t, "is_alive", True):
                    continue
                try:
                    base_mult = 0.8 + ((getattr(user, "steel_line", 0) + getattr(user, "mana_line", 0)) / 200.0) * 0.25
                    spark_mult = base_mult * arc.get("bonus", 1.0)
                    if GimmickUpdater._has_trait(user, "circuit_overdrive"):
                        spark_mult *= 1.2
                    if GimmickUpdater._has_trait(user, "feedback_spark"):
                        spark_mult *= 1.1
                    spark = DamageEffect(DamageType.BRV_HP, spark_mult, stat_type="physical")
                    spark_result = spark.execute(user, t, context)
                    if hasattr(spark_result, "damage_dealt"):
                        result["extra_damage"] += spark_result.damage_dealt
                    result["messages"].append("Arc Spark 발동")
                    if GimmickUpdater._has_trait(user, "feedback_spark") and hasattr(user, "restore_mp"):
                        restored = user.restore_mp(8)
                        if restored:
                            result["messages"].append(f"MP +{restored}")
                except Exception:
                    logger.debug("Arc Spark 적용 실패", exc_info=True)

        # 브랜드 타격 보너스: 시그넷 추가
        if hook.get("target_branded") and meta.get("circuit_channel"):
            max_sig = getattr(user, "max_resonance_sigil", 3)
            before = getattr(user, "resonance_sigil", 0)
            if before < max_sig:
                user.resonance_sigil = min(max_sig, before + 1)
                result["messages"].append("브랜드 타격: 시그넷 +1")

        # Mirror Edge 추가 방깎/파티 버프
        if hook.get("def_shred"):
            for t in target_list:
                if not t or not getattr(t, "is_alive", True):
                    continue
                try:
                    BuffEffect(BuffType.DEFENSE_DOWN, hook["def_shred"], duration=3).execute(user, t, context)
                    BuffEffect(BuffType.MAGIC_DEFENSE_DOWN, hook["def_shred"], duration=3).execute(user, t, context)
                except Exception:
                    logger.debug("추가 방깎 적용 실패", exc_info=True)

        if hook.get("sigils_used") and meta.get("grant_party_buff"):
            buff_val = meta.get("grant_party_buff", 0.05) * hook.get("sigils_used", 1)
            allies = context.get("all_allies", [])
            for ally in allies:
                if not getattr(ally, "is_alive", True):
                    continue
                BuffEffect(BuffType.ATTACK_UP, buff_val, duration=2).execute(user, ally, context)
                BuffEffect(BuffType.MAGIC_UP, buff_val, duration=2).execute(user, ally, context)

        # 궁극기/팀워크 추가 시그넷 지급
        if meta.get("grant_sigils"):
            max_sig = getattr(user, "max_resonance_sigil", 3)
            before = getattr(user, "resonance_sigil", 0)
            user.resonance_sigil = min(max_sig, before + meta.get("grant_sigils", 0))

        # 서킷 리셋 처리
        if meta.get("reset_circuit"):
            user.steel_line = 0
            user.mana_line = 0
            user.steel_lock = 0
            user.mana_lock = 0
            user.circuit_history = []

        return result

    @staticmethod
    def _add_carved_rune(user, target, rune_type: str, max_slots: int = None) -> bool:
        """대상에게 룬을 새기고 사용자 보유 룬 카운터 업데이트"""
        import random

        if not target or not getattr(target, "is_alive", True):
            logger.info(f"[룬 각인 실패] 대상 없거나 사망")
            return False
        if not rune_type:
            rune_type = random.choice(["fire", "ice", "lightning", "earth", "arcane"])

        if not hasattr(target, "carved_runes") or not isinstance(target.carved_runes, dict):
            target.carved_runes = {}

        slot_cap = max_slots if max_slots is not None else getattr(user, "max_rune_slots_per_target", 4)
        if GimmickUpdater._has_trait(user, "rune_archivist"):
            slot_cap += 1

        # 전체 룬 보유 상한
        total_owned = sum(getattr(user, f"rune_{rt}", 0) for rt in ["fire", "ice", "lightning", "earth", "arcane"])
        max_total = getattr(user, "max_runes_total", 99)
        if GimmickUpdater._has_trait(user, "rune_archivist"):
            max_total += 2
        if total_owned >= max_total:
            logger.info(f"[룬 각인 실패] 전체 룬 상한 ({total_owned}/{max_total})")
            return False

        current_total = sum(target.carved_runes.values())
        if current_total >= slot_cap:
            logger.info(f"[룬 각인 실패] 대상 슬롯 상한 ({current_total}/{slot_cap})")
            return False

        # 타입별 최대치 적용 (사용자 설정)
        max_per_type = getattr(user, "max_rune_per_type", 3)
        if GimmickUpdater._has_trait(user, "rune_archivist"):
            max_per_type += 1

        current_type = target.carved_runes.get(rune_type, 0)
        if current_type >= max_per_type:
            logger.info(f"[룬 각인 실패] 타입별 상한 {rune_type} ({current_type}/{max_per_type})")
            return False

        target.carved_runes[rune_type] = current_type + 1

        # 사용자 보유 룬 총합 갱신 (속성이 없으면 생성)
        user_field = f"rune_{rune_type}"
        current_user_runes = getattr(user, user_field, 0)
        setattr(user, user_field, current_user_runes + 1)

        return True

    @staticmethod
    def _consume_carved_runes(user, target, rune_counts=None):
        """대상에 새겨진 룬을 소모하고 사용자 카운터 감소"""
        if not target or not hasattr(target, "carved_runes"):
            return {}

        if rune_counts is None:
            rune_counts = dict(getattr(target, "carved_runes", {}))

        for rune_type, count in rune_counts.items():
            user_field = f"rune_{rune_type}"
            if hasattr(user, user_field):
                setattr(user, user_field, max(0, getattr(user, user_field, 0) - count))

        target.carved_runes = {rt: max(0, cnt - rune_counts.get(rt, 0)) for rt, cnt in target.carved_runes.items()}
        target.carved_runes = {k: v for k, v in target.carved_runes.items() if v > 0}
        if hasattr(target, "resonance_anchor"):
            target.resonance_anchor = 0

        return rune_counts

    @staticmethod
    def _get_carved_rune_count(target) -> int:
        if not target or not hasattr(target, "carved_runes"):
            return 0
        return sum(getattr(target, "carved_runes", {}).values())

    @staticmethod
    def _grant_resonance_gauge(user, amount: int):
        if not hasattr(user, "resonance_gauge"):
            return 0
        max_gauge = getattr(user, "max_resonance_gauge", 100)
        gain = amount
        # resonance_expert 특성: 게이지 획득량 +25% (최대 게이지 증가는 제거됨)
        if GimmickUpdater._has_trait(user, "resonance_expert"):
            gain = int(gain * 1.25)
        before = user.resonance_gauge
        user.resonance_gauge = min(max_gauge, before + gain)
        return user.resonance_gauge - before

    @staticmethod
    def _pre_rune_resonance_skill(user, skill, target, context):
        """룬 공명 스킬 선처리 - 룬 각인/변환/폭발 준비"""
        import random

        meta = getattr(skill, "metadata", {}) or {}
        hook = {"rune_detonations": [], "messages": []}

        target_list = target if isinstance(target, list) else [target]
        alive_targets = [t for t in target_list if t and getattr(t, "is_alive", True)]
        
        # 광역 룬 새김 시 모든 살아있는 적을 대상으로 함
        if meta.get("carve_all_targets"):
            all_enemies = []
            # context에서 적 가져오기 (all_enemies 키 사용)
            if context and 'all_enemies' in context:
                all_enemies = [e for e in context['all_enemies'] if getattr(e, 'is_alive', True)]
            # context에 없으면 combat_manager에서 가져오기
            if not all_enemies:
                try:
                    from src.combat.combat_manager import get_combat_manager
                    cm = get_combat_manager()
                    if cm and hasattr(cm, 'enemies'):
                        all_enemies = [e for e in cm.enemies if getattr(e, 'is_alive', True)]
                except Exception:
                    pass
            # 여전히 없으면 target_list 사용
            if all_enemies:
                alive_targets = all_enemies

        # 룬 각인
        if meta.get("carve_random_rune") or meta.get("carve_rune_type"):
            carve_targets = alive_targets if meta.get("carve_all_targets") else (alive_targets[:1] if alive_targets else [])
            logger.info(f"[룬 각인] carve_all_targets={meta.get('carve_all_targets')}, alive_targets={len(alive_targets)}명, carve_targets={len(carve_targets)}명")
            try:
                carve_count = int(meta.get("carve_count", 1))
            except Exception:
                carve_count = 1
            carve_count = max(1, carve_count)
            type_source = meta.get("carve_rune_type")
            for t in carve_targets:
                for i in range(carve_count):
                    if type_source:
                        if isinstance(type_source, list):
                            rune_type = type_source[i % len(type_source)]
                        else:
                            rune_type = type_source
                    else:
                        rune_type = random.choice(["fire", "ice", "lightning", "earth", "arcane"])
                    success = GimmickUpdater._add_carved_rune(user, t, rune_type, meta.get("max_rune_slots"))
                    logger.info(f"[룬 각인] {t.name} <- {rune_type} 룬 (성공={success})")
                    if success:
                        hook["messages"].append(f"룬 각인: {rune_type}")

        # 룬 변환
        if meta.get("swap_runes") and alive_targets:
            order = meta.get("swap_order", ["fire", "lightning", "ice", "earth", "arcane"])
            swap_count = meta.get("swap_count", 1)
            t = alive_targets[0]
            conversions = 0
            if hasattr(t, "carved_runes") and t.carved_runes:
                for _ in range(swap_count):
                    if not t.carved_runes:
                        break
                    src_type = max(t.carved_runes, key=t.carved_runes.get)
                    try:
                        idx = order.index(src_type)
                        dst_type = order[(idx + 1) % len(order)]
                    except ValueError:
                        break
                    if src_type == dst_type:
                        break
                    t.carved_runes[src_type] = max(0, t.carved_runes.get(src_type, 0) - 1)
                    if t.carved_runes.get(src_type) == 0:
                        t.carved_runes.pop(src_type, None)
                    GimmickUpdater._consume_carved_runes(user, t, {src_type: 1})
                    if GimmickUpdater._add_carved_rune(user, t, dst_type, meta.get("max_rune_slots")):
                        conversions += 1
                        hook["messages"].append(f"룬 변환: {src_type}→{dst_type}")
            if conversions > 0:
                hook["swap_conversions"] = conversions

        # 룬 폭발 준비 (단일 대상)
        if meta.get("detonate_target_runes") and alive_targets:
            t = alive_targets[0]
            rune_snapshot = dict(getattr(t, "carved_runes", {}))
            total_runes = sum(rune_snapshot.values())
            hook["rune_detonations"].append({"target": t, "runes": rune_snapshot})
            hook["snapshot"] = {"total_runes": total_runes}

        # 전장 모든 룬 폭발 준비 (Grand Resonance)
        if meta.get("detonate_all_runes"):
            enemies = context.get("all_enemies", []) if context else []
            total_runes = 0
            for enemy in enemies:
                if not enemy or not getattr(enemy, "is_alive", True):
                    continue
                rune_snapshot = dict(getattr(enemy, "carved_runes", {}))
                total = sum(rune_snapshot.values())
                total_runes += total
                if total > 0:
                    hook["rune_detonations"].append({"target": enemy, "runes": rune_snapshot})
            hook["snapshot"] = {"total_runes": total_runes}

        # 스냅샷 컨텍스트 전달 (DamageEffect gimmick_bonus 사용)
        if hook.get("snapshot"):
            context["snapshot_context"] = hook["snapshot"]

        hook["resonance_gain_per_rune"] = meta.get("resonance_gain_per_rune", 0)
        hook["spread_chance"] = meta.get("spread_chance", 0.0)
        hook["aoe_falloff"] = meta.get("aoe_falloff", [])
        hook["consume_resonance_gauge"] = meta.get("consume_resonance_gauge", False)

        return hook

    @staticmethod
    def _post_rune_resonance_skill(user, skill, target, context, hook, total_damage):
        """룬 공명 스킬 후처리 - 실제 폭발/게이지 처리"""
        import random
        from src.character.skills.effects.damage_effect import DamageEffect, DamageType
        from src.character.skills.effects.status_effect import StatusEffect, StatusType

        result = {"extra_damage": 0, "extra_heal": 0, "messages": []}
        meta = getattr(skill, "metadata", {}) or {}

        def _apply_direct_rune_damage(u, tgt, base_mult: float, hit_idx: int = 1, hit_total: int = 1, sfx=None) -> int:
            """공/마 공격력 기반 방어/마방으로 나눈 뒤 MAX BRV 비례 HP 피해 + 히트 이벤트"""
            if not tgt or not getattr(tgt, "is_alive", True):
                return 0
            atk = max(getattr(u, "physical_attack", 0), getattr(u, "magic_attack", 0))
            p_def = getattr(tgt, "physical_defense", 1) or 1
            m_def = getattr(tgt, "magic_defense", p_def) or 1
            defense = min(p_def, m_def)
            max_brv = getattr(u, "max_brv", 100) or 100
            ratio = max(0.2, atk / max(1, defense))
            damage = int(ratio * base_mult * max_brv)
            damage = max(1, damage)
            actual = damage
            damage_type = "hp"
            try:
                if hasattr(tgt, "take_damage"):
                    actual = tgt.take_damage(damage, damage_type=damage_type)
                else:
                    hp_before = getattr(tgt, "current_hp", 0)
                    tgt.current_hp = max(0, hp_before - damage)
                    actual = hp_before - tgt.current_hp
            except Exception:
                pass

            if actual > 0:
                try:
                    from src.core.event_bus import event_bus, Events
                    import random
                    hit_info = {
                        "attacker": u,
                        "target": tgt,
                        "damage_type": "hp",
                        "brv_damage": 0,
                        "hp_damage": actual,
                        "is_critical": False,
                        "is_break": False,
                        "multi_hit_current": hit_idx,
                        "multi_hit_total": hit_total,
                        "sfx": sfx or ("skill", "skill3", random.uniform(1.3, 1.5)),
                    }
                    event_bus.publish(Events.COMBAT_HIT, hit_info)
                except Exception:
                    pass
            return actual

        # 룬 폭발 처리
        detos = hook.get("rune_detonations", [])
        spread_chance = hook.get("spread_chance", 0.0)
        falloff = hook.get("aoe_falloff", [])

        # 완전 공명 상태 체크 (게이지 100 도달 시 자동 발동)
        perfect_resonance = getattr(user, 'perfect_resonance', False)
        gauge_bonus_mult = 1.0

        if perfect_resonance:
            gauge_bonus_mult = 2.5  # 피해량 +150%
            spread_chance += 0.5  # 연쇄 확률 +50%
            falloff = [min(1.0, f * 1.5) for f in falloff]  # 확산 피해 +50%
            result["messages"].append("완전 공명! 룬 폭발 극대 강화!")
            user.perfect_resonance = False  # 1회 사용 후 해제

        if GimmickUpdater._has_trait(user, "chain_ignition"):
            spread_chance += 0.15
            falloff = [min(1.0, f * 1.1) for f in falloff]

        pulse_gauge = 0
        if meta.get("resonance_pulse_consume") and hasattr(user, "resonance_gauge"):
            pulse_gauge = max(0, getattr(user, "resonance_gauge", 0))
            if pulse_gauge > 0:
                # 완전 공명과 중첩 가능
                gauge_bonus_mult += min(1.0, pulse_gauge * 0.005)
                spread_chance += min(0.2, pulse_gauge * 0.002)
                result["messages"].append(f"공명 게이지 {pulse_gauge} 소모")
                user.resonance_gauge = 0

        for entry in detos:
            t = entry.get("target")
            rune_counts = entry.get("runes", {})
            total_runes = sum(rune_counts.values())
            if not t or total_runes <= 0:
                continue

            anchor_bonus = getattr(t, "resonance_anchor", 0) or meta.get("anchor_bonus", 0)

            # 추가 폭발 피해 (연쇄 느낌을 주기 위해 별도 타격)
            base_mult = (0.6 + total_runes * 0.2) * gauge_bonus_mult
            base_mult *= (1 + anchor_bonus)
            applied = _apply_direct_rune_damage(user, t, base_mult, hit_idx=1, hit_total=1, sfx=("skill", "skill3", random.uniform(1.3, 1.5)))
            if applied:
                result["extra_damage"] += applied
            result["messages"].append(f"룬 폭발 {total_runes}스택")

            # 광역 충격: 다른 적들도 동시 피해
            enemies_all = context.get("all_enemies", []) if context else []
            aoe_targets = [e for e in enemies_all if e and getattr(e, "is_alive", True) and e != t]
            if aoe_targets:
                for aoe_idx, aoe_t in enumerate(aoe_targets):
                    aoe_applied = _apply_direct_rune_damage(
                        user,
                        aoe_t,
                        base_mult * 0.7,
                        hit_idx=aoe_idx + 1,
                        hit_total=len(aoe_targets),
                        sfx=("skill", "skill3", random.uniform(1.3, 1.5))
                    )
                    result["extra_damage"] += aoe_applied
                result["messages"].append("룬 충격파 확산")

            # 추가 연쇄 확률: 남은 룬 중 하나 더 폭발 (기본 30% + 체인 점화)
            remaining = sum(getattr(t, "carved_runes", {}).values())
            if remaining > 0:
                extra_chance = 0.30
                if GimmickUpdater._has_trait(user, "chain_ignition"):
                    extra_chance += 0.15
                if random.random() < extra_chance:
                    # 임의 룬 하나 소비 후 추가 폭발
                    rune_type_extra = next(iter(getattr(t, "carved_runes", {}).keys()))
                    GimmickUpdater._consume_carved_runes(user, t, {rune_type_extra: 1})
                    extra_hit = _apply_direct_rune_damage(
                        user,
                        t,
                        base_mult * 0.8,
                        hit_idx=1,
                        hit_total=1,
                        sfx=("skill", "skill3", random.uniform(1.3, 1.5))
                    )
                    if extra_hit:
                        result["extra_damage"] += extra_hit
                        result["messages"].append("추가 룬 연쇄 폭발")

            # 룬 소모 및 게이지 증가
            GimmickUpdater._consume_carved_runes(user, t, rune_counts)
            gauge_gain = hook.get("resonance_gain_per_rune", 0) * total_runes
            gained = GimmickUpdater._grant_resonance_gauge(user, gauge_gain)
            if gained:
                result["messages"].append(f"공명 게이지 +{gained}")

            # 룬 타입별 2차 효과 (간략 적용)
            for rtype in rune_counts:
                if rtype == "fire":
                    StatusEffect(StatusType.BURN, duration=2, value=1.0, damage_multiplier=0.08, damage_stat="magic").execute(user, t, context)
                elif rtype == "ice":
                    StatusEffect(StatusType.SLOW, duration=2, value=0.25).execute(user, t, context)
                elif rtype == "lightning":
                    StatusEffect(StatusType.SHOCK, duration=1, value=1.0, chance=0.35).execute(user, t, context)
                elif rtype == "earth":
                    try:
                        from src.character.skills.effects.buff_effect import BuffEffect, BuffType
                        BuffEffect(BuffType.DEFENSE_DOWN, 0.12, duration=2).execute(user, t, context)
                    except Exception:
                        pass
                elif rtype == "arcane":
                    # 비전 룬: 파티 전체 MP 회복 (광역화, 효과 50% 감소: 5 → 2)
                    party_members = context.get("party_members", []) if context else []
                    if not party_members and hasattr(user, "_combat_manager"):
                        cm = user._combat_manager
                        if hasattr(cm, "allies"):
                            party_members = [a for a in cm.allies if getattr(a, "is_alive", True)]
                    if not party_members:
                        party_members = [user]  # 최소한 본인이라도 회복

                    total_restored = 0
                    for ally in party_members:
                        if hasattr(ally, "restore_mp"):
                            restored = ally.restore_mp(2)  # 5에서 2로 감소 (50%)
                            total_restored += restored
                    if total_restored > 0:
                        result["messages"].append(f"파티 MP +{total_restored}")

            # 확산 연쇄: 다른 적의 룬도 폭발시킴 (재귀적 연쇄)
            enemies = context.get("all_enemies", []) if context else []

            if enemies and spread_chance > 0:
                # 재귀적 연쇄 폭발 함수
                def trigger_chain_explosion(source_target, already_exploded, depth=0):
                    """재귀적으로 연쇄 폭발을 일으킴"""
                    if depth >= 10:  # 최대 깊이 제한
                        return 0

                    # 아직 폭발하지 않은 다른 적들 중 룬을 가진 적 찾기
                    other_enemies = [e for e in enemies
                                    if e and getattr(e, "is_alive", True)
                                    and e != source_target
                                    and e not in already_exploded
                                    and sum(getattr(e, "carved_runes", {}).values()) > 0]

                    if not other_enemies:
                        return 0

                    chain_count = 0

                    # 각 대상마다 확률 체크
                    for chain_target in other_enemies[:]:
                        if random.random() <= spread_chance:
                            # 대상의 룬 가져오기 - 1개만 폭발
                            carved_runes = getattr(chain_target, "carved_runes", {})
                            available_runes = [rtype for rtype, count in carved_runes.items() if count > 0]

                            if available_runes:
                                # 랜덤으로 1개 타입 선택
                                selected_rune = random.choice(available_runes)
                                chain_rune_counts = {selected_rune: 1}  # 1개만 폭발

                                chain_count += 1
                                # 연쇄 폭발 피해 (1개 룬 기준, 연쇄 깊이에 따라 감쇠)
                                chain_mult = (0.5 + 0.15) * gauge_bonus_mult * (0.7 ** (depth + 1))
                                chain_applied = _apply_direct_rune_damage(
                                    user,
                                    chain_target,
                                    chain_mult,
                                    hit_idx=1,
                                    hit_total=1,
                                    sfx=("skill", "skill3", random.uniform(1.3, 1.5))
                                )
                                if chain_applied:
                                    result["extra_damage"] += chain_applied

                                # 연쇄된 룬 1개만 소모
                                GimmickUpdater._consume_carved_runes(user, chain_target, chain_rune_counts)

                                # 연쇄 폭발도 게이지 증가 (1개 기준)
                                chain_gauge_gain = hook.get("resonance_gain_per_rune", 0) * 1 * 0.5
                                if chain_gauge_gain > 0:
                                    GimmickUpdater._grant_resonance_gauge(user, int(chain_gauge_gain))

                                # 이 적을 폭발한 목록에 추가
                                already_exploded.add(chain_target)

                                # 재귀: 이 폭발도 다른 적들에게 연쇄 시도
                                chain_count += trigger_chain_explosion(chain_target, already_exploded, depth + 1)

                    return chain_count

                # 최초 폭발 대상 제외하고 연쇄 시작
                already_exploded = {t}
                total_chains = trigger_chain_explosion(t, already_exploded, 0)

                # 연쇄 횟수 메시지
                if total_chains > 0:
                    result["messages"].append(f"연쇄 룬 폭발! x{total_chains}")

        # 팀워크: 즉시 1회 기폭 처리
        if meta.get("detonate_one") and context:
            enemies = context.get("all_enemies", [])
            if enemies:
                tgt = next((e for e in enemies if getattr(e, "carved_runes", None)), None)
                if tgt and getattr(tgt, "carved_runes", {}):
                    rtype = next(iter(tgt.carved_runes.keys()))
                    applied = _apply_direct_rune_damage(user, tgt, 0.6, hit_idx=1, hit_total=1, sfx=("skill", "explosion"))
                    result["extra_damage"] += applied
                    GimmickUpdater._consume_carved_runes(user, tgt, {rtype: 1})
                    GimmickUpdater._grant_resonance_gauge(user, 5)
                    result["messages"].append("Rune Trigger 연계 폭발")

        # 촉매 엔지니어: 변환된 룬 수만큼 속도 버프
        if hook.get("swap_conversions") and GimmickUpdater._has_trait(user, "catalyst_engineer"):
            try:
                from src.character.skills.effects.buff_effect import BuffEffect, BuffType
                bonus = 0.03 * hook.get("swap_conversions", 0)
                BuffEffect(BuffType.SPEED_UP, bonus, duration=2, target="self").execute(user, user, context)
                result["messages"].append(f"촉매 가속 +{int(bonus*100)}%")
            except Exception:
                pass

        # 공명 게이지 소모 (Grand Resonance)
        if meta.get("consume_resonance_gauge") and hasattr(user, "resonance_gauge"):
            user.resonance_gauge = 0

        # 비전 도체 특성: 룬 폭발 후 MP 회복
        if GimmickUpdater._has_trait(user, "arcane_conductor") and hasattr(user, "restore_mp"):
            if meta.get("detonate_target_runes") or meta.get("detonate_all_runes"):
                restored = user.restore_mp(8)
                if restored:
                    result["messages"].append(f"MP +{restored}")

        return result
    
    @staticmethod
    def _has_trait(character, trait_id: str) -> bool:
        """특성 보유 여부 확인"""
        if not hasattr(character, 'active_traits'):
            return False
        
        for trait in character.active_traits:
            tid = trait if isinstance(trait, str) else trait.get('id', '')
            if tid == trait_id:
                return True
        return False

    # ============================================================
    # 기계공학자 - 포탑 시스템
    # ============================================================

    @staticmethod
    def _turret_auto_attack(character, context=None):
        """기계공학자: 포탑 자동 공격 및 열 증가"""
        import random

        turret_count = getattr(character, 'turret_count', 0)
        if turret_count <= 0:
            return

        # 포탑 1개당 열 +1 (열 감소는 _update_heat_management에서만 처리)
        turret_heat = turret_count * 1
        if turret_heat > 0:
            new_heat = getattr(character, 'heat', 0) + turret_heat
            character.heat = max(0, min(getattr(character, 'max_heat', 100), new_heat))
            logger.info(f"[포탑 시스템] {character.name}: 포탑 {turret_count}개 × 1 = 열 +{turret_heat} (총: {character.heat})")

        # 스턴 상태면 포탑 공격 안함
        if getattr(character, 'is_stunned', False):
            logger.info(f"[포탑 시스템] {character.name}: 스턴 상태로 포탑 공격 불가")
            return

        # 적 목록 가져오기
        enemies = []
        if context and 'combat_manager' in context:
            combat_manager = context['combat_manager']
            if hasattr(combat_manager, 'enemies'):
                enemies = [e for e in combat_manager.enemies if getattr(e, 'is_alive', True)]

        if not enemies:
            logger.debug(f"[포탑 시스템] {character.name}: 공격할 적이 없습니다")
            return

        # 공격력 가져오기
        if hasattr(character, 'stat_manager'):
            attack_power = character.stat_manager.get_value("strength")
            logger.info(f"[포탑 디버그] {character.name} StatManager 공격력: {attack_power}")
        else:
            attack_power = getattr(character, 'physical_attack', 50)
            logger.info(f"[포탑 디버그] {character.name} 기본 공격력: {attack_power}")

        # 포탑별로 랜덤 적 공격
        for i in range(turret_count):
            target = random.choice(enemies)

            # 포탑 타입별 데미지 계산
            damage_multiplier = 1.0
            turret_type = "normal"

            # 특수 포탑 확인
            fire_count = getattr(character, 'fire_turret_count', 0)
            ice_count = getattr(character, 'ice_turret_count', 0)
            thunder_count = getattr(character, 'thunder_turret_count', 0)
            explosive_count = getattr(character, 'explosive_turret_count', 0)
            heal_count = getattr(character, 'heal_turret_count', 0)

            # 포탑 종류별 배율 (밸런스 상향)
            special_turrets = []
            if fire_count > 0:
                special_turrets.extend([("fire", 0.60)] * fire_count)
            if ice_count > 0:
                special_turrets.extend([("ice", 0.40)] * ice_count)
            if thunder_count > 0:
                special_turrets.extend([("thunder", 0.50)] * thunder_count)
            if explosive_count > 0:
                special_turrets.extend([("explosive", 0.70)] * explosive_count)
            if heal_count > 0:
                special_turrets.extend([("heal", 0.0)] * heal_count)

            # 일반 포탑
            normal_count = turret_count - len(special_turrets)
            special_turrets.extend([("normal", 0.50)] * normal_count)

            if i < len(special_turrets):
                turret_type, damage_multiplier = special_turrets[i]

            # 치유 포탑 처리
            if turret_type == "heal":
                allies = []
                if context and 'combat_manager' in context:
                    combat_manager = context['combat_manager']
                    if hasattr(combat_manager, 'allies'):
                        allies = [a for a in combat_manager.allies if getattr(a, 'is_alive', True)]

                if allies:
                    heal_target = min(allies, key=lambda a: a.current_hp / max(1, a.max_hp))
                    heal_amount = int(attack_power * 0.30)
                    old_hp = heal_target.current_hp
                    heal_target.current_hp = min(heal_target.max_hp, heal_target.current_hp + heal_amount)
                    actual_heal = heal_target.current_hp - old_hp
                    if actual_heal > 0:
                        logger.info(f"[치유 포탑] {heal_target.name} HP +{actual_heal}")
                continue

            # 데미지 계산 (방어력 영향 + MAXBRV 보너스)
            # 공식: 기본피해 * 계수(1.0) * (MAXBRV / (적방어력 * 4))
            max_brv = getattr(character, 'max_brv', 100)
            enemy_defense = getattr(target, 'physical_defense', 20)
            enemy_defense = max(1, enemy_defense)  # 0 방지
            
            base_damage = attack_power * damage_multiplier
            brv_bonus = max_brv / (enemy_defense * 4)
            damage = int((base_damage * 1.0 + base_damage * brv_bonus) / 10)  # 피해량 1/10로 조정
            damage = max(1, damage)  # 최소 1 피해
            
            # 포탑 강화 특성 적용 (+20% 피해량)
            if hasattr(character, 'active_traits') and 'turret_reinforcement' in character.active_traits:
                damage = int(damage * 1.20)
                logger.debug(f"[포탑 강화] {character.name} 피해량 +20%: {damage}")
            
            # 크리티컬 계산
            is_critical = False
            base_crit_rate = getattr(character, 'crit_rate', 0.05)  # 기본 5%
            heat_crit_bonus = getattr(character, 'heat_crit_bonus', 0)  # 위험 구간 +20%
            total_crit_rate = base_crit_rate + heat_crit_bonus
            
            if random.random() < total_crit_rate:
                is_critical = True
                crit_multiplier = getattr(character, 'crit_damage', 1.5)  # 기본 150%
                damage = int(damage * crit_multiplier)
                logger.info(f"[포탑 크리티컬] {character.name} 피해량 x{crit_multiplier}: {damage}")
            
            # BREAK 보너스 (적 BRV가 0일 때 +50% 피해)
            is_break = False
            target_brv = getattr(target, 'current_brv', 0)
            if target_brv <= 0:
                is_break = True
                damage = int(damage * 1.5)
                logger.info(f"[포탑 BREAK 보너스] {character.name} 피해량 +50%: {damage}")
            
            # 디버그: 공식 확인
            logger.debug(f"[포탑 공식] {character.name}: 공격력{attack_power}×{damage_multiplier}={base_damage}, MAXBRV{max_brv}, 방어력{enemy_defense}, BRV보너스{brv_bonus:.2f}, 크리티컬{is_critical}, BREAK{is_break}, 최종{damage}")

            # HP 직접 공격 (SFX는 hit_queue에서 딜레이 적용하여 재생)
            from src.core.event_bus import event_bus, Events
            
            random_pitch = random.uniform(0.85, 1.15)
            sfx_info = ("combat", "attack_gun", random_pitch)
            
            if hasattr(target, 'take_damage'):
                logger.info(f"[포탑 디버그] {target.name}에게 {damage} 피해 시도 (take_damage 호출)")
                actual_damage = target.take_damage(damage)
                logger.info(f"[포탑 디버그] {target.name} 실제 피해: {actual_damage}")
            elif hasattr(target, 'current_hp'):
                old_hp = target.current_hp
                target.current_hp = max(0, target.current_hp - damage)
                actual_damage = old_hp - target.current_hp
                if target.current_hp <= 0:
                    target.is_alive = False
            else:
                actual_damage = damage
            
            # 다단히트 이벤트 발생 (UI 타격감용 + SFX)
            hit_info = {
                'attacker': character,
                'target': target,
                'damage_type': 'hp',
                'brv_damage': 0,
                'hp_damage': actual_damage,
                'is_critical': is_critical,
                'is_break': is_break,
                'multi_hit_current': i + 1,
                'multi_hit_total': turret_count,
                'sfx': sfx_info,  # SFX 정보 (category, name, pitch)
            }
            event_bus.publish(Events.COMBAT_HIT, hit_info)

            # 상태 효과 적용
            status_applied = ""
            # 포탑 강화 특성으로 상태이상 확률 +10%
            fire_chance = 0.20
            ice_chance = 0.25
            thunder_chance = 0.15
            
            if hasattr(character, 'active_traits') and 'turret_reinforcement' in character.active_traits:
                fire_chance += 0.10
                ice_chance += 0.10
                thunder_chance += 0.10
                logger.info(f"[포탑 강화] {character.name} 상태이상 확률 +10%")
            
            if turret_type == "fire" and random.random() < fire_chance:
                status_applied = " (화상)"
                if hasattr(target, 'status_manager'):
                    try:
                        from src.combat.status_effects import StatusEffect, StatusType
                        burn = StatusEffect("화상", StatusType.BURN, duration=2, intensity=0.03)
                        target.status_manager.add_status(burn)
                    except:
                        pass
            elif turret_type == "ice" and random.random() < ice_chance:
                status_applied = " (둔화)"
                if hasattr(target, 'status_manager'):
                    try:
                        from src.combat.status_effects import StatusEffect, StatusType
                        slow = StatusEffect("둔화", StatusType.SLOW, duration=1, intensity=0.15)
                        target.status_manager.add_status(slow)
                    except:
                        pass
            elif turret_type == "thunder" and random.random() < thunder_chance:
                status_applied = " (마비)"
                if hasattr(target, 'status_manager'):
                    try:
                        from src.combat.status_effects import StatusEffect, StatusType
                        paralyze = StatusEffect("마비", StatusType.PARALYZE, duration=1, intensity=1.0)
                        target.status_manager.add_status(paralyze)
                    except:
                        pass

            logger.info(f"[{turret_type.upper()} 포탑] {target.name}에게 {actual_damage} HP 피해{status_applied}")

    @staticmethod
    def on_take_damage_turret(character, attacker, hit_count=1):
        """기계공학자: 피격 시 포탑 파괴 및 피해 감소"""
        turret_count = getattr(character, 'turret_count', 0)
        if turret_count <= 0:
            return 1.0

        destroyed = min(hit_count, turret_count)
        character.turret_count = max(0, turret_count - destroyed)

        import random
        for _ in range(destroyed):
            special_turrets = []
            if getattr(character, 'fire_turret_count', 0) > 0:
                special_turrets.append('fire_turret_count')
            if getattr(character, 'ice_turret_count', 0) > 0:
                special_turrets.append('ice_turret_count')
            if getattr(character, 'thunder_turret_count', 0) > 0:
                special_turrets.append('thunder_turret_count')
            if getattr(character, 'explosive_turret_count', 0) > 0:
                special_turrets.append('explosive_turret_count')
            if getattr(character, 'heal_turret_count', 0) > 0:
                special_turrets.append('heal_turret_count')
            
            if special_turrets:
                to_destroy = random.choice(special_turrets)
                current = getattr(character, to_destroy, 0)
                setattr(character, to_destroy, max(0, current - 1))

        logger.info(f"[포탑 파괴] {character.name}: 포탑 {destroyed}개 파괴 (잔여: {character.turret_count})")
        return 0.6
    # 사무라이: 검심 시스템 (Kenshin System)
    # ============================================================

    @staticmethod
    def _update_kenshin_system_turn_end(character):
        """턴 종료 시 관찰 스택 감소 (-1)"""
        observation = getattr(character, "observation", 0)
        if observation > 0:
            character.observation = max(0, observation - 1)
            stage = GimmickUpdater._get_kenshin_stage(character)
            logger.info(f"{character.name} 관찰 스택 -1 (턴 종료) -> {character.observation} [{stage}]")

    @staticmethod
    def _get_kenshin_stage(character):
        """현재 관찰 단계 확인 (초심/무심/검성)"""
        observation = getattr(character, "observation", 0)
        if observation >= 10:
            return "검성(剣聖)"
        elif observation >= 5:
            return "무심(無心)"
        else:
            return "초심(初心)"

    @staticmethod
    def _get_kenshin_counter_values(character):
        """관찰 단계에 따른 반격 수치 반환 (피해 감소, BRV 반사)"""
        observation = getattr(character, "observation", 0)

        # 검성 (10+): 35% 감소, 80% 반사
        if observation >= 10:
            return 0.35, 0.8
        # 무심 (5-9): 20% 감소, 50% 반사
        elif observation >= 5:
            return 0.20, 0.5
        # 초심 (0-4): 10% 감소, 30% 반사
        else:
            return 0.10, 0.3

    @staticmethod
    def _apply_kenshin_counter(character, damage_taken: int, attacker=None):
        """피격 시 반격 시스템 적용 (데미지 감소 + BRV 반사)

        Args:
            character: 사무라이 캐릭터
            damage_taken: 받은 피해량
            attacker: 공격자

        Returns:
            tuple: (감소된 최종 피해, BRV 반사량)
        """
        damage_reduction, counter_rate = GimmickUpdater._get_kenshin_counter_values(character)

        # 피해 감소
        reduced_damage = int(damage_taken * (1 - damage_reduction))
        damage_blocked = damage_taken - reduced_damage

        # BRV 반사 (받은 원본 피해의 일정 비율)
        brv_reflection = int(damage_taken * counter_rate)

        # 관찰 스택 증가 (+1~3, 피해량에 비례)
        observation_gain = 1
        max_hp = getattr(character, "max_hp", 1)
        if damage_taken >= max_hp * 0.2:  # 최대 HP의 20% 이상 피해
            observation_gain = 3
        elif damage_taken >= max_hp * 0.1:  # 최대 HP의 10% 이상 피해
            observation_gain = 2

        character.observation = min(getattr(character, "max_observation", 10),
                                    getattr(character, "observation", 0) + observation_gain)

        # 검압 게이지 증가 (+5~15, 피해량에 비례)
        kenatsu_gain = min(15, max(5, int(damage_taken / 10)))
        character.kenatsu = min(getattr(character, "max_kenatsu", 100),
                               getattr(character, "kenatsu", 0) + kenatsu_gain)

        stage = GimmickUpdater._get_kenshin_stage(character)
        logger.info(f"[검심 반격] {character.name} {stage} 피해 -{damage_blocked} | BRV 반사 +{brv_reflection} | 관찰 +{observation_gain} | 검압 +{kenatsu_gain}")

        # 반사 BRV를 자신의 BRV에 추가
        if brv_reflection > 0:
            current_brv = getattr(character, "current_brv", 0)
            max_brv = getattr(character, "max_brv", 9999)
            character.current_brv = min(max_brv, current_brv + brv_reflection)

        return reduced_damage, brv_reflection

    @staticmethod
    def _apply_kenshin_brv_steal(character, skill, context=None):
        """미키리 스킬: 적의 BRV 흡수

        Args:
            character: 사무라이 캐릭터
            skill: 미키리 스킬
            context: 스킬 실행 컨텍스트 (target 포함)
        """
        if not context or 'target' not in context:
            logger.warning(f"[미키리] {character.name} BRV 흡수 실패: 대상 없음")
            return

        target = context['target']
        if not hasattr(target, 'current_brv'):
            logger.warning(f"[미키리] {target.name}는 BRV가 없음")
            return

        # 적의 현재 BRV
        target_brv = getattr(target, 'current_brv', 0)
        if target_brv <= 0:
            logger.info(f"[미키리] {target.name}의 BRV가 0이라 흡수 불가")
            return

        # 관찰 단계에 따른 흡수율 결정
        observation = getattr(character, "observation", 0)
        if observation >= 10:  # 검성
            steal_rate = skill.metadata.get("steal_rate_kensei", 0.8)
        elif observation >= 5:  # 무심
            steal_rate = skill.metadata.get("steal_rate_mushin", 0.6)
        else:  # 초심
            steal_rate = skill.metadata.get("steal_rate_base", 0.5)

        # 특성: 미키리의 달인 (BRV 흡수 +10%)
        if hasattr(character, 'active_traits'):
            for trait in character.active_traits:
                trait_id = trait if isinstance(trait, str) else trait.get('id', '')
                if trait_id == 'brv_absorb_master':
                    steal_rate += 0.1
                    logger.debug(f"[미키리의 달인] 흡수율 +10%")
                    break

        # BRV 흡수량 계산
        stolen_brv = int(target_brv * steal_rate)

        # 적의 BRV 감소
        target.current_brv = max(0, target_brv - stolen_brv)

        # 사무라이의 BRV 증가
        current_brv = getattr(character, "current_brv", 0)
        max_brv = getattr(character, "max_brv", 9999)
        character.current_brv = min(max_brv, current_brv + stolen_brv)

        stage = GimmickUpdater._get_kenshin_stage(character)
        logger.info(f"[미키리] {character.name} [{stage}] {target.name}의 BRV {stolen_brv} 흡수! ({int(steal_rate*100)}%)")
        logger.info(f"  → {character.name} BRV: {current_brv} → {character.current_brv}")
        logger.info(f"  → {target.name} BRV: {target_brv} → {target.current_brv}")

    @staticmethod
    def _apply_kenshin_prediction(character, skill, context=None):
        """요미 스킬: 적의 다음 행동 예측

        Args:
            character: 사무라이 캐릭터
            skill: 요미 스킬
            context: 스킬 실행 컨텍스트 (enemies 리스트 포함)
        """
        # 토글 상태 보정: active_toggles가 없거나 요미가 누락된 경우 추가
        if not hasattr(character, "active_toggles"):
            character.active_toggles = []
        if "samurai_yomi" not in character.active_toggles:
            character.active_toggles.append("samurai_yomi")
            GimmickUpdater._push_ui_log(character, "[요미] 예측 활성화 (토글 ON)")

        # 컨텍스트에서 적 목록 가져오기 (없으면 전투 관리자에서 조회)
        enemies = []
        if context:
            enemies = context.get('enemies') or []
            if not enemies:
                enemies = context.get('all_enemies', []) or []
            if not enemies and 'combat_manager' in context:
                cm = context.get('combat_manager')
                enemies = getattr(cm, 'enemies', []) if cm else []
        if not enemies:
            logger.warning(f"[요미] {character.name} 예측 실패: 적 정보 없음")
            GimmickUpdater._push_ui_log(character, "[요미] 예측 실패: 적 정보 없음", color=(255, 120, 120))
            return

        # 예측 결과를 저장할 딕셔너리 초기화
        if not hasattr(character, 'predicted_actions'):
            character.predicted_actions = {}

        # 예측 턴 수
        prediction_turns = skill.metadata.get('prediction_turns', 2)

        logger.info(f"[요미] {character.name} 적의 다음 {prediction_turns}턴 행동 예측...")

        # 각 적의 다음 행동 예측
        for enemy in enemies:
            if not getattr(enemy, 'is_alive', False):
                continue

            # 간단한 휴리스틱 기반 예측
            action_type = GimmickUpdater._predict_enemy_action(enemy)

            # ATB 정보 가져오기
            current_atb = getattr(enemy, 'atb_gauge', 0)
            atb_threshold = getattr(enemy, 'atb_threshold', 1000)
            atb_percentage = int((current_atb / atb_threshold) * 100) if atb_threshold > 0 else 0

            # 예측 결과 저장
            character.predicted_actions[enemy.name] = {
                'action': action_type,
                'atb': current_atb,
                'atb_max': atb_threshold,
                'atb_percentage': atb_percentage,
                'turns_remaining': prediction_turns
            }

            logger.info(f"  → {enemy.name}: {action_type} (ATB: {atb_percentage}%)")
            GimmickUpdater._push_ui_log(
                character,
                f"[요미] {enemy.name}: {action_type} (ATB {atb_percentage}%)",
                color=(200, 255, 200),
            )

        # 예측 정보를 UI에서 참조할 수 있도록 플래그 설정
        character.prediction_active = True
        character.prediction_turns_left = prediction_turns
        GimmickUpdater._push_ui_log(character, f"[요미] 다음 {prediction_turns}턴 예측 완료", color=(200, 255, 200))

        # 현재 선택된 대상의 예측 정보를 인게임 로그에 즉시 노출 (요미 ON일 때)
        target = None
        if context:
            target = context.get("target") or context.get("primary_target")
        if target and hasattr(target, "name"):
            pred = character.predicted_actions.get(getattr(target, "name"), None)
            if pred:
                act = pred.get("action", "알 수 없음")
                atb_pct = pred.get("atb_percentage", 0)
                GimmickUpdater._push_ui_log(character, f"[요미] 현재 대상 {target.name}: {act} (ATB {atb_pct}%)", color=(255, 255, 120))
            else:
                GimmickUpdater._push_ui_log(character, f"[요미] 현재 대상 {target.name}: 예측 데이터 없음", color=(200, 200, 200))

    @staticmethod
    def _predict_enemy_action(enemy) -> str:
        """적의 다음 행동을 예측 (간단한 휴리스틱)

        Args:
            enemy: 예측할 적

        Returns:
            예측된 행동 타입 문자열
        """
        current_brv = getattr(enemy, 'current_brv', 0)
        max_brv = getattr(enemy, 'max_brv', 9999)
        current_hp = getattr(enemy, 'current_hp', 100)
        max_hp = getattr(enemy, 'max_hp', 100)
        current_mp = getattr(enemy, 'current_mp', 0)

        hp_ratio = current_hp / max(max_hp, 1)
        brv_ratio = current_brv / max(max_brv, 1)
        is_boss = getattr(enemy, 'is_boss', False) or getattr(enemy, 'level', 1) >= 50

        if hp_ratio < 0.3:
            if current_mp >= 20:
                return "회복 스킬 사용 예정"
            return "방어 태세 예정"
        if brv_ratio >= 0.7:
            return "HP 공격 예정"
        if brv_ratio < 0.3:
            return "BRV 공격 예정"
        if is_boss and current_mp >= 30:
            return "강력한 스킬 사용 예정"
        if current_mp >= 15:
            return "스킬 사용 예정"
        return "BRV 공격 예정"

    @staticmethod
    def get_element_stacks(character) -> dict:
        """아크메이지 원소 스택 반환"""
        return {
            'fire': getattr(character, 'fire_element', 0),
            'ice': getattr(character, 'ice_element', 0),
            'lightning': getattr(character, 'lightning_element', 0)
        }

    @staticmethod
    def get_total_element_stacks(character) -> int:
        """아크메이지 총 원소 스택 반환"""
        stacks = GimmickUpdater.get_element_stacks(character)
        return sum(stacks.values())

    @staticmethod
    def check_element_balance(character, element1: str, element2: str) -> bool:
        """두 원소 스택이 균형 상태인지 체크 (각각 3개 이상, 동일)"""
        stack1 = getattr(character, f"{element1}_element", 0)
        stack2 = getattr(character, f"{element2}_element", 0)
        return stack1 == stack2 and stack1 >= 3

    @staticmethod
    def get_element_difference(character, element1: str, element2: str) -> int:
        """두 원소 스택 차이값 계산"""
        stack1 = getattr(character, f"{element1}_element", 0)
        stack2 = getattr(character, f"{element2}_element", 0)
        return abs(stack1 - stack2)

    @staticmethod
    def get_delayed_glyphs(character) -> list:
        """설치된 지연 마법진 목록 반환"""
        return getattr(character, 'delayed_glyphs', [])

    @staticmethod
    def update_delayed_glyphs(character):
        """지연 마법진 턴 업데이트 (자동 발동 처리)"""
        if not hasattr(character, 'delayed_glyphs'):
            return []

        triggered = []
        remaining = []

        for glyph in character.delayed_glyphs:
            glyph['remaining_turns'] -= 1
            if glyph['remaining_turns'] <= 0:
                triggered.append(glyph)
            else:
                remaining.append(glyph)

        character.delayed_glyphs = remaining
        return triggered

    @staticmethod
    def trigger_glyphs_by_elements(character, elements: list) -> list:
        """특정 원소의 마법진 기폭 (융합 스킬 사용 시)"""
        if not hasattr(character, 'delayed_glyphs'):
            return []

        triggered = []
        remaining = []

        for glyph in character.delayed_glyphs:
            if glyph['element'] in elements:
                triggered.append(glyph)
            else:
                remaining.append(glyph)

        character.delayed_glyphs = remaining
        return triggered

    @staticmethod
    def get_elemental_shield(character) -> dict:
        """원소 장막 정보 반환"""
        return getattr(character, 'elemental_shield', {})

    @staticmethod
    def update_elemental_shield(character, damage: int) -> dict:
        """원소 장막 피해 흡수 및 반격 효과 처리"""
        shield = getattr(character, 'elemental_shield', {})
        if not shield or shield.get('amount', 0) <= 0:
            return {'absorbed': 0, 'remaining': 0, 'destroyed': False}

        absorbed = min(damage, shield['amount'])
        shield['amount'] -= absorbed

        result = {
            'absorbed': absorbed,
            'remaining': shield['amount'],
            'destroyed': shield['amount'] <= 0,
            'fire_reflect': shield.get('fire_stacks', 0) * 0.10,
            'ice_slow': shield.get('ice_stacks', 0) * 0.15,
            'lightning_shock': shield.get('lightning_stacks', 0) * 0.15
        }

        if result['destroyed']:
            character.elemental_shield = {}
            # 원소 장막 상태 효과 제거
            if hasattr(character, 'status_manager'):
                try:
                    from src.combat.status_effects import StatusType
                    character.status_manager.remove_status(StatusType.ELEMENTAL_AEGIS)
                except:
                    pass

        return result

    @staticmethod
    def check_brand_vulnerability(target, element: str) -> float:
        """원소 낙인 취약점 확인 (데미지 증가율 반환)"""
        if not hasattr(target, 'status_manager'):
            return 0.0

        brand_types = {
            'fire': 'FIRE_BRAND',
            'ice': 'ICE_BRAND',
            'lightning': 'LIGHTNING_BRAND'
        }

        brand_type = brand_types.get(element)
        if not brand_type:
            return 0.0

        try:
            from src.combat.status_effects import StatusType
            status_type = getattr(StatusType, brand_type, None)
            if status_type:
                effect = target.status_manager.get_status(status_type)
                if effect:
                    return effect.intensity  # 기본 0.40 (40% 증가)
        except:
            pass

        return 0.0


class ElementalBalanceChecker:
    """
    원소 균형 상태 체크 유틸리티 클래스 (아크메이지 전용)
    
    설계 문서에서 정의한 원소 조합 시스템 지원
    """

    @staticmethod
    def check_balance(character, element1: str, element2: str) -> bool:
        """두 원소 스택이 같은지 체크 (3개 이상)"""
        stack1 = getattr(character, f"{element1}_element", 0)
        stack2 = getattr(character, f"{element2}_element", 0)
        return stack1 == stack2 and stack1 >= 3

    @staticmethod
    def get_element_difference(character, element1: str, element2: str) -> int:
        """두 원소 스택 차이값 계산"""
        stack1 = getattr(character, f"{element1}_element", 0)
        stack2 = getattr(character, f"{element2}_element", 0)
        return abs(stack1 - stack2)

    @staticmethod
    def is_perfect_balance(character) -> bool:
        """완벽한 균형 체크 (모든 원소 3개 이상, 동일)"""
        fire = getattr(character, 'fire_element', 0)
        ice = getattr(character, 'ice_element', 0)
        lightning = getattr(character, 'lightning_element', 0)
        return fire == ice == lightning and fire >= 3

    @staticmethod
    def is_complete_cycle_ready(character) -> bool:
        """완전 순환 조건 체크 (모든 원소 2개 이상)"""
        fire = getattr(character, 'fire_element', 0)
        ice = getattr(character, 'ice_element', 0)
        lightning = getattr(character, 'lightning_element', 0)
        return fire >= 2 and ice >= 2 and lightning >= 2

    @staticmethod
    def get_dominant_element(character) -> str:
        """가장 많은 원소 반환"""
        elements = {
            'fire': getattr(character, 'fire_element', 0),
            'ice': getattr(character, 'ice_element', 0),
            'lightning': getattr(character, 'lightning_element', 0)
        }
        return max(elements.items(), key=lambda x: x[1])[0]

    @staticmethod
    def get_weakest_element(character) -> str:
        """가장 적은 원소 반환"""
        elements = {
            'fire': getattr(character, 'fire_element', 0),
            'ice': getattr(character, 'ice_element', 0),
            'lightning': getattr(character, 'lightning_element', 0)
        }
        return min(elements.items(), key=lambda x: x[1])[0]

    @staticmethod
    def can_use_fusion_skill(character, required_elements: list) -> bool:
        """융합 스킬 사용 가능 여부 체크"""
        for element in required_elements:
            stack = getattr(character, f"{element}_element", 0)
            if stack < 1:
                return False
        return True

    @staticmethod
    def can_use_overload(character, min_stacks: int = 3) -> dict:
        """원소 과부하 사용 가능 원소 반환"""
        available = {}
        for element in ['fire', 'ice', 'lightning']:
            stacks = getattr(character, f"{element}_element", 0)
            if stacks >= min_stacks:
                available[element] = stacks
        return available

    @staticmethod
    def get_recommended_action(character) -> str:
        """현재 원소 상태에 따른 추천 행동"""
        fire = getattr(character, 'fire_element', 0)
        ice = getattr(character, 'ice_element', 0)
        lightning = getattr(character, 'lightning_element', 0)
        total = fire + ice + lightning

        # 완벽한 균형 → 상반의 격류
        if fire == ice and fire >= 3:
            return "paradox_surge"  # 상반의 격류 추천

        # 5스택 달성 → 해당 원소 과부하
        if fire >= 5:
            return "fire_overload"
        if ice >= 5:
            return "ice_overload"
        if lightning >= 5:
            return "lightning_overload"

        # 화염+번개 조합 → 폭뢰섬
        if fire >= 3 and lightning >= 3:
            return "thunderstorm_inferno"

        # 빙결+번개 조합 → 극한뇌전
        if ice >= 3 and lightning >= 3:
            return "arctic_tempest"

        # 총 스택 15개 이상 → 원소 장막
        if total >= 15:
            return "elemental_aegis"

        # 낮은 원소 있음 → 원소 순환
        if min(fire, ice, lightning) <= 1 and max(fire, ice, lightning) >= 4:
            return "elemental_transmutation"

        # 기본 → 원소 수집 계속
        return "gather_elements"


# === 이벤트 기반 리메이크 기믹 처리 (서약/관중 요구/농락 보조) ===

def _classify_action_from_skill(skill) -> str:
    """스킬 효과 및 메타데이터 기반 행동 타입 분류"""
    meta = getattr(skill, "metadata", {}) or {}
    # 메타 기반 우선
    if meta.get("purify") or meta.get("cleanse") or meta.get("dispel"):
        return "purify"
    if meta.get("resurrect") or meta.get("revive"):
        return "revive"
    if meta.get("counter"):
        return "counter"
    # 효과 기반
    from src.character.skills.effects.heal_effect import HealEffect
    from src.character.skills.effects.buff_effect import BuffEffect
    from src.character.skills.effects.damage_effect import DamageEffect
    if any(isinstance(e, HealEffect) for e in skill.effects):
        return "heal"
    if any(isinstance(e, BuffEffect) for e in skill.effects):
        return "buff"
    if any(isinstance(e, DamageEffect) for e in skill.effects):
        return "attack"
    return "action"


def _get_faith_reward(oath_data: dict, action_type: str) -> int:
    if not oath_data:
        return 0
    key = f"faith_per_{action_type}"
    if key in oath_data:
        return oath_data.get(key, 0)
    return oath_data.get("faith_per_action", 0)


def _apply_faith_empowerment(character, skill):
    """신앙 100 달성 시 스킬 강화"""
    from src.character.skills.effects.heal_effect import HealEffect
    from src.character.skills.effects.damage_effect import DamageEffect
    from src.character.skills.effects.buff_effect import BuffEffect
    from src.character.skills.effects.status_effect import StatusEffect

    # 스킬별 강화 효과
    skill_id = getattr(skill, 'skill_id', getattr(skill, 'id', skill.metadata.get('id', '')))

    # 회복기들
    if skill_id == "priest_holy_heal":
        # 축복의 치유: 회복량 1.125배 → 2.625배
        faith_mult = skill.metadata.get("faith_multiplier", 2.625)
        for effect in skill.effects:
            if isinstance(effect, HealEffect):
                if not hasattr(effect, '_original_multiplier'):
                    effect._original_multiplier = effect.multiplier
                effect.multiplier = faith_mult
                logger.info(f"[신앙 강화] {skill.name} 회복량 강화")
                break

    elif skill_id == "priest_heal":
        # 신성 치유: 회복량 1.725배 → 3.5배
        faith_mult = skill.metadata.get("faith_multiplier", 3.5)
        for effect in skill.effects:
            if isinstance(effect, HealEffect):
                if not hasattr(effect, '_original_multiplier'):
                    effect._original_multiplier = effect.multiplier
                effect.multiplier = faith_mult
                logger.info(f"[신앙 강화] {skill.name} 회복량 강화")
                break

    elif skill_id == "priest_resurrection":
        # 부활: HP 40% → 80% 회복
        for effect in skill.effects:
            if isinstance(effect, HealEffect):
                if not hasattr(effect, '_original_value'):
                    effect._original_value = effect.percentage if hasattr(effect, 'percentage') else getattr(effect, 'value', 0.4)
                effect.percentage = 0.8 if hasattr(effect, 'percentage') else None
                if hasattr(effect, 'value'):
                    effect.value = 0.8
                logger.info(f"[신앙 강화] 부활 회복량 40% → 80%")
                break

    elif skill_id == "priest_sacrifice":
        # 희생의 기도: HP 소모 없음 + 회복량 × 3.5
        skill.metadata['self_damage_percent'] = 0  # HP 소모 제거
        faith_mult = skill.metadata.get("faith_multiplier", 3.5)
        for effect in skill.effects:
            if isinstance(effect, HealEffect):
                if not hasattr(effect, '_original_multiplier'):
                    effect._original_multiplier = effect.multiplier
                effect.multiplier = faith_mult
                logger.info(f"[신앙 강화] 희생의 기도 HP 소모 없음 + 회복 강화")
                break

    elif skill_id == "mass_healing":
        # 대규모 치유: HP 25% → 50% 회복, 방어 +25% (4턴)
        for effect in skill.effects:
            if isinstance(effect, HealEffect):
                if not hasattr(effect, '_original_value'):
                    effect._original_value = getattr(effect, 'percentage', 0.25) if hasattr(effect, 'percentage') else getattr(effect, 'value', 0.25)
                if hasattr(effect, 'percentage'):
                    effect.percentage = 0.5
                if hasattr(effect, 'value'):
                    effect.value = 0.5
                logger.info(f"[신앙 강화] 대규모 치유 회복량 2배")
            elif isinstance(effect, BuffEffect):
                if not hasattr(effect, '_original_value'):
                    effect._original_value = effect.value
                    effect._original_duration = effect.duration
                effect.value = 0.25
                effect.duration = 4
                logger.info(f"[신앙 강화] 대규모 치유 방어 강화")

    elif skill_id == "priest_divine_grace":
        # 신의 은총: 회복량 2배, 재생 2배, 지속시간 6턴
        for effect in skill.effects:
            if isinstance(effect, HealEffect):
                if not hasattr(effect, '_original_multiplier'):
                    effect._original_multiplier = effect.multiplier
                effect.multiplier = effect._original_multiplier * 2.0
                logger.info(f"[신앙 강화] 신의 은총 회복량 2배")
            elif isinstance(effect, BuffEffect):
                if not hasattr(effect, '_original_value'):
                    effect._original_value = effect.value
                    effect._original_duration = effect.duration
                effect.value = effect._original_value * 2.0
                effect.duration = 6
                logger.info(f"[신앙 강화] 신의 은총 재생 강화")

    elif skill_id == "priest_ultimate":
        # 궁극기: 회복량 2배, 신탁 자동 충족 3턴 → 5턴
        for effect in skill.effects:
            if isinstance(effect, HealEffect):
                if not hasattr(effect, '_original_multiplier'):
                    effect._original_multiplier = effect.multiplier
                effect.multiplier = effect._original_multiplier * 2.0
                logger.info(f"[신앙 강화] 궁극기 회복량 2배")
            elif isinstance(effect, BuffEffect) and effect.metadata.get('auto_fulfill_oracle'):
                if not hasattr(effect, '_original_duration'):
                    effect._original_duration = effect.duration
                effect.duration = 5
                logger.info(f"[신앙 강화] 신탁 자동 충족 5턴")

    # 버프 스킬들
    elif skill_id == "priest_blessing":
        # 신의 축복: 공격/방어 +15% → +30%, 3턴 → 5턴
        for effect in skill.effects:
            if isinstance(effect, BuffEffect):
                if not hasattr(effect, '_original_value'):
                    effect._original_value = effect.effects.get('attack_multiplier', 1.15) if hasattr(effect, 'effects') else 1.15
                    effect._original_duration = effect.duration
                if hasattr(effect, 'effects'):
                    effect.effects['attack_multiplier'] = 1.30
                    effect.effects['defense_multiplier'] = 1.30
                effect.duration = 5
                logger.info(f"[신앙 강화] 신의 축복 강화")

    elif skill_id == "priest_purify":
        # 정화의 빛: 디버프 전체 제거 + 방어 +40% (4턴)
        for effect in skill.effects:
            if hasattr(effect, '__class__.__name__') and 'Cleanse' in effect.__class__.__name__:
                if hasattr(effect, 'cleanse_count'):
                    effect.cleanse_count = 999  # 전체 제거
                logger.info(f"[신앙 강화] 정화의 빛 전체 디버프 제거")
            elif isinstance(effect, BuffEffect):
                if not hasattr(effect, '_original_value'):
                    effect._original_value = effect.value
                    effect._original_duration = effect.duration
                effect.value = 0.40
                effect.duration = 4
                logger.info(f"[신앙 강화] 정화의 빛 방어 강화")

    elif skill_id == "priest_martyr":
        # 순교자의 서약: 피해 50% → 70% 감소, 3턴 → 5턴
        for effect in skill.effects:
            if hasattr(effect, 'damage_reduction'):
                if not hasattr(effect, '_original_reduction'):
                    effect._original_reduction = effect.damage_reduction
                    effect._original_duration = effect.duration
                effect.damage_reduction = 0.70
                effect.duration = 5
                logger.info(f"[신앙 강화] 순교자의 서약 피해 감소 강화")

    elif skill_id == "priest_divine_counter":
        # 신성한 응징: 반격률 +100%, 반격 데미지 2배, 4턴
        for effect in skill.effects:
            if isinstance(effect, BuffEffect):
                if not hasattr(effect, '_original_value'):
                    effect._original_duration = effect.duration
                if hasattr(effect, 'effects'):
                    effect.effects['counter_rate_bonus'] = 1.0
                    effect.effects['counter_damage_multiplier'] = 2.0
                effect.duration = 4
                logger.info(f"[신앙 강화] 신성한 응징 강화")

    elif skill_id == "priest_divine_protection":
        # 신성 보호: 방어 +25% → +80%, 4턴 → 6턴
        for effect in skill.effects:
            if isinstance(effect, BuffEffect):
                if not hasattr(effect, '_original_value'):
                    effect._original_value = effect.value
                    effect._original_duration = effect.duration
                effect.value = 0.80
                effect.duration = 6
                logger.info(f"[신앙 강화] 신성 보호 강화")

    # 공격 스킬들
    elif skill_id == "priest_holy_smite":
        # 성스러운 일격: BRV 데미지 × 2.5
        for effect in skill.effects:
            if isinstance(effect, DamageEffect):
                if not hasattr(effect, '_original_multiplier'):
                    effect._original_multiplier = effect.multiplier
                effect.multiplier = effect._original_multiplier * 2.5
                logger.info(f"[신앙 강화] 성스러운 일격 데미지 2.5배")
                break

    elif skill_id == "priest_divine_judgment":
        # 신성 심판: HP 데미지 × 2.5
        for effect in skill.effects:
            if isinstance(effect, DamageEffect):
                if not hasattr(effect, '_original_multiplier'):
                    effect._original_multiplier = effect.multiplier
                effect.multiplier = effect._original_multiplier * 2.5
                logger.info(f"[신앙 강화] 신성 심판 데미지 2.5배")
                break

    elif skill_id == "priest_light_bind":
        # 빛의 속박: BRV 데미지 × 2, 속도 감소 -60%, 4턴
        for effect in skill.effects:
            if isinstance(effect, DamageEffect):
                if not hasattr(effect, '_original_multiplier'):
                    effect._original_multiplier = effect.multiplier
                effect.multiplier = effect._original_multiplier * 2.0
                logger.info(f"[신앙 강화] 빛의 속박 데미지 2배")
            elif isinstance(effect, BuffEffect):
                if not hasattr(effect, '_original_value'):
                    effect._original_value = effect.value
                    effect._original_duration = effect.duration
                effect.value = 0.60
                effect.duration = 4
                logger.info(f"[신앙 강화] 빛의 속박 CC 강화")

    elif skill_id == "priest_judgment_light":
        # 심판의 빛: 데미지 × 2
        for effect in skill.effects:
            if isinstance(effect, DamageEffect):
                if not hasattr(effect, '_original_multiplier'):
                    effect._original_multiplier = effect.multiplier
                effect.multiplier = effect._original_multiplier * 2.0
                logger.info(f"[신앙 강화] 심판의 빛 데미지 2배")

    elif skill_id == "priest_holy_beam":
        # 신성 광선: 데미지 × 2 + 신앙 소모 없음
        for effect in skill.effects:
            if isinstance(effect, DamageEffect):
                if not hasattr(effect, '_original_multiplier'):
                    effect._original_multiplier = effect.multiplier
                effect.multiplier = effect._original_multiplier * 2.0
                logger.info(f"[신앙 강화] 신성 광선 데미지 2배 + 신앙 소모 면제")
        # 신앙 소모 효과 무효화
        skill.effects = [e for e in skill.effects if not (hasattr(e, 'operation') and e.operation.name == 'CONSUME')]

    elif skill_id == "priest_divine_wrath":
        # 신의 분노: 데미지 × 2 + 신앙 소모 없음
        for effect in skill.effects:
            if isinstance(effect, DamageEffect):
                if not hasattr(effect, '_original_multiplier'):
                    effect._original_multiplier = effect.multiplier
                effect.multiplier = effect._original_multiplier * 2.0
                logger.info(f"[신앙 강화] 신의 분노 데미지 2배 + 신앙 소모 면제")
        # 신앙 소모 효과 무효화
        skill.effects = [e for e in skill.effects if not (hasattr(e, 'operation') and e.operation.name == 'CONSUME')]


def _apply_oath_metadata_bonus(user, skill):
    """스킬 메타데이터에 명시된 신앙 보너스 적용 (oath_*_faith)"""
    if getattr(user, "gimmick_type", None) != "oath_system":
        return
    meta = getattr(skill, "metadata", {}) or {}
    oaths = getattr(user, "oaths", {})
    current_oath = getattr(user, "current_oath", None)
    for oath_id in oaths.keys():
        key = f"oath_{oath_id}_faith"
        if key in meta and (current_oath == oath_id):
            gain = meta.get(key, 0)
            if gain:
                GimmickUpdater.add_faith(user, gain, "metadata")


def _handle_skill_execute(event):
    """SKILL_EXECUTE 이벤트 핸들러"""
    if not event:
        return
    skill = event.get("skill")
    user = event.get("user")
    result = event.get("result")
    if not skill or not user or not result or not getattr(result, "success", False):
        return

    action_type = _classify_action_from_skill(skill)

    gimmick_type = getattr(user, "gimmick_type", None)
    if gimmick_type == "mp_overload_system":
        # 무당: 과부하/토글 처리
        _mp_overload_on_skill(user, skill)
        # 처리 플래그 해제 (다음 스킬에서 다시 처리할 수 있도록)
        skill.metadata.pop("_overload_processed", None)

    # 성기사: 서약/신앙 처리
    elif gimmick_type == "oath_system":
        GimmickUpdater.check_oath_violation(user, action_type)
        current_oath = getattr(user, "current_oath", None)
        oaths = getattr(user, "oaths", {})
        oath_data = oaths.get(current_oath, {})
        reward_actions = oath_data.get("reward_actions", [])
        reward_action = oath_data.get("reward_action")
        is_reward = action_type in reward_actions or (reward_action and action_type == reward_action)
        if is_reward:
            gain = _get_faith_reward(oath_data, action_type)
            if gain > 0:
                GimmickUpdater.add_faith(user, gain, action_type)
        _apply_oath_metadata_bonus(user, skill)

    # 검투사: 관중 요구 처리 (행동/공격)
    if getattr(user, "gimmick_type", None) == "crowd_cheer":
        context = {"target_id": id(event.get("target")) if event.get("target") else None}
        GimmickUpdater.check_demand_fulfillment(user, "action", context)
        if action_type == "attack":
            GimmickUpdater.check_demand_fulfillment(user, "attack", context)

    # 해커: 침투/RAM/오버클럭 처리
    if getattr(user, "gimmick_type", None) == "intrusion_system":
        meta = getattr(skill, "metadata", {}) or {}
        # 침투량 추가
        gain = meta.get("intrusion_gain", 0)
        gain_all = meta.get("intrusion_gain_all", 0)
        targets = event.get("target")
        targets = targets if isinstance(targets, list) else [targets] if targets else []
        if gain_all and targets:
            for t in targets:
                GimmickUpdater.add_intrusion(user, t, gain_all)
        elif gain and targets:
            for t in targets:
                GimmickUpdater.add_intrusion(user, t, gain)

        # 오버클럭 토글
        if meta.get("overclock_toggle"):
            turning_off = getattr(user, "overclock_active", False)
            user.overclock_active = not turning_off
            if turning_off and hasattr(user, "status_manager"):
                try:
                    user.status_manager.remove_buff("overclock")
                except Exception:
                    pass
        elif meta.get("overclock"):
            user.overclock_active = True
        if meta.get("disable_overclock"):
            user.overclock_active = False
            if hasattr(user, "status_manager"):
                try:
                    user.status_manager.remove_buff("overclock")
                except Exception:
                    pass

    # 신관: 신탁 액션 충족
    if getattr(user, "gimmick_type", None) == "oracle_system":
        meta = getattr(skill, "metadata", {}) or {}
        oracle_action = meta.get("oracle_action")
        oracle_action = oracle_action or action_type
        if oracle_action:
            GimmickUpdater.check_oracle_fulfillment(user, oracle_action)

    # 도적: 농락 게이지
    if getattr(user, "gimmick_type", None) == "mockery_system":
        GimmickUpdater._update_mockery_system(user)
        
        meta = getattr(skill, "metadata", {}) or {}
        gain = meta.get("mockery_gain", 0)
        gain_all = meta.get("mockery_gain_all", 0)
        targets = event.get("target")
        targets = targets if isinstance(targets, list) else [targets] if targets else []
        if gain_all and targets:
            for t in targets:
                GimmickUpdater.add_mockery(user, t, gain_all)
        elif gain and targets:
            for t in targets:
                GimmickUpdater.add_mockery(user, t, gain)

    # 차원술사 굴절 업데이트는 _handle_combat_action에서 처리 (중복 방지)
    # SKILL_EXECUTE는 스킬 사용 시에만 발동되므로, COMBAT_ACTION에서 처리하는 것이 적절


def _handle_combat_hit(event):
    """COMBAT_HIT 이벤트 핸들러 - 크리/광역/큰 피해"""
    if not event:
        return
    attacker = event.get("attacker")
    if getattr(attacker, "gimmick_type", None) != "crowd_cheer":
        return

    # 크리티컬 요구
    if event.get("is_critical"):
        GimmickUpdater.check_demand_fulfillment(attacker, "critical", {})

    # 광역 3명 이상 히트
    targets_hit = event.get("targets_hit", 1)
    if targets_hit >= 3:
        GimmickUpdater.check_demand_fulfillment(attacker, "hit", {"targets_hit": targets_hit})

    # 단일 큰 피해 (HP 30% 이상)
    hp_percent = event.get("hp_percent_of_target", 0)
    if hp_percent >= 30:
        GimmickUpdater.check_demand_fulfillment(attacker, "hp_damage", {"hp_percent": hp_percent})


def _handle_combat_action(event):
    """COMBAT_ACTION 이벤트 핸들러 - 행동 카운트 & 차원 굴절"""
    print(f"[DEBUG] _handle_combat_action 호출됨!")  # 핸들러 호출 확인용
    if not event:
        return
    actor = event.get("actor")
    
    # 검투사: 행동 요구
    if getattr(actor, "gimmick_type", None) == "crowd_cheer":
        GimmickUpdater.check_demand_fulfillment(actor, "action", {})
    
    # === ISSUE-16: 차원술사 굴절 업데이트 (모든 행동마다 발동) ===
    # 현재 전투에 참여 중인 모든 차원술사의 굴절 업데이트
    combat_manager = getattr(actor, "_combat_manager_ref", None) if actor else None
    if not combat_manager and actor and hasattr(actor, "combat_manager"):
        combat_manager = actor.combat_manager
         
    if not combat_manager:
        try:
            from src.combat.combat_manager import get_combat_manager
            combat_manager = get_combat_manager()
        except Exception as e:
            logger.warning(f"[COMBAT_ACTION] get_combat_manager 실패: {e}")

    if combat_manager and hasattr(combat_manager, "allies"):
        # 디버그: allies 상태 출력
        allies_count = len(combat_manager.allies) if combat_manager.allies else 0
        print(f"[DEBUG] allies 수: {allies_count}")
        for i, ally in enumerate(combat_manager.allies):
            ally_name = getattr(ally, 'name', 'Unknown')
            ally_gimmick = getattr(ally, 'gimmick_type', None)
            ally_refraction = getattr(ally, 'refraction_stacks', 0)
            print(f"[DEBUG] ally[{i}]: {ally_name}, gimmick={ally_gimmick}, refraction={ally_refraction}")
        
        # 아군 중 차원술사 찾기
        dimensionists_found = 0
        for ally in combat_manager.allies:
            if getattr(ally, "gimmick_type", None) == "dimension_refraction" and getattr(ally, "is_alive", True):
                dimensionists_found += 1
                refraction_before = getattr(ally, 'refraction_stacks', 0)
                if refraction_before > 0:
                    GimmickUpdater._update_dimension_refraction(ally)
                    refraction_after = getattr(ally, 'refraction_stacks', 0)
                    logger.info(f"[차원 굴절] {ally.name} 굴절 감소: {refraction_before} → {refraction_after} (행동자: {getattr(actor, 'name', '?')})")
        
        print(f"[DEBUG] 차원술사 발견: {dimensionists_found}명")
        # 차원술사가 없으면 로그 생략 (너무 많은 로그 방지)
    else:
        logger.warning(f"[COMBAT_ACTION] combat_manager 없음: actor={getattr(actor, 'name', 'None')}")



def _handle_damage_taken(event):
    """COMBAT_DAMAGE_TAKEN 이벤트 핸들러 - 서약/요구"""
    if not event:
        return
    target = event.get("character")
    if not target:
        return

    # 성기사: 인내 서약 보상 (피격)
    if getattr(target, "gimmick_type", None) == "oath_system":
        current_oath = getattr(target, "current_oath", None)
        oaths = getattr(target, "oaths", {})
        oath_data = oaths.get(current_oath, {})
        reward_actions = oath_data.get("reward_actions", [])
        reward_action = oath_data.get("reward_action")
        is_reward = "take_damage" in reward_actions or reward_action == "take_damage"
        if is_reward:
            gain = _get_faith_reward(oath_data, "take_damage")
            if gain > 0:
                GimmickUpdater.add_faith(target, gain, "take_damage")

    # 검투사: 피격 요구
    if getattr(target, "gimmick_type", None) == "crowd_cheer":
        GimmickUpdater.check_demand_fulfillment(target, "hit_taken", {})


def _handle_character_death(event):
    """CHARACTER_DEATH 이벤트 핸들러 - 처치/신앙 보상"""
    if not event:
        return
    attacker = event.get("attacker")
    victim = event.get("character")
    if not attacker or not victim:
        return

    # 검투사: 처치 요구
    if getattr(attacker, "gimmick_type", None) == "crowd_cheer":
        GimmickUpdater.check_demand_fulfillment(attacker, "kill", {"target_id": id(victim)})

    # 성기사: 순결 서약 처치 보상
    if getattr(attacker, "gimmick_type", None) == "oath_system":
        current_oath = getattr(attacker, "current_oath", None)
        oaths = getattr(attacker, "oaths", {})
        oath_data = oaths.get(current_oath, {})
        reward_actions = oath_data.get("reward_actions", [])
        reward_action = oath_data.get("reward_action")
        is_reward = "kill" in reward_actions or reward_action == "kill"
        if is_reward:
            gain = _get_faith_reward(oath_data, "kill")
            if gain > 0:
                GimmickUpdater.add_faith(attacker, gain, "kill")

# =======================
# MP 과부하 시스템 (무당)
# =======================
def _mp_overload_on_skill(character, skill):
    """스킬 사용 시 과부하/토글 처리"""
    # 중복 처리 방지 (SKILL_EXECUTE + on_skill_use 양쪽 호출)
    if skill.metadata.get("_overload_processed"):
        return
    skill.metadata["_overload_processed"] = True

    # 플레이어 선택(또는 기본값) 과부하 여부
    use_overload = skill.metadata.get("_use_overload", None)
    if use_overload is None:
        use_overload = skill.metadata.get("overload_default", False)

    # 토글 스킬 처리 (ON/OFF 토글)
    if skill.metadata.get("toggle"):
        toggle_id = skill.skill_id
        max_mp_penalty = skill.metadata.get("max_mp_penalty", 0.0)
        if not hasattr(character, "active_toggles"):
            character.active_toggles = []
        if toggle_id in character.active_toggles:
            # 해제
            character.active_toggles.remove(toggle_id)
            penalty = int(character.max_mp * max_mp_penalty)
            character.reserved_max_mp = max(0, getattr(character, "reserved_max_mp", 0) - penalty)
            logger.info(f"[토글 해제] {character.name} {toggle_id} 비활성화 (예약 MP 해제)")
        else:
            # 활성
            character.active_toggles.append(toggle_id)
            reserve = int(character.max_mp * max_mp_penalty)
            character.reserved_max_mp = min(character.max_mp, getattr(character, "reserved_max_mp", 0) + reserve)
            if hasattr(character, "current_mp"):
                character.current_mp = min(character.current_mp, character.effective_max_mp())
            logger.info(f"[토글 활성] {character.name} {toggle_id} 활성화 (예약 MP {reserve})")

    # 모든 토글 해제 효과
    if skill.metadata.get("toggle_release_all"):
        if hasattr(character, "active_toggles"):
            character.active_toggles.clear()
        character.reserved_max_mp = 0
        if hasattr(character, "current_mp"):
            character.current_mp = min(character.current_mp, character.effective_max_mp())
        logger.info(f"[과부하] {character.name} 모든 토글 해제 및 예약 MP 초기화")

    # 과부하 미사용이면 여기서 종료 (토글만 처리)
    if not (skill.metadata.get("overload_capable") and use_overload):
        if skill.metadata.get("overload_capable"):
            logger.debug(f"[과부하] {character.name} 과부하 미사용 선택 - 게이지 증가 없음")
        return

    # 과부하 게이지 증가
    gain = skill.metadata.get("overload_gain", 1)
    if not hasattr(character, "overload_gauge"):
        character.overload_gauge = 0
    character.overload_gauge = min(getattr(character, "max_overload_gauge", 5), character.overload_gauge + gain)
    logger.debug(f"[과부하] {character.name} 과부하 게이지 +{gain} → {character.overload_gauge}")
    GimmickUpdater._update_mp_overload_state(character)

class GimmickStateChecker:
    """기믹 상태 체크 (조건부 보너스 등)"""

# 전역 이벤트 핸들러 등록
event_bus.subscribe(Events.SKILL_EXECUTE, _handle_skill_execute)
event_bus.subscribe(Events.COMBAT_HIT, _handle_combat_hit)
event_bus.subscribe(Events.COMBAT_ACTION, _handle_combat_action)
event_bus.subscribe(Events.COMBAT_DAMAGE_TAKEN, _handle_damage_taken)
event_bus.subscribe(Events.CHARACTER_DEATH, _handle_character_death)
