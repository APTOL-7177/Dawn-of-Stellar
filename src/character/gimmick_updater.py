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
        # 광기 자연 감소 (안전 구간에서만)
        if character.madness < character.safe_max:
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

    @staticmethod
    def check_choice_mastery(character, choice_type: str) -> bool:
        """선택 숙달 달성 여부 체크 (철학자)"""
        if character.gimmick_type == "dilemma_choice":
            count = getattr(character, f'choice_{choice_type}', 0)
            threshold = getattr(character, 'accumulation_threshold', 5)
            return count >= threshold
        return False
