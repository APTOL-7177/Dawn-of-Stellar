"""
튜토리얼 완료 직업 선택 UI
Dawn of Stellar - 시공의 여명

튜토리얼 완료 보상으로 해금 직업을 선택하는 UI입니다.
"""

import tcod
import tcod.console
import tcod.event
import time
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

from src.core.event_bus import event_bus
from src.core.logger import get_logger, Loggers
from src.ui.input_handler import unified_input_handler, iter_game_input, poll_game_input, GameAction
from src.ui.pointer import PointerButton, PointerDispatcher, PointerEvent, PointerEventKind, PointerRegion
from src.ui.visual_tokens import rgb


logger = get_logger(Loggers.UI)


def _job_choice_regions(box_x: int, box_y: int, choices: list["JobChoiceInfo"]) -> tuple[PointerRegion, ...]:
    return tuple(
        PointerRegion(
            region_id=str(index),
            x=box_x + 2,
            y=box_y + 2 + index * 8,
            width=56,
            height=7,
            command=GameAction.CONFIRM,
            tooltip=f"{choice.name}: {choice.description} / {choice.story_reason}",
        )
        for index, choice in enumerate(choices)
    )


def _job_pointer_action(event: PointerEvent, regions: tuple[PointerRegion, ...]) -> tuple[GameAction | None, int | None, str | None]:
    dispatcher = PointerDispatcher(regions)
    result = dispatcher.dispatch(event)
    region = dispatcher.region_at(event.position)
    region_id = result.hovered_region_id or (region.region_id if region else None)
    hovered = int(region_id) if region_id is not None else None
    if event.kind is PointerEventKind.HOVER:
        return None, hovered, result.tooltip
    if event.kind is PointerEventKind.WHEEL:
        return result.action, None, None
    if event.kind is PointerEventKind.CLICK:
        if event.button is PointerButton.RIGHT:
            return GameAction.CANCEL, None, None
        if event.button is PointerButton.LEFT:
            return result.action, hovered, None
    return None, None, None


@dataclass
class JobChoiceInfo:
    """직업 선택지 정보"""
    id: str
    name: str
    description: str
    story_reason: str
    recommended: bool = False
    preview_skills: List[str] = None
    
    def __post_init__(self):
        if self.preview_skills is None:
            self.preview_skills = []


# 직업 카테고리 정의 (34개 직업 + 시간술사 = 35개)
JOB_CATEGORIES = {
    "melee": {
        "name": "근접 전투",
        "description": "적과 직접 맞서 싸우는 전사들",
        "color": (255, 100, 100),
        "jobs": [
            "warrior", "knight", "berserker", "gladiator", "dark_knight",
            "samurai", "monk", "dragon_knight", "sword_saint", "paladin",
        ],
    },
    "ranged": {
        "name": "원거리 전투",
        "description": "먼 거리에서 적을 공격하는 사수들",
        "color": (100, 255, 100),
        "jobs": [
            "archer", "sniper", "rogue", "assassin", "ninja", "pirate", "engineer",
        ],
    },
    "magic": {
        "name": "마법",
        "description": "강력한 마법으로 전장을 지배하는 마법사들",
        "color": (100, 150, 255),
        "jobs": [
            "magician", "elementalist", "archmage", "necromancer",
            "illusionist", "spellblade", "battle_mage",
        ],
    },
    "support": {
        "name": "지원",
        "description": "아군을 강화하고 치유하는 지원가들",
        "color": (255, 255, 100),
        "jobs": [
            "cleric", "priest", "bard", "druid", "shaman", "philosopher",
        ],
    },
    "special": {
        "name": "특수",
        "description": "독특한 기믹으로 싸우는 특수 직업들",
        "color": (200, 150, 255),
        "jobs": [
            "time_mage", "dimensionist", "hacker", "alchemist",
            "vampire", "breaker",
        ],
    },
}


def _load_job_display_name(job_id: str) -> str:
    """data/characters/{job_id}.yaml에서 직업 표시 이름 로드"""
    from pathlib import Path
    import yaml
    path = Path(f"data/characters/{job_id}.yaml")
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data.get("display_name", data.get("name", job_id))
    except Exception:
        pass
    # 폴백: 기본 이름 맵
    _FALLBACK_NAMES = {
        "warrior": "전사", "knight": "기사", "berserker": "광전사",
        "gladiator": "검투사", "dark_knight": "암흑기사", "samurai": "사무라이",
        "monk": "무투가", "dragon_knight": "용기사", "sword_saint": "검성",
        "paladin": "성기사", "archer": "궁수", "sniper": "저격수",
        "rogue": "도적", "assassin": "암살자", "ninja": "닌자", "pirate": "해적",
        "engineer": "기술자", "magician": "마법사", "elementalist": "원소술사",
        "archmage": "대마법사", "necromancer": "강령술사", "illusionist": "환술사",
        "spellblade": "마검사", "battle_mage": "전투마법사",
        "cleric": "성직자", "priest": "사제", "bard": "음유시인",
        "druid": "드루이드", "shaman": "주술사", "philosopher": "현자",
        "time_mage": "시간술사", "dimensionist": "차원술사", "hacker": "해커",
        "alchemist": "연금술사", "vampire": "뱀파이어", "breaker": "브레이커",
    }
    return _FALLBACK_NAMES.get(job_id, job_id)


class JobSelectionUI:
    """
    직업 선택 UI
    
    튜토리얼 완료 시 표시되는 직업 선택 화면입니다.
    시간술사가 기본 추천으로 표시됩니다.
    """
    
    # 색상 상수
    COLOR_TITLE = (255, 215, 0)  # 금색
    COLOR_SELECTED = (0, 255, 255)  # 시안
    COLOR_NORMAL = (200, 200, 200)
    COLOR_RECOMMENDED = (0, 255, 0)  # 녹색
    COLOR_DESCRIPTION = (180, 180, 180)
    COLOR_STORY = (255, 200, 100)  # 주황색
    COLOR_SKILL = (100, 200, 255)  # 하늘색
    
    def __init__(
        self,
        console: tcod.console.Console,
        context: tcod.context.Context,
        choices: List[JobChoiceInfo],
        timeout: float = 30.0
    ):
        self.console = console
        self.context = context
        self.choices = choices
        self.timeout = timeout
        
        self.screen_width = console.width
        self.screen_height = console.height
        
        self.selected_index = 0
        self.confirmed = False
        self.timed_out = False
        self.start_time = 0.0
        self.pointer_tooltip: str | None = None
        
        # 추천 직업을 기본 선택으로
        for i, choice in enumerate(choices):
            if choice.recommended:
                self.selected_index = i
                break
    
    def show(self, on_select: Optional[Callable[[str], None]] = None) -> Optional[str]:
        """
        직업 선택 UI 표시
        
        Args:
            on_select: 선택 완료 시 콜백
            
        Returns:
            선택된 직업 ID (None이면 타임아웃으로 기본 선택)
        """
        self.start_time = time.time()
        
        logger.info("직업 선택 UI 표시")
        
        while not self.confirmed:
            # 타임아웃 확인
            elapsed = time.time() - self.start_time
            if elapsed >= self.timeout:
                self.timed_out = True
                break
            
            # 화면 렌더링
            self._render(self.timeout - elapsed)
            self.context.present(self.console)
            
            # 입력 처리
            for action, event in iter_game_input(timeout=0.1):
                if event and isinstance(event, tcod.event.Quit):
                    return None
                pointer_event = unified_input_handler.process_pointer_event(event) if event is not None else None
                if pointer_event is not None:
                    box_width = 60
                    box_x = (self.screen_width - box_width) // 2
                    box_y = 8
                    pointer_action, hovered_index, tooltip = _job_pointer_action(
                        pointer_event, _job_choice_regions(box_x, box_y, self.choices)
                    )
                    if hovered_index is not None:
                        self.selected_index = hovered_index
                    if tooltip is not None:
                        self.pointer_tooltip = tooltip
                    if pointer_action is not None:
                        action = pointer_action
                if action is not None:
                    self._handle_action(action)
                elif event and isinstance(event, tcod.event.KeyDown):
                    self._handle_key(event)
        
        # 선택된 직업
        selected_job = self.choices[self.selected_index].id
        
        if self.timed_out:
            logger.info(f"타임아웃으로 기본 선택: {selected_job}")
        else:
            logger.info(f"직업 선택 완료: {selected_job}")
        
        # 콜백 호출
        if on_select:
            on_select(selected_job)
        
        # 선택 완료 연출
        self._show_selection_effect()
        
        return selected_job
    
    def _render(self, remaining_time: float) -> None:
        """화면 렌더링"""
        self.console.clear()
        
        # 배경 효과 (시공 느낌)
        self._draw_background()
        
        # 타이틀
        title = "★ 각성할 힘을 선택하세요 ★"
        self.console.print(
            (self.screen_width - len(title)) // 2,
            3,
            title,
            fg=self.COLOR_TITLE
        )
        
        # 설명
        desc = "튜토리얼 완료 보상으로 해금 직업 1개를 무료로 획득합니다."
        self.console.print(
            (self.screen_width - len(desc)) // 2,
            5,
            desc,
            fg=self.COLOR_DESCRIPTION
        )
        
        # 남은 시간
        time_text = f"남은 시간: {int(remaining_time)}초"
        time_color = (255, 255, 0) if remaining_time > 10 else (255, 100, 100)
        self.console.print(
            self.screen_width - len(time_text) - 3,
            3,
            time_text,
            fg=time_color
        )
        
        # 선택지 박스
        box_width = 60
        box_height = len(self.choices) * 8 + 4
        box_x = (self.screen_width - box_width) // 2
        box_y = 8
        
        self._draw_box(box_x, box_y, box_width, box_height)
        
        # 각 선택지 렌더링
        for i, choice in enumerate(self.choices):
            self._render_choice(choice, i, box_x + 2, box_y + 2 + i * 8)
        
        # 조작 안내
        help_y = box_y + box_height + 2
        self.console.print(
            box_x,
            help_y,
            "↑↓/Wheel: 선택 이동  Left/Enter: 확정  Right/ESC: 추천 직업 자동 선택",
            fg=(150, 150, 150)
        )
        if self.pointer_tooltip:
            self.console.print(box_x, help_y + 1, self.pointer_tooltip[:58], fg=rgb("accent.amber"), bg=rgb("state.tooltip"))
    
    def _render_choice(
        self,
        choice: JobChoiceInfo,
        index: int,
        x: int,
        y: int
    ) -> None:
        """선택지 렌더링"""
        is_selected = index == self.selected_index
        if is_selected:
            self.console.draw_rect(x - 1, y, 56, 7, ord(" "), bg=rgb("state.active"))
        
        # 선택 표시
        marker = "▶ " if is_selected else "  "
        
        # 직업 이름
        name_color = self.COLOR_SELECTED if is_selected else self.COLOR_NORMAL
        if choice.recommended:
            name_text = f"{marker}{choice.name} [추천]"
            if not is_selected:
                name_color = self.COLOR_RECOMMENDED
        else:
            name_text = f"{marker}{choice.name}"
        
        self.console.print(x, y, name_text, fg=name_color)
        
        # 설명 (선택된 경우만 상세)
        if is_selected:
            # 설명
            desc_lines = self._wrap_text(choice.description, 50)
            for i, line in enumerate(desc_lines[:2]):
                self.console.print(x + 2, y + 1 + i, line, fg=self.COLOR_DESCRIPTION)
            
            # 스토리 이유
            story_y = y + 3
            self.console.print(
                x + 2,
                story_y,
                f"◆ {choice.story_reason}",
                fg=self.COLOR_STORY
            )
            
            # 미리보기 스킬
            if choice.preview_skills:
                skill_y = story_y + 2
                self.console.print(x + 2, skill_y, "주요 스킬:", fg=self.COLOR_SKILL)
                skills_text = ", ".join(choice.preview_skills[:3])
                self.console.print(x + 12, skill_y, skills_text, fg=self.COLOR_SKILL)
        else:
            # 간단한 설명만
            short_desc = choice.description.split('\n')[0][:45]
            self.console.print(x + 2, y + 1, short_desc + "...", fg=(120, 120, 120))
    
    def _draw_background(self) -> None:
        """배경 효과"""
        import random
        
        # 시공 파티클 효과
        for _ in range(20):
            x = random.randint(0, self.screen_width - 1)
            y = random.randint(0, self.screen_height - 1)
            char = random.choice(['·', '∙', '•', '◦'])
            color = (
                random.randint(30, 80),
                random.randint(50, 100),
                random.randint(80, 150)
            )
            self.console.print(x, y, char, fg=color)
    
    def _draw_box(self, x: int, y: int, width: int, height: int) -> None:
        """박스 그리기"""
        # 상단
        self.console.print(x, y, "╔" + "═" * (width - 2) + "╗", fg=self.COLOR_SELECTED)
        
        # 중간
        for i in range(1, height - 1):
            self.console.print(x, y + i, "║", fg=self.COLOR_SELECTED)
            self.console.print(x + width - 1, y + i, "║", fg=self.COLOR_SELECTED)
        
        # 하단
        self.console.print(x, y + height - 1, "╚" + "═" * (width - 2) + "╝", fg=self.COLOR_SELECTED)
    
    def _wrap_text(self, text: str, max_width: int) -> List[str]:
        """텍스트 줄바꿈"""
        lines = []
        for paragraph in text.split('\n'):
            words = paragraph.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 <= max_width:
                    current_line += word + " "
                else:
                    if current_line:
                        lines.append(current_line.strip())
                    current_line = word + " "
            if current_line:
                lines.append(current_line.strip())
        return lines
    
    def _handle_action(self, action: GameAction) -> None:
        """GameAction 입력 처리 (게임패드 포함)"""
        if action == GameAction.MOVE_UP:
            self.selected_index = (self.selected_index - 1) % len(self.choices)
        elif action == GameAction.MOVE_DOWN:
            self.selected_index = (self.selected_index + 1) % len(self.choices)
        elif action == GameAction.CONFIRM:
            self.confirmed = True
        elif action in (GameAction.CANCEL, GameAction.ESCAPE):
            # CANCEL/ESC는 추천 직업으로 자동 선택
            for i, choice in enumerate(self.choices):
                if choice.recommended:
                    self.selected_index = i
                    break
            self.confirmed = True

    def _handle_key(self, event: tcod.event.KeyDown) -> None:
        """키 입력 처리"""
        if event.sym == tcod.event.KeySym.UP:
            self.selected_index = (self.selected_index - 1) % len(self.choices)
        elif event.sym == tcod.event.KeySym.DOWN:
            self.selected_index = (self.selected_index + 1) % len(self.choices)
        elif event.sym in (tcod.event.KeySym.RETURN, tcod.event.KeySym.KP_ENTER):
            self.confirmed = True
        elif event.sym == tcod.event.KeySym.ESCAPE:
            # ESC는 추천 직업으로 자동 선택
            for i, choice in enumerate(self.choices):
                if choice.recommended:
                    self.selected_index = i
                    break
            self.confirmed = True
    
    def _show_selection_effect(self) -> None:
        """선택 완료 연출"""
        selected = self.choices[self.selected_index]
        
        # 화면 플래시
        for _ in range(3):
            self.console.clear()
            
            # 선택된 직업 이름 크게 표시
            title = f"★ {selected.name} 해금! ★"
            self.console.print(
                (self.screen_width - len(title)) // 2,
                self.screen_height // 2 - 2,
                title,
                fg=self.COLOR_TITLE
            )
            
            # 스토리 이유
            self.console.print(
                (self.screen_width - len(selected.story_reason)) // 2,
                self.screen_height // 2,
                selected.story_reason,
                fg=self.COLOR_STORY
            )
            
            self.context.present(self.console)
            time.sleep(0.3)
            
            self.console.clear()
            self.context.present(self.console)
            time.sleep(0.1)
        
        # 최종 표시
        self.console.clear()
        
        title = f"★ {selected.name} 해금! ★"
        self.console.print(
            (self.screen_width - len(title)) // 2,
            self.screen_height // 2 - 2,
            title,
            fg=self.COLOR_TITLE
        )
        
        self.console.print(
            (self.screen_width - len(selected.story_reason)) // 2,
            self.screen_height // 2,
            selected.story_reason,
            fg=self.COLOR_STORY
        )
        
        continue_text = "Press any key to continue..."
        self.console.print(
            (self.screen_width - len(continue_text)) // 2,
            self.screen_height // 2 + 4,
            continue_text,
            fg=(150, 150, 150)
        )
        
        self.context.present(self.console)
        
        # 아무 키나 대기
        for action, event in iter_game_input():
            pointer_event = unified_input_handler.process_pointer_event(event) if event is not None else None
            if pointer_event is not None and pointer_event.kind is PointerEventKind.CLICK:
                break
            if event and isinstance(event, tcod.event.Quit):
                break
            if action is not None:
                break
            if event and isinstance(event, tcod.event.MouseButtonDown):
                break


def show_job_selection(
    console: tcod.console.Console,
    context: tcod.context.Context,
    on_select: Optional[Callable[[str], None]] = None
) -> Optional[str]:
    """
    직업 선택 UI를 표시하는 헬퍼 함수 (2단계: 카테고리 → 직업)

    Args:
        console: TCOD 콘솔
        context: TCOD 컨텍스트
        on_select: 선택 완료 콜백

    Returns:
        선택된 직업 ID
    """
    from src.ui.npc_dialog_ui import show_npc_dialog, NPCChoice

    # 1단계: 카테고리 선택
    while True:
        cat_choices = []
        cat_keys = list(JOB_CATEGORIES.keys())
        for key in cat_keys:
            cat = JOB_CATEGORIES[key]
            cat_choices.append(
                NPCChoice(text=f"{cat['name']} ({len(cat['jobs'])}개 직업) - {cat['description']}")
            )

        cat_result = show_npc_dialog(
            console, context,
            "셀레나",
            "35개의 직업이 5개 카테고리로 나뉘어 있어요.\n어떤 계열의 직업에 관심이 있나요?",
            choices=cat_choices,
        )

        if cat_result is None:
            # ESC → 시간술사 기본 선택
            if on_select:
                on_select("time_mage")
            return "time_mage"

        selected_cat_key = cat_keys[cat_result]
        selected_cat = JOB_CATEGORIES[selected_cat_key]

        # 2단계: 카테고리 내 직업 선택 (4개씩 페이지)
        job_ids = selected_cat["jobs"]
        page = 0
        jobs_per_page = 4

        while True:
            start = page * jobs_per_page
            end = min(start + jobs_per_page, len(job_ids))
            page_jobs = job_ids[start:end]

            job_choices = []
            for jid in page_jobs:
                name = _load_job_display_name(jid)
                recommended = " [추천]" if jid == "time_mage" else ""
                job_choices.append(NPCChoice(text=f"{name}{recommended}"))

            # 이전/다음 페이지 + 뒤로가기
            has_prev = page > 0
            has_next = end < len(job_ids)
            if has_prev:
                job_choices.append(NPCChoice(text="◀ 이전 페이지"))
            if has_next:
                job_choices.append(NPCChoice(text="▶ 다음 페이지"))
            job_choices.append(NPCChoice(text="← 카테고리로 돌아가기"))

            total_pages = (len(job_ids) + jobs_per_page - 1) // jobs_per_page
            prompt_text = (
                f"【{selected_cat['name']}】 계열 직업 "
                f"(페이지 {page + 1}/{total_pages})\n"
                f"어떤 직업을 선택하시겠어요?"
            )

            job_result = show_npc_dialog(
                console, context, "셀레나", prompt_text, choices=job_choices,
            )

            if job_result is None:
                break  # ESC → 카테고리 선택으로

            # 네비게이션 처리
            nav_offset = len(page_jobs)
            if job_result >= nav_offset:
                nav_idx = job_result - nav_offset
                nav_items = []
                if has_prev:
                    nav_items.append("prev")
                if has_next:
                    nav_items.append("next")
                nav_items.append("back")

                action = nav_items[nav_idx] if nav_idx < len(nav_items) else "back"
                if action == "prev":
                    page -= 1
                    continue
                elif action == "next":
                    page += 1
                    continue
                else:  # back
                    break
            else:
                # 직업 선택됨
                selected_job_id = page_jobs[job_result]

                # 확인 대화
                job_name = _load_job_display_name(selected_job_id)
                confirm_choices = [
                    NPCChoice(text=f"네, {job_name}(으)로 결정합니다!"),
                    NPCChoice(text="다시 선택할게요"),
                ]
                confirm = show_npc_dialog(
                    console, context,
                    "셀레나",
                    f"{job_name}을(를) 선택하시겠어요?\n이 직업은 본 게임에서 해금됩니다.",
                    choices=confirm_choices,
                )
                if confirm == 0:
                    # 선택 확정
                    choices_for_effect = [
                        JobChoiceInfo(
                            id=selected_job_id,
                            name=job_name,
                            description=f"{selected_cat['name']} 계열 직업",
                            story_reason="스토리 모드를 완료하여 각성한 힘",
                            recommended=(selected_job_id == "time_mage"),
                        )
                    ]
                    ui = JobSelectionUI(console, context, choices_for_effect, timeout=999)
                    ui.selected_index = 0
                    ui.confirmed = True
                    ui._show_selection_effect()

                    if on_select:
                        on_select(selected_job_id)
                    return selected_job_id
                # else: 다시 선택 → 같은 페이지 계속
