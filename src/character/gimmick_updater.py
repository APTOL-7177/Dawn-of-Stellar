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
        elif gimmick_type == "darkness_system":
            GimmickUpdater._update_darkness_system(character)
        elif gimmick_type == "undead_legion":
            GimmickUpdater._update_undead_legion(character)
        elif gimmick_type == "theft_system":
            GimmickUpdater._update_theft_system(character)
        elif gimmick_type == "shapeshifting_system":
            GimmickUpdater._update_shapeshifting_system(character)
        elif gimmick_type == "enchant_system":
            GimmickUpdater._update_enchant_system(character)
        elif gimmick_type == "totem_system":
            GimmickUpdater._update_totem_system(character)
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

    @staticmethod
    def on_turn_start(character):
        """턴 시작 시 기믹 업데이트"""
        gimmick_type = getattr(character, 'gimmick_type', None)
        if not gimmick_type:
            return

        # 확률 왜곡 게이지 - 턴 시작 시 +10
        if gimmick_type == "probability_distortion":
            gauge_gain = getattr(character, 'gauge_per_turn', 10)
            character.distortion_gauge = min(character.max_gauge, character.distortion_gauge + gauge_gain)
            logger.debug(f"{character.name} 확률 왜곡 게이지 +{gauge_gain} (총: {character.distortion_gauge})")

        # 갈증 게이지 - 턴 시작 시 +10
        elif gimmick_type == "thirst_gauge":
            character.thirst = min(character.max_thirst, character.thirst + 10)
            logger.debug(f"{character.name} 갈증 +10 (총: {character.thirst})")

        # ISSUE-004: 추가 턴 시작 기믹 업데이트
        # 군중 환호 - 턴 시작 시 +5
        elif gimmick_type == "crowd_cheer":
            cheer = getattr(character, 'cheer', 0)
            max_cheer = getattr(character, 'max_cheer', 100)
            character.cheer = min(max_cheer, cheer + 5)
            logger.debug(f"{character.name} 환호 증가: +5 (총: {character.cheer})")

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

                        # BRV 데미지 계산 (물리 공격)
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
            if any(t.get('id') == 'auto_cooling' for t in character.active_traits):
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
                    if any(t.get('id') == 'time_correction' for t in character.active_traits):
                        logger.info(f"{character.name} 시간 보정 발동! 타임라인 0으로")
                        character.timeline = 0
                        character.time_correction_counter = 0

    @staticmethod
    def _update_yin_yang_flow(character):
        """몽크: 음양 기 흐름 시스템 업데이트"""
        # 기 흐름 특성 (매 턴 균형(50)으로 +5 이동)
        if hasattr(character, 'active_traits'):
            if any(t.get('id') == 'ki_flow' for t in character.active_traits):
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
        """버서커: 광기 임계치 시스템 업데이트"""
        # 광기 자연 감소 (최적 구간 이하에서만)
        if character.madness < character.optimal_max:
            character.madness = max(0, character.madness - 5)
            logger.debug(f"{character.name} 광기 자연 감소: -5 (총: {character.madness})")

        # 위험 구간에서는 자연 증가
        elif character.madness >= character.danger_min:
            character.madness = min(character.max_madness, character.madness + 10)
            logger.warning(f"{character.name} 광기 위험 증가: +10 (총: {character.madness})")

        # 사망 임계치 체크
        if character.madness >= character.death_threshold:
            logger.critical(f"{character.name} 광기 100 도달! 사망 위험!")
            # 실제 사망 처리는 combat_manager에서 수행

    @staticmethod
    def _update_thirst_gauge(character):
        """뱀파이어: 갈증 게이지 시스템 업데이트"""
        # 굶주림 구간에서 HP 지속 감소
        if character.thirst >= character.starving_min:
            hp_loss = int(character.max_hp * 0.05)
            character.current_hp = max(1, character.current_hp - hp_loss)
            logger.warning(f"{character.name} 굶주림: HP -{hp_loss} (총 HP: {character.current_hp})")

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
            if any(t.get('id') == 'bullet_conservation' for t in character.active_traits):
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
        # 자세는 스킬로만 변경, 자동 업데이트 없음
        pass

    @staticmethod
    def _update_iaijutsu_system(character):
        """사무라이: 거합 시스템 업데이트"""
        # 의지 게이지 자연 증가 (매 턴 +10) - YAML: max_will_gauge
        will_gauge = getattr(character, 'will_gauge', 0)
        max_will = getattr(character, 'max_will_gauge', 100)
        character.will_gauge = min(max_will, will_gauge + 10)
        logger.debug(f"{character.name} 의지 게이지 증가: +10 (총: {character.will_gauge})")

    @staticmethod
    def _update_dragon_marks(character):
        """용기사: 드래곤 마크 시스템 업데이트"""
        # 각인은 스킬로만 축적, 자동 업데이트 없음
        # 각인 5개 도달 시 드래곤 변신 가능 상태 표시
        marks = getattr(character, 'dragon_marks', 0)
        if marks >= 5:
            character.dragon_transform_ready = True
            logger.info(f"{character.name} 드래곤 변신 준비 완료!")

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
        minions = getattr(character, 'undead_minions', 0)
        if minions > 5:
            character.undead_minions = 5

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
    def _update_totem_system(character):
        """무당: 토템 시스템 업데이트"""
        # 토템은 스킬로만 설치/제거, 자동 업데이트 없음
        # 최대 3개까지 유지
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
            
            # CPU 최적화 특성 체크 (프로그램당 MP 소모 -2)
            if hasattr(character, 'active_traits'):
                for trait_data in character.active_traits:
                    trait_id = trait_data if isinstance(trait_data, str) else trait_data.get('id')
                    if trait_id == 'cpu_optimization':
                        mp_per_program = max(1, mp_per_program - 2)  # 최소 1로 제한
            
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
    def check_choice_mastery(character, choice_type: str) -> bool:
        """딜레마틱: 선택 숙련도 확인"""
        # TODO: 구현 필요
        return False


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

        """선택 숙달 달성 여부 체크 (철학자)"""
        if character.gimmick_type == "dilemma_choice":
            count = getattr(character, f'choice_{choice_type}', 0)
            threshold = getattr(character, 'accumulation_threshold', 5)
            return count >= threshold
        return False
