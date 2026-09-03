"""
스토리 연계 튜토리얼 매니저
Dawn of Stellar - 시공의 여명

스토리 기반 튜토리얼 코스 시스템과 직업 해금 보상을 관리합니다.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from src.tutorial.tutorial_manager import TutorialManager, get_tutorial_manager
from src.core.event_bus import event_bus
from src.core.logger import get_logger, Loggers


logger = get_logger(Loggers.SYSTEM)


class StoryChapter(Enum):
    """스토리 챕터"""
    PROLOGUE = "prologue"
    CHAPTER_1 = "chapter_1"
    CHAPTER_2 = "chapter_2"
    CHAPTER_3 = "chapter_3"
    CHAPTER_4 = "chapter_4"
    CHAPTER_5 = "chapter_5"
    CHAPTER_6 = "chapter_6"
    EPILOGUE = "epilogue"


@dataclass
class NPCGuide:
    """NPC 가이드 정보"""
    id: str
    name: str
    title: str
    origin_era: str
    portrait: str
    color: tuple
    personality: str


@dataclass
class JobChoice:
    """직업 선택지"""
    id: str
    name: str
    description: str
    story_reason: str
    recommended: bool = False
    preview_skills: List[str] = field(default_factory=list)


@dataclass 
class StoryTutorialConfig:
    """스토리 튜토리얼 설정"""
    enabled: bool = True
    title: str = "시공의 여명"
    chapters: List[Dict[str, Any]] = field(default_factory=list)
    npc_guides: Dict[str, NPCGuide] = field(default_factory=dict)
    job_choices: List[JobChoice] = field(default_factory=list)
    default_job_choice: str = "time_mage"


class StoryTutorialManager:
    """
    스토리 연계 튜토리얼 매니저
    
    스토리 기반의 튜토리얼 코스를 관리하고,
    튜토리얼 완료 시 직업 해금 보상을 처리합니다.
    """
    
    def __init__(self, data_dir: str = "data/tutorials/courses"):
        self.data_dir = Path(data_dir)
        self.config: StoryTutorialConfig = StoryTutorialConfig()
        self.base_manager: TutorialManager = get_tutorial_manager()
        
        # 상태
        self.current_chapter: Optional[StoryChapter] = None
        self.completed_chapters: List[str] = []
        self.selected_job: Optional[str] = None
        self.story_mode_active: bool = False
        
        # NPC 가이드
        self.npc_guides: Dict[str, NPCGuide] = {}
        
        # 직업 선택 콜백
        self.on_job_selection: Optional[Callable[[str], None]] = None
        
        # 이벤트 구독
        self._subscribe_to_events()
        
        logger.info("스토리 튜토리얼 매니저 초기화")
        
    def load_story_config(self) -> bool:
        """스토리 튜토리얼 설정 로드"""
        try:
            config_path = self.data_dir / "story_course_config.yaml"
            if not config_path.exists():
                logger.warning(f"스토리 설정 파일 없음: {config_path}")
                return False
                
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # 기본 설정
            self.config.enabled = data.get("story_mode", {}).get("enabled", True)
            self.config.title = data.get("story_mode", {}).get("title", "시공의 여명")
            self.config.chapters = data.get("story_chapters", [])
            
            # NPC 가이드 로드
            for npc_id, npc_data in data.get("npc_guides", {}).items():
                self.npc_guides[npc_id] = NPCGuide(
                    id=npc_id,
                    name=npc_data.get("name", ""),
                    title=npc_data.get("title", ""),
                    origin_era=npc_data.get("origin_era", ""),
                    portrait=npc_data.get("portrait", ""),
                    color=tuple(npc_data.get("color", [255, 255, 255])),
                    personality=npc_data.get("personality", "")
                )
            
            # 직업 선택지 로드
            reward_config = data.get("completion_reward", {})
            self.config.default_job_choice = reward_config.get("default_choice", "time_mage")
            
            for choice_data in reward_config.get("choices", []):
                self.config.job_choices.append(JobChoice(
                    id=choice_data.get("id", ""),
                    name=choice_data.get("name", ""),
                    description=choice_data.get("description", ""),
                    story_reason=choice_data.get("story_reason", ""),
                    recommended=choice_data.get("recommended", False),
                    preview_skills=choice_data.get("preview_skills", [])
                ))
            
            logger.info(f"스토리 설정 로드 완료: {len(self.config.chapters)}개 챕터, {len(self.npc_guides)}명 NPC")
            return True
            
        except Exception as e:
            logger.error(f"스토리 설정 로드 실패: {e}")
            return False
    
    def load_story_tutorials(self) -> int:
        """스토리 튜토리얼 파일 로드"""
        loaded_count = 0
        
        try:
            for tutorial_file in self.data_dir.glob("story_*.yaml"):
                try:
                    # 기본 튜토리얼 매니저로 로드
                    tutorial = self.base_manager._load_tutorial_file(tutorial_file)
                    if tutorial:
                        self.base_manager.tutorials[tutorial.id] = tutorial
                        loaded_count += 1
                        logger.debug(f"스토리 튜토리얼 로드: {tutorial.id}")
                except Exception as e:
                    logger.error(f"스토리 튜토리얼 로드 실패 ({tutorial_file}): {e}")
                    
            logger.info(f"스토리 튜토리얼 {loaded_count}개 로드 완료")
            
        except Exception as e:
            logger.error(f"스토리 튜토리얼 로드 중 오류: {e}")
            
        return loaded_count
    
    def start_story_mode(self) -> bool:
        """스토리 모드 시작"""
        if not self.config.enabled:
            logger.info("스토리 모드가 비활성화되어 있습니다.")
            return False
            
        self.story_mode_active = True
        self.current_chapter = StoryChapter.PROLOGUE
        
        # 프롤로그부터 시작
        first_tutorial = self._get_chapter_first_tutorial(StoryChapter.PROLOGUE)
        if first_tutorial:
            event_bus.publish("story.chapter_start", {
                "chapter": StoryChapter.PROLOGUE.value,
                "title": "프롤로그: 시공의 각성"
            })
            return self.base_manager.start_tutorial(first_tutorial)
        
        return False
    
    def _get_chapter_first_tutorial(self, chapter: StoryChapter) -> Optional[str]:
        """챕터의 첫 번째 튜토리얼 ID 반환"""
        for ch in self.config.chapters:
            if ch.get("id") == chapter.value:
                tutorials = ch.get("tutorials", [])
                if tutorials:
                    return tutorials[0]
        return None
    
    def advance_chapter(self) -> bool:
        """다음 챕터로 진행"""
        if not self.current_chapter:
            return False
            
        # 현재 챕터 완료 처리
        self.completed_chapters.append(self.current_chapter.value)
        
        # 다음 챕터 찾기
        chapters = list(StoryChapter)
        current_idx = chapters.index(self.current_chapter)
        
        if current_idx < len(chapters) - 1:
            self.current_chapter = chapters[current_idx + 1]
            
            # 챕터 시작 이벤트
            chapter_info = self._get_chapter_info(self.current_chapter)
            event_bus.publish("story.chapter_start", {
                "chapter": self.current_chapter.value,
                "title": chapter_info.get("title", "")
            })
            
            # 첫 번째 튜토리얼 시작
            first_tutorial = self._get_chapter_first_tutorial(self.current_chapter)
            if first_tutorial:
                return self.base_manager.start_tutorial(first_tutorial)
                
        return False
    
    def _get_chapter_info(self, chapter: StoryChapter) -> Dict[str, Any]:
        """챕터 정보 반환"""
        for ch in self.config.chapters:
            if ch.get("id") == chapter.value:
                return ch
        return {}
    
    def complete_story_mode(self, selected_job: Optional[str] = None) -> Dict[str, Any]:
        """
        스토리 모드 완료 처리
        
        Args:
            selected_job: 선택한 직업 ID (None이면 기본값)
            
        Returns:
            완료 보상 정보
        """
        self.story_mode_active = False
        self.selected_job = selected_job or self.config.default_job_choice
        
        # 직업 해금 처리
        rewards = self._grant_completion_rewards()
        
        # 완료 이벤트 발행
        event_bus.publish("story.complete", {
            "selected_job": self.selected_job,
            "rewards": rewards
        })
        
        # 콜백 호출
        if self.on_job_selection:
            self.on_job_selection(self.selected_job)
        
        logger.info(f"스토리 모드 완료! 직업 해금: {self.selected_job}")
        
        return rewards
    
    def _grant_completion_rewards(self) -> Dict[str, Any]:
        """완료 보상 지급"""
        rewards = {
            "job_unlock": self.selected_job,
            "stellar_fragments": 100,  # 별의 파편 (메타 진행 해금용)
        }
        
        # 메타 진행에 직업 해금 적용 (exactly-once: 이미 해금 시 무지급)
        try:
            from src.persistence.meta_progress import (
                get_meta_progress,
                save_meta_progress,
            )
            meta = get_meta_progress()

            if meta.grant_job_unlock_reward(
                self.selected_job, rewards["stellar_fragments"]
            ):
                save_meta_progress()
                logger.info(
                    f"메타 진행에 직업 해금 적용: {self.selected_job}"
                )
        except Exception as e:
            logger.error(f"메타 진행 업데이트 실패: {e}")
        
        return rewards
    
    def get_npc_dialogue(self, npc_id: str, dialogue_type: str) -> Optional[str]:
        """NPC 대사 반환"""
        npc = self.npc_guides.get(npc_id)
        if not npc:
            return None
            
        # 성격에 따른 대사 스타일
        dialogues = self._get_npc_dialogues(npc_id)
        return dialogues.get(dialogue_type)
    
    def _get_npc_dialogues(self, npc_id: str) -> Dict[str, str]:
        """NPC별 대사 목록"""
        dialogues = {
            "selena": {
                "encourage": "데이터 분석 결과, 당신의 성공 확률은 87.3%입니다. 충분히 가능해요.",
                "explain": "시공 교란 이후 새로운 물리 법칙이 생겼어요. BRV, 용기의 에너지입니다.",
                "success": "완벽해요! 예상 수치를 15% 초과했어요. 대단합니다.",
                "failure": "실패는 학습의 일부예요. 로그를 분석해서 다시 시도해봐요."
            },
            "karnos": {
                "encourage": "... 나쁘지 않군. 내가 본 신병 중엔 상위권이다.",
                "explain": "시공 전쟁에서 배웠다. 적의 BRV를 0으로 만들면 BREAK. 그게 승리의 핵심이다.",
                "success": "흠. 3000년의 전술을 이 정도로 흡수하다니. 천부적이군.",
                "failure": "내 시대에선 이 정도 실패로 죽었다. 하지만 여긴 다르지. 다시 해."
            },
            "mira": {
                "encourage": "와! 당신 정말 재미있는 사람이에요! 기대되는데요?!",
                "explain": "이 직업은 특별한 시대에서 왔어요. 그때는 이런 식으로 싸웠답니다!",
                "success": "대박! 저도 수천 년 떠돌았지만 이런 재능은 처음 봐요!",
                "failure": "에이~ 아깝다! 근데 괜찮아요, 저도 처음엔 막 헤맸거든요~"
            },
            "tord": {
                "encourage": "...쓸 만하군. 우리 마을 애들보단 낫다.",
                "explain": "뭐? 이게 미래 기술? 흥, 기본 원리는 같다. 때려서 강하게 만드는 거지.",
                "success": "오호. 대장간 일 해볼 생각 없나? 센스가 있어.",
                "failure": "바보 같으니. 망치도 제대로 못 잡냐? ...다시 보여줄 테니 잘 봐."
            },
            "lina": {
                "encourage": "맛있는 거 먹으면 힘이 나요! 제가 특별 메뉴 만들어 줄게요!",
                "explain": "과거 재료 + 미래 합성 기술 = 새로운 맛! 시공 융합 요리예요!",
                "success": "와~ 완벽해요! 우주선에서 요리할 때도 이 정도면 합격이에요!",
                "failure": "괜찮아요, 요리도 실패해야 느는 거예요. 다시 해봐요!"
            }
        }
        return dialogues.get(npc_id, {})
    
    def get_job_choices(self) -> List[JobChoice]:
        """직업 선택지 반환"""
        return self.config.job_choices
    
    def _subscribe_to_events(self) -> None:
        """이벤트 구독"""
        event_bus.subscribe("tutorial.step_complete", self._on_tutorial_complete)
        event_bus.subscribe("tutorial.all_complete", self._on_all_complete)
    
    def _on_tutorial_complete(self, data: Dict[str, Any]) -> None:
        """튜토리얼 완료 이벤트 처리"""
        tutorial_id = data.get("tutorial_id", "")
        
        # 챕터 마지막 튜토리얼인지 확인
        if self.current_chapter:
            chapter_info = self._get_chapter_info(self.current_chapter)
            tutorials = chapter_info.get("tutorials", [])
            
            if tutorials and tutorial_id == tutorials[-1]:
                # 챕터 완료
                event_bus.publish("story.chapter_complete", {
                    "chapter": self.current_chapter.value
                })
                
                # 에필로그면 스토리 완료
                if self.current_chapter == StoryChapter.EPILOGUE:
                    # 직업 선택 UI 표시 이벤트
                    event_bus.publish("story.show_job_selection", {
                        "choices": [
                            {
                                "id": c.id,
                                "name": c.name,
                                "description": c.description,
                                "recommended": c.recommended
                            }
                            for c in self.config.job_choices
                        ]
                    })
    
    def _on_all_complete(self, data: Dict[str, Any]) -> None:
        """모든 튜토리얼 완료 이벤트 처리"""
        if self.story_mode_active:
            # 기본 직업으로 완료 (선택 UI가 없는 경우)
            if not self.selected_job:
                self.complete_story_mode()
    
    def save_progress(self) -> Dict[str, Any]:
        """진행 상태 저장"""
        return {
            "story_mode_active": self.story_mode_active,
            "current_chapter": self.current_chapter.value if self.current_chapter else None,
            "completed_chapters": self.completed_chapters,
            "selected_job": self.selected_job
        }
    
    def load_progress(self, data: Dict[str, Any]) -> None:
        """진행 상태 로드"""
        self.story_mode_active = data.get("story_mode_active", False)
        self.completed_chapters = data.get("completed_chapters", [])
        self.selected_job = data.get("selected_job")
        
        chapter_value = data.get("current_chapter")
        if chapter_value:
            try:
                self.current_chapter = StoryChapter(chapter_value)
            except ValueError:
                self.current_chapter = None


# 전역 인스턴스
_story_manager: Optional[StoryTutorialManager] = None


def get_story_tutorial_manager() -> StoryTutorialManager:
    """스토리 튜토리얼 매니저 싱글톤"""
    global _story_manager
    if _story_manager is None:
        _story_manager = StoryTutorialManager()
        _story_manager.load_story_config()
        _story_manager.load_story_tutorials()
    return _story_manager


def unlock_job_from_tutorial(job_id: str) -> bool:
    """
    튜토리얼 보상으로 직업 해금
    
    Args:
        job_id: 해금할 직업 ID
        
    Returns:
        성공 여부
    """
    try:
        from src.persistence.meta_progress import get_meta_progress
        meta = get_meta_progress()
        
        if job_id not in meta.unlocked_jobs:
            meta.unlocked_jobs.append(job_id)
            meta.save()
            
            event_bus.publish("job.unlocked", {
                "job_id": job_id,
                "source": "tutorial_reward"
            })
            
            logger.info(f"튜토리얼 보상으로 직업 해금: {job_id}")
            return True
            
    except Exception as e:
        logger.error(f"직업 해금 실패: {e}")
        
    return False
