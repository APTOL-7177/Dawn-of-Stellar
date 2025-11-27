"""Gimmick Updater - 기믹 자동 업데이트 시스템"""
from src.core.logger import get_logger

logger = get_logger("gimmick")

class GimmickUpdater:
    """기믹 자동 업데이트 관리자"""

    @staticmethod
    def on_turn_end(character):
        """턴 종료 시 기믹 업데이트"""
        gimmick_type = getattr(character, 'gimmick_type', None)
        if not gimmick_type:
            return

        # 기존 구현된 기믹들
        if gimmick_type == "heat_management":
            GimmickUpdater._update_heat_management(character)
        elif gimmick_type == "timeline_system":
            GimmickUpdater._update_timeline_system(character)
        elif gimmick_type == "yin_yang_flow":
            GimmickUpdater._update_yin_yang_flow(character)
        elif gimmick_type == "madness_threshold":
            GimmickUpdater._update_madness_threshold(character)
        elif gimmick_type == "thirst_gauge":
            GimmickUpdater._update_thirst_gauge(character)
        elif gimmick_type == "probability_distortion":
            GimmickUpdater._update_probability_distortion(character)
        elif gimmick_type == "stealth_exposure":
            GimmickUpdater._update_stealth_exposure(character)
        # ISSUE-004: 신규 추가 기믹들
        elif gimmick_type == "sword_aura":
            GimmickUpdater._update_sword_aura(character)
        elif gimmick_type == "crowd_cheer":
            GimmickUpdater._update_crowd_cheer(character)
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

    @staticmethod
    def on_turn_start(character, context=None):
        """턴 시작 시 기믹 업데이트
        
        Args:
            character: 캐릭터
            context: 컨텍스트 (enemies, combat_manager 등)
        """
        gimmick_type = getattr(character, 'gimmick_type', None)
        if not gimmick_type:
            return

        # 확률 왜곡 게이지 - 턴 시작 시 +10
        if gimmick_type == "probability_distortion":
            gauge_gain = getattr(character, 'gauge_per_turn', 10)
            character.distortion_gauge = min(character.max_gauge, character.distortion_gauge + gauge_gain)
            logger.debug(f"{character.name} 확률 왜곡 게이지 +{gauge_gain} (총: {character.distortion_gauge})")

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

        # 암흑기사 - 충전 시스템 턴 시작
        elif gimmick_type == "charge_system":
            GimmickUpdater._update_charge_system_turn_start(character)
        
        # 마술사 - 트릭 덱 시스템 턴 시작
        elif gimmick_type == "trick_deck":
            GimmickUpdater._update_trick_deck_turn_start(character)

        # 일반 특성 처리 (기믹과 무관한 특성들)
        GimmickUpdater._process_turn_start_traits(character, context)

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
    def on_skill_use(character, skill):
        """스킬 사용 시 기믹 업데이트"""
        gimmick_type = getattr(character, 'gimmick_type', None)
        if not gimmick_type:
            return

        if gimmick_type == "magazine_system":
            GimmickUpdater._consume_bullet(character, skill)
        elif gimmick_type == "stealth_exposure":
            # 공격 스킬 사용 시 은신 해제 체크
            if skill.metadata.get("breaks_stealth", False):
                character.stealth_active = False
                character.exposed_turns = 0
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

    @staticmethod
    def on_ally_attack(attacker, all_allies, target=None):
        """아군 공격 시 기믹 트리거 (지원사격 등)"""
        # 모든 아군 중에서 궁수 찾기
        for ally in all_allies:
            if not hasattr(ally, 'gimmick_type'):
                continue

            if ally.gimmick_type == "support_fire" and ally != attacker:
                GimmickUpdater._trigger_support_fire(ally, attacker, target)

    @staticmethod
    def _trigger_support_fire(archer, attacking_ally, target=None):
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

                        # 폭발 화살: 광역 데미지 처리
                        if arrow_type == 'explosive':
                            # combat_manager에서 적 리스트 가져오기
                            from src.combat.combat_manager import get_combat_manager
                            combat_manager = get_combat_manager()
                            
                            if combat_manager and hasattr(combat_manager, 'enemies'):
                                enemies = combat_manager.enemies
                                aoe_percent = 0.5  # 광역 데미지 50%
                                
                                # 메인 타겟에게 100% 데미지
                                damage_result = damage_calc.calculate_brv_damage(archer, target, skill_multiplier=multiplier)
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
                                damage_result = damage_calc.calculate_brv_damage(archer, target, skill_multiplier=multiplier)
                                brv_damage = damage_result.final_damage
                                
                                from src.combat.brave_system import get_brave_system
                                brave_system = get_brave_system()
                                brv_result = brave_system.brv_attack(archer, target, brv_damage)
                                
                                logger.info(f"  → {target.name}에게 {brv_result['brv_stolen']} BRV 데미지! {archer.name} BRV +{brv_result['actual_gain']}")
                                if brv_result['is_break']:
                                    logger.info(f"  → [BREAK!] {target.name} BRV 파괴!")
                        else:
                            # 일반 화살: 단일 타겟 데미지
                            damage_result = damage_calc.calculate_brv_damage(archer, target, skill_multiplier=multiplier)
                            brv_damage = damage_result.final_damage

                            # brave_system을 사용하여 BRV 공격 적용 (BREAK 체크 포함)
                            from src.combat.brave_system import get_brave_system
                            brave_system = get_brave_system()
                            brv_result = brave_system.brv_attack(archer, target, brv_damage)

                            logger.info(f"  → {target.name}에게 {brv_result['brv_stolen']} BRV 데미지! {archer.name} BRV +{brv_result['actual_gain']}")
                            if brv_result['is_break']:
                                logger.info(f"  → [BREAK!] {target.name} BRV 파괴!")

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
        """오버히트 체크 (기계공학자)"""
        if character.gimmick_type != "heat_management":
            return False

        if character.heat >= character.overheat_threshold:
            logger.info(f"{character.name} 오버히트 발동!")
            character.is_overheated = True
            character.overheat_stun_turns = 2
            character.heat = 0  # 열 리셋
            return True

        # 오버히트 방지 특성
        if character.heat >= 95 and character.overheat_prevention_count > 0:
            logger.info(f"{character.name} 오버히트 방지 발동! (-15 열)")
            character.heat -= 15
            character.overheat_prevention_count -= 1

        return False

    # === 기믹별 업데이트 로직 ===

    @staticmethod
    def _update_heat_management(character):
        """기계공학자: 열 관리 시스템 업데이트"""
        # 자동 냉각 특성 (매 턴 -5)
        if hasattr(character, 'active_traits'):
            if any((t if isinstance(t, str) else t.get('id')) == 'auto_cooling' for t in character.active_traits):
                character.heat = max(0, character.heat - 5)
                logger.debug(f"{character.name} 자동 냉각: 열 -5")

        # 최적 구간에서 자동 열 증가
        if character.optimal_min <= character.heat < character.optimal_max:
            character.heat = min(character.max_heat, character.heat + 5)
            logger.debug(f"{character.name} 최적 구간 유지: 열 +5")

        # 위험 구간에서 자동 열 증가 (더 빠름)
        elif character.danger_min <= character.heat < character.danger_max:
            character.heat = min(character.max_heat, character.heat + 10)
            logger.debug(f"{character.name} 위험 구간 유지: 열 +10")

        # 오버히트 체크
        GimmickUpdater.check_overheat(character)

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
    def _update_madness_threshold(character):
        """버서커: 광기 임계치 시스템 업데이트
        
        기본 효과 (특성 불필요):
        - 광기 30-70 (최적): 공격력 +40%, 속도 +20%
        - 광기 71-99 (위험): 공격력 +80%, 속도 +40%, 크리티컬 +20%, 받는 피해 +30%
        - 광기 100 (폭주): 공격력 +150%, 통제 불가, 무작위 공격
        """
        from src.character.stat_manager import Stats
        
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
        
        if character.madness < effective_optimal_min:
            # 최적 구간 미만: 자연 감소
            character.madness = max(0, character.madness - actual_decay)
            logger.debug(f"{character.name} 광기 자연 감소: -{actual_decay} (총: {character.madness})")
        elif character.madness >= effective_danger_min:
            # 위험 구간: 자연 증가
            character.madness = min(character.max_madness, character.madness + 10)
            logger.warning(f"{character.name} 광기 위험 증가: +10 (총: {character.madness})")
        
        # === 기본 효과 적용 (특성 불필요) ===
        madness = character.madness
        base_attack = character.stat_manager.get_base_value(Stats.STRENGTH)
        base_speed = character.stat_manager.get_base_value(Stats.SPEED)
        
        # 폭주 상태 (광기 100) - 통제 가능하지만 대가가 큼
        if madness >= character.rampage_threshold:
            character.stat_manager.add_bonus(Stats.STRENGTH, "madness_bonus", base_attack * 1.50)
            # 폭주 상태에서는 속도 보너스 없음 (공격력 +150%, 크리티컬 +30%만 적용)
            character._is_rampaging = True
            character._rampage_turns = getattr(character, '_rampage_turns', 0) + 1
            character._madness_zone = "rampage"
            character._madness_crit_bonus = 0.30  # 크리티컬 +30%
            character._madness_damage_taken_mult = 1.50  # 받는 피해 +50%
            
            # 매턴 HP 10% 감소 (폭주의 대가)
            hp_loss = int(character.max_hp * 0.10)
            character.current_hp = max(1, character.current_hp - hp_loss)
            logger.critical(f"{character.name} 폭주 상태! 공격력 +150%, 받는 피해 +50%, HP -{hp_loss} (잔여: {character.current_hp})")
            
        # 위험 구간 (effective_danger_min ~ 99)
        elif madness >= effective_danger_min:
            character.stat_manager.add_bonus(Stats.STRENGTH, "madness_bonus", base_attack * 0.80)
            character.stat_manager.add_bonus(Stats.SPEED, "madness_bonus", base_speed * 0.40)
            character._is_rampaging = False
            character._madness_zone = "danger"
            character._madness_crit_bonus = 0.20  # 크리티컬 +20%
            character._madness_damage_taken_mult = 1.30  # 받는 피해 +30%
            
            # 매턴 HP 5% 감소 (위험의 대가)
            hp_loss = int(character.max_hp * 0.05)
            character.current_hp = max(1, character.current_hp - hp_loss)
            logger.warning(f"{character.name} 위험 구간! 공격력 +80%, 받는 피해 +30%, HP -{hp_loss} (잔여: {character.current_hp})")
            
        # 최적 구간 (effective_optimal_min ~ effective_optimal_max)
        elif madness >= effective_optimal_min:
            character.stat_manager.add_bonus(Stats.STRENGTH, "madness_bonus", base_attack * 0.40)
            character.stat_manager.add_bonus(Stats.SPEED, "madness_bonus", base_speed * 0.20)
            character._is_rampaging = False
            character._madness_zone = "optimal"
            character._madness_crit_bonus = 0
            character._madness_damage_taken_mult = 1.0
            logger.info(f"{character.name} 최적 구간! 공격력 +40%, 속도 +20%")
            
        # 안전 구간 (0 ~ effective_optimal_min-1)
        else:
            character._is_rampaging = False
            character._madness_zone = "safe"
            character._madness_crit_bonus = 0
            character._madness_damage_taken_mult = 1.0
            logger.debug(f"{character.name} 안전 구간. 보너스 없음.")

    @staticmethod
    def _update_thirst_gauge(character):
        """뱀파이어: 갈증 게이지 시스템 업데이트"""
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
    def _update_stealth_exposure(character):
        """암살자: 은신-노출 딜레마 시스템 업데이트"""
        # 노출 상태에서 턴 경과 체크
        if not character.stealth_active:
            character.exposed_turns += 1
            logger.debug(f"{character.name} 노출 턴 경과: {character.exposed_turns}/{character.restealth_cooldown}")

            # 3턴 경과 시 재은신 가능 (자동 전환은 하지 않음, 스킬로만 가능)
            if character.exposed_turns >= character.restealth_cooldown:
                logger.info(f"{character.name} 재은신 가능!")

    @staticmethod
    def _consume_bullet(character, skill):
        """저격수: 탄환 소비"""
        if not hasattr(character, 'magazine'):
            return

        bullets_used = skill.metadata.get('bullets_used', 0)
        uses_magazine = skill.metadata.get('uses_magazine', False)

        if not uses_magazine or bullets_used == 0:
            return

        # 탄환 절약 특성 체크
        if hasattr(character, 'active_traits'):
            if any((t if isinstance(t, str) else t.get('id')) == 'bullet_conservation' for t in character.active_traits):
                import random
                if random.random() < 0.3:  # 30% 확률로 탄환 소모 안 함
                    logger.info(f"{character.name} 탄환 절약 발동!")
                    return

        # 탄환 소비
        for _ in range(bullets_used):
            if len(character.magazine) > 0:
                used_bullet = character.magazine.pop(0)
                logger.debug(f"{character.name} 탄환 발사: {used_bullet}")

        # 탄창이 비었으면 권총 모드로 전환
        if len(character.magazine) == 0:
            logger.warning(f"{character.name} 탄창 비움! 권총 모드")


    # === ISSUE-004: 신규 기믹 업데이트 로직 (1/3) ===

    @staticmethod
    def _update_sword_aura(character):
        """검성: 검기 시스템 업데이트"""
        # 검기는 공격 시 자동 획득하므로 자동 증가 없음 (YAML 기준 max=5)
        # 최대값 제한만 체크
        sword_aura = getattr(character, 'sword_aura', 0)
        max_aura = getattr(character, 'max_sword_aura', 5)
        if sword_aura > max_aura:
            character.sword_aura = max_aura

    @staticmethod
    def _update_crowd_cheer(character):
        """검투사: 군중 환호 시스템 업데이트"""
        # 환호 자연 감소 (매 턴 -10)
        cheer = getattr(character, 'cheer', 0)
        character.cheer = max(0, cheer - 10)
        logger.debug(f"{character.name} 환호 자연 감소: -10 (총: {character.cheer})")

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
        
        # 수호자: HP/MP 재생
        elif stance == 5:  # guardian
            if hasattr(character, 'max_hp') and hasattr(character, 'max_mp'):
                hp_regen = int(character.max_hp * 0.08)  # 최대 HP의 8%
                mp_regen = int(character.max_mp * 0.10)  # 최대 MP의 10%
                old_hp = character.current_hp
                old_mp = character.current_mp
                character.current_hp = min(character.max_hp, character.current_hp + hp_regen)
                character.current_mp = min(character.max_mp, character.current_mp + mp_regen)
                actual_hp = character.current_hp - old_hp
                actual_mp = character.current_mp - old_mp
                if actual_hp > 0 or actual_mp > 0:
                    logger.info(f"{character.name} 수호자 자세: HP +{actual_hp}, MP +{actual_mp}")
    
    @staticmethod
    def _apply_stance_effects(character):
        """전사: 스탠스 효과를 StatManager에 적용"""
        if not hasattr(character, 'stat_manager'):
            return
        
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
            # 모든 스탯 15% 감소
            base_attack = character.stat_manager.get_value(Stats.STRENGTH)
            base_defense = character.stat_manager.get_value(Stats.DEFENSE)
            base_magic = character.stat_manager.get_value(Stats.MAGIC)
            base_magic_def = character.stat_manager.get_value(Stats.SPIRIT)
            base_speed = character.stat_manager.get_value(Stats.SPEED)
            
            character.stat_manager.add_bonus(Stats.STRENGTH, "stance", -base_attack * 0.15)
            character.stat_manager.add_bonus(Stats.DEFENSE, "stance", -base_defense * 0.15)
            character.stat_manager.add_bonus(Stats.MAGIC, "stance", -base_magic * 0.15)
            character.stat_manager.add_bonus(Stats.SPIRIT, "stance", -base_magic_def * 0.15)
            character.stat_manager.add_bonus(Stats.SPEED, "stance", -base_speed * 0.15)
        
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
        """정령술사: 정령 소환 시스템 업데이트"""
        # 정령은 스킬로만 소환/해제, 자동 업데이트 없음
        pass

    @staticmethod
    def _update_plunder_system(character):
        """해적: 약탈 시스템 업데이트"""
        # 약탈한 골드는 스킬로만 획득, 자동 업데이트 없음
        pass

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
    def _update_dilemma_choice(character):
        """철학자: 딜레마 선택 시스템 업데이트"""
        # 선택 값은 스킬로만 변경, 자동 업데이트 없음
        pass

    @staticmethod
    def _update_rune_resonance(character):
        """룬마스터: 룬 공명 시스템 업데이트"""
        # 룬은 스킬로만 축적, 자동 업데이트 없음
        pass

    @staticmethod
    def _update_dimension_refraction(character):
        """차원술사: 차원 굴절 시스템 업데이트"""
        refraction = getattr(character, 'refraction_stacks', 0)

        if refraction <= 0:
            return

        # 매턴 감소율 (기본 35%)
        decay_rate = getattr(character, 'turn_decay_rate', 0.35)

        # 차원 안정화 특성 확인 (감소율 35% → 25%)
        if hasattr(character, 'active_traits'):
            if any((t if isinstance(t, str) else t.get('id')) == 'dimensional_stabilization'
                   for t in character.active_traits):
                decay_rate = 0.25
                logger.debug(f"[차원 안정화] {character.name} 굴절 감소율: 25%")

        # 이중 차원 특성 확인 (굴절 피해 +75%)
        decay_damage_mult = 1.0
        if hasattr(character, 'active_traits'):
            if any((t if isinstance(t, str) else t.get('id')) == 'double_refraction'
                   for t in character.active_traits):
                decay_damage_mult = 1.75
                logger.debug(f"[이중 차원] {character.name} 굴절 피해 배율: 1.75배")

        # 감소량 계산
        decay_amount = int(refraction * decay_rate)

        if decay_amount <= 0:
            return

        # 굴절량 감소
        character.refraction_stacks = max(0, refraction - decay_amount)

        # 감소량만큼 고정 HP 피해
        decay_damage = int(decay_amount * decay_damage_mult)

        # 고정 피해 적용 (take_fixed_damage 메서드 사용)
        if hasattr(character, 'take_fixed_damage'):
            actual_damage = character.take_fixed_damage(decay_damage)
        else:
            # 메서드가 없으면 직접 HP 감소
            actual_damage = min(decay_damage, character.current_hp)
            character.current_hp = max(0, character.current_hp - decay_damage)

        logger.warning(
            f"[차원 굴절] {character.name} 지연 피해: {actual_damage} HP "
            f"(굴절량 {refraction} → {character.refraction_stacks}, 감소율 {int(decay_rate*100)}%)"
        )

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


class GimmickStateChecker:
    """기믹 상태 체크 (조건부 보너스 등)"""

    @staticmethod
    def is_in_optimal_zone(character) -> bool:
        """최적 구간인지 체크"""
        if character.gimmick_type == "heat_management":
            return character.optimal_min <= character.heat < character.optimal_max
        elif character.gimmick_type == "timeline_system":
            return character.timeline == character.optimal_point
        elif character.gimmick_type == "yin_yang_flow":
            return 40 <= getattr(character, 'ki_gauge', 50) <= 60
        return False

    @staticmethod
    def is_in_danger_zone(character) -> bool:
        """위험 구간인지 체크"""
        if character.gimmick_type == "heat_management":
            return character.danger_min <= character.heat < character.danger_max
        elif character.gimmick_type == "madness_threshold":
            return character.madness >= character.danger_min
        elif character.gimmick_type == "thirst_gauge":
            return character.thirst >= character.starving_min
        return False

    @staticmethod
    def is_last_bullet(character) -> bool:
        """마지막 탄환인지 체크 (저격수)"""
        if character.gimmick_type == "magazine_system":
            return len(getattr(character, 'magazine', [])) == 1
        return False

    @staticmethod
    def is_at_present(character) -> bool:
        """현재(0) 타임라인인지 체크 (시간술사)"""
        if character.gimmick_type == "timeline_system":
            return getattr(character, 'timeline', 0) == 0
        return False

    @staticmethod
    def get_active_spirits_count(character) -> int:
        """활성화된 정령 수 반환 (정령술사)"""
        if character.gimmick_type == "elemental_spirits":
            return sum([
                getattr(character, 'spirit_fire', 0),
                getattr(character, 'spirit_water', 0),
                getattr(character, 'spirit_wind', 0),
                getattr(character, 'spirit_earth', 0)
            ])
        return 0

    @staticmethod
    def get_rune_resonance_bonus(character) -> float:
        """룬 공명 보너스 반환 (배틀메이지)"""
        if character.gimmick_type == "rune_resonance":
            fire = getattr(character, 'rune_fire', 0)
            ice = getattr(character, 'rune_ice', 0)
            lightning = getattr(character, 'rune_lightning', 0)

            # 3개 동일 룬 = 공명 보너스 +50%
            if fire == 3 or ice == 3 or lightning == 3:
                return 0.5
        return 0.0

    @staticmethod
    def is_in_stealth(character) -> bool:
        """은신 상태인지 체크 (암살자)"""
        if character.gimmick_type == "stealth_exposure":
            return getattr(character, 'stealth_active', False)
        return False

    @staticmethod
    def get_support_fire_combo(character) -> int:
        """지원사격 콤보 수 반환 (궁수)"""
        if character.gimmick_type == "support_fire":
            return getattr(character, 'support_fire_combo', 0)
        return 0

    # ============================================================
    # 마술사: 트릭 덱 시스템
    # ============================================================

    @staticmethod
    def _update_trick_deck(character):
        """마술사: 트릭 덱 시스템 턴 종료 업데이트"""
        # 손패 확인 및 조합 체크
        hand = getattr(character, 'card_hand', [])
        
        if hand:
            from src.character.skills.job_skills.magician_skills import check_poker_combination, get_card_name
            combo_type, combo_cards, score = check_poker_combination(hand)
            
            if combo_type:
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
                logger.debug(f"{character.name} 현재 조합: {combo_names.get(combo_type, combo_type)}")

    @staticmethod
    def _update_trick_deck_turn_start(character):
        """마술사: 트릭 덱 시스템 턴 시작 업데이트"""
        # 덱 초기화 체크
        if not hasattr(character, 'card_deck') or character.card_deck is None:
            GimmickUpdater.initialize_trick_deck(character)
        
        # 손패 표시
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
            logger.error(f"{character.name} 트릭 덱 초기화 실패: {e}", exc_info=True)
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
        
        # 조합 순위 (높은 조합은 낮은 조합을 포함)
        combo_hierarchy = {
            "royal_straight_flush": 9,
            "straight_flush": 8,
            "four_of_kind": 7,
            "full_house": 6,
            "flush": 5,
            "straight": 4,
            "triple": 3,
            "two_pair": 2,
            "pair": 1
        }
        
        current_rank = combo_hierarchy.get(combo_type, 0)
        required_rank = combo_hierarchy.get(required_combo, 0)
        
        # 현재 조합이 필요 조합보다 같거나 높으면 True
        return current_rank >= required_rank
