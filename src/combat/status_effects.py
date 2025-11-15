"""
Status Effects - 상태 효과 시스템

Dawn of Stellar의 모든 상태 이상 및 버프/디버프를 관리합니다.
"""

from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from src.core.event_bus import event_bus, Events
from src.core.logger import get_logger


logger = get_logger("status_effects")


class StatusType(Enum):
    """상태 효과 타입 Enum"""

    # === 기본 효과 카테고리 ===
    BUFF = "버프"           # 유익한 효과
    DEBUFF = "디버프"       # 해로운 효과
    DOT = "지속피해"        # Damage Over Time
    HOT = "지속회복"        # Heal Over Time
    CC = "군중제어"         # Crowd Control
    SPECIAL = "특수"        # 특수 효과

    # === 버프 상태 (27개) ===
    BOOST_ATK = "공격력증가"
    BOOST_DEF = "방어력증가"
    BOOST_SPD = "속도증가"
    BOOST_ACCURACY = "명중률증가"
    BOOST_CRIT = "치명타증가"
    BOOST_DODGE = "회피율증가"
    BOOST_ALL_STATS = "모든능력치증가"
    BOOST_MAGIC_ATK = "마법공격증가"
    BOOST_MAGIC_DEF = "마법방어증가"
    BLESSING = "축복"
    REGENERATION = "재생"
    MP_REGEN = "MP재생"
    INVINCIBLE = "무적"
    REFLECT = "반사"
    HASTE = "가속"
    FOCUS = "집중"
    RAGE = "분노"
    INSPIRATION = "영감"
    GUARDIAN = "수호"
    STRENGTHEN = "강화"
    EVASION_UP = "회피증가"
    FORESIGHT = "예지"
    ENLIGHTENMENT = "깨달음"
    WISDOM = "지혜"
    MANA_REGENERATION = "마나재생"
    MANA_INFINITE = "무한마나"
    HOLY_BLESSING = "성스러운축복"

    # === 보호막 시스템 (7개) ===
    BARRIER = "보호막"
    SHIELD = "보호막"
    MAGIC_BARRIER = "마법보호막"
    MANA_SHIELD = "마나실드"
    FIRE_SHIELD = "화염방패"
    ICE_SHIELD = "빙결방패"
    HOLY_SHIELD = "성스러운방패"
    SHADOW_SHIELD = "그림자방패"

    # === 디버프 상태 (18개) ===
    REDUCE_ATK = "공격력감소"
    REDUCE_DEF = "방어력감소"
    REDUCE_SPD = "속도감소"
    REDUCE_ACCURACY = "명중률감소"
    REDUCE_ALL_STATS = "전능력감소"
    REDUCE_MAGIC_ATK = "마법공격감소"
    REDUCE_MAGIC_DEF = "마법방어감소"
    REDUCE_SPEED = "속도감소"
    VULNERABLE = "취약"
    EXPOSED = "노출"
    WEAKNESS = "허약"
    WEAKEN = "약화"
    CONFUSION = "혼란"
    TERROR = "공포"
    FEAR = "공포"
    DESPAIR = "절망"
    HOLY_WEAKNESS = "성스러운약점"
    WEAKNESS_EXPOSURE = "약점노출"

    # === 상태이상 - DOT (11개) ===
    POISON = "독"
    BURN = "화상"
    BLEED = "출혈"
    CORRODE = "부식"
    CORROSION = "부식"
    DISEASE = "질병"
    NECROSIS = "괴사"
    MP_DRAIN = "MP소모"
    CHILL = "냉기"
    SHOCK = "감전"
    NATURE_CURSE = "자연저주"

    # === 행동 제약 - CC (14개) ===
    STUN = "기절"
    SLEEP = "수면"
    SILENCE = "침묵"
    BLIND = "실명"
    PARALYZE = "마비"
    FREEZE = "빙결"
    PETRIFY = "석화"
    CHARM = "매혹"
    DOMINATE = "지배"
    ROOT = "속박"
    SLOW = "둔화"
    ENTANGLE = "속박술"
    MADNESS = "광기"
    TAUNT = "도발"

    # === 특수 상태 (44개) ===
    CURSE = "저주"
    STEALTH = "은신"
    BERSERK = "광폭화"
    COUNTER = "반격태세"
    COUNTER_ATTACK = "반격"
    VAMPIRE = "흡혈"
    SPIRIT_LINK = "정신연결"
    SOUL_BOND = "영혼유대"
    TIME_STOP = "시간정지"
    TIME_MARKED = "시간기록"
    TIME_SAVEPOINT = "시간저장점"
    TIME_DISTORTION = "시간왜곡"
    PHASE = "위상변화"
    TRANSCENDENCE = "초월"
    ANALYZE = "분석"
    AUTO_TURRET = "자동포탑"
    REPAIR_DRONE = "수리드론"
    ABSOLUTE_EVASION = "절대회피"
    TEMPORARY_INVINCIBLE = "일시무적"
    EXISTENCE_DENIAL = "존재부정"
    TRUTH_REVELATION = "진리계시"
    GHOST_FLEET = "유령함대"
    ANIMAL_FORM = "동물변신"
    DIVINE_PUNISHMENT = "신벌"
    DIVINE_JUDGMENT = "신심판"
    HEAVEN_GATE = "천국문"
    PURIFICATION = "정화"
    MARTYRDOM = "순교"
    ELEMENTAL_WEAPON = "원소무기"
    ELEMENTAL_IMMUNITY = "원소면역"
    MAGIC_FIELD = "마법진영"
    TRANSMUTATION = "변환술"
    PHILOSOPHERS_STONE = "현자의돌"
    UNDEAD_MINION = "언데드하수인"
    SHADOW_CLONE = "그림자분신"
    SHADOW_STACK = "그림자축적"
    SHADOW_ECHO = "그림자메아리"
    SHADOW_EMPOWERED = "그림자강화"
    EXTRA_TURN = "추가턴"
    HOLY_MARK = "성스러운표식"
    HOLY_AURA = "성스러운기운"
    DRAGON_FORM = "용변신"
    WARRIOR_STANCE = "전사자세"
    AFTERIMAGE = "잔상"


@dataclass
class StatusEffect:
    """
    상태 효과 클래스

    Attributes:
        name: 상태 효과 이름
        status_type: 상태 효과 타입
        duration: 남은 지속 시간 (턴 수)
        intensity: 효과 강도 (배율)
        stack_count: 현재 스택 수
        max_stacks: 최대 스택 수
        is_stackable: 스택 가능 여부
        source_id: 효과를 부여한 캐릭터 ID (추적용)
        metadata: 추가 메타데이터
    """
    name: str
    status_type: StatusType
    duration: int
    intensity: float = 1.0
    stack_count: int = 1
    max_stacks: int = 1
    is_stackable: bool = False
    source_id: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}
        self.max_duration = self.duration

    def __str__(self) -> str:
        """상태 효과 문자열 표현"""
        stack_info = f"x{self.stack_count}" if self.is_stackable and self.stack_count > 1 else ""
        return f"{self.name}({self.duration}턴){stack_info}"

    def __repr__(self) -> str:
        """디버깅용 상세 정보"""
        return (f"StatusEffect(name={self.name}, type={self.status_type.name}, "
                f"duration={self.duration}/{self.max_duration}, "
                f"intensity={self.intensity}, stacks={self.stack_count}/{self.max_stacks})")


class StatusManager:
    """
    상태 효과 관리자

    캐릭터의 모든 상태 효과를 관리합니다.
    """

    def __init__(self, owner_name: str = "Unknown") -> None:
        """
        Args:
            owner_name: 상태 효과의 소유자 이름 (로깅용)
        """
        self.owner_name = owner_name
        self.status_effects: List[StatusEffect] = []
        self.effects = self.status_effects  # 호환성을 위한 별칭

    def add_status(
        self,
        status_effect: StatusEffect,
        allow_refresh: bool = True
    ) -> bool:
        """
        상태 효과 추가

        Args:
            status_effect: 추가할 상태 효과
            allow_refresh: True면 기존 효과의 지속시간을 갱신

        Returns:
            새로운 효과가 추가되었으면 True, 기존 효과를 갱신했으면 False
        """
        existing = self.get_status(status_effect.status_type)

        if existing:
            if existing.is_stackable and existing.stack_count < existing.max_stacks:
                # 스택 추가
                existing.stack_count += 1
                existing.duration = max(existing.duration, status_effect.duration)
                logger.debug(
                    f"{self.owner_name}: {status_effect.name} 스택 추가 "
                    f"({existing.stack_count}/{existing.max_stacks})"
                )
            elif allow_refresh:
                # 지속시간 갱신
                existing.duration = max(existing.duration, status_effect.duration)
                existing.intensity = max(existing.intensity, status_effect.intensity)
                logger.debug(
                    f"{self.owner_name}: {status_effect.name} 지속시간 갱신 "
                    f"({existing.duration}턴)"
                )

            # 이벤트 발행
            event_bus.publish(Events.STATUS_APPLIED, {
                "owner": self.owner_name,
                "status": existing,
                "is_new": False
            })

            return False
        else:
            # 새로운 효과 추가
            self.status_effects.append(status_effect)
            self.effects = self.status_effects

            logger.info(
                f"{self.owner_name}: {status_effect.name} 추가 "
                f"(지속시간: {status_effect.duration}턴, 강도: {status_effect.intensity})"
            )

            # 이벤트 발행
            event_bus.publish(Events.STATUS_APPLIED, {
                "owner": self.owner_name,
                "status": status_effect,
                "is_new": True
            })

            return True

    def remove_status(self, status_type: StatusType) -> bool:
        """
        특정 상태 효과 제거

        Args:
            status_type: 제거할 상태 효과 타입

        Returns:
            제거 성공 여부
        """
        effect = self.get_status(status_type)
        if effect:
            self.status_effects.remove(effect)
            self.effects = self.status_effects

            logger.info(f"{self.owner_name}: {effect.name} 제거")

            # 이벤트 발행
            event_bus.publish(Events.STATUS_REMOVED, {
                "owner": self.owner_name,
                "status": effect
            })

            return True
        return False

    def get_status(self, status_type: StatusType) -> Optional[StatusEffect]:
        """
        특정 상태 효과 조회

        Args:
            status_type: 조회할 상태 효과 타입

        Returns:
            해당하는 StatusEffect 또는 None
        """
        for effect in self.status_effects:
            if effect.status_type == status_type:
                return effect
        return None

    def has_status(self, status_type: StatusType) -> bool:
        """
        특정 상태 효과 보유 여부 확인

        Args:
            status_type: 확인할 상태 효과 타입

        Returns:
            보유 여부
        """
        return self.get_status(status_type) is not None

    def update_duration(self) -> List[StatusEffect]:
        """
        모든 상태 효과의 지속시간 감소

        Returns:
            만료된 상태 효과 리스트
        """
        expired: List[StatusEffect] = []

        for effect in self.status_effects[:]:
            effect.duration -= 1

            if effect.duration <= 0:
                expired.append(effect)
                self.status_effects.remove(effect)

                logger.debug(f"{self.owner_name}: {effect.name} 효과 만료")

                # 이벤트 발행
                event_bus.publish(Events.STATUS_REMOVED, {
                    "owner": self.owner_name,
                    "status": effect,
                    "expired": True
                })

        self.effects = self.status_effects
        return expired

    def clear_all_effects(self) -> None:
        """모든 상태 효과 제거"""
        cleared = self.status_effects.copy()
        self.status_effects.clear()
        self.effects = self.status_effects

        logger.info(f"{self.owner_name}: 모든 상태 효과 제거 ({len(cleared)}개)")

        for effect in cleared:
            event_bus.publish(Events.STATUS_REMOVED, {
                "owner": self.owner_name,
                "status": effect,
                "cleared": True
            })

    def can_act(self) -> bool:
        """
        행동 가능 여부 확인

        Returns:
            행동 가능하면 True, 불가능하면 False
        """
        blocking_states = [
            StatusType.STUN,
            StatusType.SLEEP,
            StatusType.FREEZE,
            StatusType.PETRIFY,
            StatusType.PARALYZE,
            StatusType.TIME_STOP
        ]

        return not any(
            effect.status_type in blocking_states
            for effect in self.status_effects
        )

    def can_use_skills(self) -> bool:
        """
        스킬 사용 가능 여부 확인

        Returns:
            스킬 사용 가능하면 True, 불가능하면 False
        """
        silencing_states = [
            StatusType.SILENCE,
            StatusType.MADNESS
        ]

        return not any(
            effect.status_type in silencing_states
            for effect in self.status_effects
        )

    def is_controlled(self) -> bool:
        """
        제어 불가 상태 확인 (매혹, 지배, 혼란)

        Returns:
            제어 불가 상태면 True
        """
        control_states = [
            StatusType.CHARM,
            StatusType.DOMINATE,
            StatusType.CONFUSION
        ]

        return any(
            effect.status_type in control_states
            for effect in self.status_effects
        )

    def has_stealth(self) -> bool:
        """은신 상태 확인"""
        return self.has_status(StatusType.STEALTH)

    def has_invincibility(self) -> bool:
        """무적 상태 확인"""
        return (self.has_status(StatusType.INVINCIBLE) or
                self.has_status(StatusType.TEMPORARY_INVINCIBLE))

    def get_stat_modifiers(self) -> Dict[str, float]:
        """
        스탯 수정치 반환 (곱셈용 배율)

        Returns:
            스탯별 배율 딕셔너리
        """
        modifiers: Dict[str, float] = {
            'physical_attack': 1.0,
            'magic_attack': 1.0,
            'physical_defense': 1.0,
            'magic_defense': 1.0,
            'speed': 1.0,
            'accuracy': 1.0,
            'evasion': 1.0,
            'critical_rate': 1.0
        }

        for effect in self.status_effects:
            intensity = effect.intensity * effect.stack_count

            # 버프
            if effect.status_type == StatusType.BOOST_ATK:
                modifiers['physical_attack'] *= (1.0 + intensity * 0.2)
                modifiers['magic_attack'] *= (1.0 + intensity * 0.2)
            elif effect.status_type == StatusType.BOOST_DEF:
                modifiers['physical_defense'] *= (1.0 + intensity * 0.2)
                modifiers['magic_defense'] *= (1.0 + intensity * 0.2)
            elif effect.status_type == StatusType.BOOST_SPD:
                modifiers['speed'] *= (1.0 + intensity * 0.3)
            elif effect.status_type == StatusType.BOOST_ACCURACY:
                modifiers['accuracy'] *= (1.0 + intensity * 0.15)
            elif effect.status_type == StatusType.BOOST_CRIT:
                modifiers['critical_rate'] *= (1.0 + intensity * 0.25)
            elif effect.status_type == StatusType.BOOST_DODGE:
                modifiers['evasion'] *= (1.0 + intensity * 0.2)
            elif effect.status_type == StatusType.BOOST_MAGIC_ATK:
                modifiers['magic_attack'] *= (1.0 + intensity * 0.25)
            elif effect.status_type == StatusType.BOOST_MAGIC_DEF:
                modifiers['magic_defense'] *= (1.0 + intensity * 0.25)
            elif effect.status_type == StatusType.BOOST_ALL_STATS:
                for key in modifiers:
                    modifiers[key] *= (1.0 + intensity * 0.15)

            # 디버프
            elif effect.status_type == StatusType.REDUCE_ATK:
                modifiers['physical_attack'] *= (1.0 - intensity * 0.2)
                modifiers['magic_attack'] *= (1.0 - intensity * 0.2)
            elif effect.status_type == StatusType.REDUCE_DEF:
                modifiers['physical_defense'] *= (1.0 - intensity * 0.2)
                modifiers['magic_defense'] *= (1.0 - intensity * 0.2)
            elif effect.status_type in [StatusType.REDUCE_SPD, StatusType.REDUCE_SPEED]:
                modifiers['speed'] *= (1.0 - intensity * 0.3)
            elif effect.status_type == StatusType.REDUCE_ACCURACY:
                modifiers['accuracy'] *= (1.0 - intensity * 0.15)
            elif effect.status_type == StatusType.REDUCE_MAGIC_ATK:
                modifiers['magic_attack'] *= (1.0 - intensity * 0.25)
            elif effect.status_type == StatusType.REDUCE_MAGIC_DEF:
                modifiers['magic_defense'] *= (1.0 - intensity * 0.25)
            elif effect.status_type == StatusType.REDUCE_ALL_STATS:
                for key in modifiers:
                    modifiers[key] *= (1.0 - intensity * 0.15)

            # 특수 상태
            elif effect.status_type == StatusType.VULNERABLE:
                modifiers['physical_defense'] *= 0.5
                modifiers['magic_defense'] *= 0.5
            elif effect.status_type == StatusType.EXPOSED:
                modifiers['evasion'] *= 0.3
            elif effect.status_type == StatusType.WEAKNESS:
                modifiers['physical_attack'] *= 0.7
                modifiers['magic_attack'] *= 0.7
            elif effect.status_type == StatusType.HASTE:
                modifiers['speed'] *= 1.5
            elif effect.status_type == StatusType.SLOW:
                modifiers['speed'] *= 0.6
            elif effect.status_type == StatusType.FOCUS:
                modifiers['accuracy'] *= 1.3
                modifiers['critical_rate'] *= 1.2
            elif effect.status_type == StatusType.RAGE:
                modifiers['physical_attack'] *= 1.4
                modifiers['physical_defense'] *= 0.8
            elif effect.status_type == StatusType.BERSERK:
                modifiers['physical_attack'] *= 1.6
                modifiers['magic_attack'] *= 1.6
                modifiers['physical_defense'] *= 0.6
                modifiers['magic_defense'] *= 0.6
                modifiers['accuracy'] *= 0.8
            elif effect.status_type == StatusType.BLIND:
                modifiers['accuracy'] *= 0.3
            elif effect.status_type == StatusType.TERROR:
                modifiers['physical_attack'] *= 0.6
                modifiers['magic_attack'] *= 0.6
                modifiers['speed'] *= 0.7

        return modifiers

    def get_active_effects(self) -> List[str]:
        """
        활성 상태 효과 이름 목록

        Returns:
            상태 효과 이름 리스트
        """
        return [effect.name for effect in self.status_effects]

    def get_status_display(self) -> str:
        """
        상태 효과 표시 문자열

        Returns:
            상태 효과 요약 문자열
        """
        if not self.status_effects:
            return "상태 효과 없음"

        effects_str = []
        for effect in self.status_effects:
            stack_info = f"x{effect.stack_count}" if effect.is_stackable and effect.stack_count > 1 else ""
            effects_str.append(f"{effect.name}({effect.duration}){stack_info}")

        return " | ".join(effects_str)


# === 유틸리티 함수 ===

def create_status_effect(
    name: str,
    status_type: StatusType,
    duration: int,
    intensity: float = 1.0,
    is_stackable: bool = False,
    max_stacks: int = 1,
    source_id: Optional[str] = None,
    **metadata
) -> StatusEffect:
    """
    상태 효과 생성 헬퍼 함수

    Args:
        name: 상태 효과 이름
        status_type: 상태 효과 타입
        duration: 지속 시간
        intensity: 효과 강도
        is_stackable: 스택 가능 여부
        max_stacks: 최대 스택 수
        source_id: 효과를 부여한 캐릭터 ID
        **metadata: 추가 메타데이터

    Returns:
        생성된 StatusEffect
    """
    return StatusEffect(
        name=name,
        status_type=status_type,
        duration=duration,
        intensity=intensity,
        stack_count=1,
        max_stacks=max_stacks,
        is_stackable=is_stackable,
        source_id=source_id,
        metadata=metadata if metadata else {}
    )


def get_status_category(status_type: StatusType) -> str:
    """
    상태 효과의 카테고리 반환

    Args:
        status_type: 상태 효과 타입

    Returns:
        카테고리 문자열 ("BUFF", "DEBUFF", "DOT", "HOT", "CC", "SPECIAL")
    """
    # HOT 타입 먼저 체크 (BUFF와 중복되는 경우가 있으므로)
    hot_types = [
        StatusType.REGENERATION, StatusType.MP_REGEN,
        StatusType.MANA_REGENERATION
    ]

    if status_type in hot_types:
        return "HOT"

    buff_types = [
        StatusType.BOOST_ATK, StatusType.BOOST_DEF, StatusType.BOOST_SPD,
        StatusType.BOOST_ACCURACY, StatusType.BOOST_CRIT, StatusType.BOOST_DODGE,
        StatusType.BOOST_ALL_STATS, StatusType.BOOST_MAGIC_ATK, StatusType.BOOST_MAGIC_DEF,
        StatusType.BLESSING, StatusType.INVINCIBLE, StatusType.REFLECT, StatusType.HASTE,
        StatusType.FOCUS, StatusType.RAGE, StatusType.INSPIRATION,
        StatusType.GUARDIAN, StatusType.STRENGTHEN, StatusType.EVASION_UP,
        StatusType.FORESIGHT, StatusType.ENLIGHTENMENT, StatusType.WISDOM,
        StatusType.MANA_INFINITE, StatusType.HOLY_BLESSING,
        StatusType.BARRIER, StatusType.SHIELD, StatusType.MAGIC_BARRIER,
        StatusType.MANA_SHIELD, StatusType.FIRE_SHIELD, StatusType.ICE_SHIELD,
        StatusType.HOLY_SHIELD, StatusType.SHADOW_SHIELD
    ]

    debuff_types = [
        StatusType.REDUCE_ATK, StatusType.REDUCE_DEF, StatusType.REDUCE_SPD,
        StatusType.REDUCE_ACCURACY, StatusType.REDUCE_ALL_STATS,
        StatusType.REDUCE_MAGIC_ATK, StatusType.REDUCE_MAGIC_DEF,
        StatusType.REDUCE_SPEED, StatusType.VULNERABLE, StatusType.EXPOSED,
        StatusType.WEAKNESS, StatusType.WEAKEN, StatusType.CONFUSION,
        StatusType.TERROR, StatusType.FEAR, StatusType.DESPAIR,
        StatusType.HOLY_WEAKNESS, StatusType.WEAKNESS_EXPOSURE
    ]

    dot_types = [
        StatusType.POISON, StatusType.BURN, StatusType.BLEED,
        StatusType.CORRODE, StatusType.CORROSION, StatusType.DISEASE,
        StatusType.NECROSIS, StatusType.MP_DRAIN, StatusType.CHILL,
        StatusType.SHOCK, StatusType.NATURE_CURSE
    ]

    cc_types = [
        StatusType.STUN, StatusType.SLEEP, StatusType.SILENCE,
        StatusType.BLIND, StatusType.PARALYZE, StatusType.FREEZE,
        StatusType.PETRIFY, StatusType.CHARM, StatusType.DOMINATE,
        StatusType.ROOT, StatusType.SLOW, StatusType.ENTANGLE,
        StatusType.MADNESS, StatusType.TAUNT
    ]

    if status_type in buff_types:
        return "BUFF"
    elif status_type in debuff_types:
        return "DEBUFF"
    elif status_type in dot_types:
        return "DOT"
    elif status_type in cc_types:
        return "CC"
    else:
        return "SPECIAL"


# === 상태 효과 아이콘 매핑 ===

STATUS_ICONS: Dict[StatusType, str] = {
    # 버프
    StatusType.BOOST_ATK: "⚔️",
    StatusType.BOOST_DEF: "🛡️",
    StatusType.BOOST_SPD: "💨",
    StatusType.BOOST_ACCURACY: "🎯",
    StatusType.BOOST_CRIT: "💥",
    StatusType.BOOST_DODGE: "💃",
    StatusType.BLESSING: "✨",
    StatusType.REGENERATION: "💚",
    StatusType.INVINCIBLE: "🌟",
    StatusType.REFLECT: "🪞",
    StatusType.HASTE: "🏃",
    StatusType.FOCUS: "🎯",
    StatusType.RAGE: "😡",

    # 보호막
    StatusType.BARRIER: "🔵",
    StatusType.SHIELD: "🛡️",
    StatusType.MAGIC_BARRIER: "🔮",
    StatusType.FIRE_SHIELD: "🔥",
    StatusType.ICE_SHIELD: "🧊",

    # 디버프
    StatusType.REDUCE_ATK: "⚔️⬇️",
    StatusType.REDUCE_DEF: "🛡️⬇️",
    StatusType.REDUCE_SPD: "💨⬇️",
    StatusType.VULNERABLE: "💔",
    StatusType.EXPOSED: "👁️",
    StatusType.WEAKNESS: "😰",

    # DOT
    StatusType.POISON: "☠️",
    StatusType.BURN: "🔥",
    StatusType.BLEED: "🩸",
    StatusType.CORRODE: "🧪",
    StatusType.NECROSIS: "💀",

    # CC
    StatusType.STUN: "😵",
    StatusType.SLEEP: "😴",
    StatusType.SILENCE: "🤐",
    StatusType.BLIND: "🙈",
    StatusType.PARALYZE: "⚡",
    StatusType.FREEZE: "🧊",
    StatusType.PETRIFY: "🗿",
    StatusType.CHARM: "💖",
    StatusType.CONFUSION: "😵‍💫",

    # 특수
    StatusType.CURSE: "🌑",
    StatusType.STEALTH: "👻",
    StatusType.BERSERK: "🤬",
    StatusType.VAMPIRE: "🧛",
    StatusType.TIME_STOP: "⏰",
}


def get_status_icon(status_type: StatusType) -> str:
    """
    상태 효과 아이콘 반환

    Args:
        status_type: 상태 효과 타입

    Returns:
        아이콘 문자열
    """
    return STATUS_ICONS.get(status_type, "❓")
