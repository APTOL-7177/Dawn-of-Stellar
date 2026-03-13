"""
릴리 대사 시스템

탐험/전투/마을에서 릴리가 상황에 맞는 대사를 하는 시스템.
FFVII 에어리스처럼 감정적 유대감을 형성하기 위한 핵심 모듈.
"""

import time
import random
import yaml
from typing import Optional, List, Dict, Any
from pathlib import Path

from src.core.logger import get_logger
from src.core.paths import get_project_root

logger = get_logger("lily_dialogue")

LILY_COLOR = (255, 200, 255)
LILY_NAME = "릴리"


class LilyDialogueManager:
    """릴리 대사 매니저"""

    def __init__(self):
        self._dialogues: Dict[str, List[Dict[str, Any]]] = {}
        self._last_idle_time = time.time()
        self._last_random_time = time.time()
        self._last_any_line_time = time.time()  # 모든 대사 쿨다운
        self._idle_interval = 120.0      # 2분마다 대기 대사
        self._random_interval = 360.0    # 6분마다 랜덤 채팅
        self._global_cooldown = 30.0     # 어떤 대사든 최소 30초 간격
        self._shown_lines: set = set()   # 중복 방지
        self._victory_count = 0  # 연승 카운터
        self._entered_dungeons: set = set()  # 첫 진입 체크용
        self._load_dialogues()

    def _load_dialogues(self):
        """YAML에서 대사 데이터 로드"""
        path = get_project_root() / "data" / "rpg_mode" / "lily_dialogues.yaml"
        if not path.exists():
            logger.warning(f"릴리 대사 파일 없음: {path}")
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._dialogues = yaml.safe_load(f) or {}
            total = sum(len(v) for v in self._dialogues.values())
            logger.info(f"릴리 대사 로드: {total}개")
        except Exception as e:
            logger.error(f"릴리 대사 로드 실패: {e}")

    def _pick_line(self, category: str, chapter: int, affinity: int = 0) -> Optional[str]:
        """조건 필터 + 가중치 기반 대사 선택"""
        lines = self._dialogues.get(category, [])
        if not lines:
            return None

        eligible = []
        weights = []
        for entry in lines:
            # 챕터 범위 필터
            cr = entry.get("chapter_range")
            if cr and not (cr[0] <= chapter <= cr[1]):
                continue
            # 친밀도 최소값 필터
            if entry.get("affinity_min", 0) > affinity:
                continue
            # 지역 필터 (있으면)
            text = entry.get("text", "")
            if not text:
                continue
            eligible.append(entry)
            weights.append(entry.get("weight", 1))

        if not eligible:
            return None

        # 중복 방지: 최근에 나온 대사 제외
        fresh = [(e, w) for e, w in zip(eligible, weights)
                 if e.get("text", "") not in self._shown_lines]
        if not fresh:
            # 모두 본 경우 리셋
            self._shown_lines.clear()
            fresh = list(zip(eligible, weights))

        entries, ws = zip(*fresh)
        chosen = random.choices(entries, weights=ws, k=1)[0]
        text = chosen.get("text", "")
        self._shown_lines.add(text)
        return text

    def _pick_region_line(self, category: str, region_id: str,
                          chapter: int, affinity: int = 0) -> Optional[str]:
        """지역 필터 포함 대사 선택"""
        lines = self._dialogues.get(category, [])
        if not lines:
            return None

        eligible = []
        weights = []
        for entry in lines:
            # 지역 필터
            r = entry.get("region")
            if r and r != region_id:
                continue
            cr = entry.get("chapter_range")
            if cr and not (cr[0] <= chapter <= cr[1]):
                continue
            if entry.get("affinity_min", 0) > affinity:
                continue
            text = entry.get("text", "")
            if not text:
                continue
            eligible.append(entry)
            weights.append(entry.get("weight", 1))

        if not eligible:
            return None

        chosen = random.choices(eligible, weights=weights, k=1)[0]
        return chosen.get("text", "")

    def _check_global_cooldown(self) -> bool:
        """글로벌 쿨다운 체크 - 어떤 대사든 최소 간격 보장"""
        return (time.time() - self._last_any_line_time) >= self._global_cooldown

    def _mark_line_spoken(self):
        """대사 출력 시 글로벌 타이머 갱신"""
        self._last_any_line_time = time.time()

    def check_idle_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """대기 시간 체크 후 대사 반환 (타이머 기반)"""
        now = time.time()
        if now - self._last_idle_time < self._idle_interval:
            return None
        if not self._check_global_cooldown():
            return None
        self._last_idle_time = now
        line = self._pick_line("exploration_idle", chapter, affinity)
        if line:
            self._mark_line_spoken()
        return line

    def check_random_chat(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """랜덤 채팅 체크 (타이머 기반)"""
        now = time.time()
        if now - self._last_random_time < self._random_interval:
            return None
        if not self._check_global_cooldown():
            return None
        self._last_random_time = now
        line = self._pick_line("random_chat", chapter, affinity)
        if line:
            self._mark_line_spoken()
        return line

    def get_region_line(self, region_id: str, chapter: int,
                        affinity: int = 0) -> Optional[str]:
        """지역 진입 대사"""
        return self._pick_region_line("exploration_region", region_id, chapter, affinity)

    def get_combat_start_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """전투 시작 대사"""
        return self._pick_line("combat_start", chapter, affinity)

    def get_combat_victory_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """전투 승리 대사"""
        return self._pick_line("combat_victory", chapter, affinity)

    def get_low_hp_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """HP 위험 대사"""
        return self._pick_line("combat_low_hp", chapter, affinity)

    def get_town_enter_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """마을 진입 대사"""
        return self._pick_line("town_enter", chapter, affinity)

    def get_boss_pre_line(self, region_id: str) -> Optional[List[Dict]]:
        """보스 전투 전 대화 씬 (boss_dialogues.yaml에서)"""
        return self._load_boss_dialogue(region_id, "pre_battle")

    def get_boss_post_line(self, region_id: str) -> Optional[List[Dict]]:
        """보스 전투 후 대화 씬"""
        return self._load_boss_dialogue(region_id, "post_battle")

    def _load_boss_dialogue(self, region_id: str, phase: str) -> Optional[List[Dict]]:
        """보스 대화 YAML 로드"""
        path = get_project_root() / "data" / "rpg_mode" / "boss_dialogues.yaml"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            boss_data = data.get("boss_dialogues", {}).get(region_id, {})
            return boss_data.get(phase)
        except Exception as e:
            logger.error(f"보스 대화 로드 실패: {e}")
            return None

    def get_chapter_cutscene(self, chapter_number: int) -> Optional[Dict]:
        """챕터 컷씬 데이터 로드"""
        path = get_project_root() / "data" / "rpg_mode" / "chapter_cutscenes.yaml"
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            key = f"rpg_ch{chapter_number}"
            cutscenes = data.get("chapter_cutscenes", {})
            return cutscenes.get(key)
        except Exception as e:
            logger.error(f"챕터 컷씬 로드 실패: {e}")
            return None

    def get_town_conversations(self, chapter: int, affinity: int = 0,
                                seen: set = None) -> List[Dict]:
        """마을 릴리 대화 목록 (아직 안 본 것 우선)"""
        path = get_project_root() / "data" / "rpg_mode" / "lily_town_dialogues.yaml"
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            return []

        seen = seen or set()
        conversations = []
        for group_key, convos in data.get("town_dialogues", {}).items():
            # group_key = "ch1_3", "ch4_5", etc.
            try:
                parts = group_key.replace("ch", "").split("_")
                ch_min, ch_max = int(parts[0]), int(parts[1])
            except (ValueError, IndexError):
                continue
            if not (ch_min <= chapter <= ch_max):
                continue
            for conv in convos:
                if conv.get("affinity_min", 0) > affinity:
                    continue
                conv_id = conv.get("id", "")
                conv["is_new"] = conv_id not in seen
                conversations.append(conv)

        # 새 대화 우선 정렬
        conversations.sort(key=lambda c: (not c.get("is_new", False), c.get("id", "")))
        return conversations

    def get_ally_down_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """크리스 전투불능 대사"""
        return self._pick_line("combat_ally_down", chapter, affinity)

    def get_ally_critical_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """크리스 HP 위험 대사"""
        return self._pick_line("combat_ally_critical", chapter, affinity)

    def get_flee_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """전투 도주 대사"""
        return self._pick_line("combat_flee", chapter, affinity)

    def get_boss_encounter_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """보스 전투 시작 대사"""
        return self._pick_line("combat_boss_encounter", chapter, affinity)

    def get_long_battle_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """장기전 대사"""
        return self._pick_line("combat_long_battle", chapter, affinity)

    def get_party_danger_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """파티 전멸 위기 대사"""
        return self._pick_line("combat_party_danger", chapter, affinity)

    def get_level_up_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """레벨업 대사"""
        return self._pick_line("level_up", chapter, affinity)

    def get_item_found_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """희귀 아이템 획득 대사"""
        return self._pick_line("item_found_rare", chapter, affinity)

    def get_treasure_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """보물상자 발견 대사"""
        return self._pick_line("treasure_chest", chapter, affinity)

    def get_rest_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """캠프파이어 휴식 대사"""
        return self._pick_line("rest_campfire", chapter, affinity)

    def get_respawn_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """패배 후 마을 부활 대사"""
        return self._pick_line("respawn_town", chapter, affinity)

    def get_new_region_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """새 지역 해금 대사"""
        return self._pick_line("new_region_unlock", chapter, affinity)

    def get_cooking_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """요리 성공 대사"""
        return self._pick_line("cooking_success", chapter, affinity)

    def get_alchemy_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """연금술 성공 대사"""
        return self._pick_line("alchemy_success", chapter, affinity)

    def get_quest_complete_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """퀘스트 완료 대사"""
        return self._pick_line("quest_complete", chapter, affinity)

    def get_shop_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """상점 방문 대사"""
        return self._pick_line("shop_visit", chapter, affinity)

    def get_night_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """밤 탐험 대사 (글로벌 쿨다운 적용)"""
        if not self._check_global_cooldown():
            return None
        line = self._pick_line("night_exploration", chapter, affinity)
        if line:
            self._mark_line_spoken()
        return line

    def get_near_boss_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """보스 문 근처 대사"""
        return self._pick_line("near_boss_door", chapter, affinity)

    def get_full_heal_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """파티 완전 회복 대사"""
        return self._pick_line("party_full_heal", chapter, affinity)

    def get_consecutive_victory_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """연승 대사"""
        return self._pick_line("consecutive_victory", chapter, affinity)

    def get_first_dungeon_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """던전 첫 진입 대사"""
        return self._pick_line("first_dungeon_enter", chapter, affinity)

    def get_equipment_line(self, chapter: int, affinity: int = 0) -> Optional[str]:
        """장비 강화 대사"""
        return self._pick_line("equipment_upgrade", chapter, affinity)

    def reset_timers(self):
        """타이머 리셋 (지역 전환 등)"""
        self._last_idle_time = time.time()
        self._last_random_time = time.time()
