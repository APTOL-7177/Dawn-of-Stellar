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

from src.ui.cursor_menu import CursorMenu, MenuItem, TextInputBox
from src.ui.tcod_display import Colors, render_space_background
from src.ui.input_handler import GameAction, InputHandler
from src.core.logger import get_logger
from src.core.config import get_config
from src.persistence.meta_progress import get_meta_progress
from src.audio import play_bgm
import random


@dataclass
class PartyMember:
    """파티 멤버 정보"""
    job_id: str
    job_name: str
    character_name: str
    stats: Dict[str, Any]
    traits_auto: bool = True  # 특성 자동 선택 여부
    selected_traits: List[str] = None  # 선택된 특성 목록 (멤버별)
    
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

        # 현재 메뉴/입력 박스
        self.job_menu: Optional[CursorMenu] = None
        self.name_input: Optional[TextInputBox] = None
        self.trait_menu: Optional[CursorMenu] = None
        self.passive_menu: Optional[CursorMenu] = None

        # 직업 선택 메뉴 생성
        self._create_job_menu()

        # 에러 메시지
        self.error_message = ""
        self.error_timer = 0  # 에러 메시지 표시 시간

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
            "dark_knight": ["탱커", "마법 딜러"],
            "dimensionist": ["탱커", "마법 딜러"],  # 회피형 탱커
            "vampire": ["탱커", "특수"],  # 생존형 탱커
            
            # 물리 딜러
            "berserker": ["물리 딜러"],
            "gladiator": ["물리 딜러"],
            "samurai": ["물리 딜러"],
            "rogue": ["물리 딜러", "스피드"],
            "assassin": ["물리 딜러", "스피드"],
            "breaker": ["물리 딜러"],
            "archer": ["물리 딜러", "스피드"],
            "sniper": ["물리 딜러"],  # 느린 직업이므로 스피드 제외
            "pirate": ["물리 딜러", "스피드"],
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
            
            # 하이브리드
            "spellblade": ["하이브리드", "물리 딜러", "마법 딜러"],
            "battle_mage": ["하이브리드", "마법 딜러"],  # 탱커 제거
            "monk": ["하이브리드", "물리 딜러", "힐러"],
            
            # 서포터
            "bard": ["서포터"],
            "shaman": ["서포터"],
            "hacker": ["서포터"],
            "engineer": ["서포터"],
            "alchemist": ["서포터"],
            
            # 특수 (유니크한 전투 방식)
            "vampire": ["탱커", "특수"],  # 생존 특화
            "breaker": ["물리 딜러", "특수"],  # BRV 파괴 특화
            "philosopher": ["서포터", "특수"],  # 논리 조작
            "druid": ["힐러", "서포터", "특수"],  # 변신 술사
            "time_mage": ["마법 딜러", "서포터", "특수"],  # 시간 조작
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
                
                # 탱커 체크
                if '탱커' in archetype or '방어' in archetype:
                    categories["탱커"].append(job)
                
                # 힐러 체크
                if '힐러' in archetype or '치유' in archetype or '치료' in archetype:
                    categories["힐러"].append(job)
                
                # 물리 딜러 체크
                if '물리' in archetype or '딜러' in archetype or '공격' in archetype:
                    if '마법' not in archetype:
                        categories["물리 딜러"].append(job)
                
                # 마법 딜러 체크
                if '마법' in archetype or '마검사' in archetype or '원소' in archetype:
                    if '딜러' in archetype or '마법' in archetype:
                        categories["마법 딜러"].append(job)
                
                # 스피드 체크
                if '속도' in archetype or '스피드' in archetype or '빠른' in archetype or \
                   '암살' in archetype or '도적' in archetype:
                    categories["스피드"].append(job)
                
                # 하이브리드 체크
                if '하이브리드' in archetype:
                    categories["하이브리드"].append(job)
                
                # 서포터 체크
                if '서포터' in archetype or '버퍼' in archetype or '지휘관' in archetype or \
                   '디버프' in archetype or '정보' in archetype or '시야' in archetype:
                    categories["서포터"].append(job)
                
                # 어떤 카테고리에도 속하지 않으면 특수
                if not any(job in cat for cat in categories.values()):
                    categories["특수"].append(job)
        
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
                menu_items.append(MenuItem(
                    text=f"  [AI 추천] {recommended_job['name']}",
                    value={"type": "ai_recommend", "job": recommended_job},
                    enabled=True,
                    description=f"AI가 현재 파티 조합을 고려하여 추천하는 {category_name}"
                ))
            
            # 카테고리 내 직업들 추가 (AI 추천 제외)
            for job in jobs_in_category:
                # AI 추천 직업은 이미 추가했으므로 제외
                if recommended_job and job['id'] == recommended_job['id']:
                    continue
                    
                already_selected = job['id'] in selected_job_ids
                desc = f"{job['archetype']} - {job['description']}"
                menu_items.append(MenuItem(
                    text=f"  {job['name']}",
                    value={"type": "job", "job": job},
                    enabled=not already_selected,
                    description=desc
                ))
        
        # 메뉴 생성
        menu_x = 3
        menu_y = 8
        menu_width = 43

        self.job_menu = CursorMenu(
            title=f"파티 멤버 {self.current_slot + 1}/4 - 직업 선택",
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
        
        self.logger.info(f"특성 메뉴 생성: 멤버 {self.current_slot + 1}/4 - {member.character_name} ({member.job_name}, job_id: {member.job_id}), 특성 수: {len(traits)}, 선택된 특성: {member.selected_traits}")
        
        if not traits:
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
            
            for trait in traits:
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
            title=f"{member.character_name} ({member.job_name}) - 특성 선택 ({selected_count}/{max_traits})",
            items=menu_items,
            x=3,
            y=8,
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
            archetype = job.get('archetype', '').lower()
            if '탱커' in archetype or '방어' in archetype or job['id'] in ['knight', 'paladin', 'warrior']:
                tanks.append(job)
            elif '힐러' in archetype or '서포터' in archetype or job['id'] in ['cleric', 'priest', 'bard', 'shaman']:
                healers.append(job)
            elif '물리 딜러' in archetype or '물리' in archetype:
                physical_dps.append(job)
            elif '마법 딜러' in archetype or '마법' in archetype:
                magic_dps.append(job)
            elif '하이브리드' in archetype:
                hybrid.append(job)
            elif '서포터' in archetype or '버퍼' in archetype or '지휘관' in archetype:
                support.append(job)
            else:
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
            return self._handle_passive_select(action)
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
            self.state = "name_input"
            self._create_name_input()
        
        return False

    def _create_passive_menu(self):
        """패시브 선택 메뉴 생성 (파티 전체 공통)"""
        import yaml
        from pathlib import Path
        
        # 패시브는 파티 전체 공통이므로 멤버별 확인 불필요
        
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
            
            # 이미 선택된 패시브인지 확인 (파티 전체 공통)
            is_selected = passive_id in self.selected_passives
            
            # 선택 표시 (선택된 패시브는 [*]로 표시)
            if is_selected:
                checkmark = "[*]"
            else:
                checkmark = "[ ]"
            menu_text = f"{checkmark} {passive_name} (코스트: {passive_cost})"
            
            # 해금 여부 확인 (현재는 unlocked만 확인)
            enabled = unlocked
            
            menu_items.append(MenuItem(
                text=menu_text,
                value=passive_id,
                enabled=enabled,
                description=passive_desc,
                is_selected=is_selected  # 선택된 항목 표시 (색상 구분용)
            ))
        
        # 완료 항목
        menu_items.append(MenuItem(
            text="← 완료",
            value="done",
            enabled=True,
            description="패시브 선택 완료"
        ))
        
        # 총 코스트 정보 포함한 제목
        title = f"파티 전체 패시브 선택 (총 코스트: {total_cost}/10)"
        if total_cost > 10:
            title += " [초과!]"
        
        self.passive_menu = CursorMenu(
            title=title,
            items=menu_items,
            x=3,
            y=8,
            width=43,
            show_description=True
        )

    def _handle_passive_select(self, action: GameAction) -> bool:
        """패시브 선택 입력 처리 (파티 전체 공통)"""
        if action == GameAction.MOVE_UP:
            self.passive_menu.move_cursor_up()
        elif action == GameAction.MOVE_DOWN:
            self.passive_menu.move_cursor_down()
        elif action == GameAction.CONFIRM:
            selected = self.passive_menu.get_selected_item()
            if selected:
                value = selected.value
                
                if value == "done":
                    # 패시브 선택 완료 → 확인 단계로
                    total_cost = 0
                    for passive_id in self.selected_passives:
                        # passives.yaml에서 코스트 확인
                        from pathlib import Path
                        import yaml
                        passives_file = Path("data/passives.yaml")
                        if passives_file.exists():
                            with open(passives_file, 'r', encoding='utf-8') as f:
                                data = yaml.safe_load(f)
                                if data and 'passives' in data:
                                    passives = data['passives'] if isinstance(data['passives'], list) else list(data['passives'].values())
                                    for p in passives:
                                        if p.get('id') == passive_id:
                                            total_cost += p.get('cost', 0)
                    
                    self.logger.info(f"패시브 선택 완료: 선택된 패시브 수: {len(self.selected_passives)}, 총 코스트: {total_cost}")
                    self.state = "confirm"
                else:
                    # 패시브 토글 (파티 전체 공통)
                    # 코스트 계산
                    from pathlib import Path
                    import yaml
                    passives_file = Path("data/passives.yaml")
                    current_cost = 0
                    passive_cost = 0
                    
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
                    else:
                        # 선택 (최대 코스트 10 제한)
                        if current_cost + passive_cost <= 10:
                            self.selected_passives.append(value)
                            self.logger.info(f"패시브 선택: {value}, 현재 선택된 패시브: {self.selected_passives}, 총 코스트: {current_cost + passive_cost}")
                        else:
                            self.error_message = f"코스트 초과! (현재: {current_cost}, 추가: {passive_cost}, 최대: 10)"
                            self.error_timer = 120
                            self.logger.warning(f"패시브 선택 실패: 코스트 초과 ({current_cost} + {passive_cost} > 10)")
                    
                    # 메뉴 다시 생성 (체크 표시 및 총 코스트 업데이트)
                    current_cursor = self.passive_menu.cursor_index if self.passive_menu else 0
                    self.passive_menu = None
                    self._create_passive_menu()
                    # 커서 위치 복원
                    if self.passive_menu and current_cursor < len(self.passive_menu.items):
                        self.passive_menu.cursor_index = current_cursor
        elif action == GameAction.CANCEL or action == GameAction.ESCAPE:
            # 이전 단계로 (마지막 멤버의 특성 선택)
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
        # Enter 키만 확인 (Z는 문자 입력으로 사용)
        # action이 CONFIRM이나 CANCEL이어도 무시 (Z, X를 문자로 입력하기 위해)
        if event and event.sym == tcod.event.KeySym.RETURN:
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

        elif event and event.sym == tcod.event.KeySym.ESCAPE:
            # ESC만 취소 (X는 문자 입력으로 사용)
            # 직업 선택으로 돌아가기
            self.state = "job_select"
            if not self.party:
                # 파티가 없으면 취소
                self.cancelled = True
                return True
            self.party.pop()  # 현재 슬롯 제거
            self._create_job_menu()

        elif event and event.sym == tcod.event.KeySym.BACKSPACE:
            self.name_input.handle_backspace()

        # 일반 문자 입력 (ASCII 32~126 범위의 출력 가능한 문자)
        # Z와 X도 여기서 문자로 처리됨 (action은 무시)
        elif event:
            # 특수 키 제외
            if event.sym not in [tcod.event.KeySym.RETURN, tcod.event.KeySym.BACKSPACE, tcod.event.KeySym.ESCAPE]:
                # ASCII 범위 확인 (32~126은 출력 가능한 문자)
                if 32 <= event.sym <= 126:
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
            self.current_slot = 3
            self.state = "name_input"
            self._create_name_input()

        return False

    def render(self, console: tcod.console.Console):
        """파티 구성 화면 렌더링"""
        render_space_background(console, self.screen_width, self.screen_height)

        # 제목
        title = "파티 구성"
        console.print(
            (self.screen_width - len(title)) // 2,
            2,
            title,
            fg=Colors.UI_TEXT_SELECTED
        )

        # 현재 파티 상태 표시 (우측)
        self._render_party_status(console)

        # 상태별 렌더링
        if self.state == "job_select":
            if self.job_menu:
                self.job_menu.render(console)

                # 도움말
                help_text = "↑↓: 이동  Z: 선택  X: 이전"
                console.print(
                    2,
                    self.screen_height - 2,
                    help_text,
                    fg=Colors.GRAY
                )

        elif self.state == "name_input":
            if self.name_input:
                self.name_input.render(console)

        elif self.state == "trait_select":
            if self.trait_menu:
                self.trait_menu.render(console)
                
                # 도움말
                help_text = "↑↓: 이동  Z: 선택/해제  X: 이전"
                console.print(
                    2,
                    self.screen_height - 2,
                    help_text,
                    fg=Colors.GRAY
                )

        elif self.state == "passive_select":
            if self.passive_menu:
                self.passive_menu.render(console)
                
                # 도움말
                help_text = "↑↓: 이동  Z: 선택/해제  X: 이전"
                console.print(
                    2,
                    self.screen_height - 2,
                    help_text,
                    fg=Colors.GRAY
                )

        elif self.state == "confirm":
            # 최종 확인 메시지
            confirm_msg = "파티 구성이 완료되었습니다!"
            console.print(
                (self.screen_width - len(confirm_msg)) // 2,
                20,
                confirm_msg,
                fg=Colors.UI_TEXT_SELECTED
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
                fg=(255, 100, 100)  # 빨간색
            )
            self.error_timer -= 1

    def _render_party_status(self, console: tcod.console.Console):
        """현재 파티 상태 표시"""
        status_x = 52
        status_y = 8

        # 테두리
        console.draw_frame(
            status_x,
            status_y - 2,
            28,
            18,
            "현재 파티",
            fg=Colors.UI_BORDER,
            bg=Colors.UI_BG
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
    # 파티 구성 BGM 재생
    play_bgm("party_setup")

    setup = PartySetup(console.width, console.height)
    handler = InputHandler()

    while True:
        # 렌더링
        setup.render(console)
        context.present(console)

        # 입력 처리
        for event in tcod.event.wait():
            action = handler.dispatch(event)

            # KeyDown 이벤트 저장 (텍스트 입력용)
            key_event = event if isinstance(event, tcod.event.KeyDown) else None

            # 이름 입력 중에는 action이 없어도 event 처리 필요
            if action or (key_event and setup.state == "name_input"):
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
