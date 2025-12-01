"""
게임 상태 내보내기 - 봇 클라이언트용

게임 상태를 JSON 파일로 내보내서 외부 봇이 읽을 수 있게 함

활성화 방법:
1. AI 관전 모드 실행 (자동 활성화)
2. 환경 변수: BOT_EXPORT=1
3. 파일 생성: user_data/enable_bot.txt
4. 코드에서: from src.bot import enable_export; enable_export(True)
"""

import os
import json
import time
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Any, Dict, List
from dataclasses import dataclass, asdict
from threading import Lock

from src.core.logger import get_logger

logger = get_logger("bot_exporter")

# 공유 파일 경로
USER_DATA = Path(__file__).parent.parent.parent / "user_data"
STATE_FILE = USER_DATA / "bot_state.json"
COMMAND_FILE = USER_DATA / "bot_command.json"
ENABLE_FILE = USER_DATA / "enable_bot.txt"

# 상태 내보내기 활성화 여부 (환경 변수 또는 파일로 자동 활성화)
_export_enabled = os.environ.get('BOT_EXPORT', '0') == '1' or ENABLE_FILE.exists()
_last_export_time = 0
_export_interval = 0.05  # 50ms 간격 (더 빠른 반응)
_write_lock = Lock()  # 파일 쓰기 동기화

def enable_export(enabled: bool = True):
    """상태 내보내기 활성화/비활성화"""
    global _export_enabled
    _export_enabled = enabled
    logger.info(f"봇 상태 내보내기: {'활성화' if enabled else '비활성화'}")
    
    # 디렉토리 생성 및 활성화 파일 생성
    if enabled:
        USER_DATA.mkdir(parents=True, exist_ok=True)
        # 활성화 파일 생성 (다음 게임 실행 시 자동 활성화)
        ENABLE_FILE.touch()
    elif ENABLE_FILE.exists():
        ENABLE_FILE.unlink()


def is_export_enabled() -> bool:
    """내보내기 활성화 여부"""
    return _export_enabled


def export_combat_state(combat_manager: Any, current_char: Any = None, screen_text: str = "", ui_state: str = "", party: List[Any] = None):
    """전투 상태 내보내기"""
    if not _export_enabled:
        return
    
    global _last_export_time
    now = time.time()
    if now - _last_export_time < _export_interval:
        return
    _last_export_time = now
    
    try:
        allies = []
        # combat_manager.allies 또는 party 사용 (둘 다 시도)
        cm_allies = getattr(combat_manager, 'allies', [])
        if not cm_allies and party:
            cm_allies = party
        for c in cm_allies:
            # BRV 값 올바르게 가져오기
            current_brv = getattr(c, 'current_brv', 0)
            max_brv = getattr(c, 'max_brv', 100)
            # max_brv가 너무 낮으면 기본값 사용 (property 문제 대비)
            if max_brv < 50:
                max_brv = 100
            
            allies.append({
                'name': c.name,
                'job': getattr(c, 'job_id', 'unknown'),
                'hp': c.current_hp,
                'max_hp': c.max_hp,
                'mp': getattr(c, 'current_mp', 0),
                'max_mp': getattr(c, 'max_mp', 1),
                'brv': current_brv,
                'max_brv': max_brv,
                'is_alive': c.is_alive,
                'is_broken': getattr(c, 'is_broken', False)
            })
        
        enemies = []
        enemy_list = getattr(combat_manager, 'enemies', [])
        
        # 같은 이름 적에 A, B, C... 접미사 붙이기
        name_counts = {}
        for e in enemy_list:
            base_name = e.name
            if base_name not in name_counts:
                name_counts[base_name] = 0
            name_counts[base_name] += 1
        
        name_used = {}
        for e in enemy_list:
            base_name = e.name
            # 같은 이름이 2개 이상이면 접미사 붙이기
            if name_counts[base_name] > 1:
                if base_name not in name_used:
                    name_used[base_name] = 0
                suffix = chr(ord('A') + name_used[base_name])  # A, B, C...
                display_name = f"{base_name} {suffix}"
                name_used[base_name] += 1
            else:
                display_name = base_name
            
            # 적 BRV 값
            e_brv = getattr(e, 'current_brv', getattr(e, 'brv', 0))
            e_max_brv = getattr(e, 'max_brv', 100)
            if e_max_brv < 50:
                e_max_brv = 100
            
            enemies.append({
                'name': display_name,
                'hp': e.current_hp,
                'max_hp': e.max_hp,
                'brv': e_brv,
                'max_brv': e_max_brv,
                'is_alive': e.is_alive,
                'is_broken': getattr(e, 'is_broken', False)
            })
        
        # 스킬 정보 추출
        skills = []
        if current_char and hasattr(current_char, 'skills'):
            for s in current_char.skills[:8]:  # 상위 8개로 확대
                # can_use 체크
                can_use = True
                if hasattr(s, 'can_use'):
                    try:
                        can_use, _ = s.can_use(current_char)
                    except:
                        pass
                
                # 비용 정보
                mp_cost = 0
                for cost in getattr(s, 'costs', []):
                    if hasattr(cost, 'amount'):
                        mp_cost = cost.amount
                        break
                
                skills.append({
                    'id': getattr(s, 'skill_id', getattr(s, 'id', '')),
                    'name': getattr(s, 'name', ''),
                    'mp_cost': mp_cost,
                    'description': getattr(s, 'description', '')[:80],
                    'skill_type': getattr(s, 'category', 'attack'),
                    'enabled': can_use
                })
        
        state = {
            'mode': 'combat',
            'turn': getattr(combat_manager, 'turn_count', 0),
            'current_actor': current_char.name if current_char else '',
            'allies': allies,
            'enemies': enemies,
            'skills': skills,
            'ui_state': ui_state,
            'screen_text': screen_text,
            'timestamp': now
        }
        
        _write_state(state)
        
    except Exception as e:
        logger.error(f"전투 상태 내보내기 실패: {e}")


def export_exploration_state(
    exploration_sys: Any,
    party: List[Any],
    dungeon: Any,
    screen_text: str = ""
):
    """탐험 상태 내보내기"""
    if not _export_enabled:
        return
    
    global _last_export_time
    now = time.time()
    if now - _last_export_time < _export_interval:
        return
    _last_export_time = now
    
    try:
        px, py = exploration_sys.player.x, exploration_sys.player.y
        
        # 계단 위치
        stairs = None
        if hasattr(dungeon, 'stairs_down') and dungeon.stairs_down:
            stairs = list(dungeon.stairs_down)
        
        # 주변 이동 가능한 방향 (벽 감지)
        walkable_dirs = []
        directions = {'up': (0, -1), 'down': (0, 1), 'left': (-1, 0), 'right': (1, 0)}
        for dir_name, (dx, dy) in directions.items():
            nx, ny = px + dx, py + dy
            try:
                # 맵 범위 체크
                width = getattr(dungeon, 'width', 100)
                height = getattr(dungeon, 'height', 100)
                if 0 <= nx < width and 0 <= ny < height:
                    is_walkable = False
                    # tiles 배열 접근
                    if hasattr(dungeon, 'tiles'):
                        tile = dungeon.tiles[nx][ny]
                        if hasattr(tile, 'walkable'):
                            is_walkable = tile.walkable
                        elif hasattr(tile, 'blocked'):
                            is_walkable = not tile.blocked
                        else:
                            is_walkable = True  # 알 수 없으면 이동 가능 가정
                    # is_walkable 메서드
                    elif hasattr(dungeon, 'is_walkable'):
                        is_walkable = dungeon.is_walkable(nx, ny)
                    else:
                        is_walkable = True  # 기본 이동 가능
                    
                    if is_walkable:
                        walkable_dirs.append(dir_name)
            except Exception:
                walkable_dirs.append(dir_name)  # 오류 시 이동 가능 가정
        
        # 모두 실패하면 전부 허용
        if not walkable_dirs:
            walkable_dirs = ['up', 'down', 'left', 'right']
        
        # 근처 적
        nearby_enemies = []
        if hasattr(exploration_sys, 'enemies'):
            for e in exploration_sys.enemies:
                if hasattr(e, 'x') and hasattr(e, 'y'):
                    dist = abs(e.x - px) + abs(e.y - py)
                    if dist <= 15:
                        nearby_enemies.append({
                            'name': getattr(e, 'name', 'enemy'),
                            'pos': [e.x, e.y],
                            'distance': dist,
                            'level': getattr(e, 'level', 1),
                            'is_boss': getattr(e, 'is_boss', False)
                        })
        
        # 힐링 포인트 / 특수 오브젝트
        healing_points = []
        items = []
        interactables = []
        
        # 던전에서 특수 타일 찾기
        if hasattr(dungeon, 'tiles'):
            for x in range(max(0, px - 10), min(getattr(dungeon, 'width', 100), px + 11)):
                for y in range(max(0, py - 10), min(getattr(dungeon, 'height', 100), py + 11)):
                    try:
                        tile = dungeon.tiles[x][y]
                        # 힐링 포인트
                        if hasattr(tile, 'is_healing') and tile.is_healing:
                            healing_points.append([x, y])
                        elif hasattr(tile, 'tile_type') and 'heal' in str(tile.tile_type).lower():
                            healing_points.append([x, y])
                    except:
                        pass
        
        # 탐험 시스템에서 아이템 찾기
        if hasattr(exploration_sys, 'items'):
            for item in exploration_sys.items:
                if hasattr(item, 'x') and hasattr(item, 'y'):
                    dist = abs(item.x - px) + abs(item.y - py)
                    if dist <= 15:
                        items.append({
                            'name': getattr(item, 'name', 'item'),
                            'pos': [item.x, item.y],
                            'distance': dist
                        })
        
        # 상호작용 가능 오브젝트
        if hasattr(exploration_sys, 'interactables'):
            for obj in exploration_sys.interactables:
                if hasattr(obj, 'x') and hasattr(obj, 'y'):
                    dist = abs(obj.x - px) + abs(obj.y - py)
                    if dist <= 15:
                        interactables.append({
                            'type': getattr(obj, 'type', 'object'),
                            'pos': [obj.x, obj.y],
                            'distance': dist
                        })
        
        # 파티 상태
        party_info = []
        for c in party:
            party_info.append({
                'name': c.name,
                'hp_pct': int(c.current_hp / c.max_hp * 100) if c.max_hp > 0 else 0,
                'mp_pct': int(getattr(c, 'current_mp', 0) / getattr(c, 'max_mp', 1) * 100)
            })
        
        # 인벤토리 정보 추출
        inventory_items = []
        equipment_upgrades = []  # 더 좋은 장비가 있는지
        healing_items = []  # 회복 아이템
        destroyable_items = []  # 파괴 가능한 아이템 (안 쓰는 장비 등)
        current_weight = 0.0
        max_weight = 10.0
        
        if hasattr(exploration_sys, 'inventory') or hasattr(exploration_sys, 'game'):
            inv = getattr(exploration_sys, 'inventory', None)
            if not inv and hasattr(exploration_sys, 'game'):
                inv = getattr(exploration_sys.game, 'inventory', None)
            
            if inv:
                # 무게 정보
                current_weight = getattr(inv, 'current_weight', 0.0)
                max_weight = getattr(inv, 'max_weight', 10.0)
                
                # 슬롯에서 아이템 추출
                slots = getattr(inv, 'slots', [])
                for idx, slot in enumerate(slots[:30]):  # 상위 30개만
                    item = getattr(slot, 'item', slot)
                    quantity = getattr(slot, 'quantity', 1)
                    
                    item_weight = getattr(item, 'weight', 0.5)
                    item_type = getattr(item, 'item_type', getattr(item, 'type', 'misc'))
                    item_name = getattr(item, 'name', '')
                    is_equipped = getattr(item, 'equipped', False)
                    
                    item_info = {
                        'name': item_name,
                        'type': str(item_type),
                        'quantity': quantity,
                        'equipped': is_equipped,
                        'weight': item_weight,
                        'total_weight': item_weight * quantity,
                        'index': idx
                    }
                    inventory_items.append(item_info)
                    
                    # 회복 아이템 분류
                    item_type_str = str(item_type).lower()
                    item_name_lower = item_name.lower()
                    if 'potion' in item_type_str or '포션' in item_name_lower or '회복' in item_name_lower or 'heal' in item_name_lower:
                        healing_items.append(item_info)
                    
                    # 파괴 가능 아이템 분류 (장착 안 된 장비)
                    if not is_equipped and ('equipment' in item_type_str or 'weapon' in item_type_str or 
                                           'armor' in item_type_str or '검' in item_name_lower or 
                                           '갑옷' in item_name_lower or '방패' in item_name_lower or
                                           '투구' in item_name_lower or '장갑' in item_name_lower):
                        destroyable_items.append(item_info)
        
        # 파괴 가능 아이템을 무게 순으로 정렬 (무거운 것 먼저)
        destroyable_items.sort(key=lambda x: x.get('total_weight', 0), reverse=True)
        
        # 파티 HP% 계산
        avg_hp_pct = sum(p['hp_pct'] for p in party_info) / len(party_info) if party_info else 100
        
        state = {
            'mode': 'exploration',
            'player_pos': [px, py],
            'stairs_pos': stairs,
            'walkable_dirs': walkable_dirs,
            'nearby_enemies': nearby_enemies,
            'healing_points': healing_points,
            'items': items,
            'interactables': interactables,
            'party': party_info,
            'floor': getattr(exploration_sys, 'floor', 0),
            'screen_text': screen_text,
            'timestamp': now,
            # 인벤토리 정보
            'inventory': inventory_items,
            'healing_items': healing_items,
            'avg_hp_pct': avg_hp_pct,
            # 무게 정보
            'current_weight': current_weight,
            'max_weight': max_weight,
            'weight_pct': int(current_weight / max_weight * 100) if max_weight > 0 else 0,
            'is_overweight': current_weight >= max_weight * 0.9,  # 90% 이상이면 무거움
            'destroyable_items': destroyable_items  # 파괴 가능 아이템 (무거운 순)
        }
        
        _write_state(state)
        
    except Exception as e:
        logger.error(f"탐험 상태 내보내기 실패: {e}")


def export_menu_state(menu_type: str, items: List[str] = None, cursor: int = 0, screen_text: str = ""):
    """메뉴 상태 내보내기"""
    if not _export_enabled:
        return
    
    global _last_export_time
    now = time.time()
    if now - _last_export_time < _export_interval:
        return
    _last_export_time = now
    
    try:
        state = {
            'mode': 'menu',
            'menu_type': menu_type,
            'items': items or [],
            'cursor': cursor,
            'screen_text': screen_text,
            'timestamp': now
        }
        
        _write_state(state)
        
    except Exception as e:
        logger.error(f"메뉴 상태 내보내기 실패: {e}")


def _write_state(state: Dict[str, Any]):
    """상태를 파일로 저장 (원자적 쓰기)"""
    if not _export_enabled:
        return
    
    # 디렉토리 생성
    USER_DATA.mkdir(parents=True, exist_ok=True)
    
    with _write_lock:
        try:
            # 임시 파일에 쓰고 이름 변경 (원자적 쓰기)
            temp_file = STATE_FILE.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, separators=(',', ':'))
            
            # 원자적 이름 변경 (Windows에서는 기존 파일 삭제 필요)
            if STATE_FILE.exists():
                STATE_FILE.unlink()
            temp_file.rename(STATE_FILE)
            
        except Exception as e:
            logger.debug(f"상태 파일 쓰기 실패: {e}")


def read_command() -> Optional[Dict[str, Any]]:
    """봇 명령 읽기 (양방향 통신용)"""
    try:
        if COMMAND_FILE.exists():
            with open(COMMAND_FILE, 'r', encoding='utf-8') as f:
                cmd = json.load(f)
            # 읽은 후 삭제
            COMMAND_FILE.unlink()
            return cmd
    except Exception:
        pass
    return None
