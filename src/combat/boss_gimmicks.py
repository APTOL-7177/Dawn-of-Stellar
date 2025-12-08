"""
보스 전용 기믹 시스템

세피로스: 광기의 카운터 - 피해를 받으면 반격
카인: 시간의 심판 - 특정 조건 시 자동 발동하는 강력한 일격
"""

from typing import Any, Dict, List, Optional
from src.core.logger import get_logger

logger = get_logger("boss_gimmicks")


class BossGimmickSystem:
    """보스 전용 기믹 관리"""
    
    # 인코딩 깨짐 문자 세트 (실제 깨진 것처럼 보이게)
    CORRUPT_CHARS = "□▯▢?¿�☐■▪◾◼"
    GARBLE_CHARS = "ㅁㄴㅇㄹㅋㅎㅂㅈㄷㅅ"
    SYMBOL_CHARS = "@#$%&*!?"
    
    # 애니메이션용 캐시 - 깨질 위치를 고정 저장
    _corrupt_positions_cache: Dict[int, List[int]] = {}  # target_id -> [깨질 위치들]
    _extra_positions_cache: Dict[int, List[int]] = {}    # target_id -> [추가 문자 위치들]
    
    def __init__(self):
        # 카인: 시간의 심판 상태
        self.cain_judgment_ready = True  # 전투 시작 시 준비 완료
        self.cain_judgment_cooldown = 0
        self.cain_judgment_triggers = 0  # 발동 횟수
        
        # 카인: 시간의 낙인 시스템
        self.cain_marked_target = None  # 낙인이 찍힌 아군
        self.cain_mark_turn_counter = 0  # 낙인 주기 카운터
        self.cain_time_freeze_chance = 0.3  # 시간 정지 확률 30%
        self.cain_paradox_damage = 0.15  # 역설 피해 (행동 시 최대HP 15%)
        
        # 세피로스: 광기의 카운터 상태
        self.sephiroth_counter_stack = 0
        self.sephiroth_rage_mode = False
        
        # 세피로스: 광기의 표식 시스템
        self.sephiroth_marked_target = None  # 표식이 찍힌 아군
        self._mark_change_pending = False  # 표식 변경 예약 플래그
        self.sephiroth_mark_damage_amp = 0.5  # 표식 대상 피해 증폭 50%
        self.sephiroth_mark_dot_damage = 0.02  # 표식 대상 매턴 최대HP 2% 피해
        self.sephiroth_shared_pain_ratio = 0.2  # 공유 고통 피해 비율 20%
    
    def reset(self):
        """전투 시작 시 리셋"""
        self.cain_judgment_ready = True
        self.cain_judgment_cooldown = 0
        self.cain_judgment_triggers = 0
        self.cain_marked_target = None
        self.cain_mark_turn_counter = 0
        self.sephiroth_counter_stack = 0
        self.sephiroth_rage_mode = False
        self.sephiroth_marked_target = None
        self._mark_change_pending = False
    
    # ================================================================
    # 글리치 이름 효과
    # ================================================================
    
    @staticmethod
    def glitch_name(name: str, intensity: int = 2, use_color: bool = True) -> str:
        """
        이름에 인코딩 깨짐 효과 적용
        
        Args:
            name: 원본 이름
            intensity: 깨짐 강도 (1=약함, 2=보통, 3=강함)
            use_color: 빨간색 ANSI 코드 적용 여부
            
        강도별 효과:
            1: 1~2글자 깨짐
            2: 2~4글자 깨짐 + 추가 문자
            3: 4~6글자 깨짐 + 많은 추가 문자
        """
        import random
        
        result = list(name)  # 원본을 리스트로
        all_corrupt = BossGimmickSystem.CORRUPT_CHARS + BossGimmickSystem.GARBLE_CHARS + BossGimmickSystem.SYMBOL_CHARS
        
        # 강도에 따라 깨질 글자 수 결정
        if intensity == 1:
            num_corrupt = random.randint(1, max(1, min(2, len(name))))
            extra_chars = 0
        elif intensity == 2:
            num_corrupt = random.randint(1, max(1, min(4, len(name))))
            extra_chars = random.randint(1, 2)
        else:  # intensity >= 3
            num_corrupt = random.randint(1, max(1, min(6, len(name))))
            extra_chars = random.randint(2, 4)
        
        # 랜덤한 위치의 글자들을 깨진 문자로 대체
        if len(name) > 0:
            corrupt_positions = random.sample(range(len(name)), min(num_corrupt, len(name)))
            
            for pos in corrupt_positions:
                corrupt_type = random.randint(0, 2)
                if corrupt_type == 0:
                    result[pos] = random.choice(BossGimmickSystem.CORRUPT_CHARS)
                elif corrupt_type == 1:
                    result[pos] = random.choice(BossGimmickSystem.GARBLE_CHARS)
                else:
                    result[pos] = random.choice(BossGimmickSystem.SYMBOL_CHARS)
        
        # 추가 깨짐 문자 삽입
        for _ in range(extra_chars):
            insert_pos = random.randint(0, len(result))
            result.insert(insert_pos, random.choice(all_corrupt))
        
        glitched = ''.join(result)
        
        # 빨간색 ANSI 코드 적용
        if use_color:
            return f"\033[91m{glitched}\033[0m"
        return glitched
    
    @staticmethod
    def get_glitched_display_name(target: Any, use_color: bool = True) -> str:
        """표식/낙인 대상의 글리치된 이름 반환 (빨간색)"""
        name = getattr(target, 'name', 'Unknown')
        
        # 세피로스 표식 (강한 글리치)
        if hasattr(target, '_sephiroth_mark'):
            return BossGimmickSystem.glitch_name(name, intensity=3, use_color=use_color)
        
        # 카인 낙인 (보통 글리치)
        if hasattr(target, '_cain_mark'):
            return BossGimmickSystem.glitch_name(name, intensity=2, use_color=use_color)
        
        return name
    
    @staticmethod
    def get_animated_glitch_name(target: Any, frame_count: int = 0) -> str:
        """
        매 프레임마다 바뀌는 애니메이션 글리치 이름
        - 깨지는 위치는 고정 (표식 부여 시 결정)
        - 깨지는 문자만 매 프레임 변경 (애니메이션)
        - 멀쩡한 글자는 원본 유지
        
        Args:
            target: 대상 캐릭터
            frame_count: 현재 프레임 (사용 안함, 호환성용)
            
        Returns:
            빨간색 + 글리치된 이름
        """
        import random
        
        name = getattr(target, 'name', 'Unknown')
        target_id = id(target)
        
        # 표식/낙인 여부 확인
        if hasattr(target, '_sephiroth_mark'):
            intensity = 3
        elif hasattr(target, '_cain_mark'):
            intensity = 2
        else:
            return name  # 표식 없으면 원본 반환
        
        all_corrupt = BossGimmickSystem.CORRUPT_CHARS + BossGimmickSystem.GARBLE_CHARS + BossGimmickSystem.SYMBOL_CHARS
        
        # 깨질 위치가 캐시에 없으면 새로 생성 (표식 부여 시 1회)
        if target_id not in BossGimmickSystem._corrupt_positions_cache:
            if intensity == 1:
                num_corrupt = random.randint(1, max(1, min(2, len(name))))
                num_extra = 0
            elif intensity == 2:
                num_corrupt = random.randint(1, max(1, min(4, len(name))))
                num_extra = random.randint(1, 2)
            else:
                num_corrupt = random.randint(1, max(1, min(6, len(name))))
                num_extra = random.randint(2, 4)
            
            # 깨질 위치 고정 저장
            if len(name) > 0:
                BossGimmickSystem._corrupt_positions_cache[target_id] = random.sample(
                    range(len(name)), min(num_corrupt, len(name))
                )
            else:
                BossGimmickSystem._corrupt_positions_cache[target_id] = []
            
            # 추가 문자 삽입 위치 고정 저장
            BossGimmickSystem._extra_positions_cache[target_id] = [
                random.randint(0, len(name)) for _ in range(num_extra)
            ]
        
        # 캐시된 위치 사용
        corrupt_positions = BossGimmickSystem._corrupt_positions_cache.get(target_id, [])
        extra_positions = BossGimmickSystem._extra_positions_cache.get(target_id, [])
        
        # 결과 생성 - 깨지는 위치만 랜덤 문자, 나머지는 원본
        result = list(name)
        for pos in corrupt_positions:
            if pos < len(result):
                corrupt_type = random.randint(0, 2)
                if corrupt_type == 0:
                    result[pos] = random.choice(BossGimmickSystem.CORRUPT_CHARS)
                elif corrupt_type == 1:
                    result[pos] = random.choice(BossGimmickSystem.GARBLE_CHARS)
                else:
                    result[pos] = random.choice(BossGimmickSystem.SYMBOL_CHARS)
        
        # 추가 문자 삽입 (위치는 고정, 문자만 변경)
        for i, pos in enumerate(sorted(extra_positions, reverse=True)):
            adjusted_pos = min(pos + i, len(result))
            result.insert(adjusted_pos, random.choice(all_corrupt))
        
        glitched = ''.join(result)
        return f"\033[91m{glitched}\033[0m"
    
    @staticmethod
    def clear_glitch_cache(target: Any = None):
        """글리치 캐시 초기화 (표식 해제 시 호출)"""
        if target is None:
            BossGimmickSystem._corrupt_positions_cache.clear()
            BossGimmickSystem._extra_positions_cache.clear()
        else:
            target_id = id(target)
            BossGimmickSystem._corrupt_positions_cache.pop(target_id, None)
            BossGimmickSystem._extra_positions_cache.pop(target_id, None)
    
    @staticmethod
    def get_animated_glitch_for_ui(name: str, intensity: int = 2) -> tuple:
        """
        UI 렌더링용 애니메이션 글리치 (색상 포함)
        
        Args:
            name: 원본 이름
            intensity: 글리치 강도
            
        Returns:
            (글리치된 이름, RGB 색상) 튜플
        """
        import random
        
        result = list(name)
        all_corrupt = BossGimmickSystem.CORRUPT_CHARS + BossGimmickSystem.GARBLE_CHARS + BossGimmickSystem.SYMBOL_CHARS
        
        # 강도에 따라 깨질 글자 수 결정
        if intensity == 1:
            num_corrupt = random.randint(1, max(1, min(2, len(name))))
            extra_chars = 0
        elif intensity == 2:
            num_corrupt = random.randint(1, max(1, min(4, len(name))))
            extra_chars = random.randint(1, 2)
        else:
            num_corrupt = random.randint(1, max(1, min(6, len(name))))
            extra_chars = random.randint(2, 4)
        
        # 랜덤한 위치의 글자들을 깨진 문자로 대체
        if len(name) > 0:
            corrupt_positions = random.sample(range(len(name)), min(num_corrupt, len(name)))
            
            for pos in corrupt_positions:
                corrupt_type = random.randint(0, 2)
                if corrupt_type == 0:
                    result[pos] = random.choice(BossGimmickSystem.CORRUPT_CHARS)
                elif corrupt_type == 1:
                    result[pos] = random.choice(BossGimmickSystem.GARBLE_CHARS)
                else:
                    result[pos] = random.choice(BossGimmickSystem.SYMBOL_CHARS)
        
        # 추가 깨짐 문자 삽입
        for _ in range(extra_chars):
            insert_pos = random.randint(0, len(result))
            result.insert(insert_pos, random.choice(all_corrupt))
        
        glitched = ''.join(result)
        
        # 빨간색 계열 랜덤 색상 (애니메이션 효과)
        red = random.randint(180, 255)
        green = random.randint(0, 60)
        blue = random.randint(0, 60)
        
        return (glitched, (red, green, blue))
    
    @staticmethod
    def should_show_glitched(target: Any) -> bool:
        """대상이 글리치 표시 대상인지 확인"""
        return hasattr(target, '_sephiroth_mark') or hasattr(target, '_cain_mark')
    
    # ================================================================
    # 기믹 대사 시스템
    # ================================================================
    
    GIMMICK_DIALOGUES = {
        # 세피로스 대사
        "sephiroth_mark": [
            "「{name}... 네가 나의 고통을 나눠 가져라...」",
            "「{name}... 광기가 너를 선택했다...」",
            "「{name}... 도망칠 수 없어...」",
        ],
        "sephiroth_shared_pain": [
            "「고통을 나눠라...」",
            "「함께... 무너져라...」",
            "「너희 모두... 광기 속으로...」",
        ],
        "sephiroth_counter": [
            "「...허무하구나...」",
            "「...부질없어...」",
        ],
        "sephiroth_rage_mode": [
            "「아아아아아아아!!!」",
            "「더 이상... 참지 않겠다!!!」",
        ],
        
        # 카인 대사
        "cain_mark": [
            "「{name}... 시간이 너를 선택했다.」",
            "「{name}... 네 시간은 내 것이다.」",
            "「{name}... 시간의 굴레에서 벗어날 수 없다.」",
        ],
        "cain_paradox": [
            "「시간의 역설... 네 행동이 너를 갉아먹는다.」",
            "「과거와 미래가 충돌한다...」",
        ],
        "cain_time_freeze": [
            "「시간이여, 멈춰라.」",
            "「...정지.」",
        ],
        "cain_judgment": [
            "「시간이 널 심판한다...」",
            "「시간의 끝에서 심판을 받아라.」",
        ],
    }
    
    @staticmethod
    def get_dialogue(dialogue_type: str, **kwargs) -> str:
        """기믹 대사 가져오기"""
        import random
        dialogues = BossGimmickSystem.GIMMICK_DIALOGUES.get(dialogue_type, [])
        if not dialogues:
            return ""
        dialogue = random.choice(dialogues)
        return dialogue.format(**kwargs) if kwargs else dialogue
    
    # ================================================================
    # 카인: 시간의 심판 (Time Judgment)
    # ================================================================
    
    def check_cain_judgment_trigger(self, cain: Any, allies: List[Any], context: Dict) -> Optional[Dict]:
        """
        카인의 '시간의 심판' 발동 조건 체크

        발동 조건:
        1. 전투 시작 직후 (첫 턴)
        2. 15턴마다 자동 발동
        
        Returns:
            발동 시 공격 정보 딕셔너리, 미발동 시 None
        """
        if not cain or not getattr(cain, 'is_alive', False):
            return None
        
        # 쿨다운 체크
        if self.cain_judgment_cooldown > 0:
            return None
        
        trigger_reason = None
        
        # 조건 1: 전투 시작 (첫 발동)
        if self.cain_judgment_triggers == 0 and self.cain_judgment_ready:
            trigger_reason = "전투 개시"
            self.cain_judgment_ready = False
        
        # 조건 2: 15턴마다 자동 발동
        elif context.get('turn_count', 0) > 0 and context.get('turn_count', 0) % 15 == 0:
            if context.get('is_turn_start'):
                trigger_reason = "시간의 순환"

        if trigger_reason:
            self.cain_judgment_triggers += 1
            self.cain_judgment_cooldown = 15  # 15턴 쿨다운
            
            # 발동 횟수에 따라 위력 소폭 증가
            power_mult = 1.0 + (self.cain_judgment_triggers - 1) * 0.1  # 발동마다 10% 증가
            
            logger.info(f"[시간의 심판] 발동! 이유: {trigger_reason} (위력: {power_mult:.0%})")
            
            return {
                "skill_name": "시간의 심판",
                "trigger_reason": trigger_reason,
                "damage_multiplier": 1.0 * power_mult,  # 3.5 → 1.0 대폭 감소
                "target_type": "random_ally",  # 랜덤 아군 1명
                "is_hp_attack": True,
                "message": f"「시간이 널 심판한다...」",
                "effects": {
                    "atb_reduce": 0.3,  # 대상 ATB 30% 감소 (50% → 30%)
                    "slow_duration": 1  # 1턴 둔화 (2턴 → 1턴)
                }
            }
        
        return None
    
    def on_cain_turn_end(self):
        """카인 턴 종료 시 쿨다운 감소"""
        if self.cain_judgment_cooldown > 0:
            self.cain_judgment_cooldown -= 1
    
    # ================================================================
    # 세피로스: 광기의 카운터 (Madness Counter)
    # ================================================================
    
    def on_sephiroth_damaged(self, sephiroth: Any, damage: int, attacker: Any) -> Optional[Dict]:
        """
        세피로스가 피해를 받을 때 호출
        
        기믹:
        1. 피해를 받을 때마다 광기 스택 +1
        2. 스택 3 도달 시 즉시 반격 발동
        3. HP 30% 이하면 광기 모드 돌입 (모든 공격에 반격)
        
        Returns:
            반격 정보 딕셔너리, 미발동 시 None
        """
        if not sephiroth or not getattr(sephiroth, 'is_alive', False):
            return None
        
        # 광기 스택 증가
        self.sephiroth_counter_stack += 1
        
        # HP 체크 - 30% 이하면 광기 모드
        hp_ratio = getattr(sephiroth, 'current_hp', 0) / max(1, getattr(sephiroth, 'max_hp', 1))
        if hp_ratio <= 0.3 and not self.sephiroth_rage_mode:
            self.sephiroth_rage_mode = True
            logger.info("[광기 모드] 세피로스의 광기가 폭주한다!")
        
        counter_attack = None
        
        # 광기 모드: 모든 공격에 즉시 반격 (피해량 감소)
        if self.sephiroth_rage_mode:
            counter_attack = {
                "skill_name": "광기의 반격",
                "damage_multiplier": 0.15,  # 광기 모드 반격 15%
                "target": attacker,
                "is_hp_attack": False,  # BRV 공격
                "message": "「...허무하구나...」",
                "effects": {}
            }
            logger.info(f"[광기의 반격] {attacker.name}에게 즉시 반격!")
        
        # 일반 모드: 스택 3 도달 시 반격 + 표식 변경
        elif self.sephiroth_counter_stack >= 3:
            self.sephiroth_counter_stack = 0  # 스택 리셋
            self._mark_change_pending = True  # 표식 변경 예약
            
            counter_attack = {
                "skill_name": "어둠의 일섬",
                "damage_multiplier": 0.2,  # 반격 피해 20%
                "target": attacker,
                "is_hp_attack": True,  # HP 공격
                "message": "「그 정도로는 부족해...」",
                "effects": {
                    "defense_down": 0.15,  # 방어력 15% 감소
                    "duration": 2
                }
            }
            logger.info(f"[어둠의 일섬] 광기 스택 3 도달! {attacker.name}에게 반격!")
        
        # 스택 상태 로그 (증가할 때마다)
        logger.info(f"[광기 스택] {self.sephiroth_counter_stack}/3")
        
        return counter_attack
    
    # ================================================================
    # 세피로스: 광기의 표식 (Mark of Madness)
    # ================================================================
    
    def update_sephiroth_mark(self, sephiroth: Any, allies: List[Any]) -> Optional[Dict]:
        """
        세피로스의 표식 시스템 업데이트 (매 턴 호출)
        
        - 광기 스택 3 도달 시 표식 대상 변경
        - 처음엔 자동 부여
        - 기존 표식 대상이 바뀌면 이전 표식 제거
        
        Returns:
            표식 변경 정보 또는 None
        """
        if not sephiroth or not getattr(sephiroth, 'is_alive', False):
            return None
        
        # 표식 변경 조건: 처음이거나 광기 스택 3 도달 시 (_mark_change_pending)
        should_change = False
        
        # 처음 표식 부여 (아직 표식 대상이 없을 때)
        if self.sephiroth_marked_target is None:
            should_change = True
        # 광기 스택 3 도달로 인한 표식 변경
        elif getattr(self, '_mark_change_pending', False):
            should_change = True
            self._mark_change_pending = False
        
        # 죽은 아군의 표식 제거
        for ally in allies:
            if not getattr(ally, 'is_alive', True) and hasattr(ally, '_sephiroth_mark'):
                delattr(ally, '_sephiroth_mark')
                BossGimmickSystem.clear_glitch_cache(ally)
                if self.sephiroth_marked_target == ally:
                    self.sephiroth_marked_target = None
                    should_change = True  # 표식 대상이 죽으면 새 대상 선택
        
        if should_change:
            
            # 살아있는 아군 필터링
            alive_allies = [a for a in allies if getattr(a, 'is_alive', True)]
            if not alive_allies:
                return None
            
            import random
            
            # 이전 표식 대상 저장
            old_target = self.sephiroth_marked_target
            
            # 모든 아군의 표식 제거 (중복 방지)
            for ally in allies:
                if hasattr(ally, '_sephiroth_mark'):
                    delattr(ally, '_sephiroth_mark')
                    BossGimmickSystem.clear_glitch_cache(ally)
            
            # 새 표식 대상 선택 (가능하면 이전과 다른 대상)
            if len(alive_allies) > 1 and old_target in alive_allies:
                candidates = [a for a in alive_allies if a != old_target]
                new_target = random.choice(candidates)
            else:
                new_target = random.choice(alive_allies)
            
            # 새 표식 부여
            self.sephiroth_marked_target = new_target
            new_target._sephiroth_mark = True
            
            logger.info(f"[광기의 표식] {new_target.name}에게 표식 부여!")
            logger.info(f"  → 받는 피해 +50%, 매턴 HP 2%")
            logger.info(f"  → 세피로스 공격 시 아군 전체 피해!")
            
            return {
                "old_target": old_target,
                "new_target": new_target,
                "message": f"「{new_target.name}... 네가 나의 고통을 나눠 가져라...」"
            }
        
        return None
    
    def process_mark_dot_damage(self, marked_target: Any) -> Optional[Dict]:
        """표식 대상에게 주기적 피해"""
        if not marked_target or not getattr(marked_target, 'is_alive', True):
            return None
        
        if not hasattr(marked_target, '_sephiroth_mark'):
            return None
        
        max_hp = getattr(marked_target, 'max_hp', 1000)
        dot_damage = int(max_hp * self.sephiroth_mark_dot_damage)
        
        if hasattr(marked_target, 'take_damage'):
            actual_damage = marked_target.take_damage(dot_damage, is_dot=True)
        else:
            actual_damage = dot_damage
            marked_target.current_hp = max(0, marked_target.current_hp - dot_damage)
        
        logger.info(f"[광기의 표식] {marked_target.name}에게 {actual_damage} 지속 피해!")
        
        return {
            "target": marked_target,
            "damage": actual_damage
        }
    
    def get_mark_damage_amplification(self, target: Any) -> float:
        """표식 대상의 피해 증폭률 반환"""
        if target and hasattr(target, '_sephiroth_mark'):
            return self.sephiroth_mark_damage_amp
        return 0.0
    
    def check_shared_pain(self, attacker: Any, damage: int, allies: List[Any]) -> Optional[Dict]:
        """
        공유 고통 체크 - 표식 대상이 세피로스 공격 시 아군 전체 피해
        
        Args:
            attacker: 공격자 (표식 대상인지 확인)
            damage: 입힌 피해량
            allies: 모든 아군 리스트
            
        Returns:
            공유 피해 정보 또는 None
        """
        if not hasattr(attacker, '_sephiroth_mark'):
            return None
        
        # 공유 피해 계산
        shared_damage = int(damage * self.sephiroth_shared_pain_ratio)
        if shared_damage <= 0:
            return None
        
        logger.info(f"[공유 고통] {attacker.name}의 공격! 아군 {len(allies)}명에게 {shared_damage} 피해 분배")
        
        damaged_allies = []
        for ally in allies:
            is_alive = getattr(ally, 'is_alive', True)
            is_self = (ally == attacker) or (ally.name == attacker.name)
            logger.info(f"[공유 고통] {ally.name}: alive={is_alive}, self={is_self}, hp={getattr(ally, 'current_hp', '?')}")
            
            if not is_alive:
                continue
            if is_self:
                continue  # 자기 자신은 제외
            
            # 직접 HP 감소 (take_damage는 다른 효과 트리거할 수 있음)
            before_hp = getattr(ally, 'current_hp', 0)
            actual = min(shared_damage, before_hp)
            if hasattr(ally, 'current_hp'):
                ally.current_hp = max(0, ally.current_hp - actual)
            after_hp = getattr(ally, 'current_hp', 0)
            
            damaged_allies.append({"name": ally.name, "damage": actual})
            logger.info(f"  → {ally.name}: {before_hp} → {after_hp} ({actual} 피해)")
        
        return {
            "shared_damage": shared_damage,
            "damaged_allies": damaged_allies,
            "message": "「고통을 나눠라...」"
        }
    
    def is_marked(self, target: Any) -> bool:
        """대상이 세피로스 표식 상태인지 확인"""
        return hasattr(target, '_sephiroth_mark')
    
    # ================================================================
    # 카인: 시간의 낙인 (Time Brand)
    # ================================================================
    
    def update_cain_mark(self, cain: Any, allies: List[Any], force_change: bool = False) -> Optional[Dict]:
        """
        카인의 시간의 낙인 시스템 업데이트
        
        변경 조건:
        - 심판 발동 시 (force_change=True)
        - 낙인 대상이 죽었을 때
        - 아직 낙인이 없을 때 (첫 부여)
        
        Returns:
            낙인 변경 정보 또는 None
        """
        if not cain or not getattr(cain, 'is_alive', False):
            return None
        
        should_change = force_change
        
        # 낙인 대상이 죽었으면 변경
        if self.cain_marked_target and not getattr(self.cain_marked_target, 'is_alive', True):
            should_change = True
        
        # 아직 낙인이 없으면 첫 부여
        if self.cain_marked_target is None:
            should_change = True
        
        if should_change:
            self.cain_mark_turn_counter = 0
            
            # 살아있는 아군 필터링
            alive_allies = [a for a in allies if getattr(a, 'is_alive', True)]
            if not alive_allies:
                return None
            
            import random
            
            # 이전 낙인 대상 저장
            old_target = self.cain_marked_target
            
            # 새 낙인 대상 선택 (가능하면 이전과 다른 대상)
            if len(alive_allies) > 1 and old_target in alive_allies:
                candidates = [a for a in alive_allies if a != old_target]
                new_target = random.choice(candidates)
            else:
                new_target = random.choice(alive_allies)
            
            # 이전 낙인 제거
            if old_target and hasattr(old_target, '_cain_mark'):
                delattr(old_target, '_cain_mark')
                BossGimmickSystem.clear_glitch_cache(old_target)  # 글리치 캐시 초기화
                logger.info(f"[시간의 낙인] {old_target.name}의 낙인 해제됨")
            
            # 새 낙인 부여
            self.cain_marked_target = new_target
            new_target._cain_mark = True
            
            # 글리치된 이름
            glitched_name = self.glitch_name(new_target.name, intensity=2)
            
            logger.info(f"[시간의 낙인] {glitched_name}에게 낙인 부여!")
            logger.info(f"  → 행동 시 최대HP {self.cain_paradox_damage*100:.0f}% 역설 피해")
            logger.info(f"  → {self.cain_time_freeze_chance*100:.0f}% 확률로 시간 정지")
            
            dialogue = self.get_dialogue("cain_mark", name=glitched_name)
            
            return {
                "old_target": old_target,
                "new_target": new_target,
                "glitched_name": glitched_name,
                "message": dialogue
            }
        
        return None
    
    def check_cain_paradox(self, actor: Any) -> Optional[Dict]:
        """
        시간의 역설 체크 - 낙인 대상이 행동할 때 피해
        
        Args:
            actor: 행동하는 캐릭터
            
        Returns:
            역설 피해 정보 또는 None
        """
        if not hasattr(actor, '_cain_mark'):
            return None
        
        import random
        
        max_hp = getattr(actor, 'max_hp', 1000)
        paradox_damage = int(max_hp * self.cain_paradox_damage)
        
        # 피해 적용
        if hasattr(actor, 'take_damage'):
            actual_damage = actor.take_damage(paradox_damage)
        else:
            actual_damage = min(paradox_damage, actor.current_hp)
            actor.current_hp = max(0, actor.current_hp - actual_damage)
        
        glitched_name = self.glitch_name(actor.name, intensity=2)
        dialogue = self.get_dialogue("cain_paradox")
        
        logger.info(f"[시간의 역설] {glitched_name}에게 {actual_damage} 피해!")
        
        result = {
            "target": actor,
            "damage": actual_damage,
            "glitched_name": glitched_name,
            "message": dialogue,
            "time_frozen": False
        }
        
        # 시간 정지 확률 체크
        if random.random() < self.cain_time_freeze_chance:
            # ATB 0으로 설정
            if hasattr(actor, 'atb'):
                actor.atb = 0
            
            dialogue_freeze = self.get_dialogue("cain_time_freeze")
            result["time_frozen"] = True
            result["freeze_message"] = dialogue_freeze
            logger.info(f"[시간 정지] {glitched_name}의 시간이 멈췄다!")
        
        return result
    
    def is_cain_marked(self, target: Any) -> bool:
        """대상이 카인 낙인 상태인지 확인"""
        return hasattr(target, '_cain_mark')
    
    def get_sephiroth_status(self) -> Dict:
        """세피로스 기믹 상태 반환"""
        return {
            "counter_stack": self.sephiroth_counter_stack,
            "rage_mode": self.sephiroth_rage_mode
        }
    
    def get_cain_status(self) -> Dict:
        """카인 기믹 상태 반환"""
        return {
            "judgment_ready": self.cain_judgment_ready,
            "judgment_cooldown": self.cain_judgment_cooldown,
            "judgment_triggers": self.cain_judgment_triggers
        }


# 싱글톤 인스턴스
_boss_gimmick_system: Optional[BossGimmickSystem] = None


def get_boss_gimmick_system() -> BossGimmickSystem:
    """보스 기믹 시스템 인스턴스 반환"""
    global _boss_gimmick_system
    if _boss_gimmick_system is None:
        _boss_gimmick_system = BossGimmickSystem()
    return _boss_gimmick_system


def reset_boss_gimmicks():
    """보스 기믹 리셋 (전투 시작 시 호출)"""
    system = get_boss_gimmick_system()
    system.reset()
