"""
멀티플레이 설정 상수

문서의 구현 설정 값들을 정의합니다.
"""

from typing import Optional

# 전투 합류 관련
COMBAT_JOIN_ATB_INITIAL = 0  # 0부터 시작
COMBAT_JOIN_TIME_LIMIT: Optional[float] = None  # 제한 없음
COMBAT_JOIN_ENEMY_REACTION = "recalculate_threat"  # 위협 재계산

# 플레이어 수별 밸런스
ENEMY_COUNT_MULTIPLIER = 1.0  # 싱글과 동일
ENEMY_HP_MULTIPLIER = 1.0  # 싱글과 동일
ENEMY_DAMAGE_MULTIPLIER = 1.0  # 싱글과 동일
EXP_DIVIDE_BY_PARTICIPANTS = True  # 참여 전투원 수로 나눔
INVENTORY_WEIGHT_MULTIPLIER = 1.0  # 싱글과 동일

# 전투 시스템
ACTION_WAIT_TIME = 1.5  # 1.5초 고정
ATB_REDUCTION_MULTIPLIER = 0.02  # 1/50 고정
PARTICIPATION_RADIUS = 5  # 5 타일 고정

# 인벤토리 시스템
ITEM_USE_PERMISSION = "free"  # 자유 사용
ITEM_DISTRIBUTION = "shared_storage"  # 공유 저장
GOLD_MANAGEMENT = "fully_shared"  # 완전 공유

# 던전 생성
DUNGEON_SEED_SOURCE = "host"  # 호스트 생성
DUNGEON_SIZE_MODE = "fixed"  # 고정 크기

# 네트워크 및 성능
SYNC_INTERVAL_POSITION = 0.1  # 0.1초 (10 FPS)
SYNC_INTERVAL_STATE = 0.1  # 0.1초 (10 FPS)
SYNC_INTERVAL_ENEMY = 0.5  # 0.5초 (2 FPS)
MESSAGE_COMPRESSION = True  # 압축 사용
MAX_LATENCY_ALLOWED = 0.5  # 0.5초 (일반적)

# UI/UX
PLAYER_INFO_DISPLAY = "toggle"  # 토글 표시
CHAT_SYSTEM_TYPE = "text"  # 텍스트 채팅
PING_DISPLAY_TYPE = "color"  # 색상 표시

# 저장 및 재개
SESSION_SAVE_HOST_ONLY = True  # 호스트만 저장
SESSION_RESUME_HOST_ONLY = True  # 호스트만 재개

# 보안 및 치트 방지
INPUT_VALIDATION_LEVEL = "strict"  # 엄격한 검증
STATE_SYNC_MODE = "host_authority"  # 호스트 권위

# 모드별 특수 규칙
SPECIAL_RULES_2P = False  # 특수 규칙 없음
SPECIAL_RULES_3P = False  # 특수 규칙 없음
SPECIAL_RULES_4P = False  # 특수 규칙 없음


class MultiplayerConfig:
    """멀티플레이 설정 클래스"""
    
    # 전투 합류 관련
    combat_join_atb_initial = COMBAT_JOIN_ATB_INITIAL
    combat_join_time_limit = COMBAT_JOIN_TIME_LIMIT
    combat_join_enemy_reaction = COMBAT_JOIN_ENEMY_REACTION
    
    # 플레이어 수별 밸런스
    enemy_count_multiplier = ENEMY_COUNT_MULTIPLIER
    enemy_hp_multiplier = ENEMY_HP_MULTIPLIER
    enemy_damage_multiplier = ENEMY_DAMAGE_MULTIPLIER
    exp_divide_by_participants = EXP_DIVIDE_BY_PARTICIPANTS
    inventory_weight_multiplier = INVENTORY_WEIGHT_MULTIPLIER
    
    # 전투 시스템
    action_wait_time = ACTION_WAIT_TIME
    atb_reduction_multiplier = ATB_REDUCTION_MULTIPLIER
    participation_radius = PARTICIPATION_RADIUS
    
    # 인벤토리 시스템
    item_use_permission = ITEM_USE_PERMISSION
    item_distribution = ITEM_DISTRIBUTION
    gold_management = GOLD_MANAGEMENT
    
    # 던전 생성
    dungeon_seed_source = DUNGEON_SEED_SOURCE
    dungeon_size_mode = DUNGEON_SIZE_MODE
    
    # 네트워크 및 성능 (상수로도 접근 가능)
    SYNC_INTERVAL_POSITION = SYNC_INTERVAL_POSITION
    SYNC_INTERVAL_STATE = SYNC_INTERVAL_STATE
    SYNC_INTERVAL_ENEMY = SYNC_INTERVAL_ENEMY
    sync_interval_position = SYNC_INTERVAL_POSITION
    sync_interval_state = SYNC_INTERVAL_STATE
    sync_interval_enemy = SYNC_INTERVAL_ENEMY
    message_compression = MESSAGE_COMPRESSION
    max_latency_allowed = MAX_LATENCY_ALLOWED
    
    # UI/UX
    player_info_display = PLAYER_INFO_DISPLAY
    chat_system_type = CHAT_SYSTEM_TYPE
    ping_display_type = PING_DISPLAY_TYPE
    
    # 저장 및 재개
    session_save_host_only = SESSION_SAVE_HOST_ONLY
    session_resume_host_only = SESSION_RESUME_HOST_ONLY
    
    # 보안 및 치트 방지
    input_validation_level = INPUT_VALIDATION_LEVEL
    state_sync_mode = STATE_SYNC_MODE
    
    # 모드별 특수 규칙
    special_rules_2p = SPECIAL_RULES_2P
    special_rules_3p = SPECIAL_RULES_3P
    special_rules_4p = SPECIAL_RULES_4P

