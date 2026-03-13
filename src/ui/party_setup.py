"""
Party Setup - 파티 구성 시스템

4인 파티를 구성하는 시스템 (직업 선택 + 이름 입력)
"""

import tcod.console
import tcod.event
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import yaml
from pathlib import Path
import math
import random
import time as _time_module

from src.ui.cursor_menu import CursorMenu, MenuItem, TextInputBox
from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, InputHandler, unified_input_handler
from src.core.logger import get_logger
from src.core.config import get_config
from src.persistence.meta_progress import get_meta_progress
from src.audio import play_bgm, play_sfx
from src.ui.pygame_backend.effects.text_effects import (
    TextScrambler,
    ColorCycler,
    render_scrambled_text,
)
from src.combat.job_synergy import get_synergy_manager


def _clamp(v: int) -> int:
    return max(0, min(255, v))


@dataclass
class PartyMember:
    """파티 멤버 정보"""
    job_id: str
    job_name: str
    character_name: str
    stats: Dict[str, Any]
    traits_auto: bool = True  # 특성 자동 선택 여부
    selected_traits: List[str] = None  # 선택된 특성 목록 (멤버별)
    player_id: str = None  # 멀티플레이: 이 캐릭터를 제어하는 플레이어 ID (싱글플레이: None)
    
    def __post_init__(self):
        if self.selected_traits is None:
            self.selected_traits = []


class PartySetup:
    """
    파티 구성 시스템

    1. 직업 선택 (34개 중 4개)
    2. 각 캐릭터 이름 입력
    3. 파티 확인
    """

    def __init__(self, screen_width: int = 80, screen_height: int = 50):
        """
        Args:
            screen_width: 화면 너비
            screen_height: 화면 높이
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.logger = get_logger("party_setup")

        # 파티 멤버 (최대 4명)
        self.party: List[PartyMember] = []
        self.current_slot = 0  # 현재 선택 중인 슬롯 (0~3)

        # 상태
        self.state = "job_select"  # job_select, name_input, trait_select, passive_select, confirm
        self.completed = False
        self.cancelled = False
        
        # 파티 전체 공통 패시브 (아군 전체 버프)
        self.selected_passives: List[str] = []

        # 직업 데이터 로드
        self.jobs = self._load_jobs()

        # 랜덤 이름 풀 로드
        self.random_names = self._load_random_names()

        # 메타 진행 정보
        self.meta = get_meta_progress()

        # 현재 메뉴/입력 박스
        self.job_menu: Optional[CursorMenu] = None
        self.name_input: Optional[TextInputBox] = None
        self.trait_menu: Optional[CursorMenu] = None
        self.passive_menu: Optional[CursorMenu] = None

        # 에러 메시지
        self.error_message = ""
        self.error_timer = 0  # 에러 메시지 표시 시간
        
        # 카테고리 필터 (메뉴 생성 전에 초기화해야 함)
        self.category_filter = "전체"  # 전체, 탱커, 힐러, 물리 딜러, 마법 딜러, 스피드, 하이브리드, 서포터, 특수
        self.category_list = ["전체", "탱커", "힐러", "물리 딜러", "마법 딜러", "스피드", "하이브리드", "서포터", "특수"]

        # ── 애니메이션 ──
        self.animation_frame = 0
        self._last_render_time = 0.0

        # 3레이어 별빛
        self.stars_layers: List[List[dict]] = [[], [], []]
        self._init_stars()

        # 유성, 파티클
        self.meteors: List[dict] = []
        self.particles: List[dict] = []

        # 텍스트 이펙트
        self._title_scrambler = TextScrambler("파티 구성", duration=1.0, style="decode")
        self._title_scramble_done = False

        # ColorCycler (내부 phase로만 애니메이션, 느린 속도)
        self._border_cycler = ColorCycler(
            colors=[
                (60, 80, 180),
                (100, 120, 220),
                (80, 100, 200),
                (120, 140, 255),
            ],
            speed=0.25,
            mode="wave",
        )
        self._star_cycler = ColorCycler(
            colors=[
                (150, 180, 255),
                (255, 255, 200),
                (200, 220, 255),
                (255, 240, 150),
            ],
            speed=0.4,
            mode="sparkle",
        )
        self._frame_cycler = ColorCycler(
            colors=[
                (50, 70, 160),
                (80, 100, 200),
                (60, 90, 180),
                (100, 120, 230),
            ],
            speed=0.2,
            mode="wave",
        )

        # 직업 선택 메뉴 생성
        self._create_job_menu()
        
        # 직업별 평점 (화력, 유틸, 생존, 스피드, 조작난이도) - 5점 만점, 0.5점 단위
        # 조작난이도: 높을수록 쉬움
        self.job_ratings = {
            # 탱커
            "warrior": {"화력": 3.0, "유틸": 3.0, "생존": 4.0, "스피드": 3.5, "조작난이도": 4.5},
            "knight": {"화력": 2.0, "유틸": 4.0, "생존": 4.5, "스피드": 2.0, "조작난이도": 4.0},
            "paladin": {"화력": 3.0, "유틸": 4.5, "생존": 5.0, "스피드": 2.0, "조작난이도": 2.5},  # [리메이크] 서약 시스템
            "dark_knight": {"화력": 4.5, "유틸": 1.5, "생존": 3.0, "스피드": 2.5, "조작난이도": 2.5},
            "dragon_knight": {"화력": 4.0, "유틸": 2.0, "생존": 3.5, "스피드": 2.5, "조작난이도": 3.0},
            "dimensionist": {"화력": 3.0, "유틸": 3.5, "생존": 4.5, "스피드": 2.5, "조작난이도": 2.0},
            
            # 물리 딜러
            "berserker": {"화력": 5.0, "유틸": 1.0, "생존": 2.5, "스피드": 3.5, "조작난이도": 3.0},
            "gladiator": {"화력": 4.5, "유틸": 2.5, "생존": 3.5, "스피드": 3.5, "조작난이도": 3.0},  # [리메이크] 콜로세움 쇼타임
            "samurai": {"화력": 4.0, "유틸": 2.0, "생존": 3.0, "스피드": 3.5, "조작난이도": 2.5},
            "rogue": {"화력": 4.5, "유틸": 3.0, "생존": 3.0, "스피드": 5.0, "조작난이도": 2.5},  # [리메이크] 농락 시스템
            "assassin": {"화력": 4.5, "유틸": 2.0, "생존": 3.5, "스피드": 5.0, "조작난이도": 3.5},
            "archer": {"화력": 3.5, "유틸": 3.0, "생존": 2.5, "스피드": 4.0, "조작난이도": 4.0},
            "sniper": {"화력": 5.0, "유틸": 1.5, "생존": 2.0, "스피드": 1.5, "조작난이도": 3.0},
            "ninja": {"화력": 3.5, "유틸": 3.5, "생존": 2.5, "스피드": 5.0, "조작난이도": 2.5},
            "pirate": {"화력": 3.5, "유틸": 3.0, "생존": 3.0, "스피드": 3.5, "조작난이도": 3.0},
            "sword_saint": {"화력": 4.5, "유틸": 1.5, "생존": 2.5, "스피드": 4.0, "조작난이도": 3.0},
            "breaker": {"화력": 4.0, "유틸": 3.5, "생존": 2.5, "스피드": 3.0, "조작난이도": 3.0},
            "engineer": {"화력": 4.0, "유틸": 3.0, "생존": 3.0, "스피드": 2.5, "조작난이도": 2.5},
            
            # 마법 딜러
            "archmage": {"화력": 5.0, "유틸": 2.0, "생존": 2.0, "스피드": 2.5, "조작난이도": 2.5},
            "elementalist": {"화력": 4.5, "유틸": 4.0, "생존": 2.5, "스피드": 3.0, "조작난이도": 2.5},  # [리메이크] 정령 전환
            "time_mage": {"화력": 3.0, "유틸": 5.0, "생존": 3.0, "스피드": 4.0, "조작난이도": 2.0},
            "necromancer": {"화력": 4.0, "유틸": 3.5, "생존": 3.0, "스피드": 2.5, "조작난이도": 3.5},
            
            # 힐러
            "cleric": {"화력": 1.5, "유틸": 5.0, "생존": 3.5, "스피드": 2.5, "조작난이도": 3.5},
            "priest": {"화력": 2.5, "유틸": 5.0, "생존": 3.5, "스피드": 2.0, "조작난이도": 3.0},  # [리메이크] 신탁 시스템
            
            # 하이브리드
            "spellblade": {"화력": 4.0, "유틸": 2.5, "생존": 3.0, "스피드": 3.5, "조작난이도": 2.5},
            "battle_mage": {"화력": 4.5, "유틸": 2.5, "생존": 3.5, "스피드": 3.0, "조작난이도": 3.5},
            "monk": {"화력": 4.0, "유틸": 2.5, "생존": 3.5, "스피드": 4.0, "조작난이도": 3.0},
            "illusionist": {"화력": 3.0, "유틸": 4.0, "생존": 4.5, "스피드": 3.5, "조작난이도": 1.5},
            "vampire": {"화력": 3.5, "유틸": 2.5, "생존": 5.0, "스피드": 3.0, "조작난이도": 2.5},
            
            # 서포터
            "bard": {"화력": 2.0, "유틸": 5.0, "생존": 2.5, "스피드": 3.5, "조작난이도": 3.5},
            "shaman": {"화력": 2.5, "유틸": 4.5, "생존": 3.0, "스피드": 3.0, "조작난이도": 3.0},
            "hacker": {"화력": 3.0, "유틸": 5.0, "생존": 2.0, "스피드": 3.5, "조작난이도": 2.0},  # [리메이크] 침투 시스템
            
            # 특수
            "alchemist": {"화력": 3.0, "유틸": 4.5, "생존": 3.0, "스피드": 2.5, "조작난이도": 3.0},
            "druid": {"화력": 3.0, "유틸": 4.0, "생존": 4.0, "스피드": 3.0, "조작난이도": 2.0},
            "magician": {"화력": 3.0, "유틸": 4.5, "생존": 2.5, "스피드": 3.5, "조작난이도": 1.5},
            "philosopher": {"화력": 3.0, "유틸": 5.0, "생존": 1.5, "스피드": 3.0, "조작난이도": 1.0},
        }

    def _load_jobs(self) -> List[Dict[str, Any]]:
        """직업 데이터 로드"""
        jobs = []
        characters_dir = Path("data/characters")

        if not characters_dir.exists():
            self.logger.error("캐릭터 디렉토리 없음: data/characters")
            return jobs

        # 메타 진행 정보 가져오기
        meta = get_meta_progress()

        # 개발 모드 확인
        config = get_config()
        dev_mode = config.get("development.unlock_all_classes", False)

        for yaml_file in sorted(characters_dir.glob("*.yaml")):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    job_id = yaml_file.stem

                    # 개발 모드이거나 메타 진행에서 해금된 직업인지 확인
                    is_unlocked = dev_mode or meta.is_job_unlocked(job_id)

                    jobs.append({
                        'id': job_id,
                        'name': data.get('class_name', job_id),
                        'description': data.get('description', ''),
                        'slogan': data.get('slogan', ''),
                        'archetype': data.get('archetype', ''),
                        'stats': data.get('base_stats', {}),
                        'unlocked': is_unlocked
                    })
            except Exception as e:
                self.logger.error(f"직업 로드 실패: {yaml_file.name}: {e}")

        self.logger.info(f"직업 {len(jobs)}개 로드 완료 (해금된 직업: {sum(1 for j in jobs if j['unlocked'])}개)")
        return jobs

    def _load_random_names(self) -> List[str]:
        """랜덤 이름 풀 로드"""
        names = []
        name_file = Path("name.txt")

        if not name_file.exists():
            self.logger.warning("name.txt 파일이 없습니다. 기본 이름을 사용합니다.")
            # 기본 랜덤 이름 풀 (직업명이 아닌 실제 이름)
            return ["아리아", "카일", "엘리나", "다리우스", "루나", "제이든", "세라", "라이언", 
                    "미아", "알렉스", "소피아", "마커스", "이리스", "테오", "엠마", "노아"]

        try:
            with open(name_file, 'r', encoding='utf-8') as f:
                # 한 줄에 하나씩 읽기
                for line in f:
                    name = line.strip()
                    if name:  # 빈 줄 제외
                        names.append(name)

            if not names:
                self.logger.warning("name.txt에서 이름을 찾을 수 없습니다.")
                # 기본 랜덤 이름 풀 (직업명이 아닌 실제 이름)
                return ["아리아", "카일", "엘리나", "다리우스", "루나", "제이든", "세라", "라이언", 
                        "미아", "알렉스", "소피아", "마커스", "이리스", "테오", "엠마", "노아"]

            self.logger.info(f"랜덤 이름 {len(names)}개 로드 완료")
            return names

        except Exception as e:
            self.logger.error(f"name.txt 로드 실패: {e}")
            # 기본 랜덤 이름 풀 (직업명이 아닌 실제 이름)
            return ["아리아", "카일", "엘리나", "다리우스", "루나", "제이든", "세라", "라이언", 
                    "미아", "알렉스", "소피아", "마커스", "이리스", "테오", "엠마", "노아"]

    def _categorize_jobs(self) -> Dict[str, List[Dict]]:
        """직업을 역할군별로 분류 (중복 가능)"""
        available_jobs = [job for job in self.jobs if job['unlocked']]
        
        categories = {
            "탱커": [],
            "힐러": [],
            "물리 딜러": [],
            "마법 딜러": [],
            "스피드": [],
            "하이브리드": [],
            "서포터": [],
            "특수": []
        }
        
        # 직업 ID 기반 역할군 매핑 (명확한 분류)
        job_role_mapping = {
            # 탱커
            "warrior": ["탱커", "물리 딜러"],
            "knight": ["탱커", "서포터"],
            "paladin": ["탱커", "힐러"],
            "dragon_knight": ["탱커", "물리 딜러"],
            "dark_knight": ["탱커", "물리 딜러"],
            "dimensionist": ["탱커", "마법 딜러"],  # 회피형 탱커
            "vampire": ["탱커", "하이브리드", "특수"],  # 생존형 탱커
            
            # 물리 딜러
            "berserker": ["물리 딜러"],
            "gladiator": ["물리 딜러"],
            "samurai": ["물리 딜러"],
            "rogue": ["물리 딜러", "스피드"],
            "assassin": ["물리 딜러", "스피드"],
            "breaker": ["물리 딜러", "특수"],  # BRV 파괴 특화
            "archer": ["물리 딜러", "스피드"],
            "sniper": ["물리 딜러"],  # 느린 직업이므로 스피드 제외
            "pirate": ["물리 딜러", "스피드"],
            "ninja": ["마법 딜러", "스피드", "서포터"],
            "sword_saint": ["물리 딜러"],
            
            # 마법 딜러
            "archmage": ["마법 딜러"],
            "necromancer": ["마법 딜러"],
            "elementalist": ["마법 딜러", "서포터"],
            "time_mage": ["마법 딜러", "서포터"],
            
            # 힐러
            "cleric": ["힐러"],
            "priest": ["힐러", "서포터"],
            "druid": ["힐러", "서포터"],
            "alchemist": ["힐러", "서포터"],
            "bard": ["힐러", "서포터"],
            
            # 하이브리드
            "spellblade": ["하이브리드", "물리 딜러", "마법 딜러"],
            "battle_mage": ["하이브리드", "마법 딜러"],  # 탱커 제거
            "monk": ["하이브리드", "물리 딜러"],
            
            # 서포터
            "shaman": ["서포터"],
            "hacker": ["서포터"],
            
            # 물리 딜러 + 특수
            "engineer": ["물리 딜러", "특수"],
            
            # 회피형 탱커
            "illusionist": ["탱커", "하이브리드", "특수"],
            
            # 특수 (유니크한 전투 방식)
            "philosopher": ["서포터", "특수"],  # 논리 조작
            "magician": ["서포터", "특수"],  # 트릭스터
        }
        
        for job in available_jobs:
            job_id = job.get('id', '').lower()
            archetype = job.get('archetype', '').lower()
            
            # 직업 ID 기반 매핑이 있으면 우선 사용
            if job_id in job_role_mapping:
                for role in job_role_mapping[job_id]:
                    if role in categories:
                        categories[role].append(job)
            else:
                # 매핑이 없으면 아키타입 기반으로 분류
                # 여러 역할군에 중복으로 들어갈 수 있음
                
                # 직업별 수동 분류 (archetype 기반)
                job_id = job.get('id', '').lower()
                
                # 탱커: 탱커/서포터, 지휘관/버퍼, 피해 지연 탱커-딜러, 회피형 탱커, 물리 딜러/탱커
                if job_id in ['paladin', 'knight', 'dimensionist', 'illusionist', 'warrior']:
                    categories["탱커"].append(job)
                
                # 힐러: 힐러/서포터, 기적/치유 특화
                if job_id in ['cleric', 'priest']:
                    categories["힐러"].append(job)
                
                # 물리 딜러: 원거리 물리 딜러, 암살 특화, 하이리스크 하이리턴, 원샷 딜러, 
                # 화염 특화 딜러, 반격 전문가, 내공 전사, 도박사/버스터, 속도형 딜러, 
                # 명예의 전사, 초고화력 원거리, 폭발 딜러, 물리 딜러/탱커, 물리 딜러 특수
                if job_id in ['archer', 'assassin', 'berserker', 'dark_knight', 'dragon_knight',
                             'gladiator', 'monk', 'pirate', 'rogue', 'samurai', 'sniper',
                             'sword_saint', 'warrior', 'engineer']:
                    categories["물리 딜러"].append(job)
                
                # 마법 딜러: 마법 딜러, 마법 딜러/서포터, 마법 딜러/유틸리티, 디버프 특화
                if job_id in ['archmage', 'elementalist', 'time_mage', 'necromancer']:
                    categories["마법 딜러"].append(job)
                
                # 스피드: 암살 특화, 속도형 딜러
                if job_id in ['assassin', 'rogue']:
                    categories["스피드"].append(job)
                
                # 하이브리드: 하이브리드 딜러, 특수/탱커/하이브리드, 피해 지연 탱커-딜러, 내공 전사
                if job_id in ['battle_mage', 'spellblade', 'illusionist', 'dimensionist', 'monk']:
                    categories["하이브리드"].append(job)
                
                # 특수: 포션 마스터, BRV 파괴 특화, 변신 술사, 트릭스터 유틸리티, 논리 조작, 
                # 생존 특화, 물리 딜러 특수, 특수/탱커/하이브리드
                if job_id in ['alchemist', 'breaker', 'druid', 'magician', 'philosopher',
                             'vampire', 'engineer', 'illusionist']:
                    categories["특수"].append(job)
                
                # 서포터: 버퍼/디버퍼, 디버프 특화, 지휘관/버퍼, 시야/정보 특화, 탱커/서포터
                if job_id in ['bard', 'hacker', 'knight', 'shaman', 'paladin', 'necromancer']:
                    categories["서포터"].append(job)
        
        return categories

    def _recommend_job_for_slot(self, slot_index: int) -> Optional[Dict]:
        """현재 파티 조합을 고려하여 현재 슬롯에 최적의 직업 추천"""
        available_jobs = [job for job in self.jobs if job['unlocked']]
        
        # 이미 선택된 직업 제외
        selected_job_ids = {member.job_id for member in self.party if member.job_id}
        available_jobs = [job for job in available_jobs if job['id'] not in selected_job_ids]
        
        if not available_jobs:
            return None
        
        # 현재 파티 구성 분석 (카테고리별로 분석)
        categories = self._categorize_jobs()
        current_archetypes = {
            "탱커": False,
            "힐러": False,
            "물리 딜러": False,
            "마법 딜러": False,
            "스피드": False,
            "서포터": False,
            "하이브리드": False,
            "특수": False
        }
        
        for member in self.party:
            if member.job_id:
                job = next((j for j in self.jobs if j['id'] == member.job_id), None)
                if job:
                    # 각 카테고리에 속하는지 확인
                    for category_name in current_archetypes.keys():
                        if any(j['id'] == member.job_id for j in categories.get(category_name, [])):
                            current_archetypes[category_name] = True
        
        # 첫 번째 슬롯: 다양한 역할 추천 (탱커, 힐러, 물리 딜러, 마법 딜러 중 랜덤)
        if slot_index == 0:
            priority_options = []
            if categories["탱커"]:
                priority_options.extend([j for j in categories["탱커"] if j['id'] not in selected_job_ids])
            if categories["힐러"]:
                priority_options.extend([j for j in categories["힐러"] if j['id'] not in selected_job_ids])
            if categories["물리 딜러"]:
                priority_options.extend([j for j in categories["물리 딜러"] if j['id'] not in selected_job_ids])
            if categories["마법 딜러"]:
                priority_options.extend([j for j in categories["마법 딜러"] if j['id'] not in selected_job_ids])
            if priority_options:
                return random.choice(priority_options)
        else:
            # 나머지 슬롯: 밸런스 있는 파티 구성 추천
            # 1. 탱커가 없으면 탱커 추천
            if not current_archetypes["탱커"]:
                if categories["탱커"]:
                    available_tanks = [j for j in categories["탱커"] if j['id'] not in selected_job_ids]
                    if available_tanks:
                        return random.choice(available_tanks)
            
            # 2. 힐러가 없으면 힐러 추천
            if not current_archetypes["힐러"]:
                if categories["힐러"]:
                    available_healers = [j for j in categories["힐러"] if j['id'] not in selected_job_ids]
                    if available_healers:
                        return random.choice(available_healers)
            
            # 3. 물리 딜러가 없으면 물리 딜러 추천
            if not current_archetypes["물리 딜러"]:
                if categories["물리 딜러"]:
                    available_physical = [j for j in categories["물리 딜러"] if j['id'] not in selected_job_ids]
                    if available_physical:
                        return random.choice(available_physical)
            
            # 4. 마법 딜러가 없으면 마법 딜러 추천
            if not current_archetypes["마법 딜러"]:
                if categories["마법 딜러"]:
                    available_magic = [j for j in categories["마법 딜러"] if j['id'] not in selected_job_ids]
                    if available_magic:
                        return random.choice(available_magic)
            
            # 5. 스피드가 없으면 스피드 추천
            if not current_archetypes["스피드"]:
                if categories["스피드"]:
                    available_speed = [j for j in categories["스피드"] if j['id'] not in selected_job_ids]
                    if available_speed:
                        return random.choice(available_speed)
            
            # 6. 서포터가 없으면 서포터 추천
            if not current_archetypes["서포터"]:
                if categories["서포터"]:
                    available_support = [j for j in categories["서포터"] if j['id'] not in selected_job_ids]
                    if available_support:
                        return random.choice(available_support)
            
            # 7. 특수 직업 추천
            if not current_archetypes["특수"]:
                if categories["특수"]:
                    available_special = [j for j in categories["특수"] if j['id'] not in selected_job_ids]
                    if available_special:
                        return random.choice(available_special)
            
            # 8. 하이브리드 추천
            if categories["하이브리드"]:
                available_hybrid = [j for j in categories["하이브리드"] if j['id'] not in selected_job_ids]
                if available_hybrid:
                    return random.choice(available_hybrid)
        
        # 9. 남은 직업 중 랜덤 선택
        return random.choice(available_jobs)

    def _create_job_menu(self):
        """직업 선택 메뉴 생성 (역할군별 카테고리 분류)"""
        menu_items = []
        categories = self._categorize_jobs()
        
        # 이미 선택된 직업 ID 목록
        selected_job_ids = {member.job_id for member in self.party if member.job_id}
        
        # 카테고리 순서
        category_order = ["탱커", "힐러", "물리 딜러", "마법 딜러", "스피드", "하이브리드", "서포터", "특수"]
        
        # 카테고리 필터 적용
        if self.category_filter != "전체":
            category_order = [self.category_filter]
        
        # AI 추천 직업 (한 번만 계산)
        recommended_job = self._recommend_job_for_slot(self.current_slot)
        
        for category_name in category_order:
            jobs_in_category = categories[category_name]
            if not jobs_in_category:
                continue
            
            # 카테고리 헤더 추가
            menu_items.append(MenuItem(
                text=f"━━━ {category_name} ━━━",
                value=None,
                enabled=False,
                description=f"{category_name} 역할군"
            ))
            
            # AI 추천 옵션을 항상 맨 위에 추가 (해당 카테고리에 속하는 경우만)
            if recommended_job and recommended_job in jobs_in_category:
                rec_slogan = recommended_job.get('slogan', '')
                rec_desc = f'"{rec_slogan}" - {recommended_job["description"]}' if rec_slogan else f"AI 추천: {recommended_job['description']}"
                menu_items.append(MenuItem(
                    text=f"  [AI 추천] {recommended_job['name']}",
                    value={"type": "ai_recommend", "job": recommended_job},
                    enabled=True,
                    description=rec_desc
                ))
            
            # 카테고리 내 직업들 추가 (AI 추천 제외)
            for job in jobs_in_category:
                # AI 추천 직업은 이미 추가했으므로 제외
                if recommended_job and job['id'] == recommended_job['id']:
                    continue
                    
                already_selected = job['id'] in selected_job_ids
                slogan = job.get('slogan', '')
                desc = f'"{slogan}" - {job["description"]}' if slogan else f"{job['archetype']} - {job['description']}"
                menu_items.append(MenuItem(
                    text=f"  {job['name']}",
                    value={"type": "job", "job": job},
                    enabled=not already_selected,
                    description=desc
                ))
        
        # 메뉴 생성
        menu_x = 3
        menu_y = 6
        menu_width = 43

        filter_info = f" [{self.category_filter}]" if self.category_filter != "전체" else ""
        self.job_menu = CursorMenu(
            title=f"파티 멤버 {self.current_slot + 1}/4 - 직업 선택{filter_info}",
            items=menu_items,
            x=menu_x,
            y=menu_y,
            width=menu_width,
            show_description=True
        )

    def _create_name_input(self):
        """이름 입력 박스 생성"""
        # 인덱스 범위 확인
        if not self.party or self.current_slot >= len(self.party):
            self.logger.error(f"이름 입력 생성 실패: party 길이={len(self.party)}, current_slot={self.current_slot}")
            if self.party:
                self.current_slot = min(self.current_slot, len(self.party) - 1)
            else:
                self.logger.error("파티가 비어있습니다!")
                self.cancelled = True
                return
        
        job = self.party[self.current_slot].job_name

        self.name_input = TextInputBox(
            title=f"파티 멤버 {self.current_slot + 1}/4",
            prompt=f"{job}의 이름을 입력하세요 (비우면 랜덤):",
            max_length=20,
            x=20,
            y=15,
            width=40
        )

    def _create_trait_menu(self, force_recreate: bool = False):
        """특성 선택 메뉴 생성"""
        self.logger.info(f"_create_trait_menu 호출: force_recreate={force_recreate}, state={self.state}, current_slot={self.current_slot}, trait_menu={self.trait_menu is not None}")
        
        # 상태 확인: trait_select 상태가 아니면 메뉴 생성하지 않음
        if self.state != "trait_select":
            self.logger.warning(f"특성 메뉴 생성 스킵: state가 'trait_select'가 아님 (현재: {self.state})")
            return
        
        from src.character.character_loader import get_traits

        # 개발 모드 확인
        config = get_config()
        dev_mode = config.get("development.unlock_all_classes", False)

        # 인덱스 범위 확인
        if not self.party or self.current_slot >= len(self.party):
            self.logger.error(f"특성 메뉴 생성 실패: party 길이={len(self.party)}, current_slot={self.current_slot}")
            if self.party:
                self.current_slot = min(self.current_slot, len(self.party) - 1)
            else:
                self.logger.error("파티가 비어있습니다!")
                self.cancelled = True
                return
        
        # 중복 생성 방지 (강제 재생성이 아니고, 이미 같은 멤버의 메뉴가 있으면 스킵)
        # 메뉴 제목에 현재 멤버 이름이 포함되어 있는지 확인
        if not force_recreate and self.trait_menu is not None:
            if self.party and self.current_slot < len(self.party):
                current_member = self.party[self.current_slot]
                # 메뉴 제목에 현재 멤버 이름이 정확히 포함되어 있는지 확인
                # (이전 멤버의 메뉴가 남아있을 수 있으므로 정확히 확인)
                if hasattr(self.trait_menu, 'title'):
                    title = self.trait_menu.title
                    # 메뉴 제목 형식: "{character_name} ({job_name}) - 특성 선택"
                    # 현재 멤버의 이름이 제목 시작 부분에 정확히 포함되어 있는지 확인
                    if current_member.character_name and title.startswith(current_member.character_name):
                        self.logger.warning(f"특성 메뉴가 이미 생성되어 있음 ({current_member.character_name}, slot: {self.current_slot}), 재생성 스킵 (force_recreate={force_recreate})")
                        return
        
        self.logger.info(f"특성 메뉴 생성 시작: 멤버 {self.current_slot + 1}/4")
        
        # 기존 메뉴가 있으면 명시적으로 None으로 설정 (중복 방지)
        if self.trait_menu is not None:
            self.logger.warning(f"기존 특성 메뉴 제거: {self.trait_menu.title if hasattr(self.trait_menu, 'title') else 'Unknown'}")
        self.trait_menu = None
        
        member = self.party[self.current_slot]
        
        # 직업의 특성 목록 로드
        traits = get_traits(member.job_id)

        # unlocked_traits에 있는 특성만 필터링
        unlocked_traits = []
        for trait in traits:
            trait_id = trait.get('id', '')
            is_unlocked = dev_mode or self.meta.is_trait_unlocked(member.job_id, trait_id)
            if is_unlocked:
                unlocked_traits.append(trait)

        self.logger.info(f"특성 메뉴 생성: 멤버 {self.current_slot + 1}/4 - {member.character_name} ({member.job_name}, job_id: {member.job_id}), 해금된 특성 수: {len(unlocked_traits)} (총 {len(traits)}개 중), 선택된 특성: {member.selected_traits}")

        selected_count = len(member.selected_traits) if member.selected_traits else 0

        if not unlocked_traits:
            self.logger.warning(f"특성이 없습니다: {member.job_id}")
            # 특성이 없어도 완료 항목은 표시
            menu_items = [
                MenuItem(
                    text="← 완료 (특성 없음)",
                    value="done",
                    enabled=True,
                    description="이 직업에는 특성이 없습니다"
                )
            ]
        else:
            menu_items = []
            # selected_traits 초기화 확인 (None 체크)
            if member.selected_traits is None:
                member.selected_traits = []

            selected_count = len(member.selected_traits)
            max_traits = 2  # 직업당 최대 특성 개수
            self.logger.info(f"특성 메뉴 생성: {member.character_name}, 선택된 특성 수: {selected_count}/{max_traits}, 선택된 특성: {member.selected_traits}")

            for trait in unlocked_traits:
                trait_id = trait.get('id', '')
                trait_name = trait.get('name', '알 수 없음')
                trait_desc = trait.get('description', '')

                # 이미 선택된 특성인지 확인 (명시적으로 리스트에서 확인)
                is_selected = False
                if member.selected_traits:
                    is_selected = trait_id in member.selected_traits

                # 최대 2개 제한: 선택되지 않은 특성은 이미 2개가 선택되었으면 비활성화
                is_enabled = True
                if not is_selected and selected_count >= max_traits:
                    is_enabled = False
                
                # 선택 표시 (선택된 특성은 [*]로 표시)
                if is_selected:
                    checkmark = "[*]"
                else:
                    checkmark = "[ ]"
                menu_text = f"{checkmark} {trait_name}"
                
                # 디버그 로그
                if is_selected:
                    self.logger.debug(f"[특성 메뉴] {trait_id} ({trait_name}) 선택됨 - 텍스트: '{menu_text}'")
                elif not is_enabled:
                    menu_text += " (선택 불가 - 최대 2개)"
                    self.logger.debug(f"[특성 메뉴] {trait_id} ({trait_name}) 비활성화 (이미 {selected_count}개 선택)")
                
                menu_items.append(MenuItem(
                    text=menu_text,
                    value=trait_id,
                    enabled=is_enabled,
                    description=trait_desc,
                    is_selected=is_selected  # 선택된 항목 표시 (색상 구분용)
                ))
            
            # 완료 항목
            menu_items.append(MenuItem(
                text="← 완료",
                value="done",
                enabled=True,
                description="특성 선택 완료"
            ))
        
        max_traits = 2  # 직업당 최대 특성 개수
        self.trait_menu = CursorMenu(
            title=f"{member.character_name} ({member.job_name}) - 특성 선택 ({selected_count}/{max_traits}, 해금: {len(unlocked_traits)}개)",
            items=menu_items,
            x=3,
            y=6,
            width=43,
            show_description=True
        )

    def _get_random_name(self) -> str:
        """랜덤 이름 선택 (중복 제외)"""
        # 이미 사용된 이름 제외
        used_names = set(member.character_name for member in self.party if member.character_name)
        available_names = [name for name in self.random_names if name not in used_names]

        if not available_names:
            # 모든 이름이 사용되었으면 숫자 추가
            return f"{random.choice(self.random_names)}{random.randint(1, 999)}"

        return random.choice(available_names)

    def _generate_auto_party(self) -> List[PartyMember]:
        """자동 파티 생성 (AI 추천)"""
        available_jobs = [job for job in self.jobs if job['unlocked']]
        
        if len(available_jobs) < 4:
            # 해금된 직업이 4개 미만이면 랜덤 선택
            selected_jobs = random.sample(available_jobs, min(4, len(available_jobs)))
            return [
                PartyMember(
                    job_id=job['id'],
                    job_name=job['name'],
                    character_name="",  # 이름은 나중에 입력
                    stats=job['stats'],
                    traits_auto=False  # 특성은 항상 수동
                )
                for job in selected_jobs
            ]
        
        # 역할별 분류
        tanks = []  # 탱커
        healers = []  # 힐러/서포터
        physical_dps = []  # 물리 딜러
        magic_dps = []  # 마법 딜러
        hybrid = []  # 하이브리드
        support = []  # 서포터/버퍼
        special = []  # 특수 역할
        
        for job in available_jobs:
            job_id = job.get('id', '').lower()
            
            # 직업별 수동 분류 (archetype 기반, 자동 파티 구성용 단일 분류)
            if job_id in ['paladin', 'knight', 'dimensionist', 'illusionist', 'warrior']:
                tanks.append(job)
            elif job_id in ['cleric', 'priest']:
                healers.append(job)
            elif job_id in ['archer', 'assassin', 'berserker', 'dark_knight', 'dragon_knight',
                           'gladiator', 'pirate', 'rogue', 'samurai', 'sniper',
                           'sword_saint', 'warrior', 'engineer']:
                physical_dps.append(job)
            elif job_id in ['archmage', 'elementalist', 'time_mage', 'necromancer']:
                magic_dps.append(job)
            elif job_id in ['battle_mage', 'spellblade', 'monk']:
                hybrid.append(job)
            elif job_id in ['bard', 'hacker', 'shaman', 'necromancer']:
                support.append(job)
            else:
                # 특수: alchemist, breaker, druid, magician, philosopher, vampire, illusionist
                special.append(job)
        
        # 밸런스 있는 파티 구성
        selected = []
        
        # 1. 탱커 1명 (없으면 물리 딜러 중 방어력 높은 것)
        if tanks:
            selected.append(random.choice(tanks))
        elif physical_dps:
            # 물리 딜러 중 방어력 높은 것 선택
            sorted_physical = sorted(physical_dps, key=lambda j: j['stats'].get('physical_defense', 0), reverse=True)
            selected.append(sorted_physical[0])
        else:
            selected.append(random.choice(available_jobs))
        
        # 2. 힐러/서포터 1명
        if healers:
            selected.append(random.choice(healers))
        elif support:
            selected.append(random.choice(support))
        else:
            # 힐러가 없으면 서포터나 특수 역할 중 선택
            if support:
                selected.append(random.choice(support))
            elif special:
                selected.append(random.choice(special))
            else:
                selected.append(random.choice(available_jobs))
        
        # 3. 물리 딜러 1명
        if physical_dps:
            # 이미 선택된 것 제외
            available_physical = [j for j in physical_dps if j not in selected]
            if available_physical:
                selected.append(random.choice(available_physical))
            else:
                selected.append(random.choice(physical_dps))
        else:
            # 물리 딜러가 없으면 하이브리드나 특수 역할
            if hybrid:
                selected.append(random.choice(hybrid))
            elif special:
                selected.append(random.choice(special))
            else:
                available = [j for j in available_jobs if j not in selected]
                if available:
                    selected.append(random.choice(available))
        
        # 4. 마법 딜러 또는 하이브리드 1명
        if magic_dps:
            available_magic = [j for j in magic_dps if j not in selected]
            if available_magic:
                selected.append(random.choice(available_magic))
            elif hybrid:
                available_hybrid = [j for j in hybrid if j not in selected]
                if available_hybrid:
                    selected.append(random.choice(available_hybrid))
                else:
                    available = [j for j in available_jobs if j not in selected]
                    if available:
                        selected.append(random.choice(available))
            else:
                available = [j for j in available_jobs if j not in selected]
                if available:
                    selected.append(random.choice(available))
        elif hybrid:
            available_hybrid = [j for j in hybrid if j not in selected]
            if available_hybrid:
                selected.append(random.choice(available_hybrid))
            else:
                available = [j for j in available_jobs if j not in selected]
                if available:
                    selected.append(random.choice(available))
        else:
            # 마법 딜러와 하이브리드가 없으면 남은 것 중 선택
            available = [j for j in available_jobs if j not in selected]
            if available:
                selected.append(random.choice(available))
            else:
                # 모든 직업이 선택되었으면 랜덤으로 하나 더 추가
                selected.append(random.choice(available_jobs))
        
        # PartyMember 리스트 생성 (정확히 4명 보장)
        party = []
        
        # selected가 4개 미만이면 나머지는 랜덤으로 채우기
        while len(selected) < 4:
            available = [j for j in available_jobs if j not in selected]
            if available:
                selected.append(random.choice(available))
            else:
                # 모든 직업이 선택되었으면 중복 허용
                selected.append(random.choice(available_jobs))
        
        # 정확히 4명만 선택
        for job in selected[:4]:
            party.append(PartyMember(
                job_id=job['id'],
                job_name=job['name'],
                character_name="",  # 이름은 나중에 입력
                stats=job['stats'],
                traits_auto=False  # 특성은 항상 수동
            ))
        
        self.logger.info(f"자동 파티 생성: {len(party)}명 생성됨 - {[m.job_name for m in party]}")
        return party


    def handle_input(self, action: GameAction, event: tcod.event.KeyDown = None) -> bool:
        """
        입력 처리

        Args:
            action: 게임 액션
            event: 키보드 이벤트 (텍스트 입력용)

        Returns:
            파티 구성이 완료되었으면 True
        """
        if self.state == "job_select":
            return self._handle_job_select(action)
        elif self.state == "name_input":
            return self._handle_name_input(action, event)
        elif self.state == "trait_select":
            return self._handle_trait_select(action)
        elif self.state == "passive_select":
            return self._handle_passive_select(action, event)
        elif self.state == "confirm":
            return self._handle_confirm(action)

        return False

    def _handle_trait_select(self, action: GameAction) -> bool:
        """특성 선택 입력 처리"""
        if action == GameAction.MOVE_UP:
            self.trait_menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            self.trait_menu.move_cursor_down()
        elif action == GameAction.CONFIRM:
            selected = self.trait_menu.get_selected_item()
            if selected:
                value = selected.value
                
                # 인덱스 범위 확인
                if not self.party or self.current_slot >= len(self.party):
                    self.logger.error(f"특성 선택 처리 실패: party 길이={len(self.party)}, current_slot={self.current_slot}")
                    return False
                
                member = self.party[self.current_slot]
                
                if value == "done":
                    # 특성 선택 완료 → 다음 멤버 특성 선택 또는 패시브 선택
                    self.logger.info(f"특성 선택 완료: 멤버 {self.current_slot + 1}/4")
                    self.current_slot += 1
                    if self.current_slot >= 4:
                        # 4명 모두 특성 선택 완료 → 패시브 선택으로 (한 번만)
                        self.logger.info("모든 멤버의 특성 선택 완료, 패시브 선택으로 전환")
                        self.state = "passive_select"
                        self.passive_menu = None
                        self._create_passive_menu()
                    else:
                        # 다음 멤버 특성 선택
                        self.logger.info(f"다음 멤버 특성 선택: 멤버 {self.current_slot + 1}/4")
                        self.state = "trait_select"
                        self.trait_menu = None
                        self._create_trait_menu(force_recreate=True)
                else:
                    # 특성 토글
                    if member.selected_traits is None:
                        member.selected_traits = []
                    
                    selected_count = len(member.selected_traits)
                    
                    # 특성 토글 처리
                    max_traits = 2  # 직업당 최대 특성 개수
                    
                    if value in member.selected_traits:
                        # 선택 해제
                        member.selected_traits.remove(value)
                        new_count = len(member.selected_traits)
                        self.logger.info(f"[특성 선택] 해제: {value}, 이전: {selected_count}개 -> 현재: {new_count}개, 목록: {member.selected_traits}")
                    else:
                        # 선택 (최대 2개)
                        if selected_count < max_traits:
                            member.selected_traits.append(value)
                            new_count = len(member.selected_traits)
                            self.logger.info(f"[특성 선택] 추가: {value}, 이전: {selected_count}개 -> 현재: {new_count}개, 목록: {member.selected_traits}")
                            
                            # 선택 후 즉시 확인 (디버깅용)
                            if value not in member.selected_traits:
                                self.logger.error(f"[특성 선택 오류] {value} 추가 실패! 목록: {member.selected_traits}")
                            
                            # 2개를 모두 선택했으면 자동으로 완료 처리 (다음 멤버 또는 패시브 선택)
                            if new_count >= max_traits:
                                self.logger.info(f"[특성 선택] {max_traits}개 선택 완료, 자동으로 다음 단계로 이동 (멤버 {self.current_slot + 1}/4)")
                                self.current_slot += 1
                                if self.current_slot >= 4:
                                    # 4명 모두 특성 선택 완료 → 패시브 선택으로 (한 번만)
                                    self.logger.info("모든 멤버의 특성 선택 완료, 패시브 선택으로 전환")
                                    self.state = "passive_select"
                                    self.passive_menu = None
                                    self._create_passive_menu()
                                else:
                                    # 다음 멤버 특성 선택
                                    self.logger.info(f"다음 멤버 특성 선택: 멤버 {self.current_slot + 1}/4")
                                    self.state = "trait_select"
                                    self.trait_menu = None
                                    self._create_trait_menu(force_recreate=True)
                                return False
                        else:
                            self.error_message = f"특성은 최대 {max_traits}개까지 선택할 수 있습니다! (현재: {selected_count}개)"
                            self.error_timer = 120
                            self.logger.warning(f"[특성 선택] 실패: 이미 {selected_count}개 선택됨, 추가하려는 특성: {value}")
                            return False  # 메뉴 다시 생성하지 않고 종료
                    
                    # 메뉴 다시 생성 (체크 표시 업데이트)
                    # 현재 커서 위치 저장
                    current_cursor = self.trait_menu.cursor_index if self.trait_menu else 0
                    self.logger.debug(f"메뉴 재생성 전: 커서 위치={current_cursor}, 선택된 특성={member.selected_traits}")
                    
                    # 메뉴 다시 생성 (강제 재생성)
                    self._create_trait_menu(force_recreate=True)
                    
                    # 커서 위치 복원 (메뉴 생성 시 _move_to_first_enabled()가 호출되므로 다시 설정)
                    if self.trait_menu and len(self.trait_menu.items) > 0:
                        # 저장된 커서 위치가 유효한 범위인지 확인
                        if 0 <= current_cursor < len(self.trait_menu.items):
                            # 해당 위치의 아이템이 활성화되어 있는지 확인
                            if self.trait_menu.items[current_cursor].enabled:
                                self.trait_menu.cursor_index = current_cursor
                            else:
                                # 비활성화된 아이템이면 가장 가까운 활성화된 아이템 찾기
                                for i in range(len(self.trait_menu.items)):
                                    idx = (current_cursor + i) % len(self.trait_menu.items)
                                    if self.trait_menu.items[idx].enabled:
                                        self.trait_menu.cursor_index = idx
                                        break
                        else:
                            # 범위를 벗어났으면 첫 번째 활성화된 아이템으로
                            for i, item in enumerate(self.trait_menu.items):
                                if item.enabled:
                                    self.trait_menu.cursor_index = i
                                    break
                    
                    self.logger.debug(f"메뉴 재생성 후: 커서 위치={self.trait_menu.cursor_index if self.trait_menu else None}, 선택된 특성={member.selected_traits}")
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 이전 단계로 (이름 입력 - 현재 슬롯)
            play_sfx("ui", "cursor_cancel")
            self.state = "name_input"
            self._create_name_input()
        
        return False

    def _create_passive_menu(self):
        """패시브 선택 메뉴 생성 (파티 전체 공통)"""
        import yaml
        from pathlib import Path
        
        # 패시브는 파티 전체 공통이므로 멤버별 확인 불필요
        
        # 개발 모드 확인
        config = get_config()
        dev_mode = config.get("development.unlock_all_classes", False)
        
        # 패시브 목록 로드
        passives_file = Path("data/passives.yaml")
        passives = []
        
        if passives_file.exists():
            try:
                with open(passives_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data and 'passives' in data:
                        passives_data = data['passives']
                        # passives가 딕셔너리면 values() 사용, 리스트면 그대로 사용
                        if isinstance(passives_data, dict):
                            passives = list(passives_data.values())
                        elif isinstance(passives_data, list):
                            passives = passives_data
                        else:
                            passives = []
                    else:
                        passives = []
            except Exception as e:
                self.logger.error(f"패시브 로드 실패: {e}")
                passives = []
        
        menu_items = []
        
        # 선택된 패시브의 총 코스트 계산
        total_cost = 0
        for passive in passives:
            if passive.get('id', '') in self.selected_passives:
                total_cost += passive.get('cost', 0)
        
        self.logger.info(f"패시브 메뉴 생성: 선택된 패시브 수: {len(self.selected_passives)}, 총 코스트: {total_cost}")
        
        for passive in passives:
            passive_id = passive.get('id', '')
            passive_name = passive.get('name', '알 수 없음')
            passive_desc = passive.get('description', '')
            passive_cost = passive.get('cost', 0)
            unlocked = passive.get('unlocked', True)

            # 개발 모드가 아니면 잠긴 패시브는 표시하지 않음
            if not dev_mode and not unlocked:
                continue

            # 이미 선택된 패시브인지 확인 (파티 전체 공통)
            is_selected = passive_id in self.selected_passives

            # 선택 표시 (선택된 패시브는 [*]로 표시)
            if is_selected:
                checkmark = "[*]"
            else:
                checkmark = "[ ]"
            menu_text = f"{checkmark} {passive_name} (코스트: {passive_cost})"

            # 해금 여부 확인 (항상 true - 이미 unlocked인 것만 표시)
            enabled = True
            
            menu_items.append(MenuItem(
                text=menu_text,
                value=passive_id,
                enabled=enabled,
                description=passive_desc,
                is_selected=is_selected  # 선택된 항목 표시 (색상 구분용)
            ))
        
        # 총 코스트 정보 포함한 제목
        max_passives = 3
        selected_count = len(self.selected_passives)
        title = f"파티 전체 패시브 선택 (선택: {selected_count}/{max_passives}, 코스트: {total_cost}/10)"
        if total_cost > 10:
            title += " [코스트 초과!]"
        if selected_count > max_passives:
            title += " [종류 초과!]"
        
        self.passive_menu = CursorMenu(
            title=title,
            items=menu_items,
            x=3,
            y=6,
            width=43,
            show_description=True
        )

    def _handle_passive_select(self, action: GameAction, event: tcod.event.KeyDown = None) -> bool:
        """패시브 선택 입력 처리 (파티 전체 공통)"""
        if action == GameAction.MOVE_UP:
            self.passive_menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            self.passive_menu.move_cursor_down()
        elif action == GameAction.MENU or (action == GameAction.START if hasattr(GameAction, 'START') else False) or (event and event.sym == tcod.event.KeySym.RETURN):
            # 엔터 키 또는 메뉴(Start) 버튼: 패시브 선택 완료
            
            # 패시브 선택 완료 조건 확인
            max_passives = 3
            selected_count = len(self.selected_passives)
            
            # 총 코스트 계산
            from pathlib import Path
            import yaml
            total_cost = 0
            passives_file = Path("data/passives.yaml")
            if passives_file.exists():
                with open(passives_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    if data and 'passives' in data:
                        passives = data['passives'] if isinstance(data['passives'], list) else list(data['passives'].values())
                        for passive_id in self.selected_passives:
                            for p in passives:
                                if p.get('id') == passive_id:
                                    total_cost += p.get('cost', 0)
            
            # 완료 조건 확인
            if selected_count > max_passives:
                self.error_message = f"패시브는 최대 {max_passives}종류까지 선택할 수 있습니다! (현재: {selected_count}개)"
                self.error_timer = 120
                self.logger.warning(f"패시브 선택 완료 실패: 종류 초과 ({selected_count} > {max_passives})")
                return False
            elif total_cost > 10:
                self.error_message = f"코스트 초과! (현재: {total_cost}, 최대: 10)"
                self.error_timer = 120
                self.logger.warning(f"패시브 선택 완료 실패: 코스트 초과 ({total_cost} > 10)")
                return False
            else:
                # 패시브 선택 완료 → 게임 시작
                self.logger.info(f"패시브 선택 완료: 선택된 패시브 수: {selected_count}, 총 코스트: {total_cost}")
                self.completed = True
                return True

        elif action == GameAction.CONFIRM:
            # Z 키 또는 A 버튼: 패시브 토글
            selected = self.passive_menu.get_selected_item()
            if selected:
                value = selected.value
                
                # 패시브 토글 (파티 전체 공통)
                # 코스트 계산
                from pathlib import Path
                import yaml
                passives_file = Path("data/passives.yaml")
                current_cost = 0
                passive_cost = 0
                max_passives = 3
                
                if passives_file.exists():
                    with open(passives_file, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        if data and 'passives' in data:
                            passives = data['passives'] if isinstance(data['passives'], list) else list(data['passives'].values())
                            for p in passives:
                                if p.get('id') in self.selected_passives:
                                    current_cost += p.get('cost', 0)
                                if p.get('id') == value:
                                    passive_cost = p.get('cost', 0)
                
                if value in self.selected_passives:
                    # 선택 해제
                    self.selected_passives.remove(value)
                    self.logger.info(f"패시브 선택 해제: {value}, 현재 선택된 패시브: {self.selected_passives}")
                    play_sfx("ui", "cursor_cancel")
                else:
                    # 선택 (최대 3종류, 최대 코스트 10 제한)
                    selected_count = len(self.selected_passives)
                    if selected_count >= max_passives:
                        self.error_message = f"패시브는 최대 {max_passives}종류까지 선택할 수 있습니다! (현재: {selected_count}개)"
                        self.error_timer = 120
                        self.logger.warning(f"패시브 선택 실패: 종류 초과 ({selected_count} >= {max_passives})")
                        play_sfx("ui", "error")
                    elif current_cost + passive_cost > 10:
                        self.error_message = f"코스트 초과! (현재: {current_cost}, 추가: {passive_cost}, 최대: 10)"
                        self.error_timer = 120
                        self.logger.warning(f"패시브 선택 실패: 코스트 초과 ({current_cost} + {passive_cost} > 10)")
                        play_sfx("ui", "error")
                    else:
                        self.selected_passives.append(value)
                        self.logger.info(f"패시브 선택: {value}, 현재 선택된 패시브: {self.selected_passives}, 총 코스트: {current_cost + passive_cost}")
                        play_sfx("ui", "cursor_select")
                
                # 메뉴 다시 생성 (체크 표시 및 총 코스트 업데이트)
                current_cursor = self.passive_menu.cursor_index if self.passive_menu else 0
                self.passive_menu = None
                self._create_passive_menu()
                # 커서 위치 복원
                if self.passive_menu and current_cursor < len(self.passive_menu.items):
                    self.passive_menu.cursor_index = current_cursor

        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 이전 단계로 (마지막 멤버의 특성 선택)
            play_sfx("ui", "cursor_cancel")
            self.current_slot = 3
            self.state = "trait_select"
            self.trait_menu = None
            self._create_trait_menu(force_recreate=True)
        
        return False

    def _handle_job_select(self, action: GameAction) -> bool:
        """직업 선택 입력 처리"""
        if action == GameAction.MOVE_UP:
            self.job_menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            self.job_menu.move_cursor_down()
        elif action == GameAction.MOVE_LEFT:
            # 이전 카테고리
            current_idx = self.category_list.index(self.category_filter)
            self.category_filter = self.category_list[(current_idx - 1) % len(self.category_list)]
            self._create_job_menu()
            play_sfx("ui", "cursor_move")
        elif action == GameAction.MOVE_RIGHT:
            # 다음 카테고리
            current_idx = self.category_list.index(self.category_filter)
            self.category_filter = self.category_list[(current_idx + 1) % len(self.category_list)]
            self._create_job_menu()
            play_sfx("ui", "cursor_move")
        elif action == GameAction.CONFIRM:
            # 선택된 직업 가져오기
            selected = self.job_menu.get_selected_item()
            if selected and selected.enabled:
                value = selected.value
                
                # value가 None이면 헤더이므로 무시
                if value is None:
                    return False
                
                # value가 dict 형태인지 확인 (카테고리 분류 후)
                if isinstance(value, dict):
                    if value.get("type") == "ai_recommend":
                        # AI 추천 직업 선택
                        job_data = value["job"]
                    elif value.get("type") == "job":
                        # 일반 직업 선택
                        job_data = value["job"]
                    else:
                        # 알 수 없는 타입
                        return False
                else:
                    # 기존 형태 (하위 호환성)
                    job_data = value

                # 임시 파티 멤버 생성 (이름은 나중에)
                member = PartyMember(
                    job_id=job_data['id'],
                    job_name=job_data['name'],
                    character_name="",  # 나중에 입력
                    stats=job_data['stats']
                )

                # 현재 슬롯에 추가
                if self.current_slot < len(self.party):
                    self.party[self.current_slot] = member
                else:
                    self.party.append(member)

                # 이름 입력 단계로
                self.state = "name_input"
                self._create_name_input()

        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 이전 슬롯으로 또는 취소
            play_sfx("ui", "cursor_cancel")
            if self.current_slot > 0:
                self.current_slot -= 1
                if self.current_slot < len(self.party):
                    # 이전 슬롯 수정
                    self.party.pop()
                self._create_job_menu()
            else:
                # 파티 구성 취소
                self.cancelled = True
                return True

        return False

    def _handle_name_input(self, action: GameAction, event: tcod.event.KeyDown = None) -> bool:
        """이름 입력 처리"""
        is_keyboard = event is not None

        # 1. 확인 (Confirm): Enter 키 또는 게임패드 A버튼
        if (is_keyboard and event.sym == tcod.event.KeySym.RETURN) or \
           (not is_keyboard and action == GameAction.CONFIRM):
            self.name_input.handle_confirm()
            if self.name_input.confirmed:
                name = self.name_input.get_result()

                # 이름이 비어있으면 랜덤 선택
                if not name:
                    name = self._get_random_name()
                    self.logger.info(f"이름이 비어있어 랜덤 선택: {name}")

                # 이름 중복 확인
                if any(m.character_name == name for m in self.party[:self.current_slot]):
                    self.logger.warning(f"중복된 이름: {name}")
                    # 에러 메시지 표시
                    self.error_message = f"이름 중복: '{name}'은(는) 이미 사용 중입니다!"
                    self.error_timer = 120  # 2초 표시 (60프레임 기준)
                    self.name_input.confirmed = False
                    self.name_input.text = ""
                    return False

                # 이름 저장 (인덱스 범위 확인)
                if not self.party or self.current_slot >= len(self.party):
                    self.logger.error(f"이름 저장 실패: party 길이={len(self.party)}, current_slot={self.current_slot}")
                    self.error_message = "파티 구성 오류가 발생했습니다!"
                    self.error_timer = 120
                    self.name_input.confirmed = False
                    self.name_input.text = ""
                    return False
                
                self.party[self.current_slot].character_name = name
                self.logger.info(
                    f"파티 멤버 {self.current_slot + 1} 완료: "
                    f"{name} ({self.party[self.current_slot].job_name})"
                )

                # 다음 슬롯으로
                self.current_slot += 1

                if self.current_slot >= 4:
                    # 4명 모두 이름 입력 완료
                    self.current_slot = 0
                    self.state = "trait_select"
                    # 메뉴 재생성을 위해 기존 메뉴 초기화
                    self.trait_menu = None
                    self._create_trait_menu(force_recreate=True)
                    self.logger.info(f"이름 입력 완료, 특성 선택 단계로 전환 (멤버 {self.current_slot + 1}/4, 파티 길이: {len(self.party)})")
                else:
                    # 다음 멤버 직업 선택
                    self.state = "job_select"
                    self._create_job_menu()
            return False

        # 2. 취소 (Cancel): ESC 키 또는 게임패드 B버튼
        elif (is_keyboard and event.sym == tcod.event.KeySym.ESCAPE) or \
             (not is_keyboard and action == GameAction.CANCEL):
            # 직업 선택으로 돌아가기
            self.state = "job_select"
            if not self.party:
                # 파티가 없으면 취소
                self.cancelled = True
                return True
            self.party.pop()  # 현재 슬롯 제거
            self._create_job_menu()
            return False

        # 3. 문자 입력 (키보드 전용)
        if is_keyboard:
            if event.sym == tcod.event.KeySym.BACKSPACE:
                self.name_input.handle_backspace()
            # 일반 문자 입력 (ASCII 32~126 범위의 출력 가능한 문자)
            elif 32 <= event.sym <= 126:
                char = chr(event.sym)
                self.name_input.handle_char_input(char)
        
        return False

    def _handle_confirm(self, action: GameAction) -> bool:
        """파티 확인 입력 처리"""
        if action == GameAction.CONFIRM:
            # 파티 구성 완료
            self.completed = True
            return True
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 마지막 멤버 수정
            play_sfx("ui", "cursor_cancel")
            self.current_slot = 3
            self.state = "name_input"
            self._create_name_input()

        return False

    # ── 렌더링 헬퍼 (메인 메뉴 동일 기법) ──────────────────────────

    def _init_stars(self):
        """3레이어 시차 별빛 초기화"""
        for layer in range(3):
            count = [60, 35, 15][layer]
            speed = [0.02, 0.05, 0.12][layer]
            for _ in range(count):
                self.stars_layers[layer].append({
                    "x": random.uniform(0, self.screen_width),
                    "y": random.uniform(0, self.screen_height),
                    "brightness": random.uniform(0.3, 1.0),
                    "twinkle_phase": random.uniform(0, math.pi * 2),
                    "twinkle_speed": random.uniform(1.0, 3.0),
                    "speed": speed,
                    "char": random.choice("·.+*") if layer < 2 else random.choice("+*"),
                })

    def _render_bg(self, console, t):
        """배경 우주 그라데이션 + 오로라"""
        aurora_limit = self.screen_height * 0.35
        for y in range(self.screen_height):
            gi = max(0, int(3 + (y / self.screen_height) * 15))
            base_r, base_g, base_b = gi // 4, gi // 5, gi
            if y < aurora_limit:
                for x in range(self.screen_width):
                    wave1 = math.sin(x * 0.06 + t * 0.8) * math.sin(y * 0.1 + t * 0.3)
                    wave2 = math.sin(x * 0.04 - t * 0.5 + 2.0) * math.cos(y * 0.07 + t * 0.4)
                    intensity = max(0, (wave1 + wave2) * 0.5)
                    y_factor = max(0, 1.0 - (y / aurora_limit))
                    intensity *= y_factor * 0.5
                    r = _clamp(base_r + int(intensity * 20))
                    g = _clamp(base_g + int(intensity * 55))
                    b = _clamp(base_b + int(intensity * 35))
                    console.rgb[y, x] = (ord(' '), (r, g, b), (r, g, b))
            else:
                for x in range(self.screen_width):
                    console.rgb[y, x] = (ord(' '), (base_r, base_g, base_b), (base_r, base_g, base_b))

    def _render_stars(self, console, t):
        """3레이어 시차 별빛 렌더링"""
        for li in range(3):
            for star in self.stars_layers[li]:
                star["y"] += star["speed"]
                if star["y"] >= self.screen_height:
                    star["y"] = 0
                    star["x"] = random.uniform(0, self.screen_width)
                twinkle = 0.5 + 0.5 * math.sin(
                    t * star["twinkle_speed"] + star["twinkle_phase"]
                )
                brt = star["brightness"] * twinkle
                if li == 0:
                    color = (
                        _clamp(int(120 * brt)),
                        _clamp(int(130 * brt)),
                        _clamp(int(200 * brt)),
                    )
                elif li == 1:
                    v = _clamp(int(180 * brt))
                    color = (v, v, _clamp(int(v * 0.9)))
                else:
                    color = (
                        _clamp(int(220 * brt)),
                        _clamp(int(210 * brt)),
                        _clamp(int(170 * brt)),
                    )
                sx, sy = int(star["x"]), int(star["y"])
                if 0 <= sx < self.screen_width and 0 <= sy < self.screen_height:
                    console.print(sx, sy, star["char"], fg=color)

    def _update_meteors(self, console):
        """유성 업데이트 및 렌더링"""
        if random.random() < 0.02:
            self.meteors.append({
                "x": random.uniform(0, self.screen_width * 0.7),
                "y": random.uniform(0, self.screen_height * 0.3),
                "vx": random.uniform(1.5, 3.5),
                "vy": random.uniform(0.8, 2.0),
                "life": random.uniform(0.4, 1.0),
                "trail": random.randint(3, 8),
            })
        remaining = []
        for m in self.meteors:
            m["x"] += m["vx"]
            m["y"] += m["vy"]
            m["life"] -= 0.03
            if m["life"] > 0 and m["x"] < self.screen_width + 10 and m["y"] < self.screen_height + 10:
                for i in range(m["trail"]):
                    tx = int(m["x"] - m["vx"] * i * 0.4)
                    ty = int(m["y"] - m["vy"] * i * 0.4)
                    if 0 <= tx < self.screen_width and 0 <= ty < self.screen_height:
                        fade = max(0, m["life"] - i * 0.1)
                        v = _clamp(int(255 * fade))
                        ch = "*" if i == 0 else "·"
                        console.print(tx, ty, ch, fg=(v, v, _clamp(int(v * 0.7))))
                remaining.append(m)
        self.meteors = remaining[-15:]

    def _update_particles(self, console):
        """화면 전체 미세 반짝이 파티클"""
        if random.random() < 0.05:
            self.particles.append({
                "x": random.uniform(0, self.screen_width),
                "y": random.uniform(0, self.screen_height),
                "vx": random.uniform(-0.2, 0.2),
                "vy": random.uniform(-0.3, 0.0),
                "life": random.uniform(0.3, 1.0),
                "char": random.choice("·.*"),
                "color": random.choice([
                    (200, 200, 255), (255, 255, 200), (180, 220, 255),
                ]),
            })
        remaining = []
        for p in self.particles:
            p["x"] += p["vx"] * 0.3
            p["y"] += p["vy"] * 0.3
            p["life"] -= 0.03
            if p["life"] > 0:
                alpha = min(1.0, p["life"])
                px, py = int(p["x"]), int(p["y"])
                if 0 <= px < self.screen_width and 0 <= py < self.screen_height:
                    c = p["color"]
                    fc = (
                        _clamp(int(c[0] * alpha)),
                        _clamp(int(c[1] * alpha)),
                        _clamp(int(c[2] * alpha)),
                    )
                    console.print(px, py, p["char"], fg=fc)
                remaining.append(p)
        self.particles = remaining[-20:]

    def _render_decoration_line(self, console, y, idx_offset):
        """상하 장식 라인: ══════════════ ✦ ══════════════"""
        cx = self.screen_width // 2
        half_len = 16
        # 고정 위치로 색상 조회 (내부 phase가 시간 애니메이션 담당)
        star_color = self._star_cycler.get_color(0)
        console.print(cx, y, "✦", fg=star_color)
        for i in range(1, half_len + 1):
            line_color = self._border_cycler.get_color(i)
            lx = cx - i
            rx = cx + i
            if 0 <= lx < self.screen_width:
                console.print(lx, y, "═", fg=line_color)
            if 0 <= rx < self.screen_width:
                console.print(rx, y, "═", fg=line_color)

    def _render_title(self, console):
        """장식 타이틀: ═══ ✦ 파티 구성 ✦ ═══"""
        title_text = "파티 구성"
        title_y = 2

        if not self._title_scramble_done:
            title_x = (self.screen_width - len(title_text)) // 2
            render_scrambled_text(
                console, title_x, title_y,
                self._title_scrambler,
                fg_resolved=(200, 200, 255),
                fg_scrambled=(0, 180, 80),
            )
        else:
            decorated = f"═══ ✦ {title_text} ✦ ═══"
            dec_len = len(decorated)
            dx = (self.screen_width - dec_len) // 2

            dash_color = self._border_cycler.get_color(0)
            star_color = self._star_cycler.get_color(0)
            sub_brightness = _clamp(int(200 + 55 * math.sin(self.animation_frame / 50.0)))
            title_color = (sub_brightness, sub_brightness, 255)

            console.print(dx, title_y, "═══", fg=dash_color)
            console.print(dx + 4, title_y, "✦", fg=star_color)
            console.print(dx + 6, title_y, title_text, fg=title_color)
            console.print(dx + 6 + len(title_text) + 1, title_y, "✦", fg=star_color)
            console.print(dx + 6 + len(title_text) + 3, title_y, "═══", fg=dash_color)

    def _render_animated_frame(self, console, x, y, w, h, title=""):
        """애니메이션 테두리 패널 (╔═╗║╚╝ + ColorCycler wave)"""
        fc = self._frame_cycler.get_color(0)

        console.print(x, y, "╔", fg=fc)
        for i in range(1, w - 1):
            console.print(x + i, y, "═", fg=fc)
        console.print(x + w - 1, y, "╗", fg=fc)

        console.print(x, y + h - 1, "╚", fg=fc)
        for i in range(1, w - 1):
            console.print(x + i, y + h - 1, "═", fg=fc)
        console.print(x + w - 1, y + h - 1, "╝", fg=fc)

        for row in range(y + 1, y + h - 1):
            console.print(x, row, "║", fg=fc)
            console.print(x + w - 1, row, "║", fg=fc)

        if title:
            title_x = x + (w - len(title)) // 2
            star_color = self._star_cycler.get_color(0)
            console.print(title_x, y, title, fg=star_color)

    # ── 메인 렌더 ────────────────────────────────────────────

    def render(self, console: tcod.console.Console):
        """파티 구성 화면 렌더링"""
        console.clear()
        self.animation_frame += 1

        # dt 계산
        _now = _time_module.time()
        _dt = min(0.1, _now - self._last_render_time) if self._last_render_time > 0 else 0.033
        self._last_render_time = _now
        t = _now

        # 이펙트 업데이트
        self._border_cycler.update(_dt)
        self._star_cycler.update(_dt)
        self._frame_cycler.update(_dt)

        if not self._title_scramble_done:
            self._title_scrambler.update(_dt)
            if self._title_scrambler.is_complete:
                self._title_scramble_done = True

        # 1. 배경 (그라데이션 + 오로라)
        self._render_bg(console, t)

        # 2. 3레이어 별빛
        self._render_stars(console, t)

        # 3. 유성
        self._update_meteors(console)

        # 4. 파티클
        self._update_particles(console)

        # 5. 상단 장식 라인 (y=0)
        self._render_decoration_line(console, 0, self.animation_frame)

        # 6. 장식 타이틀 (y=2)
        self._render_title(console)

        # 7. 현재 파티 상태 표시 (우측)
        self._render_party_status(console)

        # 8. 상태별 렌더링
        if self.state == "job_select":
            if self.job_menu:
                self.job_menu.render(console)
                self._render_category_filter(console)
                self._render_job_ratings(console)
                self._render_synergy_guide(console)
                help_text = "↑↓: 이동  ←→: 카테고리  Z: 선택  X: 이전"
                console.print(2, self.screen_height - 2, help_text, fg=Colors.GRAY)

        elif self.state == "name_input":
            if self.name_input:
                self.name_input.render(console)

        elif self.state == "trait_select":
            if self.trait_menu:
                self.trait_menu.render(console)
                help_text = "↑↓: 이동  Z: 선택/해제  X: 이전"
                console.print(2, self.screen_height - 2, help_text, fg=Colors.GRAY)

        elif self.state == "passive_select":
            if self.passive_menu:
                self.passive_menu.render(console)
                help_text = "↑↓: 이동  Z: 선택/해제  X: 이전"
                console.print(2, self.screen_height - 2, help_text, fg=Colors.GRAY)

        elif self.state == "confirm":
            confirm_msg = "파티 구성이 완료되었습니다!"
            pulse = _clamp(int(200 + 55 * math.sin(self.animation_frame / 40.0)))
            confirm_color = (pulse, pulse, 255)
            console.print(
                (self.screen_width - len(confirm_msg)) // 2,
                20,
                confirm_msg,
                fg=confirm_color
            )
            confirm_help = "Z: 게임 시작  X: 수정"
            console.print(
                (self.screen_width - len(confirm_help)) // 2,
                22,
                confirm_help,
                fg=Colors.GRAY
            )

        # 에러 메시지 표시
        if self.error_timer > 0:
            console.print(
                (self.screen_width - len(self.error_message)) // 2,
                self.screen_height - 4,
                self.error_message,
                fg=(255, 100, 100)
            )
            self.error_timer -= 1

        # 하단 장식 라인
        self._render_decoration_line(console, self.screen_height - 1, self.animation_frame + 20)

    def _render_category_filter(self, console: tcod.console.Console):
        """카테고리 필터 표시 (애니메이션)"""
        filter_y = 4
        filter_x = 3

        current_idx = self.category_list.index(self.category_filter)
        prev_cat = self.category_list[(current_idx - 1) % len(self.category_list)]
        next_cat = self.category_list[(current_idx + 1) % len(self.category_list)]

        # 좌우 화살표 미세 깜빡임 (약 1초 주기)
        arrow_blink = (self.animation_frame // 30) % 2 == 0
        arrow_color = Colors.GRAY if arrow_blink else (80, 80, 100)

        console.print(filter_x, filter_y, f"◀ {prev_cat}", fg=arrow_color)
        cat_color = self._star_cycler.get_color(0)
        console.print(filter_x + 12, filter_y, f"[ {self.category_filter} ]", fg=cat_color)
        console.print(filter_x + 28, filter_y, f"{next_cat} ▶", fg=arrow_color)

    def _render_job_ratings(self, console: tcod.console.Console):
        """선택된 직업의 평점 표시"""
        if not self.job_menu:
            return
            
        # 현재 선택된 항목 가져오기
        selected_item = self.job_menu.get_selected_item()
        if not selected_item or not selected_item.value:
            return
            
        # job 정보 추출
        job_data = selected_item.value.get('job')
        if not job_data:
            return
            
        job_id = job_data.get('id', '')
        ratings = self.job_ratings.get(job_id)
        
        if not ratings:
            return
        
        # 평점 표시 위치 (화면 우측 하단)
        rating_x = 52
        rating_y = 28
        
        # 애니메이션 테두리
        self._render_animated_frame(
            console, rating_x, rating_y, 28, 12,
            title=f"[ {job_data.get('name', job_id)} ]"
        )
        
        # 각 평점 항목 표시
        rating_names = ["화력", "유틸", "생존", "스피드", "조작난이도"]
        rating_colors = [
            (255, 100, 100),   # 화력 - 빨강
            (100, 200, 255),   # 유틸 - 하늘색
            (100, 255, 100),   # 생존 - 초록
            (255, 255, 100),   # 스피드 - 노랑
            (200, 150, 255),   # 조작난이도 - 보라
        ]
        
        for i, name in enumerate(rating_names):
            y = rating_y + 2 + i * 2
            value = ratings.get(name, 0)
            
            # 항목 이름
            console.print(rating_x + 2, y, f"{name}:", fg=Colors.UI_TEXT)
            
            # 별 표시 (★ = 1점, ☆ = 0.5점 빈칸)
            stars = ""
            full_stars = int(value)
            half_star = (value - full_stars) >= 0.5
            
            for j in range(5):
                if j < full_stars:
                    stars += "★"
                elif j == full_stars and half_star:
                    stars += "☆"
                else:
                    stars += "·"
            
            console.print(rating_x + 14, y, stars, fg=rating_colors[i])
            console.print(rating_x + 21, y, f"({value:.1f})", fg=Colors.GRAY)

    def _render_party_status(self, console: tcod.console.Console):
        """현재 파티 상태 표시"""
        status_x = 52
        status_y = 8

        # 애니메이션 테두리
        self._render_animated_frame(
            console, status_x, status_y - 2, 28, 18,
            title="현재 파티"
        )

        # 4개 슬롯 표시
        for i in range(4):
            slot_y = status_y + i * 3

            if i < len(self.party) and self.party[i].character_name:
                # 완성된 멤버
                member = self.party[i]
                console.print(
                    status_x + 2,
                    slot_y,
                    f"{i + 1}. {member.character_name}",
                    fg=Colors.UI_TEXT_SELECTED if i == self.current_slot else Colors.UI_TEXT
                )
                console.print(
                    status_x + 5,
                    slot_y + 1,
                    f"({member.job_name})",
                    fg=Colors.GRAY
                )
            elif i == self.current_slot:
                # 현재 선택 중
                console.print(
                    status_x + 2,
                    slot_y,
                    f"{i + 1}. > 선택 중...",
                    fg=Colors.UI_TEXT_SELECTED
                )
            else:
                # 빈 슬롯
                console.print(
                    status_x + 2,
                    slot_y,
                    f"{i + 1}. (비어있음)",
                    fg=Colors.DARK_GRAY
                )

    # ── 편성 효과 가이드 ────────────────────────────────────────

    def _get_preview_jobs(self) -> List[str]:
        """현재 확정된 파티원 + 커서 위치 직업으로 미리보기 직업 목록 생성"""
        jobs = [m.job_id for m in self.party if m.job_id]
        if self.job_menu:
            selected = self.job_menu.get_selected_item()
            if selected and selected.value:
                job_data = selected.value.get('job')
                if job_data:
                    hover_job = job_data.get('id', '')
                    if hover_job and hover_job not in jobs:
                        jobs.append(hover_job)
        return jobs

    def _get_job_name_map(self) -> Dict[str, str]:
        """직업 ID → 한글 이름 매핑 (메뉴 아이템에서 구축)"""
        if not hasattr(self, '_job_name_map') or not self._job_name_map:
            self._job_name_map = {}
            if self.job_menu:
                for item in self.job_menu.items:
                    if item.value and 'job' in item.value:
                        job = item.value['job']
                        self._job_name_map[job['id']] = job['name']
        return self._job_name_map

    def _render_synergy_guide(self, console: tcod.console.Console):
        """편성 보너스 & 합체기 미리보기 가이드 패널 (왼쪽 하단, 넓게)"""
        preview_jobs = self._get_preview_jobs()
        if not preview_jobs:
            return

        try:
            synergy = get_synergy_manager()
        except Exception:
            return

        lines: List[tuple] = []  # [(text, color)]

        # 1. 활성 파티 보너스
        for bonus in synergy._party_bonuses:
            if bonus.check_condition(preview_jobs):
                # 보너스 이름
                lines.append((f" ★ {bonus.name}", (100, 255, 100)))
                # 간략 효과 (설명에서 ":" 뒤 부분 추출)
                desc = bonus.description
                if ":" in desc:
                    effect_part = desc.split(":")[-1].strip()
                else:
                    effect_part = desc
                if len(effect_part.encode('utf-8')) > 88:
                    effect_part = effect_part[:30] + ".."
                lines.append((f"   {effect_part}", (120, 180, 120)))

        # 2. 사용 가능한 합체기
        name_map = self._get_job_name_map()
        for combo in synergy.get_all_combos():
            if all(j in preview_jobs for j in combo.required_jobs):
                lines.append((f" ◆ {combo.name}", (100, 200, 255)))
                job_names = "+".join(name_map.get(j, j) for j in combo.required_jobs)
                lines.append((f"   ({job_names})", (130, 160, 190)))

        if not lines:
            return

        # 패널 렌더링 (왼쪽 하단, 직업 메뉴 아래에 넓게)
        panel_x = 2
        panel_w = 48
        max_lines = min(len(lines), 8)
        panel_h = max_lines + 2  # 테두리 포함

        # 하단 도움말(screen_height - 2) 위에 배치
        panel_y = self.screen_height - panel_h - 3

        self._render_animated_frame(
            console, panel_x, panel_y, panel_w, panel_h,
            title="편성 효과"
        )

        for i, (text, color) in enumerate(lines[:max_lines]):
            display_text = text[:panel_w - 3]  # 패널 너비에 맞게 자르기
            console.print(panel_x + 1, panel_y + 1 + i, display_text, fg=color)

    def get_party(self) -> Optional[List[PartyMember]]:
        """완성된 파티 반환"""
        if self.completed and len(self.party) == 4:
            return self.party
        return None
    
    def get_passives(self) -> List[str]:
        """선택된 패시브 목록 반환 (파티 전체 공통)"""
        return self.selected_passives


def run_party_setup(console: tcod.console.Console, context: tcod.context.Context) -> tuple[Optional[List[PartyMember]], List[str]]:
    """
    파티 구성 실행

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트

    Returns:
        완성된 파티 또는 None (취소 시)
    """
    # 새 게임 시작 시 퀘스트 매니저 초기화
    from src.quest.quest_manager import reset_quest_manager
    reset_quest_manager()
    
    # 파티 구성 BGM 재생
    play_bgm("party_setup")

    # 이전 화면에서 남은 입력 이벤트 제거
    for _ in tcod.event.get():
        pass
    unified_input_handler.clear_input_state()

    setup = PartySetup(console.width, console.height)

    # 애니메이션을 위한 시간 관리
    import time
    last_time = time.time()
    frame_time = 1.0 / 30.0  # 30 FPS

    while True:
        try:
            current_time = time.time()
            delta_time = current_time - last_time

            # 프레임 제한 (30 FPS)
            if delta_time >= frame_time:
                last_time = current_time

                # 렌더링 (매 프레임마다 애니메이션 업데이트)
                setup.render(console)
                context.present(console)

            # pygame 이벤트 업데이트 (게임패드 입력을 위해)
            try:
                import pygame
                pygame.event.pump()
            except:
                pass

            # 게임패드 입력 우선 확인
            gamepad_action = unified_input_handler.get_action()
            if gamepad_action:
                if setup.handle_input(gamepad_action, None):
                    # 완료 또는 취소
                    if setup.cancelled:
                        return None
                    party = setup.get_party()
                    passives = setup.get_passives() if party else []
                    return (party, passives)

            # 키보드 입력 처리
            state_before_loop = setup.state
            for event in tcod.event.get():
                action = unified_input_handler.process_tcod_event(event)

                # KeyDown 이벤트 저장 (텍스트 입력용)
                key_event = event if isinstance(event, tcod.event.KeyDown) else None

                # TextInput 이벤트 (한글 IME 등 조합 문자) - 이름 입력 중 직접 전달
                # 단, 이번 루프에서 막 name_input으로 전환된 경우 무시 (확정키 문자 유입 방지)
                if isinstance(event, tcod.event.TextInput) and setup.state == "name_input":
                    if state_before_loop == "name_input" and setup.name_input:
                        setup.name_input.handle_input(None, text_event=event)
                    continue

                # 이름 입력 중이나 패시브 선택 중에는 action이 없어도 event 처리 필요
                if action or (key_event and (setup.state == "name_input" or setup.state == "passive_select")):
                    if setup.handle_input(action, key_event):
                        # 완료 또는 취소
                        if setup.cancelled:
                            return None
                        party = setup.get_party()
                        passives = setup.get_passives() if party else []
                        return (party, passives)

                # 윈도우 닫기
                if isinstance(event, tcod.event.Quit):
                    return None

            # CPU 사용률 낮추기
            time.sleep(0.01)

        except Exception as e:
            import traceback
            logger = get_logger("party_setup")
            logger.error(f"파티 구성 루프 오류: {e}")
            logger.error(traceback.format_exc())
            # 오류 발생 시 에러 메시지를 화면에 표시하고 계속 진행
            setup.error_message = f"오류: {e}"
            setup.error_timer = 180
