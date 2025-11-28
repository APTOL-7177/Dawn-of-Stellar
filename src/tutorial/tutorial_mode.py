"""
튜토리얼 모드 설정
Dawn of Stellar

튜토리얼 난이도와 관련 설정을 관리합니다.
15층까지 진행하는 가이드 모드
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum

from src.core.logger import get_logger, Loggers

logger = get_logger(Loggers.SYSTEM)


# =============================================================================
# 튜토리얼 모드 설정
# =============================================================================

@dataclass
class TutorialModeConfig:
    """튜토리얼 모드 설정"""
    
    # 활성화 여부
    enabled: bool = False
    
    # 목표 층수 (15층까지)
    target_floor: int = 15
    
    # 난이도 조정
    enemy_hp_multiplier: float = 0.5      # 적 HP 50%
    enemy_attack_multiplier: float = 0.5  # 적 공격력 50%
    enemy_brv_multiplier: float = 0.7     # 적 BRV 70%
    
    # 플레이어 버프
    player_hp_bonus: float = 1.3          # 플레이어 HP 130%
    player_mp_bonus: float = 1.5          # 플레이어 MP 150%
    
    # 회복 보너스
    healing_frequency: float = 2.0         # 회복 포인트 2배
    healing_amount_bonus: float = 1.5      # 회복량 150%
    
    # 부활 시스템
    auto_revive: bool = True               # 패배 시 자동 부활
    revive_hp_percent: float = 0.5         # 50% HP로 부활
    revive_mp_percent: float = 0.5         # 50% MP로 부활
    no_death_penalty: bool = True          # 사망 패널티 없음
    
    # 보상 조정
    stellar_fragment_multiplier: float = 0.5  # 별의 파편 50% (연습이니까)
    
    # 봇 조언자
    bot_enabled: bool = True
    bot_verbose: bool = True               # 자세한 조언
    
    # UI 표시
    show_tutorial_hints: bool = True       # 힌트 UI 표시
    show_recommended_action: bool = True   # 추천 행동 표시
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "enabled": self.enabled,
            "target_floor": self.target_floor,
            "enemy_hp_multiplier": self.enemy_hp_multiplier,
            "enemy_attack_multiplier": self.enemy_attack_multiplier,
            "enemy_brv_multiplier": self.enemy_brv_multiplier,
            "player_hp_bonus": self.player_hp_bonus,
            "player_mp_bonus": self.player_mp_bonus,
            "healing_frequency": self.healing_frequency,
            "healing_amount_bonus": self.healing_amount_bonus,
            "auto_revive": self.auto_revive,
            "bot_enabled": self.bot_enabled,
        }


# =============================================================================
# 튜토리얼 진행 상태
# =============================================================================

@dataclass
class TutorialProgress:
    """튜토리얼 진행 상태"""
    
    # 현재 층
    current_floor: int = 0
    
    # 클리어한 층들
    cleared_floors: List[int] = field(default_factory=list)
    
    # 전투 통계
    total_combats: int = 0
    victories: int = 0
    defeats: int = 0
    revives_used: int = 0
    
    # 학습 체크포인트
    learned_brv_attack: bool = False
    learned_hp_attack: bool = False
    learned_break: bool = False
    learned_skill: bool = False
    learned_item: bool = False
    learned_flee: bool = False
    
    # 직업 기믹 학습
    learned_job_gimmicks: List[str] = field(default_factory=list)
    
    # 완료 여부
    completed: bool = False
    
    def is_floor_cleared(self, floor: int) -> bool:
        """층 클리어 여부"""
        return floor in self.cleared_floors
    
    def mark_floor_cleared(self, floor: int):
        """층 클리어 마킹"""
        if floor not in self.cleared_floors:
            self.cleared_floors.append(floor)
            self.current_floor = max(self.current_floor, floor)
    
    def get_completion_percent(self, target: int = 15) -> float:
        """완료율"""
        return len(self.cleared_floors) / target * 100


# =============================================================================
# 전역 튜토리얼 모드 관리
# =============================================================================

_tutorial_config: Optional[TutorialModeConfig] = None
_tutorial_progress: Optional[TutorialProgress] = None


def get_tutorial_config() -> TutorialModeConfig:
    """튜토리얼 설정 반환"""
    global _tutorial_config
    if _tutorial_config is None:
        _tutorial_config = TutorialModeConfig()
    return _tutorial_config


def get_tutorial_progress() -> TutorialProgress:
    """튜토리얼 진행 상태 반환"""
    global _tutorial_progress
    if _tutorial_progress is None:
        _tutorial_progress = TutorialProgress()
    return _tutorial_progress


def is_tutorial_already_completed() -> bool:
    """튜토리얼 던전을 이미 클리어했는지 확인"""
    try:
        from src.persistence.meta_progress import get_meta_progress
        meta = get_meta_progress()
        return getattr(meta, 'tutorial_completed', False)
    except:
        return False


def start_tutorial_mode() -> TutorialModeConfig:
    """
    튜토리얼 모드 시작
    
    Returns:
        TutorialModeConfig 또는 None (이미 클리어한 경우)
    """
    global _tutorial_config, _tutorial_progress
    
    # 이미 클리어했으면 입장 불가
    if is_tutorial_already_completed():
        logger.warning("튜토리얼 던전은 이미 클리어했습니다. 재입장 불가.")
        return None
    
    _tutorial_config = TutorialModeConfig(enabled=True)
    _tutorial_progress = TutorialProgress()
    
    logger.info("튜토리얼 모드 시작")
    logger.info(f"설정: {_tutorial_config.to_dict()}")
    
    return _tutorial_config


def end_tutorial_mode(completed: bool = False):
    """
    튜토리얼 모드 종료
    
    Args:
        completed: 정상 클리어 여부 (True면 재입장 불가 처리)
    """
    global _tutorial_config, _tutorial_progress
    
    if _tutorial_config:
        _tutorial_config.enabled = False
    
    if _tutorial_progress:
        _tutorial_progress.completed = completed
    
    # 정상 클리어 시 메타 진행에 저장 (재입장 불가 처리)
    if completed:
        try:
            from src.persistence.meta_progress import get_meta_progress, save_meta_progress
            meta = get_meta_progress()
            meta.tutorial_completed = True
            save_meta_progress()
            logger.info("튜토리얼 던전 클리어! 재입장 불가 처리됨.")
        except Exception as e:
            logger.error(f"튜토리얼 완료 저장 실패: {e}")
    
    logger.info("튜토리얼 모드 종료")


def is_tutorial_mode() -> bool:
    """튜토리얼 모드 여부"""
    config = get_tutorial_config()
    return config.enabled


def is_easy_mode() -> bool:
    """평온(Easy) 모드 여부 확인"""
    try:
        from src.persistence.game_state import get_game_state
        game_state = get_game_state()
        if game_state:
            difficulty = getattr(game_state, 'difficulty', None)
            if difficulty in ["평온", "easy", "EASY"]:
                return True
    except:
        pass
    return False


def should_enable_bot() -> bool:
    """봇 활성화 여부 (튜토리얼 또는 평온 모드)"""
    # 튜토리얼 모드면 항상 봇 ON
    if is_tutorial_mode():
        return True
    
    # 평온 모드면 봇 ON
    if is_easy_mode():
        return True
    
    return False


# =============================================================================
# 난이도 적용 헬퍼 함수
# =============================================================================

def apply_tutorial_enemy_stats(
    hp: int, 
    attack: int, 
    brv: int,
    defense: int = 0,
    magic_attack: int = 0,
    magic_defense: int = 0
) -> tuple:
    """
    튜토리얼 모드일 때 적 스탯 조정
    
    Returns:
        (hp, attack, brv, defense, magic_attack, magic_defense) 튜플
    """
    config = get_tutorial_config()
    
    if not config.enabled:
        return hp, attack, brv, defense, magic_attack, magic_defense
    
    return (
        int(hp * config.enemy_hp_multiplier),
        int(attack * config.enemy_attack_multiplier),
        int(brv * config.enemy_brv_multiplier),
        int(defense * 0.7),  # 방어력도 약간 감소
        int(magic_attack * config.enemy_attack_multiplier),  # 마법 공격력도 50%
        int(magic_defense * 0.7)  # 마법 방어력도 감소
    )


def apply_tutorial_player_stats(hp: int, mp: int) -> tuple:
    """
    튜토리얼 모드일 때 플레이어 스탯 보너스
    
    Returns:
        (hp, mp) 튜플
    """
    config = get_tutorial_config()
    
    if not config.enabled:
        return hp, mp
    
    return (
        int(hp * config.player_hp_bonus),
        int(mp * config.player_mp_bonus)
    )


def apply_tutorial_healing(amount: int) -> int:
    """튜토리얼 모드 회복량 보너스"""
    config = get_tutorial_config()
    
    if not config.enabled:
        return amount
    
    return int(amount * config.healing_amount_bonus)


def should_auto_revive() -> bool:
    """자동 부활 여부"""
    config = get_tutorial_config()
    return config.enabled and config.auto_revive


def get_revive_stats(max_hp: int, max_mp: int) -> tuple:
    """부활 시 HP/MP"""
    config = get_tutorial_config()
    
    return (
        int(max_hp * config.revive_hp_percent),
        int(max_mp * config.revive_mp_percent)
    )


def apply_stellar_fragment_reward(amount: int) -> int:
    """별의 파편 보상 조정"""
    config = get_tutorial_config()
    
    if not config.enabled:
        return amount
    
    return int(amount * config.stellar_fragment_multiplier)


# =============================================================================
# 층 클리어 체크
# =============================================================================

def check_tutorial_completion() -> bool:
    """
    튜토리얼 완료 체크
    
    Returns:
        True if 15층 클리어
    """
    config = get_tutorial_config()
    progress = get_tutorial_progress()
    
    if not config.enabled:
        return False
    
    if progress.current_floor >= config.target_floor:
        progress.completed = True
        logger.info("튜토리얼 완료! 15층 도달")
        return True
    
    return False


def get_tutorial_completion_message() -> str:
    """튜토리얼 완료 메시지"""
    progress = get_tutorial_progress()
    
    stats = f"""
축하합니다! 튜토리얼을 완료했습니다!

=== 통계 ===
클리어 층수: {len(progress.cleared_floors)}층
총 전투: {progress.total_combats}회
승리: {progress.victories}회
부활 사용: {progress.revives_used}회

이제 본격적인 던전 탐험을 시작하세요!
"""
    return stats
