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
    OVERCLOCK = "오버클럭"

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
    REDUCE_EVASION = "회피율감소"
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
    FEAR = "두려움"  # 공포와 유사, AI 사용
    DESPAIR = "절망"  # 디버프 상태
    MP_DRAIN = "MP소모"
    CHILL = "냉기"
    SHOCK = "감전"
    NATURE_CURSE = "자연저주"

    # === 상태이상 - DOT (11개) ===
    POISON = "독"
    BURN = "화상"
    BLEED = "출혈"
    CORRODE = "부식"
    CORROSION = "부식"
    DISEASE = "질병"
    NECROSIS = "괴사"

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
    
    # === 팀워크 스킬용 특수 상태 ===
    HP_RECOVERY_BLOCK = "회복불가"  # HP 회복 불가
    CURSE_MARK = "저주낙인"  # 저주 낙인
    
    # === 마술사 스킬용 특수 상태 ===
    DOOM = "죽음의선고"  # 타임 봄: 지연 폭발
    
    # === 아크메이지 융합 스킬용 상태 효과 ===
    ELECTROCUTED = "감전"  # DoT + ATB 증가율 감소
    SLOWED = "둔화"  # ATB 증가율 감소
    DEFENSE_SHATTER = "방어파쇄"  # 물리/마법 방어력 -30% + 다음 공격 BRV +25%
    WOUND = "상처"  # 회복 효과 -50%
    BURNING = "작열"  # 강화된 화상 DoT + 화염 저항 -30%
    FROZEN_SOLID = "동결"  # 행동 불가 (빙결 강화 버전)
    
    # === 아크메이지 원소 낙인 ===
    FIRE_BRAND = "화염낙인"  # 화염 데미지 +40%, 화염 공격시 화상 1턴 추가
    ICE_BRAND = "빙결낙인"  # 빙결 데미지 +40%, 빙결 공격시 ATB -100
    LIGHTNING_BRAND = "번개낙인"  # 번개 데미지 +40%, 번개 공격시 BRV -30%
    
    # === 아크메이지 지연 마법진 ===
    FIRE_GLYPH = "화염마법진"  # 설치된 화염 마법진
    ICE_GLYPH = "빙결마법진"  # 설치된 빙결 마법진
    LIGHTNING_GLYPH = "번개마법진"  # 설치된 번개 마법진
    
    # === 아크메이지 원소 장막 ===
    ELEMENTAL_AEGIS = "원소장막"  # 원소 보호막 활성화
    SCATTER = "자세무너짐"  # 자세 무너짐


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

    def __init__(self, owner_name: str = "Unknown", owner: Any = None) -> None:
        """
        Args:
            owner_name: 상태 효과의 소유자 이름 (로깅용)
            owner: 상태 효과의 소유자 객체 (ATB 리셋 등에 사용)
        """
        self.owner_name = owner_name
        self.owner = owner  # 캐릭터 객체 참조
        self.status_effects: List[StatusEffect] = []
        self.effects = self.status_effects  # 호환성을 위한 별칭
        self.immune_to_all = False  # 모든 상태이상 면역

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
        # 면역 체크
        if self.immune_to_all:
            logger.debug(f"{self.owner_name}: 상태이상 면역 - {status_effect.name} 무시")
            return False
            
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

            # 기절 상태이상 갱신 시에도 ATB 리셋 (기절이 새로 적용되는 경우)
            if status_effect.status_type == StatusType.STUN and self.owner:
                from src.combat.atb_system import get_atb_system
                atb_system = get_atb_system()
                gauge = atb_system.get_gauge(self.owner)
                if gauge and not gauge.is_stunned:
                    # 기절이 새로 적용되는 경우 (기존에 기절이 없었던 경우)
                    gauge.current = 0
                    gauge.is_stunned = True
                    logger.info(f"{self.owner_name}: 기절 상태이상 갱신 → ATB 0으로 리셋")

            # 이벤트 발행
            event_bus.publish(Events.STATUS_APPLIED, {
                "owner": self.owner_name,
                "owner_object": self.owner,  # owner 객체 추가
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

            # 기절 상태이상 추가 시 ATB 즉시 0으로 리셋
            if status_effect.status_type == StatusType.STUN and self.owner:
                from src.combat.atb_system import get_atb_system
                atb_system = get_atb_system()
                gauge = atb_system.get_gauge(self.owner)
                if gauge:
                    gauge.current = 0
                    gauge.is_stunned = True
                    logger.info(f"{self.owner_name}: 기절 상태이상 적용 → ATB 0으로 리셋")
            # 마비 상태이상 추가 시 ATB 게이지 플래그 설정
            elif status_effect.status_type == StatusType.PARALYZE and self.owner:
                from src.combat.atb_system import get_atb_system
                atb_system = get_atb_system()
                gauge = atb_system.get_gauge(self.owner)
                if gauge:
                    gauge.is_paralyzed = True
                    logger.info(f"{self.owner_name}: 마비 상태이상 적용 → ATB 게이지 플래그 설정")
            # 수면 상태이상 추가 시 ATB 게이지 플래그 설정
            elif status_effect.status_type == StatusType.SLEEP and self.owner:
                from src.combat.atb_system import get_atb_system
                atb_system = get_atb_system()
                gauge = atb_system.get_gauge(self.owner)
                if gauge:
                    gauge.is_sleeping = True
                    logger.info(f"{self.owner_name}: 수면 상태이상 적용 → ATB 게이지 플래그 설정")

            # 이벤트 발행
            event_bus.publish(Events.STATUS_APPLIED, {
                "owner": self.owner_name,
                "owner_object": self.owner,  # owner 객체 추가
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

            # 기절/마비/수면 상태 제거 시 ATB 게이지 플래그도 업데이트
            if status_type == StatusType.STUN and self.owner:
                from src.combat.atb_system import get_atb_system
                atb_system = get_atb_system()
                gauge = atb_system.get_gauge(self.owner)
                if gauge:
                    gauge.is_stunned = False
                    logger.debug(f"{self.owner_name}: 기절 상태 제거 → ATB 게이지 플래그 해제")
            elif status_type == StatusType.PARALYZE and self.owner:
                from src.combat.atb_system import get_atb_system
                atb_system = get_atb_system()
                gauge = atb_system.get_gauge(self.owner)
                if gauge:
                    gauge.is_paralyzed = False
                    logger.debug(f"{self.owner_name}: 마비 상태 제거 → ATB 게이지 플래그 해제")
            elif status_type == StatusType.SLEEP and self.owner:
                from src.combat.atb_system import get_atb_system
                atb_system = get_atb_system()
                gauge = atb_system.get_gauge(self.owner)
                if gauge:
                    gauge.is_sleeping = False
                    logger.debug(f"{self.owner_name}: 수면 상태 제거 → ATB 게이지 플래그 해제")
            
            # SCATTER 상태 제거 시 플래그 해제
            elif status_type == StatusType.SCATTER and self.owner:
                self.owner.is_scattered = False
                self.owner.scatter_source = None
                logger.debug(f"{self.owner_name}: SCATTER 상태 제거 → 플래그 해제")

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

                # 기절/마비/수면 상태 만료 시 ATB 게이지 플래그도 업데이트
                if effect.status_type == StatusType.STUN and self.owner:
                    from src.combat.atb_system import get_atb_system
                    atb_system = get_atb_system()
                    gauge = atb_system.get_gauge(self.owner)
                    if gauge:
                        gauge.is_stunned = False
                        logger.debug(f"{self.owner_name}: 기절 상태 만료 → ATB 게이지 플래그 해제")
                elif effect.status_type == StatusType.PARALYZE and self.owner:
                    from src.combat.atb_system import get_atb_system
                    atb_system = get_atb_system()
                    gauge = atb_system.get_gauge(self.owner)
                    if gauge:
                        gauge.is_paralyzed = False
                        logger.debug(f"{self.owner_name}: 마비 상태 만료 → ATB 게이지 플래그 해제")
                elif effect.status_type == StatusType.SLEEP and self.owner:
                    from src.combat.atb_system import get_atb_system
                    atb_system = get_atb_system()
                    gauge = atb_system.get_gauge(self.owner)
                    if gauge:
                        gauge.is_sleeping = False
                    if gauge:
                        gauge.is_sleeping = False
                        logger.debug(f"{self.owner_name}: 수면 상태 만료 → ATB 게이지 플래그 해제")
                
                # SCATTER 상태 만료 시 플래그 해제
                elif effect.status_type == StatusType.SCATTER and self.owner:
                    self.owner.is_scattered = False
                    self.owner.scatter_source = None
                    logger.debug(f"{self.owner_name}: SCATTER 상태 만료 → 플래그 해제")
                
                # GUARDIAN (보호) 만료 시 protected_by 정리
                elif effect.status_type == StatusType.GUARDIAN and self.owner:
                    protector = effect.metadata.get('protector')
                    if protector and hasattr(self.owner, 'protected_by'):
                        # 해당 보호자에 의한 보호 정보 제거
                        original_len = len(self.owner.protected_by)
                        self.owner.protected_by = [p for p in self.owner.protected_by if p['protector'] != protector]
                        if len(self.owner.protected_by) < original_len:
                            logger.debug(f"{self.owner_name}: 보호 상태 만료 → 보호자 {getattr(protector, 'name', 'Unknown')} 연결 해제")
                            
                        # 보호자의 protected_allies에서도 제거
                        if hasattr(protector, 'protected_allies'):
                            protector.protected_allies = [r for r in protector.protected_allies if r['target'] != self.owner]

                # DOOM (죽음의 선고) 만료 시 폭발 피해 - 적 전체 동시 폭발!
                elif effect.status_type == StatusType.DOOM and self.owner:
                    # 시전자 정보에서 폭발 피해 계산
                    source_id = effect.source_id
                    damage_multiplier = effect.intensity if effect.intensity > 0 else 0.8
                    
                    # 시전자의 손패 수 기반 피해 (마술사 타임 봄)
                    hand_count = 5  # 기본값
                    all_enemies = []
                    try:
                        from src.combat.combat_manager import get_combat_manager
                        cm = get_combat_manager()
                        if cm:
                            # 시전자 찾기
                            for ally in getattr(cm, 'allies', []):
                                if getattr(ally, 'name', None) == source_id:
                                    hand_count = len(getattr(ally, 'card_hand', []))
                                    break
                            # 적 전체 목록 (살아있는 적만)
                            all_enemies = [e for e in getattr(cm, 'enemies', []) 
                                          if getattr(e, 'is_alive', True) and getattr(e, 'current_hp', 0) > 0]
                    except:
                        pass
                    
                    # 적 전체가 없으면 owner만 대상
                    if not all_enemies:
                        all_enemies = [self.owner]
                    
                    logger.warning(f"💣💣💣 [타임 봄 동시 폭발!] 손패 {hand_count}장 × {damage_multiplier} 배율")
                    
                    # 적 전체에게 동시 폭발 피해
                    for enemy in all_enemies:
                        max_hp = getattr(enemy, 'max_hp', 100)
                        explosion_damage = int(hand_count * damage_multiplier * max_hp * 0.1)
                        
                        # 피해 적용
                        if hasattr(enemy, 'take_damage'):
                            actual_damage = enemy.take_damage(explosion_damage, damage_type="magical")
                        else:
                            actual_damage = min(explosion_damage, getattr(enemy, 'current_hp', 0))
                            enemy.current_hp = max(0, enemy.current_hp - explosion_damage)
                        
                        enemy_name = getattr(enemy, 'name', 'Unknown')
                        logger.warning(f"  💥 {enemy_name}에게 {actual_damage} 피해!")
                        
                        # 사망 체크
                        if hasattr(enemy, 'current_hp') and enemy.current_hp <= 0:
                            enemy.is_alive = False
                            logger.warning(f"  ☠️ {enemy_name} 사망!")

                # 이벤트 발행
                event_bus.publish(Events.STATUS_REMOVED, {
                    "owner": self.owner_name,
                    "status": effect,
                    "expired": True
                })

        self.effects = self.status_effects
        return expired

    def process_dot_effects(self, target: Any) -> Dict[str, Any]:
        """
        지속 피해(DoT) 효과 처리

        턴마다 호출되어 독, 화상, 출혈 등의 DoT 데미지를 적용합니다.

        Args:
            target: DoT 피해를 받을 대상 (보통 self.owner와 동일)

        Returns:
            DoT 처리 결과 딕셔너리
            {
                "total_damage": int,  # 총 데미지
                "total_mp_drain": int,  # 총 MP 소모
                "effects": List[Dict]  # 각 DoT 효과 상세 정보
            }
        """
        # DoT 타입 정의
        dot_types = {
            StatusType.POISON: {"name": "독", "multiplier": 0.10, "icon": "☠️"},
            StatusType.BURN: {"name": "화상", "multiplier": 0.15, "icon": "🔥"},
            StatusType.BLEED: {"name": "출혈", "multiplier": 0.12, "icon": "🩸"},
            StatusType.CORRODE: {"name": "부식", "multiplier": 0.08, "icon": "🧪"},
            StatusType.CORROSION: {"name": "부식", "multiplier": 0.08, "icon": "🧪"},
            StatusType.DISEASE: {"name": "질병", "multiplier": 0.06, "icon": "🦠"},
            StatusType.NECROSIS: {"name": "괴사", "multiplier": 0.20, "icon": "💀"},
            StatusType.CHILL: {"name": "냉기", "multiplier": 0.05, "icon": "❄️"},
            StatusType.SHOCK: {"name": "감전", "multiplier": 0.12, "icon": "⚡"},
            StatusType.NATURE_CURSE: {"name": "자연저주", "multiplier": 0.10, "icon": "🌿"},
            # 아크메이지 융합 스킬 DoT
            StatusType.ELECTROCUTED: {"name": "감전", "multiplier": 0.20, "icon": "⚡"},  # 극한뇌전 감전
            StatusType.BURNING: {"name": "작열", "multiplier": 0.40, "icon": "🔥"},  # 원소 과부하 작열
        }

        total_damage = 0
        total_mp_drain = 0
        effect_details = []

        for effect in self.status_effects:
            if effect.status_type not in dot_types:
                continue

            dot_info = dot_types[effect.status_type]

            # metadata에서 base_damage 가져오기 (스킬 사용 시 계산된 값)
            base_damage = effect.metadata.get("base_damage", 0)

            # base_damage가 없으면 대상 최대 HP 기준으로 계산
            if base_damage == 0:
                # 대상의 최대 HP × 기본 배율 × intensity로 계산
                target_max_hp = getattr(target, 'max_hp', 1000)
                intensity_mult = effect.intensity if effect.intensity > 0 else 1.0
                base_damage = int(target_max_hp * dot_info["multiplier"] * intensity_mult)

            # 스택 수 적용
            damage = int(base_damage * effect.stack_count)

            # MP 소모 타입 처리
            if effect.status_type == StatusType.MP_DRAIN:
                mp_damage = damage // 2  # HP 데미지의 절반을 MP 소모로
                if hasattr(target, 'current_mp'):
                    actual_mp_drain = min(mp_damage, target.current_mp)
                    target.current_mp -= actual_mp_drain
                    total_mp_drain += actual_mp_drain

                    effect_details.append({
                        "name": "MP 소모",
                        "mp_drain": actual_mp_drain,
                        "icon": "💙"
                    })

                    logger.debug(f"{self.owner_name}: MP 소모 {actual_mp_drain}")

            # HP 데미지 적용
            if damage > 0:
                if hasattr(target, 'take_damage'):
                    actual_damage = target.take_damage(damage, is_dot=True)
                elif hasattr(target, 'current_hp'):
                    actual_damage = min(damage, target.current_hp)
                    target.current_hp = max(0, target.current_hp - actual_damage)
                else:
                    actual_damage = damage

                total_damage += actual_damage

                effect_details.append({
                    "name": dot_info["name"],
                    "damage": actual_damage,
                    "icon": dot_info["icon"],
                    "stacks": effect.stack_count
                })

                logger.debug(
                    f"{self.owner_name}: {dot_info['name']} 피해 {actual_damage} "
                    f"(스택: {effect.stack_count})"
                )

        # 이벤트 발행
        if total_damage > 0 or total_mp_drain > 0:
            event_bus.publish(Events.STATUS_DOT_DAMAGE, {
                "owner": self.owner_name,
                "total_damage": total_damage,
                "total_mp_drain": total_mp_drain,
                "effects": effect_details
            })

        return {
            "total_damage": total_damage,
            "total_mp_drain": total_mp_drain,
            "effects": effect_details
        }

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
            StatusType.TIME_STOP,
            StatusType.FROZEN_SOLID,  # 아크메이지 동결 (빙결 과부하)
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
                modifiers['physical_attack'] *= (1.0 + intensity * 0.25)
            elif effect.status_type == StatusType.BOOST_MAGIC_DEF:
                modifiers['magic_defense'] *= (1.0 + intensity * 0.25)
                modifiers['physical_defense'] *= (1.0 + intensity * 0.25)
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
            elif effect.status_type == StatusType.REDUCE_EVASION:
                modifiers['evasion'] *= (1.0 - intensity * 0.2)
            elif effect.status_type == StatusType.REDUCE_MAGIC_ATK:
                modifiers['magic_attack'] *= (1.0 - intensity * 0.25)
            elif effect.status_type == StatusType.REDUCE_MAGIC_DEF:
                modifiers['magic_defense'] *= (1.0 - intensity * 0.25)
            elif effect.status_type == StatusType.REDUCE_ALL_STATS:
                for key in modifiers:
                    modifiers[key] *= (1.0 - intensity * 0.15)

            # 특수 상태
            elif effect.status_type == StatusType.VULNERABLE:
                # intensity = 감소율 (기본 0.5 = 50% 감소)
                vuln_reduction = min(effect.intensity, 0.8)  # 최대 80% 감소
                modifiers['physical_defense'] *= max(1.0 - vuln_reduction, 0.1)
                modifiers['magic_defense'] *= max(1.0 - vuln_reduction, 0.1)
            elif effect.status_type == StatusType.EXPOSED:
                # intensity = 감소율 (기본 0.7 = 70% 감소)
                exposed_reduction = min(effect.intensity, 0.9)  # 최대 90% 감소
                modifiers['evasion'] *= max(1.0 - exposed_reduction, 0.05)
            elif effect.status_type == StatusType.WEAKNESS:
                # intensity = 감소율 (기본 0.3 = 30% 감소)
                weakness_reduction = min(effect.intensity, 0.5)  # 최대 50% 감소
                modifiers['physical_attack'] *= max(1.0 - weakness_reduction, 0.5)
                modifiers['magic_attack'] *= max(1.0 - weakness_reduction, 0.5)
            elif effect.status_type == StatusType.HASTE:
                # intensity = 증가율 (기본 0.5 = 50% 증가)
                haste_boost = min(effect.intensity, 1.0)  # 최대 100% 증가
                modifiers['speed'] *= (1.0 + haste_boost)
            elif effect.status_type == StatusType.SLOW:
                # intensity가 감소율 (0.5 = 50% 감소)
                # 둔화는 최대 50%까지만 적용 (사용자 요청)
                slow_reduction = min(effect.intensity, 0.5)  # 최대 50% 감소
                modifiers['speed'] *= max(1.0 - slow_reduction, 0.5)  # 최소 50% 속도 유지
            elif effect.status_type == StatusType.FOCUS:
                # intensity = 증가율 (기본 0.3 = 30% 증가)
                focus_boost_acc = min(effect.intensity * 0.3, 0.5)  # 최대 50% 증가
                focus_boost_crit = min(effect.intensity * 0.2, 0.4)  # 최대 40% 증가
                modifiers['accuracy'] *= (1.0 + focus_boost_acc)
                modifiers['critical_rate'] *= (1.0 + focus_boost_crit)
            elif effect.status_type == StatusType.RAGE:
                # intensity = 강도 (기본 1.0)
                rage_atk_boost = min(effect.intensity * 0.4, 0.8)  # 최대 80% 증가
                rage_def_reduction = min(effect.intensity * 0.2, 0.3)  # 최대 30% 감소
                modifiers['physical_attack'] *= (1.0 + rage_atk_boost)
                modifiers['magic_attack'] *= (1.0 + rage_atk_boost)
                modifiers['physical_defense'] *= max(1.0 - rage_def_reduction, 0.7)
                modifiers['magic_defense'] *= max(1.0 - rage_def_reduction, 0.7)
            elif effect.status_type == StatusType.BERSERK:
                # intensity = 강도 (기본 1.0)
                berserk_atk_boost = min(effect.intensity * 0.6, 1.0)  # 최대 100% 증가
                berserk_def_reduction = min(effect.intensity * 0.4, 0.5)  # 최대 50% 감소
                berserk_acc_reduction = min(effect.intensity * 0.2, 0.3)  # 최대 30% 감소
                modifiers['physical_attack'] *= (1.0 + berserk_atk_boost)
                modifiers['magic_attack'] *= (1.0 + berserk_atk_boost)
                modifiers['physical_defense'] *= max(1.0 - berserk_def_reduction, 0.5)
                modifiers['magic_defense'] *= max(1.0 - berserk_def_reduction, 0.5)
                modifiers['accuracy'] *= max(1.0 - berserk_acc_reduction, 0.7)
            elif effect.status_type == StatusType.BLIND:
                # intensity = 감소율 (기본 0.7 = 70% 감소)
                blind_reduction = min(effect.intensity, 0.9)  # 최대 90% 감소
                modifiers['accuracy'] *= max(1.0 - blind_reduction, 0.05)
            
            # === 아크메이지 융합 스킬 상태 효과 ===
            elif effect.status_type == StatusType.DEFENSE_SHATTER:
                # 방어 파쇄: 물리/마법 방어력 -30%
                shatter_reduction = min(effect.intensity, 0.5)  # 최대 50% 감소
                modifiers['physical_defense'] *= max(1.0 - shatter_reduction, 0.3)
                modifiers['magic_defense'] *= max(1.0 - shatter_reduction, 0.3)
            elif effect.status_type == StatusType.SLOWED:
                # 둔화: ATB 증가율 감소 (speed 배율로 처리)
                slow_amount = min(effect.intensity, 0.5)  # 최대 50% 감소
                modifiers['speed'] *= max(1.0 - slow_amount, 0.5)
            elif effect.status_type == StatusType.ELECTROCUTED:
                # 감전: ATB 증가율 -15% (speed 배율로 처리)
                modifiers['speed'] *= 0.85
            elif effect.status_type == StatusType.BURNING:
                # 작열: 화염 저항 감소 (magic_defense 사용)
                modifiers['magic_defense'] *= 0.70  # 화염 저항 -30%
            elif effect.status_type == StatusType.TERROR:
                # intensity = 감소율 (기본 0.4 = 40% 감소)
                terror_atk_reduction = min(effect.intensity * 0.4, 0.6)  # 최대 60% 감소
                terror_spd_reduction = min(effect.intensity * 0.3, 0.5)  # 최대 50% 감소
                modifiers['physical_attack'] *= max(1.0 - terror_atk_reduction, 0.4)
                modifiers['magic_attack'] *= max(1.0 - terror_atk_reduction, 0.4)
                modifiers['speed'] *= max(1.0 - terror_spd_reduction, 0.5)

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
        StatusType.REDUCE_ACCURACY, StatusType.REDUCE_EVASION, StatusType.REDUCE_ALL_STATS,
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
    
    # 아크메이지 융합 스킬
    StatusType.ELECTROCUTED: "⚡",
    StatusType.SLOWED: "🐌",
    StatusType.DEFENSE_SHATTER: "💔",
    StatusType.WOUND: "🩹",
    StatusType.BURNING: "🔥",
    StatusType.FROZEN_SOLID: "🧊",
    StatusType.FIRE_BRAND: "🔥",
    StatusType.ICE_BRAND: "❄️",
    StatusType.LIGHTNING_BRAND: "⚡",
    StatusType.FIRE_GLYPH: "🔥",
    StatusType.ICE_GLYPH: "❄️",
    StatusType.LIGHTNING_GLYPH: "⚡",
    StatusType.ELEMENTAL_AEGIS: "🛡️",
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
