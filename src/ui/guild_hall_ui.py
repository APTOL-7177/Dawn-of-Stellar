"""
모험가 길드 홀 UI (Guild Hall UI)

도전과제와 마일스톤을 확인할 수 있는 마을 시설
"""

import tcod.console
import tcod.event
from typing import Optional, List, Tuple
from enum import Enum

from src.ui.cursor_menu import CursorMenu, MenuItem
from src.ui.tcod_display import Colors
from src.ui.input_handler import GameAction, unified_input_handler
from src.core.logger import get_logger
from src.achievement.achievement_manager import AchievementManager
from src.achievement.achievement_system import AchievementCategory, AchievementRarity
from src.achievement.milestone_system import MilestoneCategory


class GuildHallTab(Enum):
    """길드 홀 탭"""
    ACHIEVEMENTS = "achievements"    # 도전과제
    MILESTONES = "milestones"        # 마일스톤
    STATS = "stats"                  # 통계


class GuildHallUI:
    """
    모험가 길드 홀 UI

    도전과제와 마일스톤 확인 및 통계 표시
    """

    def __init__(self, screen_width: int = 80, screen_height: int = 50):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.logger = get_logger("guild_hall")

        # 탭 관리
        self.current_tab = GuildHallTab.ACHIEVEMENTS
        self.tabs = [
            GuildHallTab.ACHIEVEMENTS,
            GuildHallTab.MILESTONES,
            GuildHallTab.STATS
        ]

        # 도전과제 필터
        self.achievement_category_filter = None  # None = 전체
        self.achievement_rarity_filter = None    # None = 전체
        self.show_only_unlocked = False          # 달성된 것만 표시

        # 마일스톤 필터
        self.milestone_category_filter = None   # None = 전체

        # 스크롤 위치
        self.scroll_offset = 0
        self.max_visible_items = 15

        # 선택된 항목
        self.selected_index = 0

        # 도전과제/마일스톤 관리자 (외부에서 주입)
        self.achievement_manager: Optional[AchievementManager] = None

    def set_achievement_manager(self, manager: AchievementManager):
        """도전과제 관리자 설정"""
        self.achievement_manager = manager

    def run(self, console: tcod.console.Console, context: tcod.context.Context) -> bool:
        """
        길드 홀 UI 실행

        Returns:
            True: 계속 실행, False: 종료
        """
        import time
        import pygame
        
        if not self.achievement_manager:
            self.logger.error("도전과제 관리자가 설정되지 않았습니다")
            return False

        while True:
            # 화면 렌더링
            self._render(console)
            context.present(console)

            # pygame 이벤트 업데이트 (게임패드 입력을 위해)
            try:
                pygame.event.pump()
            except:
                pass

            # 키보드 입력 처리
            action = None
            for event in tcod.event.get():
                action = unified_input_handler.process_tcod_event(event)
                
                if isinstance(event, tcod.event.Quit):
                    return False
                
                if action:
                    break
            
            # 게임패드 입력 처리
            if not action:
                action = unified_input_handler.get_action()

            if action == GameAction.ESCAPE or action == GameAction.CANCEL:
                return False
            elif action == GameAction.CONFIRM:
                self._handle_select()
            elif action == GameAction.MOVE_LEFT:
                self._change_tab(-1)
            elif action == GameAction.MOVE_RIGHT:
                self._change_tab(1)
            elif action == GameAction.MOVE_UP:
                self._move_selection(-1)
            elif action == GameAction.MOVE_DOWN:
                self._move_selection(1)
            elif action == GameAction.OPEN_INVENTORY:  # 필터 토글
                self._toggle_filter()
            elif action == GameAction.OPEN_CHARACTER:   # 정렬 토글
                self._toggle_sort()
            elif action == GameAction.OPEN_SKILLS:      # 상세 보기 토글
                self._toggle_detail_view()

            # CPU 사용률 낮추기
            time.sleep(0.01)

    def _change_tab(self, direction: int):
        """탭 변경"""
        current_index = self.tabs.index(self.current_tab)
        new_index = (current_index + direction) % len(self.tabs)
        self.current_tab = self.tabs[new_index]
        self.scroll_offset = 0
        self.selected_index = 0

    def _move_selection(self, direction: int):
        """선택 항목 이동"""
        items = self._get_current_items()
        if not items:
            return

        self.selected_index += direction

        # 범위 체크
        if self.selected_index < 0:
            self.selected_index = 0
            if self.scroll_offset > 0:
                self.scroll_offset -= 1
        elif self.selected_index >= len(items):
            self.selected_index = len(items) - 1

        # 스크롤 조정
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + self.max_visible_items:
            self.scroll_offset = self.selected_index - self.max_visible_items + 1

    def _toggle_filter(self):
        """필터 토글"""
        if self.current_tab == GuildHallTab.ACHIEVEMENTS:
            # 도전과제 카테고리 필터 순환
            categories = [None] + [cat for cat in AchievementCategory]
            if self.achievement_category_filter is None:
                self.achievement_category_filter = categories[0]
            current_index = categories.index(self.achievement_category_filter)
            self.achievement_category_filter = categories[(current_index + 1) % len(categories)]
        elif self.current_tab == GuildHallTab.MILESTONES:
            # 마일스톤 카테고리 필터 순환
            categories = [None] + [cat for cat in MilestoneCategory]
            if self.milestone_category_filter is None:
                self.milestone_category_filter = categories[0]
            current_index = categories.index(self.milestone_category_filter)
            self.milestone_category_filter = categories[(current_index + 1) % len(categories)]

        self.scroll_offset = 0
        self.selected_index = 0

    def _toggle_sort(self):
        """정렬 토글"""
        if self.current_tab == GuildHallTab.ACHIEVEMENTS:
            self.show_only_unlocked = not self.show_only_unlocked
        elif self.current_tab == GuildHallTab.MILESTONES:
            # 마일스톤 정렬 (진행률순/이름순)
            pass

        self.scroll_offset = 0
        self.selected_index = 0

    def _toggle_detail_view(self):
        """상세 보기 토글"""
        # 선택된 항목의 상세 정보 표시
        pass

    def _refresh_data(self):
        """데이터 새로고침"""
        # 도전과제 진행도 재계산 등
        if self.achievement_manager:
            self.achievement_manager.check_daily_achievements()
        self.logger.info("도전과제 데이터 새로고침 완료")

    def _handle_select(self):
        """선택 처리"""
        items = self._get_current_items()
        if not items or self.selected_index >= len(items):
            return

        # 선택된 항목 처리
        selected_item = items[self.selected_index]

        # 상세 정보 표시 또는 다른 액션
        if hasattr(selected_item, 'description'):
            # 상세 정보 토글
            pass

    def _get_current_items(self) -> List:
        """현재 탭의 항목들 가져오기"""
        if not self.achievement_manager:
            return []

        if self.current_tab == GuildHallTab.ACHIEVEMENTS:
            achievements = self.achievement_manager.get_all_achievements()

            # 필터 적용
            if self.achievement_category_filter:
                achievements = [a for a in achievements if a.category == self.achievement_category_filter]

            if self.achievement_rarity_filter:
                achievements = [a for a in achievements if a.rarity == self.achievement_rarity_filter]

            if self.show_only_unlocked:
                achievements = [a for a in achievements if a.is_unlocked]

            # 정렬: 달성된 것 우선, 그 다음 이름순
            achievements.sort(key=lambda x: (not x.is_unlocked, x.name))

            return achievements

        elif self.current_tab == GuildHallTab.MILESTONES:
            milestones = self.achievement_manager.milestone_system.get_all_milestones()

            # 필터 적용
            if self.milestone_category_filter:
                milestones = [m for m in milestones if m.category == self.milestone_category_filter]

            # 정렬: 진행률순
            milestones.sort(key=lambda x: x.progress_percentage, reverse=True)

            return milestones

        elif self.current_tab == GuildHallTab.STATS:
            # 통계 항목들
            stats = self.achievement_manager.get_completion_stats()
            return [
                {"name": "도전과제 완료율", "value": ".1f"},
                {"name": "마일스톤 완료율", "value": ".1f"},
                {"name": "총 획득 별의 파편", "value": stats["total_star_fragments_earned"]},
                {"name": "처치한 적 수", "value": self.achievement_manager.stats["total_kills"]},
                {"name": "입힌 총 데미지", "value": self.achievement_manager.stats["total_damage_dealt"]},
                {"name": "최고 데미지", "value": self.achievement_manager.stats["max_damage_in_one_hit"]},
                {"name": "도달한 최고 층", "value": self.achievement_manager.stats["floor_reached"]},
                {"name": "연 포션 수", "value": self.achievement_manager.stats["potions_brewed"]},
                {"name": "요리한 음식 수", "value": self.achievement_manager.stats["food_cooked"]},
                {"name": "플레이 시간", "value": ".1f"},
            ]

        return []

    def _render(self, console: tcod.console.Console):
        """화면 렌더링"""
        console.clear()

        # 헤더
        title = "[GUILD] 모험가 길드 홀"
        console.print(
            (self.screen_width - len(title)) // 2, 0,
            title,
            fg=Colors.YELLOW
        )

        # 탭 표시
        tab_y = 2
        for i, tab in enumerate(self.tabs):
            tab_name = {
                GuildHallTab.ACHIEVEMENTS: "도전과제",
                GuildHallTab.MILESTONES: "마일스톤",
                GuildHallTab.STATS: "통계"
            }[tab]

            fg_color = Colors.WHITE
            if tab == self.current_tab:
                fg_color = Colors.YELLOW
                console.print(i * 15 + 5, tab_y - 1, "▶", fg=Colors.YELLOW)

            console.print(i * 15 + 7, tab_y, tab_name, fg=fg_color)

        # 필터 표시
        filter_y = 4
        if self.current_tab == GuildHallTab.ACHIEVEMENTS:
            category_name = "전체" if self.achievement_category_filter is None else self.achievement_category_filter.value
            unlocked_filter = "달성만" if self.show_only_unlocked else "전체"
            console.print(2, filter_y, f"카테고리: {category_name} | 표시: {unlocked_filter}", fg=Colors.GRAY)
        elif self.current_tab == GuildHallTab.MILESTONES:
            category_name = "전체" if self.milestone_category_filter is None else self.milestone_category_filter.value
            console.print(2, filter_y, f"카테고리: {category_name}", fg=Colors.GRAY)

        # 컨텐츠 영역
        content_y = 6
        items = self._get_current_items()

        if not items:
            console.print(2, content_y, "표시할 항목이 없습니다.", fg=Colors.GRAY)
            return

        # 표시할 항목들
        visible_items = items[self.scroll_offset:self.scroll_offset + self.max_visible_items]

        for i, item in enumerate(visible_items):
            y = content_y + i
            is_selected = (self.scroll_offset + i) == self.selected_index

            if is_selected:
                # 선택된 항목 강조
                console.draw_rect(0, y, self.screen_width, 1, ch=" ", bg=Colors.DARK_BLUE)
                fg_color = Colors.WHITE
            else:
                fg_color = Colors.GRAY

            # 항목별 렌더링
            if self.current_tab == GuildHallTab.ACHIEVEMENTS:
                self._render_achievement(console, item, y, fg_color, is_selected)
            elif self.current_tab == GuildHallTab.MILESTONES:
                self._render_milestone(console, item, y, fg_color, is_selected)
            elif self.current_tab == GuildHallTab.STATS:
                self._render_stat(console, item, y, fg_color)

        # 스크롤바
        if len(items) > self.max_visible_items:
            self._render_scrollbar(console, len(items), content_y)

        # 하단 도움말
        help_y = self.screen_height - 3
        console.print(2, help_y, "[GAMEPAD] 방향키/LB/RB: 탭이동 | A/확인: 선택 | B/취소: 뒤로", fg=Colors.DARK_GRAY)
        console.print(2, help_y + 1, "[GAMEPAD] X/인벤토리: 필터 | Y/상호작용: 정렬 | LS/스킬: 상세 | RS/줍기: 새로고침", fg=Colors.DARK_GRAY)

    def _render_achievement(self, console: tcod.console.Console, achievement, y: int, fg_color, is_selected: bool):
        """도전과제 렌더링"""
        # 아이콘
        console.print(2, y, achievement.icon, fg=Colors.YELLOW)

        # 이름
        name_color = Colors.GREEN if achievement.is_unlocked else Colors.GRAY
        console.print(5, y, achievement.name, fg=name_color)

        # 진행률 또는 완료 표시
        if achievement.is_unlocked:
            console.print(45, y, "✓ 완료", fg=Colors.GREEN)
            if achievement.reward.star_fragments > 0:
                console.print(55, y, f"⭐ {achievement.reward.star_fragments}", fg=Colors.YELLOW)
        else:
            progress = ".1f"
            console.print(45, y, progress, fg=Colors.BLUE)

        # 희귀도 표시
        rarity_colors = {
            AchievementRarity.COMMON: Colors.GRAY,
            AchievementRarity.UNCOMMON: Colors.GREEN,
            AchievementRarity.RARE: Colors.BLUE,
            AchievementRarity.EPIC: Colors.PURPLE,
            AchievementRarity.LEGENDARY: Colors.YELLOW,
        }
        rarity_color = rarity_colors.get(achievement.rarity, Colors.GRAY)
        rarity_text = achievement.rarity.value.upper()
        console.print(65, y, rarity_text, fg=rarity_color)

        # 힌트 (선택된 경우)
        if is_selected and not achievement.is_unlocked and achievement.hint:
            console.print(2, y + 1, f"💡 {achievement.hint}", fg=Colors.DARK_GRAY)

    def _render_milestone(self, console: tcod.console.Console, milestone, y: int, fg_color, is_selected: bool):
        """마일스톤 렌더링"""
        # 아이콘
        console.print(2, y, milestone.icon, fg=Colors.CYAN)

        # 이름
        console.print(5, y, milestone.name, fg=fg_color)

        # 진행률
        progress_bar = self._create_progress_bar(milestone.progress_percentage, 20)
        console.print(35, y, progress_bar, fg=Colors.BLUE)

        progress_text = ".1f"
        console.print(58, y, progress_text, fg=Colors.BLUE)

        # 현재 단계
        if milestone.current_stage > 0:
            console.print(68, y, f"단계 {milestone.current_stage}", fg=Colors.GREEN)

        # 상세 정보 (선택된 경우)
        if is_selected:
            next_stage = milestone.next_stage
            if next_stage:
                console.print(2, y + 1, f"다음 목표: {next_stage.description}", fg=Colors.DARK_GRAY)
                console.print(2, y + 2, f"보상: {next_stage.reward_description}", fg=Colors.YELLOW)

    def _render_stat(self, console: tcod.console.Console, stat, y: int, fg_color):
        """통계 렌더링"""
        console.print(5, y, stat["name"], fg=fg_color)
        console.print(40, y, str(stat["value"]), fg=Colors.YELLOW)

    def _create_progress_bar(self, percentage: float, width: int) -> str:
        """진행률 바 생성"""
        filled = int(percentage * width)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}]"

    def _render_scrollbar(self, console: tcod.console.Console, total_items: int, start_y: int):
        """스크롤바 렌더링"""
        bar_height = self.max_visible_items
        scrollbar_x = self.screen_width - 3

        # 스크롤바 배경
        for y in range(bar_height):
            console.print(scrollbar_x, start_y + y, "│", fg=Colors.DARK_GRAY)

        # 스크롤바 위치 계산
        if total_items > bar_height:
            scroll_ratio = self.scroll_offset / (total_items - bar_height)
            scroll_pos = int(scroll_ratio * (bar_height - 1))
            console.print(scrollbar_x, start_y + scroll_pos, "█", fg=Colors.BLUE)
